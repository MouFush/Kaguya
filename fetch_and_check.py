#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取服务器返回的HTML并检查
"""

import urllib.request
import re

# 获取服务器返回的HTML
try:
    response = urllib.request.urlopen('http://127.0.0.1:5000/', timeout=10)
    html = response.read().decode('utf-8')
    print(f"✓ 获取HTML成功，长度: {len(html)} bytes")
    
    # 提取script内容
    script_match = re.search(r'<script>(.*?)</script>', html, re.DOTALL)
    if script_match:
        js_code = script_match.group(1)
        lines = js_code.split('\n')
        print(f"✓ JavaScript代码行数: {len(lines)}")
        
        # 检查第826-828行（根据之前的分析）
        print("\n检查第826-828行:")
        for i in range(825, min(828, len(lines))):
            print(f"  {i+1}: {lines[i][:100]}")
        
        # 保存到文件
        with open('server_js.js', 'w', encoding='utf-8') as f:
            f.write(js_code)
        print("\n✓ JavaScript已保存到 server_js.js")
        
        # 检查是否有明显的语法错误模式
        print("\n检查常见语法错误模式...")
        
        # 检查未闭合的字符串
        for i, line in enumerate(lines, 1):
            # 检查反引号
            backticks = line.count('`')
            if backticks % 2 == 1:
                # 可能是多行模板字符串，检查下一行
                pass
        
        # 检查第2761行（浏览器报告的错误位置）
        html_lines = html.split('\n')
        if len(html_lines) > 2760:
            print(f"\nHTML第2761行:")
            print(f"  {html_lines[2760][:100]}")
            
            # 找到script开始的位置
            script_start = None
            for i, line in enumerate(html_lines):
                if '<script>' in line:
                    script_start = i
                    break
            
            if script_start:
                js_line_num = 2761 - script_start - 1
                print(f"\n对应JavaScript第{js_line_num}行:")
                if js_line_num <= len(lines):
                    print(f"  {lines[js_line_num-1][:100]}")
    else:
        print("✗ 找不到script标签")
        
except Exception as e:
    print(f"✗ 获取失败: {e}")
