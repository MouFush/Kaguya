import re

FILE = r'c:\Users\林智涵\.conda\qwen3_web.py'
with open(FILE, encoding='utf-8') as f:
    content = f.read()

scripts = re.findall(r'<script>(.*?)</script>', content, re.DOTALL)
if scripts:
    js = scripts[-1]
    with open(r'c:\Users\林智涵\.conda\extracted_js.js', 'w', encoding='utf-8') as f:
        f.write(js)
    print(f'Saved {len(js)} chars, {js.count(chr(10))} lines')
