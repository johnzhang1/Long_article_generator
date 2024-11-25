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

def get_writing_style_prompt():
    """获取混合写作风格的提示"""
    return """请在写作时融合以下风格特点：
    
    - 宏大叙事与微观细节的结合：用人类进化和历史视角切入个人故事，展现个体与时代的关联。将个人故事放在更宏大的历史与社会背景下审视。
    
    - 犀利观察与幽默感：用略带戏谑的笔触描绘人性，善于发现生活中的荒诞与智慧。将复杂的概念用简单有趣的方式呈现，并揭示其中的深层逻辑。
    
    - 科学想象与人文关怀：将前沿科技概念与日常生活巧妙结合，用通俗易懂的比喻解释复杂现象。展现技术与人性的交织。
    
    - 细腻笔触与诗意表达：通过细节描写展现人物内心，用富有韵律感的语言营造意境，让抽象概念具象化。
    
    - 犀利理性与人文关怀：以理性的视角剖析现象背后的本质，但不失温度与同理心。将观察与思考融入生动的场景。
    
    - 博学与机智：适时插入典故与引用，但要用俏皮活泼的方式呈现。在严肃话题中也不失诙谐，让知识性与趣味性并存。

    写作要求：
    1. 自然流畅地融合这些风格，不要生硬堆砌
    2. 保持语言的优美与可读性
    3. 在不同段落中灵活运用不同的风格特点
    4. 用富有画面感的描写取代抽象论述
    5. 让严肃话题也能产生趣味性
    6. 在叙述中自然融入哲理性思考"""

def generate_title(topic):
    """生成吸引人的标题"""
    try:
        prompt = f"""为主题"{topic}"创作一个标题，要求：

1. 标题模式（从以下模式中选择最适合的1-2个结合）：
   - 思考类：揭示深层洞察，如"你和XX的差距，不只是XX"
   - 反思类：触发自我反思，如"你不是XX，是XX"
   - 悬念类：引发好奇心，如"为什么有的人XX，却能XX？"
   - 对立类：制造张力，如"当我反对XX时，我在反对什么？"
   - 真相类：揭示内幕，如"90%的人都错过的XX真相"
   - 规律类：总结规律，如"顶级XX的三个关键底层逻辑"
   - 共鸣类：引发共鸣，如"你的XX，正在XX"
   
2. 写作要求：
   - 字数：15字以内
   - 不使用标点符号（问号除外）
   - 使用强力动词或名词开头
   - 制造张力或反差
   - 避免虚词和过度形容
   
3. 情感触发：
   - 好奇心：引发探索欲
   - 焦虑感：暴露现状问题
   - 希望感：暗示解决方案
   - 认同感：引发情感共鸣
   
4. 表达结构（三选一）：
   A. [核心概念]的[惊人真相]
   B. 为什么[普遍现象]却[反常结果]
   C. [行为/现象]正在[意想不到的影响]

请根据主题"{topic}"的特点，选择最适合的模式和结构。只返回标题文本，不需要解释。"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "你是一位深谙用户心理的新媒体标题专家，擅长创作能引发思考和情感共鸣的标题"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=150
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"生成标题时出错: {str(e)}")
        return None

def generate_introduction(topic):
    """生成文章引言"""
    try:
        style_prompt = get_writing_style_prompt()
        prompt = f"""为主题"{topic}"创作一段引言，要求：
        1. 字数300-500字
        2. 以一个跨越时空的宏大场景开篇
        3. 用富有诗意的笔触描绘细节
        4. 巧妙融入科技与人文的思考
        5. 以略带戏谑的笔触切入主题
        6. 适时点缀机智的文化引用
        
        {style_prompt}
        
        只需要返回引言内容，不需要其他内容。"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "你是一位融合了历史学家的宏大视野、作家的文学功底、科学家的想象力、以及文化评论家的洞察力的写作大师"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"生成引言时出错: {str(e)}")
        return None

def generate_section_content(topic, section_number, previous_content=None):
    """生成单个章节的内容，包含小节结构"""
    try:
        style_prompt = get_writing_style_prompt()
        
        # 标准化的章节结构
        section_structures = {
            1: {
                "title": "1. 背景与起源",
                "subsections": [
                    "1.1 历史渊源",
                    "1.2 发展脉络",
                    "1.3 关键转折"
                ]
            },
            2: {
                "title": "2. 核心要素",
                "subsections": [
                    "2.1 基本构成",
                    "2.2 运作机制",
                    "2.3 特征分析"
                ]
            },
            3: {
                "title": "3. 创新突破",
                "subsections": [
                    "3.1 技术创新",
                    "3.2 模式创新",
                    "3.3 应用创新"
                ]
            },
            4: {
                "title": "4. 影响分析",
                "subsections": [
                    "4.1 主要影响",
                    "4.2 发展机遇",
                    "4.3 潜在挑战"
                ]
            },
            5: {
                "title": "5. 未来展望",
                "subsections": [
                    "5.1 发展方向",
                    "5.2 前景预测",
                    "5.3 行动建议"
                ]
            }
        }

        # 获取当前章节结构
        current_section = section_structures[section_number]
        section_title = current_section["title"]
        subsections = current_section["subsections"]
        
        # 构建上下文信息
        context = ""
        if previous_content and section_number > 1:
            context = f"""请注意上一章节的关键信息：
            {previous_content[:200]}...
            请确保本章节内容与上下文自然衔接。"""

        # 修改提示词，确保内容符合要求
        prompt = f"""为主题'{topic}'写作'{section_title}'章节，要求：
        
        1. 严格按照以下{len(subsections)}个三级标题组织内容：
        {chr(10).join(subsections)}
        
        2. 内容要求：
        - 每个三级标题下的内容500-600字
        - 各部分内容要有逻辑递进关系
        - 使用优美的过渡句连接各部分
        - 确保内容自然流畅，深入浅出
        - 避免使用任何总结性词语（如"总结"、"结语"、"结论"等）
        - 使用具体案例和数据支撑观点
        
        3. 写作风格：
        {style_prompt}
        
        4. 上下文联系：
        {context}
        
        请直接返回内容，无需额外说明。"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "你是一位融合了历史学家的宏大视野、作家的文学功底、科学家的想象力、以及文化评论家的洞察力的写作大师"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
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
    
    # 添加引言
    introduction = sections[0]
    article += f"## 引言\n\n{introduction}\n\n"

    section_titles = [
        "第一章 背景与动机",
        "第二章 性格与思维模式",
        "第三章 人生历程与成就",
        "第四章 社会关系与影响力",
        "第五章 文化属性与价值观"
    ]
    
    # 需要配图的章节（2，3，4号章节）
    image_sections = {1, 2, 3}
    
    previous_content = introduction
    for i, (section_title, content) in enumerate(zip(section_titles, sections[1:]), 1):
        # 添加章节过渡语
        if i > 1:
            transition = generate_transition(previous_content, section_title)
            article += f"{transition}\n\n"
            
        article += f"## {section_title}\n\n"
        if i in image_sections and images:
            img_index = i - 1
            if img_index < len(images):
                article += f"![{topic}的图片展示{i}]({images[img_index]})\n\n"
        article += f"{content}\n\n"
        previous_content = content
    
    # 添加文章结尾的总结升华部分
    epilogue = generate_epilogue(topic)
    if epilogue:
        article += f"\n## 结语\n\n{epilogue}\n"
    
    return article

def validate_article(content):
    """验证文章格式和内容"""
    try:
        sections = content.split('##')
        if len(sections) != 7:  # 标题 + 引言 + 5个章节
            print("警告：章节数量不正确")
            return False
            
        # 检查每个章节的字数和内容
        for i, section in enumerate(sections[2:], 2):  # 跳过标题和引言
            text = section.split('\n', 1)[1]  # 去掉标题行
            text = text.replace('![', '').replace(']', '')  # 去掉图片标记
            
            # 检查字数
            word_count = len(text.strip())
            if word_count < 800 or word_count > 1200:
                print(f"警告：第{i}章节字数不符合要求（当前{word_count}字）")
                return False
            
            # 检查不应出现的总结性词语
            if i < 6:  # 非结尾章节
                forbidden_words = [
                    "总结", "结语", "小结", "总的来说", "综上所述",
                    "参考文献", "引用", "Reference", "Bibliography",
                    "归纳", "概括", "小结一下", "总而言之",
                    "最后", "结论", "总结来看", "总的说来"
                ]
                for word in forbidden_words:
                    if word in text:
                        print(f"警告：第{i}章节中出现了不适合的总结性词语：{word}")
                        return False
                
            # 检查段落长度
            paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
            for p in paragraphs:
                if len(p) < 50:  # 段落太短
                    print("警告：存在过短的段落")
                    return False
                if len(p) > 800:  # 段落太长
                    print("警告：存在过长的段落")
                    return False
                    
        return True
    except Exception as e:
        print(f"验证文章格式时出错: {str(e)}")
        return False

def generate_transition(previous_content, next_section_title):
    """生成章节之间的过渡语"""
    try:
        prompt = f"""根据上一章节的内容：
        {previous_content[-200:]}
        
        为下一章节"{next_section_title}"创作一句简短的过渡语，要求：
        1. 20-40字
        2. 自然流畅地连接两个章节
        3. 点明下一章节的主题
        4. 避免使用总结性词语（如"总的来说"、"综上所述"等）
        5. 使用承上启下的连接方式
        只需要返回过渡语，不需要其他内容。"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "你是一个善于写作过渡语的作家，擅长用流畅自然的方式连接不同章节"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=100
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"生成过渡语时出错: {str(e)}")
        return ""

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

def generate_article(topic):
    """生成完整文章"""
    try:
        # 生成标题
        title = generate_title(topic)
        if not title:
            print("生成标题失败")
            return None

        # 生成引言
        introduction = generate_introduction(topic)
        if not introduction:
            print("生成引言失败")
            return None

        # 生成各个章节
        sections = []
        previous_content = introduction
        for i in range(1, 6):
            content = generate_section_content(topic, i, previous_content)
            if not content:
                print(f"生成第{i}章节失败")
                return None
            sections.append(content)
            previous_content = content

        # 生成结语
        epilogue = generate_epilogue(topic)
        if epilogue:
            sections.append(epilogue)
        
        # 获取图片
        images = get_unsplash_images(topic, 3)
        
        # 组装文章
        article = format_article(title, [introduction] + sections, images, topic)
        
        # 验证文章
        if not validate_article(article):
            print("警告：文章格式验证失败")
        
        return article
    except Exception as e:
        print(f"生成文章时出错: {str(e)}")
        return None

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
