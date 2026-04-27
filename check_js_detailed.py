import requests
import re

BASE_URL = "http://127.0.0.1:5000"

r = requests.get(f"{BASE_URL}/", timeout=5)
content = r.text

# 提取script内容
script_match = re.search(r'<script>(.*?)</script>', content, re.DOTALL)
if script_match:
    script = script_match.group(1)
    
    # 统计引号
    single_quotes = script.count("'")
    double_quotes = script.count('"')
    backticks = script.count('`')
    
    print(f"单引号: {single_quotes} ({'偶数' if single_quotes % 2 == 0 else '奇数'})")
    print(f"双引号: {double_quotes} ({'偶数' if double_quotes % 2 == 0 else '奇数'})")
    print(f"反引号: {backticks} ({'偶数' if backticks % 2 == 0 else '奇数'})")
    
    # 检查括号
    open_braces = script.count('{')
    close_braces = script.count('}')
    open_parens = script.count('(')
    close_parens = script.count(')')
    open_brackets = script.count('[')
    close_brackets = script.count(']')
    
    print(f"\n大括号: {open_braces} 开, {close_braces} 闭 ({'匹配' if open_braces == close_braces else '不匹配'})")
    print(f"小括号: {open_parens} 开, {close_parens} 闭 ({'匹配' if open_parens == close_parens else '不匹配'})")
    print(f"中括号: {open_brackets} 开, {close_brackets} 闭 ({'匹配' if open_brackets == close_brackets else '不匹配'})")
    
    # 查找可能有问题的行
    print("\n" + "=" * 60)
    print("查找可能有问题的行...")
    print("=" * 60)
    
    lines = script.split('\n')
    for i, line in enumerate(lines):
        issues = []
        
        # 检查单引号
        single = line.count("'")
        if single % 2 != 0:
            issues.append(f"单引号奇数({single})")
        
        # 检查双引号
        double = line.count('"')
        if double % 2 != 0:
            issues.append(f"双引号奇数({double})")
        
        # 检查反引号
        backtick = line.count('`')
        if backtick % 2 != 0:
            issues.append(f"反引号奇数({backtick})")
        
        if issues:
            print(f"\n行 {i+1}: {', '.join(issues)}")
            print(f"  {line[:120]}...")
