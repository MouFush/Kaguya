"""
Kaguya Unified API Adapter - 通用API接入解决方案
=================================================
统一的接口规范、可扩展的厂商适配层、标准化的请求/响应格式、
完善的错误处理机制以及清晰的接入文档。

支持厂商: OpenAI, Claude(Anthropic), DeepSeek, Kimi(Moonshot),
          GLM(Zhipu), Gemini, Mistral, Groq, XAI, Ollama(本地)
"""

import json
import urllib.request
import urllib.error
import time as _time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Iterator, Any, Union
from enum import Enum


class ProviderType(Enum):
    OPENAI_COMPATIBLE = "openai_compatible"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    OLLAMA = "ollama"


class APIError(Exception):
    """统一API错误基类"""
    def __init__(self, message: str, code: str = "unknown", status_code: int = 0, raw_response: str = ""):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.raw_response = raw_response

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": True,
            "code": self.code,
            "message": self.message,
            "status_code": self.status_code,
            "raw": self.raw_response[:500] if self.raw_response else ""
        }


class AuthError(APIError):
    """认证错误 (401/403)"""
    def __init__(self, message: str, status_code: int = 401, raw_response: str = ""):
        super().__init__(message, "auth_error", status_code, raw_response)


class RateLimitError(APIError):
    """速率限制错误 (429)"""
    def __init__(self, message: str, raw_response: str = ""):
        super().__init__(message, "rate_limit", 429, raw_response)


class TimeoutError(APIError):
    """超时错误"""
    def __init__(self, message: str, raw_response: str = ""):
        super().__init__(message, "timeout", 0, raw_response)


class ModelError(APIError):
    """模型相关错误"""
    def __init__(self, message: str, status_code: int = 0, raw_response: str = ""):
        super().__init__(message, "model_error", status_code, raw_response)


@dataclass
class Message:
    """标准化消息格式"""
    role: str
    content: str
    name: Optional[str] = None
    tool_calls: Optional[List[Dict]] = None
    tool_call_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {"role": self.role, "content": self.content}
        if self.name:
            d["name"] = self.name
        if self.tool_calls:
            d["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        return d


@dataclass
class ToolSchema:
    """工具/函数定义Schema"""
    name: str
    description: str
    parameters: Dict[str, Any]

    def to_openai(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }

    def to_anthropic(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.parameters
        }


@dataclass
class StreamChunk:
    """标准化流式响应块"""
    content: str = ""
    tool_calls: Optional[List[Dict]] = None
    finish_reason: Optional[str] = None
    usage: Optional[Dict[str, int]] = None
    is_thinking: bool = False
    model: str = ""


@dataclass
class ChatResponse:
    """标准化聊天响应"""
    content: str = ""
    tool_calls: Optional[List[Dict]] = None
    finish_reason: str = ""
    usage: Dict[str, int] = field(default_factory=dict)
    model: str = ""
    provider: str = ""


@dataclass
class ProviderConfig:
    """厂商配置"""
    provider_id: str
    display_name: str
    provider_type: ProviderType
    base_url: str
    default_model: str
    api_key_header: str = "Authorization"
    api_key_prefix: str = "Bearer "
    supports_tools: bool = True
    supports_streaming: bool = True
    max_tokens_default: int = 4096
    temperature_default: float = 0.3
    request_timeout: int = 30
    read_timeout: int = 60
    extra_headers: Dict[str, str] = field(default_factory=dict)
    chat_endpoint: str = "/chat/completions"


class BaseProviderAdapter(ABC):
    """厂商适配器基类 - 所有厂商适配器必须继承"""

    def __init__(self, config: ProviderConfig):
        self.config = config
        self._last_read_time = 0.0

    @abstractmethod
    def build_request(self, messages: List[Message], tools: Optional[List[ToolSchema]] = None,
                      stream: bool = True, **kwargs) -> tuple:
        """
        构建HTTP请求
        返回: (url: str, data: bytes, headers: dict)
        """
        pass

    @abstractmethod
    def parse_stream_chunk(self, line: str) -> Optional[StreamChunk]:
        """解析流式响应的一行数据"""
        pass

    @abstractmethod
    def parse_response(self, raw_data: bytes) -> ChatResponse:
        """解析非流式完整响应"""
        pass

    def _get_auth_header(self, api_key: str) -> Dict[str, str]:
        """获取认证头"""
        if self.config.api_key_header == "Authorization":
            return {self.config.api_key_header: f"{self.config.api_key_prefix}{api_key}"}
        return {self.config.api_key_header: api_key}

    def _make_request(self, url: str, data: bytes, headers: Dict[str, str],
                      timeout: int = 30) -> urllib.request.addinfourl:
        """发送HTTP请求并返回响应对象"""
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        return urllib.request.urlopen(req, timeout=timeout)

    def _handle_http_error(self, e: urllib.error.HTTPError, provider: str) -> None:
        """统一处理HTTP错误"""
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            body = str(e)

        if e.code in (401, 403):
            raise AuthError(
                f"API authentication failed for {provider} (HTTP {e.code}). Please check your API key.",
                e.code, body
            )
        elif e.code == 429:
            raise RateLimitError(
                f"Rate limit exceeded for {provider}. Please wait and try again.",
                body
            )
        elif e.code >= 500:
            raise APIError(
                f"Server error from {provider} (HTTP {e.code}). The service may be temporarily unavailable.",
                "server_error", e.code, body
            )
        else:
            raise APIError(
                f"HTTP error from {provider}: {e.code} - {body[:300]}",
                "http_error", e.code, body
            )

    def stream_chat(self, messages: List[Message], api_key: str,
                    tools: Optional[List[ToolSchema]] = None,
                    model: Optional[str] = None, **kwargs) -> Iterator[StreamChunk]:
        """
        流式聊天 - 统一入口
        """
        url, data, headers = self.build_request(
            messages, tools, stream=True, model=model, **kwargs
        )
        headers.update(self._get_auth_header(api_key))

        try:
            resp = self._make_request(url, data, headers, self.config.request_timeout)
        except urllib.error.HTTPError as e:
            self._handle_http_error(e, self.config.provider_id)
            return
        except urllib.error.URLError as e:
            raise APIError(f"Connection error: {e.reason}", "connection_error", 0, str(e))
        except Exception as e:
            raise APIError(f"Request failed: {str(e)}", "request_error", 0, str(e))

        self._last_read_time = _time.time()
        try:
            while True:
                if _time.time() - self._last_read_time > self.config.read_timeout:
                    raise TimeoutError(f"Read timeout: no data for {self.config.read_timeout}s")

                line = resp.readline()
                if not line:
                    break

                self._last_read_time = _time.time()
                line_str = line.decode("utf-8", errors="replace").strip()

                if not line_str:
                    continue

                chunk = self.parse_stream_chunk(line_str)
                if chunk:
                    chunk.model = model or self.config.default_model
                    yield chunk

                if chunk and chunk.finish_reason:
                    break
        finally:
            try:
                resp.close()
            except Exception:
                pass

    def chat(self, messages: List[Message], api_key: str,
             tools: Optional[List[ToolSchema]] = None,
             model: Optional[str] = None, **kwargs) -> ChatResponse:
        """
        非流式聊天 - 统一入口
        """
        url, data, headers = self.build_request(
            messages, tools, stream=False, model=model, **kwargs
        )
        headers.update(self._get_auth_header(api_key))

        try:
            resp = self._make_request(url, data, headers, self.config.request_timeout)
            raw = resp.read()
            resp.close()
            result = self.parse_response(raw)
            result.provider = self.config.provider_id
            result.model = model or self.config.default_model
            return result
        except urllib.error.HTTPError as e:
            self._handle_http_error(e, self.config.provider_id)
        except urllib.error.URLError as e:
            raise APIError(f"Connection error: {e.reason}", "connection_error", 0, str(e))
        except Exception as e:
            raise APIError(f"Request failed: {str(e)}", "request_error", 0, str(e))

        return ChatResponse()


class OpenAICompatibleAdapter(BaseProviderAdapter):
    """OpenAI兼容适配器 - 适用于绝大多数厂商"""

    def build_request(self, messages: List[Message], tools: Optional[List[ToolSchema]] = None,
                      stream: bool = True, **kwargs) -> tuple:
        model = kwargs.get("model") or self.config.default_model
        max_tokens = kwargs.get("max_tokens", self.config.max_tokens_default)
        temperature = kwargs.get("temperature", self.config.temperature_default)

        base_url = self.config.base_url.rstrip("/")
        if self.config.chat_endpoint.startswith("/"):
            url = base_url + self.config.chat_endpoint
        else:
            url = base_url + "/" + self.config.chat_endpoint

        payload = {
            "model": model,
            "messages": [m.to_dict() for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
        }

        if tools and self.config.supports_tools:
            payload["tools"] = [t.to_openai() for t in tools]

        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            **self.config.extra_headers
        }
        return url, data, headers

    def parse_stream_chunk(self, line: str) -> Optional[StreamChunk]:
        if not line.startswith("data: "):
            return None
        chunk_data = line[6:].strip()
        if chunk_data == "[DONE]":
            return StreamChunk(finish_reason="stop")

        try:
            cd = json.loads(chunk_data)
            choice = cd.get("choices", [{}])[0]
            delta = choice.get("delta", {})
            content = delta.get("content", "") or ""

            tool_calls = []
            tc_list = delta.get("tool_calls", [])
            for tci in tc_list:
                idx = tci.get("index", 0)
                while len(tool_calls) <= idx:
                    tool_calls.append({"id": "", "name": "", "arguments": ""})
                if tci.get("id"):
                    tool_calls[idx]["id"] = tci["id"]
                if tci.get("function"):
                    fn = tci["function"]
                    if fn.get("name"):
                        tool_calls[idx]["name"] = fn["name"]
                    if fn.get("arguments"):
                        tool_calls[idx]["arguments"] += fn["arguments"]

            finish = choice.get("finish_reason")
            return StreamChunk(
                content=content,
                tool_calls=tool_calls if tool_calls else None,
                finish_reason=finish,
                is_thinking=bool(content)
            )
        except (json.JSONDecodeError, IndexError, KeyError):
            return None

    def parse_response(self, raw_data: bytes) -> ChatResponse:
        try:
            data = json.loads(raw_data.decode("utf-8"))
            choice = data.get("choices", [{}])[0]
            message = choice.get("message", {})
            content = message.get("content", "")
            tool_calls = message.get("tool_calls")
            usage = data.get("usage", {})
            return ChatResponse(
                content=content,
                tool_calls=tool_calls,
                finish_reason=choice.get("finish_reason", ""),
                usage=usage,
                model=data.get("model", "")
            )
        except (json.JSONDecodeError, IndexError, KeyError) as e:
            raise ModelError(f"Failed to parse response: {e}", raw_response=raw_data.decode("utf-8", errors="replace")[:500])


class AnthropicAdapter(BaseProviderAdapter):
    """Anthropic Claude适配器"""

    def build_request(self, messages: List[Message], tools: Optional[List[ToolSchema]] = None,
                      stream: bool = True, **kwargs) -> tuple:
        model = kwargs.get("model") or self.config.default_model
        max_tokens = kwargs.get("max_tokens", self.config.max_tokens_default)

        url = self.config.base_url.rstrip("/")
        if "/v1/messages" not in url:
            url = url + "/v1/messages"

        system_content = ""
        clean_msgs = list(messages)
        if clean_msgs and clean_msgs[0].role == "system":
            system_content = clean_msgs.pop(0).content

        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "stream": stream,
            "messages": [{"role": m.role, "content": m.content} for m in clean_msgs if m.role != "system"]
        }
        if system_content:
            payload["system"] = system_content

        if tools and self.config.supports_tools:
            payload["tools"] = [t.to_anthropic() for t in tools]

        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
            **self.config.extra_headers
        }
        return url, data, headers

    def parse_stream_chunk(self, line: str) -> Optional[StreamChunk]:
        if not line.startswith("data: "):
            return None
        chunk_data = line[6:].strip()
        if chunk_data == "[DONE]":
            return StreamChunk(finish_reason="stop")

        try:
            cd = json.loads(chunk_data)
            evt = cd.get("type", "")
            if evt == "content_block_delta":
                delta = cd.get("delta", {})
                content = delta.get("text", "")
                return StreamChunk(content=content, is_thinking=True) if content else None
            elif evt == "message_stop":
                return StreamChunk(finish_reason="stop")
            return None
        except (json.JSONDecodeError, KeyError):
            return None

    def parse_response(self, raw_data: bytes) -> ChatResponse:
        try:
            data = json.loads(raw_data.decode("utf-8"))
            content_blocks = data.get("content", [])
            content = "".join([b.get("text", "") for b in content_blocks if b.get("type") == "text"])
            usage = data.get("usage", {})
            return ChatResponse(
                content=content,
                finish_reason=data.get("stop_reason", ""),
                usage=usage,
                model=data.get("model", "")
            )
        except (json.JSONDecodeError, KeyError) as e:
            raise ModelError(f"Failed to parse Claude response: {e}", raw_response=raw_data.decode("utf-8", errors="replace")[:500])


class GeminiAdapter(BaseProviderAdapter):
    """Google Gemini适配器"""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._genai = None
        try:
            import google.generativeai as genai
            self._genai = genai
        except ImportError:
            pass

    def build_request(self, messages: List[Message], tools: Optional[List[ToolSchema]] = None,
                      stream: bool = True, **kwargs) -> tuple:
        return "", b"", {}

    def parse_stream_chunk(self, line: str) -> Optional[StreamChunk]:
        return None

    def parse_response(self, raw_data: bytes) -> ChatResponse:
        return ChatResponse()

    def stream_chat(self, messages: List[Message], api_key: str,
                    tools: Optional[List[ToolSchema]] = None,
                    model: Optional[str] = None, **kwargs) -> Iterator[StreamChunk]:
        if self._genai is None:
            raise APIError("google.generativeai not installed. Install with: pip install google-generativeai", "missing_dependency")

        self._genai.configure(api_key=api_key)
        gm = (model or self.config.default_model).split("/")[-1].replace(":generateContent", "")
        gen_model = self._genai.GenerativeModel(gm)

        system_content = ""
        clean_msgs = list(messages)
        if clean_msgs and clean_msgs[0].role == "system":
            system_content = clean_msgs.pop(0).content

        history = []
        for m in clean_msgs[:-1]:
            role = "user" if m.role == "user" else "model"
            history.append({"role": role, "parts": [m.content]})

        chat = gen_model.start_chat(history=history)
        last_msg = clean_msgs[-1].content if clean_msgs else "hi"

        response = chat.send_message(last_msg, stream=True)
        for chunk in response:
            text = chunk.text if hasattr(chunk, "text") else ""
            if text:
                yield StreamChunk(content=text, is_thinking=True, model=gm)

        yield StreamChunk(finish_reason="stop", model=gm)

    def chat(self, messages: List[Message], api_key: str,
             tools: Optional[List[ToolSchema]] = None,
             model: Optional[str] = None, **kwargs) -> ChatResponse:
        content = ""
        for chunk in self.stream_chat(messages, api_key, tools, model, **kwargs):
            if chunk.finish_reason:
                break
            content += chunk.content
        return ChatResponse(content=content, finish_reason="stop", model=model or self.config.default_model)


# ============================================================
# 预定义厂商配置
# ============================================================

PROVIDER_REGISTRY: Dict[str, ProviderConfig] = {
    "deepseek": ProviderConfig(
        provider_id="deepseek",
        display_name="DeepSeek",
        provider_type=ProviderType.OPENAI_COMPATIBLE,
        base_url="https://api.deepseek.com",
        default_model="deepseek-chat",
        chat_endpoint="/chat/completions",
        supports_tools=True,
        supports_streaming=True
    ),
    "openai": ProviderConfig(
        provider_id="openai",
        display_name="OpenAI",
        provider_type=ProviderType.OPENAI_COMPATIBLE,
        base_url="https://api.openai.com/v1",
        default_model="gpt-4o",
        chat_endpoint="/chat/completions",
        supports_tools=True,
        supports_streaming=True
    ),
    "claude": ProviderConfig(
        provider_id="claude",
        display_name="Claude (Anthropic)",
        provider_type=ProviderType.ANTHROPIC,
        base_url="https://api.anthropic.com",
        default_model="claude-3-7-sonnet-20250219",
        api_key_header="x-api-key",
        api_key_prefix="",
        supports_tools=True,
        supports_streaming=True,
        extra_headers={"anthropic-version": "2023-06-01"}
    ),
    "kimi": ProviderConfig(
        provider_id="kimi",
        display_name="Kimi (Moonshot)",
        provider_type=ProviderType.OPENAI_COMPATIBLE,
        base_url="https://api.moonshot.cn/v1",
        default_model="moonshot-v1-8k",
        chat_endpoint="/chat/completions",
        supports_tools=True,
        supports_streaming=True
    ),
    "glm": ProviderConfig(
        provider_id="glm",
        display_name="GLM (Zhipu)",
        provider_type=ProviderType.OPENAI_COMPATIBLE,
        base_url="https://open.bigmodel.cn/api/paas/v4",
        default_model="glm-4-flash",
        chat_endpoint="/chat/completions",
        supports_tools=True,
        supports_streaming=True
    ),
    "gemini": ProviderConfig(
        provider_id="gemini",
        display_name="Gemini (Google)",
        provider_type=ProviderType.GEMINI,
        base_url="https://generativelanguage.googleapis.com/v1beta",
        default_model="gemini-2.0-flash",
        supports_tools=False,
        supports_streaming=True
    ),
    "mistral": ProviderConfig(
        provider_id="mistral",
        display_name="Mistral AI",
        provider_type=ProviderType.OPENAI_COMPATIBLE,
        base_url="https://api.mistral.ai/v1",
        default_model="mistral-large-latest",
        chat_endpoint="/chat/completions",
        supports_tools=True,
        supports_streaming=True
    ),
    "groq": ProviderConfig(
        provider_id="groq",
        display_name="Groq",
        provider_type=ProviderType.OPENAI_COMPATIBLE,
        base_url="https://api.groq.com/openai/v1",
        default_model="llama-3.3-70b-versatile",
        chat_endpoint="/chat/completions",
        supports_tools=True,
        supports_streaming=True
    ),
    "xai": ProviderConfig(
        provider_id="xai",
        display_name="xAI (Grok)",
        provider_type=ProviderType.OPENAI_COMPATIBLE,
        base_url="https://api.x.ai/v1",
        default_model="grok-2",
        chat_endpoint="/chat/completions",
        supports_tools=True,
        supports_streaming=True
    ),
    "ollama": ProviderConfig(
        provider_id="ollama",
        display_name="Ollama (Local)",
        provider_type=ProviderType.OPENAI_COMPATIBLE,
        base_url="http://localhost:11434/v1",
        default_model="qwen2.5",
        chat_endpoint="/chat/completions",
        supports_tools=True,
        supports_streaming=True,
        request_timeout=120,
        read_timeout=180
    ),
}


# ============================================================
# 适配器工厂
# ============================================================

def create_adapter(provider_id: str, custom_config: Optional[Dict[str, Any]] = None) -> BaseProviderAdapter:
    """
    创建厂商适配器实例

    Args:
        provider_id: 厂商ID，如 "deepseek", "openai", "claude" 等
        custom_config: 可选的自定义配置，可覆盖默认配置中的字段

    Returns:
        BaseProviderAdapter: 对应厂商的适配器实例

    Raises:
        ValueError: 如果厂商ID不存在
    """
    config = PROVIDER_REGISTRY.get(provider_id)
    if not config:
        raise ValueError(f"Unknown provider: {provider_id}. Available: {list(PROVIDER_REGISTRY.keys())}")

    if custom_config:
        for key, value in custom_config.items():
            if hasattr(config, key):
                setattr(config, key, value)

    if config.provider_type == ProviderType.OPENAI_COMPATIBLE:
        return OpenAICompatibleAdapter(config)
    elif config.provider_type == ProviderType.ANTHROPIC:
        return AnthropicAdapter(config)
    elif config.provider_type == ProviderType.GEMINI:
        return GeminiAdapter(config)
    else:
        raise ValueError(f"Unsupported provider type: {config.provider_type}")


def get_available_providers() -> List[Dict[str, Any]]:
    """获取所有可用厂商列表"""
    return [
        {
            "id": p.provider_id,
            "name": p.display_name,
            "type": p.provider_type.value,
            "base_url": p.base_url,
            "default_model": p.default_model,
            "supports_tools": p.supports_tools,
            "supports_streaming": p.supports_streaming
        }
        for p in PROVIDER_REGISTRY.values()
    ]


def register_provider(config: ProviderConfig) -> None:
    """
    注册新的厂商配置 - 扩展接口

    Example:
        register_provider(ProviderConfig(
            provider_id="custom",
            display_name="Custom API",
            provider_type=ProviderType.OPENAI_COMPATIBLE,
            base_url="https://api.custom.com/v1",
            default_model="custom-model"
        ))
    """
    PROVIDER_REGISTRY[config.provider_id] = config


# ============================================================
# 统一API客户端 - 高层封装
# ============================================================

class UnifiedAPIClient:
    """
    统一API客户端 - 简化调用接口

    Usage:
        client = UnifiedAPIClient("deepseek", api_key="sk-...")
        response = client.chat([Message(role="user", content="Hello")])
        print(response.content)

        for chunk in client.stream_chat([Message(role="user", content="Hello")]):
            print(chunk.content, end="")
    """

    def __init__(self, provider_id: str, api_key: str, api_url: Optional[str] = None,
                 model: Optional[str] = None, custom_config: Optional[Dict] = None):
        self.provider_id = provider_id
        self.api_key = api_key
        self.model = model

        cc = dict(custom_config or {})
        if api_url:
            cc["base_url"] = api_url
        if model:
            cc["default_model"] = model

        self.adapter = create_adapter(provider_id, cc if cc else None)

    def chat(self, messages: List[Message], tools: Optional[List[ToolSchema]] = None,
             **kwargs) -> ChatResponse:
        return self.adapter.chat(messages, self.api_key, tools, self.model, **kwargs)

    def stream_chat(self, messages: List[Message], tools: Optional[List[ToolSchema]] = None,
                    **kwargs) -> Iterator[StreamChunk]:
        yield from self.adapter.stream_chat(messages, self.api_key, tools, self.model, **kwargs)

    def test_connection(self) -> Dict[str, Any]:
        """测试API连接"""
        try:
            result = self.chat([Message(role="user", content="返回“连接成功”四个字。")])
            return {
                "success": True,
                "provider": self.provider_id,
                "model": self.model or self.adapter.config.default_model,
                "response_preview": result.content[:80]
            }
        except APIError as e:
            return e.to_dict()
        except Exception as e:
            return {"error": True, "code": "unexpected", "message": str(e)}


# ============================================================
# 向后兼容: 替换旧版 call_external_provider
# ============================================================

def call_external_provider_unified(provider: str, api_url: str, api_key: str,
                                    model: str, prompt: str, system: str = "") -> str:
    """
    统一的外部API调用函数 - 替代旧的 call_external_provider
    保持向后兼容的接口签名
    """
    messages = []
    if system:
        messages.append(Message(role="system", content=system))
    messages.append(Message(role="user", content=prompt))

    try:
        client = UnifiedAPIClient(provider, api_key, api_url, model)
        response = client.chat(messages)
        return response.content
    except APIError as e:
        return f"[API Error ({e.code})]: {e.message}"
    except Exception as e:
        return f"[Error]: {str(e)}"


def test_external_api_unified(provider: str, api_url: str, api_key: str,
                               model: str) -> Dict[str, Any]:
    """统一的外部API测试函数"""
    try:
        client = UnifiedAPIClient(provider, api_key, api_url, model)
        return client.test_connection()
    except Exception as e:
        return {"success": False, "error": str(e)}
