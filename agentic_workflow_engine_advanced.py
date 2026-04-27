#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agentic Workflow Engine Advanced - 高级工作流引擎
增强功能加强版

新增特性:
- 自适应工作流 (Adaptive Workflows)
- 记忆增强 (Memory-Augmented Workflows)
- 工具使用规划 (Tool Use Planning)
- 自我反思 (Self-Reflection)
- 多Agent编排 (Multi-Agent Orchestration)
- 工作流版本控制
- A/B测试支持
- 性能分析器
"""

import asyncio
import json
import uuid
import time
import logging
from typing import Dict, List, Any, Optional, Callable, Union, AsyncIterator, Set, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum, auto
from abc import ABC, abstractmethod
from collections import deque, defaultdict
import copy
import hashlib
import inspect

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ==================== 高级类型定义 ====================

class WorkflowPattern(Enum):
    """工作流模式"""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    MAP_REDUCE = "map_reduce"
    DAG = "dag"
    EVENT_DRIVEN = "event_driven"
    ADAPTIVE = "adaptive"
    CONVERSATIONAL = "conversational"


class AgentRole(Enum):
    """Agent角色"""
    PLANNER = "planner"
    EXECUTOR = "executor"
    CRITIC = "critic"
    ORCHESTRATOR = "orchestrator"
    SPECIALIST = "specialist"
    GENERALIST = "generalist"


@dataclass
class ToolDefinition:
    """工具定义"""
    tool_id: str
    name: str
    description: str
    parameters: Dict[str, Any]
    required_params: List[str]
    return_type: str = "any"
    examples: List[Dict] = field(default_factory=list)
    success_rate: float = 1.0
    avg_execution_time_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_id": self.tool_id,
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "required_params": self.required_params,
            "return_type": self.return_type,
            "success_rate": self.success_rate,
            "avg_execution_time_ms": self.avg_execution_time_ms
        }


@dataclass
class ExecutionMetrics:
    """执行指标"""
    node_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    retry_count: int = 0
    cache_hit: bool = False
    
    @property
    def duration_ms(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds() * 1000
        return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "duration_ms": self.duration_ms,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost_usd": self.cost_usd,
            "retry_count": self.retry_count,
            "cache_hit": self.cache_hit
        }


@dataclass
class ReflectionResult:
    """反思结果"""
    original_output: str
    critique: str
    improvements: List[str]
    refined_output: str
    confidence_before: float
    confidence_after: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_output": self.original_output[:200] + "..." if len(self.original_output) > 200 else self.original_output,
            "critique": self.critique,
            "improvements": self.improvements,
            "confidence_before": self.confidence_before,
            "confidence_after": self.confidence_after
        }


# ==================== 记忆增强系统 ====================

class WorkflowMemory:
    """工作流记忆系统"""
    
    def __init__(self, max_short_term: int = 10, max_long_term: int = 1000):
        self.short_term: deque = deque(maxlen=max_short_term)
        self.long_term: Dict[str, Any] = {}
        self.episodic_memory: List[Dict] = []  # 场景记忆
        self.semantic_memory: Dict[str, Any] = {}  # 语义知识
        self.procedural_memory: Dict[str, Any] = {}  # 程序性记忆
        
    def add_short_term(self, key: str, value: Any, importance: float = 0.5):
        """添加短期记忆"""
        self.short_term.append({
            "key": key,
            "value": value,
            "importance": importance,
            "timestamp": datetime.now()
        })
    
    def add_long_term(self, key: str, value: Any, category: str = "general"):
        """添加长期记忆"""
        if category not in self.long_term:
            self.long_term[category] = {}
        self.long_term[category][key] = {
            "value": value,
            "created_at": datetime.now(),
            "access_count": 0
        }
    
    def recall(self, query: str, k: int = 5) -> List[Dict]:
        """回忆相关记忆"""
        results = []
        
        # 搜索短期记忆
        for item in self.short_term:
            if query.lower() in str(item.get("key", "")).lower():
                results.append({"source": "short_term", **item})
        
        # 搜索长期记忆
        for category, items in self.long_term.items():
            for key, data in items.items():
                if query.lower() in key.lower():
                    results.append({
                        "source": "long_term",
                        "category": category,
                        "key": key,
                        **data
                    })
        
        # 按重要性排序
        results.sort(key=lambda x: x.get("importance", 0.5), reverse=True)
        return results[:k]
    
    def consolidate(self):
        """记忆巩固 - 将重要短期记忆转为长期记忆"""
        for item in list(self.short_term):
            if item.get("importance", 0) > 0.8:
                self.add_long_term(
                    item["key"],
                    item["value"],
                    "consolidated"
                )


# ==================== 工具使用规划器 ====================

class ToolUsePlanner:
    """工具使用规划器 - 智能选择和编排工具"""
    
    def __init__(self):
        self.tools: Dict[str, ToolDefinition] = {}
        self.tool_history: List[Dict] = []
        self.tool_performance: Dict[str, Dict] = defaultdict(lambda: {
            "success_count": 0,
            "fail_count": 0,
            "total_time_ms": 0
        })
    
    def register_tool(self, tool: ToolDefinition):
        """注册工具"""
        self.tools[tool.tool_id] = tool
        logger.info(f"注册工具: {tool.name} ({tool.tool_id})")
    
    async def plan_tool_usage(self, task: str, context: Dict[str, Any]) -> List[Dict]:
        """规划工具使用序列"""
        # 分析任务需求
        required_capabilities = self._analyze_task_requirements(task)
        
        # 选择合适的工具
        selected_tools = []
        for capability in required_capabilities:
            tool = self._select_best_tool(capability)
            if tool:
                selected_tools.append({
                    "tool_id": tool.tool_id,
                    "parameters": self._infer_parameters(tool, task, context),
                    "reason": f"Selected for {capability}"
                })
        
        # 优化执行顺序
        optimized_plan = self._optimize_execution_order(selected_tools)
        
        return optimized_plan
    
    def _analyze_task_requirements(self, task: str) -> List[str]:
        """分析任务需求"""
        # 简化实现，实际应该使用NLP分析
        capabilities = []
        
        if any(kw in task.lower() for kw in ["search", "find", "look up", "查询"]):
            capabilities.append("search")
        if any(kw in task.lower() for kw in ["calculate", "compute", "计算"]):
            capabilities.append("calculation")
        if any(kw in task.lower() for kw in ["write", "generate", "create", "生成"]):
            capabilities.append("generation")
        if any(kw in task.lower() for kw in ["analyze", "分析"]):
            capabilities.append("analysis")
        
        return capabilities if capabilities else ["general"]
    
    def _select_best_tool(self, capability: str) -> Optional[ToolDefinition]:
        """选择最佳工具"""
        candidates = [
            tool for tool in self.tools.values()
            if capability.lower() in tool.description.lower()
        ]
        
        if not candidates:
            return None
        
        # 按成功率和执行时间排序
        candidates.sort(key=lambda t: (
            t.success_rate,
            -t.avg_execution_time_ms
        ), reverse=True)
        
        return candidates[0]
    
    def _infer_parameters(self, tool: ToolDefinition, task: str, 
                         context: Dict) -> Dict[str, Any]:
        """推断工具参数"""
        params = {}
        for param_name in tool.required_params:
            # 从上下文或任务中提取参数
            if param_name in context:
                params[param_name] = context[param_name]
            else:
                params[param_name] = f"inferred_{param_name}"
        return params
    
    def _optimize_execution_order(self, tools: List[Dict]) -> List[Dict]:
        """优化执行顺序"""
        # 根据依赖关系排序
        # 简化实现，实际应该构建依赖图
        return tools
    
    def update_tool_performance(self, tool_id: str, success: bool, 
                               execution_time_ms: float):
        """更新工具性能统计"""
        stats = self.tool_performance[tool_id]
        if success:
            stats["success_count"] += 1
        else:
            stats["fail_count"] += 1
        stats["total_time_ms"] += execution_time_ms
        
        # 更新工具定义
        if tool_id in self.tools:
            tool = self.tools[tool_id]
            total = stats["success_count"] + stats["fail_count"]
            tool.success_rate = stats["success_count"] / total if total > 0 else 1.0
            tool.avg_execution_time_ms = stats["total_time_ms"] / total if total > 0 else 0


# ==================== 自我反思系统 ====================

class SelfReflectionSystem:
    """自我反思系统 - 提升输出质量"""
    
    def __init__(self, max_iterations: int = 3):
        self.max_iterations = max_iterations
        self.reflection_history: List[ReflectionResult] = []
    
    async def reflect_and_refine(self, 
                                original_output: str,
                                task_context: Dict[str, Any],
                                llm_client = None) -> ReflectionResult:
        """反思并改进输出"""
        
        # 第一步：生成批评
        critique = await self._generate_critique(original_output, task_context, llm_client)
        
        # 第二步：识别改进点
        improvements = self._identify_improvements(critique)
        
        # 第三步：生成改进后的输出
        refined_output = await self._refine_output(
            original_output, critique, improvements, llm_client
        )
        
        # 第四步：评估改进效果
        confidence_before = self._evaluate_quality(original_output)
        confidence_after = self._evaluate_quality(refined_output)
        
        result = ReflectionResult(
            original_output=original_output,
            critique=critique,
            improvements=improvements,
            refined_output=refined_output,
            confidence_before=confidence_before,
            confidence_after=confidence_after
        )
        
        self.reflection_history.append(result)
        return result
    
    async def _generate_critique(self, output: str, context: Dict, 
                                llm_client) -> str:
        """生成批评意见"""
        critique_prompt = f"""
        请批评以下输出，指出问题和改进空间：
        
        任务：{context.get('task', 'Unknown')}
        输出：{output}
        
        请从以下角度分析：
        1. 准确性
        2. 完整性
        3. 清晰度
        4. 相关性
        """
        
        # 简化实现
        return "输出基本正确，但可以更详细和结构化。"
    
    def _identify_improvements(self, critique: str) -> List[str]:
        """识别改进点"""
        improvements = []
        
        if "详细" in critique or "detail" in critique.lower():
            improvements.append("增加细节和例子")
        if "结构" in critique or "structure" in critique.lower():
            improvements.append("改进结构和组织")
        if "清晰" in critique or "clear" in critique.lower():
            improvements.append("提高清晰度")
        
        return improvements if improvements else ["优化表达"]
    
    async def _refine_output(self, original: str, critique: str, 
                            improvements: List[str], llm_client) -> str:
        """改进输出"""
        # 简化实现
        return f"[改进版] {original}\n\n改进点：{', '.join(improvements)}"
    
    def _evaluate_quality(self, output: str) -> float:
        """评估输出质量"""
        # 基于长度、结构等因素评分
        score = 0.7
        
        if len(output) > 200:
            score += 0.1
        if "\n" in output:
            score += 0.1
        if any(marker in output for marker in ["1.", "2.", "3.", "- ", "* "]):
            score += 0.1
        
        return min(1.0, score)


# ==================== 多Agent编排器 ====================

@dataclass
class AgentProfile:
    """Agent档案"""
    agent_id: str
    name: str
    role: AgentRole
    capabilities: List[str]
    system_prompt: str
    model_config: Dict[str, Any]
    performance_metrics: Dict[str, float] = field(default_factory=dict)


class MultiAgentOrchestrator:
    """多Agent编排器"""
    
    def __init__(self):
        self.agents: Dict[str, AgentProfile] = {}
        self.communication_bus: asyncio.Queue = asyncio.Queue()
        self.shared_context: Dict[str, Any] = {}
        self.agent_conversations: Dict[str, List[Dict]] = defaultdict(list)
    
    def register_agent(self, profile: AgentProfile):
        """注册Agent"""
        self.agents[profile.agent_id] = profile
        logger.info(f"注册Agent: {profile.name} ({profile.role.value})")
    
    async def orchestrate(self, task: str, 
                         agent_ids: List[str],
                         strategy: str = "sequential") -> Dict[str, Any]:
        """编排多个Agent协作"""
        
        if strategy == "sequential":
            return await self._sequential_execution(task, agent_ids)
        elif strategy == "parallel":
            return await self._parallel_execution(task, agent_ids)
        elif strategy == "debate":
            return await self._debate_execution(task, agent_ids)
        elif strategy == "hierarchical":
            return await self._hierarchical_execution(task, agent_ids)
        else:
            raise ValueError(f"Unknown strategy: {strategy}")
    
    async def _sequential_execution(self, task: str, 
                                   agent_ids: List[str]) -> Dict[str, Any]:
        """顺序执行"""
        results = []
        context = {"task": task, "previous_results": []}
        
        for agent_id in agent_ids:
            agent = self.agents.get(agent_id)
            if not agent:
                continue
            
            # 执行Agent任务
            result = await self._execute_agent(agent, context)
            results.append({
                "agent_id": agent_id,
                "agent_role": agent.role.value,
                "result": result
            })
            
            # 更新上下文
            context["previous_results"].append(result)
        
        return {
            "strategy": "sequential",
            "results": results,
            "final_output": results[-1]["result"] if results else None
        }
    
    async def _parallel_execution(self, task: str,
                                 agent_ids: List[str]) -> Dict[str, Any]:
        """并行执行"""
        tasks = []
        for agent_id in agent_ids:
            agent = self.agents.get(agent_id)
            if agent:
                t = self._execute_agent(agent, {"task": task})
                tasks.append(t)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            "strategy": "parallel",
            "results": [
                {"agent_id": aid, "result": res}
                for aid, res in zip(agent_ids, results)
            ]
        }
    
    async def _debate_execution(self, task: str,
                               agent_ids: List[str],
                               rounds: int = 3) -> Dict[str, Any]:
        """辩论式执行"""
        # 初始化观点
        perspectives = {}
        for agent_id in agent_ids:
            agent = self.agents.get(agent_id)
            if agent:
                perspective = await self._execute_agent(agent, {"task": task})
                perspectives[agent_id] = perspective
        
        # 多轮辩论
        for round_num in range(rounds):
            new_perspectives = {}
            for agent_id in agent_ids:
                agent = self.agents.get(agent_id)
                if agent:
                    # 考虑其他Agent的观点
                    context = {
                        "task": task,
                        "round": round_num + 1,
                        "other_perspectives": {
                            k: v for k, v in perspectives.items() if k != agent_id
                        }
                    }
                    refined = await self._execute_agent(agent, context)
                    new_perspectives[agent_id] = refined
            perspectives = new_perspectives
        
        return {
            "strategy": "debate",
            "rounds": rounds,
            "final_perspectives": perspectives
        }
    
    async def _hierarchical_execution(self, task: str,
                                     agent_ids: List[str]) -> Dict[str, Any]:
        """层级执行"""
        # 找到编排者
        orchestrator = None
        workers = []
        
        for agent_id in agent_ids:
            agent = self.agents.get(agent_id)
            if agent:
                if agent.role == AgentRole.ORCHESTRATOR:
                    orchestrator = agent
                else:
                    workers.append(agent)
        
        if not orchestrator:
            return await self._sequential_execution(task, agent_ids)
        
        # 编排者制定计划
        plan = await self._execute_agent(orchestrator, {
            "task": task,
            "available_workers": [w.name for w in workers]
        })
        
        # 执行计划
        results = []
        for worker in workers:
            result = await self._execute_agent(worker, {
                "task": task,
                "plan": plan
            })
            results.append({"worker": worker.name, "result": result})
        
        # 编排者综合结果
        final = await self._execute_agent(orchestrator, {
            "task": "synthesize results",
            "worker_results": results
        })
        
        return {
            "strategy": "hierarchical",
            "plan": plan,
            "worker_results": results,
            "final_output": final
        }
    
    async def _execute_agent(self, agent: AgentProfile, 
                            context: Dict) -> str:
        """执行单个Agent"""
        # 简化实现
        return f"[{agent.name}] 执行任务: {context.get('task', 'Unknown')}"


# ==================== 工作流版本控制 ====================

class WorkflowVersionControl:
    """工作流版本控制系统"""
    
    def __init__(self):
        self.versions: Dict[str, List[Dict]] = defaultdict(list)
        self.branches: Dict[str, Dict] = {}
    
    def commit(self, workflow_id: str, workflow_data: Dict,
              message: str, author: str) -> str:
        """提交版本"""
        version_id = f"v{len(self.versions[workflow_id]) + 1}"
        
        commit = {
            "version_id": version_id,
            "workflow_data": workflow_data,
            "message": message,
            "author": author,
            "timestamp": datetime.now().isoformat(),
            "hash": self._compute_hash(workflow_data)
        }
        
        self.versions[workflow_id].append(commit)
        logger.info(f"工作流 {workflow_id} 提交版本 {version_id}: {message}")
        return version_id
    
    def get_version(self, workflow_id: str, 
                   version_id: str = None) -> Optional[Dict]:
        """获取特定版本"""
        versions = self.versions.get(workflow_id, [])
        if not versions:
            return None
        
        if version_id is None:
            return versions[-1]  # 最新版本
        
        for v in versions:
            if v["version_id"] == version_id:
                return v
        return None
    
    def list_versions(self, workflow_id: str) -> List[Dict]:
        """列出所有版本"""
        return [
            {
                "version_id": v["version_id"],
                "message": v["message"],
                "author": v["author"],
                "timestamp": v["timestamp"]
            }
            for v in self.versions.get(workflow_id, [])
        ]
    
    def create_branch(self, workflow_id: str, branch_name: str, 
                     from_version: str = None):
        """创建分支"""
        self.branches[f"{workflow_id}/{branch_name}"] = {
            "workflow_id": workflow_id,
            "branch_name": branch_name,
            "base_version": from_version or "latest",
            "created_at": datetime.now().isoformat()
        }
    
    def _compute_hash(self, data: Dict) -> str:
        """计算工作流哈希"""
        content = json.dumps(data, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:12]


# ==================== A/B测试框架 ====================

class ABTestFramework:
    """A/B测试框架"""
    
    def __init__(self):
        self.experiments: Dict[str, Dict] = {}
        self.assignments: Dict[str, str] = {}  # user_id -> variant
        self.results: Dict[str, List[Dict]] = defaultdict(list)
    
    def create_experiment(self, experiment_id: str, 
                         name: str,
                         variants: List[Dict],
                         traffic_split: List[float] = None) -> Dict:
        """创建实验"""
        if traffic_split is None:
            traffic_split = [1.0 / len(variants)] * len(variants)
        
        experiment = {
            "experiment_id": experiment_id,
            "name": name,
            "variants": variants,
            "traffic_split": traffic_split,
            "status": "running",
            "created_at": datetime.now().isoformat(),
            "total_participants": 0
        }
        
        self.experiments[experiment_id] = experiment
        return experiment
    
    def assign_variant(self, experiment_id: str, 
                      user_id: str) -> Dict:
        """为用户分配变体"""
        exp = self.experiments.get(experiment_id)
        if not exp:
            raise ValueError(f"Experiment not found: {experiment_id}")
        
        # 检查是否已分配
        assignment_key = f"{experiment_id}:{user_id}"
        if assignment_key in self.assignments:
            variant_id = self.assignments[assignment_key]
            return next(v for v in exp["variants"] if v["id"] == variant_id)
        
        # 根据流量分配选择变体
        import random
        r = random.random()
        cumulative = 0
        selected_variant = None
        
        for i, variant in enumerate(exp["variants"]):
            cumulative += exp["traffic_split"][i]
            if r <= cumulative:
                selected_variant = variant
                break
        
        if selected_variant:
            self.assignments[assignment_key] = selected_variant["id"]
            exp["total_participants"] += 1
        
        return selected_variant
    
    def record_result(self, experiment_id: str, user_id: str,
                     metrics: Dict[str, Any]):
        """记录实验结果"""
        assignment_key = f"{experiment_id}:{user_id}"
        variant_id = self.assignments.get(assignment_key)
        
        if variant_id:
            self.results[experiment_id].append({
                "user_id": user_id,
                "variant_id": variant_id,
                "metrics": metrics,
                "timestamp": datetime.now().isoformat()
            })
    
    def get_experiment_results(self, experiment_id: str) -> Dict:
        """获取实验结果"""
        exp = self.experiments.get(experiment_id)
        results = self.results.get(experiment_id, [])
        
        if not exp:
            return {"error": "Experiment not found"}
        
        # 按变体统计
        variant_stats = defaultdict(lambda: {
            "participants": 0,
            "metrics": defaultdict(list)
        })
        
        for r in results:
            vid = r["variant_id"]
            variant_stats[vid]["participants"] += 1
            for metric, value in r["metrics"].items():
                variant_stats[vid]["metrics"][metric].append(value)
        
        return {
            "experiment_id": experiment_id,
            "name": exp["name"],
            "total_participants": exp["total_participants"],
            "variant_results": {
                vid: {
                    "participants": stats["participants"],
                    "metrics": {
                        k: {
                            "mean": sum(v) / len(v) if v else 0,
                            "count": len(v)
                        }
                        for k, v in stats["metrics"].items()
                    }
                }
                for vid, stats in variant_stats.items()
            }
        }


# ==================== 性能分析器 ====================

class WorkflowProfiler:
    """工作流性能分析器"""
    
    def __init__(self):
        self.metrics: List[ExecutionMetrics] = []
        self.node_stats: Dict[str, Dict] = defaultdict(lambda: {
            "execution_count": 0,
            "total_duration_ms": 0,
            "total_cost_usd": 0,
            "error_count": 0
        })
    
    def record_metric(self, metric: ExecutionMetrics):
        """记录指标"""
        self.metrics.append(metric)
        
        stats = self.node_stats[metric.node_id]
        stats["execution_count"] += 1
        stats["total_duration_ms"] += metric.duration_ms
        stats["total_cost_usd"] += metric.cost_usd
    
    def get_bottlenecks(self, top_n: int = 5) -> List[Dict]:
        """识别瓶颈"""
        sorted_nodes = sorted(
            self.node_stats.items(),
            key=lambda x: x[1]["total_duration_ms"],
            reverse=True
        )
        
        return [
            {
                "node_id": node_id,
                "avg_duration_ms": stats["total_duration_ms"] / stats["execution_count"],
                "execution_count": stats["execution_count"],
                "total_cost_usd": stats["total_cost_usd"]
            }
            for node_id, stats in sorted_nodes[:top_n]
        ]
    
    def generate_report(self) -> Dict[str, Any]:
        """生成性能报告"""
        total_executions = len(self.metrics)
        total_duration = sum(m.duration_ms for m in self.metrics)
        total_cost = sum(m.cost_usd for m in self.metrics)
        
        return {
            "summary": {
                "total_executions": total_executions,
                "avg_duration_ms": total_duration / total_executions if total_executions > 0 else 0,
                "total_cost_usd": total_cost,
                "avg_cost_per_execution": total_cost / total_executions if total_executions > 0 else 0
            },
            "bottlenecks": self.get_bottlenecks(),
            "node_breakdown": dict(self.node_stats)
        }


# ==================== 集成示例 ====================

async def demo_advanced_features():
    """演示高级功能"""
    print("=" * 60)
    print("🚀 Agentic Workflow 高级功能演示")
    print("=" * 60)
    
    # 1. 记忆增强
    print("\n1️⃣ 记忆增强系统")
    memory = WorkflowMemory()
    memory.add_short_term("user_name", "张三", importance=0.9)
    memory.add_short_term("task_type", "数据分析", importance=0.7)
    memory.add_long_term("api_key", "sk-xxx", category="credentials")
    
    recalled = memory.recall("user", k=3)
    print(f"回忆结果: {len(recalled)} 条记忆")
    
    # 2. 工具使用规划
    print("\n2️⃣ 工具使用规划")
    planner = ToolUsePlanner()
    planner.register_tool(ToolDefinition(
        tool_id="search_tool",
        name="搜索引擎",
        description="搜索网络信息",
        parameters={"query": "string"},
        required_params=["query"]
    ))
    planner.register_tool(ToolDefinition(
        tool_id="calc_tool",
        name="计算器",
        description="执行数学计算",
        parameters={"expression": "string"},
        required_params=["expression"]
    ))
    
    plan = await planner.plan_tool_usage(
        "搜索今天的天气并计算平均气温",
        {}
    )
    print(f"规划的工具序列: {len(plan)} 个工具")
    for p in plan:
        print(f"  - {p['tool_id']}: {p['reason']}")
    
    # 3. 自我反思
    print("\n3️⃣ 自我反思系统")
    reflection = SelfReflectionSystem()
    result = await reflection.reflect_and_refine(
        "这是一个简单的回答",
        {"task": "详细解释AI概念"}
    )
    print(f"反思改进: {len(result.improvements)} 个改进点")
    print(f"置信度提升: {result.confidence_before:.2f} -> {result.confidence_after:.2f}")
    
    # 4. 多Agent编排
    print("\n4️⃣ 多Agent编排")
    orchestrator = MultiAgentOrchestrator()
    orchestrator.register_agent(AgentProfile(
        agent_id="planner",
        name="规划Agent",
        role=AgentRole.PLANNER,
        capabilities=["planning", "analysis"],
        system_prompt="你是一个规划专家",
        model_config={}
    ))
    orchestrator.register_agent(AgentProfile(
        agent_id="executor",
        name="执行Agent",
        role=AgentRole.EXECUTOR,
        capabilities=["execution", "coding"],
        system_prompt="你是一个执行专家",
        model_config={}
    ))
    
    result = await orchestrator.orchestrate(
        "开发一个数据分析工具",
        ["planner", "executor"],
        strategy="sequential"
    )
    print(f"编排策略: {result['strategy']}")
    print(f"参与Agent: {len(result['results'])}")
    
    # 5. 版本控制
    print("\n5️⃣ 工作流版本控制")
    vcs = WorkflowVersionControl()
    v1 = vcs.commit("wf_001", {"nodes": 5}, "初始版本", "developer")
    v2 = vcs.commit("wf_001", {"nodes": 7}, "添加条件节点", "developer")
    versions = vcs.list_versions("wf_001")
    print(f"版本历史: {len(versions)} 个版本")
    for v in versions:
        print(f"  - {v['version_id']}: {v['message']}")
    
    # 6. A/B测试
    print("\n6️⃣ A/B测试框架")
    ab_test = ABTestFramework()
    ab_test.create_experiment(
        "exp_001",
        "提示词优化实验",
        [
            {"id": "control", "name": "对照组", "prompt_template": "标准模板"},
            {"id": "variant_a", "name": "变体A", "prompt_template": "优化模板A"}
        ],
        [0.5, 0.5]
    )
    
    # 分配用户
    for i in range(10):
        variant = ab_test.assign_variant("exp_001", f"user_{i}")
        # 模拟结果
        ab_test.record_result("exp_001", f"user_{i}", {
            "satisfaction": 4.5 if variant["id"] == "variant_a" else 3.5,
            "completion_time": 30
        })
    
    results = ab_test.get_experiment_results("exp_001")
    print(f"实验参与者: {results['total_participants']}")
    
    # 7. 性能分析
    print("\n7️⃣ 性能分析器")
    profiler = WorkflowProfiler()
    from agentic_workflow_engine import ExecutionMetrics as BaseMetrics
    
    # 模拟记录
    for i in range(5):
        metric = ExecutionMetrics(
            node_id=f"node_{i % 3}",
            start_time=datetime.now(),
            end_time=datetime.now(),
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.002
        )
        profiler.record_metric(metric)
    
    report = profiler.generate_report()
    print(f"总执行次数: {report['summary']['total_executions']}")
    print(f"平均耗时: {report['summary']['avg_duration_ms']:.2f}ms")
    print(f"总成本: ${report['summary']['total_cost_usd']:.4f}")
    
    print("\n" + "=" * 60)
    print("✅ 高级功能演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo_advanced_features())
