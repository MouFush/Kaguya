#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辉夜AI - Agent编排系统集成示例
展示如何将多Agent协作、自主规划、工作流编排集成到主应用
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

# 导入Agent编排系统
from agent_orchestration_system import (
    AgentOrchestrator, SimpleAgent, AutonomousAgent,
    GroupChat, Workflow, WorkflowNode, WorkflowNodeType,
    Message, MessageType, AgentRole, Task, Plan
)

# 导入LLM适配器
from llm_adapter import LLMFactory, LLMConfig

# 导入记忆系统
from memory_integration import ConversationMemory


class KaguyaAIAssistant:
    """
    辉夜AI助手 - 完整的企业级Agent系统
    整合: 多Agent协作 + 自主规划 + 工作流编排 + LLM适配 + 记忆系统
    """
    
    def __init__(self):
        # 核心编排器
        self.orchestrator = AgentOrchestrator()
        
        # LLM适配器
        self.llm_adapters = {}
        
        # 记忆系统
        self.memories = {}
        
        # 初始化
        self._init_agents()
        
    def _init_agents(self):
        """初始化专业Agent团队"""
        
        # 1. 协调者Agent
        coordinator = SimpleAgent(
            name="辉夜协调者",
            role=AgentRole.COORDINATOR,
            system_message="你是辉夜AI的协调者，负责分配任务和协调各Agent工作"
        )
        self.orchestrator.register_agent(coordinator)
        
        # 2. 规划Agent
        planner = AutonomousAgent(
            name="辉夜规划师",
            system_message="你是辉夜AI的规划专家，负责目标分解和计划制定"
        )
        self.orchestrator.register_agent(planner)
        
        # 3. 代码专家Agent
        code_expert = SimpleAgent(
            name="代码专家",
            role=AgentRole.SPECIALIST,
            system_message="你是编程专家，擅长代码生成、审查和优化"
        )
        self.orchestrator.register_agent(code_expert)
        
        # 4. 数据分析Agent
        data_analyst = SimpleAgent(
            name="数据分析师",
            role=AgentRole.SPECIALIST,
            system_message="你是数据分析专家，擅长数据处理和可视化"
        )
        self.orchestrator.register_agent(data_analyst)
        
        # 5. 内容创作Agent
        content_creator = SimpleAgent(
            name="内容创作者",
            role=AgentRole.SPECIALIST,
            system_message="你是内容创作专家，擅长写作、翻译和创意生成"
        )
        self.orchestrator.register_agent(content_creator)
        
        # 6. 评估Agent
        critic = SimpleAgent(
            name="质量评估员",
            role=AgentRole.CRITIC,
            system_message="你是质量评估专家，负责审查和提出改进建议"
        )
        self.orchestrator.register_agent(critic)
        
        print("✅ Agent团队初始化完成")
        print(f"   - 已注册 {len(self.orchestrator.agents)} 个专业Agent")
    
    def setup_llm_adapter(self, provider: str, api_key: str, **kwargs):
        """配置LLM适配器"""
        config = LLMConfig(
            api_key=api_key,
            model=kwargs.get("model"),
            base_url=kwargs.get("base_url"),
            enable_memory=kwargs.get("enable_memory", True)
        )
        
        adapter = LLMFactory.create_adapter(provider, config)
        self.llm_adapters[provider] = adapter
        
        print(f"✅ LLM适配器配置完成: {provider}")
        return adapter
    
    async def create_team_chat(self, task: str) -> str:
        """
        创建团队协作群聊
        根据任务类型自动选择合适的Agent
        """
        # 分析任务类型
        task_lower = task.lower()
        
        if any(kw in task_lower for kw in ["代码", "编程", "开发", "bug"]):
            selected_agents = ["辉夜协调者", "辉夜规划师", "代码专家", "质量评估员"]
        elif any(kw in task_lower for kw in ["数据", "分析", "图表", "统计"]):
            selected_agents = ["辉夜协调者", "数据分析师", "辉夜规划师"]
        elif any(kw in task_lower for kw in ["写作", "文章", "翻译", "内容"]):
            selected_agents = ["辉夜协调者", "内容创作者", "质量评估员"]
        else:
            selected_agents = ["辉夜协调者", "辉夜规划师", "质量评估员"]
        
        # 创建群聊
        chat = self.orchestrator.create_group_chat(
            name=f"任务协作_{datetime.now().strftime('%H%M%S')}",
            agent_names=selected_agents,
            max_round=10,
            speaker_selection_mode="auto"
        )
        
        # 启动群聊
        await chat.start(task)
        
        return chat.name
    
    async def create_autonomous_plan(self, goal: str) -> Plan:
        """
        创建自主执行计划
        """
        planner = self.orchestrator.agents.get("辉夜规划师")
        if not planner:
            raise ValueError("规划Agent未找到")
        
        message = Message(
            sender="user",
            content=goal,
            message_type=MessageType.PLAN
        )
        
        await planner.receive_message(message)
        response = await planner.think(message)
        
        print(f"\n📝 计划创建完成:")
        print(response)
        
        return planner.current_plan
    
    def create_workflow(self, name: str, workflow_type: str = "default") -> Workflow:
        """
        创建预定义工作流模板
        """
        workflow = self.orchestrator.create_workflow(name=name)
        
        if workflow_type == "content_creation":
            # 内容创作工作流
            self._build_content_workflow(workflow)
        elif workflow_type == "code_review":
            # 代码审查工作流
            self._build_code_review_workflow(workflow)
        elif workflow_type == "data_analysis":
            # 数据分析工作流
            self._build_data_analysis_workflow(workflow)
        else:
            # 默认通用工作流
            self._build_default_workflow(workflow)
        
        return workflow
    
    def _build_content_workflow(self, workflow: Workflow):
        """构建内容创作工作流"""
        start = WorkflowNode(name="开始", node_type=WorkflowNodeType.START)
        research = WorkflowNode(
            name="资料收集",
            node_type=WorkflowNodeType.AGENT,
            config={"agent_name": "辉夜规划师", "message": "收集相关资料"}
        )
        draft = WorkflowNode(
            name="撰写草稿",
            node_type=WorkflowNodeType.AGENT,
            config={"agent_name": "内容创作者", "message": "创作内容"}
        )
        review = WorkflowNode(
            name="质量审查",
            node_type=WorkflowNodeType.AGENT,
            config={"agent_name": "质量评估员", "message": "审查内容质量"}
        )
        condition = WorkflowNode(
            name="是否通过",
            node_type=WorkflowNodeType.CONDITION,
            config={"condition": "context.get('passed', True)"}
        )
        revise = WorkflowNode(
            name="修改完善",
            node_type=WorkflowNodeType.AGENT,
            config={"agent_name": "内容创作者", "message": "根据反馈修改"}
        )
        end = WorkflowNode(name="完成", node_type=WorkflowNodeType.END)
        
        # 连接节点
        for node in [start, research, draft, review, condition, revise, end]:
            workflow.add_node(node)
        
        workflow.connect_nodes(start.id, research.id)
        workflow.connect_nodes(research.id, draft.id)
        workflow.connect_nodes(draft.id, review.id)
        workflow.connect_nodes(review.id, condition.id)
        workflow.connect_nodes(condition.id, end.id)  # True分支
        workflow.connect_nodes(condition.id, revise.id)  # False分支
        workflow.connect_nodes(revise.id, review.id)  # 循环
    
    def _build_code_review_workflow(self, workflow: Workflow):
        """构建代码审查工作流"""
        start = WorkflowNode(name="开始", node_type=WorkflowNodeType.START)
        analyze = WorkflowNode(
            name="代码分析",
            node_type=WorkflowNodeType.AGENT,
            config={"agent_name": "代码专家", "message": "分析代码"}
        )
        review = WorkflowNode(
            name="代码审查",
            node_type=WorkflowNodeType.AGENT,
            config={"agent_name": "质量评估员", "message": "审查代码质量"}
        )
        test = WorkflowNode(
            name="测试验证",
            node_type=WorkflowNodeType.TOOL,
            config={"tool_name": "run_tests"}
        )
        end = WorkflowNode(name="完成", node_type=WorkflowNodeType.END)
        
        for node in [start, analyze, review, test, end]:
            workflow.add_node(node)
        
        workflow.connect_nodes(start.id, analyze.id)
        workflow.connect_nodes(analyze.id, review.id)
        workflow.connect_nodes(review.id, test.id)
        workflow.connect_nodes(test.id, end.id)
    
    def _build_data_analysis_workflow(self, workflow: Workflow):
        """构建数据分析工作流"""
        start = WorkflowNode(name="开始", node_type=WorkflowNodeType.START)
        clean = WorkflowNode(
            name="数据清洗",
            node_type=WorkflowNodeType.AGENT,
            config={"agent_name": "数据分析师", "message": "清洗数据"}
        )
        analyze = WorkflowNode(
            name="数据分析",
            node_type=WorkflowNodeType.AGENT,
            config={"agent_name": "数据分析师", "message": "分析数据"}
        )
        visualize = WorkflowNode(
            name="生成图表",
            node_type=WorkflowNodeType.TOOL,
            config={"tool_name": "create_chart"}
        )
        report = WorkflowNode(
            name="生成报告",
            node_type=WorkflowNodeType.AGENT,
            config={"agent_name": "内容创作者", "message": "撰写分析报告"}
        )
        end = WorkflowNode(name="完成", node_type=WorkflowNodeType.END)
        
        for node in [start, clean, analyze, visualize, report, end]:
            workflow.add_node(node)
        
        workflow.connect_nodes(start.id, clean.id)
        workflow.connect_nodes(clean.id, analyze.id)
        workflow.connect_nodes(analyze.id, visualize.id)
        workflow.connect_nodes(visualize.id, report.id)
        workflow.connect_nodes(report.id, end.id)
    
    def _build_default_workflow(self, workflow: Workflow):
        """构建默认工作流"""
        start = WorkflowNode(name="开始", node_type=WorkflowNodeType.START)
        plan = WorkflowNode(
            name="制定计划",
            node_type=WorkflowNodeType.AGENT,
            config={"agent_name": "辉夜规划师", "message": "制定执行计划"}
        )
        execute = WorkflowNode(
            name="执行任务",
            node_type=WorkflowNodeType.AGENT,
            config={"agent_name": "辉夜协调者", "message": "协调执行任务"}
        )
        review = WorkflowNode(
            name="结果审查",
            node_type=WorkflowNodeType.AGENT,
            config={"agent_name": "质量评估员", "message": "审查结果"}
        )
        end = WorkflowNode(name="完成", node_type=WorkflowNodeType.END)
        
        for node in [start, plan, execute, review, end]:
            workflow.add_node(node)
        
        workflow.connect_nodes(start.id, plan.id)
        workflow.connect_nodes(plan.id, execute.id)
        workflow.connect_nodes(execute.id, review.id)
        workflow.connect_nodes(review.id, end.id)
    
    async def execute_workflow(self, workflow_name: str, context: Dict[str, Any]) -> str:
        """执行工作流"""
        workflow = self.orchestrator.workflows.get(workflow_name)
        if not workflow:
            raise ValueError(f"工作流未找到: {workflow_name}")
        
        execution_id = await self.orchestrator.workflow_engine.execute(
            workflow.id,
            initial_context=context
        )
        
        return execution_id
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            "agents": len(self.orchestrator.agents),
            "workflows": len(self.orchestrator.workflows),
            "llm_adapters": list(self.llm_adapters.keys()),
            "status": "running" if self.orchestrator.is_running else "stopped"
        }


async def demo_full_system():
    """演示完整系统功能"""
    print("\n" + "="*70)
    print("🌟 辉夜AI - 企业级Agent编排系统演示")
    print("="*70)
    
    # 初始化系统
    assistant = KaguyaAIAssistant()
    
    print("\n" + "-"*70)
    print("📊 系统状态")
    print("-"*70)
    status = assistant.get_system_status()
    print(f"Agent数量: {status['agents']}")
    print(f"工作流数量: {status['workflows']}")
    print(f"LLM适配器: {status['llm_adapters']}")
    
    # 演示1: 多Agent协作
    print("\n" + "-"*70)
    print("🤝 演示1: 多Agent协作 - 软件开发任务")
    print("-"*70)
    await assistant.create_team_chat("开发一个用户认证系统，包含登录、注册、密码重置功能")
    
    # 演示2: 自主规划
    print("\n" + "-"*70)
    print("🎯 演示2: 自主规划 - 电商平台开发")
    print("-"*70)
    plan = await assistant.create_autonomous_plan(
        "开发一个完整的电商平台，包含用户系统、商品管理、购物车、订单处理、支付集成、物流跟踪"
    )
    
    # 演示3: 工作流编排
    print("\n" + "-"*70)
    print("🔄 演示3: 工作流编排 - 内容创作")
    print("-"*70)
    workflow = assistant.create_workflow(
        name="技术博客创作",
        workflow_type="content_creation"
    )
    print(f"工作流 '{workflow.name}' 已创建")
    print(f"节点: {[n.name for n in workflow.nodes.values()]}")
    
    # 执行工作流
    execution_id = await assistant.execute_workflow(
        "技术博客创作",
        context={"topic": "AI Agent技术", "passed": True}
    )
    print(f"执行ID: {execution_id}")
    
    # 演示4: 代码审查工作流
    print("\n" + "-"*70)
    print("🔍 演示4: 代码审查工作流")
    print("-"*70)
    code_workflow = assistant.create_workflow(
        name="代码审查流程",
        workflow_type="code_review"
    )
    print(f"工作流 '{code_workflow.name}' 已创建")
    
    code_execution_id = await assistant.execute_workflow(
        "代码审查流程",
        context={"code_file": "main.py"}
    )
    print(f"执行ID: {code_execution_id}")
    
    # 演示5: 数据分析工作流
    print("\n" + "-"*70)
    print("📈 演示5: 数据分析工作流")
    print("-"*70)
    data_workflow = assistant.create_workflow(
        name="销售数据分析",
        workflow_type="data_analysis"
    )
    print(f"工作流 '{data_workflow.name}' 已创建")
    
    data_execution_id = await assistant.execute_workflow(
        "销售数据分析",
        context={"data_source": "sales_2024.csv"}
    )
    print(f"执行ID: {data_execution_id}")
    
    # 最终状态
    print("\n" + "="*70)
    print("✅ 所有演示完成!")
    print("="*70)
    final_status = assistant.get_system_status()
    print(f"\n最终系统状态:")
    print(f"  - Agent团队: {final_status['agents']} 个")
    print(f"  - 工作流模板: {final_status['workflows']} 个")
    print(f"  - 执行记录: {len(assistant.orchestrator.workflow_engine.executions)} 条")


if __name__ == "__main__":
    asyncio.run(demo_full_system())
