import requests
import re

BASE_URL = "http://127.0.0.1:5000"

r = requests.get(f"{BASE_URL}/", timeout=5)
content = r.text

# 提取script内容
script_match = re.search(r'<script>(.*?)</script>', content, re.DOTALL)
if script_match:
    script = script_match.group(1)
    
    # 查找split相关行
    lines = script.split('\n')
    for i, line in enumerate(lines):
        if "split(" in line:
            print(f"行 {i+1}: {line}")
