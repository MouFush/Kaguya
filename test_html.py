import json
import re
import ast

# 读取 qwen3_web.py 文件
with open('qwen3_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

print("=" * 60)
print("测试 HTML 生成")
print("=" * 60)

# 手动解析 PRESET_ROLES
roles_start = content.find('PRESET_ROLES = [')
roles_end = content.find(']\n\nQUICK_COMMANDS', roles_start)
roles_code = content[roles_start:roles_end+1]

# 使用 ast 解析
roles_node = ast.parse(roles_code).body[0].value
PRESET_ROLES = ast.literal_eval(roles_node)

# 手动解析 PRESET_LORAS
loras_start = content.find('PRESET_LORAS = [')
loras_end = content.find(']\n\nPRESET_ROLES', loras_start)
loras_code = content[loras_start:loras_end+1]
loras_node = ast.parse(loras_code).body[0].value
PRESET_LORAS = ast.literal_eval(loras_node)

# 手动解析 QUICK_COMMANDS
cmds_start = content.find('QUICK_COMMANDS = {')
cmds_end = content.find('}\n\nHTML_TEMPLATE', cmds_start)
cmds_code = content[cmds_start:cmds_end+1]
cmds_node = ast.parse(cmds_code).body[0].value
QUICK_COMMANDS = ast.literal_eval(cmds_node)

print(f"\nPRESET_ROLES: {len(PRESET_ROLES)} items")
print(f"PRESET_LORAS: {len(PRESET_LORAS)} items")
print(f"QUICK_COMMANDS: {len(QUICK_COMMANDS)} items")

# 检查是否有换行符
print("\n检查字符串中的换行符:")
for role in PRESET_ROLES:
    if 'system' in role:
        if '\n' in role['system']:
            print(f"  ✗ Role '{role['name']}' has {role['system'].count(chr(10))} newlines in system")
        else:
            print(f"  ✓ Role '{role['name']}' has no newlines")

# 模拟 index() 函数
tools_meta = {
    "web_search": {"name": "网页搜索", "description": "搜索互联网信息", "icon": "🔍"},
    "kb_search": {"name": "知识库搜索", "description": "搜索本地知识库", "icon": "📚"},
    "execute_code": {"name": "代码执行", "description": "执行Python代码", "icon": "💻"},
}

# 获取 HTML 模板
html_start = content.find('HTML_TEMPLATE = """') + len('HTML_TEMPLATE = """')
html_end = content.find('"""\n\ndef get_client_ip', html_start)
html_template = content[html_start:html_end]

print(f"\nHTML template length: {len(html_template)} bytes")

# 替换变量
html = html_template.replace('{{roles_json}}', json.dumps(PRESET_ROLES, ensure_ascii=False))
html = html.replace('{{loras_json}}', json.dumps(PRESET_LORAS, ensure_ascii=False))
html = html.replace('{{tools_json}}', json.dumps(tools_meta, ensure_ascii=False))
html = html.replace('{{commands_json}}', json.dumps(QUICK_COMMANDS, ensure_ascii=False))

# 找到 script 标签
script_start = html.find('<script>')
script_end = html.find('</script>', script_start)
script_content = html[script_start+8:script_end]

print(f"Script content length: {len(script_content)} bytes")

# 检查关键代码片段
print("\n" + "=" * 60)
print("检查关键代码片段")
print("=" * 60)

# 检查 const roles 定义
roles_match = re.search(r'const roles = (.+?);', script_content, re.DOTALL)
if roles_match:
    roles_def = roles_match.group(1)
    print(f"\n✓ const roles found, length: {len(roles_def)}")
    
    # 检查是否有实际的换行符（不是\n）
    if chr(10) in roles_def:
        print(f"✗ ERROR: Found actual newlines in roles definition!")
        # 找到换行位置
        newline_pos = roles_def.find(chr(10))
        print(f"  Context around newline: ...{roles_def[max(0,newline_pos-50):newline_pos+50]}...")
    else:
        print(f"✓ No actual newlines in roles definition")
    
    # 尝试解析
    try:
        parsed = json.loads(roles_def)
        print(f"✓ roles JSON is valid, {len(parsed)} items")
    except Exception as e:
        print(f"✗ roles JSON is INVALID: {e}")
        print(f"  First 300 chars: {roles_def[:300]}")
else:
    print("✗ const roles NOT FOUND")

# 检查函数定义
print("\n" + "=" * 60)
print("检查函数定义")
print("=" * 60)

functions = [
    'function init()',
    'function switchTab(',
    'function newChat()',
    'function loadLoraList()',
    'function renderToolList()',
    'function renderPromptList()',
    'function loadMcpPlugins()',
    'function loadWorkflows()',
    'function refreshMemoryStats()',
    'function loadMultimodalHistory()',
    'function refreshFinetuneData()',
]

for func in functions:
    if func in script_content:
        print(f"  ✓ {func}")
    else:
        print(f"  ✗ {func} NOT FOUND")

# 保存生成的 HTML
with open('generated_page.html', 'w', encoding='utf-8') as f:
    f.write(html)
print("\n✓ Generated HTML saved to 'generated_page.html'")

print("\n" + "=" * 60)
print("诊断完成")
print("=" * 60)
