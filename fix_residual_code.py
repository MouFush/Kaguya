"""修复 qwen3_web.py 中的残留代码"""
import re

file_path = r'c:\Users\林智涵\.conda\qwen3_web.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 删除第一个 chat 函数后的残留代码（从 "    text = tokenizer.apply_chat_template" 到 "def get_provider_runtime" 之前）
pattern1 = r'(        return f"错误: \{str\(e\)\}", input_len, 0\n)\s+text = tokenizer\.apply_chat_template.*?(def get_provider_runtime)'
replacement1 = r'\1\n\2'

content = re.sub(pattern1, replacement1, content, flags=re.DOTALL)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("修复完成！")
