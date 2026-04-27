#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Real-time Collaboration Framework - 实时协作与通信框架
Phase 2 核心组件 - 辉夜AI平台增强功能

核心特性:
- WebSocket连接管理
- 多人实时协作空间
- Agent协作空间
- 操作转换算法 (OT/CRDT)
- 冲突解决策略
- 用户感知与光标同步

参考: Socket.io, WebRTC, Yjs, Figma协作架构
"""

import asyncio
import json
import uuid
import logging
from typing import Dict, List, Any, Optional, Callable, Union, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod
from collections import defaultdict
import hashlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ==================== 核心类型定义 ====================

class CollaborationEventType(Enum):
    """协作事件类型"""
    # 用户事件
    USER_JOIN = "user_join"
    USER_LEAVE = "user_leave"
    USER_CURSOR = "user_cursor"
    USER_SELECTION = "user_selection"
    
    # 内容事件
    CONTENT_UPDATE = "content_update"
    CONTENT_INSERT = "content_insert"
    CONTENT_DELETE = "content_delete"
    CONTENT_REPLACE = "content_replace"
    
    # Agent事件
    AGENT_JOIN = "agent_join"
    AGENT_LEAVE = "agent_leave"
    AGENT_ACTION = "agent_action"
    AGENT_MESSAGE = "agent_message"
    
    # 系统事件
    SYNC_REQUEST = "sync_request"
    SYNC_RESPONSE = "sync_response"
    ACKNOWLEDGE = "acknowledge"
    ERROR = "error"


class ParticipantType(Enum):
    """参与者类型"""
    HUMAN = "human"
    AGENT = "agent"
    SYSTEM = "system"


class PermissionLevel(Enum):
    """权限级别"""
    VIEW = "view"  # 只读
    COMMENT = "comment"  # 可评论
    EDIT = "edit"  # 可编辑
    ADMIN = "admin"  # 管理员


@dataclass
class UserPresence:
    """用户在线状态"""
    user_id: str
    user_name: str
    user_avatar: Optional[str] = None
    status: str = "online"  # online, away, busy, offline
    cursor_position: Optional[Dict[str, Any]] = None
    selection_range: Optional[Dict[str, Any]] = None
    last_activity: datetime = field(default_factory=datetime.now)
    joined_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "user_name": self.user_name,
            "user_avatar": self.user_avatar,
            "status": self.status,
            "cursor_position": self.cursor_position,
            "selection_range": self.selection_range,
            "last_activity": self.last_activity.isoformat(),
            "joined_at": self.joined_at.isoformat()
        }


@dataclass
class CollaborationEvent:
    """协作事件"""
    event_id: str
    event_type: CollaborationEventType
    space_id: str
    participant_id: str
    participant_type: ParticipantType
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    vector_clock: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "space_id": self.space_id,
            "participant_id": self.participant_id,
            "participant_type": self.participant_type.value,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "vector_clock": self.vector_clock
        }


@dataclass
class Operation:
    """操作 - 用于OT/CRDT"""
    op_id: str
    op_type: str  # insert, delete, retain
    position: int
    content: Optional[str] = None
    length: int = 0
    attributes: Dict[str, Any] = field(default_factory=dict)
    author_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "op_id": self.op_id,
            "op_type": self.op_type,
            "position": self.position,
            "content": self.content,
            "length": self.length,
            "attributes": self.attributes,
            "author_id": self.author_id,
            "timestamp": self.timestamp.isoformat()
        }


# ==================== CRDT实现 ====================

class CRDTDocument:
    """CRDT文档 - 无冲突复制数据类型"""
    
    def __init__(self, doc_id: str):
        self.doc_id = doc_id
        self.content: Dict[str, Any] = {}
        self.operations: List[Operation] = []
        self.version_vector: Dict[str, int] = defaultdict(int)
        
    def apply_operation(self, operation: Operation) -> bool:
        """应用操作"""
        # 检查是否已应用
        if any(op.op_id == operation.op_id for op in self.operations):
            return False
        
        # 应用操作
        self.operations.append(operation)
        self.version_vector[operation.author_id] += 1
        
        # 更新内容
        if operation.op_type == "insert":
            self._apply_insert(operation)
        elif operation.op_type == "delete":
            self._apply_delete(operation)
        elif operation.op_type == "replace":
            self._apply_replace(operation)
        
        return True
    
    def _apply_insert(self, op: Operation):
        """应用插入操作"""
        # 简化实现
        if "text" not in self.content:
            self.content["text"] = ""
        
        text = self.content["text"]
        pos = min(op.position, len(text))
        self.content["text"] = text[:pos] + (op.content or "") + text[pos:]
    
    def _apply_delete(self, op: Operation):
        """应用删除操作"""
        if "text" in self.content:
            text = self.content["text"]
            pos = op.position
            length = op.length
            self.content["text"] = text[:pos] + text[pos + length:]
    
    def _apply_replace(self, op: Operation):
        """应用替换操作"""
        self._apply_delete(Operation(
            op_id=f"{op.op_id}_del",
            op_type="delete",
            position=op.position,
            length=op.length
        ))
        self._apply_insert(Operation(
            op_id=f"{op.op_id}_ins",
            op_type="insert",
            position=op.position,
            content=op.content
        ))
    
    def get_content(self) -> Dict[str, Any]:
        """获取内容"""
        return self.content.copy()
    
    def get_state_vector(self) -> Dict[str, int]:
        """获取状态向量"""
        return dict(self.version_vector)
    
    def merge(self, other: 'CRDTDocument') -> 'CRDTDocument':
        """合并另一个文档"""
        # 合并操作
        for op in other.operations:
            self.apply_operation(op)
        return self


# ==================== 协作空间 ====================

class CollaborationSpace:
    """协作空间 - 多人协作的容器"""
    
    def __init__(self, space_id: str, space_name: str, space_type: str = "document"):
        self.space_id = space_id
        self.space_name = space_name
        self.space_type = space_type
        
        # 参与者
        self.participants: Dict[str, UserPresence] = {}
        self.agents: Dict[str, Dict[str, Any]] = {}
        
        # 文档状态
        self.document = CRDTDocument(space_id)
        self.history: List[CollaborationEvent] = []
        
        # 权限管理
        self.permissions: Dict[str, PermissionLevel] = {}
        
        # 连接管理
        self.connections: Dict[str, Any] = {}  # participant_id -> connection
        
        # 事件处理器
        self.event_handlers: List[Callable] = []
        
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    def join(self, participant_id: str, participant_type: ParticipantType,
             user_info: Dict[str, Any]) -> bool:
        """加入空间"""
        if participant_id in self.participants:
            return False
        
        if participant_type == ParticipantType.HUMAN:
            presence = UserPresence(
                user_id=participant_id,
                user_name=user_info.get("name", "Anonymous"),
                user_avatar=user_info.get("avatar")
            )
            self.participants[participant_id] = presence
        elif participant_type == ParticipantType.AGENT:
            self.agents[participant_id] = {
                "agent_id": participant_id,
                "agent_name": user_info.get("name", "Agent"),
                "capabilities": user_info.get("capabilities", []),
                "status": "active",
                "joined_at": datetime.now()
            }
        
        # 广播加入事件
        self.broadcast_event(CollaborationEvent(
            event_id=f"evt_{uuid.uuid4().hex[:8]}",
            event_type=CollaborationEventType.USER_JOIN if participant_type == ParticipantType.HUMAN else CollaborationEventType.AGENT_JOIN,
            space_id=self.space_id,
            participant_id=participant_id,
            participant_type=participant_type,
            payload={"user_info": user_info}
        ))
        
        logger.info(f"参与者 {participant_id} 加入空间 {self.space_id}")
        return True
    
    def leave(self, participant_id: str):
        """离开空间"""
        if participant_id in self.participants:
            del self.participants[participant_id]
            
            self.broadcast_event(CollaborationEvent(
                event_id=f"evt_{uuid.uuid4().hex[:8]}",
                event_type=CollaborationEventType.USER_LEAVE,
                space_id=self.space_id,
                participant_id=participant_id,
                participant_type=ParticipantType.HUMAN,
                payload={}
            ))
        
        if participant_id in self.agents:
            del self.agents[participant_id]
    
    def update_cursor(self, participant_id: str, cursor_position: Dict[str, Any]):
        """更新光标位置"""
        if participant_id in self.participants:
            self.participants[participant_id].cursor_position = cursor_position
            self.participants[participant_id].last_activity = datetime.now()
            
            # 广播光标更新
            self.broadcast_event(CollaborationEvent(
                event_id=f"evt_{uuid.uuid4().hex[:8]}",
                event_type=CollaborationEventType.USER_CURSOR,
                space_id=self.space_id,
                participant_id=participant_id,
                participant_type=ParticipantType.HUMAN,
                payload={"cursor_position": cursor_position}
            ), exclude=[participant_id])
    
    def apply_edit(self, participant_id: str, operation: Operation) -> bool:
        """应用编辑"""
        # 检查权限
        if not self._check_permission(participant_id, PermissionLevel.EDIT):
            return False
        
        # 应用操作到文档
        success = self.document.apply_operation(operation)
        
        if success:
            # 广播更新
            self.broadcast_event(CollaborationEvent(
                event_id=f"evt_{uuid.uuid4().hex[:8]}",
                event_type=CollaborationEventType.CONTENT_UPDATE,
                space_id=self.space_id,
                participant_id=participant_id,
                participant_type=ParticipantType.HUMAN,
                payload={"operation": operation.to_dict()}
            ))
            
            self.updated_at = datetime.now()
        
        return success
    
    def broadcast_event(self, event: CollaborationEvent, exclude: List[str] = None):
        """广播事件"""
        exclude = exclude or []
        self.history.append(event)
        
        # 通知所有连接的参与者
        for participant_id, connection in self.connections.items():
            if participant_id not in exclude:
                try:
                    if hasattr(connection, 'send'):
                        asyncio.create_task(connection.send(json.dumps(event.to_dict())))
                except Exception as e:
                    logger.error(f"发送事件失败: {e}")
        
        # 调用事件处理器
        for handler in self.event_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(handler(event))
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"事件处理器错误: {e}")
    
    def _check_permission(self, participant_id: str, required_level: PermissionLevel) -> bool:
        """检查权限"""
        level = self.permissions.get(participant_id, PermissionLevel.VIEW)
        level_order = [PermissionLevel.VIEW, PermissionLevel.COMMENT, PermissionLevel.EDIT, PermissionLevel.ADMIN]
        return level_order.index(level) >= level_order.index(required_level)
    
    def set_permission(self, participant_id: str, level: PermissionLevel):
        """设置权限"""
        self.permissions[participant_id] = level
    
    def get_state(self) -> Dict[str, Any]:
        """获取空间状态"""
        return {
            "space_id": self.space_id,
            "space_name": self.space_name,
            "space_type": self.space_type,
            "participants": {k: v.to_dict() for k, v in self.participants.items()},
            "agents": self.agents,
            "document": self.document.get_content(),
            "version_vector": self.document.get_state_vector(),
            "participant_count": len(self.participants),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    def register_connection(self, participant_id: str, connection: Any):
        """注册连接"""
        self.connections[participant_id] = connection
    
    def unregister_connection(self, participant_id: str):
        """注销连接"""
        if participant_id in self.connections:
            del self.connections[participant_id]


# ==================== Agent协作空间 ====================

class AgentCollaborationSpace(CollaborationSpace):
    """Agent协作空间 - 多Agent协作"""
    
    def __init__(self, space_id: str, space_name: str):
        super().__init__(space_id, space_name, "agent_collaboration")
        
        # Agent特定功能
        self.shared_context: Dict[str, Any] = {}
        self.task_queue: List[Dict[str, Any]] = []
        self.agent_messages: List[Dict[str, Any]] = []
        
    def agent_message(self, agent_id: str, message: str, message_type: str = "chat"):
        """Agent发送消息"""
        if agent_id not in self.agents:
            return False
        
        msg = {
            "message_id": f"msg_{uuid.uuid4().hex[:8]}",
            "agent_id": agent_id,
            "agent_name": self.agents[agent_id]["agent_name"],
            "message": message,
            "message_type": message_type,
            "timestamp": datetime.now().isoformat()
        }
        
        self.agent_messages.append(msg)
        
        # 广播消息
        self.broadcast_event(CollaborationEvent(
            event_id=f"evt_{uuid.uuid4().hex[:8]}",
            event_type=CollaborationEventType.AGENT_MESSAGE,
            space_id=self.space_id,
            participant_id=agent_id,
            participant_type=ParticipantType.AGENT,
            payload=msg
        ))
        
        return True
    
    def assign_task(self, task: Dict[str, Any], assignee_agent_id: str = None):
        """分配任务"""
        task["task_id"] = f"task_{uuid.uuid4().hex[:8]}"
        task["status"] = "pending"
        task["created_at"] = datetime.now().isoformat()
        
        if assignee_agent_id:
            task["assignee"] = assignee_agent_id
        
        self.task_queue.append(task)
        
        # 通知Agent
        if assignee_agent_id and assignee_agent_id in self.connections:
            self.broadcast_event(CollaborationEvent(
                event_id=f"evt_{uuid.uuid4().hex[:8]}",
                event_type=CollaborationEventType.AGENT_ACTION,
                space_id=self.space_id,
                participant_id="system",
                participant_type=ParticipantType.SYSTEM,
                payload={"action": "task_assigned", "task": task}
            ))
        
        return task["task_id"]
    
    def update_shared_context(self, key: str, value: Any, agent_id: str):
        """更新共享上下文"""
        self.shared_context[key] = {
            "value": value,
            "updated_by": agent_id,
            "updated_at": datetime.now().isoformat()
        }
        
        # 广播上下文更新
        self.broadcast_event(CollaborationEvent(
            event_id=f"evt_{uuid.uuid4().hex[:8]}",
            event_type=CollaborationEventType.CONTENT_UPDATE,
            space_id=self.space_id,
            participant_id=agent_id,
            participant_type=ParticipantType.AGENT,
            payload={"context_update": {key: self.shared_context[key]}}
        ))


# ==================== 协作管理器 ====================

class CollaborationManager:
    """协作管理器 - 管理所有协作空间"""
    
    def __init__(self):
        self.spaces: Dict[str, CollaborationSpace] = {}
        self.user_spaces: Dict[str, Set[str]] = defaultdict(set)  # user_id -> space_ids
        self.event_listeners: List[Callable] = []
    
    def create_space(self, space_name: str, space_type: str = "document",
                    creator_id: str = None) -> CollaborationSpace:
        """创建协作空间"""
        space_id = f"space_{uuid.uuid4().hex[:12]}"
        
        if space_type == "agent_collaboration":
            space = AgentCollaborationSpace(space_id, space_name)
        else:
            space = CollaborationSpace(space_id, space_name, space_type)
        
        # 设置创建者为管理员
        if creator_id:
            space.set_permission(creator_id, PermissionLevel.ADMIN)
        
        self.spaces[space_id] = space
        logger.info(f"创建协作空间: {space_id} ({space_name})")
        return space
    
    def get_space(self, space_id: str) -> Optional[CollaborationSpace]:
        """获取协作空间"""
        return self.spaces.get(space_id)
    
    def delete_space(self, space_id: str) -> bool:
        """删除协作空间"""
        if space_id in self.spaces:
            del self.spaces[space_id]
            logger.info(f"删除协作空间: {space_id}")
            return True
        return False
    
    def list_spaces(self, user_id: str = None) -> List[Dict[str, Any]]:
        """列出协作空间"""
        if user_id:
            space_ids = self.user_spaces.get(user_id, set())
            return [self.spaces[sid].get_state() for sid in space_ids if sid in self.spaces]
        return [space.get_state() for space in self.spaces.values()]
    
    def join_space(self, space_id: str, participant_id: str,
                  participant_type: ParticipantType,
                  user_info: Dict[str, Any]) -> bool:
        """加入空间"""
        space = self.spaces.get(space_id)
        if not space:
            return False
        
        success = space.join(participant_id, participant_type, user_info)
        if success and participant_type == ParticipantType.HUMAN:
            self.user_spaces[participant_id].add(space_id)
        
        return success
    
    def leave_space(self, space_id: str, participant_id: str):
        """离开空间"""
        space = self.spaces.get(space_id)
        if space:
            space.leave(participant_id)
            self.user_spaces[participant_id].discard(space_id)
    
    def get_user_presence(self, space_id: str) -> List[Dict[str, Any]]:
        """获取用户在线状态"""
        space = self.spaces.get(space_id)
        if space:
            return [p.to_dict() for p in space.participants.values()]
        return []
    
    def broadcast_to_all(self, event: CollaborationEvent):
        """广播到所有空间"""
        for space in self.spaces.values():
            space.broadcast_event(event)
    
    def on_event(self, handler: Callable):
        """注册全局事件处理器"""
        self.event_listeners.append(handler)


# ==================== WebSocket处理器 ====================

class WebSocketHandler:
    """WebSocket处理器"""
    
    def __init__(self, collaboration_manager: CollaborationManager):
        self.manager = collaboration_manager
        self.connections: Dict[str, Any] = {}  # connection_id -> websocket
    
    async def handle_connection(self, websocket, path: str = None):
        """处理WebSocket连接"""
        connection_id = f"conn_{uuid.uuid4().hex[:8]}"
        self.connections[connection_id] = websocket
        
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._handle_message(connection_id, websocket, data)
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({"error": "Invalid JSON"}))
        except Exception as e:
            logger.error(f"WebSocket错误: {e}")
        finally:
            del self.connections[connection_id]
    
    async def _handle_message(self, connection_id: str, websocket, data: Dict):
        """处理消息"""
        msg_type = data.get("type")
        
        if msg_type == "join_space":
            await self._handle_join_space(connection_id, websocket, data)
        elif msg_type == "leave_space":
            await self._handle_leave_space(connection_id, data)
        elif msg_type == "cursor_update":
            await self._handle_cursor_update(connection_id, data)
        elif msg_type == "content_edit":
            await self._handle_content_edit(connection_id, data)
        elif msg_type == "sync_request":
            await self._handle_sync_request(connection_id, websocket, data)
        else:
            await websocket.send(json.dumps({"error": f"Unknown message type: {msg_type}"}))
    
    async def _handle_join_space(self, connection_id: str, websocket, data: Dict):
        """处理加入空间"""
        space_id = data.get("space_id")
        user_id = data.get("user_id")
        user_info = data.get("user_info", {})
        
        space = self.manager.get_space(space_id)
        if not space:
            await websocket.send(json.dumps({"error": "Space not found"}))
            return
        
        success = self.manager.join_space(space_id, user_id, ParticipantType.HUMAN, user_info)
        if success:
            space.register_connection(user_id, websocket)
            await websocket.send(json.dumps({
                "type": "join_success",
                "space_state": space.get_state()
            }))
        else:
            await websocket.send(json.dumps({"error": "Failed to join space"}))
    
    async def _handle_leave_space(self, connection_id: str, data: Dict):
        """处理离开空间"""
        space_id = data.get("space_id")
        user_id = data.get("user_id")
        self.manager.leave_space(space_id, user_id)
    
    async def _handle_cursor_update(self, connection_id: str, data: Dict):
        """处理光标更新"""
        space_id = data.get("space_id")
        user_id = data.get("user_id")
        cursor_position = data.get("cursor_position")
        
        space = self.manager.get_space(space_id)
        if space:
            space.update_cursor(user_id, cursor_position)
    
    async def _handle_content_edit(self, connection_id: str, data: Dict):
        """处理内容编辑"""
        space_id = data.get("space_id")
        user_id = data.get("user_id")
        operation_data = data.get("operation", {})
        
        operation = Operation(
            op_id=operation_data.get("op_id", f"op_{uuid.uuid4().hex[:8]}"),
            op_type=operation_data.get("op_type", "insert"),
            position=operation_data.get("position", 0),
            content=operation_data.get("content"),
            length=operation_data.get("length", 0),
            author_id=user_id
        )
        
        space = self.manager.get_space(space_id)
        if space:
            space.apply_edit(user_id, operation)
    
    async def _handle_sync_request(self, connection_id: str, websocket, data: Dict):
        """处理同步请求"""
        space_id = data.get("space_id")
        client_vector = data.get("version_vector", {})
        
        space = self.manager.get_space(space_id)
        if space:
            await websocket.send(json.dumps({
                "type": "sync_response",
                "document": space.document.get_content(),
                "version_vector": space.document.get_state_vector()
            }))


# ==================== 全局实例 ====================

_default_collaboration_manager: Optional[CollaborationManager] = None
_default_websocket_handler: Optional[WebSocketHandler] = None


def get_collaboration_manager() -> CollaborationManager:
    """获取默认协作管理器"""
    global _default_collaboration_manager
    if _default_collaboration_manager is None:
        _default_collaboration_manager = CollaborationManager()
    return _default_collaboration_manager


def get_websocket_handler() -> WebSocketHandler:
    """获取默认WebSocket处理器"""
    global _default_websocket_handler
    if _default_websocket_handler is None:
        _default_websocket_handler = WebSocketHandler(get_collaboration_manager())
    return _default_websocket_handler


# ==================== 使用示例 ====================

async def example_usage():
    """使用示例"""
    # 获取管理器
    manager = get_collaboration_manager()
    
    # 创建协作空间
    space = manager.create_space(
        space_name="项目文档协作",
        space_type="document",
        creator_id="user_1"
    )
    
    # 用户加入
    manager.join_space(
        space_id=space.space_id,
        participant_id="user_1",
        participant_type=ParticipantType.HUMAN,
        user_info={"name": "张三", "avatar": "https://example.com/avatar1.png"}
    )
    
    manager.join_space(
        space_id=space.space_id,
        participant_id="user_2",
        participant_type=ParticipantType.HUMAN,
        user_info={"name": "李四", "avatar": "https://example.com/avatar2.png"}
    )
    
    # 应用编辑
    operation = Operation(
        op_id="op_1",
        op_type="insert",
        position=0,
        content="Hello, World!",
        author_id="user_1"
    )
    space.apply_edit("user_1", operation)
    
    # 获取空间状态
    state = space.get_state()
    print(f"空间状态: {json.dumps(state, indent=2, ensure_ascii=False)}")
    
    # 创建Agent协作空间
    agent_space = manager.create_space(
        space_name="多Agent协作",
        space_type="agent_collaboration"
    )
    
    # Agent加入
    manager.join_space(
        space_id=agent_space.space_id,
        participant_id="agent_1",
        participant_type=ParticipantType.AGENT,
        user_info={"name": "ResearchAgent", "capabilities": ["search", "analyze"]}
    )
    
    # Agent发送消息
    agent_space.agent_message("agent_1", "我已完成数据分析任务", "task_complete")
    
    # 分配任务
    task_id = agent_space.assign_task(
        task={"description": "搜索最新AI论文", "priority": "high"},
        assignee_agent_id="agent_1"
    )
    
    print(f"\nAgent协作空间状态:")
    print(json.dumps(agent_space.get_state(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    # 运行示例
    asyncio.run(example_usage())
