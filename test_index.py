import sys
sys.path.insert(0, '.')

# 导入必要的模块
from qwen3_web_final import index, AVAILABLE_TOOLS, QUICK_COMMANDS, PRESET_ROLES, PRESET_LORAS
import json

print("AVAILABLE_TOOLS:", list(AVAILABLE_TOOLS.keys()))
print("QUICK_COMMANDS:", list(QUICK_COMMANDS.keys()))
print("PRESET_ROLES count:", len(PRESET_ROLES))
print("PRESET_LORAS count:", len(PRESET_LORAS))

# 调用index函数
try:
    html = index()
    
    # 检查是否还有未替换的占位符
    remaining = []
    for placeholder in ['{{roles_json}}', '{{loras_json}}', '{{tools_json}}', '{{commands_json}}']:
        if placeholder in html:
            remaining.append(placeholder)
    
    if remaining:
        print(f"\n❌ 未替换的占位符: {remaining}")
    else:
        print("\n✅ 所有占位符已正确替换！")
    
    # 保存HTML以便检查
    with open('test_index_output.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("✅ HTML已保存到 test_index_output.html")
    
except Exception as e:
    print(f"\n❌ index()函数执行失败: {e}")
    import traceback
    traceback.print_exc()
