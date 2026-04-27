#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI代码生成器 - 智能代码生成与优化
功能: 自然语言转代码、代码补全、代码重构、代码解释
"""

import re
import json
import ast
import inspect
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import textwrap


class CodeLanguage(Enum):
    """支持的编程语言"""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    CPP = "cpp"
    GO = "go"
    RUST = "rust"
    SQL = "sql"
    HTML = "html"
    CSS = "css"


class CodeTask(Enum):
    """代码任务类型"""
    GENERATE = "generate"           # 生成代码
    COMPLETE = "complete"           # 补全代码
    REFACTOR = "refactor"           # 重构代码
    EXPLAIN = "explain"             # 解释代码
    OPTIMIZE = "optimize"           # 优化代码
    DEBUG = "debug"                 # 调试代码
    DOCUMENT = "document"           # 生成文档
    TEST = "test"                   # 生成测试


@dataclass
class CodeSnippet:
    """代码片段"""
    code: str
    language: CodeLanguage
    description: str = ""
    tags: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    complexity_score: float = 0.0
    line_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class CodeGenerationResult:
    """代码生成结果"""
    success: bool
    code: str = ""
    language: CodeLanguage = CodeLanguage.PYTHON
    explanation: str = ""
    suggestions: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    alternatives: List[str] = field(default_factory=list)
    error_message: str = ""


class CodePatternLibrary:
    """代码模式库"""
    
    PATTERNS = {
        CodeLanguage.PYTHON: {
            'singleton': '''
class {class_name}:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
''',
            'factory': '''
class {factory_name}:
    @staticmethod
    def create_{product_type}(type_name: str):
        if type_name == "{type_a}":
            return {class_a}()
        elif type_name == "{type_b}":
            return {class_b}()
        raise ValueError(f"Unknown type: {type_name}")
''',
            'decorator': '''
def {decorator_name}(func):
    def wrapper(*args, **kwargs):
        # Before execution
        result = func(*args, **kwargs)
        # After execution
        return result
    return wrapper
''',
            'context_manager': '''
class {manager_name}:
    def __enter__(self):
        # Setup code
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Cleanup code
        pass
''',
            'dataclass': '''
from dataclasses import dataclass

@dataclass
class {class_name}:
    {field_name}: {field_type}
    
    def __post_init__(self):
        pass
''',
            'fastapi_endpoint': '''
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class {request_model}(BaseModel):
    {field_name}: {field_type}

@app.{method}("/{endpoint}")
async def {function_name}(request: {request_model}):
    # Implementation
    return {{"result": "success"}}
''',
            'flask_route': '''
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/{endpoint}', methods=['{method}'])
def {function_name}():
    data = request.get_json()
    # Implementation
    return jsonify({{"result": "success"}})
''',
            'sqlalchemy_model': '''
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class {model_name}(Base):
    __tablename__ = '{table_name}'
    
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.now)
''',
            'pydantic_model': '''
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class {model_name}(BaseModel):
    id: int = Field(..., description="Unique identifier")
    name: str = Field(..., min_length=1, max_length=100)
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "example"
            }
        }
''',
            'async_function': '''
import asyncio

async def {function_name}({params}):
    # Async implementation
    await asyncio.sleep(1)
    return result
''',
            'thread_pool': '''
from concurrent.futures import ThreadPoolExecutor
import threading

class {class_name}:
    def __init__(self, max_workers=4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.lock = threading.Lock()
    
    def submit_task(self, func, *args, **kwargs):
        return self.executor.submit(func, *args, **kwargs)
''',
            'cache_decorator': '''
import functools
from typing import Callable

def cache_result(ttl_seconds: int = 300):
    def decorator(func: Callable):
        cache = {{}}
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key = str(args) + str(kwargs)
            if key in cache:
                return cache[key]
            result = func(*args, **kwargs)
            cache[key] = result
            return result
        
        return wrapper
    return decorator
''',
            'retry_decorator': '''
import functools
import time
from typing import Callable

def retry_on_error(max_retries: int = 3, delay: float = 1.0):
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(delay)
            return None
        return wrapper
    return decorator
''',
            'logger_setup': '''
import logging
from logging.handlers import RotatingFileHandler

def setup_logger(name: str, log_file: str = None):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        file_handler = RotatingFileHandler(
            log_file, maxBytes=10*1024*1024, backupCount=5
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger
''',
            'config_manager': '''
import json
import os
from typing import Any, Dict

class ConfigManager:
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config: Dict[str, Any] = {{}}
        self.load()
    
    def load(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
    
    def save(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def get(self, key: str, default=None):
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        self.config[key] = value
        self.save()
''',
            'api_client': '''
import requests
from typing import Dict, Any, Optional

class APIClient:
    def __init__(self, base_url: str, api_key: str = None):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        if api_key:
            self.session.headers['Authorization'] = f'Bearer {{api_key}}'
    
    def get(self, endpoint: str, params: Dict = None) -> Dict:
        response = self.session.get(
            f"{{self.base_url}}{{endpoint}}",
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    def post(self, endpoint: str, data: Dict = None) -> Dict:
        response = self.session.post(
            f"{{self.base_url}}{{endpoint}}",
            json=data
        )
        response.raise_for_status()
        return response.json()
''',
            'websocket_handler': '''
import asyncio
import websockets
import json
from typing import Callable

class WebSocketServer:
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.clients = set()
        self.message_handlers: Dict[str, Callable] = {{}}
    
    async def register(self, websocket):
        self.clients.add(websocket)
    
    async def unregister(self, websocket):
        self.clients.discard(websocket)
    
    async def broadcast(self, message: dict):
        if self.clients:
            await asyncio.gather(
                *[client.send(json.dumps(message)) for client in self.clients]
            )
    
    async def handler(self, websocket, path):
        await self.register(websocket)
        try:
            async for message in websocket:
                data = json.loads(message)
                await self.handle_message(websocket, data)
        finally:
            await self.unregister(websocket)
    
    async def handle_message(self, websocket, data: dict):
        msg_type = data.get('type')
        if msg_type in self.message_handlers:
            await self.message_handlers[msg_type](websocket, data)
    
    def start(self):
        start_server = websockets.serve(self.handler, self.host, self.port)
        asyncio.get_event_loop().run_until_complete(start_server)
        asyncio.get_event_loop().run_forever()
'''
        }
    }
    
    @classmethod
    def get_pattern(cls, language: CodeLanguage, pattern_name: str) -> Optional[str]:
        """获取代码模式"""
        patterns = cls.PATTERNS.get(language, {})
        return patterns.get(pattern_name)
    
    @classmethod
    def list_patterns(cls, language: CodeLanguage) -> List[str]:
        """列出所有模式"""
        return list(cls.PATTERNS.get(language, {}).keys())


class AICodeGenerator:
    """AI代码生成器"""
    
    def __init__(self):
        self.pattern_library = CodePatternLibrary()
        self.generation_history: List[Dict] = []
    
    def generate_from_description(self, description: str, language: CodeLanguage = CodeLanguage.PYTHON,
                                 context: Dict = None) -> CodeGenerationResult:
        """
        根据自然语言描述生成代码
        
        Args:
            description: 自然语言描述
            language: 目标编程语言
            context: 上下文信息
        
        Returns:
            代码生成结果
        """
        context = context or {}
        
        # 解析描述，提取关键信息
        parsed = self._parse_description(description)
        
        # 根据任务类型选择生成策略
        if parsed['task_type'] == 'class':
            return self._generate_class(parsed, language, context)
        elif parsed['task_type'] == 'function':
            return self._generate_function(parsed, language, context)
        elif parsed['task_type'] == 'api':
            return self._generate_api(parsed, language, context)
        elif parsed['task_type'] == 'pattern':
            return self._generate_from_pattern(parsed, language, context)
        else:
            return self._generate_generic(parsed, language, context)
    
    def _parse_description(self, description: str) -> Dict:
        """解析自然语言描述"""
        description_lower = description.lower()
        
        result = {
            'original': description,
            'task_type': 'generic',
            'class_name': None,
            'function_name': None,
            'parameters': [],
            'features': [],
            'pattern': None
        }
        
        # 检测任务类型
        if any(word in description_lower for word in ['类', 'class', '对象', 'object']):
            result['task_type'] = 'class'
        elif any(word in description_lower for word in ['函数', 'function', '方法', 'method']):
            result['task_type'] = 'function'
        elif any(word in description_lower for word in ['api', '接口', 'endpoint', '路由']):
            result['task_type'] = 'api'
        elif any(word in description_lower for word in ['单例', 'singleton', '工厂', 'factory', '装饰器', 'decorator']):
            result['task_type'] = 'pattern'
        
        # 提取类名
        class_match = re.search(r'(?:类|class)\s+(\w+)', description, re.IGNORECASE)
        if class_match:
            result['class_name'] = class_match.group(1)
        
        # 提取函数名
        func_match = re.search(r'(?:函数|function|方法|method)\s+(\w+)', description, re.IGNORECASE)
        if func_match:
            result['function_name'] = func_match.group(1)
        
        # 检测设计模式
        patterns = {
            'singleton': ['单例', 'singleton'],
            'factory': ['工厂', 'factory'],
            'decorator': ['装饰器', 'decorator'],
            'context_manager': ['上下文管理器', 'context manager'],
            'dataclass': ['数据类', 'dataclass'],
            'fastapi_endpoint': ['fastapi', 'fastapi接口'],
            'flask_route': ['flask', 'flask路由'],
            'sqlalchemy_model': ['sqlalchemy', '数据库模型'],
            'pydantic_model': ['pydantic', '数据模型']
        }
        
        for pattern_name, keywords in patterns.items():
            if any(kw in description_lower for kw in keywords):
                result['pattern'] = pattern_name
                break
        
        return result
    
    def _generate_class(self, parsed: Dict, language: CodeLanguage, 
                       context: Dict) -> CodeGenerationResult:
        """生成类代码"""
        class_name = parsed.get('class_name') or context.get('class_name', 'MyClass')
        
        code = f'''class {class_name}:
    """
    {parsed['original']}
    """
    
    def __init__(self):
        """初始化"""
        pass
    
    def process(self):
        """处理方法"""
        pass
'''
        
        return CodeGenerationResult(
            success=True,
            code=code.strip(),
            language=language,
            explanation=f"生成了{class_name}类，包含初始化和处理方法"
        )
    
    def _generate_function(self, parsed: Dict, language: CodeLanguage,
                          context: Dict) -> CodeGenerationResult:
        """生成函数代码"""
        func_name = parsed.get('function_name') or context.get('function_name', 'my_function')
        
        code = f'''def {func_name}():
    """
    {parsed['original']}
    
    Returns:
        处理结果
    """
    # TODO: 实现功能
    pass
'''
        
        return CodeGenerationResult(
            success=True,
            code=code.strip(),
            language=language,
            explanation=f"生成了{func_name}函数框架"
        )
    
    def _generate_api(self, parsed: Dict, language: CodeLanguage,
                     context: Dict) -> CodeGenerationResult:
        """生成API代码"""
        # 默认使用FastAPI模式
        pattern_code = self.pattern_library.get_pattern(language, 'fastapi_endpoint')
        
        if pattern_code:
            code = pattern_code.format(
                request_model='RequestModel',
                field_name='data',
                field_type='str',
                method='post',
                endpoint='api/endpoint',
                function_name='handle_request'
            )
            
            return CodeGenerationResult(
                success=True,
                code=code.strip(),
                language=language,
                explanation="生成了FastAPI端点代码，包含请求模型和路由处理"
            )
        
        return CodeGenerationResult(
            success=False,
            error_message=f"不支持的语言: {language.value}"
        )
    
    def _generate_from_pattern(self, parsed: Dict, language: CodeLanguage,
                              context: Dict) -> CodeGenerationResult:
        """基于模式生成代码"""
        pattern_name = parsed.get('pattern')
        
        if not pattern_name:
            return self._generate_generic(parsed, language, context)
        
        pattern_code = self.pattern_library.get_pattern(language, pattern_name)
        
        if pattern_code:
            # 填充模板变量
            code = pattern_code.format(
                class_name=context.get('class_name', 'MyClass'),
                function_name=context.get('function_name', 'my_function'),
                factory_name=context.get('factory_name', 'MyFactory'),
                product_type=context.get('product_type', 'product'),
                type_a=context.get('type_a', 'TypeA'),
                type_b=context.get('type_b', 'TypeB'),
                class_a=context.get('class_a', 'ClassA'),
                class_b=context.get('class_b', 'ClassB'),
                decorator_name=context.get('decorator_name', 'my_decorator'),
                manager_name=context.get('manager_name', 'MyManager'),
                field_name=context.get('field_name', 'name'),
                field_type=context.get('field_type', 'str'),
                request_model=context.get('request_model', 'RequestModel'),
                method=context.get('method', 'post'),
                endpoint=context.get('endpoint', 'api/endpoint'),
                model_name=context.get('model_name', 'MyModel'),
                table_name=context.get('table_name', 'my_table'),
                params=context.get('params', ''),
                max_workers=context.get('max_workers', '4'),
                log_file=context.get('log_file', 'app.log'),
                config_file=context.get('config_file', 'config.json'),
                base_url=context.get('base_url', 'https://api.example.com'),
                api_key=context.get('api_key', ''),
                host=context.get('host', 'localhost'),
                port=context.get('port', '8765')
            )
            
            return CodeGenerationResult(
                success=True,
                code=code.strip(),
                language=language,
                explanation=f"基于{pattern_name}模式生成了代码"
            )
        
        return CodeGenerationResult(
            success=False,
            error_message=f"未找到模式: {pattern_name}"
        )
    
    def _generate_generic(self, parsed: Dict, language: CodeLanguage,
                         context: Dict) -> CodeGenerationResult:
        """通用代码生成"""
        code = f'''# {parsed['original']}
# TODO: 实现功能

def main():
    pass

if __name__ == "__main__":
    main()
'''
        
        return CodeGenerationResult(
            success=True,
            code=code.strip(),
            language=language,
            explanation="生成了通用代码框架，请根据需求完善实现"
        )
    
    def complete_code(self, partial_code: str, language: CodeLanguage = CodeLanguage.PYTHON) -> CodeGenerationResult:
        """补全代码"""
        # 分析部分代码
        lines = partial_code.strip().split('\n')
        
        # 简单的补全逻辑
        completions = []
        
        # 检查是否需要补全函数体
        if lines and lines[-1].strip().endswith(':'):
            completions.append('    pass')
        
        # 检查是否需要导入语句
        if 'class ' in partial_code and 'dataclass' not in partial_code:
            if 'import' not in partial_code:
                completions.insert(0, '# 建议添加必要的导入语句')
        
        completed_code = partial_code + '\n' + '\n'.join(completions) if completions else partial_code
        
        return CodeGenerationResult(
            success=True,
            code=completed_code,
            language=language,
            explanation="基于代码上下文进行了智能补全"
        )
    
    def explain_code(self, code: str, language: CodeLanguage = CodeLanguage.PYTHON) -> str:
        """解释代码"""
        lines = code.strip().split('\n')
        explanations = []
        
        for i, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            if line_stripped.startswith('def '):
                func_name = line_stripped[4:].split('(')[0]
                explanations.append(f"第{i}行: 定义函数 '{func_name}'")
            elif line_stripped.startswith('class '):
                class_name = line_stripped[6:].split('(')[0].split(':')[0]
                explanations.append(f"第{i}行: 定义类 '{class_name}'")
            elif line_stripped.startswith('import '):
                explanations.append(f"第{i}行: 导入模块")
            elif line_stripped.startswith('return '):
                explanations.append(f"第{i}行: 返回结果")
            elif line_stripped.startswith('#'):
                explanations.append(f"第{i}行: 注释 - {line_stripped[1:].strip()}")
        
        return '\n'.join(explanations) if explanations else "代码解释暂不可用"
    
    def optimize_code(self, code: str, language: CodeLanguage = CodeLanguage.PYTHON) -> CodeGenerationResult:
        """优化代码"""
        suggestions = []
        optimized_code = code
        
        # 简单的优化建议
        if 'for ' in code and 'range(' in code:
            suggestions.append("考虑使用列表推导式简化循环")
        
        if 'open(' in code and 'close()' not in code:
            suggestions.append("建议使用 'with' 语句确保文件正确关闭")
        
        if 'except:' in code:
            suggestions.append("建议捕获具体的异常类型，而不是使用裸except")
        
        if len(code.split('\n')) > 50:
            suggestions.append("函数较长，建议拆分为多个小函数")
        
        return CodeGenerationResult(
            success=True,
            code=optimized_code,
            language=language,
            explanation="代码分析完成",
            suggestions=suggestions
        )
    
    def generate_tests(self, code: str, language: CodeLanguage = CodeLanguage.PYTHON) -> CodeGenerationResult:
        """生成测试代码"""
        # 提取函数名和类名
        func_names = re.findall(r'def\s+(\w+)\s*\(', code)
        class_names = re.findall(r'class\s+(\w+)\s*[\(:]', code)
        
        test_code = f'''import unittest
{''.join(f"\nfrom your_module import {name}" for name in class_names + func_names if name not in ['__init__'])}

'''
        
        # 为每个类生成测试类
        for class_name in class_names:
            test_code += f'''
class Test{class_name}(unittest.TestCase):
    def setUp(self):
        """测试前准备"""
        self.instance = {class_name}()
    
    def test_initialization(self):
        """测试初始化"""
        self.assertIsNotNone(self.instance)
    
    # TODO: 添加更多测试用例
'''
        
        # 为每个函数生成测试
        for func_name in func_names:
            if func_name != '__init__':
                test_code += f'''
class Test{func_name.title()}(unittest.TestCase):
    def test_{func_name}(self):
        """测试{func_name}函数"""
        # TODO: 准备测试数据
        result = {func_name}()
        # TODO: 验证结果
        self.assertIsNotNone(result)
'''
        
        test_code += '''
if __name__ == '__main__':
    unittest.main()
'''
        
        return CodeGenerationResult(
            success=True,
            code=test_code,
            language=language,
            explanation=f"为{len(class_names)}个类和{len(func_names)}个函数生成了测试框架"
        )
    
    def get_available_patterns(self, language: CodeLanguage = CodeLanguage.PYTHON) -> List[str]:
        """获取可用的代码模式"""
        return self.pattern_library.list_patterns(language)


# 全局代码生成器
ai_code_generator = AICodeGenerator()


# 便捷函数
def generate_code(description: str, language: str = "python", context: Dict = None) -> CodeGenerationResult:
    """生成代码"""
    lang = CodeLanguage(language.lower())
    return ai_code_generator.generate_from_description(description, lang, context)


def complete_code(partial_code: str, language: str = "python") -> CodeGenerationResult:
    """补全代码"""
    lang = CodeLanguage(language.lower())
    return ai_code_generator.complete_code(partial_code, lang)


def explain_code(code: str, language: str = "python") -> str:
    """解释代码"""
    lang = CodeLanguage(language.lower())
    return ai_code_generator.explain_code(code, lang)


def optimize_code(code: str, language: str = "python") -> CodeGenerationResult:
    """优化代码"""
    lang = CodeLanguage(language.lower())
    return ai_code_generator.optimize_code(code, lang)


def generate_tests(code: str, language: str = "python") -> CodeGenerationResult:
    """生成测试"""
    lang = CodeLanguage(language.lower())
    return ai_code_generator.generate_tests(code, lang)


# 测试代码
if __name__ == '__main__':
    print("=" * 60)
    print("AI代码生成器测试")
    print("=" * 60)
    
    generator = AICodeGenerator()
    
    # 测试1: 生成单例类
    print("\n1. 生成单例模式")
    result1 = generator.generate_from_description(
        "创建一个单例类 DatabaseConnection",
        CodeLanguage.PYTHON,
        {'class_name': 'DatabaseConnection'}
    )
    print(f"成功: {result1.success}")
    print(f"代码:\n{result1.code[:200]}...")
    
    # 测试2: 生成FastAPI端点
    print("\n2. 生成FastAPI端点")
    result2 = generator.generate_from_description(
        "创建一个FastAPI POST接口用于用户注册",
        CodeLanguage.PYTHON
    )
    print(f"成功: {result2.success}")
    print(f"代码:\n{result2.code[:200]}...")
    
    # 测试3: 代码补全
    print("\n3. 代码补全")
    partial = "def calculate_sum(a, b):"
    result3 = generator.complete_code(partial, CodeLanguage.PYTHON)
    print(f"补全结果:\n{result3.code}")
    
    # 测试4: 代码解释
    print("\n4. 代码解释")
    code = '''
def greet(name):
    """问候函数"""
    return f"Hello, {name}!"
'''
    explanation = generator.explain_code(code, CodeLanguage.PYTHON)
    print(f"解释:\n{explanation}")
    
    # 测试5: 生成测试
    print("\n5. 生成测试")
    test_code = '''
class Calculator:
    def add(self, a, b):
        return a + b
    
    def subtract(self, a, b):
        return a - b
'''
    result5 = generator.generate_tests(test_code, CodeLanguage.PYTHON)
    print(f"测试代码:\n{result5.code[:300]}...")
    
    # 测试6: 列出可用模式
    print("\n6. 可用代码模式")
    patterns = generator.get_available_patterns(CodeLanguage.PYTHON)
    print(f"Python模式: {', '.join(patterns)}")
    
    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)
