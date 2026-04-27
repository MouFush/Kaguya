# 🌟 辉夜AI - 企业级Agent编排系统架构

## 系统概述

本系统整合了GitHub上最先进技术（AutoGen + AutoGPT + Dify），构建了一个完整的企业级Agent编排平台。

### 核心特性

- ✅ **多Agent协作系统** - 参考Microsoft AutoGen
- ✅ **自主规划与执行** - 参考AutoGPT/BabyAGI
- ✅ **工作流编排引擎** - 参考Dify/n8n
- ✅ **LLM多厂商适配** - 支持OpenAI/Claude/百度/阿里
- ✅ **长期记忆系统** - 6层记忆架构+知识蒸馏

---

## 🏗️ 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                      辉夜AI 编排系统                              │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  多Agent协作 │  │  自主规划   │  │  工作流编排  │             │
│  │  GroupChat  │  │ Autonomous  │  │  Workflow   │             │
│  │             │  │   Agent     │  │   Engine    │             │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
│         │                │                │                     │
│         └────────────────┼────────────────┘                     │
│                          │                                      │
│              ┌───────────┴───────────┐                         │
│              │   AgentOrchestrator   │                         │
│              │    (统一编排管理器)    │                         │
│              └───────────┬───────────┘                         │
│                          │                                      │
├──────────────────────────┼──────────────────────────────────────┤
│  基础设施层               │                                      │
│  ┌─────────────┐  ┌──────┴──────┐  ┌─────────────┐             │
│  │  LLM适配器  │  │  记忆系统   │  │  工具市场   │             │
│  │  Adapter    │  │  Memory     │  │   Tools     │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📦 核心模块

### 1. 多Agent协作系统 (Multi-Agent Collaboration)

参考 **Microsoft AutoGen** 设计

#### 核心组件

| 组件 | 说明 | 特性 |
|------|------|------|
| `BaseAgent` | Agent基类 | 抽象基类，定义Agent标准接口 |
| `SimpleAgent` | 简单实现 | 可直接实例化的Agent |
| `GroupChat` | 群聊管理 | 多Agent群聊、发言控制 |
| `NestedChat` | 嵌套对话 | 子对话、上下文继承 |

#### Agent角色

```python
class AgentRole(Enum):
    COORDINATOR = "coordinator"   # 协调者 - 分配任务
    PLANNER = "planner"           # 规划者 - 制定计划
    EXECUTOR = "executor"         # 执行者 - 执行任务
    CRITIC = "critic"             # 评估者 - 质量审查
    SPECIALIST = "specialist"     # 专家 - 专业领域
    USER_PROXY = "user_proxy"     # 用户代理
```

#### 使用示例

```python
from agent_orchestration_system import AgentOrchestrator, SimpleAgent, AgentRole

# 创建编排器
orchestrator = AgentOrchestrator()

# 创建Agent
agent1 = SimpleAgent(name="产品经理", role=AgentRole.SPECIALIST)
agent2 = SimpleAgent(name="开发工程师", role=AgentRole.EXECUTOR)

# 注册Agent
orchestrator.register_agent(agent1)
orchestrator.register_agent(agent2)

# 创建群聊
chat = orchestrator.create_group_chat(
    name="开发团队",
    agent_names=["产品经理", "开发工程师"],
    max_round=10
)

# 启动群聊
await chat.start("开发用户认证系统")
```

---

### 2. 自主规划与执行框架 (Autonomous Planning)

参考 **AutoGPT/BabyAGI** 设计

#### 核心组件

| 组件 | 说明 | 特性 |
|------|------|------|
| `TaskPlanner` | 任务规划器 | 目标分解、策略选择 |
| `TaskExecutor` | 任务执行器 | 优先级队列、依赖管理 |
| `ReflectionEngine` | 反思引擎 | 结果评估、自我改进 |
| `AutonomousAgent` | 自主Agent | 规划+执行+反思一体化 |

#### 规划策略

1. **Sequential** - 顺序执行（有依赖）
2. **Parallel** - 并行执行（无依赖）
3. **Hierarchical** - 分层规划（阶段+子任务）

#### 任务状态流转

```
PENDING → IN_PROGRESS → COMPLETED
   ↓           ↓            ↓
BLOCKED    FAILED       CANCELLED
```

#### 使用示例

```python
from agent_orchestration_system import AutonomousAgent, Message, MessageType

# 创建自主Agent
agent = AutonomousAgent(name="规划助手")

# 发送规划请求
message = Message(
    content="开发电商平台",
    message_type=MessageType.PLAN
)

# Agent自动规划、执行、反思
response = await agent.think(message)
```

---

### 3. 工作流编排系统 (Workflow Orchestration)

参考 **Dify/n8n** 设计

#### 核心组件

| 组件 | 说明 | 特性 |
|------|------|------|
| `Workflow` | 工作流定义 | 节点管理、连接关系 |
| `WorkflowNode` | 工作流节点 | 多种类型、配置灵活 |
| `WorkflowEngine` | 执行引擎 | 状态机驱动、上下文传递 |

#### 节点类型

```python
class WorkflowNodeType(Enum):
    START = "start"           # 开始节点
    END = "end"               # 结束节点
    AGENT = "agent"           # Agent节点
    CONDITION = "condition"   # 条件分支
    LOOP = "loop"             # 循环节点
    PARALLEL = "parallel"     # 并行节点
    TOOL = "tool"             # 工具节点
    DELAY = "delay"           # 延迟节点
    WEBHOOK = "webhook"       # Webhook节点
```

#### 使用示例

```python
from agent_orchestration_system import (
    Workflow, WorkflowNode, WorkflowNodeType
)

# 创建工作流
workflow = Workflow(name="内容创作")

# 添加节点
start = WorkflowNode(name="开始", node_type=WorkflowNodeType.START)
draft = WorkflowNode(
    name="撰写",
    node_type=WorkflowNodeType.AGENT,
    config={"agent_name": "创作者", "message": "创作内容"}
)
review = WorkflowNode(
    name="审查",
    node_type=WorkflowNodeType.AGENT,
    config={"agent_name": "评估员", "message": "审查质量"}
)
end = WorkflowNode(name="完成", node_type=WorkflowNodeType.END)

# 连接节点
workflow.add_node(start)
workflow.add_node(draft)
workflow.add_node(review)
workflow.add_node(end)

workflow.connect_nodes(start.id, draft.id)
workflow.connect_nodes(draft.id, review.id)
workflow.connect_nodes(review.id, end.id)

# 执行工作流
execution_id = await orchestrator.workflow_engine.execute(
    workflow.id,
    initial_context={"topic": "AI技术"}
)
```

---

## 🔧 集成使用

### 完整集成示例

```python
from agent_integration_example import KaguyaAIAssistant

# 初始化系统
assistant = KaguyaAIAssistant()

# 配置LLM适配器
assistant.setup_llm_adapter(
    provider="openai",
    api_key="your-api-key",
    model="gpt-4",
    enable_memory=True
)

# 1. 多Agent协作
await assistant.create_team_chat("开发用户认证系统")

# 2. 自主规划
plan = await assistant.create_autonomous_plan("开发电商平台")

# 3. 工作流编排
workflow = assistant.create_workflow(
    name="内容创作",
    workflow_type="content_creation"
)
execution_id = await assistant.execute_workflow(
    "内容创作",
    context={"topic": "AI Agent"}
)

# 查看系统状态
status = assistant.get_system_status()
print(f"Agent数量: {status['agents']}")
print(f"工作流数量: {status['workflows']}")
```

---

## 📊 系统对比

| 特性 | 辉夜AI | AutoGen | AutoGPT | Dify |
|------|--------|---------|---------|------|
| 多Agent协作 | ✅ | ✅ | ⚠️ | ⚠️ |
| 自主规划 | ✅ | ⚠️ | ✅ | ❌ |
| 工作流编排 | ✅ | ❌ | ❌ | ✅ |
| 可视化界面 | 🚧 | ❌ | ⚠️ | ✅ |
| 开源 | ✅ | ✅ | ✅ | ✅ |
| 中文支持 | ✅ | ⚠️ | ⚠️ | ⚠️ |

🚧 = 开发中

---

## 🚀 扩展开发

### 自定义Agent

```python
from agent_orchestration_system import BaseAgent, Message

class MyCustomAgent(BaseAgent):
    async def think(self, message: Message) -> str:
        # 自定义思考逻辑
        # 可以调用LLM、工具、其他Agent
        response = await self.call_llm(message.content)
        return response
    
    async def call_llm(self, content: str) -> str:
        # 调用LLM
        pass
```

### 自定义工具

```python
# 注册工具
agent.register_tool("search", search_function)
agent.register_tool("calculator", calculator_function)

# 使用工具
result = await agent.execute_tool("search", query="AI技术")
```

### 自定义工作流节点

```python
class CustomNode(WorkflowNode):
    async def execute(self, context: Dict) -> Dict:
        # 自定义执行逻辑
        result = await self.process(context)
        return {"status": "success", "data": result}
```

---

## 📁 文件清单

| 文件 | 说明 | 大小 |
|------|------|------|
| `agent_orchestration_system.py` | 核心编排系统 | ~1400行 |
| `agent_integration_example.py` | 集成示例 | ~430行 |
| `llm_adapter.py` | LLM适配器 | ~350行 |
| `advanced_memory_system.py` | 记忆系统 | ~600行 |
| `memory_integration.py` | 记忆集成 | ~200行 |

---

## 🎯 应用场景

### 1. 软件开发团队
- 产品经理 → 需求分析
- 架构师 → 系统设计
- 开发工程师 → 代码实现
- 测试工程师 → 质量保障

### 2. 内容创作流程
- 资料收集 → 撰写草稿 → 质量审查 → 修改完善

### 3. 数据分析流程
- 数据清洗 → 数据分析 → 生成图表 → 撰写报告

### 4. 代码审查流程
- 代码分析 → 代码审查 → 测试验证 → 合并发布

---

## 🔮 未来规划

- [ ] 可视化工作流编辑器
- [ ] 更多LLM厂商支持
- [ ] 插件市场
- [ ] 实时监控面板
- [ ] 多模态Agent支持

---

## 📄 许可证

MIT License - 开源免费使用

---

**辉夜AI - 让AI协作更智能** 🌙
