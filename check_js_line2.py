import re

FILE = r'c:\Users\林智涵\.conda\qwen3_web.py'
f = open(FILE, encoding='utf-8')
content = f.read()
f.close()

# Check the actual line 4406 in the file (not extracted JS)
lines = content.split('\n')
print(f'Total lines: {len(lines)}')
if len(lines) > 4405:
    line = lines[4405]
    print(f'Line 4406: {repr(line)}')
    # Check for any unusual chars
    for j, c in enumerate(line):
        o = ord(c)
        if o > 127 or o < 32:
            print(f'  Suspicious char at col {j}: ord={o}, char={repr(c)}')

# Check the JS at position 4406
scripts = re.findall(r'<script>(.*?)</script>', content, re.DOTALL)
if scripts:
    js = scripts[-1]
    js_lines = js.split('\n')
    print(f'\nJS line 4406: {repr(js_lines[4405])}')
