#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辉夜IDE 子代理系统
参考 Claude Code 的 AgentTool/forkSubagent/runAgent 架构
实现多代理调度、Fork优化和Prompt缓存共享

核心设计：
1. 三种调度路径：命名Agent（专业委派）、Fork子进程（缓存共享）、GP回退（通用处理）
2. Fork优化：共享system prompt字节、工具集、thinking配置，最大化Prompt Cache命中率
3. 内置Agent：Explore（只读探索）、Plan（方案设计）、General-purpose（通用）、Verification（验证）
"""

import json
import os
import uuid
import copy
import time
import threading
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generator, List, Optional, Set, Tuple
from enum import Enum
from datetime import datetime
from abc import ABC, abstractmethod


class AgentExecutionMode(Enum):
    SYNC = "sync"
    ASYNC = "async"


class AgentIsolation(Enum):
    NONE = "none"
    WORKTREE = "worktree"
    REMOTE = "remote"


class AgentMemoryScope(Enum):
    NONE = "none"
    SESSION = "session"
    PROJECT = "project"
    GLOBAL = "global"


@dataclass
class AgentDefinition:
    agent_type: str
    when_to_use: str
    tools: List[str] = None
    disallowed_tools: List[str] = None
    skills: List[str] = None
    model: str = "inherit"
    effort: str = "medium"
    permission_mode: str = "acceptEdits"
    max_turns: int = 200
    background: bool = False
    isolation: AgentIsolation = AgentIsolation.NONE
    memory: AgentMemoryScope = AgentMemoryScope.SESSION
    omit_project_md: bool = False
    source: str = "built-in"
    color: str = "blue"
    auto_background_ms: int = 120000
    hooks: Dict[str, Any] = None
    get_system_prompt: Optional[Callable] = None

    def __post_init__(self):
        if self.tools is None:
            self.tools = ["*"]
        if self.disallowed_tools is None:
            self.disallowed_tools = []
        if self.skills is None:
            self.skills = []
        if self.hooks is None:
            self.hooks = {}


@dataclass
class AgentResult:
    success: bool
    output: str = ""
    error: Optional[str] = None
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    files_changed: List[str] = field(default_factory=list)
    usage: Dict[str, int] = field(default_factory=dict)
    duration_ms: int = 0
    agent_type: str = ""
    session_id: str = ""


@dataclass
class AgentContext:
    session_id: str
    working_directory: str
    messages: List[Dict[str, Any]] = field(default_factory=list)
    available_tools: List[str] = field(default_factory=list)
    system_prompt: str = ""
    rendered_system_prompt: str = ""
    permission_mode: str = "default"
    model: str = ""
    thinking_budget: int = 10000
    abort_signal: bool = False
    parent_session_id: str = ""
    is_fork: bool = False
    content_replacement_state: Dict[str, Any] = field(default_factory=dict)
    query_source: str = ""


FORK_PLACEHOLDER_RESULT = "Fork started — processing in background"

FORK_BOILERPLATE = """<fork-boilerplate>
You are a fork worker, not the main agent. Your task is to execute the directive below directly.

Rules:
- Do NOT spawn sub-agents (execute tasks directly yourself)
- Do not engage in small talk or meta-commentary
- Use tools directly to accomplish the task
- After modifying files, report what you changed
- Report format: Scope: / Result: / Key files: / Files changed: / Issues:
</fork-boilerplate>

Directive:
{directive}"""


class BuiltInAgents:
    @staticmethod
    def get_general_purpose() -> AgentDefinition:
        return AgentDefinition(
            agent_type="general-purpose",
            when_to_use="General-purpose agent for researching complex questions, implementing features, and performing multi-step tasks that require tool use",
            tools=["*"],
            model="inherit",
            permission_mode="acceptEdits",
            max_turns=200,
            get_system_prompt=lambda: (
                "You are a general-purpose AI agent working in an IDE environment. "
                "You have access to file operations, terminal commands, search tools, and more. "
                "Execute tasks efficiently by using the appropriate tools. "
                "Be thorough but concise in your responses."
            ),
        )

    @staticmethod
    def get_explore() -> AgentDefinition:
        return AgentDefinition(
            agent_type="Explore",
            when_to_use="Fast agent specialized for exploring codebases, finding files, understanding project structure, and searching for patterns",
            tools=["Read", "Glob", "Grep", "WebFetch", "WebSearch"],
            disallowed_tools=["Edit", "Write", "Bash", "Agent", "NotebookEdit"],
            model="inherit",
            effort="low",
            permission_mode="dontAsk",
            omit_project_md=True,
            max_turns=50,
            color="green",
            get_system_prompt=lambda: (
                "You are a codebase exploration agent. Your job is to quickly find and understand code. "
                "Use search and read tools to locate relevant files and understand their structure. "
                "Be fast and efficient. Do not modify any files. "
                "Report your findings clearly with file paths and line numbers."
            ),
        )

    @staticmethod
    def get_plan() -> AgentDefinition:
        return AgentDefinition(
            agent_type="Plan",
            when_to_use="Software architect agent for designing implementation plans, analyzing requirements, and creating detailed step-by-step approaches",
            tools=["Read", "Glob", "Grep", "WebFetch", "WebSearch"],
            disallowed_tools=["Edit", "Write", "Bash", "Agent", "NotebookEdit"],
            model="inherit",
            effort="high",
            permission_mode="dontAsk",
            omit_project_md=True,
            max_turns=50,
            color="purple",
            get_system_prompt=lambda: (
                "You are a planning agent. Your job is to analyze requirements and design implementation plans. "
                "Research the codebase to understand the current architecture, then create a detailed plan. "
                "Do not modify any files. Focus on creating clear, actionable implementation steps. "
                "Consider edge cases, error handling, and testing in your plan."
            ),
        )

    @staticmethod
    def get_verification() -> AgentDefinition:
        return AgentDefinition(
            agent_type="verification",
            when_to_use="Use this agent to verify that implementation work is correct, run tests, and check for regressions",
            tools=["Read", "Glob", "Grep", "Bash"],
            disallowed_tools=["Edit", "Write", "Agent", "NotebookEdit"],
            model="inherit",
            background=True,
            max_turns=30,
            color="red",
            get_system_prompt=lambda: (
                "CRITICAL: This is a VERIFICATION-ONLY task. You must NOT modify any project files. "
                "You may only read files and run read-only commands. "
                "Your job is to verify the implementation by: "
                "1. Reading the changed files and checking correctness "
                "2. Running tests if available "
                "3. Checking for common issues (syntax errors, import errors, type mismatches) "
                "Report: PASS / FAIL / PARTIAL with specific details."
            ),
        )

    @staticmethod
    def get_guide() -> AgentDefinition:
        return AgentDefinition(
            agent_type="guide",
            when_to_use="Use this agent when the user asks questions about the IDE, its features, configuration, or how to use specific functionality",
            tools=["Read", "Glob", "Grep", "WebFetch", "WebSearch"],
            model="inherit",
            effort="low",
            permission_mode="dontAsk",
            max_turns=20,
            color="cyan",
            get_system_prompt=lambda: (
                "You are a helpful guide for the Kaguya IDE. Answer questions about features, "
                "configuration, and usage. Be concise and provide examples when helpful. "
                "Search documentation and configuration files to find accurate answers."
            ),
        )

    @classmethod
    def get_all(cls) -> List[AgentDefinition]:
        return [
            cls.get_general_purpose(),
            cls.get_explore(),
            cls.get_plan(),
            cls.get_verification(),
            cls.get_guide(),
        ]


ONE_SHOT_AGENT_TYPES = {"Explore", "Plan"}


class AgentRegistry:
    def __init__(self):
        self._agents: Dict[str, AgentDefinition] = {}
        self._priority_order = [
            "built-in", "plugin", "userSettings",
            "projectSettings", "flagSettings", "managedSettings",
        ]
        self._register_builtins()

    def _register_builtins(self):
        for agent in BuiltInAgents.get_all():
            self._agents[agent.agent_type] = agent

    def register(self, agent: AgentDefinition):
        existing = self._agents.get(agent.agent_type)
        if existing:
            existing_priority = self._priority_order.index(existing.source) \
                if existing.source in self._priority_order else 0
            new_priority = self._priority_order.index(agent.source) \
                if agent.source in self._priority_order else 0
            if new_priority >= existing_priority:
                self._agents[agent.agent_type] = agent
        else:
            self._agents[agent.agent_type] = agent

    def unregister(self, agent_type: str):
        self._agents.pop(agent_type, None)

    def get(self, agent_type: str) -> Optional[AgentDefinition]:
        return self._agents.get(agent_type)

    def list_agents(self) -> List[AgentDefinition]:
        return list(self._agents.values())

    def get_agent_types(self) -> List[str]:
        return list(self._agents.keys())


class ForkSubagentBuilder:
    def __init__(self, parent_context: AgentContext):
        self._parent = parent_context

    def build_fork_messages(self, directive: str) -> List[Dict[str, Any]]:
        assistant_msg = {
            "role": "assistant",
            "content": self._get_parent_assistant_content(),
            "uuid": str(uuid.uuid4()),
        }

        tool_use_blocks = self._extract_tool_use_blocks(assistant_msg["content"])

        tool_result_blocks = []
        for block in tool_use_blocks:
            tool_result_blocks.append({
                "type": "tool_result",
                "tool_use_id": block.get("id", ""),
                "content": [{"type": "text", "text": FORK_PLACEHOLDER_RESULT}],
            })

        child_directive = FORK_BOILERPLATE.format(directive=directive)

        user_msg = {
            "role": "user",
            "content": tool_result_blocks + [{"type": "text", "text": child_directive}],
        }

        history = self._filter_incomplete_tool_calls(self._parent.messages)

        return history + [assistant_msg, user_msg]

    def _get_parent_assistant_content(self) -> List[Dict]:
        content = []
        for msg in reversed(self._parent.messages):
            if msg.get("role") == "assistant":
                msg_content = msg.get("content", "")
                if isinstance(msg_content, list):
                    content = msg_content
                elif isinstance(msg_content, str):
                    content = [{"type": "text", "text": msg_content}]
                break

        if not content:
            content = [{"type": "text", "text": "Processing..."}]

        return content

    def _extract_tool_use_blocks(self, content) -> List[Dict]:
        if isinstance(content, list):
            return [b for b in content if isinstance(b, dict) and b.get("type") == "tool_use"]
        return []

    def _filter_incomplete_tool_calls(self, messages: List[Dict]) -> List[Dict]:
        filtered = []
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, list):
                has_tool_use = any(
                    isinstance(b, dict) and b.get("type") == "tool_use"
                    for b in content
                )
                if has_tool_use:
                    tool_use_ids = {
                        b.get("id") for b in content
                        if isinstance(b, dict) and b.get("type") == "tool_use"
                    }
                    has_all_results = True
                    for uid in tool_use_ids:
                        found = False
                        for m in messages:
                            mc = m.get("content", "")
                            if isinstance(mc, list):
                                for b in mc:
                                    if isinstance(b, dict) and b.get("type") == "tool_result" \
                                       and b.get("tool_use_id") == uid:
                                        found = True
                                        break
                            if found:
                                break
                        if not found:
                            has_all_results = False
                            break
                    if not has_all_results:
                        continue
            filtered.append(msg)
        return filtered

    def build_worktree_notice(self, parent_cwd: str, worktree_cwd: str) -> str:
        return (
            f"You've inherited the conversation context above from a parent agent "
            f"working in {parent_cwd}. You are operating in an isolated git worktree "
            f"at {worktree_cwd}. Paths in the inherited context refer to the parent's "
            f"working directory; translate them to your worktree root. "
            f"Re-read files before editing if the parent may have modified them."
        )


class AgentExecutor:
    def __init__(self, registry: AgentRegistry, llm_adapter=None, permission_manager=None):
        self._registry = registry
        self._llm_adapter = llm_adapter
        self._permission_manager = permission_manager
        self._active_agents: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._hook_manager = None

    def set_hook_manager(self, hook_manager):
        self._hook_manager = hook_manager

    def set_llm_adapter(self, adapter):
        self._llm_adapter = adapter

    def set_permission_manager(self, pm):
        self._permission_manager = pm

    def execute(
        self,
        directive: str,
        agent_type: str = None,
        context: AgentContext = None,
        run_in_background: bool = False,
        force_fork: bool = False,
    ) -> AgentResult:
        if context is None:
            context = AgentContext(
                session_id=str(uuid.uuid4()),
                working_directory=os.getcwd(),
            )

        effective_type = agent_type
        is_fork = force_fork or (effective_type is None and self._should_fork(context))

        if is_fork:
            return self._execute_fork(directive, context)
        elif effective_type:
            return self._execute_named_agent(directive, effective_type, context)
        else:
            return self._execute_named_agent(
                directive, "general-purpose", context
            )

    def _should_fork(self, context: AgentContext) -> bool:
        try:
            from kaguya_feature_flags import feature
            return feature("fork_subagent")
        except ImportError:
            return False

    def _execute_fork(self, directive: str, context: AgentContext) -> AgentResult:
        if self._is_in_fork_child(context):
            return self._execute_named_agent(directive, "general-purpose", context)

        start_time = time.time()
        session_id = str(uuid.uuid4())

        fork_context = AgentContext(
            session_id=session_id,
            working_directory=context.working_directory,
            messages=context.messages,
            available_tools=context.available_tools,
            system_prompt=context.system_prompt,
            rendered_system_prompt=context.rendered_system_prompt,
            permission_mode=context.permission_mode,
            model=context.model,
            thinking_budget=context.thinking_budget,
            parent_session_id=context.session_id,
            is_fork=True,
            content_replacement_state=copy.deepcopy(context.content_replacement_state),
            query_source="agent:builtin:fork",
        )

        builder = ForkSubagentBuilder(context)
        fork_messages = builder.build_fork_messages(directive)

        fork_context.messages = fork_messages

        with self._lock:
            self._active_agents[session_id] = {
                "type": "fork",
                "started_at": datetime.utcnow().isoformat(),
                "directive": directive[:200],
            }

        try:
            result = self._run_agent_loop(fork_context, directive)
            result.agent_type = "fork"
            result.session_id = session_id
            return result
        finally:
            with self._lock:
                self._active_agents.pop(session_id, None)

    def _is_in_fork_child(self, context: AgentContext) -> bool:
        if context.query_source == "agent:builtin:fork":
            return True
        for msg in context.messages:
            content = msg.get("content", "")
            if isinstance(content, str) and "<fork-boilerplate>" in content:
                return True
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        if "<fork-boilerplate>" in block.get("text", ""):
                            return True
        return False

    def _execute_named_agent(
        self, directive: str, agent_type: str, context: AgentContext
    ) -> AgentResult:
        agent_def = self._registry.get(agent_type)
        if not agent_def:
            return AgentResult(
                success=False,
                error=f"Unknown agent type: {agent_type}",
                agent_type=agent_type,
            )

        start_time = time.time()
        session_id = str(uuid.uuid4())

        model = self._resolve_model(agent_def, context)
        system_prompt = self._build_system_prompt(agent_def, context)

        agent_context = AgentContext(
            session_id=session_id,
            working_directory=context.working_directory,
            messages=[{
                "role": "user",
                "content": [{"type": "text", "text": directive}],
            }],
            available_tools=self._resolve_tools(agent_def, context),
            system_prompt=system_prompt,
            rendered_system_prompt=system_prompt,
            permission_mode=agent_def.permission_mode,
            model=model,
            thinking_budget=self._resolve_thinking_budget(agent_def),
            parent_session_id=context.session_id,
        )

        with self._lock:
            self._active_agents[session_id] = {
                "type": agent_type,
                "started_at": datetime.utcnow().isoformat(),
                "directive": directive[:200],
            }

        try:
            result = self._run_agent_loop(agent_context, directive, agent_def)
            result.agent_type = agent_type
            result.session_id = session_id
            return result
        finally:
            with self._lock:
                self._active_agents.pop(session_id, None)

    def _run_agent_loop(
        self,
        context: AgentContext,
        directive: str,
        agent_def: AgentDefinition = None,
    ) -> AgentResult:
        start_time = time.time()
        tool_calls = []
        files_changed = []
        output_parts = []
        total_usage = {"input_tokens": 0, "output_tokens": 0}
        turn_count = 0
        max_turns = agent_def.max_turns if agent_def else 200

        if self._hook_manager:
            try:
                from kaguya_hooks import HookType, HookContext
                hook_ctx = HookContext(
                    hook_type=HookType.SESSION_START,
                    session_id=context.session_id,
                    metadata={"agent_type": agent_def.agent_type if agent_def else "fork"},
                )
                self._hook_manager.execute_hooks(hook_ctx)
            except Exception:
                pass

        while turn_count < max_turns and not context.abort_signal:
            turn_count += 1

            if not self._llm_adapter:
                output_parts.append("No LLM adapter configured - agent cannot execute")
                break

            try:
                response = self._call_llm(context)

                if not response:
                    output_parts.append("LLM returned empty response")
                    break

                content = response.get("content", "")
                stop_reason = response.get("stop_reason", "end_turn")

                if isinstance(content, str) and content:
                    output_parts.append(content)

                usage = response.get("usage", {})
                if usage:
                    total_usage["input_tokens"] += usage.get("input_tokens", 0)
                    total_usage["output_tokens"] += usage.get("output_tokens", 0)

                tool_uses = response.get("tool_uses", [])
                if not tool_uses:
                    break

                tool_results = []
                for tu in tool_uses:
                    tool_name = tu.get("name", "")
                    tool_input = tu.get("input", {})
                    tool_use_id = tu.get("id", str(uuid.uuid4()))

                    tool_calls.append({
                        "id": tool_use_id,
                        "name": tool_name,
                        "input": tool_input,
                    })

                    if tool_name in ("Edit", "Write"):
                        fp = tool_input.get("file_path", tool_input.get("path", ""))
                        if fp and fp not in files_changed:
                            files_changed.append(fp)

                    result = self._execute_tool(tool_name, tool_input, context)

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": result,
                    })

                context.messages.append({
                    "role": "assistant",
                    "content": content if isinstance(content, list) else [
                        {"type": "text", "text": content}
                    ] + [{"type": "tool_use", "id": tu["id"], "name": tu["name"],
                          "input": tu["input"]} for tu in tool_uses],
                })
                context.messages.append({
                    "role": "user",
                    "content": tool_results,
                })

                if stop_reason == "end_turn":
                    break

            except Exception as e:
                output_parts.append(f"Agent error: {str(e)}")
                break

        duration_ms = int((time.time() - start_time) * 1000)

        if self._hook_manager:
            try:
                from kaguya_hooks import HookType, HookContext
                hook_ctx = HookContext(
                    hook_type=HookType.SESSION_END,
                    session_id=context.session_id,
                    metadata={"agent_type": agent_def.agent_type if agent_def else "fork",
                              "turns": turn_count},
                )
                self._hook_manager.execute_hooks(hook_ctx)
            except Exception:
                pass

        return AgentResult(
            success=True,
            output="\n".join(output_parts),
            tool_calls=tool_calls,
            files_changed=files_changed,
            usage=total_usage,
            duration_ms=duration_ms,
        )

    def _call_llm(self, context: AgentContext) -> Optional[Dict]:
        if not self._llm_adapter:
            return {
                "content": "Error: No LLM adapter configured. Please configure an LLM provider (Ollama, DeepSeek, etc.) to enable agent execution.",
                "stop_reason": "end_turn",
                "usage": {},
                "tool_uses": [],
            }

        try:
            messages = []
            for msg in context.messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if isinstance(content, list):
                    text_parts = []
                    for block in content:
                        if isinstance(block, dict):
                            if block.get("type") == "text":
                                text_parts.append(block.get("text", ""))
                            elif block.get("type") == "tool_result":
                                rc = block.get("content", "")
                                if isinstance(rc, str):
                                    text_parts.append(rc)
                                elif isinstance(rc, list):
                                    for rb in rc:
                                        if isinstance(rb, dict) and rb.get("type") == "text":
                                            text_parts.append(rb.get("text", ""))
                    content = "\n".join(text_parts)
                messages.append({"role": role, "content": content})

            return self._llm_adapter.chat(
                messages=messages,
                system_prompt=context.system_prompt,
                model=context.model,
                max_tokens=4096,
                temperature=0.7,
            )
        except Exception as e:
            return {
                "content": f"LLM call error: {str(e)}",
                "stop_reason": "end_turn",
                "usage": {},
                "tool_uses": [],
            }

    def _execute_tool(self, tool_name: str, tool_input: Dict,
                      context: AgentContext) -> Any:
        if self._permission_manager:
            try:
                from kaguya_permissions import PermissionDecision
                decision = self._permission_manager.request_permission(
                    session_id=context.session_id,
                    tool_name=tool_name,
                    tool_input=tool_input,
                    timeout=10.0,
                )
                if decision in (PermissionDecision.REJECT, PermissionDecision.REJECT_ALWAYS):
                    return f"Permission denied: {tool_name} - operation blocked by permission system"
            except ImportError:
                pass
            except Exception as e:
                pass

        if self._hook_manager:
            try:
                from kaguya_hooks import HookType, HookContext
                hook_ctx = HookContext(
                    hook_type=HookType.PRE_TOOL_USE,
                    tool_name=tool_name,
                    tool_args=tool_input,
                    session_id=context.session_id,
                )
                proceed, msg = self._hook_manager.should_proceed(hook_ctx)
                if not proceed:
                    return f"Tool blocked: {msg}"
            except Exception:
                pass

        try:
            if tool_name in ("Read", "Glob", "Grep"):
                return self._execute_read_tool(tool_name, tool_input, context)
            elif tool_name in ("Edit", "Write"):
                return self._execute_write_tool(tool_name, tool_input, context)
            elif tool_name == "Bash":
                return self._execute_bash_tool(tool_input, context)
            elif tool_name in ("WebFetch", "WebSearch"):
                return self._execute_web_tool(tool_name, tool_input, context)
            else:
                return f"Unknown tool: {tool_name}"
        except Exception as e:
            return f"Tool error: {str(e)}"

    def _execute_read_tool(self, name: str, args: Dict, ctx: AgentContext) -> str:
        try:
            from kaguya_file_operations import SafeFileOperations
            fo = SafeFileOperations()
            if name == "Read":
                path = args.get("file_path", args.get("path", ""))
                limit = args.get("limit", 200)
                offset = args.get("offset", 1)
                content, err = fo.read_file(path, limit=limit, offset=offset)
                return content if content else f"Error: {err}"
            elif name == "Glob":
                import glob as g
                pattern = args.get("pattern", args.get("glob", "*"))
                cwd = args.get("path", ctx.working_directory)
                matches = g.glob(os.path.join(cwd, pattern), recursive=True)
                return "\n".join(matches[:100])
            elif name == "Grep":
                import subprocess
                pattern = args.get("pattern", "")
                path = args.get("path", ctx.working_directory)
                result = subprocess.run(
                    ["grep", "-rn", pattern, path],
                    capture_output=True, text=True, timeout=30,
                )
                return result.stdout[:5000] if result.stdout else "No matches found"
        except ImportError:
            path = args.get("file_path", args.get("path", ""))
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    return f.read(5000)
            return f"File not found: {path}"
        except Exception as e:
            return f"Read error: {e}"

    def _execute_write_tool(self, name: str, args: Dict, ctx: AgentContext) -> str:
        path = args.get("file_path", args.get("path", ""))
        if not path:
            return "No file path specified"

        try:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

            if name == "Write":
                content = args.get("content", "")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                return f"Successfully wrote to {path}"

            elif name == "Edit":
                old_str = args.get("old_string", args.get("old_str", ""))
                new_str = args.get("new_string", args.get("new_str", ""))
                if not os.path.exists(path):
                    return f"File not found: {path}"

                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()

                if old_str not in content:
                    return f"Old string not found in {path}"

                new_content = content.replace(old_str, new_str, 1)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                return f"Successfully edited {path}"
        except Exception as e:
            return f"Write error: {e}"

    def _execute_bash_tool(self, args: Dict, ctx: AgentContext) -> str:
        command = args.get("command", "")
        if not command:
            return "No command specified"

        try:
            import subprocess
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=ctx.working_directory,
            )
            output = result.stdout
            if result.stderr:
                output += f"\nSTDERR:\n{result.stderr}"
            return output[:10000]
        except subprocess.TimeoutExpired:
            return "Command timed out (60s)"
        except Exception as e:
            return f"Bash error: {e}"

    def _execute_web_tool(self, name: str, args: Dict, ctx: AgentContext) -> str:
        try:
            import urllib.request
            if name == "WebFetch":
                url = args.get("url", "")
                if not url:
                    return "No URL specified"
                req = urllib.request.Request(url, headers={"User-Agent": "KaguyaIDE/3.0"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    return resp.read(50000).decode("utf-8", errors="replace")
            elif name == "WebSearch":
                query = args.get("query", "")
                return f"Web search for '{query}' - requires search API configuration"
        except Exception as e:
            return f"Web tool error: {e}"

    def _resolve_model(self, agent_def: AgentDefinition, context: AgentContext) -> str:
        model = agent_def.model
        if model == "inherit" and context.model:
            return context.model
        if model and model != "inherit":
            return model
        return context.model or "qwen3"

    def _resolve_tools(self, agent_def: AgentDefinition, context: AgentContext) -> List[str]:
        if "*" in (agent_def.tools or []):
            all_tools = list(context.available_tools) if context.available_tools else [
                "Read", "Edit", "Write", "Bash", "Glob", "Grep",
                "WebFetch", "WebSearch", "Agent",
            ]
            for dt in agent_def.disallowed_tools:
                if dt in all_tools:
                    all_tools.remove(dt)
            return all_tools
        return agent_def.tools or []

    def _resolve_thinking_budget(self, agent_def: AgentDefinition) -> int:
        effort_map = {"low": 3000, "medium": 10000, "high": 30000, "max": 60000}
        return effort_map.get(agent_def.effort, 10000)

    def _build_system_prompt(self, agent_def: AgentDefinition, context: AgentContext) -> str:
        parts = []

        if agent_def.get_system_prompt:
            try:
                parts.append(agent_def.get_system_prompt())
            except Exception:
                pass

        if agent_def.tools:
            parts.append(f"\nAvailable tools: {', '.join(agent_def.tools)}")

        if agent_def.permission_mode:
            parts.append(f"Permission mode: {agent_def.permission_mode}")

        if context.working_directory:
            parts.append(f"Working directory: {context.working_directory}")

        return "\n".join(parts)

    def get_active_agents(self) -> Dict[str, Dict]:
        with self._lock:
            return dict(self._active_agents)

    def cancel_agent(self, session_id: str) -> bool:
        with self._lock:
            if session_id in self._active_agents:
                self._active_agents[session_id]["cancelled"] = True
                return True
        return False


class AgentAsyncRunner:
    def __init__(self, executor: AgentExecutor):
        self._executor = executor
        self._results: Dict[str, AgentResult] = {}
        self._lock = threading.Lock()

    def run_async(
        self,
        directive: str,
        agent_type: str = None,
        context: AgentContext = None,
        on_complete: Callable = None,
    ) -> str:
        task_id = str(uuid.uuid4())

        def _run():
            result = self._executor.execute(directive, agent_type, context)
            with self._lock:
                self._results[task_id] = result
            if on_complete:
                try:
                    on_complete(task_id, result)
                except Exception:
                    pass

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

        return task_id

    def get_result(self, task_id: str) -> Optional[AgentResult]:
        with self._lock:
            return self._results.get(task_id)

    def list_results(self) -> Dict[str, Dict]:
        with self._lock:
            return {tid: {"success": r.success, "agent_type": r.agent_type,
                          "duration_ms": r.duration_ms}
                    for tid, r in self._results.items()}


def create_agent_system(llm_adapter=None, hook_manager=None, permission_manager=None) -> Tuple[AgentRegistry, AgentExecutor, AgentAsyncRunner]:
    registry = AgentRegistry()
    executor = AgentExecutor(registry, llm_adapter, permission_manager)
    if hook_manager:
        executor.set_hook_manager(hook_manager)
    if permission_manager:
        executor.set_permission_manager(permission_manager)
    async_runner = AgentAsyncRunner(executor)
    return registry, executor, async_runner
