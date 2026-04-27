import sys
sys.path.insert(0, r'c:\Users\林智涵\.conda')

from qwen3_web import web_search, web_fetch

print("=" * 60)
print("测试网络搜索功能")
print("=" * 60)

# 测试搜索
print("\n[1] 测试网络搜索...")
result = web_search("Python编程教程", max_results=3)
print(result[:500])

print("\n" + "=" * 60)
print("测试完成")
