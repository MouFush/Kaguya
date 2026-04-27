import re
import subprocess
import sys

def extract_js_code(py_file):
    with open(py_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    script_match = re.search(r'<script>(.*?)</script>', content, re.DOTALL)
    if script_match:
        js_code = script_match.group(1)
        js_start = script_match.start()
        lines_before = content[:js_start].count('\n')
        return js_code, lines_before
    return None, 0

def check_js_syntax(js_code):
    js_code_fixed = js_code.replace('{{roles_json}}', '[]')
    js_code_fixed = js_code_fixed.replace('{{loras_json}}', '[]')
    js_code_fixed = js_code_fixed.replace('{{tools_json}}', '{}')
    js_code_fixed = js_code_fixed.replace('{{commands_json}}', '[]')
    
    with open('test_js_check.js', 'w', encoding='utf-8') as f:
        f.write(js_code_fixed)
    
    try:
        result = subprocess.run(['node', '--check', 'test_js_check.js'], 
                                capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return None
        else:
            return result.stderr
    except Exception as e:
        return str(e)

def find_invalid_token(js_code, line_num):
    lines = js_code.split('\n')
    if line_num <= len(lines):
        return lines[line_num - 1]
    return None

def main():
    py_file = r'c:\Users\林智涵\.conda\qwen3_web.py'
    
    print('=' * 60)
    print('辉夜项目 JavaScript 语法错误检测')
    print('=' * 60)
    
    js_code, lines_before = extract_js_code(py_file)
    if not js_code:
        print('未找到 JavaScript 代码')
        return
    
    print(f'JavaScript 代码行数: {len(js_code.split(chr(10)))}')
    print(f'HTML 模板起始行: {lines_before + 1}')
    
    error = check_js_syntax(js_code)
    if error:
        print(f'\n发现语法错误:\n{error}')
        
        match = re.search(r':(\d+):(\d+)', error)
        if match:
            line_num = int(match.group(1))
            col_num = int(match.group(2))
            py_line = lines_before + line_num + 1
            
            print(f'\n错误位置: JavaScript 第 {line_num} 行, 第 {col_num} 列')
            print(f'Python 文件行号: {py_line}')
            
            error_line = find_invalid_token(js_code, line_num)
            if error_line:
                print(f'\n错误行内容:\n{error_line[:100]}')
                
                start = max(0, col_num - 20)
                end = min(len(error_line), col_num + 20)
                print(f'\n错误位置上下文:\n...{error_line[start:end]}...')
                print(' ' * (col_num - start + 3) + '^')
    else:
        print('\nJavaScript 语法检查通过!')
    
    print('=' * 60)

if __name__ == '__main__':
    main()
