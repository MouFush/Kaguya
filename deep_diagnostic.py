#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
深度诊断工具 - 检查可能导致按钮失灵的问题
"""

import re

class DeepDiagnostic:
    def __init__(self, filepath='qwen3_web.py'):
        self.filepath = filepath
        self.content = None
        self.issues = []
        
    def load_file(self):
        with open(self.filepath, 'r', encoding='utf-8') as f:
            self.content = f.read()
        print(f"✓ 加载文件: {self.filepath}")
    
    def extract_html_template(self):
        start = self.content.find('HTML_TEMPLATE = """')
        if start == -1:
            return None
        start += len('HTML_TEMPLATE = """')
        end = self.content.find('"""\n\ndef get_client_ip', start)
        if end == -1:
            return None
        return self.content[start:end]
    
    def check_tab_content_structure(self, html):
        """检查标签页内容结构"""
        print("\n" + "="*70)
        print("检查标签页内容结构")
        print("="*70)
        
        # 查找所有tab-content
        tab_contents = re.findall(r'<div id="(\w+Tab)" class="tab-content"', html)
        print(f"找到 {len(tab_contents)} 个标签页:")
        for tc in tab_contents:
            print(f"  - {tc}")
        
        # 检查对应的switchTab调用
        for tc in tab_contents:
            tab_id = tc.replace('Tab', '')
            pattern = rf"switchTab\('{tab_id}'"
            if re.search(pattern, html):
                print(f"  ✓ {tab_id} 有对应的switchTab调用")
            else:
                print(f"  ✗ {tab_id} 缺少switchTab调用")
                self.issues.append(f"标签页 {tab_id} 缺少switchTab调用")
    
    def check_button_nesting(self, html):
        """检查按钮嵌套问题"""
        print("\n" + "="*70)
        print("检查按钮嵌套")
        print("="*70)
        
        # 检查按钮是否正确闭合
        buttons = re.findall(r'<button[^>]*>.*?</button>', html, re.DOTALL)
        print(f"找到 {len(buttons)} 个按钮")
        
        # 检查是否有未闭合的按钮
        open_buttons = html.count('<button')
        close_buttons = html.count('</button>')
        print(f"  开始标签: {open_buttons}")
        print(f"  结束标签: {close_buttons}")
        
        if open_buttons != close_buttons:
            print(f"  ✗ 按钮标签不匹配!")
            self.issues.append(f"按钮标签不匹配: {open_buttons} 开始, {close_buttons} 结束")
        else:
            print(f"  ✓ 按钮标签匹配")
    
    def check_quotes_in_onclick(self, html):
        """检查onclick中的引号问题"""
        print("\n" + "="*70)
        print("检查 onclick 引号")
        print("="*70)
        
        # 查找所有onclick
        onclick_attrs = re.findall(r'onclick="([^"]*)"', html)
        
        problematic = []
        for attr in onclick_attrs:
            # 检查单引号是否匹配
            single_quotes = attr.count("'")
            if single_quotes % 2 != 0:
                problematic.append(attr[:50] + "..." if len(attr) > 50 else attr)
        
        if problematic:
            print(f"  ✗ 发现 {len(problematic)} 个可能有问题的 onclick:")
            for p in problematic[:3]:
                print(f"      {p}")
            self.issues.append(f"{len(problematic)} 个 onclick 引号可能不匹配")
        else:
            print(f"  ✓ 所有 onclick 引号正确 ({len(onclick_attrs)} 个)")
    
    def check_special_chars_in_json(self):
        """检查JSON数据中的特殊字符"""
        print("\n" + "="*70)
        print("检查 JSON 数据中的特殊字符")
        print("="*70)
        
        # 检查PRESET_ROLES
        preset_start = self.content.find('PRESET_ROLES = [')
        preset_end = self.content.find(']\n\nQUICK_COMMANDS', preset_start)
        
        if preset_start != -1 and preset_end != -1:
            preset_content = self.content[preset_start:preset_end]
            
            # 检查是否有未转义的换行符在字符串中
            lines = preset_content.split('\n')
            for i, line in enumerate(lines):
                if '"' in line and line.strip().endswith('"'):
                    # 检查下一行是否以"开头（多行字符串）
                    if i + 1 < len(lines) and lines[i + 1].strip().startswith('"'):
                        print(f"  ✗ 发现可能的多行字符串 (行 {i})")
                        self.issues.append("PRESET_ROLES 中可能有多行字符串")
                        break
            else:
                print("  ✓ PRESET_ROLES 格式正确")
    
    def check_script_placement(self, html):
        """检查script标签位置"""
        print("\n" + "="*70)
        print("检查 script 标签位置")
        print("="*70)
        
        # 检查script是否在body末尾
        body_end = html.rfind('</body>')
        script_end = html.rfind('</script>')
        
        if body_end != -1 and script_end != -1:
            if script_end < body_end:
                print("  ✓ script 标签在 body 结束前 (正确)")
            else:
                print("  ✗ script 标签在 body 结束之后")
                self.issues.append("script 标签位置错误")
        
        # 检查init调用位置
        init_call = html.find('init();')
        if init_call != -1 and script_end != -1:
            if init_call < script_end:
                print("  ✓ init() 调用在 script 标签内")
            else:
                print("  ✗ init() 调用在 script 标签外")
                self.issues.append("init() 调用位置错误")
    
    def check_duplicate_ids(self, html):
        """检查重复的ID"""
        print("\n" + "="*70)
        print("检查重复的 ID")
        print("="*70)
        
        ids = re.findall(r'id="([^"]+)"', html)
        id_counts = {}
        for id in ids:
            id_counts[id] = id_counts.get(id, 0) + 1
        
        duplicates = {k: v for k, v in id_counts.items() if v > 1}
        
        if duplicates:
            print(f"  ✗ 发现 {len(duplicates)} 个重复的 ID:")
            for id, count in list(duplicates.items())[:5]:
                print(f"      '{id}': {count} 次")
            self.issues.append(f"发现 {len(duplicates)} 个重复的 ID")
        else:
            print(f"  ✓ 所有 ID 唯一 ({len(ids)} 个)")
    
    def check_finetune_buttons(self, html):
        """专门检查微调页面的按钮"""
        print("\n" + "="*70)
        print("检查微调页面按钮")
        print("="*70)
        
        # 查找finetuneTab
        finetune_match = re.search(r'<div id="finetuneTab".*?</div>\s*</div>\s*</div>\s*</div>\s*<div id="rolesTab"', html, re.DOTALL)
        if finetune_match:
            finetune_html = finetune_match.group(0)
            
            # 查找按钮
            buttons = re.findall(r'<button[^>]*onclick="([^"]*)"[^>]*>([^<]*)</button>', finetune_html)
            print(f"找到 {len(buttons)} 个按钮:")
            
            for onclick, text in buttons:
                func_name = onclick.split('(')[0].strip()
                # 检查函数是否定义
                pattern = rf'function\s+{re.escape(func_name)}\s*\('
                if re.search(pattern, html):
                    print(f"  ✓ '{text.strip()}' -> {func_name}() 已定义")
                else:
                    print(f"  ✗ '{text.strip()}' -> {func_name}() 未定义")
                    self.issues.append(f"微调页面按钮 '{text.strip()}' 调用的函数 {func_name} 未定义")
        else:
            print("  ! 无法提取 finetuneTab 内容")
    
    def run(self):
        print("="*70)
        print("深度诊断工具")
        print("="*70)
        
        self.load_file()
        html = self.extract_html_template()
        
        if html:
            self.check_tab_content_structure(html)
            self.check_button_nesting(html)
            self.check_quotes_in_onclick(html)
            self.check_special_chars_in_json()
            self.check_script_placement(html)
            self.check_duplicate_ids(html)
            self.check_finetune_buttons(html)
        
        print("\n" + "="*70)
        print("诊断报告")
        print("="*70)
        
        if not self.issues:
            print("\n✓ 未发现明显问题")
            print("\n如果按钮仍然不工作，请尝试:")
            print("  1. 在浏览器中按 F12 打开开发者工具")
            print("  2. 查看 Console 标签页是否有红色错误")
            print("  3. 在 Elements 标签页检查按钮元素")
            print("  4. 在 Network 标签页刷新页面看是否有加载错误")
        else:
            print(f"\n发现 {len(self.issues)} 个问题:")
            for i, issue in enumerate(self.issues, 1):
                print(f"  {i}. {issue}")

if __name__ == '__main__':
    diagnostic = DeepDiagnostic()
    diagnostic.run()
