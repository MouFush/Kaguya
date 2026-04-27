#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查HTML第2761行的内容
"""

import json
import re

# 模拟生成HTML
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

def check_line_2761(html):
    lines = html.split('\n')
    print(f"HTML总行数: {len(lines)}")
    
    if len(lines) > 2760:
        print(f"\n第2761行内容:")
        print(f"  {lines[2760]}")
        
        # 检查周围几行
        print(f"\n第2758-2765行内容:")
        for i in range(2757, min(2765, len(lines))):
            print(f"  {i+1}: {lines[i][:100]}")
    else:
        print(f"HTML只有 {len(lines)} 行，没有第2761行")

if __name__ == '__main__':
    html = generate_html()
    check_line_2761(html)
