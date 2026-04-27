#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chroma向量数据库集成
升级RAG系统，提供高性能向量检索
"""

import os
import json
import hashlib
import numpy as np
from typing import List, Dict, Optional, Tuple
from datetime import datetime

# Chroma配置
CHROMA_DB_DIR = os.path.join(os.path.dirname(__file__), 'chroma_db')

class ChromaRAG:
    """基于Chroma的RAG系统"""
    
    def __init__(self, collection_name: str = "kaguya_docs"):
        self.collection_name = collection_name
        self.client = None
        self.collection = None
        self.embedding_function = None
        
        try:
            import chromadb
            from chromadb.config import Settings
            
            # 初始化Chroma客户端
            self.client = chromadb.PersistentClient(
                path=CHROMA_DB_DIR,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # 获取或创建集合
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            
            print(f"✓ Chroma RAG初始化成功，集合: {collection_name}")
            
        except ImportError:
            print("⚠️ Chroma未安装，使用降级方案")
            self._init_fallback()
        except Exception as e:
            print(f"⚠️ Chroma初始化失败: {e}，使用降级方案")
            self._init_fallback()
    
    def _init_fallback(self):
        """初始化降级方案"""
        self.client = None
        self.collection = None
        # 使用原有的RAG系统
        from qwen3_web import rag_documents, rag_chunks, rag_embeddings
        self.fallback_docs = rag_documents
        self.fallback_chunks = rag_chunks
        self.fallback_embeddings = rag_embeddings
    
    def get_embedding(self, text: str) -> List[float]:
        """获取文本嵌入向量"""
        # 使用现有的嵌入函数
        try:
            from qwen3_web import get_embedding
            return get_embedding(text)
        except:
            # 降级方案：使用简单的词袋模型
            return self._simple_embedding(text)
    
    def _simple_embedding(self, text: str) -> List[float]:
        """简单嵌入（降级方案）"""
        # 使用字符频率作为简单嵌入
        embedding = [0.0] * 128
        for char in text.lower():
            idx = ord(char) % 128
            embedding[idx] += 1.0
        # 归一化
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = [x / norm for x in embedding]
        return embedding
    
    def add_document(self, 
                     doc_id: str, 
                     content: str, 
                     metadata: Optional[Dict] = None,
                     chunk_size: int = 500,
                     chunk_overlap: int = 50) -> bool:
        """添加文档到向量库"""
        try:
            if self.collection is None:
                return self._add_document_fallback(doc_id, content, metadata)
            
            # 分块
            chunks = self._split_text(content, chunk_size, chunk_overlap)
            
            # 生成嵌入
            embeddings = [self.get_embedding(chunk) for chunk in chunks]
            
            # 准备元数据
            chunk_ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
            chunk_metadata = []
            for i, chunk in enumerate(chunks):
                meta = metadata.copy() if metadata else {}
                meta.update({
                    'doc_id': doc_id,
                    'chunk_index': i,
                    'chunk_total': len(chunks),
                    'chunk_size': len(chunk),
                    'added_at': datetime.now().isoformat()
                })
                chunk_metadata.append(meta)
            
            # 添加到Chroma
            self.collection.add(
                ids=chunk_ids,
                embeddings=embeddings,
                documents=chunks,
                metadatas=chunk_metadata
            )
            
            print(f"✓ 文档 {doc_id} 已添加，分成 {len(chunks)} 个块")
            return True
            
        except Exception as e:
            print(f"✗ 添加文档失败: {e}")
            return False
    
    def _add_document_fallback(self, doc_id: str, content: str, metadata: Optional[Dict] = None) -> bool:
        """降级方案：添加到原有RAG系统"""
        try:
            from qwen3_web import rag_documents, rag_chunks, rag_embeddings, compute_text_hash
            
            doc_hash = compute_text_hash(content)
            doc_entry = {
                'id': doc_id,
                'hash': doc_hash,
                'content': content[:1000],  # 只存储前1000字符
                'metadata': metadata or {},
                'added_at': datetime.now().isoformat()
            }
            
            # 分块
            chunks = self._split_text(content, 500, 50)
            
            for i, chunk in enumerate(chunks):
                chunk_entry = {
                    'doc_id': doc_id,
                    'chunk_id': f"{doc_id}_chunk_{i}",
                    'content': chunk,
                    'embedding': self.get_embedding(chunk)
                }
                rag_chunks.append(chunk_entry)
                rag_embeddings.append(chunk_entry['embedding'])
            
            rag_documents.append(doc_entry)
            
            print(f"✓ 文档 {doc_id} 已添加到降级RAG系统")
            return True
            
        except Exception as e:
            print(f"✗ 降级添加失败: {e}")
            return False
    
    def search(self, 
               query: str, 
               top_k: int = 5,
               filter_metadata: Optional[Dict] = None) -> List[Dict]:
        """搜索相关文档"""
        try:
            if self.collection is None:
                return self._search_fallback(query, top_k)
            
            # 获取查询嵌入
            query_embedding = self.get_embedding(query)
            
            # 构建过滤条件
            where_filter = None
            if filter_metadata:
                where_filter = filter_metadata
            
            # 执行搜索
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_filter,
                include=['documents', 'metadatas', 'distances']
            )
            
            # 格式化结果
            formatted_results = []
            if results['ids'] and len(results['ids'][0]) > 0:
                for i in range(len(results['ids'][0])):
                    formatted_results.append({
                        'id': results['ids'][0][i],
                        'content': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i],
                        'score': 1.0 - results['distances'][0][i]  # 转换为相似度
                    })
            
            return formatted_results
            
        except Exception as e:
            print(f"✗ 搜索失败: {e}")
            return []
    
    def _search_fallback(self, query: str, top_k: int = 5) -> List[Dict]:
        """降级方案：使用原有RAG系统搜索"""
        try:
            from qwen3_web import rag_chunks, rag_embeddings
            
            if not rag_chunks:
                return []
            
            query_embedding = self.get_embedding(query)
            
            # 计算相似度
            similarities = []
            for i, emb in enumerate(rag_embeddings):
                sim = np.dot(query_embedding, emb)
                similarities.append((i, sim))
            
            # 排序并返回top_k
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            results = []
            for idx, score in similarities[:top_k]:
                chunk = rag_chunks[idx]
                results.append({
                    'id': chunk['chunk_id'],
                    'content': chunk['content'],
                    'metadata': {'doc_id': chunk['doc_id']},
                    'score': score
                })
            
            return results
            
        except Exception as e:
            print(f"✗ 降级搜索失败: {e}")
            return []
    
    def delete_document(self, doc_id: str) -> bool:
        """删除文档"""
        try:
            if self.collection is None:
                return self._delete_fallback(doc_id)
            
            # 删除所有相关块
            self.collection.delete(
                where={'doc_id': doc_id}
            )
            
            print(f"✓ 文档 {doc_id} 已删除")
            return True
            
        except Exception as e:
            print(f"✗ 删除失败: {e}")
            return False
    
    def _delete_fallback(self, doc_id: str) -> bool:
        """降级方案：从原有RAG系统删除"""
        try:
            from qwen3_web import rag_documents, rag_chunks, rag_embeddings
            
            # 删除文档
            rag_documents[:] = [d for d in rag_documents if d['id'] != doc_id]
            
            # 删除相关块
            indices_to_remove = [i for i, c in enumerate(rag_chunks) if c['doc_id'] == doc_id]
            for idx in sorted(indices_to_remove, reverse=True):
                rag_chunks.pop(idx)
                rag_embeddings.pop(idx)
            
            print(f"✓ 文档 {doc_id} 已从降级RAG系统删除")
            return True
            
        except Exception as e:
            print(f"✗ 降级删除失败: {e}")
            return False
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        try:
            if self.collection:
                count = self.collection.count()
                return {
                    'total_chunks': count,
                    'collection_name': self.collection_name,
                    'using_chroma': True
                }
            else:
                from qwen3_web import rag_documents, rag_chunks
                return {
                    'total_docs': len(rag_documents),
                    'total_chunks': len(rag_chunks),
                    'using_chroma': False
                }
        except Exception as e:
            return {'error': str(e)}
    
    def _split_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """文本分块"""
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # 如果不在末尾，尝试在句子边界处分割
            if end < len(text):
                # 查找最近的句子结束符
                for sep in ['。', '！', '？', '.', '!', '?', '\n']:
                    pos = text.rfind(sep, start, end)
                    if pos > start:
                        end = pos + 1
                        break
            
            chunks.append(text[start:end].strip())
            start = end - overlap
        
        return [c for c in chunks if c]  # 过滤空块

# 全局实例
chroma_rag = ChromaRAG()

if __name__ == '__main__':
    # 测试
    rag = ChromaRAG()
    
    # 添加测试文档
    test_doc = """
    人工智能（AI）是计算机科学的一个分支，致力于创造能够执行通常需要人类智能的任务的机器。
    这些任务包括学习、推理、问题解决、感知和语言理解等。
    """
    
    rag.add_document("test_doc_1", test_doc, {"category": "AI"})
    
    # 搜索
    results = rag.search("什么是人工智能？", top_k=3)
    print("\n搜索结果:")
    for r in results:
        print(f"  分数: {r['score']:.3f}, 内容: {r['content'][:50]}...")
    
    # 统计
    print(f"\n统计: {rag.get_stats()}")
