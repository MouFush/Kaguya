#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辉夜AI - 企业级Agent编排系统 (Kaguya AI Agent Orchestration System)
整合: 多Agent协作 + 自主规划 + 工作流编排
参考: AutoGen + AutoGPT + Dify
"""

import asyncio
import json
import uuid
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Dict, List, Optional, Callable, Any, Set, AsyncGenerator, Union
from collections import defaultdict
import heapq
import copy

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# 第一部分: 核心类型定义与枚举
# ============================================================================

class AgentRole(Enum):
    """Agent角色类型"""
    COORDINATOR = "coordinator"      # 协调者
    PLANNER = "planner"              # 规划者
    EXECUTOR = "executor"            # 执行者
    CRITIC = "critic"                # 评估者
    SPECIALIST = "specialist"        # 专家
    USER_PROXY = "user_proxy"        # 用户代理


class MessageType(Enum):
    """消息类型"""
    CHAT = "chat"
    TASK = "task"
    RESULT = "result"
    PLAN = "plan"
    REFLECTION = "reflection"
    SYSTEM = "system"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class WorkflowNodeType(Enum):
    """工作流节点类型"""
    START = "start"
    END = "end"
    AGENT = "agent"
    CONDITION = "condition"
    LOOP = "loop"
    PARALLEL = "parallel"
    TOOL = "tool"
    DELAY = "delay"
    WEBHOOK = "webhook"


# ============================================================================
# 第二部分: 基础数据结构
# ============================================================================

@dataclass
class Message:
    """Agent间传递的消息"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender: str = ""
    receiver: Optional[str] = None  # None表示广播
    content: str = ""
    message_type: MessageType = MessageType.CHAT
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    parent_id: Optional[str] = None
    thread_id: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "sender": self.sender,
            "receiver": self.receiver,
            "content": self.content,
            "message_type": self.message_type.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "parent_id": self.parent_id,
            "thread_id": self.thread_id
        }


@dataclass
class Task:
    """任务定义"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 5  # 1-10
    assignee: Optional[str] = None
    creator: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    deadline: Optional[datetime] = None
    dependencies: List[str] = field(default_factory=list)
    subtasks: List[str] = field(default_factory=list)
    parent_id: Optional[str] = None
    result: Any = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['status'] = self.status.value
        for key in ['created_at', 'started_at', 'completed_at', 'deadline']:
            if data[key]:
                data[key] = data[key].isoformat() if isinstance(data[key], datetime) else data[key]
        return data


@dataclass
class Plan:
    """执行计划"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    goal: str = ""
    tasks: List[Task] = field(default_factory=list)
    current_task_index: int = 0
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    reflection_history: List[Dict] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def current_task(self) -> Optional[Task]:
        if 0 <= self.current_task_index < len(self.tasks):
            return self.tasks[self.current_task_index]
        return None
    
    @property
    def progress(self) -> float:
        if not self.tasks:
            return 0.0
        completed = sum(1 for t in self.tasks if t.status == TaskStatus.COMPLETED)
        return completed / len(self.tasks)


# ============================================================================
# 第三部分: Agent基类与核心实现
# ============================================================================

class BaseAgent(ABC):
    """
    Agent基类
    参考AutoGen设计，支持对话、工具调用、人机协作
    """
    
    def __init__(
        self,
        name: str,
        role: AgentRole,
        system_message: str = "",
        llm_config: Optional[Dict] = None,
        max_consecutive_auto_reply: int = 10,
        human_input_mode: str = "NEVER"  # NEVER, ALWAYS, TERMINATE
    ):
        self.name = name
        self.role = role
        self.system_message = system_message
        self.llm_config = llm_config or {}
        self.max_consecutive_auto_reply = max_consecutive_auto_reply
        self.human_input_mode = human_input_mode
        
        # 状态管理
        self.chat_history: List[Message] = []
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.subscribers: Set[str] = set()
        self.is_running = False
        self._reply_count = 0
        
        # 工具注册
        self.tools: Dict[str, Callable] = {}
        
        # 事件处理器
        self.event_handlers: Dict[str, List[Callable]] = defaultdict(list)
        
        logger.info(f"Agent '{name}' ({role.value}) 已初始化")
    
    def register_tool(self, name: str, func: Callable):
        """注册工具函数"""
        self.tools[name] = func
        logger.info(f"Agent '{self.name}' 注册工具: {name}")
    
    def on(self, event: str, handler: Callable):
        """注册事件处理器"""
        self.event_handlers[event].append(handler)
    
    async def emit(self, event: str, data: Any):
        """触发事件"""
        for handler in self.event_handlers.get(event, []):
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    handler(data)
            except Exception as e:
                logger.error(f"事件处理器错误: {e}")
    
    async def send_message(
        self,
        content: str,
        receiver: Optional[str] = None,
        message_type: MessageType = MessageType.CHAT,
        metadata: Optional[Dict] = None
    ) -> Message:
        """发送消息"""
        message = Message(
            sender=self.name,
            receiver=receiver,
            content=content,
            message_type=message_type,
            metadata=metadata or {}
        )
        await self.emit("message_sent", message)
        return message
    
    async def receive_message(self, message: Message):
        """接收消息"""
        self.chat_history.append(message)
        await self.message_queue.put(message)
        await self.emit("message_received", message)
    
    @abstractmethod
    async def think(self, message: Message) -> str:
        """思考并生成回复（子类必须实现）"""
        pass
    
    async def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """执行工具"""
        if tool_name not in self.tools:
            raise ValueError(f"未知工具: {tool_name}")
        
        tool = self.tools[tool_name]
        try:
            if asyncio.iscoroutinefunction(tool):
                result = await tool(**kwargs)
            else:
                result = tool(**kwargs)
            return result
        except Exception as e:
            logger.error(f"工具执行错误 {tool_name}: {e}")
            raise
    
    async def run(self):
        """主运行循环"""
        self.is_running = True
        logger.info(f"Agent '{self.name}' 开始运行")
        
        while self.is_running:
            try:
                message = await asyncio.wait_for(
                    self.message_queue.get(),
                    timeout=1.0
                )
                
                # 处理消息
                if message.receiver == self.name or message.receiver is None:
                    response = await self.think(message)
                    
                    if response:
                        await self.send_message(
                            content=response,
                            receiver=message.sender,
                            message_type=MessageType.CHAT
                        )
                        
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Agent '{self.name}' 运行错误: {e}")
    
    def stop(self):
        """停止Agent"""
        self.is_running = False
        logger.info(f"Agent '{self.name}' 已停止")


# ============================================================================
# 第四部分: 多Agent协作系统 (参考AutoGen)
# ============================================================================

class GroupChat:
    """
    群聊管理器
    支持多Agent群聊、发言顺序控制、话题管理
    """
    
    def __init__(
        self,
        name: str,
        agents: List[BaseAgent],
        max_round: int = 10,
        speaker_selection_mode: str = "auto"  # auto, round_robin, random, manual
    ):
        self.name = name
        self.agents = {agent.name: agent for agent in agents}
        self.max_round = max_round
        self.speaker_selection_mode = speaker_selection_mode
        
        self.messages: List[Message] = []
        self.current_round = 0
        self.current_speaker: Optional[str] = None
        self.is_active = False
        
        # 注册消息路由
        for agent in agents:
            agent.on("message_sent", self._route_message)
    
    async def _route_message(self, message: Message):
        """路由消息到所有参与者"""
        self.messages.append(message)
        
        # 广播给所有Agent（除了发送者）
        for name, agent in self.agents.items():
            if name != message.sender:
                await agent.receive_message(message)
    
    def select_next_speaker(self, last_message: Optional[Message] = None) -> Optional[str]:
        """选择下一个发言者"""
        if self.speaker_selection_mode == "round_robin":
            agent_names = list(self.agents.keys())
            if not self.current_speaker:
                return agent_names[0]
            current_idx = agent_names.index(self.current_speaker)
            next_idx = (current_idx + 1) % len(agent_names)
            return agent_names[next_idx]
        
        elif self.speaker_selection_mode == "auto" and last_message:
            # 智能选择：根据消息内容选择最合适的Agent
            return self._select_by_relevance(last_message)
        
        return None
    
    def _select_by_relevance(self, message: Message) -> Optional[str]:
        """基于消息相关性选择Agent（简化实现）"""
        # 实际实现可以使用LLM判断
        for name, agent in self.agents.items():
            if agent.role == AgentRole.COORDINATOR:
                return name
        return list(self.agents.keys())[0]
    
    async def start(self, initial_message: str, sender: str = "user"):
        """启动群聊"""
        self.is_active = True
        self.current_round = 0
        
        # 发送初始消息
        init_msg = Message(
            sender=sender,
            content=initial_message,
            message_type=MessageType.CHAT
        )
        await self._route_message(init_msg)
        
        logger.info(f"群聊 '{self.name}' 开始，初始消息: {initial_message[:50]}...")
        
        # 运行对话循环
        while self.is_active and self.current_round < self.max_round:
            speaker = self.select_next_speaker(
                self.messages[-1] if self.messages else None
            )
            
            if not speaker:
                break
            
            self.current_speaker = speaker
            self.current_round += 1
            
            # 等待Agent处理（实际实现中Agent会异步回复）
            await asyncio.sleep(0.5)
        
        self.is_active = False
        logger.info(f"群聊 '{self.name}' 结束")
    
    def stop(self):
        """停止群聊"""
        self.is_active = False


class NestedChat:
    """
    嵌套对话管理器
    支持子对话、对话恢复、上下文继承
    """
    
    def __init__(self, parent_chat: Optional['NestedChat'] = None):
        self.id = str(uuid.uuid4())
        self.parent = parent_chat
        self.children: List['NestedChat'] = []
        self.messages: List[Message] = []
        self.context: Dict[str, Any] = {}
        self.is_resolved = False
        self.result: Any = None
    
    async def create_sub_chat(self) -> 'NestedChat':
        """创建子对话"""
        sub_chat = NestedChat(parent_chat=self)
        self.children.append(sub_chat)
        return sub_chat
    
    def get_full_context(self) -> List[Message]:
        """获取完整上下文（包括父对话）"""
        context = []
        if self.parent:
            context.extend(self.parent.get_full_context())
        context.extend(self.messages)
        return context
    
    def resolve(self, result: Any):
        """解决当前对话"""
        self.is_resolved = True
        self.result = result


# ============================================================================
# 第五部分: 自主规划与执行框架 (参考AutoGPT)
# ============================================================================

class TaskPlanner:
    """
    任务规划器
    将目标分解为可执行的任务序列
    """
    
    def __init__(self, llm_adapter: Optional[Any] = None):
        self.llm_adapter = llm_adapter
        self.planning_strategies = {
            "sequential": self._sequential_plan,
            "parallel": self._parallel_plan,
            "hierarchical": self._hierarchical_plan
        }
    
    async def create_plan(
        self,
        goal: str,
        strategy: str = "sequential",
        context: Optional[Dict] = None
    ) -> Plan:
        """创建执行计划"""
        planner = self.planning_strategies.get(strategy, self._sequential_plan)
        return await planner(goal, context)
    
    async def _sequential_plan(self, goal: str, context: Optional[Dict]) -> Plan:
        """顺序规划策略"""
        # 使用LLM分解任务
        tasks = await self._decompose_with_llm(goal)
        
        # 建立依赖关系
        for i in range(1, len(tasks)):
            tasks[i].dependencies.append(tasks[i-1].id)
        
        return Plan(goal=goal, tasks=tasks)
    
    async def _parallel_plan(self, goal: str, context: Optional[Dict]) -> Plan:
        """并行规划策略"""
        tasks = await self._decompose_with_llm(goal)
        # 并行任务无依赖
        return Plan(goal=goal, tasks=tasks)
    
    async def _hierarchical_plan(self, goal: str, context: Optional[Dict]) -> Plan:
        """分层规划策略"""
        # 先分解主要阶段
        phases = await self._decompose_with_llm(goal, depth=1)
        
        all_tasks = []
        for phase in phases:
            # 每个阶段再细分
            subtasks = await self._decompose_with_llm(phase.description)
            for subtask in subtasks:
                subtask.parent_id = phase.id
            phase.subtasks = [t.id for t in subtasks]
            all_tasks.extend([phase] + subtasks)
        
        return Plan(goal=goal, tasks=all_tasks)
    
    async def _decompose_with_llm(
        self,
        goal: str,
        depth: int = 2
    ) -> List[Task]:
        """使用LLM分解任务"""
        # 这里简化实现，实际应调用LLM
        tasks = []
        
        # 模拟任务分解
        steps = [
            f"分析需求: {goal[:30]}...",
            f"设计方案",
            f"实现功能",
            f"测试验证",
            f"部署上线"
        ]
        
        for i, step in enumerate(steps[:depth+2]):
            task = Task(
                name=f"任务{i+1}",
                description=step,
                priority=5
            )
            tasks.append(task)
        
        return tasks
    
    async def optimize_plan(self, plan: Plan, reflection: str) -> Plan:
        """基于反思优化计划"""
        # 分析反思内容，调整任务
        plan.reflection_history.append({
            "timestamp": datetime.now().isoformat(),
            "reflection": reflection
        })
        plan.updated_at = datetime.now()
        return plan


class TaskExecutor:
    """
    任务执行器
    负责任务调度、执行、监控
    """
    
    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.task_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self.results: Dict[str, Any] = {}
        self.is_running = False
    
    async def submit_task(
        self,
        task: Task,
        executor_func: Callable,
        **kwargs
    ) -> str:
        """提交任务"""
        # 检查依赖
        for dep_id in task.dependencies:
            if dep_id not in self.results:
                task.status = TaskStatus.BLOCKED
                return task.id
        
        # 加入优先级队列
        await self.task_queue.put((-task.priority, task.id, task, executor_func, kwargs))
        task.status = TaskStatus.PENDING
        
        return task.id
    
    async def run(self):
        """执行循环"""
        self.is_running = True
        
        while self.is_running:
            try:
                # 获取任务
                priority, task_id, task, func, kwargs = await asyncio.wait_for(
                    self.task_queue.get(),
                    timeout=1.0
                )
                
                # 检查依赖是否完成
                deps_satisfied = all(
                    dep_id in self.results and 
                    not isinstance(self.results[dep_id], Exception)
                    for dep_id in task.dependencies
                )
                
                if not deps_satisfied:
                    # 重新入队
                    await self.task_queue.put((priority, task_id, task, func, kwargs))
                    await asyncio.sleep(0.5)
                    continue
                
                # 执行任务
                task.status = TaskStatus.IN_PROGRESS
                task.started_at = datetime.now()
                
                try:
                    if asyncio.iscoroutinefunction(func):
                        result = await func(task, **kwargs)
                    else:
                        result = func(task, **kwargs)
                    
                    task.status = TaskStatus.COMPLETED
                    task.result = result
                    self.results[task_id] = result
                    
                except Exception as e:
                    task.status = TaskStatus.FAILED
                    task.error_message = str(e)
                    self.results[task_id] = e
                    logger.error(f"任务执行失败 {task_id}: {e}")
                
                task.completed_at = datetime.now()
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"执行器错误: {e}")
    
    def stop(self):
        """停止执行器"""
        self.is_running = False
        for task in self.active_tasks.values():
            task.cancel()


class ReflectionEngine:
    """
    反思引擎
    评估执行结果，提供改进建议
    """
    
    def __init__(self, llm_adapter: Optional[Any] = None):
        self.llm_adapter = llm_adapter
        self.reflection_history: List[Dict] = []
    
    async def reflect(
        self,
        task: Task,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """对任务执行进行反思"""
        reflection = {
            "task_id": task.id,
            "task_name": task.name,
            "success": task.status == TaskStatus.COMPLETED,
            "timestamp": datetime.now().isoformat(),
            "analysis": "",
            "suggestions": [],
            "lessons_learned": []
        }
        
        if task.status == TaskStatus.COMPLETED:
            reflection["analysis"] = f"任务 '{task.name}' 成功完成"
            reflection["suggestions"] = ["继续保持", "考虑优化执行效率"]
        else:
            reflection["analysis"] = f"任务 '{task.name}' 失败: {task.error_message}"
            reflection["suggestions"] = [
                "检查错误日志",
                "分解为更小的子任务",
                "调整执行策略"
            ]
        
        self.reflection_history.append(reflection)
        return reflection
    
    async def self_improve(self) -> List[str]:
        """基于历史反思自我改进"""
        if not self.reflection_history:
            return []
        
        # 分析失败模式
        failures = [r for r in self.reflection_history if not r["success"]]
        
        improvements = []
        if len(failures) > len(self.reflection_history) * 0.3:
            improvements.append("需要改进任务分解策略")
        
        return improvements


class AutonomousAgent(BaseAgent):
    """
    自主Agent
    结合规划、执行、反思的完整自主系统
    """
    
    def __init__(
        self,
        name: str,
        system_message: str = "",
        llm_config: Optional[Dict] = None
    ):
        super().__init__(name, AgentRole.PLANNER, system_message, llm_config)
        
        self.planner = TaskPlanner()
        self.executor = TaskExecutor()
        self.reflection = ReflectionEngine()
        
        self.plans: Dict[str, Plan] = {}
        self.current_plan: Optional[Plan] = None
    
    async def think(self, message: Message) -> str:
        """思考并决策"""
        content = message.content.lower()
        
        # 识别意图
        if any(kw in content for kw in ["计划", "规划", "目标"]):
            return await self._handle_planning(message)
        
        elif any(kw in content for kw in ["执行", "运行", "开始"]):
            return await self._handle_execution(message)
        
        elif any(kw in content for kw in ["反思", "总结", "评估"]):
            return await self._handle_reflection(message)
        
        else:
            return f"我是自主Agent '{self.name}'，可以帮助您规划任务、执行计划和反思改进。"
    
    async def _handle_planning(self, message: Message) -> str:
        """处理规划请求"""
        # 提取目标
        goal = message.content
        
        # 创建计划
        plan = await self.planner.create_plan(goal, strategy="hierarchical")
        self.plans[plan.id] = plan
        self.current_plan = plan
        
        task_summary = "\n".join([
            f"  {i+1}. {task.name}: {task.description}"
            for i, task in enumerate(plan.tasks[:5])
        ])
        
        return f"已为目标创建计划:\n{goal[:50]}...\n\n任务列表:\n{task_summary}\n\n计划ID: {plan.id}"
    
    async def _handle_execution(self, message: Message) -> str:
        """处理执行请求"""
        if not self.current_plan:
            return "请先创建计划"
        
        # 启动执行器
        executor_task = asyncio.create_task(self.executor.run())
        
        # 提交所有任务
        for task in self.current_plan.tasks:
            await self.executor.submit_task(
                task,
                self._execute_task,
                plan_id=self.current_plan.id
            )
        
        # 等待完成
        await asyncio.sleep(2)  # 简化实现
        self.executor.stop()
        
        completed = sum(1 for t in self.current_plan.tasks if t.status == TaskStatus.COMPLETED)
        return f"计划执行完成: {completed}/{len(self.current_plan.tasks)} 个任务成功"
    
    async def _handle_reflection(self, message: Message) -> str:
        """处理反思请求"""
        if not self.current_plan:
            return "没有可反思的计划"
        
        reflections = []
        for task in self.current_plan.tasks:
            if task.status != TaskStatus.PENDING:
                ref = await self.reflection.reflect(task, {})
                reflections.append(ref)
        
        insights = await self.reflection.self_improve()
        
        return f"反思完成:\n- 分析了 {len(reflections)} 个任务\n- 改进建议: {', '.join(insights) if insights else '暂无'}"
    
    async def _execute_task(self, task: Task, plan_id: str) -> str:
        """执行单个任务"""
        await asyncio.sleep(0.5)  # 模拟执行
        return f"任务 '{task.name}' 执行结果"


# ============================================================================
# 第六部分: 工作流编排系统 (参考Dify/n8n)
# ============================================================================

@dataclass
class WorkflowNode:
    """工作流节点"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    node_type: WorkflowNodeType = WorkflowNodeType.AGENT
    config: Dict[str, Any] = field(default_factory=dict)
    position: Dict[str, float] = field(default_factory=lambda: {"x": 0, "y": 0})
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    next_nodes: List[str] = field(default_factory=list)
    prev_nodes: List[str] = field(default_factory=list)
    condition: Optional[str] = None  # 条件表达式
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行节点逻辑"""
        logger.info(f"执行节点: {self.name} ({self.node_type.value})")
        
        result = {"status": "success", "data": {}}
        
        if self.node_type == WorkflowNodeType.AGENT:
            result = await self._execute_agent(context)
        elif self.node_type == WorkflowNodeType.TOOL:
            result = await self._execute_tool(context)
        elif self.node_type == WorkflowNodeType.CONDITION:
            result = await self._execute_condition(context)
        elif self.node_type == WorkflowNodeType.LOOP:
            result = await self._execute_loop(context)
        elif self.node_type == WorkflowNodeType.PARALLEL:
            result = await self._execute_parallel(context)
        
        return result
    
    async def _execute_agent(self, context: Dict) -> Dict:
        """执行Agent节点"""
        agent_name = self.config.get("agent_name")
        message = self.config.get("message", "")
        # 实际实现中调用Agent
        return {"status": "success", "data": {"agent": agent_name, "response": f"Agent {agent_name} 回复"}}
    
    async def _execute_tool(self, context: Dict) -> Dict:
        """执行工具节点"""
        tool_name = self.config.get("tool_name")
        params = self.config.get("params", {})
        return {"status": "success", "data": {"tool": tool_name, "result": f"工具 {tool_name} 执行结果"}}
    
    async def _execute_condition(self, context: Dict) -> Dict:
        """执行条件节点"""
        condition = self.config.get("condition", "true")
        # 简化条件判断
        result = eval(condition, {"context": context, **context})
        return {"status": "success", "data": {"condition_result": bool(result)}}
    
    async def _execute_loop(self, context: Dict) -> Dict:
        """执行循环节点"""
        iterations = self.config.get("iterations", 1)
        results = []
        for i in range(iterations):
            results.append(f"迭代 {i+1}")
        return {"status": "success", "data": {"iterations": results}}
    
    async def _execute_parallel(self, context: Dict) -> Dict:
        """执行并行节点"""
        branches = self.config.get("branches", [])
        # 并行执行分支
        results = await asyncio.gather(*[
            self._simulate_branch(branch) for branch in branches
        ])
        return {"status": "success", "data": {"branches": results}}
    
    async def _simulate_branch(self, branch: Dict) -> Dict:
        """模拟分支执行"""
        await asyncio.sleep(0.1)
        return {"branch": branch.get("name"), "result": "完成"}


class Workflow:
    """
    工作流定义
    """
    
    def __init__(
        self,
        name: str,
        description: str = ""
    ):
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.nodes: Dict[str, WorkflowNode] = {}
        self.start_node: Optional[str] = None
        self.variables: Dict[str, Any] = {}
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    def add_node(self, node: WorkflowNode) -> str:
        """添加节点"""
        self.nodes[node.id] = node
        if node.node_type == WorkflowNodeType.START:
            self.start_node = node.id
        self.updated_at = datetime.now()
        return node.id
    
    def connect_nodes(self, from_id: str, to_id: str, condition: Optional[str] = None):
        """连接节点"""
        if from_id in self.nodes and to_id in self.nodes:
            self.nodes[from_id].next_nodes.append(to_id)
            self.nodes[to_id].prev_nodes.append(from_id)
            if condition:
                self.nodes[from_id].condition = condition
    
    def to_dict(self) -> Dict:
        """序列化为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "nodes": {nid: {
                "id": n.id,
                "name": n.name,
                "type": n.node_type.value,
                "config": n.config,
                "position": n.position,
                "next": n.next_nodes,
                "condition": n.condition
            } for nid, n in self.nodes.items()},
            "start_node": self.start_node,
            "variables": self.variables
        }


class WorkflowEngine:
    """
    工作流执行引擎
    """
    
    def __init__(self):
        self.workflows: Dict[str, Workflow] = {}
        self.executions: Dict[str, Dict] = {}
        self.is_running = False
    
    def register_workflow(self, workflow: Workflow):
        """注册工作流"""
        self.workflows[workflow.id] = workflow
        logger.info(f"工作流 '{workflow.name}' 已注册")
    
    async def execute(
        self,
        workflow_id: str,
        initial_context: Optional[Dict] = None
    ) -> str:
        """执行工作流"""
        if workflow_id not in self.workflows:
            raise ValueError(f"未知工作流: {workflow_id}")
        
        workflow = self.workflows[workflow_id]
        execution_id = str(uuid.uuid4())
        
        context = initial_context or {}
        execution_path = []
        
        logger.info(f"开始执行工作流 '{workflow.name}' (执行ID: {execution_id})")
        
        # 从起始节点开始
        current_node_id = workflow.start_node
        visited = set()
        
        while current_node_id and current_node_id not in visited:
            visited.add(current_node_id)
            node = workflow.nodes.get(current_node_id)
            
            if not node:
                break
            
            try:
                # 执行节点
                result = await node.execute(context)
                execution_path.append({
                    "node": node.name,
                    "result": result
                })
                
                # 更新上下文
                context[f"{node.name}_output"] = result.get("data", {})
                
                # 确定下一个节点
                if node.node_type == WorkflowNodeType.END:
                    break
                
                if node.node_type == WorkflowNodeType.CONDITION and result["data"].get("condition_result"):
                    # 条件为真，走第一个分支
                    current_node_id = node.next_nodes[0] if node.next_nodes else None
                elif node.node_type == WorkflowNodeType.CONDITION:
                    # 条件为假，走第二个分支
                    current_node_id = node.next_nodes[1] if len(node.next_nodes) > 1 else None
                else:
                    current_node_id = node.next_nodes[0] if node.next_nodes else None
                
            except Exception as e:
                logger.error(f"节点执行错误 {node.name}: {e}")
                execution_path.append({
                    "node": node.name,
                    "error": str(e)
                })
                break
        
        # 保存执行记录
        self.executions[execution_id] = {
            "workflow_id": workflow_id,
            "workflow_name": workflow.name,
            "context": context,
            "path": execution_path,
            "completed_at": datetime.now().isoformat()
        }
        
        logger.info(f"工作流执行完成 (执行ID: {execution_id})")
        return execution_id
    
    def get_execution(self, execution_id: str) -> Optional[Dict]:
        """获取执行记录"""
        return self.executions.get(execution_id)


# ============================================================================
# 第七部分: 统一编排管理器
# ============================================================================

class AgentOrchestrator:
    """
    Agent编排管理器
    统一管理多Agent协作、自主规划、工作流编排
    """
    
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self.group_chats: Dict[str, GroupChat] = {}
        self.workflows: Dict[str, Workflow] = {}
        self.workflow_engine = WorkflowEngine()
        
        # 事件总线
        self.event_bus: asyncio.Queue = asyncio.Queue()
        self.event_handlers: Dict[str, List[Callable]] = defaultdict(list)
        
        self.is_running = False
    
    def register_agent(self, agent: BaseAgent):
        """注册Agent"""
        self.agents[agent.name] = agent
        logger.info(f"Agent '{agent.name}' 已注册到编排器")
    
    def create_group_chat(
        self,
        name: str,
        agent_names: List[str],
        **kwargs
    ) -> GroupChat:
        """创建群聊"""
        agents = [self.agents[name] for name in agent_names if name in self.agents]
        chat = GroupChat(name, agents, **kwargs)
        self.group_chats[name] = chat
        return chat
    
    def create_workflow(self, name: str, description: str = "") -> Workflow:
        """创建工作流"""
        workflow = Workflow(name, description)
        self.workflows[name] = workflow
        self.workflow_engine.register_workflow(workflow)
        return workflow
    
    async def run_agent(self, agent_name: str):
        """运行单个Agent"""
        if agent_name in self.agents:
            await self.agents[agent_name].run()
    
    async def run_all(self):
        """运行所有Agent"""
        self.is_running = True
        
        # 启动所有Agent
        tasks = [
            asyncio.create_task(agent.run())
            for agent in self.agents.values()
        ]
        
        logger.info(f"编排器启动，运行 {len(tasks)} 个Agent")
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    def stop_all(self):
        """停止所有Agent"""
        self.is_running = False
        for agent in self.agents.values():
            agent.stop()
        logger.info("编排器已停止所有Agent")
    
    async def create_autonomous_workflow(
        self,
        goal: str,
        agent_configs: List[Dict]
    ) -> str:
        """
        创建自主工作流
        结合自主规划和多Agent协作
        """
        # 1. 创建规划Agent
        planner = AutonomousAgent(
            name="workflow_planner",
            system_message="你是一个工作流规划专家"
        )
        self.register_agent(planner)
        
        # 2. 创建专业Agent
        for config in agent_configs:
            agent = BaseAgent(
                name=config["name"],
                role=AgentRole[config.get("role", "SPECIALIST")],
                system_message=config.get("system_message", "")
            )
            self.register_agent(agent)
        
        # 3. 创建规划
        plan_message = Message(
            sender="user",
            content=f"请为以下目标创建执行计划: {goal}",
            message_type=MessageType.PLAN
        )
        await planner.receive_message(plan_message)
        
        # 4. 创建工作流
        workflow = self.create_workflow(
            name=f"autonomous_workflow_{uuid.uuid4().hex[:8]}",
            description=goal
        )
        
        # 添加节点
        start_node = WorkflowNode(
            name="开始",
            node_type=WorkflowNodeType.START
        )
        workflow.add_node(start_node)
        
        # 为每个任务创建Agent节点
        if planner.current_plan:
            prev_node_id = start_node.id
            for task in planner.current_plan.tasks:
                agent_node = WorkflowNode(
                    name=task.name,
                    node_type=WorkflowNodeType.AGENT,
                    config={
                        "agent_name": task.assignee or "workflow_planner",
                        "message": task.description
                    }
                )
                workflow.add_node(agent_node)
                workflow.connect_nodes(prev_node_id, agent_node.id)
                prev_node_id = agent_node.id
            
            # 添加结束节点
            end_node = WorkflowNode(
                name="结束",
                node_type=WorkflowNodeType.END
            )
            workflow.add_node(end_node)
            workflow.connect_nodes(prev_node_id, end_node.id)
        
        return workflow.id
    
    def get_system_status(self) -> Dict:
        """获取系统状态"""
        return {
            "agents": {
                name: {
                    "role": agent.role.value,
                    "is_running": agent.is_running,
                    "chat_history_count": len(agent.chat_history)
                }
                for name, agent in self.agents.items()
            },
            "group_chats": {
                name: {
                    "agent_count": len(chat.agents),
                    "is_active": chat.is_active,
                    "current_round": chat.current_round
                }
                for name, chat in self.group_chats.items()
            },
            "workflows": {
                name: {
                    "node_count": len(workflow.nodes),
                    "created_at": workflow.created_at.isoformat()
                }
                for name, workflow in self.workflows.items()
            },
            "executions": len(self.workflow_engine.executions)
        }


# ============================================================================
# 第八部分: 具体Agent实现与使用示例
# ============================================================================

class SimpleAgent(BaseAgent):
    """简单Agent实现，用于演示"""
    
    async def think(self, message: Message) -> str:
        """简单思考逻辑"""
        responses = {
            AgentRole.SPECIALIST: f"[{self.name}] 收到，我正在分析: {message.content[:30]}...",
            AgentRole.EXECUTOR: f"[{self.name}] 开始执行: {message.content[:30]}...",
            AgentRole.COORDINATOR: f"[{self.name}] 协调处理: {message.content[:30]}...",
            AgentRole.CRITIC: f"[{self.name}] 评估中: {message.content[:30]}...",
        }
        return responses.get(self.role, f"[{self.name}] 处理中...")


async def demo_multi_agent_collaboration():
    """演示多Agent协作"""
    print("\n" + "="*60)
    print("演示: 多Agent协作系统")
    print("="*60)
    
    orchestrator = AgentOrchestrator()
    
    # 创建专业Agent（使用SimpleAgent）
    product_manager = SimpleAgent(
        name="产品经理",
        role=AgentRole.SPECIALIST,
        system_message="你是产品经理，负责需求分析和功能设计"
    )
    
    architect = SimpleAgent(
        name="架构师",
        role=AgentRole.SPECIALIST,
        system_message="你是系统架构师，负责技术方案设计"
    )
    
    developer = SimpleAgent(
        name="开发工程师",
        role=AgentRole.EXECUTOR,
        system_message="你是开发工程师，负责代码实现"
    )
    
    # 注册Agent
    for agent in [product_manager, architect, developer]:
        orchestrator.register_agent(agent)
    
    # 创建群聊
    chat = orchestrator.create_group_chat(
        name="软件开发团队",
        agent_names=["产品经理", "架构师", "开发工程师"],
        max_round=5,
        speaker_selection_mode="round_robin"
    )
    
    print(f"\n创建群聊: {chat.name}")
    print(f"参与者: {list(chat.agents.keys())}")
    
    # 模拟启动群聊
    await chat.start("我们需要开发一个用户认证系统")
    
    return orchestrator


async def demo_autonomous_planning():
    """演示自主规划"""
    print("\n" + "="*60)
    print("演示: 自主规划与执行框架")
    print("="*60)
    
    # 创建自主Agent
    agent = AutonomousAgent(
        name="自主规划Agent",
        system_message="你是一个能够自主规划、执行和反思的AI助手"
    )
    
    # 模拟规划请求
    plan_message = Message(
        sender="user",
        content="我计划开发一个电商平台，包含用户系统、商品管理、订单处理、支付集成",
        message_type=MessageType.PLAN
    )
    
    response = await agent.think(plan_message)
    print(f"\n规划结果:\n{response}")
    
    # 模拟执行请求
    exec_message = Message(
        sender="user",
        content="开始执行计划",
        message_type=MessageType.TASK
    )
    
    response = await agent.think(exec_message)
    print(f"\n执行结果:\n{response}")
    
    # 模拟反思请求
    reflect_message = Message(
        sender="user",
        content="请反思执行过程",
        message_type=MessageType.REFLECTION
    )
    
    response = await agent.think(reflect_message)
    print(f"\n反思结果:\n{response}")
    
    return agent


async def demo_workflow_orchestration():
    """演示工作流编排"""
    print("\n" + "="*60)
    print("演示: 工作流编排系统")
    print("="*60)
    
    orchestrator = AgentOrchestrator()
    
    # 创建客服处理工作流
    workflow = orchestrator.create_workflow(
        name="智能客服处理流程",
        description="处理客户咨询的完整流程"
    )
    
    # 添加节点
    start = WorkflowNode(name="接收咨询", node_type=WorkflowNodeType.START)
    classify = WorkflowNode(
        name="问题分类",
        node_type=WorkflowNodeType.AGENT,
        config={"agent_name": "classifier", "message": "分类客户问题"}
    )
    condition = WorkflowNode(
        name="判断类型",
        node_type=WorkflowNodeType.CONDITION,
        config={"condition": "context.get('type') == 'technical'"}
    )
    technical = WorkflowNode(
        name="技术支持",
        node_type=WorkflowNodeType.AGENT,
        config={"agent_name": "tech_support", "message": "处理技术问题"}
    )
    sales = WorkflowNode(
        name="销售支持",
        node_type=WorkflowNodeType.AGENT,
        config={"agent_name": "sales", "message": "处理销售问题"}
    )
    followup = WorkflowNode(
        name="满意度回访",
        node_type=WorkflowNodeType.TOOL,
        config={"tool_name": "send_survey"}
    )
    end = WorkflowNode(name="结束", node_type=WorkflowNodeType.END)
    
    # 添加并连接节点
    nodes = [start, classify, condition, technical, sales, followup, end]
    for node in nodes:
        workflow.add_node(node)
    
    workflow.connect_nodes(start.id, classify.id)
    workflow.connect_nodes(classify.id, condition.id)
    workflow.connect_nodes(condition.id, technical.id)  # True分支
    workflow.connect_nodes(condition.id, sales.id)      # False分支
    workflow.connect_nodes(technical.id, followup.id)
    workflow.connect_nodes(sales.id, followup.id)
    workflow.connect_nodes(followup.id, end.id)
    
    print(f"\n工作流 '{workflow.name}' 创建完成")
    print(f"节点数量: {len(workflow.nodes)}")
    print(f"节点列表: {[n.name for n in workflow.nodes.values()]}")
    
    # 执行工作流
    execution_id = await orchestrator.workflow_engine.execute(
        workflow.id,
        initial_context={"customer_id": "C12345", "type": "technical"}
    )
    
    print(f"\n工作流执行完成，执行ID: {execution_id}")
    
    execution = orchestrator.workflow_engine.get_execution(execution_id)
    if execution:
        print(f"执行路径: {[step['node'] for step in execution['path']]}")
    
    return orchestrator


async def main():
    """主函数"""
    print("\n" + "="*60)
    print("辉夜AI - 企业级Agent编排系统")
    print("="*60)
    
    # 演示1: 多Agent协作
    await demo_multi_agent_collaboration()
    
    # 演示2: 自主规划
    await demo_autonomous_planning()
    
    # 演示3: 工作流编排
    await demo_workflow_orchestration()
    
    print("\n" + "="*60)
    print("所有演示完成!")
    print("="*60)


if __name__ == "__main__":
    # 运行演示
    asyncio.run(main())
