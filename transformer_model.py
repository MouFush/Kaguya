import torch
import torch.nn as nn
import torch.nn.functional as F
import math

class PositionalEncoding(nn.Module):
    def __init__(self, d_model, max_seq_len=5000):
        super(PositionalEncoding, self).__init__()
        # 创建位置编码矩阵
        pe = torch.zeros(max_seq_len, d_model)
        # 创建位置索引
        position = torch.arange(0, max_seq_len, dtype=torch.float).unsqueeze(1)
        # 计算位置编码的分母
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        # 计算正弦和余弦位置编码
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        # 添加批次维度
        pe = pe.unsqueeze(0)
        # 注册为缓冲区，不参与梯度计算
        self.register_buffer('pe', pe)
    
    def forward(self, x):
        # x: [batch_size, seq_len, d_model]
        seq_len = x.size(1)
        # 添加位置编码到输入嵌入
        x = x + self.pe[:, :seq_len, :]
        return x

class MultiHeadAttention(nn.Module):
    def __init__(self, d_model, n_heads):
        super(MultiHeadAttention, self).__init__()
        assert d_model % n_heads == 0, "d_model must be divisible by n_heads"
        
        self.d_model = d_model
        self.n_heads = n_heads
        self.d_k = d_model // n_heads
        
        # 线性变换层
        self.W_q = nn.Linear(d_model, d_model)
        self.W_k = nn.Linear(d_model, d_model)
        self.W_v = nn.Linear(d_model, d_model)
        self.W_o = nn.Linear(d_model, d_model)
    
    def scaled_dot_product_attention(self, Q, K, V, mask=None):
        # Q: [batch_size, n_heads, seq_len_q, d_k]
        # K: [batch_size, n_heads, seq_len_k, d_k]
        # V: [batch_size, n_heads, seq_len_v, d_k]
        # mask: [batch_size, 1, seq_len_q, seq_len_k]
        
        # 计算注意力分数
        attn_scores = torch.matmul(Q, K.transpose(-2, -1)) / math.sqrt(self.d_k)
        
        # 应用掩码
        if mask is not None:
            attn_scores = attn_scores.masked_fill(mask == 0, -1e10)
        
        # 计算注意力权重
        attn_weights = F.softmax(attn_scores, dim=-1)
        
        # 计算上下文向量
        output = torch.matmul(attn_weights, V)
        
        return output, attn_weights
    
    def forward(self, Q, K, V, mask=None):
        # Q: [batch_size, seq_len_q, d_model]
        # K: [batch_size, seq_len_k, d_model]
        # V: [batch_size, seq_len_v, d_model]
        # mask: [batch_size, seq_len_q, seq_len_k]
        
        batch_size = Q.size(0)
        seq_len_q = Q.size(1)
        
        # 线性变换并分桶
        Q = self.W_q(Q).view(batch_size, seq_len_q, self.n_heads, self.d_k).transpose(1, 2)
        K = self.W_k(K).view(batch_size, K.size(1), self.n_heads, self.d_k).transpose(1, 2)
        V = self.W_v(V).view(batch_size, V.size(1), self.n_heads, self.d_k).transpose(1, 2)
        
        # 应用掩码
        if mask is not None:
            mask = mask.unsqueeze(1)  # [batch_size, 1, seq_len_q, seq_len_k]
        
        # 计算多头注意力
        attn_output, attn_weights = self.scaled_dot_product_attention(Q, K, V, mask)
        
        # 拼接多头输出
        attn_output = attn_output.transpose(1, 2).contiguous().view(batch_size, seq_len_q, self.d_model)
        
        # 最终线性变换
        output = self.W_o(attn_output)
        
        return output, attn_weights

class FeedForwardNetwork(nn.Module):
    def __init__(self, d_model, d_ff):
        super(FeedForwardNetwork, self).__init__()
        self.fc1 = nn.Linear(d_model, d_ff)
        self.fc2 = nn.Linear(d_ff, d_model)
        self.dropout = nn.Dropout(0.1)
    
    def forward(self, x):
        # x: [batch_size, seq_len, d_model]
        x = self.dropout(F.relu(self.fc1(x)))
        x = self.fc2(x)
        return x

class EncoderLayer(nn.Module):
    def __init__(self, d_model, n_heads, d_ff, dropout=0.1):
        super(EncoderLayer, self).__init__()
        # 多头注意力层
        self.mha = MultiHeadAttention(d_model, n_heads)
        # 前馈网络层
        self.ffn = FeedForwardNetwork(d_model, d_ff)
        # 层归一化
        self.layernorm1 = nn.LayerNorm(d_model)
        self.layernorm2 = nn.LayerNorm(d_model)
        #  dropout层
        self.dropout1 = nn.Dropout(dropout)
        self.dropout2 = nn.Dropout(dropout)
    
    def forward(self, x, mask):
        # x: [batch_size, seq_len, d_model]
        # mask: [batch_size, seq_len, seq_len]
        
        # 多头注意力子层
        attn_output, _ = self.mha(x, x, x, mask)
        attn_output = self.dropout1(attn_output)
        x = self.layernorm1(x + attn_output)
        
        # 前馈网络子层
        ffn_output = self.ffn(x)
        ffn_output = self.dropout2(ffn_output)
        x = self.layernorm2(x + ffn_output)
        
        return x

class DecoderLayer(nn.Module):
    def __init__(self, d_model, n_heads, d_ff, dropout=0.1):
        super(DecoderLayer, self).__init__()
        # 掩码多头注意力层
        self.masked_mha = MultiHeadAttention(d_model, n_heads)
        # 编码器-解码器多头注意力层
        self.encoder_decoder_mha = MultiHeadAttention(d_model, n_heads)
        # 前馈网络层
        self.ffn = FeedForwardNetwork(d_model, d_ff)
        # 层归一化
        self.layernorm1 = nn.LayerNorm(d_model)
        self.layernorm2 = nn.LayerNorm(d_model)
        self.layernorm3 = nn.LayerNorm(d_model)
        # dropout层
        self.dropout1 = nn.Dropout(dropout)
        self.dropout2 = nn.Dropout(dropout)
        self.dropout3 = nn.Dropout(dropout)
    
    def forward(self, x, enc_output, look_ahead_mask, padding_mask):
        # x: [batch_size, seq_len, d_model]
        # enc_output: [batch_size, seq_len, d_model]
        # look_ahead_mask: [batch_size, seq_len, seq_len]
        # padding_mask: [batch_size, seq_len, seq_len]
        
        # 掩码多头注意力子层
        attn_output, _ = self.masked_mha(x, x, x, look_ahead_mask)
        attn_output = self.dropout1(attn_output)
        x = self.layernorm1(x + attn_output)
        
        # 编码器-解码器多头注意力子层
        attn_output, _ = self.encoder_decoder_mha(x, enc_output, enc_output, padding_mask)
        attn_output = self.dropout2(attn_output)
        x = self.layernorm2(x + attn_output)
        
        # 前馈网络子层
        ffn_output = self.ffn(x)
        ffn_output = self.dropout3(ffn_output)
        x = self.layernorm3(x + ffn_output)
        
        return x

class Transformer(nn.Module):
    def __init__(self, src_vocab_size, tgt_vocab_size, d_model=512, n_heads=8, n_layers=6, d_ff=2048, max_seq_len=5000, dropout=0.1):
        super(Transformer, self).__init__()
        
        # 编码器嵌入层
        self.encoder_embedding = nn.Embedding(src_vocab_size, d_model)
        # 解码器嵌入层
        self.decoder_embedding = nn.Embedding(tgt_vocab_size, d_model)
        # 位置编码
        self.positional_encoding = PositionalEncoding(d_model, max_seq_len)
        
        # 编码器层
        self.encoder_layers = nn.ModuleList([EncoderLayer(d_model, n_heads, d_ff, dropout) for _ in range(n_layers)])
        # 解码器层
        self.decoder_layers = nn.ModuleList([DecoderLayer(d_model, n_heads, d_ff, dropout) for _ in range(n_layers)])
        
        # 最终线性层
        self.fc_out = nn.Linear(d_model, tgt_vocab_size)
        # dropout层
        self.dropout = nn.Dropout(dropout)
    
    def generate_mask(self, src, tgt):
        # src: [batch_size, src_seq_len]
        # tgt: [batch_size, tgt_seq_len]
        
        batch_size = src.size(0)
        src_seq_len = src.size(1)
        tgt_seq_len = tgt.size(1)
        
        # 源序列掩码
        src_mask = (src != 0).unsqueeze(1).unsqueeze(2)  # [batch_size, 1, 1, src_seq_len]
        src_mask = src_mask.expand(batch_size, 1, src_seq_len, src_seq_len)  # [batch_size, 1, src_seq_len, src_seq_len]
        
        # 目标序列掩码
        tgt_padding_mask = (tgt != 0).unsqueeze(1).unsqueeze(3)  # [batch_size, 1, tgt_seq_len, 1]
        tgt_padding_mask = tgt_padding_mask.expand(batch_size, 1, tgt_seq_len, tgt_seq_len)  # [batch_size, 1, tgt_seq_len, tgt_seq_len]
        
        # 前瞻掩码
        look_ahead_mask = torch.triu(torch.ones(tgt_seq_len, tgt_seq_len), diagonal=1).bool()
        look_ahead_mask = look_ahead_mask.to(tgt.device)
        tgt_mask = tgt_padding_mask & ~look_ahead_mask  # [batch_size, 1, tgt_seq_len, tgt_seq_len]
        
        return src_mask, tgt_mask
    
    def forward(self, src, tgt):
        # src: [batch_size, src_seq_len]
        # tgt: [batch_size, tgt_seq_len]
        
        # 生成掩码
        src_mask, tgt_mask = self.generate_mask(src, tgt)
        
        # 编码器前向传播
        enc_emb = self.dropout(self.positional_encoding(self.encoder_embedding(src)))
        enc_output = enc_emb
        for enc_layer in self.encoder_layers:
            enc_output = enc_layer(enc_output, src_mask)
        
        # 解码器前向传播
        dec_emb = self.dropout(self.positional_encoding(self.decoder_embedding(tgt)))
        dec_output = dec_emb
        for dec_layer in self.decoder_layers:
            dec_output = dec_layer(dec_output, enc_output, tgt_mask, src_mask)
        
        # 最终输出
        output = self.fc_out(dec_output)
        
        return output

# 测试代码
if __name__ == "__main__":
    # 超参数
    src_vocab_size = 10000
    tgt_vocab_size = 10000
    d_model = 512
    n_heads = 8
    n_layers = 6
    d_ff = 2048
    max_seq_len = 100
    dropout = 0.1
    
    # 创建模型
    model = Transformer(src_vocab_size, tgt_vocab_size, d_model, n_heads, n_layers, d_ff, max_seq_len, dropout)
    print("Transformer模型结构:")
    print(model)
    
    # 计算模型参数量
    total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"\n模型参数量: {total_params:,}")
    
    # 测试前向传播
    batch_size = 32
    src_seq_len = 50
    tgt_seq_len = 40
    
    # 生成随机输入
    src = torch.randint(1, src_vocab_size, (batch_size, src_seq_len))
    tgt = torch.randint(1, tgt_vocab_size, (batch_size, tgt_seq_len))
    
    # 前向传播
    output = model(src, tgt)
    print(f"\n输入形状:")
    print(f"src: {src.shape}")
    print(f"tgt: {tgt.shape}")
    print(f"\n输出形状:")
    print(f"output: {output.shape}")
    
    print("\nTransformer模型测试成功!")
