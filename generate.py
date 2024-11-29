#!/Users/john/miniconda3/bin/python3
import os
import sys
import time
import argparse
from blog_generator import generate_blog
from long_article_generator import generate_long_article
from md2html import convert_md_to_html

def print_progress(message, delay=0.05):
    """打印带动画的进度消息"""
    symbols = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    for symbol in symbols:
        sys.stdout.write(f'\r{symbol} {message}')
        sys.stdout.flush()
        time.sleep(delay)
    sys.stdout.write('\r')
    sys.stdout.flush()

def generate_with_progress(func, title, type_name):
    """带进度提示的生成函数"""
    print(f"\n🚀 开始生成{type_name}：{title}")
    
    # 获取当前文件的绝对路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    temp_md = os.path.join(current_dir, "temp_input.md")
    
    # 创建临时的markdown文件
    with open(temp_md, "w", encoding='utf-8') as f:
        f.write(title + "\n\n")
    
    try:
        # 显示生成进度
        messages = [
            "正在构思文章结构...",
            "深入研究主题...",
            "组织文章内容...",
            "优化文章表达...",
            "添加精美配图...",
            "最终润色中..."
        ]
        
        # 启动生成过程
        generation_started = False
        for msg in messages:
            if not generation_started:
                print_progress(msg)
                if msg == messages[-1]:
                    generation_started = True
                    func(temp_md)
        
        print(f"✅ {type_name}生成完成")
        return True
        
    except Exception as e:
        print(f"\n❌ 生成失败：{str(e)}")
        return False
        
    finally:
        # 如果是从命令行直接运行，则删除临时文件
        if __name__ == '__main__' and os.path.exists(temp_md):
            os.remove(temp_md)

def main():
    parser = argparse.ArgumentParser(description='AI文章生成器')
    parser.add_argument('title', nargs='?', help='文章标题')
    parser.add_argument('-t', '--type', choices=['blog', 'long', 'both'], 
                      default='blog', help='生成类型：blog=博客文章，long=长文，both=两者都生成')
    parser.add_argument('--html', action='store_true', 
                      help='是否同时生成HTML版本')
    parser.add_argument('-o', '--output', help='输出文件名（不含扩展名）')
    
    args = parser.parse_args()

    # 如果没有提供标题，进入交互模式
    if not args.title:
        args.title = input("✍️ 请输入文章标题: ").strip()
        if not args.title:
            print("❌ 错误：必须提供文章标题")
            sys.exit(1)

    # 确定输出文件名
    output_base = args.output or args.title
    
    try:
        # 根据类型生成文章
        success = True
        if args.type in ['blog', 'both']:
            success &= generate_with_progress(generate_blog, args.title, "博客文章")

        if args.type in ['long', 'both']:
            success &= generate_with_progress(generate_long_article, args.title, "长文")

        # 如果需要生成HTML
        if args.html and success:
            print("\n🌐 正在生成HTML版本...")
            md_file = f"generated_articles/{args.title}.md"
            if os.path.exists(md_file):
                html_file = convert_md_to_html(md_file)
                print(f"✅ HTML文件已生成：{html_file}")
                # 自动打开HTML文件
                os.system(f"open {html_file}")

        if success:
            print("\n🎉 所有任务完成！")
        else:
            print("\n⚠️ 部分任务未能完成，请检查错误信息。")
        
    except Exception as e:
        print(f"\n❌ 发生错误：{str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
