import os
import sys
import openai
import requests
from dotenv import load_dotenv
from openai import OpenAI

# 加载环境变量
load_dotenv()

# 检查API密钥
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    raise ValueError("请在.env文件中设置OPENAI_API_KEY")

# 初始化OpenAI客户端
client = OpenAI(
    base_url="https://api.gptsapi.net/v1",
    api_key=api_key
)

def create_prompt(topic):
    """创建高质量的提示词"""
    return f"""IDENTITY and PURPOSE

你是一位热爱分享知识,擅长用通俗易懂的语言讲解人物传记的科普博主。你的写作风格清晰生动,喜欢用亲切的口吻与读者交流,常用反问句和感叹句增加互动性。你善于举例说明,并经常穿插个人见解和学习心得。一步步思考，完成下面的写作目标。
WRITING STYLE

- 写作风格要体现"三性"：
  - 故事性：用叙事的方式展开内容
  - 画面性：描写要具体生动，让读者能够"看到"场景
  - 情感性：适当表达情感共鸣，拉近与读者距离
- 语言表达要注意"三度"：
  - 温度：语言亲切自然，像朋友间交谈
  - 深度：内容要有深度，但表达要简单
  - 角度：从读者感兴趣的角度切入

OUTPUT INSTRUCTIONS

为[{topic}]创作一篇人物小传，要求：

1. 文章结构（总字数不少于6000字）：
   - 开头：读书、读人、读书人。大家好，我是指月识人，带大家深入了解人物的传奇故事。
   - 标题：20字以内的吸引力标题
   - 四个核心章节（每章不少于1200字）：
     * 背景与动机：成长环境、家庭背景、时代背景、教育经历等
     * 性格与思维模式：性格形成过程、思维方式、处事态度、为人处世等
     * 人生历程与成就：重要事件、关键贡献、创新发明、主要作品等
     * 社会关系与影响力：对社会影响、对后世启示、历史评价、现代意义等
     * 文化属性与价值观：对个体影响、思维模式、行为习惯和个人价值观。
   - 结尾：用一句金句点评人物，并以"关注指月识人，带你走进人物的内心世界。"结束

2. 写作要求：
   - 使用第一人称视角
   - 多用"你"与读者对话
   - 每个论点都要有具体例子和数据支持
   - 语言通俗易懂，避免学术化
   - 适当设计故事情节增强吸引力
   - 每个章节要有明确的过渡和连接
   - 尽量不使用叹号

3. 格式要求：
   - 使用Markdown格式
   - 除标题外，每个章节内容字数约1200字左右；
   - 一级标题要有吸引力，字数20字以内；
   - 二级标题压缩到4个到12个字；
   - 如果有论点，则必须提供论证；
   - 如果有论证，则需要提供论据，论据中要包含丰富的数据；
   - 都采用文内 markdown 链接的方式（abc [xxx](https://...) def），用原始资料的 URL 来对你的叙述提供支撑；
   - 能使用自然段落表述的部分，一般不采用列表形式表达；
   - 除了正文外，前后不输出任何提示性内容；
   - 每个章节至少3个段落
   - 重要论点需要提供论据

请按照以上要求创作一篇生动有趣的人物传记。"""

def read_outline_from_file(filename):
    """从文件读取大纲"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
        return lines
    except Exception as e:
        print(f"读取文件时出错: {str(e)}")
        return None

def generate_blog_content(topic):
    """使用OpenAI生成博客内容"""
    try:
        print(f"\n正在生成关于 '{topic}' 的文章...")
        prompt = create_prompt(topic)
        
        # 第一次调用API生成主要内容
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "你是一个专业的人物传记作家，擅长写作通俗易懂、生动有趣的科普文章。每个章节必须不少于1200字，总字数必须超过6000字。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=4000
        )
        content = response.choices[0].message.content
        
        # 检查内容长度，如果不够继续生成
        if len(content.split()) < 2000:  # 粗略估计字数
            print("正在补充更多内容...")
            response2 = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "你是一个专业的人物传记作家。请为已有的文章补充更多细节和例子，使每个章节达到1200字以上。"},
                    {"role": "user", "content": f"这是已有的文章内容：\n\n{content}\n\n请为每个章节补充更多内容，确保每个章节不少于1200字，重点补充具体的历史事件、数据和例子。保持行文流畅自然。"}
                ],
                temperature=0.8,
                max_tokens=4000
            )
            content = response2.choices[0].message.content

        # 获取图片
        print(f"正在为 '{topic}' 获取配图...")
        images = get_unsplash_images(topic, 4)  # 获取4张图片，每个章节一张
        
        # 在文章内容中插入图片
        sections = content.split('###')
        modified_content = sections[0]  # 保留开头部分
        
        # 为每个章节添加图片
        for i, section in enumerate(sections[1:], 1):
            if i <= len(images):
                modified_content += f"\n\n![{i}号配图]({images[i-1]})\n\n### {section}"
            else:
                modified_content += f"\n\n### {section}"
        
        return modified_content

    except openai.APIError as e:
        print(f"API错误: {str(e)}")
        return None
    except Exception as e:
        print(f"生成文章时出错: {str(e)}")
        return None

def get_unsplash_images(keyword, count=3):
    """从Unsplash获取图片"""
    try:
        headers = {
            'Authorization': f'Client-ID {os.getenv("UNSPLASH_ACCESS_KEY")}'
        }
        params = {
            'query': keyword,
            'per_page': count,
            'orientation': 'landscape'  # 优先使用横向图片
        }
        response = requests.get(
            'https://api.unsplash.com/search/photos',
            headers=headers,
            params=params
        )
        response.raise_for_status()
        data = response.json()
        if not data.get('results'):
            return []
        return [photo['urls']['regular'] for photo in data['results']]
    except Exception as e:
        print(f"获取图片时出错: {str(e)}")
        return []

def save_article(content, topic, index):
    """保存文章到文件"""
    # 创建输出目录（如果不存在）
    output_dir = "generated_articles"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 生成文件名（使用主题的前20个字符）
    safe_topic = "".join(x for x in topic[:20] if x.isalnum() or x in (' ', '-', '_')).strip()
    filename = f"{output_dir}/article_{index+1}_{safe_topic}.md"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"文章已保存到: {filename}")
        return True
    except Exception as e:
        print(f"保存文章时出错: {str(e)}")
        return False

def main():
    try:
        # 检查命令行参数
        if len(sys.argv) != 2:
            print("使用方法: python blog_generator.py <输入文件名>")
            return
        
        input_file = sys.argv[1]
        
        # 读取主题列表
        topics = read_outline_from_file(input_file)
        if not topics:
            print("无法读取输入文件或文件为空！")
            return
        
        print(f"从 {input_file} 中读取到 {len(topics)} 个主题")
        
        # 为每个主题生成文章
        for i, topic in enumerate(topics):
            # 生成文章内容
            content = generate_blog_content(topic)
            if not content:
                print(f"跳过主题 '{topic}' - 生成失败")
                continue
            
            # 保存文章
            save_article(content, topic, i)
            
        print("\n所有文章生成完成！")
        
    except Exception as e:
        print(f"程序运行出错: {str(e)}")

if __name__ == "__main__":
    main()
