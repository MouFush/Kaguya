"""
代码智能体系统 - 项目级代码理解与生成
支持：代码分析、智能生成、自动审查、测试生成、Git集成
"""

import os
import re
import json
import ast
import subprocess
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from collections import defaultdict
import tempfile
import shutil


class CodeLanguage(Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    CPP = "cpp"
    GO = "go"
    RUST = "rust"


class CodeQualityLevel(Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"


@dataclass
class CodeSymbol:
    """代码符号（函数、类、变量等）"""
    name: str
    symbol_type: str  # function, class, method, variable, import
    line_start: int
    line_end: int
    file_path: str
    docstring: Optional[str] = None
    parameters: List[str] = field(default_factory=list)
    return_type: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    complexity: int = 0  # 圈复杂度


@dataclass
class CodeFile:
    """代码文件"""
    path: str
    language: CodeLanguage
    content: str
    symbols: List[CodeSymbol] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    exports: List[str] = field(default_factory=list)
    lines_count: int = 0
    comment_ratio: float = 0.0


@dataclass
class CodeReviewComment:
    """代码审查意见"""
    line: int
    severity: str  # error, warning, info
    category: str  # style, security, performance, bug
    message: str
    suggestion: Optional[str] = None
    rule_id: Optional[str] = None


@dataclass
class CodeReviewResult:
    """代码审查结果"""
    file_path: str
    overall_score: float
    quality_level: CodeQualityLevel
    comments: List[CodeReviewComment] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestCase:
    """测试用例"""
    name: str
    description: str
    code: str
    test_type: str  # unit, integration, e2e
    coverage_target: Optional[str] = None


class ASTAnalyzer:
    """AST代码分析器"""
    
    def __init__(self):
        self.supported_languages = {CodeLanguage.PYTHON}
    
    def analyze_file(self, file_path: str, content: str = None) -> CodeFile:
        """分析单个文件"""
        if content is None:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        
        language = self._detect_language(file_path)
        code_file = CodeFile(
            path=file_path,
            language=language,
            content=content,
            lines_count=len(content.split('\n'))
        )
        
        if language == CodeLanguage.PYTHON:
            self._analyze_python(code_file)
        
        return code_file
    
    def _detect_language(self, file_path: str) -> CodeLanguage:
        """检测编程语言"""
        ext = Path(file_path).suffix.lower()
        mapping = {
            '.py': CodeLanguage.PYTHON,
            '.js': CodeLanguage.JAVASCRIPT,
            '.ts': CodeLanguage.TYPESCRIPT,
            '.java': CodeLanguage.JAVA,
            '.cpp': CodeLanguage.CPP,
            '.go': CodeLanguage.GO,
            '.rs': CodeLanguage.RUST
        }
        return mapping.get(ext, CodeLanguage.PYTHON)
    
    def _analyze_python(self, code_file: CodeFile):
        """分析Python代码"""
        try:
            tree = ast.parse(code_file.content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    symbol = self._extract_function_symbol(node, code_file.path)
                    code_file.symbols.append(symbol)
                elif isinstance(node, ast.ClassDef):
                    symbol = self._extract_class_symbol(node, code_file.path)
                    code_file.symbols.append(symbol)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        code_file.imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        code_file.imports.append(f"{module}.{alias.name}")
            
            # 计算注释比例
            comment_lines = len(re.findall(r'#.*', code_file.content))
            code_file.comment_ratio = comment_lines / code_file.lines_count if code_file.lines_count > 0 else 0
            
        except SyntaxError as e:
            print(f"语法错误 in {code_file.path}: {e}")
    
    def _extract_function_symbol(self, node: ast.FunctionDef, file_path: str) -> CodeSymbol:
        """提取函数符号信息"""
        # 计算圈复杂度
        complexity = self._calculate_complexity(node)
        
        # 获取参数
        params = []
        for arg in node.args.args:
            param_str = arg.arg
            if arg.annotation:
                param_str += f": {ast.unparse(arg.annotation)}"
            params.append(param_str)
        
        # 获取返回类型
        return_type = None
        if node.returns:
            return_type = ast.unparse(node.returns)
        
        # 获取文档字符串
        docstring = ast.get_docstring(node)
        
        return CodeSymbol(
            name=node.name,
            symbol_type="function",
            line_start=node.lineno,
            line_end=node.end_lineno,
            file_path=file_path,
            docstring=docstring,
            parameters=params,
            return_type=return_type,
            complexity=complexity
        )
    
    def _extract_class_symbol(self, node: ast.ClassDef, file_path: str) -> CodeSymbol:
        """提取类符号信息"""
        # 获取基类
        bases = [ast.unparse(base) for base in node.bases]
        
        # 获取文档字符串
        docstring = ast.get_docstring(node)
        
        # 分析方法
        methods = []
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                methods.append(item.name)
        
        symbol = CodeSymbol(
            name=node.name,
            symbol_type="class",
            line_start=node.lineno,
            line_end=node.end_lineno,
            file_path=file_path,
            docstring=docstring,
            dependencies=bases
        )
        symbol.methods = methods  # 动态添加
        return symbol
    
    def _calculate_complexity(self, node: ast.AST) -> int:
        """计算圈复杂度"""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity


class CodeReviewer:
    """代码审查器"""
    
    def __init__(self):
        self.rules = self._load_rules()
    
    def _load_rules(self) -> List[Dict]:
        """加载审查规则"""
        return [
            {
                "id": "PY001",
                "category": "style",
                "severity": "warning",
                "pattern": r'def [a-zA-Z_][a-zA-Z0-9_]*\([^)]*\):\s*\n\s+[^\n"\']',
                "message": "函数缺少文档字符串",
                "suggestion": "请为函数添加文档字符串描述功能"
            },
            {
                "id": "PY002",
                "category": "security",
                "severity": "error",
                "pattern": r'eval\s*\(',
                "message": "使用了危险的eval函数",
                "suggestion": "避免使用eval，改用ast.literal_eval或json.loads"
            },
            {
                "id": "PY003",
                "category": "performance",
                "severity": "warning",
                "pattern": r'for\s+\w+\s+in\s+range\s*\(\s*len\s*\(',
                "message": "使用range(len())效率低下",
                "suggestion": "直接使用for item in iterable或enumerate()"
            },
            {
                "id": "PY004",
                "category": "bug",
                "severity": "error",
                "pattern": r'==\s*(True|False|None)',
                "message": "使用==比较单例对象",
                "suggestion": "使用'is'或'is not'比较True, False, None"
            },
            {
                "id": "PY005",
                "category": "style",
                "severity": "info",
                "pattern": r'print\s*\(',
                "message": "使用了print语句",
                "suggestion": "考虑使用logging模块替代print"
            }
        ]
    
    def review_file(self, code_file: CodeFile) -> CodeReviewResult:
        """审查单个文件"""
        comments = []
        
        # 应用规则
        for rule in self.rules:
            matches = re.finditer(rule["pattern"], code_file.content, re.MULTILINE)
            for match in matches:
                line_num = code_file.content[:match.start()].count('\n') + 1
                comment = CodeReviewComment(
                    line=line_num,
                    severity=rule["severity"],
                    category=rule["category"],
                    message=rule["message"],
                    suggestion=rule.get("suggestion"),
                    rule_id=rule["id"]
                )
                comments.append(comment)
        
        # 计算质量分数
        score = self._calculate_score(code_file, comments)
        quality_level = self._determine_quality_level(score)
        
        # 计算指标
        metrics = {
            "total_lines": code_file.lines_count,
            "comment_ratio": code_file.comment_ratio,
            "function_count": len([s for s in code_file.symbols if s.symbol_type == "function"]),
            "class_count": len([s for s in code_file.symbols if s.symbol_type == "class"]),
            "avg_complexity": sum(s.complexity for s in code_file.symbols) / max(len(code_file.symbols), 1),
            "issue_count": len(comments)
        }
        
        return CodeReviewResult(
            file_path=code_file.path,
            overall_score=score,
            quality_level=quality_level,
            comments=comments,
            metrics=metrics
        )
    
    def _calculate_score(self, code_file: CodeFile, comments: List[CodeReviewComment]) -> float:
        """计算质量分数"""
        base_score = 100.0
        
        # 根据问题严重程度扣分
        for comment in comments:
            if comment.severity == "error":
                base_score -= 10
            elif comment.severity == "warning":
                base_score -= 5
            elif comment.severity == "info":
                base_score -= 1
        
        # 注释比例加分
        if code_file.comment_ratio > 0.2:
            base_score += 5
        
        # 复杂度扣分
        high_complexity = sum(1 for s in code_file.symbols if s.complexity > 10)
        base_score -= high_complexity * 3
        
        return max(0, min(100, base_score))
    
    def _determine_quality_level(self, score: float) -> CodeQualityLevel:
        """确定质量等级"""
        if score >= 90:
            return CodeQualityLevel.EXCELLENT
        elif score >= 75:
            return CodeQualityLevel.GOOD
        elif score >= 60:
            return CodeQualityLevel.FAIR
        else:
            return CodeQualityLevel.POOR


class TestGenerator:
    """测试生成器"""
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
    
    def generate_tests(self, code_file: CodeFile, test_framework: str = "pytest") -> List[TestCase]:
        """为代码文件生成测试"""
        test_cases = []
        
        for symbol in code_file.symbols:
            if symbol.symbol_type == "function":
                test_case = self._generate_function_test(symbol, code_file, test_framework)
                if test_case:
                    test_cases.append(test_case)
            elif symbol.symbol_type == "class":
                test_cases.extend(self._generate_class_tests(symbol, code_file, test_framework))
        
        return test_cases
    
    def _generate_function_test(self, symbol: CodeSymbol, code_file: CodeFile, 
                                 test_framework: str) -> Optional[TestCase]:
        """为函数生成测试"""
        # 分析函数参数生成测试数据
        test_data = self._generate_test_data(symbol.parameters)
        
        test_code = f"""def test_{symbol.name}():
    \"\"\"测试 {symbol.name} 函数\"\"\"
    # Arrange
{self._format_test_data(test_data)}
    
    # Act
    result = {symbol.name}({', '.join(test_data.keys())})
    
    # Assert
    assert result is not None
    # TODO: 添加更多具体断言
"""
        
        return TestCase(
            name=f"test_{symbol.name}",
            description=f"测试 {symbol.name} 函数的基本功能",
            code=test_code,
            test_type="unit",
            coverage_target=symbol.name
        )
    
    def _generate_class_tests(self, symbol: CodeSymbol, code_file: CodeFile,
                               test_framework: str) -> List[TestCase]:
        """为类生成测试"""
        test_cases = []
        
        # 生成类实例化测试
        init_test = f"""def test_{symbol.name}_initialization():
    \"\"\"测试 {symbol.name} 类初始化\"\"\"
    instance = {symbol.name}()
    assert instance is not None
"""
        
        test_cases.append(TestCase(
            name=f"test_{symbol.name}_initialization",
            description=f"测试 {symbol.name} 类初始化",
            code=init_test,
            test_type="unit"
        ))
        
        return test_cases
    
    def _generate_test_data(self, parameters: List[str]) -> Dict[str, str]:
        """生成测试数据"""
        test_data = {}
        for param in parameters:
            param_name = param.split(':')[0].strip()
            # 根据参数名猜测类型
            if 'name' in param_name.lower():
                test_data[param_name] = '"test_name"'
            elif 'count' in param_name.lower() or 'num' in param_name.lower():
                test_data[param_name] = '42'
            elif 'list' in param_name.lower() or 'items' in param_name.lower():
                test_data[param_name] = '[1, 2, 3]'
            elif 'dict' in param_name.lower() or 'map' in param_name.lower():
                test_data[param_name] = '{"key": "value"}'
            else:
                test_data[param_name] = 'None'
        return test_data
    
    def _format_test_data(self, test_data: Dict[str, str]) -> str:
        """格式化测试数据"""
        lines = []
        for key, value in test_data.items():
            lines.append(f"    {key} = {value}")
        return '\n'.join(lines)


class GitIntegration:
    """Git集成"""
    
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
    
    def is_git_repo(self) -> bool:
        """检查是否为Git仓库"""
        git_dir = os.path.join(self.repo_path, '.git')
        return os.path.exists(git_dir)
    
    def get_status(self) -> Dict[str, List[str]]:
        """获取Git状态"""
        result = self._run_git_command(['status', '--porcelain'])
        
        staged = []
        unstaged = []
        untracked = []
        
        for line in result.stdout.split('\n'):
            if line:
                status = line[:2]
                file_path = line[3:]
                
                if status[0] != ' ':
                    staged.append(file_path)
                if status[1] != ' ':
                    unstaged.append(file_path)
                if status == '??':
                    untracked.append(file_path)
        
        return {
            "staged": staged,
            "unstaged": unstaged,
            "untracked": untracked
        }
    
    def commit(self, message: str, files: List[str] = None) -> bool:
        """提交更改"""
        try:
            # 添加文件
            if files:
                self._run_git_command(['add'] + files)
            else:
                self._run_git_command(['add', '.'])
            
            # 提交
            self._run_git_command(['commit', '-m', message])
            return True
        except Exception as e:
            print(f"提交失败: {e}")
            return False
    
    def create_branch(self, branch_name: str, base_branch: str = "main") -> bool:
        """创建分支"""
        try:
            self._run_git_command(['checkout', '-b', branch_name, base_branch])
            return True
        except Exception as e:
            print(f"创建分支失败: {e}")
            return False
    
    def generate_pr_description(self, branch_name: str) -> str:
        """生成PR描述"""
        # 获取提交历史
        result = self._run_git_command(['log', 'main..HEAD', '--oneline'])
        commits = result.stdout.strip().split('\n')
        
        # 获取更改的文件
        diff_result = self._run_git_command(['diff', 'main..HEAD', '--name-only'])
        changed_files = diff_result.stdout.strip().split('\n')
        
        description = f"""## 变更摘要

### 提交历史
"""
        for commit in commits:
            if commit:
                description += f"- {commit}\n"
        
        description += f"\n### 更改的文件\n"
        for file in changed_files:
            if file:
                description += f"- {file}\n"
        
        description += """
### 检查清单
- [ ] 代码通过所有测试
- [ ] 代码审查已完成
- [ ] 文档已更新
"""
        
        return description
    
    def _run_git_command(self, args: List[str]) -> subprocess.CompletedProcess:
        """运行Git命令"""
        cmd = ['git'] + args
        result = subprocess.run(
            cmd,
            cwd=self.repo_path,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise Exception(f"Git命令失败: {result.stderr}")
        
        return result


class ProjectAnalyzerService:
    def __init__(self, ast_analyzer: ASTAnalyzer):
        self.ast_analyzer = ast_analyzer
        self.files: Dict[str, CodeFile] = {}
        self.symbols_index: Dict[str, List[CodeSymbol]] = defaultdict(list)

    def analyze_project(self, project_path: str) -> Dict[str, Any]:
        print(f"正在分析项目: {project_path}")

        for root, dirs, files in os.walk(project_path):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'venv']]

            for file in files:
                if file.endswith(('.py', '.js', '.ts', '.java', '.cpp', '.go', '.rs')):
                    file_path = os.path.join(root, file)
                    try:
                        code_file = self.ast_analyzer.analyze_file(file_path)
                        self.files[file_path] = code_file

                        for symbol in code_file.symbols:
                            self.symbols_index[symbol.name].append(symbol)
                    except Exception as e:
                        print(f"分析文件失败 {file_path}: {e}")

        return {
            "total_files": len(self.files),
            "total_symbols": sum(len(f.symbols) for f in self.files.values()),
            "languages": list(set(f.language.value for f in self.files.values()))
        }


class CodeReviewService:
    def __init__(self, code_reviewer: CodeReviewer):
        self.code_reviewer = code_reviewer

    def review_project(self, files: Dict[str, CodeFile]) -> List[CodeReviewResult]:
        results = []
        for code_file in files.values():
            result = self.code_reviewer.review_file(code_file)
            results.append(result)
        return results


class TestGenerationService:
    def __init__(self, test_generator: TestGenerator):
        self.test_generator = test_generator

    def generate_tests_for_file(self, file_path: str, files: Dict[str, CodeFile],
                                 project_path: str) -> str:
        if file_path not in files:
            ast_analyzer = ASTAnalyzer()
            code_file = ast_analyzer.analyze_file(file_path)
            files[file_path] = code_file

        code_file = files[file_path]
        test_cases = self.test_generator.generate_tests(code_file)

        test_content = f"\"\"\"\nTests for {os.path.basename(file_path)}\n\"\"\"\n\n"
        test_content += "import pytest\n"
        rel_path = os.path.relpath(file_path, project_path)
        module_path = rel_path.replace(os.sep, '.').replace('.py', '')
        test_content += f"from {module_path} import *\n\n"

        for test_case in test_cases:
            test_content += f"\n{test_case.code}\n"

        return test_content


class CodeGenerationService:
    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    def generate_code(self, requirement: str, context: str, target_file: str = None) -> str:
        prompt = f"""请根据以下需求生成代码：

需求: {requirement}

项目上下文:
{context}

请生成完整、可运行的代码，包含：
1. 必要的导入语句
2. 文档字符串
3. 类型注解
4. 错误处理
"""

        if self.llm_client:
            generated_code = self.llm_client.generate(prompt)

            code_match = re.search(r'```python\n(.*?)\n```', generated_code, re.DOTALL)
            if code_match:
                generated_code = code_match.group(1)

            if target_file:
                os.makedirs(os.path.dirname(target_file), exist_ok=True)
                with open(target_file, 'w', encoding='utf-8') as f:
                    f.write(generated_code)

            return generated_code
        else:
            return "# 未配置LLM客户端，无法生成代码"


class SymbolSearchService:
    def __init__(self, symbols_index: Dict[str, List[CodeSymbol]]):
        self.symbols_index = symbols_index

    def search_symbol(self, symbol_name: str) -> List[CodeSymbol]:
        return self.symbols_index.get(symbol_name, [])


class DependencyAnalysisService:
    def __init__(self, files: Dict[str, CodeFile]):
        self.files = files

    def get_dependencies(self, file_path: str) -> List[str]:
        if file_path not in self.files:
            return []

        code_file = self.files[file_path]
        dependencies = []

        for imp in code_file.imports:
            dep_file = self._find_import_file(imp)
            if dep_file:
                dependencies.append(dep_file)

        return dependencies

    def _find_import_file(self, import_name: str) -> Optional[str]:
        module_name = import_name.split('.')[0]
        for file_path in self.files:
            basename = os.path.splitext(os.path.basename(file_path))[0]
            if module_name == basename:
                return file_path
            if import_name in file_path or import_name.split('.')[-1] in file_path:
                return file_path
        return None


class CodeAgent:
    """
    代码智能体主类
    整合代码分析、生成、审查、测试等功能
    """

    def __init__(self, project_path: str, llm_client=None):
        self.project_path = project_path
        self.llm_client = llm_client

        self.ast_analyzer = ASTAnalyzer()
        self.code_reviewer = CodeReviewer()
        self.test_generator = TestGenerator(llm_client)
        self.git = GitIntegration(project_path)

        self.project_analyzer = ProjectAnalyzerService(self.ast_analyzer)
        self.code_review_service = CodeReviewService(self.code_reviewer)
        self.test_generation_service = TestGenerationService(self.test_generator)
        self.code_generation_service = CodeGenerationService(llm_client)
        self.symbol_search_service: Optional[SymbolSearchService] = None
        self.dependency_analysis_service: Optional[DependencyAnalysisService] = None

    def analyze_project(self) -> Dict[str, Any]:
        result = self.project_analyzer.analyze_project(self.project_path)

        self.symbol_search_service = SymbolSearchService(
            self.project_analyzer.symbols_index
        )
        self.dependency_analysis_service = DependencyAnalysisService(
            self.project_analyzer.files
        )

        return result

    def review_project(self) -> List[CodeReviewResult]:
        return self.code_review_service.review_project(
            self.project_analyzer.files
        )

    def generate_tests_for_file(self, file_path: str) -> str:
        return self.test_generation_service.generate_tests_for_file(
            file_path,
            self.project_analyzer.files,
            self.project_path
        )

    def generate_code(self, requirement: str, target_file: str = None) -> str:
        context = self._build_generation_context()
        return self.code_generation_service.generate_code(
            requirement,
            context,
            target_file
        )

    def search_symbol(self, symbol_name: str) -> List[CodeSymbol]:
        if self.symbol_search_service is None:
            raise ValueError("请先调用 analyze_project() 方法")
        return self.symbol_search_service.search_symbol(symbol_name)

    def get_dependencies(self, file_path: str) -> List[str]:
        if self.dependency_analysis_service is None:
            raise ValueError("请先调用 analyze_project() 方法")
        return self.dependency_analysis_service.get_dependencies(file_path)

    def _build_generation_context(self) -> str:
        context_parts = []

        context_parts.append("项目结构:")
        for file_path in list(self.project_analyzer.files.keys())[:10]:
            context_parts.append(f"  - {os.path.basename(file_path)}")

        context_parts.append("\n现有符号:")
        for name, symbols in list(self.project_analyzer.symbols_index.items())[:20]:
            if symbols:
                symbol = symbols[0]
                context_parts.append(f"  - {name} ({symbol.symbol_type})")

        return '\n'.join(context_parts)


# ==================== 工具函数 ====================

def analyze_code_project(project_path: str) -> Dict[str, Any]:
    """分析代码项目的便捷函数"""
    agent = CodeAgent(project_path)
    return agent.analyze_project()


def review_code_file(file_path: str) -> CodeReviewResult:
    """审查代码文件的便捷函数"""
    analyzer = ASTAnalyzer()
    reviewer = CodeReviewer()
    
    code_file = analyzer.analyze_file(file_path)
    return reviewer.review_file(code_file)


def generate_tests(file_path: str, output_dir: str = None) -> str:
    """生成测试的便捷函数"""
    analyzer = ASTAnalyzer()
    test_gen = TestGenerator()
    
    code_file = analyzer.analyze_file(file_path)
    test_cases = test_gen.generate_tests(code_file)
    
    # 生成测试文件内容
    test_content = f"\"\"\"\nTests for {os.path.basename(file_path)}\n\"\"\"\n\n"
    test_content += "import pytest\n\n"
    
    for test_case in test_cases:
        test_content += f"\n{test_case.code}\n"
    
    # 保存测试文件
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        test_file = os.path.join(output_dir, f"test_{os.path.basename(file_path)}")
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(test_content)
        print(f"测试文件已生成: {test_file}")
    
    return test_content


if __name__ == "__main__":
    # 测试代码
    print("代码智能体系统测试")
    
    # 测试代码审查
    test_code = '''
def calculate_sum(numbers):
    result = 0
    for i in range(len(numbers)):
        result += numbers[i]
    return result

def greet(name):
    print("Hello, " + name)
    return None
'''
    
    # 创建临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(test_code)
        temp_file = f.name
    
    try:
        result = review_code_file(temp_file)
        print(f"\n文件: {result.file_path}")
        print(f"分数: {result.overall_score}")
        print(f"等级: {result.quality_level.value}")
        print(f"问题数: {len(result.comments)}")
        
        for comment in result.comments:
            print(f"  行{comment.line}: [{comment.severity}] {comment.message}")
    finally:
        os.unlink(temp_file)
