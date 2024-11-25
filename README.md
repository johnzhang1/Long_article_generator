# 自动化批量生成万字长文和博客文章

Version: 1.1.0
作者：玄清

一个基于 AI 的专业文章生成工具，支持长文和博客两种格式的智能创作。本项目利用先进的 AI 技术，结合网络搜索和智能引用，生成高质量、有深度的文章内容。

## 功能特点

### 长文生成器 (Long Article Generator)

- **智能章节规划**：自动规划文章结构，生成层次分明的章节
- **专业引用系统**：
  - 三种标准引用格式：
    * 观点引用：根据[来源名称]显示
    * 数据引用：数值（数据来源：[来源名称]）
    * 直接引用：[来源名称]指出："引用内容"
  - 自动搜索相关资料并添加规范的引用链接
  - 支持 Markdown 格式的引用标注
- **内容丰富性**：
  - 自动添加相关图片和图表
  - 智能关键词扩展
  - 专业术语解释
- **格式规范**：
  - 清晰的二级标题结构
  - 标准的 Markdown 排版
  - 自然的段落过渡
- **写作风格**：
  - 组合多位知名作家的写作特点
  - 保持专业性与可读性的平衡
  - 避免重复的章节总结，只保留文末总结

### 博客生成器 (Blog Generator)

- **多样化主题**：支持技术、科普、评论等多种博客类型
- **SEO 优化**：
  - 自动生成优化的标题
  - 关键词智能分布
  - 适合搜索引擎的内容结构
- **互动性增强**：
  - 引导性问题设计
  - 读者互动部分
  - 评论引导设计

## 最新改进

- **引用系统优化**：
  - 标准化的三种引用格式
  - 更准确的来源匹配
  - 改进的链接生成机制
- **内容结构优化**：
  - 移除重复的章节标题
  - 取消章节内的总结部分
  - 保持更自然的行文结构
- **写作风格提升**：
  - 融合多位作家的写作特点
  - 更自然的论述方式
  - 专业性与可读性的平衡

## 技术特点

- **AI 模型集成**：
  - 基于 OpenAI GPT-4 模型的智能创作
  - 特别说明：本项目使用了自定义的 OpenAI API 接入点，将标准的 `https://api.openai.com` 替换为 `https://api.gptsapi.net`
  - 多模型协同：不同任务使用不同的模型版本（如 gpt-4o-mini 和 chatgpt-4o-latest）

- **智能搜索与引用**：
  - 使用 Exa.ai 进行高质量网络搜索
  - 智能匹配最相关的引用来源
  - 自动生成规范的 Markdown 引用链接

- **图片处理**：
  - Unsplash API 集成实现专业图片配图
  - 智能图片关键词提取
  - 自动过滤重复图片

- **性能优化**：
  - 异步处理提升生成效率
  - 智能缓存减少 API 调用
  - 模块化设计便于扩展
  - 错误重试机制

- **内容质量保证**：
  - 多轮内容优化
  - 自动格式规范化
  - 引用准确性验证
  - 内容连贯性检查

## 适用场景

### 内容创作
- **专业文章撰写**：
  - 学术论文的初稿创作
  - 技术文档的框架搭建
  - 研究报告的内容生成

- **商业写作**：
  - 产品白皮书
  - 市场分析报告
  - 行业趋势研究

- **教育培训**：
  - 教材内容生成
  - 课程大纲制作
  - 学习资料整理

### 内容运营
- **新媒体运营**：
  - 公众号文章批量生成
  - 专栏内容规划
  - 话题系列策划

- **知识库建设**：
  - 企业知识库搭建
  - 培训材料生成
  - 标准文档制作

- **内容本地化**：
  - 多语言内容适配
  - 本地化内容创作
  - 文化背景调整

### 特殊用途
- **研究与分析**：
  - 文献综述生成
  - 研究方向探索
  - 数据分析报告

- **创意写作**：
  - 故事框架构建
  - 情节发展规划
  - 人物描写生成

- **技术文档**：
  - API 文档生成
  - 技术方案撰写
  - 系统说明文档

## 安装说明

1. 克隆项目
```bash
git clone https://github.com/whotto/Long_article_generator.git
cd Long_article_generator
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 配置环境变量
创建 `.env` 文件并添加以下配置：
```
OPENAI_API_KEY=your_openai_api_key
EXA_API_KEY=your_exa_api_key
UNSPLASH_ACCESS_KEY=your_unsplash_access_key
```

## 使用方法

### 长文生成

命令行运行：Python3 long_article_generator.py test.md

```python
from long_article_generator import LongArticleGenerator

# 创建生成器实例
generator = LongArticleGenerator(
    title="你的文章标题",
    keywords=["关键词1", "关键词2"]
)

# 生成文章
article = await generator.generate()
```

### 博客生成

命令行运行：Python3 blog_generator.py test.md 

```python
from blog_generator import BlogGenerator

# 创建生成器实例
generator = BlogGenerator(
    title="博客标题",
    style="tech"  # 可选: tech, popular, review
)

# 生成博客
blog = await generator.generate()
```

## 注意事项

- 需要确保有足够的 API 配额
- 建议在生成长文时适当控制文章长度
- 生成的内容建议进行人工审核和优化
- 遵守 API 使用条款和知识产权规范

## 贡献指南

欢迎提交 Issues 和 Pull Requests 来改进项目。请确保：

1. 代码符合项目的编码规范
2. 添加适当的测试用例
3. 更新相关文档

## 许可证

MIT License

## 联系方式

如有问题或建议，欢迎提交 Issue 或通过以下方式联系：

- GitHub Issues
- Email: grow8org@gmail.com
- 博客：https://yuedu.biz
