#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
专业化代码执行系统 - 深度专业化的代码执行环境
功能: 多语言支持、代码分析、性能优化、安全检查
"""

import subprocess
import tempfile
import os
import json
import re
import ast
import sys
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import threading
import resource


class CodeLanguage(Enum):
    """支持的编程语言"""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    BASH = "bash"
    SQL = "sql"
    JAVA = "java"
    CPP = "cpp"
    GO = "go"
    RUST = "rust"


@dataclass
class CodeExecutionResult:
    """代码执行结果"""
    success: bool
    output: str
    error: Optional[str] = None
    execution_time: float = 0.0
    memory_usage: int = 0
    language: str = ""
    analysis: Dict = field(default_factory=dict)
    suggestions: List[str] = field(default_factory=list)


class CodeSecurityChecker:
    """代码安全检查器"""
    
    # 危险模式列表
    DANGEROUS_PATTERNS = {
        'python': [
            r'__import__\s*\(',
            r'import\s+os\.system',
            r'subprocess\.call',
            r'subprocess\.run',
            r'eval\s*\(',
            r'exec\s*\(',
            r'compile\s*\(',
            r'open\s*\([^)]*[\"\']/(etc|bin|usr|var)',
            r'os\.remove',
            r'os\.rmdir',
            r'shutil\.rmtree',
            r'socket\.',
            r'requests\.',
            r'urllib\.request\.urlopen',
        ],
        'javascript': [
            r'eval\s*\(',
            r'Function\s*\(',
            r'setTimeout\s*\([^,]*,[^)]*\)',
            r'setInterval\s*\(',
            r'document\.write',
            r'innerHTML\s*=',
            r'XMLHttpRequest',
            r'fetch\s*\(',
        ],
        'bash': [
            r'rm\s+-rf',
            r'>\s*/dev/',
            r'curl\s+.*\|.*sh',
            r'wget\s+.*\|.*sh',
            r'mkfs',
            r'dd\s+if=',
        ]
    }
    
    @classmethod
    def check_code(cls, code: str, language: str) -> Tuple[bool, List[str]]:
        """
        检查代码安全性
        
        Returns:
            (是否安全, 警告列表)
        """
        warnings = []
        patterns = cls.DANGEROUS_PATTERNS.get(language, [])
        
        for pattern in patterns:
            if re.search(pattern, code, re.IGNORECASE):
                warnings.append(f"发现潜在危险模式: {pattern}")
        
        # 检查导入语句
        if language == 'python':
            try:
                tree = ast.parse(code)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if alias.name in ['os', 'sys', 'subprocess', 'socket', 'requests']:
                                warnings.append(f"使用了敏感模块: {alias.name}")
                    elif isinstance(node, ast.ImportFrom):
                        if node.module in ['os', 'sys', 'subprocess', 'socket', 'requests']:
                            warnings.append(f"从敏感模块导入: {node.module}")
            except SyntaxError:
                warnings.append("代码语法错误，无法完成安全检查")
        
        is_safe = len(warnings) == 0
        return is_safe, warnings


class CodeAnalyzer:
    """代码分析器"""
    
    def analyze(self, code: str, language: str) -> Dict:
        """分析代码"""
        analysis = {
            'lines': len(code.split('\n')),
            'characters': len(code),
            'functions': 0,
            'classes': 0,
            'comments': 0,
            'complexity': 0,
            'issues': [],
            'metrics': {}
        }
        
        if language == 'python':
            analysis.update(self._analyze_python(code))
        elif language in ['javascript', 'typescript']:
            analysis.update(self._analyze_javascript(code))
        
        return analysis
    
    def _analyze_python(self, code: str) -> Dict:
        """分析Python代码"""
        result = {
            'functions': len(re.findall(r'\bdef\s+\w+', code)),
            'classes': len(re.findall(r'\bclass\s+\w+', code)),
            'imports': len(re.findall(r'^(import|from)\s+', code, re.MULTILINE)),
            'comments': len(re.findall(r'#.*', code)),
            'docstrings': len(re.findall(r'"""[\s\S]*?"""', code)),
        }
        
        # 计算圈复杂度（简化版）
        complexity = 0
        complexity += len(re.findall(r'\bif\b', code))
        complexity += len(re.findall(r'\belif\b', code))
        complexity += len(re.findall(r'\bfor\b', code))
        complexity += len(re.findall(r'\bwhile\b', code))
        complexity += len(re.findall(r'\bexcept\b', code))
        complexity += len(re.findall(r'\bwith\b', code))
        result['complexity'] = complexity
        
        # 检查代码风格问题
        issues = []
        if len(code) > 1000 and result['comments'] < 5:
            issues.append({
                'type': 'style',
                'message': '代码较长但注释较少，建议添加更多注释',
                'severity': 'warning'
            })
        
        if 'print(' in code and 'logging' not in code:
            issues.append({
                'type': 'best_practice',
                'message': '建议使用logging模块替代print',
                'severity': 'suggestion'
            })
        
        result['issues'] = issues
        return result
    
    def _analyze_javascript(self, code: str) -> Dict:
        """分析JavaScript代码"""
        result = {
            'functions': len(re.findall(r'\bfunction\b|\b=>\s*\{', code)),
            'classes': len(re.findall(r'\bclass\s+\w+', code)),
            'imports': len(re.findall(r'\bimport\b|\brequire\s*\(', code)),
            'comments': len(re.findall(r'//.*|/\*[\s\S]*?\*/', code)),
        }
        return result


class CodeOptimizer:
    """代码优化建议器"""
    
    def get_suggestions(self, code: str, language: str, analysis: Dict) -> List[str]:
        """获取优化建议"""
        suggestions = []
        
        if language == 'python':
            suggestions.extend(self._python_suggestions(code, analysis))
        elif language in ['javascript', 'typescript']:
            suggestions.extend(self._javascript_suggestions(code, analysis))
        
        return suggestions
    
    def _python_suggestions(self, code: str, analysis: Dict) -> List[str]:
        """Python优化建议"""
        suggestions = []
        
        # 性能建议
        if 'for ' in code and 'range(len(' in code:
            suggestions.append("建议使用 `enumerate()` 替代 `range(len())`")
        
        if re.search(r'for.*in.*:\s*\n\s*if.*:\s*\n\s*\w+\.append', code):
            suggestions.append("考虑使用列表推导式替代循环+条件+append模式")
        
        if ' + ' in code and ('for ' in code or 'while ' in code):
            suggestions.append("循环中字符串拼接建议使用 `join()` 方法")
        
        # 代码质量建议
        if analysis.get('complexity', 0) > 10:
            suggestions.append("函数复杂度较高，建议拆分为更小的函数")
        
        if analysis.get('lines', 0) > 50 and analysis.get('functions', 0) == 0:
            suggestions.append("代码较长但没有函数，建议适当封装")
        
        # 安全检查建议
        if 'except:' in code:
            suggestions.append("建议捕获具体异常类型，避免使用裸except")
        
        return suggestions
    
    def _javascript_suggestions(self, code: str, analysis: Dict) -> List[str]:
        """JavaScript优化建议"""
        suggestions = []
        
        if 'var ' in code:
            suggestions.append("建议使用 `let` 或 `const` 替代 `var`")
        
        if 'function' in code and '=>' not in code:
            suggestions.append("适当使用箭头函数可以使代码更简洁")
        
        return suggestions


class ProfessionalCodeExecutor:
    """专业化代码执行器"""
    
    def __init__(self):
        self.analyzer = CodeAnalyzer()
        self.optimizer = CodeOptimizer()
        self.security_checker = CodeSecurityChecker()
        self.execution_timeout = 30  # 秒
        self.max_memory = 256 * 1024 * 1024  # 256MB
    
    def execute(self, code: str, language: str = "python", 
                enable_analysis: bool = True,
                enable_optimization: bool = True,
                enable_security_check: bool = True) -> CodeExecutionResult:
        """
        执行代码
        
        Args:
            code: 源代码
            language: 编程语言
            enable_analysis: 是否启用代码分析
            enable_optimization: 是否启用优化建议
            enable_security_check: 是否启用安全检查
        
        Returns:
            CodeExecutionResult
        """
        start_time = datetime.now()
        
        # 安全检查
        if enable_security_check:
            is_safe, warnings = self.security_checker.check_code(code, language)
            if not is_safe:
                return CodeExecutionResult(
                    success=False,
                    output="",
                    error=f"代码安全检查未通过:\n" + "\n".join(warnings),
                    execution_time=0,
                    language=language
                )
        
        # 代码分析
        analysis = {}
        if enable_analysis:
            analysis = self.analyzer.analyze(code, language)
        
        # 获取优化建议
        suggestions = []
        if enable_optimization:
            suggestions = self.optimizer.get_suggestions(code, language, analysis)
        
        # 执行代码
        try:
            if language == CodeLanguage.PYTHON.value:
                output, error = self._execute_python(code)
            elif language == CodeLanguage.JAVASCRIPT.value:
                output, error = self._execute_javascript(code)
            elif language == CodeLanguage.BASH.value:
                output, error = self._execute_bash(code)
            elif language == CodeLanguage.SQL.value:
                output, error = self._execute_sql(code)
            else:
                output, error = f"暂不支持 {language} 语言", None
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return CodeExecutionResult(
                success=error is None,
                output=output,
                error=error,
                execution_time=execution_time,
                language=language,
                analysis=analysis,
                suggestions=suggestions
            )
            
        except Exception as e:
            return CodeExecutionResult(
                success=False,
                output="",
                error=f"执行错误: {str(e)}",
                execution_time=(datetime.now() - start_time).total_seconds(),
                language=language,
                analysis=analysis,
                suggestions=suggestions
            )
    
    def _execute_python(self, code: str) -> Tuple[str, Optional[str]]:
        """执行Python代码"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            result = subprocess.run(
                [sys.executable, temp_file],
                capture_output=True,
                text=True,
                timeout=self.execution_timeout
            )
            
            output = result.stdout
            error = result.stderr if result.returncode != 0 else None
            
            return output, error
            
        except subprocess.TimeoutExpired:
            return "", f"执行超时（超过 {self.execution_timeout} 秒）"
        finally:
            os.unlink(temp_file)
    
    def _execute_javascript(self, code: str) -> Tuple[str, Optional[str]]:
        """执行JavaScript代码"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            result = subprocess.run(
                ['node', temp_file],
                capture_output=True,
                text=True,
                timeout=self.execution_timeout
            )
            
            output = result.stdout
            error = result.stderr if result.returncode != 0 else None
            
            return output, error
            
        except FileNotFoundError:
            return "", "Node.js 未安装，无法执行 JavaScript 代码"
        except subprocess.TimeoutExpired:
            return "", f"执行超时（超过 {self.execution_timeout} 秒）"
        finally:
            os.unlink(temp_file)
    
    def _execute_bash(self, code: str) -> Tuple[str, Optional[str]]:
        """执行Bash代码"""
        try:
            result = subprocess.run(
                code,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.execution_timeout
            )
            
            output = result.stdout
            error = result.stderr if result.returncode != 0 else None
            
            return output, error
            
        except subprocess.TimeoutExpired:
            return "", f"执行超时（超过 {self.execution_timeout} 秒）"
    
    def _execute_sql(self, code: str) -> Tuple[str, Optional[str]]:
        """执行SQL代码（语法检查）"""
        # SQL 语法检查（简化版）
        keywords = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER']
        has_keyword = any(kw in code.upper() for kw in keywords)
        
        if not has_keyword:
            return "", "无效的 SQL 语句"
        
        # 检查基本语法
        if code.count('(') != code.count(')'):
            return "", "括号不匹配"
        
        if code.count('"') % 2 != 0 or code.count("'") % 2 != 0:
            return "", "引号不匹配"
        
        return "SQL 语法检查通过\n注意：实际执行需要连接到数据库", None


# 全局执行器实例
professional_executor = ProfessionalCodeExecutor()


# 便捷函数
def execute_code_professional(code: str, language: str = "python", 
                              **options) -> CodeExecutionResult:
    """专业化代码执行"""
    return professional_executor.execute(code, language, **options)


def analyze_code_professional(code: str, language: str = "python") -> Dict:
    """专业化代码分析"""
    return professional_executor.analyzer.analyze(code, language)


def check_code_security(code: str, language: str = "python") -> Tuple[bool, List[str]]:
    """检查代码安全性"""
    return professional_executor.security_checker.check_code(code, language)


# 测试代码
if __name__ == '__main__':
    print("=" * 60)
    print("专业化代码执行系统测试")
    print("=" * 60)
    
    # 测试Python代码执行
    print("\n1. Python代码执行测试")
    python_code = """
# 计算斐波那契数列
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

result = [fibonacci(i) for i in range(10)]
print(f"斐波那契数列前10项: {result}")

# 统计分析
import statistics
data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
print(f"平均值: {statistics.mean(data)}")
print(f"标准差: {statistics.stdev(data)}")
"""
    
    result = execute_code_professional(python_code, "python")
    print(f"执行结果:\n{result.output}")
    print(f"执行时间: {result.execution_time:.3f}s")
    print(f"分析: {result.analysis}")
    print(f"优化建议: {result.suggestions}")
    
    # 测试代码分析
    print("\n2. 代码分析测试")
    code_to_analyze = """
def complex_function(data):
    result = []
    for i in range(len(data)):
        if data[i] > 0:
            result.append(data[i] * 2)
    return result
"""
    analysis = analyze_code_professional(code_to_analyze, "python")
    print(f"分析结果: {json.dumps(analysis, indent=2, ensure_ascii=False)}")
    
    # 测试安全检查
    print("\n3. 安全检查测试")
    dangerous_code = "import os; os.system('rm -rf /')"
    is_safe, warnings = check_code_security(dangerous_code, "python")
    print(f"是否安全: {is_safe}")
    print(f"警告: {warnings}")
    
    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)
