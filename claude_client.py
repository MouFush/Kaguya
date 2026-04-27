"""
Claude API 客户端 - 辉夜AI平台
支持通过 haiio.xyz 调用 Claude 模型
"""

import json
import os
from typing import Optional, Dict, Any, List, AsyncGenerator
import httpx
from dataclasses import dataclass


@dataclass
class ClaudeMessage:
    role: str
    content: str


@dataclass
class ClaudeResponse:
    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: Optional[str] = None


class ClaudeClient:
    """Claude API 客户端"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        config_path: Optional[str] = None
    ):
        """
        初始化 Claude 客户端

        Args:
            api_key: API 密钥，如果不提供则从配置文件读取
            base_url: API 基础 URL，如果不提供则从配置文件读取
            config_path: 配置文件路径
        """
        self.config = self._load_config(config_path)

        self.api_key = api_key or self.config.get("api_key")
        self.base_url = base_url or self.config.get("base_url", "https://api.haiio.xyz/")
        self.default_model = self.config.get("default_model", "claude-sonnet-4-6")
        self.timeout = self.config.get("timeout", 120)

        if not self.api_key:
            raise ValueError("API 密钥不能为空，请提供 api_key 或在配置文件中设置")

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            timeout=self.timeout
        )

    def _load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """加载配置文件"""
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "claude_api_config.json"
            )

        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    async def chat(
        self,
        messages: List[ClaudeMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False
    ) -> ClaudeResponse:
        """
        发送聊天请求

        Args:
            messages: 消息列表
            model: 模型名称，默认使用配置中的默认模型
            temperature: 温度参数 (0-1)
            max_tokens: 最大生成令牌数
            stream: 是否流式输出

        Returns:
            ClaudeResponse 对象
        """
        model = model or self.default_model

        payload = {
            "model": model,
            "messages": [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
        }

        try:
            response = await self.client.post("/v1/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()

            return ClaudeResponse(
                content=data["choices"][0]["message"]["content"],
                model=data["model"],
                usage=data.get("usage", {}),
                finish_reason=data["choices"][0].get("finish_reason")
            )

        except httpx.HTTPStatusError as e:
            raise Exception(f"API 请求失败: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise Exception(f"请求出错: {str(e)}")

    async def chat_stream(
        self,
        messages: List[ClaudeMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> AsyncGenerator[str, None]:
        """
        流式聊天请求

        Args:
            messages: 消息列表
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大生成令牌数

        Yields:
            生成的文本片段
        """
        model = model or self.default_model

        payload = {
            "model": model,
            "messages": [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True
        }

        try:
            async with self.client.stream(
                "POST", "/v1/chat/completions",
                json=payload
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break

                        try:
                            chunk = json.loads(data)
                            if "choices" in chunk and len(chunk["choices"]) > 0:
                                delta = chunk["choices"][0].get("delta", {})
                                if "content" in delta:
                                    yield delta["content"]
                        except json.JSONDecodeError:
                            continue

        except Exception as e:
            raise Exception(f"流式请求出错: {str(e)}")

    async def simple_chat(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7
    ) -> str:
        """
        简单聊天接口

        Args:
            prompt: 用户输入
            system_prompt: 系统提示词
            model: 模型名称
            temperature: 温度参数

        Returns:
            模型回复文本
        """
        messages = []

        if system_prompt:
            messages.append(ClaudeMessage(role="system", content=system_prompt))

        messages.append(ClaudeMessage(role="user", content=prompt))

        response = await self.chat(messages, model=model, temperature=temperature)
        return response.content

    def get_available_models(self) -> Dict[str, Dict[str, Any]]:
        """获取可用的模型列表"""
        return self.config.get("models", {})

    async def close(self):
        """关闭客户端连接"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# 便捷函数
async def quick_chat(
    prompt: str,
    api_key: Optional[str] = None,
    model: str = "claude-sonnet-4-6",
    temperature: float = 0.7
) -> str:
    """
    快速聊天函数

    Args:
        prompt: 用户输入
        api_key: API 密钥
        model: 模型名称
        temperature: 温度参数

    Returns:
        模型回复
    """
    async with ClaudeClient(api_key=api_key) as client:
        return await client.simple_chat(prompt, model=model, temperature=temperature)


# 示例用法
if __name__ == "__main__":
    import asyncio

    async def main():
        # 方式1: 使用配置文件
        client = ClaudeClient()

        # 查看可用模型
        print("可用模型:")
        for model_id, model_info in client.get_available_models().items():
            print(f"  - {model_info['name']}: {model_info['description']}")

        # 简单对话
        print("\n测试对话:")
        response = await client.simple_chat(
            prompt="你好，请介绍一下自己",
            model="claude-sonnet-4-6"
        )
        print(f"回复: {response}")

        # 带历史记录的对话
        messages = [
            ClaudeMessage(role="user", content="什么是机器学习？"),
            ClaudeMessage(role="assistant", content="机器学习是人工智能的一个分支..."),
            ClaudeMessage(role="user", content="能举个例子吗？")
        ]

        response = await client.chat(messages, model="claude-sonnet-4-6")
        print(f"\n上下文回复: {response.content}")

        await client.close()

    # 运行示例
    asyncio.run(main())
