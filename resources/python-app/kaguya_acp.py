#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辉夜IDE ACP协议适配器 v2.0
参考 Claude Code 的 src/services/acp/ 架构

增强功能：
1. 连接管理：建立、认证、心跳、重连、关闭
2. 会话生命周期：创建→活跃→空闲→超时→关闭
3. 会话指纹检测：参数变化时自动重建QueryEngine
4. AbortController传播链：级联取消工具调用
5. 提示队列：同一会话prompt自动排队
6. 权限桥接：ACP requestPermission → 权限决策管道
7. 消息桥接：SDKMessage → ACP SessionUpdate
8. 超时处理：连接超时、会话超时、prompt超时
"""

import json
import sys
import os
import uuid
import hashlib
import threading
import time
import traceback
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, List, Optional, Tuple
from enum import Enum
from datetime import datetime, timedelta
from collections import OrderedDict
import queue


class ConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    AUTHENTICATING = "authenticating"
    CONNECTED = "connected"
    CLOSING = "closing"
    CLOSED = "closed"


class SessionState(Enum):
    CREATING = "creating"
    ACTIVE = "active"
    IDLE = "idle"
    TIMED_OUT = "timed_out"
    CLOSING = "closing"
    CLOSED = "closed"


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
class AbortController:
    _aborted: bool = field(default=False, repr=False)
    _event: threading.Event = field(default_factory=threading.Event, repr=False)

    def abort(self):
        self._aborted = True
        self._event.set()

    @property
    def aborted(self) -> bool:
        return self._aborted

    def wait(self, timeout: float = None) -> bool:
        return self._event.wait(timeout=timeout)

    def reset(self):
        self._aborted = False
        self._event.clear()


TOOL_KIND_MAP = {
    "Read": ToolKind.READ, "file_read": ToolKind.READ,
    "Edit": ToolKind.EDIT, "file_edit": ToolKind.EDIT,
    "Write": ToolKind.EDIT, "file_write": ToolKind.EDIT,
    "Bash": ToolKind.EXECUTE, "Terminal": ToolKind.EXECUTE,
    "Glob": ToolKind.SEARCH, "Grep": ToolKind.SEARCH,
    "WebFetch": ToolKind.FETCH, "WebSearch": ToolKind.FETCH,
    "Agent": ToolKind.THINK, "Task": ToolKind.THINK,
    "Skill": ToolKind.THINK, "TodoWrite": ToolKind.THINK,
    "ExitPlanMode": ToolKind.SWITCH_MODE,
}


class NDJSONStream:
    _flask_mode = False
    _message_buffer: List[Dict[str, Any]] = []

    def __init__(self, input_stream=None, output_stream=None):
        self._input = input_stream or sys.stdin
        self._output = output_stream or (sys.stderr if NDJSONStream._flask_mode else sys.stdout)
        self._lock = threading.Lock()
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


class AcpSession:
    SESSION_TIMEOUT_SECONDS = 1800
    IDLE_TIMEOUT_SECONDS = 600

    def __init__(self, session_id: str, cwd: str,
                 client_capabilities: Dict = None,
                 mcp_servers: List = None):
        self.session_id = session_id
        self.cwd = cwd
        self.client_capabilities = client_capabilities or {}
        self.mcp_servers = mcp_servers or []
        self.state = SessionState.CREATING
        self.cancelled = False
        self.prompt_running = False
        self.pending_messages: OrderedDict = OrderedDict()
        self.next_pending_order: int = 0
        self.tool_use_cache: Dict[str, Any] = {}
        self.modes: List[SessionMode] = []
        self.models: List[SessionModel] = []
        self.config_options: List[ConfigOption] = []
        self.current_mode: str = "default"
        self.current_model: str = ""
        self.fingerprint: str = ""
        self.created_at: str = datetime.utcnow().isoformat()
        self.last_active_at: str = datetime.utcnow().isoformat()
        self.messages: List[Dict[str, Any]] = []
        self.usage: UsageInfo = UsageInfo()
        self.abort_controller: AbortController = AbortController()
        self._lock = threading.Lock()

    def activate(self):
        self.state = SessionState.ACTIVE
        self.touch()

    def idle(self):
        if self.state == SessionState.ACTIVE:
            self.state = SessionState.IDLE

    def touch(self):
        self.last_active_at = datetime.utcnow().isoformat()

    def is_timed_out(self) -> bool:
        try:
            last = datetime.fromisoformat(self.last_active_at)
            if self.state == SessionState.IDLE:
                return (datetime.utcnow() - last) > timedelta(seconds=self.IDLE_TIMEOUT_SECONDS)
            return (datetime.utcnow() - last) > timedelta(seconds=self.SESSION_TIMEOUT_SECONDS)
        except Exception:
            return False

    def close(self):
        self.state = SessionState.CLOSED
        self.cancelled = True
        self.abort_controller.abort()
        for order, (q, _) in list(self.pending_messages.items()):
            try:
                q.put({"cancelled": True}, timeout=1.0)
            except Exception:
                pass
        self.pending_messages.clear()


class ConnectionManager:
    def __init__(self):
        self._state = ConnectionState.DISCONNECTED
        self._auth_token: Optional[str] = None
        self._connected_at: Optional[str] = None
        self._last_heartbeat: Optional[str] = None
        self._heartbeat_interval = 30.0
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()

    @property
    def state(self) -> ConnectionState:
        return self._state

    def connect(self, auth_token: str = None) -> bool:
        with self._lock:
            if self._state in (ConnectionState.CONNECTED, ConnectionState.AUTHENTICATING):
                return True
            self._state = ConnectionState.CONNECTING
            self._auth_token = auth_token
            self._connected_at = datetime.utcnow().isoformat()
            self._last_heartbeat = datetime.utcnow().isoformat()
            self._state = ConnectionState.AUTHENTICATING if auth_token else ConnectionState.CONNECTED
            return True

    def authenticate(self, token: str) -> bool:
        with self._lock:
            if self._auth_token and self._auth_token != token:
                return False
            self._state = ConnectionState.CONNECTED
            self._last_heartbeat = datetime.utcnow().isoformat()
            return True

    def heartbeat(self):
        with self._lock:
            self._last_heartbeat = datetime.utcnow().isoformat()

    def is_connected(self) -> bool:
        with self._lock:
            return self._state == ConnectionState.CONNECTED

    def disconnect(self):
        with self._lock:
            self._state = ConnectionState.CLOSING
            self._running = False
            self._state = ConnectionState.CLOSED

    def start_heartbeat(self, send_func: Callable):
        self._running = True
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop, args=(send_func,), daemon=True
        )
        self._heartbeat_thread.start()

    def _heartbeat_loop(self, send_func: Callable):
        while self._running:
            try:
                if self.is_connected():
                    send_func({"type": "heartbeat", "timestamp": datetime.utcnow().isoformat()})
                    self.heartbeat()
            except Exception:
                pass
            time.sleep(self._heartbeat_interval)


class SessionManager:
    def __init__(self, session_timeout: float = 1800, idle_timeout: float = 600,
                 cleanup_interval: float = 60):
        self._sessions: Dict[str, AcpSession] = {}
        self._lock = threading.Lock()
        self._session_timeout = session_timeout
        self._idle_timeout = idle_timeout
        self._cleanup_interval = cleanup_interval
        self._running = False
        self._cleanup_thread: Optional[threading.Thread] = None
        self._on_session_timeout: Optional[Callable] = None

    def set_timeout_callback(self, callback: Callable):
        self._on_session_timeout = callback

    def create_session(self, cwd: str, client_capabilities: Dict = None,
                       mcp_servers: List = None) -> AcpSession:
        session_id = str(uuid.uuid4())
        session = AcpSession(
            session_id=session_id,
            cwd=cwd,
            client_capabilities=client_capabilities,
            mcp_servers=mcp_servers,
        )
        session.fingerprint = self._compute_fingerprint(cwd, mcp_servers or [])
        session.activate()
        with self._lock:
            self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[AcpSession]:
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.touch()
            return session

    def close_session(self, session_id: str) -> bool:
        with self._lock:
            session = self._sessions.pop(session_id, None)
        if session:
            session.close()
            return True
        return False

    def list_sessions(self) -> List[Dict]:
        with self._lock:
            return [{
                "sessionId": s.session_id,
                "cwd": s.cwd,
                "state": s.state.value,
                "createdAt": s.created_at,
                "lastActiveAt": s.last_active_at,
                "messageCount": len(s.messages),
            } for s in self._sessions.values()]

    def start_cleanup(self):
        self._running = True
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()

    def stop_cleanup(self):
        self._running = False

    def _cleanup_loop(self):
        while self._running:
            try:
                self._cleanup_timed_out()
            except Exception:
                pass
            time.sleep(self._cleanup_interval)

    def _cleanup_timed_out(self):
        timed_out = []
        with self._lock:
            for sid, session in list(self._sessions.items()):
                if session.is_timed_out():
                    timed_out.append(sid)

        for sid in timed_out:
            session = self._sessions.get(sid)
            if session:
                session.state = SessionState.TIMED_OUT
                if self._on_session_timeout:
                    try:
                        self._on_session_timeout(sid)
                    except Exception:
                        pass
                self.close_session(sid)

    def _compute_fingerprint(self, cwd: str, mcp_servers: List) -> str:
        data = json.dumps({"cwd": cwd, "mcp": sorted([str(s) for s in mcp_servers])},
                          sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()[:16]


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


class AuthCache:
    DEFAULT_TTL = 900

    def __init__(self, ttl: int = None):
        self._cache: Dict[str, Tuple[bool, float]] = {}
        self._ttl = ttl or self.DEFAULT_TTL
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[bool]:
        with self._lock:
            if key in self._cache:
                result, timestamp = self._cache[key]
                if time.time() - timestamp < self._ttl:
                    return result
                del self._cache[key]
        return None

    def set(self, key: str, result: bool):
        with self._lock:
            self._cache[key] = (result, time.time())

    def invalidate(self, key: str = None):
        with self._lock:
            if key:
                self._cache.pop(key, None)
            else:
                self._cache.clear()


class AcpAgent:
    PROTOCOL_VERSION = 1
    AGENT_NAME = "kaguya-ide"
    AGENT_TITLE = "Kaguya IDE"

    def __init__(self, bus: AcpMessageBus = None,
                 query_engine_factory: Callable = None,
                 permission_manager=None,
                 compactor=None):
        self._bus = bus
        self._session_manager = SessionManager()
        self._connection_manager = ConnectionManager()
        self._query_engine_factory = query_engine_factory
        self._query_engines: Dict[str, Any] = {}
        self._permission_manager = permission_manager
        self._compactor = compactor
        self._auth_cache = AuthCache()
        self._lock = threading.Lock()
        self._agent_version = "3.0.0"

        self._session_manager.set_timeout_callback(self._on_session_timeout)
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
        self._bus.register_handler("heartbeat", self._handle_heartbeat)

    def _handle_initialize(self, params: Dict) -> Dict:
        client_caps = params.get("clientCapabilities", {})
        auth_token = params.get("authToken")
        self._connection_manager.connect(auth_token)
        if auth_token:
            self._connection_manager.authenticate(auth_token)
        self._session_manager.start_cleanup()
        if self._bus:
            self._connection_manager.start_heartbeat(
                lambda data: self._bus.send_notification("heartbeat", data)
            )
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
                        "sessionTimeout": True,
                        "abortController": True,
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
        token = params.get("token", "")
        cached = self._auth_cache.get(token)
        if cached is not None:
            return {"authenticated": cached}
        success = self._connection_manager.authenticate(token)
        self._auth_cache.set(token, success)
        return {"authenticated": success}

    def _handle_heartbeat(self, params: Dict) -> Dict:
        self._connection_manager.heartbeat()
        return {"acknowledged": True, "timestamp": datetime.utcnow().isoformat()}

    def _handle_new_session(self, params: Dict) -> Dict:
        cwd = params.get("cwd", os.getcwd())
        mcp_servers = params.get("mcpServers", [])
        meta = params.get("_meta", {})

        session = self._session_manager.create_session(cwd, meta, mcp_servers)
        session.modes = self._get_available_modes()
        session.models = self._get_available_models()
        session.config_options = self._get_config_options()

        if self._query_engine_factory:
            self._query_engines[session.session_id] = self._query_engine_factory(session)

        self._send_commands_update(session.session_id)

        return {
            "sessionId": session.session_id,
            "modes": [asdict(m) for m in session.modes],
            "models": [asdict(m) for m in session.models],
            "configOptions": [asdict(c) for c in session.config_options],
        }

    def _handle_resume_session(self, params: Dict) -> Dict:
        session_id = params.get("sessionId", "")
        session = self._session_manager.get_session(session_id)

        if not session:
            return {"error": {"code": -32001, "message": "Session not found"}}

        new_cwd = params.get("cwd", session.cwd)
        new_mcp = params.get("mcpServers", [])
        new_fp = self._session_manager._compute_fingerprint(new_cwd, new_mcp)

        if new_fp != session.fingerprint:
            self._session_manager.close_session(session_id)
            return self._handle_new_session({"cwd": new_cwd, "mcpServers": new_mcp})

        session.cancelled = False
        session.abort_controller.reset()
        session.activate()

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
        return {"sessions": self._session_manager.list_sessions()}

    def _handle_fork_session(self, params: Dict) -> Dict:
        parent_id = params.get("sessionId", "")
        parent = self._session_manager.get_session(parent_id)
        if not parent:
            return {"error": {"code": -32001, "message": "Parent session not found"}}
        return self._handle_new_session({"cwd": parent.cwd})

    def _handle_close_session(self, params: Dict) -> Dict:
        session_id = params.get("sessionId", "")
        self._session_manager.close_session(session_id)
        self._query_engines.pop(session_id, None)
        return {}

    def _handle_prompt(self, params: Dict) -> Dict:
        session_id = params.get("sessionId", "")
        prompt_blocks = params.get("prompt", [])

        session = self._session_manager.get_session(session_id)
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
        session.abort_controller.reset()

        try:
            prompt_text = self._extract_prompt_text(prompt_blocks)
            session.messages.append({
                "role": "user",
                "content": prompt_blocks,
                "timestamp": datetime.utcnow().isoformat(),
            })

            if self._compactor and len(session.messages) > 50:
                try:
                    total_tokens = sum(
                        len(str(m.get("content", ""))) for m in session.messages
                    )
                    if total_tokens > 100000:
                        compacted = self._compactor.compact_messages(
                            session.messages, max_tokens=80000
                        )
                        if compacted:
                            session.messages = compacted
                            self._send_session_update(session_id, {
                                "sessionUpdate": "agent_message_chunk",
                                "content": {
                                    "type": "text",
                                    "text": "[Context auto-compacted to preserve working memory]",
                                },
                            })
                except Exception:
                    pass

            stop_reason = "end_turn"
            usage_data = None

            if self._query_engines.get(session_id):
                engine = self._query_engines[session_id]
                for event in engine.process(prompt_text, session):
                    if session.cancelled or session.abort_controller.aborted:
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
            session.touch()

            if session.pending_messages:
                next_order = min(session.pending_messages.keys())
                q, next_params = session.pending_messages.pop(next_order)
                q.put(self._handle_prompt(next_params))

    def _handle_cancel(self, params: Dict) -> Dict:
        session_id = params.get("sessionId", "")
        session = self._session_manager.get_session(session_id)
        if session:
            session.cancelled = True
            session.abort_controller.abort()
            for order, (q, _) in list(session.pending_messages.items()):
                try:
                    q.put({"cancelled": True}, timeout=1.0)
                except Exception:
                    pass
            session.pending_messages.clear()
            session.next_pending_order = 0
        return {}

    def _handle_set_mode(self, params: Dict) -> Dict:
        session_id = params.get("sessionId", "")
        mode_id = params.get("modeId", "default")
        session = self._session_manager.get_session(session_id)
        if session:
            session.current_mode = mode_id
            if self._permission_manager:
                try:
                    from kaguya_permissions import PermissionMode
                    self._permission_manager.set_session_mode(session_id, PermissionMode(mode_id))
                except Exception:
                    pass
            self._send_session_update(session_id, {
                "sessionUpdate": "current_mode_update",
                "currentModeId": mode_id,
            })
        return {}

    def _handle_set_model(self, params: Dict) -> Dict:
        session_id = params.get("sessionId", "")
        model_id = params.get("modelId", "")
        session = self._session_manager.get_session(session_id)
        if session:
            session.current_model = model_id
        return {}

    def _handle_set_config(self, params: Dict) -> Dict:
        session_id = params.get("sessionId", "")
        option_id = params.get("optionId", "")
        value = params.get("value")
        session = self._session_manager.get_session(session_id)
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

    def _on_session_timeout(self, session_id: str):
        self._query_engines.pop(session_id, None)

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

    def _get_available_modes(self) -> List[SessionMode]:
        return [
            SessionMode(id="auto", name="Auto", description="AI classifier auto-approves"),
            SessionMode(id="default", name="Default", description="Ask for permission"),
            SessionMode(id="acceptEdits", name="Accept Edits", description="Auto-accept edits"),
            SessionMode(id="plan", name="Plan", description="Read only"),
            SessionMode(id="dontAsk", name="Don't Ask", description="Auto-reject all"),
            SessionMode(id="bypassPermissions", name="Bypass", description="Allow all"),
        ]

    def _get_available_models(self) -> List[SessionModel]:
        return [
            SessionModel(id="qwen3", name="Qwen3", description="Qwen3 default"),
            SessionModel(id="deepseek", name="DeepSeek", description="DeepSeek V3/R1"),
            SessionModel(id="ollama", name="Ollama", description="Local Ollama"),
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

        if self._permission_manager:
            try:
                tool_name = tool_call.get("title", "").split(":")[0].strip() if tool_call.get("title") else ""
                tool_input = {}
                raw = tool_call.get("rawInput", "")
                if raw:
                    try:
                        tool_input = json.loads(raw)
                    except Exception:
                        pass
                decision = self._permission_manager.request_permission(
                    session_id=session_id,
                    tool_name=tool_name,
                    tool_input=tool_input,
                    timeout=120.0,
                )
                if decision in ("allow", "allow_always"):
                    return {"decision": "allow_always" if decision == "allow_always" else "allow_once"}
                return {"decision": "reject_once"}
            except Exception:
                pass

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
        self._lock = threading.Lock()

    def handle_initialize(self) -> Dict:
        return self._agent._handle_initialize({})

    def handle_new_session(self, params: Dict) -> Dict:
        return self._agent._handle_new_session(params)

    def handle_prompt(self, session_id: str, prompt: List[Dict],
                      on_update: Callable = None) -> Dict:
        session = self._agent._session_manager.get_session(session_id)
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
                    if session.cancelled or session.abort_controller.aborted:
                        stop_reason = "cancelled"
                        break
                    if on_update:
                        on_update(session_id, event)

            return {"stopReason": stop_reason}
        except Exception as e:
            return {"stopReason": "error", "error": str(e)}
        finally:
            session.prompt_running = False
            session.touch()

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

    def handle_heartbeat(self, session_id: str = "") -> Dict:
        return self._agent._handle_heartbeat({})


def create_acp_agent(query_engine_factory: Callable = None,
                     permission_manager=None) -> AcpAgent:
    stream = NDJSONStream()
    bus = AcpMessageBus(stream)
    agent = AcpAgent(bus, query_engine_factory, permission_manager)
    return agent


def create_acp_http_bridge(query_engine_factory: Callable = None,
                           permission_manager=None) -> AcpHttpBridge:
    NDJSONStream.enable_flask_mode()
    agent = create_acp_agent(query_engine_factory, permission_manager)
    return AcpHttpBridge(agent)


def run_acp_agent(query_engine_factory: Callable = None,
                  permission_manager=None):
    original_stdout = sys.stdout
    original_stderr = sys.stderr

    try:
        sys.stdout = sys.stderr
        stream = NDJSONStream(input_stream=sys.stdin, output_stream=original_stdout)
        bus = AcpMessageBus(stream)
        agent = AcpAgent(bus, query_engine_factory, permission_manager)
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
