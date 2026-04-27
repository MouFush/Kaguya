"""
DeepSeek-V3 对话模型 - LCCC数据集训练版

整合:
1. LCCC数据集 (682万条中文对话)
2. DeepSeek-V3架构 (MLA + MoE + Multi-Token Prediction)
3. 完整训练流程
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
import torch.optim as optim
from torch.optim.lr_scheduler import CosineAnnealingLR
import math
import json
import os
import re
import random
from typing import List, Dict, Tuple, Optional
from collections import Counter
from tqdm import tqdm
import time


# ==================== 分词器 ====================

class BPETokenizer:
    """BPE分词器"""
    
    def __init__(self):
        self.vocab: Dict[str, int] = {}
        self.idx_to_token: Dict[int, str] = {}
        self.vocab_size = 0
        
    def train(self, texts: List[str], vocab_size: int = 8000, min_freq: int = 2):
        """训练分词器"""
        print(f"训练分词器，目标词汇量: {vocab_size}")
        
        # 统计字符频率
        word_freq = Counter()
        for text in tqdm(texts, desc="统计词频"):
            # 按空格分割
            words = text.strip().split()
            for word in words:
                if word:
                    word_freq[word] += 1
        
        # 过滤低频词
        filtered_words = {w: c for w, c in word_freq.items() if c >= min_freq}
        
        # 按频率排序
        sorted_words = sorted(filtered_words.items(), key=lambda x: -x[1])
        
        # 添加特殊token
        special_tokens = ['<pad>', '<sos>', '<eos>', '<unk>']
        for i, token in enumerate(special_tokens):
            self.vocab[token] = i
            self.idx_to_token[i] = token
        
        # 添加高频词
        for word, _ in sorted_words[:vocab_size - len(special_tokens)]:
            if word not in self.vocab:
                idx = len(self.vocab)
                self.vocab[word] = idx
                self.idx_to_token[idx] = word
        
        self.vocab_size = len(self.vocab)
        print(f"词汇表构建完成，实际大小: {self.vocab_size}")
        
    def encode(self, text: str, max_len: int = 128) -> List[int]:
        """编码文本"""
        words = text.strip().split()
        ids = [self.vocab.get(w, self.vocab['<unk>']) for w in words if w]
        ids = ids[:max_len-2]
        return [self.vocab['<sos>']] + ids + [self.vocab['<eos>']]
    
    def decode(self, ids: List[int]) -> str:
        """解码文本"""
        words = []
        for idx in ids:
            if idx == self.vocab['<eos>']:
                break
            if idx not in [self.vocab['<pad>'], self.vocab['<sos>']]:
                words.append(self.idx_to_token.get(idx, '<unk>'))
        return ''.join(words)
    
    def save(self, path: str):
        """保存词汇表"""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({'vocab': self.vocab, 'idx_to_token': {str(k): v for k, v in self.idx_to_token.items()}}, f, ensure_ascii=False, indent=2)
    
    def load(self, path: str):
        """加载词汇表"""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.vocab = data['vocab']
        self.idx_to_token = {int(k): v for k, v in data['idx_to_token'].items()}
        self.vocab_size = len(self.vocab)


# ==================== 数据集 ====================

class LCCCDataset(Dataset):
    """LCCC对话数据集"""
    
    def __init__(self, data_path: str, tokenizer: BPETokenizer, max_len: int = 128, max_samples: int = None):
        self.tokenizer = tokenizer
        self.max_len = max_len
        self.pairs = []
        
        print(f"加载数据: {data_path}")
        with open(data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if max_samples:
            data = data[:max_samples]
        
        # 提取对话对
        for dialog in tqdm(data, desc="处理对话"):
            if isinstance(dialog, list) and len(dialog) >= 2:
                # 移除空格，合并为连续文本
                dialog = [''.join(turn.split()) for turn in dialog]
                
                # 生成对话对
                for i in range(len(dialog) - 1):
                    input_text = dialog[i]
                    target_text = dialog[i + 1]
                    
                    if input_text and target_text:
                        self.pairs.append({
                            'input': input_text,
                            'target': target_text
                        })
        
        print(f"对话对数量: {len(self.pairs)}")
    
    def __len__(self):
        return len(self.pairs)
    
    def __getitem__(self, idx):
        pair = self.pairs[idx]
        
        input_ids = self.tokenizer.encode(pair['input'], self.max_len)
        target_ids = self.tokenizer.encode(pair['target'], self.max_len)
        
        # 填充
        input_ids = input_ids + [0] * (self.max_len - len(input_ids))
        target_ids = target_ids + [0] * (self.max_len - len(target_ids))
        
        return {
            'input_ids': torch.tensor(input_ids[:self.max_len], dtype=torch.long),
            'target_ids': torch.tensor(target_ids[:self.max_len], dtype=torch.long)
        }


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
    """MoE专家"""
    def __init__(self, d_model: int, d_ff: int, dropout: float = 0.1):
        super().__init__()
        self.w1 = nn.Linear(d_model, d_ff, bias=False)
        self.w2 = nn.Linear(d_ff, d_model, bias=False)
        self.dropout = nn.Dropout(dropout)
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.dropout(self.w2(F.silu(self.w1(x))))


class DeepSeekMoE(nn.Module):
    """DeepSeek MoE"""
    
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
        
        # 负载均衡损失
        expert_freq = F.one_hot(top_k_idx, self.n_routed).float().mean(dim=[0, 1, 2])
        router_prob = F.softmax(gate_logits, dim=-1).mean(dim=[0, 1])
        aux_loss = (expert_freq * router_prob).sum() * self.n_routed * 0.01
        
        return output, aux_loss


class DeepSeekBlock(nn.Module):
    """DeepSeek Transformer块"""
    
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
    """多Token预测头"""
    
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
        
        loss = None
        if labels is not None:
            total_loss = 0.0
            for i, logits in enumerate(logits_list):
                if i + 1 < labels.shape[1]:
                    shift_logits = logits[:, :-(i+1)].contiguous()
                    shift_labels = labels[:, (i+1):].contiguous()
                    loss_i = F.cross_entropy(
                        shift_logits.view(-1, logits.size(-1)),
                        shift_labels.view(-1),
                        ignore_index=0
                    )
                    total_loss += loss_i
            loss = total_loss / self.n_pred
        
        return logits_list, loss


class DeepSeekV3Model(nn.Module):
    """DeepSeek-V3 对话模型"""
    
    def __init__(self, vocab_size: int, d_model: int = 512, n_layers: int = 8,
                 n_heads: int = 16, d_kv_compress: int = 128, d_ff: int = 2048,
                 n_routed: int = 32, n_shared: int = 2, top_k: int = 6,
                 n_pred: int = 2, dropout: float = 0.1, max_seq_len: int = 256):
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
        
        # 初始化
        self.apply(self._init_weights)
        
    def _init_weights(self, module):
        if isinstance(module, nn.Linear):
            torch.nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if module.bias is not None:
                torch.nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            torch.nn.init.normal_(module.weight, mean=0.0, std=0.02)
        elif isinstance(module, nn.LayerNorm):
            torch.nn.init.ones_(module.weight)
            torch.nn.init.zeros_(module.bias)
    
    def forward(self, input_ids: torch.Tensor, labels: Optional[torch.Tensor] = None) -> Dict:
        B, T = input_ids.shape
        device = input_ids.device
        
        pos = torch.arange(T, device=device).unsqueeze(0)
        x = self.tok_emb(input_ids) + self.pos_emb(pos)
        
        # 因果掩码
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
            
            # Top-p采样
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


# ==================== 训练器 ====================

class Trainer:
    """训练器 - 支持混合精度"""
    
    def __init__(self, model, tokenizer, train_loader, val_loader, device, config):
        self.model = model
        self.tokenizer = tokenizer
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.device = device
        self.config = config
        
        self.optimizer = optim.AdamW(model.parameters(), lr=config['lr'], weight_decay=config['weight_decay'])
        self.scheduler = CosineAnnealingLR(self.optimizer, T_max=config['epochs'], eta_min=config['lr'] * 0.1)
        
        # 混合精度训练
        self.use_amp = config.get('use_amp', True)
        self.scaler = torch.amp.GradScaler('cuda') if self.use_amp else None
        
        self.global_step = 0
        self.best_val_loss = float('inf')
        
    def train_epoch(self, epoch: int) -> Dict:
        self.model.train()
        total_loss = 0
        total_aux_loss = 0
        
        pbar = tqdm(self.train_loader, desc=f"Epoch {epoch}")
        for batch in pbar:
            input_ids = batch['input_ids'].to(self.device, non_blocking=True)
            target_ids = batch['target_ids'].to(self.device, non_blocking=True)
            
            self.optimizer.zero_grad()
            
            # 混合精度前向传播
            if self.use_amp:
                with torch.amp.autocast('cuda'):
                    outputs = self.model(input_ids, target_ids)
                    loss = outputs['loss'] + outputs['aux_loss'] * 0.1
                
                # 混合精度反向传播
                self.scaler.scale(loss).backward()
                self.scaler.unscale_(self.optimizer)
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                self.scaler.step(self.optimizer)
                self.scaler.update()
            else:
                outputs = self.model(input_ids, target_ids)
                loss = outputs['loss'] + outputs['aux_loss'] * 0.1
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                self.optimizer.step()
            
            total_loss += outputs['loss'].item()
            total_aux_loss += outputs['aux_loss'].item()
            
            pbar.set_postfix({
                'loss': f"{outputs['loss'].item():.4f}",
                'aux': f"{outputs['aux_loss'].item():.4f}"
            })
            
            self.global_step += 1
        
        self.scheduler.step()
        
        return {
            'train_loss': total_loss / len(self.train_loader),
            'aux_loss': total_aux_loss / len(self.train_loader)
        }
    
    @torch.no_grad()
    def validate(self) -> float:
        self.model.eval()
        total_loss = 0
        
        for batch in tqdm(self.val_loader, desc="Validating"):
            input_ids = batch['input_ids'].to(self.device)
            target_ids = batch['target_ids'].to(self.device)
            
            outputs = self.model(input_ids, target_ids)
            total_loss += outputs['loss'].item()
        
        return total_loss / len(self.val_loader)
    
    def save_checkpoint(self, path: str, epoch: int, val_loss: float):
        torch.save({
            'epoch': epoch,
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'val_loss': val_loss,
            'global_step': self.global_step
        }, path)
        print(f"检查点已保存: {path}")
    
    def train(self, epochs: int, save_dir: str):
        os.makedirs(save_dir, exist_ok=True)
        
        for epoch in range(1, epochs + 1):
            print(f"\n{'='*60}")
            print(f"Epoch {epoch}/{epochs}")
            print(f"{'='*60}")
            
            # 训练
            train_metrics = self.train_epoch(epoch)
            print(f"训练损失: {train_metrics['train_loss']:.4f}, 辅助损失: {train_metrics['aux_loss']:.4f}")
            
            # 验证
            val_loss = self.validate()
            print(f"验证损失: {val_loss:.4f}")
            
            # 保存最佳模型
            if val_loss < self.best_val_loss:
                self.best_val_loss = val_loss
                self.save_checkpoint(os.path.join(save_dir, 'best_model.pt'), epoch, val_loss)
            
            # 定期保存
            if epoch % 5 == 0:
                self.save_checkpoint(os.path.join(save_dir, f'checkpoint_epoch_{epoch}.pt'), epoch, val_loss)
            
            # 测试生成
            self.test_generation()
    
    def test_generation(self):
        """测试生成效果"""
        self.model.eval()
        
        test_inputs = ["你好", "今天天气怎么样", "你叫什么名字"]
        
        print("\n生成测试:")
        for text in test_inputs:
            input_ids = torch.tensor([self.tokenizer.encode(text)], device=self.device)
            output_ids = self.model.generate(input_ids, max_len=30, temperature=0.8)
            response = self.tokenizer.decode(output_ids[0].cpu().tolist())
            print(f"  输入: {text}")
            print(f"  输出: {response}")


# ==================== 主函数 ====================

def main():
    print("=" * 70)
    print("DeepSeek-V3 对话模型训练")
    print("数据集: LCCC (682万条中文对话)")
    print("=" * 70)
    
    # 配置 - 快速训练版（约25M参数，3轮训练）
    config = {
        'vocab_size': 8000,
        'd_model': 256,           # 减小模型维度
        'n_layers': 4,            # 减少层数
        'n_heads': 8,             # 减少注意力头
        'd_kv_compress': 64,      # 减小KV压缩维度
        'd_ff': 512,              # 减小FFN维度
        'n_routed': 16,           # 减少路由专家
        'n_shared': 2,
        'top_k': 4,               # 减少激活专家数
        'n_pred': 2,
        'dropout': 0.1,
        'max_seq_len': 128,       # 保持序列长度
        'batch_size': 256,        # 增大批次大小（模型小了可以增大）
        'epochs': 3,              # 减少训练轮数
        'lr': 2e-4,
        'weight_decay': 0.01,
        'max_train_samples': 200000,  # 训练样本
        'max_val_samples': 5000,
        'num_workers': 4,         # 数据加载线程
        'use_amp': True,          # 混合精度训练
    }
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"设备: {device}")
    
    # 数据路径
    data_dir = r'c:\Users\林智涵\LCCC\data'
    save_dir = r'c:\Users\林智涵\.conda\checkpoints'
    
    # 分词器
    tokenizer_path = os.path.join(save_dir, 'tokenizer.json')
    tokenizer = BPETokenizer()
    
    if os.path.exists(tokenizer_path):
        print("加载已有分词器...")
        tokenizer.load(tokenizer_path)
    else:
        print("训练分词器...")
        # 加载部分数据训练分词器
        with open(os.path.join(data_dir, 'LCCC-base_train.json'), 'r', encoding='utf-8') as f:
            train_data = json.load(f)[:100000]  # 用前10万条训练分词器
        
        texts = []
        for dialog in train_data:
            if isinstance(dialog, list):
                for turn in dialog:
                    texts.append(''.join(turn.split()))
        
        tokenizer.train(texts, vocab_size=config['vocab_size'])
        tokenizer.save(tokenizer_path)
    
    config['vocab_size'] = tokenizer.vocab_size
    print(f"词汇表大小: {config['vocab_size']}")
    
    # 数据集
    print("\n加载数据集...")
    train_dataset = LCCCDataset(
        os.path.join(data_dir, 'LCCC-base_train.json'),
        tokenizer,
        max_len=config['max_seq_len'],
        max_samples=config['max_train_samples']
    )
    
    val_dataset = LCCCDataset(
        os.path.join(data_dir, 'LCCC-base_valid.json'),
        tokenizer,
        max_len=config['max_seq_len'],
        max_samples=config['max_val_samples']
    )
    
    train_loader = DataLoader(
        train_dataset, 
        batch_size=config['batch_size'], 
        shuffle=True, 
        num_workers=config.get('num_workers', 4),
        pin_memory=True,
        persistent_workers=True if config.get('num_workers', 4) > 0 else False
    )
    val_loader = DataLoader(
        val_dataset, 
        batch_size=config['batch_size'], 
        num_workers=config.get('num_workers', 4),
        pin_memory=True,
        persistent_workers=True if config.get('num_workers', 4) > 0 else False
    )
    
    # 模型
    print("\n初始化模型...")
    model = DeepSeekV3Model(
        vocab_size=config['vocab_size'],
        d_model=config['d_model'],
        n_layers=config['n_layers'],
        n_heads=config['n_heads'],
        d_kv_compress=config['d_kv_compress'],
        d_ff=config['d_ff'],
        n_routed=config['n_routed'],
        n_shared=config['n_shared'],
        top_k=config['top_k'],
        n_pred=config['n_pred'],
        dropout=config['dropout'],
        max_seq_len=config['max_seq_len']
    ).to(device)
    
    total_params = sum(p.numel() for p in model.parameters())
    print(f"模型参数量: {total_params:,}")
    
    # 训练
    trainer = Trainer(model, tokenizer, train_loader, val_loader, device, config)
    trainer.train(config['epochs'], save_dir)
    
    # 保存分词器
    tokenizer.save(tokenizer_path)
    
    print("\n训练完成!")


if __name__ == "__main__":
    main()
