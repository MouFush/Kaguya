#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高级MCP (Model Context Protocol) 系统
实现标准化的模型上下文协议，支持工具调用、资源访问和提示词模板
"""

import json
import asyncio
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
from datetime import datetime
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MCPMessageType(Enum):
    """MCP消息类型"""
    INITIALIZE = "initialize"
    TOOLS_LIST = "tools/list"
    TOOLS_CALL = "tools/call"
    RESOURCES_LIST = "resources/list"
    RESOURCES_READ = "resources/read"
    PROMPTS_LIST = "prompts/list"
    PROMPTS_GET = "prompts/get"
    NOTIFICATION = "notification"
    PING = "ping"


@dataclass
class MCPTool:
    """MCP工具定义"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Optional[Callable] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema
        }


@dataclass
class MCPResource:
    """MCP资源定义"""
    uri: str
    name: str
    mime_type: str
    description: str
    handler: Optional[Callable] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "uri": self.uri,
            "name": self.name,
            "mimeType": self.mime_type,
            "description": self.description
        }


@dataclass
class MCPPrompt:
    """MCP提示词模板"""
    name: str
    description: str
    arguments: List[Dict[str, Any]]
    template: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "arguments": self.arguments
        }
    
    def render(self, **kwargs) -> str:
        """渲染提示词模板"""
        try:
            return self.template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"缺少模板参数: {e}")


class MCPServer:
    """MCP服务器 - 实现Model Context Protocol"""
    
    def __init__(self, name: str = "Kaguya AI", version: str = "1.0.0"):
        self.name = name
        self.version = version
        self.tools: Dict[str, MCPTool] = {}
        self.resources: Dict[str, MCPResource] = {}
        self.prompts: Dict[str, MCPPrompt] = {}
        self.capabilities = {
            "tools": {"listChanged": True},
            "resources": {"listChanged": True, "subscribe": True},
            "prompts": {"listChanged": True}
        }
        
    def register_tool(self, tool: MCPTool):
        """注册工具"""
        self.tools[tool.name] = tool
        logger.info(f"注册MCP工具: {tool.name}")
    
    def register_resource(self, resource: MCPResource):
        """注册资源"""
        self.resources[resource.uri] = resource
        logger.info(f"注册MCP资源: {resource.uri}")
    
    def register_prompt(self, prompt: MCPPrompt):
        """注册提示词模板"""
        self.prompts[prompt.name] = prompt
        logger.info(f"注册MCP提示词: {prompt.name}")
    
    async def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """处理MCP消息"""
        msg_type = message.get("type")
        msg_id = message.get("id")
        
        try:
            if msg_type == MCPMessageType.INITIALIZE.value:
                return await self._handle_initialize(msg_id)
            elif msg_type == MCPMessageType.TOOLS_LIST.value:
                return await self._handle_tools_list(msg_id)
            elif msg_type == MCPMessageType.TOOLS_CALL.value:
                return await self._handle_tools_call(msg_id, message.get("params", {}))
            elif msg_type == MCPMessageType.RESOURCES_LIST.value:
                return await self._handle_resources_list(msg_id)
            elif msg_type == MCPMessageType.RESOURCES_READ.value:
                return await self._handle_resources_read(msg_id, message.get("params", {}))
            elif msg_type == MCPMessageType.PROMPTS_LIST.value:
                return await self._handle_prompts_list(msg_id)
            elif msg_type == MCPMessageType.PROMPTS_GET.value:
                return await self._handle_prompts_get(msg_id, message.get("params", {}))
            elif msg_type == MCPMessageType.PING.value:
                return {"type": "pong", "id": msg_id}
            else:
                return self._error_response(msg_id, f"未知消息类型: {msg_type}")
        except Exception as e:
            logger.error(f"处理MCP消息失败: {e}")
            return self._error_response(msg_id, str(e))
    
    async def _handle_initialize(self, msg_id: str) -> Dict[str, Any]:
        """处理初始化请求"""
        return {
            "type": "initialize",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": self.capabilities,
                "serverInfo": {
                    "name": self.name,
                    "version": self.version
                }
            }
        }
    
    async def _handle_tools_list(self, msg_id: str) -> Dict[str, Any]:
        """处理工具列表请求"""
        return {
            "type": "tools/list",
            "id": msg_id,
            "result": {
                "tools": [tool.to_dict() for tool in self.tools.values()]
            }
        }
    
    async def _handle_tools_call(self, msg_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理工具调用请求"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if tool_name not in self.tools:
            return self._error_response(msg_id, f"工具不存在: {tool_name}")
        
        tool = self.tools[tool_name]
        if tool.handler is None:
            return self._error_response(msg_id, f"工具未实现: {tool_name}")
        
        try:
            # 调用工具处理器
            if asyncio.iscoroutinefunction(tool.handler):
                result = await tool.handler(**arguments)
            else:
                result = tool.handler(**arguments)
            
            return {
                "type": "tools/call",
                "id": msg_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, ensure_ascii=False) if isinstance(result, dict) else str(result)
                        }
                    ]
                }
            }
        except Exception as e:
            return self._error_response(msg_id, f"工具调用失败: {str(e)}")
    
    async def _handle_resources_list(self, msg_id: str) -> Dict[str, Any]:
        """处理资源列表请求"""
        return {
            "type": "resources/list",
            "id": msg_id,
            "result": {
                "resources": [resource.to_dict() for resource in self.resources.values()]
            }
        }
    
    async def _handle_resources_read(self, msg_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理资源读取请求"""
        uri = params.get("uri")
        
        if uri not in self.resources:
            return self._error_response(msg_id, f"资源不存在: {uri}")
        
        resource = self.resources[uri]
        if resource.handler is None:
            return self._error_response(msg_id, f"资源未实现: {uri}")
        
        try:
            content = resource.handler()
            return {
                "type": "resources/read",
                "id": msg_id,
                "result": {
                    "contents": [
                        {
                            "uri": uri,
                            "mimeType": resource.mime_type,
                            "text": content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
                        }
                    ]
                }
            }
        except Exception as e:
            return self._error_response(msg_id, f"资源读取失败: {str(e)}")
    
    async def _handle_prompts_list(self, msg_id: str) -> Dict[str, Any]:
        """处理提示词列表请求"""
        return {
            "type": "prompts/list",
            "id": msg_id,
            "result": {
                "prompts": [prompt.to_dict() for prompt in self.prompts.values()]
            }
        }
    
    async def _handle_prompts_get(self, msg_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理提示词获取请求"""
        prompt_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if prompt_name not in self.prompts:
            return self._error_response(msg_id, f"提示词不存在: {prompt_name}")
        
        prompt = self.prompts[prompt_name]
        try:
            rendered = prompt.render(**arguments)
            return {
                "type": "prompts/get",
                "id": msg_id,
                "result": {
                    "description": prompt.description,
                    "messages": [
                        {
                            "role": "user",
                            "content": {
                                "type": "text",
                                "text": rendered
                            }
                        }
                    ]
                }
            }
        except Exception as e:
            return self._error_response(msg_id, f"提示词渲染失败: {str(e)}")
    
    def _error_response(self, msg_id: str, error_msg: str) -> Dict[str, Any]:
        """生成错误响应"""
        return {
            "type": "error",
            "id": msg_id,
            "error": {
                "code": -32600,
                "message": error_msg
            }
        }


class MCPClient:
    """MCP客户端 - 用于连接MCP服务器"""
    
    def __init__(self, server_url: str):
        self.server_url = server_url
        self.capabilities = None
        self.initialized = False
    
    async def initialize(self) -> bool:
        """初始化连接"""
        try:
            response = await self._send_message({
                "type": "initialize",
                "id": str(uuid.uuid4()),
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "Kaguya MCP Client",
                        "version": "1.0.0"
                    }
                }
            })
            self.capabilities = response.get("result", {}).get("capabilities", {})
            self.initialized = True
            return True
        except Exception as e:
            logger.error(f"MCP初始化失败: {e}")
            return False
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """获取工具列表"""
        response = await self._send_message({
            "type": "tools/list",
            "id": str(uuid.uuid4())
        })
        return response.get("result", {}).get("tools", [])
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """调用工具"""
        response = await self._send_message({
            "type": "tools/call",
            "id": str(uuid.uuid4()),
            "params": {
                "name": name,
                "arguments": arguments
            }
        })
        return response.get("result", {})
    
    async def _send_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """发送消息到服务器"""
        # 这里可以实现HTTP或stdio传输
        # 简化实现，实际应根据server_url选择传输方式
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.server_url,
                json=message,
                headers={"Content-Type": "application/json"}
            ) as response:
                return await response.json()


# 全局MCP服务器实例
_mcp_server = None

def get_mcp_server() -> MCPServer:
    """获取全局MCP服务器实例"""
    global _mcp_server
    if _mcp_server is None:
        _mcp_server = MCPServer()
        _initialize_default_tools(_mcp_server)
    return _mcp_server

def _initialize_default_tools(server: MCPServer):
    """初始化默认工具"""
    # 注册计算器工具
    server.register_tool(MCPTool(
        name="calculator",
        description="执行数学计算",
        input_schema={
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "数学表达式，如 '2 + 2' 或 'sqrt(16)'"
                }
            },
            "required": ["expression"]
        },
        handler=lambda expression: safe_calculate(expression)
    ))
    
    # 注册文件读取工具
    server.register_tool(MCPTool(
        name="read_file",
        description="读取文件内容",
        input_schema={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "文件路径"
                }
            },
            "required": ["path"]
        },
        handler=lambda path: read_file_safe(path)
    ))
    
    # 注册网络搜索工具
    server.register_tool(MCPTool(
        name="web_search",
        description="搜索网络信息",
        input_schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词"
                },
                "max_results": {
                    "type": "integer",
                    "description": "最大结果数",
                    "default": 5
                }
            },
            "required": ["query"]
        },
        handler=lambda query, max_results=5: {"query": query, "results": f"搜索 {query} 的结果"}
    ))
    
    # 注册提示词模板
    server.register_prompt(MCPPrompt(
        name="code_review",
        description="代码审查提示词",
        arguments=[
            {"name": "code", "description": "需要审查的代码", "required": True},
            {"name": "language", "description": "编程语言", "required": False}
        ],
        template="""请审查以下{language}代码，找出潜在问题并提供改进建议：

```{language}
{code}
```

请从以下几个方面分析：
1. 代码质量和可读性
2. 潜在的错误或漏洞
3. 性能优化建议
4. 最佳实践遵循情况"""
    ))
    
    server.register_prompt(MCPPrompt(
        name="explain_concept",
        description="解释概念提示词",
        arguments=[
            {"name": "concept", "description": "需要解释的概念", "required": True},
            {"name": "level", "description": "解释难度级别", "required": False}
        ],
        template="""请以{level}级别解释以下概念：{concept}

请包括：
1. 基本定义
2. 核心原理
3. 实际应用场景
4. 相关示例"""
    ))

def safe_calculate(expression: str) -> Dict[str, Any]:
    """安全计算数学表达式"""
    try:
        from safe_code_executor import safe_eval
        result = safe_eval(expression)
        return {"result": result, "success": True}
    except Exception as e:
        return {"error": str(e), "success": False}

def read_file_safe(path: str) -> Dict[str, Any]:
    """安全读取文件"""
    try:
        import os
        # 安全检查：限制文件访问范围
        allowed_paths = ["./uploads", "./knowledge_base", "./prompts"]
        abs_path = os.path.abspath(path)
        
        if not any(abs_path.startswith(os.path.abspath(p)) for p in allowed_paths):
            return {"error": "路径不在允许范围内", "success": False}
        
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        return {"content": content, "success": True, "size": len(content)}
    except Exception as e:
        return {"error": str(e), "success": False}


if __name__ == "__main__":
    # 测试MCP服务器
    async def test_mcp():
        server = get_mcp_server()
        
        # 测试初始化
        response = await server.handle_message({
            "type": "initialize",
            "id": "test-1"
        })
        print("初始化响应:", json.dumps(response, indent=2, ensure_ascii=False))
        
        # 测试工具列表
        response = await server.handle_message({
            "type": "tools/list",
            "id": "test-2"
        })
        print("\n工具列表:", json.dumps(response, indent=2, ensure_ascii=False))
        
        # 测试工具调用
        response = await server.handle_message({
            "type": "tools/call",
            "id": "test-3",
            "params": {
                "name": "calculator",
                "arguments": {"expression": "2 + 3 * 4"}
            }
        })
        print("\n工具调用结果:", json.dumps(response, indent=2, ensure_ascii=False))
        
        # 测试提示词
        response = await server.handle_message({
            "type": "prompts/get",
            "id": "test-4",
            "params": {
                "name": "explain_concept",
                "arguments": {"concept": "MCP协议", "level": "初学者"}
            }
        })
        print("\n提示词结果:", json.dumps(response, indent=2, ensure_ascii=False))
    
    asyncio.run(test_mcp())
