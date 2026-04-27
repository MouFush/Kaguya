#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用大模型API适配器
支持: OpenAI, Claude, 文心一言, 通义千问, ChatGLM等
集成长期记忆系统
"""

import os
import json
import time
import requests
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Generator, Any
from dataclasses import dataclass
from enum import Enum
import threading

# 导入记忆系统
from memory_integration import ConversationMemory, MemoryEnhancedChat


class LLMProvider(Enum):
    """LLM提供商"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    BAIDU = "baidu"
    ALIBABA = "alibaba"
    ZHIPU = "zhipu"
    MOONSHOT = "moonshot"
    DEEPSEEK = "deepseek"
    LOCAL = "local"
    OLLAMA = "ollama"


@dataclass
class LLMConfig:
    """LLM配置"""
    provider: LLMProvider
    api_key: str
    base_url: Optional[str] = None
    model: str = "default"
    temperature: float = 0.7
    max_tokens: int = 2048
    timeout: int = 60
    # 记忆系统配置
    enable_memory: bool = True
    memory_max_context: int = 10


class BaseLLMAdapter(ABC):
    """LLM适配器基类"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update(self._get_headers())
        
        # 初始化记忆系统
        if config.enable_memory:
            self.memory = ConversationMemory(self.generate)
        else:
            self.memory = None
    
    @abstractmethod
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        pass
    
    @abstractmethod
    def _format_messages(self, messages: List[Dict]) -> Any:
        """格式化消息为API特定格式"""
        pass
    
    @abstractmethod
    def _parse_response(self, response: Dict) -> str:
        """解析API响应"""
        pass
    
    @abstractmethod
    def chat(self, messages: List[Dict], **kwargs) -> str:
        """非流式对话"""
        pass
    
    @abstractmethod
    def chat_stream(self, messages: List[Dict], **kwargs) -> Generator[str, None, None]:
        """流式对话"""
        pass
    
    def generate(self, prompt: str) -> str:
        """生成文本（兼容记忆系统）"""
        messages = [{"role": "user", "content": prompt}]
        return self.chat(messages)
    
    def chat_with_memory(self, user_message: str, 
                        system_prompt: str = None) -> str:
        """
        带记忆的对话
        
        Args:
            user_message: 用户消息
            system_prompt: 系统提示
        
        Returns:
            AI回复
        """
        if not self.memory:
            # 无记忆模式
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": user_message})
            return self.chat(messages)
        
        # 添加用户消息到记忆
        self.memory.add_message('user', user_message)
        
        # 获取记忆增强的上下文
        context = self.memory.get_context_for_llm(user_message)
        
        # 构建消息
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if context:
            messages.append({"role": "system", "content": context})
        messages.append({"role": "user", "content": user_message})
        
        # 调用API
        response = self.chat(messages)
        
        # 添加AI回复到记忆
        self.memory.add_message('assistant', response)
        
        return response
    
    def chat_stream_with_memory(self, user_message: str,
                               system_prompt: str = None) -> Generator[str, None, None]:
        """带记忆的流式对话"""
        if not self.memory:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": user_message})
            yield from self.chat_stream(messages)
            return
        
        # 添加用户消息到记忆
        self.memory.add_message('user', user_message)
        
        # 获取记忆增强的上下文
        context = self.memory.get_context_for_llm(user_message)
        
        # 构建消息
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if context:
            messages.append({"role": "system", "content": context})
        messages.append({"role": "user", "content": user_message})
        
        # 流式调用
        full_response = []
        for chunk in self.chat_stream(messages):
            full_response.append(chunk)
            yield chunk
        
        # 添加完整回复到记忆
        self.memory.add_message('assistant', ''.join(full_response))
    
    def get_memory_stats(self) -> Dict:
        """获取记忆统计"""
        if self.memory:
            return self.memory.manager.get_memory_stats()
        return {"error": "Memory not enabled"}
    
    def search_memories(self, query: str, top_k: int = 5) -> List[Dict]:
        """搜索记忆"""
        if self.memory:
            return self.memory.search_memories(query, top_k)
        return []


class OpenAIAdapter(BaseLLMAdapter):
    """OpenAI API适配器"""
    
    def __init__(self, config: LLMConfig):
        if not config.base_url:
            config.base_url = "https://api.openai.com/v1"
        super().__init__(config)
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }
    
    def _format_messages(self, messages: List[Dict]) -> List[Dict]:
        return messages
    
    def _parse_response(self, response: Dict) -> str:
        return response['choices'][0]['message']['content']
    
    def chat(self, messages: List[Dict], **kwargs) -> str:
        """非流式对话"""
        url = f"{self.config.base_url}/chat/completions"
        
        data = {
            "model": self.config.model or "gpt-3.5-turbo",
            "messages": self._format_messages(messages),
            "temperature": kwargs.get('temperature', self.config.temperature),
            "max_tokens": kwargs.get('max_tokens', self.config.max_tokens),
            "stream": False
        }
        
        response = self.session.post(url, json=data, timeout=self.config.timeout)
        response.raise_for_status()
        
        return self._parse_response(response.json())
    
    def chat_stream(self, messages: List[Dict], **kwargs) -> Generator[str, None, None]:
        """流式对话"""
        url = f"{self.config.base_url}/chat/completions"
        
        data = {
            "model": self.config.model or "gpt-3.5-turbo",
            "messages": self._format_messages(messages),
            "temperature": kwargs.get('temperature', self.config.temperature),
            "max_tokens": kwargs.get('max_tokens', self.config.max_tokens),
            "stream": True
        }
        
        response = self.session.post(url, json=data, timeout=self.config.timeout, stream=True)
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    line = line[6:]
                    if line == '[DONE]':
                        break
                    try:
                        chunk = json.loads(line)
                        delta = chunk['choices'][0]['delta']
                        if 'content' in delta:
                            yield delta['content']
                    except:
                        pass


class ClaudeAdapter(BaseLLMAdapter):
    """Anthropic Claude适配器"""
    
    def __init__(self, config: LLMConfig):
        if not config.base_url:
            config.base_url = "https://api.anthropic.com/v1"
        super().__init__(config)
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            "x-api-key": self.config.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
    
    def _format_messages(self, messages: List[Dict]) -> Dict:
        # Claude使用不同的消息格式
        system = None
        formatted_messages = []
        
        for msg in messages:
            if msg['role'] == 'system':
                system = msg['content']
            else:
                formatted_messages.append({
                    "role": msg['role'],
                    "content": msg['content']
                })
        
        result = {"messages": formatted_messages}
        if system:
            result["system"] = system
        
        return result
    
    def _parse_response(self, response: Dict) -> str:
        return response['content'][0]['text']
    
    def chat(self, messages: List[Dict], **kwargs) -> str:
        url = f"{self.config.base_url}/messages"
        
        formatted = self._format_messages(messages)
        data = {
            "model": self.config.model or "claude-3-sonnet-20240229",
            "max_tokens": kwargs.get('max_tokens', self.config.max_tokens),
            "temperature": kwargs.get('temperature', self.config.temperature),
            **formatted
        }
        
        response = self.session.post(url, json=data, timeout=self.config.timeout)
        response.raise_for_status()
        
        return self._parse_response(response.json())
    
    def chat_stream(self, messages: List[Dict], **kwargs) -> Generator[str, None, None]:
        url = f"{self.config.base_url}/messages"
        
        formatted = self._format_messages(messages)
        data = {
            "model": self.config.model or "claude-3-sonnet-20240229",
            "max_tokens": kwargs.get('max_tokens', self.config.max_tokens),
            "temperature": kwargs.get('temperature', self.config.temperature),
            "stream": True,
            **formatted
        }
        
        response = self.session.post(url, json=data, timeout=self.config.timeout, stream=True)
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line:
                try:
                    chunk = json.loads(line.decode('utf-8'))
                    if chunk.get('type') == 'content_block_delta':
                        yield chunk['delta']['text']
                except:
                    pass


class BaiduAdapter(BaseLLMAdapter):
    """百度文心一言适配器"""
    
    def __init__(self, config: LLMConfig):
        if not config.base_url:
            config.base_url = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat"
        super().__init__(config)
        self.access_token = None
        self.token_expire_time = 0
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json"
        }
    
    def _get_access_token(self) -> str:
        """获取百度访问令牌"""
        if self.access_token and time.time() < self.token_expire_time:
            return self.access_token
        
        url = "https://aip.baidubce.com/oauth/2.0/token"
        params = {
            "grant_type": "client_credentials",
            "client_id": self.config.api_key.split(':')[0],  # API Key
            "client_secret": self.config.api_key.split(':')[1] if ':' in self.config.api_key else ''  # Secret Key
        }
        
        response = requests.post(url, params=params)
        result = response.json()
        
        self.access_token = result['access_token']
        self.token_expire_time = time.time() + result.get('expires_in', 3600) - 300
        
        return self.access_token
    
    def _format_messages(self, messages: List[Dict]) -> List[Dict]:
        # 文心一言格式
        return [{"role": msg["role"], "content": msg["content"]} for msg in messages]
    
    def _parse_response(self, response: Dict) -> str:
        return response['result']
    
    def chat(self, messages: List[Dict], **kwargs) -> str:
        token = self._get_access_token()
        url = f"{self.config.base_url}/{self.config.model or 'completions'}?access_token={token}"
        
        data = {
            "messages": self._format_messages(messages),
            "temperature": kwargs.get('temperature', self.config.temperature),
            "max_output_tokens": kwargs.get('max_tokens', self.config.max_tokens)
        }
        
        response = self.session.post(url, json=data, timeout=self.config.timeout)
        response.raise_for_status()
        
        return self._parse_response(response.json())
    
    def chat_stream(self, messages: List[Dict], **kwargs) -> Generator[str, None, None]:
        # 文心一言流式接口
        token = self._get_access_token()
        url = f"{self.config.base_url}/{self.config.model or 'completions'}?access_token={token}"
        
        data = {
            "messages": self._format_messages(messages),
            "temperature": kwargs.get('temperature', self.config.temperature),
            "max_output_tokens": kwargs.get('max_tokens', self.config.max_tokens),
            "stream": True
        }
        
        response = self.session.post(url, json=data, timeout=self.config.timeout, stream=True)
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line:
                try:
                    chunk = json.loads(line.decode('utf-8'))
                    if 'result' in chunk:
                        yield chunk['result']
                except:
                    pass


class AlibabaAdapter(BaseLLMAdapter):
    """阿里通义千问适配器"""
    
    def __init__(self, config: LLMConfig):
        if not config.base_url:
            config.base_url = "https://dashscope.aliyuncs.com/api/v1"
        super().__init__(config)
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }
    
    def _format_messages(self, messages: List[Dict]) -> List[Dict]:
        return messages
    
    def _parse_response(self, response: Dict) -> str:
        return response['output']['choices'][0]['message']['content']
    
    def chat(self, messages: List[Dict], **kwargs) -> str:
        url = f"{self.config.base_url}/services/aigc/text-generation/generation"
        
        data = {
            "model": self.config.model or "qwen-turbo",
            "input": {
                "messages": self._format_messages(messages)
            },
            "parameters": {
                "temperature": kwargs.get('temperature', self.config.temperature),
                "max_tokens": kwargs.get('max_tokens', self.config.max_tokens)
            }
        }
        
        response = self.session.post(url, json=data, timeout=self.config.timeout)
        response.raise_for_status()
        
        return self._parse_response(response.json())
    
    def chat_stream(self, messages: List[Dict], **kwargs) -> Generator[str, None, None]:
        url = f"{self.config.base_url}/services/aigc/text-generation/generation"
        
        data = {
            "model": self.config.model or "qwen-turbo",
            "input": {
                "messages": self._format_messages(messages)
            },
            "parameters": {
                "temperature": kwargs.get('temperature', self.config.temperature),
                "max_tokens": kwargs.get('max_tokens', self.config.max_tokens),
                "incremental_output": True
            }
        }
        
        response = self.session.post(url, json=data, timeout=self.config.timeout, stream=True)
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line:
                try:
                    chunk = json.loads(line.decode('utf-8'))
                    if 'output' in chunk and 'choices' in chunk['output']:
                        yield chunk['output']['choices'][0]['message']['content']
                except:
                    pass


class OllamaAdapter(BaseLLMAdapter):
    """Ollama 本地模型适配器"""
    
    def __init__(self, config: LLMConfig):
        if not config.base_url:
            config.base_url = "http://localhost:11434"
        super().__init__(config)
        self._ollama_adapter = None
    
    def _get_ollama_adapter(self):
        if self._ollama_adapter is None:
            from ollama_adapter import get_ollama_adapter, OllamaConfig as OllamaCfg
            self._ollama_adapter = get_ollama_adapter(OllamaCfg(
                base_url=self.config.base_url,
                model=self.config.model or "qwen3.5:4b",
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            ))
        return self._ollama_adapter
    
    def _get_headers(self) -> Dict[str, str]:
        return {"Content-Type": "application/json"}
    
    def _format_messages(self, messages: List[Dict]) -> List[Dict]:
        return messages
    
    def _parse_response(self, response: Dict) -> str:
        return response.get('message', {}).get('content', '')
    
    def chat(self, messages: List[Dict], **kwargs) -> str:
        adapter = self._get_ollama_adapter()
        return adapter.chat(
            messages,
            temperature=kwargs.get('temperature', self.config.temperature),
            max_tokens=kwargs.get('max_tokens', self.config.max_tokens)
        )
    
    def chat_stream(self, messages: List[Dict], **kwargs) -> Generator[str, None, None]:
        adapter = self._get_ollama_adapter()
        yield from adapter.chat_stream(
            messages,
            temperature=kwargs.get('temperature', self.config.temperature),
            max_tokens=kwargs.get('max_tokens', self.config.max_tokens)
        )


class LLMFactory:
    """LLM工厂类"""
    
    _adapters = {
        LLMProvider.OPENAI: OpenAIAdapter,
        LLMProvider.ANTHROPIC: ClaudeAdapter,
        LLMProvider.BAIDU: BaiduAdapter,
        LLMProvider.ALIBABA: AlibabaAdapter,
        LLMProvider.OLLAMA: OllamaAdapter,
    }
    
    @classmethod
    def create(cls, provider: str, **kwargs) -> BaseLLMAdapter:
        """
        创建LLM适配器
        
        Args:
            provider: 提供商名称 (openai/claude/baidu/alibaba)
            **kwargs: 配置参数
                - api_key: API密钥
                - base_url: 自定义API地址（可选）
                - model: 模型名称
                - temperature: 温度参数
                - max_tokens: 最大token数
                - enable_memory: 是否启用记忆系统
        
        Returns:
            LLM适配器实例
        """
        try:
            provider_enum = LLMProvider(provider.lower())
        except ValueError:
            raise ValueError(f"不支持的提供商: {provider}，支持的: {[p.value for p in LLMProvider]}")
        
        adapter_class = cls._adapters.get(provider_enum)
        if not adapter_class:
            raise ValueError(f"未实现适配器: {provider}")
        
        config = LLMConfig(
            provider=provider_enum,
            api_key=kwargs.get('api_key', ''),
            base_url=kwargs.get('base_url'),
            model=kwargs.get('model', 'default'),
            temperature=kwargs.get('temperature', 0.7),
            max_tokens=kwargs.get('max_tokens', 2048),
            enable_memory=kwargs.get('enable_memory', True)
        )
        
        return adapter_class(config)


# 便捷函数
def create_llm(provider: str, api_key: str, **kwargs) -> BaseLLMAdapter:
    """创建LLM实例的便捷函数"""
    return LLMFactory.create(provider, api_key=api_key, **kwargs)


# 示例用法
if __name__ == '__main__':
    # 示例1: 使用OpenAI（带记忆）
    print("="*60)
    print("OpenAI适配器示例")
    print("="*60)
    
    # llm = create_llm(
    #     provider="openai",
    #     api_key="your-api-key",
    #     model="gpt-3.5-turbo",
    #     enable_memory=True
    # )
    
    # 带记忆的对话
    # response = llm.chat_with_memory("你好，我叫张三")
    # print(f"AI: {response}")
    
    # response = llm.chat_with_memory("我喜欢Python编程")
    # print(f"AI: {response}")
    
    # response = llm.chat_with_memory("你还记得我叫什么吗？")
    # print(f"AI: {response}")
    
    # 查看记忆统计
    # stats = llm.get_memory_stats()
    # print(f"记忆统计: {stats}")
    
    print("\n请设置实际的API密钥后使用")
    
    # 示例2: 流式对话
    # for chunk in llm.chat_stream_with_memory("讲个故事"):
    #     print(chunk, end='', flush=True)
