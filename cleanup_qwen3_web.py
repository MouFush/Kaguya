"""清理 qwen3_web.py 文件，移除本地模型相关代码"""
import re

file_path = r'c:\Users\林智涵\.conda\qwen3_web.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 移除 USE_OLLAMA 条件判断，保留 Ollama 分支
# 在 generate_stream 函数中
pattern1 = r'    if USE_OLLAMA:\s\n        generated_tokens = 0\r\n        try:\r\n            for chunk in model\.chat_stream\(messages, temperature=temperature, max_tokens=max_tokens\):\r\n                generated_tokens \+= 1\r\n                yield json\.dumps\(\{"content": chunk, "done": False\}\) \ "\\n"\r\n            yield json\.dumps\(\{"content": "", "done": True, "tokens_in": input_len, "tokens_out": generated_tokens\}\) \ "\\n"\r\n        except Exception as e:\r\n            yield json\.dumps\(\{"content": f"错误: \{str\(e\}\}", "done": True\}\) + "\\n"\r\n        return\r\n    \r\n    text = tokenizer\.apply_chat_template.*'

replacement1 = r'''    generated_tokens = 0
    try:
        for chunk in model.chat_stream(messages, temperature=temperature, max_tokens=max_tokens):
            generated_tokens += 1
            yield json.dumps({"content": chunk, "done": False}) + "\n"
        yield json.dumps({"content": "", "done": True, "tokens_in": input_len, "tokens_out": generated_tokens}) + "\n"
    except Exception as e:
        yield json.dumps({"content": f"错误: {str(e)}", "done": True}) + "\n"
'''

content = re.sub(pattern1, replacement1, content, flags=re.DOTALL)

# 2. 在 chat 函数中
pattern2 = r'    if USE_OLLAMA:\r\n        try:\r\n            response = model\.chat\(messages, temperature=temperature, max_tokens=max_tokens\)\r\n            return response, input_len, len\(response\) // 2\r\n        except Exception as e:\r\n            return f"错误: \{str\(e\}\}", input_len, 0\r\n    \r\n    text = tokenizer\.apply_chat_template.*'

replacement2 = r'''    try:
        response = model.chat(messages, temperature=temperature, max_tokens=max_tokens)
        return response, input_len, len(response) // 2
    except Exception as e:
        return f"错误: {str(e)}", input_len, 0
'''

content = re.sub(pattern2, replacement2, content, flags=re.DOTALL)

# 3. 移除 tokenizer 变量声明
content = re.sub(r'tokenizer = None\n', '', content)

# 4. 移除 HF_ENDPOINT
content = re.sub(r"os\.environ\['HF_ENDPOINT'\] = 'https://hf-mirror\.com'\n', '', content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("清理完成！")
