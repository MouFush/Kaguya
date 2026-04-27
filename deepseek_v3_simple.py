"""
DeepSeek-V3 核心思想简化实现

核心创新:
1. MLA (Multi-Head Latent Attention) - 多头潜在注意力
   - 通过低秩压缩KV Cache，大幅降低推理内存
   - Key和Value被压缩到低维潜在空间

2. DeepSeekMoE - 混合专家架构
   - 细粒度专家分割 (更多但更小的专家)
   - 共享专家 + 路由专家
   - 负载均衡损失

3. Multi-Token Prediction - 多Token预测
   - 同时预测多个未来token
   - 提升训练效率和模型能力

参考论文: 
- DeepSeek-V3 Technical Report
- DeepSeek-V2: A Strong, Economical, and Efficient Mixture-of-Experts Language Model
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import math
from typing import Optional, Tuple


class MLALayer(nn.Module):
    """
    Multi-Head Latent Attention (MLA) - 多头潜在注意力
    
    核心思想:
    1. 将Key和Value压缩到低维潜在空间
    2. 推理时只需缓存压缩后的潜在向量
    3. 大幅减少KV Cache大小 (从 2*n_heads*d 降到 2*d_kv_compress)
    
    内存节省比例: (n_heads * d_head) / d_kv_compress
    例如: n_heads=32, d_head=128, d_kv_compress=512
          节省比例 = 32*128/512 = 8倍
    """
    
    def __init__(
        self,
        d_model: int = 512,
        n_heads: int = 8,
        d_head: int = 64,
        d_kv_compress: int = 128,  # KV压缩维度
        dropout: float = 0.1
    ):
        super().__init__()
        self.d_model = d_model
        self.n_heads = n_heads
        self.d_head = d_head
        self.d_kv_compress = d_kv_compress
        
        # Query投影 (正常)
        self.wq = nn.Linear(d_model, n_heads * d_head, bias=False)
        
        # Key压缩投影 (核心创新)
        # 先压缩到低维，推理时只缓存这个低维向量
        self.wkv_compress = nn.Linear(d_model, d_kv_compress, bias=False)
        
        # Key上投影 (从压缩空间恢复)
        self.wk_up = nn.Linear(d_kv_compress, n_heads * d_head, bias=False)
        
        # Value上投影 (从压缩空间恢复)
        self.wv_up = nn.Linear(d_kv_compress, n_heads * d_head, bias=False)
        
        # 输出投影
        self.wo = nn.Linear(n_heads * d_head, d_model, bias=False)
        
        self.dropout = nn.Dropout(dropout)
        
    def forward(
        self,
        x: torch.Tensor,
        kv_cache: Optional[Tuple[torch.Tensor, torch.Tensor]] = None,
        use_cache: bool = False
    ) -> Tuple[torch.Tensor, Optional[Tuple[torch.Tensor, torch.Tensor]]]:
        """
        Args:
            x: [batch, seq_len, d_model]
            kv_cache: 之前的压缩KV缓存
            use_cache: 是否返回新的KV缓存
        
        Returns:
            output: [batch, seq_len, d_model]
            new_cache: 新的压缩KV缓存 (如果use_cache=True)
        """
        batch_size, seq_len, _ = x.shape
        
        # Query投影
        q = self.wq(x)  # [batch, seq_len, n_heads * d_head]
        q = q.view(batch_size, seq_len, self.n_heads, self.d_head)
        q = q.transpose(1, 2)  # [batch, n_heads, seq_len, d_head]
        
        # KV压缩 (核心创新: 只缓存这个低维向量)
        kv_compressed = self.wkv_compress(x)  # [batch, seq_len, d_kv_compress]
        
        # 如果有缓存，拼接
        if kv_cache is not None:
            k_cache, v_cache = kv_cache
            kv_compressed = torch.cat([k_cache, kv_compressed], dim=1)
        
        # 从压缩空间恢复Key和Value
        k = self.wk_up(kv_compressed)  # [batch, seq_len, n_heads * d_head]
        v = self.wv_up(kv_compressed)
        
        k = k.view(batch_size, -1, self.n_heads, self.d_head).transpose(1, 2)
        v = v.view(batch_size, -1, self.n_heads, self.d_head).transpose(1, 2)
        
        # 注意力计算
        scale = 1.0 / math.sqrt(self.d_head)
        attn_weights = torch.matmul(q, k.transpose(-2, -1)) * scale
        attn_weights = F.softmax(attn_weights, dim=-1)
        attn_weights = self.dropout(attn_weights)
        
        # 加权求和
        attn_output = torch.matmul(attn_weights, v)  # [batch, n_heads, seq_len, d_head]
        attn_output = attn_output.transpose(1, 2).contiguous()
        attn_output = attn_output.view(batch_size, seq_len, -1)
        
        # 输出投影
        output = self.wo(attn_output)
        
        # 返回压缩后的KV缓存 (而不是完整的KV)
        new_cache = None
        if use_cache:
            # 只缓存压缩后的向量，大幅节省内存
            new_cache = (kv_compressed, kv_compressed)
        
        return output, new_cache


class Expert(nn.Module):
    """单个专家网络 (MLP)"""
    def __init__(self, d_model: int, d_ff: int, dropout: float = 0.1):
        super().__init__()
        self.w1 = nn.Linear(d_model, d_ff, bias=False)
        self.w2 = nn.Linear(d_ff, d_model, bias=False)
        self.dropout = nn.Dropout(dropout)
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.dropout(self.w2(F.silu(self.w1(x))))


class DeepSeekMoE(nn.Module):
    """
    DeepSeekMoE - 混合专家架构
    
    核心创新:
    1. 细粒度专家分割: 更多但更小的专家
    2. 共享专家: 所有token都会经过的专家
    3. 路由专家: 根据路由选择的部分专家
    4. 负载均衡损失: 防止专家使用不均衡
    
    计算公式:
    output = sum(router_weights[i] * expert[i](x)) + shared_expert(x)
    
    内存节省: 每个token只激活部分专家，而非全部
    """
    
    def __init__(
        self,
        d_model: int = 512,
        d_ff: int = 2048,
        n_routed_experts: int = 64,  # 路由专家数量
        n_shared_experts: int = 2,   # 共享专家数量
        top_k: int = 6,              # 每个token激活的专家数
        dropout: float = 0.1
    ):
        super().__init__()
        self.d_model = d_model
        self.n_routed_experts = n_routed_experts
        self.n_shared_experts = n_shared_experts
        self.top_k = top_k
        
        # 路由专家
        self.routed_experts = nn.ModuleList([
            Expert(d_model, d_ff // 4, dropout)  # 每个专家更小
            for _ in range(n_routed_experts)
        ])
        
        # 共享专家 (所有token都会经过)
        self.shared_experts = nn.ModuleList([
            Expert(d_model, d_ff // 2, dropout)
            for _ in range(n_shared_experts)
        ])
        
        # 路由门控
        self.gate = nn.Linear(d_model, n_routed_experts, bias=False)
        
    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            x: [batch, seq_len, d_model]
        
        Returns:
            output: [batch, seq_len, d_model]
            aux_loss: 负载均衡辅助损失
        """
        batch_size, seq_len, d_model = x.shape
        
        # 计算路由权重
        gate_logits = self.gate(x)  # [batch, seq_len, n_routed_experts]
        
        # 选择top-k专家
        top_k_weights, top_k_indices = torch.topk(
            gate_logits, self.top_k, dim=-1
        )
        top_k_weights = F.softmax(top_k_weights, dim=-1)
        
        # 初始化输出
        output = torch.zeros_like(x)
        
        # 路由专家计算
        # 展平以便批处理
        x_flat = x.view(-1, d_model)  # [batch*seq_len, d_model]
        top_k_weights_flat = top_k_weights.view(-1, self.top_k)
        top_k_indices_flat = top_k_indices.view(-1, self.top_k)
        
        for k in range(self.top_k):
            expert_indices = top_k_indices_flat[:, k]  # [batch*seq_len]
            expert_weights = top_k_weights_flat[:, k:k+1]  # [batch*seq_len, 1]
            
            # 为每个专家处理对应的token
            for expert_idx in range(self.n_routed_experts):
                mask = (expert_indices == expert_idx)
                if mask.any():
                    expert_input = x_flat[mask]
                    expert_output = self.routed_experts[expert_idx](expert_input)
                    output_flat = output.view(-1, d_model)
                    output_flat[mask] += expert_weights[mask] * expert_output
        
        # 共享专家计算 (所有token都经过)
        for shared_expert in self.shared_experts:
            output = output + shared_expert(x) / self.n_shared_experts
        
        # 计算负载均衡损失
        aux_loss = self._compute_aux_loss(gate_logits, top_k_indices)
        
        return output, aux_loss
    
    def _compute_aux_loss(
        self,
        gate_logits: torch.Tensor,
        top_k_indices: torch.Tensor
    ) -> torch.Tensor:
        """
        计算负载均衡辅助损失
        
        目标: 让每个专家被均匀使用
        公式: aux_loss = alpha * sum(f_i * P_i)
        其中:
        - f_i: 专家i被选中的频率
        - P_i: 专家i的平均路由概率
        """
        # 专家被选中的频率
        expert_mask = F.one_hot(top_k_indices, self.n_routed_experts).float()
        expert_freq = expert_mask.mean(dim=[0, 1, 2])  # [n_routed_experts]
        
        # 专家的平均路由概率
        router_probs = F.softmax(gate_logits, dim=-1).mean(dim=[0, 1])
        
        # 负载均衡损失
        aux_loss = (expert_freq * router_probs).sum() * self.n_routed_experts
        
        return aux_loss * 0.01  # 缩放系数


class MultiTokenPredictionHead(nn.Module):
    """
    多Token预测头
    
    核心思想:
    1. 同时预测未来n个token
    2. 使用共享的transformer + 独立的预测头
    3. 提升训练效率和模型能力
    
    损失: L = sum(L_i) 其中L_i是第i个token的预测损失
    """
    
    def __init__(
        self,
        d_model: int = 512,
        vocab_size: int = 10000,
        n_predictions: int = 4,  # 预测未来4个token
        dropout: float = 0.1
    ):
        super().__init__()
        self.n_predictions = n_predictions
        
        # 每个预测位置有独立的输出头
        self.output_heads = nn.ModuleList([
            nn.Sequential(
                nn.Linear(d_model, d_model),
                nn.GELU(),
                nn.Dropout(dropout),
                nn.Linear(d_model, vocab_size)
            )
            for _ in range(n_predictions)
        ])
        
    def forward(
        self,
        hidden_states: torch.Tensor,
        labels: Optional[torch.Tensor] = None
    ) -> Tuple[torch.Tensor, Optional[torch.Tensor]]:
        """
        Args:
            hidden_states: [batch, seq_len, d_model]
            labels: [batch, seq_len] 真实token ids
        
        Returns:
            logits: List of [batch, seq_len, vocab_size]
            loss: 多token预测损失 (如果提供labels)
        """
        logits_list = []
        
        for i, head in enumerate(self.output_heads):
            # 第i个预测头预测第i+1个token
            logits = head(hidden_states)
            logits_list.append(logits)
        
        loss = None
        if labels is not None:
            total_loss = 0.0
            for i, logits in enumerate(logits_list):
                # 预测第i+1个token
                shift_logits = logits[:, :-i-1, :].contiguous()
                shift_labels = labels[:, i+1:].contiguous()
                
                loss_i = F.cross_entropy(
                    shift_logits.view(-1, logits.size(-1)),
                    shift_labels.view(-1),
                    ignore_index=-100
                )
                total_loss += loss_i
            
            loss = total_loss / self.n_predictions
        
        return logits_list, loss


class DeepSeekV3Block(nn.Module):
    """DeepSeek-V3 Transformer块"""
    
    def __init__(
        self,
        d_model: int = 512,
        n_heads: int = 8,
        d_head: int = 64,
        d_kv_compress: int = 128,
        d_ff: int = 2048,
        n_routed_experts: int = 64,
        n_shared_experts: int = 2,
        top_k: int = 6,
        dropout: float = 0.1
    ):
        super().__init__()
        
        # MLA注意力
        self.attention = MLALayer(
            d_model=d_model,
            n_heads=n_heads,
            d_head=d_head,
            d_kv_compress=d_kv_compress,
            dropout=dropout
        )
        
        # MoE FFN
        self.moe = DeepSeekMoE(
            d_model=d_model,
            d_ff=d_ff,
            n_routed_experts=n_routed_experts,
            n_shared_experts=n_shared_experts,
            top_k=top_k,
            dropout=dropout
        )
        
        # LayerNorm
        self.ln1 = nn.LayerNorm(d_model)
        self.ln2 = nn.LayerNorm(d_model)
        
    def forward(
        self,
        x: torch.Tensor,
        kv_cache: Optional[Tuple[torch.Tensor, torch.Tensor]] = None,
        use_cache: bool = False
    ) -> Tuple[torch.Tensor, Optional[Tuple[torch.Tensor, torch.Tensor]], torch.Tensor]:
        
        # 注意力 + 残差
        attn_out, new_cache = self.attention(
            self.ln1(x), kv_cache, use_cache
        )
        x = x + attn_out
        
        # MoE + 残差
        moe_out, aux_loss = self.moe(self.ln2(x))
        x = x + moe_out
        
        return x, new_cache, aux_loss


class DeepSeekV3Simple(nn.Module):
    """
    DeepSeek-V3 简化模型
    
    整合三大核心创新:
    1. MLA - 高效注意力
    2. DeepSeekMoE - 高效FFN
    3. Multi-Token Prediction - 高效训练
    """
    
    def __init__(
        self,
        vocab_size: int = 10000,
        d_model: int = 512,
        n_layers: int = 6,
        n_heads: int = 8,
        d_head: int = 64,
        d_kv_compress: int = 128,
        d_ff: int = 2048,
        n_routed_experts: int = 32,  # 简化版用更少专家
        n_shared_experts: int = 2,
        top_k: int = 4,
        n_predictions: int = 2,  # 预测未来2个token
        dropout: float = 0.1,
        max_seq_len: int = 512
    ):
        super().__init__()
        self.d_model = d_model
        self.vocab_size = vocab_size
        
        # 词嵌入
        self.token_embedding = nn.Embedding(vocab_size, d_model)
        self.position_embedding = nn.Embedding(max_seq_len, d_model)
        
        # Transformer层
        self.layers = nn.ModuleList([
            DeepSeekV3Block(
                d_model=d_model,
                n_heads=n_heads,
                d_head=d_head,
                d_kv_compress=d_kv_compress,
                d_ff=d_ff,
                n_routed_experts=n_routed_experts,
                n_shared_experts=n_shared_experts,
                top_k=top_k,
                dropout=dropout
            )
            for _ in range(n_layers)
        ])
        
        # 最终LayerNorm
        self.ln_f = nn.LayerNorm(d_model)
        
        # 多Token预测头
        self.mtp_head = MultiTokenPredictionHead(
            d_model=d_model,
            vocab_size=vocab_size,
            n_predictions=n_predictions,
            dropout=dropout
        )
        
    def forward(
        self,
        input_ids: torch.Tensor,
        labels: Optional[torch.Tensor] = None,
        use_cache: bool = False,
        kv_caches: Optional[list] = None
    ) -> dict:
        """
        Args:
            input_ids: [batch, seq_len]
            labels: [batch, seq_len]
            use_cache: 是否使用KV缓存
            kv_caches: 之前的KV缓存列表
        
        Returns:
            dict with logits, loss, aux_loss, new_caches
        """
        batch_size, seq_len = input_ids.shape
        device = input_ids.device
        
        # 位置编码
        positions = torch.arange(seq_len, device=device).unsqueeze(0)
        
        # 嵌入
        x = self.token_embedding(input_ids) + self.position_embedding(positions)
        
        # Transformer层
        new_caches = []
        total_aux_loss = 0.0
        
        for i, layer in enumerate(self.layers):
            kv_cache = kv_caches[i] if kv_caches else None
            x, new_cache, aux_loss = layer(x, kv_cache, use_cache)
            new_caches.append(new_cache)
            total_aux_loss += aux_loss
        
        # 最终LayerNorm
        x = self.ln_f(x)
        
        # 多Token预测
        logits_list, mtp_loss = self.mtp_head(x, labels)
        
        return {
            'logits': logits_list[0],  # 主预测 (下一个token)
            'logits_list': logits_list,  # 所有预测
            'loss': mtp_loss,
            'aux_loss': total_aux_loss / len(self.layers),
            'kv_caches': new_caches if use_cache else None
        }
    
    def generate(
        self,
        input_ids: torch.Tensor,
        max_new_tokens: int = 50,
        temperature: float = 1.0
    ) -> torch.Tensor:
        """自回归生成"""
        self.eval()
        
        with torch.no_grad():
            for _ in range(max_new_tokens):
                outputs = self.forward(input_ids, use_cache=False)
                logits = outputs['logits'][:, -1, :] / temperature
                
                probs = F.softmax(logits, dim=-1)
                next_token = torch.multinomial(probs, num_samples=1)
                
                input_ids = torch.cat([input_ids, next_token], dim=1)
        
        return input_ids


def estimate_kv_cache_savings():
    """估算KV Cache节省"""
    print("\n" + "=" * 70)
    print("MLA KV Cache 内存节省估算")
    print("=" * 70)
    
    # 标准注意力参数
    n_heads = 32
    d_head = 128
    seq_len = 4096
    batch_size = 1
    
    # 标准KV Cache大小
    standard_kv = 2 * n_heads * d_head * seq_len * batch_size * 4  # 4 bytes per float32
    standard_kv_mb = standard_kv / (1024 * 1024)
    
    # MLA压缩后的KV Cache大小
    d_kv_compress = 512
    mla_kv = 2 * d_kv_compress * seq_len * batch_size * 4
    mla_kv_mb = mla_kv / (1024 * 1024)
    
    print(f"\n配置:")
    print(f"  注意力头数: {n_heads}")
    print(f"  每头维度: {d_head}")
    print(f"  序列长度: {seq_len}")
    print(f"  KV压缩维度: {d_kv_compress}")
    
    print(f"\n内存占用:")
    print(f"  标准注意力 KV Cache: {standard_kv_mb:.2f} MB")
    print(f"  MLA KV Cache: {mla_kv_mb:.2f} MB")
    print(f"  节省比例: {standard_kv / mla_kv:.1f}x")
    
    return standard_kv / mla_kv


def estimate_moe_compute_savings():
    """估算MoE计算节省"""
    print("\n" + "=" * 70)
    print("DeepSeekMoE 计算效率估算")
    print("=" * 70)
    
    d_model = 5120
    d_ff = 20480
    n_routed_experts = 64
    top_k = 6
    n_shared_experts = 2
    
    # 稠密模型计算量
    dense_flops = 2 * d_model * d_ff  # 每个token
    
    # MoE计算量 (只激活top_k专家 + 共享专家)
    expert_d_ff = d_ff // 4  # 每个专家更小
    moe_flops = top_k * 2 * d_model * expert_d_ff  # 路由专家
    moe_flops += n_shared_experts * 2 * d_model * (d_ff // 2)  # 共享专家
    
    print(f"\n配置:")
    print(f"  模型维度: {d_model}")
    print(f"  FFN维度: {d_ff}")
    print(f"  路由专家数: {n_routed_experts}")
    print(f"  激活专家数: {top_k}")
    print(f"  共享专家数: {n_shared_experts}")
    
    print(f"\n每个token的计算量:")
    print(f"  稠密模型: {dense_flops / 1e6:.2f} MFLOPs")
    print(f"  MoE模型: {moe_flops / 1e6:.2f} MFLOPs")
    print(f"  计算节省: {(1 - moe_flops/dense_flops)*100:.1f}%")


if __name__ == "__main__":
    print("=" * 70)
    print("DeepSeek-V3 核心思想简化实现")
    print("=" * 70)
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"使用设备: {device}")
    
    # 创建模型
    print("\n" + "-" * 70)
    print("创建模型")
    print("-" * 70)
    
    model = DeepSeekV3Simple(
        vocab_size=1000,
        d_model=256,
        n_layers=4,
        n_heads=8,
        d_head=32,
        d_kv_compress=64,
        d_ff=512,
        n_routed_experts=16,
        n_shared_experts=2,
        top_k=4,
        n_predictions=2
    ).to(device)
    
    total_params = sum(p.numel() for p in model.parameters())
    print(f"模型参数量: {total_params:,}")
    
    # 测试前向传播
    print("\n" + "-" * 70)
    print("测试前向传播")
    print("-" * 70)
    
    batch_size = 2
    seq_len = 32
    input_ids = torch.randint(0, 1000, (batch_size, seq_len)).to(device)
    labels = torch.randint(0, 1000, (batch_size, seq_len)).to(device)
    
    outputs = model(input_ids, labels=labels)
    
    print(f"输入形状: {input_ids.shape}")
    print(f"主预测logits: {outputs['logits'].shape}")
    print(f"预测头数量: {len(outputs['logits_list'])}")
    print(f"多Token预测损失: {outputs['loss'].item():.4f}")
    print(f"负载均衡损失: {outputs['aux_loss'].item():.6f}")
    
    # 测试生成
    print("\n" + "-" * 70)
    print("测试生成")
    print("-" * 70)
    
    test_input = torch.randint(0, 1000, (1, 10)).to(device)
    generated = model.generate(test_input, max_new_tokens=20)
    print(f"输入长度: 10")
    print(f"生成长度: {generated.shape[1]}")
    
    # 估算效率提升
    estimate_kv_cache_savings()
    estimate_moe_compute_savings()
    
    print("\n" + "=" * 70)
    print("✅ DeepSeek-V3 核心思想演示完成!")
    print("=" * 70)
    print("\n核心创新总结:")
    print("  1. MLA - KV Cache压缩，节省推理内存")
    print("  2. DeepSeekMoE - 稀疏激活，节省计算量")
    print("  3. Multi-Token Prediction - 同时预测多个token，提升训练效率")
    print("\n注意: 这是高度简化的演示版本")
    print("      实际DeepSeek-V3有671B参数，使用更复杂的架构")
