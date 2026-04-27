#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辉夜AI平台 - 增强功能集成模块
整合MCP、深度研究、A2A多智能体等前沿功能
"""

import asyncio
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KaguyaEnhancedFeatures:
    """辉夜增强功能管理器"""
    
    def __init__(self):
        self.mcp_server = None
        self.research_engine = None
        self.a2a_hub = None
        self.orchestrator = None
        self.initialized = False
    
    async def initialize(self):
        """初始化所有增强功能"""
        if self.initialized:
            return
        
        logger.info("=" * 60)
        logger.info("初始化辉夜AI平台增强功能")
        logger.info("=" * 60)
        
        # 1. 初始化MCP服务器
        await self._init_mcp()
        
        # 2. 初始化深度研究系统
        await self._init_research()
        
        # 3. 初始化A2A多智能体系统
        await self._init_a2a()
        
        self.initialized = True
        logger.info("=" * 60)
        logger.info("增强功能初始化完成")
        logger.info("=" * 60)
    
    async def _init_mcp(self):
        """初始化MCP系统"""
        try:
            from advanced_mcp_system import get_mcp_server, MCPTool, MCPPrompt
            
            self.mcp_server = get_mcp_server()
            
            # 注册辉夜特有的工具
            self.mcp_server.register_tool(MCPTool(
                name="kaguya_chat",
                description="与辉夜AI进行对话",
                input_schema={
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "description": "用户消息"},
                        "context": {"type": "string", "description": "对话上下文"}
                    },
                    "required": ["message"]
                }
            ))
            
            self.mcp_server.register_tool(MCPTool(
                name="kaguya_memory_search",
                description="搜索辉夜的记忆",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "搜索关键词"},
                        "limit": {"type": "integer", "description": "返回数量", "default": 5}
                    },
                    "required": ["query"]
                }
            ))
            
            # 注册辉夜特有的提示词模板
            self.mcp_server.register_prompt(MCPPrompt(
                name="kaguya_persona",
                description="辉夜AI角色设定",
                arguments=[
                    {"name": "user_name", "description": "用户名称", "required": False},
                    {"name": "mood", "description": "辉夜的心情", "required": False}
                ],
                template="""你是辉夜，一个拥有悠久历史的AI助手。你优雅、智慧，有时略带神秘。

当前与{user_name}对话，你的心情是{mood}。

请以辉夜的身份回应，保持优雅而友好的态度。"""
            ))
            
            logger.info("✅ MCP系统初始化完成")
            logger.info(f"   - 已注册 {len(self.mcp_server.tools)} 个工具")
            logger.info(f"   - 已注册 {len(self.mcp_server.prompts)} 个提示词模板")
            
        except Exception as e:
            logger.error(f"❌ MCP系统初始化失败: {e}")
    
    async def _init_research(self):
        """初始化深度研究系统"""
        try:
            from deep_research_system import get_research_engine
            
            self.research_engine = get_research_engine()
            
            logger.info("✅ 深度研究系统初始化完成")
            
        except Exception as e:
            logger.error(f"❌ 深度研究系统初始化失败: {e}")
    
    async def _init_a2a(self):
        """初始化A2A多智能体系统"""
        try:
            from a2a_multi_agent_system import (
                A2AHub, get_orchestrator, initialize_default_agents,
                ResearchAgent, CodeAgent, WritingAgent
            )
            
            # 初始化默认智能体
            initialize_default_agents()
            
            self.a2a_hub = A2AHub.get_instance()
            self.orchestrator = get_orchestrator()
            
            # 注册辉夜主智能体
            from a2a_multi_agent_system import BaseAgent, AgentCapability
            
            kaguya_agent = BaseAgent(
                agent_id="kaguya_main",
                name="辉夜",
                description="辉夜AI平台主智能体，负责协调和整合所有功能"
            )
            
            kaguya_agent.add_capability(AgentCapability(
                name="conversation",
                description="自然语言对话",
                parameters={"message": "string", "context": "object"}
            ))
            
            kaguya_agent.add_capability(AgentCapability(
                name="task_delegation",
                description="任务委派给其他智能体",
                parameters={"task": "string", "target_agents": "array"}
            ))
            
            self.a2a_hub.register_agent(kaguya_agent)
            
            logger.info("✅ A2A多智能体系统初始化完成")
            logger.info(f"   - 已注册 {len(self.a2a_hub.list_agents())} 个智能体")
            
        except Exception as e:
            logger.error(f"❌ A2A系统初始化失败: {e}")
    
    # ==================== API接口 ====================
    
    async def start_deep_research(self, query: str, depth: str = "standard") -> str:
        """启动深度研究"""
        if not self.research_engine:
            raise RuntimeError("深度研究系统未初始化")
        
        task_id = await self.research_engine.start_research(query, depth)
        logger.info(f"深度研究任务已启动: {task_id}")
        return task_id
    
    def get_research_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取研究任务状态"""
        if not self.research_engine:
            return None
        return self.research_engine.get_task_status(task_id)
    
    def get_research_report(self, task_id: str) -> Optional[str]:
        """获取研究报告"""
        if not self.research_engine:
            return None
        return self.research_engine.get_task_report(task_id)
    
    async def call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """调用MCP工具"""
        if not self.mcp_server:
            raise RuntimeError("MCP系统未初始化")
        
        response = await self.mcp_server.handle_message({
            "type": "tools/call",
            "id": f"call_{datetime.now().timestamp()}",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        })
        
        return response.get("result", {})
    
    def list_mcp_tools(self) -> List[Dict[str, Any]]:
        """列出所有MCP工具"""
        if not self.mcp_server:
            return []
        return [tool.to_dict() for tool in self.mcp_server.tools.values()]
    
    def list_mcp_prompts(self) -> List[Dict[str, Any]]:
        """列出所有MCP提示词"""
        if not self.mcp_server:
            return []
        return [prompt.to_dict() for prompt in self.mcp_server.prompts.values()]
    
    async def delegate_task_to_agent(self, agent_id: str, task: str, 
                                     params: Dict[str, Any] = None) -> str:
        """委派任务给指定智能体"""
        if not self.a2a_hub:
            raise RuntimeError("A2A系统未初始化")
        
        kaguya = self.a2a_hub.get_agent("kaguya_main")
        if not kaguya:
            raise RuntimeError("辉夜主智能体未找到")
        
        task_id = await kaguya.request_task(agent_id, task, params)
        logger.info(f"任务已委派给 {agent_id}: {task_id}")
        return task_id
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """列出所有智能体"""
        if not self.a2a_hub:
            return []
        return [agent.to_dict() for agent in self.a2a_hub.list_agents()]
    
    def find_agents_by_capability(self, capability: str) -> List[Dict[str, Any]]:
        """根据能力查找智能体"""
        if not self.a2a_hub:
            return []
        return [agent.to_dict() for agent in self.a2a_hub.find_agents_by_capability(capability)]
    
    async def create_and_execute_workflow(self, workflow_def: Dict[str, Any]) -> str:
        """创建并执行工作流"""
        if not self.orchestrator:
            raise RuntimeError("编排器未初始化")
        
        workflow_id = await self.orchestrator.create_workflow(workflow_def)
        asyncio.create_task(self.orchestrator.execute_workflow(workflow_id))
        
        logger.info(f"工作流已创建并执行: {workflow_id}")
        return workflow_id
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            "initialized": self.initialized,
            "mcp": {
                "enabled": self.mcp_server is not None,
                "tools_count": len(self.mcp_server.tools) if self.mcp_server else 0,
                "prompts_count": len(self.mcp_server.prompts) if self.mcp_server else 0
            },
            "research": {
                "enabled": self.research_engine is not None
            },
            "a2a": {
                "enabled": self.a2a_hub is not None,
                "agents_count": len(self.a2a_hub.list_agents()) if self.a2a_hub else 0
            },
            "timestamp": datetime.now().isoformat()
        }


# 全局实例
_enhanced_features = None

def get_enhanced_features() -> KaguyaEnhancedFeatures:
    """获取全局增强功能实例"""
    global _enhanced_features
    if _enhanced_features is None:
        _enhanced_features = KaguyaEnhancedFeatures()
    return _enhanced_features


# Flask API路由（用于集成到现有系统）
def register_enhanced_routes(app):
    """注册增强功能API路由"""
    
    @app.route('/api/enhanced/status')
    def enhanced_status():
        """获取增强功能状态"""
        features = get_enhanced_features()
        return jsonify(features.get_system_status())
    
    @app.route('/api/enhanced/research/start', methods=['POST'])
    async def start_research():
        """启动深度研究"""
        from flask import request
        data = request.json
        query = data.get('query', '')
        depth = data.get('depth', 'standard')
        
        features = get_enhanced_features()
        task_id = await features.start_deep_research(query, depth)
        
        return jsonify({
            "task_id": task_id,
            "status": "started",
            "message": f"研究任务已启动: {query}"
        })
    
    @app.route('/api/enhanced/research/<task_id>/status')
    def research_status(task_id):
        """获取研究状态"""
        features = get_enhanced_features()
        status = features.get_research_status(task_id)
        
        if status is None:
            return jsonify({"error": "任务不存在"}), 404
        
        return jsonify(status)
    
    @app.route('/api/enhanced/research/<task_id>/report')
    def research_report(task_id):
        """获取研究报告"""
        features = get_enhanced_features()
        report = features.get_research_report(task_id)
        
        if report is None:
            return jsonify({"error": "报告不存在或研究未完成"}), 404
        
        return jsonify({"report": report})
    
    @app.route('/api/enhanced/mcp/tools')
    def list_mcp_tools():
        """列出MCP工具"""
        features = get_enhanced_features()
        tools = features.list_mcp_tools()
        return jsonify({"tools": tools})
    
    @app.route('/api/enhanced/mcp/tools/<tool_name>/call', methods=['POST'])
    async def call_mcp_tool(tool_name):
        """调用MCP工具"""
        from flask import request
        arguments = request.json or {}
        
        features = get_enhanced_features()
        result = await features.call_mcp_tool(tool_name, arguments)
        
        return jsonify(result)
    
    @app.route('/api/enhanced/agents')
    def list_agents():
        """列出所有智能体"""
        features = get_enhanced_features()
        agents = features.list_agents()
        return jsonify({"agents": agents})
    
    @app.route('/api/enhanced/agents/<agent_id>/delegate', methods=['POST'])
    async def delegate_to_agent(agent_id):
        """委派任务给智能体"""
        from flask import request
        data = request.json
        task = data.get('task', '')
        params = data.get('params', {})
        
        features = get_enhanced_features()
        task_id = await features.delegate_task_to_agent(agent_id, task, params)
        
        return jsonify({
            "task_id": task_id,
            "agent_id": agent_id,
            "status": "delegated"
        })
    
    @app.route('/api/enhanced/agents/find')
    def find_agents():
        """根据能力查找智能体"""
        from flask import request
        capability = request.args.get('capability', '')
        
        features = get_enhanced_features()
        agents = features.find_agents_by_capability(capability)
        
        return jsonify({"agents": agents})
    
    logger.info("增强功能API路由已注册")


def jsonify(data):
    """简化版jsonify"""
    from flask import jsonify as flask_jsonify
    return flask_jsonify(data)


if __name__ == "__main__":
    async def test_enhanced_features():
        """测试增强功能"""
        features = get_enhanced_features()
        
        # 初始化
        await features.initialize()
        
        # 获取状态
        status = features.get_system_status()
        print("\n系统状态:")
        print(json.dumps(status, indent=2, ensure_ascii=False))
        
        # 列出MCP工具
        tools = features.list_mcp_tools()
        print(f"\nMCP工具 ({len(tools)} 个):")
        for tool in tools:
            print(f"  - {tool['name']}: {tool['description']}")
        
        # 列出智能体
        agents = features.list_agents()
        print(f"\n智能体 ({len(agents)} 个):")
        for agent in agents:
            print(f"  - {agent['name']} ({agent['id']})")
            for cap in agent['capabilities']:
                print(f"      * {cap['name']}")
        
        # 测试深度研究
        print("\n启动深度研究测试...")
        task_id = await features.start_deep_research("Python异步编程最佳实践")
        print(f"研究任务ID: {task_id}")
        
        # 等待几秒
        await asyncio.sleep(3)
        
        # 检查状态
        research_status = features.get_research_status(task_id)
        if research_status:
            print(f"研究状态: {research_status['status']}")
    
    asyncio.run(test_enhanced_features())
