"""
记忆系统API
"""

from fastapi import APIRouter, HTTPException
from typing import List
import uuid
from datetime import datetime

from app.models.schemas import MemoryEntry, MemoryQuery, ResponseBase

router = APIRouter()

# 模拟记忆存储
memory_db = {}


@router.post("/memory", response_model=ResponseBase)
async def create_memory(content: str, importance: float = 0.5):
    """创建记忆"""
    memory_id = str(uuid.uuid4())
    
    memory_db[memory_id] = {
        "id": memory_id,
        "content": content,
        "importance": importance,
        "created_at": datetime.now(),
        "last_accessed": None,
        "access_count": 0
    }
    
    return ResponseBase(
        success=True,
        message="记忆已创建",
        data={"id": memory_id}
    )


@router.get("/memory", response_model=List[MemoryEntry])
async def list_memories(
    limit: int = 10,
    min_importance: float = 0.0
):
    """获取记忆列表"""
    memories = [
        MemoryEntry(**m) for m in memory_db.values()
        if m["importance"] >= min_importance
    ]
    
    # 按重要性和访问次数排序
    memories.sort(
        key=lambda x: (x.importance, x.access_count),
        reverse=True
    )
    
    return memories[:limit]


@router.post("/memory/query")
async def query_memories(query: MemoryQuery):
    """查询相关记忆"""
    # 简单的关键词匹配（实际应使用向量搜索）
    results = []
    
    for memory in memory_db.values():
        if query.query.lower() in memory["content"].lower():
            if memory["importance"] >= query.min_importance:
                # 更新访问统计
                memory["access_count"] += 1
                memory["last_accessed"] = datetime.now()
                
                results.append(MemoryEntry(**memory))
    
    # 限制返回数量
    results = results[:query.limit]
    
    return {
        "query": query.query,
        "results": results,
        "total": len(results)
    }


@router.get("/memory/{memory_id}", response_model=MemoryEntry)
async def get_memory(memory_id: str):
    """获取记忆详情"""
    memory = memory_db.get(memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail="记忆不存在")
    
    # 更新访问统计
    memory["access_count"] += 1
    memory["last_accessed"] = datetime.now()
    
    return MemoryEntry(**memory)


@router.delete("/memory/{memory_id}")
async def delete_memory(memory_id: str):
    """删除记忆"""
    if memory_id not in memory_db:
        raise HTTPException(status_code=404, detail="记忆不存在")
    
    del memory_db[memory_id]
    return {"success": True, "message": "记忆已删除"}


@router.get("/memory/stats")
async def get_memory_stats():
    """获取记忆统计"""
    if not memory_db:
        return {
            "total_memories": 0,
            "average_importance": 0,
            "total_accesses": 0
        }
    
    total = len(memory_db)
    avg_importance = sum(m["importance"] for m in memory_db.values()) / total
    total_accesses = sum(m["access_count"] for m in memory_db.values())
    
    return {
        "total_memories": total,
        "average_importance": round(avg_importance, 2),
        "total_accesses": total_accesses
    }
