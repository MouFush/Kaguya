#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基础Agent任务规划框架
实现任务分解、执行和反思
"""

import json
import re
import time
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"

@dataclass
class Task:
    """任务定义"""
    id: str
    description: str
    status: TaskStatus
    subtasks: List['Task']
    result: Optional[str]
    error: Optional[str]
    created_at: float
    completed_at: Optional[float]
    retry_count: int
    max_retries: int
    dependencies: List[str]  # 依赖的其他任务ID
    metadata: Dict
    
    def to_dict(self):
        return {
            'id': self.id,
            'description': self.description,
            'status': self.status.value,
            'subtasks': [t.to_dict() for t in self.subtasks],
            'result': self.result,
            'error': self.error,
            'created_at': self.created_at,
            'completed_at': self.completed_at,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'dependencies': self.dependencies,
            'metadata': self.metadata
        }

class ToolRegistry:
    """工具注册表"""
    
    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self.tool_descriptions: Dict[str, str] = {}
    
    def register(self, name: str, func: Callable, description: str = ""):
        """注册工具"""
        self.tools[name] = func
        self.tool_descriptions[name] = description
        print(f"✓ 工具已注册: {name}")
    
    def get(self, name: str) -> Optional[Callable]:
        """获取工具"""
        return self.tools.get(name)
    
    def list_tools(self) -> List[Dict]:
        """列出所有工具"""
        return [
            {'name': name, 'description': desc}
            for name, desc in self.tool_descriptions.items()
        ]
    
    def execute(self, name: str, **kwargs) -> str:
        """执行工具"""
        tool = self.get(name)
        if not tool:
            return f"错误: 工具 '{name}' 不存在"
        
        try:
            result = tool(**kwargs)
            return str(result)
        except Exception as e:
            return f"错误: 工具执行失败 - {str(e)}"

class TaskPlanner:
    """任务规划器"""
    
    def __init__(self, llm_func: Callable):
        self.llm = llm_func
        self.tool_registry = ToolRegistry()
        self._register_default_tools()
    
    def _register_default_tools(self):
        """注册默认工具"""
        # 网络搜索工具
        self.tool_registry.register(
            "web_search",
            self._web_search,
            "搜索网络获取信息"
        )
        
        # 计算器工具
        self.tool_registry.register(
            "calculator",
            self._calculator,
            "执行数学计算"
        )
        
        # 文件读取工具
        self.tool_registry.register(
            "read_file",
            self._read_file,
            "读取本地文件内容"
        )
        
        # 代码执行工具
        self.tool_registry.register(
            "execute_code",
            self._execute_code,
            "执行Python代码"
        )
    
    def _web_search(self, query: str) -> str:
        """网络搜索（简化版）"""
        # 这里应该调用实际的搜索API
        return f"[模拟搜索结果] 关于 '{query}' 的搜索结果..."
    
    def _calculator(self, expression: str) -> str:
        """计算器"""
        try:
            # 安全计算
            allowed_names = {
                "abs": abs, "max": max, "min": min,
                "sum": sum, "len": len,
            }
            result = eval(expression, {"__builtins__": {}}, allowed_names)
            return str(result)
        except Exception as e:
            return f"计算错误: {str(e)}"
    
    def _read_file(self, path: str) -> str:
        """读取文件"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"读取错误: {str(e)}"
    
    def _execute_code(self, code: str) -> str:
        """执行代码"""
        try:
            # 安全执行（简化版）
            import io
            import sys
            
            stdout = io.StringIO()
            sys.stdout = stdout
            
            exec(code, {"__builtins__": {}})
            
            sys.stdout = sys.__stdout__
            return stdout.getvalue() or "代码执行完成"
        except Exception as e:
            return f"执行错误: {str(e)}"
    
    def plan(self, goal: str, context: str = "") -> Task:
        """规划任务"""
        # 使用LLM分解任务
        planning_prompt = f"""
你是一个任务规划助手。请将以下目标分解为具体的子任务。

目标: {goal}
上下文: {context}

可用工具:
{json.dumps(self.tool_registry.list_tools(), ensure_ascii=False, indent=2)}

请将目标分解为2-5个子任务，每个子任务应该是具体的、可执行的。
以JSON格式返回:
{{
    "subtasks": [
        {{
            "id": "task_1",
            "description": "子任务描述",
            "tool": "工具名（可选）",
            "dependencies": []
        }}
    ]
}}
"""
        
        try:
            response = self.llm(planning_prompt)
            
            # 提取JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                plan_data = json.loads(json_match.group())
                
                # 创建任务树
                root_task = Task(
                    id=f"root_{int(time.time())}",
                    description=goal,
                    status=TaskStatus.PENDING,
                    subtasks=[],
                    result=None,
                    error=None,
                    created_at=time.time(),
                    completed_at=None,
                    retry_count=0,
                    max_retries=3,
                    dependencies=[],
                    metadata={'context': context}
                )
                
                # 创建子任务
                for i, subtask_data in enumerate(plan_data.get('subtasks', [])):
                    subtask = Task(
                        id=subtask_data.get('id', f"task_{i}"),
                        description=subtask_data.get('description', ''),
                        status=TaskStatus.PENDING,
                        subtasks=[],
                        result=None,
                        error=None,
                        created_at=time.time(),
                        completed_at=None,
                        retry_count=0,
                        max_retries=3,
                        dependencies=subtask_data.get('dependencies', []),
                        metadata={'tool': subtask_data.get('tool')}
                    )
                    root_task.subtasks.append(subtask)
                
                return root_task
            else:
                raise ValueError("无法解析任务规划")
                
        except Exception as e:
            # 创建简单任务
            return Task(
                id=f"root_{int(time.time())}",
                description=goal,
                status=TaskStatus.PENDING,
                subtasks=[
                    Task(
                        id="task_1",
                        description=f"直接处理: {goal}",
                        status=TaskStatus.PENDING,
                        subtasks=[],
                        result=None,
                        error=None,
                        created_at=time.time(),
                        completed_at=None,
                        retry_count=0,
                        max_retries=3,
                        dependencies=[],
                        metadata={}
                    )
                ],
                result=None,
                error=None,
                created_at=time.time(),
                completed_at=None,
                retry_count=0,
                max_retries=3,
                dependencies=[],
                metadata={'context': context, 'planning_error': str(e)}
            )
    
    def execute_task(self, task: Task) -> bool:
        """执行任务"""
        task.status = TaskStatus.RUNNING
        
        try:
            # 检查依赖
            for dep_id in task.dependencies:
                # 这里应该检查依赖任务是否完成
                pass
            
            # 获取工具
            tool_name = task.metadata.get('tool')
            
            if tool_name and tool_name in self.tool_registry.tools:
                # 使用工具执行
                result = self.tool_registry.execute(tool_name, query=task.description)
            else:
                # 使用LLM直接处理
                execution_prompt = f"""
请完成以下任务:
{task.description}

直接给出结果，不要解释过程。
"""
                result = self.llm(execution_prompt)
            
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.completed_at = time.time()
            return True
            
        except Exception as e:
            task.error = str(e)
            task.retry_count += 1
            
            if task.retry_count < task.max_retries:
                task.status = TaskStatus.RETRYING
                return self.execute_task(task)  # 重试
            else:
                task.status = TaskStatus.FAILED
                return False
    
    def execute_plan(self, root_task: Task) -> Task:
        """执行整个计划"""
        print(f"开始执行任务: {root_task.description}")
        
        for subtask in root_task.subtasks:
            print(f"  执行子任务: {subtask.description}")
            success = self.execute_task(subtask)
            
            if not success:
                print(f"  ✗ 子任务失败: {subtask.error}")
            else:
                print(f"  ✓ 子任务完成")
        
        # 汇总结果
        results = [t.result for t in root_task.subtasks if t.result]
        root_task.result = "\n\n".join(results)
        root_task.status = TaskStatus.COMPLETED
        root_task.completed_at = time.time()
        
        return root_task
    
    def reflect(self, task: Task) -> str:
        """反思任务执行结果"""
        reflection_prompt = f"""
任务: {task.description}
结果: {task.result}

请反思:
1. 结果是否完整回答了问题？
2. 是否有遗漏或错误？
3. 如何改进？

请给出简洁的反思总结。
"""
        
        return self.llm(reflection_prompt)

# 使用示例
if __name__ == '__main__':
    # 模拟LLM函数
    def mock_llm(prompt):
        if "任务规划" in prompt:
            return '''
            {
                "subtasks": [
                    {
                        "id": "task_1",
                        "description": "搜索Python最新版本信息",
                        "tool": "web_search",
                        "dependencies": []
                    },
                    {
                        "id": "task_2",
                        "description": "总结Python新特性",
                        "tool": null,
                        "dependencies": ["task_1"]
                    }
                ]
            }
            '''
        else:
            return "这是模拟的LLM响应"
    
    # 创建规划器
    planner = TaskPlanner(mock_llm)
    
    # 规划任务
    goal = "了解Python 3.12的新特性"
    task = planner.plan(goal)
    
    print(f"任务规划: {task.description}")
    print(f"子任务数: {len(task.subtasks)}")
    
    # 执行任务
    result = planner.execute_plan(task)
    
    print(f"\n执行结果:")
    print(result.result)
