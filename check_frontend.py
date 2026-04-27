#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
前端诊断脚本 - 检查API端点是否正常工作
"""

import requests
import json

def check_api(endpoint, method='GET', data=None):
    """检查API端点"""
    try:
        url = f"http://127.0.0.1:5000{endpoint}"
        if method == 'GET':
            response = requests.get(url, timeout=5)
        else:
            response = requests.post(url, json=data, timeout=5)
        
        return {
            'status': response.status_code,
            'ok': response.ok,
            'data': response.json() if response.ok else None
        }
    except Exception as e:
        return {
            'status': 0,
            'ok': False,
            'error': str(e)
        }

print("=" * 60)
print("🔍 辉夜AI前端诊断报告")
print("=" * 60)
print()

# 检查基本页面
print("📄 检查基本页面...")
result = check_api('/')
print(f"   首页: {'✅ 正常' if result['ok'] else '❌ 错误'} (状态码: {result['status']})")

# 检查高级功能API
print()
print("🚀 检查高级功能API...")

apis = [
    ('/advanced/stats', 'GET', '高级功能统计'),
    ('/advanced/graphrag/build', 'POST', 'GraphRAG构建'),
    ('/advanced/prompt/create', 'POST', '提示词创建'),
    ('/advanced/evaluate/run', 'POST', '模型评估'),
    ('/advanced/finetune/jobs', 'GET', '微调任务列表'),
    ('/advanced/security/stats', 'GET', '安全统计'),
    ('/agent/status', 'GET', 'Agent状态'),
]

for endpoint, method, name in apis:
    test_data = {'test': 'data'} if method == 'POST' else None
    result = check_api(endpoint, method, test_data)
    status = '✅' if result['ok'] else '⚠️'
    print(f"   {status} {name}: {endpoint}")
    if not result['ok'] and 'error' in result:
        print(f"      错误: {result['error']}")

print()
print("=" * 60)
print("✅ 诊断完成!")
print("=" * 60)
print()
print("说明:")
print("  ✅ - API正常工作")
print("  ⚠️ - API可能有问题(检查详细错误)")
print()
print("如果所有API都显示✅，则前端应该可以正常使用!")
