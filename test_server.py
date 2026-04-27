#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
服务器测试脚本 - 启动服务器并测试按钮功能
"""

import subprocess
import time
import urllib.request
import urllib.error
import sys
import os

def start_server():
    """启动服务器"""
    print("启动服务器...")
    
    # 使用start命令在Windows上启动服务器
    proc = subprocess.Popen(
        ['D:\\Anoconda\\envs\\DL\\python.exe', 'qwen3_web.py'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=r'C:\Users\林智涵\.conda'
    )
    
    # 等待服务器启动
    print("等待服务器启动...")
    time.sleep(5)
    
    return proc

def test_server():
    """测试服务器是否响应"""
    try:
        response = urllib.request.urlopen('http://127.0.0.1:8080/', timeout=10)
        html = response.read().decode('utf-8')
        print(f"✓ 服务器响应正常 (状态码: {response.status})")
        print(f"  响应大小: {len(html)} bytes")
        return html
    except Exception as e:
        print(f"✗ 服务器测试失败: {e}")
        return None

def check_html_issues(html):
    """检查HTML中的问题"""
    print("\n检查HTML内容...")
    
    issues = []
    
    # 检查script标签
    if '<script>' in html and '</script>' in html:
        print("  ✓ script 标签存在")
    else:
        print("  ✗ script 标签缺失")
        issues.append("script标签缺失")
    
    # 检查init函数
    if 'function init()' in html:
        print("  ✓ init 函数存在")
    else:
        print("  ✗ init 函数缺失")
        issues.append("init函数缺失")
    
    # 检查switchTab函数
    if 'function switchTab(' in html:
        print("  ✓ switchTab 函数存在")
    else:
        print("  ✗ switchTab 函数缺失")
        issues.append("switchTab函数缺失")
    
    # 检查按钮
    import re
    buttons = re.findall(r'<button[^>]*onclick="switchTab\([^"]*\)"[^>]*>', html)
    print(f"  ✓ 找到 {len(buttons)} 个标签切换按钮")
    
    # 检查是否有未替换的模板变量
    template_vars = re.findall(r'\{\{\w+\}\}', html)
    if template_vars:
        print(f"  ✗ 发现 {len(template_vars)} 个未替换的模板变量: {template_vars[:3]}")
        issues.append(f"未替换的模板变量: {template_vars}")
    else:
        print("  ✓ 所有模板变量已替换")
    
    # 检查JavaScript语法错误指示
    if 'const roles = {' in html:
        print("  ✗ 发现未正确替换的roles变量")
        issues.append("roles变量未正确替换")
    else:
        print("  ✓ roles变量已正确替换")
    
    return issues

def main():
    print("="*70)
    print("服务器测试脚本")
    print("="*70)
    
    # 检查文件是否存在
    if not os.path.exists('qwen3_web.py'):
        print("✗ qwen3_web.py 不存在")
        return
    
    # 启动服务器
    proc = start_server()
    
    try:
        # 测试服务器
        html = test_server()
        
        if html:
            # 检查HTML问题
            issues = check_html_issues(html)
            
            print("\n" + "="*70)
            print("测试结果")
            print("="*70)
            
            if issues:
                print(f"\n发现 {len(issues)} 个问题:")
                for i, issue in enumerate(issues, 1):
                    print(f"  {i}. {issue}")
            else:
                print("\n✓ 服务器运行正常，HTML内容正确")
                print("\n请在浏览器中访问 http://127.0.0.1:8080/ 测试按钮功能")
                print("按 Ctrl+C 停止服务器")
                
                # 保持运行
                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    print("\n停止服务器...")
        else:
            print("\n✗ 服务器未能正常响应")
            
    finally:
        # 停止服务器
        proc.terminate()
        proc.wait()
        print("服务器已停止")

if __name__ == '__main__':
    main()
