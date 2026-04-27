#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用pyjsparser检查JavaScript语法
"""

try:
    from pyjsparser import parse
    
    with open('extracted_js.js', 'r', encoding='utf-8') as f:
        code = f.read()
    
    try:
        parse(code)
        print('✓ JavaScript 语法正确')
    except Exception as e:
        print(f'✗ JavaScript 语法错误: {e}')
        
        # 尝试找到错误位置
        error_str = str(e)
        import re
        match = re.search(r'line (\d+)', error_str, re.IGNORECASE)
        if match:
            error_line = int(match.group(1))
            lines = code.split('\n')
            print(f'\n错误位置 (第 {error_line} 行):')
            for i in range(max(0, error_line - 3), min(len(lines), error_line + 2)):
                marker = ' >>> ' if i == error_line - 1 else '     '
                print(f'{marker}{i + 1}: {lines[i][:80]}')
        else:
            print(f'错误信息: {error_str}')
            
except ImportError:
    print("pyjsparser 未安装，尝试手动检查...")
    
    with open('extracted_js.js', 'r', encoding='utf-8') as f:
        code = f.read()
    
    lines = code.split('\n')
    
    # 检查常见语法问题
    print("\n检查常见语法问题...")
    
    for i, line in enumerate(lines, 1):
        # 检查未闭合的括号
        open_parens = line.count('(') - line.count(')')
        open_braces = line.count('{') - line.count('}')
        open_brackets = line.count('[') - line.count(']')
        
        # 检查特殊字符
        if '\x00' in line or '\x01' in line or '\x02' in line:
            print(f"  第 {i} 行有控制字符: {line[:50]}")
        
        # 检查引号
        if line.count('"') % 2 == 1 and '//' not in line and '/*' not in line:
            # 可能是模板字符串
            if '`' not in line:
                pass  # 忽略，可能是模板字符串的一部分
