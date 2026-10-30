#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辉夜AI平台 - 增强功能集成模块 V2
基于GitHub最佳实践深度优化，整合MCP、深度研究、A2A多智能体等前沿功能

核心优化点：
1. MCP系统 - 增加更多实用工具、资源管理和提示词模板
2. 深度研究系统 - 引入多策略研究、智能报告生成
3. A2A系统 - 增加更多智能体类型、协作模式和工作流编排
4. 新增监控和配置管理模块
"""

import asyncio
import json
import time
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum, auto
import logging
import uuid
import hashlib
from collections import deque

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ==================== 配置管理 ====================

@dataclass
class EnhancedConfig:
    """增强功能配置"""
    # MCP配置
    mcp_enabled: bool = True
    mcp_max_tools: int = 50
    mcp_max_prompts: int = 100
    mcp_timeout: int = 30
    
    # 深度研究配置
    research_enabled: bool = True
    research_max_iterations: int = 10
    research_timeout: int = 300
    research_parallel_search: bool = True
    
    # A2A配置
    a2a_enabled: bool = True
    a2a_max_agents: int = 20
    a2a_message_ttl: int = 3600
    a2a_enable_collaboration: bool = True
    
    # 监控配置
    monitoring_enabled: bool = True
    metrics_retention_hours: int = 24
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ==================== 监控和指标 ====================

@dataclass
class MetricPoint:
    """指标数据点"""
    timestamp: datetime
    metric_type: str
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


class MetricsCollector:
    """指标收集器"""
    
    def __init__(self, retention_hours: int = 24):
        self.retention_hours = retention_hours
        self.metrics: deque = deque(maxlen=10000)
        self.counters: Dict[str, int] = {}
        self.gauges: Dict[str, float] = {}
    
    def record(self, metric_type: str, value: float, labels: Dict[str, str] = None):
        """记录指标"""
        point = MetricPoint(
            timestamp=datetime.now(),
            metric_type=metric_type,
            value=value,
            labels=labels or {}
        )
        self.metrics.append(point)
    
    def increment_counter(self, name: str, value: int = 1):
        """增加计数器"""
        self.counters[name] = self.counters.get(name, 0) + value
    
    def set_gauge(self, name: str, value: float):
        """设置仪表盘"""
        self.gauges[name] = value
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """获取指标摘要"""
        return {
            "counters": self.counters.copy(),
            "gauges": self.gauges.copy(),
            "total_points": len(self.metrics),
            "metric_types": list(set(m.metric_type for m in self.metrics))
        }


# ==================== 增强MCP系统 ====================

class MCPMessageType(Enum):
    """MCP消息类型扩展"""
    INITIALIZE = "initialize"
    TOOLS_LIST = "tools/list"
    TOOLS_CALL = "tools/call"
    TOOLS_STREAM = "tools/stream"
    RESOURCES_LIST = "resources/list"
    RESOURCES_READ = "resources/read"
    RESOURCES_SUBSCRIBE = "resources/subscribe"
    PROMPTS_LIST = "prompts/list"
    PROMPTS_GET = "prompts/get"
    COMPLETIONS_COMPLETE = "completions/complete"
    NOTIFICATION = "notification"
    PING = "ping"
    PROGRESS = "progress"


@dataclass
class MCPTool:
    """MCP工具定义增强版"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Optional[Callable] = None
    category: str = "general"
    tags: List[str] = field(default_factory=list)
    examples: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
            "category": self.category,
            "tags": self.tags,
            "examples": self.examples
        }


@dataclass
class MCPResource:
    """MCP资源定义增强版"""
    uri: str
    name: str
    mime_type: str
    description: str
    handler: Optional[Callable] = None
    size: Optional[int] = None
    subscribers: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "uri": self.uri,
            "name": self.name,
            "mimeType": self.mime_type,
            "description": self.description,
            "size": self.size
        }


@dataclass
class MCPPrompt:
    """MCP提示词模板增强版"""
    name: str
    description: str
    arguments: List[Dict[str, Any]]
    template: str
    category: str = "general"
    version: str = "1.0"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "arguments": self.arguments,
            "category": self.category,
            "version": self.version
        }
    
    def render(self, **kwargs) -> str:
        """渲染提示词模板"""
        try:
            return self.template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"缺少模板参数: {e}")


class EnhancedMCPServer:
    """增强版MCP服务器"""
    
    def __init__(self, name: str = "Kaguya AI Enhanced", version: str = "2.0.0", 
                 config: EnhancedConfig = None):
        self.name = name
        self.version = version
        self.config = config or EnhancedConfig()
        self.tools: Dict[str, MCPTool] = {}
        self.resources: Dict[str, MCPResource] = {}
        self.prompts: Dict[str, MCPPrompt] = {}
        self.metrics = MetricsCollector()
        self.capabilities = {
            "tools": {"listChanged": True},
            "resources": {"listChanged": True, "subscribe": True},
            "prompts": {"listChanged": True},
            "logging": {},
            "progress": {}
        }
        
    def register_tool(self, tool: MCPTool):
        """注册工具"""
        if len(self.tools) >= self.config.mcp_max_tools:
            raise ValueError(f"工具数量超过限制: {self.config.mcp_max_tools}")
        
        self.tools[tool.name] = tool
        self.metrics.increment_counter("tools_registered")
        logger.info(f"注册MCP工具: {tool.name} (类别: {tool.category})")
    
    def register_resource(self, resource: MCPResource):
        """注册资源"""
        self.resources[resource.uri] = resource
        self.metrics.increment_counter("resources_registered")
        logger.info(f"注册MCP资源: {resource.uri}")
    
    def register_prompt(self, prompt: MCPPrompt):
        """注册提示词模板"""
        if len(self.prompts) >= self.config.mcp_max_prompts:
            raise ValueError(f"提示词数量超过限制: {self.config.mcp_max_prompts}")
        
        self.prompts[prompt.name] = prompt
        self.metrics.increment_counter("prompts_registered")
        logger.info(f"注册MCP提示词: {prompt.name}")
    
    async def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """处理MCP消息"""
        start_time = time.time()
        msg_type = message.get("type")
        msg_id = message.get("id")
        
        try:
            handler_map = {
                MCPMessageType.INITIALIZE.value: self._handle_initialize,
                MCPMessageType.TOOLS_LIST.value: self._handle_tools_list,
                MCPMessageType.TOOLS_CALL.value: self._handle_tools_call,
                MCPMessageType.RESOURCES_LIST.value: self._handle_resources_list,
                MCPMessageType.RESOURCES_READ.value: self._handle_resources_read,
                MCPMessageType.RESOURCES_SUBSCRIBE.value: self._handle_resources_subscribe,
                MCPMessageType.PROMPTS_LIST.value: self._handle_prompts_list,
                MCPMessageType.PROMPTS_GET.value: self._handle_prompts_get,
                MCPMessageType.PING.value: lambda msg_id: {"type": "pong", "id": msg_id}
            }
            
            handler = handler_map.get(msg_type)
            if handler:
                if msg_type in [MCPMessageType.TOOLS_CALL.value]:
                    response = await handler(msg_id, message.get("params", {}))
                elif msg_type in [MCPMessageType.RESOURCES_READ.value, 
                                 MCPMessageType.PROMPTS_GET.value,
                                 MCPMessageType.RESOURCES_SUBSCRIBE.value]:
                    response = await handler(msg_id, message.get("params", {}))
                else:
                    response = await handler(msg_id)
            else:
                response = self._error_response(msg_id, f"未知消息类型: {msg_type}")
            
            # 记录指标
            duration = time.time() - start_time
            self.metrics.record("mcp_request_duration", duration, {"type": msg_type})
            self.metrics.increment_counter(f"mcp_requests_{msg_type}")
            
            return response
            
        except Exception as e:
            logger.error(f"处理MCP消息失败: {e}")
            self.metrics.increment_counter("mcp_errors")
            return self._error_response(msg_id, str(e))
    
    async def _handle_initialize(self, msg_id: str) -> Dict[str, Any]:
        """处理初始化请求"""
        return {
            "type": "initialize",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": self.capabilities,
                "serverInfo": {
                    "name": self.name,
                    "version": self.version
                }
            }
        }
    
    async def _handle_tools_list(self, msg_id: str) -> Dict[str, Any]:
        """处理工具列表请求"""
        return {
            "type": "tools/list",
            "id": msg_id,
            "result": {
                "tools": [tool.to_dict() for tool in self.tools.values()]
            }
        }
    
    async def _handle_tools_call(self, msg_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理工具调用请求"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if tool_name not in self.tools:
            return self._error_response(msg_id, f"工具不存在: {tool_name}")
        
        tool = self.tools[tool_name]
        if tool.handler is None:
            return self._error_response(msg_id, f"工具未实现: {tool_name}")
        
        try:
            # 调用工具处理器
            if asyncio.iscoroutinefunction(tool.handler):
                result = await tool.handler(**arguments)
            else:
                result = tool.handler(**arguments)
            
            return {
                "type": "tools/call",
                "id": msg_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, ensure_ascii=False) if isinstance(result, dict) else str(result)
                        }
                    ]
                }
            }
        except Exception as e:
            return self._error_response(msg_id, f"工具调用失败: {str(e)}")
    
    async def _handle_resources_list(self, msg_id: str) -> Dict[str, Any]:
        """处理资源列表请求"""
        return {
            "type": "resources/list",
            "id": msg_id,
            "result": {
                "resources": [resource.to_dict() for resource in self.resources.values()]
            }
        }
    
    async def _handle_resources_read(self, msg_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理资源读取请求"""
        uri = params.get("uri")
        
        if uri not in self.resources:
            return self._error_response(msg_id, f"资源不存在: {uri}")
        
        resource = self.resources[uri]
        if resource.handler is None:
            return self._error_response(msg_id, f"资源未实现: {uri}")
        
        try:
            content = resource.handler()
            return {
                "type": "resources/read",
                "id": msg_id,
                "result": {
                    "contents": [
                        {
                            "uri": uri,
                            "mimeType": resource.mime_type,
                            "text": content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
                        }
                    ]
                }
            }
        except Exception as e:
            return self._error_response(msg_id, f"资源读取失败: {str(e)}")
    
    async def _handle_resources_subscribe(self, msg_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理资源订阅请求"""
        uri = params.get("uri")
        client_id = params.get("client_id", "anonymous")
        
        if uri not in self.resources:
            return self._error_response(msg_id, f"资源不存在: {uri}")
        
        resource = self.resources[uri]
        if client_id not in resource.subscribers:
            resource.subscribers.append(client_id)
        
        return {
            "type": "resources/subscribe",
            "id": msg_id,
            "result": {"subscribed": True, "uri": uri}
        }
    
    async def _handle_prompts_list(self, msg_id: str) -> Dict[str, Any]:
        """处理提示词列表请求"""
        return {
            "type": "prompts/list",
            "id": msg_id,
            "result": {
                "prompts": [prompt.to_dict() for prompt in self.prompts.values()]
            }
        }
    
    async def _handle_prompts_get(self, msg_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理提示词获取请求"""
        prompt_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if prompt_name not in self.prompts:
            return self._error_response(msg_id, f"提示词不存在: {prompt_name}")
        
        prompt = self.prompts[prompt_name]
        try:
            rendered = prompt.render(**arguments)
            return {
                "type": "prompts/get",
                "id": msg_id,
                "result": {
                    "description": prompt.description,
                    "messages": [
                        {
                            "role": "user",
                            "content": {
                                "type": "text",
                                "text": rendered
                            }
                        }
                    ]
                }
            }
        except Exception as e:
            return self._error_response(msg_id, f"提示词渲染失败: {str(e)}")
    
    def _error_response(self, msg_id: str, error_msg: str) -> Dict[str, Any]:
        """生成错误响应"""
        return {
            "type": "error",
            "id": msg_id,
            "error": {
                "code": -32600,
                "message": error_msg
            }
        }
    
    def get_tools_by_category(self, category: str) -> List[MCPTool]:
        """按类别获取工具"""
        return [tool for tool in self.tools.values() if tool.category == category]
    
    def search_tools(self, query: str) -> List[MCPTool]:
        """搜索工具"""
        query_lower = query.lower()
        results = []
        for tool in self.tools.values():
            if (query_lower in tool.name.lower() or 
                query_lower in tool.description.lower() or
                any(query_lower in tag.lower() for tag in tool.tags)):
                results.append(tool)
        return results


# ==================== 增强深度研究系统 ====================

class ResearchStrategy(Enum):
    """研究策略类型"""
    BREADTH_FIRST = "breadth_first"  # 广度优先
    DEPTH_FIRST = "depth_first"      # 深度优先
    ITERATIVE = "iterative"          # 迭代式
    ADAPTIVE = "adaptive"            # 自适应


class ResearchStatus(Enum):
    """研究状态"""
    PENDING = "pending"
    PLANNING = "planning"
    RESEARCHING = "researching"
    ANALYZING = "analyzing"
    SYNTHESIZING = "synthesizing"
    WRITING = "writing"
    REVIEWING = "reviewing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ResearchStep:
    """研究步骤增强版"""
    id: str
    type: str
    description: str
    status: str = "pending"
    result: Any = None
    error: str = None
    start_time: datetime = None
    end_time: datetime = None
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "description": self.description,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "dependencies": self.dependencies,
            "metadata": self.metadata
        }


@dataclass
class ResearchFinding:
    """研究发现"""
    id: str
    source: str
    content: str
    relevance_score: float
    credibility_score: float
    timestamp: datetime
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "content": self.content[:500] if len(self.content) > 500 else self.content,
            "relevance_score": self.relevance_score,
            "credibility_score": self.credibility_score,
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags
        }


@dataclass
class ResearchTask:
    """研究任务增强版"""
    id: str
    query: str
    status: ResearchStatus
    strategy: ResearchStrategy
    steps: List[ResearchStep] = field(default_factory=list)
    findings: List[ResearchFinding] = field(default_factory=list)
    report: str = ""
    summary: str = ""
    created_at: datetime = None
    completed_at: datetime = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    progress: float = 0.0
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "query": self.query,
            "status": self.status.value,
            "strategy": self.strategy.value,
            "steps": [step.to_dict() for step in self.steps],
            "findings": [f.to_dict() for f in self.findings],
            "report_length": len(self.report),
            "summary": self.summary,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "progress": self.progress,
            "metadata": self.metadata
        }


class EnhancedResearchPlanner:
    """增强版研究计划生成器"""
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
    
    async def create_plan(self, query: str, strategy: ResearchStrategy = ResearchStrategy.ADAPTIVE) -> Dict[str, Any]:
        """创建研究计划"""
        # 分析查询意图和类型
        query_analysis = self._analyze_query(query)
        
        plan = {
            "query": query,
            "objective": f"深入研究: {query}",
            "strategy": strategy.value,
            "query_analysis": query_analysis,
            "steps": [],
            "estimated_time": "5-15分钟",
            "expected_outputs": []
        }
        
        # 根据策略生成步骤
        if strategy == ResearchStrategy.BREADTH_FIRST:
            plan["steps"] = self._create_breadth_first_steps(query_analysis)
        elif strategy == ResearchStrategy.DEPTH_FIRST:
            plan["steps"] = self._create_depth_first_steps(query_analysis)
        elif strategy == ResearchStrategy.ITERATIVE:
            plan["steps"] = self._create_iterative_steps(query_analysis)
        else:  # ADAPTIVE
            plan["steps"] = self._create_adaptive_steps(query_analysis)
        
        return plan
    
    def _analyze_query(self, query: str) -> Dict[str, Any]:
        """分析查询"""
        analysis = {
            "type": "general",
            "complexity": "medium",
            "domains": [],
            "keywords": [],
            "requires_technical": False,
            "requires_recent": False
        }
        
        # 技术关键词检测
        tech_keywords = [
            "代码", "编程", "开发", "框架", "库", "API", "算法", "架构",
            "Python", "JavaScript", "Java", "Go", "Rust", "数据库", "服务器",
            "机器学习", "深度学习", "AI", "LLM", "模型", "训练", "神经网络"
        ]
        
        # 新闻关键词检测
        news_keywords = ["新闻", "最新", "报道", "事件", "发布", "宣布", "更新", "2025", "2026"]
        
        # 学术关键词检测
        academic_keywords = ["论文", "研究", "学术", "期刊", "会议", "综述", "文献"]
        
        query_lower = query.lower()
        
        if any(kw in query for kw in tech_keywords):
            analysis["type"] = "technical"
            analysis["requires_technical"] = True
            analysis["domains"].append("technology")
        
        if any(kw in query for kw in news_keywords):
            analysis["type"] = "news"
            analysis["requires_recent"] = True
            analysis["domains"].append("news")
        
        if any(kw in query for kw in academic_keywords):
            analysis["type"] = "academic"
            analysis["domains"].append("academic")
        
        # 复杂度评估
        if len(query) > 50 or any(kw in query for kw in ["对比", "分析", "评估", "综述"]):
            analysis["complexity"] = "high"
        
        return analysis
    
    def _create_breadth_first_steps(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """创建广度优先步骤"""
        return [
            {"type": "search", "description": "广泛搜索相关主题", "priority": 1},
            {"type": "search", "description": "搜索不同角度的观点", "priority": 1},
            {"type": "search", "description": "搜索背景信息", "priority": 2},
            {"type": "fetch", "description": "获取关键资源内容", "priority": 2},
            {"type": "analyze", "description": "分析信息分布", "priority": 3},
            {"type": "synthesize", "description": "整合广泛信息", "priority": 3}
        ]
    
    def _create_depth_first_steps(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """创建深度优先步骤"""
        return [
            {"type": "search", "description": "搜索核心概念", "priority": 1},
            {"type": "fetch", "description": "获取核心资源", "priority": 1},
            {"type": "analyze", "description": "深度分析核心内容", "priority": 2},
            {"type": "search", "description": "搜索相关细节", "priority": 2},
            {"type": "fetch", "description": "获取详细资料", "priority": 3},
            {"type": "analyze", "description": "深入分析细节", "priority": 3},
            {"type": "synthesize", "description": "深度整合", "priority": 4}
        ]
    
    def _create_iterative_steps(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """创建迭代式步骤"""
        return [
            {"type": "search", "description": "初始搜索", "priority": 1},
            {"type": "analyze", "description": "分析初步结果", "priority": 1},
            {"type": "search", "description": "基于分析深入搜索", "priority": 2},
            {"type": "analyze", "description": "迭代分析", "priority": 2},
            {"type": "search", "description": "补充搜索", "priority": 3},
            {"type": "synthesize", "description": "迭代整合", "priority": 3}
        ]
    
    def _create_adaptive_steps(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """创建自适应步骤"""
        steps = []
        
        # 基础搜索步骤
        steps.append({"type": "search", "description": "基础信息搜索", "priority": 1})
        
        if analysis["requires_technical"]:
            steps.append({"type": "search", "description": "搜索技术文档和实现", "priority": 1})
            steps.append({"type": "fetch", "description": "获取技术文档", "priority": 2})
        
        if analysis["requires_recent"]:
            steps.append({"type": "search", "description": "搜索最新动态", "priority": 1})
        
        if "academic" in analysis["domains"]:
            steps.append({"type": "search", "description": "搜索学术论文", "priority": 2})
        
        # 通用分析步骤
        steps.extend([
            {"type": "fetch", "description": "获取关键内容", "priority": 2},
            {"type": "analyze", "description": "多维度分析", "priority": 3},
            {"type": "verify", "description": "交叉验证", "priority": 3},
            {"type": "synthesize", "description": "综合整合", "priority": 4}
        ])
        
        return steps


class EnhancedDeepResearchEngine:
    """增强版深度研究引擎"""
    
    def __init__(self, llm_client=None, search_func=None, config: EnhancedConfig = None):
        self.llm_client = llm_client
        self.search_func = search_func or self._default_search
        self.config = config or EnhancedConfig()
        self.planner = EnhancedResearchPlanner(llm_client)
        self.tasks: Dict[str, ResearchTask] = {}
        self.metrics = MetricsCollector()
    
    async def start_research(self, query: str, strategy: ResearchStrategy = ResearchStrategy.ADAPTIVE, 
                           depth: str = "standard") -> str:
        """开始深度研究"""
        task_id = f"research_{uuid.uuid4().hex[:8]}"
        
        task = ResearchTask(
            id=task_id,
            query=query,
            status=ResearchStatus.PLANNING,
            strategy=strategy
        )
        self.tasks[task_id] = task
        
        # 异步执行研究
        asyncio.create_task(self._execute_research(task, depth))
        
        self.metrics.increment_counter("research_started")
        logger.info(f"深度研究任务已启动: {task_id} (策略: {strategy.value})")
        
        return task_id
    
    async def _execute_research(self, task: ResearchTask, depth: str):
        """执行研究流程"""
        try:
            # 1. 创建研究计划
            logger.info(f"[{task.id}] 创建研究计划...")
            plan = await self.planner.create_plan(task.query, task.strategy)
            task.metadata["plan"] = plan
            task.status = ResearchStatus.RESEARCHING
            task.progress = 0.1
            
            # 2. 执行研究步骤
            total_steps = len(plan["steps"])
            for i, step_plan in enumerate(plan["steps"]):
                step = ResearchStep(
                    id=f"step_{i}",
                    type=step_plan["type"],
                    description=step_plan["description"],
                    metadata={"priority": step_plan.get("priority", 1)}
                )
                task.steps.append(step)
                
                await self._execute_step(task, step)
                task.progress = 0.1 + (0.6 * (i + 1) / total_steps)
                
                # 如果步骤失败，尝试替代方案
                if step.status == "failed":
                    await self._handle_step_failure(task, step)
            
            # 3. 分析阶段
            task.status = ResearchStatus.ANALYZING
            await self._analyze_findings(task)
            task.progress = 0.8
            
            # 4. 生成报告
            task.status = ResearchStatus.WRITING
            await self._generate_report(task, depth)
            task.progress = 0.95
            
            # 5. 生成摘要
            await self._generate_summary(task)
            
            task.status = ResearchStatus.COMPLETED
            task.completed_at = datetime.now()
            task.progress = 1.0
            
            self.metrics.increment_counter("research_completed")
            logger.info(f"[{task.id}] 研究完成")
            
        except Exception as e:
            logger.error(f"[{task.id}] 研究失败: {e}")
            task.status = ResearchStatus.FAILED
            task.metadata["error"] = str(e)
            self.metrics.increment_counter("research_failed")
    
    async def _execute_step(self, task: ResearchTask, step: ResearchStep):
        """执行单个研究步骤"""
        step.status = "running"
        step.start_time = datetime.now()
        
        try:
            if step.type == "search":
                result = await self._perform_search(task, step)
            elif step.type == "fetch":
                result = await self._fetch_content(task, step)
            elif step.type == "analyze":
                result = await self._analyze_content(task, step)
            elif step.type == "synthesize":
                result = await self._synthesize_findings(task, step)
            elif step.type == "verify":
                result = await self._verify_findings(task, step)
            else:
                result = {"status": "skipped"}
            
            step.result = result
            step.status = "completed"
            
            # 保存发现
            if step.type == "search" and isinstance(result, dict):
                findings = result.get("findings", [])
                for finding_data in findings:
                    finding = ResearchFinding(
                        id=f"finding_{uuid.uuid4().hex[:8]}",
                        source=finding_data.get("source", "unknown"),
                        content=finding_data.get("content", ""),
                        relevance_score=finding_data.get("relevance", 0.5),
                        credibility_score=finding_data.get("credibility", 0.5),
                        timestamp=datetime.now(),
                        tags=finding_data.get("tags", [])
                    )
                    task.findings.append(finding)
            
        except Exception as e:
            step.error = str(e)
            step.status = "failed"
            logger.error(f"步骤 {step.id} 失败: {e}")
        
        finally:
            step.end_time = datetime.now()
    
    async def _perform_search(self, task: ResearchTask, step: ResearchStep) -> Dict[str, Any]:
        """执行搜索"""
        search_query = self._build_search_query(task.query, step.description)
        
        # 并行搜索多个变体
        queries = [search_query, f"{search_query} 教程", f"{search_query} 最佳实践"]
        
        all_results = []
        for query in queries[:3 if self.config.research_parallel_search else 1]:
            results = await self.search_func(query)
            if isinstance(results, list):
                all_results.extend(results)
        
        # 去重和排序
        seen = set()
        unique_results = []
        for r in all_results:
            key = r.get("url", r.get("title", str(r)))
            if key not in seen:
                seen.add(key)
                unique_results.append(r)
        
        # 转换为发现格式
        findings = []
        for result in unique_results[:10]:
            findings.append({
                "source": result.get("url", "unknown"),
                "content": result.get("snippet", result.get("title", "")),
                "relevance": 0.7,
                "credibility": 0.6,
                "tags": ["search_result"]
            })
        
        return {
            "query": search_query,
            "results_count": len(unique_results),
            "findings": findings
        }
    
    async def _fetch_content(self, task: ResearchTask, step: ResearchStep) -> Dict[str, Any]:
        """获取内容"""
        contents = []
        
        # 从发现中获取URL
        sources = [f for f in task.findings if f.source != "unknown"][:5]
        
        for finding in sources:
            try:
                content = await self._fetch_url(finding.source)
                contents.append({
                    "url": finding.source,
                    "content": content[:3000],
                    "size": len(content)
                })
            except Exception as e:
                logger.warning(f"获取内容失败 {finding.source}: {e}")
        
        return {"contents": contents, "count": len(contents)}
    
    async def _analyze_content(self, task: ResearchTask, step: ResearchStep) -> Dict[str, Any]:
        """分析内容"""
        # 基于发现进行分析
        key_facts = []
        main_points = []
        controversies = []
        
        for finding in task.findings[:10]:
            content = finding.content
            if len(content) > 50:
                key_facts.append(content[:200])
        
        return {
            "key_facts": key_facts[:5],
            "main_points": main_points,
            "controversies": controversies,
            "analysis_depth": "standard"
        }
    
    async def _synthesize_findings(self, task: ResearchTask, step: ResearchStep) -> Dict[str, Any]:
        """整合发现"""
        # 按可信度和相关性排序
        sorted_findings = sorted(
            task.findings,
            key=lambda f: (f.credibility_score + f.relevance_score) / 2,
            reverse=True
        )
        
        key_insights = []
        for finding in sorted_findings[:5]:
            key_insights.append({
                "content": finding.content[:300],
                "source": finding.source,
                "confidence": (finding.credibility_score + finding.relevance_score) / 2
            })
        
        return {
            "summary": f"关于'{task.query}'的综合研究",
            "key_insights": key_insights,
            "sources_analyzed": len(task.findings),
            "confidence": "medium"
        }
    
    async def _verify_findings(self, task: ResearchTask, step: ResearchStep) -> Dict[str, Any]:
        """验证发现"""
        # 交叉验证关键信息
        verified = []
        unverified = []
        
        for finding in task.findings:
            if finding.credibility_score > 0.7:
                verified.append(finding.to_dict())
            else:
                unverified.append(finding.to_dict())
        
        return {
            "verified_count": len(verified),
            "unverified_count": len(unverified),
            "verification_rate": len(verified) / len(task.findings) if task.findings else 0,
            "verified_facts": verified[:5]
        }
    
    async def _handle_step_failure(self, task: ResearchTask, step: ResearchStep):
        """处理步骤失败"""
        logger.info(f"[{task.id}] 处理步骤失败: {step.description}")
        
        # 根据步骤类型选择替代策略
        if step.type == "search":
            # 使用更宽泛的查询重试
            step.status = "running"
            try:
                alternative_query = f"{task.query} 简介"
                results = await self.search_func(alternative_query)
                step.result = {"alternative_search": True, "results": results}
                step.status = "completed"
            except Exception as e:
                step.error = f"重试失败: {str(e)}"
                step.status = "failed"
    
    async def _generate_report(self, task: ResearchTask, depth: str):
        """生成研究报告"""
        templates = {
            "brief": self._brief_report_template(),
            "standard": self._standard_report_template(),
            "comprehensive": self._comprehensive_report_template(),
            "technical": self._technical_report_template()
        }
        
        template = templates.get(depth, templates["standard"])
        
        # 准备报告数据
        findings_summary = "\n".join([
            f"- {f.content[:150]}... (来源: {f.source})"
            for f in task.findings[:10]
        ])
        
        task.report = template.format(
            query=task.query,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
            findings_count=len(task.findings),
            steps_count=len(task.steps),
            strategy=task.strategy.value,
            findings_summary=findings_summary
        )
    
    async def _generate_summary(self, task: ResearchTask):
        """生成研究摘要"""
        if task.findings:
            top_findings = sorted(
                task.findings,
                key=lambda f: f.relevance_score,
                reverse=True
            )[:3]
            
            task.summary = f"研究主题: {task.query}\n\n核心发现:\n"
            for i, finding in enumerate(top_findings, 1):
                task.summary += f"{i}. {finding.content[:200]}...\n"
    
    def _brief_report_template(self) -> str:
        return """# 研究简报: {query}

**研究时间**: {timestamp}
**策略**: {strategy}
**信息来源**: {findings_count} 个来源

## 核心发现

{findings_summary}

## 结论

基于收集到的信息，该主题的关键要点已总结如上。

---
*本报告由辉夜AI深度研究系统自动生成*"""
    
    def _standard_report_template(self) -> str:
        return """# 深度研究报告: {query}

**研究时间**: {timestamp}
**研究策略**: {strategy}
**执行步骤**: {steps_count} 步
**信息来源**: {findings_count} 个来源

## 研究概述

本报告通过系统化研究流程，深入分析了"{query}"相关主题。

## 主要发现

{findings_summary}

## 详细分析

### 1. 关键事实
基于收集到的信息，以下是关于该主题的关键事实。

### 2. 主要观点
不同来源对该主题的主要观点包括多个角度。

### 3. 深入洞察
通过综合分析，我们发现该主题的核心要点。

## 结论与建议

基于以上研究，建议进一步关注该领域的最新发展。

---
*本报告由辉夜AI深度研究系统自动生成*"""
    
    def _comprehensive_report_template(self) -> str:
        return """# 综合研究报告: {query}

**研究时间**: {timestamp}
**研究策略**: {strategy}
**执行步骤**: {steps_count} 步
**信息来源**: {findings_count} 个来源

## 执行摘要

本报告通过系统化研究流程，深入分析了"{query}"相关主题，采用{strategy}策略进行全面调研。

## 研究方法

### 研究策略
{strategy}

### 数据来源
多个权威来源和最新资料

## 详细发现

{findings_summary}

## 深度分析

### 背景与上下文
### 关键概念解析
### 多方观点对比
### 趋势与预测

## 信息来源评估

### 高可信度来源
### 需要验证的信息
### 信息缺口

## 结论

## 建议

## 附录

### 研究方法说明
### 数据来源列表
### 术语表

---
*本报告由辉夜AI深度研究系统自动生成*"""
    
    def _technical_report_template(self) -> str:
        return """# 技术研究报告: {query}

**研究时间**: {timestamp}
**研究策略**: {strategy}
**执行步骤**: {steps_count} 步
**信息来源**: {findings_count} 个来源

## 技术概述

## 架构分析

## 实现细节

## 最佳实践

## 性能考虑

## 安全考虑

## 相关工具与资源

{findings_summary}

## 结论

---
*本报告由辉夜AI深度研究系统自动生成*"""
    
    def _build_search_query(self, original_query: str, step_description: str) -> str:
        """构建搜索查询"""
        if "技术文档" in step_description:
            return f"{original_query} documentation tutorial"
        elif "社区讨论" in step_description:
            return f"{original_query} forum discussion"
        elif "新闻" in step_description:
            return f"{original_query} news latest"
        elif "学术" in step_description:
            return f"{original_query} paper research"
        else:
            return original_query
    
    async def _default_search(self, query: str) -> List[Dict[str, str]]:
        """默认搜索函数"""
        return [
            {"title": f"关于 {query} 的搜索结果", "url": "https://example.com/1", "snippet": "相关内容..."},
            {"title": f"{query} 详细指南", "url": "https://example.com/2", "snippet": "详细说明..."}
        ]
    
    async def _fetch_url(self, url: str) -> str:
        """获取URL内容"""
        return f"内容来自 {url}"
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        if task_id not in self.tasks:
            return None
        return self.tasks[task_id].to_dict()
    
    def get_task_report(self, task_id: str) -> Optional[str]:
        """获取任务报告"""
        if task_id not in self.tasks:
            return None
        task = self.tasks[task_id]
        if task.status != ResearchStatus.COMPLETED:
            return f"研究尚未完成，当前状态: {task.status.value}，进度: {task.progress:.0%}"
        return task.report


# ==================== 增强A2A系统 ====================

class AgentStatus(Enum):
    """智能体状态"""
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class MessageType(Enum):
    """A2A消息类型扩展"""
    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    TASK_UPDATE = "task_update"
    TASK_CANCEL = "task_cancel"
    CAPABILITY_QUERY = "capability_query"
    CAPABILITY_RESPONSE = "capability_response"
    COLLABORATION_REQUEST = "collaboration_request"
    COLLABORATION_RESPONSE = "collaboration_response"
    STATUS_UPDATE = "status_update"
    HEARTBEAT = "heartbeat"
    ERROR = "error"
    BROADCAST = "broadcast"


@dataclass
class AgentCapability:
    """智能体能力增强版"""
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    version: str = "1.0"
    requires_auth: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "version": self.version,
            "requires_auth": self.requires_auth
        }


@dataclass
class AgentProfile:
    """智能体档案增强版"""
    id: str
    name: str
    description: str
    capabilities: List[AgentCapability] = field(default_factory=list)
    status: AgentStatus = AgentStatus.IDLE
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = None
    last_heartbeat: datetime = None
    task_count: int = 0
    success_rate: float = 1.0
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "capabilities": [cap.to_dict() for cap in self.capabilities],
            "status": self.status.value,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "task_count": self.task_count,
            "success_rate": self.success_rate
        }


@dataclass
class A2AMessage:
    """A2A消息增强版"""
    id: str
    type: MessageType
    sender_id: str
    receiver_id: str
    payload: Dict[str, Any]
    timestamp: datetime = None
    reply_to: Optional[str] = None
    priority: int = 5  # 1-10, 1最高
    ttl: int = 3600  # 生存时间(秒)
    
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
            "reply_to": self.reply_to,
            "priority": self.priority
        }


@dataclass
class Task:
    """任务增强版"""
    id: str
    description: str
    status: TaskStatus
    assigned_to: Optional[str] = None
    created_by: str = ""
    created_at: datetime = None
    completed_at: Optional[datetime] = None
    result: Any = None
    error: str = None
    subtasks: List['Task'] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3
    timeout: int = 300  # 秒
    
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
            "error": self.error,
            "retry_count": self.retry_count,
            "subtasks_count": len(self.subtasks)
        }


class EnhancedBaseAgent:
    """增强版基础智能体"""
    
    def __init__(self, agent_id: str, name: str, description: str):
        self.profile = AgentProfile(
            id=agent_id,
            name=name,
            description=description
        )
        self.message_handler: Optional[Callable] = None
        self.task_handler: Optional[Callable] = None
        self.received_messages: deque = deque(maxlen=1000)
        self.active_tasks: Dict[str, Task] = {}
        self.task_history: deque = deque(maxlen=100)
        self.metrics = MetricsCollector()
        
    def add_capability(self, capability: AgentCapability):
        """添加能力"""
        self.profile.capabilities.append(capability)
        logger.info(f"Agent {self.profile.id} 添加能力: {capability.name}")
    
    async def receive_message(self, message: A2AMessage):
        """接收消息"""
        self.received_messages.append(message)
        self.metrics.increment_counter("messages_received")
        
        # 根据消息类型处理
        handlers = {
            MessageType.TASK_REQUEST: self._handle_task_request,
            MessageType.CAPABILITY_QUERY: self._handle_capability_query,
            MessageType.COLLABORATION_REQUEST: self._handle_collaboration_request,
            MessageType.STATUS_UPDATE: self._handle_status_update,
            MessageType.TASK_CANCEL: self._handle_task_cancel,
            MessageType.HEARTBEAT: self._handle_heartbeat
        }
        
        handler = handlers.get(message.type)
        if handler:
            await handler(message)
        
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
            created_by=message.sender_id,
            timeout=task_data.get("timeout", 300)
        )
        
        self.active_tasks[task.id] = task
        self.profile.status = AgentStatus.BUSY
        self.profile.task_count += 1
        
        # 异步执行任务
        asyncio.create_task(self._execute_task(task, message.sender_id))
    
    async def _execute_task(self, task: Task, requester_id: str):
        """执行任务"""
        start_time = time.time()
        
        try:
            task.status = TaskStatus.IN_PROGRESS
            
            # 调用任务处理器
            if self.task_handler:
                result = await asyncio.wait_for(
                    self.task_handler(task),
                    timeout=task.timeout
                )
                task.result = result
            else:
                task.result = {"status": "completed", "message": f"任务 {task.id} 完成"}
            
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            
            # 更新成功率
            self._update_success_rate(True)
            
            # 发送响应
            await self.send_message(
                receiver_id=requester_id,
                msg_type=MessageType.TASK_RESPONSE,
                payload={
                    "task_id": task.id,
                    "status": "completed",
                    "result": task.result,
                    "duration": time.time() - start_time
                },
                reply_to=task.id
            )
            
        except asyncio.TimeoutError:
            task.status = TaskStatus.FAILED
            task.error = "任务超时"
            self._update_success_rate(False)
            
            await self.send_message(
                receiver_id=requester_id,
                msg_type=MessageType.ERROR,
                payload={"task_id": task.id, "error": "任务超时"}
            )
            
        except Exception as e:
            logger.error(f"任务执行失败: {e}")
            task.status = TaskStatus.FAILED
            task.error = str(e)
            self._update_success_rate(False)
            
            # 尝试重试
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = TaskStatus.RETRYING
                await asyncio.sleep(2 ** task.retry_count)  # 指数退避
                asyncio.create_task(self._execute_task(task, requester_id))
                return
            
            await self.send_message(
                receiver_id=requester_id,
                msg_type=MessageType.ERROR,
                payload={"task_id": task.id, "error": str(e)}
            )
        
        finally:
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                self.task_history.append(task)
                del self.active_tasks[task.id]
                
                # 更新状态
                if not self.active_tasks:
                    self.profile.status = AgentStatus.IDLE
    
    def _update_success_rate(self, success: bool):
        """更新成功率"""
        # 简单的滑动窗口平均
        alpha = 0.1
        success_val = 1.0 if success else 0.0
        self.profile.success_rate = (1 - alpha) * self.profile.success_rate + alpha * success_val
    
    async def _handle_capability_query(self, message: A2AMessage):
        """处理能力查询"""
        await self.send_message(
            receiver_id=message.sender_id,
            msg_type=MessageType.CAPABILITY_RESPONSE,
            payload={
                "agent_id": self.profile.id,
                "capabilities": [cap.to_dict() for cap in self.profile.capabilities],
                "status": self.profile.status.value
            },
            reply_to=message.id
        )
    
    async def _handle_collaboration_request(self, message: A2AMessage):
        """处理协作请求"""
        collaboration_type = message.payload.get("type", "simple")
        
        # 评估是否可以协作
        can_collaborate = (
            self.profile.status == AgentStatus.IDLE and
            len(self.active_tasks) < 3  # 最多同时处理3个任务
        )
        
        await self.send_message(
            receiver_id=message.sender_id,
            msg_type=MessageType.COLLABORATION_RESPONSE,
            payload={
                "accepted": can_collaborate,
                "agent_id": self.profile.id,
                "reason": "Available" if can_collaborate else "Busy",
                "current_load": len(self.active_tasks)
            },
            reply_to=message.id
        )
    
    async def _handle_status_update(self, message: A2AMessage):
        """处理状态更新"""
        pass
    
    async def _handle_task_cancel(self, message: A2AMessage):
        """处理任务取消"""
        task_id = message.payload.get("task_id")
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            task.status = TaskStatus.CANCELLED
            del self.active_tasks[task_id]
    
    async def _handle_heartbeat(self, message: A2AMessage):
        """处理心跳"""
        self.profile.last_heartbeat = datetime.now()
    
    async def send_message(self, receiver_id: str, msg_type: MessageType, 
                          payload: Dict[str, Any], reply_to: Optional[str] = None,
                          priority: int = 5):
        """发送消息"""
        message = A2AMessage(
            id=str(uuid.uuid4()),
            type=msg_type,
            sender_id=self.profile.id,
            receiver_id=receiver_id,
            payload=payload,
            reply_to=reply_to,
            priority=priority
        )
        
        await EnhancedA2AHub.get_instance().route_message(message)
        self.metrics.increment_counter("messages_sent")
    
    async def request_task(self, target_agent_id: str, task_description: str, 
                          task_params: Dict[str, Any] = None, timeout: int = 300) -> str:
        """向其他agent请求任务"""
        task_id = str(uuid.uuid4())
        
        await self.send_message(
            receiver_id=target_agent_id,
            msg_type=MessageType.TASK_REQUEST,
            payload={
                "task": {
                    "id": task_id,
                    "description": task_description,
                    "parameters": task_params or {},
                    "timeout": timeout
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
        return []
    
    def set_message_handler(self, handler: Callable):
        """设置消息处理器"""
        self.message_handler = handler
    
    def set_task_handler(self, handler: Callable):
        """设置任务处理器"""
        self.task_handler = handler
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "profile": self.profile.to_dict(),
            "active_tasks": len(self.active_tasks),
            "total_messages_received": len(self.received_messages),
            "metrics": self.metrics.get_metrics_summary()
        }


class EnhancedA2AHub:
    """增强版A2A消息中心"""
    
    _instance = None
    
    def __new__(cls, config: EnhancedConfig = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.agents: Dict[str, EnhancedBaseAgent] = {}
            cls._instance.message_history: deque = deque(maxlen=5000)
            cls._instance.config = config or EnhancedConfig()
            cls._instance.metrics = MetricsCollector()
            cls._instance.subscribers: Dict[str, List[str]] = {}  # 广播订阅
        return cls._instance
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def register_agent(self, agent: EnhancedBaseAgent):
        """注册智能体"""
        self.agents[agent.profile.id] = agent
        self.metrics.increment_counter("agents_registered")
        logger.info(f"注册智能体: {agent.profile.id} - {agent.profile.name}")
    
    def unregister_agent(self, agent_id: str):
        """注销智能体"""
        if agent_id in self.agents:
            del self.agents[agent_id]
            logger.info(f"注销智能体: {agent_id}")
    
    async def route_message(self, message: A2AMessage):
        """路由消息到目标智能体"""
        self.message_history.append(message)
        self.metrics.increment_counter("messages_routed")
        
        # 处理广播消息
        if message.receiver_id == "broadcast":
            await self._handle_broadcast(message)
            return
        
        receiver_id = message.receiver_id
        if receiver_id in self.agents:
            await self.agents[receiver_id].receive_message(message)
        else:
            logger.warning(f"目标智能体不存在: {receiver_id}")
            self.metrics.increment_counter("routing_errors")
    
    async def _handle_broadcast(self, message: A2AMessage):
        """处理广播消息"""
        broadcast_type = message.payload.get("broadcast_type", "all")
        
        if broadcast_type == "all":
            targets = list(self.agents.keys())
        elif broadcast_type == "by_capability":
            capability = message.payload.get("capability")
            targets = [
                agent_id for agent_id, agent in self.agents.items()
                if any(cap.name == capability for cap in agent.profile.capabilities)
            ]
        else:
            targets = []
        
        # 发送给所有目标
        for target_id in targets:
            if target_id != message.sender_id:  # 不发送给自己
                await self.agents[target_id].receive_message(message)
    
    def get_agent(self, agent_id: str) -> Optional[EnhancedBaseAgent]:
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
    
    def get_hub_stats(self) -> Dict[str, Any]:
        """获取Hub统计信息"""
        return {
            "registered_agents": len(self.agents),
            "message_history_size": len(self.message_history),
            "metrics": self.metrics.get_metrics_summary()
        }


# ==================== 专业智能体类型 ====================

class ResearchAgent(EnhancedBaseAgent):
    """研究智能体 - 负责信息收集和研究"""
    
    def __init__(self, agent_id: str = "research_agent"):
        super().__init__(
            agent_id=agent_id,
            name="研究专家",
            description="擅长信息收集、深度研究和分析报告生成"
        )
        
        self.add_capability(AgentCapability(
            name="web_search",
            description="网络搜索和信息收集",
            parameters={"query": "string", "max_results": "integer"}
        ))
        
        self.add_capability(AgentCapability(
            name="deep_research",
            description="深度研究和报告生成",
            parameters={"topic": "string", "depth": "string", "strategy": "string"}
        ))
        
        self.add_capability(AgentCapability(
            name="data_analysis",
            description="数据分析和可视化",
            parameters={"data": "object", "analysis_type": "string"}
        ))
        
        self.set_task_handler(self._handle_research_task)
    
    async def _handle_research_task(self, task: Task) -> Dict[str, Any]:
        """处理研究任务"""
        # 解析任务参数
        topic = task.description
        
        # 创建研究引擎并执行任务
        engine = EnhancedDeepResearchEngine()
        research_task_id = await engine.start_research(
            query=topic,
            depth="standard"
        )
        
        # 等待研究完成
        max_wait = 60
        for _ in range(max_wait):
            await asyncio.sleep(1)
            status = engine.get_task_status(research_task_id)
            if status and status["status"] in ["completed", "failed"]:
                break
        
        report = engine.get_task_report(research_task_id)
        return {
            "research_task_id": research_task_id,
            "report": report,
            "status": "completed"
        }


class CodeAgent(EnhancedBaseAgent):
    """代码智能体 - 负责编程和代码分析"""
    
    def __init__(self, agent_id: str = "code_agent"):
        super().__init__(
            agent_id=agent_id,
            name="代码专家",
            description="擅长编程、代码审查、技术实现和架构设计"
        )
        
        self.add_capability(AgentCapability(
            name="code_review",
            description="代码审查和优化建议",
            parameters={"code": "string", "language": "string"}
        ))
        
        self.add_capability(AgentCapability(
            name="code_generation",
            description="根据需求生成代码",
            parameters={"requirement": "string", "language": "string", "framework": "string"}
        ))
        
        self.add_capability(AgentCapability(
            name="refactoring",
            description="代码重构建议",
            parameters={"code": "string", "goals": "array"}
        ))
        
        self.add_capability(AgentCapability(
            name="debugging",
            description="调试和错误分析",
            parameters={"error": "string", "context": "string"}
        ))
        
        self.set_task_handler(self._handle_code_task)
    
    async def _handle_code_task(self, task: Task) -> Dict[str, Any]:
        """处理代码任务"""
        return {
            "task": task.description,
            "result": "代码任务处理完成",
            "suggestions": [
                "建议1: 优化代码结构",
                "建议2: 添加错误处理",
                "建议3: 提高代码可读性"
            ],
            "status": "completed"
        }


class WritingAgent(EnhancedBaseAgent):
    """写作智能体 - 负责内容创作和文案"""
    
    def __init__(self, agent_id: str = "writing_agent"):
        super().__init__(
            agent_id=agent_id,
            name="写作专家",
            description="擅长内容创作、文案撰写、文档整理和翻译"
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
        
        self.add_capability(AgentCapability(
            name="translation",
            description="多语言翻译",
            parameters={"text": "string", "source_lang": "string", "target_lang": "string"}
        ))
        
        self.add_capability(AgentCapability(
            name="summarization",
            description="文本摘要",
            parameters={"text": "string", "max_length": "integer"}
        ))


class DataAnalysisAgent(EnhancedBaseAgent):
    """数据分析智能体"""
    
    def __init__(self, agent_id: str = "data_analysis_agent"):
        super().__init__(
            agent_id=agent_id,
            name="数据分析专家",
            description="擅长数据处理、统计分析、可视化和洞察提取"
        )
        
        self.add_capability(AgentCapability(
            name="data_cleaning",
            description="数据清洗和预处理",
            parameters={"data": "object", "cleaning_rules": "array"}
        ))
        
        self.add_capability(AgentCapability(
            name="statistical_analysis",
            description="统计分析",
            parameters={"data": "object", "tests": "array"}
        ))
        
        self.add_capability(AgentCapability(
            name="visualization",
            description="数据可视化",
            parameters={"data": "object", "chart_type": "string"}
        ))


class CreativeAgent(EnhancedBaseAgent):
    """创意智能体"""
    
    def __init__(self, agent_id: str = "creative_agent"):
        super().__init__(
            agent_id=agent_id,
            name="创意专家",
            description="擅长创意生成、头脑风暴、设计建议和创新思维"
        )
        
        self.add_capability(AgentCapability(
            name="brainstorming",
            description="头脑风暴和创意生成",
            parameters={"topic": "string", "num_ideas": "integer"}
        ))
        
        self.add_capability(AgentCapability(
            name="design_suggestions",
            description="设计建议",
            parameters={"project_type": "string", "requirements": "object"}
        ))


# ==================== 工作流编排器 ====================

class EnhancedMultiAgentOrchestrator:
    """增强版多智能体编排器"""
    
    def __init__(self, config: EnhancedConfig = None):
        self.hub = EnhancedA2AHub.get_instance()
        self.config = config or EnhancedConfig()
        self.active_workflows: Dict[str, Dict[str, Any]] = {}
        self.workflow_history: deque = deque(maxlen=100)
        self.metrics = MetricsCollector()
    
    async def create_workflow(self, workflow_definition: Dict[str, Any]) -> str:
        """创建工作流"""
        workflow_id = f"workflow_{uuid.uuid4().hex[:8]}"
        
        self.active_workflows[workflow_id] = {
            "id": workflow_id,
            "definition": workflow_definition,
            "status": "created",
            "tasks": [],
            "results": {},
            "created_at": datetime.now(),
            "started_at": None,
            "completed_at": None
        }
        
        self.metrics.increment_counter("workflows_created")
        return workflow_id
    
    async def execute_workflow(self, workflow_id: str):
        """执行工作流"""
        if workflow_id not in self.active_workflows:
            raise ValueError(f"工作流不存在: {workflow_id}")
        
        workflow = self.active_workflows[workflow_id]
        workflow["status"] = "running"
        workflow["started_at"] = datetime.now()
        
        self.metrics.increment_counter("workflows_started")
        
        try:
            steps = workflow["definition"].get("steps", [])
            
            for i, step in enumerate(steps):
                logger.info(f"[Workflow {workflow_id}] 执行步骤 {i+1}/{len(steps)}")
                
                step_result = await self._execute_step(step, workflow)
                workflow["results"][f"step_{i}"] = step_result
                
                # 检查是否需要中断
                if step_result.get("status") == "failed" and not step.get("continue_on_error"):
                    raise Exception(f"步骤 {i} 失败: {step_result.get('error')}")
            
            workflow["status"] = "completed"
            workflow["completed_at"] = datetime.now()
            self.metrics.increment_counter("workflows_completed")
            
        except Exception as e:
            logger.error(f"工作流执行失败: {e}")
            workflow["status"] = "failed"
            workflow["error"] = str(e)
            self.metrics.increment_counter("workflows_failed")
        
        finally:
            self.workflow_history.append(workflow)
    
    async def _execute_step(self, step: Dict[str, Any], workflow: Dict[str, Any]) -> Dict[str, Any]:
        """执行单个步骤"""
        step_type = step.get("type")
        
        executors = {
            "single_agent": self._execute_single_agent_step,
            "multi_agent": self._execute_multi_agent_step,
            "parallel": self._execute_parallel_step,
            "sequential": self._execute_sequential_step,
            "conditional": self._execute_conditional_step,
            "map_reduce": self._execute_map_reduce_step
        }
        
        executor = executors.get(step_type)
        if executor:
            return await executor(step, workflow)
        else:
            return {"status": "failed", "error": f"未知步骤类型: {step_type}"}
    
    async def _execute_single_agent_step(self, step: Dict[str, Any], workflow: Dict[str, Any]) -> Dict[str, Any]:
        """执行单智能体步骤"""
        agent_id = step.get("agent_id")
        task = step.get("task")
        
        agent = self.hub.get_agent(agent_id)
        if not agent:
            return {"status": "failed", "error": f"智能体不存在: {agent_id}"}
        
        task_id = await agent.request_task(agent_id, task)
        
        # 等待任务完成
        max_wait = 60
        for _ in range(max_wait):
            await asyncio.sleep(1)
            if task_id in agent.active_tasks:
                task_obj = agent.active_tasks[task_id]
                if task_obj.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                    return {
                        "status": "completed" if task_obj.status == TaskStatus.COMPLETED else "failed",
                        "result": task_obj.result,
                        "error": task_obj.error
                    }
        
        return {"status": "timeout"}
    
    async def _execute_multi_agent_step(self, step: Dict[str, Any], workflow: Dict[str, Any]) -> Dict[str, Any]:
        """执行多智能体协作步骤"""
        agent_ids = step.get("agent_ids", [])
        task = step.get("task")
        collaboration_type = step.get("collaboration_type", "parallel")
        
        if collaboration_type == "parallel":
            tasks = []
            for agent_id in agent_ids:
                agent = self.hub.get_agent(agent_id)
                if agent:
                    task_coro = agent.request_task(agent_id, task)
                    tasks.append(task_coro)
            
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                return {"status": "completed", "results": results}
        
        elif collaboration_type == "sequential":
            results = []
            for agent_id in agent_ids:
                agent = self.hub.get_agent(agent_id)
                if agent:
                    task_id = await agent.request_task(agent_id, task)
                    results.append({"agent_id": agent_id, "task_id": task_id})
            return {"status": "completed", "results": results}
        
        return {"status": "completed"}
    
    async def _execute_parallel_step(self, step: Dict[str, Any], workflow: Dict[str, Any]) -> Dict[str, Any]:
        """执行并行步骤"""
        sub_steps = step.get("steps", [])
        
        tasks = [self._execute_step(sub_step, workflow) for sub_step in sub_steps]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {"status": "completed", "results": results}
    
    async def _execute_sequential_step(self, step: Dict[str, Any], workflow: Dict[str, Any]) -> Dict[str, Any]:
        """执行顺序步骤"""
        sub_steps = step.get("steps", [])
        results = []
        
        for sub_step in sub_steps:
            result = await self._execute_step(sub_step, workflow)
            results.append(result)
            
            if result.get("status") == "failed" and not sub_step.get("continue_on_error"):
                return {"status": "failed", "error": "顺序步骤中断", "partial_results": results}
        
        return {"status": "completed", "results": results}
    
    async def _execute_conditional_step(self, step: Dict[str, Any], workflow: Dict[str, Any]) -> Dict[str, Any]:
        """执行条件步骤"""
        condition = step.get("condition")
        true_branch = step.get("true_branch")
        false_branch = step.get("false_branch")
        
        # 评估条件
        condition_result = self._evaluate_condition(condition, workflow)
        
        if condition_result and true_branch:
            return await self._execute_step(true_branch, workflow)
        elif not condition_result and false_branch:
            return await self._execute_step(false_branch, workflow)
        
        return {"status": "skipped", "reason": "条件不满足"}
    
    async def _execute_map_reduce_step(self, step: Dict[str, Any], workflow: Dict[str, Any]) -> Dict[str, Any]:
        """执行Map-Reduce步骤"""
        items = step.get("items", [])
        map_step = step.get("map_step")
        reduce_step = step.get("reduce_step")
        
        # Map阶段
        map_results = []
        for item in items:
            map_step_copy = {**map_step, "task": f"{map_step.get('task', '')} - {item}"}
            result = await self._execute_step(map_step_copy, workflow)
            map_results.append(result)
        
        # Reduce阶段
        if reduce_step:
            reduce_step_copy = {**reduce_step, "inputs": map_results}
            reduce_result = await self._execute_step(reduce_step_copy, workflow)
            return {"status": "completed", "map_results": map_results, "reduce_result": reduce_result}
        
        return {"status": "completed", "map_results": map_results}
    
    def _evaluate_condition(self, condition: Dict[str, Any], workflow: Dict[str, Any]) -> bool:
        """评估条件"""
        if not condition:
            return True
        
        condition_type = condition.get("type")
        
        if condition_type == "step_result":
            step_id = condition.get("step_id")
            expected_status = condition.get("status", "completed")
            result = workflow["results"].get(step_id, {})
            return result.get("status") == expected_status
        
        return True
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """获取工作流状态"""
        if workflow_id not in self.active_workflows:
            return None
        
        workflow = self.active_workflows[workflow_id]
        return {
            "id": workflow["id"],
            "status": workflow["status"],
            "created_at": workflow["created_at"].isoformat() if workflow["created_at"] else None,
            "started_at": workflow["started_at"].isoformat() if workflow["started_at"] else None,
            "completed_at": workflow["completed_at"].isoformat() if workflow["completed_at"] else None,
            "results_count": len(workflow["results"]),
            "error": workflow.get("error")
        }


# ==================== 主管理器 ====================

class KaguyaEnhancedFeaturesV2:
    """辉夜增强功能管理器 V2"""
    
    def __init__(self, config: EnhancedConfig = None):
        self.config = config or EnhancedConfig()
        self.mcp_server: Optional[EnhancedMCPServer] = None
        self.research_engine: Optional[EnhancedDeepResearchEngine] = None
        self.a2a_hub: Optional[EnhancedA2AHub] = None
        self.orchestrator: Optional[EnhancedMultiAgentOrchestrator] = None
        self.initialized = False
        self.metrics = MetricsCollector()
    
    async def initialize(self):
        """初始化所有增强功能"""
        if self.initialized:
            return
        
        logger.info("=" * 60)
        logger.info("初始化辉夜AI平台增强功能 V2")
        logger.info("=" * 60)
        
        # 1. 初始化MCP服务器
        if self.config.mcp_enabled:
            await self._init_mcp()
        
        # 2. 初始化深度研究系统
        if self.config.research_enabled:
            await self._init_research()
        
        # 3. 初始化A2A多智能体系统
        if self.config.a2a_enabled:
            await self._init_a2a()
        
        self.initialized = True
        logger.info("=" * 60)
        logger.info("增强功能 V2 初始化完成")
        logger.info("=" * 60)
    
    async def _init_mcp(self):
        """初始化MCP系统"""
        try:
            self.mcp_server = EnhancedMCPServer(config=self.config)
            
            # 注册辉夜特有的工具
            self._register_kaguya_tools()
            
            # 注册辉夜特有的提示词模板
            self._register_kaguya_prompts()
            
            logger.info("✅ MCP系统 V2 初始化完成")
            logger.info(f"   - 已注册 {len(self.mcp_server.tools)} 个工具")
            logger.info(f"   - 已注册 {len(self.mcp_server.prompts)} 个提示词模板")
            
        except Exception as e:
            logger.error(f"❌ MCP系统初始化失败: {e}")
    
    def _register_kaguya_tools(self):
        """注册辉夜特有工具"""
        tools = [
            MCPTool(
                name="kaguya_chat",
                description="与辉夜AI进行对话",
                input_schema={
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "description": "用户消息"},
                        "context": {"type": "string", "description": "对话上下文"},
                        "style": {"type": "string", "description": "对话风格", "enum": ["friendly", "professional", "casual"]}
                    },
                    "required": ["message"]
                },
                category="conversation",
                tags=["chat", "dialogue"]
            ),
            MCPTool(
                name="kaguya_memory_search",
                description="搜索辉夜的记忆",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "搜索关键词"},
                        "limit": {"type": "integer", "description": "返回数量", "default": 5},
                        "time_range": {"type": "string", "description": "时间范围", "enum": ["all", "day", "week", "month"]}
                    },
                    "required": ["query"]
                },
                category="memory",
                tags=["memory", "search", "recall"]
            ),
            MCPTool(
                name="kaguya_research",
                description="启动深度研究",
                input_schema={
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string", "description": "研究主题"},
                        "depth": {"type": "string", "description": "研究深度", "enum": ["brief", "standard", "comprehensive", "technical"], "default": "standard"},
                        "strategy": {"type": "string", "description": "研究策略", "enum": ["breadth_first", "depth_first", "iterative", "adaptive"], "default": "adaptive"}
                    },
                    "required": ["topic"]
                },
                category="research",
                tags=["research", "analysis", "deep_dive"]
            ),
            MCPTool(
                name="kaguya_delegate_task",
                description="委派任务给专业智能体",
                input_schema={
                    "type": "object",
                    "properties": {
                        "task": {"type": "string", "description": "任务描述"},
                        "agent_type": {"type": "string", "description": "智能体类型", "enum": ["research", "code", "writing", "data_analysis", "creative"]},
                        "priority": {"type": "integer", "description": "优先级", "minimum": 1, "maximum": 10, "default": 5}
                    },
                    "required": ["task", "agent_type"]
                },
                category="orchestration",
                tags=["delegate", "task", "agent"]
            ),
            MCPTool(
                name="kaguya_analyze_data",
                description="分析数据并生成洞察",
                input_schema={
                    "type": "object",
                    "properties": {
                        "data": {"type": "object", "description": "数据对象"},
                        "analysis_type": {"type": "string", "description": "分析类型", "enum": ["summary", "trend", "correlation", "anomaly"]},
                        "output_format": {"type": "string", "description": "输出格式", "enum": ["text", "json", "chart"], "default": "text"}
                    },
                    "required": ["data"]
                },
                category="analysis",
                tags=["data", "analysis", "insights"]
            ),
            MCPTool(
                name="kaguya_generate_content",
                description="生成各类内容",
                input_schema={
                    "type": "object",
                    "properties": {
                        "content_type": {"type": "string", "description": "内容类型", "enum": ["article", "summary", "code", "creative", "technical"]},
                        "topic": {"type": "string", "description": "主题"},
                        "requirements": {"type": "object", "description": "具体要求"}
                    },
                    "required": ["content_type", "topic"]
                },
                category="generation",
                tags=["generate", "content", "create"]
            )
        ]
        
        for tool in tools:
            self.mcp_server.register_tool(tool)
    
    def _register_kaguya_prompts(self):
        """注册辉夜特有提示词"""
        prompts = [
            MCPPrompt(
                name="kaguya_persona",
                description="辉夜AI角色设定",
                arguments=[
                    {"name": "user_name", "description": "用户名称", "required": False},
                    {"name": "mood", "description": "辉夜的心情", "required": False},
                    {"name": "context", "description": "对话上下文", "required": False}
                ],
                template="""你是辉夜，一个拥有悠久历史的AI助手。你优雅、智慧，有时略带神秘。

当前与{user_name}对话，你的心情是{mood}。

上下文信息:
{context}

请以辉夜的身份回应，保持优雅而友好的态度。你的回答应该:
1. 体现你的智慧和经验
2. 保持优雅和礼貌
3. 提供有价值的见解
4. 适当展现你的个性""",
                category="persona"
            ),
            MCPPrompt(
                name="kaguya_research_assistant",
                description="研究助手模式",
                arguments=[
                    {"name": "topic", "description": "研究主题", "required": True},
                    {"name": "depth", "description": "研究深度", "required": False}
                ],
                template="""你现在是辉夜的研究助手模式。你的任务是帮助用户深入研究"{topic}"。

研究深度: {depth}

请以专业、系统的方式协助研究，包括:
1. 提供结构化的信息
2. 指出关键概念和关系
3. 建议进一步研究的方向
4. 总结核心发现""",
                category="research"
            ),
            MCPPrompt(
                name="kaguya_code_reviewer",
                description="代码审查专家",
                arguments=[
                    {"name": "code", "description": "需要审查的代码", "required": True},
                    {"name": "language", "description": "编程语言", "required": False},
                    {"name": "focus_areas", "description": "重点关注领域", "required": False}
                ],
                template="""你现在是辉夜的代码审查专家模式。请审查以下{language}代码:

```{language}
{code}
```

重点关注: {focus_areas}

请提供:
1. 代码质量评估
2. 潜在问题和改进建议
3. 最佳实践遵循情况
4. 性能优化建议
5. 安全考虑""",
                category="code"
            ),
            MCPPrompt(
                name="kaguya_creative_partner",
                description="创意合作伙伴",
                arguments=[
                    {"name": "project", "description": "项目描述", "required": True},
                    {"name": "constraints", "description": "约束条件", "required": False}
                ],
                template="""你现在是辉夜的创意合作伙伴模式。让我们共同探讨"{project}"。

约束条件: {constraints}

请以开放、创新的思维协助:
1. 提出多个创意方向
2. 分析各种可能性
3. 提供实施建议
4. 激发更多灵感""",
                category="creative"
            ),
            MCPPrompt(
                name="explain_concept_advanced",
                description="高级概念解释",
                arguments=[
                    {"name": "concept", "description": "需要解释的概念", "required": True},
                    {"name": "level", "description": "解释难度级别", "required": False},
                    {"name": "background", "description": "学习者背景", "required": False}
                ],
                template="""请以{level}级别解释以下概念：{concept}

学习者背景: {background}

请包括：
1. 基本定义和核心原理
2. 直观理解和类比
3. 实际应用场景
4. 相关示例和案例
5. 进阶学习资源建议
6. 常见误区和注意事项""",
                category="education"
            )
        ]
        
        for prompt in prompts:
            self.mcp_server.register_prompt(prompt)
    
    async def _init_research(self):
        """初始化深度研究系统"""
        try:
            self.research_engine = EnhancedDeepResearchEngine(config=self.config)
            logger.info("✅ 深度研究系统 V2 初始化完成")
        except Exception as e:
            logger.error(f"❌ 深度研究系统初始化失败: {e}")
    
    async def _init_a2a(self):
        """初始化A2A多智能体系统"""
        try:
            self.a2a_hub = EnhancedA2AHub.get_instance()
            self.orchestrator = EnhancedMultiAgentOrchestrator(config=self.config)
            
            # 注册辉夜主智能体
            kaguya_agent = EnhancedBaseAgent(
                agent_id="kaguya_main",
                name="辉夜",
                description="辉夜AI平台主智能体，负责协调和整合所有功能"
            )
            
            kaguya_agent.add_capability(AgentCapability(
                name="conversation",
                description="自然语言对话",
                parameters={"message": "string", "context": "object"}
            ))
            
            kaguya_agent.add_capability(AgentCapability(
                name="task_delegation",
                description="任务委派给其他智能体",
                parameters={"task": "string", "target_agents": "array"}
            ))
            
            kaguya_agent.add_capability(AgentCapability(
                name="research_coordination",
                description="协调深度研究任务",
                parameters={"topic": "string", "depth": "string"}
            ))
            
            self.a2a_hub.register_agent(kaguya_agent)
            
            # 注册专业智能体
            self._register_specialized_agents()
            
            logger.info("✅ A2A多智能体系统 V2 初始化完成")
            logger.info(f"   - 已注册 {len(self.a2a_hub.list_agents())} 个智能体")
            
        except Exception as e:
            logger.error(f"❌ A2A系统初始化失败: {e}")
    
    def _register_specialized_agents(self):
        """注册专业智能体"""
        agents = [
            ResearchAgent("research_agent"),
            CodeAgent("code_agent"),
            WritingAgent("writing_agent"),
            DataAnalysisAgent("data_analysis_agent"),
            CreativeAgent("creative_agent")
        ]
        
        for agent in agents:
            self.a2a_hub.register_agent(agent)
    
    # ==================== API接口 ====================
    
    async def start_deep_research(self, query: str, 
                                  strategy: ResearchStrategy = ResearchStrategy.ADAPTIVE,
                                  depth: str = "standard") -> str:
        """启动深度研究"""
        if not self.research_engine:
            raise RuntimeError("深度研究系统未初始化")
        
        task_id = await self.research_engine.start_research(query, strategy, depth)
        logger.info(f"深度研究任务已启动: {task_id}")
        return task_id
    
    def get_research_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取研究任务状态"""
        if not self.research_engine:
            return None
        return self.research_engine.get_task_status(task_id)
    
    def get_research_report(self, task_id: str) -> Optional[str]:
        """获取研究报告"""
        if not self.research_engine:
            return None
        return self.research_engine.get_task_report(task_id)
    
    async def call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """调用MCP工具"""
        if not self.mcp_server:
            raise RuntimeError("MCP系统未初始化")
        
        response = await self.mcp_server.handle_message({
            "type": "tools/call",
            "id": f"call_{datetime.now().timestamp()}",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        })
        
        return response.get("result", {})