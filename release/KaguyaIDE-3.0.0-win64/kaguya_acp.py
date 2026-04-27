#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辉夜IDE ACP协议适配器
参考 Claude Code 的 src/services/acp/ 架构
实现 Agent Client Protocol，支持IDE集成通信

ACP协议使用NDJSON(Newline-Delimited JSON)通过stdin/stdout传输，
支持IDE与Agent之间的双向通信，包括会话管理、消息传递、权限请求等。
"""

import json
import sys
import os
import uuid
import threading
import time
import traceback
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, List, Optional, Tuple, AsyncIterator
from enum import Enum
from datetime import datetime
from collections import OrderedDict
import queue


class AcpMessageType(Enum):
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"


class SessionUpdateType(Enum):
    AGENT_MESSAGE_CHUNK = "agent_message_chunk"
    AGENT_THOUGHT_CHUNK = "agent_thought_chunk"
    USER_MESSAGE_CHUNK = "user_message_chunk"
    TOOL_CALL = "tool_call"
    TOOL_CALL_UPDATE = "tool_call_update"
    USAGE_UPDATE = "usage_update"
    PLAN = "plan"
    AVAILABLE_COMMANDS_UPDATE = "available_commands_update"
    CURRENT_MODE_UPDATE = "current_mode_update"
    CONFIG_OPTION_UPDATE = "config_option_update"


class ToolKind(Enum):
    READ = "read"
    EDIT = "edit"
    EXECUTE = "execute"
    SEARCH = "search"
    FETCH = "fetch"
    THINK = "think"
    SWITCH_MODE = "switch_mode"


class PermissionOptionKind(Enum):
    ALLOW_ALWAYS = "allow_always"
    ALLOW_ONCE = "allow_once"
    REJECT_ONCE = "reject_once"


@dataclass
class ContentBlock:
    type: str
    text: str = ""
    data: str = ""
    mime_type: str = ""
    name: str = ""
    uri: str = ""


@dataclass
class PermissionOption:
    kind: PermissionOptionKind
    name: str
    option_id: str


@dataclass
class ToolCallInfo:
    tool_call_id: str
    title: str
    kind: ToolKind
    status: str = "pending"
    raw_input: str = ""
    raw_output: str = ""
    content: Optional[List[Dict]] = None
    locations: Optional[List[Dict]] = None


@dataclass
class PlanEntry:
    id: str
    content: str
    status: str = "pending"
    priority: str = "medium"


@dataclass
class UsageInfo:
    used: int = 0
    size: int = 0
    cost: Optional[Dict[str, Any]] = None


@dataclass
class SessionMode:
    id: str
    name: str
    description: str = ""


@dataclass
class SessionModel:
    id: str
    name: str
    description: str = ""


@dataclass
class ConfigOption:
    id: str
    name: str
    value: Any = None
    type: str = "string"
    description: str = ""


@dataclass
class CommandInfo:
    name: str
    description: str
    input_hint: str = ""


@dataclass
class AcpSession:
    session_id: str
    cwd: str
    cancelled: bool = False
    prompt_running: bool = False
    pending_messages: OrderedDict = field(default_factory=OrderedDict)
    next_pending_order: int = 0
    tool_use_cache: Dict[str, Any] = field(default_factory=dict)
    client_capabilities: Dict[str, Any] = field(default_factory=dict)
    modes: List[SessionMode] = field(default_factory=list)
    models: List[SessionModel] = field(default_factory=list)
    config_options: List[ConfigOption] = field(default_factory=list)
    current_mode: str = "default"
    current_model: str = ""
    fingerprint: str = ""
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    messages: List[Dict[str, Any]] = field(default_factory=list)
    usage: UsageInfo = field(default_factory=UsageInfo)


TOOL_KIND_MAP = {
    "Read": ToolKind.READ,
    "Edit": ToolKind.EDIT,
    "Write": ToolKind.EDIT,
    "Bash": ToolKind.EXECUTE,
    "Terminal": ToolKind.EXECUTE,
    "Glob": ToolKind.SEARCH,
    "Grep": ToolKind.SEARCH,
    "WebFetch": ToolKind.FETCH,
    "WebSearch": ToolKind.FETCH,
    "Agent": ToolKind.THINK,
    "Task": ToolKind.THINK,
    "Skill": ToolKind.THINK,
    "TodoWrite": ToolKind.THINK,
    "ExitPlanMode": ToolKind.SWITCH_MODE,
}


class NDJSONStream:
    _flask_mode = False
    _message_buffer: List[Dict[str, Any]] = []

    def __init__(self, input_stream=None, output_stream=None):
        self._input = input_stream or sys.stdin
        self._output = output_stream or (sys.stderr if NDJSONStream._flask_mode else sys.stdout)
        self._lock = threading.Lock()
        self._buffer = ""
        self._closed = False

    @classmethod
    def enable_flask_mode(cls):
        cls._flask_mode = True
        cls._message_buffer = []

    @classmethod
    def disable_flask_mode(cls):
        cls._flask_mode = False
        cls._message_buffer = []

    def write(self, obj: Dict[str, Any]) -> None:
        if self._closed:
            return
        with self._lock:
            try:
                line = json.dumps(obj, ensure_ascii=False, separators=(',', ':'))
                if NDJSONStream._flask_mode:
                    NDJSONStream._message_buffer.append(obj)
                else:
                    self._output.write(line + '\n')
                    self._output.flush()
            except Exception:
                pass

    def read(self) -> Optional[Dict[str, Any]]:
        try:
            line = self._input.readline()
            if not line:
                return None
            line = line.strip()
            if not line:
                return None
            return json.loads(line)
        except json.JSONDecodeError:
            return None
        except Exception:
            return None

    def read_iter(self):
        while True:
            msg = self.read()
            if msg is None:
                break
            yield msg

    def close(self):
        self._closed = True


class AcpMessageBus:
    def __init__(self, stream: NDJSONStream):
        self._stream = stream
        self._pending_requests: Dict[str, queue.Queue] = {}
        self._request_handlers: Dict[str, Callable] = {}
        self._notification_handlers: Dict[str, List[Callable]] = {}
        self._running = False
        self._reader_thread: Optional[threading.Thread] = None

    def register_handler(self, method: str, handler: Callable):
        self._request_handlers[method] = handler

    def register_notification_handler(self, method: str, handler: Callable):
        if method not in self._notification_handlers:
            self._notification_handlers[method] = []
        self._notification_handlers[method].append(handler)

    def send_request(self, method: str, params: Dict[str, Any] = None,
                     timeout: float = 30.0) -> Optional[Dict[str, Any]]:
        request_id = str(uuid.uuid4())
        msg = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {},
        }

        q = queue.Queue()
        self._pending_requests[request_id] = q

        self._stream.write(msg)

        try:
            return q.get(timeout=timeout)
        except queue.Empty:
            return None
        finally:
            self._pending_requests.pop(request_id, None)

    def send_response(self, request_id: str, result: Any = None,
                      error: Dict = None) -> None:
        msg = {"jsonrpc": "2.0", "id": request_id}
        if error:
            msg["error"] = error
        else:
            msg["result"] = result
        self._stream.write(msg)

    def send_notification(self, method: str, params: Dict[str, Any] = None) -> None:
        msg = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
        }
        self._stream.write(msg)

    def _dispatch_message(self, msg: Dict[str, Any]):
        if "id" in msg and "method" in msg:
            request_id = msg["id"]
            method = msg["method"]
            params = msg.get("params", {})

            handler = self._request_handlers.get(method)
            if handler:
                try:
                    result = handler(params)
                    self.send_response(request_id, result=result)
                except Exception as e:
                    self.send_response(request_id, error={
                        "code": -32603,
                        "message": str(e),
                    })
            else:
                self.send_response(request_id, error={
                    "code": -32601,
                    "message": f"Method not found: {method}",
                })

        elif "id" in msg and ("result" in msg or "error" in msg):
            request_id = msg["id"]
            q = self._pending_requests.get(request_id)
            if q:
                q.put(msg)

        elif "method" in msg:
            method = msg["method"]
            params = msg.get("params", {})
            handlers = self._notification_handlers.get(method, [])
            for handler in handlers:
                try:
                    handler(params)
                except Exception:
                    pass

    def start(self):
        self._running = True
        self._reader_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._reader_thread.start()

    def _read_loop(self):
        for msg in self._stream.read_iter():
            if not self._running:
                break
            try:
                self._dispatch_message(msg)
            except Exception:
                pass

    def stop(self):
        self._running = False


class AcpAgent:
    PROTOCOL_VERSION = 1
    AGENT_NAME = "kaguya-ide"
    AGENT_TITLE = "Kaguya IDE"

    def __init__(self, bus: AcpMessageBus, query_engine_factory: Callable = None):
        self._bus = bus
        self._sessions: Dict[str, AcpSession] = {}
        self._query_engine_factory = query_engine_factory
        self._query_engines: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self._agent_version = "3.0.0"

        self._register_handlers()

    def _register_handlers(self):
        if self._bus is None:
            return
        self._bus.register_handler("initialize", self._handle_initialize)
        self._bus.register_handler("authenticate", self._handle_authenticate)
        self._bus.register_handler("newSession", self._handle_new_session)
        self._bus.register_handler("resumeSession", self._handle_resume_session)
        self._bus.register_handler("loadSession", self._handle_load_session)
        self._bus.register_handler("listSessions", self._handle_list_sessions)
        self._bus.register_handler("forkSession", self._handle_fork_session)
        self._bus.register_handler("closeSession", self._handle_close_session)
        self._bus.register_handler("prompt", self._handle_prompt)
        self._bus.register_handler("cancel", self._handle_cancel)
        self._bus.register_handler("setSessionMode", self._handle_set_mode)
        self._bus.register_handler("setSessionModel", self._handle_set_model)
        self._bus.register_handler("setSessionConfigOption", self._handle_set_config)

    def _handle_initialize(self, params: Dict) -> Dict:
        client_caps = params.get("clientCapabilities", {})
        return {
            "protocolVersion": self.PROTOCOL_VERSION,
            "agentInfo": {
                "name": self.AGENT_NAME,
                "title": self.AGENT_TITLE,
                "version": self._agent_version,
            },
            "agentCapabilities": {
                "_meta": {
                    "kaguyaIde": {
                        "promptQueueing": True,
                    }
                },
                "promptCapabilities": {
                    "image": True,
                    "embeddedContext": True,
                },
                "mcpCapabilities": {
                    "http": True,
                    "sse": True,
                },
                "loadSession": True,
                "sessionCapabilities": {
                    "fork": {},
                    "list": {},
                    "resume": {},
                    "close": {},
                },
            },
        }

    def _handle_authenticate(self, params: Dict) -> Dict:
        return {}

    def _handle_new_session(self, params: Dict) -> Dict:
        session_id = str(uuid.uuid4())
        cwd = params.get("cwd", os.getcwd())
        mcp_servers = params.get("mcpServers", [])
        meta = params.get("_meta", {})

        session = AcpSession(
            session_id=session_id,
            cwd=cwd,
            client_capabilities=meta,
            fingerprint=self._compute_fingerprint(cwd, mcp_servers),
        )

        session.modes = self._get_available_modes()
        session.models = self._get_available_models()
        session.config_options = self._get_config_options()

        if self._query_engine_factory:
            self._query_engines[session_id] = self._query_engine_factory(session)

        with self._lock:
            self._sessions[session_id] = session

        self._send_commands_update(session_id)

        return {
            "sessionId": session_id,
            "modes": [asdict(m) for m in session.modes],
            "models": [asdict(m) for m in session.models],
            "configOptions": [asdict(c) for c in session.config_options],
        }

    def _handle_resume_session(self, params: Dict) -> Dict:
        session_id = params.get("sessionId", "")
        with self._lock:
            session = self._sessions.get(session_id)

        if not session:
            return {"error": {"code": -32001, "message": "Session not found"}}

        new_cwd = params.get("cwd", session.cwd)
        new_mcp = params.get("mcpServers", [])

        new_fp = self._compute_fingerprint(new_cwd, new_mcp)
        if new_fp != session.fingerprint:
            with self._lock:
                del self._sessions[session_id]
            return self._handle_new_session({"cwd": new_cwd, "mcpServers": new_mcp})

        session.prompt_running = False
        session.cancelled = False

        for msg in session.messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        self._send_session_update(session_id, {
                            "sessionUpdate": "user_message_chunk" if role == "user" else "agent_message_chunk",
                            "content": {"type": "text", "text": block.get("text", "")},
                        })
            elif isinstance(content, str):
                self._send_session_update(session_id, {
                    "sessionUpdate": "user_message_chunk" if role == "user" else "agent_message_chunk",
                    "content": {"type": "text", "text": content},
                })

        return {
            "sessionId": session_id,
            "modes": [asdict(m) for m in session.modes],
            "models": [asdict(m) for m in session.models],
            "configOptions": [asdict(c) for c in session.config_options],
        }

    def _handle_load_session(self, params: Dict) -> Dict:
        return self._handle_resume_session(params)

    def _handle_list_sessions(self, params: Dict) -> Dict:
        with self._lock:
            sessions = []
            for sid, session in self._sessions.items():
                sessions.append({
                    "sessionId": sid,
                    "cwd": session.cwd,
                    "createdAt": session.created_at,
                    "messageCount": len(session.messages),
                })
        return {"sessions": sessions}

    def _handle_fork_session(self, params: Dict) -> Dict:
        parent_id = params.get("sessionId", "")
        with self._lock:
            parent = self._sessions.get(parent_id)

        if not parent:
            return {"error": {"code": -32001, "message": "Parent session not found"}}

        return self._handle_new_session({"cwd": parent.cwd})

    def _handle_close_session(self, params: Dict) -> Dict:
        session_id = params.get("sessionId", "")
        with self._lock:
            session = self._sessions.pop(session_id, None)
            self._query_engines.pop(session_id, None)

        if session:
            session.cancelled = True
            for order, (q, _) in session.pending_messages.items():
                q.put({"cancelled": True})
            session.pending_messages.clear()

        return {}

    def _handle_prompt(self, params: Dict) -> Dict:
        session_id = params.get("sessionId", "")
        prompt_blocks = params.get("prompt", [])

        with self._lock:
            session = self._sessions.get(session_id)

        if not session:
            return {"error": {"code": -32001, "message": "Session not found"}}

        if session.cancelled:
            return {"stopReason": "cancelled"}

        if session.prompt_running:
            q = queue.Queue()
            order = session.next_pending_order
            session.next_pending_order += 1
            session.pending_messages[order] = (q, params)
            try:
                result = q.get(timeout=300)
                if isinstance(result, dict) and result.get("cancelled"):
                    return {"stopReason": "cancelled"}
                return result
            except queue.Empty:
                return {"stopReason": "timeout"}

        session.prompt_running = True

        try:
            prompt_text = self._extract_prompt_text(prompt_blocks)
            session.messages.append({
                "role": "user",
                "content": prompt_blocks,
                "timestamp": datetime.utcnow().isoformat(),
            })

            stop_reason = "end_turn"
            usage_data = None

            if self._query_engines.get(session_id):
                engine = self._query_engines[session_id]
                for event in engine.process(prompt_text, session):
                    if session.cancelled:
                        stop_reason = "cancelled"
                        break

                    event_type = event.get("type", "")
                    if event_type == "text":
                        self._send_session_update(session_id, {
                            "sessionUpdate": "agent_message_chunk",
                            "content": {"type": "text", "text": event.get("text", "")},
                        })
                    elif event_type == "thinking":
                        self._send_session_update(session_id, {
                            "sessionUpdate": "agent_thought_chunk",
                            "content": {"type": "text", "text": event.get("text", "")},
                        })
                    elif event_type == "tool_call":
                        self._send_session_update(session_id, {
                            "sessionUpdate": "tool_call",
                            "toolCallId": event.get("tool_call_id", ""),
                            "title": event.get("title", ""),
                            "kind": event.get("kind", "think"),
                            "status": "pending",
                            "rawInput": event.get("raw_input", ""),
                        })
                    elif event_type == "tool_result":
                        self._send_session_update(session_id, {
                            "sessionUpdate": "tool_call_update",
                            "toolCallId": event.get("tool_call_id", ""),
                            "status": event.get("status", "completed"),
                            "rawOutput": event.get("raw_output", ""),
                            "content": event.get("content"),
                            "locations": event.get("locations"),
                        })
                    elif event_type == "usage":
                        self._send_session_update(session_id, {
                            "sessionUpdate": "usage_update",
                            "used": event.get("used", 0),
                            "size": event.get("size", 0),
                            "cost": event.get("cost"),
                        })
                    elif event_type == "done":
                        stop_reason = event.get("stop_reason", "end_turn")
                        usage_data = event.get("usage")

            result = {"stopReason": stop_reason}
            if usage_data:
                result["usage"] = usage_data
            return result

        except Exception as e:
            return {"stopReason": "error", "error": str(e)}
        finally:
            session.prompt_running = False

            if session.pending_messages:
                next_order = min(session.pending_messages.keys())
                q, next_params = session.pending_messages.pop(next_order)
                q.put(self._handle_prompt(next_params))

    def _handle_cancel(self, params: Dict) -> Dict:
        session_id = params.get("sessionId", "")
        with self._lock:
            session = self._sessions.get(session_id)

        if session:
            session.cancelled = True
            for order, (q, _) in list(session.pending_messages.items()):
                q.put({"cancelled": True})
            session.pending_messages.clear()
            session.next_pending_order = 0

        return {}

    def _handle_set_mode(self, params: Dict) -> Dict:
        session_id = params.get("sessionId", "")
        mode_id = params.get("modeId", "default")

        with self._lock:
            session = self._sessions.get(session_id)

        if session:
            session.current_mode = mode_id
            self._send_session_update(session_id, {
                "sessionUpdate": "current_mode_update",
                "currentModeId": mode_id,
            })

        return {}

    def _handle_set_model(self, params: Dict) -> Dict:
        session_id = params.get("sessionId", "")
        model_id = params.get("modelId", "")

        with self._lock:
            session = self._sessions.get(session_id)

        if session:
            session.current_model = model_id

        return {}

    def _handle_set_config(self, params: Dict) -> Dict:
        session_id = params.get("sessionId", "")
        option_id = params.get("optionId", "")
        value = params.get("value")

        with self._lock:
            session = self._sessions.get(session_id)

        if session:
            for opt in session.config_options:
                if opt.id == option_id:
                    opt.value = value
                    break

            self._send_session_update(session_id, {
                "sessionUpdate": "config_option_update",
                "configOptions": [asdict(c) for c in session.config_options],
            })

        return {}

    def _extract_prompt_text(self, blocks: List[Dict]) -> str:
        texts = []
        for block in blocks:
            if isinstance(block, dict):
                btype = block.get("type", "")
                if btype == "text":
                    texts.append(block.get("text", ""))
                elif btype == "resource":
                    res = block.get("resource", {})
                    if isinstance(res, dict):
                        texts.append(res.get("text", ""))
            elif isinstance(block, str):
                texts.append(block)
        return "\n".join(texts)

    def _compute_fingerprint(self, cwd: str, mcp_servers: List) -> str:
        import hashlib
        data = json.dumps({"cwd": cwd, "mcp": sorted([str(s) for s in mcp_servers])},
                          sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def _get_available_modes(self) -> List[SessionMode]:
        return [
            SessionMode(id="auto", name="Auto", description="Automatically approve safe operations"),
            SessionMode(id="default", name="Default", description="Ask for permission on risky operations"),
            SessionMode(id="acceptEdits", name="Accept Edits", description="Auto-accept file edits"),
            SessionMode(id="plan", name="Plan", description="Plan mode - read only"),
            SessionMode(id="dontAsk", name="Don't Ask", description="Never ask for permission"),
        ]

    def _get_available_models(self) -> List[SessionModel]:
        return [
            SessionModel(id="qwen3", name="Qwen3", description="Qwen3 default model"),
            SessionModel(id="deepseek", name="DeepSeek", description="DeepSeek V3/R1"),
            SessionModel(id="ollama", name="Ollama", description="Local Ollama models"),
        ]

    def _get_config_options(self) -> List[ConfigOption]:
        return [
            ConfigOption(id="thinking_budget", name="Thinking Budget", value=10000,
                         type="number", description="Token budget for thinking"),
            ConfigOption(id="max_turns", name="Max Turns", value=200,
                         type="number", description="Maximum agentic turns"),
            ConfigOption(id="auto_compact", name="Auto Compact", value=True,
                         type="boolean", description="Auto-compact conversation"),
        ]

    def _send_session_update(self, session_id: str, update: Dict):
        if self._bus is not None:
            self._bus.send_notification("sessionUpdate", {
                "sessionId": session_id,
                **update,
            })

    def _send_commands_update(self, session_id: str):
        commands = [
            CommandInfo(name="help", description="Show available commands"),
            CommandInfo(name="compact", description="Compact conversation history"),
            CommandInfo(name="clear", description="Clear conversation"),
            CommandInfo(name="mode", description="Change permission mode", input_hint="[mode]"),
            CommandInfo(name="model", description="Switch model", input_hint="[model]"),
        ]
        self._send_session_update(session_id, {
            "sessionUpdate": "available_commands_update",
            "availableCommands": [asdict(c) for c in commands],
        })

    def request_permission(self, session_id: str, tool_call: Dict,
                           options: List[PermissionOption] = None) -> Dict:
        if options is None:
            options = [
                PermissionOption(PermissionOptionKind.ALLOW_ALWAYS, "Always Allow", "allow_always"),
                PermissionOption(PermissionOptionKind.ALLOW_ONCE, "Allow", "allow"),
                PermissionOption(PermissionOptionKind.REJECT_ONCE, "Reject", "reject"),
            ]

        if self._bus is None:
            return {"decision": "allow_always"}

        response = self._bus.send_request("requestPermission", {
            "sessionId": session_id,
            "toolCall": tool_call,
            "options": [{"kind": o.kind.value, "name": o.name, "optionId": o.option_id}
                        for o in options],
        }, timeout=120.0)

        if response and "result" in response:
            return response["result"]
        return {"decision": "reject"}


class AcpBridge:
    def __init__(self, agent: AcpAgent):
        self._agent = agent

    def convert_tool_info(self, tool_name: str, tool_input: Dict) -> Dict:
        kind = TOOL_KIND_MAP.get(tool_name, ToolKind.THINK)
        title = self._generate_tool_title(tool_name, tool_input)
        raw_input = json.dumps(tool_input, ensure_ascii=False)

        locations = []
        if kind in (ToolKind.READ, ToolKind.EDIT):
            path = tool_input.get("file_path", tool_input.get("path", ""))
            if path:
                start_line = tool_input.get("offset", tool_input.get("line", 0))
                end_line = start_line + tool_input.get("limit", 0)
                locations.append({
                    "path": path,
                    "startLine": start_line,
                    "endLine": end_line if end_line > start_line else None,
                })

        return {
            "toolCallId": str(uuid.uuid4()),
            "title": title,
            "kind": kind.value,
            "rawInput": raw_input,
            "locations": locations if locations else None,
        }

    def convert_tool_result(self, tool_call_id: str, result: Any,
                            tool_name: str = "") -> Dict:
        status = "completed"
        raw_output = ""
        content = None

        if isinstance(result, dict):
            if result.get("error"):
                status = "error"
                raw_output = result["error"]
            else:
                raw_output = json.dumps(result.get("data", result),
                                        ensure_ascii=False)[:2000]
        elif isinstance(result, str):
            raw_output = result[:2000]
        elif isinstance(result, Exception):
            status = "error"
            raw_output = str(result)

        if tool_name in ("Edit", "Write"):
            content = [{
                "type": "diff",
                "path": "",
                "oldText": "",
                "newText": raw_output,
            }]

        update = {
            "sessionUpdate": "tool_call_update",
            "toolCallId": tool_call_id,
            "status": status,
            "rawOutput": raw_output,
        }
        if content:
            update["content"] = content
        return update

    def _generate_tool_title(self, tool_name: str, tool_input: Dict) -> str:
        path = tool_input.get("file_path", tool_input.get("path", ""))
        cmd = tool_input.get("command", "")
        pattern = tool_input.get("pattern", tool_input.get("glob", ""))

        if tool_name == "Read" and path:
            return f"Read {os.path.basename(path)}"
        elif tool_name == "Edit" and path:
            return f"Edit {os.path.basename(path)}"
        elif tool_name == "Write" and path:
            return f"Write {os.path.basename(path)}"
        elif tool_name == "Bash" and cmd:
            return f"Run: {cmd[:60]}"
        elif tool_name == "Grep" and pattern:
            return f"Search: {pattern}"
        elif tool_name == "Glob" and pattern:
            return f"Find: {pattern}"
        elif tool_name == "WebFetch":
            return f"Fetch: {tool_input.get('url', '')[:60]}"
        elif tool_name == "WebSearch":
            return f"Search: {tool_input.get('query', '')[:60]}"
        else:
            return f"{tool_name}"


class AcpHttpBridge:
    def __init__(self, agent: AcpAgent):
        self._agent = agent
        self._sessions: Dict[str, AcpSession] = {}
        self._lock = threading.Lock()

    def handle_initialize(self) -> Dict:
        return self._agent._handle_initialize({})

    def handle_new_session(self, params: Dict) -> Dict:
        return self._agent._handle_new_session(params)

    def handle_prompt(self, session_id: str, prompt: List[Dict],
                      on_update: Callable = None) -> Dict:
        with self._lock:
            session = self._agent._sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}

        session.prompt_running = True
        try:
            prompt_text = self._agent._extract_prompt_text(prompt)
            session.messages.append({
                "role": "user",
                "content": prompt,
                "timestamp": datetime.utcnow().isoformat(),
            })

            stop_reason = "end_turn"

            if self._agent._query_engines.get(session_id):
                engine = self._agent._query_engines[session_id]
                for event in engine.process(prompt_text, session):
                    if session.cancelled:
                        stop_reason = "cancelled"
                        break
                    if on_update:
                        on_update(session_id, event)

            return {"stopReason": stop_reason}
        except Exception as e:
            return {"stopReason": "error", "error": str(e)}
        finally:
            session.prompt_running = False

    def handle_cancel(self, session_id: str) -> Dict:
        return self._agent._handle_cancel({"sessionId": session_id})

    def handle_close_session(self, session_id: str) -> Dict:
        return self._agent._handle_close_session({"sessionId": session_id})

    def handle_set_mode(self, session_id: str, mode_id: str) -> Dict:
        return self._agent._handle_set_mode({
            "sessionId": session_id, "modeId": mode_id
        })

    def handle_set_model(self, session_id: str, model_id: str) -> Dict:
        return self._agent._handle_set_model({
            "sessionId": session_id, "modelId": model_id
        })

    def handle_list_sessions(self) -> Dict:
        return self._agent._handle_list_sessions({})

    def handle_resume_session(self, session_id: str) -> Dict:
        return self._agent._handle_resume_session({"sessionId": session_id})


def create_acp_agent(query_engine_factory: Callable = None) -> AcpAgent:
    stream = NDJSONStream()
    bus = AcpMessageBus(stream)
    agent = AcpAgent(bus, query_engine_factory)
    return agent


def create_acp_http_bridge(query_engine_factory: Callable = None) -> AcpHttpBridge:
    NDJSONStream.enable_flask_mode()
    agent = create_acp_agent(query_engine_factory)
    return AcpHttpBridge(agent)


def run_acp_agent(query_engine_factory: Callable = None):
    original_stdout = sys.stdout
    original_stderr = sys.stderr

    try:
        sys.stdout = sys.stderr

        stream = NDJSONStream(input_stream=sys.stdin, output_stream=original_stdout)
        bus = AcpMessageBus(stream)
        agent = AcpAgent(bus, query_engine_factory)
        bus.start()

        import signal
        stop_event = threading.Event()

        def signal_handler(signum, frame):
            stop_event.set()

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        stop_event.wait()

    except Exception as e:
        original_stderr.write(f"ACP agent error: {e}\n")
        original_stderr.write(traceback.format_exc())
    finally:
        sys.stdout = original_stdout
        sys.stderr = original_stderr
