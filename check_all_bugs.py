import re
import subprocess

with open(r'c:\Users\林智涵\.conda\qwen3_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 找到 script 标签内的 JavaScript 代码
script_match = re.search(r'<script>(.*?)</script>', content, re.DOTALL)
if script_match:
    js_code = script_match.group(1)
    js_start = script_match.start()
    lines_before = content[:js_start].count('\n')
    
    # 替换 Python 模板占位符
    js_code_fixed = js_code.replace('{{roles_json}}', '[]')
    js_code_fixed = js_code_fixed.replace('{{loras_json}}', '[]')
    js_code_fixed = js_code_fixed.replace('{{tools_json}}', '{}')
    js_code_fixed = js_code_fixed.replace('{{commands_json}}', '[]')
    
    # 保存 JavaScript 代码到文件
    with open(r'c:\Users\林智涵\.conda\test_js_full.js', 'w', encoding='utf-8') as f:
        f.write(js_code_fixed)
    
    print('=' * 60)
    print('辉夜项目全面 JavaScript 检查')
    print('=' * 60)
    print(f'JavaScript 代码行数: {len(js_code.split(chr(10)))}')
    print(f'HTML 模板起始行: {js_start + 1}')
    
    # 检查语法错误
    try:
        result = subprocess.run(['node', '--check', 'test_js_full.js'], 
                                capture_output=True, text=True, timeout=30, cwd=r'c:\Users\林智涵\.conda')
        if result.returncode == 0:
            print('\n✅ JavaScript 语法检查通过!')
        else:
            print(f'\n❌ JavaScript 语法错误:\n{result.stderr}')
    except Exception as e:
        print(f'\n❌ 检查失败: {e}')
    
    # 检查潜在的空值问题
    print('\n' + '=' * 60)
    print('潜在空值问题检查')
    print('=' * 60)
    
    # 查找所有 getElementById 后直接访问属性的模式
    patterns = [
        (r'getElementById\([\'"][^\'"]+[\'"]\)\.textContent\s*=', 'textContent 赋值'),
        (r'getElementById\([\'"][^\'"]+[\'"]\)\.innerHTML\s*=', 'innerHTML 赋值'),
        (r'getElementById\([\'"][^\'"]+[\'"]\)\.value\s*=', 'value 赋值'),
        (r'getElementById\([\'"][^\'"]+[\'"]\)\.title\s*=', 'title 赋值'),
        (r'getElementById\([\'"][^\'"]+[\'"]\)\.classList', 'classList 操作'),
    ]
    
    issues = []
    for pattern, desc in patterns:
        matches = re.finditer(pattern, js_code)
        for m in matches:
            # 检查是否有空值保护
            line_start = js_code.rfind('\n', 0, m.start()) + 1
            line_end = js_code.find('\n', m.end())
            line = js_code[line_start:line_end]
            
            # 检查前面是否有 if 检查
            prev_code = js_code[max(0, m.start()-200):m.start()]
            has_check = 'if' in prev_code and ('getElementById' in prev_code or 'const' in prev_code or 'let' in prev_code)
            
            if not has_check:
                line_num = js_code[:m.start()].count('\n') + 1
                issues.append(f'  行 {line_num}: {desc} - {line.strip()[:80]}')
    
    if issues:
        print(f'\n⚠️ 发现 {len(issues)} 个潜在的空值问题:')
        for issue in issues[:20]:
            print(issue)
    else:
        print('\n✅ 未发现潜在的空值问题')
    
    print('=' * 60)
