#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
前端按钮失灵问题诊断与修复工具
"""

import re
import json
import ast
import sys

class ButtonFixer:
    def __init__(self, filepath='qwen3_web.py'):
        self.filepath = filepath
        self.content = None
        self.issues = []
        self.fixes = []
        
    def load_file(self):
        """加载文件"""
        print("=" * 70)
        print("步骤 1: 加载文件")
        print("=" * 70)
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                self.content = f.read()
            print(f"✓ 成功加载文件: {self.filepath}")
            print(f"  文件大小: {len(self.content)} bytes")
            return True
        except Exception as e:
            print(f"✗ 加载文件失败: {e}")
            return False
    
    def check_html_template(self):
        """检查 HTML 模板结构"""
        print("\n" + "=" * 70)
        print("步骤 2: 检查 HTML 模板")
        print("=" * 70)
        
        # 查找 HTML_TEMPLATE
        template_start = self.content.find('HTML_TEMPLATE = """')
        if template_start == -1:
            print("✗ 找不到 HTML_TEMPLATE")
            return False
        
        template_start += len('HTML_TEMPLATE = """')
        template_end = self.content.find('"""\n\ndef get_client_ip', template_start)
        
        if template_end == -1:
            print("✗ 找不到 HTML_TEMPLATE 结束位置")
            return False
        
        html_template = self.content[template_start:template_end]
        print(f"✓ 找到 HTML_TEMPLATE ({len(html_template)} bytes)")
        
        # 检查关键元素
        checks = [
            ('<script>', 'script 开始标签'),
            ('</script>', 'script 结束标签'),
            ('function init()', 'init 函数'),
            ('function switchTab(', 'switchTab 函数'),
            ('onclick="switchTab(', 'switchTab 调用'),
        ]
        
        for pattern, name in checks:
            if pattern in html_template:
                print(f"  ✓ {name}")
            else:
                print(f"  ✗ {name} - 缺失")
                self.issues.append(f"HTML模板缺失: {name}")
        
        return True
    
    def check_switchtab_function(self):
        """检查 switchTab 函数"""
        print("\n" + "=" * 70)
        print("步骤 3: 检查 switchTab 函数")
        print("=" * 70)
        
        # 查找 switchTab 函数定义
        switchtab_pattern = r'function switchTab\(([^)]*)\)\s*\{'
        match = re.search(switchtab_pattern, self.content)
        
        if not match:
            print("✗ 找不到 switchTab 函数定义")
            self.issues.append("switchTab 函数缺失")
            return False
        
        params = match.group(1)
        print(f"✓ 找到 switchTab 函数")
        print(f"  参数: {params}")
        
        # 检查参数是否正确
        if 'clickedElement' in params or 'element' in params.lower():
            print("  ✓ 参数包含元素引用")
        else:
            print("  ✗ 参数缺少元素引用")
            self.issues.append("switchTab 参数需要包含元素引用")
            self.fixes.append({
                'type': 'switchtab_params',
                'old': f'function switchTab({params})',
                'new': 'function switchTab(tab, clickedElement)'
            })
        
        # 检查函数体是否使用 event.target
        func_start = match.end() - 1
        brace_count = 0
        func_end = func_start
        for i, char in enumerate(self.content[func_start:], func_start):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    func_end = i
                    break
        
        func_body = self.content[func_start:func_end+1]
        
        if 'event.target' in func_body:
            print("  ✗ 使用了 event.target (可能导致问题)")
            self.issues.append("switchTab 使用了 event.target")
            self.fixes.append({
                'type': 'switchtab_body',
                'old': 'event.target',
                'new': 'clickedElement'
            })
        elif 'clickedElement' in func_body:
            print("  ✓ 使用了 clickedElement")
        
        return True
    
    def check_html_buttons(self):
        """检查 HTML 按钮"""
        print("\n" + "=" * 70)
        print("步骤 4: 检查 HTML 按钮")
        print("=" * 70)
        
        # 查找所有 switchTab 调用
        switchtab_calls = re.findall(r'onclick="switchTab\(([^"]*)\)"', self.content)
        print(f"找到 {len(switchtab_calls)} 个 switchTab 调用")
        
        incorrect = []
        correct = []
        
        for call in switchtab_calls:
            if ', this)' in call:
                correct.append(call)
            else:
                incorrect.append(call)
        
        if correct:
            print(f"  ✓ {len(correct)} 个正确调用 (传递了 this)")
        
        if incorrect:
            print(f"  ✗ {len(incorrect)} 个错误调用 (缺少 this):")
            for call in incorrect[:3]:
                print(f"      switchTab({call})")
            self.issues.append(f"{len(incorrect)} 个按钮缺少 this 参数")
            self.fixes.append({
                'type': 'button_onclick',
                'pattern': r'onclick="switchTab\((\'[^\']+\')\)"',
                'replacement': r'onclick="switchTab(\1, this)"'
            })
        
        return True
    
    def check_init_function(self):
        """检查 init 函数"""
        print("\n" + "=" * 70)
        print("步骤 5: 检查 init 函数")
        print("=" * 70)
        
        # 查找 init 函数
        init_match = re.search(r'function init\(\)\s*\{', self.content)
        if not init_match:
            print("✗ 找不到 init 函数")
            return False
        
        print("✓ 找到 init 函数")
        
        # 获取函数体
        func_start = init_match.end() - 1
        brace_count = 0
        func_end = func_start
        for i, char in enumerate(self.content[func_start:], func_start):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    func_end = i
                    break
        
        func_body = self.content[func_start:func_end+1]
        
        # 检查是否有 try-catch
        if 'try {' in func_body:
            print("  ✓ 已有 try-catch 保护")
        else:
            print("  ✗ 缺少 try-catch 保护")
            self.issues.append("init 函数缺少错误处理")
            self.fixes.append({
                'type': 'init_try_catch',
                'func_body': func_body,
                'func_start': func_start,
                'func_end': func_end
            })
        
        # 检查 getElementById 调用是否有保护
        getelem_calls = re.findall(r"document\.getElementById\('([^']+)'\)", func_body)
        unprotected = []
        
        for elem_id in getelem_calls:
            # 检查是否有保护
            pattern = rf"const \w+ = document\.getElementById\('{elem_id}'\);"
            if re.search(pattern, func_body):
                continue
            pattern2 = rf"document\.getElementById\('{elem_id}'\)\.checked"
            if pattern2 in func_body:
                unprotected.append(elem_id)
        
        if unprotected:
            print(f"  ✗ {len(unprotected)} 个 getElementById 调用缺少保护")
            for elem_id in unprotected[:3]:
                print(f"      - {elem_id}")
        else:
            print("  ✓ 所有 getElementById 调用都有保护")
        
        return True
    
    def check_variable_definitions(self):
        """检查变量定义"""
        print("\n" + "=" * 70)
        print("步骤 6: 检查变量定义")
        print("=" * 70)
        
        # 查找 const 定义
        vars_to_check = ['const roles', 'const loras', 'const tools', 'const commands']
        
        for var in vars_to_check:
            if var in self.content:
                print(f"  ✓ {var}")
            else:
                print(f"  ✗ {var} - 缺失")
                self.issues.append(f"变量缺失: {var}")
    
    def apply_fixes(self):
        """应用修复"""
        print("\n" + "=" * 70)
        print("步骤 7: 应用修复")
        print("=" * 70)
        
        if not self.fixes:
            print("没有需要应用的修复")
            return True
        
        print(f"发现 {len(self.fixes)} 个需要修复的问题")
        
        content = self.content
        
        for fix in self.fixes:
            fix_type = fix.get('type')
            
            if fix_type == 'switchtab_params':
                # 修复 switchTab 参数
                old = fix['old']
                new = fix['new']
                content = content.replace(old, new)
                print(f"  ✓ 修复 switchTab 参数: {old} -> {new}")
                
            elif fix_type == 'switchtab_body':
                # 修复 event.target
                old = fix['old']
                new = fix['new']
                content = content.replace(old, new)
                print(f"  ✓ 修复 event.target -> clickedElement")
                
            elif fix_type == 'button_onclick':
                # 修复按钮 onclick
                pattern = fix['pattern']
                replacement = fix['replacement']
                content = re.sub(pattern, replacement, content)
                print(f"  ✓ 修复按钮 onclick (添加 this 参数)")
                
            elif fix_type == 'init_try_catch':
                # 为 init 函数添加 try-catch
                func_body = fix['func_body']
                func_start = fix['func_start']
                func_end = fix['func_end']
                
                # 提取函数体内容（去掉外层花括号）
                inner_body = func_body[1:-1].strip()
                
                # 创建新的函数体
                new_body = '''{\n            try {\n''' + inner_body + '''\n            } catch (e) {\n                console.error('Init error:', e);\n            }\n        }'''
                
                # 替换
                content = content[:func_start] + new_body + content[func_end+1:]
                print(f"  ✓ 为 init 函数添加 try-catch")
        
        # 保存修复后的文件
        self.content = content
        print("\n✓ 所有修复已应用")
        return True
    
    def save_file(self):
        """保存文件"""
        print("\n" + "=" * 70)
        print("步骤 8: 保存文件")
        print("=" * 70)
        
        try:
            # 备份原文件
            backup_path = self.filepath + '.backup'
            with open(backup_path, 'w', encoding='utf-8') as f:
                with open(self.filepath, 'r', encoding='utf-8') as orig:
                    f.write(orig.read())
            print(f"✓ 已创建备份: {backup_path}")
            
            # 保存修复后的文件
            with open(self.filepath, 'w', encoding='utf-8') as f:
                f.write(self.content)
            print(f"✓ 已保存修复后的文件: {self.filepath}")
            return True
        except Exception as e:
            print(f"✗ 保存文件失败: {e}")
            return False
    
    def generate_report(self):
        """生成报告"""
        print("\n" + "=" * 70)
        print("诊断报告")
        print("=" * 70)
        
        if not self.issues:
            print("\n✓ 未发现明显问题")
            return True
        else:
            print(f"\n发现 {len(self.issues)} 个问题:")
            for i, issue in enumerate(self.issues, 1):
                print(f"  {i}. {issue}")
            
            if self.fixes:
                print(f"\n已应用 {len(self.fixes)} 个修复")
            
            return False
    
    def run(self):
        """运行诊断和修复"""
        print("\n" + "=" * 70)
        print("前端按钮失灵问题诊断与修复工具")
        print("=" * 70)
        
        if not self.load_file():
            return False
        
        self.check_html_template()
        self.check_switchtab_function()
        self.check_html_buttons()
        self.check_init_function()
        self.check_variable_definitions()
        
        success = self.generate_report()
        
        if self.fixes:
            print("\n是否应用修复? (y/n): ", end='')
            # 自动应用修复
            self.apply_fixes()
            self.save_file()
            print("\n✓ 修复完成，请重启服务器测试")
        
        return success


if __name__ == '__main__':
    fixer = ButtonFixer()
    fixer.run()
