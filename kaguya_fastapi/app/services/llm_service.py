"""
LLM服务 - 统一的大语言模型接口
"""

from typing import List, Dict, Any, Optional, AsyncGenerator
import httpx
import json
import os

from app.core.config import settings

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")


class LLMService:
    """LLM服务类"""

    def __init__(self):
        self.model_name = settings.DEFAULT_MODEL
        self.temperature = settings.DEFAULT_TEMPERATURE
        self.max_tokens = settings.DEFAULT_MAX_TOKENS
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(120.0))
        return self._client

    async def _try_ollama(self, messages: List[Dict[str, str]]) -> Optional[Dict[str, Any]]:
        try:
            client = await self._get_client()
            resp = await client.post(
                f"{OLLAMA_HOST}/api/chat",
                json={"model": self.model_name, "messages": messages, "stream": False,
                      "options": {"temperature": self.temperature}},
                timeout=60.0
            )
            if resp.status_code == 200:
                data = resp.json()
                return {"content": data.get("message", {}).get("content", ""),
                        "usage": {"prompt_tokens": data.get("prompt_eval_count", 0),
                                  "completion_tokens": data.get("eval_count", 0)},
                        "finish_reason": data.get("done_reason", "stop")}
        except Exception:
            pass
        return None

    async def generate(
        self,
        message: str,
        history: List[Dict[str, str]] = None,
        system_prompt: str = "",
        temperature: float = None,
        max_tokens: int = None
    ) -> Dict[str, Any]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": message})

        result = await self._try_ollama(messages)
        if result:
            return result

        if settings.DEEPSEEK_API_KEY:
            try:
                return await self.chat_with_deepseek(
                    messages, settings.DEEPSEEK_API_KEY,
                    settings.DEEPSEEK_API_URL, settings.DEEPSEEK_MODEL,
                    temperature or self.temperature, max_tokens or self.max_tokens
                )
            except Exception:
                pass

        return {
            "content": f"[注意] 未检测到本地模型或API配置。您的消息: {message[:200]}",
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "finish_reason": "no_model_available"
        }

    async def generate_stream(
        self,
        message: str,
        history: List[Dict[str, str]] = None,
        system_prompt: str = "",
        temperature: float = None,
        max_tokens: int = None
    ) -> AsyncGenerator[str, None]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": message})

        try:
            client = await self._get_client()
            async with client.stream(
                "POST", f"{OLLAMA_HOST}/api/chat",
                json={"model": self.model_name, "messages": messages, "stream": True,
                      "options": {"temperature": temperature or self.temperature}},
                timeout=120.0
            ) as resp:
                if resp.status_code == 200:
                    async for line in resp.aiter_lines():
                        if not line:
                            continue
                        try:
                            chunk = json.loads(line)
                            content = chunk.get("message", {}).get("content", "")
                            if content:
                                yield content
                            if chunk.get("done"):
                                break
                        except json.JSONDecodeError:
                            continue
                    return
        except Exception:
            pass

        fallback = f"[注意] 未检测到本地模型。您的消息: {message[:200]}"
        yield fallback

    async def chat_with_deepseek(
        self,
        messages: List[Dict[str, str]],
        api_key: str,
        api_url: str = "https://api.deepseek.com",
        model: str = "deepseek-chat",
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> Dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        client = await self._get_client()
        response = await client.post(
            f"{api_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=120.0
        )
        response.raise_for_status()
        result = response.json()
        return {
            "content": result["choices"][0]["message"]["content"],
            "usage": result.get("usage", {}),
            "model": result.get("model", model)
        }
