#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辉夜IDE 结构化工具系统
参考 Claude Code 的 Tool.ts 架构，实现统一的工具接口、权限验证和安全属性
"""

import os
import re
import subprocess
import fnmatch
import glob as glob_module
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from enum import Enum


class PermissionDecision(Enum):
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


@dataclass
class PermissionResult:
    decision: PermissionDecision
    message: str = ""
    updated_input: Optional[Dict[str, Any]] = None


@dataclass
class ValidationResult:
    result: bool
    message: str = ""
    error_code: int = 0


@dataclass
class ToolResult:
    data: Any = None
    error: Optional[str] = None
    new_messages: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ToolPermissionContext:
    mode: str = "default"
    allowed_paths: List[str] = field(default_factory=list)
    denied_paths: List[str] = field(default_factory=list)
    allowed_tools: List[str] = field(default_factory=list)
    denied_tools: List[str] = field(default_factory=list)
    read_only_mode: bool = False
    sandbox_mode: bool = False
    bypass_permissions: bool = False


class ToolUseContext:
    def __init__(
        self,
        permission_context: ToolPermissionContext = None,
        messages: List[Dict] = None,
        working_directory: str = None,
        abort_signal: bool = False,
    ):
        self.permission_context = permission_context or ToolPermissionContext()
        self.messages = messages or []
        self.working_directory = working_directory or os.getcwd()
        self.abort_signal = abort_signal
        self._progress_callbacks: List[Callable] = []

    def on_progress(self, callback: Callable):
        self._progress_callbacks.append(callback)

    def emit_progress(self, tool_use_id: str, data: Dict):
        for cb in self._progress_callbacks:
            cb(tool_use_id, data)


class Tool(ABC):
    name: str = ""
    description_text: str = ""
    max_result_size_chars: int = 100_000
    aliases: List[str] = []
    search_hint: str = ""

    @abstractmethod
    def call(self, args: Dict[str, Any], context: ToolUseContext) -> ToolResult:
        pass

    @abstractmethod
    def get_input_schema(self) -> Dict[str, Any]:
        pass

    def description(self, args: Dict[str, Any] = None) -> str:
        return self.description_text

    def prompt(self) -> str:
        return f"Tool: {self.name} - {self.description_text}"

    def is_enabled(self) -> bool:
        return True

    def is_read_only(self, args: Dict[str, Any] = None) -> bool:
        return False

    def is_concurrency_safe(self, args: Dict[str, Any] = None) -> bool:
        return False

    def is_destructive(self, args: Dict[str, Any] = None) -> bool:
        return not self.is_read_only(args)

    def check_permissions(
        self,
        args: Dict[str, Any],
        context: ToolUseContext,
    ) -> PermissionResult:
        if context.permission_context.bypass_permissions:
            return PermissionResult(decision=PermissionDecision.ALLOW)
        if self.name in context.permission_context.denied_tools:
            return PermissionResult(
                decision=PermissionDecision.DENY,
                message=f"Tool '{self.name}' is denied by permission settings",
            )
        if context.permission_context.allowed_tools and self.name not in context.permission_context.allowed_tools:
            return PermissionResult(
                decision=PermissionDecision.ASK,
                message=f"Tool '{self.name}' is not in allowed list",
            )
        if context.permission_context.read_only_mode and not self.is_read_only(args):
            return PermissionResult(
                decision=PermissionDecision.DENY,
                message=f"Tool '{self.name}' is not read-only and read-only mode is enabled",
            )
        return PermissionResult(decision=PermissionDecision.ALLOW)

    def validate_input(
        self,
        args: Dict[str, Any],
        context: ToolUseContext,
    ) -> ValidationResult:
        schema = self.get_input_schema()
        required = schema.get("required", [])
        for key in required:
            if key not in args:
                return ValidationResult(
                    result=False,
                    message=f"Missing required parameter: {key}",
                    error_code=1,
                )
        return ValidationResult(result=True)

    def get_path(self, args: Dict[str, Any]) -> Optional[str]:
        return None

    def user_facing_name(self, args: Dict[str, Any] = None) -> str:
        return self.name


class FileReadTool(Tool):
    name = "file_read"
    description_text = "Read file contents with line range support"
    search_hint = "read file contents"

    BLOCKED_PATHS = {"/dev/zero", "/dev/random", "/dev/urandom", "/dev/full"}

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to the file"},
                "offset": {"type": "integer", "description": "Line offset to start reading from"},
                "limit": {"type": "integer", "description": "Maximum number of lines to read"},
            },
            "required": ["file_path"],
        }

    def is_read_only(self, args=None) -> bool:
        return True

    def is_concurrency_safe(self, args=None) -> bool:
        return True

    def check_permissions(self, args, context):
        file_path = args.get("file_path", "")
        for denied in context.permission_context.denied_paths:
            if fnmatch.fnmatch(file_path, denied):
                return PermissionResult(
                    decision=PermissionDecision.DENY,
                    message=f"Access denied to path: {file_path}",
                )
        return super().check_permissions(args, context)

    def call(self, args: Dict[str, Any], context: ToolUseContext) -> ToolResult:
        file_path = args.get("file_path", "")
        offset = args.get("offset", 1)
        limit = args.get("limit", 2000)

        if not os.path.isabs(file_path):
            file_path = os.path.join(context.working_directory, file_path)

        if any(file_path.startswith(bp) for bp in self.BLOCKED_PATHS):
            return ToolResult(error=f"Blocked device path: {file_path}")

        try:
            if not os.path.exists(file_path):
                return ToolResult(error=f"File not found: {file_path}")

            if os.path.isdir(file_path):
                entries = os.listdir(file_path)
                return ToolResult(data="Directory listing:\n" + "\n".join(entries))

            file_size = os.path.getsize(file_path)
            max_size = 50 * 1024 * 1024
            if file_size > max_size:
                return ToolResult(
                    error=f"File too large ({file_size} bytes). Use offset/limit to read portions."
                )

            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            total_lines = len(lines)
            start = max(0, offset - 1)
            end = min(total_lines, start + limit)
            selected = lines[start:end]

            numbered = []
            for i, line in enumerate(selected, start=start + 1):
                numbered.append(f"{i:>6}\u2192{line.rstrip()}")

            result = "\n".join(numbered)
            if end < total_lines:
                result += f"\n... ({total_lines - end} more lines)"

            return ToolResult(data=result, metadata={"total_lines": total_lines, "file_path": file_path})

        except Exception as e:
            return ToolResult(error=f"Error reading file: {e}")


class FileWriteTool(Tool):
    name = "file_write"
    description_text = "Create or overwrite a file with content"
    search_hint = "write create file"

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to the file"},
                "content": {"type": "string", "description": "Content to write"},
            },
            "required": ["file_path", "content"],
        }

    def is_destructive(self, args=None) -> bool:
        return True

    def get_path(self, args):
        return args.get("file_path")

    def check_permissions(self, args, context):
        file_path = args.get("file_path", "")
        for denied in context.permission_context.denied_paths:
            if fnmatch.fnmatch(file_path, denied):
                return PermissionResult(
                    decision=PermissionDecision.DENY,
                    message=f"Write access denied to path: {file_path}",
                )
        return super().check_permissions(args, context)

    def call(self, args: Dict[str, Any], context: ToolUseContext) -> ToolResult:
        file_path = args.get("file_path", "")
        content = args.get("content", "")

        if not os.path.isabs(file_path):
            file_path = os.path.join(context.working_directory, file_path)

        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return ToolResult(
                data=f"File written: {file_path} ({len(content)} chars)",
                metadata={"file_path": file_path, "size": len(content)},
            )
        except Exception as e:
            return ToolResult(error=f"Error writing file: {e}")


class FileEditTool(Tool):
    name = "file_edit"
    description_text = "Edit a file by replacing old_string with new_string"
    search_hint = "modify edit file"

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to the file"},
                "old_string": {"type": "string", "description": "Text to find and replace"},
                "new_string": {"type": "string", "description": "Replacement text"},
                "replace_all": {"type": "boolean", "description": "Replace all occurrences"},
            },
            "required": ["file_path", "old_string", "new_string"],
        }

    def is_destructive(self, args=None) -> bool:
        return True

    def get_path(self, args):
        return args.get("file_path")

    def validate_input(self, args, context):
        old = args.get("old_string", "")
        new = args.get("new_string", "")
        if old == new:
            return ValidationResult(
                result=False,
                message="old_string and new_string are identical - no changes to make",
                error_code=1,
            )
        file_path = args.get("file_path", "")
        if not file_path:
            return ValidationResult(
                result=False, message="file_path is required", error_code=2
            )
        return ValidationResult(result=True)

    def call(self, args: Dict[str, Any], context: ToolUseContext) -> ToolResult:
        file_path = args.get("file_path", "")
        old_string = args.get("old_string", "")
        new_string = args.get("new_string", "")
        replace_all = args.get("replace_all", False)

        if not os.path.isabs(file_path):
            file_path = os.path.join(context.working_directory, file_path)

        try:
            if not os.path.exists(file_path):
                return ToolResult(error=f"File not found: {file_path}")

            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            if old_string not in content:
                return ToolResult(
                    error=f"old_string not found in {file_path}. Ensure the string matches exactly."
                )

            count = content.count(old_string)
            if count > 1 and not replace_all:
                return ToolResult(
                    error=f"Found {count} occurrences of old_string. Set replace_all=true to replace all, or provide more context to uniquely identify the target."
                )

            if replace_all:
                new_content = content.replace(old_string, new_string)
            else:
                new_content = content.replace(old_string, new_string, 1)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            return ToolResult(
                data=f"Edited {file_path}: replaced {count} occurrence(s)",
                metadata={"file_path": file_path, "replacements": count},
            )
        except Exception as e:
            return ToolResult(error=f"Error editing file: {e}")


class BashTool(Tool):
    name = "bash"
    description_text = "Execute shell commands"
    search_hint = "run execute shell command"

    SEARCH_COMMANDS = {"find", "grep", "rg", "ag", "ack", "locate", "which", "whereis"}
    READ_COMMANDS = {"cat", "head", "tail", "less", "more", "wc", "stat", "file"}
    LIST_COMMANDS = {"ls", "tree", "du"}
    SILENT_COMMANDS = {"mv", "cp", "rm", "mkdir", "rmdir", "chmod", "chown", "touch", "ln"}

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command to execute"},
                "timeout": {"type": "integer", "description": "Timeout in seconds (default 120)"},
                "working_dir": {"type": "string", "description": "Working directory"},
            },
            "required": ["command"],
        }

    def is_destructive(self, args=None) -> bool:
        if not args:
            return True
        cmd = args.get("command", "")
        destructive_keywords = ["rm ", "rmdir", "del ", "format", "mkfs", "dd ", "> /dev"]
        return any(kw in cmd for kw in destructive_keywords)

    def is_read_only(self, args=None) -> bool:
        if not args:
            return False
        cmd = args.get("command", "").strip()
        first_word = cmd.split()[0] if cmd.split() else ""
        return first_word in (self.SEARCH_COMMANDS | self.READ_COMMANDS | self.LIST_COMMANDS)

    def check_permissions(self, args, context):
        cmd = args.get("command", "")
        dangerous_patterns = [
            "rm -rf /", "format c:", "del /s /q c:\\", ":(){ :|:& };:",
            "dd if=/dev/zero", "mkfs.", "> /dev/sd",
        ]
        for pattern in dangerous_patterns:
            if pattern in cmd:
                return PermissionResult(
                    decision=PermissionDecision.DENY,
                    message=f"Dangerous command detected: {pattern}",
                )
        return super().check_permissions(args, context)

    def call(self, args: Dict[str, Any], context: ToolUseContext) -> ToolResult:
        command = args.get("command", "")
        timeout = args.get("timeout", 120)
        working_dir = args.get("working_dir", context.working_directory)

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=working_dir,
            )

            output = result.stdout
            if result.stderr:
                output += f"\nSTDERR:\n{result.stderr}"

            if result.returncode != 0:
                output += f"\nExit code: {result.returncode}"

            max_chars = self.max_result_size_chars
            if len(output) > max_chars:
                output = output[:max_chars] + f"\n... (truncated, {len(output)} total chars)"

            return ToolResult(
                data=output,
                metadata={"return_code": result.returncode, "command": command},
            )
        except subprocess.TimeoutExpired:
            return ToolResult(error=f"Command timed out after {timeout}s: {command}")
        except Exception as e:
            return ToolResult(error=f"Error executing command: {e}")


class GlobTool(Tool):
    name = "glob"
    description_text = "Find files matching a glob pattern"
    search_hint = "find search files pattern"

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Glob pattern (e.g. **/*.py)"},
                "path": {"type": "string", "description": "Directory to search in"},
            },
            "required": ["pattern"],
        }

    def is_read_only(self, args=None) -> bool:
        return True

    def is_concurrency_safe(self, args=None) -> bool:
        return True

    def call(self, args: Dict[str, Any], context: ToolUseContext) -> ToolResult:
        pattern = args.get("pattern", "**/*")
        search_path = args.get("path", context.working_directory)

        if not os.path.isabs(search_path):
            search_path = os.path.join(context.working_directory, search_path)

        try:
            matches = glob_module.glob(
                os.path.join(search_path, pattern), recursive=True
            )
            matches = [m for m in matches if os.path.isfile(m)]

            if not matches:
                return ToolResult(data="No files found matching pattern")

            max_results = 1000
            truncated = len(matches) > max_results
            matches = matches[:max_results]

            result = "\n".join(matches)
            if truncated:
                result += f"\n... (truncated, {len(matches)} of more results shown)"

            return ToolResult(data=result, metadata={"count": len(matches)})
        except Exception as e:
            return ToolResult(error=f"Error searching files: {e}")


class GrepTool(Tool):
    name = "grep"
    description_text = "Search file contents with regex pattern"
    search_hint = "search content regex"

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Regex pattern to search for"},
                "path": {"type": "string", "description": "Directory or file to search in"},
                "file_pattern": {"type": "string", "description": "File glob pattern (e.g. *.py)"},
                "case_insensitive": {"type": "boolean", "description": "Case insensitive search"},
            },
            "required": ["pattern"],
        }

    def is_read_only(self, args=None) -> bool:
        return True

    def is_concurrency_safe(self, args=None) -> bool:
        return True

    def call(self, args: Dict[str, Any], context: ToolUseContext) -> ToolResult:
        pattern = args.get("pattern", "")
        search_path = args.get("path", context.working_directory)
        file_pattern = args.get("file_pattern", "*")
        case_insensitive = args.get("case_insensitive", False)

        if not os.path.isabs(search_path):
            search_path = os.path.join(context.working_directory, search_path)

        try:
            flags = re.IGNORECASE if case_insensitive else 0
            regex = re.compile(pattern, flags)
        except re.error as e:
            return ToolResult(error=f"Invalid regex pattern: {e}")

        try:
            results = []
            if os.path.isfile(search_path):
                files = [search_path]
            else:
                files = glob_module.glob(
                    os.path.join(search_path, "**", file_pattern), recursive=True
                )
                files = [f for f in files if os.path.isfile(f)]

            max_results = 500
            for filepath in files:
                if len(results) >= max_results:
                    break
                try:
                    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                        for line_num, line in enumerate(f, 1):
                            if regex.search(line):
                                results.append(f"{filepath}:{line_num}: {line.rstrip()}")
                                if len(results) >= max_results:
                                    break
                except Exception:
                    continue

            if not results:
                return ToolResult(data="No matches found")

            output = "\n".join(results)
            return ToolResult(data=output, metadata={"count": len(results)})
        except Exception as e:
            return ToolResult(error=f"Error searching: {e}")


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool):
        self._tools[tool.name] = tool
        for alias in getattr(tool, "aliases", []):
            self._tools[alias] = tool

    def unregister(self, name: str):
        tool = self._tools.pop(name, None)
        if tool:
            for alias in getattr(tool, "aliases", []):
                self._tools.pop(alias, None)

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def list_tools(self) -> List[Tool]:
        seen = set()
        result = []
        for tool in self._tools.values():
            if tool.name not in seen:
                seen.add(tool.name)
                result.append(tool)
        return result

    def get_tools_prompt(self) -> str:
        prompts = []
        for tool in self.list_tools():
            schema = tool.get_input_schema()
            props = schema.get("properties", {})
            required = schema.get("required", [])
            params_desc = ", ".join(
                f"{k}{'(required)' if k in required else '(optional)'}: {v.get('description', '')}"
                for k, v in props.items()
            )
            safety = []
            if tool.is_read_only():
                safety.append("read-only")
            if tool.is_concurrency_safe():
                safety.append("concurrency-safe")
            if tool.is_destructive():
                safety.append("destructive")
            safety_str = f" [{', '.join(safety)}]" if safety else ""
            prompts.append(f"- {tool.name}{safety_str}: {tool.description()} | Params: {params_desc}")
        return "\n".join(prompts)

    def execute_tool(
        self,
        name: str,
        args: Dict[str, Any],
        context: ToolUseContext,
    ) -> ToolResult:
        tool = self.get(name)
        if not tool:
            return ToolResult(error=f"Unknown tool: {name}")

        if not tool.is_enabled():
            return ToolResult(error=f"Tool '{name}' is currently disabled")

        perm = tool.check_permissions(args, context)
        if perm.decision == PermissionDecision.DENY:
            return ToolResult(error=f"Permission denied: {perm.message}")
        if perm.decision == PermissionDecision.ASK:
            return ToolResult(error=f"Tool '{name}' requires user approval: {perm.message}")

        validation = tool.validate_input(args, context)
        if not validation.result:
            return ToolResult(error=f"Validation failed: {validation.message}")

        try:
            return tool.call(args, context)
        except Exception as e:
            return ToolResult(error=f"Tool execution error: {e}")


def create_default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(FileReadTool())
    registry.register(FileWriteTool())
    registry.register(FileEditTool())
    registry.register(BashTool())
    registry.register(GlobTool())
    registry.register(GrepTool())
    return registry
