"""
自主Agent任务执行系统 - ReAct架构实现
支持：任务分解、工具自主调用、多步推理、错误自恢复
"""

import json
import re
import time
import uuid
from typing import Dict, List, Optional, Callable, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import threading


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class ActionType(Enum):
    THINK = "think"
    SEARCH = "search"
    CODE = "code"
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    API_CALL = "api_call"
    CALCULATE = "calculate"
    ASK_USER = "ask_user"
    FINISH = "finish"


@dataclass
class Thought:
    """思考过程记录"""
    step: int
    content: str
    timestamp: float
    reasoning_type: str = "general"  # general, planning, reflection, error_analysis


@dataclass
class Action:
    """行动记录"""
    step: int
    action_type: ActionType
    params: Dict[str, Any]
    timestamp: float
    status: str = "pending"  # pending, executing, completed, failed
    result: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0


@dataclass
class Observation:
    """观察结果"""
    step: int
    content: str
    timestamp: float
    observation_type: str = "result"  # result, error, intermediate


@dataclass
class SubTask:
    """子任务"""
    id: str
    description: str
    status: TaskStatus
    dependencies: List[str] = field(default_factory=list)
    result: Any = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class TaskExecution:
    """任务执行记录"""
    task_id: str
    goal: str
    status: TaskStatus
    thoughts: List[Thought] = field(default_factory=list)
    actions: List[Action] = field(default_factory=list)
    observations: List[Observation] = field(default_factory=list)
    subtasks: List[SubTask] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    final_result: Any = None
    context: Dict[str, Any] = field(default_factory=dict)


class ToolRegistry:
    """工具注册中心"""
    
    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self.tool_descriptions: Dict[str, Dict] = {}
    
    def register(self, name: str, func: Callable, description: str, 
                 parameters: Dict[str, Any], required: List[str] = None):
        """注册工具"""
        self.tools[name] = func
        self.tool_descriptions[name] = {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": parameters,
                "required": required or []
            }
        }
    
    def get_tool(self, name: str) -> Optional[Callable]:
        return self.tools.get(name)
    
    def get_all_tools_description(self) -> str:
        """获取所有工具描述"""
        descriptions = []
        for name, desc in self.tool_descriptions.items():
            descriptions.append(f"- {name}: {desc['description']}")
        return "\n".join(descriptions)


class ReActAgent:
    """
    ReAct (Reasoning + Acting) Agent
    实现思考-行动-观察的循环架构
    """
    
    def __init__(self, llm_client, tool_registry: ToolRegistry, 
                 max_iterations: int = 20, max_retries: int = 3):
        self.llm_client = llm_client
        self.tools = tool_registry
        self.max_iterations = max_iterations
        self.max_retries = max_retries
        self.execution_history: List[TaskExecution] = []
        self.current_execution: Optional[TaskExecution] = None
        self._lock = threading.Lock()
        
        # 系统提示词模板
        self.system_prompt_template = """你是一个智能Agent助手，使用ReAct (Reasoning + Acting) 架构解决问题。

## 可用工具
{tools_description}

## 执行规则
1. 每次回复必须包含 Thought（思考）和 Action（行动）
2. Thought 格式: "Thought: [你的思考过程]"
3. Action 格式: "Action: [工具名]\nParameters: {JSON参数}"
4. 当任务完成时，使用 Action: finish
5. 如果工具执行失败，分析原因并尝试替代方案
6. 复杂任务先分解为子任务

## 输出格式示例
Thought: 用户需要查询天气，我应该使用搜索工具获取信息。
Action: search
Parameters: {"query": "北京今天天气"}

或者

Thought: 计算完成，可以返回最终结果。
Action: finish
Parameters: {"result": "42", "summary": "计算结果为42"}
"""
    
    def execute(self, goal: str, context: Dict[str, Any] = None) -> TaskExecution:
        """
        执行目标任务
        
        Args:
            goal: 任务目标描述
            context: 额外上下文信息
            
        Returns:
            TaskExecution: 完整执行记录
        """
        task_id = str(uuid.uuid4())[:8]
        execution = TaskExecution(
            task_id=task_id,
            goal=goal,
            status=TaskStatus.RUNNING,
            context=context or {}
        )
        
        with self._lock:
            self.current_execution = execution
            self.execution_history.append(execution)
        
        try:
            # 步骤1: 任务分解
            self._decompose_task(execution)
            
            # 步骤2: 执行ReAct循环
            for iteration in range(self.max_iterations):
                # 思考
                thought = self._think(execution, iteration)
                execution.thoughts.append(thought)
                
                # 决定行动
                action = self._decide_action(execution, thought)
                if not action:
                    continue
                    
                execution.actions.append(action)
                
                # 执行行动
                if action.action_type == ActionType.FINISH:
                    execution.final_result = action.params.get("result")
                    execution.status = TaskStatus.COMPLETED
                    break
                
                observation = self._execute_action(execution, action)
                execution.observations.append(observation)
                
                # 检查是否需要重试
                if observation.observation_type == "error":
                    action.status = "failed"
                    action.error = observation.content
                    
                    # 错误恢复策略
                    if self._should_retry(execution, action):
                        recovery_action = self._generate_recovery_action(execution, action)
                        if recovery_action:
                            execution.actions.append(recovery_action)
                            observation = self._execute_action(execution, recovery_action)
                            execution.observations.append(observation)
                else:
                    action.status = "completed"
                    action.result = observation.content
            
            else:
                # 达到最大迭代次数
                execution.status = TaskStatus.FAILED
                execution.final_result = "达到最大迭代次数限制"
                
        except Exception as e:
            execution.status = TaskStatus.FAILED
            execution.final_result = f"执行异常: {str(e)}"
        finally:
            execution.end_time = time.time()
            
        return execution
    
    def _decompose_task(self, execution: TaskExecution):
        """任务分解"""
        prompt = f"""请将以下任务分解为具体的子任务列表：

任务: {execution.goal}

请以JSON格式返回子任务列表：
{{
    "subtasks": [
        {{"id": "1", "description": "子任务描述", "dependencies": []}},
        {{"id": "2", "description": "子任务描述", "dependencies": ["1"]}}
    ]
}}
"""
        
        try:
            response = self.llm_client.generate(prompt)
            # 提取JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                for st_data in data.get("subtasks", []):
                    subtask = SubTask(
                        id=st_data["id"],
                        description=st_data["description"],
                        status=TaskStatus.PENDING,
                        dependencies=st_data.get("dependencies", [])
                    )
                    execution.subtasks.append(subtask)
        except Exception as e:
            # 如果分解失败，创建一个单一子任务
            execution.subtasks.append(SubTask(
                id="1",
                description=execution.goal,
                status=TaskStatus.PENDING
            ))
    
    def _think(self, execution: TaskExecution, step: int) -> Thought:
        """思考过程"""
        # 构建上下文
        context = self._build_context(execution)
        
        prompt = f"""基于以下执行历史，决定下一步行动：

目标: {execution.goal}

执行历史:
{context}

请提供你的思考（Thought）和下一步行动（Action）。
"""
        
        response = self.llm_client.generate(prompt)
        
        return Thought(
            step=step,
            content=response,
            timestamp=time.time()
        )
    
    def _decide_action(self, execution: TaskExecution, thought: Thought) -> Optional[Action]:
        """根据思考决定行动"""
        content = thought.content
        
        # 解析 Thought 和 Action
        thought_match = re.search(r'Thought:\s*(.+?)(?=Action:|$)', content, re.DOTALL | re.IGNORECASE)
        action_match = re.search(r'Action:\s*(\w+)', content, re.IGNORECASE)
        params_match = re.search(r'Parameters:\s*(\{.*\})', content, re.DOTALL)
        
        if not action_match:
            return None
        
        action_name = action_match.group(1).lower()
        
        # 映射到 ActionType
        action_type_map = {
            "think": ActionType.THINK,
            "search": ActionType.SEARCH,
            "code": ActionType.CODE,
            "file_read": ActionType.FILE_READ,
            "file_write": ActionType.FILE_WRITE,
            "api_call": ActionType.API_CALL,
            "calculate": ActionType.CALCULATE,
            "ask_user": ActionType.ASK_USER,
            "finish": ActionType.FINISH
        }
        
        action_type = action_type_map.get(action_name, ActionType.THINK)
        
        # 解析参数
        params = {}
        if params_match:
            try:
                params = json.loads(params_match.group(1))
            except:
                pass
        
        return Action(
            step=thought.step,
            action_type=action_type,
            params=params,
            timestamp=time.time()
        )
    
    def _execute_action(self, execution: TaskExecution, action: Action) -> Observation:
        """执行行动"""
        start_time = time.time()
        action.status = "executing"
        
        try:
            if action.action_type == ActionType.FINISH:
                return Observation(
                    step=action.step,
                    content="任务完成",
                    timestamp=time.time(),
                    observation_type="result"
                )
            
            # 查找并执行工具
            tool_name = action.action_type.value
            tool_func = self.tools.get_tool(tool_name)
            
            if tool_func:
                result = tool_func(**action.params)
                action.execution_time = time.time() - start_time
                
                return Observation(
                    step=action.step,
                    content=str(result),
                    timestamp=time.time(),
                    observation_type="result"
                )
            else:
                return Observation(
                    step=action.step,
                    content=f"工具 {tool_name} 未找到",
                    timestamp=time.time(),
                    observation_type="error"
                )
                
        except Exception as e:
            action.execution_time = time.time() - start_time
            return Observation(
                step=action.step,
                content=f"执行错误: {str(e)}",
                timestamp=time.time(),
                observation_type="error"
            )
    
    def _should_retry(self, execution: TaskExecution, action: Action) -> bool:
        """判断是否应该重试"""
        return action.retry_count < self.max_retries
    
    def _generate_recovery_action(self, execution: TaskExecution, failed_action: Action) -> Optional[Action]:
        """生成恢复行动"""
        failed_action.retry_count += 1
        
        # 根据错误类型生成恢复策略
        prompt = f"""之前的行动失败了：
行动: {failed_action.action_type.value}
参数: {json.dumps(failed_action.params)}
错误: {failed_action.error}

请提供一个替代的行动方案。
"""
        
        response = self.llm_client.generate(prompt)
        
        # 解析新的行动
        action_match = re.search(r'Action:\s*(\w+)', response, re.IGNORECASE)
        params_match = re.search(r'Parameters:\s*(\{.*\})', response, re.DOTALL)
        
        if action_match:
            action_name = action_match.group(1).lower()
            params = {}
            if params_match:
                try:
                    params = json.loads(params_match.group(1))
                except:
                    pass
            
            action_type_map = {
                "think": ActionType.THINK,
                "search": ActionType.SEARCH,
                "code": ActionType.CODE,
                "finish": ActionType.FINISH
            }
            
            return Action(
                step=failed_action.step,
                action_type=action_type_map.get(action_name, ActionType.THINK),
                params=params,
                timestamp=time.time(),
                status="retry"
            )
        
        return None
    
    def _build_context(self, execution: TaskExecution) -> str:
        """构建执行上下文"""
        context_parts = []
        
        # 添加最近的思考和观察
        for i in range(max(0, len(execution.thoughts) - 5), len(execution.thoughts)):
            if i < len(execution.thoughts):
                thought = execution.thoughts[i]
                context_parts.append(f"Step {thought.step}: {thought.content[:200]}...")
            
            if i < len(execution.actions):
                action = execution.actions[i]
                context_parts.append(f"  Action: {action.action_type.value} - Status: {action.status}")
            
            if i < len(execution.observations):
                obs = execution.observations[i]
                context_parts.append(f"  Observation: {obs.content[:150]}...")
        
        return "\n".join(context_parts)
    
    def get_execution_summary(self, task_id: str) -> Dict[str, Any]:
        """获取执行摘要"""
        for execution in self.execution_history:
            if execution.task_id == task_id:
                return {
                    "task_id": execution.task_id,
                    "goal": execution.goal,
                    "status": execution.status.value,
                    "duration": (execution.end_time or time.time()) - execution.start_time,
                    "thoughts_count": len(execution.thoughts),
                    "actions_count": len(execution.actions),
                    "success_rate": sum(1 for a in execution.actions if a.status == "completed") / max(len(execution.actions), 1),
                    "final_result": execution.final_result
                }
        return {}


class PlanAndExecuteAgent:
    """
    Plan-and-Execute Agent
    先规划后执行，适合复杂多步骤任务
    """
    
    def __init__(self, llm_client, tool_registry: ToolRegistry):
        self.llm_client = llm_client
        self.tools = tool_registry
        self.react_agent = ReActAgent(llm_client, tool_registry)
    
    def execute(self, goal: str) -> TaskExecution:
        """执行计划并执行"""
        # 步骤1: 创建计划
        plan = self._create_plan(goal)
        
        # 步骤2: 逐步执行计划
        execution = TaskExecution(
            task_id=str(uuid.uuid4())[:8],
            goal=goal,
            status=TaskStatus.RUNNING
        )
        
        for step in plan:
            sub_execution = self.react_agent.execute(step["task"])
            
            # 合并子任务执行结果
            execution.thoughts.extend(sub_execution.thoughts)
            execution.actions.extend(sub_execution.actions)
            execution.observations.extend(sub_execution.observations)
            
            if sub_execution.status == TaskStatus.FAILED:
                execution.status = TaskStatus.FAILED
                execution.final_result = f"步骤失败: {step['task']}"
                break
        else:
            execution.status = TaskStatus.COMPLETED
            execution.final_result = "所有步骤执行完成"
        
        execution.end_time = time.time()
        return execution
    
    def _create_plan(self, goal: str) -> List[Dict]:
        """创建执行计划"""
        prompt = f"""请为以下目标创建详细的执行计划：

目标: {goal}

请以JSON格式返回计划步骤：
{{
    "plan": [
        {{"step": 1, "task": "具体任务描述", "expected_outcome": "预期结果"}},
        {{"step": 2, "task": "具体任务描述", "expected_outcome": "预期结果"}}
    ]
}}
"""
        
        try:
            response = self.llm_client.generate(prompt)
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return data.get("plan", [])
        except:
            pass
        
        # 默认返回单一任务
        return [{"step": 1, "task": goal, "expected_outcome": "完成任务"}]


class ReflectionAgent:
    """
    反思型Agent
    执行后自我反思，改进策略
    """
    
    def __init__(self, llm_client, tool_registry: ToolRegistry):
        self.llm_client = llm_client
        self.tools = tool_registry
        self.react_agent = ReActAgent(llm_client, tool_registry)
        self.reflection_history: List[Dict] = []
    
    def execute_with_reflection(self, goal: str, max_reflections: int = 2) -> TaskExecution:
        """带反思的执行"""
        best_execution = None
        best_score = float('-inf')
        
        for reflection_round in range(max_reflections + 1):
            # 执行
            execution = self.react_agent.execute(goal)
            
            # 评估
            score = self._evaluate_execution(execution)
            
            if score > best_score:
                best_score = score
                best_execution = execution
            
            # 如果不是最后一轮，进行反思
            if reflection_round < max_reflections and execution.status != TaskStatus.COMPLETED:
                reflection = self._reflect(execution)
                self.reflection_history.append({
                    "round": reflection_round,
                    "execution": execution,
                    "reflection": reflection,
                    "score": score
                })
                
                # 根据反思改进策略
                goal = self._improve_goal(goal, reflection)
        
        return best_execution
    
    def _evaluate_execution(self, execution: TaskExecution) -> float:
        """评估执行质量"""
        score = 0.0
        
        # 完成状态
        if execution.status == TaskStatus.COMPLETED:
            score += 50
        
        # 成功率
        success_rate = sum(1 for a in execution.actions if a.status == "completed") / max(len(execution.actions), 1)
        score += success_rate * 30
        
        # 效率（步骤数适中）
        optimal_steps = 5  # 假设最优步骤数
        step_penalty = abs(len(execution.actions) - optimal_steps) * 2
        score -= step_penalty
        
        return score
    
    def _reflect(self, execution: TaskExecution) -> str:
        """反思执行过程"""
        prompt = f"""请反思以下任务执行过程：

目标: {execution.goal}
状态: {execution.status.value}
行动数: {len(execution.actions)}
成功行动: {sum(1 for a in execution.actions if a.status == "completed")}
失败行动: {sum(1 for a in execution.actions if a.status == "failed")}

失败详情:
"""
        for action in execution.actions:
            if action.status == "failed":
                prompt += f"- {action.action_type.value}: {action.error}\n"
        
        prompt += "\n请分析失败原因并提出改进建议："
        
        return self.llm_client.generate(prompt)
    
    def _improve_goal(self, original_goal: str, reflection: str) -> str:
        """根据反思改进目标"""
        prompt = f"""基于以下反思，重新表述任务目标以更好地完成：

原目标: {original_goal}

反思: {reflection}

请提供一个更清晰、更具体的任务描述：
"""
        
        return self.llm_client.generate(prompt)


# ==================== 工具函数 ====================

def create_default_tool_registry() -> ToolRegistry:
    """创建默认工具注册表"""
    registry = ToolRegistry()
    
    # 搜索工具
    registry.register(
        name="search",
        func=lambda query: f"搜索结果: {query}",
        description="搜索网络信息",
        parameters={"query": {"type": "string", "description": "搜索关键词"}},
        required=["query"]
    )
    
    # 代码执行工具
    registry.register(
        name="code",
        func=lambda code, language="python": f"执行 {language} 代码: {code[:50]}...",
        description="执行代码",
        parameters={
            "code": {"type": "string", "description": "代码内容"},
            "language": {"type": "string", "description": "编程语言"}
        },
        required=["code"]
    )
    
    # 计算工具
    registry.register(
        name="calculate",
        func=lambda expression: eval(expression),
        description="计算数学表达式",
        parameters={"expression": {"type": "string", "description": "数学表达式"}},
        required=["expression"]
    )
    
    # 文件读取工具
    registry.register(
        name="file_read",
        func=lambda path: f"读取文件: {path}",
        description="读取文件内容",
        parameters={"path": {"type": "string", "description": "文件路径"}},
        required=["path"]
    )
    
    # 文件写入工具
    registry.register(
        name="file_write",
        func=lambda path, content: f"写入文件: {path}",
        description="写入文件内容",
        parameters={
            "path": {"type": "string", "description": "文件路径"},
            "content": {"type": "string", "description": "文件内容"}
        },
        required=["path", "content"]
    )
    
    return registry


# 全局Agent实例
_default_agent: Optional[ReActAgent] = None

def get_autonomous_agent(llm_client=None, tool_registry=None) -> ReActAgent:
    """获取全局Agent实例"""
    global _default_agent
    if _default_agent is None:
        if llm_client is None:
            # 创建一个简单的LLM客户端模拟
            class SimpleLLM:
                def generate(self, prompt: str) -> str:
                    return f"Thought: 思考中...\nAction: think\nParameters: {{}}"
            
            llm_client = SimpleLLM()
        
        if tool_registry is None:
            tool_registry = create_default_tool_registry()
        
        _default_agent = ReActAgent(llm_client, tool_registry)
    
    return _default_agent


if __name__ == "__main__":
    # 测试代码
    print("自主Agent系统测试")
    
    class MockLLM:
        def generate(self, prompt: str) -> str:
            if "分解" in prompt:
                return '{"subtasks": [{"id": "1", "description": "搜索信息", "dependencies": []}]}'
            elif "计划" in prompt:
                return '{"plan": [{"step": 1, "task": "搜索相关信息", "expected_outcome": "获得搜索结果"}]}'
            else:
                return "Thought: 需要搜索信息\nAction: search\nParameters: {\"query\": \"测试\"}"
    
    llm = MockLLM()
    tools = create_default_tool_registry()
    agent = ReActAgent(llm, tools)
    
    result = agent.execute("测试任务")
    print(f"任务ID: {result.task_id}")
    print(f"状态: {result.status.value}")
    print(f"思考次数: {len(result.thoughts)}")
    print(f"行动次数: {len(result.actions)}")
