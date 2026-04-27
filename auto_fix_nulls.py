import re

with open(r'c:\Users\林智涵\.conda\qwen3_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 找到 script 标签内的 JavaScript 代码
script_match = re.search(r'<script>(.*?)</script>', content, re.DOTALL)
if script_match:
    js_code = script_match.group(1)
    js_start = script_match.start()
    js_end = script_match.end()
    
    # 修复模式：将 document.getElementById('xxx').property = value 
    # 改为 const el = document.getElementById('xxx'); if (el) el.property = value;
    # 或简化为 if (document.getElementById('xxx')) document.getElementById('xxx').property = value;
    
    # 需要修复的模式
    fixes = []
    
    # 查找所有需要修复的地方
    patterns = [
        r"document\.getElementById\('([^']+)'\)\.textContent\s*=\s*([^;]+);",
        r"document\.getElementById\('([^']+)'\)\.innerHTML\s*=\s*([^;]+);",
        r"document\.getElementById\('([^']+)'\)\.value\s*=\s*([^;]+);",
        r'document\.getElementById\("([^"]+)"\)\.textContent\s*=\s*([^;]+);',
        r'document\.getElementById\("([^"]+)"\)\.innerHTML\s*=\s*([^;]+);',
    ]
    
    # 统计修复数量
    fix_count = 0
    
    # 对每个模式进行修复
    for pattern in patterns:
        def add_null_check(match):
            global fix_count
            id_name = match.group(1)
            value = match.group(2)
            fix_count += 1
            return f"const _el{fix_count} = document.getElementById('{id_name}'); if (_el{fix_count}) _el{fix_count}.textContent = {value};"
        
        js_code = re.sub(pattern, add_null_check, js_code)
    
    # 重建文件内容
    new_content = content[:js_start] + '<script>' + js_code + '</script>' + content[js_end:]
    
    # 保存修复后的文件
    with open(r'c:\Users\林智涵\.conda\qwen3_web.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f'修复了 {fix_count} 个潜在的空值问题')
