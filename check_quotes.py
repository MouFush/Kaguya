import requests
import re

BASE_URL = "http://127.0.0.1:5000"

r = requests.get(f"{BASE_URL}/", timeout=5)
content = r.text

# 提取script内容
script_match = re.search(r'<script>(.*?)</script>', content, re.DOTALL)
if script_match:
    script = script_match.group(1)
    
    # 统计单引号
    single_quotes = script.count("'")
    print(f"Script中单引号数量: {single_quotes}")
    print(f"单引号是否偶数: {single_quotes % 2 == 0}")
    
    # 统计双引号
    double_quotes = script.count('"')
    print(f"Script中双引号数量: {double_quotes}")
    print(f"双引号是否偶数: {double_quotes % 2 == 0}")
    
    # 统计反引号
    backticks = script.count('`')
    print(f"Script中反引号数量: {backticks}")
    print(f"反引号是否偶数: {backticks % 2 == 0}")
    
    # 查找可能有问题的行
    print("\n查找可能有问题的单引号使用...")
    lines = script.split('\n')
    for i, line in enumerate(lines):
        single = line.count("'")
        if single % 2 != 0:
            # 检查是否在注释中
            if '//' not in line or line.index("'") < (line.index('//') if '//' in line else len(line)):
                print(f"行 {i+1}: 单引号数量={single} (奇数)")
                print(f"  内容: {line[:100]}...")
                if i > 0:
                    print(f"  前一行: {lines[i-1][:80]}...")
                print()
