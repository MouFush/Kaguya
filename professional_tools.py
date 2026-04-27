#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
专业化工具系统 - 深度专业化的工具执行模块
功能: 数学计算、数据分析、代码处理、网络工具等
"""

import json
import re
import math
import statistics
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
import urllib.request
import urllib.parse
from html.parser import HTMLParser


@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    data: Any
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ToolRegistry:
    """工具注册中心"""
    
    def __init__(self):
        self.tools: Dict[str, 'ProfessionalTool'] = {}
        self.categories: Dict[str, List[str]] = {}
    
    def register(self, tool: 'ProfessionalTool'):
        """注册工具"""
        self.tools[tool.id] = tool
        
        # 按分类组织
        category = tool.category
        if category not in self.categories:
            self.categories[category] = []
        self.categories[category].append(tool.id)
    
    def get_tool(self, tool_id: str) -> Optional['ProfessionalTool']:
        """获取工具"""
        return self.tools.get(tool_id)
    
    def get_tools_by_category(self, category: str) -> List['ProfessionalTool']:
        """获取分类下的所有工具"""
        tool_ids = self.categories.get(category, [])
        return [self.tools[tid] for tid in tool_ids if tid in self.tools]
    
    def list_all_tools(self) -> List[Dict]:
        """列出所有工具"""
        return [
            {
                'id': tool.id,
                'name': tool.name,
                'description': tool.description,
                'category': tool.category,
                'icon': tool.icon,
                'parameters': tool.parameters
            }
            for tool in self.tools.values()
        ]


class ProfessionalTool:
    """专业化工具基类"""
    
    def __init__(self, 
                 tool_id: str, 
                 name: str, 
                 description: str,
                 category: str,
                 icon: str = "🔧",
                 parameters: Dict = None):
        self.id = tool_id
        self.name = name
        self.description = description
        self.category = category
        self.icon = icon
        self.parameters = parameters or {}
    
    def execute(self, **kwargs) -> ToolResult:
        """执行工具 - 子类必须实现"""
        raise NotImplementedError
    
    def validate_params(self, params: Dict) -> tuple[bool, Optional[str]]:
        """验证参数"""
        for param_name, param_config in self.parameters.items():
            if param_config.get('required', False) and param_name not in params:
                return False, f"缺少必需参数: {param_name}"
            
            if param_name in params:
                value = params[param_name]
                param_type = param_config.get('type', 'string')
                
                if param_type == 'number' and not isinstance(value, (int, float)):
                    return False, f"参数 {param_name} 必须是数字"
                elif param_type == 'string' and not isinstance(value, str):
                    return False, f"参数 {param_name} 必须是字符串"
                elif param_type == 'boolean' and not isinstance(value, bool):
                    return False, f"参数 {param_name} 必须是布尔值"
        
        return True, None


# ==================== 数学计算工具 ====================

class AdvancedCalculator(ProfessionalTool):
    """高级计算器 - 支持复杂数学运算"""
    
    def __init__(self):
        super().__init__(
            tool_id="advanced_calculator",
            name="高级计算器",
            description="执行复杂数学计算、公式求解、单位转换",
            category="mathematics",
            icon="🔢",
            parameters={
                "expression": {
                    "type": "string",
                    "description": "数学表达式",
                    "required": True
                },
                "precision": {
                    "type": "number",
                    "description": "结果精度（小数位数）",
                    "required": False,
                    "default": 10
                }
            }
        )
        self.safe_dict = {
            'abs': abs, 'round': round, 'max': max, 'min': min,
            'sum': sum, 'pow': pow, 'sqrt': math.sqrt,
            'sin': math.sin, 'cos': math.cos, 'tan': math.tan,
            'asin': math.asin, 'acos': math.acos, 'atan': math.atan,
            'sinh': math.sinh, 'cosh': math.cosh, 'tanh': math.tanh,
            'exp': math.exp, 'log': math.log, 'log10': math.log10,
            'log2': math.log2, 'pi': math.pi, 'e': math.e,
            'floor': math.floor, 'ceil': math.ceil,
            'degrees': math.degrees, 'radians': math.radians,
            'factorial': math.factorial, 'gcd': math.gcd,
            'statistics_mean': statistics.mean,
            'statistics_median': statistics.median,
            'statistics_stdev': statistics.stdev
        }
    
    def execute(self, expression: str, precision: int = 10, **kwargs) -> ToolResult:
        try:
            # 清理表达式
            expression = expression.replace('^', '**')
            expression = expression.replace('×', '*')
            expression = expression.replace('÷', '/')
            
            # 安全求值
            result = eval(expression, {"__builtins__": {}}, self.safe_dict)
            
            # 格式化结果
            if isinstance(result, float):
                result = round(result, precision)
            
            return ToolResult(
                success=True,
                data={
                    'result': result,
                    'expression': expression,
                    'type': type(result).__name__
                },
                metadata={'precision': precision}
            )
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=f"计算错误: {str(e)}"
            )


class StatisticalAnalyzer(ProfessionalTool):
    """统计分析器 - 数据统计分析"""
    
    def __init__(self):
        super().__init__(
            tool_id="statistical_analyzer",
            name="统计分析器",
            description="对数据集进行统计分析，包括均值、中位数、标准差等",
            category="mathematics",
            icon="📊",
            parameters={
                "data": {
                    "type": "string",
                    "description": "数据列表（逗号分隔或JSON数组）",
                    "required": True
                },
                "analysis_type": {
                    "type": "string",
                    "description": "分析类型: basic, full, regression",
                    "required": False,
                    "default": "basic"
                }
            }
        )
    
    def execute(self, data: str, analysis_type: str = "basic", **kwargs) -> ToolResult:
        try:
            # 解析数据
            if data.startswith('[') and data.endswith(']'):
                numbers = json.loads(data)
            else:
                numbers = [float(x.strip()) for x in data.split(',')]
            
            if not numbers:
                return ToolResult(success=False, data=None, error="数据不能为空")
            
            # 基础统计
            result = {
                'count': len(numbers),
                'sum': sum(numbers),
                'mean': statistics.mean(numbers),
                'median': statistics.median(numbers),
                'min': min(numbers),
                'max': max(numbers),
                'range': max(numbers) - min(numbers)
            }
            
            # 完整统计
            if analysis_type in ['full', 'regression']:
                if len(numbers) > 1:
                    result['stdev'] = statistics.stdev(numbers)
                    result['variance'] = statistics.variance(numbers)
                
                # 四分位数
                sorted_nums = sorted(numbers)
                n = len(sorted_nums)
                result['q1'] = sorted_nums[n // 4]
                result['q3'] = sorted_nums[3 * n // 4]
                result['iqr'] = result['q3'] - result['q1']
            
            return ToolResult(
                success=True,
                data=result,
                metadata={'analysis_type': analysis_type, 'data_points': len(numbers)}
            )
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=f"统计分析错误: {str(e)}"
            )


# ==================== 代码处理工具 ====================

class CodeFormatter(ProfessionalTool):
    """代码格式化器"""
    
    def __init__(self):
        super().__init__(
            tool_id="code_formatter",
            name="代码格式化器",
            description="格式化多种编程语言代码",
            category="code",
            icon="📝",
            parameters={
                "code": {
                    "type": "string",
                    "description": "源代码",
                    "required": True
                },
                "language": {
                    "type": "string",
                    "description": "编程语言: python, javascript, json, sql",
                    "required": True
                }
            }
        )
    
    def execute(self, code: str, language: str, **kwargs) -> ToolResult:
        try:
            formatted_code = code
            
            if language == 'json':
                # JSON格式化
                parsed = json.loads(code)
                formatted_code = json.dumps(parsed, indent=2, ensure_ascii=False)
            
            elif language == 'python':
                # Python基础格式化
                lines = code.split('\n')
                formatted_lines = []
                indent_level = 0
                
                for line in lines:
                    stripped = line.strip()
                    
                    # 减少缩进
                    if stripped.startswith(('}', ']', 'elif', 'else:', 'except', 'finally:')):
                        indent_level = max(0, indent_level - 1)
                    
                    # 添加格式化行
                    if stripped:
                        formatted_lines.append('    ' * indent_level + stripped)
                    else:
                        formatted_lines.append('')
                    
                    # 增加缩进
                    if stripped.endswith((':', '{', '[')) or stripped.startswith(('def ', 'class ', 'if ', 'for ', 'while ')):
                        indent_level += 1
                
                formatted_code = '\n'.join(formatted_lines)
            
            elif language == 'sql':
                # SQL格式化
                keywords = ['SELECT', 'FROM', 'WHERE', 'JOIN', 'LEFT', 'RIGHT', 'INNER', 
                           'OUTER', 'GROUP BY', 'ORDER BY', 'HAVING', 'LIMIT', 'INSERT', 
                           'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP']
                
                formatted_code = code
                for keyword in keywords:
                    formatted_code = re.sub(
                        rf'\b{keyword}\b', 
                        f'\n{keyword}', 
                        formatted_code, 
                        flags=re.IGNORECASE
                    )
            
            return ToolResult(
                success=True,
                data={
                    'formatted_code': formatted_code,
                    'language': language,
                    'original_length': len(code),
                    'formatted_length': len(formatted_code)
                }
            )
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=f"格式化错误: {str(e)}"
            )


class CodeAnalyzer(ProfessionalTool):
    """代码分析器"""
    
    def __init__(self):
        super().__init__(
            tool_id="code_analyzer",
            name="代码分析器",
            description="分析代码质量、复杂度、潜在问题",
            category="code",
            icon="🔍",
            parameters={
                "code": {
                    "type": "string",
                    "description": "源代码",
                    "required": True
                },
                "language": {
                    "type": "string",
                    "description": "编程语言",
                    "required": True
                }
            }
        )
    
    def execute(self, code: str, language: str, **kwargs) -> ToolResult:
        try:
            analysis = {
                'lines': len(code.split('\n')),
                'characters': len(code),
                'functions': 0,
                'classes': 0,
                'comments': 0,
                'issues': []
            }
            
            if language == 'python':
                # 统计函数和类
                analysis['functions'] = len(re.findall(r'\bdef\s+\w+', code))
                analysis['classes'] = len(re.findall(r'\bclass\s+\w+', code))
                analysis['comments'] = len(re.findall(r'#.*', code))
                
                # 检查潜在问题
                if 'print(' in code and 'import logging' not in code:
                    analysis['issues'].append({
                        'type': 'warning',
                        'message': '建议使用logging替代print',
                        'line': None
                    })
                
                if 'except:' in code:
                    analysis['issues'].append({
                        'type': 'warning',
                        'message': '建议捕获具体异常类型，避免裸except',
                        'line': None
                    })
            
            # 计算复杂度（简化版）
            analysis['complexity_score'] = min(100, analysis['lines'] // 10 + analysis['functions'] * 2)
            
            return ToolResult(
                success=True,
                data=analysis,
                metadata={'language': language}
            )
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=f"分析错误: {str(e)}"
            )


# ==================== 网络工具 ====================

class URLAnalyzer(ProfessionalTool):
    """URL分析器"""
    
    def __init__(self):
        super().__init__(
            tool_id="url_analyzer",
            name="URL分析器",
            description="解析和分析URL结构",
            category="network",
            icon="🔗",
            parameters={
                "url": {
                    "type": "string",
                    "description": "URL地址",
                    "required": True
                }
            }
        )
    
    def execute(self, url: str, **kwargs) -> ToolResult:
        try:
            parsed = urllib.parse.urlparse(url)
            
            result = {
                'scheme': parsed.scheme,
                'netloc': parsed.netloc,
                'path': parsed.path,
                'params': parsed.params,
                'query': parsed.query,
                'fragment': parsed.fragment,
                'hostname': parsed.hostname,
                'port': parsed.port,
                'query_params': urllib.parse.parse_qs(parsed.query)
            }
            
            # 安全检查
            result['is_https'] = parsed.scheme == 'https'
            result['has_query'] = bool(parsed.query)
            result['has_fragment'] = bool(parsed.fragment)
            
            return ToolResult(
                success=True,
                data=result
            )
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=f"URL解析错误: {str(e)}"
            )


class HTMLEntityDecoder(ProfessionalTool):
    """HTML实体解码器"""
    
    def __init__(self):
        super().__init__(
            tool_id="html_decoder",
            name="HTML解码器",
            description="解码HTML实体和转义字符",
            category="network",
            icon="🌐",
            parameters={
                "html": {
                    "type": "string",
                    "description": "HTML文本",
                    "required": True
                },
                "remove_tags": {
                    "type": "boolean",
                    "description": "是否移除HTML标签",
                    "required": False,
                    "default": False
                }
            }
        )
        
        self.html_entities = {
            '&amp;': '&', '&lt;': '<', '&gt;': '>', '&quot;': '"',
            '&#39;': "'", '&nbsp;': ' ', '&copy;': '©', '&reg;': '®',
            '&trade;': '™', '&euro;': '€', '&pound;': '£', '&yen;': '¥',
            '&mdash;': '—', '&ndash;': '–', '&hellip;': '…'
        }
    
    def execute(self, html: str, remove_tags: bool = False, **kwargs) -> ToolResult:
        try:
            result = html
            
            # 解码HTML实体
            for entity, char in self.html_entities.items():
                result = result.replace(entity, char)
            
            # 解码数字实体
            result = re.sub(r'&#(\d+);', lambda m: chr(int(m.group(1))), result)
            result = re.sub(r'&#x([0-9a-fA-F]+);', lambda m: chr(int(m.group(1), 16)), result)
            
            # 移除标签
            if remove_tags:
                result = re.sub(r'<[^>]+>', '', result)
            
            return ToolResult(
                success=True,
                data={
                    'decoded': result,
                    'original_length': len(html),
                    'decoded_length': len(result),
                    'tags_removed': remove_tags
                }
            )
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=f"解码错误: {str(e)}"
            )


# ==================== 文本处理工具 ====================

class TextDiffTool(ProfessionalTool):
    """文本差异对比工具"""
    
    def __init__(self):
        super().__init__(
            tool_id="text_diff",
            name="文本对比器",
            description="对比两段文本的差异",
            category="text",
            icon="📋",
            parameters={
                "text1": {
                    "type": "string",
                    "description": "原始文本",
                    "required": True
                },
                "text2": {
                    "type": "string",
                    "description": "对比文本",
                    "required": True
                }
            }
        )
    
    def execute(self, text1: str, text2: str, **kwargs) -> ToolResult:
        try:
            lines1 = text1.split('\n')
            lines2 = text2.split('\n')
            
            # 简化版差异检测
            diff = []
            max_lines = max(len(lines1), len(lines2))
            
            for i in range(max_lines):
                line1 = lines1[i] if i < len(lines1) else None
                line2 = lines2[i] if i < len(lines2) else None
                
                if line1 != line2:
                    diff.append({
                        'line': i + 1,
                        'type': 'modified' if line1 and line2 else ('removed' if line1 else 'added'),
                        'original': line1,
                        'modified': line2
                    })
            
            # 计算相似度
            if text1 == text2:
                similarity = 100.0
            else:
                common = sum(1 for a, b in zip(text1, text2) if a == b)
                similarity = (common / max(len(text1), len(text2))) * 100
            
            return ToolResult(
                success=True,
                data={
                    'diff': diff,
                    'similarity': round(similarity, 2),
                    'total_lines': max_lines,
                    'changed_lines': len(diff)
                }
            )
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=f"对比错误: {str(e)}"
            )


class RegexTester(ProfessionalTool):
    """正则表达式测试器"""
    
    def __init__(self):
        super().__init__(
            tool_id="regex_tester",
            name="正则测试器",
            description="测试和验证正则表达式",
            category="text",
            icon="🔤",
            parameters={
                "pattern": {
                    "type": "string",
                    "description": "正则表达式",
                    "required": True
                },
                "text": {
                    "type": "string",
                    "description": "测试文本",
                    "required": True
                },
                "flags": {
                    "type": "string",
                    "description": "标志: i(忽略大小写), m(多行), s(点匹配换行)",
                    "required": False,
                    "default": ""
                }
            }
        )
    
    def execute(self, pattern: str, text: str, flags: str = "", **kwargs) -> ToolResult:
        try:
            # 解析标志
            re_flags = 0
            if 'i' in flags:
                re_flags |= re.IGNORECASE
            if 'm' in flags:
                re_flags |= re.MULTILINE
            if 's' in flags:
                re_flags |= re.DOTALL
            
            # 编译正则
            compiled = re.compile(pattern, re_flags)
            
            # 查找所有匹配
            matches = []
            for match in compiled.finditer(text):
                matches.append({
                    'match': match.group(),
                    'start': match.start(),
                    'end': match.end(),
                    'groups': match.groups()
                })
            
            # 替换测试
            replacement = compiled.sub('【匹配内容】', text)
            
            return ToolResult(
                success=True,
                data={
                    'pattern': pattern,
                    'flags': flags,
                    'matches': matches,
                    'match_count': len(matches),
                    'replacement_preview': replacement[:500],
                    'is_valid': True
                }
            )
        except re.error as e:
            return ToolResult(
                success=False,
                data={'is_valid': False, 'error_position': e.pos},
                error=f"正则表达式错误: {e.msg}"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=f"测试错误: {str(e)}"
            )


# ==================== 初始化工具注册表 ====================

def create_professional_toolkit() -> ToolRegistry:
    """创建专业化工具包"""
    registry = ToolRegistry()
    
    # 数学工具
    registry.register(AdvancedCalculator())
    registry.register(StatisticalAnalyzer())
    
    # 代码工具
    registry.register(CodeFormatter())
    registry.register(CodeAnalyzer())
    
    # 网络工具
    registry.register(URLAnalyzer())
    registry.register(HTMLEntityDecoder())
    
    # 文本工具
    registry.register(TextDiffTool())
    registry.register(RegexTester())
    
    return registry


# 全局工具注册表实例
professional_toolkit = create_professional_toolkit()


# 便捷函数
def execute_professional_tool(tool_id: str, **params) -> ToolResult:
    """执行专业工具"""
    tool = professional_toolkit.get_tool(tool_id)
    if not tool:
        return ToolResult(
            success=False,
            data=None,
            error=f"工具不存在: {tool_id}"
        )
    
    # 验证参数
    is_valid, error_msg = tool.validate_params(params)
    if not is_valid:
        return ToolResult(
            success=False,
            data=None,
            error=error_msg
        )
    
    # 执行工具
    return tool.execute(**params)


def list_professional_tools() -> List[Dict]:
    """列出所有专业工具"""
    return professional_toolkit.list_all_tools()


# 测试代码
if __name__ == '__main__':
    print("=" * 60)
    print("专业化工具系统测试")
    print("=" * 60)
    
    # 测试高级计算器
    print("\n1. 高级计算器测试")
    result = execute_professional_tool(
        "advanced_calculator",
        expression="sqrt(16) + sin(pi/2) + 2**10",
        precision=5
    )
    print(f"结果: {result.data if result.success else result.error}")
    
    # 测试统计分析器
    print("\n2. 统计分析器测试")
    result = execute_professional_tool(
        "statistical_analyzer",
        data="1, 2, 3, 4, 5, 6, 7, 8, 9, 10",
        analysis_type="full"
    )
    print(f"结果: {result.data if result.success else result.error}")
    
    # 测试代码格式化
    print("\n3. 代码格式化器测试")
    result = execute_professional_tool(
        "code_formatter",
        code='{"name": "test", "value": 123}',
        language="json"
    )
    print(f"结果:\n{result.data['formatted_code'] if result.success else result.error}")
    
    # 测试正则测试器
    print("\n4. 正则测试器测试")
    result = execute_professional_tool(
        "regex_tester",
        pattern=r"\b\w+@\w+\.\w+",
        text="联系邮箱: user@example.com 或 admin@test.org",
        flags=""
    )
    print(f"找到 {result.data['match_count']} 个匹配" if result.success else result.error)
    
    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)
