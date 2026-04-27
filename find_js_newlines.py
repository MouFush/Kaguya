import re

with open(r'c:\Users\林智涵\.conda\qwen3_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 找到 script 标签内的 JavaScript 代码
script_match = re.search(r'<script>(.*?)</script>', content, re.DOTALL)
if script_match:
    js_code = script_match.group(1)
    js_lines = js_code.split('\n')
    
    print('JavaScript 代码中包含 \\n 的行:')
    print('=' * 60)
    
    for i, line in enumerate(js_lines):
        # 查找单引号字符串中的 \n（不是 \\n）
        # 匹配 '...\n...' 但不匹配 '\\n'
        matches = re.findall(r"'[^']*\\n[^']*'", line)
        if matches:
            print(f'行 {i+1}: {line.strip()[:100]}')
            for m in matches:
                print(f'  -> {m[:50]}')
