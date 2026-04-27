"""
DeepSeek-V3 对话机器人 - 使用训练好的模型
交互式对话界面
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import math
import json
import os
import re
from typing import List, Dict, Optional, Tuple


# ==================== 模型组件 ====================

class MLALayer(nn.Module):
    """Multi-Head Latent Attention"""
    
    def __init__(self, d_model: int, n_heads: int, d_kv_compress: int, dropout: float = 0.1):
        super().__init__()
        self.n_heads = n_heads
        self.d_head = d_model // n_heads
        self.d_kv_compress = d_kv_compress
        
        self.wq = nn.Linear(d_model, d_model, bias=False)
        self.wkv_compress = nn.Linear(d_model, d_kv_compress, bias=False)
        self.wk_up = nn.Linear(d_kv_compress, d_model, bias=False)
        self.wv_up = nn.Linear(d_kv_compress, d_model, bias=False)
        self.wo = nn.Linear(d_model, d_model, bias=False)
        self.dropout = nn.Dropout(dropout)
        
    def forward(self, x: torch.Tensor, mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        B, T, C = x.shape
        
        q = self.wq(x).view(B, T, self.n_heads, self.d_head).transpose(1, 2)
        kv_c = self.wkv_compress(x)
        k = self.wk_up(kv_c).view(B, T, self.n_heads, self.d_head).transpose(1, 2)
        v = self.wv_up(kv_c).view(B, T, self.n_heads, self.d_head).transpose(1, 2)
        
        scale = 1.0 / math.sqrt(self.d_head)
        attn = torch.matmul(q, k.transpose(-2, -1)) * scale
        
        if mask is not None:
            attn = attn.masked_fill(mask == 0, float('-inf'))
        
        attn = F.softmax(attn, dim=-1)
        attn = self.dropout(attn)
        
        out = torch.matmul(attn, v)
        out = out.transpose(1, 2).contiguous().view(B, T, C)
        return self.wo(out)


class Expert(nn.Module):
    def __init__(self, d_model: int, d_ff: int, dropout: float = 0.1):
        super().__init__()
        self.w1 = nn.Linear(d_model, d_ff, bias=False)
        self.w2 = nn.Linear(d_ff, d_model, bias=False)
        self.dropout = nn.Dropout(dropout)
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.dropout(self.w2(F.silu(self.w1(x))))


class DeepSeekMoE(nn.Module):
    def __init__(self, d_model: int, d_ff: int, n_routed: int = 16, n_shared: int = 2, 
                 top_k: int = 4, dropout: float = 0.1):
        super().__init__()
        self.n_routed = n_routed
        self.n_shared = n_shared
        self.top_k = top_k
        
        self.routed_experts = nn.ModuleList([
            Expert(d_model, d_ff // 4, dropout) for _ in range(n_routed)
        ])
        self.shared_experts = nn.ModuleList([
            Expert(d_model, d_ff // 2, dropout) for _ in range(n_shared)
        ])
        self.gate = nn.Linear(d_model, n_routed, bias=False)
        
    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        B, T, D = x.shape
        
        gate_logits = self.gate(x)
        top_k_w, top_k_idx = torch.topk(gate_logits, self.top_k, dim=-1)
        top_k_w = F.softmax(top_k_w, dim=-1)
        
        output = torch.zeros_like(x)
        x_flat = x.view(-1, D)
        top_k_w_flat = top_k_w.view(-1, self.top_k)
        top_k_idx_flat = top_k_idx.view(-1, self.top_k)
        
        for k in range(self.top_k):
            idx = top_k_idx_flat[:, k]
            w = top_k_w_flat[:, k:k+1]
            
            for e in range(self.n_routed):
                mask = (idx == e)
                if mask.any():
                    out = self.routed_experts[e](x_flat[mask])
                    output.view(-1, D)[mask] += w[mask] * out
        
        for se in self.shared_experts:
            output = output + se(x) / self.n_shared
        
        expert_freq = F.one_hot(top_k_idx, self.n_routed).float().mean(dim=[0, 1, 2])
        router_prob = F.softmax(gate_logits, dim=-1).mean(dim=[0, 1])
        aux_loss = (expert_freq * router_prob).sum() * self.n_routed * 0.01
        
        return output, aux_loss


class DeepSeekBlock(nn.Module):
    def __init__(self, d_model: int, n_heads: int, d_kv: int, d_ff: int,
                 n_routed: int, n_shared: int, top_k: int, dropout: float = 0.1):
        super().__init__()
        self.attn = MLALayer(d_model, n_heads, d_kv, dropout)
        self.moe = DeepSeekMoE(d_model, d_ff, n_routed, n_shared, top_k, dropout)
        self.ln1 = nn.LayerNorm(d_model)
        self.ln2 = nn.LayerNorm(d_model)
        
    def forward(self, x: torch.Tensor, mask: Optional[torch.Tensor] = None) -> Tuple[torch.Tensor, torch.Tensor]:
        x = x + self.attn(self.ln1(x), mask)
        moe_out, aux_loss = self.moe(self.ln2(x))
        x = x + moe_out
        return x, aux_loss


class MultiTokenHead(nn.Module):
    def __init__(self, d_model: int, vocab_size: int, n_pred: int = 2, dropout: float = 0.1):
        super().__init__()
        self.n_pred = n_pred
        self.heads = nn.ModuleList([
            nn.Sequential(
                nn.Linear(d_model, d_model * 2),
                nn.GELU(),
                nn.Dropout(dropout),
                nn.Linear(d_model * 2, vocab_size)
            ) for _ in range(n_pred)
        ])
        
    def forward(self, x: torch.Tensor, labels: Optional[torch.Tensor] = None) -> Tuple[List[torch.Tensor], Optional[torch.Tensor]]:
        logits_list = [head(x) for head in self.heads]
        return logits_list, None


class DeepSeekV3Model(nn.Module):
    def __init__(self, vocab_size: int, d_model: int = 256, n_layers: int = 4,
                 n_heads: int = 8, d_kv_compress: int = 64, d_ff: int = 512,
                 n_routed: int = 16, n_shared: int = 2, top_k: int = 4,
                 n_pred: int = 2, dropout: float = 0.1, max_seq_len: int = 128):
        super().__init__()
        
        self.d_model = d_model
        self.vocab_size = vocab_size
        
        self.tok_emb = nn.Embedding(vocab_size, d_model)
        self.pos_emb = nn.Embedding(max_seq_len, d_model)
        
        self.layers = nn.ModuleList([
            DeepSeekBlock(d_model, n_heads, d_kv_compress, d_ff, n_routed, n_shared, top_k, dropout)
            for _ in range(n_layers)
        ])
        
        self.ln_f = nn.LayerNorm(d_model)
        self.mtp_head = MultiTokenHead(d_model, vocab_size, n_pred, dropout)
        
    def forward(self, input_ids: torch.Tensor, labels: Optional[torch.Tensor] = None) -> Dict:
        B, T = input_ids.shape
        device = input_ids.device
        
        pos = torch.arange(T, device=device).unsqueeze(0)
        x = self.tok_emb(input_ids) + self.pos_emb(pos)
        
        mask = torch.tril(torch.ones(T, T, device=device)).unsqueeze(0).unsqueeze(0)
        
        total_aux_loss = 0.0
        for layer in self.layers:
            x, aux_loss = layer(x, mask)
            total_aux_loss += aux_loss
        
        x = self.ln_f(x)
        logits_list, mtp_loss = self.mtp_head(x, labels)
        
        return {
            'logits': logits_list[0],
            'logits_list': logits_list,
            'loss': mtp_loss,
            'aux_loss': total_aux_loss / len(self.layers)
        }
    
    @torch.no_grad()
    def generate(self, input_ids: torch.Tensor, max_len: int = 50, 
                 temperature: float = 0.8, top_p: float = 0.9) -> torch.Tensor:
        self.eval()
        device = input_ids.device
        
        for _ in range(max_len):
            outputs = self.forward(input_ids)
            logits = outputs['logits'][:, -1, :] / temperature
            
            sorted_logits, sorted_idx = torch.sort(logits, descending=True)
            cum_probs = torch.cumsum(F.softmax(sorted_logits, dim=-1), dim=-1)
            sorted_rm = cum_probs > top_p
            sorted_rm[..., 1:] = sorted_rm[..., :-1].clone()
            sorted_rm[..., 0] = 0
            
            idx_rm = sorted_rm.scatter(1, sorted_idx, sorted_rm)
            logits = logits.masked_fill(idx_rm, float('-inf'))
            
            probs = F.softmax(logits, dim=-1)
            next_token = torch.multinomial(probs, 1)
            
            input_ids = torch.cat([input_ids, next_token], dim=1)
            
            if (next_token == 2).all():
                break
        
        return input_ids


# ==================== 分词器 ====================

class BPETokenizer:
    def __init__(self):
        self.vocab: Dict[str, int] = {}
        self.idx_to_token: Dict[int, str] = {}
        self.vocab_size = 0
        
    def load(self, path: str):
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.vocab = data['vocab']
        self.idx_to_token = {int(k): v for k, v in data['idx_to_token'].items()}
        self.vocab_size = len(self.vocab)
    
    def encode(self, text: str, max_len: int = 128) -> List[int]:
        # 尝试匹配最长词
        text = text.strip()
        ids = []
        i = 0
        while i < len(text) and len(ids) < max_len - 2:
            # 尝试最长匹配
            matched = False
            for length in range(min(10, len(text) - i), 0, -1):
                word = text[i:i+length]
                if word in self.vocab:
                    ids.append(self.vocab[word])
                    i += length
                    matched = True
                    break
            if not matched:
                # 单个字符
                char = text[i]
                ids.append(self.vocab.get(char, self.vocab['<unk>']))
                i += 1
        
        return [self.vocab['<sos>']] + ids + [self.vocab['<eos>']]
    
    def decode(self, ids: List[int]) -> str:
        words = []
        for idx in ids:
            if idx == self.vocab['<eos>']:
                break
            if idx not in [self.vocab['<pad>'], self.vocab['<sos>']]:
                words.append(self.idx_to_token.get(idx, '<unk>'))
        return ''.join(words)


# ==================== 对话机器人 ====================

class TrainedChatbot:
    """使用训练好模型的对话机器人"""
    
    def __init__(self, checkpoint_dir: str = r'c:\Users\林智涵\.conda\checkpoints'):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.checkpoint_dir = checkpoint_dir
        
        # 加载分词器
        tokenizer_path = os.path.join(checkpoint_dir, 'tokenizer.json')
        self.tokenizer = BPETokenizer()
        self.tokenizer.load(tokenizer_path)
        print(f"分词器加载完成，词汇量: {self.tokenizer.vocab_size}")
        
        # 加载模型
        self.model = self._load_model()
        print(f"模型加载完成，设备: {self.device}")
        
        # 对话历史
        self.history: List[Dict[str, str]] = []
        
    def _load_model(self) -> DeepSeekV3Model:
        model = DeepSeekV3Model(
            vocab_size=self.tokenizer.vocab_size,
            d_model=256,
            n_layers=4,
            n_heads=8,
            d_kv_compress=64,
            d_ff=512,
            n_routed=16,
            n_shared=2,
            top_k=4,
            n_pred=2,
            dropout=0.1,
            max_seq_len=128
        ).to(self.device)
        
        checkpoint_path = os.path.join(self.checkpoint_dir, 'best_model.pt')
        checkpoint = torch.load(checkpoint_path, map_location=self.device, weights_only=False)
        model.load_state_dict(checkpoint['model_state_dict'])
        model.eval()
        
        return model
    
    def chat(self, user_input: str, max_len: int = 50, temperature: float = 0.7) -> str:
        """生成回复"""
        self.history.append({'role': 'user', 'content': user_input})
        
        # 编码输入
        input_ids = self.tokenizer.encode(user_input)
        input_tensor = torch.tensor([input_ids], dtype=torch.long, device=self.device)
        
        # 生成回复
        output_ids = self.model.generate(
            input_tensor, 
            max_len=max_len, 
            temperature=temperature
        )
        
        # 解码输出
        response = self.tokenizer.decode(output_ids[0].cpu().tolist())
        
        # 清理输出
        response = self._clean_response(response, user_input)
        
        self.history.append({'role': 'bot', 'content': response})
        return response
    
    def _clean_response(self, response: str, user_input: str) -> str:
        """清理和优化回复"""
        # 移除特殊token
        response = response.replace('<unk>', '')
        response = response.replace('<pad>', '')
        response = response.replace('<sos>', '')
        response = response.replace('<eos>', '')
        
        # 移除输入中的内容（避免重复）
        if user_input in response:
            response = response.replace(user_input, '')
        
        # 清理空白
        response = response.strip()
        
        # 如果回复为空，返回默认消息
        if not response:
            response = "我正在学习中，请换个问题问我吧~"
        
        return response
    
    def get_history(self, last_n: int = 10) -> str:
        """获取对话历史"""
        history = self.history[-last_n:]
        lines = []
        for msg in history:
            role = "你" if msg['role'] == 'user' else "AI"
            lines.append(f"{role}: {msg['content']}")
        return "\n".join(lines)
    
    def clear_history(self):
        """清空对话历史"""
        self.history = []
        print("对话历史已清空")


def interactive_chat():
    """交互式对话"""
    print("=" * 60)
    print("DeepSeek-V3 对话机器人")
    print("基于LCCC数据集训练")
    print("=" * 60)
    print("命令:")
    print("  quit/exit  - 退出")
    print("  history    - 查看对话历史")
    print("  clear      - 清空对话历史")
    print("  temp 0.8   - 调整温度 (0.1-2.0)")
    print("=" * 60)
    
    # 加载模型
    print("\n加载模型中...")
    chatbot = TrainedChatbot()
    print("模型加载完成！\n")
    
    temperature = 0.7
    
    while True:
        try:
            user_input = input("\n你: ").strip()
            
            if not user_input:
                continue
            
            # 命令处理
            if user_input.lower() in ['quit', 'exit', '退出']:
                print("\nAI: 再见！下次再聊！")
                break
            
            if user_input.lower() in ['history', '历史']:
                print("\n--- 对话历史 ---")
                print(chatbot.get_history())
                print("----------------")
                continue
            
            if user_input.lower() in ['clear', '清空']:
                chatbot.clear_history()
                continue
            
            if user_input.lower().startswith('temp '):
                try:
                    temperature = float(user_input.split()[1])
                    temperature = max(0.1, min(2.0, temperature))
                    print(f"温度已设置为: {temperature}")
                except:
                    print("格式错误，请使用: temp 0.8")
                continue
            
            # 生成回复
            response = chatbot.chat(user_input, temperature=temperature)
            print(f"\nAI: {response}")
            
        except KeyboardInterrupt:
            print("\n\nAI: 再见！")
            break
        except Exception as e:
            print(f"\n[错误] {e}")


if __name__ == "__main__":
    interactive_chat()
