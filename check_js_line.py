import re

FILE = r'c:\Users\林智涵\.conda\qwen3_web.py'
f = open(FILE, encoding='utf-8')
content = f.read()
f.close()

scripts = re.findall(r'<script>(.*?)</script>', content, re.DOTALL)
if scripts:
    js = scripts[-1]
    lines = js.split('\n')
    print(f'JS total lines: {len(lines)}')
    if len(lines) > 4405:
        line = lines[4405]
        print(f'Line 4406: {repr(line)}')
        # Check for hidden chars
        for j, c in enumerate(line):
            if ord(c) > 127 or ord(c) < 32:
                print(f'  Suspicious char at col {j}: ord={ord(c)}, repr={repr(c)}')
else:
    print('No script found')
