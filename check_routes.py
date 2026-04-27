#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, 'c:\\Users\\林智涵\\.conda')

# 先检查企业级套件导入
try:
    from enterprise_llm_suite import EnterpriseLLMSuite, enterprise_suite
    print("✅ 企业级套件导入成功")
except Exception as e:
    print(f"❌ 企业级套件导入失败: {e}")

# 检查路由
print("\n正在检查Flask路由...")

# 读取文件并查找路由
with open('qwen3_web_final.py', 'r', encoding='utf-8') as f:
    content = f.read()

import re
routes = re.findall(r"@app\.route\(['\"]([^'\"]+)['\"]", content)

enterprise_routes = [r for r in routes if 'enterprise' in r]
memory_routes = [r for r in routes if 'memory' in r]

print(f"\n企业级套件路由 ({len(enterprise_routes)}个):")
for r in enterprise_routes:
    print(f"  - {r}")

print(f"\n记忆系统路由 ({len(memory_routes)}个):")
for r in memory_routes:
    print(f"  - {r}")

print("\n✅ 检查完成")
