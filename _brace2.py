import urllib.request, re

BASE = "http://127.0.0.1:5000"
r = urllib.request.urlopen(BASE + '/agent-ide')
html = r.read().decode('utf-8')

scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
main_js = scripts[1] if len(scripts) > 1 else ""

# More careful brace counting that properly handles template literals
def count_braces(js):
    stack = []
    i = 0
    in_single = False
    in_double = False
    in_template = False
    in_regex = False
    in_line_comment = False
    in_block_comment = False
    
    while i < len(js):
        ch = js[i]
        
        # Handle comments
        if not in_single and not in_double and not in_template:
            if not in_block_comment and ch == '/' and i+1 < len(js) and js[i+1] == '/':
                in_line_comment = True
                i += 2
                continue
            if not in_line_comment and ch == '/' and i+1 < len(js) and js[i+1] == '*':
                in_block_comment = True
                i += 2
                continue
        
        if in_line_comment:
            if ch == '\n':
                in_line_comment = False
            i += 1
            continue
        if in_block_comment:
            if ch == '*' and i+1 < len(js) and js[i+1] == '/':
                in_block_comment = False
                i += 2
            else:
                i += 1
            continue
            
        # Handle strings
        if ch == "'" and not in_double and not in_template:
            if in_single and i > 0 and js[i-1] != '\\':
                in_single = False
            elif not in_single:
                in_single = True
        elif ch == '"' and not in_single and not in_template:
            if in_double and i > 0 and js[i-1] != '\\':
                in_double = False
            elif not in_double:
                in_double = True
        elif ch == '`' and not in_single and not in_double:
            if in_template and i > 0 and js[i-1] != '\\':
                # Check for ${} inside template literal
                in_template = False
            elif not in_template:
                in_template = True
        
        # Track braces only when not in string/comment
        if not in_single and not in_double and not in_template:
            if ch in '{([':
                stack.append((ch, i))
            elif ch in '})]':
                expected = {'(':')', '{':'}', '[':']'}
                if stack and expected.get(stack[-1][0]) == ch:
                    stack.pop()
                else:
                    print(f"  UNEXPECTED '{ch}' at pos {i}: ...{js[max(0,i-30):i+30]}...")
        
        i += 1
    
    return stack

print("Tracking braces with proper string handling...")
stack = count_braces(main_js)
print(f"\n{len(stack)} unclosed items:")
for ch, pos in stack:
    ctx = main_js[max(0,pos-40):pos+60]
    print(f"  '{ch}' at {pos}:")
    print(f"    {ctx}")
    print()
