"""
DeepSeek-V3 增强版对话系统

整合DeepSeek-V3三大核心技术:
1. MLA (Multi-Head Latent Attention) - 高效注意力
2. DeepSeekMoE - 混合专家FFN
3. Multi-Token Prediction - 多Token预测训练
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import math
import re
import random
from typing import List, Dict, Tuple, Optional
from collections import defaultdict


class SimpleTokenizer:
    """增强版分词器"""
    
    def __init__(self):
        self.word2idx = {'<pad>': 0, '<sos>': 1, '<eos>': 2, '<unk>': 3}
        self.idx2word = {v: k for k, v in self.word2idx.items()}
        self.vocab_size = 4
        
    def build_vocab(self, texts: List[str], min_freq: int = 1):
        word_freq = defaultdict(int)
        for text in texts:
            words = self.tokenize(text)
            for word in words:
                word_freq[word] += 1
        
        for word, freq in word_freq.items():
            if freq >= min_freq and word not in self.word2idx:
                self.word2idx[word] = self.vocab_size
                self.idx2word[self.vocab_size] = word
                self.vocab_size += 1
    
    def tokenize(self, text: str) -> List[str]:
        text = text.lower().strip()
        text = re.sub(r'[^\w\s\u4e00-\u9fff]', '', text)
        return text.split()
    
    def encode(self, text: str, max_len: int = 64) -> List[int]:
        words = self.tokenize(text)
        ids = [self.word2idx.get(w, self.word2idx['<unk>']) for w in words]
        ids = ids[:max_len-2]
        return [self.word2idx['<sos>']] + ids + [self.word2idx['<eos>']]
    
    def decode(self, ids: List[int]) -> str:
        words = []
        for idx in ids:
            if idx == self.word2idx['<eos>']:
                break
            if idx not in [self.word2idx['<pad>'], self.word2idx['<sos>']]:
                words.append(self.idx2word.get(idx, '<unk>'))
        return ' '.join(words)


class MLALayer(nn.Module):
    """
    Multi-Head Latent Attention (MLA)
    DeepSeek-V3核心创新: KV Cache压缩
    """
    
    def __init__(self, d_model: int, n_heads: int, d_head: int, 
                 d_kv_compress: int, dropout: float = 0.1):
        super().__init__()
        self.d_model = d_model
        self.n_heads = n_heads
        self.d_head = d_head
        self.d_kv_compress = d_kv_compress
        
        self.wq = nn.Linear(d_model, n_heads * d_head, bias=False)
        self.wkv_compress = nn.Linear(d_model, d_kv_compress, bias=False)
        self.wk_up = nn.Linear(d_kv_compress, n_heads * d_head, bias=False)
        self.wv_up = nn.Linear(d_kv_compress, n_heads * d_head, bias=False)
        self.wo = nn.Linear(n_heads * d_head, d_model, bias=False)
        
        self.dropout = nn.Dropout(dropout)
        
    def forward(self, x: torch.Tensor, mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        batch_size, seq_len, _ = x.shape
        
        q = self.wq(x).view(batch_size, seq_len, self.n_heads, self.d_head).transpose(1, 2)
        
        kv_compressed = self.wkv_compress(x)
        k = self.wk_up(kv_compressed).view(batch_size, seq_len, self.n_heads, self.d_head).transpose(1, 2)
        v = self.wv_up(kv_compressed).view(batch_size, seq_len, self.n_heads, self.d_head).transpose(1, 2)
        
        scale = 1.0 / math.sqrt(self.d_head)
        attn_weights = torch.matmul(q, k.transpose(-2, -1)) * scale
        
        if mask is not None:
            attn_weights = attn_weights.masked_fill(mask == 0, float('-inf'))
        
        attn_weights = F.softmax(attn_weights, dim=-1)
        attn_weights = self.dropout(attn_weights)
        
        attn_output = torch.matmul(attn_weights, v)
        attn_output = attn_output.transpose(1, 2).contiguous().view(batch_size, seq_len, -1)
        
        return self.wo(attn_output)


class Expert(nn.Module):
    """单个专家网络"""
    def __init__(self, d_model: int, d_ff: int, dropout: float = 0.1):
        super().__init__()
        self.w1 = nn.Linear(d_model, d_ff, bias=False)
        self.w2 = nn.Linear(d_ff, d_model, bias=False)
        self.dropout = nn.Dropout(dropout)
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.dropout(self.w2(F.silu(self.w1(x))))


class DeepSeekMoE(nn.Module):
    """
    DeepSeekMoE - 混合专家FFN
    核心创新: 细粒度专家 + 共享专家
    """
    
    def __init__(self, d_model: int, d_ff: int, n_routed_experts: int = 16,
                 n_shared_experts: int = 2, top_k: int = 4, dropout: float = 0.1):
        super().__init__()
        self.d_model = d_model
        self.n_routed_experts = n_routed_experts
        self.n_shared_experts = n_shared_experts
        self.top_k = top_k
        
        self.routed_experts = nn.ModuleList([
            Expert(d_model, d_ff // 4, dropout)
            for _ in range(n_routed_experts)
        ])
        
        self.shared_experts = nn.ModuleList([
            Expert(d_model, d_ff // 2, dropout)
            for _ in range(n_shared_experts)
        ])
        
        self.gate = nn.Linear(d_model, n_routed_experts, bias=False)
        
    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        batch_size, seq_len, d_model = x.shape
        
        gate_logits = self.gate(x)
        top_k_weights, top_k_indices = torch.topk(gate_logits, self.top_k, dim=-1)
        top_k_weights = F.softmax(top_k_weights, dim=-1)
        
        output = torch.zeros_like(x)
        x_flat = x.view(-1, d_model)
        top_k_weights_flat = top_k_weights.view(-1, self.top_k)
        top_k_indices_flat = top_k_indices.view(-1, self.top_k)
        
        for k in range(self.top_k):
            expert_indices = top_k_indices_flat[:, k]
            expert_weights = top_k_weights_flat[:, k:k+1]
            
            for expert_idx in range(self.n_routed_experts):
                mask = (expert_indices == expert_idx)
                if mask.any():
                    expert_input = x_flat[mask]
                    expert_output = self.routed_experts[expert_idx](expert_input)
                    output_flat = output.view(-1, d_model)
                    output_flat[mask] += expert_weights[mask] * expert_output
        
        for shared_expert in self.shared_experts:
            output = output + shared_expert(x) / self.n_shared_experts
        
        expert_mask = F.one_hot(top_k_indices, self.n_routed_experts).float()
        expert_freq = expert_mask.mean(dim=[0, 1, 2])
        router_probs = F.softmax(gate_logits, dim=-1).mean(dim=[0, 1])
        aux_loss = (expert_freq * router_probs).sum() * self.n_routed_experts * 0.01
        
        return output, aux_loss


class DeepSeekBlock(nn.Module):
    """DeepSeek-V3 Transformer块"""
    
    def __init__(self, d_model: int, n_heads: int, d_head: int, d_kv_compress: int,
                 d_ff: int, n_routed_experts: int, n_shared_experts: int, 
                 top_k: int, dropout: float = 0.1):
        super().__init__()
        
        self.attention = MLALayer(d_model, n_heads, d_head, d_kv_compress, dropout)
        self.moe = DeepSeekMoE(d_model, d_ff, n_routed_experts, n_shared_experts, top_k, dropout)
        self.ln1 = nn.LayerNorm(d_model)
        self.ln2 = nn.LayerNorm(d_model)
        
    def forward(self, x: torch.Tensor, mask: Optional[torch.Tensor] = None) -> Tuple[torch.Tensor, torch.Tensor]:
        attn_out = self.attention(self.ln1(x), mask)
        x = x + attn_out
        
        moe_out, aux_loss = self.moe(self.ln2(x))
        x = x + moe_out
        
        return x, aux_loss


class MultiTokenPredictionHead(nn.Module):
    """多Token预测头"""
    
    def __init__(self, d_model: int, vocab_size: int, n_predictions: int = 2, dropout: float = 0.1):
        super().__init__()
        self.n_predictions = n_predictions
        
        self.output_heads = nn.ModuleList([
            nn.Sequential(
                nn.Linear(d_model, d_model * 2),
                nn.GELU(),
                nn.Dropout(dropout),
                nn.Linear(d_model * 2, vocab_size)
            )
            for _ in range(n_predictions)
        ])
        
    def forward(self, hidden_states: torch.Tensor, labels: Optional[torch.Tensor] = None) -> Tuple[List[torch.Tensor], Optional[torch.Tensor]]:
        logits_list = [head(hidden_states) for head in self.output_heads]
        
        loss = None
        if labels is not None:
            total_loss = 0.0
            for i, logits in enumerate(logits_list):
                if i + 1 < labels.shape[1]:
                    shift_logits = logits[:, :-(i+1), :].contiguous()
                    shift_labels = labels[:, (i+1):].contiguous()
                    loss_i = F.cross_entropy(
                        shift_logits.view(-1, logits.size(-1)),
                        shift_labels.view(-1),
                        ignore_index=0
                    )
                    total_loss += loss_i
            loss = total_loss / self.n_predictions
        
        return logits_list, loss


class DeepSeekChatModel(nn.Module):
    """
    DeepSeek-V3 增强版对话模型
    整合MLA + MoE + Multi-Token Prediction
    """
    
    def __init__(self, vocab_size: int, d_model: int = 256, n_layers: int = 4,
                 n_heads: int = 8, d_head: int = 32, d_kv_compress: int = 64,
                 d_ff: int = 512, n_routed_experts: int = 16, n_shared_experts: int = 2,
                 top_k: int = 4, n_predictions: int = 2, dropout: float = 0.1,
                 max_seq_len: int = 256):
        super().__init__()
        
        self.d_model = d_model
        self.vocab_size = vocab_size
        
        self.token_embedding = nn.Embedding(vocab_size, d_model)
        self.position_embedding = nn.Embedding(max_seq_len, d_model)
        
        self.layers = nn.ModuleList([
            DeepSeekBlock(d_model, n_heads, d_head, d_kv_compress, d_ff,
                         n_routed_experts, n_shared_experts, top_k, dropout)
            for _ in range(n_layers)
        ])
        
        self.ln_f = nn.LayerNorm(d_model)
        self.mtp_head = MultiTokenPredictionHead(d_model, vocab_size, n_predictions, dropout)
        
    def forward(self, input_ids: torch.Tensor, labels: Optional[torch.Tensor] = None) -> Dict:
        batch_size, seq_len = input_ids.shape
        device = input_ids.device
        
        positions = torch.arange(seq_len, device=device).unsqueeze(0)
        x = self.token_embedding(input_ids) + self.position_embedding(positions)
        
        causal_mask = torch.tril(torch.ones(seq_len, seq_len, device=device)).unsqueeze(0).unsqueeze(0)
        
        total_aux_loss = 0.0
        for layer in self.layers:
            x, aux_loss = layer(x, causal_mask)
            total_aux_loss += aux_loss
        
        x = self.ln_f(x)
        
        logits_list, mtp_loss = self.mtp_head(x, labels)
        
        return {
            'logits': logits_list[0],
            'logits_list': logits_list,
            'loss': mtp_loss,
            'aux_loss': total_aux_loss / len(self.layers)
        }
    
    def generate(self, input_ids: torch.Tensor, max_len: int = 50, 
                 temperature: float = 0.8, top_p: float = 0.9) -> torch.Tensor:
        """增强版生成: 支持温度采样和nucleus采样"""
        self.eval()
        device = input_ids.device
        
        with torch.no_grad():
            for _ in range(max_len):
                outputs = self.forward(input_ids)
                logits = outputs['logits'][:, -1, :] / temperature
                
                # Nucleus (top-p) 采样
                sorted_logits, sorted_indices = torch.sort(logits, descending=True)
                cumulative_probs = torch.cumsum(F.softmax(sorted_logits, dim=-1), dim=-1)
                
                sorted_indices_to_remove = cumulative_probs > top_p
                sorted_indices_to_remove[..., 1:] = sorted_indices_to_remove[..., :-1].clone()
                sorted_indices_to_remove[..., 0] = 0
                
                indices_to_remove = sorted_indices_to_remove.scatter(1, sorted_indices, sorted_indices_to_remove)
                logits = logits.masked_fill(indices_to_remove, float('-inf'))
                
                probs = F.softmax(logits, dim=-1)
                next_token = torch.multinomial(probs, num_samples=1)
                
                input_ids = torch.cat([input_ids, next_token], dim=1)
                
                if (next_token == 2).all():
                    break
        
        return input_ids


class EnhancedRuleResponder:
    """增强版规则回复器"""
    
    def __init__(self):
        self.patterns = self._build_patterns()
        self.context_memory: Dict[str, List[str]] = defaultdict(list)
        self.default_responses = [
            "这是一个有趣的话题，能详细说说吗？",
            "我在认真思考你说的话...",
            "你能换个方式解释一下吗？",
            "让我想想该怎么回答...",
            "这个问题很有深度呢！",
        ]
        
    def _build_patterns(self) -> List[Tuple[str, List[str]]]:
        return [
            (r'你好|您好|hi|hello|嗨',
             ['你好！很高兴见到你！今天想聊点什么？', 
              '嗨！欢迎来找我聊天！', 
              '你好呀！我是你的AI助手，有什么可以帮你的吗？']),
            (r'再见|拜拜|bye|再见',
             ['再见！期待下次和你聊天！', 
              '拜拜！祝你一切顺利！', 
              '好的，下次见！有什么问题随时来找我。']),
            (r'谢谢|感谢|多谢',
             ['不客气！很高兴能帮到你！', 
              '不用谢！这是我应该做的。', 
              '能帮到你我很开心！']),
            (r'你叫什么|你是谁|名字|介绍一下',
             ['我是基于DeepSeek-V3架构的对话AI，整合了MLA注意力和MoE技术。', 
              '我是你的AI助手，使用了先进的混合专家架构。']),
            (r'你会什么|能做什么|功能',
             ['我可以和你聊天、回答问题、提供建议。我的架构使用了MLA注意力和MoE技术，能更高效地处理对话。', 
              '我支持多轮对话，能理解上下文，还可以进行知识问答。']),
            (r'天气|气温',
             ['抱歉，我暂时无法获取实时天气信息。建议你查看天气应用或搜索引擎。', 
              '我还没有接入天气服务，你可以查看手机上的天气应用。']),
            (r'时间|几点|日期',
             ['我无法获取当前时间，请查看你的设备。', 
              '你可以查看手机或电脑上的时间显示。']),
            (r'开心|高兴|快乐|哈哈',
             ['太棒了！保持好心情！', 
              '开心最重要！有什么开心的事想分享吗？', 
              '快乐是最好的状态！']),
            (r'难过|伤心|不开心|郁闷',
             ['别难过，有什么我可以帮你的吗？', 
              '每个人都有低谷的时候，相信自己会好起来的。', 
              '想开点，明天会更好！有什么烦心事可以说出来。']),
            (r'学习|读书|考试',
             ['学习使人进步！加油！有什么具体的问题吗？', 
              '读书是很好的习惯！需要我帮你解答学习问题吗？']),
            (r'无聊|没意思',
             ['无聊的时候可以看看书、听听音乐，或者和我聊聊天！', 
              '要不要我给你讲个笑话或者聊聊有趣的话题？']),
            (r'喜欢|爱',
             ['喜欢一个人或事物是很美好的！', 
              '有喜欢的东西是件幸福的事！']),
            (r'讨厌|恨|烦',
             ['别太在意那些让你不开心的事，放下负面情绪会更好。', 
              '每个人都有不喜欢的事物，这很正常。']),
            (r'工作|上班|加班',
             ['工作辛苦了！记得劳逸结合。', 
              '努力工作的人最棒！但也别忘了休息。']),
            (r'睡觉|困|累',
             ['累了就好好休息吧，身体最重要。', 
              '充足的睡眠对健康很重要，早点休息吧！']),
            (r'吃饭|饿了|美食',
             ['记得按时吃饭哦！身体是革命的本钱。', 
              '民以食为天，快去吃点好吃的吧！']),
            (r'怎么样|如何|好不好',
             ['我觉得挺好的！你有什么想法呢？', 
              '这要看具体情况，你有什么看法？']),
            (r'是的|对|没错|好的',
             ['好的，我明白了。还有什么想说的吗？', 
              '嗯嗯，继续说，我在听。']),
            (r'不是|不对|错了',
             ['抱歉，我理解错了。能再解释一下吗？', 
              '哦，我搞错了，请告诉我正确的理解。']),
            (r'为什么|原因',
             ['这个问题很有深度，让我想想...', 
              '原因可能有很多方面，你想了解哪个角度？']),
            (r'怎么|如何做|方法',
             ['这个问题需要具体分析，你能说说详细情况吗？', 
              '我可以给你一些建议，但需要了解更多信息。']),
            (r'mla|moe|deepseek|架构|技术',
             ['MLA (Multi-Head Latent Attention) 是DeepSeek-V3的核心技术之一，通过压缩KV Cache大幅降低推理内存。', 
              'MoE (Mixture of Experts) 使用稀疏激活，每个token只激活部分专家，节省计算量。']),
        ]
    
    def get_response(self, user_input: str) -> Optional[str]:
        user_input_lower = user_input.lower().strip()
        
        for pattern, responses in self.patterns:
            if re.search(pattern, user_input_lower):
                return random.choice(responses)
        
        return None
    
    def get_default_response(self) -> str:
        return random.choice(self.default_responses)


class DeepSeekChatbot:
    """DeepSeek-V3增强版聊天机器人"""
    
    def __init__(self, device: str = 'cuda'):
        self.device = torch.device(device if torch.cuda.is_available() else 'cpu')
        self.tokenizer = SimpleTokenizer()
        self.rule_responder = EnhancedRuleResponder()
        self.model = None
        self.conversation_history: List[Dict[str, str]] = []
        self.max_history = 10
        
        self._build_vocab()
        self._init_model()
        
    def _build_vocab(self):
        sample_texts = [
            "你好", "再见", "谢谢", "我是", "你是", "什么", "怎么",
            "为什么", "哪里", "谁", "什么时候", "多少", "可以", "能",
            "会", "想", "知道", "明白", "理解", "学习", "工作",
            "生活", "开心", "难过", "喜欢", "讨厌", "好的", "不",
            "是的", "对", "错", "我", "你", "他", "她", "它",
            "这", "那", "有", "没有", "在", "不在", "来", "去",
            "说", "听", "看", "做", "吃", "喝", "玩", "睡",
            "今天", "明天", "昨天", "现在", "以后", "以前",
            "时间", "地点", "人物", "事情", "问题", "答案",
            "hello", "hi", "bye", "yes", "no", "ok", "thanks",
            "mla", "moe", "deepseek", "attention", "expert",
            "模型", "架构", "技术", "神经网络", "深度学习"
        ]
        self.tokenizer.build_vocab(sample_texts)
        
    def _init_model(self):
        self.model = DeepSeekChatModel(
            vocab_size=self.tokenizer.vocab_size,
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
        ).to(self.device)
        
        total_params = sum(p.numel() for p in self.model.parameters())
        print(f"模型参数量: {total_params:,}")
        
    def chat(self, user_input: str, use_rule: bool = True) -> str:
        self.conversation_history.append({'role': 'user', 'content': user_input})
        
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]
        
        if use_rule:
            rule_response = self.rule_responder.get_response(user_input)
            if rule_response:
                self.conversation_history.append({'role': 'bot', 'content': rule_response})
                return rule_response
        
        try:
            input_ids = self.tokenizer.encode(user_input)
            input_tensor = torch.tensor([input_ids], dtype=torch.long, device=self.device)
            
            output_ids = self.model.generate(input_tensor, max_len=40, temperature=0.8, top_p=0.9)
            response = self.tokenizer.decode(output_ids[0].cpu().tolist())
            
            if response.strip() and len(response) > 3:
                self.conversation_history.append({'role': 'bot', 'content': response})
                return response
        except Exception as e:
            pass
        
        default_response = self.rule_responder.get_default_response()
        self.conversation_history.append({'role': 'bot', 'content': default_response})
        return default_response
    
    def get_history(self, last_n: int = 5) -> str:
        history = self.conversation_history[-last_n:]
        lines = []
        for msg in history:
            role = "你" if msg['role'] == 'user' else "AI"
            lines.append(f"{role}: {msg['content']}")
        return "\n".join(lines)
    
    def clear_history(self):
        self.conversation_history = []
        print("对话历史已清空")
    
    def get_model_info(self) -> str:
        info = []
        info.append("=" * 50)
        info.append("DeepSeek-V3 增强版对话模型")
        info.append("=" * 50)
        info.append(f"词汇表大小: {self.tokenizer.vocab_size}")
        info.append(f"设备: {self.device}")
        info.append(f"对话历史: {len(self.conversation_history)} 条")
        info.append("")
        info.append("核心技术:")
        info.append("  - MLA (Multi-Head Latent Attention)")
        info.append("  - DeepSeekMoE (混合专家)")
        info.append("  - Multi-Token Prediction")
        info.append("=" * 50)
        return "\n".join(info)


def interactive_chat():
    """交互式对话"""
    print("=" * 60)
    print("DeepSeek-V3 增强版对话系统")
    print("=" * 60)
    print("命令:")
    print("  quit/exit  - 退出")
    print("  history    - 查看对话历史")
    print("  clear      - 清空对话历史")
    print("  info       - 查看模型信息")
    print("=" * 60)
    
    chatbot = DeepSeekChatbot()
    
    while True:
        try:
            user_input = input("\n你: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', '退出']:
                print("\nAI: 再见！期待下次和你聊天！")
                break
            
            if user_input.lower() in ['history', '历史']:
                print("\n--- 对话历史 ---")
                print(chatbot.get_history())
                print("----------------")
                continue
            
            if user_input.lower() in ['clear', '清空']:
                chatbot.clear_history()
                continue
            
            if user_input.lower() in ['info', '信息']:
                print(chatbot.get_model_info())
                continue
            
            response = chatbot.chat(user_input)
            print(f"\nAI: {response}")
            
        except KeyboardInterrupt:
            print("\n\nAI: 再见！")
            break
        except Exception as e:
            print(f"\n[错误] {e}")


if __name__ == "__main__":
    print("使用设备:", torch.device('cuda' if torch.cuda.is_available() else 'cpu'))
    
    chatbot = DeepSeekChatbot()
    
    print("\n" + "=" * 60)
    print("测试对话")
    print("=" * 60)
    
    test_inputs = [
        "你好",
        "你叫什么名字",
        "你会做什么",
        "介绍一下MLA技术",
        "什么是MoE",
        "我有点难过",
        "谢谢",
        "再见"
    ]
    
    for user_input in test_inputs:
        response = chatbot.chat(user_input)
        print(f"用户: {user_input}")
        print(f"AI:   {response}")
        print()
    
    print(chatbot.get_model_info())
    
    print("\n进入交互模式...")
    interactive_chat()
