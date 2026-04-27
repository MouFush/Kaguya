"""
Advanced RAG v2 - 更深化的专业级RAG系统
基于CRAG、Self-RAG、FLARE等最新研究实现
"""

import numpy as np
import re
import json
import time
import hashlib
from typing import List, Dict, Any, Tuple, Optional, Callable
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum
import heapq

class RetrievalStrategy(Enum):
    """检索策略枚举"""
    NAIVE = "naive"  # 朴素检索
    ADAPTIVE = "adaptive"  # 自适应检索
    MULTI_STEP = "multi_step"  # 多步检索
    ITERATIVE = "iterative"  # 迭代检索
    AGENTIC = "agentic"  # 智能体检索

class ChunkingStrategy(Enum):
    """文档切分策略"""
    FIXED = "fixed"  # 固定大小
    RECURSIVE = "recursive"  # 递归切分
    SEMANTIC = "semantic"  # 语义切分
    MARKDOWN = "markdown"  # Markdown标题切分
    SENTENCE = "sentence"  # 句子切分

@dataclass
class RAGState:
    """RAG状态跟踪"""
    query: str = ""
    original_query: str = ""
    retrieval_count: int = 0
    documents: List[Dict] = field(default_factory=list)
    scores: List[float] = field(default_factory=list)
    confidence: float = 0.0
    needs_correction: bool = False
    correction_attempts: int = 0
    max_corrections: int = 3

@dataclass
class ChunkingConfig:
    """切分配置"""
    strategy: ChunkingStrategy = ChunkingStrategy.RECURSIVE
    chunk_size: int = 500
    chunk_overlap: int = 100
    separators: List[str] = field(default_factory=lambda: ["\n\n", "\n", "。", "；", " ", ""])
    min_chunk_size: int = 100
    max_chunk_size: int = 1000

class SemanticChunker:
    """语义切分器 - 基于语义相似度进行切分"""
    
    def __init__(self, embedding_func: Optional[Callable] = None):
        self.embedding_func = embedding_func or self._default_embedding
        self.similarity_threshold = 0.8
    
    def _default_embedding(self, text: str) -> np.ndarray:
        """默认嵌入函数 - 基于词频"""
        words = text.lower().split()
        vocab = list(set(words))
        vec = np.zeros(len(vocab))
        for word in words:
            if word in vocab:
                vec[vocab.index(word)] += 1
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec
    
    def split_text(self, text: str, target_chunk_size: int = 500) -> List[str]:
        """基于语义相似度切分文本"""
        # 首先按句子切分
        sentences = re.split(r'([。！？.!?])', text)
        sentences = [''.join(i) for i in zip(sentences[::2], sentences[1::2] + [''])]
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return [text]
        
        chunks = []
        current_chunk = [sentences[0]]
        current_size = len(sentences[0])
        
        for i in range(1, len(sentences)):
            prev_emb = self.embedding_func(sentences[i-1])
            curr_emb = self.embedding_func(sentences[i])
            similarity = np.dot(prev_emb, curr_emb)
            
            # 如果语义相似度低或当前块太大，开始新块
            if similarity < self.similarity_threshold or current_size > target_chunk_size:
                chunks.append(''.join(current_chunk))
                current_chunk = [sentences[i]]
                current_size = len(sentences[i])
            else:
                current_chunk.append(sentences[i])
                current_size += len(sentences[i])
        
        if current_chunk:
            chunks.append(''.join(current_chunk))
        
        return chunks

class RecursiveCharacterTextSplitter:
    """递归字符切分器 - LangChain风格的多级切分"""
    
    def __init__(self, separators: List[str] = None, 
                 chunk_size: int = 500, chunk_overlap: int = 100):
        self.separators = separators or ["\n\n", "\n", "。", "；", "，", " ", ""]
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def split_text(self, text: str) -> List[str]:
        """递归切分文本"""
        return self._split_text_recursive(text, self.separators)
    
    def _split_text_recursive(self, text: str, separators: List[str]) -> List[str]:
        """递归切分实现"""
        if not text:
            return []
        
        # 如果文本小于块大小，直接返回
        if len(text) <= self.chunk_size:
            return [text]
        
        # 如果没有分隔符了，强制切分
        if not separators:
            return [text[i:i+self.chunk_size] for i in range(0, len(text), self.chunk_size - self.chunk_overlap)]
        
        separator = separators[0]
        next_separators = separators[1:]
        
        # 按当前分隔符切分
        if separator:
            splits = text.split(separator)
        else:
            splits = list(text)
        
        # 合并小块
        chunks = []
        current_chunk = ""
        
        for split in splits:
            # 添加分隔符回来（除了最后一个）
            split_with_sep = split + separator if separator and split != splits[-1] else split
            
            if len(current_chunk) + len(split_with_sep) <= self.chunk_size:
                current_chunk += split_with_sep
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                    # 保留重叠部分
                    if self.chunk_overlap > 0:
                        current_chunk = current_chunk[-self.chunk_overlap:] + split_with_sep
                    else:
                        current_chunk = split_with_sep
                else:
                    # 单个split就超过块大小，需要递归切分
                    if next_separators:
                        sub_chunks = self._split_text_recursive(split_with_sep, next_separators)
                        chunks.extend(sub_chunks)
                    else:
                        chunks.append(split_with_sep)
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks

class MarkdownTextSplitter:
    """Markdown文本切分器 - 按标题层级切分"""
    
    def __init__(self, headers_to_split_on: List[Tuple[str, str]] = None):
        self.headers_to_split_on = headers_to_split_on or [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
        ]
    
    def split_text(self, text: str) -> List[Dict]:
        """按Markdown标题切分文本"""
        lines = text.split('\n')
        chunks = []
        current_chunk = {"content": "", "metadata": {}}
        current_headers = {}
        
        for line in lines:
            # 检查是否是标题行
            is_header = False
            for header_char, header_name in self.headers_to_split_on:
                if line.strip().startswith(header_char + ' '):
                    # 保存当前块
                    if current_chunk["content"].strip():
                        current_chunk["metadata"].update(current_headers)
                        chunks.append(current_chunk)
                    
                    # 开始新块
                    header_text = line.strip()[len(header_char)+1:].strip()
                    current_headers[header_name] = header_text
                    current_chunk = {"content": line + "\n", "metadata": {}}
                    is_header = True
                    break
            
            if not is_header:
                current_chunk["content"] += line + "\n"
        
        # 保存最后一个块
        if current_chunk["content"].strip():
            current_chunk["metadata"].update(current_headers)
            chunks.append(current_chunk)
        
        return chunks

class CRAGSystem:
    """CRAG (Corrective RAG) 系统 - 自纠正检索"""
    
    def __init__(self, retriever: Callable, web_searcher: Optional[Callable] = None):
        self.retriever = retriever
        self.web_searcher = web_searcher
        self.confidence_threshold = 0.5
        self.max_attempts = 3
    
    def evaluate_retrieval_quality(self, query: str, documents: List[Dict]) -> Tuple[float, bool]:
        """评估检索质量"""
        if not documents:
            return 0.0, False
        
        # 计算平均相似度分数
        avg_score = np.mean([d.get('score', 0) for d in documents])
        
        # 计算文档多样性
        sources = set(d.get('doc_id') for d in documents)
        diversity = len(sources) / len(documents) if documents else 0
        
        # 计算查询覆盖度
        query_terms = set(query.lower().split())
        covered_terms = set()
        for doc in documents:
            text = doc.get('text', '').lower()
            for term in query_terms:
                if term in text:
                    covered_terms.add(term)
        coverage = len(covered_terms) / len(query_terms) if query_terms else 0
        
        # 综合评分
        confidence = avg_score * 0.4 + diversity * 0.3 + coverage * 0.3
        
        # 判断是否需要纠正
        needs_correction = confidence < self.confidence_threshold or len(documents) < 2
        
        return confidence, needs_correction
    
    def correct_retrieval(self, query: str, state: RAGState) -> List[Dict]:
        """纠正检索 - 使用网络搜索或查询重写"""
        if state.correction_attempts >= state.max_corrections:
            return state.documents
        
        state.correction_attempts += 1
        
        # 策略1: 查询重写
        rewritten_query = self._rewrite_query(query)
        new_docs = self.retriever(rewritten_query)
        
        # 策略2: 网络搜索（如果有）
        if self.web_searcher and state.correction_attempts > 1:
            web_results = self.web_searcher(query)
            new_docs.extend(web_results)
        
        # 合并结果
        all_docs = state.documents + new_docs
        
        # 去重
        seen = set()
        unique_docs = []
        for doc in all_docs:
            doc_id = doc.get('chunk_id', doc.get('id'))
            if doc_id not in seen:
                seen.add(doc_id)
                unique_docs.append(doc)
        
        return unique_docs
    
    def _rewrite_query(self, query: str) -> str:
        """重写查询以改善检索效果"""
        # 添加同义词
        expansions = {
            '如何': ['怎么', '怎样'],
            '什么是': ['定义', '概念'],
            '为什么': ['原因', '原理'],
        }
        
        rewritten = query
        for key, values in expansions.items():
            if key in query:
                rewritten += ' ' + ' '.join(values)
        
        return rewritten
    
    def retrieve_with_correction(self, query: str) -> Dict:
        """带纠正的检索"""
        state = RAGState(original_query=query, query=query)
        
        # 初始检索
        documents = self.retriever(query)
        state.documents = documents
        state.retrieval_count = 1
        
        # 评估质量
        confidence, needs_correction = self.evaluate_retrieval_quality(query, documents)
        state.confidence = confidence
        state.needs_correction = needs_correction
        
        # 如果需要纠正
        while needs_correction and state.correction_attempts < state.max_corrections:
            documents = self.correct_retrieval(query, state)
            state.documents = documents
            state.retrieval_count += 1
            
            confidence, needs_correction = self.evaluate_retrieval_quality(query, documents)
            state.confidence = confidence
            state.needs_correction = needs_correction
        
        return {
            'documents': documents,
            'state': state,
            'confidence': confidence,
            'retrieval_count': state.retrieval_count
        }

class SelfRAGSystem:
    """Self-RAG 系统 - 自反思检索生成"""
    
    def __init__(self, llm_func: Optional[Callable] = None):
        self.llm_func = llm_func
        self.reflection_prompt = """
        请评估以下检索结果是否足以回答用户问题。
        
        用户问题: {query}
        
        检索结果:
        {context}
        
        请回答:
        1. 检索结果是否包含足够信息回答问题? (是/否)
        2. 如果不足，还需要什么信息?
        3. 是否需要进一步检索? (是/否)
        """
    
    def reflect(self, query: str, documents: List[Dict]) -> Dict:
        """反思检索结果"""
        if not self.llm_func:
            return {'sufficient': True, 'feedback': ''}
        
        context = '\n\n'.join([d.get('text', '') for d in documents[:3]])
        prompt = self.reflection_prompt.format(query=query, context=context)
        
        # 这里应该调用LLM进行反思
        # 简化实现
        return {
            'sufficient': len(documents) >= 2,
            'feedback': '',
            'needs_more': len(documents) < 2
        }
    
    def generate_with_citation(self, query: str, documents: List[Dict]) -> Dict:
        """带引用的生成"""
        # 组织带引用的上下文
        cited_context = []
        for i, doc in enumerate(documents):
            citation = f"[{i+1}]"
            cited_context.append(f"{citation} {doc.get('text', '')}")
        
        context = '\n\n'.join(cited_context)
        
        return {
            'context': context,
            'citations': [f"[{i+1}] {d.get('doc_name', 'Unknown')}" for i, d in enumerate(documents)],
            'document_count': len(documents)
        }

class FLARESystem:
    """FLARE (Forward-Looking Active REtrieval) 系统 - 前瞻主动检索"""
    
    def __init__(self, retriever: Callable, llm_func: Optional[Callable] = None):
        self.retriever = retriever
        self.llm_func = llm_func
        self.lookahead_window = 50  # 前瞻窗口大小
    
    def generate_with_retrieval(self, query: str, max_tokens: int = 512) -> Dict:
        """生成过程中主动检索"""
        generated_text = ""
        all_retrieved_docs = []
        retrieval_points = []
        
        # 初始检索
        initial_docs = self.retriever(query)
        all_retrieved_docs.extend(initial_docs)
        
        # 模拟生成过程（实际应该使用LLM）
        current_context = query + '\n\n' + '\n\n'.join([d.get('text', '') for d in initial_docs[:2]])
        
        # 每生成一定token后检查是否需要检索
        for step in range(0, max_tokens, self.lookahead_window):
            # 检查是否需要更多检索
            if step > 0 and step % 100 == 0:
                # 基于已生成内容预测下一步需要什么信息
                predicted_need = self._predict_information_need(query, generated_text)
                if predicted_need:
                    new_docs = self.retriever(predicted_need)
                    all_retrieved_docs.extend(new_docs)
                    retrieval_points.append({'position': step, 'query': predicted_need})
        
        return {
            'generated_text': generated_text,
            'retrieved_documents': all_retrieved_docs,
            'retrieval_points': retrieval_points,
            'retrieval_count': len(retrieval_points) + 1
        }
    
    def _predict_information_need(self, original_query: str, generated_text: str) -> Optional[str]:
        """预测下一步需要什么信息"""
        # 简化实现：基于生成内容提取关键词
        # 实际应该使用LLM进行预测
        words = generated_text.split()[-10:]  # 最后10个词
        if words:
            return ' '.join(words)
        return None

class AdaptiveRAGRouter:
    """自适应RAG路由器 - 根据查询类型选择最佳策略"""
    
    def __init__(self):
        self.strategies = {
            'factual': {'retriever': 'dense', 'top_k': 5, 'rerank': True},
            'analytical': {'retriever': 'hybrid', 'top_k': 10, 'rerank': True},
            'procedural': {'retriever': 'dense', 'top_k': 3, 'rerank': False},
            'comparative': {'retriever': 'hybrid', 'top_k': 8, 'rerank': True},
            'creative': {'retriever': 'dense', 'top_k': 5, 'rerank': False},
        }
    
    def classify_query(self, query: str) -> str:
        """分类查询类型"""
        query_lower = query.lower()
        
        # 事实性查询
        if any(kw in query_lower for kw in ['什么是', '是谁', '在哪里', '什么时候', '多少']):
            return 'factual'
        
        # 分析性查询
        if any(kw in query_lower for kw in ['为什么', '如何', '怎么', '分析', '解释']):
            return 'analytical'
        
        # 程序性查询
        if any(kw in query_lower for kw in ['步骤', '流程', '怎么做', '教程']):
            return 'procedural'
        
        # 比较性查询
        if any(kw in query_lower for kw in ['比较', '对比', '区别', 'vs', '和']):
            return 'comparative'
        
        # 创造性查询
        if any(kw in query_lower for kw in ['生成', '创建', '写', '设计']):
            return 'creative'
        
        return 'factual'  # 默认
    
    def get_strategy(self, query: str) -> Dict:
        """获取查询策略"""
        query_type = self.classify_query(query)
        return self.strategies.get(query_type, self.strategies['factual'])

class RAGCache:
    """RAG缓存系统 - 优化重复查询性能"""
    
    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        self.cache = {}
        self.max_size = max_size
        self.ttl = ttl
        self.access_count = defaultdict(int)
    
    def _get_key(self, query: str, **kwargs) -> str:
        """生成缓存键"""
        key_data = json.dumps({'query': query, **kwargs}, sort_keys=True)
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, query: str, **kwargs) -> Optional[List[Dict]]:
        """获取缓存结果"""
        key = self._get_key(query, **kwargs)
        if key in self.cache:
            entry = self.cache[key]
            if time.time() - entry['timestamp'] < self.ttl:
                self.access_count[key] += 1
                return entry['data']
            else:
                del self.cache[key]
        return None
    
    def set(self, query: str, data: List[Dict], **kwargs):
        """设置缓存"""
        # 清理过期缓存
        self._cleanup()
        
        # 如果缓存已满，移除最少访问的
        if len(self.cache) >= self.max_size:
            lru_key = min(self.cache.keys(), key=lambda k: self.access_count[k])
            del self.cache[lru_key]
            del self.access_count[lru_key]
        
        key = self._get_key(query, **kwargs)
        self.cache[key] = {
            'data': data,
            'timestamp': time.time()
        }
        self.access_count[key] = 1
    
    def _cleanup(self):
        """清理过期缓存"""
        current_time = time.time()
        expired_keys = [
            k for k, v in self.cache.items()
            if current_time - v['timestamp'] > self.ttl
        ]
        for k in expired_keys:
            del self.cache[k]
            if k in self.access_count:
                del self.access_count[k]

class AdvancedRAGv2:
    """高级RAG v2 - 整合所有先进功能"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.chunkers = {
            ChunkingStrategy.RECURSIVE: RecursiveCharacterTextSplitter(),
            ChunkingStrategy.SEMANTIC: SemanticChunker(),
            ChunkingStrategy.MARKDOWN: MarkdownTextSplitter(),
            ChunkingStrategy.SENTENCE: RecursiveCharacterTextSplitter(
                separators=["。", "；", "！", "？", ".", ";", "!", "?"]
            ),
        }
        self.crag = None
        self.self_rag = SelfRAGSystem()
        self.flare = None
        self.router = AdaptiveRAGRouter()
        self.cache = RAGCache()
    
    def chunk_document(self, text: str, strategy: ChunkingStrategy = None, 
                       config: ChunkingConfig = None) -> List[Dict]:
        """智能文档切分"""
        strategy = strategy or ChunkingStrategy.RECURSIVE
        config = config or ChunkingConfig(strategy=strategy)
        
        chunker = self.chunkers.get(strategy, self.chunkers[ChunkingStrategy.RECURSIVE])
        
        if strategy == ChunkingStrategy.MARKDOWN:
            chunks = chunker.split_text(text)
        else:
            chunks_text = chunker.split_text(text)
            chunks = [{'text': t, 'metadata': {}} for t in chunks_text]
        
        # 添加元数据
        for i, chunk in enumerate(chunks):
            chunk['index'] = i
            chunk['char_count'] = len(chunk.get('text', ''))
            chunk['word_count'] = len(chunk.get('text', '').split())
        
        return chunks
    
    def retrieve(self, query: str, use_crag: bool = False, use_self_rag: bool = False,
                 use_adaptive: bool = True, **kwargs) -> Dict:
        """智能检索"""
        # 检查缓存
        cached = self.cache.get(query, **kwargs)
        if cached:
            return {
                'documents': cached,
                'from_cache': True,
                'strategy': 'cache'
            }
        
        # 自适应路由
        if use_adaptive:
            strategy = self.router.get_strategy(query)
            kwargs.update(strategy)
        
        # CRAG检索
        if use_crag and self.crag:
            result = self.crag.retrieve_with_correction(query)
            documents = result['documents']
        else:
            # 基础检索（这里应该调用实际的检索器）
            documents = []
        
        # Self-RAG反思
        if use_self_rag:
            reflection = self.self_rag.reflect(query, documents)
            if reflection.get('needs_more'):
                # 需要更多检索
                pass
        
        # 缓存结果
        self.cache.set(query, documents, **kwargs)
        
        return {
            'documents': documents,
            'from_cache': False,
            'strategy': strategy if use_adaptive else 'default'
        }
    
    def generate_with_citation(self, query: str, documents: List[Dict]) -> Dict:
        """带引用的生成"""
        return self.self_rag.generate_with_citation(query, documents)

# 全局实例
_default_rag_v2 = None

def get_advanced_rag_v2(config: Dict = None) -> AdvancedRAGv2:
    """获取或创建AdvancedRAGv2实例"""
    global _default_rag_v2
    if _default_rag_v2 is None:
        _default_rag_v2 = AdvancedRAGv2(config)
    return _default_rag_v2
