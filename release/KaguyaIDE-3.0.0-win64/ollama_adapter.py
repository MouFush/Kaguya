#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ollama 适配器模块
将 Ollama API 封装为与原 Qwen3.5-9B 模型接口兼容的形式
使用 urllib 实现，无需额外依赖
"""

import json
import re
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Generator, Any, Tuple
from dataclasses import dataclass, field
import threading


class ThinkingFilterStrategy(ABC):
    """思考过程过滤策略抽象基类"""

    @abstractmethod
    def filter(self, content: str, thinking: str) -> Tuple[Optional[str], Optional[str]]:
        """
        过滤思考过程

        Args:
            content: 消息的content字段
            thinking: 消息的thinking字段

        Returns:
            (filtered_content, filtered_thinking) 过滤后的内容和思考过程
            如果某个字段应该被过滤掉，则返回None
        """
        pass

    @abstractmethod
    def flush(self) -> Tuple[Optional[str], Optional[str]]:
        """
        刷新缓冲区，返回剩余内容

        Returns:
            (remaining_content, remaining_thinking) 缓冲区中剩余的内容
        """
        pass

    @abstractmethod
    def reset(self):
        """重置策略状态（用于流式处理）"""
        pass


class NoFilterStrategy(ThinkingFilterStrategy):
    """不过滤策略：直接输出所有内容"""

    def filter(self, content: str, thinking: str) -> Tuple[Optional[str], Optional[str]]:
        return (content if content else None), (thinking if thinking else None)

    def flush(self) -> Tuple[Optional[str], Optional[str]]:
        return None, None

    def reset(self):
        pass


class FieldBasedStrategy(ThinkingFilterStrategy):
    """基于字段的过滤策略：优先使用thinking字段分离思考过程"""

    def filter(self, content: str, thinking: str) -> Tuple[Optional[str], Optional[str]]:
        filtered_thinking = thinking if thinking else None
        return (content if content else None), filtered_thinking

    def flush(self) -> Tuple[Optional[str], Optional[str]]:
        return None, None

    def reset(self):
        pass


class RegexBasedStrategy(ThinkingFilterStrategy):
    """基于正则表达式的过滤策略：从content中提取思考过程"""

    DEFAULT_START_PATTERNS = [
        r"Thinking\s*Process",
        r"思考过程",
        r"Thought\s*Process",
    ]
    DEFAULT_END_PATTERNS = [
        r"\n\n",
        r"\n[哼辉夜]",
    ]

    def __init__(self, start_patterns: List[str] = None, end_patterns: List[str] = None):
        self._start_patterns = [re.compile(p, re.MULTILINE) for p in (start_patterns or self.DEFAULT_START_PATTERNS)]
        self._end_patterns = [re.compile(p, re.MULTILINE) for p in (end_patterns or self.DEFAULT_END_PATTERNS)]
        self._in_thinking = False
        self._buffer = ""

    def filter(self, content: str, thinking: str) -> Tuple[Optional[str], Optional[str]]:
        if not content:
            return None, (thinking if thinking else None)

        self._buffer += content
        results = {"content": None, "thinking": None}

        if not self._in_thinking:
            for pattern in self._start_patterns:
                match = pattern.search(self._buffer)
                if match:
                    self._in_thinking = True
                    before = self._buffer[:match.start()]
                    self._buffer = self._buffer[match.start():]
                    if before:
                        results["content"] = before
                    break

            if not self._in_thinking:
                result = self._buffer
                self._buffer = ""
                return result, (thinking if thinking else None)

        if self._in_thinking:
            for pattern in self._end_patterns:
                match = pattern.search(self._buffer)
                if match:
                    self._in_thinking = False
                    thinking_content = self._buffer[:match.end()]
                    formal_content = self._buffer[match.end():]
                    self._buffer = ""
                    results["thinking"] = thinking_content
                    if formal_content:
                        results["content"] = formal_content
                    return results["content"], results["thinking"]
            return results["content"], None

    def flush(self) -> Tuple[Optional[str], Optional[str]]:
        if self._in_thinking and self._buffer.strip():
            remaining = self._buffer
            self._buffer = ""
            self._in_thinking = False
            return remaining, None
        self._buffer = ""
        self._in_thinking = False
        return None, None

    def reset(self):
        self._in_thinking = False
        self._buffer = ""


@dataclass
class OllamaConfig:
    """Ollama 配置"""
    base_url: str = "http://localhost:11434"
    model: str = "qwen3.5:4b"
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 0.9
    timeout: int = 120
    num_gpu: int = -1
    use_gpu: bool = True
    thinking_filter_strategy: str = "field_based"
    thinking_start_patterns: List[str] = field(default_factory=list)
    thinking_end_patterns: List[str] = field(default_factory=list)


class OllamaAdapter:
    """Ollama API 适配器"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, config: OllamaConfig = None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config: OllamaConfig = None):
        if self._initialized:
            if config:
                self.config = config
            return
        self._initialized = True
        self.config = config or OllamaConfig()
        self._model_loaded = False

    def _create_filter_strategy(self) -> ThinkingFilterStrategy:
        """根据配置创建过滤策略"""
        strategy_type = self.config.thinking_filter_strategy

        if strategy_type == "none":
            return NoFilterStrategy()
        elif strategy_type == "field_based":
            return FieldBasedStrategy()
        elif strategy_type == "regex_based":
            start_patterns = self.config.thinking_start_patterns or None
            end_patterns = self.config.thinking_end_patterns or None
            return RegexBasedStrategy(start_patterns, end_patterns)
        else:
            return FieldBasedStrategy()
    
    def _request(self, endpoint: str, data: dict = None, stream: bool = False) -> Any:
        """发送 HTTP 请求"""
        url = f"{self.config.base_url}{endpoint}"
        headers = {"Content-Type": "application/json"}
        
        if data:
            body = json.dumps(data, ensure_ascii=False).encode('utf-8')
            req = urllib.request.Request(url, data=body, headers=headers, method='POST')
        else:
            req = urllib.request.Request(url, headers=headers, method='GET')
        
        try:
            response = urllib.request.urlopen(req, timeout=self.config.timeout)
            if stream:
                return response
            result = json.loads(response.read().decode('utf-8'))
            response.close()
            return result
        except urllib.error.URLError as e:
            raise ConnectionError(f"无法连接到 Ollama 服务: {e}")
    
    def is_server_running(self) -> bool:
        """检查 Ollama 服务是否运行"""
        try:
            response = self._request("/api/tags")
            return True
        except:
            return False
    
    def list_models(self) -> List[Dict]:
        """列出可用模型"""
        try:
            data = self._request("/api/tags")
            return data.get('models', [])
        except Exception as e:
            print(f"获取模型列表失败: {e}")
            return []
    
    def is_model_available(self, model_name: str = None) -> bool:
        """检查模型是否可用"""
        models = self.list_models()
        target = model_name or self.config.model
        return any(m.get('name', '').startswith(target) for m in models)
    
    def chat(
        self,
        messages: List[Dict],
        temperature: float = None,
        max_tokens: int = None,
        **kwargs
    ) -> str:
        """
        非流式对话
        
        Args:
            messages: 消息列表 [{"role": "user/assistant/system", "content": "..."}]
            temperature: 温度参数
            max_tokens: 最大生成 token 数
            **kwargs: 其他参数
        
        Returns:
            模型回复文本
        """
        data = {
            "model": self.config.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature or self.config.temperature,
                "num_predict": max_tokens or self.config.max_tokens,
                "top_p": kwargs.get('top_p', self.config.top_p),
                "num_gpu": self.config.num_gpu if self.config.use_gpu else 0,
            }
        }
        
        try:
            result = self._request("/api/chat", data)
            message = result.get('message', {})
            content = message.get('content', '')
            thinking = message.get('thinking', '')
            # 优先返回 content，如果为空则返回 thinking
            return content if content else thinking
        except Exception as e:
            print(f"Ollama chat 错误: {e}")
            raise
    
    def chat_stream(
        self,
        messages: List[Dict],
        temperature: float = None,
        max_tokens: int = None,
        **kwargs
    ) -> Generator[tuple, None, None]:
        """
        流式对话
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大生成 token 数
            **kwargs: 其他参数
        
        Yields:
            (type, content) 元组，type 为 'content' 或 'thinking'
        """
        strategy = self._create_filter_strategy()

        data = {
            "model": self.config.model,
            "messages": messages,
            "stream": True,
            "think": False,
            "options": {
                "temperature": temperature or self.config.temperature,
                "num_predict": max_tokens or self.config.max_tokens,
                "top_p": kwargs.get('top_p', self.config.top_p),
                "num_gpu": self.config.num_gpu if self.config.use_gpu else 0,
            }
        }
        
        try:
            response = self._request("/api/chat", data, stream=True)
            
            for line in response:
                if line:
                    try:
                        line_str = line.decode('utf-8') if isinstance(line, bytes) else line
                        if not line_str.strip():
                            continue
                        chunk = json.loads(line_str)
                        message = chunk.get('message', {})
                        
                        content = message.get('content', '')
                        thinking = message.get('thinking', '')
                        
                        filtered_content, filtered_thinking = strategy.filter(content, thinking)
                        
                        if filtered_content:
                            yield ('content', filtered_content)
                        if filtered_thinking:
                            yield ('thinking', filtered_thinking)
                        
                        if chunk.get('done', False):
                            remaining_content, remaining_thinking = strategy.flush()
                            if remaining_content:
                                yield ('content', remaining_content)
                            if remaining_thinking:
                                yield ('thinking', remaining_thinking)
                            break
                    except json.JSONDecodeError as e:
                        print(f"JSON解析错误: {e}, line: {line}")
                        continue
        except Exception as e:
            print(f"Ollama chat_stream 错误: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def generate(
        self,
        prompt: str,
        temperature: float = None,
        max_tokens: int = None,
        **kwargs
    ) -> str:
        """
        简单文本生成
        
        Args:
            prompt: 输入提示词
            temperature: 温度参数
            max_tokens: 最大生成 token 数
        
        Returns:
            生成的文本
        """
        data = {
            "model": self.config.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature or self.config.temperature,
                "num_predict": max_tokens or self.config.max_tokens,
                "top_p": kwargs.get('top_p', self.config.top_p),
            }
        }
        
        try:
            result = self._request("/api/generate", data)
            return result.get('response', '')
        except Exception as e:
            print(f"Ollama generate 错误: {e}")
            raise
    
    def generate_stream(
        self,
        prompt: str,
        temperature: float = None,
        max_tokens: int = None,
        **kwargs
    ) -> Generator[str, None, None]:
        """
        流式文本生成
        
        Args:
            prompt: 输入提示词
            temperature: 温度参数
            max_tokens: 最大生成 token 数
        
        Yields:
            生成的文本片段
        """
        data = {
            "model": self.config.model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": temperature or self.config.temperature,
                "num_predict": max_tokens or self.config.max_tokens,
                "top_p": kwargs.get('top_p', self.config.top_p),
            }
        }
        
        try:
            response = self._request("/api/generate", data, stream=True)
            for line in response:
                if line:
                    try:
                        chunk = json.loads(line.decode('utf-8'))
                        content = chunk.get('response', '')
                        if content:
                            yield content
                        if chunk.get('done', False):
                            break
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"Ollama generate_stream 错误: {e}")
            raise
    
    def embeddings(self, text: str) -> List[float]:
        """
        获取文本嵌入向量
        
        Args:
            text: 输入文本
        
        Returns:
            嵌入向量
        """
        data = {
            "model": self.config.model,
            "prompt": text
        }
        
        try:
            result = self._request("/api/embeddings", data)
            return result.get('embedding', [])
        except Exception as e:
            print(f"Ollama embeddings 错误: {e}")
            return []
    
    def count_tokens(self, text: str) -> int:
        """
        计算 token 数量（近似）
        
        Args:
            text: 输入文本
        
        Returns:
            token 数量
        """
        return len(text) // 2


class OllamaModel:
    """
    兼容原 Qwen3.5-9B 接口的 Ollama 模型包装器
    提供与 transformers 模型类似的接口
    """
    
    def __init__(self, config: OllamaConfig = None):
        self.adapter = OllamaAdapter(config)
        self.device = "ollama"
        self._tokenizer = None
    
    @property
    def tokenizer(self):
        if self._tokenizer is None:
            self._tokenizer = OllamaTokenizer(self.adapter)
        return self._tokenizer
    
    def generate(
        self,
        input_ids=None,
        max_new_tokens: int = 512,
        do_sample: bool = True,
        temperature: float = 0.7,
        top_p: float = 0.9,
        pad_token_id=None,
        **kwargs
    ):
        """
        兼容 transformers 的 generate 方法
        """
        if input_ids is None:
            raise ValueError("input_ids 不能为空")
        
        prompt = self._tokenizer.decode(input_ids[0])
        
        result = self.adapter.generate(
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_new_tokens
        )
        
        return OllamaOutput(result, self._tokenizer)
    
    def __call__(self, input_ids=None, use_cache=True, **kwargs):
        """兼容 transformers 的调用方式"""
        return self.generate(input_ids=input_ids, **kwargs)


class OllamaTokenizer:
    """
    兼容 transformers 的 Tokenizer 包装器
    """
    
    def __init__(self, adapter: OllamaAdapter):
        self.adapter = adapter
        self.eos_token_id = 0
        self.eos_token = ""
    
    def apply_chat_template(
        self,
        messages: List[Dict],
        tokenize: bool = True,
        add_generation_prompt: bool = True
    ) -> str:
        """
        应用聊天模板
        
        将消息列表转换为模型可理解的格式
        """
        prompt_parts = []
        
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            
            if role == 'system':
                prompt_parts.append(f"<|im_start|>system\n{content}<|im_end|>\n")
            elif role == 'user':
                prompt_parts.append(f"<|im_start|>user\n{content}<|im_end|>\n")
            elif role == 'assistant':
                prompt_parts.append(f"<|im_start|>assistant\n{content}<|im_end|>\n")
        
        if add_generation_prompt:
            prompt_parts.append("<|im_start|>assistant\n")
        
        result = "".join(prompt_parts)
        
        if tokenize:
            return self.encode(result)
        return result
    
    def encode(self, text: str) -> List[int]:
        """编码文本为 token ids（模拟）"""
        return list(range(len(text) // 2))
    
    def decode(self, token_ids, skip_special_tokens: bool = True) -> str:
        """解码 token ids 为文本"""
        if hasattr(token_ids, 'tolist'):
            token_ids = token_ids.tolist()
        if isinstance(token_ids, list) and len(token_ids) > 0:
            if isinstance(token_ids[0], list):
                token_ids = token_ids[0]
        return str(token_ids) if not isinstance(token_ids, str) else token_ids
    
    def __call__(self, text: List[str], return_tensors: str = "pt") -> Dict:
        """调用编码"""
        encoded = [self.encode(t) for t in text]
        max_len = max(len(e) for e in encoded)
        padded = [e + [0] * (max_len - len(e)) for e in encoded]
        
        return {"input_ids": padded}


class OllamaOutput:
    """模型输出包装器"""
    
    def __init__(self, text: str, tokenizer: OllamaTokenizer):
        self._text = text
        self._tokenizer = tokenizer
        self.past_key_values = None
        self.logits = None
    
    @property
    def sequences(self):
        return self._tokenizer.encode(self._text)
    
    def __getitem__(self, key):
        if key == 0:
            return self.sequences
        raise IndexError(f"索引 {key} 超出范围")


_ollama_instance: Optional[OllamaAdapter] = None
_ollama_lock = threading.Lock()


def get_ollama_adapter(config: OllamaConfig = None) -> OllamaAdapter:
    """获取全局 Ollama 适配器实例"""
    global _ollama_instance
    if _ollama_instance is None:
        with _ollama_lock:
            if _ollama_instance is None:
                _ollama_instance = OllamaAdapter(config)
    elif config:
        _ollama_instance.config = config
    return _ollama_instance


def load_ollama_model(model_name: str = "qwen3.5:4b") -> Tuple[OllamaModel, OllamaTokenizer]:
    """
    加载 Ollama 模型（兼容原 load_model 接口）
    
    Args:
        model_name: 模型名称
    
    Returns:
        (model, tokenizer) 元组
    """
    config = OllamaConfig(model=model_name)
    model = OllamaModel(config)
    return model, model.tokenizer


def chat_with_ollama(
    message: str,
    history: List[Tuple[str, str]] = None,
    system_prompt: str = None,
    temperature: float = 0.7,
    max_tokens: int = 512
) -> str:
    """
    使用 Ollama 进行对话（便捷函数）
    
    Args:
        message: 用户消息
        history: 历史对话 [(user_msg, assistant_msg), ...]
        system_prompt: 系统提示词
        temperature: 温度参数
        max_tokens: 最大生成 token 数
    
    Returns:
        模型回复
    """
    adapter = get_ollama_adapter()
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    
    if history:
        for user_msg, assistant_msg in history:
            messages.append({"role": "user", "content": user_msg})
            messages.append({"role": "assistant", "content": assistant_msg})
    
    messages.append({"role": "user", "content": message})
    
    return adapter.chat(messages, temperature=temperature, max_tokens=max_tokens)


def stream_chat_with_ollama(
    message: str,
    history: List[Tuple[str, str]] = None,
    system_prompt: str = None,
    temperature: float = 0.7,
    max_tokens: int = 512
) -> Generator[str, None, None]:
    """
    使用 Ollama 进行流式对话（便捷函数）
    
    Args:
        message: 用户消息
        history: 历史对话
        system_prompt: 系统提示词
        temperature: 温度参数
        max_tokens: 最大生成 token 数
    
    Yields:
        生成的文本片段
    """
    adapter = get_ollama_adapter()
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    
    if history:
        for user_msg, assistant_msg in history:
            messages.append({"role": "user", "content": user_msg})
            messages.append({"role": "assistant", "content": assistant_msg})
    
    messages.append({"role": "user", "content": message})
    
    yield from adapter.chat_stream(messages, temperature=temperature, max_tokens=max_tokens)


if __name__ == '__main__':
    print("=" * 60)
    print("Ollama 适配器测试")
    print("=" * 60)
    
    adapter = get_ollama_adapter()
    
    print(f"\nOllama 服务状态: {'运行中' if adapter.is_server_running() else '未运行'}")
    
    if adapter.is_server_running():
        print("\n可用模型:")
        for model in adapter.list_models():
            print(f"  - {model.get('name')} ({model.get('size', 'unknown')})")
        
        print(f"\n模型 qwen3.5:4b 可用: {adapter.is_model_available('qwen3.5:4b')}")
        
        print("\n测试对话...")
        response = chat_with_ollama(
            "你好，请用一句话介绍自己",
            system_prompt="你是一个有帮助的AI助手。"
        )
        print(f"回复: {response}")
    else:
        print("\n请先启动 Ollama 服务")
