#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全的代码执行模块
替代eval/exec，提供更安全的代码执行环境
"""

import ast
import operator
import math
import re
from typing import Dict, Any, Optional

class SafeMathEvaluator:
    """安全的数学表达式求值器"""
    
    # 支持的操作符
    OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
        ast.Mod: operator.mod,
        ast.FloorDiv: operator.floordiv,
    }
    
    # 支持的函数
    FUNCTIONS = {
        'abs': abs,
        'max': max,
        'min': min,
        'sum': sum,
        'len': len,
        'round': round,
        'pow': pow,
        'sqrt': math.sqrt,
        'sin': math.sin,
        'cos': math.cos,
        'tan': math.tan,
        'log': math.log,
        'log10': math.log10,
        'exp': math.exp,
        'floor': math.floor,
        'ceil': math.ceil,
        'pi': math.pi,
        'e': math.e,
    }
    
    @classmethod
    def evaluate(cls, expression: str) -> Any:
        """安全地求值数学表达式"""
        try:
            # 解析表达式
            tree = ast.parse(expression.strip(), mode='eval')
            return cls._eval_node(tree.body)
        except Exception as e:
            raise ValueError(f"表达式求值错误: {str(e)}")
    
    @classmethod
    def _eval_node(cls, node):
        """递归求值AST节点"""
        if isinstance(node, ast.Num):  # Python 3.7
            return node.n
        elif isinstance(node, ast.Constant):  # Python 3.8+
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError(f"不支持的常量类型: {type(node.value)}")
        
        elif isinstance(node, ast.BinOp):
            left = cls._eval_node(node.left)
            right = cls._eval_node(node.right)
            op_type = type(node.op)
            if op_type in cls.OPERATORS:
                return cls.OPERATORS[op_type](left, right)
            raise ValueError(f"不支持的操作符: {op_type}")
        
        elif isinstance(node, ast.UnaryOp):
            operand = cls._eval_node(node.operand)
            op_type = type(node.op)
            if op_type in cls.OPERATORS:
                return cls.OPERATORS[op_type](operand)
            raise ValueError(f"不支持的一元操作符: {op_type}")
        
        elif isinstance(node, ast.Call):
            # 检查函数名
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
                if func_name not in cls.FUNCTIONS:
                    raise ValueError(f"不支持的函数: {func_name}")
                
                # 求值参数
                args = [cls._eval_node(arg) for arg in node.args]
                return cls.FUNCTIONS[func_name](*args)
            else:
                raise ValueError("不支持的函数调用")
        
        elif isinstance(node, ast.Name):
            if node.id in cls.FUNCTIONS:
                return cls.FUNCTIONS[node.id]
            raise ValueError(f"未定义的变量: {node.id}")
        
        elif isinstance(node, ast.Expression):
            return cls._eval_node(node.body)
        
        else:
            raise ValueError(f"不支持的表达式类型: {type(node)}")

class SafeCodeExecutor:
    """安全的代码执行器"""
    
    # 允许的操作
    ALLOWED_NODES = (
        ast.Expression,
        ast.BinOp,
        ast.UnaryOp,
        ast.Num,
        ast.Constant,
        ast.Call,
        ast.Name,
        ast.Load,
        ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow,
        ast.USub, ast.UAdd, ast.Mod, ast.FloorDiv,
        ast.List, ast.Tuple, ast.Dict, ast.Set,
        ast.Subscript,
        ast.Index,
        ast.Slice,
        ast.Compare,
        ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
        ast.BoolOp,
        ast.And, ast.Or,
        ast.UnaryOp,
        ast.Not,
        ast.IfExp,
        ast.Attribute,
        ast.Str,  # Python 3.7
        ast.JoinedStr,
        ast.FormattedValue,
    )
    
    # 允许的内置函数
    ALLOWED_BUILTINS = {
        'abs': abs,
        'all': all,
        'any': any,
        'bin': bin,
        'bool': bool,
        'chr': chr,
        'dict': dict,
        'divmod': divmod,
        'enumerate': enumerate,
        'filter': filter,
        'float': float,
        'format': format,
        'frozenset': frozenset,
        'hex': hex,
        'int': int,
        'isinstance': isinstance,
        'issubclass': issubclass,
        'iter': iter,
        'len': len,
        'list': list,
        'map': map,
        'max': max,
        'min': min,
        'next': next,
        'oct': oct,
        'ord': ord,
        'pow': pow,
        'range': range,
        'repr': repr,
        'reversed': reversed,
        'round': round,
        'set': set,
        'slice': slice,
        'sorted': sorted,
        'str': str,
        'sum': sum,
        'tuple': tuple,
        'type': type,
        'zip': zip,
    }
    
    # 允许的模块
    ALLOWED_MODULES = {
        'math': math,
        'json': __import__('json'),
        're': __import__('re'),
        'random': __import__('random'),
        'statistics': __import__('statistics'),
        'itertools': __import__('itertools'),
        'functools': __import__('functools'),
        'operator': __import__('operator'),
        'datetime': __import__('datetime'),
        'time': __import__('time'),
        'collections': __import__('collections'),
    }
    
    @classmethod
    def execute(cls, code: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """安全地执行代码"""
        try:
            # 解析代码
            tree = ast.parse(code, mode='exec')
            
            # 验证AST
            cls._validate_ast(tree)
            
            # 准备执行环境
            safe_globals = {
                '__builtins__': cls.ALLOWED_BUILTINS,
            }
            safe_globals.update(cls.ALLOWED_MODULES)
            
            safe_locals = context or {}
            
            # 执行代码
            exec(compile(tree, '<string>', 'exec'), safe_globals, safe_locals)
            
            return {
                'success': True,
                'output': safe_locals.get('output'),
                'result': safe_locals.get('result'),
                'context': {k: v for k, v in safe_locals.items() if not k.startswith('_')}
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @classmethod
    def _validate_ast(cls, node):
        """验证AST节点是否安全"""
        if not isinstance(node, cls.ALLOWED_NODES):
            raise ValueError(f"不安全的代码: {type(node).__name__}")
        
        for child in ast.iter_child_nodes(node):
            cls._validate_ast(child)
    
    @classmethod
    def evaluate_expression(cls, expression: str, context: Optional[Dict] = None) -> Any:
        """安全地求值表达式"""
        try:
            tree = ast.parse(expression, mode='eval')
            cls._validate_ast(tree)
            
            safe_globals = {
                '__builtins__': cls.ALLOWED_BUILTINS,
            }
            safe_globals.update(cls.ALLOWED_MODULES)
            
            return eval(compile(tree, '<string>', 'eval'), safe_globals, context or {})
            
        except Exception as e:
            raise ValueError(f"表达式求值错误: {str(e)}")

# 便捷函数
def safe_eval(expression: str) -> Any:
    """安全的eval替代"""
    return SafeMathEvaluator.evaluate(expression)

def safe_exec(code: str, context: Optional[Dict] = None) -> Dict[str, Any]:
    """安全的exec替代"""
    return SafeCodeExecutor.execute(code, context)

if __name__ == '__main__':
    # 测试数学表达式
    print("测试数学表达式:")
    test_exprs = [
        "1 + 2 * 3",
        "sqrt(16) + pow(2, 3)",
        "sin(pi/2)",
        "(10 + 20) / 5",
    ]
    
    for expr in test_exprs:
        try:
            result = safe_eval(expr)
            print(f"  {expr} = {result}")
        except Exception as e:
            print(f"  {expr} -> 错误: {e}")
    
    # 测试代码执行
    print("\n测试代码执行:")
    test_codes = [
        "result = [x**2 for x in range(5)]",
        "output = sum([1, 2, 3, 4, 5])",
        "import os",  # 应该失败
    ]
    
    for code in test_codes:
        result = safe_exec(code)
        status = "✓" if result['success'] else "✗"
        print(f"  {status} {code[:40]}...")
        if not result['success']:
            print(f"      错误: {result['error']}")
