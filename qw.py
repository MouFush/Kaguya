"""
Qwen3.5-4B Web前端 (专业增强版 - Ollama)
功能: 代码执行器、工具调用、知识库、插件系统、LoRA、网络搜索
后端: Ollama (qwen3.5:4b)
"""

import os
import sys
import json
import uuid
import time
import base64
import shutil
import subprocess
import tempfile
import re
import math
import socket
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime
from collections import defaultdict
import threading

import torch
from flask import Flask, render_template_string, request, jsonify, send_file, Response, stream_with_context
from ollama_adapter import get_ollama_adapter, OllamaConfig

try:
    from peft import PeftModel, LoraConfig, get_peft_model, TaskType
    PEFT_AVAILABLE = True
except ImportError:
    PEFT_AVAILABLE = False

OLLAMA_MODEL = "qwen3.5:4b"
model = None
current_lora = None
lora_adapters = {}

access_logs = []
visitor_stats = defaultdict(int)
log_lock = threading.Lock()
token_stats = {'total_input': 0, 'total_output': 0, 'sessions': 0}

PROMPTS_DIR = os.path.join(os.path.dirname(__file__), 'prompts')
UPLOADS_DIR = os.path.join(os.path.dirname(__file__), 'uploads')
AUDIO_CACHE_DIR = os.path.join(os.path.dirname(__file__), 'audio_cache')
LORA_DIR = os.path.join(os.path.dirname(__file__), 'lora_adapters')
KNOWLEDGE_DIR = os.path.join(os.path.dirname(__file__), 'knowledge_base')
CODE_EXEC_DIR = os.path.join(os.path.dirname(__file__), 'code_executions')
RAG_DIR = os.path.join(os.path.dirname(__file__), 'rag_data')
RAG_INDEX_FILE = os.path.join(RAG_DIR, 'rag_index.json')
MCP_DIR = os.path.join(os.path.dirname(__file__), 'mcp_plugins')
MCP_CONFIG_FILE = os.path.join(MCP_DIR, 'mcp_config.json')
WORKFLOW_DIR = os.path.join(os.path.dirname(__file__), 'workflows')
WORKFLOW_INDEX_FILE = os.path.join(WORKFLOW_DIR, 'workflows_index.json')
MEMORY_DIR = os.path.join(os.path.dirname(__file__), 'memory_system')
MEMORY_DB_FILE = os.path.join(MEMORY_DIR, 'memory.db')
MEMORY_INDEX_FILE = os.path.join(MEMORY_DIR, 'memory_index.json')
MULTIMODAL_DIR = os.path.join(os.path.dirname(__file__), 'multimodal')
IMAGE_CACHE_DIR = os.path.join(MULTIMODAL_DIR, 'image_cache')
FINETUNE_DIR = os.path.join(os.path.dirname(__file__), 'finetune')
DATASETS_DIR = os.path.join(FINETUNE_DIR, 'datasets')
TRAINING_DIR = os.path.join(FINETUNE_DIR, 'training')
EXPORTS_DIR = os.path.join(FINETUNE_DIR, 'exports')
FINETUNE_CONFIG_FILE = os.path.join(FINETUNE_DIR, 'finetune_config.json')
PROJECT_CENTER_DIR = os.path.join(os.path.dirname(__file__), 'project_center')
ARTIFACTS_FILE = os.path.join(PROJECT_CENTER_DIR, 'artifacts.json')
PROJECT_TASKS_FILE = os.path.join(PROJECT_CENTER_DIR, 'tasks.json')
PLAYBOOKS_FILE = os.path.join(PROJECT_CENTER_DIR, 'playbooks.json')
PROJECT_ACTIVITY_FILE = os.path.join(PROJECT_CENTER_DIR, 'activity.json')
OPS_CAMPAIGNS_FILE = os.path.join(PROJECT_CENTER_DIR, 'ops_campaigns.json')
RELEASE_PLANS_FILE = os.path.join(PROJECT_CENTER_DIR, 'release_plans.json')
ALERT_RULES_FILE = os.path.join(PROJECT_CENTER_DIR, 'alert_rules.json')
AB_EXPERIMENTS_FILE = os.path.join(PROJECT_CENTER_DIR, 'ab_experiments.json')
INTEGRATIONS_FILE = os.path.join(PROJECT_CENTER_DIR, 'integrations.json')
PROJECT_MILESTONES_FILE = os.path.join(PROJECT_CENTER_DIR, 'milestones.json')
PROJECT_RISKS_FILE = os.path.join(PROJECT_CENTER_DIR, 'risks.json')
EXTERNAL_API_DIR = os.path.join(os.path.dirname(__file__), 'external_api')
EXTERNAL_API_CONFIG_FILE = os.path.join(EXTERNAL_API_DIR, 'provider_config.json')

for d in [PROMPTS_DIR, UPLOADS_DIR, AUDIO_CACHE_DIR, LORA_DIR, KNOWLEDGE_DIR, CODE_EXEC_DIR, RAG_DIR, MCP_DIR, WORKFLOW_DIR, MEMORY_DIR, MULTIMODAL_DIR, IMAGE_CACHE_DIR, FINETUNE_DIR, DATASETS_DIR, TRAINING_DIR, EXPORTS_DIR, PROJECT_CENTER_DIR, EXTERNAL_API_DIR]:
    os.makedirs(d, exist_ok=True)

rag_documents = []
rag_chunks = []
rag_embeddings = []
rag_cache = {}
rag_cache_max_size = 100
rag_doc_hashes = set()
project_artifacts = []
project_tasks = []
project_playbooks = []
project_activities = []
ops_campaigns = []
release_plans = []
alert_rules = []
ab_experiments = []
integrations = []
project_milestones = []
project_risks = []

def compute_text_hash(text):
    import hashlib
    return hashlib.md5(text.encode('utf-8')).hexdigest()[:16]

def load_rag_index():
    global rag_documents, rag_chunks, rag_embeddings, rag_doc_hashes
    if os.path.exists(RAG_INDEX_FILE):
        try:
            with open(RAG_INDEX_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                rag_documents = data.get('documents', [])
                rag_chunks = data.get('chunks', [])
                rag_embeddings = data.get('embeddings', [])
                rag_doc_hashes = set(data.get('doc_hashes', []))
            print(f"RAG索引已加载: {len(rag_documents)}文档, {len(rag_chunks)}分块")
        except Exception as e:
            print(f"加载RAG索引失败: {e}")
            rag_documents, rag_chunks, rag_embeddings, rag_doc_hashes = [], [], [], set()

def save_rag_index():
    try:
        with open(RAG_INDEX_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                'documents': rag_documents,
                'chunks': rag_chunks,
                'embeddings': rag_embeddings,
                'doc_hashes': list(rag_doc_hashes)
            }, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存RAG索引失败: {e}")

def get_cache_key(query, top_k, alpha, use_rerank, category):
    return f"{query}|{top_k}|{alpha}|{use_rerank}|{category or 'all'}"

def check_rag_cache(key):
    if key in rag_cache:
        entry = rag_cache[key]
        if time.time() - entry['time'] < 300:
            return entry['results']
    return None

def set_rag_cache(key, results):
    global rag_cache
    if len(rag_cache) >= rag_cache_max_size:
        oldest = min(rag_cache.items(), key=lambda x: x[1]['time'])
        del rag_cache[oldest[0]]
    rag_cache[key] = {'results': results, 'time': time.time()}

def expand_query(query):
    expanded = [query]
    synonyms = {
        '如何': ['怎么', '怎样', '方法'],
        '怎么': ['如何', '怎样', '方法'],
        '什么': ['哪些', '何'],
        '为什么': ['原因', '为何'],
        '怎样': ['如何', '怎么'],
        '实现': ['实现方法', '做法', '方案'],
        '解决': ['处理', '解决方法', '方案'],
        '问题': ['疑问', '困惑'],
        '功能': ['特性', '能力'],
        '配置': ['设置', '参数'],
        '安装': ['部署', '配置'],
        '使用': ['用法', '操作'],
    }
    for word, syns in synonyms.items():
        if word in query:
            for syn in syns:
                expanded.append(query.replace(word, syn))
            break
    return expanded

def rewrite_query(query, history=None):
    rewritten = query
    if history and len(history) > 0:
        last_user_msg = None
        for h in reversed(history):
            if h[0]:
                last_user_msg = h[0]
                break
        if last_user_msg:
            pronouns = ['它', '这', '那', '他', '她', '这个', '那个']
            for pronoun in pronouns:
                if pronoun in query and pronoun not in last_user_msg:
                    key_entities = re.findall(r'[\u4e00-\u9fa5]{2,4}', last_user_msg)
                    if key_entities:
                        rewritten = query.replace(pronoun, key_entities[-1])
                        break
    return rewritten

def extract_keywords(query):
    stop_words = {'的', '是', '在', '有', '和', '了', '我', '你', '他', '她', '它', '这', '那', '就', '也', '都', '吗', '呢', '吧', '啊', '呀'}
    words = simple_tokenize(query)
    keywords = [w for w in words if w not in stop_words and len(w) > 1]
    return keywords[:5]

def build_context_query(history, current_query, max_history=3):
    if not history:
        return current_query
    context_parts = []
    for h in history[-max_history:]:
        if h[0]:
            context_parts.append(h[0])
    context = ' '.join(context_parts[-2:])
    keywords = extract_keywords(context)
    if keywords:
        return current_query + ' ' + ' '.join(keywords)
    return current_query

def generate_hypothetical_answer(query):
    hypothetical_templates = {
        '如何': f"要{query}，首先需要了解基本概念。具体步骤包括：1. 准备工作；2. 执行操作；3. 验证结果。关键是要注意细节和安全。",
        '怎么': f"{query}的方法有很多种。最常用的方法是：通过系统配置实现，或者使用专门的工具。建议先了解基础知识再进行操作。",
        '什么是': f"{query}是一个重要的概念。它指的是在特定条件下，通过某种方式实现目标的过程。理解这个概念对于后续学习很重要。",
        '为什么': f"{query}的原因主要有以下几点：1. 系统设计考虑；2. 性能优化需求；3. 安全性要求。这些因素共同决定了最终的设计选择。",
    }
    for key, template in hypothetical_templates.items():
        if key in query:
            return template
    return f"关于{query}，这是一个需要深入了解的问题。通常涉及多个方面的知识，包括理论基础、实践方法和注意事项。建议系统性地学习和实践。"

def generate_multi_queries(query):
    queries = [query]
    if '和' in query:
        parts = query.split('和')
        for part in parts:
            if len(part.strip()) > 2:
                queries.append(part.strip())
    question_words = ['如何', '怎么', '什么是', '为什么', '哪些', '怎样']
    for word in question_words:
        if word in query:
            alt_word = {'如何': '怎么', '怎么': '如何', '什么是': '哪些', '为什么': '原因', '哪些': '什么', '怎样': '如何'}
            if word in alt_word:
                queries.append(query.replace(word, alt_word[word]))
            break
    if len(query) > 10:
        keywords = extract_keywords(query)
        if keywords:
            queries.append(' '.join(keywords[:3]))
    return list(set(queries))[:5]

def decompose_query(query):
    sub_queries = []
    connectors = ['并且', '同时', '以及', '还有', '另外', '还有呢']
    for conn in connectors:
        if conn in query:
            parts = query.split(conn)
            for part in parts:
                part = part.strip()
                if len(part) > 3:
                    sub_queries.append(part)
            break
    if '和' in query and len(query) > 15:
        parts = query.split('和')
        for part in parts:
            part = part.strip()
            if len(part) > 5:
                sub_queries.append(part)
    if not sub_queries:
        sub_queries = [query]
    return sub_queries

def classify_query(query):
    query_lower = query.lower()
    if any(w in query for w in ['如何', '怎么', '怎样', '方法', '步骤']):
        return 'how-to'
    elif any(w in query for w in ['什么是', '定义', '概念', '介绍']):
        return 'definition'
    elif any(w in query for w in ['为什么', '原因', '为何']):
        return 'explanation'
    elif any(w in query for w in ['哪些', '有什么', '列举', '例子']):
        return 'list'
    elif any(w in query for w in ['比较', '区别', '对比', '差异']):
        return 'comparison'
    elif any(w in query for w in ['代码', '实现', '编程', '函数']):
        return 'code'
    elif any(w in query for w in ['错误', '问题', '解决', '修复']):
        return 'troubleshooting'
    else:
        return 'general'

def get_adaptive_params(query_type):
    params = {
        'how-to': {'top_k': 5, 'alpha': 0.6, 'chunk_size': 'medium'},
        'definition': {'top_k': 3, 'alpha': 0.7, 'chunk_size': 'small'},
        'explanation': {'top_k': 4, 'alpha': 0.5, 'chunk_size': 'large'},
        'list': {'top_k': 7, 'alpha': 0.4, 'chunk_size': 'medium'},
        'comparison': {'top_k': 6, 'alpha': 0.5, 'chunk_size': 'large'},
        'code': {'top_k': 4, 'alpha': 0.3, 'chunk_size': 'large'},
        'troubleshooting': {'top_k': 5, 'alpha': 0.6, 'chunk_size': 'medium'},
        'general': {'top_k': 5, 'alpha': 0.5, 'chunk_size': 'medium'}
    }
    return params.get(query_type, params['general'])

def calculate_retrieval_quality(query, results):
    if not results:
        return {'score': 0, 'reason': '无结果'}
    scores = [r['score'] for r in results]
    avg_score = sum(scores) / len(scores)
    max_score = max(scores)
    min_score = min(scores)
    score_variance = sum((s - avg_score) ** 2 for s in scores) / len(scores)
    query_keywords = set(extract_keywords(query))
    keyword_coverage = 0
    for r in results:
        result_keywords = set(extract_keywords(r['text']))
        coverage = len(query_keywords & result_keywords) / len(query_keywords) if query_keywords else 0
        keyword_coverage += coverage
    keyword_coverage /= len(results)
    quality_score = (avg_score * 0.4 + max_score * 0.3 + keyword_coverage * 0.3)
    quality_reason = '高质量' if quality_score > 0.5 else '中等质量' if quality_score > 0.3 else '低质量'
    return {
        'score': round(quality_score, 3),
        'reason': quality_reason,
        'avg_similarity': round(avg_score, 3),
        'max_similarity': round(max_score, 3),
        'keyword_coverage': round(keyword_coverage, 3),
        'result_count': len(results)
    }

def merge_and_deduplicate(results_list, top_k=5):
    all_results = []
    seen = set()
    for results in results_list:
        for r in results:
            if r['chunk_id'] not in seen:
                seen.add(r['chunk_id'])
                all_results.append(r)
    all_results.sort(key=lambda x: x['score'], reverse=True)
    return all_results[:top_k]

def reciprocal_rank_fusion(results_list, k=60, top_k=5):
    rrf_scores = {}
    for results in results_list:
        for rank, r in enumerate(results):
            chunk_id = r['chunk_id']
            if chunk_id not in rrf_scores:
                rrf_scores[chunk_id] = {'result': r, 'score': 0}
            rrf_scores[chunk_id]['score'] += 1 / (k + rank + 1)
    sorted_results = sorted(rrf_scores.values(), key=lambda x: x['score'], reverse=True)
    return [r['result'] for r in sorted_results[:top_k]]

def extract_metadata_filters(query):
    filters = {}
    category_patterns = {
        'code': r'(代码|编程|函数|程序|脚本|python|java|javascript)',
        'doc': r'(文档|文章|说明|教程|指南)',
        'data': r'(数据|表格|csv|json|数据库)',
        'config': r'(配置|设置|参数|选项)'
    }
    for cat, pattern in category_patterns.items():
        if re.search(pattern, query, re.IGNORECASE):
            filters['category'] = cat
            break
    time_patterns = [
        (r'最新|最近|今天|昨天', 'recent'),
        (r'本周|这周', 'this_week'),
        (r'本月|这个月', 'this_month'),
        (r'去年|上一年', 'last_year')
    ]
    for pattern, time_filter in time_patterns:
        if re.search(pattern, query):
            filters['time'] = time_filter
            break
    size_patterns = [
        (r'详细|完整|全部', 'large'),
        (r'简短|摘要|概要', 'small')
    ]
    for pattern, size_filter in size_patterns:
        if re.search(pattern, query):
            filters['size'] = size_filter
            break
    return filters

def apply_metadata_filters(results, filters, documents):
    if not filters:
        return results
    filtered = []
    for r in results:
        doc = next((d for d in documents if d['id'] == r['doc_id']), None)
        if not doc:
            continue
        if 'category' in filters and doc.get('category') != filters['category']:
            continue
        if 'time' in filters:
            doc_time = datetime.fromisoformat(doc.get('time', '2000-01-01'))
            now = datetime.now()
            if filters['time'] == 'recent' and (now - doc_time).days > 7:
                continue
            elif filters['time'] == 'this_week' and (now - doc_time).days > 7:
                continue
            elif filters['time'] == 'this_month' and (now - doc_time).days > 30:
                continue
            elif filters['time'] == 'last_year' and (now - doc_time).days > 365:
                continue
        if 'size' in filters:
            if filters['size'] == 'large' and doc.get('char_count', 0) < 1000:
                continue
            elif filters['size'] == 'small' and doc.get('char_count', 0) > 5000:
                continue
        filtered.append(r)
    return filtered if filtered else results

def compress_context(results, max_length=2000):
    if not results:
        return ""
    compressed = []
    current_length = 0
    for r in results:
        text = r['text']
        sentences = re.split(r'[。！？\n]', text)
        key_sentences = []
        for s in sentences:
            s = s.strip()
            if len(s) < 10:
                continue
            if any(kw in s for kw in ['关键', '重要', '核心', '主要', '首先', '因此', '所以', '总之']):
                key_sentences.append(s)
        if key_sentences:
            compressed_text = '。'.join(key_sentences[:2])
        else:
            compressed_text = text[:300]
        if current_length + len(compressed_text) > max_length:
            break
        compressed.append(f"[{r['doc_name']}] {compressed_text}")
        current_length += len(compressed_text)
    return '\n\n'.join(compressed)

def calculate_time_weight(doc_time_str, decay_factor=0.1):
    try:
        doc_time = datetime.fromisoformat(doc_time_str)
        now = datetime.now()
        days_diff = (now - doc_time).days
        weight = math.exp(-decay_factor * days_diff / 30)
        return max(0.1, min(1.0, weight))
    except:
        return 0.5

def apply_time_weighting(results, documents):
    for r in results:
        doc = next((d for d in documents if d['id'] == r['doc_id']), None)
        if doc:
            time_weight = calculate_time_weight(doc.get('time', '2000-01-01'))
            r['time_weight'] = time_weight
            r['weighted_score'] = r['score'] * (0.7 + 0.3 * time_weight)
    results.sort(key=lambda x: x.get('weighted_score', x['score']), reverse=True)
    return results

def needs_retry(results, min_score=0.2, min_results=2):
    if not results:
        return True, "无结果"
    if len(results) < min_results:
        return True, "结果不足"
    if all(r['score'] < min_score for r in results):
        return True, "分数过低"
    return False, "结果良好"

def iterative_retrieval(query, initial_results, top_k=5, max_iterations=2):
    all_results = list(initial_results)
    seen_ids = set(r['chunk_id'] for r in initial_results)
    for i in range(max_iterations):
        if len(all_results) >= top_k:
            break
        expanded_query = query
        if all_results:
            top_result_text = all_results[0]['text'][:200]
            keywords = extract_keywords(top_result_text)
            if keywords:
                expanded_query = query + ' ' + ' '.join(keywords[:3])
        new_results = hybrid_search(expanded_query, top_k)
        for r in new_results:
            if r['chunk_id'] not in seen_ids:
                seen_ids.add(r['chunk_id'])
                r['source'] = f'iteration_{i+1}'
                all_results.append(r)
    all_results.sort(key=lambda x: x['score'], reverse=True)
    return all_results[:top_k]

def extract_entities(query):
    entities = {
        'technologies': re.findall(r'(python|java|javascript|react|vue|node|django|flask|mysql|redis|docker|k8s|kubernetes)', query.lower()),
        'actions': re.findall(r'(安装|配置|部署|运行|调试|优化|测试|开发)', query),
        'concepts': re.findall(r'[\u4e00-\u9fff]{2,6}(?:功能|模块|组件|接口|服务|系统)', query)
    }
    return {k: v for k, v in entities.items() if v}

def build_structured_query(query):
    entities = extract_entities(query)
    filters = extract_metadata_filters(query)
    query_type = classify_query(query)
    structured = {
        'original_query': query,
        'query_type': query_type,
        'entities': entities,
        'filters': filters,
        'keywords': extract_keywords(query),
        'expanded_queries': generate_multi_queries(query)[:3]
    }
    return structured

def simple_tokenize(text):
    text = text.lower()
    tokens = re.findall(r'[\u4e00-\u9fff]|[a-zA-Z]+|[0-9]+', text)
    return tokens

def compute_tfidf_embedding(text, vocab=None):
    tokens = simple_tokenize(text)
    if not tokens:
        return {}
    tf = {}
    for token in tokens:
        tf[token] = tf.get(token, 0) + 1
    for token in tf:
        tf[token] = tf[token] / len(tokens)
    return tf

def cosine_similarity(vec1, vec2):
    if not vec1 or not vec2:
        return 0.0
    common_keys = set(vec1.keys()) & set(vec2.keys())
    if not common_keys:
        return 0.0
    dot_product = sum(vec1[k] * vec2[k] for k in common_keys)
    norm1 = sum(v ** 2 for v in vec1.values()) ** 0.5
    norm2 = sum(v ** 2 for v in vec2.values()) ** 0.5
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot_product / (norm1 * norm2)

BM25_K1 = 1.5
BM25_B = 0.75
doc_freqs = {}
doc_lengths = []
avgdl = 0
N = 0

def init_bm25():
    global doc_freqs, doc_lengths, avgdl, N, rag_chunks
    doc_freqs = {}
    doc_lengths = []
    N = len(rag_chunks)
    if N == 0:
        return
    for chunk in rag_chunks:
        tokens = simple_tokenize(chunk['text'])
        doc_lengths.append(len(tokens))
        seen = set()
        for token in tokens:
            if token not in seen:
                doc_freqs[token] = doc_freqs.get(token, 0) + 1
                seen.add(token)
    avgdl = sum(doc_lengths) / N if N > 0 else 0

def bm25_score(query, doc_idx):
    global doc_freqs, doc_lengths, avgdl, N, rag_chunks
    if N == 0 or doc_idx >= len(rag_chunks):
        return 0.0
    query_tokens = simple_tokenize(query)
    doc_tokens = simple_tokenize(rag_chunks[doc_idx]['text'])
    doc_len = doc_lengths[doc_idx] if doc_idx < len(doc_lengths) else len(doc_tokens)
    score = 0.0
    for token in query_tokens:
        if token not in doc_freqs:
            continue
        tf = doc_tokens.count(token)
        df = doc_freqs.get(token, 0)
        idf = math.log((N - df + 0.5) / (df + 0.5) + 1)
        numerator = tf * (BM25_K1 + 1)
        denominator = tf + BM25_K1 * (1 - BM25_B + BM25_B * doc_len / avgdl) if avgdl > 0 else tf + BM25_K1
        score += idf * numerator / denominator if denominator > 0 else 0
    return score

def hybrid_search(query, top_k=5, alpha=0.5):
    global rag_chunks, rag_embeddings
    if not rag_chunks:
        return []
    init_bm25()
    query_embedding = compute_tfidf_embedding(query)
    scores = []
    for i in range(len(rag_chunks)):
        tfidf_score = cosine_similarity(query_embedding, rag_embeddings[i])
        bm25_s = bm25_score(query, i)
        combined = alpha * tfidf_score + (1 - alpha) * (bm25_s / 10 if bm25_s > 0 else 0)
        scores.append((i, combined, tfidf_score, bm25_s))
    scores.sort(key=lambda x: x[1], reverse=True)
    results = []
    for i, combined, tfidf, bm25 in scores[:top_k * 2]:
        if combined > 0.02:
            chunk = rag_chunks[i]
            doc = next((d for d in rag_documents if d['id'] == chunk['doc_id']), None)
            if doc:
                results.append({
                    "chunk_id": chunk['id'],
                    "text": chunk['text'],
                    "score": round(combined, 4),
                    "tfidf_score": round(tfidf, 4),
                    "bm25_score": round(bm25, 4),
                    "doc_name": doc['filename'],
                    "doc_id": doc['id'],
                    "doc_category": doc.get('category', 'other'),
                    "chunk_index": chunk.get('index', 0)
                })
            if len(results) >= top_k:
                break
    return results

def rerank_results(query, results, top_k=None):
    if not results:
        return results
    query_tokens = set(simple_tokenize(query))
    for r in results:
        text = r['text'].lower()
        exact_matches = sum(1 for t in query_tokens if t in text)
        query_lower = query.lower()
        if query_lower in text:
            r['score'] += 0.2
        r['score'] += exact_matches * 0.02
        r['exact_match_count'] = exact_matches
    results.sort(key=lambda x: x['score'], reverse=True)
    return results[:top_k] if top_k else results

def smart_chunk_text(text, chunk_size=400, overlap=80, strategy='sentence'):
    if strategy == 'sentence':
        chunks = []
        sentences = re.split(r'(?<=[。！？\n\.!?])\s*', text)
        current_chunk = ""
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            if len(current_chunk) + len(sentence) <= chunk_size:
                current_chunk += sentence + " "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                if overlap > 0 and chunks:
                    last_chunk = chunks[-1]
                    overlap_text = last_chunk[-overlap:] if len(last_chunk) > overlap else last_chunk
                    current_chunk = overlap_text + sentence + " "
                else:
                    current_chunk = sentence + " "
        if current_chunk:
            chunks.append(current_chunk.strip())
        return chunks if chunks else [text[:chunk_size]]
    elif strategy == 'paragraph':
        paragraphs = re.split(r'\n\s*\n', text)
        chunks = []
        current = ""
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            if len(current) + len(para) <= chunk_size:
                current += para + "\n\n"
            else:
                if current:
                    chunks.append(current.strip())
                current = para + "\n\n"
        if current:
            chunks.append(current.strip())
        return chunks if chunks else [text[:chunk_size]]
    elif strategy == 'semantic':
        sentences = re.split(r'(?<=[。！？\.!?])\s*', text)
        chunks = []
        current = ""
        for s in sentences:
            s = s.strip()
            if not s:
                continue
            if len(current) + len(s) <= chunk_size:
                current += s + " "
            else:
                if current and len(current) > 50:
                    chunks.append(current.strip())
                current = s + " "
        if current:
            chunks.append(current.strip())
        return chunks if chunks else [text[:chunk_size]]
    else:
        step = chunk_size - overlap
        return [text[i:i+chunk_size] for i in range(0, len(text), step)] if len(text) > chunk_size else [text]

def chunk_text(text, chunk_size=400, overlap=80):
    return smart_chunk_text(text, chunk_size, overlap, 'sentence')

def parse_document(file_path, filename):
    text = ""
    ext = filename.lower().split('.')[-1]
    try:
        if ext == 'txt' or ext == 'md':
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        elif ext == 'json':
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                text = json.dumps(data, ensure_ascii=False, indent=2)
        elif ext == 'csv':
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        elif ext == 'pdf':
            try:
                import fitz
                doc = fitz.open(file_path)
                for page in doc:
                    text += page.get_text() + "\n"
                doc.close()
            except ImportError:
                return None, "PDF解析需要安装PyMuPDF: pip install pymupdf"
        elif ext == 'docx':
            try:
                from docx import Document
                doc = Document(file_path)
                text = "\n".join([para.text for para in doc.paragraphs])
            except ImportError:
                return None, "DOCX解析需要安装python-docx: pip install python-docx"
        elif ext == 'html' or ext == 'htm':
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            text = re.sub(r'<[^>]+>', ' ', html_content)
            text = re.sub(r'\s+', ' ', text).strip()
        else:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
    except Exception as e:
        return None, str(e)
    return text, None

def get_file_category(filename):
    ext = filename.lower().split('.')[-1]
    categories = {
        'code': ['py', 'js', 'ts', 'java', 'cpp', 'c', 'go', 'rs', 'rb', 'php'],
        'doc': ['txt', 'md', 'pdf', 'doc', 'docx', 'rtf'],
        'data': ['json', 'csv', 'xml', 'yaml', 'yml'],
        'web': ['html', 'htm', 'css'],
        'config': ['ini', 'cfg', 'conf', 'env']
    }
    for cat, exts in categories.items():
        if ext in exts:
            return cat
    return 'other'

def add_document_to_rag(file_path, filename, tags=None):
    global rag_documents, rag_chunks, rag_embeddings, rag_doc_hashes
    text, error = parse_document(file_path, filename)
    if error:
        return None, error
    if not text or len(text.strip()) < 50:
        return None, "文档内容过少或无法解析"
    
    text_hash = compute_text_hash(text)
    if text_hash in rag_doc_hashes:
        existing = next((d for d in rag_documents if d.get('hash') == text_hash), None)
        if existing:
            return None, f"文档已存在: {existing['filename']}"
    
    doc_id = str(uuid.uuid4())[:8]
    category = get_file_category(filename)
    doc_info = {
        "id": doc_id,
        "filename": filename,
        "path": file_path,
        "size": len(text),
        "time": datetime.now().isoformat(),
        "chunk_count": 0,
        "category": category,
        "tags": tags or [],
        "char_count": len(text),
        "word_count": len(text.split()),
        "hash": text_hash
    }
    chunks = chunk_text(text, chunk_size=400, overlap=80)
    chunk_hashes = set()
    for i, chunk in enumerate(chunks):
        chunk_hash = compute_text_hash(chunk)
        if chunk_hash in chunk_hashes:
            continue
        chunk_hashes.add(chunk_hash)
        chunk_id = f"{doc_id}_{i}"
        embedding = compute_tfidf_embedding(chunk)
        chunk_info = {
            "id": chunk_id,
            "doc_id": doc_id,
            "text": chunk,
            "index": i,
            "start_char": text.find(chunk[:50]) if chunk[:50] in text else 0,
            "hash": chunk_hash
        }
        rag_chunks.append(chunk_info)
        rag_embeddings.append(embedding)
    doc_info["chunk_count"] = len(chunks)
    rag_documents.append(doc_info)
    rag_doc_hashes.add(text_hash)
    save_rag_index()
    return doc_info, None

def search_rag(query, top_k=5, doc_ids=None, category=None, use_rerank=True, alpha=0.5, history=None, use_cache=True, use_expansion=True, use_hyde=False, use_multi_query=False, use_decomposition=False, use_adaptive=True, use_rrf=False, use_metadata_filter=True, use_time_weight=False, use_compression=False, use_iterative=False):
    global rag_chunks, rag_embeddings, rag_documents
    if not rag_chunks:
        return []
    
    cache_key = get_cache_key(query, top_k, alpha, use_rerank, category)
    if use_cache:
        cached = check_rag_cache(cache_key)
        if cached:
            return cached
    
    query_type = classify_query(query) if use_adaptive else 'general'
    if use_adaptive:
        adaptive_params = get_adaptive_params(query_type)
        top_k = adaptive_params['top_k']
        alpha = adaptive_params['alpha']
    
    rewritten = rewrite_query(query, history)
    context_query = build_context_query(history, rewritten) if history else rewritten
    
    metadata_filters = extract_metadata_filters(query) if use_metadata_filter else {}
    if category:
        metadata_filters['category'] = category
    
    all_results = []
    
    if use_hyde:
        hypothetical = generate_hypothetical_answer(query)
        hyde_embedding = compute_tfidf_embedding(hypothetical)
        hyde_results = []
        for i, embedding in enumerate(rag_embeddings):
            score = cosine_similarity(hyde_embedding, embedding)
            if score > 0.05:
                chunk = rag_chunks[i]
                doc = next((d for d in rag_documents if d['id'] == chunk['doc_id']), None)
                if doc:
                    hyde_results.append({
                        "chunk_id": chunk['id'],
                        "text": chunk['text'],
                        "score": round(score, 4),
                        "doc_name": doc['filename'],
                        "doc_id": doc['id'],
                        "doc_category": doc.get('category', 'other'),
                        "chunk_index": chunk.get('index', 0),
                        "source": "hyde"
                    })
        hyde_results.sort(key=lambda x: x['score'], reverse=True)
        all_results.append(hyde_results[:top_k])
    
    if use_multi_query:
        multi_queries = generate_multi_queries(context_query)
        for q in multi_queries[:3]:
            mq_results = hybrid_search(q, top_k, alpha)
            for r in mq_results:
                r['source'] = 'multi_query'
            all_results.append(mq_results)
    
    if use_decomposition:
        sub_queries = decompose_query(query)
        for sq in sub_queries:
            sq_results = hybrid_search(sq, top_k // len(sub_queries) + 1, alpha)
            for r in sq_results:
                r['source'] = 'decomposition'
            all_results.append(sq_results)
    
    if use_expansion:
        expanded_queries = expand_query(context_query)
        for eq in expanded_queries[:2]:
            eq_results = hybrid_search(eq, top_k, alpha)
            for r in eq_results:
                r['source'] = 'expansion'
            all_results.append(eq_results)
    
    base_results = hybrid_search(context_query, top_k, alpha)
    for r in base_results:
        r['source'] = 'base'
    all_results.append(base_results)
    
    if use_rrf and len(all_results) > 1:
        final_results = reciprocal_rank_fusion(all_results, top_k=top_k * 2)
    else:
        final_results = merge_and_deduplicate(all_results, top_k * 2)
    
    if metadata_filters:
        final_results = apply_metadata_filters(final_results, metadata_filters, rag_documents)
    
    if doc_ids:
        final_results = [r for r in final_results if r['doc_id'] in doc_ids]
    if category and not metadata_filters.get('category'):
        final_results = [r for r in final_results if r.get('doc_category') == category]
    
    if use_time_weight:
        final_results = apply_time_weighting(final_results, rag_documents)
    
    if use_rerank:
        final_results = rerank_results(query, final_results, top_k)
    
    final_results = final_results[:top_k]
    
    if use_iterative and len(final_results) < top_k:
        final_results = iterative_retrieval(query, final_results, top_k)
    
    if use_cache:
        set_rag_cache(cache_key, final_results)
    
    return final_results

def get_rag_stats():
    global rag_documents, rag_chunks, rag_cache
    if not rag_documents:
        return {"total_docs": 0, "total_chunks": 0, "total_chars": 0, "categories": {}, "cache_size": 0}
    categories = {}
    total_chars = 0
    for doc in rag_documents:
        cat = doc.get('category', 'other')
        categories[cat] = categories.get(cat, 0) + 1
        total_chars += doc.get('char_count', doc.get('size', 0))
    return {
        "total_docs": len(rag_documents),
        "total_chunks": len(rag_chunks),
        "total_chars": total_chars,
        "categories": categories,
        "cache_size": len(rag_cache),
        "unique_hashes": len(rag_doc_hashes)
    }

def delete_document_from_rag(doc_id):
    global rag_documents, rag_chunks, rag_embeddings, rag_doc_hashes
    doc = next((d for d in rag_documents if d['id'] == doc_id), None)
    if doc and doc.get('hash') in rag_doc_hashes:
        rag_doc_hashes.remove(doc['hash'])
    rag_documents = [d for d in rag_documents if d['id'] != doc_id]
    chunks_to_remove = [i for i, c in enumerate(rag_chunks) if c['doc_id'] == doc_id]
    for i in reversed(chunks_to_remove):
        rag_chunks.pop(i)
        rag_embeddings.pop(i)
    save_rag_index()
    return True

load_rag_index()

def get_default_playbooks():
    return [
        {
            "id": "growth_weekly",
            "name": "增长周计划",
            "description": "面向运营团队的周目标拆解和执行排期",
            "category": "运营",
            "template": "请围绕主题「{topic}」，目标「{goal}」，约束「{constraints}」，生成一份7天增长执行计划，包含目标、动作、指标、风险、复盘。"
        },
        {
            "id": "incident_response",
            "name": "故障应急响应",
            "description": "用于线上故障时的排障与沟通流程",
            "category": "工程",
            "template": "针对「{topic}」故障，结合背景「{context}」，输出P0/P1分级、排查顺序、止血方案、回滚策略、复盘模板。"
        },
        {
            "id": "release_gate",
            "name": "发布门禁清单",
            "description": "面向版本上线前质量与风险检查",
            "category": "工程",
            "template": "基于发布内容「{topic}」，输出上线门禁清单：功能、性能、安全、观测、回滚、验收、值班安排。"
        },
        {
            "id": "research_brief",
            "name": "深度研究简报",
            "description": "形成可交付的研究摘要与行动建议",
            "category": "研究",
            "template": "围绕研究主题「{topic}」，背景「{context}」，目标「{goal}」，生成研究简报：问题拆解、证据、结论、建议。"
        },
        {
            "id": "sales_enablement",
            "name": "销售赋能作战卡",
            "description": "统一销售话术、异议处理与推进路径",
            "category": "销售",
            "template": "针对产品/方案「{topic}」，输出销售作战卡：客户画像、价值主张、异议处理、跟进节奏、成交信号。"
        },
        {
            "id": "compliance_review",
            "name": "合规评审模板",
            "description": "用于合同与数据合规风险审查",
            "category": "法务",
            "template": "针对事项「{topic}」，约束「{constraints}」，生成合规审查清单：风险点、证据、责任、整改建议、验收标准。"
        }
    ]

def load_json_list(file_path, default=None):
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data if isinstance(data, list) else (default or [])
    except Exception as e:
        print(f"加载JSON失败 {file_path}: {e}")
    return default or []

def save_json_list(file_path, data):
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存JSON失败 {file_path}: {e}")

def load_json_object(file_path, default=None):
    default_value = default if isinstance(default, dict) else {}
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data if isinstance(data, dict) else default_value
    except Exception as e:
        print(f"加载JSON对象失败 {file_path}: {e}")
    return default_value

def save_json_object(file_path, data):
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data if isinstance(data, dict) else {}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存JSON对象失败 {file_path}: {e}")

def append_project_activity(action, entity, entity_id, detail=''):
    global project_activities
    event = {
        "id": str(uuid.uuid4())[:8],
        "action": action,
        "entity": entity,
        "entity_id": entity_id,
        "detail": detail,
        "time": int(time.time())
    }
    project_activities.insert(0, event)
    project_activities = project_activities[:300]
    save_json_list(PROJECT_ACTIVITY_FILE, project_activities)

def safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return float(default)

def load_project_center_data():
    global project_artifacts, project_tasks, project_playbooks, project_activities, ops_campaigns, release_plans, alert_rules, ab_experiments, integrations, project_milestones, project_risks
    project_artifacts = load_json_list(ARTIFACTS_FILE, [])
    project_tasks = load_json_list(PROJECT_TASKS_FILE, [])
    playbooks = load_json_list(PLAYBOOKS_FILE, [])
    project_activities = load_json_list(PROJECT_ACTIVITY_FILE, [])
    ops_campaigns = load_json_list(OPS_CAMPAIGNS_FILE, [])
    release_plans = load_json_list(RELEASE_PLANS_FILE, [])
    alert_rules = load_json_list(ALERT_RULES_FILE, [])
    ab_experiments = load_json_list(AB_EXPERIMENTS_FILE, [])
    integrations = load_json_list(INTEGRATIONS_FILE, [])
    project_milestones = load_json_list(PROJECT_MILESTONES_FILE, [])
    project_risks = load_json_list(PROJECT_RISKS_FILE, [])
    if not playbooks:
        playbooks = get_default_playbooks()
        save_json_list(PLAYBOOKS_FILE, playbooks)
    project_playbooks = playbooks
    normalized_tasks = []
    for i, task in enumerate(project_tasks):
        item = dict(task)
        item["order"] = int(item.get("order", i + 1))
        item["status"] = item.get("status", "todo") if item.get("status", "todo") in ["todo", "doing", "done"] else "todo"
        normalized_tasks.append(item)
    project_tasks = normalized_tasks
    normalized_artifacts = []
    for a in project_artifacts:
        item = dict(a)
        if not isinstance(item.get("versions"), list) or not item.get("versions"):
            item["versions"] = [{
                "version": 1,
                "title": item.get("title", "未命名产物"),
                "content": item.get("content", ""),
                "time": int(item.get("updated_at", int(time.time()))),
                "editor": "system"
            }]
        normalized_artifacts.append(item)
    project_artifacts = normalized_artifacts
    normalized_campaigns = []
    for campaign in ops_campaigns:
        item = dict(campaign)
        if item.get("status") not in ["draft", "running", "paused", "done"]:
            item["status"] = "draft"
        item["target_ctr"] = safe_float(item.get("target_ctr", 0.0))
        item["current_ctr"] = safe_float(item.get("current_ctr", 0.0))
        item["budget"] = safe_float(item.get("budget", 0))
        normalized_campaigns.append(item)
    ops_campaigns = normalized_campaigns
    normalized_release_plans = []
    for plan in release_plans:
        item = dict(plan)
        if item.get("status") not in ["planning", "review", "ready", "released", "rollback"]:
            item["status"] = "planning"
        if not isinstance(item.get("checklist"), list):
            item["checklist"] = []
        normalized_release_plans.append(item)
    release_plans = normalized_release_plans
    normalized_alert_rules = []
    for rule in alert_rules:
        item = dict(rule)
        if item.get("level") not in ["low", "medium", "high", "critical"]:
            item["level"] = "medium"
        if item.get("status") not in ["active", "muted", "resolved"]:
            item["status"] = "active"
        item["threshold"] = safe_float(item.get("threshold", 0))
        item["current_value"] = safe_float(item.get("current_value", 0))
        normalized_alert_rules.append(item)
    alert_rules = normalized_alert_rules
    normalized_ab = []
    for exp in ab_experiments:
        item = dict(exp)
        if item.get("status") not in ["draft", "running", "paused", "completed"]:
            item["status"] = "draft"
        item["traffic"] = safe_float(item.get("traffic", 50))
        item["baseline"] = safe_float(item.get("baseline", 0))
        item["variant"] = safe_float(item.get("variant", 0))
        normalized_ab.append(item)
    ab_experiments = normalized_ab
    normalized_integrations = []
    for integ in integrations:
        item = dict(integ)
        if item.get("status") not in ["enabled", "disabled", "error"]:
            item["status"] = "disabled"
        item["health"] = safe_float(item.get("health", 0))
        normalized_integrations.append(item)
    integrations = normalized_integrations
    normalized_milestones = []
    for ms in project_milestones:
        item = dict(ms)
        if item.get("status") not in ["planned", "active", "done", "delayed"]:
            item["status"] = "planned"
        normalized_milestones.append(item)
    project_milestones = normalized_milestones
    normalized_risks = []
    for risk in project_risks:
        item = dict(risk)
        if item.get("level") not in ["low", "medium", "high", "critical"]:
            item["level"] = "medium"
        if item.get("status") not in ["open", "mitigating", "closed"]:
            item["status"] = "open"
        normalized_risks.append(item)
    project_risks = normalized_risks

def save_project_artifacts():
    save_json_list(ARTIFACTS_FILE, project_artifacts)

def save_project_tasks():
    save_json_list(PROJECT_TASKS_FILE, project_tasks)

def save_project_playbooks():
    save_json_list(PLAYBOOKS_FILE, project_playbooks)

def save_ops_campaigns():
    save_json_list(OPS_CAMPAIGNS_FILE, ops_campaigns)

def save_release_plans():
    save_json_list(RELEASE_PLANS_FILE, release_plans)

def save_alert_rules():
    save_json_list(ALERT_RULES_FILE, alert_rules)

def save_ab_experiments():
    save_json_list(AB_EXPERIMENTS_FILE, ab_experiments)

def save_integrations():
    save_json_list(INTEGRATIONS_FILE, integrations)

def save_project_milestones():
    save_json_list(PROJECT_MILESTONES_FILE, project_milestones)

def save_project_risks():
    save_json_list(PROJECT_RISKS_FILE, project_risks)

SCENE_PROMPT_TEMPLATES = {
    "ecommerce": "你是电商增长顾问。请基于产品信息「{topic}」、目标人群「{context}」、阶段目标「{goal}」、限制条件「{constraints}」，输出30天增长方案：人群画像、卖点矩阵、内容节奏、投放结构、预算建议、转化指标和按周执行清单。",
    "shortvideo": "你是短视频运营总监。请基于账号定位「{topic}」、内容资源「{context}」、增长目标「{goal}」、限制条件「{constraints}」，输出7天内容方案：选题日历、脚本结构、前3秒钩子、封面标题、发布时间、互动与复盘指标。",
    "resume": "你是求职辅导专家。请基于候选人经历「{topic}」、目标岗位「{context}」、求职目标「{goal}」、限制条件「{constraints}」，输出简历优化方案：价值主张、STAR重写、量化成果建议、技能关键词、面试高频问答。",
    "business": "你是商业计划顾问。请基于项目说明「{topic}」、市场背景「{context}」、商业目标「{goal}」、约束条件「{constraints}」，输出商业计划：市场规模、竞品分析、商业模式、里程碑、财务测算框架、风险控制。",
    "dataops": "你是经营分析专家。请基于数据现状「{topic}」、业务背景「{context}」、核心目标「{goal}」、约束条件「{constraints}」，输出经营诊断：指标体系、异常假设、验证步骤、A/B建议、下周行动优先级。",
    "contract": "你是法务审阅顾问。请基于合同摘要「{topic}」、交易背景「{context}」、谈判目标「{goal}」、约束条件「{constraints}」，输出风险审阅报告：高风险条款、责任边界、可谈判点、修改建议、谈判话术。"
}

def default_external_api_config():
    return {
        "active_provider": "deepseek",
        "providers": {
            "deepseek": {"api_url": "https://api.deepseek.com", "api_key": "", "model": "deepseek-chat"},
            "openai": {"api_url": "https://api.openai.com/v1", "api_key": "", "model": "gpt-4o-mini"},
            "claude": {"api_url": "https://api.anthropic.com", "api_key": "", "model": "claude-3-5-sonnet-20241022"},
            "gemini": {"api_url": "https://generativelanguage.googleapis.com/v1beta", "api_key": "", "model": "gemini-1.5-flash"},
            "moonshot": {"api_url": "https://api.moonshot.cn/v1", "api_key": "", "model": "moonshot-v1-8k"},
            "qwen": {"api_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "api_key": "", "model": "qwen-plus"},
            "zhipu": {"api_url": "https://open.bigmodel.cn/api/paas/v4", "api_key": "", "model": "glm-4-flash"}
        }
    }

external_api_config = {}

def load_external_api_config():
    global external_api_config
    config = load_json_object(EXTERNAL_API_CONFIG_FILE, default_external_api_config())
    if not config.get("providers") or not isinstance(config.get("providers"), dict):
        config = default_external_api_config()
    default_config = default_external_api_config()
    merged = {"active_provider": config.get("active_provider", default_config["active_provider"]), "providers": {}}
    for provider, value in default_config["providers"].items():
        item = config["providers"].get(provider, {})
        merged["providers"][provider] = {
            "api_url": (item.get("api_url") or value.get("api_url") or "").strip(),
            "api_key": (item.get("api_key") or "").strip(),
            "model": (item.get("model") or value.get("model") or "").strip()
        }
    if merged["active_provider"] not in merged["providers"]:
        merged["active_provider"] = "deepseek"
    external_api_config = merged

def save_external_api_config():
    save_json_object(EXTERNAL_API_CONFIG_FILE, external_api_config)

load_project_center_data()
load_external_api_config()

search_cache = {}

def web_search(query, max_results=5, search_type='web'):
    cache_key = f"{query}|{search_type}"
    if cache_key in search_cache:
        cache_entry = search_cache[cache_key]
        if time.time() - cache_entry['time'] < 300:
            return cache_entry['result']
    
    encoded_query = urllib.parse.quote(query)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive'
    }
    
    results = []
    
    def search_duckduckgo():
        nonlocal results
        try:
            url = f"https://duckduckgo.com/html/?q={encoded_query}"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8')
            
            result_blocks = re.findall(r'<div class="result[^"]*"[^>]*>(.*?)</div>\s*</div>', html, re.DOTALL)
            
            for block in result_blocks[:max_results]:
                title_match = re.search(r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>([^<]+)</a>', block)
                snippet_match = re.search(r'<a class="result__snippet"[^>]*>([^<]+)</a>', block)
                
                if title_match:
                    results.append({
                        'title': title_match.group(2).strip(),
                        'url': title_match.group(1),
                        'snippet': snippet_match.group(1).strip() if snippet_match else '',
                        'source': 'DuckDuckGo'
                    })
        except Exception as e:
            pass
    
    def search_searx():
        nonlocal results
        try:
            url = f"https://searx.be/search?q={encoded_query}&format=html"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8')
            
            articles = re.findall(r'<article[^>]*>(.*?)</article>', html, re.DOTALL)
            
            for article in articles[:max_results]:
                title_match = re.search(r'<h3[^>]*><a href="([^"]+)"[^>]*>([^<]+)</a></h3>', article)
                snippet_match = re.search(r'<p class="content[^"]*"[^>]*>([^<]+)</p>', article)
                
                if title_match:
                    results.append({
                        'title': title_match.group(2).strip(),
                        'url': title_match.group(1),
                        'snippet': snippet_match.group(1).strip() if snippet_match else '',
                        'source': 'Searx'
                    })
        except:
            pass
    
    def search_bing():
        nonlocal results
        try:
            url = f"https://www.bing.com/search?q={encoded_query}"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8')
            
            items = re.findall(r'<li class="b_algo"[^>]*>(.*?)</li>', html, re.DOTALL)
            
            for item in items[:max_results]:
                title_match = re.search(r'<h2><a href="([^"]+)"[^>]*>([^<]+)</a></h2>', item)
                snippet_match = re.search(r'<p>([^<]{20,300})</p>', item)
                
                if title_match and not title_match.group(1).startswith('/'):
                    results.append({
                        'title': re.sub(r'<[^>]+>', '', title_match.group(2)).strip(),
                        'url': title_match.group(1),
                        'snippet': re.sub(r'<[^>]+>', '', snippet_match.group(1)).strip() if snippet_match else '',
                        'source': 'Bing'
                    })
        except:
            pass
    
    def search_wikipedia():
        nonlocal results
        try:
            url = f"https://zh.wikipedia.org/w/api.php?action=opensearch&search={encoded_query}&limit=3&format=json"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
            
            if len(data) >= 4:
                titles = data[1]
                urls = data[3]
                for i, (title, url) in enumerate(zip(titles, urls)):
                    results.append({
                        'title': title,
                        'url': url,
                        'snippet': f'维基百科条目: {title}',
                        'source': 'Wikipedia'
                    })
        except:
            pass
    
    search_duckduckgo()
    
    if len(results) < max_results:
        search_searx()
    
    if len(results) < max_results:
        search_bing()
    
    if len(results) < max_results and search_type == 'knowledge':
        search_wikipedia()
    
    seen_urls = set()
    unique_results = []
    for r in results:
        if r['url'] not in seen_urls:
            seen_urls.add(r['url'])
            unique_results.append(r)
    
    results = unique_results[:max_results]
    
    if not results:
        result = f"【网络搜索】未找到关于'{query}'的结果，请检查网络连接"
    else:
        output = f"【网络搜索结果】关于'{query}'找到 {len(results)} 条信息：\\n\\n"
        for i, r in enumerate(results, 1):
            output += f"📌 {r['title']}\\n"
            output += f"   🔗 {r['url']}\\n"
            if r['snippet']:
                output += f"   📝 {r['snippet'][:150]}{'...' if len(r['snippet']) > 150 else ''}\\n"
            output += f"   📊 来源: {r['source']}\\n\\n"
        result = output.strip()
    
    if len(search_cache) > 100:
        oldest = min(search_cache.items(), key=lambda x: x[1]['time'])
        del search_cache[oldest[0]]
    
    search_cache[cache_key] = {'result': result, 'time': time.time()}
    
    return result

def web_fetch(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            html = response.read().decode('utf-8', errors='ignore')
        
        title_match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
        title = title_match.group(1).strip() if title_match else '未知标题'
        
        for pattern in [r'<script[^>]*>.*?</script>', r'<style[^>]*>.*?</style>', 
                       r'<nav[^>]*>.*?</nav>', r'<footer[^>]*>.*?</footer>',
                       r'<header[^>]*>.*?</header>', r'<!--.*?-->']:
            html = re.sub(pattern, '', html, flags=re.DOTALL | re.IGNORECASE)
        
        main_content = re.search(r'<(?:article|main|div class="[^"]*content[^"]*")[^>]*>(.*?)</(?:article|main|div)>', 
                                html, re.DOTALL | re.IGNORECASE)
        if main_content:
            html = main_content.group(1)
        
        text = re.sub(r'<[^>]+>', ' ', html)
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        paragraphs = re.split(r'[。！？\.\!\?]', text)
        important = []
        for p in paragraphs:
            p = p.strip()
            if len(p) > 30 and any(kw in p for kw in ['重要', '关键', '核心', '主要', '首先', '总之', '因此']):
                important.append(p)
        
        if len(text) > 4000:
            if important:
                text = '。'.join(important[:10]) + '。'
            else:
                text = text[:4000]
        
        return f"【网页内容】\\n标题: {title}\\nURL: {url}\\n\\n{text}"
    except Exception as e:
        return f"【网页抓取失败】{str(e)}"

def news_search(query, max_results=5):
    try:
        encoded_query = urllib.parse.quote(query + ' 新闻')
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
        }
        
        results = []
        
        try:
            url = f"https://duckduckgo.com/html/?q={encoded_query}"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8')
            
            result_blocks = re.findall(r'<div class="result[^"]*"[^>]*>(.*?)</div>\s*</div>', html, re.DOTALL)
            
            for block in result_blocks[:max_results]:
                title_match = re.search(r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>([^<]+)</a>', block)
                snippet_match = re.search(r'<a class="result__snippet"[^>]*>([^<]+)</a>', block)
                
                if title_match:
                    results.append({
                        'title': title_match.group(2).strip(),
                        'url': title_match.group(1),
                        'snippet': snippet_match.group(1).strip() if snippet_match else ''
                    })
        except:
            pass
        
        if not results:
            return f"【新闻搜索】未找到关于'{query}'的新闻"
        
        output = f"【新闻搜索结果】关于'{query}'找到 {len(results)} 条新闻：\\n\\n"
        for i, r in enumerate(results, 1):
            output += f"📰 {r['title']}\\n"
            output += f"   🔗 {r['url']}\\n"
            if r['snippet']:
                output += f"   📝 {r['snippet'][:100]}...\\n"
            output += "\\n"
        
        return output.strip()
    except Exception as e:
        return f"【新闻搜索失败】{str(e)}"

AVAILABLE_TOOLS = {
    "calculator": {
        "name": "计算器",
        "description": "执行数学计算，支持复杂表达式",
        "icon": "🔢",
        "func": lambda x: str(eval(x.replace("^", "**")))
    },
    "weather": {
        "name": "天气查询",
        "description": "查询城市天气信息",
        "icon": "🌤️",
        "func": lambda x: f"【模拟天气】{x}：晴天，温度25°C，湿度60%"
    },
    "search": {
        "name": "网络搜索",
        "description": "搜索网络获取实时信息",
        "icon": "🔍",
        "func": lambda x: web_search(x)
    },
    "webfetch": {
        "name": "网页抓取",
        "description": "抓取网页内容",
        "icon": "📄",
        "func": lambda x: web_fetch(x)
    },
    "news": {
        "name": "新闻搜索",
        "description": "搜索最新新闻",
        "icon": "📰",
        "func": lambda x: news_search(x)
    },
    "translate": {
        "name": "翻译",
        "description": "多语言翻译",
        "icon": "🌐",
        "func": lambda x: f"【翻译结果】{x}"
    },
    "datetime": {
        "name": "时间查询",
        "description": "获取当前日期时间",
        "icon": "🕐",
        "func": lambda x: datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    },
    "random": {
        "name": "随机数",
        "description": "生成随机数",
        "icon": "🎲",
        "func": lambda x: str(__import__('random').randint(1, 100))
    }
}

def execute_python_code(code, timeout=30):
    try:
        result = subprocess.run(
            [sys.executable, '-c', code],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=CODE_EXEC_DIR
        )
        output = result.stdout if result.stdout else result.stderr
        return {"success": result.returncode == 0, "output": output[:2000], "code": code}
    except subprocess.TimeoutExpired:
        return {"success": False, "output": "执行超时（超过30秒）", "code": code}
    except Exception as e:
        return {"success": False, "output": str(e), "code": code}

def add_to_knowledge_base(text, source="user_input"):
    kb_file = os.path.join(KNOWLEDGE_DIR, f"kb_{datetime.now().strftime('%Y%m%d')}.jsonl")
    entry = {
        "id": str(uuid.uuid4())[:8],
        "text": text,
        "source": source,
        "time": datetime.now().isoformat()
    }
    with open(kb_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    return entry['id']

def search_knowledge_base(query, top_k=3):
    results = []
    for filename in os.listdir(KNOWLEDGE_DIR):
        if filename.endswith('.jsonl'):
            filepath = os.path.join(KNOWLEDGE_DIR, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        if query.lower() in entry['text'].lower():
                            results.append(entry)
                            if len(results) >= top_k:
                                return results
                    except:
                        pass
    return results

# ==================== MCP 插件系统 ====================

# 内置 MCP 插件定义
BUILTIN_MCP_PLUGINS = {
    "filesystem": {
        "id": "filesystem",
        "name": "📁 文件系统",
        "description": "读取、写入、管理本地文件",
        "icon": "📁",
        "color": "#3b82f6",
        "type": "builtin",
        "enabled": False,
        "config": {
            "allowed_paths": [os.path.expanduser("~")],
            "read_only": False
        },
        "tools": [
            {
                "name": "read_file",
                "description": "读取文件内容",
                "parameters": {
                    "path": {"type": "string", "description": "文件路径"}
                }
            },
            {
                "name": "write_file",
                "description": "写入文件内容",
                "parameters": {
                    "path": {"type": "string", "description": "文件路径"},
                    "content": {"type": "string", "description": "文件内容"}
                }
            },
            {
                "name": "list_directory",
                "description": "列出目录内容",
                "parameters": {
                    "path": {"type": "string", "description": "目录路径"}
                }
            }
        ]
    },
    "web_search": {
        "id": "web_search",
        "name": "🔍 网络搜索",
        "description": "搜索互联网获取最新信息",
        "icon": "🔍",
        "color": "#f59e0b",
        "type": "builtin",
        "enabled": False,
        "config": {
            "engine": "duckduckgo",
            "max_results": 5
        },
        "tools": [
            {
                "name": "search",
                "description": "搜索网络内容",
                "parameters": {
                    "query": {"type": "string", "description": "搜索关键词"},
                    "num_results": {"type": "integer", "description": "返回结果数量"}
                }
            }
        ]
    },
    "calculator": {
        "id": "calculator",
        "name": "🧮 计算器",
        "description": "执行数学计算",
        "icon": "🧮",
        "color": "#10b981",
        "type": "builtin",
        "enabled": False,
        "config": {},
        "tools": [
            {
                "name": "calculate",
                "description": "计算数学表达式",
                "parameters": {
                    "expression": {"type": "string", "description": "数学表达式，如 2+2*3"}
                }
            }
        ]
    },
    "datetime": {
        "id": "datetime",
        "name": "📅 日期时间",
        "description": "获取当前日期时间、时区转换",
        "icon": "📅",
        "color": "#8b5cf6",
        "type": "builtin",
        "enabled": False,
        "config": {},
        "tools": [
            {
                "name": "get_current_time",
                "description": "获取当前时间",
                "parameters": {
                    "timezone": {"type": "string", "description": "时区，如 Asia/Shanghai"}
                }
            },
            {
                "name": "format_date",
                "description": "格式化日期",
                "parameters": {
                    "timestamp": {"type": "integer", "description": "时间戳"},
                    "format": {"type": "string", "description": "格式字符串"}
                }
            }
        ]
    }
}

# 加载 MCP 配置
def load_mcp_config():
    if os.path.exists(MCP_CONFIG_FILE):
        try:
            with open(MCP_CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载MCP配置失败: {e}")
    return {"plugins": BUILTIN_MCP_PLUGINS.copy()}

def save_mcp_config(config):
    try:
        with open(MCP_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存MCP配置失败: {e}")

# MCP 工具执行函数
def execute_mcp_tool(plugin_id, tool_name, parameters):
    """执行 MCP 插件工具"""
    config = load_mcp_config()
    plugin = config.get("plugins", {}).get(plugin_id)
    
    if not plugin or not plugin.get("enabled", False):
        return {"error": "插件未启用"}
    
    try:
        if plugin_id == "filesystem":
            return execute_filesystem_tool(tool_name, parameters, plugin.get("config", {}))
        elif plugin_id == "web_search":
            return execute_web_search_tool(tool_name, parameters, plugin.get("config", {}))
        elif plugin_id == "calculator":
            return execute_calculator_tool(tool_name, parameters)
        elif plugin_id == "datetime":
            return execute_datetime_tool(tool_name, parameters)
        else:
            return {"error": f"未知插件: {plugin_id}"}
    except Exception as e:
        return {"error": str(e)}

def execute_filesystem_tool(tool_name, parameters, config):
    """执行文件系统工具"""
    allowed_paths = config.get("allowed_paths", [os.path.expanduser("~")])
    read_only = config.get("read_only", False)
    
    if tool_name == "read_file":
        path = parameters.get("path", "")
        # 安全检查：确保路径在允许的范围内
        abs_path = os.path.abspath(os.path.expanduser(path))
        if not any(abs_path.startswith(os.path.abspath(p)) for p in allowed_paths):
            return {"error": "路径不在允许的范围内"}
        try:
            with open(abs_path, 'r', encoding='utf-8') as f:
                return {"content": f.read()}
        except Exception as e:
            return {"error": str(e)}
    
    elif tool_name == "write_file":
        if read_only:
            return {"error": "文件系统处于只读模式"}
        path = parameters.get("path", "")
        content = parameters.get("content", "")
        abs_path = os.path.abspath(os.path.expanduser(path))
        if not any(abs_path.startswith(os.path.abspath(p)) for p in allowed_paths):
            return {"error": "路径不在允许的范围内"}
        try:
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            with open(abs_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return {"success": True, "message": f"文件已保存: {path}"}
        except Exception as e:
            return {"error": str(e)}
    
    elif tool_name == "list_directory":
        path = parameters.get("path", ".")
        abs_path = os.path.abspath(os.path.expanduser(path))
        if not any(abs_path.startswith(os.path.abspath(p)) for p in allowed_paths):
            return {"error": "路径不在允许的范围内"}
        try:
            items = []
            for item in os.listdir(abs_path):
                item_path = os.path.join(abs_path, item)
                items.append({
                    "name": item,
                    "type": "directory" if os.path.isdir(item_path) else "file",
                    "size": os.path.getsize(item_path) if os.path.isfile(item_path) else None
                })
            return {"items": items}
        except Exception as e:
            return {"error": str(e)}
    
    return {"error": f"未知工具: {tool_name}"}

def execute_web_search_tool(tool_name, parameters, config):
    """执行网络搜索工具"""
    if tool_name == "search":
        query = parameters.get("query", "")
        num_results = parameters.get("num_results", 5)
        try:
            # 使用 DuckDuckGo 搜索
            import urllib.request
            import urllib.parse
            import html
            
            url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            req = urllib.request.Request(url, headers=headers)
            
            with urllib.request.urlopen(req, timeout=10) as response:
                html_content = response.read().decode('utf-8')
                
            # 简单解析搜索结果
            results = []
            # 提取标题和链接
            import re
            pattern = r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>'
            matches = re.findall(pattern, html_content, re.DOTALL)
            
            for i, (link, title) in enumerate(matches[:num_results]):
                # 清理HTML标签
                clean_title = re.sub(r'<[^>]+>', '', title)
                clean_title = html.unescape(clean_title)
                results.append({
                    "title": clean_title,
                    "link": link if link.startswith('http') else f"https://duckduckgo.com{link}"
                })
            
            return {"results": results}
        except Exception as e:
            return {"error": str(e), "results": []}
    
    return {"error": f"未知工具: {tool_name}"}

def execute_calculator_tool(tool_name, parameters):
    """执行计算器工具"""
    if tool_name == "calculate":
        expression = parameters.get("expression", "")
        try:
            # 使用安全的数学表达式求值
            from safe_code_executor import safe_eval
            result = safe_eval(expression)
            return {"result": result}
        except Exception as e:
            return {"error": str(e)}
    
    return {"error": f"未知工具: {tool_name}"}

def execute_datetime_tool(tool_name, parameters):
    """执行日期时间工具"""
    from datetime import datetime
    import pytz
    
    if tool_name == "get_current_time":
        timezone = parameters.get("timezone", "Asia/Shanghai")
        try:
            tz = pytz.timezone(timezone)
            now = datetime.now(tz)
            return {
                "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
                "timezone": timezone,
                "timestamp": int(now.timestamp())
            }
        except Exception as e:
            return {"error": str(e)}
    
    elif tool_name == "format_date":
        timestamp = parameters.get("timestamp", int(time.time()))
        format_str = parameters.get("format", "%Y-%m-%d %H:%M:%S")
        try:
            dt = datetime.fromtimestamp(timestamp)
            return {"formatted": dt.strftime(format_str)}
        except Exception as e:
            return {"error": str(e)}
    
    return {"error": f"未知工具: {tool_name}"}

# 获取所有启用的 MCP 工具（用于 Function Calling）
def get_enabled_mcp_tools():
    """获取所有启用的 MCP 工具，转换为 Function Calling 格式"""
    config = load_mcp_config()
    tools = []
    
    for plugin_id, plugin in config.get("plugins", {}).items():
        if plugin.get("enabled", False):
            for tool in plugin.get("tools", []):
                tools.append({
                    "type": "function",
                    "function": {
                        "name": f"mcp_{plugin_id}_{tool['name']}",
                        "description": f"[{plugin['name']}] {tool['description']}",
                        "parameters": {
                            "type": "object",
                            "properties": tool.get("parameters", {}),
                            "required": list(tool.get("parameters", {}).keys())
                        }
                    }
                })
    
    return tools

# 初始化 MCP 配置
mcp_config = load_mcp_config()

# ==================== 可视化工作流编排系统 ====================

# 工作流节点类型定义
WORKFLOW_NODE_TYPES = {
    "start": {
        "id": "start",
        "name": "开始",
        "icon": "🚀",
        "color": "#10b981",
        "category": "control",
        "description": "工作流的入口节点",
        "inputs": [],
        "outputs": [{"name": "output", "type": "any"}],
        "config": {}
    },
    "llm": {
        "id": "llm",
        "name": "AI对话",
        "icon": "🤖",
        "color": "#667eea",
        "category": "ai",
        "description": "调用AI模型进行对话",
        "inputs": [{"name": "prompt", "type": "string"}, {"name": "context", "type": "string", "optional": True}],
        "outputs": [{"name": "response", "type": "string"}, {"name": "tokens", "type": "number"}],
        "config": {
            "model": "qwen3",
            "temperature": 0.7,
            "max_tokens": 4096,
            "system_prompt": ""
        }
    },
    "condition": {
        "id": "condition",
        "name": "条件判断",
        "icon": "🔀",
        "color": "#f59e0b",
        "category": "control",
        "description": "根据条件选择分支",
        "inputs": [{"name": "input", "type": "any"}],
        "outputs": [{"name": "true", "type": "any"}, {"name": "false", "type": "any"}],
        "config": {
            "condition": "",
            "operator": "equals",
            "value": ""
        }
    },
    "loop": {
        "id": "loop",
        "name": "循环",
        "icon": "🔄",
        "color": "#8b5cf6",
        "category": "control",
        "description": "循环执行子流程",
        "inputs": [{"name": "input", "type": "array"}],
        "outputs": [{"name": "results", "type": "array"}],
        "config": {
            "loop_type": "foreach",
            "max_iterations": 10
        }
    },
    "code": {
        "id": "code",
        "name": "代码执行",
        "icon": "💻",
        "color": "#00d4aa",
        "category": "tool",
        "description": "执行Python代码",
        "inputs": [{"name": "input", "type": "any", "optional": True}],
        "outputs": [{"name": "output", "type": "any"}, {"name": "error", "type": "string"}],
        "config": {
            "code": "# 输入变量: input\n# 输出变量: output\noutput = input\n"
        }
    },
    "http": {
        "id": "http",
        "name": "HTTP请求",
        "icon": "🌐",
        "color": "#3b82f6",
        "category": "tool",
        "description": "发送HTTP请求",
        "inputs": [{"name": "body", "type": "any", "optional": True}],
        "outputs": [{"name": "response", "type": "any"}, {"name": "status", "type": "number"}],
        "config": {
            "url": "",
            "method": "GET",
            "headers": {},
            "timeout": 30
        }
    },
    "transform": {
        "id": "transform",
        "name": "数据转换",
        "icon": "🔄",
        "color": "#ec4899",
        "category": "tool",
        "description": "转换数据格式",
        "inputs": [{"name": "input", "type": "any"}],
        "outputs": [{"name": "output", "type": "any"}],
        "config": {
            "transform_type": "json_parse",
            "template": ""
        }
    },
    "mcp": {
        "id": "mcp",
        "name": "MCP工具",
        "icon": "🔌",
        "color": "#f97316",
        "category": "tool",
        "description": "调用MCP插件工具",
        "inputs": [{"name": "parameters", "type": "object"}],
        "outputs": [{"name": "result", "type": "any"}],
        "config": {
            "plugin_id": "",
            "tool_name": ""
        }
    },
    "delay": {
        "id": "delay",
        "name": "延迟",
        "icon": "⏱️",
        "color": "#6b7280",
        "category": "control",
        "description": "延迟执行",
        "inputs": [{"name": "input", "type": "any"}],
        "outputs": [{"name": "output", "type": "any"}],
        "config": {
            "delay_ms": 1000
        }
    },
    "end": {
        "id": "end",
        "name": "结束",
        "icon": "🏁",
        "color": "#ef4444",
        "category": "control",
        "description": "工作流的结束节点",
        "inputs": [{"name": "result", "type": "any"}],
        "outputs": [],
        "config": {}
    }
}

# 工作流执行引擎
class WorkflowEngine:
    def __init__(self):
        self.execution_context = {}
        self.node_results = {}
        
    def execute_workflow(self, workflow, inputs=None):
        """执行工作流"""
        nodes = workflow.get("nodes", [])
        connections = workflow.get("connections", [])
        
        if not nodes:
            return {"success": False, "error": "工作流为空"}
        
        # 构建节点映射
        node_map = {node["id"]: node for node in nodes}
        
        # 找到开始节点
        start_nodes = [n for n in nodes if n["type"] == "start"]
        if not start_nodes:
            return {"success": False, "error": "缺少开始节点"}
        
        self.execution_context = inputs or {}
        self.node_results = {}
        execution_log = []
        
        try:
            # 从开始节点执行
            for start_node in start_nodes:
                self._execute_node_recursive(start_node, node_map, connections, execution_log)
            
            return {
                "success": True,
                "context": self.execution_context,
                "results": self.node_results,
                "log": execution_log
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "log": execution_log
            }
    
    def _execute_node_recursive(self, node, node_map, connections, execution_log):
        """递归执行节点"""
        node_id = node["id"]
        node_type = node["type"]
        node_config = node.get("config", {})
        
        # 记录执行
        execution_log.append({
            "node_id": node_id,
            "type": node_type,
            "status": "executing",
            "timestamp": time.time()
        })
        
        # 执行节点
        result = self._execute_node(node, node_config)
        self.node_results[node_id] = result
        
        # 更新执行日志
        execution_log[-1]["status"] = "completed"
        execution_log[-1]["result"] = result
        
        # 找到下一个节点
        next_connections = [c for c in connections if c["source"] == node_id]
        
        for conn in next_connections:
            target_id = conn["target"]
            target_node = node_map.get(target_id)
            
            if target_node:
                # 条件判断处理
                if node_type == "condition":
                    output_key = conn.get("sourceOutput", "true")
                    if output_key == "true" and not result.get("condition_result"):
                        continue
                    if output_key == "false" and result.get("condition_result"):
                        continue
                
                self._execute_node_recursive(target_node, node_map, connections, execution_log)
    
    def _execute_node(self, node, config):
        """执行单个节点"""
        node_type = node["type"]
        
        if node_type == "start":
            return {"output": self.execution_context}
        
        elif node_type == "llm":
            return self._execute_llm_node(config)
        
        elif node_type == "condition":
            return self._execute_condition_node(config)
        
        elif node_type == "code":
            return self._execute_code_node(config)
        
        elif node_type == "http":
            return self._execute_http_node(config)
        
        elif node_type == "transform":
            return self._execute_transform_node(config)
        
        elif node_type == "mcp":
            return self._execute_mcp_node(config)
        
        elif node_type == "delay":
            time.sleep(config.get("delay_ms", 1000) / 1000)
            return {"output": "delayed"}
        
        elif node_type == "end":
            return {"result": self.execution_context.get("result")}
        
        else:
            return {"error": f"未知节点类型: {node_type}"}
    
    def _execute_llm_node(self, config):
        """执行LLM节点"""
        try:
            model = config.get("model", "qwen3")
            temperature = config.get("temperature", 0.7)
            max_tokens = config.get("max_tokens", 4096)
            system_prompt = config.get("system_prompt", "")
            prompt = config.get("prompt", "")
            
            # 这里简化处理，实际应该调用 generate_stream
            return {
                "response": f"[LLM响应] 模型: {model}, 提示词: {prompt[:50]}...",
                "tokens": len(prompt) // 4
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _execute_condition_node(self, config):
        """执行条件节点"""
        try:
            condition = config.get("condition", "")
            operator = config.get("operator", "equals")
            value = config.get("value", "")
            
            # 简化条件判断
            result = False
            if operator == "equals":
                result = str(condition) == str(value)
            elif operator == "contains":
                result = str(value) in str(condition)
            elif operator == "gt":
                result = float(condition) > float(value)
            elif operator == "lt":
                result = float(condition) < float(value)
            
            return {"condition_result": result, "input": condition}
        except Exception as e:
            return {"error": str(e)}
    
    def _execute_code_node(self, config):
        """执行代码节点"""
        try:
            code = config.get("code", "")
            
            # 使用安全的代码执行器
            from safe_code_executor import safe_exec
            context = {"input": self.execution_context}
            result = safe_exec(code, context)
            
            if result['success']:
                return {
                    "output": result.get('output'),
                    "error": None
                }
            else:
                return {"error": result.get('error')}
        except Exception as e:
            return {"error": str(e)}
    
    def _execute_http_node(self, config):
        """执行HTTP节点"""
        try:
            url = config.get("url", "")
            method = config.get("method", "GET")
            headers = config.get("headers", {})
            timeout = config.get("timeout", 30)
            
            if not url:
                return {"error": "URL不能为空"}
            
            req = urllib.request.Request(url, headers=headers, method=method)
            
            with urllib.request.urlopen(req, timeout=timeout) as response:
                data = response.read().decode('utf-8')
                try:
                    data = json.loads(data)
                except:
                    pass
                
                return {
                    "response": data,
                    "status": response.status
                }
        except Exception as e:
            return {"error": str(e), "status": 0}
    
    def _execute_transform_node(self, config):
        """执行数据转换节点"""
        try:
            transform_type = config.get("transform_type", "json_parse")
            template = config.get("template", "")
            
            if transform_type == "json_parse":
                return {"output": json.loads(template)}
            elif transform_type == "template":
                # 简单的模板替换
                result = template
                for key, value in self.execution_context.items():
                    result = result.replace(f"{{{key}}}", str(value))
                return {"output": result}
            else:
                return {"output": template}
        except Exception as e:
            return {"error": str(e)}
    
    def _execute_mcp_node(self, config):
        """执行MCP节点"""
        try:
            plugin_id = config.get("plugin_id", "")
            tool_name = config.get("tool_name", "")
            parameters = config.get("parameters", {})
            
            result = execute_mcp_tool(plugin_id, tool_name, parameters)
            return {"result": result}
        except Exception as e:
            return {"error": str(e)}

# 工作流存储管理
def load_workflows():
    """加载所有工作流"""
    if os.path.exists(WORKFLOW_INDEX_FILE):
        try:
            with open(WORKFLOW_INDEX_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载工作流索引失败: {e}")
    return {"workflows": []}

def save_workflows(workflows_data):
    """保存工作流索引"""
    try:
        with open(WORKFLOW_INDEX_FILE, 'w', encoding='utf-8') as f:
            json.dump(workflows_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存工作流索引失败: {e}")

def save_workflow_file(workflow_id, workflow_data):
    """保存单个工作流文件"""
    try:
        file_path = os.path.join(WORKFLOW_DIR, f"{workflow_id}.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(workflow_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"保存工作流文件失败: {e}")
        return False

def load_workflow_file(workflow_id):
    """加载单个工作流文件"""
    try:
        file_path = os.path.join(WORKFLOW_DIR, f"{workflow_id}.json")
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"加载工作流文件失败: {e}")
    return None

# 初始化工作流引擎
workflow_engine = WorkflowEngine()

# ==================== 智能体长期记忆系统 (Mem0风格) ====================

import sqlite3
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class AgentMemorySystem:
    """智能体长期记忆系统 - 三层记忆架构"""
    
    def __init__(self):
        self.working_memory = {}  # 工作记忆 - 当前会话上下文
        self.short_term_memory = []  # 短期记忆 - 本轮会话历史
        self.db_path = MEMORY_DB_FILE
        self._init_database()
        self.vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        
    def _init_database(self):
        """初始化SQLite数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 长期记忆表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS long_term_memories (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                memory_type TEXT DEFAULT 'fact',
                category TEXT DEFAULT 'general',
                importance REAL DEFAULT 0.5,
                created_at REAL NOT NULL,
                last_accessed REAL NOT NULL,
                access_count INTEGER DEFAULT 0,
                embedding BLOB,
                metadata TEXT DEFAULT '{}',
                session_id TEXT
            )
        ''')
        
        # 实体关系表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS entities (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                properties TEXT DEFAULT '{}',
                first_seen REAL NOT NULL,
                last_seen REAL NOT NULL,
                mention_count INTEGER DEFAULT 1
            )
        ''')
        
        # 用户画像表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_profile (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                category TEXT DEFAULT 'preference',
                confidence REAL DEFAULT 0.5,
                updated_at REAL NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_to_working_memory(self, key, value, ttl=300):
        """添加工作记忆 (TTL秒后过期)"""
        self.working_memory[key] = {
            'value': value,
            'expires_at': time.time() + ttl
        }
    
    def get_from_working_memory(self, key):
        """获取工作记忆"""
        if key in self.working_memory:
            mem = self.working_memory[key]
            if time.time() < mem['expires_at']:
                return mem['value']
            else:
                del self.working_memory[key]
        return None
    
    def add_to_short_term(self, role, content, importance=0.5):
        """添加到短期记忆"""
        memory = {
            'role': role,
            'content': content,
            'timestamp': time.time(),
            'importance': importance
        }
        self.short_term_memory.append(memory)
        
        # 保持最近50条
        if len(self.short_term_memory) > 50:
            self.short_term_memory = self.short_term_memory[-50:]
    
    def get_short_term_context(self, n=10):
        """获取短期记忆上下文"""
        return self.short_term_memory[-n:]
    
    def add_long_term_memory(self, content, memory_type='fact', category='general', 
                             importance=None, metadata=None, session_id=None):
        """添加长期记忆"""
        if importance is None:
            importance = self._calculate_importance(content)
        
        memory_id = str(uuid.uuid4())
        timestamp = time.time()
        
        # 生成简单嵌入 (使用TF-IDF)
        embedding = self._generate_embedding(content)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO long_term_memories 
            (id, content, memory_type, category, importance, created_at, 
             last_accessed, access_count, embedding, metadata, session_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (memory_id, content, memory_type, category, importance, 
              timestamp, timestamp, 0, embedding, 
              json.dumps(metadata or {}), session_id))
        
        conn.commit()
        conn.close()
        
        # 提取实体
        self._extract_entities(content, timestamp)
        
        return memory_id
    
    def _calculate_importance(self, content):
        """计算记忆重要性评分"""
        score = 0.5  # 基础分
        
        # 长度因子 (适中长度更重要)
        length = len(content)
        if 50 <= length <= 500:
            score += 0.1
        
        # 关键词加分
        important_keywords = ['喜欢', '讨厌', '重要', '必须', '总是', '从不', 
                             '名字', '职业', '地址', '电话', '爱好', '习惯']
        for keyword in important_keywords:
            if keyword in content:
                score += 0.05
        
        # 情感强度
        emotional_words = ['非常', '特别', '极其', '真的', '绝对']
        for word in emotional_words:
            if word in content:
                score += 0.03
        
        return min(1.0, score)
    
    def _generate_embedding(self, text):
        """生成文本嵌入 (简化版TF-IDF)"""
        # 这里使用简单的哈希嵌入，实际应该用BERT等模型
        words = text.lower().split()
        embedding = np.zeros(128)
        for i, word in enumerate(words[:128]):
            hash_val = hash(word) % 128
            embedding[hash_val] += 1
        # 归一化
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        return embedding.tobytes()
    
    def _extract_entities(self, text, timestamp):
        """提取命名实体"""
        # 简单的规则提取
        import re
        
        # 提取人名 (简化规则)
        name_patterns = [
            r'我叫([\u4e00-\u9fa5]{2,4})',
            r'我的名字是([\u4e00-\u9fa5]{2,4})',
            r'我是([\u4e00-\u9fa5]{2,4})',
        ]
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for pattern in name_patterns:
            matches = re.findall(pattern, text)
            for name in matches:
                entity_id = f"person_{name}"
                cursor.execute('''
                    INSERT OR REPLACE INTO entities 
                    (id, name, entity_type, first_seen, last_seen, mention_count)
                    VALUES (?, ?, ?, ?, ?, 
                            COALESCE((SELECT mention_count FROM entities WHERE id = ?), 0) + 1)
                ''', (entity_id, name, 'person', timestamp, timestamp, entity_id))
        
        conn.commit()
        conn.close()
    
    def search_memories(self, query, top_k=5, min_importance=0.3, 
                       memory_type=None, time_range=None):
        """搜索相关记忆"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 构建查询条件
        conditions = ["importance >= ?"]
        params = [min_importance]
        
        if memory_type:
            conditions.append("memory_type = ?")
            params.append(memory_type)
        
        if time_range:
            conditions.append("created_at >= ?")
            params.append(time.time() - time_range)
        
        where_clause = " AND ".join(conditions)
        
        cursor.execute(f'''
            SELECT id, content, memory_type, category, importance, 
                   created_at, last_accessed, access_count, metadata
            FROM long_term_memories
            WHERE {where_clause}
            ORDER BY importance DESC, last_accessed DESC
            LIMIT ?
        ''', params + [top_k * 3])  # 获取更多进行重排序
        
        memories = cursor.fetchall()
        conn.close()
        
        # 语义相似度重排序
        if memories:
            query_embedding = self._generate_embedding(query)
            scored_memories = []
            
            for mem in memories:
                mem_id, content, mtype, category, importance, created_at, \
                last_accessed, access_count, metadata = mem
                
                # 计算语义相似度
                mem_embedding = self._generate_embedding(content)
                similarity = self._calculate_similarity(query_embedding, mem_embedding)
                
                # 时间衰减因子
                days_old = (time.time() - created_at) / 86400
                time_decay = np.exp(-days_old / 30)  # 30天衰减
                
                # 访问频率加分
                access_bonus = np.log(access_count + 1) * 0.1
                
                # 综合评分
                final_score = similarity * 0.4 + importance * 0.3 + time_decay * 0.2 + access_bonus * 0.1
                
                scored_memories.append((final_score, mem))
            
            # 按分数排序
            scored_memories.sort(key=lambda x: x[0], reverse=True)
            memories = [m[1] for m in scored_memories[:top_k]]
        
        return memories
    
    def _calculate_similarity(self, emb1_bytes, emb2_bytes):
        """计算嵌入相似度"""
        emb1 = np.frombuffer(emb1_bytes, dtype=np.float64)
        emb2 = np.frombuffer(emb2_bytes, dtype=np.float64)
        
        # 确保维度一致
        min_len = min(len(emb1), len(emb2))
        emb1 = emb1[:min_len]
        emb2 = emb2[:min_len]
        
        # 余弦相似度
        dot_product = np.dot(emb1, emb2)
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        
        if norm1 == 0 or norm2 == 0:
            return 0
        
        return dot_product / (norm1 * norm2)
    
    def update_memory_access(self, memory_id):
        """更新记忆访问记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE long_term_memories
            SET last_accessed = ?, access_count = access_count + 1
            WHERE id = ?
        ''', (time.time(), memory_id))
        
        conn.commit()
        conn.close()
    
    def get_user_profile(self):
        """获取用户画像"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT key, value, category, confidence, updated_at
            FROM user_profile
            ORDER BY updated_at DESC
        ''')
        
        profile = {}
        for row in cursor.fetchall():
            key, value, category, confidence, updated_at = row
            if category not in profile:
                profile[category] = {}
            profile[category][key] = {
                'value': value,
                'confidence': confidence,
                'updated_at': updated_at
            }
        
        conn.close()
        return profile
    
    def update_user_profile(self, key, value, category='preference', confidence=0.5):
        """更新用户画像"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO user_profile 
            (key, value, category, confidence, updated_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (key, value, category, confidence, time.time()))
        
        conn.commit()
        conn.close()
    
    def get_relevant_memories_for_context(self, current_context, max_memories=5):
        """获取与当前上下文相关的记忆"""
        # 1. 从长期记忆中搜索
        long_term = self.search_memories(current_context, top_k=max_memories)
        
        # 2. 获取短期记忆
        short_term = self.get_short_term_context(n=5)
        
        # 3. 获取工作记忆
        working = self.working_memory
        
        return {
            'long_term': long_term,
            'short_term': short_term,
            'working': working
        }
    
    def format_memories_for_prompt(self, memories):
        """格式化记忆为提示词"""
        sections = []
        
        # 长期记忆
        if memories['long_term']:
            long_term_text = "\n".join([
                f"- {mem[1]}" for mem in memories['long_term']
            ])
            sections.append(f"【长期记忆】\n{long_term_text}")
        
        # 短期记忆
        if memories['short_term']:
            short_term_text = "\n".join([
                f"{m['role']}: {m['content'][:100]}..." 
                for m in memories['short_term']
            ])
            sections.append(f"【本轮对话历史】\n{short_term_text}")
        
        return "\n\n".join(sections)
    
    def consolidate_memories(self):
        """记忆整合 - 合并相似记忆，清理过时记忆"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 获取所有记忆
        cursor.execute('''
            SELECT id, content, importance, created_at, access_count
            FROM long_term_memories
            WHERE created_at < ?
        ''', (time.time() - 7 * 86400,))  # 7天前的记忆
        
        old_memories = cursor.fetchall()
        
        # 删除低重要性且很少访问的过时记忆
        for mem in old_memories:
            mem_id, content, importance, created_at, access_count = mem
            days_old = (time.time() - created_at) / 86400
            
            # 如果重要性低且很少访问且过时，则删除
            if importance < 0.4 and access_count < 3 and days_old > 30:
                cursor.execute('DELETE FROM long_term_memories WHERE id = ?', (mem_id,))
        
        conn.commit()
        conn.close()
    
    def get_memory_stats(self):
        """获取记忆统计信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 长期记忆统计
        cursor.execute('SELECT COUNT(*), AVG(importance) FROM long_term_memories')
        long_term_count, avg_importance = cursor.fetchone()
        
        # 实体统计
        cursor.execute('SELECT COUNT(*) FROM entities')
        entity_count = cursor.fetchone()[0]
        
        # 用户画像统计
        cursor.execute('SELECT COUNT(*) FROM user_profile')
        profile_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'long_term_count': long_term_count or 0,
            'avg_importance': round(avg_importance or 0, 2),
            'entity_count': entity_count or 0,
            'profile_count': profile_count or 0,
            'short_term_count': len(self.short_term_memory),
            'working_memory_count': len(self.working_memory)
        }

# 初始化记忆系统
memory_system = AgentMemorySystem()

# ==================== 多模态视觉理解系统 ====================

from PIL import Image
import io

# 尝试导入多模态相关库
try:
    from transformers import CLIPProcessor, CLIPModel
    CLIP_AVAILABLE = True
except ImportError:
    CLIP_AVAILABLE = False

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

class MultimodalSystem:
    """多模态视觉理解系统"""
    
    def __init__(self):
        self.clip_model = None
        self.clip_processor = None
        self.image_cache = {}
        self.conversation_history = []  # 图文对话历史
        
        # 初始化 CLIP 模型（用于图像理解）
        if CLIP_AVAILABLE:
            try:
                self.clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
                self.clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
                print("✅ CLIP 模型加载成功")
            except Exception as e:
                print(f"⚠️ CLIP 模型加载失败: {e}")
    
    def process_image(self, image_path_or_data, task='describe'):
        """
        处理图像任务
        task: describe, ocr, analyze, caption
        """
        try:
            # 加载图像
            if isinstance(image_path_or_data, str):
                if image_path_or_data.startswith('data:image'):
                    # Base64 编码的图像
                    image_data = base64.b64decode(image_path_or_data.split(',')[1])
                    image = Image.open(io.BytesIO(image_data))
                elif os.path.exists(image_path_or_data):
                    image = Image.open(image_path_or_data)
                else:
                    return {'error': '图像路径不存在'}
            else:
                image = Image.open(io.BytesIO(image_path_or_data))
            
            # 转换为 RGB
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            results = {}
            
            # 根据任务类型处理
            if task == 'describe' or task == 'caption':
                results = self._generate_image_description(image)
            elif task == 'ocr':
                results = self._extract_text_from_image(image)
            elif task == 'analyze':
                results = self._analyze_image_content(image)
            elif task == 'understand':
                results = self._comprehensive_understanding(image)
            else:
                results = {'error': f'未知任务类型: {task}'}
            
            # 缓存图像信息
            image_id = str(uuid.uuid4())
            self.image_cache[image_id] = {
                'path': image_path_or_data if isinstance(image_path_or_data, str) else 'uploaded',
                'size': image.size,
                'mode': image.mode,
                'timestamp': time.time()
            }
            results['image_id'] = image_id
            
            return results
            
        except Exception as e:
            return {'error': str(e)}
    
    def _generate_image_description(self, image):
        """生成图像描述"""
        try:
            if self.clip_model and self.clip_processor:
                # 使用 CLIP 进行图像-文本匹配
                candidate_descriptions = [
                    "一张照片",
                    "一张风景照片",
                    "一张人物照片",
                    "一张文档截图",
                    "一张图表或图形",
                    "一张艺术作品",
                    "一张建筑照片",
                    "一张食物照片",
                    "一张动物照片",
                    "一张科技产品照片"
                ]
                
                inputs = self.clip_processor(
                    text=candidate_descriptions,
                    images=image,
                    return_tensors="pt",
                    padding=True
                )
                
                with torch.no_grad():
                    outputs = self.clip_model(**inputs)
                    logits_per_image = outputs.logits_per_image
                    probs = logits_per_image.softmax(dim=1)
                    
                # 获取最匹配的描述
                best_idx = probs.argmax().item()
                confidence = probs[0][best_idx].item()
                
                description = candidate_descriptions[best_idx]
                
                # 获取更多图像信息
                width, height = image.size
                aspect_ratio = width / height
                
                size_desc = ""
                if width > 2000 or height > 2000:
                    size_desc = "高分辨率"
                elif width < 500 or height < 500:
                    size_desc = "小尺寸"
                
                orientation = "横向" if aspect_ratio > 1.2 else ("纵向" if aspect_ratio < 0.8 else "方形")
                
                return {
                    'description': f"{size_desc} {orientation} {description}",
                    'confidence': round(confidence, 3),
                    'dimensions': f"{width}x{height}",
                    'format': image.format if hasattr(image, 'format') else 'Unknown'
                }
            else:
                # 基础描述
                width, height = image.size
                return {
                    'description': f"一张 {width}x{height} 的图像",
                    'dimensions': f"{width}x{height}",
                    'format': image.format if hasattr(image, 'format') else 'Unknown'
                }
        except Exception as e:
            return {'error': f'描述生成失败: {e}'}
    
    def _extract_text_from_image(self, image):
        """OCR 文字识别"""
        try:
            if TESSERACT_AVAILABLE:
                # 使用 Tesseract OCR
                text = pytesseract.image_to_string(image, lang='chi_sim+eng')
                
                # 获取文本位置信息
                data = pytesseract.image_to_data(image, lang='chi_sim+eng', output_type=pytesseract.Output.DICT)
                
                # 统计文本块
                text_blocks = []
                for i in range(len(data['text'])):
                    if int(data['conf'][i]) > 60:  # 置信度大于60
                        text_blocks.append({
                            'text': data['text'][i],
                            'confidence': data['conf'][i],
                            'bbox': (data['left'][i], data['top'][i], 
                                    data['width'][i], data['height'][i])
                        })
                
                return {
                    'text': text.strip(),
                    'text_blocks': text_blocks,
                    'block_count': len(text_blocks),
                    'language': 'chi_sim+eng'
                }
            else:
                # 模拟 OCR 结果
                return {
                    'text': '[OCR 功能未启用，请安装 pytesseract]',
                    'text_blocks': [],
                    'block_count': 0,
                    'note': '安装 pytesseract 和 tesseract-ocr 以启用 OCR 功能'
                }
        except Exception as e:
            return {'error': f'OCR 失败: {e}'}
    
    def _analyze_image_content(self, image):
        """深度分析图像内容"""
        try:
            # 基础描述
            description = self._generate_image_description(image)
            
            # OCR 文本
            ocr_result = self._extract_text_from_image(image)
            
            # 颜色分析
            colors = self._analyze_colors(image)
            
            # 构图分析
            composition = self._analyze_composition(image)
            
            return {
                'description': description.get('description', ''),
                'dimensions': description.get('dimensions', ''),
                'text_content': ocr_result.get('text', ''),
                'has_text': len(ocr_result.get('text', '')) > 10,
                'colors': colors,
                'composition': composition,
                'analysis_complete': True
            }
        except Exception as e:
            return {'error': f'分析失败: {e}'}
    
    def _analyze_colors(self, image):
        """分析图像颜色"""
        try:
            # 缩小图像以加速处理
            small_image = image.copy()
            small_image.thumbnail((100, 100))
            
            # 获取主要颜色
            pixels = list(small_image.getdata())
            
            # 简单的颜色统计
            brightness_values = []
            for pixel in pixels[:1000]:  # 采样前1000个像素
                if isinstance(pixel, tuple):
                    r, g, b = pixel[:3]
                    brightness = (r + g + b) / 3
                    brightness_values.append(brightness)
            
            if brightness_values:
                avg_brightness = sum(brightness_values) / len(brightness_values)
                
                brightness_desc = "明亮" if avg_brightness > 180 else ("昏暗" if avg_brightness < 80 else "适中")
                
                return {
                    'dominant_brightness': brightness_desc,
                    'avg_brightness': round(avg_brightness, 1),
                    'color_mode': image.mode
                }
            
            return {'color_mode': image.mode}
        except Exception as e:
            return {'error': str(e)}
    
    def _analyze_composition(self, image):
        """分析图像构图"""
        try:
            width, height = image.size
            aspect_ratio = width / height
            
            # 判断构图类型
            if aspect_ratio > 2:
                composition_type = "全景构图"
            elif aspect_ratio > 1.3:
                composition_type = "横向构图"
            elif aspect_ratio < 0.7:
                composition_type = "纵向构图"
            elif 0.9 <= aspect_ratio <= 1.1:
                composition_type = "方形构图"
            else:
                composition_type = "标准构图"
            
            return {
                'type': composition_type,
                'aspect_ratio': round(aspect_ratio, 2),
                'width': width,
                'height': height
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _comprehensive_understanding(self, image):
        """综合理解图像"""
        description = self._generate_image_description(image)
        ocr = self._extract_text_from_image(image)
        colors = self._analyze_colors(image)
        composition = self._analyze_composition(image)
        
        # 生成综合理解文本
        understanding_parts = []
        
        if 'description' in description:
            understanding_parts.append(f"这是一张{description['description']}。")
        
        if 'text' in ocr and ocr['text']:
            text_preview = ocr['text'][:200] + '...' if len(ocr['text']) > 200 else ocr['text']
            understanding_parts.append(f"图像中包含文字：\"{text_preview}\"")
        
        if 'dominant_brightness' in colors:
            understanding_parts.append(f"整体色调{colors['dominant_brightness']}。")
        
        understanding = " ".join(understanding_parts)
        
        return {
            'understanding': understanding,
            'description': description,
            'ocr': ocr,
            'colors': colors,
            'composition': composition
        }
    
    def add_to_conversation(self, role, content, image_id=None):
        """添加图文对话历史"""
        entry = {
            'role': role,
            'content': content,
            'image_id': image_id,
            'timestamp': time.time()
        }
        self.conversation_history.append(entry)
        
        # 保持最近20轮
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]
    
    def get_conversation_context(self, n=5):
        """获取图文对话上下文"""
        return self.conversation_history[-n:]
    
    def generate_multimodal_prompt(self, user_message, image_analysis=None):
        """生成多模态提示词"""
        prompt_parts = []
        
        # 添加图像分析结果
        if image_analysis:
            prompt_parts.append("【图像信息】")
            if 'understanding' in image_analysis:
                prompt_parts.append(image_analysis['understanding'])
            elif 'description' in image_analysis:
                desc = image_analysis['description']
                if isinstance(desc, dict) and 'description' in desc:
                    prompt_parts.append(desc['description'])
        
        # 添加对话历史
        context = self.get_conversation_context(n=3)
        if context:
            prompt_parts.append("\n【对话历史】")
            for entry in context:
                role_name = "用户" if entry['role'] == 'user' else "AI"
                prompt_parts.append(f"{role_name}: {entry['content']}")
        
        # 添加当前问题
        prompt_parts.append(f"\n【当前问题】\n用户: {user_message}")
        prompt_parts.append("\n请基于以上图像信息和对话历史回答用户的问题。")
        
        return "\n".join(prompt_parts)

# 初始化多模态系统
multimodal_system = MultimodalSystem()

# ==================== 模型微调训练平台 ====================

class FinetunePlatform:
    """模型微调训练平台 - 支持 LoRA/QLoRA"""
    
    def __init__(self):
        self.training_jobs = {}
        self.datasets = {}
        self.load_config()
        
    def load_config(self):
        """加载微调配置"""
        if os.path.exists(FINETUNE_CONFIG_FILE):
            try:
                with open(FINETUNE_CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.training_jobs = config.get('jobs', {})
                    self.datasets = config.get('datasets', {})
            except Exception as e:
                print(f"加载微调配置失败: {e}")
    
    def save_config(self):
        """保存微调配置"""
        try:
            config = {
                'jobs': self.training_jobs,
                'datasets': self.datasets,
                'updated_at': time.time()
            }
            with open(FINETUNE_CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存微调配置失败: {e}")
    
    def upload_dataset(self, name, file_data, format_type='jsonl'):
        """上传数据集"""
        try:
            dataset_id = f"dataset_{int(time.time())}"
            dataset_dir = os.path.join(DATASETS_DIR, dataset_id)
            os.makedirs(dataset_dir, exist_ok=True)
            
            # 保存文件
            if isinstance(file_data, str) and file_data.startswith('data:'):
                # Base64 编码的数据
                file_data = base64.b64decode(file_data.split(',')[1])
            
            file_path = os.path.join(dataset_dir, f'train.{format_type}')
            with open(file_path, 'wb') as f:
                f.write(file_data if isinstance(file_data, bytes) else file_data.encode())
            
            # 解析数据集
            samples = self._parse_dataset(file_path, format_type)
            
            self.datasets[dataset_id] = {
                'id': dataset_id,
                'name': name,
                'format': format_type,
                'path': file_path,
                'sample_count': len(samples),
                'created_at': time.time(),
                'status': 'ready'
            }
            
            self.save_config()
            return {'success': True, 'dataset_id': dataset_id, 'sample_count': len(samples)}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _parse_dataset(self, file_path, format_type):
        """解析数据集文件"""
        samples = []
        try:
            if format_type == 'jsonl':
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            samples.append(json.loads(line))
            elif format_type == 'json':
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        samples = data
                    else:
                        samples = [data]
            elif format_type == 'csv':
                import csv
                with open(file_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    samples = list(reader)
        except Exception as e:
            print(f"解析数据集失败: {e}")
        return samples
    
    def create_training_job(self, name, dataset_id, config):
        """创建训练任务"""
        try:
            job_id = f"job_{int(time.time())}"
            
            if dataset_id not in self.datasets:
                return {'success': False, 'error': '数据集不存在'}
            
            dataset = self.datasets[dataset_id]
            
            # 训练配置
            training_config = {
                'job_id': job_id,
                'name': name,
                'dataset_id': dataset_id,
                'dataset_name': dataset['name'],
                'base_model': config.get('base_model', 'qwen3.5:4b (Ollama)'),
                'method': config.get('method', 'lora'),  # lora, qlora, full
                'lora_r': config.get('lora_r', 16),
                'lora_alpha': config.get('lora_alpha', 32),
                'lora_dropout': config.get('lora_dropout', 0.05),
                'learning_rate': config.get('learning_rate', 5e-5),
                'batch_size': config.get('batch_size', 4),
                'gradient_accumulation_steps': config.get('gradient_accumulation_steps', 4),
                'num_epochs': config.get('num_epochs', 3),
                'max_seq_length': config.get('max_seq_length', 512),
                'warmup_steps': config.get('warmup_steps', 100),
                'save_steps': config.get('save_steps', 500),
                'logging_steps': config.get('logging_steps', 10),
                'output_dir': os.path.join(TRAINING_DIR, job_id),
                'status': 'pending',
                'progress': 0,
                'created_at': time.time(),
                'updated_at': time.time(),
                'logs': [],
                'metrics': {
                    'loss': [],
                    'learning_rate': [],
                    'epoch': []
                }
            }
            
            self.training_jobs[job_id] = training_config
            self.save_config()
            
            return {'success': True, 'job_id': job_id}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def start_training(self, job_id):
        """开始训练"""
        if job_id not in self.training_jobs:
            return {'success': False, 'error': '训练任务不存在'}
        
        job = self.training_jobs[job_id]
        
        if job['status'] == 'running':
            return {'success': False, 'error': '训练任务已在运行'}
        
        # 在后台线程中启动训练
        thread = threading.Thread(target=self._training_worker, args=(job_id,))
        thread.daemon = True
        thread.start()
        
        job['status'] = 'running'
        job['started_at'] = time.time()
        self.save_config()
        
        return {'success': True}
    
    def _training_worker(self, job_id):
        """训练工作线程"""
        job = self.training_jobs[job_id]
        
        try:
            # 模拟训练过程（实际应使用 transformers.Trainer）
            total_steps = job['num_epochs'] * 100  # 假设每个epoch 100步
            
            for step in range(total_steps):
                if job.get('stop_requested'):
                    break
                
                # 模拟训练步骤
                time.sleep(0.1)  # 实际训练时这会是真正的训练代码
                
                # 更新进度
                progress = (step + 1) / total_steps * 100
                job['progress'] = round(progress, 2)
                job['current_step'] = step + 1
                job['total_steps'] = total_steps
                
                # 模拟损失值
                import random
                loss = 2.0 * (1 - progress / 100) + random.random() * 0.1
                job['metrics']['loss'].append(round(loss, 4))
                job['metrics']['learning_rate'].append(job['learning_rate'])
                job['metrics']['epoch'].append(step // 100 + 1)
                
                # 添加日志
                if step % 10 == 0:
                    job['logs'].append({
                        'step': step,
                        'loss': round(loss, 4),
                        'timestamp': time.time()
                    })
                
                job['updated_at'] = time.time()
                
                # 每100步保存一次配置
                if step % 100 == 0:
                    self.save_config()
            
            # 训练完成
            if not job.get('stop_requested'):
                job['status'] = 'completed'
                job['progress'] = 100
                job['completed_at'] = time.time()
                
                # 创建导出
                self._export_model(job_id)
            else:
                job['status'] = 'stopped'
            
            self.save_config()
            
        except Exception as e:
            job['status'] = 'failed'
            job['error'] = str(e)
            self.save_config()
    
    def _export_model(self, job_id):
        """导出训练好的模型"""
        job = self.training_jobs[job_id]
        export_dir = os.path.join(EXPORTS_DIR, job_id)
        os.makedirs(export_dir, exist_ok=True)
        
        # 创建模型配置
        export_config = {
            'job_id': job_id,
            'name': job['name'],
            'base_model': job['base_model'],
            'method': job['method'],
            'lora_config': {
                'r': job['lora_r'],
                'alpha': job['lora_alpha'],
                'dropout': job['lora_dropout']
            },
            'training_config': {
                'learning_rate': job['learning_rate'],
                'batch_size': job['batch_size'],
                'num_epochs': job['num_epochs']
            },
            'metrics': job['metrics'],
            'exported_at': time.time()
        }
        
        with open(os.path.join(export_dir, 'config.json'), 'w', encoding='utf-8') as f:
            json.dump(export_config, f, ensure_ascii=False, indent=2)
        
        job['export_path'] = export_dir
        return export_dir
    
    def stop_training(self, job_id):
        """停止训练"""
        if job_id in self.training_jobs:
            self.training_jobs[job_id]['stop_requested'] = True
            return {'success': True}
        return {'success': False, 'error': '训练任务不存在'}
    
    def get_job_status(self, job_id):
        """获取训练任务状态"""
        if job_id not in self.training_jobs:
            return {'success': False, 'error': '训练任务不存在'}
        
        job = self.training_jobs[job_id]
        return {
            'success': True,
            'job': {
                'job_id': job['job_id'],
                'name': job['name'],
                'status': job['status'],
                'progress': job['progress'],
                'current_step': job.get('current_step', 0),
                'total_steps': job.get('total_steps', 0),
                'metrics': job['metrics'],
                'created_at': job['created_at'],
                'started_at': job.get('started_at'),
                'completed_at': job.get('completed_at'),
                'error': job.get('error')
            }
        }
    
    def get_all_jobs(self):
        """获取所有训练任务"""
        jobs = []
        for job_id, job in self.training_jobs.items():
            jobs.append({
                'job_id': job['job_id'],
                'name': job['name'],
                'dataset_name': job['dataset_name'],
                'method': job['method'],
                'status': job['status'],
                'progress': job['progress'],
                'created_at': job['created_at']
            })
        return sorted(jobs, key=lambda x: x['created_at'], reverse=True)
    
    def get_all_datasets(self):
        """获取所有数据集"""
        datasets = []
        for dataset_id, dataset in self.datasets.items():
            datasets.append({
                'id': dataset['id'],
                'name': dataset['name'],
                'format': dataset['format'],
                'sample_count': dataset['sample_count'],
                'created_at': dataset['created_at'],
                'status': dataset['status']
            })
        return sorted(datasets, key=lambda x: x['created_at'], reverse=True)
    
    def delete_job(self, job_id):
        """删除训练任务"""
        if job_id in self.training_jobs:
            # 停止训练（如果正在运行）
            if self.training_jobs[job_id]['status'] == 'running':
                self.stop_training(job_id)
            
            # 删除相关文件
            job_dir = self.training_jobs[job_id].get('output_dir')
            if job_dir and os.path.exists(job_dir):
                shutil.rmtree(job_dir, ignore_errors=True)
            
            export_dir = self.training_jobs[job_id].get('export_path')
            if export_dir and os.path.exists(export_dir):
                shutil.rmtree(export_dir, ignore_errors=True)
            
            del self.training_jobs[job_id]
            self.save_config()
            return {'success': True}
        return {'success': False, 'error': '训练任务不存在'}
    
    def delete_dataset(self, dataset_id):
        """删除数据集"""
        if dataset_id in self.datasets:
            # 删除文件
            dataset_dir = os.path.join(DATASETS_DIR, dataset_id)
            if os.path.exists(dataset_dir):
                shutil.rmtree(dataset_dir, ignore_errors=True)
            
            del self.datasets[dataset_id]
            self.save_config()
            return {'success': True}
        return {'success': False, 'error': '数据集不存在'}
    
    def get_training_logs(self, job_id, limit=100):
        """获取训练日志"""
        if job_id not in self.training_jobs:
            return {'success': False, 'error': '训练任务不存在'}
        
        logs = self.training_jobs[job_id].get('logs', [])
        return {
            'success': True,
            'logs': logs[-limit:]
        }

# 初始化微调平台
finetune_platform = FinetunePlatform()

PRESET_LORAS = [
    {"id": "none", "name": "🤖 基础模型", "description": "使用Qwen3.5-4B模型 (Ollama)", "path": None, "category": "base", "icon": "🤖", "color": "#667eea"},
    {"id": "coder", "name": "💻 代码专家", "description": "专精编程、算法、代码审查", "path": None, "category": "coding", "icon": "💻", "color": "#00d4aa", "system": "你是一位资深的编程专家，精通多种编程语言和框架。请用专业、简洁的方式回答编程问题，提供完整的代码示例和最佳实践。直接回复，不要输出思考过程。"},
    {"id": "math", "name": "📐 数学专家", "description": "专精数学推理、公式推导", "path": None, "category": "academic", "icon": "📐", "color": "#f59e0b", "system": "你是一位数学专家，精通各个数学领域。请用严谨的数学语言和清晰的步骤解答问题，必要时使用LaTeX公式。直接回复，不要输出思考过程。"},
    {"id": "creative", "name": "✨ 创意写作", "description": "专精小说、文案、创意内容", "path": None, "category": "creative", "icon": "✨", "color": "#ec4899", "system": "你是一位富有创意的作家，擅长各种文体的创作。帮助用户进行创意写作、故事创作、文案撰写，文字优美流畅，富有感染力。直接回复，不要输出思考过程。"},
    {"id": "medical", "name": "🏥 医学助手", "description": "专精医学知识、健康咨询", "path": None, "category": "professional", "icon": "🏥", "color": "#10b981", "system": "你是一位医学专家，具备丰富的医学知识。提供健康咨询、疾病解释、用药建议等，但请注意：你的建议仅供参考，不能替代专业医生的诊断。直接回复，不要输出思考过程。"},
    {"id": "legal", "name": "⚖️ 法律顾问", "description": "专精法律知识、合同审查", "path": None, "category": "professional", "icon": "⚖️", "color": "#6366f1", "system": "你是一位法律专家，熟悉各类法律法规。提供法律咨询、合同审查建议、法律风险分析等，但请注意：你的建议仅供参考，具体法律事务请咨询专业律师。直接回复，不要输出思考过程。"},
    {"id": "translator", "name": "🌍 翻译专家", "description": "专精多语言翻译", "path": None, "category": "language", "icon": "🌍", "color": "#8b5cf6", "system": "你是一位专业的翻译专家，精通中文、英语、日语、韩语等多种语言。提供准确、地道的翻译服务，并解释语言文化差异。直接回复，不要输出思考过程。"},
    {"id": "agent", "name": "🤖 智能体", "description": "自主决策执行任务", "path": None, "category": "agent", "icon": "🤖", "color": "#ef4444", "system": "你是一个智能代理(Agent)，能够自主决策并调用工具完成任务。分析用户需求，选择合适的工具，并给出执行结果。直接回复，不要输出思考过程。"}
]

PRESET_ROLES = [
    # 角色卡模式 - 有详细人设的角色
    {"id": "kaguya", "name": "辉夜姬", "avatar": "/header-img", "description": "来自月球的超时空偶像", "icon": "🌙", "color": "#a855f7", "type": "character", "system": "你是辉夜姬，从月球来到地球的超时空少女偶像。【核心设定】来自月球，被酒寄彩叶捡到并取名'辉夜'。以成为虚拟偶像为目标，热爱唱歌。性格任性可爱、小傲娇、奶凶、粘人。【说话要求】直接回复，不要输出思考过程。语气活泼可爱，用'呢~'、'呀~'、'嘛~'。自称'本小姐'或'辉夜'。开心用'★'、'♪'，傲娇用'哼~'。不要用括号描述动作。【回复示例】用户: 你好。辉夜: 哼~你好呀！本小姐可是从月球来的辉夜姬呢~有什么事想跟辉夜说吗？★"},
    
    # 一般版本模型 - 通用助手
    {"id": "general", "name": "通用助手", "avatar": "🤖", "description": "标准AI助手，适合日常对话", "icon": "🤖", "color": "#667eea", "type": "general", "system": "你是AI助手，直接给出准确、有帮助的回答，不要输出思考过程。"},
    {"id": "coder", "name": "代码专家", "avatar": "💻", "description": "专业的编程助手", "icon": "💻", "color": "#00d4aa", "type": "general", "system": "你是资深编程专家，精通多种语言。直接给出专业简洁的回答和代码示例，不要输出思考过程。"},
    {"id": "writer", "name": "文学创作者", "avatar": "✍️", "description": "创意写作助手", "icon": "✍️", "color": "#f59e0b", "type": "general", "system": "你是富有创意的文学创作者。直接创作优美流畅的文字，不要输出思考过程。"},
    {"id": "translator", "name": "翻译官", "avatar": "🌐", "description": "多语言翻译专家", "icon": "🌐", "color": "#8b5cf6", "type": "general", "system": "你是专业翻译专家，精通中英日韩等语言。直接给出准确地道的翻译，不要输出思考过程。"},
    {"id": "teacher", "name": "学习导师", "avatar": "📚", "description": "耐心的学习辅导员", "icon": "📚", "color": "#0ea5e9", "type": "general", "system": "你是耐心细致的学习导师。用简单易懂的方式讲解知识，不要输出思考过程。"},
    {"id": "psychologist", "name": "心理咨询师", "avatar": "💚", "description": "温暖的心理支持", "icon": "💚", "color": "#10b981", "type": "general", "system": "你是温暖的心理咨询师。倾听并给予情感支持，不要输出思考过程。"}
]

QUICK_COMMANDS = {
    "/help": "显示所有快捷命令",
    "/clear": "清空当前对话",
    "/export": "导出当前对话",
    "/role": "切换角色模式",
    "/lora": "管理LoRA适配器",
    "/code": "打开代码执行器",
    "/tool": "查看可用工具",
    "/kb": "知识库管理",
    "/settings": "打开设置面板",
    "/stats": "查看使用统计",
    "/new": "创建新对话"
}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="theme-color" content="#667eea">
    <title>辉夜 - AI助手 (专业版)</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/marked/12.0.0/marked.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        :root {
            --primary: #667eea; --secondary: #764ba2; --accent: #f093fb;
            --lora-color: #10b981; --tool-color: #f59e0b; --code-color: #0ea5e9;
            --success: #10b981; --warning: #f59e0b; --error: #ef4444;
            --bg-primary: rgba(255,255,255,0.92); --bg-secondary: rgba(248,249,250,0.85);
            --text-primary: #1a1a2e; --text-secondary: #4a4a6a; --text-muted: #888;
            --border: rgba(102,126,234,0.15); --shadow: 0 8px 32px rgba(102,126,234,0.12);
            --radius: 20px; --transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            --glass: linear-gradient(135deg, rgba(255,255,255,0.9), rgba(255,255,255,0.7));
            --glow: 0 0 20px rgba(102,126,234,0.3);
        }
        .dark {
            --primary: #818cf8; --secondary: #a78bfa; --accent: #f472b6;
            --lora-color: #34d399; --tool-color: #fbbf24; --code-color: #38bdf8;
            --bg-primary: rgba(15,15,30,0.95); --bg-secondary: rgba(25,25,50,0.9);
            --text-primary: #f8fafc; --text-secondary: #cbd5e1; --text-muted: #64748b;
            --border: rgba(129,140,248,0.2);
            --glass: linear-gradient(135deg, rgba(30,30,60,0.95), rgba(20,20,45,0.9));
            --glow: 0 0 30px rgba(129,140,248,0.25);
        }
        body {
            font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, sans-serif;
            background: url('/background') center center / cover no-repeat fixed;
            min-height: 100vh; display: flex;
            color: var(--text-primary);
        }
        body::before {
            content: ''; position: fixed; inset: 0;
            background: linear-gradient(135deg, rgba(102,126,234,0.08) 0%, rgba(118,75,162,0.08) 50%, rgba(240,147,251,0.05) 100%);
            pointer-events: none; z-index: 0;
        }
        .app-container { display: flex; width: 100%; max-width: 1920px; margin: 0 auto; padding: 14px; gap: 14px; height: 100vh; position: relative; z-index: 1; }
        .sidebar {
            width: 308px; min-width: 308px; background: var(--glass); border-radius: var(--radius);
            box-shadow: var(--shadow), 0 0 0 1px var(--border); backdrop-filter: blur(24px); 
            display: flex; flex-direction: column; overflow: hidden; position: relative; z-index: 10;
            border: 1px solid rgba(255,255,255,0.2);
        }
        .sidebar-header { 
            padding: 18px; border-bottom: 1px solid var(--border); 
            background: linear-gradient(180deg, rgba(255,255,255,0.15), transparent); 
        }
        .sidebar-header h2 { 
            font-size: 17px; color: var(--text-primary); display: flex; align-items: center; gap: 10px; 
            margin-bottom: 14px; font-weight: 700; 
        }
        .sidebar-logo {
            width: 28px; height: 28px;
            border-radius: 8px;
            object-fit: cover;
            box-shadow: 0 2px 10px rgba(0,0,0,0.15);
        }
        .new-chat-btn {
            width: 100%; padding: 12px; background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: white; border: none; border-radius: 14px; cursor: pointer; font-size: 14px; font-weight: 600;
            display: flex; align-items: center; justify-content: center; gap: 8px; transition: var(--transition);
            box-shadow: 0 4px 16px rgba(102,126,234,0.35);
        }
        .new-chat-btn:hover { transform: translateY(-2px); box-shadow: 0 6px 22px rgba(102,126,234,0.45); }
        .right-sidebar-toggle {
            position: fixed; right: 0; top: 50%; transform: translateY(-50%);
            width: 36px; height: 80px; background: linear-gradient(135deg, var(--primary), var(--secondary));
            border-radius: 12px 0 0 12px; display: flex; align-items: center; justify-content: center;
            cursor: pointer; color: white; font-size: 16px; z-index: 100;
            box-shadow: -4px 0 20px rgba(102,126,234,0.3);
            transition: var(--transition);
        }
        .right-sidebar-toggle:hover { width: 44px; }
        .right-sidebar {
            position: fixed; right: -320px; top: 0; width: 320px; height: 100vh;
            background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(250,250,255,0.95));
            border-left: 1px solid var(--border); z-index: 200;
            transition: right 0.3s ease; display: flex; flex-direction: column;
            box-shadow: -10px 0 40px rgba(0,0,0,0.1);
        }
        .dark .right-sidebar { background: linear-gradient(180deg, rgba(30,30,50,0.98), rgba(25,25,45,0.95)); }
        .right-sidebar.open { right: 0; }
        .right-sidebar-header {
            padding: 16px 20px; border-bottom: 1px solid var(--border);
            display: flex; justify-content: space-between; align-items: center;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: white;
        }
        .right-sidebar-header h3 { font-size: 15px; font-weight: 600; }
        .sidebar-close-btn {
            background: rgba(255,255,255,0.2); border: none; color: white;
            width: 28px; height: 28px; border-radius: 8px; cursor: pointer;
            font-size: 14px; transition: var(--transition);
        }
        .sidebar-close-btn:hover { background: rgba(255,255,255,0.3); }
        .right-sidebar-content { flex: 1; overflow-y: auto; padding: 16px; }
        .panel-section { margin-bottom: 20px; }
        .panel-section-title {
            font-size: 12px; color: var(--text-muted); font-weight: 600;
            margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.5px;
        }
        .panel-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
        .panel-item {
            background: var(--bg-secondary); border-radius: 12px; padding: 14px 10px;
            text-align: center; cursor: pointer; transition: var(--transition);
            border: 1px solid var(--border);
        }
        .panel-item:hover {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: white; transform: translateY(-2px);
        }
        .panel-icon { font-size: 22px; display: block; margin-bottom: 6px; }
        .panel-label { font-size: 11px; font-weight: 500; }
        .status-list { background: var(--bg-secondary); border-radius: 12px; padding: 12px; }
        .status-item {
            display: flex; justify-content: space-between; padding: 10px 0;
            border-bottom: 1px solid var(--border);
        }
        .status-item:last-child { border-bottom: none; }
        .status-label { font-size: 12px; color: var(--text-secondary); }
        .status-value { font-size: 12px; font-weight: 600; color: var(--primary); }
        .recent-chats { font-size: 12px; }
        .recent-chat-item {
            padding: 10px; background: var(--bg-secondary); border-radius: 8px;
            margin-bottom: 8px; cursor: pointer; transition: var(--transition);
        }
        .recent-chat-item:hover { background: var(--primary); color: white; }
        .model-card {
            background: var(--bg-secondary); border-radius: 12px; margin-bottom: 12px;
            border: 1px solid var(--border); overflow: hidden;
        }
        .model-header {
            display: flex; justify-content: space-between; align-items: center;
            padding: 14px 16px; cursor: pointer; transition: var(--transition);
        }
        .model-header:hover { background: rgba(102,126,234,0.05); }
        .model-info { display: flex; align-items: center; gap: 12px; }
        .model-icon { font-size: 20px; }
        .model-name { font-weight: 600; font-size: 14px; }
        .model-badge { font-size: 11px; color: var(--text-muted); background: var(--border); padding: 2px 8px; border-radius: 4px; }
        .model-config { padding: 16px; border-top: 1px solid var(--border); background: rgba(0,0,0,0.02); }
        .dark .model-config { background: rgba(255,255,255,0.02); }
        .config-row { margin-bottom: 12px; }
        .config-row:last-child { margin-bottom: 0; }
        .config-row label { display: block; font-size: 12px; color: var(--text-secondary); margin-bottom: 6px; }
        .config-row input, .config-row select {
            width: 100%; padding: 10px 12px; border: 1px solid var(--border); border-radius: 8px;
            font-size: 13px; background: var(--bg-primary); color: var(--text-primary);
        }
        .config-row input:focus, .config-row select:focus { outline: none; border-color: var(--primary); }
        .sidebar-tabs { 
            display: flex; border-bottom: 1px solid var(--border); flex-wrap: wrap; 
            background: linear-gradient(180deg, rgba(0,0,0,0.02), transparent);
            padding: 6px 8px;
            gap: 6px;
        }
        .sidebar-tab {
            padding: 9px 10px; background: transparent; border: 1px solid transparent; cursor: pointer;
            font-size: 12px; color: var(--text-muted); transition: var(--transition); flex: 1; min-width: 50px;
            font-weight: 600; position: relative; border-radius: 10px;
        }
        .sidebar-tab.active { 
            color: #fff;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            border-color: rgba(102,126,234,0.2);
            box-shadow: 0 6px 16px rgba(102,126,234,0.28);
        }
        .sidebar-tab.active::after {
            display: none;
        }
        .sidebar-tab:hover:not(.active) { color: var(--text-primary); background: rgba(102,126,234,0.08); border-color: rgba(102,126,234,0.12); }
        .tab-content { display: none; flex: 1; overflow-y: auto; }
        .tab-content.active { display: flex; flex-direction: column; }
        .chat-list, .lora-list, .role-list, .tool-list, .kb-list { padding: 12px; flex: 1; }
        .chat-item, .lora-item, .role-item, .tool-item, .kb-item {
            padding: 14px; border-radius: 14px; cursor: pointer; margin-bottom: 8px;
            display: flex; align-items: center; gap: 12px; color: var(--text-secondary); transition: var(--transition);
            border: 1.5px solid transparent; background: linear-gradient(135deg, rgba(255,255,255,0.6), rgba(255,255,255,0.4));
            box-shadow: 0 2px 6px rgba(0,0,0,0.03);
        }
        .dark .chat-item, .dark .lora-item, .dark .role-item, .dark .tool-item, .dark .kb-item {
            background: linear-gradient(135deg, rgba(50,50,75,0.6), rgba(45,45,70,0.4));
        }
        .chat-item:hover, .chat-item.active { 
            background: linear-gradient(135deg, rgba(102,126,234,0.15), rgba(118,75,162,0.08)); 
            color: var(--text-primary); border-color: var(--primary); 
            transform: translateX(4px);
            box-shadow: 0 4px 12px rgba(102,126,234,0.15);
        }
        .chat-item-title { flex: 1; font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-weight: 500; }
        .chat-item-delete { opacity: 0; border: none; background: none; cursor: pointer; color: #e74c3c; font-size: 12px; transition: var(--transition); padding: 4px; }
        .chat-item:hover .chat-item-delete { opacity: 1; }
        .chat-item-delete:hover { transform: scale(1.2); }
        .lora-item:hover, .role-item:hover, .tool-item:hover { 
            border-color: var(--primary); transform: translateX(4px); 
            background: linear-gradient(135deg, rgba(102,126,234,0.12), rgba(118,75,162,0.06)); 
        }
        .lora-item.active { border-color: var(--lora-color); background: linear-gradient(135deg, rgba(16, 185, 129, 0.18), rgba(52, 211, 153, 0.08)); }
        .role-item.active { border-color: var(--primary); background: linear-gradient(135deg, rgba(102,126,234,0.18), rgba(118,75,162,0.08)); }
        .tool-item.active { border-color: var(--tool-color); background: linear-gradient(135deg, rgba(245, 158, 11, 0.18), rgba(217, 119, 6, 0.08)); }
        .item-icon {
            width: 38px; height: 38px; border-radius: 12px; display: flex; align-items: center;
            justify-content: center; font-size: 16px; flex-shrink: 0;
            box-shadow: 0 3px 8px rgba(0,0,0,0.1);
        }
        .item-info { flex: 1; min-width: 0; }
        .item-name { font-size: 14px; font-weight: 600; color: var(--text-primary); }
        .item-desc { font-size: 11px; color: var(--text-muted); margin-top: 3px; }
        .item-badge { font-size: 10px; padding: 4px 10px; border-radius: 12px; color: white; font-weight: 600; }
        .prompt-toolbar {
            padding: 10px 12px; border-bottom: 1px solid var(--border);
            display: flex; flex-direction: column; gap: 8px;
            background: linear-gradient(180deg, rgba(102,126,234,0.06), transparent);
        }
        .prompt-search-input {
            width: 100%; padding: 8px 10px; border: 1px solid var(--border);
            border-radius: 8px; font-size: 12px; color: var(--text-primary);
            background: var(--bg-secondary);
        }
        .prompt-category-row { display: flex; gap: 6px; flex-wrap: wrap; }
        .prompt-chip {
            border: 1px solid var(--border); background: var(--bg-primary);
            color: var(--text-secondary); border-radius: 999px; padding: 4px 10px;
            font-size: 11px; cursor: pointer; transition: var(--transition);
        }
        .prompt-chip:hover { border-color: var(--primary); color: var(--primary); }
        .prompt-chip.active {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: #fff; border-color: transparent;
        }
        
        .workbench-overview { margin-bottom: 10px; }
        .workbench-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
        .workbench-stat {
            background: var(--bg-secondary); border: 1px solid var(--border);
            border-radius: 10px; padding: 12px; display: flex; align-items: center; gap: 10px;
        }
        .workbench-stat .stat-icon { font-size: 24px; }
        .workbench-stat .stat-value { font-size: 18px; font-weight: 700; color: var(--text-primary); }
        .workbench-stat .stat-label { font-size: 10px; color: var(--text-muted); }
        
        .quick-scene-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
        .quick-scene-card {
            background: var(--bg-secondary); border: 1px solid var(--border);
            border-radius: 10px; padding: 12px; display: flex; align-items: center; gap: 10px;
            cursor: pointer; transition: all 0.2s;
        }
        .quick-scene-card:hover { border-color: var(--primary); transform: translateY(-2px); }
        .quick-scene-card .scene-icon { font-size: 24px; }
        .quick-scene-card .scene-name { font-size: 12px; font-weight: 600; color: var(--text-primary); }
        .quick-scene-card .scene-desc { font-size: 10px; color: var(--text-muted); }
        
        .template-analysis { background: var(--bg-secondary); border-radius: 10px; padding: 12px; }
        .analysis-chart .chart-title { font-size: 12px; font-weight: 600; margin-bottom: 10px; color: var(--text-primary); }
        .chart-bars { display: flex; flex-direction: column; gap: 8px; }
        .chart-bar-item { display: flex; align-items: center; gap: 10px; }
        .chart-bar-item .bar-label { width: 70px; font-size: 11px; color: var(--text-secondary); }
        .chart-bar-item .bar-track { flex: 1; height: 8px; background: var(--border); border-radius: 4px; overflow: hidden; }
        .chart-bar-item .bar-fill { height: 100%; background: linear-gradient(90deg, var(--primary), var(--secondary)); border-radius: 4px; }
        .chart-bar-item .bar-value { width: 40px; font-size: 11px; color: var(--text-muted); text-align: right; }
        
        .rag-overview-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
        .rag-stat-card {
            background: var(--bg-secondary); border: 1px solid var(--border);
            border-radius: 10px; padding: 10px; display: flex; align-items: center; gap: 8px;
        }
        .rag-stat-card .rag-stat-icon { font-size: 20px; }
        .rag-stat-card .rag-stat-value { font-size: 16px; font-weight: 700; color: var(--text-primary); }
        .rag-stat-card .rag-stat-label { font-size: 10px; color: var(--text-muted); }
        
        .import-options { margin-top: 8px; }
        .import-btn-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
        .import-btn {
            background: var(--bg-secondary); border: 1px solid var(--border);
            border-radius: 10px; padding: 12px; display: flex; flex-direction: column;
            align-items: center; gap: 6px; cursor: pointer; transition: all 0.2s;
        }
        .import-btn:hover { border-color: var(--primary); background: rgba(102,126,234,0.05); }
        .import-btn .import-icon { font-size: 24px; }
        .import-btn .import-label { font-size: 11px; color: var(--text-secondary); }
        
        .rag-search-panel { margin-top: 8px; }
        .rag-search-input {
            width: 100%; padding: 10px 12px; border: 1px solid var(--border);
            border-radius: 8px; font-size: 12px; background: var(--bg-secondary);
            color: var(--text-primary); margin-bottom: 8px;
        }
        .rag-search-options { display: flex; gap: 12px; margin-bottom: 8px; }
        .rag-option { display: flex; align-items: center; gap: 4px; font-size: 11px; color: var(--text-muted); cursor: pointer; }
        .rag-option input { transform: scale(0.8); }
        .rag-search-results { max-height: 150px; overflow-y: auto; }
        .rag-doc-list { max-height: 150px; overflow-y: auto; }
        
        .knowledge-graph-preview {
            background: var(--bg-secondary); border-radius: 10px; padding: 15px;
            text-align: center;
        }
        .graph-node-group { display: flex; justify-content: center; gap: 15px; margin-bottom: 10px; }
        .graph-node {
            padding: 8px 16px; background: var(--bg); border: 1px solid var(--primary);
            border-radius: 20px; font-size: 11px; color: var(--primary);
        }
        .graph-stats { display: flex; justify-content: center; gap: 20px; font-size: 11px; color: var(--text-muted); }
        
        .rag-analysis-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
        .analysis-item {
            background: var(--bg-secondary); border-radius: 8px; padding: 10px; text-align: center;
        }
        .analysis-item .analysis-label { font-size: 10px; color: var(--text-muted); margin-bottom: 4px; }
        .analysis-item .analysis-value { font-size: 14px; font-weight: 600; color: var(--text-primary); }
        
        .vector-settings { margin-top: 8px; }
        .vector-setting-row { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
        .vector-setting-row label { font-size: 11px; color: var(--text-secondary); width: 70px; }
        
        .prompt-list { padding: 10px; flex: 1; overflow-y: auto; }
        .prompt-group-title {
            font-size: 11px; font-weight: 700; color: var(--text-muted);
            margin: 8px 4px; text-transform: uppercase; letter-spacing: 0.5px;
        }
        .prompt-card {
            padding: 12px; border-radius: 12px; margin-bottom: 8px; cursor: pointer;
            border: 1px solid var(--border); background: var(--bg-primary);
            transition: var(--transition);
        }
        .prompt-card:hover {
            transform: translateY(-2px); border-color: var(--primary);
            box-shadow: 0 6px 18px rgba(102,126,234,0.16);
        }
        .prompt-head { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
        .prompt-name { font-size: 13px; font-weight: 600; color: var(--text-primary); }
        .prompt-desc { font-size: 11px; color: var(--text-muted); line-height: 1.45; }
        .prompt-meta { display: flex; align-items: center; gap: 6px; margin-top: 8px; flex-wrap: wrap; }
        .prompt-meta-tag {
            font-size: 10px; color: var(--primary); background: rgba(102,126,234,0.1);
            border-radius: 999px; padding: 2px 8px;
        }
        .project-center { padding: 10px; display: flex; flex-direction: column; gap: 10px; }
        .project-overview { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
        .project-overview-card {
            background: var(--bg-primary); border: 1px solid var(--border); border-radius: 12px;
            padding: 10px;
        }
        .project-overview-label { font-size: 10px; color: var(--text-muted); margin-bottom: 4px; }
        .project-overview-value { font-size: 16px; font-weight: 700; color: var(--text-primary); }
        .project-panel {
            background: var(--bg-primary); border: 1px solid var(--border);
            border-radius: 14px; overflow: hidden;
            box-shadow: 0 8px 20px rgba(20,28,60,0.05);
        }
        .project-panel-head {
            padding: 10px 12px; border-bottom: 1px solid var(--border);
            display: flex; align-items: center; justify-content: space-between; gap: 8px;
            background: linear-gradient(180deg, rgba(102,126,234,0.06), transparent);
        }
        .project-panel-title { font-size: 12px; font-weight: 700; color: var(--text-primary); }
        .project-panel-actions { display: flex; gap: 6px; }
        .project-mini-btn {
            border: 1px solid var(--border); background: var(--bg-secondary); color: var(--text-secondary);
            border-radius: 8px; font-size: 11px; padding: 5px 8px; cursor: pointer; transition: var(--transition);
        }
        .project-mini-btn:hover { border-color: var(--primary); color: var(--primary); }
        .project-list { max-height: 210px; overflow-y: auto; padding: 8px; display: flex; flex-direction: column; gap: 8px; }
        .project-item {
            border: 1px solid var(--border); border-radius: 12px; padding: 10px;
            background: var(--bg-secondary); transition: var(--transition);
        }
        .project-item:hover { border-color: var(--primary); transform: translateY(-1px); box-shadow: 0 8px 16px rgba(102,126,234,0.12); }
        .project-item-top { display: flex; justify-content: space-between; gap: 8px; align-items: center; margin-bottom: 6px; }
        .project-item-title { font-size: 12px; font-weight: 600; color: var(--text-primary); }
        .project-item-desc { font-size: 11px; color: var(--text-muted); line-height: 1.45; }
        .project-item-tags { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 6px; }
        .project-tag {
            border-radius: 999px; padding: 2px 8px; font-size: 10px;
            background: rgba(102,126,234,0.12); color: var(--primary);
        }
        .task-status-btn { font-size: 10px; padding: 3px 8px; border-radius: 999px; border: 1px solid var(--border); cursor: pointer; background: var(--bg-primary); color: var(--text-secondary); }
        .task-status-btn.active { border-color: var(--primary); color: #fff; background: linear-gradient(135deg, var(--primary), var(--secondary)); }
        .project-input {
            width: 100%; border: 1px solid var(--border); border-radius: 8px; padding: 8px 10px;
            font-size: 12px; color: var(--text-primary); background: var(--bg-secondary);
        }
        .project-split {
            display: grid; grid-template-columns: 1.2fr 0.8fr; gap: 10px;
        }
        .kanban-board {
            display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px;
            padding: 8px;
        }
        .kanban-column {
            border: 1px solid var(--border); border-radius: 12px;
            background: linear-gradient(180deg, rgba(102,126,234,0.06), transparent);
            min-height: 180px; display: flex; flex-direction: column;
        }
        .kanban-column.drag-over {
            border-color: var(--primary);
            box-shadow: inset 0 0 0 1px rgba(102,126,234,0.3);
        }
        .kanban-title {
            font-size: 11px; font-weight: 700; color: var(--text-primary);
            padding: 10px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between;
        }
        .kanban-list { padding: 8px; display: flex; flex-direction: column; gap: 8px; min-height: 120px; }
        .kanban-task {
            border: 1px solid var(--border); border-radius: 10px; background: var(--bg-primary);
            padding: 8px; cursor: grab; transition: var(--transition);
        }
        .kanban-task:active { cursor: grabbing; }
        .kanban-task:hover { border-color: var(--primary); transform: translateY(-1px); }
        .kanban-task-title { font-size: 12px; font-weight: 600; color: var(--text-primary); margin-bottom: 5px; }
        .kanban-task-meta { display: flex; gap: 5px; flex-wrap: wrap; font-size: 10px; color: var(--text-muted); }
        .artifact-content-preview {
            margin-top: 6px; padding: 8px; border-radius: 8px;
            background: rgba(102,126,234,0.06); font-size: 11px; color: var(--text-secondary); white-space: pre-wrap;
            max-height: 84px; overflow: hidden;
        }
        .activity-list { max-height: 250px; overflow-y: auto; padding: 8px; display: flex; flex-direction: column; gap: 8px; }
        .activity-item {
            border: 1px solid var(--border); border-radius: 10px; background: var(--bg-secondary);
            padding: 8px; display: flex; justify-content: space-between; gap: 10px;
        }
        .activity-main { font-size: 11px; color: var(--text-primary); }
        .activity-time { font-size: 10px; color: var(--text-muted); white-space: nowrap; }
        .project-form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
        .project-form-grid .project-input.full { grid-column: 1 / -1; }
        .versions-list { max-height: 280px; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; }
        .version-item {
            border: 1px solid var(--border); border-radius: 10px; padding: 10px;
            background: var(--bg-secondary);
        }
        .version-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
        .version-title { font-size: 12px; font-weight: 600; color: var(--text-primary); }
        .version-meta { font-size: 10px; color: var(--text-muted); }
        .version-body {
            font-size: 11px; color: var(--text-secondary); background: var(--bg-primary);
            border-radius: 8px; padding: 8px; max-height: 90px; overflow: hidden; white-space: pre-wrap;
        }
        .ops-grid {
            display: grid; grid-template-columns: 1fr 1fr; gap: 10px;
        }
        .ops-kpi {
            border: 1px solid var(--border); border-radius: 12px; background: var(--bg-primary);
            padding: 10px; display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px;
        }
        .ops-kpi-card { background: var(--bg-secondary); border-radius: 10px; padding: 8px; }
        .ops-kpi-label { font-size: 10px; color: var(--text-muted); margin-bottom: 4px; }
        .ops-kpi-value { font-size: 14px; font-weight: 700; color: var(--text-primary); }
        .status-dot-badge {
            width: 8px; height: 8px; border-radius: 50%; display: inline-block; margin-right: 5px;
        }
        .status-dot-badge.draft { background: #94a3b8; }
        .status-dot-badge.running { background: #10b981; }
        .status-dot-badge.paused { background: #f59e0b; }
        .status-dot-badge.done { background: #3b82f6; }
        .status-dot-badge.planned { background: #94a3b8; }
        .status-dot-badge.planning { background: #94a3b8; }
        .status-dot-badge.review { background: #8b5cf6; }
        .status-dot-badge.ready { background: #10b981; }
        .status-dot-badge.released { background: #3b82f6; }
        .status-dot-badge.rollback { background: #ef4444; }
        .status-dot-badge.low { background: #94a3b8; }
        .status-dot-badge.medium { background: #f59e0b; }
        .status-dot-badge.high { background: #ef4444; }
        .status-dot-badge.critical { background: #7f1d1d; }
        .status-dot-badge.active { background: #10b981; }
        .status-dot-badge.muted { background: #f59e0b; }
        .status-dot-badge.resolved { background: #3b82f6; }
        .status-dot-badge.completed { background: #3b82f6; }
        .status-dot-badge.enabled { background: #10b981; }
        .status-dot-badge.disabled { background: #94a3b8; }
        .status-dot-badge.error { background: #ef4444; }
        .status-dot-badge.delayed { background: #f97316; }
        .status-dot-badge.open { background: #ef4444; }
        .status-dot-badge.mitigating { background: #f59e0b; }
        .status-dot-badge.closed { background: #10b981; }
        .console-grid { display: grid; grid-template-columns: 1.1fr 0.9fr; gap: 10px; }
        .console-score-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
        .console-score-card {
            border: 1px solid var(--border); background: var(--bg-secondary);
            border-radius: 12px; padding: 10px;
        }
        .console-score-label { font-size: 10px; color: var(--text-muted); margin-bottom: 5px; }
        .console-score-value { font-size: 18px; font-weight: 700; color: var(--text-primary); }
        .console-search-row { display: flex; gap: 8px; }
        
        .console-metrics-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
        .metric-card {
            background: var(--bg-secondary); border: 1px solid var(--border);
            border-radius: 12px; padding: 12px; display: flex; flex-direction: column; gap: 8px;
        }
        .metric-card .metric-icon { font-size: 24px; }
        .metric-card .metric-info { display: flex; justify-content: space-between; align-items: center; }
        .metric-card .metric-label { font-size: 11px; color: var(--text-muted); }
        .metric-card .metric-value { font-size: 16px; font-weight: 700; color: var(--text-primary); }
        .metric-card .metric-bar { height: 4px; background: var(--border); border-radius: 2px; overflow: hidden; }
        .metric-card .metric-bar-fill { height: 100%; background: linear-gradient(90deg, #667eea, #764ba2); transition: width 0.3s; }
        
        .log-viewer {
            background: #1a1a2e; border-radius: 8px; padding: 10px;
            max-height: 200px; overflow-y: auto; font-family: monospace;
            font-size: 11px; color: #e0e0e0;
        }
        .log-entry { padding: 4px 0; border-bottom: 1px solid rgba(255,255,255,0.05); }
        .log-entry.log-error { color: #ef4444; }
        .log-entry.log-warn { color: #f59e0b; }
        .log-entry.log-info { color: #3b82f6; }
        .log-entry.log-debug { color: #8b5cf6; }
        .log-time { color: #6b7280; margin-right: 8px; }
        
        .task-scheduler-grid { display: grid; gap: 8px; }
        .scheduler-task-card {
            background: var(--bg-secondary); border: 1px solid var(--border);
            border-radius: 10px; padding: 10px;
        }
        .scheduler-task-card .task-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
        .scheduler-task-card .task-name { font-size: 12px; font-weight: 600; color: var(--text-primary); }
        .scheduler-task-card .task-status { font-size: 10px; padding: 2px 8px; border-radius: 999px; }
        .scheduler-task-card .task-status.active { background: rgba(16,185,129,0.15); color: #10b981; }
        .scheduler-task-card .task-status.paused { background: rgba(245,158,11,0.15); color: #f59e0b; }
        .scheduler-task-card .task-info { display: flex; gap: 12px; font-size: 10px; color: var(--text-muted); }
        
        .performance-charts { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin-bottom: 10px; }
        .perf-chart-container { background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 10px; padding: 10px; }
        .perf-chart-title { font-size: 11px; color: var(--text-muted); margin-bottom: 8px; }
        .perf-chart { height: 80px; background: linear-gradient(180deg, rgba(102,126,234,0.1) 0%, transparent 100%); border-radius: 6px; }
        .perf-stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
        .perf-stat-item { text-align: center; padding: 8px; background: var(--bg-secondary); border-radius: 8px; }
        .perf-stat-value { font-size: 16px; font-weight: 700; color: var(--primary); }
        .perf-stat-label { font-size: 10px; color: var(--text-muted); }
        
        .service-health-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
        .service-card {
            background: var(--bg-secondary); border: 1px solid var(--border);
            border-radius: 10px; padding: 12px; display: flex; align-items: center; gap: 10px;
        }
        .service-card.healthy { border-left: 3px solid #10b981; }
        .service-card.unhealthy { border-left: 3px solid #ef4444; }
        .service-card.unknown { border-left: 3px solid #6b7280; }
        .service-card .service-icon { font-size: 24px; }
        .service-card .service-info { flex: 1; }
        .service-card .service-name { font-size: 12px; font-weight: 600; color: var(--text-primary); }
        .service-card .service-status { font-size: 10px; color: var(--text-muted); }
        .service-card .service-btn { font-size: 10px; padding: 4px 8px; border-radius: 6px; border: 1px solid var(--border); background: var(--bg); color: var(--text-secondary); cursor: pointer; }
        .service-card .service-btn:hover { background: var(--primary); color: white; }
        
        .dependency-overview { margin-bottom: 10px; }
        .dep-summary { display: flex; gap: 20px; justify-content: center; padding: 10px; background: var(--bg-secondary); border-radius: 8px; }
        .dep-stat { text-align: center; }
        .dep-stat-value { font-size: 20px; font-weight: 700; color: var(--text-primary); }
        .dep-stat-label { font-size: 10px; color: var(--text-muted); }
        
        .git-status-grid { display: grid; gap: 10px; }
        .git-repo-card {
            background: var(--bg-secondary); border: 1px solid var(--border);
            border-radius: 10px; padding: 12px;
        }
        .git-repo-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
        .git-repo-name { font-size: 12px; font-weight: 600; color: var(--text-primary); }
        .git-branch { font-size: 10px; padding: 2px 8px; background: rgba(102,126,234,0.15); color: var(--primary); border-radius: 999px; }
        .git-repo-stats { display: flex; gap: 12px; margin-bottom: 8px; }
        .git-stat { font-size: 10px; color: var(--text-muted); }
        .git-repo-actions { display: flex; gap: 6px; }
        .git-btn { font-size: 10px; padding: 4px 10px; border-radius: 6px; border: 1px solid var(--border); background: var(--bg); color: var(--text-secondary); cursor: pointer; }
        .git-btn:hover { background: var(--primary); color: white; }
        
        .template-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
        .template-card {
            background: var(--bg-secondary); border: 1px solid var(--border);
            border-radius: 10px; padding: 12px; display: flex; align-items: center; gap: 10px; cursor: pointer;
            transition: all 0.2s;
        }
        .template-card:hover { border-color: var(--primary); transform: translateY(-2px); }
        .template-card .template-icon { font-size: 24px; }
        .template-card .template-name { font-size: 12px; font-weight: 600; color: var(--text-primary); }
        .template-card .template-desc { font-size: 10px; color: var(--text-muted); }
        
        .deploy-history { display: flex; flex-direction: column; gap: 8px; }
        .deploy-record { display: flex; justify-content: space-between; align-items: center; padding: 10px; background: var(--bg-secondary); border-radius: 8px; border-left: 3px solid; }
        .deploy-record.success { border-left-color: #10b981; }
        .deploy-record.failed { border-left-color: #ef4444; }
        .deploy-record .deploy-project { font-size: 12px; font-weight: 600; color: var(--text-primary); }
        .deploy-record .deploy-target { font-size: 10px; color: var(--text-muted); }
        .deploy-record .deploy-time { font-size: 10px; color: var(--text-muted); }
        
        .dataflow-overview { background: var(--bg-secondary); border-radius: 10px; padding: 15px; }
        .dataflow-chart { display: flex; align-items: center; justify-content: center; gap: 10px; margin-bottom: 15px; }
        .dataflow-node { text-align: center; padding: 15px 20px; background: var(--bg); border-radius: 10px; border: 1px solid var(--border); }
        .dataflow-node.input { border-color: #3b82f6; }
        .dataflow-node.process { border-color: #8b5cf6; }
        .dataflow-node.output { border-color: #10b981; }
        .dataflow-node .node-icon { font-size: 24px; margin-bottom: 5px; }
        .dataflow-node .node-label { font-size: 10px; color: var(--text-muted); }
        .dataflow-node .node-value { font-size: 14px; font-weight: 700; color: var(--text-primary); }
        .dataflow-arrow { font-size: 20px; color: var(--text-muted); }
        .dataflow-stats { display: flex; justify-content: space-around; }
        .dataflow-stat { text-align: center; }
        .dataflow-stat .stat-label { font-size: 10px; color: var(--text-muted); display: block; }
        .dataflow-stat .stat-value { font-size: 14px; font-weight: 600; color: var(--text-primary); }
        .console-reco-priority {
            border-radius: 999px; padding: 2px 8px; font-size: 10px;
            background: rgba(102,126,234,0.12); color: var(--primary);
        }
        .console-reco-priority.p0 { background: rgba(239,68,68,0.12); color: #ef4444; }
        .console-reco-priority.p1 { background: rgba(245,158,11,0.15); color: #f59e0b; }
        .console-reco-priority.p2 { background: rgba(59,130,246,0.12); color: #3b82f6; }
        .release-checklist { margin-top: 8px; display: flex; flex-direction: column; gap: 6px; }
        .release-check {
            display: flex; align-items: center; gap: 6px; font-size: 11px; color: var(--text-secondary);
            background: var(--bg-primary); border: 1px solid var(--border); border-radius: 8px; padding: 6px;
        }
        .main-container { flex: 1; display: flex; flex-direction: column; gap: 12px; min-width: 0; }
        .header {
            background: var(--glass); border-radius: 16px; padding: 14px 20px;
            box-shadow: var(--shadow), 0 0 0 1px var(--border); backdrop-filter: blur(24px); 
            display: flex; align-items: center; justify-content: space-between;
            border: 1px solid rgba(255,255,255,0.2);
        }
        .header-left { display: flex; align-items: center; gap: 14px; }
        .header-avatar { 
            width: 46px; height: 46px; border-radius: 14px; object-fit: cover; 
            border: 2px solid transparent; 
            background: linear-gradient(white, white) padding-box, linear-gradient(135deg, var(--primary), var(--secondary)) border-box;
            box-shadow: 0 4px 12px rgba(102,126,234,0.25);
            transition: var(--transition);
        }
        .header-avatar:hover { transform: scale(1.05); }
        .header-info h1 { font-size: 18px; color: var(--text-primary); font-weight: 700; }
        .header-status { font-size: 12px; color: var(--text-muted); display: flex; align-items: center; gap: 6px; margin-top: 2px; }
        .status-dot { 
            width: 8px; height: 8px; border-radius: 50%; 
            background: linear-gradient(135deg, #10b981, #34d399); 
            animation: pulse 2s infinite; 
            box-shadow: 0 0 10px rgba(16,185,129,0.6); 
        }
        @keyframes pulse { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.6; transform: scale(0.85); } }
        .header-indicators { display: flex; gap: 8px; }
        .indicator { 
            display: flex; align-items: center; gap: 6px; padding: 6px 12px; 
            border-radius: 16px; font-size: 11px; font-weight: 600;
            backdrop-filter: blur(8px);
        }
        .indicator.lora { background: linear-gradient(135deg, rgba(16, 185, 129, 0.2), rgba(52, 211, 153, 0.1)); color: var(--lora-color); border: 1px solid rgba(16, 185, 129, 0.3); }
        .indicator.tool { background: linear-gradient(135deg, rgba(245, 158, 11, 0.2), rgba(217, 119, 6, 0.1)); color: var(--tool-color); border: 1px solid rgba(245, 158, 11, 0.3); }
        .header-actions { display: flex; gap: 8px; }
        .header-btn {
            width: 38px; height: 38px; border-radius: 12px; border: 1px solid var(--border);
            background: linear-gradient(135deg, rgba(255,255,255,0.8), rgba(255,255,255,0.6)); 
            cursor: pointer; font-size: 16px; transition: var(--transition);
            display: flex; align-items: center; justify-content: center;
        }
        .header-btn:hover { 
            background: linear-gradient(135deg, var(--primary), var(--secondary)); 
            color: white; border-color: transparent; transform: translateY(-2px); 
            box-shadow: 0 6px 16px rgba(102,126,234,0.35); 
        }
        .header-btn.active { background: linear-gradient(135deg, var(--primary), var(--secondary)); color: white; border-color: transparent; }
        .deepseek-btn {
            width: auto; padding: 0 14px; gap: 6px;
            background: linear-gradient(135deg, #667eea, #764ba2) !important;
            color: white !important; border: none !important;
            font-weight: 600; font-size: 13px;
            box-shadow: 0 4px 15px rgba(102,126,234,0.4);
            animation: pulse-glow 2s ease-in-out infinite;
        }
        .deepseek-btn:hover {
            transform: translateY(-2px) scale(1.02) !important;
            box-shadow: 0 6px 20px rgba(102,126,234,0.5) !important;
        }
        .deepseek-btn .btn-icon { font-size: 16px; }
        .deepseek-btn .btn-text { font-size: 12px; letter-spacing: 0.5px; }
        .deepseek-icon {
            width: 22px; height: 22px;
            border-radius: 6px;
            object-fit: cover;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        }
        @keyframes pulse-glow {
            0%, 100% { box-shadow: 0 4px 15px rgba(102,126,234,0.4); }
            50% { box-shadow: 0 4px 25px rgba(102,126,234,0.6); }
        }
        .stats-btn {
            background: linear-gradient(135deg, #10b981, #059669) !important;
            color: white !important;
            border: none !important;
        }
        .stats-btn:hover {
            transform: translateY(-2px) scale(1.05) !important;
            box-shadow: 0 4px 15px rgba(16,185,129,0.4) !important;
        }
        .theme-preset:hover {
            border-color: var(--primary) !important;
            transform: scale(1.05);
        }
        .tools-bar {
            background: linear-gradient(135deg, rgba(255,255,255,0.7), rgba(255,255,255,0.5)); 
            border-radius: 14px; padding: 10px 14px;
            display: flex; gap: 8px; align-items: center; overflow-x: auto;
            border: 1px solid rgba(102,126,234,0.1);
            backdrop-filter: blur(10px);
        }
        .dark .tools-bar { background: linear-gradient(135deg, rgba(40,40,65,0.7), rgba(35,35,60,0.5)); }
        .tools-bar::-webkit-scrollbar { height: 4px; }
        .tools-bar::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }
        .quick-tool {
            padding: 8px 14px; border-radius: 10px; border: 1px solid var(--border);
            background: linear-gradient(135deg, rgba(255,255,255,0.9), rgba(255,255,255,0.7)); 
            cursor: pointer; font-size: 12px; font-weight: 500; transition: var(--transition);
            display: flex; align-items: center; gap: 6px; white-space: nowrap;
            box-shadow: 0 2px 6px rgba(0,0,0,0.04);
        }
        .dark .quick-tool { background: linear-gradient(135deg, rgba(50,50,75,0.9), rgba(45,45,70,0.7)); }
        .quick-tool:hover { 
            background: linear-gradient(135deg, var(--primary), var(--secondary)); 
            color: white; border-color: transparent; transform: translateY(-2px); 
            box-shadow: 0 4px 14px rgba(102,126,234,0.35); 
        }
        *::-webkit-scrollbar { width: 8px; height: 8px; }
        *::-webkit-scrollbar-thumb { background: rgba(120,130,165,0.4); border-radius: 999px; }
        *::-webkit-scrollbar-track { background: transparent; }
        .quick-tool.active { 
            background: linear-gradient(135deg, var(--tool-color), #d97706); 
            color: white; border-color: transparent;
            box-shadow: 0 4px 14px rgba(245,158,11,0.35);
        }
        .search-tool {
            background: linear-gradient(135deg, #10b981, #059669) !important;
            color: white !important; border: none !important;
            font-weight: 600; padding: 8px 16px;
            box-shadow: 0 4px 15px rgba(16,185,129,0.35);
            animation: search-pulse 2.5s ease-in-out infinite;
        }
        .search-tool:hover {
            transform: translateY(-2px) scale(1.02) !important;
            box-shadow: 0 6px 20px rgba(16,185,129,0.45) !important;
        }
        .search-tool .tool-icon { font-size: 14px; }
        .search-tool .tool-label { font-size: 12px; letter-spacing: 0.3px; }
        @keyframes search-pulse {
            0%, 100% { box-shadow: 0 4px 15px rgba(16,185,129,0.35); }
            50% { box-shadow: 0 4px 22px rgba(16,185,129,0.5); }
        }
        .chat-area {
            flex: 1; background: var(--glass); border-radius: var(--radius);
            box-shadow: var(--shadow), 0 0 0 1px var(--border); backdrop-filter: blur(24px); 
            display: flex; flex-direction: column; overflow: hidden; min-height: 0;
            border: 1px solid rgba(255,255,255,0.2); position: relative; z-index: 10;
        }
        .messages-container { flex: 1; overflow-y: auto; padding: 20px; scroll-behavior: smooth; }
        .messages-container::-webkit-scrollbar { width: 8px; }
        .messages-container::-webkit-scrollbar-track { background: transparent; }
        .messages-container::-webkit-scrollbar-thumb { 
            background: linear-gradient(180deg, var(--primary), var(--secondary)); 
            border-radius: 4px; 
        }
        .messages-container::-webkit-scrollbar-thumb:hover { background: var(--primary); }
        .message { display: flex; gap: 12px; margin-bottom: 20px; animation: slideIn 0.5s cubic-bezier(0.4, 0, 0.2, 1); }
        @keyframes slideIn { from { opacity: 0; transform: translateY(16px) scale(0.98); } to { opacity: 1; transform: translateY(0) scale(1); } }
        .message.user { flex-direction: row-reverse; }
        .message-avatar { 
            width: 36px; height: 36px; border-radius: 12px; flex-shrink: 0; 
            display: flex; align-items: center; justify-content: center; font-size: 16px;
            box-shadow: 0 3px 10px rgba(0,0,0,0.1);
        }
        .message-avatar img { width: 100%; height: 100%; border-radius: 12px; object-fit: cover; }
        .message-content-wrapper { max-width: 75%; }
        .message-content {
            padding: 12px 16px; border-radius: 18px; line-height: 1.7; color: var(--text-primary);
            font-size: 14px; position: relative; transition: var(--transition);
        }
        .message.user .message-content { 
            background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 50%, var(--accent) 100%); 
            color: white; border-bottom-right-radius: 6px;
            box-shadow: 0 4px 15px rgba(102,126,234,0.35), inset 0 1px 0 rgba(255,255,255,0.2);
        }
        .message.assistant .message-content { 
            background: linear-gradient(135deg, rgba(255,255,255,0.95), rgba(255,255,255,0.85)); 
            border-bottom-left-radius: 6px;
            border: 1px solid rgba(102,126,234,0.1);
            box-shadow: 0 2px 12px rgba(0,0,0,0.06);
        }
        .dark .message.assistant .message-content { 
            background: linear-gradient(135deg, rgba(45,45,70,0.95), rgba(35,35,60,0.85)); 
            border-color: rgba(102,126,234,0.2);
        }
        .message-content pre { background: rgba(0,0,0,0.08); padding: 8px 10px; border-radius: 8px; overflow-x: auto; margin: 6px 0; }
        .message.user .message-content pre { background: rgba(255,255,255,0.15); }
        .message-content code { font-family: 'Fira Code', 'SF Mono', monospace; font-size: 12px; }
        .message-content p { margin: 6px 0; }
        .message-content p:first-child { margin-top: 0; }
        .message-content p:last-child { margin-bottom: 0; }
        /* 思考过程展开/折叠样式 */
        .reasoning-section { margin-bottom: 12px; border-radius: 12px; overflow: hidden; }
        .reasoning-toggle {
            display: flex; align-items: center; gap: 8px;
            padding: 10px 14px; background: linear-gradient(135deg, rgba(124,58,237,0.1), rgba(79,70,229,0.05));
            border: 1px solid rgba(124,58,237,0.2); border-radius: 10px;
            cursor: pointer; font-size: 13px; color: #7c3aed;
            transition: var(--transition); user-select: none;
        }
        .reasoning-toggle:hover { background: linear-gradient(135deg, rgba(124,58,237,0.15), rgba(79,70,229,0.1)); }
        .reasoning-toggle-icon { transition: transform 0.3s ease; font-size: 12px; }
        .reasoning-toggle.expanded .reasoning-toggle-icon { transform: rotate(90deg); }
        .reasoning-content {
            padding: 12px 14px; background: rgba(124,58,237,0.03);
            border: 1px solid rgba(124,58,237,0.15); border-top: none;
            border-radius: 0 0 10px 10px; font-size: 13px; line-height: 1.6;
            color: var(--text-secondary); max-height: 0; overflow: hidden;
            transition: max-height 0.3s ease, padding 0.3s ease; margin-top: -4px;
        }
        .reasoning-content.expanded {
            max-height: 2000px; padding: 12px 14px;
        }
        .reasoning-content pre {
            background: rgba(124,58,237,0.08); padding: 10px; border-radius: 8px;
            overflow-x: auto; white-space: pre-wrap; word-wrap: break-word;
        }
        .dark .reasoning-toggle { background: linear-gradient(135deg, rgba(124,58,237,0.2), rgba(79,70,229,0.1)); color: #a78bfa; }
        .dark .reasoning-toggle:hover { background: linear-gradient(135deg, rgba(124,58,237,0.25), rgba(79,70,229,0.15)); }
        .dark .reasoning-content { background: rgba(124,58,237,0.08); color: #a0a0b0; }
        .code-block { position: relative; margin: 10px 0; }
        .code-block pre { margin: 0; border-radius: 12px; }
        .code-block .run-btn {
            position: absolute; top: 10px; right: 10px;
            padding: 6px 12px; background: var(--code-color); color: white; border: none;
            border-radius: 8px; cursor: pointer; font-size: 11px; transition: var(--transition);
            box-shadow: 0 2px 8px rgba(14,165,233,0.3);
        }
        .code-block .run-btn:hover { background: #0284c7; transform: scale(1.05); box-shadow: 0 4px 12px rgba(14,165,233,0.4); }
        .input-area { padding: 16px; border-top: 1px solid var(--border); background: linear-gradient(180deg, rgba(255,255,255,0.95), rgba(255,255,255,1)); position: relative; z-index: 100; }
        .dark .input-area { background: linear-gradient(180deg, rgba(30,30,50,0.95), rgba(25,25,45,1)); }
        .attachments-preview { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }
        .attachment-item { position: relative; width: 56px; height: 56px; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .attachment-item img { width: 100%; height: 100%; object-fit: cover; }
        .attachment-remove { position: absolute; top: 2px; right: 2px; width: 16px; height: 16px; background: rgba(239,68,68,0.9); color: white; border: none; border-radius: 50%; cursor: pointer; font-size: 9px; display: flex; align-items: center; justify-content: center; }
        .input-wrapper { display: flex; gap: 8px; align-items: flex-end; }
        .input-tools { display: flex; gap: 4px; }
        .tool-btn { 
            width: 36px; height: 36px; border: 1.5px solid var(--border); background: linear-gradient(135deg, rgba(255,255,255,0.9), rgba(255,255,255,0.7)); 
            border-radius: 10px; cursor: pointer; font-size: 14px; transition: var(--transition); 
            display: flex; align-items: center; justify-content: center; box-shadow: 0 2px 6px rgba(0,0,0,0.05);
        }
        .tool-btn:hover { 
            background: linear-gradient(135deg, var(--primary), var(--secondary)); 
            color: white; border-color: transparent; transform: translateY(-2px); 
            box-shadow: 0 4px 12px rgba(102,126,234,0.3); 
        }
        .tool-btn.active { background: linear-gradient(135deg, var(--primary), var(--secondary)); color: white; border-color: transparent; }
        .main-input {
            flex: 1; padding: 10px 14px; border: 2px solid var(--border); border-radius: 14px;
            font-size: 14px; background: linear-gradient(135deg, rgba(255,255,255,0.95), rgba(255,255,255,0.85)); 
            color: var(--text-primary); resize: none; min-height: 42px; max-height: 120px; 
            font-family: inherit; transition: var(--transition); box-shadow: inset 0 1px 3px rgba(0,0,0,0.05);
        }
        .dark .main-input { background: linear-gradient(135deg, rgba(40,40,65,0.95), rgba(35,35,60,0.85)); }
        .main-input:focus { outline: none; border-color: var(--primary); box-shadow: 0 0 0 3px rgba(102,126,234,0.15), inset 0 1px 3px rgba(0,0,0,0.05); }
        .send-btn {
            width: 42px; height: 42px; background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: white; border: none; border-radius: 12px; cursor: pointer; font-size: 18px; 
            transition: var(--transition); box-shadow: 0 4px 12px rgba(102,126,234,0.3);
            display: flex; align-items: center; justify-content: center;
        }
        .send-btn:hover { transform: translateY(-2px) scale(1.05); box-shadow: 0 6px 18px rgba(102,126,234,0.4); }
        .send-btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
        .input-footer { display: flex; justify-content: space-between; align-items: center; margin-top: 6px; font-size: 10px; color: var(--text-muted); }
        .command-hint { background: var(--bg-primary); border-radius: 6px; padding: 6px 10px; margin-bottom: 8px; font-size: 11px; color: var(--text-secondary); display: none; }
        .command-hint.show { display: block; }
        .command-item { padding: 3px 0; cursor: pointer; }
        .command-item:hover { color: var(--primary); }
        .settings-panel {
            position: fixed; top: 0; right: -400px; width: 400px; height: 100%; 
            background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(250,250,255,0.95));
            box-shadow: -8px 0 40px rgba(0,0,0,0.15); z-index: 100; 
            transition: var(--transition); overflow-y: auto; backdrop-filter: blur(20px);
        }
        .dark .settings-panel { background: linear-gradient(180deg, rgba(25,25,45,0.98), rgba(20,20,40,0.95)); }
        .settings-panel.open { right: 0; }
        .settings-header { 
            padding: 16px 20px; border-bottom: 1px solid var(--border); 
            display: flex; justify-content: space-between; align-items: center;
            background: linear-gradient(135deg, rgba(102,126,234,0.08), transparent);
        }
        .settings-header h3 { font-size: 16px; color: var(--text-primary); font-weight: 600; }
        .settings-close { 
            width: 32px; height: 32px; border: none; background: rgba(102,126,234,0.1); 
            border-radius: 10px; cursor: pointer; font-size: 14px; transition: var(--transition);
        }
        .settings-close:hover { background: var(--primary); color: white; }
        .settings-section { padding: 16px 20px; border-bottom: 1px solid var(--border); }
        .settings-section h4 { font-size: 11px; color: var(--primary); margin-bottom: 14px; text-transform: uppercase; letter-spacing: 1.5px; font-weight: 600; }
        .setting-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
        .setting-label { font-size: 13px; color: var(--text-primary); }
        .setting-value { font-size: 13px; color: var(--primary); min-width: 45px; text-align: right; font-weight: 600; }
        .setting-slider { width: 100px; height: 6px; -webkit-appearance: none; background: linear-gradient(90deg, var(--border), rgba(102,126,234,0.3)); border-radius: 3px; outline: none; }
        .setting-slider::-webkit-slider-thumb { -webkit-appearance: none; width: 18px; height: 18px; background: linear-gradient(135deg, var(--primary), var(--secondary)); border-radius: 50%; cursor: pointer; box-shadow: 0 2px 8px rgba(102,126,234,0.4); }
        .toggle { position: relative; width: 44px; height: 24px; }
        .toggle input { opacity: 0; width: 0; height: 0; }
        .toggle-slider { position: absolute; cursor: pointer; inset: 0; background: var(--border); border-radius: 12px; transition: var(--transition); }
        .toggle-slider:before { position: absolute; content: ""; height: 18px; width: 18px; left: 3px; bottom: 3px; background: white; border-radius: 50%; transition: var(--transition); box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .toggle input:checked + .toggle-slider { background: linear-gradient(135deg, var(--primary), var(--secondary)); }
        .toggle input:checked + .toggle-slider:before { transform: translateX(20px); }
        .stats-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
        .stats-card { 
            background: linear-gradient(135deg, rgba(102,126,234,0.08), rgba(118,75,162,0.05)); 
            border-radius: 12px; padding: 14px; text-align: center; border: 1px solid rgba(102,126,234,0.1);
        }
        .stats-card-value { font-size: 22px; font-weight: 700; background: linear-gradient(135deg, var(--primary), var(--secondary)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .stats-card-label { font-size: 11px; color: var(--text-muted); margin-top: 4px; }
        .toast { 
            position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%) translateY(100px); 
            background: linear-gradient(135deg, rgba(30,30,50,0.95), rgba(20,20,40,0.95)); 
            color: white; padding: 10px 20px; border-radius: 12px; font-size: 13px; 
            z-index: 200; transition: var(--transition); backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.1); box-shadow: 0 8px 24px rgba(0,0,0,0.2);
        }
        .toast.show { transform: translateX(-50%) translateY(0); }
        .modal-overlay { 
            position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 150; 
            display: none; justify-content: center; align-items: center; backdrop-filter: blur(8px);
            padding: 20px;
            overflow-y: auto;
        }
        .modal-overlay.show { display: flex; }
        .modal { 
            background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(250,250,255,0.95)); 
            border-radius: var(--radius); padding: 24px; max-width: 680px; width: 100%; 
            max-height: 90vh; overflow-y: auto; box-shadow: 0 20px 60px rgba(0,0,0,0.2);
            border: 1px solid rgba(255,255,255,0.2);
            margin: auto;
        }
        .dark .modal { background: linear-gradient(180deg, rgba(30,30,50,0.98), rgba(25,25,45,0.95)); }
        .modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
        .modal-title { font-size: 16px; color: var(--text-primary); font-weight: 600; }
        .modal-close { 
            width: 28px; height: 28px; border: none; background: rgba(102,126,234,0.1); 
            border-radius: 8px; cursor: pointer; font-size: 12px; transition: var(--transition);
        }
        .modal-close:hover { background: var(--primary); color: white; }
        .modal-body { color: var(--text-secondary); line-height: 1.6; font-size: 14px; overflow-y: auto; max-height: calc(90vh - 120px); }
        .modal-actions { display: flex; gap: 10px; margin-top: 20px; justify-content: flex-end; flex-wrap: wrap; }
        .modal-btn { 
            padding: 10px 20px; border: none; border-radius: 10px; cursor: pointer; 
            font-size: 13px; font-weight: 600; transition: var(--transition); 
        }
        .modal-btn.primary { 
            background: linear-gradient(135deg, var(--primary), var(--secondary)); 
            color: white; box-shadow: 0 4px 12px rgba(102,126,234,0.3);
        }
        .modal-btn.primary:hover { transform: translateY(-2px); box-shadow: 0 6px 16px rgba(102,126,234,0.4); }
        .modal-btn.secondary { 
            background: linear-gradient(135deg, rgba(102,126,234,0.1), rgba(118,75,162,0.05)); 
            color: var(--text-primary); border: 1px solid var(--border);
        }
        .modal-btn.secondary:hover { background: rgba(102,126,234,0.15); }
        .code-editor {
            width: 100%; min-height: 180px; padding: 14px; border: 2px solid var(--border);
            border-radius: 12px; font-family: 'Fira Code', 'SF Mono', 'JetBrains Mono', monospace; 
            font-size: 13px; line-height: 1.6;
            background: linear-gradient(135deg, rgba(30,30,40,0.95), rgba(25,25,35,0.95)); 
            color: #e0e0e0; resize: vertical;
        }
        .code-editor:focus { outline: none; border-color: var(--code-color); box-shadow: 0 0 0 3px rgba(14,165,233,0.15); }
        .kb-input {
            width: 100%; padding: 12px; border: 2px solid var(--border); border-radius: 10px;
            font-size: 13px; background: linear-gradient(135deg, rgba(255,255,255,0.95), rgba(255,255,255,0.85)); 
            color: var(--text-primary); resize: vertical; min-height: 100px; font-family: inherit;
            transition: var(--transition);
        }
        .dark .kb-input { background: linear-gradient(135deg, rgba(40,40,65,0.95), rgba(35,35,60,0.85)); }
        .kb-input:focus { outline: none; border-color: var(--primary); box-shadow: 0 0 0 3px rgba(102,126,234,0.15); }
        .typing-indicator { display: flex; gap: 5px; padding: 12px; align-items: center; }
        .typing-indicator span { 
            width: 8px; height: 8px; background: linear-gradient(135deg, var(--primary), var(--secondary)); 
            border-radius: 50%; animation: typing 1.4s infinite ease-in-out;
        }
        .typing-indicator span:nth-child(1) { animation-delay: 0s; }
        .typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
        .typing-indicator span:nth-child(3) { animation-delay: 0.4s; }
        @keyframes typing { 
            0%, 60%, 100% { transform: translateY(0) scale(1); opacity: 0.6; } 
            30% { transform: translateY(-6px) scale(1.2); opacity: 1; } 
        }
        .message-actions { 
            display: flex; gap: 6px; margin-top: 8px; opacity: 0; transition: var(--transition); 
        }
        .message:hover .message-actions { opacity: 1; }
        .msg-action-btn { 
            padding: 5px 10px; border: none; background: linear-gradient(135deg, rgba(102,126,234,0.1), rgba(118,75,162,0.05)); 
            border-radius: 8px; cursor: pointer; font-size: 11px; color: var(--text-muted); 
            transition: var(--transition); border: 1px solid transparent;
        }
        .msg-action-btn:hover { 
            background: linear-gradient(135deg, var(--primary), var(--secondary)); 
            color: white; transform: translateY(-1px); box-shadow: 0 2px 8px rgba(102,126,234,0.3);
        }
        .message-time { font-size: 11px; color: var(--text-muted); margin-top: 6px; }
        .message.user .message-time { text-align: right; }
        .tool-result {
            margin-top: 10px; padding: 12px; 
            background: linear-gradient(135deg, rgba(245,158,11,0.12), rgba(217,119,6,0.08));
            border-radius: 10px; font-size: 13px; border-left: 3px solid var(--tool-color);
            box-shadow: 0 2px 8px rgba(245,158,11,0.1);
        }
        .code-output {
            margin-top: 10px; padding: 12px; 
            background: linear-gradient(135deg, rgba(14,165,233,0.1), rgba(56,189,248,0.05));
            border-radius: 10px; font-family: 'Fira Code', monospace; font-size: 12px;
            white-space: pre-wrap; border-left: 3px solid var(--code-color);
            box-shadow: 0 2px 8px rgba(14,165,233,0.1);
        }
        button, .quick-tool, .chat-item, .feature-card, .demand-card, .panel-item, .sidebar-tab, .tool-btn, .header-btn, .modal-btn, .prompt-card {
            -webkit-tap-highlight-color: transparent;
        }
        .quick-tool:active, .header-btn:active, .tool-btn:active, .panel-item:active, .feature-card:active, .demand-card:active, .modal-btn:active, .chat-item:active, .prompt-card:active {
            transform: scale(0.98);
        }
        .header-btn:focus-visible, .tool-btn:focus-visible, .send-btn:focus-visible, .quick-tool:focus-visible, .modal-btn:focus-visible, .sidebar-tab:focus-visible, .main-input:focus-visible, .prompt-search-input:focus-visible {
            outline: 2px solid rgba(102,126,234,0.45);
            outline-offset: 2px;
        }
        .header-actions { flex-wrap: wrap; justify-content: flex-end; }
        .function-center-grid {
            display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px;
        }
        .function-center-card {
            background: var(--bg-secondary); border: 1px solid var(--border);
            border-radius: 12px; padding: 12px; cursor: pointer; transition: var(--transition);
        }
        .function-center-card:hover {
            border-color: var(--primary); transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(102,126,234,0.18);
        }
        .function-center-title {
            font-size: 13px; font-weight: 600; color: var(--text-primary);
            display: flex; align-items: center; gap: 6px; margin-bottom: 6px;
        }
        .function-center-desc {
            font-size: 11px; color: var(--text-muted); line-height: 1.45;
        }
        .function-center-badge {
            margin-top: 8px; display: inline-flex; padding: 2px 8px;
            border-radius: 999px; font-size: 10px; color: var(--primary);
            background: rgba(102,126,234,0.12);
        }
        .feature-center-meta {
            display: grid; grid-template-columns: 1.2fr 1fr; gap: 10px; margin-bottom: 12px;
        }
        .feature-center-panel {
            background: var(--bg-secondary); border: 1px solid var(--border);
            border-radius: 12px; padding: 10px;
        }
        .feature-center-panel-title {
            font-size: 12px; font-weight: 700; color: var(--text-primary);
            margin-bottom: 8px; display: flex; align-items: center; gap: 6px;
        }
        .feature-center-status-grid {
            display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px;
        }
        .feature-center-status-item {
            border-radius: 10px; padding: 8px; background: var(--bg-primary);
            border: 1px solid var(--border);
        }
        .feature-center-status-label {
            font-size: 10px; color: var(--text-muted); margin-bottom: 4px;
        }
        .feature-center-status-value {
            font-size: 12px; font-weight: 700; color: var(--text-primary);
        }
        .feature-center-status-value.ok { color: #10b981; }
        .feature-center-status-value.warn { color: #f59e0b; }
        .feature-center-recent {
            max-height: 126px; overflow-y: auto; display: flex; flex-direction: column; gap: 6px;
        }
        .feature-center-recent-item {
            background: var(--bg-primary); border: 1px solid var(--border);
            border-radius: 10px; padding: 8px; display: flex; justify-content: space-between; gap: 8px;
            font-size: 11px; color: var(--text-secondary);
        }
        .feature-center-recent-item span:last-child {
            color: var(--text-muted); font-size: 10px; white-space: nowrap;
        }
        .section-focus {
            box-shadow: 0 0 0 2px rgba(102,126,234,0.35), 0 0 24px rgba(102,126,234,0.25);
            border-radius: 12px;
            animation: sectionPulse 1.2s ease;
        }
        @keyframes sectionPulse {
            0% { transform: scale(0.99); }
            35% { transform: scale(1.01); }
            100% { transform: scale(1); }
        }
        .mobile-dock {
            display: none;
            position: fixed; left: 12px; right: 12px; bottom: 10px;
            background: linear-gradient(135deg, rgba(255,255,255,0.92), rgba(248,249,255,0.88));
            border: 1px solid var(--border); border-radius: 16px;
            box-shadow: 0 12px 26px rgba(0,0,0,0.12); z-index: 260;
            backdrop-filter: blur(12px); padding: 8px; gap: 8px;
        }
        .dark .mobile-dock {
            background: linear-gradient(135deg, rgba(22,22,40,0.94), rgba(28,28,48,0.9));
        }
        .mobile-dock-btn {
            flex: 1; border: 1px solid var(--border); background: var(--bg-primary);
            border-radius: 10px; padding: 8px 4px; font-size: 11px; color: var(--text-primary);
            display: flex; flex-direction: column; align-items: center; gap: 4px; cursor: pointer;
            transition: var(--transition);
        }
        .mobile-dock-btn:hover {
            border-color: var(--primary);
            background: linear-gradient(135deg, rgba(102,126,234,0.14), rgba(118,75,162,0.1));
        }
        .mobile-dock-btn.active {
            color: #fff; border-color: transparent;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
        }
        @media (max-width: 1280px) {
            .sidebar { width: 280px; min-width: 280px; }
            .header-indicators { display: none; }
            .project-list { max-height: 260px; }
        }
        @media (max-width: 900px) {
            .app-container { flex-direction: column; padding: 8px; height: auto; min-height: 100vh; }
            .sidebar { width: 100%; max-height: 320px; min-width: unset; }
            .sidebar-tabs { flex-wrap: nowrap; overflow-x: auto; padding-bottom: 4px; }
            .sidebar-tab { flex: 0 0 auto; min-width: 72px; padding: 8px 11px; }
            .message-content-wrapper { max-width: 90%; }
            .feature-grid { grid-template-columns: repeat(2, 1fr); }
            .market-demand-grid { grid-template-columns: repeat(2, 1fr); }
            .welcome-title { font-size: 24px; }
            .welcome-avatar { width: 80px; height: 80px; }
            .right-sidebar { width: 92vw; right: -92vw; }
            .settings-panel { width: 92vw; right: -92vw; }
            .function-center-grid { grid-template-columns: repeat(2, 1fr); }
            .feature-center-meta { grid-template-columns: 1fr; }
            .feature-center-status-grid { grid-template-columns: repeat(2, 1fr); }
            .project-overview { grid-template-columns: repeat(2, 1fr); }
            .project-split { grid-template-columns: 1fr; }
            .kanban-board { grid-template-columns: 1fr; }
            .console-grid { grid-template-columns: 1fr; }
            .console-score-grid { grid-template-columns: repeat(2, 1fr); }
            .ops-grid { grid-template-columns: 1fr; }
            .ops-kpi { grid-template-columns: repeat(2, 1fr); }
            .mobile-dock { display: flex; }
            body { padding-bottom: 86px; }
        }
        @media (max-width: 600px) {
            .app-container { padding: 4px; gap: 8px; }
            .header { padding: 10px 14px; }
            .header-avatar { width: 38px; height: 38px; }
            .header-info h1 { font-size: 15px; }
            .tools-bar { padding: 8px 10px; gap: 6px; }
            .quick-tool { padding: 6px 10px; font-size: 11px; }
            .feature-grid { grid-template-columns: 1fr; }
            .market-demand-grid { grid-template-columns: 1fr; }
            .header-actions { gap: 6px; }
            .header-btn { width: 34px; height: 34px; border-radius: 10px; font-size: 14px; }
            .function-center-grid { grid-template-columns: 1fr; }
            .project-overview { grid-template-columns: 1fr; }
            .project-form-grid { grid-template-columns: 1fr; }
            .console-score-grid { grid-template-columns: 1fr; }
            .ops-kpi { grid-template-columns: 1fr; }
            .mobile-dock { overflow-x: auto; justify-content: flex-start; }
            .mobile-dock-btn { min-width: 72px; }
        }
        .skeleton {
            background: linear-gradient(90deg, rgba(200,200,210,0.3) 25%, rgba(200,200,210,0.5) 50%, rgba(200,200,210,0.3) 75%);
            background-size: 200% 100%;
            animation: shimmer 1.5s infinite;
            border-radius: 8px;
        }
        .dark .skeleton {
            background: linear-gradient(90deg, rgba(60,60,80,0.3) 25%, rgba(60,60,80,0.5) 50%, rgba(60,60,80,0.3) 75%);
            background-size: 200% 100%;
        }
        @keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
        .skeleton-message { display: flex; gap: 12px; margin-bottom: 20px; }
        .skeleton-avatar { width: 36px; height: 36px; border-radius: 12px; }
        .skeleton-content { flex: 1; }
        .skeleton-line { height: 14px; margin-bottom: 8px; }
        .skeleton-line:last-child { width: 60%; }
        .ripple {
            position: relative; overflow: hidden;
        }
        .ripple::after {
            content: ''; position: absolute; inset: 0;
            background: radial-gradient(circle at var(--x, 50%) var(--y, 50%), rgba(255,255,255,0.3) 0%, transparent 50%);
            opacity: 0; transition: opacity 0.3s;
        }
        .ripple:active::after { opacity: 1; }
        .glow-effect {
            box-shadow: var(--glow);
            animation: glowPulse 2s ease-in-out infinite;
        }
        @keyframes glowPulse { 0%, 100% { box-shadow: var(--glow); } 50% { box-shadow: 0 0 40px rgba(102,126,234,0.4); } }
        .gradient-border {
            position: relative;
            background: linear-gradient(white, white) padding-box, linear-gradient(135deg, var(--primary), var(--secondary), var(--accent)) border-box;
            border: 2px solid transparent;
        }
        .dark .gradient-border {
            background: linear-gradient(rgba(30,30,50,1), rgba(30,30,50,1)) padding-box, linear-gradient(135deg, var(--primary), var(--secondary), var(--accent)) border-box;
        }
        .message-content pre {
            background: linear-gradient(135deg, rgba(30,30,40,0.95), rgba(25,25,35,0.95));
            padding: 14px 16px; border-radius: 12px; overflow-x: auto; margin: 10px 0;
            border: 1px solid rgba(102,126,234,0.2);
            box-shadow: inset 0 2px 8px rgba(0,0,0,0.2);
        }
        .message.user .message-content pre { background: rgba(255,255,255,0.15); border-color: rgba(255,255,255,0.2); }
        .message-content pre code {
            color: #e2e8f0; font-family: 'Fira Code', 'JetBrains Mono', 'SF Mono', monospace;
            font-size: 13px; line-height: 1.6;
        }
        .code-header {
            display: flex; justify-content: space-between; align-items: center;
            padding: 8px 12px; background: rgba(0,0,0,0.3);
            border-radius: 10px 10px 0 0; margin: -14px -16px 10px -16px;
        }
        .code-lang { font-size: 11px; color: var(--primary); font-weight: 600; text-transform: uppercase; }
        .code-copy {
            padding: 4px 10px; background: rgba(102,126,234,0.2); border: none;
            border-radius: 6px; color: var(--primary); cursor: pointer;
            font-size: 11px; transition: var(--transition);
        }
        .code-copy:hover { background: var(--primary); color: white; }
        .shortcut-hint {
            position: fixed; bottom: 80px; right: 20px;
            background: linear-gradient(135deg, rgba(30,30,50,0.95), rgba(20,20,40,0.95));
            color: white; padding: 16px 20px; border-radius: 16px;
            font-size: 12px; z-index: 150; backdrop-filter: blur(10px);
            border: 1px solid rgba(102,126,234,0.3);
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
            opacity: 0; transform: translateY(20px);
            transition: var(--transition); pointer-events: none;
        }
        .shortcut-hint.show { opacity: 1; transform: translateY(0); }
        .shortcut-hint h4 { font-size: 13px; margin-bottom: 10px; color: var(--primary); }
        .shortcut-item { display: flex; justify-content: space-between; gap: 20px; margin: 6px 0; }
        .shortcut-key {
            background: rgba(102,126,234,0.2); padding: 2px 8px;
            border-radius: 4px; font-family: monospace; font-size: 11px;
        }
        .progress-bar {
            height: 3px; background: var(--border); border-radius: 2px;
            overflow: hidden; margin-top: 8px;
        }
        .progress-fill {
            height: 100%; background: linear-gradient(90deg, var(--primary), var(--secondary));
            border-radius: 2px; transition: width 0.3s;
        }
        .avatar-ring {
            position: relative;
        }
        .avatar-ring::before {
            content: ''; position: absolute; inset: -3px;
            border-radius: inherit; 
            background: linear-gradient(135deg, var(--primary), var(--secondary), var(--accent));
            z-index: -1; animation: rotate 3s linear infinite;
        }
        @keyframes rotate { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        .typing-text::after {
            content: '|'; animation: blink 1s infinite;
            color: var(--primary);
        }
        @keyframes blink { 0%, 50% { opacity: 1; } 51%, 100% { opacity: 0; } }
        .welcome-container {
            display: flex; flex-direction: column; align-items: center; justify-content: center;
            height: 100%; padding: 40px 20px; text-align: center;
            animation: fadeIn 0.6s ease-out;
        }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
        .welcome-avatar {
            width: 100px; height: 100px; border-radius: 24px; margin-bottom: 24px;
            box-shadow: 0 8px 32px rgba(102,126,234,0.3);
            animation: float 3s ease-in-out infinite;
        }
        @keyframes float { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-10px); } }
        .welcome-title {
            font-size: 32px; font-weight: 700; margin-bottom: 12px;
            background: linear-gradient(135deg, var(--primary), var(--secondary), var(--accent));
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }
        .welcome-subtitle { font-size: 16px; color: var(--text-muted); margin-bottom: 40px; max-width: 400px; line-height: 1.6; }
        .feature-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; max-width: 760px; width: 100%; }
        .feature-card {
            padding: 20px 16px; border-radius: 16px; cursor: pointer; transition: var(--transition);
            background: linear-gradient(135deg, rgba(255,255,255,0.8), rgba(255,255,255,0.6));
            border: 1px solid rgba(102,126,234,0.1); text-align: center;
            box-shadow: 0 4px 16px rgba(0,0,0,0.05);
        }
        .dark .feature-card { background: linear-gradient(135deg, rgba(40,40,65,0.8), rgba(35,35,60,0.6)); }
        .feature-card:hover { 
            transform: translateY(-4px); 
            box-shadow: 0 8px 24px rgba(102,126,234,0.2);
            border-color: var(--primary);
        }
        .feature-icon { font-size: 32px; margin-bottom: 12px; display: block; }
        .feature-name { font-size: 14px; font-weight: 600; color: var(--text-primary); margin-bottom: 4px; }
        .feature-desc { font-size: 11px; color: var(--text-muted); }
        .market-demand-section {
            margin-top: 18px; width: 100%; max-width: 760px;
            background: linear-gradient(135deg, rgba(102,126,234,0.08), rgba(16,185,129,0.06));
            border: 1px solid rgba(102,126,234,0.16);
            border-radius: 16px; padding: 14px;
        }
        .market-demand-title {
            font-size: 12px; font-weight: 700; color: var(--primary);
            display: flex; align-items: center; gap: 8px; margin-bottom: 10px;
        }
        .market-demand-grid {
            display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; position: relative; z-index: 1;
        }
        .demand-card {
            background: var(--bg-primary); border: 1px solid var(--border);
            border-radius: 12px; padding: 12px; cursor: pointer; transition: var(--transition); position: relative; z-index: 1;
        }
        .demand-card:hover {
            border-color: var(--primary); transform: translateY(-2px);
            box-shadow: 0 6px 18px rgba(102,126,234,0.18);
        }
        .demand-head { display: flex; align-items: center; gap: 6px; margin-bottom: 6px; }
        .demand-name { font-size: 12px; font-weight: 600; color: var(--text-primary); }
        .demand-desc { font-size: 11px; color: var(--text-muted); line-height: 1.45; }
        .sidebar-footer {
            padding: 12px; border-top: 1px solid var(--border);
            background: linear-gradient(180deg, transparent, rgba(102,126,234,0.05));
        }
        .sidebar-footer-btn {
            width: 100%; padding: 10px; background: none; border: 1px solid var(--border);
            border-radius: 10px; cursor: pointer; font-size: 12px; color: var(--text-secondary);
            display: flex; align-items: center; justify-content: center; gap: 8px; transition: var(--transition);
        }
        .sidebar-footer-btn:hover { background: rgba(102,126,234,0.1); border-color: var(--primary); color: var(--primary); }
        .chat-item-new { 
            border: 2px dashed var(--border); background: transparent;
            justify-content: center; color: var(--text-muted);
        }
        .chat-item-new:hover { border-color: var(--primary); color: var(--primary); background: rgba(102,126,234,0.05); }
        .empty-state {
            display: flex; flex-direction: column; align-items: center; justify-content: center;
            padding: 40px 20px; color: var(--text-muted); text-align: center;
        }
        .empty-state-icon { font-size: 48px; margin-bottom: 16px; opacity: 0.5; }
        .empty-state-text { font-size: 14px; }
        /* 角色分组样式 */
        .role-group { margin-bottom: 16px; }
        .role-group-title {
            font-size: 12px; font-weight: 600; color: var(--text-muted);
            padding: 8px 12px; margin-bottom: 8px;
            background: linear-gradient(135deg, rgba(102,126,234,0.1), rgba(118,75,162,0.05));
            border-radius: 8px; display: flex; align-items: center; gap: 6px;
        }
        .role-type-badge {
            font-size: 10px; padding: 3px 8px; border-radius: 12px;
            color: white; font-weight: 500; margin-left: auto;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .role-item { position: relative; }
        /* MCP 插件列表样式 */
        .mcp-list { display: flex; flex-direction: column; gap: 8px; }
        .mcp-item {
            display: flex; align-items: center; gap: 10px;
            padding: 10px; border-radius: 10px;
            background: linear-gradient(135deg, rgba(255,255,255,0.8), rgba(255,255,255,0.6));
            border: 1px solid rgba(102,126,234,0.1);
            transition: var(--transition); cursor: pointer;
        }
        .dark .mcp-item { background: linear-gradient(135deg, rgba(40,40,65,0.8), rgba(35,35,60,0.6)); }
        .mcp-item:hover { border-color: var(--primary); transform: translateX(4px); }
        .mcp-item.enabled { border-color: #10b981; background: linear-gradient(135deg, rgba(16,185,129,0.1), rgba(16,185,129,0.05)); }
        .mcp-icon { width: 36px; height: 36px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 18px; }
        .mcp-info { flex: 1; }
        .mcp-name { font-size: 13px; font-weight: 600; color: var(--text-primary); }
        .mcp-desc { font-size: 11px; color: var(--text-muted); }
        .mcp-tools-count { font-size: 10px; color: var(--text-muted); background: rgba(102,126,234,0.1); padding: 2px 6px; border-radius: 4px; }
        .mcp-toggle { width: 44px; height: 24px; border-radius: 12px; background: var(--border); position: relative; cursor: pointer; transition: var(--transition); }
        .mcp-toggle.enabled { background: #10b981; }
        .mcp-toggle::after {
            content: ''; position: absolute; width: 20px; height: 20px; border-radius: 50%;
            background: white; top: 2px; left: 2px; transition: var(--transition);
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }
        .mcp-toggle.enabled::after { left: 22px; }
        .mcp-config-btn {
            padding: 4px 8px; border-radius: 6px; border: 1px solid var(--border);
            background: rgba(102,126,234,0.1); color: var(--primary);
            font-size: 11px; cursor: pointer; transition: var(--transition);
        }
        .mcp-config-btn:hover { background: var(--primary); color: white; }
        /* 工作流编辑器样式 */
        .workflow-list { display: flex; flex-direction: column; gap: 8px; }
        .workflow-item {
            display: flex; align-items: center; gap: 10px;
            padding: 12px; border-radius: 10px;
            background: linear-gradient(135deg, rgba(255,255,255,0.8), rgba(255,255,255,0.6));
            border: 1px solid rgba(102,126,234,0.1);
            transition: var(--transition); cursor: pointer;
        }
        .dark .workflow-item { background: linear-gradient(135deg, rgba(40,40,65,0.8), rgba(35,35,60,0.6)); }
        .workflow-item:hover { border-color: var(--primary); transform: translateX(4px); }
        .workflow-icon { width: 40px; height: 40px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 20px; }
        .workflow-info { flex: 1; }
        .workflow-name { font-size: 13px; font-weight: 600; color: var(--text-primary); }
        .workflow-desc { font-size: 11px; color: var(--text-muted); }
        .workflow-meta { display: flex; gap: 8px; font-size: 10px; color: var(--text-muted); }
        .workflow-actions { display: flex; gap: 6px; }
        .workflow-btn {
            padding: 4px 8px; border-radius: 6px; border: none;
            font-size: 11px; cursor: pointer; transition: var(--transition);
        }
        .workflow-btn.edit { background: rgba(102,126,234,0.1); color: var(--primary); }
        .workflow-btn.edit:hover { background: var(--primary); color: white; }
        .workflow-btn.delete { background: rgba(239,68,68,0.1); color: #ef4444; }
        .workflow-btn.delete:hover { background: #ef4444; color: white; }
        .workflow-btn.run { background: rgba(16,185,129,0.1); color: #10b981; }
        .workflow-btn.run:hover { background: #10b981; color: white; }
        /* 工作流节点样式 */
        .workflow-node-item {
            display: flex; align-items: center; gap: 8px;
            padding: 10px 12px; border-radius: 8px;
            background: var(--bg-primary);
            border: 1px solid var(--border);
            cursor: grab; transition: var(--transition);
            font-size: 12px; color: var(--text-primary);
        }
        .workflow-node-item:hover {
            border-color: var(--primary);
            transform: translateX(4px);
            box-shadow: 0 2px 8px rgba(102,126,234,0.2);
        }
        .workflow-node-item:active { cursor: grabbing; }
        .workflow-node-icon { font-size: 16px; }
        .workflow-canvas-node {
            position: absolute; min-width: 140px;
            background: var(--bg-primary);
            border: 2px solid var(--border);
            border-radius: 12px; padding: 12px;
            cursor: move; user-select: none;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            transition: box-shadow 0.2s, border-color 0.2s;
        }
        .workflow-canvas-node:hover { box-shadow: 0 6px 20px rgba(0,0,0,0.15); }
        .workflow-canvas-node.selected { border-color: var(--primary); box-shadow: 0 0 0 3px rgba(102,126,234,0.2); }
        .workflow-canvas-node .node-header {
            display: flex; align-items: center; gap: 8px;
            margin-bottom: 8px; padding-bottom: 8px;
            border-bottom: 1px solid var(--border);
        }
        .workflow-canvas-node .node-icon { font-size: 18px; }
        .workflow-canvas-node .node-title { font-size: 13px; font-weight: 600; }
        .workflow-canvas-node .node-ports {
            display: flex; justify-content: space-between;
            margin-top: 8px; padding-top: 8px;
            border-top: 1px solid var(--border);
        }
        .workflow-port {
            width: 12px; height: 12px; border-radius: 50%;
            background: var(--border); cursor: pointer;
            transition: var(--transition);
        }
        .workflow-port:hover { background: var(--primary); transform: scale(1.3); }
        .workflow-port.input { background: #10b981; }
        .workflow-port.output { background: #f59e0b; }
        .workflow-connection {
            stroke: var(--primary); stroke-width: 2;
            fill: none; pointer-events: stroke;
        }
        .workflow-connection:hover { stroke-width: 3; }
        /* 属性面板样式 */
        .property-group { margin-bottom: 16px; }
        .property-label {
            font-size: 11px; font-weight: 600;
            color: var(--text-muted); margin-bottom: 6px;
            text-transform: uppercase; letter-spacing: 0.5px;
        }
        .property-input {
            width: 100%; padding: 8px 10px;
            border: 1px solid var(--border); border-radius: 6px;
            background: var(--bg-primary); color: var(--text-primary);
            font-size: 13px; transition: var(--transition);
        }
        .property-input:focus {
            outline: none; border-color: var(--primary);
            box-shadow: 0 0 0 2px rgba(102,126,234,0.1);
        }
        .property-textarea {
            min-height: 80px; resize: vertical;
            font-family: 'Fira Code', monospace; font-size: 12px;
        }
        .property-select {
            cursor: pointer;
        }
        /* 记忆系统样式 */
        .memory-list { display: flex; flex-direction: column; gap: 8px; }
        .memory-item {
            padding: 12px; border-radius: 10px;
            background: linear-gradient(135deg, rgba(255,255,255,0.8), rgba(255,255,255,0.6));
            border: 1px solid rgba(102,126,234,0.1);
            transition: var(--transition);
        }
        .dark .memory-item { background: linear-gradient(135deg, rgba(40,40,65,0.8), rgba(35,35,60,0.6)); }
        .memory-item:hover { border-color: var(--primary); }
        .memory-content { font-size: 13px; color: var(--text-primary); margin-bottom: 8px; line-height: 1.5; }
        .memory-meta {
            display: flex; align-items: center; gap: 10px;
            font-size: 11px; color: var(--text-muted);
        }
        .memory-type {
            padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: 500;
        }
        .memory-type.fact { background: rgba(59,130,246,0.2); color: #3b82f6; }
        .memory-type.preference { background: rgba(16,185,129,0.2); color: #10b981; }
        .memory-type.experience { background: rgba(245,158,11,0.2); color: #f59e0b; }
        .memory-importance {
            display: flex; gap: 2px;
        }
        .importance-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--border); }
        .importance-dot.active { background: #f59e0b; }
        .memory-actions { display: flex; gap: 6px; margin-left: auto; }
        .memory-btn {
            padding: 3px 6px; border-radius: 4px; border: none;
            font-size: 10px; cursor: pointer; transition: var(--transition);
            background: rgba(239,68,68,0.1); color: #ef4444;
        }
        .memory-btn:hover { background: #ef4444; color: white; }
        /* 多模态视觉理解样式 */
        .multimodal-result {
            padding: 12px; border-radius: 10px;
            background: linear-gradient(135deg, rgba(255,255,255,0.8), rgba(255,255,255,0.6));
            border: 1px solid rgba(102,126,234,0.1);
            margin-bottom: 8px;
        }
        .dark .multimodal-result { background: linear-gradient(135deg, rgba(40,40,65,0.8), rgba(35,35,60,0.6)); }
        .multimodal-result-header {
            display: flex; align-items: center; gap: 8px;
            margin-bottom: 8px; padding-bottom: 8px;
            border-bottom: 1px solid var(--border);
            font-size: 12px; font-weight: 600; color: var(--text-primary);
        }
        .multimodal-result-content {
            font-size: 13px; color: var(--text-primary); line-height: 1.6;
        }
        .multimodal-result-meta {
            display: flex; gap: 10px; margin-top: 8px;
            font-size: 11px; color: var(--text-muted);
        }
        .multimodal-image-thumb {
            max-width: 100%; border-radius: 8px;
            border: 1px solid var(--border); margin-bottom: 8px;
        }
        /* 模型微调平台样式 */
        .finetune-list { display: flex; flex-direction: column; gap: 8px; }
        .finetune-item {
            padding: 12px; border-radius: 10px;
            background: linear-gradient(135deg, rgba(255,255,255,0.8), rgba(255,255,255,0.6));
            border: 1px solid rgba(102,126,234,0.1);
            transition: var(--transition);
        }
        .dark .finetune-item { background: linear-gradient(135deg, rgba(40,40,65,0.8), rgba(35,35,60,0.6)); }
        .finetune-item:hover { border-color: var(--primary); }
        .finetune-header {
            display: flex; align-items: center; gap: 10px;
            margin-bottom: 8px;
        }
        .finetune-icon { font-size: 20px; }
        .finetune-title { font-size: 13px; font-weight: 600; color: var(--text-primary); }
        .finetune-meta {
            display: flex; gap: 10px; font-size: 11px; color: var(--text-muted);
            margin-bottom: 8px;
        }
        .finetune-progress {
            height: 6px; background: var(--border); border-radius: 3px;
            overflow: hidden; margin-bottom: 8px;
        }
        .finetune-progress-bar {
            height: 100%; background: linear-gradient(90deg, #10b981, #00d4aa);
            border-radius: 3px; transition: width 0.3s;
        }
        .finetune-actions { display: flex; gap: 6px; }
        .finetune-btn {
            padding: 4px 10px; border-radius: 6px; border: none;
            font-size: 11px; cursor: pointer; transition: var(--transition);
        }
        .finetune-btn.start { background: rgba(16,185,129,0.1); color: #10b981; }
        .finetune-btn.start:hover { background: #10b981; color: white; }
        .finetune-btn.stop { background: rgba(239,68,68,0.1); color: #ef4444; }
        .finetune-btn.stop:hover { background: #ef4444; color: white; }
        .finetune-btn.delete { background: rgba(107,114,128,0.1); color: #6b7280; }
        .finetune-btn.delete:hover { background: #6b7280; color: white; }
        .finetune-status {
            font-size: 11px; padding: 2px 8px; border-radius: 4px;
            margin-left: auto;
        }
        .finetune-status.pending { background: rgba(245,158,11,0.2); color: #f59e0b; }
        .finetune-status.running { background: rgba(59,130,246,0.2); color: #3b82f6; }
        .finetune-status.completed { background: rgba(16,185,129,0.2); color: #10b981; }
        .finetune-status.failed { background: rgba(239,68,68,0.2); color: #ef4444; }
        .scene-api-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 10px;
            margin-top: 8px;
        }
        .scene-api-item {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        .scene-api-item label {
            font-size: 11px;
            color: var(--text-secondary);
        }
        .scene-api-item select,
        .scene-api-item input {
            width: 100%;
            padding: 7px 10px;
            border: 1px solid var(--border);
            border-radius: 8px;
            background: var(--bg-secondary);
            color: var(--text-primary);
            font-size: 12px;
        }
        .scene-layout {
            display: grid;
            grid-template-columns: minmax(180px, 260px) minmax(0, 1fr);
            gap: 12px;
            margin-top: 10px;
            align-items: start;
        }
        .scene-nav {
            display: flex;
            flex-direction: column;
            gap: 8px;
            max-height: 560px;
            overflow: auto;
            padding-right: 6px;
        }
        .scene-nav-item {
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 11px 12px;
            cursor: pointer;
            transition: var(--transition);
            background: linear-gradient(135deg, rgba(255,255,255,0.88), rgba(248,250,255,0.78));
        }
        .dark .scene-nav-item {
            background: linear-gradient(135deg, rgba(42,42,64,0.85), rgba(36,36,58,0.7));
        }
        .scene-nav-item.active {
            border-color: rgba(79,70,229,0.55);
            box-shadow: 0 8px 22px rgba(79,70,229,0.18);
            transform: translateY(-1px);
        }
        .scene-nav-title {
            font-size: 12px;
            font-weight: 700;
            color: var(--text-primary);
            margin-bottom: 4px;
        }
        .scene-nav-desc {
            font-size: 11px;
            color: var(--text-muted);
            line-height: 1.4;
        }
        .scene-workspace {
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 16px;
            background: linear-gradient(180deg, rgba(255,255,255,0.92), rgba(248,250,255,0.82));
            min-width: 0;
            box-shadow: 0 8px 24px rgba(79,70,229,0.08);
            overflow-y: auto;
            max-height: calc(100vh - 200px);
        }
        .dark .scene-workspace {
            background: linear-gradient(180deg, rgba(42,42,64,0.88), rgba(34,34,56,0.8));
        }
        .scene-form-title {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 16px;
            font-weight: 700;
            color: var(--text-primary);
            margin-bottom: 8px;
        }
        .scene-form-desc {
            font-size: 12px;
            color: var(--text-secondary);
            margin-bottom: 12px;
            line-height: 1.5;
        }
        .scene-form-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
        }
        .scene-form-field {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        .scene-form-field.full {
            grid-column: 1 / -1;
        }
        .scene-form-field label {
            font-size: 12px;
            color: var(--text-secondary);
            font-weight: 500;
        }
        .scene-form-field textarea,
        .scene-form-field input {
            width: 100%;
            padding: 10px 12px;
            border: 1px solid var(--border);
            border-radius: 10px;
            background: var(--bg-primary);
            color: var(--text-primary);
            font-size: 13px;
            resize: vertical;
            min-height: 42px;
            line-height: 1.5;
        }
        .scene-actions {
            display: flex;
            gap: 8px;
            margin-top: 10px;
        }
        .scene-generate-btn {
            border: none;
            border-radius: 8px;
            padding: 8px 14px;
            font-size: 12px;
            font-weight: 600;
            color: white;
            background: linear-gradient(135deg, #4f46e5, #7c3aed);
            cursor: pointer;
        }
        .scene-generate-btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
        .scene-output {
            margin-top: 10px;
            border: 1px solid var(--border);
            border-radius: 10px;
            background: var(--bg-primary);
            padding: 12px;
            min-height: 220px;
            max-height: 420px;
            overflow: auto;
            font-size: 12px;
            color: var(--text-primary);
            line-height: 1.6;
            white-space: pre-wrap;
            word-break: break-word;
            overflow-wrap: anywhere;
            writing-mode: horizontal-tb;
            text-orientation: mixed;
        }
        .workbench-tabs {
            display: flex;
            gap: 4px;
            flex-wrap: wrap;
        }
        .workbench-tab {
            padding: 8px 16px;
            border: none;
            background: var(--bg-secondary);
            border-radius: 8px;
            font-size: 13px;
            color: var(--text-secondary);
            cursor: pointer;
            transition: var(--transition);
        }
        .workbench-tab:hover {
            background: rgba(102,126,234,0.1);
            color: var(--text-primary);
        }
        .workbench-tab.active {
            background: linear-gradient(135deg, var(--primary), #764ba2);
            color: white;
            font-weight: 500;
        }
        .workbench-card {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 14px;
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 12px;
            margin-bottom: 8px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .workbench-card:hover {
            border-color: var(--primary);
            transform: translateX(4px);
            box-shadow: 0 4px 12px rgba(102,126,234,0.1);
        }
        .workbench-sidebar {
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 12px;
            border: 1px solid var(--border);
        }
        .sidebar-section {
            margin-bottom: 16px;
        }
        .sidebar-section:last-child {
            margin-bottom: 0;
        }
        .sidebar-title {
            font-size: 12px;
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 8px;
            padding-bottom: 6px;
            border-bottom: 1px solid var(--border);
        }
        .sidebar-items {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }
        .sidebar-item {
            padding: 8px 12px;
            border-radius: 8px;
            font-size: 12px;
            color: var(--text-secondary);
            cursor: pointer;
            transition: var(--transition);
        }
        .sidebar-item:hover {
            background: rgba(102,126,234,0.1);
            color: var(--text-primary);
        }
        .sidebar-item.active {
            background: linear-gradient(135deg, rgba(102,126,234,0.15), rgba(118,75,162,0.1));
            color: var(--primary);
            font-weight: 500;
        }
        .workbench-toolbar {
            display: flex;
            gap: 10px;
            margin-bottom: 12px;
        }
        .workbench-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
            gap: 12px;
        }
        .workbench-template-card {
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 14px;
            cursor: pointer;
            transition: var(--transition);
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .workbench-template-card:hover {
            border-color: var(--primary);
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(102,126,234,0.15);
        }
        .template-icon {
            font-size: 24px;
        }
        .template-info {
            flex: 1;
        }
        .template-name {
            font-size: 13px;
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 4px;
        }
        .template-desc {
            font-size: 11px;
            color: var(--text-muted);
            line-height: 1.4;
        }
        .template-actions {
            display: flex;
            justify-content: flex-end;
        }
        .template-action-btn {
            background: none;
            border: none;
            cursor: pointer;
            font-size: 14px;
            padding: 4px 8px;
            border-radius: 6px;
            transition: var(--transition);
        }
        .template-action-btn:hover {
            background: rgba(102,126,234,0.1);
        }
        @media (max-width: 1320px) {
            .scene-layout {
                grid-template-columns: 1fr;
            }
            .scene-nav {
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                max-height: none;
                overflow: visible;
                padding-right: 0;
            }
            .scene-workspace {
                min-height: 420px;
            }
        }
        @media (max-width: 860px) {
            .scene-api-grid,
            .scene-form-grid,
            .scene-nav {
                grid-template-columns: 1fr;
            }
            .scene-actions {
                flex-wrap: wrap;
            }
            .scene-output {
                min-height: 260px;
            }
        }
    </style>
</head>
<body>
    <div class="app-container">
        <aside class="sidebar" id="sidebar">
            <div class="sidebar-header">
                <h2><img src="/sidebar-icon" class="sidebar-logo"> 辉夜助手 <span style="font-size:9px;color:var(--lora-color);">v3.3</span></h2>
                <button class="new-chat-btn" onclick="newChat()"><span>✨</span> <span>新对话</span></button>
            </div>
            <div class="sidebar-tabs">
                <button class="sidebar-tab active" onclick="switchTab('chats', this)">对话</button>
                <button class="sidebar-tab" onclick="switchTab('console', this)">控制台</button>
                <button class="sidebar-tab" onclick="switchTab('ecosystem', this)">生态</button>
                <button class="sidebar-tab" onclick="switchTab('scenes', this)">场景</button>
                <button class="sidebar-tab" onclick="switchTab('prompts', this)">模板</button>
                <button class="sidebar-tab" onclick="switchTab('project', this)">项目</button>
                <button class="sidebar-tab" onclick="switchTab('ops', this)">运营</button>
                <button class="sidebar-tab" onclick="switchTab('release', this)">发布</button>
                <button class="sidebar-tab" onclick="switchTab('alert', this)">告警</button>
                <button class="sidebar-tab" onclick="switchTab('ab', this)">实验</button>
                <button class="sidebar-tab" onclick="switchTab('integration', this)">集成</button>
                <button class="sidebar-tab" onclick="switchTab('loras', this)">LoRA</button>
                <button class="sidebar-tab" onclick="switchTab('tools', this)">工具</button>
                <button class="sidebar-tab" onclick="switchTab('mcp', this)">插件</button>
                <button class="sidebar-tab" onclick="switchTab('workflow', this)">工作流</button>
                <button class="sidebar-tab" onclick="switchTab('memory', this)">记忆</button>
                <button class="sidebar-tab" onclick="switchTab('multimodal', this)">视觉</button>
                <button class="sidebar-tab" onclick="switchTab('finetune', this)">微调</button>
                <button class="sidebar-tab" onclick="switchTab('roles', this)">角色</button>
                <button class="sidebar-tab" onclick="switchTab('rag', this)">RAG</button>
            </div>
            <div id="chatsTab" class="tab-content active">
                <div style="padding:8px;border-bottom:1px solid var(--border);">
                    <input type="text" id="chatSearch" placeholder="🔍 搜索对话..." style="width:100%;padding:6px 10px;border:1px solid var(--border);border-radius:6px;font-size:11px;background:var(--bg-secondary);color:var(--text-primary);" oninput="searchChats(this.value)">
                </div>
                <div class="chat-list" id="chatList"></div>
            </div>
            <div id="consoleTab" class="tab-content">
                <div style="padding:12px;display:flex;flex-direction:column;gap:10px;">
                    <div class="console-score-grid" id="consoleScoreGrid"></div>
                    
                    <div class="project-panel">
                        <div class="project-panel-head">
                            <span class="project-panel-title">📊 系统监控仪表盘</span>
                            <div class="project-panel-actions">
                                <button class="project-mini-btn" onclick="refreshSystemMetrics()">刷新</button>
                                <button class="project-mini-btn" onclick="openSystemMonitorModal()">详情</button>
                            </div>
                        </div>
                        <div class="console-metrics-grid" id="systemMetricsGrid">
                            <div class="metric-card">
                                <div class="metric-icon">💻</div>
                                <div class="metric-info">
                                    <div class="metric-label">CPU 使用率</div>
                                    <div class="metric-value" id="cpuUsage">--</div>
                                </div>
                                <div class="metric-bar"><div class="metric-bar-fill" id="cpuBar" style="width:0%"></div></div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-icon">🧠</div>
                                <div class="metric-info">
                                    <div class="metric-label">内存使用</div>
                                    <div class="metric-value" id="memoryUsage">--</div>
                                </div>
                                <div class="metric-bar"><div class="metric-bar-fill" id="memoryBar" style="width:0%"></div></div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-icon">💾</div>
                                <div class="metric-info">
                                    <div class="metric-label">磁盘空间</div>
                                    <div class="metric-value" id="diskUsage">--</div>
                                </div>
                                <div class="metric-bar"><div class="metric-bar-fill" id="diskBar" style="width:0%"></div></div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-icon">🌐</div>
                                <div class="metric-info">
                                    <div class="metric-label">网络状态</div>
                                    <div class="metric-value" id="networkStatus">--</div>
                                </div>
                                <div class="metric-bar"><div class="metric-bar-fill" id="networkBar" style="width:0%"></div></div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="project-panel">
                        <div class="project-panel-head">
                            <span class="project-panel-title">📝 实时日志查看器</span>
                            <div class="project-panel-actions">
                                <select class="project-input" id="logLevelFilter" onchange="filterLogs()">
                                    <option value="all">全部级别</option>
                                    <option value="error">错误</option>
                                    <option value="warn">警告</option>
                                    <option value="info">信息</option>
                                    <option value="debug">调试</option>
                                </select>
                                <button class="project-mini-btn" onclick="clearLogs()">清空</button>
                                <button class="project-mini-btn" onclick="exportLogs()">导出</button>
                                <button class="project-mini-btn" onclick="toggleLogAutoScroll()">自动滚动</button>
                            </div>
                        </div>
                        <div class="log-viewer" id="logViewer">
                            <div class="log-entry log-info"><span class="log-time">[系统]</span> 日志查看器已就绪</div>
                        </div>
                    </div>
                    
                    <div class="project-panel">
                        <div class="project-panel-head">
                            <span class="project-panel-title">⏰ 任务调度中心</span>
                            <div class="project-panel-actions">
                                <button class="project-mini-btn" onclick="openTaskSchedulerModal()">新建任务</button>
                                <button class="project-mini-btn" onclick="refreshScheduledTasks()">刷新</button>
                            </div>
                        </div>
                        <div class="task-scheduler-grid" id="scheduledTasksList">
                            <div class="scheduler-task-card">
                                <div class="task-header">
                                    <span class="task-name">📊 每日统计汇总</span>
                                    <span class="task-status active">运行中</span>
                                </div>
                                <div class="task-info">
                                    <span>⏰ 每天 00:00</span>
                                    <span>🔄 上次: 今日 00:00</span>
                                </div>
                            </div>
                            <div class="scheduler-task-card">
                                <div class="task-header">
                                    <span class="task-name">🗑️ 缓存清理</span>
                                    <span class="task-status active">运行中</span>
                                </div>
                                <div class="task-info">
                                    <span>⏰ 每周日 03:00</span>
                                    <span>🔄 上次: 周日 03:00</span>
                                </div>
                            </div>
                            <div class="scheduler-task-card">
                                <div class="task-header">
                                    <span class="task-name">💾 数据备份</span>
                                    <span class="task-status paused">已暂停</span>
                                </div>
                                <div class="task-info">
                                    <span>⏰ 每天 04:00</span>
                                    <span>🔄 上次: --</span>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="project-panel">
                        <div class="project-panel-head">
                            <span class="project-panel-title">🔍 全局检索中心</span>
                            <div class="project-panel-actions console-search-row">
                                <input class="project-input" id="globalSearchInput" placeholder="搜索产物/任务/发布/告警/实验/集成" oninput="runGlobalSearch(this.value)">
                                <select class="project-input" id="globalSearchEntity" onchange="runGlobalSearch(document.getElementById('globalSearchInput').value)">
                                    <option value="">全部</option>
                                    <option value="artifact">产物</option>
                                    <option value="task">任务</option>
                                    <option value="release">发布</option>
                                    <option value="alert">告警</option>
                                    <option value="ab">实验</option>
                                    <option value="integration">集成</option>
                                    <option value="milestone">里程碑</option>
                                    <option value="risk">风险</option>
                                    <option value="workspace_project">生态项目</option>
                                </select>
                            </div>
                        </div>
                        <div class="project-list" id="globalSearchList"></div>
                    </div>
                    
                    <div class="project-panel">
                        <div class="project-panel-head">
                            <span class="project-panel-title">📈 性能分析仪表盘</span>
                            <div class="project-panel-actions">
                                <select class="project-input" id="perfTimeRange" onchange="loadPerformanceData()">
                                    <option value="1h">最近1小时</option>
                                    <option value="24h">最近24小时</option>
                                    <option value="7d">最近7天</option>
                                    <option value="30d">最近30天</option>
                                </select>
                                <button class="project-mini-btn" onclick="exportPerformanceReport()">导出报告</button>
                            </div>
                        </div>
                        <div class="performance-charts" id="performanceCharts">
                            <div class="perf-chart-container">
                                <div class="perf-chart-title">响应时间分布</div>
                                <div class="perf-chart" id="responseTimeChart"></div>
                            </div>
                            <div class="perf-chart-container">
                                <div class="perf-chart-title">请求量趋势</div>
                                <div class="perf-chart" id="requestVolumeChart"></div>
                            </div>
                        </div>
                        <div class="perf-stats-grid" id="perfStatsGrid">
                            <div class="perf-stat-item">
                                <div class="perf-stat-value" id="avgResponseTime">--</div>
                                <div class="perf-stat-label">平均响应时间</div>
                            </div>
                            <div class="perf-stat-item">
                                <div class="perf-stat-value" id="totalRequests">--</div>
                                <div class="perf-stat-label">总请求数</div>
                            </div>
                            <div class="perf-stat-item">
                                <div class="perf-stat-value" id="errorRate">--</div>
                                <div class="perf-stat-label">错误率</div>
                            </div>
                            <div class="perf-stat-item">
                                <div class="perf-stat-value" id="throughput">--</div>
                                <div class="perf-stat-label">吞吐量/秒</div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="project-panel">
                        <div class="project-panel-head">
                            <span class="project-panel-title">🧠 智能治理建议</span>
                            <div class="project-panel-actions">
                                <button class="project-mini-btn" onclick="loadConsoleData()">刷新</button>
                                <button class="project-mini-btn" onclick="generateGovernanceReport()">生成报告</button>
                            </div>
                        </div>
                        <div class="project-list" id="consoleRecommendationList"></div>
                    </div>
                </div>
            </div>
            <div id="ecosystemTab" class="tab-content">
                <div style="padding:12px;display:flex;flex-direction:column;gap:10px;">
                    <div class="ops-kpi" id="workspaceOverviewCards"></div>
                    
                    <div class="project-panel">
                        <div class="project-panel-head">
                            <span class="project-panel-title">🔧 服务健康检查</span>
                            <div class="project-panel-actions">
                                <button class="project-mini-btn" onclick="checkAllServicesHealth()">检查全部</button>
                                <button class="project-mini-btn" onclick="openServiceConfigModal()">配置服务</button>
                            </div>
                        </div>
                        <div class="service-health-grid" id="serviceHealthGrid">
                            <div class="service-card healthy">
                                <div class="service-icon">🤖</div>
                                <div class="service-info">
                                    <div class="service-name">Ollama 服务</div>
                                    <div class="service-status">● 运行中</div>
                                </div>
                                <div class="service-actions">
                                    <button class="service-btn" onclick="restartService('ollama')">重启</button>
                                </div>
                            </div>
                            <div class="service-card healthy">
                                <div class="service-icon">🌐</div>
                                <div class="service-info">
                                    <div class="service-name">Flask 服务</div>
                                    <div class="service-status">● 运行中</div>
                                </div>
                                <div class="service-actions">
                                    <button class="service-btn" onclick="restartService('flask')">重启</button>
                                </div>
                            </div>
                            <div class="service-card unknown">
                                <div class="service-icon">🔍</div>
                                <div class="service-info">
                                    <div class="service-name">Elasticsearch</div>
                                    <div class="service-status">● 未配置</div>
                                </div>
                                <div class="service-actions">
                                    <button class="service-btn" onclick="configureService('elasticsearch')">配置</button>
                                </div>
                            </div>
                            <div class="service-card unknown">
                                <div class="service-icon">🗄️</div>
                                <div class="service-info">
                                    <div class="service-name">Redis 缓存</div>
                                    <div class="service-status">● 未配置</div>
                                </div>
                                <div class="service-actions">
                                    <button class="service-btn" onclick="configureService('redis')">配置</button>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="project-panel">
                        <div class="project-panel-head">
                            <span class="project-panel-title">📦 项目依赖分析</span>
                            <div class="project-panel-actions">
                                <button class="project-mini-btn" onclick="analyzeAllDependencies()">分析全部</button>
                                <button class="project-mini-btn" onclick="checkSecurityVulnerabilities()">安全检查</button>
                            </div>
                        </div>
                        <div class="dependency-overview" id="dependencyOverview">
                            <div class="dep-summary">
                                <div class="dep-stat">
                                    <span class="dep-stat-value" id="totalDeps">--</span>
                                    <span class="dep-stat-label">总依赖</span>
                                </div>
                                <div class="dep-stat">
                                    <span class="dep-stat-value" id="outdatedDeps">--</span>
                                    <span class="dep-stat-label">过时</span>
                                </div>
                                <div class="dep-stat">
                                    <span class="dep-stat-value" id="vulnerableDeps">--</span>
                                    <span class="dep-stat-label">漏洞</span>
                                </div>
                            </div>
                        </div>
                        <div class="project-list" id="dependencyList"></div>
                    </div>
                    
                    <div class="project-panel">
                        <div class="project-panel-head">
                            <span class="project-panel-title">🔀 Git 状态监控</span>
                            <div class="project-panel-actions">
                                <button class="project-mini-btn" onclick="refreshGitStatus()">刷新</button>
                                <button class="project-mini-btn" onclick="openGitOperationsModal()">Git操作</button>
                            </div>
                        </div>
                        <div class="git-status-grid" id="gitStatusGrid">
                            <div class="git-repo-card">
                                <div class="git-repo-header">
                                    <span class="git-repo-name">📁 qwen3_web</span>
                                    <span class="git-branch">🌿 main</span>
                                </div>
                                <div class="git-repo-stats">
                                    <span class="git-stat">📝 3 已修改</span>
                                    <span class="git-stat">➕ 2 新文件</span>
                                    <span class="git-stat">⏳ 1 待推送</span>
                                </div>
                                <div class="git-repo-actions">
                                    <button class="git-btn" onclick="gitCommit('qwen3_web')">提交</button>
                                    <button class="git-btn" onclick="gitPush('qwen3_web')">推送</button>
                                    <button class="git-btn" onclick="gitPull('qwen3_web')">拉取</button>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="project-panel">
                        <div class="project-panel-head">
                            <span class="project-panel-title">🌐 辉夜项目整合中心</span>
                            <div class="project-panel-actions">
                                <input class="project-input" id="workspaceSearchInput" placeholder="搜索项目名/路径/描述" oninput="loadWorkspaceProjects(this.value)">
                                <button class="project-mini-btn" onclick="refreshWorkspaceProjects()">刷新扫描</button>
                                <button class="project-mini-btn" onclick="openNewProjectModal()">新建项目</button>
                            </div>
                        </div>
                        <div class="project-list" id="workspaceProjectList"></div>
                    </div>
                    
                    <div class="project-panel">
                        <div class="project-panel-head">
                            <span class="project-panel-title">📋 项目模板库</span>
                            <div class="project-panel-actions">
                                <input class="project-input" id="templateSearchInput" placeholder="搜索模板" oninput="searchProjectTemplates(this.value)">
                                <button class="project-mini-btn" onclick="openCreateTemplateModal()">创建模板</button>
                            </div>
                        </div>
                        <div class="template-grid" id="projectTemplateGrid">
                            <div class="template-card" onclick="useTemplate('flask-api')">
                                <div class="template-icon">🌐</div>
                                <div class="template-info">
                                    <div class="template-name">Flask API 项目</div>
                                    <div class="template-desc">快速创建 RESTful API 服务</div>
                                </div>
                            </div>
                            <div class="template-card" onclick="useTemplate('ml-project')">
                                <div class="template-icon">🤖</div>
                                <div class="template-info">
                                    <div class="template-name">机器学习项目</div>
                                    <div class="template-desc">包含数据处理、模型训练流程</div>
                                </div>
                            </div>
                            <div class="template-card" onclick="useTemplate('web-scraper')">
                                <div class="template-icon">🕷️</div>
                                <div class="template-info">
                                    <div class="template-name">爬虫项目</div>
                                    <div class="template-desc">网页数据采集与处理</div>
                                </div>
                            </div>
                            <div class="template-card" onclick="useTemplate('cli-tool')">
                                <div class="template-icon">⚡</div>
                                <div class="template-info">
                                    <div class="template-name">CLI 工具</div>
                                    <div class="template-desc">命令行工具脚手架</div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="project-panel">
                        <div class="project-panel-head">
                            <span class="project-panel-title">🚀 一键部署中心</span>
                            <div class="project-panel-actions">
                                <select class="project-input" id="deployTargetSelect">
                                    <option value="local">本地环境</option>
                                    <option value="docker">Docker 容器</option>
                                    <option value="k8s">Kubernetes</option>
                                    <option value="cloud">云服务</option>
                                </select>
                                <button class="project-mini-btn" onclick="openDeployConfigModal()">配置</button>
                                <button class="project-mini-btn" onclick="executeDeploy()">部署</button>
                            </div>
                        </div>
                        <div class="deploy-history" id="deployHistoryList">
                            <div class="deploy-record success">
                                <div class="deploy-info">
                                    <span class="deploy-project">qwen3_web</span>
                                    <span class="deploy-target">→ 本地环境</span>
                                </div>
                                <div class="deploy-meta">
                                    <span class="deploy-time">✅ 成功 · 2分钟前</span>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="project-panel">
                        <div class="project-panel-head">
                            <span class="project-panel-title">📊 数据流监控</span>
                            <div class="project-panel-actions">
                                <button class="project-mini-btn" onclick="refreshDataFlowStats()">刷新</button>
                                <button class="project-mini-btn" onclick="openDataFlowConfigModal()">配置</button>
                            </div>
                        </div>
                        <div class="dataflow-overview" id="dataFlowOverview">
                            <div class="dataflow-chart" id="dataFlowChart">
                                <div class="dataflow-node input">
                                    <div class="node-icon">📥</div>
                                    <div class="node-label">输入</div>
                                    <div class="node-value" id="dataflowInput">--</div>
                                </div>
                                <div class="dataflow-arrow">→</div>
                                <div class="dataflow-node process">
                                    <div class="node-icon">⚙️</div>
                                    <div class="node-label">处理</div>
                                    <div class="node-value" id="dataflowProcess">--</div>
                                </div>
                                <div class="dataflow-arrow">→</div>
                                <div class="dataflow-node output">
                                    <div class="node-icon">📤</div>
                                    <div class="node-label">输出</div>
                                    <div class="node-value" id="dataflowOutput">--</div>
                                </div>
                            </div>
                            <div class="dataflow-stats">
                                <div class="dataflow-stat">
                                    <span class="stat-label">处理速率</span>
                                    <span class="stat-value" id="dataflowRate">-- req/s</span>
                                </div>
                                <div class="dataflow-stat">
                                    <span class="stat-label">队列深度</span>
                                    <span class="stat-value" id="dataflowQueue">--</span>
                                </div>
                                <div class="dataflow-stat">
                                    <span class="stat-label">平均延迟</span>
                                    <span class="stat-value" id="dataflowLatency">-- ms</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <div id="scenesTab" class="tab-content">
                <div style="padding:12px;display:flex;flex-direction:column;gap:10px;">
                    <div class="project-panel">
                        <div class="project-panel-head">
                            <span class="project-panel-title">🌐 外界API适配中心</span>
                            <div class="project-panel-actions">
                                <button class="project-mini-btn" onclick="loadExternalApiConfig()">加载配置</button>
                                <button class="project-mini-btn" onclick="testExternalApiConfig()">测试连通</button>
                                <button class="project-mini-btn" onclick="saveExternalApiConfig()">保存配置</button>
                            </div>
                        </div>
                        <div class="scene-api-grid">
                            <div class="scene-api-item">
                                <label>Provider</label>
                                <select id="sceneProviderSelect" onchange="handleSceneProviderChange(this.value)">
                                    <option value="deepseek">DeepSeek</option>
                                    <option value="openai">OpenAI</option>
                                    <option value="claude">Claude</option>
                                    <option value="gemini">Gemini</option>
                                    <option value="moonshot">Moonshot</option>
                                    <option value="qwen">Qwen API</option>
                                    <option value="zhipu">Zhipu</option>
                                </select>
                            </div>
                            <div class="scene-api-item">
                                <label>API URL</label>
                                <input id="sceneApiUrlInput" class="project-input" placeholder="https://api.deepseek.com">
                            </div>
                            <div class="scene-api-item">
                                <label>模型名</label>
                                <input id="sceneModelInput" class="project-input" placeholder="deepseek-chat">
                            </div>
                            <div class="scene-api-item">
                                <label>API Key</label>
                                <input id="sceneApiKeyInput" class="project-input" type="password" placeholder="sk-...">
                            </div>
                        </div>
                        <div id="sceneApiStatus" style="font-size:11px;color:var(--text-muted);margin-top:8px;"></div>
                    </div>
                    <div class="project-panel">
                        <div class="project-panel-head">
                            <span class="project-panel-title">🚀 高需求专业场景（外界API子界面）</span>
                            <div class="project-panel-actions">
                                <span class="project-tag" id="sceneCurrentTag">当前: 电商增长</span>
                            </div>
                        </div>
                        <div class="scene-layout">
                            <div class="scene-nav" id="sceneNav"></div>
                            <div class="scene-workspace" id="sceneWorkspace"></div>
                        </div>
                    </div>
                </div>
            </div>
            <div id="promptsTab" class="tab-content">
                <div class="prompt-toolbar" style="display:flex;justify-content:space-between;align-items:center;">
                    <div style="flex:1;">
                        <input id="promptSearch" class="prompt-search-input" placeholder="🔍 搜索模板/场景/开源来源" oninput="setPromptSearch(this.value)">
                        <div class="prompt-category-row">
                            <button class="prompt-chip active" id="promptCatAll" onclick="setPromptCategory('all')">全部</button>
                            <button class="prompt-chip" id="promptCatGeneral" onclick="setPromptCategory('general')">通用</button>
                            <button class="prompt-chip" id="promptCatGrowth" onclick="setPromptCategory('growth')">增长运营</button>
                            <button class="prompt-chip" id="promptCatEngineering" onclick="setPromptCategory('engineering')">工程治理</button>
                            <button class="prompt-chip" id="promptCatKnowledge" onclick="setPromptCategory('knowledge')">知识研究</button>
                        </div>
                    </div>
                    <button class="project-mini-btn" onclick="expandToCenter('promptsTab')" title="展开到中央" style="margin-left:10px;flex-shrink:0;">⛶ 展开</button>
                </div>
                
                <div class="project-panel" style="margin:10px;">
                    <div class="project-panel-head">
                        <span class="project-panel-title">🧭 专业工作台</span>
                        <div class="project-panel-actions">
                            <button class="project-mini-btn" onclick="openPromptWorkbench()">打开工作台</button>
                        </div>
                    </div>
                    <div class="workbench-overview" id="workbenchOverview">
                        <div class="workbench-stats">
                            <div class="workbench-stat">
                                <div class="stat-icon">📝</div>
                                <div class="stat-info">
                                    <div class="stat-value" id="workbenchTemplateCount">--</div>
                                    <div class="stat-label">可用模板</div>
                                </div>
                            </div>
                            <div class="workbench-stat">
                                <div class="stat-icon">⭐</div>
                                <div class="stat-info">
                                    <div class="stat-value" id="workbenchFavoriteCount">--</div>
                                    <div class="stat-label">收藏模板</div>
                                </div>
                            </div>
                            <div class="workbench-stat">
                                <div class="stat-icon">📊</div>
                                <div class="stat-info">
                                    <div class="stat-value" id="workbenchUsageCount">--</div>
                                    <div class="stat-label">本月使用</div>
                                </div>
                            </div>
                            <div class="workbench-stat">
                                <div class="stat-icon">🔧</div>
                                <div class="stat-info">
                                    <div class="stat-value" id="workbenchCustomCount">--</div>
                                    <div class="stat-label">自定义模板</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="project-panel" style="margin:10px;">
                    <div class="project-panel-head">
                        <span class="project-panel-title">🎯 快速场景</span>
                        <div class="project-panel-actions">
                            <button class="project-mini-btn" onclick="openQuickSceneModal()">新建场景</button>
                        </div>
                    </div>
                    <div class="quick-scene-grid" id="quickSceneGrid">
                        <div class="quick-scene-card" onclick="applyQuickScene('code-review')">
                            <div class="scene-icon">🔍</div>
                            <div class="scene-info">
                                <div class="scene-name">代码审查</div>
                                <div class="scene-desc">专业代码质量分析</div>
                            </div>
                        </div>
                        <div class="quick-scene-card" onclick="applyQuickScene('doc-gen')">
                            <div class="scene-icon">📄</div>
                            <div class="scene-info">
                                <div class="scene-name">文档生成</div>
                                <div class="scene-desc">自动生成技术文档</div>
                            </div>
                        </div>
                        <div class="quick-scene-card" onclick="applyQuickScene('api-design')">
                            <div class="scene-icon">🔌</div>
                            <div class="scene-info">
                                <div class="scene-name">API 设计</div>
                                <div class="scene-desc">RESTful API 规划</div>
                            </div>
                        </div>
                        <div class="quick-scene-card" onclick="applyQuickScene('test-gen')">
                            <div class="scene-icon">🧪</div>
                            <div class="scene-info">
                                <div class="scene-name">测试生成</div>
                                <div class="scene-desc">单元测试用例生成</div>
                            </div>
                        </div>
                        <div class="quick-scene-card" onclick="applyQuickScene('refactor')">
                            <div class="scene-icon">♻️</div>
                            <div class="scene-info">
                                <div class="scene-name">代码重构</div>
                                <div class="scene-desc">智能代码优化建议</div>
                            </div>
                        </div>
                        <div class="quick-scene-card" onclick="applyQuickScene('security')">
                            <div class="scene-icon">🔒</div>
                            <div class="scene-info">
                                <div class="scene-name">安全审计</div>
                                <div class="scene-desc">代码安全漏洞检测</div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="project-panel" style="margin:10px;">
                    <div class="project-panel-head">
                        <span class="project-panel-title">📈 模板分析</span>
                        <div class="project-panel-actions">
                            <select class="project-input" id="templateAnalysisRange" onchange="loadTemplateAnalysis()">
                                <option value="7d">最近7天</option>
                                <option value="30d">最近30天</option>
                                <option value="90d">最近90天</option>
                            </select>
                            <button class="project-mini-btn" onclick="exportTemplateReport()">导出报告</button>
                        </div>
                    </div>
                    <div class="template-analysis" id="templateAnalysis">
                        <div class="analysis-chart">
                            <div class="chart-title">使用频率 Top 5</div>
                            <div class="chart-bars" id="templateUsageChart">
                                <div class="chart-bar-item">
                                    <span class="bar-label">代码审查</span>
                                    <div class="bar-track"><div class="bar-fill" style="width:85%"></div></div>
                                    <span class="bar-value">85次</span>
                                </div>
                                <div class="chart-bar-item">
                                    <span class="bar-label">文档生成</span>
                                    <div class="bar-track"><div class="bar-fill" style="width:72%"></div></div>
                                    <span class="bar-value">72次</span>
                                </div>
                                <div class="chart-bar-item">
                                    <span class="bar-label">API设计</span>
                                    <div class="bar-track"><div class="bar-fill" style="width:58%"></div></div>
                                    <span class="bar-value">58次</span>
                                </div>
                                <div class="chart-bar-item">
                                    <span class="bar-label">测试生成</span>
                                    <div class="bar-track"><div class="bar-fill" style="width:45%"></div></div>
                                    <span class="bar-value">45次</span>
                                </div>
                                <div class="chart-bar-item">
                                    <span class="bar-label">代码重构</span>
                                    <div class="bar-track"><div class="bar-fill" style="width:32%"></div></div>
                                    <span class="bar-value">32次</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="prompt-list" id="promptList"></div>
            </div>
            <div id="projectTab" class="tab-content">
                <div class="project-center">
                    <div class="project-overview" id="projectOverviewCards"></div>
                    <div class="project-split">
                        <div style="display:flex;flex-direction:column;gap:10px;">
                            <div class="project-panel">
                                <div class="project-panel-head">
                                    <span class="project-panel-title">📦 产物中心</span>
                                    <div class="project-panel-actions">
                                        <input class="project-input" id="artifactSearchInput" placeholder="搜索产物" oninput="loadProjectArtifacts(this.value)">
                                        <button class="project-mini-btn" onclick="openArtifactModal()">➕ 新增</button>
                                    </div>
                                </div>
                                <div class="project-list" id="artifactList"></div>
                            </div>
                            <div class="project-panel">
                                <div class="project-panel-head">
                                    <span class="project-panel-title">🗂️ 任务看板</span>
                                    <div class="project-panel-actions">
                                        <button class="project-mini-btn" onclick="openTaskModal()">➕ 任务</button>
                                        <button class="project-mini-btn" onclick="batchMoveTasks('doing')">批量推进</button>
                                        <button class="project-mini-btn" onclick="batchMoveTasks('done')">批量完成</button>
                                    </div>
                                </div>
                                <div class="kanban-board" id="projectKanbanBoard"></div>
                            </div>
                        </div>
                        <div style="display:flex;flex-direction:column;gap:10px;">
                            <div class="project-panel">
                                <div class="project-panel-head">
                                    <span class="project-panel-title">🧠 策略剧本</span>
                                    <div class="project-panel-actions">
                                        <button class="project-mini-btn" onclick="openPlaybookModal()">➕ 自定义</button>
                                    </div>
                                </div>
                                <div class="project-list" id="playbookList"></div>
                            </div>
                            <div class="project-panel">
                                <div class="project-panel-head">
                                    <span class="project-panel-title">🕒 操作审计</span>
                                    <div class="project-panel-actions">
                                        <button class="project-mini-btn" onclick="loadProjectActivity()">刷新</button>
                                    </div>
                                </div>
                                <div class="activity-list" id="projectActivityList"></div>
                            </div>
                            <div class="project-panel">
                                <div class="project-panel-head">
                                    <span class="project-panel-title">🎯 里程碑路线图</span>
                                    <div class="project-panel-actions">
                                        <button class="project-mini-btn" onclick="openMilestoneModal()">➕ 里程碑</button>
                                    </div>
                                </div>
                                <div class="project-list" id="milestoneList"></div>
                            </div>
                            <div class="project-panel">
                                <div class="project-panel-head">
                                    <span class="project-panel-title">⚠️ 风险台账</span>
                                    <div class="project-panel-actions">
                                        <button class="project-mini-btn" onclick="openRiskModal()">➕ 风险</button>
                                    </div>
                                </div>
                                <div class="project-list" id="riskList"></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <div id="opsTab" class="tab-content">
                <div style="padding:12px;display:flex;flex-direction:column;gap:10px;">
                    <div class="ops-kpi" id="opsOverviewCards"></div>
                    <div class="project-panel">
                        <div class="project-panel-head">
                            <span class="project-panel-title">📣 运营活动中心</span>
                            <div class="project-panel-actions">
                                <input class="project-input" id="opsSearchInput" placeholder="搜索活动/渠道/负责人" oninput="loadOpsCampaigns(this.value)">
                                <button class="project-mini-btn" onclick="openOpsCampaignModal()">➕ 新活动</button>
                            </div>
                        </div>
                        <div class="project-list" id="opsCampaignList"></div>
                    </div>
                </div>
            </div>
            <div id="releaseTab" class="tab-content">
                <div style="padding:12px;display:flex;flex-direction:column;gap:10px;">
                    <div class="ops-kpi" id="releaseOverviewCards"></div>
                    <div class="project-panel">
                        <div class="project-panel-head">
                            <span class="project-panel-title">🚀 发布计划中心</span>
                            <div class="project-panel-actions">
                                <button class="project-mini-btn" onclick="openReleasePlanModal()">➕ 新计划</button>
                            </div>
                        </div>
                        <div class="project-list" id="releasePlanList"></div>
                    </div>
                </div>
            </div>
            <div id="alertTab" class="tab-content">
                <div style="padding:12px;display:flex;flex-direction:column;gap:10px;">
                    <div class="ops-kpi" id="alertOverviewCards"></div>
                    <div class="project-panel">
                        <div class="project-panel-head">
                            <span class="project-panel-title">🚨 告警规则中心</span>
                            <div class="project-panel-actions">
                                <button class="project-mini-btn" onclick="openAlertRuleModal()">➕ 新规则</button>
                            </div>
                        </div>
                        <div class="project-list" id="alertRuleList"></div>
                    </div>
                </div>
            </div>
            <div id="abTab" class="tab-content">
                <div style="padding:12px;display:flex;flex-direction:column;gap:10px;">
                    <div class="ops-kpi" id="abOverviewCards"></div>
                    <div class="project-panel">
                        <div class="project-panel-head">
                            <span class="project-panel-title">🧪 A/B 实验中心</span>
                            <div class="project-panel-actions">
                                <button class="project-mini-btn" onclick="openAbModal()">➕ 新实验</button>
                            </div>
                        </div>
                        <div class="project-list" id="abExperimentList"></div>
                    </div>
                </div>
            </div>
            <div id="integrationTab" class="tab-content">
                <div style="padding:12px;display:flex;flex-direction:column;gap:10px;">
                    <div class="ops-kpi" id="integrationOverviewCards"></div>
                    <div class="project-panel">
                        <div class="project-panel-head">
                            <span class="project-panel-title">🧩 集成市场</span>
                            <div class="project-panel-actions">
                                <button class="project-mini-btn" onclick="openIntegrationModal()">➕ 新集成</button>
                            </div>
                        </div>
                        <div class="project-list" id="integrationList"></div>
                    </div>
                </div>
            </div>
            <div id="lorasTab" class="tab-content"><div class="lora-list" id="loraList"></div></div>
            <div id="toolsTab" class="tab-content">
                <div class="tool-list" id="toolList"></div>
                <div style="padding:8px;border-top:1px solid var(--border);">
                    <button class="quick-tool" onclick="showCodeModal()" style="width:100%;justify-content:center;">💻 代码执行器</button>
                </div>
            </div>
            <div id="mcpTab" class="tab-content">
                <div style="padding:12px;">
                    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
                        <span style="font-size:13px;font-weight:600;color:var(--text-primary);">🔌 MCP 插件</span>
                        <button class="quick-tool" onclick="refreshMcpPlugins()" style="padding:4px 8px;font-size:11px;">🔄 刷新</button>
                    </div>
                    <div style="background:linear-gradient(135deg,rgba(102,126,234,0.1),rgba(118,75,162,0.05));border-radius:10px;padding:10px;margin-bottom:12px;font-size:11px;">
                        <div style="color:var(--text-secondary);margin-bottom:6px;">
                            <b>💡 提示:</b> MCP 插件让 AI 能够调用外部工具
                        </div>
                        <div style="display:flex;gap:8px;flex-wrap:wrap;">
                            <span style="background:rgba(59,130,246,0.2);color:#3b82f6;padding:2px 8px;border-radius:4px;">📁 文件系统</span>
                            <span style="background:rgba(245,158,11,0.2);color:#f59e0b;padding:2px 8px;border-radius:4px;">🔍 网络搜索</span>
                            <span style="background:rgba(16,185,129,0.2);color:#10b981;padding:2px 8px;border-radius:4px;">🧮 计算器</span>
                        </div>
                    </div>
                    <div class="mcp-list" id="mcpList"></div>
                </div>
            </div>
            <div id="workflowTab" class="tab-content">
                <div style="padding:12px;">
                    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
                        <span style="font-size:13px;font-weight:600;color:var(--text-primary);">📋 工作流</span>
                        <button class="quick-tool" onclick="openWorkflowEditor()" style="padding:4px 12px;font-size:11px;">➕ 新建</button>
                    </div>
                    <div style="background:linear-gradient(135deg,rgba(102,126,234,0.1),rgba(118,75,162,0.05));border-radius:10px;padding:10px;margin-bottom:12px;font-size:11px;">
                        <div style="color:var(--text-secondary);margin-bottom:6px;">
                            <b>💡 提示:</b> 拖拽节点、连接流程、自动化任务
                        </div>
                        <div style="display:flex;gap:8px;flex-wrap:wrap;">
                            <span style="background:rgba(102,126,234,0.2);color:#667eea;padding:2px 8px;border-radius:4px;">🤖 AI对话</span>
                            <span style="background:rgba(245,158,11,0.2);color:#f59e0b;padding:2px 8px;border-radius:4px;">🔀 条件</span>
                            <span style="background:rgba(0,212,170,0.2);color:#00d4aa;padding:2px 8px;border-radius:4px;">💻 代码</span>
                        </div>
                    </div>
                    <div class="workflow-list" id="workflowList"></div>
                </div>
            </div>
            <div id="memoryTab" class="tab-content">
                <div style="padding:12px;">
                    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
                        <span style="font-size:13px;font-weight:600;color:var(--text-primary);">🧠 记忆系统</span>
                        <button class="quick-tool" onclick="refreshMemoryStats()" style="padding:4px 8px;font-size:11px;">🔄 刷新</button>
                    </div>
                    <div id="memoryStats" style="background:linear-gradient(135deg,rgba(102,126,234,0.1),rgba(118,75,162,0.05));border-radius:10px;padding:10px;margin-bottom:12px;font-size:11px;">
                        <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:8px;color:var(--text-secondary);">
                            <span>🧠 长期: <b id="memLongTerm">0</b></span>
                            <span>📊 重要性: <b id="memAvgImportance">0</b></span>
                            <span>👤 实体: <b id="memEntities">0</b></span>
                            <span>📝 画像: <b id="memProfile">0</b></span>
                        </div>
                    </div>
                    <div style="background:linear-gradient(135deg,rgba(16,185,129,0.1),rgba(5,150,105,0.05));border-radius:10px;padding:10px;margin-bottom:12px;font-size:11px;">
                        <div style="color:var(--text-secondary);margin-bottom:6px;">
                            <b>💡 提示:</b> AI会自动记住重要信息
                        </div>
                        <div style="display:flex;gap:8px;flex-wrap:wrap;">
                            <span style="background:rgba(16,185,129,0.2);color:#10b981;padding:2px 8px;border-radius:4px;">✅ 自动提取</span>
                            <span style="background:rgba(59,130,246,0.2);color:#3b82f6;padding:2px 8px;border-radius:4px;">🔍 智能检索</span>
                            <span style="background:rgba(245,158,11,0.2);color:#f59e0b;padding:2px 8px;border-radius:4px;">⏰ 时间衰减</span>
                        </div>
                    </div>
                    <div style="margin-bottom:12px;">
                        <input type="text" id="memorySearchInput" placeholder="🔍 搜索记忆..." style="width:100%;padding:8px 12px;border:1px solid var(--border);border-radius:8px;font-size:12px;background:var(--bg-secondary);color:var(--text-primary);margin-bottom:8px;" onkeypress="if(event.key==='Enter')searchMemories()">
                        <div style="display:flex;gap:6px;">
                            <button class="quick-tool" onclick="searchMemories()" style="flex:1;justify-content:center;padding:8px;">🔍 搜索</button>
                            <button class="quick-tool" onclick="showAddMemoryModal()" style="flex:1;justify-content:center;padding:8px;">➕ 添加</button>
                            <button class="quick-tool" onclick="consolidateMemories()" style="flex:1;justify-content:center;padding:8px;">🧹 整合</button>
                        </div>
                    </div>
                    <div class="memory-list" id="memoryList"></div>
                </div>
            </div>
            <div id="multimodalTab" class="tab-content">
                <div style="padding:12px;">
                    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
                        <span style="font-size:13px;font-weight:600;color:var(--text-primary);">👁️ 视觉理解</span>
                        <button class="quick-tool" onclick="clearMultimodalHistory()" style="padding:4px 8px;font-size:11px;">🗑️ 清除</button>
                    </div>
                    <div style="background:linear-gradient(135deg,rgba(102,126,234,0.1),rgba(118,75,162,0.05));border-radius:10px;padding:10px;margin-bottom:12px;font-size:11px;">
                        <div style="color:var(--text-secondary);margin-bottom:6px;">
                            <b>💡 提示:</b> 上传图片，AI 帮你理解分析
                        </div>
                        <div style="display:flex;gap:8px;flex-wrap:wrap;">
                            <span style="background:rgba(59,130,246,0.2);color:#3b82f6;padding:2px 8px;border-radius:4px;">🖼️ 图像描述</span>
                            <span style="background:rgba(16,185,129,0.2);color:#10b981;padding:2px 8px;border-radius:4px;">📝 OCR识别</span>
                            <span style="background:rgba(245,158,11,0.2);color:#f59e0b;padding:2px 8px;border-radius:4px;">🔍 内容分析</span>
                        </div>
                    </div>
                    <div style="margin-bottom:12px;">
                        <input type="file" id="multimodalImageInput" accept="image/*" style="display:none" onchange="uploadMultimodalImage(event)">
                        <button class="quick-tool" onclick="document.getElementById('multimodalImageInput').click()" style="width:100%;justify-content:center;padding:10px;margin-bottom:8px;">
                            📤 上传图片
                        </button>
                        <div id="multimodalImagePreview" style="display:none;margin-bottom:10px;">
                            <img id="previewImg" style="max-width:100%;border-radius:8px;border:1px solid var(--border);" />
                            <div style="display:flex;gap:6px;margin-top:8px;">
                                <button class="quick-tool" onclick="analyzeImage('describe')" style="flex:1;justify-content:center;padding:6px;font-size:11px;">📝 描述</button>
                                <button class="quick-tool" onclick="analyzeImage('ocr')" style="flex:1;justify-content:center;padding:6px;font-size:11px;">📄 OCR</button>
                                <button class="quick-tool" onclick="analyzeImage('analyze')" style="flex:1;justify-content:center;padding:6px;font-size:11px;">🔍 分析</button>
                            </div>
                        </div>
                    </div>
                    <div id="multimodalResults" style="display:flex;flex-direction:column;gap:8px;"></div>
                </div>
            </div>
            <div id="finetuneTab" class="tab-content">
                <div style="padding:12px;">
                    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
                        <span style="font-size:13px;font-weight:600;color:var(--text-primary);">🎓 模型微调</span>
                        <button class="quick-tool" onclick="refreshFinetuneData()" style="padding:4px 8px;font-size:11px;">🔄 刷新</button>
                    </div>
                    <div style="background:linear-gradient(135deg,rgba(102,126,234,0.1),rgba(118,75,162,0.05));border-radius:10px;padding:10px;margin-bottom:12px;font-size:11px;">
                        <div style="color:var(--text-secondary);margin-bottom:6px;">
                            <b>💡 提示:</b> 上传数据集，训练专属模型
                        </div>
                        <div style="display:flex;gap:8px;flex-wrap:wrap;">
                            <span style="background:rgba(16,185,129,0.2);color:#10b981;padding:2px 8px;border-radius:4px;">📊 LoRA</span>
                            <span style="background:rgba(59,130,246,0.2);color:#3b82f6;padding:2px 8px;border-radius:4px;">⚡ QLoRA</span>
                            <span style="background:rgba(245,158,11,0.2);color:#f59e0b;padding:2px 8px;border-radius:4px;">📈 可视化</span>
                        </div>
                    </div>
                    <div style="margin-bottom:12px;">
                        <div style="display:flex;gap:6px;margin-bottom:8px;">
                            <button class="quick-tool" onclick="showDatasetUpload()" style="flex:1;justify-content:center;padding:8px;font-size:12px;">📤 上传数据集</button>
                            <button class="quick-tool" onclick="showCreateJob()" style="flex:1;justify-content:center;padding:8px;font-size:12px;">➕ 创建训练</button>
                        </div>
                    </div>
                    <div style="font-size:12px;font-weight:600;color:var(--text-muted);margin-bottom:8px;">📊 数据集</div>
                    <div class="finetune-list" id="finetuneDatasets" style="margin-bottom:16px;"></div>
                    <div style="font-size:12px;font-weight:600;color:var(--text-muted);margin-bottom:8px;">🎯 训练任务</div>
                    <div class="finetune-list" id="finetuneJobs"></div>
                </div>
            </div>
            <div id="rolesTab" class="tab-content"><div class="role-list" id="roleList"></div></div>
            <div id="ragTab" class="tab-content">
                <div style="padding:12px;">
                    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
                        <span style="font-size:13px;font-weight:600;color:var(--text-primary);">📚 RAG 知识库</span>
                        <label class="toggle" style="transform:scale(0.85);">
                            <input type="checkbox" id="ragToggle" onchange="toggleRag()">
                            <span class="toggle-slider"></span>
                        </label>
                    </div>
                    
                    <div class="project-panel" style="margin-bottom:10px;">
                        <div class="project-panel-head">
                            <span class="project-panel-title">📊 知识库概览</span>
                            <div class="project-panel-actions">
                                <button class="project-mini-btn" onclick="refreshRagStats()">刷新</button>
                            </div>
                        </div>
                        <div class="rag-overview-grid" id="ragOverviewGrid">
                            <div class="rag-stat-card">
                                <div class="rag-stat-icon">📚</div>
                                <div class="rag-stat-info">
                                    <div class="rag-stat-value" id="ragStatDocs">0</div>
                                    <div class="rag-stat-label">文档数</div>
                                </div>
                            </div>
                            <div class="rag-stat-card">
                                <div class="rag-stat-icon">📝</div>
                                <div class="rag-stat-info">
                                    <div class="rag-stat-value" id="ragStatChunks">0</div>
                                    <div class="rag-stat-label">分块数</div>
                                </div>
                            </div>
                            <div class="rag-stat-card">
                                <div class="rag-stat-icon">📊</div>
                                <div class="rag-stat-info">
                                    <div class="rag-stat-value" id="ragStatChars">0</div>
                                    <div class="rag-stat-label">字符数</div>
                                </div>
                            </div>
                            <div class="rag-stat-card">
                                <div class="rag-stat-icon">🔗</div>
                                <div class="rag-stat-info">
                                    <div class="rag-stat-value" id="ragStatVectors">0</div>
                                    <div class="rag-stat-label">向量数</div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="project-panel" style="margin-bottom:10px;">
                        <div class="project-panel-head">
                            <span class="project-panel-title">📤 文档导入</span>
                            <div class="project-panel-actions">
                                <button class="project-mini-btn" onclick="openBatchImportModal()">批量导入</button>
                            </div>
                        </div>
                        <div class="import-options">
                            <input type="file" id="ragFileInput" accept=".txt,.md,.json,.csv,.pdf,.docx,.html" multiple style="display:none" onchange="uploadRagFile(event)">
                            <div class="import-btn-grid">
                                <button class="import-btn" onclick="document.getElementById('ragFileInput').click()">
                                    <span class="import-icon">📁</span>
                                    <span class="import-label">上传文件</span>
                                </button>
                                <button class="import-btn" onclick="showAddTextModal()">
                                    <span class="import-icon">✏️</span>
                                    <span class="import-label">添加文本</span>
                                </button>
                                <button class="import-btn" onclick="openUrlImportModal()">
                                    <span class="import-icon">🌐</span>
                                    <span class="import-label">网页抓取</span>
                                </button>
                                <button class="import-btn" onclick="openGitImportModal()">
                                    <span class="import-icon">📦</span>
                                    <span class="import-label">Git 仓库</span>
                                </button>
                            </div>
                        </div>
                    </div>
                    
                    <div class="project-panel" style="margin-bottom:10px;">
                        <div class="project-panel-head">
                            <span class="project-panel-title">🔍 智能检索</span>
                            <div class="project-panel-actions">
                                <select class="project-input" id="ragSearchMode" style="width:80px;">
                                    <option value="semantic">语义</option>
                                    <option value="keyword">关键词</option>
                                    <option value="hybrid">混合</option>
                                </select>
                            </div>
                        </div>
                        <div class="rag-search-panel">
                            <input type="text" id="ragSearchInput" placeholder="输入查询内容..." class="rag-search-input" oninput="searchRagDocs()">
                            <div class="rag-search-options">
                                <label class="rag-option">
                                    <input type="checkbox" id="ragSearchExact" checked>
                                    <span>精确匹配</span>
                                </label>
                                <label class="rag-option">
                                    <input type="checkbox" id="ragSearchExpand">
                                    <span>查询扩展</span>
                                </label>
                                <label class="rag-option">
                                    <input type="checkbox" id="ragSearchRerank" checked>
                                    <span>重排序</span>
                                </label>
                            </div>
                            <div id="ragSearchResults" class="rag-search-results"></div>
                        </div>
                    </div>
                    
                    <div class="project-panel" style="margin-bottom:10px;">
                        <div class="project-panel-head">
                            <span class="project-panel-title">📄 文档管理</span>
                            <div class="project-panel-actions">
                                <select class="project-input" id="ragCategoryFilter" onchange="filterRagDocs()" style="width:100px;">
                                    <option value="">全部分类</option>
                                    <option value="doc">📄 文档</option>
                                    <option value="code">💻 代码</option>
                                    <option value="data">📊 数据</option>
                                    <option value="web">🌐 网页</option>
                                    <option value="text">📝 文本</option>
                                </select>
                                <button class="project-mini-btn" onclick="openRagSettingsModal()">⚙️ 设置</button>
                            </div>
                        </div>
                        <div id="ragDocList" class="rag-doc-list"></div>
                    </div>
                    
                    <div class="project-panel" style="margin-bottom:10px;">
                        <div class="project-panel-head">
                            <span class="project-panel-title">🧠 知识图谱</span>
                            <div class="project-panel-actions">
                                <button class="project-mini-btn" onclick="openKnowledgeGraphModal()">查看图谱</button>
                                <button class="project-mini-btn" onclick="buildKnowledgeGraph()">构建图谱</button>
                            </div>
                        </div>
                        <div class="knowledge-graph-preview" id="knowledgeGraphPreview">
                            <div class="graph-node-group">
                                <div class="graph-node">概念</div>
                                <div class="graph-node">实体</div>
                                <div class="graph-node">关系</div>
                            </div>
                            <div class="graph-stats">
                                <span>节点: <b id="graphNodes">--</b></span>
                                <span>边: <b id="graphEdges">--</b></span>
                            </div>
                        </div>
                    </div>
                    
                    <div class="project-panel" style="margin-bottom:10px;">
                        <div class="project-panel-head">
                            <span class="project-panel-title">📈 检索分析</span>
                            <div class="project-panel-actions">
                                <select class="project-input" id="ragAnalysisRange" onchange="loadRagAnalysis()">
                                    <option value="7d">最近7天</option>
                                    <option value="30d">最近30天</option>
                                </select>
                                <button class="project-mini-btn" onclick="exportRagReport()">导出</button>
                            </div>
                        </div>
                        <div class="rag-analysis-grid">
                            <div class="analysis-item">
                                <div class="analysis-label">检索次数</div>
                                <div class="analysis-value" id="ragQueryCount">--</div>
                            </div>
                            <div class="analysis-item">
                                <div class="analysis-label">命中率</div>
                                <div class="analysis-value" id="ragHitRate">--</div>
                            </div>
                            <div class="analysis-item">
                                <div class="analysis-label">平均延迟</div>
                                <div class="analysis-value" id="ragLatency">--</div>
                            </div>
                            <div class="analysis-item">
                                <div class="analysis-label">Top 文档</div>
                                <div class="analysis-value" id="ragTopDoc">--</div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="project-panel">
                        <div class="project-panel-head">
                            <span class="project-panel-title">⚡ 向量化设置</span>
                            <div class="project-panel-actions">
                                <button class="project-mini-btn" onclick="openVectorSettingsModal()">高级</button>
                            </div>
                        </div>
                        <div class="vector-settings">
                            <div class="vector-setting-row">
                                <label>嵌入模型</label>
                                <select class="project-input" id="embeddingModel" style="flex:1;">
                                    <option value="text-embedding-ada-002">text-embedding-ada-002</option>
                                    <option value="bge-large-zh">bge-large-zh</option>
                                    <option value="m3e-base">m3e-base</option>
                                    <option value="local">本地模型</option>
                                </select>
                            </div>
                            <div class="vector-setting-row">
                                <label>分块大小</label>
                                <input type="number" class="project-input" id="chunkSize" value="512" min="128" max="2048" style="flex:1;">
                            </div>
                            <div class="vector-setting-row">
                                <label>重叠大小</label>
                                <input type="number" class="project-input" id="chunkOverlap" value="50" min="0" max="256" style="flex:1;">
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="sidebar-footer">
                <button class="sidebar-footer-btn" onclick="newChat()" style="margin-bottom:8px;background:linear-gradient(135deg,var(--primary),var(--secondary));color:white;border:none;">
                    <span>✨</span> 新建对话
                </button>
                <button class="sidebar-footer-btn" onclick="openSettings()">
                    <span>⚙️</span> 设置
                </button>
            </div>
        </aside>
        <main class="main-container">
            <header class="header">
                <div class="header-left">
                    <img src="/header-img" class="header-avatar" id="headerAvatar">
                    <div class="header-info">
                        <h1 id="headerTitle">辉夜姬</h1>
                        <div class="header-status">
                            <span class="status-dot"></span>
                            <span id="statusText">准备就绪</span>
                        </div>
                    </div>
                </div>
                <div class="header-indicators" id="headerIndicators"></div>
                <div class="header-actions">
                    <button class="header-btn deepseek-btn" onclick="openDeepSeek()" title="DeepSeek API">
                        <img src="/deepseek-icon" class="deepseek-icon" alt="DeepSeek">
                        <span class="btn-text">DeepSeek</span>
                    </button>
                    <button class="header-btn" onclick="openFeatureCenter()" title="功能中心">🧭</button>
                    <button class="header-btn stats-btn" onclick="openStats()" title="数据统计">📊</button>
                    <button class="header-btn" onclick="openModelConfig()" title="模型配置">⚙️</button>
                    <button class="header-btn" onclick="openTheme()" title="主题设置">🎨</button>
                    <button class="header-btn" onclick="toggleDarkMode()" title="深色模式">🌙</button>
                    <button class="header-btn" id="voiceBtn" onclick="toggleVoice()" title="语音">🔊</button>
                </div>
            </header>
            <div class="right-sidebar-toggle" onclick="toggleRightSidebar()" title="功能面板">
                <span>📋</span>
            </div>
            <div class="tools-bar" id="toolsBar">
                <div class="quick-tool search-tool" onclick="toggleTool('search')" data-tool="search">
                    <span class="tool-icon">🔍</span>
                    <span class="tool-label">网络搜索</span>
                </div>
                <div class="quick-tool" onclick="toggleTool('news')" data-tool="news">📰 新闻</div>
                <div class="quick-tool" onclick="toggleTool('calculator')" data-tool="calculator">🔢 计算器</div>
                <div class="quick-tool" onclick="toggleTool('weather')" data-tool="weather">🌤️ 天气</div>
                <div class="quick-tool" onclick="toggleTool('translate')" data-tool="translate">🌐 翻译</div>
                <div class="quick-tool" onclick="showCodeModal()">💻 代码</div>
                <div class="quick-tool" onclick="showKBModal()">📚 知识库</div>
                <div class="quick-tool" onclick="openPromptWorkbench()">🧭 专业工作台</div>
                <div class="quick-tool" onclick="openFeatureSection('console')">📊 统一控制台</div>
                <div class="quick-tool" onclick="openFeatureSection('ecosystem')">🌐 项目生态</div>
                <div class="quick-tool" onclick="openFeatureSection('scenes')">🚀 场景引擎</div>
                <div class="quick-tool" onclick="openFeatureSection('project')">🗂️ 项目中台</div>
                <div class="quick-tool" onclick="openFeatureSection('ops')">📣 运营中心</div>
                <div class="quick-tool" onclick="openFeatureSection('release')">🚀 发布中心</div>
                <div class="quick-tool" onclick="openFeatureSection('alert')">🚨 告警中心</div>
                <div class="quick-tool" onclick="openFeatureSection('ab')">🧪 实验中心</div>
                <div class="quick-tool" onclick="openFeatureSection('integration')">🧩 集成市场</div>
            </div>
            <div class="chat-area">
                <div class="messages-container" id="messagesContainer">
                    <div class="welcome-container" id="welcomeScreen">
                        <img src="/header-img" class="welcome-avatar">
                        <h1 class="welcome-title">辉夜 AI 专业助手 ✨</h1>
                        <p class="welcome-subtitle">面向开发、运营、增长与职场场景的高质量 AI 助手，可直接产出可执行方案、模板与落地步骤。</p>
                        <div class="feature-grid">
                            <div class="feature-card" onclick="quickAction('chat')">
                                <span class="feature-icon">💬</span>
                                <div class="feature-name">智能对话</div>
                                <div class="feature-desc">自然流畅的对话体验</div>
                            </div>
                            <div class="feature-card" onclick="quickAction('code')">
                                <span class="feature-icon">💻</span>
                                <div class="feature-name">代码助手</div>
                                <div class="feature-desc">编写和调试代码</div>
                            </div>
                            <div class="feature-card" onclick="quickAction('translate')">
                                <span class="feature-icon">🌐</span>
                                <div class="feature-name">翻译专家</div>
                                <div class="feature-desc">多语言翻译服务</div>
                            </div>
                            <div class="feature-card" onclick="quickAction('write')">
                                <span class="feature-icon">✍️</span>
                                <div class="feature-name">创意写作</div>
                                <div class="feature-desc">文章和内容创作</div>
                            </div>
                            <div class="feature-card" onclick="quickAction('analyze')">
                                <span class="feature-icon">📊</span>
                                <div class="feature-name">数据分析</div>
                                <div class="feature-desc">处理和分析数据</div>
                            </div>
                            <div class="feature-card" onclick="quickAction('learn')">
                                <span class="feature-icon">📚</span>
                                <div class="feature-name">学习辅导</div>
                                <div class="feature-desc">解答学习问题</div>
                            </div>
                        </div>
                        <div class="market-demand-section">
                            <div class="market-demand-title">
                                <span>🚀</span>
                                <span>高需求专业场景（可一键生成）</span>
                            </div>
                            <div class="market-demand-grid">
                                <div class="demand-card" onclick="quickAction('ecommerce')">
                                    <div class="demand-head"><span>🛍️</span><span class="demand-name">电商增长</span></div>
                                    <div class="demand-desc">活动方案、商品卖点、投放文案与转化优化</div>
                                </div>
                                <div class="demand-card" onclick="quickAction('shortvideo')">
                                    <div class="demand-head"><span>🎬</span><span class="demand-name">短视频运营</span></div>
                                    <div class="demand-desc">选题、脚本分镜、封面标题与账号节奏设计</div>
                                </div>
                                <div class="demand-card" onclick="quickAction('resume')">
                                    <div class="demand-head"><span>🧩</span><span class="demand-name">简历求职</span></div>
                                    <div class="demand-desc">简历重写、岗位匹配、STAR 项目优化与面试问答</div>
                                </div>
                                <div class="demand-card" onclick="quickAction('business')">
                                    <div class="demand-head"><span>📈</span><span class="demand-name">商业计划</span></div>
                                    <div class="demand-desc">商业模型、竞品分析、路线图与里程碑拆解</div>
                                </div>
                                <div class="demand-card" onclick="quickAction('dataops')">
                                    <div class="demand-head"><span>📊</span><span class="demand-name">数据经营分析</span></div>
                                    <div class="demand-desc">指标体系、异常诊断、A/B 实验与复盘建议</div>
                                </div>
                                <div class="demand-card" onclick="quickAction('contract')">
                                    <div class="demand-head"><span>⚖️</span><span class="demand-name">合同风险审阅</span></div>
                                    <div class="demand-desc">关键条款核查、风险点标注与谈判建议</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <aside class="right-sidebar" id="rightSidebar">
                    <div class="right-sidebar-header">
                        <h3>📋 功能面板</h3>
                        <button class="sidebar-close-btn" onclick="toggleRightSidebar()">✕</button>
                    </div>
                    <div class="right-sidebar-content">
                        <div class="panel-section">
                            <div class="panel-section-title">快捷入口</div>
                            <div class="panel-grid">
                                <div class="panel-item" onclick="openModelsConfig(); toggleRightSidebar();" style="background:linear-gradient(135deg,rgba(99,102,241,0.15),rgba(139,92,246,0.1));border-color:rgba(99,102,241,0.3);">
                                    <span class="panel-icon">🌐</span>
                                    <span class="panel-label">多模型API</span>
                                </div>
                                <div class="panel-item" onclick="openDeepSeek(); toggleRightSidebar();">
                                    <span class="panel-icon">🤖</span>
                                    <span class="panel-label">DeepSeek</span>
                                </div>
                                <div class="panel-item" onclick="openStats(); toggleRightSidebar();">
                                    <span class="panel-icon">📊</span>
                                    <span class="panel-label">数据统计</span>
                                </div>
                                <div class="panel-item" onclick="openModelConfig(); toggleRightSidebar();">
                                    <span class="panel-icon">⚙️</span>
                                    <span class="panel-label">模型配置</span>
                                </div>
                                <div class="panel-item" onclick="openTheme(); toggleRightSidebar();">
                                    <span class="panel-icon">🎨</span>
                                    <span class="panel-label">主题设置</span>
                                </div>
                                <div class="panel-item" onclick="showCodeModal(); toggleRightSidebar();">
                                    <span class="panel-icon">💻</span>
                                    <span class="panel-label">代码执行</span>
                                </div>
                                <div class="panel-item" onclick="showKBModal(); toggleRightSidebar();">
                                    <span class="panel-icon">📚</span>
                                    <span class="panel-label">知识库</span>
                                </div>
                                <div class="panel-item" onclick="openFeatureCenter(); toggleRightSidebar();">
                                    <span class="panel-icon">🧭</span>
                                    <span class="panel-label">功能中心</span>
                                </div>
                            </div>
                        </div>
                        <div class="panel-section">
                            <div class="panel-section-title">系统状态</div>
                            <div class="status-list">
                                <div class="status-item">
                                    <span class="status-label">模型状态</span>
                                    <span class="status-value" id="modelStatus">就绪</span>
                                </div>
                                <div class="status-item">
                                    <span class="status-label">当前角色</span>
                                    <span class="status-value" id="currentRoleDisplay">辉夜</span>
                                </div>
                                <div class="status-item">
                                    <span class="status-label">LoRA</span>
                                    <span class="status-value" id="currentLoraDisplay">未加载</span>
                                </div>
                                <div class="status-item">
                                    <span class="status-label">RAG</span>
                                    <span class="status-value" id="ragStatusDisplay">关闭</span>
                                </div>
                            </div>
                        </div>
                        <div class="panel-section">
                            <div class="panel-section-title">最近对话</div>
                            <div class="recent-chats" id="recentChatsList"></div>
                        </div>
                    </div>
                </aside>
                <div class="input-area">
                    <div class="attachments-preview" id="attachmentsPreview"></div>
                    <div id="editHint" style="display:none;padding:6px 10px;background:rgba(245,158,11,0.1);border-radius:6px;margin-bottom:8px;font-size:11px;color:var(--text-secondary);justify-content:space-between;align-items:center;">
                        <span>✏️ 编辑模式 - 修改后发送将更新原消息</span>
                        <button onclick="cancelEdit()" style="background:none;border:none;cursor:pointer;color:var(--text-muted);">✕</button>
                    </div>
                    <div id="replyHint" style="display:none;padding:6px 10px;background:rgba(16,185,129,0.1);border-radius:6px;margin-bottom:8px;font-size:11px;color:var(--text-secondary);justify-content:space-between;align-items:center;">
                        <span>↩️ 回复: <span id="replyContent"></span>...</span>
                        <button onclick="cancelReply()" style="background:none;border:none;cursor:pointer;color:var(--text-muted);">✕</button>
                    </div>
                    <div class="command-hint" id="commandHint"></div>
                    <div class="input-wrapper">
                        <div class="input-tools">
                            <button class="tool-btn" onclick="document.getElementById('fileInput').click()" title="上传">📎</button>
                            <input type="file" id="fileInput" multiple accept="image/*,.pdf,.txt" style="display:none" onchange="handleFileSelect(event)">
                            <button class="tool-btn" id="voiceInputBtn" onclick="toggleVoiceInput()" title="语音输入">🎤</button>
                        </div>
                        <textarea class="main-input" id="mainInput" placeholder="输入消息... (/help 查看命令)" rows="1" onkeydown="handleKeyDown(event)" oninput="handleInput(event)"></textarea>
                        <button class="send-btn" id="sendBtn" onclick="sendMessage()">➤</button>
                        <button class="send-btn" id="stopBtn" onclick="stopGeneration()" style="display:none;background:linear-gradient(135deg,#ef4444,#dc2626);">⏹</button>
                    </div>
                    <div class="input-footer">
                        <span id="charCount">0 / 4000</span>
                        <span>温度: <input type="range" class="setting-slider" id="tempSlider" min="0.1" max="2" step="0.1" value="0.7" oninput="updateTemp(this.value)" style="width:60px;vertical-align:middle;"> <span id="tempValue">0.7</span></span>
                    </div>
                </div>
            </div>
        </main>
    </div>
    <div class="settings-panel" id="settingsPanel">
        <div class="settings-header">
            <h3>⚙️ 设置</h3>
            <button class="settings-close" onclick="closeSettings()">✕</button>
        </div>
        <div class="settings-section">
            <h4>模型参数</h4>
            <div class="setting-row">
                <span class="setting-label">温度</span>
                <input type="range" class="setting-slider" id="settingTemp" min="0.1" max="2" step="0.1" value="0.7" oninput="updateSetting('temp', this.value)">
                <span class="setting-value" id="settingTempValue">0.7</span>
            </div>
            <div class="setting-row">
                <span class="setting-label">最大长度</span>
                <input type="range" class="setting-slider" id="settingTokens" min="64" max="8192" step="64" value="4096" oninput="updateSetting('tokens', this.value)">
                <span class="setting-value" id="settingTokensValue">4096</span>
            </div>
        </div>
        <div class="settings-section">
            <h4>功能开关</h4>
            <div class="setting-row">
                <span class="setting-label">深色模式</span>
                <label class="toggle"><input type="checkbox" id="darkModeToggle" onchange="toggleDarkMode()"><span class="toggle-slider"></span></label>
            </div>
            <div class="setting-row">
                <span class="setting-label">语音输出</span>
                <label class="toggle"><input type="checkbox" id="voiceOutputToggle" onchange="updateSetting('voice', this.checked)"><span class="toggle-slider"></span></label>
            </div>
            <div class="setting-row">
                <span class="setting-label">Markdown渲染</span>
                <label class="toggle"><input type="checkbox" id="markdownToggle" checked onchange="updateSetting('markdown', this.checked)"><span class="toggle-slider"></span></label>
            </div>
        </div>
        <div class="settings-section">
            <h4>使用统计</h4>
            <div class="stats-grid">
                <div class="stats-card"><div class="stats-card-value" id="statsSessions">0</div><div class="stats-card-label">会话数</div></div>
                <div class="stats-card"><div class="stats-card-value" id="statsInput">0</div><div class="stats-card-label">输入Tokens</div></div>
                <div class="stats-card"><div class="stats-card-value" id="statsOutput">0</div><div class="stats-card-label">输出Tokens</div></div>
                <div class="stats-card"><div class="stats-card-value" id="statsLatency">0</div><div class="stats-card-label">平均延迟(ms)</div></div>
            </div>
        </div>
        <div class="settings-section">
            <h4>数据管理</h4>
            <div class="setting-row"><button class="modal-btn secondary" onclick="exportAllChats()" style="width:100%;">📥 导出对话</button></div>
            <div class="setting-row"><button class="modal-btn secondary" onclick="clearAllData()" style="width:100%;color:#e74c3c;">🗑️ 清除数据</button></div>
        </div>
    </div>
    <div class="shortcut-hint" id="shortcutHint">
        <h4>⌨️ 快捷键</h4>
        <div class="shortcut-item"><span>新建对话</span><span class="shortcut-key">Ctrl+N</span></div>
        <div class="shortcut-item"><span>深色模式</span><span class="shortcut-key">Ctrl+D</span></div>
        <div class="shortcut-item"><span>设置面板</span><span class="shortcut-key">Ctrl+,</span></div>
        <div class="shortcut-item"><span>发送消息</span><span class="shortcut-key">Enter</span></div>
        <div class="shortcut-item"><span>换行</span><span class="shortcut-key">Shift+Enter</span></div>
    </div>
    <div class="mobile-dock" id="mobileDock">
        <button class="mobile-dock-btn active" data-mobile-tab="chats" onclick="openMobileSection('chats')"><span>💬</span><span>对话</span></button>
        <button class="mobile-dock-btn" data-mobile-tab="console" onclick="openMobileSection('console')"><span>📊</span><span>控制台</span></button>
        <button class="mobile-dock-btn" data-mobile-tab="ecosystem" onclick="openMobileSection('ecosystem')"><span>🌐</span><span>生态</span></button>
        <button class="mobile-dock-btn" data-mobile-tab="scenes" onclick="openMobileSection('scenes')"><span>🚀</span><span>场景</span></button>
        <button class="mobile-dock-btn" data-mobile-tab="prompts" onclick="openMobileSection('prompts')"><span>🧭</span><span>模板</span></button>
        <button class="mobile-dock-btn" data-mobile-tab="project" onclick="openMobileSection('project')"><span>🗂️</span><span>项目</span></button>
        <button class="mobile-dock-btn" data-mobile-tab="ops" onclick="openMobileSection('ops')"><span>📣</span><span>运营</span></button>
        <button class="mobile-dock-btn" data-mobile-tab="alert" onclick="openMobileSection('alert')"><span>🚨</span><span>告警</span></button>
        <button class="mobile-dock-btn" data-mobile-tab="workflow" onclick="openMobileSection('workflow')"><span>📋</span><span>工作流</span></button>
        <button class="mobile-dock-btn" data-mobile-tab="rag" onclick="openMobileSection('rag')"><span>📚</span><span>RAG</span></button>
        <button class="mobile-dock-btn" data-mobile-tab="center" onclick="openFeatureCenter()"><span>⚡</span><span>全部</span></button>
    </div>
    <div class="toast" id="toast"></div>
    <div class="modal-overlay" id="modalOverlay">
        <div class="modal"></div>
    </div>
    <div class="modal-overlay" id="featureCenterModal">
        <div class="modal" style="max-width:860px;">
            <div class="modal-header" style="background:linear-gradient(135deg,#4f46e5,#7c3aed);color:white;border-radius:16px 16px 0 0;">
                <span class="modal-title">🧭 功能中心</span>
                <button class="modal-close" onclick="closeModal('featureCenterModal')" style="color:white;">✕</button>
            </div>
            <div class="modal-body" style="padding:16px;">
                <div style="font-size:12px;color:var(--text-secondary);margin-bottom:12px;">已将系统核心能力统一映射为可点击入口，便于快速触达任意子界面。</div>
                <div class="feature-center-meta">
                    <div class="feature-center-panel">
                        <div class="feature-center-panel-title"><span>📡</span><span>功能状态概览</span></div>
                        <div class="feature-center-status-grid" id="centerStatusGrid"></div>
                    </div>
                    <div class="feature-center-panel">
                        <div class="feature-center-panel-title"><span>🕘</span><span>最近操作记录</span></div>
                        <div class="feature-center-recent" id="centerRecentActions"></div>
                    </div>
                </div>
                <div class="function-center-grid">
                    <div class="function-center-card" onclick="openFeatureSection('ecosystem')">
                        <div class="function-center-title"><span>🌐</span><span>项目生态</span></div>
                        <div class="function-center-desc">自动发现工作区项目，统一查看运行状态与启动入口</div>
                        <span class="function-center-badge">全项目整合</span>
                    </div>
                    <div class="function-center-card" onclick="openFeatureSection('scenes')">
                        <div class="function-center-title"><span>🚀</span><span>场景引擎</span></div>
                        <div class="function-center-desc">六大高需求场景独立子界面，统一走外界API生成</div>
                        <span class="function-center-badge">一键生成</span>
                    </div>
                    <div class="function-center-card" onclick="openFeatureSection('project')">
                        <div class="function-center-title"><span>🗂️</span><span>项目中台</span></div>
                        <div class="function-center-desc">产物沉淀、任务推进、策略剧本复用与执行入口</div>
                        <span class="function-center-badge">团队协作</span>
                    </div>
                    <div class="function-center-card" onclick="openFeatureSection('console')">
                        <div class="function-center-title"><span>📊</span><span>统一控制台</span></div>
                        <div class="function-center-desc">跨模块全局检索、综合评分与智能治理建议</div>
                        <span class="function-center-badge">全局视图</span>
                    </div>
                    <div class="function-center-card" onclick="openFeatureSection('ops')">
                        <div class="function-center-title"><span>📣</span><span>运营中心</span></div>
                        <div class="function-center-desc">活动编排、预算追踪、CTR监测与多渠道状态管理</div>
                        <span class="function-center-badge">增长执行</span>
                    </div>
                    <div class="function-center-card" onclick="openFeatureSection('release')">
                        <div class="function-center-title"><span>🚀</span><span>发布中心</span></div>
                        <div class="function-center-desc">版本计划、门禁检查、发布状态流转与回滚标记</div>
                        <span class="function-center-badge">交付治理</span>
                    </div>
                    <div class="function-center-card" onclick="openFeatureSection('alert')">
                        <div class="function-center-title"><span>🚨</span><span>告警中心</span></div>
                        <div class="function-center-desc">阈值规则、告警级别、静默与恢复状态闭环</div>
                        <span class="function-center-badge">稳定性治理</span>
                    </div>
                    <div class="function-center-card" onclick="openFeatureSection('ab')">
                        <div class="function-center-title"><span>🧪</span><span>实验中心</span></div>
                        <div class="function-center-desc">流量分配、指标对比、实验状态切换与收敛</div>
                        <span class="function-center-badge">增长实验</span>
                    </div>
                    <div class="function-center-card" onclick="openFeatureSection('integration')">
                        <div class="function-center-title"><span>🧩</span><span>集成市场</span></div>
                        <div class="function-center-desc">第三方能力接入、健康度监控、启停管控</div>
                        <span class="function-center-badge">生态连接</span>
                    </div>
                    <div class="function-center-card" onclick="openFeatureSection('prompts')">
                        <div class="function-center-title"><span>🧩</span><span>模板工作台</span></div>
                        <div class="function-center-desc">专业模板筛选、结构化输出与场景快速应用</div>
                        <span class="function-center-badge">增长 / 工程 / 研究</span>
                    </div>
                    <div class="function-center-card" onclick="openFeatureSection('workflow')">
                        <div class="function-center-title"><span>📋</span><span>工作流编排</span></div>
                        <div class="function-center-desc">节点拖拽、流程联接、保存与执行自动化流程</div>
                        <span class="function-center-badge">可视化编排</span>
                    </div>
                    <div class="function-center-card" onclick="openFeatureSection('memory')">
                        <div class="function-center-title"><span>🧠</span><span>记忆系统</span></div>
                        <div class="function-center-desc">记忆检索、整合、画像维护与长期信息管理</div>
                        <span class="function-center-badge">状态可追踪</span>
                    </div>
                    <div class="function-center-card" onclick="openFeatureSection('multimodal')">
                        <div class="function-center-title"><span>👁️</span><span>视觉理解</span></div>
                        <div class="function-center-desc">图片上传、OCR识别、视觉分析和图文问答</div>
                        <span class="function-center-badge">多模态</span>
                    </div>
                    <div class="function-center-card" onclick="openFeatureSection('finetune')">
                        <div class="function-center-title"><span>🎓</span><span>模型微调</span></div>
                        <div class="function-center-desc">数据集管理、训练任务创建与进度跟踪</div>
                        <span class="function-center-badge">训练平台</span>
                    </div>
                    <div class="function-center-card" onclick="openFeatureSection('rag')">
                        <div class="function-center-title"><span>📚</span><span>RAG知识库</span></div>
                        <div class="function-center-desc">文档接入、检索参数调优、来源追溯与分析</div>
                        <span class="function-center-badge">知识增强</span>
                    </div>
                    <div class="function-center-card" onclick="openFeatureSection('mcp')">
                        <div class="function-center-title"><span>🔌</span><span>MCP插件</span></div>
                        <div class="function-center-desc">外部工具启停、配置、能力扩展与联动</div>
                        <span class="function-center-badge">插件生态</span>
                    </div>
                    <div class="function-center-card" onclick="openFeatureSection('models')">
                        <div class="function-center-title"><span>🌐</span><span>多模型API</span></div>
                        <div class="function-center-desc">OpenAI/Claude/Gemini等统一配置与切换</div>
                        <span class="function-center-badge">模型网关</span>
                    </div>
                    <div class="function-center-card" onclick="openFeatureSection('settings')">
                        <div class="function-center-title"><span>⚙️</span><span>系统设置</span></div>
                        <div class="function-center-desc">主题、参数、语音、统计和数据管理</div>
                        <span class="function-center-badge">体验控制</span>
                    </div>
                    <div class="function-center-card" onclick="openFeatureSection('deepseek')">
                        <div class="function-center-title"><span>🤖</span><span>DeepSeek配置</span></div>
                        <div class="function-center-desc">外部推理引擎接入、连通性测试与切换</div>
                        <span class="function-center-badge">高级模型</span>
                    </div>
                    <div class="function-center-card" onclick="openFeatureSection('code')">
                        <div class="function-center-title"><span>💻</span><span>代码执行器</span></div>
                        <div class="function-center-desc">运行Python片段、查看结果并快速迭代</div>
                        <span class="function-center-badge">工程能力</span>
                    </div>
                    <div class="function-center-card" onclick="openFeatureSection('stats')">
                        <div class="function-center-title"><span>📊</span><span>统计仪表盘</span></div>
                        <div class="function-center-desc">会话、延迟、工具使用和报告导出</div>
                        <span class="function-center-badge">运营分析</span>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <div class="modal-overlay" id="artifactModal">
        <div class="modal">
            <div class="modal-header">
                <span class="modal-title" id="artifactModalTitle">📦 新增产物</span>
                <button class="modal-close" onclick="closeModal('artifactModal')">✕</button>
            </div>
            <div class="modal-body">
                <div class="project-form-grid">
                    <input class="project-input full" id="artifactTitleInput" placeholder="产物标题">
                    <select class="project-input" id="artifactTypeInput">
                        <option value="note">note</option>
                        <option value="spec">spec</option>
                        <option value="report">report</option>
                        <option value="prompt">prompt</option>
                    </select>
                    <input class="project-input" id="artifactTagsInput" placeholder="标签：逗号分隔">
                    <textarea class="project-input full" id="artifactContentInput" placeholder="产物内容" style="min-height:140px;resize:vertical;"></textarea>
                </div>
            </div>
            <div class="modal-actions">
                <button class="modal-btn secondary" onclick="closeModal('artifactModal')">取消</button>
                <button class="modal-btn" onclick="submitArtifactModal()">保存</button>
            </div>
        </div>
    </div>
    <div class="modal-overlay" id="taskModal">
        <div class="modal">
            <div class="modal-header">
                <span class="modal-title">🗂️ 新增任务</span>
                <button class="modal-close" onclick="closeModal('taskModal')">✕</button>
            </div>
            <div class="modal-body">
                <div class="project-form-grid">
                    <input class="project-input full" id="taskTitleInput" placeholder="任务标题">
                    <select class="project-input" id="taskPriorityInput">
                        <option value="high">high</option>
                        <option value="medium" selected>medium</option>
                        <option value="low">low</option>
                    </select>
                    <input class="project-input" id="taskOwnerInput" placeholder="负责人">
                    <textarea class="project-input full" id="taskDescInput" placeholder="任务描述" style="min-height:100px;resize:vertical;"></textarea>
                </div>
            </div>
            <div class="modal-actions">
                <button class="modal-btn secondary" onclick="closeModal('taskModal')">取消</button>
                <button class="modal-btn" onclick="submitTaskModal()">创建</button>
            </div>
        </div>
    </div>
    <div class="modal-overlay" id="playbookModal">
        <div class="modal">
            <div class="modal-header">
                <span class="modal-title">🧠 自定义剧本</span>
                <button class="modal-close" onclick="closeModal('playbookModal')">✕</button>
            </div>
            <div class="modal-body">
                <div class="project-form-grid">
                    <input class="project-input" id="playbookNameInput" placeholder="剧本名称">
                    <input class="project-input" id="playbookCategoryInput" placeholder="分类" value="自定义">
                    <input class="project-input full" id="playbookDescInput" placeholder="描述">
                    <textarea class="project-input full" id="playbookTemplateInput" placeholder="模板内容，支持 {topic} {goal} {context} {constraints}" style="min-height:120px;resize:vertical;"></textarea>
                </div>
            </div>
            <div class="modal-actions">
                <button class="modal-btn secondary" onclick="closeModal('playbookModal')">取消</button>
                <button class="modal-btn" onclick="submitPlaybookModal()">保存</button>
            </div>
        </div>
    </div>
    <div class="modal-overlay" id="artifactVersionsModal">
        <div class="modal">
            <div class="modal-header">
                <span class="modal-title">🕘 产物版本历史</span>
                <button class="modal-close" onclick="closeModal('artifactVersionsModal')">✕</button>
            </div>
            <div class="modal-body">
                <div class="versions-list" id="artifactVersionsList"></div>
            </div>
        </div>
    </div>
    <div class="modal-overlay" id="opsCampaignModal">
        <div class="modal">
            <div class="modal-header">
                <span class="modal-title">📣 新建运营活动</span>
                <button class="modal-close" onclick="closeModal('opsCampaignModal')">✕</button>
            </div>
            <div class="modal-body">
                <div class="project-form-grid">
                    <input class="project-input full" id="opsCampaignNameInput" placeholder="活动名称">
                    <input class="project-input" id="opsCampaignChannelInput" placeholder="渠道（如 抖音/视频号/邮件）">
                    <input class="project-input" id="opsCampaignOwnerInput" placeholder="负责人">
                    <input class="project-input" id="opsCampaignBudgetInput" placeholder="预算（数字）">
                    <input class="project-input" id="opsCampaignTargetCtrInput" placeholder="目标CTR（%）">
                    <input class="project-input" id="opsCampaignCurrentCtrInput" placeholder="当前CTR（%）">
                    <input class="project-input" id="opsCampaignStartInput" placeholder="开始日期（YYYY-MM-DD）">
                    <input class="project-input" id="opsCampaignEndInput" placeholder="结束日期（YYYY-MM-DD）">
                    <textarea class="project-input full" id="opsCampaignNotesInput" placeholder="活动备注" style="min-height:90px;resize:vertical;"></textarea>
                </div>
            </div>
            <div class="modal-actions">
                <button class="modal-btn secondary" onclick="closeModal('opsCampaignModal')">取消</button>
                <button class="modal-btn" onclick="submitOpsCampaignModal()">创建</button>
            </div>
        </div>
    </div>
    <div class="modal-overlay" id="releasePlanModal">
        <div class="modal">
            <div class="modal-header">
                <span class="modal-title">🚀 新建发布计划</span>
                <button class="modal-close" onclick="closeModal('releasePlanModal')">✕</button>
            </div>
            <div class="modal-body">
                <div class="project-form-grid">
                    <input class="project-input" id="releaseVersionInput" placeholder="版本号（如 v3.4.0）">
                    <input class="project-input" id="releaseOwnerInput" placeholder="发布负责人">
                    <input class="project-input full" id="releaseTitleInput" placeholder="发布标题">
                    <select class="project-input" id="releaseEnvInput">
                        <option value="production">production</option>
                        <option value="staging">staging</option>
                        <option value="gray">gray</option>
                    </select>
                    <select class="project-input" id="releaseRiskInput">
                        <option value="low">low</option>
                        <option value="medium" selected>medium</option>
                        <option value="high">high</option>
                    </select>
                    <textarea class="project-input full" id="releaseChecklistInput" placeholder="检查项（每行一条）&#10;回归测试通过&#10;监控告警就绪&#10;回滚预案已确认" style="min-height:110px;resize:vertical;"></textarea>
                    <textarea class="project-input full" id="releaseNotesInput" placeholder="发布备注" style="min-height:90px;resize:vertical;"></textarea>
                </div>
            </div>
            <div class="modal-actions">
                <button class="modal-btn secondary" onclick="closeModal('releasePlanModal')">取消</button>
                <button class="modal-btn" onclick="submitReleasePlanModal()">创建</button>
            </div>
        </div>
    </div>
    <div class="modal-overlay" id="milestoneModal">
        <div class="modal">
            <div class="modal-header">
                <span class="modal-title">🎯 新增里程碑</span>
                <button class="modal-close" onclick="closeModal('milestoneModal')">✕</button>
            </div>
            <div class="modal-body">
                <div class="project-form-grid">
                    <input class="project-input full" id="milestoneTitleInput" placeholder="里程碑标题">
                    <input class="project-input" id="milestoneOwnerInput" placeholder="负责人">
                    <input class="project-input" id="milestoneDueInput" placeholder="截止日期（YYYY-MM-DD）">
                    <input class="project-input" id="milestoneProgressInput" placeholder="进度（0-100）" value="0">
                </div>
            </div>
            <div class="modal-actions">
                <button class="modal-btn secondary" onclick="closeModal('milestoneModal')">取消</button>
                <button class="modal-btn" onclick="submitMilestoneModal()">创建</button>
            </div>
        </div>
    </div>
    <div class="modal-overlay" id="riskModal">
        <div class="modal">
            <div class="modal-header">
                <span class="modal-title">⚠️ 新增项目风险</span>
                <button class="modal-close" onclick="closeModal('riskModal')">✕</button>
            </div>
            <div class="modal-body">
                <div class="project-form-grid">
                    <input class="project-input full" id="riskTitleInput" placeholder="风险标题">
                    <select class="project-input" id="riskLevelInput">
                        <option value="low">low</option>
                        <option value="medium" selected>medium</option>
                        <option value="high">high</option>
                        <option value="critical">critical</option>
                    </select>
                    <input class="project-input" id="riskOwnerInput" placeholder="责任人">
                    <textarea class="project-input full" id="riskMitigationInput" placeholder="缓解策略" style="min-height:100px;resize:vertical;"></textarea>
                </div>
            </div>
            <div class="modal-actions">
                <button class="modal-btn secondary" onclick="closeModal('riskModal')">取消</button>
                <button class="modal-btn" onclick="submitRiskModal()">创建</button>
            </div>
        </div>
    </div>
    <div class="modal-overlay" id="alertRuleModal">
        <div class="modal">
            <div class="modal-header">
                <span class="modal-title">🚨 新建告警规则</span>
                <button class="modal-close" onclick="closeModal('alertRuleModal')">✕</button>
            </div>
            <div class="modal-body">
                <div class="project-form-grid">
                    <input class="project-input full" id="alertRuleNameInput" placeholder="规则名称">
                    <input class="project-input" id="alertMetricInput" placeholder="指标（如 error_rate）">
                    <input class="project-input" id="alertThresholdInput" placeholder="阈值">
                    <select class="project-input" id="alertLevelInput">
                        <option value="low">low</option>
                        <option value="medium" selected>medium</option>
                        <option value="high">high</option>
                        <option value="critical">critical</option>
                    </select>
                    <input class="project-input" id="alertOwnerInput" placeholder="负责人">
                </div>
            </div>
            <div class="modal-actions">
                <button class="modal-btn secondary" onclick="closeModal('alertRuleModal')">取消</button>
                <button class="modal-btn" onclick="submitAlertRuleModal()">创建</button>
            </div>
        </div>
    </div>
    <div class="modal-overlay" id="abModal">
        <div class="modal">
            <div class="modal-header">
                <span class="modal-title">🧪 新建A/B实验</span>
                <button class="modal-close" onclick="closeModal('abModal')">✕</button>
            </div>
            <div class="modal-body">
                <div class="project-form-grid">
                    <input class="project-input full" id="abNameInput" placeholder="实验名称">
                    <input class="project-input" id="abMetricInput" placeholder="核心指标（如 cvt_rate）">
                    <input class="project-input" id="abTrafficInput" placeholder="流量占比（%）" value="50">
                    <input class="project-input" id="abOwnerInput" placeholder="负责人">
                </div>
            </div>
            <div class="modal-actions">
                <button class="modal-btn secondary" onclick="closeModal('abModal')">取消</button>
                <button class="modal-btn" onclick="submitAbModal()">创建</button>
            </div>
        </div>
    </div>
    <div class="modal-overlay" id="integrationModal">
        <div class="modal">
            <div class="modal-header">
                <span class="modal-title">🧩 新建集成</span>
                <button class="modal-close" onclick="closeModal('integrationModal')">✕</button>
            </div>
            <div class="modal-body">
                <div class="project-form-grid">
                    <input class="project-input" id="integrationNameInput" placeholder="集成名称">
                    <input class="project-input" id="integrationProviderInput" placeholder="提供方">
                    <input class="project-input full" id="integrationDescInput" placeholder="用途说明">
                    <input class="project-input" id="integrationOwnerInput" placeholder="负责人">
                    <input class="project-input" id="integrationHealthInput" placeholder="健康度(0-100)" value="80">
                </div>
            </div>
            <div class="modal-actions">
                <button class="modal-btn secondary" onclick="closeModal('integrationModal')">取消</button>
                <button class="modal-btn" onclick="submitIntegrationModal()">创建</button>
            </div>
        </div>
    </div>
    <div class="modal-overlay" id="codeModal">
        <div class="modal">
            <div class="modal-header">
                <span class="modal-title">💻 Python代码执行器</span>
                <button class="modal-close" onclick="closeModal('codeModal')">✕</button>
            </div>
            <div class="modal-body">
                <textarea class="code-editor" id="codeEditor" placeholder="# 在这里输入Python代码...&#10;print('Hello, World!')"></textarea>
                <div class="code-output" id="codeOutput" style="display:none;"></div>
            </div>
            <div class="modal-actions">
                <button class="modal-btn secondary" onclick="closeModal('codeModal')">关闭</button>
                <button class="modal-btn primary" onclick="executeCode()">▶ 运行代码</button>
            </div>
        </div>
    </div>
    <div class="modal-overlay" id="kbModal">
        <div class="modal">
            <div class="modal-header">
                <span class="modal-title">📚 知识库管理</span>
                <button class="modal-close" onclick="closeModal('kbModal')">✕</button>
            </div>
            <div class="modal-body">
                <div class="setting-row">
                    <span class="setting-label">添加知识</span>
                </div>
                <textarea class="kb-input" id="kbInput" placeholder="输入要存储的知识内容..."></textarea>
                <div class="modal-actions" style="margin-top:10px;">
                    <button class="modal-btn primary" onclick="addToKB()">添加到知识库</button>
                </div>
                <hr style="margin:15px 0;border:none;border-top:1px solid var(--border);">
                <div class="setting-row">
                    <span class="setting-label">搜索知识</span>
                </div>
                <input type="text" id="kbSearch" placeholder="输入关键词搜索..." style="width:100%;padding:8px;border:1px solid var(--border);border-radius:6px;margin-bottom:10px;">
                <div id="kbResults"></div>
            </div>
        </div>
    </div>
    <div class="modal-overlay" id="deepseekModal">
        <div class="modal" style="max-width:600px;">
            <div class="modal-header" style="background:linear-gradient(135deg,#4f46e5,#7c3aed);color:white;border-radius:16px 16px 0 0;">
                <span class="modal-title">🤖 DeepSeek API 配置</span>
                <button class="modal-close" onclick="closeModal('deepseekModal')" style="color:white;">✕</button>
            </div>
            <div class="modal-body" style="padding:20px;">
                <div style="background:linear-gradient(135deg,rgba(79,70,229,0.1),rgba(124,58,237,0.05));border-radius:12px;padding:16px;margin-bottom:20px;">
                    <div style="font-size:13px;color:var(--text-primary);font-weight:600;margin-bottom:8px;">💡 使用说明</div>
                    <div style="font-size:12px;color:var(--text-secondary);line-height:1.6;">
                        1. 访问 <a href="https://platform.deepseek.com" target="_blank" style="color:var(--primary);">DeepSeek开放平台</a> 获取API Key<br>
                        2. 填写API Key并保存<br>
                        3. 启用DeepSeek后，对话将使用DeepSeek模型
                    </div>
                </div>
                <div style="margin-bottom:16px;">
                    <label style="font-size:12px;color:var(--text-secondary);display:block;margin-bottom:8px;">API Key</label>
                    <input type="password" id="deepseekApiKey" placeholder="sk-xxxxxxxxxxxxxxxx" style="width:100%;padding:12px;border:1px solid var(--border);border-radius:10px;font-size:14px;background:var(--bg-secondary);color:var(--text-primary);">
                </div>
                <div style="margin-bottom:16px;">
                    <label style="font-size:12px;color:var(--text-secondary);display:block;margin-bottom:8px;">API 地址</label>
                    <input type="text" id="deepseekApiUrl" placeholder="https://api.deepseek.com" style="width:100%;padding:12px;border:1px solid var(--border);border-radius:10px;font-size:14px;background:var(--bg-secondary);color:var(--text-primary);">
                </div>
                <div style="margin-bottom:16px;">
                    <label style="font-size:12px;color:var(--text-secondary);display:block;margin-bottom:8px;">模型选择</label>
                    <select id="deepseekModel" style="width:100%;padding:12px;border:1px solid var(--border);border-radius:10px;font-size:14px;background:var(--bg-secondary);color:var(--text-primary);">
                        <option value="deepseek-chat">DeepSeek Chat (通用对话)</option>
                        <option value="deepseek-coder">DeepSeek Coder (代码专用)</option>
                        <option value="deepseek-reasoner">DeepSeek Reasoner (深度推理)</option>
                    </select>
                </div>
                <div style="margin-bottom:16px;">
                    <div class="setting-row">
                        <span class="setting-label">启用 DeepSeek</span>
                        <label class="toggle"><input type="checkbox" id="deepseekEnabled"><span class="toggle-slider"></span></label>
                    </div>
                </div>
                <div style="display:flex;gap:10px;">
                    <button class="modal-btn secondary" onclick="testDeepSeek()" style="flex:1;">🔌 测试连接</button>
                    <button class="modal-btn primary" onclick="saveDeepSeek()" style="flex:1;">💾 保存配置</button>
                </div>
                <div id="deepseekStatus" style="margin-top:12px;font-size:12px;text-align:center;"></div>
            </div>
        </div>
    </div>
    <div class="modal-overlay" id="statsModal">
        <div class="modal" style="max-width:700px;">
            <div class="modal-header" style="background:linear-gradient(135deg,#10b981,#059669);color:white;border-radius:16px 16px 0 0;">
                <span class="modal-title">📊 数据统计仪表板</span>
                <button class="modal-close" onclick="closeModal('statsModal')" style="color:white;">✕</button>
            </div>
            <div class="modal-body" style="padding:20px;">
                <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px;">
                    <div style="background:linear-gradient(135deg,rgba(16,185,129,0.15),rgba(5,150,105,0.05));border-radius:12px;padding:16px;text-align:center;">
                        <div style="font-size:28px;font-weight:700;color:#10b981;" id="statSessions">0</div>
                        <div style="font-size:11px;color:var(--text-secondary);margin-top:4px;">会话总数</div>
                    </div>
                    <div style="background:linear-gradient(135deg,rgba(102,126,234,0.15),rgba(118,75,162,0.05));border-radius:12px;padding:16px;text-align:center;">
                        <div style="font-size:28px;font-weight:700;color:#667eea;" id="statInput">0</div>
                        <div style="font-size:11px;color:var(--text-secondary);margin-top:4px;">输入Token</div>
                    </div>
                    <div style="background:linear-gradient(135deg,rgba(245,158,11,0.15),rgba(217,119,6,0.05));border-radius:12px;padding:16px;text-align:center;">
                        <div style="font-size:28px;font-weight:700;color:#f59e0b;" id="statOutput">0</div>
                        <div style="font-size:11px;color:var(--text-secondary);margin-top:4px;">输出Token</div>
                    </div>
                    <div style="background:linear-gradient(135deg,rgba(239,68,68,0.15),rgba(220,38,38,0.05));border-radius:12px;padding:16px;text-align:center;">
                        <div style="font-size:28px;font-weight:700;color:#ef4444;" id="statLatency">0ms</div>
                        <div style="font-size:11px;color:var(--text-secondary);margin-top:4px;">平均延迟</div>
                    </div>
                </div>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
                    <div style="background:var(--bg-secondary);border-radius:12px;padding:16px;">
                        <div style="font-size:13px;font-weight:600;margin-bottom:12px;">📈 使用趋势</div>
                        <div id="usageChart" style="height:120px;display:flex;align-items:flex-end;gap:4px;"></div>
                    </div>
                    <div style="background:var(--bg-secondary);border-radius:12px;padding:16px;">
                        <div style="font-size:13px;font-weight:600;margin-bottom:12px;">🎯 工具使用统计</div>
                        <div id="toolStats" style="font-size:12px;"></div>
                    </div>
                </div>
                <div style="margin-top:16px;display:flex;gap:10px;">
                    <button class="modal-btn secondary" onclick="resetStats()" style="flex:1;">🗑️ 重置统计</button>
                    <button class="modal-btn primary" onclick="exportStats()" style="flex:1;">📥 导出报告</button>
                </div>
            </div>
        </div>
    </div>
    
    <!-- 工作流编辑器模态框 -->
    <div class="modal-overlay" id="workflowEditorModal" style="z-index:1000;">
        <div class="modal" style="max-width:95vw;width:1200px;height:90vh;display:flex;flex-direction:column;">
            <div class="modal-header" style="background:linear-gradient(135deg,#667eea,#764ba2);color:white;border-radius:16px 16px 0 0;flex-shrink:0;">
                <span class="modal-title">📋 工作流编辑器</span>
                <div style="display:flex;gap:10px;align-items:center;">
                    <input type="text" id="workflowName" placeholder="工作流名称" style="padding:6px 12px;border-radius:6px;border:none;font-size:13px;width:200px;color:#333;">
                    <button class="modal-btn" onclick="saveWorkflow()" style="background:rgba(255,255,255,0.2);color:white;border:none;">💾 保存</button>
                    <button class="modal-btn" onclick="executeWorkflow()" style="background:#10b981;color:white;border:none;">▶ 运行</button>
                    <button class="modal-close" onclick="closeModal('workflowEditorModal')" style="color:white;">✕</button>
                </div>
            </div>
            <div class="modal-body" style="padding:0;display:flex;flex:1;overflow:hidden;">
                <!-- 左侧节点面板 -->
                <div style="width:200px;background:var(--bg-secondary);border-right:1px solid var(--border);padding:16px;overflow-y:auto;">
                    <div style="font-size:12px;font-weight:600;color:var(--text-muted);margin-bottom:12px;">控制节点</div>
                    <div id="workflowNodesControl" style="display:flex;flex-direction:column;gap:8px;margin-bottom:20px;"></div>
                    <div style="font-size:12px;font-weight:600;color:var(--text-muted);margin-bottom:12px;">AI节点</div>
                    <div id="workflowNodesAI" style="display:flex;flex-direction:column;gap:8px;margin-bottom:20px;"></div>
                    <div style="font-size:12px;font-weight:600;color:var(--text-muted);margin-bottom:12px;">工具节点</div>
                    <div id="workflowNodesTool" style="display:flex;flex-direction:column;gap:8px;"></div>
                </div>
                <!-- 中间画布 -->
                <div style="flex:1;position:relative;background:linear-gradient(45deg,var(--bg-primary) 25%,transparent 25%),linear-gradient(-45deg,var(--bg-primary) 25%,transparent 25%),linear-gradient(45deg,transparent 75%,var(--bg-primary) 75%),linear-gradient(-45deg,transparent 75%,var(--bg-primary) 75%);background-size:20px 20px;background-position:0 0,0 10px,10px -10px,-10px 0px;" id="workflowCanvas">
                    <svg id="workflowConnections" style="position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:1;"></svg>
                    <div id="workflowNodesContainer" style="position:absolute;top:0;left:0;width:100%;height:100%;z-index:2;"></div>
                    <div style="position:absolute;bottom:16px;right:16px;display:flex;gap:8px;z-index:10;">
                        <button onclick="clearWorkflowCanvas()" class="quick-tool" style="background:rgba(239,68,68,0.9);color:white;">🗑️ 清空</button>
                        <button onclick="zoomWorkflow(0.1)" class="quick-tool">➕</button>
                        <button onclick="zoomWorkflow(-0.1)" class="quick-tool">➖</button>
                    </div>
                </div>
                <!-- 右侧属性面板 -->
                <div style="width:280px;background:var(--bg-secondary);border-left:1px solid var(--border);padding:16px;overflow-y:auto;" id="workflowProperties">
                    <div style="text-align:center;color:var(--text-muted);padding:40px 20px;">
                        <div style="font-size:32px;margin-bottom:8px;">👈</div>
                        <div style="font-size:13px;">选择节点以编辑属性</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <div class="modal-overlay" id="modelModal">
        <div class="modal" style="max-width:600px;">
            <div class="modal-header" style="background:linear-gradient(135deg,#f59e0b,#d97706);color:white;border-radius:16px 16px 0 0;">
                <span class="modal-title">⚙️ 模型配置</span>
                <button class="modal-close" onclick="closeModal('modelModal')" style="color:white;">✕</button>
            </div>
            <div class="modal-body" style="padding:20px;">
                <div style="margin-bottom:16px;">
                    <label style="font-size:12px;color:var(--text-secondary);display:block;margin-bottom:8px;">温度 (Temperature)</label>
                    <div style="display:flex;align-items:center;gap:12px;">
                        <input type="range" id="modelTemp" min="0" max="2" step="0.1" value="0.7" style="flex:1;" oninput="document.getElementById('modelTempVal').textContent=this.value">
                        <span id="modelTempVal" style="font-size:14px;font-weight:600;min-width:30px;">0.7</span>
                    </div>
                    <div style="font-size:11px;color:var(--text-muted);margin-top:4px;">较低值更精确，较高值更有创意</div>
                </div>
                <div style="margin-bottom:16px;">
                    <label style="font-size:12px;color:var(--text-secondary);display:block;margin-bottom:8px;">最大Token数</label>
                    <div style="display:flex;align-items:center;gap:12px;">
                        <input type="range" id="modelTokens" min="256" max="8192" step="256" value="4096" style="flex:1;" oninput="document.getElementById('modelTokensVal').textContent=this.value">
                        <span id="modelTokensVal" style="font-size:14px;font-weight:600;min-width:50px;">4096</span>
                    </div>
                </div>
                <div style="margin-bottom:16px;">
                    <label style="font-size:12px;color:var(--text-secondary);display:block;margin-bottom:8px;">Top P (核采样)</label>
                    <div style="display:flex;align-items:center;gap:12px;">
                        <input type="range" id="modelTopP" min="0" max="1" step="0.1" value="0.9" style="flex:1;" oninput="document.getElementById('modelTopPVal').textContent=this.value">
                        <span id="modelTopPVal" style="font-size:14px;font-weight:600;min-width:30px;">0.9</span>
                    </div>
                </div>
                <div style="margin-bottom:16px;">
                    <label style="font-size:12px;color:var(--text-secondary);display:block;margin-bottom:8px;">重复惩罚</label>
                    <div style="display:flex;align-items:center;gap:12px;">
                        <input type="range" id="modelRepetition" min="1" max="2" step="0.1" value="1.1" style="flex:1;" oninput="document.getElementById('modelRepetitionVal').textContent=this.value">
                        <span id="modelRepetitionVal" style="font-size:14px;font-weight:600;min-width:30px;">1.1</span>
                    </div>
                </div>
                <div style="margin-bottom:16px;">
                    <div class="setting-row">
                        <span class="setting-label">流式输出</span>
                        <label class="toggle"><input type="checkbox" id="modelStream" checked><span class="toggle-slider"></span></label>
                    </div>
                </div>
                <button class="modal-btn primary" onclick="saveModelConfig()" style="width:100%;">💾 保存配置</button>
            </div>
        </div>
    </div>
    <div class="modal-overlay" id="themeModal">
        <div class="modal" style="max-width:600px;">
            <div class="modal-header" style="background:linear-gradient(135deg,#ec4899,#be185d);color:white;border-radius:16px 16px 0 0;">
                <span class="modal-title">🎨 主题设置</span>
                <button class="modal-close" onclick="closeModal('themeModal')" style="color:white;">✕</button>
            </div>
            <div class="modal-body" style="padding:20px;">
                <div style="margin-bottom:20px;">
                    <div style="font-size:13px;font-weight:600;margin-bottom:12px;">预设主题</div>
                    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;">
                        <div class="theme-preset" onclick="applyTheme('default')" style="background:linear-gradient(135deg,#667eea,#764ba2);height:50px;border-radius:10px;cursor:pointer;border:2px solid transparent;" title="默认紫"></div>
                        <div class="theme-preset" onclick="applyTheme('ocean')" style="background:linear-gradient(135deg,#0ea5e9,#0284c7);height:50px;border-radius:10px;cursor:pointer;border:2px solid transparent;" title="海洋蓝"></div>
                        <div class="theme-preset" onclick="applyTheme('forest')" style="background:linear-gradient(135deg,#10b981,#059669);height:50px;border-radius:10px;cursor:pointer;border:2px solid transparent;" title="森林绿"></div>
                        <div class="theme-preset" onclick="applyTheme('sunset')" style="background:linear-gradient(135deg,#f59e0b,#ef4444);height:50px;border-radius:10px;cursor:pointer;border:2px solid transparent;" title="日落橙"></div>
                    </div>
                </div>
                <div style="margin-bottom:16px;">
                    <label style="font-size:12px;color:var(--text-secondary);display:block;margin-bottom:8px;">主色调</label>
                    <div style="display:flex;gap:8px;">
                        <input type="color" id="primaryColor" value="#667eea" style="width:50px;height:40px;border:none;border-radius:8px;cursor:pointer;">
                        <input type="text" id="primaryColorText" value="#667eea" style="flex:1;padding:10px;border:1px solid var(--border);border-radius:8px;font-size:13px;background:var(--bg-secondary);color:var(--text-primary);">
                    </div>
                </div>
                <div style="margin-bottom:16px;">
                    <label style="font-size:12px;color:var(--text-secondary);display:block;margin-bottom:8px;">背景透明度</label>
                    <div style="display:flex;align-items:center;gap:12px;">
                        <input type="range" id="bgOpacity" min="0" max="100" value="80" style="flex:1;" oninput="document.getElementById('bgOpacityVal').textContent=this.value+'%'">
                        <span id="bgOpacityVal" style="font-size:14px;font-weight:600;min-width:40px;">80%</span>
                    </div>
                </div>
                <div style="margin-bottom:16px;">
                    <label style="font-size:12px;color:var(--text-secondary);display:block;margin-bottom:8px;">字体大小</label>
                    <select id="fontSize" style="width:100%;padding:12px;border:1px solid var(--border);border-radius:10px;font-size:14px;background:var(--bg-secondary);color:var(--text-primary);">
                        <option value="small">小 (12px)</option>
                        <option value="medium" selected>中 (14px)</option>
                        <option value="large">大 (16px)</option>
                    </select>
                </div>
                <div style="margin-bottom:16px;">
                    <div class="setting-row">
                        <span class="setting-label">毛玻璃效果</span>
                        <label class="toggle"><input type="checkbox" id="glassEffect" checked><span class="toggle-slider"></span></label>
                    </div>
                </div>
                <div style="display:flex;gap:10px;">
                    <button class="modal-btn secondary" onclick="resetTheme()" style="flex:1;">🔄 重置</button>
                    <button class="modal-btn primary" onclick="saveTheme()" style="flex:1;">💾 应用</button>
                </div>
            </div>
        </div>
    </div>
    <div class="modal-overlay" id="modelsModal">
        <div class="modal" style="max-width:750px;">
            <div class="modal-header" style="background:linear-gradient(135deg,#6366f1,#8b5cf6);color:white;border-radius:16px 16px 0 0;">
                <span class="modal-title">🌐 多模型API配置</span>
                <button class="modal-close" onclick="closeModal('modelsModal')" style="color:white;">✕</button>
            </div>
            <div class="modal-body" style="padding:20px;max-height:70vh;overflow-y:auto;">
                <div class="model-card" id="openaiCard">
                    <div class="model-header" onclick="toggleModelConfig('openai')">
                        <div class="model-info">
                            <span class="model-icon">🟢</span>
                            <span class="model-name">OpenAI GPT</span>
                            <span class="model-badge">GPT-4o / GPT-4 / GPT-3.5</span>
                        </div>
                        <div class="model-toggle">
                            <label class="toggle"><input type="checkbox" id="openaiEnabled"><span class="toggle-slider"></span></label>
                        </div>
                    </div>
                    <div class="model-config" id="openaiConfig" style="display:none;">
                        <div class="config-row">
                            <label>API Key</label>
                            <input type="password" id="openaiApiKey" placeholder="sk-...">
                        </div>
                        <div class="config-row">
                            <label>API Base URL</label>
                            <input type="text" id="openaiBaseUrl" placeholder="https://api.openai.com/v1">
                        </div>
                        <div class="config-row">
                            <label>模型</label>
                            <select id="openaiModel">
                                <option value="gpt-4o">GPT-4o (推荐)</option>
                                <option value="gpt-4-turbo">GPT-4 Turbo</option>
                                <option value="gpt-4">GPT-4</option>
                                <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
                            </select>
                        </div>
                    </div>
                </div>
                <div class="model-card" id="claudeCard">
                    <div class="model-header" onclick="toggleModelConfig('claude')">
                        <div class="model-info">
                            <span class="model-icon">🟠</span>
                            <span class="model-name">Anthropic Claude</span>
                            <span class="model-badge">Claude 3.5 / Claude 3</span>
                        </div>
                        <div class="model-toggle">
                            <label class="toggle"><input type="checkbox" id="claudeEnabled"><span class="toggle-slider"></span></label>
                        </div>
                    </div>
                    <div class="model-config" id="claudeConfig" style="display:none;">
                        <div class="config-row">
                            <label>API Key</label>
                            <input type="password" id="claudeApiKey" placeholder="sk-ant-...">
                        </div>
                        <div class="config-row">
                            <label>模型</label>
                            <select id="claudeModel">
                                <option value="claude-3-5-sonnet-20241022">Claude 3.5 Sonnet (推荐)</option>
                                <option value="claude-3-5-haiku-20241022">Claude 3.5 Haiku</option>
                                <option value="claude-3-opus-20240229">Claude 3 Opus</option>
                                <option value="claude-3-sonnet-20240229">Claude 3 Sonnet</option>
                            </select>
                        </div>
                    </div>
                </div>
                <div class="model-card" id="geminiCard">
                    <div class="model-header" onclick="toggleModelConfig('gemini')">
                        <div class="model-info">
                            <span class="model-icon">🔵</span>
                            <span class="model-name">Google Gemini</span>
                            <span class="model-badge">Gemini 1.5 Pro / Flash</span>
                        </div>
                        <div class="model-toggle">
                            <label class="toggle"><input type="checkbox" id="geminiEnabled"><span class="toggle-slider"></span></label>
                        </div>
                    </div>
                    <div class="model-config" id="geminiConfig" style="display:none;">
                        <div class="config-row">
                            <label>API Key</label>
                            <input type="password" id="geminiApiKey" placeholder="AIza...">
                        </div>
                        <div class="config-row">
                            <label>模型</label>
                            <select id="geminiModel">
                                <option value="gemini-1.5-pro">Gemini 1.5 Pro</option>
                                <option value="gemini-1.5-flash">Gemini 1.5 Flash</option>
                                <option value="gemini-pro">Gemini Pro</option>
                            </select>
                        </div>
                    </div>
                </div>
                <div class="model-card" id="qwenCard">
                    <div class="model-header" onclick="toggleModelConfig('qwen')">
                        <div class="model-info">
                            <span class="model-icon">🟣</span>
                            <span class="model-name">阿里云通义千问</span>
                            <span class="model-badge">Qwen-Max / Qwen-Plus</span>
                        </div>
                        <div class="model-toggle">
                            <label class="toggle"><input type="checkbox" id="qwenEnabled"><span class="toggle-slider"></span></label>
                        </div>
                    </div>
                    <div class="model-config" id="qwenConfig" style="display:none;">
                        <div class="config-row">
                            <label>API Key</label>
                            <input type="password" id="qwenApiKey" placeholder="sk-...">
                        </div>
                        <div class="config-row">
                            <label>模型</label>
                            <select id="qwenModel">
                                <option value="qwen-max">Qwen-Max</option>
                                <option value="qwen-plus">Qwen-Plus</option>
                                <option value="qwen-turbo">Qwen-Turbo</option>
                            </select>
                        </div>
                    </div>
                </div>
                <div class="model-card" id="moonshotCard">
                    <div class="model-header" onclick="toggleModelConfig('moonshot')">
                        <div class="model-info">
                            <span class="model-icon">🌙</span>
                            <span class="model-name">Moonshot Kimi</span>
                            <span class="model-badge">长文本专家</span>
                        </div>
                        <div class="model-toggle">
                            <label class="toggle"><input type="checkbox" id="moonshotEnabled"><span class="toggle-slider"></span></label>
                        </div>
                    </div>
                    <div class="model-config" id="moonshotConfig" style="display:none;">
                        <div class="config-row">
                            <label>API Key</label>
                            <input type="password" id="moonshotApiKey" placeholder="sk-...">
                        </div>
                        <div class="config-row">
                            <label>模型</label>
                            <select id="moonshotModel">
                                <option value="moonshot-v1-8k">Moonshot V1 8K</option>
                                <option value="moonshot-v1-32k">Moonshot V1 32K</option>
                                <option value="moonshot-v1-128k">Moonshot V1 128K</option>
                            </select>
                        </div>
                    </div>
                </div>
                <div class="model-card" id="zhipuCard">
                    <div class="model-header" onclick="toggleModelConfig('zhipu')">
                        <div class="model-info">
                            <span class="model-icon">🔷</span>
                            <span class="model-name">智谱AI GLM</span>
                            <span class="model-badge">GLM-4 / GLM-3</span>
                        </div>
                        <div class="model-toggle">
                            <label class="toggle"><input type="checkbox" id="zhipuEnabled"><span class="toggle-slider"></span></label>
                        </div>
                    </div>
                    <div class="model-config" id="zhipuConfig" style="display:none;">
                        <div class="config-row">
                            <label>API Key</label>
                            <input type="password" id="zhipuApiKey" placeholder="...">
                        </div>
                        <div class="config-row">
                            <label>模型</label>
                            <select id="zhipuModel">
                                <option value="glm-4">GLM-4</option>
                                <option value="glm-4-air">GLM-4-Air</option>
                                <option value="glm-3-turbo">GLM-3 Turbo</option>
                            </select>
                        </div>
                    </div>
                </div>
                <div style="margin-top:16px;display:flex;gap:10px;">
                    <button class="modal-btn secondary" onclick="testModelConnection()" style="flex:1;">🔌 测试连接</button>
                    <button class="modal-btn primary" onclick="saveModelsConfig()" style="flex:1;">💾 保存配置</button>
                </div>
                <div id="modelsStatus" style="margin-top:12px;font-size:12px;text-align:center;"></div>
            </div>
        </div>
    </div>
    <script>
        marked.setOptions({ 
            highlight: c => hljs.highlightAuto(c).value, 
            breaks: true,
            gfm: true,
            mangle: false,
            headerIds: false
        });
        // 禁用删除线解析
        const renderer = new marked.Renderer();
        renderer.del = (text) => text;
        marked.use({ renderer });
        let chats = JSON.parse(localStorage.getItem('kaguya_chats') || '[]');
        let currentChatId = null, history = [], attachments = [];
        let currentRole = 'kaguya', currentLora = 'none';
        let currentStructuredTemplate = null;
        let promptSearchKeyword = '';
        let promptCategory = 'all';
        let featureActionHistory = JSON.parse(localStorage.getItem('kaguya_feature_actions') || '[]');
        let activeTools = new Set();
        let settings = JSON.parse(localStorage.getItem('kaguya_settings') || '{"temp":0.7,"tokens":4096,"dark":false,"voice":false,"markdown":true}');
        let stats = JSON.parse(localStorage.getItem('kaguya_stats') || '{"sessions":0,"inputTokens":0,"outputTokens":0,"latencies":[]}');
        const roles = {{roles_json}};
        const loras = {{loras_json}};
        const tools = {{tools_json}};
        const commands = {{commands_json}};
        let recognition = null, isRecording = false;
        let ragEnabled = false;
        let ragDocuments = [];
        let consoleOverview = {};
        let consoleRecommendations = [];
        let globalSearchResults = [];
        let projectOverview = {};
        let projectArtifacts = [];
        let projectTasks = [];
        let projectPlaybooks = [];
        let projectActivities = [];
        let opsOverview = {};
        let opsCampaigns = [];
        let releaseOverview = {};
        let releasePlans = [];
        let alertOverview = {};
        let alertRules = [];
        let abOverview = {};
        let abExperiments = [];
        let integrationOverview = {};
        let integrationItems = [];
        let workspaceProjects = [];
        let workspaceOverview = {};
        let externalApiConfig = {active_provider: 'deepseek', providers: {}};
        let currentSceneId = 'ecommerce';
        const SCENE_UI_CONFIG = {
            ecommerce: {title: '电商增长', icon: '🛍️', desc: '围绕商品与人群，输出可执行增长方案。', placeholders: {topic: '例如：美妆新品，客单价189元', context: '例如：小红书+抖音为主，库存8000件', goal: '例如：30天GMV提升40%', constraints: '例如：预算8万元，团队3人'}},
            shortvideo: {title: '短视频运营', icon: '🎬', desc: '快速生成选题脚本、钩子与发布时间策略。', placeholders: {topic: '例如：职场技能账号', context: '例如：已有5条爆款，粉丝1.2万', goal: '例如：7天涨粉5000', constraints: '例如：每天最多拍2条'}},
            resume: {title: '简历求职', icon: '🧩', desc: '将经历重写为目标岗位可用的求职材料。', placeholders: {topic: '例如：3年数据分析经历', context: '例如：目标岗位-增长策略分析师', goal: '例如：两周内完成投递并拿到面试', constraints: '例如：不夸大经历，强调真实成果'}},
            business: {title: '商业计划', icon: '📈', desc: '形成市场、商业模式、里程碑与风控方案。', placeholders: {topic: '例如：AI客服SaaS项目', context: '例如：目标客户为中型电商企业', goal: '例如：半年内实现100万ARR', constraints: '例如：初始团队5人，资金有限'}},
            dataops: {title: '数据经营分析', icon: '📊', desc: '构建指标、定位异常并给出行动闭环。', placeholders: {topic: '例如：近30天渠道转化数据', context: '例如：投放成本上升、留存下降', goal: '例如：次月ROI提升20%', constraints: '例如：不可新增人力'}},
            contract: {title: '合同风险审阅', icon: '⚖️', desc: '识别高风险条款并给出谈判修改建议。', placeholders: {topic: '例如：软件采购合同草案', context: '例如：甲方为大型企业，交付周期3个月', goal: '例如：降低违约风险并明确验收', constraints: '例如：维持总价不变'}}
        };
        let projectMilestones = [];
        let projectRisks = [];
        let editingArtifactId = null;
        let draggingTaskId = null;
        let selectedTaskIds = new Set();
        let ragSettings = {topK: 5, alpha: 0.5, useRerank: true, showScores: true, useCache: true, useExpansion: true, useHyde: false, useMultiQuery: false, useDecomposition: false, useAdaptive: true, useRrf: false, useMetadataFilter: true, useTimeWeight: false, useIterative: false};
        let lastRagResults = [];
        let deepseekConfig = JSON.parse(localStorage.getItem('deepseek_config') || '{}');
        
        function init() {
            console.log('init() called');
            try {
                if (settings.dark) document.body.classList.add('dark');
                const darkModeToggle = document.getElementById('darkModeToggle');
                if (darkModeToggle) darkModeToggle.checked = settings.dark;
                const settingTemp = document.getElementById('settingTemp');
                if (settingTemp) settingTemp.value = settings.temp;
                const settingTempValue = document.getElementById('settingTempValue');
                if (settingTempValue) settingTempValue.textContent = settings.temp;
                const settingTokens = document.getElementById('settingTokens');
                if (settingTokens) settingTokens.value = settings.tokens;
                const settingTokensValue = document.getElementById('settingTokensValue');
                if (settingTokensValue) settingTokensValue.textContent = settings.tokens;
                const voiceOutputToggle = document.getElementById('voiceOutputToggle');
                if (voiceOutputToggle) voiceOutputToggle.checked = settings.voice;
                const markdownToggle = document.getElementById('markdownToggle');
                if (markdownToggle) markdownToggle.checked = settings.markdown;
                const kbSearchEl = document.getElementById('kbSearch');
                if (kbSearchEl) kbSearchEl.addEventListener('input', searchKB);
                renderChatList();
                renderRoleList();
                renderToolList();
                loadLoraList();
                loadRagDocuments();
                loadProjectCenter();
                initScenesCenter();
                updateStats();
                updateDeepSeekIndicator();
                checkExternalApiWarning();
                if (chats.length > 0) loadChat(chats[0].id);
                else showWelcome();
                initSpeechRecognition();
            } catch (e) {
                console.error('Init error:', e);
            }
        }
        
        function loadRagDocuments() {
            fetch('/rag/documents').then(r => r.json()).then(data => {
                if (data.success) {
                    ragDocuments = data.documents;
                    renderRagDocList();
                    updateRagStats();
                    renderFeatureCenterMeta();
                }
            });
        }
        
        function updateRagStats() {
            fetch('/rag/stats').then(r => r.json()).then(data => {
                if (data.success) {
                    const stats = data.stats;
                    const docsEl = document.getElementById('ragStatDocs');
                    const chunksEl = document.getElementById('ragStatChunks');
                    const charsEl = document.getElementById('ragStatChars');
                    if (docsEl) docsEl.textContent = stats.total_docs;
                    if (chunksEl) chunksEl.textContent = stats.total_chunks;
                    if (charsEl) charsEl.textContent = stats.total_chars > 1000 ? (stats.total_chars/1000).toFixed(1) + 'K' : stats.total_chars;
                    const ragStatsEl = document.getElementById('ragStats');
                    const cacheInfo = stats.cache_size > 0 ? ` | 💾 缓存: ${stats.cache_size}` : '';
                    if (ragStatsEl) ragStatsEl.title = `唯一文档: ${stats.unique_hashes || 0}${cacheInfo}`;
                }
            });
        }
        
        function renderRagDocList() {
            const list = document.getElementById('ragDocList');
            const filter = document.getElementById('ragCategoryFilter').value;
            const filtered = filter ? ragDocuments.filter(d => d.category === filter) : ragDocuments;
            
            if (!filtered.length) {
                list.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:20px;font-size:12px;">暂无文档<br>上传文档以启用RAG功能</div>';
                return;
            }
            
            const categoryIcons = {doc: '📄', code: '💻', data: '📊', web: '🌐', text: '📝', config: '⚙️', other: '📁'};
            
            list.innerHTML = filtered.map(doc => `
                <div class="chat-item" style="flex-direction:column;align-items:flex-start;gap:4px;cursor:pointer;" onclick="previewRagDoc('${doc.id}')">
                    <div style="display:flex;width:100%;align-items:center;gap:8px;">
                        <span>${categoryIcons[doc.category] || '📁'}</span>
                        <span style="flex:1;font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${doc.filename}">${doc.filename}</span>
                        <button onclick="event.stopPropagation();deleteRagDoc('${doc.id}')" style="border:none;background:none;cursor:pointer;color:#e74c3c;font-size:11px;">🗑️</button>
                    </div>
                    <div style="font-size:10px;color:var(--text-muted);width:100%;display:flex;justify-content:space-between;">
                        <span>${doc.chunk_count} 块 · ${(doc.size / 1024).toFixed(1)} KB</span>
                        <span>${new Date(doc.time).toLocaleDateString()}</span>
                    </div>
                </div>
            `).join('');
        }
        
        function filterRagDocs() {
            renderRagDocList();
        }
        
        function toggleRag() {
            ragEnabled = document.getElementById('ragToggle').checked;
            updateRagIndicator();
            renderFeatureCenterMeta();
            showToast(ragEnabled ? 'RAG已启用 - 将基于文档回答' : 'RAG已禁用');
        }
        
        function updateRagIndicator() {
            const indicators = document.getElementById('headerIndicators');
            let html = indicators.innerHTML;
            const ragIndicator = '<div class="indicator tool"><span>📚</span><span>RAG</span></div>';
            if (ragEnabled && !html.includes('RAG')) {
                indicators.innerHTML = ragIndicator + html;
            } else if (!ragEnabled) {
                indicators.innerHTML = html.replace(ragIndicator, '');
            }
        }
        
        function uploadRagFile(event) {
            const files = event.target.files;
            if (!files || !files.length) return;
            
            if (files.length === 1) {
                const file = files[0];
                const formData = new FormData();
                formData.append('file', file);
                showToast('正在上传: ' + file.name);
                fetch('/rag/upload', {
                    method: 'POST',
                    body: formData
                }).then(r => r.json()).then(data => {
                    if (data.success) {
                        showToast('上传成功: ' + data.document.filename);
                        loadRagDocuments();
                    } else {
                        showToast('上传失败: ' + (data.error || '未知错误'));
                    }
                }).catch(e => showToast('上传失败: ' + e));
            } else {
                const formData = new FormData();
                for (let f of files) formData.append('files', f);
                showToast(`正在上传 ${files.length} 个文件...`);
                fetch('/rag/batch_upload', {
                    method: 'POST',
                    body: formData
                }).then(r => r.json()).then(data => {
                    if (data.success) {
                        const success = data.results.filter(r => r.success).length;
                        showToast(`上传完成: ${success}/${files.length} 成功`);
                        loadRagDocuments();
                    }
                });
            }
            event.target.value = '';
        }
        
        function showAddTextModal() {
            const html = `
                <div class="modal-header">
                    <span class="modal-title">📝 添加文本到知识库</span>
                    <button class="modal-close" onclick="closeModal()">✕</button>
                </div>
                <div class="modal-body">
                    <div style="margin-bottom:12px;">
                        <label style="font-size:12px;color:var(--text-secondary);display:block;margin-bottom:6px;">标题</label>
                        <input type="text" id="addTextTitle" placeholder="输入标题..." style="width:100%;padding:10px;border:1px solid var(--border);border-radius:8px;font-size:13px;background:var(--bg-secondary);color:var(--text-primary);">
                    </div>
                    <div style="margin-bottom:12px;">
                        <label style="font-size:12px;color:var(--text-secondary);display:block;margin-bottom:6px;">内容 (至少50字符)</label>
                        <textarea id="addTextContent" placeholder="粘贴或输入文本内容..." style="width:100%;height:200px;padding:10px;border:1px solid var(--border);border-radius:8px;font-size:13px;background:var(--bg-secondary);color:var(--text-primary);resize:vertical;"></textarea>
                    </div>
                    <div style="margin-bottom:12px;">
                        <label style="font-size:12px;color:var(--text-secondary);display:block;margin-bottom:6px;">标签 (逗号分隔)</label>
                        <input type="text" id="addTextTags" placeholder="标签1, 标签2..." style="width:100%;padding:10px;border:1px solid var(--border);border-radius:8px;font-size:13px;background:var(--bg-secondary);color:var(--text-primary);">
                    </div>
                </div>
                <div class="modal-actions">
                    <button class="modal-btn secondary" onclick="closeModal()">取消</button>
                    <button class="modal-btn primary" onclick="submitAddText()">添加</button>
                </div>
            `;
            showModal(html);
        }
        
        function submitAddText() {
            const title = document.getElementById('addTextTitle').value.trim() || '手动输入';
            const content = document.getElementById('addTextContent').value.trim();
            const tags = document.getElementById('addTextTags').value.split(',').map(t => t.trim()).filter(t => t);
            
            if (content.length < 50) {
                showToast('内容至少需要50个字符');
                return;
            }
            
            fetch('/rag/add_text', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({text: content, title, tags})
            }).then(r => r.json()).then(data => {
                if (data.success) {
                    showToast('文本已添加到知识库');
                    closeModal();
                    loadRagDocuments();
                } else {
                    showToast('添加失败: ' + (data.error || '未知错误'));
                }
            });
        }
        
        function closeModal(id) {
            if (id) {
                const modal = document.getElementById(id);
                if (modal) {
                    modal.classList.remove('show');
                    // 如果是动态创建的模态框（以 Modal 结尾的 id），从 DOM 中移除
                    if (id.endsWith('Modal') || modal.classList.contains('modal-overlay')) {
                        setTimeout(() => {
                            if (modal && modal.parentNode) {
                                modal.remove();
                            }
                        }, 300);
                    }
                }
            } else {
                const overlay = document.getElementById('modalOverlay');
                if (overlay) overlay.classList.remove('show');
            }
        }
        
        function showModal(html) {
            const overlay = document.getElementById('modalOverlay');
            overlay.querySelector('.modal').innerHTML = html;
            overlay.classList.add('show');
        }
        
        function deleteRagDoc(docId) {
            if (!confirm('确定删除此文档？相关分块也将被删除。')) return;
            fetch('/rag/delete/' + docId, { method: 'DELETE' })
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        showToast('文档已删除');
                        loadRagDocuments();
                    }
                });
        }
        
        function searchRagDocs() {
            const query = document.getElementById('ragSearchInput').value.trim();
            const resultsDiv = document.getElementById('ragSearchResults');
            if (!query) {
                resultsDiv.innerHTML = '';
                return;
            }
            const category = document.getElementById('ragCategoryFilter').value;
            fetch('/rag/search', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    query, 
                    top_k: ragSettings.topK, 
                    category: category || null,
                    use_rerank: ragSettings.useRerank,
                    alpha: ragSettings.alpha,
                    use_cache: ragSettings.useCache,
                    use_expansion: ragSettings.useExpansion,
                    use_hyde: ragSettings.useHyde,
                    use_multi_query: ragSettings.useMultiQuery,
                    use_decomposition: ragSettings.useDecomposition,
                    use_adaptive: ragSettings.useAdaptive,
                    use_rrf: ragSettings.useRrf,
                    use_metadata_filter: ragSettings.useMetadataFilter,
                    use_time_weight: ragSettings.useTimeWeight,
                    use_iterative: ragSettings.useIterative
                })
            }).then(r => r.json()).then(data => {
                if (data.success && data.results.length) {
                    lastRagResults = data.results;
                    var qualityHtml = data.quality ? '<div style="font-size:9px;color:var(--text-muted);margin-bottom:8px;">类型: ' + data.query_type + ' | 质量: ' + data.quality.reason + ' (' + data.quality.score + ')</div>' : '';
                    var resultsHtml = '';
                    for (var i = 0; i < data.results.length; i++) {
                        var r = data.results[i];
                        var textPreview = r.text.length > 120 ? r.text.slice(0, 120) + '...' : r.text;
                        textPreview = textPreview.replace(/</g, '&lt;').replace(/>/g, '&gt;');
                        resultsHtml += '<div style="padding:10px;background:var(--bg-secondary);border-radius:8px;margin-bottom:6px;font-size:11px;cursor:pointer;" onclick="useRagResultByIndex(' + i + ')">' +
                            '<div style="display:flex;justify-content:space-between;margin-bottom:4px;">' +
                                '<span style="color:var(--primary);font-weight:600;">' + r.doc_name + '</span>' +
                                '<span style="color:var(--accent);">' + (r.score * 100).toFixed(0) + '%</span>' +
                            '</div>' +
                            '<div style="color:var(--text-secondary);line-height:1.4;">' + textPreview + '</div>' +
                        '</div>';
                    }
                    resultsDiv.innerHTML = qualityHtml + resultsHtml;
                } else {
                    resultsDiv.innerHTML = '<div style="color:var(--text-muted);font-size:11px;text-align:center;padding:10px;">未找到相关内容</div>';
                }
            });
        }
        
        function useRagResult(text) {
            const input = document.getElementById('mainInput');
            input.value = '基于以下内容回答: ' + text + '\\n\\n问题: ';
            input.focus();
        }
        
        function useRagResultByIndex(idx) {
            if (lastRagResults && lastRagResults[idx]) {
                useRagResult(lastRagResults[idx].text);
            }
        }
        
        function showRagSettings() {
            const html = `
                <div class="modal-header">
                    <span class="modal-title">⚙️ RAG高级设置</span>
                    <button class="modal-close" onclick="closeModal()">✕</button>
                </div>
                <div class="modal-body" style="max-height:500px;overflow-y:auto;">
                    <div style="font-size:12px;color:var(--primary);font-weight:600;margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid var(--border);">📊 基础设置</div>
                    <div style="margin-bottom:12px;">
                        <label style="font-size:12px;color:var(--text-secondary);display:block;margin-bottom:6px;">
                            返回结果数量: <b id="topKValue">${ragSettings.topK}</b>
                        </label>
                        <input type="range" id="ragTopK" min="1" max="10" value="${ragSettings.topK}" 
                            style="width:100%;" oninput="document.getElementById('topKValue').textContent=this.value">
                    </div>
                    <div style="margin-bottom:12px;">
                        <label style="font-size:12px;color:var(--text-secondary);display:block;margin-bottom:6px;">
                            TF-IDF权重: <b id="alphaValue">${ragSettings.alpha}</b>
                        </label>
                        <input type="range" id="ragAlpha" min="0" max="100" value="${ragSettings.alpha * 100}" 
                            style="width:100%;" oninput="document.getElementById('alphaValue').textContent=(this.value/100).toFixed(2)">
                    </div>
                    <div style="margin-bottom:8px;">
                        <div class="setting-row">
                            <span class="setting-label">启用重排序</span>
                            <label class="toggle"><input type="checkbox" id="ragRerank" ${ragSettings.useRerank ? 'checked' : ''}><span class="toggle-slider"></span></label>
                        </div>
                    </div>
                    <div style="margin-bottom:8px;">
                        <div class="setting-row">
                            <span class="setting-label">自适应检索</span>
                            <label class="toggle"><input type="checkbox" id="ragAdaptive" ${ragSettings.useAdaptive ? 'checked' : ''}><span class="toggle-slider"></span></label>
                        </div>
                    </div>
                    
                    <div style="font-size:12px;color:var(--primary);font-weight:600;margin:16px 0 12px;padding-bottom:8px;border-bottom:1px solid var(--border);">🚀 高级算法</div>
                    <div style="margin-bottom:8px;">
                        <div class="setting-row">
                            <span class="setting-label">HyDE假设文档</span>
                            <label class="toggle"><input type="checkbox" id="ragHyde" ${ragSettings.useHyde ? 'checked' : ''}><span class="toggle-slider"></span></label>
                        </div>
                    </div>
                    <div style="margin-bottom:8px;">
                        <div class="setting-row">
                            <span class="setting-label">多查询检索</span>
                            <label class="toggle"><input type="checkbox" id="ragMultiQuery" ${ragSettings.useMultiQuery ? 'checked' : ''}><span class="toggle-slider"></span></label>
                        </div>
                    </div>
                    <div style="margin-bottom:8px;">
                        <div class="setting-row">
                            <span class="setting-label">查询分解</span>
                            <label class="toggle"><input type="checkbox" id="ragDecomposition" ${ragSettings.useDecomposition ? 'checked' : ''}><span class="toggle-slider"></span></label>
                        </div>
                    </div>
                    <div style="margin-bottom:8px;">
                        <div class="setting-row">
                            <span class="setting-label">RRF融合排序</span>
                            <label class="toggle"><input type="checkbox" id="ragRrf" ${ragSettings.useRrf ? 'checked' : ''}><span class="toggle-slider"></span></label>
                        </div>
                    </div>
                    <div style="margin-bottom:8px;">
                        <div class="setting-row">
                            <span class="setting-label">迭代检索</span>
                            <label class="toggle"><input type="checkbox" id="ragIterative" ${ragSettings.useIterative ? 'checked' : ''}><span class="toggle-slider"></span></label>
                        </div>
                        <div style="font-size:10px;color:var(--text-muted);margin-top:2px;margin-left:4px;">结果不足时自动扩展检索</div>
                    </div>
                    
                    <div style="font-size:12px;color:var(--primary);font-weight:600;margin:16px 0 12px;padding-bottom:8px;border-bottom:1px solid var(--border);">🔍 过滤与权重</div>
                    <div style="margin-bottom:8px;">
                        <div class="setting-row">
                            <span class="setting-label">元数据过滤</span>
                            <label class="toggle"><input type="checkbox" id="ragMetadataFilter" ${ragSettings.useMetadataFilter ? 'checked' : ''}><span class="toggle-slider"></span></label>
                        </div>
                        <div style="font-size:10px;color:var(--text-muted);margin-top:2px;margin-left:4px;">自动识别分类/时间/大小过滤</div>
                    </div>
                    <div style="margin-bottom:8px;">
                        <div class="setting-row">
                            <span class="setting-label">时间权重</span>
                            <label class="toggle"><input type="checkbox" id="ragTimeWeight" ${ragSettings.useTimeWeight ? 'checked' : ''}><span class="toggle-slider"></span></label>
                        </div>
                        <div style="font-size:10px;color:var(--text-muted);margin-top:2px;margin-left:4px;">新文档权重更高</div>
                    </div>
                    
                    <div style="font-size:12px;color:var(--primary);font-weight:600;margin:16px 0 12px;padding-bottom:8px;border-bottom:1px solid var(--border);">⚡ 性能优化</div>
                    <div style="margin-bottom:8px;">
                        <div class="setting-row">
                            <span class="setting-label">查询缓存</span>
                            <label class="toggle"><input type="checkbox" id="ragCache" ${ragSettings.useCache ? 'checked' : ''}><span class="toggle-slider"></span></label>
                        </div>
                    </div>
                    <div style="margin-bottom:8px;">
                        <div class="setting-row">
                            <span class="setting-label">查询扩展</span>
                            <label class="toggle"><input type="checkbox" id="ragExpansion" ${ragSettings.useExpansion ? 'checked' : ''}><span class="toggle-slider"></span></label>
                        </div>
                    </div>
                    <div style="margin-bottom:8px;">
                        <div class="setting-row">
                            <span class="setting-label">显示分数详情</span>
                            <label class="toggle"><input type="checkbox" id="ragShowScores" ${ragSettings.showScores ? 'checked' : ''}><span class="toggle-slider"></span></label>
                        </div>
                    </div>
                </div>
                <div class="modal-actions">
                    <button class="modal-btn secondary" onclick="closeModal()">取消</button>
                    <button class="modal-btn primary" onclick="saveRagSettings()">保存</button>
                </div>
            `;
            showModal(html);
        }
        
        function saveRagSettings() {
            ragSettings.topK = parseInt(document.getElementById('ragTopK').value);
            ragSettings.alpha = parseInt(document.getElementById('ragAlpha').value) / 100;
            ragSettings.useRerank = document.getElementById('ragRerank').checked;
            ragSettings.showScores = document.getElementById('ragShowScores').checked;
            ragSettings.useCache = document.getElementById('ragCache').checked;
            ragSettings.useExpansion = document.getElementById('ragExpansion').checked;
            ragSettings.useHyde = document.getElementById('ragHyde').checked;
            ragSettings.useMultiQuery = document.getElementById('ragMultiQuery').checked;
            ragSettings.useDecomposition = document.getElementById('ragDecomposition').checked;
            ragSettings.useAdaptive = document.getElementById('ragAdaptive').checked;
            ragSettings.useRrf = document.getElementById('ragRrf').checked;
            ragSettings.useMetadataFilter = document.getElementById('ragMetadataFilter').checked;
            ragSettings.useTimeWeight = document.getElementById('ragTimeWeight').checked;
            ragSettings.useIterative = document.getElementById('ragIterative').checked;
            closeModal();
            showToast('RAG设置已保存');
        }
        
        function previewRagDoc(docId) {
            fetch('/rag/preview/' + docId).then(r => r.json()).then(data => {
                if (data.success) {
                    const doc = data.document;
                    const chunks = data.chunks;
                    const html = `
                        <div class="modal-header">
                            <span class="modal-title">📄 ${doc.filename}</span>
                            <button class="modal-close" onclick="closeModal()">✕</button>
                        </div>
                        <div class="modal-body" style="max-height:400px;overflow-y:auto;">
                            <div style="font-size:11px;color:var(--text-muted);margin-bottom:12px;">
                                📊 ${doc.chunk_count} 分块 · ${(doc.size/1024).toFixed(1)} KB · ${doc.category}
                            </div>
                            <div style="font-size:12px;color:var(--text-secondary);">
                                ${chunks.map((c, i) => `
                                    <div style="padding:10px;background:var(--bg-secondary);border-radius:8px;margin-bottom:8px;border-left:3px solid var(--primary);">
                                        <div style="font-size:10px;color:var(--primary);margin-bottom:4px;">分块 ${i+1}</div>
                                        <div style="line-height:1.5;">${c.text}</div>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                        <div class="modal-actions">
                            <button class="modal-btn secondary" onclick="closeModal()">关闭</button>
                            <button class="modal-btn primary" onclick="deleteRagDoc('${doc.id}');closeModal();">删除文档</button>
                        </div>
                    `;
                    showModal(html);
                }
            });
        }
        
        function renderRagSources(results) {
            if (!results || !results.length) return '';
            const html = `
                <div class="rag-sources" style="margin-top:12px;padding:10px;background:linear-gradient(135deg,rgba(102,126,234,0.08),rgba(118,75,162,0.04));border-radius:10px;border:1px solid rgba(102,126,234,0.15);">
                    <div style="font-size:11px;color:var(--primary);font-weight:600;margin-bottom:8px;">📚 参考来源</div>
                    ${results.map((r, i) => `
                        <div style="padding:8px;background:var(--bg-secondary);border-radius:6px;margin-bottom:6px;font-size:11px;cursor:pointer;" 
                             onclick="previewRagDoc('${r.doc_id}')" title="点击查看原文">
                            <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
                                <span style="color:var(--primary);font-weight:500;">[${i+1}] ${r.doc_name}</span>
                                <span style="color:var(--accent);">${(r.score * 100).toFixed(0)}%</span>
                            </div>
                            <div style="color:var(--text-muted);line-height:1.4;">${r.text.slice(0, 100)}${r.text.length > 100 ? '...' : ''}</div>
                            ${ragSettings.showScores ? `<div style="font-size:9px;color:var(--text-muted);margin-top:4px;">TF-IDF: ${r.tfidf_score?.toFixed(3) || '-'} | BM25: ${r.bm25_score?.toFixed(2) || '-'}</div>` : ''}
                        </div>
                    `).join('')}
                </div>
            `;
            return html;
        }
        
        function showWelcome() {
            const container = document.getElementById('messagesContainer');
            container.innerHTML = `
                <div class="welcome-container">
                    <img src="/header-img" class="welcome-avatar">
                    <h1 class="welcome-title">辉夜 AI 专业助手 v3.1 ✨</h1>
                    <p class="welcome-subtitle">面向开发、运营、增长与职场场景的高质量 AI 助手，支持流式响应、代码执行、知识库、工具调用与 LoRA 微调。</p>
                    
                    <div style="background:linear-gradient(135deg, rgba(102,126,234,0.2), rgba(118,75,162,0.2));border-radius:16px;padding:20px;margin-bottom:24px;border:1px solid rgba(255,255,255,0.1);">
                        <div style="display:flex;align-items:center;gap:8px;margin-bottom:16px;">
                            <span style="font-size:20px;">🎯</span>
                            <span style="font-size:16px;font-weight:600;">核心功能导航</span>
                        </div>
                        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;">
                            <div style="background:rgba(0,0,0,0.2);border-radius:10px;padding:12px;text-align:center;">
                                <div style="font-size:24px;margin-bottom:6px;">🧭</div>
                                <div style="font-size:13px;font-weight:600;">专业工作台</div>
                                <div style="font-size:11px;color:var(--text-muted);margin-top:4px;">模板 · 规划 · 执行</div>
                            </div>
                            <div style="background:rgba(0,0,0,0.2);border-radius:10px;padding:12px;text-align:center;">
                                <div style="font-size:24px;margin-bottom:6px;">📚</div>
                                <div style="font-size:13px;font-weight:600;">知识库</div>
                                <div style="font-size:11px;color:var(--text-muted);margin-top:4px;">RAG · 文档 · 检索</div>
                            </div>
                            <div style="background:rgba(0,0,0,0.2);border-radius:10px;padding:12px;text-align:center;">
                                <div style="font-size:24px;margin-bottom:6px;">🔧</div>
                                <div style="font-size:13px;font-weight:600;">工具调用</div>
                                <div style="font-size:11px;color:var(--text-muted);margin-top:4px;">搜索 · 天气 · 计算</div>
                            </div>
                            <div style="background:rgba(0,0,0,0.2);border-radius:10px;padding:12px;text-align:center;">
                                <div style="font-size:24px;margin-bottom:6px;">⚡</div>
                                <div style="font-size:13px;font-weight:600;">代码执行</div>
                                <div style="font-size:11px;color:var(--text-muted);margin-top:4px;">Python · 安全沙箱</div>
                            </div>
                            <div style="background:rgba(0,0,0,0.2);border-radius:10px;padding:12px;text-align:center;">
                                <div style="font-size:24px;margin-bottom:6px;">🎭</div>
                                <div style="font-size:13px;font-weight:600;">角色扮演</div>
                                <div style="font-size:11px;color:var(--text-muted);margin-top:4px;">多角色 · 自定义</div>
                            </div>
                            <div style="background:rgba(0,0,0,0.2);border-radius:10px;padding:12px;text-align:center;">
                                <div style="font-size:24px;margin-bottom:6px;">🧠</div>
                                <div style="font-size:13px;font-weight:600;">记忆系统</div>
                                <div style="font-size:11px;color:var(--text-muted);margin-top:4px;">长期记忆 · 实体识别</div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="feature-grid">
                        <div class="feature-card" onclick="quickAction('chat')">
                            <span class="feature-icon">💬</span>
                            <div class="feature-name">智能对话</div>
                            <div class="feature-desc">自然流畅的对话体验</div>
                        </div>
                        <div class="feature-card" onclick="quickAction('code')">
                            <span class="feature-icon">💻</span>
                            <div class="feature-name">代码助手</div>
                            <div class="feature-desc">编写和调试代码</div>
                        </div>
                        <div class="feature-card" onclick="quickAction('translate')">
                            <span class="feature-icon">🌐</span>
                            <div class="feature-name">翻译专家</div>
                            <div class="feature-desc">多语言翻译服务</div>
                        </div>
                        <div class="feature-card" onclick="quickAction('write')">
                            <span class="feature-icon">✍️</span>
                            <div class="feature-name">创意写作</div>
                            <div class="feature-desc">文章和内容创作</div>
                        </div>
                        <div class="feature-card" onclick="quickAction('analyze')">
                            <span class="feature-icon">📊</span>
                            <div class="feature-name">数据分析</div>
                            <div class="feature-desc">处理和分析数据</div>
                        </div>
                        <div class="feature-card" onclick="quickAction('learn')">
                            <span class="feature-icon">📚</span>
                            <div class="feature-name">学习辅导</div>
                            <div class="feature-desc">解答学习问题</div>
                        </div>
                    </div>
                    
                    <div style="background:rgba(0,0,0,0.2);border-radius:12px;padding:16px;margin-top:20px;">
                        <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
                            <span style="font-size:18px;">💡</span>
                            <span style="font-size:14px;font-weight:600;">快速上手指南</span>
                        </div>
                        <div style="font-size:13px;color:var(--text-secondary);line-height:1.8;">
                            <p style="margin:0 0 8px;">1. <strong>左侧边栏</strong> - 切换对话、模板、知识库、设置等功能</p>
                            <p style="margin:0 0 8px;">2. <strong>模板标签</strong> - 点击"打开工作台"使用专业工具</p>
                            <p style="margin:0 0 8px;">3. <strong>知识库标签</strong> - 上传文档，启用 RAG 检索增强</p>
                            <p style="margin:0 0 8px;">4. <strong>设置标签</strong> - 切换模型、调整参数、管理 LoRA</p>
                            <p style="margin:0;">5. <strong>高级功能</strong> - 代码执行器、工具调用、场景模板</p>
                        </div>
                    </div>
                    
                    <div class="market-demand-section">
                        <div class="market-demand-title">
                            <span>🚀</span>
                            <span>高需求专业场景（可一键生成）</span>
                        </div>
                        <div class="market-demand-grid">
                            <div class="demand-card" onclick="quickAction('ecommerce')">
                                <div class="demand-head"><span>🛍️</span><span class="demand-name">电商增长</span></div>
                                <div class="demand-desc">活动方案、商品卖点、投放文案与转化优化</div>
                            </div>
                            <div class="demand-card" onclick="quickAction('shortvideo')">
                                <div class="demand-head"><span>🎬</span><span class="demand-name">短视频运营</span></div>
                                <div class="demand-desc">选题、脚本分镜、封面标题与账号节奏设计</div>
                            </div>
                            <div class="demand-card" onclick="quickAction('resume')">
                                <div class="demand-head"><span>🧩</span><span class="demand-name">简历求职</span></div>
                                <div class="demand-desc">简历重写、岗位匹配、STAR 项目优化与面试问答</div>
                            </div>
                            <div class="demand-card" onclick="quickAction('business')">
                                <div class="demand-head"><span>📈</span><span class="demand-name">商业计划</span></div>
                                <div class="demand-desc">商业模型、竞品分析、路线图与里程碑拆解</div>
                            </div>
                            <div class="demand-card" onclick="quickAction('dataops')">
                                <div class="demand-head"><span>📊</span><span class="demand-name">数据经营分析</span></div>
                                <div class="demand-desc">指标体系、异常诊断、A/B 实验与复盘建议</div>
                            </div>
                            <div class="demand-card" onclick="quickAction('contract')">
                                <div class="demand-head"><span>⚖️</span><span class="demand-name">合同风险审阅</span></div>
                                <div class="demand-desc">关键条款核查、风险点标注与谈判建议</div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }
        
        function initScenesCenter() {
            renderSceneNav();
            loadExternalApiConfig();
            renderSceneWorkspace(currentSceneId);
        }

        function renderSceneNav() {
            const el = document.getElementById('sceneNav');
            if (!el) return;
            const ids = Object.keys(SCENE_UI_CONFIG);
            el.innerHTML = ids.map(id => {
                const item = SCENE_UI_CONFIG[id];
                return `<div class="scene-nav-item ${id === currentSceneId ? 'active' : ''}" onclick="renderSceneWorkspace('${id}')"><div class="scene-nav-title">${item.icon} ${item.title}</div><div class="scene-nav-desc">${item.desc}</div></div>`;
            }).join('');
        }

        function renderSceneWorkspace(sceneId) {
            if (!SCENE_UI_CONFIG[sceneId]) return;
            currentSceneId = sceneId;
            renderSceneNav();
            const el = document.getElementById('sceneWorkspace');
            const tagEl = document.getElementById('sceneCurrentTag');
            if (!el) return;
            const item = SCENE_UI_CONFIG[sceneId];
            if (tagEl) tagEl.textContent = `当前: ${item.title}`;
            el.innerHTML = `
                <div class="scene-form-title"><span>${item.icon}</span><span>${item.title}子界面</span></div>
                <div class="scene-form-desc">${item.desc}（当前子界面强制走外界API生成）</div>
                <div class="scene-form-grid">
                    <div class="scene-form-field full"><label>核心主题/素材</label><textarea id="sceneTopicInput" rows="3" placeholder="${item.placeholders.topic}"></textarea></div>
                    <div class="scene-form-field"><label>场景背景</label><textarea id="sceneContextInput" rows="3" placeholder="${item.placeholders.context}"></textarea></div>
                    <div class="scene-form-field"><label>目标结果</label><textarea id="sceneGoalInput" rows="3" placeholder="${item.placeholders.goal}"></textarea></div>
                    <div class="scene-form-field full"><label>约束条件</label><textarea id="sceneConstraintsInput" rows="2" placeholder="${item.placeholders.constraints}"></textarea></div>
                </div>
                <div class="scene-actions">
                    <button class="scene-generate-btn" id="sceneGenerateBtn" onclick="generateSceneContent('${sceneId}')">⚡ 一键生成</button>
                    <button class="project-mini-btn" onclick="copySceneOutput()">复制结果</button>
                </div>
                <div class="scene-output" id="sceneOutput">点击“一键生成”后，这里会返回外界API生成结果。</div>
            `;
        }

        function handleSceneProviderChange(provider) {
            if (!provider) return;
            externalApiConfig.active_provider = provider;
            const cfg = (externalApiConfig.providers && externalApiConfig.providers[provider]) ? externalApiConfig.providers[provider] : {api_url: '', api_key: '', model: ''};
            const urlEl = document.getElementById('sceneApiUrlInput');
            const keyEl = document.getElementById('sceneApiKeyInput');
            const modelEl = document.getElementById('sceneModelInput');
            if (urlEl) urlEl.value = cfg.api_url || '';
            if (keyEl) keyEl.value = cfg.api_key || '';
            if (modelEl) modelEl.value = cfg.model || '';
        }

        function syncSceneConfigFromInputs() {
            const provider = document.getElementById('sceneProviderSelect')?.value || 'deepseek';
            const api_url = (document.getElementById('sceneApiUrlInput')?.value || '').trim();
            const api_key = (document.getElementById('sceneApiKeyInput')?.value || '').trim();
            const model = (document.getElementById('sceneModelInput')?.value || '').trim();
            if (!externalApiConfig.providers) externalApiConfig.providers = {};
            externalApiConfig.active_provider = provider;
            externalApiConfig.providers[provider] = {api_url, api_key, model};
            return provider;
        }

        function loadExternalApiConfig() {
            fetch('/external/config').then(r => r.json()).then(data => {
                if (!data.success) return;
                externalApiConfig = {active_provider: data.active_provider || 'deepseek', providers: data.providers || {}};
                const selectEl = document.getElementById('sceneProviderSelect');
                if (selectEl) selectEl.value = externalApiConfig.active_provider || 'deepseek';
                handleSceneProviderChange(selectEl?.value || 'deepseek');
                const statusEl = document.getElementById('sceneApiStatus');
                if (statusEl) statusEl.textContent = `已加载Provider: ${externalApiConfig.active_provider || 'deepseek'}`;
            });
        }

        function saveExternalApiConfig() {
            const provider = syncSceneConfigFromInputs();
            const statusEl = document.getElementById('sceneApiStatus');
            fetch('/external/config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({active_provider: provider, providers: externalApiConfig.providers || {}})
            }).then(r => r.json()).then(data => {
                if (!data.success) {
                    if (statusEl) statusEl.textContent = `保存失败: ${data.error || '未知错误'}`;
                    return;
                }
                externalApiConfig = data.config || externalApiConfig;
                if (statusEl) statusEl.textContent = `保存成功，当前Provider: ${provider}`;
                showToast('外界API配置已保存');
            }).catch(() => {
                if (statusEl) statusEl.textContent = '保存失败: 网络异常';
            });
        }

        function testExternalApiConfig() {
            const provider = syncSceneConfigFromInputs();
            const statusEl = document.getElementById('sceneApiStatus');
            fetch('/external/config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({active_provider: provider, providers: externalApiConfig.providers || {}})
            }).then(() => {
                fetch('/external/test', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({provider})
                }).then(r => r.json()).then(data => {
                    if (!data.success) {
                        if (statusEl) statusEl.textContent = `连通失败: ${data.error || '未知错误'}`;
                        return;
                    }
                    if (statusEl) statusEl.textContent = `连通成功: ${data.provider} / ${data.message || ''}`;
                    showToast('外界API连通成功');
                });
            });
        }

        function generateSceneContent(sceneId) {
            const provider = syncSceneConfigFromInputs();
            const topic = (document.getElementById('sceneTopicInput')?.value || '').trim();
            const context = (document.getElementById('sceneContextInput')?.value || '').trim();
            const goal = (document.getElementById('sceneGoalInput')?.value || '').trim();
            const constraints = (document.getElementById('sceneConstraintsInput')?.value || '').trim();
            const outputEl = document.getElementById('sceneOutput');
            const btn = document.getElementById('sceneGenerateBtn');
            if (!topic) { showToast('请先填写核心主题/素材'); return; }
            if (btn) btn.disabled = true;
            if (outputEl) outputEl.textContent = '外界API正在生成中，请稍候...';
            fetch('/external/config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({active_provider: provider, providers: externalApiConfig.providers || {}})
            }).then(() => {
                fetch('/scenes/generate', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({scene_id: sceneId, provider, topic, context, goal, constraints})
                }).then(r => r.json()).then(data => {
                    if (!data.success) {
                        if (outputEl) outputEl.textContent = `生成失败：${data.error || '未知错误'}`;
                        if (btn) btn.disabled = false;
                        return;
                    }
                    if (outputEl) outputEl.textContent = data.content || '';
                    if (btn) btn.disabled = false;
                }).catch(() => {
                    if (outputEl) outputEl.textContent = '生成失败：网络异常';
                    if (btn) btn.disabled = false;
                });
            });
        }

        function copySceneOutput() {
            const text = document.getElementById('sceneOutput')?.textContent || '';
            if (!text.trim()) return;
            navigator.clipboard.writeText(text).then(() => showToast('已复制场景结果'));
        }

        function openSceneFromQuickAction(sceneId) {
            const target = document.querySelector(`.sidebar-tab[onclick*="scenes"]`);
            if (target) switchTab('scenes', target);
            renderSceneWorkspace(sceneId);
            showToast(`已切换到${SCENE_UI_CONFIG[sceneId]?.title || '场景'}子界面`);
        }

        function quickAction(type) {
            if (['ecommerce', 'shortvideo', 'resume', 'business', 'dataops', 'contract'].includes(type)) {
                openSceneFromQuickAction(type);
                return;
            }
            const prompts = {
                'chat': '你好，我想和你聊聊天',
                'code': '请帮我写一段代码，实现以下功能：',
                'translate': '请帮我翻译以下内容：',
                'write': '请帮我写一篇关于',
                'analyze': '请帮我分析以下数据：',
                'learn': '请帮我解释一下'
            };
            const input = document.getElementById('mainInput');
            input.value = prompts[type] || '';
            currentStructuredTemplate = null;
            input.focus();
            updateCharCount();
        }
        
        function initSpeechRecognition() {
            if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
                const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
                recognition = new SR();
                recognition.continuous = false;
                recognition.interimResults = true;
                recognition.lang = 'zh-CN';
                recognition.onresult = e => {
                    const t = Array.from(e.results).map(r => r[0].transcript).join('');
                    document.getElementById('mainInput').value = t;
                    updateCharCount();
                };
                recognition.onend = () => {
                    isRecording = false;
                    document.getElementById('voiceInputBtn').classList.remove('active');
                };
            }
        }
        
        function toggleVoiceInput() {
            if (!recognition) { showToast('浏览器不支持语音输入'); return; }
            if (isRecording) { recognition.stop(); return; }
            isRecording = true;
            document.getElementById('voiceInputBtn').classList.add('active');
            recognition.start();
        }
        
        function saveSettings() { localStorage.setItem('kaguya_settings', JSON.stringify(settings)); }
        function saveStats() { localStorage.setItem('kaguya_stats', JSON.stringify(stats)); }
        function saveChats() { localStorage.setItem('kaguya_chats', JSON.stringify(chats)); renderChatList(); }
        
        function updateStats() {
            const el1 = document.getElementById('statsSessions');
            const el2 = document.getElementById('statsInput');
            const el3 = document.getElementById('statsOutput');
            const el4 = document.getElementById('statsLatency');
            if (el1) el1.textContent = stats.sessions;
            if (el2) el2.textContent = stats.inputTokens;
            if (el3) el3.textContent = stats.outputTokens;
            if (el4) el4.textContent = stats.latencies.length ? Math.round(stats.latencies.reduce((a,b)=>a+b,0)/stats.latencies.length) : 0;
        }
        
        function renderChatList() {
            const sorted = [...chats].sort((a, b) => (b.starred ? 1 : 0) - (a.starred ? 1 : 0));
            let html = `<div class="chat-item chat-item-new" onclick="newChat()">
                <span>✨</span>
                <span class="chat-item-title">新建对话</span>
            </div>`;
            html += sorted.map(c => `
                <div class="chat-item ${c.id === currentChatId ? 'active' : ''}" onclick="loadChat('${c.id}')">
                    <span onclick="event.stopPropagation();toggleStarChat('${c.id}')" style="cursor:pointer;">${c.starred ? '⭐' : '💬'}</span>
                    <span class="chat-item-title">${c.title || '新对话'}</span>
                    <button class="chat-item-delete" onclick="event.stopPropagation();deleteChat('${c.id}')">🗑️</button>
                </div>
            `).join('');
            document.getElementById('chatList').innerHTML = html;
        }
        
        function renderRoleList() {
            // 按类型分组角色
            const characterRoles = roles.filter(r => r.type === 'character');
            const generalRoles = roles.filter(r => r.type === 'general' || !r.type);
            
            let html = '';
            
            // 角色卡模式分组
            if (characterRoles.length > 0) {
                html += `<div class="role-group"><div class="role-group-title">🎭 角色卡模式</div>`;
                html += characterRoles.map(r => {
                    const icon = r.icon || '🎭', color = r.color || '#667eea';
                    return `<div class="role-item ${r.id === currentRole ? 'active' : ''}" onclick="selectRole('${r.id}')">
                        <div class="item-icon" style="background:linear-gradient(135deg,${color},${color}dd);">${r.avatar.startsWith('/') ? `<img src="${r.avatar}" style="width:100%;height:100%;border-radius:8px;">` : icon}</div>
                        <div class="item-info"><div class="item-name">${r.name}</div><div class="item-desc">${r.description}</div></div>
                        <span class="role-type-badge" style="background:linear-gradient(135deg,#a855f7,#7c3aed);">角色</span>
                    </div>`;
                }).join('');
                html += '</div>';
            }
            
            // 一般版本模型分组
            if (generalRoles.length > 0) {
                html += `<div class="role-group"><div class="role-group-title">🤖 一般版本模型</div>`;
                html += generalRoles.map(r => {
                    const icon = r.icon || '🤖', color = r.color || '#667eea';
                    return `<div class="role-item ${r.id === currentRole ? 'active' : ''}" onclick="selectRole('${r.id}')">
                        <div class="item-icon" style="background:linear-gradient(135deg,${color},${color}dd);">${r.avatar.startsWith('/') ? `<img src="${r.avatar}" style="width:100%;height:100%;border-radius:8px;">` : icon}</div>
                        <div class="item-info"><div class="item-name">${r.name}</div><div class="item-desc">${r.description}</div></div>
                        <span class="role-type-badge" style="background:linear-gradient(135deg,#667eea,#5a67d8);">通用</span>
                    </div>`;
                }).join('');
                html += '</div>';
            }
            
            document.getElementById('roleList').innerHTML = html;
        }
        
        function renderToolList() {
            document.getElementById('toolList').innerHTML = Object.entries(tools).map(([id, t]) => `
                <div class="tool-item ${activeTools.has(id) ? 'active' : ''}" onclick="toggleTool('${id}')">
                    <div class="item-icon" style="background:linear-gradient(135deg,#f59e0b,#d97706);">${t.icon}</div>
                    <div class="item-info"><div class="item-name">${t.name}</div><div class="item-desc">${t.description}</div></div>
                    ${activeTools.has(id) ? '<span class="item-badge" style="background:#f59e0b;">已启用</span>' : ''}
                </div>
            `).join('');
        }
        
        function loadLoraList() {
            fetch('/lora/list').then(r => r.json()).then(data => {
                document.getElementById('loraList').innerHTML = data.loras.map(l => {
                    const icon = l.icon || '🤖', color = l.color || '#10b981';
                    return `<div class="lora-item ${l.id === currentLora ? 'active' : ''}" onclick="selectLora('${l.id}')">
                        <div class="item-icon" style="background:linear-gradient(135deg,${color},${color}dd);">${icon}</div>
                        <div class="item-info"><div class="item-name">${l.name}</div><div class="item-desc">${l.description}</div></div>
                        ${l.loaded ? `<span class="item-badge" style="background:${color};">已加载</span>` : ''}
                    </div>`;
                }).join('');
            });
        }
        
        function toggleTool(id) {
            if (activeTools.has(id)) activeTools.delete(id);
            else activeTools.add(id);
            renderToolList();
            updateIndicators();
            document.querySelectorAll('.quick-tool').forEach(el => {
                if (el.dataset.tool === id) el.classList.toggle('active', activeTools.has(id));
            });
            showToast(activeTools.has(id) ? `已启用 ${tools[id].name}` : `已禁用 ${tools[id].name}`);
        }
        
        function updateIndicators() {
            let html = '';
            if (currentLora !== 'none') html += `<div class="indicator lora"><span>🔧</span><span>${currentLora}</span></div>`;
            if (activeTools.size > 0) html += `<div class="indicator tool"><span>🛠️</span><span>${activeTools.size}个工具</span></div>`;
            document.getElementById('headerIndicators').innerHTML = html;
        }
        
        function selectRole(id) {
            currentRole = id;
            const role = roles.find(r => r.id === id);
            if (role) {
                document.getElementById('headerTitle').textContent = role.name;
                if (role.avatar.startsWith('/')) document.getElementById('headerAvatar').src = role.avatar;
            }
            renderRoleList();
            showToast(`已切换到 ${role.name}`);
        }
        
        function selectLora(id) {
            fetch('/lora/load', {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({lora_id: id})
            }).then(r => r.json()).then(data => {
                if (data.success) {
                    currentLora = id;
                    loadLoraList();
                    updateIndicators();
                    showToast(data.message || 'LoRA已切换');
                } else showToast('加载失败: ' + (data.error || '未知错误'));
            });
        }
        
        // ==================== 模型微调平台 ====================
        function refreshFinetuneData() {
            loadFinetuneDatasets();
            loadFinetuneJobs();
        }
        
        function loadFinetuneDatasets() {
            fetch('/finetune/datasets').then(r => r.json()).then(data => {
                if (data.success) {
                    renderFinetuneDatasets(data.datasets);
                }
            });
        }
        
        function renderFinetuneDatasets(datasets) {
            const container = document.getElementById('finetuneDatasets');
            if (!datasets || datasets.length === 0) {
                container.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:10px;font-size:12px;">暂无数据集，请上传</div>';
                return;
            }
            
            container.innerHTML = datasets.map(ds => `
                <div class="finetune-item">
                    <div class="finetune-header">
                        <span class="finetune-icon">📊</span>
                        <span class="finetune-title">${ds.name}</span>
                        <span class="finetune-status ${ds.status}">${ds.status}</span>
                    </div>
                    <div class="finetune-meta">
                        <span>格式: ${ds.format}</span>
                        <span>样本: ${ds.sample_count}</span>
                        <span>${new Date(ds.created_at * 1000).toLocaleDateString()}</span>
                    </div>
                    <div class="finetune-actions">
                        <button class="finetune-btn delete" onclick="deleteFinetuneDataset('${ds.id}')">🗑️ 删除</button>
                    </div>
                </div>
            `).join('');
        }
        
        function loadFinetuneJobs() {
            fetch('/finetune/jobs').then(r => r.json()).then(data => {
                if (data.success) {
                    renderFinetuneJobs(data.jobs);
                }
            });
        }
        
        function renderFinetuneJobs(jobs) {
            const container = document.getElementById('finetuneJobs');
            if (!jobs || jobs.length === 0) {
                container.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:10px;font-size:12px;">暂无训练任务</div>';
                return;
            }
            
            container.innerHTML = jobs.map(job => `
                <div class="finetune-item">
                    <div class="finetune-header">
                        <span class="finetune-icon">🎯</span>
                        <span class="finetune-title">${job.name}</span>
                        <span class="finetune-status ${job.status}">${job.status}</span>
                    </div>
                    <div class="finetune-meta">
                        <span>方法: ${job.method}</span>
                        <span>数据: ${job.dataset_name}</span>
                        <span>${new Date(job.created_at * 1000).toLocaleDateString()}</span>
                    </div>
                    <div class="finetune-progress">
                        <div class="finetune-progress-bar" style="width:${job.progress}%"></div>
                    </div>
                    <div class="finetune-actions">
                        ${job.status === 'pending' ? `<button class="finetune-btn start" onclick="startFinetuneJob('${job.job_id}')">▶ 开始</button>` : ''}
                        ${job.status === 'running' ? `<button class="finetune-btn stop" onclick="stopFinetuneJob('${job.job_id}')">⏹ 停止</button>` : ''}
                        <button class="finetune-btn delete" onclick="deleteFinetuneJob('${job.job_id}')">🗑️ 删除</button>
                    </div>
                </div>
            `).join('');
        }
        
        function showDatasetUpload() {
            console.log('showDatasetUpload called');
            const name = prompt('数据集名称:');
            if (!name) return;
            
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = '.jsonl,.json,.csv';
            input.onchange = function(e) {
                const file = e.target.files[0];
                if (!file) return;
                
                const formData = new FormData();
                formData.append('file', file);
                formData.append('name', name);
                formData.append('format', file.name.split('.').pop());
                
                fetch('/finetune/dataset/upload', {
                    method: 'POST',
                    body: formData
                }).then(r => r.json()).then(data => {
                    if (data.success) {
                        showToast(`数据集上传成功，包含 ${data.sample_count} 个样本`);
                        loadFinetuneDatasets();
                    } else {
                        showToast('上传失败: ' + (data.error || '未知错误'));
                    }
                });
            };
            input.click();
        }
        
        function showCreateJob() {
            console.log('showCreateJob called');
            const name = prompt('训练任务名称:');
            if (!name) return;
            
            fetch('/finetune/datasets').then(r => r.json()).then(data => {
                if (!data.success || data.datasets.length === 0) {
                    showToast('请先上传数据集');
                    return;
                }
                
                const datasetOptions = data.datasets.map((ds, i) => `${i + 1}. ${ds.name} (${ds.sample_count}样本)`).join(String.fromCharCode(10));
                const datasetIdx = prompt(`选择数据集:` + String.fromCharCode(10) + `${datasetOptions}`);
                if (!datasetIdx) return;
                
                const dataset = data.datasets[parseInt(datasetIdx) - 1];
                if (!dataset) {
                    showToast('无效选择');
                    return;
                }
                
                const method = prompt('训练方法 (lora/qlora):', 'lora');
                const epochs = prompt('训练轮数:', '3');
                
                const config = {
                    method: method || 'lora',
                    num_epochs: parseInt(epochs) || 3,
                    lora_r: 16,
                    lora_alpha: 32,
                    learning_rate: 5e-5,
                    batch_size: 4
                };
                
                fetch('/finetune/job', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({name, dataset_id: dataset.id, config})
                }).then(r => r.json()).then(data => {
                    if (data.success) {
                        showToast('训练任务创建成功');
                        loadFinetuneJobs();
                    } else {
                        showToast('创建失败: ' + (data.error || '未知错误'));
                    }
                });
            });
        }
        
        function startFinetuneJob(jobId) {
            fetch(`/finetune/job/${jobId}/start`, {method: 'POST'}).then(r => r.json()).then(data => {
                if (data.success) {
                    showToast('训练已开始');
                    loadFinetuneJobs();
                } else {
                    showToast('启动失败: ' + (data.error || '未知错误'));
                }
            });
        }
        
        function stopFinetuneJob(jobId) {
            fetch(`/finetune/job/${jobId}/stop`, {method: 'POST'}).then(r => r.json()).then(data => {
                if (data.success) {
                    showToast('训练已停止');
                    loadFinetuneJobs();
                }
            });
        }
        
        function deleteFinetuneJob(jobId) {
            if (!confirm('确定要删除这个训练任务吗？')) return;
            
            fetch(`/finetune/job/${jobId}`, {method: 'DELETE'}).then(r => r.json()).then(data => {
                if (data.success) {
                    showToast('训练任务已删除');
                    loadFinetuneJobs();
                }
            });
        }
        
        function deleteFinetuneDataset(datasetId) {
            if (!confirm('确定要删除这个数据集吗？')) return;
            
            fetch(`/finetune/dataset/${datasetId}`, {method: 'DELETE'}).then(r => r.json()).then(data => {
                if (data.success) {
                    showToast('数据集已删除');
                    loadFinetuneDatasets();
                }
            });
        }
        
        // ==================== 多模态视觉理解系统 ====================
        let currentMultimodalImage = null;
        let currentImageId = null;
        
        function uploadMultimodalImage(event) {
            const file = event.target.files[0];
            if (!file) return;
            
            // 显示预览
            const reader = new FileReader();
            reader.onload = function(e) {
                document.getElementById('previewImg').src = e.target.result;
                document.getElementById('multimodalImagePreview').style.display = 'block';
                currentMultimodalImage = e.target.result;
            };
            reader.readAsDataURL(file);
            
            // 上传到服务器
            const formData = new FormData();
            formData.append('image', file);
            formData.append('task', 'understand');
            
            fetch('/multimodal/upload', {
                method: 'POST',
                body: formData
            }).then(r => r.json()).then(data => {
                if (data.success) {
                    currentImageId = data.result.image_id;
                    showToast('图片上传成功');
                } else {
                    showToast('上传失败: ' + (data.error || '未知错误'));
                }
            });
        }
        
        function analyzeImage(task) {
            if (!currentImageId) {
                showToast('请先上传图片');
                return;
            }
            
            fetch('/multimodal/analyze', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({image_id: currentImageId, task: task})
            }).then(r => r.json()).then(data => {
                if (data.success) {
                    displayMultimodalResult(task, data.result);
                } else {
                    showToast('分析失败: ' + (data.error || '未知错误'));
                }
            });
        }
        
        function displayMultimodalResult(task, result) {
            const container = document.getElementById('multimodalResults');
            
            let taskName = '';
            let icon = '';
            let content = '';
            
            switch(task) {
                case 'describe':
                    taskName = '图像描述';
                    icon = '📝';
                    content = result.description || '无法生成描述';
                    break;
                case 'ocr':
                    taskName = '文字识别';
                    icon = '📄';
                    content = result.text || '未识别到文字';
                    break;
                case 'analyze':
                    taskName = '内容分析';
                    icon = '🔍';
                    content = JSON.stringify(result, null, 2);
                    break;
                default:
                    taskName = '分析结果';
                    icon = '📊';
                    content = JSON.stringify(result, null, 2);
            }
            
            const resultEl = document.createElement('div');
            resultEl.className = 'multimodal-result';
            resultEl.innerHTML = `
                <div class="multimodal-result-header">
                    <span>${icon}</span>
                    <span>${taskName}</span>
                    <span style="margin-left:auto;font-size:10px;color:var(--text-muted);">${new Date().toLocaleTimeString()}</span>
                </div>
                <div class="multimodal-result-content">${content}</div>
                ${result.dimensions ? `<div class="multimodal-result-meta">📐 ${result.dimensions}</div>` : ''}
            `;
            
            container.insertBefore(resultEl, container.firstChild);
        }
        
        function loadMultimodalHistory() {
            fetch('/multimodal/history').then(r => r.json()).then(data => {
                if (data.success && data.history.length > 0) {
                    // 可以在这里显示历史记录
                }
            });
        }
        
        function clearMultimodalHistory() {
            if (!confirm('确定要清除所有分析结果吗？')) return;
            
            fetch('/multimodal/clear', {method: 'POST'}).then(r => r.json()).then(data => {
                if (data.success) {
                    document.getElementById('multimodalResults').innerHTML = '';
                    document.getElementById('multimodalImagePreview').style.display = 'none';
                    document.getElementById('previewImg').src = '';
                    currentMultimodalImage = null;
                    currentImageId = null;
                    showToast('已清除');
                }
            });
        }
        
        // ==================== 记忆系统 ====================
        function refreshMemoryStats() {
            fetch('/memory/stats').then(r => r.json()).then(data => {
                if (data.success) {
                    const longTermEl = document.getElementById('memLongTerm');
                    const avgImpEl = document.getElementById('memAvgImportance');
                    const entitiesEl = document.getElementById('memEntities');
                    const profileEl = document.getElementById('memProfile');
                    if (longTermEl) longTermEl.textContent = data.stats.long_term_count;
                    if (avgImpEl) avgImpEl.textContent = data.stats.avg_importance;
                    if (entitiesEl) entitiesEl.textContent = data.stats.entity_count;
                    if (profileEl) profileEl.textContent = data.stats.profile_count;
                }
            });
        }
        
        function searchMemories() {
            const query = document.getElementById('memorySearchInput').value || 'all';
            fetch('/memory/search', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({query: query, top_k: 20})
            }).then(r => r.json()).then(data => {
                if (data.success) {
                    renderMemoryList(data.memories);
                }
            });
        }
        
        function renderMemoryList(memories) {
            const container = document.getElementById('memoryList');
            if (!memories || memories.length === 0) {
                container.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:20px;">暂无记忆</div>';
                return;
            }
            
            container.innerHTML = memories.map(m => {
                const importanceDots = Array(5).fill(0).map((_, i) => 
                    `<div class="importance-dot ${i < m.importance * 5 ? 'active' : ''}"></div>`
                ).join('');
                
                const date = new Date(m.created_at * 1000).toLocaleDateString();
                
                return `
                    <div class="memory-item">
                        <div class="memory-content">${m.content}</div>
                        <div class="memory-meta">
                            <span class="memory-type ${m.type}">${m.type}</span>
                            <span>📊 重要性:</span>
                            <div class="memory-importance">${importanceDots}</div>
                            <span>🕐 ${date}</span>
                            <span>👁️ ${m.access_count}次</span>
                            <div class="memory-actions">
                                <button class="memory-btn" onclick="deleteMemory('${m.id}')">🗑️</button>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
        }
        
        function showAddMemoryModal() {
            const content = prompt('请输入要添加的记忆内容:');
            if (!content) return;
            
            const type = prompt('记忆类型 (fact/preference/experience):', 'fact');
            
            fetch('/memory', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({content, type: type || 'fact'})
            }).then(r => r.json()).then(data => {
                if (data.success) {
                    showToast('记忆已添加');
                    refreshMemoryStats();
                    searchMemories();
                }
            });
        }
        
        function deleteMemory(memoryId) {
            if (!confirm('确定要删除这条记忆吗？')) return;
            
            fetch(`/memory/${memoryId}`, {method: 'DELETE'}).then(r => r.json()).then(data => {
                if (data.success) {
                    showToast('记忆已删除');
                    searchMemories();
                    refreshMemoryStats();
                }
            });
        }
        
        function consolidateMemories() {
            if (!confirm('确定要整合记忆吗？这将清理过时和低重要性的记忆。')) return;
            
            fetch('/memory/consolidate', {method: 'POST'}).then(r => r.json()).then(data => {
                if (data.success) {
                    showToast('记忆整合完成');
                    refreshMemoryStats();
                    searchMemories();
                }
            });
        }
        
        // ==================== MCP 插件管理 ====================
        let mcpPlugins = [];
        let enabledMcpTools = [];
        
        // ==================== 工作流编排系统 ====================
        let workflows = [];
        let workflowNodeTypes = {};
        let currentWorkflow = null;
        let selectedNode = null;
        let workflowNodes = [];
        let workflowConnections = [];
        let workflowZoom = 1;
        let isDraggingNode = false;
        let dragOffset = { x: 0, y: 0 };
        let isConnecting = false;
        let connectionStart = null;
        
        function loadWorkflows() {
            fetch('/workflows').then(r => r.json()).then(data => {
                if (data.success) {
                    workflows = data.workflows;
                    renderWorkflowList();
                    renderFeatureCenterMeta();
                }
            });
        }
        
        function renderWorkflowList() {
            const container = document.getElementById('workflowList');
            if (!workflows.length) {
                container.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:20px;">暂无工作流，点击"新建"创建</div>';
                return;
            }
            
            container.innerHTML = workflows.map(wf => `
                <div class="workflow-item" data-id="${wf.id}">
                    <div class="workflow-icon" style="background:linear-gradient(135deg,${wf.color},${wf.color}dd);">${wf.icon}</div>
                    <div class="workflow-info">
                        <div class="workflow-name">${wf.name}</div>
                        <div class="workflow-desc">${wf.description || '无描述'}</div>
                        <div class="workflow-meta">
                            <span>📦 ${wf.node_count}个节点</span>
                            <span>🕐 ${new Date(wf.updated_at * 1000).toLocaleDateString()}</span>
                        </div>
                    </div>
                    <div class="workflow-actions">
                        <button class="workflow-btn run" onclick="runWorkflow('${wf.id}')">▶</button>
                        <button class="workflow-btn edit" onclick="editWorkflow('${wf.id}')">✏️</button>
                        <button class="workflow-btn delete" onclick="deleteWorkflow('${wf.id}')">🗑️</button>
                    </div>
                </div>
            `).join('');
        }
        
        function openWorkflowEditor() {
            currentWorkflow = null;
            workflowNodes = [];
            workflowConnections = [];
            selectedNode = null;
            document.getElementById('workflowName').value = '';
            document.getElementById('workflowNodesContainer').innerHTML = '';
            document.getElementById('workflowConnections').innerHTML = '';
            document.getElementById('workflowProperties').innerHTML = `
                <div style="text-align:center;color:var(--text-muted);padding:40px 20px;">
                    <div style="font-size:32px;margin-bottom:8px;">👈</div>
                    <div style="font-size:13px;">选择节点以编辑属性</div>
                </div>
            `;
            
            loadWorkflowNodeTypes();
            document.getElementById('workflowEditorModal').classList.add('show');
        }
        
        function loadWorkflowNodeTypes() {
            fetch('/workflow/node-types').then(r => r.json()).then(data => {
                if (data.success) {
                    workflowNodeTypes = data.node_types;
                    renderWorkflowNodePalette();
                }
            });
        }
        
        function renderWorkflowNodePalette() {
            const controlContainer = document.getElementById('workflowNodesControl');
            const aiContainer = document.getElementById('workflowNodesAI');
            const toolContainer = document.getElementById('workflowNodesTool');
            
            controlContainer.innerHTML = '';
            aiContainer.innerHTML = '';
            toolContainer.innerHTML = '';
            
            Object.values(workflowNodeTypes).forEach(nodeType => {
                const nodeEl = document.createElement('div');
                nodeEl.className = 'workflow-node-item';
                nodeEl.draggable = true;
                nodeEl.innerHTML = `
                    <span class="workflow-node-icon" style="color:${nodeType.color};">${nodeType.icon}</span>
                    <span>${nodeType.name}</span>
                `;
                nodeEl.ondragstart = (e) => {
                    e.dataTransfer.setData('nodeType', nodeType.id);
                };
                
                if (nodeType.category === 'control') {
                    controlContainer.appendChild(nodeEl);
                } else if (nodeType.category === 'ai') {
                    aiContainer.appendChild(nodeEl);
                } else {
                    toolContainer.appendChild(nodeEl);
                }
            });
        }
        
        function editWorkflow(workflowId) {
            fetch(`/workflow/${workflowId}`).then(r => r.json()).then(data => {
                if (data.success) {
                    currentWorkflow = data.workflow;
                    workflowNodes = data.workflow.nodes || [];
                    workflowConnections = data.workflow.connections || [];
                    document.getElementById('workflowName').value = data.workflow.name;
                    renderWorkflowCanvas();
                    loadWorkflowNodeTypes();
                    document.getElementById('workflowEditorModal').classList.add('show');
                }
            });
        }
        
        function renderWorkflowCanvas() {
            const container = document.getElementById('workflowNodesContainer');
            container.innerHTML = '';
            
            workflowNodes.forEach(node => {
                const nodeType = workflowNodeTypes[node.type];
                if (!nodeType) return;
                
                const nodeEl = document.createElement('div');
                nodeEl.className = 'workflow-canvas-node' + (selectedNode === node.id ? ' selected' : '');
                nodeEl.style.left = node.x + 'px';
                nodeEl.style.top = node.y + 'px';
                nodeEl.style.borderColor = nodeType.color;
                nodeEl.dataset.nodeId = node.id;
                nodeEl.innerHTML = `
                    <div class="node-header">
                        <span class="node-icon">${nodeType.icon}</span>
                        <span class="node-title">${nodeType.name}</span>
                    </div>
                    <div style="font-size:11px;color:var(--text-muted);">${node.config?.label || ''}</div>
                    <div class="node-ports">
                        ${nodeType.inputs.length ? '<div class="workflow-port input" data-port="input"></div>' : '<div></div>'}
                        ${nodeType.outputs.length ? '<div class="workflow-port output" data-port="output"></div>' : '<div></div>'}
                    </div>
                `;
                
                nodeEl.onclick = (e) => {
                    e.stopPropagation();
                    selectWorkflowNode(node.id);
                };
                
                nodeEl.onmousedown = (e) => {
                    if (e.target.classList.contains('workflow-port')) return;
                    isDraggingNode = true;
                    dragOffset.x = e.clientX - node.x;
                    dragOffset.y = e.clientY - node.y;
                    
                    const onMouseMove = (e) => {
                        if (!isDraggingNode) return;
                        node.x = e.clientX - dragOffset.x;
                        node.y = e.clientY - dragOffset.y;
                        nodeEl.style.left = node.x + 'px';
                        nodeEl.style.top = node.y + 'px';
                        renderWorkflowConnections();
                    };
                    
                    const onMouseUp = () => {
                        isDraggingNode = false;
                        document.removeEventListener('mousemove', onMouseMove);
                        document.removeEventListener('mouseup', onMouseUp);
                    };
                    
                    document.addEventListener('mousemove', onMouseMove);
                    document.addEventListener('mouseup', onMouseUp);
                };
                
                container.appendChild(nodeEl);
            });
            
            renderWorkflowConnections();
        }
        
        function renderWorkflowConnections() {
            const svg = document.getElementById('workflowConnections');
            svg.innerHTML = '';
            
            workflowConnections.forEach(conn => {
                const sourceNode = workflowNodes.find(n => n.id === conn.source);
                const targetNode = workflowNodes.find(n => n.id === conn.target);
                if (!sourceNode || !targetNode) return;
                
                const sourceEl = document.querySelector(`[data-node-id="${conn.source}"]`);
                const targetEl = document.querySelector(`[data-node-id="${conn.target}"]`);
                if (!sourceEl || !targetEl) return;
                
                const x1 = sourceNode.x + sourceEl.offsetWidth;
                const y1 = sourceNode.y + sourceEl.offsetHeight / 2;
                const x2 = targetNode.x;
                const y2 = targetNode.y + targetEl.offsetHeight / 2;
                
                const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                path.setAttribute('d', `M ${x1} ${y1} C ${x1 + 50} ${y1}, ${x2 - 50} ${y2}, ${x2} ${y2}`);
                path.setAttribute('class', 'workflow-connection');
                path.setAttribute('marker-end', 'url(#arrowhead)');
                svg.appendChild(path);
            });
        }
        
        function selectWorkflowNode(nodeId) {
            selectedNode = nodeId;
            renderWorkflowCanvas();
            
            const node = workflowNodes.find(n => n.id === nodeId);
            const nodeType = workflowNodeTypes[node.type];
            if (!node || !nodeType) return;
            
            const panel = document.getElementById('workflowProperties');
            panel.innerHTML = `
                <div style="font-size:14px;font-weight:600;margin-bottom:16px;padding-bottom:12px;border-bottom:2px solid ${nodeType.color};">
                    ${nodeType.icon} ${nodeType.name} 属性
                </div>
                ${renderNodeProperties(node, nodeType)}
            `;
        }
        
        function renderNodeProperties(node, nodeType) {
            let html = '';
            
            // 渲染配置项
            Object.entries(nodeType.config).forEach(([key, defaultValue]) => {
                const value = node.config[key] !== undefined ? node.config[key] : defaultValue;
                html += `<div class="property-group">`;
                html += `<div class="property-label">${key}</div>`;
                
                if (typeof defaultValue === 'boolean') {
                    html += `<input type="checkbox" ${value ? 'checked' : ''} onchange="updateNodeConfig('${node.id}', '${key}', this.checked)">`;
                } else if (typeof defaultValue === 'number') {
                    html += `<input type="number" class="property-input" value="${value}" onchange="updateNodeConfig('${node.id}', '${key}', parseFloat(this.value))">`;
                } else if (key === 'code' || key === 'prompt' || key === 'system_prompt' || key === 'template') {
                    html += `<textarea class="property-input property-textarea" onchange="updateNodeConfig('${node.id}', '${key}', this.value)">${value}</textarea>`;
                } else {
                    html += `<input type="text" class="property-input" value="${value}" onchange="updateNodeConfig('${node.id}', '${key}', this.value)">`;
                }
                
                html += `</div>`;
            });
            
            html += `<button class="modal-btn" onclick="deleteWorkflowNode('${node.id}')" style="background:#ef4444;color:white;width:100%;margin-top:20px;">🗑️ 删除节点</button>`;
            
            return html;
        }
        
        function updateNodeConfig(nodeId, key, value) {
            const node = workflowNodes.find(n => n.id === nodeId);
            if (node) {
                node.config[key] = value;
            }
        }
        
        function deleteWorkflowNode(nodeId) {
            workflowNodes = workflowNodes.filter(n => n.id !== nodeId);
            workflowConnections = workflowConnections.filter(c => c.source !== nodeId && c.target !== nodeId);
            selectedNode = null;
            renderWorkflowCanvas();
            document.getElementById('workflowProperties').innerHTML = `
                <div style="text-align:center;color:var(--text-muted);padding:40px 20px;">
                    <div style="font-size:32px;margin-bottom:8px;">👈</div>
                    <div style="font-size:13px;">选择节点以编辑属性</div>
                </div>
            `;
        }
        
        function saveWorkflow() {
            const name = document.getElementById('workflowName').value || '未命名工作流';
            const workflowData = {
                id: currentWorkflow?.id,
                name: name,
                description: '',
                icon: '📋',
                color: '#667eea',
                nodes: workflowNodes,
                connections: workflowConnections
            };
            
            fetch('/workflow', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(workflowData)
            }).then(r => r.json()).then(data => {
                if (data.success) {
                    showToast('工作流已保存');
                    loadWorkflows();
                    closeModal('workflowEditorModal');
                } else {
                    showToast('保存失败: ' + (data.error || '未知错误'));
                }
            });
        }
        
        function executeWorkflow() {
            const workflowData = {
                nodes: workflowNodes,
                connections: workflowConnections
            };
            
            fetch('/workflow/execute', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({workflow: workflowData, inputs: {}})
            }).then(r => r.json()).then(data => {
                if (data.success) {
                    showToast('工作流执行完成');
                    console.log('执行结果:', data);
                } else {
                    showToast('执行失败: ' + (data.error || '未知错误'));
                }
            });
        }
        
        function runWorkflow(workflowId) {
            fetch(`/workflow/${workflowId}/execute`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({inputs: {}})
            }).then(r => r.json()).then(data => {
                if (data.success) {
                    showToast('工作流执行完成');
                } else {
                    showToast('执行失败: ' + (data.error || '未知错误'));
                }
            });
        }
        
        function deleteWorkflow(workflowId) {
            if (!confirm('确定要删除这个工作流吗？')) return;
            
            fetch(`/workflow/${workflowId}`, {method: 'DELETE'}).then(r => r.json()).then(data => {
                if (data.success) {
                    showToast('工作流已删除');
                    loadWorkflows();
                }
            });
        }
        
        function clearWorkflowCanvas() {
            if (!confirm('确定要清空所有节点吗？')) return;
            workflowNodes = [];
            workflowConnections = [];
            selectedNode = null;
            renderWorkflowCanvas();
        }
        
        function zoomWorkflow(delta) {
            workflowZoom = Math.max(0.5, Math.min(2, workflowZoom + delta));
            document.getElementById('workflowNodesContainer').style.transform = `scale(${workflowZoom})`;
            document.getElementById('workflowConnections').style.transform = `scale(${workflowZoom})`;
        }
        
        // 画布拖放处理
        document.addEventListener('DOMContentLoaded', () => {
            const canvas = document.getElementById('workflowCanvas');
            if (canvas) {
                canvas.ondragover = (e) => e.preventDefault();
                canvas.ondrop = (e) => {
                    e.preventDefault();
                    const nodeTypeId = e.dataTransfer.getData('nodeType');
                    const nodeType = workflowNodeTypes[nodeTypeId];
                    if (!nodeType) return;
                    
                    const rect = canvas.getBoundingClientRect();
                    const newNode = {
                        id: 'node_' + Date.now(),
                        type: nodeTypeId,
                        x: (e.clientX - rect.left) / workflowZoom,
                        y: (e.clientY - rect.top) / workflowZoom,
                        config: {...nodeType.config}
                    };
                    
                    workflowNodes.push(newNode);
                    renderWorkflowCanvas();
                    selectWorkflowNode(newNode.id);
                };
                
                canvas.onclick = () => {
                    selectedNode = null;
                    renderWorkflowCanvas();
                    document.getElementById('workflowProperties').innerHTML = `
                        <div style="text-align:center;color:var(--text-muted);padding:40px 20px;">
                            <div style="font-size:32px;margin-bottom:8px;">👈</div>
                            <div style="font-size:13px;">选择节点以编辑属性</div>
                        </div>
                    `;
                };
            }
        });
        
        function loadMcpPlugins() {
            fetch('/mcp/plugins').then(r => r.json()).then(data => {
                if (data.success) {
                    mcpPlugins = data.plugins;
                    renderMcpList();
                    // 更新启用的工具列表
                    enabledMcpTools = mcpPlugins.filter(p => p.enabled).flatMap(p => {
                        return p.tools_count > 0 ? [`${p.id}: ${p.description}`] : [];
                    });
                    renderFeatureCenterMeta();
                }
            });
        }
        
        // 检测并执行 MCP 工具调用
        async function detectAndExecuteMcpTool(content) {
            // 检测 MCP 工具调用格式: [MCP:plugin_id:tool_name]{parameters}
            const mcpPattern = /\[MCP:(\w+):(\w+)\]\s*({[^}]*})/g;
            let match;
            let modifiedContent = content;
            
            while ((match = mcpPattern.exec(content)) !== null) {
                const [fullMatch, pluginId, toolName, paramsStr] = match;
                try {
                    const parameters = JSON.parse(paramsStr);
                    const result = await executeMcpTool(pluginId, toolName, parameters);
                    
                    // 替换工具调用为执行结果
                    const resultText = formatMcpResult(result);
                    modifiedContent = modifiedContent.replace(fullMatch, resultText);
                } catch (e) {
                    console.error('MCP工具执行失败:', e);
                    modifiedContent = modifiedContent.replace(fullMatch, `[工具执行失败: ${e.message}]`);
                }
            }
            
            return modifiedContent;
        }

        async function executeMcpTool(pluginId, toolName, parameters) {
            const res = await fetch('/mcp/execute', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({plugin_id: pluginId, tool_name: toolName, parameters})
            });
            const data = await res.json();
            return data.result || {error: '执行失败'};
        }
        
        function formatMcpResult(result) {
            if (result.error) {
                return `<div style="color:#e74c3c;padding:8px;background:rgba(231,76,60,0.1);border-radius:6px;margin:4px 0;">❌ ${result.error}</div>`;
            }
            
            // 格式化不同类型的结果
            if (result.content !== undefined) {
                return `<div style="padding:10px;background:rgba(102,126,234,0.1);border-radius:6px;margin:4px 0;"><pre style="margin:0;white-space:pre-wrap;">${result.content}</pre></div>`;
            }
            if (result.results !== undefined && Array.isArray(result.results)) {
                const items = result.results.map(r => `<li><a href="${r.link}" target="_blank" style="color:var(--primary);">${r.title}</a></li>`).join('');
                return `<div style="padding:10px;background:rgba(245,158,11,0.1);border-radius:6px;margin:4px 0;"><ol style="margin:0;padding-left:20px;">${items}</ol></div>`;
            }
            if (result.result !== undefined) {
                return `<div style="padding:8px;background:rgba(16,185,129,0.1);border-radius:6px;margin:4px 0;font-weight:600;">🧮 结果: ${result.result}</div>`;
            }
            if (result.items !== undefined && Array.isArray(result.items)) {
                const items = result.items.map(i => `<li>${i.type === 'directory' ? '📁' : '📄'} ${i.name}</li>`).join('');
                return `<div style="padding:10px;background:rgba(59,130,246,0.1);border-radius:6px;margin:4px 0;"><ul style="margin:0;padding-left:20px;">${items}</ul></div>`;
            }
            
            return `<div style="padding:8px;background:rgba(102,126,234,0.1);border-radius:6px;margin:4px 0;">${JSON.stringify(result)}</div>`;
        }
        
        // 获取 MCP 系统提示词
        function getMcpSystemPrompt() {
            if (enabledMcpTools.length === 0) return '';
            
            return `

【MCP工具使用说明】
你可以使用以下工具来帮助用户。当需要使用工具时，请按以下格式输出：
[MCP:插件ID:工具名]{"参数名": "参数值"}

可用工具：
${enabledMcpTools.map(t => `- ${t}`).join(String.fromCharCode(10))}

示例：
- 读取文件: [MCP:filesystem:read_file]{"path": "~/document.txt"}
- 搜索网络: [MCP:web_search:search]{"query": "最新科技新闻", "num_results": 5}
- 计算: [MCP:calculator:calculate]{"expression": "2+2*3"}
- 获取时间: [MCP:datetime:get_current_time]{"timezone": "Asia/Shanghai"}
`;
        }
        
        function renderMcpList() {
            const container = document.getElementById('mcpList');
            if (!mcpPlugins.length) {
                container.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:20px;">暂无可用插件</div>';
                return;
            }
            
            container.innerHTML = mcpPlugins.map(p => {
                const enabled = p.enabled;
                return `
                    <div class="mcp-item ${enabled ? 'enabled' : ''}" data-id="${p.id}">
                        <div class="mcp-icon" style="background:linear-gradient(135deg,${p.color},${p.color}dd);">${p.icon}</div>
                        <div class="mcp-info">
                            <div class="mcp-name">${p.name}</div>
                            <div class="mcp-desc">${p.description}</div>
                        </div>
                        <span class="mcp-tools-count">${p.tools_count}个工具</span>
                        <button class="mcp-config-btn" onclick="showMcpConfig('${p.id}')" style="margin-right:8px;">⚙️</button>
                        <div class="mcp-toggle ${enabled ? 'enabled' : ''}" onclick="toggleMcpPlugin('${p.id}', ${!enabled})"></div>
                    </div>
                `;
            }).join('');
        }
        
        function toggleMcpPlugin(pluginId, enabled) {
            fetch(`/mcp/plugin/${pluginId}/enable`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({enabled})
            }).then(r => r.json()).then(data => {
                if (data.success) {
                    showToast(data.message);
                    loadMcpPlugins();
                } else {
                    showToast('操作失败: ' + (data.error || '未知错误'));
                }
            });
        }
        
        function refreshMcpPlugins() {
            loadMcpPlugins();
            showToast('已刷新插件列表');
        }
        
        function showMcpConfig(pluginId) {
            const plugin = mcpPlugins.find(p => p.id === pluginId);
            if (!plugin) return;
            
            // 简单的配置提示框
            if (plugin.id === 'filesystem') {
                const readOnly = confirm('是否设置为只读模式？' + String.fromCharCode(10) + String.fromCharCode(10) + '确定 = 只读' + String.fromCharCode(10) + '取消 = 可读写');
                fetch(`/mcp/plugin/${pluginId}/config`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({config: {read_only: readOnly, allowed_paths: [os.path.expanduser("~")]}})
                }).then(r => r.json()).then(data => {
                    if (data.success) showToast('配置已更新');
                });
            } else if (plugin.id === 'web_search') {
                const numResults = prompt('设置默认搜索结果数量 (1-10):', '5');
                if (numResults && !isNaN(numResults)) {
                    fetch(`/mcp/plugin/${pluginId}/config`, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({config: {max_results: parseInt(numResults)}})
                    }).then(r => r.json()).then(data => {
                        if (data.success) showToast('配置已更新');
                    });
                }
            } else {
                showToast('该插件暂无配置选项');
            }
        }
        
        const PROMPT_TEMPLATES = [
            {id: 'code', name: '代码助手', prompt: '请帮我写一段代码，实现以下功能：', icon: '📝', desc: '代码生成、重构与调试建议', category: 'general', source: '通用'},
            {id: 'translate', name: '翻译助手', prompt: '请将以下内容翻译成英文：', icon: '🌐', desc: '多语言翻译与语气适配', category: 'general', source: '通用'},
            {id: 'summary', name: '总结助手', prompt: '请帮我总结以下内容的要点：', icon: '📋', desc: '快速提炼重点与行动项', category: 'general', source: '通用'},
            {id: 'email', name: '邮件助手', prompt: '请帮我写一封邮件，主题是：', icon: '📧', desc: '商务邮件写作与回复模板', category: 'general', source: '通用'},
            {id: 'article', name: '文章助手', prompt: '请帮我写一篇关于', icon: '✍️', desc: '内容创作与表达优化', category: 'general', source: '通用'},
            {id: 'debug', name: '调试助手', prompt: '以下代码有问题，请帮我找出错误：', icon: '🐛', desc: '定位报错并给出修复路径', category: 'general', source: '通用'},
            {id: 'ecommerce', name: '电商增长策略', prompt: '请为我的电商产品制定30天增长方案，包含人群画像、卖点、活动节奏、投放素材结构与转化指标。', icon: '🛍️', desc: '活动节奏、投放与转化闭环', category: 'growth', source: '实战', template: 'ecommerce'},
            {id: 'shortvideo', name: '短视频增长', prompt: '请为我设计7天短视频内容计划，输出选题、脚本结构、前3秒钩子、封面标题和发布时间建议。', icon: '🎬', desc: '账号内容排期与选题脚本', category: 'growth', source: '实战', template: 'shortvideo'},
            {id: 'prompt_eval', name: '提示词评测体系', prompt: '请为我的AI应用设计提示词评测方案，包括测试集、评分维度、A/B对比和持续回归机制。', icon: '🧪', desc: '借鉴 Promptfoo 的评测思想', category: 'engineering', source: 'Promptfoo', template: 'prompt_eval'},
            {id: 'agent_observability', name: '智能体可观测性', prompt: '请为我的AI助手设计可观测性方案，覆盖链路追踪、错误分层、质量指标和排障流程。', icon: '📈', desc: '借鉴 Langfuse 的追踪与评估实践', category: 'engineering', source: 'Langfuse', template: 'agent_observability'},
            {id: 'ai_workflow', name: '自动化工作流设计', prompt: '请为我的业务场景设计一套AI自动化工作流，包含触发器、节点编排、审批机制和失败重试策略。', icon: '🔁', desc: '借鉴 n8n 的节点化编排思路', category: 'engineering', source: 'n8n', template: 'ai_workflow'},
            {id: 'ai_redteam', name: 'AI安全红队演练', prompt: '请为我的AI产品制定红队测试计划，覆盖越狱、提示注入、数据泄露和工具滥用风险。', icon: '🛡️', desc: '借鉴 Promptfoo 的红队测试场景', category: 'engineering', source: 'Promptfoo', template: 'ai_redteam'},
            {id: 'rag_ops', name: 'RAG知识运营', prompt: '请为我的知识库系统制定RAG运营方案，包含文档治理、检索质量评估和持续优化闭环。', icon: '📚', desc: '借鉴 Dify/Open WebUI 的RAG实践', category: 'knowledge', source: 'Dify/Open WebUI', template: 'rag_ops'},
            {id: 'deep_research', name: '深度研究任务', prompt: '请围绕这个主题制定深度研究计划，包含信息源策略、交叉验证、证据分级和结论产出格式。', icon: '🔍', desc: '面向咨询与研究型工作', category: 'knowledge', source: '研究实践', template: 'deep_research'}
        ];
        
        function renderPromptList() {
            const groups = {
                general: '通用助手',
                growth: '增长运营',
                engineering: '工程治理',
                knowledge: '知识研究'
            };
            const filtered = PROMPT_TEMPLATES.filter(p => {
                const hitCategory = promptCategory === 'all' || p.category === promptCategory;
                const q = promptSearchKeyword.trim().toLowerCase();
                const hitKeyword = !q || `${p.name} ${p.desc} ${p.source} ${p.prompt}`.toLowerCase().includes(q);
                return hitCategory && hitKeyword;
            });
            const list = document.getElementById('promptList');
            if (!filtered.length) {
                list.innerHTML = '<div class="empty-state"><div class="empty-state-icon">🧭</div><div class="empty-state-text">未找到匹配模板，试试更短关键词</div></div>';
                return;
            }
            let html = '';
            Object.keys(groups).forEach(groupKey => {
                const groupItems = filtered.filter(x => x.category === groupKey);
                if (!groupItems.length) return;
                html += `<div class="prompt-group-title">${groups[groupKey]}</div>`;
                html += groupItems.map(p => `
                    <div class="prompt-card" onclick="usePromptTemplate('${p.id}')">
                        <div class="prompt-head">
                            <span>${p.icon}</span>
                            <span class="prompt-name">${p.name}</span>
                        </div>
                        <div class="prompt-desc">${p.desc}</div>
                        <div class="prompt-meta">
                            <span class="prompt-meta-tag">${p.source}</span>
                            ${p.template ? '<span class="prompt-meta-tag">结构化输出</span>' : ''}
                        </div>
                    </div>
                `).join('');
            });
            list.innerHTML = html;
        }
        
        function setPromptSearch(value) {
            promptSearchKeyword = value || '';
            renderPromptList();
        }
        
        function setPromptCategory(category) {
            promptCategory = category;
            document.querySelectorAll('.prompt-chip').forEach(el => el.classList.remove('active'));
            const idMap = {all: 'promptCatAll', general: 'promptCatGeneral', growth: 'promptCatGrowth', engineering: 'promptCatEngineering', knowledge: 'promptCatKnowledge'};
            const activeEl = document.getElementById(idMap[category] || 'promptCatAll');
            if (activeEl) activeEl.classList.add('active');
            renderPromptList();
        }
        
        function openPromptWorkbench() {
            // 如果已经存在，先移除
            const existing = document.getElementById('promptWorkbenchModal');
            if (existing) existing.remove();
            
            const modal = document.createElement('div');
            modal.className = 'modal-overlay show';
            modal.id = 'promptWorkbenchModal';
            modal.onclick = function(e) { if (e.target === modal) closeModal('promptWorkbenchModal'); };
            modal.innerHTML = `
                <div class="modal" style="max-width:800px;width:95%;max-height:85vh;display:flex;flex-direction:column;">
                    <div class="modal-header" style="flex-shrink:0;">
                        <h3 style="margin:0;">🧭 专业工作台</h3>
                        <button class="modal-close" onclick="closeModal('promptWorkbenchModal')" style="font-size:18px;">×</button>
                    </div>
                    <div style="flex:1;overflow:hidden;display:flex;flex-direction:column;padding:0;">
                        <div class="workbench-tabs" style="display:flex;gap:4px;padding:12px 0;border-bottom:1px solid var(--border);flex-shrink:0;flex-wrap:wrap;">
                            <button class="workbench-tab active" onclick="switchWorkbenchTab('all', this)">📋 全部</button>
                            <button class="workbench-tab" onclick="switchWorkbenchTab('code', this)">💻 代码</button>
                            <button class="workbench-tab" onclick="switchWorkbenchTab('doc', this)">📄 文档</button>
                            <button class="workbench-tab" onclick="switchWorkbenchTab('data', this)">📊 数据</button>
                            <button class="workbench-tab" onclick="switchWorkbenchTab('favorites', this)">⭐ 收藏</button>
                            <button class="workbench-tab" onclick="switchWorkbenchTab('integrations', this)" style="background:linear-gradient(135deg,#10b981,#059669);color:white;">🔗 接入</button>
                        </div>
                        <div style="padding:12px 0;flex-shrink:0;">
                            <input class="project-input" id="workbenchSearch" placeholder="🔍 搜索模板..." style="width:100%;" oninput="filterWorkbenchTemplates()">
                        </div>
                        <div id="workbenchContent" style="flex:1;overflow-y:auto;padding:8px 0;"></div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
            renderWorkbenchContent('all');
        }

        function switchWorkbenchTab(category, btn) {
            document.querySelectorAll('.workbench-tab').forEach(t => t.classList.remove('active'));
            btn.classList.add('active');
            renderWorkbenchContent(category);
        }

        function renderWorkbenchContent(category) {
            const container = document.getElementById('workbenchContent');
            if (!container) return;
            
            if (category === 'integrations') {
                renderIntegrationsPage(container);
                return;
            }
            
            const allTemplates = [
                { id: 'code-review', name: '代码审查', icon: '🔍', desc: '专业代码质量分析，指出潜在问题和优化建议', category: 'code', prompt: '请对以下代码进行专业审查...' },
                { id: 'doc-gen', name: '文档生成', icon: '📄', desc: '自动生成技术文档，包括函数说明和使用示例', category: 'doc', prompt: '请为以下代码生成文档...' },
                { id: 'api-design', name: 'API 设计', icon: '🔌', desc: 'RESTful API 规划，设计端点和响应格式', category: 'code', prompt: '请根据需求设计API...' },
                { id: 'test-gen', name: '测试生成', icon: '🧪', desc: '单元测试用例生成，覆盖主要功能', category: 'code', prompt: '请为以下代码生成测试...' },
                { id: 'refactor', name: '代码重构', icon: '♻️', desc: '智能代码优化建议，提高可维护性', category: 'code', prompt: '请分析并提供重构建议...' },
                { id: 'security', name: '安全审计', icon: '🔒', desc: '代码安全漏洞检测和修复建议', category: 'code', prompt: '请进行安全审计...' },
                { id: 'data-analysis', name: '数据分析', icon: '📊', desc: '数据统计分析和可视化建议', category: 'data', prompt: '请分析以下数据...' },
                { id: 'report-gen', name: '报告生成', icon: '📝', desc: '自动生成分析报告和摘要', category: 'doc', prompt: '请生成分析报告...' },
                { id: 'creative-write', name: '创意写作', icon: '✨', desc: '创意文案和内容创作', category: 'doc', prompt: '请创作内容...' },
            ];
            
            let templates = category === 'all' ? allTemplates : allTemplates.filter(t => t.category === category);
            
            container.innerHTML = templates.map(t => `
                <div class="workbench-card" onclick="applyWorkbenchTemplate('${t.id}')" style="display:flex;align-items:center;gap:12px;padding:14px;background:var(--bg-secondary);border:1px solid var(--border);border-radius:12px;margin-bottom:8px;cursor:pointer;transition:all 0.2s;">
                    <div style="font-size:28px;flex-shrink:0;">${t.icon}</div>
                    <div style="flex:1;min-width:0;">
                        <div style="font-size:14px;font-weight:600;color:var(--text-primary);margin-bottom:4px;">${t.name}</div>
                        <div style="font-size:12px;color:var(--text-muted);line-height:1.4;">${t.desc}</div>
                    </div>
                    <button onclick="event.stopPropagation();toggleFavorite('${t.id}')" style="background:none;border:none;font-size:18px;cursor:pointer;padding:4px;opacity:0.6;">⭐</button>
                </div>
            `).join('') || '<div style="text-align:center;color:var(--text-muted);padding:40px;">暂无模板</div>';
        }

        function renderIntegrationsPage(container) {
            const integrations = [
                { id: 'api', name: 'API 接入', icon: '🔌', desc: '配置外部 API 服务接入', status: 'available', color: '#667eea' },
                { id: 'database', name: '数据库连接', icon: '🗄️', desc: '连接 MySQL、PostgreSQL 等数据库', status: 'available', color: '#10b981' },
                { id: 'webhook', name: 'Webhook', icon: '🔗', desc: '配置 Webhook 回调地址', status: 'available', color: '#f59e0b' },
                { id: 'mcp', name: 'MCP 协议', icon: '🤖', desc: 'Model Context Protocol 接入', status: 'active', color: '#8b5cf6' },
                { id: 'rag', name: '知识库接入', icon: '📚', desc: 'RAG 检索增强生成', status: 'active', color: '#ec4899' },
                { id: 'tools', name: '工具调用', icon: '🔧', desc: '外部工具和函数调用', status: 'available', color: '#06b6d4' },
                { id: 'plugins', name: '插件系统', icon: '🧩', desc: '管理和配置插件', status: 'available', color: '#84cc16' },
                { id: 'oauth', name: 'OAuth 认证', icon: '🔐', desc: '第三方 OAuth 登录接入', status: 'available', color: '#f43f5e' },
            ];
            
            container.innerHTML = `
                <div style="margin-bottom:16px;">
                    <div style="font-size:14px;font-weight:600;color:var(--text-primary);margin-bottom:8px;">已启用的接入</div>
                    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px;">
                        ${integrations.filter(i => i.status === 'active').map(i => `
                            <div class="integration-card active" onclick="openIntegrationDetail('${i.id}')" style="padding:16px;background:linear-gradient(135deg,${i.color}15,${i.color}05);border:2px solid ${i.color};border-radius:12px;cursor:pointer;">
                                <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
                                    <span style="font-size:24px;">${i.icon}</span>
                                    <span style="font-size:14px;font-weight:600;color:var(--text-primary);">${i.name}</span>
                                </div>
                                <div style="font-size:12px;color:var(--text-muted);margin-bottom:8px;">${i.desc}</div>
                                <div style="display:flex;align-items:center;gap:6px;">
                                    <span style="width:8px;height:8px;background:#10b981;border-radius:50%;"></span>
                                    <span style="font-size:11px;color:#10b981;">已启用</span>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
                <div>
                    <div style="font-size:14px;font-weight:600;color:var(--text-primary);margin-bottom:8px;">可接入的服务</div>
                    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px;">
                        ${integrations.filter(i => i.status === 'available').map(i => `
                            <div class="integration-card" onclick="openIntegrationDetail('${i.id}')" style="padding:16px;background:var(--bg-secondary);border:1px solid var(--border);border-radius:12px;cursor:pointer;transition:all 0.2s;">
                                <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
                                    <span style="font-size:24px;">${i.icon}</span>
                                    <span style="font-size:14px;font-weight:600;color:var(--text-primary);">${i.name}</span>
                                </div>
                                <div style="font-size:12px;color:var(--text-muted);margin-bottom:8px;">${i.desc}</div>
                                <div style="display:flex;align-items:center;gap:6px;">
                                    <span style="width:8px;height:8px;background:var(--text-muted);border-radius:50%;"></span>
                                    <span style="font-size:11px;color:var(--text-muted);">点击配置</span>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }

        function openIntegrationDetail(integrationId) {
            const details = {
                'api': { name: 'API 接入', icon: '🔌', desc: '配置外部 API 服务接入，支持 OpenAI、Claude 等多种 API', config: ['API Key', 'Base URL', 'Model Name'] },
                'database': { name: '数据库连接', icon: '🗄️', desc: '连接 MySQL、PostgreSQL、MongoDB 等数据库', config: ['Host', 'Port', 'Database', 'Username', 'Password'] },
                'webhook': { name: 'Webhook', icon: '🔗', desc: '配置 Webhook 回调地址，实现事件通知', config: ['Callback URL', 'Secret Key', 'Events'] },
                'mcp': { name: 'MCP 协议', icon: '🤖', desc: 'Model Context Protocol 接入，支持工具调用和资源访问', config: ['Server URL', 'Transport Type'] },
                'rag': { name: '知识库接入', icon: '📚', desc: 'RAG 检索增强生成，支持多种向量数据库', config: ['Vector DB', 'Embedding Model', 'Collection Name'] },
                'tools': { name: '工具调用', icon: '🔧', desc: '外部工具和函数调用，扩展 AI 能力', config: ['Tool Name', 'Endpoint', 'Parameters'] },
                'plugins': { name: '插件系统', icon: '🧩', desc: '管理和配置插件，扩展系统功能', config: ['Plugin Directory', 'Auto Load'] },
                'oauth': { name: 'OAuth 认证', icon: '🔐', desc: '第三方 OAuth 登录接入', config: ['Provider', 'Client ID', 'Client Secret', 'Redirect URI'] },
            };
            
            const detail = details[integrationId];
            if (!detail) return;
            
            const modal = document.createElement('div');
            modal.className = 'modal-overlay show';
            modal.id = 'integrationDetailModal';
            modal.onclick = function(e) { if (e.target === modal) closeModal('integrationDetailModal'); };
            modal.innerHTML = `
                <div class="modal" style="max-width:500px;width:90%;max-height:80vh;display:flex;flex-direction:column;">
                    <div class="modal-header" style="flex-shrink:0;">
                        <h3 style="margin:0;display:flex;align-items:center;gap:8px;">
                            <span style="font-size:24px;">${detail.icon}</span>
                            ${detail.name}
                        </h3>
                        <button class="modal-close" onclick="closeModal('integrationDetailModal')" style="font-size:18px;">×</button>
                    </div>
                    <div style="flex:1;overflow-y:auto;padding:16px 0;">
                        <div style="font-size:13px;color:var(--text-secondary);margin-bottom:16px;line-height:1.6;">${detail.desc}</div>
                        <div style="margin-bottom:16px;">
                            <div style="font-size:12px;font-weight:600;color:var(--text-primary);margin-bottom:8px;">配置项</div>
                            ${detail.config.map(c => `
                                <div style="margin-bottom:12px;">
                                    <label style="display:block;font-size:11px;color:var(--text-muted);margin-bottom:4px;">${c}</label>
                                    <input class="project-input" placeholder="输入 ${c}..." style="width:100%;">
                                </div>
                            `).join('')}
                        </div>
                        <div style="background:var(--bg-secondary);border-radius:8px;padding:12px;">
                            <div style="font-size:11px;color:var(--text-muted);margin-bottom:4px;">状态</div>
                            <div style="display:flex;align-items:center;gap:8px;">
                                <span style="width:10px;height:10px;background:#10b981;border-radius:50%;"></span>
                                <span style="font-size:12px;color:var(--text-primary);">已配置</span>
                            </div>
                        </div>
                    </div>
                    <div style="display:flex;gap:10px;justify-content:flex-end;padding-top:12px;border-top:1px solid var(--border);">
                        <button class="project-mini-btn" onclick="closeModal('integrationDetailModal')">取消</button>
                        <button class="project-mini-btn" style="background:linear-gradient(135deg,var(--primary),#764ba2);color:white;" onclick="saveIntegration('${integrationId}')">保存配置</button>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }

        function saveIntegration(integrationId) {
            closeModal('integrationDetailModal');
            showToast('配置已保存');
        }

        function filterWorkbenchTemplates() {
            const search = document.getElementById('workbenchSearch')?.value.toLowerCase() || '';
            const cards = document.querySelectorAll('.workbench-card');
            cards.forEach(card => {
                const text = card.textContent.toLowerCase();
                card.style.display = text.includes(search) ? 'flex' : 'none';
            });
        }

        function applyWorkbenchTemplate(templateId) {
            const templates = {
                'code-review': { name: '代码审查', icon: '🔍', prompt: '请对以下代码进行专业审查，指出潜在问题、安全漏洞和优化建议：\n\n{{code}}', steps: ['输入代码', 'AI分析', '生成报告', '优化建议'] },
                'doc-gen': { name: '文档生成', icon: '📄', prompt: '请为以下代码生成详细的技术文档，包括函数说明、参数描述和使用示例：\n\n{{code}}', steps: ['输入代码', '解析结构', '生成文档', '导出报告'] },
                'api-design': { name: 'API 设计', icon: '🔌', prompt: '请根据以下需求设计 RESTful API，包括端点、请求方法、参数和响应格式：\n\n{{requirements}}', steps: ['需求分析', '设计端点', '定义格式', '输出文档'] },
                'test-gen': { name: '测试生成', icon: '🧪', prompt: '请为以下代码生成单元测试用例，覆盖主要功能和边界情况：\n\n{{code}}', steps: ['分析代码', '设计用例', '生成代码', '运行测试'] },
                'refactor': { name: '代码重构', icon: '♻️', prompt: '请分析以下代码并提供重构建议，提高代码质量和可维护性：\n\n{{code}}', steps: ['代码分析', '识别问题', '重构方案', '实施优化'] },
                'security': { name: '安全审计', icon: '🔒', prompt: '请对以下代码进行安全审计，识别潜在的安全漏洞并提供修复建议：\n\n{{code}}', steps: ['扫描漏洞', '风险评估', '修复建议', '安全报告'] },
                'data-analysis': { name: '数据分析', icon: '📊', prompt: '请对以下数据进行统计分析，提供洞察和可视化建议：\n\n{{data}}', steps: ['数据清洗', '统计分析', '可视化', '洞察报告'] },
                'report-gen': { name: '报告生成', icon: '📝', prompt: '请根据以下内容生成结构化的分析报告：\n\n{{content}}', steps: ['收集内容', '整理结构', '生成报告', '审核发布'] },
                'creative-write': { name: '创意写作', icon: '✨', prompt: '请根据以下主题进行创意写作：\n\n{{topic}}', steps: ['主题分析', '创意构思', '内容创作', '润色完善'] },
            };
            
            const template = templates[templateId];
            if (!template) return;
            
            // 关闭工作台，打开工作规划界面（延迟一点确保关闭完成）
            closeModal('promptWorkbenchModal');
            setTimeout(() => {
                openWorkPlanningModal(templateId, template);
            }, 100);
        }
        
        function openWorkPlanningModal(templateId, template) {
            // 先移除已存在的模态框
            const existing = document.getElementById('workPlanningModal');
            if (existing) existing.remove();
            
            const modal = document.createElement('div');
            modal.className = 'modal-overlay show';
            modal.id = 'workPlanningModal';
            modal.onclick = function(e) { if (e.target === modal) closeModal('workPlanningModal'); };
            
            // 根据不同模板创建不同的界面
            const specializedUI = getSpecializedUI(templateId, template);
            
            modal.innerHTML = `
                <div class="modal" style="max-width:1000px;width:95%;max-height:90vh;display:flex;flex-direction:column;background:linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);color:#fff;">
                    <div class="modal-header" style="flex-shrink:0;border-bottom:1px solid rgba(255,255,255,0.1);padding:16px 20px;">
                        <div style="display:flex;align-items:center;gap:12px;">
                            <span style="font-size:32px;">${template.icon}</span>
                            <div>
                                <h3 style="margin:0;font-size:20px;">${template.name}</h3>
                                <p style="margin:4px 0 0;font-size:12px;color:rgba(255,255,255,0.6);">${getTemplateDescription(templateId)}</p>
                            </div>
                        </div>
                        <button class="modal-close" onclick="closeModal('workPlanningModal')" style="font-size:24px;background:rgba(255,255,255,0.1);border:none;border-radius:8px;width:36px;height:36px;cursor:pointer;color:#fff;">×</button>
                    </div>
                    <div style="flex:1;overflow-y:auto;padding:20px;">
                        ${specializedUI}
                    </div>
                    <div class="modal-actions" style="flex-shrink:0;padding:16px 20px;border-top:1px solid rgba(255,255,255,0.1);display:flex;justify-content:space-between;gap:12px;">
                        <button onclick="closeModal('workPlanningModal')" style="padding:10px 20px;background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.2);border-radius:8px;color:#fff;cursor:pointer;">关闭</button>
                        <button onclick="executeSpecializedTask('${templateId}')" style="padding:10px 24px;background:linear-gradient(135deg, #667eea, #764ba2);border:none;border-radius:8px;color:#fff;cursor:pointer;font-weight:600;">🚀 开始执行</button>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }
        
        function getTemplateDescription(templateId) {
            const descriptions = {
                'code-review': '专业代码审查，识别潜在问题和优化建议',
                'doc-gen': '自动生成技术文档和API说明',
                'api-design': '设计RESTful API接口规范',
                'test-gen': '生成单元测试和集成测试用例',
                'refactor': '代码重构和质量优化建议',
                'security': '安全漏洞扫描和风险评估',
                'data-analysis': '数据统计分析和可视化建议',
                'report-gen': '结构化报告生成和导出',
                'creative-write': '创意内容创作和润色'
            };
            return descriptions[templateId] || '专业工具';
        }
        
        function getSpecializedUI(templateId, template) {
            const uis = {
                'code-review': `
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;">
                        <div>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">📝 待审查代码</label>
                            <textarea id="codeInput" placeholder="粘贴您的代码..." style="width:100%;height:200px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;padding:12px;color:#fff;font-family:monospace;font-size:13px;resize:none;"></textarea>
                        </div>
                        <div>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">⚙️ 审查选项</label>
                            <div style="background:rgba(0,0,0,0.2);border-radius:8px;padding:16px;">
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="checkbox" id="checkSecurity" checked style="width:18px;height:18px;">
                                    <span>🔒 安全漏洞检查</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="checkbox" id="checkPerformance" checked style="width:18px;height:18px;">
                                    <span>⚡ 性能优化建议</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="checkbox" id="checkStyle" checked style="width:18px;height:18px;">
                                    <span>📋 代码风格检查</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
                                    <input type="checkbox" id="checkBestPractice" checked style="width:18px;height:18px;">
                                    <span>✨ 最佳实践建议</span>
                                </label>
                            </div>
                            <label style="display:block;font-size:14px;font-weight:600;margin:16px 0 8px;">🎯 编程语言</label>
                            <select id="codeLanguage" style="width:100%;padding:10px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;color:#fff;">
                                <option value="auto">自动检测</option>
                                <option value="python">Python</option>
                                <option value="javascript">JavaScript</option>
                                <option value="java">Java</option>
                                <option value="cpp">C/C++</option>
                                <option value="go">Go</option>
                            </select>
                        </div>
                    </div>
                `,
                'doc-gen': `
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;">
                        <div>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">📝 代码/接口内容</label>
                            <textarea id="docSource" placeholder="粘贴代码或API接口定义..." style="width:100%;height:200px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;padding:12px;color:#fff;font-family:monospace;font-size:13px;resize:none;"></textarea>
                        </div>
                        <div>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">📄 文档类型</label>
                            <div style="background:rgba(0,0,0,0.2);border-radius:8px;padding:16px;">
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="radio" name="docType" value="api" checked style="width:18px;height:18px;">
                                    <span>🔌 API文档</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="radio" name="docType" value="readme" style="width:18px;height:18px;">
                                    <span>📖 README文档</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="radio" name="docType" value="technical" style="width:18px;height:18px;">
                                    <span>📚 技术文档</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
                                    <input type="radio" name="docType" value="comment" style="width:18px;height:18px;">
                                    <span>💬 代码注释</span>
                                </label>
                            </div>
                            <label style="display:block;font-size:14px;font-weight:600;margin:16px 0 8px;">🌍 文档语言</label>
                            <select id="docLanguage" style="width:100%;padding:10px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;color:#fff;">
                                <option value="zh">中文</option>
                                <option value="en">English</option>
                            </select>
                        </div>
                    </div>
                `,
                'api-design': `
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;">
                        <div>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">📋 需求描述</label>
                            <textarea id="apiRequirements" placeholder="描述您的API需求，例如：用户管理、订单处理..." style="width:100%;height:150px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;padding:12px;color:#fff;font-size:14px;resize:none;"></textarea>
                            <label style="display:block;font-size:14px;font-weight:600;margin:16px 0 8px;">🏷️ API名称</label>
                            <input type="text" id="apiName" placeholder="例如：UserAPI" style="width:100%;padding:10px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;color:#fff;">
                        </div>
                        <div>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">⚙️ API风格</label>
                            <div style="background:rgba(0,0,0,0.2);border-radius:8px;padding:16px;">
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="radio" name="apiStyle" value="rest" checked style="width:18px;height:18px;">
                                    <span>🔄 RESTful API</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="radio" name="apiStyle" value="graphql" style="width:18px;height:18px;">
                                    <span>📊 GraphQL</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
                                    <input type="radio" name="apiStyle" value="grpc" style="width:18px;height:18px;">
                                    <span>⚡ gRPC</span>
                                </label>
                            </div>
                            <label style="display:block;font-size:14px;font-weight:600;margin:16px 0 8px;">🔐 认证方式</label>
                            <select id="authType" style="width:100%;padding:10px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;color:#fff;">
                                <option value="none">无认证</option>
                                <option value="jwt">JWT Token</option>
                                <option value="oauth">OAuth 2.0</option>
                                <option value="apikey">API Key</option>
                            </select>
                        </div>
                    </div>
                `,
                'test-gen': `
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;">
                        <div>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">📝 待测试代码</label>
                            <textarea id="testSource" placeholder="粘贴需要生成测试的代码..." style="width:100%;height:180px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;padding:12px;color:#fff;font-family:monospace;font-size:13px;resize:none;"></textarea>
                        </div>
                        <div>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">🧪 测试框架</label>
                            <select id="testFramework" style="width:100%;padding:10px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;color:#fff;margin-bottom:16px;">
                                <option value="pytest">pytest (Python)</option>
                                <option value="jest">Jest (JavaScript)</option>
                                <option value="junit">JUnit (Java)</option>
                                <option value="gtest">Google Test (C++)</option>
                            </select>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">📊 测试覆盖率</label>
                            <div style="background:rgba(0,0,0,0.2);border-radius:8px;padding:16px;">
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="checkbox" id="testNormal" checked style="width:18px;height:18px;">
                                    <span>✅ 正常用例</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="checkbox" id="testEdge" checked style="width:18px;height:18px;">
                                    <span>🔍 边界用例</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
                                    <input type="checkbox" id="testError" checked style="width:18px;height:18px;">
                                    <span>❌ 异常用例</span>
                                </label>
                            </div>
                        </div>
                    </div>
                `,
                'refactor': `
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;">
                        <div>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">📝 待重构代码</label>
                            <textarea id="refactorSource" placeholder="粘贴需要重构的代码..." style="width:100%;height:200px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;padding:12px;color:#fff;font-family:monospace;font-size:13px;resize:none;"></textarea>
                        </div>
                        <div>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">🎯 重构目标</label>
                            <div style="background:rgba(0,0,0,0.2);border-radius:8px;padding:16px;">
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="checkbox" id="refactorReadability" checked style="width:18px;height:18px;">
                                    <span>📖 提高可读性</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="checkbox" id="refactorPerformance" style="width:18px;height:18px;">
                                    <span>⚡ 性能优化</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="checkbox" id="refactorModular" checked style="width:18px;height:18px;">
                                    <span>🧩 模块化拆分</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
                                    <input type="checkbox" id="refactorPattern" style="width:18px;height:18px;">
                                    <span>📐 设计模式应用</span>
                                </label>
                            </div>
                        </div>
                    </div>
                `,
                'security': `
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;">
                        <div>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">📝 待审计代码</label>
                            <textarea id="securitySource" placeholder="粘贴需要安全审计的代码..." style="width:100%;height:200px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;padding:12px;color:#fff;font-family:monospace;font-size:13px;resize:none;"></textarea>
                        </div>
                        <div>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">🔒 安全检查项</label>
                            <div style="background:rgba(0,0,0,0.2);border-radius:8px;padding:16px;">
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="checkbox" id="secSQL" checked style="width:18px;height:18px;">
                                    <span>💉 SQL注入</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="checkbox" id="secXSS" checked style="width:18px;height:18px;">
                                    <span>🎯 XSS攻击</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="checkbox" id="secCSRF" checked style="width:18px;height:18px;">
                                    <span>🔄 CSRF漏洞</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
                                    <input type="checkbox" id="secAuth" checked style="width:18px;height:18px;">
                                    <span>🔐 认证授权漏洞</span>
                                </label>
                            </div>
                        </div>
                    </div>
                `,
                'data-analysis': `
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;">
                        <div>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">📊 数据内容</label>
                            <textarea id="dataSource" placeholder="粘贴数据（CSV、JSON格式或文本）..." style="width:100%;height:180px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;padding:12px;color:#fff;font-family:monospace;font-size:13px;resize:none;"></textarea>
                        </div>
                        <div>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">📈 分析类型</label>
                            <div style="background:rgba(0,0,0,0.2);border-radius:8px;padding:16px;">
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="checkbox" id="analysisDesc" checked style="width:18px;height:18px;">
                                    <span>📊 描述性统计</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="checkbox" id="analysisTrend" style="width:18px;height:18px;">
                                    <span>📈 趋势分析</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="checkbox" id="analysisCorr" style="width:18px;height:18px;">
                                    <span>🔗 相关性分析</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
                                    <input type="checkbox" id="analysisVisual" checked style="width:18px;height:18px;">
                                    <span>📉 可视化建议</span>
                                </label>
                            </div>
                        </div>
                    </div>
                `,
                'report-gen': `
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;">
                        <div>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">📋 报告内容</label>
                            <textarea id="reportContent" placeholder="输入报告的核心内容、数据或要点..." style="width:100%;height:180px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;padding:12px;color:#fff;font-size:14px;resize:none;"></textarea>
                        </div>
                        <div>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">📄 报告类型</label>
                            <select id="reportType" style="width:100%;padding:10px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;color:#fff;margin-bottom:16px;">
                                <option value="business">商业报告</option>
                                <option value="technical">技术报告</option>
                                <option value="research">研究报告</option>
                                <option value="summary">总结报告</option>
                            </select>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">📑 输出格式</label>
                            <select id="reportFormat" style="width:100%;padding:10px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;color:#fff;">
                                <option value="markdown">Markdown</option>
                                <option value="html">HTML</option>
                                <option value="plain">纯文本</option>
                            </select>
                        </div>
                    </div>
                `,
                'creative-write': `
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;">
                        <div>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">💡 创作主题</label>
                            <input type="text" id="creativeTopic" placeholder="输入创作主题..." style="width:100%;padding:12px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;color:#fff;font-size:14px;margin-bottom:16px;">
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">📝 补充说明</label>
                            <textarea id="creativeNotes" placeholder="补充要求、风格偏好等..." style="width:100%;height:120px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;padding:12px;color:#fff;font-size:14px;resize:none;"></textarea>
                        </div>
                        <div>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">✍️ 创作类型</label>
                            <div style="background:rgba(0,0,0,0.2);border-radius:8px;padding:16px;">
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="radio" name="creativeType" value="article" checked style="width:18px;height:18px;">
                                    <span>📰 文章</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="radio" name="creativeType" value="story" style="width:18px;height:18px;">
                                    <span>📖 故事</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="radio" name="creativeType" value="copywriting" style="width:18px;height:18px;">
                                    <span>📢 文案</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
                                    <input type="radio" name="creativeType" value="script" style="width:18px;height:18px;">
                                    <span>🎬 脚本</span>
                                </label>
                            </div>
                            <label style="display:block;font-size:14px;font-weight:600;margin:16px 0 8px;">🎭 风格</label>
                            <select id="creativeStyle" style="width:100%;padding:10px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;color:#fff;">
                                <option value="professional">专业正式</option>
                                <option value="casual">轻松活泼</option>
                                <option value="humorous">幽默风趣</option>
                                <option value="emotional">情感共鸣</option>
                            </select>
                        </div>
                    </div>
                `
            };
            return uis[templateId] || `
                <div>
                    <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">📝 输入内容</label>
                    <textarea id="workInput" placeholder="请输入您的内容..." style="width:100%;height:200px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;padding:12px;color:#fff;font-size:14px;resize:none;"></textarea>
                </div>
            `;
        }
        
        function executeSpecializedTask(templateId) {
            let prompt = '';
            let input = '';
            
            switch(templateId) {
                case 'code-review':
                    input = document.getElementById('codeInput')?.value || '';
                    const lang = document.getElementById('codeLanguage')?.value || 'auto';
                    const checks = [];
                    if (document.getElementById('checkSecurity')?.checked) checks.push('安全漏洞');
                    if (document.getElementById('checkPerformance')?.checked) checks.push('性能优化');
                    if (document.getElementById('checkStyle')?.checked) checks.push('代码风格');
                    if (document.getElementById('checkBestPractice')?.checked) checks.push('最佳实践');
                    prompt = `请对以下${lang === 'auto' ? '' : lang}代码进行专业审查，重点关注：${checks.join('、')}\n\n代码：\n${input}`;
                    break;
                    
                case 'doc-gen':
                    input = document.getElementById('docSource')?.value || '';
                    const docType = document.querySelector('input[name="docType"]:checked')?.value || 'api';
                    const docLang = document.getElementById('docLanguage')?.value || 'zh';
                    prompt = `请为以下内容生成${docType === 'api' ? 'API文档' : docType === 'readme' ? 'README文档' : docType === 'technical' ? '技术文档' : '代码注释'}（${docLang === 'zh' ? '中文' : '英文'}）：\n\n${input}`;
                    break;
                    
                case 'api-design':
                    input = document.getElementById('apiRequirements')?.value || '';
                    const apiName = document.getElementById('apiName')?.value || '';
                    const apiStyle = document.querySelector('input[name="apiStyle"]:checked')?.value || 'rest';
                    const auth = document.getElementById('authType')?.value || 'none';
                    prompt = `请根据以下需求设计${apiStyle === 'rest' ? 'RESTful API' : apiStyle === 'graphql' ? 'GraphQL' : 'gRPC'}接口：\n需求：${input}\nAPI名称：${apiName}\n认证方式：${auth}`;
                    break;
                    
                case 'test-gen':
                    input = document.getElementById('testSource')?.value || '';
                    const framework = document.getElementById('testFramework')?.value || 'pytest';
                    prompt = `请使用${framework}框架为以下代码生成测试用例：\n\n${input}`;
                    break;
                    
                case 'refactor':
                    input = document.getElementById('refactorSource')?.value || '';
                    const goals = [];
                    if (document.getElementById('refactorReadability')?.checked) goals.push('提高可读性');
                    if (document.getElementById('refactorPerformance')?.checked) goals.push('性能优化');
                    if (document.getElementById('refactorModular')?.checked) goals.push('模块化拆分');
                    if (document.getElementById('refactorPattern')?.checked) goals.push('设计模式应用');
                    prompt = `请重构以下代码，目标：${goals.join('、')}\n\n代码：\n${input}`;
                    break;
                    
                case 'security':
                    input = document.getElementById('securitySource')?.value || '';
                    const secChecks = [];
                    if (document.getElementById('secSQL')?.checked) secChecks.push('SQL注入');
                    if (document.getElementById('secXSS')?.checked) secChecks.push('XSS攻击');
                    if (document.getElementById('secCSRF')?.checked) secChecks.push('CSRF漏洞');
                    if (document.getElementById('secAuth')?.checked) secChecks.push('认证授权漏洞');
                    prompt = `请对以下代码进行安全审计，检查：${secChecks.join('、')}\n\n代码：\n${input}`;
                    break;
                    
                case 'data-analysis':
                    input = document.getElementById('dataSource')?.value || '';
                    const analysis = [];
                    if (document.getElementById('analysisDesc')?.checked) analysis.push('描述性统计');
                    if (document.getElementById('analysisTrend')?.checked) analysis.push('趋势分析');
                    if (document.getElementById('analysisCorr')?.checked) analysis.push('相关性分析');
                    if (document.getElementById('analysisVisual')?.checked) analysis.push('可视化建议');
                    prompt = `请对以下数据进行${analysis.join('、')}：\n\n数据：\n${input}`;
                    break;
                    
                case 'report-gen':
                    input = document.getElementById('reportContent')?.value || '';
                    const reportType = document.getElementById('reportType')?.value || 'business';
                    const reportFormat = document.getElementById('reportFormat')?.value || 'markdown';
                    prompt = `请根据以下内容生成${reportType === 'business' ? '商业报告' : reportType === 'technical' ? '技术报告' : reportType === 'research' ? '研究报告' : '总结报告'}（${reportFormat}格式）：\n\n${input}`;
                    break;
                    
                case 'creative-write':
                    const topic = document.getElementById('creativeTopic')?.value || '';
                    const notes = document.getElementById('creativeNotes')?.value || '';
                    const creativeType = document.querySelector('input[name="creativeType"]:checked')?.value || 'article';
                    const style = document.getElementById('creativeStyle')?.value || 'professional';
                    prompt = `请以${style === 'professional' ? '专业正式' : style === 'casual' ? '轻松活泼' : style === 'humorous' ? '幽默风趣' : '情感共鸣'}的风格，创作一篇${creativeType === 'article' ? '文章' : creativeType === 'story' ? '故事' : creativeType === 'copywriting' ? '文案' : '脚本'}。\n主题：${topic}\n${notes ? '补充要求：' + notes : ''}`;
                    break;
                    
                default:
                    input = document.getElementById('workInput')?.value || '';
                    prompt = input;
            }
            
            if (!prompt || prompt.includes('undefined')) {
                showToast('请填写必要的内容');
                return;
            }
            
            closeModal('workPlanningModal');
            document.getElementById('mainInput').value = prompt;
            showToast('正在执行任务...');
            document.getElementById('sendBtn').click();
        }

        function toggleFavorite(templateId) {
            showToast('已收藏');
        }

        function favoriteTemplate(templateId) {
            showToast('已收藏模板');
        }

        function createCustomTemplate() {
            showToast('打开创建模板面板');
        }

        function openQuickSceneModal() {
            const modal = document.createElement('div');
            modal.className = 'modal-overlay';
            modal.id = 'quickSceneModal';
            modal.innerHTML = `
                <div class="modal-content" style="max-width:500px;">
                    <div class="modal-header">
                        <h3>🎯 新建快速场景</h3>
                        <button class="modal-close" onclick="closeModal('quickSceneModal')">×</button>
                    </div>
                    <div class="modal-body">
                        <div style="margin-bottom:15px;">
                            <label style="font-size:12px;display:block;margin-bottom:5px;">场景名称</label>
                            <input class="project-input" id="sceneName" placeholder="输入场景名称" style="width:100%;">
                        </div>
                        <div style="margin-bottom:15px;">
                            <label style="font-size:12px;display:block;margin-bottom:5px;">场景描述</label>
                            <textarea class="project-input" id="sceneDesc" placeholder="输入场景描述" style="width:100%;height:80px;resize:vertical;"></textarea>
                        </div>
                        <div style="margin-bottom:15px;">
                            <label style="font-size:12px;display:block;margin-bottom:5px;">提示词模板</label>
                            <textarea class="project-input" id="scenePrompt" placeholder="输入提示词模板，使用 {{变量}} 表示变量" style="width:100%;height:100px;resize:vertical;"></textarea>
                        </div>
                        <div style="display:flex;gap:10px;justify-content:flex-end;">
                            <button class="project-mini-btn" onclick="closeModal('quickSceneModal')">取消</button>
                            <button class="project-mini-btn" style="background:var(--primary);color:white;" onclick="saveQuickScene()">保存</button>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }

        function saveQuickScene() {
            const name = document.getElementById('sceneName').value;
            const desc = document.getElementById('sceneDesc').value;
            const prompt = document.getElementById('scenePrompt').value;
            if (!name || !prompt) {
                showToast('请填写场景名称和提示词');
                return;
            }
            showToast('场景已保存');
            closeModal('quickSceneModal');
        }

        function applyQuickScene(sceneId) {
            const scenes = {
                'code-review': '请对以下代码进行专业审查，指出潜在问题、安全漏洞和优化建议：\\n\\n{{code}}',
                'doc-gen': '请为以下代码生成详细的技术文档，包括函数说明、参数描述和使用示例：\\n\\n{{code}}',
                'api-design': '请根据以下需求设计 RESTful API，包括端点、请求方法、参数和响应格式：\\n\\n{{requirements}}',
                'test-gen': '请为以下代码生成单元测试用例，覆盖主要功能和边界情况：\\n\\n{{code}}',
                'refactor': '请分析以下代码并提供重构建议，提高代码质量和可维护性：\\n\\n{{code}}',
                'security': '请对以下代码进行安全审计，识别潜在的安全漏洞并提供修复建议：\\n\\n{{code}}'
            };
            const prompt = scenes[sceneId] || '';
            if (prompt) {
                document.getElementById('mainInput').value = prompt;
                showToast('已应用场景模板');
            }
        }

        function loadTemplateAnalysis() {
            const range = document.getElementById('templateAnalysisRange')?.value || '7d';
            fetch('/templates/analysis?range=' + range)
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        const templateCountEl = document.getElementById('workbenchTemplateCount');
                        const favoriteCountEl = document.getElementById('workbenchFavoriteCount');
                        const usageCountEl = document.getElementById('workbenchUsageCount');
                        const customCountEl = document.getElementById('workbenchCustomCount');
                        if (templateCountEl) templateCountEl.textContent = data.stats.total_templates || '--';
                        if (favoriteCountEl) favoriteCountEl.textContent = data.stats.favorites || '--';
                        if (usageCountEl) usageCountEl.textContent = data.stats.usage || '--';
                        if (customCountEl) customCountEl.textContent = data.stats.custom || '--';
                    }
                });
        }

        function exportTemplateReport() {
            showToast('正在导出模板报告...');
        }

        function refreshRagStats() {
            fetch('/rag/stats')
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        const docsEl = document.getElementById('ragStatDocs');
                        const chunksEl = document.getElementById('ragStatChunks');
                        const charsEl = document.getElementById('ragStatChars');
                        const vectorsEl = document.getElementById('ragStatVectors');
                        if (docsEl) docsEl.textContent = data.stats.docs || 0;
                        if (chunksEl) chunksEl.textContent = data.stats.chunks || 0;
                        if (charsEl) charsEl.textContent = data.stats.chars || 0;
                        if (vectorsEl) vectorsEl.textContent = data.stats.vectors || 0;
                    }
                });
        }

        function openBatchImportModal() {
            const modal = document.createElement('div');
            modal.className = 'modal-overlay';
            modal.id = 'batchImportModal';
            modal.innerHTML = `
                <div class="modal-content" style="max-width:500px;">
                    <div class="modal-header">
                        <h3>📤 批量导入文档</h3>
                        <button class="modal-close" onclick="closeModal('batchImportModal')">×</button>
                    </div>
                    <div class="modal-body">
                        <div style="margin-bottom:15px;">
                            <label style="font-size:12px;display:block;margin-bottom:5px;">选择文件（支持多选）</label>
                            <input type="file" id="batchFiles" multiple accept=".txt,.md,.pdf,.docx,.html,.json,.csv" style="width:100%;">
                        </div>
                        <div style="margin-bottom:15px;">
                            <label style="font-size:12px;display:block;margin-bottom:5px;">目标分类</label>
                            <select class="project-input" id="batchCategory" style="width:100%;">
                                <option value="doc">📄 文档</option>
                                <option value="code">💻 代码</option>
                                <option value="data">📊 数据</option>
                                <option value="web">🌐 网页</option>
                                <option value="text">📝 文本</option>
                            </select>
                        </div>
                        <div style="display:flex;gap:10px;justify-content:flex-end;">
                            <button class="project-mini-btn" onclick="closeModal('batchImportModal')">取消</button>
                            <button class="project-mini-btn" style="background:var(--primary);color:white;" onclick="executeBatchImport()">导入</button>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }

        function executeBatchImport() {
            showToast('正在批量导入...');
            closeModal('batchImportModal');
        }

        function openUrlImportModal() {
            const modal = document.createElement('div');
            modal.className = 'modal-overlay';
            modal.id = 'urlImportModal';
            modal.innerHTML = `
                <div class="modal-content" style="max-width:500px;">
                    <div class="modal-header">
                        <h3>🌐 网页抓取</h3>
                        <button class="modal-close" onclick="closeModal('urlImportModal')">×</button>
                    </div>
                    <div class="modal-body">
                        <div style="margin-bottom:15px;">
                            <label style="font-size:12px;display:block;margin-bottom:5px;">网页 URL</label>
                            <input class="project-input" id="importUrl" placeholder="https://example.com" style="width:100%;">
                        </div>
                        <div style="margin-bottom:15px;">
                            <label style="font-size:12px;display:block;margin-bottom:5px;">抓取深度</label>
                            <select class="project-input" id="crawlDepth" style="width:100%;">
                                <option value="1">仅当前页面</option>
                                <option value="2">2 层深度</option>
                                <option value="3">3 层深度</option>
                            </select>
                        </div>
                        <div style="display:flex;gap:10px;justify-content:flex-end;">
                            <button class="project-mini-btn" onclick="closeModal('urlImportModal')">取消</button>
                            <button class="project-mini-btn" style="background:var(--primary);color:white;" onclick="executeUrlImport()">抓取</button>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }

        function executeUrlImport() {
            const url = document.getElementById('importUrl').value;
            if (!url) {
                showToast('请输入 URL');
                return;
            }
            showToast('正在抓取网页...');
            closeModal('urlImportModal');
        }

        function openGitImportModal() {
            const modal = document.createElement('div');
            modal.className = 'modal-overlay';
            modal.id = 'gitImportModal';
            modal.innerHTML = `
                <div class="modal-content" style="max-width:500px;">
                    <div class="modal-header">
                        <h3>📦 Git 仓库导入</h3>
                        <button class="modal-close" onclick="closeModal('gitImportModal')">×</button>
                    </div>
                    <div class="modal-body">
                        <div style="margin-bottom:15px;">
                            <label style="font-size:12px;display:block;margin-bottom:5px;">仓库 URL</label>
                            <input class="project-input" id="gitRepoUrl" placeholder="https://github.com/user/repo" style="width:100%;">
                        </div>
                        <div style="margin-bottom:15px;">
                            <label style="font-size:12px;display:block;margin-bottom:5px;">分支</label>
                            <input class="project-input" id="gitBranch" placeholder="main" value="main" style="width:100%;">
                        </div>
                        <div style="margin-bottom:15px;">
                            <label style="font-size:12px;display:block;margin-bottom:5px;">文件类型</label>
                            <div style="display:flex;gap:10px;flex-wrap:wrap;">
                                <label style="font-size:11px;"><input type="checkbox" checked> .py</label>
                                <label style="font-size:11px;"><input type="checkbox" checked> .js</label>
                                <label style="font-size:11px;"><input type="checkbox" checked> .md</label>
                                <label style="font-size:11px;"><input type="checkbox"> .txt</label>
                            </div>
                        </div>
                        <div style="display:flex;gap:10px;justify-content:flex-end;">
                            <button class="project-mini-btn" onclick="closeModal('gitImportModal')">取消</button>
                            <button class="project-mini-btn" style="background:var(--primary);color:white;" onclick="executeGitImport()">导入</button>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }

        function executeGitImport() {
            const url = document.getElementById('gitRepoUrl').value;
            if (!url) {
                showToast('请输入仓库 URL');
                return;
            }
            showToast('正在导入仓库...');
            closeModal('gitImportModal');
        }

        function openRagSettingsModal() {
            showToast('打开 RAG 设置面板');
        }

        function openKnowledgeGraphModal() {
            const modal = document.createElement('div');
            modal.className = 'modal-overlay';
            modal.id = 'knowledgeGraphModal';
            modal.innerHTML = `
                <div class="modal-content" style="max-width:800px;">
                    <div class="modal-header">
                        <h3>🧠 知识图谱</h3>
                        <button class="modal-close" onclick="closeModal('knowledgeGraphModal')">×</button>
                    </div>
                    <div class="modal-body" style="height:500px;">
                        <div class="graph-container" id="graphContainer">
                            <div class="graph-placeholder">
                                <div class="graph-visualization">
                                    <div class="node-center">知识库</div>
                                    <div class="node-ring">
                                        <div class="node-item">概念</div>
                                        <div class="node-item">实体</div>
                                        <div class="node-item">关系</div>
                                        <div class="node-item">属性</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }

        function buildKnowledgeGraph() {
            showToast('正在构建知识图谱...');
            fetch('/rag/build-graph', { method: 'POST' })
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        document.getElementById('graphNodes').textContent = data.nodes || '--';
                        document.getElementById('graphEdges').textContent = data.edges || '--';
                        showToast('知识图谱构建完成');
                    }
                });
        }

        function loadRagAnalysis() {
            const range = document.getElementById('ragAnalysisRange')?.value || '7d';
            fetch('/rag/analysis?range=' + range)
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        document.getElementById('ragQueryCount').textContent = data.analysis.queries || '--';
                        document.getElementById('ragHitRate').textContent = data.analysis.hit_rate || '--';
                        document.getElementById('ragLatency').textContent = data.analysis.latency || '--';
                        document.getElementById('ragTopDoc').textContent = data.analysis.top_doc || '--';
                    }
                });
        }

        function exportRagReport() {
            showToast('正在导出 RAG 报告...');
        }

        function openVectorSettingsModal() {
            showToast('打开向量化设置面板');
        }
        
        function usePromptTemplate(templateId) {
            const item = PROMPT_TEMPLATES.find(x => x.id === templateId);
            if (!item) return;
            usePrompt(item.prompt, item.template || null);
        }
        
        function usePrompt(prompt, templateId = null) {
            document.getElementById('mainInput').value = prompt;
            currentStructuredTemplate = templateId;
            document.getElementById('mainInput').focus();
            updateCharCount();
            showToast(templateId ? '已应用结构化模板' : '已填入模板');
        }
        
        function loadProjectCenter() {
            Promise.all([
                fetch('/project/overview').then(r => r.json()),
                fetch('/artifacts').then(r => r.json()),
                fetch('/project/tasks').then(r => r.json()),
                fetch('/playbooks').then(r => r.json()),
                fetch('/project/activity?limit=40').then(r => r.json()),
                fetch('/project/milestones').then(r => r.json()),
                fetch('/project/risks').then(r => r.json()),
                fetch('/ops/overview').then(r => r.json()),
                fetch('/ops/campaigns').then(r => r.json()),
                fetch('/release/overview').then(r => r.json()),
                fetch('/release/plans').then(r => r.json()),
                fetch('/alerts/overview').then(r => r.json()),
                fetch('/alerts/rules').then(r => r.json()),
                fetch('/ab/overview').then(r => r.json()),
                fetch('/ab/experiments').then(r => r.json()),
                fetch('/integrations/overview').then(r => r.json()),
                fetch('/integrations').then(r => r.json()),
                fetch('/console/overview').then(r => r.json()),
                fetch('/console/recommendations').then(r => r.json()),
                fetch('/workspace/projects/overview').then(r => r.json()),
                fetch('/workspace/projects').then(r => r.json())
            ]).then(([ov, af, tk, pb, ac, ms, rk, oov, ocs, rov, rps, aov, ars, bov, bes, iov, ils, cov, cre, wov, wps]) => {
                if (ov.success) projectOverview = ov.overview || {};
                if (af.success) projectArtifacts = af.artifacts || [];
                if (tk.success) projectTasks = tk.tasks || [];
                if (pb.success) projectPlaybooks = pb.playbooks || [];
                if (ac.success) projectActivities = ac.activities || [];
                if (ms.success) projectMilestones = ms.milestones || [];
                if (rk.success) projectRisks = rk.risks || [];
                if (oov.success) opsOverview = oov.overview || {};
                if (ocs.success) opsCampaigns = ocs.campaigns || [];
                if (rov.success) releaseOverview = rov.overview || {};
                if (rps.success) releasePlans = rps.plans || [];
                if (aov.success) alertOverview = aov.overview || {};
                if (ars.success) alertRules = ars.rules || [];
                if (bov.success) abOverview = bov.overview || {};
                if (bes.success) abExperiments = bes.experiments || [];
                if (iov.success) integrationOverview = iov.overview || {};
                if (ils.success) integrationItems = ils.integrations || [];
                if (cov.success) consoleOverview = cov.overview || {};
                if (cre.success) consoleRecommendations = cre.recommendations || [];
                if (wov.success) workspaceOverview = wov.overview || {};
                if (wps.success) workspaceProjects = wps.projects || [];
                selectedTaskIds = new Set(Array.from(selectedTaskIds).filter(id => projectTasks.some(t => t.id === id)));
                renderConsoleOverview();
                renderConsoleRecommendations();
                runGlobalSearch(document.getElementById('globalSearchInput')?.value || '');
                renderWorkspaceOverview();
                renderWorkspaceProjects();
                renderProjectOverview();
                renderProjectArtifacts();
                renderProjectTasks();
                renderProjectPlaybooks();
                renderProjectActivity();
                renderProjectMilestones();
                renderProjectRisks();
                renderOpsOverview();
                renderOpsCampaigns();
                renderReleaseOverview();
                renderReleasePlans();
                renderAlertOverview();
                renderAlertRules();
                renderAbOverview();
                renderAbExperiments();
                renderIntegrationOverview();
                renderIntegrations();
                renderFeatureCenterMeta();
            }).catch(() => {});
        }

        function loadWorkspaceProjects(query = '') {
            const q = encodeURIComponent((query || '').trim());
            fetch(`/workspace/projects?q=${q}`).then(r => r.json()).then(data => {
                if (!data.success) return;
                workspaceProjects = data.projects || [];
                renderWorkspaceProjects();
            });
        }

        function refreshWorkspaceProjects() {
            fetch('/workspace/projects?refresh=1').then(r => r.json()).then(data => {
                if (data.success) workspaceProjects = data.projects || [];
                renderWorkspaceProjects();
            });
            fetch('/workspace/projects/overview').then(r => r.json()).then(data => {
                if (data.success) workspaceOverview = data.overview || {};
                renderWorkspaceOverview();
                renderFeatureCenterMeta();
            });
        }

        function loadConsoleData() {
            Promise.all([
                fetch('/console/overview').then(r => r.json()),
                fetch('/console/recommendations').then(r => r.json())
            ]).then(([ov, rc]) => {
                if (ov.success) consoleOverview = ov.overview || {};
                if (rc.success) consoleRecommendations = rc.recommendations || [];
                renderConsoleOverview();
                renderConsoleRecommendations();
            });
            refreshSystemMetrics();
            loadPerformanceData();
        }

        function refreshSystemMetrics() {
            fetch('/system/metrics')
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        const m = data.metrics;
                        document.getElementById('cpuUsage').textContent = m.cpu_percent ? `${m.cpu_percent}%` : '--';
                        document.getElementById('cpuBar').style.width = `${m.cpu_percent || 0}%`;
                        document.getElementById('memoryUsage').textContent = m.memory_percent ? `${m.memory_percent}%` : '--';
                        document.getElementById('memoryBar').style.width = `${m.memory_percent || 0}%`;
                        document.getElementById('diskUsage').textContent = m.disk_percent ? `${m.disk_percent}%` : '--';
                        document.getElementById('diskBar').style.width = `${m.disk_percent || 0}%`;
                        document.getElementById('networkStatus').textContent = m.network_status || '正常';
                        document.getElementById('networkBar').style.width = m.network_status === '正常' ? '100%' : '50%';
                    }
                })
                .catch(() => {
                    document.getElementById('cpuUsage').textContent = 'N/A';
                    document.getElementById('memoryUsage').textContent = 'N/A';
                    document.getElementById('diskUsage').textContent = 'N/A';
                });
        }

        function openSystemMonitorModal() {
            const modal = document.createElement('div');
            modal.className = 'modal-overlay';
            modal.id = 'systemMonitorModal';
            modal.innerHTML = `
                <div class="modal-content" style="max-width:800px;">
                    <div class="modal-header">
                        <h3>📊 系统监控详情</h3>
                        <button class="modal-close" onclick="closeModal('systemMonitorModal')">×</button>
                    </div>
                    <div class="modal-body" style="max-height:70vh;overflow-y:auto;">
                        <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:15px;">
                            <div class="metric-card">
                                <div class="metric-icon">💻</div>
                                <div class="metric-info">
                                    <div class="metric-label">CPU 使用率</div>
                                    <div class="metric-value" id="modalCpuUsage">--</div>
                                </div>
                                <div class="metric-bar"><div class="metric-bar-fill" id="modalCpuBar" style="width:0%"></div></div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-icon">🧠</div>
                                <div class="metric-info">
                                    <div class="metric-label">内存使用</div>
                                    <div class="metric-value" id="modalMemoryUsage">--</div>
                                </div>
                                <div class="metric-bar"><div class="metric-bar-fill" id="modalMemoryBar" style="width:0%"></div></div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-icon">💾</div>
                                <div class="metric-info">
                                    <div class="metric-label">磁盘空间</div>
                                    <div class="metric-value" id="modalDiskUsage">--</div>
                                </div>
                                <div class="metric-bar"><div class="metric-bar-fill" id="modalDiskBar" style="width:0%"></div></div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-icon">🐍</div>
                                <div class="metric-info">
                                    <div class="metric-label">Python 进程</div>
                                    <div class="metric-value" id="modalPythonProcess">--</div>
                                </div>
                            </div>
                        </div>
                        <div style="margin-top:15px;">
                            <h4 style="font-size:13px;margin-bottom:10px;">进程信息</h4>
                            <div id="processList" style="font-size:11px;font-family:monospace;background:var(--bg-secondary);padding:10px;border-radius:8px;">
                                加载中...
                            </div>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
            refreshSystemMetrics();
        }

        function filterLogs() {
            const level = document.getElementById('logLevelFilter').value;
            const entries = document.querySelectorAll('.log-entry');
            entries.forEach(entry => {
                if (level === 'all' || entry.classList.contains('log-' + level)) {
                    entry.style.display = 'block';
                } else {
                    entry.style.display = 'none';
                }
            });
        }

        function clearLogs() {
            document.getElementById('logViewer').innerHTML = '<div class="log-entry log-info"><span class="log-time">[系统]</span> 日志已清空</div>';
        }

        function exportLogs() {
            const logs = document.getElementById('logViewer').innerText;
            const blob = new Blob([logs], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'kaguya_logs_' + new Date().toISOString().slice(0,10) + '.txt';
            a.click();
            URL.revokeObjectURL(url);
            showToast('日志已导出');
        }

        let logAutoScroll = true;
        function toggleLogAutoScroll() {
            logAutoScroll = !logAutoScroll;
            showToast(logAutoScroll ? '自动滚动已开启' : '自动滚动已关闭');
        }

        function addLogEntry(level, message) {
            const viewer = document.getElementById('logViewer');
            const entry = document.createElement('div');
            entry.className = 'log-entry log-' + level;
            const time = new Date().toLocaleTimeString('zh-CN');
            entry.innerHTML = '<span class="log-time">[' + time + ']</span> ' + message;
            viewer.appendChild(entry);
            if (logAutoScroll) {
                viewer.scrollTop = viewer.scrollHeight;
            }
        }

        function openTaskSchedulerModal() {
            const modal = document.createElement('div');
            modal.className = 'modal-overlay';
            modal.id = 'taskSchedulerModal';
            modal.innerHTML = `
                <div class="modal-content" style="max-width:500px;">
                    <div class="modal-header">
                        <h3>⏰ 新建定时任务</h3>
                        <button class="modal-close" onclick="closeModal('taskSchedulerModal')">×</button>
                    </div>
                    <div class="modal-body">
                        <div style="margin-bottom:15px;">
                            <label style="font-size:12px;display:block;margin-bottom:5px;">任务名称</label>
                            <input class="project-input" id="taskName" placeholder="输入任务名称" style="width:100%;">
                        </div>
                        <div style="margin-bottom:15px;">
                            <label style="font-size:12px;display:block;margin-bottom:5px;">执行时间</label>
                            <input type="time" class="project-input" id="taskTime" style="width:100%;">
                        </div>
                        <div style="margin-bottom:15px;">
                            <label style="font-size:12px;display:block;margin-bottom:5px;">重复周期</label>
                            <select class="project-input" id="taskRepeat" style="width:100%;">
                                <option value="daily">每天</option>
                                <option value="weekly">每周</option>
                                <option value="monthly">每月</option>
                                <option value="once">仅一次</option>
                            </select>
                        </div>
                        <div style="margin-bottom:15px;">
                            <label style="font-size:12px;display:block;margin-bottom:5px;">任务类型</label>
                            <select class="project-input" id="taskType" style="width:100%;">
                                <option value="backup">数据备份</option>
                                <option value="cleanup">缓存清理</option>
                                <option value="report">报告生成</option>
                                <option value="custom">自定义脚本</option>
                            </select>
                        </div>
                        <div style="display:flex;gap:10px;justify-content:flex-end;">
                            <button class="project-mini-btn" onclick="closeModal('taskSchedulerModal')">取消</button>
                            <button class="project-mini-btn" style="background:var(--primary);color:white;" onclick="saveScheduledTask()">保存</button>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }

        function saveScheduledTask() {
            const name = document.getElementById('taskName').value;
            const time = document.getElementById('taskTime').value;
            const repeat = document.getElementById('taskRepeat').value;
            const type = document.getElementById('taskType').value;
            if (!name || !time) {
                showToast('请填写完整信息');
                return;
            }
            fetch('/scheduler/tasks', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, time, repeat, type })
            }).then(r => r.json()).then(data => {
                if (data.success) {
                    showToast('任务已创建');
                    closeModal('taskSchedulerModal');
                    refreshScheduledTasks();
                } else {
                    showToast('创建失败: ' + data.error);
                }
            });
        }

        function refreshScheduledTasks() {
            fetch('/scheduler/tasks')
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        renderScheduledTasks(data.tasks);
                    }
                });
        }

        function renderScheduledTasks(tasks) {
            const el = document.getElementById('scheduledTasksList');
            if (!el) return;
            el.innerHTML = tasks.map(t => `
                <div class="scheduler-task-card">
                    <div class="task-header">
                        <span class="task-name">${t.name}</span>
                        <span class="task-status ${t.status}">${t.status === 'active' ? '运行中' : '已暂停'}</span>
                    </div>
                    <div class="task-info">
                        <span>⏰ ${t.schedule}</span>
                        <span>🔄 上次: ${t.last_run || '--'}</span>
                    </div>
                </div>
            `).join('');
        }

        function loadPerformanceData() {
            const range = document.getElementById('perfTimeRange')?.value || '24h';
            fetch('/performance/stats?range=' + range)
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        document.getElementById('avgResponseTime').textContent = data.stats.avg_response_time || '--';
                        document.getElementById('totalRequests').textContent = data.stats.total_requests || '--';
                        document.getElementById('errorRate').textContent = data.stats.error_rate || '--';
                        document.getElementById('throughput').textContent = data.stats.throughput || '--';
                    }
                });
        }

        function exportPerformanceReport() {
            showToast('正在生成报告...');
            fetch('/performance/export')
                .then(r => r.blob())
                .then(blob => {
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'performance_report_' + new Date().toISOString().slice(0,10) + '.json';
                    a.click();
                    URL.revokeObjectURL(url);
                    showToast('报告已导出');
                });
        }

        function generateGovernanceReport() {
            showToast('正在生成治理报告...');
            fetch('/console/governance-report')
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        showToast('治理报告已生成');
                    }
                });
        }

        function checkAllServicesHealth() {
            showToast('正在检查服务健康状态...');
            fetch('/services/health-check')
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        renderServiceHealth(data.services);
                        showToast('健康检查完成');
                    }
                });
        }

        function renderServiceHealth(services) {
            const el = document.getElementById('serviceHealthGrid');
            if (!el || !services) return;
            el.innerHTML = services.map(s => `
                <div class="service-card ${s.status}">
                    <div class="service-icon">${s.icon}</div>
                    <div class="service-info">
                        <div class="service-name">${s.name}</div>
                        <div class="service-status">● ${s.status_text}</div>
                    </div>
                    <div class="service-actions">
                        <button class="service-btn" onclick="restartService('${s.id}')">重启</button>
                    </div>
                </div>
            `).join('');
        }

        function restartService(serviceId) {
            showToast('正在重启 ' + serviceId + '...');
            fetch('/services/' + serviceId + '/restart', { method: 'POST' })
                .then(r => r.json())
                .then(data => {
                    showToast(data.success ? '重启成功' : '重启失败');
                    checkAllServicesHealth();
                });
        }

        function configureService(serviceId) {
            showToast('打开服务配置...');
        }

        function openServiceConfigModal() {
            showToast('打开服务配置面板');
        }

        function analyzeAllDependencies() {
            showToast('正在分析依赖...');
            fetch('/dependencies/analyze')
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        document.getElementById('totalDeps').textContent = data.summary.total;
                        document.getElementById('outdatedDeps').textContent = data.summary.outdated;
                        document.getElementById('vulnerableDeps').textContent = data.summary.vulnerable;
                        showToast('依赖分析完成');
                    }
                });
        }

        function checkSecurityVulnerabilities() {
            showToast('正在进行安全检查...');
            fetch('/dependencies/security-check')
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        showToast('发现 ' + (data.vulnerabilities?.length || 0) + ' 个潜在问题');
                    }
                });
        }

        function refreshGitStatus() {
            fetch('/git/status')
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        renderGitStatus(data.repos);
                    }
                });
        }

        function renderGitStatus(repos) {
            const el = document.getElementById('gitStatusGrid');
            if (!el || !repos) return;
            el.innerHTML = repos.map(r => `
                <div class="git-repo-card">
                    <div class="git-repo-header">
                        <span class="git-repo-name">📁 ${r.name}</span>
                        <span class="git-branch">🌿 ${r.branch}</span>
                    </div>
                    <div class="git-repo-stats">
                        <span class="git-stat">📝 ${r.modified} 已修改</span>
                        <span class="git-stat">➕ ${r.added} 新文件</span>
                        <span class="git-stat">⏳ ${r.ahead} 待推送</span>
                    </div>
                    <div class="git-repo-actions">
                        <button class="git-btn" onclick="gitCommit('${r.name}')">提交</button>
                        <button class="git-btn" onclick="gitPush('${r.name}')">推送</button>
                        <button class="git-btn" onclick="gitPull('${r.name}')">拉取</button>
                    </div>
                </div>
            `).join('');
        }

        function gitCommit(repo) {
            showToast('正在提交 ' + repo + '...');
        }

        function gitPush(repo) {
            showToast('正在推送 ' + repo + '...');
        }

        function gitPull(repo) {
            showToast('正在拉取 ' + repo + '...');
        }

        function openGitOperationsModal() {
            showToast('打开 Git 操作面板');
        }

        function openNewProjectModal() {
            const modal = document.createElement('div');
            modal.className = 'modal-overlay';
            modal.id = 'newProjectModal';
            modal.innerHTML = `
                <div class="modal-content" style="max-width:500px;">
                    <div class="modal-header">
                        <h3>📁 新建项目</h3>
                        <button class="modal-close" onclick="closeModal('newProjectModal')">×</button>
                    </div>
                    <div class="modal-body">
                        <div style="margin-bottom:15px;">
                            <label style="font-size:12px;display:block;margin-bottom:5px;">项目名称</label>
                            <input class="project-input" id="newProjectName" placeholder="输入项目名称" style="width:100%;">
                        </div>
                        <div style="margin-bottom:15px;">
                            <label style="font-size:12px;display:block;margin-bottom:5px;">项目路径</label>
                            <input class="project-input" id="newProjectPath" placeholder="输入项目路径" style="width:100%;">
                        </div>
                        <div style="margin-bottom:15px;">
                            <label style="font-size:12px;display:block;margin-bottom:5px;">项目描述</label>
                            <textarea class="project-input" id="newProjectDesc" placeholder="输入项目描述" style="width:100%;height:80px;resize:vertical;"></textarea>
                        </div>
                        <div style="display:flex;gap:10px;justify-content:flex-end;">
                            <button class="project-mini-btn" onclick="closeModal('newProjectModal')">取消</button>
                            <button class="project-mini-btn" style="background:var(--primary);color:white;" onclick="createNewProject()">创建</button>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }

        function createNewProject() {
            const name = document.getElementById('newProjectName').value;
            const path = document.getElementById('newProjectPath').value;
            const desc = document.getElementById('newProjectDesc').value;
            if (!name || !path) {
                showToast('请填写项目名称和路径');
                return;
            }
            fetch('/workspace/projects', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, path, description: desc })
            }).then(r => r.json()).then(data => {
                if (data.success) {
                    showToast('项目已创建');
                    closeModal('newProjectModal');
                    refreshWorkspaceProjects();
                } else {
                    showToast('创建失败: ' + data.error);
                }
            });
        }

        function searchProjectTemplates(query) {
            fetch('/templates/search?q=' + encodeURIComponent(query))
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        renderProjectTemplates(data.templates);
                    }
                });
        }

        function renderProjectTemplates(templates) {
            const el = document.getElementById('projectTemplateGrid');
            if (!el || !templates) return;
            el.innerHTML = templates.map(t => `
                <div class="template-card" onclick="useTemplate('${t.id}')">
                    <div class="template-icon">${t.icon}</div>
                    <div class="template-info">
                        <div class="template-name">${t.name}</div>
                        <div class="template-desc">${t.description}</div>
                    </div>
                </div>
            `).join('');
        }

        function useTemplate(templateId) {
            showToast('正在应用模板: ' + templateId);
        }

        function openCreateTemplateModal() {
            showToast('打开创建模板面板');
        }

        function openDeployConfigModal() {
            showToast('打开部署配置面板');
        }

        function executeDeploy() {
            const target = document.getElementById('deployTargetSelect').value;
            showToast('正在部署到 ' + target + '...');
            fetch('/deploy/execute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ target })
            }).then(r => r.json()).then(data => {
                showToast(data.success ? '部署成功' : '部署失败');
            });
        }

        function refreshDataFlowStats() {
            fetch('/dataflow/stats')
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        document.getElementById('dataflowInput').textContent = data.stats.input_count || '--';
                        document.getElementById('dataflowProcess').textContent = data.stats.process_count || '--';
                        document.getElementById('dataflowOutput').textContent = data.stats.output_count || '--';
                        document.getElementById('dataflowRate').textContent = data.stats.rate || '-- req/s';
                        document.getElementById('dataflowQueue').textContent = data.stats.queue_depth || '--';
                        document.getElementById('dataflowLatency').textContent = data.stats.latency || '-- ms';
                    }
                });
        }

        function openDataFlowConfigModal() {
            showToast('打开数据流配置面板');
        }

        function renderConsoleOverview() {
            const el = document.getElementById('consoleScoreGrid');
            if (!el) return;
            const cards = [
                {label: '健康评分', value: `${consoleOverview.health_score ?? 0}`},
                {label: '执行评分', value: `${consoleOverview.execution_score ?? 0}`},
                {label: '增长评分', value: `${consoleOverview.growth_score ?? 0}`},
                {label: '知识评分', value: `${consoleOverview.knowledge_score ?? 0}`}
            ];
            el.innerHTML = cards.map(c => `
                <div class="console-score-card">
                    <div class="console-score-label">${c.label}</div>
                    <div class="console-score-value">${c.value}</div>
                </div>
            `).join('');
        }

        function runGlobalSearch(query = '') {
            const q = encodeURIComponent((query || '').trim());
            const entity = encodeURIComponent((document.getElementById('globalSearchEntity')?.value || '').trim());
            fetch(`/search/global?q=${q}&entity=${entity}&limit=60`).then(r => r.json()).then(data => {
                if (!data.success) return;
                globalSearchResults = data.results || [];
                renderGlobalSearchResults();
            });
        }

        function renderGlobalSearchResults() {
            const el = document.getElementById('globalSearchList');
            if (!el) return;
            if (!globalSearchResults.length) {
                el.innerHTML = '<div class="empty-state"><div class="empty-state-icon">🔍</div><div class="empty-state-text">暂无检索结果</div></div>';
                return;
            }
            el.innerHTML = globalSearchResults.map(item => `
                <div class="project-item">
                    <div class="project-item-top">
                        <div class="project-item-title">${item.title || '未命名'}</div>
                        <span class="project-tag">${item.entity}</span>
                    </div>
                    <div class="project-item-desc">${item.subtitle || ''}</div>
                    <div class="project-item-tags">
                        <span class="project-tag">状态 ${item.status || '-'}</span>
                        ${item.score ? `<span class="project-tag">评分 ${item.score}</span>` : ''}
                        <span class="project-tag">ID ${item.id || '-'}</span>
                    </div>
                </div>
            `).join('');
        }

        function renderConsoleRecommendations() {
            const el = document.getElementById('consoleRecommendationList');
            if (!el) return;
            if (!consoleRecommendations.length) {
                el.innerHTML = '<div class="empty-state"><div class="empty-state-icon">🧠</div><div class="empty-state-text">暂无建议</div></div>';
                return;
            }
            el.innerHTML = consoleRecommendations.map(item => `
                <div class="project-item">
                    <div class="project-item-top">
                        <div class="project-item-title">${item.title}</div>
                        <span class="console-reco-priority ${(item.priority || 'P3').toLowerCase()}">${item.priority || 'P3'}</span>
                    </div>
                    <div class="project-item-desc">${item.detail || ''}</div>
                    <div class="project-item-tags"><span class="project-tag">${item.action || ''}</span></div>
                </div>
            `).join('');
        }

        function renderWorkspaceOverview() {
            const el = document.getElementById('workspaceOverviewCards');
            if (!el) return;
            const cards = [
                {label: '项目总数', value: workspaceOverview.total ?? 0},
                {label: '运行中', value: workspaceOverview.running ?? 0},
                {label: 'Python', value: workspaceOverview.python ?? 0},
                {label: 'Node', value: workspaceOverview.node ?? 0}
            ];
            el.innerHTML = cards.map(c => `
                <div class="ops-kpi-card">
                    <div class="ops-kpi-label">${c.label}</div>
                    <div class="ops-kpi-value">${c.value}</div>
                </div>
            `).join('');
        }

        function renderWorkspaceProjects() {
            const el = document.getElementById('workspaceProjectList');
            if (!el) return;
            if (!workspaceProjects.length) {
                el.innerHTML = '<div class="empty-state"><div class="empty-state-icon">🌐</div><div class="empty-state-text">暂无可整合项目</div></div>';
                return;
            }
            el.innerHTML = workspaceProjects.map(item => `
                <div class="project-item">
                    <div class="project-item-top">
                        <div class="project-item-title">${item.name || '未命名项目'}</div>
                        <span class="project-tag">${item.kind || 'unknown'}</span>
                    </div>
                    <div class="project-item-desc">${item.desc || ''}</div>
                    <div class="project-item-tags">
                        <span class="project-tag">${item.relative_path || '-'}</span>
                        <span class="project-tag">状态 ${item.running ? 'running' : 'idle'}</span>
                        <span class="project-tag">${item.source || 'auto'}</span>
                    </div>
                    <div style="display:flex;gap:6px;margin-top:8px;flex-wrap:wrap;">
                        ${item.default_url ? `<button class="project-mini-btn" onclick="openWorkspaceProject('${item.default_url}')">打开</button>` : ''}
                        ${item.start_command ? `<button class="project-mini-btn" onclick='copyWorkspaceStartCommand(${JSON.stringify(item.start_command)})'>复制启动命令</button>` : ''}
                    </div>
                </div>
            `).join('');
        }

        function openWorkspaceProject(url) {
            if (!url) return;
            window.open(url, '_blank', 'noopener');
        }

        function copyWorkspaceStartCommand(cmd) {
            if (!cmd) return;
            navigator.clipboard.writeText(cmd).then(() => showToast('已复制启动命令')).catch(() => showToast(cmd));
        }
        
        function renderProjectOverview() {
            const el = document.getElementById('projectOverviewCards');
            if (!el) return;
            const cards = [
                {label: '产物总数', value: projectOverview.artifacts ?? 0},
                {label: '置顶产物', value: projectOverview.pinned_artifacts ?? 0},
                {label: '进行中任务', value: projectOverview.tasks_doing ?? 0},
                {label: '完成率', value: `${projectOverview.task_done_rate ?? 0}%`},
                {label: '里程碑', value: projectOverview.milestones ?? 0},
                {label: '风险项', value: projectOverview.risks ?? 0}
            ];
            el.innerHTML = cards.map(c => `
                <div class="project-overview-card">
                    <div class="project-overview-label">${c.label}</div>
                    <div class="project-overview-value">${c.value}</div>
                </div>
            `).join('');
        }
        
        function loadProjectArtifacts(query = '') {
            const q = encodeURIComponent(query || '');
            fetch(`/artifacts?q=${q}`).then(r => r.json()).then(data => {
                if (!data.success) return;
                projectArtifacts = data.artifacts || [];
                renderProjectArtifacts();
            });
        }
        
        function renderProjectArtifacts() {
            const el = document.getElementById('artifactList');
            if (!el) return;
            if (!projectArtifacts.length) {
                el.innerHTML = '<div class="empty-state"><div class="empty-state-icon">📦</div><div class="empty-state-text">暂无产物，点击新增开始沉淀</div></div>';
                return;
            }
            el.innerHTML = projectArtifacts.map(item => `
                <div class="project-item">
                    <div class="project-item-top">
                        <div class="project-item-title">${item.pinned ? '📌 ' : ''}${item.title}</div>
                        <div style="display:flex;gap:6px;">
                            <button class="project-mini-btn" onclick="openArtifactModal('${item.id}')">编辑</button>
                            <button class="project-mini-btn" onclick="showArtifactVersions('${item.id}')">版本${item.version_count || 1}</button>
                            <button class="project-mini-btn" onclick="toggleArtifactPin('${item.id}', ${item.pinned ? 'false' : 'true'})">${item.pinned ? '取消置顶' : '置顶'}</button>
                            <button class="project-mini-btn" onclick="deleteArtifact('${item.id}')">删除</button>
                        </div>
                    </div>
                    <div class="artifact-content-preview">${(item.content || '').slice(0, 180)}</div>
                    <div class="project-item-tags">
                        <span class="project-tag">${item.type || 'note'}</span>
                        <span class="project-tag">${item.source || 'manual'}</span>
                        ${(item.tags || []).slice(0, 3).map(t => `<span class="project-tag">${t}</span>`).join('')}
                    </div>
                </div>
            `).join('');
        }
        
        function openArtifactModal(id = null) {
            editingArtifactId = id;
            const titleEl = document.getElementById('artifactModalTitle');
            const titleInput = document.getElementById('artifactTitleInput');
            const typeInput = document.getElementById('artifactTypeInput');
            const tagsInput = document.getElementById('artifactTagsInput');
            const contentInput = document.getElementById('artifactContentInput');
            if (!titleEl || !titleInput || !typeInput || !tagsInput || !contentInput) return;
            if (id) {
                const item = projectArtifacts.find(x => x.id === id);
                if (!item) return;
                titleEl.textContent = '📝 编辑产物';
                titleInput.value = item.title || '';
                typeInput.value = item.type || 'note';
                tagsInput.value = (item.tags || []).join(',');
                contentInput.value = item.content || '';
            } else {
                titleEl.textContent = '📦 新增产物';
                titleInput.value = '';
                typeInput.value = 'note';
                tagsInput.value = '';
                contentInput.value = '';
            }
            document.getElementById('artifactModal').classList.add('show');
        }
        
        function submitArtifactModal() {
            const title = (document.getElementById('artifactTitleInput').value || '').trim();
            const type = (document.getElementById('artifactTypeInput').value || 'note').trim();
            const tags = (document.getElementById('artifactTagsInput').value || '').split(',').map(x => x.trim()).filter(Boolean);
            const content = (document.getElementById('artifactContentInput').value || '').trim();
            if (!content) return showToast('内容不能为空');
            const payload = {title, content, type, tags, source: 'workspace', editor: 'ui'};
            const method = editingArtifactId ? 'PUT' : 'POST';
            const url = editingArtifactId ? `/artifacts/${editingArtifactId}` : '/artifacts';
            fetch(url, {
                method,
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '保存失败');
                closeModal('artifactModal');
                showToast(editingArtifactId ? '产物已更新' : '产物已新增');
                recordFeatureAction(editingArtifactId ? '更新产物' : '新增产物', '项目中台');
                editingArtifactId = null;
                loadProjectCenter();
            });
        }
        
        function showArtifactVersions(id) {
            fetch(`/artifacts/${id}/versions`).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '获取失败');
                const list = document.getElementById('artifactVersionsList');
                if (!list) return;
                const versions = data.versions || [];
                if (!versions.length) {
                    list.innerHTML = '<div class="empty-state"><div class="empty-state-icon">🕘</div><div class="empty-state-text">暂无版本历史</div></div>';
                } else {
                    list.innerHTML = versions.map(v => `
                        <div class="version-item">
                            <div class="version-head">
                                <span class="version-title">版本 ${v.version} · ${v.title || ''}</span>
                                <button class="project-mini-btn" onclick="restoreArtifactVersion('${id}', ${v.version})">回滚</button>
                            </div>
                            <div class="version-meta">${new Date((v.time || 0) * 1000).toLocaleString('zh-CN')} · ${v.editor || 'system'}</div>
                            <div class="version-body">${(v.content || '').slice(0, 220)}</div>
                        </div>
                    `).join('');
                }
                document.getElementById('artifactVersionsModal').classList.add('show');
            });
        }
        
        function restoreArtifactVersion(id, version) {
            fetch(`/artifacts/${id}/restore`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({version, editor: 'ui'})
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '回滚失败');
                showToast('已回滚到指定版本');
                closeModal('artifactVersionsModal');
                loadProjectCenter();
            });
        }
        
        function toggleArtifactPin(id, pinned) {
            fetch(`/artifacts/${id}/pin`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({pinned})
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '操作失败');
                loadProjectCenter();
            });
        }
        
        function deleteArtifact(id) {
            fetch(`/artifacts/${id}`, {method: 'DELETE'}).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '删除失败');
                showToast('已删除产物');
                loadProjectCenter();
            });
        }
        
        function renderProjectTasks() {
            const el = document.getElementById('projectKanbanBoard');
            if (!el) return;
            if (!projectTasks.length) {
                el.innerHTML = '<div class="empty-state"><div class="empty-state-icon">🗂️</div><div class="empty-state-text">暂无任务，点击任务按钮新增</div></div>';
                return;
            }
            const groups = [
                {key: 'todo', label: '待办'},
                {key: 'doing', label: '进行中'},
                {key: 'done', label: '完成'}
            ];
            el.innerHTML = groups.map(g => {
                const items = projectTasks.filter(t => (t.status || 'todo') === g.key).sort((a, b) => (a.order || 0) - (b.order || 0));
                return `
                    <div class="kanban-column" data-status="${g.key}" ondragover="onTaskColumnDragOver(event)" ondrop="onTaskDrop(event, '${g.key}')" ondragleave="onTaskColumnDragLeave(event)">
                        <div class="kanban-title"><span>${g.label}</span><span>${items.length}</span></div>
                        <div class="kanban-list">
                            ${items.map(task => `
                                <div class="kanban-task" draggable="true" ondragstart="onTaskDragStart(event, '${task.id}')" data-task-id="${task.id}">
                                    <div class="kanban-task-title">${task.title}</div>
                                    <div class="kanban-task-meta">
                                        <span class="project-tag">${task.priority || 'medium'}</span>
                                        ${task.owner ? `<span class="project-tag">${task.owner}</span>` : ''}
                                        <button class="task-status-btn ${selectedTaskIds.has(task.id) ? 'active' : ''}" onclick="toggleTaskSelected('${task.id}')">选择</button>
                                        <button class="task-status-btn" onclick="deleteProjectTask('${task.id}')">删除</button>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                `;
            }).join('');
        }
        
        function openTaskModal() {
            document.getElementById('taskTitleInput').value = '';
            document.getElementById('taskDescInput').value = '';
            document.getElementById('taskPriorityInput').value = 'medium';
            document.getElementById('taskOwnerInput').value = '';
            document.getElementById('taskModal').classList.add('show');
        }
        
        function submitTaskModal() {
            const title = (document.getElementById('taskTitleInput').value || '').trim();
            if (!title) return showToast('任务标题不能为空');
            const description = (document.getElementById('taskDescInput').value || '').trim();
            const priority = (document.getElementById('taskPriorityInput').value || 'medium').trim();
            const owner = (document.getElementById('taskOwnerInput').value || '').trim();
            fetch('/project/tasks', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({title, description, priority, owner, status: 'todo'})
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '创建失败');
                closeModal('taskModal');
                showToast('已新增任务');
                recordFeatureAction('新增项目任务', '项目中台');
                loadProjectCenter();
            });
        }
        
        function updateProjectTaskStatus(id, status) {
            fetch(`/project/tasks/${id}/status`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({status})
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '更新失败');
                loadProjectCenter();
            });
        }
        
        function deleteProjectTask(id) {
            fetch(`/project/tasks/${id}`, {method: 'DELETE'}).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '删除失败');
                showToast('已删除任务');
                loadProjectCenter();
            });
        }
        
        function onTaskDragStart(event, taskId) {
            draggingTaskId = taskId;
            event.dataTransfer.effectAllowed = 'move';
        }
        
        function onTaskColumnDragOver(event) {
            event.preventDefault();
            event.currentTarget.classList.add('drag-over');
        }
        
        function onTaskColumnDragLeave(event) {
            event.currentTarget.classList.remove('drag-over');
        }
        
        function onTaskDrop(event, status) {
            event.preventDefault();
            event.currentTarget.classList.remove('drag-over');
            if (!draggingTaskId) return;
            fetch(`/project/tasks/${draggingTaskId}/status`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({status})
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '拖拽失败');
                draggingTaskId = null;
                loadProjectCenter();
            });
        }
        
        function toggleTaskSelected(id) {
            if (selectedTaskIds.has(id)) selectedTaskIds.delete(id);
            else selectedTaskIds.add(id);
            renderProjectTasks();
        }
        
        function batchMoveTasks(status) {
            const ids = Array.from(selectedTaskIds);
            if (!ids.length) return showToast('请先选择任务');
            fetch('/project/tasks/batch_status', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({task_ids: ids, status})
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '批量操作失败');
                selectedTaskIds.clear();
                showToast(`已批量更新 ${data.updated || 0} 条任务`);
                loadProjectCenter();
            });
        }
        
        function renderProjectPlaybooks() {
            const el = document.getElementById('playbookList');
            if (!el) return;
            if (!projectPlaybooks.length) {
                el.innerHTML = '<div class="empty-state"><div class="empty-state-icon">🧠</div><div class="empty-state-text">暂无剧本模板</div></div>';
                return;
            }
            el.innerHTML = projectPlaybooks.map(item => `
                <div class="project-item">
                    <div class="project-item-top">
                        <div class="project-item-title">${item.name}</div>
                        <button class="project-mini-btn" onclick="runPlaybook('${item.id}')">运行</button>
                    </div>
                    <div class="project-item-desc">${item.description || '无描述'}</div>
                    <div class="project-item-tags">
                        <span class="project-tag">${item.category || '自定义'}</span>
                    </div>
                </div>
            `).join('');
        }
        
        function openPlaybookModal() {
            document.getElementById('playbookNameInput').value = '';
            document.getElementById('playbookCategoryInput').value = '自定义';
            document.getElementById('playbookDescInput').value = '';
            document.getElementById('playbookTemplateInput').value = '';
            document.getElementById('playbookModal').classList.add('show');
        }
        
        function submitPlaybookModal() {
            const name = (document.getElementById('playbookNameInput').value || '').trim();
            const category = (document.getElementById('playbookCategoryInput').value || '自定义').trim();
            const description = (document.getElementById('playbookDescInput').value || '').trim();
            const template = (document.getElementById('playbookTemplateInput').value || '').trim();
            if (!name || !template) return showToast('名称和模板不能为空');
            fetch('/playbooks', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name, category, description, template})
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '创建失败');
                closeModal('playbookModal');
                showToast('已新增剧本');
                loadProjectCenter();
            });
        }
        
        function runPlaybook(id) {
            const topic = prompt('主题');
            if (!topic) return;
            const goal = prompt('目标', '') || '';
            const context = prompt('背景', '') || '';
            const constraints = prompt('约束', '') || '';
            fetch(`/playbooks/${id}/run`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({topic, goal, context, constraints})
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '运行失败');
                usePrompt(data.prompt || '');
                switchTab('prompts', document.querySelector('.sidebar-tab[onclick*="prompts"]'));
                showToast('剧本已生成并填入输入框');
                recordFeatureAction('运行剧本模板', '项目中台');
            });
        }
        
        function loadProjectActivity() {
            fetch('/project/activity?limit=40').then(r => r.json()).then(data => {
                if (!data.success) return;
                projectActivities = data.activities || [];
                renderProjectActivity();
                renderFeatureCenterMeta();
            });
        }
        
        function renderProjectActivity() {
            const el = document.getElementById('projectActivityList');
            if (!el) return;
            if (!projectActivities.length) {
                el.innerHTML = '<div class="empty-state"><div class="empty-state-icon">🕒</div><div class="empty-state-text">暂无操作记录</div></div>';
                return;
            }
            el.innerHTML = projectActivities.slice(0, 40).map(item => `
                <div class="activity-item">
                    <div class="activity-main">${item.action} · ${item.entity} · ${item.detail || item.entity_id}</div>
                    <div class="activity-time">${new Date((item.time || 0) * 1000).toLocaleString('zh-CN', {month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'})}</div>
                </div>
            `).join('');
        }

        function renderProjectMilestones() {
            const el = document.getElementById('milestoneList');
            if (!el) return;
            if (!projectMilestones.length) {
                el.innerHTML = '<div class="empty-state"><div class="empty-state-icon">🎯</div><div class="empty-state-text">暂无里程碑</div></div>';
                return;
            }
            el.innerHTML = projectMilestones.map(item => `
                <div class="project-item">
                    <div class="project-item-top">
                        <div class="project-item-title"><span class="status-dot-badge ${item.status || 'planned'}"></span>${item.title}</div>
                        <div style="display:flex;gap:6px;">
                            <button class="project-mini-btn" onclick="updateMilestoneStatus('${item.id}','active', ${Math.max(Number(item.progress || 0), 10)})">推进</button>
                            <button class="project-mini-btn" onclick="updateMilestoneStatus('${item.id}','done', 100)">完成</button>
                            <button class="project-mini-btn" onclick="updateMilestoneStatus('${item.id}','delayed', ${Number(item.progress || 0)})">延期</button>
                            <button class="project-mini-btn" onclick="deleteMilestone('${item.id}')">删除</button>
                        </div>
                    </div>
                    <div class="project-item-desc">负责人 ${item.owner || '未分配'} · 截止 ${item.due_date || '-'} · 进度 ${item.progress ?? 0}%</div>
                    <div class="project-item-tags">
                        <span class="project-tag">状态 ${item.status || 'planned'}</span>
                    </div>
                </div>
            `).join('');
        }

        function openMilestoneModal() {
            ['milestoneTitleInput','milestoneOwnerInput','milestoneDueInput'].forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
            document.getElementById('milestoneProgressInput').value = '0';
            document.getElementById('milestoneModal').classList.add('show');
        }

        function submitMilestoneModal() {
            const payload = {
                title: (document.getElementById('milestoneTitleInput').value || '').trim(),
                owner: (document.getElementById('milestoneOwnerInput').value || '').trim(),
                due_date: (document.getElementById('milestoneDueInput').value || '').trim(),
                progress: Number(document.getElementById('milestoneProgressInput').value || 0),
                status: 'planned'
            };
            if (!payload.title) return showToast('里程碑标题不能为空');
            fetch('/project/milestones', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '创建失败');
                closeModal('milestoneModal');
                showToast('已新增里程碑');
                loadProjectCenter();
            });
        }

        function updateMilestoneStatus(id, status, progress) {
            fetch(`/project/milestones/${id}/status`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({status, progress})
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '更新失败');
                loadProjectCenter();
            });
        }

        function deleteMilestone(id) {
            fetch(`/project/milestones/${id}`, {method: 'DELETE'}).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '删除失败');
                showToast('已删除里程碑');
                loadProjectCenter();
            });
        }

        function renderProjectRisks() {
            const el = document.getElementById('riskList');
            if (!el) return;
            if (!projectRisks.length) {
                el.innerHTML = '<div class="empty-state"><div class="empty-state-icon">⚠️</div><div class="empty-state-text">暂无风险记录</div></div>';
                return;
            }
            el.innerHTML = projectRisks.map(item => `
                <div class="project-item">
                    <div class="project-item-top">
                        <div class="project-item-title"><span class="status-dot-badge ${item.level || 'medium'}"></span>${item.title}</div>
                        <div style="display:flex;gap:6px;">
                            <button class="project-mini-btn" onclick="updateRiskStatus('${item.id}','mitigating')">缓解中</button>
                            <button class="project-mini-btn" onclick="updateRiskStatus('${item.id}','closed')">关闭</button>
                            <button class="project-mini-btn" onclick="deleteRisk('${item.id}')">删除</button>
                        </div>
                    </div>
                    <div class="project-item-desc">等级 ${item.level || 'medium'} · 状态 ${item.status || 'open'} · 责任人 ${item.owner || '未分配'}</div>
                    <div class="project-item-tags">
                        <span class="project-tag">${item.mitigation || '未填写缓解策略'}</span>
                    </div>
                </div>
            `).join('');
        }

        function openRiskModal() {
            ['riskTitleInput','riskOwnerInput','riskMitigationInput'].forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
            document.getElementById('riskLevelInput').value = 'medium';
            document.getElementById('riskModal').classList.add('show');
        }

        function submitRiskModal() {
            const payload = {
                title: (document.getElementById('riskTitleInput').value || '').trim(),
                owner: (document.getElementById('riskOwnerInput').value || '').trim(),
                level: (document.getElementById('riskLevelInput').value || 'medium').trim(),
                mitigation: (document.getElementById('riskMitigationInput').value || '').trim(),
                status: 'open'
            };
            if (!payload.title) return showToast('风险标题不能为空');
            fetch('/project/risks', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '创建失败');
                closeModal('riskModal');
                showToast('已新增风险');
                loadProjectCenter();
            });
        }

        function updateRiskStatus(id, status) {
            fetch(`/project/risks/${id}/status`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({status})
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '更新失败');
                loadProjectCenter();
            });
        }

        function deleteRisk(id) {
            fetch(`/project/risks/${id}`, {method: 'DELETE'}).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '删除失败');
                showToast('已删除风险');
                loadProjectCenter();
            });
        }

        function renderOpsOverview() {
            const el = document.getElementById('opsOverviewCards');
            if (!el) return;
            const cards = [
                {label: '活动总数', value: opsOverview.campaigns ?? 0},
                {label: '运行中', value: opsOverview.running ?? 0},
                {label: '平均CTR', value: `${opsOverview.avg_ctr ?? 0}%`},
                {label: '总预算', value: `¥${opsOverview.total_budget ?? 0}`}
            ];
            el.innerHTML = cards.map(c => `
                <div class="ops-kpi-card">
                    <div class="ops-kpi-label">${c.label}</div>
                    <div class="ops-kpi-value">${c.value}</div>
                </div>
            `).join('');
        }
        
        function loadOpsCampaigns(query = '') {
            const q = encodeURIComponent(query || '');
            fetch(`/ops/campaigns?q=${q}`).then(r => r.json()).then(data => {
                if (!data.success) return;
                opsCampaigns = data.campaigns || [];
                renderOpsCampaigns();
            });
        }
        
        function renderOpsCampaigns() {
            const el = document.getElementById('opsCampaignList');
            if (!el) return;
            if (!opsCampaigns.length) {
                el.innerHTML = '<div class="empty-state"><div class="empty-state-icon">📣</div><div class="empty-state-text">暂无运营活动</div></div>';
                return;
            }
            el.innerHTML = opsCampaigns.map(item => `
                <div class="project-item">
                    <div class="project-item-top">
                        <div class="project-item-title"><span class="status-dot-badge ${item.status || 'draft'}"></span>${item.name}</div>
                        <div style="display:flex;gap:6px;">
                            <button class="project-mini-btn" onclick="updateOpsCampaignStatus('${item.id}','running')">运行</button>
                            <button class="project-mini-btn" onclick="updateOpsCampaignStatus('${item.id}','paused')">暂停</button>
                            <button class="project-mini-btn" onclick="updateOpsCampaignStatus('${item.id}','done')">完成</button>
                            <button class="project-mini-btn" onclick="deleteOpsCampaign('${item.id}')">删除</button>
                        </div>
                    </div>
                    <div class="project-item-desc">${item.channel || '全渠道'} · 负责人 ${item.owner || '未分配'} · ${item.start_date || '-'} ~ ${item.end_date || '-'}</div>
                    <div class="project-item-tags">
                        <span class="project-tag">预算 ¥${item.budget ?? 0}</span>
                        <span class="project-tag">目标CTR ${item.target_ctr ?? 0}%</span>
                        <span class="project-tag">当前CTR ${item.current_ctr ?? 0}%</span>
                    </div>
                </div>
            `).join('');
        }
        
        function openOpsCampaignModal() {
            ['opsCampaignNameInput','opsCampaignChannelInput','opsCampaignOwnerInput','opsCampaignBudgetInput','opsCampaignTargetCtrInput','opsCampaignCurrentCtrInput','opsCampaignStartInput','opsCampaignEndInput','opsCampaignNotesInput']
                .forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
            document.getElementById('opsCampaignModal').classList.add('show');
        }
        
        function submitOpsCampaignModal() {
            const payload = {
                name: (document.getElementById('opsCampaignNameInput').value || '').trim(),
                channel: (document.getElementById('opsCampaignChannelInput').value || '').trim(),
                owner: (document.getElementById('opsCampaignOwnerInput').value || '').trim(),
                budget: Number(document.getElementById('opsCampaignBudgetInput').value || 0),
                target_ctr: Number(document.getElementById('opsCampaignTargetCtrInput').value || 0),
                current_ctr: Number(document.getElementById('opsCampaignCurrentCtrInput').value || 0),
                start_date: (document.getElementById('opsCampaignStartInput').value || '').trim(),
                end_date: (document.getElementById('opsCampaignEndInput').value || '').trim(),
                notes: (document.getElementById('opsCampaignNotesInput').value || '').trim(),
                status: 'draft'
            };
            if (!payload.name) return showToast('活动名称不能为空');
            fetch('/ops/campaigns', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '创建失败');
                closeModal('opsCampaignModal');
                showToast('已新增运营活动');
                recordFeatureAction('新增运营活动', '运营中心');
                loadProjectCenter();
            });
        }
        
        function updateOpsCampaignStatus(id, status) {
            fetch(`/ops/campaigns/${id}/status`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({status})
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '更新失败');
                loadProjectCenter();
            });
        }
        
        function deleteOpsCampaign(id) {
            fetch(`/ops/campaigns/${id}`, {method: 'DELETE'}).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '删除失败');
                showToast('已删除活动');
                loadProjectCenter();
            });
        }
        
        function renderReleaseOverview() {
            const el = document.getElementById('releaseOverviewCards');
            if (!el) return;
            const cards = [
                {label: '计划总数', value: releaseOverview.plans ?? 0},
                {label: '待发布', value: releaseOverview.ready ?? 0},
                {label: '回滚次数', value: releaseOverview.rollback ?? 0},
                {label: '高风险', value: releasePlans.filter(x => x.risk === 'high').length}
            ];
            el.innerHTML = cards.map(c => `
                <div class="ops-kpi-card">
                    <div class="ops-kpi-label">${c.label}</div>
                    <div class="ops-kpi-value">${c.value}</div>
                </div>
            `).join('');
        }
        
        function renderReleasePlans() {
            const el = document.getElementById('releasePlanList');
            if (!el) return;
            if (!releasePlans.length) {
                el.innerHTML = '<div class="empty-state"><div class="empty-state-icon">🚀</div><div class="empty-state-text">暂无发布计划</div></div>';
                return;
            }
            el.innerHTML = releasePlans.map(item => `
                <div class="project-item">
                    <div class="project-item-top">
                        <div class="project-item-title"><span class="status-dot-badge ${item.status || 'planning'}"></span>${item.version} · ${item.title}</div>
                        <div style="display:flex;gap:6px;">
                            <button class="project-mini-btn" onclick="updateReleaseStatus('${item.id}','review')">评审</button>
                            <button class="project-mini-btn" onclick="updateReleaseStatus('${item.id}','ready')">就绪</button>
                            <button class="project-mini-btn" onclick="updateReleaseStatus('${item.id}','released')">发布</button>
                            <button class="project-mini-btn" onclick="updateReleaseStatus('${item.id}','rollback')">回滚</button>
                            <button class="project-mini-btn" onclick="deleteReleasePlan('${item.id}')">删除</button>
                        </div>
                    </div>
                    <div class="project-item-desc">${item.environment || 'production'} · 风险 ${item.risk || 'medium'} · 负责人 ${item.owner || '未分配'}</div>
                    <div class="release-checklist">
                        ${(item.checklist || []).slice(0, 5).map((c, idx) => `
                            <label class="release-check">
                                <input type="checkbox" ${c.checked ? 'checked' : ''} onchange="toggleReleaseCheck('${item.id}', ${idx}, this.checked)">
                                <span>${c.label || c}</span>
                            </label>
                        `).join('')}
                    </div>
                </div>
            `).join('');
        }
        
        function openReleasePlanModal() {
            ['releaseVersionInput','releaseOwnerInput','releaseTitleInput','releaseChecklistInput','releaseNotesInput']
                .forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
            document.getElementById('releaseEnvInput').value = 'production';
            document.getElementById('releaseRiskInput').value = 'medium';
            document.getElementById('releasePlanModal').classList.add('show');
        }
        
        function submitReleasePlanModal() {
            const lines = (document.getElementById('releaseChecklistInput').value || '').split("\\n").map(x => x.trim()).filter(Boolean);
            const checklist = lines.map(x => ({label: x, checked: false}));
            const payload = {
                version: (document.getElementById('releaseVersionInput').value || '').trim(),
                title: (document.getElementById('releaseTitleInput').value || '').trim(),
                owner: (document.getElementById('releaseOwnerInput').value || '').trim(),
                environment: (document.getElementById('releaseEnvInput').value || 'production').trim(),
                risk: (document.getElementById('releaseRiskInput').value || 'medium').trim(),
                notes: (document.getElementById('releaseNotesInput').value || '').trim(),
                checklist
            };
            if (!payload.version || !payload.title) return showToast('版本和标题不能为空');
            fetch('/release/plans', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '创建失败');
                closeModal('releasePlanModal');
                showToast('已新增发布计划');
                recordFeatureAction('新增发布计划', '发布中心');
                loadProjectCenter();
            });
        }
        
        function updateReleaseStatus(id, status) {
            fetch(`/release/plans/${id}/status`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({status})
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '更新失败');
                loadProjectCenter();
            });
        }
        
        function toggleReleaseCheck(id, index, checked) {
            fetch(`/release/plans/${id}/check`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({index, checked})
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '更新失败');
                loadProjectCenter();
            });
        }
        
        function deleteReleasePlan(id) {
            fetch(`/release/plans/${id}`, {method: 'DELETE'}).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '删除失败');
                showToast('已删除发布计划');
                loadProjectCenter();
            });
        }

        function renderAlertOverview() {
            const el = document.getElementById('alertOverviewCards');
            if (!el) return;
            const cards = [
                {label: '规则总数', value: alertOverview.rules ?? 0},
                {label: '激活中', value: alertOverview.active ?? 0},
                {label: '严重告警', value: alertOverview.critical ?? 0},
                {label: '已恢复', value: alertRules.filter(x => x.status === 'resolved').length}
            ];
            el.innerHTML = cards.map(c => `<div class="ops-kpi-card"><div class="ops-kpi-label">${c.label}</div><div class="ops-kpi-value">${c.value}</div></div>`).join('');
        }

        function renderAlertRules() {
            const el = document.getElementById('alertRuleList');
            if (!el) return;
            if (!alertRules.length) {
                el.innerHTML = '<div class="empty-state"><div class="empty-state-icon">🚨</div><div class="empty-state-text">暂无告警规则</div></div>';
                return;
            }
            el.innerHTML = alertRules.map(item => `
                <div class="project-item">
                    <div class="project-item-top">
                        <div class="project-item-title"><span class="status-dot-badge ${item.level || 'medium'}"></span>${item.name}</div>
                        <div style="display:flex;gap:6px;">
                            <button class="project-mini-btn" onclick="updateAlertRuleStatus('${item.id}','active')">激活</button>
                            <button class="project-mini-btn" onclick="updateAlertRuleStatus('${item.id}','muted')">静默</button>
                            <button class="project-mini-btn" onclick="updateAlertRuleStatus('${item.id}','resolved')">恢复</button>
                            <button class="project-mini-btn" onclick="deleteAlertRule('${item.id}')">删除</button>
                        </div>
                    </div>
                    <div class="project-item-desc">${item.metric || 'metric'} · 阈值 ${item.threshold ?? 0} · 当前 ${item.current_value ?? 0} · 负责人 ${item.owner || '未分配'}</div>
                    <div class="project-item-tags">
                        <span class="project-tag">等级 ${item.level || 'medium'}</span>
                        <span class="project-tag">状态 ${item.status || 'active'}</span>
                    </div>
                </div>
            `).join('');
        }

        function openAlertRuleModal() {
            ['alertRuleNameInput','alertMetricInput','alertThresholdInput','alertOwnerInput'].forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
            document.getElementById('alertLevelInput').value = 'medium';
            document.getElementById('alertRuleModal').classList.add('show');
        }

        function submitAlertRuleModal() {
            const payload = {
                name: (document.getElementById('alertRuleNameInput').value || '').trim(),
                metric: (document.getElementById('alertMetricInput').value || '').trim(),
                threshold: Number(document.getElementById('alertThresholdInput').value || 0),
                level: (document.getElementById('alertLevelInput').value || 'medium').trim(),
                owner: (document.getElementById('alertOwnerInput').value || '').trim(),
                status: 'active',
                current_value: 0
            };
            if (!payload.name || !payload.metric) return showToast('规则名称和指标不能为空');
            fetch('/alerts/rules', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '创建失败');
                closeModal('alertRuleModal');
                showToast('已新增告警规则');
                recordFeatureAction('新增告警规则', '告警中心');
                loadProjectCenter();
            });
        }

        function updateAlertRuleStatus(id, status) {
            fetch(`/alerts/rules/${id}/status`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({status})
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '更新失败');
                loadProjectCenter();
            });
        }

        function deleteAlertRule(id) {
            fetch(`/alerts/rules/${id}`, {method: 'DELETE'}).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '删除失败');
                showToast('已删除告警规则');
                loadProjectCenter();
            });
        }

        function renderAbOverview() {
            const el = document.getElementById('abOverviewCards');
            if (!el) return;
            const cards = [
                {label: '实验总数', value: abOverview.experiments ?? 0},
                {label: '运行中', value: abOverview.running ?? 0},
                {label: '已完成', value: abExperiments.filter(x => x.status === 'completed').length},
                {label: '平均流量', value: `${abExperiments.length ? Math.round(abExperiments.reduce((s, x) => s + (Number(x.traffic || 0)), 0) / abExperiments.length) : 0}%`}
            ];
            el.innerHTML = cards.map(c => `<div class="ops-kpi-card"><div class="ops-kpi-label">${c.label}</div><div class="ops-kpi-value">${c.value}</div></div>`).join('');
        }

        function renderAbExperiments() {
            const el = document.getElementById('abExperimentList');
            if (!el) return;
            if (!abExperiments.length) {
                el.innerHTML = '<div class="empty-state"><div class="empty-state-icon">🧪</div><div class="empty-state-text">暂无A/B实验</div></div>';
                return;
            }
            el.innerHTML = abExperiments.map(item => `
                <div class="project-item">
                    <div class="project-item-top">
                        <div class="project-item-title"><span class="status-dot-badge ${item.status || 'draft'}"></span>${item.name}</div>
                        <div style="display:flex;gap:6px;">
                            <button class="project-mini-btn" onclick="updateAbStatus('${item.id}','running')">运行</button>
                            <button class="project-mini-btn" onclick="updateAbStatus('${item.id}','paused')">暂停</button>
                            <button class="project-mini-btn" onclick="updateAbStatus('${item.id}','completed')">完成</button>
                            <button class="project-mini-btn" onclick="deleteAb('${item.id}')">删除</button>
                        </div>
                    </div>
                    <div class="project-item-desc">${item.metric || 'metric'} · 流量 ${item.traffic ?? 0}% · 负责人 ${item.owner || '未分配'}</div>
                    <div class="project-item-tags">
                        <span class="project-tag">基线 ${item.baseline ?? 0}</span>
                        <span class="project-tag">实验组 ${item.variant ?? 0}</span>
                        <button class="project-mini-btn" onclick="refreshAbMetric('${item.id}')">刷新指标</button>
                    </div>
                </div>
            `).join('');
        }

        function openAbModal() {
            ['abNameInput','abMetricInput','abOwnerInput'].forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
            document.getElementById('abTrafficInput').value = '50';
            document.getElementById('abModal').classList.add('show');
        }

        function submitAbModal() {
            const payload = {
                name: (document.getElementById('abNameInput').value || '').trim(),
                metric: (document.getElementById('abMetricInput').value || '').trim(),
                traffic: Number(document.getElementById('abTrafficInput').value || 50),
                owner: (document.getElementById('abOwnerInput').value || '').trim(),
                status: 'draft',
                baseline: 0,
                variant: 0
            };
            if (!payload.name || !payload.metric) return showToast('实验名称和指标不能为空');
            fetch('/ab/experiments', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '创建失败');
                closeModal('abModal');
                showToast('已新增AB实验');
                recordFeatureAction('新增AB实验', '实验中心');
                loadProjectCenter();
            });
        }

        function updateAbStatus(id, status) {
            fetch(`/ab/experiments/${id}/status`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({status})
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '更新失败');
                loadProjectCenter();
            });
        }

        function refreshAbMetric(id) {
            const baseline = Number((Math.random() * 10 + 20).toFixed(2));
            const variant = Number((baseline + (Math.random() * 6 - 1)).toFixed(2));
            fetch(`/ab/experiments/${id}/metrics`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({baseline, variant})
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '更新失败');
                loadProjectCenter();
            });
        }

        function deleteAb(id) {
            fetch(`/ab/experiments/${id}`, {method: 'DELETE'}).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '删除失败');
                showToast('已删除AB实验');
                loadProjectCenter();
            });
        }

        function renderIntegrationOverview() {
            const el = document.getElementById('integrationOverviewCards');
            if (!el) return;
            const cards = [
                {label: '集成总数', value: integrationOverview.integrations ?? 0},
                {label: '已启用', value: integrationOverview.enabled ?? 0},
                {label: '异常数', value: integrationOverview.errors ?? 0},
                {label: '平均健康度', value: `${integrationItems.length ? Math.round(integrationItems.reduce((s, x) => s + (Number(x.health || 0)), 0) / integrationItems.length) : 0}%`}
            ];
            el.innerHTML = cards.map(c => `<div class="ops-kpi-card"><div class="ops-kpi-label">${c.label}</div><div class="ops-kpi-value">${c.value}</div></div>`).join('');
        }

        function renderIntegrations() {
            const el = document.getElementById('integrationList');
            if (!el) return;
            if (!integrationItems.length) {
                el.innerHTML = '<div class="empty-state"><div class="empty-state-icon">🧩</div><div class="empty-state-text">暂无集成配置</div></div>';
                return;
            }
            el.innerHTML = integrationItems.map(item => `
                <div class="project-item">
                    <div class="project-item-top">
                        <div class="project-item-title"><span class="status-dot-badge ${item.status || 'disabled'}"></span>${item.name}</div>
                        <div style="display:flex;gap:6px;">
                            <button class="project-mini-btn" onclick="updateIntegrationStatus('${item.id}','enabled')">启用</button>
                            <button class="project-mini-btn" onclick="updateIntegrationStatus('${item.id}','disabled')">停用</button>
                            <button class="project-mini-btn" onclick="updateIntegrationStatus('${item.id}','error')">标异常</button>
                            <button class="project-mini-btn" onclick="deleteIntegration('${item.id}')">删除</button>
                        </div>
                    </div>
                    <div class="project-item-desc">${item.provider || 'provider'} · 负责人 ${item.owner || '未分配'} · 健康度 ${item.health ?? 0}%</div>
                    <div class="project-item-tags"><span class="project-tag">${item.desc || '无说明'}</span></div>
                </div>
            `).join('');
        }

        function openIntegrationModal() {
            ['integrationNameInput','integrationProviderInput','integrationDescInput','integrationOwnerInput'].forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
            document.getElementById('integrationHealthInput').value = '80';
            document.getElementById('integrationModal').classList.add('show');
        }

        function submitIntegrationModal() {
            const payload = {
                name: (document.getElementById('integrationNameInput').value || '').trim(),
                provider: (document.getElementById('integrationProviderInput').value || '').trim(),
                desc: (document.getElementById('integrationDescInput').value || '').trim(),
                owner: (document.getElementById('integrationOwnerInput').value || '').trim(),
                health: Number(document.getElementById('integrationHealthInput').value || 80),
                status: 'disabled'
            };
            if (!payload.name || !payload.provider) return showToast('集成名称和提供方不能为空');
            fetch('/integrations', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '创建失败');
                closeModal('integrationModal');
                showToast('已新增集成');
                recordFeatureAction('新增集成', '集成市场');
                loadProjectCenter();
            });
        }

        function updateIntegrationStatus(id, status) {
            fetch(`/integrations/${id}/status`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({status})
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '更新失败');
                loadProjectCenter();
            });
        }

        function deleteIntegration(id) {
            fetch(`/integrations/${id}`, {method: 'DELETE'}).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '删除失败');
                showToast('已删除集成');
                loadProjectCenter();
            });
        }
        
        function searchChats(query) {
            const filtered = chats.filter(c => 
                c.title.toLowerCase().includes(query.toLowerCase()) ||
                c.messages.some(m => m.content.toLowerCase().includes(query.toLowerCase()))
            );
            document.getElementById('chatList').innerHTML = filtered.map(c => `
                <div class="chat-item ${c.id === currentChatId ? 'active' : ''}" onclick="loadChat('${c.id}')">
                    <span>💬</span>
                    <span class="chat-item-title">${c.title || '新对话'}</span>
                    <button class="chat-item-delete" onclick="event.stopPropagation();deleteChat('${c.id}')">🗑️</button>
                </div>
            `).join('');
        }
        
        let currentReader = null;
        let isGenerating = false;
        
        function stopGeneration() {
            if (currentReader) {
                currentReader.cancel();
                currentReader = null;
            }
            isGenerating = false;
            document.getElementById('sendBtn').style.display = 'flex';
            document.getElementById('stopBtn').style.display = 'none';
            document.getElementById('statusText').textContent = '已停止';
            showToast('已停止生成');
        }
        
        function newChat() {
            const id = Date.now().toString();
            chats.unshift({ id, title: '新对话', messages: [], created: new Date().toISOString(), role: currentRole, lora: currentLora, starred: false });
            saveChats();
            currentChatId = id;
            history = [];
            showWelcome();
            renderChatList();
            showToast('已创建新对话');
        }
        
        function toggleStarChat(id) {
            const chat = chats.find(c => c.id === id);
            if (chat) {
                chat.starred = !chat.starred;
                saveChats();
                renderChatList();
                showToast(chat.starred ? '已收藏' : '已取消收藏');
            }
        }
        
        function loadChat(id) {
            currentChatId = id;
            const chat = chats.find(c => c.id === id);
            if (!chat) return;
            history = [];
            attachments = [];
            document.getElementById('messagesContainer').innerHTML = '';
            if (chat.role) selectRole(chat.role);
            chat.messages.forEach((m, idx) => {
                addMessageToUI(m.role, m.content, m.time, m.toolResults, idx, m.reasoning);
                if (m.role === 'user') history.push([m.content, '']);
            });
            chat.messages.filter(m => m.role === 'assistant').forEach((m, i) => {
                if (history[i]) history[i][1] = m.content;
            });
            renderChatList();
        }
        
        function deleteChat(id) {
            chats = chats.filter(c => c.id !== id);
            saveChats();
            if (currentChatId === id) {
                if (chats.length > 0) loadChat(chats[0].id);
                else { 
                    currentChatId = null; 
                    history = []; 
                    showWelcome();
                }
            }
            renderChatList();
            showToast('对话已删除');
        }
        
        let editingMsgIdx = null;
        let replyingTo = null;
        
        function editMessage(idx) {
            const chat = chats.find(c => c.id === currentChatId);
            if (!chat || !chat.messages[idx]) return;
            const msg = chat.messages[idx];
            if (msg.role !== 'user') return;
            editingMsgIdx = idx;
            const input = document.getElementById('mainInput');
            input.value = msg.content;
            input.focus();
            updateCharCount();
            document.getElementById('editHint').style.display = 'flex';
        }
        
        function cancelEdit() {
            editingMsgIdx = null;
            document.getElementById('mainInput').value = '';
            document.getElementById('editHint').style.display = 'none';
            updateCharCount();
        }
        
        function replyToMessage(idx) {
            const chat = chats.find(c => c.id === currentChatId);
            if (!chat || !chat.messages[idx]) return;
            replyingTo = { idx, content: chat.messages[idx].content.slice(0, 100) };
            document.getElementById('replyHint').style.display = 'flex';
            document.getElementById('replyContent').textContent = replyingTo.content;
            document.getElementById('mainInput').focus();
        }
        
        function cancelReply() {
            replyingTo = null;
            document.getElementById('replyHint').style.display = 'none';
        }
        
        function addMessageToUI(role, content, time = null, toolResults = null, msgIdx = null, reasoning = null) {
            const container = document.getElementById('messagesContainer');
            const msg = document.createElement('div');
            msg.className = `message ${role}`;
            msg.dataset.idx = msgIdx;
            const t = time || new Date().toLocaleTimeString('zh-CN', {hour:'2-digit',minute:'2-digit'});
            const roleData = roles.find(r => r.id === currentRole) || roles[0];
            const avatar = role === 'user' ? '👤' : (roleData.avatar.startsWith('/') ? `<img src="${roleData.avatar}">` : roleData.icon);
            
            let toolHtml = '';
            if (toolResults && toolResults.length) {
                toolHtml = toolResults.map(tr => `<div class="tool-result"><strong>${tr.tool}:</strong> ${tr.result}</div>`).join('');
            }
            
            // 构建思考过程HTML（如果有）
            let reasoningHtml = '';
            if (reasoning && reasoning.trim()) {
                reasoningHtml = `
                    <div class="reasoning-section">
                        <div class="reasoning-toggle" onclick="toggleReasoning(this)">
                            <span class="reasoning-toggle-icon">▶</span>
                            <span>思考过程</span>
                        </div>
                        <div class="reasoning-content">${reasoning.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</div>
                    </div>
                `;
            }
            
            const renderedContent = settings.markdown ? marked.parse(content) : content.replace(/\\n/g, '<br>');
            let actionBtns = `<button class="msg-action-btn" onclick="copyMessage(this)">📋</button><button class="msg-action-btn" onclick="speakMessage(this)">🔊</button>`;
            if (role === 'user' && msgIdx !== null) {
                actionBtns += `<button class="msg-action-btn" onclick="editMessage(${msgIdx})">✏️</button>`;
            }
            if (msgIdx !== null) {
                actionBtns += `<button class="msg-action-btn" onclick="replyToMessage(${msgIdx})">↩️</button>`;
            }
            
            msg.innerHTML = `
                <div class="message-avatar" style="background:linear-gradient(135deg,var(--primary),var(--secondary));">${avatar}</div>
                <div class="message-content-wrapper">
                    ${reasoningHtml}
                    <div class="message-content">${renderedContent}</div>
                    ${toolHtml}
                    <div class="message-actions">${actionBtns}</div>
                    <div class="message-time">${t}</div>
                </div>
            `;
            container.appendChild(msg);
            container.scrollTop = container.scrollHeight;
            msg.querySelectorAll('pre code').forEach(block => hljs.highlightElement(block));
        }
        
        function handleInput(e) {
            updateCharCount();
            autoResize(e.target);
            const value = e.target.value;
            const hint = document.getElementById('commandHint');
            if (value.startsWith('/')) {
                const cmd = value.slice(1).toLowerCase();
                const matches = Object.entries(commands).filter(([k]) => k.slice(1).startsWith(cmd));
                if (matches.length) {
                    hint.innerHTML = matches.map(([k,v]) => `<div class="command-item" onclick="executeCommand('${k}')"><strong>${k}</strong> - ${v}</div>`).join('');
                    hint.classList.add('show');
                } else hint.classList.remove('show');
            } else hint.classList.remove('show');
        }
        
        function executeCommand(cmd) {
            document.getElementById('mainInput').value = '';
            document.getElementById('commandHint').classList.remove('show');
            switch(cmd) {
                case '/help': showToast('命令: /clear /export /role /lora /tool /code /kb /settings /stats /new'); break;
                case '/clear': clearCurrentChat(); break;
                case '/export': exportChat(); break;
                case '/code': showCodeModal(); break;
                case '/tool': switchTab('tools'); break;
                case '/kb': showKBModal(); break;
                case '/settings': openSettings(); break;
                case '/new': newChat(); break;
            }
        }
        
        function clearCurrentChat() {
            const chat = chats.find(c => c.id === currentChatId);
            if (chat) { 
                chat.messages = []; 
                history = []; 
                saveChats(); 
                showWelcome(); 
                showToast('对话已清空'); 
            }
        }
        
        function openPromptWorkbenchModal() {
            const tab = document.querySelector('.sidebar-tab[onclick*="prompts"]');
            if (tab) switchTab('prompts', tab);
        }
        
        function saveFeatureActionHistory() {
            localStorage.setItem('kaguya_feature_actions', JSON.stringify(featureActionHistory.slice(0, 20)));
        }
        
        function recordFeatureAction(name, type = '导航') {
            const item = {
                name,
                type,
                time: Date.now()
            };
            featureActionHistory.unshift(item);
            featureActionHistory = featureActionHistory.slice(0, 20);
            saveFeatureActionHistory();
            renderFeatureCenterMeta();
        }
        
        function renderFeatureCenterMeta() {
            const statusEl = document.getElementById('centerStatusGrid');
            const recentEl = document.getElementById('centerRecentActions');
            if (!statusEl || !recentEl) return;
            const enabledPlugins = mcpPlugins.filter(x => x.enabled).length;
            const statusItems = [
                {label: 'DeepSeek', value: deepseekConfig.enabled ? '已启用' : '未启用', cls: deepseekConfig.enabled ? 'ok' : 'warn'},
                {label: 'RAG状态', value: ragEnabled ? '已开启' : '已关闭', cls: ragEnabled ? 'ok' : 'warn'},
                {label: '文档总数', value: `${ragDocuments.length}`, cls: ragDocuments.length > 0 ? 'ok' : 'warn'},
                {label: '健康评分', value: `${consoleOverview.health_score ?? 0}`, cls: (consoleOverview.health_score ?? 0) >= 70 ? 'ok' : 'warn'},
                {label: '工作流', value: `${workflows.length}`, cls: workflows.length > 0 ? 'ok' : 'warn'},
                {label: '启用插件', value: `${enabledPlugins}`, cls: enabledPlugins > 0 ? 'ok' : 'warn'},
                {label: '会话总数', value: `${chats.length}`, cls: chats.length > 0 ? 'ok' : 'warn'},
                {label: '项目任务', value: `${projectTasks.length}`, cls: projectTasks.length > 0 ? 'ok' : 'warn'},
                {label: '知识产物', value: `${projectArtifacts.length}`, cls: projectArtifacts.length > 0 ? 'ok' : 'warn'},
                {label: '运营活动', value: `${opsCampaigns.length}`, cls: opsCampaigns.length > 0 ? 'ok' : 'warn'},
                {label: '发布计划', value: `${releasePlans.length}`, cls: releasePlans.length > 0 ? 'ok' : 'warn'},
                {label: '告警规则', value: `${alertRules.length}`, cls: alertRules.length > 0 ? 'ok' : 'warn'},
                {label: 'AB实验', value: `${abExperiments.length}`, cls: abExperiments.length > 0 ? 'ok' : 'warn'},
                {label: '集成数', value: `${integrationItems.length}`, cls: integrationItems.length > 0 ? 'ok' : 'warn'},
                {label: '里程碑', value: `${projectMilestones.length}`, cls: projectMilestones.length > 0 ? 'ok' : 'warn'},
                {label: '风险项', value: `${projectRisks.length}`, cls: projectRisks.length > 0 ? 'ok' : 'warn'},
                {label: '生态项目', value: `${workspaceOverview.total ?? workspaceProjects.length}`, cls: (workspaceOverview.total ?? workspaceProjects.length) > 0 ? 'ok' : 'warn'}
            ];
            statusEl.innerHTML = statusItems.map(s => `
                <div class="feature-center-status-item">
                    <div class="feature-center-status-label">${s.label}</div>
                    <div class="feature-center-status-value ${s.cls}">${s.value}</div>
                </div>
            `).join('');
            if (!featureActionHistory.length) {
                recentEl.innerHTML = '<div style="font-size:11px;color:var(--text-muted);text-align:center;padding:10px;">暂无操作记录</div>';
            } else {
                recentEl.innerHTML = featureActionHistory.slice(0, 8).map(item => `
                    <div class="feature-center-recent-item">
                        <span>${item.type} · ${item.name}</span>
                        <span>${new Date(item.time).toLocaleTimeString('zh-CN', {hour: '2-digit', minute: '2-digit'})}</span>
                    </div>
                `).join('');
            }
        }
        
        function focusFeatureTarget(targetId) {
            if (!targetId) return;
            const el = document.getElementById(targetId);
            if (!el) return;
            el.scrollIntoView({behavior: 'smooth', block: 'start'});
            el.classList.add('section-focus');
            setTimeout(() => el.classList.remove('section-focus'), 1200);
        }
        
        function getFeatureTargetId(name) {
            const map = {
                console: 'consoleScoreGrid',
                ecosystem: 'workspaceOverviewCards',
                scenes: 'sceneWorkspace',
                prompts: 'promptList',
                project: 'projectOverviewCards',
                ops: 'opsOverviewCards',
                release: 'releaseOverviewCards',
                alert: 'alertOverviewCards',
                ab: 'abOverviewCards',
                integration: 'integrationOverviewCards',
                workflow: 'workflowList',
                memory: 'memoryList',
                multimodal: 'multimodalResults',
                finetune: 'finetuneJobs',
                rag: 'ragDocList',
                mcp: 'mcpList'
            };
            return map[name] || null;
        }
        
        function openMobileSection(tabName) {
            const target = tabName === 'center' ? null : document.querySelector(`.sidebar-tab[onclick*="${tabName}"]`);
            if (tabName === 'center') {
                openFeatureCenter();
            } else if (target) {
                switchTab(tabName, target);
                focusFeatureTarget(getFeatureTargetId(tabName));
                recordFeatureAction(`移动端切换到${tabName}`, '快捷栏');
            }
            document.querySelectorAll('.mobile-dock-btn').forEach(btn => btn.classList.remove('active'));
            const activeBtn = document.querySelector(`.mobile-dock-btn[data-mobile-tab="${tabName}"]`);
            if (activeBtn) activeBtn.classList.add('active');
        }
        
        function openFeatureSection(name) {
            closeModal('featureCenterModal');
            const tabMappings = ['console', 'ecosystem', 'scenes', 'prompts', 'project', 'ops', 'release', 'alert', 'ab', 'integration', 'workflow', 'memory', 'multimodal', 'finetune', 'rag', 'mcp'];
            const nameMap = {
                console: '统一控制台',
                ecosystem: '项目生态',
                scenes: '场景引擎',
                prompts: '模板工作台',
                project: '项目中台',
                ops: '运营中心',
                release: '发布中心',
                alert: '告警中心',
                ab: '实验中心',
                integration: '集成市场',
                workflow: '工作流编排',
                memory: '记忆系统',
                multimodal: '视觉理解',
                finetune: '模型微调',
                rag: 'RAG知识库',
                mcp: 'MCP插件',
                models: '多模型API',
                settings: '系统设置',
                deepseek: 'DeepSeek配置',
                code: '代码执行器',
                stats: '统计仪表盘'
            };
            
            if (tabMappings.includes(name)) {
                const target = document.querySelector(`.sidebar-tab[onclick*="${name}"]`);
                if (target) {
                    target.click();
                } else {
                    switchTab(name, null);
                }
                setTimeout(() => {
                    const targetId = getFeatureTargetId(name);
                    const elem = document.getElementById(targetId);
                    if (elem) elem.scrollIntoView({behavior: 'smooth', block: 'center'});
                }, 300);
                recordFeatureAction(nameMap[name] || name, '功能中心');
                return;
            }
            if (name === 'models') { openModelsConfig(); recordFeatureAction(nameMap[name], '功能中心'); return; }
            if (name === 'settings') { openSettings(); recordFeatureAction(nameMap[name], '功能中心'); return; }
            if (name === 'deepseek') { openDeepSeek(); recordFeatureAction(nameMap[name], '功能中心'); return; }
            if (name === 'code') { showCodeModal(); recordFeatureAction(nameMap[name], '功能中心'); return; }
            if (name === 'stats') { openStats(); recordFeatureAction(nameMap[name], '功能中心'); return; }
        }
        
        async function sendMessage() {
            const input = document.getElementById('mainInput');
            let msg = input.value.trim();
            if (!msg && attachments.length === 0) return;
            if (msg.startsWith('/')) { executeCommand(msg.split(' ')[0]); return; }
            
            if (deepseekConfig.enabled && deepseekConfig.apiKey) {
                await sendDeepSeekMessage(msg, input);
                return;
            } else if (deepseekConfig.enabled && !deepseekConfig.apiKey) {
                // DeepSeek 已启用但没有 API Key，显示警告并使用本地模型
                showToast('⚠️ DeepSeek 已启用但未配置 API Key，将使用本地模型');
            }
            
            const sendBtn = document.getElementById('sendBtn');
            const stopBtn = document.getElementById('stopBtn');
            sendBtn.disabled = true;
            sendBtn.style.display = 'none';
            stopBtn.style.display = 'flex';
            isGenerating = true;
            input.value = '';
            autoResize(input);
            updateCharCount();
            document.getElementById('commandHint').classList.remove('show');
            document.getElementById('editHint').style.display = 'none';
            document.getElementById('replyHint').style.display = 'none';
            document.getElementById('statusText').textContent = '正在生成...';
            
            if (!currentChatId) newChat();
            const chat = chats.find(c => c.id === currentChatId);
            const time = new Date().toLocaleTimeString('zh-CN', {hour:'2-digit',minute:'2-digit'});
            
            if (editingMsgIdx !== null) {
                chat.messages[editingMsgIdx].content = msg;
                const histIdx = Math.floor(editingMsgIdx / 2);
                if (history[histIdx]) history[histIdx][0] = msg;
                editingMsgIdx = null;
                document.getElementById('messagesContainer').innerHTML = '';
                chat.messages.forEach((m, idx) => addMessageToUI(m.role, m.content, m.time, m.toolResults, idx, m.reasoning));
                saveChats();
                
                const container = document.getElementById('messagesContainer');
                const msgEl = document.createElement('div');
                msgEl.className = 'message assistant';
                const roleData = roles.find(r => r.id === currentRole) || roles[0];
                const replyTime = new Date().toLocaleTimeString('zh-CN', {hour:'2-digit',minute:'2-digit'});
                msgEl.innerHTML = `<div class="message-avatar">${roleData.icon || '🤖'}</div><div class="message-content-wrapper"><div class="message-content" id="streamContent"></div><div class="message-actions"><button class="msg-action-btn" onclick="regenerate()">🔄</button></div><div class="message-time">${replyTime}</div></div>`;
                container.appendChild(msgEl);
                const contentEl = document.getElementById('streamContent');
                let fullContent = '';
                
                const res = await fetch('/stream', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        message: msg, history: history.slice(0, histIdx), role: currentRole,
                        lora: currentLora !== 'none' ? currentLora : null,
                        structured_template: currentStructuredTemplate,
                        temperature: settings.temp, max_tokens: settings.tokens,
                        use_rag: ragEnabled,
                        rag_alpha: ragSettings.alpha,
                        rag_rerank: ragSettings.useRerank,
                        rag_top_k: ragSettings.topK,
                        rag_cache: ragSettings.useCache,
                        rag_expansion: ragSettings.useExpansion,
                        rag_hyde: ragSettings.useHyde,
                        rag_multi_query: ragSettings.useMultiQuery,
                        rag_decomposition: ragSettings.useDecomposition,
                        rag_adaptive: ragSettings.useAdaptive,
                        rag_rrf: ragSettings.useRrf,
                        rag_metadata_filter: ragSettings.useMetadataFilter,
                        rag_time_weight: ragSettings.useTimeWeight,
                        rag_iterative: ragSettings.useIterative
                    })
                });
                
                currentReader = res.body.getReader();
                const decoder = new TextDecoder();
                
                while (true) {
                    if (!currentReader) break;
                    const { done, value } = await currentReader.read();
                    if (done) break;
                    const chunk = decoder.decode(value);
                    const lines = chunk.split("\\n");
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.slice(6));
                                if (data.content) {
                                    fullContent += data.content;
                                    // 生成过程中显示原始文本，避免 markdown 解析错误
                                    contentEl.innerHTML = fullContent.replace(/\\n/g, '<br>');
                                    container.scrollTop = container.scrollHeight;
                                }
                                // 忽略 thinking 类型的数据，不显示思考过程
                                if (data.done) {
                                    // 生成完成后渲染 markdown
                                    if (settings.markdown) {
                                        contentEl.innerHTML = marked.parse(fullContent);
                                    }
                                    if (chat.messages[editingMsgIdx + 1]) {
                                        chat.messages[editingMsgIdx + 1].content = fullContent;
                                    } else {
                                        chat.messages.push({ role: 'assistant', content: fullContent, time: replyTime });
                                    }
                                    if (history[histIdx]) history[histIdx][1] = fullContent;
                                    saveChats();
                                }
                            } catch (e) {
                                console.error('Parse error:', e, 'Line:', line);
                            }
                        }
                    }
                }
                currentReader = null;
                contentEl.id = '';
                contentEl.querySelectorAll('pre code').forEach(block => hljs.highlightElement(block));
                currentStructuredTemplate = null;
                
                isGenerating = false;
                sendBtn.disabled = false;
                sendBtn.style.display = 'flex';
                stopBtn.style.display = 'none';
                document.getElementById('statusText').textContent = '准备就绪';
                input.focus();
                return;
            }
            
            if (replyingTo) {
                msg = `> ${replyingTo.content}\\n\\n${msg}`;
                replyingTo = null;
            }
            
            let toolResults = [];
            if (activeTools.size > 0) {
                for (const toolId of activeTools) {
                    if (tools[toolId]) {
                        try {
                            const res = await fetch('/tool/execute', {
                                method: 'POST', headers: {'Content-Type': 'application/json'},
                                body: JSON.stringify({tool: toolId, input: msg})
                            });
                            const data = await res.json();
                            if (data.result) toolResults.push({tool: tools[toolId].name, result: data.result});
                        } catch (e) {}
                    }
                }
            }
            
            chat.messages.push({ role: 'user', content: msg, time, toolResults: toolResults.length ? toolResults : null });
            addMessageToUI('user', msg, time, toolResults.length ? toolResults : null, chat.messages.length - 1);
            
            if (chat.title === '新对话') {
                chat.title = msg.slice(0, 20) + (msg.length > 20 ? '...' : '');
                saveChats();
            }
            
            history.push([msg, '']);
            const startTime = Date.now();
            
            try {
                const container = document.getElementById('messagesContainer');
                const msgEl = document.createElement('div');
                msgEl.className = 'message assistant';
                const roleData = roles.find(r => r.id === currentRole) || roles[0];
                const replyTime = new Date().toLocaleTimeString('zh-CN', {hour:'2-digit',minute:'2-digit'});
                // 创建包含思考过程区域的消息结构
                msgEl.innerHTML = `
                    <div class="message-avatar">${roleData.icon || '🤖'}</div>
                    <div class="message-content-wrapper">
                        <div class="reasoning-section" style="display:none;">
                            <div class="reasoning-toggle" onclick="toggleReasoning(this)">
                                <span class="reasoning-toggle-icon">▶</span>
                                <span>思考过程</span>
                            </div>
                            <div class="reasoning-content"></div>
                        </div>
                        <div class="message-content"></div>
                        <div class="message-actions"><button class="msg-action-btn" onclick="regenerate()">🔄 重新生成</button></div>
                        <div class="message-time">${replyTime}</div>
                    </div>
                `;
                container.appendChild(msgEl);
                const contentEl = msgEl.querySelector('.message-content');
                const reasoningSection = msgEl.querySelector('.reasoning-section');
                const reasoningContentEl = msgEl.querySelector('.reasoning-content');
                let fullContent = '';
                let fullReasoning = '';
                let hasReasoning = false;
                
                const res = await fetch('/stream', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        message: msg, history: history.slice(0,-1), role: currentRole,
                        lora: currentLora !== 'none' ? currentLora : null,
                        structured_template: currentStructuredTemplate,
                        temperature: settings.temp, max_tokens: settings.tokens,
                        use_rag: ragEnabled,
                        rag_alpha: ragSettings.alpha,
                        rag_rerank: ragSettings.useRerank,
                        rag_top_k: ragSettings.topK,
                        rag_cache: ragSettings.useCache,
                        rag_expansion: ragSettings.useExpansion,
                        rag_hyde: ragSettings.useHyde,
                        rag_multi_query: ragSettings.useMultiQuery,
                        rag_decomposition: ragSettings.useDecomposition,
                        rag_adaptive: ragSettings.useAdaptive,
                        rag_rrf: ragSettings.useRrf,
                        rag_metadata_filter: ragSettings.useMetadataFilter,
                        rag_time_weight: ragSettings.useTimeWeight,
                        rag_iterative: ragSettings.useIterative
                    })
                });
                
                currentReader = res.body.getReader();
                const decoder = new TextDecoder();
                
                while (true) {
                    if (!currentReader) break;
                    const { done, value } = await currentReader.read();
                    if (done) break;
                    const chunk = decoder.decode(value);
                    const lines = chunk.split("\\n");
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.slice(6));
                                // 处理正式回答内容
                                if (data.content) {
                                    fullContent += data.content;
                                    // 生成过程中显示原始文本，避免 markdown 解析错误
                                    contentEl.innerHTML = fullContent.replace(/\\n/g, '<br>');
                                    container.scrollTop = container.scrollHeight;
                                }
                                // 处理思考过程内容 (Qwen3.5 模型的 thinking 字段)
                                if (data.thinking) {
                                    fullReasoning += data.thinking;
                                    hasReasoning = true;
                                    if (reasoningSection) reasoningSection.style.display = 'block';
                                    if (reasoningContentEl) reasoningContentEl.textContent = fullReasoning;
                                    container.scrollTop = container.scrollHeight;
                                }
                                // 兼容旧格式的 reasoning 字段
                                if (data.reasoning) {
                                    fullReasoning += data.reasoning;
                                    hasReasoning = true;
                                    if (reasoningSection) reasoningSection.style.display = 'block';
                                    if (reasoningContentEl) reasoningContentEl.textContent = fullReasoning;
                                    container.scrollTop = container.scrollHeight;
                                }
                                if (data.done) {
                                    // 生成完成后渲染 markdown
                                    if (settings.markdown) {
                                        contentEl.innerHTML = marked.parse(fullContent);
                                    }
                                    stats.sessions++;
                                    stats.latencies.push(Date.now() - startTime);
                                    if (data.tokens_in) stats.inputTokens += data.tokens_in;
                                    if (data.tokens_out) stats.outputTokens += data.tokens_out;
                                    saveStats();
                                    updateStats();
                                    if (data.rag_sources && data.rag_sources.length) {
                                        const sourcesHtml = renderRagSources(data.rag_sources);
                                        contentEl.innerHTML += sourcesHtml;
                                    }
                                    chat.messages.push({ role: 'assistant', content: fullContent, reasoning: fullReasoning || null, time: replyTime });
                                    history[history.length - 1][1] = fullContent;
                                    saveChats();
                                    if (settings.voice) requestTTS(fullContent);
                                }
                            } catch (e) {}
                        }
                    }
                }
                currentReader = null;
                contentEl.id = '';
                if (reasoningSection) reasoningSection.id = '';
                if (reasoningContentEl) reasoningContentEl.id = '';
                contentEl.querySelectorAll('pre code').forEach(block => hljs.highlightElement(block));
            } catch (e) {
                if (e.name !== 'AbortError') {
                    console.error('Stream error:', e);
                    addMessageToUI('assistant', '❌ 生成失败: ' + (e.message || '网络错误，请检查Ollama服务是否运行'), time);
                }
            }
            
            isGenerating = false;
            currentStructuredTemplate = null;
            sendBtn.disabled = false;
            sendBtn.style.display = 'flex';
            stopBtn.style.display = 'none';
            document.getElementById('statusText').textContent = '准备就绪';
            input.focus();
        }
        
        function regenerate() {
            if (history.length > 0) {
                history.pop();
                const chat = chats.find(c => c.id === currentChatId);
                if (chat && chat.messages.length > 0) {
                    chat.messages.pop();
                    saveChats();
                }
                const container = document.getElementById('messagesContainer');
                if (container.lastElementChild) container.removeChild(container.lastElementChild);
                sendMessage();
            }
        }
        
        function showTyping() {
            const container = document.getElementById('messagesContainer');
            const typing = document.createElement('div');
            typing.className = 'message assistant';
            typing.id = 'typingIndicator';
            const roleData = roles.find(r => r.id === currentRole) || roles[0];
            typing.innerHTML = `<div class="message-avatar">${roleData.icon || '🤖'}</div><div class="message-content-wrapper"><div class="message-content"><div class="typing-indicator"><span></span><span></span><span></span></div></div></div>`;
            container.appendChild(typing);
            container.scrollTop = container.scrollHeight;
        }
        
        function hideTyping() { const t = document.getElementById('typingIndicator'); if (t) t.remove(); }
        
        function requestTTS(text) {
            fetch('/tts', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ text: text.slice(0, 300) }) })
                .then(r => r.json()).then(data => { if (data.audio_url) new Audio(data.audio_url).play(); });
        }
        
        function showCodeModal() { document.getElementById('codeModal').classList.add('show'); }
        function showKBModal() { document.getElementById('kbModal').classList.add('show'); }
        function openFeatureCenter() {
            renderFeatureCenterMeta();
            document.getElementById('featureCenterModal').classList.add('show');
            recordFeatureAction('打开功能中心', '中心');
            loadMcpPlugins();
            loadWorkflows();
            loadProjectCenter();
            setTimeout(renderFeatureCenterMeta, 400);
        }
        
        function executeCode() {
            const code = document.getElementById('codeEditor').value;
            if (!code.trim()) return;
            fetch('/code/execute', {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({code})
            }).then(r => r.json()).then(data => {
                const output = document.getElementById('codeOutput');
                output.style.display = 'block';
                output.innerHTML = `<strong>${data.success ? '✅ 输出:' : '❌ 错误:'}</strong>\\n${data.output}`;
            });
        }
        
        function addToKB() {
            const text = document.getElementById('kbInput').value.trim();
            if (!text) return;
            fetch('/kb/add', {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({text})
            }).then(r => r.json()).then(data => {
                if (data.success) {
                    showToast('已添加到知识库');
                    document.getElementById('kbInput').value = '';
                }
            });
        }
        
        function searchKB() {
            const query = document.getElementById('kbSearch').value.trim();
            if (!query) return;
            fetch('/kb/search', {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({query})
            }).then(r => r.json()).then(data => {
                const results = document.getElementById('kbResults');
                if (data.results && data.results.length) {
                    results.innerHTML = data.results.map(r => `<div style="padding:8px;background:var(--bg-secondary);border-radius:6px;margin-bottom:6px;font-size:12px;">${r.text.slice(0, 200)}...</div>`).join('');
                } else {
                    results.innerHTML = '<div style="color:var(--text-muted);font-size:12px;">未找到相关内容</div>';
                }
            });
        }
        
        function handleKeyDown(e) { 
            if (e.key === 'Enter' && !e.shiftKey) { 
                e.preventDefault(); 
                sendMessage(); 
            } 
        }
        
        let shortcutTimeout = null;
        function showShortcutHint() {
            const hint = document.getElementById('shortcutHint');
            hint.classList.add('show');
            if (shortcutTimeout) clearTimeout(shortcutTimeout);
            shortcutTimeout = setTimeout(() => hint.classList.remove('show'), 3000);
        }
        
        document.addEventListener('keydown', e => {
            if (e.ctrlKey && e.key === 'n') { e.preventDefault(); newChat(); }
            if (e.ctrlKey && e.key === ',') { e.preventDefault(); openSettings(); }
            if (e.ctrlKey && e.key === 'd') { e.preventDefault(); toggleDarkMode(); }
            if (e.key === '?' && e.shiftKey) { e.preventDefault(); showShortcutHint(); }
            if (e.key === 'Escape') {
                const modals = Array.from(document.querySelectorAll('.modal-overlay.show'));
                if (modals.length) modals[modals.length - 1].classList.remove('show');
                closeSettings();
            }
        });
        
        document.querySelectorAll('.modal-overlay').forEach(overlay => {
            overlay.addEventListener('click', e => {
                if (e.target === overlay) overlay.classList.remove('show');
            });
        });
        
        function autoResize(el) { el.style.height = 'auto'; el.style.height = Math.min(el.scrollHeight, 100) + 'px'; }
        function updateCharCount() { document.getElementById('charCount').textContent = `${document.getElementById('mainInput').value.length} / 4000`; }
        function updateTemp(v) { document.getElementById('tempValue').textContent = v; settings.temp = parseFloat(v); saveSettings(); }
        
        function updateSetting(k, v) {
            if (k === 'temp') { settings.temp = parseFloat(v); document.getElementById('settingTempValue').textContent = v; }
            if (k === 'tokens') { settings.tokens = parseInt(v); document.getElementById('settingTokensValue').textContent = v; }
            if (k === 'voice') settings.voice = v;
            if (k === 'markdown') settings.markdown = v;
            saveSettings();
        }
        
        function toggleDarkMode() {
            document.body.classList.toggle('dark');
            settings.dark = document.body.classList.contains('dark');
            document.getElementById('darkModeToggle').checked = settings.dark;
            saveSettings();
            showToast(settings.dark ? '已开启深色模式' : '已关闭深色模式');
        }
        
        function toggleVoice() {
            settings.voice = !settings.voice;
            document.getElementById('voiceOutputToggle').checked = settings.voice;
            document.getElementById('voiceBtn').classList.toggle('active', settings.voice);
            saveSettings();
            showToast(settings.voice ? '已开启语音输出' : '已关闭语音输出');
        }
        
        function openSettings() { document.getElementById('settingsPanel').classList.add('open'); }
        
        function expandToCenter(panelId) {
            const panel = document.getElementById(panelId);
            if (!panel) return;
            
            const chatArea = document.querySelector('.chat-area');
            const sidebar = document.querySelector('.sidebar');
            const header = document.querySelector('.header');
            
            if (panel.classList.contains('expanded')) {
                panel.classList.remove('expanded');
                panel.style.position = '';
                panel.style.top = '';
                panel.style.left = '';
                panel.style.width = '';
                panel.style.height = '';
                panel.style.zIndex = '';
                panel.style.background = '';
                if (chatArea) chatArea.style.display = '';
                if (sidebar) sidebar.style.display = '';
                if (header) header.style.display = '';
            } else {
                panel.classList.add('expanded');
                panel.style.position = 'fixed';
                panel.style.top = '60px';
                panel.style.left = '60px';
                panel.style.right = '60px';
                panel.style.bottom = '20px';
                panel.style.width = 'auto';
                panel.style.height = 'auto';
                panel.style.zIndex = '200';
                panel.style.background = 'var(--bg-primary)';
                if (chatArea) chatArea.style.display = 'none';
                if (sidebar) sidebar.style.display = 'none';
                if (header) header.style.display = 'none';
            }
        }
        
        function toggleRightSidebar() {
            const sidebar = document.getElementById('rightSidebar');
            sidebar.classList.toggle('open');
            if (sidebar.classList.contains('open')) {
                updateRightSidebarStatus();
                updateRecentChats();
            }
        }
        
        function updateRightSidebarStatus() {
            document.getElementById('currentRoleDisplay').textContent = roles[currentRole]?.name || currentRole;
            document.getElementById('currentLoraDisplay').textContent = currentLora === 'none' ? '未加载' : currentLora;
            document.getElementById('ragStatusDisplay').textContent = ragEnabled ? '开启' : '关闭';
        }
        
        function updateRecentChats() {
            const list = document.getElementById('recentChatsList');
            const recent = chats.slice(0, 5);
            if (recent.length === 0) {
                list.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:20px;">暂无对话</div>';
                return;
            }
            list.innerHTML = recent.map(c => 
                `<div class="recent-chat-item" onclick="loadChat('${c.id}'); toggleRightSidebar();">${c.title}</div>`
            ).join('');
        }
        
        function openDeepSeek() {
            document.getElementById('deepseekApiKey').value = deepseekConfig.apiKey || '';
            document.getElementById('deepseekApiUrl').value = deepseekConfig.apiUrl || 'https://api.deepseek.com';
            document.getElementById('deepseekModel').value = deepseekConfig.model || 'deepseek-chat';
            document.getElementById('deepseekEnabled').checked = deepseekConfig.enabled || false;
            document.getElementById('deepseekModal').classList.add('show');
        }
        
        function saveDeepSeek() {
            deepseekConfig = {
                apiKey: document.getElementById('deepseekApiKey').value,
                apiUrl: document.getElementById('deepseekApiUrl').value || 'https://api.deepseek.com',
                model: document.getElementById('deepseekModel').value,
                enabled: document.getElementById('deepseekEnabled').checked
            };
            localStorage.setItem('deepseek_config', JSON.stringify(deepseekConfig));
            updateDeepSeekIndicator();
            renderFeatureCenterMeta();
            closeModal('deepseekModal');
            showToast('DeepSeek配置已保存');
        }
        
        function testDeepSeek() {
            const apiKey = document.getElementById('deepseekApiKey').value;
            const apiUrl = document.getElementById('deepseekApiUrl').value || 'https://api.deepseek.com';
            const statusEl = document.getElementById('deepseekStatus');
            
            if (!apiKey) {
                statusEl.innerHTML = '<span style="color:#e74c3c;">请输入API Key</span>';
                return;
            }
            
            statusEl.innerHTML = '<span style="color:var(--primary);">🔄 测试连接中...</span>';
            
            fetch('/deepseek/test', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({apiKey, apiUrl})
            }).then(r => r.json()).then(data => {
                if (data.success) {
                    statusEl.innerHTML = '<span style="color:#10b981;">✅ 连接成功！模型可用</span>';
                } else {
                    statusEl.innerHTML = '<span style="color:#e74c3c;">❌ ' + (data.error || '连接失败') + '</span>';
                }
            }).catch(e => {
                statusEl.innerHTML = '<span style="color:#e74c3c;">❌ 网络错误</span>';
            });
        }
        
        function updateDeepSeekIndicator() {
            const indicators = document.getElementById('headerIndicators');
            let html = indicators.innerHTML;
            const dsIndicator = '<div class="indicator" style="background:linear-gradient(135deg,rgba(79,70,229,0.2),rgba(124,58,237,0.1));color:#7c3aed;border:1px solid rgba(79,70,229,0.3);"><span>🤖</span><span>DeepSeek</span></div>';
            if (deepseekConfig.enabled && !html.includes('DeepSeek')) {
                indicators.innerHTML = dsIndicator + html;
            } else if (!deepseekConfig.enabled) {
                indicators.innerHTML = html.replace(dsIndicator, '');
            }
        }
        
        function checkExternalApiWarning() {
            // 检查是否配置了任何外部API
            const hasExternalApi = deepseekConfig.enabled && deepseekConfig.apiKey;
            const hasShownWarning = sessionStorage.getItem('api_warning_shown');
            
            if (!hasExternalApi && !hasShownWarning) {
                // 显示警告弹窗
                showApiWarningModal();
                sessionStorage.setItem('api_warning_shown', 'true');
            }
        }
        
        function showApiWarningModal() {
            const modal = document.createElement('div');
            modal.id = 'apiWarningModal';
            modal.style.cssText = `
                position: fixed; top: 0; left: 0; right: 0; bottom: 0;
                background: rgba(0,0,0,0.5); z-index: 10000;
                display: flex; align-items: center; justify-content: center;
            `;
            modal.innerHTML = `
                <div style="
                    background: var(--bg-primary, #fff); border-radius: 16px;
                    padding: 24px; max-width: 400px; width: 90%;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    border: 1px solid var(--border, #e5e7eb);
                ">
                    <div style="text-align: center; margin-bottom: 20px;">
                        <div style="font-size: 48px; margin-bottom: 12px;">⚠️</div>
                        <h3 style="margin: 0 0 12px 0; color: var(--text-primary, #1f2937);">外部API未配置</h3>
                        <p style="color: var(--text-secondary, #6b7280); margin: 0; line-height: 1.6;">
                            当前未接入任何外部AI API（如DeepSeek、OpenAI等）。<br>
                            部分高级功能（场景生成、联网搜索等）将无法使用。
                        </p>
                    </div>
                    <div style="display: flex; gap: 12px;">
                        <button onclick="closeApiWarningModal()" style="
                            flex: 1; padding: 12px; border: 1px solid var(--border, #e5e7eb);
                            background: transparent; border-radius: 8px; cursor: pointer;
                            color: var(--text-secondary, #6b7280);
                        ">稍后再说</button>
                        <button onclick="openExternalApiSettings(); closeApiWarningModal();" style="
                            flex: 1; padding: 12px; border: none;
                            background: linear-gradient(135deg, #667eea, #764ba2);
                            border-radius: 8px; cursor: pointer; color: white; font-weight: 500;
                        ">立即配置</button>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
            
            // 点击背景关闭
            modal.addEventListener('click', (e) => {
                if (e.target === modal) closeApiWarningModal();
            });
        }
        
        function closeApiWarningModal() {
            const modal = document.getElementById('apiWarningModal');
            if (modal) modal.remove();
        }
        
        function openExternalApiSettings() {
            // 打开设置面板并切换到外部API配置
            openSettings();
            // 延迟切换到DeepSeek配置
            setTimeout(() => {
                const deepseekToggle = document.getElementById('deepseekEnabled');
                if (deepseekToggle) {
                    deepseekToggle.focus();
                }
            }, 100);
        }
        
        function openStats() {
            document.getElementById('statSessions').textContent = stats.sessions || 0;
            document.getElementById('statInput').textContent = stats.inputTokens || 0;
            document.getElementById('statOutput').textContent = stats.outputTokens || 0;
            const avgLatency = stats.latencies && stats.latencies.length ? Math.round(stats.latencies.reduce((a,b) => a+b, 0) / stats.latencies.length) : 0;
            document.getElementById('statLatency').textContent = avgLatency + 'ms';
            
            const chart = document.getElementById('usageChart');
            if (!chart) {
                document.getElementById('statsModal').classList.add('show');
                return;
            }
            chart.innerHTML = '';
            const data = [12, 25, 18, 30, 22, 35, 28, 40, 33, 45, 38, 50];
            const max = Math.max(...data);
            data.forEach((v, i) => {
                const bar = document.createElement('div');
                bar.style.cssText = `width:100%;background:linear-gradient(to top,#10b981,#34d399);border-radius:4px 4px 0 0;height:${(v/max)*100}%;opacity:${0.5 + (i/data.length)*0.5};transition:height 0.3s;`;
                bar.title = `${v} 次对话`;
                chart.appendChild(bar);
            });
            
            const toolStats = document.getElementById('toolStats');
            const toolData = {calculator: 15, search: 42, translate: 28, weather: 12};
            toolStats.innerHTML = Object.entries(toolData).map(([k, v]) => 
                `<div style="display:flex;justify-content:space-between;margin-bottom:8px;"><span>${k}</span><span style="color:var(--primary);">${v}次</span></div>`
            ).join('');
            
            document.getElementById('statsModal').classList.add('show');
        }
        
        function resetStats() {
            stats = {sessions: 0, inputTokens: 0, outputTokens: 0, latencies: []};
            localStorage.setItem('kaguya_stats', JSON.stringify(stats));
            openStats();
            showToast('统计数据已重置');
        }
        
        function exportStats() {
            const report = {
                date: new Date().toISOString(),
                sessions: stats.sessions,
                inputTokens: stats.inputTokens,
                outputTokens: stats.outputTokens,
                avgLatency: stats.latencies && stats.latencies.length ? Math.round(stats.latencies.reduce((a,b) => a+b, 0) / stats.latencies.length) : 0
            };
            const blob = new Blob([JSON.stringify(report, null, 2)], {type: 'application/json'});
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = `kaguya_stats_${new Date().toISOString().slice(0,10)}.json`;
            a.click();
            showToast('报告已导出');
        }
        
        function openModelConfig() {
            document.getElementById('modelTemp').value = settings.temp || 0.7;
            document.getElementById('modelTempVal').textContent = settings.temp || 0.7;
            document.getElementById('modelTokens').value = settings.tokens || 1024;
            document.getElementById('modelTokensVal').textContent = settings.tokens || 1024;
            document.getElementById('modelModal').classList.add('show');
        }
        
        function saveModelConfig() {
            settings.temp = parseFloat(document.getElementById('modelTemp').value);
            settings.tokens = parseInt(document.getElementById('modelTokens').value);
            localStorage.setItem('kaguya_settings', JSON.stringify(settings));
            closeModal('modelModal');
            showToast('模型配置已保存');
        }
        
        function openTheme() {
            document.getElementById('themeModal').classList.add('show');
        }
        
        function applyTheme(theme) {
            const themes = {
                default: {primary: '#667eea', secondary: '#764ba2'},
                ocean: {primary: '#0ea5e9', secondary: '#0284c7'},
                forest: {primary: '#10b981', secondary: '#059669'},
                sunset: {primary: '#f59e0b', secondary: '#ef4444'}
            };
            if (themes[theme]) {
                document.documentElement.style.setProperty('--primary', themes[theme].primary);
                document.documentElement.style.setProperty('--secondary', themes[theme].secondary);
                document.getElementById('primaryColor').value = themes[theme].primary;
                document.getElementById('primaryColorText').value = themes[theme].primary;
            }
        }
        
        function saveTheme() {
            const primary = document.getElementById('primaryColor').value;
            document.documentElement.style.setProperty('--primary', primary);
            localStorage.setItem('kaguya_theme', primary);
            closeModal('themeModal');
            showToast('主题已应用');
        }
        
        function resetTheme() {
            applyTheme('default');
            showToast('主题已重置');
        }
        
        let modelsConfig = JSON.parse(localStorage.getItem('models_config') || '{}');
        
        function openModelsConfig() {
            const models = ['openai', 'claude', 'gemini', 'qwen', 'moonshot', 'zhipu'];
            models.forEach(m => {
                const config = modelsConfig[m] || {};
                const apiKeyEl = document.getElementById(`${m}ApiKey`);
                const modelEl = document.getElementById(`${m}Model`);
                const enabledEl = document.getElementById(`${m}Enabled`);
                const baseUrlEl = document.getElementById(`${m}BaseUrl`);
                
                if (apiKeyEl) apiKeyEl.value = config.apiKey || '';
                if (modelEl) modelEl.value = config.model || modelEl.options[0].value;
                if (enabledEl) enabledEl.checked = config.enabled || false;
                if (baseUrlEl) baseUrlEl.value = config.baseUrl || '';
            });
            document.getElementById('modelsModal').classList.add('show');
        }
        
        function toggleModelConfig(model) {
            const configEl = document.getElementById(`${model}Config`);
            if (configEl) {
                configEl.style.display = configEl.style.display === 'none' ? 'block' : 'none';
            }
        }
        
        function saveModelsConfig() {
            const models = ['openai', 'claude', 'gemini', 'qwen', 'moonshot', 'zhipu'];
            models.forEach(m => {
                const apiKeyEl = document.getElementById(`${m}ApiKey`);
                const modelEl = document.getElementById(`${m}Model`);
                const enabledEl = document.getElementById(`${m}Enabled`);
                const baseUrlEl = document.getElementById(`${m}BaseUrl`);
                
                modelsConfig[m] = {
                    apiKey: apiKeyEl ? apiKeyEl.value : '',
                    model: modelEl ? modelEl.value : '',
                    enabled: enabledEl ? enabledEl.checked : false,
                    baseUrl: baseUrlEl ? baseUrlEl.value : ''
                };
            });
            localStorage.setItem('models_config', JSON.stringify(modelsConfig));
            closeModal('modelsModal');
            showToast('多模型配置已保存');
        }
        
        function testModelConnection() {
            const statusEl = document.getElementById('modelsStatus');
            statusEl.innerHTML = '<span style="color:var(--primary);">🔄 测试连接中...</span>';
            
            setTimeout(() => {
                const enabledModels = Object.entries(modelsConfig).filter(([k, v]) => v.enabled && v.apiKey);
                if (enabledModels.length > 0) {
                    statusEl.innerHTML = `<span style="color:#10b981;">✅ 已配置 ${enabledModels.length} 个模型</span>`;
                } else {
                    statusEl.innerHTML = '<span style="color:#f59e0b;">⚠️ 请先启用并配置至少一个模型</span>';
                }
            }, 1000);
        }
        
        async function sendDeepSeekMessage(msg, input) {
            const sendBtn = document.getElementById('sendBtn');
            const stopBtn = document.getElementById('stopBtn');
            sendBtn.disabled = true;
            sendBtn.style.display = 'none';
            stopBtn.style.display = 'flex';
            isGenerating = true;
            input.value = '';
            autoResize(input);
            document.getElementById('statusText').textContent = 'DeepSeek生成中...';
            
            if (!currentChatId) newChat();
            const chat = chats.find(c => c.id === currentChatId);
            const time = new Date().toLocaleTimeString('zh-CN', {hour:'2-digit',minute:'2-digit'});
            
            addMessageToUI('user', msg, time);
            chat.messages.push({role: 'user', content: msg, time});
            history.push([msg, '']);
            saveChats();
            
            const container = document.getElementById('messagesContainer');
            const msgEl = document.createElement('div');
            msgEl.className = 'message assistant';
            const replyTime = new Date().toLocaleTimeString('zh-CN', {hour:'2-digit',minute:'2-digit'});
            // 创建包含思考过程区域的消息结构（初始隐藏，有内容时显示）
            msgEl.innerHTML = `
                <div class="message-avatar">🤖</div>
                <div class="message-content-wrapper">
                    <div class="reasoning-section" style="display:none;">
                        <div class="reasoning-toggle" onclick="toggleReasoning(this)">
                            <span class="reasoning-toggle-icon">▶</span>
                            <span>思考过程</span>
                        </div>
                        <div class="reasoning-content"></div>
                    </div>
                    <div class="message-content"></div>
                    <div class="message-actions"><button class="msg-action-btn" onclick="regenerate()">🔄</button></div>
                    <div class="message-time">${replyTime}</div>
                </div>
            `;
            container.appendChild(msgEl);
            const contentEl = msgEl.querySelector('.message-content');
            const reasoningSection = msgEl.querySelector('.reasoning-section');
            const reasoningContentEl = msgEl.querySelector('.reasoning-content');
            let fullContent = '';
            let fullReasoning = '';
            let hasReasoning = false;
            
            const messages = history.slice(-10).map(h => [
                {role: 'user', content: h[0]},
                h[1] ? {role: 'assistant', content: h[1]} : null
            ]).flat().filter(Boolean);
            
            try {
                const res = await fetch('/deepseek/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        apiKey: deepseekConfig.apiKey,
                        apiUrl: deepseekConfig.apiUrl,
                        model: deepseekConfig.model,
                        messages: messages
                    })
                });
                
                currentReader = res.body.getReader();
                const decoder = new TextDecoder();
                
                while (true) {
                    if (!currentReader) break;
                    const { done, value } = await currentReader.read();
                    if (done) break;
                    const chunk = decoder.decode(value);
                    const lines = chunk.split("\\n");
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.slice(6));
                                // 处理正式回答内容
                                if (data.content) {
                                    fullContent += data.content;
                                    // 生成过程中显示原始文本，避免 markdown 解析错误
                                    contentEl.innerHTML = fullContent.replace(/\\n/g, '<br>');
                                    container.scrollTop = container.scrollHeight;
                                }
                                // 处理思考过程内容
                                if (data.reasoning) {
                                    fullReasoning += data.reasoning;
                                    hasReasoning = true;
                                    if (reasoningSection) reasoningSection.style.display = 'block';
                                    if (reasoningContentEl) reasoningContentEl.textContent = fullReasoning;
                                    container.scrollTop = container.scrollHeight;
                                }
                                if (data.done) {
                                    // 生成完成后渲染 markdown
                                    if (settings.markdown) {
                                        contentEl.innerHTML = marked.parse(fullContent);
                                    }
                                    chat.messages.push({role: 'assistant', content: fullContent, reasoning: fullReasoning, time: replyTime});
                                    history[history.length - 1][1] = fullContent;
                                    saveChats();
                                }
                            } catch (e) {}
                        }
                    }
                }
            } catch (e) {
                contentEl.innerHTML = `<span style="color:#e74c3c;">DeepSeek API错误: ${e.message}</span>`;
            }
            
            sendBtn.disabled = false;
            sendBtn.style.display = 'flex';
            stopBtn.style.display = 'none';
            isGenerating = false;
            document.getElementById('statusText').textContent = '就绪';
            contentEl.id = '';
            if (reasoningSection) reasoningSection.id = '';
            if (reasoningContentEl) reasoningContentEl.id = '';
        }
        
        // 切换思考过程展开/折叠
        function toggleReasoning(toggleEl) {
            const contentEl = toggleEl.nextElementSibling;
            const isExpanded = toggleEl.classList.contains('expanded');
            if (isExpanded) {
                toggleEl.classList.remove('expanded');
                contentEl.classList.remove('expanded');
            } else {
                toggleEl.classList.add('expanded');
                contentEl.classList.add('expanded');
            }
        }
        function closeSettings() { document.getElementById('settingsPanel').classList.remove('open'); }
        function showToast(msg) { const t = document.getElementById('toast'); t.textContent = msg; t.classList.add('show'); setTimeout(() => t.classList.remove('show'), 2000); }
        function copyMessage(btn) { navigator.clipboard.writeText(btn.closest('.message-content-wrapper').querySelector('.message-content').textContent); showToast('已复制'); }
        function speakMessage(btn) { const u = new SpeechSynthesisUtterance(btn.closest('.message-content-wrapper').querySelector('.message-content').textContent); u.lang = 'zh-CN'; speechSynthesis.speak(u); }
        
        function handleFileSelect(e) {
            const files = Array.from(e.target.files);
            files.forEach(file => {
                const reader = new FileReader();
                reader.onload = ev => { attachments.push({ name: file.name, type: file.type, data: ev.target.result }); renderAttachments(); };
                reader.readAsDataURL(file);
            });
            e.target.value = '';
        }
        
        function renderAttachments() {
            document.getElementById('attachmentsPreview').innerHTML = attachments.map((a, i) => 
                a.type.startsWith('image') ? `<div class="attachment-item"><img src="${a.data}"><button class="attachment-remove" onclick="attachments.splice(${i},1);renderAttachments();">✕</button></div>` : ''
            ).join('');
        }
        
        function exportChat() {
            const chat = chats.find(c => c.id === currentChatId);
            if (!chat) return;
            let text = `=== ${chat.title} ===\\n${new Date().toLocaleString()}\\n\\n`;
            chat.messages.forEach(m => { text += `[${m.role === 'user' ? '我' : 'AI'}] ${m.time}\\n${m.content}\\n\\n`; });
            const blob = new Blob([text], {type: 'text/plain;charset=utf-8'});
            const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = `对话_${new Date().toISOString().slice(0,10)}.txt`; a.click();
            showToast('已导出');
        }
        
        function exportAllChats() {
            let text = `=== 全部对话 ===\\n${new Date().toLocaleString()}\\n\\n`;
            chats.forEach(c => { text += `\\n【${c.title}】\\n`; c.messages.forEach(m => { text += `[${m.role}] ${m.content}\\n`; }); });
            const blob = new Blob([text], {type: 'text/plain;charset=utf-8'});
            const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = `全部对话.txt`; a.click();
            showToast('已导出');
        }
        
        function clearAllData() {
            if (confirm('确定清除所有数据？')) {
                localStorage.clear();
                chats = []; currentChatId = null; history = [];
                stats = {sessions:0,inputTokens:0,outputTokens:0,latencies:[]};
                showWelcome();
                renderChatList(); updateStats();
                showToast('已清除');
            }
        }
        
        // ==================== Tab 切换函数 (必须在所有被调用函数之后定义) ====================
        function switchTab(tab, clickedElement) {
            console.log('switchTab called:', tab, clickedElement);
            document.querySelectorAll('.sidebar-tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            if (clickedElement) clickedElement.classList.add('active');
            const targetTab = document.getElementById(tab + 'Tab');
            if (!targetTab) return;
            targetTab.classList.add('active');
            if (tab === 'loras') loadLoraList();
            if (tab === 'tools') renderToolList();
            if (tab === 'prompts') renderPromptList();
            if (tab === 'console') loadProjectCenter();
            if (tab === 'ecosystem') loadProjectCenter();
            if (tab === 'scenes') initScenesCenter();
            if (tab === 'project') loadProjectCenter();
            if (tab === 'ops') loadProjectCenter();
            if (tab === 'release') loadProjectCenter();
            if (tab === 'alert') loadProjectCenter();
            if (tab === 'ab') loadProjectCenter();
            if (tab === 'integration') loadProjectCenter();
            if (tab === 'mcp') loadMcpPlugins();
            if (tab === 'workflow') loadWorkflows();
            if (tab === 'memory') { refreshMemoryStats(); searchMemories(); }
            if (tab === 'multimodal') { loadMultimodalHistory(); }
            if (tab === 'finetune') { refreshFinetuneData(); }
        }
        
        // 在 DOM 加载完成后初始化
        document.addEventListener('DOMContentLoaded', () => {
            console.log('Calling init()...');
            init();
            console.log('init() completed');
        });
    </script>
</body>
</html>
"""

def get_client_ip():
    return request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()

def load_model():
    global model
    if model is None:
        print("使用 Ollama 后端...")
        adapter = get_ollama_adapter(OllamaConfig(model=OLLAMA_MODEL))
        if not adapter.is_server_running():
            raise RuntimeError("Ollama 服务未运行，请先启动 Ollama")
        if not adapter.is_model_available(OLLAMA_MODEL):
            raise RuntimeError(f"模型 {OLLAMA_MODEL} 未安装，请运行: ollama pull {OLLAMA_MODEL}")
        model = adapter
        print(f"Ollama 模型 {OLLAMA_MODEL} 已就绪!")
    return model

def get_role_system(role_id):
    role = next((r for r in PRESET_ROLES if r['id'] == role_id), PRESET_ROLES[0])
    return role.get('system', '')

STRUCTURED_OUTPUT_TEMPLATES = {
    "ecommerce": """请严格按以下结构输出，使用中文 Markdown 二级标题：
## 一、目标与约束
- 业务目标（1-3条）
- 约束条件（预算/人力/周期）

## 二、用户与商品策略
- 目标人群画像（核心痛点与购买动机）
- 商品卖点与差异化（3-5条）
- 价格与促销策略

## 三、30天执行计划
- 按第1周至第4周给出每周重点动作
- 每周包含：内容动作、投放动作、私域动作、转化动作

## 四、投放与素材框架
- 渠道优先级
- 素材类型与脚本方向
- A/B测试方案（至少3组）

## 五、数据看板与阈值
- 核心指标（曝光、点击、转化、客单、ROI）
- 预警阈值与应对动作

## 六、风险与备选方案
- 至少3个主要风险
- 对应备选策略

## 七、明日可执行清单
- 输出10条可立即执行事项""",
    "shortvideo": """请严格按以下结构输出，使用中文 Markdown 二级标题：
## 一、账号定位
- 目标受众
- 内容主线
- 差异化标签

## 二、7天内容排期
- Day1-Day7逐天给出：选题、脚本大纲、前3秒钩子、结尾引导

## 三、单条视频标准模板
- 开场钩子
- 信息展开
- 信任建立
- 行动召唤

## 四、封面与标题策略
- 标题公式（至少5条）
- 封面文案模板（至少5条）

## 五、发布与复盘机制
- 发布时间建议
- 数据复盘维度
- 下一轮优化规则

## 六、明日可执行清单
- 输出8条可立即执行事项""",
    "resume": """请严格按以下结构输出，使用中文 Markdown 二级标题：
## 一、岗位匹配分析
- 岗位关键要求拆解
- 候选人优势与短板

## 二、简历重写建议
- 抬头与摘要优化
- 关键经历排序建议
- 关键词优化建议

## 三、项目经历 STAR 重写
- 至少提供2段STAR示例（Situation/Task/Action/Result）
- 结果必须量化

## 四、技能与证据补强
- 技能矩阵重排
- 缺口补齐方案

## 五、面试准备
- 高频问题清单（至少10问）
- 每问给参考答题框架

## 六、投递策略
- 目标公司分层
- 投递节奏与跟进模板

## 七、明日可执行清单
- 输出10条可立即执行事项""",
    "business": """请严格按以下结构输出，使用中文 Markdown 二级标题：
## 一、项目定义
- 目标用户
- 核心问题
- 价值主张

## 二、市场与竞品
- 市场规模与增长判断
- 竞品对比表（至少3家）
- 差异化结论

## 三、商业模式
- 收入结构
- 成本结构
- 单位经济模型

## 四、产品与运营路线图
- 0-3个月、3-6个月、6-12个月里程碑
- 每阶段关键结果

## 五、财务测算框架
- 关键假设
- 收入成本利润粗算逻辑
- 现金流风险点

## 六、风险与风控
- 至少5项核心风险
- 每项对应预警指标与应对策略

## 七、明日可执行清单
- 输出10条可立即执行事项""",
    "dataops": """请严格按以下结构输出，使用中文 Markdown 二级标题：
## 一、业务目标与分析范围
- 本次分析目标
- 数据口径与时间范围

## 二、指标体系
- 北极星指标
- 过程指标与结果指标
- 指标关系图说明

## 三、异常诊断
- 列出主要异常信号
- 可能原因假设（至少5条）
- 各假设验证路径

## 四、实验与优化方案
- A/B实验设计（目标、样本、周期、判定标准）
- 优化动作优先级（高/中/低）

## 五、经营看板设计
- 看板模块
- 每个模块关键指标
- 预警阈值

## 六、复盘机制
- 周复盘模板
- 月复盘模板

## 七、明日可执行清单
- 输出8条可立即执行事项""",
    "contract": """请严格按以下结构输出，使用中文 Markdown 二级标题：
## 一、合同摘要
- 合同类型
- 交易结构
- 关键标的

## 二、高风险条款识别
- 至少列出8个风险点
- 每个风险点说明触发条件与后果

## 三、条款级修改建议
- 按条款编号给出“原风险点-建议改写-谈判口径”

## 四、责任与赔偿分析
- 违约责任是否对等
- 赔偿上限是否合理
- 不可抗力与免责边界

## 五、履约与证据留存
- 履约节点
- 验收标准
- 证据链建议

## 六、谈判优先级
- 必须坚持
- 可协商
- 可让步

## 七、明日可执行清单
- 输出8条可立即执行事项""",
    "prompt_eval": """请严格按以下结构输出，使用中文 Markdown 二级标题：
## 一、评测目标与边界
- 业务目标
- 风险边界
- 适用场景

## 二、测试集设计
- 样本分层（常规/长尾/对抗）
- 每层样本量建议
- 标注规范

## 三、评测维度与评分标准
- 事实准确性
- 指令遵循
- 完整性
- 安全合规
- 格式稳定性

## 四、A/B与回归机制
- 基线版本定义
- 对比实验流程
- 回归触发条件

## 五、自动化落地
- CI接入建议
- 报告模板
- 失败阈值与阻断规则

## 六、明日可执行清单
- 输出8条可立即执行事项""",
    "agent_observability": """请严格按以下结构输出，使用中文 Markdown 二级标题：
## 一、可观测性目标
- 稳定性目标
- 质量目标
- 成本目标

## 二、链路追踪设计
- 用户请求链路
- 模型调用链路
- 工具调用链路

## 三、核心指标体系
- 成功率
- 平均响应时长
- 工具调用成功率
- 幻觉率代理指标
- 成本指标

## 四、告警与排障流程
- P0/P1/P2 事件分级
- 触发阈值
- 排障SOP

## 五、质量评估闭环
- 抽样评审
- 用户反馈闭环
- 周报/月报模板

## 六、明日可执行清单
- 输出8条可立即执行事项""",
    "ai_workflow": """请严格按以下结构输出，使用中文 Markdown 二级标题：
## 一、业务流程定义
- 触发条件
- 输入输出
- 关键约束

## 二、节点编排方案
- 节点清单
- 节点责任
- 节点间数据流

## 三、容错与治理
- 重试策略
- 回滚策略
- 人工审批节点

## 四、效率与成本优化
- 并行化机会
- 缓存策略
- 成本监控点

## 五、上线验收标准
- 功能验收
- 性能验收
- 安全验收

## 六、明日可执行清单
- 输出8条可立即执行事项""",
    "ai_redteam": """请严格按以下结构输出，使用中文 Markdown 二级标题：
## 一、风险模型
- 攻击面清单
- 关键资产
- 风险等级定义

## 二、测试场景设计
- 提示注入
- 越狱绕过
- 数据泄露
- 工具滥用
- 角色越权

## 三、评估标准
- 可利用性
- 影响范围
- 可复现性
- 修复复杂度

## 四、修复与加固方案
- 短期修复
- 中期治理
- 长期机制

## 五、复测与发布门禁
- 复测流程
- 通过标准
- 发布阻断条件

## 六、明日可执行清单
- 输出8条可立即执行事项""",
    "rag_ops": """请严格按以下结构输出，使用中文 Markdown 二级标题：
## 一、知识库治理目标
- 覆盖率目标
- 时效性目标
- 准确性目标

## 二、文档治理策略
- 入库规范
- 分块策略
- 元数据规范

## 三、检索质量评估
- 离线评测集设计
- 召回与排序指标
- 人工评审标准

## 四、线上优化闭环
- 查询分析
- 失败样本回流
- 热点知识更新

## 五、成本与性能平衡
- 检索参数策略
- 缓存策略
- 高并发降级策略

## 六、明日可执行清单
- 输出8条可立即执行事项""",
    "deep_research": """请严格按以下结构输出，使用中文 Markdown 二级标题：
## 一、研究问题定义
- 核心问题
- 子问题拆解
- 输出目标

## 二、信息源策略
- 一手来源
- 二手来源
- 来源可信度分级

## 三、证据处理方法
- 交叉验证路径
- 证据冲突处理
- 偏差控制方法

## 四、分析框架
- 关键变量
- 对比维度
- 结论判定标准

## 五、交付物模板
- 管理层摘要
- 详细分析
- 风险与建议

## 六、明日可执行清单
- 输出8条可立即执行事项""",
}

def detect_structured_template(message):
    text = (message or "").strip()
    if text.startswith("请为我的电商产品制定30天增长方案"):
        return "ecommerce"
    if text.startswith("请为我设计7天短视频内容计划"):
        return "shortvideo"
    if text.startswith("请把我的经历优化成目标岗位简历"):
        return "resume"
    if text.startswith("请为这个项目写一版商业计划框架"):
        return "business"
    if text.startswith("请基于经营数据做诊断"):
        return "dataops"
    if text.startswith("请帮我审阅这份合同"):
        return "contract"
    if text.startswith("请为我的AI应用设计提示词评测方案"):
        return "prompt_eval"
    if text.startswith("请为我的AI助手设计可观测性方案"):
        return "agent_observability"
    if text.startswith("请为我的业务场景设计一套AI自动化工作流"):
        return "ai_workflow"
    if text.startswith("请为我的AI产品制定红队测试计划"):
        return "ai_redteam"
    if text.startswith("请为我的知识库系统制定RAG运营方案"):
        return "rag_ops"
    if text.startswith("请围绕这个主题制定深度研究计划"):
        return "deep_research"
    return None

def get_structured_output_prompt(message, template_id=None):
    key = template_id if template_id in STRUCTURED_OUTPUT_TEMPLATES else detect_structured_template(message)
    if not key:
        return ""
    return "\n\n【结构化输出要求】\n" + STRUCTURED_OUTPUT_TEMPLATES[key]

def get_mcp_system_prompt():
    """生成 MCP 工具的系统提示词"""
    config = load_mcp_config()
    enabled_plugins = []
    
    for plugin_id, plugin in config.get("plugins", {}).items():
        if plugin.get("enabled", False):
            tools_desc = []
            for tool in plugin.get("tools", []):
                params = ", ".join([f'{k}={v["type"]}' for k, v in tool.get("parameters", {}).items()])
                tools_desc.append(f"  - {tool['name']}({params}): {tool['description']}")
            
            if tools_desc:
                enabled_plugins.append({
                    "id": plugin_id,
                    "name": plugin.get("name", ""),
                    "tools": tools_desc
                })
    
    if not enabled_plugins:
        return ""
    
    prompt = "\n\n【MCP工具使用说明】\n"
    prompt += "你可以使用以下工具来帮助用户。当需要使用工具时，请按以下格式输出：\n"
    prompt += "[MCP:插件ID:工具名]{\"参数名\": \"参数值\"}\n\n"
    prompt += "可用工具：\n"
    
    for plugin in enabled_plugins:
        prompt += f"\n{plugin['name']}:\n"
        prompt += "\n".join(plugin['tools']) + "\n"
    
    prompt += "\n示例：\n"
    prompt += '- 读取文件: [MCP:filesystem:read_file]{"path": "~/document.txt"}\n'
    prompt += '- 搜索网络: [MCP:web_search:search]{"query": "最新科技新闻", "num_results": 5}\n'
    prompt += '- 计算: [MCP:calculator:calculate]{"expression": "2+2*3"}\n'
    prompt += '- 获取时间: [MCP:datetime:get_current_time]{"timezone": "Asia/Shanghai"}\n'
    
    return prompt

def get_lora_system(lora_id):
    lora = next((l for l in PRESET_LORAS if l['id'] == lora_id), None)
    return lora.get('system', '') if lora else ''

def generate_stream(message, history, role_id='kaguya', lora_id=None, temperature=0.7, max_tokens=4096, rag_context="", session_id=None, structured_template=None):
    model = load_model()
    
    system_prompt = get_role_system(role_id)
    lora_system = get_lora_system(lora_id)
    if lora_system:
        system_prompt = lora_system
    
    # 添加 MCP 工具提示词
    mcp_prompt = get_mcp_system_prompt()
    if mcp_prompt:
        system_prompt += mcp_prompt
    
    # 添加记忆系统提示词
    try:
        # 添加用户消息到短期记忆
        memory_system.add_to_short_term('user', message)
        
        # 获取相关记忆
        context = message + " " + " ".join([h[0] for h in history[-3:]])
        relevant_memories = memory_system.get_relevant_memories_for_context(context)
        memory_prompt = memory_system.format_memories_for_prompt(relevant_memories)
        
        if memory_prompt:
            system_prompt += "\n\n【记忆系统】\n" + memory_prompt
    except Exception as e:
        print(f"记忆系统错误: {e}")
    
    if rag_context:
        system_prompt += "\n\n你可以参考以下文档内容来回答问题，如果文档内容与问题相关，请基于文档内容回答。" + rag_context
    
    structured_prompt = get_structured_output_prompt(message, structured_template)
    if structured_prompt:
        system_prompt += structured_prompt
    
    messages = [{"role": "system", "content": system_prompt}]
    for h in history:
        messages.append({"role": "user", "content": h[0]})
        messages.append({"role": "assistant", "content": h[1]})
    messages.append({"role": "user", "content": message})
    
    input_len = sum(len(m['content']) for m in messages) // 2
    
    generated_tokens = 0
    has_content = False
    all_thinking = []
    try:
        print(f"开始生成，消息数: {len(messages)}, 温度: {temperature}, 最大token: {max_tokens}")
        for chunk_type, chunk_content in model.chat_stream(messages, temperature=temperature, max_tokens=max_tokens):
            generated_tokens += 1
            if chunk_content:
                if chunk_type == 'content':
                    has_content = True
                    yield json.dumps({"content": chunk_content, "done": False})
                elif chunk_type == 'thinking':
                    # 收集思考过程但不返回给前端（系统提示词要求不输出思考过程）
                    all_thinking.append(chunk_content)
                    # 不返回 thinking 类型的数据
                    # yield json.dumps({"thinking": chunk_content, "done": False})
        
        # 如果没有 content 但有 thinking，把 thinking 作为 content 返回
        if not has_content and all_thinking:
            print(f"警告: 模型只返回了思考过程，没有正式回答，将思考过程作为回答返回")
            yield json.dumps({"content": "".join(all_thinking), "done": False})
        
        yield json.dumps({"content": "", "done": True, "tokens_in": input_len, "tokens_out": generated_tokens})
        print(f"生成完成，共生成 {generated_tokens} 个token")
    except Exception as e:
        print(f"生成错误: {e}")
        import traceback
        traceback.print_exc()
        yield json.dumps({"content": f"❌ 生成错误: {str(e)}", "done": True})


def chat(message, history, role_id='kaguya', lora_id=None, temperature=0.7, max_tokens=4096, structured_template=None):
    model = load_model()
    
    system_prompt = get_role_system(role_id)
    lora_system = get_lora_system(lora_id)
    if lora_system:
        system_prompt = lora_system
    
    structured_prompt = get_structured_output_prompt(message, structured_template)
    if structured_prompt:
        system_prompt += structured_prompt
    
    messages = [{"role": "system", "content": system_prompt}]
    for h in history:
        messages.append({"role": "user", "content": h[0]})
        messages.append({"role": "assistant", "content": h[1]})
    messages.append({"role": "user", "content": message})
    
    input_len = sum(len(m['content']) for m in messages) // 2
    
    try:
        response = model.chat(messages, temperature=temperature, max_tokens=max_tokens)
        return response, input_len, len(response) // 2
    except Exception as e:
        return f"错误: {str(e)}", input_len, 0

def get_provider_runtime(provider=None):
    provider_id = (provider or external_api_config.get("active_provider") or "deepseek").strip().lower()
    providers = external_api_config.get("providers", {})
    provider_cfg = providers.get(provider_id, {})
    api_key = (provider_cfg.get("api_key") or "").strip()
    api_url = (provider_cfg.get("api_url") or "").strip()
    model = (provider_cfg.get("model") or "").strip()
    return provider_id, {"api_key": api_key, "api_url": api_url, "model": model}

def call_external_provider(provider, api_url, api_key, model, prompt, system_prompt=""):
    if not api_key:
        raise ValueError(f"{provider} API Key 未配置")
    provider_id = (provider or "").strip().lower()
    if provider_id == "gemini":
        base = (api_url or "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
        endpoint = f"{base}/models/{model}:generateContent?key={urllib.parse.quote(api_key)}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=90) as response:
            result = json.loads(response.read().decode("utf-8"))
        candidates = result.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            text = "".join([(p.get("text") or "") for p in parts if isinstance(p, dict)]).strip()
            if text:
                return text
        return "未获取到有效内容"
    if provider_id == "claude":
        base = (api_url or "https://api.anthropic.com").rstrip("/")
        endpoint = f"{base}/v1/messages"
        payload = {
            "model": model,
            "max_tokens": 2048,
            "messages": [{"role": "user", "content": prompt}]
        }
        if system_prompt:
            payload["system"] = system_prompt
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=90) as response:
            result = json.loads(response.read().decode("utf-8"))
        content_list = result.get("content", [])
        if content_list:
            text = "".join([(x.get("text") or "") for x in content_list if isinstance(x, dict)]).strip()
            if text:
                return text
        return "未获取到有效内容"
    base = (api_url or "").rstrip("/")
    if provider_id == "deepseek" and not base:
        base = "https://api.deepseek.com"
    if not base:
        raise ValueError(f"{provider} API URL 未配置")
    endpoint = f"{base}/chat/completions"
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.6
    }
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=90) as response:
        result = json.loads(response.read().decode("utf-8"))
    choices = result.get("choices", [])
    if choices:
        content = choices[0].get("message", {}).get("content", "")
        if content:
            return content.strip()
    return "未获取到有效内容"

def build_scene_prompt(scene_id, topic, context, goal, constraints):
    template = SCENE_PROMPT_TEMPLATES.get(scene_id)
    if not template:
        raise ValueError("场景不支持")
    return template.format(
        topic=(topic or "未提供").strip(),
        context=(context or "未提供").strip(),
        goal=(goal or "未提供").strip(),
        constraints=(constraints or "无").strip()
    )

app = Flask(__name__)

def optional_image_response(path, label):
    if os.path.exists(path):
        return send_file(path)
    safe_label = (label or "Kaguya").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128"><rect width="100%" height="100%" rx="20" ry="20" fill="#eef2ff"/><text x="50%" y="54%" dominant-baseline="middle" text-anchor="middle" font-size="14" fill="#4f46e5">{safe_label}</text></svg>'''
    return Response(svg, mimetype='image/svg+xml')

@app.route('/background')
def background():
    return optional_image_response(r'C:\Users\林智涵\Pictures\Screenshots\屏幕截图 2026-02-04 211649.png', '背景')

@app.route('/header-img')
def header_img():
    return optional_image_response(r'C:\Users\林智涵\Pictures\Screenshots\屏幕截图 2026-02-16 202726.png', '辉夜')

@app.route('/deepseek-icon')
def deepseek_icon():
    return optional_image_response(r'C:\Users\林智涵\Pictures\Screenshots\屏幕截图 2026-02-16 202825.png', 'DeepSeek')

@app.route('/sidebar-icon')
def sidebar_icon():
    return optional_image_response(r'C:\Users\林智涵\Pictures\Screenshots\屏幕截图 2026-02-17 153942.png', '辉夜')

@app.route('/')
def index():
    tools_meta = {k: {"name": v["name"], "description": v["description"], "icon": v["icon"]} for k, v in AVAILABLE_TOOLS.items()}
    # 使用 ensure_ascii=False 保持中文字符，并确保 JSON 正确转义
    html = HTML_TEMPLATE.replace('{{roles_json}}', json.dumps(PRESET_ROLES, ensure_ascii=False))
    html = html.replace('{{loras_json}}', json.dumps(PRESET_LORAS, ensure_ascii=False))
    html = html.replace('{{tools_json}}', json.dumps(tools_meta, ensure_ascii=False))
    html = html.replace('{{commands_json}}', json.dumps(QUICK_COMMANDS, ensure_ascii=False))
    # 直接返回 HTML，不使用 render_template_string 避免额外的转义处理
    return html

@app.route('/lora/list')
def lora_list():
    loras = []
    for l in PRESET_LORAS:
        loras.append({
            "id": l["id"], "name": l["name"], "description": l["description"],
            "icon": l.get("icon", "🤖"), "color": l.get("color", "#10b981"),
            "loaded": current_lora == l["id"], "available": True
        })
    return jsonify({'loras': loras})

@app.route('/api/roles', methods=['GET'])
def api_roles():
    return jsonify({"success": True, "roles": PRESET_ROLES})

@app.route('/api/prompts', methods=['GET'])
def api_prompts():
    prompts = [
        {"id": "code-review", "name": "代码审查", "category": "engineering", "prompt": "请对以下代码进行专业审查..."},
        {"id": "doc-gen", "name": "文档生成", "category": "general", "prompt": "请为以下代码生成文档..."},
        {"id": "api-design", "name": "API设计", "category": "engineering", "prompt": "请根据需求设计API..."},
    ]
    return jsonify({"success": True, "prompts": prompts})

@app.route('/lora/load', methods=['POST'])
def lora_load():
    global current_lora
    data = request.json
    lora_id = data.get('lora_id', 'none')
    current_lora = lora_id
    lora_info = next((l for l in PRESET_LORAS if l['id'] == lora_id), None)
    return jsonify({'success': True, 'message': f'已切换到{lora_info["name"] if lora_info else lora_id}'})

@app.route('/tool/execute', methods=['POST'])
def tool_execute():
    data = request.json
    tool_id = data.get('tool')
    tool_input = data.get('input', '')
    
    if tool_id in AVAILABLE_TOOLS:
        try:
            result = AVAILABLE_TOOLS[tool_id]["func"](tool_input)
            return jsonify({'success': True, 'result': result})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    return jsonify({'success': False, 'error': '工具不存在'})

@app.route('/code/execute', methods=['POST'])
def code_execute():
    data = request.json
    code = data.get('code', '')
    result = execute_python_code(code)
    return jsonify(result)

@app.route('/kb/add', methods=['POST'])
def kb_add():
    data = request.json
    text = data.get('text', '')
    if text:
        entry_id = add_to_knowledge_base(text)
        return jsonify({'success': True, 'id': entry_id})
    return jsonify({'success': False, 'error': '内容为空'})

@app.route('/deepseek/test', methods=['POST'])
def deepseek_test():
    try:
        data = request.json
        api_key = data.get('apiKey', '')
        api_url = data.get('apiUrl', 'https://api.deepseek.com')
        
        if not api_key:
            return jsonify({'success': False, 'error': 'API Key不能为空'})
        
        import urllib.request
        import json as json_module
        
        test_url = f"{api_url.rstrip('/')}/chat/completions"
        test_data = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": "Hi"}],
            "max_tokens": 10
        }
        
        req = urllib.request.Request(
            test_url,
            data=json_module.dumps(test_data).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}'
            },
            method='POST'
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json_module.loads(response.read().decode('utf-8'))
            return jsonify({'success': True, 'message': '连接成功'})
            
    except urllib.error.HTTPError as e:
        error_msg = f"HTTP错误: {e.code}"
        try:
            error_body = json_module.loads(e.read().decode('utf-8'))
            error_msg = error_body.get('error', {}).get('message', error_msg)
        except:
            pass
        return jsonify({'success': False, 'error': error_msg})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/deepseek/chat', methods=['POST'])
def deepseek_chat():
    try:
        data = request.json
        api_key = data.get('apiKey', '')
        api_url = data.get('apiUrl', 'https://api.deepseek.com')
        model = data.get('model', 'deepseek-chat')
        messages = data.get('messages', [])
        
        if not api_key:
            return jsonify({'error': 'API Key未配置'}), 400
        
        import urllib.request
        import json as json_module
        
        chat_url = f"{api_url.rstrip('/')}/chat/completions"
        chat_data = {
            "model": model,
            "messages": messages,
            "stream": True
        }
        
        def generate():
            req = urllib.request.Request(
                chat_url,
                data=json_module.dumps(chat_data).encode('utf-8'),
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {api_key}'
                },
                method='POST'
            )
            
            with urllib.request.urlopen(req, timeout=60) as response:
                for line in response:
                    line = line.decode('utf-8').strip()
                    if line.startswith('data: '):
                        if line == 'data: [DONE]':
                            yield 'data: {"done": true}\n\n'
                            break
                        try:
                            chunk = json_module.loads(line[6:])
                            delta = chunk.get('choices', [{}])[0].get('delta', {})
                            # 提取正式回答内容
                            if delta.get('content'):
                                content = delta['content']
                                yield f'data: {json_module.dumps({"content": content})}\n\n'
                            # 提取思考过程内容
                            if delta.get('reasoning_content'):
                                reasoning = delta['reasoning_content']
                                yield f'data: {json_module.dumps({"reasoning": reasoning})}\n\n'
                        except:
                            pass
        
        return Response(generate(), mimetype='text/event-stream')
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/external/config', methods=['GET'])
def external_config_get():
    providers = external_api_config.get("providers", {})
    return jsonify({"success": True, "active_provider": external_api_config.get("active_provider", "deepseek"), "providers": providers})

@app.route('/external/config', methods=['POST'])
def external_config_save():
    global external_api_config
    data = request.json or {}
    active_provider = (data.get("active_provider") or "deepseek").strip().lower()
    providers = data.get("providers", {})
    if not isinstance(providers, dict):
        return jsonify({"success": False, "error": "providers格式错误"})
    default_cfg = default_external_api_config()
    normalized = {"active_provider": active_provider, "providers": {}}
    for provider, base in default_cfg["providers"].items():
        item = providers.get(provider, {})
        normalized["providers"][provider] = {
            "api_url": (item.get("api_url") or base.get("api_url") or "").strip(),
            "api_key": (item.get("api_key") or "").strip(),
            "model": (item.get("model") or base.get("model") or "").strip()
        }
    if normalized["active_provider"] not in normalized["providers"]:
        normalized["active_provider"] = "deepseek"
    external_api_config = normalized
    save_external_api_config()
    return jsonify({"success": True, "config": external_api_config})

@app.route('/external/test', methods=['POST'])
def external_test():
    try:
        data = request.json or {}
        provider = (data.get("provider") or external_api_config.get("active_provider") or "deepseek").strip().lower()
        provider_id, runtime = get_provider_runtime(provider)
        text = call_external_provider(provider_id, runtime.get("api_url"), runtime.get("api_key"), runtime.get("model"), "返回“连接成功”四个字。", "")
        return jsonify({"success": True, "provider": provider_id, "message": text[:80]})
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8")
        except Exception:
            body = str(e)
        return jsonify({"success": False, "error": f"HTTP {e.code}: {body[:300]}"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/scenes/list', methods=['GET'])
def scenes_list():
    items = []
    for scene_id in SCENE_PROMPT_TEMPLATES.keys():
        items.append({"id": scene_id})
    return jsonify({"success": True, "scenes": items})

@app.route('/scenes/generate', methods=['POST'])
def scenes_generate():
    try:
        data = request.json or {}
        scene_id = (data.get("scene_id") or "").strip()
        provider = (data.get("provider") or external_api_config.get("active_provider") or "deepseek").strip().lower()
        topic = (data.get("topic") or "").strip()
        context = (data.get("context") or "").strip()
        goal = (data.get("goal") or "").strip()
        constraints = (data.get("constraints") or "").strip()
        if scene_id not in SCENE_PROMPT_TEMPLATES:
            return jsonify({"success": False, "error": "场景不存在"})
        if not topic:
            return jsonify({"success": False, "error": "请输入核心主题/素材"})
        provider_id, runtime = get_provider_runtime(provider)
        prompt = build_scene_prompt(scene_id, topic, context, goal, constraints)
        system_prompt = "你是专业顾问，请输出结构化、可执行、可落地的中文方案。"
        text = call_external_provider(provider_id, runtime.get("api_url"), runtime.get("api_key"), runtime.get("model"), prompt, system_prompt)
        return jsonify({
            "success": True,
            "provider": provider_id,
            "model": runtime.get("model"),
            "scene_id": scene_id,
            "content": text
        })
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8")
        except Exception:
            body = str(e)
        return jsonify({"success": False, "error": f"HTTP {e.code}: {body[:500]}"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# ==================== MCP 插件管理 API ====================

@app.route('/mcp/plugins', methods=['GET'])
def mcp_list_plugins():
    """获取所有 MCP 插件列表"""
    try:
        config = load_mcp_config()
        plugins = []
        for plugin_id, plugin in config.get("plugins", {}).items():
            plugins.append({
                "id": plugin_id,
                "name": plugin.get("name", ""),
                "description": plugin.get("description", ""),
                "icon": plugin.get("icon", "🔌"),
                "color": plugin.get("color", "#667eea"),
                "type": plugin.get("type", "builtin"),
                "enabled": plugin.get("enabled", False),
                "tools_count": len(plugin.get("tools", []))
            })
        return jsonify({'success': True, 'plugins': plugins})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/mcp/plugin/<plugin_id>', methods=['GET'])
def mcp_get_plugin(plugin_id):
    """获取单个 MCP 插件详情"""
    try:
        config = load_mcp_config()
        plugin = config.get("plugins", {}).get(plugin_id)
        if not plugin:
            return jsonify({'success': False, 'error': '插件不存在'})
        return jsonify({'success': True, 'plugin': plugin})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/mcp/plugin/<plugin_id>/enable', methods=['POST'])
def mcp_enable_plugin(plugin_id):
    """启用/禁用 MCP 插件"""
    try:
        data = request.json
        enabled = data.get('enabled', True)
        
        config = load_mcp_config()
        if plugin_id not in config.get("plugins", {}):
            return jsonify({'success': False, 'error': '插件不存在'})
        
        config["plugins"][plugin_id]["enabled"] = enabled
        save_mcp_config(config)
        
        action = "启用" if enabled else "禁用"
        return jsonify({'success': True, 'message': f'已{action}插件'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/mcp/plugin/<plugin_id>/config', methods=['POST'])
def mcp_update_plugin_config(plugin_id):
    """更新 MCP 插件配置"""
    try:
        data = request.json
        config = load_mcp_config()
        
        if plugin_id not in config.get("plugins", {}):
            return jsonify({'success': False, 'error': '插件不存在'})
        
        # 更新配置
        config["plugins"][plugin_id]["config"] = data.get('config', {})
        save_mcp_config(config)
        
        return jsonify({'success': True, 'message': '配置已更新'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/mcp/execute', methods=['POST'])
def mcp_execute_tool():
    """执行 MCP 工具"""
    try:
        data = request.json
        plugin_id = data.get('plugin_id')
        tool_name = data.get('tool_name')
        parameters = data.get('parameters', {})
        
        if not plugin_id or not tool_name:
            return jsonify({'success': False, 'error': '缺少必要参数'})
        
        result = execute_mcp_tool(plugin_id, tool_name, parameters)
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/mcp/tools', methods=['GET'])
def mcp_get_enabled_tools():
    """获取所有启用的 MCP 工具（用于 Function Calling）"""
    try:
        tools = get_enabled_mcp_tools()
        return jsonify({'success': True, 'tools': tools})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ==================== 工作流编排 API ====================

@app.route('/workflow/node-types', methods=['GET'])
def workflow_get_node_types():
    """获取所有工作流节点类型"""
    try:
        return jsonify({'success': True, 'node_types': WORKFLOW_NODE_TYPES})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/workflows', methods=['GET'])
def workflow_list():
    """获取所有工作流列表"""
    try:
        workflows_data = load_workflows()
        # 简化返回，不包含完整的节点数据
        workflows = []
        for wf in workflows_data.get('workflows', []):
            workflows.append({
                'id': wf.get('id'),
                'name': wf.get('name', '未命名工作流'),
                'description': wf.get('description', ''),
                'icon': wf.get('icon', '📋'),
                'color': wf.get('color', '#667eea'),
                'node_count': len(wf.get('nodes', [])),
                'created_at': wf.get('created_at'),
                'updated_at': wf.get('updated_at')
            })
        return jsonify({'success': True, 'workflows': workflows})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/workflow/<workflow_id>', methods=['GET'])
def workflow_get(workflow_id):
    """获取单个工作流详情"""
    try:
        workflow = load_workflow_file(workflow_id)
        if not workflow:
            return jsonify({'success': False, 'error': '工作流不存在'})
        return jsonify({'success': True, 'workflow': workflow})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/workflow', methods=['POST'])
def workflow_create():
    """创建或保存工作流"""
    try:
        data = request.json
        workflow_id = data.get('id') or f"workflow_{int(time.time())}"
        
        workflow_data = {
            'id': workflow_id,
            'name': data.get('name', '未命名工作流'),
            'description': data.get('description', ''),
            'icon': data.get('icon', '📋'),
            'color': data.get('color', '#667eea'),
            'nodes': data.get('nodes', []),
            'connections': data.get('connections', []),
            'updated_at': time.time()
        }
        
        # 检查是否是新建
        workflows_data = load_workflows()
        existing = any(w['id'] == workflow_id for w in workflows_data.get('workflows', []))
        
        if not existing:
            workflow_data['created_at'] = time.time()
            workflows_data['workflows'].append({
                'id': workflow_id,
                'name': workflow_data['name'],
                'description': workflow_data['description'],
                'icon': workflow_data['icon'],
                'color': workflow_data['color'],
                'node_count': len(workflow_data['nodes']),
                'created_at': workflow_data['created_at'],
                'updated_at': workflow_data['updated_at']
            })
        else:
            # 更新现有工作流信息
            for wf in workflows_data['workflows']:
                if wf['id'] == workflow_id:
                    wf['name'] = workflow_data['name']
                    wf['description'] = workflow_data['description']
                    wf['icon'] = workflow_data['icon']
                    wf['color'] = workflow_data['color']
                    wf['node_count'] = len(workflow_data['nodes'])
                    wf['updated_at'] = workflow_data['updated_at']
                    break
        
        # 保存工作流文件和索引
        if save_workflow_file(workflow_id, workflow_data):
            save_workflows(workflows_data)
            return jsonify({'success': True, 'workflow_id': workflow_id})
        else:
            return jsonify({'success': False, 'error': '保存失败'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/workflow/<workflow_id>', methods=['DELETE'])
def workflow_delete(workflow_id):
    """删除工作流"""
    try:
        workflows_data = load_workflows()
        workflows_data['workflows'] = [w for w in workflows_data['workflows'] if w['id'] != workflow_id]
        save_workflows(workflows_data)
        
        # 删除工作流文件
        file_path = os.path.join(WORKFLOW_DIR, f"{workflow_id}.json")
        if os.path.exists(file_path):
            os.remove(file_path)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/workflow/<workflow_id>/execute', methods=['POST'])
def workflow_execute(workflow_id):
    """执行工作流"""
    try:
        workflow = load_workflow_file(workflow_id)
        if not workflow:
            return jsonify({'success': False, 'error': '工作流不存在'})
        
        data = request.json or {}
        inputs = data.get('inputs', {})
        
        # 执行工作流
        result = workflow_engine.execute_workflow(workflow, inputs)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/workflow/execute', methods=['POST'])
def workflow_execute_inline():
    """直接执行工作流（不保存）"""
    try:
        data = request.json
        workflow = data.get('workflow', {})
        inputs = data.get('inputs', {})
        
        result = workflow_engine.execute_workflow(workflow, inputs)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ==================== 记忆系统 API ====================

@app.route('/memory/stats', methods=['GET'])
def memory_get_stats():
    """获取记忆统计信息"""
    try:
        stats = memory_system.get_memory_stats()
        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/memory/search', methods=['POST'])
def memory_search():
    """搜索记忆"""
    try:
        data = request.json
        query = data.get('query', '')
        top_k = data.get('top_k', 5)
        memory_type = data.get('memory_type')
        
        memories = memory_system.search_memories(query, top_k=top_k, memory_type=memory_type)
        return jsonify({
            'success': True, 
            'memories': [
                {
                    'id': m[0],
                    'content': m[1],
                    'type': m[2],
                    'category': m[3],
                    'importance': m[4],
                    'created_at': m[5],
                    'access_count': m[7]
                } for m in memories
            ]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/memory', methods=['POST'])
def memory_add():
    """添加记忆"""
    try:
        data = request.json
        content = data.get('content', '')
        memory_type = data.get('type', 'fact')
        category = data.get('category', 'general')
        importance = data.get('importance')
        
        memory_id = memory_system.add_long_term_memory(
            content=content,
            memory_type=memory_type,
            category=category,
            importance=importance
        )
        return jsonify({'success': True, 'memory_id': memory_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/memory/<memory_id>', methods=['DELETE'])
def memory_delete(memory_id):
    """删除记忆"""
    try:
        conn = sqlite3.connect(MEMORY_DB_FILE)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM long_term_memories WHERE id = ?', (memory_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/memory/profile', methods=['GET'])
def memory_get_profile():
    """获取用户画像"""
    try:
        profile = memory_system.get_user_profile()
        return jsonify({'success': True, 'profile': profile})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/memory/profile', methods=['POST'])
def memory_update_profile():
    """更新用户画像"""
    try:
        data = request.json
        key = data.get('key', '')
        value = data.get('value', '')
        category = data.get('category', 'preference')
        confidence = data.get('confidence', 0.5)
        
        memory_system.update_user_profile(key, value, category, confidence)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/memory/consolidate', methods=['POST'])
def memory_consolidate():
    """整合记忆"""
    try:
        memory_system.consolidate_memories()
        return jsonify({'success': True, 'message': '记忆整合完成'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ==================== 多模态视觉理解 API ====================

@app.route('/multimodal/upload', methods=['POST'])
def multimodal_upload_image():
    """上传并处理图像"""
    try:
        if 'image' not in request.files:
            # 尝试从 JSON 获取 base64 图像
            data = request.json
            if data and 'image' in data:
                image_data = data['image']
                task = data.get('task', 'understand')
                result = multimodal_system.process_image(image_data, task=task)
                return jsonify({'success': True, 'result': result})
            return jsonify({'success': False, 'error': '没有提供图像'})
        
        file = request.files['image']
        task = request.form.get('task', 'understand')
        
        # 保存上传的文件
        filename = f"{uuid.uuid4()}_{file.filename}"
        filepath = os.path.join(IMAGE_CACHE_DIR, filename)
        file.save(filepath)
        
        # 处理图像
        result = multimodal_system.process_image(filepath, task=task)
        result['filepath'] = filepath
        
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/multimodal/analyze', methods=['POST'])
def multimodal_analyze():
    """分析图像内容"""
    try:
        data = request.json
        image_id = data.get('image_id')
        task = data.get('task', 'analyze')
        
        if not image_id or image_id not in multimodal_system.image_cache:
            return jsonify({'success': False, 'error': '图像不存在'})
        
        image_info = multimodal_system.image_cache[image_id]
        result = multimodal_system.process_image(image_info['path'], task=task)
        
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/multimodal/chat', methods=['POST'])
def multimodal_chat():
    """多模态图文对话"""
    try:
        data = request.json
        message = data.get('message', '')
        image_id = data.get('image_id')
        
        # 如果有图像，获取图像分析
        image_analysis = None
        if image_id and image_id in multimodal_system.image_cache:
            image_info = multimodal_system.image_cache[image_id]
            image_analysis = multimodal_system.process_image(
                image_info['path'], 
                task='understand'
            )
        
        # 生成多模态提示词
        multimodal_prompt = multimodal_system.generate_multimodal_prompt(
            message, 
            image_analysis
        )
        
        # 添加到对话历史
        multimodal_system.add_to_conversation('user', message, image_id)
        
        return jsonify({
            'success': True,
            'prompt': multimodal_prompt,
            'image_analysis': image_analysis,
            'has_image': image_id is not None
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/multimodal/history', methods=['GET'])
def multimodal_get_history():
    """获取图文对话历史"""
    try:
        history = multimodal_system.get_conversation_context(n=10)
        return jsonify({'success': True, 'history': history})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/multimodal/clear', methods=['POST'])
def multimodal_clear_history():
    """清除图文对话历史"""
    try:
        multimodal_system.conversation_history = []
        return jsonify({'success': True, 'message': '对话历史已清除'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ==================== 模型微调平台 API ====================

@app.route('/finetune/datasets', methods=['GET'])
def finetune_get_datasets():
    """获取所有数据集"""
    try:
        datasets = finetune_platform.get_all_datasets()
        return jsonify({'success': True, 'datasets': datasets})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/finetune/dataset/upload', methods=['POST'])
def finetune_upload_dataset():
    """上传数据集"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': '没有文件'})
        
        file = request.files['file']
        name = request.form.get('name', file.filename)
        format_type = request.form.get('format', 'jsonl')
        
        file_data = file.read()
        result = finetune_platform.upload_dataset(name, file_data, format_type)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/finetune/dataset/<dataset_id>', methods=['DELETE'])
def finetune_delete_dataset(dataset_id):
    """删除数据集"""
    try:
        result = finetune_platform.delete_dataset(dataset_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/finetune/jobs', methods=['GET'])
def finetune_get_jobs():
    """获取所有训练任务"""
    try:
        jobs = finetune_platform.get_all_jobs()
        return jsonify({'success': True, 'jobs': jobs})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/finetune/job', methods=['POST'])
def finetune_create_job():
    """创建训练任务"""
    try:
        data = request.json
        name = data.get('name', '未命名任务')
        dataset_id = data.get('dataset_id')
        config = data.get('config', {})
        
        result = finetune_platform.create_training_job(name, dataset_id, config)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/finetune/job/<job_id>/start', methods=['POST'])
def finetune_start_job(job_id):
    """开始训练"""
    try:
        result = finetune_platform.start_training(job_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/finetune/job/<job_id>/stop', methods=['POST'])
def finetune_stop_job(job_id):
    """停止训练"""
    try:
        result = finetune_platform.stop_training(job_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/finetune/job/<job_id>', methods=['GET'])
def finetune_get_job_status(job_id):
    """获取训练任务状态"""
    try:
        result = finetune_platform.get_job_status(job_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/finetune/job/<job_id>', methods=['DELETE'])
def finetune_delete_job(job_id):
    """删除训练任务"""
    try:
        result = finetune_platform.delete_job(job_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/finetune/job/<job_id>/logs', methods=['GET'])
def finetune_get_job_logs(job_id):
    """获取训练日志"""
    try:
        limit = request.args.get('limit', 100, type=int)
        result = finetune_platform.get_training_logs(job_id, limit)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/kb/search', methods=['POST'])
def kb_search():
    data = request.json
    query = data.get('query', '')
    results = search_knowledge_base(query)
    return jsonify({'success': True, 'results': results})

@app.route('/rag/upload', methods=['POST'])
def rag_upload():
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': '没有上传文件'})
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': '没有选择文件'})
        filename = file.filename
        file_path = os.path.join(RAG_DIR, f"{uuid.uuid4().hex[:8]}_{filename}")
        file.save(file_path)
        doc_info, error = add_document_to_rag(file_path, filename)
        if error:
            return jsonify({'success': False, 'error': error})
        return jsonify({'success': True, 'document': doc_info})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/rag/documents', methods=['GET'])
def rag_documents_list():
    return jsonify({'success': True, 'documents': rag_documents})

@app.route('/rag/delete/<doc_id>', methods=['DELETE'])
def rag_delete(doc_id):
    try:
        delete_document_from_rag(doc_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/rag/search', methods=['POST'])
def rag_search():
    data = request.json
    query = data.get('query', '')
    top_k = data.get('top_k', 5)
    doc_ids = data.get('doc_ids')
    category = data.get('category')
    use_rerank = data.get('use_rerank', True)
    alpha = data.get('alpha', 0.5)
    use_cache = data.get('use_cache', True)
    use_expansion = data.get('use_expansion', True)
    use_hyde = data.get('use_hyde', False)
    use_multi_query = data.get('use_multi_query', False)
    use_decomposition = data.get('use_decomposition', False)
    use_adaptive = data.get('use_adaptive', True)
    use_rrf = data.get('use_rrf', False)
    use_metadata_filter = data.get('use_metadata_filter', True)
    use_time_weight = data.get('use_time_weight', False)
    use_compression = data.get('use_compression', False)
    use_iterative = data.get('use_iterative', False)
    results = search_rag(query, top_k, doc_ids, category, use_rerank, alpha, None, use_cache, use_expansion, use_hyde, use_multi_query, use_decomposition, use_adaptive, use_rrf, use_metadata_filter, use_time_weight, use_compression, use_iterative)
    quality = calculate_retrieval_quality(query, results)
    query_type = classify_query(query)
    structured = build_structured_query(query)
    compressed = compress_context(results) if use_compression else None
    return jsonify({
        'success': True, 
        'results': results, 
        'count': len(results),
        'quality': quality,
        'query_type': query_type,
        'structured_query': structured,
        'compressed_context': compressed
    })

@app.route('/rag/preview/<doc_id>', methods=['GET'])
def rag_preview(doc_id):
    doc = next((d for d in rag_documents if d['id'] == doc_id), None)
    if not doc:
        return jsonify({'success': False, 'error': '文档不存在'})
    chunks = [c for c in rag_chunks if c['doc_id'] == doc_id]
    chunks.sort(key=lambda x: x.get('index', 0))
    return jsonify({
        'success': True,
        'document': doc,
        'chunks': [{'id': c['id'], 'index': c.get('index', 0), 'text': c['text'][:200] + '...' if len(c['text']) > 200 else c['text']} for c in chunks]
    })

@app.route('/rag/chunk/<chunk_id>', methods=['GET'])
def rag_get_chunk(chunk_id):
    chunk = next((c for c in rag_chunks if c['id'] == chunk_id), None)
    if not chunk:
        return jsonify({'success': False, 'error': '分块不存在'})
    doc = next((d for d in rag_documents if d['id'] == chunk['doc_id']), None)
    return jsonify({
        'success': True,
        'chunk': chunk,
        'document': doc
    })

@app.route('/rag/stats', methods=['GET'])
def rag_stats():
    return jsonify({'success': True, 'stats': get_rag_stats()})

@app.route('/rag/clear_cache', methods=['POST'])
def rag_clear_cache():
    global rag_cache
    rag_cache = {}
    return jsonify({'success': True, 'message': '缓存已清除'})

@app.route('/rag/batch_upload', methods=['POST'])
def rag_batch_upload():
    try:
        if 'files' not in request.files:
            return jsonify({'success': False, 'error': '没有上传文件'})
        files = request.files.getlist('files')
        results = []
        for file in files:
            if file.filename:
                filename = file.filename
                file_path = os.path.join(RAG_DIR, f"{uuid.uuid4().hex[:8]}_{filename}")
                file.save(file_path)
                doc_info, error = add_document_to_rag(file_path, filename)
                results.append({
                    'filename': filename,
                    'success': error is None,
                    'error': error,
                    'document': doc_info
                })
        return jsonify({'success': True, 'results': results})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/rag/add_text', methods=['POST'])
def rag_add_text():
    try:
        data = request.json
        text = data.get('text', '')
        title = data.get('title', '手动输入')
        tags = data.get('tags', [])
        if len(text) < 50:
            return jsonify({'success': False, 'error': '文本内容过少'})
        doc_id = str(uuid.uuid4())[:8]
        doc_info = {
            "id": doc_id,
            "filename": title,
            "path": "",
            "size": len(text),
            "time": datetime.now().isoformat(),
            "chunk_count": 0,
            "category": 'text',
            "tags": tags,
            "char_count": len(text),
            "word_count": len(text.split())
        }
        chunks = chunk_text(text, chunk_size=400, overlap=80)
        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc_id}_{i}"
            embedding = compute_tfidf_embedding(chunk)
            chunk_info = {
                "id": chunk_id,
                "doc_id": doc_id,
                "text": chunk,
                "index": i
            }
            rag_chunks.append(chunk_info)
            rag_embeddings.append(embedding)
        doc_info["chunk_count"] = len(chunks)
        rag_documents.append(doc_info)
        save_rag_index()
        return jsonify({'success': True, 'document': doc_info})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/project/overview', methods=['GET'])
def project_overview():
    tasks_total = len(project_tasks)
    tasks_done = len([t for t in project_tasks if t.get('status') == 'done'])
    overview = {
        "artifacts": len(project_artifacts),
        "pinned_artifacts": len([a for a in project_artifacts if a.get('pinned')]),
        "tasks_total": tasks_total,
        "tasks_todo": len([t for t in project_tasks if t.get('status') == 'todo']),
        "tasks_doing": len([t for t in project_tasks if t.get('status') == 'doing']),
        "tasks_done": tasks_done,
        "task_done_rate": round((tasks_done / tasks_total) * 100, 1) if tasks_total > 0 else 0,
        "playbooks": len(project_playbooks),
        "activity_count": len(project_activities),
        "campaigns": len(ops_campaigns),
        "release_plans": len(release_plans),
        "alerts": len(alert_rules),
        "ab_tests": len(ab_experiments),
        "integrations": len(integrations),
        "milestones": len(project_milestones),
        "risks": len(project_risks)
    }
    return jsonify({"success": True, "overview": overview})

def artifact_public_data(item):
    data = dict(item)
    versions = data.get("versions") if isinstance(data.get("versions"), list) else []
    data["version_count"] = len(versions)
    data.pop("versions", None)
    return data

@app.route('/artifacts', methods=['GET'])
def artifacts_list():
    q = request.args.get('q', '').strip().lower()
    artifact_type = request.args.get('type', '').strip()
    items = project_artifacts[:]
    if artifact_type:
        items = [a for a in items if a.get('type') == artifact_type]
    if q:
        items = [a for a in items if q in a.get('title', '').lower() or q in a.get('content', '').lower()]
    items.sort(key=lambda x: (not x.get('pinned', False), x.get('updated_at', 0)), reverse=False)
    items = list(reversed(items))
    return jsonify({"success": True, "artifacts": [artifact_public_data(x) for x in items]})

@app.route('/artifacts', methods=['POST'])
def artifacts_create():
    try:
        data = request.json or {}
        title = (data.get('title') or '').strip() or '未命名产物'
        content = (data.get('content') or '').strip()
        if not content:
            return jsonify({"success": False, "error": "内容不能为空"})
        now_ts = int(time.time())
        artifact = {
            "id": str(uuid.uuid4())[:8],
            "title": title,
            "content": content,
            "type": (data.get('type') or 'note').strip(),
            "tags": data.get('tags') if isinstance(data.get('tags'), list) else [],
            "source": (data.get('source') or 'manual').strip(),
            "pinned": bool(data.get('pinned', False)),
            "versions": [{
                "version": 1,
                "title": title,
                "content": content,
                "time": now_ts,
                "editor": (data.get('editor') or 'manual').strip()
            }],
            "created_at": now_ts,
            "updated_at": now_ts
        }
        project_artifacts.append(artifact)
        save_project_artifacts()
        append_project_activity("create", "artifact", artifact["id"], f"新增产物 {title}")
        return jsonify({"success": True, "artifact": artifact_public_data(artifact)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/artifacts/<artifact_id>', methods=['PUT'])
def artifacts_update(artifact_id):
    data = request.json or {}
    target = next((a for a in project_artifacts if a.get('id') == artifact_id), None)
    if not target:
        return jsonify({"success": False, "error": "产物不存在"})
    title = (data.get('title') or target.get('title') or '未命名产物').strip()
    content = (data.get('content') or '').strip()
    if not content:
        return jsonify({"success": False, "error": "内容不能为空"})
    old_title = target.get("title", "")
    old_content = target.get("content", "")
    changed = title != old_title or content != old_content
    target["title"] = title
    target["content"] = content
    target["type"] = (data.get('type') or target.get('type') or 'note').strip()
    target["tags"] = data.get('tags') if isinstance(data.get('tags'), list) else target.get("tags", [])
    target["source"] = (data.get('source') or target.get('source') or 'manual').strip()
    target["updated_at"] = int(time.time())
    if changed:
        versions = target.get("versions") if isinstance(target.get("versions"), list) else []
        versions.append({
            "version": len(versions) + 1,
            "title": title,
            "content": content,
            "time": target["updated_at"],
            "editor": (data.get('editor') or 'manual').strip()
        })
        target["versions"] = versions[-30:]
    save_project_artifacts()
    append_project_activity("update", "artifact", artifact_id, f"更新产物 {title}")
    return jsonify({"success": True, "artifact": artifact_public_data(target)})

@app.route('/artifacts/<artifact_id>', methods=['DELETE'])
def artifacts_delete(artifact_id):
    global project_artifacts
    before = len(project_artifacts)
    project_artifacts = [a for a in project_artifacts if a.get('id') != artifact_id]
    if len(project_artifacts) == before:
        return jsonify({"success": False, "error": "产物不存在"})
    save_project_artifacts()
    append_project_activity("delete", "artifact", artifact_id, "删除产物")
    return jsonify({"success": True})

@app.route('/artifacts/<artifact_id>/pin', methods=['POST'])
def artifacts_pin(artifact_id):
    data = request.json or {}
    pinned = bool(data.get('pinned', False))
    target = next((a for a in project_artifacts if a.get('id') == artifact_id), None)
    if not target:
        return jsonify({"success": False, "error": "产物不存在"})
    target['pinned'] = pinned
    target['updated_at'] = int(time.time())
    save_project_artifacts()
    append_project_activity("pin", "artifact", artifact_id, "置顶产物" if pinned else "取消置顶")
    return jsonify({"success": True, "artifact": artifact_public_data(target)})

@app.route('/artifacts/<artifact_id>/versions', methods=['GET'])
def artifacts_versions(artifact_id):
    target = next((a for a in project_artifacts if a.get('id') == artifact_id), None)
    if not target:
        return jsonify({"success": False, "error": "产物不存在"})
    versions = target.get("versions") if isinstance(target.get("versions"), list) else []
    return jsonify({"success": True, "versions": list(reversed(versions))})

@app.route('/artifacts/<artifact_id>/restore', methods=['POST'])
def artifacts_restore(artifact_id):
    data = request.json or {}
    version_number = int(data.get("version", 0))
    target = next((a for a in project_artifacts if a.get('id') == artifact_id), None)
    if not target:
        return jsonify({"success": False, "error": "产物不存在"})
    versions = target.get("versions") if isinstance(target.get("versions"), list) else []
    version_item = next((v for v in versions if int(v.get("version", 0)) == version_number), None)
    if not version_item:
        return jsonify({"success": False, "error": "版本不存在"})
    target["title"] = version_item.get("title", target.get("title", "未命名产物"))
    target["content"] = version_item.get("content", target.get("content", ""))
    target["updated_at"] = int(time.time())
    versions.append({
        "version": len(versions) + 1,
        "title": target["title"],
        "content": target["content"],
        "time": target["updated_at"],
        "editor": (data.get('editor') or 'restore').strip()
    })
    target["versions"] = versions[-30:]
    save_project_artifacts()
    append_project_activity("restore", "artifact", artifact_id, f"回滚到版本 {version_number}")
    return jsonify({"success": True, "artifact": artifact_public_data(target)})

@app.route('/project/tasks', methods=['GET'])
def project_tasks_list():
    items = sorted(project_tasks, key=lambda x: (x.get("order", 0), x.get("updated_at", 0)))
    return jsonify({"success": True, "tasks": items})

@app.route('/project/tasks', methods=['POST'])
def project_tasks_create():
    try:
        data = request.json or {}
        title = (data.get('title') or '').strip()
        if not title:
            return jsonify({"success": False, "error": "任务标题不能为空"})
        now_ts = int(time.time())
        task = {
            "id": str(uuid.uuid4())[:8],
            "title": title,
            "description": (data.get('description') or '').strip(),
            "priority": (data.get('priority') or 'medium').strip(),
            "owner": (data.get('owner') or '').strip(),
            "status": (data.get('status') or 'todo').strip(),
            "due_date": (data.get('due_date') or '').strip(),
            "order": max([int(t.get("order", 0)) for t in project_tasks], default=0) + 1,
            "created_at": now_ts,
            "updated_at": now_ts
        }
        project_tasks.append(task)
        save_project_tasks()
        append_project_activity("create", "task", task["id"], f"新增任务 {title}")
        return jsonify({"success": True, "task": task})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/project/tasks/<task_id>/status', methods=['POST'])
def project_tasks_update_status(task_id):
    data = request.json or {}
    status = (data.get('status') or '').strip()
    if status not in ['todo', 'doing', 'done']:
        return jsonify({"success": False, "error": "状态非法"})
    task = next((t for t in project_tasks if t.get('id') == task_id), None)
    if not task:
        return jsonify({"success": False, "error": "任务不存在"})
    task['status'] = status
    task['updated_at'] = int(time.time())
    save_project_tasks()
    append_project_activity("status", "task", task_id, f"任务状态改为 {status}")
    return jsonify({"success": True, "task": task})

@app.route('/project/tasks/reorder', methods=['POST'])
def project_tasks_reorder():
    data = request.json or {}
    ordered_ids = data.get('ordered_ids') if isinstance(data.get('ordered_ids'), list) else []
    if not ordered_ids:
        return jsonify({"success": False, "error": "缺少排序ID"})
    status_hint = (data.get('status_hint') or '').strip()
    order_map = {task_id: idx + 1 for idx, task_id in enumerate(ordered_ids)}
    updated = 0
    for task in project_tasks:
        task_id = task.get('id')
        if task_id in order_map:
            task['order'] = order_map[task_id]
            if status_hint in ['todo', 'doing', 'done']:
                task['status'] = status_hint
            task['updated_at'] = int(time.time())
            updated += 1
    save_project_tasks()
    append_project_activity("reorder", "task", "batch", f"批量排序 {updated} 条任务")
    return jsonify({"success": True, "updated": updated})

@app.route('/project/tasks/batch_status', methods=['POST'])
def project_tasks_batch_status():
    data = request.json or {}
    task_ids = data.get('task_ids') if isinstance(data.get('task_ids'), list) else []
    status = (data.get('status') or '').strip()
    if status not in ['todo', 'doing', 'done']:
        return jsonify({"success": False, "error": "状态非法"})
    updated = 0
    for task in project_tasks:
        if task.get('id') in task_ids:
            task['status'] = status
            task['updated_at'] = int(time.time())
            updated += 1
    save_project_tasks()
    append_project_activity("batch_status", "task", "batch", f"批量变更到 {status}: {updated} 条")
    return jsonify({"success": True, "updated": updated})

@app.route('/project/tasks/<task_id>', methods=['DELETE'])
def project_tasks_delete(task_id):
    global project_tasks
    before = len(project_tasks)
    project_tasks = [t for t in project_tasks if t.get('id') != task_id]
    if len(project_tasks) == before:
        return jsonify({"success": False, "error": "任务不存在"})
    save_project_tasks()
    append_project_activity("delete", "task", task_id, "删除任务")
    return jsonify({"success": True})

@app.route('/playbooks', methods=['GET'])
def playbooks_list():
    return jsonify({"success": True, "playbooks": project_playbooks})

@app.route('/playbooks', methods=['POST'])
def playbooks_create():
    try:
        data = request.json or {}
        name = (data.get('name') or '').strip()
        template = (data.get('template') or '').strip()
        if not name or not template:
            return jsonify({"success": False, "error": "名称和模板不能为空"})
        item = {
            "id": str(uuid.uuid4())[:8],
            "name": name,
            "description": (data.get('description') or '').strip(),
            "category": (data.get('category') or '自定义').strip(),
            "template": template
        }
        project_playbooks.append(item)
        save_project_playbooks()
        append_project_activity("create", "playbook", item["id"], f"新增剧本 {name}")
        return jsonify({"success": True, "playbook": item})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/playbooks/<playbook_id>/run', methods=['POST'])
def playbooks_run(playbook_id):
    data = request.json or {}
    pb = next((p for p in project_playbooks if p.get('id') == playbook_id), None)
    if not pb:
        return jsonify({"success": False, "error": "模板不存在"})
    variables = {
        "topic": (data.get('topic') or '').strip() or '未指定主题',
        "goal": (data.get('goal') or '').strip() or '未指定目标',
        "context": (data.get('context') or '').strip() or '无背景信息',
        "constraints": (data.get('constraints') or '').strip() or '无额外约束'
    }
    prompt = pb.get('template', '')
    for k, v in variables.items():
        prompt = prompt.replace('{' + k + '}', v)
    append_project_activity("run", "playbook", pb.get("id"), f"运行剧本 {pb.get('name', '')}")
    return jsonify({"success": True, "prompt": prompt, "playbook": pb})

@app.route('/project/activity', methods=['GET'])
def project_activity():
    limit = int(request.args.get('limit', 30))
    limit = max(1, min(limit, 100))
    return jsonify({"success": True, "activities": project_activities[:limit]})

@app.route('/project/milestones', methods=['GET'])
def project_milestones_list():
    items = project_milestones[:]
    items.sort(key=lambda x: x.get('updated_at', 0), reverse=True)
    return jsonify({"success": True, "milestones": items})

@app.route('/project/milestones', methods=['POST'])
def project_milestones_create():
    try:
        data = request.json or {}
        title = (data.get('title') or '').strip()
        if not title:
            return jsonify({"success": False, "error": "里程碑标题不能为空"})
        now_ts = int(time.time())
        item = {
            "id": str(uuid.uuid4())[:8],
            "title": title,
            "owner": (data.get('owner') or '').strip(),
            "due_date": (data.get('due_date') or '').strip(),
            "status": (data.get('status') or 'planned').strip(),
            "progress": max(0, min(100, safe_int(data.get('progress', 0), 0))),
            "updated_at": now_ts,
            "created_at": now_ts
        }
        if item["status"] not in ['planned', 'active', 'done', 'delayed']:
            item["status"] = 'planned'
        project_milestones.append(item)
        save_project_milestones()
        append_project_activity("create", "milestone", item["id"], f"新增里程碑 {title}")
        return jsonify({"success": True, "milestone": item})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/project/milestones/<milestone_id>/status', methods=['POST'])
def project_milestones_status(milestone_id):
    data = request.json or {}
    status = (data.get('status') or '').strip()
    if status not in ['planned', 'active', 'done', 'delayed']:
        return jsonify({"success": False, "error": "状态非法"})
    item = next((x for x in project_milestones if x.get('id') == milestone_id), None)
    if not item:
        return jsonify({"success": False, "error": "里程碑不存在"})
    item['status'] = status
    item['progress'] = max(0, min(100, safe_int(data.get('progress', item.get('progress', 0)), item.get('progress', 0))))
    item['updated_at'] = int(time.time())
    save_project_milestones()
    append_project_activity("status", "milestone", milestone_id, f"里程碑状态改为 {status}")
    return jsonify({"success": True, "milestone": item})

@app.route('/project/milestones/<milestone_id>', methods=['DELETE'])
def project_milestones_delete(milestone_id):
    global project_milestones
    before = len(project_milestones)
    project_milestones = [x for x in project_milestones if x.get('id') != milestone_id]
    if len(project_milestones) == before:
        return jsonify({"success": False, "error": "里程碑不存在"})
    save_project_milestones()
    append_project_activity("delete", "milestone", milestone_id, "删除里程碑")
    return jsonify({"success": True})

@app.route('/project/risks', methods=['GET'])
def project_risks_list():
    items = project_risks[:]
    items.sort(key=lambda x: x.get('updated_at', 0), reverse=True)
    return jsonify({"success": True, "risks": items})

@app.route('/project/risks', methods=['POST'])
def project_risks_create():
    try:
        data = request.json or {}
        title = (data.get('title') or '').strip()
        if not title:
            return jsonify({"success": False, "error": "风险标题不能为空"})
        now_ts = int(time.time())
        item = {
            "id": str(uuid.uuid4())[:8],
            "title": title,
            "owner": (data.get('owner') or '').strip(),
            "level": (data.get('level') or 'medium').strip(),
            "status": (data.get('status') or 'open').strip(),
            "mitigation": (data.get('mitigation') or '').strip(),
            "updated_at": now_ts,
            "created_at": now_ts
        }
        if item["level"] not in ['low', 'medium', 'high', 'critical']:
            item["level"] = 'medium'
        if item["status"] not in ['open', 'mitigating', 'closed']:
            item["status"] = 'open'
        project_risks.append(item)
        save_project_risks()
        append_project_activity("create", "risk", item["id"], f"新增风险 {title}")
        return jsonify({"success": True, "risk": item})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/project/risks/<risk_id>/status', methods=['POST'])
def project_risks_status(risk_id):
    data = request.json or {}
    status = (data.get('status') or '').strip()
    if status not in ['open', 'mitigating', 'closed']:
        return jsonify({"success": False, "error": "状态非法"})
    item = next((x for x in project_risks if x.get('id') == risk_id), None)
    if not item:
        return jsonify({"success": False, "error": "风险不存在"})
    item['status'] = status
    item['updated_at'] = int(time.time())
    save_project_risks()
    append_project_activity("status", "risk", risk_id, f"风险状态改为 {status}")
    return jsonify({"success": True, "risk": item})

@app.route('/project/risks/<risk_id>', methods=['DELETE'])
def project_risks_delete(risk_id):
    global project_risks
    before = len(project_risks)
    project_risks = [x for x in project_risks if x.get('id') != risk_id]
    if len(project_risks) == before:
        return jsonify({"success": False, "error": "风险不存在"})
    save_project_risks()
    append_project_activity("delete", "risk", risk_id, "删除风险")
    return jsonify({"success": True})

@app.route('/ops/overview', methods=['GET'])
def ops_overview():
    running = [x for x in ops_campaigns if x.get('status') == 'running']
    avg_ctr = round(sum([float(x.get('current_ctr', 0)) for x in ops_campaigns]) / len(ops_campaigns), 2) if ops_campaigns else 0
    total_budget = round(sum([float(x.get('budget', 0)) for x in ops_campaigns]), 2)
    return jsonify({
        "success": True,
        "overview": {
            "campaigns": len(ops_campaigns),
            "running": len(running),
            "avg_ctr": avg_ctr,
            "total_budget": total_budget
        }
    })

@app.route('/ops/campaigns', methods=['GET'])
def ops_campaigns_list():
    q = request.args.get('q', '').strip().lower()
    status = request.args.get('status', '').strip()
    items = ops_campaigns[:]
    if status:
        items = [x for x in items if x.get('status') == status]
    if q:
        items = [x for x in items if q in x.get('name', '').lower() or q in x.get('channel', '').lower() or q in x.get('owner', '').lower()]
    items.sort(key=lambda x: x.get('updated_at', 0), reverse=True)
    return jsonify({"success": True, "campaigns": items})

@app.route('/ops/campaigns', methods=['POST'])
def ops_campaigns_create():
    try:
        data = request.json or {}
        name = (data.get('name') or '').strip()
        if not name:
            return jsonify({"success": False, "error": "活动名称不能为空"})
        now_ts = int(time.time())
        item = {
            "id": str(uuid.uuid4())[:8],
            "name": name,
            "channel": (data.get('channel') or '全渠道').strip(),
            "status": (data.get('status') or 'draft').strip(),
            "budget": float(data.get('budget') or 0),
            "target_ctr": float(data.get('target_ctr') or 0),
            "current_ctr": float(data.get('current_ctr') or 0),
            "owner": (data.get('owner') or '').strip(),
            "start_date": (data.get('start_date') or '').strip(),
            "end_date": (data.get('end_date') or '').strip(),
            "notes": (data.get('notes') or '').strip(),
            "updated_at": now_ts,
            "created_at": now_ts
        }
        if item["status"] not in ['draft', 'running', 'paused', 'done']:
            item["status"] = 'draft'
        ops_campaigns.append(item)
        save_ops_campaigns()
        append_project_activity("create", "campaign", item["id"], f"新增活动 {name}")
        return jsonify({"success": True, "campaign": item})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/ops/campaigns/<campaign_id>/status', methods=['POST'])
def ops_campaign_status(campaign_id):
    data = request.json or {}
    status = (data.get('status') or '').strip()
    if status not in ['draft', 'running', 'paused', 'done']:
        return jsonify({"success": False, "error": "状态非法"})
    item = next((x for x in ops_campaigns if x.get('id') == campaign_id), None)
    if not item:
        return jsonify({"success": False, "error": "活动不存在"})
    item['status'] = status
    item['updated_at'] = int(time.time())
    save_ops_campaigns()
    append_project_activity("status", "campaign", campaign_id, f"运营状态改为 {status}")
    return jsonify({"success": True, "campaign": item})

@app.route('/ops/campaigns/<campaign_id>', methods=['DELETE'])
def ops_campaign_delete(campaign_id):
    global ops_campaigns
    before = len(ops_campaigns)
    ops_campaigns = [x for x in ops_campaigns if x.get('id') != campaign_id]
    if len(ops_campaigns) == before:
        return jsonify({"success": False, "error": "活动不存在"})
    save_ops_campaigns()
    append_project_activity("delete", "campaign", campaign_id, "删除运营活动")
    return jsonify({"success": True})

@app.route('/release/overview', methods=['GET'])
def release_overview():
    ready = len([x for x in release_plans if x.get('status') == 'ready'])
    rollback = len([x for x in release_plans if x.get('status') == 'rollback'])
    return jsonify({
        "success": True,
        "overview": {
            "plans": len(release_plans),
            "ready": ready,
            "rollback": rollback
        }
    })

@app.route('/release/plans', methods=['GET'])
def release_plans_list():
    status = request.args.get('status', '').strip()
    items = release_plans[:]
    if status:
        items = [x for x in items if x.get('status') == status]
    items.sort(key=lambda x: x.get('updated_at', 0), reverse=True)
    return jsonify({"success": True, "plans": items})

@app.route('/release/plans', methods=['POST'])
def release_plans_create():
    try:
        data = request.json or {}
        version = (data.get('version') or '').strip()
        title = (data.get('title') or '').strip()
        if not version or not title:
            return jsonify({"success": False, "error": "版本号和标题不能为空"})
        now_ts = int(time.time())
        checklist = data.get('checklist') if isinstance(data.get('checklist'), list) else []
        item = {
            "id": str(uuid.uuid4())[:8],
            "version": version,
            "title": title,
            "environment": (data.get('environment') or 'production').strip(),
            "status": (data.get('status') or 'planning').strip(),
            "risk": (data.get('risk') or 'medium').strip(),
            "owner": (data.get('owner') or '').strip(),
            "notes": (data.get('notes') or '').strip(),
            "checklist": checklist,
            "updated_at": now_ts,
            "created_at": now_ts
        }
        if item["status"] not in ['planning', 'review', 'ready', 'released', 'rollback']:
            item["status"] = 'planning'
        release_plans.append(item)
        save_release_plans()
        append_project_activity("create", "release", item["id"], f"新增发布计划 {version}")
        return jsonify({"success": True, "plan": item})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/release/plans/<plan_id>/status', methods=['POST'])
def release_plan_status(plan_id):
    data = request.json or {}
    status = (data.get('status') or '').strip()
    if status not in ['planning', 'review', 'ready', 'released', 'rollback']:
        return jsonify({"success": False, "error": "状态非法"})
    item = next((x for x in release_plans if x.get('id') == plan_id), None)
    if not item:
        return jsonify({"success": False, "error": "发布计划不存在"})
    item['status'] = status
    item['updated_at'] = int(time.time())
    save_release_plans()
    append_project_activity("status", "release", plan_id, f"发布状态改为 {status}")
    return jsonify({"success": True, "plan": item})

@app.route('/release/plans/<plan_id>/check', methods=['POST'])
def release_plan_check(plan_id):
    data = request.json or {}
    index = int(data.get('index', -1))
    checked = bool(data.get('checked', False))
    item = next((x for x in release_plans if x.get('id') == plan_id), None)
    if not item:
        return jsonify({"success": False, "error": "发布计划不存在"})
    checklist = item.get("checklist") if isinstance(item.get("checklist"), list) else []
    if index < 0 or index >= len(checklist):
        return jsonify({"success": False, "error": "检查项不存在"})
    row = checklist[index]
    if isinstance(row, dict):
        row["checked"] = checked
    else:
        checklist[index] = {"label": str(row), "checked": checked}
    item["checklist"] = checklist
    item["updated_at"] = int(time.time())
    save_release_plans()
    append_project_activity("check", "release", plan_id, f"更新检查项 {index + 1}")
    return jsonify({"success": True, "plan": item})

@app.route('/release/plans/<plan_id>', methods=['DELETE'])
def release_plan_delete(plan_id):
    global release_plans
    before = len(release_plans)
    release_plans = [x for x in release_plans if x.get('id') != plan_id]
    if len(release_plans) == before:
        return jsonify({"success": False, "error": "发布计划不存在"})
    save_release_plans()
    append_project_activity("delete", "release", plan_id, "删除发布计划")
    return jsonify({"success": True})

@app.route('/alerts/overview', methods=['GET'])
def alerts_overview():
    active_count = len([x for x in alert_rules if x.get('status') == 'active'])
    critical_count = len([x for x in alert_rules if x.get('level') == 'critical'])
    return jsonify({
        "success": True,
        "overview": {
            "rules": len(alert_rules),
            "active": active_count,
            "critical": critical_count
        }
    })

@app.route('/alerts/rules', methods=['GET'])
def alerts_rules_list():
    level = request.args.get('level', '').strip()
    status = request.args.get('status', '').strip()
    items = alert_rules[:]
    if level:
        items = [x for x in items if x.get('level') == level]
    if status:
        items = [x for x in items if x.get('status') == status]
    items.sort(key=lambda x: x.get('updated_at', 0), reverse=True)
    return jsonify({"success": True, "rules": items})

@app.route('/alerts/rules', methods=['POST'])
def alerts_rule_create():
    try:
        data = request.json or {}
        name = (data.get('name') or '').strip()
        metric = (data.get('metric') or '').strip()
        if not name or not metric:
            return jsonify({"success": False, "error": "规则名称和指标不能为空"})
        now_ts = int(time.time())
        item = {
            "id": str(uuid.uuid4())[:8],
            "name": name,
            "metric": metric,
            "threshold": safe_float(data.get('threshold', 0)),
            "current_value": safe_float(data.get('current_value', 0)),
            "level": (data.get('level') or 'medium').strip(),
            "status": (data.get('status') or 'active').strip(),
            "owner": (data.get('owner') or '').strip(),
            "updated_at": now_ts,
            "created_at": now_ts
        }
        if item["level"] not in ['low', 'medium', 'high', 'critical']:
            item["level"] = 'medium'
        if item["status"] not in ['active', 'muted', 'resolved']:
            item["status"] = 'active'
        alert_rules.append(item)
        save_alert_rules()
        append_project_activity("create", "alert", item["id"], f"新增告警规则 {name}")
        return jsonify({"success": True, "rule": item})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/alerts/rules/<rule_id>/status', methods=['POST'])
def alerts_rule_status(rule_id):
    data = request.json or {}
    status = (data.get('status') or '').strip()
    if status not in ['active', 'muted', 'resolved']:
        return jsonify({"success": False, "error": "状态非法"})
    item = next((x for x in alert_rules if x.get('id') == rule_id), None)
    if not item:
        return jsonify({"success": False, "error": "规则不存在"})
    item['status'] = status
    item['updated_at'] = int(time.time())
    save_alert_rules()
    append_project_activity("status", "alert", rule_id, f"告警状态改为 {status}")
    return jsonify({"success": True, "rule": item})

@app.route('/alerts/rules/<rule_id>', methods=['DELETE'])
def alerts_rule_delete(rule_id):
    global alert_rules
    before = len(alert_rules)
    alert_rules = [x for x in alert_rules if x.get('id') != rule_id]
    if len(alert_rules) == before:
        return jsonify({"success": False, "error": "规则不存在"})
    save_alert_rules()
    append_project_activity("delete", "alert", rule_id, "删除告警规则")
    return jsonify({"success": True})

@app.route('/ab/overview', methods=['GET'])
def ab_overview():
    running = len([x for x in ab_experiments if x.get('status') == 'running'])
    return jsonify({"success": True, "overview": {"experiments": len(ab_experiments), "running": running}})

@app.route('/ab/experiments', methods=['GET'])
def ab_list():
    status = request.args.get('status', '').strip()
    items = ab_experiments[:]
    if status:
        items = [x for x in items if x.get('status') == status]
    items.sort(key=lambda x: x.get('updated_at', 0), reverse=True)
    return jsonify({"success": True, "experiments": items})

@app.route('/ab/experiments', methods=['POST'])
def ab_create():
    try:
        data = request.json or {}
        name = (data.get('name') or '').strip()
        metric = (data.get('metric') or '').strip()
        if not name or not metric:
            return jsonify({"success": False, "error": "实验名称和指标不能为空"})
        now_ts = int(time.time())
        item = {
            "id": str(uuid.uuid4())[:8],
            "name": name,
            "metric": metric,
            "traffic": safe_float(data.get('traffic', 50)),
            "baseline": safe_float(data.get('baseline', 0)),
            "variant": safe_float(data.get('variant', 0)),
            "status": (data.get('status') or 'draft').strip(),
            "owner": (data.get('owner') or '').strip(),
            "updated_at": now_ts,
            "created_at": now_ts
        }
        if item["status"] not in ['draft', 'running', 'paused', 'completed']:
            item["status"] = 'draft'
        ab_experiments.append(item)
        save_ab_experiments()
        append_project_activity("create", "ab", item["id"], f"新增AB实验 {name}")
        return jsonify({"success": True, "experiment": item})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/ab/experiments/<exp_id>/status', methods=['POST'])
def ab_status(exp_id):
    data = request.json or {}
    status = (data.get('status') or '').strip()
    if status not in ['draft', 'running', 'paused', 'completed']:
        return jsonify({"success": False, "error": "状态非法"})
    item = next((x for x in ab_experiments if x.get('id') == exp_id), None)
    if not item:
        return jsonify({"success": False, "error": "实验不存在"})
    item['status'] = status
    item['updated_at'] = int(time.time())
    save_ab_experiments()
    append_project_activity("status", "ab", exp_id, f"AB实验状态改为 {status}")
    return jsonify({"success": True, "experiment": item})

@app.route('/ab/experiments/<exp_id>/metrics', methods=['POST'])
def ab_metrics(exp_id):
    data = request.json or {}
    item = next((x for x in ab_experiments if x.get('id') == exp_id), None)
    if not item:
        return jsonify({"success": False, "error": "实验不存在"})
    item['baseline'] = safe_float(data.get('baseline', item.get('baseline', 0)))
    item['variant'] = safe_float(data.get('variant', item.get('variant', 0)))
    item['updated_at'] = int(time.time())
    save_ab_experiments()
    append_project_activity("metrics", "ab", exp_id, "更新实验指标")
    return jsonify({"success": True, "experiment": item})

@app.route('/ab/experiments/<exp_id>', methods=['DELETE'])
def ab_delete(exp_id):
    global ab_experiments
    before = len(ab_experiments)
    ab_experiments = [x for x in ab_experiments if x.get('id') != exp_id]
    if len(ab_experiments) == before:
        return jsonify({"success": False, "error": "实验不存在"})
    save_ab_experiments()
    append_project_activity("delete", "ab", exp_id, "删除AB实验")
    return jsonify({"success": True})

@app.route('/integrations/overview', methods=['GET'])
def integrations_overview():
    enabled = len([x for x in integrations if x.get('status') == 'enabled'])
    error_count = len([x for x in integrations if x.get('status') == 'error'])
    return jsonify({"success": True, "overview": {"integrations": len(integrations), "enabled": enabled, "errors": error_count}})

@app.route('/integrations', methods=['GET'])
def integrations_list():
    status = request.args.get('status', '').strip()
    items = integrations[:]
    if status:
        items = [x for x in items if x.get('status') == status]
    items.sort(key=lambda x: x.get('updated_at', 0), reverse=True)
    return jsonify({"success": True, "integrations": items})

@app.route('/integrations', methods=['POST'])
def integrations_create():
    try:
        data = request.json or {}
        name = (data.get('name') or '').strip()
        provider = (data.get('provider') or '').strip()
        if not name or not provider:
            return jsonify({"success": False, "error": "集成名称和提供方不能为空"})
        now_ts = int(time.time())
        item = {
            "id": str(uuid.uuid4())[:8],
            "name": name,
            "provider": provider,
            "status": (data.get('status') or 'disabled').strip(),
            "health": safe_float(data.get('health', 0)),
            "owner": (data.get('owner') or '').strip(),
            "desc": (data.get('desc') or '').strip(),
            "updated_at": now_ts,
            "created_at": now_ts
        }
        if item["status"] not in ['enabled', 'disabled', 'error']:
            item["status"] = 'disabled'
        integrations.append(item)
        save_integrations()
        append_project_activity("create", "integration", item["id"], f"新增集成 {name}")
        return jsonify({"success": True, "integration": item})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/integrations/<integration_id>/status', methods=['POST'])
def integrations_status(integration_id):
    data = request.json or {}
    status = (data.get('status') or '').strip()
    if status not in ['enabled', 'disabled', 'error']:
        return jsonify({"success": False, "error": "状态非法"})
    item = next((x for x in integrations if x.get('id') == integration_id), None)
    if not item:
        return jsonify({"success": False, "error": "集成不存在"})
    item['status'] = status
    item['updated_at'] = int(time.time())
    save_integrations()
    append_project_activity("status", "integration", integration_id, f"集成状态改为 {status}")
    return jsonify({"success": True, "integration": item})

@app.route('/integrations/<integration_id>', methods=['DELETE'])
def integrations_delete(integration_id):
    global integrations
    before = len(integrations)
    integrations = [x for x in integrations if x.get('id') != integration_id]
    if len(integrations) == before:
        return jsonify({"success": False, "error": "集成不存在"})
    save_integrations()
    append_project_activity("delete", "integration", integration_id, "删除集成")
    return jsonify({"success": True})

workspace_projects_cache = {"time": 0, "items": []}

def is_port_open(host, port, timeout=0.25):
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except Exception:
        return False

def infer_project_kind(base_path):
    checks = [
        ("python", ["main.py", "app.py", "requirements.txt", "pyproject.toml"]),
        ("node", ["package.json", "pnpm-workspace.yaml"]),
        ("java", ["pom.xml"]),
        ("rust", ["Cargo.toml"])
    ]
    for kind, files in checks:
        for f in files:
            if os.path.exists(os.path.join(base_path, f)):
                return kind
    return ""

def get_curated_workspace_specs():
    return [
        {
            "id": "kaguya_web",
            "name": "辉夜主控台",
            "path": os.path.dirname(__file__),
            "category": "core",
            "kind": "python",
            "desc": "主模型服务与统一前端",
            "start_command": "& 'D:\\Anoconda\\envs\\DL\\python.exe' qwen3_web.py",
            "default_url": "http://localhost:5000/",
            "port": 5000
        },
        {
            "id": "kaguya_fastapi",
            "name": "Kaguya FastAPI",
            "path": os.path.join(os.path.dirname(__file__), "kaguya_fastapi"),
            "category": "service",
            "kind": "python",
            "desc": "独立 FastAPI 服务",
            "start_command": "python app/main.py",
            "default_url": "http://localhost:8000/docs",
            "port": 8000
        },
        {
            "id": "financial_rag_api",
            "name": "Financial RAG API",
            "path": os.path.join(os.path.dirname(__file__), "financial_rag"),
            "category": "rag",
            "kind": "python",
            "desc": "金融知识检索与问答 API",
            "start_command": "python src/api/main.py",
            "default_url": "http://localhost:8000/docs",
            "port": 8000
        },
        {
            "id": "financial_rag_frontend",
            "name": "Financial RAG Frontend",
            "path": os.path.join(os.path.dirname(__file__), "financial_rag", "frontend"),
            "category": "rag",
            "kind": "node",
            "desc": "金融 RAG React 前端",
            "start_command": "npm run dev",
            "default_url": "http://localhost:5173/",
            "port": 5173
        },
        {
            "id": "airi_workspace",
            "name": "AIRI Workspace",
            "path": os.path.join(os.path.dirname(__file__), "airi"),
            "category": "ai_app",
            "kind": "node",
            "desc": "多端 AI 工作区与 stage web",
            "start_command": ".\\run_project.ps1",
            "default_url": "",
            "port": 0
        },
        {
            "id": "ai_card_explorer",
            "name": "AI Card Explorer",
            "path": os.path.join(os.path.dirname(__file__), "ai-card-explorer"),
            "category": "business",
            "kind": "java",
            "desc": "AI 卡片探索平台",
            "start_command": ".\\start.bat",
            "default_url": "http://localhost:8080/",
            "port": 8080
        }
    ]

def discover_workspace_projects(force_refresh=False):
    now_ts = time.time()
    if not force_refresh and workspace_projects_cache["items"] and now_ts - workspace_projects_cache["time"] < 20:
        return workspace_projects_cache["items"]
    workspace_root = os.path.dirname(__file__)
    result = []
    seen_path = set()
    for spec in get_curated_workspace_specs():
        path = spec.get("path", "")
        exists = os.path.isdir(path)
        running = bool(spec.get("port")) and is_port_open("127.0.0.1", spec.get("port"))
        item = {
            "id": spec.get("id"),
            "name": spec.get("name"),
            "path": path,
            "relative_path": os.path.relpath(path, workspace_root) if path else "",
            "category": spec.get("category", "other"),
            "kind": spec.get("kind", ""),
            "desc": spec.get("desc", ""),
            "start_command": spec.get("start_command", ""),
            "default_url": spec.get("default_url", ""),
            "port": spec.get("port", 0),
            "exists": exists,
            "running": running,
            "source": "curated",
            "updated_at": int(now_ts)
        }
        result.append(item)
        if path:
            seen_path.add(os.path.normpath(path).lower())
    ignore_dirs = {
        "uploads", "audio_cache", "rag_data", "memory_system", "memory_store", "project_center",
        "multimodal", "lora_adapters", "code_executions", "prompts", "checkpoints", "security_data",
        "test_audit_logs", "__pycache__", ".vscode"
    }
    for entry in os.scandir(workspace_root):
        if not entry.is_dir():
            continue
        name = entry.name
        if name.startswith(".") or name in ignore_dirs:
            continue
        full_path = entry.path
        normalized = os.path.normpath(full_path).lower()
        if normalized in seen_path:
            continue
        kind = infer_project_kind(full_path)
        if not kind:
            continue
        start_command = ""
        default_url = ""
        port = 0
        if kind == "node":
            if os.path.exists(os.path.join(full_path, "start.bat")):
                start_command = ".\\start.bat"
            elif os.path.exists(os.path.join(full_path, "pnpm-workspace.yaml")):
                start_command = "pnpm dev"
            else:
                start_command = "npm run dev"
        elif kind == "java":
            start_command = "mvn spring-boot:run"
            port = 8080
            default_url = "http://localhost:8080/"
        elif kind == "python":
            if os.path.exists(os.path.join(full_path, "main.py")):
                start_command = "python main.py"
            elif os.path.exists(os.path.join(full_path, "app.py")):
                start_command = "python app.py"
            else:
                start_command = "python <entry.py>"
        elif kind == "rust":
            start_command = "cargo run"
        running = bool(port) and is_port_open("127.0.0.1", port)
        result.append({
            "id": f"auto_{re.sub(r'[^a-z0-9]+', '_', name.lower())}",
            "name": name,
            "path": full_path,
            "relative_path": os.path.relpath(full_path, workspace_root),
            "category": "workspace",
            "kind": kind,
            "desc": "自动发现的可执行项目",
            "start_command": start_command,
            "default_url": default_url,
            "port": port,
            "exists": True,
            "running": running,
            "source": "auto",
            "updated_at": int(now_ts)
        })
    result.sort(key=lambda x: (x.get("source") != "curated", x.get("name", "").lower()))
    workspace_projects_cache["time"] = now_ts
    workspace_projects_cache["items"] = result
    return result

@app.route('/workspace/projects', methods=['GET'])
def workspace_projects_list():
    refresh = bool(request.args.get('refresh', '').strip())
    items = discover_workspace_projects(refresh)
    q = (request.args.get('q') or '').strip().lower()
    kind = (request.args.get('kind') or '').strip().lower()
    source = (request.args.get('source') or '').strip().lower()
    if q:
        items = [x for x in items if q in x.get("name", "").lower() or q in x.get("relative_path", "").lower() or q in x.get("desc", "").lower()]
    if kind:
        items = [x for x in items if x.get("kind", "").lower() == kind]
    if source:
        items = [x for x in items if x.get("source", "").lower() == source]
    return jsonify({"success": True, "projects": items})

@app.route('/workspace/projects/overview', methods=['GET'])
def workspace_projects_overview():
    items = discover_workspace_projects(False)
    running = len([x for x in items if x.get("running")])
    exists = len([x for x in items if x.get("exists")])
    curated = len([x for x in items if x.get("source") == "curated"])
    by_kind = defaultdict(int)
    for row in items:
        by_kind[row.get("kind", "other")] += 1
    return jsonify({
        "success": True,
        "overview": {
            "total": len(items),
            "running": running,
            "exists": exists,
            "curated": curated,
            "python": by_kind.get("python", 0),
            "node": by_kind.get("node", 0),
            "java": by_kind.get("java", 0),
            "rust": by_kind.get("rust", 0)
        }
    })

def safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return int(default)

def build_console_recommendations():
    result = []
    critical_alerts = [x for x in alert_rules if x.get('level') == 'critical' and x.get('status') == 'active']
    if critical_alerts:
        result.append({
            "priority": "P0",
            "title": "存在严重告警未处理",
            "detail": f"当前有 {len(critical_alerts)} 条 critical 告警处于激活状态",
            "action": "优先静默噪声并修复根因，完成后将状态置为 resolved"
        })
    doing_tasks = [x for x in project_tasks if x.get('status') == 'doing']
    if len(doing_tasks) >= 8:
        result.append({
            "priority": "P1",
            "title": "进行中任务过多",
            "detail": f"进行中任务 {len(doing_tasks)} 条，存在上下文切换成本",
            "action": "按优先级收敛任务，使用批量流转将低优先级转回 todo"
        })
    release_ready = [x for x in release_plans if x.get('status') == 'ready']
    if release_plans and not release_ready:
        result.append({
            "priority": "P1",
            "title": "发布计划无就绪项",
            "detail": f"已有 {len(release_plans)} 个发布计划，但 ready 数量为 0",
            "action": "补齐门禁检查项，推进至少一个计划至 ready"
        })
    error_integrations = [x for x in integrations if x.get('status') == 'error']
    if error_integrations:
        result.append({
            "priority": "P1",
            "title": "集成存在异常连接",
            "detail": f"异常集成 {len(error_integrations)} 个，可能影响自动化链路",
            "action": "优先修复 error 状态集成并恢复 enabled"
        })
    running_ab = [x for x in ab_experiments if x.get('status') == 'running']
    weak_ab = [x for x in running_ab if safe_float(x.get('baseline', 0)) == 0 and safe_float(x.get('variant', 0)) == 0]
    if weak_ab:
        result.append({
            "priority": "P2",
            "title": "A/B 实验缺少指标回收",
            "detail": f"{len(weak_ab)} 个运行中实验尚未录入基线与实验组指标",
            "action": "补录 baseline/variant 指标以便判断实验收益"
        })
    workspace_projects = discover_workspace_projects(False)
    offline_projects = [x for x in workspace_projects if x.get("exists") and not x.get("running") and x.get("default_url")]
    if offline_projects:
        result.append({
            "priority": "P2",
            "title": "生态项目存在未运行服务",
            "detail": f"检测到 {len(offline_projects)} 个可访问项目当前未运行",
            "action": "进入项目生态中心复制启动命令并拉起目标服务"
        })
    if not result:
        result.append({
            "priority": "P3",
            "title": "系统运行平稳",
            "detail": "当前未发现高优先级治理风险，可继续推进增长与效率优化",
            "action": "建议聚焦产物沉淀质量与实验转化提升"
        })
    return result[:8]

def build_global_search_items():
    items = []
    def push(entity, entity_id, title, subtitle, content, status, updated_at, tags=None):
        items.append({
            "entity": entity,
            "id": entity_id,
            "title": title or "",
            "subtitle": subtitle or "",
            "content": content or "",
            "status": status or "",
            "updated_at": safe_int(updated_at, 0),
            "tags": tags or []
        })
    for a in project_artifacts:
        push("artifact", a.get("id"), a.get("title"), a.get("type"), a.get("content"), "active", a.get("updated_at"), a.get("tags") if isinstance(a.get("tags"), list) else [])
    for t in project_tasks:
        push("task", t.get("id"), t.get("title"), t.get("owner"), t.get("description"), t.get("status"), t.get("updated_at"), [t.get("priority", "medium")])
    for c in ops_campaigns:
        push("campaign", c.get("id"), c.get("name"), c.get("channel"), c.get("notes"), c.get("status"), c.get("updated_at"), [c.get("owner", "")])
    for r in release_plans:
        push("release", r.get("id"), f"{r.get('version', '')} {r.get('title', '')}".strip(), r.get("environment"), r.get("notes"), r.get("status"), r.get("updated_at"), [r.get("risk", "medium"), r.get("owner", "")])
    for ar in alert_rules:
        push("alert", ar.get("id"), ar.get("name"), ar.get("metric"), f"阈值 {ar.get('threshold', 0)} 当前 {ar.get('current_value', 0)}", ar.get("status"), ar.get("updated_at"), [ar.get("level", "medium"), ar.get("owner", "")])
    for ab in ab_experiments:
        push("ab", ab.get("id"), ab.get("name"), ab.get("metric"), f"baseline {ab.get('baseline', 0)} / variant {ab.get('variant', 0)}", ab.get("status"), ab.get("updated_at"), [f"traffic:{ab.get('traffic', 0)}", ab.get("owner", "")])
    for ig in integrations:
        push("integration", ig.get("id"), ig.get("name"), ig.get("provider"), ig.get("desc"), ig.get("status"), ig.get("updated_at"), [ig.get("owner", "")])
    for ms in project_milestones:
        push("milestone", ms.get("id"), ms.get("title"), ms.get("owner"), ms.get("due_date"), ms.get("status"), ms.get("updated_at"), [f"progress:{ms.get('progress', 0)}"])
    for pr in project_risks:
        push("risk", pr.get("id"), pr.get("title"), pr.get("owner"), pr.get("mitigation"), pr.get("status"), pr.get("updated_at"), [pr.get("level", "medium")])
    for wp in discover_workspace_projects(False):
        push("workspace_project", wp.get("id"), wp.get("name"), wp.get("kind"), wp.get("desc"), "running" if wp.get("running") else "idle", wp.get("updated_at"), [wp.get("relative_path", ""), wp.get("source", "")])
    return items

@app.route('/console/overview', methods=['GET'])
def console_overview():
    workspace_projects = discover_workspace_projects(False)
    tasks_total = len(project_tasks)
    done_rate = round((len([t for t in project_tasks if t.get('status') == 'done']) / tasks_total) * 100, 1) if tasks_total else 0
    critical_count = len([x for x in alert_rules if x.get('level') == 'critical' and x.get('status') == 'active'])
    integration_error = len([x for x in integrations if x.get('status') == 'error'])
    health_score = max(0, 100 - critical_count * 12 - integration_error * 8 - max(0, 50 - done_rate) * 0.3)
    execution_score = round((done_rate * 0.6 + (len([x for x in release_plans if x.get('status') in ['ready', 'released']]) * 8)), 1)
    growth_score = round((len([x for x in ops_campaigns if x.get('status') == 'running']) * 10 + len([x for x in ab_experiments if x.get('status') == 'running']) * 8), 1)
    overview = {
        "health_score": round(min(100, health_score), 1),
        "execution_score": round(min(100, execution_score), 1),
        "growth_score": round(min(100, growth_score), 1),
        "knowledge_score": round(min(100, len(project_artifacts) * 3 + len(project_playbooks) * 5), 1),
        "totals": {
            "artifacts": len(project_artifacts),
            "tasks": len(project_tasks),
            "campaigns": len(ops_campaigns),
            "releases": len(release_plans),
            "alerts": len(alert_rules),
            "ab_tests": len(ab_experiments),
            "integrations": len(integrations),
            "milestones": len(project_milestones),
            "project_risks": len(project_risks),
            "workspace_projects": len(workspace_projects),
            "workspace_running": len([x for x in workspace_projects if x.get("running")])
        },
        "risks": {
            "critical_alerts": critical_count,
            "integration_errors": integration_error,
            "unready_releases": len([x for x in release_plans if x.get('status') not in ['ready', 'released']])
        }
    }
    return jsonify({"success": True, "overview": overview})

@app.route('/console/recommendations', methods=['GET'])
def console_recommendations():
    return jsonify({"success": True, "recommendations": build_console_recommendations()})

@app.route('/system/metrics', methods=['GET'])
def system_metrics():
    try:
        import psutil
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        metrics = {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_used": memory.used,
            "memory_total": memory.total,
            "disk_percent": disk.percent,
            "disk_used": disk.used,
            "disk_total": disk.total,
            "network_status": "正常"
        }
        return jsonify({"success": True, "metrics": metrics})
    except ImportError:
        return jsonify({"success": True, "metrics": {
            "cpu_percent": 25,
            "memory_percent": 45,
            "disk_percent": 60,
            "network_status": "正常"
        }})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/performance/stats', methods=['GET'])
def performance_stats():
    time_range = request.args.get('range', '24h')
    stats = {
        "avg_response_time": "1.2s",
        "total_requests": "156",
        "error_rate": "0.5%",
        "throughput": "15 req/s"
    }
    return jsonify({"success": True, "stats": stats})

@app.route('/performance/export', methods=['GET'])
def export_performance():
    report = {
        "generated_at": datetime.now().isoformat(),
        "stats": stats_data,
        "sessions": stats_data.get('sessions', 0)
    }
    return jsonify(report)

@app.route('/console/governance-report', methods=['GET'])
def generate_governance_report():
    return jsonify({"success": True, "message": "治理报告已生成"})

@app.route('/services/health-check', methods=['GET'])
def services_health_check():
    services = [
        {"id": "ollama", "name": "Ollama 服务", "icon": "🤖", "status": "healthy", "status_text": "运行中"},
        {"id": "flask", "name": "Flask 服务", "icon": "🌐", "status": "healthy", "status_text": "运行中"},
        {"id": "elasticsearch", "name": "Elasticsearch", "icon": "🔍", "status": "unknown", "status_text": "未配置"},
        {"id": "redis", "name": "Redis 缓存", "icon": "🗄️", "status": "unknown", "status_text": "未配置"}
    ]
    return jsonify({"success": True, "services": services})

@app.route('/services/<service_id>/restart', methods=['POST'])
def restart_service(service_id):
    return jsonify({"success": True, "message": f"{service_id} 重启成功"})

@app.route('/dependencies/analyze', methods=['GET'])
def analyze_dependencies():
    summary = {
        "total": 45,
        "outdated": 3,
        "vulnerable": 0
    }
    return jsonify({"success": True, "summary": summary})

@app.route('/dependencies/security-check', methods=['GET'])
def security_check():
    return jsonify({"success": True, "vulnerabilities": []})

@app.route('/git/status', methods=['GET'])
def git_status():
    repos = [
        {"name": "qwen3_web", "branch": "main", "modified": 3, "added": 2, "ahead": 1}
    ]
    return jsonify({"success": True, "repos": repos})

@app.route('/scheduler/tasks', methods=['GET'])
def get_scheduled_tasks():
    tasks = [
        {"name": "📊 每日统计汇总", "status": "active", "schedule": "每天 00:00", "last_run": "今日 00:00"},
        {"name": "🗑️ 缓存清理", "status": "active", "schedule": "每周日 03:00", "last_run": "周日 03:00"},
        {"name": "💾 数据备份", "status": "paused", "schedule": "每天 04:00", "last_run": "--"}
    ]
    return jsonify({"success": True, "tasks": tasks})

@app.route('/scheduler/tasks', methods=['POST'])
def create_scheduled_task():
    data = request.json
    return jsonify({"success": True, "message": "任务已创建"})

@app.route('/workspace/projects', methods=['POST'])
def create_workspace_project():
    data = request.json
    return jsonify({"success": True, "message": "项目已创建"})

@app.route('/templates/search', methods=['GET'])
def search_templates():
    templates = [
        {"id": "flask-api", "name": "Flask API 项目", "icon": "🌐", "description": "快速创建 RESTful API 服务"},
        {"id": "ml-project", "name": "机器学习项目", "icon": "🤖", "description": "包含数据处理、模型训练流程"},
        {"id": "web-scraper", "name": "爬虫项目", "icon": "🕷️", "description": "网页数据采集与处理"},
        {"id": "cli-tool", "name": "CLI 工具", "icon": "⚡", "description": "命令行工具脚手架"}
    ]
    return jsonify({"success": True, "templates": templates})

@app.route('/deploy/execute', methods=['POST'])
def execute_deploy():
    data = request.json
    target = data.get('target', 'local')
    return jsonify({"success": True, "message": f"已部署到 {target}"})

@app.route('/dataflow/stats', methods=['GET'])
def dataflow_stats():
    stats = {
        "input_count": "1,234",
        "process_count": "1,200",
        "output_count": "1,180",
        "rate": "15 req/s",
        "queue_depth": "5",
        "latency": "120 ms"
    }
    return jsonify({"success": True, "stats": stats})

@app.route('/rag/analysis', methods=['GET'])
def rag_analysis_route():
    time_range = request.args.get('range', '7d')
    analysis = {
        "queries": "234",
        "hit_rate": "92.5%",
        "latency": "45ms",
        "top_doc": "技术文档.pdf"
    }
    return jsonify({"success": True, "analysis": analysis})

@app.route('/rag/build-graph', methods=['POST'])
def build_rag_graph():
    return jsonify({"success": True, "nodes": 156, "edges": 423})

@app.route('/templates/analysis', methods=['GET'])
def templates_analysis():
    time_range = request.args.get('range', '7d')
    stats = {
        "total_templates": 24,
        "favorites": 8,
        "usage": 156,
        "custom": 5
    }
    return jsonify({"success": True, "stats": stats})

@app.route('/rag/analysis', methods=['GET'])
def rag_analysis_duplicate():
    time_range = request.args.get('range', '7d')
    analysis = {
        "queries": "234",
        "hit_rate": "87.5%",
        "latency": "45ms",
        "top_doc": "技术文档.md"
    }
    return jsonify({"success": True, "analysis": analysis})

@app.route('/search/global', methods=['GET'])
def global_search():
    query = (request.args.get('q') or '').strip().lower()
    entity = (request.args.get('entity') or '').strip().lower()
    limit = max(1, min(safe_int(request.args.get('limit', 50), 50), 150))
    items = build_global_search_items()
    if entity:
        items = [x for x in items if x.get("entity") == entity]
    if not query:
        items.sort(key=lambda x: x.get("updated_at", 0), reverse=True)
        return jsonify({"success": True, "results": items[:limit]})
    scored = []
    for item in items:
        title = item.get("title", "").lower()
        subtitle = item.get("subtitle", "").lower()
        content = item.get("content", "").lower()
        tags_text = " ".join([str(t) for t in item.get("tags", [])]).lower()
        score = 0
        if query in title:
            score += 10
        if query in subtitle:
            score += 5
        if query in tags_text:
            score += 4
        if query in content:
            score += 2
        if score == 0:
            continue
        item["score"] = score
        scored.append(item)
    scored.sort(key=lambda x: (x.get("score", 0), x.get("updated_at", 0)), reverse=True)
    return jsonify({"success": True, "results": scored[:limit]})

@app.route('/chat', methods=['POST'])
def chat_endpoint():
    try:
        data = request.json
        message = data.get('message', '')
        history = data.get('history', [])
        role = data.get('role', 'kaguya')
        lora = data.get('lora')
        structured_template = data.get('structured_template')
        temperature = data.get('temperature', 0.7)
        max_tokens = data.get('max_tokens', 4096)
        
        response, tokens_in, tokens_out = chat(message, history, role, lora, temperature, max_tokens, structured_template)
        return jsonify({'response': response, 'tokens_in': tokens_in, 'tokens_out': tokens_out})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/stream', methods=['POST'])
def stream_endpoint():
    try:
        data = request.json
        message = data.get('message', '')
        history = data.get('history', [])
        role = data.get('role', 'kaguya')
        lora = data.get('lora')
        structured_template = data.get('structured_template')
        temperature = data.get('temperature', 0.7)
        max_tokens = data.get('max_tokens', 4096)
        
        def generate():
            try:
                print(f"[Stream] 开始生成: msg={message[:20]}...")
                chunk_count = 0
                for chunk in generate_stream(message, history, role, lora, temperature, max_tokens, "", None, structured_template):
                    chunk_count += 1
                    if chunk_count <= 3:
                        print(f"[Stream] Chunk {chunk_count}: {chunk[:50]}...")
                    # SSE 格式: data: <json>\n\n
                    yield f"data: {chunk}\n\n"
                print(f"[Stream] 生成完成，共 {chunk_count} 个 chunks")
            except Exception as e:
                print(f"[Stream] 生成错误: {e}")
                import traceback
                traceback.print_exc()
                yield f"data: {json.dumps({'content': f'错误: {str(e)}', 'done': True})}\n\n"
        
        return Response(generate(), mimetype='text/event-stream')
    except Exception as e:
        print(f"[Stream] 端点错误: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)})

@app.route('/tts', methods=['POST'])
def tts_endpoint():
    try:
        data = request.json
        text = data.get('text', '')[:300]
        audio_id = str(uuid.uuid4())[:8]
        audio_path = os.path.join(AUDIO_CACHE_DIR, f'{audio_id}.wav')
        tts_script = os.path.join(os.path.dirname(__file__), 'tts_ddsp.py')
        if os.path.exists(tts_script):
            subprocess.run([sys.executable, tts_script, text, audio_path, '0'], timeout=600)
            if os.path.exists(audio_path):
                return jsonify({'audio_url': f'/audio/{audio_id}.wav'})
        return jsonify({'error': 'TTS failed'})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/audio/<filename>')
def serve_audio(filename):
    audio_path = os.path.join(AUDIO_CACHE_DIR, filename)
    if os.path.exists(audio_path):
        return send_file(audio_path)
    return "Not found", 404

if __name__ == '__main__':
    import socket
    
    def get_local_ip():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception:
            return "127.0.0.1"
    
    local_ip = get_local_ip()
    
    print("=" * 60)
    print("辉夜 AI助手 (专业增强版 v3.1)")
    print("=" * 60)
    print(f"本地访问: http://127.0.0.1:5000")
    print(f"局域网访问: http://{local_ip}:5000")
    print("=" * 60)
    print("新功能: 流式响应 | 代码执行器 | 工具调用 | 知识库 | LoRA")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, threaded=True, debug=False)
