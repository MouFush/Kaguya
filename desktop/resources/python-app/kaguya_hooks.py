#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辉夜IDE 钩子系统
参考 Claude Code 的 hooks.ts 架构，实现工具执行生命周期钩子
"""

import json
import os
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
from enum import Enum
from datetime import datetime


class HookType(Enum):
    PRE_TOOL_USE = "pre_tool_use"
    POST_TOOL_USE = "post_tool_use"
    PRE_COMPACT = "pre_compact"
    POST_COMPACT = "post_compact"
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    PRE_EDIT = "pre_edit"
    POST_EDIT = "post_edit"
    PRE_WRITE = "pre_write"
    POST_WRITE = "post_write"
    PRE_BASH = "pre_bash"
    POST_BASH = "post_bash"


@dataclass
class HookResult:
    success: bool
    message: str = ""
    data: Optional[Dict[str, Any]] = None
    should_block: bool = False
    modified_input: Optional[Dict[str, Any]] = None


@dataclass
class HookDefinition:
    name: str
    hook_type: HookType
    handler: Optional[Callable] = None
    command: Optional[str] = None
    enabled: bool = True
    priority: int = 100
    tool_filter: Optional[List[str]] = None
    path_filter: Optional[List[str]] = None


@dataclass
class HookContext:
    hook_type: HookType
    tool_name: str = ""
    tool_args: Dict[str, Any] = field(default_factory=dict)
    tool_result: Optional[Any] = None
    file_path: Optional[str] = None
    session_id: str = ""
    timestamp: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class HookManager:
    DEFAULT_COMMAND_TIMEOUT = 60
    MAX_COMMAND_TIMEOUT = 300

    def __init__(self, config_path: str = None, command_timeout: int = None):
        self._hooks: Dict[HookType, List[HookDefinition]] = {
            ht: [] for ht in HookType
        }
        self._config_path = config_path
        self._execution_log: List[Dict] = []
        self._command_timeout = min(
            command_timeout or self.DEFAULT_COMMAND_TIMEOUT,
            self.MAX_COMMAND_TIMEOUT
        )

        if config_path and os.path.exists(config_path):
            self.load_config(config_path)

    def register(self, hook: HookDefinition):
        if hook.hook_type not in self._hooks:
            self._hooks[hook.hook_type] = []
        self._hooks[hook.hook_type].append(hook)
        self._hooks[hook.hook_type].sort(key=lambda h: h.priority)

    def unregister(self, name: str):
        for ht in HookType:
            self._hooks[ht] = [h for h in self._hooks[ht] if h.name != name]

    def _match_filters(self, hook: HookDefinition, context: HookContext) -> bool:
        if hook.tool_filter and context.tool_name not in hook.tool_filter:
            return False
        if hook.path_filter and context.file_path:
            import fnmatch
            if not any(fnmatch.fnmatch(context.file_path, p) for p in hook.path_filter):
                return False
        return True

    def _execute_command_hook(self, command: str, context: HookContext) -> HookResult:
        env = {
            "KAGUYA_HOOK_TYPE": context.hook_type.value,
            "KAGUYA_TOOL_NAME": context.tool_name,
            "KAGUYA_FILE_PATH": context.file_path or "",
            "KAGUYA_SESSION_ID": context.session_id,
            "KAGUYA_TIMESTAMP": context.timestamp,
        }
        env.update(os.environ)

        if context.tool_args:
            env["KAGUYA_TOOL_ARGS"] = json.dumps(context.tool_args, ensure_ascii=False)

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self._command_timeout,
                env=env,
            )

            if result.returncode == 0:
                data = None
                if result.stdout.strip():
                    try:
                        data = json.loads(result.stdout.strip())
                    except json.JSONDecodeError:
                        pass

                return HookResult(
                    success=True,
                    message=result.stdout.strip() or "Hook executed successfully",
                    data=data,
                    should_block=False,
                )
            else:
                return HookResult(
                    success=False,
                    message=f"Hook command failed (exit {result.returncode}): {result.stderr.strip()}",
                    should_block=result.returncode == 2,
                )
        except subprocess.TimeoutExpired:
            return HookResult(
                success=False,
                message=f"Hook command timed out after {self._command_timeout}s",
                should_block=False,
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Hook execution error: {e}", exc_info=True)
            return HookResult(
                success=False,
                message=f"Hook execution error: {e}",
                should_block=False,
            )

    def _execute_handler_hook(self, handler: Callable, context: HookContext) -> HookResult:
        try:
            result = handler(context)
            if isinstance(result, HookResult):
                return result
            if isinstance(result, bool):
                return HookResult(success=result)
            if isinstance(result, dict):
                return HookResult(
                    success=result.get("success", True),
                    message=result.get("message", ""),
                    data=result.get("data"),
                    should_block=result.get("should_block", False),
                    modified_input=result.get("modified_input"),
                )
            return HookResult(success=True)
        except Exception as e:
            return HookResult(
                success=False,
                message=f"Hook handler error: {e}",
                should_block=False,
            )

    def execute_hooks(self, context: HookContext) -> List[HookResult]:
        hooks = self._hooks.get(context.hook_type, [])
        results = []

        for hook in hooks:
            if not hook.enabled:
                continue

            if not self._match_filters(hook, context):
                continue

            start_time = time.time()

            if hook.command:
                result = self._execute_command_hook(hook.command, context)
            elif hook.handler:
                result = self._execute_handler_hook(hook.handler, context)
            else:
                continue

            duration = time.time() - start_time

            self._execution_log.append({
                "hook_name": hook.name,
                "hook_type": context.hook_type.value,
                "tool_name": context.tool_name,
                "success": result.success,
                "duration_ms": int(duration * 1000),
                "timestamp": context.timestamp,
            })

            results.append(result)

            if result.should_block:
                break

        return results

    def should_proceed(self, context: HookContext) -> Tuple[bool, str]:
        results = self.execute_hooks(context)

        for result in results:
            if result.should_block:
                return False, result.message
            if result.modified_input and context.tool_args:
                context.tool_args.update(result.modified_input)

        return True, ""

    def load_config(self, config_path: str):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception:
            return

        hooks_config = config.get("hooks", [])
        for hc in hooks_config:
            hook_type_str = hc.get("type", "")
            try:
                hook_type = HookType(hook_type_str)
            except ValueError:
                continue

            hook = HookDefinition(
                name=hc.get("name", "unnamed"),
                hook_type=hook_type,
                command=hc.get("command"),
                enabled=hc.get("enabled", True),
                priority=hc.get("priority", 100),
                tool_filter=hc.get("tool_filter"),
                path_filter=hc.get("path_filter"),
            )
            self.register(hook)

    def save_config(self, config_path: str = None):
        path = config_path or self._config_path
        if not path:
            return

        hooks_list = []
        for ht in HookType:
            for hook in self._hooks[ht]:
                if hook.handler:
                    continue
                hooks_list.append({
                    "name": hook.name,
                    "type": hook.hook_type.value,
                    "command": hook.command,
                    "enabled": hook.enabled,
                    "priority": hook.priority,
                    "tool_filter": hook.tool_filter,
                    "path_filter": hook.path_filter,
                })

        config = {"hooks": hooks_list}
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

    def get_execution_log(self, limit: int = 100) -> List[Dict]:
        return self._execution_log[-limit:]

    def list_hooks(self, hook_type: HookType = None) -> List[Dict]:
        result = []
        types = [hook_type] if hook_type else list(HookType)
        for ht in types:
            for hook in self._hooks.get(ht, []):
                result.append({
                    "name": hook.name,
                    "type": ht.value,
                    "enabled": hook.enabled,
                    "priority": hook.priority,
                    "has_command": hook.command is not None,
                    "has_handler": hook.handler is not None,
                    "tool_filter": hook.tool_filter,
                    "path_filter": hook.path_filter,
                })
        return result


def create_default_hooks() -> HookManager:
    manager = HookManager()

    manager.register(HookDefinition(
        name="log_bash_commands",
        hook_type=HookType.PRE_BASH,
        priority=10,
        handler=lambda ctx: HookResult(
            success=True,
            message=f"Bash: {ctx.tool_args.get('command', '')[:100]}",
        ),
    ))

    manager.register(HookDefinition(
        name="log_file_edits",
        hook_type=HookType.PRE_EDIT,
        priority=10,
        handler=lambda ctx: HookResult(
            success=True,
            message=f"Edit: {ctx.file_path or ctx.tool_args.get('file_path', '')}",
        ),
    ))

    manager.register(HookDefinition(
        name="block_sensitive_paths",
        hook_type=HookType.PRE_WRITE,
        priority=5,
        path_filter=["/etc/*", "/usr/*", "C:\\Windows\\*", "*.env", "*secret*", "*credential*"],
        handler=lambda ctx: HookResult(
            success=False,
            should_block=True,
            message=f"Write to sensitive path blocked: {ctx.file_path}",
        ),
    ))

    return manager
