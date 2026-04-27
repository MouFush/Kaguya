import re

FILE = r'c:\Users\林智涵\.conda\qwen3_web.py'
f = open(FILE, encoding='utf-8')
content = f.read()
f.close()

scripts = re.findall(r'<script>(.*?)</script>', content, re.DOTALL)
if scripts:
    js = scripts[-1]
    with open(r'c:\Users\林智涵\.conda\check_syntax.js', 'w', encoding='utf-8') as f:
        f.write(js)
    print(f'Saved {len(js)} chars, {js.count(chr(10))} lines')
    print('Checking with Node.js...')
