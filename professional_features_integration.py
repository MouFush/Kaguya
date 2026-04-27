#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Professional Features Integration - 专业级功能整合模块
整合LLM可观测性、RAG评估、模型路由等高级功能
"""

import asyncio
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

# 导入专业级功能模块
from llm_observability_platform import (
    get_observability_platform, SpanType, TokenUsage, TraceStatus
)
from rag_evaluation_framework import (
    get_rag_evaluator, RAGTestCase, RAGMetric
)
from model_router_gateway import (
    get_model_router, RoutingStrategy, ModelProvider
)


class ProfessionalFeaturesIntegration:
    """专业级功能整合管理器"""
    
    def __init__(self):
        self.observability = get_observability_platform()
        self.rag_evaluator = get_rag_evaluator()
        self.model_router = get_model_router()
        self.initialized = False
    
    async def initialize(self):
        """初始化所有专业级功能"""
        if self.initialized:
            return
        
        print("=" * 70)
        print("🚀 初始化辉夜AI平台专业级功能")
        print("=" * 70)
        
        # 1. 初始化模型路由
        self._init_model_router()
        
        # 2. 初始化可观测性
        self._init_observability()
        
        # 3. 初始化RAG评估
        self._init_rag_evaluation()
        
        self.initialized = True
        print("=" * 70)
        print("✅ 专业级功能初始化完成")
        print("=" * 70)
    
    def _init_model_router(self):
        """初始化模型路由器"""
        # 注册本地模型端点
        self.model_router.register_local_endpoint(
            "qwen3.5-9b",
            "http://localhost:5000"
        )
        
        # 设置默认路由策略
        self.model_router.routing_strategy = RoutingStrategy.WEIGHTED
        
        print("✅ 模型路由器初始化完成")
    
    def _init_observability(self):
        """初始化可观测性平台"""
        # 创建示例提示词
        self.observability.create_prompt(
            "qa_system",
            "Question: {question}\nContext: {context}\nAnswer: ",
            variables=["question", "context"]
        )
        
        print("✅ 可观测性平台初始化完成")
    
    def _init_rag_evaluation(self):
        """初始化RAG评估"""
        # 创建示例测试用例
        test_case = RAGTestCase(
            test_id="demo_001",
            question="什么是人工智能？",
            ground_truth="人工智能是模拟人类智能的技术。",
            contexts=["AI是一种技术", "它模拟人类智能"],
            answer="人工智能是模拟人类智能的技术。"
        )
        
        print("✅ RAG评估框架初始化完成")
    
    # ==================== API方法 ====================
    
    async def route_and_generate(self, prompt: str, model: str = None,
                                 **kwargs) -> Dict[str, Any]:
        """路由并生成文本"""
        # 使用模型路由器
        result = await self.model_router.generate(prompt, model, **kwargs)
        return result
    
    async def start_traced_generation(self, name: str, prompt: str,
                                     user_id: str = None) -> Dict[str, Any]:
        """开始带追踪的生成"""
        # 开始追踪
        trace = self.observability.start_trace(
            name=name,
            user_id=user_id,
            metadata={"prompt": prompt[:100]}
        )
        
        # 创建LLM跨度
        span = self.observability.start_span(
            trace.trace_id,
            SpanType.LLM,
            "text_generation",
            input_data=prompt
        )
        
        # 路由并生成
        result = await self.route_and_generate(prompt)
        
        # 更新Token使用量
        if "tokens" in result:
            tokens = result["tokens"]
            self.observability.update_span_tokens(
                span.span_id,
                TokenUsage(
                    prompt_tokens=tokens.get("input", 0),
                    completion_tokens=tokens.get("output", 0),
                    total_tokens=tokens.get("total", 0)
                )
            )
        
        # 结束跨度
        self.observability.end_span(
            span.span_id,
            output=result.get("text", "")[:200]
        )
        
        # 结束追踪
        self.observability.end_trace(
            trace.trace_id,
            TraceStatus.SUCCESS if "error" not in result else TraceStatus.ERROR
        )
        
        # 自动评估
        self.observability.run_auto_evaluation(trace.trace_id)
        
        return {
            **result,
            "trace_id": trace.trace_id
        }
    
    async def evaluate_rag(self, question: str, ground_truth: str,
                          contexts: List[str], answer: str) -> Dict[str, Any]:
        """评估RAG性能"""
        test_case = RAGTestCase(
            test_id=f"eval_{datetime.now().timestamp()}",
            question=question,
            ground_truth=ground_truth,
            contexts=contexts,
            answer=answer
        )
        
        result = await self.rag_evaluator.evaluate(test_case)
        
        # 生成优化建议
        suggestions = self.rag_evaluator.generate_optimization_suggestions(result)
        
        return {
            "evaluation_id": result.evaluation_id,
            "overall_score": result.overall_score,
            "metrics": [m.to_dict() for m in result.metrics],
            "suggestions": suggestions,
            "duration_ms": result.duration_ms
        }
    
    def get_observability_dashboard(self) -> Dict[str, Any]:
        """获取可观测性仪表板数据"""
        return self.observability.get_dashboard_data()
    
    def get_router_stats(self) -> Dict[str, Any]:
        """获取路由器统计"""
        return {
            "routing": self.model_router.get_routing_stats(),
            "usage": self.model_router.get_usage_stats(hours=24),
            "cost_projection": self.model_router.get_cost_projection(daily_tokens=50000)
        }
    
    def get_rag_stats(self) -> Dict[str, Any]:
        """获取RAG评估统计"""
        return {
            "total_evaluations": len(self.rag_evaluator.evaluations),
            "experiments": [e.to_dict() for e in self.rag_evaluator.experiments.values()],
            "recent_results": [e.to_dict() for e in self.rag_evaluator.evaluations[-10:]]
        }
    
    def get_professional_features_status(self) -> Dict[str, Any]:
        """获取专业级功能状态"""
        return {
            "initialized": self.initialized,
            "components": {
                "model_router": {
                    "endpoints": len(self.model_router.endpoints),
                    "strategy": self.model_router.routing_strategy.value
                },
                "observability": {
                    "traces": len(self.observability.traces),
                    "prompts": len(self.observability.prompts),
                    "datasets": len(self.observability.datasets)
                },
                "rag_evaluation": {
                    "evaluations": len(self.rag_evaluator.evaluations),
                    "experiments": len(self.rag_evaluator.experiments)
                }
            }
        }


# ==================== 全局实例 ====================

_professional_features: Optional[ProfessionalFeaturesIntegration] = None


def get_professional_features() -> ProfessionalFeaturesIntegration:
    """获取专业级功能整合实例"""
    global _professional_features
    if _professional_features is None:
        _professional_features = ProfessionalFeaturesIntegration()
    return _professional_features


# ==================== Flask路由注册 ====================

def register_professional_features_routes(app):
    """注册专业级功能路由"""
    
    @app.route('/api/professional/status')
    def get_professional_status():
        """获取专业级功能状态"""
        features = get_professional_features()
        return jsonify(features.get_professional_features_status())
    
    @app.route('/api/professional/router/generate', methods=['POST'])
    def router_generate():
        """通过路由器生成"""
        from flask import request
        data = request.get_json()
        features = get_professional_features()
        
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(features.route_and_generate(
                prompt=data.get('prompt', ''),
                model=data.get('model'),
                max_tokens=data.get('max_tokens', 512),
                temperature=data.get('temperature', 0.7)
            ))
            return jsonify(result)
        except Exception as e:
            return jsonify({"error": str(e)})
    
    @app.route('/api/professional/observability/dashboard')
    def get_observability_dashboard():
        """获取可观测性仪表板"""
        features = get_professional_features()
        return jsonify(features.get_observability_dashboard())
    
    @app.route('/api/professional/router/stats')
    def get_router_stats():
        """获取路由器统计"""
        features = get_professional_features()
        return jsonify(features.get_router_stats())
    
    @app.route('/api/professional/rag/evaluate', methods=['POST'])
    def evaluate_rag():
        """评估RAG"""
        from flask import request
        data = request.get_json()
        features = get_professional_features()
        
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(features.evaluate_rag(
                question=data.get('question', ''),
                ground_truth=data.get('ground_truth', ''),
                contexts=data.get('contexts', []),
                answer=data.get('answer', '')
            ))
            return jsonify(result)
        except Exception as e:
            return jsonify({"error": str(e)})
    
    @app.route('/api/professional/rag/stats')
    def get_rag_stats():
        """获取RAG统计"""
        features = get_professional_features()
        return jsonify(features.get_rag_stats())
    
    print("✅ 专业级功能路由注册完成")


# ==================== 初始化函数 ====================

def initialize_professional_features():
    """初始化专业级功能"""
    features = get_professional_features()
    
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(features.initialize())
        else:
            loop.run_until_complete(features.initialize())
    except RuntimeError:
        asyncio.run(features.initialize())


if __name__ == "__main__":
    # 测试
    async def test():
        features = get_professional_features()
        await features.initialize()
        
        # 测试路由生成
        result = await features.route_and_generate("解释什么是AI")
        print(f"路由生成结果: {result}")
        
        # 测试RAG评估
        eval_result = await features.evaluate_rag(
            question="什么是AI？",
            ground_truth="人工智能是模拟人类智能的技术。",
            contexts=["AI是一种技术", "它模拟人类智能"],
            answer="人工智能是模拟人类智能的技术。"
        )
        print(f"RAG评估结果: {eval_result}")
    
    asyncio.run(test())
