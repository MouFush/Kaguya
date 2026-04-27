#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
浏览器端按钮问题诊断工具
模拟浏览器环境检查JavaScript代码
"""

import re
import json

class BrowserDiagnostic:
    def __init__(self, filepath='qwen3_web.py'):
        self.filepath = filepath
        self.content = None
        self.issues = []
        
    def load_file(self):
        """加载文件"""
        with open(self.filepath, 'r', encoding='utf-8') as f:
            self.content = f.read()
        print(f"✓ 加载文件: {self.filepath} ({len(self.content)} bytes)")
        
    def extract_html_template(self):
        """提取HTML模板"""
        start = self.content.find('HTML_TEMPLATE = """')
        if start == -1:
            print("✗ 找不到 HTML_TEMPLATE")
            return None
        start += len('HTML_TEMPLATE = """')
        end = self.content.find('"""\n\ndef get_client_ip', start)
        if end == -1:
            print("✗ 找不到 HTML_TEMPLATE 结束位置")
            return None
        return self.content[start:end]
    
    def check_json_variables(self, html):
        """检查JSON变量替换"""
        print("\n" + "="*70)
        print("检查 JSON 变量替换")
        print("="*70)
        
        # 检查模板变量
        vars_in_template = re.findall(r'\{\{(\w+)\}\}', html)
        print(f"模板中的变量: {vars_in_template}")
        
        # 检查Python代码中的替换
        replacements = re.findall(r"\.replace\('\{\{(\w+)\}\}'", self.content)
        print(f"Python中的替换: {replacements}")
        
        # 检查是否有未替换的变量
        for var in vars_in_template:
            if var not in replacements:
                self.issues.append(f"变量 {{%s}} 没有在Python中替换" % var)
                print(f"  ✗ {{%s}} 没有在Python中替换" % var)
            else:
                print(f"  ✓ {{%s}} 已替换" % var)
    
    def check_javascript_syntax(self, html):
        """检查JavaScript语法"""
        print("\n" + "="*70)
        print("检查 JavaScript 语法")
        print("="*70)
        
        # 提取script内容
        script_match = re.search(r'<script>(.*?)</script>', html, re.DOTALL)
        if not script_match:
            print("✗ 找不到 script 标签")
            return
        
        js_code = script_match.group(1)
        print(f"JavaScript 代码长度: {len(js_code)} bytes")
        
        # 检查基本语法问题
        checks = [
            (r'const\s+\w+\s*=\s*\{\{', "未替换的模板变量"),
            (r'function\s+\w+\s*\([^)]*\)\s*\{', "函数定义"),
            (r'\bevent\.target\b', "event.target 使用"),
        ]
        
        for pattern, desc in checks:
            matches = re.findall(pattern, js_code)
            if matches:
                if desc == "未替换的模板变量":
                    print(f"  ✗ 发现 {len(matches)} 个未替换的模板变量")
                    for m in matches[:3]:
                        print(f"      {m}")
                    self.issues.append(f"发现 {len(matches)} 个未替换的模板变量")
                elif desc == "event.target 使用":
                    print(f"  ✗ 发现 {len(matches)} 处 event.target 使用")
                    self.issues.append(f"发现 {len(matches)} 处 event.target 使用")
                else:
                    print(f"  ✓ {desc}: {len(matches)} 个")
    
    def check_button_handlers(self, html):
        """检查按钮事件处理器"""
        print("\n" + "="*70)
        print("检查按钮事件处理器")
        print("="*70)
        
        # 查找所有onclick
        onclick_pattern = r'onclick="([^"]+)"'
        onclick_handlers = re.findall(onclick_pattern, html)
        
        print(f"找到 {len(onclick_handlers)} 个 onclick 处理器")
        
        # 检查switchTab调用
        switchtab_calls = [h for h in onclick_handlers if 'switchTab' in h]
        print(f"  - switchTab 调用: {len(switchtab_calls)} 个")
        
        correct = sum(1 for h in switchtab_calls if ', this)' in h)
        incorrect = len(switchtab_calls) - correct
        
        if correct:
            print(f"    ✓ {correct} 个正确 (传递了 this)")
        if incorrect:
            print(f"    ✗ {incorrect} 个错误 (缺少 this)")
            self.issues.append(f"{incorrect} 个switchTab调用缺少this参数")
        
        # 检查其他函数调用
        other_calls = [h for h in onclick_handlers if 'switchTab' not in h]
        print(f"  - 其他函数调用: {len(other_calls)} 个")
        
        # 检查这些函数是否定义
        for call in other_calls[:10]:
            func_name = call.split('(')[0].strip()
            if func_name:
                pattern = rf'function\s+{re.escape(func_name)}\s*\('
                if re.search(pattern, html):
                    print(f"    ✓ {func_name} 已定义")
                else:
                    print(f"    ✗ {func_name} 未定义")
                    self.issues.append(f"函数 {func_name} 被调用但未定义")
    
    def check_function_order(self, html):
        """检查函数定义顺序"""
        print("\n" + "="*70)
        print("检查函数定义顺序")
        print("="*70)
        
        # 提取script内容
        script_match = re.search(r'<script>(.*?)</script>', html, re.DOTALL)
        if not script_match:
            return
        
        js_code = script_match.group(1)
        
        # 查找所有函数定义
        func_defs = re.findall(r'function\s+(\w+)\s*\(', js_code)
        print(f"找到 {len(func_defs)} 个函数定义")
        
        # 检查switchTab是否在init之后
        try:
            switchtab_idx = func_defs.index('switchTab')
            init_idx = func_defs.index('init')
            print(f"  init 定义位置: #{init_idx + 1}")
            print(f"  switchTab 定义位置: #{switchtab_idx + 1}")
            
            if switchtab_idx > init_idx:
                print("  ✓ switchTab 在 init 之后定义 (正确)")
            else:
                print("  ✗ switchTab 在 init 之前定义 (可能导致问题)")
                self.issues.append("switchTab 应该在 init 之后定义")
        except ValueError as e:
            print(f"  ✗ 找不到函数: {e}")
    
    def check_dom_readiness(self, html):
        """检查DOM就绪处理"""
        print("\n" + "="*70)
        print("检查 DOM 就绪处理")
        print("="*70)
        
        # 提取script内容
        script_match = re.search(r'<script>(.*?)</script>', html, re.DOTALL)
        if not script_match:
            return
        
        js_code = script_match.group(1)
        
        # 检查init调用方式
        if 'document.addEventListener(\'DOMContentLoaded\'' in js_code:
            print("  ✓ 使用 DOMContentLoaded 事件")
        elif 'window.onload' in js_code:
            print("  ✓ 使用 window.onload")
        elif 'init();' in js_code:
            print("  ! 直接调用 init() (如果script在body末尾则没问题)")
        else:
            print("  ✗ 没有找到 DOM 就绪处理")
            self.issues.append("缺少DOM就绪处理")
    
    def run(self):
        """运行诊断"""
        print("="*70)
        print("浏览器端按钮问题诊断工具")
        print("="*70)
        
        self.load_file()
        html = self.extract_html_template()
        
        if html:
            self.check_json_variables(html)
            self.check_javascript_syntax(html)
            self.check_button_handlers(html)
            self.check_function_order(html)
            self.check_dom_readiness(html)
        
        # 生成报告
        print("\n" + "="*70)
        print("诊断报告")
        print("="*70)
        
        if not self.issues:
            print("\n✓ 未发现明显问题")
            print("\n建议:")
            print("  1. 重启服务器并清除浏览器缓存")
            print("  2. 在浏览器中打开开发者工具(F12)查看Console错误")
            print("  3. 检查Network标签页确保资源加载正常")
        else:
            print(f"\n发现 {len(self.issues)} 个问题:")
            for i, issue in enumerate(self.issues, 1):
                print(f"  {i}. {issue}")

if __name__ == '__main__':
    diagnostic = BrowserDiagnostic()
    diagnostic.run()
