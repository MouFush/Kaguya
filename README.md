# Kaguya IDE v3.1.0

> AI-Powered Development Environment — 面向开发、运营、增长与职场场景的高质量 AI 助手

---

## 快速开始

### 方式一：桌面端直接运行（推荐，无需安装 Python）

1. 解压 `KaguyaIDE-3.1.0-win64-Desktop.7z`
2. 双击运行 `Kaguya IDE.exe`
3. 在配置页面输入 API Key（支持 DeepSeek / OpenAI / Claude / Qwen 等）
4. 开始对话！

### 方式二：命令行启动（需要 Python 3.9+）

```bash
# 使用DL虚拟环境
conda activate DL
python start_server.py

# 或直接启动Web服务
python qwen3_web.py --port 58000
```

访问 `http://127.0.0.1:58000`

### 方式三：使用 Ollama 本地模型

```bash
# 安装Ollama并下载模型
ollama pull qwen3.5:4b

# 启动IDE
python qwen3_web.py
```

---

## 核心功能

| 功能 | 说明 |
|------|------|
| 🤖 智能对话 | 流式响应、多轮对话、角色扮演 |
| 💻 代码助手 | Python/JS/C/C++/Java/Go/Rust 在线执行 |
| 📁 文件管理 | 上传、分析、多文件操作 |
| 🛠 工具调用 | 网络搜索、代码执行、文件读写 |
| 📚 知识库/RAG | 文档上传、向量检索、上下文增强 |
| 🎛 LoRA 微调 | 模型低秩适配、在线训练与切换 |
| 🔄 工作流 | 可视化工作流编辑器、自动执行 |
| 📊 项目管理 | Tasks、Milestones、Risks 全生命周期 |
| 🧪 A/B 实验 | 在线实验设计、指标分析 |
| 🚨 告警中心 | 自定义告警规则、实时监控 |
| 🧩 集成市场 | 第三方服务集成管理 |
| 🔐 安全框架 | IP白名单、JWT认证、审计日志 |
| 🗄 隐私管理 | 数据导出、账户删除、隐私设置 |

---

## 系统架构

```
┌─────────────────────────────────────────────┐
│             Kaguya IDE Desktop               │
│  ┌─────────────────┐  ┌──────────────────┐  │
│  │  Electron Shell  │  │  MiniServer      │  │
│  │  (Chromium UI)   │  │  (Node.js API)   │  │
│  └────────┬─────────┘  └────────┬─────────┘  │
│           │                     │            │
│           ▼                     ▼            │
│  ┌──────────────────────────────────────┐    │
│  │     Python Flask Backend              │    │
│  │  ┌──────┐ ┌───────┐ ┌───────────┐   │    │
│  │  │ Olla│ │ AGENT │ │ TOOLS/HOOKS│   │    │
│  │  │Adapter│ │SYSTEM │ │/FEATURES   │   │    │
│  │  └──────┘ └───────┘ └───────────┘   │    │
│  └──────────────────────────────────────┘    │
│           │                     │            │
│           ▼                     ▼            │
│  ┌──────────────┐  ┌────────────────────┐    │
│  │  Ollama /    │  │  External APIs     │    │
│  │  Local Model │  │  (DeepSeek/OpenAI) │    │
│  └──────────────┘  └────────────────────┘    │
└─────────────────────────────────────────────┘
```

---

## 安装要求

### 桌面端（Electron）
- Windows 10+ x64
- 无需 Python、无需 Ollama

### 完整版（Python后端）
- Python 3.9+
- Flask >= 2.3.0
- NumPy >= 1.24.0
- scikit-learn >= 1.3.0
- Ollama (可选，用于本地模型)

### 可选依赖
| 包 | 用途 |
|----|------|
| torch | PyTorch GPU推理 |
| transformers | HuggingFace模型 |
| peft | LoRA微调 |
| chromadb | 向量数据库 |
| openai | API代理 |

---

## 项目结构

```
kaguya-desktop/
├── electron/              # Electron主进程
│   ├── main.js           # 主入口 + MiniServer
│   ├── preload.js        # 预加载脚本
│   └── package.json
├── src/                   # Python源码
│   ├── qwen3_web.py      # Flask Web主应用
│   ├── ollama_adapter.py # Ollama适配器
│   ├── kaguya_bootstrap.py # 核心引导层
│   ├── kaguya_agents.py  # Agent系统
│   ├── kaguya_skills.py  # Skill系统
│   ├── kaguya_acp.py     # ACP协议
│   ├── kaguya_permissions.py # 权限系统
│   ├── kaguya_accounts.py # 账户系统
│   ├── kaguya_memory.py  # 记忆系统
│   ├── kaguya_terminal.py # 终端系统
│   └── ...
├── kaguya_core/           # 核心框架
│   ├── config.py         # 统一配置
│   ├── base_manager.py   # 基础管理器
│   ├── models.py         # 数据模型
│   ├── utils.py          # 工具函数
│   └── ...
├── static/                # 前端资源
│   ├── css/
│   └── js/
├── assets/                # 图片/图标
├── package.json           # Electron-builder配置
└── build.py              # 构建脚本
```

---

## 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--port` | 指定端口 | 5000 |
| `--host` | 绑定IP | 127.0.0.1 |
| `--localhost-only` | 仅本地访问 | false |
| `--https` | 启用HTTPS | false |
| `--cert` | SSL证书路径 | cert.pem |
| `--key` | SSL密钥路径 | key.pem |
| `--debug` | 调试模式 | false |

---

## 环境变量

| 变量 | 说明 |
|------|------|
| `KAGUYA_DESKTOP_MODE` | 桌面模式（禁用ngrok等） |
| `KAGUYA_PORT` | 指定端口 |
| `KAGUYA_SECRET_KEY` | 加密主密钥 |
| `KAGUYA_PERMISSION_MODE` | 权限模式：bypassPermissions |

---

## 支持的API提供商

| 提供商 | 默认URL | 模型 |
|--------|---------|------|
| DeepSeek | https://api.deepseek.com | deepseek-chat |
| OpenAI | https://api.openai.com/v1 | gpt-4o |
| Claude | https://api.anthropic.com | claude-3-7-sonnet |
| Qwen | https://dashscope.aliyuncs.com/compatible-mode/v1 | qwen-plus |
| Moonshot | https://api.moonshot.cn/v1 | moonshot-v1-8k |
| Zhipu | https://open.bigmodel.cn/api/paas/v4 | glm-4-flash |
| Groq | https://api.groq.com/openai/v1 | llama-3.3-70b |

---

## 构建

```bash
# 安装依赖
npm install

# 打包Windows桌面版
npx electron-builder --win --x64 --dir

# 打包所有平台
npx electron-builder --win --mac --linux

# 压缩发布包
7za a -t7z KaguyaIDE-3.1.0-win64-Desktop.7z dist-electron-final/win-unpacked/*
```

---

## 许可

MIT License

---

## 更新日志

### v3.1.0
- 新增 Electron 桌面端支持
- 新增 Node.js MiniServer（无Python也能运行）
- 修复 Ollama 流式响应超时问题
- 修复 KaguyaBootstrap 子系统初始化问题
- 修复 Feature Flags API 返回 500 错误
- 新增文件上传/管理功能（桌面端）
- 新增自包含 SPA 前端（无需 Flask）
- 图片资源更新为辉夜姬角色图
- 外部API代理支持 7 个提供商
