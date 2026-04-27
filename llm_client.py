"""
统一LLM客户端
支持本地模型和外部API（OpenAI、Claude、Qwen等）
"""

import os
import json
import requests
from typing import List, Dict, Optional, Generator, Any
from abc import ABC, abstractmethod


class BaseLLMClient(ABC):
    """LLM客户端基类"""
    
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """生成文本"""
        pass
    
    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """对话模式"""
        pass


class LocalModelClient(BaseLLMClient):
    """本地模型客户端"""
    
    def __init__(self, model=None, tokenizer=None):
        self.model = model
        self.tokenizer = tokenizer
        self.device = model.device if model else 'cpu'
    
    def generate(self, prompt: str, max_tokens: int = 500, temperature: float = 0.7, **kwargs) -> str:
        """使用本地模型生成"""
        if not self.model or not self.tokenizer:
            return "Error: 本地模型未加载"
        
        try:
            import torch
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    temperature=temperature,
                    do_sample=True
                )
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            return response[len(prompt):].strip()
        except Exception as e:
            return f"Error: 本地模型生成失败 - {str(e)}"
    
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """对话模式"""
        # 将消息列表转换为prompt
        prompt = self._messages_to_prompt(messages)
        return self.generate(prompt, **kwargs)
    
    def _messages_to_prompt(self, messages: List[Dict[str, str]]) -> str:
        """将消息列表转换为prompt字符串"""
        prompt_parts = []
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            if role == 'system':
                prompt_parts.append(f"System: {content}")
            elif role == 'user':
                prompt_parts.append(f"User: {content}")
            elif role == 'assistant':
                prompt_parts.append(f"Assistant: {content}")
        prompt_parts.append("Assistant: ")
        return "\n".join(prompt_parts)


class OpenAICompatibleClient(BaseLLMClient):
    """OpenAI兼容API客户端"""
    
    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.model = model
    
    def generate(self, prompt: str, max_tokens: int = 500, temperature: float = 0.7, **kwargs) -> str:
        """使用OpenAI兼容API生成"""
        messages = [{"role": "user", "content": prompt}]
        return self.chat(messages, max_tokens=max_tokens, temperature=temperature)
    
    def chat(self, messages: List[Dict[str, str]], max_tokens: int = 500, 
             temperature: float = 0.7, stream: bool = False, **kwargs) -> str:
        """对话模式"""
        headers = {
            'Authorization': f"Bearer {self.api_key}",
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': self.model,
            'messages': messages,
            'temperature': temperature,
            'max_tokens': max_tokens,
            'stream': stream
        }
        
        url = f"{self.base_url}/chat/completions"
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=60)
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']
        except Exception as e:
            return f"Error: API调用失败 - {str(e)}"
    
    def chat_stream(self, messages: List[Dict[str, str]], max_tokens: int = 500,
                    temperature: float = 0.7, **kwargs) -> Generator[str, None, None]:
        """流式对话"""
        headers = {
            'Authorization': f"Bearer {self.api_key}",
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': self.model,
            'messages': messages,
            'temperature': temperature,
            'max_tokens': max_tokens,
            'stream': True
        }
        
        url = f"{self.base_url}/chat/completions"
        
        try:
            response = requests.post(url, headers=headers, json=data, stream=True, timeout=60)
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
                        if 'choices' in chunk and len(chunk['choices']) > 0:
                            delta = chunk['choices'][0].get('delta', {})
                            content = delta.get('content', '')
                            if content:
                                yield content
                    except:
                        pass
        except Exception as e:
            yield f"Error: API流式调用失败 - {str(e)}"


class GeminiClient(BaseLLMClient):
    """Google Gemini API客户端"""
    
    def __init__(self, api_key: str, model: str = "gemini-1.5-pro"):
        self.api_key = api_key
        self.model = model
    
    def generate(self, prompt: str, max_tokens: int = 500, temperature: float = 0.7, **kwargs) -> str:
        """使用Gemini API生成"""
        messages = [{"role": "user", "content": prompt}]
        return self.chat(messages, max_tokens=max_tokens, temperature=temperature)
    
    def chat(self, messages: List[Dict[str, str]], max_tokens: int = 500,
             temperature: float = 0.7, **kwargs) -> str:
        """对话模式"""
        # 转换消息格式为Gemini格式
        contents = []
        for msg in messages:
            role = "user" if msg['role'] == 'user' else "model"
            contents.append({"role": role, "parts": [{"text": msg['content']}]})
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        
        data = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens
            }
        }
        
        try:
            response = requests.post(url, json=data, timeout=60)
            response.raise_for_status()
            result = response.json()
            return result['candidates'][0]['content']['parts'][0]['text']
        except Exception as e:
            return f"Error: Gemini API调用失败 - {str(e)}"


class ClaudeClient(BaseLLMClient):
    """Anthropic Claude API客户端"""
    
    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.anthropic.com/v1"
    
    def generate(self, prompt: str, max_tokens: int = 500, temperature: float = 0.7, **kwargs) -> str:
        """使用Claude API生成"""
        messages = [{"role": "user", "content": prompt}]
        return self.chat(messages, max_tokens=max_tokens, temperature=temperature)
    
    def chat(self, messages: List[Dict[str, str]], max_tokens: int = 500,
             temperature: float = 0.7, **kwargs) -> str:
        """对话模式"""
        headers = {
            'x-api-key': self.api_key,
            'anthropic-version': '2023-06-01',
            'Content-Type': 'application/json'
        }
        
        # 分离system消息
        system_msg = ""
        chat_messages = []
        for msg in messages:
            if msg['role'] == 'system':
                system_msg = msg['content']
            else:
                chat_messages.append(msg)
        
        data = {
            'model': self.model,
            'messages': chat_messages,
            'temperature': temperature,
            'max_tokens': max_tokens
        }
        if system_msg:
            data['system'] = system_msg
        
        url = f"{self.base_url}/messages"
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=60)
            response.raise_for_status()
            result = response.json()
            return result['content'][0]['text']
        except Exception as e:
            return f"Error: Claude API调用失败 - {str(e)}"


class UnifiedLLMClient:
    """统一LLM客户端，自动选择本地模型或外部API"""
    
    # 默认API配置
    DEFAULT_CONFIGS = {
        'openai': {
            'api_key': '',
            'base_url': 'https://api.openai.com/v1',
            'model': 'gpt-4o',
            'enabled': False
        },
        'claude': {
            'api_key': '',
            'base_url': 'https://api.anthropic.com',
            'model': 'claude-3-5-sonnet-20241022',
            'enabled': False
        },
        'deepseek': {
            'api_key': '',
            'base_url': 'https://api.deepseek.com',
            'model': 'deepseek-chat',
            'enabled': False
        },
        'gemini': {
            'api_key': '',
            'model': 'gemini-1.5-pro',
            'enabled': False
        },
        'qwen': {
            'api_key': '',
            'base_url': 'https://dashscope.aliyuncs.com/api/v1',
            'model': 'qwen-max',
            'enabled': False
        },
        'moonshot': {
            'api_key': '',
            'base_url': 'https://api.moonshot.cn/v1',
            'model': 'moonshot-v1-8k',
            'enabled': False
        },
        'zhipu': {
            'api_key': '',
            'base_url': 'https://open.bigmodel.cn/api/paas/v4',
            'model': 'glm-4',
            'enabled': False
        }
    }
    
    def __init__(self, model=None, tokenizer=None, config: Dict = None):
        """
        初始化统一LLM客户端
        
        Args:
            model: 本地模型（可选）
            tokenizer: 本地tokenizer（可选）
            config: API配置字典（可选）
        """
        self.local_client = None
        self.api_client = None
        self.config = config or {}
        
        # 如果有本地模型，优先使用
        if model and tokenizer:
            self.local_client = LocalModelClient(model, tokenizer)
        
        # 初始化API客户端
        self._init_api_client()
    
    def _init_api_client(self):
        """初始化API客户端"""
        # 检查是否有启用的API配置
        for provider, cfg in self.config.items():
            if cfg.get('enabled') and cfg.get('api_key'):
                try:
                    if provider == 'openai' or provider == 'deepseek' or provider == 'qwen' or provider == 'moonshot' or provider == 'zhipu':
                        self.api_client = OpenAICompatibleClient(
                            api_key=cfg['api_key'],
                            base_url=cfg['base_url'],
                            model=cfg['model']
                        )
                        self.provider = provider
                        print(f"✅ 已连接到 {provider} API")
                        return
                    elif provider == 'claude':
                        self.api_client = ClaudeClient(
                            api_key=cfg['api_key'],
                            model=cfg['model']
                        )
                        self.provider = provider
                        print(f"✅ 已连接到 {provider} API")
                        return
                    elif provider == 'gemini':
                        self.api_client = GeminiClient(
                            api_key=cfg['api_key'],
                            model=cfg['model']
                        )
                        self.provider = provider
                        print(f"✅ 已连接到 {provider} API")
                        return
                except Exception as e:
                    print(f"⚠️ 初始化 {provider} API失败: {e}")
        
        self.provider = 'local'
    
    def generate(self, prompt: str, max_tokens: int = 500, temperature: float = 0.7, **kwargs) -> str:
        """
        生成文本
        优先使用API，如果API不可用则使用本地模型
        """
        # 优先使用API
        if self.api_client:
            try:
                return self.api_client.generate(prompt, max_tokens=max_tokens, temperature=temperature, **kwargs)
            except Exception as e:
                print(f"API调用失败，回退到本地模型: {e}")
        
        # 使用本地模型
        if self.local_client:
            return self.local_client.generate(prompt, max_tokens=max_tokens, temperature=temperature, **kwargs)
        
        return "Error: 没有可用的LLM客户端"
    
    def chat(self, messages: List[Dict[str, str]], max_tokens: int = 500,
             temperature: float = 0.7, **kwargs) -> str:
        """
        对话模式
        优先使用API，如果API不可用则使用本地模型
        """
        # 优先使用API
        if self.api_client:
            try:
                return self.api_client.chat(messages, max_tokens=max_tokens, temperature=temperature, **kwargs)
            except Exception as e:
                print(f"API调用失败，回退到本地模型: {e}")
        
        # 使用本地模型
        if self.local_client:
            return self.local_client.chat(messages, max_tokens=max_tokens, temperature=temperature, **kwargs)
        
        return "Error: 没有可用的LLM客户端"
    
    def is_api_available(self) -> bool:
        """检查API是否可用"""
        return self.api_client is not None
    
    def get_provider(self) -> str:
        """获取当前使用的提供商"""
        return getattr(self, 'provider', 'local')


# 全局客户端实例
_unified_client = None

def get_unified_llm_client(model=None, tokenizer=None, config: Dict = None) -> UnifiedLLMClient:
    """获取统一LLM客户端单例"""
    global _unified_client
    if _unified_client is None:
        _unified_client = UnifiedLLMClient(model, tokenizer, config)
    return _unified_client


def update_llm_config(config: Dict):
    """更新LLM配置"""
    global _unified_client
    _unified_client = UnifiedLLMClient(config=config)


if __name__ == "__main__":
    # 测试代码
    print("统一LLM客户端测试")
    
    # 测试配置
    test_config = {
        'openai': {
            'api_key': 'test-key',
            'base_url': 'https://api.openai.com/v1',
            'model': 'gpt-4o',
            'enabled': False  # 设置为True需要真实API密钥
        }
    }
    
    client = UnifiedLLMClient(config=test_config)
    print(f"当前提供商: {client.get_provider()}")
    
    # 测试生成
    if client.is_api_available():
        response = client.generate("Hello, how are you?")
        print(f"API响应: {response}")
    else:
        print("API未配置，使用本地模式")
