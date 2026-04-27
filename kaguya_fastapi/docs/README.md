# Kaguya AI Platform - FastAPI版本

辉夜AI助手后端API - 基于FastAPI的专业级架构

## 🚀 特性

- **FastAPI框架**: 现代、快速、异步的Python Web框架
- **自动API文档**: 内置Swagger UI和ReDoc
- **类型安全**: Pydantic模型验证
- **流式响应**: Server-Sent Events支持
- **模块化架构**: 易于扩展和维护
- **Docker支持**: 一键部署

## 📁 项目结构

```
kaguya_fastapi/
├── app/
│   ├── api/v1/          # API路由
│   │   ├── chat.py      # 聊天接口
│   │   ├── roles.py     # 角色管理
│   │   ├── deepseek.py  # DeepSeek API
│   │   ├── knowledge.py # 知识库
│   │   └── memory.py    # 记忆系统
│   ├── core/            # 核心配置
│   │   ├── config.py    # 应用配置
│   │   ├── security.py  # 安全相关
│   │   └── logging.py   # 日志配置
│   ├── models/          # 数据模型
│   │   └── schemas.py   # Pydantic模型
│   ├── services/        # 业务逻辑
│   │   └── llm_service.py
│   └── main.py          # 应用入口
├── tests/               # 测试
├── docs/                # 文档
├── requirements.txt     # 依赖
├── Dockerfile          # 容器镜像
└── docker-compose.yml  # 编排配置
```

## 🛠️ 安装

### 方式1: 本地运行

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 运行应用
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 方式2: Docker运行

```bash
# 构建镜像
docker build -t kaguya-api .

# 运行容器
docker run -p 8000:8000 kaguya-api
```

### 方式3: Docker Compose

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f api
```

## 📖 API文档

启动服务后访问:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **健康检查**: http://localhost:8000/health

## 🔌 API端点

### 聊天
- `POST /api/v1/chat` - 非流式聊天
- `POST /api/v1/chat/stream` - 流式聊天
- `GET /api/v1/chat/models` - 获取可用模型

### 角色
- `GET /api/v1/roles` - 获取角色列表
- `GET /api/v1/roles/{role_id}` - 获取角色详情
- `GET /api/v1/roles/{role_id}/system-prompt` - 获取系统提示词

### DeepSeek
- `GET /api/v1/deepseek/status` - API状态
- `POST /api/v1/deepseek/config` - 更新配置
- `POST /api/v1/deepseek/chat` - 聊天
- `POST /api/v1/deepseek/chat/stream` - 流式聊天

### 知识库
- `POST /api/v1/knowledge/documents` - 上传文档
- `GET /api/v1/knowledge/documents` - 文档列表
- `GET /api/v1/knowledge/documents/{doc_id}` - 文档详情
- `DELETE /api/v1/knowledge/documents/{doc_id}` - 删除文档
- `POST /api/v1/knowledge/query` - RAG查询
- `GET /api/v1/knowledge/stats` - 统计信息

### 记忆
- `POST /api/v1/memory` - 创建记忆
- `GET /api/v1/memory` - 记忆列表
- `GET /api/v1/memory/{memory_id}` - 记忆详情
- `POST /api/v1/memory/query` - 查询记忆
- `DELETE /api/v1/memory/{memory_id}` - 删除记忆

## ⚙️ 配置

通过环境变量配置:

```bash
# .env文件
HOST=0.0.0.0
PORT=8000
DEBUG=false
DATABASE_URL=sqlite+aiosqlite:///./kaguya_ai.db
REDIS_URL=redis://localhost:6379/0
DEEPSEEK_API_KEY=your-api-key
DEEPSEEK_API_URL=https://api.deepseek.com
SECRET_KEY=your-secret-key
```

## 🧪 测试

```bash
# 运行测试
pytest tests/

# 覆盖率报告
pytest --cov=app tests/
```

## 📝 开发计划

- [ ] 集成真实LLM模型 (Qwen3-8B)
- [ ] 实现向量数据库 (Chroma/Milvus)
- [ ] 添加用户认证 (JWT)
- [ ] 实现WebSocket支持
- [ ] 添加监控和日志
- [ ] 性能优化 (缓存、连接池)

## 📄 许可证

MIT License
