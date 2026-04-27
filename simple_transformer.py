import torch
import torch.nn as nn
import torch.nn.functional as F
import math

class PositionalEncoding(nn.Module):
    def __init__(self, d_model, max_seq_len=100):
        super(PositionalEncoding, self).__init__()
        pe = torch.zeros(max_seq_len, d_model)
        position = torch.arange(0, max_seq_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)
        self.register_buffer('pe', pe)
    
    def forward(self, x):
        seq_len = x.size(1)
        x = x + self.pe[:, :seq_len, :]
        return x

class MultiHeadAttention(nn.Module):
    def __init__(self, d_model, n_heads):
        super(MultiHeadAttention, self).__init__()
        assert d_model % n_heads == 0, "d_model must be divisible by n_heads"
        
        self.d_model = d_model
        self.n_heads = n_heads
        self.d_k = d_model // n_heads
        
        self.W_q = nn.Linear(d_model, d_model)
        self.W_k = nn.Linear(d_model, d_model)
        self.W_v = nn.Linear(d_model, d_model)
        self.W_o = nn.Linear(d_model, d_model)
    
    def scaled_dot_product_attention(self, Q, K, V, mask=None):
        # Q: [batch_size, n_heads, seq_len_q, d_k]
        # K: [batch_size, n_heads, seq_len_k, d_k]
        # V: [batch_size, n_heads, seq_len_v, d_k]
        attn_scores = torch.matmul(Q, K.transpose(-2, -1)) / math.sqrt(self.d_k)
        if mask is not None:
            # 确保mask形状与attn_scores匹配
            mask = mask.expand_as(attn_scores)
            attn_scores = attn_scores.masked_fill(mask == 0, -1e10)
        attn_weights = F.softmax(attn_scores, dim=-1)
        output = torch.matmul(attn_weights, V)
        return output, attn_weights
    
    def forward(self, Q, K, V, mask=None):
        batch_size = Q.size(0)
        seq_len_q = Q.size(1)
        
        Q = self.W_q(Q).view(batch_size, seq_len_q, self.n_heads, self.d_k).transpose(1, 2)
        K = self.W_k(K).view(batch_size, K.size(1), self.n_heads, self.d_k).transpose(1, 2)
        V = self.W_v(V).view(batch_size, V.size(1), self.n_heads, self.d_k).transpose(1, 2)
        
        # mask已经是[batch_size, 1, seq_len_q, seq_len_k]形状，不需要再unsqueeze
        attn_output, attn_weights = self.scaled_dot_product_attention(Q, K, V, mask)
        attn_output = attn_output.transpose(1, 2).contiguous().view(batch_size, seq_len_q, self.d_model)
        output = self.W_o(attn_output)
        
        return output, attn_weights

class FeedForwardNetwork(nn.Module):
    def __init__(self, d_model, d_ff):
        super(FeedForwardNetwork, self).__init__()
        self.fc1 = nn.Linear(d_model, d_ff)
        self.fc2 = nn.Linear(d_ff, d_model)
        self.dropout = nn.Dropout(0.1)
    
    def forward(self, x):
        x = self.dropout(F.relu(self.fc1(x)))
        x = self.fc2(x)
        return x

class EncoderLayer(nn.Module):
    def __init__(self, d_model, n_heads, d_ff, dropout=0.1):
        super(EncoderLayer, self).__init__()
        self.mha = MultiHeadAttention(d_model, n_heads)
        self.ffn = FeedForwardNetwork(d_model, d_ff)
        self.layernorm1 = nn.LayerNorm(d_model)
        self.layernorm2 = nn.LayerNorm(d_model)
        self.dropout1 = nn.Dropout(dropout)
        self.dropout2 = nn.Dropout(dropout)
    
    def forward(self, x, mask):
        attn_output, _ = self.mha(x, x, x, mask)
        attn_output = self.dropout1(attn_output)
        x = self.layernorm1(x + attn_output)
        
        ffn_output = self.ffn(x)
        ffn_output = self.dropout2(ffn_output)
        x = self.layernorm2(x + ffn_output)
        
        return x

class DecoderLayer(nn.Module):
    def __init__(self, d_model, n_heads, d_ff, dropout=0.1):
        super(DecoderLayer, self).__init__()
        self.masked_mha = MultiHeadAttention(d_model, n_heads)
        self.encoder_decoder_mha = MultiHeadAttention(d_model, n_heads)
        self.ffn = FeedForwardNetwork(d_model, d_ff)
        self.layernorm1 = nn.LayerNorm(d_model)
        self.layernorm2 = nn.LayerNorm(d_model)
        self.layernorm3 = nn.LayerNorm(d_model)
        self.dropout1 = nn.Dropout(dropout)
        self.dropout2 = nn.Dropout(dropout)
        self.dropout3 = nn.Dropout(dropout)
    
    def forward(self, x, enc_output, look_ahead_mask, padding_mask):
        attn_output, _ = self.masked_mha(x, x, x, look_ahead_mask)
        attn_output = self.dropout1(attn_output)
        x = self.layernorm1(x + attn_output)
        
        attn_output, _ = self.encoder_decoder_mha(x, enc_output, enc_output, padding_mask)
        attn_output = self.dropout2(attn_output)
        x = self.layernorm2(x + attn_output)
        
        ffn_output = self.ffn(x)
        ffn_output = self.dropout3(ffn_output)
        x = self.layernorm3(x + ffn_output)
        
        return x

class Transformer(nn.Module):
    def __init__(self, src_vocab_size, tgt_vocab_size, d_model=64, n_heads=2, n_layers=2, d_ff=128, max_seq_len=100, dropout=0.1):
        super(Transformer, self).__init__()
        
        self.encoder_embedding = nn.Embedding(src_vocab_size, d_model)
        self.decoder_embedding = nn.Embedding(tgt_vocab_size, d_model)
        self.positional_encoding = PositionalEncoding(d_model, max_seq_len)
        
        self.encoder_layers = nn.ModuleList([EncoderLayer(d_model, n_heads, d_ff, dropout) for _ in range(n_layers)])
        self.decoder_layers = nn.ModuleList([DecoderLayer(d_model, n_heads, d_ff, dropout) for _ in range(n_layers)])
        
        self.fc_out = nn.Linear(d_model, tgt_vocab_size)
        self.dropout = nn.Dropout(dropout)
    
    def generate_mask(self, src, tgt):
        batch_size = src.size(0)
        src_seq_len = src.size(1)
        tgt_seq_len = tgt.size(1)
        
        src_mask = (src != 0).unsqueeze(1).unsqueeze(2)
        src_mask = src_mask.expand(batch_size, 1, src_seq_len, src_seq_len)
        
        tgt_padding_mask = (tgt != 0).unsqueeze(1).unsqueeze(3)
        tgt_padding_mask = tgt_padding_mask.expand(batch_size, 1, tgt_seq_len, tgt_seq_len)
        
        look_ahead_mask = torch.triu(torch.ones(tgt_seq_len, tgt_seq_len), diagonal=1).bool()
        look_ahead_mask = look_ahead_mask.to(tgt.device)
        tgt_mask = tgt_padding_mask & ~look_ahead_mask
        
        return src_mask, tgt_mask
    
    def forward(self, src, tgt):
        src_mask, tgt_mask = self.generate_mask(src, tgt)
        
        enc_emb = self.dropout(self.positional_encoding(self.encoder_embedding(src)))
        enc_output = enc_emb
        for enc_layer in self.encoder_layers:
            enc_output = enc_layer(enc_output, src_mask)
        
        dec_emb = self.dropout(self.positional_encoding(self.decoder_embedding(tgt)))
        dec_output = dec_emb
        for dec_layer in self.decoder_layers:
            dec_output = dec_layer(dec_output, enc_output, tgt_mask, src_mask)
        
        output = self.fc_out(dec_output)
        
        return output

# 测试代码
if __name__ == "__main__":
    # 简化版超参数
    src_vocab_size = 1000
    tgt_vocab_size = 1000
    d_model = 64
    n_heads = 2
    n_layers = 2
    d_ff = 128
    max_seq_len = 50
    dropout = 0.1
    
    # 创建模型
    model = Transformer(src_vocab_size, tgt_vocab_size, d_model, n_heads, n_layers, d_ff, max_seq_len, dropout)
    print("简化版Transformer模型结构:")
    print(model)
    
    # 计算模型参数量
    total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"\n模型参数量: {total_params:,}")
    
    # 测试前向传播
    batch_size = 8
    src_seq_len = 20
    tgt_seq_len = 15
    
    # 生成随机输入
    src = torch.randint(1, src_vocab_size, (batch_size, src_seq_len))
    tgt = torch.randint(1, tgt_vocab_size, (batch_size, tgt_seq_len))
    
    # 前向传播
    print("\n开始前向传播测试...")
    output = model(src, tgt)
    print(f"\n输入形状:")
    print(f"src: {src.shape}")
    print(f"tgt: {tgt.shape}")
    print(f"\n输出形状:")
    print(f"output: {output.shape}")
    
    print("\n简化版Transformer模型测试成功!")
