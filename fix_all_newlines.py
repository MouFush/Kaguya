import re

with open(r'c:\Users\林智涵\.conda\qwen3_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 找到 script 标签内的 JavaScript 代码
script_match = re.search(r'<script>(.*?)</script>', content, re.DOTALL)
if script_match:
    js_code = script_match.group(1)
    js_start = script_match.start()
    js_end = script_match.end()
    
    # 替换所有 JavaScript 单引号字符串中的 \n 为 \\n
    # 但不替换已经是 \\n 的
    def fix_newlines(match):
        s = match.group(0)
        # 如果已经包含 \\n，不处理
        if '\\\\n' in s:
            return s
        # 替换 \n 为 \\n
        return s.replace('\\n', '\\\\n')
    
    # 匹配单引号字符串（不包含已转义的引号）
    js_code_fixed = re.sub(r"'[^'\\]*(?:\\.[^'\\]*)*'", fix_newlines, js_code)
    
    # 重建文件内容
    new_content = content[:js_start] + '<script>' + js_code_fixed + '</script>' + content[js_end:]
    
    # 保存修复后的文件
    with open(r'c:\Users\林智涵\.conda\qwen3_web.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print('JavaScript 代码中的 \\n 已修复')
    print(f'原始 JS 代码长度: {len(js_code)}')
    print(f'修复后 JS 代码长度: {len(js_code_fixed)}')
