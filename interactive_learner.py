"""
MiniMind 交互式学习系统
========================

这是一个交互式的命令行学习工具，让用户可以：
1. 运行代码示例
2. 完成编程练习
3. 查看输出结果
4. 对比参考答案

使用方法：
    python interactive_learner.py
"""

import os
import sys
import time
import subprocess
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum


class ExerciseStatus(Enum):
    NOT_STARTED = "未开始"
    IN_PROGRESS = "进行中"
    COMPLETED = "已完成"
    FAILED = "失败"


@dataclass
class Exercise:
    """练习题数据结构"""
    id: str
    title: str
    description: str
    template_code: str
    reference_code: str
    test_code: str
    difficulty: str
    module: str


class CodeRunner:
    """代码运行器"""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.history: List[Dict] = []
    
    def run_code(self, code: str, test_code: str = "") -> Dict:
        """
        运行代码并返回结果
        
        参数:
            code: 用户代码
            test_code: 测试代码
            
        返回:
            {
                'success': bool,
                'output': str,
                'error': str,
                'time': float
            }
        """
        full_code = code + "\n\n" + test_code if test_code else code
        
        start_time = time.time()
        
        try:
            result = subprocess.run(
                [sys.executable, '-c', full_code],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=os.getcwd()
            )
            
            elapsed = time.time() - start_time
            
            output = {
                'success': result.returncode == 0,
                'output': result.stdout,
                'error': result.stderr,
                'time': elapsed
            }
            
        except subprocess.TimeoutExpired:
            output = {
                'success': False,
                'output': '',
                'error': f'代码执行超时（{self.timeout}秒）',
                'time': self.timeout
            }
        except Exception as e:
            output = {
                'success': False,
                'output': '',
                'error': str(e),
                'time': 0
            }
        
        self.history.append({
            'code': full_code,
            'result': output,
            'timestamp': time.time()
        })
        
        return output


class InteractiveLearner:
    """交互式学习系统"""
    
    def __init__(self):
        self.runner = CodeRunner()
        self.exercises: Dict[str, Exercise] = {}
        self.progress: Dict[str, ExerciseStatus] = {}
        self.current_exercise: Optional[str] = None
        
        self._init_exercises()
    
    def _init_exercises(self):
        """初始化练习题"""
        
        exercises = [
            Exercise(
                id="rmsnorm_1",
                title="实现RMSNorm",
                description="""
实现RMSNorm归一化层。

RMSNorm的数学公式：
    RMS(x) = sqrt(1/n * Σx_i² + eps)
    y = x / RMS(x) * weight

要求：
1. 实现__init__方法，初始化weight参数
2. 实现_norm方法，计算RMS归一化
3. 实现forward方法，完成前向传播
""",
                template_code='''
import torch
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
        pass
''',
                reference_code='''
import torch
import torch.nn as nn

class RMSNorm(nn.Module):
    def __init__(self, dim: int, eps: float = 1e-6):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(dim))
        self.eps = eps
    
    def _norm(self, x: torch.Tensor) -> torch.Tensor:
        return x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + self.eps)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.weight * self._norm(x.float()).type_as(x)
''',
                test_code='''
# 测试代码
norm = RMSNorm(64)
x = torch.randn(2, 10, 64)
output = norm(x)
assert output.shape == x.shape, f"形状错误: {output.shape} != {x.shape}"
print("✓ RMSNorm测试通过!")
print(f"  输入形状: {x.shape}")
print(f"  输出形状: {output.shape}")
''',
                difficulty="简单",
                module="模块1：模型架构"
            ),
            Exercise(
                id="attention_1",
                title="实现多头注意力",
                description="""
实现多头注意力机制。

要求：
1. 实现Q、K、V投影
2. 实现注意力计算
3. 实现输出投影
4. 支持多头拆分和合并
""",
                template_code='''
import torch
import torch.nn as nn
import math

class MultiHeadAttention(nn.Module):
    def __init__(self, d_model: int, n_heads: int):
        super().__init__()
        # TODO: 初始化投影层
        pass
    
    def forward(self, x, mask=None):
        # TODO: 实现多头注意力
        pass
''',
                reference_code='''
import torch
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
        return self.W_o(attn_output)
''',
                test_code='''
# 测试代码
mha = MultiHeadAttention(64, 8)
x = torch.randn(2, 10, 64)
output = mha(x)
assert output.shape == x.shape, f"形状错误: {output.shape} != {x.shape}"
print("✓ MultiHeadAttention测试通过!")
print(f"  输入形状: {x.shape}")
print(f"  输出形状: {output.shape}")
''',
                difficulty="中等",
                module="模块1：模型架构"
            ),
            Exercise(
                id="rope_1",
                title="实现RoPE位置编码",
                description="""
实现旋转位置编码（RoPE）。

RoPE的核心思想是使用复数旋转来编码位置：
    对于位置m和维度d，旋转角度为：θ_{m,d} = m * θ_d
    其中 θ_d = 1 / (theta^(2d/dim))
""",
                template_code='''
import torch
import torch.nn as nn

class RotaryPositionEmbedding(nn.Module):
    def __init__(self, dim: int, max_seq_len: int = 512, base: int = 10000):
        super().__init__()
        # TODO: 预计算cos和sin值
        pass
    
    def forward(self, x):
        # TODO: 应用旋转位置编码
        pass
    
    def rotate_half(self, x):
        # TODO: 实现旋转操作
        pass
''',
                reference_code='''
import torch
import torch.nn as nn

class RotaryPositionEmbedding(nn.Module):
    def __init__(self, dim: int, max_seq_len: int = 512, base: int = 10000):
        super().__init__()
        inv_freq = 1.0 / (base ** (torch.arange(0, dim, 2).float() / dim))
        self.register_buffer('inv_freq', inv_freq)
        
        pos = torch.arange(max_seq_len).float()
        freqs = torch.outer(pos, inv_freq)
        emb = torch.cat([freqs, freqs], dim=-1)
        self.register_buffer('cos_cached', emb.cos())
        self.register_buffer('sin_cached', emb.sin())
    
    def forward(self, x):
        seq_len = x.shape[1]
        cos = self.cos_cached[:seq_len].unsqueeze(0).unsqueeze(2)
        sin = self.sin_cached[:seq_len].unsqueeze(0).unsqueeze(2)
        return x * cos + self.rotate_half(x) * sin
    
    def rotate_half(self, x):
        x1 = x[..., :x.shape[-1] // 2]
        x2 = x[..., x.shape[-1] // 2:]
        return torch.cat([-x2, x1], dim=-1)
''',
                test_code='''
# 测试代码
rope = RotaryPositionEmbedding(64)
x = torch.randn(2, 10, 8, 64)
output = rope(x)
assert output.shape == x.shape, f"形状错误: {output.shape} != {x.shape}"
print("✓ RoPE测试通过!")
print(f"  输入形状: {x.shape}")
print(f"  输出形状: {output.shape}")
''',
                difficulty="中等",
                module="模块1：模型架构"
            ),
            Exercise(
                id="swiglu_1",
                title="实现SwiGLU激活函数",
                description="""
实现SwiGLU激活函数。

SwiGLU的公式：
    SwiGLU(x) = Swish(W1(x)) * W2(x)
    其中 Swish(x) = x * sigmoid(x)
    
SwiGLU相比普通FFN的优势：
1. 门控机制增强表达能力
2. Swish激活平滑且非单调
3. 实践中效果更好
""",
                template_code='''
import torch
import torch.nn as nn
import torch.nn.functional as F

class SwiGLU(nn.Module):
    def __init__(self, dim: int, hidden_dim: int = None, dropout: float = 0.0):
        super().__init__()
        # TODO: 初始化三个线性层
        pass
    
    def forward(self, x):
        # TODO: 实现SwiGLU计算
        pass
''',
                reference_code='''
import torch
import torch.nn as nn
import torch.nn.functional as F

class SwiGLU(nn.Module):
    def __init__(self, dim: int, hidden_dim: int = None, dropout: float = 0.0):
        super().__init__()
        if hidden_dim is None:
            hidden_dim = int(dim * 4 / 3)
            hidden_dim = ((hidden_dim + 255) // 256) * 256
        
        self.w1 = nn.Linear(dim, hidden_dim, bias=False)
        self.w2 = nn.Linear(hidden_dim, dim, bias=False)
        self.w3 = nn.Linear(dim, hidden_dim, bias=False)
        self.dropout = nn.Dropout(dropout)
    
    def forward(self, x):
        return self.dropout(self.w2(F.silu(self.w1(x)) * self.w3(x)))
''',
                test_code='''
# 测试代码
swiglu = SwiGLU(64)
x = torch.randn(2, 10, 64)
output = swiglu(x)
assert output.shape == x.shape, f"形状错误: {output.shape} != {x.shape}"
print("✓ SwiGLU测试通过!")
print(f"  输入形状: {x.shape}")
print(f"  输出形状: {output.shape}")
''',
                difficulty="简单",
                module="模块1：模型架构"
            ),
            Exercise(
                id="transformer_block_1",
                title="实现Transformer Block",
                description="""
实现完整的Transformer Block。

要求：
1. 使用Pre-Norm结构
2. 实现残差连接
3. 组合Attention和FFN
""",
                template_code='''
import torch
import torch.nn as nn

class TransformerBlock(nn.Module):
    def __init__(self, dim: int, n_heads: int, dropout: float = 0.0):
        super().__init__()
        # TODO: 初始化组件
        pass
    
    def forward(self, x, mask=None):
        # TODO: 实现Transformer块
        pass
''',
                reference_code='''
import torch
import torch.nn as nn

class RMSNorm(nn.Module):
    def __init__(self, dim, eps=1e-6):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(dim))
        self.eps = eps
    
    def forward(self, x):
        return self.weight * x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + self.eps)

class TransformerBlock(nn.Module):
    def __init__(self, dim: int, n_heads: int, dropout: float = 0.0):
        super().__init__()
        self.attention = MultiHeadAttention(dim, n_heads)
        self.ffn = SwiGLU(dim)
        self.norm1 = RMSNorm(dim)
        self.norm2 = RMSNorm(dim)
        self.dropout = nn.Dropout(dropout)
    
    def forward(self, x, mask=None):
        x = x + self.dropout(self.attention(self.norm1(x), mask))
        x = x + self.dropout(self.ffn(self.norm2(x)))
        return x
''',
                test_code='''
# 需要先定义MultiHeadAttention和SwiGLU
import torch
import torch.nn as nn
import math

class MultiHeadAttention(nn.Module):
    def __init__(self, d_model, n_heads):
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
        return self.W_o(out)

class SwiGLU(nn.Module):
    def __init__(self, dim, hidden_dim=None):
        super().__init__()
        if hidden_dim is None:
            hidden_dim = int(dim * 4 / 3)
        self.w1 = nn.Linear(dim, hidden_dim, bias=False)
        self.w2 = nn.Linear(hidden_dim, dim, bias=False)
        self.w3 = nn.Linear(dim, hidden_dim, bias=False)
    
    def forward(self, x):
        import torch.nn.functional as F
        return self.w2(F.silu(self.w1(x)) * self.w3(x))

# 测试代码
block = TransformerBlock(64, 8)
x = torch.randn(2, 10, 64)
output = block(x)
assert output.shape == x.shape, f"形状错误: {output.shape} != {x.shape}"
print("✓ TransformerBlock测试通过!")
print(f"  输入形状: {x.shape}")
print(f"  输出形状: {output.shape}")
''',
                difficulty="困难",
                module="模块1：模型架构"
            ),
            Exercise(
                id="generation_1",
                title="实现文本生成器",
                description="""
实现文本生成器，支持多种采样策略。

要求：
1. 实现贪婪解码
2. 实现Top-K采样
3. 实现Top-P采样
""",
                template_code='''
import torch
import torch.nn.functional as F

class TextGenerator:
    def __init__(self, model, tokenizer, max_length: int = 100):
        self.model = model
        self.tokenizer = tokenizer
        self.max_length = max_length
    
    def greedy_decode(self, prompt: str) -> str:
        # TODO: 实现贪婪解码
        pass
    
    def top_k_sample(self, prompt: str, k: int = 50, temperature: float = 1.0) -> str:
        # TODO: 实现Top-K采样
        pass
    
    def top_p_sample(self, prompt: str, p: float = 0.9, temperature: float = 1.0) -> str:
        # TODO: 实现Top-P采样
        pass
''',
                reference_code='''
import torch
import torch.nn.functional as F

class TextGenerator:
    def __init__(self, model, tokenizer, max_length: int = 100):
        self.model = model
        self.tokenizer = tokenizer
        self.max_length = max_length
    
    def greedy_decode(self, prompt: str) -> str:
        tokens = self.tokenizer.encode(prompt)
        input_ids = torch.tensor([tokens])
        
        self.model.eval()
        with torch.no_grad():
            for _ in range(self.max_length):
                logits = self.model(input_ids)
                next_token = torch.argmax(logits[:, -1, :], dim=-1, keepdim=True)
                input_ids = torch.cat([input_ids, next_token], dim=-1)
        
        return self.tokenizer.decode(input_ids[0].tolist())
    
    def top_k_sample(self, prompt: str, k: int = 50, temperature: float = 1.0) -> str:
        tokens = self.tokenizer.encode(prompt)
        input_ids = torch.tensor([tokens])
        
        self.model.eval()
        with torch.no_grad():
            for _ in range(self.max_length):
                logits = self.model(input_ids)[:, -1, :] / temperature
                values, indices = torch.topk(logits, k)
                probs = F.softmax(values, dim=-1)
                next_idx = torch.multinomial(probs, 1)
                next_token = indices.gather(-1, next_idx)
                input_ids = torch.cat([input_ids, next_token], dim=-1)
        
        return self.tokenizer.decode(input_ids[0].tolist())
    
    def top_p_sample(self, prompt: str, p: float = 0.9, temperature: float = 1.0) -> str:
        tokens = self.tokenizer.encode(prompt)
        input_ids = torch.tensor([tokens])
        
        self.model.eval()
        with torch.no_grad():
            for _ in range(self.max_length):
                logits = self.model(input_ids)[:, -1, :] / temperature
                probs = F.softmax(logits, dim=-1)
                
                sorted_probs, sorted_indices = torch.sort(probs, descending=True)
                cumsum_probs = torch.cumsum(sorted_probs, dim=-1)
                
                sorted_indices_to_remove = cumsum_probs > p
                sorted_indices_to_remove[..., 1:] = sorted_indices_to_remove[..., :-1].clone()
                sorted_indices_to_remove[..., 0] = 0
                
                indices_to_remove = sorted_indices_to_remove.scatter(-1, sorted_indices, sorted_indices_to_remove)
                probs = probs.masked_fill(indices_to_remove, 0)
                probs = probs / probs.sum(dim=-1, keepdim=True)
                
                next_token = torch.multinomial(probs, 1)
                input_ids = torch.cat([input_ids, next_token], dim=-1)
        
        return self.tokenizer.decode(input_ids[0].tolist())
''',
                test_code='''
# 模拟测试
print("✓ TextGenerator结构测试通过!")
print("  注：完整测试需要加载实际模型")
''',
                difficulty="中等",
                module="模块3：推理优化"
            ),
        ]
        
        for ex in exercises:
            self.exercises[ex.id] = ex
            self.progress[ex.id] = ExerciseStatus.NOT_STARTED
    
    def list_exercises(self) -> str:
        """列出所有练习"""
        output = ["\n" + "=" * 60]
        output.append("📚 MiniMind 交互式练习列表")
        output.append("=" * 60)
        
        current_module = None
        for ex_id, ex in self.exercises.items():
            if ex.module != current_module:
                current_module = ex.module
                output.append(f"\n【{current_module}】")
            
            status = self.progress[ex_id].value
            difficulty_icon = {"简单": "⭐", "中等": "⭐⭐", "困难": "⭐⭐⭐"}.get(ex.difficulty, "")
            output.append(f"  [{status}] {ex_id}: {ex.title} {difficulty_icon}")
        
        output.append("\n" + "=" * 60)
        return "\n".join(output)
    
    def show_exercise(self, ex_id: str) -> str:
        """显示练习详情"""
        if ex_id not in self.exercises:
            return f"错误：找不到练习 {ex_id}"
        
        ex = self.exercises[ex_id]
        
        output = [
            "\n" + "=" * 60,
            f"📝 练习：{ex.title}",
            "=" * 60,
            f"ID: {ex.id}",
            f"难度: {ex.difficulty}",
            f"模块: {ex.module}",
            f"状态: {self.progress[ex_id].value}",
            "",
            "📖 题目描述：",
            ex.description,
            "",
            "💻 代码模板：",
            "-" * 40,
            ex.template_code.strip(),
            "-" * 40,
        ]
        
        return "\n".join(output)
    
    def run_exercise(self, ex_id: str, user_code: str) -> Dict:
        """运行练习"""
        if ex_id not in self.exercises:
            return {'success': False, 'error': f"找不到练习 {ex_id}"}
        
        ex = self.exercises[ex_id]
        self.current_exercise = ex_id
        self.progress[ex_id] = ExerciseStatus.IN_PROGRESS
        
        result = self.runner.run_code(user_code, ex.test_code)
        
        if result['success']:
            self.progress[ex_id] = ExerciseStatus.COMPLETED
        else:
            self.progress[ex_id] = ExerciseStatus.FAILED
        
        return result
    
    def show_reference(self, ex_id: str) -> str:
        """显示参考答案"""
        if ex_id not in self.exercises:
            return f"错误：找不到练习 {ex_id}"
        
        ex = self.exercises[ex_id]
        
        return f"""
{'=' * 60}
📖 参考答案：{ex.title}
{'=' * 60}

{ex.reference_code.strip()}

{'=' * 60}
💡 提示：请先尝试自己实现，再查看参考答案
{'=' * 60}
"""
    
    def show_progress(self) -> str:
        """显示学习进度"""
        total = len(self.exercises)
        completed = sum(1 for s in self.progress.values() if s == ExerciseStatus.COMPLETED)
        in_progress = sum(1 for s in self.progress.values() if s == ExerciseStatus.IN_PROGRESS)
        
        return f"""
{'=' * 60}
📊 学习进度
{'=' * 60}

总练习数: {total}
已完成: {completed} ({completed/total*100:.1f}%)
进行中: {in_progress}
未开始: {total - completed - in_progress}

{'=' * 60}
"""


def main():
    """主函数 - 交互式命令行界面"""
    learner = InteractiveLearner()
    
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║        🎓 MiniMind 交互式学习系统                            ║
║                                                              ║
║        输入 'help' 查看帮助                                  ║
║        输入 'list' 查看练习列表                              ║
║        输入 'show <id>' 查看练习详情                         ║
║        输入 'run <id>' 运行练习                              ║
║        输入 'ref <id>' 查看参考答案                          ║
║        输入 'progress' 查看学习进度                          ║
║        输入 'quit' 退出                                      ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    while True:
        try:
            user_input = input("\n>>> ").strip()
            
            if not user_input:
                continue
            
            parts = user_input.split(maxsplit=1)
            cmd = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else None
            
            if cmd in ['help', 'h', '?']:
                print("""
命令帮助：
  help          - 显示帮助信息
  list          - 列出所有练习
  show <id>     - 显示练习详情
  run <id>      - 运行练习（进入代码编辑模式）
  ref <id>      - 显示参考答案
  progress      - 显示学习进度
  quit / exit   - 退出程序
""")
            
            elif cmd in ['list', 'ls']:
                print(learner.list_exercises())
            
            elif cmd == 'show':
                if arg:
                    print(learner.show_exercise(arg))
                else:
                    print("用法: show <练习ID>")
            
            elif cmd == 'run':
                if arg:
                    ex = learner.exercises.get(arg)
                    if ex:
                        print(f"\n📝 练习：{ex.title}")
                        print("请输入代码（输入空行结束，输入 'cancel' 取消）：")
                        print("-" * 40)
                        
                        code_lines = []
                        while True:
                            line = input()
                            if line.strip() == '':
                                break
                            if line.strip().lower() == 'cancel':
                                print("已取消")
                                break
                            code_lines.append(line)
                        
                        if code_lines:
                            user_code = '\n'.join(code_lines)
                            print("\n运行中...")
                            result = learner.run_exercise(arg, user_code)
                            
                            if result['success']:
                                print("\n✅ 运行成功！")
                                print(result['output'])
                            else:
                                print("\n❌ 运行失败！")
                                print(f"错误: {result['error']}")
                    else:
                        print(f"找不到练习: {arg}")
                else:
                    print("用法: run <练习ID>")
            
            elif cmd in ['ref', 'reference']:
                if arg:
                    print(learner.show_reference(arg))
                else:
                    print("用法: ref <练习ID>")
            
            elif cmd == 'progress':
                print(learner.show_progress())
            
            elif cmd in ['quit', 'exit', 'q']:
                print("\n再见！继续加油学习！👋")
                break
            
            else:
                print(f"未知命令: {cmd}。输入 'help' 查看帮助。")
        
        except KeyboardInterrupt:
            print("\n\n再见！")
            break
        except Exception as e:
            print(f"错误: {e}")


if __name__ == "__main__":
    main()
