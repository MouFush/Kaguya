#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查生成的HTML输出
"""

import json
import re

# 模拟Flask的index函数
def simulate_index():
    # 读取文件
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

def check_html(html):
    """检查HTML内容"""
    print("="*70)
    print("HTML 输出检查")
    print("="*70)
    
    print(f"\nHTML 总长度: {len(html)} bytes")
    
    # 检查script标签
    script_start = html.find('<script>')
    script_end = html.find('</script>')
    if script_start != -1 and script_end != -1:
        js_code = html[script_start+8:script_end]
        print(f"JavaScript 代码长度: {len(js_code)} bytes")
    
    # 检查关键函数
    checks = [
        ('function init()', 'init 函数'),
        ('function switchTab(', 'switchTab 函数'),
        ('function showDatasetUpload()', 'showDatasetUpload 函数'),
        ('function showCreateJob()', 'showCreateJob 函数'),
        ('init();', 'init 调用'),
    ]
    
    print("\n关键函数检查:")
    for pattern, name in checks:
        if pattern in html:
            print(f"  ✓ {name}")
        else:
            print(f"  ✗ {name} - 缺失")
    
    # 检查按钮
    print("\n按钮检查:")
    buttons = re.findall(r'<button[^>]*onclick="([^"]*)"[^>]*>([^<]*)</button>', html)
    switchtab_btns = [b for b in buttons if 'switchTab' in b[0]]
    print(f"  switchTab 按钮: {len(switchtab_btns)} 个")
    
    # 检查微调按钮
    finetune_btns = [b for b in buttons if 'Dataset' in b[0] or 'Job' in b[0]]
    print(f"  微调相关按钮: {len(finetune_btns)} 个")
    for onclick, text in finetune_btns:
        print(f"    - '{text.strip()}' -> {onclick}")
    
    # 检查变量定义
    print("\n变量定义检查:")
    var_checks = [
        (r'const roles = \[', 'roles 变量'),
        (r'const loras = \[', 'loras 变量'),
        (r'const tools = \{', 'tools 变量'),
        (r'const commands = \{', 'commands 变量'),
    ]
    
    for pattern, name in var_checks:
        if re.search(pattern, html):
            print(f"  ✓ {name}")
        else:
            print(f"  ✗ {name} - 缺失或格式错误")
    
    # 检查是否有语法错误指示
    print("\n语法问题检查:")
    if 'const roles = {{' in html:
        print("  ✗ roles 变量未正确替换")
    else:
        print("  ✓ 所有模板变量已替换")
    
    # 检查switchTab调用
    print("\nswitchTab 调用检查:")
    switchtab_calls = re.findall(r'onclick="switchTab\(([^"]*)\)"', html)
    for call in switchtab_calls[:5]:
        if ', this)' in call:
            print(f"  ✓ switchTab({call})")
        else:
            print(f"  ✗ switchTab({call}) - 缺少 this")
    
    # 保存HTML到文件以便检查
    with open('generated_html.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("\n✓ HTML 已保存到 generated_html.html")

if __name__ == '__main__':
    html = simulate_index()
    check_html(html)
