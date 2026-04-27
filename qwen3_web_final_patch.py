#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全修复补丁 - 用于修复 qwen3_web_final.py 的安全漏洞
"""

import re

def apply_security_patches():
    """应用安全修复"""
    
    # 读取原文件
    with open('qwen3_web_final.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    patches_applied = []
    
    # 1. 修复 eval() 安全漏洞
    if 'lambda x: str(eval(x.replace("^", "**")))' in content:
        content = content.replace(
            'lambda x: str(eval(x.replace("^", "**")))',
            'lambda x: str(safe_eval(x.replace("^", "**")))'
        )
        patches_applied.append("✓ 修复 eval() 安全漏洞")
    
    # 2. 添加 RAG 锁保护（在全局变量定义后）
    if 'rag_doc_hashes = set()' in content and 'rag_lock = threading.RLock()' not in content:
        content = content.replace(
            'rag_doc_hashes = set()',
            'rag_doc_hashes = set()\n\n# RAG数据锁，用于线程安全\nrag_lock = threading.RLock()'
        )
        patches_applied.append("✓ 添加 RAG 线程锁")
    
    # 3. 修复 load_rag_index 函数
    old_load = '''def load_rag_index():
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
            rag_documents, rag_chunks, rag_embeddings, rag_doc_hashes = [], [], [], set()'''
    
    new_load = '''def load_rag_index():
    global rag_documents, rag_chunks, rag_embeddings, rag_doc_hashes
    if os.path.exists(RAG_INDEX_FILE):
        try:
            with open(RAG_INDEX_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            with rag_lock:
                rag_documents = data.get('documents', [])
                rag_chunks = data.get('chunks', [])
                rag_embeddings = data.get('embeddings', [])
                rag_doc_hashes = set(data.get('doc_hashes', []))
            print(f"RAG索引已加载: {len(rag_documents)}文档, {len(rag_chunks)}分块")
        except Exception as e:
            print(f"加载RAG索引失败: {e}")
            with rag_lock:
                rag_documents, rag_chunks, rag_embeddings, rag_doc_hashes = [], [], [], set()'''
    
    if old_load in content:
        content = content.replace(old_load, new_load)
        patches_applied.append("✓ 修复 load_rag_index 线程安全")
    
    # 4. 修复 save_rag_index 函数
    old_save = '''def save_rag_index():
    try:
        with open(RAG_INDEX_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                'documents': rag_documents,
                'chunks': rag_chunks,
                'embeddings': rag_embeddings,
                'doc_hashes': list(rag_doc_hashes)
            }, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存RAG索引失败: {e}")'''
    
    new_save = '''def save_rag_index():
    try:
        with rag_lock:
            data = {
                'documents': rag_documents,
                'chunks': rag_chunks,
                'embeddings': rag_embeddings,
                'doc_hashes': list(rag_doc_hashes)
            }
        with open(RAG_INDEX_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存RAG索引失败: {e}")'''
    
    if old_save in content:
        content = content.replace(old_save, new_save)
        patches_applied.append("✓ 修复 save_rag_index 线程安全")
    
    # 5. 修复 get_rag_stats 函数
    old_stats = '''def get_rag_stats():
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
    }'''
    
    new_stats = '''def get_rag_stats():
    global rag_documents, rag_chunks, rag_cache
    with rag_lock:
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
        }'''
    
    if old_stats in content:
        content = content.replace(old_stats, new_stats)
        patches_applied.append("✓ 修复 get_rag_stats 线程安全")
    
    # 6. 修复 delete_document_from_rag 函数
    old_delete = '''def delete_document_from_rag(doc_id):
    global rag_documents, rag_chunks, rag_embeddings, rag_doc_hashes
    doc = next((d for d in rag_documents if d['id'] == doc_id), None)
    if doc and doc.get('hash') in rag_doc_hashes:
        rag_doc_hashes.remove(doc.get('hash'))
    rag_documents = [d for d in rag_documents if d['id'] != doc_id]
    chunks_to_remove = [i for i, c in enumerate(rag_chunks) if c['doc_id'] == doc_id]
    for i in reversed(chunks_to_remove):
        rag_chunks.pop(i)
        rag_embeddings.pop(i)
    save_rag_index()
    return True'''
    
    new_delete = '''def delete_document_from_rag(doc_id):
    global rag_documents, rag_chunks, rag_embeddings, rag_doc_hashes
    with rag_lock:
        doc = next((d for d in rag_documents if d['id'] == doc_id), None)
        if doc and doc.get('hash') in rag_doc_hashes:
            rag_doc_hashes.remove(doc.get('hash'))
        rag_documents = [d for d in rag_documents if d['id'] != doc_id]
        chunks_to_remove = [i for i, c in enumerate(rag_chunks) if c['doc_id'] == doc_id]
        for i in reversed(chunks_to_remove):
            rag_chunks.pop(i)
            rag_embeddings.pop(i)
    save_rag_index()
    return True'''
    
    if old_delete in content:
        content = content.replace(old_delete, new_delete)
        patches_applied.append("✓ 修复 delete_document_from_rag 线程安全")
    
    # 保存修复后的文件
    with open('qwen3_web_final.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    return patches_applied

if __name__ == '__main__':
    print("应用安全修复补丁...")
    patches = apply_security_patches()
    if patches:
        print("\n已应用的修复:")
        for patch in patches:
            print(f"  {patch}")
        print("\n✅ 安全修复完成!")
    else:
        print("\n⚠️ 未找到需要修复的内容，可能已修复或文件结构不同")
