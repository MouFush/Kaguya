import json

# 测试数据
PRESET_LORAS = [
    {"id": "none", "name": "🤖 基础模型", "description": "使用原始Qwen3.5-9B模型", "path": None, "category": "base", "icon": "🤖", "color": "#667eea"},
    {"id": "coder", "name": "💻 代码专家", "description": "专精编程、算法、代码审查", "path": None, "category": "coding", "icon": "💻", "color": "#00d4aa", "system": "你是一位资深的编程专家，精通多种编程语言和框架。请用专业、简洁的方式回答编程问题，提供完整的代码示例和最佳实践。"},
]

# 测试HTML模板
html_template = """
<script>
    const loras = {{loras_json}};
</script>
"""

# 替换
json_str = json.dumps(PRESET_LORAS, ensure_ascii=False)
print("JSON字符串:")
print(json_str)
print("\n替换后的HTML:")
result = html_template.replace('{{loras_json}}', json_str)
print(result)

# 检查是否有语法错误
if '{{loras_json}}' in result:
    print("\n❌ 替换失败！")
else:
    print("\n✅ 替换成功！")
