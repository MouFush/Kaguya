import json
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

# 替换变量
html = html_template.replace('{{roles_json}}', json.dumps(PRESET_ROLES, ensure_ascii=False))
html = html.replace('{{loras_json}}', json.dumps(PRESET_LORAS, ensure_ascii=False))
html = html.replace('{{tools_json}}', json.dumps(tools_meta, ensure_ascii=False))
html = html.replace('{{commands_json}}', json.dumps(QUICK_COMMANDS, ensure_ascii=False))

# 找到 script 标签
script_start = html.find('<script>')
script_end = html.find('</script>', script_start)
script_content = html[script_start+8:script_end]

print("=" * 70)
print("查找括号不平衡问题")
print("=" * 70)

# 逐行检查括号平衡
lines = script_content.split('\n')
brace_count = 0
paren_count = 0
bracket_count = 0

issues = []

for i, line in enumerate(lines, 1):
    # 计算这一行的括号变化
    open_braces = line.count('{')
    close_braces = line.count('}')
    open_parens = line.count('(')
    close_parens = line.count(')')
    open_brackets = line.count('[')
    close_brackets = line.count(']')
    
    brace_count += open_braces - close_braces
    paren_count += open_parens - close_parens
    bracket_count += open_brackets - close_brackets
    
    # 如果括号计数变为负数，说明有问题
    if brace_count < 0:
        issues.append(f"Line {i}: Brace count went negative ({brace_count}): {line[:80]}")
        brace_count = 0  # 重置以避免后续错误
    if paren_count < 0:
        issues.append(f"Line {i}: Paren count went negative ({paren_count}): {line[:80]}")
        paren_count = 0
    if bracket_count < 0:
        issues.append(f"Line {i}: Bracket count went negative ({bracket_count}): {line[:80]}")
        bracket_count = 0

print(f"\nFinal counts:")
print(f"  Braces: {brace_count}")
print(f"  Parens: {paren_count}")
print(f"  Brackets: {bracket_count}")

if issues:
    print(f"\nFound {len(issues)} issues:")
    for issue in issues[:20]:
        print(f"  {issue}")
else:
    print("\nNo bracket balance issues found during line-by-line check")

# 检查最后几行
print("\n" + "=" * 70)
print("最后 20 行代码:")
print("=" * 70)
for i, line in enumerate(lines[-20:], len(lines) - 19):
    print(f"{i:4d}: {line}")

print("\n" + "=" * 70)
print("检查完成")
print("=" * 70)
