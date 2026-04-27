"""
简易NLP对话系统

基于规则的对话系统 + 简单神经网络增强
适用于演示和学习目的
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import re
import random
from typing import List, Dict, Tuple, Optional
from collections import defaultdict


class SimpleTokenizer:
    """简单的分词器"""
    
    def __init__(self):
        self.word2idx = {'<pad>': 0, '<sos>': 1, '<eos>': 2, '<unk>': 3}
        self.idx2word = {v: k for k, v in self.word2idx.items()}
        self.vocab_size = 4
        
    def build_vocab(self, texts: List[str], min_freq: int = 1):
        """构建词汇表"""
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
        """简单分词"""
        text = text.lower().strip()
        text = re.sub(r'[^\w\s\u4e00-\u9fff]', '', text)
        return text.split()
    
    def encode(self, text: str, max_len: int = 50) -> List[int]:
        """编码文本"""
        words = self.tokenize(text)
        ids = [self.word2idx.get(w, self.word2idx['<unk>']) for w in words]
        ids = ids[:max_len-2]
        return [self.word2idx['<sos>']] + ids + [self.word2idx['<eos>']]
    
    def decode(self, ids: List[int]) -> str:
        """解码文本"""
        words = []
        for idx in ids:
            if idx == self.word2idx['<eos>']:
                break
            if idx not in [self.word2idx['<pad>'], self.word2idx['<sos>']]:
                words.append(self.idx2word.get(idx, '<unk>'))
        return ' '.join(words)


class SimpleChatModel(nn.Module):
    """简单的对话模型 - Seq2Seq架构"""
    
    def __init__(self, vocab_size: int, d_model: int = 256, nhead: int = 4, 
                 num_layers: int = 2, dropout: float = 0.1):
        super().__init__()
        self.d_model = d_model
        
        self.embedding = nn.Embedding(vocab_size, d_model)
        self.pos_encoding = nn.Parameter(torch.randn(1, 512, d_model) * 0.02)
        
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=nhead, dim_feedforward=d_model*4,
            dropout=dropout, batch_first=True
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        
        decoder_layer = nn.TransformerDecoderLayer(
            d_model=d_model, nhead=nhead, dim_feedforward=d_model*4,
            dropout=dropout, batch_first=True
        )
        self.decoder = nn.TransformerDecoder(decoder_layer, num_layers=num_layers)
        
        self.output_proj = nn.Linear(d_model, vocab_size)
        self.dropout = nn.Dropout(dropout)
        
    def forward(self, src: torch.Tensor, tgt: torch.Tensor,
                src_mask: Optional[torch.Tensor] = None,
                tgt_mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        batch_size, src_len = src.shape
        _, tgt_len = tgt.shape
        
        src_emb = self.embedding(src) + self.pos_encoding[:, :src_len, :]
        tgt_emb = self.embedding(tgt) + self.pos_encoding[:, :tgt_len, :]
        
        src_emb = self.dropout(src_emb)
        tgt_emb = self.dropout(tgt_emb)
        
        memory = self.encoder(src_emb, src_key_padding_mask=src_mask)
        
        tgt_attn_mask = torch.triu(
            torch.ones(tgt_len, tgt_len, device=tgt.device) * float('-inf'),
            diagonal=1
        )
        
        output = self.decoder(tgt_emb, memory, tgt_mask=tgt_attn_mask,
                              tgt_key_padding_mask=tgt_mask)
        
        return self.output_proj(output)
    
    def generate(self, src: torch.Tensor, max_len: int = 50,
                 temperature: float = 1.0) -> torch.Tensor:
        """生成回复"""
        self.eval()
        device = src.device
        batch_size = src.shape[0]
        
        with torch.no_grad():
            src_len = src.shape[1]
            src_emb = self.embedding(src) + self.pos_encoding[:, :src_len, :]
            memory = self.encoder(src_emb)
            
            tgt = torch.full((batch_size, 1), 1, dtype=torch.long, device=device)
            
            for _ in range(max_len - 1):
                tgt_len = tgt.shape[1]
                tgt_emb = self.embedding(tgt) + self.pos_encoding[:, :tgt_len, :]
                
                tgt_attn_mask = torch.triu(
                    torch.ones(tgt_len, tgt_len, device=device) * float('-inf'),
                    diagonal=1
                )
                
                output = self.decoder(tgt_emb, memory, tgt_mask=tgt_attn_mask)
                logits = self.output_proj(output[:, -1, :]) / temperature
                probs = F.softmax(logits, dim=-1)
                next_token = torch.multinomial(probs, num_samples=1)
                
                tgt = torch.cat([tgt, next_token], dim=1)
                
                if (next_token == 2).all():
                    break
            
            return tgt


class RuleBasedResponder:
    """基于规则的回复生成器"""
    
    def __init__(self):
        self.patterns = self._build_patterns()
        self.default_responses = [
            "我不太明白你的意思，能再说清楚一点吗？",
            "这个话题很有趣，能详细说说吗？",
            "我正在学习，还不太懂这个。",
            "你能换个方式问吗？",
            "让我想想...这个问题有点复杂。",
        ]
        
    def _build_patterns(self) -> List[Tuple[str, List[str]]]:
        """构建对话模式"""
        return [
            (r'你好|您好|hi|hello', 
             ['你好！很高兴见到你！', '你好呀！有什么可以帮你的吗？', '嗨！今天过得怎么样？']),
            (r'再见|拜拜|bye', 
             ['再见！下次再聊！', '拜拜！祝你愉快！', '好的，再见！']),
            (r'谢谢|感谢', 
             ['不客气！', '很高兴能帮到你！', '不用谢！']),
            (r'你叫什么|你是谁|名字', 
             ['我是一个简单的对话AI，你可以叫我小助手。', '我是AI助手，很高兴认识你！']),
            (r'你会什么|能做什么', 
             ['我可以和你聊天，回答一些简单的问题。', '我会聊天，也会尝试回答你的问题。']),
            (r'天气', 
             ['抱歉，我暂时无法查询天气信息。', '你可以查看手机上的天气应用。']),
            (r'时间|几点', 
             ['我无法获取当前时间，请查看你的设备。', '你可以看看手机或电脑上的时间。']),
            (r'开心|高兴|快乐', 
             ['太好了！保持好心情！', '开心最重要！', '快乐是最好的状态！']),
            (r'难过|伤心|不开心', 
             ['别难过，一切都会好起来的。', '有什么我可以帮你的吗？', '想开点，明天会更好！']),
            (r'学习|读书', 
             ['学习使人进步！加油！', '读书是很好的习惯！', '活到老学到老！']),
            (r'无聊', 
             ['无聊的时候可以看看书，或者听听音乐。', '要不要聊聊天？', '找点有趣的事情做吧！']),
            (r'喜欢|爱', 
             ['喜欢一个人/事物是很美好的！', '有喜欢的东西很幸福！']),
            (r'讨厌|恨', 
             ['别太在意那些让你不开心的事。', '放下负面情绪，生活会更好。']),
            (r'工作|上班', 
             ['工作辛苦了！注意休息。', '努力工作的人最棒！']),
            (r'睡觉|困', 
             ['累了就休息吧，身体最重要。', '晚安，好梦！']),
            (r'吃饭|饿了', 
             ['记得按时吃饭哦！', '民以食为天，快去吃饭吧！']),
            (r'怎么样|如何', 
             ['我觉得挺好的！', '这要看具体情况。', '你有什么想法呢？']),
            (r'是的|对|没错', 
             ['好的，我明白了。', '嗯嗯，继续说。', '然后呢？']),
            (r'不是|不对|错了', 
             ['哦，我理解错了，能再解释一下吗？', '抱歉，我搞错了。']),
        ]
    
    def get_response(self, user_input: str) -> Optional[str]:
        """根据规则获取回复"""
        user_input = user_input.lower().strip()
        
        for pattern, responses in self.patterns:
            if re.search(pattern, user_input):
                return random.choice(responses)
        
        return None
    
    def get_default_response(self) -> str:
        """获取默认回复"""
        return random.choice(self.default_responses)


class SimpleChatbot:
    """简易聊天机器人"""
    
    def __init__(self, model_path: Optional[str] = None, device: str = 'cuda'):
        self.device = torch.device(device if torch.cuda.is_available() else 'cpu')
        self.tokenizer = SimpleTokenizer()
        self.rule_responder = RuleBasedResponder()
        self.model = None
        self.conversation_history: List[Dict[str, str]] = []
        
        self._build_vocab()
        
        if model_path:
            self.load_model(model_path)
        else:
            self._init_model()
    
    def _build_vocab(self):
        """构建基础词汇表"""
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
            "hello", "hi", "bye", "yes", "no", "ok", "thanks"
        ]
        self.tokenizer.build_vocab(sample_texts)
    
    def _init_model(self):
        """初始化模型"""
        self.model = SimpleChatModel(
            vocab_size=self.tokenizer.vocab_size,
            d_model=128,
            nhead=4,
            num_layers=2
        ).to(self.device)
        
        total_params = sum(p.numel() for p in self.model.parameters())
        print(f"模型参数量: {total_params:,}")
    
    def save_model(self, path: str):
        """保存模型"""
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'vocab': self.tokenizer.word2idx
        }, path)
        print(f"模型已保存到: {path}")
    
    def load_model(self, path: str):
        """加载模型"""
        checkpoint = torch.load(path, map_location=self.device)
        self.tokenizer.word2idx = checkpoint['vocab']
        self.tokenizer.idx2word = {v: k for k, v in self.tokenizer.word2idx.items()}
        self.tokenizer.vocab_size = len(self.tokenizer.word2idx)
        
        self._init_model()
        self.model.load_state_dict(checkpoint['model_state_dict'])
        print(f"模型已从 {path} 加载")
    
    def chat(self, user_input: str, use_rule: bool = True) -> str:
        """
        对话主函数
        
        Args:
            user_input: 用户输入
            use_rule: 是否优先使用规则回复
        
        Returns:
            机器人回复
        """
        self.conversation_history.append({'role': 'user', 'content': user_input})
        
        if use_rule:
            rule_response = self.rule_responder.get_response(user_input)
            if rule_response:
                self.conversation_history.append({'role': 'bot', 'content': rule_response})
                return rule_response
        
        if self.model is not None:
            try:
                input_ids = self.tokenizer.encode(user_input)
                input_tensor = torch.tensor([input_ids], dtype=torch.long, device=self.device)
                
                output_ids = self.model.generate(input_tensor, max_len=30, temperature=0.8)
                response = self.tokenizer.decode(output_ids[0].cpu().tolist())
                
                if response.strip():
                    self.conversation_history.append({'role': 'bot', 'content': response})
                    return response
            except Exception as e:
                pass
        
        default_response = self.rule_responder.get_default_response()
        self.conversation_history.append({'role': 'bot', 'content': default_response})
        return default_response
    
    def get_history(self, last_n: int = 5) -> str:
        """获取最近对话历史"""
        history = self.conversation_history[-last_n:]
        lines = []
        for msg in history:
            role = "你" if msg['role'] == 'user' else "AI"
            lines.append(f"{role}: {msg['content']}")
        return "\n".join(lines)
    
    def clear_history(self):
        """清空对话历史"""
        self.conversation_history = []
        print("对话历史已清空")


def interactive_chat():
    """交互式对话"""
    print("=" * 60)
    print("简易NLP对话系统")
    print("=" * 60)
    print("输入 'quit' 或 'exit' 退出")
    print("输入 'history' 查看对话历史")
    print("输入 'clear' 清空对话历史")
    print("=" * 60)
    
    chatbot = SimpleChatbot()
    
    while True:
        try:
            user_input = input("\n你: ").strip()
            
            if not user_input:
                continue
            
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
            
            response = chatbot.chat(user_input)
            print(f"\nAI: {response}")
            
        except KeyboardInterrupt:
            print("\n\nAI: 再见！")
            break
        except Exception as e:
            print(f"\n[错误] {e}")


if __name__ == "__main__":
    print("使用设备:", torch.device('cuda' if torch.cuda.is_available() else 'cpu'))
    
    chatbot = SimpleChatbot()
    
    print("\n" + "=" * 60)
    print("测试对话")
    print("=" * 60)
    
    test_inputs = [
        "你好",
        "你叫什么名字",
        "你会做什么",
        "今天天气怎么样",
        "我有点难过",
        "谢谢",
        "再见"
    ]
    
    for user_input in test_inputs:
        response = chatbot.chat(user_input)
        print(f"用户: {user_input}")
        print(f"AI:   {response}")
        print()
    
    print("\n" + "=" * 60)
    print("进入交互模式...")
    print("=" * 60)
    
    interactive_chat()
