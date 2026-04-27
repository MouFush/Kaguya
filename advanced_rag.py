"""
Advanced RAG Module - 专业级检索增强生成系统
基于GitHub开源项目和业界最佳实践实现
"""

import numpy as np
import re
import json
import time
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict
import heapq

@dataclass
class RAGConfig:
    """RAG配置类"""
    # 检索配置
    top_k: int = 5
    hybrid_alpha: float = 0.5  # 混合检索权重
    rerank_top_k: int = 10  # 重排序前K个
    
    # 查询优化
    use_query_expansion: bool = True
    use_multi_query: bool = True
    use_hyde: bool = False  # Hypothetical Document Embedding
    use_decomposition: bool = False
    
    # 检索策略
    use_hybrid_search: bool = True
    use_bm25: bool = True
    use_vector: bool = True
    use_rrf: bool = True  # Reciprocal Rank Fusion
    
    # 重排序
    use_rerank: bool = True
    rerank_model: str = 'cross_encoder'  # 或 'bge'
    
    # 后处理
    use_context_compression: bool = False
    use_answer_refinement: bool = True
    
    # 评估
    use_retrieval_eval: bool = False


class QueryOptimizer:
    """查询优化器 - 实现查询扩展、重写和分解"""
    
    def __init__(self):
        self.expansion_patterns = {
            'synonyms': {
                '如何': ['怎么', '怎样', '用什么方法'],
                '什么是': ['定义', '概念', '含义'],
                '为什么': ['原因', '理由', '原理'],
                '比较': ['对比', '区别', '差异'],
            }
        }
    
    def expand_query(self, query: str, num_expansions: int = 3) -> List[str]:
        """查询扩展 - 生成语义相似的查询变体"""
        expansions = [query]
        
        # 同义词替换
        for key, synonyms in self.expansion_patterns['synonyms'].items():
            if key in query:
                for syn in synonyms[:num_expansions]:
                    new_query = query.replace(key, syn, 1)
                    if new_query not in expansions:
                        expansions.append(new_query)
        
        # 添加疑问词变体
        if '?' not in query:
            expansions.append(query + '？')
        
        return expansions[:num_expansions + 1]
    
    def decompose_query(self, query: str) -> List[str]:
        """查询分解 - 将复杂查询分解为子查询"""
        sub_queries = []
        
        # 识别并列结构
        patterns = [
            r'(.*?)和(.*?)的区别',
            r'(.*?)与(.*?)的比较',
            r'(.*?)还是(.*?)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query)
            if match:
                sub_queries.append(f"什么是{match.group(1)}")
                sub_queries.append(f"什么是{match.group(2)}")
                sub_queries.append(query)
                return sub_queries
        
        # 如果没有匹配到模式，返回原查询
        return [query]
    
    def generate_multi_queries(self, query: str, num_queries: int = 3) -> List[str]:
        """生成多角度查询 - Multi-Query策略"""
        queries = [query]
        
        # 角度1: 更具体的查询
        queries.append(f"详细介绍{query}")
        
        # 角度2: 实际应用角度
        queries.append(f"{query}的应用")
        
        # 角度3: 优缺点角度
        queries.append(f"{query}的优缺点")
        
        return queries[:num_queries + 1]
    
    def rewrite_query(self, query: str, history: List[Tuple[str, str]] = None) -> str:
        """查询重写 - 基于对话历史优化查询"""
        if not history or len(history) == 0:
            return query
        
        # 检查是否是代词引用
        pronouns = ['它', '这个', '那个', '这些', '那些']
        if any(p in query for p in pronouns):
            # 获取上一轮对话的主题
            last_topic = history[-1][0] if history else ""
            # 替换代词
            for p in pronouns:
                if p in query:
                    query = query.replace(p, last_topic[:20])
                    break
        
        return query


class HybridRetriever:
    """混合检索器 - 结合多种检索策略"""
    
    def __init__(self, config: RAGConfig):
        self.config = config
        self.bm25_params = {'k1': 1.5, 'b': 0.75}
    
    def bm25_score(self, query_tokens: List[str], doc_tokens: List[str], 
                   doc_freqs: Dict, doc_length: int, avgdl: float) -> float:
        """BM25评分"""
        score = 0.0
        for term in query_tokens:
            if term in doc_freqs:
                idf = np.log((len(doc_freqs) - doc_freqs[term] + 0.5) / (doc_freqs[term] + 0.5) + 1)
                tf = doc_tokens.count(term)
                numerator = tf * (self.bm25_params['k1'] + 1)
                denominator = tf + self.bm25_params['k1'] * (1 - self.bm25_params['b'] + self.bm25_params['b'] * (doc_length / avgdl))
                score += idf * numerator / denominator
        return score
    
    def vector_search(self, query_embedding: np.ndarray, 
                      doc_embeddings: List[np.ndarray]) -> List[Tuple[int, float]]:
        """向量相似度搜索"""
        scores = []
        for i, doc_emb in enumerate(doc_embeddings):
            similarity = np.dot(query_embedding, doc_emb) / (np.linalg.norm(query_embedding) * np.linalg.norm(doc_emb) + 1e-8)
            scores.append((i, similarity))
        return sorted(scores, key=lambda x: x[1], reverse=True)
    
    def reciprocal_rank_fusion(self, results_lists: List[List[Dict]], 
                               k: int = 60, top_n: int = 10) -> List[Dict]:
        """RRF - 倒数排名融合"""
        scores = defaultdict(float)
        doc_info = {}
        
        for results in results_lists:
            for rank, doc in enumerate(results):
                doc_id = doc.get('chunk_id', doc.get('id', str(rank)))
                scores[doc_id] += 1 / (k + rank + 1)
                if doc_id not in doc_info:
                    doc_info[doc_id] = doc
        
        # 排序并返回
        sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [doc_info[doc_id] for doc_id, _ in sorted_docs[:top_n]]


class Reranker:
    """重排序器 - 使用更精确的模型进行重排序"""
    
    def __init__(self, method: str = 'cross_encoder'):
        self.method = method
        self.cross_encoder = None
        
        if method == 'bge':
            try:
                from sentence_transformers import CrossEncoder
                self.cross_encoder = CrossEncoder('BAAI/bge-reranker-base')
            except:
                print("BGE Reranker加载失败，使用基础重排序")
                self.method = 'basic'
    
    def rerank(self, query: str, documents: List[Dict], top_k: int = 5) -> List[Dict]:
        """重排序文档"""
        if not documents:
            return documents
        
        if self.method == 'bge' and self.cross_encoder:
            return self._bge_rerank(query, documents, top_k)
        else:
            return self._basic_rerank(query, documents, top_k)
    
    def _bge_rerank(self, query: str, documents: List[Dict], top_k: int) -> List[Dict]:
        """使用BGE模型重排序"""
        pairs = [[query, doc['text']] for doc in documents]
        scores = self.cross_encoder.predict(pairs)
        
        for doc, score in zip(documents, scores):
            doc['rerank_score'] = float(score)
        
        return sorted(documents, key=lambda x: x['rerank_score'], reverse=True)[:top_k]
    
    def _basic_rerank(self, query: str, documents: List[Dict], top_k: int) -> List[Dict]:
        """基础重排序 - 基于关键词匹配"""
        query_tokens = set(query.lower().split())
        
        for doc in documents:
            text = doc['text'].lower()
            
            # 精确匹配加分
            exact_match_score = 0
            for token in query_tokens:
                if token in text:
                    exact_match_score += 1
            
            # 位置加分（关键词出现在文档前面）
            position_score = 0
            for i, token in enumerate(query_tokens):
                pos = text.find(token)
                if pos != -1:
                    position_score += 1 / (1 + pos / 100)
            
            # 长度惩罚（避免过长文档）
            length_penalty = 1 / (1 + len(text) / 1000)
            
            # 综合得分
            doc['rerank_score'] = (
                doc.get('score', 0) * 0.4 +
                exact_match_score * 0.3 +
                position_score * 0.2 +
                length_penalty * 0.1
            )
        
        return sorted(documents, key=lambda x: x['rerank_score'], reverse=True)[:top_k]


class ContextProcessor:
    """上下文处理器 - 优化检索结果的上下文"""
    
    def __init__(self):
        self.max_context_length = 4000
    
    def compress_context(self, documents: List[Dict], query: str) -> List[Dict]:
        """上下文压缩 - 移除冗余信息"""
        if not documents:
            return documents
        
        compressed = []
        total_length = 0
        
        for doc in documents:
            text = doc['text']
            
            # 如果文档太长，提取关键句子
            if len(text) > 500:
                sentences = re.split(r'[。！？.!?]', text)
                # 保留前3个句子
                text = '。'.join(sentences[:3]) + '。'
            
            doc['text'] = text
            total_length += len(text)
            compressed.append(doc)
            
            if total_length > self.max_context_length:
                break
        
        return compressed
    
    def add_citations(self, documents: List[Dict]) -> str:
        """添加引用标记"""
        context_parts = []
        for i, doc in enumerate(documents):
            citation = f"[{i+1}] {doc.get('doc_name', 'Unknown')}"
            context_parts.append(f"{citation}\n{doc['text']}")
        
        return "\n\n".join(context_parts)


class RAGEvaluator:
    """RAG评估器 - 评估检索质量"""
    
    def __init__(self):
        self.metrics = {}
    
    def evaluate_retrieval(self, query: str, retrieved_docs: List[Dict], 
                          ground_truth: List[str] = None) -> Dict:
        """评估检索质量"""
        metrics = {
            'retrieval_count': len(retrieved_docs),
            'avg_score': np.mean([d.get('score', 0) for d in retrieved_docs]) if retrieved_docs else 0,
            'diversity': self._calculate_diversity(retrieved_docs),
            'coverage': self._calculate_coverage(query, retrieved_docs)
        }
        
        return metrics
    
    def _calculate_diversity(self, documents: List[Dict]) -> float:
        """计算文档多样性"""
        if len(documents) <= 1:
            return 1.0
        
        # 基于文档来源计算多样性
        sources = set(d.get('doc_id') for d in documents)
        return len(sources) / len(documents)
    
    def _calculate_coverage(self, query: str, documents: List[Dict]) -> float:
        """计算查询覆盖度"""
        query_terms = set(query.lower().split())
        if not query_terms:
            return 0.0
        
        covered_terms = set()
        for doc in documents:
            text = doc['text'].lower()
            for term in query_terms:
                if term in text:
                    covered_terms.add(term)
        
        return len(covered_terms) / len(query_terms)


class AdvancedRAG:
    """高级RAG系统 - 整合所有组件"""
    
    def __init__(self, config: RAGConfig = None):
        self.config = config or RAGConfig()
        self.query_optimizer = QueryOptimizer()
        self.retriever = HybridRetriever(self.config)
        self.reranker = Reranker(self.config.rerank_model)
        self.context_processor = ContextProcessor()
        self.evaluator = RAGEvaluator()
    
    def retrieve(self, query: str, chunks: List[Dict], embeddings: List[np.ndarray],
                 history: List[Tuple[str, str]] = None) -> Dict:
        """执行完整的检索流程"""
        start_time = time.time()
        
        # 1. 查询优化
        optimized_query = self.query_optimizer.rewrite_query(query, history)
        
        all_results = []
        
        # 2. 多查询检索
        if self.config.use_multi_query:
            multi_queries = self.query_optimizer.generate_multi_queries(optimized_query)
            for mq in multi_queries:
                results = self._single_retrieve(mq, chunks, embeddings)
                for r in results:
                    r['source_query'] = mq
                all_results.append(results)
        else:
            all_results.append(self._single_retrieve(optimized_query, chunks, embeddings))
        
        # 3. 查询扩展
        if self.config.use_query_expansion:
            expanded_queries = self.query_optimizer.expand_query(optimized_query)
            for eq in expanded_queries[1:]:  # 跳过原查询
                results = self._single_retrieve(eq, chunks, embeddings)
                for r in results:
                    r['source_query'] = eq
                all_results.append(results)
        
        # 4. 查询分解
        if self.config.use_decomposition:
            sub_queries = self.query_optimizer.decompose_query(optimized_query)
            for sq in sub_queries:
                results = self._single_retrieve(sq, chunks, embeddings)
                for r in results:
                    r['source_query'] = sq
                all_results.append(results)
        
        # 5. 融合结果
        if self.config.use_rrf and len(all_results) > 1:
            final_results = self.retriever.reciprocal_rank_fusion(
                all_results, top_n=self.config.rerank_top_k
            )
        else:
            # 简单合并去重
            seen = set()
            final_results = []
            for results in all_results:
                for r in results:
                    if r['chunk_id'] not in seen:
                        seen.add(r['chunk_id'])
                        final_results.append(r)
            final_results = final_results[:self.config.rerank_top_k]
        
        # 6. 重排序
        if self.config.use_rerank:
            final_results = self.reranker.rerank(
                optimized_query, final_results, self.config.top_k
            )
        
        # 7. 上下文压缩
        if self.config.use_context_compression:
            final_results = self.context_processor.compress_context(
                final_results, optimized_query
            )
        
        # 8. 评估
        eval_metrics = {}
        if self.config.use_retrieval_eval:
            eval_metrics = self.evaluator.evaluate_retrieval(
                optimized_query, final_results
            )
        
        retrieval_time = time.time() - start_time
        
        return {
            'results': final_results,
            'optimized_query': optimized_query,
            'num_queries': len(all_results),
            'retrieval_time': retrieval_time,
            'eval_metrics': eval_metrics
        }
    
    def _single_retrieve(self, query: str, chunks: List[Dict], 
                        embeddings: List[np.ndarray]) -> List[Dict]:
        """单次检索"""
        # 简化的向量检索
        query_emb = self._simple_embedding(query)
        
        scores = []
        for i, emb in enumerate(embeddings):
            similarity = np.dot(query_emb, emb) / (np.linalg.norm(query_emb) * np.linalg.norm(emb) + 1e-8)
            if similarity > 0.1:  # 阈值过滤
                chunk = chunks[i]
                scores.append({
                    'chunk_id': chunk.get('id', i),
                    'text': chunk.get('text', ''),
                    'score': float(similarity),
                    'doc_id': chunk.get('doc_id', ''),
                    'doc_name': chunk.get('doc_name', 'Unknown')
                })
        
        scores.sort(key=lambda x: x['score'], reverse=True)
        return scores[:self.config.rerank_top_k]
    
    def _simple_embedding(self, text: str) -> np.ndarray:
        """简化的文本嵌入 - 使用TF-IDF思想"""
        # 这里应该使用真实的embedding模型
        # 简化实现：基于词频的one-hot编码
        words = text.lower().split()
        vocab = list(set(words))
        vec = np.zeros(len(vocab))
        for word in words:
            if word in vocab:
                vec[vocab.index(word)] += 1
        
        # 归一化
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        
        return vec


# 全局RAG实例
_default_rag = None

def get_advanced_rag(config: RAGConfig = None) -> AdvancedRAG:
    """获取或创建AdvancedRAG实例"""
    global _default_rag
    if _default_rag is None:
        _default_rag = AdvancedRAG(config)
    return _default_rag
