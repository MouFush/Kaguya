"""
MiniMind 代码运行服务器
=======================

提供HTTP API接口，允许前端运行Python代码并获取结果。

使用方法：
    python code_runner_server.py

依赖：
    pip install fastapi uvicorn
"""

import os
import sys
import subprocess
import time
from typing import Optional
from dataclasses import dataclass
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


@dataclass
class Exercise:
    id: str
    title: str
    description: str
    template: str
    reference: str
    test: str
    difficulty: str
    module: str


class ExerciseManager:
    def __init__(self):
        self.exercises = self._init_exercises()
    
    def _init_exercises(self) -> dict:
        exercises = [
            Exercise(
                id="rmsnorm_1",
                title="实现RMSNorm",
                description="实现RMSNorm归一化层",
                template='''import torch
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
                reference='''import torch
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
                test='''
norm = RMSNorm(64)
x = torch.randn(2, 10, 64)
output = norm(x)
assert output.shape == x.shape
print("RMSNorm测试通过!")''',
                difficulty="easy",
                module="模块1：模型架构"
            ),
            Exercise(
                id="attention_1",
                title="实现多头注意力",
                description="实现多头注意力机制",
                template='''import torch
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
                reference='''import torch
import torch.nn as nn
import math

class MultiHeadAttention(nn.Module):
    def __init__(self, d_model: int, n_heads: int):
        super().__init__()
        self.d_model = d_model
        self.n_heads = n_heads
        self.head_dim = d_model // n_heads
        self.W_q = nn.Linear(d_model, d_model, bias=False)
        self.W_k = nn.Linear(d_model, d_model, bias=False)
        self.W_v = nn.Linear(d_model, d_model, bias=False)
        self.W_o = nn.Linear(d_model, d_model, bias=False)
    
    def forward(self, x, mask=None):
        b, s, _ = x.shape
        Q = self.W_q(x).view(b, s, self.n_heads, self.head_dim).transpose(1, 2)
        K = self.W_k(x).view(b, s, self.n_heads, self.head_dim).transpose(1, 2)
        V = self.W_v(x).view(b, s, self.n_heads, self.head_dim).transpose(1, 2)
        scores = torch.matmul(Q, K.transpose(-2, -1)) / math.sqrt(self.head_dim)
        if mask is not None:
            scores = scores.masked_fill(mask == 0, float('-inf'))
        attn_weights = torch.softmax(scores, dim=-1)
        out = torch.matmul(attn_weights, V)
        out = out.transpose(1, 2).contiguous().view(b, s, self.d_model)
        return self.W_o(out)''',
                test='''
mha = MultiHeadAttention(64, 8)
x = torch.randn(2, 10, 64)
output = mha(x)
assert output.shape == x.shape
print("MultiHeadAttention测试通过!")''',
                difficulty="medium",
                module="模块1：模型架构"
            ),
            Exercise(
                id="swiglu_1",
                title="实现SwiGLU",
                description="实现SwiGLU激活函数",
                template='''import torch
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
                reference='''import torch
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
                test='''
swiglu = SwiGLU(64)
x = torch.randn(2, 10, 64)
output = swiglu(x)
assert output.shape == x.shape
print("SwiGLU测试通过!")''',
                difficulty="easy",
                module="模块1：模型架构"
            ),
        ]
        return {ex.id: ex for ex in exercises}
    
    def get_exercise(self, exercise_id: str) -> Optional[Exercise]:
        return self.exercises.get(exercise_id)
    
    def list_exercises(self):
        return [
            {
                "id": ex.id,
                "title": ex.title,
                "module": ex.module,
                "difficulty": ex.difficulty,
                "description": ex.description,
                "template": ex.template
            }
            for ex in self.exercises.values()
        ]


app = FastAPI(title="MiniMind 代码运行器")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

exercise_manager = ExerciseManager()


class RunRequest(BaseModel):
    code: str
    test_code: str = ""
    timeout: int = 30


@app.get("/")
async def root():
    return {"message": "MiniMind 代码运行器 API", "version": "1.0"}


@app.post("/run")
async def run_code(request: RunRequest):
    full_code = request.code
    if request.test_code:
        full_code += "\n\n" + request.test_code
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            [sys.executable, '-c', full_code],
            capture_output=True,
            text=True,
            timeout=request.timeout,
            cwd=os.getcwd()
        )
        
        elapsed = time.time() - start_time
        
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr,
            "time": elapsed
        }
        
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": "",
            "error": f"代码执行超时（{request.timeout}秒）",
            "time": request.timeout
        }
    except Exception as e:
        return {
            "success": False,
            "output": "",
            "error": str(e),
            "time": 0
        }


@app.get("/exercises")
async def get_exercises():
    return {"exercises": exercise_manager.list_exercises()}


@app.get("/exercises/{exercise_id}")
async def get_exercise(exercise_id: str):
    ex = exercise_manager.get_exercise(exercise_id)
    if not ex:
        raise HTTPException(status_code=404, detail="练习不存在")
    
    return {
        "id": ex.id,
        "title": ex.title,
        "module": ex.module,
        "difficulty": ex.difficulty,
        "description": ex.description,
        "template": ex.template,
        "reference": ex.reference,
        "test": ex.test
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
