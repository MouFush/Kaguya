"""
Pydantic模型定义
用于请求验证和响应序列化
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from enum import Enum


# ==================== 基础模型 ====================

class ResponseBase(BaseModel):
    """基础响应模型"""
    success: bool = True
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class PaginationParams(BaseModel):
    """分页参数"""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


# ==================== 聊天模型 ====================

class ChatMessage(BaseModel):
    """聊天消息"""
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: Optional[datetime] = None


class ChatRequest(BaseModel):
    """聊天请求"""
    message: str = Field(..., min_length=1, max_length=32000)
    history: List[ChatMessage] = Field(default_factory=list)
    role: Optional[str] = Field(default=None, description="角色ID，null表示无角色")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1024, ge=1, le=8192)
    stream: bool = Field(default=True)
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "你好",
                "history": [],
                "role": "kaguya",
                "temperature": 0.7,
                "max_tokens": 1024,
                "stream": True
            }
        }


class ChatResponse(BaseModel):
    """聊天响应"""
    content: str
    role: str = "assistant"
    usage: Optional[Dict[str, int]] = None
    finish_reason: Optional[str] = None


class StreamChunk(BaseModel):
    """流式响应块"""
    content: str
    done: bool = False
    index: int = 0


# ==================== 角色模型 ====================

class RoleType(str, Enum):
    """角色类型"""
    CHARACTER = "character"
    GENERAL = "general"


class Role(BaseModel):
    """角色定义"""
    id: str
    name: str
    description: str
    icon: str
    color: str
    type: RoleType
    system: str
    avatar: Optional[str] = None
    enabled: bool = True


class RoleListResponse(ResponseBase):
    """角色列表响应"""
    data: List[Role]
    total: int


# ==================== DeepSeek API模型 ====================

class DeepSeekConfig(BaseModel):
    """DeepSeek配置"""
    api_key: Optional[str] = None
    api_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"
    enabled: bool = False


class DeepSeekChatRequest(BaseModel):
    """DeepSeek聊天请求"""
    messages: List[ChatMessage]
    role: Optional[str] = None
    kaguya_mode: bool = True
    temperature: float = 0.7
    max_tokens: int = 1024


# ==================== 知识库模型 ====================

class DocumentUpload(BaseModel):
    """文档上传"""
    title: str
    content: str
    tags: List[str] = Field(default_factory=list)


class DocumentResponse(BaseModel):
    """文档响应"""
    id: str
    title: str
    content_preview: str
    tags: List[str]
    created_at: datetime
    updated_at: datetime


class RAGQuery(BaseModel):
    """RAG查询"""
    query: str
    top_k: int = Field(default=5, ge=1, le=20)
    filter_tags: Optional[List[str]] = None


# ==================== 记忆模型 ====================

class MemoryEntry(BaseModel):
    """记忆条目"""
    id: str
    content: str
    importance: float = Field(ge=0.0, le=1.0)
    created_at: datetime
    last_accessed: Optional[datetime] = None
    access_count: int = 0


class MemoryQuery(BaseModel):
    """记忆查询"""
    query: str
    limit: int = Field(default=10, ge=1, le=50)
    min_importance: float = Field(default=0.5, ge=0.0, le=1.0)


# ==================== 统计模型 ====================

class UsageStats(BaseModel):
    """使用统计"""
    total_sessions: int
    total_messages: int
    total_tokens: int
    average_response_time: float
    active_users: int


class ModelStats(BaseModel):
    """模型统计"""
    model_name: str
    request_count: int
    average_latency: float
    error_rate: float
    last_used: Optional[datetime]
