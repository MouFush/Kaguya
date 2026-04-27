#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试统一API适配器 - 静态测试（不依赖requests）
"""

import sys
import json
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

# 模拟统一API适配器的核心类
print("=" * 60)
print("测试统一API适配器核心类")
print("=" * 60)

class APIProvider(Enum):
    """支持的API提供商"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    ALIBABA = "alibaba"
    BAIDU = "baidu"
    ZHIPU = "zhipu"
    MOONSHOT = "moonshot"
    MINIMAX = "minimax"
    DEEPSEEK = "deepseek"
    LOCAL = "local"


@dataclass
class APIConfig:
    """API配置"""
    provider: str
    api_key: str
    base_url: str
    model: str
    enabled: bool = True
    timeout: int = 60
    max_retries: int = 3


@dataclass
class APIResponse:
    """API响应"""
    content: str
    reasoning: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    provider: str = ""
    model: str = ""
    error: Optional[str] = None


class UnifiedAPIAdapter:
    """统一API适配器"""
    
    PROVIDER_CONFIGS = {
        APIProvider.OPENAI: {
            "base_url": "https://api.openai.com/v1",
            "headers_template": {"Authorization": "Bearer {api_key}", "Content-Type": "application/json"},
            "endpoint": "/chat/completions",
            "supports_streaming": True,
            "message_format": "openai",
        },
        APIProvider.ANTHROPIC: {
            "base_url": "https://api.anthropic.com",
            "headers_template": {"x-api-key": "{api_key}", "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
            "endpoint": "/v1/messages",
            "supports_streaming": True,
            "message_format": "claude",
        },
        APIProvider.GOOGLE: {
            "base_url": "https://generativelanguage.googleapis.com/v1beta",
            "headers_template": {"Content-Type": "application/json"},
            "endpoint": "/models/{model}:generateContent",
            "supports_streaming": False,
            "message_format": "gemini",
            "api_key_in_url": True,
        },
        APIProvider.ALIBABA: {
            "base_url": "https://dashscope.aliyuncs.com/api/v1",
            "headers_template": {"Authorization": "Bearer {api_key}", "Content-Type": "application/json"},
            "endpoint": "/services/aigc/text-generation/generation",
            "supports_streaming": True,
            "message_format": "openai",
        },
        APIProvider.BAIDU: {
            "base_url": "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat",
            "headers_template": {"Content-Type": "application/json"},
            "endpoint": "/{model}",
            "supports_streaming": True,
            "message_format": "baidu",
        },
        APIProvider.ZHIPU: {
            "base_url": "https://open.bigmodel.cn/api/paas/v4",
            "headers_template": {"Authorization": "{api_key}", "Content-Type": "application/json"},
            "endpoint": "/chat/completions",
            "supports_streaming": True,
            "message_format": "openai",
        },
        APIProvider.MOONSHOT: {
            "base_url": "https://api.moonshot.cn/v1",
            "headers_template": {"Authorization": "Bearer {api_key}", "Content-Type": "application/json"},
            "endpoint": "/chat/completions",
            "supports_streaming": True,
            "message_format": "openai",
        },
        APIProvider.MINIMAX: {
            "base_url": "https://api.minimax.chat/v1",
            "headers_template": {"Authorization": "Bearer {api_key}", "Content-Type": "application/json"},
            "endpoint": "/text/chatcompletion_v2",
            "supports_streaming": True,
            "message_format": "minimax",
        },
        APIProvider.DEEPSEEK: {
            "base_url": "https://api.deepseek.com/v1",
            "headers_template": {"Authorization": "Bearer {api_key}", "Content-Type": "application/json"},
            "endpoint": "/chat/completions",
            "supports_streaming": True,
            "message_format": "openai",
        },
    }
    
    def __init__(self, config: APIConfig):
        self.config = config
        self.provider_enum = self._get_provider_enum(config.provider)
        self.provider_config = self.PROVIDER_CONFIGS.get(self.provider_enum, {})
    
    def _get_provider_enum(self, provider: str) -> APIProvider:
        """获取提供商枚举"""
        provider_map = {
            "openai": APIProvider.OPENAI,
            "anthropic": APIProvider.ANTHROPIC,
            "claude": APIProvider.ANTHROPIC,
            "google": APIProvider.GOOGLE,
            "gemini": APIProvider.GOOGLE,
            "alibaba": APIProvider.ALIBABA,
            "qwen": APIProvider.ALIBABA,
            "baidu": APIProvider.BAIDU,
            "ernie": APIProvider.BAIDU,
            "zhipu": APIProvider.ZHIPU,
            "glm": APIProvider.ZHIPU,
            "moonshot": APIProvider.MOONSHOT,
            "kimi": APIProvider.MOONSHOT,
            "minimax": APIProvider.MINIMAX,
            "deepseek": APIProvider.DEEPSEEK,
        }
        return provider_map.get(provider.lower(), APIProvider.OPENAI)
    
    def _format_messages(self, messages: List[Dict[str, str]]) -> Tuple[List[Dict], Optional[str]]:
        """根据提供商格式化消息"""
        message_format = self.provider_config.get("message_format", "openai")
        
        if message_format == "claude":
            system_msg = ""
            chat_messages = []
            for msg in messages:
                if msg['role'] == 'system':
                    system_msg = msg['content']
                else:
                    chat_messages.append(msg)
            return chat_messages, system_msg
        
        elif message_format == "gemini":
            contents = []
            system_msg = ""
            for msg in messages:
                if msg['role'] == 'system':
                    system_msg = msg['content']
                elif msg['role'] == 'user':
                    contents.append({'role': 'user', 'parts': [{'text': msg['content']}]})
                elif msg['role'] == 'assistant':
                    contents.append({'role': 'model', 'parts': [{'text': msg['content']}]})
            return contents, system_msg
        
        elif message_format == "baidu":
            formatted = []
            for msg in messages:
                if msg['role'] == 'system':
                    formatted.append({'role': 'user', 'content': msg['content']})
                    formatted.append({'role': 'assistant', 'content': '明白了'})
                else:
                    formatted.append(msg)
            return formatted, None
        
        elif message_format == "minimax":
            formatted = []
            for msg in messages:
                if msg['role'] == 'system':
                    formatted.append({'sender_type': 'SYSTEM', 'text': msg['content']})
                elif msg['role'] == 'user':
                    formatted.append({'sender_type': 'USER', 'text': msg['content']})
                elif msg['role'] == 'assistant':
                    formatted.append({'sender_type': 'BOT', 'text': msg['content']})
            return formatted, None
        
        else:
            return messages, None
    
    def _build_request_data(self, messages: List[Dict], temperature: float, 
                           max_tokens: int, stream: bool) -> Dict:
        """构建请求数据"""
        formatted_messages, system_msg = self._format_messages(messages)
        message_format = self.provider_config.get("message_format", "openai")
        
        if message_format == "openai":
            data = {
                'model': self.config.model,
                'messages': formatted_messages,
                'temperature': temperature,
                'max_tokens': max_tokens,
                'stream': stream
            }
            if system_msg:
                data['system'] = system_msg
            return data
        
        elif message_format == "claude":
            data = {
                'model': self.config.model,
                'messages': formatted_messages,
                'temperature': temperature,
                'max_tokens': max_tokens,
                'stream': stream
            }
            if system_msg:
                data['system'] = system_msg
            return data
        
        elif message_format == "gemini":
            data = {
                'contents': formatted_messages,
                'generationConfig': {
                    'temperature': temperature,
                    'maxOutputTokens': max_tokens
                }
            }
            if system_msg:
                data['systemInstruction'] = {'parts': [{'text': system_msg}]}
            return data
        
        elif message_format == "baidu":
            return {
                'messages': formatted_messages,
                'temperature': temperature,
                'max_output_tokens': max_tokens,
                'stream': stream
            }
        
        elif message_format == "minimax":
            return {
                'model': self.config.model,
                'messages': formatted_messages,
                'temperature': temperature,
                'max_tokens': max_tokens,
                'stream': stream
            }
        
        return {
            'model': self.config.model,
            'messages': formatted_messages,
            'temperature': temperature,
            'max_tokens': max_tokens,
            'stream': stream
        }
    
    def _build_headers(self) -> Dict[str, str]:
        """构建请求头"""
        template = self.provider_config.get("headers_template", {})
        headers = {}
        for key, value in template.items():
            headers[key] = value.format(api_key=self.config.api_key)
        return headers
    
    def _build_url(self) -> str:
        """构建请求URL"""
        base_url = self.config.base_url.rstrip('/')
        endpoint = self.provider_config.get("endpoint", "/chat/completions")
        endpoint = endpoint.format(model=self.config.model)
        
        url = f"{base_url}{endpoint}"
        
        if self.provider_config.get("api_key_in_url"):
            url = f"{url}?key={self.config.api_key}"
        
        return url


class APIProviderManager:
    """API提供商管理器"""
    
    def __init__(self):
        self.providers: Dict[str, UnifiedAPIAdapter] = {}
        self.active_provider: Optional[str] = None
        self.fallback_order: List[str] = []
    
    def register_provider(self, name: str, config: APIConfig):
        """注册API提供商"""
        self.providers[name] = UnifiedAPIAdapter(config)
        if config.enabled and not self.active_provider:
            self.active_provider = name
    
    def set_fallback_order(self, order: List[str]):
        """设置回退顺序"""
        self.fallback_order = order
    
    def get_active_adapter(self) -> Optional[UnifiedAPIAdapter]:
        """获取当前活动的适配器"""
        if self.active_provider and self.active_provider in self.providers:
            return self.providers[self.active_provider]
        return None


# 全局实例
_api_manager: Optional[APIProviderManager] = None


def get_api_manager() -> APIProviderManager:
    """获取全局API管理器实例"""
    global _api_manager
    if _api_manager is None:
        _api_manager = APIProviderManager()
    return _api_manager


# 测试API配置
print("\n" + "=" * 60)
print("测试API配置")
print("=" * 60)

test_configs = [
    {
        "provider": "openai",
        "api_key": "test-key",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4"
    },
    {
        "provider": "anthropic",
        "api_key": "test-key",
        "base_url": "https://api.anthropic.com",
        "model": "claude-3-sonnet"
    },
    {
        "provider": "google",
        "api_key": "test-key",
        "base_url": "",
        "model": "gemini-pro"
    },
    {
        "provider": "alibaba",
        "api_key": "test-key",
        "base_url": "https://dashscope.aliyuncs.com/api/v1",
        "model": "qwen-max"
    },
    {
        "provider": "baidu",
        "api_key": "test-key",
        "base_url": "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat",
        "model": "ernie-bot"
    },
    {
        "provider": "zhipu",
        "api_key": "test-key",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "model": "glm-4"
    },
    {
        "provider": "moonshot",
        "api_key": "test-key",
        "base_url": "https://api.moonshot.cn/v1",
        "model": "moonshot-v1-8k"
    },
    {
        "provider": "minimax",
        "api_key": "test-key",
        "base_url": "https://api.minimax.chat/v1",
        "model": "abab6-chat"
    },
    {
        "provider": "deepseek",
        "api_key": "test-key",
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat"
    }
]

for config_data in test_configs:
    try:
        config = APIConfig(**config_data)
        adapter = UnifiedAPIAdapter(config)
        
        print(f"\n✅ {config.provider}:")
        print(f"   URL: {adapter._build_url()}")
        print(f"   Headers: {adapter._build_headers()}")
        print(f"   Supports Streaming: {adapter.provider_config.get('supports_streaming', False)}")
        print(f"   Message Format: {adapter.provider_config.get('message_format', 'openai')}")
        
        # 测试消息格式化
        messages = [
            {"role": "system", "content": "你是一个助手"},
            {"role": "user", "content": "你好"}
        ]
        formatted, system = adapter._format_messages(messages)
        print(f"   Formatted Messages: {json.dumps(formatted, ensure_ascii=False)[:100]}...")
        
        # 测试请求数据构建
        request_data = adapter._build_request_data(messages, 0.7, 512, False)
        print(f"   Request Data Keys: {list(request_data.keys())}")
        
    except Exception as e:
        print(f"\n❌ {config_data['provider']}: {e}")

# 测试API管理器
print("\n" + "=" * 60)
print("测试API管理器")
print("=" * 60)

try:
    manager = get_api_manager()
    print(f"✅ API管理器创建成功")
    print(f"   当前活动提供商: {manager.active_provider}")
    print(f"   已注册提供商: {list(manager.providers.keys())}")
    
    # 注册测试提供商
    for config_data in test_configs[:3]:  # 只注册前3个
        config = APIConfig(**config_data)
        manager.register_provider(config_data['provider'], config)
    
    print(f"   注册后提供商: {list(manager.providers.keys())}")
    
    # 设置回退顺序
    manager.set_fallback_order(['openai', 'anthropic', 'google'])
    print(f"   回退顺序: {manager.fallback_order}")
    
except Exception as e:
    print(f"❌ API管理器测试失败: {e}")

# 测试API响应
print("\n" + "=" * 60)
print("测试API响应")
print("=" * 60)

try:
    response = APIResponse(
        content="这是测试响应",
        reasoning="思考过程",
        tokens_in=100,
        tokens_out=50,
        provider="openai",
        model="gpt-4"
    )
    print(f"✅ API响应创建成功")
    print(f"   Content: {response.content}")
    print(f"   Reasoning: {response.reasoning}")
    print(f"   Tokens In: {response.tokens_in}")
    print(f"   Tokens Out: {response.tokens_out}")
    print(f"   Provider: {response.provider}")
    print(f"   Model: {response.model}")
except Exception as e:
    print(f"❌ API响应测试失败: {e}")

print("\n" + "=" * 60)
print("所有测试完成!")
print("=" * 60)

# 打印支持的API提供商列表
print("\n支持的API提供商:")
for provider in APIProvider:
    print(f"  - {provider.value}")
