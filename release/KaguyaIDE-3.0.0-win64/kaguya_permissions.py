#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辉夜IDE 网页端权限申请机制
参考 Trae/Claude Code 的权限架构实现

核心设计：
1. 权限模式：auto(自动审批)/default(默认)/acceptEdits(自动接受编辑)/plan(只读)/dontAsk(不询问)
2. 实时权限请求推送：通过SSE将权限请求从后端推送到前端
3. 自动审批分类器：基于工具类型、路径、命令安全性自动判断
4. 信任系统：用户可信任特定工具/路径/命令，后续自动放行
5. 与ACP协议集成：桥接ACP的requestPermission到Web UI
"""

import json
import os
import uuid
import time
import threading
import traceback
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from enum import Enum
from datetime import datetime
from collections import OrderedDict


class PermissionMode(Enum):
    AUTO = "auto"
    DEFAULT = "default"
    ACCEPT_EDITS = "acceptEdits"
    PLAN = "plan"
    DONT_ASK = "dontAsk"
    BYPASS_PERMISSIONS = "bypassPermissions"


class PermissionDecision(Enum):
    ALLOW = "allow"
    ALLOW_ALWAYS = "allow_always"
    REJECT = "reject"
    REJECT_ALWAYS = "reject_always"


class ToolRiskLevel(Enum):
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


TOOL_RISK_MAP = {
    "Read": ToolRiskLevel.SAFE,
    "Glob": ToolRiskLevel.SAFE,
    "Grep": ToolRiskLevel.SAFE,
    "WebFetch": ToolRiskLevel.LOW,
    "WebSearch": ToolRiskLevel.LOW,
    "Edit": ToolRiskLevel.MEDIUM,
    "Write": ToolRiskLevel.MEDIUM,
    "Bash": ToolRiskLevel.HIGH,
    "Terminal": ToolRiskLevel.HIGH,
    "Agent": ToolRiskLevel.LOW,
    "Task": ToolRiskLevel.LOW,
    "Skill": ToolRiskLevel.LOW,
    "TodoWrite": ToolRiskLevel.SAFE,
    "NotebookEdit": ToolRiskLevel.MEDIUM,
}

SAFE_PATHS_PATTERNS = [
    "/tmp/", "/temp/", "\\temp\\", "\\tmp\\",
    ".kaguya/", ".claude/",
]

DENIED_PATHS_PATTERNS = [
    "/etc/passwd", "/etc/shadow", "/etc/hosts",
    ".ssh/id_rsa", ".ssh/id_ed25519", ".ssh/authorized_keys",
    ".env", ".aws/credentials", ".gnupg/",
    "credentials.json", "service-account-key.json",
]

DENIED_COMMAND_PATTERNS = [
    "rm -rf /", "rm -rf ~", "del /f /s /q C:",
    "format ", "mkfs.", "dd if=",
    ":(){:|:&};:", "shutdown", "reboot", "halt", "poweroff",
    "net user", "net localgroup", "reg add", "reg delete",
    "chmod 777 /", "chmod -R 777 /",
]


@dataclass
class PermissionRequest:
    request_id: str
    session_id: str
    tool_name: str
    tool_input: Dict[str, Any]
    risk_level: ToolRiskLevel
    reason: str
    options: List[Dict[str, str]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    resolved: bool = False
    decision: Optional[PermissionDecision] = None
    auto_approved: bool = False
    timeout_seconds: float = 120.0
    _event: threading.Event = field(default_factory=threading.Event, repr=False)

    def wait(self, timeout=None):
        return self._event.wait(timeout=timeout or self.timeout_seconds)

    def resolve(self, decision: PermissionDecision):
        self.decision = decision
        self.resolved = True
        self._event.set()


@dataclass
class TrustRule:
    rule_id: str
    tool_name: str
    pattern: str
    decision: PermissionDecision
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    source: str = "user"
    hit_count: int = 0
    last_used: Optional[str] = None


@dataclass
class PermissionAuditEntry:
    entry_id: str
    request_id: str
    session_id: str
    tool_name: str
    risk_level: str
    decision: str
    auto_approved: bool
    reason: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class AutoApprovalClassifier:
    def __init__(self):
        self._safe_tools = {"Read", "Glob", "Grep", "TodoWrite", "Skill", "Task"}
        self._read_only_tools = {"Read", "Glob", "Grep"}
        self._edit_tools = {"Edit", "Write", "NotebookEdit"}
        self._execute_tools = {"Bash", "Terminal"}

    def classify(self, tool_name: str, tool_input: Dict[str, Any],
                 mode: PermissionMode, trust_rules: List[TrustRule]) -> Tuple[bool, str]:
        if mode == PermissionMode.AUTO:
            return self._classify_auto(tool_name, tool_input)
        elif mode == PermissionMode.ACCEPT_EDITS:
            return self._classify_accept_edits(tool_name, tool_input)
        elif mode == PermissionMode.PLAN:
            return self._classify_plan(tool_name, tool_input)
        elif mode == PermissionMode.DONT_ASK:
            return True, "dontAsk mode - auto approve all"
        elif mode == PermissionMode.DEFAULT:
            return self._classify_default(tool_name, tool_input, trust_rules)
        return False, "unknown mode"

    def _classify_auto(self, tool_name: str, tool_input: Dict) -> Tuple[bool, str]:
        if tool_name in self._safe_tools:
            return True, f"auto mode: {tool_name} is safe tool"
        if tool_name in self._read_only_tools:
            return True, f"auto mode: {tool_name} is read-only"
        if tool_name in self._edit_tools:
            path = tool_input.get("file_path", tool_input.get("path", ""))
            if self._is_safe_path(path):
                return True, f"auto mode: edit to safe path"
            return False, "auto mode: edit to non-safe path requires approval"
        if tool_name in self._execute_tools:
            cmd = tool_input.get("command", "")
            if self._is_safe_command(cmd):
                return True, f"auto mode: safe command"
            return False, "auto mode: command requires approval"
        return False, "auto mode: unknown tool requires approval"

    def _classify_accept_edits(self, tool_name: str, tool_input: Dict) -> Tuple[bool, str]:
        if tool_name in self._safe_tools:
            return True, "acceptEdits: safe tool"
        if tool_name in self._edit_tools:
            return True, "acceptEdits: auto-accept file edits"
        if tool_name in self._execute_tools:
            cmd = tool_input.get("command", "")
            if self._is_safe_command(cmd):
                return True, "acceptEdits: safe command"
            return False, "acceptEdits: dangerous command requires approval"
        return False, "acceptEdits: requires approval"

    def _classify_plan(self, tool_name: str, tool_input: Dict) -> Tuple[bool, str]:
        if tool_name in self._read_only_tools:
            return True, "plan mode: read-only allowed"
        if tool_name in ("WebFetch", "WebSearch"):
            return True, "plan mode: search allowed"
        return False, "plan mode: only read operations allowed"

    def _classify_default(self, tool_name: str, tool_input: Dict,
                          trust_rules: List[TrustRule]) -> Tuple[bool, str]:
        for rule in trust_rules:
            if rule.tool_name == tool_name or rule.tool_name == "*":
                if rule.decision in (PermissionDecision.ALLOW, PermissionDecision.ALLOW_ALWAYS):
                    rule.hit_count += 1
                    rule.last_used = datetime.utcnow().isoformat()
                    return True, f"trusted: {rule.tool_name} rule"
                elif rule.decision in (PermissionDecision.REJECT, PermissionDecision.REJECT_ALWAYS):
                    return False, f"blocked: {rule.tool_name} rule"

        if tool_name in self._safe_tools:
            return True, "default mode: safe tool auto-approved"
        return False, "default mode: requires user approval"

    def _is_safe_path(self, path: str) -> bool:
        if not path:
            return False
        for denied in DENIED_PATHS_PATTERNS:
            if denied in path:
                return False
        return True

    def _is_safe_command(self, cmd: str) -> bool:
        if not cmd:
            return False
        cmd_lower = cmd.lower().strip()
        for denied in DENIED_COMMAND_PATTERNS:
            if denied.lower() in cmd_lower:
                return False
        dangerous = ["sudo ", "runas ", "chmod 777", "icacls /grant Everyone"]
        for pat in dangerous:
            if pat.lower() in cmd_lower:
                return False
        return True

    def get_risk_level(self, tool_name: str, tool_input: Dict) -> ToolRiskLevel:
        base_risk = TOOL_RISK_MAP.get(tool_name, ToolRiskLevel.MEDIUM)
        if tool_name in ("Bash", "Terminal"):
            cmd = tool_input.get("command", "")
            if not self._is_safe_command(cmd):
                return ToolRiskLevel.CRITICAL
        if tool_name in ("Edit", "Write"):
            path = tool_input.get("file_path", tool_input.get("path", ""))
            if not self._is_safe_path(path):
                return ToolRiskLevel.HIGH
        return base_risk


class PermissionManager:
    def __init__(self):
        self._pending: OrderedDict[str, PermissionRequest] = OrderedDict()
        self._trust_rules: Dict[str, TrustRule] = {}
        self._session_modes: Dict[str, PermissionMode] = {}
        self._audit_log: List[PermissionAuditEntry] = []
        self._classifier = AutoApprovalClassifier()
        self._lock = threading.Lock()
        self._sse_listeners: Dict[str, List[Callable]] = {}
        self._global_mode = PermissionMode.BYPASS_PERMISSIONS
        self._max_audit_entries = 10000

    def set_session_mode(self, session_id: str, mode: PermissionMode):
        with self._lock:
            self._session_modes[session_id] = mode

    def get_session_mode(self, session_id: str) -> PermissionMode:
        with self._lock:
            return self._session_modes.get(session_id, self._global_mode)

    def set_global_mode(self, mode: PermissionMode):
        self._global_mode = mode

    def get_global_mode(self) -> PermissionMode:
        return self._global_mode

    def has_active_listeners(self) -> bool:
        with self._lock:
            for listener_id, callbacks in self._sse_listeners.items():
                if callbacks:
                    return True
            return False

    def request_permission(self, session_id: str, tool_name: str,
                           tool_input: Dict[str, Any],
                           timeout: float = 120.0) -> PermissionDecision:
        mode = self.get_session_mode(session_id)
        risk_level = self._classifier.get_risk_level(tool_name, tool_input)
        trust_rules = list(self._trust_rules.values())

        if mode == PermissionMode.BYPASS_PERMISSIONS:
            request = PermissionRequest(
                request_id=f"perm_{uuid.uuid4().hex[:12]}",
                session_id=session_id,
                tool_name=tool_name,
                tool_input=tool_input,
                risk_level=risk_level,
                reason="bypassPermissions mode - auto approved",
                auto_approved=True,
            )
            request.resolve(PermissionDecision.ALLOW)
            self._add_audit_entry(request, "bypass_mode")
            return PermissionDecision.ALLOW

        if mode == PermissionMode.DONT_ASK:
            request = PermissionRequest(
                request_id=f"perm_{uuid.uuid4().hex[:12]}",
                session_id=session_id,
                tool_name=tool_name,
                tool_input=tool_input,
                risk_level=risk_level,
                reason="dontAsk mode - auto rejected",
                auto_approved=False,
            )
            request.resolve(PermissionDecision.REJECT)
            self._add_audit_entry(request, "dont_ask_mode")
            return PermissionDecision.REJECT

        auto_approved, reason = self._classifier.classify(
            tool_name, tool_input, mode, trust_rules
        )

        if auto_approved:
            request = PermissionRequest(
                request_id=f"perm_{uuid.uuid4().hex[:12]}",
                session_id=session_id,
                tool_name=tool_name,
                tool_input=tool_input,
                risk_level=risk_level,
                reason=reason,
                auto_approved=True,
            )
            request.resolve(PermissionDecision.ALLOW)
            self._add_audit_entry(request, "auto_approved")
            self._notify_sse_listeners("permission_auto_approved", {
                "request_id": request.request_id,
                "tool_name": tool_name,
                "reason": reason,
            })
            return PermissionDecision.ALLOW

        has_ui = self.has_active_listeners()

        if not has_ui:
            if mode == PermissionMode.AUTO:
                if risk_level in (ToolRiskLevel.SAFE, ToolRiskLevel.LOW, ToolRiskLevel.MEDIUM):
                    request = PermissionRequest(
                        request_id=f"perm_{uuid.uuid4().hex[:12]}",
                        session_id=session_id,
                        tool_name=tool_name,
                        tool_input=tool_input,
                        risk_level=risk_level,
                        reason="no_ui_auto_mode: auto-approved safe/low/medium risk",
                        auto_approved=True,
                    )
                    request.resolve(PermissionDecision.ALLOW)
                    self._add_audit_entry(request, "no_ui_auto_approved")
                    return PermissionDecision.ALLOW
                else:
                    request = PermissionRequest(
                        request_id=f"perm_{uuid.uuid4().hex[:12]}",
                        session_id=session_id,
                        tool_name=tool_name,
                        tool_input=tool_input,
                        risk_level=risk_level,
                        reason="no_ui_auto_mode: high/critical risk rejected",
                        auto_approved=False,
                    )
                    request.resolve(PermissionDecision.REJECT)
                    self._add_audit_entry(request, "no_ui_auto_rejected")
                    return PermissionDecision.REJECT
            elif mode == PermissionMode.ACCEPT_EDITS:
                if tool_name in ("Edit", "Write", "Read", "Glob", "Grep"):
                    request = PermissionRequest(
                        request_id=f"perm_{uuid.uuid4().hex[:12]}",
                        session_id=session_id,
                        tool_name=tool_name,
                        tool_input=tool_input,
                        risk_level=risk_level,
                        reason="no_ui_acceptEdits: file operation auto-approved",
                        auto_approved=True,
                    )
                    request.resolve(PermissionDecision.ALLOW)
                    self._add_audit_entry(request, "no_ui_accept_edits")
                    return PermissionDecision.ALLOW
                else:
                    request = PermissionRequest(
                        request_id=f"perm_{uuid.uuid4().hex[:12]}",
                        session_id=session_id,
                        tool_name=tool_name,
                        tool_input=tool_input,
                        risk_level=risk_level,
                        reason="no_ui_acceptEdits: non-file operation rejected",
                        auto_approved=False,
                    )
                    request.resolve(PermissionDecision.REJECT)
                    self._add_audit_entry(request, "no_ui_rejected")
                    return PermissionDecision.REJECT
            elif mode == PermissionMode.PLAN:
                if tool_name in ("Read", "Glob", "Grep", "WebFetch", "WebSearch"):
                    request = PermissionRequest(
                        request_id=f"perm_{uuid.uuid4().hex[:12]}",
                        session_id=session_id,
                        tool_name=tool_name,
                        tool_input=tool_input,
                        risk_level=risk_level,
                        reason="no_ui_plan: read-only operation auto-approved",
                        auto_approved=True,
                    )
                    request.resolve(PermissionDecision.ALLOW)
                    self._add_audit_entry(request, "no_ui_plan_approved")
                    return PermissionDecision.ALLOW
                else:
                    request = PermissionRequest(
                        request_id=f"perm_{uuid.uuid4().hex[:12]}",
                        session_id=session_id,
                        tool_name=tool_name,
                        tool_input=tool_input,
                        risk_level=risk_level,
                        reason="no_ui_plan: write operation rejected",
                        auto_approved=False,
                    )
                    request.resolve(PermissionDecision.REJECT)
                    self._add_audit_entry(request, "no_ui_plan_rejected")
                    return PermissionDecision.REJECT
            else:
                if risk_level in (ToolRiskLevel.SAFE, ToolRiskLevel.LOW):
                    request = PermissionRequest(
                        request_id=f"perm_{uuid.uuid4().hex[:12]}",
                        session_id=session_id,
                        tool_name=tool_name,
                        tool_input=tool_input,
                        risk_level=risk_level,
                        reason="no_ui_default: safe/low risk auto-approved",
                        auto_approved=True,
                    )
                    request.resolve(PermissionDecision.ALLOW)
                    self._add_audit_entry(request, "no_ui_safe_approved")
                    return PermissionDecision.ALLOW
                else:
                    request = PermissionRequest(
                        request_id=f"perm_{uuid.uuid4().hex[:12]}",
                        session_id=session_id,
                        tool_name=tool_name,
                        tool_input=tool_input,
                        risk_level=risk_level,
                        reason="no_ui_default: medium+ risk rejected",
                        auto_approved=False,
                    )
                    request.resolve(PermissionDecision.REJECT)
                    self._add_audit_entry(request, "no_ui_rejected")
                    return PermissionDecision.REJECT

        request = PermissionRequest(
            request_id=f"perm_{uuid.uuid4().hex[:12]}",
            session_id=session_id,
            tool_name=tool_name,
            tool_input=tool_input,
            risk_level=risk_level,
            reason=reason,
            timeout_seconds=timeout,
            options=[
                {"kind": "allow_always", "name": "Always Allow", "option_id": "allow_always"},
                {"kind": "allow", "name": "Allow Once", "option_id": "allow"},
                {"kind": "reject", "name": "Reject", "option_id": "reject"},
            ],
        )

        with self._lock:
            self._pending[request.request_id] = request

        self._notify_sse_listeners("permission_request", {
            "request_id": request.request_id,
            "session_id": session_id,
            "tool_name": tool_name,
            "tool_input": tool_input,
            "risk_level": risk_level.value,
            "reason": reason,
            "options": request.options,
            "created_at": request.created_at,
        })

        if request.wait(timeout=timeout):
            with self._lock:
                self._pending.pop(request.request_id, None)

            self._add_audit_entry(request, "user_approved" if request.decision in
                                  (PermissionDecision.ALLOW, PermissionDecision.ALLOW_ALWAYS)
                                  else "user_rejected")

            if request.decision == PermissionDecision.ALLOW_ALWAYS:
                self._add_trust_rule(tool_name, tool_input, PermissionDecision.ALLOW_ALWAYS)
            elif request.decision == PermissionDecision.REJECT_ALWAYS:
                self._add_trust_rule(tool_name, tool_input, PermissionDecision.REJECT_ALWAYS)

            return request.decision
        else:
            with self._lock:
                self._pending.pop(request.request_id, None)

            request.resolve(PermissionDecision.REJECT)
            self._add_audit_entry(request, "timeout")
            self._notify_sse_listeners("permission_timeout", {
                "request_id": request.request_id,
                "tool_name": tool_name,
            })
            return PermissionDecision.REJECT

    def respond_permission(self, request_id: str, decision: str) -> bool:
        with self._lock:
            request = self._pending.get(request_id)

        if not request or request.resolved:
            return False

        try:
            perm_decision = PermissionDecision(decision)
        except ValueError:
            return False

        request.resolve(perm_decision)

        self._notify_sse_listeners("permission_resolved", {
            "request_id": request_id,
            "decision": decision,
            "tool_name": request.tool_name,
        })

        return True

    def get_pending_requests(self, session_id: str = None) -> List[Dict]:
        with self._lock:
            requests = list(self._pending.values())
        if session_id:
            requests = [r for r in requests if r.session_id == session_id]
        return [asdict(r) for r in requests if not r.resolved]

    def _add_trust_rule(self, tool_name: str, tool_input: Dict,
                        decision: PermissionDecision):
        path = tool_input.get("file_path", tool_input.get("path", ""))
        cmd = tool_input.get("command", "")
        pattern = path or cmd or "*"

        rule_id = f"rule_{uuid.uuid4().hex[:8]}"
        rule = TrustRule(
            rule_id=rule_id,
            tool_name=tool_name,
            pattern=pattern,
            decision=decision,
            source="user",
        )
        with self._lock:
            self._trust_rules[rule_id] = rule

    def remove_trust_rule(self, rule_id: str) -> bool:
        with self._lock:
            return self._trust_rules.pop(rule_id, None) is not None

    def get_trust_rules(self) -> List[Dict]:
        with self._lock:
            return [asdict(r) for r in self._trust_rules.values()]

    def _add_audit_entry(self, request: PermissionRequest, outcome: str):
        entry = PermissionAuditEntry(
            entry_id=f"audit_{uuid.uuid4().hex[:8]}",
            request_id=request.request_id,
            session_id=request.session_id,
            tool_name=request.tool_name,
            risk_level=request.risk_level.value,
            decision=request.decision.value if request.decision else "none",
            auto_approved=request.auto_approved,
            reason=f"{request.reason} [{outcome}]",
        )
        with self._lock:
            self._audit_log.append(entry)
            if len(self._audit_log) > self._max_audit_entries:
                self._audit_log = self._audit_log[-self._max_audit_entries:]

    def get_audit_log(self, limit: int = 100, session_id: str = None) -> List[Dict]:
        with self._lock:
            entries = list(self._audit_log)
        if session_id:
            entries = [e for e in entries if e.session_id == session_id]
        return [asdict(e) for e in entries[-limit:]]

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total = len(self._audit_log)
            auto_approved = sum(1 for e in self._audit_log if e.auto_approved)
            user_approved = sum(1 for e in self._audit_log
                                if not e.auto_approved and e.decision in
                                (PermissionDecision.ALLOW.value, PermissionDecision.ALLOW_ALWAYS.value))
            rejected = sum(1 for e in self._audit_log
                           if e.decision in (PermissionDecision.REJECT.value, PermissionDecision.REJECT_ALWAYS.value))
            pending = len([r for r in self._pending.values() if not r.resolved])

        return {
            "total_requests": total,
            "auto_approved": auto_approved,
            "user_approved": user_approved,
            "rejected": rejected,
            "pending": pending,
            "trust_rules_count": len(self._trust_rules),
            "global_mode": self._global_mode.value,
        }

    def register_sse_listener(self, listener_id: str, callback: Callable):
        with self._lock:
            if listener_id not in self._sse_listeners:
                self._sse_listeners[listener_id] = []
            self._sse_listeners[listener_id].append(callback)

    def unregister_sse_listener(self, listener_id: str):
        with self._lock:
            self._sse_listeners.pop(listener_id, None)

    def _notify_sse_listeners(self, event_type: str, data: Dict):
        with self._lock:
            listeners = list(self._sse_listeners.items())

        for listener_id, callbacks in listeners:
            for cb in callbacks:
                try:
                    cb(event_type, data)
                except Exception:
                    pass

    def cancel_pending(self, session_id: str = None):
        with self._lock:
            for req in self._pending.values():
                if not req.resolved:
                    if session_id is None or req.session_id == session_id:
                        req.resolve(PermissionDecision.REJECT)
            if session_id:
                self._pending = OrderedDict(
                    (k, v) for k, v in self._pending.items()
                    if v.session_id != session_id
                )
            else:
                self._pending.clear()

    def get_available_modes(self) -> List[Dict]:
        return [
            {"id": "auto", "name": "Auto", "description": "Automatically approve safe operations"},
            {"id": "default", "name": "Default", "description": "Ask for permission on risky operations"},
            {"id": "acceptEdits", "name": "Accept Edits", "description": "Auto-accept file edits, ask for commands"},
            {"id": "plan", "name": "Plan", "description": "Plan mode - read only, no modifications"},
            {"id": "dontAsk", "name": "Don't Ask", "description": "Never ask for permission (auto-reject all)"},
            {"id": "bypassPermissions", "name": "Bypass Permissions", "description": "Allow all operations without asking (use with caution)"},
        ]


permission_manager = PermissionManager()


def create_permission_manager() -> PermissionManager:
    return PermissionManager()
