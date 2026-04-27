import json
import re
import ast

# 读取 qwen3_web.py 文件
with open('qwen3_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

print("=" * 70)
print("深度 JavaScript 语法检查")
print("=" * 70)

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

# 替换变量
html = html_template.replace('{{roles_json}}', json.dumps(PRESET_ROLES, ensure_ascii=False))
html = html.replace('{{loras_json}}', json.dumps(PRESET_LORAS, ensure_ascii=False))
html = html.replace('{{tools_json}}', json.dumps(tools_meta, ensure_ascii=False))
html = html.replace('{{commands_json}}', json.dumps(QUICK_COMMANDS, ensure_ascii=False))

# 找到 script 标签
script_start = html.find('<script>')
script_end = html.find('</script>', script_start)
script_content = html[script_start+8:script_end]

print(f"\nScript content length: {len(script_content)} bytes")

# 检查 script 内容的前 1000 个字符
print("\n" + "=" * 70)
print("Script 开头内容 (前 1000 字符)")
print("=" * 70)
print(script_content[:1000])

# 检查变量定义
print("\n" + "=" * 70)
print("检查变量定义")
print("=" * 70)

# 找到 const roles 定义
roles_match = re.search(r'const roles = (.+?);', script_content, re.DOTALL)
if roles_match:
    roles_def = roles_match.group(1)
    print(f"\n✓ const roles found")
    print(f"  Length: {len(roles_def)}")
    
    # 检查是否有实际的换行符
    if '\n' in roles_def:
        print(f"  ✗ Contains actual newlines!")
    else:
        print(f"  ✓ No actual newlines")
    
    # 尝试解析 JSON
    try:
        parsed = json.loads(roles_def)
        print(f"  ✓ Valid JSON with {len(parsed)} items")
    except Exception as e:
        print(f"  ✗ JSON parse error: {e}")
        # 找到错误位置
        try:
            json.loads(roles_def)
        except json.JSONDecodeError as je:
            print(f"    Error at position: {je.pos}")
            print(f"    Context: ...{roles_def[max(0,je.pos-30):je.pos+30]}...")

# 检查所有函数定义
print("\n" + "=" * 70)
print("检查函数定义顺序")
print("=" * 70)

# 找到所有函数定义
func_pattern = r'function (\w+)\('
functions = re.findall(func_pattern, script_content)
print(f"\nFound {len(functions)} functions:")

# 检查关键函数的顺序
key_functions = ['init', 'switchTab', 'newChat', 'loadLoraList', 'renderToolList', 
                 'renderPromptList', 'loadMcpPlugins', 'loadWorkflows', 
                 'refreshMemoryStats', 'loadMultimodalHistory', 'refreshFinetuneData']

func_positions = {}
for func in functions:
    pos = script_content.find(f'function {func}(')
    func_positions[func] = pos

# 检查 switchTab 是否在它调用的函数之后
switchTab_pos = func_positions.get('switchTab', -1)
if switchTab_pos >= 0:
    print(f"\nswitchTab position: {switchTab_pos}")
    print("\nFunctions called by switchTab:")
    for called_func in ['loadLoraList', 'renderToolList', 'renderPromptList', 
                        'loadMcpPlugins', 'loadWorkflows', 'refreshMemoryStats', 
                        'loadMultimodalHistory', 'refreshFinetuneData']:
        if called_func in func_positions:
            pos = func_positions[called_func]
            if pos > switchTab_pos:
                print(f"  ✗ {called_func} is AFTER switchTab (pos: {pos})")
            else:
                print(f"  ✓ {called_func} is BEFORE switchTab (pos: {pos})")

# 检查是否有语法错误模式
print("\n" + "=" * 70)
print("检查常见语法错误")
print("=" * 70)

# 检查未闭合的括号
lines = script_content.split('\n')
issues = []
for i, line in enumerate(lines, 1):
    stripped = line.strip()
    
    # 跳过注释和空行
    if not stripped or stripped.startswith('//') or stripped.startswith('*'):
        continue
    
    # 检查引号平衡
    single_quotes = line.count("'") - line.count("\\'")
    double_quotes = line.count('"') - line.count('\\"')
    
    # 简单的引号检查（不处理转义）
    if single_quotes % 2 != 0 and '"' not in line:
        issues.append(f"Line {i}: Unbalanced single quotes: {stripped[:60]}")
    
    # 检查括号
    open_parens = line.count('(')
    close_parens = line.count(')')
    open_braces = line.count('{')
    close_braces = line.count('}')
    open_brackets = line.count('[')
    close_brackets = line.count(']')
    
    # 如果一行中有未闭合的括号（除了正常的控制流语句）
    if open_parens != close_parens:
        if not any(kw in stripped for kw in ['if ', 'for ', 'while ', 'function ', '=>', 'switch', 'catch']):
            if not stripped.endswith(('&&', '||', '?', ':', ',', '(', ')', '{', '}', ';')):
                issues.append(f"Line {i}: Unbalanced parens ({open_parens} vs {close_parens}): {stripped[:60]}")

if issues:
    print(f"\nFound {len(issues)} potential issues:")
    for issue in issues[:10]:  # 只显示前10个
        print(f"  {issue}")
else:
    print("\nNo obvious syntax issues found")

# 保存完整的 script 内容以便检查
with open('script_content.js', 'w', encoding='utf-8') as f:
    f.write(script_content)
print("\n✓ Script content saved to 'script_content.js'")

print("\n" + "=" * 70)
print("诊断完成")
print("=" * 70)
