"""
DeepSeek-R1 核心思想简化实现

核心创新:
1. GRPO (Group Relative Policy Optimization) - 组相对策略优化
   - 不需要critic模型，使用组内相对奖励
   - 降低内存开销，提升训练效率

2. 基于规则的奖励系统
   - 准确性奖励: 答案是否正确
   - 格式奖励: 是否遵循<think>...</think><answer>...</answer>格式

3. 冷启动 + 多阶段训练
   - 阶段1: 冷启动 - 少量高质量数据SFT
   - 阶段2: 推理导向RL - 使用GRPO提升推理能力
   - 阶段3: 拒绝采样 - 生成更多训练数据
   - 阶段4: 全场景RL - 综合提升

参考论文: DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement Learning
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.distributions import Categorical
import numpy as np
import re
from typing import List, Tuple, Dict


class SimpleTransformer(nn.Module):
    """
    简化的Transformer模型用于推理任务
    """
    def __init__(self, vocab_size=1000, d_model=256, nhead=8, num_layers=6, max_len=512):
        super().__init__()
        self.d_model = d_model
        self.vocab_size = vocab_size
        
        # 词嵌入
        self.token_embedding = nn.Embedding(vocab_size, d_model)
        self.position_embedding = nn.Embedding(max_len, d_model)
        
        # Transformer编码器
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=d_model * 4,
            dropout=0.1,
            batch_first=True
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        
        # 输出头
        self.lm_head = nn.Linear(d_model, vocab_size)
        
    def forward(self, input_ids, attention_mask=None):
        batch_size, seq_len = input_ids.shape
        
        # 位置编码
        positions = torch.arange(seq_len, device=input_ids.device).unsqueeze(0).expand(batch_size, -1)
        
        # 嵌入
        x = self.token_embedding(input_ids) + self.position_embedding(positions)
        
        # Transformer
        if attention_mask is not None:
            # 将attention_mask转换为key_padding_mask (True表示mask)
            key_padding_mask = (attention_mask == 0)
            x = self.transformer(x, src_key_padding_mask=key_padding_mask)
        else:
            x = self.transformer(x)
        
        # 输出logits
        logits = self.lm_head(x)
        return logits
    
    def generate(self, input_ids, max_new_tokens=100, temperature=1.0, eos_token_id=2):
        """自回归生成"""
        self.eval()
        device = input_ids.device
        
        with torch.no_grad():
            for _ in range(max_new_tokens):
                # 前向传播
                logits = self.forward(input_ids)
                next_token_logits = logits[:, -1, :] / temperature
                
                # 采样
                probs = F.softmax(next_token_logits, dim=-1)
                next_token = torch.multinomial(probs, num_samples=1)
                
                # 拼接到序列
                input_ids = torch.cat([input_ids, next_token], dim=1)
                
                # 检查是否生成结束符
                if (next_token == eos_token_id).all():
                    break
        
        return input_ids


class RuleBasedReward:
    """
    基于规则的奖励系统
    DeepSeek-R1的核心设计之一
    """
    
    def __init__(self):
        self.format_pattern = re.compile(
            r'<think>(.*?)</think>\s*<answer>(.*?)</answer>',
            re.DOTALL
        )
    
    def check_format(self, text: str) -> float:
        """
        检查格式奖励
        要求输出格式: <think>...</think><answer>...</answer>
        """
        match = self.format_pattern.search(text)
        if not match:
            return 0.0
        
        # 检查是否有内容
        think_content = match.group(1).strip()
        answer_content = match.group(2).strip()
        
        if not think_content or not answer_content:
            return 0.5  # 有格式但内容为空
        
        return 1.0  # 完全正确
    
    def check_accuracy(self, text: str, ground_truth: str) -> float:
        """
        检查答案准确性
        从<answer>标签中提取答案并与标准答案比较
        """
        match = self.format_pattern.search(text)
        if not match:
            return 0.0
        
        predicted_answer = match.group(2).strip()
        
        # 简单的字符串匹配（实际应用中可以使用更复杂的评估）
        if predicted_answer.lower() == ground_truth.lower():
            return 1.0
        
        # 部分匹配
        if ground_truth.lower() in predicted_answer.lower():
            return 0.5
        
        return 0.0
    
    def compute_rewards(self, outputs: List[str], ground_truths: List[str]) -> torch.Tensor:
        """
        计算奖励
        总奖励 = 格式奖励 + 准确性奖励
        """
        rewards = []
        for output, gt in zip(outputs, ground_truths):
            format_reward = self.check_format(output)
            accuracy_reward = self.check_accuracy(output, gt)
            
            # 总奖励 (可以调整权重)
            total_reward = 0.3 * format_reward + 0.7 * accuracy_reward
            rewards.append(total_reward)
        
        return torch.tensor(rewards, dtype=torch.float32)


class GRPO:
    """
    GRPO (Group Relative Policy Optimization)
    DeepSeek-R1的核心算法
    
    关键特点:
    1. 不需要critic模型，节省内存
    2. 使用组内相对奖励，减少方差
    3. 基于PPO的裁剪目标
    
    算法步骤:
    1. 对同一个问题生成G个回答 (组)
    2. 计算每个回答的奖励
    3. 计算组内平均奖励作为baseline
    4. 优势 = 奖励 - baseline
    5. 使用PPO目标更新策略
    """
    
    def __init__(
        self,
        model: nn.Module,
        ref_model: nn.Module,
        reward_fn: RuleBasedReward,
        group_size: 4,
        epsilon: float = 0.2,
        beta: float = 0.01,
        lr: float = 1e-5
    ):
        self.model = model
        self.ref_model = ref_model
        self.reward_fn = reward_fn
        self.group_size = group_size
        self.epsilon = epsilon
        self.beta = beta  # KL惩罚系数
        
        self.optimizer = optim.Adam(model.parameters(), lr=lr)
        
    def compute_grpo_loss(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
        old_log_probs: torch.Tensor,
        advantages: torch.Tensor
    ) -> torch.Tensor:
        """
        计算GRPO损失
        
        Args:
            input_ids: 输入token [batch_size * group_size, seq_len]
            attention_mask: 注意力掩码
            old_log_probs: 旧策略的log概率 [batch_size * group_size, seq_len]
            advantages: 优势值 [batch_size * group_size]
        
        Returns:
            loss: GRPO损失
        """
        # 新策略的log概率
        logits = self.model(input_ids, attention_mask)
        log_probs = F.log_softmax(logits, dim=-1)
        
        # 获取每个token的log概率
        # 假设input_ids是生成的序列，我们需要计算每个位置的log_prob
        # 这里简化处理，使用平均log_prob
        new_log_probs = log_probs.gather(2, input_ids.unsqueeze(-1)).squeeze(-1)
        new_log_probs = (new_log_probs * attention_mask).sum(dim=1) / attention_mask.sum(dim=1)
        
        # 参考模型的log概率 (用于KL惩罚)
        with torch.no_grad():
            ref_logits = self.ref_model(input_ids, attention_mask)
            ref_log_probs = F.log_softmax(ref_logits, dim=-1)
            ref_log_probs = ref_log_probs.gather(2, input_ids.unsqueeze(-1)).squeeze(-1)
            ref_log_probs = (ref_log_probs * attention_mask).sum(dim=1) / attention_mask.sum(dim=1)
        
        # 概率比
        ratio = torch.exp(new_log_probs - old_log_probs)
        
        # 扩展advantages以匹配ratio的形状
        advantages = advantages.unsqueeze(1).expand(-1, ratio.shape[0] // advantages.shape[0])
        advantages = advantages.reshape(-1)
        
        # PPO裁剪目标
        surr1 = ratio * advantages
        surr2 = torch.clamp(ratio, 1 - self.epsilon, 1 + self.epsilon) * advantages
        policy_loss = -torch.min(surr1, surr2).mean()
        
        # KL惩罚 (防止策略偏离参考模型太远)
        kl_div = (new_log_probs - ref_log_probs).mean()
        
        # 总损失
        loss = policy_loss + self.beta * kl_div
        
        return loss
    
    def train_step(
        self,
        questions: List[str],
        ground_truths: List[str],
        tokenizer
    ) -> Dict[str, float]:
        """
        单步训练
        
        Args:
            questions: 问题列表
            ground_truths: 标准答案列表
            tokenizer: 分词器
        
        Returns:
            metrics: 训练指标
        """
        self.model.train()
        
        all_outputs = []
        all_input_ids = []
        all_attention_masks = []
        all_log_probs = []
        all_rewards = []
        
        # 对每个问题生成group_size个回答
        for question, gt in zip(questions, ground_truths):
            # 编码问题
            question_tokens = tokenizer.encode(question)
            question_tensor = torch.tensor([question_tokens]).to(self.model.token_embedding.weight.device)
            
            group_outputs = []
            group_log_probs = []
            
            for _ in range(self.group_size):
                # 生成回答
                output_ids = self.model.generate(
                    question_tensor,
                    max_new_tokens=100,
                    temperature=1.0
                )
                
                # 解码
                output_text = tokenizer.decode(output_ids[0].cpu().numpy())
                group_outputs.append(output_text)
                
                # 计算log概率 (简化处理)
                logits = self.model(output_ids)
                log_probs = F.log_softmax(logits, dim=-1)
                token_log_probs = log_probs.gather(2, output_ids.unsqueeze(-1)).squeeze(-1)
                seq_log_prob = token_log_probs.mean().item()
                group_log_probs.append(seq_log_prob)
                
                all_input_ids.append(output_ids[0])
                all_attention_masks.append(torch.ones_like(output_ids[0]))
            
            # 计算奖励
            rewards = self.reward_fn.compute_rewards(group_outputs, [gt] * self.group_size)
            all_rewards.extend(rewards.tolist())
            all_outputs.extend(group_outputs)
            all_log_probs.extend(group_log_probs)
        
        # 计算组内相对优势
        advantages = []
        for i in range(0, len(all_rewards), self.group_size):
            group_rewards = torch.tensor(all_rewards[i:i+self.group_size])
            mean_reward = group_rewards.mean()
            std_reward = group_rewards.std() + 1e-8
            group_advantages = (group_rewards - mean_reward) / std_reward
            advantages.extend(group_advantages.tolist())
        
        # 准备批次数据
        max_len = max(len(ids) for ids in all_input_ids)
        padded_input_ids = []
        padded_attention_masks = []
        
        for ids, mask in zip(all_input_ids, all_attention_masks):
            pad_len = max_len - len(ids)
            padded_ids = torch.cat([ids, torch.zeros(pad_len, dtype=torch.long, device=ids.device)])
            padded_mask = torch.cat([mask, torch.zeros(pad_len, dtype=torch.long, device=mask.device)])
            padded_input_ids.append(padded_ids)
            padded_attention_masks.append(padded_mask)
        
        device = self.model.token_embedding.weight.device
        batch_input_ids = torch.stack(padded_input_ids).to(device)
        batch_attention_masks = torch.stack(padded_attention_masks).to(device)
        batch_old_log_probs = torch.tensor(all_log_probs, device=device)
        batch_advantages = torch.tensor(advantages, device=device)
        
        # 计算损失并更新
        loss = self.compute_grpo_loss(
            batch_input_ids,
            batch_attention_masks,
            batch_old_log_probs,
            batch_advantages
        )
        
        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
        self.optimizer.step()
        
        # 返回指标
        metrics = {
            'loss': loss.item(),
            'mean_reward': np.mean(all_rewards),
            'max_reward': np.max(all_rewards),
            'format_accuracy': np.mean([self.reward_fn.check_format(o) for o in all_outputs]),
        }
        
        return metrics


class SimpleTokenizer:
    """简单的tokenizer用于演示"""
    
    def __init__(self, vocab_size=1000):
        self.vocab_size = vocab_size
        self.word2idx = {'<pad>': 0, '<sos>': 1, '<eos>': 2, '<unk>': 3}
        self.idx2word = {v: k for k, v in self.word2idx.items()}
        
        # 添加一些基本词汇
        words = ['<think>', '</think>', '<answer>', '</answer>'] + \
                [str(i) for i in range(100)] + \
                ['+', '-', '*', '/', '=', 'the', 'answer', 'is', 'what', 'of', 'and']
        
        for word in words:
            if word not in self.word2idx:
                idx = len(self.word2idx)
                self.word2idx[word] = idx
                self.idx2word[idx] = word
    
    def encode(self, text: str) -> List[int]:
        tokens = text.lower().split()
        return [self.word2idx.get(token, self.word2idx['<unk>']) for token in tokens]
    
    def decode(self, indices: List[int]) -> str:
        tokens = [self.idx2word.get(int(idx), '<unk>') for idx in indices]
        return ' '.join(tokens)


def create_synthetic_dataset(num_samples=100):
    """创建简单的数学推理数据集"""
    dataset = []
    
    for _ in range(num_samples):
        a = np.random.randint(1, 20)
        b = np.random.randint(1, 20)
        op = np.random.choice(['+', '-', '*'])
        
        if op == '+':
            question = f"What is {a} + {b} ?"
            answer = str(a + b)
        elif op == '-':
            question = f"What is {a} - {b} ?"
            answer = str(a - b)
        else:
            question = f"What is {a} * {b} ?"
            answer = str(a * b)
        
        dataset.append({
            'question': question,
            'answer': answer
        })
    
    return dataset


def train_simple_r1():
    """训练简单的DeepSeek-R1风格模型"""
    
    print("=" * 70)
    print("DeepSeek-R1 核心思想简化实现")
    print("=" * 70)
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"使用设备: {device}")
    
    # 初始化
    tokenizer = SimpleTokenizer(vocab_size=1000)
    model = SimpleTransformer(
        vocab_size=1000,
        d_model=256,
        nhead=8,
        num_layers=4
    ).to(device)
    
    # 参考模型 (冻结参数)
    ref_model = SimpleTransformer(
        vocab_size=1000,
        d_model=256,
        nhead=8,
        num_layers=4
    ).to(device)
    ref_model.load_state_dict(model.state_dict())
    for param in ref_model.parameters():
        param.requires_grad = False
    
    # 奖励函数和GRPO
    reward_fn = RuleBasedReward()
    grpo = GRPO(
        model=model,
        ref_model=ref_model,
        reward_fn=reward_fn,
        group_size=4,
        epsilon=0.2,
        beta=0.01,
        lr=1e-4
    )
    
    # 创建数据集
    dataset = create_synthetic_dataset(num_samples=100)
    print(f"\n数据集大小: {len(dataset)}")
    print(f"模型参数量: {sum(p.numel() for p in model.parameters()):,}")
    print(f"GRPO组大小: {grpo.group_size}")
    
    # 训练
    print("\n" + "-" * 70)
    print("开始训练")
    print("-" * 70)
    
    num_epochs = 10
    batch_size = 4
    
    for epoch in range(num_epochs):
        # 随机采样批次
        batch_indices = np.random.choice(len(dataset), size=batch_size, replace=False)
        batch = [dataset[i] for i in batch_indices]
        
        questions = [item['question'] for item in batch]
        ground_truths = [item['answer'] for item in batch]
        
        # 训练步骤
        try:
            metrics = grpo.train_step(questions, ground_truths, tokenizer)
            
            print(f"Epoch {epoch+1}/{num_epochs}: "
                  f"Loss={metrics['loss']:.4f}, "
                  f"Mean Reward={metrics['mean_reward']:.3f}, "
                  f"Max Reward={metrics['max_reward']:.3f}, "
                  f"Format Acc={metrics['format_accuracy']:.2%}")
        except Exception as e:
            print(f"Epoch {epoch+1}/{num_epochs}: 训练步骤出错 - {e}")
            continue
    
    # 测试生成
    print("\n" + "-" * 70)
    print("测试生成")
    print("-" * 70)
    
    test_questions = [
        "What is 5 + 3 ?",
        "What is 10 - 4 ?",
        "What is 3 * 7 ?"
    ]
    
    model.eval()
    for question in test_questions:
        question_tokens = tokenizer.encode(question)
        question_tensor = torch.tensor([question_tokens]).to(device)
        
        output_ids = model.generate(question_tensor, max_new_tokens=50)
        output_text = tokenizer.decode(output_ids[0].cpu().numpy())
        
        print(f"\n问题: {question}")
        print(f"回答: {output_text}")
        
        # 检查格式
        format_reward = reward_fn.check_format(output_text)
        print(f"格式奖励: {format_reward}")
    
    print("\n" + "=" * 70)
    print("✅ DeepSeek-R1 核心思想演示完成!")
    print("=" * 70)
    print("\n核心创新总结:")
    print("  1. GRPO - 组相对策略优化，无需critic模型")
    print("  2. 基于规则的奖励 - 格式奖励 + 准确性奖励")
    print("  3. 多阶段训练 - 冷启动 + RL + 拒绝采样")
    print("\n注意: 这是一个高度简化的演示版本")
    print("      实际DeepSeek-R1使用更大的模型和更复杂的训练流程")


if __name__ == "__main__":
    train_simple_r1()
