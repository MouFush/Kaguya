"""
聊天API - 流式响应支持
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
import json

from app.models.schemas import ChatRequest, ChatResponse, StreamChunk
from app.services.llm_service import LLMService
from app.core.config import PRESET_ROLES, settings

router = APIRouter()
llm_service = LLMService()


async def stream_chat_response(request: ChatRequest) -> AsyncGenerator[str, None]:
    """流式聊天响应生成器"""
    try:
        system_prompt = ""
        if request.role:
            role = next((r for r in PRESET_ROLES if r["id"] == request.role), None)
            if role:
                system_prompt = role.get("system", "")

        chunk_index = 0
        async for content in llm_service.generate_stream(
            message=request.message,
            history=[msg.model_dump() for msg in request.history],
            system_prompt=system_prompt,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        ):
            chunk_size = settings.STREAM_CHUNK_SIZE
            for i in range(0, len(content), chunk_size):
                chunk = content[i:i + chunk_size]
                data = StreamChunk(
                    content=chunk,
                    done=False,
                    index=chunk_index
                )
                yield f"data: {json.dumps(data.model_dump())}\n\n"
                chunk_index += 1

        data = StreamChunk(content="", done=True, index=chunk_index)
        yield f"data: {json.dumps(data.model_dump())}\n\n"

    except Exception as e:
        yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """非流式聊天接口"""
    try:
        # 构建系统提示词
        system_prompt = ""
        if request.role:
            role = next((r for r in PRESET_ROLES if r["id"] == request.role), None)
            if role:
                system_prompt = role.get("system", "")
        
        # 调用LLM服务
        response = await llm_service.generate(
            message=request.message,
            history=[msg.model_dump() for msg in request.history],
            system_prompt=system_prompt,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        
        return ChatResponse(
            content=response["content"],
            usage=response.get("usage"),
            finish_reason=response.get("finish_reason")
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """流式聊天接口"""
    return StreamingResponse(
        stream_chat_response(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/chat/models")
async def get_available_models():
    """获取可用模型列表"""
    return {
        "models": [
            {"id": "qwen3.5-9b", "name": "Qwen3.5-9B", "type": "local"},
            {"id": "deepseek-chat", "name": "DeepSeek Chat", "type": "api"},
            {"id": "deepseek-reasoner", "name": "DeepSeek Reasoner", "type": "api"}
        ]
    }
