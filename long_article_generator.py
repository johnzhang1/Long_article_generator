import os
import re
import json
import asyncio
import datetime
import aiohttp
import random
from typing import List, Dict, Any, Tuple, Optional
from openai import OpenAI
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from functools import lru_cache
from tenacity import retry, stop_after_attempt, wait_exponential
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置API客户端
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable not set")

client = OpenAI(
    base_url="https://api.gptsapi.net/v1",
    api_key=OPENAI_API_KEY,
    timeout=60.0,  # 增加超时时间
    max_retries=3  # 添加重试次数
)
UNSPLASH_ACCESS_KEY = os.getenv('UNSPLASH_ACCESS_KEY')
EXA_API_KEY = os.getenv('EXA_API_KEY')  # 用于Exa AI搜索的API密钥

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

    def clean_text(self, text: str) -> str:
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
        cleaned_text = self.clean_text(combined_text)
        
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
        prompt = f"""作为专业内容创作者，请根据以下信息创作文章章节：

章节标题：{title}
内容要求：{requirements}
参考信息：{processed_info}

创作要求：
1. 内容必须详尽深入，字数不少于2000字
2. 分析要专业、深入，观点要新颖独到
3. 每个观点都要有充分论述和具体例证
4. 确保内容的专业性、可读性和连贯性
5. 使用三级标题（###）组织内容，确保层次分明，标题格式为"{section_num}.1"、"{section_num}.2"等
6. 避免泛泛而谈，深入挖掘主题内涵
7. 重要观点必须注明引用出处，格式为：[作者/机构, 年份]
8. 引用的数据必须标注来源，格式为：（数据来源：xxx）
9. 不要在章节末尾添加小结或总结
10. 适当引用专家观点、研究报告或权威数据

直接输出内容，不要包含任何额外说明。"""

        try:
            content = await self.call_openai(prompt)
            # 添加引用链接
            try:
                content = await self.search_and_add_citations(content)
            except Exception as e:
                print(f"为章节 {title} 添加引用时出错: {str(e)}")
        
            return f"\n## {section_num}. {title}\n\n{content}\n"
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
        prompt = f"""作为专业内容创作者，请为文章《{title}》创作一个富有深度的总结，要求：

1. 总结核心观点（100字以内）
2. 提炼关键启示（100字以内）
3. 以一段富有哲理的金句作为升华，要求：
   - 言简意赅，20-30字
   - 富有哲理性和启发性
   - 紧扣主题
   - 具有诗意美感
   - 能引发深度思考

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
            prompt = f"""请为以下文章生成一段导读：
            文章标题：{title}
            
            要求：
            1. 200字左右
            2. 说明为什么要阅读这篇文章
            3. 点明文章的核心价值和主要收获
            4. 语言要有吸引力，激发读者兴趣
            5. 不要用"本文"、"文章"等字眼
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
                return self.image_cache[cache_key]

            # 从section内容中提取关键词来优化图片搜索
            if section_content:
                # 生成更精确的搜索查询
                search_prompt = f"""Analyze the following text and generate the best image search query.
                Requirements:
                1. Extract 3-5 most representative keywords that capture the core content
                2. Prioritize visually expressive terms
                3. Include both concrete and abstract concepts
                4. Avoid overly broad terms
                5. Consider emotional and atmospheric elements
                6. Format: return only English keywords, separated by spaces

                Text content:
                {section_content[:500]}...
                """
                
                enhanced_keywords = await self.call_openai(search_prompt)
                query = f"{query} {enhanced_keywords.strip()}"

            # 构建Unsplash API请求
            url = "https://api.unsplash.com/search/photos"
            headers = {"Authorization": f"Client-ID {self.unsplash_access_key}"}
            params = {
                "query": query,
                "per_page": 30,  # Get more results for better selection
                "orientation": "landscape",
                "content_filter": "high",
                "order_by": "relevant"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    response.raise_for_status()  # Raise exception for bad status codes
                    
                    data = await response.json()
                    if not data.get("results"):
                        print(f"No images found for query: {query}")
                        return None

                    # Filter and score images based on multiple criteria
                    scored_images = []
                    for img in data["results"]:
                        score = 0
                        # Relevancy score (if available)
                        score += img.get("relevancy_score", 0) * 3
                        # Likes indicate image quality
                        score += min(img.get("likes", 0) / 100, 5)
                        # Prefer images with descriptions
                        score += 2 if img.get("description") else 0
                        # Prefer images with focus on the subject
                        score += 1 if img.get("color") != "#FFFFFF" else 0
                        
                        scored_images.append((score, img))

                    # Sort by score and get top 5
                    top_images = sorted(scored_images, key=lambda x: x[0], reverse=True)[:5]
                    
                    if not top_images:
                        return None

                    # Randomly select one of the top images to add variety
                    selected_image = random.choice(top_images)[1]
                    
                    result = {
                        "url": selected_image["urls"]["regular"],
                        "description": selected_image.get("description", ""),
                        "author": selected_image["user"]["name"],
                        "author_url": selected_image["user"]["links"]["html"],
                        "download_url": selected_image["links"]["download"],
                    }

                    # Cache the result
                    self.image_cache[cache_key] = result
                    return result
                    
        except Exception as e:
            print(f"Error getting image: {str(e)}")
            return None

    async def search_and_add_citations(self, text: str) -> str:
        """搜索并添加引用链接，使用 Markdown 链接格式"""
        # 识别需要引用的内容类型
        citation_patterns = {
            'data': r'(\d+(?:\.\d+)?%|\d{3,}(?:万|亿)?)',  # 数据模式
            'quote': r'[""](.*?)[""]',  # 引用模式
            'claim': r'(研究表明|数据显示|报告指出|专家认为|调查发现|统计数据表明|根据.*?显示|据.*?统计)',  # 论证引用模式
        }
        
        # 为每种类型的内容添加引用
        for citation_type, pattern in citation_patterns.items():
            matches = re.finditer(pattern, text)
            for match in matches:
                matched_text = match.group()
                # 对于每个匹配项进行搜索
                search_query = matched_text
                if citation_type == 'data':
                    search_query = f"数据来源 {matched_text}"
                elif citation_type == 'quote':
                    search_query = f"原文引用 {matched_text}"
                elif citation_type == 'claim':
                    search_query = f"论证来源 {matched_text}"
                
                try:
                    # 使用Exa搜索相关内容
                    search_results = await self.search_web(search_query)
                    if search_results:
                        # 选择最相关的结果
                        best_result = max(search_results, key=lambda x: x.get('score', 0))
                        # 添加 Markdown 格式的引用链接
                        citation_text = f"{matched_text} [{best_result.get('title', '来源')}]({best_result['url']})"
                        text = text.replace(matched_text, citation_text, 1)
                except Exception as e:
                    print(f"为{matched_text}添加引用时出错: {str(e)}")
                    continue
        
        return text

    async def format_article_with_references(self, content: str) -> str:
        """在文章内容中添加所有类型的引用链接"""
        formatted_content = content
        
        # 1. 添加关键词引用
        for keyword in self.keywords:
            if keyword in self.keyword_urls:
                urls = self.keyword_urls[keyword]
                if urls:
                    best_url = max(urls, key=lambda x: x.get('relevance_score', 0))
                    formatted_content = formatted_content.replace(
                        keyword,
                        f"{keyword} [{best_url.get('title', '相关资料')}]({best_url['url']})",
                        1  # 只替换第一次出现
                    )
        
        # 2. 添加其他引用（数据、引用、论证等）
        try:
            formatted_content = await self.search_and_add_citations(formatted_content)
        except Exception as e:
            print(f"添加引用链接时出错: {str(e)}")
        
        return formatted_content

    async def format_article(self) -> str:
        """格式化文章内容"""
        try:
            current_time = datetime.datetime.now().strftime("%Y-%m-d")
            article_parts = []
            
            # 添加标题和元信息
            article_parts.append(f"# {self.title}\n\n")
            article_parts.append(f"作者：玄清\n")
            article_parts.append(f"时间：{current_time}\n")
            article_parts.append(f"关键词：{', '.join(self.keywords)}\n")
            article_parts.append(f"字数：{self.total_words}\n\n")
            
            # 添加正文内容
            seen_titles = set()  # 跟踪所有级别的标题
            section_counter = 1
            
            for section in self.content_sections:
                # 生成标准化的标题
                section_title = self.standardize_title(section['title'], seen_titles)
                seen_titles.add(section_title.lower())
                
                # 添加带编号的章节标题
                article_parts.append(f"\n## {section_counter}. {section_title}\n\n")
                
                # 处理子章节
                subsection_counter = 1
                content_lines = section['content'].split('\n')
                current_subsection = []
                
                for line in content_lines:
                    # 检查是否是子标题（以#开头或包含"章"、"节"等关键词）
                    if line.strip().startswith('#') or any(key in line for key in ['章', '节', '部分']):
                        # 先处理之前收集的内容
                        if current_subsection:
                            processed_content = self.process_section_content('\n'.join(current_subsection))
                            if processed_content:
                                article_parts.append(processed_content + '\n\n')
                            current_subsection = []
                        
                        # 处理子标题，统一使用 X.Y 格式
                        subsection_title = self.standardize_title(line.lstrip('#').strip(), seen_titles)
                        seen_titles.add(subsection_title.lower())
                        article_parts.append(f"### {section_counter}.{subsection_counter}. {subsection_title}\n\n")
                        subsection_counter += 1
                    else:
                        current_subsection.append(line)
                
                # 处理最后一个子章节的内容
                if current_subsection:
                    processed_content = self.process_section_content('\n'.join(current_subsection))
                    if processed_content:
                        article_parts.append(processed_content + '\n\n')
                
                section_counter += 1
            
            # 合并所有内容并添加引用
            full_content = ''.join(article_parts)
            formatted_content = await self.format_article_with_references(full_content)
            
            return formatted_content
            
        except Exception as e:
            print("生成文章时出错:", str(e))
            raise

    def standardize_title(self, title: str, seen_titles: set) -> str:
        """标准化标题，确保不重复"""
        base_title = re.sub(r'^[#\d\.\s]+', '', title).strip()
        base_title = re.sub(r'[：:](.*?)$', '', base_title)
        
        if base_title.lower() not in seen_titles:
            return base_title
        
        # 如果标题重复，添加区分词
        counter = 1
        while f"{base_title}（续{counter}）".lower() in seen_titles:
            counter += 1
        return f"{base_title}（续{counter}）"

    def process_section_content(self, content: str) -> str:
        """处理章节内容，移除总结性段落并规范化格式"""
        # 移除总结性段落
        lines = content.split('\n')
        filtered_lines = []
        skip_section = False
        
        for line in lines:
            # 检查是否包含总结性关键词
            if any(keyword in line.lower() for keyword in [
                '总结', '小结', '总的来说', '综上所述', '总而言之', 
                '结论', '结语', '小结', '总括', '概括来说'
            ]):
                skip_section = True
                continue
            
            if not skip_section:
                # 规范化列表格式为自然段
                if line.strip().startswith(('- ', '• ', '* ')):
                    line = line.strip()[2:]
                filtered_lines.append(line)
        
        # 合并相邻的短句为自然段
        processed_lines = []
        current_paragraph = []
        
        for line in filtered_lines:
            line = line.strip()
            if not line:
                if current_paragraph:
                    processed_lines.append(' '.join(current_paragraph))
                    current_paragraph = []
                processed_lines.append('')
            else:
                current_paragraph.append(line)
        
        if current_paragraph:
            processed_lines.append(' '.join(current_paragraph))
        
        return '\n'.join(processed_lines)

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
            article_parts.append(f"{intro}\n\n")
            
            self.total_words = len(intro)
            
            # 生成每个章节的内容
            for i in range(1, 6):
                print(f"正在生成第{i}部分...")
                section_key = f'p{i}'
                title_key = f'z{i}'
                
                if section_key not in self.outline:
                    raise Exception(f"大纲中缺少第{i}部分的内容要求")
                
                section_title = self.outline.get(title_key, f'第{i}部分')
                section_requirements = self.outline[section_key]
                
                # 生成内容
                content = await self.generate_section_content(
                    i,
                    section_title,
                    section_requirements,
                    self.processed_info
                )
                
                # 统计字数
                section_words = len(content)
                self.total_words += section_words
                print(f"第{i}部分完成，字数：{section_words}")
                
                # 获取并添加图片
                image_url = await self.get_image(section_title, content)
                if image_url:
                    article_parts.append(f"\n![{section_title}]({image_url['url']})\n\n")
                
                article_parts.append(content)
            
            # 生成总结
            print("正在生成总结...")
            conclusion = await self.generate_conclusion(self.title)
            article_parts.append(f"\n## 总结与展望\n\n{conclusion}\n")
            
            # 添加引用链接
            formatted_article = await self.format_article_with_references(''.join(article_parts))
            
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

if __name__ == "__main__":
    asyncio.run(main())
