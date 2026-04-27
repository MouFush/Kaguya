#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A2A (Agent2Agent) 多智能体协作系统
实现智能体间的标准化通信协议，支持多智能体协作完成任务
"""

import asyncio
import json
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """智能体状态"""
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"
    ERROR = "error"


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MessageType(Enum):
    """A2A消息类型"""
    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    TASK_UPDATE = "task_update"
    CAPABILITY_QUERY = "capability_query"
    CAPABILITY_RESPONSE = "capability_response"
    COLLABORATION_REQUEST = "collaboration_request"
    COLLABORATION_RESPONSE = "collaboration_response"
    STATUS_UPDATE = "status_update"
    ERROR = "error"


@dataclass
class AgentCapability:
    """智能体能力"""
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }


@dataclass
class AgentProfile:
    """智能体档案"""
    id: str
    name: str
    description: str
    capabilities: List[AgentCapability] = field(default_factory=list)
    status: AgentStatus = AgentStatus.IDLE
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "capabilities": [cap.to_dict() for cap in self.capabilities],
            "status": self.status.value,
            "metadata": self.metadata
        }


@dataclass
class A2AMessage:
    """A2A消息"""
    id: str
    type: MessageType
    sender_id: str
    receiver_id: str
    payload: Dict[str, Any]
    timestamp: datetime = None
    reply_to: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "reply_to": self.reply_to
        }


@dataclass
class Task:
    """任务"""
    id: str
    description: str
    status: TaskStatus
    assigned_to: Optional[str] = None
    created_by: str = ""
    created_at: datetime = None
    completed_at: Optional[datetime] = None
    result: Any = None
    subtasks: List['Task'] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "status": self.status.value,
            "assigned_to": self.assigned_to,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "subtasks": [t.to_dict() for t in self.subtasks],
            "dependencies": self.dependencies
        }


class BaseAgent:
    """基础智能体类"""
    
    def __init__(self, agent_id: str, name: str, description: str):
        self.profile = AgentProfile(
            id=agent_id,
            name=name,
            description=description
        )
        self.message_handler: Optional[Callable] = None
        self.task_handler: Optional[Callable] = None
        self.received_messages: List[A2AMessage] = []
        self.active_tasks: Dict[str, Task] = {}
        
    def add_capability(self, capability: AgentCapability):
        """添加能力"""
        self.profile.capabilities.append(capability)
        logger.info(f"Agent {self.profile.id} 添加能力: {capability.name}")
    
    async def receive_message(self, message: A2AMessage):
        """接收消息"""
        self.received_messages.append(message)
        logger.info(f"Agent {self.profile.id} 收到消息: {message.type.value}")
        
        # 根据消息类型处理
        if message.type == MessageType.TASK_REQUEST:
            await self._handle_task_request(message)
        elif message.type == MessageType.CAPABILITY_QUERY:
            await self._handle_capability_query(message)
        elif message.type == MessageType.COLLABORATION_REQUEST:
            await self._handle_collaboration_request(message)
        elif message.type == MessageType.STATUS_UPDATE:
            await self._handle_status_update(message)
        
        # 调用自定义处理器
        if self.message_handler:
            await self.message_handler(message)
    
    async def _handle_task_request(self, message: A2AMessage):
        """处理任务请求"""
        task_data = message.payload.get("task", {})
        task = Task(
            id=task_data.get("id", str(uuid.uuid4())),
            description=task_data.get("description", ""),
            status=TaskStatus.ASSIGNED,
            assigned_to=self.profile.id,
            created_by=message.sender_id
        )
        
        self.active_tasks[task.id] = task
        self.profile.status = AgentStatus.BUSY
        
        # 异步执行任务
        asyncio.create_task(self._execute_task(task, message.sender_id))
    
    async def _execute_task(self, task: Task, requester_id: str):
        """执行任务"""
        try:
            task.status = TaskStatus.IN_PROGRESS
            
            # 调用任务处理器
            if self.task_handler:
                result = await self.task_handler(task)
                task.result = result
            else:
                # 默认处理
                task.result = {"status": "completed", "message": f"任务 {task.id} 完成"}
            
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            
            # 发送响应
            await self.send_message(
                receiver_id=requester_id,
                msg_type=MessageType.TASK_RESPONSE,
                payload={
                    "task_id": task.id,
                    "status": "completed",
                    "result": task.result
                },
                reply_to=task.id
            )
            
        except Exception as e:
            logger.error(f"任务执行失败: {e}")
            task.status = TaskStatus.FAILED
            task.result = {"error": str(e)}
            
            await self.send_message(
                receiver_id=requester_id,
                msg_type=MessageType.ERROR,
                payload={
                    "task_id": task.id,
                    "error": str(e)
                }
            )
        
        finally:
            self.profile.status = AgentStatus.IDLE
    
    async def _handle_capability_query(self, message: A2AMessage):
        """处理能力查询"""
        await self.send_message(
            receiver_id=message.sender_id,
            msg_type=MessageType.CAPABILITY_RESPONSE,
            payload={
                "agent_id": self.profile.id,
                "capabilities": [cap.to_dict() for cap in self.profile.capabilities]
            },
            reply_to=message.id
        )
    
    async def _handle_collaboration_request(self, message: A2AMessage):
        """处理协作请求"""
        collaboration_type = message.payload.get("type", "simple")
        
        # 评估是否可以协作
        can_collaborate = self.profile.status == AgentStatus.IDLE
        
        await self.send_message(
            receiver_id=message.sender_id,
            msg_type=MessageType.COLLABORATION_RESPONSE,
            payload={
                "accepted": can_collaborate,
                "agent_id": self.profile.id,
                "reason": "Available" if can_collaborate else "Busy"
            },
            reply_to=message.id
        )
    
    async def _handle_status_update(self, message: A2AMessage):
        """处理状态更新"""
        # 可以在这里更新对其他agent状态的认知
        pass
    
    async def send_message(self, receiver_id: str, msg_type: MessageType, 
                          payload: Dict[str, Any], reply_to: Optional[str] = None):
        """发送消息"""
        message = A2AMessage(
            id=str(uuid.uuid4()),
            type=msg_type,
            sender_id=self.profile.id,
            receiver_id=receiver_id,
            payload=payload,
            reply_to=reply_to
        )
        
        # 通过A2A Hub发送
        await A2AHub.get_instance().route_message(message)
    
    async def request_task(self, target_agent_id: str, task_description: str, 
                          task_params: Dict[str, Any] = None) -> str:
        """向其他agent请求任务"""
        task_id = str(uuid.uuid4())
        
        await self.send_message(
            receiver_id=target_agent_id,
            msg_type=MessageType.TASK_REQUEST,
            payload={
                "task": {
                    "id": task_id,
                    "description": task_description,
                    "parameters": task_params or {}
                }
            }
        )
        
        return task_id
    
    async def query_capabilities(self, target_agent_id: str) -> List[AgentCapability]:
        """查询其他agent的能力"""
        await self.send_message(
            receiver_id=target_agent_id,
            msg_type=MessageType.CAPABILITY_QUERY,
            payload={}
        )
        
        # 等待响应（简化实现，实际应该使用future）
        # 这里返回空列表，实际实现需要异步等待响应
        return []
    
    def set_message_handler(self, handler: Callable):
        """设置消息处理器"""
        self.message_handler = handler
    
    def set_task_handler(self, handler: Callable):
        """设置任务处理器"""
        self.task_handler = handler


class A2AHub:
    """A2A消息中心 - 负责智能体间的消息路由"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.agents: Dict[str, BaseAgent] = {}
            cls._instance.message_history: List[A2AMessage] = []
        return cls._instance
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def register_agent(self, agent: BaseAgent):
        """注册智能体"""
        self.agents[agent.profile.id] = agent
        logger.info(f"注册智能体: {agent.profile.id} - {agent.profile.name}")
    
    def unregister_agent(self, agent_id: str):
        """注销智能体"""
        if agent_id in self.agents:
            del self.agents[agent_id]
            logger.info(f"注销智能体: {agent_id}")
    
    async def route_message(self, message: A2AMessage):
        """路由消息到目标智能体"""
        self.message_history.append(message)
        
        receiver_id = message.receiver_id
        if receiver_id in self.agents:
            await self.agents[receiver_id].receive_message(message)
        else:
            logger.warning(f"目标智能体不存在: {receiver_id}")
    
    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """获取智能体"""
        return self.agents.get(agent_id)
    
    def list_agents(self) -> List[AgentProfile]:
        """列出所有智能体"""
        return [agent.profile for agent in self.agents.values()]
    
    def find_agents_by_capability(self, capability_name: str) -> List[AgentProfile]:
        """根据能力查找智能体"""
        matching_agents = []
        for agent in self.agents.values():
            for cap in agent.profile.capabilities:
                if cap.name == capability_name:
                    matching_agents.append(agent.profile)
                    break
        return matching_agents


class MultiAgentOrchestrator:
    """多智能体编排器 - 协调多个智能体完成复杂任务"""
    
    def __init__(self):
        self.hub = A2AHub.get_instance()
        self.active_workflows: Dict[str, Dict[str, Any]] = {}
    
    async def create_workflow(self, workflow_definition: Dict[str, Any]) -> str:
        """创建工作流"""
        workflow_id = f"workflow_{uuid.uuid4().hex[:8]}"
        
        self.active_workflows[workflow_id] = {
            "id": workflow_id,
            "definition": workflow_definition,
            "status": "created",
            "tasks": [],
            "created_at": datetime.now()
        }
        
        return workflow_id
    
    async def execute_workflow(self, workflow_id: str):
        """执行工作流"""
        if workflow_id not in self.active_workflows:
            raise ValueError(f"工作流不存在: {workflow_id}")
        
        workflow = self.active_workflows[workflow_id]
        workflow["status"] = "running"
        
        try:
            # 解析工作流定义
            steps = workflow["definition"].get("steps", [])
            
            for step in steps:
                step_type = step.get("type")
                
                if step_type == "single_agent":
                    await self._execute_single_agent_step(step)
                elif step_type == "multi_agent":
                    await self._execute_multi_agent_step(step)
                elif step_type == "parallel":
                    await self._execute_parallel_step(step)
                elif step_type == "conditional":
                    await self._execute_conditional_step(step)
            
            workflow["status"] = "completed"
            
        except Exception as e:
            logger.error(f"工作流执行失败: {e}")
            workflow["status"] = "failed"
            workflow["error"] = str(e)
    
    async def _execute_single_agent_step(self, step: Dict[str, Any]):
        """执行单智能体步骤"""
        agent_id = step.get("agent_id")
        task = step.get("task")
        
        agent = self.hub.get_agent(agent_id)
        if not agent:
            raise ValueError(f"智能体不存在: {agent_id}")
        
        # 创建任务消息
        task_id = await agent.request_task(agent_id, task)
        logger.info(f"单智能体任务已分配: {task_id}")
    
    async def _execute_multi_agent_step(self, step: Dict[str, Any]):
        """执行多智能体协作步骤"""
        agent_ids = step.get("agent_ids", [])
        task = step.get("task")
        collaboration_type = step.get("collaboration_type", "sequential")
        
        if collaboration_type == "sequential":
            # 顺序执行
            for agent_id in agent_ids:
                agent = self.hub.get_agent(agent_id)
                if agent:
                    await agent.request_task(agent_id, task)
        elif collaboration_type == "parallel":
            # 并行执行
            tasks = []
            for agent_id in agent_ids:
                agent = self.hub.get_agent(agent_id)
                if agent:
                    task_coro = agent.request_task(agent_id, task)
                    tasks.append(task_coro)
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _execute_parallel_step(self, step: Dict[str, Any]):
        """执行并行步骤"""
        sub_steps = step.get("steps", [])
        
        tasks = []
        for sub_step in sub_steps:
            if sub_step.get("type") == "single_agent":
                task = self._execute_single_agent_step(sub_step)
                tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _execute_conditional_step(self, step: Dict[str, Any]):
        """执行条件步骤"""
        condition = step.get("condition")
        true_branch = step.get("true_branch")
        false_branch = step.get("false_branch")
        
        # 评估条件（简化实现）
        condition_result = True  # 实际应该根据上下文评估
        
        if condition_result and true_branch:
            await self._execute_single_agent_step(true_branch)
        elif not condition_result and false_branch:
            await self._execute_single_agent_step(false_branch)


# 预定义的智能体类型

class ResearchAgent(BaseAgent):
    """研究智能体 - 负责信息收集和研究"""
    
    def __init__(self, agent_id: str = "research_agent"):
        super().__init__(
            agent_id=agent_id,
            name="研究专家",
            description="擅长信息收集、研究和分析"
        )
        
        self.add_capability(AgentCapability(
            name="web_search",
            description="网络搜索和信息收集",
            parameters={"query": "string", "max_results": "integer"}
        ))
        
        self.add_capability(AgentCapability(
            name="deep_research",
            description="深度研究和报告生成",
            parameters={"topic": "string", "depth": "string"}
        ))
        
        self.set_task_handler(self._handle_research_task)
    
    async def _handle_research_task(self, task: Task) -> Dict[str, Any]:
        """处理研究任务"""
        # 这里集成深度研究系统
        from deep_research_system import get_research_engine
        
        engine = get_research_engine()
        research_task_id = await engine.start_research(
            query=task.description,
            depth="standard"
        )
        
        # 等待研究完成
        for _ in range(60):  # 最多等待60秒
            await asyncio.sleep(1)
            status = engine.get_task_status(research_task_id)
            if status["status"] in ["completed", "failed"]:
                break
        
        report = engine.get_task_report(research_task_id)
        return {
            "research_task_id": research_task_id,
            "report": report,
            "status": "completed"
        }


class CodeAgent(BaseAgent):
    """代码智能体 - 负责编程和代码分析"""
    
    def __init__(self, agent_id: str = "code_agent"):
        super().__init__(
            agent_id=agent_id,
            name="代码专家",
            description="擅长编程、代码审查和技术实现"
        )
        
        self.add_capability(AgentCapability(
            name="code_review",
            description="代码审查和优化建议",
            parameters={"code": "string", "language": "string"}
        ))
        
        self.add_capability(AgentCapability(
            name="code_generation",
            description="根据需求生成代码",
            parameters={"requirement": "string", "language": "string"}
        ))
        
        self.set_task_handler(self._handle_code_task)
    
    async def _handle_code_task(self, task: Task) -> Dict[str, Any]:
        """处理代码任务"""
        # 这里集成代码智能体系统
        return {
            "task": task.description,
            "result": "代码任务处理完成",
            "status": "completed"
        }


class WritingAgent(BaseAgent):
    """写作智能体 - 负责内容创作和文案"""
    
    def __init__(self, agent_id: str = "writing_agent"):
        super().__init__(
            agent_id=agent_id,
            name="写作专家",
            description="擅长内容创作、文案撰写和文档整理"
        )
        
        self.add_capability(AgentCapability(
            name="content_writing",
            description="创作各类内容",
            parameters={"topic": "string", "style": "string", "length": "string"}
        ))
        
        self.add_capability(AgentCapability(
            name="document_editing",
            description="文档编辑和润色",
            parameters={"document": "string", "improvements": "array"}
        ))


# 全局实例
_orchestrator = None

def get_orchestrator() -> MultiAgentOrchestrator:
    """获取全局编排器实例"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = MultiAgentOrchestrator()
    return _orchestrator


def initialize_default_agents():
    """初始化默认智能体"""
    hub = A2AHub.get_instance()
    
    # 创建并注册默认智能体
    research_agent = ResearchAgent()
    hub.register_agent(research_agent)
    
    code_agent = CodeAgent()
    hub.register_agent(code_agent)
    
    writing_agent = WritingAgent()
    hub.register_agent(writing_agent)
    
    logger.info("默认智能体初始化完成")


if __name__ == "__main__":
    async def test_a2a():
        # 初始化
        initialize_default_agents()
        
        hub = A2AHub.get_instance()
        orchestrator = get_orchestrator()
        
        # 列出所有智能体
        print("已注册智能体:")
        for profile in hub.list_agents():
            print(f"  - {profile.name} ({profile.id})")
            for cap in profile.capabilities:
                print(f"      * {cap.name}: {cap.description}")
        
        # 测试消息发送
        research_agent = hub.get_agent("research_agent")
        code_agent = hub.get_agent("code_agent")
        
        # 从代码智能体发送任务请求给研究智能体
        task_id = await code_agent.request_task(
            target_agent_id="research_agent",
            task_description="Python异步编程最佳实践"
        )
        
        print(f"\n任务已创建: {task_id}")
        
        # 等待几秒让任务执行
        await asyncio.sleep(5)
        
        # 检查研究智能体的任务状态
        if task_id in research_agent.active_tasks:
            task = research_agent.active_tasks[task_id]
            print(f"任务状态: {task.status.value}")
    
    asyncio.run(test_a2a())
