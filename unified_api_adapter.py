#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一API适配器 - 支持所有外部API提供商
Unified API Adapter - Support for all external API providers

支持: OpenAI, Claude, Gemini, Qwen, DeepSeek, Moonshot, Zhipu, MiniMax, Baidu等
"""

import json
import requests
from typing import Dict, List, Optional, Tuple, Generator, Any
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


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
    """
    统一API适配器
    
    为所有增强功能提供统一的API调用接口
    """
    
    # API提供商配置模板
    PROVIDER_CONFIGS = {
        APIProvider.OPENAI: {
            "base_url": "https://api.openai.com/v1",
            "headers_template": {"Authorization": "Bearer {api_key}", "Content-Type": "application/json"},
            "endpoint": "/chat/completions",
            "supports_streaming": True,
            "message_format": "openai",  # openai, claude, gemini
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
        """
        根据提供商格式化消息
        
        Returns:
            (formatted_messages, system_message)
        """
        message_format = self.provider_config.get("message_format", "openai")
        
        if message_format == "claude":
            # Claude格式：分离system消息
            system_msg = ""
            chat_messages = []
            for msg in messages:
                if msg['role'] == 'system':
                    system_msg = msg['content']
                else:
                    chat_messages.append(msg)
            return chat_messages, system_msg
        
        elif message_format == "gemini":
            # Gemini格式
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
            # 百度文心格式
            formatted = []
            for msg in messages:
                if msg['role'] == 'system':
                    formatted.append({'role': 'user', 'content': msg['content']})
                    formatted.append({'role': 'assistant', 'content': '明白了'})
                else:
                    formatted.append(msg)
            return formatted, None
        
        elif message_format == "minimax":
            # MiniMax格式
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
            # 默认OpenAI格式
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
        
        # 某些API需要在URL中添加key
        if self.provider_config.get("api_key_in_url"):
            url = f"{url}?key={self.config.api_key}"
        
        return url
    
    def _parse_response(self, response_data: Dict) -> APIResponse:
        """解析响应数据"""
        message_format = self.provider_config.get("message_format", "openai")
        
        try:
            if message_format == "openai":
                content = response_data['choices'][0]['message']['content']
                reasoning = response_data['choices'][0]['message'].get('reasoning_content', '')
                tokens_in = response_data.get('usage', {}).get('prompt_tokens', 0)
                tokens_out = response_data.get('usage', {}).get('completion_tokens', 0)
                model = response_data.get('model', self.config.model)
                
            elif message_format == "claude":
                content = response_data['content'][0]['text'] if response_data.get('content') else ''
                reasoning = ""
                tokens_in = response_data.get('usage', {}).get('input_tokens', 0)
                tokens_out = response_data.get('usage', {}).get('output_tokens', 0)
                model = response_data.get('model', self.config.model)
                
            elif message_format == "gemini":
                candidates = response_data.get('candidates', [])
                if candidates:
                    content = candidates[0].get('content', {}).get('parts', [{}])[0].get('text', '')
                else:
                    content = ""
                reasoning = ""
                tokens_in = response_data.get('usageMetadata', {}).get('promptTokenCount', 0)
                tokens_out = response_data.get('usageMetadata', {}).get('candidatesTokenCount', 0)
                model = self.config.model
                
            elif message_format == "baidu":
                content = response_data.get('result', '')
                reasoning = ""
                tokens_in = response_data.get('usage', {}).get('prompt_tokens', 0)
                tokens_out = response_data.get('usage', {}).get('completion_tokens', 0)
                model = self.config.model
                
            elif message_format == "minimax":
                choices = response_data.get('choices', [])
                if choices:
                    messages = choices[0].get('messages', [])
                    content = messages[0].get('text', '') if messages else ''
                else:
                    content = ""
                reasoning = ""
                tokens_in = response_data.get('usage', {}).get('prompt_tokens', 0)
                tokens_out = response_data.get('usage', {}).get('completion_tokens', 0)
                model = self.config.model
            
            else:
                content = str(response_data)
                reasoning = ""
                tokens_in = 0
                tokens_out = 0
                model = self.config.model
            
            return APIResponse(
                content=content,
                reasoning=reasoning,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                provider=self.config.provider,
                model=model
            )
            
        except Exception as e:
            logger.error(f"解析响应失败: {e}")
            return APIResponse(
                content="",
                error=f"解析响应失败: {str(e)}"
            )
    
    def chat_completion(self, messages: List[Dict[str, str]], 
                       temperature: float = 0.7,
                       max_tokens: int = 512,
                       stream: bool = False) -> APIResponse:
        """
        统一的聊天完成接口
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            stream: 是否流式输出
            
        Returns:
            APIResponse对象
        """
        try:
            url = self._build_url()
            headers = self._build_headers()
            data = self._build_request_data(messages, temperature, max_tokens, stream)
            
            logger.info(f"调用 {self.config.provider} API: {self.config.model}")
            
            if stream:
                # 流式输出返回生成器
                return self._stream_chat(url, headers, data)
            else:
                # 非流式输出
                response = requests.post(
                    url, 
                    headers=headers, 
                    json=data, 
                    timeout=self.config.timeout
                )
                response.raise_for_status()
                result = response.json()
                return self._parse_response(result)
                
        except requests.exceptions.RequestException as e:
            logger.error(f"API请求失败: {e}")
            return APIResponse(
                content="",
                error=f"API请求失败: {str(e)}"
            )
        except Exception as e:
            logger.error(f"API调用错误: {e}")
            return APIResponse(
                content="",
                error=f"API调用错误: {str(e)}"
            )
    
    def _stream_chat(self, url: str, headers: Dict, data: Dict) -> Generator[str, None, None]:
        """流式聊天"""
        try:
            response = requests.post(
                url,
                headers=headers,
                json=data,
                stream=True,
                timeout=self.config.timeout
            )
            response.raise_for_status()
            
            message_format = self.provider_config.get("message_format", "openai")
            
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    
                    if line.startswith('data: '):
                        line = line[6:]
                    
                    if line == '[DONE]':
                        break
                    
                    try:
                        chunk = json.loads(line)
                        
                        if message_format == "openai":
                            if 'choices' in chunk and len(chunk['choices']) > 0:
                                delta = chunk['choices'][0].get('delta', {})
                                content = delta.get('content', '')
                                reasoning = delta.get('reasoning_content', '')
                                
                                if content:
                                    yield json.dumps({"content": content, "done": False}) + "\n"
                                if reasoning:
                                    yield json.dumps({"reasoning": reasoning, "done": False}) + "\n"
                        
                        elif message_format == "claude":
                            if chunk.get('type') == 'content_block_delta':
                                content = chunk['delta'].get('text', '')
                                if content:
                                    yield json.dumps({"content": content, "done": False}) + "\n"
                        
                    except json.JSONDecodeError:
                        continue
            
            yield json.dumps({"content": "", "done": True}) + "\n"
            
        except Exception as e:
            logger.error(f"流式API错误: {e}")
            yield json.dumps({"error": str(e), "done": True}) + "\n"


class APIProviderManager:
    """
    API提供商管理器
    
    管理多个API提供商，支持自动切换和负载均衡
    """
    
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
    
    def chat_completion(self, messages: List[Dict[str, str]], 
                       temperature: float = 0.7,
                       max_tokens: int = 512,
                       stream: bool = False,
                       use_fallback: bool = True) -> APIResponse:
        """
        统一的聊天完成接口，支持自动回退
        """
        providers_to_try = [self.active_provider] if self.active_provider else []
        
        if use_fallback:
            for provider in self.fallback_order:
                if provider not in providers_to_try and provider in self.providers:
                    providers_to_try.append(provider)
        
        last_error = None
        
        for provider_name in providers_to_try:
            adapter = self.providers.get(provider_name)
            if not adapter:
                continue
            
            try:
                result = adapter.chat_completion(messages, temperature, max_tokens, stream)
                if not result.error:
                    return result
                last_error = result.error
            except Exception as e:
                last_error = str(e)
                logger.warning(f"{provider_name} API调用失败: {e}")
                continue
        
        # 所有提供商都失败
        return APIResponse(
            content="",
            error=f"所有API提供商都不可用。最后错误: {last_error}"
        )


# 全局实例
_api_manager: Optional[APIProviderManager] = None


def get_api_manager() -> APIProviderManager:
    """获取全局API管理器实例"""
    global _api_manager
    if _api_manager is None:
        _api_manager = APIProviderManager()
    return _api_manager


# 便捷函数
def chat_with_any_provider(messages: List[Dict[str, str]], 
                          provider: str = None,
                          temperature: float = 0.7,
                          max_tokens: int = 512) -> str:
    """
    与任意提供商进行对话
    
    Args:
        messages: 消息列表
        provider: 指定提供商，None则使用活动提供商
        temperature: 温度
        max_tokens: 最大token数
        
    Returns:
        回复内容
    """
    manager = get_api_manager()
    
    if provider and provider in manager.providers:
        adapter = manager.providers[provider]
    else:
        adapter = manager.get_active_adapter()
    
    if not adapter:
        return "错误: 没有可用的API提供商"
    
    result = adapter.chat_completion(messages, temperature, max_tokens)
    
    if result.error:
        return f"错误: {result.error}"
    
    return result.content


# 测试代码
if __name__ == '__main__':
    # 测试配置
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
        }
    ]
    
    for config_data in test_configs:
        config = APIConfig(**config_data)
        adapter = UnifiedAPIAdapter(config)
        
        print(f"\n测试 {config.provider}:")
        print(f"  URL: {adapter._build_url()}")
        print(f"  Headers: {adapter._build_headers()}")
        
        messages = [
            {"role": "system", "content": "你是一个助手"},
            {"role": "user", "content": "你好"}
        ]
        
        data = adapter._build_request_data(messages, 0.7, 512, False)
        print(f"  Request Data: {json.dumps(data, indent=2, ensure_ascii=False)[:200]}...")
