import os
import sys
import markdown
import codecs
from bs4 import BeautifulSoup

def convert_md_to_html(md_file):
    # 读取Markdown文件
    with codecs.open(md_file, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # 转换Markdown为HTML
    html = markdown.markdown(md_content, extensions=['extra'])
    
    # 创建完整的HTML文档
    template = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>文章预览</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            .container {{
                background-color: white;
                padding: 40px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            h1, h2, h3, h4, h5, h6 {{
                color: #2c3e50;
                margin-top: 24px;
                margin-bottom: 16px;
            }}
            h1 {{
                font-size: 2em;
                border-bottom: 2px solid #eaecef;
                padding-bottom: 0.3em;
            }}
            h2 {{
                font-size: 1.5em;
                border-bottom: 1px solid #eaecef;
                padding-bottom: 0.3em;
            }}
            p {{
                margin: 16px 0;
            }}
            img {{
                max-width: 100%;
                height: auto;
                display: block;
                margin: 20px auto;
                border-radius: 4px;
            }}
            blockquote {{
                border-left: 4px solid #42b983;
                margin: 16px 0;
                padding: 0 16px;
                color: #666;
            }}
            code {{
                background-color: #f8f8f8;
                padding: 2px 4px;
                border-radius: 3px;
                font-family: Consolas, Monaco, 'Andale Mono', monospace;
            }}
            pre {{
                background-color: #f8f8f8;
                padding: 16px;
                overflow: auto;
                border-radius: 3px;
            }}
            a {{
                color: #42b983;
                text-decoration: none;
            }}
            a:hover {{
                text-decoration: underline;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            {html}
        </div>
    </body>
    </html>
    """
    
    # 生成HTML文件
    output_file = os.path.splitext(md_file)[0] + '.html'
    with codecs.open(output_file, 'w', encoding='utf-8') as f:
        f.write(template)
    
    return output_file

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("使用方法: python md2html.py <markdown文件>")
        sys.exit(1)
    
    md_file = sys.argv[1]
    if not os.path.exists(md_file):
        print(f"错误：文件 {md_file} 不存在")
        sys.exit(1)
    
    output_file = convert_md_to_html(md_file)
    print(f"HTML文件已生成：{output_file}")
