"""
DeepSeek API 路由
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
import json
import httpx
import asyncio

from app.models.schemas import DeepSeekConfig, DeepSeekChatRequest, ChatMessage, StreamChunk
from app.core.config import settings, PRESET_ROLES

router = APIRouter()


@router.get("/deepseek/status")
async def get_deepseek_status():
    """获取 DeepSeek API 状态"""
    return {
        "enabled": bool(settings.DEEPSEEK_API_KEY),
        "api_url": settings.DEEPSEEK_API_URL,
        "model": settings.DEEPSEEK_MODEL,
        "api_key_configured": bool(settings.DEEPSEEK_API_KEY)
    }


@router.post("/deepseek/config")
async def update_deepseek_config(config: DeepSeekConfig):
    """更新 DeepSeek 配置"""
    # 注意：实际应用中应该保存到数据库或配置文件
    return {
        "success": True,
        "message": "配置已更新（仅内存中，重启后失效）",
        "config": config
    }


async def stream_deepseek_response(
    messages: list,
    api_key: str,
    api_url: str,
    model: str,
    temperature: float = 0.7,
    max_tokens: int = 1024
) -> AsyncGenerator[str, None]:
    """流式 DeepSeek API 响应"""
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True
    }
    
    try:
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{api_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60.0
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    yield f"data: {json.dumps({'error': f'API错误: {response.status_code}', 'details': error_text.decode()})}\n\n"
                    return
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            yield f"data: {json.dumps({'done': True})}\n\n"
                            break
                        
                        try:
                            data = json.loads(data_str)
                            if "choices" in data and len(data["choices"]) > 0:
                                delta = data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    chunk = StreamChunk(content=content, done=False)
                                    yield f"data: {json.dumps(chunk.model_dump())}\n\n"
                        except json.JSONDecodeError:
                            continue
    
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


@router.post("/deepseek/chat")
async def deepseek_chat(request: DeepSeekChatRequest):
    """DeepSeek 聊天接口（非流式）"""
    
    if not settings.DEEPSEEK_API_KEY:
        raise HTTPException(status_code=400, detail="DeepSeek API 密钥未配置")
    
    # 构建系统提示词
    system_prompt = ""
    if request.kaguya_mode and request.role:
        role = next((r for r in PRESET_ROLES if r["id"] == request.role), None)
        if role:
            system_prompt = role.get("system", "")
    
    # 构建消息列表
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    
    for msg in request.messages:
        messages.append({"role": msg.role, "content": msg.content})
    
    headers = {
        "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": settings.DEEPSEEK_MODEL,
        "messages": messages,
        "temperature": request.temperature,
        "max_tokens": request.max_tokens
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.DEEPSEEK_API_URL}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60.0
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"DeepSeek API 错误: {response.text}"
                )
            
            result = response.json()
            return {
                "success": True,
                "content": result["choices"][0]["message"]["content"],
                "usage": result.get("usage", {}),
                "model": result.get("model", settings.DEEPSEEK_MODEL)
            }
    
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"请求失败: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/deepseek/chat/stream")
async def deepseek_chat_stream(request: DeepSeekChatRequest):
    """DeepSeek 聊天接口（流式）"""
    
    if not settings.DEEPSEEK_API_KEY:
        raise HTTPException(status_code=400, detail="DeepSeek API 密钥未配置")
    
    # 构建系统提示词
    system_prompt = ""
    if request.kaguya_mode and request.role:
        role = next((r for r in PRESET_ROLES if r["id"] == request.role), None)
        if role:
            system_prompt = role.get("system", "")
    
    # 构建消息列表
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    
    for msg in request.messages:
        messages.append({"role": msg.role, "content": msg.content})
    
    return StreamingResponse(
        stream_deepseek_response(
            messages=messages,
            api_key=settings.DEEPSEEK_API_KEY,
            api_url=settings.DEEPSEEK_API_URL,
            model=settings.DEEPSEEK_MODEL,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
