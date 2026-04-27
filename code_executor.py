"""
MiniMind 增强版代码执行引擎
===========================

支持：
1. 实时代码执行
2. 输入输出捕获
3. 错误追踪
4. 超时控制
5. 沙箱安全

使用方法：
    from code_executor import CodeExecutor
    
    executor = CodeExecutor()
    result = executor.run("print('Hello World')")
    print(result)
"""

import os
import sys
import io
import re
import ast
import time
import signal
import threading
import traceback
from contextlib import redirect_stdout, redirect_stderr
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import subprocess
import tempfile
import json


class ExecutionStatus(Enum):
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    INTERRUPTED = "interrupted"


@dataclass
class ExecutionResult:
    """执行结果"""
    status: ExecutionStatus
    output: str
    error: str
    return_value: Any = None
    execution_time: float = 0.0
    memory_used: int = 0
    
    def to_dict(self) -> Dict:
        return {
            'status': self.status.value,
            'output': self.output,
            'error': self.error,
            'return_value': str(self.return_value) if self.return_value is not None else None,
            'execution_time': self.execution_time,
            'memory_used': self.memory_used
        }
    
    def __str__(self) -> str:
        if self.status == ExecutionStatus.SUCCESS:
            return self.output
        else:
            return f"[{self.status.value}] {self.error}\n{self.output}"


class InputSimulator:
    """输入模拟器"""
    
    def __init__(self, inputs: List[str] = None):
        self.inputs = inputs or []
        self.index = 0
    
    def add_input(self, value: str):
        self.inputs.append(value)
    
    def get_input(self) -> str:
        if self.index < len(self.inputs):
            value = self.inputs[self.index]
            self.index += 1
            return value
        return ""
    
    def reset(self):
        self.index = 0


class OutputCapture:
    """输出捕获器"""
    
    def __init__(self):
        self.stdout_buffer = io.StringIO()
        self.stderr_buffer = io.StringIO()
        self.outputs: List[str] = []
    
    def write(self, text: str):
        self.stdout_buffer.write(text)
        self.outputs.append(text)
    
    def get_output(self) -> str:
        return self.stdout_buffer.getvalue()
    
    def get_error(self) -> str:
        return self.stderr_buffer.getvalue()
    
    def clear(self):
        self.stdout_buffer = io.StringIO()
        self.stderr_buffer = io.StringIO()
        self.outputs = []


class CodeExecutor:
    """增强版代码执行器"""
    
    def __init__(
        self,
        timeout: int = 30,
        max_output_size: int = 100000,
        allowed_modules: List[str] = None,
        blocked_modules: List[str] = None
    ):
        self.timeout = timeout
        self.max_output_size = max_output_size
        self.allowed_modules = allowed_modules
        self.blocked_modules = blocked_modules or ['os', 'subprocess', 'sys', 'shutil']
        
        self.input_simulator = InputSimulator()
        self.output_capture = OutputCapture()
        
        self._globals = {}
        self._locals = {}
        self._setup_environment()
    
    def _setup_environment(self):
        """设置执行环境"""
        safe_builtins = {
            'print': print,
            'input': self._safe_input,
            'len': len,
            'range': range,
            'list': list,
            'dict': dict,
            'tuple': tuple,
            'set': set,
            'str': str,
            'int': int,
            'float': float,
            'bool': bool,
            'sum': sum,
            'max': max,
            'min': min,
            'abs': abs,
            'round': round,
            'sorted': sorted,
            'reversed': reversed,
            'enumerate': enumerate,
            'zip': zip,
            'map': map,
            'filter': filter,
            'any': any,
            'all': all,
            'isinstance': isinstance,
            'type': type,
            'hasattr': hasattr,
            'getattr': getattr,
            'setattr': setattr,
            'open': open,
            '__import__': self._safe_import,
        }
        
        self._globals = {
            '__builtins__': safe_builtins,
            '__name__': '__main__',
        }
    
    def _safe_input(self, prompt: str = "") -> str:
        """安全的输入函数"""
        if prompt:
            print(prompt, end='')
        return self.input_simulator.get_input()
    
    def _safe_import(self, name: str, *args, **kwargs):
        """安全的模块导入"""
        if self.blocked_modules and name in self.blocked_modules:
            raise ImportError(f"模块 '{name}' 被禁止导入")
        
        if self.allowed_modules and name not in self.allowed_modules:
            raise ImportError(f"模块 '{name}' 不在允许列表中")
        
        return __import__(name, *args, **kwargs)
    
    def run(
        self,
        code: str,
        inputs: List[str] = None,
        timeout: int = None
    ) -> ExecutionResult:
        """
        执行代码
        
        参数:
            code: Python代码字符串
            inputs: 预设输入列表
            timeout: 超时时间（秒）
            
        返回:
            ExecutionResult对象
        """
        if inputs:
            self.input_simulator = InputSimulator(inputs)
        else:
            self.input_simulator = InputSimulator()
        
        timeout = timeout or self.timeout
        
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        start_time = time.time()
        
        result = None
        error_msg = ""
        output = ""
        
        def execute():
            nonlocal result, error_msg, output
            
            try:
                with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                    exec(code, self._globals, self._locals)
                
                result = self._locals.get('_', None)
                
            except SyntaxError as e:
                error_msg = f"语法错误 (行 {e.lineno}): {e.msg}\n{e.text}"
            except Exception as e:
                error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        
        thread = threading.Thread(target=execute)
        thread.daemon = True
        thread.start()
        thread.join(timeout=timeout)
        
        execution_time = time.time() - start_time
        
        if thread.is_alive():
            return ExecutionResult(
                status=ExecutionStatus.TIMEOUT,
                output="",
                error=f"代码执行超时（{timeout}秒）",
                execution_time=execution_time
            )
        
        output = stdout_capture.getvalue()
        error_output = stderr_capture.getvalue()
        
        if len(output) > self.max_output_size:
            output = output[:self.max_output_size] + f"\n... (输出被截断，总长度: {len(output)})"
        
        if error_msg:
            return ExecutionResult(
                status=ExecutionStatus.ERROR,
                output=output,
                error=error_msg + "\n" + error_output,
                execution_time=execution_time
            )
        
        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output=output,
            error=error_output,
            return_value=result,
            execution_time=execution_time
        )
    
    def run_with_torch(
        self,
        code: str,
        inputs: List[str] = None,
        timeout: int = None
    ) -> ExecutionResult:
        """
        执行包含PyTorch的代码
        
        使用子进程方式执行，支持完整的PyTorch环境
        """
        timeout = timeout or self.timeout
        
        full_code = code
        
        if inputs:
            input_code = f"_inputs = {repr(inputs)}\n_input_index = 0\n"
            input_func = '''
def _mock_input(prompt=""):
    global _input_index
    if prompt:
        print(prompt, end='')
    if _input_index < len(_inputs):
        val = _inputs[_input_index]
        _input_index += 1
        return val
    return ""

__builtins__['input'] = _mock_input
'''
            full_code = input_code + input_func + "\n" + code
        
        start_time = time.time()
        
        try:
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.py',
                delete=False,
                encoding='utf-8'
            ) as f:
                f.write(full_code)
                temp_file = f.name
            
            result = subprocess.run(
                [sys.executable, temp_file],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=os.getcwd()
            )
            
            execution_time = time.time() - start_time
            
            if result.returncode == 0:
                return ExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    output=result.stdout,
                    error="",
                    execution_time=execution_time
                )
            else:
                return ExecutionResult(
                    status=ExecutionStatus.ERROR,
                    output=result.stdout,
                    error=result.stderr,
                    execution_time=execution_time
                )
                
        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            return ExecutionResult(
                status=ExecutionStatus.TIMEOUT,
                output="",
                error=f"代码执行超时（{timeout}秒）",
                execution_time=execution_time
            )
        except Exception as e:
            execution_time = time.time() - start_time
            return ExecutionResult(
                status=ExecutionStatus.ERROR,
                output="",
                error=str(e),
                execution_time=execution_time
            )
        finally:
            try:
                os.unlink(temp_file)
            except:
                pass


class InteractiveSession:
    """交互式会话"""
    
    def __init__(self, executor: CodeExecutor = None):
        self.executor = executor or CodeExecutor()
        self.history: List[Dict] = []
        self.variables: Dict = {}
    
    def execute(self, code: str, inputs: List[str] = None) -> ExecutionResult:
        """执行代码并保存历史"""
        result = self.executor.run_with_torch(code, inputs)
        
        self.history.append({
            'code': code,
            'inputs': inputs,
            'result': result.to_dict(),
            'timestamp': time.time()
        })
        
        return result
    
    def get_history(self, n: int = 10) -> List[Dict]:
        """获取最近n条历史"""
        return self.history[-n:]
    
    def clear_history(self):
        """清空历史"""
        self.history = []
    
    def save_session(self, filepath: str):
        """保存会话"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)
    
    def load_session(self, filepath: str):
        """加载会话"""
        with open(filepath, 'r', encoding='utf-8') as f:
            self.history = json.load(f)


class ExerciseRunner:
    """练习运行器"""
    
    def __init__(self):
        self.executor = CodeExecutor()
        self.session = InteractiveSession(self.executor)
        
        self.exercises = self._init_exercises()
    
    def _init_exercises(self) -> Dict:
        """初始化练习"""
        return {
            "rmsnorm_1": {
                "title": "实现RMSNorm",
                "description": "实现RMSNorm归一化层",
                "template": '''import torch
import torch.nn as nn

class RMSNorm(nn.Module):
    def __init__(self, dim: int, eps: float = 1e-6):
        super().__init__()
        # TODO: 初始化weight参数和eps
        pass
    
    def _norm(self, x: torch.Tensor) -> torch.Tensor:
        # TODO: 实现RMS归一化
        pass
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # TODO: 实现前向传播
        pass''',
                "reference": '''import torch
import torch.nn as nn

class RMSNorm(nn.Module):
    def __init__(self, dim: int, eps: float = 1e-6):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(dim))
        self.eps = eps
    
    def _norm(self, x: torch.Tensor) -> torch.Tensor:
        return x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + self.eps)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.weight * self._norm(x.float()).type_as(x)''',
                "test": '''
# 测试代码
norm = RMSNorm(64)
x = torch.randn(2, 10, 64)
output = norm(x)
assert output.shape == x.shape, f"形状错误: {output.shape} != {x.shape}"
print("✓ RMSNorm测试通过!")
print(f"  输入形状: {x.shape}")
print(f"  输出形状: {output.shape}")
print(f"  参数量: {sum(p.numel() for p in norm.parameters())}")
''',
                "difficulty": "easy",
                "module": "模块1：模型架构"
            },
            "attention_1": {
                "title": "实现多头注意力",
                "description": "实现多头注意力机制",
                "template": '''import torch
import torch.nn as nn
import math

class MultiHeadAttention(nn.Module):
    def __init__(self, d_model: int, n_heads: int):
        super().__init__()
        # TODO: 初始化投影层
        pass
    
    def forward(self, x, mask=None):
        # TODO: 实现多头注意力
        pass''',
                "reference": '''import torch
import torch.nn as nn
import math

class MultiHeadAttention(nn.Module):
    def __init__(self, d_model: int, n_heads: int):
        super().__init__()
        assert d_model % n_heads == 0
        self.d_model = d_model
        self.n_heads = n_heads
        self.head_dim = d_model // n_heads
        
        self.W_q = nn.Linear(d_model, d_model, bias=False)
        self.W_k = nn.Linear(d_model, d_model, bias=False)
        self.W_v = nn.Linear(d_model, d_model, bias=False)
        self.W_o = nn.Linear(d_model, d_model, bias=False)
    
    def forward(self, x, mask=None):
        batch_size, seq_len, _ = x.shape
        
        Q = self.W_q(x).view(batch_size, seq_len, self.n_heads, self.head_dim).transpose(1, 2)
        K = self.W_k(x).view(batch_size, seq_len, self.n_heads, self.head_dim).transpose(1, 2)
        V = self.W_v(x).view(batch_size, seq_len, self.n_heads, self.head_dim).transpose(1, 2)
        
        scores = torch.matmul(Q, K.transpose(-2, -1)) / math.sqrt(self.head_dim)
        
        if mask is not None:
            scores = scores.masked_fill(mask == 0, float('-inf'))
        
        attn_weights = torch.softmax(scores, dim=-1)
        attn_output = torch.matmul(attn_weights, V)
        
        attn_output = attn_output.transpose(1, 2).contiguous().view(batch_size, seq_len, self.d_model)
        return self.W_o(attn_output)''',
                "test": '''
# 测试代码
mha = MultiHeadAttention(64, 8)
x = torch.randn(2, 10, 64)
output = mha(x)
assert output.shape == x.shape, f"形状错误: {output.shape} != {x.shape}"
print("✓ MultiHeadAttention测试通过!")
print(f"  输入形状: {x.shape}")
print(f"  输出形状: {output.shape}")
print(f"  参数量: {sum(p.numel() for p in mha.parameters())}")
''',
                "difficulty": "medium",
                "module": "模块1：模型架构"
            },
            "swiglu_1": {
                "title": "实现SwiGLU",
                "description": "实现SwiGLU激活函数",
                "template": '''import torch
import torch.nn as nn
import torch.nn.functional as F

class SwiGLU(nn.Module):
    def __init__(self, dim: int, hidden_dim: int = None):
        super().__init__()
        # TODO: 初始化三个线性层
        pass
    
    def forward(self, x):
        # TODO: 实现SwiGLU计算
        pass''',
                "reference": '''import torch
import torch.nn as nn
import torch.nn.functional as F

class SwiGLU(nn.Module):
    def __init__(self, dim: int, hidden_dim: int = None):
        super().__init__()
        if hidden_dim is None:
            hidden_dim = int(dim * 4 / 3)
        self.w1 = nn.Linear(dim, hidden_dim, bias=False)
        self.w2 = nn.Linear(hidden_dim, dim, bias=False)
        self.w3 = nn.Linear(dim, hidden_dim, bias=False)
    
    def forward(self, x):
        return self.w2(F.silu(self.w1(x)) * self.w3(x))''',
                "test": '''
# 测试代码
swiglu = SwiGLU(64)
x = torch.randn(2, 10, 64)
output = swiglu(x)
assert output.shape == x.shape, f"形状错误: {output.shape} != {x.shape}"
print("✓ SwiGLU测试通过!")
print(f"  输入形状: {x.shape}")
print(f"  输出形状: {output.shape}")
print(f"  参数量: {sum(p.numel() for p in swiglu.parameters())}")
''',
                "difficulty": "easy",
                "module": "模块1：模型架构"
            },
            "input_test": {
                "title": "输入输出测试",
                "description": "测试输入输出功能",
                "template": '''# 这是一个测试输入输出的练习
name = input("请输入你的名字: ")
age = input("请输入你的年龄: ")
print(f"你好，{name}！你今年{age}岁。")
''',
                "reference": '''name = input("请输入你的名字: ")
age = input("请输入你的年龄: ")
print(f"你好，{name}！你今年{age}岁。")
''',
                "test": "",
                "difficulty": "easy",
                "module": "测试模块",
                "inputs": ["小明", "18"]
            }
        }
    
    def get_exercise(self, exercise_id: str) -> Optional[Dict]:
        """获取练习"""
        return self.exercises.get(exercise_id)
    
    def list_exercises(self) -> List[Dict]:
        """列出所有练习"""
        return [
            {
                "id": ex_id,
                "title": ex["title"],
                "module": ex["module"],
                "difficulty": ex["difficulty"]
            }
            for ex_id, ex in self.exercises.items()
        ]
    
    def run_exercise(
        self,
        exercise_id: str,
        user_code: str,
        inputs: List[str] = None
    ) -> ExecutionResult:
        """运行练习"""
        ex = self.get_exercise(exercise_id)
        if not ex:
            return ExecutionResult(
                status=ExecutionStatus.ERROR,
                output="",
                error=f"找不到练习: {exercise_id}"
            )
        
        full_code = user_code
        if ex.get("test"):
            full_code = user_code + "\n" + ex["test"]
        
        exercise_inputs = inputs or ex.get("inputs", [])
        
        return self.session.execute(full_code, exercise_inputs)


def main():
    """主函数 - 演示代码执行器"""
    print("=" * 60)
    print("MiniMind 增强版代码执行引擎演示")
    print("=" * 60)
    
    runner = ExerciseRunner()
    
    print("\n可用练习:")
    for ex in runner.list_exercises():
        print(f"  - {ex['id']}: {ex['title']} ({ex['difficulty']})")
    
    print("\n" + "=" * 60)
    print("测试1: 简单输出")
    print("=" * 60)
    
    result = runner.session.execute('''
print("Hello, MiniMind!")
print("这是一个测试")
for i in range(5):
    print(f"数字: {i}")
''')
    
    print(f"状态: {result.status.value}")
    print(f"输出:\n{result.output}")
    print(f"耗时: {result.execution_time:.3f}秒")
    
    print("\n" + "=" * 60)
    print("测试2: 带输入的代码")
    print("=" * 60)
    
    result = runner.session.execute('''
name = input("请输入名字: ")
age = input("请输入年龄: ")
print(f"你好，{name}！你{age}岁了。")
''', inputs=["小明", "18"])
    
    print(f"状态: {result.status.value}")
    print(f"输出:\n{result.output}")
    
    print("\n" + "=" * 60)
    print("测试3: 运行练习")
    print("=" * 60)
    
    ex = runner.get_exercise("swiglu_1")
    print(f"练习: {ex['title']}")
    
    result = runner.run_exercise("swiglu_1", ex["reference"])
    
    print(f"状态: {result.status.value}")
    print(f"输出:\n{result.output}")
    
    print("\n演示完成!")


if __name__ == "__main__":
    main()
