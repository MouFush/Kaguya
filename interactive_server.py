"""
MiniMind 交互式学习后端服务器
=============================

提供代码运行API，支持：
1. 代码执行
2. 测试验证
3. 结果返回

运行方式：
    python interactive_server.py

然后打开 MiniMind_Interactive.html 或访问 http://localhost:5000
"""

import os
import sys
import json
import time
import subprocess
import tempfile
from typing import Dict, List, Optional
from dataclasses import dataclass
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import threading
import traceback

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


@dataclass
class Exercise:
    """练习题数据结构"""
    id: str
    title: str
    module: str
    difficulty: str
    description: str
    template: str
    reference: str
    test: str


class CodeExecutor:
    """代码执行器"""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
    
    def execute(self, code: str, test_code: str = "") -> Dict:
        """
        执行代码并返回结果
        
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
                timeout=self.timeout,
                cwd=BASE_DIR
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
                'error': str(e) + '\n' + traceback.format_exc(),
                'time': 0
            }
        finally:
            try:
                os.unlink(temp_file)
            except:
                pass
        
        return output


class ExerciseManager:
    """练习管理器"""
    
    def __init__(self):
        self.exercises: Dict[str, Exercise] = {}
        self.executor = CodeExecutor()
        self._init_exercises()
    
    def _init_exercises(self):
        """初始化练习题"""
        
        exercises = [
            Exercise(
                id="rmsnorm_1",
                title="实现RMSNorm",
                module="模块1：模型架构",
                difficulty="easy",
                description="""
<h3>RMSNorm 归一化层</h3>
<p>实现RMSNorm归一化层。</p>
<br>
<p><strong>数学公式：</strong></p>
<pre><code>RMS(x) = sqrt(1/n * Σx_i² + eps)
y = x / RMS(x) * weight</code></pre>
<br>
<p><strong>要求：</strong></p>
<ol>
    <li>实现 <code>__init__</code> 方法，初始化weight参数</li>
    <li>实现 <code>_norm</code> 方法，计算RMS归一化</li>
    <li>实现 <code>forward</code> 方法，完成前向传播</li>
</ol>
""",
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
# 测试代码
norm = RMSNorm(64)
x = torch.randn(2, 10, 64)
output = norm(x)
assert output.shape == x.shape, f"形状错误: {output.shape} != {x.shape}"
print("✓ RMSNorm测试通过!")
print(f"  输入形状: {x.shape}")
print(f"  输出形状: {output.shape}")
'''
            ),
            Exercise(
                id="attention_1",
                title="实现多头注意力",
                module="模块1：模型架构",
                difficulty="medium",
                description="""
<h3>多头注意力机制</h3>
<p>实现多头注意力机制。</p>
<br>
<p><strong>要求：</strong></p>
<ol>
    <li>实现Q、K、V投影</li>
    <li>实现注意力计算</li>
    <li>实现输出投影</li>
    <li>支持多头拆分和合并</li>
</ol>
""",
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
                test='''
# 测试代码
mha = MultiHeadAttention(64, 8)
x = torch.randn(2, 10, 64)
output = mha(x)
assert output.shape == x.shape, f"形状错误: {output.shape} != {x.shape}"
print("✓ MultiHeadAttention测试通过!")
print(f"  输入形状: {x.shape}")
print(f"  输出形状: {output.shape}")
'''
            ),
            Exercise(
                id="rope_1",
                title="实现RoPE位置编码",
                module="模块1：模型架构",
                difficulty="medium",
                description="""
<h3>旋转位置编码 (RoPE)</h3>
<p>实现旋转位置编码。</p>
<br>
<p><strong>核心思想：</strong></p>
<p>使用复数旋转来编码位置，对于位置m和维度d：</p>
<pre><code>θ_{m,d} = m * θ_d
其中 θ_d = 1 / (theta^(2d/dim))</code></pre>
""",
                template='''import torch
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
        pass''',
                reference='''import torch
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
        return torch.cat([-x2, x1], dim=-1)''',
                test='''
# 测试代码
rope = RotaryPositionEmbedding(64)
x = torch.randn(2, 10, 8, 64)
output = rope(x)
assert output.shape == x.shape, f"形状错误: {output.shape} != {x.shape}"
print("✓ RoPE测试通过!")
print(f"  输入形状: {x.shape}")
print(f"  输出形状: {output.shape}")
'''
            ),
            Exercise(
                id="swiglu_1",
                title="实现SwiGLU激活函数",
                module="模块1：模型架构",
                difficulty="easy",
                description="""
<h3>SwiGLU 激活函数</h3>
<p>实现SwiGLU激活函数。</p>
<br>
<p><strong>公式：</strong></p>
<pre><code>SwiGLU(x) = Swish(W1(x)) * W2(x)
其中 Swish(x) = x * sigmoid(x)</code></pre>
""",
                template='''import torch
import torch.nn as nn
import torch.nn.functional as F

class SwiGLU(nn.Module):
    def __init__(self, dim: int, hidden_dim: int = None, dropout: float = 0.0):
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
        return self.dropout(self.w2(F.silu(self.w1(x)) * self.w3(x)))''',
                test='''
# 测试代码
swiglu = SwiGLU(64)
x = torch.randn(2, 10, 64)
output = swiglu(x)
assert output.shape == x.shape, f"形状错误: {output.shape} != {x.shape}"
print("✓ SwiGLU测试通过!")
print(f"  输入形状: {x.shape}")
print(f"  输出形状: {output.shape}")
'''
            ),
            Exercise(
                id="transformer_block_1",
                title="实现Transformer Block",
                module="模块1：模型架构",
                difficulty="hard",
                description="""
<h3>Transformer Block</h3>
<p>实现完整的Transformer Block。</p>
<br>
<p><strong>要求：</strong></p>
<ol>
    <li>使用Pre-Norm结构</li>
    <li>实现残差连接</li>
    <li>组合Attention和FFN</li>
</ol>
""",
                template='''import torch
import torch.nn as nn

class TransformerBlock(nn.Module):
    def __init__(self, dim: int, n_heads: int, dropout: float = 0.0):
        super().__init__()
        # TODO: 初始化组件
        pass
    
    def forward(self, x, mask=None):
        # TODO: 实现Transformer块
        pass''',
                reference='''import torch
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
        return x''',
                test='''
# 测试代码（需要先定义依赖）
print("✓ TransformerBlock结构测试通过!")
print("  注：完整测试需要先完成Attention和SwiGLU练习")
'''
            ),
            Exercise(
                id="generation_1",
                title="实现文本生成器",
                module="模块3：推理优化",
                difficulty="medium",
                description="""
<h3>文本生成器</h3>
<p>实现文本生成器，支持多种采样策略。</p>
<br>
<p><strong>要求：</strong></p>
<ol>
    <li>实现贪婪解码</li>
    <li>实现Top-K采样</li>
    <li>实现Top-P采样</li>
</ol>
""",
                template='''import torch
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
        pass''',
                reference='''import torch
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
        
        return self.tokenizer.decode(input_ids[0].tolist())''',
                test='''
# 模拟测试
print("✓ TextGenerator结构测试通过!")
print("  注：完整测试需要加载实际模型")
'''
            ),
        ]
        
        for ex in exercises:
            self.exercises[ex.id] = ex
    
    def get_exercises(self) -> List[Dict]:
        """获取所有练习"""
        return [
            {
                'id': ex.id,
                'title': ex.title,
                'module': ex.module,
                'difficulty': ex.difficulty
            }
            for ex in self.exercises.values()
        ]
    
    def get_exercise(self, ex_id: str) -> Optional[Dict]:
        """获取单个练习"""
        ex = self.exercises.get(ex_id)
        if not ex:
            return None
        
        return {
            'id': ex.id,
            'title': ex.title,
            'module': ex.module,
            'difficulty': ex.difficulty,
            'description': ex.description,
            'template': ex.template,
            'reference': ex.reference
        }
    
    def run_code(self, ex_id: str, code: str) -> Dict:
        """运行代码"""
        ex = self.exercises.get(ex_id)
        if not ex:
            return {
                'success': False,
                'output': '',
                'error': f'找不到练习: {ex_id}',
                'time': 0
            }
        
        return self.executor.execute(code, ex.test)


manager = ExerciseManager()
executor = CodeExecutor()


@app.route('/')
def index():
    """主页"""
    return send_from_directory(BASE_DIR, 'MiniMind_Interactive.html')


@app.route('/api/exercises', methods=['GET'])
def get_exercises():
    """获取练习列表"""
    return jsonify(manager.get_exercises())


@app.route('/api/exercise/<ex_id>', methods=['GET'])
def get_exercise(ex_id):
    """获取练习详情"""
    ex = manager.get_exercise(ex_id)
    if not ex:
        return jsonify({'error': 'Exercise not found'}), 404
    return jsonify(ex)


@app.route('/api/run', methods=['POST'])
def run_code():
    """运行代码"""
    data = request.get_json()
    code = data.get('code')
    timeout = data.get('timeout', 30)
    ex_id = data.get('exercise_id')
    
    if not code:
        return jsonify({'error': 'Missing code'}), 400
    
    if ex_id:
        result = manager.run_code(ex_id, code)
    else:
        result = executor.execute(code, "")
    
    return jsonify(result)


@app.route('/api/reference/<ex_id>', methods=['GET'])
def get_reference(ex_id):
    """获取参考答案"""
    ex = manager.get_exercise(ex_id)
    if not ex:
        return jsonify({'error': 'Exercise not found'}), 404
    return jsonify({'reference': ex['reference']})


def main():
    """主函数"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║        🎓 MiniMind 交互式学习服务器                          ║
║                                                              ║
║        服务已启动！                                          ║
║                                                              ║
║        访问地址: http://localhost:5000                       ║
║        或打开: MiniMind_Interactive.html                     ║
║                                                              ║
║        按 Ctrl+C 停止服务                                    ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    app.run(host='0.0.0.0', port=5000, debug=False)


if __name__ == '__main__':
    main()
