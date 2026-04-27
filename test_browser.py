import json
import re
import ast

# 读取 qwen3_web.py 文件
with open('qwen3_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 手动解析 PRESET_ROLES
roles_start = content.find('PRESET_ROLES = [')
roles_end = content.find(']\n\nQUICK_COMMANDS', roles_start)
roles_code = content[roles_start:roles_end+1]
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

# 模拟 AVAILABLE_TOOLS
AVAILABLE_TOOLS = {
    "web_search": {"name": "网页搜索", "description": "搜索互联网信息", "icon": "🔍", "action": "search_web"},
    "kb_search": {"name": "知识库搜索", "description": "搜索本地知识库", "icon": "📚", "action": "search_kb"},
    "execute_code": {"name": "代码执行", "description": "执行Python代码", "icon": "💻", "action": "execute_code"},
}

# 模拟 index() 函数
tools_meta = {k: {"name": v["name"], "description": v["description"], "icon": v["icon"]} for k, v in AVAILABLE_TOOLS.items()}

# 获取 HTML 模板
html_start = content.find('HTML_TEMPLATE = """') + len('HTML_TEMPLATE = """')
html_end = content.find('"""\n\ndef get_client_ip', html_start)
html_template = content[html_start:html_end]

# 替换变量（完全按照 Flask 的方式）
html = html_template.replace('{{roles_json}}', json.dumps(PRESET_ROLES, ensure_ascii=False))
html = html.replace('{{loras_json}}', json.dumps(PRESET_LORAS, ensure_ascii=False))
html = html.replace('{{tools_json}}', json.dumps(tools_meta, ensure_ascii=False))
html = html.replace('{{commands_json}}', json.dumps(QUICK_COMMANDS, ensure_ascii=False))

# 保存完整的 HTML
with open('test_page.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("=" * 70)
print("生成测试页面")
print("=" * 70)
print(f"\nHTML length: {len(html)} bytes")

# 找到 script 标签
script_start = html.find('<script>')
script_end = html.find('</script>', script_start)
script_content = html[script_start+8:script_end]

print(f"Script length: {len(script_content)} bytes")

# 检查关键部分
print("\n" + "=" * 70)
print("检查关键代码")
print("=" * 70)

# 1. 检查变量定义
print("\n1. 变量定义:")
vars_to_check = [
    ('const roles = ', 'roles'),
    ('const loras = ', 'loras'),
    ('const tools = ', 'tools'),
    ('const commands = ', 'commands'),
]
for pattern, name in vars_to_check:
    if pattern in script_content:
        print(f"  ✓ {name} defined")
    else:
        print(f"  ✗ {name} NOT found")

# 2. 检查函数定义
print("\n2. 关键函数:")
funcs_to_check = [
    'function init()',
    'function switchTab(',
    'function newChat()',
    'function showDatasetUpload()',
    'function showCreateJob()',
]
for func in funcs_to_check:
    if func in script_content:
        print(f"  ✓ {func}")
    else:
        print(f"  ✗ {func} NOT found")

# 3. 检查 HTML 按钮
print("\n3. HTML 按钮:")
buttons_to_check = [
    ('onclick="switchTab(\'finetune\')"', 'finetune tab'),
    ('onclick="showDatasetUpload()"', 'upload dataset button'),
    ('onclick="showCreateJob()"', 'create job button'),
    ('onclick="newChat()"', 'new chat button'),
]
for pattern, name in buttons_to_check:
    if pattern in html:
        print(f"  ✓ {name}")
    else:
        print(f"  ✗ {name} NOT found")

# 4. 检查是否有语法错误
print("\n4. 语法检查:")

# 检查括号平衡
open_braces = script_content.count('{')
close_braces = script_content.count('}')
open_parens = script_content.count('(')
close_parens = script_content.count(')')

print(f"  Braces: {open_braces} open, {close_braces} close (diff: {open_braces - close_braces})")
print(f"  Parentheses: {open_parens} open, {close_parens} close (diff: {open_parens - close_parens})")

if open_braces == close_braces and open_parens == close_parens:
    print("  ✓ Brackets are balanced")
else:
    print("  ✗ Brackets are NOT balanced!")

# 5. 检查 script 标签位置
print("\n5. Script 标签位置:")
head_end = html.find('</head>')
body_end = html.find('</body>')
print(f"  </head> at position: {head_end}")
print(f"  <script> at position: {script_start}")
print(f"  </body> at position: {body_end}")

if head_end < script_start < body_end:
    print("  ✓ Script is in correct position (in body)")
else:
    print("  ✗ Script position may be wrong")

print("\n" + "=" * 70)
print("测试页面已保存到 test_page.html")
print("请用浏览器打开此文件测试按钮是否工作")
print("=" * 70)
