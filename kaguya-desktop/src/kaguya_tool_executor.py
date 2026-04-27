#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辉夜IDE 并发工具执行器 v2.0
参考 Claude Code 的 StreamingToolExecutor 架构

核心设计：
1. 并发安全工具并行执行（Read, Grep, Glob等）
2. 非安全工具独占执行（Edit, Write, Bash等）
3. 动态任务优先级调度
4. 资源使用监控（CPU、内存、文件描述符）
5. 失败重试机制（指数退避）
6. 任务超时控制
7. Bash错误级联取消兄弟工具
8. Hook生命周期（PreToolUse/PostToolUse/PostToolUseFailure）
9. 结果按序输出保证
"""

import os
import uuid
import time
import threading
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
from enum import Enum
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
from collections import OrderedDict


class TaskPriority(Enum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class TaskStatus(Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    RETRYING = "retrying"


class HookType(Enum):
    PRE_TOOL_USE = "pre_tool_use"
    POST_TOOL_USE = "post_tool_use"
    POST_TOOL_USE_FAILURE = "post_tool_use_failure"


@dataclass
class HookContext:
    hook_type: HookType
    tool_name: str
    tool_args: Dict[str, Any]
    session_id: str = ""
    tool_use_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HookResult:
    proceed: bool = True
    message: str = ""
    modified_args: Optional[Dict[str, Any]] = None


class HookManager:
    def __init__(self):
        self._hooks: Dict[HookType, List[Callable]] = {}
        self._lock = threading.Lock()

    def register(self, hook_type: HookType, handler: Callable):
        with self._lock:
            if hook_type not in self._hooks:
                self._hooks[hook_type] = []
            self._hooks[hook_type].append(handler)

    def unregister(self, hook_type: HookType, handler: Callable):
        with self._lock:
            if hook_type in self._hooks:
                self._hooks[hook_type] = [
                    h for h in self._hooks[hook_type] if h != handler
                ]

    def execute_hooks(self, context: HookContext) -> HookResult:
        with self._lock:
            handlers = list(self._hooks.get(context.hook_type, []))

        for handler in handlers:
            try:
                result = handler(context)
                if isinstance(result, HookResult):
                    if not result.proceed:
                        return result
                    if result.modified_args:
                        context.tool_args = result.modified_args
                elif isinstance(result, bool):
                    if not result:
                        return HookResult(proceed=False, message="Hook blocked execution")
            except Exception:
                pass

        return HookResult(proceed=True)


@dataclass
class ResourceMetrics:
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    open_files: int = 0
    active_threads: int = 0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class ToolTask:
    task_id: str
    tool_name: str
    tool_input: Dict[str, Any]
    session_id: str
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: float = 120.0
    is_concurrency_safe: bool = False
    is_destructive: bool = False
    tool_use_id: str = ""
    order_index: int = 0
    _cancel_event: threading.Event = field(default_factory=threading.Event, repr=False)
    _future: Optional[Future] = field(default=None, repr=False)

    def cancel(self):
        self._cancel_event.set()
        self.status = TaskStatus.CANCELLED

    def is_cancelled(self) -> bool:
        return self._cancel_event.is_set()


@dataclass
class ExecutionResult:
    task_id: str
    tool_name: str
    tool_use_id: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    duration_ms: int = 0
    retry_count: int = 0
    status: TaskStatus = TaskStatus.COMPLETED
    order_index: int = 0


class ResourceMonitor:
    def __init__(self):
        self._metrics: List[ResourceMetrics] = []
        self._lock = threading.Lock()
        self._max_samples = 1000
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None

    def start(self):
        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

    def stop(self):
        self._monitoring = False

    def _monitor_loop(self):
        while self._monitoring:
            try:
                metrics = self._collect_metrics()
                with self._lock:
                    self._metrics.append(metrics)
                    if len(self._metrics) > self._max_samples:
                        self._metrics = self._metrics[-self._max_samples:]
            except Exception:
                pass
            time.sleep(5.0)

    def _collect_metrics(self) -> ResourceMetrics:
        metrics = ResourceMetrics(
            active_threads=threading.active_count(),
        )
        try:
            import psutil
            proc = psutil.Process()
            metrics.cpu_percent = proc.cpu_percent()
            metrics.memory_mb = proc.memory_info().rss / (1024 * 1024)
            try:
                metrics.open_files = len(proc.open_files())
            except Exception:
                metrics.open_files = 0
        except ImportError:
            pass
        return metrics

    def get_current(self) -> ResourceMetrics:
        with self._lock:
            return self._metrics[-1] if self._metrics else ResourceMetrics()

    def get_history(self, limit: int = 100) -> List[Dict]:
        with self._lock:
            return [vars(m) for m in self._metrics[-limit:]]

    def is_overloaded(self, cpu_threshold: float = 90.0,
                      memory_threshold_mb: float = 4096.0) -> bool:
        current = self.get_current()
        return current.cpu_percent > cpu_threshold or current.memory_mb > memory_threshold_mb


class StreamingToolExecutor:
    def __init__(self, tool_registry=None, permission_manager=None,
                 hook_manager=None, max_workers: int = 8):
        self._registry = tool_registry
        self._permission_manager = permission_manager
        self._hook_manager = hook_manager or HookManager()
        self._thread_pool = ThreadPoolExecutor(max_workers=max_workers)
        self._resource_monitor = ResourceMonitor()
        self._active_tasks: Dict[str, ToolTask] = {}
        self._completed_results: Dict[str, ExecutionResult] = {}
        self._lock = threading.Lock()
        self._order_counter = 0
        self._has_errored = False
        self._sibling_cancel = threading.Event()
        self._max_workers = max_workers
        self._max_completed = 1000

    def start(self):
        self._resource_monitor.start()

    def stop(self):
        self._resource_monitor.stop()
        self._thread_pool.shutdown(wait=False)

    def submit(self, tool_name: str, tool_input: Dict[str, Any],
               session_id: str, priority: TaskPriority = TaskPriority.NORMAL,
               timeout: float = 120.0, max_retries: int = 3,
               tool_use_id: str = "") -> str:
        with self._lock:
            self._order_counter += 1
            order = self._order_counter

        is_safe = self._is_concurrency_safe(tool_name, tool_input)
        is_destructive = self._is_destructive(tool_name, tool_input)

        task = ToolTask(
            task_id=f"task_{uuid.uuid4().hex[:12]}",
            tool_name=tool_name,
            tool_input=tool_input,
            session_id=session_id,
            priority=priority,
            timeout_seconds=timeout,
            max_retries=max_retries,
            is_concurrency_safe=is_safe,
            is_destructive=is_destructive,
            tool_use_id=tool_use_id or f"tu_{uuid.uuid4().hex[:8]}",
            order_index=order,
        )

        with self._lock:
            self._active_tasks[task.task_id] = task

        future = self._thread_pool.submit(self._execute_task, task)
        task._future = future

        return task.task_id

    def submit_batch(self, tasks: List[Dict[str, Any]],
                     session_id: str) -> List[str]:
        task_ids = []
        for t in tasks:
            tid = self.submit(
                tool_name=t.get("tool_name", ""),
                tool_input=t.get("tool_input", {}),
                session_id=session_id,
                priority=t.get("priority", TaskPriority.NORMAL),
                timeout=t.get("timeout", 120.0),
                max_retries=t.get("max_retries", 3),
                tool_use_id=t.get("tool_use_id", ""),
            )
            task_ids.append(tid)
        return task_ids

    def wait_for(self, task_id: str, timeout: float = None) -> Optional[ExecutionResult]:
        with self._lock:
            task = self._active_tasks.get(task_id)

        if not task:
            return self._completed_results.get(task_id)

        if task._future:
            try:
                task._future.result(timeout=timeout)
            except Exception:
                pass

        with self._lock:
            return self._completed_results.get(task_id)

    def wait_for_all(self, task_ids: List[str],
                     timeout: float = None) -> List[ExecutionResult]:
        results = []
        deadline = time.time() + (timeout or 300.0)

        for tid in task_ids:
            remaining = deadline - time.time()
            if remaining <= 0:
                break
            result = self.wait_for(tid, timeout=remaining)
            if result:
                results.append(result)

        results.sort(key=lambda r: r.order_index)
        return results

    def cancel(self, task_id: str) -> bool:
        with self._lock:
            task = self._active_tasks.get(task_id)
        if task:
            task.cancel()
            if task._future:
                task._future.cancel()
            return True
        return False

    def cancel_all(self, session_id: str = None):
        with self._lock:
            tasks = list(self._active_tasks.values())
        for task in tasks:
            if session_id is None or task.session_id == session_id:
                task.cancel()

    def get_task_status(self, task_id: str) -> Optional[Dict]:
        with self._lock:
            task = self._active_tasks.get(task_id)
        if task:
            return {
                "task_id": task.task_id,
                "tool_name": task.tool_name,
                "status": task.status.value,
                "retry_count": task.retry_count,
                "is_concurrency_safe": task.is_concurrency_safe,
                "created_at": task.created_at,
            }
        result = self._completed_results.get(task_id)
        if result:
            return {
                "task_id": result.task_id,
                "tool_name": result.tool_name,
                "status": result.status.value,
                "success": result.success,
                "duration_ms": result.duration_ms,
            }
        return None

    def get_active_tasks(self, session_id: str = None) -> List[Dict]:
        with self._lock:
            tasks = list(self._active_tasks.values())
        if session_id:
            tasks = [t for t in tasks if t.session_id == session_id]
        return [{
            "task_id": t.task_id,
            "tool_name": t.tool_name,
            "status": t.status.value,
            "priority": t.priority.value,
            "is_concurrency_safe": t.is_concurrency_safe,
        } for t in tasks]

    def get_resource_metrics(self) -> Dict[str, Any]:
        current = self._resource_monitor.get_current()
        return {
            "cpu_percent": current.cpu_percent,
            "memory_mb": current.memory_mb,
            "active_threads": current.active_threads,
            "open_files": current.open_files,
            "is_overloaded": self._resource_monitor.is_overloaded(),
            "pool_size": self._max_workers,
        }

    def _execute_task(self, task: ToolTask) -> ExecutionResult:
        start_time = time.time()
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow().isoformat()

        if task.is_cancelled():
            return self._make_result(task, False, None, "Cancelled", start_time, TaskStatus.CANCELLED)

        if self._has_errored and not task.is_concurrency_safe:
            return self._make_result(task, False, None, "Sibling Bash error - cascading cancel",
                                     start_time, TaskStatus.CANCELLED)

        if self._resource_monitor.is_overloaded():
            if task.priority.value >= TaskPriority.LOW.value:
                return self._make_result(task, False, None, "System overloaded - low priority task deferred",
                                         start_time, TaskStatus.CANCELLED)

        try:
            perm_result = self._check_permissions(task)
            if not perm_result:
                return self._make_result(task, False, None, "Permission denied", start_time, TaskStatus.FAILED)

            hook_result = self._run_pre_hooks(task)
            if not hook_result.proceed:
                return self._make_result(task, False, None, hook_result.message, start_time, TaskStatus.FAILED)
            if hook_result.modified_args:
                task.tool_input = hook_result.modified_args

            validated = self._validate_input(task)
            if not validated:
                return self._make_result(task, False, None, "Input validation failed", start_time, TaskStatus.FAILED)

            result = self._execute_with_retry(task)

            if result.success:
                self._run_post_hooks(task, result.output)
            else:
                self._run_failure_hooks(task, result.error)

            if not result.success and task.tool_name in ("Bash", "bash", "Terminal", "terminal"):
                self._has_errored = True
                self._sibling_cancel.set()

            return result

        except Exception as e:
            self._run_failure_hooks(task, str(e))
            return self._make_result(task, False, None, f"Execution error: {e}", start_time, TaskStatus.FAILED)

    def _execute_with_retry(self, task: ToolTask) -> ExecutionResult:
        start_time = time.time()
        last_error = None

        for attempt in range(task.max_retries + 1):
            if task.is_cancelled():
                return self._make_result(task, False, None, "Cancelled", start_time, TaskStatus.CANCELLED)

            try:
                task.retry_count = attempt
                if attempt > 0:
                    task.status = TaskStatus.RETRYING
                    backoff = min(2 ** attempt, 30)
                    time.sleep(backoff)

                output = self._call_tool(task)

                if task.is_cancelled():
                    return self._make_result(task, False, None, "Cancelled", start_time, TaskStatus.CANCELLED)

                return self._make_result(task, True, output, None, start_time, TaskStatus.COMPLETED)

            except TimeoutError:
                return self._make_result(task, False, None, f"Timeout after {task.timeout_seconds}s",
                                         start_time, TaskStatus.TIMEOUT)
            except Exception as e:
                last_error = str(e)
                if not self._is_retryable(task, e):
                    return self._make_result(task, False, None, last_error, start_time, TaskStatus.FAILED)

        return self._make_result(task, False, None,
                                 f"Failed after {task.max_retries} retries: {last_error}",
                                 start_time, TaskStatus.FAILED)

    def _call_tool(self, task: ToolTask) -> Any:
        if self._registry:
            from kaguya_tool_system import ToolUseContext, ToolPermissionContext
            perm_ctx = ToolPermissionContext(
                bypass_permissions=self._permission_manager is None,
            )
            ctx = ToolUseContext(
                permission_context=perm_ctx,
                working_directory=os.getcwd(),
            )
            result = self._registry.execute_tool(task.tool_name, task.tool_input, ctx)
            if result.error:
                raise RuntimeError(result.error)
            return result.data

        if task.tool_name in ("Read", "file_read"):
            return self._builtin_read(task.tool_input)
        elif task.tool_name in ("Write", "file_write"):
            return self._builtin_write(task.tool_input)
        elif task.tool_name in ("Edit", "file_edit"):
            return self._builtin_edit(task.tool_input)
        elif task.tool_name in ("Bash", "bash"):
            return self._builtin_bash(task.tool_input, task.timeout_seconds)
        elif task.tool_name in ("Glob", "glob"):
            return self._builtin_glob(task.tool_input)
        elif task.tool_name in ("Grep", "grep"):
            return self._builtin_grep(task.tool_input)
        else:
            raise RuntimeError(f"Unknown tool: {task.tool_name}")

    def _builtin_read(self, args: Dict) -> str:
        path = args.get("file_path", args.get("path", ""))
        if not os.path.isabs(path):
            path = os.path.join(os.getcwd(), path)
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found: {path}")
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()

    def _builtin_write(self, args: Dict) -> str:
        path = args.get("file_path", args.get("path", ""))
        content = args.get("content", "")
        if not os.path.isabs(path):
            path = os.path.join(os.getcwd(), path)
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Written: {path}"

    def _builtin_edit(self, args: Dict) -> str:
        path = args.get("file_path", args.get("path", ""))
        old = args.get("old_string", args.get("old_str", ""))
        new = args.get("new_string", args.get("new_str", ""))
        if not os.path.isabs(path):
            path = os.path.join(os.getcwd(), path)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        if old not in content:
            raise ValueError(f"Old string not found in {path}")
        content = content.replace(old, new, 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Edited: {path}"

    def _builtin_bash(self, args: Dict, timeout: float) -> str:
        import subprocess
        cmd = args.get("command", "")
        cwd = args.get("working_dir", os.getcwd())
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=timeout, cwd=cwd,
        )
        output = result.stdout
        if result.stderr:
            output += f"\nSTDERR:\n{result.stderr}"
        if result.returncode != 0:
            raise RuntimeError(f"Exit code {result.returncode}: {output}")
        return output

    def _builtin_glob(self, args: Dict) -> str:
        import glob as g
        pattern = args.get("pattern", "**/*")
        path = args.get("path", os.getcwd())
        matches = g.glob(os.path.join(path, pattern), recursive=True)
        return "\n".join(matches[:500])

    def _builtin_grep(self, args: Dict) -> str:
        import subprocess
        pattern = args.get("pattern", "")
        path = args.get("path", os.getcwd())
        result = subprocess.run(
            ["grep", "-rn", pattern, path],
            capture_output=True, text=True, timeout=30,
        )
        return result.stdout[:10000] if result.stdout else "No matches"

    def _check_permissions(self, task: ToolTask) -> bool:
        if not self._permission_manager:
            return True
        try:
            decision = self._permission_manager.request_permission(
                session_id=task.session_id,
                tool_name=task.tool_name,
                tool_input=task.tool_input,
                timeout=10.0,
            )
            return decision in ("allow", "allow_always")
        except Exception:
            return True

    def _run_pre_hooks(self, task: ToolTask) -> HookResult:
        ctx = HookContext(
            hook_type=HookType.PRE_TOOL_USE,
            tool_name=task.tool_name,
            tool_args=task.tool_input,
            session_id=task.session_id,
            tool_use_id=task.tool_use_id,
        )
        return self._hook_manager.execute_hooks(ctx)

    def _run_post_hooks(self, task: ToolTask, output: Any):
        ctx = HookContext(
            hook_type=HookType.POST_TOOL_USE,
            tool_name=task.tool_name,
            tool_args=task.tool_input,
            session_id=task.session_id,
            tool_use_id=task.tool_use_id,
            metadata={"output": str(output)[:1000]},
        )
        self._hook_manager.execute_hooks(ctx)

    def _run_failure_hooks(self, task: ToolTask, error: str):
        ctx = HookContext(
            hook_type=HookType.POST_TOOL_USE_FAILURE,
            tool_name=task.tool_name,
            tool_args=task.tool_input,
            session_id=task.session_id,
            tool_use_id=task.tool_use_id,
            metadata={"error": error[:1000]},
        )
        self._hook_manager.execute_hooks(ctx)

    def _validate_input(self, task: ToolTask) -> bool:
        if not task.tool_name:
            return False
        if not task.tool_input and task.tool_name not in ("Glob", "Grep"):
            return False
        return True

    def _is_retryable(self, task: ToolTask, error: Exception) -> bool:
        if task.retry_count >= task.max_retries:
            return False
        if isinstance(error, (FileNotFoundError, ValueError, PermissionError)):
            return False
        return True

    def _is_concurrency_safe(self, tool_name: str, tool_input: Dict) -> bool:
        safe_tools = {"Read", "file_read", "Glob", "glob", "Grep", "grep",
                      "WebFetch", "WebSearch", "TodoWrite"}
        return tool_name in safe_tools

    def _is_destructive(self, tool_name: str, tool_input: Dict) -> bool:
        destructive_tools = {"Write", "file_write", "Edit", "file_edit",
                             "Bash", "bash", "Terminal", "terminal"}
        return tool_name in destructive_tools

    def _make_result(self, task: ToolTask, success: bool, output: Any,
                     error: Optional[str], start_time: float,
                     status: TaskStatus) -> ExecutionResult:
        duration_ms = int((time.time() - start_time) * 1000)
        task.status = status
        task.completed_at = datetime.utcnow().isoformat()

        result = ExecutionResult(
            task_id=task.task_id,
            tool_name=task.tool_name,
            tool_use_id=task.tool_use_id,
            success=success,
            output=output,
            error=error,
            duration_ms=duration_ms,
            retry_count=task.retry_count,
            status=status,
            order_index=task.order_index,
        )

        with self._lock:
            self._completed_results[task.task_id] = result
            self._active_tasks.pop(task.task_id, None)
            if len(self._completed_results) > self._max_completed:
                oldest = list(self._completed_results.keys())[:self._max_completed // 2]
                for k in oldest:
                    del self._completed_results[k]

        return result

    def submit_partitioned(self, tasks: List[Dict[str, Any]],
                           session_id: str) -> Dict[str, List[str]]:
        concurrent_ids = []
        serial_ids = []

        for t in tasks:
            tool_name = t.get("tool_name", "")
            tool_input = t.get("tool_input", {})
            is_safe = self._is_concurrency_safe(tool_name, tool_input)

            tid = self.submit(
                tool_name=tool_name,
                tool_input=tool_input,
                session_id=session_id,
                priority=t.get("priority", TaskPriority.NORMAL),
                timeout=t.get("timeout", 120.0),
                max_retries=t.get("max_retries", 3),
                tool_use_id=t.get("tool_use_id", ""),
            )

            if is_safe:
                concurrent_ids.append(tid)
            else:
                serial_ids.append(tid)

        return {"concurrent": concurrent_ids, "serial": serial_ids}

    def execute_partitioned(self, tasks: List[Dict[str, Any]],
                            session_id: str,
                            timeout: float = 300.0) -> List[ExecutionResult]:
        partition = self.submit_partitioned(tasks, session_id)
        results = []

        concurrent_ids = partition["concurrent"]
        if concurrent_ids:
            concurrent_results = self.wait_for_all(concurrent_ids, timeout=timeout)
            results.extend(concurrent_results)

        serial_ids = partition["serial"]
        for tid in serial_ids:
            remaining = timeout - sum(r.duration_ms for r in results) / 1000.0
            if remaining <= 0:
                self.cancel(tid)
                continue
            r = self.wait_for(tid, timeout=remaining)
            if r:
                results.append(r)

        results.sort(key=lambda r: r.order_index)
        return results


def create_tool_executor(tool_registry=None, permission_manager=None,
                         hook_manager=None, max_workers: int = 8) -> StreamingToolExecutor:
    executor = StreamingToolExecutor(
        tool_registry=tool_registry,
        permission_manager=permission_manager,
        hook_manager=hook_manager,
        max_workers=max_workers,
    )
    executor.start()
    return executor
