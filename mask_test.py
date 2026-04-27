import torch
import torch.nn as nn
import torch.nn.functional as F
import math

# 简化的掩码测试
if __name__ == "__main__":
    print("测试掩码生成功能...")
    
    # 创建测试输入（包含填充0）
    batch_size = 2
    src_seq_len = 5
    tgt_seq_len = 4
    
    # 源序列：包含填充0
    src = torch.tensor([[1, 2, 3, 0, 0], [4, 5, 0, 0, 0]], dtype=torch.long)
    # 目标序列：包含填充0
    tgt = torch.tensor([[6, 7, 8, 0], [9, 10, 0, 0]], dtype=torch.long)
    
    print("\n输入序列:")
    print("src:", src)
    print("tgt:", tgt)
    
    # 生成源序列掩码
    src_mask = (src != 0).unsqueeze(1).unsqueeze(2)
    src_mask = src_mask.expand(-1, 1, src_seq_len, src_seq_len)
    print("\n源序列掩码 (src_mask):")
    print(src_mask)
    print("形状:", src_mask.shape)
    
    # 生成编码器-解码器注意力掩码
    enc_dec_mask = (src != 0).unsqueeze(1).unsqueeze(2)
    enc_dec_mask = enc_dec_mask.expand(-1, 1, tgt_seq_len, src_seq_len)
    print("\n编码器-解码器掩码 (enc_dec_mask):")
    print(enc_dec_mask)
    print("形状:", enc_dec_mask.shape)
    
    # 生成目标序列前瞻掩码
    tgt_padding_mask = (tgt != 0).unsqueeze(1).unsqueeze(3)
    tgt_padding_mask = tgt_padding_mask.expand(-1, 1, tgt_seq_len, tgt_seq_len)
    look_ahead_mask = torch.tril(torch.ones(tgt_seq_len, tgt_seq_len)).bool()
    tgt_mask = tgt_padding_mask & look_ahead_mask
    print("\n目标序列掩码 (tgt_mask):")
    print(tgt_mask)
    print("形状:", tgt_mask.shape)
    
    # 测试掩码在注意力计算中的应用
    print("\n测试掩码在注意力计算中的应用...")
    
    # 创建随机注意力分数
    n_heads = 2
    d_k = 8
    
    # 模拟多头注意力的Q和K
    Q = torch.randn(batch_size, n_heads, tgt_seq_len, d_k)
    K = torch.randn(batch_size, n_heads, src_seq_len, d_k)
    
    # 计算注意力分数
    attn_scores = torch.matmul(Q, K.transpose(-2, -1)) / math.sqrt(d_k)
    print("原始注意力分数形状:", attn_scores.shape)
    
    # 应用编码器-解码器掩码
    # 扩展掩码以匹配多头注意力的形状
    expanded_mask = enc_dec_mask.repeat(1, n_heads, 1, 1)
    masked_attn_scores = attn_scores.masked_fill(expanded_mask == 0, -1e10)
    
    # 计算注意力权重
    attn_weights = F.softmax(masked_attn_scores, dim=-1)
    print("\n应用掩码后的注意力权重:")
    print(attn_weights)
    print("形状:", attn_weights.shape)
    
    print("\n掩码功能测试成功!")
