#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG Evaluation Framework - RAG评估与优化框架
参考: RAGAS, TruLens, Arize AI

核心功能:
- 检索质量评估 (Context Precision, Context Recall)
- 生成质量评估 (Faithfulness, Answer Relevance)
- 端到端评估 (RAGAS Score)
- 自动优化建议
- 对比实验
"""

import asyncio
import json
import uuid
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import defaultdict
import statistics


class RAGMetric(Enum):
    """RAG评估指标"""
    CONTEXT_PRECISION = "context_precision"  # 上下文精确率
    CONTEXT_RECALL = "context_recall"        # 上下文召回率
    FAITHFULNESS = "faithfulness"            # 忠实度
    ANSWER_RELEVANCE = "answer_relevance"    # 答案相关性
    CONTEXT_RELEVANCE = "context_relevance"  # 上下文相关性
    ANSWER_CORRECTNESS = "answer_correctness"  # 答案正确性
    ANSWER_SIMILARITY = "answer_similarity"   # 答案相似度


@dataclass
class RAGTestCase:
    """RAG测试用例"""
    test_id: str
    question: str
    ground_truth: str  # 标准答案
    contexts: List[str]  # 检索到的上下文
    answer: str  # 生成的答案
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_id": self.test_id,
            "question": self.question,
            "ground_truth": self.ground_truth,
            "contexts_count": len(self.contexts),
            "answer": self.answer[:200] + "..." if len(self.answer) > 200 else self.answer,
            "metadata": self.metadata
        }


@dataclass
class RAGMetricResult:
    """RAG指标结果"""
    metric_name: str
    score: float  # 0-1
    details: Dict[str, Any] = field(default_factory=dict)
    explanation: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_name": self.metric_name,
            "score": round(self.score, 3),
            "details": self.details,
            "explanation": self.explanation
        }


@dataclass
class RAGEvaluationResult:
    """RAG评估结果"""
    evaluation_id: str
    test_case: RAGTestCase
    metrics: List[RAGMetricResult]
    overall_score: float
    timestamp: datetime = field(default_factory=datetime.now)
    duration_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "evaluation_id": self.evaluation_id,
            "test_case": self.test_case.to_dict(),
            "metrics": [m.to_dict() for m in self.metrics],
            "overall_score": round(self.overall_score, 3),
            "timestamp": self.timestamp.isoformat(),
            "duration_ms": self.duration_ms
        }


@dataclass
class RAGExperiment:
    """RAG实验"""
    experiment_id: str
    name: str
    description: str
    config: Dict[str, Any]  # 实验配置
    results: List[RAGEvaluationResult] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "name": self.name,
            "description": self.description,
            "config": self.config,
            "result_count": len(self.results),
            "created_at": self.created_at.isoformat()
        }


class RAGEvaluator:
    """RAG评估器"""
    
    def __init__(self):
        self.evaluations: List[RAGEvaluationResult] = []
        self.experiments: Dict[str, RAGExperiment] = {}
        self.benchmarks: Dict[str, List[RAGTestCase]] = {}
    
    # ==================== 核心评估指标 ====================
    
    def evaluate_context_precision(self, question: str, contexts: List[str], 
                                   answer: str) -> RAGMetricResult:
        """
        评估上下文精确率
        衡量检索到的上下文中与问题相关的比例
        """
        if not contexts:
            return RAGMetricResult(
                metric_name=RAGMetric.CONTEXT_PRECISION.value,
                score=0.0,
                explanation="没有检索到任何上下文"
            )
        
        # 简化实现：基于关键词匹配
        relevant_count = 0
        question_keywords = set(question.lower().split())
        
        for i, context in enumerate(contexts):
            context_words = set(context.lower().split())
            overlap = len(question_keywords & context_words)
            relevance = overlap / len(question_keywords) if question_keywords else 0
            
            if relevance > 0.3:  # 阈值
                relevant_count += 1
        
        score = relevant_count / len(contexts)
        
        return RAGMetricResult(
            metric_name=RAGMetric.CONTEXT_PRECISION.value,
            score=score,
            details={
                "total_contexts": len(contexts),
                "relevant_contexts": relevant_count
            },
            explanation=f"{relevant_count}/{len(contexts)} 个上下文与问题相关"
        )
    
    def evaluate_context_recall(self, question: str, contexts: List[str],
                               ground_truth: str) -> RAGMetricResult:
        """
        评估上下文召回率
        衡量标准答案中的信息有多少被上下文覆盖
        """
        if not contexts or not ground_truth:
            return RAGMetricResult(
                metric_name=RAGMetric.CONTEXT_RECALL.value,
                score=0.0,
                explanation="缺少上下文或标准答案"
            )
        
        # 提取标准答案的关键信息
        truth_keywords = set(ground_truth.lower().split())
        covered_keywords = set()
        
        all_context = " ".join(contexts).lower()
        for keyword in truth_keywords:
            if keyword in all_context:
                covered_keywords.add(keyword)
        
        score = len(covered_keywords) / len(truth_keywords) if truth_keywords else 0
        
        return RAGMetricResult(
            metric_name=RAGMetric.CONTEXT_RECALL.value,
            score=score,
            details={
                "truth_keywords": len(truth_keywords),
                "covered_keywords": len(covered_keywords)
            },
            explanation=f"标准答案中 {len(covered_keywords)}/{len(truth_keywords)} 个关键词被上下文覆盖"
        )
    
    def evaluate_faithfulness(self, answer: str, contexts: List[str]) -> RAGMetricResult:
        """
        评估忠实度
        衡量答案中的信息有多少来自上下文（而非幻觉）
        """
        if not answer or not contexts:
            return RAGMetricResult(
                metric_name=RAGMetric.FAITHFULNESS.value,
                score=0.0,
                explanation="缺少答案或上下文"
            )
        
        # 提取答案中的陈述
        all_context = " ".join(contexts).lower()
        answer_sentences = [s.strip() for s in answer.split('.') if s.strip()]
        
        faithful_count = 0
        for sentence in answer_sentences:
            sentence_words = set(sentence.lower().split())
            context_words = set(all_context.split())
            
            # 计算句子中的词有多少在上下文中
            overlap = len(sentence_words & context_words)
            coverage = overlap / len(sentence_words) if sentence_words else 0
            
            if coverage > 0.5:  # 阈值
                faithful_count += 1
        
        score = faithful_count / len(answer_sentences) if answer_sentences else 0
        
        return RAGMetricResult(
            metric_name=RAGMetric.FAITHFULNESS.value,
            score=score,
            details={
                "total_statements": len(answer_sentences),
                "faithful_statements": faithful_count
            },
            explanation=f"{faithful_count}/{len(answer_sentences)} 个陈述忠实于上下文"
        )
    
    def evaluate_answer_relevance(self, question: str, answer: str) -> RAGMetricResult:
        """
        评估答案相关性
        衡量答案与问题的相关程度
        """
        if not question or not answer:
            return RAGMetricResult(
                metric_name=RAGMetric.ANSWER_RELEVANCE.value,
                score=0.0,
                explanation="缺少问题或答案"
            )
        
        # 基于关键词重叠计算
        question_words = set(question.lower().split())
        answer_words = set(answer.lower().split())
        
        overlap = len(question_words & answer_words)
        score = overlap / len(question_words) if question_words else 0
        
        return RAGMetricResult(
            metric_name=RAGMetric.ANSWER_RELEVANCE.value,
            score=min(1.0, score),
            details={
                "question_keywords": len(question_words),
                "overlap": overlap
            },
            explanation=f"答案覆盖了 {overlap}/{len(question_words)} 个问题关键词"
        )
    
    def evaluate_answer_correctness(self, answer: str, 
                                   ground_truth: str) -> RAGMetricResult:
        """
        评估答案正确性
        衡量答案与标准答案的一致性
        """
        if not answer or not ground_truth:
            return RAGMetricResult(
                metric_name=RAGMetric.ANSWER_CORRECTNESS.value,
                score=0.0,
                explanation="缺少答案或标准答案"
            )
        
        # 基于语义相似度（简化实现）
        answer_words = set(answer.lower().split())
        truth_words = set(ground_truth.lower().split())
        
        # Jaccard相似度
        intersection = len(answer_words & truth_words)
        union = len(answer_words | truth_words)
        score = intersection / union if union > 0 else 0
        
        return RAGMetricResult(
            metric_name=RAGMetric.ANSWER_CORRECTNESS.value,
            score=score,
            details={
                "answer_length": len(answer_words),
                "truth_length": len(truth_words),
                "overlap": intersection
            },
            explanation=f"答案与标准答案的相似度为 {score:.2%}"
        )
    
    # ==================== 综合评估 ====================
    
    async def evaluate(self, test_case: RAGTestCase,
                      metrics: List[RAGMetric] = None) -> RAGEvaluationResult:
        """
        执行完整RAG评估
        """
        start_time = datetime.now()
        
        if metrics is None:
            metrics = [
                RAGMetric.CONTEXT_PRECISION,
                RAGMetric.CONTEXT_RECALL,
                RAGMetric.FAITHFULNESS,
                RAGMetric.ANSWER_RELEVANCE,
                RAGMetric.ANSWER_CORRECTNESS
            ]
        
        results = []
        
        for metric in metrics:
            if metric == RAGMetric.CONTEXT_PRECISION:
                result = self.evaluate_context_precision(
                    test_case.question, test_case.contexts, test_case.answer
                )
            elif metric == RAGMetric.CONTEXT_RECALL:
                result = self.evaluate_context_recall(
                    test_case.question, test_case.contexts, test_case.ground_truth
                )
            elif metric == RAGMetric.FAITHFULNESS:
                result = self.evaluate_faithfulness(
                    test_case.answer, test_case.contexts
                )
            elif metric == RAGMetric.ANSWER_RELEVANCE:
                result = self.evaluate_answer_relevance(
                    test_case.question, test_case.answer
                )
            elif metric == RAGMetric.ANSWER_CORRECTNESS:
                result = self.evaluate_answer_correctness(
                    test_case.answer, test_case.ground_truth
                )
            else:
                continue
            
            results.append(result)
        
        # 计算综合得分
        overall_score = statistics.mean([r.score for r in results]) if results else 0
        
        duration = (datetime.now() - start_time).total_seconds() * 1000
        
        evaluation = RAGEvaluationResult(
            evaluation_id=f"eval_{uuid.uuid4().hex[:8]}",
            test_case=test_case,
            metrics=results,
            overall_score=overall_score,
            duration_ms=duration
        )
        
        self.evaluations.append(evaluation)
        return evaluation
    
    async def evaluate_batch(self, test_cases: List[RAGTestCase],
                            metrics: List[RAGMetric] = None) -> List[RAGEvaluationResult]:
        """批量评估"""
        tasks = [self.evaluate(tc, metrics) for tc in test_cases]
        return await asyncio.gather(*tasks)
    
    # ==================== 实验管理 ====================
    
    def create_experiment(self, name: str, description: str,
                         config: Dict[str, Any]) -> RAGExperiment:
        """创建实验"""
        experiment = RAGExperiment(
            experiment_id=f"exp_{uuid.uuid4().hex[:8]}",
            name=name,
            description=description,
            config=config
        )
        self.experiments[experiment.experiment_id] = experiment
        return experiment
    
    def add_evaluation_to_experiment(self, experiment_id: str,
                                    evaluation: RAGEvaluationResult):
        """添加评估到实验"""
        experiment = self.experiments.get(experiment_id)
        if experiment:
            experiment.results.append(evaluation)
    
    def compare_experiments(self, experiment_ids: List[str]) -> Dict[str, Any]:
        """对比多个实验"""
        comparison = {
            "experiments": [],
            "metrics_comparison": defaultdict(dict),
            "winner": None
        }
        
        scores = {}
        for exp_id in experiment_ids:
            exp = self.experiments.get(exp_id)
            if not exp or not exp.results:
                continue
            
            # 计算平均指标
            avg_score = statistics.mean([r.overall_score for r in exp.results])
            scores[exp_id] = avg_score
            
            comparison["experiments"].append({
                "experiment_id": exp_id,
                "name": exp.name,
                "avg_score": avg_score,
                "result_count": len(exp.results)
            })
            
            # 各指标对比
            for metric in RAGMetric:
                metric_scores = []
                for result in exp.results:
                    for m in result.metrics:
                        if m.metric_name == metric.value:
                            metric_scores.append(m.score)
                
                if metric_scores:
                    comparison["metrics_comparison"][metric.value][exp_id] = {
                        "mean": statistics.mean(metric_scores),
                        "std": statistics.stdev(metric_scores) if len(metric_scores) > 1 else 0
                    }
        
        # 找出最佳实验
        if scores:
            winner_id = max(scores, key=scores.get)
            comparison["winner"] = {
                "experiment_id": winner_id,
                "score": scores[winner_id]
            }
        
        return comparison
    
    # ==================== 优化建议 ====================
    
    def generate_optimization_suggestions(self, 
                                         evaluation: RAGEvaluationResult) -> List[Dict]:
        """生成优化建议"""
        suggestions = []
        
        for metric_result in evaluation.metrics:
            if metric_result.score < 0.5:
                if metric_result.metric_name == RAGMetric.CONTEXT_PRECISION.value:
                    suggestions.append({
                        "priority": "high",
                        "area": "retrieval",
                        "issue": "上下文精确率低",
                        "suggestion": "考虑优化检索策略，使用重排序(reranking)或混合搜索",
                        "current_score": metric_result.score
                    })
                
                elif metric_result.metric_name == RAGMetric.CONTEXT_RECALL.value:
                    suggestions.append({
                        "priority": "high",
                        "area": "retrieval",
                        "issue": "上下文召回率低",
                        "suggestion": "增加检索结果数量或调整相似度阈值",
                        "current_score": metric_result.score
                    })
                
                elif metric_result.metric_name == RAGMetric.FAITHFULNESS.value:
                    suggestions.append({
                        "priority": "critical",
                        "area": "generation",
                        "issue": "答案忠实度低，可能存在幻觉",
                        "suggestion": "加强提示词约束，要求模型严格基于上下文回答",
                        "current_score": metric_result.score
                    })
                
                elif metric_result.metric_name == RAGMetric.ANSWER_RELEVANCE.value:
                    suggestions.append({
                        "priority": "medium",
                        "area": "generation",
                        "issue": "答案相关性低",
                        "suggestion": "优化提示词，明确要求回答问题的核心",
                        "current_score": metric_result.score
                    })
        
        return suggestions
    
    # ==================== 基准测试 ====================
    
    def create_benchmark(self, name: str, test_cases: List[RAGTestCase]) -> str:
        """创建基准测试集"""
        benchmark_id = f"bench_{uuid.uuid4().hex[:8]}"
        self.benchmarks[benchmark_id] = test_cases
        return benchmark_id
    
    async def run_benchmark(self, benchmark_id: str,
                           rag_pipeline: Callable) -> Dict[str, Any]:
        """运行基准测试"""
        test_cases = self.benchmarks.get(benchmark_id, [])
        if not test_cases:
            return {"error": "Benchmark not found"}
        
        results = []
        for test_case in test_cases:
            # 使用提供的RAG管道生成答案
            try:
                result = await rag_pipeline(test_case.question)
                test_case.answer = result.get("answer", "")
                test_case.contexts = result.get("contexts", [])
                
                evaluation = await self.evaluate(test_case)
                results.append(evaluation)
            except Exception as e:
                print(f"评估失败: {e}")
        
        # 计算统计信息
        if results:
            overall_scores = [r.overall_score for r in results]
            return {
                "benchmark_id": benchmark_id,
                "total_cases": len(test_cases),
                "successful_evaluations": len(results),
                "avg_overall_score": statistics.mean(overall_scores),
                "min_score": min(overall_scores),
                "max_score": max(overall_scores),
                "std_score": statistics.stdev(overall_scores) if len(overall_scores) > 1 else 0,
                "detailed_results": [r.to_dict() for r in results]
            }
        
        return {"error": "No successful evaluations"}
    
    # ==================== 报告生成 ====================
    
    def generate_report(self, experiment_id: str = None) -> Dict[str, Any]:
        """生成评估报告"""
        if experiment_id:
            experiment = self.experiments.get(experiment_id)
            if not experiment:
                return {"error": "Experiment not found"}
            
            results = experiment.results
        else:
            results = self.evaluations
        
        if not results:
            return {"error": "No evaluation results"}
        
        # 计算各项指标的平均值
        metric_scores = defaultdict(list)
        for result in results:
            for metric in result.metrics:
                metric_scores[metric.metric_name].append(metric.score)
        
        metrics_summary = {
            metric: {
                "mean": statistics.mean(scores),
                "median": statistics.median(scores),
                "std": statistics.stdev(scores) if len(scores) > 1 else 0,
                "min": min(scores),
                "max": max(scores)
            }
            for metric, scores in metric_scores.items()
        }
        
        overall_scores = [r.overall_score for r in results]
        
        return {
            "experiment_id": experiment_id,
            "total_evaluations": len(results),
            "overall_score": {
                "mean": statistics.mean(overall_scores),
                "median": statistics.median(overall_scores),
                "std": statistics.stdev(overall_scores) if len(overall_scores) > 1 else 0
            },
            "metrics_summary": metrics_summary,
            "best_performing_cases": sorted(
                results, key=lambda x: x.overall_score, reverse=True
            )[:5],
            "worst_performing_cases": sorted(
                results, key=lambda x: x.overall_score
            )[:5]
        }


# ==================== 全局实例 ====================

_default_rag_evaluator: Optional[RAGEvaluator] = None


def get_rag_evaluator() -> RAGEvaluator:
    """获取默认RAG评估器"""
    global _default_rag_evaluator
    if _default_rag_evaluator is None:
        _default_rag_evaluator = RAGEvaluator()
    return _default_rag_evaluator


# ==================== 使用示例 ====================

async def example_usage():
    """使用示例"""
    evaluator = get_rag_evaluator()
    
    # 创建测试用例
    test_case = RAGTestCase(
        test_id="test_001",
        question="什么是RAG？",
        ground_truth="RAG（检索增强生成）是一种结合信息检索和文本生成的技术。",
        contexts=[
            "RAG（Retrieval-Augmented Generation）是一种AI技术。",
            "它将信息检索与语言模型结合，提高生成质量。",
            "RAG可以减少幻觉，提高答案的准确性。"
        ],
        answer="RAG是检索增强生成技术，结合了信息检索和语言模型。"
    )
    
    # 执行评估
    result = await evaluator.evaluate(test_case)
    
    print(f"评估结果:")
    print(f"  综合得分: {result.overall_score:.3f}")
    print(f"  各项指标:")
    for metric in result.metrics:
        print(f"    - {metric.metric_name}: {metric.score:.3f}")
        print(f"      {metric.explanation}")
    
    # 生成优化建议
    suggestions = evaluator.generate_optimization_suggestions(result)
    if suggestions:
        print(f"\n优化建议:")
        for suggestion in suggestions:
            print(f"  [{suggestion['priority']}] {suggestion['issue']}")
            print(f"    建议: {suggestion['suggestion']}")


if __name__ == "__main__":
    asyncio.run(example_usage())
