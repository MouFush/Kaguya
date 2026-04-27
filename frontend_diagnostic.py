"""
前端自我诊断与修复系统
自动检查前端入口问题并自我修复
"""

import re
import os
import sys
import json
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum


class IssueType(Enum):
    """问题类型"""
    MISSING_TAB_CONTENT = "missing_tab_content"
    MISSING_JS_FUNCTION = "missing_js_function"
    MISSING_API_ROUTE = "missing_api_route"
    CSS_CONFLICT = "css_conflict"
    EVENT_BINDING_ERROR = "event_binding_error"
    HTML_STRUCTURE_ERROR = "html_structure_error"
    IMPORT_ERROR = "import_error"


@dataclass
class Issue:
    """问题记录"""
    issue_type: IssueType
    severity: str  # critical, high, medium, low
    description: str
    location: str
    line_number: Optional[int] = None
    suggested_fix: str = ""
    auto_fixable: bool = False


@dataclass
class FixResult:
    """修复结果"""
    issue: Issue
    fixed: bool
    message: str
    backup_created: bool = False


class FrontendDiagnostic:
    """前端诊断器"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.content = ""
        self.lines = []
        self.issues: List[Issue] = []
        self.fix_results: List[FixResult] = []
        self.backup_path = ""
        
    def load_file(self) -> bool:
        """加载文件"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                self.content = f.read()
                self.lines = self.content.split('\n')
            return True
        except Exception as e:
            print(f"❌ 无法加载文件: {e}")
            return False
    
    def create_backup(self) -> bool:
        """创建备份"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        self.backup_path = f"{self.file_path}.backup_{timestamp}"
        try:
            with open(self.backup_path, 'w', encoding='utf-8') as f:
                f.write(self.content)
            print(f"✅ 备份已创建: {self.backup_path}")
            return True
        except Exception as e:
            print(f"⚠️ 无法创建备份: {e}")
            return False
    
    def save_file(self) -> bool:
        """保存文件"""
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                f.write(self.content)
            return True
        except Exception as e:
            print(f"❌ 无法保存文件: {e}")
            return False
    
    # ==================== 检查函数 ====================
    
    def check_tab_buttons(self):
        """检查标签页按钮"""
        print("\n🔍 检查标签页按钮...")
        
        # 查找所有按钮
        button_pattern = r'<button[^>]*onclick="switchTab\(\'([^\']+)\'[^>]*>([^<]+)</button>'
        buttons = re.findall(button_pattern, self.content)
        
        print(f"  找到 {len(buttons)} 个标签页按钮")
        
        for tab_id, button_text in buttons:
            # 检查对应的标签页内容是否存在
            tab_content_pattern = f'id="{tab_id}Tab"'
            if tab_content_pattern not in self.content:
                issue = Issue(
                    issue_type=IssueType.MISSING_TAB_CONTENT,
                    severity="high",
                    description=f"按钮 '{button_text}' (tab={tab_id}) 缺少对应的标签页内容",
                    location=f"sidebar-tabs",
                    suggested_fix=f"添加 <div id='{tab_id}Tab' class='tab-content'>...</div>",
                    auto_fixable=True
                )
                self.issues.append(issue)
                print(f"  ⚠️  {button_text}: 缺少标签页内容")
    
    def check_js_functions(self):
        """检查JavaScript函数"""
        print("\n🔍 检查JavaScript函数...")
        
        # 查找所有onclick调用的函数
        onclick_pattern = r'onclick="([^"]+)"'
        onclicks = re.findall(onclick_pattern, self.content)
        
        # 提取函数名
        function_calls = set()
        for onclick in onclicks:
            # 处理 switchTab('xxx', this) 格式
            match = re.match(r'(\w+)\(', onclick)
            if match:
                function_calls.add(match.group(1))
        
        print(f"  找到 {len(function_calls)} 个不同的函数调用")
        
        # 检查函数是否定义
        for func_name in function_calls:
            # 跳过内联JavaScript
            if '(' in func_name and ')' in func_name:
                continue
                
            func_pattern = f'function {func_name}\\('
            if not re.search(func_pattern, self.content):
                issue = Issue(
                    issue_type=IssueType.MISSING_JS_FUNCTION,
                    severity="critical",
                    description=f"函数 '{func_name}' 被调用但未定义",
                    location="JavaScript",
                    suggested_fix=f"添加 function {func_name}() {{ ... }}",
                    auto_fixable=False
                )
                self.issues.append(issue)
                print(f"  ❌  {func_name}: 函数未定义")
    
    def check_api_routes(self):
        """检查API路由"""
        print("\n🔍 检查API路由...")
        
        # 查找所有fetch调用
        fetch_pattern = r'fetch\([\'"]([^\'"]+)[\'"]'
        fetches = re.findall(fetch_pattern, self.content)
        
        # 提取路由
        routes = set()
        for fetch_url in fetches:
            if fetch_url.startswith('/'):
                # 提取基础路由
                base_route = fetch_url.split('?')[0]
                routes.add(base_route)
        
        print(f"  找到 {len(routes)} 个API调用")
        
        # 检查Python后端是否定义了这些路由
        python_routes = self._extract_python_routes()
        
        for route in routes:
            # 简化路由进行匹配
            route_parts = route.split('/')
            found = False
            
            for py_route in python_routes:
                if route in py_route or py_route in route:
                    found = True
                    break
            
            if not found:
                issue = Issue(
                    issue_type=IssueType.MISSING_API_ROUTE,
                    severity="high",
                    description=f"API路由 '{route}' 在前端被调用但后端可能未定义",
                    location="API",
                    suggested_fix=f"添加 @app.route('{route}') 装饰器",
                    auto_fixable=False
                )
                self.issues.append(issue)
                print(f"  ⚠️  {route}: 后端路由可能缺失")
    
    def _extract_python_routes(self) -> List[str]:
        """提取Python路由"""
        routes = []
        route_pattern = r'@app\.route\([\'"]([^\'"]+)[\'"]'
        routes = re.findall(route_pattern, self.content)
        return routes
    
    def check_css_issues(self):
        """检查CSS问题"""
        print("\n🔍 检查CSS问题...")
        
        # 检查tab-content样式
        if '.tab-content { display: none' not in self.content:
            issue = Issue(
                issue_type=IssueType.CSS_CONFLICT,
                severity="critical",
                description="缺少 .tab-content 基础样式",
                location="CSS",
                suggested_fix="添加 .tab-content { display: none; ... }",
                auto_fixable=True
            )
            self.issues.append(issue)
            print(f"  ❌  缺少 .tab-content 基础样式")
        
        if '.tab-content.active { display: flex' not in self.content:
            issue = Issue(
                issue_type=IssueType.CSS_CONFLICT,
                severity="critical",
                description="缺少 .tab-content.active 激活样式",
                location="CSS",
                suggested_fix="添加 .tab-content.active { display: flex; ... }",
                auto_fixable=True
            )
            self.issues.append(issue)
            print(f"  ❌  缺少 .tab-content.active 激活样式")
    
    def check_html_structure(self):
        """检查HTML结构"""
        print("\n🔍 检查HTML结构...")
        
        # 检查script标签
        script_open = self.content.count('<script>') + self.content.count('<script ')
        script_close = self.content.count('</script>')
        
        if script_open != script_close:
            issue = Issue(
                issue_type=IssueType.HTML_STRUCTURE_ERROR,
                severity="critical",
                description=f"script标签不匹配: {script_open} 开始, {script_close} 结束",
                location="HTML",
                suggested_fix="检查script标签配对",
                auto_fixable=False
            )
            self.issues.append(issue)
            print(f"  ❌  script标签不匹配")
        
        # 检查div标签（简单检查）
        div_open = self.content.count('<div')
        div_close = self.content.count('</div>')
        
        if abs(div_open - div_close) > 10:  # 允许一些误差
            issue = Issue(
                issue_type=IssueType.HTML_STRUCTURE_ERROR,
                severity="medium",
                description=f"div标签可能不匹配: {div_open} 开始, {div_close} 结束",
                location="HTML",
                suggested_fix="检查div标签配对",
                auto_fixable=False
            )
            self.issues.append(issue)
            print(f"  ⚠️  div标签可能不匹配")
    
    def check_imports(self):
        """检查导入语句"""
        print("\n🔍 检查导入语句...")
        
        # 检查新功能模块的导入
        new_modules = [
            ('autonomous_agent', 'AUTONOMOUS_AGENT_AVAILABLE'),
            ('code_agent', 'CODE_AGENT_AVAILABLE'),
            ('secure_sandbox', 'SECURE_SANDBOX_AVAILABLE')
        ]
        
        for module_name, flag_name in new_modules:
            if f'from {module_name} import' not in self.content:
                issue = Issue(
                    issue_type=IssueType.IMPORT_ERROR,
                    severity="high",
                    description=f"缺少 {module_name} 模块导入",
                    location="Python imports",
                    suggested_fix=f"添加 from {module_name} import ...",
                    auto_fixable=False
                )
                self.issues.append(issue)
                print(f"  ⚠️  缺少 {module_name} 导入")
    
    # ==================== 修复函数 ====================
    
    def fix_missing_tab_content(self, issue: Issue) -> FixResult:
        """修复缺失的标签页内容"""
        try:
            # 从issue描述中提取tab_id
            match = re.search(r"tab=(\w+)", issue.description)
            if not match:
                return FixResult(issue, False, "无法提取tab_id")
            
            tab_id = match.group(1)
            
            # 创建基本的标签页内容
            tab_content = f'''
            <div id="{tab_id}Tab" class="tab-content">
                <div style="padding:12px;">
                    <div style="text-align:center;padding:40px;color:var(--text-muted);">
                        <div style="font-size:48px;margin-bottom:16px;">🚧</div>
                        <div style="font-size:16px;font-weight:600;margin-bottom:8px;">功能开发中</div>
                        <div style="font-size:12px;">此功能正在开发中，敬请期待</div>
                    </div>
                </div>
            </div>
'''
            
            # 找到插入位置（在sidebar-footer之前）
            footer_pattern = r'(<div class="sidebar-footer">)'
            match = re.search(footer_pattern, self.content)
            if match:
                insert_pos = match.start()
                self.content = self.content[:insert_pos] + tab_content + '\n' + self.content[insert_pos:]
                return FixResult(issue, True, f"已添加 {tab_id}Tab 内容", True)
            
            return FixResult(issue, False, "无法找到插入位置")
            
        except Exception as e:
            return FixResult(issue, False, f"修复失败: {e}")
    
    def fix_css_issues(self, issue: Issue) -> FixResult:
        """修复CSS问题"""
        try:
            if "tab-content 基础样式" in issue.description:
                css = '''        .tab-content { display: none; flex: 1; overflow-y: auto; }
'''
                # 在style标签内添加
                style_match = re.search(r'<style>(.*?)</style>', self.content, re.DOTALL)
                if style_match:
                    insert_pos = style_match.start(1)
                    self.content = self.content[:insert_pos] + css + self.content[insert_pos:]
                    return FixResult(issue, True, "已添加 .tab-content 样式", True)
            
            elif "tab-content.active 激活样式" in issue.description:
                css = '''        .tab-content.active { display: flex; flex-direction: column; }
'''
                style_match = re.search(r'<style>(.*?)</style>', self.content, re.DOTALL)
                if style_match:
                    insert_pos = style_match.start(1)
                    self.content = self.content[:insert_pos] + css + self.content[insert_pos:]
                    return FixResult(issue, True, "已添加 .tab-content.active 样式", True)
            
            return FixResult(issue, False, "无法修复CSS")
            
        except Exception as e:
            return FixResult(issue, False, f"修复失败: {e}")
    
    def apply_fixes(self):
        """应用自动修复"""
        print("\n🔧 应用自动修复...")
        
        auto_fixable_issues = [i for i in self.issues if i.auto_fixable]
        print(f"  发现 {len(auto_fixable_issues)} 个可自动修复的问题")
        
        if not auto_fixable_issues:
            print("  没有可自动修复的问题")
            return
        
        # 创建备份
        if not self.create_backup():
            print("  ⚠️ 无法创建备份，跳过修复")
            return
        
        for issue in auto_fixable_issues:
            print(f"\n  修复: {issue.description[:50]}...")
            
            if issue.issue_type == IssueType.MISSING_TAB_CONTENT:
                result = self.fix_missing_tab_content(issue)
            elif issue.issue_type == IssueType.CSS_CONFLICT:
                result = self.fix_css_issues(issue)
            else:
                result = FixResult(issue, False, "未实现自动修复")
            
            self.fix_results.append(result)
            
            if result.fixed:
                print(f"  ✅ {result.message}")
            else:
                print(f"  ❌ {result.message}")
        
        # 保存文件
        if self.save_file():
            print("\n✅ 修复已保存")
        else:
            print("\n❌ 保存失败")
    
    # ==================== 报告生成 ====================
    
    def generate_report(self) -> str:
        """生成诊断报告"""
        report = []
        report.append("=" * 60)
        report.append("前端自我诊断报告")
        report.append("=" * 60)
        report.append(f"检查文件: {self.file_path}")
        report.append(f"检查时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"总行数: {len(self.lines)}")
        report.append("")
        
        # 统计
        critical = len([i for i in self.issues if i.severity == "critical"])
        high = len([i for i in self.issues if i.severity == "high"])
        medium = len([i for i in self.issues if i.severity == "medium"])
        low = len([i for i in self.issues if i.severity == "low"])
        
        report.append("问题统计:")
        report.append(f"  严重: {critical}")
        report.append(f"  高: {high}")
        report.append(f"  中: {medium}")
        report.append(f"  低: {low}")
        report.append(f"  总计: {len(self.issues)}")
        report.append("")
        
        # 详细问题
        if self.issues:
            report.append("详细问题列表:")
            report.append("-" * 60)
            for i, issue in enumerate(self.issues, 1):
                report.append(f"\n{i}. [{issue.severity.upper()}] {issue.issue_type.value}")
                report.append(f"   描述: {issue.description}")
                report.append(f"   位置: {issue.location}")
                report.append(f"   可自动修复: {'是' if issue.auto_fixable else '否'}")
                if issue.suggested_fix:
                    report.append(f"   建议: {issue.suggested_fix}")
        
        # 修复结果
        if self.fix_results:
            report.append("\n" + "=" * 60)
            report.append("自动修复结果")
            report.append("=" * 60)
            for result in self.fix_results:
                status = "✅ 成功" if result.fixed else "❌ 失败"
                report.append(f"{status}: {result.message}")
                if result.backup_created:
                    report.append(f"   备份: {self.backup_path}")
        
        report.append("\n" + "=" * 60)
        return "\n".join(report)
    
    def run_diagnostic(self):
        """运行完整诊断"""
        print("=" * 60)
        print("前端自我诊断工具")
        print("=" * 60)
        
        if not self.load_file():
            return False
        
        print(f"\n📄 文件: {self.file_path}")
        print(f"📊 行数: {len(self.lines)}")
        
        # 运行所有检查
        self.check_tab_buttons()
        self.check_js_functions()
        self.check_api_routes()
        self.check_css_issues()
        self.check_html_structure()
        self.check_imports()
        
        # 生成报告
        report = self.generate_report()
        print("\n" + report)
        
        # 保存报告
        report_path = f"frontend_diagnostic_report_{time.strftime('%Y%m%d_%H%M%S')}.txt"
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"\n📄 报告已保存: {report_path}")
        except Exception as e:
            print(f"\n⚠️ 无法保存报告: {e}")
        
        # 询问是否修复
        auto_fixable_count = len([i for i in self.issues if i.auto_fixable])
        if auto_fixable_count > 0:
            print(f"\n🔧 发现 {auto_fixable_count} 个可自动修复的问题")
            response = input("是否应用自动修复? (y/n): ").lower().strip()
            if response == 'y':
                self.apply_fixes()
        
        return True


def main():
    """主函数"""
    # 默认检查的文件
    default_file = "qwen3_web_final.py"
    
    # 可以通过命令行参数指定文件
    if len(sys.argv) > 1:
        target_file = sys.argv[1]
    else:
        target_file = default_file
    
    # 检查文件是否存在
    if not os.path.exists(target_file):
        print(f"❌ 文件不存在: {target_file}")
        print(f"请确保在正确的目录运行，或使用: python frontend_diagnostic.py <文件路径>")
        return
    
    # 运行诊断
    diagnostic = FrontendDiagnostic(target_file)
    diagnostic.run_diagnostic()


if __name__ == "__main__":
    main()
