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

def generate_title(topic):
    """生成吸引人的标题"""
    try:
        prompt = f"""请为主题"{topic}"创作一个标题，要求：
        1. 长度控制在15字以内
        2. 不使用标点符号
        3. 符合传播学原理 如话题性 新闻性 时效性
        4. 使用吸引人的动词或名词开头
        5. 避免使用虚词和形容词
        只需要返回标题文本，不需要其他内容。"""
        

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "你是一个专业的新媒体标题创作专家"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=150
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"生成标题时出错: {str(e)}")
        return None

def generate_section_content(topic, section_number):
    """生成单个章节的内容"""
    try:
        prompts = {
            1: f"""为主题'{topic}'写一个背景与动机章节，要求：
               - 介绍成长环境、家庭背景等
               - 字数800-1200字
               - 分3-4个自然段
               - 不要自行添加标题
               - 段落之间要有逻辑连接
               - 结尾不要做总结""",
            2: f"""为主题'{topic}'写一个性格与思维模式章节，要求：
               - 分析性格特点和处事方式
               - 字数800-1200字
               - 分3-4个自然段
               - 不要自行添加标题
               - 段落之间要有逻辑连接
               - 结尾不要做总结""",
            3: f"""为主题'{topic}'写一个人生历程与成就章节，要求：
               - 讲述重要事件和贡献
               - 字数800-1200字
               - 分3-4个自然段
               - 不要自行添加标题
               - 段落之间要有逻辑连接
               - 结尾不要做总结""",
            4: f"""为主题'{topic}'写一个社会关系与影响力章节，要求：
               - 分析社会影响和历史评价
               - 字数800-1200字
               - 分3-4个自然段
               - 不要自行添加标题
               - 段落之间要有逻辑连接
               - 结尾不要做总结""",
            5: f"""为主题'{topic}'写一个文化属性与价值观章节，要求：
               - 探讨个人价值观和思维模式
               - 字数800-1200字
               - 分3-4个自然段
               - 不要自行添加标题
               - 段落之间要有逻辑连接
               - 最后一段进行总结升华，可以使用一句金句点题""",
        }
        

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "你是一个专业的传记作家"},
                {"role": "user", "content": prompts[section_number]}
            ],
            temperature=0.6,
            max_tokens=4000
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"生成章节 {section_number} 时出错: {str(e)}")
        return None

def get_unsplash_images(keyword, count=3):
    """获取Unsplash图片"""
    try:
        headers = {
            'Authorization': f'Client-ID {os.getenv("UNSPLASH_ACCESS_KEY")}'
        }
        params = {
            'query': keyword,
            'per_page': count,
            'orientation': 'landscape'
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
            
        return [photo['urls']['regular'] for photo in data['results'][:count]]
    except Exception as e:
        print(f"获取图片时出错: {str(e)}")
        return []

def format_article(title, sections, images, topic):
    """格式化文章内容"""
    article = f"# {title}\n\n"
    

    section_titles = [
        "第一章 背景与动机",
        "第二章 性格与思维模式",
        "第三章 人生历程与成就",
        "第四章 社会关系与影响力",
        "第五章 文化属性与价值观"
    ]
    
    # 需要配图的章节（2，3，4号章节）
    image_sections = {1, 2, 3}
    
    for i, (section_title, content) in enumerate(zip(section_titles, sections), 1):
        article += f"## {section_title}\n\n"
        if i in image_sections and images:
            img_index = i - 1
            if img_index < len(images):
                article += f"![{topic}的图片展示{i}]({images[img_index]})\n\n"
        article += f"{content}\n\n"
    
    # 添加文章结尾的总结升华部分
    epilogue = generate_epilogue(topic)
    if epilogue:
        article += f"\n## 结语\n\n{epilogue}\n"
    
    return article

def generate_epilogue(topic):
    """生成文章结尾的总结升华部分"""
    try:
        prompt = f"""请为主题"{topic}"写一段200字左右的总结升华，要求：
        1. 提炼核心启示或价值观
        2. 使用一句经典名言或金句点题
        3. 体现历史意义和现代价值
        4. 语言优美，富有哲理性
        5. 结构完整，首尾呼应
        只需要返回内容，不要加标题。"""
        

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "你是一个擅长文章升华总结的作家"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"生成结语时出错: {str(e)}")
        return None

def validate_article(content):
    """验证文章格式和内容"""
    try:
        sections = content.split('##')
        if len(sections) != 6:  # 标题 + 5个章节
            print("警告：章节数量不正确")
            return False
            

        # 检查每个章节的字数
        for i, section in enumerate(sections[1:], 1):  # 跳过标题
            text = section.split('\n', 1)[1]  # 去掉标题行
            text = text.replace('![', '').replace(']', '')  # 去掉图片标记
            word_count = len(text.strip())
            if word_count < 800 or word_count > 1200:
                print(f"警告：第{i}章节字数不符合要求（当前{word_count}字）")
                return False
                
        # 检查格式一致性
        for section in sections[1:]:
            if "总结" in section or "结语" in section or "结论" in section:
                if "第五章" not in section:  # 只允许最后一章有总结
                    print("警告：非结尾章节包含总结性语言")
                    return False
                    
        return True
    except Exception as e:
        print(f"验证文章格式时出错: {str(e)}")
        return False

def generate_article(topic):
    """生成完整文章"""
    # 生成标题
    title = generate_title(topic)
    if not title:
        return None
        

    # 生成各个章节
    sections = []
    for i in range(1, 6):
        content = generate_section_content(topic, i)
        if not content:
            return None
        sections.append(content)
        
    # 获取图片
    images = get_unsplash_images(topic, 3)
    
    # 组装文章
    article = format_article(title, sections, images, topic)
    
    # 验证文章
    if not validate_article(article):
        print("警告：文章格式验证失败")
    
    return article

def save_article(content, topic):
    """保存文章到文件"""
    output_dir = "generated_articles"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    

    safe_topic = "".join(x for x in topic[:20] if x.isalnum() or x in (' ', '-', '_')).strip()
    filename = f"{output_dir}/{safe_topic}.md"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"文章已保存到: {filename}")
        return True
    except Exception as e:
        print(f"保存文章时出错: {str(e)}")
        return False

def main():
    if len(sys.argv) != 2:
        print("使用方法: python blog_generator.py <输入文件名>")
        return
        

    input_file = sys.argv[1]
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            topics = [line.strip() for line in f if line.strip()]
            
        for topic in topics:
            print(f"\n开始生成关于 '{topic}' 的文章...")
            article = generate_article(topic)
            if article:
                save_article(article, topic)
                
        print("\n所有文章生成完成！")
        
    except Exception as e:
        print(f"程序运行出错: {str(e)}")

if __name__ == "__main__":
    main()
