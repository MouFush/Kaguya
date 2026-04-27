#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agentic Workflow Engine - LangGraph风格的工作流引擎
Phase 1 核心组件 - 辉夜AI平台增强功能

核心特性:
- 状态图构建 (StateGraph)
- 节点编排与条件分支
- 检查点与恢复机制
- 人机协同 (Human-in-the-loop)
- 分布式执行支持

参考: LangGraph, CrewAI, AutoGen
"""

import asyncio
import json
import uuid
import logging
from typing import Dict, List, Any, Optional, Callable, Union, AsyncIterator, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum, auto
from abc import ABC, abstractmethod
from collections import deque
import copy
import hashlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ==================== 核心类型定义 ====================

class NodeType(Enum):
    """节点类型"""
    START = "start"
    END = "end"
    AGENT = "agent"
    TOOL = "tool"
    CONDITION = "condition"
    HUMAN = "human"
    PARALLEL = "parallel"
    MAP_REDUCE = "map_reduce"
    SUBGRAPH = "subgraph"
    WAIT = "wait"


class EdgeType(Enum):
    """边类型"""
    DEFAULT = "default"
    CONDITIONAL = "conditional"
    PARALLEL = "parallel"
    ERROR = "error"
    TIMEOUT = "timeout"


class WorkflowStatus(Enum):
    """工作流状态"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"  # 等待人工输入
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class CheckpointStrategy(Enum):
    """检查点策略"""
    EVERY_NODE = "every_node"
    EVERY_STEP = "every_step"
    ON_ERROR = "on_error"
    MANUAL = "manual"


@dataclass
class WorkflowState:
    """工作流状态 - 可在节点间传递"""
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)
    checkpoint_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取状态数据"""
        return self.data.get(key, default)
    
    def set(self, key: str, value: Any):
        """设置状态数据"""
        self.data[key] = value
        self.updated_at = datetime.now()
    
    def update(self, updates: Dict[str, Any]):
        """批量更新状态"""
        self.data.update(updates)
        self.updated_at = datetime.now()
    
    def copy(self) -> 'WorkflowState':
        """创建状态副本"""
        return WorkflowState(
            data=copy.deepcopy(self.data),
            metadata=copy.deepcopy(self.metadata),
            history=copy.deepcopy(self.history),
            checkpoint_id=self.checkpoint_id,
            created_at=self.created_at,
            updated_at=self.updated_at
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "data": self.data,
            "metadata": self.metadata,
            "history": self.history,
            "checkpoint_id": self.checkpoint_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


@dataclass
class NodeResult:
    """节点执行结果"""
    node_id: str
    state: WorkflowState
    output: Any = None
    status: str = "success"  # success, error, paused, skipped
    error_message: Optional[str] = None
    execution_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "output": self.output,
            "status": self.status,
            "error_message": self.error_message,
            "execution_time_ms": self.execution_time_ms,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class Checkpoint:
    """检查点 - 用于恢复工作流"""
    id: str
    workflow_id: str
    node_id: str
    state: WorkflowState
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "workflow_id": self.workflow_id,
            "node_id": self.node_id,
            "state": self.state.to_dict(),
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata
        }


# ==================== 节点定义 ====================

class WorkflowNode(ABC):
    """工作流节点基类"""
    
    def __init__(self, node_id: str, node_type: NodeType, 
                 name: str = None, description: str = None):
        self.node_id = node_id
        self.node_type = node_type
        self.name = name or node_id
        self.description = description or ""
        self.config: Dict[str, Any] = {}
        self.retry_count: int = 0
        self.max_retries: int = 3
        self.timeout: Optional[float] = None
        
    @abstractmethod
    async def execute(self, state: WorkflowState, 
                     context: Dict[str, Any] = None) -> NodeResult:
        """执行节点逻辑"""
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "name": self.name,
            "description": self.description,
            "config": self.config,
            "max_retries": self.max_retries,
            "timeout": self.timeout
        }


class AgentNode(WorkflowNode):
    """AI Agent节点"""
    
    def __init__(self, node_id: str, agent_func: Callable = None,
                 name: str = None, description: str = None,
                 llm_client = None):
        super().__init__(node_id, NodeType.AGENT, name, description)
        self.agent_func = agent_func
        self.llm_client = llm_client
        self.system_prompt: Optional[str] = None
        self.tools: List[str] = []
        
    async def execute(self, state: WorkflowState, 
                     context: Dict[str, Any] = None) -> NodeResult:
        """执行Agent逻辑"""
        start_time = datetime.now()
        
        try:
            # 构建输入
            input_data = state.get("input", "")
            history = state.get("history", [])
            
            # 调用Agent函数或LLM
            if self.agent_func:
                if asyncio.iscoroutinefunction(self.agent_func):
                    result = await self.agent_func(input_data, state, context)
                else:
                    result = self.agent_func(input_data, state, context)
            elif self.llm_client:
                result = await self._call_llm(input_data, history)
            else:
                result = {"response": f"Agent {self.name} 执行完成", "actions": []}
            
            # 更新状态
            state.set(f"{self.node_id}_output", result)
            state.history.append({
                "node_id": self.node_id,
                "role": "agent",
                "content": result.get("response", str(result)),
                "timestamp": datetime.now().isoformat()
            })
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return NodeResult(
                node_id=self.node_id,
                state=state,
                output=result,
                status="success",
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            logger.error(f"Agent节点 {self.node_id} 执行失败: {e}")
            return NodeResult(
                node_id=self.node_id,
                state=state,
                status="error",
                error_message=str(e),
                execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000
            )
    
    async def _call_llm(self, input_data: str, history: List[Dict]) -> Dict[str, Any]:
        """调用LLM"""
        # 这里集成实际的LLM调用
        return {
            "response": f"LLM响应: {input_data}",
            "actions": []
        }


class ToolNode(WorkflowNode):
    """工具调用节点"""
    
    def __init__(self, node_id: str, tool_func: Callable,
                 name: str = None, description: str = None):
        super().__init__(node_id, NodeType.TOOL, name, description)
        self.tool_func = tool_func
        self.parameters: Dict[str, Any] = {}
        
    async def execute(self, state: WorkflowState,
                     context: Dict[str, Any] = None) -> NodeResult:
        """执行工具"""
        start_time = datetime.now()
        
        try:
            # 获取工具参数
            params = self._extract_parameters(state)
            
            # 调用工具
            if asyncio.iscoroutinefunction(self.tool_func):
                result = await self.tool_func(**params)
            else:
                result = self.tool_func(**params)
            
            # 更新状态
            state.set(f"{self.node_id}_output", result)
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return NodeResult(
                node_id=self.node_id,
                state=state,
                output=result,
                status="success",
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            logger.error(f"工具节点 {self.node_id} 执行失败: {e}")
            return NodeResult(
                node_id=self.node_id,
                state=state,
                status="error",
                error_message=str(e),
                execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000
            )
    
    def _extract_parameters(self, state: WorkflowState) -> Dict[str, Any]:
        """从状态中提取参数"""
        params = {}
        for key, config in self.parameters.items():
            source = config.get("source", "state")
            if source == "state":
                params[key] = state.get(config.get("key", key))
            elif source == "static":
                params[key] = config.get("value")
            elif source == "context":
                params[key] = config.get("value")
        return params


class ConditionNode(WorkflowNode):
    """条件判断节点"""
    
    def __init__(self, node_id: str, condition_func: Callable,
                 name: str = None, description: str = None):
        super().__init__(node_id, NodeType.CONDITION, name, description)
        self.condition_func = condition_func
        self.branches: Dict[str, str] = {}  # condition -> next_node_id
        
    async def execute(self, state: WorkflowState,
                     context: Dict[str, Any] = None) -> NodeResult:
        """执行条件判断"""
        start_time = datetime.now()
        
        try:
            # 评估条件
            if asyncio.iscoroutinefunction(self.condition_func):
                condition_result = await self.condition_func(state, context)
            else:
                condition_result = self.condition_func(state, context)
            
            # 确定分支
            branch = condition_result if isinstance(condition_result, str) else "default"
            
            state.set(f"{self.node_id}_branch", branch)
            state.set(f"{self.node_id}_condition_result", condition_result)
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return NodeResult(
                node_id=self.node_id,
                state=state,
                output={"branch": branch, "condition": condition_result},
                status="success",
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            logger.error(f"条件节点 {self.node_id} 执行失败: {e}")
            return NodeResult(
                node_id=self.node_id,
                state=state,
                status="error",
                error_message=str(e),
                execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000
            )


class HumanNode(WorkflowNode):
    """人工介入节点 - Human-in-the-loop"""
    
    def __init__(self, node_id: str, prompt_template: str = None,
                 name: str = None, description: str = None):
        super().__init__(node_id, NodeType.HUMAN, name, description)
        self.prompt_template = prompt_template or "请审核并提供反馈:"
        self.timeout: Optional[float] = 3600  # 默认1小时超时
        
    async def execute(self, state: WorkflowState,
                     context: Dict[str, Any] = None) -> NodeResult:
        """触发人工介入"""
        # 生成提示
        prompt = self._generate_prompt(state)
        
        # 标记状态为等待人工输入
        state.set(f"{self.node_id}_waiting", True)
        state.set(f"{self.node_id}_prompt", prompt)
        state.set(f"{self.node_id}_submitted_at", datetime.now().isoformat())
        
        # 返回暂停状态
        return NodeResult(
            node_id=self.node_id,
            state=state,
            output={"prompt": prompt, "status": "waiting_for_human"},
            status="paused"
        )
    
    def _generate_prompt(self, state: WorkflowState) -> str:
        """生成提示"""
        return self.prompt_template.format(
            state=state.to_dict()
        )
    
    def submit_human_input(self, state: WorkflowState, input_data: Any) -> WorkflowState:
        """提交人工输入"""
        state.set(f"{self.node_id}_input", input_data)
        state.set(f"{self.node_id}_waiting", False)
        state.set(f"{self.node_id}_completed_at", datetime.now().isoformat())
        return state


class ParallelNode(WorkflowNode):
    """并行执行节点"""
    
    def __init__(self, node_id: str, sub_nodes: List[WorkflowNode] = None,
                 name: str = None, description: str = None):
        super().__init__(node_id, NodeType.PARALLEL, name, description)
        self.sub_nodes: List[WorkflowNode] = sub_nodes or []
        self.aggregation_func: Optional[Callable] = None
        
    async def execute(self, state: WorkflowState,
                     context: Dict[str, Any] = None) -> NodeResult:
        """并行执行子节点"""
        start_time = datetime.now()
        
        try:
            # 并行执行所有子节点
            tasks = [node.execute(state.copy(), context) for node in self.sub_nodes]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理结果
            outputs = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    outputs.append({
                        "node_id": self.sub_nodes[i].node_id,
                        "error": str(result),
                        "status": "error"
                    })
                else:
                    outputs.append(result.to_dict())
            
            # 聚合结果
            if self.aggregation_func:
                aggregated = self.aggregation_func(outputs)
            else:
                aggregated = {"parallel_results": outputs}
            
            state.set(f"{self.node_id}_output", aggregated)
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return NodeResult(
                node_id=self.node_id,
                state=state,
                output=aggregated,
                status="success",
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            logger.error(f"并行节点 {self.node_id} 执行失败: {e}")
            return NodeResult(
                node_id=self.node_id,
                state=state,
                status="error",
                error_message=str(e),
                execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000
            )


# ==================== 边定义 ====================

@dataclass
class WorkflowEdge:
    """工作流边 - 连接节点"""
    source_id: str
    target_id: str
    edge_type: EdgeType = EdgeType.DEFAULT
    condition: Optional[str] = None  # 条件边的条件名称
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "edge_type": self.edge_type.value,
            "condition": self.condition,
            "weight": self.weight,
            "metadata": self.metadata
        }


# ==================== 状态图构建器 ====================

class StateGraph:
    """状态图 - 工作流的核心结构"""
    
    def __init__(self, name: str = "workflow"):
        self.name = name
        self.nodes: Dict[str, WorkflowNode] = {}
        self.edges: Dict[str, List[WorkflowEdge]] = {}  # source_id -> edges
        self.entry_point: Optional[str] = None
        
    def add_node(self, node: WorkflowNode) -> 'StateGraph':
        """添加节点"""
        self.nodes[node.node_id] = node
        if node.node_id not in self.edges:
            self.edges[node.node_id] = []
        logger.info(f"添加节点: {node.node_id} ({node.node_type.value})")
        return self
    
    def add_edge(self, source_id: str, target_id: str,
                 edge_type: EdgeType = EdgeType.DEFAULT,
                 condition: str = None) -> 'StateGraph':
        """添加边"""
        if source_id not in self.nodes:
            raise ValueError(f"源节点不存在: {source_id}")
        if target_id not in self.nodes:
            raise ValueError(f"目标节点不存在: {target_id}")
        
        edge = WorkflowEdge(
            source_id=source_id,
            target_id=target_id,
            edge_type=edge_type,
            condition=condition
        )
        
        self.edges[source_id].append(edge)
        logger.info(f"添加边: {source_id} -> {target_id} ({edge_type.value})")
        return self
    
    def set_entry_point(self, node_id: str) -> 'StateGraph':
        """设置入口点"""
        if node_id not in self.nodes:
            raise ValueError(f"入口节点不存在: {node_id}")
        self.entry_point = node_id
        logger.info(f"设置入口点: {node_id}")
        return self
    
    def add_conditional_edges(self, source_id: str, 
                             condition_func: Callable,
                             path_map: Dict[str, str]) -> 'StateGraph':
        """添加条件边"""
        for condition, target_id in path_map.items():
            self.add_edge(source_id, target_id, EdgeType.CONDITIONAL, condition)
        return self
    
    def get_next_nodes(self, current_node_id: str, 
                      state: WorkflowState) -> List[str]:
        """获取下一个节点"""
        edges = self.edges.get(current_node_id, [])
        next_nodes = []
        
        for edge in edges:
            if edge.edge_type == EdgeType.DEFAULT:
                next_nodes.append(edge.target_id)
            elif edge.edge_type == EdgeType.CONDITIONAL:
                # 检查条件
                condition_result = state.get(f"{current_node_id}_branch")
                if condition_result == edge.condition:
                    next_nodes.append(edge.target_id)
        
        return next_nodes
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "name": self.name,
            "entry_point": self.entry_point,
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            "edges": {k: [e.to_dict() for e in v] for k, v in self.edges.items()}
        }
    
    def visualize(self) -> str:
        """生成可视化描述 (Mermaid格式)"""
        lines = ["graph TD"]
        
        for node_id, node in self.nodes.items():
            shape = self._get_node_shape(node.node_type)
            lines.append(f"    {node_id}{shape}")
        
        for source_id, edges in self.edges.items():
            for edge in edges:
                label = edge.condition or ""
                lines.append(f"    {source_id} -->|{label}| {edge.target_id}")
        
        return "\n".join(lines)
    
    def _get_node_shape(self, node_type: NodeType) -> str:
        """获取节点形状"""
        shapes = {
            NodeType.START: "([开始])",
            NodeType.END: "([结束])",
            NodeType.AGENT: "{Agent}",
            NodeType.TOOL: "[工具]",
            NodeType.CONDITION: "{条件}",
            NodeType.HUMAN: "{{人工}}",
            NodeType.PARALLEL: "[/并行/]",
        }
        return shapes.get(node_type, f"[{node_type.value}]")


# ==================== 工作流执行引擎 ====================

class WorkflowEngine:
    """工作流执行引擎"""
    
    def __init__(self, checkpoint_store = None):
        self.checkpoint_store = checkpoint_store or InMemoryCheckpointStore()
        self.active_workflows: Dict[str, 'WorkflowInstance'] = {}
        self.event_handlers: Dict[str, List[Callable]] = {}
        
    async def start_workflow(self, graph: StateGraph, 
                            initial_state: WorkflowState = None,
                            workflow_id: str = None) -> str:
        """启动工作流"""
        workflow_id = workflow_id or f"wf_{uuid.uuid4().hex[:12]}"
        
        instance = WorkflowInstance(
            workflow_id=workflow_id,
            graph=graph,
            engine=self,
            initial_state=initial_state or WorkflowState()
        )
        
        self.active_workflows[workflow_id] = instance
        
        # 异步执行
        asyncio.create_task(instance.run())
        
        logger.info(f"启动工作流: {workflow_id}")
        return workflow_id
    
    async def resume_workflow(self, workflow_id: str, 
                             human_input: Any = None) -> bool:
        """恢复暂停的工作流"""
        if workflow_id not in self.active_workflows:
            # 尝试从检查点恢复
            checkpoint = await self.checkpoint_store.get(workflow_id)
            if checkpoint:
                # 重建工作流实例
                pass
            return False
        
        instance = self.active_workflows[workflow_id]
        if instance.status == WorkflowStatus.PAUSED:
            await instance.resume(human_input)
            return True
        return False
    
    async def cancel_workflow(self, workflow_id: str) -> bool:
        """取消工作流"""
        if workflow_id in self.active_workflows:
            instance = self.active_workflows[workflow_id]
            await instance.cancel()
            return True
        return False
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """获取工作流状态"""
        if workflow_id not in self.active_workflows:
            return None
        return self.active_workflows[workflow_id].get_status()
    
    def on_event(self, event_type: str, handler: Callable):
        """注册事件处理器"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
    
    async def emit_event(self, event_type: str, data: Dict[str, Any]):
        """触发事件"""
        handlers = self.event_handlers.get(event_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    handler(data)
            except Exception as e:
                logger.error(f"事件处理器错误: {e}")


class WorkflowInstance:
    """工作流实例"""
    
    def __init__(self, workflow_id: str, graph: StateGraph,
                 engine: WorkflowEngine, initial_state: WorkflowState):
        self.workflow_id = workflow_id
        self.graph = graph
        self.engine = engine
        self.state = initial_state
        self.status = WorkflowStatus.PENDING
        self.current_node_id: Optional[str] = None
        self.history: List[NodeResult] = []
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self._cancelled = False
        self._paused = False
        self._pause_event = asyncio.Event()
        
    async def run(self):
        """执行工作流"""
        self.status = WorkflowStatus.RUNNING
        self.start_time = datetime.now()
        
        try:
            # 从入口点开始
            current_id = self.graph.entry_point
            
            while current_id and not self._cancelled:
                # 检查是否暂停
                if self._paused:
                    await self._pause_event.wait()
                    self._pause_event.clear()
                
                self.current_node_id = current_id
                node = self.graph.nodes[current_id]
                
                # 执行节点
                logger.info(f"[{self.workflow_id}] 执行节点: {current_id}")
                result = await node.execute(self.state, {"workflow_id": self.workflow_id})
                
                # 记录历史
                self.history.append(result)
                self.state = result.state
                
                # 触发事件
                await self.engine.emit_event("node_completed", {
                    "workflow_id": self.workflow_id,
                    "node_id": current_id,
                    "result": result.to_dict()
                })
                
                # 处理结果
                if result.status == "error":
                    # 检查是否有错误处理边
                    error_edges = [e for e in self.graph.edges.get(current_id, [])
                                 if e.edge_type == EdgeType.ERROR]
                    if error_edges:
                        current_id = error_edges[0].target_id
                        continue
                    else:
                        self.status = WorkflowStatus.FAILED
                        break
                
                elif result.status == "paused":
                    self.status = WorkflowStatus.PAUSED
                    self._paused = True
                    logger.info(f"[{self.workflow_id}] 工作流暂停，等待人工输入")
                    break
                
                # 获取下一个节点
                next_nodes = self.graph.get_next_nodes(current_id, self.state)
                
                if not next_nodes:
                    # 到达终点
                    if node.node_type == NodeType.END:
                        self.status = WorkflowStatus.COMPLETED
                    else:
                        self.status = WorkflowStatus.COMPLETED
                    break
                
                # 处理分支
                if len(next_nodes) == 1:
                    current_id = next_nodes[0]
                else:
                    # 并行分支处理
                    await self._handle_parallel_branches(next_nodes)
                    break
                
                # 创建检查点
                await self._create_checkpoint(current_id)
            
        except Exception as e:
            logger.error(f"[{self.workflow_id}] 工作流执行失败: {e}")
            self.status = WorkflowStatus.FAILED
        
        finally:
            self.end_time = datetime.now()
            await self.engine.emit_event("workflow_completed", {
                "workflow_id": self.workflow_id,
                "status": self.status.value,
                "duration": self.get_duration()
            })
    
    async def _handle_parallel_branches(self, node_ids: List[str]):
        """处理并行分支"""
        # 创建并行执行
        tasks = []
        for node_id in node_ids:
            node = self.graph.nodes[node_id]
            task = node.execute(self.state.copy(), {"workflow_id": self.workflow_id})
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 合并结果
        for result in results:
            if isinstance(result, NodeResult):
                self.history.append(result)
    
    async def _create_checkpoint(self, node_id: str):
        """创建检查点"""
        checkpoint = Checkpoint(
            id=f"cp_{uuid.uuid4().hex[:8]}",
            workflow_id=self.workflow_id,
            node_id=node_id,
            state=self.state.copy()
        )
        await self.engine.checkpoint_store.save(checkpoint)
    
    async def resume(self, human_input: Any = None):
        """恢复工作流"""
        if self.status == WorkflowStatus.PAUSED:
            # 更新状态
            if self.current_node_id and human_input is not None:
                node = self.graph.nodes[self.current_node_id]
                if isinstance(node, HumanNode):
                    self.state = node.submit_human_input(self.state, human_input)
            
            self._paused = False
            self.status = WorkflowStatus.RUNNING
            self._pause_event.set()
            
            # 继续执行
            next_nodes = self.graph.get_next_nodes(self.current_node_id, self.state)
            if next_nodes:
                await self.run_from_node(next_nodes[0])
    
    async def run_from_node(self, node_id: str):
        """从指定节点继续执行"""
        # 简化实现，实际应该重构run方法
        pass
    
    async def cancel(self):
        """取消工作流"""
        self._cancelled = True
        self.status = WorkflowStatus.CANCELLED
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        return {
            "workflow_id": self.workflow_id,
            "status": self.status.value,
            "current_node": self.current_node_id,
            "progress": self._calculate_progress(),
            "duration": self.get_duration(),
            "history_count": len(self.history)
        }
    
    def _calculate_progress(self) -> float:
        """计算进度"""
        if not self.graph.nodes:
            return 0.0
        executed = len(self.history)
        total = len(self.graph.nodes)
        return min(1.0, executed / total)
    
    def get_duration(self) -> float:
        """获取执行时长"""
        if not self.start_time:
            return 0.0
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()


# ==================== 检查点存储 ====================

class CheckpointStore(ABC):
    """检查点存储抽象基类"""
    
    @abstractmethod
    async def save(self, checkpoint: Checkpoint):
        pass
    
    @abstractmethod
    async def get(self, workflow_id: str) -> Optional[Checkpoint]:
        pass
    
    @abstractmethod
    async def list(self, workflow_id: str = None) -> List[Checkpoint]:
        pass


class InMemoryCheckpointStore(CheckpointStore):
    """内存检查点存储"""
    
    def __init__(self):
        self.checkpoints: Dict[str, List[Checkpoint]] = {}
    
    async def save(self, checkpoint: Checkpoint):
        if checkpoint.workflow_id not in self.checkpoints:
            self.checkpoints[checkpoint.workflow_id] = []
        self.checkpoints[checkpoint.workflow_id].append(checkpoint)
    
    async def get(self, workflow_id: str) -> Optional[Checkpoint]:
        checkpoints = self.checkpoints.get(workflow_id, [])
        return checkpoints[-1] if checkpoints else None
    
    async def list(self, workflow_id: str = None) -> List[Checkpoint]:
        if workflow_id:
            return self.checkpoints.get(workflow_id, [])
        all_checkpoints = []
        for cps in self.checkpoints.values():
            all_checkpoints.extend(cps)
        return all_checkpoints


# ==================== 预置工作流模板 ====================

class WorkflowTemplates:
    """预置工作流模板"""
    
    @staticmethod
    def create_react_agent(name: str = "ReAct Agent") -> StateGraph:
        """创建ReAct Agent工作流"""
        graph = StateGraph(name)
        
        # 节点
        start = WorkflowNode("start", NodeType.START, "开始")
        think = AgentNode("think", name="思考", 
                         description="分析问题和当前状态")
        act = ToolNode("act", lambda action: {"result": f"执行: {action}"},
                      name="执行", description="执行工具调用")
        observe = AgentNode("observe", name="观察",
                          description="观察执行结果")
        condition = ConditionNode("check", 
                                 lambda state: "continue" if state.get("continue", False) else "end",
                                 name="检查条件")
        end = WorkflowNode("end", NodeType.END, "结束")
        
        # 添加节点
        graph.add_node(start).add_node(think).add_node(act).add_node(observe).add_node(condition).add_node(end)
        
        # 添加边
        graph.set_entry_point("start")
        graph.add_edge("start", "think")
        graph.add_edge("think", "act")
        graph.add_edge("act", "observe")
        graph.add_edge("observe", "check")
        graph.add_conditional_edges("check", None, {
            "continue": "think",
            "end": "end"
        })
        
        return graph
    
    @staticmethod
    def create_plan_and_execute(name: str = "Plan & Execute") -> StateGraph:
        """创建计划-执行工作流"""
        graph = StateGraph(name)
        
        # 规划节点
        planner = AgentNode("planner", name="规划器",
                          description="制定执行计划")
        # 执行节点
        executor = AgentNode("executor", name="执行器",
                           description="执行计划步骤")
        # 检查节点
        checker = ConditionNode("checker",
                               lambda state: "complete" if state.get("all_complete", False) else "continue",
                               name="完成检查")
        
        graph.add_node(planner).add_node(executor).add_node(checker)
        graph.set_entry_point("planner")
        graph.add_edge("planner", "executor")
        graph.add_edge("executor", "checker")
        graph.add_conditional_edges("checker", None, {
            "continue": "executor",
            "complete": "end"
        })
        
        return graph
    
    @staticmethod
    def create_approval_workflow(name: str = "Approval Workflow") -> StateGraph:
        """创建审批工作流"""
        graph = StateGraph(name)
        
        # 提交
        submit = AgentNode("submit", name="提交申请",
                          description="提交审批申请")
        # 自动审核
        auto_review = AgentNode("auto_review", name="自动审核",
                               description="自动审核申请")
        # 人工审核
        human_review = HumanNode("human_review", 
                                prompt_template="请审核申请: {state}",
                                name="人工审核")
        # 条件判断
        decision = ConditionNode("decision",
                                lambda state: state.get("decision", "reject"),
                                name="审批决策")
        # 通知
        notify = AgentNode("notify", name="通知结果",
                          description="通知审批结果")
        
        graph.add_node(submit).add_node(auto_review).add_node(human_review).add_node(decision).add_node(notify)
        graph.set_entry_point("submit")
        graph.add_edge("submit", "auto_review")
        graph.add_edge("auto_review", "human_review")
        graph.add_edge("human_review", "decision")
        graph.add_conditional_edges("decision", None, {
            "approve": "notify",
            "reject": "notify",
            "need_more_info": "submit"
        })
        
        return graph


# ==================== 全局实例 ====================

# 默认工作流引擎
_default_engine: Optional[WorkflowEngine] = None


def get_workflow_engine() -> WorkflowEngine:
    """获取默认工作流引擎"""
    global _default_engine
    if _default_engine is None:
        _default_engine = WorkflowEngine()
    return _default_engine


# ==================== 使用示例 ====================

async def example_usage():
    """使用示例"""
    # 创建工作流引擎
    engine = get_workflow_engine()
    
    # 使用预置模板
    graph = WorkflowTemplates.create_react_agent("我的ReAct Agent")
    
    # 创建初始状态
    initial_state = WorkflowState()
    initial_state.set("input", "查询今天的天气")
    initial_state.set("continue", True)
    
    # 启动工作流
    workflow_id = await engine.start_workflow(graph, initial_state)
    
    print(f"工作流已启动: {workflow_id}")
    
    # 等待一段时间
    await asyncio.sleep(2)
    
    # 检查状态
    status = engine.get_workflow_status(workflow_id)
    print(f"工作流状态: {status}")


if __name__ == "__main__":
    # 运行示例
    asyncio.run(example_usage())
