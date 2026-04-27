#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目检查工具
检查代码质量、潜在错误和性能问题
"""

import os
import re
import ast
import sys
from pathlib import Path
from typing import List, Dict, Tuple

class ProjectChecker:
    """项目检查器"""
    
    def __init__(self, project_dir: str = '.'):
        self.project_dir = Path(project_dir)
        self.issues = []
        self.warnings = []
        self.optimizations = []
    
    def check_all(self):
        """运行所有检查"""
        print("="*70)
        print("项目全面检查")
        print("="*70)
        
        self.check_main_file()
        self.check_imports()
        self.check_syntax_errors()
        self.check_common_issues()
        self.check_performance_issues()
        self.check_security_issues()
        
        self.print_report()
    
    def check_main_file(self):
        """检查主文件"""
        print("\n[1/6] 检查主文件 qwen3_web.py...")
        
        main_file = self.project_dir / 'qwen3_web.py'
        if not main_file.exists():
            self.issues.append("主文件 qwen3_web.py 不存在")
            return
        
        content = main_file.read_text(encoding='utf-8')
        
        # 检查文件大小
        file_size = len(content)
        if file_size > 500000:  # 500KB
            self.warnings.append(f"主文件过大 ({file_size/1024:.1f} KB)，建议拆分")
        
        # 检查函数数量
        functions = re.findall(r'^def \w+\(', content, re.MULTILINE)
        if len(functions) > 50:
            self.warnings.append(f"函数数量过多 ({len(functions)} 个)，建议模块化")
        
        # 检查HTML模板
        if 'HTML_TEMPLATE' in content:
            template_match = re.search(r'HTML_TEMPLATE = """(.*?)"""', content, re.DOTALL)
            if template_match:
                template_size = len(template_match.group(1))
                if template_size > 100000:  # 100KB
                    self.optimizations.append(f"HTML模板过大 ({template_size/1024:.1f} KB)，建议使用模板文件")
        
        # 检查全局变量
        global_vars = re.findall(r'^[A-Z_]+\s*=', content, re.MULTILINE)
        if len(global_vars) > 30:
            self.warnings.append(f"全局常量过多 ({len(global_vars)} 个)")
        
        # 检查硬编码的密钥或密码
        sensitive_patterns = [
            (r'password\s*=\s*["\'][^"\']+["\']', "硬编码密码"),
            (r'secret\s*=\s*["\'][^"\']+["\']', "硬编码密钥"),
            (r'api_key\s*=\s*["\'][^"\']+["\']', "硬编码API密钥"),
        ]
        
        for pattern, desc in sensitive_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                self.warnings.append(f"发现{desc}，建议使用环境变量")
        
        # 检查SQL注入风险
        sql_patterns = [
            r'execute\s*\(\s*["\'].*%s',
            r'execute\s*\(\s*["\'].*\+',
            r'execute\s*\(\s*f["\']',
        ]
        
        for pattern in sql_patterns:
            if re.search(pattern, content):
                self.issues.append("可能存在SQL注入风险，请使用参数化查询")
                break
        
        # 检查异常处理
        try_except = re.findall(r'try:', content)
        bare_except = re.findall(r'except\s*:', content)
        
        if len(bare_except) > len(try_except) * 0.5:
            self.warnings.append(f"裸except过多 ({len(bare_except)} 个)，建议指定异常类型")
        
        print(f"  ✓ 文件大小: {file_size/1024:.1f} KB")
        print(f"  ✓ 函数数量: {len(functions)}")
        print(f"  ✓ 全局常量: {len(global_vars)}")
    
    def check_imports(self):
        """检查导入"""
        print("\n[2/6] 检查导入...")
        
        main_file = self.project_dir / 'qwen3_web.py'
        content = main_file.read_text(encoding='utf-8')
        
        # 检查未使用的导入（简化检查）
        imports = re.findall(r'^(?:from|import)\s+(\S+)', content, re.MULTILINE)
        
        # 检查重复导入
        from collections import Counter
        duplicates = [item for item, count in Counter(imports).items() if count > 1]
        if duplicates:
            self.warnings.append(f"重复导入: {', '.join(duplicates)}")
        
        # 检查导入顺序
        std_lib = ['os', 'sys', 'json', 're', 'time', 'datetime', 'typing', 'pathlib', 'hashlib', 'base64', 'uuid', 'secrets', 'threading', 'queue', 'logging', 'sqlite3', 'statistics', 'ast', 'functools', 'dataclasses', 'enum', 'collections', 'copy', 'random', 'string', 'math', 'warnings', 'traceback', 'inspect', 'types', 'io', 'csv', 'html']
        
        third_party = ['flask', 'requests', 'numpy', 'torch', 'transformers', 'PIL', 'cv2', 'sklearn', 'psutil', 'cryptography', 'chromadb', 'pyjsparser']
        
        import_lines = content.split('\n')
        std_imports = []
        third_imports = []
        local_imports = []
        
        for line in import_lines:
            line = line.strip()
            if line.startswith('import ') or line.startswith('from '):
                module = line.split()[1].split('.')[0]
                if module in std_lib:
                    std_imports.append(module)
                elif module in third_party:
                    third_imports.append(module)
                else:
                    local_imports.append(module)
        
        print(f"  ✓ 标准库导入: {len(std_imports)} 个")
        print(f"  ✓ 第三方导入: {len(third_imports)} 个")
        print(f"  ✓ 本地导入: {len(local_imports)} 个")
    
    def check_syntax_errors(self):
        """检查语法错误"""
        print("\n[3/6] 检查语法错误...")
        
        py_files = list(self.project_dir.glob('*.py'))
        
        for file in py_files:
            if file.name.startswith('test_') or file.name.startswith('check_'):
                continue
            
            try:
                content = file.read_text(encoding='utf-8')
                ast.parse(content)
            except SyntaxError as e:
                self.issues.append(f"{file.name}: 语法错误 - {e}")
            except Exception as e:
                self.warnings.append(f"{file.name}: 解析错误 - {e}")
        
        print(f"  ✓ 检查了 {len(py_files)} 个Python文件")
    
    def check_common_issues(self):
        """检查常见问题"""
        print("\n[4/6] 检查常见问题...")
        
        main_file = self.project_dir / 'qwen3_web.py'
        content = main_file.read_text(encoding='utf-8')
        
        # 检查print语句（生产环境应该使用日志）
        prints = re.findall(r'^\s*print\s*\(', content, re.MULTILINE)
        if len(prints) > 20:
            self.optimizations.append(f"print语句过多 ({len(prints)} 个)，建议改用日志系统")
        
        # 检查TODO注释
        todos = re.findall(r'#\s*TODO', content, re.IGNORECASE)
        if todos:
            self.warnings.append(f"发现 {len(todos)} 个TODO待办事项")
        
        # 检查硬编码路径
        paths = re.findall(r'["\']([A-Za-z]:\\[^"\']+)["\']', content)
        if paths:
            self.warnings.append(f"发现 {len(paths)} 个硬编码路径")
        
        # 检查循环导入风险
        circular_imports = re.findall(r'from\s+(\w+)\s+import.*\n.*import\s+\1', content)
        if circular_imports:
            self.warnings.append("可能存在循环导入风险")
        
        # 检查可变默认参数
        mutable_defaults = re.findall(r'def \w+\([^)]*=\s*(\[|\{)', content)
        if mutable_defaults:
            self.issues.append("发现可变默认参数，可能导致意外行为")
    
    def check_performance_issues(self):
        """检查性能问题"""
        print("\n[5/6] 检查性能问题...")
        
        main_file = self.project_dir / 'qwen3_web.py'
        content = main_file.read_text(encoding='utf-8')
        
        # 检查字符串拼接
        string_concat = re.findall(r'\+\s*["\']', content)
        if len(string_concat) > 50:
            self.optimizations.append(f"大量字符串拼接 ({len(string_concat)} 处)，建议使用f-string或join")
        
        # 检查列表推导式外的循环
        loops = re.findall(r'^\s*for\s+\w+\s+in\s+', content, re.MULTILINE)
        if len(loops) > 30:
            self.optimizations.append(f"循环较多 ({len(loops)} 个)，检查是否可用向量化操作")
        
        # 检查文件IO
        file_ops = re.findall(r'open\s*\(', content)
        if len(file_ops) > 20:
            self.optimizations.append(f"文件操作较多 ({len(file_ops)} 处)，建议使用上下文管理器")
        
        # 检查正则编译
        regex_compile = re.findall(r're\.compile', content)
        inline_regex = re.findall(r're\.(search|match|findall)', content)
        if len(inline_regex) > len(regex_compile) * 3:
            self.optimizations.append("建议预编译常用正则表达式")
    
    def check_security_issues(self):
        """检查安全问题"""
        print("\n[6/6] 检查安全问题...")
        
        main_file = self.project_dir / 'qwen3_web.py'
        content = main_file.read_text(encoding='utf-8')
        
        # 检查eval使用
        eval_usage = re.findall(r'\beval\s*\(', content)
        if eval_usage:
            self.issues.append(f"发现 {len(eval_usage)} 处eval使用，存在安全风险")
        
        # 检查exec使用
        exec_usage = re.findall(r'\bexec\s*\(', content)
        if exec_usage:
            self.issues.append(f"发现 {len(exec_usage)} 处exec使用，存在安全风险")
        
        # 检查pickle使用
        pickle_usage = re.findall(r'pickle\.(load|loads)', content)
        if pickle_usage:
            self.warnings.append("使用pickle加载数据存在安全风险")
        
        # 检查yaml加载
        yaml_usage = re.findall(r'yaml\.load', content)
        if yaml_usage:
            self.warnings.append("yaml.load不安全，建议使用yaml.safe_load")
        
        # 检查调试模式
        if 'debug=True' in content or 'DEBUG = True' in content:
            self.warnings.append("调试模式已开启，生产环境应关闭")
        
        # 检查CORS配置
        cors = re.findall(r'CORS', content)
        if cors:
            self.warnings.append("检查CORS配置是否过于宽松")
    
    def print_report(self):
        """打印检查报告"""
        print("\n" + "="*70)
        print("检查报告")
        print("="*70)
        
        if self.issues:
            print(f"\n❌ 发现 {len(self.issues)} 个严重问题:")
            for i, issue in enumerate(self.issues, 1):
                print(f"  {i}. {issue}")
        
        if self.warnings:
            print(f"\n⚠️  发现 {len(self.warnings)} 个警告:")
            for i, warning in enumerate(self.warnings, 1):
                print(f"  {i}. {warning}")
        
        if self.optimizations:
            print(f"\n💡 发现 {len(self.optimizations)} 个优化建议:")
            for i, opt in enumerate(self.optimizations, 1):
                print(f"  {i}. {opt}")
        
        if not self.issues and not self.warnings and not self.optimizations:
            print("\n✅ 代码检查通过，未发现明显问题！")
        
        print("\n" + "="*70)

if __name__ == '__main__':
    checker = ProjectChecker()
    checker.check_all()
