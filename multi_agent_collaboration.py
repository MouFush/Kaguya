"""
多Agent协作系统 - AutoGen风格群聊
支持多个Agent之间的协作对话和任务分配
"""

import asyncio
import json
import uuid
import time
from typing import Dict, List, Optional, Callable, Any, AsyncGenerator
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime
from collections import defaultdict
import threading


class AgentRole(Enum):
    """Agent角色类型"""
    COORDINATOR = "coordinator"      # 协调者，负责任务分配
    EXPERT = "expert"                # 专家，负责特定领域
    CRITIC = "critic"                # 批评者，负责审查和反馈
    EXECUTOR = "executor"            # 执行者，负责具体任务执行
    OBSERVER = "observer"            # 观察者，负责记录和总结


class MessageType(Enum):
    """消息类型"""
    CHAT = "chat"                    # 普通聊天
    TASK_ASSIGN = "task_assign"      # 任务分配
    TASK_RESULT = "task_result"      # 任务结果
    QUESTION = "question"            # 提问
    ANSWER = "answer"                # 回答
    FEEDBACK = "feedback"            # 反馈
    SUMMARY = "summary"              # 总结


@dataclass
class Agent:
    """Agent定义"""
    id: str
    name: str
    role: AgentRole
    system_prompt: str
    capabilities: List[str] = field(default_factory=list)
    llm_client: Any = None
    is_active: bool = True
    created_at: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'name': self.name,
            'role': self.role.value,
            'system_prompt': self.system_prompt,
            'capabilities': self.capabilities,
            'is_active': self.is_active,
            'created_at': self.created_at
        }


@dataclass
class ChatMessage:
    """聊天消息"""
    id: str
    agent_id: str
    agent_name: str
    content: str
    message_type: MessageType
    timestamp: float
    reply_to: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'agent_id': self.agent_id,
            'agent_name': self.agent_name,
            'content': self.content,
            'message_type': self.message_type.value,
            'timestamp': self.timestamp,
            'reply_to': self.reply_to,
            'metadata': self.metadata
        }


@dataclass
class CollaborationTask:
    """协作任务"""
    id: str
    description: str
    assigned_to: str
    assigned_by: str
    status: str  # pending, in_progress, completed, failed
    created_at: float
    completed_at: Optional[float] = None
    result: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'description': self.description,
            'assigned_to': self.assigned_to,
            'assigned_by': self.assigned_by,
            'status': self.status,
            'created_at': self.created_at,
            'completed_at': self.completed_at,
            'result': self.result
        }


class AgentGroup:
    """Agent群组 - AutoGen风格的多Agent协作"""
    
    def __init__(self, group_id: str, name: str, description: str = ""):
        self.group_id = group_id
        self.name = name
        self.description = description
        self.agents: Dict[str, Agent] = {}
        self.messages: List[ChatMessage] = []
        self.tasks: Dict[str, CollaborationTask] = {}
        self.max_rounds = 10
        self.current_round = 0
        self.is_active = False
        self._lock = threading.Lock()
        self._message_callbacks: List[Callable] = []
        self._task_callbacks: List[Callable] = []
        
    def add_agent(self, agent: Agent) -> bool:
        """添加Agent到群组"""
        with self._lock:
            if agent.id in self.agents:
                return False
            self.agents[agent.id] = agent
            return True
    
    def remove_agent(self, agent_id: str) -> bool:
        """从群组移除Agent"""
        with self._lock:
            if agent_id not in self.agents:
                return False
            del self.agents[agent_id]
            return True
    
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """获取Agent"""
        return self.agents.get(agent_id)
    
    def get_agents_by_role(self, role: AgentRole) -> List[Agent]:
        """获取特定角色的所有Agent"""
        return [a for a in self.agents.values() if a.role == role]
    
    def add_message(self, message: ChatMessage):
        """添加消息"""
        with self._lock:
            self.messages.append(message)
            # 触发回调
            for callback in self._message_callbacks:
                try:
                    callback(message)
                except:
                    pass
    
    def add_task(self, task: CollaborationTask):
        """添加任务"""
        with self._lock:
            self.tasks[task.id] = task
            # 触发回调
            for callback in self._task_callbacks:
                try:
                    callback(task)
                except:
                    pass
    
    def update_task_status(self, task_id: str, status: str, result: str = None):
        """更新任务状态"""
        with self._lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                task.status = status
                if result:
                    task.result = result
                if status in ['completed', 'failed']:
                    task.completed_at = time.time()
    
    def register_message_callback(self, callback: Callable):
        """注册消息回调"""
        self._message_callbacks.append(callback)
    
    def register_task_callback(self, callback: Callable):
        """注册任务回调"""
        self._task_callbacks.append(callback)
    
    def get_conversation_history(self, limit: int = 50) -> List[Dict]:
        """获取对话历史"""
        return [m.to_dict() for m in self.messages[-limit:]]
    
    def to_dict(self) -> Dict:
        return {
            'group_id': self.group_id,
            'name': self.name,
            'description': self.description,
            'agents': {k: v.to_dict() for k, v in self.agents.items()},
            'messages': [m.to_dict() for m in self.messages[-20:]],  # 最近20条
            'tasks': {k: v.to_dict() for k, v in self.tasks.items()},
            'is_active': self.is_active,
            'current_round': self.current_round,
            'max_rounds': self.max_rounds
        }


class MultiAgentCollaboration:
    """多Agent协作管理器"""
    
    def __init__(self):
        self.groups: Dict[str, AgentGroup] = {}
        self._lock = threading.Lock()
        self._default_system_prompts = {
            AgentRole.COORDINATOR: "你是协调者，负责理解用户需求并将任务分配给合适的专家Agent。你需要确保任务被正确分解和分配。",
            AgentRole.EXPERT: "你是领域专家，负责解决特定领域的问题。请提供专业的分析和解决方案。",
            AgentRole.CRITIC: "你是批评者，负责审查其他Agent的输出并提供改进建议。请指出潜在的问题和优化空间。",
            AgentRole.EXECUTOR: "你是执行者，负责具体任务的实施。请提供详细的执行步骤和结果。",
            AgentRole.OBSERVER: "你是观察者，负责记录对话过程并提供总结。请确保所有重要信息都被记录下来。"
        }
    
    def create_group(self, name: str, description: str = "") -> AgentGroup:
        """创建新的Agent群组"""
        group_id = str(uuid.uuid4())
        group = AgentGroup(group_id, name, description)
        
        with self._lock:
            self.groups[group_id] = group
        
        return group
    
    def get_group(self, group_id: str) -> Optional[AgentGroup]:
        """获取群组"""
        return self.groups.get(group_id)
    
    def delete_group(self, group_id: str) -> bool:
        """删除群组"""
        with self._lock:
            if group_id in self.groups:
                del self.groups[group_id]
                return True
            return False
    
    def create_agent(self, name: str, role: AgentRole, 
                     system_prompt: str = None, 
                     capabilities: List[str] = None,
                     llm_client: Any = None) -> Agent:
        """创建Agent"""
        agent_id = str(uuid.uuid4())
        
        if system_prompt is None:
            system_prompt = self._default_system_prompts.get(role, "你是一个AI助手。")
        
        return Agent(
            id=agent_id,
            name=name,
            role=role,
            system_prompt=system_prompt,
            capabilities=capabilities or [],
            llm_client=llm_client
        )
    
    def start_collaboration(self, group_id: str, initial_message: str, 
                           user_id: str = "user") -> Optional[str]:
        """开始协作对话"""
        group = self.get_group(group_id)
        if not group:
            return None
        
        # 添加用户消息
        message = ChatMessage(
            id=str(uuid.uuid4()),
            agent_id=user_id,
            agent_name="用户",
            content=initial_message,
            message_type=MessageType.CHAT,
            timestamp=time.time()
        )
        group.add_message(message)
        
        # 启动协作流程
        group.is_active = True
        group.current_round = 0
        
        # 在后台启动协作流程
        threading.Thread(
            target=self._collaboration_loop,
            args=(group_id,),
            daemon=True
        ).start()
        
        return message.id
    
    def _collaboration_loop(self, group_id: str):
        """协作循环 - 模拟AutoGen的群聊机制"""
        group = self.get_group(group_id)
        if not group:
            return
        
        while group.is_active and group.current_round < group.max_rounds:
            group.current_round += 1
            
            # 获取活跃的Agent
            active_agents = [a for a in group.agents.values() if a.is_active]
            if not active_agents:
                break
            
            # 简单的轮询机制：每个Agent轮流发言
            for agent in active_agents:
                if not group.is_active:
                    break
                
                # 生成Agent的响应
                response = self._generate_agent_response(agent, group)
                
                if response:
                    message = ChatMessage(
                        id=str(uuid.uuid4()),
                        agent_id=agent.id,
                        agent_name=agent.name,
                        content=response,
                        message_type=MessageType.CHAT,
                        timestamp=time.time()
                    )
                    group.add_message(message)
                    
                    # 模拟处理时间
                    time.sleep(0.5)
            
            # 检查是否应该结束
            if self._should_end_collaboration(group):
                break
        
        group.is_active = False
        
        # 添加总结消息
        self._add_summary_message(group)
    
    def _generate_agent_response(self, agent: Agent, group: AgentGroup) -> str:
        """生成Agent的响应"""
        # 这里应该调用实际的LLM
        # 暂时返回模拟响应
        
        history = group.get_conversation_history(5)
        last_message = history[-1] if history else None
        
        if agent.role == AgentRole.COORDINATOR:
            return f"【协调者-{agent.name}】我分析了当前情况，建议我们分步骤解决这个问题。首先..."
        elif agent.role == AgentRole.EXPERT:
            return f"【专家-{agent.name}】从专业角度来看，这个问题可以这样解决..."
        elif agent.role == AgentRole.CRITIC:
            return f"【批评者-{agent.name}】我注意到前面的方案可能存在以下问题..."
        elif agent.role == AgentRole.EXECUTOR:
            return f"【执行者-{agent.name}】我将按照计划执行具体步骤..."
        elif agent.role == AgentRole.OBSERVER:
            return f"【观察者-{agent.name}】总结一下目前的进展..."
        
        return f"【{agent.name}】收到，正在处理..."
    
    def _should_end_collaboration(self, group: AgentGroup) -> bool:
        """判断是否应该结束协作"""
        # 简单的结束条件：最后一条消息包含"结束"或"完成"
        if group.messages:
            last_msg = group.messages[-1]
            if any(keyword in last_msg.content for keyword in ['结束', '完成', '总结', '完毕']):
                return True
        return False
    
    def _add_summary_message(self, group: AgentGroup):
        """添加总结消息"""
        summary = ChatMessage(
            id=str(uuid.uuid4()),
            agent_id="system",
            agent_name="系统",
            content=f"协作已完成，共进行了 {group.current_round} 轮对话。",
            message_type=MessageType.SUMMARY,
            timestamp=time.time()
        )
        group.add_message(summary)
    
    def send_message_to_group(self, group_id: str, content: str, 
                              user_id: str = "user", user_name: str = "用户") -> Optional[str]:
        """向群组发送消息"""
        group = self.get_group(group_id)
        if not group or not group.is_active:
            return None
        
        message = ChatMessage(
            id=str(uuid.uuid4()),
            agent_id=user_id,
            agent_name=user_name,
            content=content,
            message_type=MessageType.CHAT,
            timestamp=time.time()
        )
        group.add_message(message)
        return message.id
    
    def stop_collaboration(self, group_id: str) -> bool:
        """停止协作"""
        group = self.get_group(group_id)
        if group:
            group.is_active = False
            return True
        return False
    
    def get_all_groups(self) -> List[Dict]:
        """获取所有群组"""
        return [g.to_dict() for g in self.groups.values()]


# 全局协作管理器实例
_collaboration_manager = None

def get_collaboration_manager() -> MultiAgentCollaboration:
    """获取协作管理器单例"""
    global _collaboration_manager
    if _collaboration_manager is None:
        _collaboration_manager = MultiAgentCollaboration()
    return _collaboration_manager


# 预设的Agent团队配置
PRESET_TEAMS = {
    "软件开发团队": {
        "description": "包含产品经理、架构师、开发工程师、测试工程师的完整开发团队",
        "agents": [
            {"name": "产品经理", "role": AgentRole.COORDINATOR, "capabilities": ["需求分析", "产品规划"]},
            {"name": "架构师", "role": AgentRole.EXPERT, "capabilities": ["系统设计", "技术选型"]},
            {"name": "开发工程师", "role": AgentRole.EXECUTOR, "capabilities": ["编码实现", "代码审查"]},
            {"name": "测试工程师", "role": AgentRole.CRITIC, "capabilities": ["测试用例", "质量保证"]},
        ]
    },
    "数据分析团队": {
        "description": "专业的数据分析团队",
        "agents": [
            {"name": "数据分析师", "role": AgentRole.EXPERT, "capabilities": ["数据清洗", "统计分析"]},
            {"name": "业务专家", "role": AgentRole.COORDINATOR, "capabilities": ["业务理解", "需求转化"]},
            {"name": "可视化专家", "role": AgentRole.EXECUTOR, "capabilities": ["图表制作", "报告生成"]},
        ]
    },
    "创意写作团队": {
        "description": "创意写作和内容生成团队",
        "agents": [
            {"name": "创意总监", "role": AgentRole.COORDINATOR, "capabilities": ["创意策划", "方向把控"]},
            {"name": "文案写手", "role": AgentRole.EXECUTOR, "capabilities": ["文案撰写", "内容创作"]},
            {"name": "编辑", "role": AgentRole.CRITIC, "capabilities": ["内容审查", "质量把控"]},
        ]
    }
}


if __name__ == "__main__":
    # 测试代码
    print("多Agent协作系统测试")
    
    manager = get_collaboration_manager()
    
    # 创建群组
    group = manager.create_group("测试团队", "用于测试的多Agent团队")
    print(f"创建群组: {group.name} (ID: {group.group_id})")
    
    # 创建Agent
    coordinator = manager.create_agent("协调者", AgentRole.COORDINATOR)
    expert = manager.create_agent("专家", AgentRole.EXPERT)
    critic = manager.create_agent("批评者", AgentRole.CRITIC)
    
    # 添加到群组
    group.add_agent(coordinator)
    group.add_agent(expert)
    group.add_agent(critic)
    
    print(f"添加了 {len(group.agents)} 个Agent")
    
    # 开始协作
    msg_id = manager.start_collaboration(group.group_id, "请讨论如何设计一个高性能的Web应用")
    print(f"开始协作，消息ID: {msg_id}")
    
    # 等待一段时间
    time.sleep(5)
    
    # 查看消息
    print(f"\n对话历史 ({len(group.messages)} 条消息):")
    for msg in group.messages:
        print(f"[{msg.agent_name}]: {msg.content[:50]}...")
    
    # 停止协作
    manager.stop_collaboration(group.group_id)
    print("\n协作已停止")
