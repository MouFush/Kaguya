#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查找JavaScript语法错误
"""

import json
import re

def generate_html():
    with open('qwen3_web.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取PRESET_ROLES
    preset_match = re.search(r'PRESET_ROLES = (\[.*?\])\n\nQUICK_COMMANDS', content, re.DOTALL)
    if preset_match:
        PRESET_ROLES = eval(preset_match.group(1))
    else:
        PRESET_ROLES = []
    
    # 提取PRESET_LORAS
    lora_match = re.search(r'PRESET_LORAS = (\[.*?\])\n\nHTML_TEMPLATE', content, re.DOTALL)
    if lora_match:
        PRESET_LORAS = eval(lora_match.group(1))
    else:
        PRESET_LORAS = []
    
    # 提取QUICK_COMMANDS
    cmds_match = re.search(r'QUICK_COMMANDS = (\{.*?\})\n\nHTML_TEMPLATE', content, re.DOTALL)
    if cmds_match:
        QUICK_COMMANDS = eval(cmds_match.group(1))
    else:
        QUICK_COMMANDS = {}
    
    # 提取HTML_TEMPLATE
    template_start = content.find('HTML_TEMPLATE = """')
    template_start += len('HTML_TEMPLATE = """')
    template_end = content.find('"""\n\ndef get_client_ip', template_start)
    HTML_TEMPLATE = content[template_start:template_end]
    
    # 模拟工具元数据
    tools_meta = {}
    
    # 执行替换
    html = HTML_TEMPLATE.replace('{{roles_json}}', json.dumps(PRESET_ROLES, ensure_ascii=False))
    html = html.replace('{{loras_json}}', json.dumps(PRESET_LORAS, ensure_ascii=False))
    html = html.replace('{{tools_json}}', json.dumps(tools_meta, ensure_ascii=False))
    html = html.replace('{{commands_json}}', json.dumps(QUICK_COMMANDS, ensure_ascii=False))
    
    return html

def find_syntax_errors(html):
    # 提取script内容
    script_match = re.search(r'<script>(.*?)</script>', html, re.DOTALL)
    if not script_match:
        print("找不到 script 标签")
        return
    
    js_code = script_match.group(1)
    lines = js_code.split('\n')
    
    print(f"JavaScript 代码行数: {len(lines)}")
    print("\n检查可能的语法错误...")
    
    # 检查第2761行（相对于整个HTML）
    html_lines = html.split('\n')
    script_start_line = None
    for i, line in enumerate(html_lines):
        if '<script>' in line:
            script_start_line = i
            break
    
    if script_start_line:
        # 浏览器报告的错误行号2761是相对于整个HTML的
        error_line_in_html = 2761
        error_line_in_js = error_line_in_html - script_start_line - 1
        
        print(f"\nScript 开始于 HTML 第 {script_start_line + 1} 行")
        print(f"错误行号 {error_line_in_html} 对应 JavaScript 第 {error_line_in_js} 行")
        
        if 0 <= error_line_in_js < len(lines):
            print(f"\n错误位置周围代码:")
            for i in range(max(0, error_line_in_js - 3), min(len(lines), error_line_in_js + 4)):
                marker = " >>> " if i == error_line_in_js else "     "
                print(f"{marker}{i+1}: {lines[i][:80]}")
    
    # 检查常见语法错误
    print("\n检查常见问题...")
    
    # 检查未闭合的字符串
    for i, line in enumerate(lines):
        single_quotes = line.count("'") - line.count("\\'")
        double_quotes = line.count('"') - line.count('\\"')
        backticks = line.count('`') - line.count('\\`')
        
        # 简单检查：如果行中有奇数个引号，可能有问题
        if single_quotes % 2 == 1 and '/*' not in line and '//' not in line:
            print(f"  第 {i+1} 行可能有未闭合的单引号: {line[:60]}")
        if backticks % 2 == 1:
            print(f"  第 {i+1} 行可能有未闭合的反引号: {line[:60]}")
    
    # 检查特殊字符
    for i, line in enumerate(lines):
        # 检查非ASCII字符（除了注释和字符串中的）
        for char in line:
            if ord(char) > 127 and char not in '。，、；：？！""''（）【】《》':
                # 可能是中文标点或其他特殊字符
                pass
    
    # 检查JSON中的特殊字符
    json_vars = ['const roles = ', 'const loras = ', 'const tools = ', 'const commands = ']
    for var in json_vars:
        for i, line in enumerate(lines):
            if var in line:
                # 检查这一行和接下来的几行
                for j in range(i, min(i+5, len(lines))):
                    if '{{' in lines[j] or '}}' in lines[j]:
                        print(f"  第 {j+1} 行有未替换的模板变量: {lines[j][:60]}")
                break
    
    # 保存JS代码以便检查
    with open('extracted_js.js', 'w', encoding='utf-8') as f:
        f.write(js_code)
    print("\n✓ JavaScript 代码已保存到 extracted_js.js")

if __name__ == '__main__':
    html = generate_html()
    find_syntax_errors(html)
