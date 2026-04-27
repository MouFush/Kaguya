import requests
import re

BASE_URL = "http://127.0.0.1:5000"

r = requests.get(f"{BASE_URL}/", timeout=5)
content = r.text

# 提取script内容
script_match = re.search(r'<script>(.*?)</script>', content, re.DOTALL)
if script_match:
    script = script_match.group(1)
    
    lines = script.split('\n')
    
    # 检查行261
    print("行 261 内容:")
    print(lines[260])
    print()
    
    # 检查行261周围的上下文
    print("上下文:")
    for i in range(258, 272):
        if i < len(lines):
            print(f"{i+1}: {lines[i][:100]}...")
