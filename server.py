import os
import json
import uuid
import time
from queue import Queue, Empty
from threading import Thread
from flask import Flask, request, jsonify, Response, send_from_directory
from flask_cors import CORS
from blog_generator import generate_with_progress

app = Flask(__name__, static_folder='.')
generation_progress = {}

def format_sse_message(data, event_type='message'):
    """格式化SSE消息"""
    if isinstance(data, dict):
        data_str = json.dumps(data, ensure_ascii=False)
    else:
        data_str = str(data)
    return f"event: {event_type}\ndata: {data_str}\n\n"

class ContentMonitor:
    def __init__(self, session_id, progress_queue):
        self.session_id = session_id
        self.progress_queue = progress_queue
        self.last_size = 0
        self.last_content = ""

    def check_content(self, temp_file):
        if os.path.exists(temp_file):
            current_size = os.path.getsize(temp_file)
            if current_size > self.last_size:
                with open(temp_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    new_content = content[len(self.last_content):]
                    if new_content.strip():
                        # 发送API响应更新
                        self.progress_queue.put({
                            "status": "content_update",
                            "type": "api_response",
                            "content": new_content.strip()
                        })
                    self.last_size = current_size
                    self.last_content = content

def send_progress(queue, messages, temp_file, session_id):
    """发送进度消息到前端"""
    monitor = ContentMonitor(session_id, queue)
    
    for msg in messages:
        queue.put({"status": "progress", "message": msg})
        # 检查文件更新
        for _ in range(10):  # 增加检查次数，获取更多日志
            monitor.check_content(temp_file)
            time.sleep(0.2)  # 缩短检查间隔

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/generated_articles/<path:filename>')
def serve_article(filename):
    return send_from_directory('generated_articles', filename)

@app.route('/progress/<session_id>')
def progress(session_id):
    def generate():
        if session_id not in generation_progress:
            yield format_sse_message({'status': 'error', 'message': '无效的会话ID'})
            return

        queue = generation_progress[session_id]
        heartbeat_interval = 5  # 心跳包间隔（秒）
        last_heartbeat = time.time()

        try:
            while True:
                current_time = time.time()
                
                # 检查是否需要发送心跳包
                if current_time - last_heartbeat >= heartbeat_interval:
                    yield format_sse_message({'status': 'heartbeat', 'timestamp': current_time})
                    last_heartbeat = current_time

                try:
                    # 使用更短的超时时间来允许更频繁的心跳检查
                    data = queue.get(timeout=1)
                    
                    if isinstance(data, dict):
                        if data.get('type') == 'progress':
                            yield format_sse_message({
                                'status': 'progress',
                                'type': 'progress',
                                'step': data.get('step', 0),
                                'total': data.get('total', 1),
                                'message': data.get('message', ''),
                                'content': data.get('content', '')
                            })
                        elif data.get('type') == 'api_response':
                            content = data.get('content', '')
                            if isinstance(content, (dict, list)):
                                content = json.dumps(content, ensure_ascii=False)
                            yield format_sse_message({
                                'status': 'content_update',
                                'type': 'api_response',
                                'content': content
                            })
                        elif data.get('type') == 'complete':
                            yield format_sse_message({
                                'status': 'complete',
                                'message': '生成完成！',
                                'stats': data.get('stats', {}),
                                'content': data.get('content', '')
                            })
                            break
                        elif data.get('type') == 'error':
                            yield format_sse_message({
                                'status': 'error',
                                'message': data.get('message', '发生未知错误')
                            })
                            break
                        elif data.get('type') == 'final':
                            yield format_sse_message({
                                'status': 'complete',
                                'message': '生成完成！',
                                'stats': data.get('stats', {}),
                                'content': data.get('content', '')
                            })
                            break
                    else:
                        yield format_sse_message({
                            'status': 'progress',
                            'message': str(data)
                        })

                except Empty:  
                    continue
                except Exception as e:
                    print(f"Error processing queue data: {str(e)}")
                    yield format_sse_message({
                        'status': 'error',
                        'message': f'处理数据时出错: {str(e)}'
                    })
                    break

        except GeneratorExit:
            print(f"Client disconnected from session {session_id}")
        except Exception as e:
            print(f"Error in event stream: {str(e)}")
            yield format_sse_message({
                'status': 'error',
                'message': f'服务器错误: {str(e)}'
            })
        finally:
            # 清理会话资源
            if session_id in generation_progress:
                del generation_progress[session_id]

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',
            'Access-Control-Allow-Origin': '*'
        }
    )

@app.route('/generate', methods=['POST'])
def generate():
    try:
        data = request.get_json()
        if not data or 'topic' not in data:
            return jsonify({'error': '缺少必要参数'}), 400

        topic = data['topic']
        type = data.get('type', 'blog')  # 默认为blog类型

        session_id = str(uuid.uuid4())
        generation_progress[session_id] = Queue()

        def generate_in_thread():
            try:
                def progress_callback(data):
                    generation_progress[session_id].put(data)

                # 开始生成
                article = generate_with_progress(
                    topic=topic,
                    type_name=type,
                    progress_callback=progress_callback
                )
                
                if article:
                    # 保存生成的文章
                    filename = f"{topic}.md"
                    os.makedirs('generated_articles', exist_ok=True)
                    filepath = os.path.join('generated_articles', filename)
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(article)
                    
                    # 发送完成信号和文章内容
                    generation_progress[session_id].put({
                        'status': 'complete',
                        'message': '生成完成！',
                        'content': article,
                        'type': 'final',
                        'stats': {
                            'time': int(time.time() - start_time),  # 转换为整数秒
                            'word_count': len(article),
                            'api_calls': 7
                        }
                    })
                else:
                    generation_progress[session_id].put({
                        'type': 'error',
                        'message': '生成文章失败，请检查控制台输出以获取详细错误信息'
                    })
            except Exception as e:
                print(f"Error in generate_in_thread: {str(e)}")
                generation_progress[session_id].put({
                    'type': 'error',
                    'message': f'生成过程出错: {str(e)}'
                })

        # 启动生成线程
        start_time = time.time()
        Thread(target=generate_in_thread).start()

        return jsonify({'session_id': session_id})

    except Exception as e:
        print(f"Error in generate endpoint: {str(e)}")
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)
