#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
深度研究系统 (Deep Research System)
实现类似Manus的自主研究能力，支持多步骤调研、信息整合和报告生成
"""

import asyncio
import json
import re
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ResearchStatus(Enum):
    """研究状态"""
    PENDING = "pending"
    PLANNING = "planning"
    RESEARCHING = "researching"
    ANALYZING = "analyzing"
    WRITING = "writing"
    COMPLETED = "completed"
    FAILED = "failed"


class ResearchStepType(Enum):
    """研究步骤类型"""
    SEARCH = "search"
    FETCH = "fetch"
    ANALYZE = "analyze"
    SUMMARIZE = "summarize"
    SYNTHESIZE = "synthesize"
    VERIFY = "verify"


@dataclass
class ResearchStep:
    """研究步骤"""
    id: str
    type: ResearchStepType
    description: str
    status: str = "pending"
    result: Any = None
    error: str = None
    start_time: datetime = None
    end_time: datetime = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "description": self.description,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None
        }


@dataclass
class ResearchTask:
    """研究任务"""
    id: str
    query: str
    status: ResearchStatus
    steps: List[ResearchStep] = field(default_factory=list)
    plan: Dict[str, Any] = field(default_factory=dict)
    findings: List[Dict[str, Any]] = field(default_factory=list)
    report: str = ""
    created_at: datetime = None
    completed_at: datetime = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "query": self.query,
            "status": self.status.value,
            "steps": [step.to_dict() for step in self.steps],
            "plan": self.plan,
            "findings": self.findings,
            "report": self.report,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metadata": self.metadata
        }


class ResearchPlanner:
    """研究计划生成器"""
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
    
    async def create_plan(self, query: str) -> Dict[str, Any]:
        """为查询创建研究计划"""
        # 分析查询类型和所需步骤
        plan = {
            "query": query,
            "objective": f"深入研究: {query}",
            "steps": [],
            "estimated_time": "5-10分钟"
        }
        
        # 根据查询类型确定研究步骤
        if self._is_technical_query(query):
            plan["steps"] = [
                {"type": "search", "description": "搜索技术文档和官方资料"},
                {"type": "search", "description": "搜索社区讨论和实践经验"},
                {"type": "fetch", "description": "获取关键技术文档内容"},
                {"type": "analyze", "description": "分析技术架构和实现原理"},
                {"type": "synthesize", "description": "整合技术信息"},
                {"type": "verify", "description": "验证信息准确性"}
            ]
        elif self._is_news_query(query):
            plan["steps"] = [
                {"type": "search", "description": "搜索最新新闻报道"},
                {"type": "search", "description": "搜索多方观点和分析"},
                {"type": "fetch", "description": "获取关键报道内容"},
                {"type": "analyze", "description": "分析事件背景和影响"},
                {"type": "synthesize", "description": "整合多方信息"}
            ]
        else:
            plan["steps"] = [
                {"type": "search", "description": "搜索基础信息和定义"},
                {"type": "search", "description": "搜索深入分析和案例"},
                {"type": "fetch", "description": "获取权威资料内容"},
                {"type": "analyze", "description": "分析关键概念和关系"},
                {"type": "synthesize", "description": "整合研究发现"}
            ]
        
        return plan
    
    def _is_technical_query(self, query: str) -> bool:
        """判断是否为技术类查询"""
        tech_keywords = [
            "代码", "编程", "开发", "框架", "库", "API", "算法", "架构",
            "Python", "JavaScript", "Java", "Go", "Rust", "数据库", "服务器",
            "机器学习", "深度学习", "AI", "LLM", "模型", "训练"
        ]
        return any(kw in query for kw in tech_keywords)
    
    def _is_news_query(self, query: str) -> bool:
        """判断是否为新闻类查询"""
        news_keywords = ["新闻", "最新", "报道", "事件", "发布", "宣布", "更新"]
        return any(kw in query for kw in news_keywords)


class DeepResearchEngine:
    """深度研究引擎"""
    
    def __init__(self, llm_client=None, search_func=None):
        self.llm_client = llm_client
        self.search_func = search_func or self._default_search
        self.planner = ResearchPlanner(llm_client)
        self.tasks: Dict[str, ResearchTask] = {}
        self.max_iterations = 5
    
    async def start_research(self, query: str, depth: str = "standard") -> str:
        """开始深度研究"""
        task_id = f"research_{uuid.uuid4().hex[:8]}"
        
        task = ResearchTask(
            id=task_id,
            query=query,
            status=ResearchStatus.PLANNING
        )
        self.tasks[task_id] = task
        
        # 异步执行研究
        asyncio.create_task(self._execute_research(task, depth))
        
        return task_id
    
    async def _execute_research(self, task: ResearchTask, depth: str):
        """执行研究流程"""
        try:
            # 1. 创建研究计划
            logger.info(f"[{task.id}] 创建研究计划...")
            task.plan = await self.planner.create_plan(task.query)
            task.status = ResearchStatus.RESEARCHING
            
            # 2. 执行研究步骤
            for i, step_plan in enumerate(task.plan["steps"]):
                step = ResearchStep(
                    id=f"step_{i}",
                    type=ResearchStepType(step_plan["type"]),
                    description=step_plan["description"]
                )
                task.steps.append(step)
                
                await self._execute_step(task, step)
                
                # 如果步骤失败，尝试替代方案
                if step.status == "failed" and step.type == ResearchStepType.SEARCH:
                    await self._retry_search_step(task, step)
            
            # 3. 分析阶段
            task.status = ResearchStatus.ANALYZING
            await self._analyze_findings(task)
            
            # 4. 生成报告
            task.status = ResearchStatus.WRITING
            await self._generate_report(task, depth)
            
            task.status = ResearchStatus.COMPLETED
            task.completed_at = datetime.now()
            
            logger.info(f"[{task.id}] 研究完成")
            
        except Exception as e:
            logger.error(f"[{task.id}] 研究失败: {e}")
            task.status = ResearchStatus.FAILED
            task.metadata["error"] = str(e)
    
    async def _execute_step(self, task: ResearchTask, step: ResearchStep):
        """执行单个研究步骤"""
        step.status = "running"
        step.start_time = datetime.now()
        
        try:
            if step.type == ResearchStepType.SEARCH:
                result = await self._perform_search(task, step)
            elif step.type == ResearchStepType.FETCH:
                result = await self._fetch_content(task, step)
            elif step.type == ResearchStepType.ANALYZE:
                result = await self._analyze_content(task, step)
            elif step.type == ResearchStepType.SYNTHESIZE:
                result = await self._synthesize_findings(task, step)
            elif step.type == ResearchStepType.VERIFY:
                result = await self._verify_findings(task, step)
            else:
                result = {"status": "skipped"}
            
            step.result = result
            step.status = "completed"
            
            # 保存发现
            if step.type in [ResearchStepType.SEARCH, ResearchStepType.FETCH]:
                task.findings.append({
                    "step_id": step.id,
                    "type": step.type.value,
                    "content": result,
                    "timestamp": datetime.now().isoformat()
                })
            
        except Exception as e:
            step.error = str(e)
            step.status = "failed"
            logger.error(f"步骤 {step.id} 失败: {e}")
        
        finally:
            step.end_time = datetime.now()
    
    async def _perform_search(self, task: ResearchTask, step: ResearchStep) -> Dict[str, Any]:
        """执行搜索"""
        # 构建搜索查询
        search_query = self._build_search_query(task.query, step.description)
        
        # 执行搜索
        results = await self.search_func(search_query)
        
        return {
            "query": search_query,
            "results_count": len(results) if isinstance(results, list) else 0,
            "results": results[:5] if isinstance(results, list) else results  # 限制结果数量
        }
    
    async def _fetch_content(self, task: ResearchTask, step: ResearchStep) -> Dict[str, Any]:
        """获取内容"""
        # 从上一步的搜索结果中提取URL并获取内容
        contents = []
        
        for finding in task.findings:
            if finding["type"] == "search":
                results = finding["content"].get("results", [])
                for result in results[:3]:  # 获取前3个结果的内容
                    if isinstance(result, dict) and "url" in result:
                        try:
                            content = await self._fetch_url(result["url"])
                            contents.append({
                                "url": result["url"],
                                "title": result.get("title", ""),
                                "content": content[:2000]  # 限制内容长度
                            })
                        except Exception as e:
                            logger.warning(f"获取内容失败 {result['url']}: {e}")
        
        return {"contents": contents}
    
    async def _analyze_content(self, task: ResearchTask, step: ResearchStep) -> Dict[str, Any]:
        """分析内容"""
        # 使用LLM分析收集到的信息
        findings_text = json.dumps(task.findings, ensure_ascii=False, indent=2)
        
        analysis_prompt = f"""请分析以下研究信息，提取关键观点、事实和洞察：

研究主题: {task.query}

收集到的信息:
{findings_text[:3000]}

请提供：
1. 关键事实和发现
2. 主要观点和结论
3. 存在的争议或不同观点
4. 信息缺口和需要进一步研究的方向"""
        
        # 这里应该调用LLM进行分析
        analysis = {
            "key_facts": ["分析结果示例"],
            "main_points": ["主要观点示例"],
            "controversies": [],
            "gaps": ["需要更多信息"]
        }
        
        return analysis
    
    async def _synthesize_findings(self, task: ResearchTask, step: ResearchStep) -> Dict[str, Any]:
        """整合发现"""
        # 整合所有研究发现
        synthesis = {
            "summary": f"关于'{task.query}'的研究综合",
            "key_insights": [],
            "sources": len(task.findings),
            "confidence": "medium"
        }
        
        return synthesis
    
    async def _verify_findings(self, task: ResearchTask, step: ResearchStep) -> Dict[str, Any]:
        """验证发现"""
        # 交叉验证关键信息
        verification = {
            "verified_facts": [],
            "unverified_claims": [],
            "conflicting_info": [],
            "verification_status": "partial"
        }
        
        return verification
    
    async def _generate_report(self, task: ResearchTask, depth: str):
        """生成研究报告"""
        # 根据深度生成不同详细程度的报告
        if depth == "brief":
            template = self._brief_report_template()
        elif depth == "comprehensive":
            template = self._comprehensive_report_template()
        else:  # standard
            template = self._standard_report_template()
        
        # 填充报告内容
        report = template.format(
            query=task.query,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
            findings_count=len(task.findings),
            steps_count=len(task.steps),
            plan=json.dumps(task.plan, ensure_ascii=False, indent=2),
            findings=json.dumps(task.findings, ensure_ascii=False, indent=2)[:2000]
        )
        
        task.report = report
    
    def _brief_report_template(self) -> str:
        """简要报告模板"""
        return """# 研究简报: {query}

**研究时间**: {timestamp}
**信息来源**: {findings_count} 个来源

## 核心发现

{findings}

## 结论

基于收集到的信息，{query} 的关键要点如上所述。

---
*本报告由AI深度研究系统自动生成*"""
    
    def _standard_report_template(self) -> str:
        """标准报告模板"""
        return """# 深度研究报告: {query}

**研究时间**: {timestamp}
**执行步骤**: {steps_count} 步
**信息来源**: {findings_count} 个来源

## 研究计划

{plan}

## 研究发现

{findings}

## 详细分析

### 1. 关键事实
基于收集到的信息，以下是关于该主题的关键事实：

### 2. 主要观点
不同来源对该主题的主要观点包括：

### 3. 深入洞察
通过综合分析，我们发现：

## 结论与建议

基于以上研究，我们得出以下结论：

---
*本报告由AI深度研究系统自动生成*"""
    
    def _comprehensive_report_template(self) -> str:
        """综合报告模板"""
        return """# 综合研究报告: {query}

**研究时间**: {timestamp}
**执行步骤**: {steps_count} 步
**信息来源**: {findings_count} 个来源

## 执行摘要

本报告通过系统化研究流程，深入分析了"{query}"相关主题。

## 研究方法

{plan}

## 详细发现

{findings}

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
*本报告由AI深度研究系统自动生成*"""
    
    async def _retry_search_step(self, task: ResearchTask, step: ResearchStep):
        """重试搜索步骤"""
        logger.info(f"[{task.id}] 重试搜索步骤: {step.description}")
        # 使用替代搜索策略
        step.status = "running"
        try:
            # 修改搜索查询重试
            alternative_query = f"{task.query} 详细教程"
            results = await self.search_func(alternative_query)
            step.result = {
                "query": alternative_query,
                "results": results,
                "note": "使用替代查询"
            }
            step.status = "completed"
        except Exception as e:
            step.error = f"重试失败: {str(e)}"
            step.status = "failed"
    
    def _build_search_query(self, original_query: str, step_description: str) -> str:
        """构建搜索查询"""
        # 根据步骤描述优化搜索词
        if "技术文档" in step_description:
            return f"{original_query} documentation tutorial"
        elif "社区讨论" in step_description:
            return f"{original_query} forum discussion reddit"
        elif "新闻" in step_description:
            return f"{original_query} news latest"
        else:
            return original_query
    
    async def _default_search(self, query: str) -> List[Dict[str, str]]:
        """默认搜索函数（示例）"""
        # 这里应该集成实际的搜索API
        return [
            {"title": f"关于 {query} 的搜索结果", "url": "https://example.com/1"},
            {"title": f"{query} 详细指南", "url": "https://example.com/2"}
        ]
    
    async def _fetch_url(self, url: str) -> str:
        """获取URL内容"""
        # 这里应该实现实际的网页抓取
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
            return f"研究尚未完成，当前状态: {task.status.value}"
        return task.report


# 全局研究引擎实例
_research_engine = None

def get_research_engine(llm_client=None) -> DeepResearchEngine:
    """获取全局研究引擎实例"""
    global _research_engine
    if _research_engine is None:
        _research_engine = DeepResearchEngine(llm_client)
    return _research_engine


if __name__ == "__main__":
    async def test_research():
        engine = get_research_engine()
        
        # 启动研究
        task_id = await engine.start_research(
            query="Python异步编程最佳实践",
            depth="standard"
        )
        
        print(f"研究任务已启动: {task_id}")
        
        # 等待研究完成
        for i in range(30):
            await asyncio.sleep(1)
            status = engine.get_task_status(task_id)
            print(f"状态: {status['status']} - 步骤: {len(status['steps'])}")
            
            if status['status'] in ['completed', 'failed']:
                break
        
        # 获取报告
        report = engine.get_task_report(task_id)
        print("\n" + "="*50)
        print("研究报告:")
        print("="*50)
        print(report[:1000] if report else "无报告")
    
    asyncio.run(test_research())
