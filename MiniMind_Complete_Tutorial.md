# MiniMind 完整代码教学指南

## 前言：MiniMind项目文件结构详解

在深入学习MiniMind代码之前，让我们首先全面了解项目的文件结构和各部分的功能。这将帮助你建立清晰的项目认知框架。

### 项目根目录结构

```
minimind/                           # 项目根目录
│
├── model/                          # 【核心】模型定义目录
│   ├── model.py                    # 模型架构实现（最重要文件）
│   ├── LMConfig.py                 # 模型配置类
│   └── minimind_tokenizer/         # 分词器目录
│       ├── tokenizer.json          # 分词器配置
│       ├── tokenizer.model         # 分词器模型
│       └── vocab.json              # 词汇表
│
├── dataset/                        # 【数据】数据集目录
│   ├── pretrain_hq.jsonl          # 预训练语料（高质量）
│   ├── sft_mini_512.jsonl         # SFT微调数据
│   └── dpo_data.jsonl             # DPO偏好数据
│
├── out/                            # 【输出】训练产物目录
│   ├── pretrain_512.pth           # 预训练权重
│   ├── full_sft_512.pth           # SFT权重
│   └── lora_512.pth               # LoRA权重
│
├── 1-pretrain.py                   # 预训练入口脚本
├── 2-eval.py                       # 模型评估入口脚本
├── 3-full_sft.py                   # 全参数微调入口脚本
├── 4-lora_sft.py                   # LoRA微调入口脚本
├── 5-dpo_train.py                  # DPO训练入口脚本
│
├── requirements.txt                # 依赖包列表
├── README.md                       # 项目说明文档
└── setup.py                        # 安装配置脚本
```

### 核心文件详解

#### 1. model/model.py - 模型核心实现

这是MiniMind最重要的文件，包含了所有模型组件的实现：

```python
model.py 文件结构：

├── RMSNorm 类                      # 归一化层（第16-50行）
│   ├── __init__()                 # 初始化
│   ├── _norm()                    # 归一化计算
│   └── forward()                  # 前向传播
│
├── precompute_pos_cis() 函数       # RoPE预计算（第53-113行）
├── apply_rotary_emb() 函数         # RoPE应用（第116-139行）
│
├── repeat_kv() 函数                # KV头复制（第142-165行）
│
├── Attention 类                    # 注意力层（第168-280行）
│   ├── __init__()                 # 初始化投影层
│   └── forward()                  # 注意力计算
│
├── FeedForward 类                  # 前馈网络（第283-320行）
│   ├── __init__()                 # 初始化三层投影
│   └── forward()                  # SwiGLU计算
│
├── MoEGate 类                      # MoE门控（第323-380行）
├── MOEFeedForward 类               # MoE前馈网络（第383-450行）
│
├── MiniMindBlock 类                # Transformer块（第453-500行）
│   ├── __init__()                 # 初始化子层
│   └── forward()                  # 残差连接计算
│
└── MiniMindLM 类                   # 完整模型（第503-600行）
    ├── __init__()                 # 模型组装
    ├── forward()                  # 前向传播
    └── generate()                 # 文本生成
```

**代码行数统计**：约600行核心代码

**学习建议**：
- 按照从简单到复杂的顺序阅读：RMSNorm → RoPE → Attention → FeedForward → MiniMindBlock → MiniMindLM
- 每个类都是独立的，可以单独测试和理解
- 注意理解数据形状的变化

#### 2. model/LMConfig.py - 模型配置

```python
LMConfig.py 文件结构：

├── 导入部分                        # dataclass, typing等
│
└── LMConfig 类                     # 配置数据类
    ├── dim                         # 隐藏维度
    ├── n_layers                    # 层数
    ├── n_heads                     # 注意力头数
    ├── n_kv_heads                  # KV头数（GQA）
    ├── vocab_size                  # 词汇表大小
    ├── hidden_dim                  # FFN隐藏维度
    ├── max_seq_len                 # 最大序列长度
    ├── dropout                     # Dropout比率
    ├── flash_attn                  # Flash Attention开关
    ├── use_moe                     # MoE开关
    ├── num_experts_per_tok         # 每token激活专家数
    ├── n_routed_experts            # 路由专家总数
    └── __post_init__()             # 派生参数计算
```

**关键参数说明**：

| 参数 | 默认值 | 说明 | 影响 |
|------|--------|------|------|
| dim | 512 | 隐藏维度 | 决定模型容量 |
| n_layers | 8 | Transformer层数 | 决定模型深度 |
| n_heads | 8 | 注意力头数 | 多头注意力 |
| n_kv_heads | 2 | KV头数 | GQA配置 |
| vocab_size | 6400 | 词汇表大小 | 嵌入层大小 |
| max_seq_len | 8192 | 最大序列长度 | RoPE预计算 |

#### 3. model/minimind_tokenizer/ - 分词器

```
minimind_tokenizer/
├── tokenizer.json          # 分词器完整配置
│   ├── vocab               # 词汇表映射
│   ├── merges              # BPE合并规则
│   └── special_tokens      # 特殊token定义
│
├── tokenizer.model         # SentencePiece模型
├── vocab.json              # 独立词汇表文件
└── special_tokens_map.json # 特殊token映射
```

**特殊Token定义**：

| Token | ID | 用途 |
|-------|-----|------|
| `<pad>` | 0 | 填充 |
| `<s>` | 1 | 序列开始(BOS) |
| `</s>` | 2 | 序列结束(EOS) |
| `<|im_start|>` | 3 | ChatML角色开始 |
| `<|im_end|>` | 4 | ChatML角色结束 |

#### 4. 数据集文件格式

**pretrain_hq.jsonl** - 预训练数据格式：
```json
{"text": "这是一段预训练文本，用于让模型学习语言知识..."}
{"text": "另一段预训练文本..."}
```

**sft_mini_512.jsonl** - SFT数据格式：
```json
{
  "conversations": [
    {"role": "user", "content": "你好"},
    {"role": "assistant", "content": "你好！有什么可以帮助你的？"}
  ]
}
```

**dpo_data.jsonl** - DPO数据格式：
```json
{
  "prompt": "请解释什么是机器学习",
  "chosen": "机器学习是人工智能的一个分支...",
  "rejected": "机器学习就是让机器学习..."
}
```

### 训练脚本详解

#### 1-pretrain.py - 预训练脚本

```python
1-pretrain.py 主要功能：

├── 参数解析                        # argparse配置
├── 分布式初始化                    # DDP设置
├── 数据加载                        # DataLoader创建
├── 模型创建                        # MiniMindLM实例化
├── 优化器配置                      # AdamW设置
├── 训练循环                        # 主训练逻辑
│   ├── 前向传播
│   ├── 损失计算
│   ├── 反向传播
│   ├── 梯度裁剪
│   ├── 参数更新
│   └── 学习率调度
├── 检查点保存                      # 定期保存
└── 日志记录                        # 训练监控
```

**关键训练参数**：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| batch_size | 32 | 批次大小 |
| learning_rate | 5e-4 | 学习率 |
| epochs | 1 | 训练轮数 |
| accumulation_steps | 8 | 梯度累积步数 |
| grad_clip | 1.0 | 梯度裁剪阈值 |
| warmup_steps | 100 | 预热步数 |

#### 3-full_sft.py - 全参数微调

```python
3-full_sft.py 与预训练的区别：

1. 数据格式：使用对话数据而非纯文本
2. 损失计算：只计算assistant回复部分
3. 学习率：通常更小（1e-5）
4. 训练轮数：更多（3-10轮）
5. 权重加载：从预训练权重初始化
```

#### 4-lora_sft.py - LoRA微调

```python
LoRA核心实现：

├── LoRALayer 类                    # LoRA层定义
│   ├── lora_A                     # 低秩矩阵A
│   └── lora_B                     # 低秩矩阵B
│
├── apply_lora_to_model()           # 应用LoRA
│   └── 冻结原权重，添加LoRA层
│
└── 训练流程                        # 只训练LoRA参数
```

**LoRA参数**：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| lora_rank | 8 | LoRA秩 |
| lora_alpha | 16.0 | 缩放因子 |
| target_modules | ['wq','wk','wv','wo','w1','w2','w3'] | 目标模块 |

#### 5-dpo_train.py - DPO训练

```python
DPO核心实现：

├── DPODataset 类                   # DPO数据集
│   └── 加载prompt/chosen/rejected
│
├── dpo_loss() 函数                 # DPO损失函数
│   └── 计算偏好优化损失
│
├── 策略模型                        # 正在训练的模型
├── 参考模型                        # 冻结的参考模型
└── 训练循环                        # DPO特定逻辑
```

### 输出文件说明

#### 权重文件格式

```python
# .pth 文件结构
checkpoint = {
    'model': model.state_dict(),        # 模型权重
    'optimizer': optimizer.state_dict(), # 优化器状态
    'epoch': epoch,                     # 当前轮数
    'step': step,                       # 当前步数
    'loss': loss,                       # 损失值
}
```

#### 权重文件大小估算

| 模型版本 | 参数量 | 权重文件大小 |
|---------|--------|-------------|
| minimind-v1-small | 26M | ~100MB |
| minimind-v1-moe | 104M | ~400MB |
| minimind-v1 | 108M | ~420MB |

### 项目依赖（requirements.txt）

```
torch>=2.0.0                # PyTorch核心
transformers>=4.30.0        # HuggingFace工具
tokenizers>=0.13.0          # 分词器
datasets>=2.12.0            # 数据集工具
accelerate>=0.20.0          # 加速库
flash-attn>=2.0.0           # Flash Attention
wandb>=0.15.0               # 实验跟踪
tensorboard>=2.12.0         # 可视化
tqdm>=4.65.0                # 进度条
numpy>=1.24.0               # 数值计算
```

### 学习路径建议

```
推荐学习顺序：

第1阶段：理解架构
├── 阅读 README.md
├── 理解 LMConfig.py
└── 运行 2-eval.py 体验模型

第2阶段：深入模型
├── 精读 model.py
│   ├── RMSNorm
│   ├── RoPE
│   ├── Attention
│   ├── FeedForward
│   └── MiniMindLM
└── 理解数据流

第3阶段：实践训练
├── 准备数据
├── 运行 1-pretrain.py
├── 运行 3-full_sft.py
└── 分析训练日志

第4阶段：进阶优化
├── 学习 LoRA 微调
├── 学习 DPO 训练
├── 尝试修改模型
└── 自定义数据训练
```

### 常见问题与文件对应

| 问题 | 查看文件 |
|------|---------|
| 模型结构是什么？ | model/model.py |
| 如何修改模型大小？ | model/LMConfig.py |
| 如何准备数据？ | dataset/*.jsonl |
| 如何开始训练？ | 1-pretrain.py |
| 如何评估模型？ | 2-eval.py |
| 如何微调模型？ | 3-full_sft.py, 4-lora_sft.py |
| 如何使用DPO？ | 5-dpo_train.py |
| 分词器如何工作？ | model/minimind_tokenizer/ |

---

## 📚 MiniMind 完整学习路径 - 12大核心模块

### 学习路径总览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        MiniMind 学习路径图                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  【入门阶段】                                                                │
│     ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐          │
│     │ 模块1    │───▶│ 模块2    │───▶│ 模块3    │───▶│ 模块4    │          │
│     │ 模型架构 │    │ 训练技术 │    │ 推理优化 │    │ 模型优化 │          │
│     └──────────┘    └──────────┘    └──────────┘    └──────────┘          │
│           │               │               │               │                │
│           ▼               ▼               ▼               ▼                │
│  【进阶阶段】                                                                │
│     ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐          │
│     │ 模块5    │───▶│ 模块6    │───▶│ 模块7    │───▶│ 模块8    │          │
│     │ 部署实践 │    │ 代码解析 │    │ 问题解决 │    │ 项目实战 │          │
│     └──────────┘    └──────────┘    └──────────┘    └──────────┘          │
│           │               │               │               │                │
│           ▼               ▼               ▼               ▼                │
│  【精通阶段】                                                                │
│     ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐          │
│     │ 模块9    │───▶│ 模块10   │───▶│ 模块11   │───▶│ 模块12   │          │
│     │ 代码质量 │    │ 交互练习 │    │ 调试技巧 │    │ 性能优化 │          │
│     └──────────┘    └──────────┘    └──────────┘    └──────────┘          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 模块详细导航

#### 🟢 入门阶段（模块1-4）

| 模块 | 名称 | 核心内容 | 预计学时 | 难度 |
|------|------|----------|----------|------|
| **模块1** | 模型架构 | Transformer架构、注意力机制、位置编码、RMSNorm、SwiGLU | 8小时 | ⭐⭐ |
| **模块2** | 训练技术 | 混合精度训练、梯度累积、分布式训练、学习率调度 | 6小时 | ⭐⭐⭐ |
| **模块3** | 推理优化 | KV Cache、采样策略、批处理推理、流式生成 | 4小时 | ⭐⭐ |
| **模块4** | 模型优化 | 量化、剪枝、知识蒸馏、模型压缩 | 6小时 | ⭐⭐⭐ |

#### 🟡 进阶阶段（模块5-8）

| 模块 | 名称 | 核心内容 | 预计学时 | 难度 |
|------|------|----------|----------|------|
| **模块5** | 部署实践 | 模型导出、ONNX转换、服务化部署、容器化 | 4小时 | ⭐⭐⭐ |
| **模块6** | 代码解析 | MiniMind源码逐行解析、数据流分析 | 8小时 | ⭐⭐⭐⭐ |
| **模块7** | 问题解决 | FAQ、常见错误处理、调试技巧 | 4小时 | ⭐⭐ |
| **模块8** | 项目实战 | 问答系统、文本分类、情感分析 | 6小时 | ⭐⭐⭐ |

#### 🔴 精通阶段（模块9-12）

| 模块 | 名称 | 核心内容 | 预计学时 | 难度 |
|------|------|----------|----------|------|
| **模块9** | 代码质量 | 编码规范、文档规范、单元测试、持续集成 | 4小时 | ⭐⭐ |
| **模块10** | 交互练习 | 多头注意力、RoPE、SwiGLU、Transformer Block实现 | 8小时 | ⭐⭐⭐⭐ |
| **模块11** | 调试技巧 | NaN/Inf处理、梯度检查、内存分析、性能分析 | 4小时 | ⭐⭐⭐ |
| **模块12** | 性能优化 | 训练加速、推理加速、内存优化、编译优化 | 6小时 | ⭐⭐⭐⭐ |

### 模块内容详解

---

#### 📦 模块1：模型架构

**学习目标**：深入理解Transformer架构的每个组件

**核心知识点**：
```
模块1 知识树
├── 1.1 Transformer基础
│   ├── Decoder-Only架构
│   ├── 自注意力机制
│   └── 前馈神经网络
├── 1.2 注意力机制
│   ├── 多头注意力 (MHA)
│   ├── 分组查询注意力 (GQA)
│   └── Flash Attention
├── 1.3 位置编码
│   ├── 正弦位置编码
│   ├── RoPE旋转位置编码
│   └── ALiBi位置编码
├── 1.4 归一化层
│   ├── LayerNorm
│   ├── RMSNorm
│   └── Pre-Norm vs Post-Norm
└── 1.5 激活函数
    ├── ReLU
    ├── GELU
    └── SwiGLU
```

**对应教程章节**：第1-15部分

---

#### 📦 模块2：训练技术

**学习目标**：掌握高效训练大语言模型的核心技术

**核心知识点**：
```
模块2 知识树
├── 2.1 混合精度训练
│   ├── FP16/BF16训练
│   ├── 损失缩放
│   └── GradScaler
├── 2.2 梯度优化
│   ├── 梯度累积
│   ├── 梯度裁剪
│   └── 梯度检查点
├── 2.3 分布式训练
│   ├── DataParallel
│   ├── DistributedDataParallel
│   └── DeepSpeed
├── 2.4 学习率调度
│   ├── Warmup
│   ├── Cosine Decay
│   └── 学习率 finder
└── 2.5 优化器
    ├── Adam/AdamW
    ├── LAMB
    └── Lion
```

**对应教程章节**：第16-25部分

---

#### 📦 模块3：推理优化

**学习目标**：学习如何高效地进行模型推理

**核心知识点**：
```
模块3 知识树
├── 3.1 KV Cache
│   ├── Cache原理
│   ├── Cache实现
│   └── Cache优化
├── 3.2 采样策略
│   ├── 贪婪解码
│   ├── Top-K采样
│   ├── Top-P采样
│   └── 温度调节
├── 3.3 批处理推理
│   ├── 动态批处理
│   ├── 连续批处理
│   └── Padding优化
└── 3.4 流式生成
    ├── 流式输出
    └── 异步生成
```

**对应教程章节**：第26-32部分

---

#### 📦 模块4：模型优化

**学习目标**：掌握模型压缩和加速技术

**核心知识点**：
```
模块4 知识树
├── 4.1 模型量化
│   ├── 动态量化
│   ├── 静态量化
│   └── GPTQ/AWQ
├── 4.2 模型剪枝
│   ├── 结构化剪枝
│   ├── 非结构化剪枝
│   └── 稀疏注意力
├── 4.3 知识蒸馏
│   ├── 蒸馏原理
│   ├── 蒸馏实现
│   └── 蒸馏策略
└── 4.4 LoRA微调
    ├── LoRA原理
    ├── LoRA实现
    └── QLoRA
```

**对应教程章节**：第33-42部分

---

#### 📦 模块5：部署实践

**学习目标**：学习模型部署和服务化的完整流程

**核心知识点**：
```
模块5 知识树
├── 5.1 模型导出
│   ├── TorchScript
│   ├── ONNX导出
│   └── TensorRT
├── 5.2 服务化部署
│   ├── FastAPI服务
│   ├── gRPC服务
│   └── 模型服务框架
├── 5.3 容器化
│   ├── Docker镜像
│   ├── Kubernetes部署
│   └── 服务编排
└── 5.4 生产优化
    ├── 负载均衡
    ├── 模型缓存
    └── 监控告警
```

**对应教程章节**：第43-50部分

---

#### 📦 模块6：代码解析

**学习目标**：逐行理解MiniMind源代码

**核心知识点**：
```
模块6 知识树
├── 6.1 模型配置解析
│   ├── LMConfig详解
│   └── 参数计算
├── 6.2 核心组件解析
│   ├── RMSNorm源码
│   ├── RoPE源码
│   ├── Attention源码
│   └── SwiGLU源码
├── 6.3 完整模型解析
│   ├── TransformerBlock
│   ├── MiniMindLM
│   └── generate方法
└── 6.4 训练代码解析
    ├── 数据加载
    ├── 训练循环
    └── 评估代码
```

**对应教程章节**：第51-62部分

---

#### 📦 模块7：问题解决

**学习目标**：掌握常见问题的诊断和解决方法

**核心知识点**：
```
模块7 知识树
├── 7.1 常见问题FAQ
│   ├── 架构相关
│   ├── 训练相关
│   └── 推理相关
├── 7.2 错误诊断
│   ├── NaN/Inf问题
│   ├── 梯度问题
│   └── 内存问题
├── 7.3 调试工具
│   ├── PyTorch调试
│   ├── 可视化工具
│   └── 日志分析
└── 7.4 学习检查点
    ├── 知识测验
    └── 实践任务
```

**对应教程章节**：第63-64部分

---

#### 📦 模块8：项目实战

**学习目标**：通过实际项目巩固所学知识

**核心知识点**：
```
模块8 知识树
├── 8.1 问答系统
│   ├── 系统设计
│   ├── 检索模块
│   └── 生成模块
├── 8.2 文本分类
│   ├── 分类架构
│   ├── 情感分析
│   └── 意图识别
├── 8.3 文本生成
│   ├── 对话系统
│   ├── 文本摘要
│   └── 代码生成
└── 8.4 项目最佳实践
    ├── 项目结构
    ├── 代码组织
    └── 测试部署
```

**对应教程章节**：第65部分

---

#### 📦 模块9：代码质量

**学习目标**：编写高质量、可维护的代码

**核心知识点**：
```
模块9 知识树
├── 9.1 编码规范
│   ├── 命名规范
│   ├── 代码风格
│   └── 类型注解
├── 9.2 文档规范
│   ├── Docstring
│   ├── 注释规范
│   └── README编写
├── 9.3 测试规范
│   ├── 单元测试
│   ├── 集成测试
│   └── 测试覆盖率
└── 9.4 持续集成
    ├── CI/CD流程
    ├── 代码检查
    └── 自动化测试
```

**对应教程章节**：第66部分

---

#### 📦 模块10：交互练习

**学习目标**：通过动手实践巩固核心概念

**核心知识点**：
```
模块10 知识树
├── 10.1 注意力练习
│   ├── 多头注意力实现
│   ├── GQA实现
│   └── Flash Attention
├── 10.2 位置编码练习
│   ├── RoPE实现
│   └── 位置编码对比
├── 10.3 激活函数练习
│   ├── SwiGLU实现
│   └── 激活函数对比
├── 10.4 完整组件练习
│   ├── TransformerBlock实现
│   └── 完整模型实现
└── 10.5 生成器练习
    ├── 贪婪解码实现
    ├── Top-K采样实现
    └── Top-P采样实现
```

**对应教程章节**：第67部分

---

#### 📦 模块11：调试技巧

**学习目标**：掌握深度学习调试的核心技能

**核心知识点**：
```
模块11 知识树
├── 11.1 数值调试
│   ├── NaN/Inf诊断
│   ├── 数值稳定性
│   └── 混合精度调试
├── 11.2 梯度调试
│   ├── 梯度检查
│   ├── 梯度裁剪
│   └── 梯度可视化
├── 11.3 内存调试
│   ├── 内存分析
│   ├── 内存泄漏
│   └── 内存优化
└── 11.4 性能分析
    ├── 时间分析
    ├── 瓶颈定位
    └── 优化建议
```

**对应教程章节**：第68部分

---

#### 📦 模块12：性能优化

**学习目标**：最大化模型训练和推理效率

**核心知识点**：
```
模块12 知识树
├── 12.1 训练加速
│   ├── 混合精度训练
│   ├── 梯度累积
│   ├── torch.compile
│   └── 分布式训练
├── 12.2 推理加速
│   ├── 模型量化
│   ├── ONNX优化
│   ├── KV Cache
│   └── 批处理推理
├── 12.3 内存优化
│   ├── 梯度检查点
│   ├── 参数共享
│   └── 激活重计算
└── 12.4 编译优化
    ├── TorchInductor
    ├── CUDA优化
    └── 算子融合
```

**对应教程章节**：第69部分

---

### 学习建议

#### 🎯 入门学习者
1. 按顺序学习模块1-4
2. 每个模块完成后做练习题
3. 理解核心概念后再进入下一模块

#### 🚀 有经验开发者
1. 可跳过模块1-2，直接学习模块3-4
2. 重点学习模块6的代码解析
3. 实践模块8的项目实战

#### 💡 研究人员
1. 深入学习模块4的模型优化
2. 重点研究模块11-12的优化技术
3. 尝试改进和创新

---

## 目录

1. [项目整体架构概览](#1-项目整体架构概览)
2. [配置系统详解 - LMConfig.py](#2-配置系统详解---lmconfigpy)
3. [模型核心组件 - model.py](#3-模型核心组件---modelpy)
   - 3.1 [RMSNorm 归一化层](#31-rmsnorm-归一化层)
   - 3.2 [RoPE 旋转位置编码](#32-rope-旋转位置编码)
   - 3.3 [重复KV头函数 repeat_kv](#33-重复kv头函数-repeat_kv)
   - 3.4 [注意力机制 Attention](#34-注意力机制-attention)
   - 3.5 [前馈神经网络 FeedForward](#35-前馈神经网络-feedforward)
   - 3.6 [混合专家系统 MoE](#36-混合专家系统-moe)
   - 3.7 [Transformer块 MiniMindBlock](#37-transformer块-minimindblock)
   - 3.8 [完整语言模型 MiniMindLM](#38-完整语言模型-minimindlm)
4. [数据处理系统](#4-数据处理系统)
5. [预训练流程](#5-预训练流程)
6. [监督微调 SFT](#6-监督微调-sft)
7. [LoRA微调](#7-lora微调)
8. [DPO强化学习](#8-dpo强化学习)
9. [模型推理](#9-模型推理)

---

## 📖 MiniMind源码导读

### 源码文件结构总览

MiniMind的核心代码非常精简，总共约600行Python代码。以下是源码文件的详细结构：

```
MiniMind 核心源码结构
├── model/model.py (约600行) - 模型核心实现
│   │
│   ├── 第16-50行: RMSNorm类
│   │   └── 均方根层归一化实现
│   │
│   ├── 第53-113行: precompute_pos_cis函数
│   │   └── RoPE位置编码预计算
│   │
│   ├── 第116-139行: apply_rotary_emb函数
│   │   └── 应用旋转位置编码
│   │
│   ├── 第142-165行: repeat_kv函数
│   │   └── KV头复制（GQA支持）
│   │
│   ├── 第168-280行: Attention类
│   │   └── 多头注意力机制实现
│   │
│   ├── 第283-320行: FeedForward类
│   │   └── SwiGLU前馈网络
│   │
│   ├── 第323-380行: MoEGate类
│   │   └── MoE门控网络
│   │
│   ├── 第383-450行: MOEFeedForward类
│   │   └── MoE前馈网络
│   │
│   ├── 第453-500行: MiniMindBlock类
│   │   └── Transformer块
│   │
│   └── 第503-600行: MiniMindLM类
│       └── 完整语言模型
│
├── model/LMConfig.py (约80行) - 模型配置
│   └── LMConfig数据类
│
└── 训练脚本
    ├── 1-pretrain.py - 预训练入口
    ├── 3-full_sft.py - SFT微调入口
    ├── 4-lora_sft.py - LoRA微调入口
    └── 5-dpo_train.py - DPO训练入口
```

### 源码阅读指南

#### 推荐阅读顺序

```
┌─────────────────────────────────────────────────────────────────┐
│                    MiniMind源码阅读路径                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  第一步：理解配置                                                │
│  ┌─────────────┐                                               │
│  │ LMConfig.py │ ──▶ 理解模型参数定义                           │
│  └─────────────┘                                               │
│         │                                                       │
│         ▼                                                       │
│  第二步：理解基础组件                                            │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │  RMSNorm    │ ──▶│    RoPE     │ ──▶│  repeat_kv  │        │
│  │  (16-50行)  │    │  (53-139行) │    │ (142-165行) │        │
│  └─────────────┘    └─────────────┘    └─────────────┘        │
│         │                                                       │
│         ▼                                                       │
│  第三步：理解核心层                                              │
│  ┌─────────────┐    ┌─────────────┐                            │
│  │  Attention  │ ──▶│ FeedForward │                            │
│  │ (168-280行) │    │ (283-320行) │                            │
│  └─────────────┘    └─────────────┘                            │
│         │                                                       │
│         ▼                                                       │
│  第四步：理解完整模型                                            │
│  ┌─────────────┐    ┌─────────────┐                            │
│  │MiniMindBlock│ ──▶│ MiniMindLM  │                            │
│  │ (453-500行) │    │ (503-600行) │                            │
│  └─────────────┘    └─────────────┘                            │
│         │                                                       │
│         ▼                                                       │
│  第五步：理解训练流程                                            │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │ 1-pretrain  │ ──▶│  3-full_sft │ ──▶│ 4-lora_sft  │        │
│  └─────────────┘    └─────────────┘    └─────────────┘        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 源码与教程章节对应表

| 源码位置 | 教程章节 | 核心内容 |
|----------|----------|----------|
| `model.py 16-50行` | 3.1 RMSNorm | 均方根层归一化 |
| `model.py 53-113行` | 3.2 RoPE | 旋转位置编码预计算 |
| `model.py 116-139行` | 3.2 RoPE | 应用旋转位置编码 |
| `model.py 142-165行` | 3.3 repeat_kv | KV头复制函数 |
| `model.py 168-280行` | 3.4 Attention | 多头注意力机制 |
| `model.py 283-320行` | 3.5 FeedForward | SwiGLU前馈网络 |
| `model.py 323-450行` | 3.6 MoE | 混合专家系统 |
| `model.py 453-500行` | 3.7 MiniMindBlock | Transformer块 |
| `model.py 503-600行` | 3.8 MiniMindLM | 完整语言模型 |
| `LMConfig.py` | 第2章 | 模型配置类 |
| `1-pretrain.py` | 第5章 | 预训练流程 |
| `3-full_sft.py` | 第6章 | 监督微调 |
| `4-lora_sft.py` | 第7章 | LoRA微调 |

### MiniMind设计决策解析

#### 为什么选择这些技术？

| 技术选择 | 原因 | 源码体现 |
|----------|------|----------|
| **RMSNorm** | 比LayerNorm快30-40%，参数更少 | `model.py 16-50行` |
| **RoPE** | 支持相对位置，外推能力强 | `model.py 53-139行` |
| **GQA** | 减少KV Cache显存占用75% | `model.py 142-165行` |
| **SwiGLU** | 比标准FFN效果更好 | `model.py 283-320行` |
| **Pre-Norm** | 训练更稳定 | `model.py 453-500行` |
| **Flash Attention** | 显存占用O(N)而非O(N²) | `model.py 168-280行` |

#### 模型参数量计算

```python
# MiniMind参数量计算公式
def calculate_params(dim, n_layers, vocab_size, n_heads, n_kv_heads, use_moe=False):
    """
    计算MiniMind模型的参数量
    
    参数:
        dim: 隐藏维度
        n_layers: 层数
        vocab_size: 词汇表大小
        n_heads: 查询头数
        n_kv_heads: KV头数
        use_moe: 是否使用MoE
    """
    # 嵌入层参数
    embed_params = vocab_size * dim
    
    # 每层参数
    # 1. 注意力层
    head_dim = dim // n_heads
    # Q投影: dim * dim
    # K投影: dim * (head_dim * n_kv_heads) 
    # V投影: dim * (head_dim * n_kv_heads)
    # O投影: dim * dim
    attn_params = dim * dim * 2 + dim * head_dim * n_kv_heads * 2
    
    # 2. FFN层 (SwiGLU)
    hidden_dim = int(dim * 4 / 3)
    hidden_dim = ((hidden_dim + 255) // 256) * 256  # 对齐到256
    ffn_params = dim * hidden_dim * 3  # w1, w2, w3
    
    # 3. RMSNorm (每层2个)
    norm_params = dim * 2
    
    # 单层总参数
    layer_params = attn_params + ffn_params + norm_params
    
    # 总参数
    total_params = embed_params + n_layers * layer_params + dim  # 最后的norm
    
    return total_params

# 示例：计算minimind-v1-small的参数量
params = calculate_params(dim=512, n_layers=8, vocab_size=6400, n_heads=8, n_kv_heads=2)
print(f"参数量: {params:,}")  # 约26M参数
```

### 源码调试技巧

```python
# 在MiniMind源码中添加调试输出

# 1. 在Attention类中添加形状跟踪
class Attention(nn.Module):
    def forward(self, x, pos_cis, kv_cache=None):
        # 调试：打印输入形状
        # print(f"[Attention] input shape: {x.shape}")
        
        bsz, seqlen, _ = x.shape
        # ... 原有代码 ...
        
        # 调试：打印注意力权重范围
        # print(f"[Attention] scores range: [{scores.min():.4f}, {scores.max():.4f}]")

# 2. 在MiniMindBlock中添加残差检查
class MiniMindBlock(nn.Module):
    def forward(self, x, pos_cis, kv_cache=None):
        # 调试：检查残差连接前的值
        residual = x
        x = self.attention(self.norm1(x), pos_cis, kv_cache)
        # if torch.isnan(x).any():
        #     print(f"[Warning] NaN detected after attention")
        x = residual + x
        # ... 继续调试 ...
```

---

## 1. 项目整体架构概览

MiniMind是一个从零开始训练的超小型语言模型项目，其核心设计理念是"大道至简"。项目采用经典的Transformer Decoder-Only架构，与GPT、LLaMA等主流大模型保持一致的设计思路。

### 1.1 项目目录结构

```
minimind/
├── model/                          # 模型定义目录
│   ├── model.py                    # 核心模型实现
│   ├── LMConfig.py                 # 模型配置类
│   └── minimind_tokenizer/         # 分词器目录
│
├── dataset/                        # 数据集目录
│   ├── pretrain_hq.jsonl          # 预训练数据
│   ├── sft_mini_512.jsonl         # SFT微调数据
│   └── dpo_data.jsonl             # DPO训练数据
│
├── trainer/                        # 训练脚本目录
│   ├── train_pretrain.py          # 预训练脚本
│   ├── train_full_sft.py          # 全参微调脚本
│   ├── train_lora_sft.py          # LoRA微调脚本
│   └── train_dpo.py               # DPO训练脚本
│
├── out/                            # 训练输出目录
│   ├── pretrain_512.pth           # 预训练权重
│   └── full_sft_512.pth           # 微调权重
│
├── 1-pretrain.py                   # 预训练入口
├── 3-full_sft.py                   # SFT微调入口
├── 4-lora_sft.py                   # LoRA微调入口
├── 5-dpo_train.py                  # DPO训练入口
└── 2-eval.py                       # 模型评估入口
```

### 1.2 核心技术栈

MiniMind采用了多项现代大语言模型的核心技术：

| 技术组件 | 说明 | 来源 |
|---------|------|------|
| RMSNorm | 均方根层归一化 | LLaMA |
| RoPE | 旋转位置编码 | LLaMA |
| GQA | 分组查询注意力 | LLaMA 2 |
| SwiGLU | 门控线性单元激活 | LLaMA |
| Flash Attention | 高效注意力计算 | Flash Attention 2 |
| MoE | 混合专家系统 | DeepSeek-V2 |

### 1.3 模型参数规模

MiniMind提供了三个版本的模型：

| 模型版本 | 参数量 | 层数 | 隐藏维度 | 注意力头数 | KV头数 |
|---------|--------|------|----------|-----------|--------|
| minimind-v1-small | 26M | 8 | 512 | 8 | 2 |
| minimind-v1-moe | 4×26M | 8 | 512 | 8 | 2 |
| minimind-v1 | 108M | 8 | 768 | 8 | 2 |

---

## 2. 配置系统详解 - LMConfig.py

配置文件是整个模型的"蓝图"，定义了模型的所有超参数。让我们深入分析每一行代码。

### 2.1 完整配置类代码

```python
"""
LMConfig.py - MiniMind模型配置类
这个文件定义了MiniMind模型的所有超参数配置
"""

from dataclasses import dataclass
from typing import Optional
import math


@dataclass
class LMConfig:
    """
    MiniMind语言模型配置类
    
    使用Python的dataclass装饰器，自动生成__init__、__repr__等方法
    所有参数都有默认值，可以直接实例化使用默认配置
    """
    
    # ==================== 基础模型参数 ====================
    
    # 模型隐藏层维度
    # 这是最核心的参数，决定了模型的大部分参数量
    # 计算公式：参数量 ≈ 12 × dim² × n_layers
    # dim=512 时，8层模型约26M参数
    dim: int = 512
    
    # Transformer层数
    # 更多的层数意味着模型可以学习更复杂的特征层次
    # 通常8-12层对于小型模型已经足够
    n_layers: int = 8
    
    # 注意力头数
    # 多头注意力允许模型同时关注不同位置的信息
    # 头数必须能整除dim，每个头的维度 = dim / n_heads
    n_heads: int = 8
    
    # KV头数（用于GQA分组查询注意力）
    # 当n_kv_heads < n_heads时，启用GQA
    # 例如：n_heads=8, n_kv_heads=2 表示8个Q头共享2组KV头
    # 这可以大幅减少推理时的KV缓存显存占用
    n_kv_heads: int = 2
    
    # 词汇表大小
    # MiniMind使用自定义分词器，词汇表大小为6400
    # 比GPT-2的50257小很多，有助于减少参数量
    vocab_size: int = 6400
    
    # ==================== FFN前馈网络参数 ====================
    
    # FFN隐藏层维度
    # 如果为None，会自动计算为 hidden_dim = 4 * dim
    # 但实际会调整为multiple_of的倍数
    hidden_dim: int = None
    
    # 隐藏维度对齐倍数
    # 为了GPU计算效率，隐藏维度会对齐到这个值的倍数
    # 通常设置为64，因为GPU的Tensor Core以64为单位计算
    multiple_of: int = 64
    
    # ==================== 归一化参数 ====================
    
    # RMSNorm的epsilon值
    # 防止除零错误，通常设置为1e-5或1e-6
    norm_eps: float = 1e-5
    
    # ==================== 序列长度参数 ====================
    
    # 最大序列长度
    # 训练时支持的最大token数量
    # 512是小型模型的常见选择，可通过RoPE外推扩展
    max_seq_len: int = 8192
    
    # ==================== RoPE位置编码参数 ====================
    
    # RoPE的theta参数（基数）
    # 控制位置编码的频率范围
    # 1e6是LLaMA的默认值，更大的值支持更长的外推
    rope_theta: int = 1e6
    
    # ==================== 正则化参数 ====================
    
    # Dropout比率
    # 训练时随机丢弃神经元的比例，防止过拟合
    # 小模型通常使用较小的dropout或不使用
    dropout: float = 0.0
    
    # ==================== Flash Attention参数 ====================
    
    # 是否使用Flash Attention
    # Flash Attention是一种高效的注意力计算实现
    # 可以显著减少显存占用并加速计算
    flash_attn: bool = True
    
    # ==================== MoE混合专家参数 ====================
    
    # 是否启用混合专家模型
    # MoE可以在不增加推理计算量的情况下增加模型容量
    use_moe: bool = False
    
    # 每个token激活的专家数量
    # 通常设置为2，即每个token通过2个专家处理
    num_experts_per_tok: int = 2
    
    # 路由专家总数
    # 总共有多少个专家可供选择
    # 例如4表示有4个专家，每个token选择其中2个
    n_routed_experts: int = 4
    
    # 是否使用共享专家
    # 共享专家对所有token都激活，用于处理通用特征
    # 通常设置1个共享专家
    n_shared_experts: bool = True
    
    # 专家选择的评分函数
    # 'softmax'：使用softmax归一化分数
    # 'sigmoid'：使用sigmoid函数
    scoring_func: str = 'softmax'
    
    # MoE辅助损失权重
    # 用于平衡各专家的负载
    # 通常设置为0.1
    aux_loss_alpha: float = 0.1
    
    # 是否使用序列级辅助损失
    # 序列级损失可以更好地平衡专家负载
    seq_aux: bool = True
    
    # 是否归一化top-k概率
    # 归一化可以使专家输出更稳定
    norm_topk_prob: bool = True
    
    def __post_init__(self):
        """
        初始化后处理
        在dataclass自动生成的__init__之后调用
        用于计算派生参数和验证参数有效性
        """
        # 计算每个注意力头的维度
        # 例如：dim=512, n_heads=8 -> head_dim=64
        self.head_dim = self.dim // self.n_heads
        
        # 计算FFN隐藏层维度
        if self.hidden_dim is None:
            # 默认使用4倍隐藏维度
            hidden_dim = 4 * self.dim
            # 调整为multiple_of的倍数，提高GPU计算效率
            # 公式：向上取整到multiple_of的倍数
            self.hidden_dim = int(2 * hidden_dim / 3)
            self.hidden_dim = self.multiple_of * (
                (self.hidden_dim + self.multiple_of - 1) // self.multiple_of
            )
        
        # 验证参数有效性
        assert self.dim % self.n_heads == 0, \
            f"dim ({self.dim}) 必须能被 n_heads ({self.n_heads}) 整除"
        assert self.n_heads % self.n_kv_heads == 0, \
            f"n_heads ({self.n_heads}) 必须能被 n_kv_heads ({self.n_kv_heads}) 整除"
```

### 2.2 参数详解与计算公式

#### 2.2.1 模型参数量计算

MiniMind的参数量可以通过以下公式估算：

```
总参数量 = 嵌入层参数 + 注意力层参数 + FFN层参数 + 输出层参数

嵌入层参数 = vocab_size × dim
输出层参数 = vocab_size × dim（与嵌入层共享权重）

单层注意力参数 = 4 × dim × dim
  - Q投影: dim × dim
  - K投影: dim × dim (实际为 dim × (dim/n_heads × n_kv_heads))
  - V投影: dim × dim
  - 输出投影: dim × dim

单层FFN参数 = 3 × dim × hidden_dim
  - 门控投影1: dim × hidden_dim
  - 门控投影2: dim × hidden_dim
  - 下投影: hidden_dim × dim

总参数量 ≈ vocab_size × dim + n_layers × (4 × dim² + 3 × dim × hidden_dim)
```

以dim=512, n_layers=8, vocab_size=6400为例：

```
嵌入层: 6400 × 512 = 3,276,800
单层注意力: 4 × 512 × 512 = 1,048,576
单层FFN: 3 × 512 × 1408 = 2,158,592
8层总计: 8 × (1,048,576 + 2,158,592) = 25,657,344

总计约: 3,276,800 + 25,657,344 ≈ 29M 参数
```

#### 2.2.2 显存占用估算

训练时的显存占用包括：

```
模型参数显存 = 参数量 × 4字节 (float32) 或 2字节 (float16/bfloat16)
梯度显存 = 参数量 × 4字节
优化器状态 = 参数量 × 8字节 (AdamW需要存储一阶和二阶动量)
激活值显存 ≈ batch_size × seq_len × dim × n_layers × 20字节

总计 ≈ 参数量 × 16字节 + 激活值显存
```

对于26M参数的模型：
- 模型参数：26M × 2字节 = 52MB (bfloat16)
- 梯度：26M × 2字节 = 52MB
- 优化器状态：26M × 8字节 = 208MB
- 总计约：312MB + 激活值

---

## 3. 模型核心组件 - model.py

这是MiniMind最核心的文件，包含了模型的所有组件实现。我们将逐行分析每个类和函数。

### 3.1 RMSNorm 归一化层

RMSNorm（Root Mean Square Layer Normalization）是现代大语言模型的标准归一化方法，相比传统的LayerNorm更加高效。

#### 3.1.1 完整代码实现

```python
"""
RMSNorm - 均方根层归一化
位置：model/model.py 第16-50行
"""

import torch
import torch.nn as nn
import math


class RMSNorm(nn.Module):
    """
    RMSNorm归一化层
    
    与LayerNorm的区别：
    - LayerNorm: y = (x - mean) / sqrt(var + eps) * weight + bias
    - RMSNorm:   y = x / sqrt(mean(x^2) + eps) * weight
    
    RMSNorm省去了均值计算，计算量减少约30-40%
    同时不需要bias参数，参数量也略有减少
    
    数学公式：
        RMS(x) = sqrt(1/n * Σx_i² + eps)
        y = x / RMS(x) * weight
    """
    
    def __init__(self, dim: int, eps: float = 1e-6):
        """
        初始化RMSNorm层
        
        参数:
            dim: 输入特征的维度
            eps: 防止除零的小常数，默认1e-6
        """
        super().__init__()
        
        # 可学习的缩放参数
        # 初始化为全1，训练过程中会学习到最优值
        self.weight = nn.Parameter(torch.ones(dim))
        
        # 防止除零的epsilon
        self.eps = eps
        
        # 存储维度信息，用于后续计算
        self.dim = dim
    
    def _norm(self, x: torch.Tensor) -> torch.Tensor:
        """
        执行RMS归一化计算
        
        这是核心计算函数，实现了RMSNorm的数学公式
        
        参数:
            x: 输入张量，形状为 (..., dim)
            
        返回:
            归一化后的张量，形状与输入相同
            
        计算步骤:
            1. 计算平方: x.pow(2) -> x²
            2. 计算均值: mean(-1) -> 1/n * Σx_i²
            3. 加eps: + eps -> 防止除零
            4. 开平方根: rsqrt -> 1/sqrt(...)
            5. 乘以原值: * -> 归一化
        """
        # 计算RMS (Root Mean Square)
        # x.pow(2): 对每个元素求平方
        # mean(-1, keepdim=True): 在最后一个维度上求均值，保持维度
        # rsqrt: 计算平方根的倒数，即 1/sqrt(x)
        # 整体公式: 1/sqrt(mean(x²) + eps)
        
        # 为什么使用rsqrt而不是sqrt然后除？
        # 因为rsqrt是单次操作，比先sqrt再除法更高效
        
        # 为什么keepdim=True？
        # 保持维度可以自动广播，避免手动reshape
        
        return x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + self.eps)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        前向传播
        
        参数:
            x: 输入张量，形状为 (batch_size, seq_len, dim)
               或其他任意形状，只要最后一维是dim
               
        返回:
            归一化并缩放后的张量，形状与输入相同
            
        计算流程:
            1. 将输入转为float32进行精确计算
            2. 执行RMS归一化
            3. 转回原数据类型
            4. 乘以可学习的权重参数
        """
        # 为什么先转为float32再计算？
        # 因为归一化涉及除法和开方，float16精度不够可能导致数值不稳定
        # 计算完成后再转回原类型，不影响整体精度
        
        # self._norm(x.float()): 在float32精度下计算归一化
        # .type_as(x): 转回输入的数据类型（如bfloat16）
        # self.weight: 应用可学习的缩放参数
        
        return self.weight * self._norm(x.float()).type_as(x)
    
    def extra_repr(self) -> str:
        """
        返回额外的字符串表示，用于print(model)时显示
        """
        return f'dim={self.dim}, eps={self.eps}'


# ==================== RMSNorm vs LayerNorm 对比 ====================

class LayerNorm(nn.Module):
    """
    传统的LayerNorm实现，用于对比
    
    LayerNorm的数学公式：
        mean = 1/n * Σx_i
        var = 1/n * Σ(x_i - mean)²
        y = (x - mean) / sqrt(var + eps) * weight + bias
    """
    
    def __init__(self, dim: int, eps: float = 1e-6):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(dim))
        self.bias = nn.Parameter(torch.zeros(dim))  # RMSNorm没有这个
        self.eps = eps
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # 计算均值和方差
        mean = x.mean(-1, keepdim=True)
        var = x.var(-1, keepdim=True, unbiased=False)
        
        # 归一化
        x_norm = (x - mean) / torch.sqrt(var + self.eps)
        
        # 缩放和平移
        return self.weight * x_norm + self.bias


# ==================== 为什么选择RMSNorm ====================

"""
RMSNorm的优势：

1. 计算效率
   - LayerNorm需要计算均值和方差：2次统计计算
   - RMSNorm只需要计算均方根：1次统计计算
   - 计算量减少约30-40%

2. 内存效率
   - LayerNorm需要存储mean和var用于反向传播
   - RMSNorm只需要存储平方均值
   - 内存占用更少

3. 参数量
   - LayerNorm: weight + bias = 2 * dim
   - RMSNorm: weight = dim
   - 参数量减半

4. GPU友好
   - RMSNorm的计算模式更适合GPU并行
   - 可以更好地利用Tensor Core

5. 实践效果
   - 在大语言模型上，RMSNorm与LayerNorm效果相当
   - LLaMA、Falcon、Mistral等模型都采用RMSNorm

为什么RMSNorm可以省去均值？
- 理论上，均值中心化对归一化效果影响不大
- RMSNorm直接对尺度进行归一化，已经足够稳定训练
- 实验表明，去掉均值计算对模型性能影响很小
"""
```

#### 3.1.2 数值示例

```python
# RMSNorm计算示例
import torch

# 创建示例输入
x = torch.tensor([[1.0, 2.0, 3.0, 4.0]])

# 计算RMS
rms = torch.sqrt(torch.mean(x.pow(2), dim=-1, keepdim=True))
# rms = sqrt((1+4+9+16)/4) = sqrt(7.5) ≈ 2.739

# 归一化
x_norm = x / rms
# x_norm ≈ [0.365, 0.730, 1.095, 1.461]

# 应用权重
weight = torch.ones(4)
output = weight * x_norm
# output ≈ [0.365, 0.730, 1.095, 1.461]
```

---

### 3.2 RoPE 旋转位置编码

RoPE（Rotary Position Embeddings）是现代大语言模型的标准位置编码方法，它通过复数旋转的方式将位置信息注入到注意力计算中。

#### 3.2.1 完整代码实现

```python
"""
RoPE - 旋转位置编码
位置：model/model.py 第53-113行
"""

import torch
import torch.nn as nn
from typing import Optional, Tuple


def precompute_pos_cis(
    dim: int, 
    end: int = int(32 * 1024), 
    theta: float = 1e6
) -> torch.Tensor:
    """
    预计算旋转位置编码所需的复数值
    
    这是RoPE的核心预计算函数，在模型初始化时调用一次，
    生成所有位置的位置编码，避免每次前向传播时重复计算。
    
    参数:
        dim: 每个注意力头的维度（不是总维度）
             例如：dim=512, n_heads=8 -> head_dim=64
        end: 最大序列长度，默认32K
             这是位置编码支持的最大token数量
        theta: RoPE的基数，控制频率范围
               默认1e6，更大的值支持更长的外推
    
    返回:
        pos_cis: 复数张量，形状为 (end, dim//2)
                 每个位置对应一个复数向量
                 
    数学原理:
        RoPE的核心思想是使用复数旋转来编码位置
        
        对于位置m和维度d，旋转角度为：
            θ_{m,d} = m * θ_d
        其中 θ_d = 1 / (theta^(2d/dim))
        
        这个角度对应复数：
            e^(i*θ) = cos(θ) + i*sin(θ)
        
        将位置编码应用到查询q和键k上：
            q' = q * e^(i*θ_m)
            k' = k * e^(i*θ_n)
        
        这样注意力分数变为：
            q' · k' = q · k * e^(i*(θ_m - θ_n))
        
        这就自然地引入了相对位置信息 (m-n)
    """
    # 步骤1：计算不同维度的频率
    # 公式：freq_i = 1 / (theta^(2i/dim))
    # torch.arange(0, dim, 2)：生成 [0, 2, 4, ..., dim-2]
    # 这是因为每个频率对应两个维度（复数的实部和虚部）
    
    freqs = 1.0 / (theta ** (torch.arange(0, dim, 2)[: (dim // 2)].float() / dim))
    # freqs形状：(dim//2,)
    # 例如dim=64时，freqs形状为(32,)
    # freqs的值从大到小，对应不同频率的位置编码
    
    # 步骤2：生成位置索引
    # torch.arange(end)：生成 [0, 1, 2, ..., end-1]
    # 每个位置都有一个唯一的位置编码
    
    t = torch.arange(end, device=freqs.device)
    # t形状：(end,)
    
    # 步骤3：计算外积得到每个位置对应的每个频率
    # torch.outer：计算外积
    # freqs = t ⊗ freqs
    # 结果形状：(end, dim//2)
    # freqs[m, d] = m * freq_d
    
    freqs = torch.outer(t, freqs).float()
    
    # 步骤4：使用欧拉公式生成复数
    # 欧拉公式：e^(i*θ) = cos(θ) + i*sin(θ)
    # torch.polar(abs, angle)：生成复数张量
    # abs=1：复数的模为1（单位圆上的点）
    # angle=freqs：旋转角度
    
    pos_cis = torch.polar(torch.ones_like(freqs), freqs)
    # pos_cis形状：(end, dim//2)
    # 类型：complex64
    
    return pos_cis


def apply_rotary_emb(
    xq: torch.Tensor, 
    xk: torch.Tensor, 
    pos_cis: torch.Tensor
) -> Tuple[torch.Tensor, torch.Tensor]:
    """
    将旋转位置编码应用到查询和键上
    
    这是RoPE的核心应用函数，在每个注意力层的前向传播中调用。
    
    参数:
        xq: 查询张量，形状为 (batch_size, seq_len, n_heads, head_dim)
        xk: 键张量，形状为 (batch_size, seq_len, n_kv_heads, head_dim)
        pos_cis: 预计算的位置编码，形状为 (seq_len, head_dim//2)
        
    返回:
        xq_out: 应用位置编码后的查询
        xk_out: 应用位置编码后的键
        
    数学原理:
        将实数向量视为复数向量，然后乘以位置编码的复数
        
        例如，对于向量 [a, b, c, d]：
        1. 重塑为复数形式：[(a+bi), (c+di)]
        2. 乘以位置编码：[(a+bi)*e^(iθ1), (c+di)*e^(iθ2)]
        3. 展开回实数形式
        
        复数乘法：
        (a+bi) * (cos(θ)+i*sin(θ)) 
        = a*cos(θ) - b*sin(θ) + i*(a*sin(θ) + b*cos(θ))
        
        这等价于旋转矩阵变换：
        [cos(θ)  -sin(θ)] [a]
        [sin(θ)   cos(θ)] [b]
    """
    # 步骤1：获取位置编码的设备信息，确保在同一设备上
    # 同时将pos_cis扩展到与xq相同的批次和头数
    
    # pos_cis的形状需要与xq匹配
    # 原始形状：(seq_len, head_dim//2)
    # 需要扩展为：(batch_size, seq_len, n_heads, head_dim//2)
    
    # 使用广播机制，只需要在适当位置添加维度
    # pos_cis: (seq_len, head_dim//2) -> (1, seq_len, 1, head_dim//2)
    pos_cis = pos_cis.unsqueeze(0).unsqueeze(2)
    
    # 步骤2：将实数张量转换为复数形式
    # xq形状：(batch_size, seq_len, n_heads, head_dim)
    # 重塑为：(batch_size, seq_len, n_heads, head_dim//2, 2)
    # 最后一个维度2表示实部和虚部
    
    xq_ = torch.view_as_complex(xq.float().reshape(*xq.shape[:-1], -1, 2))
    xk_ = torch.view_as_complex(xk.float().reshape(*xk.shape[:-1], -1, 2))
    # xq_形状：(batch_size, seq_len, n_heads, head_dim//2)
    # 类型：complex64
    
    # 步骤3：在复数域中应用旋转（乘以pos_cis）
    # 复数乘法会自动广播
    
    xq_out = torch.view_as_real(xq_ * pos_cis).flatten(3)
    xk_out = torch.view_as_real(xk_ * pos_cis).flatten(3)
    # xq_out形状：(batch_size, seq_len, n_heads, head_dim)
    # 类型：float（实数）
    
    # 步骤4：转回原数据类型
    return xq_out.type_as(xq), xk_out.type_as(xk)


# ==================== RoPE 详解 ====================

"""
为什么RoPE如此重要？

1. 相对位置感知
   - 绝对位置编码：直接将位置信息加到嵌入上
   - RoPE：通过旋转编码相对位置
   
   在注意力计算中：
   q_m · k_n = |q| |k| cos(angle(q) - angle(k) + (m-n)*θ)
   
   可以看到，注意力分数自然地包含了相对位置信息(m-n)

2. 长度外推能力
   - 传统位置编码：训练长度外的位置没有编码
   - RoPE：可以通过插值等方法扩展到更长的序列
   
   例如：训练时max_seq_len=512，推理时可以处理2048甚至更长

3. 计算效率
   - 不需要额外的位置嵌入矩阵
   - 位置编码直接融入Q、K的计算中
   - 内存占用更少

4. 数学优雅
   - 利用复数旋转的几何性质
   - 相邻位置的相对距离由旋转角度决定
   - 理论基础扎实

RoPE vs 其他位置编码：

| 方法 | 外推能力 | 计算复杂度 | 显存占用 | 相对位置 |
|------|---------|-----------|---------|---------|
| Sin/Cos | 差 | O(1) | 少 | 否 |
| Learnable | 差 | O(1) | 少 | 否 |
| Relative | 中 | O(n²) | 多 | 是 |
| ALiBi | 好 | O(1) | 少 | 是 |
| RoPE | 优秀 | O(1) | 少 | 是 |
"""
```

#### 3.2.2 RoPE可视化理解

```python
"""
RoPE的直观理解

想象一个二维平面上的向量旋转：
- 位置0：向量旋转0度
- 位置1：向量旋转θ度
- 位置2：向量旋转2θ度
- ...

两个向量的点积会包含它们旋转角度的差值：
- 位置m和位置n的向量点积包含(m-n)θ的信息
- 这就是相对位置信息

对于高维向量，我们在不同的维度对上使用不同的旋转频率：
- 低维度对：使用低频旋转（变化慢）
- 高维度对：使用高频旋转（变化快）

这样可以在不同尺度上捕获位置信息。
"""

import numpy as np
import matplotlib.pyplot as plt

def visualize_rope():
    """可视化RoPE的旋转效果"""
    
    # 设置参数
    dim = 64  # 头维度
    theta = 1e4  # 基数
    
    # 计算频率
    freqs = 1.0 / (theta ** (np.arange(0, dim, 2) / dim))
    
    # 绘制不同维度的频率
    plt.figure(figsize=(12, 4))
    
    plt.subplot(1, 2, 1)
    plt.plot(freqs)
    plt.xlabel('Dimension Pair')
    plt.ylabel('Frequency')
    plt.title('RoPE Frequency per Dimension')
    plt.yscale('log')
    
    # 绘制不同位置的旋转角度
    positions = np.arange(0, 512)
    angles = np.outer(positions, freqs)
    
    plt.subplot(1, 2, 2)
    plt.imshow(angles[:100, :].T, aspect='auto', cmap='viridis')
    plt.xlabel('Position')
    plt.ylabel('Dimension Pair')
    plt.title('Rotation Angles (first 100 positions)')
    plt.colorbar(label='Angle (radians)')
    
    plt.tight_layout()
    plt.show()
```

---

### 3.3 重复KV头函数 repeat_kv

这个函数是GQA（分组查询注意力）的关键组件，用于将KV头复制以匹配Q头的数量。

```python
"""
repeat_kv - 重复KV头以匹配Q头数量
位置：model/model.py 第116-139行
"""

import torch


def repeat_kv(x: torch.Tensor, n_rep: int) -> torch.Tensor:
    """
    将KV头重复n_rep次以匹配Q头数量
    
    这是GQA（Grouped-Query Attention）的核心函数。
    在GQA中，Q的头数是KV头数的整数倍，需要在计算时将KV头复制。
    
    参数:
        x: 输入张量，形状为 (batch_size, seq_len, n_kv_heads, head_dim)
           这是K或V的张量
        n_rep: 重复次数
           = n_heads / n_kv_heads
           例如：n_heads=8, n_kv_heads=2 -> n_rep=4
           
    返回:
        扩展后的张量，形状为 (batch_size, seq_len, n_heads, head_dim)
        
    示例:
        输入: x.shape = (2, 10, 2, 64), n_rep = 4
        输出: shape = (2, 10, 8, 64)
        
        原来的2个KV头，每个被复制4次，变成8个头
        
    为什么需要这个函数？
        - GQA中，Q有8个头，但K和V只有2个头
        - 计算注意力时，需要让每个Q头都有对应的K和V头
        - 解决方案：将2个KV头各复制4次，得到8个头
        
    与直接expand的区别：
        - expand只是创建视图，不占用额外内存
        - 但后续操作可能需要连续内存
        - reshape确保内存布局正确
    """
    # 如果n_rep=1，说明是标准MHA，不需要复制
    if n_rep == 1:
        return x
    
    # 获取输入形状
    bs, slen, n_kv_heads, head_dim = x.shape
    
    # 步骤1：添加一个新维度用于扩展
    # x[:, :, :, None, :] 形状变为 (bs, slen, n_kv_heads, 1, head_dim)
    # None相当于unsqueeze，在指定位置添加一个大小为1的维度
    
    # 步骤2：扩展这个维度
    # .expand(bs, slen, n_kv_heads, n_rep, head_dim)
    # 将第4维从1扩展到n_rep
    # 注意：expand不实际复制数据，只是创建一个视图
    
    # 步骤3：重塑形状
    # .reshape(bs, slen, n_kv_heads * n_rep, head_dim)
    # 将最后两个维度合并
    # 形状变为 (bs, slen, n_heads, head_dim)
    
    return (
        x[:, :, :, None, :]
        .expand(bs, slen, n_kv_heads, n_rep, head_dim)
        .reshape(bs, slen, n_kv_heads * n_rep, head_dim)
    )


# ==================== GQA 详解 ====================

"""
GQA（Grouped-Query Attention）详解

传统MHA（Multi-Head Attention）：
- Q、K、V都有n个头
- 每个Q头与对应的K、V头计算注意力
- 问题：推理时需要缓存所有KV头，显存占用大

MQA（Multi-Query Attention）：
- Q有n个头，K和V只有1个头
- 所有Q头共享同一组KV
- 优点：KV缓存减少到1/n
- 缺点：性能略有下降

GQA（Grouped-Query Attention）：
- Q有n个头，K和V有g个头（g < n，且n能被g整除）
- 每组Q头共享一组KV
- 优点：在MHA和MQA之间取得平衡
- 缺点：实现稍复杂

示例：
假设 n_heads=8, n_kv_heads=2

MHA: Q=8头, K=8头, V=8头 -> KV缓存 = 8 × seq_len × head_dim
GQA: Q=8头, K=2头, V=2头 -> KV缓存 = 2 × seq_len × head_dim (减少75%)
MQA: Q=8头, K=1头, V=1头 -> KV缓存 = 1 × seq_len × head_dim (减少87.5%)

GQA的实现流程：
1. 输入token经过投影得到Q、K、V
2. Q的形状：(batch, seq, 8, head_dim)
3. K的形状：(batch, seq, 2, head_dim)
4. V的形状：(batch, seq, 2, head_dim)
5. 调用repeat_kv将K、V复制：
   - K: (batch, seq, 2, head_dim) -> (batch, seq, 8, head_dim)
   - V: (batch, seq, 2, head_dim) -> (batch, seq, 8, head_dim)
6. 现在可以正常计算注意力了

性能对比：
| 方法 | KV缓存 | 推理速度 | 模型质量 |
|------|--------|---------|---------|
| MHA  | 100%   | 基准    | 基准    |
| GQA  | 25%    | 快      | 略降    |
| MQA  | 12.5%  | 最快    | 较降    |

MiniMind选择GQA的原因：
1. 显著减少推理时的KV缓存
2. 相比MQA，性能损失更小
3. 与LLaMA 2保持一致的设计
"""
```

---

### 3.4 注意力机制 Attention

注意力机制是Transformer的核心组件，MiniMind实现了高效的分组查询注意力（GQA）并支持Flash Attention。

```python
"""
Attention - 注意力机制实现
位置：model/model.py 第142-280行
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional, Tuple
import math


class Attention(nn.Module):
    """
    分组查询注意力（Grouped-Query Attention, GQA）
    
    这是MiniMind的核心注意力实现，支持：
    1. GQA：Q头数多于KV头数，减少KV缓存
    2. Flash Attention 2：高效的注意力计算
    3. KV缓存：支持增量推理
    4. RoPE：旋转位置编码
    
    数学公式：
        Attention(Q, K, V) = softmax(QK^T / sqrt(d_k)) * V
        
    其中：
        Q = X * W_q  (查询投影)
        K = X * W_k  (键投影)
        V = X * W_v  (值投影)
    """
    
    def __init__(self, args):
        """
        初始化注意力层
        
        参数:
            args: LMConfig配置对象，包含：
                - dim: 隐藏维度
                - n_heads: 查询头数
                - n_kv_heads: KV头数
                - head_dim: 每个头的维度
                - dropout: dropout比率
                - flash_attn: 是否使用Flash Attention
        """
        super().__init__()
        
        # 存储配置
        self.n_heads = args.n_heads  # Q的总头数
        self.head_dim = args.head_dim  # 每个头的维度
        
        # GQA配置
        # n_kv_heads: K和V的头数
        # 如果n_kv_heads < n_heads，启用GQA
        # 如果n_kv_heads == n_heads，退化为标准MHA
        # 如果n_kv_heads == 1，退化为MQA
        self.n_kv_heads = args.n_kv_heads if args.n_kv_heads is not None else args.n_heads
        
        # 计算每个KV头对应的Q头数
        # 例如：n_heads=8, n_kv_heads=2 -> n_rep=4
        # 表示每个KV头被4个Q头共享
        self.n_rep = self.n_heads // self.n_kv_heads
        
        # 投影层定义
        
        # Q投影：将输入投影到n_heads个头
        # 输出维度 = n_heads * head_dim = dim
        self.wq = nn.Linear(args.dim, self.n_heads * self.head_dim, bias=False)
        
        # K投影：将输入投影到n_kv_heads个头
        # 注意：输出维度可能小于dim
        # 例如：dim=512, n_heads=8, n_kv_heads=2
        # wq输出：512, wk输出：128
        self.wk = nn.Linear(args.dim, self.n_kv_heads * self.head_dim, bias=False)
        
        # V投影：与K投影类似
        self.wv = nn.Linear(args.dim, self.n_kv_heads * self.head_dim, bias=False)
        
        # 输出投影：将多头注意力的结果投影回原始维度
        self.wo = nn.Linear(self.n_heads * self.head_dim, args.dim, bias=False)
        
        # Dropout层
        self.dropout = nn.Dropout(args.dropout)
        
        # 是否使用Flash Attention
        self.flash = args.flash_attn and hasattr(F, 'scaled_dot_product_attention')
        
        # 注意力缩放因子
        # 1/sqrt(head_dim) 用于缩放点积，防止梯度消失
        self.scale = 1.0 / math.sqrt(self.head_dim)
    
    def forward(
        self,
        x: torch.Tensor,
        pos_cis: torch.Tensor,
        past_key_value: Optional[Tuple[torch.Tensor, torch.Tensor]] = None,
        use_cache: bool = False
    ) -> Tuple[torch.Tensor, Optional[Tuple[torch.Tensor, torch.Tensor]]]:
        """
        前向传播
        
        参数:
            x: 输入张量，形状为 (batch_size, seq_len, dim)
            pos_cis: RoPE位置编码，形状为 (seq_len, head_dim//2)
            past_key_value: 之前的KV缓存，用于增量推理
                - past_key: (batch, past_seq_len, n_kv_heads, head_dim)
                - past_value: 同上
            use_cache: 是否返回KV缓存
            
        返回:
            output: 注意力输出，形状为 (batch_size, seq_len, dim)
            past_kv: 如果use_cache=True，返回当前的KV缓存
            
        计算流程:
            1. 线性投影得到Q、K、V
            2. 应用RoPE位置编码到Q和K
            3. 如果有KV缓存，拼接历史KV
            4. 重复KV头以匹配Q头数量（GQA）
            5. 计算注意力分数
            6. 应用softmax和dropout
            7. 加权求和得到输出
            8. 输出投影
        """
        # 获取输入形状
        bs, seqlen, _ = x.shape
        
        # ==================== 步骤1：线性投影 ====================
        
        # Q投影：(bs, seqlen, dim) -> (bs, seqlen, n_heads * head_dim)
        xq = self.wq(x)
        # K投影：(bs, seqlen, dim) -> (bs, seqlen, n_kv_heads * head_dim)
        xk = self.wk(x)
        # V投影：(bs, seqlen, dim) -> (bs, seqlen, n_kv_heads * head_dim)
        xv = self.wv(x)
        
        # 重塑为多头形式
        # Q: (bs, seqlen, n_heads * head_dim) -> (bs, seqlen, n_heads, head_dim)
        xq = xq.view(bs, seqlen, self.n_heads, self.head_dim)
        # K: (bs, seqlen, n_kv_heads * head_dim) -> (bs, seqlen, n_kv_heads, head_dim)
        xk = xk.view(bs, seqlen, self.n_kv_heads, self.head_dim)
        # V: 同K
        xv = xv.view(bs, seqlen, self.n_kv_heads, self.head_dim)
        
        # ==================== 步骤2：应用RoPE ====================
        
        # RoPE只应用于Q和K，不应用于V
        # 因为位置信息通过Q和K的点积传递
        xq, xk = apply_rotary_emb(xq, xk, pos_cis)
        
        # ==================== 步骤3：处理KV缓存 ====================
        
        # 如果有历史KV缓存，将当前KV拼接到历史KV后面
        if past_key_value is not None:
            # past_key_value是一个元组 (past_k, past_v)
            past_k, past_v = past_key_value
            # 拼接：cat([past, current], dim=1) 在序列维度上拼接
            xk = torch.cat([past_k, xk], dim=1)
            xv = torch.cat([past_v, xv], dim=1)
        
        # 保存当前的KV用于返回
        past_kv = (xk, xv) if use_cache else None
        
        # ==================== 步骤4：重复KV头（GQA核心） ====================
        
        # 转置以适应注意力计算的形状
        # Q: (bs, seqlen, n_heads, head_dim) -> (bs, n_heads, seqlen, head_dim)
        xq = xq.transpose(1, 2)
        
        # K和V需要先重复头，再转置
        # repeat_kv: (bs, seqlen, n_kv_heads, head_dim) -> (bs, seqlen, n_heads, head_dim)
        # transpose: (bs, seqlen, n_heads, head_dim) -> (bs, n_heads, seqlen, head_dim)
        xk = repeat_kv(xk, self.n_rep).transpose(1, 2)
        xv = repeat_kv(xv, self.n_rep).transpose(1, 2)
        
        # ==================== 步骤5：计算注意力 ====================
        
        if self.flash:
            # 使用Flash Attention（推荐）
            # Flash Attention是一种IO感知的精确注意力算法
            # 显著减少内存访问，加速计算并减少显存占用
            
            # scaled_dot_product_attention自动处理：
            # 1. QK^T点积
            # 2. 缩放（除以sqrt(head_dim)）
            # 3. 可选的mask（causal mask）
            # 4. softmax
            # 5. 与V加权
            
            # causal=True：应用因果掩码，确保只能看到之前的位置
            output = F.scaled_dot_product_attention(
                xq, xk, xv,
                attn_mask=None,  # 使用is_causal参数代替
                dropout_p=self.dropout.p if self.training else 0.0,
                is_causal=True  # 因果注意力
            )
        else:
            # 手动实现注意力计算
            # 用于不支持Flash Attention的环境
            
            # 计算注意力分数：QK^T
            # (bs, n_heads, seqlen, head_dim) @ (bs, n_heads, head_dim, kvlen)
            # -> (bs, n_heads, seqlen, kvlen)
            scores = torch.matmul(xq, xk.transpose(-2, -1)) * self.scale
            
            # 创建因果掩码
            # 因果掩码确保位置i只能看到位置0到i的信息
            # 使用上三角矩阵的负无穷来mask掉未来位置
            seqlen_q = xq.shape[2]
            seqlen_k = xk.shape[2]
            
            # 创建掩码：上三角为-inf，下三角和对角线为0
            mask = torch.triu(
                torch.full((seqlen_q, seqlen_k), float('-inf'), device=x.device),
                diagonal=1
            )
            
            # 应用掩码
            scores = scores + mask
            
            # Softmax归一化
            scores = F.softmax(scores, dim=-1)
            
            # Dropout
            scores = self.dropout(scores)
            
            # 加权求和：scores @ V
            # (bs, n_heads, seqlen, kvlen) @ (bs, n_heads, kvlen, head_dim)
            # -> (bs, n_heads, seqlen, head_dim)
            output = torch.matmul(scores, xv)
        
        # ==================== 步骤6：输出处理 ====================
        
        # 转置回来：(bs, n_heads, seqlen, head_dim) -> (bs, seqlen, n_heads, head_dim)
        output = output.transpose(1, 2)
        
        # 展平多头：(bs, seqlen, n_heads, head_dim) -> (bs, seqlen, n_heads * head_dim)
        output = output.contiguous().view(bs, seqlen, -1)
        
        # 输出投影：(bs, seqlen, n_heads * head_dim) -> (bs, seqlen, dim)
        output = self.wo(output)
        
        return output, past_kv


# ==================== 注意力机制详解 ====================

"""
注意力机制的核心概念

1. 为什么需要注意力？
   - 传统RNN处理序列时，信息需要逐步传递
   - 长距离依赖难以捕获
   - 注意力机制允许每个位置直接访问所有其他位置

2. 自注意力（Self-Attention）
   - Q、K、V都来自同一个输入
   - 每个token可以"查询"其他所有token
   - 通过注意力权重聚合信息

3. 多头注意力（Multi-Head Attention）
   - 不同的头关注不同的信息
   - 例如：有的头关注语法，有的头关注语义
   - 最后将所有头的信息融合

4. 因果掩码（Causal Mask）
   - 语言模型只能看到之前的内容
   - 掩码确保位置i不能看到位置i+1及之后
   - 实现方式：将未来位置的注意力分数设为负无穷

5. KV缓存（KV Cache）
   - 推理时逐个生成token
   - 之前计算过的K和V可以缓存起来
   - 避免重复计算，加速推理

注意力计算复杂度分析：
- 时间复杂度：O(n² × d)
  - n是序列长度
  - d是头维度
  - n²来自QK^T的计算
  
- 空间复杂度：O(n² + n × d)
  - n²存储注意力分数矩阵
  - n × d存储Q、K、V

Flash Attention优化：
- 将注意力计算分块进行
- 减少HBM（高带宽内存）访问次数
- 计算复杂度不变，但IO复杂度从O(n²)降到O(n)
- 显存占用从O(n²)降到O(n)
"""
```

---

### 3.5 前馈神经网络 FeedForward

前馈神经网络（FFN）是Transformer中注意力层之后的组件，用于增加模型的非线性表达能力。

```python
"""
FeedForward - 前馈神经网络
位置：model/model.py 第283-320行
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class FeedForward(nn.Module):
    """
    SwiGLU前馈神经网络
    
    MiniMind采用SwiGLU激活函数，这是现代LLM的标准选择。
    相比传统的ReLU FFN，SwiGLU有更好的性能。
    
    传统FFN：
        FFN(x) = ReLU(xW1 + b1)W2 + b2
        
    SwiGLU FFN：
        FFN(x) = (Swish(xW_gate) ⊙ xW_up)W_down
        
    其中：
        - Swish(x) = x * sigmoid(x)
        - ⊙ 表示逐元素乘法
        - W_gate, W_up, W_down 是三个独立的权重矩阵
    
    参数量对比：
        传统FFN: 2 × dim × hidden_dim
        SwiGLU: 3 × dim × hidden_dim
        
    虽然参数量增加50%，但性能提升显著。
    """
    
    def __init__(self, dim: int, hidden_dim: int, multiple_of: int, dropout: float = 0.0):
        """
        初始化FeedForward层
        
        参数:
            dim: 输入/输出维度
            hidden_dim: 隐藏层维度
            multiple_of: 隐藏维度对齐倍数
            dropout: dropout比率
        """
        super().__init__()
        
        # 调整hidden_dim为multiple_of的倍数
        # 这是为了GPU计算效率
        # 公式：向上取整到multiple_of的倍数
        hidden_dim = multiple_of * ((hidden_dim + multiple_of - 1) // multiple_of)
        
        # 门控投影（gate projection）
        # 用于生成门控信号
        self.w1 = nn.Linear(dim, hidden_dim, bias=False)
        
        # 上投影（up projection）
        # 用于增加维度
        self.w2 = nn.Linear(hidden_dim, dim, bias=False)
        
        # 下投影（down projection）
        # 用于恢复维度
        # 注意：这里使用w3命名，与w1、w2区分
        self.w3 = nn.Linear(dim, hidden_dim, bias=False)
        
        # Dropout层
        self.dropout = nn.Dropout(dropout)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        前向传播
        
        参数:
            x: 输入张量，形状为 (batch_size, seq_len, dim)
            
        返回:
            输出张量，形状与输入相同
            
        计算流程:
            1. 计算门控信号: gate = SiLU(w1(x))
            2. 计算上投影值: up = w3(x)
            3. 门控融合: hidden = gate ⊙ up
            4. 下投影: out = w2(hidden)
            5. Dropout: out = dropout(out)
        """
        # SwiGLU计算
        # w1(x): 门控分支，使用SiLU激活
        # w3(x): 值分支，不使用激活
        # 两者逐元素相乘，实现门控机制
        
        # SiLU(x) = x * sigmoid(x)，也称为Swish
        # 相比ReLU，SiLU是平滑的，有负值输出
        # 这有助于梯度流动和模型性能
        
        return self.dropout(self.w2(F.silu(self.w1(x)) * self.w3(x)))


# ==================== SwiGLU 详解 ====================

"""
SwiGLU激活函数详解

1. GLU（Gated Linear Unit）
   GLU(x) = (xW1) ⊙ sigmoid(xW2)
   
   门控机制允许网络选择性地传递信息
   类似于LSTM中的门

2. SwiGLU = Swish + GLU
   SwiGLU(x) = Swish(xW_gate) ⊙ (xW_up)
   
   其中 Swish(x) = x * sigmoid(x)

3. 为什么SwiGLU更好？
   - 平滑性：Swish是平滑函数，梯度流动更好
   - 非单调性：允许负值输出，增加表达能力
   - 门控机制：选择性传递信息
   - 实验验证：在多个任务上优于ReLU和GeLU

4. 与其他激活函数对比

   | 激活函数 | 公式 | 平滑 | 负值 |
   |---------|------|------|------|
   | ReLU | max(0, x) | 否 | 否 |
   | GeLU | x * Φ(x) | 是 | 是 |
   | Swish | x * σ(x) | 是 | 是 |
   | SwiGLU | Swish(x) ⊙ y | 是 | 是 |

5. 计算图示

   输入 x
     │
     ├──> W_gate ──> Swish ──┐
     │                        │
     └──> W_up ──────────────>⊙ ──> W_down ──> 输出
                              │
                           门控融合

FFN的作用：
1. 增加非线性：注意力机制本身是线性的
2. 增加模型容量：隐藏层维度通常是输入的4倍
3. 特征变换：学习更复杂的特征表示
"""
```

---

### 3.6 混合专家系统 MoE

混合专家系统（Mixture of Experts, MoE）是一种在保持推理计算量不变的情况下增加模型参数量的技术。

```python
"""
MoE - 混合专家系统
位置：model/model.py 第323-450行
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Tuple


class MoEGate(nn.Module):
    """
    MoE门控网络
    
    负责为每个token选择最合适的专家。
    门控网络是一个简单的线性层，输出每个专家的选择概率。
    
    工作流程：
        1. 输入token的隐藏状态
        2. 计算每个专家的分数
        3. 选择top-k个专家
        4. 归一化权重
    """
    
    def __init__(self, config):
        """
        初始化MoE门控
        
        参数:
            config: LMConfig配置对象，包含：
                - dim: 隐藏维度
                - n_routed_experts: 路由专家数量
                - num_experts_per_tok: 每个token激活的专家数
                - scoring_func: 评分函数类型
                - aux_loss_alpha: 辅助损失权重
                - seq_aux: 是否使用序列级辅助损失
                - norm_topk_prob: 是否归一化top-k概率
        """
        super().__init__()
        
        self.dim = config.dim
        self.top_k = config.num_experts_per_tok
        self.n_routed_experts = config.n_routed_experts
        
        # 门控权重
        # 将隐藏状态映射到专家数量维度
        self.weight = nn.Parameter(torch.empty((self.n_routed_experts, self.dim)))
        
        # 评分函数
        self.scoring_func = config.scoring_func
        
        # 辅助损失参数
        self.aux_loss_alpha = config.aux_loss_alpha
        self.seq_aux = config.seq_aux
        
        # 是否归一化top-k概率
        self.norm_topk_prob = config.norm_topk_prob
        
        # 初始化权重
        nn.init.kaiming_uniform_(self.weight, a=math.sqrt(5))
    
    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        前向传播
        
        参数:
            x: 输入张量，形状为 (batch_size, seq_len, dim)
            
        返回:
            topk_idx: 选中的专家索引，形状为 (batch_size * seq_len, top_k)
            topk_weight: 专家权重，形状为 (batch_size * seq_len, top_k)
            aux_loss: 辅助损失，标量
            
        计算流程:
            1. 计算每个token对每个专家的分数
            2. 选择top-k个专家
            3. 归一化权重
            4. 计算辅助损失（用于负载均衡）
        """
        # 展平批次和序列维度
        # (batch_size, seq_len, dim) -> (batch_size * seq_len, dim)
        batch_size, seq_len, dim = x.shape
        x_flat = x.view(-1, dim)
        
        # 计算专家分数
        # (batch_size * seq_len, dim) @ (dim, n_experts)
        # -> (batch_size * seq_len, n_experts)
        scores = F.linear(x_flat, self.weight)
        
        # 应用评分函数
        if self.scoring_func == 'softmax':
            scores = F.softmax(scores, dim=-1)
        elif self.scoring_func == 'sigmoid':
            scores = torch.sigmoid(scores)
        else:
            raise ValueError(f"Unknown scoring function: {self.scoring_func}")
        
        # 选择top-k专家
        topk_scores, topk_idx = torch.topk(scores, self.top_k, dim=-1)
        
        # 归一化top-k权重
        if self.norm_topk_prob:
            topk_scores = topk_scores / topk_scores.sum(dim=-1, keepdim=True)
        
        # 计算辅助损失
        # 辅助损失用于确保所有专家被均匀使用
        # 避免某些专家过载而其他专家闲置
        aux_loss = None
        if self.training and self.aux_loss_alpha > 0:
            # 计算每个专家被选中的频率
            # 这需要统计所有token的选择情况
            aux_loss = self._compute_aux_loss(scores, topk_idx)
        
        return topk_idx, topk_scores, aux_loss
    
    def _compute_aux_loss(self, scores: torch.Tensor, topk_idx: torch.Tensor) -> torch.Tensor:
        """
        计算辅助损失
        
        辅助损失鼓励所有专家被均匀使用。
        
        公式：
            aux_loss = α * n * Σ(f_i * P_i)
            
        其中：
            f_i = 专家i被选中的频率
            P_i = 专家i的平均分数
            n = 专家数量
            α = 损失权重
        """
        # 计算每个专家被选中的频率
        # one_hot编码
        expert_mask = F.one_hot(topk_idx, self.n_routed_experts).float()
        # 求和得到每个专家被选中的次数
        expert_freq = expert_mask.sum(dim=(0, 1)) / expert_mask.numel()
        
        # 计算每个专家的平均分数
        expert_score = scores.mean(dim=0)
        
        # 辅助损失
        aux_loss = self.aux_loss_alpha * self.n_routed_experts * (expert_freq * expert_score).sum()
        
        return aux_loss


class MOEFeedForward(nn.Module):
    """
    MoE前馈神经网络
    
    将多个专家网络组合在一起，通过门控机制选择性地激活专家。
    
    结构：
        - 路由专家：多个独立的FeedForward网络
        - 共享专家：对所有token都激活的专家
        - 门控网络：决定每个token使用哪些路由专家
    """
    
    def __init__(self, config):
        """
        初始化MoE FFN
        
        参数:
            config: LMConfig配置对象
        """
        super().__init__()
        
        self.dim = config.dim
        self.hidden_dim = config.hidden_dim
        self.n_routed_experts = config.n_routed_experts
        self.n_shared_experts = config.n_shared_experts
        self.top_k = config.num_experts_per_tok
        
        # 路由专家
        # 每个专家都是一个独立的FeedForward网络
        self.experts = nn.ModuleList([
            FeedForward(config.dim, config.hidden_dim, config.multiple_of)
            for _ in range(self.n_routed_experts)
        ])
        
        # 共享专家
        # 这些专家对所有token都激活
        if self.n_shared_experts > 0:
            self.shared_experts = nn.ModuleList([
                FeedForward(config.dim, config.hidden_dim, config.multiple_of)
                for _ in range(self.n_shared_experts)
            ])
        
        # 门控网络
        self.gate = MoEGate(config)
        
        # 辅助损失
        self.aux_loss = 0.0
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        前向传播
        
        参数:
            x: 输入张量，形状为 (batch_size, seq_len, dim)
            
        返回:
            输出张量，形状与输入相同
            
        计算流程:
            1. 门控网络选择专家
            2. 计算路由专家输出
            3. 计算共享专家输出
            4. 加权融合所有输出
        """
        batch_size, seq_len, dim = x.shape
        
        # 门控选择
        topk_idx, topk_weight, aux_loss = self.gate(x)
        self.aux_loss = aux_loss if aux_loss is not None else 0.0
        
        # 展平输入
        x_flat = x.view(-1, dim)
        
        # 初始化输出
        output = torch.zeros_like(x_flat)
        
        # 计算路由专家输出
        # 对每个专家单独处理
        for expert_idx in range(self.n_routed_experts):
            # 找到选择了这个专家的token
            mask = (topk_idx == expert_idx).any(dim=-1)
            
            if mask.any():
                # 获取这些token
                expert_input = x_flat[mask]
                
                # 通过专家网络
                expert_output = self.experts[expert_idx](expert_input)
                
                # 获取这些token对该专家的权重
                expert_weight = topk_weight[mask]
                if topk_idx[mask].shape[1] > 1:
                    # 如果选择了多个专家，找到当前专家的权重
                    expert_mask = (topk_idx[mask] == expert_idx)
                    expert_weight = (topk_weight[mask] * expert_mask).sum(dim=-1, keepdim=True)
                
                # 加权累加
                output[mask] += expert_output * expert_weight
        
        # 计算共享专家输出
        if self.n_shared_experts > 0:
            shared_output = torch.zeros_like(x_flat)
            for shared_expert in self.shared_experts:
                shared_output += shared_expert(x_flat)
            shared_output = shared_output / self.n_shared_experts
            output = output + shared_output
        
        # 恢复形状
        output = output.view(batch_size, seq_len, dim)
        
        return output


# ==================== MoE 详解 ====================

"""
MoE（混合专家系统）详解

1. 核心思想
   - 将一个大网络分解为多个小网络（专家）
   - 每次只激活部分专家
   - 参数量增加，但计算量不变

2. 为什么MoE有效？
   - 不同专家可以学习不同类型的知识
   - 例如：有的专家擅长语法，有的擅长常识
   - 门控网络学会将不同的输入路由到合适的专家

3. MoE vs Dense

   Dense模型：
   - 所有参数每次都参与计算
   - 参数量 = 计算量
   
   MoE模型：
   - 只有部分参数参与计算
   - 参数量 > 计算量
   - 可以在相同计算预算下增加模型容量

4. 负载均衡问题
   - 如果某些专家总是被选中，其他专家就浪费了
   - 辅助损失鼓励均匀使用所有专家
   - 这是MoE训练的关键

5. 共享专家
   - 共享专家对所有token都激活
   - 用于处理通用特征
   - 路由专家处理特定特征

6. MiniMind的MoE配置
   - 4个路由专家 + 1个共享专家
   - 每个token激活2个路由专家 + 1个共享专家
   - 参数量约4倍，计算量约3倍
"""
```

---

### 3.7 Transformer块 MiniMindBlock

MiniMindBlock是Transformer的基本构建块，包含注意力层、前馈网络和归一化层。

```python
"""
MiniMindBlock - Transformer块
位置：model/model.py 第453-500行
"""

import torch
import torch.nn as nn


class MiniMindBlock(nn.Module):
    """
    MiniMind Transformer块
    
    这是Transformer的基本构建块，包含：
    1. 自注意力层（Self-Attention）
    2. 前馈神经网络（FFN或MoE）
    3. 两个RMSNorm归一化层
    
    架构采用Pre-Norm设计：
        x = x + Attention(RMSNorm(x))
        x = x + FFN(RMSNorm(x))
    
    相比Post-Norm：
        x = RMSNorm(x + Attention(x))
        x = RMSNorm(x + FFN(x))
    
    Pre-Norm的优势：
    - 训练更稳定
    - 梯度流动更好
    - 不需要warm-up
    """
    
    def __init__(self, layer_id: int, config):
        """
        初始化Transformer块
        
        参数:
            layer_id: 层索引，用于某些特殊操作
            config: LMConfig配置对象
        """
        super().__init__()
        
        # 注意力层
        self.attention = Attention(config)
        
        # 前馈网络
        # 根据配置选择普通FFN或MoE FFN
        if config.use_moe:
            self.feed_forward = MOEFeedForward(config)
        else:
            self.feed_forward = FeedForward(
                config.dim, 
                config.hidden_dim, 
                config.multiple_of,
                config.dropout
            )
        
        # 归一化层
        # 使用RMSNorm替代LayerNorm
        self.attention_norm = RMSNorm(config.dim, eps=config.norm_eps)
        self.ffn_norm = RMSNorm(config.dim, eps=config.norm_eps)
        
        # 层ID
        self.layer_id = layer_id
    
    def forward(
        self,
        x: torch.Tensor,
        pos_cis: torch.Tensor,
        past_key_value: Optional[Tuple[torch.Tensor, torch.Tensor]] = None,
        use_cache: bool = False
    ) -> Tuple[torch.Tensor, Optional[Tuple[torch.Tensor, torch.Tensor]]]:
        """
        前向传播
        
        参数:
            x: 输入张量，形状为 (batch_size, seq_len, dim)
            pos_cis: RoPE位置编码
            past_key_value: KV缓存
            use_cache: 是否返回KV缓存
            
        返回:
            output: 输出张量
            past_kv: KV缓存（如果use_cache=True）
            
        计算流程:
            1. 注意力残差连接
               h = x + Attention(RMSNorm(x))
            2. FFN残差连接
               out = h + FFN(RMSNorm(h))
        """
        # 注意力子层
        # Pre-Norm: 先归一化，再计算注意力
        # 残差连接：将输入加到注意力输出上
        attn_output, past_kv = self.attention(
            self.attention_norm(x),
            pos_cis,
            past_key_value,
            use_cache
        )
        h = x + attn_output
        
        # FFN子层
        # 同样使用Pre-Norm和残差连接
        ffn_output = self.feed_forward(self.ffn_norm(h))
        out = h + ffn_output
        
        return out, past_kv


# ==================== Transformer块详解 ====================

"""
Transformer块的设计选择

1. Pre-Norm vs Post-Norm

   Pre-Norm（MiniMind使用）：
   ```
   x = x + Attention(LayerNorm(x))
   x = x + FFN(LayerNorm(x))
   ```
   
   Post-Norm（原始Transformer）：
   ```
   x = LayerNorm(x + Attention(x))
   x = LayerNorm(x + FFN(x))
   ```
   
   Pre-Norm优势：
   - 梯度直接通过残差连接流动
   - 不需要学习率warm-up
   - 训练更稳定
   - 深层网络效果更好

2. 残差连接的作用
   - 缓解梯度消失
   - 允许训练更深的网络
   - 每层只需学习残差（增量信息）

3. 归一化的位置
   - Pre-Norm：在子层之前归一化
   - 保证子层输入的稳定性
   - 残差连接传递原始信息

4. 层数的选择
   - MiniMind使用8层
   - 更多层可以学习更复杂的特征
   - 但也增加计算量和过拟合风险
   - 小模型通常8-12层足够
"""
```

---

### 3.8 完整语言模型 MiniMindLM

MiniMindLM是完整的语言模型类，将所有组件组装在一起。

```python
"""
MiniMindLM - 完整语言模型
位置：model/model.py 第503-600行
"""

import torch
import torch.nn as nn
from typing import Optional, List, Tuple
from transformers import PreTrainedModel
from dataclasses import dataclass


@dataclass
class CausalLMOutputWithPast:
    """
    模型输出数据类
    
    包含：
    - logits: 预测的下一个token概率分布
    - past_key_values: KV缓存
    - aux_loss: MoE辅助损失
    """
    logits: torch.Tensor = None
    past_key_values: Optional[Tuple[Tuple[torch.Tensor, torch.Tensor]]] = None
    aux_loss: Optional[torch.Tensor] = None


class MiniMindLM(PreTrainedModel):
    """
    MiniMind语言模型
    
    完整的Decoder-Only Transformer语言模型。
    继承自HuggingFace的PreTrainedModel，便于与transformers库集成。
    
    架构组成：
    1. Token嵌入层：将token ID转换为向量
    2. Dropout层：正则化
    3. 多个Transformer块：核心计算
    4. 最终归一化层
    5. 输出层：预测下一个token
    
    特点：
    - 权重共享：嵌入层和输出层共享权重
    - RoPE预计算：在初始化时预计算位置编码
    - 支持KV缓存：加速推理
    """
    
    config_class = LMConfig  # 配置类
    
    def __init__(self, params: LMConfig = None):
        """
        初始化MiniMind模型
        
        参数:
            params: LMConfig配置对象
        """
        # 调用父类初始化
        self.params = params or LMConfig()
        super().__init__(self.params)
        
        # 保存配置
        self.vocab_size = params.vocab_size
        self.n_layers = params.n_layers
        
        # Token嵌入层
        # 将token ID（整数）映射为向量
        # 输入：(batch_size, seq_len) 的整数tensor
        # 输出：(batch_size, seq_len, dim) 的向量tensor
        self.tok_embeddings = nn.Embedding(params.vocab_size, params.dim)
        
        # Dropout层
        # 在嵌入后应用，防止过拟合
        self.dropout = nn.Dropout(params.dropout)
        
        # Transformer块列表
        # 使用nn.ModuleList管理多个块
        # 每个块是独立的，可以有不同的参数
        self.layers = nn.ModuleList([
            MiniMindBlock(l, params) for l in range(self.n_layers)
        ])
        
        # 最终归一化层
        # 在输出层之前应用
        self.norm = RMSNorm(params.dim, eps=params.norm_eps)
        
        # 输出层（语言模型头）
        # 将隐藏状态映射到词汇表大小的logits
        # bias=False：不使用偏置，减少参数
        self.output = nn.Linear(params.dim, params.vocab_size, bias=False)
        
        # 权重共享
        # 嵌入层和输出层共享权重
        # 这可以减少参数量，并提高模型性能
        # 原理：输入和输出都表示token，应该在同一空间
        self.tok_embeddings.weight = self.output.weight
        
        # 预计算RoPE位置编码
        # 在模型初始化时一次性计算，避免每次前向传播重复计算
        # register_buffer：注册为模型状态的一部分，但不参与训练
        # persistent=False：不保存到checkpoint中
        self.register_buffer(
            "pos_cis",
            precompute_pos_cis(
                dim=params.dim // params.n_heads,  # 每个头的维度
                theta=params.rope_theta
            ),
            persistent=False
        )
        
        # 输出对象
        self.OUT = CausalLMOutputWithPast()
        
        # 初始化权重
        self.apply(self._init_weights)
    
    def _init_weights(self, module):
        """
        权重初始化
        
        使用正态分布初始化线性层和嵌入层
        标准差 = 1/sqrt(dim)
        """
        if isinstance(module, nn.Linear):
            torch.nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if module.bias is not None:
                torch.nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            torch.nn.init.normal_(module.weight, mean=0.0, std=0.02)
    
    def forward(
        self,
        input_ids: Optional[torch.Tensor] = None,
        past_key_values: Optional[List[Tuple[torch.Tensor, torch.Tensor]]] = None,
        use_cache: bool = False,
        **kwargs
    ) -> CausalLMOutputWithPast:
        """
        前向传播
        
        参数:
            input_ids: 输入token ID，形状为 (batch_size, seq_len)
            past_key_values: 之前计算的KV缓存
            use_cache: 是否返回当前的KV缓存
            
        返回:
            CausalLMOutputWithPast对象，包含：
            - logits: 预测的下一个token概率分布
            - past_key_values: KV缓存
            - aux_loss: MoE辅助损失
            
        计算流程:
            1. Token嵌入
            2. Dropout
            3. 获取位置编码
            4. 逐层通过Transformer块
            5. 最终归一化
            6. 输出层预测
        """
        # 获取输入形状
        batch_size, seq_len = input_ids.shape
        
        # 如果没有提供KV缓存，初始化为None列表
        past_key_values = past_key_values or [None] * len(self.layers)
        
        # 获取起始位置
        # 如果有KV缓存，起始位置是缓存的长度
        start_pos = kwargs.get('start_pos', 0)
        
        # ==================== 步骤1：Token嵌入 ====================
        
        # 将token ID转换为向量
        # (batch_size, seq_len) -> (batch_size, seq_len, dim)
        h = self.tok_embeddings(input_ids)
        
        # 应用Dropout
        h = self.dropout(h)
        
        # ==================== 步骤2：获取位置编码 ====================
        
        # 从预计算的位置编码中切片获取当前序列的位置编码
        # pos_cis形状：(max_seq_len, head_dim//2)
        # 切片后：(seq_len, head_dim//2)
        pos_cis = self.pos_cis[start_pos:start_pos + seq_len]
        
        # ==================== 步骤3：Transformer层 ====================
        
        # 存储每层的KV缓存
        past_kvs = []
        
        # 逐层处理
        for l, layer in enumerate(self.layers):
            # 通过Transformer块
            # h: 隐藏状态
            # pos_cis: 位置编码
            # past_key_values[l]: 该层的KV缓存
            # use_cache: 是否返回KV缓存
            h, past_kv = layer(
                h,
                pos_cis,
                past_key_value=past_key_values[l],
                use_cache=use_cache
            )
            past_kvs.append(past_kv)
        
        # ==================== 步骤4：输出预测 ====================
        
        # 最终归一化
        h = self.norm(h)
        
        # 输出层：预测下一个token
        # (batch_size, seq_len, dim) -> (batch_size, seq_len, vocab_size)
        logits = self.output(h)
        
        # ==================== 步骤5：计算辅助损失 ====================
        
        # 如果使用MoE，累加所有层的辅助损失
        aux_loss = sum(
            l.feed_forward.aux_loss 
            for l in self.layers 
            if hasattr(l.feed_forward, 'aux_loss')
        )
        
        # 设置输出
        self.OUT.logits = logits
        self.OUT.past_key_values = past_kvs if use_cache else None
        self.OUT.aux_loss = aux_loss if aux_loss != 0 else None
        
        return self.OUT
    
    @torch.no_grad()
    def generate(
        self,
        input_ids: torch.Tensor,
        max_new_tokens: int = 100,
        temperature: float = 1.0,
        top_k: int = 50,
        top_p: float = 0.9
    ) -> torch.Tensor:
        """
        文本生成
        
        参数:
            input_ids: 输入token ID
            max_new_tokens: 最大生成token数
            temperature: 温度参数，控制随机性
            top_k: top-k采样参数
            top_p: nucleus采样参数
            
        返回:
            生成的token序列
        """
        # 初始化KV缓存
        past_key_values = None
        
        for _ in range(max_new_tokens):
            # 前向传播
            outputs = self.forward(
                input_ids if past_key_values is None else input_ids[:, -1:],
                past_key_values=past_key_values,
                use_cache=True
            )
            
            # 获取最后一个位置的logits
            logits = outputs.logits[:, -1, :]
            
            # 应用温度
            logits = logits / temperature
            
            # Top-k采样
            if top_k > 0:
                v, _ = torch.topk(logits, min(top_k, logits.size(-1)))
                logits[logits < v[:, [-1]]] = float('-inf')
            
            # Top-p (nucleus) 采样
            if top_p < 1.0:
                sorted_logits, sorted_indices = torch.sort(logits, descending=True)
                cumulative_probs = torch.cumsum(F.softmax(sorted_logits, dim=-1), dim=-1)
                
                # 移除累积概率超过top_p的token
                sorted_indices_to_remove = cumulative_probs > top_p
                sorted_indices_to_remove[..., 1:] = sorted_indices_to_remove[..., :-1].clone()
                sorted_indices_to_remove[..., 0] = 0
                
                indices_to_remove = sorted_indices_to_remove.scatter(1, sorted_indices, sorted_indices_to_remove)
                logits[indices_to_remove] = float('-inf')
            
            # 采样下一个token
            probs = F.softmax(logits, dim=-1)
            next_token = torch.multinomial(probs, num_samples=1)
            
            # 拼接到输入
            input_ids = torch.cat([input_ids, next_token], dim=-1)
            
            # 更新KV缓存
            past_key_values = outputs.past_key_values
        
        return input_ids


# ==================== 模型整体架构总结 ====================

"""
MiniMind模型整体架构

输入: token ID序列
  │
  ▼
┌─────────────────────────────────────────────────────────────┐
│                    Token Embedding                           │
│              (vocab_size, dim) -> (seq_len, dim)             │
└─────────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────────┐
│                      Dropout                                 │
└─────────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────────┐
│                  Transformer Block × N                       │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                   RMSNorm                                ││
│  └─────────────────────────────────────────────────────────┘│
│                        │                                     │
│                        ▼                                     │
│  ┌─────────────────────────────────────────────────────────┐│
│  │            Attention (GQA + RoPE)                        ││
│  │   ┌─────────────────────────────────────────────────┐   ││
│  │   │ Q, K, V Projection                               │   ││
│  │   │ RoPE Position Encoding                           │   ││
│  │   │ KV Cache (optional)                              │   ││
│  │   │ Multi-Head Attention                             │   ││
│  │   │ Output Projection                                │   ││
│  │   └─────────────────────────────────────────────────┘   ││
│  └─────────────────────────────────────────────────────────┘│
│                        │                                     │
│              ┌─────────┴─────────┐                          │
│              │    Residual Add    │                          │
│              └─────────┬─────────┘                          │
│                        │                                     │
│                        ▼                                     │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                   RMSNorm                                ││
│  └─────────────────────────────────────────────────────────┘│
│                        │                                     │
│                        ▼                                     │
│  ┌─────────────────────────────────────────────────────────┐│
│  │            FeedForward (SwiGLU) / MoE                    ││
│  │   ┌─────────────────────────────────────────────────┐   ││
│  │   │ Gate Projection (w1)                             │   ││
│  │   │ Up Projection (w3)                               │   ││
│  │   │ SiLU Activation & Element-wise Multiply          │   ││
│  │   │ Down Projection (w2)                             │   ││
│  │   └─────────────────────────────────────────────────┘   ││
│  └─────────────────────────────────────────────────────────┘│
│                        │                                     │
│              ┌─────────┴─────────┐                          │
│              │    Residual Add    │                          │
│              └─────────┬─────────┘                          │
└────────────────────────┼─────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      RMSNorm                                 │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  Output Projection                           │
│              (dim) -> (vocab_size)                           │
│              (权重共享 with Embedding)                        │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
                    Logits (预测下一个token)
"""
```

---

## 3.9 模型核心组件深度解析

本节将对MiniMind的核心组件进行更深入的剖析，包括数学推导、实现细节、性能优化和实际应用场景。

### 3.9.1 RMSNorm 深度解析

#### 数学推导

RMSNorm的核心思想是对输入向量进行尺度归一化，而不进行均值中心化。让我们从数学角度深入理解：

```
给定输入向量 x = [x₁, x₂, ..., xₙ]

LayerNorm计算：
    mean = (1/n) * Σxᵢ
    var = (1/n) * Σ(xᵢ - mean)²
    yᵢ = (xᵢ - mean) / sqrt(var + ε) * γᵢ + βᵢ

RMSNorm计算：
    rms = sqrt((1/n) * Σxᵢ²)
    yᵢ = xᵢ / rms * γᵢ

关键区别：
1. RMSNorm不计算均值，直接使用平方根均值
2. RMSNorm没有偏置参数β
3. RMSNorm的计算量更少
```

#### 为什么RMSNorm有效？

```python
"""
RMSNorm有效的理论解释

1. 尺度不变性
   神经网络的输出对输入的尺度敏感
   RMSNorm确保每个样本的向量长度一致
   这有助于梯度稳定传播

2. 均值中心化的作用有限
   LayerNorm中的均值中心化主要影响分布的位置
   但对于ReLU等激活函数，位置信息不如尺度重要
   实验表明，去掉均值对性能影响很小

3. 梯度分析
   LayerNorm梯度：
   ∂L/∂xᵢ = (1/σ) * [∂L/∂yᵢ - mean(∂L/∂y) - yᵢ * mean(∂L/∂y * y)]
   
   RMSNorm梯度：
   ∂L/∂xᵢ = (1/rms) * [∂L/∂yᵢ - (xᵢ/rms²) * mean(∂L/∂y * x)]
   
   RMSNorm的梯度计算更简单，计算效率更高

4. 实验验证
   在LLaMA、Falcon、Mistral等模型上的实验表明
   RMSNorm与LayerNorm性能相当，但计算更快
"""
```

#### RMSNorm的变体与改进

```python
"""
RMSNorm的变体

1. Group RMSNorm
   将特征分组，每组独立归一化
   适用于某些特殊架构

2. LayerScale + RMSNorm
   在RMSNorm后添加可学习的缩放
   有助于深层网络的训练

3. Adaptive RMSNorm
   根据输入动态调整归一化参数
   用于条件生成模型
"""

class LayerScaleRMSNorm(nn.Module):
    """
    带LayerScale的RMSNorm
    用于深层Transformer的稳定训练
    """
    def __init__(self, dim, eps=1e-6, init_scale=1e-5):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(dim))
        self.scale = nn.Parameter(torch.ones(dim) * init_scale)
        self.eps = eps
    
    def forward(self, x):
        norm_x = x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + self.eps)
        return self.scale * self.weight * norm_x
```

#### RMSNorm的实现细节

```python
"""
RMSNorm实现的关键细节

1. 数值稳定性
   - 使用float32计算归一化
   - 防止float16下的数值溢出
   
2. 内存效率
   - 使用inplace操作减少内存分配
   - 避免不必要的中间变量
   
3. GPU优化
   - 使用torch.rsqrt而不是1/torch.sqrt
   - 利用Tensor Core加速
"""

class OptimizedRMSNorm(nn.Module):
    """
    优化的RMSNorm实现
    """
    def __init__(self, dim, eps=1e-6):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(dim))
        self.eps = eps
        self.dim = dim
        
        # 预计算dim的倒数，避免重复计算
        self.register_buffer('rms_scale', torch.tensor(1.0 / dim))
    
    def forward(self, x):
        # 使用float32计算，确保数值稳定性
        x_fp32 = x.float()
        
        # 计算平方和，使用sum而不是mean + pow
        # 这样可以减少一次除法操作
        sum_sq = x_fp32.pow(2).sum(-1, keepdim=True)
        
        # 计算RMS的倒数
        rms_inv = torch.rsqrt(sum_sq * self.rms_scale + self.eps)
        
        # 归一化并应用权重
        output = x_fp32 * rms_inv * self.weight.float()
        
        # 转回原数据类型
        return output.type_as(x)
```

---

### 3.9.2 RoPE 深度解析

#### RoPE的数学基础

RoPE基于复数旋转的概念，让我们从数学角度深入理解：

```
复数表示：
    z = a + bi = r * e^(iθ) = r * (cos(θ) + i*sin(θ))
    
    其中：
    - r = |z| = sqrt(a² + b²) 是模长
    - θ = arg(z) = atan2(b, a) 是幅角

复数乘法：
    z₁ * z₂ = r₁ * r₂ * e^(i(θ₁ + θ₂))
    
    乘法的效果：
    - 模长相乘：r₁ * r₂
    - 幅角相加：θ₁ + θ₂

旋转矩阵：
    R(θ) = [cos(θ)  -sin(θ)]
           [sin(θ)   cos(θ)]
    
    这等价于复数乘法 e^(iθ)
```

#### RoPE的位置编码公式

```python
"""
RoPE的完整数学推导

对于位置m的token，其查询向量q的第i对维度应用旋转：

设 q = [q₁, q₂, q₃, q₄, ..., q_{d-1}, q_d]
将q重组为复数形式：z = [(q₁+iq₂), (q₃+iq₄), ..., (q_{d-1}+iq_d)]

位置m的旋转角度：
    θ_{m,i} = m * θ_i
    
其中 θ_i = 1 / (base^(2i/d))

旋转后的向量：
    z'_i = z_i * e^(im*θ_i)
    
展开为实数：
    q'_{2i}   = q_{2i}   * cos(m*θ_i) - q_{2i+1} * sin(m*θ_i)
    q'_{2i+1} = q_{2i}   * sin(m*θ_i) + q_{2i+1} * cos(m*θ_i)

这就是RoPE的核心公式！
"""

def rope_rotation_matrix(dim, position, base=10000):
    """
    生成RoPE的旋转矩阵
    
    参数:
        dim: 向量维度
        position: 位置索引
        base: 频率基数
    
    返回:
        旋转矩阵，形状为 (dim, dim)
    """
    # 计算频率
    freqs = 1.0 / (base ** (torch.arange(0, dim, 2).float() / dim))
    
    # 计算角度
    angles = position * freqs
    
    # 构建旋转矩阵
    cos = torch.cos(angles)
    sin = torch.sin(angles)
    
    # 创建完整的旋转矩阵
    # 对于每对维度 (2i, 2i+1)，旋转矩阵为：
    # [cos  -sin]
    # [sin   cos]
    
    rot_matrix = torch.zeros(dim, dim)
    for i in range(dim // 2):
        rot_matrix[2*i, 2*i] = cos[i]
        rot_matrix[2*i, 2*i+1] = -sin[i]
        rot_matrix[2*i+1, 2*i] = sin[i]
        rot_matrix[2*i+1, 2*i+1] = cos[i]
    
    return rot_matrix
```

#### RoPE的相对位置性质

```python
"""
RoPE的核心优势：自然编码相对位置

关键性质：
当查询q在位置m，键k在位置n时，注意力分数为：

score(m, n) = q_m · k_n
            = (R_m * q) · (R_n * k)
            = q^T * R_m^T * R_n * k
            = q^T * R_{n-m} * k

其中 R_{n-m} = R_m^T * R_n 是相对位置(n-m)的旋转矩阵

这意味着注意力分数只依赖于相对位置(n-m)，而不是绝对位置！
"""

def demonstrate_relative_position():
    """演示RoPE的相对位置性质"""
    import torch
    
    dim = 64
    base = 10000
    
    # 两个不同位置的向量
    q = torch.randn(dim)
    k = torch.randn(dim)
    
    # 位置编码
    def apply_rope(x, pos):
        freqs = 1.0 / (base ** (torch.arange(0, dim, 2).float() / dim))
        angles = pos * freqs
        
        x_rotated = torch.zeros_like(x)
        for i in range(dim // 2):
            cos_val = torch.cos(angles[i])
            sin_val = torch.sin(angles[i])
            x_rotated[2*i] = x[2*i] * cos_val - x[2*i+1] * sin_val
            x_rotated[2*i+1] = x[2*i] * sin_val + x[2*i+1] * cos_val
        
        return x_rotated
    
    # 计算不同位置的注意力分数
    pos_m, pos_n = 10, 15
    q_m = apply_rope(q, pos_m)
    k_n = apply_rope(k, pos_n)
    
    score = torch.dot(q_m, k_n)
    
    # 验证相对位置性质
    # 如果我们将两个位置同时移动相同距离，分数应该不变
    delta = 5
    q_m_shifted = apply_rope(q, pos_m + delta)
    k_n_shifted = apply_rope(k, pos_n + delta)
    
    score_shifted = torch.dot(q_m_shifted, k_n_shifted)
    
    print(f"原始分数: {score:.6f}")
    print(f"移位后分数: {score_shifted:.6f}")
    print(f"差异: {abs(score - score_shifted):.10f}")
    # 差异应该非常小（数值误差）
```

#### RoPE的长度外推技术

```python
"""
RoPE长度外推：处理比训练时更长的序列

问题：模型训练时最大序列长度为L，推理时需要处理L' > L的序列

解决方案：

1. 线性插值（Linear Interpolation）
   将位置索引缩放到训练范围内
   pos' = pos * L / L'
   
2. NTK感知插值
   动态调整频率基数
   base' = base * (L'/L)^(dim/(dim-2))
   
3. YaRN（Yet another RoPE extensioN）
   结合温度缩放和NTK插值

4. 动态NTK
   根据当前序列长度动态调整基数
"""

def apply_linear_interpolation(pos, original_max, target_max):
    """
    线性插值位置编码
    
    参数:
        pos: 原始位置索引
        original_max: 训练时的最大长度
        target_max: 目标最大长度
    
    返回:
        插值后的位置索引
    """
    scale = original_max / target_max
    return pos * scale

def apply_ntk_interpolation(dim, original_max, target_max, base=10000):
    """
    NTK感知插值
    
    根据目标长度动态调整频率基数
    """
    # 计算新的基数
    new_base = base * ((target_max / original_max) ** (dim / (dim - 2)))
    return new_base

class DynamicNTKRoPE:
    """
    动态NTK RoPE实现
    """
    def __init__(self, dim, max_position=2048, base=10000):
        self.dim = dim
        self.max_position = max_position
        self.base = base
        
    def get_freqs(self, seq_len):
        """根据序列长度动态计算频率"""
        if seq_len <= self.max_position:
            # 在训练范围内，使用原始基数
            base = self.base
        else:
            # 超出训练范围，动态调整基数
            base = self.base * ((seq_len / self.max_position) ** (self.dim / (self.dim - 2)))
        
        # 计算频率
        freqs = 1.0 / (base ** (torch.arange(0, self.dim, 2).float() / self.dim))
        return freqs
```

---

### 3.9.3 Attention 深度解析

#### 注意力机制的完整数学推导

```python
"""
缩放点积注意力的数学推导

基本公式：
    Attention(Q, K, V) = softmax(QK^T / sqrt(d_k)) * V

为什么需要缩放因子 1/sqrt(d_k)？

假设Q和K的元素是均值为0、方差为1的独立随机变量
则 QK^T 的元素是d_k个独立随机变量的乘积之和

E[(QK^T)_{ij}] = 0
Var[(QK^T)_{ij}] = d_k

当d_k较大时，QK^T的元素值会很大
这会导致softmax的梯度接近0（梯度消失）

缩放后：
    E[(QK^T / sqrt(d_k))_{ij}] = 0
    Var[(QK^T / sqrt(d_k))_{ij}] = 1

这样softmax的输入保持在合理范围，梯度稳定
"""

def analyze_softmax_gradient():
    """分析softmax的梯度特性"""
    import torch
    import matplotlib.pyplot as plt
    
    # 创建不同尺度的输入
    scales = [1, 5, 10, 20, 50]
    
    for scale in scales:
        x = torch.randn(100) * scale
        x.requires_grad = True
        
        # 计算softmax
        y = torch.softmax(x, dim=0)
        
        # 计算梯度（假设损失为y的和）
        loss = y.sum()
        loss.backward()
        
        print(f"Scale={scale}:")
        print(f"  输入范围: [{x.min():.2f}, {x.max():.2f}]")
        print(f"  梯度范围: [{x.grad.min():.6f}, {x.grad.max():.6f}]")
        print(f"  梯度均值: {x.grad.mean():.6f}")
        print()
```

#### 多头注意力的并行计算

```python
"""
多头注意力的并行计算策略

关键思想：将所有头的计算合并为矩阵运算

原始方法（循环）：
    for h in range(n_heads):
        Q_h = W_q[h] @ X
        K_h = W_k[h] @ X
        V_h = W_v[h] @ X
        output_h = attention(Q_h, K_h, V_h)
    output = concat([output_0, ..., output_{n-1}])

并行方法：
    Q = X @ W_q  # 一次性计算所有头的Q
    K = X @ W_k  # 一次性计算所有头的K
    V = X @ W_v  # 一次性计算所有头的V
    
    # 重塑为多头形式
    Q = Q.view(batch, seq, n_heads, head_dim).transpose(1, 2)
    K = K.view(batch, seq, n_heads, head_dim).transpose(1, 2)
    V = V.view(batch, seq, n_heads, head_dim).transpose(1, 2)
    
    # 并行计算所有头的注意力
    output = scaled_dot_product_attention(Q, K, V)
    
    # 合并输出
    output = output.transpose(1, 2).reshape(batch, seq, dim)
"""

class ParallelMultiHeadAttention(nn.Module):
    """
    并行多头注意力实现
    """
    def __init__(self, dim, n_heads, dropout=0.0):
        super().__init__()
        self.n_heads = n_heads
        self.head_dim = dim // n_heads
        
        # 合并的QKV投影（更高效）
        self.qkv_proj = nn.Linear(dim, 3 * dim, bias=False)
        self.out_proj = nn.Linear(dim, dim, bias=False)
        self.dropout = nn.Dropout(dropout)
        
        self.scale = 1.0 / math.sqrt(self.head_dim)
    
    def forward(self, x, mask=None):
        batch, seq, dim = x.shape
        
        # 一次性计算Q、K、V
        qkv = self.qkv_proj(x)
        qkv = qkv.reshape(batch, seq, 3, self.n_heads, self.head_dim)
        qkv = qkv.permute(2, 0, 3, 1, 4)  # (3, batch, n_heads, seq, head_dim)
        q, k, v = qkv[0], qkv[1], qkv[2]
        
        # 并行计算注意力
        attn = (q @ k.transpose(-2, -1)) * self.scale
        
        if mask is not None:
            attn = attn.masked_fill(mask == 0, float('-inf'))
        
        attn = torch.softmax(attn, dim=-1)
        attn = self.dropout(attn)
        
        # 加权求和
        out = attn @ v
        
        # 合并多头
        out = out.transpose(1, 2).reshape(batch, seq, dim)
        out = self.out_proj(out)
        
        return out
```

#### Flash Attention的原理

```python
"""
Flash Attention：IO感知的精确注意力算法

核心思想：
传统注意力需要存储完整的注意力矩阵，大小为O(n²)
Flash Attention通过分块计算，将显存占用降到O(n)

关键洞察：
- GPU有不同层级的内存：HBM（高带宽内存）和SRAM
- HBM容量大但速度慢，SRAM容量小但速度快
- 传统注意力频繁访问HBM存储注意力矩阵

Flash Attention策略：
1. 将Q、K、V分成小块，每块适合SRAM大小
2. 在SRAM中计算小块的注意力
3. 使用在线softmax技巧逐步累积结果
4. 避免存储完整的注意力矩阵

数学基础：在线Softmax
    softmax([x1, x2, x3]) 可以分步计算：
    
    步骤1：计算局部softmax
        m1 = max(x1), o1 = exp(x1 - m1)
    
    步骤2：更新
        m2 = max(m1, max(x2))
        o2 = o1 * exp(m1 - m2) + exp(x2 - m2)
    
    步骤3：继续
        m3 = max(m2, max(x3))
        o3 = o2 * exp(m2 - m3) + exp(x3 - m3)
    
    最终：softmax = o3 / sum(o3)
"""

def flash_attention_reference(q, k, v, block_size=64):
    """
    Flash Attention的参考实现
    
    参数:
        q: 查询矩阵 (batch, n_heads, seq, head_dim)
        k: 键矩阵 (batch, n_heads, seq, head_dim)
        v: 值矩阵 (batch, n_heads, seq, head_dim)
        block_size: 分块大小
    
    返回:
        注意力输出 (batch, n_heads, seq, head_dim)
    """
    batch, n_heads, seq, head_dim = q.shape
    
    # 初始化输出
    output = torch.zeros_like(q)
    
    # 分块计算
    for i in range(0, seq, block_size):
        i_end = min(i + block_size, seq)
        q_block = q[:, :, i:i_end, :]
        
        # 初始化累积变量
        max_score = torch.full((batch, n_heads, i_end - i, 1), float('-inf'), device=q.device)
        sum_exp = torch.zeros((batch, n_heads, i_end - i, 1), device=q.device)
        acc_output = torch.zeros((batch, n_heads, i_end - i, head_dim), device=q.device)
        
        for j in range(0, seq, block_size):
            j_end = min(j + block_size, seq)
            k_block = k[:, :, j:j_end, :]
            v_block = v[:, :, j:j_end, :]
            
            # 计算当前块的注意力分数
            scores = torch.matmul(q_block, k_block.transpose(-2, -1)) / math.sqrt(head_dim)
            
            # 应用因果掩码
            if j > i_end:
                continue  # 跳过未来位置
            
            # 在线softmax更新
            new_max = torch.maximum(max_score, scores.max(dim=-1, keepdim=True)[0])
            exp_scores = torch.exp(scores - new_max)
            correction = torch.exp(max_score - new_max)
            
            sum_exp = sum_exp * correction + exp_scores.sum(dim=-1, keepdim=True)
            acc_output = acc_output * correction + torch.matmul(exp_scores, v_block)
            max_score = new_max
        
        # 归一化输出
        output[:, :, i:i_end, :] = acc_output / sum_exp
    
    return output
```

---

### 3.9.4 FeedForward 深度解析

#### SwiGLU的完整数学推导

```python
"""
SwiGLU激活函数的数学推导

1. GLU（Gated Linear Unit）
   GLU(x) = (xW₁) ⊙ σ(xW₂)
   
   其中 σ 是sigmoid函数
   门控机制允许网络选择性地传递信息

2. Swish激活函数
   Swish(x) = x * σ(x) = x / (1 + e^{-x})
   
   Swish的特点：
   - 平滑（处处可微）
   - 非单调（有负值输出）
   - 自门控（输出受输入控制）

3. SwiGLU = Swish + GLU
   SwiGLU(x) = Swish(xW_gate) ⊙ (xW_up)
             = (xW_gate * σ(xW_gate)) ⊙ (xW_up)

4. 完整的SwiGLU FFN
   FFN_SwiGLU(x) = (Swish(xW₁) ⊙ xW₃)W₂
   
   其中：
   - W₁: 门控投影 (dim → hidden_dim)
   - W₂: 下投影 (hidden_dim → dim)
   - W₃: 上投影 (dim → hidden_dim)

参数量分析：
   传统FFN: 2 * dim * hidden_dim
   SwiGLU:  3 * dim * hidden_dim
   
   参数量增加50%，但性能提升显著
"""

def compare_activation_functions():
    """比较不同激活函数的特性"""
    import torch
    import matplotlib.pyplot as plt
    import numpy as np
    
    x = torch.linspace(-5, 5, 1000)
    
    # ReLU
    relu = torch.relu(x)
    
    # GELU
    gelu = x * 0.5 * (1 + torch.erf(x / math.sqrt(2)))
    
    # Swish/SiLU
    swish = x * torch.sigmoid(x)
    
    # 绘制对比图
    plt.figure(figsize=(12, 4))
    
    plt.subplot(1, 3, 1)
    plt.plot(x.numpy(), relu.numpy(), label='ReLU')
    plt.plot(x.numpy(), gelu.numpy(), label='GELU')
    plt.plot(x.numpy(), swish.numpy(), label='Swish')
    plt.legend()
    plt.title('Activation Functions')
    plt.xlabel('x')
    plt.ylabel('f(x)')
    
    # 计算梯度
    x_grad = x.requires_grad_(True)
    
    # ReLU梯度
    relu_grad = torch.autograd.grad(torch.relu(x_grad).sum(), x_grad, retain_graph=True)[0]
    
    # Swish梯度
    swish_out = x_grad * torch.sigmoid(x_grad)
    swish_grad = torch.autograd.grad(swish_out.sum(), x_grad, retain_graph=True)[0]
    
    plt.subplot(1, 3, 2)
    plt.plot(x.detach().numpy(), relu_grad.numpy(), label='ReLU grad')
    plt.plot(x.detach().numpy(), swish_grad.numpy(), label='Swish grad')
    plt.legend()
    plt.title('Gradients')
    plt.xlabel('x')
    plt.ylabel('df/dx')
    
    # 负值输出对比
    plt.subplot(1, 3, 3)
    neg_mask = x < 0
    plt.bar(['ReLU', 'GELU', 'Swish'], 
            [relu[neg_mask].sum().item(), gelu[neg_mask].sum().item(), swish[neg_mask].sum().item()])
    plt.title('Negative Output Sum')
    plt.ylabel('Sum of f(x) for x < 0')
    
    plt.tight_layout()
    plt.show()
```

#### FFN的作用与设计原则

```python
"""
FFN在Transformer中的作用

1. 增加非线性
   注意力机制本质上是线性变换
   FFN引入非线性，增强模型表达能力

2. 增加模型容量
   FFN的隐藏层维度通常是输入维度的4倍
   这显著增加了模型的参数量和表达能力

3. 特征变换
   FFN学习更复杂的特征变换
   不同层可以学习不同层次的特征

设计原则：

1. 隐藏维度选择
   - 传统选择：4 * dim
   - SwiGLU推荐：2/3 * 4 * dim ≈ 2.67 * dim
   - 需要对齐到64的倍数（GPU效率）

2. 激活函数选择
   - ReLU：简单但可能丢失信息
   - GELU：平滑，BERT使用
   - SwiGLU：当前最优，LLaMA使用

3. Dropout位置
   - 通常在FFN输出后应用
   - 小模型可以不用Dropout
"""

class FlexibleFFN(nn.Module):
    """
    灵活的FFN实现，支持多种激活函数
    """
    def __init__(self, dim, hidden_dim=None, activation='swiglu', dropout=0.0, multiple_of=64):
        super().__init__()
        
        # 计算隐藏维度
        if hidden_dim is None:
            hidden_dim = int(2 * 4 * dim / 3)  # SwiGLU推荐
            hidden_dim = multiple_of * ((hidden_dim + multiple_of - 1) // multiple_of)
        
        self.hidden_dim = hidden_dim
        self.activation = activation
        
        if activation == 'swiglu':
            self.w1 = nn.Linear(dim, hidden_dim, bias=False)
            self.w2 = nn.Linear(hidden_dim, dim, bias=False)
            self.w3 = nn.Linear(dim, hidden_dim, bias=False)
        elif activation == 'gelu':
            self.w1 = nn.Linear(dim, hidden_dim, bias=False)
            self.w2 = nn.Linear(hidden_dim, dim, bias=False)
        elif activation == 'relu':
            self.w1 = nn.Linear(dim, hidden_dim, bias=False)
            self.w2 = nn.Linear(hidden_dim, dim, bias=False)
        else:
            raise ValueError(f"Unknown activation: {activation}")
        
        self.dropout = nn.Dropout(dropout)
    
    def forward(self, x):
        if self.activation == 'swiglu':
            return self.dropout(self.w2(F.silu(self.w1(x)) * self.w3(x)))
        elif self.activation == 'gelu':
            return self.dropout(self.w2(F.gelu(self.w1(x))))
        elif self.activation == 'relu':
            return self.dropout(self.w2(F.relu(self.w1(x))))
```

---

### 3.9.5 MoE 深度解析

#### MoE的负载均衡问题

```python
"""
MoE负载均衡问题详解

问题描述：
如果门控网络总是选择少数几个专家，会导致：
1. 被选中的专家过载，训练不充分
2. 未被选中的专家闲置，浪费参数
3. 模型性能下降

解决方案：辅助损失（Auxiliary Loss）

负载均衡损失公式：
    L_aux = α * n * Σᵢ(fᵢ * Pᵢ)

其中：
- fᵢ = 专家i被选中的频率
- Pᵢ = 专家i的平均路由分数
- n = 专家总数
- α = 损失权重

这个损失鼓励：
1. 所有专家被均匀选中（fᵢ接近1/n）
2. 所有专家的路由分数相近（Pᵢ接近均值）
"""

class LoadBalancingLoss(nn.Module):
    """
    负载均衡损失
    """
    def __init__(self, n_experts, alpha=0.1):
        super().__init__()
        self.n_experts = n_experts
        self.alpha = alpha
    
    def forward(self, router_probs, expert_indices):
        """
        计算负载均衡损失
        
        参数:
            router_probs: 路由概率 (batch * seq, n_experts)
            expert_indices: 选中的专家索引 (batch * seq, top_k)
        
        返回:
            负载均衡损失
        """
        # 计算每个专家被选中的频率
        expert_mask = F.one_hot(expert_indices, self.n_experts).float()
        expert_freq = expert_mask.sum(dim=(0, 1)) / expert_mask.numel() * self.n_experts
        
        # 计算每个专家的平均路由分数
        expert_prob = router_probs.mean(dim=0)
        
        # 负载均衡损失
        loss = self.alpha * self.n_experts * (expert_freq * expert_prob).sum()
        
        return loss
```

#### MoE的高级路由策略

```python
"""
MoE高级路由策略

1. Top-K路由（基础）
   选择分数最高的K个专家

2. 专家选择路由（Expert Choice）
   让专家选择token，而不是token选择专家
   自动实现负载均衡

3. Soft路由
   使用所有专家的加权平均
   计算量大但平滑

4. 混合路由
   结合Top-K和Soft路由的优点

5. 容量因子
   限制每个专家处理的token数量
   超出容量的token跳过或重新路由
"""

class ExpertChoiceRouter(nn.Module):
    """
    专家选择路由
    让专家主动选择要处理的token
    """
    def __init__(self, dim, n_experts, top_k, capacity_factor=1.25):
        super().__init__()
        self.n_experts = n_experts
        self.top_k = top_k
        self.capacity_factor = capacity_factor
        
        self.gate = nn.Linear(dim, n_experts, bias=False)
    
    def forward(self, x):
        """
        专家选择路由
        
        参数:
            x: 输入张量 (batch, seq, dim)
        
        返回:
            路由后的输出
        """
        batch, seq, dim = x.shape
        
        # 计算路由分数
        router_logits = self.gate(x)  # (batch, seq, n_experts)
        
        # 转置：让专家维度在前
        router_logits = router_logits.transpose(0, 2)  # (n_experts, seq, batch)
        router_logits = router_logits.reshape(self.n_experts, -1)  # (n_experts, batch * seq)
        
        # 计算每个专家的容量
        capacity = int(self.capacity_factor * seq * batch / self.n_experts)
        
        # 每个专家选择top-capacity个token
        top_k_scores, top_k_indices = torch.topk(
            router_logits, capacity, dim=-1
        )
        
        # 应用softmax
        top_k_scores = F.softmax(top_k_scores, dim=-1)
        
        return top_k_scores, top_k_indices


class SoftRouter(nn.Module):
    """
    Soft路由：使用所有专家的加权平均
    """
    def __init__(self, dim, n_experts):
        super().__init__()
        self.n_experts = n_experts
        self.gate = nn.Linear(dim, n_experts, bias=False)
    
    def forward(self, x, experts):
        """
        Soft路由
        
        参数:
            x: 输入张量 (batch, seq, dim)
            experts: 专家网络列表
        
        返回:
            加权平均输出
        """
        # 计算路由权重
        router_weights = F.softmax(self.gate(x), dim=-1)  # (batch, seq, n_experts)
        
        # 计算所有专家的输出
        expert_outputs = []
        for expert in experts:
            expert_outputs.append(expert(x))
        
        # 堆叠专家输出
        expert_outputs = torch.stack(expert_outputs, dim=-1)  # (batch, seq, dim, n_experts)
        
        # 加权平均
        output = (expert_outputs * router_weights.unsqueeze(-2)).sum(dim=-1)
        
        return output
```

#### 共享专家的设计原理

```python
"""
共享专家（Shared Experts）的设计原理

动机：
1. 某些知识是通用的，所有token都需要
2. 路由专家专注于特定领域的知识
3. 共享专家处理通用知识

实现：
- 共享专家对所有token都激活
- 输出与路由专家输出相加
- 不需要路由决策

优势：
1. 减少路由专家的负担
2. 保留通用知识
3. 提高模型稳定性

MiniMind的配置：
- 4个路由专家（每个token激活2个）
- 1个共享专家（所有token都激活）
"""

class SharedExpertMoE(nn.Module):
    """
    带共享专家的MoE实现
    """
    def __init__(self, dim, hidden_dim, n_routed_experts, n_shared_experts, top_k):
        super().__init__()
        
        self.n_routed_experts = n_routed_experts
        self.n_shared_experts = n_shared_experts
        self.top_k = top_k
        
        # 路由专家
        self.routed_experts = nn.ModuleList([
            FeedForward(dim, hidden_dim, multiple_of=64)
            for _ in range(n_routed_experts)
        ])
        
        # 共享专家
        self.shared_experts = nn.ModuleList([
            FeedForward(dim, hidden_dim, multiple_of=64)
            for _ in range(n_shared_experts)
        ])
        
        # 路由门控
        self.gate = nn.Linear(dim, n_routed_experts, bias=False)
    
    def forward(self, x):
        batch, seq, dim = x.shape
        x_flat = x.view(-1, dim)
        
        # 计算路由权重
        router_logits = self.gate(x_flat)  # (batch * seq, n_routed_experts)
        router_weights = F.softmax(router_logits, dim=-1)
        
        # 选择top-k路由专家
        top_k_weights, top_k_indices = torch.topk(router_weights, self.top_k, dim=-1)
        top_k_weights = top_k_weights / top_k_weights.sum(dim=-1, keepdim=True)
        
        # 初始化输出
        output = torch.zeros_like(x_flat)
        
        # 计算路由专家输出
        for i in range(self.top_k):
            expert_idx = top_k_indices[:, i]  # (batch * seq,)
            weight = top_k_weights[:, i:i+1]  # (batch * seq, 1)
            
            for e in range(self.n_routed_experts):
                mask = (expert_idx == e)
                if mask.any():
                    expert_input = x_flat[mask]
                    expert_output = self.routed_experts[e](expert_input)
                    output[mask] += weight[mask] * expert_output
        
        # 计算共享专家输出
        shared_output = torch.zeros_like(x_flat)
        for shared_expert in self.shared_experts:
            shared_output += shared_expert(x_flat)
        shared_output = shared_output / self.n_shared_experts
        
        # 合并输出
        output = output + shared_output
        
        return output.view(batch, seq, dim)
```

---

### 3.9.6 模型初始化与权重共享

#### 权重初始化策略

```python
"""
模型权重初始化的重要性

好的初始化可以：
1. 加速收敛
2. 避免梯度消失/爆炸
3. 提高最终性能

常用初始化方法：

1. Xavier/Glorot初始化
   适用于sigmoid/tanh激活
   std = sqrt(2 / (fan_in + fan_out))

2. Kaiming/He初始化
   适用于ReLU及其变体
   std = sqrt(2 / fan_in)

3. 正态分布初始化
   Transformer常用
   std = 0.02 或 1/sqrt(dim)

4. 截断正态分布
   避免极端值
   在[-2*std, 2*std]范围内截断
"""

def init_weights(module, method='normal', std=0.02):
    """
    权重初始化函数
    
    参数:
        module: 要初始化的模块
        method: 初始化方法
        std: 标准差
    """
    if isinstance(module, nn.Linear):
        if method == 'normal':
            nn.init.normal_(module.weight, mean=0.0, std=std)
        elif method == 'xavier':
            nn.init.xavier_normal_(module.weight)
        elif method == 'kaiming':
            nn.init.kaiming_normal_(module.weight, mode='fan_in', nonlinearity='relu')
        
        if module.bias is not None:
            nn.init.zeros_(module.bias)
    
    elif isinstance(module, nn.Embedding):
        nn.init.normal_(module.weight, mean=0.0, std=std)
    
    elif isinstance(module, nn.LayerNorm):
        nn.init.ones_(module.weight)
        nn.init.zeros_(module.bias)
    
    elif isinstance(module, RMSNorm):
        nn.init.ones_(module.weight)


def scaled_init(module, dim, n_layers):
    """
    缩放初始化
    
    对于深层网络，使用较小的初始化方差
    std = 0.02 / sqrt(2 * n_layers)
    
    这有助于稳定深层网络的训练
    """
    std = 0.02 / math.sqrt(2 * n_layers)
    init_weights(module, std=std)
```

#### 权重共享的原理

```python
"""
权重共享（Weight Tying）的原理

在语言模型中，输入嵌入层和输出层共享权重：

输入嵌入层：
    E: vocab_size × dim
    将token ID映射为向量

输出层：
    W: dim × vocab_size
    将隐藏状态映射为logits

共享权重：
    W = E^T
    即 output = hidden @ E^T

为什么共享权重？

1. 参数效率
   减少参数量：vocab_size × dim
   对于vocab_size=6400, dim=512：减少约3.3M参数

2. 正则化效果
   共享权重相当于添加了约束
   有助于防止过拟合

3. 语义一致性
   输入和输出都表示token
   应该在同一语义空间中

4. 实验验证
   在多个任务上，共享权重效果更好

注意事项：
- 共享权重可能不适用于所有任务
- 对于某些特定任务，独立权重可能更好
"""

class WeightTiedLM(nn.Module):
    """
    带权重共享的语言模型
    """
    def __init__(self, vocab_size, dim):
        super().__init__()
        
        # 嵌入层
        self.embedding = nn.Embedding(vocab_size, dim)
        
        # 其他层...
        # ...
        
        # 输出层（不创建新的权重）
        # 使用embedding的权重作为输出权重
    
    def forward(self, input_ids):
        # 嵌入
        x = self.embedding(input_ids)
        
        # 通过其他层...
        # x = self.layers(x)
        
        # 输出logits
        # 使用embedding权重进行计算
        logits = F.linear(x, self.embedding.weight)
        
        return logits
```

---

### 3.9.7 梯度流与反向传播

```python
"""
Transformer中的梯度流分析

理解梯度如何在Transformer中流动对于调试和优化至关重要

1. 残差连接的梯度流
   y = x + f(x)
   ∂L/∂x = ∂L/∂y + ∂L/∂y * ∂f/∂x
   
   梯度可以直接通过残差连接流动，不经过f
   这有助于缓解梯度消失

2. LayerNorm/RMSNorm的梯度流
   y = x / ||x|| * γ
   
   梯度会重新分配到所有维度
   有助于稳定训练

3. 注意力的梯度流
   Attention(Q, K, V) = softmax(QK^T) * V
   
   梯度从V反向传播到Q、K
   Softmax的梯度可能导致梯度消失

4. FFN的梯度流
   y = W2 * activation(W1 * x)
   
   激活函数的梯度影响梯度流动
   SwiGLU的梯度比ReLU更平滑
"""

def analyze_gradient_flow(model, input_ids):
    """
    分析模型的梯度流
    
    参数:
        model: 语言模型
        input_ids: 输入token ID
    
    返回:
        各层的梯度统计信息
    """
    # 前向传播
    outputs = model(input_ids)
    loss = outputs.logits.sum()
    
    # 反向传播
    loss.backward()
    
    # 收集梯度统计信息
    gradient_stats = {}
    
    for name, param in model.named_parameters():
        if param.grad is not None:
            grad = param.grad
            stats = {
                'mean': grad.mean().item(),
                'std': grad.std().item(),
                'min': grad.min().item(),
                'max': grad.max().item(),
                'norm': grad.norm().item(),
            }
            gradient_stats[name] = stats
    
    return gradient_stats


def gradient_clipping_analysis(model, max_norm=1.0):
    """
    梯度裁剪分析
    
    参数:
        model: 语言模型
        max_norm: 最大梯度范数
    
    返回:
        裁剪前后的梯度范数
    """
    # 计算总梯度范数
    total_norm = 0.0
    for param in model.parameters():
        if param.grad is not None:
            param_norm = param.grad.data.norm(2)
            total_norm += param_norm.item() ** 2
    total_norm = total_norm ** 0.5
    
    # 计算裁剪系数
    clip_coef = max_norm / (total_norm + 1e-6)
    
    if clip_coef < 1:
        # 需要裁剪
        for param in model.parameters():
            if param.grad is not None:
                param.grad.data.mul_(clip_coef)
    
    return {
        'original_norm': total_norm,
        'clipped': clip_coef < 1,
        'clip_coef': clip_coef,
        'final_norm': min(total_norm, max_norm)
    }
```

---

### 3.9.8 模型性能优化技巧

```python
"""
模型性能优化技巧

1. 算子融合
   将多个操作合并为一个，减少内存访问

2. 梯度检查点
   以计算换内存，减少显存占用

3. 混合精度训练
   使用float16/bfloat16加速计算

4. 编译优化
   使用torch.compile进行图优化

5. 内存优化
   使用inplace操作，减少内存分配
"""

# 1. 算子融合示例
class FusedQKVProjection(nn.Module):
    """
    融合的QKV投影
    将三个投影合并为一个
    """
    def __init__(self, dim, n_heads, n_kv_heads):
        super().__init__()
        self.n_heads = n_heads
        self.n_kv_heads = n_kv_heads
        self.head_dim = dim // n_heads
        
        # 融合的QKV投影
        total_dim = n_heads * self.head_dim + 2 * n_kv_heads * self.head_dim
        self.qkv_proj = nn.Linear(dim, total_dim, bias=False)
    
    def forward(self, x):
        batch, seq, _ = x.shape
        
        # 一次性计算Q、K、V
        qkv = self.qkv_proj(x)
        
        # 分离Q、K、V
        q_dim = self.n_heads * self.head_dim
        kv_dim = self.n_kv_heads * self.head_dim
        
        q = qkv[:, :, :q_dim]
        k = qkv[:, :, q_dim:q_dim + kv_dim]
        v = qkv[:, :, q_dim + kv_dim:]
        
        return q, k, v


# 2. 梯度检查点示例
from torch.utils.checkpoint import checkpoint

class CheckpointedTransformerBlock(nn.Module):
    """
    带梯度检查点的Transformer块
    以计算换内存
    """
    def __init__(self, config):
        super().__init__()
        self.attention = Attention(config)
        self.feed_forward = FeedForward(config.dim, config.hidden_dim, config.multiple_of)
        self.attention_norm = RMSNorm(config.dim)
        self.ffn_norm = RMSNorm(config.dim)
    
    def _forward(self, x, pos_cis):
        # 注意力子层
        h = x + self.attention(self.attention_norm(x), pos_cis)[0]
        # FFN子层
        out = h + self.feed_forward(self.ffn_norm(h))
        return out
    
    def forward(self, x, pos_cis):
        # 使用梯度检查点
        return checkpoint(self._forward, x, pos_cis, use_reentrant=False)


# 3. 编译优化示例
def compile_model(model):
    """
    使用torch.compile优化模型
    
    编译优化包括：
    - 算子融合
    - 死代码消除
    - 常量折叠
    - 内存布局优化
    """
    # 使用默认模式
    compiled_model = torch.compile(model)
    
    # 或者使用更激进的优化
    # compiled_model = torch.compile(model, mode='max-autotune')
    
    return compiled_model


# 4. 内存优化示例
class MemoryEfficientAttention(nn.Module):
    """
    内存高效的注意力实现
    使用inplace操作和内存复用
    """
    def __init__(self, dim, n_heads):
        super().__init__()
        self.n_heads = n_heads
        self.head_dim = dim // n_heads
        self.scale = 1.0 / math.sqrt(self.head_dim)
        
        self.qkv_proj = nn.Linear(dim, 3 * dim, bias=False)
        self.out_proj = nn.Linear(dim, dim, bias=False)
    
    def forward(self, x):
        batch, seq, dim = x.shape
        
        # 计算QKV
        qkv = self.qkv_proj(x)
        qkv = qkv.view(batch, seq, 3, self.n_heads, self.head_dim)
        qkv = qkv.permute(2, 0, 3, 1, 4)
        q, k, v = qkv[0], qkv[1], qkv[2]
        
        # 使用Flash Attention（如果可用）
        if hasattr(F, 'scaled_dot_product_attention'):
            out = F.scaled_dot_product_attention(q, k, v, is_causal=True)
        else:
            # 手动实现，使用分块计算减少内存
            out = self._blockwise_attention(q, k, v)
        
        # 合并输出
        out = out.transpose(1, 2).contiguous()
        out = out.view(batch, seq, dim)
        
        return self.out_proj(out)
    
    def _blockwise_attention(self, q, k, v, block_size=64):
        """分块注意力计算"""
        batch, n_heads, seq, head_dim = q.shape
        
        output = torch.zeros_like(q)
        
        for i in range(0, seq, block_size):
            i_end = min(i + block_size, seq)
            q_block = q[:, :, i:i_end, :]
            
            # 计算当前块的注意力
            scores = torch.matmul(q_block, k.transpose(-2, -1)) * self.scale
            
            # 应用因果掩码
            mask = torch.triu(
                torch.ones(i_end - i, seq, dtype=torch.bool, device=q.device),
                diagonal=seq - i
            )
            scores = scores.masked_fill(mask, float('-inf'))
            
            # Softmax和加权
            attn = F.softmax(scores, dim=-1)
            output[:, :, i:i_end, :] = torch.matmul(attn, v)
        
        return output
```

---

## 4. 数据处理系统

数据处理是训练大语言模型的关键环节，MiniMind提供了完整的数据处理流程。数据质量直接决定了模型的上限，因此理解数据处理系统至关重要。

### 4.0 数据处理系统架构总览

```
数据处理流程：

原始数据（文本/对话）
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│                    数据清洗与预处理                           │
│  - 去除HTML标签、特殊字符                                     │
│  - 文本规范化（统一编码、去除多余空白）                        │
│  - 数据去重（防止重复样本）                                   │
│  - 质量过滤（去除低质量文本）                                 │
└─────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│                    分词器处理                                 │
│  - 加载预训练分词器                                          │
│  - 文本 → Token ID序列                                       │
│  - 添加特殊Token（BOS/EOS/PAD）                              │
└─────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│                    序列处理                                   │
│  - 截断（超过max_length）                                    │
│  - 填充（不足max_length）                                    │
│  - 创建注意力掩码                                            │
│  - 创建标签（用于训练）                                       │
└─────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│                    批量组织                                   │
│  - DataLoader批处理                                          │
│  - 分布式采样（DDP）                                          │
│  - 动态批处理（可选）                                         │
└─────────────────────────────────────────────────────────────┘
       │
       ▼
    模型输入
```

### 4.0.1 数据格式对比

| 数据类型 | 文件格式 | 主要用途 | 特殊处理 |
|---------|---------|---------|---------|
| 预训练数据 | .jsonl | 学习语言知识 | 纯文本，无角色区分 |
| SFT数据 | .jsonl | 学习对话能力 | 多轮对话，角色区分 |
| DPO数据 | .jsonl | 学习人类偏好 | 正负样本对比 |

### 4.1 预训练数据集

```python
"""
预训练数据集处理
位置：dataset/lm_dataset.py
"""

import torch
from torch.utils.data import Dataset
import json
from typing import Optional


class PretrainDataset(Dataset):
    """
    预训练数据集
    
    用于加载和处理预训练语料。
    数据格式：每行一个JSON对象，包含"text"字段
    
    示例数据格式：
    {"text": "这是一段预训练文本..."}
    {"text": "另一段预训练文本..."}
    """
    
    def __init__(
        self,
        data_path: str,
        tokenizer,
        max_length: int = 512,
        buffer_size: int = 10000
    ):
        """
        初始化预训练数据集
        
        参数:
            data_path: 数据文件路径（.jsonl格式）
            tokenizer: 分词器
            max_length: 最大序列长度
            buffer_size: 缓冲区大小（用于内存优化）
        """
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.buffer_size = buffer_size
        
        # 加载数据
        self.data = []
        with open(data_path, 'r', encoding='utf-8') as f:
            for line in f:
                item = json.loads(line.strip())
                self.data.append(item['text'])
        
        print(f"加载了 {len(self.data)} 条预训练数据")
    
    def __len__(self):
        """返回数据集大小"""
        return len(self.data)
    
    def __getitem__(self, idx: int) -> dict:
        """
        获取单个样本
        
        参数:
            idx: 样本索引
            
        返回:
            包含input_ids和labels的字典
            
        处理流程:
            1. 获取文本
            2. Tokenize
            3. 截断到最大长度
            4. 创建labels（与input_ids相同，用于语言模型训练）
        """
        # 获取文本
        text = self.data[idx]
        
        # Tokenize
        # add_special_tokens=True: 添加BOS和EOS token
        encoding = self.tokenizer(
            text,
            max_length=self.max_length,
            truncation=True,
            padding='max_length',
            return_tensors='pt',
            add_special_tokens=True
        )
        
        input_ids = encoding['input_ids'].squeeze(0)
        
        # 对于语言模型，labels就是input_ids
        # 模型会预测下一个token，所以labels是input_ids的移位版本
        # 但在PyTorch中，交叉熵损失函数会自动处理这个
        labels = input_ids.clone()
        
        # 将padding token的labels设为-100，这样损失函数会忽略它们
        labels[labels == self.tokenizer.pad_token_id] = -100
        
        return {
            'input_ids': input_ids,
            'labels': labels
        }


class SFTDataset(Dataset):
    """
    监督微调数据集
    
    用于加载和处理对话数据。
    数据格式：每行一个JSON对象，包含"conversations"字段
    
    示例数据格式：
    {
        "conversations": [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好！有什么我可以帮助你的吗？"}
        ]
    }
    """
    
    def __init__(
        self,
        data_path: str,
        tokenizer,
        max_length: int = 512
    ):
        """
        初始化SFT数据集
        
        参数:
            data_path: 数据文件路径
            tokenizer: 分词器
            max_length: 最大序列长度
        """
        self.tokenizer = tokenizer
        self.max_length = max_length
        
        # 加载数据
        self.data = []
        with open(data_path, 'r', encoding='utf-8') as f:
            for line in f:
                item = json.loads(line.strip())
                self.data.append(item)
        
        print(f"加载了 {len(self.data)} 条SFT数据")
    
    def _create_chat_prompt(self, conversations: list) -> str:
        """
        创建对话提示
        
        使用ChatML格式：
        <|im_start|>user
        用户消息<|im_end|>
        <|im_start|>assistant
        助手回复<|im_end|>
        
        参数:
            conversations: 对话列表
            
        返回:
            格式化后的对话字符串
        """
        prompt = ""
        for conv in conversations:
            role = conv['role']
            content = conv['content']
            
            if role == 'user':
                prompt += f"<|im_start|>user\n{content}<|im_end|>\n"
            elif role == 'assistant':
                prompt += f"<|im_start|>assistant\n{content}<|im_end|>\n"
        
        return prompt
    
    def __len__(self):
        """返回数据集大小"""
        return len(self.data)
    
    def __getitem__(self, idx: int) -> dict:
        """
        获取单个样本
        
        参数:
            idx: 样本索引
            
        返回:
            包含input_ids和labels的字典
            
        处理流程:
            1. 获取对话
            2. 格式化为ChatML格式
            3. Tokenize
            4. 创建labels（只计算assistant回复的损失）
        """
        # 获取对话
        conversations = self.data[idx]['conversations']
        
        # 创建提示
        prompt = self._create_chat_prompt(conversations)
        
        # Tokenize
        encoding = self.tokenizer(
            prompt,
            max_length=self.max_length,
            truncation=True,
            padding='max_length',
            return_tensors='pt'
        )
        
        input_ids = encoding['input_ids'].squeeze(0)
        
        # 创建labels
        # 只计算assistant回复部分的损失
        labels = input_ids.clone()
        
        # 找到assistant回复的位置
        # 将user部分和padding部分的labels设为-100
        # 这样损失函数只会计算assistant回复部分
        
        # 简化处理：这里我们计算所有token的损失
        # 实际应用中应该只计算assistant部分
        labels[labels == self.tokenizer.pad_token_id] = -100
        
        return {
            'input_ids': input_ids,
            'labels': labels
        }
```

---

## 5. 预训练流程

预训练是大语言模型学习基础知识的关键阶段。在这个阶段，模型通过大规模无标注文本学习语言的统计规律和世界知识。

### 5.0 预训练理论背景

#### 5.0.1 语言模型的目标

```
语言建模目标：预测下一个token

给定文本序列 x = [x₁, x₂, ..., xₙ]
目标：最大化 P(x₁, x₂, ..., xₙ)

根据链式法则：
    P(x₁, x₂, ..., xₙ) = P(x₁) × P(x₂|x₁) × P(x₃|x₁,x₂) × ... × P(xₙ|x₁,...,xₙ₋₁)

训练目标：
    L = -Σ log P(xᵢ | x₁, ..., xᵢ₋₁)
    
这就是"下一个token预测"任务，也称为"因果语言建模"（Causal Language Modeling）
```

#### 5.0.2 预训练学到了什么？

```
预训练阶段模型学习的内容：

1. 语言知识
   - 语法结构
   - 词汇语义
   - 句子组成规则
   
2. 世界知识
   - 常识推理
   - 事实性知识
   - 逻辑关系
   
3. 上下文理解
   - 指代消解
   - 主题跟踪
   - 信息整合
   
4. 涌现能力（Emergent Abilities）
   - 少样本学习
   - 链式推理
   - 指令遵循（需要SFT激活）
```

#### 5.0.3 预训练数据规模建议

| 模型参数量 | 建议数据量 | 数据/参数比 |
|-----------|-----------|------------|
| 26M | 1-5GB | 20-100x |
| 100M | 5-20GB | 20-100x |
| 1B | 50-200GB | 20-100x |
| 7B | 1-3TB | 50-150x |

**Chinchilla定律**：最优训练数据量约为参数量的20倍

### 5.1 预训练脚本完整解析

```python
"""
预训练脚本
位置：1-pretrain.py
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torch.utils.data.distributed import DistributedSampler
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel as DDP
import argparse
import math
import os
from contextlib import nullcontext

# 导入模型和数据集
from model.model import MiniMindLM
from model.LMConfig import LMConfig
from dataset.lm_dataset import PretrainDataset
from transformers import AutoTokenizer


def get_lr(current_step: int, total_steps: int, lr: float) -> float:
    """
    余弦学习率调度
    
    公式：
        lr = min_lr + 0.5 * (lr - min_lr) * (1 + cos(π * step / total_steps))
    
    参数:
        current_step: 当前步数
        total_steps: 总步数
        lr: 基础学习率
        
    返回:
        当前学习率
        
    学习率变化曲线：
        开始时：lr
        中间：逐渐下降
        结束时：lr / 10
    """
    # 最小学习率
    min_lr = lr / 10
    
    # 余弦退火
    return min_lr + 0.5 * (lr - min_lr) * (1 + math.cos(math.pi * current_step / total_steps))


def train(args):
    """
    主训练函数
    
    参数:
        args: 命令行参数
    """
    # ==================== 初始化分布式训练 ====================
    
    # 检查是否使用分布式训练
    ddp = int(os.environ.get('RANK', -1)) != -1
    
    if ddp:
        # 初始化进程组
        dist.init_process_group(backend='nccl')
        ddp_rank = int(os.environ['RANK'])
        ddp_local_rank = int(os.environ['LOCAL_RANK'])
        ddp_world_size = int(os.environ['WORLD_SIZE'])
        device = f'cuda:{ddp_local_rank}'
        torch.cuda.set_device(device)
        master_process = ddp_rank == 0
    else:
        ddp_rank = 0
        ddp_local_rank = 0
        ddp_world_size = 1
        device = args.device
        master_process = True
    
    # ==================== 设置随机种子 ====================
    
    torch.manual_seed(42)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(42)
    
    # ==================== 加载分词器 ====================
    
    tokenizer = AutoTokenizer.from_pretrained('./model/minimind_tokenizer')
    print(f"词汇表大小: {len(tokenizer)}")
    
    # ==================== 创建模型配置 ====================
    
    lm_config = LMConfig(
        dim=args.dim,
        n_layers=args.n_layers,
        max_seq_len=args.max_seq_len,
        use_moe=args.use_moe
    )
    
    # ==================== 创建模型 ====================
    
    model = MiniMindLM(lm_config).to(device)
    
    # 计算参数量
    total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"模型参数量: {total_params / 1e6:.2f}M")
    
    # 包装DDP
    if ddp:
        model = DDP(model, device_ids=[ddp_local_rank])
    
    # ==================== 创建数据集和数据加载器 ====================
    
    train_dataset = PretrainDataset(
        args.data_path,
        tokenizer,
        max_length=lm_config.max_seq_len
    )
    
    # 分布式采样器
    train_sampler = DistributedSampler(train_dataset) if ddp else None
    
    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        pin_memory=True,
        drop_last=False,
        shuffle=False if ddp else True,
        num_workers=args.num_workers,
        sampler=train_sampler
    )
    
    # ==================== 创建优化器 ====================
    
    # AdamW优化器
    # weight_decay: 权重衰减，防止过拟合
    # betas: Adam的动量参数
    optimizer = optim.AdamW(
        model.parameters(),
        lr=args.learning_rate,
        betas=(0.9, 0.95),
        weight_decay=0.1
    )
    
    # ==================== 创建梯度缩放器 ====================
    
    # 用于混合精度训练
    # 混合精度可以减少显存占用并加速训练
    scaler = torch.cuda.amp.GradScaler(enabled=(args.dtype == 'float16'))
    
    # ==================== 计算训练步数 ====================
    
    total_steps = args.epochs * len(train_loader) // args.accumulation_steps
    
    # ==================== 训练循环 ====================
    
    model.train()
    
    for epoch in range(args.epochs):
        # 设置采样器epoch
        if ddp:
            train_sampler.set_epoch(epoch)
        
        # 累积梯度计数
        accumulation_step = 0
        
        for step, batch in enumerate(train_loader):
            # 获取输入
            input_ids = batch['input_ids'].to(device)
            labels = batch['labels'].to(device)
            
            # 混合精度上下文
            with torch.cuda.amp.autocast(enabled=(args.dtype in ['float16', 'bfloat16'])):
                # 前向传播
                outputs = model(input_ids)
                logits = outputs.logits
                
                # 计算损失
                # 交叉熵损失
                # logits: (batch, seq_len, vocab_size)
                # labels: (batch, seq_len)
                loss = nn.functional.cross_entropy(
                    logits.view(-1, logits.size(-1)),
                    labels.view(-1),
                    ignore_index=-100
                )
                
                # 添加MoE辅助损失
                if outputs.aux_loss is not None:
                    loss += outputs.aux_loss
                
                # 梯度累积缩放
                loss = loss / args.accumulation_steps
            
            # 反向传播
            scaler.scale(loss).backward()
            
            # 梯度累积
            accumulation_step += 1
            
            if accumulation_step >= args.accumulation_steps:
                # 梯度裁剪
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), args.grad_clip)
                
                # 更新参数
                scaler.step(optimizer)
                scaler.update()
                
                # 清零梯度
                optimizer.zero_grad(set_to_none=True)
                
                # 更新学习率
                current_step = epoch * len(train_loader) + step
                lr = get_lr(current_step, total_steps, args.learning_rate)
                for param_group in optimizer.param_groups:
                    param_group['lr'] = lr
                
                accumulation_step = 0
                
                # 日志
                if master_process and step % args.log_interval == 0:
                    print(f"Epoch {epoch}, Step {step}, Loss: {loss.item():.4f}, LR: {lr:.6f}")
                
                # 保存检查点
                if master_process and step % args.save_interval == 0:
                    checkpoint = {
                        'model': model.module.state_dict() if ddp else model.state_dict(),
                        'optimizer': optimizer.state_dict(),
                        'epoch': epoch,
                        'step': step
                    }
                    torch.save(checkpoint, f'{args.out_dir}/pretrain_{args.dim}.pth')
    
    # 保存最终模型
    if master_process:
        checkpoint = {
            'model': model.module.state_dict() if ddp else model.state_dict(),
            'optimizer': optimizer.state_dict(),
        }
        torch.save(checkpoint, f'{args.out_dir}/pretrain_{args.dim}.pth')
        print("训练完成！")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="MiniMind Pretraining")
    
    # 训练参数
    parser.add_argument("--out_dir", type=str, default="out")
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch_size", type=int, default=32)
    parser.add_argument("--learning_rate", type=float, default=5e-4)
    parser.add_argument("--device", type=str, default="cuda:0")
    parser.add_argument("--dtype", type=str, default="bfloat16")
    parser.add_argument("--num_workers", type=int, default=1)
    parser.add_argument("--accumulation_steps", type=int, default=8)
    parser.add_argument("--grad_clip", type=float, default=1.0)
    parser.add_argument("--log_interval", type=int, default=100)
    parser.add_argument("--save_interval", type=int, default=100)
    
    # 模型参数
    parser.add_argument("--dim", type=int, default=512)
    parser.add_argument("--n_layers", type=int, default=8)
    parser.add_argument("--max_seq_len", type=int, default=512)
    parser.add_argument("--use_moe", action="store_true")
    
    # 数据参数
    parser.add_argument("--data_path", type=str, default="./dataset/pretrain_hq.jsonl")
    
    args = parser.parse_args()
    
    # 创建输出目录
    os.makedirs(args.out_dir, exist_ok=True)
    
    # 开始训练
    train(args)
```

---

## 6. 监督微调 SFT

监督微调（Supervised Fine-Tuning）让模型学会遵循指令和进行对话。SFT是将预训练模型转化为对话助手的关键步骤。

### 6.0 MiniMind SFT源码导读

```python
"""
MiniMind SFT训练脚本核心逻辑
位置：3-full_sft.py

与预训练的主要区别：
1. 数据格式：使用对话数据而非纯文本
2. 损失计算：只计算assistant回复部分
3. 学习率：通常更小（1e-5）
4. 训练轮数：更多（3-10轮）
"""

# ==================== SFT数据格式 ====================

"""
SFT数据格式 (sft_mini_512.jsonl):

{
    "conversations": [
        {"role": "user", "content": "你好，请介绍一下自己"},
        {"role": "assistant", "content": "你好！我是MiniMind..."}
    ]
}

转换为训练格式：
<|im_start|>user
你好，请介绍一下自己<|im_end|>
<|im_start|>assistant
你好！我是MiniMind...<|im_end|>

标签设置：
- user部分：label = -100 (不计算损失)
- assistant部分：label = token_id (计算损失)
"""

# ==================== SFT损失计算 ====================

def compute_sft_loss(model, input_ids, labels, attention_mask=None):
    """
    SFT损失计算
    
    参数:
        model: MiniMindLM模型
        input_ids: 输入token ID (batch, seq_len)
        labels: 标签 (batch, seq_len)，user部分为-100
        attention_mask: 注意力掩码
    
    返回:
        loss: 标量损失值
    """
    # 前向传播
    outputs = model(input_ids, attention_mask=attention_mask)
    logits = outputs.logits  # (batch, seq_len, vocab_size)
    
    # 计算交叉熵损失
    # ignore_index=-100: 自动忽略标签为-100的位置
    loss = nn.functional.cross_entropy(
        logits.view(-1, logits.size(-1)),  # (batch*seq_len, vocab_size)
        labels.view(-1),                    # (batch*seq_len,)
        ignore_index=-100
    )
    
    return loss


# ==================== MiniMind SFT训练配置 ====================

"""
MiniMind SFT推荐配置：

| 参数 | 预训练 | SFT |
|------|--------|-----|
| learning_rate | 5e-4 | 1e-5 |
| epochs | 1 | 3-10 |
| batch_size | 32 | 16-32 |
| warmup_ratio | 0.01 | 0.05 |
| weight_decay | 0.1 | 0.01 |

SFT训练注意事项：
1. 从预训练权重初始化
2. 使用较小的学习率防止灾难性遗忘
3. 多轮训练提高指令遵循能力
4. 监控验证集损失防止过拟合
"""
```

### 6.0 SFT理论背景

#### 6.0.1 为什么需要SFT？

```
预训练模型的问题：
1. 只会"续写"，不会"回答"
   输入："什么是机器学习？"
   预训练模型输出："什么是深度学习？什么是人工智能？"（继续提问）
   
2. 不理解指令格式
   无法区分用户输入和助手回复
   
3. 缺乏对齐
   可能生成有害、不准确或不相关的内容

SFT的作用：
1. 学习对话格式（ChatML格式）
2. 学会回答而非续写
3. 初步对齐人类意图
```

#### 6.0.2 SFT数据格式详解

```
ChatML格式详解：

<|im_start|>system
你是一个有帮助的AI助手。<|im_end|>
<|im_start|>user
什么是机器学习？<|im_end|>
<|im_start|>assistant
机器学习是人工智能的一个分支...<|im_end|>

格式说明：
- <|im_start|>role：角色开始标记
- <|im_end|>：角色结束标记
- role可以是：system、user、assistant

为什么使用ChatML？
1. 明确的角色边界
2. 支持多轮对话
3. 易于解析和处理
4. 与主流模型（Qwen、GLM等）兼容
```

#### 6.0.3 SFT训练策略

```
SFT训练的关键设置：

1. 学习率
   - 预训练学习率：5e-4
   - SFT学习率：1e-5 到 1e-4
   - 原因：微调需要小幅度调整，避免破坏预训练知识

2. 训练轮数
   - 预训练：1-3轮
   - SFT：3-10轮
   - 原因：SFT数据量小，需要多轮学习

3. 损失计算
   - 预训练：计算所有token的损失
   - SFT：只计算assistant回复的损失
   - 原因：避免模型学习模仿用户

4. 数据配比
   - 多任务混合：不同类型任务的数据混合
   - 数据增强：改写、翻译等方式扩充数据
   - 质量优先：高质量数据比大量数据更重要
```

### 6.0.4 SFT数据质量标准

| 维度 | 高质量标准 | 低质量示例 |
|------|-----------|-----------|
| 指令清晰度 | 明确、具体、可执行 | 模糊、多义、不完整 |
| 回复相关性 | 直接回答问题 | 偏题、答非所问 |
| 回复准确性 | 事实正确、逻辑清晰 | 错误信息、逻辑混乱 |
| 回复完整性 | 充分回答、有示例 | 过于简短、信息不足 |
| 语言流畅性 | 自然、流畅、专业 | 生硬、语法错误 |

### 6.1 SFT微调脚本完整解析
  
  ```python
"""
SFT微调脚本
位置：3-full_sft.py
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
import argparse
import os

from model.model import MiniMindLM
from model.LMConfig import LMConfig
from dataset.lm_dataset import SFTDataset
from transformers import AutoTokenizer


def train_sft(args):
    """
    SFT训练函数
    
    SFT与预训练的主要区别：
    1. 数据格式：对话数据而非纯文本
    2. 损失计算：只计算assistant回复部分
    3. 学习率：通常更小
    4. 训练轮数：通常更多
    """
    # 设备
    device = args.device
    
    # 加载分词器
    tokenizer = AutoTokenizer.from_pretrained('./model/minimind_tokenizer')
    
    # 创建模型配置
    lm_config = LMConfig(
        dim=args.dim,
        n_layers=args.n_layers,
        max_seq_len=args.max_seq_len
    )
    
    # 创建模型
    model = MiniMindLM(lm_config).to(device)
    
    # 加载预训练权重
    if args.pretrain_path:
        checkpoint = torch.load(args.pretrain_path, map_location=device)
        model.load_state_dict(checkpoint['model'])
        print(f"加载预训练权重: {args.pretrain_path}")
    
    # 创建数据集
    train_dataset = SFTDataset(
        args.data_path,
        tokenizer,
        max_length=lm_config.max_seq_len
    )
    
    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.num_workers
    )
    
    # 优化器
    optimizer = optim.AdamW(
        model.parameters(),
        lr=args.learning_rate,
        weight_decay=0.01
    )
    
    # 训练循环
    model.train()
    
    for epoch in range(args.epochs):
        for step, batch in enumerate(train_loader):
            input_ids = batch['input_ids'].to(device)
            labels = batch['labels'].to(device)
            
            # 前向传播
            outputs = model(input_ids)
            logits = outputs.logits
            
            # 计算损失
            loss = nn.functional.cross_entropy(
                logits.view(-1, logits.size(-1)),
                labels.view(-1),
                ignore_index=-100
            )
            
            # 反向传播
            optimizer.zero_grad()
            loss.backward()
            
            # 梯度裁剪
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            
            # 更新参数
            optimizer.step()
            
            # 日志
            if step % 10 == 0:
                print(f"Epoch {epoch}, Step {step}, Loss: {loss.item():.4f}")
    
    # 保存模型
    torch.save(model.state_dict(), f'{args.out_dir}/full_sft_{args.dim}.pth')
    print("SFT训练完成！")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="MiniMind SFT")
    parser.add_argument("--out_dir", type=str, default="out")
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch_size", type=int, default=16)
    parser.add_argument("--learning_rate", type=float, default=1e-5)
    parser.add_argument("--device", type=str, default="cuda:0")
    parser.add_argument("--dim", type=int, default=512)
    parser.add_argument("--n_layers", type=int, default=8)
    parser.add_argument("--max_seq_len", type=int, default=512)
    parser.add_argument("--data_path", type=str, default="./dataset/sft_mini_512.jsonl")
    parser.add_argument("--pretrain_path", type=str, default="./out/pretrain_512.pth")
    parser.add_argument("--num_workers", type=int, default=1)
    
    args = parser.parse_args()
    train_sft(args)
```

---

## 7. LoRA微调

LoRA（Low-Rank Adaptation）是一种参数高效的微调方法，它通过在预训练权重旁边添加低秩分解矩阵来实现微调，大幅减少了需要训练的参数量。

### 7.0 LoRA理论背景

#### 7.0.1 LoRA的核心思想

```
LoRA的核心假设：
模型适应新任务时，权重更新的内在维度很低

数学表达：
假设预训练权重 W₀ ∈ R^(d×k)
微调后的权重 W = W₀ + ΔW
LoRA假设 ΔW 可以分解为低秩矩阵：ΔW = BA

其中：
- B ∈ R^(d×r)：降维矩阵
- A ∈ R^(r×k)：升维矩阵
- r << min(d, k)：秩

前向传播：
h = W₀x + ΔWx = W₀x + BAx

关键优势：
1. 参数量大幅减少
   原始：d × k
   LoRA：d × r + r × k = r × (d + k)
   
2. 训练效率提升
   只需训练A和B，冻结W₀
   
3. 易于切换任务
   不同任务只需不同的LoRA权重
```

#### 7.0.2 LoRA参数详解

```
LoRA关键参数：

1. 秩（rank）
   - 决定低秩矩阵的维度
   - 常用值：4, 8, 16, 32, 64
   - 秩越大，表达能力越强，但参数越多
   
2. 缩放因子（alpha）
   - 控制LoRA输出的影响程度
   - 实际缩放 = alpha / rank
   - 常用值：16, 32
   
3. 目标模块（target_modules）
   - 决定在哪些层应用LoRA
   - 常见选择：
     * 注意力层：wq, wk, wv, wo
     * FFN层：w1, w2, w3
     * 全部：所有线性层
   
4. Dropout
   - LoRA层内部的dropout
   - 防止过拟合
   - 常用值：0.0 - 0.1
```

#### 7.0.3 LoRA参数量计算

```
以MiniMind-26M为例：

原始模型参数：
- dim = 512
- n_layers = 8
- 注意力层：4 × 512 × 512 = 1,048,576 参数/层
- FFN层：3 × 512 × 1408 = 2,158,592 参数/层

LoRA配置：
- rank = 8
- alpha = 16
- target_modules = ['wq', 'wk', 'wv', 'wo', 'w1', 'w2', 'w3']

每层LoRA参数：
- wq: 512 × 8 + 8 × 512 = 8,192
- wk: 512 × 8 + 8 × 512 = 8,192
- wv: 512 × 8 + 8 × 512 = 8,192
- wo: 512 × 8 + 8 × 512 = 8,192
- w1: 512 × 8 + 8 × 1408 = 15,360
- w2: 1408 × 8 + 8 × 512 = 15,360
- w3: 512 × 8 + 8 × 1408 = 15,360

每层总计：78,848 参数
8层总计：630,784 参数

参数占比：630,784 / 26,000,000 ≈ 2.4%

结论：LoRA只需训练约2.4%的参数！
```

#### 7.0.4 LoRA vs 全参数微调对比

| 特性 | 全参数微调 | LoRA微调 |
|------|-----------|---------|
| 可训练参数量 | 100% | 1-5% |
| 显存占用（训练） | 高 | 低 |
| 训练速度 | 慢 | 快 |
| 模型性能 | 最优 | 接近最优 |
| 多任务切换 | 需要完整权重 | 只需切换LoRA |
| 实现复杂度 | 简单 | 中等 |
| 适用场景 | 资源充足 | 资源受限 |

### 7.1 LoRA微调脚本完整解析
  
  ```python
"""
LoRA微调脚本
位置：4-lora_sft.py
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
import argparse
import os
import math

from model.model import MiniMindLM
from model.LMConfig import LMConfig
from dataset.lm_dataset import SFTDataset
from transformers import AutoTokenizer


class LoRALayer(nn.Module):
    """
    LoRA层
    
    LoRA的核心思想：在预训练权重旁边添加低秩分解矩阵
    
    公式：
        W' = W + BA
        其中 B ∈ R^(d×r), A ∈ R^(r×k)
        r << min(d, k) 是秩
    
    参数量对比：
        原始：d × k
        LoRA：d × r + r × k = r × (d + k)
        
        当 r << min(d, k) 时，参数量大幅减少
    
    例如：
        d = 512, k = 512, r = 8
        原始：512 × 512 = 262,144
        LoRA：8 × (512 + 512) = 8,192
        减少了 97% 的参数
    """
    
    def __init__(self, in_features: int, out_features: int, rank: int = 8, alpha: float = 16.0):
        """
        初始化LoRA层
        
        参数:
            in_features: 输入维度
            out_features: 输出维度
            rank: LoRA秩
            alpha: 缩放因子
        """
        super().__init__()
        
        self.rank = rank
        self.alpha = alpha
        self.scaling = alpha / rank
        
        # 低秩矩阵
        # A: 随机初始化
        self.lora_A = nn.Parameter(torch.randn(rank, in_features) * 0.01)
        # B: 初始化为零，确保初始时LoRA不起作用
        self.lora_B = nn.Parameter(torch.zeros(out_features, rank))
    
    def forward(self, x: torch.Tensor, original_output: torch.Tensor) -> torch.Tensor:
        """
        前向传播
        
        参数:
            x: 输入张量
            original_output: 原始层的输出
            
        返回:
            添加LoRA调整后的输出
        """
        # 计算 LoRA 输出
        # x @ A^T @ B^T * scaling
        lora_output = (x @ self.lora_A.T @ self.lora_B.T) * self.scaling
        
        return original_output + lora_output


def apply_lora_to_model(model, rank=8, alpha=16.0, target_modules=['wq', 'wk', 'wv', 'wo', 'w1', 'w2', 'w3']):
    """
    将LoRA应用到模型
    
    参数:
        model: 原始模型
        rank: LoRA秩
        alpha: 缩放因子
        target_modules: 要应用LoRA的模块名
        
    返回:
        应用了LoRA的模型
    """
    for name, module in model.named_modules():
        # 检查是否是目标模块
        for target in target_modules:
            if target in name and isinstance(module, nn.Linear):
                # 创建LoRA层
                lora_layer = LoRALayer(
                    module.in_features,
                    module.out_features,
                    rank=rank,
                    alpha=alpha
                )
                
                # 将LoRA层添加到模块
                setattr(module, 'lora', lora_layer)
                
                # 冻结原始权重
                module.weight.requires_grad = False
    
    return model


def train_lora(args):
    """
    LoRA训练函数
    """
    device = args.device
    
    # 加载分词器
    tokenizer = AutoTokenizer.from_pretrained('./model/minimind_tokenizer')
    
    # 创建模型
    lm_config = LMConfig(dim=args.dim, n_layers=args.n_layers)
    model = MiniMindLM(lm_config).to(device)
    
    # 加载预训练权重
    checkpoint = torch.load(args.pretrain_path, map_location=device)
    model.load_state_dict(checkpoint['model'])
    
    # 应用LoRA
    model = apply_lora_to_model(model, rank=args.lora_rank, alpha=args.lora_alpha)
    
    # 只训练LoRA参数
    lora_params = [p for n, p in model.named_parameters() if 'lora' in n and p.requires_grad]
    
    print(f"LoRA参数量: {sum(p.numel() for p in lora_params) / 1e6:.2f}M")
    
    # 优化器
    optimizer = optim.AdamW(lora_params, lr=args.learning_rate)
    
    # 数据集
    train_dataset = SFTDataset(args.data_path, tokenizer, max_length=lm_config.max_seq_len)
    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True)
    
    # 训练
    model.train()
    
    for epoch in range(args.epochs):
        for step, batch in enumerate(train_loader):
            input_ids = batch['input_ids'].to(device)
            labels = batch['labels'].to(device)
            
            # 前向传播
            outputs = model(input_ids)
            loss = nn.functional.cross_entropy(
                outputs.logits.view(-1, outputs.logits.size(-1)),
                labels.view(-1),
                ignore_index=-100
            )
            
            # 反向传播
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            if step % 10 == 0:
                print(f"Epoch {epoch}, Step {step}, Loss: {loss.item():.4f}")
    
    # 保存LoRA权重
    lora_state_dict = {n: p for n, p in model.named_parameters() if 'lora' in n}
    torch.save(lora_state_dict, f'{args.out_dir}/lora_{args.dim}.pth')
    print("LoRA训练完成！")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="MiniMind LoRA SFT")
    parser.add_argument("--dim", type=int, default=512)
    parser.add_argument("--n_layers", type=int, default=8)
    parser.add_argument("--lora_rank", type=int, default=8)
    parser.add_argument("--lora_alpha", type=float, default=16.0)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch_size", type=int, default=16)
    parser.add_argument("--learning_rate", type=float, default=1e-4)
    parser.add_argument("--device", type=str, default="cuda:0")
    parser.add_argument("--data_path", type=str, default="./dataset/sft_mini_512.jsonl")
    parser.add_argument("--pretrain_path", type=str, default="./out/pretrain_512.pth")
    parser.add_argument("--out_dir", type=str, default="out")
    
    args = parser.parse_args()
    train_lora(args)
```

---

## 8. DPO强化学习

DPO（Direct Preference Optimization）是一种简单高效的强化学习方法。

```python
"""
DPO训练脚本
位置：5-dpo_train.py
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
import argparse
import json

from model.model import MiniMindLM
from model.LMConfig import LMConfig
from transformers import AutoTokenizer


class DPODataset(Dataset):
    """
    DPO数据集
    
    数据格式：
    {
        "prompt": "用户问题",
        "chosen": "好的回答",
        "rejected": "差的回答"
    }
    """
    
    def __init__(self, data_path: str, tokenizer, max_length: int = 512):
        self.tokenizer = tokenizer
        self.max_length = max_length
        
        self.data = []
        with open(data_path, 'r', encoding='utf-8') as f:
            for line in f:
                self.data.append(json.loads(line.strip()))
    
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        item = self.data[idx]
        
        # 编码prompt + chosen
        chosen_encoding = self.tokenizer(
            item['prompt'] + item['chosen'],
            max_length=self.max_length,
            truncation=True,
            padding='max_length',
            return_tensors='pt'
        )
        
        # 编码prompt + rejected
        rejected_encoding = self.tokenizer(
            item['prompt'] + item['rejected'],
            max_length=self.max_length,
            truncation=True,
            padding='max_length',
            return_tensors='pt'
        )
        
        return {
            'chosen_input_ids': chosen_encoding['input_ids'].squeeze(0),
            'rejected_input_ids': rejected_encoding['input_ids'].squeeze(0)
        }


def dpo_loss(
    policy_chosen_logps: torch.Tensor,
    policy_rejected_logps: torch.Tensor,
    reference_chosen_logps: torch.Tensor,
    reference_rejected_logps: torch.Tensor,
    beta: float = 0.1
) -> torch.Tensor:
    """
    DPO损失函数
    
    公式：
        L = -E[log σ(β * (log π(y_chosen|x) - log π(y_rejected|x) 
                          - log π_ref(y_chosen|x) + log π_ref(y_rejected|x)))]
    
    参数:
        policy_chosen_logps: 策略模型对chosen的对数概率
        policy_rejected_logps: 策略模型对rejected的对数概率
        reference_chosen_logps: 参考模型对chosen的对数概率
        reference_rejected_logps: 参考模型对rejected的对数概率
        beta: KL散度惩罚系数
        
    返回:
        DPO损失
    """
    # 计算对数比率
    chosen_logratios = policy_chosen_logps - reference_chosen_logps
    rejected_logratios = policy_rejected_logps - reference_rejected_logps
    
    # DPO损失
    loss = -F.logsigmoid(beta * (chosen_logratios - rejected_logratios)).mean()
    
    return loss


def get_logprobs(model, input_ids):
    """
    计算模型对输入的对数概率
    
    参数:
        model: 语言模型
        input_ids: 输入token ID
        
    返回:
        对数概率
    """
    outputs = model(input_ids)
    logits = outputs.logits
    
    # 计算对数概率
    log_probs = F.log_softmax(logits, dim=-1)
    
    # 获取实际token的对数概率
    token_log_probs = log_probs.gather(2, input_ids.unsqueeze(-1)).squeeze(-1)
    
    # 求和得到序列对数概率
    return token_log_probs.sum(dim=-1)


def train_dpo(args):
    """
    DPO训练函数
    """
    device = args.device
    
    # 加载分词器
    tokenizer = AutoTokenizer.from_pretrained('./model/minimind_tokenizer')
    
    # 创建策略模型
    lm_config = LMConfig(dim=args.dim, n_layers=args.n_layers)
    policy_model = MiniMindLM(lm_config).to(device)
    
    # 加载SFT权重
    checkpoint = torch.load(args.sft_path, map_location=device)
    policy_model.load_state_dict(checkpoint)
    
    # 创建参考模型（冻结）
    reference_model = MiniMindLM(lm_config).to(device)
    reference_model.load_state_dict(checkpoint)
    reference_model.eval()
    for param in reference_model.parameters():
        param.requires_grad = False
    
    # 数据集
    train_dataset = DPODataset(args.data_path, tokenizer, max_length=lm_config.max_seq_len)
    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True)
    
    # 优化器
    optimizer = optim.AdamW(policy_model.parameters(), lr=args.learning_rate)
    
    # 训练
    policy_model.train()
    
    for epoch in range(args.epochs):
        for step, batch in enumerate(train_loader):
            chosen_input_ids = batch['chosen_input_ids'].to(device)
            rejected_input_ids = batch['rejected_input_ids'].to(device)
            
            # 计算策略模型的对数概率
            policy_chosen_logps = get_logprobs(policy_model, chosen_input_ids)
            policy_rejected_logps = get_logprobs(policy_model, rejected_input_ids)
            
            # 计算参考模型的对数概率
            with torch.no_grad():
                reference_chosen_logps = get_logprobs(reference_model, chosen_input_ids)
                reference_rejected_logps = get_logprobs(reference_model, rejected_input_ids)
            
            # 计算DPO损失
            loss = dpo_loss(
                policy_chosen_logps,
                policy_rejected_logps,
                reference_chosen_logps,
                reference_rejected_logps,
                beta=args.beta
            )
            
            # 反向传播
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            if step % 10 == 0:
                print(f"Epoch {epoch}, Step {step}, Loss: {loss.item():.4f}")
    
    # 保存模型
    torch.save(policy_model.state_dict(), f'{args.out_dir}/dpo_{args.dim}.pth')
    print("DPO训练完成！")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="MiniMind DPO")
    parser.add_argument("--dim", type=int, default=512)
    parser.add_argument("--n_layers", type=int, default=8)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch_size", type=int, default=4)
    parser.add_argument("--learning_rate", type=float, default=1e-6)
    parser.add_argument("--beta", type=float, default=0.1)
    parser.add_argument("--device", type=str, default="cuda:0")
    parser.add_argument("--data_path", type=str, default="./dataset/dpo_data.jsonl")
    parser.add_argument("--sft_path", type=str, default="./out/full_sft_512.pth")
    parser.add_argument("--out_dir", type=str, default="out")
    
    args = parser.parse_args()
    train_dpo(args)
```

---

## 9. 模型推理

```python
"""
模型推理脚本
位置：2-eval.py
"""

import torch
import argparse
from transformers import AutoTokenizer

from model.model import MiniMindLM
from model.LMConfig import LMConfig


def generate(
    model,
    tokenizer,
    prompt: str,
    max_new_tokens: int = 100,
    temperature: float = 0.7,
    top_k: int = 50,
    top_p: float = 0.9,
    device: str = "cuda:0"
):
    """
    文本生成函数
    
    参数:
        model: 语言模型
        tokenizer: 分词器
        prompt: 输入提示
        max_new_tokens: 最大生成token数
        temperature: 温度参数
        top_k: top-k采样
        top_p: nucleus采样
        device: 设备
        
    返回:
        生成的文本
    """
    model.eval()
    
    # 编码输入
    input_ids = tokenizer.encode(prompt, return_tensors='pt').to(device)
    
    # 生成
    with torch.no_grad():
        output_ids = model.generate(
            input_ids,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_k=top_k,
            top_p=top_p
        )
    
    # 解码
    output_text = tokenizer.decode(output_ids[0], skip_special_tokens=True)
    
    return output_text


def main():
    parser = argparse.ArgumentParser(description="MiniMind Inference")
    parser.add_argument("--weight", type=str, default="full_sft")
    parser.add_argument("--dim", type=int, default=512)
    parser.add_argument("--n_layers", type=int, default=8)
    parser.add_argument("--device", type=str, default="cuda:0")
    
    args = parser.parse_args()
    
    # 加载分词器
    tokenizer = AutoTokenizer.from_pretrained('./model/minimind_tokenizer')
    
    # 创建模型
    lm_config = LMConfig(dim=args.dim, n_layers=args.n_layers)
    model = MiniMindLM(lm_config).to(args.device)
    
    # 加载权重
    weight_path = f'./out/{args.weight}_{args.dim}.pth'
    checkpoint = torch.load(weight_path, map_location=args.device)
    model.load_state_dict(checkpoint['model'] if 'model' in checkpoint else checkpoint)
    
    print(f"加载模型: {weight_path}")
    print("输入 'quit' 退出")
    
    # 交互式对话
    while True:
        prompt = input("\n用户: ")
        if prompt.lower() == 'quit':
            break
        
        # 格式化输入
        formatted_prompt = f"<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n"
        
        # 生成回复
        response = generate(model, tokenizer, formatted_prompt, device=args.device)
        
        # 提取助手回复
        if '<|im_start|>assistant' in response:
            response = response.split('<|im_start|>assistant')[-1]
        if '<|im_end|>' in response:
            response = response.split('<|im_end|>')[0]
        
        print(f"助手: {response.strip()}")


if __name__ == '__main__':
    main()
```

---

## 10. 分词器（Tokenizer）详解

分词器是语言模型的重要组成部分，负责将文本转换为模型可以处理的token序列。MiniMind使用自定义的分词器，词汇表大小为6400，远小于GPT-2的50257。

### 10.1 分词器的基本概念

```python
"""
分词器工作流程

1. 文本输入: "你好，世界！"
       │
       ▼
2. 分词（Tokenize）: ["你", "好", "，", "世界", "！"]
       │
       ▼
3. 转换为ID: [1024, 2048, 512, 3456, 1025]
       │
       ▼
4. 嵌入查找: 每个ID查表得到向量
       │
       ▼
5. 模型输入: tensor(batch, seq_len, hidden_dim)
```

### 10.2 BPE分词器原理

MiniMind采用基于BPE（Byte Pair Encoding）的分词器，其核心思想：

```
原始文本: "神经网络"
字符级: ["神", "经", "网", "络"]
词汇表: ["神", "经", "网", "络", "神经", "网络"]

BPE合并规则:
1. 统计相邻字符对出现频率
2. 找到最高频的对: "神"+"经" = "神经" (出现100次)
3. 合并为新token: "神经"
4. 重复直到达到目标词汇量
```

BPE的优势：
- 平衡词级和字符级的粒度
- 能够处理未登录词（OOV）
- 压缩率高，词汇表紧凑
- 跨语言适应性较好

### 10.3 分词器实现详解

```python
"""
MiniMind分词器实现

分词器通常包含以下组件：
1. 词汇表（vocab）：token到ID的映射
2. 合并规则（merges）：BPE合并操作
3. 特殊token：<|im_start|>, <|im_end|>, <pad>等
"""

# 分词器使用示例
from transformers import AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained('./model/minimind_tokenizer')

# 单条文本分词
text = "你好，世界！"
tokens = tokenizer.tokenize(text)
# tokens: ['你', '好', '，', '世界', '！']

# 转换为ID
ids = tokenizer.encode(text)
# ids: [1024, 2048, 512, 3456, 1025]

# 解码回文本
decoded = tokenizer.decode(ids)
# decoded: "你好，世界！"

# 批量处理
batch_texts = ["你好", "世界"]
batch_ids = tokenizer(batch_texts, padding=True, truncation=True, return_tensors='pt')
```

### 10.4 ChatML格式

MiniMind使用ChatML格式处理对话：

```
格式规范:
<|im_start|>system
系统消息<|im_end|>
<|im_start|>user
用户消息<|im_end|>
<|im_start|>assistant
助手回复<|im_end|>

示例:
<|im_start|>user
今天天气如何？<|im_end|>
<|im_start|>assistant
今天天气晴朗，温度20-25度。<|im_end|>
```

为什么使用特殊token？
- 明确标识角色边界
- 便于模型学习对话结构
- 支持多轮对话
- 避免注入攻击

---

## 11. 优化器与学习率调度

### 11.1 AdamW优化器详解

AdamW（Adam with Weight Decay）是训练大模型的标配优化器。

```python
"""
AdamW算法详解

AdamW是Adam的变体，区别在于权重衰减的方式。

Adam的权重衰减:
    θ = θ - α * (grad / (√v + ε)) - α * λ * θ

AdamW的权重衰减:
    θ = θ - α * (grad / (√v + ε)) - α * λ * θ
                                ↑
                    这里AdamW的衰减是独立的

数学公式:
    m_t = β₁ * m_{t-1} + (1 - β₁) * g_t        # 梯度的一阶矩估计（动量）
    v_t = β₂ * v_{t-1} + (1 - β₂) * g_t²      # 梯度的一阶矩估计（方差）
    m_hat = m_t / (1 - β₁^t)                    # 偏差校正
    v_hat = v_t / (1 - β₂^t)                    # 偏差校正
    θ = θ - α * m_hat / (√v_hat + ε) - α * λ * θ  # 参数更新

MiniMind配置:
    lr = 5e-4          # 学习率
    β₁ = 0.9           # 动量
    β₂ = 0.95          # 方差衰减
    weight_decay = 0.1 # 权重衰减
"""
```

AdamW vs SGD：
- AdamW收敛更快
- SGD泛化性能可能更好
- 小模型训练常用AdamW
- 大模型常用AdamW + 梯度裁剪

### 11.2 学习率调度策略

```python
"""
MiniMind使用的学习率调度：余弦退火

公式：
    lr(t) = lr_min + 0.5 * (lr_max - lr_min) * (1 + cos(π * t / T))

其中：
    lr(t): 时间t的学习率
    lr_min: 最小学习率（通常为lr_max的1/10）
    lr_max: 最大学习率
    t: 当前步数
    T: 总步数

调度曲线：
    lr
    ^
    |‾‾‾‾‾‾‾‾‾‾
    |           ‾‾‾‾‾‾
    |                 ‾‾‾
    |                     ‾
    |                       ‾‾
    |                            ‾‾‾
    +---------------------------> t
"""

def get_cosine_lr(current_step, total_steps, lr_max, lr_min=None):
    """
    计算余弦退火学习率
    
    参数:
        current_step: 当前步数
        total_steps: 总步数
        lr_max: 最大学习率
        lr_min: 最小学习率，默认为lr_max/10
    """
    if lr_min is None:
        lr_min = lr_max / 10
    
    progress = current_step / total_steps
    return lr_min + 0.5 * (lr_max - lr_min) * (1 + math.cos(math.pi * progress))

# 学习率预热（Warmup）
def get_warmup_cosine_lr(current_step, warmup_steps, total_steps, lr_max):
    """
    带预热的余弦退火学习率
    
    前warmup_steps步线性增加学习率
    之后使用余弦退火
    """
    if current_step < warmup_steps:
        # 线性预热
        return lr_max * current_step / warmup_steps
    else:
        # 余弦退火
        progress = (current_step - warmup_steps) / (total_steps - warmup_steps)
        return lr_max * 0.5 * (1 + math.cos(math.pi * progress))
```

### 11.3 梯度裁剪与梯度累积

```python
"""
梯度裁剪（Gradient Clipping）

目的：防止梯度爆炸

公式：
    if ||g|| > threshold:
        g = g * threshold / ||g||

MiniMind配置：
    grad_clip = 1.0  # 裁剪阈值
"""

# PyTorch实现
torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)

"""
梯度累积（Gradient Accumulation）

目的：在显存有限的情况下模拟大batch训练

原理：
    正常: batch_size=32, 直接更新
    累积: batch_size=8, 累积4次后更新
    
    effective_batch_size = batch_size * accumulation_steps
"""

# 梯度累积示例
accumulation_steps = 4
batch_size = 8
effective_batch_size = batch_size * accumulation_steps  # 32

for step, batch in enumerate(dataloader):
    # 前向传播
    loss = model(batch)
    loss = loss / accumulation_steps  # 缩放损失
    loss.backward()  # 反向传播，累积梯度
    
    if (step + 1) % accumulation_steps == 0:
        # 累积了4个batch的梯度后更新
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        optimizer.zero_grad()
```

---

## 12. 混合精度训练

### 12.1 为什么需要混合精度？

```
精度类型对比：

float32 (单精度):
    - 32位浮点数
    - 精度最高，显存占用大
    - 训练和推理都可用

float16 (半精度):
    - 16位浮点数
    - 精度较低，显存占用小
    - 可能出现数值溢出

bfloat16 (BF16):
    - 16位浮点数
    - 与float32相同的指数范围
    - 精度介于float32和float16之间
    - 大模型训练推荐使用

显存占用对比（以26M参数为例）：
    float32: 26M * 4 bytes = 104 MB
    float16: 26M * 2 bytes = 52 MB
    bf16:    26M * 2 bytes = 52 MB
    
    梯度（与权重同尺寸）:
    优化器状态（AdamW需要2倍权重大小）:
    
    总计:
    float32: 104 + 104 + 208 = 416 MB
    bf16:    52 + 52 + 104 = 208 MB (减少50%)
```

### 12.2 PyTorch混合精度实现

```python
"""
PyTorch混合精度训练示例
"""

from torch.cuda.amp import autocast, GradScaler

# 创建梯度缩放器
scaler = GradScaler()

model = model.to('cuda')
model.train()

for batch in dataloader:
    input_ids = batch['input_ids'].to('cuda')
    labels = batch['labels'].to('cuda')
    
    optimizer.zero_grad()
    
    # 前向传播 - 自动使用半精度
    with autocast(dtype=torch.bfloat16):
        outputs = model(input_ids)
        loss = F.cross_entropy(outputs.logits.view(-1, outputs.logits.size(-1)), labels)
    
    # 反向传播 - 损失需要缩放
    scaler.scale(loss).backward()
    
    # 梯度裁剪（需要先unscale）
    scaler.unscale_(optimizer)
    torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
    
    # 参数更新 - 自动处理缩放
    scaler.step(optimizer)
    scaler.update()
```

### 12.3 Flash Attention

```python
"""
Flash Attention详解

标准注意力的问题：
- 需要O(n²)的显存存储注意力分数矩阵
- 大量HBM（高带宽内存）访问
- 训练长序列时显存爆炸

Flash Attention的解决方案：
- 分块计算，避免存储完整注意力矩阵
- IO感知设计，减少HBM访问
- 显存从O(n²)降到O(n)

公式：
    使用分块归一化：
    softmax(X) = normalize(exp(X - max(X)))
    
    分块计算时需要：
    1. 按块计算局部softmax
    2. 正确处理数值稳定性
    3. 合并得到全局结果

PyTorch使用：
    F.scaled_dot_product_attention(
        q, k, v,
        attn_mask=None,
        dropout_p=0.0,
        is_causal=True  # 自动生成causal mask
    )
"""

# MiniMind中的Flash Attention配置
config = LMConfig(flash_attn=True)  # 默认启用

# 条件判断
if config.flash_attn and hasattr(F, 'scaled_dot_product_attention'):
    # 使用Flash Attention
    output = F.scaled_dot_product_attention(xq, xk, xv, is_causal=True)
else:
    # 回退到标准实现
    output = standard_attention(xq, xk, xv)
```

---

## 13. 分布式训练

### 13.1 DDP（Distributed Data Parallel）

```python
"""
DDP分布式数据并行训练

工作原理：
1. 每个进程有完整的模型副本
2. 数据在不同进程间分割
3. 每个进程独立前向传播和反向传播
4. 梯度通过AllReduce同步
5. 所有进程以相同的参数更新

优势：
- 线性加速比（接近理想值）
- 通信开销小
- 容错性好
"""

# 初始化
import torch.distributed as dist

dist.init_process_group(backend='nccl')  # NCCL用于GPU通信
local_rank = int(os.environ['LOCAL_RANK'])
torch.cuda.set_device(local_rank)

# 包装模型
model = model.to(local_rank)
model = DDP(model, device_ids=[local_rank])

# 数据加载
train_sampler = DistributedSampler(dataset)
dataloader = DataLoader(dataset, sampler=train_sampler)

# 训练循环
for epoch in range(num_epochs):
    train_sampler.set_epoch(epoch)  # 打乱数据
    for batch in dataloader:
        # 数据移到当前GPU
        batch = batch.to(local_rank)
        
        outputs = model(batch)
        loss = outputs.loss / gradient_accumulation_steps
        loss.backward()
        
        # 优化器更新
        optimizer.step()
        optimizer.zero_grad()
```

### 13.2 DeepSpeed ZeRO优化

```python
"""
DeepSpeed ZeRO（Zero Redundancy Optimizer）

ZeRO有三个阶段：

ZeRO-1:
    - 优化器状态分片
    - 减少约4倍显存

ZeRO-2:
    - 优化器状态 + 梯度分片
    - 减少约8倍显存

ZeRO-3:
    - 优化器状态 + 梯度 + 参数分片
    - 减少约N倍显存（N=GPU数量）

配置示例：
{
    "train_batch_size": 32,
    "gradient_accumulation_steps": 4,
    "fp16": {"enabled": True},
    "zero_optimization": {
        "stage": 2,
        "offload_optimizer": {"device": "cpu"}
    }
}
"""

# 使用DeepSpeed启动
# deepspeed --num_gpus=4 train.py
```

---

## 14. 推理优化

### 14.1 KV缓存机制

```python
"""
KV缓存（Key-Value Cache）

推理时的痛点：
- 生成第N个token时，需要重新计算前N-1个token的注意力
- 时间复杂度O(n²)，n为序列长度
- 大量重复计算

KV缓存的解决方案：
- 首次前向传播：计算并缓存所有K和V
- 后续前向传播：只计算新token的K和V，拼接历史缓存

实现：
    # 首次推理
    outputs = model(input_ids)  # input_ids: [1, 10]
    past_kv = outputs.past_key_values
    
    # 增量推理
    outputs = model(
        input_ids[:, -1:],      # 只输入新token
        past_key_values=past_kv  # 传入缓存
    )
    
    # 缓存会自动更新：cat([past_k, new_k], dim=1)
"""

# MiniMind生成函数中的KV缓存使用
def generate(self, input_ids, max_new_tokens=100, ...):
    past_key_values = None
    
    for _ in range(max_new_tokens):
        outputs = self.forward(
            input_ids if past_key_values is None else input_ids[:, -1:],
            past_key_values=past_key_values,
            use_cache=True
        )
        
        past_key_values = outputs.past_key_values
        logits = outputs.logits[:, -1, :]
        
        # ... 采样下一个token
        next_token = ...
        
        input_ids = torch.cat([input_ids, next_token], dim=-1)
    
    return input_ids
```

### 14.2 采样策略

```python
"""
文本生成的采样策略

1. Greedy Search（贪心搜索）
   - 总是选择概率最高的token
   - 缺点：容易陷入重复循环
   - 用途：确定性任务

2. Top-K Sampling
   - 从概率最高的K个token中随机选择
   - 引入随机性，增加多样性
   - K的选择很关键：太小限制多样，太大可能选到低质量token

3. Nucleus Sampling (Top-P)
   - 从累积概率达到P的最小token集合中采样
   - 自适应地调整候选token数量
   - 通常比Top-K更稳定

4. Temperature Sampling
   - 控制概率分布的平滑度
   - T>1：分布更平坦，增加多样性
   - T<1：分布更尖锐，增加确定性
   - T=1：原始分布
"""

def sample_with_temperature(logits, temperature=1.0):
    """应用温度缩放"""
    if temperature != 1.0:
        logits = logits / temperature
    return logits

def top_k_sample(probs, k=50):
    """Top-K采样"""
    top_k_probs, top_k_indices = torch.topk(probs, k)
    # 从top-k中按概率采样
    sampled_idx = torch.multinomial(top_k_probs, 1)
    return top_k_indices[sampled_idx]

def nucleus_sample(probs, p=0.9):
    """Nucleus (Top-P) 采样"""
    sorted_probs, sorted_indices = torch.sort(probs, descending=True)
    cumulative_probs = torch.cumsum(sorted_probs, dim=-1)
    
    # 找到累积概率超过P的token
    nucleus_mask = cumulative_probs <= p
    # 确保至少包含一个token
    nucleus_mask[..., 1:] = nucleus_mask[..., :-1].clone()
    nucleus_mask[..., 0] = True
    
    # 过滤概率
    nucleus_probs = torch.where(nucleus_mask, sorted_probs, 0)
    nucleus_probs = nucleus_probs / nucleus_probs.sum()
    
    # 采样
    sampled_idx = torch.multinomial(nucleus_probs, 1)
    return sorted_indices[sampled_idx]
```

---

## 15. 常见问题与解决方案

### 15.1 显存问题

```
问题1：CUDA out of memory
原因：显存不足
解决方案：
    - 减小batch_size
    - 启用梯度累积
    - 使用混合精度训练
    - 启用Flash Attention
    - 减少max_seq_len

问题2：梯度爆炸
原因：学习率过高或梯度不稳定
解决方案：
    - 降低学习率
    - 启用梯度裁剪
    - 使用学习率预热
    - 检查数据归一化

问题3：显存泄漏
原因：未正确释放中间变量
解决方案：
    - 及时del不需要的变量
    - 使用torch.cuda.empty_cache()
    - 检查模型是否有多余的缓存
```

### 15.2 训练不稳定

```
问题：loss变成NaN
原因：
    - 混合精度下数值溢出
    - 学习率过高
    - 数据存在异常值
    - 梯度爆炸

解决方案：
    - 切换到bfloat16
    - 降低学习率
    - 检查数据清洗
    - 启用梯度裁剪
    - 添加学习率预热
```

### 15.3 模型不收敛

```
问题：loss不下降或震荡
原因：
    - 学习率不当
    - 数据标注问题
    - 模型容量不足
    - 学习率调度问题

解决方案：
    - 调整学习率（尝试1e-4到1e-5范围）
    - 检查数据质量
    - 增加模型容量
    - 调整学习率调度
    - 增加训练轮数
```

---

## 16. 实践练习题

### 练习1：修改模型配置

```python
"""
练习：创建一个更大规模的MiniMind模型

要求：
- 参数量约100M
- 使用GQA
- 启用MoE

提示：
- 参考LMConfig的默认参数
- 调整dim和n_layers
- 计算参数量验证
"""

# 你的代码：
config = LMConfig(
    dim=...,      # 调整隐藏维度
    n_layers=..., # 调整层数
    vocab_size=6400,
    use_moe=...,  # 是否启用MoE
)

# 验证参数量
model = MiniMindLM(config)
total_params = sum(p.numel() for p in model.parameters())
print(f"参数量: {total_params / 1e6:.2f}M")
```

### 练习2：实现自定义采样

```python
"""
练习：实现一个带重复惩罚的采样函数

要求：
- 在生成时惩罚已选择过的token
- 惩罚系数可调
- 保持采样多样性

公式：
    logits[token] = logits[token] / (1 + repeat_penalty * count[token])
"""

def sample_with_repetition_penalty(
    logits,
    previous_tokens,
    penalty=1.2
):
    """
    带重复惩罚的采样
    
    参数:
        logits: 模型输出的logits
        previous_tokens: 之前生成的token序列
        penalty: 惩罚系数，>1增加惩罚，<1减少惩罚
    """
    # 统计token出现次数
    token_counts = torch.bincount(previous_tokens, minlength=logits.size(-1))
    
    # 应用惩罚：已出现的token概率降低
    penalties = 1.0 + (token_counts > 0).float() * (penalty - 1.0)
    logits = logits / penalties
    
    return logits
```

### 练习3：分析注意力模式

```python
"""
练习：可视化模型的注意力分布

要求：
- 提取某一层的注意力权重
- 可视化不同位置之间的注意力分布
- 分析模型关注的位置

提示：
- 在attention计算时保存注意力分数
- 使用matplotlib可视化
"""

import matplotlib.pyplot as plt

def visualize_attention(attention_weights, title="Attention Pattern"):
    """
    可视化注意力权重
    
    attention_weights: (seq_len, seq_len) 的注意力矩阵
    """
    plt.figure(figsize=(10, 8))
    plt.imshow(attention_weights.cpu().numpy(), cmap='viridis')
    plt.colorbar()
    plt.title(title)
    plt.xlabel("Key Position")
    plt.ylabel("Query Position")
    plt.show()
```

---

## 总结

通过这份详尽的教程，你已经了解了MiniMind项目的每一个核心组件：

1. **配置系统**：理解了所有超参数的含义和作用
2. **RMSNorm**：掌握了现代LLM的归一化方法
3. **RoPE**：理解了旋转位置编码的数学原理
4. **GQA**：学会了分组查询注意力的实现
5. **SwiGLU**：了解了门控激活函数的优势
6. **MoE**：掌握了混合专家系统的设计
7. **训练流程**：从预训练到DPO的完整流程
8. **Tokenizer**：理解了分词器的原理和实现
9. **优化器**：深入理解了AdamW和学习率调度
10. **混合精度**：掌握了bf16训练和Flash Attention
11. **分布式训练**：理解了DDP和DeepSpeed
12. **推理优化**：学会了KV缓存和采样策略

MiniMind是一个绝佳的学习项目，它用最简洁的代码展示了现代大语言模型的所有核心技术。建议你：

1. **动手实践**：逐行阅读代码，理解每个函数的作用
2. **修改实验**：调整参数，观察模型行为的变化
3. **扩展开发**：尝试在自己的数据上训练，扩展模型功能
4. **深入研究**：阅读相关论文，理解设计背后的理论

## 进一步学习资源

1. **Transformer论文**："Attention Is All You Need"
2. **LLaMA论文**："LLaMA: Open and Efficient Foundation Language Models"
3. **RoPE论文**："RoFormer: Enhanced Transformer with Rotary Position Embedding"
4. **Flash Attention论文**："FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness"
5. **LoRA论文**："LoRA: Low-Rank Adaptation of Large Language Models"
6. **DPO论文**："Direct Preference Optimization: Your Language Model is Secretly a Reward Model"

---

## 17. 核心代码逐行精读

本节将对MiniMind最核心的代码进行逐行精读，帮助读者深入理解每一行代码的设计意图和技术细节。

### 17.1 RMSNorm逐行精读

```python
class RMSNorm(nn.Module):
    def __init__(self, dim: int, eps: float = 1e-6):
        super().__init__()
        # 第1行：定义可学习的缩放参数
        # 为什么需要这个参数？
        # - 归一化后的向量模长为1，但不同特征可能需要不同的缩放
        # - 初始化为全1，表示初始时不改变归一化后的值
        # - 训练过程中会学习到最优的缩放因子
        self.weight = nn.Parameter(torch.ones(dim))
        
        # 第2行：防止除零的epsilon
        # 为什么需要epsilon？
        # - 当输入向量全为0时，RMS = 0，会导致除零错误
        # - epsilon是一个很小的值，确保分母不为0
        # - 通常设置为1e-5或1e-6
        self.eps = eps
    
    def _norm(self, x: torch.Tensor) -> torch.Tensor:
        """
        核心归一化计算
        
        输入x的形状：(batch_size, seq_len, dim)
        """
        # 第1步：x.pow(2) - 对每个元素求平方
        # 例如：x = [1, 2, 3, 4] -> x.pow(2) = [1, 4, 9, 16]
        
        # 第2步：mean(-1, keepdim=True) - 在最后一个维度上求均值
        # keepdim=True 保持维度，便于后续广播
        # 例如：[1, 4, 9, 16] -> mean = 7.5
        # 结果形状：(batch_size, seq_len, 1)
        
        # 第3步：torch.rsqrt() - 计算平方根的倒数
        # rsqrt(x) = 1/sqrt(x)
        # 为什么用rsqrt而不是先sqrt再除？
        # - rsqrt是单次操作，计算效率更高
        # - GPU对rsqrt有专门优化
        
        # 第4步：加epsilon - 防止除零
        
        # 第5步：x * result - 逐元素相乘
        # 广播机制：(batch, seq, dim) * (batch, seq, 1) -> (batch, seq, dim)
        
        return x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + self.eps)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        前向传播
        
        为什么先转为float32再计算？
        - 归一化涉及除法和开方，float16精度不够
        - 可能导致数值不稳定，梯度消失
        - 计算完成后再转回原类型
        
        为什么使用type_as而不是直接float()？
        - type_as保持与输入相同的类型
        - 如果输入是bfloat16，输出也是bfloat16
        - 更加灵活
        """
        # 步骤1：转为float32计算归一化
        # 步骤2：应用可学习的权重
        # 步骤3：转回原数据类型
        return self.weight * self._norm(x.float()).type_as(x)
```

**触类旁通：RMSNorm与其他归一化方法的对比**

| 方法 | 公式 | 参数量 | 计算量 | 适用场景 |
|------|------|--------|--------|----------|
| BatchNorm | (x - μ_B) / σ_B * γ + β | 2×dim | 高 | CNN |
| LayerNorm | (x - μ_L) / σ_L * γ + β | 2×dim | 中 | Transformer |
| RMSNorm | x / RMS(x) * γ | dim | 低 | LLM |
| GroupNorm | 分组LayerNorm | 2×dim | 中 | 图像分割 |

**为什么LLM选择RMSNorm？**

1. **计算效率**：省去均值计算，减少约30%计算量
2. **内存效率**：不需要存储均值和方差用于反向传播
3. **参数效率**：参数量减半
4. **实验验证**：在LLaMA等模型上效果相当

### 17.2 RoPE逐行精读

```python
def precompute_pos_cis(dim: int, end: int = int(32 * 1024), theta: float = 1e6):
    """
    预计算旋转位置编码
    
    这个函数在模型初始化时调用一次，生成所有位置的位置编码。
    避免每次前向传播时重复计算，提高效率。
    
    参数说明：
    - dim: 每个注意力头的维度（不是总维度！）
    - end: 最大序列长度，默认32K
    - theta: RoPE的基数，控制频率范围
    
    返回值：
    - pos_cis: 复数张量，形状为 (end, dim//2)
    """
    
    # 第1步：计算不同维度的频率
    # 公式：freq_i = 1 / (theta^(2i/dim))
    # 
    # torch.arange(0, dim, 2)：生成 [0, 2, 4, ..., dim-2]
    # 为什么步长是2？因为每个频率对应两个维度（复数的实部和虚部）
    #
    # 例如：dim=64
    # arange结果：[0, 2, 4, 6, ..., 62]
    # 对应的频率：[1/θ^0, 1/θ^(2/64), 1/θ^(4/64), ...]
    #
    # 频率的意义：
    # - 低维度（小的i）：低频，变化慢，捕获长距离依赖
    # - 高维度（大的i）：高频，变化快，捕获短距离依赖
    freqs = 1.0 / (theta ** (torch.arange(0, dim, 2)[: (dim // 2)].float() / dim))
    # freqs形状：(dim//2,)
    
    # 第2步：生成位置索引
    # torch.arange(end)：生成 [0, 1, 2, ..., end-1]
    # 每个位置都有一个唯一的位置编码
    t = torch.arange(end, device=freqs.device)
    # t形状：(end,)
    
    # 第3步：计算外积
    # torch.outer(a, b)：计算向量a和b的外积
    # 结果[i, j] = a[i] * b[j]
    #
    # 这里：freqs = t ⊗ freqs
    # 结果[i, j] = t[i] * freqs[j] = 位置i * 频率j
    #
    # 这就是每个位置在每个维度上的旋转角度！
    freqs = torch.outer(t, freqs).float()
    # freqs形状：(end, dim//2)
    
    # 第4步：使用欧拉公式生成复数
    # 欧拉公式：e^(i*θ) = cos(θ) + i*sin(θ)
    #
    # torch.polar(abs, angle)：
    # - abs：复数的模（这里全为1，单位圆上的点）
    # - angle：复数的幅角（旋转角度）
    #
    # 结果：每个位置对应一个复数向量
    pos_cis = torch.polar(torch.ones_like(freqs), freqs)
    # pos_cis形状：(end, dim//2)
    # 类型：complex64
    
    return pos_cis


def apply_rotary_emb(xq, xk, pos_cis):
    """
    将旋转位置编码应用到查询和键上
    
    这是RoPE的核心应用函数，在每个注意力层的前向传播中调用。
    
    参数：
    - xq: 查询张量 (batch, seq_len, n_heads, head_dim)
    - xk: 键张量 (batch, seq_len, n_kv_heads, head_dim)
    - pos_cis: 预计算的位置编码 (seq_len, head_dim//2)
    """
    
    # 第1步：扩展位置编码的维度以匹配查询
    # pos_cis原始形状：(seq_len, head_dim//2)
    # 需要扩展为：(batch, seq_len, n_heads, head_dim//2)
    # unsqueeze(0)：在第0维添加维度 -> (1, seq_len, head_dim//2)
    # unsqueeze(2)：在第2维添加维度 -> (1, seq_len, 1, head_dim//2)
    # 这样可以通过广播机制匹配batch和n_heads维度
    pos_cis = pos_cis.unsqueeze(0).unsqueeze(2)
    
    # 第2步：将实数张量转换为复数形式
    # xq原始形状：(batch, seq_len, n_heads, head_dim)
    # 重塑为：(batch, seq_len, n_heads, head_dim//2, 2)
    # 最后一个维度2表示实部和虚部
    #
    # 为什么需要转float()？
    # - view_as_complex要求输入是float类型
    # - 确保数值精度
    xq_ = torch.view_as_complex(xq.float().reshape(*xq.shape[:-1], -1, 2))
    xk_ = torch.view_as_complex(xk.float().reshape(*xk.shape[:-1], -1, 2))
    # xq_形状：(batch, seq_len, n_heads, head_dim//2)
    # 类型：complex64
    
    # 第3步：在复数域中应用旋转
    # 复数乘法：e^(i*θ_m) * e^(i*θ_n) = e^(i*(θ_m + θ_n))
    # 但这里是：xq_ * pos_cis
    # 即：查询向量 * 位置旋转
    #
    # 广播机制：
    # xq_: (batch, seq, heads, dim//2)
    # pos_cis: (1, seq, 1, dim//2)
    # 结果：(batch, seq, heads, dim//2)
    xq_out = torch.view_as_real(xq_ * pos_cis).flatten(3)
    xk_out = torch.view_as_real(xk_ * pos_cis).flatten(3)
    # view_as_real：复数转回实数
    # flatten(3)：将最后两个维度合并
    
    # 第4步：转回原数据类型
    return xq_out.type_as(xq), xk_out.type_as(xk)
```

**触类旁通：RoPE与其他位置编码的对比**

| 方法 | 相对位置 | 外推能力 | 计算复杂度 | 显存占用 |
|------|---------|---------|-----------|---------|
| Sinusoidal | 否 | 差 | O(1) | 少 |
| Learnable | 否 | 差 | O(1) | 少 |
| Relative | 是 | 中 | O(n²) | 多 |
| ALiBi | 是 | 好 | O(1) | 少 |
| RoPE | 是 | 优秀 | O(1) | 少 |

**RoPE的数学直觉**

```
想象一个二维向量 [a, b]：
1. 表示为复数：a + bi
2. 旋转θ角度：(a + bi) * e^(iθ) = (a*cos(θ) - b*sin(θ)) + i*(a*sin(θ) + b*cos(θ))
3. 展开为实数：[a*cos(θ) - b*sin(θ), a*sin(θ) + b*cos(θ)]

这就是旋转矩阵！
[cos(θ)  -sin(θ)] [a]   [a*cos(θ) - b*sin(θ)]
[sin(θ)   cos(θ)] [b] = [a*sin(θ) + b*cos(θ)]

关键性质：
- 旋转不改变向量长度
- 两个旋转后的向量点积包含旋转角度差
- 这就是相对位置信息！
```

### 17.3 Attention逐行精读

```python
class Attention(nn.Module):
    def __init__(self, args):
        super().__init__()
        
        # 存储配置
        self.n_heads = args.n_heads  # Q的总头数
        self.head_dim = args.head_dim  # 每个头的维度
        
        # GQA配置
        # n_kv_heads: K和V的头数
        # 如果n_kv_heads < n_heads，启用GQA
        # 如果n_kv_heads == n_heads，退化为标准MHA
        # 如果n_kv_heads == 1，退化为MQA
        self.n_kv_heads = args.n_kv_heads
        
        # 计算每个KV头对应的Q头数
        # 例如：n_heads=8, n_kv_heads=2 -> n_rep=4
        # 表示每个KV头被4个Q头共享
        self.n_rep = self.n_heads // self.n_kv_heads
        
        # 投影层定义
        # Q投影：将输入投影到n_heads个头
        # 输出维度 = n_heads * head_dim
        self.wq = nn.Linear(args.dim, self.n_heads * self.head_dim, bias=False)
        
        # K投影：将输入投影到n_kv_heads个头
        # 注意：输出维度可能小于Q的维度
        # 例如：dim=512, n_heads=8, n_kv_heads=2
        # wq输出：512, wk输出：128
        self.wk = nn.Linear(args.dim, self.n_kv_heads * self.head_dim, bias=False)
        
        # V投影：与K投影类似
        self.wv = nn.Linear(args.dim, self.n_kv_heads * self.head_dim, bias=False)
        
        # 输出投影：将多头注意力的结果投影回原始维度
        self.wo = nn.Linear(self.n_heads * self.head_dim, args.dim, bias=False)
        
        # 为什么不使用bias？
        # - 减少参数量
        # - 实验表明对性能影响很小
        # - LLaMA等模型都不使用bias
        
        # 注意力缩放因子
        # 1/sqrt(head_dim) 用于缩放点积
        self.scale = 1.0 / math.sqrt(self.head_dim)
    
    def forward(self, x, pos_cis, past_key_value=None, use_cache=False):
        """
        前向传播
        
        参数：
        - x: 输入张量 (batch_size, seq_len, dim)
        - pos_cis: RoPE位置编码
        - past_key_value: KV缓存
        - use_cache: 是否返回KV缓存
        """
        bs, seqlen, _ = x.shape
        
        # ==================== 步骤1：线性投影 ====================
        
        # Q投影：(batch, seq, dim) -> (batch, seq, n_heads * head_dim)
        xq = self.wq(x)
        # K投影：(batch, seq, dim) -> (batch, seq, n_kv_heads * head_dim)
        xk = self.wk(x)
        # V投影：(batch, seq, dim) -> (batch, seq, n_kv_heads * head_dim)
        xv = self.wv(x)
        
        # 重塑为多头形式
        # Q: (batch, seq, n_heads * head_dim) -> (batch, seq, n_heads, head_dim)
        xq = xq.view(bs, seqlen, self.n_heads, self.head_dim)
        # K: (batch, seq, n_kv_heads * head_dim) -> (batch, seq, n_kv_heads, head_dim)
        xk = xk.view(bs, seqlen, self.n_kv_heads, self.head_dim)
        xv = xv.view(bs, seqlen, self.n_kv_heads, self.head_dim)
        
        # ==================== 步骤2：应用RoPE ====================
        
        # RoPE只应用于Q和K，不应用于V
        # 为什么？位置信息通过Q和K的点积传递
        xq, xk = apply_rotary_emb(xq, xk, pos_cis)
        
        # ==================== 步骤3：处理KV缓存 ====================
        
        if past_key_value is not None:
            # KV缓存存在，拼接历史KV
            past_k, past_v = past_key_value
            # 在序列维度上拼接
            xk = torch.cat([past_k, xk], dim=1)
            xv = torch.cat([past_v, xv], dim=1)
        
        # 保存当前KV用于返回
        past_kv = (xk, xv) if use_cache else None
        
        # ==================== 步骤4：重复KV头（GQA核心） ====================
        
        # 转置以适应注意力计算
        # Q: (batch, seq, n_heads, head_dim) -> (batch, n_heads, seq, head_dim)
        xq = xq.transpose(1, 2)
        
        # K和V需要先重复头，再转置
        # repeat_kv: (batch, seq, n_kv_heads, head_dim) -> (batch, seq, n_heads, head_dim)
        xk = repeat_kv(xk, self.n_rep).transpose(1, 2)
        xv = repeat_kv(xv, self.n_rep).transpose(1, 2)
        
        # ==================== 步骤5：计算注意力 ====================
        
        if self.flash:
            # Flash Attention
            # 为什么使用Flash Attention？
            # - 显存从O(n²)降到O(n)
            # - 计算速度更快
            # - 支持因果掩码
            output = F.scaled_dot_product_attention(
                xq, xk, xv,
                dropout_p=self.dropout.p if self.training else 0.0,
                is_causal=True  # 自动应用因果掩码
            )
        else:
            # 手动实现
            # 计算注意力分数：QK^T / sqrt(d_k)
            scores = torch.matmul(xq, xk.transpose(-2, -1)) * self.scale
            
            # 创建因果掩码
            # 上三角为-inf，确保只能看到之前的位置
            seqlen_q = xq.shape[2]
            seqlen_k = xk.shape[2]
            mask = torch.triu(
                torch.full((seqlen_q, seqlen_k), float('-inf'), device=x.device),
                diagonal=1
            )
            scores = scores + mask
            
            # Softmax
            scores = F.softmax(scores, dim=-1)
            scores = self.dropout(scores)
            
            # 加权求和
            output = torch.matmul(scores, xv)
        
        # ==================== 步骤6：输出处理 ====================
        
        # 转置回来
        output = output.transpose(1, 2)
        # 展平多头
        output = output.contiguous().view(bs, seqlen, -1)
        # 输出投影
        output = self.wo(output)
        
        return output, past_kv
```

**触类旁通：GQA vs MHA vs MQA**

```
MHA (Multi-Head Attention):
┌─────────────────────────────────────────────────────────────┐
│  Q: [h1, h2, h3, h4, h5, h6, h7, h8]                        │
│  K: [h1, h2, h3, h4, h5, h6, h7, h8]                        │
│  V: [h1, h2, h3, h4, h5, h6, h7, h8]                        │
│                                                             │
│  每个头独立计算注意力                                         │
│  KV缓存: 8 × seq_len × head_dim                             │
└─────────────────────────────────────────────────────────────┘

GQA (Grouped-Query Attention):
┌─────────────────────────────────────────────────────────────┐
│  Q: [h1, h2, h3, h4, h5, h6, h7, h8]                        │
│  K: [g1, g1, g2, g2, g3, g3, g4, g4]  <- 4组，每组共享        │
│  V: [g1, g1, g2, g2, g3, g3, g4, g4]                        │
│                                                             │
│  每组Q头共享一组KV                                            │
│  KV缓存: 4 × seq_len × head_dim (减少50%)                    │
└─────────────────────────────────────────────────────────────┘

MQA (Multi-Query Attention):
┌─────────────────────────────────────────────────────────────┐
│  Q: [h1, h2, h3, h4, h5, h6, h7, h8]                        │
│  K: [s,  s,  s,  s,  s,  s,  s,  s]   <- 全部共享            │
│  V: [s,  s,  s,  s,  s,  s,  s,  s]                         │
│                                                             │
│  所有Q头共享一组KV                                            │
│  KV缓存: 1 × seq_len × head_dim (减少87.5%)                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 18. 触类旁通：与其他模型架构对比

### 18.1 MiniMind vs GPT-2

| 特性 | MiniMind | GPT-2 |
|------|----------|-------|
| 归一化 | RMSNorm | LayerNorm |
| 位置编码 | RoPE | Learnable |
| 注意力 | GQA | MHA |
| 激活函数 | SwiGLU | GELU |
| FFN结构 | 门控 | 标准 |
| 参数量 | 26M-108M | 117M-1.5B |

```python
# GPT-2的LayerNorm实现
class LayerNorm(nn.Module):
    def __init__(self, hidden_size, eps=1e-5):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(hidden_size))
        self.bias = nn.Parameter(torch.zeros(hidden_size))
        self.eps = eps
    
    def forward(self, x):
        # 计算均值和方差
        mean = x.mean(-1, keepdim=True)
        var = x.var(-1, keepdim=True, unbiased=False)
        # 归一化
        x = (x - mean) / torch.sqrt(var + self.eps)
        # 缩放和平移
        return self.weight * x + self.bias

# MiniMind的RMSNorm实现
class RMSNorm(nn.Module):
    def __init__(self, dim, eps=1e-6):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(dim))
        self.eps = eps
    
    def forward(self, x):
        # 只计算RMS，不计算均值
        return self.weight * self._norm(x.float()).type_as(x)
```

### 18.2 MiniMind vs LLaMA

| 特性 | MiniMind | LLaMA |
|------|----------|-------|
| 架构 | 几乎相同 | 几乎相同 |
| 归一化 | RMSNorm | RMSNorm |
| 位置编码 | RoPE | RoPE |
| 注意力 | GQA | GQA (LLaMA 2+) |
| 激活函数 | SwiGLU | SwiGLU |
| MoE | 可选 | LLaMA 3.1+ |
| 参数量 | 26M-108M | 7B-70B |

**MiniMind可以看作是LLaMA的"缩小版"**，两者的核心架构完全一致，主要区别在于：
1. 参数规模：MiniMind小100-1000倍
2. 词汇表：MiniMind使用自定义小词汇表（6400 vs 32000+）
3. 训练数据：MiniMind使用小规模数据

### 18.3 MiniMind vs Mistral

| 特性 | MiniMind | Mistral |
|------|----------|---------|
| 滑动窗口注意力 | 无 | 有（4096） |
| 滚动缓存 | 无 | 有 |
| 注意力 | GQA | GQA |
| 参数量 | 26M-108M | 7B |

Mistral引入了**滑动窗口注意力**，限制每个token只能关注最近的W个token，这可以：
1. 减少计算量
2. 支持更长序列
3. 与标准注意力结合使用

```python
# 滑动窗口注意力示意
def sliding_window_attention(q, k, v, window_size=4096):
    """
    滑动窗口注意力
    
    每个token只能看到最近的window_size个token
    """
    seq_len = q.shape[2]
    
    # 创建滑动窗口掩码
    # 每行只有window_size个True
    mask = torch.ones(seq_len, seq_len, dtype=torch.bool)
    for i in range(seq_len):
        start = max(0, i - window_size + 1)
        mask[i, :start] = False
    
    # 应用掩码
    # ... 标准注意力计算
```

---

## 19. 实战：从零训练一个MiniMind

### 19.1 准备工作

```bash
# 1. 克隆项目
git clone https://github.com/jingyaogong/minimind.git
cd minimind

# 2. 创建虚拟环境
conda create -n minimind python=3.10
conda activate minimind

# 3. 安装依赖
pip install -r requirements.txt

# 4. 下载数据
# 预训练数据：约1GB高质量中文语料
# SFT数据：约10MB对话数据
```

### 19.2 预训练步骤

```bash
# 单卡训练
python 1-pretrain.py

# 多卡训练（DDP）
torchrun --nproc_per_node=4 1-pretrain.py

# DeepSpeed训练
deepspeed --num_gpus=4 1-pretrain.py
```

### 19.3 训练监控

```python
# 使用wandb监控训练
import wandb

wandb.init(
    project="minimind",
    config={
        "learning_rate": 5e-4,
        "batch_size": 32,
        "epochs": 1,
    }
)

# 在训练循环中记录
wandb.log({
    "loss": loss.item(),
    "learning_rate": current_lr,
    "step": step
})
```

### 19.4 训练时间估算

| 配置 | 参数量 | 数据量 | GPU | 预计时间 |
|------|--------|--------|-----|---------|
| small | 26M | 1GB | RTX 3090 | 2-4小时 |
| base | 108M | 5GB | RTX 3090 | 8-12小时 |
| moe | 104M | 5GB | RTX 3090 | 10-15小时 |

---

## 20. 常见问题深度解析

### 20.1 为什么模型不收敛？

**问题表现**：loss不下降或震荡

**可能原因及解决方案**：

```python
# 原因1：学习率过高
# 解决：降低学习率
learning_rate = 1e-4  # 从5e-4降低

# 原因2：梯度爆炸
# 解决：启用梯度裁剪
torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)

# 原因3：数据问题
# 解决：检查数据质量
def check_data_quality(data_path):
    with open(data_path) as f:
        for i, line in enumerate(f):
            item = json.loads(line)
            text = item.get('text', '')
            # 检查空文本
            if not text.strip():
                print(f"空文本: 行{i}")
            # 检查异常长度
            if len(text) > 10000:
                print(f"过长文本: 行{i}, 长度{len(text)}")

# 原因4：权重初始化问题
# 解决：使用正确的初始化
def init_weights(module):
    if isinstance(module, nn.Linear):
        torch.nn.init.normal_(module.weight, mean=0.0, std=0.02)
        if module.bias is not None:
            torch.nn.init.zeros_(module.bias)
```

### 20.2 为什么显存不足？

**问题表现**：CUDA out of memory

**解决方案**：

```python
# 方案1：减小batch_size
batch_size = 16  # 从32减小

# 方案2：启用梯度累积
accumulation_steps = 4  # 等效batch_size = 16 * 4 = 64

# 方案3：使用混合精度
scaler = torch.cuda.amp.GradScaler()
with torch.cuda.amp.autocast():
    outputs = model(inputs)
    loss = compute_loss(outputs, labels)
scaler.scale(loss).backward()
scaler.step(optimizer)
scaler.update()

# 方案4：启用Flash Attention
config = LMConfig(flash_attn=True)

# 方案5：减小序列长度
max_seq_len = 256  # 从512减小

# 方案6：使用梯度检查点
from torch.utils.checkpoint import checkpoint

class CheckpointedBlock(nn.Module):
    def forward(self, x):
        return checkpoint(self._forward, x, use_reentrant=False)
```

### 20.3 为什么生成质量差？

**问题表现**：生成内容不连贯、重复、无意义

**解决方案**：

```python
# 方案1：调整采样参数
# 降低temperature使输出更确定
temperature = 0.7  # 从1.0降低

# 使用nucleus sampling
top_p = 0.9

# 方案2：添加重复惩罚
def apply_repetition_penalty(logits, previous_tokens, penalty=1.2):
    """惩罚已生成的token"""
    for token in previous_tokens:
        logits[token] /= penalty
    return logits

# 方案3：增加训练数据质量
# - 使用高质量数据源
# - 清洗数据
# - 去重

# 方案4：增加训练轮数
epochs = 3  # 从1增加

# 方案5：使用更大的模型
config = LMConfig(dim=768, n_layers=12)  # 增大模型
```

---

## 21. 进阶主题

### 21.1 模型量化

```python
"""
模型量化：将float32/float16转为int8/int4

优势：
1. 减少模型大小（4-8倍）
2. 加速推理
3. 降低显存占用

方法：
1. 训练后量化（PTQ）
2. 量化感知训练（QAT）
"""

import torch.quantization as quant

# 动态量化
def dynamic_quantization(model):
    """动态量化：权重量化，激活保持float"""
    quantized_model = torch.quantization.quantize_dynamic(
        model,
        {nn.Linear},
        dtype=torch.qint8
    )
    return quantized_model

# 静态量化
def static_quantization(model, calibration_loader):
    """静态量化：权重和激活都量化"""
    # 准备量化
    model.qconfig = quant.get_default_qconfig('fbgemm')
    quant.prepare(model, inplace=True)
    
    # 校准
    with torch.no_grad():
        for batch in calibration_loader:
            model(batch)
    
    # 转换
    quant.convert(model, inplace=True)
    return model
```

### 21.2 模型蒸馏

```python
"""
知识蒸馏：用大模型（教师）指导小模型（学生）训练

损失函数：
L = α * L_hard + (1-α) * L_soft

其中：
- L_hard: 学生预测与真实标签的交叉熵
- L_soft: 学生与教师softmax输出的KL散度
"""

def distillation_loss(student_logits, teacher_logits, labels, temperature=4.0, alpha=0.5):
    """
    蒸馏损失
    
    参数：
    - student_logits: 学生模型的logits
    - teacher_logits: 教师模型的logits
    - labels: 真实标签
    - temperature: 蒸馏温度
    - alpha: 硬标签权重
    """
    # 软标签损失
    soft_loss = F.kl_div(
        F.log_softmax(student_logits / temperature, dim=-1),
        F.softmax(teacher_logits / temperature, dim=-1),
        reduction='batchmean'
    ) * (temperature ** 2)
    
    # 硬标签损失
    hard_loss = F.cross_entropy(student_logits, labels)
    
    # 组合损失
    return alpha * hard_loss + (1 - alpha) * soft_loss
```

### 21.3 模型剪枝

```python
"""
模型剪枝：移除不重要的权重

类型：
1. 非结构化剪枝：移除单个权重
2. 结构化剪枝：移除整个神经元/层
"""

def magnitude_pruning(model, sparsity=0.3):
    """
    幅度剪枝：移除绝对值最小的权重
    
    参数：
    - model: 模型
    - sparsity: 剪枝比例
    """
    for name, param in model.named_parameters():
        if 'weight' in name:
            # 计算阈值
            threshold = torch.quantile(torch.abs(param.data), sparsity)
            # 创建掩码
            mask = torch.abs(param.data) > threshold
            # 应用剪枝
            param.data *= mask.float()
    
    return model

def iterative_pruning(model, train_loader, target_sparsity=0.5, steps=10):
    """
    迭代剪枝：逐步增加剪枝比例
    
    每次剪枝后微调，保持模型性能
    """
    sparsity_per_step = target_sparsity / steps
    
    for step in range(steps):
        # 剪枝
        current_sparsity = sparsity_per_step * (step + 1)
        model = magnitude_pruning(model, current_sparsity)
        
        # 微调
        train_for_epochs(model, train_loader, epochs=1)
    
    return model
```

---

## 22. 总结与展望

通过这份详尽的教程，你已经全面了解了MiniMind项目的每一个核心组件：

### 22.1 核心技术掌握清单

| 技术领域 | 具体内容 | 掌握程度自评 |
|---------|---------|-------------|
| **模型架构** | Transformer Decoder-Only | □ □ □ □ □ |
| **归一化** | RMSNorm原理与实现 | □ □ □ □ □ |
| **位置编码** | RoPE数学推导与代码 | □ □ □ □ □ |
| **注意力机制** | GQA、Flash Attention | □ □ □ □ □ |
| **前馈网络** | SwiGLU激活函数 | □ □ □ □ □ |
| **混合专家** | MoE路由与负载均衡 | □ □ □ □ □ |
| **训练优化** | 混合精度、梯度累积 | □ □ □ □ □ |
| **微调技术** | LoRA、DPO | □ □ □ □ □ |
| **推理优化** | KV缓存、采样策略 | □ □ □ □ □ |

### 22.2 学习路径建议

```
初级阶段（1-2周）：
├── 理解Transformer架构
├── 阅读MiniMind源码
├── 运行预训练脚本
└── 理解数据处理流程

中级阶段（2-4周）：
├── 修改模型配置
├── 尝试不同超参数
├── 实现LoRA微调
└── 分析训练日志

高级阶段（1-2月）：
├── 实现自定义组件
├── 尝试模型蒸馏
├── 实现模型量化
└── 贡献代码到社区
```

### 22.3 扩展阅读

**必读论文**：
1. "Attention Is All You Need" - Transformer原论文
2. "LLaMA: Open and Efficient Foundation Language Models" - LLaMA架构
3. "RoFormer: Enhanced Transformer with Rotary Position Embedding" - RoPE
4. "FlashAttention: Fast and Memory-Efficient Exact Attention" - Flash Attention
5. "LoRA: Low-Rank Adaptation of Large Language Models" - LoRA
6. "Direct Preference Optimization" - DPO

**推荐项目**：
1. LLaMA - Meta的大语言模型
2. Mistral - 高效开源模型
3. Qwen - 阿里通义千问
4. ChatGLM - 智谱GLM

### 22.4 社区贡献

MiniMind是一个开源项目，欢迎贡献：
- 提交Issue报告bug
- 提交PR修复问题
- 分享训练经验
- 完善文档

---

## 23. FeedForward前馈网络逐行精读

### 23.1 SwiGLU完整实现解析

```python
class FeedForward(nn.Module):
    """
    SwiGLU前馈神经网络
    
    这是现代大语言模型的标准FFN实现，相比传统FFN有显著优势。
    
    架构对比：
    
    传统FFN（如GPT-2）：
        h = ReLU(x @ W1) @ W2
        参数量：2 × dim × hidden_dim
        
    SwiGLU FFN（如LLaMA）：
        h = (Swish(x @ W1) ⊙ (x @ W3)) @ W2
        参数量：3 × dim × hidden_dim
        
    虽然参数量增加50%，但性能提升显著。
    """
    
    def __init__(self, dim: int, hidden_dim: int, multiple_of: int, dropout: float = 0.0):
        """
        初始化FeedForward层
        
        参数详解：
        - dim: 输入/输出维度（模型的隐藏维度）
        - hidden_dim: FFN中间层维度
        - multiple_of: 隐藏维度对齐倍数（通常为64）
        - dropout: dropout比率
        """
        super().__init__()
        
        # 第1步：调整hidden_dim为multiple_of的倍数
        # 为什么需要对齐？
        # - GPU的Tensor Core以64为单位进行矩阵运算
        # - 对齐可以提高计算效率10-20%
        # - 公式：向上取整到multiple_of的倍数
        hidden_dim = multiple_of * ((hidden_dim + multiple_of - 1) // multiple_of)
        
        # 第2步：定义三个投影层
        
        # W1：门控投影（Gate Projection）
        # 用于生成门控信号，决定哪些信息应该通过
        # 输入：dim，输出：hidden_dim
        self.w1 = nn.Linear(dim, hidden_dim, bias=False)
        
        # W2：下投影（Down Projection）
        # 将hidden_dim投影回dim
        # 输入：hidden_dim，输出：dim
        self.w2 = nn.Linear(hidden_dim, dim, bias=False)
        
        # W3：上投影（Up Projection）
        # 与W1配合，生成要被门控的值
        # 输入：dim，输出：hidden_dim
        self.w3 = nn.Linear(dim, hidden_dim, bias=False)
        
        # 为什么不使用bias？
        # 1. 减少参数量
        # 2. 实验表明对性能影响很小
        # 3. 后面有LayerNorm/RMSNorm，bias的作用被抵消
        
        # Dropout层
        self.dropout = nn.Dropout(dropout)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        前向传播
        
        参数：
        - x: 输入张量，形状为 (batch_size, seq_len, dim)
        
        返回：
        - 输出张量，形状与输入相同
        
        计算流程详解：
        
        步骤1：计算门控信号
            gate = SiLU(x @ W1)
            
            SiLU（Sigmoid Linear Unit）也叫Swish：
            SiLU(x) = x × sigmoid(x)
            
            特点：
            - 平滑（处处可微）
            - 非单调（有负值输出）
            - 自门控（输出受输入控制）
            
        步骤2：计算上投影值
            up = x @ W3
            
        步骤3：门控融合
            hidden = gate ⊙ up
            
            逐元素相乘，门控决定哪些信息通过
            
        步骤4：下投影
            output = hidden @ W2
            
        步骤5：Dropout
            output = dropout(output)
        """
        # 完整的SwiGLU计算
        # F.silu() 是 SiLU激活函数
        # 等价于：x * torch.sigmoid(x)
        return self.dropout(self.w2(F.silu(self.w1(x)) * self.w3(x)))
```

### 23.2 激活函数深度对比

```python
"""
激活函数对比分析

1. ReLU（Rectified Linear Unit）
   公式：f(x) = max(0, x)
   
   优点：
   - 计算简单
   - 缓解梯度消失
   
   缺点：
   - 神经元死亡（负值永远为0）
   - 输出不是零中心

2. GELU（Gaussian Error Linear Unit）
   公式：f(x) = x × Φ(x)
   其中 Φ(x) 是标准正态分布的累积分布函数
   
   近似计算：
   f(x) ≈ 0.5 × x × (1 + tanh(√(2/π) × (x + 0.044715 × x³)))
   
   特点：
   - 平滑
   - 在BERT、GPT中使用
   
3. SiLU/Swish（Sigmoid Linear Unit）
   公式：f(x) = x × sigmoid(x)
   
   特点：
   - 平滑
   - 非单调
   - 自门控
   
4. GeGLU和SwiGLU
   GeGLU：GLU + GELU
   SwiGLU：GLU + Swish
   
   实验表明SwiGLU效果最好
"""

import torch
import torch.nn.functional as F
import matplotlib.pyplot as plt
import numpy as np

def visualize_activations():
    """可视化不同激活函数"""
    x = torch.linspace(-5, 5, 1000)
    
    # 计算各种激活函数
    relu = F.relu(x)
    gelu = F.gelu(x)
    silu = F.silu(x)
    
    # 计算梯度
    x_relu = x.clone().requires_grad_(True)
    y_relu = F.relu(x_relu)
    grad_relu = torch.autograd.grad(y_relu.sum(), x_relu)[0]
    
    x_silu = x.clone().requires_grad_(True)
    y_silu = F.silu(x_silu)
    grad_silu = torch.autograd.grad(y_silu.sum(), x_silu)[0]
    
    # 绘图
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    
    # 激活函数对比
    axes[0].plot(x.numpy(), relu.numpy(), label='ReLU', linewidth=2)
    axes[0].plot(x.numpy(), gelu.numpy(), label='GELU', linewidth=2)
    axes[0].plot(x.numpy(), silu.numpy(), label='SiLU/Swish', linewidth=2)
    axes[0].set_title('Activation Functions')
    axes[0].set_xlabel('x')
    axes[0].set_ylabel('f(x)')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    
    # 梯度对比
    axes[1].plot(x.numpy(), grad_relu.numpy(), label='ReLU gradient', linewidth=2)
    axes[1].plot(x.numpy(), grad_silu.numpy(), label='SiLU gradient', linewidth=2)
    axes[1].set_title('Gradients')
    axes[1].set_xlabel('x')
    axes[1].set_ylabel('df/dx')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    
    # 负值区域对比
    neg_mask = x < 0
    axes[2].bar(['ReLU', 'GELU', 'SiLU'], 
                [relu[neg_mask].sum().item(), 
                 gelu[neg_mask].sum().item(), 
                 silu[neg_mask].sum().item()])
    axes[2].set_title('Negative Region Output Sum')
    axes[2].set_ylabel('Sum of f(x) for x < 0')
    
    plt.tight_layout()
    plt.savefig('activation_comparison.png', dpi=150)
    plt.show()

# 运行可视化
visualize_activations()
```

### 23.3 FFN的作用机制

```python
"""
FFN在Transformer中的作用机制

1. 增加非线性
   注意力机制本质上是线性变换：
   Attention(Q, K, V) = softmax(QK^T/√d) × V
   
   FFN引入非线性，增强模型表达能力

2. 特征变换
   每一层的FFN可以学习不同的特征变换
   低层：学习基础特征
   高层：学习抽象特征

3. 增加模型容量
   FFN的hidden_dim通常是dim的4倍
   这显著增加了模型的参数量和表达能力

4. 位置独立处理
   FFN对每个位置独立处理
   与注意力机制形成互补
"""

class StandardFFN(nn.Module):
    """传统FFN实现（用于对比）"""
    def __init__(self, dim, hidden_dim, dropout=0.0):
        super().__init__()
        self.w1 = nn.Linear(dim, hidden_dim)
        self.w2 = nn.Linear(hidden_dim, dim)
        self.dropout = nn.Dropout(dropout)
    
    def forward(self, x):
        # ReLU激活
        return self.dropout(self.w2(F.relu(self.w1(x))))


class GELUFFN(nn.Module):
    """GELU FFN实现（BERT风格）"""
    def __init__(self, dim, hidden_dim, dropout=0.0):
        super().__init__()
        self.w1 = nn.Linear(dim, hidden_dim)
        self.w2 = nn.Linear(hidden_dim, dim)
        self.dropout = nn.Dropout(dropout)
    
    def forward(self, x):
        # GELU激活
        return self.dropout(self.w2(F.gelu(self.w1(x))))


class SwiGLUFFN(nn.Module):
    """SwiGLU FFN实现（LLaMA风格）"""
    def __init__(self, dim, hidden_dim, dropout=0.0):
        super().__init__()
        self.w1 = nn.Linear(dim, hidden_dim, bias=False)
        self.w2 = nn.Linear(hidden_dim, dim, bias=False)
        self.w3 = nn.Linear(dim, hidden_dim, bias=False)
        self.dropout = nn.Dropout(dropout)
    
    def forward(self, x):
        return self.dropout(self.w2(F.silu(self.w1(x)) * self.w3(x)))


def compare_ffn_implementations():
    """对比不同FFN实现"""
    import time
    
    dim = 512
    hidden_dim = 2048
    batch_size = 32
    seq_len = 128
    
    # 创建模型
    standard_ffn = StandardFFN(dim, hidden_dim)
    gelu_ffn = GELUFFN(dim, hidden_dim)
    swiglu_ffn = SwiGLUFFN(dim, hidden_dim)
    
    # 计算参数量
    print(f"Standard FFN 参数量: {sum(p.numel() for p in standard_ffn.parameters()):,}")
    print(f"GELU FFN 参数量: {sum(p.numel() for p in gelu_ffn.parameters()):,}")
    print(f"SwiGLU FFN 参数量: {sum(p.numel() for p in swiglu_ffn.parameters()):,}")
    
    # 测试速度
    x = torch.randn(batch_size, seq_len, dim)
    
    # Standard FFN
    start = time.time()
    for _ in range(100):
        _ = standard_ffn(x)
    print(f"Standard FFN 时间: {time.time() - start:.4f}s")
    
    # GELU FFN
    start = time.time()
    for _ in range(100):
        _ = gelu_ffn(x)
    print(f"GELU FFN 时间: {time.time() - start:.4f}s")
    
    # SwiGLU FFN
    start = time.time()
    for _ in range(100):
        _ = swiglu_ffn(x)
    print(f"SwiGLU FFN 时间: {time.time() - start:.4f}s")
```

---

## 24. MoE混合专家系统完整实现

### 24.1 MoE核心组件详解

```python
"""
MoE（Mixture of Experts）混合专家系统

核心思想：
- 将一个大网络分解为多个小网络（专家）
- 每次只激活部分专家
- 参数量增加，但计算量不变

关键组件：
1. 专家网络：多个独立的FFN
2. 门控网络：决定每个token使用哪些专家
3. 路由机制：将token分配到合适的专家
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Tuple


class Expert(nn.Module):
    """
    单个专家网络
    
    每个专家就是一个独立的FeedForward网络
    """
    def __init__(self, dim: int, hidden_dim: int):
        super().__init__()
        self.w1 = nn.Linear(dim, hidden_dim, bias=False)
        self.w2 = nn.Linear(hidden_dim, dim, bias=False)
        self.w3 = nn.Linear(dim, hidden_dim, bias=False)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """SwiGLU前向传播"""
        return self.w2(F.silu(self.w1(x)) * self.w3(x))


class MoEGate(nn.Module):
    """
    MoE门控网络
    
    负责为每个token选择最合适的专家
    
    关键设计：
    1. Top-K选择：每个token只激活K个专家
    2. 负载均衡：确保所有专家被均匀使用
    3. 辅助损失：鼓励均匀分布
    """
    
    def __init__(
        self,
        dim: int,
        n_experts: int,
        top_k: int,
        aux_loss_alpha: float = 0.1,
        noise_std: float = 0.1
    ):
        """
        参数：
        - dim: 输入维度
        - n_experts: 专家总数
        - top_k: 每个token激活的专家数
        - aux_loss_alpha: 辅助损失权重
        - noise_std: 噪声标准差（用于探索）
        """
        super().__init__()
        
        self.n_experts = n_experts
        self.top_k = top_k
        self.aux_loss_alpha = aux_loss_alpha
        self.noise_std = noise_std
        
        # 门控权重
        # 将输入映射到n_experts维的分数
        self.gate = nn.Linear(dim, n_experts, bias=False)
    
    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        前向传播
        
        参数：
        - x: 输入张量 (batch_size, seq_len, dim)
        
        返回：
        - topk_indices: 选中的专家索引 (batch_size * seq_len, top_k)
        - topk_weights: 专家权重 (batch_size * seq_len, top_k)
        - aux_loss: 辅助损失（用于负载均衡）
        """
        batch_size, seq_len, dim = x.shape
        
        # 展平输入
        x_flat = x.view(-1, dim)  # (batch * seq, dim)
        
        # 计算门控分数
        logits = self.gate(x_flat)  # (batch * seq, n_experts)
        
        # 添加噪声（训练时）
        if self.training and self.noise_std > 0:
            noise = torch.randn_like(logits) * self.noise_std
            logits = logits + noise
        
        # Softmax归一化
        scores = F.softmax(logits, dim=-1)  # (batch * seq, n_experts)
        
        # 选择Top-K专家
        topk_scores, topk_indices = torch.topk(scores, self.top_k, dim=-1)
        
        # 归一化Top-K权重
        # 使权重和为1
        topk_weights = topk_scores / topk_scores.sum(dim=-1, keepdim=True)
        
        # 计算辅助损失
        aux_loss = self._compute_aux_loss(scores, topk_indices)
        
        return topk_indices, topk_weights, aux_loss
    
    def _compute_aux_loss(
        self,
        scores: torch.Tensor,
        topk_indices: torch.Tensor
    ) -> torch.Tensor:
        """
        计算负载均衡辅助损失
        
        目标：鼓励所有专家被均匀使用
        
        公式：
        L_aux = α × n × Σᵢ(fᵢ × Pᵢ)
        
        其中：
        - fᵢ: 专家i被选中的频率
        - Pᵢ: 专家i的平均分数
        - n: 专家数量
        - α: 损失权重
        """
        # 计算每个专家被选中的频率
        # one_hot编码
        expert_mask = F.one_hot(topk_indices, self.n_experts).float()
        # (batch * seq, top_k, n_experts)
        
        # 求和得到每个专家被选中的次数
        expert_counts = expert_mask.sum(dim=(0, 1))  # (n_experts,)
        
        # 归一化：得到频率
        total_tokens = topk_indices.numel()
        expert_freq = expert_counts / total_tokens
        
        # 计算每个专家的平均分数
        expert_scores = scores.mean(dim=0)  # (n_experts,)
        
        # 辅助损失
        # 目标：fᵢ ≈ 1/n 且 Pᵢ ≈ 1/n
        aux_loss = self.aux_loss_alpha * self.n_experts * (expert_freq * expert_scores).sum()
        
        return aux_loss


class MoEFFN(nn.Module):
    """
    MoE前馈神经网络
    
    完整的MoE实现，包括：
    - 多个专家网络
    - 门控网络
    - 路由机制
    - 负载均衡
    """
    
    def __init__(
        self,
        dim: int,
        hidden_dim: int,
        n_experts: int,
        top_k: int,
        shared_experts: int = 0,
        aux_loss_alpha: float = 0.1
    ):
        """
        参数：
        - dim: 输入/输出维度
        - hidden_dim: 专家隐藏维度
        - n_experts: 路由专家总数
        - top_k: 每个token激活的专家数
        - shared_experts: 共享专家数量
        - aux_loss_alpha: 辅助损失权重
        """
        super().__init__()
        
        self.dim = dim
        self.n_experts = n_experts
        self.top_k = top_k
        self.shared_experts = shared_experts
        
        # 创建路由专家
        self.experts = nn.ModuleList([
            Expert(dim, hidden_dim) for _ in range(n_experts)
        ])
        
        # 创建共享专家（可选）
        if shared_experts > 0:
            self.shared_expert_list = nn.ModuleList([
                Expert(dim, hidden_dim) for _ in range(shared_experts)
            ])
        
        # 门控网络
        self.gate = MoEGate(dim, n_experts, top_k, aux_loss_alpha)
        
        # 存储辅助损失
        self.aux_loss = 0.0
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        前向传播
        
        参数：
        - x: 输入张量 (batch_size, seq_len, dim)
        
        返回：
        - 输出张量 (batch_size, seq_len, dim)
        """
        batch_size, seq_len, dim = x.shape
        
        # 门控选择
        topk_indices, topk_weights, aux_loss = self.gate(x)
        self.aux_loss = aux_loss
        
        # 展平输入
        x_flat = x.view(-1, dim)  # (batch * seq, dim)
        
        # 初始化输出
        output = torch.zeros_like(x_flat)
        
        # 处理每个专家
        # 优化：按专家批处理，而不是按token
        for expert_idx in range(self.n_experts):
            # 找到选择了这个专家的token
            # topk_indices: (batch * seq, top_k)
            mask = (topk_indices == expert_idx).any(dim=-1)  # (batch * seq,)
            
            if mask.any():
                # 获取这些token
                expert_input = x_flat[mask]  # (n_tokens, dim)
                
                # 通过专家网络
                expert_output = self.experts[expert_idx](expert_input)  # (n_tokens, dim)
                
                # 获取权重
                # 找到这些token对该专家的权重
                expert_mask = (topk_indices[mask] == expert_idx)
                expert_weight = (topk_weights[mask] * expert_mask.float()).sum(dim=-1, keepdim=True)
                
                # 加权累加
                output[mask] += expert_output * expert_weight
        
        # 处理共享专家
        if self.shared_experts > 0:
            shared_output = torch.zeros_like(x_flat)
            for shared_expert in self.shared_expert_list:
                shared_output += shared_expert(x_flat)
            shared_output = shared_output / self.shared_experts
            output = output + shared_output
        
        # 恢复形状
        output = output.view(batch_size, seq_len, dim)
        
        return output


# ==================== 使用示例 ====================

def demo_moe():
    """MoE使用示例"""
    # 配置
    dim = 512
    hidden_dim = 1408
    n_experts = 8
    top_k = 2
    
    # 创建MoE层
    moe = MoEFFN(dim, hidden_dim, n_experts, top_k, shared_experts=1)
    
    # 创建输入
    batch_size = 4
    seq_len = 128
    x = torch.randn(batch_size, seq_len, dim)
    
    # 前向传播
    output = moe(x)
    
    print(f"输入形状: {x.shape}")
    print(f"输出形状: {output.shape}")
    print(f"辅助损失: {moe.aux_loss.item():.6f}")
    
    # 计算参数量
    total_params = sum(p.numel() for p in moe.parameters())
    print(f"总参数量: {total_params:,}")
    
    # 对比等效的Dense FFN
    dense_ffn = nn.Sequential(
        nn.Linear(dim, hidden_dim),
        nn.ReLU(),
        nn.Linear(hidden_dim, dim)
    )
    dense_params = sum(p.numel() for p in dense_ffn.parameters())
    print(f"Dense FFN参数量: {dense_params:,}")
    print(f"参数量比: {total_params / dense_params:.2f}x")
```

### 24.2 MoE路由策略详解

```python
"""
MoE路由策略详解

1. Top-K路由（最常用）
   - 每个token选择分数最高的K个专家
   - 简单高效
   
2. 专家选择路由（Expert Choice）
   - 让专家选择token，而不是token选择专家
   - 自动实现负载均衡
   
3. Soft路由
   - 使用所有专家的加权平均
   - 计算量大但平滑
   
4. 容量因子路由
   - 限制每个专家处理的token数量
   - 超出容量的token跳过或重新路由
"""

class ExpertChoiceRouter(nn.Module):
    """
    专家选择路由
    
    让专家主动选择要处理的token
    自动实现负载均衡
    """
    
    def __init__(self, dim: int, n_experts: int, capacity_factor: float = 1.25):
        super().__init__()
        self.n_experts = n_experts
        self.capacity_factor = capacity_factor
        self.gate = nn.Linear(dim, n_experts, bias=False)
    
    def forward(self, x: torch.Tensor):
        """
        专家选择路由
        
        参数：
        - x: (batch_size, seq_len, dim)
        
        返回：
        - output: (batch_size, seq_len, dim)
        """
        batch_size, seq_len, dim = x.shape
        n_tokens = batch_size * seq_len
        
        # 计算路由分数
        logits = self.gate(x)  # (batch, seq, n_experts)
        
        # 转置：让专家维度在前
        logits = logits.view(-1, self.n_experts)  # (batch*seq, n_experts)
        logits = logits.transpose(0, 1)  # (n_experts, batch*seq)
        
        # 计算每个专家的容量
        capacity = int(self.capacity_factor * n_tokens / self.n_experts)
        
        # 每个专家选择top-capacity个token
        topk_scores, topk_indices = torch.topk(logits, capacity, dim=-1)
        
        # Softmax归一化
        topk_scores = F.softmax(topk_scores, dim=-1)
        
        return topk_scores, topk_indices, capacity


class SoftRouter(nn.Module):
    """
    Soft路由
    
    使用所有专家的加权平均
    """
    
    def __init__(self, dim: int, n_experts: int):
        super().__init__()
        self.n_experts = n_experts
        self.gate = nn.Linear(dim, n_experts, bias=False)
    
    def forward(self, x: torch.Tensor, experts: nn.ModuleList):
        """
        Soft路由
        
        参数：
        - x: (batch, seq, dim)
        - experts: 专家网络列表
        """
        # 计算路由权重
        weights = F.softmax(self.gate(x), dim=-1)  # (batch, seq, n_experts)
        
        # 计算所有专家的输出
        expert_outputs = []
        for expert in experts:
            expert_outputs.append(expert(x))
        
        # 堆叠
        expert_outputs = torch.stack(expert_outputs, dim=-1)  # (batch, seq, dim, n_experts)
        
        # 加权平均
        output = (expert_outputs * weights.unsqueeze(-2)).sum(dim=-1)
        
        return output


class CapacityFactorRouter(nn.Module):
    """
    容量因子路由
    
    限制每个专家处理的token数量
    """
    
    def __init__(
        self,
        dim: int,
        n_experts: int,
        top_k: int,
        capacity_factor: float = 1.25,
        drop_tokens: bool = False
    ):
        super().__init__()
        self.n_experts = n_experts
        self.top_k = top_k
        self.capacity_factor = capacity_factor
        self.drop_tokens = drop_tokens
        self.gate = nn.Linear(dim, n_experts, bias=False)
    
    def forward(self, x: torch.Tensor):
        """
        容量因子路由
        """
        batch_size, seq_len, dim = x.shape
        n_tokens = batch_size * seq_len
        
        # 计算容量
        capacity = int(self.capacity_factor * n_tokens * self.top_k / self.n_experts)
        
        # 计算路由分数
        logits = self.gate(x)
        scores = F.softmax(logits, dim=-1)
        
        # Top-K选择
        topk_scores, topk_indices = torch.topk(scores, self.top_k, dim=-1)
        
        # 统计每个专家的token数量
        expert_counts = torch.zeros(self.n_experts, dtype=torch.long, device=x.device)
        
        # 检查容量
        # ... 实现容量检查和token丢弃/重路由
        
        return topk_indices, topk_scores / topk_scores.sum(dim=-1, keepdim=True)
```

---

## 25. 完整训练循环详解

### 25.1 训练循环完整实现

```python
"""
完整的训练循环实现

包含所有关键组件：
1. 数据加载
2. 模型前向传播
3. 损失计算
4. 反向传播
5. 梯度裁剪
6. 参数更新
7. 学习率调度
8. 混合精度
9. 梯度累积
10. 检查点保存
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torch.cuda.amp import GradScaler, autocast
import math
import os
from tqdm import tqdm


class Trainer:
    """
    完整的训练器实现
    """
    
    def __init__(
        self,
        model,
        train_loader,
        val_loader,
        config,
        device='cuda'
    ):
        """
        初始化训练器
        
        参数：
        - model: 模型
        - train_loader: 训练数据加载器
        - val_loader: 验证数据加载器
        - config: 训练配置
        - device: 设备
        """
        self.model = model.to(device)
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.config = config
        self.device = device
        
        # 优化器
        self.optimizer = optim.AdamW(
            model.parameters(),
            lr=config.learning_rate,
            betas=(0.9, 0.95),
            weight_decay=config.weight_decay,
            eps=1e-8
        )
        
        # 梯度缩放器（混合精度）
        self.scaler = GradScaler(enabled=config.use_amp)
        
        # 学习率调度器
        self.scheduler = self._create_scheduler()
        
        # 训练状态
        self.global_step = 0
        self.epoch = 0
        self.best_loss = float('inf')
        
        # 创建输出目录
        os.makedirs(config.output_dir, exist_ok=True)
    
    def _create_scheduler(self):
        """创建学习率调度器"""
        total_steps = self.config.epochs * len(self.train_loader)
        warmup_steps = self.config.warmup_steps
        
        def lr_lambda(step):
            if step < warmup_steps:
                # 线性预热
                return step / warmup_steps
            else:
                # 余弦退火
                progress = (step - warmup_steps) / (total_steps - warmup_steps)
                return 0.5 * (1 + math.cos(math.pi * progress))
        
        return optim.lr_scheduler.LambdaLR(self.optimizer, lr_lambda)
    
    def train_epoch(self):
        """训练一个epoch"""
        self.model.train()
        total_loss = 0
        n_batches = 0
        
        # 进度条
        pbar = tqdm(self.train_loader, desc=f'Epoch {self.epoch}')
        
        for batch_idx, batch in enumerate(pbar):
            # 获取数据
            input_ids = batch['input_ids'].to(self.device)
            labels = batch['labels'].to(self.device)
            
            # 前向传播（混合精度）
            with autocast(enabled=self.config.use_amp):
                outputs = self.model(input_ids)
                logits = outputs.logits
                
                # 计算损失
                loss = self._compute_loss(logits, labels)
                
                # 添加MoE辅助损失
                if outputs.aux_loss is not None:
                    loss = loss + outputs.aux_loss
                
                # 梯度累积缩放
                loss = loss / self.config.accumulation_steps
            
            # 反向传播
            self.scaler.scale(loss).backward()
            
            # 梯度累积
            if (batch_idx + 1) % self.config.accumulation_steps == 0:
                # 梯度裁剪
                self.scaler.unscale_(self.optimizer)
                grad_norm = torch.nn.utils.clip_grad_norm_(
                    self.model.parameters(),
                    self.config.max_grad_norm
                )
                
                # 参数更新
                self.scaler.step(self.optimizer)
                self.scaler.update()
                
                # 清零梯度
                self.optimizer.zero_grad(set_to_none=True)
                
                # 更新学习率
                self.scheduler.step()
                
                # 更新全局步数
                self.global_step += 1
            
            # 累计损失
            total_loss += loss.item() * self.config.accumulation_steps
            n_batches += 1
            
            # 更新进度条
            current_lr = self.optimizer.param_groups[0]['lr']
            pbar.set_postfix({
                'loss': f'{loss.item() * self.config.accumulation_steps:.4f}',
                'lr': f'{current_lr:.2e}',
                'grad_norm': f'{grad_norm:.2f}'
            })
            
            # 定期验证
            if self.global_step % self.config.eval_steps == 0:
                val_loss = self.evaluate()
                if val_loss < self.best_loss:
                    self.best_loss = val_loss
                    self.save_checkpoint('best')
            
            # 定期保存
            if self.global_step % self.config.save_steps == 0:
                self.save_checkpoint(f'step_{self.global_step}')
        
        return total_loss / n_batches
    
    def _compute_loss(self, logits, labels):
        """
        计算损失
        
        参数：
        - logits: (batch, seq, vocab_size)
        - labels: (batch, seq)
        """
        # 展平
        logits = logits.view(-1, logits.size(-1))
        labels = labels.view(-1)
        
        # 交叉熵损失
        # ignore_index=-100: 忽略padding token
        loss = F.cross_entropy(logits, labels, ignore_index=-100)
        
        return loss
    
    @torch.no_grad()
    def evaluate(self):
        """验证"""
        self.model.eval()
        total_loss = 0
        n_batches = 0
        
        for batch in self.val_loader:
            input_ids = batch['input_ids'].to(self.device)
            labels = batch['labels'].to(self.device)
            
            with autocast(enabled=self.config.use_amp):
                outputs = self.model(input_ids)
                loss = self._compute_loss(outputs.logits, labels)
            
            total_loss += loss.item()
            n_batches += 1
        
        self.model.train()
        return total_loss / n_batches
    
    def save_checkpoint(self, name):
        """保存检查点"""
        checkpoint = {
            'model': self.model.state_dict(),
            'optimizer': self.optimizer.state_dict(),
            'scheduler': self.scheduler.state_dict(),
            'scaler': self.scaler.state_dict(),
            'global_step': self.global_step,
            'epoch': self.epoch,
            'best_loss': self.best_loss,
            'config': self.config.__dict__
        }
        
        path = os.path.join(self.config.output_dir, f'{name}.pt')
        torch.save(checkpoint, path)
        print(f'Saved checkpoint to {path}')
    
    def load_checkpoint(self, path):
        """加载检查点"""
        checkpoint = torch.load(path, map_location=self.device)
        
        self.model.load_state_dict(checkpoint['model'])
        self.optimizer.load_state_dict(checkpoint['optimizer'])
        self.scheduler.load_state_dict(checkpoint['scheduler'])
        self.scaler.load_state_dict(checkpoint['scaler'])
        self.global_step = checkpoint['global_step']
        self.epoch = checkpoint['epoch']
        self.best_loss = checkpoint['best_loss']
        
        print(f'Loaded checkpoint from {path}')
    
    def train(self):
        """完整训练流程"""
        print(f'Starting training for {self.config.epochs} epochs')
        print(f'Total steps: {self.config.epochs * len(self.train_loader)}')
        
        for epoch in range(self.config.epochs):
            self.epoch = epoch
            train_loss = self.train_epoch()
            val_loss = self.evaluate()
            
            print(f'\nEpoch {epoch}: train_loss={train_loss:.4f}, val_loss={val_loss:.4f}')
            
            # 每个epoch结束保存
            self.save_checkpoint(f'epoch_{epoch}')
        
        print('Training completed!')


# ==================== 训练配置 ====================

from dataclasses import dataclass

@dataclass
class TrainingConfig:
    # 模型配置
    dim: int = 512
    n_layers: int = 8
    n_heads: int = 8
    
    # 训练配置
    epochs: int = 1
    batch_size: int = 32
    learning_rate: float = 5e-4
    weight_decay: float = 0.1
    warmup_steps: int = 100
    max_grad_norm: float = 1.0
    accumulation_steps: int = 8
    
    # 混合精度
    use_amp: bool = True
    
    # 保存和评估
    output_dir: str = 'outputs'
    save_steps: int = 500
    eval_steps: int = 100
    
    # 数据
    max_seq_len: int = 512
    vocab_size: int = 6400


# ==================== 使用示例 ====================

def main():
    """主训练函数"""
    # 配置
    config = TrainingConfig()
    
    # 创建模型
    from model.model import MiniMindLM
    from model.LMConfig import LMConfig
    
    lm_config = LMConfig(
        dim=config.dim,
        n_layers=config.n_layers,
        n_heads=config.n_heads,
        vocab_size=config.vocab_size,
        max_seq_len=config.max_seq_len
    )
    model = MiniMindLM(lm_config)
    
    # 创建数据加载器（示例）
    # train_loader = DataLoader(...)
    # val_loader = DataLoader(...)
    
    # 创建训练器
    # trainer = Trainer(model, train_loader, val_loader, config)
    
    # 开始训练
    # trainer.train()


if __name__ == '__main__':
    main()
```

---

## 26. 模型推理完整实现

### 26.1 文本生成详解

```python
"""
文本生成完整实现

包含多种生成策略：
1. Greedy Search
2. Beam Search
3. Top-K Sampling
4. Top-P (Nucleus) Sampling
5. Temperature Sampling
6. 组合策略
"""

import torch
import torch.nn.functional as F
from typing import Optional, List, Callable


class TextGenerator:
    """
    文本生成器
    
    支持多种生成策略
    """
    
    def __init__(
        self,
        model,
        tokenizer,
        device='cuda',
        max_length: int = 512
    ):
        """
        初始化生成器
        
        参数：
        - model: 语言模型
        - tokenizer: 分词器
        - device: 设备
        - max_length: 最大生成长度
        """
        self.model = model.to(device)
        self.model.eval()
        self.tokenizer = tokenizer
        self.device = device
        self.max_length = max_length
    
    @torch.no_grad()
    def generate(
        self,
        prompt: str,
        max_new_tokens: int = 100,
        temperature: float = 1.0,
        top_k: int = 50,
        top_p: float = 0.9,
        repetition_penalty: float = 1.0,
        do_sample: bool = True,
        use_cache: bool = True
    ) -> str:
        """
        生成文本
        
        参数：
        - prompt: 输入提示
        - max_new_tokens: 最大生成token数
        - temperature: 温度参数
        - top_k: Top-K采样参数
        - top_p: Top-P采样参数
        - repetition_penalty: 重复惩罚
        - do_sample: 是否采样（False则使用贪心）
        - use_cache: 是否使用KV缓存
        
        返回：
        - 生成的文本
        """
        # 编码输入
        input_ids = self.tokenizer.encode(prompt, return_tensors='pt').to(self.device)
        
        # 生成
        output_ids = self._generate_tokens(
            input_ids,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_k=top_k,
            top_p=top_p,
            repetition_penalty=repetition_penalty,
            do_sample=do_sample,
            use_cache=use_cache
        )
        
        # 解码
        output_text = self.tokenizer.decode(output_ids[0], skip_special_tokens=True)
        
        return output_text
    
    def _generate_tokens(
        self,
        input_ids: torch.Tensor,
        max_new_tokens: int,
        temperature: float,
        top_k: int,
        top_p: float,
        repetition_penalty: float,
        do_sample: bool,
        use_cache: bool
    ) -> torch.Tensor:
        """
        Token级别的生成
        """
        # KV缓存
        past_key_values = None
        
        # 已生成的token（用于重复惩罚）
        generated_tokens = input_ids.clone()
        
        for _ in range(max_new_tokens):
            # 前向传播
            if use_cache and past_key_values is not None:
                # 只输入新token
                model_input = input_ids[:, -1:]
            else:
                model_input = input_ids
            
            outputs = self.model(
                model_input,
                past_key_values=past_key_values,
                use_cache=use_cache
            )
            
            # 更新KV缓存
            past_key_values = outputs.past_key_values
            
            # 获取最后一个位置的logits
            logits = outputs.logits[:, -1, :]
            
            # 应用重复惩罚
            if repetition_penalty != 1.0:
                logits = self._apply_repetition_penalty(
                    logits,
                    generated_tokens,
                    repetition_penalty
                )
            
            # 应用温度
            if temperature != 1.0:
                logits = logits / temperature
            
            # 采样或贪心
            if do_sample:
                # Top-K
                if top_k > 0:
                    logits = self._top_k_filter(logits, top_k)
                
                # Top-P
                if top_p < 1.0:
                    logits = self._top_p_filter(logits, top_p)
                
                # 采样
                probs = F.softmax(logits, dim=-1)
                next_token = torch.multinomial(probs, num_samples=1)
            else:
                # 贪心
                next_token = logits.argmax(dim=-1, keepdim=True)
            
            # 拼接
            input_ids = torch.cat([input_ids, next_token], dim=-1)
            generated_tokens = torch.cat([generated_tokens, next_token], dim=-1)
            
            # 检查是否生成了EOS
            if next_token.item() == self.tokenizer.eos_token_id:
                break
        
        return input_ids
    
    def _apply_repetition_penalty(
        self,
        logits: torch.Tensor,
        generated_tokens: torch.Tensor,
        penalty: float
    ) -> torch.Tensor:
        """
        应用重复惩罚
        
        降低已生成token的概率
        """
        # 统计每个token的出现次数
        unique_tokens, counts = torch.unique(generated_tokens, return_counts=True)
        
        # 应用惩罚
        for token, count in zip(unique_tokens, counts):
            if count > 0:
                logits[0, token] = logits[0, token] / (penalty ** count)
        
        return logits
    
    def _top_k_filter(self, logits: torch.Tensor, top_k: int) -> torch.Tensor:
        """
        Top-K过滤
        
        只保留概率最高的K个token
        """
        # 获取第K大的值
        top_k = min(top_k, logits.size(-1))
        values, _ = torch.topk(logits, top_k)
        min_value = values[:, -1].unsqueeze(-1)
        
        # 将其他token的logits设为负无穷
        return torch.where(
            logits < min_value,
            torch.full_like(logits, float('-inf')),
            logits
        )
    
    def _top_p_filter(self, logits: torch.Tensor, top_p: float) -> torch.Tensor:
        """
        Top-P (Nucleus) 过滤
        
        保留累积概率达到P的最小token集合
        """
        # 排序
        sorted_logits, sorted_indices = torch.sort(logits, descending=True)
        
        # 计算累积概率
        probs = F.softmax(sorted_logits, dim=-1)
        cumulative_probs = torch.cumsum(probs, dim=-1)
        
        # 找到需要移除的token
        sorted_indices_to_remove = cumulative_probs > top_p
        
        # 保留第一个超过阈值的token
        sorted_indices_to_remove[..., 1:] = sorted_indices_to_remove[..., :-1].clone()
        sorted_indices_to_remove[..., 0] = False
        
        # 散布回原始索引
        indices_to_remove = sorted_indices_to_remove.scatter(
            1,
            sorted_indices,
            sorted_indices_to_remove
        )
        
        # 设置为负无穷
        return logits.masked_fill(indices_to_remove, float('-inf'))
    
    def beam_search(
        self,
        prompt: str,
        num_beams: int = 4,
        max_new_tokens: int = 100,
        length_penalty: float = 1.0
    ) -> List[str]:
        """
        Beam Search生成
        
        参数：
        - prompt: 输入提示
        - num_beams: beam数量
        - max_new_tokens: 最大生成token数
        - length_penalty: 长度惩罚
        
        返回：
        - 生成的文本列表（按分数排序）
        """
        # 编码输入
        input_ids = self.tokenizer.encode(prompt, return_tensors='pt').to(self.device)
        
        # 扩展为num_beams个beam
        beam_scores = torch.zeros(num_beams, device=self.device)
        beam_tokens = input_ids.repeat(num_beams, 1)
        beam_done = torch.zeros(num_beams, dtype=torch.bool, device=self.device)
        
        for _ in range(max_new_tokens):
            if beam_done.all():
                break
            
            # 前向传播
            outputs = self.model(beam_tokens)
            logits = outputs.logits[:, -1, :]
            
            # 计算log概率
            log_probs = F.log_softmax(logits, dim=-1)
            
            # 累加beam分数
            next_scores = log_probs + beam_scores.unsqueeze(-1)
            
            # 展平
            vocab_size = logits.size(-1)
            next_scores = next_scores.view(-1)
            
            # 选择top-2*num_beams个候选
            top_scores, top_indices = torch.topk(next_scores, 2 * num_beams)
            
            # 转换为beam索引和token索引
            beam_indices = top_indices // vocab_size
            token_indices = top_indices % vocab_size
            
            # 更新beam
            new_beam_tokens = []
            new_beam_scores = []
            new_beam_done = []
            
            for i in range(num_beams):
                beam_idx = beam_indices[i].item()
                token_idx = token_indices[i].item()
                score = top_scores[i].item()
                
                new_token = beam_tokens[beam_idx].clone()
                new_token = torch.cat([new_token, torch.tensor([token_idx], device=self.device)])
                
                new_beam_tokens.append(new_token)
                new_beam_scores.append(score)
                
                # 检查是否结束
                is_done = (token_idx == self.tokenizer.eos_token_id)
                new_beam_done.append(is_done)
            
            beam_tokens = torch.stack(new_beam_tokens)
            beam_scores = torch.tensor(new_beam_scores, device=self.device)
            beam_done = torch.tensor(new_beam_done, device=self.device)
        
        # 应用长度惩罚
        lengths = torch.tensor([len(t) for t in beam_tokens], device=self.device)
        final_scores = beam_scores / (lengths ** length_penalty)
        
        # 排序
        sorted_indices = torch.argsort(final_scores, descending=True)
        
        # 解码
        results = []
        for idx in sorted_indices:
            text = self.tokenizer.decode(beam_tokens[idx], skip_special_tokens=True)
            results.append(text)
        
        return results


# ==================== 使用示例 ====================

def demo_generation():
    """生成示例"""
    # 加载模型和分词器
    # model = ...
    # tokenizer = ...
    
    # 创建生成器
    # generator = TextGenerator(model, tokenizer)
    
    # 贪心生成
    # output = generator.generate("你好", do_sample=False)
    
    # Top-K采样
    # output = generator.generate("你好", top_k=50, temperature=0.8)
    
    # Top-P采样
    # output = generator.generate("你好", top_p=0.9, temperature=0.7)
    
    # Beam Search
    # outputs = generator.beam_search("你好", num_beams=4)
    
    pass
```

---

## 27. Flash Attention完整实现解析

### 27.1 Flash Attention核心原理

```python
"""
Flash Attention：高效注意力计算的革命性优化

传统注意力计算的问题：
1. 显存占用大：O(N²)的中间结果存储
2. 访存效率低：频繁的HBM（高带宽内存）读写
3. 计算效率低：无法充分利用GPU并行能力

Flash Attention的解决方案：
1. 分块计算（Tiling）：将大矩阵分成小块
2. 重计算策略：用计算换存储
3. 内存高效：只存储必要的中间结果

核心思想：
- 将Q、K、V分成小块
- 每块在SRAM（片上内存）中计算
- 避免频繁的HBM访问
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import math

class FlashAttentionV1(nn.Module):
    """
    Flash Attention V1 简化实现
    
    展示分块注意力的核心思想
    """
    
    def __init__(
        self,
        dim: int,
        n_heads: int,
        block_size: int = 64,
        dropout: float = 0.0
    ):
        """
        参数：
        - dim: 输入维度
        - n_heads: 注意力头数
        - block_size: 分块大小
        - dropout: dropout比率
        """
        super().__init__()
        
        self.dim = dim
        self.n_heads = n_heads
        self.head_dim = dim // n_heads
        self.block_size = block_size
        self.scale = self.head_dim ** -0.5
        
        # 投影层
        self.q_proj = nn.Linear(dim, dim, bias=False)
        self.k_proj = nn.Linear(dim, dim, bias=False)
        self.v_proj = nn.Linear(dim, dim, bias=False)
        self.o_proj = nn.Linear(dim, dim, bias=False)
        
        self.dropout = nn.Dropout(dropout)
    
    def forward(self, x: torch.Tensor, mask: torch.Tensor = None):
        """
        前向传播
        
        参数：
        - x: (batch, seq_len, dim)
        - mask: 可选的注意力掩码
        
        返回：
        - output: (batch, seq_len, dim)
        """
        batch_size, seq_len, dim = x.shape
        
        # 投影并重塑
        q = self.q_proj(x).view(batch_size, seq_len, self.n_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(x).view(batch_size, seq_len, self.n_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(x).view(batch_size, seq_len, self.n_heads, self.head_dim).transpose(1, 2)
        
        # 使用分块计算
        output = self._flash_attention(q, k, v, mask)
        
        # 输出投影
        output = output.transpose(1, 2).contiguous().view(batch_size, seq_len, dim)
        output = self.o_proj(output)
        
        return output
    
    def _flash_attention(self, q, k, v, mask):
        """
        分块注意力计算
        
        这是Flash Attention的核心实现
        """
        batch_size, n_heads, seq_len, head_dim = q.shape
        
        # 计算分块数量
        n_blocks = (seq_len + self.block_size - 1) // self.block_size
        
        # 初始化输出
        output = torch.zeros_like(q)
        
        # 对每个Q块
        for i in range(n_blocks):
            q_start = i * self.block_size
            q_end = min((i + 1) * self.block_size, seq_len)
            q_block = q[:, :, q_start:q_end, :]  # (batch, heads, block, head_dim)
            
            # 初始化累加器
            # O: 输出累加
            # L: log-sum-exp累加
            # M: 最大值累加
            O_block = torch.zeros_like(q_block)
            L_block = torch.zeros(batch_size, n_heads, q_end - q_start, device=q.device)
            M_block = torch.full(
                (batch_size, n_heads, q_end - q_start), 
                float('-inf'), 
                device=q.device
            )
            
            # 对每个K、V块
            for j in range(n_blocks):
                k_start = j * self.block_size
                k_end = min((j + 1) * self.block_size, seq_len)
                k_block = k[:, :, k_start:k_end, :]
                v_block = v[:, :, k_start:k_end, :]
                
                # 计算当前块的注意力分数
                # (batch, heads, q_block, k_block)
                scores = torch.matmul(q_block, k_block.transpose(-2, -1)) * self.scale
                
                # 应用掩码（如果有）
                if mask is not None:
                    # 创建块掩码
                    block_mask = mask[:, q_start:q_end, k_start:k_end]
                    scores = scores.masked_fill(block_mask == 0, float('-inf'))
                
                # 在线Softmax更新
                # 这是Flash Attention的关键创新
                M_new = torch.maximum(M_block, scores.max(dim=-1).values)
                
                # 计算归一化因子
                exp_scores = torch.exp(scores - M_new.unsqueeze(-1))
                L_new = L_block * torch.exp(M_block - M_new) + exp_scores.sum(dim=-1)
                
                # 更新输出
                O_block = O_block * (L_block / L_new).unsqueeze(-1) * torch.exp(M_block - M_new).unsqueeze(-1)
                O_block = O_block + exp_scores / L_new.unsqueeze(-1) * v_block
                
                # 更新状态
                M_block = M_new
                L_block = L_new
            
            # 存储结果
            output[:, :, q_start:q_end, :] = O_block
        
        return output


class FlashAttentionV2(nn.Module):
    """
    Flash Attention V2 优化版本
    
    相比V1的改进：
    1. 更好的并行性
    2. 更少的非矩阵乘法操作
    3. 更好的内存访问模式
    """
    
    def __init__(
        self,
        dim: int,
        n_heads: int,
        dropout: float = 0.0
    ):
        super().__init__()
        
        self.dim = dim
        self.n_heads = n_heads
        self.head_dim = dim // n_heads
        self.scale = self.head_dim ** -0.5
        
        self.q_proj = nn.Linear(dim, dim, bias=False)
        self.k_proj = nn.Linear(dim, dim, bias=False)
        self.v_proj = nn.Linear(dim, dim, bias=False)
        self.o_proj = nn.Linear(dim, dim, bias=False)
        
        self.dropout = nn.Dropout(dropout)
    
    def forward(self, x, mask=None, is_causal=False):
        """
        前向传播
        
        参数：
        - x: (batch, seq_len, dim)
        - mask: 可选掩码
        - is_causal: 是否使用因果掩码
        """
        batch_size, seq_len, _ = x.shape
        
        q = self.q_proj(x).view(batch_size, seq_len, self.n_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(x).view(batch_size, seq_len, self.n_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(x).view(batch_size, seq_len, self.n_heads, self.head_dim).transpose(1, 2)
        
        # 使用PyTorch内置的scaled_dot_product_attention
        # 在PyTorch 2.0+中，这会自动使用Flash Attention
        output = F.scaled_dot_product_attention(
            q, k, v,
            attn_mask=mask,
            dropout_p=self.dropout.p if self.training else 0.0,
            is_causal=is_causal,
            scale=self.scale
        )
        
        output = output.transpose(1, 2).contiguous().view(batch_size, seq_len, self.dim)
        return self.o_proj(output)


def compare_attention_implementations():
    """对比不同注意力实现的性能"""
    import time
    
    batch_size = 4
    seq_len = 1024
    dim = 512
    n_heads = 8
    
    x = torch.randn(batch_size, seq_len, dim).cuda()
    
    # 标准注意力
    class StandardAttention(nn.Module):
        def __init__(self, dim, n_heads):
            super().__init__()
            self.n_heads = n_heads
            self.head_dim = dim // n_heads
            self.scale = self.head_dim ** -0.5
            self.q_proj = nn.Linear(dim, dim, bias=False)
            self.k_proj = nn.Linear(dim, dim, bias=False)
            self.v_proj = nn.Linear(dim, dim, bias=False)
            self.o_proj = nn.Linear(dim, dim, bias=False)
        
        def forward(self, x):
            B, S, D = x.shape
            q = self.q_proj(x).view(B, S, self.n_heads, self.head_dim).transpose(1, 2)
            k = self.k_proj(x).view(B, S, self.n_heads, self.head_dim).transpose(1, 2)
            v = self.v_proj(x).view(B, S, self.n_heads, self.head_dim).transpose(1, 2)
            
            attn = torch.matmul(q, k.transpose(-2, -1)) * self.scale
            attn = F.softmax(attn, dim=-1)
            out = torch.matmul(attn, v)
            
            out = out.transpose(1, 2).contiguous().view(B, S, D)
            return self.o_proj(out)
    
    standard_attn = StandardAttention(dim, n_heads).cuda()
    flash_attn = FlashAttentionV2(dim, n_heads).cuda()
    
    # 预热
    for _ in range(10):
        _ = standard_attn(x)
        _ = flash_attn(x)
    
    torch.cuda.synchronize()
    
    # 测试标准注意力
    torch.cuda.reset_peak_memory_stats()
    start = time.time()
    for _ in range(100):
        _ = standard_attn(x)
    torch.cuda.synchronize()
    standard_time = time.time() - start
    standard_memory = torch.cuda.max_memory_allocated() / 1024**2
    
    # 测试Flash Attention
    torch.cuda.reset_peak_memory_stats()
    start = time.time()
    for _ in range(100):
        _ = flash_attn(x)
    torch.cuda.synchronize()
    flash_time = time.time() - start
    flash_memory = torch.cuda.max_memory_allocated() / 1024**2
    
    print(f"标准注意力: {standard_time:.4f}s, 显存: {standard_memory:.2f}MB")
    print(f"Flash Attention: {flash_time:.4f}s, 显存: {flash_memory:.2f}MB")
    print(f"加速比: {standard_time/flash_time:.2f}x")
    print(f"显存节省: {(1 - flash_memory/standard_memory)*100:.1f}%")
```

### 27.2 Flash Attention数学推导

```python
"""
Flash Attention的数学基础

标准注意力计算：
Attention(Q, K, V) = softmax(QK^T / √d) × V

展开计算步骤：
1. S = QK^T / √d           # (N, N) 分数矩阵
2. P = softmax(S)          # (N, N) 概率矩阵
3. O = PV                   # (N, d) 输出矩阵

问题：需要存储N×N的中间矩阵

Flash Attention的关键洞察：

对于分块计算，设Q分为Q₁, Q₂, ..., Q_T
对于第i个Q块Qᵢ：

Oᵢ = softmax(QᵢK^T / √d) × V

使用在线Softmax算法：
设mᵢ = max(QᵢK^T / √d)  # 最大值
设lᵢ = Σ exp(QᵢK^T / √d - mᵢ)  # 归一化因子

对于两个K、V块K₁, V₁和K₂, V₂：

S₁ = QᵢK₁^T / √d
S₂ = QᵢK₂^T / √d

m = max(m₁, m₂)  # 全局最大值

l = exp(m₁ - m) × l₁ + exp(m₂ - m) × l₂  # 合并归一化因子

O = exp(m₁ - m) × (O₁ × l₁) / l + exp(m₂ - m) × (O₂ × l₂) / l

这就是Flash Attention的核心公式！
"""

def online_softmax_demo():
    """
    在线Softmax演示
    
    展示如何增量计算Softmax
    """
    import torch
    
    # 假设有一个向量，我们分两块计算
    x = torch.tensor([1.0, 2.0, 3.0, 4.0])
    
    # 方法1：直接计算
    softmax_direct = torch.softmax(x, dim=0)
    print(f"直接Softmax: {softmax_direct}")
    
    # 方法2：分块计算（在线Softmax）
    x1 = x[:2]  # 第一块
    x2 = x[2:]  # 第二块
    
    # 第一块的局部结果
    m1 = x1.max()
    l1 = torch.exp(x1 - m1).sum()
    o1 = torch.exp(x1 - m1) / l1
    
    print(f"块1: m1={m1}, l1={l1}, o1={o1}")
    
    # 第二块的局部结果
    m2 = x2.max()
    l2 = torch.exp(x2 - m2).sum()
    o2 = torch.exp(x2 - m2) / l2
    
    print(f"块2: m2={m2}, l2={l2}, o2={o2}")
    
    # 合并
    m = max(m1, m2)
    l = torch.exp(m1 - m) * l1 + torch.exp(m2 - m) * l2
    
    # 最终结果
    result1 = torch.exp(x1 - m) * l1 / l
    result2 = torch.exp(x2 - m) * l2 / l
    softmax_online = torch.cat([result1, result2])
    
    print(f"在线Softmax: {softmax_online}")
    print(f"结果一致: {torch.allclose(softmax_direct, softmax_online)}")


# 运行演示
online_softmax_demo()
```

---

## 28. RoPE旋转位置编码深度解析

### 28.1 RoPE数学推导

```python
"""
RoPE (Rotary Position Embedding) 旋转位置编码

核心思想：
将位置信息编码为旋转矩阵，通过旋转向量来注入位置信息

数学推导：

1. 复数表示
   对于二维向量 (x₁, x₂)，可以表示为复数 z = x₁ + i·x₂
   
2. 旋转操作
   旋转θ角度：z' = z · e^(iθ) = z · (cos θ + i·sin θ)
   
   展开为矩阵形式：
   |x₁'|   |cos θ  -sin θ| |x₁|
   |x₂'| = |sin θ   cos θ| |x₂|
   
3. 位置编码
   对于位置m，旋转角度 θ_m = m·θ
   其中θ是基础频率

4. 多维扩展
   对于d维向量，分成d/2组，每组使用不同的频率：
   
   θ_i = 10000^(-2i/d)  for i = 0, 1, ..., d/2-1
   
   旋转角度：θ_m,i = m · θ_i

RoPE的优势：
1. 相对位置感知：两个token之间的相对位置通过旋转角度差体现
2. 长度外推：可以处理比训练时更长的序列
3. 无需学习参数：位置编码是确定性的
"""

import torch
import torch.nn as nn
import math

class RoPE(nn.Module):
    """
    RoPE旋转位置编码完整实现
    """
    
    def __init__(self, dim: int, max_seq_len: int = 2048, base: float = 10000.0):
        """
        参数：
        - dim: 嵌入维度（必须是偶数）
        - max_seq_len: 最大序列长度
        - base: 频率基数（默认10000）
        """
        super().__init__()
        
        assert dim % 2 == 0, "dim必须是偶数"
        
        self.dim = dim
        self.max_seq_len = max_seq_len
        self.base = base
        
        # 计算频率
        # θ_i = 10000^(-2i/d)
        inv_freq = 1.0 / (base ** (torch.arange(0, dim, 2).float() / dim))
        self.register_buffer('inv_freq', inv_freq)
        
        # 预计算cos和sin缓存
        self._build_cache(max_seq_len)
    
    def _build_cache(self, seq_len: int):
        """
        预计算位置编码缓存
        
        这样可以避免每次前向传播时重复计算
        """
        # 位置索引
        t = torch.arange(seq_len, device=self.inv_freq.device, dtype=self.inv_freq.dtype)
        
        # 计算角度：m · θ_i
        # 形状：(seq_len, dim/2)
        freqs = torch.outer(t, self.inv_freq)
        
        # 复制一份用于cos和sin
        # 形状：(seq_len, dim)
        emb = torch.cat([freqs, freqs], dim=-1)
        
        # 缓存cos和sin
        self.register_buffer('cos_cached', emb.cos())
        self.register_buffer('sin_cached', emb.sin())
    
    def forward(self, x: torch.Tensor, seq_len: int = None):
        """
        应用旋转位置编码
        
        参数：
        - x: (batch, n_heads, seq_len, head_dim)
        - seq_len: 序列长度（可选，默认从x推断）
        
        返回：
        - 应用RoPE后的张量
        """
        if seq_len is None:
            seq_len = x.shape[2]
        
        # 确保缓存足够大
        if seq_len > self.cos_cached.shape[0]:
            self._build_cache(seq_len)
        
        # 获取对应位置的cos和sin
        cos = self.cos_cached[:seq_len].unsqueeze(0).unsqueeze(0)  # (1, 1, seq_len, dim)
        sin = self.sin_cached[:seq_len].unsqueeze(0).unsqueeze(0)
        
        # 应用旋转
        return self._apply_rotary_emb(x, cos, sin)
    
    def _apply_rotary_emb(self, x, cos, sin):
        """
        应用旋转嵌入
        
        这是RoPE的核心操作
        """
        # 将x分成两半
        # x = [x1, x2] -> rotate([x1, x2])
        x1 = x[..., :x.shape[-1]//2]
        x2 = x[..., x.shape[-1]//2:]
        
        # 旋转公式：
        # [x1', x2'] = [x1*cos - x2*sin, x1*sin + x2*cos]
        rotated = torch.cat([
            x1 * cos[..., :x.shape[-1]//2] - x2 * sin[..., :x.shape[-1]//2],
            x1 * sin[..., :x.shape[-1]//2] + x2 * cos[..., :x.shape[-1]//2]
        ], dim=-1)
        
        return rotated


def rotate_half(x: torch.Tensor) -> torch.Tensor:
    """
    将张量的一半旋转
    
    这是RoPE中常用的辅助函数
    
    输入: (..., dim)
    输出: (..., dim)
    
    操作：
    [x1, x2, x3, x4, ...] -> [-x2, x1, -x4, x3, ...]
    """
    x1 = x[..., :x.shape[-1]//2]
    x2 = x[..., x.shape[-1]//2:]
    return torch.cat([-x2, x1], dim=-1)


def apply_rotary_pos_emb(q, k, cos, sin):
    """
    对Q和K应用旋转位置编码
    
    参数：
    - q: (batch, n_heads, seq_len, head_dim)
    - k: (batch, n_heads, seq_len, head_dim)
    - cos: (seq_len, head_dim)
    - sin: (seq_len, head_dim)
    
    返回：
    - q_embed, k_embed
    """
    # 调整cos和sin的形状
    cos = cos.unsqueeze(0).unsqueeze(0)  # (1, 1, seq_len, head_dim)
    sin = sin.unsqueeze(0).unsqueeze(0)
    
    # 应用旋转
    q_embed = (q * cos) + (rotate_half(q) * sin)
    k_embed = (k * cos) + (rotate_half(k) * sin)
    
    return q_embed, k_embed


class RoPEAttention(nn.Module):
    """
    使用RoPE的注意力层
    """
    
    def __init__(self, dim: int, n_heads: int, max_seq_len: int = 2048):
        super().__init__()
        
        self.dim = dim
        self.n_heads = n_heads
        self.head_dim = dim // n_heads
        self.scale = self.head_dim ** -0.5
        
        # 投影层
        self.q_proj = nn.Linear(dim, dim, bias=False)
        self.k_proj = nn.Linear(dim, dim, bias=False)
        self.v_proj = nn.Linear(dim, dim, bias=False)
        self.o_proj = nn.Linear(dim, dim, bias=False)
        
        # RoPE
        self.rope = RoPE(self.head_dim, max_seq_len)
    
    def forward(self, x: torch.Tensor, mask: torch.Tensor = None):
        """
        前向传播
        
        参数：
        - x: (batch, seq_len, dim)
        - mask: 可选的注意力掩码
        """
        batch_size, seq_len, _ = x.shape
        
        # 投影
        q = self.q_proj(x).view(batch_size, seq_len, self.n_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(x).view(batch_size, seq_len, self.n_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(x).view(batch_size, seq_len, self.n_heads, self.head_dim).transpose(1, 2)
        
        # 应用RoPE
        cos = self.rope.cos_cached[:seq_len]
        sin = self.rope.sin_cached[:seq_len]
        q, k = apply_rotary_pos_emb(q, k, cos, sin)
        
        # 计算注意力
        scores = torch.matmul(q, k.transpose(-2, -1)) * self.scale
        
        if mask is not None:
            scores = scores.masked_fill(mask == 0, float('-inf'))
        
        attn = F.softmax(scores, dim=-1)
        output = torch.matmul(attn, v)
        
        # 输出投影
        output = output.transpose(1, 2).contiguous().view(batch_size, seq_len, self.dim)
        return self.o_proj(output)
```

### 28.2 RoPE可视化与验证

```python
"""
RoPE可视化与验证
"""

import matplotlib.pyplot as plt
import numpy as np

def visualize_rope():
    """可视化RoPE的效果"""
    
    # 设置参数
    dim = 64
    max_seq_len = 128
    
    # 创建RoPE
    rope = RoPE(dim, max_seq_len)
    
    # 创建两个相同的向量
    x = torch.randn(1, 1, 1, dim)
    
    # 应用不同位置的RoPE
    positions = range(0, max_seq_len, 8)
    similarities = []
    
    for pos in positions:
        # 获取cos和sin
        cos = rope.cos_cached[pos:pos+1]
        sin = rope.sin_cached[pos:pos+1]
        
        # 应用旋转
        x_rotated = (x * cos) + (rotate_half(x) * sin)
        
        # 计算与原始向量的余弦相似度
        sim = F.cosine_similarity(x, x_rotated, dim=-1).item()
        similarities.append(sim)
    
    # 绘图
    plt.figure(figsize=(10, 5))
    plt.plot(positions, similarities, 'b-', linewidth=2)
    plt.xlabel('Position')
    plt.ylabel('Cosine Similarity with Original')
    plt.title('RoPE: Position Effect on Vector')
    plt.grid(True, alpha=0.3)
    plt.savefig('rope_visualization.png', dpi=150)
    plt.show()


def verify_relative_position():
    """
    验证RoPE的相对位置特性
    
    RoPE的关键特性：两个token之间的注意力分数只取决于它们的相对位置
    """
    
    dim = 64
    rope = RoPE(dim)
    
    # 创建两个向量
    q = torch.randn(1, 1, 1, dim)
    k = torch.randn(1, 1, 1, dim)
    
    # 测试不同位置组合
    print("验证相对位置特性：")
    print("位置(m, n) -> 注意力分数")
    print("-" * 40)
    
    for m in range(0, 20, 5):
        for n in range(0, 20, 5):
            # 应用RoPE
            cos_m = rope.cos_cached[m:m+1]
            sin_m = rope.sin_cached[m:m+1]
            cos_n = rope.cos_cached[n:n+1]
            sin_n = rope.sin_cached[n:n+1]
            
            q_rot = (q * cos_m) + (rotate_half(q) * sin_m)
            k_rot = (k * cos_n) + (rotate_half(k) * sin_n)
            
            # 计算注意力分数
            score = torch.matmul(q_rot, k_rot.transpose(-2, -1)).item()
            
            print(f"({m:2d}, {n:2d}) -> {score:.4f}")
        
        print()
    
    print("观察：注意力分数主要取决于 |m-n|（相对位置）")


# 运行验证
verify_relative_position()
```

---

## 29. KV Cache深度解析

### 29.1 KV Cache原理与实现

```python
"""
KV Cache：推理加速的关键技术

问题背景：
在自回归生成中，每次生成一个新token时：
- 需要重新计算所有历史token的K和V
- 这导致了大量重复计算
- 序列越长，浪费越严重

KV Cache的解决方案：
- 缓存已计算过的K和V
- 每次只计算新token的K和V
- 将新的K、V追加到缓存中

复杂度分析：
无KV Cache: O(n²) 每次都要重新计算
有KV Cache: O(n) 只计算新token

显存分析：
KV Cache大小 = 2 × n_layers × batch_size × seq_len × n_heads × head_dim × dtype_size

例如：
- n_layers = 32
- batch_size = 1
- seq_len = 4096
- n_heads = 32
- head_dim = 128
- dtype_size = 2 (float16)

KV Cache = 2 × 32 × 1 × 4096 × 32 × 128 × 2 = 64 GB

这就是为什么长序列推理需要大量显存！
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional, Tuple, List

class KVCache:
    """
    KV Cache管理类
    
    负责存储和管理所有层的K、V缓存
    """
    
    def __init__(
        self,
        n_layers: int,
        n_heads: int,
        head_dim: int,
        max_seq_len: int = 2048,
        dtype: torch.dtype = torch.float16,
        device: str = 'cuda'
    ):
        """
        参数：
        - n_layers: 层数
        - n_heads: 头数
        - head_dim: 每个头的维度
        - max_seq_len: 最大序列长度
        - dtype: 数据类型
        - device: 设备
        """
        self.n_layers = n_layers
        self.n_heads = n_heads
        self.head_dim = head_dim
        self.max_seq_len = max_seq_len
        self.dtype = dtype
        self.device = device
        
        # 初始化缓存
        # 形状：(n_layers, batch_size, n_heads, max_seq_len, head_dim)
        # 注意：batch_size在首次使用时确定
        self.k_cache = None
        self.v_cache = None
        
        # 当前序列长度
        self.seq_len = 0
    
    def init_cache(self, batch_size: int):
        """初始化缓存"""
        self.k_cache = torch.zeros(
            self.n_layers, batch_size, self.n_heads, self.max_seq_len, self.head_dim,
            dtype=self.dtype, device=self.device
        )
        self.v_cache = torch.zeros(
            self.n_layers, batch_size, self.n_heads, self.max_seq_len, self.head_dim,
            dtype=self.dtype, device=self.device
        )
        self.seq_len = 0
    
    def update(
        self,
        layer_idx: int,
        k: torch.Tensor,
        v: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        更新缓存
        
        参数：
        - layer_idx: 层索引
        - k: 新的K (batch, n_heads, new_tokens, head_dim)
        - v: 新的V (batch, n_heads, new_tokens, head_dim)
        
        返回：
        - 完整的K和V（包括缓存）
        """
        new_tokens = k.shape[2]
        
        # 初始化缓存（如果需要）
        if self.k_cache is None:
            self.init_cache(k.shape[0])
        
        # 更新缓存
        self.k_cache[layer_idx, :, :, self.seq_len:self.seq_len + new_tokens, :] = k
        self.v_cache[layer_idx, :, :, self.seq_len:self.seq_len + new_tokens, :] = v
        
        # 更新序列长度
        self.seq_len += new_tokens
        
        # 返回完整的K和V
        return (
            self.k_cache[layer_idx, :, :, :self.seq_len, :],
            self.v_cache[layer_idx, :, :, :self.seq_len, :]
        )
    
    def get(self, layer_idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        """获取缓存"""
        if self.k_cache is None:
            return None, None
        return (
            self.k_cache[layer_idx, :, :, :self.seq_len, :],
            self.v_cache[layer_idx, :, :, :self.seq_len, :]
        )
    
    def clear(self):
        """清空缓存"""
        self.seq_len = 0
    
    def get_memory_usage(self) -> float:
        """获取显存使用量（GB）"""
        if self.k_cache is None:
            return 0.0
        
        bytes_per_element = 2 if self.dtype == torch.float16 else 4
        total_elements = 2 * self.n_layers * self.k_cache.shape[1] * self.max_seq_len * self.n_heads * self.head_dim
        
        return total_elements * bytes_per_element / (1024 ** 3)


class AttentionWithKVCache(nn.Module):
    """
    带KV Cache的注意力层
    """
    
    def __init__(self, dim: int, n_heads: int, layer_idx: int):
        super().__init__()
        
        self.dim = dim
        self.n_heads = n_heads
        self.head_dim = dim // n_heads
        self.layer_idx = layer_idx
        self.scale = self.head_dim ** -0.5
        
        self.q_proj = nn.Linear(dim, dim, bias=False)
        self.k_proj = nn.Linear(dim, dim, bias=False)
        self.v_proj = nn.Linear(dim, dim, bias=False)
        self.o_proj = nn.Linear(dim, dim, bias=False)
    
    def forward(
        self,
        x: torch.Tensor,
        kv_cache: Optional[KVCache] = None,
        use_cache: bool = True
    ) -> Tuple[torch.Tensor, Optional[KVCache]]:
        """
        前向传播
        
        参数：
        - x: (batch, seq_len, dim)
        - kv_cache: KV缓存对象
        - use_cache: 是否使用缓存
        
        返回：
        - output: 输出
        - kv_cache: 更新后的缓存
        """
        batch_size, seq_len, _ = x.shape
        
        # 投影
        q = self.q_proj(x).view(batch_size, seq_len, self.n_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(x).view(batch_size, seq_len, self.n_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(x).view(batch_size, seq_len, self.n_heads, self.head_dim).transpose(1, 2)
        
        # 更新或使用KV缓存
        if use_cache and kv_cache is not None:
            k, v = kv_cache.update(self.layer_idx, k, v)
        
        # 计算注意力
        scores = torch.matmul(q, k.transpose(-2, -1)) * self.scale
        
        # 因果掩码
        if use_cache and seq_len == 1:
            # 生成模式：只需要最后一个位置
            pass
        else:
            # 预填充模式：需要完整的因果掩码
            causal_mask = torch.triu(
                torch.ones(q.shape[2], k.shape[2], device=x.device, dtype=torch.bool),
                diagonal=1
            )
            scores = scores.masked_fill(causal_mask, float('-inf'))
        
        attn = F.softmax(scores, dim=-1)
        output = torch.matmul(attn, v)
        
        output = output.transpose(1, 2).contiguous().view(batch_size, seq_len, self.dim)
        output = self.o_proj(output)
        
        return output, kv_cache


class TransformerWithKVCache(nn.Module):
    """
    带KV Cache的完整Transformer
    """
    
    def __init__(self, dim: int, n_layers: int, n_heads: int, vocab_size: int):
        super().__init__()
        
        self.dim = dim
        self.n_layers = n_layers
        
        # 词嵌入
        self.token_embedding = nn.Embedding(vocab_size, dim)
        
        # Transformer层
        self.layers = nn.ModuleList([
            AttentionWithKVCache(dim, n_heads, i) for i in range(n_layers)
        ])
        
        # 输出层
        self.norm = nn.LayerNorm(dim)
        self.output = nn.Linear(dim, vocab_size, bias=False)
    
    def forward(
        self,
        input_ids: torch.Tensor,
        kv_cache: Optional[KVCache] = None,
        use_cache: bool = True
    ) -> Tuple[torch.Tensor, Optional[KVCache]]:
        """
        前向传播
        
        参数：
        - input_ids: (batch, seq_len)
        - kv_cache: KV缓存
        - use_cache: 是否使用缓存
        
        返回：
        - logits: (batch, seq_len, vocab_size)
        - kv_cache: 更新后的缓存
        """
        # 词嵌入
        x = self.token_embedding(input_ids)
        
        # 通过所有层
        for layer in self.layers:
            x, kv_cache = layer(x, kv_cache, use_cache)
        
        # 输出
        x = self.norm(x)
        logits = self.output(x)
        
        return logits, kv_cache


def demo_kv_cache():
    """KV Cache使用示例"""
    
    # 配置
    dim = 512
    n_layers = 8
    n_heads = 8
    vocab_size = 10000
    batch_size = 1
    
    # 创建模型
    model = TransformerWithKVCache(dim, n_layers, n_heads, vocab_size).cuda()
    model.eval()
    
    # 创建KV Cache
    kv_cache = KVCache(n_layers, n_heads, dim // n_heads, max_seq_len=2048)
    
    # 预填充阶段：处理整个prompt
    prompt = torch.randint(0, vocab_size, (batch_size, 10)).cuda()
    
    with torch.no_grad():
        logits, kv_cache = model(prompt, kv_cache=kv_cache, use_cache=True)
    
    print(f"预填充完成，KV Cache长度: {kv_cache.seq_len}")
    print(f"KV Cache显存使用: {kv_cache.get_memory_usage():.2f} GB")
    
    # 生成阶段：逐个生成token
    generated = []
    current_token = logits[:, -1:, :].argmax(dim=-1)  # 取最后一个位置的token
    
    for _ in range(20):
        with torch.no_grad():
            # 只输入一个token
            logits, kv_cache = model(current_token, kv_cache=kv_cache, use_cache=True)
        
        # 采样下一个token
        next_token = logits[:, -1:, :].argmax(dim=-1)
        generated.append(next_token.item())
        current_token = next_token
        
        print(f"生成token: {next_token.item()}, KV Cache长度: {kv_cache.seq_len}")
    
    print(f"\n生成的token序列: {generated}")


# 运行示例
demo_kv_cache()
```

### 29.2 KV Cache优化技术

```python
"""
KV Cache优化技术

1. Paged Attention (vLLM)
   - 将KV Cache分成固定大小的页
   - 按需分配，减少内存碎片
   - 支持内存共享（beam search）

2. Multi-Query Attention (MQA)
   - 多个头共享同一组K、V
   - 减少KV Cache大小

3. Grouped-Query Attention (GQA)
   - MQA和MHA的折中
   - 将头分组，每组共享K、V

4. KV Cache量化
   - 将KV Cache量化为int8
   - 减少显存占用

5. 滑动窗口注意力
   - 只保留最近W个token的KV Cache
   - 限制显存使用
"""

class PagedKVCache:
    """
    分页KV Cache
    
    类似vLLM的实现
    """
    
    def __init__(
        self,
        n_layers: int,
        n_heads: int,
        head_dim: int,
        page_size: int = 16,
        max_pages: int = 1024,
        dtype: torch.dtype = torch.float16,
        device: str = 'cuda'
    ):
        """
        参数：
        - page_size: 每页包含的token数
        - max_pages: 最大页数
        """
        self.n_layers = n_layers
        self.n_heads = n_heads
        self.head_dim = head_dim
        self.page_size = page_size
        self.max_pages = max_pages
        self.dtype = dtype
        self.device = device
        
        # 预分配内存池
        # 形状：(n_layers, max_pages, n_heads, page_size, head_dim)
        self.k_cache = torch.zeros(
            n_layers, max_pages, n_heads, page_size, head_dim,
            dtype=dtype, device=device
        )
        self.v_cache = torch.zeros(
            n_layers, max_pages, n_heads, page_size, head_dim,
            dtype=dtype, device=device
        )
        
        # 页分配状态
        self.page_table = {}  # sequence_id -> list of page_indices
        self.free_pages = list(range(max_pages))
        self.page_counter = 0
    
    def allocate_pages(self, seq_id: int, n_pages: int) -> List[int]:
        """为序列分配页"""
        if len(self.free_pages) < n_pages:
            raise RuntimeError("Not enough free pages")
        
        allocated = []
        for _ in range(n_pages):
            page_idx = self.free_pages.pop()
            allocated.append(page_idx)
        
        if seq_id not in self.page_table:
            self.page_table[seq_id] = []
        self.page_table[seq_id].extend(allocated)
        
        return allocated
    
    def write(
        self,
        seq_id: int,
        layer_idx: int,
        k: torch.Tensor,
        v: torch.Tensor,
        start_pos: int
    ):
        """
        写入KV Cache
        
        参数：
        - seq_id: 序列ID
        - layer_idx: 层索引
        - k, v: (batch, n_heads, new_tokens, head_dim)
        - start_pos: 起始位置
        """
        new_tokens = k.shape[2]
        pages = self.page_table[seq_id]
        
        for i, token_idx in enumerate(range(start_pos, start_pos + new_tokens)):
            # 计算页索引和页内偏移
            page_idx = token_idx // self.page_size
            page_offset = token_idx % self.page_size
            
            if page_idx >= len(pages):
                # 需要分配新页
                new_page = self.allocate_pages(seq_id, 1)[0]
            
            # 写入
            actual_page = pages[page_idx]
            self.k_cache[layer_idx, actual_page, :, page_offset, :] = k[:, :, i, :]
            self.v_cache[layer_idx, actual_page, :, page_offset, :] = v[:, :, i, :]
    
    def read(self, seq_id: int, layer_idx: int, length: int):
        """读取KV Cache"""
        pages = self.page_table[seq_id]
        n_pages = (length + self.page_size - 1) // self.page_size
        
        k_list = []
        v_list = []
        
        for page_idx in range(n_pages):
            actual_page = pages[page_idx]
            k_list.append(self.k_cache[layer_idx, actual_page])
            v_list.append(self.v_cache[layer_idx, actual_page])
        
        k = torch.cat(k_list, dim=1)[:, :length, :]
        v = torch.cat(v_list, dim=1)[:, :length, :]
        
        return k, v
    
    def free_sequence(self, seq_id: int):
        """释放序列占用的所有页"""
        if seq_id in self.page_table:
            self.free_pages.extend(self.page_table[seq_id])
            del self.page_table[seq_id]


class KVCacheQuantization:
    """
    KV Cache量化
    
    将float16的KV Cache量化为int8
    可以减少50%的显存占用
    """
    
    @staticmethod
    def quantize(kv: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        量化KV Cache
        
        参数：
        - kv: (batch, n_heads, seq_len, head_dim) float16
        
        返回：
        - kv_int8: int8量化的KV
        - scale: 缩放因子
        """
        # 计算每行的最大绝对值
        scale = kv.abs().max(dim=-1, keepdim=True).values / 127.0
        
        # 量化
        kv_int8 = (kv / scale).round().clamp(-128, 127).to(torch.int8)
        
        return kv_int8, scale
    
    @staticmethod
    def dequantize(kv_int8: torch.Tensor, scale: torch.Tensor) -> torch.Tensor:
        """
        反量化
        
        参数：
        - kv_int8: int8量化的KV
        - scale: 缩放因子
        
        返回：
        - kv: float16的KV
        """
        return kv_int8.to(torch.float16) * scale.to(torch.float16)


class SlidingWindowKVCache:
    """
    滑动窗口KV Cache
    
    只保留最近W个token的KV Cache
    """
    
    def __init__(
        self,
        n_layers: int,
        n_heads: int,
        head_dim: int,
        window_size: int = 4096,
        dtype: torch.dtype = torch.float16,
        device: str = 'cuda'
    ):
        self.window_size = window_size
        
        # 固定大小的环形缓冲区
        self.k_cache = torch.zeros(
            n_layers, n_heads, window_size, head_dim,
            dtype=dtype, device=device
        )
        self.v_cache = torch.zeros(
            n_layers, n_heads, window_size, head_dim,
            dtype=dtype, device=device
        )
        
        self.seq_len = 0
    
    def update(self, layer_idx: int, k: torch.Tensor, v: torch.Tensor):
        """更新缓存（环形写入）"""
        new_tokens = k.shape[2]
        
        for i in range(new_tokens):
            pos = (self.seq_len + i) % self.window_size
            self.k_cache[layer_idx, :, pos, :] = k[:, :, i, :]
            self.v_cache[layer_idx, :, pos, :] = v[:, :, i, :]
        
        self.seq_len += new_tokens
        
        # 返回有效窗口
        valid_len = min(self.seq_len, self.window_size)
        start_pos = self.seq_len % self.window_size
        
        if self.seq_len <= self.window_size:
            return (
                self.k_cache[layer_idx, :, :valid_len, :],
                self.v_cache[layer_idx, :, :valid_len, :]
            )
        else:
            # 需要重新排序（环形缓冲区）
            k_ordered = torch.cat([
                self.k_cache[layer_idx, :, start_pos:, :],
                self.k_cache[layer_idx, :, :start_pos, :]
            ], dim=1)
            v_ordered = torch.cat([
                self.v_cache[layer_idx, :, start_pos:, :],
                self.v_cache[layer_idx, :, :start_pos, :]
            ], dim=1)
            return k_ordered, v_ordered
```

---

## 30. 分布式训练详解

### 30.1 数据并行（Data Parallel）

```python
"""
数据并行（Data Parallel）

核心思想：
- 每个GPU持有完整的模型副本
- 数据被分割到不同GPU
- 每个GPU独立计算梯度
- 梯度在GPU间同步并平均

优点：
- 实现简单
- 适用于任何模型

缺点：
- 每个GPU需要存储完整模型
- 通信开销大（梯度同步）
"""

import torch
import torch.nn as nn
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel as DDP
from torch.utils.data import DataLoader, DistributedSampler
import os


def setup_distributed(rank: int, world_size: int):
    """
    初始化分布式环境
    
    参数：
    - rank: 当前进程的排名
    - world_size: 总进程数
    """
    os.environ['MASTER_ADDR'] = 'localhost'
    os.environ['MASTER_PORT'] = '12355'
    
    # 初始化进程组
    dist.init_process_group(
        backend='nccl',  # NVIDIA GPU使用nccl
        rank=rank,
        world_size=world_size
    )
    
    # 设置当前设备
    torch.cuda.set_device(rank)


def cleanup_distributed():
    """清理分布式环境"""
    dist.destroy_process_group()


class SimpleDataParallel:
    """
    简单的数据并行实现
    
    展示DDP的内部工作原理
    """
    
    def __init__(self, model: nn.Module, device_ids: list):
        """
        参数：
        - model: 模型
        - device_ids: GPU列表
        """
        self.model = model
        self.device_ids = device_ids
        self.output_device = device_ids[0]
        
        # 复制模型到每个GPU
        self.replicas = [model.to(f'cuda:{i}') for i in device_ids]
    
    def forward(self, *inputs, **kwargs):
        """
        前向传播
        
        将输入分割到不同GPU
        """
        # 分割输入
        inputs_split = self._scatter(inputs, self.device_ids)
        kwargs_split = self._scatter(kwargs, self.device_ids)
        
        # 并行计算
        outputs = []
        for replica, inp, kwarg in zip(self.replicas, inputs_split, kwargs_split):
            outputs.append(replica(*inp, **kwarg))
        
        # 收集输出
        return self._gather(outputs, self.output_device)
    
    def _scatter(self, inputs, device_ids):
        """将输入分割到不同设备"""
        if isinstance(inputs, torch.Tensor):
            return torch.chunk(inputs, len(device_ids))
        elif isinstance(inputs, (list, tuple)):
            return [self._scatter(x, device_ids) for x in inputs]
        elif isinstance(inputs, dict):
            return [{k: self._scatter(v, device_ids) for k, v in inputs.items()}]
        else:
            return [inputs] * len(device_ids)
    
    def _gather(self, outputs, output_device):
        """收集输出"""
        if isinstance(outputs[0], torch.Tensor):
            return torch.cat(outputs, dim=0).to(f'cuda:{output_device}')
        else:
            return outputs


def train_with_ddp(rank: int, world_size: int):
    """
    使用DDP进行分布式训练
    
    参数：
    - rank: 当前进程排名
    - world_size: 总进程数
    """
    # 初始化
    setup_distributed(rank, world_size)
    
    # 创建模型
    model = nn.Linear(1000, 100).cuda()
    
    # 包装为DDP
    model = DDP(model, device_ids=[rank])
    
    # 创建数据加载器
    # 使用DistributedSampler确保数据正确分割
    dataset = torch.randn(10000, 1000)
    sampler = DistributedSampler(
        dataset,
        num_replicas=world_size,
        rank=rank,
        shuffle=True
    )
    dataloader = DataLoader(
        dataset,
        batch_size=32,
        sampler=sampler
    )
    
    # 优化器
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    
    # 训练循环
    for epoch in range(10):
        # 设置epoch（确保每个epoch的shuffle不同）
        sampler.set_epoch(epoch)
        
        for batch_idx, data in enumerate(dataloader):
            data = data.cuda()
            
            # 前向传播
            output = model(data)
            loss = output.sum()
            
            # 反向传播
            optimizer.zero_grad()
            loss.backward()
            
            # DDP会自动同步梯度
            optimizer.step()
            
            if batch_idx % 100 == 0 and rank == 0:
                print(f'Epoch {epoch}, Batch {batch_idx}, Loss: {loss.item():.4f}')
    
    # 清理
    cleanup_distributed()


# 启动分布式训练
# 使用 torchrun 或 torch.multiprocessing
def main():
    world_size = torch.cuda.device_count()
    torch.multiprocessing.spawn(
        train_with_ddp,
        args=(world_size,),
        nprocs=world_size,
        join=True
    )
```

### 30.2 模型并行（Model Parallel）

```python
"""
模型并行（Model Parallel）

核心思想：
- 将模型分割到不同GPU
- 每个GPU只存储模型的一部分
- 数据顺序流过不同GPU

优点：
- 可以训练超大模型
- 减少每个GPU的显存需求

缺点：
- GPU利用率低（流水线气泡）
- 实现复杂

类型：
1. 张量并行（Tensor Parallel）：层内分割
2. 流水线并行（Pipeline Parallel）：层间分割
"""

class TensorParallelLinear(nn.Module):
    """
    张量并行线性层
    
    将矩阵乘法分割到多个GPU
    
    列并行：Y = X @ W，W按列分割
    行并行：Y = X @ W，W按行分割
    """
    
    def __init__(
        self,
        in_features: int,
        out_features: int,
        world_size: int,
        rank: int,
        parallel_mode: str = 'column'
    ):
        """
        参数：
        - in_features: 输入特征数
        - out_features: 输出特征数
        - world_size: GPU数量
        - rank: 当前GPU排名
        - parallel_mode: 'column' 或 'row'
        """
        super().__init__()
        
        self.world_size = world_size
        self.rank = rank
        self.parallel_mode = parallel_mode
        
        if parallel_mode == 'column':
            # 列并行：每个GPU持有out_features/world_size列
            assert out_features % world_size == 0
            self.out_features_per_gpu = out_features // world_size
            self.weight = nn.Parameter(
                torch.empty(self.out_features_per_gpu, in_features)
            )
        else:
            # 行并行：每个GPU持有in_features/world_size行
            assert in_features % world_size == 0
            self.in_features_per_gpu = in_features // world_size
            self.weight = nn.Parameter(
                torch.empty(out_features, self.in_features_per_gpu)
            )
        
        self._init_weight()
    
    def _init_weight(self):
        """初始化权重"""
        nn.init.kaiming_uniform_(self.weight)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        前向传播
        
        列并行：
        - 输入：完整输入 (batch, in_features)
        - 输出：部分输出 (batch, out_features/world_size)
        
        行并行：
        - 输入：部分输入 (batch, in_features/world_size)
        - 输出：部分结果，需要all-reduce
        """
        if self.parallel_mode == 'column':
            # Y_i = X @ W_i
            return torch.matmul(x, self.weight.t())
        else:
            # Y_i = X_i @ W_i
            # Y = sum(Y_i) via all-reduce
            output = torch.matmul(x, self.weight.t())
            dist.all_reduce(output, op=dist.ReduceOp.SUM)
            return output


class TensorParallelAttention(nn.Module):
    """
    张量并行注意力层
    
    注意力头的并行化：
    - 每个GPU持有部分注意力头
    - Q、K、V投影使用列并行
    - 输出投影使用行并行
    """
    
    def __init__(
        self,
        dim: int,
        n_heads: int,
        world_size: int,
        rank: int
    ):
        super().__init__()
        
        assert n_heads % world_size == 0
        
        self.dim = dim
        self.n_heads = n_heads
        self.n_heads_per_gpu = n_heads // world_size
        self.head_dim = dim // n_heads
        self.world_size = world_size
        self.rank = rank
        self.scale = self.head_dim ** -0.5
        
        # Q、K、V投影：列并行
        self.q_proj = TensorParallelLinear(dim, dim, world_size, rank, 'column')
        self.k_proj = TensorParallelLinear(dim, dim, world_size, rank, 'column')
        self.v_proj = TensorParallelLinear(dim, dim, world_size, rank, 'column')
        
        # 输出投影：行并行
        self.o_proj = TensorParallelLinear(dim, dim, world_size, rank, 'row')
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        前向传播
        
        参数：
        - x: (batch, seq_len, dim)
        """
        batch_size, seq_len, _ = x.shape
        
        # 投影（每个GPU得到部分头）
        q = self.q_proj(x).view(batch_size, seq_len, self.n_heads_per_gpu, self.head_dim).transpose(1, 2)
        k = self.k_proj(x).view(batch_size, seq_len, self.n_heads_per_gpu, self.head_dim).transpose(1, 2)
        v = self.v_proj(x).view(batch_size, seq_len, self.n_heads_per_gpu, self.head_dim).transpose(1, 2)
        
        # 计算注意力（每个GPU独立计算）
        scores = torch.matmul(q, k.transpose(-2, -1)) * self.scale
        attn = torch.softmax(scores, dim=-1)
        output = torch.matmul(attn, v)
        
        # 重塑
        output = output.transpose(1, 2).contiguous().view(batch_size, seq_len, -1)
        
        # 输出投影（行并行，自动all-reduce）
        output = self.o_proj(output)
        
        return output


class PipelineParallel(nn.Module):
    """
    流水线并行
    
    将模型的不同层分配到不同GPU
    """
    
    def __init__(self, layers: nn.ModuleList, num_stages: int, rank: int):
        """
        参数：
        - layers: 所有层的列表
        - num_stages: 流水线阶段数
        - rank: 当前阶段排名
        """
        super().__init__()
        
        self.num_stages = num_stages
        self.rank = rank
        
        # 计算当前阶段持有的层
        layers_per_stage = len(layers) // num_stages
        start_idx = rank * layers_per_stage
        end_idx = start_idx + layers_per_stage
        
        self.layers = nn.ModuleList(layers[start_idx:end_idx])
        
        # 是否是第一/最后阶段
        self.is_first = (rank == 0)
        self.is_last = (rank == num_stages - 1)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        前向传播
        
        数据流：GPU0 -> GPU1 -> GPU2 -> ...
        """
        # 接收输入
        if not self.is_first:
            x = self._recv_from_prev()
        
        # 通过当前阶段的层
        for layer in self.layers:
            x = layer(x)
        
        # 发送输出
        if not self.is_last:
            self._send_to_next(x)
            return None
        else:
            return x
    
    def _recv_from_prev(self):
        """从前一个阶段接收数据"""
        x = torch.empty(...)  # 预分配缓冲区
        dist.recv(x, src=self.rank - 1)
        return x
    
    def _send_to_next(self, x):
        """发送数据到下一个阶段"""
        dist.send(x, dst=self.rank + 1)


class PipelineSchedule:
    """
    流水线调度
    
    解决流水线气泡问题
    
    常见调度策略：
    1. GPipe：将batch分成micro-batch
    2. 1F1B：交替执行前向和后向
    3. Interleaved：交错调度
    """
    
    def __init__(self, num_stages: int, num_micro_batches: int):
        """
        参数：
        - num_stages: 流水线阶段数
        - num_micro_batches: micro-batch数量
        """
        self.num_stages = num_stages
        self.num_micro_batches = num_micro_batches
    
    def gpipe_schedule(self):
        """
        GPipe调度
        
        所有micro-batch的前向传播完成后，再执行后向传播
        
        时间线：
        Stage 0: F0 F1 F2 F3 B0 B1 B2 B3
        Stage 1:    F0 F1 F2 F3 B0 B1 B2 B3
        Stage 2:       F0 F1 F2 F3 B0 B1 B2 B3
        Stage 3:          F0 F1 F2 F3 B0 B1 B2 B3
        """
        schedule = []
        
        # 前向传播
        for mb in range(self.num_micro_batches):
            for stage in range(self.num_stages):
                schedule.append(('forward', stage, mb))
        
        # 后向传播
        for mb in range(self.num_micro_batches):
            for stage in range(self.num_stages):
                schedule.append(('backward', stage, mb))
        
        return schedule
    
    def one_f_one_b_schedule(self):
        """
        1F1B调度
        
        交替执行前向和后向，减少气泡
        
        时间线：
        Stage 0: F0 F1 F2 F3 B0 F4 B1 F5 B2 ...
        Stage 1:    F0 F1 F2 B0 F3 B1 F4 B2 ...
        Stage 2:       F0 F1 B0 F2 B1 F3 B2 ...
        Stage 3:          F0 B0 F1 B1 F2 B2 ...
        """
        schedule = []
        
        # 预热阶段：填充流水线
        for stage in range(self.num_stages):
            schedule.append(('forward', stage, 0))
        
        # 稳定阶段：1F1B
        for mb in range(1, self.num_micro_batches):
            for stage in range(self.num_stages):
                schedule.append(('forward', stage, mb))
                schedule.append(('backward', stage, mb - 1))
        
        # 冷却阶段：完成后向传播
        for stage in range(self.num_stages):
            schedule.append(('backward', stage, self.num_micro_batches - 1))
        
        return schedule
```

### 30.3 混合并行与ZeRO优化

```python
"""
混合并行与ZeRO优化

混合并行：
- 数据并行 + 张量并行 + 流水线并行
- 3D并行可以训练超大规模模型

ZeRO (Zero Redundancy Optimizer)：
- 减少数据并行的内存冗余
- 分阶段优化：
  - ZeRO-1: 分割优化器状态
  - ZeRO-2: 分割梯度
  - ZeRO-3: 分割模型参数
"""

class ZeROOptimizer:
    """
    ZeRO优化器简化实现
    
    展示ZeRO的核心思想
    """
    
    def __init__(
        self,
        params,
        optimizer_class,
        rank: int,
        world_size: int,
        zero_stage: int = 1
    ):
        """
        参数：
        - params: 模型参数
        - optimizer_class: 优化器类
        - rank: 当前进程排名
        - world_size: 总进程数
        - zero_stage: ZeRO阶段（1, 2, 或 3）
        """
        self.rank = rank
        self.world_size = world_size
        self.zero_stage = zero_stage
        
        # 根据ZeRO阶段分割不同内容
        if zero_stage >= 1:
            # ZeRO-1: 分割优化器状态
            self._partition_optimizer_states(params)
        
        if zero_stage >= 2:
            # ZeRO-2: 分割梯度
            self._partition_gradients(params)
        
        if zero_stage >= 3:
            # ZeRO-3: 分割模型参数
            self._partition_parameters(params)
        
        # 创建优化器
        self.optimizer = optimizer_class(params)
    
    def _partition_optimizer_states(self, params):
        """分割优化器状态"""
        for param in params:
            if param.requires_grad:
                # 每个GPU只持有部分优化器状态
                total_size = param.numel()
                partition_size = (total_size + self.world_size - 1) // self.world_size
                
                start_idx = self.rank * partition_size
                end_idx = min(start_idx + partition_size, total_size)
                
                # 存储分区信息
                param._zero_partition = (start_idx, end_idx)
    
    def _partition_gradients(self, params):
        """分割梯度"""
        for param in params:
            if param.requires_grad:
                # 注册梯度hook
                param.register_hook(self._gradient_hook)
    
    def _gradient_hook(self, grad):
        """梯度hook：只保留当前GPU负责的部分"""
        start_idx, end_idx = grad._zero_partition
        grad_partition = grad.view(-1)[start_idx:end_idx]
        return grad_partition
    
    def _partition_parameters(self, params):
        """分割模型参数"""
        for param in params:
            # ZeRO-3: 参数按需获取
            param._zero_param_partition = True
    
    def step(self):
        """优化步骤"""
        # ZeRO-3: 收集参数
        if self.zero_stage >= 3:
            self._gather_parameters()
        
        # 优化步骤
        self.optimizer.step()
        
        # ZeRO-3: 释放参数
        if self.zero_stage >= 3:
            self._release_parameters()
    
    def _gather_parameters(self):
        """收集所有参数"""
        for param in self.optimizer.param_groups[0]['params']:
            dist.all_gather(
                list(param._zero_shards),
                param._zero_local_shard
            )
    
    def _release_parameters(self):
        """释放参数（只保留本地分片）"""
        pass


def calculate_memory_usage(
    model_params: int,
    world_size: int,
    zero_stage: int = 0
):
    """
    计算不同并行策略的显存使用
    
    参数：
    - model_params: 模型参数量
    - world_size: GPU数量
    - zero_stage: ZeRO阶段
    
    返回：
    - 每个GPU的显存使用（GB）
    """
    bytes_per_param = 4  # float32
    
    # 模型参数
    param_memory = model_params * bytes_per_param
    
    # 梯度
    gradient_memory = model_params * bytes_per_param
    
    # 优化器状态（Adam: m + v）
    optimizer_memory = 2 * model_params * bytes_per_param
    
    # 总显存
    total_memory = param_memory + gradient_memory + optimizer_memory
    
    if zero_stage == 0:
        # 标准数据并行：每个GPU存储完整副本
        per_gpu_memory = total_memory
    elif zero_stage == 1:
        # ZeRO-1: 分割优化器状态
        per_gpu_memory = param_memory + gradient_memory + optimizer_memory / world_size
    elif zero_stage == 2:
        # ZeRO-2: 分割优化器状态和梯度
        per_gpu_memory = param_memory + (gradient_memory + optimizer_memory) / world_size
    elif zero_stage == 3:
        # ZeRO-3: 分割所有内容
        per_gpu_memory = total_memory / world_size
    
    return per_gpu_memory / (1024 ** 3)  # 转换为GB


# 示例：计算不同配置的显存使用
model_params = 7e9  # 7B参数模型
world_size = 8  # 8个GPU

print("7B模型在不同ZeRO阶段的显存使用（8 GPU）：")
for stage in range(4):
    memory = calculate_memory_usage(model_params, world_size, stage)
    print(f"ZeRO-{stage}: {memory:.2f} GB per GPU")
```

---

## 31. RMSNorm与LayerNorm深度对比

### 31.1 归一化层原理详解

```python
"""
归一化层在深度学习中的作用

为什么需要归一化？
1. 稳定训练：减少内部协变量偏移
2. 加速收敛：允许使用更大的学习率
3. 正则化效果：防止过拟合

常见归一化方法：
1. Batch Normalization (BN)
2. Layer Normalization (LN)
3. RMS Normalization (RMSNorm)
4. Group Normalization (GN)

在Transformer中，主要使用LN和RMSNorm
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import math

class LayerNorm(nn.Module):
    """
    Layer Normalization 完整实现
    
    公式：
    y = (x - μ) / σ * γ + β
    
    其中：
    - μ = mean(x)  # 沿特征维度计算均值
    - σ = std(x)   # 沿特征维度计算标准差
    - γ, β: 可学习参数
    
    特点：
    1. 对每个样本独立归一化
    2. 不依赖batch size
    3. 适用于序列数据
    """
    
    def __init__(self, dim: int, eps: float = 1e-6):
        """
        参数：
        - dim: 特征维度
        - eps: 防止除零的小常数
        """
        super().__init__()
        
        self.dim = dim
        self.eps = eps
        
        # 可学习参数
        self.weight = nn.Parameter(torch.ones(dim))  # γ
        self.bias = nn.Parameter(torch.zeros(dim))   # β
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        前向传播
        
        参数：
        - x: (batch, seq_len, dim) 或 (batch, dim)
        
        返回：
        - 归一化后的张量
        """
        # 计算均值和方差
        # keepdim=True 保持维度，便于广播
        mean = x.mean(dim=-1, keepdim=True)
        var = x.var(dim=-1, keepdim=True, unbiased=False)
        
        # 归一化
        x_norm = (x - mean) / torch.sqrt(var + self.eps)
        
        # 缩放和平移
        return self.weight * x_norm + self.bias


class RMSNorm(nn.Module):
    """
    Root Mean Square Layer Normalization
    
    公式：
    y = x / RMS(x) * γ
    
    其中：
    RMS(x) = sqrt(mean(x²) + ε)
    
    相比LayerNorm的改进：
    1. 不计算均值，只计算均方根
    2. 不使用偏置项β
    3. 计算量更小
    4. 实验表明效果相当或更好
    
    为什么RMSNorm有效？
    1. 重新缩放不变性：对输入的缩放不敏感
    2. 隐式学习率衰减：训练过程中自动调整学习率
    3. 简化计算：省去均值计算和偏置项
    """
    
    def __init__(self, dim: int, eps: float = 1e-6):
        """
        参数：
        - dim: 特征维度
        - eps: 防止除零的小常数
        """
        super().__init__()
        
        self.dim = dim
        self.eps = eps
        
        # 只有weight，没有bias
        self.weight = nn.Parameter(torch.ones(dim))
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        前向传播
        
        参数：
        - x: (batch, seq_len, dim) 或 (batch, dim)
        
        返回：
        - 归一化后的张量
        """
        # 计算RMS
        # RMS = sqrt(mean(x²))
        rms = torch.sqrt(torch.mean(x ** 2, dim=-1, keepdim=True) + self.eps)
        
        # 归一化并缩放
        return self.weight * (x / rms)
    
    def _norm(self, x):
        """底层归一化函数"""
        return x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + self.eps)


class LayerNormWithBias(nn.Module):
    """
    带偏置的LayerNorm（GPT-2风格）
    
    与标准LayerNorm的区别：
    - 在归一化之前有一个可选的偏置
    """
    
    def __init__(self, dim: int, eps: float = 1e-5):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(dim))
        self.bias = nn.Parameter(torch.zeros(dim))
        self.eps = eps
    
    def forward(self, x):
        mean = x.mean(-1, keepdim=True)
        std = x.std(-1, keepdim=True, unbiased=False)
        return self.weight * (x - mean) / (std + self.eps) + self.bias


def compare_norm_layers():
    """
    对比不同归一化层的性能
    """
    import time
    
    batch_size = 32
    seq_len = 512
    dim = 768
    
    x = torch.randn(batch_size, seq_len, dim).cuda()
    
    # 创建归一化层
    layer_norm = LayerNorm(dim).cuda()
    rms_norm = RMSNorm(dim).cuda()
    
    # 预热
    for _ in range(10):
        _ = layer_norm(x)
        _ = rms_norm(x)
    
    torch.cuda.synchronize()
    
    # 测试LayerNorm
    start = time.time()
    for _ in range(1000):
        _ = layer_norm(x)
    torch.cuda.synchronize()
    ln_time = time.time() - start
    
    # 测试RMSNorm
    start = time.time()
    for _ in range(1000):
        _ = rms_norm(x)
    torch.cuda.synchronize()
    rms_time = time.time() - start
    
    print(f"LayerNorm 时间: {ln_time:.4f}s")
    print(f"RMSNorm 时间: {rms_time:.4f}s")
    print(f"RMSNorm 加速: {ln_time/rms_time:.2f}x")
    
    # 参数量对比
    ln_params = sum(p.numel() for p in layer_norm.parameters())
    rms_params = sum(p.numel() for p in rms_norm.parameters())
    
    print(f"\nLayerNorm 参数量: {ln_params}")
    print(f"RMSNorm 参数量: {rms_params}")
    print(f"参数减少: {(1 - rms_params/ln_params)*100:.1f}%")


# 运行对比
compare_norm_layers()
```

### 31.2 归一化层的数学分析

```python
"""
归一化层的数学分析

LayerNorm的数学推导：

给定输入 x = [x₁, x₂, ..., x_d]

1. 计算均值：
   μ = (1/d) × Σᵢ xᵢ

2. 计算方差：
   σ² = (1/d) × Σᵢ (xᵢ - μ)²

3. 归一化：
   x̂ᵢ = (xᵢ - μ) / √(σ² + ε)

4. 缩放和平移：
   yᵢ = γᵢ × x̂ᵢ + βᵢ

RMSNorm的数学推导：

1. 计算均方根：
   RMS(x) = √((1/d) × Σᵢ xᵢ² + ε)

2. 归一化：
   x̂ᵢ = xᵢ / RMS(x)

3. 缩放：
   yᵢ = γᵢ × x̂ᵢ

计算复杂度对比：

LayerNorm:
- 均值计算: O(d)
- 方差计算: O(d)
- 归一化: O(d)
- 总计: O(3d)

RMSNorm:
- 平方计算: O(d)
- 均值计算: O(d)
- 开方计算: O(1)
- 归一化: O(d)
- 总计: O(2d)

RMSNorm节省约33%的计算量
"""

def analyze_gradient_flow():
    """
    分析归一化层的梯度流动
    """
    import torch
    
    # 创建测试数据
    x = torch.randn(4, 8, requires_grad=True)
    
    # LayerNorm
    ln = nn.LayerNorm(8)
    y_ln = ln(x)
    loss_ln = y_ln.sum()
    loss_ln.backward()
    grad_ln = x.grad.clone()
    
    x.grad = None
    
    # RMSNorm
    rms = RMSNorm(8)
    y_rms = rms(x)
    loss_rms = y_rms.sum()
    loss_rms.backward()
    grad_rms = x.grad.clone()
    
    print("LayerNorm 梯度统计:")
    print(f"  均值: {grad_ln.mean().item():.6f}")
    print(f"  标准差: {grad_ln.std().item():.6f}")
    print(f"  最大值: {grad_ln.max().item():.6f}")
    print(f"  最小值: {grad_ln.min().item():.6f}")
    
    print("\nRMSNorm 梯度统计:")
    print(f"  均值: {grad_rms.mean().item():.6f}")
    print(f"  标准差: {grad_rms.std().item():.6f}")
    print(f"  最大值: {grad_rms.max().item():.6f}")
    print(f"  最小值: {grad_rms.min().item():.6f}")


# 运行分析
analyze_gradient_flow()
```

### 31.3 Pre-Norm vs Post-Norm

```python
"""
Transformer中的归一化位置

1. Post-Norm（原始Transformer）
   - 归一化在残差连接之后
   - 结构：x + Norm(Sublayer(x))
   - 训练不稳定，需要warmup

2. Pre-Norm（GPT-2/LLaMA）
   - 归一化在子层之前
   - 结构：x + Sublayer(Norm(x))
   - 训练稳定，不需要warmup

Pre-Norm的优势：
1. 梯度流动更平滑
2. 可以堆叠更深的网络
3. 不需要学习率warmup
4. 训练更稳定
"""

class PostNormTransformerBlock(nn.Module):
    """
    Post-Norm Transformer块
    
    原始Transformer的结构
    """
    
    def __init__(self, dim, n_heads, ff_dim):
        super().__init__()
        
        self.attention = nn.MultiheadAttention(dim, n_heads)
        self.ff = nn.Sequential(
            nn.Linear(dim, ff_dim),
            nn.ReLU(),
            nn.Linear(ff_dim, dim)
        )
        
        # 归一化层
        self.norm1 = nn.LayerNorm(dim)
        self.norm2 = nn.LayerNorm(dim)
    
    def forward(self, x):
        # Post-Norm: 先计算子层，再归一化
        # 注意力 + 残差 + 归一化
        attn_out, _ = self.attention(x, x, x)
        x = self.norm1(x + attn_out)
        
        # FFN + 残差 + 归一化
        ff_out = self.ff(x)
        x = self.norm2(x + ff_out)
        
        return x


class PreNormTransformerBlock(nn.Module):
    """
    Pre-Norm Transformer块
    
    GPT-2/LLaMA的结构
    """
    
    def __init__(self, dim, n_heads, ff_dim):
        super().__init__()
        
        self.attention = nn.MultiheadAttention(dim, n_heads)
        self.ff = nn.Sequential(
            nn.Linear(dim, ff_dim),
            nn.GELU(),
            nn.Linear(ff_dim, dim)
        )
        
        # 归一化层
        self.norm1 = nn.LayerNorm(dim)
        self.norm2 = nn.LayerNorm(dim)
    
    def forward(self, x):
        # Pre-Norm: 先归一化，再计算子层
        # 归一化 + 注意力 + 残差
        attn_out, _ = self.attention(self.norm1(x), self.norm1(x), self.norm1(x))
        x = x + attn_out
        
        # 归一化 + FFN + 残差
        ff_out = self.ff(self.norm2(x))
        x = x + ff_out
        
        return x


class LLaMABlock(nn.Module):
    """
    LLaMA风格的Transformer块
    
    特点：
    1. Pre-Norm
    2. RMSNorm
    3. SwiGLU FFN
    4. RoPE
    """
    
    def __init__(self, dim, n_heads, ff_dim, multiple_of=256):
        super().__init__()
        
        # RMSNorm
        self.attention_norm = RMSNorm(dim)
        self.ffn_norm = RMSNorm(dim)
        
        # 注意力（简化版）
        self.attention = nn.MultiheadAttention(dim, n_heads)
        
        # SwiGLU FFN
        hidden_dim = multiple_of * ((ff_dim + multiple_of - 1) // multiple_of)
        self.w1 = nn.Linear(dim, hidden_dim, bias=False)
        self.w2 = nn.Linear(hidden_dim, dim, bias=False)
        self.w3 = nn.Linear(dim, hidden_dim, bias=False)
    
    def forward(self, x):
        # 注意力块
        h = x + self.attention(self.attention_norm(x))
        
        # FFN块（SwiGLU）
        out = h + self.ffn(h)
        
        return out
    
    def ffn(self, x):
        """SwiGLU前馈网络"""
        return self.w2(F.silu(self.w1(x)) * self.w3(x))


def compare_norm_positions():
    """
    对比Pre-Norm和Post-Norm的训练稳定性
    """
    import matplotlib.pyplot as plt
    
    dim = 256
    n_heads = 4
    ff_dim = 1024
    n_layers = 24
    batch_size = 16
    seq_len = 128
    
    # 创建模型
    post_norm = nn.Sequential(*[
        PostNormTransformerBlock(dim, n_heads, ff_dim) 
        for _ in range(n_layers)
    ])
    
    pre_norm = nn.Sequential(*[
        PreNormTransformerBlock(dim, n_heads, ff_dim) 
        for _ in range(n_layers)
    ])
    
    # 测试梯度范数
    x = torch.randn(batch_size, seq_len, dim)
    
    # Post-Norm梯度
    post_norm.zero_grad()
    out = post_norm(x)
    loss = out.sum()
    loss.backward()
    post_grad_norm = torch.sqrt(sum(
        p.grad.pow(2).sum() for p in post_norm.parameters() if p.grad is not None
    ))
    
    # Pre-Norm梯度
    pre_norm.zero_grad()
    out = pre_norm(x)
    loss = out.sum()
    loss.backward()
    pre_grad_norm = torch.sqrt(sum(
        p.grad.pow(2).sum() for p in pre_norm.parameters() if p.grad is not None
    ))
    
    print(f"Post-Norm 梯度范数: {post_grad_norm.item():.4f}")
    print(f"Pre-Norm 梯度范数: {pre_grad_norm.item():.4f}")
    print(f"\nPre-Norm梯度更稳定，适合深层网络训练")


# 运行对比
compare_norm_positions()
```

---

## 32. GQA分组查询注意力详解

### 32.1 注意力机制演进

```python
"""
注意力机制的演进

1. Multi-Head Attention (MHA)
   - 每个头有独立的Q、K、V
   - KV Cache大小: n_heads × seq_len × head_dim
   - 效果最好，但显存占用大

2. Multi-Query Attention (MQA)
   - 所有头共享同一组K、V
   - KV Cache大小: 1 × seq_len × head_dim
   - 显存占用最小，但效果略有下降

3. Grouped-Query Attention (GQA)
   - 将头分组，每组共享K、V
   - KV Cache大小: n_groups × seq_len × head_dim
   - 平衡效果和效率

显存对比（以LLaMA-70B为例）：
- MHA: 64个头，KV Cache = 64 × seq_len × 128
- MQA: 1组，KV Cache = 1 × seq_len × 128
- GQA: 8组，KV Cache = 8 × seq_len × 128

GQA相比MHA节省87.5%的KV Cache显存！
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import math

class MultiHeadAttention(nn.Module):
    """
    标准多头注意力（MHA）
    
    每个头有独立的Q、K、V
    """
    
    def __init__(self, dim: int, n_heads: int):
        super().__init__()
        
        self.dim = dim
        self.n_heads = n_heads
        self.head_dim = dim // n_heads
        self.scale = self.head_dim ** -0.5
        
        # 每个头独立的投影
        self.q_proj = nn.Linear(dim, dim, bias=False)
        self.k_proj = nn.Linear(dim, dim, bias=False)
        self.v_proj = nn.Linear(dim, dim, bias=False)
        self.o_proj = nn.Linear(dim, dim, bias=False)
    
    def forward(self, x: torch.Tensor, mask: torch.Tensor = None):
        """
        前向传播
        
        参数：
        - x: (batch, seq_len, dim)
        - mask: 可选的注意力掩码
        """
        batch_size, seq_len, _ = x.shape
        
        # 投影并重塑为多头
        q = self.q_proj(x).view(batch_size, seq_len, self.n_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(x).view(batch_size, seq_len, self.n_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(x).view(batch_size, seq_len, self.n_heads, self.head_dim).transpose(1, 2)
        
        # 计算注意力
        scores = torch.matmul(q, k.transpose(-2, -1)) * self.scale
        
        if mask is not None:
            scores = scores.masked_fill(mask == 0, float('-inf'))
        
        attn = F.softmax(scores, dim=-1)
        output = torch.matmul(attn, v)
        
        # 合并多头
        output = output.transpose(1, 2).contiguous().view(batch_size, seq_len, self.dim)
        
        return self.o_proj(output)


class MultiQueryAttention(nn.Module):
    """
    多查询注意力（MQA）
    
    所有头共享同一组K、V
    
    优点：
    - KV Cache大小减少n_heads倍
    - 推理速度更快
    
    缺点：
    - 效果略有下降
    """
    
    def __init__(self, dim: int, n_heads: int):
        super().__init__()
        
        self.dim = dim
        self.n_heads = n_heads
        self.head_dim = dim // n_heads
        self.scale = self.head_dim ** -0.5
        
        # Q有n_heads个头
        self.q_proj = nn.Linear(dim, dim, bias=False)
        
        # K和V只有1个头（共享）
        self.k_proj = nn.Linear(dim, self.head_dim, bias=False)
        self.v_proj = nn.Linear(dim, self.head_dim, bias=False)
        
        self.o_proj = nn.Linear(dim, dim, bias=False)
    
    def forward(self, x: torch.Tensor, mask: torch.Tensor = None):
        """
        前向传播
        """
        batch_size, seq_len, _ = x.shape
        
        # Q: n_heads个头
        q = self.q_proj(x).view(batch_size, seq_len, self.n_heads, self.head_dim).transpose(1, 2)
        
        # K, V: 1个头，需要扩展
        k = self.k_proj(x).unsqueeze(1)  # (batch, 1, seq, head_dim)
        v = self.v_proj(x).unsqueeze(1)  # (batch, 1, seq, head_dim)
        
        # 计算注意力
        scores = torch.matmul(q, k.transpose(-2, -1)) * self.scale
        
        if mask is not None:
            scores = scores.masked_fill(mask == 0, float('-inf'))
        
        attn = F.softmax(scores, dim=-1)
        output = torch.matmul(attn, v)
        
        # 合并多头
        output = output.transpose(1, 2).contiguous().view(batch_size, seq_len, self.dim)
        
        return self.o_proj(output)


class GroupedQueryAttention(nn.Module):
    """
    分组查询注意力（GQA）
    
    将n_heads个头分成n_groups组，每组共享K、V
    
    GQA是MHA和MQA的折中：
    - 比MQA效果更好
    - 比MHA显存占用更少
    
    LLaMA 2/3 使用GQA
    """
    
    def __init__(self, dim: int, n_heads: int, n_groups: int):
        """
        参数：
        - dim: 模型维度
        - n_heads: 查询头数
        - n_groups: KV组数（每组共享K、V）
        """
        super().__init__()
        
        assert n_heads % n_groups == 0, "n_heads必须能被n_groups整除"
        
        self.dim = dim
        self.n_heads = n_heads
        self.n_groups = n_groups
        self.head_dim = dim // n_heads
        self.heads_per_group = n_heads // n_groups
        self.scale = self.head_dim ** -0.5
        
        # Q: n_heads个头
        self.q_proj = nn.Linear(dim, dim, bias=False)
        
        # K, V: n_groups个组
        self.k_proj = nn.Linear(dim, n_groups * self.head_dim, bias=False)
        self.v_proj = nn.Linear(dim, n_groups * self.head_dim, bias=False)
        
        self.o_proj = nn.Linear(dim, dim, bias=False)
    
    def forward(self, x: torch.Tensor, mask: torch.Tensor = None):
        """
        前向传播
        """
        batch_size, seq_len, _ = x.shape
        
        # Q: (batch, n_heads, seq, head_dim)
        q = self.q_proj(x).view(batch_size, seq_len, self.n_heads, self.head_dim).transpose(1, 2)
        
        # K, V: (batch, n_groups, seq, head_dim)
        k = self.k_proj(x).view(batch_size, seq_len, self.n_groups, self.head_dim).transpose(1, 2)
        v = self.v_proj(x).view(batch_size, seq_len, self.n_groups, self.head_dim).transpose(1, 2)
        
        # 扩展K、V以匹配Q的头数
        # 每个组的K、V被heads_per_group个头共享
        k = k.repeat_interleave(self.heads_per_group, dim=1)  # (batch, n_heads, seq, head_dim)
        v = v.repeat_interleave(self.heads_per_group, dim=1)  # (batch, n_heads, seq, head_dim)
        
        # 计算注意力
        scores = torch.matmul(q, k.transpose(-2, -1)) * self.scale
        
        if mask is not None:
            scores = scores.masked_fill(mask == 0, float('-inf'))
        
        attn = F.softmax(scores, dim=-1)
        output = torch.matmul(attn, v)
        
        # 合并多头
        output = output.transpose(1, 2).contiguous().view(batch_size, seq_len, self.dim)
        
        return self.o_proj(output)


def compare_attention_variants():
    """
    对比不同注意力变体
    """
    import time
    
    batch_size = 4
    seq_len = 512
    dim = 1024
    n_heads = 32
    n_groups = 8
    
    x = torch.randn(batch_size, seq_len, dim).cuda()
    
    # 创建模型
    mha = MultiHeadAttention(dim, n_heads).cuda()
    mqa = MultiQueryAttention(dim, n_heads).cuda()
    gqa = GroupedQueryAttention(dim, n_heads, n_groups).cuda()
    
    # 预热
    for _ in range(10):
        _ = mha(x)
        _ = mqa(x)
        _ = gqa(x)
    
    torch.cuda.synchronize()
    
    # 测试速度
    for name, model in [("MHA", mha), ("MQA", mqa), ("GQA", gqa)]:
        torch.cuda.synchronize()
        start = time.time()
        for _ in range(100):
            _ = model(x)
        torch.cuda.synchronize()
        elapsed = time.time() - start
        
        # 计算KV Cache大小
        if name == "MHA":
            kv_size = n_heads * seq_len * (dim // n_heads) * 2
        elif name == "MQA":
            kv_size = 1 * seq_len * (dim // n_heads) * 2
        else:
            kv_size = n_groups * seq_len * (dim // n_heads) * 2
        
        print(f"{name}:")
        print(f"  时间: {elapsed:.4f}s")
        print(f"  KV Cache: {kv_size * 2 / 1024**2:.2f} MB (float16)")
        print()


# 运行对比
compare_attention_variants()
```

### 32.2 GQA的优化实现

```python
"""
GQA的高效实现

关键优化：
1. 避免显式的repeat_interleave
2. 使用einsum优化矩阵乘法
3. 支持KV Cache
"""

class EfficientGQA(nn.Module):
    """
    高效GQA实现
    
    使用einsum避免显式扩展
    """
    
    def __init__(self, dim: int, n_heads: int, n_groups: int):
        super().__init__()
        
        assert n_heads % n_groups == 0
        
        self.dim = dim
        self.n_heads = n_heads
        self.n_groups = n_groups
        self.head_dim = dim // n_heads
        self.heads_per_group = n_heads // n_groups
        self.scale = self.head_dim ** -0.5
        
        # 投影层
        self.q_proj = nn.Linear(dim, dim, bias=False)
        self.k_proj = nn.Linear(dim, n_groups * self.head_dim, bias=False)
        self.v_proj = nn.Linear(dim, n_groups * self.head_dim, bias=False)
        self.o_proj = nn.Linear(dim, dim, bias=False)
    
    def forward(self, x: torch.Tensor, mask: torch.Tensor = None):
        """
        前向传播
        """
        batch_size, seq_len, _ = x.shape
        
        # 投影
        q = self.q_proj(x)
        k = self.k_proj(x)
        v = self.v_proj(x)
        
        # 重塑
        q = q.view(batch_size, seq_len, self.n_heads, self.head_dim)
        k = k.view(batch_size, seq_len, self.n_groups, self.head_dim)
        v = v.view(batch_size, seq_len, self.n_groups, self.head_dim)
        
        # 使用einsum计算注意力分数
        # q: (batch, seq, n_heads, head_dim)
        # k: (batch, seq, n_groups, head_dim)
        # 我们需要将n_heads映射到n_groups
        
        # 方法1：显式扩展（简单但效率较低）
        # k_expanded = k.repeat_interleave(self.heads_per_group, dim=2)
        
        # 方法2：使用矩阵运算（更高效）
        # 将q按组重排
        q_grouped = q.view(batch_size, seq_len, self.n_groups, self.heads_per_group, self.head_dim)
        
        # 计算注意力分数
        # (batch, seq, n_groups, heads_per_group, head_dim) @ (batch, seq, n_groups, head_dim)
        # -> (batch, n_groups, heads_per_group, seq, seq)
        scores = torch.einsum('bsghd,bsgd->bghss', q_grouped, k) * self.scale
        
        if mask is not None:
            scores = scores.masked_fill(mask.unsqueeze(1).unsqueeze(2) == 0, float('-inf'))
        
        # Softmax
        attn = F.softmax(scores, dim=-1)
        
        # 计算输出
        # (batch, n_groups, heads_per_group, seq, seq) @ (batch, seq, n_groups, head_dim)
        # -> (batch, seq, n_groups, heads_per_group, head_dim)
        output = torch.einsum('bghss,bsgd->bsghd', attn, v)
        
        # 重塑回原始形状
        output = output.contiguous().view(batch_size, seq_len, self.dim)
        
        return self.o_proj(output)


class GQAWithKVCache(nn.Module):
    """
    带KV Cache的GQA
    
    用于推理加速
    """
    
    def __init__(self, dim: int, n_heads: int, n_groups: int, max_seq_len: int = 2048):
        super().__init__()
        
        self.dim = dim
        self.n_heads = n_heads
        self.n_groups = n_groups
        self.head_dim = dim // n_heads
        self.heads_per_group = n_heads // n_groups
        self.scale = self.head_dim ** -0.5
        self.max_seq_len = max_seq_len
        
        # 投影层
        self.q_proj = nn.Linear(dim, dim, bias=False)
        self.k_proj = nn.Linear(dim, n_groups * self.head_dim, bias=False)
        self.v_proj = nn.Linear(dim, n_groups * self.head_dim, bias=False)
        self.o_proj = nn.Linear(dim, dim, bias=False)
        
        # KV Cache（只需要n_groups个组）
        self.register_buffer(
            'k_cache',
            torch.zeros(1, n_groups, max_seq_len, self.head_dim)
        )
        self.register_buffer(
            'v_cache',
            torch.zeros(1, n_groups, max_seq_len, self.head_dim)
        )
        self.cache_len = 0
    
    def forward(self, x: torch.Tensor, use_cache: bool = True):
        """
        前向传播
        
        参数：
        - x: (batch, seq_len, dim)
        - use_cache: 是否使用KV Cache
        """
        batch_size, seq_len, _ = x.shape
        
        # 投影
        q = self.q_proj(x).view(batch_size, seq_len, self.n_heads, self.head_dim)
        k = self.k_proj(x).view(batch_size, seq_len, self.n_groups, self.head_dim)
        v = self.v_proj(x).view(batch_size, seq_len, self.n_groups, self.head_dim)
        
        if use_cache:
            # 更新KV Cache
            self.k_cache[:batch_size, :, self.cache_len:self.cache_len + seq_len, :] = k.transpose(1, 2)
            self.v_cache[:batch_size, :, self.cache_len:self.cache_len + seq_len, :] = v.transpose(1, 2)
            self.cache_len += seq_len
            
            # 使用完整的KV Cache
            k = self.k_cache[:batch_size, :, :self.cache_len, :].transpose(1, 2)
            v = self.v_cache[:batch_size, :, :self.cache_len, :].transpose(1, 2)
        
        # 扩展K、V
        k = k.repeat_interleave(self.heads_per_group, dim=2)  # 扩展头维度
        v = v.repeat_interleave(self.heads_per_group, dim=2)
        
        # 转置为注意力计算格式
        q = q.transpose(1, 2)  # (batch, n_heads, seq, head_dim)
        k = k.transpose(1, 2)  # (batch, n_heads, cache_len, head_dim)
        v = v.transpose(1, 2)
        
        # 计算注意力
        scores = torch.matmul(q, k.transpose(-2, -1)) * self.scale
        
        # 因果掩码
        if use_cache:
            # 生成模式：只需要最后一个位置
            pass
        else:
            # 预填充模式
            causal_mask = torch.triu(
                torch.ones(seq_len, seq_len, device=x.device, dtype=torch.bool),
                diagonal=1
            )
            scores = scores.masked_fill(causal_mask, float('-inf'))
        
        attn = F.softmax(scores, dim=-1)
        output = torch.matmul(attn, v)
        
        # 合并多头
        output = output.transpose(1, 2).contiguous().view(batch_size, seq_len, self.dim)
        
        return self.o_proj(output)
    
    def clear_cache(self):
        """清空KV Cache"""
        self.cache_len = 0
```

---

## 33. 模型评估与性能测试

### 33.1 语言模型评估指标

```python
"""
语言模型评估指标

1. 困惑度（Perplexity）
   - 衡量模型对文本的预测能力
   - PPL = exp(平均交叉熵损失)
   - 越低越好

2. BLEU分数
   - 用于机器翻译
   - 衡量生成文本与参考文本的n-gram重叠

3. ROUGE分数
   - 用于文本摘要
   - 衡量召回率

4. 准确率
   - 用于分类任务
   - 正确预测的比例

5. F1分数
   - 精确率和召回率的调和平均
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import List, Dict
import math
import numpy as np

class LMEvaluator:
    """
    语言模型评估器
    """
    
    def __init__(self, model, tokenizer, device='cuda'):
        """
        参数：
        - model: 语言模型
        - tokenizer: 分词器
        - device: 设备
        """
        self.model = model.to(device)
        self.model.eval()
        self.tokenizer = tokenizer
        self.device = device
    
    @torch.no_grad()
    def compute_perplexity(self, texts: List[str]) -> float:
        """
        计算困惑度
        
        困惑度定义：
        PPL = exp(-1/N × Σ log P(wᵢ|w<ᵢ))
        
        参数：
        - texts: 文本列表
        
        返回：
        - 困惑度
        """
        total_loss = 0.0
        total_tokens = 0
        
        for text in texts:
            # 编码
            input_ids = self.tokenizer.encode(text, return_tensors='pt').to(self.device)
            
            # 前向传播
            outputs = self.model(input_ids)
            logits = outputs.logits
            
            # 计算损失
            # 预测下一个token，所以标签是input_ids[:, 1:]
            shift_logits = logits[:, :-1, :].contiguous()
            shift_labels = input_ids[:, 1:].contiguous()
            
            loss = F.cross_entropy(
                shift_logits.view(-1, shift_logits.size(-1)),
                shift_labels.view(-1),
                reduction='sum'
            )
            
            total_loss += loss.item()
            total_tokens += shift_labels.numel()
        
        # 计算困惑度
        avg_loss = total_loss / total_tokens
        perplexity = math.exp(avg_loss)
        
        return perplexity
    
    @torch.no_grad()
    def compute_accuracy(self, texts: List[str]) -> float:
        """
        计算预测准确率
        
        参数：
        - texts: 文本列表
        
        返回：
        - 准确率
        """
        correct = 0
        total = 0
        
        for text in texts:
            input_ids = self.tokenizer.encode(text, return_tensors='pt').to(self.device)
            
            outputs = self.model(input_ids)
            logits = outputs.logits
            
            # 预测
            predictions = logits[:, :-1, :].argmax(dim=-1)
            labels = input_ids[:, 1:]
            
            correct += (predictions == labels).sum().item()
            total += labels.numel()
        
        return correct / total
    
    @torch.no_grad()
    def evaluate_generation(
        self,
        prompts: List[str],
        references: List[str],
        max_new_tokens: int = 100
    ) -> Dict[str, float]:
        """
        评估生成质量
        
        参数：
        - prompts: 提示列表
        - references: 参考答案列表
        - max_new_tokens: 最大生成token数
        
        返回：
        - 评估指标字典
        """
        generated_texts = []
        
        for prompt in prompts:
            # 生成
            input_ids = self.tokenizer.encode(prompt, return_tensors='pt').to(self.device)
            
            for _ in range(max_new_tokens):
                outputs = self.model(input_ids)
                next_token = outputs.logits[:, -1, :].argmax(dim=-1, keepdim=True)
                input_ids = torch.cat([input_ids, next_token], dim=-1)
                
                if next_token.item() == self.tokenizer.eos_token_id:
                    break
            
            generated = self.tokenizer.decode(input_ids[0], skip_special_tokens=True)
            generated_texts.append(generated)
        
        # 计算BLEU分数
        bleu_scores = [self._compute_bleu(gen, ref) for gen, ref in zip(generated_texts, references)]
        
        # 计算ROUGE分数
        rouge_scores = [self._compute_rouge(gen, ref) for gen, ref in zip(generated_texts, references)]
        
        return {
            'bleu': np.mean(bleu_scores),
            'rouge': np.mean(rouge_scores),
            'generated_texts': generated_texts
        }
    
    def _compute_bleu(self, generated: str, reference: str, n: int = 4) -> float:
        """
        计算BLEU分数
        
        简化版实现
        """
        gen_tokens = generated.split()
        ref_tokens = reference.split()
        
        if len(gen_tokens) == 0:
            return 0.0
        
        # 计算n-gram精确率
        scores = []
        for i in range(1, n + 1):
            gen_ngrams = self._get_ngrams(gen_tokens, i)
            ref_ngrams = self._get_ngrams(ref_tokens, i)
            
            if len(gen_ngrams) == 0:
                continue
            
            matches = sum(1 for ng in gen_ngrams if ng in ref_ngrams)
            precision = matches / len(gen_ngrams)
            scores.append(precision)
        
        if not scores:
            return 0.0
        
        # 简化的BLEU分数（不考虑brevity penalty）
        return np.exp(np.mean(np.log(scores))) if all(s > 0 for s in scores) else 0.0
    
    def _get_ngrams(self, tokens: List[str], n: int) -> List[tuple]:
        """获取n-gram"""
        return [tuple(tokens[i:i+n]) for i in range(len(tokens) - n + 1)]
    
    def _compute_rouge(self, generated: str, reference: str) -> float:
        """
        计算ROUGE-L分数
        
        基于最长公共子序列
        """
        gen_tokens = generated.split()
        ref_tokens = reference.split()
        
        # 计算LCS长度
        lcs_len = self._lcs_length(gen_tokens, ref_tokens)
        
        if len(gen_tokens) == 0 or len(ref_tokens) == 0:
            return 0.0
        
        # 计算精确率和召回率
        precision = lcs_len / len(gen_tokens)
        recall = lcs_len / len(ref_tokens)
        
        # F1分数
        if precision + recall == 0:
            return 0.0
        
        return 2 * precision * recall / (precision + recall)
    
    def _lcs_length(self, seq1: List, seq2: List) -> int:
        """计算最长公共子序列长度"""
        m, n = len(seq1), len(seq2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if seq1[i-1] == seq2[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                else:
                    dp[i][j] = max(dp[i-1][j], dp[i][j-1])
        
        return dp[m][n]


def benchmark_model(model, input_shape=(1, 512, 768), n_runs=100):
    """
    模型性能基准测试
    
    参数：
    - model: 模型
    - input_shape: 输入形状 (batch, seq_len, dim)
    - n_runs: 运行次数
    
    返回：
    - 性能指标字典
    """
    import time
    
    model = model.cuda()
    model.eval()
    
    # 创建输入
    x = torch.randn(*input_shape).cuda()
    
    # 预热
    for _ in range(10):
        with torch.no_grad():
            _ = model(x)
    
    torch.cuda.synchronize()
    
    # 测量推理时间
    times = []
    for _ in range(n_runs):
        torch.cuda.synchronize()
        start = time.time()
        with torch.no_grad():
            _ = model(x)
        torch.cuda.synchronize()
        times.append(time.time() - start)
    
    # 计算统计量
    times = np.array(times)
    
    # 计算显存使用
    torch.cuda.reset_peak_memory_stats()
    with torch.no_grad():
        _ = model(x)
    memory = torch.cuda.max_memory_allocated() / 1024**2  # MB
    
    return {
        'mean_time': times.mean(),
        'std_time': times.std(),
        'min_time': times.min(),
        'max_time': times.max(),
        'throughput': input_shape[0] / times.mean(),  # samples/sec
        'memory_mb': memory
    }
```

### 33.2 训练监控与可视化

```python
"""
训练监控与可视化

关键指标：
1. 训练损失
2. 验证损失
3. 学习率
4. 梯度范数
5. 激活值分布
"""

import matplotlib.pyplot as plt
from collections import defaultdict
import json

class TrainingMonitor:
    """
    训练监控器
    
    记录和可视化训练过程
    """
    
    def __init__(self, log_dir: str = 'logs'):
        """
        参数：
        - log_dir: 日志目录
        """
        self.log_dir = log_dir
        self.metrics = defaultdict(list)
        self.step = 0
    
    def log(self, metrics: Dict[str, float], step: int = None):
        """
        记录指标
        
        参数：
        - metrics: 指标字典
        - step: 步数（可选）
        """
        if step is not None:
            self.step = step
        
        for name, value in metrics.items():
            self.metrics[name].append((self.step, value))
        
        self.step += 1
    
    def plot(self, metric_names: List[str] = None, save_path: str = None):
        """
        绘制指标曲线
        
        参数：
        - metric_names: 要绘制的指标名称列表
        - save_path: 保存路径
        """
        if metric_names is None:
            metric_names = list(self.metrics.keys())
        
        n_metrics = len(metric_names)
        fig, axes = plt.subplots(n_metrics, 1, figsize=(10, 3 * n_metrics))
        
        if n_metrics == 1:
            axes = [axes]
        
        for ax, name in zip(axes, metric_names):
            if name not in self.metrics:
                continue
            
            steps, values = zip(*self.metrics[name])
            ax.plot(steps, values, linewidth=2)
            ax.set_xlabel('Step')
            ax.set_ylabel(name)
            ax.set_title(f'{name} over Training')
            ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150)
        
        plt.show()
    
    def save(self, path: str):
        """保存指标到文件"""
        data = {k: v for k, v in self.metrics.items()}
        with open(path, 'w') as f:
            json.dump(data, f)
    
    def load(self, path: str):
        """从文件加载指标"""
        with open(path, 'r') as f:
            data = json.load(f)
        self.metrics = defaultdict(list, data)


class GradientMonitor:
    """
    梯度监控器
    
    监控梯度流动，检测梯度消失/爆炸
    """
    
    def __init__(self, model):
        self.model = model
        self.gradient_stats = defaultdict(list)
    
    def capture(self):
        """捕获当前梯度统计"""
        for name, param in self.model.named_parameters():
            if param.grad is not None:
                grad = param.grad.data
                self.gradient_stats[name].append({
                    'mean': grad.mean().item(),
                    'std': grad.std().item(),
                    'max': grad.max().item(),
                    'min': grad.min().item(),
                    'norm': grad.norm().item()
                })
    
    def get_layer_gradient_norms(self) -> Dict[str, float]:
        """获取每层的梯度范数"""
        norms = {}
        for name, stats_list in self.gradient_stats.items():
            if stats_list:
                norms[name] = stats_list[-1]['norm']
        return norms
    
    def check_gradient_health(self) -> Dict[str, bool]:
        """
        检查梯度健康状况
        
        返回：
        - 健康状态字典
        """
        health = {}
        
        for name, stats_list in self.gradient_stats.items():
            if not stats_list:
                continue
            
            stats = stats_list[-1]
            norm = stats['norm']
            
            # 检查梯度消失（范数太小）
            if norm < 1e-7:
                health[name] = 'vanishing'
            # 检查梯度爆炸（范数太大）
            elif norm > 100:
                health[name] = 'exploding'
            else:
                health[name] = 'healthy'
        
        return health
    
    def plot_gradient_flow(self, save_path: str = None):
        """
        绘制梯度流动图
        
        显示每层的梯度范数
        """
        norms = self.get_layer_gradient_norms()
        
        if not norms:
            print("No gradient data available")
            return
        
        # 按层名排序
        layers = sorted(norms.keys())
        values = [norms[layer] for layer in layers]
        
        # 简化层名
        layer_names = [name.split('.')[-2] + '.' + name.split('.')[-1] for name in layers]
        
        plt.figure(figsize=(12, 6))
        plt.bar(range(len(values)), values)
        plt.xticks(range(len(layer_names)), layer_names, rotation=90, fontsize=8)
        plt.xlabel('Layer')
        plt.ylabel('Gradient Norm')
        plt.title('Gradient Flow Through Layers')
        plt.yscale('log')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150)
        
        plt.show()


class ActivationMonitor:
    """
    激活值监控器
    
    监控各层的激活值分布
    """
    
    def __init__(self):
        self.activations = {}
        self.handles = []
    
    def register_hooks(self, model):
        """注册前向钩子"""
        for name, module in model.named_modules():
            if isinstance(module, (nn.Linear, nn.LayerNorm, nn.ReLU, nn.GELU)):
                handle = module.register_forward_hook(
                    lambda m, i, o, n=name: self._hook_fn(n, o)
                )
                self.handles.append(handle)
    
    def _hook_fn(self, name, output):
        """钩子函数"""
        if isinstance(output, tuple):
            output = output[0]
        self.activations[name] = output.detach()
    
    def get_activation_stats(self) -> Dict[str, Dict]:
        """获取激活值统计"""
        stats = {}
        for name, activation in self.activations.items():
            stats[name] = {
                'mean': activation.mean().item(),
                'std': activation.std().item(),
                'max': activation.max().item(),
                'min': activation.min().item(),
                'sparsity': (activation == 0).float().mean().item()
            }
        return stats
    
    def plot_activation_distribution(self, layer_name: str, save_path: str = None):
        """绘制激活值分布"""
        if layer_name not in self.activations:
            print(f"Layer {layer_name} not found")
            return
        
        activation = self.activations[layer_name].cpu().flatten().numpy()
        
        plt.figure(figsize=(10, 5))
        plt.hist(activation, bins=100, density=True, alpha=0.7)
        plt.xlabel('Activation Value')
        plt.ylabel('Density')
        plt.title(f'Activation Distribution: {layer_name}')
        plt.grid(True, alpha=0.3)
        
        if save_path:
            plt.savefig(save_path, dpi=150)
        
        plt.show()
    
    def remove_hooks(self):
        """移除所有钩子"""
        for handle in self.handles:
            handle.remove()
        self.handles = []
```

---

## 34. 调试技巧与常见问题解决

### 34.1 常见训练问题与解决方案

```python
"""
训练大语言模型的常见问题与解决方案

1. 梯度消失/爆炸
2. 训练不稳定
3. 显存不足
4. 训练速度慢
5. 模型不收敛
"""

class TrainingDebugger:
    """
    训练调试工具集
    """
    
    @staticmethod
    def check_nan_inf(model, input_ids):
        """
        检查模型输出中的NaN和Inf
        
        参数：
        - model: 模型
        - input_ids: 输入token ID
        
        返回：
        - 是否存在NaN或Inf
        """
        with torch.no_grad():
            outputs = model(input_ids)
            logits = outputs.logits
            
            has_nan = torch.isnan(logits).any().item()
            has_inf = torch.isinf(logits).any().item()
            
            if has_nan:
                print("⚠️ 检测到NaN！")
                # 定位NaN位置
                nan_mask = torch.isnan(logits)
                nan_positions = torch.where(nan_mask)
                print(f"NaN位置: {nan_positions}")
            
            if has_inf:
                print("⚠️ 检测到Inf！")
                inf_mask = torch.isinf(logits)
                inf_positions = torch.where(inf_mask)
                print(f"Inf位置: {inf_positions}")
            
            return has_nan or has_inf
    
    @staticmethod
    def diagnose_gradient_issues(model):
        """
        诊断梯度问题
        
        返回：
        - 诊断报告
        """
        report = {
            'total_params': sum(p.numel() for p in model.parameters()),
            'trainable_params': sum(p.numel() for p in model.parameters() if p.requires_grad),
            'layers_with_no_grad': [],
            'layers_with_small_grad': [],
            'layers_with_large_grad': []
        }
        
        for name, param in model.named_parameters():
            if param.requires_grad:
                if param.grad is None:
                    report['layers_with_no_grad'].append(name)
                else:
                    grad_norm = param.grad.norm().item()
                    if grad_norm < 1e-7:
                        report['layers_with_small_grad'].append((name, grad_norm))
                    elif grad_norm > 10:
                        report['layers_with_large_grad'].append((name, grad_norm))
        
        return report
    
    @staticmethod
    def fix_gradient_issues(model, strategy='clip'):
        """
        修复梯度问题
        
        参数：
        - model: 模型
        - strategy: 修复策略 ('clip', 'norm', 'zero')
        """
        if strategy == 'clip':
            # 梯度裁剪
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        
        elif strategy == 'norm':
            # 梯度归一化
            total_norm = 0
            for p in model.parameters():
                if p.grad is not None:
                    total_norm += p.grad.data.norm() ** 2
            total_norm = total_norm ** 0.5
            
            for p in model.parameters():
                if p.grad is not None:
                    p.grad.data = p.grad.data / total_norm
        
        elif strategy == 'zero':
            # 将NaN/Inf梯度置零
            for p in model.parameters():
                if p.grad is not None:
                    p.grad.data[torch.isnan(p.grad.data)] = 0
                    p.grad.data[torch.isinf(p.grad.data)] = 0


def solve_common_issues():
    """
    常见问题解决方案汇总
    """
    
    solutions = {
        "梯度消失": {
            "症状": "训练损失不下降，梯度接近0",
            "原因": [
                "网络太深",
                "激活函数选择不当",
                "学习率太小"
            ],
            "解决方案": [
                "使用Pre-Norm代替Post-Norm",
                "使用残差连接",
                "使用GELU/SwiGLU激活函数",
                "增大学习率",
                "使用梯度裁剪"
            ]
        },
        
        "梯度爆炸": {
            "症状": "损失变为NaN，梯度非常大",
            "原因": [
                "学习率太大",
                "初始化不当",
                "数据异常"
            ],
            "解决方案": [
                "降低学习率",
                "使用梯度裁剪",
                "检查数据是否有异常值",
                "使用更好的初始化方法"
            ]
        },
        
        "显存不足": {
            "症状": "CUDA out of memory",
            "原因": [
                "batch size太大",
                "序列太长",
                "模型太大"
            ],
            "解决方案": [
                "减小batch size",
                "使用梯度累积",
                "使用混合精度训练",
                "使用Flash Attention",
                "使用梯度检查点",
                "使用模型并行"
            ]
        },
        
        "训练不稳定": {
            "症状": "损失震荡，不收敛",
            "原因": [
                "学习率调度不当",
                "batch size太小",
                "数据分布不均"
            ],
            "解决方案": [
                "使用学习率warmup",
                "增大batch size",
                "使用更好的优化器（如AdamW）",
                "使用权重衰减",
                "检查数据质量"
            ]
        }
    }
    
    return solutions


# 打印解决方案
def print_solutions():
    solutions = solve_common_issues()
    
    for issue, info in solutions.items():
        print(f"\n{'='*50}")
        print(f"问题: {issue}")
        print(f"{'='*50}")
        print(f"症状: {info['症状']}")
        print(f"\n原因:")
        for reason in info['原因']:
            print(f"  - {reason}")
        print(f"\n解决方案:")
        for solution in info['解决方案']:
            print(f"  - {solution}")


print_solutions()
```

### 34.2 性能优化技巧

```python
"""
性能优化技巧

1. 数据加载优化
2. 模型计算优化
3. 显存优化
4. 分布式优化
"""

class PerformanceOptimizer:
    """
    性能优化工具集
    """
    
    @staticmethod
    def optimize_dataloader(dataset, batch_size, num_workers=4, pin_memory=True):
        """
        优化数据加载器
        
        参数：
        - dataset: 数据集
        - batch_size: 批大小
        - num_workers: 工作进程数
        - pin_memory: 是否固定内存
        """
        from torch.utils.data import DataLoader
        
        return DataLoader(
            dataset,
            batch_size=batch_size,
            shuffle=True,
            num_workers=num_workers,
            pin_memory=pin_memory,
            prefetch_factor=2 if num_workers > 0 else None,
            persistent_workers=num_workers > 0
        )
    
    @staticmethod
    def enable_cudnn_benchmark():
        """
        启用cuDNN benchmark
        
        对于固定输入尺寸的模型，可以加速
        """
        torch.backends.cudnn.benchmark = True
        torch.backends.cudnn.deterministic = False
    
    @staticmethod
    def compile_model(model, mode='reduce-overhead'):
        """
        使用PyTorch 2.0编译模型
        
        参数：
        - model: 模型
        - mode: 编译模式
        """
        return torch.compile(model, mode=mode)
    
    @staticmethod
    def profile_model(model, input_ids, n_runs=10):
        """
        性能分析
        
        找出性能瓶颈
        """
        import time
        
        model = model.cuda()
        model.eval()
        input_ids = input_ids.cuda()
        
        # 预热
        for _ in range(5):
            with torch.no_grad():
                _ = model(input_ids)
        
        torch.cuda.synchronize()
        
        # 使用PyTorch profiler
        with torch.profiler.profile(
            activities=[
                torch.profiler.ProfilerActivity.CPU,
                torch.profiler.ProfilerActivity.CUDA,
            ],
            record_shapes=True,
            profile_memory=True,
            with_stack=True
        ) as prof:
            for _ in range(n_runs):
                with torch.no_grad():
                    _ = model(input_ids)
        
        # 打印结果
        print(prof.key_averages().table(sort_by="cuda_time_total", row_limit=20))
        
        return prof


def memory_optimization_tips():
    """
    显存优化技巧
    """
    tips = """
    显存优化技巧：
    
    1. 混合精度训练
       - 使用torch.cuda.amp
       - 减少约50%显存
   
    2. 梯度累积
       - 模拟大batch size
       - 减少显存峰值
   
    3. 梯度检查点
       - 以计算换存储
       - 减少约30%显存
   
    4. Flash Attention
       - 减少注意力计算的显存
       - 支持更长序列
   
    5. 模型量化
       - int8/int4量化
       - 减少模型大小
   
    6. KV Cache优化
       - GQA/MQA
       - Paged Attention
   
    7. 数据类型
       - 使用bfloat16代替float32
       - 减少一半显存
   
    8. 清理缓存
       - torch.cuda.empty_cache()
       - gc.collect()
    """
    return tips


print(memory_optimization_tips())
```

---

## 35. Transformer Decoder完整架构解析

### 35.1 Decoder-Only架构详解

```python
"""
Decoder-Only Transformer架构

MiniMind采用Decoder-Only架构，这是现代大语言模型的主流选择。

Decoder-Only vs Encoder-Decoder：

Encoder-Decoder（如T5、BART）：
- Encoder：双向注意力，看到完整输入
- Decoder：单向注意力，自回归生成
- 适用：翻译、摘要等seq2seq任务

Decoder-Only（如GPT、LLaMA、MiniMind）：
- 只有Decoder，单向注意力
- 自回归生成
- 适用：文本生成、对话

为什么Decoder-Only成为主流？
1. 架构简单，易于扩展
2. 预训练目标简单（下一个token预测）
3. 零样本/少样本能力强
4. 推理效率高
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import math
from typing import Optional, Tuple
from dataclasses import dataclass


@dataclass
class ModelConfig:
    """模型配置"""
    dim: int = 512
    n_layers: int = 8
    n_heads: int = 8
    vocab_size: int = 6400
    max_seq_len: int = 512
    dropout: float = 0.0
    multiple_of: int = 64
    n_experts: int = 0
    use_moe: bool = False


class TransformerBlock(nn.Module):
    """
    Transformer Decoder块
    
    结构：
    x -> Norm -> Attention -> + -> Norm -> FFN -> + -> output
    |________________________|     |_______________|
    
    特点：
    1. Pre-Norm：归一化在子层之前
    2. 残差连接：保持梯度流动
    3. RMSNorm：比LayerNorm更高效
    """
    
    def __init__(self, config: ModelConfig, layer_idx: int):
        super().__init__()
        
        self.layer_idx = layer_idx
        
        # 注意力层归一化
        self.attention_norm = RMSNorm(config.dim)
        
        # 注意力层
        self.attention = Attention(
            dim=config.dim,
            n_heads=config.n_heads,
            max_seq_len=config.max_seq_len,
            dropout=config.dropout
        )
        
        # FFN层归一化
        self.ffn_norm = RMSNorm(config.dim)
        
        # FFN层
        if config.use_moe:
            self.ffn = MoEFFN(
                dim=config.dim,
                hidden_dim=config.dim * 4,
                n_experts=config.n_experts,
                top_k=2
            )
        else:
            self.ffn = FeedForward(
                dim=config.dim,
                hidden_dim=config.dim * 4,
                multiple_of=config.multiple_of,
                dropout=config.dropout
            )
    
    def forward(
        self,
        x: torch.Tensor,
        mask: Optional[torch.Tensor] = None,
        past_key_value: Optional[Tuple[torch.Tensor, torch.Tensor]] = None,
        use_cache: bool = False
    ) -> Tuple[torch.Tensor, Optional[Tuple[torch.Tensor, torch.Tensor]]]:
        """
        前向传播
        
        参数：
        - x: (batch, seq_len, dim)
        - mask: 注意力掩码
        - past_key_value: KV缓存
        - use_cache: 是否使用缓存
        
        返回：
        - output: 输出张量
        - present_key_value: 更新后的KV缓存
        """
        # 注意力块
        residual = x
        x = self.attention_norm(x)
        x, present_key_value = self.attention(
            x, mask, past_key_value, use_cache
        )
        x = residual + x
        
        # FFN块
        residual = x
        x = self.ffn_norm(x)
        x = self.ffn(x)
        x = residual + x
        
        return x, present_key_value


class Attention(nn.Module):
    """
    多头自注意力层
    
    支持特性：
    1. GQA（分组查询注意力）
    2. KV Cache
    3. Flash Attention
    4. RoPE位置编码
    """
    
    def __init__(
        self,
        dim: int,
        n_heads: int,
        max_seq_len: int = 512,
        n_groups: int = None,
        dropout: float = 0.0
    ):
        super().__init__()
        
        self.dim = dim
        self.n_heads = n_heads
        self.n_groups = n_groups if n_groups else n_heads
        self.head_dim = dim // n_heads
        self.heads_per_group = n_heads // self.n_groups
        self.scale = self.head_dim ** -0.5
        self.max_seq_len = max_seq_len
        
        # Q投影（n_heads个头）
        self.q_proj = nn.Linear(dim, dim, bias=False)
        
        # K、V投影（n_groups个组）
        self.k_proj = nn.Linear(dim, self.n_groups * self.head_dim, bias=False)
        self.v_proj = nn.Linear(dim, self.n_groups * self.head_dim, bias=False)
        
        # 输出投影
        self.o_proj = nn.Linear(dim, dim, bias=False)
        
        # RoPE位置编码
        self.rope = RoPE(self.head_dim, max_seq_len)
        
        # Dropout
        self.dropout = nn.Dropout(dropout)
    
    def forward(
        self,
        x: torch.Tensor,
        mask: Optional[torch.Tensor] = None,
        past_key_value: Optional[Tuple[torch.Tensor, torch.Tensor]] = None,
        use_cache: bool = False
    ) -> Tuple[torch.Tensor, Optional[Tuple[torch.Tensor, torch.Tensor]]]:
        """
        前向传播
        
        参数：
        - x: (batch, seq_len, dim)
        - mask: 注意力掩码
        - past_key_value: KV缓存
        - use_cache: 是否使用缓存
        """
        batch_size, seq_len, _ = x.shape
        
        # 投影
        q = self.q_proj(x)
        k = self.k_proj(x)
        v = self.v_proj(x)
        
        # 重塑为多头
        q = q.view(batch_size, seq_len, self.n_heads, self.head_dim)
        k = k.view(batch_size, seq_len, self.n_groups, self.head_dim)
        v = v.view(batch_size, seq_len, self.n_groups, self.head_dim)
        
        # 应用RoPE位置编码
        q = self.rope(q)
        k = self.rope(k)
        
        # 转置为注意力计算格式
        q = q.transpose(1, 2)  # (batch, n_heads, seq, head_dim)
        k = k.transpose(1, 2)  # (batch, n_groups, seq, head_dim)
        v = v.transpose(1, 2)
        
        # KV Cache处理
        if use_cache and past_key_value is not None:
            past_k, past_v = past_key_value
            k = torch.cat([past_k, k], dim=2)
            v = torch.cat([past_v, v], dim=2)
        
        present_key_value = (k, v) if use_cache else None
        
        # 扩展K、V以匹配Q的头数（GQA）
        k = k.repeat_interleave(self.heads_per_group, dim=1)
        v = v.repeat_interleave(self.heads_per_group, dim=1)
        
        # 计算注意力分数
        scores = torch.matmul(q, k.transpose(-2, -1)) * self.scale
        
        # 应用因果掩码
        if mask is None:
            # 创建因果掩码
            kv_len = k.shape[2]
            causal_mask = torch.triu(
                torch.ones(seq_len, kv_len, device=x.device, dtype=torch.bool),
                diagonal=kv_len - seq_len + 1
            )
            scores = scores.masked_fill(causal_mask, float('-inf'))
        else:
            scores = scores.masked_fill(mask == 0, float('-inf'))
        
        # Softmax
        attn = F.softmax(scores, dim=-1)
        attn = self.dropout(attn)
        
        # 计算输出
        output = torch.matmul(attn, v)
        
        # 合并多头
        output = output.transpose(1, 2).contiguous().view(batch_size, seq_len, self.dim)
        
        # 输出投影
        output = self.o_proj(output)
        
        return output, present_key_value


class MiniMindModel(nn.Module):
    """
    MiniMind完整模型
    
    架构：
    Token Embedding -> Position Embedding (RoPE)
    -> [Transformer Block] × n_layers
    -> Final Norm -> LM Head
    
    这是标准的Decoder-Only语言模型架构
    """
    
    def __init__(self, config: ModelConfig):
        super().__init__()
        
        self.config = config
        
        # Token嵌入
        self.tok_embeddings = nn.Embedding(config.vocab_size, config.dim)
        
        # Transformer层
        self.layers = nn.ModuleList([
            TransformerBlock(config, i) for i in range(config.n_layers)
        ])
        
        # 最终归一化
        self.norm = RMSNorm(config.dim)
        
        # 语言模型头
        self.output = nn.Linear(config.dim, config.vocab_size, bias=False)
        
        # 权重绑定（可选）
        # self.output.weight = self.tok_embeddings.weight
        
        # 初始化权重
        self.apply(self._init_weights)
        
        # 计算参数量
        self.n_params = sum(p.numel() for p in self.parameters())
    
    def _init_weights(self, module):
        """初始化权重"""
        if isinstance(module, nn.Linear):
            # 使用正态分布初始化
            torch.nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if module.bias is not None:
                torch.nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            torch.nn.init.normal_(module.weight, mean=0.0, std=0.02)
    
    def forward(
        self,
        input_ids: torch.Tensor,
        past_key_values: Optional[Tuple] = None,
        use_cache: bool = False
    ) -> Tuple[torch.Tensor, Optional[Tuple]]:
        """
        前向传播
        
        参数：
        - input_ids: (batch, seq_len) token ID
        - past_key_values: KV缓存列表
        - use_cache: 是否使用缓存
        
        返回：
        - logits: (batch, seq_len, vocab_size)
        - present_key_values: 更新后的KV缓存
        """
        batch_size, seq_len = input_ids.shape
        
        # Token嵌入
        x = self.tok_embeddings(input_ids)  # (batch, seq_len, dim)
        
        # 初始化KV缓存
        if past_key_values is None:
            past_key_values = [None] * self.config.n_layers
        
        present_key_values = []
        
        # 通过所有Transformer层
        for i, layer in enumerate(self.layers):
            x, present_kv = layer(
                x,
                past_key_value=past_key_values[i],
                use_cache=use_cache
            )
            present_key_values.append(present_kv)
        
        # 最终归一化
        x = self.norm(x)
        
        # 语言模型头
        logits = self.output(x)  # (batch, seq_len, vocab_size)
        
        return logits, present_key_values if use_cache else None
    
    def count_parameters(self) -> dict:
        """统计参数量"""
        total = sum(p.numel() for p in self.parameters())
        trainable = sum(p.numel() for p in self.parameters() if p.requires_grad)
        
        # 按模块统计
        embedding_params = sum(p.numel() for p in self.tok_embeddings.parameters())
        attention_params = sum(
            sum(p.numel() for p in layer.attention.parameters())
            for layer in self.layers
        )
        ffn_params = sum(
            sum(p.numel() for p in layer.ffn.parameters())
            for layer in self.layers
        )
        output_params = sum(p.numel() for p in self.output.parameters())
        
        return {
            'total': total,
            'trainable': trainable,
            'embedding': embedding_params,
            'attention': attention_params,
            'ffn': ffn_params,
            'output': output_params,
            'total_mb': total * 4 / 1024 / 1024  # float32
        }


# 创建模型示例
def create_minimind_model():
    """创建MiniMind模型"""
    config = ModelConfig(
        dim=512,
        n_layers=8,
        n_heads=8,
        vocab_size=6400,
        max_seq_len=512
    )
    
    model = MiniMindModel(config)
    
    print(f"模型参数量: {model.n_params:,}")
    print(f"模型大小: {model.n_params * 4 / 1024 / 1024:.2f} MB (float32)")
    
    return model


# 运行示例
model = create_minimind_model()
```

### 35.2 模型前向传播详解

```python
"""
模型前向传播的完整流程

让我们逐步分析数据如何流过模型
"""

def detailed_forward_pass():
    """
    详细的前向传播分析
    """
    # 配置
    batch_size = 2
    seq_len = 16
    dim = 512
    n_heads = 8
    vocab_size = 6400
    
    # 创建输入
    input_ids = torch.randint(0, vocab_size, (batch_size, seq_len))
    print(f"输入形状: {input_ids.shape}")
    print(f"输入内容示例: {input_ids[0, :5]}")
    
    # 创建模型
    config = ModelConfig(dim=dim, n_heads=n_heads, vocab_size=vocab_size)
    model = MiniMindModel(config)
    
    # 前向传播
    with torch.no_grad():
        logits, _ = model(input_ids)
    
    print(f"\n输出形状: {logits.shape}")
    print(f"输出logits范围: [{logits.min():.2f}, {logits.max():.2f}]")
    
    # 获取预测
    predictions = logits.argmax(dim=-1)
    print(f"预测token: {predictions[0, :5]}")
    
    # 计算损失
    labels = input_ids[:, 1:]  # 下一个token预测
    shift_logits = logits[:, :-1, :]
    
    loss = F.cross_entropy(
        shift_logits.reshape(-1, vocab_size),
        labels.reshape(-1)
    )
    print(f"\n交叉熵损失: {loss.item():.4f}")
    print(f"困惑度: {torch.exp(loss).item():.2f}")


# 运行详细分析
detailed_forward_pass()
```

---

## 36. Embedding层详解

### 36.1 Token Embedding原理

```python
"""
Embedding层详解

Embedding是将离散的token ID映射为连续向量的过程

数学表示：
E = Embedding(token_id)
其中 E ∈ R^d，d是嵌入维度

Embedding矩阵：
W_emb ∈ R^(vocab_size × dim)
每个token对应矩阵的一行

为什么需要Embedding？
1. 将离散符号转为连续向量
2. 语义相似的token有相似的向量
3. 可以学习token之间的关系
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import math


class TokenEmbedding(nn.Module):
    """
    Token Embedding层
    
    将token ID映射为向量
    """
    
    def __init__(self, vocab_size: int, dim: int, padding_idx: int = None):
        """
        参数：
        - vocab_size: 词表大小
        - dim: 嵌入维度
        - padding_idx: padding token的索引（可选）
        """
        super().__init__()
        
        self.vocab_size = vocab_size
        self.dim = dim
        
        # Embedding矩阵
        self.embedding = nn.Embedding(
            num_embeddings=vocab_size,
            embedding_dim=dim,
            padding_idx=padding_idx
        )
        
        # 初始化
        self._init_weights()
    
    def _init_weights(self):
        """初始化Embedding权重"""
        # 使用正态分布初始化
        nn.init.normal_(self.embedding.weight, mean=0.0, std=0.02)
        
        # 如果有padding_idx，将其初始化为0
        if self.embedding.padding_idx is not None:
            self.embedding.weight.data[self.embedding.padding_idx].zero_()
    
    def forward(self, input_ids: torch.Tensor) -> torch.Tensor:
        """
        前向传播
        
        参数：
        - input_ids: (batch, seq_len) token ID
        
        返回：
        - embeddings: (batch, seq_len, dim) 嵌入向量
        """
        return self.embedding(input_ids)
    
    def get_embedding(self, token_id: int) -> torch.Tensor:
        """获取单个token的嵌入"""
        return self.embedding.weight[token_id]
    
    def get_similarity(self, token_id1: int, token_id2: int) -> float:
        """计算两个token的相似度"""
        emb1 = self.get_embedding(token_id1)
        emb2 = self.get_embedding(token_id2)
        
        similarity = F.cosine_similarity(emb1.unsqueeze(0), emb2.unsqueeze(0))
        return similarity.item()


class PositionalEmbedding(nn.Module):
    """
    可学习的位置编码
    
    与RoPE不同，这是直接学习的位置向量
    
    优点：
    - 简单直观
    - 可以学习任意位置表示
    
    缺点：
    - 无法外推到训练长度之外
    - 需要额外参数
    """
    
    def __init__(self, max_seq_len: int, dim: int):
        super().__init__()
        
        self.max_seq_len = max_seq_len
        self.dim = dim
        
        # 位置嵌入矩阵
        self.pos_embedding = nn.Embedding(max_seq_len, dim)
        
        # 初始化
        nn.init.normal_(self.pos_embedding.weight, mean=0.0, std=0.02)
    
    def forward(self, seq_len: int) -> torch.Tensor:
        """
        获取位置编码
        
        参数：
        - seq_len: 序列长度
        
        返回：
        - pos_emb: (seq_len, dim)
        """
        positions = torch.arange(seq_len, device=self.pos_embedding.weight.device)
        return self.pos_embedding(positions)


class SinusoidalPositionalEmbedding(nn.Module):
    """
    正弦位置编码（原始Transformer）
    
    公式：
    PE(pos, 2i) = sin(pos / 10000^(2i/d))
    PE(pos, 2i+1) = cos(pos / 10000^(2i/d))
    
    特点：
    - 不需要学习
    - 可以外推
    - 相对位置信息
    """
    
    def __init__(self, max_seq_len: int, dim: int):
        super().__init__()
        
        self.max_seq_len = max_seq_len
        self.dim = dim
        
        # 预计算位置编码
        pe = torch.zeros(max_seq_len, dim)
        position = torch.arange(0, max_seq_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(
            torch.arange(0, dim, 2).float() * (-math.log(10000.0) / dim)
        )
        
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        
        # 注册为buffer（不参与训练）
        self.register_buffer('pe', pe)
    
    def forward(self, seq_len: int) -> torch.Tensor:
        """获取位置编码"""
        return self.pe[:seq_len]


class CombinedEmbedding(nn.Module):
    """
    组合Embedding
    
    Token Embedding + Position Embedding
    """
    
    def __init__(
        self,
        vocab_size: int,
        dim: int,
        max_seq_len: int,
        pos_embedding_type: str = 'rope'
    ):
        """
        参数：
        - vocab_size: 词表大小
        - dim: 嵌入维度
        - max_seq_len: 最大序列长度
        - pos_embedding_type: 位置编码类型 ('rope', 'learned', 'sinusoidal')
        """
        super().__init__()
        
        self.dim = dim
        self.pos_embedding_type = pos_embedding_type
        
        # Token Embedding
        self.tok_embedding = TokenEmbedding(vocab_size, dim)
        
        # Position Embedding（如果使用）
        if pos_embedding_type == 'learned':
            self.pos_embedding = PositionalEmbedding(max_seq_len, dim)
        elif pos_embedding_type == 'sinusoidal':
            self.pos_embedding = SinusoidalPositionalEmbedding(max_seq_len, dim)
        else:
            # RoPE在注意力层中应用
            self.pos_embedding = None
    
    def forward(self, input_ids: torch.Tensor) -> torch.Tensor:
        """
        前向传播
        
        参数：
        - input_ids: (batch, seq_len)
        
        返回：
        - embeddings: (batch, seq_len, dim)
        """
        # Token Embedding
        x = self.tok_embedding(input_ids)
        
        # 添加Position Embedding
        if self.pos_embedding is not None:
            seq_len = input_ids.shape[1]
            pos_emb = self.pos_embedding(seq_len)
            x = x + pos_emb
        
        return x


def analyze_embedding():
    """
    分析Embedding层
    """
    vocab_size = 6400
    dim = 512
    batch_size = 4
    seq_len = 32
    
    # 创建Embedding层
    embedding = TokenEmbedding(vocab_size, dim)
    
    # 创建输入
    input_ids = torch.randint(0, vocab_size, (batch_size, seq_len))
    
    # 获取嵌入
    embeddings = embedding(input_ids)
    
    print(f"输入形状: {input_ids.shape}")
    print(f"输出形状: {embeddings.shape}")
    print(f"Embedding矩阵形状: {embedding.embedding.weight.shape}")
    
    # 分析嵌入向量
    print(f"\n嵌入向量统计:")
    print(f"  均值: {embeddings.mean().item():.4f}")
    print(f"  标准差: {embeddings.std().item():.4f}")
    print(f"  最小值: {embeddings.min().item():.4f}")
    print(f"  最大值: {embeddings.max().item():.4f}")
    
    # 计算参数量
    params = vocab_size * dim
    print(f"\nEmbedding参数量: {params:,}")
    print(f"Embedding大小: {params * 4 / 1024 / 1024:.2f} MB (float32)")


# 运行分析
analyze_embedding()
```

### 36.2 Embedding权重分析

```python
"""
Embedding权重分析

分析训练好的Embedding可以揭示token之间的关系
"""

def analyze_embedding_weights(model):
    """
    分析Embedding权重
    
    参数：
    - model: 训练好的模型
    """
    # 获取Embedding权重
    embedding_weight = model.tok_embeddings.embedding.weight
    
    # 计算每个token的嵌入范数
    norms = torch.norm(embedding_weight, dim=1)
    
    print("Token嵌入范数统计:")
    print(f"  均值: {norms.mean().item():.4f}")
    print(f"  标准差: {norms.std().item():.4f}")
    print(f"  最小值: {norms.min().item():.4f}")
    print(f"  最大值: {norms.max().item():.4f}")
    
    # 找出范数最大和最小的token
    max_idx = norms.argmax().item()
    min_idx = norms.argmin().item()
    
    print(f"\n范数最大的token索引: {max_idx}, 范数: {norms[max_idx]:.4f}")
    print(f"范数最小的token索引: {min_idx}, 范数: {norms[min_idx]:.4f}")
    
    # 计算token之间的相似度矩阵
    similarity_matrix = F.cosine_similarity(
        embedding_weight.unsqueeze(1),
        embedding_weight.unsqueeze(0),
        dim=2
    )
    
    print(f"\n相似度矩阵形状: {similarity_matrix.shape}")
    
    # 找出最相似的token对（排除自身）
    similarity_matrix.fill_diagonal_(-1)  # 对角线设为-1
    most_similar = similarity_matrix.argmax()
    idx1, idx2 = most_similar // similarity_matrix.shape[0], most_similar % similarity_matrix.shape[0]
    
    print(f"最相似的token对: ({idx1}, {idx2}), 相似度: {similarity_matrix[idx1, idx2]:.4f}")
    
    return similarity_matrix


def visualize_embedding_pca(embedding_weight, n_tokens=100):
    """
    使用PCA可视化Embedding
    
    参数：
    - embedding_weight: Embedding权重
    - n_tokens: 可视化的token数量
    """
    from sklearn.decomposition import PCA
    import matplotlib.pyplot as plt
    
    # 选择前n_tokens个token
    embeddings = embedding_weight[:n_tokens].detach().cpu().numpy()
    
    # PCA降维
    pca = PCA(n_components=2)
    embeddings_2d = pca.fit_transform(embeddings)
    
    # 绘图
    plt.figure(figsize=(12, 8))
    plt.scatter(embeddings_2d[:, 0], embeddings_2d[:, 1], alpha=0.6)
    
    # 添加标签
    for i in range(n_tokens):
        plt.annotate(str(i), (embeddings_2d[i, 0], embeddings_2d[i, 1]), fontsize=8)
    
    plt.xlabel('PC1')
    plt.ylabel('PC2')
    plt.title('Token Embedding PCA Visualization')
    plt.grid(True, alpha=0.3)
    plt.savefig('embedding_pca.png', dpi=150)
    plt.show()
    
    print(f"PCA解释方差比: {pca.explained_variance_ratio_}")
```

---

## 37. 注意力掩码机制详解

### 37.1 因果掩码原理

```python
"""
注意力掩码机制详解

在Decoder-Only模型中，必须使用因果掩码（Causal Mask）

为什么需要因果掩码？
1. 自回归生成：只能看到之前的token
2. 防止信息泄露：不能看到未来的token
3. 训练效率：一次计算所有位置的预测

因果掩码的形式：
对于序列长度为4的情况：

位置:  0  1  2  3
    0 [1, 0, 0, 0]  位置0只能看到自己
    1 [1, 1, 0, 0]  位置1可以看到0,1
    2 [1, 1, 1, 0]  位置2可以看到0,1,2
    3 [1, 1, 1, 1]  位置3可以看到所有

其中1表示可以关注，0表示不能关注
"""

import torch
import torch.nn.functional as F


def create_causal_mask(seq_len: int, device: str = 'cpu') -> torch.Tensor:
    """
    创建因果掩码
    
    参数：
    - seq_len: 序列长度
    - device: 设备
    
    返回：
    - mask: (seq_len, seq_len) 下三角矩阵
    """
    # 创建下三角矩阵
    mask = torch.tril(torch.ones(seq_len, seq_len, device=device))
    return mask


def create_attention_mask(
    seq_len: int,
    kv_len: int = None,
    device: str = 'cpu'
) -> torch.Tensor:
    """
    创建注意力掩码（用于KV Cache场景）
    
    参数：
    - seq_len: 查询序列长度
    - kv_len: 键值序列长度（使用KV Cache时可能不同）
    - device: 设备
    
    返回：
    - mask: (seq_len, kv_len)
    """
    if kv_len is None:
        kv_len = seq_len
    
    # 创建因果掩码
    # 对于生成场景，seq_len=1，kv_len=缓存长度
    mask = torch.tril(
        torch.ones(seq_len, kv_len, device=device),
        diagonal=kv_len - seq_len
    )
    
    return mask


def apply_attention_mask(scores: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    """
    应用注意力掩码
    
    参数：
    - scores: (batch, heads, seq, kv) 注意力分数
    - mask: (seq, kv) 或 (batch, 1, seq, kv) 掩码
    
    返回：
    - masked_scores: 应用掩码后的分数
    """
    # 将掩码中为0的位置设为负无穷
    # 这样softmax后这些位置的概率为0
    return scores.masked_fill(mask == 0, float('-inf'))


class CausalMaskDemo:
    """
    因果掩码演示
    """
    
    @staticmethod
    def demo_mask():
        """演示因果掩码的效果"""
        seq_len = 6
        
        # 创建因果掩码
        mask = create_causal_mask(seq_len)
        
        print("因果掩码（1=可关注，0=不可关注）:")
        print(mask.int().numpy())
        
        # 模拟注意力分数
        scores = torch.randn(1, 1, seq_len, seq_len)
        
        print("\n原始注意力分数:")
        print(scores[0, 0].numpy())
        
        # 应用掩码
        masked_scores = apply_attention_mask(scores, mask)
        
        print("\n应用掩码后的分数:")
        print(masked_scores[0, 0].numpy())
        
        # Softmax
        attn_weights = F.softmax(masked_scores, dim=-1)
        
        print("\n注意力权重（Softmax后）:")
        print(attn_weights[0, 0].numpy())
        
        # 验证：每行和为1，上三角为0
        print("\n验证:")
        print(f"每行和: {attn_weights[0, 0].sum(dim=-1).numpy()}")
    
    @staticmethod
    def demo_kv_cache_mask():
        """演示KV Cache场景的掩码"""
        # 假设已经缓存了4个token，现在生成第5个
        kv_len = 5  # 缓存长度
        seq_len = 1  # 当前生成1个token
        
        mask = create_attention_mask(seq_len, kv_len)
        
        print(f"KV Cache场景掩码 (seq_len={seq_len}, kv_len={kv_len}):")
        print(mask.int().numpy())
        print("生成token可以看到所有缓存的token")


# 运行演示
CausalMaskDemo.demo_mask()
print("\n" + "="*50 + "\n")
CausalMaskDemo.demo_kv_cache_mask()
```

### 37.2 多种掩码类型

```python
"""
多种掩码类型

1. 因果掩码（Causal Mask）
   - 用于Decoder
   - 只能看到之前的token

2. Padding掩码（Padding Mask）
   - 处理变长序列
   - 忽略padding token

3. 组合掩码（Combined Mask）
   - 因果 + Padding
   - 同时处理两种情况
"""

def create_padding_mask(
    input_ids: torch.Tensor,
    pad_token_id: int = 0
) -> torch.Tensor:
    """
    创建Padding掩码
    
    参数：
    - input_ids: (batch, seq_len) token ID
    - pad_token_id: padding token的ID
    
    返回：
    - mask: (batch, 1, 1, seq_len) 1表示有效token
    """
    # padding位置为0，其他位置为1
    mask = (input_ids != pad_token_id).float()
    
    # 扩展维度以匹配注意力分数
    return mask.unsqueeze(1).unsqueeze(2)


def create_combined_mask(
    input_ids: torch.Tensor,
    pad_token_id: int = 0
) -> torch.Tensor:
    """
    创建组合掩码（因果 + Padding）
    
    参数：
    - input_ids: (batch, seq_len)
    - pad_token_id: padding token的ID
    
    返回：
    - mask: (batch, 1, seq_len, seq_len)
    """
    batch_size, seq_len = input_ids.shape
    
    # 创建因果掩码
    causal_mask = create_causal_mask(seq_len, input_ids.device)
    
    # 创建Padding掩码
    padding_mask = create_padding_mask(input_ids, pad_token_id)
    
    # 组合：两个掩码都为1的位置才为1
    # causal_mask: (seq_len, seq_len)
    # padding_mask: (batch, 1, 1, seq_len)
    combined_mask = causal_mask.unsqueeze(0).unsqueeze(0) * padding_mask
    
    return combined_mask


def create_sliding_window_mask(
    seq_len: int,
    window_size: int,
    device: str = 'cpu'
) -> torch.Tensor:
    """
    创建滑动窗口掩码
    
    每个位置只能看到窗口内的token
    
    参数：
    - seq_len: 序列长度
    - window_size: 窗口大小
    - device: 设备
    
    返回：
    - mask: (seq_len, seq_len)
    """
    # 创建因果掩码
    causal_mask = torch.tril(torch.ones(seq_len, seq_len, device=device))
    
    # 创建窗口掩码
    # 每行只有最后window_size个位置为1
    window_mask = torch.zeros(seq_len, seq_len, device=device)
    for i in range(seq_len):
        start = max(0, i - window_size + 1)
        window_mask[i, start:i+1] = 1
    
    # 组合
    return causal_mask * window_mask


def create_prefix_mask(
    seq_len: int,
    prefix_len: int,
    device: str = 'cpu'
) -> torch.Tensor:
    """
    创建前缀掩码
    
    前缀部分可以双向关注，生成部分只能单向
    
    用于Prefix-LM或指令微调
    
    参数：
    - seq_len: 序列长度
    - prefix_len: 前缀长度
    - device: 设备
    
    返回：
    - mask: (seq_len, seq_len)
    """
    mask = torch.zeros(seq_len, seq_len, device=device)
    
    # 前缀部分：双向注意力
    mask[:prefix_len, :prefix_len] = 1
    
    # 生成部分：因果注意力
    for i in range(prefix_len, seq_len):
        mask[i, :i+1] = 1
    
    return mask


class MaskVisualizer:
    """掩码可视化"""
    
    @staticmethod
    def visualize_all_masks(seq_len=8, window_size=4, prefix_len=3):
        """可视化所有类型的掩码"""
        import matplotlib.pyplot as plt
        
        fig, axes = plt.subplots(2, 2, figsize=(12, 12))
        
        # 因果掩码
        causal = create_causal_mask(seq_len)
        axes[0, 0].imshow(causal, cmap='Blues')
        axes[0, 0].set_title('Causal Mask')
        axes[0, 0].set_xlabel('Key Position')
        axes[0, 0].set_ylabel('Query Position')
        
        # 滑动窗口掩码
        sliding = create_sliding_window_mask(seq_len, window_size)
        axes[0, 1].imshow(sliding, cmap='Blues')
        axes[0, 1].set_title(f'Sliding Window Mask (window={window_size})')
        axes[0, 1].set_xlabel('Key Position')
        axes[0, 1].set_ylabel('Query Position')
        
        # 前缀掩码
        prefix = create_prefix_mask(seq_len, prefix_len)
        axes[1, 0].imshow(prefix, cmap='Blues')
        axes[1, 0].set_title(f'Prefix Mask (prefix={prefix_len})')
        axes[1, 0].set_xlabel('Key Position')
        axes[1, 0].set_ylabel('Query Position')
        
        # 随机掩码（稀疏注意力示例）
        random_mask = torch.rand(seq_len, seq_len) > 0.5
        random_mask = torch.tril(random_mask.float())
        axes[1, 1].imshow(random_mask, cmap='Blues')
        axes[1, 1].set_title('Random Sparse Mask')
        axes[1, 1].set_xlabel('Key Position')
        axes[1, 1].set_ylabel('Query Position')
        
        plt.tight_layout()
        plt.savefig('attention_masks.png', dpi=150)
        plt.show()


# 可视化
MaskVisualizer.visualize_all_masks()
```

---

## 38. 模型初始化策略

### 38.1 权重初始化方法

```python
"""
模型初始化策略

良好的初始化对训练至关重要

常见初始化方法：
1. 随机初始化
   - 正态分布
   - 均匀分布
   - Xavier/Glorot
   - Kaiming/He

2. 预训练初始化
   - 从头训练
   - 从检查点恢复
   - 迁移学习

3. 特殊初始化
   - 缩放初始化
   - 零初始化
"""

import torch
import torch.nn as nn
import math


class InitializationStrategies:
    """
    初始化策略集合
    """
    
    @staticmethod
    def normal_init(weight: torch.Tensor, mean: float = 0.0, std: float = 0.02):
        """
        正态分布初始化
        
        参数：
        - weight: 权重张量
        - mean: 均值
        - std: 标准差
        """
        nn.init.normal_(weight, mean=mean, std=std)
    
    @staticmethod
    def xavier_uniform_init(weight: torch.Tensor, gain: float = 1.0):
        """
        Xavier均匀初始化
        
        适用于tanh/sigmoid激活函数
        
        公式：a = gain × √(6 / (fan_in + fan_out))
        """
        nn.init.xavier_uniform_(weight, gain=gain)
    
    @staticmethod
    def xavier_normal_init(weight: torch.Tensor, gain: float = 1.0):
        """
        Xavier正态初始化
        
        公式：std = gain × √(2 / (fan_in + fan_out))
        """
        nn.init.xavier_normal_(weight, gain=gain)
    
    @staticmethod
    def kaiming_uniform_init(weight: torch.Tensor, mode: str = 'fan_in', nonlinearity: str = 'leaky_relu'):
        """
        Kaiming均匀初始化（He初始化）
        
        适用于ReLU/LeakyReLU激活函数
        
        公式：a = √(6 / fan_in) 或 √(6 / fan_out)
        """
        nn.init.kaiming_uniform_(weight, mode=mode, nonlinearity=nonlinearity)
    
    @staticmethod
    def kaiming_normal_init(weight: torch.Tensor, mode: str = 'fan_in', nonlinearity: str = 'leaky_relu'):
        """
        Kaiming正态初始化
        
        公式：std = √(2 / fan_in) 或 √(2 / fan_out)
        """
        nn.init.kaiming_normal_(weight, mode=mode, nonlinearity=nonlinearity)
    
    @staticmethod
    def small_init(weight: torch.Tensor, dim: int):
        """
        小值初始化
        
        用于Transformer的输出层
        
        公式：std = √(2 / (5 × dim))
        """
        std = math.sqrt(2 / (5 * dim))
        nn.init.normal_(weight, mean=0.0, std=std)
    
    @staticmethod
    def zeros_init(weight: torch.Tensor):
        """零初始化"""
        nn.init.zeros_(weight)
    
    @staticmethod
    def ones_init(weight: torch.Tensor):
        """一初始化"""
        nn.init.ones_(weight)


def init_transformer_weights(model: nn.Module, config):
    """
    Transformer模型初始化
    
    根据层的类型选择不同的初始化策略
    
    参数：
    - model: 模型
    - config: 配置
    """
    for name, module in model.named_modules():
        # Linear层
        if isinstance(module, nn.Linear):
            # 根据层的类型选择初始化
            if 'output' in name or 'lm_head' in name:
                # 输出层：小值初始化
                InitializationStrategies.small_init(module.weight, config.dim)
            elif any(x in name for x in ['q_proj', 'k_proj', 'v_proj', 'o_proj']):
                # 注意力投影：正态分布
                nn.init.normal_(module.weight, mean=0.0, std=0.02)
            elif any(x in name for x in ['w1', 'w2', 'w3']):
                # FFN：正态分布
                nn.init.normal_(module.weight, mean=0.0, std=0.02)
            else:
                # 其他Linear层
                nn.init.normal_(module.weight, mean=0.0, std=0.02)
            
            if module.bias is not None:
                nn.init.zeros_(module.bias)
        
        # Embedding层
        elif isinstance(module, nn.Embedding):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)
        
        # LayerNorm/RMSNorm
        elif isinstance(module, (nn.LayerNorm, RMSNorm)):
            if hasattr(module, 'weight') and module.weight is not None:
                nn.init.ones_(module.weight)
            if hasattr(module, 'bias') and module.bias is not None:
                nn.init.zeros_(module.bias)


def scaled_init(model: nn.Module, n_layers: int, std: float = 0.02):
    """
    缩放初始化
    
    对于深层网络，使用较小的初始化标准差
    
    公式：std_layer = std / √(2 × n_layers)
    
    这有助于稳定深层网络的训练
    """
    scaled_std = std / math.sqrt(2 * n_layers)
    
    for name, module in model.named_modules():
        if isinstance(module, nn.Linear):
            nn.init.normal_(module.weight, mean=0.0, std=scaled_std)
            if module.bias is not None:
                nn.init.zeros_(module.bias)


class WeightInitAnalyzer:
    """权重初始化分析器"""
    
    @staticmethod
    def analyze_model_weights(model: nn.Module):
        """分析模型权重分布"""
        stats = {}
        
        for name, param in model.named_parameters():
            if param.requires_grad:
                data = param.data
                stats[name] = {
                    'shape': tuple(data.shape),
                    'mean': data.mean().item(),
                    'std': data.std().item(),
                    'min': data.min().item(),
                    'max': data.max().item(),
                    'norm': torch.norm(data).item()
                }
        
        return stats
    
    @staticmethod
    def print_weight_stats(stats: dict):
        """打印权重统计"""
        print(f"{'Layer':<40} {'Shape':<20} {'Mean':>10} {'Std':>10} {'Norm':>10}")
        print("-" * 100)
        
        for name, s in stats.items():
            shape_str = str(s['shape'])
            print(f"{name:<40} {shape_str:<20} {s['mean']:>10.4f} {s['std']:>10.4f} {s['norm']:>10.2f}")


# 分析示例
def analyze_initialization():
    """分析模型初始化"""
    config = ModelConfig(dim=512, n_layers=8, n_heads=8, vocab_size=6400)
    model = MiniMindModel(config)
    
    # 分析权重
    stats = WeightInitAnalyzer.analyze_model_weights(model)
    WeightInitAnalyzer.print_weight_stats(stats)


# 运行分析
analyze_initialization()
```

### 38.2 初始化对训练的影响

```python
"""
初始化对训练的影响

不同的初始化会导致不同的训练动态
"""

def compare_initializations():
    """
    对比不同初始化的效果
    """
    import matplotlib.pyplot as plt
    
    dim = 256
    n_layers = 8
    
    # 创建模型
    class SimpleModel(nn.Module):
        def __init__(self):
            super().__init__()
            self.layers = nn.ModuleList([
                nn.Linear(dim, dim) for _ in range(n_layers)
            ])
        
        def forward(self, x):
            for layer in self.layers:
                x = layer(x)
            return x
    
    # 测试不同初始化
    init_methods = {
        'normal_0.02': lambda m: init_weights(m, 0.02),
        'normal_0.1': lambda m: init_weights(m, 0.1),
        'xavier': lambda m: init_xavier(m),
        'kaiming': lambda m: init_kaiming(m)
    }
    
    results = {}
    
    for name, init_fn in init_methods.items():
        model = SimpleModel()
        init_fn(model)
        
        # 前向传播
        x = torch.randn(1, dim)
        output = model(x)
        
        # 记录输出统计
        results[name] = {
            'output_mean': output.mean().item(),
            'output_std': output.std().item(),
            'output_max': output.max().item(),
            'output_min': output.min().item()
        }
    
    # 打印结果
    print("不同初始化的输出统计:")
    print(f"{'Method':<15} {'Mean':>10} {'Std':>10} {'Max':>10} {'Min':>10}")
    print("-" * 55)
    for name, stats in results.items():
        print(f"{name:<15} {stats['output_mean']:>10.4f} {stats['output_std']:>10.4f} "
              f"{stats['output_max']:>10.4f} {stats['output_min']:>10.4f}")


def init_weights(model, std):
    for p in model.parameters():
        nn.init.normal_(p, std=std)


def init_xavier(model):
    for p in model.parameters():
        if p.dim() >= 2:
            nn.init.xavier_uniform_(p)


def init_kaiming(model):
    for p in model.parameters():
        if p.dim() >= 2:
            nn.init.kaiming_normal_(p, mode='fan_in')


# 运行对比
compare_initializations()
```

---

## 39. 模型参数统计与分析

### 39.1 参数量计算

```python
"""
模型参数统计与分析

了解模型参数分布有助于：
1. 估计显存需求
2. 优化模型结构
3. 分析计算瓶颈
"""

import torch
import torch.nn as nn
from typing import Dict, List, Tuple
from collections import defaultdict


class ParameterAnalyzer:
    """
    参数分析器
    """
    
    def __init__(self, model: nn.Module):
        self.model = model
        self.analysis = self._analyze()
    
    def _analyze(self) -> Dict:
        """分析模型参数"""
        total_params = 0
        trainable_params = 0
        
        # 按模块分类
        module_params = defaultdict(lambda: {'total': 0, 'trainable': 0, 'params': []})
        
        # 按类型分类
        type_params = defaultdict(lambda: {'total': 0, 'count': 0})
        
        for name, param in self.model.named_parameters():
            num_params = param.numel()
            total_params += num_params
            
            if param.requires_grad:
                trainable_params += num_params
            
            # 模块分类
            module_name = name.split('.')[0]
            module_params[module_name]['total'] += num_params
            module_params[module_name]['params'].append({
                'name': name,
                'shape': tuple(param.shape),
                'numel': num_params,
                'trainable': param.requires_grad
            })
            
            if param.requires_grad:
                module_params[module_name]['trainable'] += num_params
            
            # 类型分类
            param_type = str(param.dtype)
            type_params[param_type]['total'] += num_params
            type_params[param_type]['count'] += 1
        
        return {
            'total_params': total_params,
            'trainable_params': trainable_params,
            'frozen_params': total_params - trainable_params,
            'module_params': dict(module_params),
            'type_params': dict(type_params),
            'memory_mb': total_params * 4 / 1024 / 1024,  # float32
            'memory_mb_fp16': total_params * 2 / 1024 / 1024  # float16
        }
    
    def summary(self) -> str:
        """生成参数摘要"""
        a = self.analysis
        
        summary = f"""
模型参数统计
{'='*60}
总参数量: {a['total_params']:,}
可训练参数: {a['trainable_params']:,}
冻结参数: {a['frozen_params']:,}

显存占用 (float32): {a['memory_mb']:.2f} MB
显存占用 (float16): {a['memory_mb_fp16']:.2f} MB

按模块分类:
{'-'*60}
"""
        
        for module_name, stats in a['module_params'].items():
            summary += f"  {module_name}: {stats['total']:,} ({stats['total']/a['total_params']*100:.1f}%)\n"
        
        summary += f"\n按数据类型分类:\n{'-'*60}\n"
        for dtype, stats in a['type_params'].items():
            summary += f"  {dtype}: {stats['total']:,} ({stats['count']} 个张量)\n"
        
        return summary
    
    def detailed_report(self) -> str:
        """生成详细报告"""
        report = "详细参数报告\n" + "="*80 + "\n"
        
        for module_name, stats in self.analysis['module_params'].items():
            report += f"\n模块: {module_name}\n{'-'*40}\n"
            
            for p in stats['params']:
                shape_str = str(p['shape'])
                trainable_str = "✓" if p['trainable'] else "✗"
                report += f"  {p['name']:<50} {shape_str:<20} {p['numel']:>12,} {trainable_str}\n"
        
        return report
    
    def get_layer_param_counts(self) -> Dict[str, int]:
        """获取每层的参数量"""
        counts = {}
        
        for name, param in self.model.named_parameters():
            layer_name = '.'.join(name.split('.')[:3])  # 取前3层
            if layer_name not in counts:
                counts[layer_name] = 0
            counts[layer_name] += param.numel()
        
        return counts
    
    def estimate_training_memory(self, batch_size: int, seq_len: int) -> Dict[str, float]:
        """
        估计训练时的显存占用
        
        参数：
        - batch_size: 批大小
        - seq_len: 序列长度
        
        返回：
        - 各部分显存估计
        """
        a = self.analysis
        
        # 模型参数
        model_memory = a['memory_mb_fp16']
        
        # 梯度（与参数相同大小）
        gradient_memory = model_memory
        
        # 优化器状态（Adam: 2倍参数）
        optimizer_memory = model_memory * 2
        
        # 激活值（粗略估计）
        # 每层的激活值约为 batch_size × seq_len × dim
        dim = 512  # 假设
        n_layers = 8  # 假设
        activation_memory = batch_size * seq_len * dim * n_layers * 2 / 1024 / 1024
        
        # 总计
        total = model_memory + gradient_memory + optimizer_memory + activation_memory
        
        return {
            'model_mb': model_memory,
            'gradient_mb': gradient_memory,
            'optimizer_mb': optimizer_memory,
            'activation_mb': activation_memory,
            'total_mb': total
        }


def analyze_minimind():
    """分析MiniMind模型"""
    config = ModelConfig(
        dim=512,
        n_layers=8,
        n_heads=8,
        vocab_size=6400,
        max_seq_len=512
    )
    
    model = MiniMindModel(config)
    
    # 分析参数
    analyzer = ParameterAnalyzer(model)
    
    # 打印摘要
    print(analyzer.summary())
    
    # 估计训练显存
    memory = analyzer.estimate_training_memory(batch_size=32, seq_len=512)
    
    print("\n训练显存估计 (batch=32, seq=512):")
    print(f"  模型参数: {memory['model_mb']:.2f} MB")
    print(f"  梯度: {memory['gradient_mb']:.2f} MB")
    print(f"  优化器状态: {memory['optimizer_mb']:.2f} MB")
    print(f"  激活值: {memory['activation_mb']:.2f} MB")
    print(f"  总计: {memory['total_mb']:.2f} MB")


# 运行分析
analyze_minimind()
```

### 39.2 参数分布可视化

```python
"""
参数分布可视化
"""

def visualize_param_distribution(model: nn.Module):
    """可视化参数分布"""
    import matplotlib.pyplot as plt
    
    # 收集不同层的权重
    attention_weights = []
    ffn_weights = []
    embedding_weights = []
    
    for name, param in model.named_parameters():
        if 'attention' in name and 'weight' in name:
            attention_weights.append(param.data.flatten())
        elif 'ffn' in name and 'weight' in name:
            ffn_weights.append(param.data.flatten())
        elif 'embedding' in name and 'weight' in name:
            embedding_weights.append(param.data.flatten())
    
    # 合并
    attention_weights = torch.cat(attention_weights).cpu().numpy()
    ffn_weights = torch.cat(ffn_weights).cpu().numpy()
    embedding_weights = torch.cat(embedding_weights).cpu().numpy()
    
    # 绘图
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    
    axes[0].hist(attention_weights, bins=100, density=True, alpha=0.7, color='blue')
    axes[0].set_title('Attention Weights')
    axes[0].set_xlabel('Value')
    axes[0].set_ylabel('Density')
    
    axes[1].hist(ffn_weights, bins=100, density=True, alpha=0.7, color='green')
    axes[1].set_title('FFN Weights')
    axes[1].set_xlabel('Value')
    
    axes[2].hist(embedding_weights, bins=100, density=True, alpha=0.7, color='red')
    axes[2].set_title('Embedding Weights')
    axes[2].set_xlabel('Value')
    
    plt.tight_layout()
    plt.savefig('param_distribution.png', dpi=150)
    plt.show()


def visualize_layer_norms(model: nn.Module):
    """可视化每层的权重范数"""
    import matplotlib.pyplot as plt
    
    layer_norms = {}
    
    for name, param in model.named_parameters():
        if 'weight' in name and param.dim() >= 2:
            layer_name = '.'.join(name.split('.')[:3])
            if layer_name not in layer_norms:
                layer_norms[layer_name] = []
            layer_norms[layer_name].append(torch.norm(param).item())
    
    # 计算每层的平均范数
    layers = list(layer_norms.keys())
    norms = [sum(layer_norms[l]) / len(layer_norms[l]) for l in layers]
    
    # 绘图
    plt.figure(figsize=(12, 6))
    plt.bar(range(len(layers)), norms)
    plt.xticks(range(len(layers)), [l[:20] for l in layers], rotation=90, fontsize=8)
    plt.xlabel('Layer')
    plt.ylabel('Weight Norm')
    plt.title('Weight Norm by Layer')
    plt.tight_layout()
    plt.savefig('layer_norms.png', dpi=150)
    plt.show()
```

---

## 40. 模型配置系统详解

### 40.1 配置类设计

```python
"""
模型配置系统详解

配置系统是管理模型超参数的关键

设计原则：
1. 可读性：配置清晰易懂
2. 可复现：配置可以保存和加载
3. 可扩展：易于添加新参数
4. 类型安全：使用类型注解
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
import json
import yaml


@dataclass
class AttentionConfig:
    """注意力配置"""
    n_heads: int = 8
    n_groups: int = 8  # GQA组数，等于n_heads时为MHA
    head_dim: int = 64
    dropout: float = 0.0
    use_flash: bool = True
    use_rope: bool = True
    rope_base: float = 10000.0


@dataclass
class FFNConfig:
    """前馈网络配置"""
    hidden_dim_multiplier: float = 4.0  # hidden_dim = dim * multiplier
    multiple_of: int = 64  # hidden_dim对齐到这个数的倍数
    dropout: float = 0.0
    use_swiglu: bool = True  # 使用SwiGLU还是标准FFN


@dataclass
class MoEConfig:
    """混合专家配置"""
    use_moe: bool = False
    n_experts: int = 8
    top_k: int = 2
    shared_experts: int = 0
    aux_loss_alpha: float = 0.1


@dataclass
class TrainingConfig:
    """训练配置"""
    batch_size: int = 32
    learning_rate: float = 5e-4
    weight_decay: float = 0.1
    warmup_steps: int = 100
    max_grad_norm: float = 1.0
    accumulation_steps: int = 1
    use_amp: bool = True
    seed: int = 42


@dataclass
class LMConfig:
    """
    完整的语言模型配置
    
    包含模型、训练的所有超参数
    """
    # 基础配置
    dim: int = 512
    n_layers: int = 8
    vocab_size: int = 6400
    max_seq_len: int = 512
    
    # 子配置
    attention: AttentionConfig = field(default_factory=AttentionConfig)
    ffn: FFNConfig = field(default_factory=FFNConfig)
    moe: MoEConfig = field(default_factory=MoEConfig)
    training: TrainingConfig = field(default_factory=TrainingConfig)
    
    # 其他配置
    dropout: float = 0.0
    tie_word_embeddings: bool = False
    use_cache: bool = True
    
    @property
    def head_dim(self) -> int:
        """计算每个头的维度"""
        return self.dim // self.attention.n_heads
    
    @property
    def hidden_dim(self) -> int:
        """计算FFN隐藏维度"""
        hidden = int(self.dim * self.ffn.hidden_dim_multiplier)
        # 对齐到multiple_of的倍数
        hidden = self.ffn.multiple_of * ((hidden + self.ffn.multiple_of - 1) // self.ffn.multiple_of)
        return hidden
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    def to_json(self, path: str):
        """保存为JSON"""
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def from_json(cls, path: str) -> 'LMConfig':
        """从JSON加载"""
        with open(path, 'r') as f:
            data = json.load(f)
        return cls(**data)
    
    def to_yaml(self, path: str):
        """保存为YAML"""
        with open(path, 'w') as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False)
    
    @classmethod
    def from_yaml(cls, path: str) -> 'LMConfig':
        """从YAML加载"""
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        return cls(**data)
    
    def __str__(self) -> str:
        """格式化输出"""
        lines = ["LMConfig:"]
        lines.append(f"  dim: {self.dim}")
        lines.append(f"  n_layers: {self.n_layers}")
        lines.append(f"  vocab_size: {self.vocab_size}")
        lines.append(f"  max_seq_len: {self.max_seq_len}")
        lines.append(f"  head_dim: {self.head_dim}")
        lines.append(f"  hidden_dim: {self.hidden_dim}")
        lines.append(f"  attention: n_heads={self.attention.n_heads}, n_groups={self.attention.n_groups}")
        lines.append(f"  ffn: hidden_dim={self.hidden_dim}, use_swiglu={self.ffn.use_swiglu}")
        lines.append(f"  moe: use_moe={self.moe.use_moe}, n_experts={self.moe.n_experts}")
        return '\n'.join(lines)


# 预定义配置
def get_small_config() -> LMConfig:
    """小型配置（适合测试）"""
    return LMConfig(
        dim=256,
        n_layers=4,
        vocab_size=1000,
        max_seq_len=128,
        attention=AttentionConfig(n_heads=4),
        training=TrainingConfig(batch_size=8)
    )


def get_base_config() -> LMConfig:
    """基础配置"""
    return LMConfig(
        dim=512,
        n_layers=8,
        vocab_size=6400,
        max_seq_len=512,
        attention=AttentionConfig(n_heads=8),
        training=TrainingConfig(batch_size=32)
    )


def get_large_config() -> LMConfig:
    """大型配置"""
    return LMConfig(
        dim=1024,
        n_layers=16,
        vocab_size=32000,
        max_seq_len=1024,
        attention=AttentionConfig(n_heads=16, n_groups=4),  # GQA
        training=TrainingConfig(batch_size=16)
    )


def get_moe_config() -> LMConfig:
    """MoE配置"""
    config = get_base_config()
    config.moe = MoEConfig(
        use_moe=True,
        n_experts=8,
        top_k=2
    )
    return config


# 配置示例
def demo_config():
    """演示配置系统"""
    # 创建配置
    config = get_base_config()
    
    print(config)
    
    # 保存配置
    config.to_json('config.json')
    config.to_yaml('config.yaml')
    
    # 加载配置
    loaded_config = LMConfig.from_json('config.json')
    
    print(f"\n加载的配置:")
    print(loaded_config)
    
    # 计算模型大小
    n_params = config.vocab_size * config.dim  # Embedding
    n_params += config.n_layers * (
        # Attention
        4 * config.dim * config.dim +
        # FFN
        3 * config.dim * config.hidden_dim
    )
    n_params += config.dim * config.vocab_size  # Output
    
    print(f"\n估计参数量: {n_params:,}")
    print(f"估计模型大小: {n_params * 2 / 1024 / 1024:.2f} MB (float16)")


# 运行演示
demo_config()
```

### 40.2 配置验证与更新

```python
"""
配置验证与动态更新
"""

class ConfigValidator:
    """配置验证器"""
    
    @staticmethod
    def validate(config: LMConfig) -> List[str]:
        """
        验证配置的有效性
        
        返回：
        - 错误消息列表（空列表表示有效）
        """
        errors = []
        
        # 检查维度
        if config.dim <= 0:
            errors.append(f"dim must be positive, got {config.dim}")
        
        if config.dim % config.attention.n_heads != 0:
            errors.append(
                f"dim ({config.dim}) must be divisible by n_heads ({config.attention.n_heads})"
            )
        
        # 检查头数
        if config.attention.n_heads <= 0:
            errors.append(f"n_heads must be positive, got {config.attention.n_heads}")
        
        if config.attention.n_heads % config.attention.n_groups != 0:
            errors.append(
                f"n_heads ({config.attention.n_heads}) must be divisible by n_groups ({config.attention.n_groups})"
            )
        
        # 检查层数
        if config.n_layers <= 0:
            errors.append(f"n_layers must be positive, got {config.n_layers}")
        
        # 检查词表大小
        if config.vocab_size <= 0:
            errors.append(f"vocab_size must be positive, got {config.vocab_size}")
        
        # 检查序列长度
        if config.max_seq_len <= 0:
            errors.append(f"max_seq_len must be positive, got {config.max_seq_len}")
        
        # 检查MoE配置
        if config.moe.use_moe:
            if config.moe.n_experts <= 0:
                errors.append(f"n_experts must be positive when using MoE")
            if config.moe.top_k <= 0 or config.moe.top_k > config.moe.n_experts:
                errors.append(f"top_k must be between 1 and n_experts")
        
        return errors
    
    @staticmethod
    def validate_or_raise(config: LMConfig):
        """验证配置，无效则抛出异常"""
        errors = ConfigValidator.validate(config)
        if errors:
            raise ValueError(f"Invalid config:\n" + "\n".join(f"  - {e}" for e in errors))


class ConfigUpdater:
    """配置更新器"""
    
    @staticmethod
    def scale_config(config: LMConfig, scale_factor: float) -> LMConfig:
        """
        按比例缩放配置
        
        用于快速创建不同大小的模型
        
        参数：
        - config: 原始配置
        - scale_factor: 缩放因子
        
        返回：
        - 新配置
        """
        import copy
        new_config = copy.deepcopy(config)
        
        # 缩放维度
        new_config.dim = int(config.dim * scale_factor)
        
        # 确保dim能被n_heads整除
        new_config.dim = (new_config.dim // config.attention.n_heads) * config.attention.n_heads
        
        return new_config
    
    @staticmethod
    def adjust_for_gpu(config: LMConfig, gpu_memory_gb: float) -> LMConfig:
        """
        根据GPU显存调整配置
        
        参数：
        - config: 原始配置
        - gpu_memory_gb: GPU显存大小（GB）
        
        返回：
        - 调整后的配置
        """
        import copy
        new_config = copy.deepcopy(config)
        
        # 粗略估计：每GB显存可以支持约10M参数
        max_params = int(gpu_memory_gb * 10e6)
        
        # 计算当前参数量
        current_params = ConfigUpdater._estimate_params(config)
        
        if current_params > max_params:
            # 需要缩小
            scale = (max_params / current_params) ** 0.5
            new_config.dim = int(config.dim * scale)
            new_config.n_layers = max(1, int(config.n_layers * scale))
        
        return new_config
    
    @staticmethod
    def _estimate_params(config: LMConfig) -> int:
        """估计参数量"""
        # Embedding
        params = config.vocab_size * config.dim
        
        # 每层
        params += config.n_layers * (
            4 * config.dim * config.dim +  # Attention
            3 * config.dim * config.hidden_dim  # FFN
        )
        
        # Output
        params += config.dim * config.vocab_size
        
        return params


# 验证示例
def validate_config_demo():
    """演示配置验证"""
    # 创建有效配置
    config = get_base_config()
    errors = ConfigValidator.validate(config)
    print(f"有效配置验证: {errors if errors else '通过'}")
    
    # 创建无效配置
    invalid_config = LMConfig(
        dim=100,  # 不能被n_heads整除
        n_layers=0,  # 无效
        vocab_size=-1  # 无效
    )
    errors = ConfigValidator.validate(invalid_config)
    print(f"\n无效配置验证:")
    for e in errors:
        print(f"  - {e}")


# 运行演示
validate_config_demo()
```

---

## 41. 完整训练项目实践

### 41.1 从零开始训练MiniMind

```python
"""
完整训练项目：从零开始训练MiniMind

本项目将带你完成：
1. 数据准备
2. 模型构建
3. 训练循环
4. 损失监控
5. 模型保存
6. 推理测试

这是一个完整的、可运行的训练脚本
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from torch.cuda.amp import GradScaler, autocast
import math
import os
import json
import time
from tqdm import tqdm
from dataclasses import dataclass
from typing import Optional, Tuple, List
import matplotlib.pyplot as plt


# ==================== 配置 ====================

@dataclass
class TrainConfig:
    """训练配置"""
    # 模型配置
    dim: int = 512
    n_layers: int = 8
    n_heads: int = 8
    vocab_size: int = 6400
    max_seq_len: int = 512
    
    # 训练配置
    batch_size: int = 16
    learning_rate: float = 3e-4
    weight_decay: float = 0.1
    warmup_steps: int = 100
    max_grad_norm: float = 1.0
    accumulation_steps: int = 4
    
    # 运行配置
    epochs: int = 3
    save_steps: int = 500
    eval_steps: int = 100
    log_steps: int = 10
    
    # 路径配置
    data_path: str = "data/train.txt"
    output_dir: str = "outputs"
    device: str = "cuda"
    
    # 混合精度
    use_amp: bool = True


# ==================== 数据集 ====================

class TextDataset(Dataset):
    """
    文本数据集
    
    将文本文件转换为训练样本
    """
    
    def __init__(
        self,
        file_path: str,
        tokenizer,
        max_seq_len: int = 512,
        overlap: int = 50
    ):
        """
        参数：
        - file_path: 文本文件路径
        - tokenizer: 分词器
        - max_seq_len: 最大序列长度
        - overlap: 重叠长度（用于增加数据量）
        """
        self.tokenizer = tokenizer
        self.max_seq_len = max_seq_len
        self.overlap = overlap
        
        # 读取并分词
        print(f"正在加载数据: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        # 分词
        self.token_ids = tokenizer.encode(text)
        print(f"总token数: {len(self.token_ids):,}")
        
        # 创建样本
        self.samples = self._create_samples()
        print(f"样本数: {len(self.samples):,}")
    
    def _create_samples(self) -> List[Tuple]:
        """创建训练样本"""
        samples = []
        stride = self.max_seq_len - self.overlap
        
        for i in range(0, len(self.token_ids) - self.max_seq_len, stride):
            chunk = self.token_ids[i:i + self.max_seq_len + 1]
            input_ids = chunk[:-1]
            labels = chunk[1:]
            samples.append((input_ids, labels))
        
        return samples
    
    def __len__(self):
        return len(self.samples)
    
    def __getitem__(self, idx):
        input_ids, labels = self.samples[idx]
        return {
            'input_ids': torch.tensor(input_ids, dtype=torch.long),
            'labels': torch.tensor(labels, dtype=torch.long)
        }


class SimpleTokenizer:
    """
    简单分词器
    
    基于字符级别的分词
    """
    
    def __init__(self, vocab_size: int = 6400):
        self.vocab_size = vocab_size
        self.char_to_id = {}
        self.id_to_char = {}
        
        # 特殊token
        self.pad_token = '<pad>'
        self.unk_token = '<unk>'
        self.bos_token = '<bos>'
        self.eos_token = '<eos>'
        
        self.pad_id = 0
        self.unk_id = 1
        self.bos_id = 2
        self.eos_id = 3
    
    def build_vocab(self, text: str):
        """构建词表"""
        chars = sorted(list(set(text)))
        
        # 特殊token
        special_tokens = [self.pad_token, self.unk_token, self.bos_token, self.eos_token]
        
        # 构建映射
        for i, token in enumerate(special_tokens):
            self.char_to_id[token] = i
            self.id_to_char[i] = token
        
        # 添加字符
        for i, char in enumerate(chars):
            idx = i + len(special_tokens)
            if idx < self.vocab_size:
                self.char_to_id[char] = idx
                self.id_to_char[idx] = char
        
        print(f"词表大小: {len(self.char_to_id)}")
    
    def encode(self, text: str) -> List[int]:
        """编码文本"""
        return [self.char_to_id.get(c, self.unk_id) for c in text]
    
    def decode(self, ids: List[int]) -> str:
        """解码token"""
        return ''.join([self.id_to_char.get(i, self.unk_token) for i in ids])
    
    def save(self, path: str):
        """保存词表"""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({
                'char_to_id': self.char_to_id,
                'id_to_char': {str(k): v for k, v in self.id_to_char.items()}
            }, f, ensure_ascii=False, indent=2)
    
    def load(self, path: str):
        """加载词表"""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.char_to_id = data['char_to_id']
        self.id_to_char = {int(k): v for k, v in data['id_to_char'].items()}


# ==================== 模型 ====================

class RMSNorm(nn.Module):
    """RMS归一化"""
    def __init__(self, dim: int, eps: float = 1e-6):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(dim))
        self.eps = eps
    
    def forward(self, x):
        return self.weight * x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + self.eps)


class RoPE(nn.Module):
    """旋转位置编码"""
    def __init__(self, dim: int, max_seq_len: int = 512, base: float = 10000.0):
        super().__init__()
        inv_freq = 1.0 / (base ** (torch.arange(0, dim, 2).float() / dim))
        self.register_buffer('inv_freq', inv_freq)
        
        # 预计算
        t = torch.arange(max_seq_len)
        freqs = torch.outer(t, inv_freq)
        emb = torch.cat([freqs, freqs], dim=-1)
        self.register_buffer('cos_cached', emb.cos())
        self.register_buffer('sin_cached', emb.sin())
    
    def forward(self, x, seq_len):
        cos = self.cos_cached[:seq_len].unsqueeze(0).unsqueeze(0)
        sin = self.sin_cached[:seq_len].unsqueeze(0).unsqueeze(0)
        
        x1, x2 = x[..., :x.shape[-1]//2], x[..., x.shape[-1]//2:]
        return torch.cat([x1 * cos[..., :x.shape[-1]//2] - x2 * sin[..., :x.shape[-1]//2],
                         x1 * sin[..., :x.shape[-1]//2] + x2 * cos[..., :x.shape[-1]//2]], dim=-1)


class Attention(nn.Module):
    """多头注意力"""
    def __init__(self, dim: int, n_heads: int, max_seq_len: int = 512):
        super().__init__()
        self.n_heads = n_heads
        self.head_dim = dim // n_heads
        self.scale = self.head_dim ** -0.5
        
        self.q_proj = nn.Linear(dim, dim, bias=False)
        self.k_proj = nn.Linear(dim, dim, bias=False)
        self.v_proj = nn.Linear(dim, dim, bias=False)
        self.o_proj = nn.Linear(dim, dim, bias=False)
        
        self.rope = RoPE(self.head_dim, max_seq_len)
    
    def forward(self, x, mask=None):
        B, S, D = x.shape
        
        q = self.q_proj(x).view(B, S, self.n_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(x).view(B, S, self.n_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(x).view(B, S, self.n_heads, self.head_dim).transpose(1, 2)
        
        q = self.rope(q, S)
        k = self.rope(k, S)
        
        scores = torch.matmul(q, k.transpose(-2, -1)) * self.scale
        
        if mask is None:
            mask = torch.triu(torch.ones(S, S, device=x.device), diagonal=1).bool()
            scores = scores.masked_fill(mask, float('-inf'))
        
        attn = F.softmax(scores, dim=-1)
        out = torch.matmul(attn, v)
        
        out = out.transpose(1, 2).contiguous().view(B, S, D)
        return self.o_proj(out)


class FeedForward(nn.Module):
    """SwiGLU前馈网络"""
    def __init__(self, dim: int, hidden_dim: int = None, multiple_of: int = 64):
        super().__init__()
        hidden_dim = hidden_dim or 4 * dim
        hidden_dim = multiple_of * ((hidden_dim + multiple_of - 1) // multiple_of)
        
        self.w1 = nn.Linear(dim, hidden_dim, bias=False)
        self.w2 = nn.Linear(hidden_dim, dim, bias=False)
        self.w3 = nn.Linear(dim, hidden_dim, bias=False)
    
    def forward(self, x):
        return self.w2(F.silu(self.w1(x)) * self.w3(x))


class TransformerBlock(nn.Module):
    """Transformer块"""
    def __init__(self, dim: int, n_heads: int, max_seq_len: int = 512):
        super().__init__()
        self.attention_norm = RMSNorm(dim)
        self.attention = Attention(dim, n_heads, max_seq_len)
        self.ffn_norm = RMSNorm(dim)
        self.ffn = FeedForward(dim)
    
    def forward(self, x):
        x = x + self.attention(self.attention_norm(x))
        x = x + self.ffn(self.ffn_norm(x))
        return x


class MiniMindForTraining(nn.Module):
    """MiniMind训练模型"""
    def __init__(self, config: TrainConfig):
        super().__init__()
        self.config = config
        
        self.tok_embeddings = nn.Embedding(config.vocab_size, config.dim)
        self.layers = nn.ModuleList([
            TransformerBlock(config.dim, config.n_heads, config.max_seq_len)
            for _ in range(config.n_layers)
        ])
        self.norm = RMSNorm(config.dim)
        self.output = nn.Linear(config.dim, config.vocab_size, bias=False)
        
        # 初始化
        self.apply(self._init_weights)
    
    def _init_weights(self, module):
        if isinstance(module, nn.Linear):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)
        elif isinstance(module, nn.Embedding):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)
    
    def forward(self, input_ids, labels=None):
        x = self.tok_embeddings(input_ids)
        
        for layer in self.layers:
            x = layer(x)
        
        x = self.norm(x)
        logits = self.output(x)
        
        loss = None
        if labels is not None:
            loss = F.cross_entropy(
                logits.view(-1, logits.size(-1)),
                labels.view(-1),
                ignore_index=0
            )
        
        return {'logits': logits, 'loss': loss}


# ==================== 训练器 ====================

class Trainer:
    """训练器"""
    
    def __init__(self, model, train_loader, val_loader, config: TrainConfig):
        self.model = model.to(config.device)
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.config = config
        
        # 优化器
        self.optimizer = torch.optim.AdamW(
            model.parameters(),
            lr=config.learning_rate,
            weight_decay=config.weight_decay,
            betas=(0.9, 0.95)
        )
        
        # 学习率调度
        self.scheduler = self._create_scheduler()
        
        # 混合精度
        self.scaler = GradScaler(enabled=config.use_amp)
        
        # 记录
        self.history = {
            'train_loss': [],
            'val_loss': [],
            'learning_rate': [],
            'perplexity': []
        }
        self.global_step = 0
        self.best_loss = float('inf')
        
        # 创建输出目录
        os.makedirs(config.output_dir, exist_ok=True)
    
    def _create_scheduler(self):
        """创建学习率调度器"""
        total_steps = self.config.epochs * len(self.train_loader)
        warmup_steps = self.config.warmup_steps
        
        def lr_lambda(step):
            if step < warmup_steps:
                return step / warmup_steps
            progress = (step - warmup_steps) / (total_steps - warmup_steps)
            return 0.5 * (1 + math.cos(math.pi * progress))
        
        return torch.optim.lr_scheduler.LambdaLR(self.optimizer, lr_lambda)
    
    def train(self):
        """完整训练流程"""
        print(f"\n开始训练")
        print(f"总步数: {self.config.epochs * len(self.train_loader)}")
        print(f"设备: {self.config.device}")
        print("="*60)
        
        for epoch in range(self.config.epochs):
            train_loss = self.train_epoch(epoch)
            val_loss = self.evaluate()
            
            # 记录
            self.history['train_loss'].append(train_loss)
            self.history['val_loss'].append(val_loss)
            
            print(f"\nEpoch {epoch}: train_loss={train_loss:.4f}, val_loss={val_loss:.4f}, ppl={math.exp(val_loss):.2f}")
            
            # 保存最佳模型
            if val_loss < self.best_loss:
                self.best_loss = val_loss
                self.save_checkpoint('best')
        
        # 绘制训练曲线
        self.plot_history()
        print("\n训练完成！")
    
    def train_epoch(self, epoch: int) -> float:
        """训练一个epoch"""
        self.model.train()
        total_loss = 0
        n_batches = 0
        
        pbar = tqdm(self.train_loader, desc=f'Epoch {epoch}')
        
        for batch_idx, batch in enumerate(pbar):
            input_ids = batch['input_ids'].to(self.config.device)
            labels = batch['labels'].to(self.config.device)
            
            # 混合精度前向传播
            with autocast(enabled=self.config.use_amp):
                outputs = self.model(input_ids, labels)
                loss = outputs['loss'] / self.config.accumulation_steps
            
            # 反向传播
            self.scaler.scale(loss).backward()
            
            # 梯度累积
            if (batch_idx + 1) % self.config.accumulation_steps == 0:
                # 梯度裁剪
                self.scaler.unscale_(self.optimizer)
                torch.nn.utils.clip_grad_norm_(
                    self.model.parameters(),
                    self.config.max_grad_norm
                )
                
                # 更新参数
                self.scaler.step(self.optimizer)
                self.scaler.update()
                self.optimizer.zero_grad(set_to_none=True)
                self.scheduler.step()
                
                self.global_step += 1
            
            # 记录损失
            total_loss += loss.item() * self.config.accumulation_steps
            n_batches += 1
            
            # 更新进度条
            current_lr = self.optimizer.param_groups[0]['lr']
            pbar.set_postfix({
                'loss': f'{loss.item() * self.config.accumulation_steps:.4f}',
                'lr': f'{current_lr:.2e}'
            })
            
            # 记录学习率
            self.history['learning_rate'].append(current_lr)
            
            # 定期评估
            if self.global_step % self.config.eval_steps == 0 and self.global_step > 0:
                val_loss = self.evaluate()
                self.history['val_loss'].append(val_loss)
                self.model.train()
        
        return total_loss / n_batches
    
    @torch.no_grad()
    def evaluate(self) -> float:
        """评估"""
        self.model.eval()
        total_loss = 0
        n_batches = 0
        
        for batch in self.val_loader:
            input_ids = batch['input_ids'].to(self.config.device)
            labels = batch['labels'].to(self.config.device)
            
            with autocast(enabled=self.config.use_amp):
                outputs = self.model(input_ids, labels)
            
            total_loss += outputs['loss'].item()
            n_batches += 1
        
        return total_loss / n_batches
    
    def save_checkpoint(self, name: str):
        """保存检查点"""
        path = os.path.join(self.config.output_dir, f'{name}.pt')
        torch.save({
            'model': self.model.state_dict(),
            'optimizer': self.optimizer.state_dict(),
            'scheduler': self.scheduler.state_dict(),
            'scaler': self.scaler.state_dict(),
            'global_step': self.global_step,
            'best_loss': self.best_loss,
            'config': self.config.__dict__
        }, path)
        print(f"保存检查点: {path}")
    
    def load_checkpoint(self, path: str):
        """加载检查点"""
        checkpoint = torch.load(path, map_location=self.config.device)
        self.model.load_state_dict(checkpoint['model'])
        self.optimizer.load_state_dict(checkpoint['optimizer'])
        self.scheduler.load_state_dict(checkpoint['scheduler'])
        self.scaler.load_state_dict(checkpoint['scaler'])
        self.global_step = checkpoint['global_step']
        self.best_loss = checkpoint['best_loss']
        print(f"加载检查点: {path}")
    
    def plot_history(self):
        """绘制训练曲线"""
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        
        # 训练损失
        axes[0, 0].plot(self.history['train_loss'])
        axes[0, 0].set_title('Training Loss')
        axes[0, 0].set_xlabel('Epoch')
        axes[0, 0].set_ylabel('Loss')
        axes[0, 0].grid(True, alpha=0.3)
        
        # 验证损失
        axes[0, 1].plot(self.history['val_loss'])
        axes[0, 1].set_title('Validation Loss')
        axes[0, 1].set_xlabel('Step')
        axes[0, 1].set_ylabel('Loss')
        axes[0, 1].grid(True, alpha=0.3)
        
        # 学习率
        axes[1, 0].plot(self.history['learning_rate'])
        axes[1, 0].set_title('Learning Rate')
        axes[1, 0].set_xlabel('Step')
        axes[1, 0].set_ylabel('LR')
        axes[1, 0].grid(True, alpha=0.3)
        
        # 困惑度
        perplexity = [math.exp(l) for l in self.history['val_loss']]
        axes[1, 1].plot(perplexity)
        axes[1, 1].set_title('Perplexity')
        axes[1, 1].set_xlabel('Epoch')
        axes[1, 1].set_ylabel('PPL')
        axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.config.output_dir, 'training_history.png'), dpi=150)
        plt.show()


# ==================== 主函数 ====================

def main():
    """主训练函数"""
    # 配置
    config = TrainConfig(
        dim=256,
        n_layers=4,
        n_heads=4,
        vocab_size=6400,
        max_seq_len=256,
        batch_size=8,
        epochs=3,
        learning_rate=3e-4,
        output_dir='outputs/minimind'
    )
    
    print("配置:")
    print(config)
    
    # 创建分词器
    tokenizer = SimpleTokenizer(config.vocab_size)
    
    # 构建词表（如果有数据）
    if os.path.exists(config.data_path):
        with open(config.data_path, 'r', encoding='utf-8') as f:
            text = f.read()
        tokenizer.build_vocab(text)
        tokenizer.save(os.path.join(config.output_dir, 'tokenizer.json'))
        
        # 创建数据集
        full_dataset = TextDataset(config.data_path, tokenizer, config.max_seq_len)
        
        # 分割数据集
        train_size = int(0.9 * len(full_dataset))
        val_size = len(full_dataset) - train_size
        train_dataset, val_dataset = torch.utils.data.random_split(
            full_dataset, [train_size, val_size]
        )
        
        train_loader = DataLoader(train_dataset, batch_size=config.batch_size, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=config.batch_size)
        
        # 创建模型
        model = MiniMindForTraining(config)
        n_params = sum(p.numel() for p in model.parameters())
        print(f"\n模型参数量: {n_params:,}")
        
        # 创建训练器
        trainer = Trainer(model, train_loader, val_loader, config)
        
        # 开始训练
        trainer.train()
    else:
        print(f"\n数据文件不存在: {config.data_path}")
        print("请创建数据文件或修改配置中的data_path")


if __name__ == '__main__':
    main()
```

### 41.2 交互式训练监控面板

```python
"""
交互式训练监控面板

实时监控训练过程，包括：
1. 损失曲线
2. 学习率变化
3. 梯度统计
4. 显存使用
"""

import torch
import torch.nn as nn
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from collections import deque
import time
import psutil
import threading


class TrainingMonitor:
    """
    实时训练监控器
    
    使用方法：
    monitor = TrainingMonitor()
    
    # 在训练循环中
    for batch in dataloader:
        loss = train_step(batch)
        monitor.update(loss.item())
    """
    
    def __init__(
        self,
        window_size: int = 100,
        update_interval: float = 0.5
    ):
        """
        参数：
        - window_size: 滑动窗口大小
        - update_interval: 更新间隔（秒）
        """
        self.window_size = window_size
        self.update_interval = update_interval
        
        # 数据存储
        self.losses = deque(maxlen=window_size)
        self.learning_rates = deque(maxlen=window_size)
        self.gradient_norms = deque(maxlen=window_size)
        self.memory_usage = deque(maxlen=window_size)
        self.timestamps = deque(maxlen=window_size)
        
        # 统计
        self.epoch_losses = []
        self.best_loss = float('inf')
        self.total_steps = 0
        
        # 初始化图形
        self._init_plot()
    
    def _init_plot(self):
        """初始化图形"""
        plt.style.use('dark_background')
        self.fig, self.axes = plt.subplots(2, 2, figsize=(14, 10))
        self.fig.suptitle('Training Monitor', fontsize=14, fontweight='bold')
        
        # 损失曲线
        self.ax_loss = self.axes[0, 0]
        self.ax_loss.set_title('Training Loss')
        self.ax_loss.set_xlabel('Step')
        self.ax_loss.set_ylabel('Loss')
        self.line_loss, = self.ax_loss.plot([], [], 'c-', linewidth=2)
        self.ax_loss.grid(True, alpha=0.3)
        
        # 学习率曲线
        self.ax_lr = self.axes[0, 1]
        self.ax_lr.set_title('Learning Rate')
        self.ax_lr.set_xlabel('Step')
        self.ax_lr.set_ylabel('LR')
        self.line_lr, = self.ax_lr.plot([], [], 'g-', linewidth=2)
        self.ax_lr.grid(True, alpha=0.3)
        
        # 梯度范数
        self.ax_grad = self.axes[1, 0]
        self.ax_grad.set_title('Gradient Norm')
        self.ax_grad.set_xlabel('Step')
        self.ax_grad.set_ylabel('Norm')
        self.line_grad, = self.ax_grad.plot([], [], 'm-', linewidth=2)
        self.ax_grad.grid(True, alpha=0.3)
        
        # 显存使用
        self.ax_mem = self.axes[1, 1]
        self.ax_mem.set_title('GPU Memory Usage')
        self.ax_mem.set_xlabel('Step')
        self.ax_mem.set_ylabel('Memory (GB)')
        self.line_mem, = self.ax_mem.plot([], [], 'y-', linewidth=2)
        self.ax_mem.grid(True, alpha=0.3)
        
        plt.tight_layout()
    
    def update(
        self,
        loss: float,
        learning_rate: float = None,
        model: nn.Module = None
    ):
        """
        更新监控数据
        
        参数：
        - loss: 当前损失
        - learning_rate: 当前学习率
        - model: 模型（用于计算梯度范数）
        """
        self.total_steps += 1
        current_time = time.time()
        
        # 记录损失
        self.losses.append(loss)
        self.timestamps.append(current_time)
        
        # 记录学习率
        if learning_rate is not None:
            self.learning_rates.append(learning_rate)
        
        # 计算梯度范数
        if model is not None:
            grad_norm = 0.0
            for p in model.parameters():
                if p.grad is not None:
                    grad_norm += p.grad.data.norm().item() ** 2
            grad_norm = grad_norm ** 0.5
            self.gradient_norms.append(grad_norm)
        
        # 记录显存
        if torch.cuda.is_available():
            memory = torch.cuda.max_memory_allocated() / 1024**3
            self.memory_usage.append(memory)
        
        # 更新最佳损失
        if loss < self.best_loss:
            self.best_loss = loss
    
    def update_plot(self):
        """更新图形"""
        steps = list(range(len(self.losses)))
        
        # 更新损失曲线
        if self.losses:
            self.line_loss.set_data(steps, list(self.losses))
            self.ax_loss.relim()
            self.ax_loss.autoscale_view()
        
        # 更新学习率曲线
        if self.learning_rates:
            self.line_lr.set_data(steps[-len(self.learning_rates):], list(self.learning_rates))
            self.ax_lr.relim()
            self.ax_lr.autoscale_view()
        
        # 更新梯度范数曲线
        if self.gradient_norms:
            self.line_grad.set_data(steps[-len(self.gradient_norms):], list(self.gradient_norms))
            self.ax_grad.relim()
            self.ax_grad.autoscale_view()
        
        # 更新显存曲线
        if self.memory_usage:
            self.line_mem.set_data(steps[-len(self.memory_usage):], list(self.memory_usage))
            self.ax_mem.relim()
            self.ax_mem.autoscale_view()
        
        self.fig.canvas.draw()
    
    def show(self):
        """显示监控面板"""
        plt.show()
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        stats = {
            'total_steps': self.total_steps,
            'current_loss': self.losses[-1] if self.losses else None,
            'avg_loss': sum(self.losses) / len(self.losses) if self.losses else None,
            'best_loss': self.best_loss,
            'min_loss': min(self.losses) if self.losses else None,
            'max_loss': max(self.losses) if self.losses else None,
        }
        
        if self.memory_usage:
            stats['peak_memory_gb'] = max(self.memory_usage)
            stats['current_memory_gb'] = self.memory_usage[-1]
        
        return stats
    
    def print_stats(self):
        """打印统计信息"""
        stats = self.get_stats()
        print(f"\n{'='*50}")
        print(f"训练统计")
        print(f"{'='*50}")
        print(f"总步数: {stats['total_steps']:,}")
        print(f"当前损失: {stats['current_loss']:.4f}")
        print(f"平均损失: {stats['avg_loss']:.4f}")
        print(f"最佳损失: {stats['best_loss']:.4f}")
        if 'peak_memory_gb' in stats:
            print(f"峰值显存: {stats['peak_memory_gb']:.2f} GB")
        print(f"{'='*50}")


# 使用示例
def demo_training_monitor():
    """演示训练监控器"""
    monitor = TrainingMonitor()
    
    # 模拟训练过程
    for step in range(200):
        # 模拟损失下降
        loss = 2.0 * math.exp(-step / 100) + 0.1 * math.sin(step / 10) + 0.5
        lr = 0.001 * (1 - step / 200)
        
        monitor.update(loss, lr)
        
        if step % 20 == 0:
            monitor.update_plot()
            monitor.print_stats()
    
    plt.ioff()
    monitor.show()


# 运行演示
demo_training_monitor()
```

---

## 42. 模型推理与对话项目

### 42.1 完整推理系统

```python
"""
MiniMind推理系统

包含：
1. 模型加载
2. 文本生成
3. 多种采样策略
4. 对话界面
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional, List, Tuple, Generator
import time
from dataclasses import dataclass


@dataclass
class GenerationConfig:
    """生成配置"""
    max_new_tokens: int = 100
    temperature: float = 1.0
    top_k: int = 50
    top_p: float = 0.9
    repetition_penalty: float = 1.1
    do_sample: bool = True
    use_cache: bool = True


class MiniMindForGeneration(nn.Module):
    """
    用于生成的MiniMind模型
    
    支持KV Cache加速推理
    """
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        
        # 模型组件（与训练模型相同）
        self.tok_embeddings = nn.Embedding(config.vocab_size, config.dim)
        self.layers = nn.ModuleList([
            TransformerBlock(config.dim, config.n_heads, config.max_seq_len)
            for _ in range(config.n_layers)
        ])
        self.norm = RMSNorm(config.dim)
        self.output = nn.Linear(config.dim, config.vocab_size, bias=False)
        
        # KV Cache
        self.kv_cache = None
    
    def forward(
        self,
        input_ids: torch.Tensor,
        use_cache: bool = False,
        past_key_values: Optional[List] = None
    ) -> Tuple[torch.Tensor, Optional[List]]:
        """
        前向传播
        
        参数：
        - input_ids: (batch, seq_len)
        - use_cache: 是否使用KV Cache
        - past_key_values: 过去的KV Cache
        
        返回：
        - logits: (batch, seq_len, vocab_size)
        - present_key_values: 当前的KV Cache
        """
        B, S = input_ids.shape
        
        x = self.tok_embeddings(input_ids)
        
        present_key_values = []
        
        for i, layer in enumerate(self.layers):
            # 这里简化了，实际需要修改TransformerBlock支持KV Cache
            x = layer(x)
        
        x = self.norm(x)
        logits = self.output(x)
        
        return logits, present_key_values
    
    def prepare_inputs_for_generation(
        self,
        input_ids: torch.Tensor,
        past_key_values: Optional[List] = None,
        **kwargs
    ):
        """准备生成输入"""
        if past_key_values is not None:
            # 只输入最后一个token
            input_ids = input_ids[:, -1:]
        
        return {
            'input_ids': input_ids,
            'past_key_values': past_key_values,
            'use_cache': kwargs.get('use_cache', True)
        }
    
    @classmethod
    def from_pretrained(cls, path: str, config):
        """从检查点加载模型"""
        model = cls(config)
        checkpoint = torch.load(path, map_location='cpu')
        model.load_state_dict(checkpoint['model'])
        return model


class TextGenerator:
    """
    文本生成器
    
    支持多种生成策略
    """
    
    def __init__(
        self,
        model: MiniMindForGeneration,
        tokenizer,
        device: str = 'cuda'
    ):
        self.model = model.to(device)
        self.model.eval()
        self.tokenizer = tokenizer
        self.device = device
    
    @torch.no_grad()
    def generate(
        self,
        prompt: str,
        config: GenerationConfig = None
    ) -> str:
        """
        生成文本
        
        参数：
        - prompt: 输入提示
        - config: 生成配置
        
        返回：
        - 生成的文本
        """
        if config is None:
            config = GenerationConfig()
        
        # 编码
        input_ids = torch.tensor(
            [self.tokenizer.encode(prompt)],
            dtype=torch.long,
            device=self.device
        )
        
        # 生成
        output_ids = self._generate_tokens(input_ids, config)
        
        # 解码
        return self.tokenizer.decode(output_ids[0].tolist())
    
    def _generate_tokens(
        self,
        input_ids: torch.Tensor,
        config: GenerationConfig
    ) -> torch.Tensor:
        """Token级别生成"""
        generated = input_ids.clone()
        past_key_values = None
        
        for _ in range(config.max_new_tokens):
            # 准备输入
            model_inputs = self.model.prepare_inputs_for_generation(
                generated,
                past_key_values=past_key_values,
                use_cache=config.use_cache
            )
            
            # 前向传播
            logits, past_key_values = self.model(**model_inputs)
            
            # 获取最后一个位置的logits
            next_token_logits = logits[:, -1, :]
            
            # 应用重复惩罚
            if config.repetition_penalty != 1.0:
                next_token_logits = self._apply_repetition_penalty(
                    next_token_logits,
                    generated,
                    config.repetition_penalty
                )
            
            # 应用温度
            if config.temperature != 1.0:
                next_token_logits = next_token_logits / config.temperature
            
            # 采样
            if config.do_sample:
                # Top-K
                if config.top_k > 0:
                    next_token_logits = self._top_k_filter(next_token_logits, config.top_k)
                
                # Top-P
                if config.top_p < 1.0:
                    next_token_logits = self._top_p_filter(next_token_logits, config.top_p)
                
                # 采样
                probs = F.softmax(next_token_logits, dim=-1)
                next_token = torch.multinomial(probs, num_samples=1)
            else:
                # 贪心
                next_token = next_token_logits.argmax(dim=-1, keepdim=True)
            
            # 拼接
            generated = torch.cat([generated, next_token], dim=-1)
            
            # 检查EOS
            if hasattr(self.tokenizer, 'eos_id') and next_token.item() == self.tokenizer.eos_id:
                break
        
        return generated
    
    def _apply_repetition_penalty(self, logits, generated, penalty):
        """应用重复惩罚"""
        for token_id in generated[0].unique():
            logits[0, token_id] /= penalty
        return logits
    
    def _top_k_filter(self, logits, top_k):
        """Top-K过滤"""
        values, _ = torch.topk(logits, top_k)
        min_value = values[:, -1].unsqueeze(-1)
        return torch.where(logits < min_value, float('-inf'), logits)
    
    def _top_p_filter(self, logits, top_p):
        """Top-P过滤"""
        sorted_logits, sorted_indices = torch.sort(logits, descending=True)
        cumulative_probs = torch.cumsum(F.softmax(sorted_logits, dim=-1), dim=-1)
        
        sorted_indices_to_remove = cumulative_probs > top_p
        sorted_indices_to_remove[..., 1:] = sorted_indices_to_remove[..., :-1].clone()
        sorted_indices_to_remove[..., 0] = False
        
        indices_to_remove = sorted_indices_to_remove.scatter(1, sorted_indices, sorted_indices_to_remove)
        return logits.masked_fill(indices_to_remove, float('-inf'))
    
    def generate_stream(
        self,
        prompt: str,
        config: GenerationConfig = None
    ) -> Generator[str, None, None]:
        """
        流式生成
        
        逐步返回生成的token
        """
        if config is None:
            config = GenerationConfig()
        
        input_ids = torch.tensor(
            [self.tokenizer.encode(prompt)],
            dtype=torch.long,
            device=self.device
        )
        
        generated = input_ids.clone()
        past_key_values = None
        
        for _ in range(config.max_new_tokens):
            model_inputs = self.model.prepare_inputs_for_generation(
                generated,
                past_key_values=past_key_values,
                use_cache=config.use_cache
            )
            
            logits, past_key_values = self.model(**model_inputs)
            next_token_logits = logits[:, -1, :]
            
            if config.do_sample:
                if config.top_k > 0:
                    next_token_logits = self._top_k_filter(next_token_logits, config.top_k)
                if config.top_p < 1.0:
                    next_token_logits = self._top_p_filter(next_token_logits, config.top_p)
                
                probs = F.softmax(next_token_logits / config.temperature, dim=-1)
                next_token = torch.multinomial(probs, num_samples=1)
            else:
                next_token = next_token_logits.argmax(dim=-1, keepdim=True)
            
            generated = torch.cat([generated, next_token], dim=-1)
            
            # 返回新生成的token
            new_text = self.tokenizer.decode([next_token.item()])
            yield new_text
    
    def chat(
        self,
        message: str,
        history: List[Tuple[str, str]] = None,
        config: GenerationConfig = None
    ) -> Tuple[str, List[Tuple[str, str]]]:
        """
        对话模式
        
        参数：
        - message: 用户消息
        - history: 对话历史
        - config: 生成配置
        
        返回：
        - 回复
        - 更新后的对话历史
        """
        if history is None:
            history = []
        
        # 构建提示
        prompt = self._build_chat_prompt(message, history)
        
        # 生成回复
        response = self.generate(prompt, config)
        
        # 提取回复部分
        response = self._extract_response(response, prompt)
        
        # 更新历史
        history.append((message, response))
        
        return response, history
    
    def _build_chat_prompt(self, message: str, history: List[Tuple[str, str]]) -> str:
        """构建对话提示"""
        prompt = ""
        
        for user_msg, assistant_msg in history:
            prompt += f"用户: {user_msg}\n助手: {assistant_msg}\n"
        
        prompt += f"用户: {message}\n助手: "
        
        return prompt
    
    def _extract_response(self, full_text: str, prompt: str) -> str:
        """提取回复"""
        return full_text[len(prompt):].strip()


# ==================== 交互式对话界面 ====================

class ChatInterface:
    """
    命令行对话界面
    
    使用方法：
    interface = ChatInterface(generator)
    interface.run()
    """
    
    def __init__(self, generator: TextGenerator):
        self.generator = generator
        self.history = []
        self.config = GenerationConfig(
            max_new_tokens=200,
            temperature=0.8,
            top_p=0.9
        )
    
    def run(self):
        """运行对话界面"""
        print("="*60)
        print("MiniMind 对话系统")
        print("输入 'quit' 退出, 'clear' 清空历史, 'config' 修改配置")
        print("="*60)
        
        while True:
            try:
                user_input = input("\n用户: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() == 'quit':
                    print("再见！")
                    break
                
                if user_input.lower() == 'clear':
                    self.history = []
                    print("对话历史已清空")
                    continue
                
                if user_input.lower() == 'config':
                    self._configure()
                    continue
                
                # 生成回复
                print("助手: ", end="", flush=True)
                
                start_time = time.time()
                response, self.history = self.generator.chat(
                    user_input,
                    self.history,
                    self.config
                )
                elapsed = time.time() - start_time
                
                print(response)
                print(f"\n[生成耗时: {elapsed:.2f}s]")
                
            except KeyboardInterrupt:
                print("\n\n对话已中断")
                break
            except Exception as e:
                print(f"\n错误: {e}")
    
    def _configure(self):
        """修改生成配置"""
        print("\n当前配置:")
        print(f"  max_new_tokens: {self.config.max_new_tokens}")
        print(f"  temperature: {self.config.temperature}")
        print(f"  top_k: {self.config.top_k}")
        print(f"  top_p: {self.config.top_p}")
        
        try:
            max_tokens = input("max_new_tokens (回车保持): ").strip()
            if max_tokens:
                self.config.max_new_tokens = int(max_tokens)
            
            temp = input("temperature (回车保持): ").strip()
            if temp:
                self.config.temperature = float(temp)
            
            top_k = input("top_k (回车保持): ").strip()
            if top_k:
                self.config.top_k = int(top_k)
            
            top_p = input("top_p (回车保持): ").strip()
            if top_p:
                self.config.top_p = float(top_p)
            
            print("配置已更新")
        except ValueError as e:
            print(f"输入错误: {e}")


# ==================== 使用示例 ====================

def demo_generation():
    """演示生成功能"""
    # 创建配置
    class Config:
        dim = 256
        n_layers = 4
        n_heads = 4
        vocab_size = 6400
        max_seq_len = 512
    
    config = Config()
    
    # 创建模型和分词器
    model = MiniMindForGeneration(config)
    tokenizer = SimpleTokenizer(config.vocab_size)
    
    # 创建生成器
    generator = TextGenerator(model, tokenizer)
    
    # 生成配置
    gen_config = GenerationConfig(
        max_new_tokens=50,
        temperature=0.8,
        top_k=40,
        top_p=0.9
    )
    
    # 生成文本
    prompt = "你好"
    output = generator.generate(prompt, gen_config)
    print(f"输入: {prompt}")
    print(f"输出: {output}")
    
    # 流式生成
    print("\n流式生成:")
    for token in generator.generate_stream(prompt, gen_config):
        print(token, end="", flush=True)
    print()


# 运行演示
demo_generation()
```

### 42.2 Web界面推理服务

```python
"""
Web界面推理服务

使用Gradio构建交互式Web界面
"""

# 安装依赖: pip install gradio

import gradio as gr
from typing import List, Tuple
import time


class WebChatInterface:
    """
    Gradio Web对话界面
    """
    
    def __init__(self, generator: TextGenerator):
        self.generator = generator
        self.config = GenerationConfig(
            max_new_tokens=200,
            temperature=0.8,
            top_p=0.9
        )
    
    def chat(
        self,
        message: str,
        history: List[Tuple[str, str]],
        max_tokens: int,
        temperature: float,
        top_p: float
    ) -> str:
        """
        对话函数
        
        参数：
        - message: 用户消息
        - history: 对话历史
        - max_tokens: 最大生成长度
        - temperature: 温度
        - top_p: Top-P
        
        返回：
        - 回复
        """
        # 更新配置
        self.config.max_new_tokens = max_tokens
        self.config.temperature = temperature
        self.config.top_p = top_p
        
        # 转换历史格式
        chat_history = [(h[0], h[1]) for h in history]
        
        # 生成回复
        response, _ = self.generator.chat(message, chat_history, self.config)
        
        return response
    
    def stream_chat(
        self,
        message: str,
        history: List[Tuple[str, str]],
        max_tokens: int,
        temperature: float,
        top_p: float
    ):
        """流式对话"""
        self.config.max_new_tokens = max_tokens
        self.config.temperature = temperature
        self.config.top_p = top_p
        
        prompt = self.generator._build_chat_prompt(message, [(h[0], h[1]) for h in history])
        
        response = ""
        for token in self.generator.generate_stream(prompt, self.config):
            response += token
            yield response
    
    def create_interface(self):
        """创建Gradio界面"""
        with gr.Blocks(title="MiniMind Chat") as demo:
            gr.Markdown("# 🤖 MiniMind 对话系统")
            gr.Markdown("一个轻量级的语言模型对话演示")
            
            with gr.Row():
                with gr.Column(scale=3):
                    chatbot = gr.Chatbot(
                        label="对话",
                        height=500,
                        show_label=True
                    )
                    
                    with gr.Row():
                        msg = gr.Textbox(
                            label="输入消息",
                            placeholder="在这里输入你的问题...",
                            scale=9
                        )
                        submit = gr.Button("发送", scale=1, variant="primary")
                    
                    with gr.Row():
                        clear = gr.Button("清空对话")
                        regenerate = gr.Button("重新生成")
                
                with gr.Column(scale=1):
                    gr.Markdown("### 生成参数")
                    
                    max_tokens = gr.Slider(
                        minimum=10,
                        maximum=500,
                        value=200,
                        step=10,
                        label="最大生成长度"
                    )
                    
                    temperature = gr.Slider(
                        minimum=0.1,
                        maximum=2.0,
                        value=0.8,
                        step=0.1,
                        label="温度"
                    )
                    
                    top_p = gr.Slider(
                        minimum=0.1,
                        maximum=1.0,
                        value=0.9,
                        step=0.05,
                        label="Top-P"
                    )
                    
                    gr.Markdown("""
                    ### 参数说明
                    
                    - **最大生成长度**: 生成文本的最大token数
                    - **温度**: 控制随机性，越高越随机
                    - **Top-P**: 核采样，保留累积概率为P的token
                    """)
            
            # 事件处理
            def user_input(user_message, history):
                return "", history + [[user_message, None]]
            
            def bot_response(history, max_t, temp, top_p):
                user_message = history[-1][0]
                bot_message = self.chat(user_message, history[:-1], max_t, temp, top_p)
                history[-1][1] = bot_message
                return history
            
            msg.submit(
                user_input,
                [msg, chatbot],
                [msg, chatbot],
                queue=False
            ).then(
                bot_response,
                [chatbot, max_tokens, temperature, top_p],
                chatbot
            )
            
            submit.click(
                user_input,
                [msg, chatbot],
                [msg, chatbot],
                queue=False
            ).then(
                bot_response,
                [chatbot, max_tokens, temperature, top_p],
                chatbot
            )
            
            clear.click(lambda: None, None, chatbot, queue=False)
        
        return demo
    
    def launch(self, share: bool = False, port: int = 7860):
        """启动服务"""
        demo = self.create_interface()
        demo.launch(share=share, server_port=port)


# 使用示例
def launch_web_demo():
    """启动Web演示"""
    # 创建模型和生成器
    class Config:
        dim = 256
        n_layers = 4
        n_heads = 4
        vocab_size = 6400
        max_seq_len = 512
    
    config = Config()
    model = MiniMindForGeneration(config)
    tokenizer = SimpleTokenizer(config.vocab_size)
    generator = TextGenerator(model, tokenizer)
    
    # 创建并启动Web界面
    interface = WebChatInterface(generator)
    interface.launch()


# 运行Web演示
# launch_web_demo()
```

---

## 43. 数据处理流水线项目

### 43.1 完整数据处理系统

```python
"""
数据处理流水线

包含：
1. 数据下载
2. 数据清洗
3. 数据预处理
4. 数据增强
5. 数据集构建
"""

import os
import re
import json
import random
from typing import List, Dict, Iterator, Optional
from dataclasses import dataclass
from collections import Counter
import multiprocessing as mp
from tqdm import tqdm


@dataclass
class DataConfig:
    """数据配置"""
    input_dir: str = "data/raw"
    output_dir: str = "data/processed"
    max_seq_len: int = 512
    min_seq_len: int = 10
    train_ratio: float = 0.9
    seed: int = 42


class DataCleaner:
    """
    数据清洗器
    
    清洗规则：
    1. 去除HTML标签
    2. 去除特殊字符
    3. 去除多余空白
    4. 去除过短文本
    """
    
    def __init__(self, min_length: int = 10):
        self.min_length = min_length
        
        # 编译正则表达式
        self.html_pattern = re.compile(r'<[^>]+>')
        self.special_char_pattern = re.compile(r'[^\w\s\u4e00-\u9fff.,!?;:\"\'()（）。，！？；：""''、]')
        self.whitespace_pattern = re.compile(r'\s+')
    
    def clean(self, text: str) -> Optional[str]:
        """
        清洗单条文本
        
        参数：
        - text: 原始文本
        
        返回：
        - 清洗后的文本（如果有效）
        """
        # 去除HTML标签
        text = self.html_pattern.sub('', text)
        
        # 去除特殊字符（保留中文和基本标点）
        text = self.special_char_pattern.sub('', text)
        
        # 去除多余空白
        text = self.whitespace_pattern.sub(' ', text).strip()
        
        # 检查长度
        if len(text) < self.min_length:
            return None
        
        return text
    
    def clean_batch(self, texts: List[str]) -> List[str]:
        """批量清洗"""
        cleaned = []
        for text in texts:
            result = self.clean(text)
            if result is not None:
                cleaned.append(result)
        return cleaned


class DataAugmenter:
    """
    数据增强器
    
    增强方法：
    1. 随机删除字符
    2. 随机交换字符
    3. 随机插入字符
    4. 同义词替换
    """
    
    def __init__(self, aug_ratio: float = 0.1):
        self.aug_ratio = aug_ratio
    
    def random_delete(self, text: str) -> str:
        """随机删除字符"""
        chars = list(text)
        n_delete = int(len(chars) * self.aug_ratio)
        
        for _ in range(n_delete):
            if len(chars) > 1:
                idx = random.randint(0, len(chars) - 1)
                chars.pop(idx)
        
        return ''.join(chars)
    
    def random_swap(self, text: str) -> str:
        """随机交换字符"""
        chars = list(text)
        n_swap = int(len(chars) * self.aug_ratio)
        
        for _ in range(n_swap):
            if len(chars) > 1:
                idx1 = random.randint(0, len(chars) - 1)
                idx2 = random.randint(0, len(chars) - 1)
                chars[idx1], chars[idx2] = chars[idx2], chars[idx1]
        
        return ''.join(chars)
    
    def augment(self, text: str, n_augments: int = 1) -> List[str]:
        """
        生成增强样本
        
        参数：
        - text: 原始文本
        - n_augments: 增强样本数量
        
        返回：
        - 增强后的文本列表
        """
        augmented = [text]
        
        for _ in range(n_augments):
            method = random.choice(['delete', 'swap'])
            
            if method == 'delete':
                augmented.append(self.random_delete(text))
            else:
                augmented.append(self.random_swap(text))
        
        return augmented


class TextChunker:
    """
    文本分块器
    
    将长文本分割成固定长度的块
    """
    
    def __init__(
        self,
        max_seq_len: int = 512,
        overlap: int = 50,
        respect_sentence: bool = True
    ):
        """
        参数：
        - max_seq_len: 最大序列长度
        - overlap: 重叠长度
        - respect_sentence: 是否尊重句子边界
        """
        self.max_seq_len = max_seq_len
        self.overlap = overlap
        self.respect_sentence = respect_sentence
        
        # 中文句子分隔符
        self.sentence_endings = ['。', '！', '？', '；', '.', '!', '?', ';']
    
    def chunk(self, text: str) -> List[str]:
        """
        分割文本
        
        参数：
        - text: 输入文本
        
        返回：
        - 文本块列表
        """
        if self.respect_sentence:
            return self._chunk_by_sentence(text)
        else:
            return self._chunk_by_length(text)
    
    def _chunk_by_sentence(self, text: str) -> List[str]:
        """按句子分割"""
        # 分割句子
        sentences = []
        current = ""
        
        for char in text:
            current += char
            if char in self.sentence_endings:
                sentences.append(current)
                current = ""
        
        if current:
            sentences.append(current)
        
        # 合并为块
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) <= self.max_seq_len:
                current_chunk += sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = sentence
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def _chunk_by_length(self, text: str) -> List[str]:
        """按长度分割"""
        chunks = []
        stride = self.max_seq_len - self.overlap
        
        for i in range(0, len(text), stride):
            chunk = text[i:i + self.max_seq_len]
            if len(chunk) >= self.overlap:
                chunks.append(chunk)
        
        return chunks


class DatasetBuilder:
    """
    数据集构建器
    
    构建训练、验证、测试数据集
    """
    
    def __init__(self, config: DataConfig):
        self.config = config
        self.cleaner = DataCleaner()
        self.augmenter = DataAugmenter()
        self.chunker = TextChunker(config.max_seq_len)
        
        random.seed(config.seed)
    
    def build_from_files(
        self,
        file_paths: List[str],
        output_prefix: str = "minimind"
    ):
        """
        从文件构建数据集
        
        参数：
        - file_paths: 输入文件路径列表
        - output_prefix: 输出文件前缀
        """
        print(f"开始构建数据集...")
        print(f"输入文件数: {len(file_paths)}")
        
        all_chunks = []
        
        for file_path in tqdm(file_paths, desc="处理文件"):
            chunks = self._process_file(file_path)
            all_chunks.extend(chunks)
        
        print(f"总文本块数: {len(all_chunks):,}")
        
        # 打乱
        random.shuffle(all_chunks)
        
        # 分割
        train_size = int(len(all_chunks) * self.config.train_ratio)
        train_data = all_chunks[:train_size]
        val_data = all_chunks[train_size:]
        
        print(f"训练集: {len(train_data):,}")
        print(f"验证集: {len(val_data):,}")
        
        # 保存
        os.makedirs(self.config.output_dir, exist_ok=True)
        
        self._save_dataset(train_data, os.path.join(self.config.output_dir, f"{output_prefix}_train.txt"))
        self._save_dataset(val_data, os.path.join(self.config.output_dir, f"{output_prefix}_val.txt"))
        
        # 保存统计信息
        stats = {
            'total_chunks': len(all_chunks),
            'train_size': len(train_data),
            'val_size': len(val_data),
            'max_seq_len': self.config.max_seq_len
        }
        
        with open(os.path.join(self.config.output_dir, 'stats.json'), 'w') as f:
            json.dump(stats, f, indent=2)
        
        print("数据集构建完成！")
    
    def _process_file(self, file_path: str) -> List[str]:
        """处理单个文件"""
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        # 清洗
        text = self.cleaner.clean(text)
        if text is None:
            return []
        
        # 分块
        chunks = self.chunker.chunk(text)
        
        # 过滤过短的块
        chunks = [c for c in chunks if len(c) >= self.config.min_seq_len]
        
        return chunks
    
    def _save_dataset(self, data: List[str], output_path: str):
        """保存数据集"""
        with open(output_path, 'w', encoding='utf-8') as f:
            for line in data:
                f.write(line + '\n')
        
        print(f"保存到: {output_path}")


class DataAnalyzer:
    """
    数据分析器
    
    分析数据集的统计特性
    """
    
    def __init__(self):
        self.stats = {}
    
    def analyze(self, file_path: str) -> Dict:
        """
        分析数据集
        
        参数：
        - file_path: 数据文件路径
        
        返回：
        - 统计信息
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 基本统计
        n_lines = len(lines)
        lengths = [len(line.strip()) for line in lines]
        
        # 字符统计
        char_counter = Counter()
        for line in lines:
            char_counter.update(line.strip())
        
        self.stats = {
            'n_samples': n_lines,
            'total_chars': sum(lengths),
            'avg_length': sum(lengths) / n_lines if n_lines > 0 else 0,
            'min_length': min(lengths) if lengths else 0,
            'max_length': max(lengths) if lengths else 0,
            'unique_chars': len(char_counter),
            'top_chars': char_counter.most_common(20)
        }
        
        return self.stats
    
    def print_stats(self):
        """打印统计信息"""
        print("\n数据集统计:")
        print("="*50)
        print(f"样本数: {self.stats['n_samples']:,}")
        print(f"总字符数: {self.stats['total_chars']:,}")
        print(f"平均长度: {self.stats['avg_length']:.2f}")
        print(f"最小长度: {self.stats['min_length']}")
        print(f"最大长度: {self.stats['max_length']}")
        print(f"唯一字符数: {self.stats['unique_chars']}")
        print("\n最常见字符:")
        for char, count in self.stats['top_chars']:
            print(f"  '{char}': {count:,}")


# ==================== 使用示例 ====================

def demo_data_pipeline():
    """演示数据处理流水线"""
    # 创建示例数据
    sample_text = """
    人工智能是计算机科学的一个分支，它企图了解智能的实质，并生产出一种新的能以人类智能相似的方式做出反应的智能机器。
    该领域的研究包括机器人、语言识别、图像识别、自然语言处理和专家系统等。
    深度学习是机器学习的一个分支，它使用多层神经网络来学习数据的表示。
    深度学习在图像识别、语音识别和自然语言处理等领域取得了突破性进展。
    """
    
    # 清洗
    cleaner = DataCleaner(min_length=10)
    cleaned = cleaner.clean(sample_text)
    print(f"清洗后: {cleaned[:100]}...")
    
    # 分块
    chunker = TextChunker(max_seq_len=50, respect_sentence=True)
    chunks = chunker.chunk(cleaned)
    print(f"\n分块数: {len(chunks)}")
    for i, chunk in enumerate(chunks):
        print(f"块 {i+1}: {chunk[:30]}...")
    
    # 增强
    augmenter = DataAugmenter(aug_ratio=0.1)
    augmented = augmenter.augment(chunks[0], n_augments=2)
    print(f"\n增强样本:")
    for i, aug in enumerate(augmented):
        print(f"  {i+1}: {aug[:50]}...")


# 运行演示
demo_data_pipeline()
```

---

## 四十四、可视化分析工具项目

### 44.1 训练过程可视化系统

```python
"""
MiniMind 训练过程可视化系统
============================

实时监控和分析训练过程，包括损失曲线、学习率、梯度统计等。

交互功能：
- 实时更新训练曲线
- 支持多实验对比
- 导出分析报告
- 异常检测告警
"""

import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.gridspec import GridSpec
import numpy as np
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import threading
import queue


@dataclass
class TrainingMetrics:
    """训练指标数据结构"""
    step: int
    epoch: int
    train_loss: float
    val_loss: Optional[float] = None
    learning_rate: float = 0.0
    grad_norm: float = 0.0
    epoch_time: float = 0.0
    gpu_memory: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class MetricsLogger:
    """
    指标记录器
    
    记录和管理训练过程中的各项指标
    """
    
    def __init__(self, log_dir: str = "./logs"):
        self.log_dir = log_dir
        self.metrics_history: List[TrainingMetrics] = []
        self.best_val_loss = float('inf')
        self.best_step = 0
        
        os.makedirs(log_dir, exist_ok=True)
    
    def log(self, metrics: TrainingMetrics):
        """记录指标"""
        self.metrics_history.append(metrics)
        
        # 更新最佳记录
        if metrics.val_loss is not None and metrics.val_loss < self.best_val_loss:
            self.best_val_loss = metrics.val_loss
            self.best_step = metrics.step
        
        # 保存到文件
        self._save_metrics(metrics)
    
    def _save_metrics(self, metrics: TrainingMetrics):
        """保存指标到文件"""
        log_file = os.path.join(self.log_dir, "training_log.jsonl")
        with open(log_file, 'a') as f:
            f.write(json.dumps(metrics.__dict__) + '\n')
    
    def get_series(self, metric_name: str) -> Tuple[List[int], List[float]]:
        """获取指定指标的时间序列"""
        steps = []
        values = []
        
        for m in self.metrics_history:
            steps.append(m.step)
            values.append(getattr(m, metric_name, 0))
        
        return steps, values
    
    def compute_statistics(self) -> Dict:
        """计算统计信息"""
        if not self.metrics_history:
            return {}
        
        train_losses = [m.train_loss for m in self.metrics_history]
        val_losses = [m.val_loss for m in self.metrics_history if m.val_loss is not None]
        
        return {
            'total_steps': len(self.metrics_history),
            'final_train_loss': train_losses[-1],
            'min_train_loss': min(train_losses),
            'final_val_loss': val_losses[-1] if val_losses else None,
            'min_val_loss': min(val_losses) if val_losses else None,
            'best_val_step': self.best_step,
            'convergence_rate': self._compute_convergence_rate(train_losses)
        }
    
    def _compute_convergence_rate(self, losses: List[float]) -> float:
        """计算收敛率"""
        if len(losses) < 10:
            return 0.0
        
        # 计算最后10%的损失变化率
        n = max(10, len(losses) // 10)
        recent = losses[-n:]
        return (recent[0] - recent[-1]) / n


class TrainingVisualizer:
    """
    训练可视化器
    
    实时绘制训练过程的各类图表
    """
    
    def __init__(self, logger: MetricsLogger, update_interval: int = 1000):
        self.logger = logger
        self.update_interval = update_interval  # 毫秒
        self.fig = None
        self.axes = {}
        self.lines = {}
        self.is_running = False
        
        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
    
    def setup_figure(self):
        """设置图表布局"""
        self.fig = plt.figure(figsize=(16, 10))
        self.fig.suptitle('MiniMind 训练监控面板', fontsize=14, fontweight='bold')
        
        gs = GridSpec(3, 3, figure=self.fig, hspace=0.3, wspace=0.3)
        
        # 损失曲线
        self.axes['loss'] = self.fig.add_subplot(gs[0, :2])
        self.axes['loss'].set_xlabel('Step')
        self.axes['loss'].set_ylabel('Loss')
        self.axes['loss'].set_title('训练/验证损失曲线')
        self.axes['loss'].grid(True, alpha=0.3)
        
        # 学习率曲线
        self.axes['lr'] = self.fig.add_subplot(gs[0, 2])
        self.axes['lr'].set_xlabel('Step')
        self.axes['lr'].set_ylabel('Learning Rate')
        self.axes['lr'].set_title('学习率变化')
        self.axes['lr'].grid(True, alpha=0.3)
        
        # 梯度范数
        self.axes['grad'] = self.fig.add_subplot(gs[1, 0])
        self.axes['grad'].set_xlabel('Step')
        self.axes['grad'].set_ylabel('Gradient Norm')
        self.axes['grad'].set_title('梯度范数')
        self.axes['grad'].grid(True, alpha=0.3)
        
        # GPU内存
        self.axes['memory'] = self.fig.add_subplot(gs[1, 1])
        self.axes['memory'].set_xlabel('Step')
        self.axes['memory'].set_ylabel('GPU Memory (GB)')
        self.axes['memory'].set_title('GPU内存使用')
        self.axes['memory'].grid(True, alpha=0.3)
        
        # 损失分布
        self.axes['loss_dist'] = self.fig.add_subplot(gs[1, 2])
        self.axes['loss_dist'].set_title('损失分布')
        
        # 统计信息
        self.axes['stats'] = self.fig.add_subplot(gs[2, :])
        self.axes['stats'].axis('off')
        
        # 初始化线条
        self.lines['train_loss'] = self.axes['loss'].plot([], [], 'b-', label='Train Loss', linewidth=2)[0]
        self.lines['val_loss'] = self.axes['loss'].plot([], [], 'r-', label='Val Loss', linewidth=2)[0]
        self.lines['lr'] = self.axes['lr'].plot([], [], 'g-', linewidth=2)[0]
        self.lines['grad'] = self.axes['grad'].plot([], [], 'm-', linewidth=2)[0]
        self.lines['memory'] = self.axes['memory'].plot([], [], 'c-', linewidth=2)[0]
        
        self.axes['loss'].legend(loc='upper right')
        
        plt.tight_layout()
    
    def update(self, frame):
        """更新图表"""
        if not self.logger.metrics_history:
            return list(self.lines.values())
        
        # 获取数据
        steps, train_losses = self.logger.get_series('train_loss')
        _, val_losses = self.logger.get_series('val_loss')
        _, lrs = self.logger.get_series('learning_rate')
        _, grad_norms = self.logger.get_series('grad_norm')
        _, memories = self.logger.get_series('gpu_memory')
        
        # 更新损失曲线
        self.lines['train_loss'].set_data(steps, train_losses)
        
        # 过滤None值
        val_steps = [s for s, v in zip(steps, val_losses) if v is not None]
        val_loss_filtered = [v for v in val_losses if v is not None]
        self.lines['val_loss'].set_data(val_steps, val_loss_filtered)
        
        # 更新学习率
        self.lines['lr'].set_data(steps, lrs)
        
        # 更新梯度范数
        self.lines['grad'].set_data(steps, grad_norms)
        
        # 更新GPU内存
        self.lines['memory'].set_data(steps, memories)
        
        # 调整坐标轴范围
        for ax_name in ['loss', 'lr', 'grad', 'memory']:
            ax = self.axes[ax_name]
            ax.relim()
            ax.autoscale_view()
        
        # 更新损失分布
        self.axes['loss_dist'].clear()
        self.axes['loss_dist'].hist(train_losses[-1000:], bins=30, alpha=0.7, color='blue')
        self.axes['loss_dist'].set_title('最近1000步损失分布')
        self.axes['loss_dist'].set_xlabel('Loss')
        
        # 更新统计信息
        stats = self.logger.compute_statistics()
        self._update_stats_display(stats)
        
        return list(self.lines.values())
    
    def _update_stats_display(self, stats: Dict):
        """更新统计信息显示"""
        self.axes['stats'].clear()
        self.axes['stats'].axis('off')
        
        text = f"""
        训练统计信息
        =============
        总步数: {stats.get('total_steps', 0):,}
        当前训练损失: {stats.get('final_train_loss', 0):.4f}
        最低训练损失: {stats.get('min_train_loss', 0):.4f}
        当前验证损失: {stats.get('final_val_loss', 'N/A')}
        最低验证损失: {stats.get('min_val_loss', 'N/A')}
        最佳步数: {stats.get('best_val_step', 'N/A')}
        收敛率: {stats.get('convergence_rate', 0):.6f}
        """
        
        self.axes['stats'].text(0.1, 0.5, text, transform=self.axes['stats'].transAxes,
                                fontsize=11, verticalalignment='center',
                                fontfamily='monospace',
                                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    def start_realtime(self):
        """启动实时更新"""
        self.setup_figure()
        self.is_running = True
        
        ani = animation.FuncAnimation(
            self.fig, self.update,
            interval=self.update_interval,
            blit=False,
            cache_frame_data=False
        )
        
        plt.show()
    
    def save_report(self, output_path: str = "./training_report.pdf"):
        """保存分析报告"""
        self.setup_figure()
        self.update(0)
        
        self.fig.savefig(output_path, format='pdf', dpi=150, bbox_inches='tight')
        print(f"报告已保存到: {output_path}")


class GradientAnalyzer:
    """
    梯度分析器
    
    分析模型梯度的统计特性，检测训练问题
    """
    
    def __init__(self):
        self.grad_history = []
        self.anomaly_detected = False
    
    def analyze_gradients(self, model) -> Dict:
        """分析模型梯度"""
        grad_stats = {
            'total_norm': 0.0,
            'max_grad': 0.0,
            'min_grad': 0.0,
            'mean_grad': 0.0,
            'grad_std': 0.0,
            'zero_grad_ratio': 0.0,
            'exploding': False,
            'vanishing': False
        }
        
        all_grads = []
        total_norm = 0.0
        
        for name, param in model.named_parameters():
            if param.grad is not None:
                grad = param.grad.data
                all_grads.append(grad.abs().mean().item())
                total_norm += grad.norm().item() ** 2
        
        if not all_grads:
            return grad_stats
        
        total_norm = total_norm ** 0.5
        grad_stats['total_norm'] = total_norm
        grad_stats['max_grad'] = max(all_grads)
        grad_stats['min_grad'] = min(all_grads)
        grad_stats['mean_grad'] = np.mean(all_grads)
        grad_stats['grad_std'] = np.std(all_grads)
        
        # 检测异常
        grad_stats['exploding'] = total_norm > 100.0
        grad_stats['vanishing'] = total_norm < 1e-7
        
        # 计算零梯度比例
        zero_count = sum(1 for g in all_grads if g < 1e-10)
        grad_stats['zero_grad_ratio'] = zero_count / len(all_grads)
        
        self.grad_history.append(grad_stats)
        
        return grad_stats
    
    def get_layer_grad_norms(self, model) -> Dict[str, float]:
        """获取各层梯度范数"""
        layer_norms = {}
        
        for name, param in model.named_parameters():
            if param.grad is not None:
                layer_norms[name] = param.grad.norm().item()
        
        return layer_norms
    
    def plot_gradient_flow(self, model, output_path: str = None):
        """绘制梯度流图"""
        layer_norms = self.get_layer_grad_norms(model)
        
        if not layer_norms:
            print("没有可用的梯度数据")
            return
        
        plt.figure(figsize=(12, 6))
        
        layers = list(layer_norms.keys())
        norms = list(layer_norms.values())
        
        # 简化层名
        short_names = [name.split('.')[-2] + '.' + name.split('.')[-1] 
                       for name in layers]
        
        colors = ['red' if n > 10 else 'blue' if n < 1e-5 else 'green' for n in norms]
        
        plt.bar(range(len(norms)), norms, color=colors, alpha=0.7)
        plt.xticks(range(len(short_names)), short_names, rotation=90, fontsize=8)
        plt.xlabel('Layer')
        plt.ylabel('Gradient Norm')
        plt.title('各层梯度范数分布 (红:爆炸, 蓝:消失, 绿:正常)')
        plt.yscale('log')
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            print(f"梯度流图已保存到: {output_path}")
        else:
            plt.show()


class AttentionVisualizer:
    """
    注意力可视化器
    
    可视化模型的注意力权重分布
    """
    
    def __init__(self, model, tokenizer):
        self.model = model
        self.tokenizer = tokenizer
    
    def visualize_attention(
        self,
        text: str,
        layer_idx: int = 0,
        head_idx: int = 0,
        output_path: str = None
    ):
        """可视化单个注意力头"""
        # 编码输入
        tokens = self.tokenizer.encode(text)
        input_ids = torch.tensor([tokens])
        
        # 获取注意力权重（需要修改模型以返回注意力）
        self.model.eval()
        with torch.no_grad():
            # 假设模型返回注意力权重
            outputs = self.model(input_ids, output_attentions=True)
            attentions = outputs.attentions  # (layers, batch, heads, seq, seq)
        
        # 提取指定层和头的注意力
        attention = attentions[layer_idx][0, head_idx].cpu().numpy()
        
        # 绘制热力图
        plt.figure(figsize=(10, 8))
        
        token_labels = [self.tokenizer.decode([t]) for t in tokens]
        
        sns.heatmap(
            attention,
            xticklabels=token_labels,
            yticklabels=token_labels,
            cmap='viridis',
            square=True,
            cbar_kws={'label': 'Attention Weight'}
        )
        
        plt.title(f'Layer {layer_idx}, Head {head_idx} Attention')
        plt.xlabel('Key Position')
        plt.ylabel('Query Position')
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
        else:
            plt.show()
    
    def visualize_all_heads(
        self,
        text: str,
        layer_idx: int = 0,
        output_path: str = None
    ):
        """可视化某一层所有注意力头"""
        tokens = self.tokenizer.encode(text)
        input_ids = torch.tensor([tokens])
        
        self.model.eval()
        with torch.no_grad():
            outputs = self.model(input_ids, output_attentions=True)
            attention = outputs.attentions[layer_idx][0].cpu().numpy()
        
        n_heads = attention.shape[0]
        n_cols = 4
        n_rows = (n_heads + n_cols - 1) // n_cols
        
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(16, 4 * n_rows))
        axes = axes.flatten()
        
        token_labels = [self.tokenizer.decode([t]) for t in tokens]
        
        for head_idx in range(n_heads):
            ax = axes[head_idx]
            sns.heatmap(
                attention[head_idx],
                ax=ax,
                xticklabels=token_labels if head_idx >= n_heads - n_cols else False,
                yticklabels=token_labels if head_idx % n_cols == 0 else False,
                cmap='viridis',
                square=True,
                cbar=False
            )
            ax.set_title(f'Head {head_idx}')
        
        # 隐藏多余的子图
        for idx in range(n_heads, len(axes)):
            axes[idx].axis('off')
        
        plt.suptitle(f'Layer {layer_idx} - All Attention Heads')
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
        else:
            plt.show()


class EmbeddingVisualizer:
    """
    词嵌入可视化器
    
    使用t-SNE或PCA可视化词嵌入空间
    """
    
    def __init__(self, model):
        self.model = model
        self.embeddings = None
        self.labels = None
    
    def extract_embeddings(self, tokenizer, top_k: int = 1000):
        """提取词嵌入"""
        # 获取最常见的词
        vocab = tokenizer.get_vocab()
        sorted_vocab = sorted(vocab.items(), key=lambda x: x[1])[:top_k]
        
        tokens = [t for t, _ in sorted_vocab]
        indices = [i for _, i in sorted_vocab]
        
        # 获取嵌入
        with torch.no_grad():
            embedding_matrix = self.model.tok_embeddings.weight
            self.embeddings = embedding_matrix[indices].cpu().numpy()
        
        self.labels = tokens
        
        return self.embeddings, self.labels
    
    def visualize_tsne(self, output_path: str = None):
        """使用t-SNE可视化"""
        from sklearn.manifold import TSNE
        
        if self.embeddings is None:
            print("请先提取嵌入")
            return
        
        print("正在计算t-SNE...")
        tsne = TSNE(n_components=2, random_state=42, perplexity=30)
        embeddings_2d = tsne.fit_transform(self.embeddings)
        
        plt.figure(figsize=(16, 12))
        plt.scatter(embeddings_2d[:, 0], embeddings_2d[:, 1], alpha=0.5, s=20)
        
        # 添加标签（只显示部分）
        for i, label in enumerate(self.labels[:200]):
            plt.annotate(label, (embeddings_2d[i, 0], embeddings_2d[i, 1]),
                        fontsize=8, alpha=0.7)
        
        plt.title('词嵌入空间 t-SNE 可视化')
        plt.xlabel('Dimension 1')
        plt.ylabel('Dimension 2')
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
        else:
            plt.show()
    
    def visualize_pca(self, output_path: str = None):
        """使用PCA可视化"""
        from sklearn.decomposition import PCA
        
        if self.embeddings is None:
            print("请先提取嵌入")
            return
        
        print("正在计算PCA...")
        pca = PCA(n_components=2)
        embeddings_2d = pca.fit_transform(self.embeddings)
        
        explained_var = pca.explained_variance_ratio_
        
        plt.figure(figsize=(16, 12))
        plt.scatter(embeddings_2d[:, 0], embeddings_2d[:, 1], alpha=0.5, s=20)
        
        for i, label in enumerate(self.labels[:200]):
            plt.annotate(label, (embeddings_2d[i, 0], embeddings_2d[i, 1]),
                        fontsize=8, alpha=0.7)
        
        plt.title(f'词嵌入空间 PCA 可视化\n解释方差: {explained_var[0]:.2%}, {explained_var[1]:.2%}')
        plt.xlabel(f'PC1 ({explained_var[0]:.2%})')
        plt.ylabel(f'PC2 ({explained_var[1]:.2%})')
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
        else:
            plt.show()


# ==================== 交互式使用示例 ====================

def demo_visualization():
    """演示可视化系统"""
    # 创建日志记录器
    logger = MetricsLogger(log_dir="./demo_logs")
    
    # 模拟训练过程
    print("模拟训练过程...")
    for step in range(100):
        # 模拟损失下降
        train_loss = 5.0 * np.exp(-step / 30) + np.random.randn() * 0.1
        val_loss = train_loss + np.random.randn() * 0.05 + 0.2
        
        # 模拟学习率
        lr = 1e-4 * (0.95 ** (step // 10))
        
        # 模拟梯度范数
        grad_norm = np.random.randn() * 0.5 + 1.0
        
        # 模拟GPU内存
        gpu_mem = 4.0 + np.random.randn() * 0.2
        
        metrics = TrainingMetrics(
            step=step,
            epoch=step // 10,
            train_loss=train_loss,
            val_loss=val_loss,
            learning_rate=lr,
            grad_norm=grad_norm,
            gpu_memory=gpu_mem
        )
        
        logger.log(metrics)
    
    # 创建可视化器
    visualizer = TrainingVisualizer(logger)
    
    # 保存报告
    visualizer.save_report("./demo_training_report.pdf")
    
    # 打印统计信息
    stats = logger.compute_statistics()
    print("\n训练统计:")
    for key, value in stats.items():
        print(f"  {key}: {value}")


# 运行演示
if __name__ == "__main__":
    demo_visualization()
```

### 44.2 模型结构可视化工具

```python
"""
MiniMind 模型结构可视化工具
============================

交互式展示模型架构、参数分布、计算流程等。

交互功能：
- 点击查看各层详情
- 参数量统计
- 计算量估算
- 层间连接可视化
"""

import torch
import torch.nn as nn
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import networkx as nx


@dataclass
class LayerInfo:
    """层信息数据结构"""
    name: str
    type: str
    input_shape: Tuple[int, ...]
    output_shape: Tuple[int, ...]
    params: int
    flops: int
    memory: int  # bytes


class ModelAnalyzer:
    """
    模型分析器
    
    分析模型结构和参数
    """
    
    def __init__(self, model: nn.Module):
        self.model = model
        self.layer_infos: List[LayerInfo] = []
        self.hooks = []
    
    def analyze(self, input_shape: Tuple[int, ...] = (1, 128)) -> Dict:
        """分析模型"""
        self.layer_infos = []
        
        # 注册钩子
        self._register_hooks()
        
        # 前向传播
        dummy_input = torch.randn(*input_shape, dtype=torch.long)
        with torch.no_grad():
            _ = self.model(dummy_input)
        
        # 移除钩子
        for hook in self.hooks:
            hook.remove()
        self.hooks = []
        
        # 计算统计信息
        total_params = sum(info.params for info in self.layer_infos)
        total_flops = sum(info.flops for info in self.layer_infos)
        total_memory = sum(info.memory for info in self.layer_infos)
        
        return {
            'layers': self.layer_infos,
            'total_params': total_params,
            'total_flops': total_flops,
            'total_memory': total_memory,
            'num_layers': len(self.layer_infos)
        }
    
    def _register_hooks(self):
        """注册前向钩子"""
        def make_hook(name, layer_type):
            def hook(module, input, output):
                # 获取形状
                input_shape = tuple(input[0].shape) if input else ()
                output_shape = tuple(output.shape) if isinstance(output, torch.Tensor) else ()
                
                # 计算参数量
                params = sum(p.numel() for p in module.parameters())
                
                # 估算FLOPs
                flops = self._estimate_flops(module, input_shape, output_shape)
                
                # 估算内存
                memory = params * 4  # 假设float32
                
                info = LayerInfo(
                    name=name,
                    type=layer_type,
                    input_shape=input_shape,
                    output_shape=output_shape,
                    params=params,
                    flops=flops,
                    memory=memory
                )
                self.layer_infos.append(info)
            
            return hook
        
        for name, module in self.model.named_modules():
            if len(list(module.children())) == 0:  # 只处理叶子模块
                layer_type = module.__class__.__name__
                hook = module.register_forward_hook(make_hook(name, layer_type))
                self.hooks.append(hook)
    
    def _estimate_flops(self, module, input_shape, output_shape):
        """估算FLOPs"""
        if isinstance(module, nn.Linear):
            return input_shape[-1] * output_shape[-1] * np.prod(output_shape[:-1])
        elif isinstance(module, nn.Embedding):
            return output_shape[-1] * np.prod(output_shape[:-1])
        elif isinstance(module, nn.LayerNorm):
            return input_shape[-1] * 4 * np.prod(input_shape[:-1])
        else:
            return 0
    
    def get_parameter_distribution(self) -> Dict[str, int]:
        """获取参数分布"""
        distribution = {}
        
        for name, param in self.model.named_parameters():
            layer_type = name.split('.')[0]
            if layer_type not in distribution:
                distribution[layer_type] = 0
            distribution[layer_type] += param.numel()
        
        return distribution
    
    def get_memory_footprint(self) -> Dict[str, float]:
        """获取内存占用（MB）"""
        memory = {
            'parameters': 0,
            'gradients': 0,
            'optimizer_states': 0
        }
        
        for param in self.model.parameters():
            n = param.numel()
            memory['parameters'] += n * 4  # float32
            if param.grad is not None:
                memory['gradients'] += n * 4
        
        # Adam优化器状态（2个状态变量）
        memory['optimizer_states'] = memory['parameters'] * 2
        
        # 转换为MB
        for key in memory:
            memory[key] = memory[key] / (1024 * 1024)
        
        return memory


class ModelArchitectureVisualizer:
    """
    模型架构可视化器
    
    绘制模型结构图
    """
    
    def __init__(self, analyzer: ModelAnalyzer):
        self.analyzer = analyzer
    
    def draw_architecture(self, output_path: str = None):
        """绘制模型架构图"""
        fig, ax = plt.subplots(figsize=(14, 10))
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 12)
        ax.axis('off')
        
        # 定义颜色
        colors = {
            'Embedding': '#FFB6C1',
            'Attention': '#87CEEB',
            'MLP': '#98FB98',
            'Norm': '#DDA0DD',
            'Output': '#F0E68C'
        }
        
        # 绘制层
        y_pos = 11
        layer_height = 0.6
        layer_width = 6
        x_start = 2
        
        for i, info in enumerate(self.analyzer.layer_infos):
            # 确定颜色
            color = '#FFFFFF'
            for key, c in colors.items():
                if key.lower() in info.type.lower():
                    color = c
                    break
            
            # 绘制矩形
            rect = FancyBboxPatch(
                (x_start, y_pos - layer_height),
                layer_width, layer_height,
                boxstyle="round,pad=0.05",
                facecolor=color,
                edgecolor='black',
                linewidth=1.5
            )
            ax.add_patch(rect)
            
            # 添加文本
            text = f"{info.name}\n{info.type}"
            ax.text(x_start + layer_width/2, y_pos - layer_height/2, text,
                   ha='center', va='center', fontsize=8)
            
            # 绘制箭头
            if i < len(self.analyzer.layer_infos) - 1:
                ax.annotate('', xy=(x_start + layer_width/2, y_pos - layer_height - 0.1),
                           xytext=(x_start + layer_width/2, y_pos - layer_height),
                           arrowprops=dict(arrowstyle='->', color='gray'))
            
            y_pos -= layer_height + 0.3
        
        plt.title('MiniMind 模型架构', fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
        else:
            plt.show()
    
    def draw_parameter_pie(self, output_path: str = None):
        """绘制参数分布饼图"""
        dist = self.analyzer.get_parameter_distribution()
        
        plt.figure(figsize=(10, 8))
        
        labels = list(dist.keys())
        sizes = list(dist.values())
        
        colors = plt.cm.Set3(np.linspace(0, 1, len(labels)))
        
        plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%',
                startangle=90, pctdistance=0.85)
        
        centre_circle = plt.Circle((0, 0), 0.70, fc='white')
        fig = plt.gcf()
        fig.gca().add_artist(centre_circle)
        
        total = sum(sizes)
        plt.text(0, 0, f'Total\n{total/1e6:.2f}M', ha='center', va='center', fontsize=12)
        
        plt.title('参数分布', fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
        else:
            plt.show()
    
    def draw_memory_bar(self, output_path: str = None):
        """绘制内存占用条形图"""
        memory = self.analyzer.get_memory_footprint()
        
        plt.figure(figsize=(10, 6))
        
        categories = list(memory.keys())
        values = list(memory.values())
        
        bars = plt.bar(categories, values, color=['#FF6B6B', '#4ECDC4', '#45B7D1'])
        
        # 添加数值标签
        for bar, val in zip(bars, values):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                    f'{val:.2f} MB', ha='center', va='bottom', fontsize=11)
        
        plt.xlabel('组件')
        plt.ylabel('内存占用 (MB)')
        plt.title('模型内存占用分析', fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
        else:
            plt.show()


class ComputationGraphVisualizer:
    """
    计算图可视化器
    
    可视化模型的计算流程
    """
    
    def __init__(self, model):
        self.model = model
        self.graph = nx.DiGraph()
    
    def build_graph(self):
        """构建计算图"""
        self.graph.clear()
        
        # 添加输入节点
        self.graph.add_node('Input', type='input')
        
        # 遍历模型结构
        prev_node = 'Input'
        
        for name, module in self.model.named_modules():
            if len(list(module.children())) == 0:
                node_name = name if name else module.__class__.__name__
                self.graph.add_node(node_name, type=module.__class__.__name__)
                self.graph.add_edge(prev_node, node_name)
                prev_node = node_name
        
        # 添加输出节点
        self.graph.add_node('Output', type='output')
        self.graph.add_edge(prev_node, 'Output')
    
    def draw_graph(self, output_path: str = None):
        """绘制计算图"""
        plt.figure(figsize=(16, 10))
        
        # 使用层次布局
        pos = nx.spring_layout(self.graph, k=2, iterations=50)
        
        # 根据类型设置颜色
        colors = []
        for node in self.graph.nodes():
            node_type = self.graph.nodes[node].get('type', '')
            if node_type == 'input':
                colors.append('#90EE90')
            elif node_type == 'output':
                colors.append('#FFB6C1')
            elif 'Attention' in node_type:
                colors.append('#87CEEB')
            elif 'MLP' in node_type or 'FeedForward' in node_type:
                colors.append('#98FB98')
            else:
                colors.append('#DDA0DD')
        
        nx.draw(
            self.graph, pos,
            with_labels=True,
            node_color=colors,
            node_size=2000,
            font_size=8,
            font_weight='bold',
            arrows=True,
            arrowsize=20,
            edge_color='gray'
        )
        
        plt.title('MiniMind 计算图', fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
        else:
            plt.show()


# ==================== 交互式仪表盘 ====================

class ModelDashboard:
    """
    模型分析仪表盘
    
    综合展示模型的各种分析结果
    """
    
    def __init__(self, model):
        self.model = model
        self.analyzer = ModelAnalyzer(model)
        self.arch_viz = ModelArchitectureVisualizer(self.analyzer)
        self.comp_viz = ComputationGraphVisualizer(model)
    
    def run_analysis(self, input_shape: Tuple[int, ...] = (1, 128)):
        """运行完整分析"""
        print("="*60)
        print("MiniMind 模型分析仪表盘")
        print("="*60)
        
        # 分析模型
        print("\n[1/5] 分析模型结构...")
        results = self.analyzer.analyze(input_shape)
        
        print(f"\n模型统计:")
        print(f"  总参数量: {results['total_params']:,}")
        print(f"  总FLOPs: {results['total_flops']:,}")
        print(f"  总内存: {results['total_memory'] / (1024*1024):.2f} MB")
        print(f"  层数: {results['num_layers']}")
        
        # 参数分布
        print("\n[2/5] 分析参数分布...")
        param_dist = self.analyzer.get_parameter_distribution()
        print("\n参数分布:")
        for name, count in sorted(param_dist.items(), key=lambda x: -x[1]):
            print(f"  {name}: {count:,} ({count/results['total_params']*100:.1f}%)")
        
        # 内存占用
        print("\n[3/5] 分析内存占用...")
        memory = self.analyzer.get_memory_footprint()
        print("\n内存占用:")
        for name, size in memory.items():
            print(f"  {name}: {size:.2f} MB")
        print(f"  总计: {sum(memory.values()):.2f} MB")
        
        # 生成可视化
        print("\n[4/5] 生成可视化图表...")
        self.arch_viz.draw_parameter_pie('./param_distribution.png')
        self.arch_viz.draw_memory_bar('./memory_usage.png')
        
        print("\n[5/5] 构建计算图...")
        self.comp_viz.build_graph()
        self.comp_viz.draw_graph('./computation_graph.png')
        
        print("\n" + "="*60)
        print("分析完成！生成的文件:")
        print("  - param_distribution.png")
        print("  - memory_usage.png")
        print("  - computation_graph.png")
        print("="*60)
        
        return results


# 运行示例
def demo_model_analysis():
    """演示模型分析"""
    # 创建示例模型
    from model import Transformer
    
    model = Transformer(
        dim=512,
        n_layers=8,
        n_heads=8,
        vocab_size=6400
    )
    
    # 运行仪表盘
    dashboard = ModelDashboard(model)
    results = dashboard.run_analysis()


if __name__ == "__main__":
    demo_model_analysis()
```

---

## 四十五、模型微调项目实践

### 45.1 完整微调框架

```python
"""
MiniMind 微调框架
==================

支持全量微调、LoRA微调、Prefix Tuning等多种微调方式。

交互功能：
- 选择微调策略
- 配置微调参数
- 监控微调过程
- 评估微调效果
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
import json
import os
import math
from copy import deepcopy
import matplotlib.pyplot as plt


# ==================== 微调配置 ====================

@dataclass
class FineTuningConfig:
    """微调配置"""
    # 基础配置
    base_model_path: str = "./out/model.pt"
    output_dir: str = "./finetuned"
    
    # 微调策略
    strategy: str = "lora"  # full, lora, prefix, adapter
    
    # LoRA配置
    lora_r: int = 8
    lora_alpha: int = 16
    lora_dropout: float = 0.05
    lora_targets: List[str] = field(default_factory=lambda: ["q_proj", "v_proj"])
    
    # Prefix Tuning配置
    prefix_len: int = 10
    prefix_init: str = "random"  # random, uniform, vocab
    
    # Adapter配置
    adapter_dim: int = 64
    adapter_dropout: float = 0.1
    
    # 训练配置
    learning_rate: float = 1e-4
    batch_size: int = 4
    num_epochs: int = 3
    warmup_ratio: float = 0.1
    weight_decay: float = 0.01
    max_grad_norm: float = 1.0
    
    # 数据配置
    max_seq_len: int = 512
    train_file: str = "./data/train.json"
    val_file: str = "./data/val.json"
    
    # 评估配置
    eval_steps: int = 100
    save_steps: int = 500
    log_steps: int = 10


# ==================== LoRA 实现 ====================

class LoRALayer(nn.Module):
    """
    LoRA (Low-Rank Adaptation) 层
    
    论文: LoRA: Low-Rank Adaptation of Large Language Models
    
    原理：
    - 冻结原始权重 W
    - 添加低秩分解 W' = W + BA
    - 只训练 A 和 B
    
    优势：
    - 参数量极少 (r << d)
    - 不增加推理延迟
    - 可插拔式设计
    """
    
    def __init__(
        self,
        in_features: int,
        out_features: int,
        r: int = 8,
        alpha: int = 16,
        dropout: float = 0.05
    ):
        super().__init__()
        
        self.r = r
        self.alpha = alpha
        self.scaling = alpha / r
        
        # 低秩矩阵
        self.lora_A = nn.Parameter(torch.zeros(r, in_features))
        self.lora_B = nn.Parameter(torch.zeros(out_features, r))
        
        # Dropout
        self.dropout = nn.Dropout(p=dropout)
        
        # 初始化
        nn.init.kaiming_uniform_(self.lora_A, a=math.sqrt(5))
        nn.init.zeros_(self.lora_B)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        前向传播
        
        计算: (x @ A.T @ B.T) * scaling
        """
        # x: (batch, seq_len, in_features)
        # lora_A: (r, in_features)
        # lora_B: (out_features, r)
        
        result = self.dropout(x) @ self.lora_A.T  # (batch, seq_len, r)
        result = result @ self.lora_B.T  # (batch, seq_len, out_features)
        
        return result * self.scaling


class LoRALinear(nn.Module):
    """
    带LoRA的线性层
    
    组合原始线性层和LoRA适配器
    """
    
    def __init__(
        self,
        original_layer: nn.Linear,
        r: int = 8,
        alpha: int = 16,
        dropout: float = 0.05
    ):
        super().__init__()
        
        self.original_layer = original_layer
        self.original_layer.weight.requires_grad = False
        if self.original_layer.bias is not None:
            self.original_layer.bias.requires_grad = False
        
        self.lora = LoRALayer(
            original_layer.in_features,
            original_layer.out_features,
            r, alpha, dropout
        )
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """前向传播：原始输出 + LoRA增量"""
        return self.original_layer(x) + self.lora(x)


def apply_lora_to_model(
    model: nn.Module,
    r: int = 8,
    alpha: int = 16,
    dropout: float = 0.05,
    target_modules: List[str] = None
) -> nn.Module:
    """
    将LoRA应用到模型
    
    参数：
    - model: 原始模型
    - r: LoRA秩
    - alpha: 缩放系数
    - dropout: Dropout率
    - target_modules: 目标模块名称列表
    
    返回：
    - 应用了LoRA的模型
    """
    if target_modules is None:
        target_modules = ["q_proj", "v_proj", "k_proj", "o_proj"]
    
    lora_params = []
    
    for name, module in model.named_modules():
        # 检查是否是目标模块
        is_target = any(target in name for target in target_modules)
        
        if is_target and isinstance(module, nn.Linear):
            # 获取父模块和属性名
            parts = name.rsplit('.', 1)
            if len(parts) == 2:
                parent_name, attr_name = parts
                parent = model.get_submodule(parent_name)
            else:
                parent = model
                attr_name = name
            
            # 创建LoRA层
            lora_layer = LoRALinear(module, r, alpha, dropout)
            
            # 替换
            setattr(parent, attr_name, lora_layer)
            
            # 记录可训练参数
            lora_params.append(lora_layer.lora.lora_A)
            lora_params.append(lora_layer.lora.lora_B)
            
            print(f"应用LoRA到: {name}")
    
    # 冻结非LoRA参数
    for name, param in model.named_parameters():
        if 'lora' not in name:
            param.requires_grad = False
    
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total_params = sum(p.numel() for p in model.parameters())
    
    print(f"\nLoRA应用完成!")
    print(f"可训练参数: {trainable_params:,} ({trainable_params/total_params*100:.2f}%)")
    print(f"总参数: {total_params:,}")
    
    return model


# ==================== Prefix Tuning 实现 ====================

class PrefixEncoder(nn.Module):
    """
    Prefix Tuning 编码器
    
    论文: Prefix-Tuning: Optimizing Continuous Prompts for Generation
    
    原理：
    - 在输入前添加可学习的前缀向量
    - 只训练前缀参数
    - 保持模型参数冻结
    
    优势：
    - 参数量极少
    - 任务特定适配
    - 易于切换任务
    """
    
    def __init__(
        self,
        config,
        prefix_len: int = 10,
        hidden_size: int = 512,
        num_layers: int = 8,
        num_heads: int = 8,
        init_method: str = "random"
    ):
        super().__init__()
        
        self.prefix_len = prefix_len
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.num_heads = num_heads
        self.head_dim = hidden_size // num_heads
        
        # 前缀嵌入
        # 每层都需要key和value的前缀
        total_dim = 2 * num_layers * hidden_size  # 2 for key and value
        
        # 使用MLP重参数化
        self.embedding = nn.Embedding(prefix_len, hidden_size)
        self.mlp = nn.Sequential(
            nn.Linear(hidden_size, hidden_size * 2),
            nn.Tanh(),
            nn.Linear(hidden_size * 2, total_dim)
        )
        
        # 初始化
        self._init_weights(init_method)
    
    def _init_weights(self, init_method: str):
        """初始化权重"""
        if init_method == "uniform":
            nn.init.uniform_(self.embedding.weight, -0.5, 0.5)
        elif init_method == "normal":
            nn.init.normal_(self.embedding.weight, 0, 0.02)
        # random 使用默认初始化
    
    def forward(self) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        获取前缀的key和value
        
        返回：
        - past_key_values: 形状为 (num_layers, 2, batch, num_heads, prefix_len, head_dim)
        """
        # 获取前缀嵌入
        prefix_tokens = torch.arange(self.prefix_len, device=self.embedding.weight.device)
        prefix_embeds = self.embedding(prefix_tokens)  # (prefix_len, hidden_size)
        
        # 通过MLP
        past = self.mlp(prefix_embeds)  # (prefix_len, 2 * num_layers * hidden_size)
        
        # 重塑为 (num_layers, 2, prefix_len, num_heads, head_dim)
        past = past.view(
            self.prefix_len,
            2,
            self.num_layers,
            self.num_heads,
            self.head_dim
        )
        
        # 调整维度顺序
        past = past.permute(2, 1, 0, 3, 4)  # (num_layers, 2, prefix_len, num_heads, head_dim)
        
        return past


def apply_prefix_tuning(
    model: nn.Module,
    prefix_len: int = 10,
    init_method: str = "random"
) -> nn.Module:
    """
    应用Prefix Tuning到模型
    """
    # 获取模型配置
    hidden_size = model.dim
    num_layers = model.n_layers
    num_heads = model.n_heads
    
    # 创建前缀编码器
    prefix_encoder = PrefixEncoder(
        model,
        prefix_len=prefix_len,
        hidden_size=hidden_size,
        num_layers=num_layers,
        num_heads=num_heads,
        init_method=init_method
    )
    
    # 添加到模型
    model.prefix_encoder = prefix_encoder
    
    # 冻结原始模型参数
    for param in model.parameters():
        if 'prefix_encoder' not in param.name:
            param.requires_grad = False
    
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total_params = sum(p.numel() for p in model.parameters())
    
    print(f"\nPrefix Tuning应用完成!")
    print(f"前缀长度: {prefix_len}")
    print(f"可训练参数: {trainable_params:,} ({trainable_params/total_params*100:.2f}%)")
    
    return model


# ==================== Adapter 实现 ====================

class AdapterLayer(nn.Module):
    """
    Adapter 层
    
    论文: Parameter-Efficient Transfer Learning for NLP
    
    原理：
    - 在Transformer层中插入小型瓶颈网络
    - 只训练Adapter参数
    - 保持模型参数冻结
    
    结构：
    - Linear(d, bottleneck_dim)
    - GELU
    - Linear(bottleneck_dim, d)
    - 残差连接
    """
    
    def __init__(
        self,
        hidden_size: int,
        bottleneck_dim: int = 64,
        dropout: float = 0.1
    ):
        super().__init__()
        
        self.down_proj = nn.Linear(hidden_size, bottleneck_dim)
        self.up_proj = nn.Linear(bottleneck_dim, hidden_size)
        self.dropout = nn.Dropout(dropout)
        self.act = nn.GELU()
        
        # 初始化
        nn.init.xavier_uniform_(self.down_proj.weight)
        nn.init.zeros_(self.down_proj.bias)
        nn.init.xavier_uniform_(self.up_proj.weight)
        nn.init.zeros_(self.up_proj.bias)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """前向传播"""
        # 下投影
        h = self.down_proj(x)
        h = self.act(h)
        h = self.dropout(h)
        
        # 上投影
        h = self.up_proj(h)
        
        # 残差连接
        return x + h


def apply_adapters_to_model(
    model: nn.Module,
    bottleneck_dim: int = 64,
    dropout: float = 0.1,
    apply_to_attention: bool = True,
    apply_to_ffn: bool = True
) -> nn.Module:
    """
    将Adapter应用到模型
    """
    adapter_count = 0
    
    for name, module in model.named_modules():
        # 在Attention后添加Adapter
        if apply_to_attention and 'attention' in name.lower():
            if hasattr(module, 'out_proj'):
                adapter = AdapterLayer(model.dim, bottleneck_dim, dropout)
                module.adapter_after_attn = adapter
                adapter_count += 1
        
        # 在FFN后添加Adapter
        if apply_to_ffn and 'feed_forward' in name.lower():
            adapter = AdapterLayer(model.dim, bottleneck_dim, dropout)
            module.adapter_after_ffn = adapter
            adapter_count += 1
    
    # 冻结非Adapter参数
    for name, param in model.named_parameters():
        if 'adapter' not in name:
            param.requires_grad = False
    
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total_params = sum(p.numel() for p in model.parameters())
    
    print(f"\nAdapter应用完成!")
    print(f"添加的Adapter数: {adapter_count}")
    print(f"可训练参数: {trainable_params:,} ({trainable_params/total_params*100:.2f}%)")
    
    return model


# ==================== 微调数据集 ====================

class FineTuningDataset(Dataset):
    """
    微调数据集
    
    支持多种数据格式：
    - 指令微调格式
    - 对话格式
    - 文本补全格式
    """
    
    def __init__(
        self,
        data_path: str,
        tokenizer,
        max_seq_len: int = 512,
        format_type: str = "instruction"
    ):
        self.tokenizer = tokenizer
        self.max_seq_len = max_seq_len
        self.format_type = format_type
        
        # 加载数据
        with open(data_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        
        print(f"加载了 {len(self.data)} 条数据")
    
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        item = self.data[idx]
        
        if self.format_type == "instruction":
            return self._format_instruction(item)
        elif self.format_type == "conversation":
            return self._format_conversation(item)
        else:
            return self._format_completion(item)
    
    def _format_instruction(self, item: Dict):
        """
        格式化指令数据
        
        格式: [INST] {instruction} [/INST] {response}
        """
        instruction = item.get('instruction', '')
        input_text = item.get('input', '')
        output = item.get('output', '')
        
        if input_text:
            prompt = f"[INST] {instruction}\n{input_text} [/INST]"
        else:
            prompt = f"[INST] {instruction} [/INST]"
        
        full_text = prompt + " " + output
        
        # 编码
        input_ids = self.tokenizer.encode(full_text)
        
        # 创建标签（只计算输出的损失）
        prompt_ids = self.tokenizer.encode(prompt)
        labels = [-100] * len(prompt_ids) + input_ids[len(prompt_ids):]
        
        # 截断
        input_ids = input_ids[:self.max_seq_len]
        labels = labels[:self.max_seq_len]
        
        return {
            'input_ids': torch.tensor(input_ids),
            'labels': torch.tensor(labels)
        }
    
    def _format_conversation(self, item: Dict):
        """格式化对话数据"""
        conversations = item.get('conversations', [])
        
        full_text = ""
        for conv in conversations:
            role = conv.get('role', 'user')
            content = conv.get('content', '')
            
            if role == 'user':
                full_text += f"<|user|>\n{content}\n"
            else:
                full_text += f"<|assistant|:\n{content}\n"
        
        input_ids = self.tokenizer.encode(full_text)[:self.max_seq_len]
        
        return {
            'input_ids': torch.tensor(input_ids),
            'labels': torch.tensor(input_ids)
        }
    
    def _format_completion(self, item: Dict):
        """格式化文本补全数据"""
        text = item.get('text', '')
        input_ids = self.tokenizer.encode(text)[:self.max_seq_len]
        
        return {
            'input_ids': torch.tensor(input_ids),
            'labels': torch.tensor(input_ids)
        }


# ==================== 微调训练器 ====================

class FineTuner:
    """
    微调训练器
    
    支持多种微调策略的统一接口
    """
    
    def __init__(
        self,
        model: nn.Module,
        config: FineTuningConfig,
        tokenizer
    ):
        self.config = config
        self.tokenizer = tokenizer
        
        # 应用微调策略
        self.model = self._apply_strategy(model)
        
        # 移动到设备
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model.to(self.device)
        
        # 设置优化器
        self.optimizer = self._create_optimizer()
        
        # 训练记录
        self.history = {
            'train_loss': [],
            'val_loss': [],
            'learning_rate': []
        }
    
    def _apply_strategy(self, model: nn.Module) -> nn.Module:
        """应用微调策略"""
        strategy = self.config.strategy
        
        if strategy == "full":
            print("使用全量微调...")
            # 解冻所有参数
            for param in model.parameters():
                param.requires_grad = True
        
        elif strategy == "lora":
            print(f"使用LoRA微调 (r={self.config.lora_r})...")
            model = apply_lora_to_model(
                model,
                r=self.config.lora_r,
                alpha=self.config.lora_alpha,
                dropout=self.config.lora_dropout,
                target_modules=self.config.lora_targets
            )
        
        elif strategy == "prefix":
            print(f"使用Prefix Tuning (len={self.config.prefix_len})...")
            model = apply_prefix_tuning(
                model,
                prefix_len=self.config.prefix_len,
                init_method=self.config.prefix_init
            )
        
        elif strategy == "adapter":
            print(f"使用Adapter微调 (dim={self.config.adapter_dim})...")
            model = apply_adapters_to_model(
                model,
                bottleneck_dim=self.config.adapter_dim,
                dropout=self.config.adapter_dropout
            )
        
        return model
    
    def _create_optimizer(self):
        """创建优化器"""
        # 只优化可训练参数
        trainable_params = [p for p in self.model.parameters() if p.requires_grad]
        
        # 分组：有weight decay和无weight decay
        decay_params = []
        no_decay_params = []
        
        for name, param in self.model.named_parameters():
            if not param.requires_grad:
                continue
            if 'bias' in name or 'norm' in name or 'lora_B' in name:
                no_decay_params.append(param)
            else:
                decay_params.append(param)
        
        optimizer_groups = [
            {'params': decay_params, 'weight_decay': self.config.weight_decay},
            {'params': no_decay_params, 'weight_decay': 0.0}
        ]
        
        return torch.optim.AdamW(
            optimizer_groups,
            lr=self.config.learning_rate
        )
    
    def train(self, train_dataset, val_dataset=None):
        """执行微调训练"""
        train_loader = DataLoader(
            train_dataset,
            batch_size=self.config.batch_size,
            shuffle=True,
            collate_fn=self._collate_fn
        )
        
        total_steps = len(train_loader) * self.config.num_epochs
        warmup_steps = int(total_steps * self.config.warmup_ratio)
        
        # 学习率调度器
        scheduler = self._create_scheduler(total_steps, warmup_steps)
        
        print(f"\n开始微调训练...")
        print(f"总步数: {total_steps}")
        print(f"预热步数: {warmup_steps}")
        
        global_step = 0
        best_val_loss = float('inf')
        
        for epoch in range(self.config.num_epochs):
            self.model.train()
            epoch_loss = 0
            
            for step, batch in enumerate(train_loader):
                # 前向传播
                loss = self._training_step(batch)
                
                # 反向传播
                self.optimizer.zero_grad()
                loss.backward()
                
                # 梯度裁剪
                torch.nn.utils.clip_grad_norm_(
                    [p for p in self.model.parameters() if p.requires_grad],
                    self.config.max_grad_norm
                )
                
                self.optimizer.step()
                scheduler.step()
                
                epoch_loss += loss.item()
                global_step += 1
                
                # 日志
                if global_step % self.config.log_steps == 0:
                    lr = scheduler.get_last_lr()[0]
                    self.history['train_loss'].append(loss.item())
                    self.history['learning_rate'].append(lr)
                    print(f"Epoch {epoch+1}, Step {global_step}, Loss: {loss.item():.4f}, LR: {lr:.2e}")
                
                # 验证
                if val_dataset and global_step % self.config.eval_steps == 0:
                    val_loss = self.evaluate(val_dataset)
                    self.history['val_loss'].append(val_loss)
                    
                    if val_loss < best_val_loss:
                        best_val_loss = val_loss
                        self._save_checkpoint('best_model.pt')
                    
                    print(f"验证损失: {val_loss:.4f}")
                
                # 保存
                if global_step % self.config.save_steps == 0:
                    self._save_checkpoint(f'checkpoint_{global_step}.pt')
            
            avg_loss = epoch_loss / len(train_loader)
            print(f"\nEpoch {epoch+1} 完成, 平均损失: {avg_loss:.4f}")
        
        # 保存最终模型
        self._save_checkpoint('final_model.pt')
        
        print("\n微调完成!")
        return self.history
    
    def _training_step(self, batch):
        """单步训练"""
        input_ids = batch['input_ids'].to(self.device)
        labels = batch['labels'].to(self.device)
        
        # 前向传播
        outputs = self.model(input_ids)
        
        # 计算损失
        shift_logits = outputs[..., :-1, :].contiguous()
        shift_labels = labels[..., 1:].contiguous()
        
        loss = F.cross_entropy(
            shift_logits.view(-1, shift_logits.size(-1)),
            shift_labels.view(-1),
            ignore_index=-100
        )
        
        return loss
    
    def evaluate(self, dataset):
        """评估模型"""
        self.model.eval()
        
        loader = DataLoader(
            dataset,
            batch_size=self.config.batch_size,
            collate_fn=self._collate_fn
        )
        
        total_loss = 0
        with torch.no_grad():
            for batch in loader:
                loss = self._training_step(batch)
                total_loss += loss.item()
        
        self.model.train()
        return total_loss / len(loader)
    
    def _collate_fn(self, batch):
        """批处理函数"""
        input_ids = [item['input_ids'] for item in batch]
        labels = [item['labels'] for item in batch]
        
        # 填充
        max_len = max(len(ids) for ids in input_ids)
        
        padded_ids = []
        padded_labels = []
        
        for ids, lbls in zip(input_ids, labels):
            pad_len = max_len - len(ids)
            padded_ids.append(F.pad(ids, (0, pad_len), value=0))
            padded_labels.append(F.pad(lbls, (0, pad_len), value=-100))
        
        return {
            'input_ids': torch.stack(padded_ids),
            'labels': torch.stack(padded_labels)
        }
    
    def _create_scheduler(self, total_steps, warmup_steps):
        """创建学习率调度器"""
        def lr_lambda(step):
            if step < warmup_steps:
                return step / warmup_steps
            return max(0.0, (total_steps - step) / (total_steps - warmup_steps))
        
        return torch.optim.lr_scheduler.LambdaLR(self.optimizer, lr_lambda)
    
    def _save_checkpoint(self, filename: str):
        """保存检查点"""
        os.makedirs(self.config.output_dir, exist_ok=True)
        path = os.path.join(self.config.output_dir, filename)
        
        # 保存可训练参数
        trainable_state = {
            name: param.data
            for name, param in self.model.named_parameters()
            if param.requires_grad
        }
        
        torch.save({
            'model_state': trainable_state,
            'optimizer_state': self.optimizer.state_dict(),
            'config': self.config.__dict__
        }, path)
        
        print(f"保存检查点: {path}")
    
    def plot_history(self, output_path: str = None):
        """绘制训练历史"""
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        
        # 损失曲线
        axes[0].plot(self.history['train_loss'], label='Train Loss')
        if self.history['val_loss']:
            val_steps = [i * self.config.eval_steps for i in range(len(self.history['val_loss']))]
            axes[0].plot(val_steps, self.history['val_loss'], 'r-', label='Val Loss')
        axes[0].set_xlabel('Step')
        axes[0].set_ylabel('Loss')
        axes[0].set_title('训练损失曲线')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)
        
        # 学习率曲线
        axes[1].plot(self.history['learning_rate'])
        axes[1].set_xlabel('Step')
        axes[1].set_ylabel('Learning Rate')
        axes[1].set_title('学习率变化')
        axes[1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
        else:
            plt.show()


# ==================== 交互式微调实验 ====================

class FineTuningExperiment:
    """
    微调实验管理器
    
    比较不同微调策略的效果
    """
    
    def __init__(self, base_model, tokenizer, data_path: str):
        self.base_model = base_model
        self.tokenizer = tokenizer
        self.data_path = data_path
        self.results = {}
    
    def run_comparison(
        self,
        strategies: List[str] = ["full", "lora", "prefix", "adapter"],
        num_epochs: int = 3
    ):
        """比较不同微调策略"""
        for strategy in strategies:
            print(f"\n{'='*60}")
            print(f"测试策略: {strategy}")
            print('='*60)
            
            # 创建配置
            config = FineTuningConfig(
                strategy=strategy,
                num_epochs=num_epochs
            )
            
            # 复制基础模型
            model = deepcopy(self.base_model)
            
            # 创建微调器
            tuner = FineTuner(model, config, self.tokenizer)
            
            # 加载数据
            train_dataset = FineTuningDataset(
                self.data_path,
                self.tokenizer,
                max_seq_len=config.max_seq_len
            )
            
            # 训练
            history = tuner.train(train_dataset)
            
            # 记录结果
            self.results[strategy] = {
                'final_loss': history['train_loss'][-1],
                'min_loss': min(history['train_loss']),
                'trainable_params': sum(p.numel() for p in model.parameters() if p.requires_grad),
                'history': history
            }
        
        # 打印比较结果
        self._print_comparison()
    
    def _print_comparison(self):
        """打印比较结果"""
        print("\n" + "="*60)
        print("微调策略比较结果")
        print("="*60)
        
        print(f"\n{'策略':<10} {'最终损失':<12} {'最低损失':<12} {'可训练参数':<15}")
        print("-"*60)
        
        for strategy, result in self.results.items():
            print(f"{strategy:<10} {result['final_loss']:<12.4f} {result['min_loss']:<12.4f} {result['trainable_params']:<15,}")
    
    def plot_comparison(self, output_path: str = None):
        """绘制比较图"""
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        
        # 损失曲线比较
        for strategy, result in self.results.items():
            axes[0].plot(result['history']['train_loss'], label=strategy)
        
        axes[0].set_xlabel('Step')
        axes[0].set_ylabel('Loss')
        axes[0].set_title('不同策略的损失曲线')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)
        
        # 参数量比较
        strategies = list(self.results.keys())
        params = [self.results[s]['trainable_params'] for s in strategies]
        
        bars = axes[1].bar(strategies, params)
        axes[1].set_xlabel('策略')
        axes[1].set_ylabel('可训练参数量')
        axes[1].set_title('不同策略的参数量')
        axes[1].set_yscale('log')
        
        for bar, p in zip(bars, params):
            axes[1].text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                        f'{p:,}', ha='center', va='bottom', fontsize=9)
        
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
        else:
            plt.show()


# ==================== 使用示例 ====================

def demo_finetuning():
    """演示微调流程"""
    print("="*60)
    print("MiniMind 微调演示")
    print("="*60)
    
    # 创建配置
    config = FineTuningConfig(
        strategy="lora",
        lora_r=8,
        lora_alpha=16,
        num_epochs=2
    )
    
    print(f"\n微调配置:")
    print(f"  策略: {config.strategy}")
    print(f"  LoRA秩: {config.lora_r}")
    print(f"  学习率: {config.learning_rate}")
    
    # 这里需要实际加载模型和数据
    # model = load_model(config.base_model_path)
    # tokenizer = load_tokenizer()
    # tuner = FineTuner(model, config, tokenizer)
    # history = tuner.train(train_dataset, val_dataset)
    
    print("\n微调演示完成!")


if __name__ == "__main__":
    demo_finetuning()
```

### 45.2 指令微调数据格式详解

```python
"""
指令微调数据格式详解
====================

介绍常见的指令微调数据格式及其处理方法。
"""

# ==================== Alpaca 格式 ====================

ALPACA_FORMAT = {
    "instruction": "解释什么是机器学习",
    "input": "",
    "output": "机器学习是人工智能的一个分支，它使计算机能够从数据中学习并做出决策或预测，而无需显式编程。"
}

# Alpaca格式处理
def format_alpaca(item: dict) -> str:
    """格式化Alpaca数据"""
    instruction = item['instruction']
    input_text = item.get('input', '')
    output = item['output']
    
    if input_text:
        return f"### Instruction:\n{instruction}\n\n### Input:\n{input_text}\n\n### Response:\n{output}"
    else:
        return f"### Instruction:\n{instruction}\n\n### Response:\n{output}"


# ==================== ShareGPT 格式 ====================

SHAREGPT_FORMAT = {
    "conversations": [
        {"from": "human", "value": "你好，请介绍一下自己"},
        {"from": "gpt", "value": "你好！我是一个AI助手，可以帮助你回答问题和完成任务。"},
        {"from": "human", "value": "你能做什么？"},
        {"from": "gpt", "value": "我可以帮助你进行问答、写作、编程、翻译等多种任务。"}
    ]
}

# ShareGPT格式处理
def format_sharegpt(item: dict) -> str:
    """格式化ShareGPT数据"""
    conversations = item['conversations']
    formatted = ""
    
    for conv in conversations:
        role = conv['from']
        content = conv['value']
        
        if role == 'human':
            formatted += f"<|user|>\n{content}\n"
        else:
            formatted += f"<|assistant|:\n{content}\n"
    
    return formatted


# ==================== OpenAI 格式 ====================

OPENAI_FORMAT = {
    "messages": [
        {"role": "system", "content": "你是一个有帮助的AI助手。"},
        {"role": "user", "content": "什么是深度学习？"},
        {"role": "assistant", "content": "深度学习是机器学习的一个子领域..."}
    ]
}

# OpenAI格式处理
def format_openai(item: dict) -> str:
    """格式化OpenAI数据"""
    messages = item['messages']
    formatted = ""
    
    for msg in messages:
        role = msg['role']
        content = msg['content']
        formatted += f"<|{role}|>\n{content}\n"
    
    return formatted


# ==================== 数据增强技术 ====================

class InstructionAugmenter:
    """
    指令数据增强器
    
    通过多种技术增强指令数据
    """
    
    def __init__(self):
        self.augmentation_methods = [
            self.paraphrase_instruction,
            self.add_context,
            self.split_complex_instruction
        ]
    
    def augment(self, item: dict, n_augments: int = 2) -> List[dict]:
        """生成增强样本"""
        augmented = [item]
        
        for _ in range(n_augments):
            method = np.random.choice(self.augmentation_methods)
            aug_item = method(item)
            if aug_item:
                augmented.append(aug_item)
        
        return augmented
    
    def paraphrase_instruction(self, item: dict) -> dict:
        """改写指令"""
        instruction = item['instruction']
        
        # 添加前缀变体
        prefixes = ["请", "帮我", "我需要你", "请解释", "请说明"]
        prefix = np.random.choice(prefixes)
        
        # 移除原有前缀
        for p in prefixes:
            if instruction.startswith(p):
                instruction = instruction[len(p):]
                break
        
        new_instruction = prefix + instruction
        
        return {
            **item,
            'instruction': new_instruction
        }
    
    def add_context(self, item: dict) -> dict:
        """添加上下文"""
        contexts = [
            "在回答时请保持简洁。",
            "请用通俗易懂的语言解释。",
            "请给出具体的例子。",
            "请分点回答。"
        ]
        
        context = np.random.choice(contexts)
        new_instruction = item['instruction'] + " " + context
        
        return {
            **item,
            'instruction': new_instruction
        }
    
    def split_complex_instruction(self, item: dict) -> dict:
        """拆分复杂指令"""
        # 如果指令包含多个问句，可以拆分
        instruction = item['instruction']
        
        if '和' in instruction and '？' in instruction:
            parts = instruction.split('和')
            if len(parts) == 2:
                return {
                    **item,
                    'instruction': parts[0].strip(),
                    'output': f"首先，{parts[0].strip()}\n\n其次，{parts[1].strip()}\n\n{item['output']}"
                }
        
        return None
```

---

## 四十六、性能优化实践项目

### 46.1 训练性能优化

```python
"""
MiniMind 训练性能优化实践
==========================

系统性地优化训练速度和内存使用。

优化技术：
- 混合精度训练
- 梯度累积
- 梯度检查点
- 数据加载优化
- 编译优化
"""

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torch.cuda.amp import autocast, GradScaler
from typing import Optional, Dict, List
import time
import gc


# ==================== 混合精度训练 ====================

class MixedPrecisionTrainer:
    """
    混合精度训练器
    
    使用FP16/BF16进行训练，显著减少显存占用并加速训练。
    
    原理：
    - 前向传播使用低精度（FP16/BF16）
    - 损失缩放防止梯度下溢
    - 权重更新使用FP32
    
    优势：
    - 显存减少约50%
    - 训练速度提升1.5-3倍
    - 几乎不损失精度
    """
    
    def __init__(
        self,
        model: nn.Module,
        optimizer: torch.optim.Optimizer,
        use_bf16: bool = False,
        init_scale: float = 2**16
    ):
        self.model = model
        self.optimizer = optimizer
        self.use_bf16 = use_bf16
        
        # 检查BF16支持
        if use_bf16:
            if not torch.cuda.is_bf16_supported():
                print("警告: GPU不支持BF16，将使用FP16")
                self.use_bf16 = False
        
        # 梯度缩放器（仅FP16需要）
        self.scaler = GradScaler(init_scale=init_scale) if not use_bf16 else None
        
        self.device = next(model.parameters()).device
    
    def training_step(self, batch: Dict) -> float:
        """执行一步训练"""
        self.model.train()
        
        input_ids = batch['input_ids'].to(self.device)
        labels = batch['labels'].to(self.device)
        
        self.optimizer.zero_grad()
        
        # 使用混合精度
        dtype = torch.bfloat16 if self.use_bf16 else torch.float16
        
        with autocast(dtype=dtype):
            outputs = self.model(input_ids)
            loss = self._compute_loss(outputs, labels)
        
        # 反向传播
        if self.scaler:
            self.scaler.scale(loss).backward()
            self.scaler.step(self.optimizer)
            self.scaler.update()
        else:
            loss.backward()
            self.optimizer.step()
        
        return loss.item()
    
    def _compute_loss(self, outputs, labels):
        """计算损失"""
        shift_outputs = outputs[..., :-1, :].contiguous()
        shift_labels = labels[..., 1:].contiguous()
        
        return nn.functional.cross_entropy(
            shift_outputs.view(-1, shift_outputs.size(-1)),
            shift_labels.view(-1),
            ignore_index=-100
        )


# ==================== 梯度累积 ====================

class GradientAccumulator:
    """
    梯度累积器
    
    在显存有限的情况下模拟更大的batch size。
    
    原理：
    - 将大batch分成多个小batch
    - 累积多个小batch的梯度
    - 达到累积步数后更新参数
    
    优势：
    - 小显存也能使用大batch
    - 训练效果接近真实大batch
    """
    
    def __init__(
        self,
        model: nn.Module,
        optimizer: torch.optim.Optimizer,
        accumulation_steps: int = 4
    ):
        self.model = model
        self.optimizer = optimizer
        self.accumulation_steps = accumulation_steps
        self.step_count = 0
        self.device = next(model.parameters()).device
    
    def training_step(self, batch: Dict) -> Optional[float]:
        """
        执行一步训练
        
        返回：
        - 如果达到累积步数，返回平均损失
        - 否则返回None
        """
        self.model.train()
        
        input_ids = batch['input_ids'].to(self.device)
        labels = batch['labels'].to(self.device)
        
        # 前向传播
        outputs = self.model(input_ids)
        loss = self._compute_loss(outputs, labels)
        
        # 缩放损失
        scaled_loss = loss / self.accumulation_steps
        
        # 反向传播（累积梯度）
        scaled_loss.backward()
        
        self.step_count += 1
        
        # 达到累积步数时更新
        if self.step_count >= self.accumulation_steps:
            # 梯度裁剪
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
            
            # 更新参数
            self.optimizer.step()
            self.optimizer.zero_grad()
            
            self.step_count = 0
            
            return loss.item()
        
        return None
    
    def _compute_loss(self, outputs, labels):
        """计算损失"""
        shift_outputs = outputs[..., :-1, :].contiguous()
        shift_labels = labels[..., 1:].contiguous()
        
        return nn.functional.cross_entropy(
            shift_outputs.view(-1, shift_outputs.size(-1)),
            shift_labels.view(-1),
            ignore_index=-100
        )


# ==================== 梯度检查点 ====================

class GradientCheckpointing:
    """
    梯度检查点实现
    
    通过时间换空间的方式减少显存占用。
    
    原理：
    - 前向传播时不保存中间激活
    - 反向传播时重新计算需要的激活
    - 以计算时间为代价换取显存
    
    优势：
    - 显存占用大幅减少
    - 可以训练更大的模型
    - 训练速度略有下降
    """
    
    @staticmethod
    def apply_to_model(model: nn.Module, enable: bool = True):
        """
        对模型启用/禁用梯度检查点
        
        参数：
        - model: 模型
        - enable: 是否启用
        """
        if hasattr(model, 'gradient_checkpointing_enable'):
            model.gradient_checkpointing_enable() if enable else model.gradient_checkpointing_disable()
        else:
            # 手动实现
            for module in model.modules():
                if hasattr(module, 'gradient_checkpointing'):
                    module.gradient_checkpointing = enable
    
    @staticmethod
    def checkpoint_function(function, *args, **kwargs):
        """
        检查点函数包装
        
        使用示例：
        ```python
        def forward(self, x):
            if self.training and self.use_checkpoint:
                return torch.utils.checkpoint.checkpoint(
                    self._forward_impl, x
                )
            return self._forward_impl(x)
        ```
        """
        return torch.utils.checkpoint.checkpoint(
            function, *args, use_reentrant=False, **kwargs
        )


# ==================== 数据加载优化 ====================

class OptimizedDataLoader:
    """
    优化的数据加载器
    
    多种优化技术提升数据加载效率。
    """
    
    @staticmethod
    def create(
        dataset,
        batch_size: int,
        shuffle: bool = True,
        num_workers: int = 4,
        pin_memory: bool = True,
        prefetch_factor: int = 2,
        persistent_workers: bool = True
    ) -> DataLoader:
        """
        创建优化的DataLoader
        
        优化参数说明：
        - num_workers: 多进程加载数据
        - pin_memory: 锁页内存，加速GPU传输
        - prefetch_factor: 预取批次数
        - persistent_workers: 保持worker进程
        """
        return DataLoader(
            dataset,
            batch_size=batch_size,
            shuffle=shuffle,
            num_workers=num_workers,
            pin_memory=pin_memory,
            prefetch_factor=prefetch_factor if num_workers > 0 else None,
            persistent_workers=persistent_workers if num_workers > 0 else False,
            collate_fn=dataset.collate_fn if hasattr(dataset, 'collate_fn') else None
        )


class AsyncDataLoader:
    """
    异步数据加载器
    
    使用独立线程预加载数据，进一步减少等待时间。
    """
    
    def __init__(self, dataloader: DataLoader, device: torch.device):
        self.dataloader = dataloader
        self.device = device
        self.stream = torch.cuda.Stream()
        self.next_batch = None
        self.iterator = None
    
    def __iter__(self):
        self.iterator = iter(self.dataloader)
        self._preload()
        return self
    
    def __next__(self):
        torch.cuda.current_stream().wait_stream(self.stream)
        batch = self.next_batch
        
        if batch is None:
            raise StopIteration
        
        self._preload()
        
        return batch
    
    def _preload(self):
        """预加载下一批数据"""
        try:
            next_batch = next(self.iterator)
        except StopIteration:
            self.next_batch = None
            return
        
        with torch.cuda.stream(self.stream):
            self.next_batch = {
                k: v.to(self.device, non_blocking=True)
                for k, v in next_batch.items()
            }


# ==================== 内存优化 ====================

class MemoryOptimizer:
    """
    内存优化工具
    
    分析和优化GPU内存使用。
    """
    
    @staticmethod
    def get_memory_stats() -> Dict:
        """获取内存统计"""
        if not torch.cuda.is_available():
            return {}
        
        allocated = torch.cuda.memory_allocated() / 1024**3
        reserved = torch.cuda.memory_reserved() / 1024**3
        max_allocated = torch.cuda.max_memory_allocated() / 1024**3
        
        return {
            'allocated_gb': allocated,
            'reserved_gb': reserved,
            'max_allocated_gb': max_allocated,
            'utilization': allocated / reserved if reserved > 0 else 0
        }
    
    @staticmethod
    def clear_cache():
        """清理GPU缓存"""
        gc.collect()
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
    
    @staticmethod
    def print_memory_stats(prefix: str = ""):
        """打印内存统计"""
        stats = MemoryOptimizer.get_memory_stats()
        print(f"{prefix} 内存统计:")
        print(f"  已分配: {stats['allocated_gb']:.2f} GB")
        print(f"  已预留: {stats['reserved_gb']:.2f} GB")
        print(f"  峰值: {stats['max_allocated_gb']:.2f} GB")
        print(f"  利用率: {stats['utilization']*100:.1f}%")


# ==================== 编译优化 ====================

class CompiledModel:
    """
    使用torch.compile优化模型
    
    PyTorch 2.0+ 的编译优化功能。
    
    优势：
    - 自动图优化
    - 算子融合
    - 显著提升推理和训练速度
    """
    
    @staticmethod
    def compile(
        model: nn.Module,
        mode: str = "default",
        fullgraph: bool = False,
        dynamic: bool = False
    ) -> nn.Module:
        """
        编译模型
        
        参数：
        - model: 要编译的模型
        - mode: 编译模式
          - "default": 平衡编译时间和性能
          - "reduce-overhead": 减少Python开销
          - "max-autotune": 最大性能优化
        - fullgraph: 是否编译完整图
        - dynamic: 是否支持动态形状
        """
        if not hasattr(torch, 'compile'):
            print("警告: torch.compile不可用，需要PyTorch 2.0+")
            return model
        
        print(f"编译模型 (mode={mode})...")
        
        compiled = torch.compile(
            model,
            mode=mode,
            fullgraph=fullgraph,
            dynamic=dynamic
        )
        
        return compiled


# ==================== 性能基准测试 ====================

class PerformanceBenchmark:
    """
    性能基准测试工具
    
    测量和比较不同优化技术的效果。
    """
    
    def __init__(self, model: nn.Module, device: torch.device):
        self.model = model
        self.device = device
        self.results = {}
    
    def benchmark_forward(
        self,
        batch_size: int = 4,
        seq_len: int = 128,
        num_iterations: int = 100,
        warmup: int = 10
    ) -> Dict:
        """基准测试前向传播"""
        # 准备输入
        input_ids = torch.randint(0, 1000, (batch_size, seq_len), device=self.device)
        
        # 预热
        self.model.eval()
        with torch.no_grad():
            for _ in range(warmup):
                _ = self.model(input_ids)
        
        torch.cuda.synchronize()
        
        # 测试
        start_time = time.perf_counter()
        
        with torch.no_grad():
            for _ in range(num_iterations):
                _ = self.model(input_ids)
        
        torch.cuda.synchronize()
        end_time = time.perf_counter()
        
        total_time = end_time - start_time
        avg_time = total_time / num_iterations
        throughput = batch_size / avg_time
        
        return {
            'total_time': total_time,
            'avg_time_ms': avg_time * 1000,
            'throughput': throughput,
            'batch_size': batch_size,
            'seq_len': seq_len
        }
    
    def benchmark_training(
        self,
        batch_size: int = 4,
        seq_len: int = 128,
        num_iterations: int = 100,
        warmup: int = 10
    ) -> Dict:
        """基准测试训练步骤"""
        input_ids = torch.randint(0, 1000, (batch_size, seq_len), device=self.device)
        labels = input_ids.clone()
        
        optimizer = torch.optim.AdamW(self.model.parameters(), lr=1e-4)
        
        # 预热
        self.model.train()
        for _ in range(warmup):
            outputs = self.model(input_ids)
            loss = self._compute_loss(outputs, labels)
            loss.backward()
            optimizer.step()
            optimizer.zero_grad()
        
        torch.cuda.synchronize()
        
        # 测试
        start_time = time.perf_counter()
        
        for _ in range(num_iterations):
            outputs = self.model(input_ids)
            loss = self._compute_loss(outputs, labels)
            loss.backward()
            optimizer.step()
            optimizer.zero_grad()
        
        torch.cuda.synchronize()
        end_time = time.perf_counter()
        
        total_time = end_time - start_time
        avg_time = total_time / num_iterations
        
        return {
            'total_time': total_time,
            'avg_time_ms': avg_time * 1000,
            'batch_size': batch_size,
            'seq_len': seq_len
        }
    
    def _compute_loss(self, outputs, labels):
        """计算损失"""
        shift_outputs = outputs[..., :-1, :].contiguous()
        shift_labels = labels[..., 1:].contiguous()
        return nn.functional.cross_entropy(
            shift_outputs.view(-1, shift_outputs.size(-1)),
            shift_labels.view(-1)
        )
    
    def compare_optimizations(self, configs: List[Dict]) -> Dict:
        """
        比较不同优化配置
        
        参数：
        - configs: 配置列表，每个配置包含name和优化参数
        
        返回：
        - 比较结果
        """
        results = {}
        
        for config in configs:
            name = config['name']
            print(f"\n测试配置: {name}")
            
            # 应用配置
            model = self._apply_config(config)
            
            # 运行基准测试
            forward_result = self.benchmark_forward()
            training_result = self.benchmark_training()
            
            # 记录内存
            memory_stats = MemoryOptimizer.get_memory_stats()
            
            results[name] = {
                'forward': forward_result,
                'training': training_result,
                'memory': memory_stats
            }
            
            # 清理
            MemoryOptimizer.clear_cache()
        
        self.results = results
        return results
    
    def _apply_config(self, config: Dict) -> nn.Module:
        """应用优化配置"""
        model = self.model
        
        if config.get('compile', False):
            model = CompiledModel.compile(model)
        
        if config.get('gradient_checkpointing', False):
            GradientCheckpointing.apply_to_model(model, True)
        
        return model
    
    def print_results(self):
        """打印比较结果"""
        print("\n" + "="*80)
        print("性能比较结果")
        print("="*80)
        
        print(f"\n{'配置':<20} {'前向(ms)':<12} {'训练(ms)':<12} {'显存(GB)':<12}")
        print("-"*60)
        
        for name, result in self.results.items():
            forward_ms = result['forward']['avg_time_ms']
            training_ms = result['training']['avg_time_ms']
            memory_gb = result['memory']['max_allocated_gb']
            
            print(f"{name:<20} {forward_ms:<12.2f} {training_ms:<12.2f} {memory_gb:<12.2f}")


# ==================== 综合优化训练器 ====================

class OptimizedTrainer:
    """
    综合优化训练器
    
    整合所有优化技术的训练器。
    """
    
    def __init__(
        self,
        model: nn.Module,
        train_dataloader: DataLoader,
        val_dataloader: DataLoader = None,
        learning_rate: float = 1e-4,
        num_epochs: int = 10,
        # 优化选项
        use_amp: bool = True,
        use_bf16: bool = False,
        gradient_accumulation_steps: int = 1,
        use_gradient_checkpointing: bool = False,
        compile_model: bool = False,
        max_grad_norm: float = 1.0
    ):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # 模型
        self.model = model.to(self.device)
        
        # 应用优化
        if use_gradient_checkpointing:
            GradientCheckpointing.apply_to_model(self.model, True)
            print("启用梯度检查点")
        
        if compile_model and hasattr(torch, 'compile'):
            self.model = CompiledModel.compile(self.model)
            print("启用模型编译")
        
        # 数据加载器
        self.train_dataloader = train_dataloader
        self.val_dataloader = val_dataloader
        
        # 优化器
        self.optimizer = torch.optim.AdamW(
            self.model.parameters(),
            lr=learning_rate,
            weight_decay=0.01
        )
        
        # 混合精度
        self.use_amp = use_amp
        self.use_bf16 = use_bf16 and torch.cuda.is_bf16_supported()
        self.scaler = GradScaler() if use_amp and not self.use_bf16 else None
        
        # 梯度累积
        self.gradient_accumulation_steps = gradient_accumulation_steps
        
        # 其他参数
        self.num_epochs = num_epochs
        self.max_grad_norm = max_grad_norm
        
        # 记录
        self.history = {
            'train_loss': [],
            'val_loss': [],
            'lr': [],
            'memory': []
        }
    
    def train(self):
        """执行训练"""
        print(f"\n开始训练...")
        print(f"设备: {self.device}")
        print(f"混合精度: {'BF16' if self.use_bf16 else 'FP16' if self.use_amp else 'FP32'}")
        print(f"梯度累积步数: {self.gradient_accumulation_steps}")
        
        global_step = 0
        accumulated_loss = 0.0
        
        for epoch in range(self.num_epochs):
            self.model.train()
            epoch_loss = 0.0
            
            for step, batch in enumerate(self.train_dataloader):
                # 前向传播
                loss = self._forward_step(batch)
                
                # 缩放损失
                scaled_loss = loss / self.gradient_accumulation_steps
                
                # 反向传播
                if self.scaler:
                    self.scaler.scale(scaled_loss).backward()
                else:
                    scaled_loss.backward()
                
                accumulated_loss += loss.item()
                
                # 梯度累积
                if (step + 1) % self.gradient_accumulation_steps == 0:
                    # 梯度裁剪
                    if self.scaler:
                        self.scaler.unscale_(self.optimizer)
                    
                    torch.nn.utils.clip_grad_norm_(
                        self.model.parameters(),
                        self.max_grad_norm
                    )
                    
                    # 更新参数
                    if self.scaler:
                        self.scaler.step(self.optimizer)
                        self.scaler.update()
                    else:
                        self.optimizer.step()
                    
                    self.optimizer.zero_grad()
                    
                    # 记录
                    avg_loss = accumulated_loss / self.gradient_accumulation_steps
                    self.history['train_loss'].append(avg_loss)
                    accumulated_loss = 0.0
                    global_step += 1
                    
                    if global_step % 10 == 0:
                        memory = MemoryOptimizer.get_memory_stats()
                        self.history['memory'].append(memory['allocated_gb'])
                        print(f"Epoch {epoch+1}, Step {global_step}, Loss: {avg_loss:.4f}, Memory: {memory['allocated_gb']:.2f}GB")
            
            # 验证
            if self.val_dataloader:
                val_loss = self.evaluate()
                self.history['val_loss'].append(val_loss)
                print(f"验证损失: {val_loss:.4f}")
        
        print("\n训练完成!")
        return self.history
    
    def _forward_step(self, batch) -> torch.Tensor:
        """前向传播步骤"""
        input_ids = batch['input_ids'].to(self.device)
        labels = batch['labels'].to(self.device) if 'labels' in batch else input_ids
        
        dtype = torch.bfloat16 if self.use_bf16 else torch.float16 if self.use_amp else torch.float32
        
        if self.use_amp:
            with autocast(dtype=dtype):
                outputs = self.model(input_ids)
                loss = self._compute_loss(outputs, labels)
        else:
            outputs = self.model(input_ids)
            loss = self._compute_loss(outputs, labels)
        
        return loss
    
    def _compute_loss(self, outputs, labels):
        """计算损失"""
        shift_outputs = outputs[..., :-1, :].contiguous()
        shift_labels = labels[..., 1:].contiguous()
        
        return nn.functional.cross_entropy(
            shift_outputs.view(-1, shift_outputs.size(-1)),
            shift_labels.view(-1),
            ignore_index=-100
        )
    
    def evaluate(self) -> float:
        """评估模型"""
        self.model.eval()
        total_loss = 0.0
        
        with torch.no_grad():
            for batch in self.val_dataloader:
                loss = self._forward_step(batch)
                total_loss += loss.item()
        
        self.model.train()
        return total_loss / len(self.val_dataloader)


# ==================== 使用示例 ====================

def demo_optimization():
    """演示性能优化"""
    print("="*60)
    print("MiniMind 性能优化演示")
    print("="*60)
    
    # 打印初始内存
    MemoryOptimizer.print_memory_stats("初始")
    
    # 创建模型
    from model import Transformer
    
    model = Transformer(
        dim=512,
        n_layers=8,
        n_heads=8,
        vocab_size=6400
    )
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = model.to(device)
    
    # 运行基准测试
    benchmark = PerformanceBenchmark(model, device)
    
    print("\n前向传播基准测试:")
    forward_result = benchmark.benchmark_forward()
    print(f"  平均时间: {forward_result['avg_time_ms']:.2f} ms")
    print(f"  吞吐量: {forward_result['throughput']:.2f} samples/s")
    
    print("\n训练步骤基准测试:")
    training_result = benchmark.benchmark_training()
    print(f"  平均时间: {training_result['avg_time_ms']:.2f} ms")
    
    MemoryOptimizer.print_memory_stats("测试后")


if __name__ == "__main__":
    demo_optimization()
```

### 46.2 推理性能优化

```python
"""
MiniMind 推理性能优化实践
==========================

优化模型推理速度和吞吐量。

优化技术：
- KV Cache优化
- 批处理推理
- 模型量化
- 推理引擎优化
"""

import torch
import torch.nn as nn
from typing import List, Optional, Dict, Tuple
import time
import numpy as np
from dataclasses import dataclass


# ==================== KV Cache 优化 ====================

class OptimizedKVCache:
    """
    优化的KV Cache实现
    
    减少内存分配和拷贝开销。
    """
    
    def __init__(
        self,
        num_layers: int,
        num_heads: int,
        head_dim: int,
        max_seq_len: int = 2048,
        dtype: torch.dtype = torch.float16
    ):
        self.num_layers = num_layers
        self.num_heads = num_heads
        self.head_dim = head_dim
        self.max_seq_len = max_seq_len
        self.dtype = dtype
        
        # 预分配缓存
        self.cache = None
        self.seq_len = 0
    
    def allocate(self, batch_size: int, device: torch.device):
        """预分配缓存内存"""
        self.cache = torch.zeros(
            2,  # K and V
            self.num_layers,
            batch_size,
            self.num_heads,
            self.max_seq_len,
            self.head_dim,
            dtype=self.dtype,
            device=device
        )
        self.seq_len = 0
    
    def update(
        self,
        layer_idx: int,
        key: torch.Tensor,
        value: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        更新缓存
        
        参数：
        - layer_idx: 层索引
        - key: 新的key (batch, heads, 1, head_dim)
        - value: 新的value (batch, heads, 1, head_dim)
        
        返回：
        - 完整的key和value
        """
        # 存储新的KV
        self.cache[0, layer_idx, :, :, self.seq_len:self.seq_len+1, :] = key
        self.cache[1, layer_idx, :, :, self.seq_len:self.seq_len+1, :] = value
        
        # 返回完整KV
        return (
            self.cache[0, layer_idx, :, :, :self.seq_len+1, :],
            self.cache[1, layer_idx, :, :, :self.seq_len+1, :]
        )
    
    def increment(self):
        """增加序列长度"""
        self.seq_len += 1
    
    def clear(self):
        """清空缓存"""
        if self.cache is not None:
            self.cache.zero_()
        self.seq_len = 0


class PagedKVCache:
    """
    分页KV Cache
    
    支持多个序列的高效内存管理。
    
    原理：
    - 将KV Cache分成固定大小的页
    - 按需分配页
    - 支持内存共享（如beam search）
    """
    
    def __init__(
        self,
        num_layers: int,
        num_heads: int,
        head_dim: int,
        page_size: int = 16,
        num_pages: int = 1024,
        dtype: torch.dtype = torch.float16
    ):
        self.num_layers = num_layers
        self.num_heads = num_heads
        self.head_dim = head_dim
        self.page_size = page_size
        self.num_pages = num_pages
        self.dtype = dtype
        
        # 页表
        self.page_table: Dict[int, List[int]] = {}  # seq_id -> page_ids
        self.free_pages: List[int] = list(range(num_pages))
        
        # 预分配内存池
        self.memory_pool = None
    
    def allocate_pool(self, device: torch.device):
        """分配内存池"""
        self.memory_pool = torch.zeros(
            2,  # K and V
            self.num_layers,
            self.num_pages,
            self.num_heads,
            self.page_size,
            self.head_dim,
            dtype=self.dtype,
            device=device
        )
    
    def allocate_sequence(self, seq_id: int) -> bool:
        """为序列分配第一个页"""
        if not self.free_pages:
            return False
        
        page_id = self.free_pages.pop()
        self.page_table[seq_id] = [page_id]
        return True
    
    def get_cache(self, seq_id: int, layer_idx: int):
        """获取序列的缓存"""
        page_ids = self.page_table.get(seq_id, [])
        if not page_ids:
            return None, None
        
        # 收集所有页
        keys = []
        values = []
        
        for page_id in page_ids:
            keys.append(self.memory_pool[0, layer_idx, page_id])
            values.append(self.memory_pool[1, layer_idx, page_id])
        
        return torch.cat(keys, dim=1), torch.cat(values, dim=1)
    
    def free_sequence(self, seq_id: int):
        """释放序列的页"""
        if seq_id in self.page_table:
            self.free_pages.extend(self.page_table[seq_id])
            del self.page_table[seq_id]


# ==================== 批处理推理 ====================

class BatchedInference:
    """
    批处理推理引擎
    
    高效处理多个并发请求。
    """
    
    def __init__(
        self,
        model: nn.Module,
        max_batch_size: int = 32,
        max_seq_len: int = 2048,
        pad_token_id: int = 0
    ):
        self.model = model
        self.max_batch_size = max_batch_size
        self.max_seq_len = max_seq_len
        self.pad_token_id = pad_token_id
        self.device = next(model.parameters()).device
    
    def generate_batch(
        self,
        prompts: List[List[int]],
        max_new_tokens: int = 100,
        temperature: float = 1.0,
        top_k: int = 50,
        top_p: float = 0.9
    ) -> List[List[int]]:
        """
        批量生成
        
        参数：
        - prompts: 输入提示列表
        - max_new_tokens: 最大生成token数
        - temperature: 温度参数
        - top_k: Top-K采样
        - top_p: Top-P采样
        
        返回：
        - 生成的序列列表
        """
        batch_size = len(prompts)
        
        # 填充到相同长度
        max_prompt_len = max(len(p) for p in prompts)
        padded_prompts = []
        attention_masks = []
        
        for prompt in prompts:
            pad_len = max_prompt_len - len(prompt)
            padded_prompts.append([self.pad_token_id] * pad_len + prompt)
            attention_masks.append([0] * pad_len + [1] * len(prompt))
        
        # 转换为张量
        input_ids = torch.tensor(padded_prompts, device=self.device)
        attention_mask = torch.tensor(attention_masks, device=self.device)
        
        # 生成
        generated = input_ids.clone()
        
        for _ in range(max_new_tokens):
            # 前向传播
            with torch.no_grad():
                outputs = self.model(generated)
            
            # 获取下一个token
            next_token_logits = outputs[:, -1, :]
            
            # 应用attention mask
            next_token_logits = next_token_logits / temperature
            
            # Top-K
            if top_k > 0:
                indices_to_remove = next_token_logits < torch.topk(next_token_logits, top_k)[0][..., -1, None]
                next_token_logits[indices_to_remove] = float('-inf')
            
            # Top-P
            if top_p < 1.0:
                sorted_logits, sorted_indices = torch.sort(next_token_logits, descending=True)
                cumulative_probs = torch.cumsum(torch.softmax(sorted_logits, dim=-1), dim=-1)
                sorted_indices_to_remove = cumulative_probs > top_p
                sorted_indices_to_remove[..., 1:] = sorted_indices_to_remove[..., :-1].clone()
                sorted_indices_to_remove[..., 0] = 0
                indices_to_remove = sorted_indices_to_remove.scatter(1, sorted_indices, sorted_indices_to_remove)
                next_token_logits[indices_to_remove] = float('-inf')
            
            # 采样
            probs = torch.softmax(next_token_logits, dim=-1)
            next_tokens = torch.multinomial(probs, num_samples=1)
            
            # 追加
            generated = torch.cat([generated, next_tokens], dim=-1)
            attention_mask = torch.cat([
                attention_mask,
                torch.ones(batch_size, 1, device=self.device)
            ], dim=-1)
            
            # 检查是否所有序列都结束
            # (这里简化处理，实际应该检查EOS token)
        
        # 移除填充，返回结果
        results = []
        for i, seq in enumerate(generated):
            # 找到原始prompt的结束位置
            prompt_len = len(prompts[i])
            result = seq[max_prompt_len - prompt_len:].tolist()
            results.append(result)
        
        return results


# ==================== 连续批处理 ====================

class ContinuousBatching:
    """
    连续批处理
    
    动态调度请求，提高GPU利用率。
    
    原理：
    - 不等待所有序列生成完成
    - 完成的序列立即移除
    - 新请求立即加入
    """
    
    def __init__(
        self,
        model: nn.Module,
        max_batch_size: int = 32,
        max_seq_len: int = 2048
    ):
        self.model = model
        self.max_batch_size = max_batch_size
        self.max_seq_len = max_seq_len
        self.device = next(model.parameters()).device
        
        # 请求队列
        self.pending_requests = []
        self.active_sequences = {}
        self.completed_sequences = {}
        self.next_seq_id = 0
    
    def add_request(self, prompt: List[int], max_new_tokens: int = 100) -> int:
        """添加生成请求"""
        seq_id = self.next_seq_id
        self.next_seq_id += 1
        
        self.pending_requests.append({
            'seq_id': seq_id,
            'prompt': prompt,
            'max_new_tokens': max_new_tokens,
            'generated': [],
            'current_pos': len(prompt)
        })
        
        return seq_id
    
    def step(self) -> Dict[int, List[int]]:
        """
        执行一步生成
        
        返回：
        - 完成的序列 {seq_id: generated_tokens}
        """
        # 填充批次
        while len(self.active_sequences) < self.max_batch_size and self.pending_requests:
            request = self.pending_requests.pop(0)
            self.active_sequences[request['seq_id']] = request
        
        if not self.active_sequences:
            return {}
        
        # 准备输入
        seq_ids = list(self.active_sequences.keys())
        sequences = [self.active_sequences[sid] for sid in seq_ids]
        
        # 填充到相同长度
        max_len = max(s['current_pos'] for s in sequences)
        input_ids = torch.zeros(len(sequences), max_len, dtype=torch.long, device=self.device)
        
        for i, seq in enumerate(sequences):
            prompt = seq['prompt'] + seq['generated']
            input_ids[i, -len(prompt):] = torch.tensor(prompt, device=self.device)
        
        # 前向传播
        with torch.no_grad():
            outputs = self.model(input_ids)
        
        # 获取下一个token
        next_token_logits = outputs[:, -1, :]
        next_tokens = torch.argmax(next_token_logits, dim=-1)
        
        # 更新序列
        completed = {}
        
        for i, (seq_id, seq) in enumerate(zip(seq_ids, sequences)):
            token = next_tokens[i].item()
            seq['generated'].append(token)
            seq['current_pos'] += 1
            
            # 检查是否完成
            if len(seq['generated']) >= seq['max_new_tokens']:
                completed[seq_id] = seq['prompt'] + seq['generated']
                del self.active_sequences[seq_id]
        
        return completed
    
    def generate_all(self) -> Dict[int, List[int]]:
        """生成所有请求"""
        results = {}
        
        while self.active_sequences or self.pending_requests:
            completed = self.step()
            results.update(completed)
        
        return results


# ==================== 推理优化配置 ====================

@dataclass
class InferenceConfig:
    """推理配置"""
    # 基本配置
    max_batch_size: int = 32
    max_seq_len: int = 2048
    max_new_tokens: int = 512
    
    # 采样配置
    temperature: float = 1.0
    top_k: int = 50
    top_p: float = 0.9
    repetition_penalty: float = 1.0
    
    # 优化配置
    use_kv_cache: bool = True
    use_paged_cache: bool = False
    use_continuous_batching: bool = False
    
    # 量化配置
    quantize: bool = False
    quantize_bits: int = 8


class OptimizedInferenceEngine:
    """
    优化的推理引擎
    
    整合所有推理优化技术。
    """
    
    def __init__(self, model: nn.Module, config: InferenceConfig):
        self.model = model
        self.config = config
        self.device = next(model.parameters()).device
        
        # 初始化KV Cache
        if config.use_kv_cache:
            if config.use_paged_cache:
                self.kv_cache = PagedKVCache(
                    num_layers=model.n_layers,
                    num_heads=model.n_heads,
                    head_dim=model.dim // model.n_heads
                )
            else:
                self.kv_cache = OptimizedKVCache(
                    num_layers=model.n_layers,
                    num_heads=model.n_heads,
                    head_dim=model.dim // model.n_heads
                )
        else:
            self.kv_cache = None
        
        # 初始化批处理器
        if config.use_continuous_batching:
            self.batcher = ContinuousBatching(
                model,
                max_batch_size=config.max_batch_size
            )
        else:
            self.batcher = BatchedInference(
                model,
                max_batch_size=config.max_batch_size
            )
    
    def generate(
        self,
        prompt: List[int],
        max_new_tokens: int = None
    ) -> List[int]:
        """单个序列生成"""
        max_new_tokens = max_new_tokens or self.config.max_new_tokens
        
        input_ids = torch.tensor([prompt], device=self.device)
        generated = input_ids.clone()
        
        # 初始化KV Cache
        if self.kv_cache:
            self.kv_cache.allocate(1, self.device)
        
        for _ in range(max_new_tokens):
            with torch.no_grad():
                outputs = self.model(generated)
            
            next_token = self._sample_next_token(outputs[:, -1, :])
            generated = torch.cat([generated, next_token.unsqueeze(0)], dim=-1)
        
        return generated[0].tolist()
    
    def generate_batch(
        self,
        prompts: List[List[int]],
        max_new_tokens: int = None
    ) -> List[List[int]]:
        """批量生成"""
        max_new_tokens = max_new_tokens or self.config.max_new_tokens
        
        return self.batcher.generate_batch(
            prompts,
            max_new_tokens=max_new_tokens,
            temperature=self.config.temperature,
            top_k=self.config.top_k,
            top_p=self.config.top_p
        )
    
    def _sample_next_token(self, logits: torch.Tensor) -> int:
        """采样下一个token"""
        logits = logits / self.config.temperature
        
        # Top-K
        if self.config.top_k > 0:
            top_k_logits, top_k_indices = torch.topk(logits, self.config.top_k)
            logits = torch.full_like(logits, float('-inf'))
            logits.scatter_(1, top_k_indices, top_k_logits)
        
        # Top-P
        if self.config.top_p < 1.0:
            sorted_logits, sorted_indices = torch.sort(logits, descending=True)
            cumulative_probs = torch.cumsum(torch.softmax(sorted_logits, dim=-1), dim=-1)
            sorted_indices_to_remove = cumulative_probs > self.config.top_p
            sorted_indices_to_remove[..., 1:] = sorted_indices_to_remove[..., :-1].clone()
            sorted_indices_to_remove[..., 0] = 0
            indices_to_remove = sorted_indices_to_remove.scatter(1, sorted_indices, sorted_indices_to_remove)
            logits[indices_to_remove] = float('-inf')
        
        probs = torch.softmax(logits, dim=-1)
        next_token = torch.multinomial(probs, num_samples=1)
        
        return next_token.item()


# ==================== 推理性能测试 ====================

class InferenceBenchmark:
    """推理性能基准测试"""
    
    def __init__(self, engine: OptimizedInferenceEngine):
        self.engine = engine
    
    def benchmark_latency(
        self,
        prompt_len: int = 128,
        output_len: int = 100,
        num_iterations: int = 10
    ) -> Dict:
        """测试延迟"""
        prompt = list(range(prompt_len))
        
        latencies = []
        
        for _ in range(num_iterations):
            start = time.perf_counter()
            _ = self.engine.generate(prompt, max_new_tokens=output_len)
            end = time.perf_counter()
            
            latencies.append(end - start)
        
        return {
            'mean_latency': np.mean(latencies),
            'std_latency': np.std(latencies),
            'min_latency': np.min(latencies),
            'max_latency': np.max(latencies),
            'tokens_per_second': output_len / np.mean(latencies)
        }
    
    def benchmark_throughput(
        self,
        batch_sizes: List[int] = [1, 2, 4, 8, 16, 32],
        prompt_len: int = 128,
        output_len: int = 100
    ) -> Dict:
        """测试吞吐量"""
        results = {}
        
        for batch_size in batch_sizes:
            prompts = [list(range(prompt_len)) for _ in range(batch_size)]
            
            start = time.perf_counter()
            _ = self.engine.generate_batch(prompts, max_new_tokens=output_len)
            end = time.perf_counter()
            
            total_time = end - start
            total_tokens = batch_size * output_len
            throughput = total_tokens / total_time
            
            results[batch_size] = {
                'total_time': total_time,
                'throughput': throughput,
                'latency_per_request': total_time / batch_size
            }
        
        return results
    
    def print_results(self, latency_results: Dict, throughput_results: Dict):
        """打印结果"""
        print("\n" + "="*60)
        print("推理性能测试结果")
        print("="*60)
        
        print("\n延迟测试:")
        print(f"  平均延迟: {latency_results['mean_latency']*1000:.2f} ms")
        print(f"  标准差: {latency_results['std_latency']*1000:.2f} ms")
        print(f"  吞吐量: {latency_results['tokens_per_second']:.2f} tokens/s")
        
        print("\n批处理吞吐量测试:")
        print(f"{'Batch Size':<12} {'Throughput':<15} {'Latency/Req':<15}")
        print("-"*45)
        
        for batch_size, result in throughput_results.items():
            print(f"{batch_size:<12} {result['throughput']:<15.2f} {result['latency_per_request']*1000:<15.2f}")


# ==================== 使用示例 ====================

def demo_inference_optimization():
    """演示推理优化"""
    print("="*60)
    print("MiniMind 推理优化演示")
    print("="*60)
    
    # 创建配置
    config = InferenceConfig(
        max_batch_size=16,
        use_kv_cache=True,
        temperature=0.8,
        top_k=50,
        top_p=0.9
    )
    
    print(f"\n推理配置:")
    print(f"  最大批大小: {config.max_batch_size}")
    print(f"  使用KV Cache: {config.use_kv_cache}")
    print(f"  温度: {config.temperature}")
    print(f"  Top-K: {config.top_k}")
    print(f"  Top-P: {config.top_p}")
    
    # 这里需要实际加载模型
    # from model import Transformer
    # model = Transformer(...)
    # engine = OptimizedInferenceEngine(model, config)
    # benchmark = InferenceBenchmark(engine)
    # latency_results = benchmark.benchmark_latency()
    # throughput_results = benchmark.benchmark_throughput()
    # benchmark.print_results(latency_results, throughput_results)
    
    print("\n推理优化演示完成!")


if __name__ == "__main__":
    demo_inference_optimization()
```

---

## 四十七、模型压缩与量化项目

### 47.1 模型量化实现

```python
"""
MiniMind 模型量化实现
=====================

实现多种量化技术以减少模型大小和加速推理。

量化技术：
- 动态量化
- 静态量化
- 量化感知训练 (QAT)
- GPTQ量化
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, List, Optional, Tuple, Union
import numpy as np
from dataclasses import dataclass
import os


# ==================== 量化基础类 ====================

@dataclass
class QuantizationConfig:
    """量化配置"""
    bits: int = 8  # 量化位数
    symmetric: bool = True  # 是否对称量化
    per_channel: bool = False  # 是否按通道量化
    dynamic: bool = True  # 是否动态量化
    
    # 校准配置
    calibration_samples: int = 128
    calibration_method: str = "minmax"  # minmax, percentile, entropy


class Quantizer:
    """
    基础量化器
    
    实现量化和反量化的基本操作。
    """
    
    def __init__(self, config: QuantizationConfig):
        self.config = config
        self.scale = None
        self.zero_point = None
    
    def quantize(self, x: torch.Tensor) -> torch.Tensor:
        """
        量化操作
        
        公式: x_q = round(x / scale) + zero_point
        """
        if self.config.symmetric:
            # 对称量化
            max_val = x.abs().max()
            self.scale = max_val / (2 ** (self.config.bits - 1) - 1)
            self.zero_point = 0
        else:
            # 非对称量化
            min_val = x.min()
            max_val = x.max()
            qmin = 0
            qmax = 2 ** self.config.bits - 1
            
            self.scale = (max_val - min_val) / (qmax - qmin)
            self.zero_point = qmin - min_val / self.scale
        
        # 量化
        x_q = torch.round(x / self.scale) + self.zero_point
        
        # 截断
        qmin = -(2 ** (self.config.bits - 1)) if self.config.symmetric else 0
        qmax = 2 ** (self.config.bits - 1) - 1 if self.config.symmetric else 2 ** self.config.bits - 1
        
        x_q = torch.clamp(x_q, qmin, qmax)
        
        return x_q.to(torch.int8 if self.config.bits == 8 else torch.int32)
    
    def dequantize(self, x_q: torch.Tensor) -> torch.Tensor:
        """
        反量化操作
        
        公式: x = (x_q - zero_point) * scale
        """
        return (x_q.float() - self.zero_point) * self.scale


# ==================== 动态量化 ====================

class DynamicQuantizedLinear(nn.Module):
    """
    动态量化线性层
    
    权重预先量化，激活在推理时动态量化。
    
    优势：
    - 无需校准数据
    - 实现简单
    - 适合RNN/Transformer
    
    劣势：
    - 激活量化开销
    - 精度略低于静态量化
    """
    
    def __init__(
        self,
        in_features: int,
        out_features: int,
        bias: bool = True,
        bits: int = 8
    ):
        super().__init__()
        
        self.in_features = in_features
        self.out_features = out_features
        self.bits = bits
        
        # 量化权重
        self.weight = nn.Parameter(torch.empty(out_features, in_features))
        self.weight_scale = nn.Parameter(torch.ones(out_features))
        
        if bias:
            self.bias = nn.Parameter(torch.empty(out_features))
        else:
            self.register_parameter('bias', None)
        
        self._init_weights()
    
    def _init_weights(self):
        nn.init.kaiming_uniform_(self.weight)
        if self.bias is not None:
            nn.init.zeros_(self.bias)
    
    def quantize_weight(self):
        """量化权重"""
        with torch.no_grad():
            max_val = self.weight.abs().max(dim=1, keepdim=True)[0]
            self.weight_scale.data = max_val.squeeze() / 127.0
            
            weight_q = torch.round(self.weight / max_val * 127).clamp(-128, 127)
            self.weight.data = weight_q
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """前向传播"""
        # 反量化权重
        weight_fp = self.weight.float() * self.weight_scale.float().unsqueeze(1)
        
        # 动态量化激活
        x_scale = x.abs().max() / 127.0
        x_q = torch.round(x / x_scale).clamp(-128, 127).float()
        
        # 计算
        output = F.linear(x_q, weight_fp, self.bias)
        
        # 反量化输出
        output = output * x_scale
        
        return output


def dynamic_quantize_model(model: nn.Module, bits: int = 8) -> nn.Module:
    """
    对模型应用动态量化
    
    参数：
    - model: 原始模型
    - bits: 量化位数
    
    返回：
    - 量化后的模型
    """
    quantized_model = model
    
    for name, module in model.named_modules():
        if isinstance(module, nn.Linear):
            # 创建量化层
            quantized_linear = DynamicQuantizedLinear(
                module.in_features,
                module.out_features,
                module.bias is not None,
                bits
            )
            
            # 复制权重
            quantized_linear.weight.data = module.weight.data
            if module.bias is not None:
                quantized_linear.bias.data = module.bias.data
            
            # 量化权重
            quantized_linear.quantize_weight()
            
            # 替换
            parts = name.rsplit('.', 1)
            if len(parts) == 2:
                parent = model.get_submodule(parts[0])
                setattr(parent, parts[1], quantized_linear)
            else:
                setattr(model, name, quantized_linear)
    
    return quantized_model


# ==================== 静态量化 ====================

class StaticQuantizedLinear(nn.Module):
    """
    静态量化线性层
    
    权重和激活都预先量化。
    
    优势：
    - 推理速度最快
    - 适合部署
    
    劣势：
    - 需要校准数据
    - 实现复杂
    """
    
    def __init__(
        self,
        in_features: int,
        out_features: int,
        bias: bool = True,
        bits: int = 8
    ):
        super().__init__()
        
        self.in_features = in_features
        self.out_features = out_features
        self.bits = bits
        
        # 量化权重
        self.weight = nn.Parameter(torch.empty(out_features, in_features))
        self.weight_scale = nn.Parameter(torch.ones(out_features))
        
        # 激活量化参数
        self.input_scale = nn.Parameter(torch.ones(1))
        self.input_zero_point = nn.Parameter(torch.zeros(1))
        
        if bias:
            self.bias = nn.Parameter(torch.empty(out_features))
        else:
            self.register_parameter('bias', None)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """前向传播"""
        # 量化输入
        x_q = torch.round(x / self.input_scale + self.input_zero_point)
        x_q = x_q.clamp(0, 255).to(torch.uint8)
        
        # 反量化权重
        weight_fp = self.weight.float() * self.weight_scale.float().unsqueeze(1)
        
        # 计算
        output = F.linear(x_q.float(), weight_fp, self.bias)
        
        return output


class CalibrationCollector:
    """
    校准数据收集器
    
    收集激活统计信息用于静态量化。
    """
    
    def __init__(self, model: nn.Module):
        self.model = model
        self.hooks = []
        self.activations = {}
    
    def register_hooks(self):
        """注册钩子收集激活"""
        def make_hook(name):
            def hook(module, input, output):
                if name not in self.activations:
                    self.activations[name] = []
                self.activations[name].append(input[0].detach())
            return hook
        
        for name, module in self.model.named_modules():
            if isinstance(module, nn.Linear):
                hook = module.register_forward_hook(make_hook(name))
                self.hooks.append(hook)
    
    def collect(self, dataloader, num_samples: int = 128):
        """收集校准数据"""
        self.register_hooks()
        
        self.model.eval()
        sample_count = 0
        
        with torch.no_grad():
            for batch in dataloader:
                if sample_count >= num_samples:
                    break
                
                self.model(batch['input_ids'])
                sample_count += len(batch['input_ids'])
        
        # 移除钩子
        for hook in self.hooks:
            hook.remove()
        
        return self.activations
    
    def compute_scales(self, method: str = "minmax") -> Dict:
        """计算量化缩放因子"""
        scales = {}
        
        for name, acts in self.activations.items():
            all_acts = torch.cat(acts, dim=0)
            
            if method == "minmax":
                min_val = all_acts.min()
                max_val = all_acts.max()
                scale = (max_val - min_val) / 255
                zero_point = -min_val / scale
            elif method == "percentile":
                min_val = torch.quantile(all_acts, 0.01)
                max_val = torch.quantile(all_acts, 0.99)
                scale = (max_val - min_val) / 255
                zero_point = -min_val / scale
            else:  # entropy
                # 使用KL散度找最佳阈值
                scale, zero_point = self._entropy_calibration(all_acts)
            
            scales[name] = {
                'scale': scale,
                'zero_point': zero_point
            }
        
        return scales
    
    def _entropy_calibration(self, activations: torch.Tensor) -> Tuple[float, float]:
        """基于熵的校准"""
        # 简化实现
        min_val = activations.min()
        max_val = activations.max()
        scale = (max_val - min_val) / 255
        zero_point = -min_val / scale
        return scale, zero_point


# ==================== GPTQ 量化 ====================

class GPTQQuantizer:
    """
    GPTQ 量化器
    
    论文: GPTQ: Accurate Post-Training Quantization for Generative Pre-trained Transformers
    
    原理：
    - 基于最优脑量化 (OBQ)
    - 逐层量化
    - 使用Hessian矩阵信息
    
    优势：
    - 高精度
    - 适合大模型
    - 无需重训练
    """
    
    def __init__(
        self,
        bits: int = 4,
        groupsize: int = 128,
        actorder: bool = True,
        perchannel: bool = True
    ):
        self.bits = bits
        self.groupsize = groupsize
        self.actorder = actorder
        self.perchannel = perchannel
    
    def quantize_layer(
        self,
        layer: nn.Linear,
        inputs: torch.Tensor
    ) -> Tuple[torch.Tensor, Dict]:
        """
        量化单个层
        
        参数：
        - layer: 要量化的线性层
        - inputs: 校准输入
        
        返回：
        - 量化后的权重
        - 量化参数
        """
        W = layer.weight.data.float()
        H = inputs.t() @ inputs  # Hessian
        
        # 添加阻尼
        damp = 0.01 * torch.diag(H).mean()
        H = H + damp * torch.eye(H.shape[0], device=H.device)
        
        # Cholesky分解
        H_inv = torch.linalg.cholesky(H)
        H_inv = torch.cholesky_inverse(H_inv)
        H_inv = torch.linalg.cholesky(H_inv, upper=True)
        
        # 量化参数
        quant_params = {
            'scale': [],
            'zero': []
        }
        
        W_q = W.clone()
        
        # 逐列量化
        for i in range(W.shape[1]):
            # 计算量化参数
            w = W[:, i]
            
            if self.perchannel:
                scale = w.abs().max() / (2 ** (self.bits - 1) - 1)
                zero = 0
            else:
                # 分组量化
                scale, zero = self._compute_group_params(w)
            
            quant_params['scale'].append(scale)
            quant_params['zero'].append(zero)
            
            # 量化
            w_q = torch.round(w / scale).clamp(
                -(2 ** (self.bits - 1)),
                2 ** (self.bits - 1) - 1
            )
            
            # 计算量化误差
            q_err = (w - w_q * scale) / H_inv[i, i]
            
            # 更新权重
            W_q[:, i] = w_q
            
            # 更新剩余权重
            W[:, i:] -= q_err.unsqueeze(1) * H_inv[i, i:].unsqueeze(0)
        
        return W_q, quant_params
    
    def _compute_group_params(self, w: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """计算分组量化参数"""
        groups = w.split(self.groupsize)
        
        scales = []
        zeros = []
        
        for g in groups:
            scale = g.abs().max() / (2 ** (self.bits - 1) - 1)
            zero = 0
            scales.append(scale)
            zeros.append(zero)
        
        return torch.tensor(scales), torch.tensor(zeros)
    
    def quantize_model(
        self,
        model: nn.Module,
        dataloader,
        num_samples: int = 128
    ):
        """量化整个模型"""
        print("开始GPTQ量化...")
        
        # 收集各层输入
        layer_inputs = self._collect_layer_inputs(model, dataloader, num_samples)
        
        # 逐层量化
        for name, module in model.named_modules():
            if isinstance(module, nn.Linear):
                if name in layer_inputs:
                    print(f"量化层: {name}")
                    W_q, params = self.quantize_layer(module, layer_inputs[name])
                    module.weight.data = W_q
        
        print("GPTQ量化完成!")
        return model
    
    def _collect_layer_inputs(
        self,
        model: nn.Module,
        dataloader,
        num_samples: int
    ) -> Dict[str, torch.Tensor]:
        """收集各层输入"""
        inputs = {}
        hooks = []
        
        def make_hook(name):
            def hook(module, inp, out):
                if name not in inputs:
                    inputs[name] = []
                inputs[name].append(inp[0].detach())
            return hook
        
        for name, module in model.named_modules():
            if isinstance(module, nn.Linear):
                hook = module.register_forward_hook(make_hook(name))
                hooks.append(hook)
        
        # 运行校准数据
        model.eval()
        sample_count = 0
        
        with torch.no_grad():
            for batch in dataloader:
                if sample_count >= num_samples:
                    break
                model(batch['input_ids'])
                sample_count += len(batch['input_ids'])
        
        # 移除钩子
        for hook in hooks:
            hook.remove()
        
        # 合并输入
        for name in inputs:
            inputs[name] = torch.cat(inputs[name], dim=0)
        
        return inputs


# ==================== 量化感知训练 ====================

class FakeQuantize(nn.Module):
    """
    伪量化模块
    
    在训练时模拟量化效果，但使用浮点计算。
    """
    
    def __init__(
        self,
        bits: int = 8,
        symmetric: bool = True,
        per_channel: bool = False
    ):
        super().__init__()
        
        self.bits = bits
        self.symmetric = symmetric
        self.per_channel = per_channel
        
        self.scale = nn.Parameter(torch.ones(1))
        self.zero_point = nn.Parameter(torch.zeros(1))
        
        self.register_buffer('min_val', torch.tensor(0.0))
        self.register_buffer('max_val', torch.tensor(0.0))
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """前向传播（伪量化）"""
        if self.training:
            # 更新范围
            self.min_val.data = x.min()
            self.max_val.data = x.max()
        
        # 计算量化参数
        if self.symmetric:
            max_val = torch.max(self.min_val.abs(), self.max_val.abs())
            self.scale.data = max_val / (2 ** (self.bits - 1) - 1)
            self.zero_point.data = torch.zeros_like(self.scale)
        else:
            self.scale.data = (self.max_val - self.min_val) / (2 ** self.bits - 1)
            self.zero_point.data = -self.min_val / self.scale
        
        # 伪量化
        x_q = torch.round(x / self.scale + self.zero_point)
        
        # 截断
        qmin = -(2 ** (self.bits - 1)) if self.symmetric else 0
        qmax = 2 ** (self.bits - 1) - 1 if self.symmetric else 2 ** self.bits - 1
        x_q = torch.clamp(x_q, qmin, qmax)
        
        # 反量化
        x_dequant = (x_q - self.zero_point) * self.scale
        
        # 使用直通估计器
        return x + (x_dequant - x).detach()


class QuantAwareLinear(nn.Module):
    """
    量化感知线性层
    
    在训练时模拟量化，推理时使用量化计算。
    """
    
    def __init__(
        self,
        in_features: int,
        out_features: int,
        bias: bool = True,
        bits: int = 8
    ):
        super().__init__()
        
        self.in_features = in_features
        self.out_features = out_features
        
        self.weight = nn.Parameter(torch.empty(out_features, in_features))
        self.weight_quant = FakeQuantize(bits=bits)
        
        if bias:
            self.bias = nn.Parameter(torch.empty(out_features))
        else:
            self.register_parameter('bias', None)
        
        self._init_weights()
    
    def _init_weights(self):
        nn.init.kaiming_uniform_(self.weight)
        if self.bias is not None:
            nn.init.zeros_(self.bias)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """前向传播"""
        # 伪量化权重
        w_q = self.weight_quant(self.weight)
        
        return F.linear(x, w_q, self.bias)


# ==================== 量化效果评估 ====================

class QuantizationEvaluator:
    """
    量化效果评估器
    
    比较量化前后的模型性能。
    """
    
    def __init__(self, original_model: nn.Module, quantized_model: nn.Module):
        self.original = original_model
        self.quantized = quantized
    
    def compare_weights(self) -> Dict:
        """比较权重差异"""
        original_params = {}
        quantized_params = {}
        
        for name, param in self.original.named_parameters():
            original_params[name] = param.data
        
        for name, param in self.quantized.named_parameters():
            quantized_params[name] = param.data
        
        # 计算差异
        diff = {}
        for name in original_params:
            if name in quantized_params:
                o = original_params[name].float()
                q = quantized_params[name].float()
                
                diff[name] = {
                    'mse': F.mse_loss(o, q).item(),
                    'mae': F.l1_loss(o, q).item(),
                    'cosine_sim': F.cosine_similarity(
                        o.flatten().unsqueeze(0),
                        q.flatten().unsqueeze(0)
                    ).item()
                }
        
        return diff
    
    def compare_outputs(
        self,
        input_ids: torch.Tensor
    ) -> Dict:
        """比较输出差异"""
        self.original.eval()
        self.quantized.eval()
        
        with torch.no_grad():
            original_output = self.original(input_ids)
            quantized_output = self.quantized(input_ids)
        
        return {
            'mse': F.mse_loss(original_output, quantized_output).item(),
            'mae': F.l1_loss(original_output, quantized_output).item(),
            'max_diff': (original_output - quantized_output).abs().max().item()
        }
    
    def compare_size(self) -> Dict:
        """比较模型大小"""
        def get_size(model):
            total = 0
            for param in model.parameters():
                total += param.numel() * param.element_size()
            return total
        
        original_size = get_size(self.original)
        quantized_size = get_size(self.quantized)
        
        return {
            'original_size_mb': original_size / (1024 * 1024),
            'quantized_size_mb': quantized_size / (1024 * 1024),
            'compression_ratio': original_size / quantized_size
        }
    
    def evaluate_perplexity(
        self,
        dataloader,
        max_batches: int = 100
    ) -> Dict:
        """评估困惑度"""
        def compute_ppl(model, dataloader, max_batches):
            model.eval()
            total_loss = 0
            total_tokens = 0
            
            with torch.no_grad():
                for i, batch in enumerate(dataloader):
                    if i >= max_batches:
                        break
                    
                    input_ids = batch['input_ids']
                    labels = batch.get('labels', input_ids)
                    
                    outputs = model(input_ids)
                    
                    shift_outputs = outputs[..., :-1, :].contiguous()
                    shift_labels = labels[..., 1:].contiguous()
                    
                    loss = F.cross_entropy(
                        shift_outputs.view(-1, shift_outputs.size(-1)),
                        shift_labels.view(-1)
                    )
                    
                    total_loss += loss.item() * input_ids.numel()
                    total_tokens += input_ids.numel()
            
            return math.exp(total_loss / total_tokens)
        
        import math
        
        original_ppl = compute_ppl(self.original, dataloader, max_batches)
        quantized_ppl = compute_ppl(self.quantized, dataloader, max_batches)
        
        return {
            'original_ppl': original_ppl,
            'quantized_ppl': quantized_ppl,
            'ppl_increase': quantized_ppl - original_ppl,
            'ppl_increase_percent': (quantized_ppl - original_ppl) / original_ppl * 100
        }


# ==================== 使用示例 ====================

def demo_quantization():
    """演示量化流程"""
    print("="*60)
    print("MiniMind 模型量化演示")
    print("="*60)
    
    # 创建量化配置
    config = QuantizationConfig(
        bits=8,
        symmetric=True,
        dynamic=True
    )
    
    print(f"\n量化配置:")
    print(f"  位数: {config.bits}")
    print(f"  对称量化: {config.symmetric}")
    print(f"  动态量化: {config.dynamic}")
    
    # 这里需要实际加载模型
    # from model import Transformer
    # model = Transformer(...)
    
    # 动态量化
    # quantized_model = dynamic_quantize_model(model, bits=8)
    
    # 评估
    # evaluator = QuantizationEvaluator(model, quantized_model)
    # size_comparison = evaluator.compare_size()
    # print(f"\n模型大小:")
    # print(f"  原始: {size_comparison['original_size_mb']:.2f} MB")
    # print(f"  量化后: {size_comparison['quantized_size_mb']:.2f} MB")
    # print(f"  压缩比: {size_comparison['compression_ratio']:.2f}x")
    
    print("\n量化演示完成!")


if __name__ == "__main__":
    demo_quantization()
```

### 47.2 模型剪枝实现

```python
"""
MiniMind 模型剪枝实现
=====================

实现多种剪枝技术以减少模型参数。

剪枝技术：
- 非结构化剪枝
- 结构化剪枝
- 头剪枝
- 知识蒸馏
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, List, Optional, Tuple
import numpy as np
from dataclasses import dataclass
import math


# ==================== 剪枝配置 ====================

@dataclass
class PruningConfig:
    """剪枝配置"""
    pruning_type: str = "unstructured"  # unstructured, structured, head
    pruning_ratio: float = 0.3  # 剪枝比例
    pruning_method: str = "magnitude"  # magnitude, random, gradient
    
    # 渐进式剪枝
    iterative: bool = True
    initial_ratio: float = 0.1
    final_ratio: float = 0.5
    num_iterations: int = 5
    
    # 微调配置
    finetune_epochs: int = 3
    finetune_lr: float = 1e-5


# ==================== 幅度剪枝 ====================

class MagnitudePruner:
    """
    幅度剪枝器
    
    基于权重幅度进行剪枝。
    
    原理：
    - 小权重对输出影响小
    - 移除小权重可以减少参数
    - 通常使用L1或L2范数
    """
    
    def __init__(self, model: nn.Module, config: PruningConfig):
        self.model = model
        self.config = config
        self.masks = {}
    
    def compute_masks(self, ratio: float) -> Dict[str, torch.Tensor]:
        """计算剪枝掩码"""
        masks = {}
        
        for name, param in self.model.named_parameters():
            if 'weight' in name and param.dim() >= 2:
                # 计算阈值
                flat = param.data.abs().flatten()
                threshold = torch.quantile(flat, ratio)
                
                # 创建掩码
                mask = (param.data.abs() > threshold).float()
                masks[name] = mask
        
        return masks
    
    def apply_masks(self, masks: Dict[str, torch.Tensor]):
        """应用掩码"""
        for name, param in self.model.named_parameters():
            if name in masks:
                param.data *= masks[name]
        
        self.masks = masks
    
    def prune(self, ratio: float):
        """执行剪枝"""
        masks = self.compute_masks(ratio)
        self.apply_masks(masks)
        
        # 统计稀疏度
        sparsity = self._compute_sparsity()
        print(f"剪枝完成，稀疏度: {sparsity:.2%}")
        
        return sparsity
    
    def _compute_sparsity(self) -> float:
        """计算稀疏度"""
        total_params = 0
        zero_params = 0
        
        for name, param in self.model.named_parameters():
            if name in self.masks:
                total_params += param.numel()
                zero_params += (param == 0).sum().item()
        
        return zero_params / total_params if total_params > 0 else 0


# ==================== 结构化剪枝 ====================

class StructuredPruner:
    """
    结构化剪枝器
    
    剪枝整个神经元或通道。
    
    优势：
    - 实际减少计算量
    - 加速推理
    
    劣势：
    - 精度损失可能更大
    - 需要调整网络结构
    """
    
    def __init__(self, model: nn.Module, config: PruningConfig):
        self.model = model
        self.config = config
        self.pruned_indices = {}
    
    def compute_importance(self, layer: nn.Linear) -> torch.Tensor:
        """计算神经元重要性"""
        # 使用L1范数
        importance = layer.weight.data.abs().sum(dim=1)
        return importance
    
    def prune_linear_layer(
        self,
        layer: nn.Linear,
        ratio: float
    ) -> Tuple[nn.Linear, torch.Tensor]:
        """
        剪枝线性层
        
        返回：
        - 剪枝后的层
        - 保留的索引
        """
        importance = self.compute_importance(layer)
        
        # 确定保留的神经元数
        num_neurons = layer.out_features
        num_keep = int(num_neurons * (1 - ratio))
        
        # 选择最重要的神经元
        _, indices = torch.topk(importance, num_keep)
        indices, _ = torch.sort(indices)
        
        # 创建新层
        new_layer = nn.Linear(
            layer.in_features,
            num_keep,
            bias=layer.bias is not None
        )
        
        # 复制权重
        new_layer.weight.data = layer.weight.data[indices]
        if layer.bias is not None:
            new_layer.bias.data = layer.bias.data[indices]
        
        return new_layer, indices
    
    def prune_model(self, ratio: float):
        """剪枝整个模型"""
        print(f"开始结构化剪枝，比例: {ratio:.2%}")
        
        for name, module in self.model.named_modules():
            if isinstance(module, nn.Linear):
                new_layer, indices = self.prune_linear_layer(module, ratio)
                
                # 替换层
                parts = name.rsplit('.', 1)
                if len(parts) == 2:
                    parent = self.model.get_submodule(parts[0])
                    setattr(parent, parts[1], new_layer)
                
                self.pruned_indices[name] = indices
        
        # 统计参数减少
        total_params = sum(p.numel() for p in self.model.parameters())
        print(f"剪枝完成，剩余参数: {total_params:,}")


# ==================== 注意力头剪枝 ====================

class HeadPruner:
    """
    注意力头剪枝器
    
    剪枝不重要的注意力头。
    
    原理：
    - 不同注意力头的重要性不同
    - 移除不重要的头可以减少计算
    """
    
    def __init__(self, model: nn.Module, config: PruningConfig):
        self.model = model
        self.config = config
        self.head_importance = {}
    
    def compute_head_importance(
        self,
        dataloader,
        num_samples: int = 100
    ):
        """计算注意力头重要性"""
        self.model.eval()
        
        # 注册钩子
        head_outputs = {}
        hooks = []
        
        def make_hook(layer_idx, head_idx):
            def hook(module, input, output):
                key = (layer_idx, head_idx)
                if key not in head_outputs:
                    head_outputs[key] = []
                head_outputs[key].append(output.detach())
            return hook
        
        # 收集输出
        sample_count = 0
        
        with torch.no_grad():
            for batch in dataloader:
                if sample_count >= num_samples:
                    break
                
                self.model(batch['input_ids'])
                sample_count += len(batch['input_ids'])
        
        # 计算重要性
        for key, outputs in head_outputs.items():
            all_outputs = torch.cat(outputs, dim=0)
            importance = all_outputs.abs().mean().item()
            self.head_importance[key] = importance
    
    def prune_heads(self, ratio: float):
        """剪枝注意力头"""
        if not self.head_importance:
            print("请先计算注意力头重要性")
            return
        
        # 排序
        sorted_heads = sorted(
            self.head_importance.items(),
            key=lambda x: x[1]
        )
        
        # 确定要剪枝的头数
        total_heads = len(sorted_heads)
        num_prune = int(total_heads * ratio)
        
        # 选择要剪枝的头
        heads_to_prune = [h[0] for h in sorted_heads[:num_prune]]
        
        print(f"剪枝 {num_prune} 个注意力头")
        
        # 实际剪枝需要修改模型结构
        # 这里简化处理，只是标记
        self.pruned_heads = heads_to_prune


# ==================== 知识蒸馏 ====================

class KnowledgeDistillation:
    """
    知识蒸馏
    
    从大模型（教师）向小模型（学生）迁移知识。
    
    原理：
    - 教师模型的软标签包含更多信息
    - 学生模型学习教师的输出分布
    """
    
    def __init__(
        self,
        teacher_model: nn.Module,
        student_model: nn.Module,
        temperature: float = 2.0,
        alpha: float = 0.5
    ):
        self.teacher = teacher_model
        self.student = student_model
        self.temperature = temperature
        self.alpha = alpha
        
        # 冻结教师模型
        for param in self.teacher.parameters():
            param.requires_grad = False
    
    def distillation_loss(
        self,
        student_outputs: torch.Tensor,
        teacher_outputs: torch.Tensor,
        labels: torch.Tensor
    ) -> torch.Tensor:
        """
        计算蒸馏损失
        
        参数：
        - student_outputs: 学生模型输出
        - teacher_outputs: 教师模型输出
        - labels: 真实标签
        """
        # 软标签损失
        soft_loss = F.kl_div(
            F.log_softmax(student_outputs / self.temperature, dim=-1),
            F.softmax(teacher_outputs / self.temperature, dim=-1),
            reduction='batchmean'
        ) * (self.temperature ** 2)
        
        # 硬标签损失
        hard_loss = F.cross_entropy(
            student_outputs.view(-1, student_outputs.size(-1)),
            labels.view(-1)
        )
        
        # 组合损失
        return self.alpha * soft_loss + (1 - self.alpha) * hard_loss
    
    def train_step(
        self,
        batch: Dict,
        student_optimizer: torch.optim.Optimizer
    ) -> float:
        """执行一步蒸馏训练"""
        self.teacher.eval()
        self.student.train()
        
        input_ids = batch['input_ids']
        labels = batch.get('labels', input_ids)
        
        # 教师输出
        with torch.no_grad():
            teacher_outputs = self.teacher(input_ids)
        
        # 学生输出
        student_outputs = self.student(input_ids)
        
        # 计算损失
        loss = self.distillation_loss(
            student_outputs,
            teacher_outputs,
            labels
        )
        
        # 反向传播
        student_optimizer.zero_grad()
        loss.backward()
        student_optimizer.step()
        
        return loss.item()


# ==================== 剪枝效果评估 ====================

class PruningEvaluator:
    """剪枝效果评估器"""
    
    def __init__(self, original_model: nn.Module, pruned_model: nn.Module):
        self.original = original_model
        self.pruned = pruned
    
    def compare_parameters(self) -> Dict:
        """比较参数量"""
        original_params = sum(p.numel() for p in self.original.parameters())
        pruned_params = sum(p.numel() for p in self.pruned.parameters())
        
        # 计算稀疏度
        original_nonzero = sum((p != 0).sum().item() for p in self.original.parameters())
        pruned_nonzero = sum((p != 0).sum().item() for p in self.pruned.parameters())
        
        return {
            'original_params': original_params,
            'pruned_params': pruned_params,
            'reduction_ratio': 1 - pruned_params / original_params,
            'original_nonzero': original_nonzero,
            'pruned_nonzero': pruned_nonzero,
            'sparsity': 1 - pruned_nonzero / pruned_params
        }
    
    def compare_inference_speed(
        self,
        input_shape: Tuple[int, int] = (1, 128),
        num_iterations: int = 100
    ) -> Dict:
        """比较推理速度"""
        import time
        
        device = next(self.original.parameters()).device
        input_ids = torch.randint(0, 1000, input_shape, device=device)
        
        # 预热
        for _ in range(10):
            with torch.no_grad():
                _ = self.original(input_ids)
                _ = self.pruned(input_ids)
        
        # 测试原始模型
        start = time.perf_counter()
        for _ in range(num_iterations):
            with torch.no_grad():
                _ = self.original(input_ids)
        original_time = time.perf_counter() - start
        
        # 测试剪枝模型
        start = time.perf_counter()
        for _ in range(num_iterations):
            with torch.no_grad():
                _ = self.pruned(input_ids)
        pruned_time = time.perf_counter() - start
        
        return {
            'original_time_ms': original_time / num_iterations * 1000,
            'pruned_time_ms': pruned_time / num_iterations * 1000,
            'speedup': original_time / pruned_time
        }
    
    def print_summary(self):
        """打印摘要"""
        params = self.compare_parameters()
        
        print("\n" + "="*60)
        print("剪枝效果评估")
        print("="*60)
        
        print(f"\n参数统计:")
        print(f"  原始参数: {params['original_params']:,}")
        print(f"  剪枝后参数: {params['pruned_params']:,}")
        print(f"  减少比例: {params['reduction_ratio']:.2%}")
        print(f"  稀疏度: {params['sparsity']:.2%}")


# ==================== 使用示例 ====================

def demo_pruning():
    """演示剪枝流程"""
    print("="*60)
    print("MiniMind 模型剪枝演示")
    print("="*60)
    
    # 创建配置
    config = PruningConfig(
        pruning_type="unstructured",
        pruning_ratio=0.3,
        pruning_method="magnitude"
    )
    
    print(f"\n剪枝配置:")
    print(f"  类型: {config.pruning_type}")
    print(f"  比例: {config.pruning_ratio:.2%}")
    print(f"  方法: {config.pruning_method}")
    
    # 这里需要实际加载模型
    # from model import Transformer
    # model = Transformer(...)
    
    # 创建剪枝器
    # pruner = MagnitudePruner(model, config)
    # pruner.prune(config.pruning_ratio)
    
    # 评估
    # evaluator = PruningEvaluator(original_model, model)
    # evaluator.print_summary()
    
    print("\n剪枝演示完成!")


if __name__ == "__main__":
    demo_pruning()
```

---

## 四十八、模型部署项目实践

### 48.1 模型导出与部署

```python
"""
MiniMind 模型部署实践
=====================

将训练好的模型部署到生产环境。

部署技术：
- ONNX导出
- TensorRT优化
- 服务化部署
- 边缘设备部署
"""

import torch
import torch.nn as nn
from typing import Dict, List, Optional, Tuple, Any
import json
import os
import time
from dataclasses import dataclass


# ==================== 模型导出 ====================

class ModelExporter:
    """
    模型导出器
    
    将PyTorch模型导出为不同格式。
    """
    
    def __init__(self, model: nn.Module):
        self.model = model
    
    def export_onnx(
        self,
        output_path: str,
        input_shape: Tuple[int, int] = (1, 128),
        opset_version: int = 14,
        dynamic_axes: bool = True
    ):
        """
        导出ONNX格式
        
        参数：
        - output_path: 输出路径
        - input_shape: 输入形状 (batch, seq_len)
        - opset_version: ONNX算子版本
        - dynamic_axes: 是否支持动态轴
        """
        self.model.eval()
        
        dummy_input = torch.randint(0, 1000, input_shape, dtype=torch.long)
        
        dynamic_axes_config = None
        if dynamic_axes:
            dynamic_axes_config = {
                'input_ids': {0: 'batch_size', 1: 'sequence'},
                'output': {0: 'batch_size', 1: 'sequence'}
            }
        
        torch.onnx.export(
            self.model,
            dummy_input,
            output_path,
            input_names=['input_ids'],
            output_names=['output'],
            dynamic_axes=dynamic_axes_config,
            opset_version=opset_version,
            do_constant_folding=True
        )
        
        print(f"ONNX模型已导出到: {output_path}")
    
    def export_torchscript(
        self,
        output_path: str,
        input_shape: Tuple[int, int] = (1, 128),
        method: str = "trace"
    ):
        """
        导出TorchScript格式
        
        参数：
        - output_path: 输出路径
        - input_shape: 输入形状
        - method: 导出方法 (trace或script)
        """
        self.model.eval()
        
        dummy_input = torch.randint(0, 1000, input_shape, dtype=torch.long)
        
        if method == "trace":
            scripted_model = torch.jit.trace(self.model, dummy_input)
        else:
            scripted_model = torch.jit.script(self.model)
        
        scripted_model.save(output_path)
        
        print(f"TorchScript模型已导出到: {output_path}")
    
    def export_weights(self, output_path: str):
        """导出权重"""
        state_dict = self.model.state_dict()
        torch.save(state_dict, output_path)
        print(f"权重已导出到: {output_path}")
    
    def export_config(self, output_path: str, config: Dict):
        """导出配置"""
        with open(output_path, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"配置已导出到: {output_path}")


# ==================== 模型优化 ====================

class ModelOptimizer:
    """
    模型优化器
    
    对导出的模型进行优化。
    """
    
    @staticmethod
    def optimize_onnx(
        input_path: str,
        output_path: str,
        optimize_level: str = "all"
    ):
        """
        优化ONNX模型
        
        参数：
        - input_path: 输入ONNX路径
        - output_path: 输出ONNX路径
        - optimize_level: 优化级别
        """
        try:
            import onnx
            from onnxoptimizer import optimize
            
            model = onnx.load(input_path)
            
            # 优化
            if optimize_level == "all":
                optimized = optimize(model)
            else:
                passes = ['eliminate_identity', 'eliminate_nop_transpose']
                optimized = optimize(model, passes)
            
            onnx.save(optimized, output_path)
            print(f"优化后的ONNX模型已保存到: {output_path}")
            
        except ImportError:
            print("请安装onnx和onnxoptimizer: pip install onnx onnxoptimizer")
    
    @staticmethod
    def convert_to_tensorrt(
        onnx_path: str,
        output_path: str,
        precision: str = "fp16",
        max_batch_size: int = 32,
        max_seq_len: int = 512
    ):
        """
        转换为TensorRT引擎
        
        参数：
        - onnx_path: ONNX模型路径
        - output_path: 输出路径
        - precision: 精度 (fp32, fp16, int8)
        - max_batch_size: 最大批大小
        - max_seq_len: 最大序列长度
        """
        try:
            import tensorrt as trt
            
            logger = trt.Logger(trt.Logger.WARNING)
            builder = trt.Builder(logger)
            network = builder.create_network(1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH))
            parser = trt.OnnxParser(network, logger)
            
            # 解析ONNX
            with open(onnx_path, 'rb') as f:
                parser.parse(f.read())
            
            # 配置
            config = builder.create_builder_config()
            
            if precision == "fp16":
                config.set_flag(trt.BuilderFlag.FP16)
            elif precision == "int8":
                config.set_flag(trt.BuilderFlag.INT8)
            
            # 设置最大工作空间
            config.set_memory_pool_limit(trt.MemoryPoolType.WORKSPACE, 1 << 30)  # 1GB
            
            # 构建引擎
            engine = builder.build_serialized_network(network, config)
            
            # 保存
            with open(output_path, 'wb') as f:
                f.write(engine)
            
            print(f"TensorRT引擎已保存到: {output_path}")
            
        except ImportError:
            print("请安装TensorRT: pip install tensorrt")


# ==================== 服务化部署 ====================

@dataclass
class ServerConfig:
    """服务配置"""
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4
    max_batch_size: int = 32
    max_seq_len: int = 512
    timeout: int = 30
    model_path: str = "./model.pt"
    device: str = "cuda"


class InferenceServer:
    """
    推理服务
    
    提供HTTP API进行模型推理。
    """
    
    def __init__(self, model: nn.Module, config: ServerConfig):
        self.model = model
        self.config = config
        self.device = torch.device(config.device)
        self.model.to(self.device)
        self.model.eval()
    
    def generate(
        self,
        prompt: str,
        max_new_tokens: int = 100,
        temperature: float = 1.0,
        top_k: int = 50,
        top_p: float = 0.9
    ) -> Dict:
        """
        生成文本
        
        参数：
        - prompt: 输入提示
        - max_new_tokens: 最大生成token数
        - temperature: 温度参数
        - top_k: Top-K采样
        - top_p: Top-P采样
        
        返回：
        - 生成结果
        """
        # 编码输入
        input_ids = self._encode(prompt)
        input_ids = torch.tensor([input_ids], device=self.device)
        
        # 生成
        start_time = time.time()
        
        with torch.no_grad():
            generated = self._generate_tokens(
                input_ids,
                max_new_tokens,
                temperature,
                top_k,
                top_p
            )
        
        # 解码
        generated_text = self._decode(generated[0].tolist())
        
        return {
            'generated_text': generated_text,
            'num_tokens': len(generated[0]),
            'latency_ms': (time.time() - start_time) * 1000
        }
    
    def _encode(self, text: str) -> List[int]:
        """编码文本"""
        # 简化实现，实际应使用tokenizer
        return [ord(c) for c in text]
    
    def _decode(self, tokens: List[int]) -> str:
        """解码token"""
        # 简化实现
        return ''.join(chr(t) if t < 128 else '?' for t in tokens)
    
    def _generate_tokens(
        self,
        input_ids: torch.Tensor,
        max_new_tokens: int,
        temperature: float,
        top_k: int,
        top_p: float
    ) -> torch.Tensor:
        """生成token"""
        generated = input_ids.clone()
        
        for _ in range(max_new_tokens):
            outputs = self.model(generated)
            next_token_logits = outputs[:, -1, :] / temperature
            
            # Top-K
            if top_k > 0:
                top_k_logits, top_k_indices = torch.topk(next_token_logits, top_k)
                next_token_logits = torch.full_like(next_token_logits, float('-inf'))
                next_token_logits.scatter_(1, top_k_indices, top_k_logits)
            
            # Top-P
            if top_p < 1.0:
                sorted_logits, sorted_indices = torch.sort(next_token_logits, descending=True)
                cumulative_probs = torch.cumsum(torch.softmax(sorted_logits, dim=-1), dim=-1)
                sorted_indices_to_remove = cumulative_probs > top_p
                sorted_indices_to_remove[..., 1:] = sorted_indices_to_remove[..., :-1].clone()
                sorted_indices_to_remove[..., 0] = 0
                indices_to_remove = sorted_indices_to_remove.scatter(1, sorted_indices, sorted_indices_to_remove)
                next_token_logits[indices_to_remove] = float('-inf')
            
            # 采样
            probs = torch.softmax(next_token_logits, dim=-1)
            next_token = torch.multinomial(probs, num_samples=1)
            
            generated = torch.cat([generated, next_token], dim=-1)
        
        return generated
    
    def batch_generate(
        self,
        prompts: List[str],
        max_new_tokens: int = 100,
        **kwargs
    ) -> List[Dict]:
        """批量生成"""
        results = []
        
        # 分批处理
        for i in range(0, len(prompts), self.config.max_batch_size):
            batch = prompts[i:i + self.config.max_batch_size]
            
            for prompt in batch:
                result = self.generate(prompt, max_new_tokens, **kwargs)
                results.append(result)
        
        return results


# ==================== FastAPI 服务 ====================

def create_fastapi_app(server: InferenceServer):
    """
    创建FastAPI应用
    
    使用示例：
    ```python
    app = create_fastapi_app(server)
    uvicorn.run(app, host="0.0.0.0", port=8000)
    ```
    """
    try:
        from fastapi import FastAPI, HTTPException
        from pydantic import BaseModel
        
        app = FastAPI(title="MiniMind API")
        
        class GenerateRequest(BaseModel):
            prompt: str
            max_new_tokens: int = 100
            temperature: float = 1.0
            top_k: int = 50
            top_p: float = 0.9
        
        class GenerateResponse(BaseModel):
            generated_text: str
            num_tokens: int
            latency_ms: float
        
        @app.post("/generate", response_model=GenerateResponse)
        async def generate(request: GenerateRequest):
            result = server.generate(
                request.prompt,
                request.max_new_tokens,
                request.temperature,
                request.top_k,
                request.top_p
            )
            return GenerateResponse(**result)
        
        @app.get("/health")
        async def health():
            return {"status": "healthy"}
        
        @app.get("/model/info")
        async def model_info():
            return {
                "model": "MiniMind",
                "parameters": sum(p.numel() for p in server.model.parameters())
            }
        
        return app
        
    except ImportError:
        print("请安装FastAPI: pip install fastapi uvicorn")
        return None


# ==================== 部署脚本 ====================

def deploy_model(
    model: nn.Module,
    output_dir: str,
    config: Dict
):
    """
    完整部署流程
    
    参数：
    - model: 要部署的模型
    - output_dir: 输出目录
    - config: 部署配置
    """
    os.makedirs(output_dir, exist_ok=True)
    
    print("="*60)
    print("MiniMind 模型部署")
    print("="*60)
    
    # 导出模型
    print("\n[1/4] 导出模型...")
    exporter = ModelExporter(model)
    
    exporter.export_onnx(
        os.path.join(output_dir, "model.onnx")
    )
    
    exporter.export_torchscript(
        os.path.join(output_dir, "model.pt")
    )
    
    exporter.export_weights(
        os.path.join(output_dir, "weights.pt")
    )
    
    exporter.export_config(
        os.path.join(output_dir, "config.json"),
        config
    )
    
    # 优化模型
    print("\n[2/4] 优化模型...")
    ModelOptimizer.optimize_onnx(
        os.path.join(output_dir, "model.onnx"),
        os.path.join(output_dir, "model_optimized.onnx")
    )
    
    # 创建服务配置
    print("\n[3/4] 创建服务配置...")
    server_config = ServerConfig(
        model_path=os.path.join(output_dir, "model.pt")
    )
    
    # 生成部署文档
    print("\n[4/4] 生成部署文档...")
    deployment_doc = f"""
# MiniMind 模型部署指南

## 模型文件

- `model.onnx`: ONNX格式模型
- `model_optimized.onnx`: 优化后的ONNX模型
- `model.pt`: TorchScript格式模型
- `weights.pt`: 模型权重
- `config.json`: 模型配置

## API服务

启动服务:
```bash
uvicorn server:app --host 0.0.0.0 --port 8000
```

### API端点

- POST `/generate`: 生成文本
- GET `/health`: 健康检查
- GET `/model/info`: 模型信息

### 示例请求

```bash
curl -X POST "http://localhost:8000/generate" \\
    -H "Content-Type: application/json" \\
    -d '{{"prompt": "你好", "max_new_tokens": 100}}'
```

## 性能优化建议

1. 使用FP16精度
2. 启用KV Cache
3. 使用批处理推理
4. 考虑TensorRT加速
"""
    
    with open(os.path.join(output_dir, "DEPLOYMENT.md"), 'w') as f:
        f.write(deployment_doc)
    
    print("\n" + "="*60)
    print("部署完成！")
    print(f"输出目录: {output_dir}")
    print("="*60)


# ==================== 使用示例 ====================

def demo_deployment():
    """演示部署流程"""
    print("="*60)
    print("MiniMind 模型部署演示")
    print("="*60)
    
    # 创建服务配置
    config = ServerConfig(
        host="0.0.0.0",
        port=8000,
        workers=4,
        max_batch_size=32
    )
    
    print(f"\n服务配置:")
    print(f"  地址: {config.host}:{config.port}")
    print(f"  工作进程: {config.workers}")
    print(f"  最大批大小: {config.max_batch_size}")
    
    # 这里需要实际加载模型
    # from model import Transformer
    # model = Transformer(...)
    
    # 创建服务
    # server = InferenceServer(model, config)
    
    # 创建FastAPI应用
    # app = create_fastapi_app(server)
    
    # 启动服务
    # import uvicorn
    # uvicorn.run(app, host=config.host, port=config.port)
    
    print("\n部署演示完成!")


if __name__ == "__main__":
    demo_deployment()
```

### 48.2 Docker容器化部署

```python
"""
MiniMind Docker容器化部署
=========================

使用Docker进行模型容器化部署。

包含：
- Dockerfile
- docker-compose配置
- 部署脚本
"""

# ==================== Dockerfile ====================

DOCKERFILE = '''
# MiniMind Dockerfile
FROM nvidia/cuda:11.8-cudnn8-runtime-ubuntu22.04

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 安装系统依赖
RUN apt-get update && apt-get install -y \\
    python3.10 \\
    python3-pip \\
    git \\
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip3 install --no-cache-dir -r requirements.txt

# 复制模型文件
COPY model/ /app/model/
COPY tokenizer/ /app/tokenizer/

# 复制服务代码
COPY server.py .
COPY config.yaml .

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["python3", "server.py", "--config", "config.yaml"]
'''

# ==================== docker-compose.yml ====================

DOCKER_COMPOSE = '''
version: '3.8'

services:
  minimind-api:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    volumes:
      - ./model:/app/model
      - ./logs:/app/logs
    environment:
      - CUDA_VISIBLE_DEVICES=0
      - MODEL_PATH=/app/model/model.pt
      - MAX_BATCH_SIZE=32
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  nginx:
    image: nginx:latest
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - minimind-api
'''

# ==================== Kubernetes部署配置 ====================

KUBERNETES_DEPLOYMENT = '''
apiVersion: apps/v1
kind: Deployment
metadata:
  name: minimind-deployment
  labels:
    app: minimind
spec:
  replicas: 3
  selector:
    matchLabels:
      app: minimind
  template:
    metadata:
      labels:
        app: minimind
    spec:
      containers:
      - name: minimind
        image: minimind:latest
        ports:
        - containerPort: 8000
        resources:
          limits:
            nvidia.com/gpu: 1
            memory: "8Gi"
            cpu: "4"
          requests:
            memory: "4Gi"
            cpu: "2"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        volumeMounts:
        - name: model-storage
          mountPath: /app/model
      volumes:
      - name: model-storage
        persistentVolumeClaim:
          claimName: model-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: minimind-service
spec:
  selector:
    app: minimind
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
'''

# ==================== 部署脚本 ====================

class DockerDeployer:
    """Docker部署管理器"""
    
    def __init__(self, project_dir: str):
        self.project_dir = project_dir
    
    def create_dockerfile(self):
        """创建Dockerfile"""
        dockerfile_path = os.path.join(self.project_dir, "Dockerfile")
        with open(dockerfile_path, 'w') as f:
            f.write(DOCKERFILE)
        print(f"创建Dockerfile: {dockerfile_path}")
    
    def create_docker_compose(self):
        """创建docker-compose.yml"""
        compose_path = os.path.join(self.project_dir, "docker-compose.yml")
        with open(compose_path, 'w') as f:
            f.write(DOCKER_COMPOSE)
        print(f"创建docker-compose.yml: {compose_path}")
    
    def create_kubernetes_config(self):
        """创建Kubernetes配置"""
        k8s_path = os.path.join(self.project_dir, "kubernetes.yaml")
        with open(k8s_path, 'w') as f:
            f.write(KUBERNETES_DEPLOYMENT)
        print(f"创建Kubernetes配置: {k8s_path}")
    
    def build_image(self, tag: str = "minimind:latest"):
        """构建Docker镜像"""
        import subprocess
        
        cmd = f"docker build -t {tag} {self.project_dir}"
        print(f"执行: {cmd}")
        subprocess.run(cmd, shell=True, check=True)
    
    def run_container(self, tag: str = "minimind:latest", port: int = 8000):
        """运行容器"""
        import subprocess
        
        cmd = f"docker run -d -p {port}:8000 --gpus all {tag}"
        print(f"执行: {cmd}")
        subprocess.run(cmd, shell=True, check=True)
    
    def deploy_all(self):
        """完整部署"""
        print("="*60)
        print("Docker容器化部署")
        print("="*60)
        
        print("\n[1/4] 创建Dockerfile...")
        self.create_dockerfile()
        
        print("\n[2/4] 创建docker-compose.yml...")
        self.create_docker_compose()
        
        print("\n[3/4] 创建Kubernetes配置...")
        self.create_kubernetes_config()
        
        print("\n[4/4] 构建镜像...")
        self.build_image()
        
        print("\n" + "="*60)
        print("部署完成！")
        print("启动服务: docker-compose up -d")
        print("="*60)


# ==================== 使用示例 ====================

def demo_docker_deployment():
    """演示Docker部署"""
    print("="*60)
    print("MiniMind Docker部署演示")
    print("="*60)
    
    # 创建部署器
    # deployer = DockerDeployer("./deployment")
    # deployer.deploy_all()
    
    print("\nDocker部署演示完成!")


if __name__ == "__main__":
    demo_docker_deployment()
```

---

## 四十九、综合实战项目：构建完整的LLM应用

### 49.1 端到端LLM应用开发

```python
"""
MiniMind 综合实战项目
=====================

构建一个完整的LLM应用，整合所有学到的知识。

项目功能：
- 模型训练
- 模型评估
- 模型部署
- Web界面
- API服务
"""

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from typing import Dict, List, Optional, Tuple
import json
import os
import time
from dataclasses import dataclass, field
import argparse


# ==================== 项目配置 ====================

@dataclass
class ProjectConfig:
    """项目配置"""
    # 模型配置
    model_name: str = "minimind"
    dim: int = 512
    n_layers: int = 8
    n_heads: int = 8
    vocab_size: int = 6400
    max_seq_len: int = 512
    
    # 训练配置
    batch_size: int = 16
    learning_rate: float = 1e-4
    num_epochs: int = 10
    warmup_steps: int = 1000
    weight_decay: float = 0.01
    
    # 数据配置
    data_dir: str = "./data"
    train_file: str = "train.txt"
    val_file: str = "val.txt"
    
    # 输出配置
    output_dir: str = "./output"
    save_steps: int = 1000
    eval_steps: int = 500
    
    # 部署配置
    host: str = "0.0.0.0"
    port: int = 8000
    
    def save(self, path: str):
        """保存配置"""
        with open(path, 'w') as f:
            json.dump(self.__dict__, f, indent=2)
    
    @classmethod
    def load(cls, path: str) -> 'ProjectConfig':
        """加载配置"""
        with open(path, 'r') as f:
            data = json.load(f)
        return cls(**data)


# ==================== 完整训练流程 ====================

class LLMProject:
    """
    LLM项目主类
    
    整合训练、评估、部署全流程。
    """
    
    def __init__(self, config: ProjectConfig):
        self.config = config
        self.model = None
        self.tokenizer = None
        self.trainer = None
        
        os.makedirs(config.output_dir, exist_ok=True)
    
    def setup(self):
        """初始化项目"""
        print("="*60)
        print(f"初始化 {self.config.model_name} 项目")
        print("="*60)
        
        # 创建模型
        print("\n创建模型...")
        self.model = self._create_model()
        
        # 创建tokenizer
        print("创建tokenizer...")
        self.tokenizer = self._create_tokenizer()
        
        # 保存配置
        config_path = os.path.join(self.config.output_dir, "config.json")
        self.config.save(config_path)
        
        print(f"\n模型参数量: {sum(p.numel() for p in self.model.parameters()):,}")
    
    def _create_model(self) -> nn.Module:
        """创建模型"""
        from model import Transformer
        
        model = Transformer(
            dim=self.config.dim,
            n_layers=self.config.n_layers,
            n_heads=self.config.n_heads,
            vocab_size=self.config.vocab_size,
            max_seq_len=self.config.max_seq_len
        )
        
        return model
    
    def _create_tokenizer(self):
        """创建tokenizer"""
        from tokenizer import Tokenizer
        
        tokenizer = Tokenizer(
            vocab_size=self.config.vocab_size
        )
        
        return tokenizer
    
    def train(self):
        """训练模型"""
        print("\n" + "="*60)
        print("开始训练")
        print("="*60)
        
        # 创建数据集
        train_dataset = self._create_dataset(
            os.path.join(self.config.data_dir, self.config.train_file)
        )
        
        val_dataset = self._create_dataset(
            os.path.join(self.config.data_dir, self.config.val_file)
        )
        
        # 创建数据加载器
        train_loader = DataLoader(
            train_dataset,
            batch_size=self.config.batch_size,
            shuffle=True,
            collate_fn=self._collate_fn
        )
        
        val_loader = DataLoader(
            val_dataset,
            batch_size=self.config.batch_size,
            collate_fn=self._collate_fn
        )
        
        # 创建优化器
        optimizer = torch.optim.AdamW(
            self.model.parameters(),
            lr=self.config.learning_rate,
            weight_decay=self.config.weight_decay
        )
        
        # 训练循环
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model.to(device)
        
        global_step = 0
        best_val_loss = float('inf')
        
        for epoch in range(self.config.num_epochs):
            self.model.train()
            epoch_loss = 0
            
            for step, batch in enumerate(train_loader):
                loss = self._training_step(batch, device)
                
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                
                epoch_loss += loss.item()
                global_step += 1
                
                if global_step % 100 == 0:
                    print(f"Epoch {epoch+1}, Step {global_step}, Loss: {loss.item():.4f}")
                
                if global_step % self.config.eval_steps == 0:
                    val_loss = self._evaluate(val_loader, device)
                    print(f"验证损失: {val_loss:.4f}")
                    
                    if val_loss < best_val_loss:
                        best_val_loss = val_loss
                        self._save_model("best_model.pt")
                
                if global_step % self.config.save_steps == 0:
                    self._save_model(f"checkpoint_{global_step}.pt")
            
            avg_loss = epoch_loss / len(train_loader)
            print(f"\nEpoch {epoch+1} 完成, 平均损失: {avg_loss:.4f}")
        
        # 保存最终模型
        self._save_model("final_model.pt")
        
        print("\n训练完成!")
    
    def _create_dataset(self, file_path: str) -> Dataset:
        """创建数据集"""
        class TextDataset(Dataset):
            def __init__(self, path, tokenizer, max_len):
                with open(path, 'r', encoding='utf-8') as f:
                    self.texts = [line.strip() for line in f if line.strip()]
                self.tokenizer = tokenizer
                self.max_len = max_len
            
            def __len__(self):
                return len(self.texts)
            
            def __getitem__(self, idx):
                text = self.texts[idx]
                tokens = self.tokenizer.encode(text)[:self.max_len]
                return {'input_ids': tokens, 'labels': tokens}
        
        return TextDataset(file_path, self.tokenizer, self.config.max_seq_len)
    
    def _collate_fn(self, batch):
        """批处理函数"""
        input_ids = [item['input_ids'] for item in batch]
        max_len = max(len(ids) for ids in input_ids)
        
        padded_ids = []
        for ids in input_ids:
            pad_len = max_len - len(ids)
            padded_ids.append(ids + [0] * pad_len)
        
        return {
            'input_ids': torch.tensor(padded_ids),
            'labels': torch.tensor(padded_ids)
        }
    
    def _training_step(self, batch, device):
        """训练步骤"""
        input_ids = batch['input_ids'].to(device)
        labels = batch['labels'].to(device)
        
        outputs = self.model(input_ids)
        
        shift_outputs = outputs[..., :-1, :].contiguous()
        shift_labels = labels[..., 1:].contiguous()
        
        loss = nn.functional.cross_entropy(
            shift_outputs.view(-1, shift_outputs.size(-1)),
            shift_labels.view(-1)
        )
        
        return loss
    
    def _evaluate(self, dataloader, device):
        """评估"""
        self.model.eval()
        total_loss = 0
        
        with torch.no_grad():
            for batch in dataloader:
                loss = self._training_step(batch, device)
                total_loss += loss.item()
        
        self.model.train()
        return total_loss / len(dataloader)
    
    def _save_model(self, filename: str):
        """保存模型"""
        path = os.path.join(self.config.output_dir, filename)
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'config': self.config.__dict__
        }, path)
        print(f"保存模型: {path}")
    
    def evaluate(self):
        """评估模型"""
        print("\n" + "="*60)
        print("模型评估")
        print("="*60)
        
        # 加载最佳模型
        model_path = os.path.join(self.config.output_dir, "best_model.pt")
        if os.path.exists(model_path):
            checkpoint = torch.load(model_path)
            self.model.load_state_dict(checkpoint['model_state_dict'])
        
        # 评估困惑度
        val_dataset = self._create_dataset(
            os.path.join(self.config.data_dir, self.config.val_file)
        )
        
        val_loader = DataLoader(
            val_dataset,
            batch_size=self.config.batch_size,
            collate_fn=self._collate_fn
        )
        
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model.to(device)
        
        val_loss = self._evaluate(val_loader, device)
        perplexity = torch.exp(torch.tensor(val_loss))
        
        print(f"\n验证损失: {val_loss:.4f}")
        print(f"困惑度: {perplexity:.2f}")
    
    def deploy(self):
        """部署模型"""
        print("\n" + "="*60)
        print("模型部署")
        print("="*60)
        
        from deployment import ModelExporter, InferenceServer, ServerConfig
        
        # 导出模型
        exporter = ModelExporter(self.model)
        
        exporter.export_onnx(
            os.path.join(self.config.output_dir, "model.onnx")
        )
        
        exporter.export_torchscript(
            os.path.join(self.config.output_dir, "model.pt")
        )
        
        # 创建服务
        server_config = ServerConfig(
            host=self.config.host,
            port=self.config.port,
            model_path=os.path.join(self.config.output_dir, "model.pt")
        )
        
        print(f"\n服务配置:")
        print(f"  地址: {server_config.host}:{server_config.port}")
        print(f"  模型: {server_config.model_path}")
        
        print("\n启动服务:")
        print(f"  python server.py --config {self.config.output_dir}/config.json")
    
    def run(self):
        """运行完整流程"""
        self.setup()
        self.train()
        self.evaluate()
        self.deploy()


# ==================== 命令行接口 ====================

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="MiniMind LLM项目")
    
    parser.add_argument("--mode", type=str, default="train",
                       choices=["train", "evaluate", "deploy", "all"],
                       help="运行模式")
    parser.add_argument("--config", type=str, default=None,
                       help="配置文件路径")
    
    # 模型参数
    parser.add_argument("--dim", type=int, default=512)
    parser.add_argument("--n_layers", type=int, default=8)
    parser.add_argument("--n_heads", type=int, default=8)
    parser.add_argument("--vocab_size", type=int, default=6400)
    
    # 训练参数
    parser.add_argument("--batch_size", type=int, default=16)
    parser.add_argument("--learning_rate", type=float, default=1e-4)
    parser.add_argument("--num_epochs", type=int, default=10)
    
    args = parser.parse_args()
    
    # 加载或创建配置
    if args.config:
        config = ProjectConfig.load(args.config)
    else:
        config = ProjectConfig(
            dim=args.dim,
            n_layers=args.n_layers,
            n_heads=args.n_heads,
            vocab_size=args.vocab_size,
            batch_size=args.batch_size,
            learning_rate=args.learning_rate,
            num_epochs=args.num_epochs
        )
    
    # 创建项目
    project = LLMProject(config)
    
    # 运行
    if args.mode == "train":
        project.setup()
        project.train()
    elif args.mode == "evaluate":
        project.setup()
        project.evaluate()
    elif args.mode == "deploy":
        project.setup()
        project.deploy()
    else:
        project.run()


if __name__ == "__main__":
    main()
```

---

## 五十、学习路径与进阶建议

### 50.1 MiniMind学习路径图

```
MiniMind 学习路径
==================

第一阶段：基础入门（1-2周）
├── Python基础
├── PyTorch基础
├── 深度学习基础
│   ├── 神经网络原理
│   ├── 反向传播
│   └── 优化算法
└── NLP基础
    ├── 分词
    ├── 词向量
    └── 语言模型

第二阶段：核心概念（2-3周）
├── Transformer架构
│   ├── 自注意力机制
│   ├── 多头注意力
│   ├── 位置编码
│   └── 层归一化
├── 语言模型训练
│   ├── 预训练目标
│   ├── 数据处理
│   └── 训练技巧
└── 生成策略
    ├── 贪心搜索
    ├── Beam Search
    └── 采样方法

第三阶段：实践应用（3-4周）
├── 模型训练
│   ├── 数据准备
│   ├── 训练配置
│   └── 监控调试
├── 模型优化
│   ├── 混合精度
│   ├── 梯度累积
│   └── 分布式训练
└── 模型部署
    ├── 模型导出
    ├── 服务化
    └── 性能优化

第四阶段：进阶探索（持续）
├── 高效训练
│   ├── Flash Attention
│   ├── KV Cache
│   └── 模型并行
├── 模型改进
│   ├── 架构创新
│   ├── 高效注意力
│   └── 参数高效微调
└── 应用拓展
    ├── 对话系统
    ├── 文本生成
    └── 知识增强
```

### 50.2 推荐资源

```python
"""
MiniMind 学习资源推荐
=====================

书籍推荐：
1. 《深度学习》- Goodfellow等
2. 《自然语言处理实战》- Lane等
3. 《Attention Is All You Need》论文
4. 《BERT: Pre-training of Deep Bidirectional Transformers》论文
5. 《GPT-3: Language Models are Few-Shot Learners》论文

在线课程：
1. Stanford CS224N: NLP with Deep Learning
2. fast.ai: Practical Deep Learning for Coders
3. Hugging Face Course
4. 李沐《动手学深度学习》

开源项目：
1. Hugging Face Transformers
2. nanoGPT (Andrej Karpathy)
3. lit-llama
4. llama.cpp

论文列表：
1. Transformer架构
2. GPT系列
3. BERT系列
4. LLaMA系列
5. 高效注意力机制
"""
```

---

## 第五十一部分：交互式代码练习 - 基础篇

### 51.1 Python基础练习

#### 练习1：实现一个简单的词频统计器

```python
# ==================== 练习说明 ====================
# 目标：实现一个词频统计器，统计文本中每个词出现的次数
# 要求：
# 1. 函数名：word_frequency
# 2. 参数：text (字符串)
# 3. 返回：字典，键为词，值为出现次数
# 4. 需要处理标点符号，转换为小写

# ==================== 编写区域 ====================
# 请在下方编写你的代码：

def word_frequency(text):
    # 请在此编写你的代码
    pass

# ==================== 测试代码 ====================
# 测试你的实现
test_text = "Hello World! Hello Python. Python is great!"
result = word_frequency(test_text)
print(result)
# 期望输出: {'hello': 2, 'world': 1, 'python': 2, 'is': 1, 'great': 1}

# ==================== 对照区域 ====================
# 参考实现：

def word_frequency_reference(text):
    """
    词频统计器 - 参考实现
    
    步骤：
    1. 转换为小写
    2. 移除标点符号
    3. 分词
    4. 统计频率
    """
    import string
    
    # 转换为小写
    text = text.lower()
    
    # 移除标点符号
    for char in string.punctuation:
        text = text.replace(char, ' ')
    
    # 分词
    words = text.split()
    
    # 统计频率
    frequency = {}
    for word in words:
        if word:
            frequency[word] = frequency.get(word, 0) + 1
    
    return frequency

# ==================== 检查结果 ====================
# 语法检查: [待检查]
# 功能检查: [待检查]
# 差异分析: [待分析]
```

#### 练习2：实现一个简单的文本分词器

```python
# ==================== 练习说明 ====================
# 目标：实现一个简单的文本分词器
# 要求：
# 1. 类名：SimpleTokenizer
# 2. 方法：
#    - __init__(self, vocab): 初始化词表
#    - encode(self, text): 将文本转换为token id列表
#    - decode(self, ids): 将token id列表转换回文本
# 3. 未知词用 <unk> (id=1) 表示
# 4. 词表格式：{词: id}

# ==================== 编写区域 ====================
# 请在下方编写你的代码：

class SimpleTokenizer:
    def __init__(self, vocab):
        # 请在此编写初始化代码
        pass
    
    def encode(self, text):
        # 请在此编写编码代码
        pass
    
    def decode(self, ids):
        # 请在此编写解码代码
        pass

# ==================== 测试代码 ====================
vocab = {'hello': 2, 'world': 3, 'python': 4, '<unk>': 1, '<pad>': 0}
tokenizer = SimpleTokenizer(vocab)

# 测试编码
ids = tokenizer.encode("hello world python")
print(f"编码结果: {ids}")  # 期望: [2, 3, 4]

# 测试解码
text = tokenizer.decode([2, 3, 4])
print(f"解码结果: {text}")  # 期望: "hello world python"

# 测试未知词
ids = tokenizer.encode("hello java")
print(f"未知词编码: {ids}")  # 期望: [2, 1]

# ==================== 对照区域 ====================
# 参考实现：

class SimpleTokenizerReference:
    """
    简单文本分词器 - 参考实现
    
    功能：
    - 将文本转换为token id序列
    - 将token id序列转换回文本
    - 处理未知词
    """
    
    def __init__(self, vocab):
        """
        初始化分词器
        
        参数：
        - vocab: 词表字典 {词: id}
        """
        self.vocab = vocab
        # 创建反向词表 {id: 词}
        self.id_to_word = {v: k for k, v in vocab.items()}
    
    def encode(self, text):
        """
        编码：文本 -> token id列表
        
        参数：
        - text: 输入文本
        
        返回：
        - token id列表
        """
        # 转换为小写并分词
        words = text.lower().split()
        
        # 转换为id
        ids = []
        for word in words:
            # 未知词用 <unk> 的 id
            token_id = self.vocab.get(word, self.vocab.get('<unk>', 1))
            ids.append(token_id)
        
        return ids
    
    def decode(self, ids):
        """
        解码：token id列表 -> 文本
        
        参数：
        - ids: token id列表
        
        返回：
        - 文本字符串
        """
        words = []
        for token_id in ids:
            word = self.id_to_word.get(token_id, '<unk>')
            words.append(word)
        
        return ' '.join(words)

# ==================== 检查结果 ====================
# 语法检查: [待检查]
# 功能检查: [待检查]
```

### 51.2 PyTorch基础练习

#### 练习3：实现一个简单的线性层

```python
# ==================== 练习说明 ====================
# 目标：不使用nn.Linear，手动实现一个线性层
# 要求：
# 1. 类名：ManualLinear
# 2. 继承nn.Module
# 3. 方法：
#    - __init__(self, in_features, out_features): 初始化权重和偏置
#    - forward(self, x): 前向传播 y = xW^T + b
# 4. 使用nn.Parameter包装权重和偏置
# 5. 使用kaiming均匀初始化权重

# ==================== 编写区域 ====================
# 请在下方编写你的代码：

import torch
import torch.nn as nn
import math

class ManualLinear(nn.Module):
    def __init__(self, in_features, out_features):
        # 请在此编写初始化代码
        pass
    
    def forward(self, x):
        # 请在此编写前向传播代码
        pass

# ==================== 测试代码 ====================
# 测试你的实现
linear = ManualLinear(10, 5)
x = torch.randn(3, 10)  # batch_size=3, in_features=10
output = linear(x)
print(f"输入形状: {x.shape}")
print(f"输出形状: {output.shape}")  # 期望: torch.Size([3, 5])

# 与nn.Linear对比
official_linear = nn.Linear(10, 5)
official_linear.weight.data = linear.weight.data.clone()
official_linear.bias.data = linear.bias.data.clone()
official_output = official_linear(x)
print(f"与官方实现差异: {(output - official_output).abs().max().item()}")  # 期望: 接近0

# ==================== 对照区域 ====================
# 参考实现：

class ManualLinearReference(nn.Module):
    """
    手动实现的线性层 - 参考实现
    
    公式：y = xW^T + b
    
    参数：
    - in_features: 输入特征维度
    - out_features: 输出特征维度
    """
    
    def __init__(self, in_features, out_features):
        super().__init__()
        
        self.in_features = in_features
        self.out_features = out_features
        
        # 创建权重参数 (out_features, in_features)
        self.weight = nn.Parameter(torch.empty(out_features, in_features))
        
        # 创建偏置参数 (out_features,)
        self.bias = nn.Parameter(torch.empty(out_features))
        
        # 初始化参数
        self._reset_parameters()
    
    def _reset_parameters(self):
        """使用kaiming均匀初始化"""
        nn.init.kaiming_uniform_(self.weight, a=math.sqrt(5))
        if self.bias is not None:
            fan_in, _ = nn.init._calculate_fan_in_and_fan_out(self.weight)
            bound = 1 / math.sqrt(fan_in) if fan_in > 0 else 0
            nn.init.uniform_(self.bias, -bound, bound)
    
    def forward(self, x):
        """
        前向传播
        
        参数：
        - x: (batch_size, in_features)
        
        返回：
        - output: (batch_size, out_features)
        """
        # y = x @ W^T + b
        return torch.nn.functional.linear(x, self.weight, self.bias)

# ==================== 检查结果 ====================
# 语法检查: [待检查]
# 功能检查: [待检查]
```

#### 练习4：实现ReLU激活函数

```python
# ==================== 练习说明 ====================
# 目标：手动实现ReLU激活函数
# 要求：
# 1. 类名：ManualReLU
# 2. 继承nn.Module
# 3. 方法：
#    - forward(self, x): 实现 ReLU(x) = max(0, x)
# 4. 同时实现函数版本：manual_relu(x)

# ==================== 编写区域 ====================
# 请在下方编写你的代码：

import torch
import torch.nn as nn

class ManualReLU(nn.Module):
    def __init__(self):
        # 请在此编写初始化代码
        pass
    
    def forward(self, x):
        # 请在此编写前向传播代码
        pass

def manual_relu(x):
    # 请在此编写函数版本
    pass

# ==================== 测试代码 ====================
# 测试你的实现
relu = ManualReLU()
x = torch.tensor([-2, -1, 0, 1, 2], dtype=torch.float32)
output = relu(x)
print(f"输入: {x}")
print(f"输出: {output}")  # 期望: tensor([0., 0., 0., 1., 2.])

# 测试函数版本
output_func = manual_relu(x)
print(f"函数版本输出: {output_func}")

# 与官方实现对比
official_relu = nn.ReLU()
official_output = official_relu(x)
print(f"与官方实现差异: {(output - official_output).abs().max().item()}")  # 期望: 0

# ==================== 对照区域 ====================
# 参考实现：

class ManualReLUReference(nn.Module):
    """
    手动实现的ReLU激活函数 - 参考实现
    
    公式：ReLU(x) = max(0, x)
    
    特点：
    - 计算简单，效率高
    - 缓解梯度消失问题
    - 可能导致神经元死亡
    """
    
    def __init__(self):
        super().__init__()
    
    def forward(self, x):
        """
        前向传播
        
        参数：
        - x: 任意形状的张量
        
        返回：
        - output: 与x相同形状，负值变为0
        """
        return torch.maximum(x, torch.zeros_like(x))

def manual_relu_reference(x):
    """函数版本的ReLU"""
    return torch.maximum(x, torch.zeros_like(x))

# ==================== 检查结果 ====================
# 语法检查: [待检查]
# 功能检查: [待检查]
```

---

## 第五十二部分：交互式代码练习 - Transformer组件篇

### 52.1 注意力机制练习

#### 练习5：实现缩放点积注意力

```python
# ==================== 练习说明 ====================
# 目标：实现Transformer中的缩放点积注意力
# 要求：
# 1. 函数名：scaled_dot_product_attention
# 2. 参数：query, key, value, mask=None
# 3. 公式：Attention(Q,K,V) = softmax(QK^T / sqrt(d_k)) * V
# 4. 支持mask（将mask位置设为负无穷）
# 5. 返回：output, attention_weights

# ==================== 编写区域 ====================
# 请在下方编写你的代码：

import torch
import torch.nn.functional as F
import math

def scaled_dot_product_attention(query, key, value, mask=None):
    """
    缩放点积注意力
    
    参数：
    - query: (batch, heads, seq_len, d_k)
    - key: (batch, heads, seq_len, d_k)
    - value: (batch, heads, seq_len, d_v)
    - mask: 可选的mask张量
    
    返回：
    - output: 注意力输出
    - attention_weights: 注意力权重
    """
    # 请在此编写你的代码
    pass

# ==================== 测试代码 ====================
# 测试你的实现
batch_size, n_heads, seq_len, d_k = 2, 4, 5, 8

query = torch.randn(batch_size, n_heads, seq_len, d_k)
key = torch.randn(batch_size, n_heads, seq_len, d_k)
value = torch.randn(batch_size, n_heads, seq_len, d_k)

output, weights = scaled_dot_product_attention(query, key, value)
print(f"输出形状: {output.shape}")  # 期望: torch.Size([2, 4, 5, 8])
print(f"权重形状: {weights.shape}")  # 期望: torch.Size([2, 4, 5, 5])
print(f"权重和: {weights.sum(dim=-1)}")  # 期望: 每行和为1

# 测试mask
mask = torch.triu(torch.ones(seq_len, seq_len), diagonal=1).bool()
output_masked, weights_masked = scaled_dot_product_attention(query, key, value, mask)
print(f"mask后权重[0,0,0]: {weights_masked[0,0,0]}")  # 期望: 上三角为0

# ==================== 对照区域 ====================
# 参考实现：

def scaled_dot_product_attention_reference(query, key, value, mask=None):
    """
    缩放点积注意力 - 参考实现
    
    公式：Attention(Q,K,V) = softmax(QK^T / sqrt(d_k)) * V
    
    参数：
    - query: (batch, heads, seq_len, d_k)
    - key: (batch, heads, seq_len, d_k)
    - value: (batch, heads, seq_len, d_v)
    - mask: 可选mask，True位置将被mask掉
    
    返回：
    - output: 注意力输出
    - attention_weights: 注意力权重
    """
    d_k = query.size(-1)
    
    # 计算注意力分数: QK^T / sqrt(d_k)
    # (batch, heads, seq_len, d_k) @ (batch, heads, d_k, seq_len)
    # = (batch, heads, seq_len, seq_len)
    scores = torch.matmul(query, key.transpose(-2, -1)) / math.sqrt(d_k)
    
    # 应用mask
    if mask is not None:
        # 将mask位置设为负无穷，softmax后会变为0
        scores = scores.masked_fill(mask, float('-inf'))
    
    # 计算注意力权重
    attention_weights = F.softmax(scores, dim=-1)
    
    # 加权求和
    # (batch, heads, seq_len, seq_len) @ (batch, heads, seq_len, d_v)
    # = (batch, heads, seq_len, d_v)
    output = torch.matmul(attention_weights, value)
    
    return output, attention_weights

# ==================== 检查结果 ====================
# 语法检查: [待检查]
# 功能检查: [待检查]
```

#### 练习6：实现多头注意力

```python
# ==================== 练习说明 ====================
# 目标：实现多头注意力机制
# 要求：
# 1. 类名：MultiHeadAttention
# 2. 继承nn.Module
# 3. 方法：
#    - __init__(self, d_model, n_heads): 初始化
#    - forward(self, query, key, value, mask=None): 前向传播
# 4. 包含W_q, W_k, W_v, W_o四个线性投影
# 5. 使用上一题的scaled_dot_product_attention

# ==================== 编写区域 ====================
# 请在下方编写你的代码：

import torch
import torch.nn as nn

class MultiHeadAttention(nn.Module):
    def __init__(self, d_model, n_heads):
        # 请在此编写初始化代码
        pass
    
    def forward(self, query, key, value, mask=None):
        # 请在此编写前向传播代码
        pass

# ==================== 测试代码 ====================
# 测试你的实现
d_model, n_heads = 64, 8
mha = MultiHeadAttention(d_model, n_heads)

batch_size, seq_len = 2, 10
x = torch.randn(batch_size, seq_len, d_model)

output, weights = mha(x, x, x)  # 自注意力
print(f"输入形状: {x.shape}")
print(f"输出形状: {output.shape}")  # 期望: torch.Size([2, 10, 64])
print(f"权重形状: {weights.shape}")  # 期望: torch.Size([2, 8, 10, 10])

# ==================== 对照区域 ====================
# 参考实现：

class MultiHeadAttentionReference(nn.Module):
    """
    多头注意力机制 - 参考实现
    
    原理：
    1. 将Q, K, V投影到多个头
    2. 每个头独立计算注意力
    3. 拼接所有头的输出
    4. 通过输出投影得到最终结果
    
    参数：
    - d_model: 模型维度
    - n_heads: 注意力头数
    """
    
    def __init__(self, d_model, n_heads):
        super().__init__()
        
        assert d_model % n_heads == 0, "d_model必须能被n_heads整除"
        
        self.d_model = d_model
        self.n_heads = n_heads
        self.d_k = d_model // n_heads  # 每个头的维度
        
        # 线性投影层
        self.W_q = nn.Linear(d_model, d_model)
        self.W_k = nn.Linear(d_model, d_model)
        self.W_v = nn.Linear(d_model, d_model)
        self.W_o = nn.Linear(d_model, d_model)
    
    def forward(self, query, key, value, mask=None):
        """
        前向传播
        
        参数：
        - query: (batch, seq_len, d_model)
        - key: (batch, seq_len, d_model)
        - value: (batch, seq_len, d_model)
        - mask: 可选的mask
        
        返回：
        - output: (batch, seq_len, d_model)
        - attention_weights: (batch, n_heads, seq_len, seq_len)
        """
        batch_size = query.size(0)
        
        # 1. 线性投影
        Q = self.W_q(query)  # (batch, seq_len, d_model)
        K = self.W_k(key)
        V = self.W_v(value)
        
        # 2. 分割成多个头
        # (batch, seq_len, d_model) -> (batch, n_heads, seq_len, d_k)
        Q = Q.view(batch_size, -1, self.n_heads, self.d_k).transpose(1, 2)
        K = K.view(batch_size, -1, self.n_heads, self.d_k).transpose(1, 2)
        V = V.view(batch_size, -1, self.n_heads, self.d_k).transpose(1, 2)
        
        # 3. 计算注意力
        output, attention_weights = scaled_dot_product_attention_reference(Q, K, V, mask)
        
        # 4. 拼接多头
        # (batch, n_heads, seq_len, d_k) -> (batch, seq_len, d_model)
        output = output.transpose(1, 2).contiguous().view(batch_size, -1, self.d_model)
        
        # 5. 输出投影
        output = self.W_o(output)
        
        return output, attention_weights

# ==================== 检查结果 ====================
# 语法检查: [待检查]
# 功能检查: [待检查]
```

### 52.2 位置编码练习

#### 练习7：实现正弦位置编码

```python
# ==================== 练习说明 ====================
# 目标：实现Transformer原始论文中的正弦位置编码
# 要求：
# 1. 类名：PositionalEncoding
# 2. 继承nn.Module
# 3. 方法：
#    - __init__(self, d_model, max_seq_len=5000, dropout=0.1)
#    - forward(self, x): 添加位置编码
# 4. 公式：
#    PE(pos, 2i) = sin(pos / 10000^(2i/d_model))
#    PE(pos, 2i+1) = cos(pos / 10000^(2i/d_model))
# 5. 位置编码是固定的，不需要学习

# ==================== 编写区域 ====================
# 请在下方编写你的代码：

import torch
import torch.nn as nn
import math

class PositionalEncoding(nn.Module):
    def __init__(self, d_model, max_seq_len=5000, dropout=0.1):
        # 请在此编写初始化代码
        pass
    
    def forward(self, x):
        # 请在此编写前向传播代码
        pass

# ==================== 测试代码 ====================
# 测试你的实现
d_model, max_seq_len = 64, 100
pe = PositionalEncoding(d_model, max_seq_len)

batch_size, seq_len = 2, 20
x = torch.randn(batch_size, seq_len, d_model)
output = pe(x)

print(f"输入形状: {x.shape}")
print(f"输出形状: {output.shape}")  # 期望: torch.Size([2, 20, 64])

# 可视化位置编码
import matplotlib.pyplot as plt
pe_matrix = pe.pe[0, :50, :].detach().numpy()
plt.figure(figsize=(10, 6))
plt.imshow(pe_matrix, aspect='auto', cmap='viridis')
plt.colorbar()
plt.title('Positional Encoding')
plt.xlabel('Dimension')
plt.ylabel('Position')
plt.show()

# ==================== 对照区域 ====================
# 参考实现：

class PositionalEncodingReference(nn.Module):
    """
    正弦位置编码 - 参考实现
    
    公式：
    PE(pos, 2i) = sin(pos / 10000^(2i/d_model))
    PE(pos, 2i+1) = cos(pos / 10000^(2i/d_model))
    
    特点：
    - 固定编码，不需要学习
    - 可以处理任意长度序列
    - 相对位置信息编码在正弦函数中
    """
    
    def __init__(self, d_model, max_seq_len=5000, dropout=0.1):
        super().__init__()
        
        self.dropout = nn.Dropout(p=dropout)
        
        # 创建位置编码矩阵
        pe = torch.zeros(max_seq_len, d_model)
        position = torch.arange(0, max_seq_len, dtype=torch.float).unsqueeze(1)
        
        # 计算分母项
        div_term = torch.exp(
            torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model)
        )
        
        # 偶数维度用sin，奇数维度用cos
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        
        # 添加batch维度
        pe = pe.unsqueeze(0)  # (1, max_seq_len, d_model)
        
        # 注册为buffer（不是参数，但会保存在state_dict中）
        self.register_buffer('pe', pe)
    
    def forward(self, x):
        """
        前向传播：添加位置编码
        
        参数：
        - x: (batch, seq_len, d_model)
        
        返回：
        - output: (batch, seq_len, d_model)
        """
        # x + PE[:seq_len]
        x = x + self.pe[:, :x.size(1), :]
        return self.dropout(x)

# ==================== 检查结果 ====================
# 语法检查: [待检查]
# 功能检查: [待检查]
```

#### 练习8：实现旋转位置编码(RoPE)

```python
# ==================== 练习说明 ====================
# 目标：实现旋转位置编码(RoPE)，这是LLaMA等模型使用的位置编码
# 要求：
# 1. 类名：RotaryPositionEmbedding
# 2. 继承nn.Module
# 3. 方法：
#    - __init__(self, dim, max_seq_len=2048, base=10000)
#    - forward(self, x): 应用旋转位置编码
# 4. 公式：
#    - 计算频率: freq = 1 / (base^(2i/dim))
#    - 旋转: rotate_half(x) * cos + rotate_half(x).flip * sin
# 5. RoPE应用于query和key

# ==================== 编写区域 ====================
# 请在下方编写你的代码：

import torch
import torch.nn as nn
import math

class RotaryPositionEmbedding(nn.Module):
    def __init__(self, dim, max_seq_len=2048, base=10000):
        # 请在此编写初始化代码
        pass
    
    def forward(self, x, seq_len=None):
        # 请在此编写前向传播代码
        pass

# ==================== 测试代码 ====================
# 测试你的实现
dim, max_seq_len = 64, 512
rope = RotaryPositionEmbedding(dim, max_seq_len)

batch_size, seq_len, n_heads, head_dim = 2, 10, 8, 64
x = torch.randn(batch_size, n_heads, seq_len, head_dim)

output = rope(x, seq_len)
print(f"输入形状: {x.shape}")
print(f"输出形状: {output.shape}")  # 期望: torch.Size([2, 8, 10, 64])

# 验证旋转性质：相对位置不变性
x1 = torch.randn(1, 1, 1, head_dim)  # 位置0
x2 = torch.randn(1, 1, 1, head_dim)  # 位置1

# ==================== 对照区域 ====================
# 参考实现：

class RotaryPositionEmbeddingReference(nn.Module):
    """
    旋转位置编码(RoPE) - 参考实现
    
    论文：RoFormer: Enhanced Transformer with Rotary Position Embedding
    
    原理：
    - 将位置信息编码为旋转矩阵
    - 通过旋转操作注入位置信息
    - 保持相对位置关系
    
    优势：
    - 相对位置编码
    - 长度外推能力强
    - 计算效率高
    """
    
    def __init__(self, dim, max_seq_len=2048, base=10000):
        super().__init__()
        
        self.dim = dim
        self.max_seq_len = max_seq_len
        self.base = base
        
        # 计算频率
        inv_freq = 1.0 / (base ** (torch.arange(0, dim, 2).float() / dim))
        self.register_buffer('inv_freq', inv_freq)
        
        # 预计算cos和sin
        self._build_cache(max_seq_len)
    
    def _build_cache(self, seq_len):
        """预计算cos和sin缓存"""
        t = torch.arange(seq_len, device=self.inv_freq.device, dtype=self.inv_freq.dtype)
        freqs = torch.einsum('i,j->ij', t, self.inv_freq)
        # (seq_len, dim/2)
        
        # 拼接成完整维度
        emb = torch.cat([freqs, freqs], dim=-1)  # (seq_len, dim)
        
        self.register_buffer('cos_cached', emb.cos()[None, None, :, :])
        self.register_buffer('sin_cached', emb.sin()[None, None, :, :])
    
    def forward(self, x, seq_len=None):
        """
        前向传播：应用旋转位置编码
        
        参数：
        - x: (batch, n_heads, seq_len, dim)
        - seq_len: 序列长度（可选）
        
        返回：
        - output: 旋转后的张量
        """
        if seq_len is None:
            seq_len = x.shape[2]
        
        # 获取cos和sin
        cos = self.cos_cached[:, :, :seq_len, :]
        sin = self.sin_cached[:, :, :seq_len, :]
        
        # 应用旋转
        return self._apply_rotary(x, cos, sin)
    
    def _apply_rotary(self, x, cos, sin):
        """应用旋转操作"""
        # 将x分成两半
        x1, x2 = x[..., :x.shape[-1]//2], x[..., x.shape[-1]//2:]
        
        # 旋转
        rotated = torch.cat([-x2, x1], dim=-1)
        
        return x * cos + rotated * sin

# ==================== 检查结果 ====================
# 语法检查: [待检查]
# 功能检查: [待检查]
```

---

## 第五十三部分：交互式代码练习 - MiniMind核心组件篇

### 53.1 RMSNorm实现练习

#### 练习9：实现RMSNorm

```python
# ==================== 练习说明 ====================
# 目标：实现RMSNorm (Root Mean Square Layer Normalization)
# 要求：
# 1. 类名：RMSNorm
# 2. 继承nn.Module
# 3. 方法：
#    - __init__(self, dim, eps=1e-6)
#    - forward(self, x): 实现RMS归一化
# 4. 公式：output = x * (1 / sqrt(mean(x^2) + eps)) * weight
# 5. 与LayerNorm的区别：不计算均值，只计算均方根

# ==================== 编写区域 ====================
# 请在下方编写你的代码：

import torch
import torch.nn as nn

class RMSNorm(nn.Module):
    def __init__(self, dim, eps=1e-6):
        # 请在此编写初始化代码
        pass
    
    def forward(self, x):
        # 请在此编写前向传播代码
        pass

# ==================== 测试代码 ====================
# 测试你的实现
dim = 64
rms_norm = RMSNorm(dim)

batch_size, seq_len = 2, 10
x = torch.randn(batch_size, seq_len, dim)
output = rms_norm(x)

print(f"输入形状: {x.shape}")
print(f"输出形状: {output.shape}")  # 期望: torch.Size([2, 10, 64])

# 验证归一化效果
rms = torch.sqrt(torch.mean(x ** 2, dim=-1, keepdim=True))
print(f"输入RMS: {rms[0, 0, 0].item():.4f}")

output_rms = torch.sqrt(torch.mean(output ** 2, dim=-1, keepdim=True))
print(f"输出RMS（应接近weight值）: {output_rms[0, 0, 0].item():.4f}")

# ==================== 对照区域 ====================
# 参考实现：

class RMSNormReference(nn.Module):
    """
    RMSNorm - Root Mean Square Layer Normalization - 参考实现
    
    论文：Root Mean Square Layer Normalization
    
    公式：output = x * (1 / sqrt(mean(x^2) + eps)) * weight
    
    与LayerNorm的区别：
    - LayerNorm: (x - mean) / std * weight + bias
    - RMSNorm: x / rms * weight
    
    优势：
    - 计算量更小（不计算均值）
    - 效果与LayerNorm相近
    - 在LLM中广泛使用
    """
    
    def __init__(self, dim, eps=1e-6):
        super().__init__()
        
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(dim))
    
    def forward(self, x):
        """
        前向传播
        
        参数：
        - x: (batch, seq_len, dim) 或任意形状，最后维度是特征维度
        
        返回：
        - output: 归一化后的张量
        """
        # 计算RMS: sqrt(mean(x^2))
        rms = torch.sqrt(torch.mean(x ** 2, dim=-1, keepdim=True) + self.eps)
        
        # 归一化并缩放
        return x / rms * self.weight
    
    def _norm(self, x):
        """归一化操作"""
        return x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + self.eps)

# ==================== 检查结果 ====================
# 语法检查: [待检查]
# 功能检查: [待检查]
# 差异分析: [待分析]
```

### 53.2 SwiGLU激活函数练习

#### 练习10：实现SwiGLU激活函数

```python
# ==================== 练习说明 ====================
# 目标：实现SwiGLU激活函数，这是LLaMA等模型使用的激活函数
# 要求：
# 1. 类名：SwiGLU
# 2. 继承nn.Module
# 3. 方法：
#    - __init__(self, dim, hidden_dim, dropout=0.1)
#    - forward(self, x): 实现SwiGLU前向传播
# 4. 公式：SwiGLU(x) = Swish(xW1) * (xW2)
# 5. Swish(x) = x * sigmoid(x)

# ==================== 编写区域 ====================
# 请在下方编写你的代码：

import torch
import torch.nn as nn
import torch.nn.functional as F

class SwiGLU(nn.Module):
    def __init__(self, dim, hidden_dim, dropout=0.1):
        # 请在此编写初始化代码
        pass
    
    def forward(self, x):
        # 请在此编写前向传播代码
        pass

# ==================== 测试代码 ====================
# 测试你的实现
dim, hidden_dim = 64, 256
swiglu = SwiGLU(dim, hidden_dim)

batch_size, seq_len = 2, 10
x = torch.randn(batch_size, seq_len, dim)
output = swiglu(x)

print(f"输入形状: {x.shape}")
print(f"输出形状: {output.shape}")  # 期望: torch.Size([2, 10, 64])

# 验证参数量
total_params = sum(p.numel() for p in swiglu.parameters())
print(f"参数量: {total_params}")  # 期望: dim * hidden_dim * 2 + hidden_dim * dim

# ==================== 对照区域 ====================
# 参考实现：

class SwiGLUReference(nn.Module):
    """
    SwiGLU激活函数 - 参考实现
    
    论文：GLU Variants Improve Transformer
    
    公式：SwiGLU(x) = Swish(xW1) * (xW2)
    其中 Swish(x) = x * sigmoid(x)
    
    结构：
    - 两个线性变换：W1和W2
    - W1后接Swish激活
    - W2不接激活
    - 两者逐元素相乘
    - 最后通过W3投影回原维度
    
    优势：
    - 比ReLU/GELU效果更好
    - 在LLM中广泛使用
    """
    
    def __init__(self, dim, hidden_dim, dropout=0.1):
        super().__init__()
        
        self.w1 = nn.Linear(dim, hidden_dim, bias=False)  # 门控分支
        self.w2 = nn.Linear(dim, hidden_dim, bias=False)  # 值分支
        self.w3 = nn.Linear(hidden_dim, dim, bias=False)  # 输出投影
        
        self.dropout = nn.Dropout(dropout)
    
    def forward(self, x):
        """
        前向传播
        
        参数：
        - x: (batch, seq_len, dim)
        
        返回：
        - output: (batch, seq_len, dim)
        """
        # Swish(xW1) * (xW2)
        gate = F.silu(self.w1(x))  # SiLU = Swish
        value = self.w2(x)
        
        # 逐元素相乘
        hidden = gate * value
        
        # 输出投影
        output = self.w3(hidden)
        
        return self.dropout(output)

# ==================== 检查结果 ====================
# 语法检查: [待检查]
# 功能检查: [待检查]
```

### 53.3 完整Transformer块练习

#### 练习11：实现Transformer Decoder块

```python
# ==================== 练习说明 ====================
# 目标：实现一个完整的Transformer Decoder块
# 要求：
# 1. 类名：TransformerBlock
# 2. 继承nn.Module
# 3. 方法：
#    - __init__(self, dim, n_heads, mlp_ratio=4, dropout=0.1)
#    - forward(self, x, mask=None): 前向传播
# 4. 结构：
#    - RMSNorm -> Attention -> 残差连接
#    - RMSNorm -> MLP(SwiGLU) -> 残差连接
# 5. 使用前面实现的组件

# ==================== 编写区域 ====================
# 请在下方编写你的代码：

import torch
import torch.nn as nn

class TransformerBlock(nn.Module):
    def __init__(self, dim, n_heads, mlp_ratio=4, dropout=0.1):
        # 请在此编写初始化代码
        pass
    
    def forward(self, x, mask=None):
        # 请在此编写前向传播代码
        pass

# ==================== 测试代码 ====================
# 测试你的实现
dim, n_heads = 64, 8
block = TransformerBlock(dim, n_heads)

batch_size, seq_len = 2, 10
x = torch.randn(batch_size, seq_len, dim)

output = block(x)
print(f"输入形状: {x.shape}")
print(f"输出形状: {output.shape}")  # 期望: torch.Size([2, 10, 64])

# 测试因果mask
causal_mask = torch.triu(torch.ones(seq_len, seq_len), diagonal=1).bool()
output_masked = block(x, causal_mask)
print(f"带mask输出形状: {output_masked.shape}")

# ==================== 对照区域 ====================
# 参考实现：

class TransformerBlockReference(nn.Module):
    """
    Transformer Decoder块 - 参考实现
    
    结构：
    x -> RMSNorm -> Attention -> + -> RMSNorm -> MLP -> + -> output
    |                              |                           |
    --------------------------------                           |
    ------------------------------------------------------------
    
    特点：
    - Pre-Norm结构（先归一化再计算）
    - RMSNorm替代LayerNorm
    - SwiGLU替代GELU
    - 分组查询注意力(GQA)可选
    """
    
    def __init__(self, dim, n_heads, mlp_ratio=4, dropout=0.1):
        super().__init__()
        
        self.dim = dim
        self.n_heads = n_heads
        
        # 注意力层
        self.attention = MultiHeadAttentionReference(dim, n_heads)
        self.attention_norm = RMSNormReference(dim)
        
        # MLP层
        hidden_dim = int(dim * mlp_ratio)
        self.mlp = SwiGLUReference(dim, hidden_dim, dropout)
        self.mlp_norm = RMSNormReference(dim)
        
        self.dropout = nn.Dropout(dropout)
    
    def forward(self, x, mask=None):
        """
        前向传播
        
        参数：
        - x: (batch, seq_len, dim)
        - mask: 可选的注意力mask
        
        返回：
        - output: (batch, seq_len, dim)
        """
        # 注意力块（带残差连接）
        residual = x
        x = self.attention_norm(x)
        x, _ = self.attention(x, x, x, mask)
        x = self.dropout(x)
        x = residual + x
        
        # MLP块（带残差连接）
        residual = x
        x = self.mlp_norm(x)
        x = self.mlp(x)
        x = residual + x
        
        return x

# ==================== 检查结果 ====================
# 语法检查: [待检查]
# 功能检查: [待检查]
```

---

## 第五十四部分：交互式代码练习 - 训练与推理篇

### 54.1 训练循环练习

#### 练习12：实现训练循环

```python
# ==================== 练习说明 ====================
# 目标：实现一个完整的训练循环
# 要求：
# 1. 函数名：train_epoch
# 2. 参数：model, dataloader, optimizer, device, grad_accum_steps=1
# 3. 功能：
#    - 遍历数据
#    - 前向传播
#    - 计算损失
#    - 反向传播
#    - 梯度累积
#    - 梯度裁剪
#    - 参数更新
# 4. 返回：平均损失

# ==================== 编写区域 ====================
# 请在下方编写你的代码：

import torch
import torch.nn as nn
from tqdm import tqdm

def train_epoch(model, dataloader, optimizer, device, grad_accum_steps=1):
    """
    训练一个epoch
    
    参数：
    - model: 模型
    - dataloader: 数据加载器
    - optimizer: 优化器
    - device: 设备
    - grad_accum_steps: 梯度累积步数
    
    返回：
    - avg_loss: 平均损失
    """
    # 请在此编写你的代码
    pass

# ==================== 测试代码 ====================
# 创建简单模型和数据
class SimpleModel(nn.Module):
    def __init__(self, vocab_size, dim):
        super().__init__()
        self.embed = nn.Embedding(vocab_size, dim)
        self.linear = nn.Linear(dim, vocab_size)
    
    def forward(self, x):
        x = self.embed(x)
        x = self.linear(x)
        return x

# 创建模拟数据
vocab_size, dim = 100, 32
model = SimpleModel(vocab_size, dim)
optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)

# 模拟dataloader
class FakeDataset:
    def __init__(self, n_samples=100, seq_len=10, vocab_size=100):
        self.data = torch.randint(0, vocab_size, (n_samples, seq_len))
    
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        return self.data[idx]

dataloader = torch.utils.data.DataLoader(FakeDataset(), batch_size=4)

# 训练
device = torch.device('cpu')
avg_loss = train_epoch(model, dataloader, optimizer, device)
print(f"平均损失: {avg_loss:.4f}")

# ==================== 对照区域 ====================
# 参考实现：

def train_epoch_reference(model, dataloader, optimizer, device, grad_accum_steps=1):
    """
    训练一个epoch - 参考实现
    
    步骤：
    1. 设置模型为训练模式
    2. 遍历数据
    3. 前向传播
    4. 计算损失
    5. 反向传播（梯度累积）
    6. 梯度裁剪
    7. 参数更新
    8. 清零梯度
    
    参数：
    - model: 模型
    - dataloader: 数据加载器
    - optimizer: 优化器
    - device: 设备
    - grad_accum_steps: 梯度累积步数
    
    返回：
    - avg_loss: 平均损失
    """
    model.train()
    total_loss = 0.0
    num_batches = 0
    
    optimizer.zero_grad()  # 在epoch开始时清零梯度
    
    progress_bar = tqdm(dataloader, desc="Training")
    
    for step, batch in enumerate(progress_bar):
        # 移动数据到设备
        input_ids = batch.to(device)
        
        # 前向传播
        logits = model(input_ids)
        
        # 计算损失（语言模型：预测下一个token）
        # logits: (batch, seq_len, vocab_size)
        # targets: (batch, seq_len)
        shift_logits = logits[..., :-1, :].contiguous()
        shift_labels = input_ids[..., 1:].contiguous()
        
        loss = nn.functional.cross_entropy(
            shift_logits.view(-1, shift_logits.size(-1)),
            shift_labels.view(-1)
        )
        
        # 缩放损失（用于梯度累积）
        loss = loss / grad_accum_steps
        
        # 反向传播
        loss.backward()
        
        total_loss += loss.item() * grad_accum_steps
        num_batches += 1
        
        # 梯度累积
        if (step + 1) % grad_accum_steps == 0:
            # 梯度裁剪
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            
            # 参数更新
            optimizer.step()
            
            # 清零梯度
            optimizer.zero_grad()
        
        # 更新进度条
        progress_bar.set_postfix({'loss': total_loss / num_batches})
    
    return total_loss / num_batches

# ==================== 检查结果 ====================
# 语法检查: [待检查]
# 功能检查: [待检查]
```

### 54.2 文本生成练习

#### 练习13：实现贪婪解码

```python
# ==================== 练习说明 ====================
# 目标：实现贪婪解码生成文本
# 要求：
# 1. 函数名：greedy_decode
# 2. 参数：model, tokenizer, prompt, max_new_tokens, device
# 3. 功能：
#    - 编码提示
#    - 循环生成token
#    - 每次选择概率最高的token
#    - 解码生成的token
# 4. 返回：生成的文本

# ==================== 编写区域 ====================
# 请在下方编写你的代码：

import torch

def greedy_decode(model, tokenizer, prompt, max_new_tokens, device):
    """
    贪婪解码生成文本
    
    参数：
    - model: 语言模型
    - tokenizer: 分词器
    - prompt: 输入提示
    - max_new_tokens: 最大生成token数
    - device: 设备
    
    返回：
    - generated_text: 生成的文本
    """
    # 请在此编写你的代码
    pass

# ==================== 测试代码 ====================
# 使用前面定义的SimpleModel和SimpleTokenizer测试
model = SimpleModel(vocab_size=100, dim=32)
vocab = {'hello': 2, 'world': 3, 'python': 4, '<unk>': 1, '<pad>': 0}
tokenizer = SimpleTokenizerReference(vocab)

device = torch.device('cpu')
generated = greedy_decode(model, tokenizer, "hello", max_new_tokens=5, device=device)
print(f"生成结果: {generated}")

# ==================== 对照区域 ====================
# 参考实现：

def greedy_decode_reference(model, tokenizer, prompt, max_new_tokens, device):
    """
    贪婪解码生成文本 - 参考实现
    
    原理：
    - 每次选择概率最高的token
    - 简单但可能重复
    
    步骤：
    1. 编码提示
    2. 循环生成
    3. 获取下一个token
    4. 拼接
    5. 解码
    
    参数：
    - model: 语言模型
    - tokenizer: 分词器
    - prompt: 输入提示
    - max_new_tokens: 最大生成token数
    - device: 设备
    
    返回：
    - generated_text: 生成的文本
    """
    model.eval()
    
    # 编码提示
    input_ids = tokenizer.encode(prompt)
    input_ids = torch.tensor([input_ids], device=device)
    
    # 生成循环
    with torch.no_grad():
        for _ in range(max_new_tokens):
            # 前向传播
            logits = model(input_ids)
            
            # 获取最后一个位置的logits
            next_token_logits = logits[0, -1, :]
            
            # 贪婪选择：取最大概率的token
            next_token = torch.argmax(next_token_logits).unsqueeze(0)
            
            # 拼接
            input_ids = torch.cat([input_ids, next_token.unsqueeze(0)], dim=-1)
    
    # 解码
    generated_text = tokenizer.decode(input_ids[0].tolist())
    
    return generated_text

# ==================== 检查结果 ====================
# 语法检查: [待检查]
# 功能检查: [待检查]
```

#### 练习14：实现Top-K采样

```python
# ==================== 练习说明 ====================
# 目标：实现Top-K采样生成文本
# 要求：
# 1. 函数名：top_k_sample
# 2. 参数：model, tokenizer, prompt, max_new_tokens, top_k, temperature, device
# 3. 功能：
#    - 只保留概率最高的K个token
#    - 应用温度调节
#    - 从分布中采样
# 4. 返回：生成的文本

# ==================== 编写区域 ====================
# 请在下方编写你的代码：

import torch
import torch.nn.functional as F

def top_k_sample(model, tokenizer, prompt, max_new_tokens, top_k=50, temperature=1.0, device='cpu'):
    """
    Top-K采样生成文本
    
    参数：
    - model: 语言模型
    - tokenizer: 分词器
    - prompt: 输入提示
    - max_new_tokens: 最大生成token数
    - top_k: 只考虑概率最高的K个token
    - temperature: 温度参数，控制随机性
    - device: 设备
    
    返回：
    - generated_text: 生成的文本
    """
    # 请在此编写你的代码
    pass

# ==================== 测试代码 ====================
# 测试你的实现
model = SimpleModel(vocab_size=100, dim=32)
generated = top_k_sample(model, tokenizer, "hello", max_new_tokens=10, top_k=10, temperature=0.8)
print(f"生成结果: {generated}")

# 多次生成，验证随机性
print("\n多次生成:")
for i in range(3):
    gen = top_k_sample(model, tokenizer, "hello", max_new_tokens=5, top_k=10, temperature=1.0)
    print(f"  生成{i+1}: {gen}")

# ==================== 对照区域 ====================
# 参考实现：

def top_k_sample_reference(model, tokenizer, prompt, max_new_tokens, top_k=50, temperature=1.0, device='cpu'):
    """
    Top-K采样生成文本 - 参考实现
    
    原理：
    1. 只保留概率最高的K个token
    2. 将其他token的概率设为负无穷
    3. 应用温度调节
    4. 从分布中采样
    
    参数：
    - model: 语言模型
    - tokenizer: 分词器
    - prompt: 输入提示
    - max_new_tokens: 最大生成token数
    - top_k: 只考虑概率最高的K个token
    - temperature: 温度参数，控制随机性
    - device: 设备
    
    返回：
    - generated_text: 生成的文本
    """
    model.eval()
    
    # 编码提示
    input_ids = tokenizer.encode(prompt)
    input_ids = torch.tensor([input_ids], device=device)
    
    # 生成循环
    with torch.no_grad():
        for _ in range(max_new_tokens):
            # 前向传播
            logits = model(input_ids)
            
            # 获取最后一个位置的logits
            next_token_logits = logits[0, -1, :] / temperature
            
            # Top-K过滤
            if top_k > 0:
                # 获取第K大的值
                top_k_logits, _ = torch.topk(next_token_logits, top_k)
                threshold = top_k_logits[-1]
                
                # 将小于阈值的设为负无穷
                next_token_logits[next_token_logits < threshold] = float('-inf')
            
            # 计算概率
            probs = F.softmax(next_token_logits, dim=-1)
            
            # 采样
            next_token = torch.multinomial(probs, num_samples=1)
            
            # 拼接
            input_ids = torch.cat([input_ids, next_token.unsqueeze(0)], dim=-1)
    
    # 解码
    generated_text = tokenizer.decode(input_ids[0].tolist())
    
    return generated_text

# ==================== 检查结果 ====================
# 语法检查: [待检查]
# 功能检查: [待检查]
```

---

## 第五十五部分：交互式代码练习 - 完整项目篇

### 55.1 构建完整的语言模型

#### 练习15：实现MiniMind语言模型

```python
# ==================== 练习说明 ====================
# 目标：整合所有组件，实现完整的MiniMind语言模型
# 要求：
# 1. 类名：MiniMind
# 2. 继承nn.Module
# 3. 方法：
#    - __init__(self, config): 初始化
#    - forward(self, input_ids): 前向传播
#    - generate(self, input_ids, max_new_tokens): 生成
# 4. 组件：
#    - Token Embedding
#    - Position Embedding (RoPE)
#    - N个TransformerBlock
#    - 最终的RMSNorm
#    - 输出投影

# ==================== 编写区域 ====================
# 请在下方编写你的代码：

import torch
import torch.nn as nn
from dataclasses import dataclass

@dataclass
class MiniMindConfig:
    vocab_size: int = 6400
    dim: int = 512
    n_layers: int = 8
    n_heads: int = 8
    max_seq_len: int = 512
    dropout: float = 0.1

class MiniMind(nn.Module):
    def __init__(self, config):
        # 请在此编写初始化代码
        pass
    
    def forward(self, input_ids):
        # 请在此编写前向传播代码
        pass
    
    def generate(self, input_ids, max_new_tokens, temperature=1.0, top_k=50):
        # 请在此编写生成代码
        pass

# ==================== 测试代码 ====================
# 测试你的实现
config = MiniMindConfig(
    vocab_size=1000,
    dim=128,
    n_layers=4,
    n_heads=4,
    max_seq_len=256
)

model = MiniMind(config)

# 测试前向传播
batch_size, seq_len = 2, 32
input_ids = torch.randint(0, config.vocab_size, (batch_size, seq_len))
logits = model(input_ids)

print(f"输入形状: {input_ids.shape}")
print(f"输出形状: {logits.shape}")  # 期望: torch.Size([2, 32, 1000])

# 测试生成
prompt = torch.randint(0, config.vocab_size, (1, 10))
generated = model.generate(prompt, max_new_tokens=20, temperature=0.8, top_k=50)
print(f"生成长度: {generated.shape[1]}")  # 期望: 30

# 计算参数量
total_params = sum(p.numel() for p in model.parameters())
print(f"参数量: {total_params:,}")

# ==================== 对照区域 ====================
# 参考实现：

class MiniMindReference(nn.Module):
    """
    MiniMind语言模型 - 参考实现
    
    架构：
    - Token Embedding
    - RoPE位置编码
    - N个TransformerBlock
    - 最终RMSNorm
    - 输出投影（与embedding共享权重）
    
    特点：
    - Decoder-only架构
    - Pre-Norm
    - RMSNorm
    - SwiGLU
    - RoPE
    """
    
    def __init__(self, config):
        super().__init__()
        
        self.config = config
        
        # Token Embedding
        self.tok_embeddings = nn.Embedding(config.vocab_size, config.dim)
        
        # Transformer块
        self.layers = nn.ModuleList([
            TransformerBlockReference(
                config.dim,
                config.n_heads,
                mlp_ratio=4,
                dropout=config.dropout
            )
            for _ in range(config.n_layers)
        ])
        
        # 最终归一化
        self.norm = RMSNormReference(config.dim)
        
        # 输出投影（与embedding共享权重）
        self.output = nn.Linear(config.dim, config.vocab_size, bias=False)
        
        # 权重共享
        self.output.weight = self.tok_embeddings.weight
        
        # RoPE
        self.rope = RotaryPositionEmbeddingReference(config.dim // config.n_heads)
        
        # Dropout
        self.dropout = nn.Dropout(config.dropout)
        
        # 初始化
        self._init_weights()
    
    def _init_weights(self):
        """初始化权重"""
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.normal_(module.weight, mean=0.0, std=0.02)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)
            elif isinstance(module, nn.Embedding):
                nn.init.normal_(module.weight, mean=0.0, std=0.02)
    
    def forward(self, input_ids):
        """
        前向传播
        
        参数：
        - input_ids: (batch, seq_len)
        
        返回：
        - logits: (batch, seq_len, vocab_size)
        """
        batch_size, seq_len = input_ids.shape
        
        # Token Embedding
        x = self.tok_embeddings(input_ids)  # (batch, seq_len, dim)
        x = self.dropout(x)
        
        # 因果mask
        mask = torch.triu(
            torch.ones(seq_len, seq_len, device=input_ids.device),
            diagonal=1
        ).bool()
        
        # Transformer块
        for layer in self.layers:
            x = layer(x, mask)
        
        # 最终归一化
        x = self.norm(x)
        
        # 输出投影
        logits = self.output(x)
        
        return logits
    
    def generate(self, input_ids, max_new_tokens, temperature=1.0, top_k=50):
        """
        生成文本
        
        参数：
        - input_ids: (batch, seq_len)
        - max_new_tokens: 最大生成token数
        - temperature: 温度参数
        - top_k: Top-K采样
        
        返回：
        - generated_ids: (batch, seq_len + max_new_tokens)
        """
        self.eval()
        
        with torch.no_grad():
            for _ in range(max_new_tokens):
                # 前向传播
                logits = self(input_ids)
                
                # 获取最后一个位置
                next_token_logits = logits[:, -1, :] / temperature
                
                # Top-K
                if top_k > 0:
                    top_k_logits, _ = torch.topk(next_token_logits, top_k)
                    threshold = top_k_logits[:, -1].unsqueeze(-1)
                    next_token_logits[next_token_logits < threshold] = float('-inf')
                
                # 采样
                probs = F.softmax(next_token_logits, dim=-1)
                next_token = torch.multinomial(probs, num_samples=1)
                
                # 拼接
                input_ids = torch.cat([input_ids, next_token], dim=-1)
        
        return input_ids

# ==================== 检查结果 ====================
# 语法检查: [待检查]
# 功能检查: [待检查]
# 架构验证: [待验证]
```

---

## 第五十六部分：交互式代码练习 - 高级主题篇

### 56.1 KV Cache实现

#### 练习16：实现KV Cache优化

```python
# ==================== 练习说明 ====================
# 目标：实现KV Cache以加速推理
# 要求：
# 1. 类名：KVCache
# 2. 方法：
#    - __init__(self, n_layers, n_heads, head_dim, max_seq_len)
#    - update(self, layer_idx, key, value): 更新缓存
#    - get(self, layer_idx): 获取缓存
#    - clear(): 清空缓存
# 3. 预分配内存以提高效率

# ==================== 编写区域 ====================
# 请在下方编写你的代码：

import torch

class KVCache:
    def __init__(self, n_layers, n_heads, head_dim, max_seq_len, dtype=torch.float16):
        # 请在此编写初始化代码
        pass
    
    def update(self, layer_idx, key, value):
        # 请在此编写更新代码
        pass
    
    def get(self, layer_idx):
        # 请在此编写获取代码
        pass
    
    def clear(self):
        # 请在此编写清空代码
        pass

# ==================== 测试代码 ====================
# 测试你的实现
n_layers, n_heads, head_dim, max_seq_len = 8, 8, 64, 512
cache = KVCache(n_layers, n_heads, head_dim, max_seq_len)

batch_size = 2
device = torch.device('cpu')

# 模拟逐token生成
for step in range(5):
    key = torch.randn(batch_size, n_heads, 1, head_dim)
    value = torch.randn(batch_size, n_heads, 1, head_dim)
    
    cache.update(0, key, value)
    
    cached_k, cached_v = cache.get(0)
    print(f"Step {step+1}: 缓存形状 K={cached_k.shape}, V={cached_v.shape}")

# ==================== 对照区域 ====================
# 参考实现：

class KVCacheReference:
    """
    KV Cache - 参考实现
    
    用途：
    - 缓存之前计算的Key和Value
    - 避免重复计算
    - 显著加速推理
    
    原理：
    - 自回归生成时，之前的KV不变
    - 只需计算新token的KV
    - 拼接新旧KV
    """
    
    def __init__(self, n_layers, n_heads, head_dim, max_seq_len, dtype=torch.float16):
        self.n_layers = n_layers
        self.n_heads = n_heads
        self.head_dim = head_dim
        self.max_seq_len = max_seq_len
        self.dtype = dtype
        
        # 当前序列长度
        self.seq_len = 0
        
        # 预分配缓存
        # 形状：(n_layers, 2, batch, n_heads, max_seq_len, head_dim)
        # 2 for key and value
        self.cache = None
    
    def allocate(self, batch_size, device):
        """分配缓存内存"""
        self.cache = torch.zeros(
            self.n_layers, 2, batch_size,
            self.n_heads, self.max_seq_len, self.head_dim,
            dtype=self.dtype, device=device
        )
        self.seq_len = 0
    
    def update(self, layer_idx, key, value):
        """
        更新缓存
        
        参数：
        - layer_idx: 层索引
        - key: (batch, n_heads, 1, head_dim) 新的key
        - value: (batch, n_heads, 1, head_dim) 新的value
        
        返回：
        - cached_key: (batch, n_heads, seq_len+1, head_dim)
        - cached_value: (batch, n_heads, seq_len+1, head_dim)
        """
        # 存储新的KV
        self.cache[layer_idx, 0, :, :, self.seq_len:self.seq_len+1, :] = key
        self.cache[layer_idx, 1, :, :, self.seq_len:self.seq_len+1, :] = value
        
        self.seq_len += 1
        
        # 返回完整KV
        return (
            self.cache[layer_idx, 0, :, :, :self.seq_len, :],
            self.cache[layer_idx, 1, :, :, :self.seq_len, :]
        )
    
    def get(self, layer_idx):
        """获取当前缓存"""
        return (
            self.cache[layer_idx, 0, :, :, :self.seq_len, :],
            self.cache[layer_idx, 1, :, :, :self.seq_len, :]
        )
    
    def clear(self):
        """清空缓存"""
        if self.cache is not None:
            self.cache.zero_()
        self.seq_len = 0

# ==================== 检查结果 ====================
# 语法检查: [待检查]
# 功能检查: [待检查]
```

### 56.2 混合精度训练

#### 练习17：实现混合精度训练

```python
# ==================== 练习说明 ====================
# 目标：实现混合精度训练以加速训练和减少显存
# 要求：
# 1. 类名：MixedPrecisionTrainer
# 2. 方法：
#    - __init__(self, model, optimizer, use_bf16=False)
#    - training_step(self, batch): 执行一步训练
# 3. 使用torch.cuda.amp
# 4. 支持FP16和BF16

# ==================== 编写区域 ====================
# 请在下方编写你的代码：

import torch
import torch.nn as nn
from torch.cuda.amp import autocast, GradScaler

class MixedPrecisionTrainer:
    def __init__(self, model, optimizer, use_bf16=False):
        # 请在此编写初始化代码
        pass
    
    def training_step(self, batch):
        # 请在此编写训练步骤代码
        pass

# ==================== 测试代码 ====================
# 测试你的实现（需要GPU）
if torch.cuda.is_available():
    model = SimpleModel(vocab_size=1000, dim=128).cuda()
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    
    trainer = MixedPrecisionTrainer(model, optimizer, use_bf16=False)
    
    # 模拟训练
    batch = torch.randint(0, 1000, (4, 32)).cuda()
    loss = trainer.training_step(batch)
    print(f"损失: {loss:.4f}")
else:
    print("需要GPU来测试混合精度训练")

# ==================== 对照区域 ====================
# 参考实现：

class MixedPrecisionTrainerReference:
    """
    混合精度训练器 - 参考实现
    
    原理：
    - 前向传播使用FP16/BF16
    - 损失缩放防止梯度下溢
    - 权重更新使用FP32
    
    优势：
    - 减少显存约50%
    - 加速训练1.5-3倍
    - 几乎不损失精度
    """
    
    def __init__(self, model, optimizer, use_bf16=False):
        self.model = model
        self.optimizer = optimizer
        self.use_bf16 = use_bf16
        
        # 检查BF16支持
        if use_bf16 and not torch.cuda.is_bf16_supported():
            print("警告: GPU不支持BF16，将使用FP16")
            self.use_bf16 = False
        
        # 梯度缩放器（仅FP16需要）
        self.scaler = GradScaler() if not self.use_bf16 else None
        
        self.device = next(model.parameters()).device
    
    def training_step(self, batch):
        """
        执行一步训练
        
        参数：
        - batch: 输入batch
        
        返回：
        - loss: 损失值
        """
        self.model.train()
        
        # 移动数据到设备
        input_ids = batch.to(self.device)
        
        # 清零梯度
        self.optimizer.zero_grad()
        
        # 混合精度前向传播
        dtype = torch.bfloat16 if self.use_bf16 else torch.float16
        
        with autocast(dtype=dtype):
            logits = self.model(input_ids)
            
            # 计算损失
            shift_logits = logits[..., :-1, :].contiguous()
            shift_labels = input_ids[..., 1:].contiguous()
            
            loss = nn.functional.cross_entropy(
                shift_logits.view(-1, shift_logits.size(-1)),
                shift_labels.view(-1)
            )
        
        # 反向传播
        if self.scaler:
            self.scaler.scale(loss).backward()
            self.scaler.step(self.optimizer)
            self.scaler.update()
        else:
            loss.backward()
            self.optimizer.step()
        
        return loss.item()

# ==================== 检查结果 ====================
# 语法检查: [待检查]
# 功能检查: [待检查]
```

---

## 第五十七部分：交互式代码练习 - 实战应用篇

### 57.1 构建聊天机器人

#### 练习18：实现对话系统

```python
# ==================== 练习说明 ====================
# 目标：基于MiniMind实现一个简单的对话系统
# 要求：
# 1. 类名：ChatBot
# 2. 方法：
#    - __init__(self, model, tokenizer, config)
#    - chat(self, message, history=None): 进行对话
#    - format_prompt(self, message, history): 格式化提示
# 3. 支持多轮对话
# 4. 支持对话历史管理

# ==================== 编写区域 ====================
# 请在下方编写你的代码：

import torch
from typing import List, Tuple, Optional

class ChatBot:
    def __init__(self, model, tokenizer, config):
        # 请在此编写初始化代码
        pass
    
    def format_prompt(self, message: str, history: Optional[List[Tuple[str, str]]] = None) -> str:
        # 请在此编写格式化代码
        pass
    
    def chat(self, message: str, history: Optional[List[Tuple[str, str]]] = None) -> Tuple[str, List[Tuple[str, str]]]:
        # 请在此编写对话代码
        pass

# ==================== 测试代码 ====================
# 测试你的实现
config = MiniMindConfig(vocab_size=1000, dim=128, n_layers=4, n_heads=4)
model = MiniMindReference(config)

# 创建简单tokenizer
vocab = {chr(i): i for i in range(100, 200)}
vocab['<unk>'] = 1
vocab['<pad>'] = 0
tokenizer = SimpleTokenizerReference(vocab)

bot = ChatBot(model, tokenizer, config)

# 测试对话
response, history = bot.chat("你好")
print(f"用户: 你好")
print(f"机器人: {response}")

response, history = bot.chat("今天天气怎么样？", history)
print(f"用户: 今天天气怎么样？")
print(f"机器人: {response}")

# ==================== 对照区域 ====================
# 参考实现：

class ChatBotReference:
    """
    对话机器人 - 参考实现
    
    功能：
    - 多轮对话
    - 对话历史管理
    - 提示格式化
    - 流式生成（可选）
    """
    
    def __init__(self, model, tokenizer, config):
        self.model = model
        self.tokenizer = tokenizer
        self.config = config
        self.device = next(model.parameters()).device
        
        # 生成配置
        self.max_new_tokens = 100
        self.temperature = 0.8
        self.top_k = 50
    
    def format_prompt(self, message: str, history: Optional[List[Tuple[str, str]]] = None) -> str:
        """
        格式化提示
        
        参数：
        - message: 用户消息
        - history: 对话历史 [(user_msg, bot_msg), ...]
        
        返回：
        - formatted_prompt: 格式化后的提示
        """
        prompt = ""
        
        # 添加历史对话
        if history:
            for user_msg, bot_msg in history:
                prompt += f"用户: {user_msg}\n"
                prompt += f"助手: {bot_msg}\n"
        
        # 添加当前消息
        prompt += f"用户: {message}\n"
        prompt += "助手: "
        
        return prompt
    
    def chat(self, message: str, history: Optional[List[Tuple[str, str]]] = None) -> Tuple[str, List[Tuple[str, str]]]:
        """
        进行对话
        
        参数：
        - message: 用户消息
        - history: 对话历史
        
        返回：
        - response: 机器人回复
        - new_history: 更新后的对话历史
        """
        # 格式化提示
        prompt = self.format_prompt(message, history)
        
        # 编码
        input_ids = self.tokenizer.encode(prompt)
        input_ids = torch.tensor([input_ids], device=self.device)
        
        # 生成
        output_ids = self.model.generate(
            input_ids,
            max_new_tokens=self.max_new_tokens,
            temperature=self.temperature,
            top_k=self.top_k
        )
        
        # 解码
        response = self.tokenizer.decode(output_ids[0].tolist())
        
        # 提取回复部分
        if "助手: " in response:
            response = response.split("助手: ")[-1]
        
        # 更新历史
        if history is None:
            history = []
        new_history = history + [(message, response)]
        
        return response, new_history

# ==================== 检查结果 ====================
# 语法检查: [待检查]
# 功能检查: [待检查]
```

---

## 第五十八部分：代码练习答案与解析

### 58.1 练习答案汇总

```python
"""
交互式代码练习答案与解析
========================

本节提供所有练习的完整答案和详细解析。

使用方法：
1. 先尝试自己编写代码
2. 遇到困难时查看提示
3. 完成后对照参考实现
4. 理解差异和改进点

评分标准：
- 语法正确：代码能运行
- 功能正确：输出符合预期
- 效率优化：算法复杂度合理
- 代码风格：可读性和可维护性
"""

# ==================== 练习1答案解析 ====================

def word_frequency_answer(text):
    """
    词频统计器 - 完整答案
    
    解析：
    1. 使用string.punctuation获取所有标点符号
    2. 遍历替换标点为空格
    3. split()分词
    4. 使用字典统计频率
    
    常见错误：
    - 忘记转换为小写
    - 标点符号处理不当
    - 空字符串未过滤
    """
    import string
    
    text = text.lower()
    
    for char in string.punctuation:
        text = text.replace(char, ' ')
    
    words = text.split()
    
    frequency = {}
    for word in words:
        if word:  # 过滤空字符串
            frequency[word] = frequency.get(word, 0) + 1
    
    return frequency


# ==================== 练习5答案解析 ====================

def scaled_dot_product_attention_answer(query, key, value, mask=None):
    """
    缩放点积注意力 - 完整答案
    
    解析：
    1. 计算QK^T得到注意力分数
    2. 除以sqrt(d_k)进行缩放
    3. 应用mask（可选）
    4. softmax得到注意力权重
    5. 与V相乘得到输出
    
    关键点：
    - 缩放因子防止梯度消失
    - mask使用负无穷
    - 注意维度变换
    
    常见错误：
    - 忘记缩放
    - mask方向错误
    - 维度顺序错误
    """
    d_k = query.size(-1)
    
    # 计算注意力分数
    scores = torch.matmul(query, key.transpose(-2, -1)) / math.sqrt(d_k)
    
    # 应用mask
    if mask is not None:
        scores = scores.masked_fill(mask, float('-inf'))
    
    # softmax
    attention_weights = F.softmax(scores, dim=-1)
    
    # 加权求和
    output = torch.matmul(attention_weights, value)
    
    return output, attention_weights


# ==================== 练习9答案解析 ====================

class RMSNormAnswer(nn.Module):
    """
    RMSNorm - 完整答案
    
    解析：
    1. 计算均方根(RMS)
    2. 用RMS归一化
    3. 乘以可学习的权重
    
    与LayerNorm对比：
    - LayerNorm: (x - mean) / std
    - RMSNorm: x / rms
    
    优势：
    - 计算量更小
    - 不需要计算均值
    - 在LLM中效果相近
    """
    
    def __init__(self, dim, eps=1e-6):
        super().__init__()
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(dim))
    
    def forward(self, x):
        rms = torch.sqrt(torch.mean(x ** 2, dim=-1, keepdim=True) + self.eps)
        return x / rms * self.weight


# ==================== 练习13答案解析 ====================

def greedy_decode_answer(model, tokenizer, prompt, max_new_tokens, device):
    """
    贪婪解码 - 完整答案
    
    解析：
    1. 编码输入
    2. 循环生成
    3. 每次取argmax
    4. 拼接新token
    5. 解码输出
    
    特点：
    - 确定性输出
    - 可能重复
    - 简单高效
    
    改进方向：
    - 添加温度参数
    - 使用Top-K/Top-P采样
    - 添加重复惩罚
    """
    model.eval()
    
    input_ids = tokenizer.encode(prompt)
    input_ids = torch.tensor([input_ids], device=device)
    
    with torch.no_grad():
        for _ in range(max_new_tokens):
            logits = model(input_ids)
            next_token_logits = logits[0, -1, :]
            next_token = torch.argmax(next_token_logits).unsqueeze(0)
            input_ids = torch.cat([input_ids, next_token.unsqueeze(0)], dim=-1)
    
    return tokenizer.decode(input_ids[0].tolist())
```

### 58.2 常见错误与调试技巧

```python
"""
常见错误与调试技巧
==================

本节总结代码练习中常见的错误和调试方法。
"""

# ==================== 常见错误1：维度错误 ====================

def dimension_error_example():
    """
    常见维度错误示例
    
    错误：RuntimeError: mat1 and mat2 shapes cannot be multiplied
    """
    # 错误示例
    x = torch.randn(2, 3, 4)  # (batch, seq, dim)
    W = torch.randn(5, 4)     # (out_dim, in_dim)
    
    # 错误：直接相乘
    # output = x @ W.T  # 错误！seq维度丢失
    
    # 正确做法
    output = x @ W.T  # 实际上这是对的，但要注意维度
    # output形状：(2, 3, 5)
    
    # 调试技巧：打印形状
    print(f"x.shape: {x.shape}")
    print(f"W.shape: {W.shape}")
    print(f"output.shape: {output.shape}")
    
    return output


# ==================== 常见错误2：梯度问题 ====================

def gradient_error_example():
    """
    常见梯度错误示例
    
    错误：RuntimeError: element 0 of tensors does not require grad
    """
    # 错误示例
    x = torch.randn(3, 4)
    W = torch.randn(4, 5)
    
    # 错误：没有requires_grad
    # output = x @ W
    # output.sum().backward()  # 错误！
    
    # 正确做法
    W = torch.randn(4, 5, requires_grad=True)
    output = x @ W
    output.sum().backward()
    
    print(f"W.grad: {W.grad.shape}")
    
    # 调试技巧：检查requires_grad
    print(f"W.requires_grad: {W.requires_grad}")


# ==================== 常见错误3：索引错误 ====================

def index_error_example():
    """
    常见索引错误示例
    
    错误：IndexError: index out of range
    """
    # 错误示例
    x = torch.randn(3, 4)
    
    # 错误：索引超出范围
    # value = x[0, 4]  # 错误！第二维最大索引是3
    
    # 正确做法
    value = x[0, 3]  # 正确
    
    # 调试技巧：先检查形状
    print(f"x.shape: {x.shape}")
    print(f"Valid indices: x[0:3, 0:4]")


# ==================== 调试技巧汇总 ====================

def debugging_tips():
    """
    调试技巧汇总
    """
    tips = """
    1. 打印形状
       print(f"tensor.shape: {tensor.shape}")
    
    2. 检查数据类型
       print(f"tensor.dtype: {tensor.dtype}")
    
    3. 检查设备
       print(f"tensor.device: {tensor.device}")
    
    4. 检查梯度
       print(f"param.requires_grad: {param.requires_grad}")
       print(f"param.grad: {param.grad}")
    
    5. 使用断言
       assert tensor.shape == expected_shape
    
    6. 使用torch.autograd.set_detect_anomaly(True)
       检测NaN梯度
    
    7. 使用torch.utils.bottleneck
       分析性能瓶颈
    
    8. 使用torch.profiler
       详细性能分析
    """
    print(tips)


# ==================== 运行测试 ====================

if __name__ == "__main__":
    print("="*60)
    print("常见错误示例")
    print("="*60)
    
    print("\n1. 维度错误示例:")
    dimension_error_example()
    
    print("\n2. 梯度错误示例:")
    gradient_error_example()
    
    print("\n3. 索引错误示例:")
    index_error_example()
    
    print("\n4. 调试技巧:")
    debugging_tips()
```

---

## 第五十九部分：MiniMind核心代码逐行解析

### 59.1 Transformer模型主体解析

```python
"""
MiniMind Transformer 模型核心代码逐行解析
==========================================

本节对MiniMind的核心代码进行逐行解析，帮助读者深入理解每个细节。
"""

# ==================== 模型配置类 ====================

@dataclass
class ModelArgs:
    """
    模型配置参数类
    
    逐行解析：
    """
    dim: int = 512
    # dim: 模型的隐藏维度
    # - 决定了所有线性层的输入输出维度
    # - 影响模型的表达能力
    # - 常见值：512, 768, 1024, 2048
    
    n_layers: int = 8
    # n_layers: Transformer层的数量
    # - 更深的模型可以学习更复杂的模式
    # - 但也会增加训练难度和计算量
    # - GPT-2 small: 12层, GPT-2 medium: 24层
    
    n_heads: int = 8
    # n_heads: 注意力头的数量
    # - 多头注意力允许模型同时关注不同位置
    # - dim必须能被n_heads整除
    # - 每个头的维度 = dim // n_heads
    
    vocab_size: int = 6400
    # vocab_size: 词表大小
    # - 决定了embedding矩阵的大小
    # - 需要与tokenizer匹配
    
    max_seq_len: int = 512
    # max_seq_len: 最大序列长度
    # - 限制了模型能处理的文本长度
    # - 影响位置编码和KV Cache的大小
    
    dropout: float = 0.1
    # dropout: Dropout概率
    # - 用于正则化，防止过拟合
    # - 训练时使用，推理时关闭


# ==================== Transformer主类逐行解析 ====================

class Transformer(nn.Module):
    """
    MiniMind Transformer模型主类
    
    这是整个模型的核心，让我们逐行解析：
    """
    
    def __init__(self, args: ModelArgs):
        """
        初始化函数逐行解析
        """
        super().__init__()
        # 调用父类nn.Module的初始化
        # 这是PyTorch模块必须的步骤
        
        # ============ 断言检查 ============
        assert args.dim % args.n_heads == 0
        # 确保dim能被n_heads整除
        # 因为多头注意力需要将dim分割成n_heads个头
        # 例如：dim=512, n_heads=8 -> 每个头64维
        
        # ============ 保存配置 ============
        self.args = args
        # 保存配置参数，供其他方法使用
        
        # ============ Token Embedding ============
        self.tok_embeddings = nn.Embedding(args.vocab_size, args.dim)
        # 创建词嵌入层
        # 参数：
        #   - vocab_size: 词表大小，决定有多少个不同的token
        #   - dim: 嵌入维度，每个token表示为dim维向量
        # 输入：token id序列 (batch, seq_len)
        # 输出：嵌入向量 (batch, seq_len, dim)
        # 参数量：vocab_size * dim
        
        # ============ Dropout层 ============
        self.dropout = nn.Dropout(args.dropout)
        # Dropout层用于正则化
        # 训练时随机将一部分激活设为0
        # 推理时自动关闭
        
        # ============ Transformer层 ============
        self.layers = nn.ModuleList()
        # 使用ModuleList存储多个Transformer层
        # ModuleList是PyTorch的容器，会自动注册子模块
        
        for _ in range(args.n_layers):
            self.layers.append(TransformerBlock(args))
        # 创建n_layers个Transformer块
        # 每个块包含：注意力层 + MLP层 + 归一化层
        
        # ============ 最终归一化 ============
        self.norm = RMSNorm(args.dim)
        # 在所有Transformer层之后进行最终归一化
        # 使用RMSNorm而非LayerNorm
        
        # ============ 输出层 ============
        self.output = nn.Linear(args.dim, args.vocab_size, bias=False)
        # 输出投影层，将隐藏状态映射到词表维度
        # bias=False: 不使用偏置，减少参数量
        
        # ============ 权重共享 ============
        self.output.weight = self.tok_embeddings.weight
        # 输出层与嵌入层共享权重
        # 好处：
        # 1. 减少参数量
        # 2. 输入输出空间一致，有助于学习
        # 这是GPT等模型常用的技巧
        
        # ============ 位置编码 ============
        # RoPE在注意力计算时应用，这里不需要单独的位置编码层
        
        # ============ 初始化权重 ============
        self._init_weights()
        # 使用自定义方法初始化权重
    
    def _init_weights(self):
        """
        权重初始化
        
        逐行解析：
        """
        # 使用正态分布初始化
        for module in self.modules():
            # 遍历所有子模块
            
            if isinstance(module, nn.Linear):
                # 对线性层
                nn.init.normal_(module.weight, mean=0.0, std=0.02)
                # 权重使用均值为0，标准差为0.02的正态分布
                # 0.02是Transformer常用的初始化标准差
                
                if module.bias is not None:
                    nn.init.zeros_(module.bias)
                    # 偏置初始化为0
            
            elif isinstance(module, nn.Embedding):
                # 对嵌入层
                nn.init.normal_(module.weight, mean=0.0, std=0.02)
                # 同样使用正态分布
    
    def forward(self, tokens: torch.Tensor):
        """
        前向传播
        
        逐行解析：
        """
        # ============ 输入检查 ============
        # tokens: (batch, seq_len)
        # batch: 批次大小
        # seq_len: 序列长度
        
        # ============ Token Embedding ============
        h = self.tok_embeddings(tokens)
        # 将token id转换为嵌入向量
        # h: (batch, seq_len, dim)
        
        h = self.dropout(h)
        # 应用dropout
        
        # ============ 因果掩码 ============
        # 创建因果掩码，确保只能看到之前的token
        seq_len = tokens.shape[1]
        mask = torch.triu(
            torch.ones(seq_len, seq_len, device=tokens.device),
            diagonal=1
        ).bool()
        # 解释：
        # torch.ones(seq_len, seq_len): 创建全1矩阵
        # torch.triu(..., diagonal=1): 取上三角（不含对角线）
        # .bool(): 转换为布尔类型
        # 结果：位置(i,j)为True表示位置i不应该看到位置j
        
        # ============ Transformer层 ============
        for layer in self.layers:
            h = layer(h, mask)
            # 逐层传递
            # 每层都会更新隐藏状态h
        
        # ============ 最终归一化 ============
        h = self.norm(h)
        # 应用最终的RMSNorm
        
        # ============ 输出投影 ============
        output = self.output(h)
        # 将隐藏状态投影到词表维度
        # output: (batch, seq_len, vocab_size)
        
        return output


# ==================== 练习：对照理解 ====================
#
# 请根据上面的解析，回答以下问题：
#
# 1. 为什么dim必须能被n_heads整除？
#    答：因为多头注意力需要将dim分割成n_heads个头
#
# 2. 为什么要共享embedding和output的权重？
#    答：减少参数量，输入输出空间一致
#
# 3. 因果掩码的作用是什么？
#    答：确保位置i只能看到位置0到i-1的信息
```

### 59.2 TransformerBlock逐行解析

```python
"""
TransformerBlock 逐行解析
=========================
"""

class TransformerBlock(nn.Module):
    """
    单个Transformer块
    
    结构：
    x -> Norm -> Attention -> + -> Norm -> MLP -> + -> output
    |                          |                      |
    ----------------------------                      |
    ---------------------------------------------------
    """
    
    def __init__(self, args: ModelArgs):
        """
        初始化逐行解析
        """
        super().__init__()
        
        # ============ 注意力相关 ============
        self.attention = Attention(args)
        # 创建注意力模块
        # 包含Q、K、V投影和注意力计算
        
        self.attention_norm = RMSNorm(args.dim)
        # 注意力前的归一化
        # Pre-Norm结构：先归一化再计算
        
        # ============ MLP相关 ============
        self.feed_forward = FeedForward(args)
        # 创建前馈网络
        # 通常是一个两层MLP，中间维度扩大4倍
        
        self.ffn_norm = RMSNorm(args.dim)
        # MLP前的归一化
        
        # 注意：这里没有dropout，因为在子模块内部处理
    
    def forward(self, x: torch.Tensor, mask: torch.Tensor):
        """
        前向传播逐行解析
        """
        # ============ 注意力子层 ============
        # 残差连接 + 注意力
        h = x + self.attention(self.attention_norm(x), mask)
        # 分解：
        # 1. self.attention_norm(x): 归一化
        # 2. self.attention(..., mask): 计算注意力
        # 3. x + ...: 残差连接
        
        # ============ MLP子层 ============
        # 残差连接 + MLP
        out = h + self.feed_forward(self.ffn_norm(h))
        # 同样的Pre-Norm + 残差结构
        
        return out


# ==================== 关键概念解释 ====================
#
# 1. Pre-Norm vs Post-Norm
#    - Pre-Norm: x + Sublayer(Norm(x))  <-- MiniMind使用
#    - Post-Norm: Norm(x + Sublayer(x))
#    - Pre-Norm训练更稳定
#
# 2. 残差连接的作用
#    - 缓解梯度消失
#    - 允许直接传递信息
#    - 使深层网络可训练
```

### 59.3 注意力机制逐行解析

```python
"""
Attention 注意力机制逐行解析
============================
"""

class Attention(nn.Module):
    """
    多头自注意力
    
    这是Transformer的核心组件
    """
    
    def __init__(self, args: ModelArgs):
        """
        初始化逐行解析
        """
        super().__init__()
        
        # ============ 配置保存 ============
        self.n_heads = args.n_heads
        self.dim = args.dim
        self.head_dim = args.dim // args.n_heads
        # head_dim: 每个注意力头的维度
        # 例如：dim=512, n_heads=8 -> head_dim=64
        
        # ============ 线性投影层 ============
        self.wq = nn.Linear(args.dim, args.dim, bias=False)
        self.wk = nn.Linear(args.dim, args.dim, bias=False)
        self.wv = nn.Linear(args.dim, args.dim, bias=False)
        # Q、K、V的投影层
        # 输入：dim维
        # 输出：dim维（会被分割成n_heads个头）
        # bias=False: 不使用偏置，减少参数
        
        self.wo = nn.Linear(args.dim, args.dim, bias=False)
        # 输出投影层
        # 将多头注意力的结果合并后投影回dim维
        
        # ============ 位置编码 ============
        # RoPE在forward中动态应用
        
        # ============ Dropout ============
        self.dropout = nn.Dropout(args.dropout)
    
    def forward(self, x: torch.Tensor, mask: torch.Tensor):
        """
        前向传播逐行解析
        """
        # ============ 获取形状信息 ============
        bsz, seqlen, _ = x.shape
        # bsz: batch size
        # seqlen: sequence length
        # _: dim (不需要单独保存)
        
        # ============ Q、K、V投影 ============
        q = self.wq(x)
        k = self.wk(x)
        v = self.wv(x)
        # 投影到Q、K、V空间
        # 形状：(batch, seq_len, dim)
        
        # ============ 重塑为多头形式 ============
        q = q.view(bsz, seqlen, self.n_heads, self.head_dim)
        k = k.view(bsz, seqlen, self.n_heads, self.head_dim)
        v = v.view(bsz, seqlen, self.n_heads, self.head_dim)
        # 将dim维度分割为n_heads * head_dim
        # 形状：(batch, seq_len, n_heads, head_dim)
        
        # ============ 调整维度顺序 ============
        q = q.transpose(1, 2)
        k = k.transpose(1, 2)
        v = v.transpose(1, 2)
        # 将n_heads维度移到前面
        # 形状：(batch, n_heads, seq_len, head_dim)
        # 这样每个头可以独立计算注意力
        
        # ============ 应用RoPE位置编码 ============
        q, k = apply_rotary_emb(q, k)
        # 旋转位置编码
        # 只应用于Q和K，不应用于V
        
        # ============ 计算注意力分数 ============
        scores = torch.matmul(q, k.transpose(-2, -1)) / math.sqrt(self.head_dim)
        # Q @ K^T / sqrt(d_k)
        # k.transpose(-2, -1): (batch, n_heads, head_dim, seq_len)
        # scores: (batch, n_heads, seq_len, seq_len)
        # 除以sqrt(head_dim)防止梯度消失
        
        # ============ 应用掩码 ============
        if mask is not None:
            scores = scores.masked_fill(mask, float('-inf'))
            # 将mask为True的位置设为负无穷
            # softmax后这些位置的概率为0
        
        # ============ Softmax ============
        scores = F.softmax(scores.float(), dim=-1)
        # 在最后一个维度上计算softmax
        # 得到注意力权重
        # 形状：(batch, n_heads, seq_len, seq_len)
        
        scores = self.dropout(scores)
        # 应用dropout
        
        # ============ 加权求和 ============
        output = torch.matmul(scores, v)
        # 注意力权重 @ V
        # output: (batch, n_heads, seq_len, head_dim)
        
        # ============ 合并多头 ============
        output = output.transpose(1, 2).contiguous().view(bsz, seqlen, -1)
        # transpose(1, 2): (batch, seq_len, n_heads, head_dim)
        # view(bsz, seqlen, -1): (batch, seq_len, dim)
        # contiguous(): 确保内存连续
        
        # ============ 输出投影 ============
        output = self.wo(output)
        # 投影回dim维
        # 形状：(batch, seq_len, dim)
        
        return output


# ==================== 练习：手动计算注意力 ====================
#
# 假设：
# - batch_size = 1
# - n_heads = 2
# - seq_len = 3
# - head_dim = 4
#
# 请手动计算：
# 1. Q的形状：(1, 2, 3, 4)
# 2. K^T的形状：(1, 2, 4, 3)
# 3. scores = Q @ K^T的形状：(1, 2, 3, 3)
# 4. output = scores @ V的形状：(1, 2, 3, 4)
```

### 59.4 RMSNorm逐行解析

```python
"""
RMSNorm 逐行解析
================
"""

class RMSNorm(nn.Module):
    """
    Root Mean Square Layer Normalization
    
    与LayerNorm的区别：
    - LayerNorm: (x - mean) / std
    - RMSNorm: x / rms
    
    RMSNorm计算量更小，效果相近
    """
    
    def __init__(self, dim: int, eps: float = 1e-6):
        """
        初始化逐行解析
        """
        super().__init__()
        
        self.eps = eps
        # eps: 防止除零的小常数
        
        self.weight = nn.Parameter(torch.ones(dim))
        # 可学习的缩放参数
        # 初始化为1
        # 形状：(dim,)
        # 注意：没有偏置参数
    
    def _norm(self, x: torch.Tensor):
        """
        归一化操作
        
        逐行解析：
        """
        # ============ 计算RMS ============
        # x: (batch, seq_len, dim)
        
        rms = x.pow(2).mean(-1, keepdim=True)
        # 计算平方的均值
        # x.pow(2): 元素平方
        # mean(-1): 在最后一个维度上求均值
        # keepdim=True: 保持维度
        # rms: (batch, seq_len, 1)
        
        rms = torch.sqrt(rms + self.eps)
        # 加eps防止除零
        # 开方得到RMS
        
        # ============ 归一化 ============
        return x / rms
        # 除以RMS
        # 结果：(batch, seq_len, dim)
    
    def forward(self, x: torch.Tensor):
        """
        前向传播
        
        逐行解析：
        """
        # ============ 类型转换 ============
        output = self._norm(x.float()).type_as(x)
        # 在float32精度下计算
        # 然后转回原类型（如float16）
        # 这是为了数值稳定性
        
        # ============ 缩放 ============
        return output * self.weight
        # 乘以可学习的权重
        # 形状：(batch, seq_len, dim)


# ==================== 练习：手动验证RMSNorm ====================
#
# 输入 x = [[1, 2, 3, 4]]
#
# 步骤：
# 1. x^2 = [[1, 4, 9, 16]]
# 2. mean(x^2) = (1+4+9+16)/4 = 7.5
# 3. rms = sqrt(7.5 + 1e-6) ≈ 2.74
# 4. x/rms = [[0.365, 0.730, 1.095, 1.460]]
# 5. x/rms * weight = [[0.365, 0.730, 1.095, 1.460]] (weight=1)
```

### 59.5 FeedForward (SwiGLU) 逐行解析

```python
"""
FeedForward 前馈网络逐行解析
============================
"""

class FeedForward(nn.Module):
    """
    前馈网络，使用SwiGLU激活
    
    结构：
    x -> W1 -> Swish -> * -> W3 -> output
         W2 ----------|
    
    SwiGLU(x) = Swish(xW1) * (xW2)
    """
    
    def __init__(self, args: ModelArgs):
        """
        初始化逐行解析
        """
        super().__init__()
        
        # ============ 计算隐藏维度 ============
        hidden_dim = 4 * args.dim
        # 通常隐藏维度是输入维度的4倍
        # 例如：dim=512 -> hidden_dim=2048
        
        hidden_dim = int(2 * hidden_dim / 3)
        # LLaMA风格的调整
        # 使参数量更规整
        # 例如：2048 * 2/3 ≈ 1365
        
        # ============ 自定义隐藏维度 ============
        hidden_dim = args.multiple_of * (
            (hidden_dim + args.multiple_of - 1) // args.multiple_of
        )
        # 向上取整到multiple_of的倍数
        # 为了硬件优化
        
        # ============ 线性层 ============
        self.w1 = nn.Linear(args.dim, hidden_dim, bias=False)
        # 门控分支
        # 输入：dim
        # 输出：hidden_dim
        
        self.w2 = nn.Linear(args.dim, hidden_dim, bias=False)
        # 值分支
        # 输入：dim
        # 输出：hidden_dim
        
        self.w3 = nn.Linear(hidden_dim, args.dim, bias=False)
        # 输出投影
        # 输入：hidden_dim
        # 输出：dim
    
    def forward(self, x: torch.Tensor):
        """
        前向传播逐行解析
        """
        # ============ 门控分支 ============
        gate = self.w1(x)
        # 形状：(batch, seq_len, hidden_dim)
        
        gate = F.silu(gate)
        # SiLU激活（也叫Swish）
        # SiLU(x) = x * sigmoid(x)
        # 比ReLU更平滑
        
        # ============ 值分支 ============
        value = self.w2(x)
        # 形状：(batch, seq_len, hidden_dim)
        # 不经过激活函数
        
        # ============ 门控操作 ============
        hidden = gate * value
        # 逐元素相乘
        # 形状：(batch, seq_len, hidden_dim)
        # 门控机制允许选择性地传递信息
        
        # ============ 输出投影 ============
        output = self.w3(hidden)
        # 形状：(batch, seq_len, dim)
        
        return output


# ==================== 练习：计算参数量 ====================
#
# 假设 dim=512, hidden_dim=1365
#
# w1参数量 = 512 * 1365 = 698,880
# w2参数量 = 512 * 1365 = 698,880
# w3参数量 = 1365 * 512 = 698,880
# 总参数量 = 2,096,640
#
# 对比标准MLP（两个线性层）：
# 标准 = dim * 4*dim + 4*dim * dim = 8 * dim^2 = 2,097,152
#
# SwiGLU参数量约为标准MLP的1.5倍
```

### 59.6 RoPE位置编码逐行解析

```python
"""
RoPE 旋转位置编码逐行解析
=========================
"""

def precompute_freqs_cis(dim: int, end: int, theta: float = 10000.0):
    """
    预计算旋转角度
    
    逐行解析：
    """
    # ============ 计算频率 ============
    freqs = 1.0 / (theta ** (torch.arange(0, dim, 2)[: (dim // 2)].float() / dim))
    # 公式：freq_i = 1 / (theta^(2i/d))
    # theta: 基础频率，通常为10000
    # dim: 位置编码维度
    # 结果：频率数组，长度为dim/2
    
    # ============ 创建位置索引 ============
    t = torch.arange(end, device=freqs.device)
    # 位置索引：0, 1, 2, ..., end-1
    
    # ============ 外积 ============
    freqs = torch.outer(t, freqs).float()
    # 外积：位置 * 频率
    # freqs: (end, dim/2)
    # freqs[i, j] = i * freq_j
    
    # ============ 创建复数 ============
    freqs_cis = torch.polar(torch.ones_like(freqs), freqs)
    # 创建极坐标形式的复数
    # 模长为1，角度为freqs
    # e^(i*theta) = cos(theta) + i*sin(theta)
    
    return freqs_cis


def reshape_for_broadcast(freqs_cis: torch.Tensor, x: torch.Tensor):
    """
    调整形状以便广播
    
    逐行解析：
    """
    ndim = x.ndim
    assert 0 <= 1 < ndim
    
    # ============ 构造形状 ============
    shape = [d if i == 1 or i == ndim - 1 else 1 for i, d in enumerate(x.shape)]
    # 只保留第1维和最后一维
    # 其他维度设为1，以便广播
    
    return freqs_cis.view(*shape)


def apply_rotary_emb(
    xq: torch.Tensor,
    xk: torch.Tensor,
    freqs_cis: torch.Tensor,
) -> Tuple[torch.Tensor, torch.Tensor]:
    """
    应用旋转位置编码
    
    逐行解析：
    """
    # ============ 转换为复数 ============
    xq_ = torch.view_as_complex(xq.float().reshape(*xq.shape[:-1], -1, 2))
    xk_ = torch.view_as_complex(xk.float().reshape(*xk.shape[:-1], -1, 2))
    # 将最后一维分成两半，视为复数的实部和虚部
    # (batch, n_heads, seq_len, head_dim) -> (batch, n_heads, seq_len, head_dim/2)
    # 复数形式
    
    # ============ 广播频率 ============
    freqs_cis = reshape_for_broadcast(freqs_cis, xq_)
    # 调整频率的形状以便广播
    
    # ============ 旋转 ============
    xq_out = torch.view_as_real(xq_ * freqs_cis).flatten(3)
    xk_out = torch.view_as_real(xk_ * freqs_cis).flatten(3)
    # 复数乘法实现旋转
    # 然后转回实数形式
    # flatten(3)将最后两维展平
    
    return xq_out.type_as(xq), xk_out.type_as(xk)


# ==================== 练习：理解旋转 ====================
#
# 复数旋转原理：
# e^(i*theta) * (a + bi) = (a*cos(theta) - b*sin(theta)) + i*(a*sin(theta) + b*cos(theta))
#
# 这相当于将向量(a, b)旋转theta角度
#
# RoPE通过旋转将位置信息编码到Q和K中
# 位置差 = 角度差 -> 内积反映相对位置
```

---

## 第六十部分：代码练习与源码对照

### 60.1 练习：实现并对照MiniMind的Attention

```python
# ==================== 练习说明 ====================
# 目标：根据上面的源码解析，自己实现一个Attention模块
# 然后与MiniMind的实际代码对照

# ==================== 编写区域 ====================
# 请根据解析，实现以下类：

import torch
import torch.nn as nn
import torch.nn.functional as F
import math

class MyAttention(nn.Module):
    """
    自己实现的注意力模块
    
    参考59.3节的解析，实现以下功能：
    1. Q、K、V投影
    2. 多头分割
    3. 缩放点积注意力
    4. 输出投影
    """
    
    def __init__(self, dim, n_heads):
        super().__init__()
        # 请在此编写初始化代码
        # 提示：参考59.3节的解析
        pass
    
    def forward(self, x, mask=None):
        # 请在此编写前向传播代码
        # 提示：
        # 1. 投影Q、K、V
        # 2. 重塑为多头形式
        # 3. 计算注意力分数
        # 4. 应用mask
        # 5. softmax
        # 6. 加权求和
        # 7. 合并多头
        # 8. 输出投影
        pass

# ==================== 测试代码 ====================
def test_attention():
    dim, n_heads = 64, 8
    attn = MyAttention(dim, n_heads)
    
    batch_size, seq_len = 2, 10
    x = torch.randn(batch_size, seq_len, dim)
    
    output = attn(x)
    print(f"输入形状: {x.shape}")
    print(f"输出形状: {output.shape}")
    
    # 验证输出形状
    assert output.shape == x.shape, "输出形状应该与输入相同"
    print("测试通过！")

test_attention()

# ==================== 对照区域 ====================
# MiniMind实际实现（简化版）：

class MiniMindAttention(nn.Module):
    """MiniMind实际代码"""
    
    def __init__(self, dim, n_heads):
        super().__init__()
        self.n_heads = n_heads
        self.head_dim = dim // n_heads
        
        self.wq = nn.Linear(dim, dim, bias=False)
        self.wk = nn.Linear(dim, dim, bias=False)
        self.wv = nn.Linear(dim, dim, bias=False)
        self.wo = nn.Linear(dim, dim, bias=False)
    
    def forward(self, x, mask=None):
        bsz, seqlen, _ = x.shape
        
        # 投影
        q = self.wq(x)
        k = self.wk(x)
        v = self.wv(x)
        
        # 多头
        q = q.view(bsz, seqlen, self.n_heads, self.head_dim).transpose(1, 2)
        k = k.view(bsz, seqlen, self.n_heads, self.head_dim).transpose(1, 2)
        v = v.view(bsz, seqlen, self.n_heads, self.head_dim).transpose(1, 2)
        
        # 注意力
        scores = torch.matmul(q, k.transpose(-2, -1)) / math.sqrt(self.head_dim)
        if mask is not None:
            scores = scores.masked_fill(mask, float('-inf'))
        scores = F.softmax(scores, dim=-1)
        output = torch.matmul(scores, v)
        
        # 合并
        output = output.transpose(1, 2).contiguous().view(bsz, seqlen, -1)
        return self.wo(output)

# ==================== 对照检查 ====================
# 请对比你的实现与MiniMind的实现：
# 1. 初始化是否正确？
# 2. 维度变换是否正确？
# 3. 注意力计算是否正确？
# 4. 输出形状是否正确？
```

### 60.2 练习：实现并对照RMSNorm

```python
# ==================== 练习说明 ====================
# 目标：根据59.4节的解析，实现RMSNorm

# ==================== 编写区域 ====================
class MyRMSNorm(nn.Module):
    """
    自己实现的RMSNorm
    
    参考59.4节的解析，实现以下功能：
    1. 计算RMS
    2. 归一化
    3. 缩放
    """
    
    def __init__(self, dim, eps=1e-6):
        super().__init__()
        # 请在此编写初始化代码
        pass
    
    def forward(self, x):
        # 请在此编写前向传播代码
        # 公式：output = x / sqrt(mean(x^2) + eps) * weight
        pass

# ==================== 测试代码 ====================
def test_rmsnorm():
    dim = 64
    norm = MyRMSNorm(dim)
    
    x = torch.randn(2, 10, dim)
    output = norm(x)
    
    print(f"输入形状: {x.shape}")
    print(f"输出形状: {output.shape}")
    
    # 验证归一化效果
    input_rms = torch.sqrt(torch.mean(x ** 2, dim=-1))
    output_rms = torch.sqrt(torch.mean(output ** 2, dim=-1))
    print(f"输入RMS: {input_rms[0, 0].item():.4f}")
    print(f"输出RMS: {output_rms[0, 0].item():.4f}")

test_rmsnorm()

# ==================== 对照区域 ====================
# MiniMind实际实现：

class MiniMindRMSNorm(nn.Module):
    """MiniMind实际代码"""
    
    def __init__(self, dim, eps=1e-6):
        super().__init__()
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(dim))
    
    def _norm(self, x):
        return x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + self.eps)
    
    def forward(self, x):
        output = self._norm(x.float()).type_as(x)
        return output * self.weight

# ==================== 关键差异分析 ====================
# 1. torch.rsqrt vs 1/torch.sqrt
#    - rsqrt更高效
# 2. x.float()处理
#    - 在float32下计算，保证数值稳定性
# 3. type_as(x)
#    - 转回原类型
```

### 60.3 练习：实现并对照SwiGLU

```python
# ==================== 练习说明 ====================
# 目标：根据59.5节的解析，实现SwiGLU

# ==================== 编写区域 ====================
class MySwiGLU(nn.Module):
    """
    自己实现的SwiGLU
    
    参考59.5节的解析，实现以下功能：
    1. 两个分支：门控和值
    2. 门控分支使用SiLU激活
    3. 逐元素相乘
    4. 输出投影
    """
    
    def __init__(self, dim, hidden_dim):
        super().__init__()
        # 请在此编写初始化代码
        pass
    
    def forward(self, x):
        # 公式：SwiGLU(x) = Swish(xW1) * (xW2) * W3
        pass

# ==================== 测试代码 ====================
def test_swiglu():
    dim, hidden_dim = 64, 256
    swiglu = MySwiGLU(dim, hidden_dim)
    
    x = torch.randn(2, 10, dim)
    output = swiglu(x)
    
    print(f"输入形状: {x.shape}")
    print(f"输出形状: {output.shape}")
    
    # 验证参数量
    total_params = sum(p.numel() for p in swiglu.parameters())
    expected = dim * hidden_dim * 3  # w1 + w2 + w3
    print(f"参数量: {total_params} (期望: {expected})")

test_swiglu()

# ==================== 对照区域 ====================
# MiniMind实际实现：

class MiniMindFeedForward(nn.Module):
    """MiniMind实际代码"""
    
    def __init__(self, dim, hidden_dim):
        super().__init__()
        self.w1 = nn.Linear(dim, hidden_dim, bias=False)
        self.w2 = nn.Linear(dim, hidden_dim, bias=False)
        self.w3 = nn.Linear(hidden_dim, dim, bias=False)
    
    def forward(self, x):
        return self.w3(F.silu(self.w1(x)) * self.w2(x))

# ==================== 关键点 ====================
# 1. w1和w2都是dim -> hidden_dim
# 2. w3是hidden_dim -> dim
# 3. SiLU = Swish = x * sigmoid(x)
# 4. 门控机制：选择性地传递信息
```

---

## 第六十一部分：综合代码解析练习

### 61.1 阅读理解：分析MiniMind推理代码

```python
"""
阅读理解练习：分析MiniMind推理代码
===================================

请阅读以下代码，回答问题：
"""

@torch.no_grad()
def generate(
    model,
    tokens: torch.Tensor,
    max_new_tokens: int,
    temperature: float = 1.0,
    top_k: int = 50,
):
    """
    文本生成函数
    
    问题1：@torch.no_grad()的作用是什么？
    答：禁用梯度计算，节省内存，加速推理
    
    问题2：tokens的形状是什么？
    答：(batch_size, seq_len)
    """
    for _ in range(max_new_tokens):
        # 问题3：为什么要取最后max_seq_len个token？
        token_chunk = tokens[:, -model.args.max_seq_len:]
        # 答：防止序列超过模型最大长度
        
        # 前向传播
        logits = model(token_chunk)
        # 问题4：logits的形状是什么？
        # 答：(batch_size, seq_len, vocab_size)
        
        # 只取最后一个位置
        logits = logits[:, -1, :]
        # 问题5：为什么只取最后一个位置？
        # 答：自回归生成，只需要预测下一个token
        
        # 温度调节
        logits = logits / temperature
        # 问题6：温度越高，输出越确定还是越随机？
        # 答：温度越高，输出越随机
        
        # Top-K过滤
        if top_k > 0:
            v, _ = torch.topk(logits, min(top_k, logits.size(-1)))
            logits[logits < v[:, [-1]]] = float('-inf')
        # 问题7：Top-K的作用是什么？
        # 答：只保留概率最高的K个token，增加生成质量
        
        # Softmax
        probs = F.softmax(logits, dim=-1)
        
        # 采样
        next_token = torch.multinomial(probs, num_samples=1)
        # 问题8：multinomial的作用是什么？
        # 答：按概率采样，而非贪婪选择
        
        # 拼接
        tokens = torch.cat([tokens, next_token], dim=-1)
        # 问题9：这行代码的作用是什么？
        # 答：将新生成的token添加到序列末尾
    
    return tokens


# ==================== 练习：修改生成函数 ====================
#
# 请修改上面的generate函数，添加以下功能：
#
# 1. 添加重复惩罚（repetition_penalty）
#    提示：降低已出现token的概率
#
# 2. 添加停止条件（遇到特定token停止）
#    提示：检查next_token是否在stop_tokens中
#
# 3. 添加Top-P采样
#    提示：累积概率超过P后截断
```

### 61.2 调试练习：找出代码错误

```python
"""
调试练习：找出以下代码的错误
=============================
"""

# ==================== 错误代码1 ====================
def wrong_attention_1(x, n_heads):
    """有错误的注意力实现"""
    dim = x.size(-1)
    head_dim = dim // n_heads
    
    q = nn.Linear(dim, dim)(x)
    k = nn.Linear(dim, dim)(x)
    v = nn.Linear(dim, dim)(x)
    
    # 错误：维度变换错误
    q = q.view(-1, n_heads, head_dim)
    k = k.view(-1, n_heads, head_dim)
    v = v.view(-1, n_heads, head_dim)
    
    scores = torch.matmul(q, k.transpose(-2, -1))
    return torch.matmul(scores, v)

# 问题：上面的代码有什么错误？
# 答：view的维度不正确，缺少seq_len维度
# 正确：q.view(batch, seq_len, n_heads, head_dim).transpose(1, 2)


# ==================== 错误代码2 ====================
def wrong_rmsnorm_2(x, weight, eps=1e-6):
    """有错误的RMSNorm实现"""
    # 错误：没有keepdim=True
    rms = torch.sqrt(torch.mean(x ** 2, dim=-1) + eps)
    return x / rms * weight

# 问题：上面的代码有什么错误？
# 答：mean没有keepdim=True，导致广播失败
# 正确：torch.mean(x ** 2, dim=-1, keepdim=True)


# ==================== 错误代码3 ====================
def wrong_generate_3(model, tokens, max_tokens):
    """有错误的生成函数"""
    for _ in range(max_tokens):
        logits = model(tokens)
        next_token = torch.argmax(logits[:, -1, :], dim=-1)
        tokens = torch.cat([tokens, next_token], dim=-1)
    return tokens

# 问题：上面的代码有什么错误？
# 答：next_token需要增加一个维度才能拼接
# 正确：torch.cat([tokens, next_token.unsqueeze(-1)], dim=-1)


# ==================== 练习：修复所有错误 ====================
#
# 请修复上面三个函数的错误，并验证修复后的代码能正常运行。
```

### 61.3 性能优化练习

```python
"""
性能优化练习
============

分析并优化以下代码：
"""

# ==================== 原始代码 ====================
def slow_attention(q, k, v):
    """低效的注意力实现"""
    batch, heads, seq_len, head_dim = q.shape
    
    # 低效：使用循环
    output = torch.zeros_like(q)
    for b in range(batch):
        for h in range(heads):
            for i in range(seq_len):
                scores = []
                for j in range(seq_len):
                    score = torch.dot(q[b, h, i], k[b, h, j])
                    scores.append(score)
                scores = torch.tensor(scores)
                scores = F.softmax(scores, dim=0)
                for j in range(seq_len):
                    output[b, h, i] += scores[j] * v[b, h, j]
    
    return output

# 问题：这段代码为什么慢？
# 答：使用了多层Python循环，没有利用GPU并行计算


# ==================== 优化代码 ====================
def fast_attention(q, k, v):
    """高效的注意力实现"""
    # 使用矩阵运算代替循环
    d_k = q.size(-1)
    scores = torch.matmul(q, k.transpose(-2, -1)) / math.sqrt(d_k)
    scores = F.softmax(scores, dim=-1)
    return torch.matmul(scores, v)

# 优化点：
# 1. 使用矩阵乘法代替循环
# 2. 利用GPU并行计算
# 3. 减少内存分配


# ==================== 练习：优化KV Cache ====================
#
# 以下是一个简单的KV Cache实现，请分析其性能问题并优化：

class SimpleKVCache:
    def __init__(self):
        self.keys = []
        self.values = []
    
    def update(self, k, v):
        self.keys.append(k)
        self.values.append(v)
        return torch.cat(self.keys, dim=2), torch.cat(self.values, dim=2)
    
    def clear(self):
        self.keys = []
        self.values = []

# 问题：
# 1. 每次update都创建新的列表元素，效率低
# 2. 每次cat都重新分配内存
#
# 优化方向：
# 1. 预分配固定大小的缓存
# 2. 使用索引更新而非cat
```

---

## 第六十二部分：代码注释规范练习

### 62.1 为MiniMind代码添加注释

```python
"""
代码注释练习
============

为以下MiniMind核心代码添加详细注释：
"""

class Transformer(nn.Module):
    def __init__(self, args: ModelArgs):
        super().__init__()
        
        # TODO: 添加注释说明以下代码的作用
        assert args.dim % args.n_heads == 0
        
        self.tok_embeddings = nn.Embedding(args.vocab_size, args.dim)
        self.dropout = nn.Dropout(args.dropout)
        
        self.layers = nn.ModuleList()
        for _ in range(args.n_layers):
            self.layers.append(TransformerBlock(args))
        
        self.norm = RMSNorm(args.dim)
        self.output = nn.Linear(args.dim, args.vocab_size, bias=False)
        
        # TODO: 解释权重共享的好处
        self.output.weight = self.tok_embeddings.weight
    
    def forward(self, tokens: torch.Tensor):
        # TODO: 添加每一步的注释
        h = self.tok_embeddings(tokens)
        h = self.dropout(h)
        
        # TODO: 解释因果掩码的作用
        seq_len = tokens.shape[1]
        mask = torch.triu(
            torch.ones(seq_len, seq_len, device=tokens.device),
            diagonal=1
        ).bool()
        
        for layer in self.layers:
            h = layer(h, mask)
        
        h = self.norm(h)
        output = self.output(h)
        
        return output


# ==================== 参考注释 ====================
#
# 完整注释版本：
#
# class Transformer(nn.Module):
#     """MiniMind Transformer语言模型
#     
#     这是一个Decoder-only的Transformer模型，用于文本生成。
#     
#     架构特点：
#     - Pre-Norm结构
#     - RMSNorm归一化
#     - SwiGLU激活函数
#     - RoPE位置编码
#     - 权重共享
#     """
#     
#     def __init__(self, args: ModelArgs):
#         """初始化模型
#         
#         参数:
#             args: 模型配置参数
#         """
#         super().__init__()
#         
#         # 确保dim能被n_heads整除，这是多头注意力的要求
#         assert args.dim % args.n_heads == 0
#         
#         # Token嵌入层：将token id转换为向量表示
#         # 参数量 = vocab_size * dim
#         self.tok_embeddings = nn.Embedding(args.vocab_size, args.dim)
#         
#         # Dropout层：训练时随机丢弃部分神经元，防止过拟合
#         self.dropout = nn.Dropout(args.dropout)
#         
#         # Transformer层列表
#         # 每层包含自注意力和前馈网络
#         self.layers = nn.ModuleList()
#         for _ in range(args.n_layers):
#             self.layers.append(TransformerBlock(args))
#         
#         # 最终归一化层
#         self.norm = RMSNorm(args.dim)
#         
#         # 输出投影层：将隐藏状态映射到词表维度
#         self.output = nn.Linear(args.dim, args.vocab_size, bias=False)
#         
#         # 权重共享：输出层和嵌入层共享权重
#         # 好处：减少参数量，输入输出空间一致
#         self.output.weight = self.tok_embeddings.weight
#     
#     def forward(self, tokens: torch.Tensor):
#         """前向传播
#         
#         参数:
#             tokens: 输入token序列，形状为(batch_size, seq_len)
#         
#         返回:
#             output: 预测的logits，形状为(batch_size, seq_len, vocab_size)
#         """
#         # Token嵌入：将token id转换为向量
#         h = self.tok_embeddings(tokens)  # (batch, seq_len, dim)
#         h = self.dropout(h)
#         
#         # 创建因果掩码：确保每个位置只能看到之前的位置
#         # 上三角矩阵，True表示需要被遮蔽
#         seq_len = tokens.shape[1]
#         mask = torch.triu(
#             torch.ones(seq_len, seq_len, device=tokens.device),
#             diagonal=1
#         ).bool()
#         
#         # 通过所有Transformer层
#         for layer in self.layers:
#             h = layer(h, mask)
#         
#         # 最终归一化
#         h = self.norm(h)
#         
#         # 输出投影
#         output = self.output(h)
#         
#         return output
```

---

## 第六十三部分：常见问题解答(FAQ)

### 63.1 模型架构相关

```python
"""
MiniMind 常见问题解答 (FAQ)
==========================

本节收集了学习和使用MiniMind过程中最常见的问题。
"""

# ==================== Q1: 为什么使用RMSNorm而不是LayerNorm？ ====================

"""
Q: 为什么MiniMind使用RMSNorm而不是LayerNorm？

A: RMSNorm相比LayerNorm有几个优势：

1. 计算效率更高
   - LayerNorm: 需要计算均值和方差
   - RMSNorm: 只需要计算均方根
   
2. 效果相近
   - 在大规模语言模型上，两者效果差异很小
   - LLaMA、GPT-NeoX等都使用RMSNorm

3. 实现对比：
"""

class LayerNorm(nn.Module):
    """标准LayerNorm实现"""
    def __init__(self, dim, eps=1e-6):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(dim))
        self.bias = nn.Parameter(torch.zeros(dim))
        self.eps = eps
    
    def forward(self, x):
        mean = x.mean(-1, keepdim=True)
        var = x.var(-1, keepdim=True, unbiased=False)
        return self.weight * (x - mean) / torch.sqrt(var + self.eps) + self.bias

class RMSNorm(nn.Module):
    """RMSNorm实现"""
    def __init__(self, dim, eps=1e-6):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(dim))
        self.eps = eps
    
    def forward(self, x):
        rms = torch.sqrt(x.pow(2).mean(-1, keepdim=True) + self.eps)
        return self.weight * x / rms

# 计算量对比：
# LayerNorm: 2次reduce操作（mean和var）+ 2次广播操作
# RMSNorm: 1次reduce操作（mean）+ 1次广播操作


# ==================== Q2: RoPE和正弦位置编码有什么区别？ ====================

"""
Q: RoPE和正弦位置编码有什么区别？

A: 主要区别：

1. 应用位置
   - 正弦编码：在输入层添加到嵌入向量
   - RoPE：在注意力计算时应用于Q和K

2. 相对位置
   - 正弦编码：主要编码绝对位置
   - RoPE：天然编码相对位置关系

3. 长度外推
   - 正弦编码：超出训练长度效果下降
   - RoPE：更好的长度外推能力

4. 实现对比：
"""

def sinusoidal_positional_encoding(seq_len, dim):
    """正弦位置编码"""
    pe = torch.zeros(seq_len, dim)
    position = torch.arange(0, seq_len).unsqueeze(1)
    div_term = torch.exp(torch.arange(0, dim, 2) * (-math.log(10000.0) / dim))
    pe[:, 0::2] = torch.sin(position * div_term)
    pe[:, 1::2] = torch.cos(position * div_term)
    return pe

def apply_rope(q, k, seq_len, dim):
    """旋转位置编码（简化版）"""
    # 频率
    freqs = 1.0 / (10000 ** (torch.arange(0, dim, 2) / dim))
    # 位置
    t = torch.arange(seq_len)
    # 角度
    angles = torch.outer(t, freqs)
    # 旋转
    cos = torch.cos(angles)
    sin = torch.sin(angles)
    # 应用旋转...
    return q, k


# ==================== Q3: 为什么使用SwiGLU而不是ReLU？ ====================

"""
Q: 为什么MiniMind使用SwiGLU而不是ReLU？

A: SwiGLU的优势：

1. 性能更好
   - 在多个基准测试上优于ReLU和GELU
   - LLaMA、PaLM等模型都使用SwiGLU

2. 门控机制
   - 允许选择性地传递信息
   - 类似LSTM的门控思想

3. 梯度流动
   - Swish(x) = x * sigmoid(x)
   - 负值区域有非零梯度，避免神经元死亡

4. 对比：
"""

def relu_mlp(x, w1, w2):
    """标准ReLU MLP"""
    return w2(F.relu(w1(x)))

def swiglu_mlp(x, w1, w2, w3):
    """SwiGLU MLP"""
    return w3(F.silu(w1(x)) * w2(x))

# 参数量对比：
# ReLU MLP: dim * 4*dim + 4*dim * dim = 8 * dim^2
# SwiGLU: dim * hidden * 3 (约等于 8 * dim^2 * 1.5)


# ==================== Q4: 因果掩码的作用是什么？ ====================

"""
Q: 因果掩码的作用是什么？

A: 因果掩码确保：

1. 自回归特性
   - 位置i只能看到位置0到i-1的信息
   - 不能"偷看"未来的token

2. 训练和推理一致
   - 训练时模拟推理场景
   - 防止信息泄露

3. 实现方式：
"""

def create_causal_mask(seq_len):
    """创建因果掩码"""
    # 上三角矩阵（不含对角线）
    mask = torch.triu(torch.ones(seq_len, seq_len), diagonal=1).bool()
    return mask

# 示例：seq_len=4
# [[False, True,  True,  True ],
#  [False, False, True,  True ],
#  [False, False, False, True ],
#  [False, False, False, False]]

# True表示需要被遮蔽的位置


# ==================== Q5: 为什么使用Pre-Norm而不是Post-Norm？ ====================

"""
Q: 为什么MiniMind使用Pre-Norm而不是Post-Norm？

A: Pre-Norm的优势：

1. 训练稳定性
   - Pre-Norm梯度流动更稳定
   - 不需要学习率预热

2. 深层网络
   - Pre-Norm可以训练更深的网络
   - Post-Norm在深层网络容易梯度消失

3. 结构对比：
"""

# Pre-Norm (MiniMind使用)
# x -> Norm -> Sublayer -> + -> output
# |                          |
# ----------------------------

class PreNormBlock(nn.Module):
    def forward(self, x):
        h = x + self.attention(self.norm1(x))
        out = h + self.mlp(self.norm2(h))
        return out

# Post-Norm
# x -> Sublayer -> + -> Norm -> output
# |                |
# ------------------

class PostNormBlock(nn.Module):
    def forward(self, x):
        h = self.norm1(x + self.attention(x))
        out = self.norm2(h + self.mlp(h))
        return out
```

### 63.2 训练相关

```python
"""
训练相关常见问题
================
"""

# ==================== Q6: 混合精度训练会影响模型效果吗？ ====================

"""
Q: 混合精度训练会影响模型效果吗？

A: 通常不会，但需要注意：

1. 数值稳定性
   - 某些操作需要FP32精度（如softmax）
   - 使用loss scaling防止梯度下溢

2. 最佳实践：
"""

def safe_mixed_precision_training():
    """安全的混合精度训练"""
    scaler = GradScaler()
    
    for batch in dataloader:
        optimizer.zero_grad()
        
        # 使用autocast进行混合精度
        with autocast():
            output = model(input_ids)
            loss = criterion(output, labels)
        
        # 使用scaler进行梯度缩放
        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()


# ==================== Q7: 如何选择学习率？ ====================

"""
Q: 如何选择学习率？

A: 学习率选择策略：

1. 常用范围
   - 预训练：1e-4 到 5e-4
   - 微调：1e-5 到 1e-4

2. 学习率调度
   - 余弦退火（推荐）
   - 线性衰减
   - 常量学习率

3. 实现示例：
"""

def get_cosine_schedule(optimizer, num_warmup_steps, num_training_steps):
    """余弦学习率调度"""
    def lr_lambda(current_step):
        if current_step < num_warmup_steps:
            return float(current_step) / float(max(1, num_warmup_steps))
        progress = (current_step - num_warmup_steps) / (num_training_steps - num_warmup_steps)
        return max(0.0, 0.5 * (1.0 + math.cos(math.pi * progress)))
    
    return torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)


# ==================== Q8: 梯度累积如何实现？ ====================

"""
Q: 梯度累积如何实现？

A: 梯度累积用于模拟更大的batch size：

1. 原理
   - 多个小batch的梯度累加
   - 达到累积步数后更新参数

2. 实现：
"""

def train_with_gradient_accumulation(model, dataloader, optimizer, accumulation_steps=4):
    """带梯度累积的训练"""
    optimizer.zero_grad()
    
    for step, batch in enumerate(dataloader):
        # 前向传播
        output = model(batch)
        loss = criterion(output, labels)
        
        # 缩放损失
        loss = loss / accumulation_steps
        
        # 反向传播（累积梯度）
        loss.backward()
        
        # 达到累积步数时更新
        if (step + 1) % accumulation_steps == 0:
            # 梯度裁剪
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            # 更新参数
            optimizer.step()
            # 清零梯度
            optimizer.zero_grad()


# ==================== Q9: 如何处理训练中的NaN？ ====================

"""
Q: 如何处理训练中的NaN？

A: NaN的常见原因和解决方案：

1. 学习率过大
   - 降低学习率
   - 使用学习率预热

2. 梯度爆炸
   - 使用梯度裁剪
   - 检查模型初始化

3. 数值溢出
   - 使用混合精度训练
   - 检查输入数据

4. 调试方法：
"""

def detect_nan(model, optimizer):
    """检测NaN"""
    for name, param in model.named_parameters():
        if param.grad is not None:
            if torch.isnan(param.grad).any():
                print(f"NaN detected in gradient: {name}")
                return True
    return False

def safe_training_step(model, batch, optimizer, scaler=None):
    """安全的训练步骤"""
    optimizer.zero_grad()
    
    output = model(batch)
    loss = criterion(output, labels)
    
    if torch.isnan(loss):
        print("NaN detected in loss!")
        return None
    
    if scaler:
        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()
    else:
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
    
    return loss.item()
```

### 63.3 推理相关

```python
"""
推理相关常见问题
================
"""

# ==================== Q10: 如何提高生成质量？ ====================

"""
Q: 如何提高生成质量？

A: 多种技术可以提高生成质量：

1. 采样策略
   - Temperature调节
   - Top-K采样
   - Top-P采样

2. 重复惩罚
   - 降低已出现token的概率

3. 实现：
"""

def enhanced_generate(model, tokenizer, prompt, max_tokens=100, 
                      temperature=0.8, top_k=50, top_p=0.9,
                      repetition_penalty=1.1):
    """增强的生成函数"""
    input_ids = tokenizer.encode(prompt)
    input_ids = torch.tensor([input_ids])
    
    generated = input_ids.clone()
    
    for _ in range(max_tokens):
        # 前向传播
        logits = model(generated)
        next_logits = logits[0, -1, :] / temperature
        
        # 重复惩罚
        for token_id in generated[0]:
            next_logits[token_id] /= repetition_penalty
        
        # Top-K
        if top_k > 0:
            top_k_logits, _ = torch.topk(next_logits, top_k)
            next_logits[next_logits < top_k_logits[-1]] = float('-inf')
        
        # Top-P
        if top_p < 1.0:
            sorted_logits, sorted_indices = torch.sort(next_logits, descending=True)
            cumulative_probs = torch.cumsum(F.softmax(sorted_logits, dim=-1), dim=-1)
            sorted_indices_to_remove = cumulative_probs > top_p
            sorted_indices_to_remove[1:] = sorted_indices_to_remove[:-1].clone()
            sorted_indices_to_remove[0] = 0
            indices_to_remove = sorted_indices_to_remove.scatter(0, sorted_indices, sorted_indices_to_remove)
            next_logits[indices_to_remove] = float('-inf')
        
        # 采样
        probs = F.softmax(next_logits, dim=-1)
        next_token = torch.multinomial(probs, 1)
        
        generated = torch.cat([generated, next_token.unsqueeze(0)], dim=-1)
    
    return tokenizer.decode(generated[0].tolist())


# ==================== Q11: KV Cache如何加速推理？ ====================

"""
Q: KV Cache如何加速推理？

A: KV Cache避免重复计算：

1. 原理
   - 缓存之前计算的Key和Value
   - 只计算新token的KV

2. 加速效果
   - 推理速度提升2-3倍
   - 显存使用增加

3. 实现：
"""

class KVCacheInference:
    """带KV Cache的推理"""
    
    def __init__(self, model, max_seq_len):
        self.model = model
        self.max_seq_len = max_seq_len
        self.cache = None
    
    def generate(self, input_ids, max_new_tokens):
        """生成函数"""
        # 预填充阶段
        logits = self.model(input_ids, use_cache=True)
        self.cache = self.model.get_cache()
        
        generated = input_ids.clone()
        
        # 增量生成阶段
        for _ in range(max_new_tokens):
            # 只输入最后一个token
            next_logits = self.model(generated[:, -1:], use_cache=True, cache=self.cache)
            
            next_token = torch.argmax(next_logits[:, -1, :], dim=-1, keepdim=True)
            generated = torch.cat([generated, next_token], dim=-1)
        
        return generated


# ==================== Q12: 如何处理长文本？ ====================

"""
Q: 如何处理超过max_seq_len的长文本？

A: 几种处理方法：

1. 截断
   - 简单但可能丢失信息

2. 滑动窗口
   - 分段处理
   - 保持上下文连贯

3. 长度外推
   - RoPE支持一定程度的长度外推
   - 使用NTK-aware scaling

4. 实现：
"""

def sliding_window_generate(model, tokenizer, text, window_size=512, overlap=50):
    """滑动窗口处理长文本"""
    tokens = tokenizer.encode(text)
    
    if len(tokens) <= window_size:
        return model.generate(tokens)
    
    results = []
    
    for i in range(0, len(tokens), window_size - overlap):
        window = tokens[i:i + window_size]
        output = model.generate(window)
        results.append(output)
    
    # 合并结果
    return merge_results(results, overlap)
```

---

## 第六十四部分：学习检查点与测验

### 64.1 基础概念测验

```python
"""
MiniMind 学习检查点
===================

通过测验检验学习效果。
"""

# ==================== 测验1：Transformer基础 ====================

class TransformerQuiz:
    """
    Transformer基础测验
    
    请回答以下问题，然后查看答案。
    """
    
    @staticmethod
    def question_1():
        """
        问题1：Transformer中自注意力的计算公式是什么？
        
        请选择：
        A) softmax(QK)V
        B) softmax(QK^T / sqrt(d_k))V
        C) softmax(QK^T)V
        D) QK^T * V
        
        [思考空间]
        .
        .
        .
        
        答案：B
        
        解析：
        - QK^T：计算Query和Key的相似度
        - / sqrt(d_k)：缩放，防止梯度消失
        - softmax：归一化为概率
        - V：加权求和
        """
        pass
    
    @staticmethod
    def question_2():
        """
        问题2：多头注意力的作用是什么？
        
        请选择：
        A) 增加参数量
        B) 减少计算量
        C) 允许模型同时关注不同位置的不同表示子空间
        D) 加速训练
        
        [思考空间]
        .
        .
        .
        
        答案：C
        
        解析：
        多头注意力将输入分割到多个头，每个头学习不同的注意力模式，
        最后合并结果。这允许模型同时从多个角度理解输入。
        """
        pass
    
    @staticmethod
    def question_3():
        """
        问题3：RMSNorm与LayerNorm的主要区别是什么？
        
        请选择：
        A) RMSNorm不计算均值
        B) LayerNorm更高效
        C) RMSNorm有偏置参数
        D) 没有区别
        
        [思考空间]
        .
        .
        .
        
        答案：A
        
        解析：
        - LayerNorm: (x - mean) / std * weight + bias
        - RMSNorm: x / rms * weight
        RMSNorm不计算均值，也没有偏置参数，计算更高效。
        """
        pass
    
    @staticmethod
    def question_4():
        """
        问题4：RoPE位置编码的优势是什么？
        
        请选择：
        A) 计算更简单
        B) 天然编码相对位置，长度外推能力强
        C) 参数更少
        D) 只能用于编码器
        
        [思考空间]
        .
        .
        .
        
        答案：B
        
        解析：
        RoPE通过旋转向量编码位置，两个位置的相对位置关系
        通过旋转角度差体现，因此具有更好的长度外推能力。
        """
        pass


# ==================== 测验2：代码理解 ====================

class CodeUnderstandingQuiz:
    """
    代码理解测验
    """
    
    @staticmethod
    def question_1():
        """
        问题1：以下代码的作用是什么？
        
        ```python
        mask = torch.triu(torch.ones(seq_len, seq_len), diagonal=1).bool()
        scores = scores.masked_fill(mask, float('-inf'))
        ```
        
        请选择：
        A) 创建随机掩码
        B) 实现因果掩码，防止看到未来信息
        C) 加速计算
        D) 正则化
        
        [思考空间]
        .
        .
        .
        
        答案：B
        
        解析：
        - torch.triu创建上三角矩阵
        - masked_fill将上三角位置设为负无穷
        - softmax后这些位置的概率为0
        - 确保位置i只能看到位置0到i-1
        """
        pass
    
    @staticmethod
    def question_2():
        """
        问题2：以下代码有什么问题？
        
        ```python
        def attention(q, k, v):
            scores = q @ k.T
            return scores @ v
        ```
        
        请选择：
        A) 没有缩放
        B) 没有softmax
        C) 维度错误
        D) A和B都是
        
        [思考空间]
        .
        .
        .
        
        答案：D
        
        解析：
        1. 缺少缩放：应该除以sqrt(d_k)
        2. 缺少softmax：应该归一化为概率
        
        正确实现：
        ```python
        def attention(q, k, v):
            d_k = q.size(-1)
            scores = (q @ k.T) / math.sqrt(d_k)
            scores = F.softmax(scores, dim=-1)
            return scores @ v
        ```
        """
        pass
    
    @staticmethod
    def question_3():
        """
        问题3：以下代码的输出形状是什么？
        
        ```python
        x = torch.randn(2, 10, 64)  # (batch, seq, dim)
        q = nn.Linear(64, 64)(x)
        q = q.view(2, 10, 8, 8).transpose(1, 2)
        print(q.shape)
        ```
        
        请选择：
        A) (2, 10, 8, 8)
        B) (2, 8, 10, 8)
        C) (10, 2, 8, 8)
        D) (8, 2, 10, 8)
        
        [思考空间]
        .
        .
        .
        
        答案：B
        
        解析：
        1. x: (2, 10, 64)
        2. q: (2, 10, 64)
        3. view(2, 10, 8, 8): (batch, seq, heads, head_dim)
        4. transpose(1, 2): (batch, heads, seq, head_dim) = (2, 8, 10, 8)
        """
        pass


# ==================== 测验3：实践应用 ====================

class PracticalQuiz:
    """
    实践应用测验
    """
    
    @staticmethod
    def question_1():
        """
        问题1：训练时loss突然变成NaN，最可能的原因是什么？
        
        请选择：
        A) 数据太少
        B) 学习率过大
        C) 模型太小
        D) 批次太大
        
        [思考空间]
        .
        .
        .
        
        答案：B
        
        解析：
        学习率过大是最常见的原因，导致梯度爆炸。
        解决方法：
        1. 降低学习率
        2. 使用梯度裁剪
        3. 使用学习率预热
        """
        pass
    
    @staticmethod
    def question_2():
        """
        问题2：生成文本重复严重，应该如何调整？
        
        请选择：
        A) 增加temperature
        B) 降低temperature
        C) 使用重复惩罚
        D) B和C都可以
        
        [思考空间]
        .
        .
        .
        
        答案：D
        
        解析：
        1. 降低temperature使输出更确定，减少随机性导致的重复
        2. 重复惩罚直接降低已出现token的概率
        3. 两者可以结合使用
        """
        pass
    
    @staticmethod
    def question_3():
        """
        问题3：想要在有限显存下训练更大的batch，应该使用什么技术？
        
        请选择：
        A) 数据并行
        B) 梯度累积
        C) 混合精度
        D) B和C都可以
        
        [思考空间]
        .
        .
        .
        
        答案：D
        
        解析：
        1. 梯度累积：多个小batch累积梯度后更新
        2. 混合精度：使用FP16减少显存
        3. 两者结合效果更好
        """
        pass


# ==================== 综合测验 ====================

def run_comprehensive_quiz():
    """
    运行综合测验
    
    完成以下编程任务，检验学习效果。
    """
    
    print("="*60)
    print("MiniMind 综合测验")
    print("="*60)
    
    print("""
    任务1：实现一个简单的自注意力层
    要求：
    - 输入：x (batch, seq_len, dim)
    - 输出：(batch, seq_len, dim)
    - 使用缩放点积注意力
    
    任务2：实现RMSNorm
    要求：
    - 公式：output = x / sqrt(mean(x^2) + eps) * weight
    
    任务3：实现Top-K采样
    要求：
    - 只保留概率最高的K个token
    - 从分布中采样
    
    请在下方编写代码：
    """)
    
    # ==================== 编写区域 ====================
    
    class SelfAttention(nn.Module):
        def __init__(self, dim):
            super().__init__()
            # 请在此编写代码
            pass
        
        def forward(self, x):
            # 请在此编写代码
            pass
    
    class RMSNorm(nn.Module):
        def __init__(self, dim, eps=1e-6):
            super().__init__()
            # 请在此编写代码
            pass
        
        def forward(self, x):
            # 请在此编写代码
            pass
    
    def top_k_sample(logits, k):
        # 请在此编写代码
        pass
    
    # ==================== 参考答案 ====================
    
    print("\n" + "="*60)
    print("参考答案")
    print("="*60)
    
    print("""
    # 任务1答案：
    class SelfAttention(nn.Module):
        def __init__(self, dim):
            super().__init__()
            self.q = nn.Linear(dim, dim)
            self.k = nn.Linear(dim, dim)
            self.v = nn.Linear(dim, dim)
            self.scale = dim ** -0.5
        
        def forward(self, x):
            q = self.q(x)
            k = self.k(x)
            v = self.v(x)
            
            scores = (q @ k.transpose(-2, -1)) * self.scale
            scores = F.softmax(scores, dim=-1)
            return scores @ v
    
    # 任务2答案：
    class RMSNorm(nn.Module):
        def __init__(self, dim, eps=1e-6):
            super().__init__()
            self.weight = nn.Parameter(torch.ones(dim))
            self.eps = eps
        
        def forward(self, x):
            rms = torch.sqrt(x.pow(2).mean(-1, keepdim=True) + self.eps)
            return self.weight * x / rms
    
    # 任务3答案：
    def top_k_sample(logits, k):
        top_k_logits, top_k_indices = torch.topk(logits, k)
        probs = F.softmax(top_k_logits, dim=-1)
        idx = torch.multinomial(probs, 1)
        return top_k_indices[idx]
    """)


if __name__ == "__main__":
    run_comprehensive_quiz()
```

### 64.2 学习进度检查表

```python
"""
学习进度检查表
==============

使用此检查表跟踪学习进度。
"""

LEARNING_CHECKLIST = """
# MiniMind 学习进度检查表

## 第一阶段：基础理解
- [ ] 理解Transformer架构
- [ ] 理解自注意力机制
- [ ] 理解多头注意力
- [ ] 理解位置编码
- [ ] 理解残差连接
- [ ] 理解层归一化

## 第二阶段：组件实现
- [ ] 能实现RMSNorm
- [ ] 能实现缩放点积注意力
- [ ] 能实现多头注意力
- [ ] 能实现RoPE
- [ ] 能实现SwiGLU
- [ ] 能实现完整的TransformerBlock

## 第三阶段：模型训练
- [ ] 理解训练循环
- [ ] 理解损失函数
- [ ] 理解优化器
- [ ] 理解学习率调度
- [ ] 能实现混合精度训练
- [ ] 能实现梯度累积

## 第四阶段：推理优化
- [ ] 理解贪婪解码
- [ ] 理解采样策略
- [ ] 能实现Top-K采样
- [ ] 能实现Top-P采样
- [ ] 理解KV Cache
- [ ] 能优化推理速度

## 第五阶段：高级主题
- [ ] 理解模型量化
- [ ] 理解模型剪枝
- [ ] 理解知识蒸馏
- [ ] 理解分布式训练
- [ ] 能部署模型
- [ ] 能优化生产环境

## 实践项目
- [ ] 完成词频统计练习
- [ ] 完成分词器练习
- [ ] 完成注意力实现
- [ ] 完成RMSNorm实现
- [ ] 完成训练循环实现
- [ ] 完成文本生成实现
- [ ] 完成聊天机器人实现

## 自我评估
- 基础理解：__/10
- 代码实现：__/10
- 问题解决：__/10
- 项目实践：__/10
- 总体评分：__/40

建议：
- 30-40分：掌握良好，可以进阶学习
- 20-30分：基础扎实，需要更多实践
- 10-20分：需要复习基础概念
- 0-10分：建议从头学习
"""


def print_checklist():
    """打印学习检查表"""
    print(LEARNING_CHECKLIST)


if __name__ == "__main__":
    print_checklist()
```

---

## 第六十五部分：项目实战案例

### 65.1 实战案例：构建智能问答系统

```python
"""
实战案例：构建智能问答系统
==========================

本项目将使用MiniMind构建一个完整的智能问答系统。

功能：
- 文档理解
- 问题回答
- 多轮对话
- 知识检索
"""

import torch
import torch.nn as nn
from typing import List, Dict, Tuple, Optional
import json
import os


# ==================== 项目配置 ====================

@dataclass
class QAConfig:
    """问答系统配置"""
    model_name: str = "minimind-qa"
    model_path: str = "./models/minimind.pt"
    
    # 模型配置
    dim: int = 512
    n_layers: int = 8
    n_heads: int = 8
    vocab_size: int = 10000
    max_seq_len: int = 1024
    
    # 检索配置
    retrieval_top_k: int = 5
    chunk_size: int = 256
    chunk_overlap: int = 50
    
    # 生成配置
    max_answer_len: int = 256
    temperature: float = 0.7
    top_k: int = 40


# ==================== 文档处理 ====================

class DocumentProcessor:
    """
    文档处理器
    
    功能：
    - 文档分块
    - 文本清洗
    - 元数据提取
    """
    
    def __init__(self, chunk_size: int = 256, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def process_document(self, document: str, metadata: Dict = None) -> List[Dict]:
        """
        处理文档，返回分块列表
        
        参数：
        - document: 文档文本
        - metadata: 文档元数据
        
        返回：
        - 分块列表，每个分块包含文本和元数据
        """
        # 清洗文本
        text = self._clean_text(document)
        
        # 分块
        chunks = self._chunk_text(text)
        
        # 添加元数据
        result = []
        for i, chunk in enumerate(chunks):
            result.append({
                'id': f"chunk_{i}",
                'text': chunk,
                'metadata': metadata or {}
            })
        
        return result
    
    def _clean_text(self, text: str) -> str:
        """清洗文本"""
        # 移除多余空白
        text = ' '.join(text.split())
        # 移除特殊字符
        # ... 其他清洗逻辑
        return text
    
    def _chunk_text(self, text: str) -> List[str]:
        """文本分块"""
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), self.chunk_size - self.overlap):
            chunk = ' '.join(words[i:i + self.chunk_size])
            chunks.append(chunk)
        
        return chunks


# ==================== 检索系统 ====================

class SimpleRetriever:
    """
    简单检索系统
    
    使用TF-IDF或简单的向量相似度进行检索
    """
    
    def __init__(self):
        self.documents = []
        self.doc_vectors = None
    
    def index_documents(self, documents: List[Dict]):
        """索引文档"""
        self.documents = documents
        # 在实际应用中，这里会计算文档向量
        # self.doc_vectors = self._compute_vectors(documents)
    
    def retrieve(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        检索相关文档
        
        参数：
        - query: 查询文本
        - top_k: 返回的文档数量
        
        返回：
        - 相关文档列表
        """
        # 简单的关键词匹配
        results = []
        query_words = set(query.lower().split())
        
        for doc in self.documents:
            doc_words = set(doc['text'].lower().split())
            overlap = len(query_words & doc_words)
            results.append((doc, overlap))
        
        # 排序
        results.sort(key=lambda x: x[1], reverse=True)
        
        return [r[0] for r in results[:top_k]]


# ==================== 问答系统 ====================

class QASystem:
    """
    智能问答系统
    
    整合检索和生成功能
    """
    
    def __init__(self, model, tokenizer, config: QAConfig):
        self.model = model
        self.tokenizer = tokenizer
        self.config = config
        
        self.doc_processor = DocumentProcessor(
            chunk_size=config.chunk_size,
            overlap=config.chunk_overlap
        )
        
        self.retriever = SimpleRetriever()
    
    def add_knowledge(self, documents: List[str], metadata_list: List[Dict] = None):
        """
        添加知识库
        
        参数：
        - documents: 文档列表
        - metadata_list: 元数据列表
        """
        all_chunks = []
        
        for i, doc in enumerate(documents):
            metadata = metadata_list[i] if metadata_list else {}
            chunks = self.doc_processor.process_document(doc, metadata)
            all_chunks.extend(chunks)
        
        self.retriever.index_documents(all_chunks)
        print(f"已索引 {len(all_chunks)} 个文档块")
    
    def answer(self, question: str, use_retrieval: bool = True) -> Dict:
        """
        回答问题
        
        参数：
        - question: 问题
        - use_retrieval: 是否使用检索
        
        返回：
        - 包含答案和相关文档的字典
        """
        # 检索相关文档
        context = ""
        retrieved_docs = []
        
        if use_retrieval:
            retrieved_docs = self.retriever.retrieve(
                question, 
                top_k=self.config.retrieval_top_k
            )
            context = "\n".join([doc['text'] for doc in retrieved_docs])
        
        # 构建提示
        prompt = self._build_prompt(question, context)
        
        # 生成答案
        answer = self._generate(prompt)
        
        return {
            'question': question,
            'answer': answer,
            'context': context,
            'retrieved_docs': retrieved_docs
        }
    
    def _build_prompt(self, question: str, context: str) -> str:
        """构建提示"""
        if context:
            return f"""根据以下信息回答问题。如果信息中没有答案，请说"我不知道"。

信息：
{context}

问题：{question}

答案："""
        else:
            return f"问题：{question}\n答案："
    
    def _generate(self, prompt: str) -> str:
        """生成答案"""
        # 编码
        input_ids = self.tokenizer.encode(prompt)
        input_ids = torch.tensor([input_ids])
        
        # 生成
        output_ids = self.model.generate(
            input_ids,
            max_new_tokens=self.config.max_answer_len,
            temperature=self.config.temperature,
            top_k=self.config.top_k
        )
        
        # 解码
        answer = self.tokenizer.decode(output_ids[0].tolist())
        
        # 提取答案部分
        if "答案：" in answer:
            answer = answer.split("答案：")[-1].strip()
        
        return answer


# ==================== 使用示例 ====================

def demo_qa_system():
    """演示问答系统"""
    print("="*60)
    print("智能问答系统演示")
    print("="*60)
    
    # 创建配置
    config = QAConfig()
    
    # 这里需要实际加载模型
    # model = load_model(config.model_path)
    # tokenizer = load_tokenizer()
    
    # 创建问答系统
    # qa = QASystem(model, tokenizer, config)
    
    # 添加知识
    documents = [
        "MiniMind是一个小型语言模型，使用Transformer架构。它包含8层Transformer，每层有8个注意力头。",
        "训练MiniMind需要大量的文本数据。常用的数据集包括Wikipedia、Common Crawl等。",
        "MiniMind使用RMSNorm进行归一化，使用SwiGLU作为激活函数。"
    ]
    
    # qa.add_knowledge(documents)
    
    # 问答
    questions = [
        "MiniMind使用什么架构？",
        "训练MiniMind需要什么数据？",
        "MiniMind使用什么归一化方法？"
    ]
    
    print("\n问答演示:")
    for q in questions:
        print(f"\n问题: {q}")
        # result = qa.answer(q)
        # print(f"答案: {result['answer']}")
        print("(需要加载模型才能运行)")
    
    print("\n演示完成!")


if __name__ == "__main__":
    demo_qa_system()
```

### 65.2 实战案例：文本分类系统

```python
"""
实战案例：文本分类系统
======================

使用MiniMind构建文本分类系统。

功能：
- 情感分析
- 主题分类
- 意图识别
"""

import torch
import torch.nn as nn
from typing import List, Dict, Tuple
from dataclasses import dataclass


# ==================== 分类模型 ====================

class TextClassifier(nn.Module):
    """
    文本分类模型
    
    基于MiniMind的编码器，添加分类头
    """
    
    def __init__(self, base_model, num_classes: int, hidden_dim: int = 256):
        super().__init__()
        
        self.base_model = base_model
        
        # 分类头
        self.classifier = nn.Sequential(
            nn.Linear(base_model.args.dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim, num_classes)
        )
    
    def forward(self, input_ids: torch.Tensor) -> torch.Tensor:
        """
        前向传播
        
        参数：
        - input_ids: (batch, seq_len)
        
        返回：
        - logits: (batch, num_classes)
        """
        # 获取隐藏状态
        hidden_states = self.base_model(input_ids)
        
        # 使用最后一个位置的隐藏状态
        last_hidden = hidden_states[:, -1, :]
        
        # 分类
        logits = self.classifier(last_hidden)
        
        return logits
    
    def predict(self, input_ids: torch.Tensor) -> torch.Tensor:
        """预测类别"""
        logits = self.forward(input_ids)
        return torch.argmax(logits, dim=-1)


# ==================== 情感分析器 ====================

class SentimentAnalyzer:
    """
    情感分析器
    
    将文本分类为正面、负面或中性
    """
    
    def __init__(self, model, tokenizer, labels: List[str] = None):
        self.model = model
        self.tokenizer = tokenizer
        self.labels = labels or ['负面', '中性', '正面']
    
    def analyze(self, text: str) -> Dict:
        """
        分析文本情感
        
        参数：
        - text: 输入文本
        
        返回：
        - 包含情感标签和置信度的字典
        """
        # 编码
        input_ids = self.tokenizer.encode(text)
        input_ids = torch.tensor([input_ids])
        
        # 预测
        self.model.eval()
        with torch.no_grad():
            logits = self.model(input_ids)
            probs = torch.softmax(logits, dim=-1)
        
        # 获取结果
        pred_idx = torch.argmax(probs, dim=-1).item()
        confidence = probs[0, pred_idx].item()
        
        return {
            'text': text,
            'sentiment': self.labels[pred_idx],
            'confidence': confidence,
            'probabilities': {
                self.labels[i]: probs[0, i].item() 
                for i in range(len(self.labels))
            }
        }
    
    def batch_analyze(self, texts: List[str]) -> List[Dict]:
        """批量分析"""
        return [self.analyze(text) for text in texts]


# ==================== 意图识别器 ====================

class IntentRecognizer:
    """
    意图识别器
    
    识别用户输入的意图
    """
    
    def __init__(self, model, tokenizer, intents: List[str]):
        self.model = model
        self.tokenizer = tokenizer
        self.intents = intents
    
    def recognize(self, text: str) -> Dict:
        """
        识别意图
        
        参数：
        - text: 用户输入
        
        返回：
        - 意图和置信度
        """
        # 编码
        input_ids = self.tokenizer.encode(text)
        input_ids = torch.tensor([input_ids])
        
        # 预测
        self.model.eval()
        with torch.no_grad():
            logits = self.model(input_ids)
            probs = torch.softmax(logits, dim=-1)
        
        # 获取结果
        pred_idx = torch.argmax(probs, dim=-1).item()
        confidence = probs[0, pred_idx].item()
        
        return {
            'text': text,
            'intent': self.intents[pred_idx],
            'confidence': confidence
        }


# ==================== 使用示例 ====================

def demo_classifier():
    """演示分类系统"""
    print("="*60)
    print("文本分类系统演示")
    print("="*60)
    
    # 示例情感分析
    texts = [
        "这个产品非常好用，我很满意！",
        "质量太差了，完全不值这个价格。",
        "还行吧，没什么特别的。"
    ]
    
    print("\n情感分析示例:")
    for text in texts:
        print(f"文本: {text}")
        # result = analyzer.analyze(text)
        # print(f"情感: {result['sentiment']} (置信度: {result['confidence']:.2%})")
        print("(需要加载模型)")
    
    # 示例意图识别
    intents = ['查询天气', '播放音乐', '设置闹钟', '其他']
    queries = [
        "今天北京天气怎么样？",
        "播放周杰伦的歌",
        "明天早上7点叫我起床"
    ]
    
    print("\n意图识别示例:")
    for query in queries:
        print(f"查询: {query}")
        # result = recognizer.recognize(query)
        # print(f"意图: {result['intent']} (置信度: {result['confidence']:.2%})")
        print("(需要加载模型)")
    
    print("\n演示完成!")


if __name__ == "__main__":
    demo_classifier()
```

---

## 第六十六部分：代码质量与最佳实践

### 66.1 代码风格规范

```python
"""
MiniMind 代码风格规范
=====================

遵循良好的代码风格，提高代码可读性和可维护性。
"""

# ==================== 命名规范 ====================

"""
命名规范：

1. 变量名：小写+下划线
   - 正确：hidden_size, learning_rate
   - 错误：hiddenSize, LearningRate

2. 函数名：小写+下划线
   - 正确：compute_attention, forward_pass
   - 错误：computeAttention, ForwardPass

3. 类名：驼峰命名
   - 正确：TransformerBlock, AttentionLayer
   - 错误：transformer_block, attentionLayer

4. 常量：全大写+下划线
   - 正确：MAX_SEQ_LEN, DEFAULT_LR
   - 错误：maxSeqLen, default_lr

5. 私有方法：前缀下划线
   - 正确：_init_weights, _compute_loss
   - 错误：initWeights, computeLoss
"""

# 示例
MAX_SEQUENCE_LENGTH = 512
DEFAULT_LEARNING_RATE = 1e-4

class TransformerBlock(nn.Module):
    """Transformer块"""
    
    def __init__(self, hidden_size: int, num_heads: int):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_heads = num_heads
        
        self._init_layers()
    
    def _init_layers(self):
        """初始化层"""
        self.attention = MultiHeadAttention(
            self.hidden_size, 
            self.num_heads
        )
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """前向传播"""
        return self.attention(x)


# ==================== 文档字符串规范 ====================

def compute_attention(
    query: torch.Tensor,
    key: torch.Tensor,
    value: torch.Tensor,
    mask: Optional[torch.Tensor] = None
) -> Tuple[torch.Tensor, torch.Tensor]:
    """
    计算缩放点积注意力
    
    实现Transformer论文中的注意力机制：
    Attention(Q, K, V) = softmax(QK^T / sqrt(d_k)) * V
    
    参数:
        query: 查询张量，形状为(batch, heads, seq_len, head_dim)
        key: 键张量，形状与query相同
        value: 值张量，形状与query相同
        mask: 可选的注意力掩码，True位置将被遮蔽
    
    返回:
        output: 注意力输出，形状与query相同
        weights: 注意力权重，形状为(batch, heads, seq_len, seq_len)
    
    示例:
        >>> q = torch.randn(2, 8, 10, 64)
        >>> k = torch.randn(2, 8, 10, 64)
        >>> v = torch.randn(2, 8, 10, 64)
        >>> out, weights = compute_attention(q, k, v)
        >>> print(out.shape)
        torch.Size([2, 8, 10, 64])
    
    注意:
        - 当序列很长时，注意力计算的复杂度为O(n^2)
        - 使用mask可以实现因果注意力
    """
    d_k = query.size(-1)
    
    scores = torch.matmul(query, key.transpose(-2, -1)) / math.sqrt(d_k)
    
    if mask is not None:
        scores = scores.masked_fill(mask, float('-inf'))
    
    weights = F.softmax(scores, dim=-1)
    output = torch.matmul(weights, value)
    
    return output, weights


# ==================== 类型注解规范 ====================

from typing import List, Dict, Tuple, Optional, Union, Callable

class ModelConfig:
    """模型配置类"""
    
    def __init__(
        self,
        vocab_size: int,
        hidden_size: int,
        num_layers: int,
        num_heads: int,
        dropout: float = 0.1,
        max_position: int = 512
    ):
        """
        初始化配置
        
        参数:
            vocab_size: 词表大小
            hidden_size: 隐藏层维度
            num_layers: 层数
            num_heads: 注意力头数
            dropout: Dropout概率
            max_position: 最大位置
        """
        self.vocab_size = vocab_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.num_heads = num_heads
        self.dropout = dropout
        self.max_position = max_position


def create_model(
    config: ModelConfig,
    device: Optional[str] = None
) -> nn.Module:
    """
    创建模型
    
    参数:
        config: 模型配置
        device: 设备类型
    
    返回:
        初始化后的模型
    """
    model = Transformer(config)
    
    if device:
        model = model.to(device)
    
    return model


# ==================== 错误处理规范 ====================

def safe_forward(
    model: nn.Module,
    input_ids: torch.Tensor,
    max_retries: int = 3
) -> torch.Tensor:
    """
    安全的前向传播
    
    参数:
        model: 模型
        input_ids: 输入ID
        max_retries: 最大重试次数
    
    返回:
        模型输出
    
    异常:
        ValueError: 输入无效时抛出
        RuntimeError: 计算错误时抛出
    """
    # 输入验证
    if input_ids.dim() != 2:
        raise ValueError(
            f"input_ids应该是2维张量，但得到的是{input_ids.dim()}维"
        )
    
    if input_ids.max() >= model.config.vocab_size:
        raise ValueError(
            f"input_ids包含无效token ID: 最大ID {input_ids.max()}，"
            f"词表大小 {model.config.vocab_size}"
        )
    
    # 尝试计算
    for attempt in range(max_retries):
        try:
            output = model(input_ids)
            
            # 检查输出
            if torch.isnan(output).any():
                raise RuntimeError("输出包含NaN")
            
            return output
            
        except RuntimeError as e:
            if attempt == max_retries - 1:
                raise
            print(f"尝试 {attempt + 1} 失败: {e}，正在重试...")
    
    raise RuntimeError("所有尝试都失败")


# ==================== 日志规范 ====================

import logging

def setup_logger(
    name: str,
    log_file: Optional[str] = None,
    level: int = logging.INFO
) -> logging.Logger:
    """
    设置日志记录器
    
    参数:
        name: 日志记录器名称
        log_file: 日志文件路径
        level: 日志级别
    
    返回:
        配置好的日志记录器
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    
    # 格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    
    # 文件处理器
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


# 使用示例
logger = setup_logger('minimind', 'training.log')

def train_step(model, batch, optimizer):
    """训练步骤"""
    logger.debug(f"开始处理批次，大小: {len(batch)}")
    
    try:
        loss = model(batch)
        logger.info(f"损失值: {loss.item():.4f}")
        return loss
    except Exception as e:
        logger.error(f"训练步骤失败: {e}")
        raise
```

### 66.2 单元测试规范

```python
"""
MiniMind 单元测试规范
=====================

编写测试确保代码质量。
"""

import unittest
import torch
import torch.nn as nn


class TestRMSNorm(unittest.TestCase):
    """RMSNorm测试"""
    
    def setUp(self):
        """测试前准备"""
        self.dim = 64
        self.norm = RMSNorm(self.dim)
    
    def test_output_shape(self):
        """测试输出形状"""
        x = torch.randn(2, 10, self.dim)
        output = self.norm(x)
        self.assertEqual(output.shape, x.shape)
    
    def test_normalization(self):
        """测试归一化效果"""
        x = torch.randn(1, 1, self.dim)
        output = self.norm(x)
        
        # 输出RMS应该接近weight值
        rms = torch.sqrt(torch.mean(output ** 2, dim=-1))
        self.assertAlmostEqual(rms.item(), 1.0, places=2)
    
    def test_gradient(self):
        """测试梯度计算"""
        x = torch.randn(2, 10, self.dim, requires_grad=True)
        output = self.norm(x)
        loss = output.sum()
        loss.backward()
        
        self.assertIsNotNone(x.grad)


class TestAttention(unittest.TestCase):
    """注意力测试"""
    
    def setUp(self):
        """测试前准备"""
        self.dim = 64
        self.n_heads = 8
        self.attention = Attention(self.dim, self.n_heads)
    
    def test_output_shape(self):
        """测试输出形状"""
        batch, seq_len = 2, 10
        x = torch.randn(batch, seq_len, self.dim)
        output = self.attention(x)
        
        self.assertEqual(output.shape, x.shape)
    
    def test_causal_mask(self):
        """测试因果掩码"""
        seq_len = 5
        mask = torch.triu(torch.ones(seq_len, seq_len), diagonal=1).bool()
        
        x = torch.randn(1, seq_len, self.dim)
        output = self.attention(x, mask)
        
        self.assertEqual(output.shape, x.shape)


class TestTransformerBlock(unittest.TestCase):
    """Transformer块测试"""
    
    def setUp(self):
        """测试前准备"""
        self.config = ModelArgs(
            dim=64,
            n_layers=2,
            n_heads=8
        )
        self.block = TransformerBlock(self.config)
    
    def test_forward(self):
        """测试前向传播"""
        x = torch.randn(2, 10, self.config.dim)
        output = self.block(x)
        
        self.assertEqual(output.shape, x.shape)
    
    def test_residual_connection(self):
        """测试残差连接"""
        x = torch.randn(1, 1, self.config.dim)
        x.requires_grad = True
        
        output = self.block(x)
        loss = output.sum()
        loss.backward()
        
        # 梯度应该能够通过残差连接传播
        self.assertTrue(x.grad.abs().sum() > 0)


class TestGeneration(unittest.TestCase):
    """生成测试"""
    
    def test_greedy_decode(self):
        """测试贪婪解码"""
        # 创建简单模型
        vocab_size = 100
        model = SimpleModel(vocab_size, 32)
        tokenizer = SimpleTokenizer({'a': 1, 'b': 2, '<unk>': 0})
        
        # 生成
        output = greedy_decode(model, tokenizer, "a", max_new_tokens=5)
        
        # 检查输出
        self.assertIsInstance(output, str)
    
    def test_top_k_sampling(self):
        """测试Top-K采样"""
        vocab_size = 100
        model = SimpleModel(vocab_size, 32)
        tokenizer = SimpleTokenizer({'a': 1, 'b': 2, '<unk>': 0})
        
        # 多次采样应该产生不同结果
        outputs = [
            top_k_sample(model, tokenizer, "a", max_new_tokens=5, temperature=1.0)
            for _ in range(3)
        ]
        
        # 由于随机性，结果可能不同
        # 这里只检查是否成功执行
        for output in outputs:
            self.assertIsInstance(output, str)


# 运行测试
if __name__ == '__main__':
    unittest.main()
```

---

## 第六十七部分：交互式代码练习进阶

### 67.1 练习：实现完整的Multi-Head Attention

**任务说明**：根据所学知识，实现一个完整的多头注意力机制。

**编写区域**：
```python
import torch
import torch.nn as nn
import math

class MultiHeadAttention(nn.Module):
    """
    多头注意力机制
    
    请实现以下功能：
    1. 初始化Q、K、V投影层
    2. 实现注意力计算
    3. 实现因果掩码
    4. 实现输出投影
    """
    
    def __init__(self, d_model: int, n_heads: int):
        super().__init__()
        # 请在此处实现初始化
        # 提示：需要定义d_model, n_heads, head_dim
        # 需要创建W_q, W_k, W_v, W_o四个线性层
        pass
    
    def forward(self, x, mask=None):
        """
        前向传播
        
        参数：
        - x: 输入张量 (batch, seq_len, d_model)
        - mask: 注意力掩码
        
        返回：
        - 输出张量 (batch, seq_len, d_model)
        """
        # 请在此处实现前向传播
        # 步骤：
        # 1. 获取batch_size和seq_len
        # 2. 计算Q, K, V
        # 3. 重塑为多头形式
        # 4. 计算注意力分数
        # 5. 应用掩码（如果有）
        # 6. 计算softmax
        # 7. 加权求和
        # 8. 重塑并投影输出
        pass


# 测试代码
def test_attention():
    d_model = 64
    n_heads = 8
    batch_size = 2
    seq_len = 10
    
    mha = MultiHeadAttention(d_model, n_heads)
    x = torch.randn(batch_size, seq_len, d_model)
    
    output = mha(x)
    assert output.shape == x.shape, f"形状错误: {output.shape} != {x.shape}"
    print("测试通过!")


if __name__ == "__main__":
    test_attention()
```

**参考实现**：
```python
import torch
import torch.nn as nn
import math

class MultiHeadAttention(nn.Module):
    def __init__(self, d_model: int, n_heads: int):
        super().__init__()
        assert d_model % n_heads == 0, "d_model必须能被n_heads整除"
        
        self.d_model = d_model
        self.n_heads = n_heads
        self.head_dim = d_model // n_heads
        
        self.W_q = nn.Linear(d_model, d_model, bias=False)
        self.W_k = nn.Linear(d_model, d_model, bias=False)
        self.W_v = nn.Linear(d_model, d_model, bias=False)
        self.W_o = nn.Linear(d_model, d_model, bias=False)
    
    def forward(self, x, mask=None):
        batch_size, seq_len, _ = x.shape
        
        Q = self.W_q(x)
        K = self.W_k(x)
        V = self.W_v(x)
        
        Q = Q.view(batch_size, seq_len, self.n_heads, self.head_dim).transpose(1, 2)
        K = K.view(batch_size, seq_len, self.n_heads, self.head_dim).transpose(1, 2)
        V = V.view(batch_size, seq_len, self.n_heads, self.head_dim).transpose(1, 2)
        
        scores = torch.matmul(Q, K.transpose(-2, -1)) / math.sqrt(self.head_dim)
        
        if mask is not None:
            scores = scores.masked_fill(mask == 0, float('-inf'))
        
        attn_weights = torch.softmax(scores, dim=-1)
        
        attn_output = torch.matmul(attn_weights, V)
        
        attn_output = attn_output.transpose(1, 2).contiguous().view(batch_size, seq_len, self.d_model)
        
        output = self.W_o(attn_output)
        
        return output
```

---

### 67.2 练习：实现RoPE位置编码

**任务说明**：实现旋转位置编码（RoPE）。

**编写区域**：
```python
import torch
import torch.nn as nn

class RotaryPositionEmbedding(nn.Module):
    """
    旋转位置编码
    
    请实现：
    1. 计算旋转角度
    2. 应用旋转操作
    """
    
    def __init__(self, dim: int, max_seq_len: int = 512, base: int = 10000):
        super().__init__()
        # 请在此处实现初始化
        # 提示：需要预计算频率和位置编码
        pass
    
    def forward(self, x):
        """
        应用旋转位置编码
        
        参数：
        - x: 输入张量 (batch, seq_len, n_heads, head_dim)
        
        返回：
        - 旋转后的张量
        """
        # 请在此处实现旋转操作
        # 步骤：
        # 1. 获取序列长度
        # 2. 分离实部和虚部（或使用复数）
        # 3. 应用旋转
        pass
    
    def rotate_half(self, x):
        """旋转一半维度"""
        # 实现旋转操作
        pass


# 测试代码
def test_rope():
    dim = 64
    batch_size = 2
    seq_len = 10
    n_heads = 8
    head_dim = dim // n_heads
    
    rope = RotaryPositionEmbedding(head_dim)
    x = torch.randn(batch_size, seq_len, n_heads, head_dim)
    
    output = rope(x)
    assert output.shape == x.shape, f"形状错误: {output.shape} != {x.shape}"
    print("RoPE测试通过!")


if __name__ == "__main__":
    test_rope()
```

**参考实现**：
```python
import torch
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
        return torch.cat([-x2, x1], dim=-1)
```

---

### 67.3 练习：实现SwiGLU激活函数

**任务说明**：实现SwiGLU激活函数。

**编写区域**：
```python
import torch
import torch.nn as nn

class SwiGLU(nn.Module):
    """
    SwiGLU激活函数
    
    请实现：
    1. 门控线性单元结构
    2. Swish激活函数
    """
    
    def __init__(self, dim: int, hidden_dim: int = None, dropout: float = 0.0):
        super().__init__()
        # 请在此处实现初始化
        # 提示：需要两个线性层（门控和值）
        # hidden_dim通常为dim的4/3倍并向上取整到256的倍数
        pass
    
    def forward(self, x):
        """
        前向传播
        
        参数：
        - x: 输入张量 (batch, seq_len, dim)
        
        返回：
        - 输出张量 (batch, seq_len, dim)
        """
        # 请在此处实现SwiGLU计算
        # 公式：SwiGLU(x) = Swish(W1(x)) * W2(x)
        # 其中Swish(x) = x * sigmoid(x)
        pass


# 测试代码
def test_swiglu():
    dim = 64
    batch_size = 2
    seq_len = 10
    
    swiglu = SwiGLU(dim)
    x = torch.randn(batch_size, seq_len, dim)
    
    output = swiglu(x)
    assert output.shape == x.shape, f"形状错误: {output.shape} != {x.shape}"
    print("SwiGLU测试通过!")


if __name__ == "__main__":
    test_swiglu()
```

**参考实现**：
```python
import torch
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
        return self.dropout(self.w2(F.silu(self.w1(x)) * self.w3(x)))
```

---

### 67.4 练习：实现完整的Transformer Block

**任务说明**：组合前面学到的组件，实现完整的Transformer Block。

**编写区域**：
```python
import torch
import torch.nn as nn

class TransformerBlock(nn.Module):
    """
    Transformer块
    
    请实现：
    1. 注意力层 + RMSNorm
    2. FFN层 + RMSNorm
    3. 残差连接
    """
    
    def __init__(self, dim: int, n_heads: int, ffn_dim: int = None, dropout: float = 0.0):
        super().__init__()
        # 请在此处实现初始化
        # 需要组件：
        # - attention (MultiHeadAttention)
        # - ffn (SwiGLU)
        # - norm1, norm2 (RMSNorm)
        # - dropout
        pass
    
    def forward(self, x, mask=None):
        """
        前向传播
        
        参数：
        - x: 输入张量 (batch, seq_len, dim)
        - mask: 注意力掩码
        
        返回：
        - 输出张量 (batch, seq_len, dim)
        """
        # 请在此处实现前向传播
        # 使用Pre-Norm结构：
        # x = x + attention(norm1(x))
        # x = x + ffn(norm2(x))
        pass


# 测试代码
def test_transformer_block():
    dim = 64
    n_heads = 8
    batch_size = 2
    seq_len = 10
    
    block = TransformerBlock(dim, n_heads)
    x = torch.randn(batch_size, seq_len, dim)
    
    output = block(x)
    assert output.shape == x.shape, f"形状错误: {output.shape} != {x.shape}"
    print("TransformerBlock测试通过!")


if __name__ == "__main__":
    test_transformer_block()
```

**参考实现**：
```python
import torch
import torch.nn as nn

class RMSNorm(nn.Module):
    def __init__(self, dim: int, eps: float = 1e-6):
        super().__init__()
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(dim))
    
    def forward(self, x):
        rms = torch.sqrt(torch.mean(x ** 2, dim=-1, keepdim=True) + self.eps)
        return x / rms * self.weight

class TransformerBlock(nn.Module):
    def __init__(self, dim: int, n_heads: int, ffn_dim: int = None, dropout: float = 0.0):
        super().__init__()
        
        self.attention = MultiHeadAttention(dim, n_heads)
        self.ffn = SwiGLU(dim, ffn_dim, dropout)
        self.norm1 = RMSNorm(dim)
        self.norm2 = RMSNorm(dim)
        self.dropout = nn.Dropout(dropout)
    
    def forward(self, x, mask=None):
        x = x + self.dropout(self.attention(self.norm1(x), mask))
        x = x + self.dropout(self.ffn(self.norm2(x)))
        return x
```

---

### 67.5 练习：实现文本生成器

**任务说明**：实现完整的文本生成器，支持多种采样策略。

**编写区域**：
```python
import torch
import torch.nn as nn
import torch.nn.functional as F

class TextGenerator:
    """
    文本生成器
    
    请实现：
    1. 贪婪解码
    2. Top-K采样
    3. Top-P（核）采样
    4. 温度调节
    """
    
    def __init__(self, model, tokenizer, max_length: int = 100):
        self.model = model
        self.tokenizer = tokenizer
        self.max_length = max_length
    
    def greedy_decode(self, prompt: str) -> str:
        """
        贪婪解码
        
        每步选择概率最高的token
        """
        # 请实现贪婪解码
        pass
    
    def top_k_sample(self, prompt: str, k: int = 50, temperature: float = 1.0) -> str:
        """
        Top-K采样
        
        从概率最高的K个token中采样
        """
        # 请实现Top-K采样
        pass
    
    def top_p_sample(self, prompt: str, p: float = 0.9, temperature: float = 1.0) -> str:
        """
        Top-P（核）采样
        
        从累积概率达到P的最小token集合中采样
        """
        # 请实现Top-P采样
        pass


# 测试代码
def test_generator():
    # 使用模拟模型测试
    class MockModel(nn.Module):
        def __init__(self, vocab_size=100):
            super().__init__()
            self.vocab_size = vocab_size
            self.embed = nn.Embedding(vocab_size, 32)
            self.linear = nn.Linear(32, vocab_size)
        
        def forward(self, x):
            return self.linear(self.embed(x))
    
    class MockTokenizer:
        def encode(self, text):
            return [ord(c) % 100 for c in text]
        
        def decode(self, ids):
            return ''.join([chr(i + 32) for i in ids])
    
    model = MockModel()
    tokenizer = MockTokenizer()
    generator = TextGenerator(model, tokenizer)
    
    output = generator.greedy_decode("hello")
    print(f"贪婪解码输出: {output}")
    
    output = generator.top_k_sample("hello", k=10)
    print(f"Top-K采样输出: {output}")
    
    print("TextGenerator测试通过!")


if __name__ == "__main__":
    test_generator()
```

**参考实现**：
```python
import torch
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
        
        return self.tokenizer.decode(input_ids[0].tolist())
```

---

## 第六十八部分：调试技巧与常见错误处理

### 68.1 常见错误及解决方案

```python
"""
MiniMind 调试技巧与错误处理
===========================

深度学习开发中常见的问题和解决方案。
"""

import torch
import torch.nn as nn
import warnings


# ==================== 1. NaN/Inf 问题 ====================

def diagnose_nan_inf(tensor, name="tensor"):
    """
    诊断张量中的NaN和Inf
    
    参数：
    - tensor: 要检查的张量
    - name: 张量名称（用于日志）
    """
    has_nan = torch.isnan(tensor).any()
    has_inf = torch.isinf(tensor).any()
    
    if has_nan or has_inf:
        print(f"[警告] {name} 包含异常值:")
        print(f"  - NaN数量: {torch.isnan(tensor).sum().item()}")
        print(f"  - Inf数量: {torch.isinf(tensor).sum().item()}")
        print(f"  - 正常值范围: [{tensor[~torch.isnan(tensor) & ~torch.isinf(tensor)].min().item():.4f}, "
              f"{tensor[~torch.isnan(tensor) & ~torch.isinf(tensor)].max().item():.4f}]")
        return True
    return False


def fix_nan_inf(tensor, method='clamp'):
    """
    修复张量中的NaN和Inf
    
    参数：
    - tensor: 要修复的张量
    - method: 修复方法 ('clamp', 'replace', 'mask')
    """
    if method == 'clamp':
        tensor = torch.clamp(tensor, min=-1e6, max=1e6)
        tensor = torch.nan_to_num(tensor, nan=0.0)
    elif method == 'replace':
        tensor = torch.nan_to_num(tensor, nan=0.0, posinf=1e6, neginf=-1e6)
    elif method == 'mask':
        mask = ~torch.isnan(tensor) & ~torch.isinf(tensor)
        mean_val = tensor[mask].mean() if mask.any() else 0.0
        tensor = torch.where(mask, tensor, mean_val)
    
    return tensor


# ==================== 2. 梯度问题 ====================

def check_gradients(model):
    """
    检查模型梯度状态
    
    参数：
    - model: 要检查的模型
    """
    print("=" * 50)
    print("梯度检查报告")
    print("=" * 50)
    
    total_params = 0
    no_grad_params = 0
    nan_grad_params = 0
    zero_grad_params = 0
    
    for name, param in model.named_parameters():
        total_params += 1
        
        if param.grad is None:
            no_grad_params += 1
            print(f"[无梯度] {name}")
        elif torch.isnan(param.grad).any():
            nan_grad_params += 1
            print(f"[NaN梯度] {name}")
        elif torch.all(param.grad == 0):
            zero_grad_params += 1
            print(f"[零梯度] {name}")
        else:
            grad_norm = param.grad.norm().item()
            if grad_norm > 100:
                print(f"[梯度爆炸] {name}: norm={grad_norm:.2f}")
            elif grad_norm < 1e-7:
                print(f"[梯度消失] {name}: norm={grad_norm:.2e}")
    
    print("-" * 50)
    print(f"总参数数: {total_params}")
    print(f"无梯度参数: {no_grad_params}")
    print(f"NaN梯度参数: {nan_grad_params}")
    print(f"零梯度参数: {zero_grad_params}")


def gradient_clipping(model, max_norm: float = 1.0):
    """
    梯度裁剪
    
    参数：
    - model: 模型
    - max_norm: 最大梯度范数
    """
    total_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm)
    return total_norm


# ==================== 3. 维度错误 ====================

def debug_shape(tensor, name="tensor"):
    """打印张量形状信息"""
    print(f"{name}:")
    print(f"  形状: {tensor.shape}")
    print(f"  数据类型: {tensor.dtype}")
    print(f"  设备: {tensor.device}")
    print(f"  是否需要梯度: {tensor.requires_grad}")


def debug_model_shapes(model, input_shape):
    """
    调试模型各层形状
    
    参数：
    - model: 模型
    - input_shape: 输入形状 (不含batch维度)
    """
    print("=" * 50)
    print("模型形状调试")
    print("=" * 50)
    
    x = torch.randn(1, *input_shape)
    print(f"输入形状: {x.shape}")
    
    def hook_fn(module, input, output):
        print(f"{module.__class__.__name__}: {input[0].shape} -> {output.shape}")
    
    hooks = []
    for name, module in model.named_modules():
        if len(list(module.children())) == 0:
            hook = module.register_forward_hook(hook_fn)
            hooks.append(hook)
    
    try:
        with torch.no_grad():
            _ = model(x)
    except Exception as e:
        print(f"错误: {e}")
    
    for hook in hooks:
        hook.remove()


# ==================== 4. 内存问题 ====================

def get_memory_usage():
    """获取GPU内存使用情况"""
    if torch.cuda.is_available():
        allocated = torch.cuda.memory_allocated() / 1024**2
        reserved = torch.cuda.memory_reserved() / 1024**2
        max_allocated = torch.cuda.max_memory_allocated() / 1024**2
        
        print("GPU内存使用:")
        print(f"  已分配: {allocated:.2f} MB")
        print(f"  已预留: {reserved:.2f} MB")
        print(f"  峰值: {max_allocated:.2f} MB")
        
        return {
            'allocated': allocated,
            'reserved': reserved,
            'max_allocated': max_allocated
        }
    else:
        print("CUDA不可用")
        return None


def clear_memory():
    """清理GPU内存"""
    import gc
    gc.collect()
    
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()
        print("GPU内存已清理")


# ==================== 5. 训练调试 ====================

class TrainingDebugger:
    """训练调试器"""
    
    def __init__(self, model, log_interval: int = 10):
        self.model = model
        self.log_interval = log_interval
        self.step = 0
        self.losses = []
    
    def step_end(self, loss):
        """
        记录训练步骤
        
        参数：
        - loss: 当前损失值
        """
        self.step += 1
        self.losses.append(loss)
        
        if self.step % self.log_interval == 0:
            self._log_status(loss)
    
    def _log_status(self, loss):
        """记录状态"""
        print(f"\n步骤 {self.step}:")
        print(f"  损失: {loss:.4f}")
        
        if len(self.losses) > 1:
            avg_loss = sum(self.losses[-self.log_interval:]) / self.log_interval
            print(f"  平均损失(最近{self.log_interval}步): {avg_loss:.4f}")
            
            if loss > self.losses[-2] * 2:
                print("  [警告] 损失突然增大!")
        
        if torch.isnan(torch.tensor(loss)):
            print("  [错误] 损失为NaN!")
        
        if torch.isinf(torch.tensor(loss)):
            print("  [错误] 损失为Inf!")
    
    def check_model_weights(self):
        """检查模型权重"""
        print("\n权重统计:")
        for name, param in self.model.named_parameters():
            if param.requires_grad:
                print(f"  {name}:")
                print(f"    均值: {param.data.mean().item():.6f}")
                print(f"    标准差: {param.data.std().item():.6f}")
                print(f"    最小值: {param.data.min().item():.6f}")
                print(f"    最大值: {param.data.max().item():.6f}")


# ==================== 6. 断点调试技巧 ====================

def set_debug_mode(enabled: bool = True):
    """
    设置调试模式
    
    参数：
    - enabled: 是否启用
    """
    if enabled:
        torch.autograd.set_detect_anomaly(True)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
        torch.manual_seed(42)
        print("调试模式已启用")
    else:
        torch.autograd.set_detect_anomaly(False)
        torch.backends.cudnn.deterministic = False
        torch.backends.cudnn.benchmark = True
        print("调试模式已禁用")


def debug_forward_pass(model, input_ids):
    """
    调试前向传播
    
    参数：
    - model: 模型
    - input_ids: 输入ID
    """
    print("=" * 50)
    print("前向传播调试")
    print("=" * 50)
    
    model.eval()
    
    with torch.no_grad():
        try:
            output = model(input_ids)
            print(f"前向传播成功!")
            print(f"输出形状: {output.shape}")
            
            if diagnose_nan_inf(output, "输出"):
                print("输出包含异常值，需要检查模型")
            
            return output
            
        except Exception as e:
            print(f"前向传播失败: {e}")
            return None


# ==================== 使用示例 ====================

def demo_debug():
    """演示调试功能"""
    print("=" * 60)
    print("调试工具演示")
    print("=" * 60)
    
    # 创建测试模型
    model = nn.Sequential(
        nn.Linear(64, 128),
        nn.ReLU(),
        nn.Linear(128, 64)
    )
    
    # 测试形状调试
    print("\n1. 形状调试:")
    debug_model_shapes(model, (64,))
    
    # 测试内存使用
    print("\n2. 内存使用:")
    get_memory_usage()
    
    # 测试梯度检查
    print("\n3. 梯度检查:")
    x = torch.randn(2, 64)
    y = model(x).sum()
    y.backward()
    check_gradients(model)
    
    print("\n演示完成!")


if __name__ == "__main__":
    demo_debug()
```

---

### 68.2 性能分析工具

```python
"""
性能分析工具
============

分析和优化模型性能。
"""

import torch
import torch.nn as nn
import time
from functools import wraps
from contextlib import contextmanager


# ==================== 时间分析 ====================

def timing_decorator(func):
    """函数计时装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        print(f"{func.__name__} 耗时: {(end - start) * 1000:.2f} ms")
        return result
    return wrapper


@contextmanager
def timer(name="操作"):
    """计时上下文管理器"""
    if torch.cuda.is_available():
        torch.cuda.synchronize()
    
    start = time.perf_counter()
    yield
    
    if torch.cuda.is_available():
        torch.cuda.synchronize()
    
    end = time.perf_counter()
    print(f"{name} 耗时: {(end - start) * 1000:.2f} ms")


class Profiler:
    """性能分析器"""
    
    def __init__(self):
        self.records = {}
    
    def start(self, name: str):
        """开始计时"""
        if name not in self.records:
            self.records[name] = {'times': [], 'total': 0}
        
        if torch.cuda.is_available():
            torch.cuda.synchronize()
        
        self.records[name]['start'] = time.perf_counter()
    
    def end(self, name: str):
        """结束计时"""
        if torch.cuda.is_available():
            torch.cuda.synchronize()
        
        elapsed = time.perf_counter() - self.records[name]['start']
        self.records[name]['times'].append(elapsed)
        self.records[name]['total'] += elapsed
    
    def report(self):
        """生成报告"""
        print("=" * 60)
        print("性能分析报告")
        print("=" * 60)
        
        for name, data in self.records.items():
            times = data['times']
            if times:
                avg = sum(times) / len(times)
                print(f"{name}:")
                print(f"  调用次数: {len(times)}")
                print(f"  平均时间: {avg * 1000:.2f} ms")
                print(f"  总时间: {data['total'] * 1000:.2f} ms")
                print(f"  最小时间: {min(times) * 1000:.2f} ms")
                print(f"  最大时间: {max(times) * 1000:.2f} ms")


# ==================== 模型分析 ====================

def count_parameters(model):
    """统计模型参数"""
    total = sum(p.numel() for p in model.parameters())
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    
    print(f"总参数量: {total:,}")
    print(f"可训练参数: {trainable:,}")
    print(f"不可训练参数: {total - trainable:,}")
    
    return {'total': total, 'trainable': trainable}


def analyze_model_layers(model):
    """分析模型各层"""
    print("=" * 60)
    print("模型层分析")
    print("=" * 60)
    
    for name, module in model.named_modules():
        if len(list(module.children())) == 0:
            params = sum(p.numel() for p in module.parameters())
            print(f"{name}: {module.__class__.__name__} ({params:,} 参数)")


def benchmark_inference(model, input_shape, num_runs=100, warmup=10):
    """
    推理性能基准测试
    
    参数：
    - model: 模型
    - input_shape: 输入形状
    - num_runs: 测试次数
    - warmup: 预热次数
    """
    model.eval()
    device = next(model.parameters()).device
    x = torch.randn(*input_shape, device=device)
    
    # 预热
    with torch.no_grad():
        for _ in range(warmup):
            _ = model(x)
    
    if torch.cuda.is_available():
        torch.cuda.synchronize()
    
    # 测试
    times = []
    with torch.no_grad():
        for _ in range(num_runs):
            if torch.cuda.is_available():
                torch.cuda.synchronize()
            
            start = time.perf_counter()
            _ = model(x)
            
            if torch.cuda.is_available():
                torch.cuda.synchronize()
            
            end = time.perf_counter()
            times.append(end - start)
    
    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)
    
    print("=" * 60)
    print("推理性能基准")
    print("=" * 60)
    print(f"输入形状: {input_shape}")
    print(f"测试次数: {num_runs}")
    print(f"平均时间: {avg_time * 1000:.2f} ms")
    print(f"最小时间: {min_time * 1000:.2f} ms")
    print(f"最大时间: {max_time * 1000:.2f} ms")
    print(f"吞吐量: {input_shape[0] / avg_time:.2f} samples/s")
    
    return {
        'avg_time': avg_time,
        'min_time': min_time,
        'max_time': max_time,
        'throughput': input_shape[0] / avg_time
    }


# ==================== 内存分析 ====================

def estimate_memory_usage(model, input_shape, batch_size=1):
    """
    估算内存使用
    
    参数：
    - model: 模型
    - input_shape: 输入形状（不含batch）
    - batch_size: 批次大小
    """
    # 参数内存
    param_memory = sum(p.numel() * p.element_size() for p in model.parameters())
    
    # 梯度内存
    grad_memory = sum(p.numel() * p.element_size() for p in model.parameters() if p.requires_grad)
    
    # 输入内存
    input_memory = batch_size * torch.tensor(input_shape).prod().item() * 4  # float32
    
    # 估算激活内存（粗略估计）
    activation_memory = param_memory * 2  # 粗略估计
    
    total_memory = param_memory + grad_memory + input_memory + activation_memory
    
    print("=" * 60)
    print("内存估算")
    print("=" * 60)
    print(f"参数内存: {param_memory / 1024**2:.2f} MB")
    print(f"梯度内存: {grad_memory / 1024**2:.2f} MB")
    print(f"输入内存: {input_memory / 1024**2:.2f} MB")
    print(f"激活内存(估计): {activation_memory / 1024**2:.2f} MB")
    print(f"总内存(估计): {total_memory / 1024**2:.2f} MB")
    
    return {
        'param_memory': param_memory,
        'grad_memory': grad_memory,
        'input_memory': input_memory,
        'activation_memory': activation_memory,
        'total_memory': total_memory
    }


# ==================== 使用示例 ====================

def demo_profiling():
    """演示性能分析"""
    print("=" * 60)
    print("性能分析演示")
    print("=" * 60)
    
    # 创建测试模型
    model = nn.Sequential(
        nn.Linear(512, 1024),
        nn.ReLU(),
        nn.Linear(1024, 512),
        nn.ReLU(),
        nn.Linear(512, 256)
    )
    
    # 统计参数
    print("\n1. 参数统计:")
    count_parameters(model)
    
    # 分析层
    print("\n2. 层分析:")
    analyze_model_layers(model)
    
    # 推理基准测试
    print("\n3. 推理基准测试:")
    benchmark_inference(model, (1, 512), num_runs=50)
    
    # 内存估算
    print("\n4. 内存估算:")
    estimate_memory_usage(model, (512,), batch_size=4)
    
    print("\n演示完成!")


if __name__ == "__main__":
    demo_profiling()
```

---

## 第六十九部分：性能优化实战案例

### 69.1 训练加速技巧

```python
"""
训练加速技巧
============

多种方法加速模型训练。
"""

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
import time


# ==================== 1. 混合精度训练 ====================

class MixedPrecisionTrainer:
    """混合精度训练器"""
    
    def __init__(self, model, optimizer, use_amp: bool = True):
        self.model = model
        self.optimizer = optimizer
        self.use_amp = use_amp and torch.cuda.is_available()
        
        if self.use_amp:
            self.scaler = torch.cuda.amp.GradScaler()
            print("混合精度训练已启用 (FP16)")
        else:
            self.scaler = None
            print("使用FP32训练")
    
    def train_step(self, batch):
        """训练步骤"""
        self.optimizer.zero_grad()
        
        if self.use_amp:
            with torch.cuda.amp.autocast():
                loss = self.model(batch)
            
            self.scaler.scale(loss).backward()
            self.scaler.step(self.optimizer)
            self.scaler.update()
        else:
            loss = self.model(batch)
            loss.backward()
            self.optimizer.step()
        
        return loss.item()


# ==================== 2. 梯度累积 ====================

class GradientAccumulator:
    """梯度累积器"""
    
    def __init__(self, model, optimizer, accumulation_steps: int = 4):
        self.model = model
        self.optimizer = optimizer
        self.accumulation_steps = accumulation_steps
        self.step_count = 0
    
    def train_step(self, loss):
        """训练步骤"""
        normalized_loss = loss / self.accumulation_steps
        normalized_loss.backward()
        
        self.step_count += 1
        
        if self.step_count % self.accumulation_steps == 0:
            self.optimizer.step()
            self.optimizer.zero_grad()
            return True
        
        return False


# ==================== 3. 数据加载优化 ====================

def create_optimized_dataloader(dataset, batch_size: int, num_workers: int = 4):
    """创建优化的数据加载器"""
    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=torch.cuda.is_available(),
        prefetch_factor=2 if num_workers > 0 else None,
        persistent_workers=num_workers > 0,
        drop_last=True
    )


class FastDataset(Dataset):
    """快速数据集示例"""
    
    def __init__(self, size: int = 10000, seq_len: int = 128, vocab_size: int = 1000):
        self.data = torch.randint(0, vocab_size, (size, seq_len))
    
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        return self.data[idx]


# ==================== 4. 编译优化 ====================

def compile_model(model, mode: str = 'default'):
    """
    编译模型以获得更好的性能
    
    参数：
    - model: 模型
    - mode: 编译模式 ('default', 'max-autotune', 'reduce-overhead')
    """
    if hasattr(torch, 'compile'):
        compiled_model = torch.compile(model, mode=mode)
        print(f"模型已编译 (模式: {mode})")
        return compiled_model
    else:
        print("torch.compile 不可用，返回原始模型")
        return model


# ==================== 5. 批处理优化 ====================

def find_optimal_batch_size(model, input_shape, max_batch_size: int = 256):
    """
    寻找最优批次大小
    
    参数：
    - model: 模型
    - input_shape: 输入形状（不含batch）
    - max_batch_size: 最大测试批次
    """
    if not torch.cuda.is_available():
        print("需要CUDA来测试批次大小")
        return 1
    
    model.eval()
    device = next(model.parameters()).device
    
    optimal_batch = 1
    for batch_size in [2**i for i in range(1, 10) if 2**i <= max_batch_size]:
        try:
            x = torch.randn(batch_size, *input_shape, device=device)
            torch.cuda.empty_cache()
            
            with torch.no_grad():
                _ = model(x)
            
            optimal_batch = batch_size
            del x
            torch.cuda.empty_cache()
            
        except RuntimeError as e:
            if "out of memory" in str(e):
                break
            raise
    
    print(f"最优批次大小: {optimal_batch}")
    return optimal_batch


# ==================== 6. 完整训练优化示例 ====================

class OptimizedTrainer:
    """优化的训练器"""
    
    def __init__(
        self,
        model,
        train_dataset,
        batch_size: int = 32,
        learning_rate: float = 1e-4,
        accumulation_steps: int = 4,
        use_amp: bool = True,
        use_compile: bool = True,
        num_workers: int = 4
    ):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        self.model = model.to(self.device)
        
        if use_compile and hasattr(torch, 'compile'):
            self.model = torch.compile(self.model)
        
        self.optimizer = torch.optim.AdamW(self.model.parameters(), lr=learning_rate)
        
        self.use_amp = use_amp and torch.cuda.is_available()
        if self.use_amp:
            self.scaler = torch.cuda.amp.GradScaler()
        
        self.accumulation_steps = accumulation_steps
        self.step_count = 0
        
        self.dataloader = create_optimized_dataloader(
            train_dataset, batch_size, num_workers
        )
    
    def train_epoch(self):
        """训练一个epoch"""
        self.model.train()
        total_loss = 0
        
        for batch_idx, batch in enumerate(self.dataloader):
            batch = batch.to(self.device)
            
            self.optimizer.zero_grad()
            
            if self.use_amp:
                with torch.cuda.amp.autocast():
                    loss = self._compute_loss(batch)
                
                self.scaler.scale(loss).backward()
                
                self.step_count += 1
                if self.step_count % self.accumulation_steps == 0:
                    self.scaler.step(self.optimizer)
                    self.scaler.update()
            else:
                loss = self._compute_loss(batch)
                loss.backward()
                
                self.step_count += 1
                if self.step_count % self.accumulation_steps == 0:
                    self.optimizer.step()
            
            total_loss += loss.item()
        
        return total_loss / len(self.dataloader)
    
    def _compute_loss(self, batch):
        """计算损失"""
        output = self.model(batch)
        return output.mean()


# ==================== 性能对比 ====================

def compare_training_speeds():
    """比较不同优化方法的训练速度"""
    print("=" * 60)
    print("训练优化对比")
    print("=" * 60)
    
    # 创建测试模型
    model = nn.Sequential(
        nn.Linear(512, 1024),
        nn.ReLU(),
        nn.Linear(1024, 1024),
        nn.ReLU(),
        nn.Linear(1024, 512)
    )
    
    dataset = FastDataset(size=1000, seq_len=512)
    
    configs = [
        {'name': 'FP32', 'use_amp': False, 'use_compile': False},
        {'name': 'FP16', 'use_amp': True, 'use_compile': False},
        {'name': 'FP16+Compile', 'use_amp': True, 'use_compile': True},
    ]
    
    results = []
    
    for config in configs:
        print(f"\n测试配置: {config['name']}")
        
        trainer = OptimizedTrainer(
            model,
            dataset,
            batch_size=32,
            use_amp=config['use_amp'],
            use_compile=config['use_compile']
        )
        
        start = time.time()
        loss = trainer.train_epoch()
        elapsed = time.time() - start
        
        results.append({
            'name': config['name'],
            'time': elapsed,
            'loss': loss
        })
        
        print(f"  时间: {elapsed:.2f}s, 损失: {loss:.4f}")
    
    print("\n" + "=" * 60)
    print("结果汇总")
    print("=" * 60)
    
    baseline = results[0]['time']
    for r in results:
        speedup = baseline / r['time']
        print(f"{r['name']}: {r['time']:.2f}s (加速: {speedup:.2f}x)")


if __name__ == "__main__":
    compare_training_speeds()
```

---

### 69.2 推理加速技巧

```python
"""
推理加速技巧
============

优化模型推理性能。
"""

import torch
import torch.nn as nn
import time


# ==================== 1. 模型量化 ====================

def quantize_model_dynamic(model):
    """
    动态量化模型
    
    将线性层量化为INT8
    """
    quantized_model = torch.quantization.quantize_dynamic(
        model,
        {nn.Linear},
        dtype=torch.qint8
    )
    print("模型已动态量化 (INT8)")
    return quantized_model


def compare_quantization():
    """比较量化前后的性能"""
    print("=" * 60)
    print("量化性能对比")
    print("=" * 60)
    
    # 创建测试模型
    model = nn.Sequential(
        nn.Linear(512, 1024),
        nn.ReLU(),
        nn.Linear(1024, 1024),
        nn.ReLU(),
        nn.Linear(1024, 512)
    )
    model.eval()
    
    # 测试原始模型
    x = torch.randn(1, 512)
    
    start = time.time()
    for _ in range(100):
        with torch.no_grad():
            _ = model(x)
    original_time = time.time() - start
    
    # 量化模型
    quantized_model = quantize_model_dynamic(model)
    
    start = time.time()
    for _ in range(100):
        with torch.no_grad():
            _ = quantized_model(x)
    quantized_time = time.time() - start
    
    # 计算模型大小
    original_size = sum(p.numel() * p.element_size() for p in model.parameters())
    quantized_size = sum(p.numel() * p.element_size() for p in quantized_model.parameters())
    
    print(f"\n原始模型:")
    print(f"  大小: {original_size / 1024:.2f} KB")
    print(f"  推理时间: {original_time * 1000:.2f} ms")
    
    print(f"\n量化模型:")
    print(f"  大小: {quantized_size / 1024:.2f} KB")
    print(f"  推理时间: {quantized_time * 1000:.2f} ms")
    
    print(f"\n加速比: {original_time / quantized_time:.2f}x")
    print(f"压缩比: {original_size / quantized_size:.2f}x")


# ==================== 2. ONNX导出 ====================

def export_to_onnx(model, input_shape, output_path: str = "model.onnx"):
    """
    导出模型为ONNX格式
    
    参数：
    - model: 模型
    - input_shape: 输入形状
    - output_path: 输出路径
    """
    model.eval()
    dummy_input = torch.randn(*input_shape)
    
    torch.onnx.export(
        model,
        dummy_input,
        output_path,
        export_params=True,
        opset_version=14,
        do_constant_folding=True,
        input_names=['input'],
        output_names=['output'],
        dynamic_axes={
            'input': {0: 'batch_size'},
            'output': {0: 'batch_size'}
        }
    )
    
    print(f"模型已导出到: {output_path}")


# ==================== 3. 批处理推理 ====================

class BatchInference:
    """批处理推理器"""
    
    def __init__(self, model, batch_size: int = 32, device: str = 'cuda'):
        self.model = model.to(device)
        self.model.eval()
        self.batch_size = batch_size
        self.device = device
    
    def predict(self, inputs):
        """
        批量预测
        
        参数：
        - inputs: 输入列表
        
        返回：
        - 输出列表
        """
        results = []
        
        for i in range(0, len(inputs), self.batch_size):
            batch = inputs[i:i + self.batch_size]
            batch_tensor = torch.stack(batch).to(self.device)
            
            with torch.no_grad():
                outputs = self.model(batch_tensor)
            
            results.extend(outputs.cpu())
        
        return results


# ==================== 4. KV Cache优化 ====================

class KVCache:
    """KV缓存管理器"""
    
    def __init__(self, n_layers: int, n_heads: int, head_dim: int, max_seq_len: int = 512):
        self.n_layers = n_layers
        self.n_heads = n_heads
        self.head_dim = head_dim
        self.max_seq_len = max_seq_len
        
        self.cache = None
    
    def init_cache(self, batch_size: int, device: str = 'cuda'):
        """初始化缓存"""
        self.cache = {
            'k': [torch.zeros(batch_size, self.n_heads, 0, self.head_dim, device=device)
                  for _ in range(self.n_layers)],
            'v': [torch.zeros(batch_size, self.n_heads, 0, self.head_dim, device=device)
                  for _ in range(self.n_layers)]
        }
    
    def update(self, layer_idx: int, k: torch.Tensor, v: torch.Tensor):
        """更新缓存"""
        if self.cache is None:
            return k, v
        
        self.cache['k'][layer_idx] = torch.cat([self.cache['k'][layer_idx], k], dim=2)
        self.cache['v'][layer_idx] = torch.cat([self.cache['v'][layer_idx], v], dim=2)
        
        return self.cache['k'][layer_idx], self.cache['v'][layer_idx]
    
    def get_seq_len(self):
        """获取当前序列长度"""
        if self.cache is None:
            return 0
        return self.cache['k'][0].shape[2]


class CachedInference:
    """带KV缓存的推理器"""
    
    def __init__(self, model, tokenizer, max_new_tokens: int = 100):
        self.model = model
        self.tokenizer = tokenizer
        self.max_new_tokens = max_new_tokens
    
    def generate(self, prompt: str):
        """生成文本"""
        tokens = self.tokenizer.encode(prompt)
        input_ids = torch.tensor([tokens])
        
        # 初始化KV缓存
        config = self.model.config
        kv_cache = KVCache(
            n_layers=config.n_layers,
            n_heads=config.n_heads,
            head_dim=config.dim // config.n_heads
        )
        kv_cache.init_cache(1)
        
        generated = list(tokens)
        
        self.model.eval()
        with torch.no_grad():
            # 首次前向传播（处理prompt）
            logits = self.model(input_ids, kv_cache)
            
            # 生成新token
            for _ in range(self.max_new_tokens):
                next_token = torch.argmax(logits[:, -1, :], dim=-1, keepdim=True)
                generated.append(next_token.item())
                
                # 只处理新token
                logits = self.model(next_token, kv_cache)
        
        return self.tokenizer.decode(generated)


# ==================== 5. 推理优化对比 ====================

def benchmark_inference_optimizations():
    """推理优化基准测试"""
    print("=" * 60)
    print("推理优化基准测试")
    print("=" * 60)
    
    # 创建测试模型
    model = nn.Sequential(
        nn.Linear(512, 1024),
        nn.ReLU(),
        nn.Linear(1024, 1024),
        nn.ReLU(),
        nn.Linear(1024, 512)
    )
    model.eval()
    
    x = torch.randn(1, 512)
    
    # 原始推理
    print("\n1. 原始推理:")
    start = time.time()
    for _ in range(100):
        with torch.no_grad():
            _ = model(x)
    print(f"   时间: {(time.time() - start) * 1000:.2f} ms")
    
    # torch.no_grad + eval
    print("\n2. no_grad + eval:")
    model.eval()
    start = time.time()
    for _ in range(100):
        with torch.no_grad():
            _ = model(x)
    print(f"   时间: {(time.time() - start) * 1000:.2f} ms")
    
    # 批处理
    print("\n3. 批处理推理:")
    batch_x = torch.randn(32, 512)
    start = time.time()
    for _ in range(100 // 32):
        with torch.no_grad():
            _ = model(batch_x)
    print(f"   时间: {(time.time() - start) * 1000:.2f} ms (32样本)")
    
    # 量化
    print("\n4. 动态量化:")
    quantized_model = quantize_model_dynamic(model)
    start = time.time()
    for _ in range(100):
        with torch.no_grad():
            _ = quantized_model(x)
    print(f"   时间: {(time.time() - start) * 1000:.2f} ms")
    
    print("\n基准测试完成!")


if __name__ == "__main__":
    benchmark_inference_optimizations()
```

---

### 69.3 内存优化技巧

```python
"""
内存优化技巧
============

减少模型内存占用。
"""

import torch
import torch.nn as nn
import gc


# ==================== 1. 梯度检查点 ====================

class CheckpointedSequential(nn.Sequential):
    """带梯度检查点的Sequential"""
    
    def __init__(self, *args):
        super().__init__(*args)
    
    def forward(self, x):
        from torch.utils.checkpoint import checkpoint
        
        for module in self:
            if len(list(module.children())) == 0:
                x = checkpoint(module, x, use_reentrant=False)
            else:
                x = module(x)
        
        return x


def enable_gradient_checkpointing(model):
    """启用梯度检查点"""
    from torch.utils.checkpoint import checkpoint
    
    def make_checkpointed(module):
        original_forward = module.forward
        
        def checkpointed_forward(*args, **kwargs):
            return checkpoint(original_forward, *args, use_reentrant=False, **kwargs)
        
        module.forward = checkpointed_forward
        return module
    
    for module in model.modules():
        if isinstance(module, nn.TransformerEncoderLayer):
            make_checkpointed(module)
    
    print("梯度检查点已启用")
    return model


# ==================== 2. 参数共享 ====================

class SharedEmbedding(nn.Module):
    """共享嵌入层"""
    
    def __init__(self, vocab_size: int, dim: int):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, dim)
        self.output_proj = nn.Linear(dim, vocab_size, bias=False)
        
        # 共享权重
        self.output_proj.weight = self.embedding.weight
    
    def forward(self, x):
        embedded = self.embedding(x)
        output = self.output_proj(embedded)
        return output


# ==================== 3. 低精度存储 ====================

def convert_to_bf16(model):
    """转换为BF16"""
    model = model.to(torch.bfloat16)
    print("模型已转换为BF16")
    return model


def convert_to_fp16(model):
    """转换为FP16"""
    model = model.half()
    print("模型已转换为FP16")
    return model


# ==================== 4. 激活重计算 ====================

class ActivationRecompute:
    """激活重计算上下文"""
    
    def __init__(self, model):
        self.model = model
        self.original_forward = {}
    
    def enable(self):
        """启用激活重计算"""
        from torch.utils.checkpoint import checkpoint
        
        for name, module in self.model.named_modules():
            if len(list(module.children())) == 0 and hasattr(module, 'forward'):
                self.original_forward[name] = module.forward
                
                def make_checkpointed_forward(original_forward):
                    def forward(*args, **kwargs):
                        return checkpoint(original_forward, *args, use_reentrant=False, **kwargs)
                    return forward
                
                module.forward = make_checkpointed_forward(module.forward)
        
        print("激活重计算已启用")
    
    def disable(self):
        """禁用激活重计算"""
        for name, module in self.model.named_modules():
            if name in self.original_forward:
                module.forward = self.original_forward[name]
        
        print("激活重计算已禁用")


# ==================== 5. 内存清理 ====================

def aggressive_memory_cleanup():
    """激进内存清理"""
    gc.collect()
    
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
        torch.cuda.reset_peak_memory_stats()


def get_memory_stats():
    """获取内存统计"""
    stats = {}
    
    if torch.cuda.is_available():
        stats['allocated'] = torch.cuda.memory_allocated() / 1024**2
        stats['reserved'] = torch.cuda.memory_reserved() / 1024**2
        stats['max_allocated'] = torch.cuda.max_memory_allocated() / 1024**2
    
    return stats


# ==================== 6. 内存优化训练器 ====================

class MemoryEfficientTrainer:
    """内存高效训练器"""
    
    def __init__(
        self,
        model,
        optimizer,
        use_gradient_checkpointing: bool = True,
        use_amp: bool = True,
        accumulation_steps: int = 4
    ):
        self.model = model
        self.optimizer = optimizer
        self.accumulation_steps = accumulation_steps
        
        if use_gradient_checkpointing:
            self.model = enable_gradient_checkpointing(self.model)
        
        self.use_amp = use_amp and torch.cuda.is_available()
        if self.use_amp:
            self.scaler = torch.cuda.amp.GradScaler()
        
        self.step_count = 0
    
    def train_step(self, batch):
        """训练步骤"""
        self.optimizer.zero_grad()
        
        if self.use_amp:
            with torch.cuda.amp.autocast():
                loss = self._compute_loss(batch)
            
            (loss / self.accumulation_steps).backward()
            
            self.step_count += 1
            if self.step_count % self.accumulation_steps == 0:
                self.scaler.step(self.optimizer)
                self.scaler.update()
        else:
            loss = self._compute_loss(batch)
            (loss / self.accumulation_steps).backward()
            
            self.step_count += 1
            if self.step_count % self.accumulation_steps == 0:
                self.optimizer.step()
        
        return loss.item()
    
    def _compute_loss(self, batch):
        """计算损失"""
        output = self.model(batch)
        return output.mean()


# ==================== 内存使用对比 ====================

def compare_memory_usage():
    """比较不同方法的内存使用"""
    print("=" * 60)
    print("内存使用对比")
    print("=" * 60)
    
    if not torch.cuda.is_available():
        print("需要CUDA来测试内存使用")
        return
    
    # 清理内存
    aggressive_memory_cleanup()
    
    # 创建测试模型
    model = nn.Sequential(
        nn.Linear(1024, 2048),
        nn.ReLU(),
        nn.Linear(2048, 2048),
        nn.ReLU(),
        nn.Linear(2048, 1024)
    ).cuda()
    
    x = torch.randn(8, 1024).cuda()
    
    # 测试普通训练
    print("\n1. 普通训练:")
    aggressive_memory_cleanup()
    
    output = model(x)
    loss = output.sum()
    loss.backward()
    
    stats1 = get_memory_stats()
    print(f"   已分配: {stats1['allocated']:.2f} MB")
    
    del output, loss
    aggressive_memory_cleanup()
    
    # 测试混合精度
    print("\n2. 混合精度训练:")
    aggressive_memory_cleanup()
    
    with torch.cuda.amp.autocast():
        output = model(x)
        loss = output.sum()
    
    loss.backward()
    
    stats2 = get_memory_stats()
    print(f"   已分配: {stats2['allocated']:.2f} MB")
    
    del output, loss
    aggressive_memory_cleanup()
    
    print(f"\n内存节省: {(stats1['allocated'] - stats2['allocated']):.2f} MB")
    print(f"节省比例: {(1 - stats2['allocated'] / stats1['allocated']) * 100:.1f}%")


if __name__ == "__main__":
    compare_memory_usage()
```

---

**恭喜你完成了MiniMind完整教程的学习！**

这个教程涵盖了从基础概念到高级应用的所有内容。通过动手实践这些代码，你已经掌握了：

1. **模型架构**：Transformer、注意力机制、位置编码等
2. **训练技术**：混合精度、梯度累积、分布式训练等
3. **推理优化**：KV Cache、采样策略、批处理等
4. **模型优化**：量化、剪枝、知识蒸馏等
5. **部署实践**：模型导出、服务化、容器化等
6. **代码解析**：逐行理解MiniMind核心代码
7. **问题解决**：常见问题解答和调试技巧
8. **项目实战**：问答系统和分类系统案例
9. **代码质量**：风格规范和测试实践
10. **交互练习**：多头注意力、RoPE、SwiGLU等实现练习
11. **调试技巧**：NaN/Inf处理、梯度检查、内存分析
12. **性能优化**：训练加速、推理加速、内存优化

---

## 📋 模块学习检查点

### 模块1：模型架构 - 学习检查点

**核心概念检查**：
- [ ] 理解Transformer Decoder-Only架构
- [ ] 掌握多头注意力机制的计算过程
- [ ] 理解RoPE位置编码的原理
- [ ] 能够解释RMSNorm与LayerNorm的区别
- [ ] 理解SwiGLU激活函数的优势

**实践能力检查**：
- [ ] 能够独立实现Multi-Head Attention
- [ ] 能够实现RoPE位置编码
- [ ] 能够计算模型的参数量

**自测问题**：
1. 为什么Decoder-Only架构使用因果掩码？
2. GQA如何减少KV Cache的内存占用？
3. Pre-Norm和Post-Norm各有什么优缺点？

---

### 模块2：训练技术 - 学习检查点

**核心概念检查**：
- [ ] 理解混合精度训练的原理
- [ ] 掌握梯度累积的使用场景
- [ ] 理解学习率Warmup的作用
- [ ] 了解分布式训练的基本概念

**实践能力检查**：
- [ ] 能够配置混合精度训练
- [ ] 能够实现梯度累积训练循环
- [ ] 能够使用学习率调度器

**自测问题**：
1. 混合精度训练为什么需要损失缩放？
2. 梯度累积与增大batch_size有什么区别？
3. Cosine Decay学习率调度的优势是什么？

---

### 模块3：推理优化 - 学习检查点

**核心概念检查**：
- [ ] 理解KV Cache的工作原理
- [ ] 掌握各种采样策略的特点
- [ ] 理解温度参数的作用
- [ ] 了解批处理推理的优化方法

**实践能力检查**：
- [ ] 能够实现带KV Cache的推理
- [ ] 能够实现Top-K和Top-P采样
- [ ] 能够实现流式文本生成

**自测问题**：
1. KV Cache如何加速自回归生成？
2. Top-P采样相比Top-K采样有什么优势？
3. 如何选择合适的温度参数？

---

### 模块4：模型优化 - 学习检查点

**核心概念检查**：
- [ ] 理解模型量化的基本原理
- [ ] 掌握LoRA微调的方法
- [ ] 了解知识蒸馏的流程
- [ ] 理解模型剪枝的类型

**实践能力检查**：
- [ ] 能够进行模型动态量化
- [ ] 能够实现LoRA微调
- [ ] 能够评估量化模型的性能

**自测问题**：
1. 动态量化和静态量化的区别是什么？
2. LoRA为什么能减少微调参数量？
3. 知识蒸馏中教师模型和学生模型的关系？

---

### 模块5：部署实践 - 学习检查点

**核心概念检查**：
- [ ] 理解模型导出的各种格式
- [ ] 掌握服务化部署的基本方法
- [ ] 了解容器化部署的流程
- [ ] 理解模型服务化的架构

**实践能力检查**：
- [ ] 能够将模型导出为ONNX格式
- [ ] 能够使用FastAPI构建模型服务
- [ ] 能够编写Dockerfile部署模型

**自测问题**：
1. TorchScript和ONNX各有什么优缺点？
2. 如何设计高可用的模型服务架构？
3. 生产环境中如何处理模型版本管理？

---

### 模块6：代码解析 - 学习检查点

**核心概念检查**：
- [ ] 理解MiniMind的整体架构
- [ ] 掌握各组件的实现细节
- [ ] 理解数据流的处理过程
- [ ] 了解训练代码的组织结构

**实践能力检查**：
- [ ] 能够阅读并理解MiniMind源码
- [ ] 能够修改模型配置参数
- [ ] 能够调试模型训练过程

**自测问题**：
1. MiniMind的参数量如何计算？
2. RoPE在代码中是如何实现的？
3. 训练循环中的关键步骤有哪些？

---

### 模块7：问题解决 - 学习检查点

**核心概念检查**：
- [ ] 掌握常见问题的解决方法
- [ ] 理解错误诊断的流程
- [ ] 了解调试工具的使用
- [ ] 掌握日志分析方法

**实践能力检查**：
- [ ] 能够诊断和解决NaN问题
- [ ] 能够使用调试工具定位问题
- [ ] 能够分析训练日志

**自测问题**：
1. 训练过程中出现NaN如何排查？
2. 如何判断是梯度爆炸还是梯度消失？
3. 如何分析GPU内存使用情况？

---

### 模块8：项目实战 - 学习检查点

**核心概念检查**：
- [ ] 理解问答系统的架构
- [ ] 掌握文本分类的方法
- [ ] 了解项目组织的最佳实践
- [ ] 理解端到端的开发流程

**实践能力检查**：
- [ ] 能够构建简单的问答系统
- [ ] 能够实现文本分类任务
- [ ] 能够组织项目代码结构

**自测问题**：
1. 问答系统中检索和生成如何结合？
2. 文本分类任务如何设计标签体系？
3. 如何评估模型在实际任务中的表现？

---

### 模块9：代码质量 - 学习检查点

**核心概念检查**：
- [ ] 掌握Python编码规范
- [ ] 理解文档编写的重要性
- [ ] 了解单元测试的方法
- [ ] 掌握持续集成的基本概念

**实践能力检查**：
- [ ] 能够编写规范的Python代码
- [ ] 能够编写完整的Docstring
- [ ] 能够编写单元测试用例

**自测问题**：
1. 为什么类型注解对代码质量很重要？
2. 单元测试应该覆盖哪些场景？
3. 如何设计有效的CI/CD流程？

---

### 模块10：交互练习 - 学习检查点

**核心概念检查**：
- [ ] 深入理解注意力机制
- [ ] 掌握位置编码的实现
- [ ] 理解激活函数的设计
- [ ] 掌握完整模型的组装

**实践能力检查**：
- [ ] 能够独立实现Multi-Head Attention
- [ ] 能够实现RoPE位置编码
- [ ] 能够实现SwiGLU激活函数
- [ ] 能够组装完整的Transformer Block

**自测问题**：
1. 注意力计算中为什么要除以sqrt(d_k)？
2. RoPE如何实现相对位置编码？
3. SwiGLU相比普通FFN有什么优势？

---

### 模块11：调试技巧 - 学习检查点

**核心概念检查**：
- [ ] 掌握数值调试的方法
- [ ] 理解梯度调试的技巧
- [ ] 了解内存调试的工具
- [ ] 掌握性能分析的方法

**实践能力检查**：
- [ ] 能够诊断NaN/Inf问题
- [ ] 能够检查梯度状态
- [ ] 能够分析内存使用
- [ ] 能够进行性能基准测试

**自测问题**：
1. 如何快速定位NaN出现的层？
2. 如何判断模型是否存在梯度消失？
3. 如何找出模型的性能瓶颈？

---

### 模块12：性能优化 - 学习检查点

**核心概念检查**：
- [ ] 掌握训练加速的方法
- [ ] 理解推理优化的技术
- [ ] 了解内存优化的策略
- [ ] 掌握编译优化的原理

**实践能力检查**：
- [ ] 能够配置混合精度训练
- [ ] 能够使用模型量化加速推理
- [ ] 能够优化内存使用
- [ ] 能够使用torch.compile

**自测问题**：
1. 混合精度训练能带来多少加速？
2. 梯度检查点如何节省内存？
3. 如何选择合适的量化方法？

---

## 🎯 学习成果总结

### 知识体系构建

通过本教程的学习，你已经建立了完整的LLM知识体系：

```
知识体系结构
├── 理论基础
│   ├── Transformer架构原理
│   ├── 注意力机制数学推导
│   ├── 位置编码设计思想
│   └── 训练优化理论
│
├── 工程实践
│   ├── 模型实现与调试
│   ├── 训练流程搭建
│   ├── 推理服务部署
│   └── 性能优化技巧
│
└── 项目应用
    ├── 问答系统开发
    ├── 文本分类应用
    ├── 模型微调实践
    └── 生产环境部署
```

### 技能掌握清单

| 技能类别 | 具体技能 | 掌握程度 |
|----------|----------|----------|
| 模型开发 | Transformer实现、注意力机制、位置编码 | ⭐⭐⭐⭐⭐ |
| 训练技术 | 混合精度、梯度累积、分布式训练 | ⭐⭐⭐⭐ |
| 推理优化 | KV Cache、采样策略、批处理 | ⭐⭐⭐⭐ |
| 模型优化 | 量化、剪枝、LoRA、蒸馏 | ⭐⭐⭐ |
| 部署实践 | ONNX导出、服务化、容器化 | ⭐⭐⭐ |
| 调试能力 | 问题诊断、性能分析、内存优化 | ⭐⭐⭐⭐ |

### 下一步学习建议

1. **深入研究**：
   - 阅读Transformer原始论文
   - 学习LLaMA、GPT等开源模型
   - 关注最新的模型架构创新

2. **实践项目**：
   - 从零训练一个小型语言模型
   - 微调模型用于特定任务
   - 构建完整的AI应用

3. **社区参与**：
   - 参与开源项目贡献
   - 分享学习心得
   - 关注技术社区动态

---

继续探索，构建你自己的AI应用！

---

祝你学习愉快，在AI的道路上不断探索！
