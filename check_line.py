import re

with open(r'c:\Users\林智涵\.conda\qwen3_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 找到 HTML_TEMPLATE
html_match = re.search(r'HTML_TEMPLATE\s*=\s*"""(.*?)"""', content, re.DOTALL)
if html_match:
    html_template = html_match.group(1)
    html_lines = html_template.split('\n')
    
    print(f'HTML 模板行数: {len(html_lines)}')
    
    # 打印第 6230-6250 行
    for i in range(6229, min(6250, len(html_lines))):
        print(f'{i+1}: {html_lines[i][:150]}')
