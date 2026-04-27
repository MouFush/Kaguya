#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能工作流引擎 - 自动化任务编排与执行
功能: 可视化工作流设计、条件分支、并行执行、错误重试
"""

import json
import time
import uuid
import threading
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from collections import defaultdict
import traceback


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class WorkflowStatus(Enum):
    """工作流状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """工作流任务"""
    id: str
    name: str
    type: str  # 'action', 'condition', 'parallel', 'loop'
    config: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    next_tasks: List[str] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: float = 300.0
    
    # 运行时状态
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error_message: str = ""
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    execution_count: int = 0


@dataclass
class Workflow:
    """工作流定义"""
    id: str
    name: str
    description: str = ""
    tasks: Dict[str, Task] = field(default_factory=dict)
    start_task_id: Optional[str] = None
    variables: Dict[str, Any] = field(default_factory=dict)
    
    # 运行时状态
    status: WorkflowStatus = WorkflowStatus.PENDING
    current_task_ids: List[str] = field(default_factory=list)
    completed_task_ids: List[str] = field(default_factory=list)
    failed_task_ids: List[str] = field(default_factory=list)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    created_by: str = ""


class TaskExecutor:
    """任务执行器"""
    
    def __init__(self):
        self.action_handlers: Dict[str, Callable] = {}
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """注册默认处理器"""
        self.action_handlers['http_request'] = self._handle_http_request
        self.action_handlers['data_transform'] = self._handle_data_transform
        self.action_handlers['delay'] = self._handle_delay
        self.action_handlers['condition'] = self._handle_condition
        self.action_handlers['parallel'] = self._handle_parallel
        self.action_handlers['loop'] = self._handle_loop
        self.action_handlers['notify'] = self._handle_notify
    
    def register_handler(self, action_type: str, handler: Callable):
        """注册自定义处理器"""
        self.action_handlers[action_type] = handler
    
    def execute(self, task: Task, workflow: Workflow, context: Dict) -> Dict:
        """执行任务"""
        task.status = TaskStatus.RUNNING
        task.started_at = time.time()
        task.execution_count += 1
        
        try:
            handler = self.action_handlers.get(task.type)
            if not handler:
                raise ValueError(f"未知的任务类型: {task.type}")
            
            result = handler(task.config, workflow, context)
            
            task.status = TaskStatus.SUCCESS
            task.result = result
            task.completed_at = time.time()
            
            return {
                'success': True,
                'result': result,
                'execution_time': task.completed_at - task.started_at
            }
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            task.completed_at = time.time()
            
            return {
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
    
    def _handle_http_request(self, config: Dict, workflow: Workflow, context: Dict) -> Dict:
        """处理HTTP请求"""
        import urllib.request
        import urllib.parse
        
        url = config.get('url', '')
        method = config.get('method', 'GET')
        headers = config.get('headers', {})
        body = config.get('body', '')
        
        # 变量替换
        url = self._replace_variables(url, workflow, context)
        body = self._replace_variables(body, workflow, context)
        
        req = urllib.request.Request(
            url,
            data=body.encode() if body else None,
            headers=headers,
            method=method
        )
        
        with urllib.request.urlopen(req, timeout=config.get('timeout', 30)) as response:
            return {
                'status_code': response.status,
                'body': response.read().decode('utf-8'),
                'headers': dict(response.headers)
            }
    
    def _handle_data_transform(self, config: Dict, workflow: Workflow, context: Dict) -> Any:
        """处理数据转换"""
        operation = config.get('operation', 'pass')
        input_data = config.get('input', '')
        
        # 变量替换
        if isinstance(input_data, str):
            input_data = self._replace_variables(input_data, workflow, context)
        
        if operation == 'json_parse':
            return json.loads(input_data)
        elif operation == 'json_stringify':
            return json.dumps(input_data)
        elif operation == 'extract':
            field_path = config.get('field_path', '')
            data = input_data if isinstance(input_data, dict) else json.loads(input_data)
            for key in field_path.split('.'):
                data = data.get(key, {}) if isinstance(data, dict) else None
            return data
        elif operation == 'merge':
            sources = config.get('sources', [])
            result = {}
            for source in sources:
                if isinstance(source, str):
                    source = self._replace_variables(source, workflow, context)
                    source = json.loads(source)
                result.update(source)
            return result
        else:
            return input_data
    
    def _handle_delay(self, config: Dict, workflow: Workflow, context: Dict) -> Dict:
        """处理延迟"""
        seconds = config.get('seconds', 1)
        time.sleep(seconds)
        return {'delayed_seconds': seconds}
    
    def _handle_condition(self, config: Dict, workflow: Workflow, context: Dict) -> Dict:
        """处理条件分支"""
        condition = config.get('condition', '')
        
        # 变量替换
        condition = self._replace_variables(condition, workflow, context)
        
        # 简单的条件求值
        try:
            result = eval(condition, {"__builtins__": {}}, context)
            return {
                'condition_result': bool(result),
                'next_branch': 'true' if result else 'false'
            }
        except:
            return {
                'condition_result': False,
                'next_branch': 'false'
            }
    
    def _handle_parallel(self, config: Dict, workflow: Workflow, context: Dict) -> Dict:
        """处理并行任务"""
        # 并行任务由工作流引擎处理，这里只是占位
        return {'parallel': True}
    
    def _handle_loop(self, config: Dict, workflow: Workflow, context: Dict) -> Dict:
        """处理循环"""
        # 循环由工作流引擎处理，这里只是占位
        return {'loop': True}
    
    def _handle_notify(self, config: Dict, workflow: Workflow, context: Dict) -> Dict:
        """处理通知"""
        message = config.get('message', '')
        level = config.get('level', 'info')
        
        # 变量替换
        message = self._replace_variables(message, workflow, context)
        
        print(f"[{level.upper()}] {message}")
        
        return {
            'notified': True,
            'message': message,
            'level': level
        }
    
    def _replace_variables(self, text: str, workflow: Workflow, context: Dict) -> str:
        """替换变量"""
        if not isinstance(text, str):
            return text
        
        # 替换工作流变量
        for key, value in workflow.variables.items():
            placeholder = f"${{{key}}}"
            if placeholder in text:
                text = text.replace(placeholder, str(value))
        
        # 替换上下文变量
        for key, value in context.items():
            placeholder = f"${{{key}}}"
            if placeholder in text:
                text = text.replace(placeholder, str(value))
        
        return text


class WorkflowEngine:
    """工作流引擎"""
    
    def __init__(self):
        self.executor = TaskExecutor()
        self.workflows: Dict[str, Workflow] = {}
        self.running_workflows: Dict[str, threading.Thread] = {}
        self.workflow_results: Dict[str, Dict] = {}
        self.lock = threading.RLock()
        
        # 事件回调
        self.on_workflow_start: Optional[Callable] = None
        self.on_workflow_complete: Optional[Callable] = None
        self.on_task_complete: Optional[Callable] = None
    
    def create_workflow(self, name: str, description: str = "", 
                       created_by: str = "") -> Workflow:
        """创建工作流"""
        workflow = Workflow(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            created_by=created_by
        )
        
        with self.lock:
            self.workflows[workflow.id] = workflow
        
        return workflow
    
    def add_task(self, workflow_id: str, task: Task) -> bool:
        """添加任务到工作流"""
        with self.lock:
            if workflow_id not in self.workflows:
                return False
            
            workflow = self.workflows[workflow_id]
            workflow.tasks[task.id] = task
            
            # 如果没有设置起始任务，设置为第一个
            if workflow.start_task_id is None:
                workflow.start_task_id = task.id
            
            return True
    
    def start_workflow(self, workflow_id: str, variables: Dict = None) -> str:
        """启动工作流"""
        with self.lock:
            if workflow_id not in self.workflows:
                raise ValueError(f"工作流不存在: {workflow_id}")
            
            workflow = self.workflows[workflow_id]
            
            if workflow.status == WorkflowStatus.RUNNING:
                raise ValueError("工作流已在运行中")
            
            # 更新变量
            if variables:
                workflow.variables.update(variables)
            
            # 重置状态
            workflow.status = WorkflowStatus.RUNNING
            workflow.started_at = time.time()
            workflow.current_task_ids = [workflow.start_task_id] if workflow.start_task_id else []
            workflow.completed_task_ids = []
            workflow.failed_task_ids = []
            
            # 重置任务状态
            for task in workflow.tasks.values():
                task.status = TaskStatus.PENDING
                task.result = None
                task.error_message = ""
                task.started_at = None
                task.completed_at = None
                task.execution_count = 0
            
            # 启动执行线程
            thread = threading.Thread(
                target=self._execute_workflow,
                args=(workflow_id,),
                daemon=True
            )
            self.running_workflows[workflow_id] = thread
            thread.start()
            
            # 触发事件
            if self.on_workflow_start:
                self.on_workflow_start(workflow)
            
            return workflow_id
    
    def _execute_workflow(self, workflow_id: str):
        """执行工作流"""
        workflow = self.workflows[workflow_id]
        context = {}
        
        try:
            while workflow.current_task_ids:
                current_task_id = workflow.current_task_ids.pop(0)
                
                if current_task_id not in workflow.tasks:
                    continue
                
                task = workflow.tasks[current_task_id]
                
                # 检查依赖是否完成
                if not self._check_dependencies_complete(task, workflow):
                    # 依赖未完成，放回队列
                    workflow.current_task_ids.append(current_task_id)
                    time.sleep(0.1)
                    continue
                
                # 执行任务
                result = self.executor.execute(task, workflow, context)
                
                # 处理结果
                if result['success']:
                    workflow.completed_task_ids.append(current_task_id)
                    context[f"task_{task.id}_result"] = result['result']
                    
                    # 添加后续任务
                    if task.next_tasks:
                        workflow.current_task_ids.extend(task.next_tasks)
                    
                    # 触发任务完成事件
                    if self.on_task_complete:
                        self.on_task_complete(workflow, task, result)
                else:
                    # 任务失败，检查是否需要重试
                    if task.execution_count < task.max_retries:
                        task.status = TaskStatus.RETRYING
                        workflow.current_task_ids.append(current_task_id)
                        time.sleep(1)  # 重试延迟
                    else:
                        workflow.failed_task_ids.append(current_task_id)
                        
                        # 如果配置了错误处理
                        if task.config.get('on_error'):
                            error_handler = task.config['on_error']
                            if error_handler in workflow.tasks:
                                workflow.current_task_ids.append(error_handler)
                        else:
                            # 没有错误处理，工作流失败
                            workflow.status = WorkflowStatus.FAILED
                            break
                
                # 检查是否所有任务完成
                if not workflow.current_task_ids:
                    all_complete = all(
                        t.status in [TaskStatus.SUCCESS, TaskStatus.CANCELLED]
                        for t in workflow.tasks.values()
                    )
                    if all_complete:
                        workflow.status = WorkflowStatus.COMPLETED
                    else:
                        workflow.status = WorkflowStatus.FAILED
            
            workflow.completed_at = time.time()
            
            # 保存结果
            self.workflow_results[workflow_id] = {
                'status': workflow.status.value,
                'completed_tasks': workflow.completed_task_ids,
                'failed_tasks': workflow.failed_task_ids,
                'variables': workflow.variables,
                'context': context,
                'duration': workflow.completed_at - workflow.started_at if workflow.completed_at and workflow.started_at else 0
            }
            
            # 触发完成事件
            if self.on_workflow_complete:
                self.on_workflow_complete(workflow)
                
        except Exception as e:
            workflow.status = WorkflowStatus.FAILED
            workflow.completed_at = time.time()
            self.workflow_results[workflow_id] = {
                'status': 'failed',
                'error': str(e),
                'traceback': traceback.format_exc()
            }
    
    def _check_dependencies_complete(self, task: Task, workflow: Workflow) -> bool:
        """检查任务依赖是否完成"""
        for dep_id in task.dependencies:
            if dep_id not in workflow.tasks:
                return False
            dep_task = workflow.tasks[dep_id]
            if dep_task.status != TaskStatus.SUCCESS:
                return False
        return True
    
    def get_workflow_status(self, workflow_id: str) -> Dict:
        """获取工作流状态"""
        with self.lock:
            if workflow_id not in self.workflows:
                return {'error': '工作流不存在'}
            
            workflow = self.workflows[workflow_id]
            
            return {
                'id': workflow.id,
                'name': workflow.name,
                'status': workflow.status.value,
                'progress': {
                    'total': len(workflow.tasks),
                    'completed': len(workflow.completed_task_ids),
                    'failed': len(workflow.failed_task_ids),
                    'running': len([t for t in workflow.tasks.values() if t.status == TaskStatus.RUNNING])
                },
                'current_tasks': workflow.current_task_ids,
                'started_at': workflow.started_at,
                'completed_at': workflow.completed_at
            }
    
    def get_workflow_result(self, workflow_id: str) -> Dict:
        """获取工作流执行结果"""
        with self.lock:
            return self.workflow_results.get(workflow_id, {})
    
    def cancel_workflow(self, workflow_id: str) -> bool:
        """取消工作流"""
        with self.lock:
            if workflow_id not in self.workflows:
                return False
            
            workflow = self.workflows[workflow_id]
            workflow.status = WorkflowStatus.CANCELLED
            
            # 取消所有运行中的任务
            for task in workflow.tasks.values():
                if task.status == TaskStatus.RUNNING:
                    task.status = TaskStatus.CANCELLED
            
            return True
    
    def list_workflows(self) -> List[Dict]:
        """列出所有工作流"""
        with self.lock:
            return [
                {
                    'id': w.id,
                    'name': w.name,
                    'description': w.description,
                    'status': w.status.value,
                    'task_count': len(w.tasks),
                    'created_by': w.created_by
                }
                for w in self.workflows.values()
            ]


# 全局工作流引擎
workflow_engine = WorkflowEngine()


# 便捷函数
def create_workflow(name: str, description: str = "", created_by: str = "") -> Workflow:
    """创建工作流"""
    return workflow_engine.create_workflow(name, description, created_by)


def add_task(workflow_id: str, task: Task) -> bool:
    """添加任务"""
    return workflow_engine.add_task(workflow_id, task)


def start_workflow(workflow_id: str, variables: Dict = None) -> str:
    """启动工作流"""
    return workflow_engine.start_workflow(workflow_id, variables)


def get_workflow_status(workflow_id: str) -> Dict:
    """获取工作流状态"""
    return workflow_engine.get_workflow_status(workflow_id)


# 测试代码
if __name__ == '__main__':
    print("=" * 60)
    print("智能工作流引擎测试")
    print("=" * 60)
    
    engine = WorkflowEngine()
    
    # 创建工作流
    print("\n1. 创建工作流")
    workflow = engine.create_workflow(
        name="数据处理流程",
        description="示例数据处理工作流"
    )
    print(f"工作流ID: {workflow.id}")
    
    # 添加任务
    print("\n2. 添加任务")
    
    # 任务1: 数据获取
    task1 = Task(
        id="fetch_data",
        name="获取数据",
        type="http_request",
        config={
            'url': 'https://api.example.com/data',
            'method': 'GET'
        }
    )
    engine.add_task(workflow.id, task1)
    
    # 任务2: 数据处理
    task2 = Task(
        id="process_data",
        name="处理数据",
        type="data_transform",
        config={
            'operation': 'json_parse',
            'input': '${fetch_data_result}'
        },
        dependencies=["fetch_data"]
    )
    task1.next_tasks.append("process_data")
    engine.add_task(workflow.id, task2)
    
    # 任务3: 通知
    task3 = Task(
        id="notify",
        name="发送通知",
        type="notify",
        config={
            'message': '数据处理完成',
            'level': 'info'
        },
        dependencies=["process_data"]
    )
    task2.next_tasks.append("notify")
    engine.add_task(workflow.id, task3)
    
    print(f"添加了 {len(workflow.tasks)} 个任务")
    
    # 启动工作流
    print("\n3. 启动工作流")
    engine.start_workflow(workflow.id, {'user_id': '12345'})
    
    # 等待完成
    time.sleep(2)
    
    # 获取状态
    print("\n4. 工作流状态")
    status = engine.get_workflow_status(workflow.id)
    print(f"状态: {status['status']}")
    print(f"进度: {status['progress']}")
    
    # 获取结果
    print("\n5. 执行结果")
    result = engine.get_workflow_result(workflow.id)
    print(f"结果: {result}")
    
    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)
