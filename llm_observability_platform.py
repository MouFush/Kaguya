#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM Observability Platform - LLM可观测性平台
参考: Langfuse, Langsmith, Phoenix Arize

核心功能:
- 追踪(Tracing) - 完整的请求链路追踪
- 指标监控(Metrics) - Token使用量、延迟、成本
- 评估(Evaluation) - 自动化质量评估
- 提示词版本管理 - Prompt版本控制
- 数据集管理 - 测试数据集
"""

import asyncio
import json
import uuid
import time
import logging
from typing import Dict, List, Any, Optional, Callable, Union, AsyncIterator
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict
import statistics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SpanType(Enum):
    """追踪跨度类型"""
    LLM = "llm"
    RETRIEVER = "retriever"
    TOOL = "tool"
    CHAIN = "chain"
    AGENT = "agent"
    EMBEDDING = "embedding"


class TraceStatus(Enum):
    """追踪状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"


@dataclass
class TokenUsage:
    """Token使用量"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens
        }


@dataclass
class SpanMetrics:
    """跨度指标"""
    start_time: datetime
    end_time: Optional[datetime] = None
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    token_usage: TokenUsage = field(default_factory=TokenUsage)
    
    def finish(self):
        """完成跨度"""
        self.end_time = datetime.now()
        self.latency_ms = (self.end_time - self.start_time).total_seconds() * 1000
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "latency_ms": self.latency_ms,
            "cost_usd": self.cost_usd,
            "token_usage": self.token_usage.to_dict()
        }


@dataclass
class Span:
    """追踪跨度"""
    span_id: str
    trace_id: str
    parent_span_id: Optional[str]
    span_type: SpanType
    name: str
    input: Any
    output: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    metrics: SpanMetrics = field(default_factory=lambda: SpanMetrics(start_time=datetime.now()))
    status: TraceStatus = TraceStatus.PENDING
    error: Optional[str] = None
    children: List['Span'] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "parent_span_id": self.parent_span_id,
            "span_type": self.span_type.value,
            "name": self.name,
            "input": str(self.input)[:500] if self.input else None,
            "output": str(self.output)[:500] if self.output else None,
            "metadata": self.metadata,
            "metrics": self.metrics.to_dict(),
            "status": self.status.value,
            "error": self.error,
            "children_count": len(self.children)
        }


@dataclass
class Trace:
    """追踪记录"""
    trace_id: str
    name: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    spans: List[Span] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    status: TraceStatus = TraceStatus.PENDING
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "name": self.name,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "metadata": self.metadata,
            "span_count": len(self.spans),
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "status": self.status.value
        }


@dataclass
class PromptVersion:
    """提示词版本"""
    prompt_id: str
    version: str
    template: str
    variables: List[str]
    metadata: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)
    is_active: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "prompt_id": self.prompt_id,
            "version": self.version,
            "template": self.template[:200] + "..." if len(self.template) > 200 else self.template,
            "variables": self.variables,
            "created_at": self.created_at.isoformat(),
            "is_active": self.is_active
        }


@dataclass
class Dataset:
    """数据集"""
    dataset_id: str
    name: str
    description: str
    items: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "name": self.name,
            "description": self.description,
            "item_count": len(self.items),
            "created_at": self.created_at.isoformat()
        }


@dataclass
class EvaluationResult:
    """评估结果"""
    evaluation_id: str
    trace_id: str
    metric_name: str
    score: float
    comment: Optional[str] = None
    evaluator: str = "auto"
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "evaluation_id": self.evaluation_id,
            "trace_id": self.trace_id,
            "metric_name": self.metric_name,
            "score": self.score,
            "comment": self.comment,
            "evaluator": self.evaluator,
            "timestamp": self.timestamp.isoformat()
        }


class LLMObservabilityPlatform:
    """LLM可观测性平台"""
    
    def __init__(self):
        self.traces: Dict[str, Trace] = {}
        self.spans: Dict[str, Span] = {}
        self.prompts: Dict[str, List[PromptVersion]] = defaultdict(list)
        self.datasets: Dict[str, Dataset] = {}
        self.evaluations: List[EvaluationResult] = []
        
        # 统计指标
        self.metrics_history: List[Dict] = []
        
        # 回调函数
        self.trace_callbacks: List[Callable] = []
        
    # ==================== 追踪管理 ====================
    
    def start_trace(self, name: str, user_id: str = None, 
                   session_id: str = None,
                   metadata: Dict = None) -> Trace:
        """开始追踪"""
        trace_id = f"trace_{uuid.uuid4().hex[:12]}"
        trace = Trace(
            trace_id=trace_id,
            name=name,
            user_id=user_id,
            session_id=session_id,
            metadata=metadata or {}
        )
        self.traces[trace_id] = trace
        logger.info(f"开始追踪: {trace_id} ({name})")
        return trace
    
    def end_trace(self, trace_id: str, status: TraceStatus = TraceStatus.SUCCESS):
        """结束追踪"""
        trace = self.traces.get(trace_id)
        if trace:
            trace.end_time = datetime.now()
            trace.status = status
            
            # 触发回调
            for callback in self.trace_callbacks:
                try:
                    callback(trace)
                except Exception as e:
                    logger.error(f"追踪回调错误: {e}")
            
            logger.info(f"结束追踪: {trace_id} ({status.value})")
    
    def start_span(self, trace_id: str, span_type: SpanType, name: str,
                  input_data: Any, parent_span_id: str = None,
                  metadata: Dict = None) -> Span:
        """开始跨度"""
        span_id = f"span_{uuid.uuid4().hex[:12]}"
        span = Span(
            span_id=span_id,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            span_type=span_type,
            name=name,
            input=input_data,
            metadata=metadata or {},
            status=TraceStatus.RUNNING
        )
        self.spans[span_id] = span
        
        # 添加到追踪
        trace = self.traces.get(trace_id)
        if trace:
            trace.spans.append(span)
        
        return span
    
    def end_span(self, span_id: str, output: Any = None, 
                error: str = None):
        """结束跨度"""
        span = self.spans.get(span_id)
        if span:
            span.output = output
            span.error = error
            span.metrics.finish()
            span.status = TraceStatus.ERROR if error else TraceStatus.SUCCESS
    
    def update_span_tokens(self, span_id: str, token_usage: TokenUsage):
        """更新跨度Token使用量"""
        span = self.spans.get(span_id)
        if span:
            span.metrics.token_usage = token_usage
            # 计算成本 (简化计算)
            span.metrics.cost_usd = (
                token_usage.prompt_tokens * 0.00001 +
                token_usage.completion_tokens * 0.00003
            )
    
    # ==================== 装饰器 ====================
    
    def trace_function(self, name: str = None, span_type: SpanType = SpanType.LLM):
        """追踪函数装饰器"""
        def decorator(func):
            async def async_wrapper(*args, **kwargs):
                trace_name = name or func.__name__
                trace = self.start_trace(trace_name)
                span = self.start_span(
                    trace.trace_id, span_type, trace_name,
                    input_data={"args": str(args), "kwargs": str(kwargs)}
                )
                
                try:
                    result = await func(*args, **kwargs)
                    self.end_span(span.span_id, output=result)
                    self.end_trace(trace.trace_id, TraceStatus.SUCCESS)
                    return result
                except Exception as e:
                    self.end_span(span.span_id, error=str(e))
                    self.end_trace(trace.trace_id, TraceStatus.ERROR)
                    raise
            
            def sync_wrapper(*args, **kwargs):
                trace_name = name or func.__name__
                trace = self.start_trace(trace_name)
                span = self.start_span(
                    trace.trace_id, span_type, trace_name,
                    input_data={"args": str(args), "kwargs": str(kwargs)}
                )
                
                try:
                    result = func(*args, **kwargs)
                    self.end_span(span.span_id, output=result)
                    self.end_trace(trace.trace_id, TraceStatus.SUCCESS)
                    return result
                except Exception as e:
                    self.end_span(span.span_id, error=str(e))
                    self.end_trace(trace.trace_id, TraceStatus.ERROR)
                    raise
            
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        return decorator
    
    # ==================== 提示词管理 ====================
    
    def create_prompt(self, prompt_id: str, template: str, 
                     variables: List[str] = None,
                     metadata: Dict = None) -> PromptVersion:
        """创建提示词版本"""
        # 停用之前的版本
        for pv in self.prompts[prompt_id]:
            pv.is_active = False
        
        version = f"v{len(self.prompts[prompt_id]) + 1}"
        prompt_version = PromptVersion(
            prompt_id=prompt_id,
            version=version,
            template=template,
            variables=variables or [],
            metadata=metadata or {},
            is_active=True
        )
        self.prompts[prompt_id].append(prompt_version)
        logger.info(f"创建提示词版本: {prompt_id}@{version}")
        return prompt_version
    
    def get_prompt(self, prompt_id: str, version: str = None) -> Optional[PromptVersion]:
        """获取提示词版本"""
        versions = self.prompts.get(prompt_id, [])
        if not versions:
            return None
        
        if version:
            for pv in versions:
                if pv.version == version:
                    return pv
            return None
        
        # 返回激活的版本
        for pv in versions:
            if pv.is_active:
                return pv
        return versions[-1] if versions else None
    
    def list_prompts(self) -> List[Dict]:
        """列出所有提示词"""
        result = []
        for prompt_id, versions in self.prompts.items():
            result.append({
                "prompt_id": prompt_id,
                "version_count": len(versions),
                "active_version": next((v.version for v in versions if v.is_active), None),
                "versions": [v.to_dict() for v in versions[-5:]]  # 最近5个版本
            })
        return result
    
    # ==================== 数据集管理 ====================
    
    def create_dataset(self, name: str, description: str = "") -> Dataset:
        """创建数据集"""
        dataset_id = f"dataset_{uuid.uuid4().hex[:12]}"
        dataset = Dataset(
            dataset_id=dataset_id,
            name=name,
            description=description
        )
        self.datasets[dataset_id] = dataset
        return dataset
    
    def add_dataset_item(self, dataset_id: str, item: Dict[str, Any]):
        """添加数据集项"""
        dataset = self.datasets.get(dataset_id)
        if dataset:
            dataset.items.append(item)
    
    # ==================== 评估 ====================
    
    def evaluate_trace(self, trace_id: str, metric_name: str, 
                      score: float, comment: str = None,
                      evaluator: str = "auto") -> EvaluationResult:
        """评估追踪"""
        evaluation = EvaluationResult(
            evaluation_id=f"eval_{uuid.uuid4().hex[:8]}",
            trace_id=trace_id,
            metric_name=metric_name,
            score=score,
            comment=comment,
            evaluator=evaluator
        )
        self.evaluations.append(evaluation)
        return evaluation
    
    def run_auto_evaluation(self, trace_id: str) -> List[EvaluationResult]:
        """运行自动评估"""
        trace = self.traces.get(trace_id)
        if not trace:
            return []
        
        results = []
        
        # 查找LLM跨度
        llm_spans = [s for s in trace.spans if s.span_type == SpanType.LLM]
        for span in llm_spans:
            # 延迟评估
            if span.metrics.latency_ms < 1000:
                results.append(self.evaluate_trace(
                    trace_id, "latency", 1.0, "延迟优秀", "system"
                ))
            elif span.metrics.latency_ms < 3000:
                results.append(self.evaluate_trace(
                    trace_id, "latency", 0.7, "延迟良好", "system"
                ))
            else:
                results.append(self.evaluate_trace(
                    trace_id, "latency", 0.4, "延迟较高", "system"
                ))
            
            # Token效率评估
            if span.metrics.token_usage.total_tokens > 0:
                efficiency = span.metrics.token_usage.completion_tokens / span.metrics.token_usage.total_tokens
                results.append(self.evaluate_trace(
                    trace_id, "token_efficiency", efficiency, None, "system"
                ))
        
        return results
    
    # ==================== 分析和报告 ====================
    
    def get_trace_stats(self, start_time: datetime = None, 
                       end_time: datetime = None) -> Dict[str, Any]:
        """获取追踪统计"""
        traces = list(self.traces.values())
        
        if start_time:
            traces = [t for t in traces if t.start_time >= start_time]
        if end_time:
            traces = [t for t in traces if t.start_time <= end_time]
        
        if not traces:
            return {"total_traces": 0}
        
        # 计算指标
        total_latency = []
        total_tokens = []
        total_cost = []
        
        for trace in traces:
            for span in trace.spans:
                total_latency.append(span.metrics.latency_ms)
                total_tokens.append(span.metrics.token_usage.total_tokens)
                total_cost.append(span.metrics.cost_usd)
        
        return {
            "total_traces": len(traces),
            "total_spans": sum(len(t.spans) for t in traces),
            "avg_latency_ms": statistics.mean(total_latency) if total_latency else 0,
            "p95_latency_ms": statistics.quantiles(total_latency, n=20)[18] if len(total_latency) >= 20 else 0,
            "total_tokens": sum(total_tokens),
            "total_cost_usd": sum(total_cost),
            "success_rate": sum(1 for t in traces if t.status == TraceStatus.SUCCESS) / len(traces)
        }
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """获取仪表板数据"""
        now = datetime.now()
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)
        
        return {
            "last_24h": self.get_trace_stats(last_24h, now),
            "last_7d": self.get_trace_stats(last_7d, now),
            "all_time": self.get_trace_stats(),
            "recent_traces": [t.to_dict() for t in list(self.traces.values())[-10:]],
            "prompts": self.list_prompts(),
            "datasets": [d.to_dict() for d in self.datasets.values()],
            "evaluations": [e.to_dict() for e in self.evaluations[-20:]]
        }
    
    def export_trace(self, trace_id: str, format: str = "json") -> str:
        """导出追踪"""
        trace = self.traces.get(trace_id)
        if not trace:
            return ""
        
        if format == "json":
            return json.dumps(trace.to_dict(), indent=2, ensure_ascii=False)
        
        return ""


# ==================== 全局实例 ====================

_default_observability_platform: Optional[LLMObservabilityPlatform] = None


def get_observability_platform() -> LLMObservabilityPlatform:
    """获取默认可观测性平台"""
    global _default_observability_platform
    if _default_observability_platform is None:
        _default_observability_platform = LLMObservabilityPlatform()
    return _default_observability_platform


# ==================== 使用示例 ====================

async def example_usage():
    """使用示例"""
    platform = get_observability_platform()
    
    # 创建提示词
    prompt = platform.create_prompt(
        "qa_prompt",
        "Question: {question}\nAnswer: ",
        variables=["question"]
    )
    
    # 开始追踪
    trace = platform.start_trace(
        "问答系统",
        user_id="user_123",
        metadata={"source": "web"}
    )
    
    # 创建LLM跨度
    span = platform.start_span(
        trace.trace_id,
        SpanType.LLM,
        "gpt-4调用",
        input_data="什么是人工智能？"
    )
    
    # 模拟LLM调用
    await asyncio.sleep(0.5)
    
    # 更新Token使用量
    platform.update_span_tokens(
        span.span_id,
        TokenUsage(prompt_tokens=20, completion_tokens=100, total_tokens=120)
    )
    
    # 结束跨度
    platform.end_span(
        span.span_id,
        output="人工智能是模拟人类智能的技术..."
    )
    
    # 结束追踪
    platform.end_trace(trace.trace_id)
    
    # 自动评估
    evaluations = platform.run_auto_evaluation(trace.trace_id)
    print(f"自动评估结果: {len(evaluations)} 项")
    
    # 获取仪表板数据
    dashboard = platform.get_dashboard_data()
    print(f"\n仪表板数据:")
    print(f"  24小时追踪数: {dashboard['last_24h']['total_traces']}")
    print(f"  平均延迟: {dashboard['last_24h']['avg_latency_ms']:.2f}ms")
    print(f"  成功率: {dashboard['last_24h']['success_rate']*100:.1f}%")


if __name__ == "__main__":
    asyncio.run(example_usage())
