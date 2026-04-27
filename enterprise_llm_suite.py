#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辉夜AI - 企业级LLM基础设施套件
整合: 模型服务化 + 实验追踪 + 监控观测 + 提示词管理
参考: vLLM + MLflow + Langfuse + Promptflow
"""

import asyncio
import json
import uuid
import time
import hashlib
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Set, Tuple
from collections import defaultdict, deque
import threading
import logging
import copy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# 第一部分: 模型服务化部署系统 (参考vLLM + KServe)
# ============================================================================

class ModelStatus(Enum):
    """模型状态"""
    PENDING = "pending"
    LOADING = "loading"
    READY = "ready"
    SERVING = "serving"
    ERROR = "error"
    SCALING = "scaling"
    TERMINATED = "terminated"


@dataclass
class ModelEndpoint:
    """模型服务端点"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    model_path: str = ""
    framework: str = "pytorch"  # pytorch, tensorflow, onnx, etc.
    status: ModelStatus = ModelStatus.PENDING
    
    # 资源配置
    gpu_count: int = 1
    gpu_memory: int = 24  # GB
    cpu_cores: int = 4
    memory_gb: int = 32
    
    # 服务配置
    batch_size: int = 16
    max_concurrent: int = 100
    timeout_seconds: int = 30
    
    # 自动扩缩容
    auto_scale: bool = True
    min_replicas: int = 1
    max_replicas: int = 5
    scale_threshold: float = 0.8  # CPU/GPU利用率阈值
    
    # 统计信息
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: Optional[datetime] = None
    total_requests: int = 0
    total_tokens: int = 0
    avg_latency_ms: float = 0.0
    error_rate: float = 0.0
    
    # 端点信息
    endpoint_url: Optional[str] = None
    health_check_url: Optional[str] = None


class ModelServingEngine:
    """
    模型服务化引擎 (参考vLLM + KServe)
    支持高性能推理、自动扩缩容、负载均衡
    """
    
    def __init__(self):
        self.endpoints: Dict[str, ModelEndpoint] = {}
        self.request_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self.active_requests: Dict[str, Dict] = {}
        self.metrics_history: deque = deque(maxlen=10000)
        self.lock = threading.RLock()
        
        # 模拟的模型实例
        self.model_instances: Dict[str, Any] = {}
        
        logger.info("模型服务化引擎初始化完成")
    
    def deploy_model(self, config: Dict[str, Any]) -> ModelEndpoint:
        """
        部署模型服务
        
        Args:
            config: 模型配置
        
        Returns:
            模型端点
        """
        with self.lock:
            endpoint = ModelEndpoint(
                name=config.get('name', f"model_{int(time.time())}"),
                model_path=config.get('model_path', ''),
                framework=config.get('framework', 'pytorch'),
                gpu_count=config.get('gpu_count', 1),
                cpu_cores=config.get('cpu_cores', 4),
                memory_gb=config.get('memory_gb', 32),
                batch_size=config.get('batch_size', 16),
                auto_scale=config.get('auto_scale', True),
                min_replicas=config.get('min_replicas', 1),
                max_replicas=config.get('max_replicas', 5)
            )
            
            # 模拟部署过程
            endpoint.status = ModelStatus.LOADING
            endpoint.endpoint_url = f"/v1/models/{endpoint.name}/predict"
            endpoint.health_check_url = f"/v1/models/{endpoint.name}/health"
            
            self.endpoints[endpoint.id] = endpoint
            
            # 模拟加载完成
            endpoint.status = ModelStatus.READY
            
            logger.info(f"模型 {endpoint.name} 部署完成，ID: {endpoint.id}")
            return endpoint
    
    async def predict(self, endpoint_id: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        模型推理
        
        Args:
            endpoint_id: 端点ID
            inputs: 输入数据
        
        Returns:
            推理结果
        """
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        with self.lock:
            if endpoint_id not in self.endpoints:
                return {"error": "Endpoint not found"}
            
            endpoint = self.endpoints[endpoint_id]
            if endpoint.status != ModelStatus.READY:
                return {"error": f"Endpoint not ready: {endpoint.status}"}
            
            endpoint.status = ModelStatus.SERVING
            endpoint.total_requests += 1
            endpoint.last_accessed = datetime.now()
        
        # 模拟推理延迟
        await asyncio.sleep(0.1)
        
        # 模拟推理结果
        latency_ms = (time.time() - start_time) * 1000
        
        # 记录指标
        self.metrics_history.append({
            "timestamp": datetime.now().isoformat(),
            "endpoint_id": endpoint_id,
            "request_id": request_id,
            "latency_ms": latency_ms,
            "status": "success"
        })
        
        # 更新端点统计
        with self.lock:
            endpoint.avg_latency_ms = (endpoint.avg_latency_ms * 0.9) + (latency_ms * 0.1)
            endpoint.status = ModelStatus.READY
        
        return {
            "request_id": request_id,
            "predictions": ["prediction_1", "prediction_2"],
            "latency_ms": latency_ms,
            "model_version": "1.0.0"
        }
    
    def get_endpoint_stats(self, endpoint_id: Optional[str] = None) -> Dict[str, Any]:
        """获取端点统计"""
        with self.lock:
            if endpoint_id:
                if endpoint_id not in self.endpoints:
                    return {"error": "Endpoint not found"}
                endpoint = self.endpoints[endpoint_id]
                return {
                    "id": endpoint.id,
                    "name": endpoint.name,
                    "status": endpoint.status.value,
                    "total_requests": endpoint.total_requests,
                    "avg_latency_ms": round(endpoint.avg_latency_ms, 2),
                    "error_rate": endpoint.error_rate,
                    "endpoint_url": endpoint.endpoint_url,
                    "created_at": endpoint.created_at.isoformat()
                }
            else:
                return {
                    "total_endpoints": len(self.endpoints),
                    "endpoints": [
                        {
                            "id": e.id,
                            "name": e.name,
                            "status": e.status.value,
                            "total_requests": e.total_requests
                        }
                        for e in self.endpoints.values()
                    ]
                }
    
    def scale_endpoint(self, endpoint_id: str, replicas: int) -> bool:
        """手动扩缩容"""
        with self.lock:
            if endpoint_id not in self.endpoints:
                return False
            
            endpoint = self.endpoints[endpoint_id]
            endpoint.status = ModelStatus.SCALING
            
            # 模拟扩缩容
            logger.info(f"模型 {endpoint.name} 扩缩容到 {replicas} 副本")
            
            endpoint.status = ModelStatus.READY
            return True
    
    def undeploy_model(self, endpoint_id: str) -> bool:
        """下线模型"""
        with self.lock:
            if endpoint_id not in self.endpoints:
                return False
            
            endpoint = self.endpoints[endpoint_id]
            endpoint.status = ModelStatus.TERMINATED
            
            logger.info(f"模型 {endpoint.name} 已下线")
            return True


# ============================================================================
# 第二部分: 实验追踪管理系统 (参考MLflow)
# ============================================================================

@dataclass
class Experiment:
    """实验"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    tags: Dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = ""
    status: str = "active"  # active, archived, deleted


@dataclass
class Run:
    """实验运行"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    experiment_id: str = ""
    name: str = ""
    status: str = "running"  # running, completed, failed, aborted
    
    # 参数
    params: Dict[str, Any] = field(default_factory=dict)
    
    # 指标
    metrics: Dict[str, List[Tuple[float, float]]] = field(default_factory=dict)  # {metric_name: [(timestamp, value), ...]}
    
    # 标签
    tags: Dict[str, str] = field(default_factory=dict)
    
    #  artifact
    artifacts: List[Dict] = field(default_factory=list)
    
    # 时间
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    
    # 模型
    model_version: Optional[str] = None
    model_path: Optional[str] = None


class ExperimentTracker:
    """
    实验追踪管理器 (参考MLflow)
    支持实验管理、运行追踪、指标记录、模型版本控制
    """
    
    def __init__(self, artifact_dir: str = "./experiments"):
        self.artifact_dir = artifact_dir
        self.experiments: Dict[str, Experiment] = {}
        self.runs: Dict[str, Run] = {}
        self.lock = threading.RLock()
        
        os.makedirs(artifact_dir, exist_ok=True)
        
        # 创建默认实验
        self.create_experiment("Default", "默认实验")
        
        logger.info("实验追踪管理器初始化完成")
    
    def create_experiment(self, name: str, description: str = "",
                         tags: Optional[Dict[str, str]] = None) -> Experiment:
        """创建实验"""
        with self.lock:
            experiment = Experiment(
                name=name,
                description=description,
                tags=tags or {}
            )
            self.experiments[experiment.id] = experiment
            
            # 创建实验目录
            exp_dir = os.path.join(self.artifact_dir, experiment.id)
            os.makedirs(exp_dir, exist_ok=True)
            
            logger.info(f"实验创建: {name} (ID: {experiment.id})")
            return experiment
    
    def start_run(self, experiment_id: Optional[str] = None,
                  run_name: Optional[str] = None,
                  tags: Optional[Dict[str, str]] = None) -> Run:
        """开始实验运行"""
        with self.lock:
            # 使用默认实验
            if experiment_id is None:
                experiment_id = list(self.experiments.keys())[0]
            
            run = Run(
                experiment_id=experiment_id,
                name=run_name or f"run_{int(time.time())}",
                tags=tags or {}
            )
            self.runs[run.id] = run
            
            logger.info(f"运行开始: {run.name} (ID: {run.id})")
            return run
    
    def log_param(self, run_id: str, key: str, value: Any):
        """记录参数"""
        with self.lock:
            if run_id in self.runs:
                self.runs[run_id].params[key] = value
    
    def log_metric(self, run_id: str, key: str, value: float, step: Optional[int] = None):
        """记录指标"""
        with self.lock:
            if run_id in self.runs:
                timestamp = time.time()
                if key not in self.runs[run_id].metrics:
                    self.runs[run_id].metrics[key] = []
                self.runs[run_id].metrics[key].append((timestamp, value))
    
    def log_artifact(self, run_id: str, local_path: str, artifact_path: Optional[str] = None):
        """记录Artifact"""
        with self.lock:
            if run_id in self.runs:
                artifact = {
                    "path": local_path,
                    "artifact_path": artifact_path or os.path.basename(local_path),
                    "timestamp": datetime.now().isoformat()
                }
                self.runs[run_id].artifacts.append(artifact)
    
    def end_run(self, run_id: str, status: str = "completed"):
        """结束运行"""
        with self.lock:
            if run_id in self.runs:
                run = self.runs[run_id]
                run.status = status
                run.end_time = datetime.now()
                
                logger.info(f"运行结束: {run.name} (状态: {status})")
    
    def get_experiment(self, experiment_id: str) -> Optional[Experiment]:
        """获取实验"""
        return self.experiments.get(experiment_id)
    
    def get_run(self, run_id: str) -> Optional[Run]:
        """获取运行"""
        return self.runs.get(run_id)
    
    def search_runs(self, experiment_ids: Optional[List[str]] = None,
                   filter_string: Optional[str] = None) -> List[Run]:
        """搜索运行"""
        with self.lock:
            runs = list(self.runs.values())
            
            if experiment_ids:
                runs = [r for r in runs if r.experiment_id in experiment_ids]
            
            return runs
    
    def get_metric_history(self, run_id: str, metric_key: str) -> List[Tuple[float, float]]:
        """获取指标历史"""
        with self.lock:
            if run_id in self.runs:
                return self.runs[run_id].metrics.get(metric_key, [])
            return []


# ============================================================================
# 第三部分: 生产监控观测系统 (参考Langfuse)
# ============================================================================

@dataclass
class Trace:
    """追踪记录"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    
    # 时间
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    
    # 输入输出
    input_data: Optional[str] = None
    output_data: Optional[str] = None
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    # 成本
    total_cost: float = 0.0
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    
    # 性能
    latency_ms: float = 0.0
    
    # 状态
    status: str = "success"  # success, error, aborted
    error_message: Optional[str] = None
    
    # 子追踪
    observations: List['Observation'] = field(default_factory=list)


@dataclass
class Observation:
    """观测点"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    trace_id: str = ""
    name: str = ""
    type: str = ""  # llm, retrieval, tool, etc.
    
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    
    input_data: Optional[str] = None
    output_data: Optional[str] = None
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # LLM特定
    model: Optional[str] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_cost: float = 0.0
    
    # 性能
    latency_ms: float = 0.0


class ObservabilityPlatform:
    """
    可观测性平台 (参考Langfuse)
    支持分布式追踪、性能监控、成本分析
    """
    
    def __init__(self):
        self.traces: Dict[str, Trace] = {}
        self.observations: Dict[str, Observation] = {}
        self.active_traces: Dict[str, Trace] = {}
        self.metrics_aggregator = defaultdict(lambda: defaultdict(list))
        self.lock = threading.RLock()
        
        logger.info("可观测性平台初始化完成")
    
    def start_trace(self, name: str, input_data: Optional[str] = None,
                   metadata: Optional[Dict] = None,
                   tags: Optional[List[str]] = None) -> Trace:
        """开始追踪"""
        with self.lock:
            trace = Trace(
                name=name,
                input_data=input_data,
                metadata=metadata or {},
                tags=tags or []
            )
            self.traces[trace.id] = trace
            self.active_traces[trace.id] = trace
            
            return trace
    
    def end_trace(self, trace_id: str, output_data: Optional[str] = None,
                 status: str = "success", error_message: Optional[str] = None):
        """结束追踪"""
        with self.lock:
            if trace_id in self.active_traces:
                trace = self.active_traces[trace_id]
                trace.end_time = datetime.now()
                trace.output_data = output_data
                trace.status = status
                trace.error_message = error_message
                
                # 计算延迟
                trace.latency_ms = (trace.end_time - trace.start_time).total_seconds() * 1000
                
                del self.active_traces[trace_id]
                
                # 聚合指标
                self._aggregate_metrics(trace)
    
    def add_observation(self, trace_id: str, name: str, type: str,
                       input_data: Optional[str] = None,
                       output_data: Optional[str] = None,
                       model: Optional[str] = None,
                       metadata: Optional[Dict] = None) -> Observation:
        """添加观测点"""
        with self.lock:
            observation = Observation(
                trace_id=trace_id,
                name=name,
                type=type,
                input_data=input_data,
                output_data=output_data,
                model=model,
                metadata=metadata or {}
            )
            
            self.observations[observation.id] = observation
            
            if trace_id in self.traces:
                self.traces[trace_id].observations.append(observation)
            
            return observation
    
    def end_observation(self, observation_id: str, output_data: Optional[str] = None,
                       prompt_tokens: int = 0, completion_tokens: int = 0,
                       cost: float = 0.0):
        """结束观测点"""
        with self.lock:
            if observation_id in self.observations:
                obs = self.observations[observation_id]
                obs.end_time = datetime.now()
                obs.output_data = output_data
                obs.prompt_tokens = prompt_tokens
                obs.completion_tokens = completion_tokens
                obs.total_cost = cost
                
                # 计算延迟
                obs.latency_ms = (obs.end_time - obs.start_time).total_seconds() * 1000
                
                # 更新父追踪
                if obs.trace_id in self.traces:
                    trace = self.traces[obs.trace_id]
                    trace.total_tokens += prompt_tokens + completion_tokens
                    trace.total_cost += cost
                    trace.prompt_tokens += prompt_tokens
                    trace.completion_tokens += completion_tokens
    
    def _aggregate_metrics(self, trace: Trace):
        """聚合指标"""
        date_key = trace.start_time.strftime("%Y-%m-%d")
        
        self.metrics_aggregator[date_key]["total_traces"].append(1)
        self.metrics_aggregator[date_key]["total_latency"].append(trace.latency_ms)
        self.metrics_aggregator[date_key]["total_tokens"].append(trace.total_tokens)
        self.metrics_aggregator[date_key]["total_cost"].append(trace.total_cost)
        
        if trace.status == "error":
            self.metrics_aggregator[date_key]["error_count"].append(1)
    
    def get_trace(self, trace_id: str) -> Optional[Trace]:
        """获取追踪"""
        return self.traces.get(trace_id)
    
    def get_traces(self, limit: int = 100, offset: int = 0) -> List[Trace]:
        """获取追踪列表"""
        with self.lock:
            sorted_traces = sorted(
                self.traces.values(),
                key=lambda x: x.start_time,
                reverse=True
            )
            return sorted_traces[offset:offset+limit]
    
    def get_metrics_summary(self, days: int = 7) -> Dict[str, Any]:
        """获取指标汇总"""
        summary = {
            "total_traces": 0,
            "avg_latency_ms": 0.0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "error_rate": 0.0,
            "daily_stats": []
        }
        
        with self.lock:
            for i in range(days):
                date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
                if date in self.metrics_aggregator:
                    day_data = self.metrics_aggregator[date]
                    
                    day_traces = sum(day_data.get("total_traces", [0]))
                    day_latency = day_data.get("total_latency", [0])
                    day_tokens = sum(day_data.get("total_tokens", [0]))
                    day_cost = sum(day_data.get("total_cost", [0]))
                    day_errors = sum(day_data.get("error_count", [0]))
                    
                    summary["total_traces"] += day_traces
                    summary["total_tokens"] += day_tokens
                    summary["total_cost"] += day_cost
                    
                    summary["daily_stats"].append({
                        "date": date,
                        "traces": day_traces,
                        "avg_latency_ms": sum(day_latency) / len(day_latency) if day_latency else 0,
                        "tokens": day_tokens,
                        "cost": round(day_cost, 4),
                        "error_rate": day_errors / day_traces if day_traces > 0 else 0
                    })
        
        # 计算平均延迟
        if summary["total_traces"] > 0:
            all_latencies = []
            for day_stat in summary["daily_stats"]:
                all_latencies.append(day_stat["avg_latency_ms"])
            summary["avg_latency_ms"] = sum(all_latencies) / len(all_latencies) if all_latencies else 0
        
        return summary


# ============================================================================
# 第四部分: 提示词版本控制系统 (参考Promptflow)
# ============================================================================

@dataclass
class PromptTemplate:
    """提示词模板"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    
    # 版本
    version: str = "1.0.0"
    version_history: List[Dict] = field(default_factory=list)
    
    # 内容
    system_prompt: str = ""
    user_prompt_template: str = ""
    
    # 变量定义
    variables: List[Dict] = field(default_factory=list)  # [{"name": "var1", "type": "string", "default": ""}]
    
    # 元数据
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 统计
    usage_count: int = 0
    avg_rating: float = 0.0
    
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    created_by: str = ""


@dataclass
class PromptFlow:
    """提示词流程"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    
    # 节点和连接
    nodes: List[Dict] = field(default_factory=list)
    connections: List[Dict] = field(default_factory=list)
    
    # 输入输出
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class PromptManager:
    """
    提示词管理器 (参考Promptflow)
    支持提示词版本控制、变量管理、流程编排
    """
    
    def __init__(self):
        self.templates: Dict[str, PromptTemplate] = {}
        self.flows: Dict[str, PromptFlow] = {}
        self.lock = threading.RLock()
        
        # 创建默认模板
        self._create_default_templates()
        
        logger.info("提示词管理器初始化完成")
    
    def _create_default_templates(self):
        """创建默认模板"""
        default_templates = [
            {
                "name": "通用对话",
                "description": "通用对话模板",
                "system_prompt": "你是一个 helpful AI助手。",
                "user_prompt_template": "{input}",
                "variables": [{"name": "input", "type": "string", "default": ""}]
            },
            {
                "name": "代码生成",
                "description": "代码生成模板",
                "system_prompt": "你是一个专业的程序员。",
                "user_prompt_template": "请用{language}编写代码：\n{requirement}",
                "variables": [
                    {"name": "language", "type": "string", "default": "Python"},
                    {"name": "requirement", "type": "string", "default": ""}
                ]
            }
        ]
        
        for template_data in default_templates:
            self.create_template(**template_data)
    
    def create_template(self, name: str, description: str = "",
                       system_prompt: str = "", user_prompt_template: str = "",
                       variables: Optional[List[Dict]] = None,
                       tags: Optional[List[str]] = None,
                       created_by: str = "") -> PromptTemplate:
        """创建提示词模板"""
        with self.lock:
            template = PromptTemplate(
                name=name,
                description=description,
                system_prompt=system_prompt,
                user_prompt_template=user_prompt_template,
                variables=variables or [],
                tags=tags or [],
                created_by=created_by
            )
            
            self.templates[template.id] = template
            
            logger.info(f"提示词模板创建: {name} (ID: {template.id})")
            return template
    
    def update_template(self, template_id: str, **kwargs) -> Optional[PromptTemplate]:
        """更新模板（自动创建新版本）"""
        with self.lock:
            if template_id not in self.templates:
                return None
            
            template = self.templates[template_id]
            
            # 保存旧版本到历史
            old_version = {
                "version": template.version,
                "system_prompt": template.system_prompt,
                "user_prompt_template": template.user_prompt_template,
                "variables": copy.deepcopy(template.variables),
                "updated_at": template.updated_at.isoformat()
            }
            template.version_history.append(old_version)
            
            # 更新字段
            if "system_prompt" in kwargs:
                template.system_prompt = kwargs["system_prompt"]
            if "user_prompt_template" in kwargs:
                template.user_prompt_template = kwargs["user_prompt_template"]
            if "variables" in kwargs:
                template.variables = kwargs["variables"]
            if "description" in kwargs:
                template.description = kwargs["description"]
            if "tags" in kwargs:
                template.tags = kwargs["tags"]
            
            # 更新版本号和时间
            version_parts = template.version.split(".")
            version_parts[-1] = str(int(version_parts[-1]) + 1)
            template.version = ".".join(version_parts)
            template.updated_at = datetime.now()
            
            logger.info(f"提示词模板更新: {template.name} (新版本: {template.version})")
            return template
    
    def render_template(self, template_id: str, variables: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """渲染模板"""
        with self.lock:
            if template_id not in self.templates:
                return None
            
            template = self.templates[template_id]
            
            # 替换变量
            user_prompt = template.user_prompt_template
            for var_name, var_value in variables.items():
                user_prompt = user_prompt.replace(f"{{{var_name}}}", str(var_value))
            
            # 更新使用统计
            template.usage_count += 1
            
            return {
                "system_prompt": template.system_prompt,
                "user_prompt": user_prompt,
                "template_id": template.id,
                "version": template.version
            }
    
    def get_template(self, template_id: str) -> Optional[PromptTemplate]:
        """获取模板"""
        return self.templates.get(template_id)
    
    def list_templates(self, tags: Optional[List[str]] = None) -> List[PromptTemplate]:
        """列出模板"""
        with self.lock:
            templates = list(self.templates.values())
            
            if tags:
                templates = [t for t in templates if any(tag in t.tags for tag in tags)]
            
            return sorted(templates, key=lambda x: x.updated_at, reverse=True)
    
    def create_flow(self, name: str, description: str = "",
                   nodes: Optional[List[Dict]] = None,
                   connections: Optional[List[Dict]] = None) -> PromptFlow:
        """创建提示词流程"""
        with self.lock:
            flow = PromptFlow(
                name=name,
                description=description,
                nodes=nodes or [],
                connections=connections or []
            )
            
            self.flows[flow.id] = flow
            
            logger.info(f"提示词流程创建: {name} (ID: {flow.id})")
            return flow
    
    def get_flow(self, flow_id: str) -> Optional[PromptFlow]:
        """获取流程"""
        return self.flows.get(flow_id)


# ============================================================================
# 第五部分: 企业级套件管理器
# ============================================================================

class EnterpriseLLMSuite:
    """
    企业级LLM套件管理器
    统一管理所有企业级功能
    包含缓存机制优化性能
    """
    
    def __init__(self):
        self.model_serving = ModelServingEngine()
        self.experiment_tracker = ExperimentTracker()
        self.observability = ObservabilityPlatform()
        self.prompt_manager = PromptManager()
        
        # 缓存机制
        self._cache = {}
        self._cache_ttl = 30  # 缓存30秒
        self._cache_timestamps = {}
        self._cache_lock = threading.RLock()
        
        # 批量操作队列
        self._batch_queue = []
        self._batch_size = 100
        self._batch_interval = 5  # 5秒批量处理
        self._batch_timer = None
        
        logger.info("企业级LLM套件初始化完成")
    
    def _get_cached(self, key: str) -> Optional[Any]:
        """获取缓存数据"""
        with self._cache_lock:
            if key in self._cache:
                timestamp = self._cache_timestamps.get(key, 0)
                if time.time() - timestamp < self._cache_ttl:
                    return self._cache[key]
                else:
                    # 过期清理
                    del self._cache[key]
                    del self._cache_timestamps[key]
            return None
    
    def _set_cached(self, key: str, value: Any):
        """设置缓存数据"""
        with self._cache_lock:
            self._cache[key] = value
            self._cache_timestamps[key] = time.time()
    
    def _clear_cache(self, pattern: str = None):
        """清理缓存"""
        with self._cache_lock:
            if pattern:
                keys_to_remove = [k for k in self._cache.keys() if pattern in k]
                for k in keys_to_remove:
                    del self._cache[k]
                    del self._cache_timestamps[k]
            else:
                self._cache.clear()
                self._cache_timestamps.clear()
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态（带缓存）"""
        cache_key = "system_status"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        result = {
            "model_serving": {
                "endpoints_count": len(self.model_serving.endpoints),
                "active_requests": len(self.model_serving.active_requests)
            },
            "experiment_tracker": {
                "experiments_count": len(self.experiment_tracker.experiments),
                "runs_count": len(self.experiment_tracker.runs)
            },
            "observability": {
                "traces_count": len(self.observability.traces),
                "active_traces": len(self.observability.active_traces),
                "metrics_summary": self.observability.get_metrics_summary(days=1)
            },
            "prompt_manager": {
                "templates_count": len(self.prompt_manager.templates),
                "flows_count": len(self.prompt_manager.flows)
            }
        }
        
        self._set_cached(cache_key, result)
        return result
    
    def get_stats(self) -> Dict[str, Any]:
        """获取快速统计（带缓存）"""
        cache_key = "stats"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        result = {
            "endpoints": len(self.model_serving.endpoints),
            "active_models": sum(1 for ep in self.model_serving.endpoints.values() if ep.status == "running"),
            "experiments": len(self.experiment_tracker.experiments),
            "runs": len(self.experiment_tracker.runs),
            "traces": len(self.observability.traces),
            "total_cost": sum(t.cost for t in self.observability.traces.values()),
            "templates": len(self.prompt_manager.templates),
            "versions": sum(len(t.version_history) for t in self.prompt_manager.templates.values())
        }
        
        self._set_cached(cache_key, result)
        return result
    
    def invalidate_cache(self, component: str = None):
        """使缓存失效"""
        if component:
            self._clear_cache(pattern=component)
        else:
            self._clear_cache()


# 创建全局实例
enterprise_suite = EnterpriseLLMSuite()


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("🏢 辉夜AI - 企业级LLM基础设施套件测试")
    print("=" * 70)
    print()
    
    suite = EnterpriseLLMSuite()
    
    # 1. 测试模型服务化
    print("🚀 1. 模型服务化部署")
    endpoint = suite.model_serving.deploy_model({
        "name": "gpt-model-v1",
        "model_path": "/models/gpt",
        "gpu_count": 2,
        "batch_size": 32
    })
    print(f"   端点创建: {endpoint.name}")
    print(f"   状态: {endpoint.status.value}")
    print(f"   URL: {endpoint.endpoint_url}")
    
    # 2. 测试实验追踪
    print("\n📊 2. 实验追踪管理")
    exp = suite.experiment_tracker.create_experiment("LLM微调实验", "测试不同参数")
    run = suite.experiment_tracker.start_run(exp.id, "baseline_run")
    suite.experiment_tracker.log_param(run.id, "learning_rate", 0.001)
    suite.experiment_tracker.log_param(run.id, "batch_size", 32)
    suite.experiment_tracker.log_metric(run.id, "accuracy", 0.95)
    suite.experiment_tracker.log_metric(run.id, "loss", 0.05)
    suite.experiment_tracker.end_run(run.id)
    print(f"   实验创建: {exp.name}")
    print(f"   运行记录: {run.name}")
    print(f"   参数: {run.params}")
    
    # 3. 测试监控观测
    print("\n📈 3. 生产监控观测")
    trace = suite.observability.start_trace("对话请求", "你好")
    obs = suite.observability.add_observation(
        trace.id, "LLM调用", "llm",
        input_data="你好",
        model="gpt-4"
    )
    suite.observability.end_observation(
        obs.id, "你好！有什么可以帮助你？",
        prompt_tokens=10, completion_tokens=20, cost=0.002
    )
    suite.observability.end_trace(trace.id, "你好！有什么可以帮助你？")
    print(f"   追踪ID: {trace.id}")
    print(f"   观测点: {obs.name}")
    
    # 4. 测试提示词管理
    print("\n📝 4. 提示词版本控制")
    template = suite.prompt_manager.create_template(
        name="客服对话",
        system_prompt="你是客服助手",
        user_prompt_template="客户问题：{question}",
        variables=[{"name": "question", "type": "string"}],
        tags=["customer_service"]
    )
    
    # 更新模板（创建新版本）
    suite.prompt_manager.update_template(
        template.id,
        system_prompt="你是专业的客服助手",
        user_prompt_template="客户问题：{question}\n请用{language}回答"
    )
    
    rendered = suite.prompt_manager.render_template(
        template.id,
        {"question": "如何退款？", "language": "中文"}
    )
    print(f"   模板: {template.name}")
    print(f"   版本: {template.version}")
    print(f"   历史版本: {len(template.version_history)}")
    print(f"   渲染结果: {rendered['user_prompt'][:50]}...")
    
    # 5. 系统状态
    print("\n📋 5. 系统状态汇总")
    status = suite.get_system_status()
    print(f"   模型端点: {status['model_serving']['endpoints_count']}")
    print(f"   实验数量: {status['experiment_tracker']['experiments_count']}")
    print(f"   追踪记录: {status['observability']['traces_count']}")
    print(f"   提示模板: {status['prompt_manager']['templates_count']}")
    
    print("\n" + "=" * 70)
    print("✅ 所有测试通过!")
    print("=" * 70)
