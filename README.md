# AI 文章生成器

一个基于 AI 的专业文章生成工具，支持长文和博客两种格式的智能创作。本项目利用先进的 AI 技术，结合网络搜索和智能引用，生成高质量、有深度的文章内容。

## 功能特点

### 长文生成器 (Long Article Generator)

- **智能章节规划**：自动规划文章结构，生成层次分明的章节
- **自动引用与论证**：
  - 智能识别需要引用的内容（数据、引用、论证等）
  - 自动搜索相关资料并添加规范的引用链接
  - 支持 Markdown 格式的引用标注
- **内容丰富性**：
  - 自动添加相关图片和图表
  - 智能关键词扩展
  - 专业术语解释
- **格式规范**：
  - 统一的章节编号（X.Y 格式）
  - 标准的 Markdown 排版
  - 清晰的文章结构

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

## 技术特点

- 基于 OpenAI GPT 模型的智能创作
- 使用 Exa.ai 进行高质量网络搜索
- Unsplash API 集成实现专业图片配图
- 异步处理提升生成效率
- 模块化设计便于扩展

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
- Email: your.email@example.com
