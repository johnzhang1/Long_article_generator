import os
import re
import json
import asyncio
import datetime
import aiohttp
import random
import statistics
from typing import List, Dict, Any, Tuple, Optional
from openai import OpenAI
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from functools import lru_cache
from tenacity import retry, stop_after_attempt, wait_exponential
from dotenv import load_dotenv
import concurrent.futures
import time

# 加载环境变量
load_dotenv()

# 配置API客户端
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set")

api_base = os.getenv('OPENAI_API_BASE', 'https://api.openai.com/v1')
api_type = os.getenv('OPENAI_API_TYPE', 'openai')

if api_type == 'azure':
    client = OpenAI(
        api_key=api_key,
        base_url=f"{api_base}/openai/deployments/gpt-35-turbo",
        api_version=os.getenv('OPENAI_API_VERSION', '2023-05-15'),
        default_headers={"api-key": api_key}
    )
else:
    # 处理base_url
    if api_base.endswith('/'):
        api_base = api_base[:-1]
    if not api_base.endswith('/v1'):
        api_base = f"{api_base}/v1"
    
    print(f"Using API base URL: {api_base}")
    
    client = OpenAI(
        api_key=api_key,
        base_url=api_base
    )

UNSPLASH_ACCESS_KEY = os.getenv('UNSPLASH_ACCESS_KEY')
EXA_API_KEY = os.getenv('EXA_API_KEY')  # 用于Exa AI搜索的API密钥

# 创建线程池
thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=4)

# 创建异步会话
async def get_aiohttp_session():
    if not hasattr(get_aiohttp_session, 'session'):
        get_aiohttp_session.session = aiohttp.ClientSession()
    return get_aiohttp_session.session

# 缓存配置
CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

@lru_cache(maxsize=100)
def get_cached_response(cache_key: str) -> Optional[dict]:
    """从缓存获取响应"""
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.json")
    if os.path.exists(cache_file):
        if time.time() - os.path.getmtime(cache_file) < 3600:  # 1小时缓存
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    return None

def save_to_cache(cache_key: str, data: dict):
    """保存响应到缓存"""
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.json")
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)

class ArticleGenerator:
    def __init__(self):
        self.topic = ""
        self.keywords = []
        self.search_results = []
        self.keyword_urls = {}  # 存储关键词和URL的映射
        self.outline = {}
        self.content_sections = []
        self.images = []
        self.title = ""
        self.processed_info = ""
        self.total_words = 0
        self.unsplash_access_key = os.getenv('UNSPLASH_ACCESS_KEY')
        if not self.unsplash_access_key:
            raise ValueError("UNSPLASH_ACCESS_KEY environment variable not set")
        self.image_cache = {}
        self.used_image_ids = set()  # 用于追踪已使用的图片ID
        
        # 添加写作风格配置
        self.writing_style = """
写作风格组合：
- 10% Yuval Noah Harari：宏大叙事、跨学科视角、历史演化
- 20% Scott Adams：直观解析、系统思维、幽默讽刺
- 20% Michio Kaku：科学严谨、前瞻视野、通俗易懂
- 10% Toni Morrison：细腻描写、深度洞察、情感共鸣
- 10% 马克吐温：诙谐幽默、辛辣讽刺、生动形象
- 5% 和菜头：理性思考、生活感悟、简洁明快
- 15% 钱钟书：博学多识、妙语连珠、旁征博引

写作特征要求：
1. 具象类比：用生动形象阐释抽象概念
2. 对话表达：直接用"你"与读者交流
3. 结构布局：问题/观点-论述-结论
4. 趣味呈现：巧妙植入诙谐元素
5. 疑问预答：提前回应可能困惑
6. 实例说明：结合具体应用场景
7. 引导思考：以设问代替直接解答
"""

    async def clean_text(self, text: str) -> str:
        """清理文本，移除HTML标签、多余空白等"""
        # 使用BeautifulSoup清理HTML
        if bool(BeautifulSoup(text, "html.parser").find()):
            soup = BeautifulSoup(text, 'html.parser')
            text = soup.get_text()
        
        # 清理其他格式
        text = re.sub(r'https?://\S+', '', text)  # 移除URL
        text = re.sub(r'\s+', ' ', text)  # 规范化空白
        text = re.sub(r'[^\w\s\u4e00-\u9fff.,!?，。！？]', '', text)  # 保留中英文字符和基本标点
        return text.strip()

    async def search_web(self, query: str) -> List[Dict[str, str]]:
        """使用Exa AI进行网络搜索"""
        if not EXA_API_KEY:
            print("警告：EXA_API_KEY未设置，搜索功能将不可用")
            return []

        headers = {
            "x-api-key": EXA_API_KEY,
            "accept": "application/json",
            "content-type": "application/json"
        }

        try:
            url = "https://api.exa.ai/api/search"  # 修正API端点
            data = {
                "query": query,
                "num_results": 10,
                "start_published_date": "2020-01-01",
                "include_domains": ["wikipedia.org", "zhihu.com", "baidu.com"],
                "exclude_domains": ["twitter.com", "facebook.com"],
                "language": "zh",
                "summary_length": 3,
                "highlights_per_url": 5
            }
            
            print(f"\n发送搜索请求: {url}")
            print(f"搜索关键词: {query}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data, timeout=30) as response:
                    if response.status != 200:
                        print(f"搜索请求失败，状态码: {response.status}")
                        print(f"错误响应: {await response.text()}")
                        return []
                    
                    results = await response.json()
            
            processed_results = []
            if "results" in results:
                for doc in results["results"]:
                    # 提取高亮片段
                    highlights = []
                    if "highlights" in doc:
                        highlights = [h["text"] for h in doc["highlights"]]
                    elif "summary" in doc:
                        highlights = [doc["summary"]]
                    
                    # 合并高亮片段作为摘要
                    snippet = " ... ".join(highlights) if highlights else doc.get("text", "")[:500]
                    
                    result = {
                        "title": doc.get("title", ""),
                        "snippet": snippet,
                        "url": doc.get("url", ""),
                        "score": doc.get("relevance_score", 1.0),
                        "publish_date": doc.get("published_date", "")
                    }
                    
                    processed_results.append(result)
                    print(f"\n找到相关文章: {result['title']}")
                    print(f"链接: {result['url']}")
            
            return processed_results[:5]  # 只返回最相关的5个结果
            
        except Exception as e:
            print(f"\n搜索请求出错: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"错误响应: {await e.response.text()}")
            return []

    async def generate_keywords(self, topic: str) -> List[str]:
        """生成搜索关键词"""
        prompt = f"""请为以下主题生成5个最相关的关键词，要求：
1. 关键词应该准确反映主题的核心内容
2. 关键词应该有助于搜索相关信息
3. 直接输出关键词，用逗号分隔

主题：{topic}"""
        
        try:
            response = await self.call_openai(prompt)
            keywords = [kw.strip() for kw in response.split(',')]
            return keywords[:5]  # 确保只返回5个关键词
        except Exception as e:
            print(f"生成关键词出错: {str(e)}")
            return [topic]  # 如果出错，至少返回主题本身作为关键词

    async def process_search_results(self, results: List[Dict[str, str]]) -> str:
        """处理和整理搜索结果"""
        if not results:
            return ""
            
        # 合并所有搜索结果的文本
        combined_text = "\n".join([
            f"标题：{result['title']}\n内容：{result['snippet']}\n相关度：{result['score']}"
            for result in results
        ])
        
        # 清理和整理文本
        cleaned_text = await self.clean_text(combined_text)
        
        # 使用AI总结和组织信息
        prompt = f"""请对以下搜索结果进行总结和组织，生成一份结构化的信息摘要：

{cleaned_text}

要求：
1. 提取最重要和最相关的信息
2. 去除重复内容
3. 保持客观性
4. 确保信息的准确性和可信度
5. 保留重要的数据和引用信息"""

        try:
            summary = await self.call_openai(prompt)
            return summary
        except Exception as e:
            print(f"处理搜索结果出错: {str(e)}")
            return cleaned_text

    async def create_outline(self, topic: str, processed_info: str) -> Dict[str, str]:
        """创建文章大纲"""
        prompt = f"""请根据以下信息创建一个详细的5部分文章大纲：

主题：{topic}
参考信息：{processed_info}

要求：
1. 每个部分必须详尽深入，确保生成内容至少2000字
2. 内容要专业、深入、观点新颖
3. 结构要清晰、逻辑性强，层次分明
4. 每部分内容要有明确的重点和论述方向
5. 确保内容的连贯性和完整性
6. 适当引用数据、案例和研究支持论点
7. 避免泛泛而谈，深入挖掘主题内涵

输出格式：
p1=[第1部分内容要点，包含3-4个重要论述方向，每个方向配有具体论述要点]
p2=[第2部分内容要点，包含3-4个重要论述方向，每个方向配有具体论述要点]
p3=[第3部分内容要点，包含3-4个重要论述方向，每个方向配有具体论述要点]
p4=[第4部分内容要点，包含3-4个重要论述方向，每个方向配有具体论述要点]
p5=[第5部分内容要点，包含3-4个重要论述方向，每个方向配有具体论述要点]"""

        try:
            response = await self.call_openai(prompt)
            outline = {}
            lines = response.strip().split('\n')
            
            # 定义每个部分的类型和特点
            section_types = {
                'p1': ['背景', '探讨历史渊源、时代背景和发展脉络'],
                'p2': ['特征', '分析核心特点、独特价值和关键要素'],
                'p3': ['成就', '阐述重要贡献、突破创新和影响力'],
                'p4': ['影响', '评估历史意义、现实价值和未来启示'],
                'p5': ['启示', '总结深层启发、时代意义和未来展望']
            }
            
            for line in lines:
                if '=' in line:
                    key, content = line.split('=', 1)
                    key = key.strip()
                    content = content.strip()
                    if key in section_types:
                        # 为每个部分生成引人入胜的标题
                        section_title = await self.generate_section_title(
                            section_types[key][0],
                            content,
                            section_types[key][1]
                        )
                        outline[key] = content
                        outline[f'z{key[1]}'] = section_title  # 使用z1-z5作为标题键名
            
            return outline
        except Exception as e:
            print(f"创建大纲出错: {str(e)}")
            return {}

    async def generate_section_title(self, section_type: str, content_brief: str, section_feature: str) -> str:
        """生成引人入胜的二级标题
        
        section_type: 段落类型（背景/特征/成就/影响）
        content_brief: 段落主要内容概述
        section_feature: 段落特点
        """
        prompt = f"""作为专业文案专家，请为文章章节创作一个富有吸引力的二级标题，要求：

段落类型：{section_type}
段落特点：{section_feature}
内容概要：{content_brief}

标题要求：
1. 字数：4-15字
2. 不要使用"第X部分"、"标题"等机械性表述
3. 不使用标点符号
4. 体现本节核心观点
5. 具有引导性和故事性
6. 可以使用对偶、排比等修辞手法

根据段落类型的标题设计策略：
背景类：
- 乱世出英雄
- 科技变革的时代浪潮
- 旧秩序崩塌的黎明时分
- 互联网颠覆传统商业的新纪元

特征类：
- 逆境中的坚持者
- 用代码改变世界的理想主义
- 创新基因与颠覆式思维
- 在不可能中寻找机会

成就类：
- 改变世界格局的新物种
- 开创数字文明新纪元
- 重构产业链条的超级变革者
- 从车库到帝国的商业传奇

影响类：
- 未来已来只是分布不均
- 新时代的曙光已经照亮世界
- 变革浪潮中的引领者
- 数字化转型的先行者与布道者

启示类：
- 深度洞察未来的发展趋势
- 颠覆你对未来的认知
- 未来世界的惊人变化
- 未来已来，只是你没有注意

请直接输出标题，不要任何解释和标点符号。"""

        try:
            response = await self.call_openai(prompt)
            # 清理标题中可能的标点符号和空格
            title = re.sub(r'[^\w\u4e00-\u9fff]', '', response.strip())
            return title
        except Exception as e:
            print(f"生成二级标题出错: {str(e)}")
            return section_type

    async def generate_section_content(self, section_num: int, title: str, requirements: str, processed_info: str) -> str:
        """生成章节内容"""
        prompt = f"""作为专业内容创作者，请根据以下信息创作文章章节，严格遵循指定的写作风格和特征：

章节标题：{title}
内容要求：{requirements}
参考信息：{processed_info}

{self.writing_style}

创作要求：
1. 内容必须详尽深入，字数不少于2000字
2. 分析要专业、深入，观点要新颖独到
3. 每个观点都要有充分论述和具体例证
4. 确保内容的专业性、可读性和连贯性
5. 使用三级标题，格式为"{section_num}.x 标题内容"（x为小节序号，如"{section_num}.1 引言"）
   - 每个小节标题要简洁有力，4-10字为宜
   - 标题要体现该节核心内容
   - 序号格式统一，如 {section_num}.1、{section_num}.2 等
6. 避免泛泛而谈，深入挖掘主题内涵
7. 重要观点和数据必须注明来源，使用以下格式：
   - 观点引用：根据[来源名称]显示
   - 数据引用：xxx（数据来源：[来源名称]）
   - 直接引用：[来源名称]指出："引用内容"
8. 严格禁止在章节末尾添加任何形式的小结、总结、结语等内容
9. 适当引用专家观点、研究报告或权威数据
10. 直接从正文内容开始，不要重复输出主标题
11. 文章最后不要出现"总而言之"、"综上所述"等总结性语句

直接输出内容，不要包含任何额外说明。"""

        try:
            content = await self.call_openai(prompt)
            # 添加引用链接
            try:
                content = await self.search_and_add_citations(content)
            except Exception as e:
                print(f"为章节 {title} 添加引用时出错: {str(e)}")
            return content
        except Exception as e:
            print(f"生成第{section_num}部分内容出错: {str(e)}")
            return ""

    async def generate_title(self, topic: str, processed_info: str) -> str:
        """生成文章标题"""
        prompt = f"""作为专业文案专家，请为这篇文章创作一个吸引人的标题。

主题：{topic}
核心信息：{processed_info}

要求：
1. 字数控制在10-20字之间
2. 突出主题的核心价值和深度
3. 避免过度使用标点符号
4. 使用富有吸引力的表达方式
5. 体现专业性和思考深度

可以参考以下模式：
- [主题]对[领域]的深远影响
- [主题]如何改变了[领域]
- 深入解析[主题]的核心思想
- [主题]带给我们的启示
- [主题]的智慧与现代价值
- 从[主题]看[某个角度]

直接输出标题，不要任何解释。"""

        try:
            response = await self.call_openai(prompt)
            # 清理标题中可能的标点符号和多余空格
            title = re.sub(r'[^\w\u4e00-\u9fff]', '', response.strip())
            return title
        except Exception as e:
            print(f"生成标题出错: {str(e)}")
            return f"{topic}的深度解析"

    def chinese_to_arabic(self, cn_num: str) -> int:
        """将中文数字转换为阿拉伯数字"""
        CN_NUM = {
            '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
            '六': 6, '七': 7, '八': 8, '九': 9, '十': 10
        }
        return CN_NUM.get(cn_num, 0)

    def parse_outline(self, outline_text: str) -> Dict[str, str]:
        """解析大纲文本"""
        try:
            outline = {}
            lines = outline_text.split('\n')
            current_section = 0
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                if '大纲标题=' in line:
                    try:
                        # 从"第X部分"中提取数字，支持中文数字和阿拉伯数字
                        section_text = line[1]  # 获取"第"后面的字符
                        if section_text.isdigit():
                            current_section = int(section_text)
                        else:
                            current_section = self.chinese_to_arabic(section_text)
                            
                        if current_section == 0:
                            raise ValueError(f"无法识别的部分编号: {section_text}")
                            
                        title = line.split('=')[1].strip()
                        if not title:
                            raise Exception(f"第{current_section}部分标题为空")
                        outline[f'z{current_section}'] = title
                    except (IndexError, ValueError) as e:
                        print(f"解析标题行出错: {line}")
                        raise
                elif '编写要求=' in line:
                    try:
                        req = line.split('=')[1].strip()
                        if not req:
                            raise Exception(f"第{current_section}部分要求为空")
                        outline[f'p{current_section}'] = req
                    except (IndexError, ValueError) as e:
                        print(f"解析要求行出错: {line}")
                        raise
            
            # 验证是否有完整的5个部分
            for i in range(1, 6):
                if f'z{i}' not in outline or f'p{i}' not in outline:
                    missing = []
                    if f'z{i}' not in outline:
                        missing.append("标题")
                    if f'p{i}' not in outline:
                        missing.append("要求")
                    raise Exception(f"大纲格式错误：第{i}部分缺少{' 和 '.join(missing)}")
            
            return outline
        except Exception as e:
            print(f"解析大纲出错: {str(e)}")
            print(f"大纲文本:\n{outline_text}")
            raise

    async def generate_conclusion(self, title: str) -> str:
        """生成文章总结"""
        prompt = f"""作为专业内容创作者，请为文章《{title}》创作一个富有深度的总结，严格遵循指定的写作风格和特征：

{self.writing_style}

要求：
1. 总结核心观点（150字以内）
   - 运用具象类比
   - 使用生动形象的语言
   - 体现跨学科视角

2. 提炼关键启示（150字以内）
   - 采用对话式表达
   - 引导读者思考
   - 预答可能困惑

3. 以一段富有哲理的金句作为升华，要求：
   - 言简意赅，30-40字
   - 富有哲理性和启发性
   - 紧扣主题
   - 具有诗意美感
   - 能引发深度思考
   - 巧妙融入幽默元素

输出格式：
[核心观点]
xxx

[关键启示]
xxx

[主题升华]
xxx"""

        try:
            conclusion = await self.call_openai(prompt)
            return conclusion
        except Exception as e:
            print(f"生成总结出错: {str(e)}")
            return ""

    async def generate_intro(self, title: str) -> str:
        """生成文章导读"""
        try:
            prompt = f"""请为以下文章生成一段导读，严格遵循指定的写作风格和特征：
            
文章标题：{title}

{self.writing_style}
            
要求：
1. 200字左右
2. 说明为什么要阅读这篇文章
3. 点明文章的核心价值和主要收获
4. 语言要有吸引力，激发读者兴趣
5. 不要用"本文"、"文章"等字眼
6. 采用对话式表达，直接与读者交流
7. 巧妙植入一个引人深思的问题
"""
            
            intro = await self.call_openai(prompt)
            return intro
            
        except Exception as e:
            print(f"生成导读时出错: {str(e)}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def get_image(self, query: str, section_content: str = "") -> Optional[Dict[str, Any]]:
        """获取与内容相关的图片
        
        Args:
            query: 基础搜索词
            section_content: 章节内容，用于提取关键词优化搜索

        Returns:
            Dict containing image URL and metadata, or None if no suitable image found
        """
        try:
            # Check cache first
            cache_key = f"{query}_{section_content[:100]}"
            if cache_key in self.image_cache:
                cached_image = self.image_cache[cache_key]
                if cached_image.get('id') in self.used_image_ids:
                    del self.image_cache[cache_key]
                else:
                    return cached_image

            # 分析内容并优化搜索查询
            if section_content:
                search_prompt = f"""分析以下文本内容，生成最佳的图片搜索关键词组合。

要求：
1. 提取3-5个最具代表性的视觉关键词
2. 关键词必须具有明确的视觉特征
3. 结合具象和抽象概念
4. 考虑场景、情绪和氛围元素
5. 避免过于宽泛的词语
6. 考虑内容的时代背景和文化特征
7. 优先选择能形成具体画面的词语

文本内容：
{section_content[:1000]}

输出格式：
1. 主要视觉元素：（描述最核心的视觉内容）
2. 场景特征：（描述环境和背景特征）
3. 情绪氛围：（描述画面应传达的情感）
4. 风格建议：（描述图片的风格，如：现代、复古、科技感等）
5. 搜索关键词：（输出英文关键词，用空格分隔）"""

                analysis = await self.call_openai(search_prompt)
                
                # 解析分析结果
                keywords = ""
                style_tags = ""
                for line in analysis.split('\n'):
                    if line.startswith('搜索关键词：'):
                        keywords = line.split('：')[1].strip()
                    elif line.startswith('风格建议：'):
                        style = line.split('：')[1].strip()
                        # 转换风格描述为英文标签
                        style_prompt = f"将这个图片风格描述转换为2-3个英文风格标签（如modern, vintage, tech等）：{style}"
                        style_tags = await self.call_openai(style_prompt)

                query = f"{query} {keywords} {style_tags}"

            # 构建Unsplash API请求
            url = "https://api.unsplash.com/search/photos"
            headers = {"Authorization": f"Client-ID {self.unsplash_access_key}"}
            params = {
                "query": query,
                "per_page": 30,  # Get more results for better selection
                "content_filter": "high",
                "orientation": "landscape"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = data.get("results", [])
                        
                        if not results:
                            return None

                        # 计算每张图片的综合得分
                        scored_images = []
                        for img in results:
                            if img['id'] in self.used_image_ids:
                                continue
                                
                            score = 0
                            
                            # 1. 基础质量分数 (0-30分)
                            quality_score = min(img['likes'] / 50, 30)  # 最高30分
                            score += quality_score
                            
                            # 2. 图片尺寸适合度 (0-20分)
                            width, height = img['width'], img['height']
                            ratio = width / height
                            if 1.3 <= ratio <= 1.8:  # 黄金比例附近
                                score += 20
                            elif 1.0 <= ratio <= 2.0:  # 可接受范围
                                score += 10
                                
                            # 3. 颜色分析 (0-20分)
                            if img.get('color'):  # 颜色和谐度
                                # 避免过于极端的颜色
                                color = img['color'].lstrip('#')
                                r, g, b = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
                                color_variance = statistics.variance([r, g, b])
                                if 1000 <= color_variance <= 5000:  # 适中的颜色变化
                                    score += 20
                                elif color_variance < 8000:  # 可接受的颜色变化
                                    score += 10
                                    
                            # 4. 内容相关性分数 (0-30分)
                            description = img.get('description', '') or img.get('alt_description', '')
                            tags = [tag['title'] for tag in img.get('tags', [])]
                            
                            relevance_prompt = f"""评估图片描述与内容的相关性（0-30分）。

图片描述：{description}
图片标签：{', '.join(tags)}

内容主题：{query}
内容摘要：{section_content[:200] if section_content else ''}

评分标准：
1. 主题相关性 (0-10分)
2. 情感氛围匹配 (0-10分)
3. 视觉元素匹配 (0-10分)

只返回最终分数（0-30的整数）"""

                            try:
                                relevance_score = int(await self.call_openai(relevance_prompt))
                                score += relevance_score
                            except (ValueError, TypeError):
                                score += 15  # 默认中等相关性分数
                                
                            scored_images.append({
                                'data': img,
                                'score': score
                            })
                            
                        if not scored_images:
                            return None
                            
                        # 按分数排序并选择最佳图片
                        scored_images.sort(key=lambda x: x['score'], reverse=True)
                        best_image = scored_images[0]['data']
                        
                        # 记录已使用的图片ID
                        self.used_image_ids.add(best_image['id'])
                        
                        # 构建返回数据
                        image_data = {
                            'id': best_image['id'],
                            'url': best_image['urls']['regular'],
                            'thumb': best_image['urls']['thumb'],
                            'description': best_image.get('description', '') or best_image.get('alt_description', ''),
                            'author': best_image['user']['name'],
                            'author_url': best_image['user']['links']['html'],
                            'download_url': best_image['links']['download'],
                            'score': scored_images[0]['score']
                        }
                        
                        # 缓存结果
                        self.image_cache[cache_key] = image_data
                        return image_data
                        
            return None
                        
        except Exception as e:
            print(f"Error in get_image: {str(e)}")
            return None

    async def search_and_add_citations(self, text: str) -> str:
        """搜索并添加引用链接，使用 Markdown 链接格式"""
        # 识别需要引用的内容类型
        citation_patterns = {
            'data': r'（数据来源：\[(.*?)\]）',  # 数据来源引用
            'quote': r'\[(.*?)\]指出：“(.*?)”',  # 直接引用
            'claim': r'根据\[(.*?)\]显示',  # 观点引用
        }
        
        # 为每种类型的内容添加引用
        for citation_type, pattern in citation_patterns.items():
            matches = re.finditer(pattern, text)
            for match in matches:
                if citation_type == 'data':
                    source_name = match.group(1)
                    full_match = match.group(0)
                elif citation_type == 'quote':
                    source_name = match.group(1)
                    quote_content = match.group(2)
                    full_match = match.group(0)
                elif citation_type == 'claim':
                    source_name = match.group(1)
                    full_match = match.group(0)
                
                try:
                    # 使用Exa搜索相关内容
                    search_query = f"{source_name} {citation_type}"
                    if citation_type == 'quote':
                        search_query = f"{source_name} {quote_content}"
                    
                    search_results = await self.search_web(search_query)
                    if search_results:
                        # 选择最相关的结果
                        best_result = max(search_results, key=lambda x: x.get('score', 0))
                        # 根据不同类型构建新的引用文本
                        if citation_type == 'data':
                            new_text = f"（数据来源：[{source_name}]({best_result['url']})）"
                        elif citation_type == 'quote':
                            new_text = f'[{source_name}]({best_result["url"]})指出：“{quote_content}”'
                        else:  # claim
                            new_text = f"根据[{source_name}]({best_result['url']})显示"
                        
                        text = text.replace(full_match, new_text, 1)
                except Exception as e:
                    print(f"为{full_match}添加引用时出错: {str(e)}")
                    continue
        
        return text

    def format_article(self) -> str:
        """格式化文章内容"""
        formatted_content = []
        
        # 添加文章标题
        formatted_content.append(f"# {self.title}\n")
        
        # 添加导读
        if hasattr(self, 'intro') and self.intro:
            formatted_content.append(f"## 导读\n\n{self.intro}\n")
        
        # 添加正文内容
        formatted_content.extend(self.content_sections)
        
        # 添加总结
        if hasattr(self, 'conclusion') and self.conclusion:
            formatted_content.append(f"## 总结\n\n{self.conclusion}\n")
        
        # 合并所有内容
        return "\n".join(formatted_content)

    async def translate_and_format_citation(self, text: str, url: str) -> str:
        """翻译非中文引用并格式化引用"""
        if not re.search(r'[\u4e00-\u9fff]', text):  # 如果不包含中文
            prompt = f"""请将以下英文翻译成中文，保持专业性和准确性：
            {text}"""
            try:
                translated = await self.call_openai(prompt)
                return f"{translated} [原文]({url})"
            except Exception as e:
                print(f"翻译引用文本时出错: {str(e)}")
                return f"{text} [原文]({url})"
        return f"{text} [来源]({url})"

    def log_progress(self, message: str, is_important: bool = False):
        """输出进度信息，只显示重要信息"""
        if is_important:
            print(message)

    async def call_openai(self, prompt: str, is_main_content: bool = False) -> str:
        """调用OpenAI API
        
        Args:
            prompt: 提示词
            is_main_content: 是否是主要内容生成（标题、大纲、章节内容、总结），如果是则使用chatgpt-4o-latest，否则使用gpt-4o-mini
        """
        try:
            model = "chatgpt-4o-latest" if is_main_content else "gpt-4o-mini"
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=4000
                )
            )
            print(f"调用参数: prompt={prompt}, model={model}")
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"OpenAI API调用出错: {str(e)}")
            print(f"调用参数: prompt={prompt}, model={model}")
            raise

    async def generate_article(self, topic: str, output_file: str) -> None:
        """生成完整文章的主流程"""
        try:
            print(f"开始处理主题: {topic}")
            self.topic = topic
            
            # 1. 生成关键词
            print("正在生成关键词...")
            self.keywords = await self.generate_keywords(topic)
            print(f"生成的关键词: {self.keywords}")
            
            # 2. 搜索相关信息
            print("正在搜索相关信息...")
            for keyword in self.keywords:
                results = await self.search_web(f"{topic} {keyword}")
                self.search_results.extend(results)
            
            # 3. 处理搜索结果
            print("正在处理搜索结果...")
            self.processed_info = await self.process_search_results(self.search_results)
            
            # 4. 生成标题
            print("正在生成标题...")
            self.title = await self.generate_title(self.topic, self.processed_info)
            print(f"已生成标题: {self.title}")
            
            # 5. 创建大纲
            print("正在创建大纲...")
            self.outline = await self.create_outline(self.topic, self.processed_info)
            print("大纲创建完成")
            
            # 6. 生成文章内容
            print("正在生成文章内容...")
            article_parts = []
            
            # 添加标题
            article_parts.append(f"# {self.title}\n\n")
            
            # 添加元信息
            current_time = datetime.datetime.now().strftime("%Y-%m-%d")
            article_parts.append(f"作者：玄清\n")
            article_parts.append(f"时间：{current_time}\n")
            article_parts.append(f"关键词：{', '.join(self.keywords)}\n\n")
            
            # 生成导读
            print("正在生成导读...")
            intro = await self.generate_intro(self.title)
            article_parts.append(intro + "\n\n")
            
            self.total_words = len(intro)
            
            # 生成每个章节的内容
            async def generate_section(section_num: int) -> dict:
                section_key = f'p{section_num}'
                title_key = f'z{section_num}'
                
                if section_key not in self.outline:
                    raise Exception(f"大纲中缺少第{section_num}部分的内容要求")
                
                section_title = self.outline.get(title_key, f'第{section_num}部分')
                section_requirements = self.outline[section_key]
                
                # 生成内容
                content = await self.generate_section_content(
                    section_num,
                    section_title,
                    section_requirements,
                    self.processed_info
                )
                
                # 统计字数
                section_words = len(content)
                self.total_words += section_words
                print(f"第{section_num}部分完成，字数：{section_words}")
                
                # 获取配图
                image_data = await self.get_image(section_title, content)
                
                return {
                    'number': section_num,
                    'title': section_title,
                    'content': content,
                    'image': image_data
                }
            
            # 并行生成所有章节
            sections = await asyncio.gather(*[generate_section(i) for i in range(1, 6)])
            
            # 按章节顺序组装文章
            sections.sort(key=lambda x: x['number'])
            for section in sections:
                # 添加章节标题
                article_parts.append(f"\n## {section['number']}. {section['title']}\n\n")
                
                # 添加配图（如果有）
                if section['image']:
                    article_parts.append(f"![{section['title']}]({section['image']['url']})\n\n")
                
                # 添加章节内容
                article_parts.append(f"{section['content']}\n\n")
            
            # 生成总结
            print("正在生成总结...")
            conclusion = await self.generate_conclusion(self.title)
            article_parts.append(f"\n## 总结与展望\n\n{conclusion}\n")
            
            # 添加引用链接
            article_text = ''.join(article_parts)
            formatted_article = await self.search_and_add_citations(article_text)
            
            # 保存文章
            print("正在保存文章...")
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(formatted_article)
            
            print(f"文章已生成并保存到: {output_file}")
            print(f"总字数：{self.total_words}")
            
        except Exception as e:
            print("生成文章时出错:", str(e))
            print("详细错误信息:")
            import traceback
            print(traceback.format_exc())
            raise

async def main():
    generator = ArticleGenerator()
    
    # 读取主题列表
    with open('test.md', 'r', encoding='utf-8') as f:
        topics = [line.strip() for line in f if line.strip()]
    
    # 为每个主题生成文章
    for i, topic in enumerate(topics, 1):
        output_file = f"generated_articles/article_{i}_{topic}.md"
        await generator.generate_article(topic, output_file)
        print(f"文章已生成并保存到: {output_file}")

def generate_long_article(input_file):
    """
    生成长文的主函数
    :param input_file: 输入文件路径
    :return: None
    """
    # 读取输入文件
    with open(input_file, 'r', encoding='utf-8') as f:
        topic = f.read().strip()

    # 创建输出目录
    os.makedirs('generated_articles', exist_ok=True)
    
    # 生成文章
    article = ArticleGenerator()
    asyncio.run(article.generate_article(topic, f"generated_articles/article_{topic}.md"))

if __name__ == "__main__":
    asyncio.run(main())
