#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辉夜IDE 权限决策管道 v2.0
参考 Claude Code 的 src/utils/permissions/permissions.ts 分层架构

核心架构：10步分层决策管道
1a. 检查 deny 规则 → 直接拒绝
1b. 检查 ask 规则 → 需要确认
1c. 工具自身 checkPermissions() → 工具级权限
1d. 工具拒绝 → 直接拒绝
1e. requiresUserInteraction() → 必须交互
1f. 内容级 ask 规则 → 精细化控制
1g. 安全检查(.git/, .claude/) → 不可绕过
2a. bypassPermissions 模式 → 全部允许
2b. alwaysAllow 规则 → 自动允许
3.  转换 passthrough → ask
4.  auto 模式 → AI 分类器决策
5.  dontAsk 模式 → 静默拒绝
6.  无 UI 回退 → 降级处理
7.  交互式权限请求 → SSE 推送

拒绝追踪机制：
- 拒绝原因代码及描述
- 决策时间戳
- 请求主体标识
- 涉及资源路径及属性
- 决策依据的策略规则ID
- 连续拒绝计数与回退
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
    DENY = "deny"
    ASK = "ask"


class DenialReasonCode(Enum):
    RULE_DENY = "RULE_DENY"
    TOOL_DENY = "TOOL_DENY"
    SAFETY_CHECK = "SAFETY_CHECK"
    MODE_DONT_ASK = "MODE_DONT_ASK"
    NO_UI_FALLBACK = "NO_UI_FALLBACK"
    TIMEOUT = "TIMEOUT"
    CLASSIFIER_DENY = "CLASSIFIER_DENY"
    READ_ONLY_MODE = "READ_ONLY_MODE"
    DENIED_PATH = "DENIED_PATH"
    DANGEROUS_COMMAND = "DANGEROUS_COMMAND"
    CONSECUTIVE_DENIAL_LIMIT = "CONSECUTIVE_DENIAL_LIMIT"


class ToolRiskLevel(Enum):
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RuleSource(Enum):
    USER = "user"
    PROJECT = "project"
    POLICY = "policy"
    SESSION = "session"
    SYSTEM = "system"
    TRUST = "trust"
    ALWAYS_ALLOW = "alwaysAllow"
    DENY = "deny"


class PipelineStep(Enum):
    STEP_1A_DENY_RULES = "1a_deny_rules"
    STEP_1B_ASK_RULES = "1b_ask_rules"
    STEP_1C_TOOL_PERMISSIONS = "1c_tool_permissions"
    STEP_1D_TOOL_DENY = "1d_tool_deny"
    STEP_1E_USER_INTERACTION = "1e_user_interaction"
    STEP_1F_CONTENT_RULES = "1f_content_rules"
    STEP_1G_SAFETY_CHECK = "1g_safety_check"
    STEP_2A_BYPASS_MODE = "2a_bypass_mode"
    STEP_2B_ALWAYS_ALLOW = "2b_always_allow"
    STEP_3_PASSTHROUGH = "3_passthrough"
    STEP_4_AUTO_CLASSIFIER = "4_auto_classifier"
    STEP_5_DONT_ASK = "5_dont_ask"
    STEP_6_NO_UI_FALLBACK = "6_no_ui_fallback"
    STEP_7_INTERACTIVE = "7_interactive"


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

SAFE_TOOLS = {"Read", "Glob", "Grep", "TodoWrite", "Skill", "Task"}
READ_ONLY_TOOLS = {"Read", "Glob", "Grep"}
EDIT_TOOLS = {"Edit", "Write", "NotebookEdit"}
EXECUTE_TOOLS = {"Bash", "Terminal"}

PROTECTED_PATHS = [
    ".git/", ".git\\",
    ".claude/", ".claude\\",
    ".kaguya/", ".kaguya\\",
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
class PermissionRule:
    rule_id: str
    tool_name: str
    pattern: str
    decision: PermissionDecision
    source: RuleSource = RuleSource.USER
    priority: int = 0
    classifier_approvable: bool = False
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    hit_count: int = 0
    last_used: Optional[str] = None
    description: str = ""


@dataclass
class DenialRecord:
    record_id: str
    session_id: str
    tool_name: str
    reason_code: DenialReasonCode
    reason_description: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    request_id: str = ""
    resource_path: str = ""
    resource_attributes: Dict[str, Any] = field(default_factory=dict)
    policy_rule_id: str = ""
    pipeline_step: str = ""
    tool_input_summary: str = ""
    risk_level: str = ""
    mode_at_time: str = ""


@dataclass
class DenialTrackingState:
    consecutive_denials: int = 0
    total_denials: int = 0
    max_consecutive: int = 3
    max_total: int = 20
    last_denial_time: Optional[str] = None
    last_denial_reason: Optional[str] = None
    session_id: str = ""

    def record_denial(self, reason_code: str):
        self.consecutive_denials += 1
        self.total_denials += 1
        self.last_denial_time = datetime.utcnow().isoformat()
        self.last_denial_reason = reason_code

    def record_success(self):
        self.consecutive_denials = 0

    def should_escalate(self) -> bool:
        if self.consecutive_denials >= self.max_consecutive:
            return True
        if self.total_denials >= self.max_total:
            return True
        return False


@dataclass
class PermissionRequest:
    request_id: str
    session_id: str
    tool_name: str
    tool_input: Dict[str, Any]
    risk_level: ToolRiskLevel
    reason: str
    pipeline_step: str = ""
    options: List[Dict[str, str]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    resolved: bool = False
    decision: Optional[PermissionDecision] = None
    auto_approved: bool = False
    timeout_seconds: float = 120.0
    denial_record: Optional[DenialRecord] = None
    _event: threading.Event = field(default_factory=threading.Event, repr=False)

    def wait(self, timeout=None):
        return self._event.wait(timeout=timeout or self.timeout_seconds)

    def resolve(self, decision: PermissionDecision):
        self.decision = decision
        self.resolved = True
        self._event.set()


@dataclass
class PipelineResult:
    decision: PermissionDecision
    step: PipelineStep
    reason: str
    rule_id: str = ""
    classifier_approvable: bool = False
    denial_record: Optional[DenialRecord] = None


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
    pipeline_step: str = ""
    denial_reason_code: str = ""
    policy_rule_id: str = ""
    resource_path: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class PermissionRuleStore:
    def __init__(self):
        self._rules: Dict[str, PermissionRule] = {}
        self._lock = threading.Lock()
        self._sorted_cache: Optional[List[PermissionRule]] = None
        self._cache_dirty = True
        self._init_builtin_rules()

    def _invalidate_cache(self):
        self._cache_dirty = True
        self._sorted_cache = None

    def _init_builtin_rules(self):
        builtin = [
            PermissionRule(
                rule_id="builtin_deny_protected_paths",
                tool_name="*",
                pattern=".git/",
                decision=PermissionDecision.DENY,
                source=RuleSource.SYSTEM,
                priority=1000,
                classifier_approvable=False,
                description="Protect .git directories",
            ),
            PermissionRule(
                rule_id="builtin_deny_protected_paths_2",
                tool_name="*",
                pattern=".claude/",
                decision=PermissionDecision.DENY,
                source=RuleSource.SYSTEM,
                priority=1000,
                classifier_approvable=False,
                description="Protect .claude directories",
            ),
            PermissionRule(
                rule_id="builtin_deny_protected_paths_3",
                tool_name="*",
                pattern=".kaguya/",
                decision=PermissionDecision.DENY,
                source=RuleSource.SYSTEM,
                priority=1000,
                classifier_approvable=False,
                description="Protect .kaguya directories",
            ),
            PermissionRule(
                rule_id="builtin_allow_safe_tools",
                tool_name="*",
                pattern="safe_tools",
                decision=PermissionDecision.ALLOW,
                source=RuleSource.ALWAYS_ALLOW,
                priority=100,
                classifier_approvable=False,
                description="Always allow safe/read-only tools",
            ),
        ]
        for rule in builtin:
            self._rules[rule.rule_id] = rule
        self._invalidate_cache()

    def add_rule(self, rule: PermissionRule):
        with self._lock:
            self._rules[rule.rule_id] = rule
            self._invalidate_cache()

    def remove_rule(self, rule_id: str) -> bool:
        with self._lock:
            result = self._rules.pop(rule_id, None) is not None
            if result:
                self._invalidate_cache()
            return result

    def _get_sorted_rules(self) -> List[PermissionRule]:
        if not self._cache_dirty and self._sorted_cache is not None:
            return self._sorted_cache
        with self._lock:
            self._sorted_cache = sorted(
                self._rules.values(), key=lambda r: r.priority, reverse=True
            )
            self._cache_dirty = False
            return self._sorted_cache

    def get_rules(self, tool_name: str = None, source: RuleSource = None) -> List[PermissionRule]:
        rules = self._get_sorted_rules()
        if tool_name:
            rules = [r for r in rules if r.tool_name == tool_name or r.tool_name == "*"]
        if source:
            rules = [r for r in rules if r.source == source]
        return rules

    def get_deny_rules(self, tool_name: str) -> List[PermissionRule]:
        return [r for r in self.get_rules(tool_name)
                if r.decision == PermissionDecision.DENY]

    def get_ask_rules(self, tool_name: str) -> List[PermissionRule]:
        return [r for r in self.get_rules(tool_name)
                if r.decision == PermissionDecision.ASK]

    def get_allow_rules(self, tool_name: str) -> List[PermissionRule]:
        return [r for r in self.get_rules(tool_name)
                if r.decision in (PermissionDecision.ALLOW, PermissionDecision.ALLOW_ALWAYS)]

    def match_rule(self, rule: PermissionRule, tool_name: str, tool_input: Dict) -> bool:
        if rule.tool_name != "*" and rule.tool_name != tool_name:
            return False
        if rule.pattern == "safe_tools":
            return tool_name in SAFE_TOOLS
        if rule.pattern == "*":
            return True
        path = tool_input.get("file_path", tool_input.get("path", ""))
        cmd = tool_input.get("command", "")
        if path:
            import fnmatch
            if fnmatch.fnmatch(path.replace("\\", "/"), rule.pattern):
                return True
            if rule.pattern in path:
                return True
        if cmd:
            if rule.pattern in cmd:
                return True
        target = path or cmd or ""
        return rule.pattern in target if target else False


class DenialTracker:
    def __init__(self):
        self._states: Dict[str, DenialTrackingState] = {}
        self._records: List[DenialRecord] = []
        self._lock = threading.Lock()
        self._max_records = 10000

    def get_state(self, session_id: str) -> DenialTrackingState:
        with self._lock:
            if session_id not in self._states:
                self._states[session_id] = DenialTrackingState(session_id=session_id)
            return self._states[session_id]

    def record_denial(self, record: DenialRecord):
        with self._lock:
            self._records.append(record)
            if len(self._records) > self._max_records:
                self._records = self._records[-self._max_records:]
            state = self._states.get(record.session_id)
            if state:
                state.record_denial(record.reason_code.value)

    def record_success(self, session_id: str):
        with self._lock:
            state = self._states.get(session_id)
            if state:
                state.record_success()

    def should_escalate(self, session_id: str) -> bool:
        state = self.get_state(session_id)
        return state.should_escalate()

    def get_records(self, session_id: str = None, limit: int = 100,
                    reason_code: DenialReasonCode = None) -> List[Dict]:
        with self._lock:
            records = list(self._records)
        if session_id:
            records = [r for r in records if r.session_id == session_id]
        if reason_code:
            records = [r for r in records if r.reason_code == reason_code]
        return [asdict(r) for r in records[-limit:]]

    def get_stats(self, session_id: str = None) -> Dict[str, Any]:
        with self._lock:
            records = list(self._records)
        if session_id:
            records = [r for r in records if r.session_id == session_id]
        reason_counts = {}
        for r in records:
            code = r.reason_code.value
            reason_counts[code] = reason_counts.get(code, 0) + 1
        state = self.get_state(session_id) if session_id else None
        return {
            "total_denials": len(records),
            "reason_breakdown": reason_counts,
            "consecutive_denials": state.consecutive_denials if state else 0,
            "should_escalate": state.should_escalate() if state else False,
        }


class CommandFlagSpec:
    def __init__(self, name: str, flag_type: str = "none",
                 requires_value: bool = False, safe_values: List[str] = None,
                 allow_any_value: bool = False, description: str = ""):
        self.name = name
        self.flag_type = flag_type
        self.requires_value = requires_value
        self.safe_values = safe_values or []
        self.allow_any_value = allow_any_value
        self.description = description


class CommandSpec:
    def __init__(self, name: str, is_safe: bool = False,
                 safe_flags: List[CommandFlagSpec] = None,
                 allow_arguments: bool = False,
                 description: str = ""):
        self.name = name
        self.is_safe = is_safe
        self.safe_flags = {f.name: f for f in (safe_flags or [])}
        self.allow_arguments = allow_arguments
        self.description = description


COMMAND_ALLOWLIST = {
    "ls": CommandSpec("ls", is_safe=True, allow_arguments=True, description="List directory contents"),
    "dir": CommandSpec("dir", is_safe=True, allow_arguments=True, description="List directory (Windows)"),
    "cat": CommandSpec("cat", is_safe=True, allow_arguments=True, description="Display file contents"),
    "head": CommandSpec("head", is_safe=True, allow_arguments=True, description="Display file beginning"),
    "tail": CommandSpec("tail", is_safe=True, allow_arguments=True, description="Display file ending"),
    "less": CommandSpec("less", is_safe=True, allow_arguments=True, description="Page through file"),
    "more": CommandSpec("more", is_safe=True, allow_arguments=True, description="Page through file"),
    "wc": CommandSpec("wc", is_safe=True, allow_arguments=True, description="Word count"),
    "sort": CommandSpec("sort", is_safe=True, allow_arguments=True, description="Sort lines"),
    "uniq": CommandSpec("uniq", is_safe=True, allow_arguments=True, description="Unique lines"),
    "diff": CommandSpec("diff", is_safe=True, allow_arguments=True, description="Compare files"),
    "echo": CommandSpec("echo", is_safe=True, allow_arguments=True, description="Print text"),
    "pwd": CommandSpec("pwd", is_safe=True, description="Print working directory"),
    "whoami": CommandSpec("whoami", is_safe=True, description="Current user"),
    "hostname": CommandSpec("hostname", is_safe=True, description="System hostname"),
    "date": CommandSpec("date", is_safe=True, description="Current date"),
    "uname": CommandSpec("uname", is_safe=True, allow_arguments=True, description="System info"),
    "env": CommandSpec("env", is_safe=True, description="Environment variables"),
    "printenv": CommandSpec("printenv", is_safe=True, allow_arguments=True, description="Print env vars"),
    "which": CommandSpec("which", is_safe=True, allow_arguments=True, description="Find command path"),
    "where": CommandSpec("where", is_safe=True, allow_arguments=True, description="Find command (Windows)"),
    "type": CommandSpec("type", is_safe=True, allow_arguments=True, description="Display command type"),
    "find": CommandSpec("find", is_safe=True, allow_arguments=True, description="Find files"),
    "grep": CommandSpec("grep", is_safe=True, allow_arguments=True, description="Search text"),
    "rg": CommandSpec("rg", is_safe=True, allow_arguments=True, description="Ripgrep search"),
    "ag": CommandSpec("ag", is_safe=True, allow_arguments=True, description="Silver search"),
    "ack": CommandSpec("ack", is_safe=True, allow_arguments=True, description="Ack search"),
    "git": CommandSpec("git", is_safe=True, safe_flags=[
        CommandFlagSpec("status", flag_type="subcommand", description="Show working tree status"),
        CommandFlagSpec("log", flag_type="subcommand", allow_any_value=True, description="Show commit logs"),
        CommandFlagSpec("diff", flag_type="subcommand", allow_any_value=True, description="Show differences"),
        CommandFlagSpec("show", flag_type="subcommand", allow_any_value=True, description="Show objects"),
        CommandFlagSpec("branch", flag_type="subcommand", allow_any_value=True, description="List branches"),
        CommandFlagSpec("tag", flag_type="subcommand", allow_any_value=True, description="List tags"),
        CommandFlagSpec("remote", flag_type="subcommand", allow_any_value=True, description="Manage remotes"),
        CommandFlagSpec("stash", flag_type="subcommand", allow_any_value=True, description="Stash changes"),
        CommandFlagSpec("fetch", flag_type="subcommand", allow_any_value=True, description="Fetch from remote"),
        CommandFlagSpec("blame", flag_type="subcommand", allow_any_value=True, description="Line annotations"),
    ], description="Git version control"),
    "python": CommandSpec("python", is_safe=True, safe_flags=[
        CommandFlagSpec("--version", flag_type="flag", description="Show version"),
        CommandFlagSpec("-c", flag_type="flag", requires_value=True, allow_any_value=True, description="Run command"),
        CommandFlagSpec("-m", flag_type="flag", requires_value=True, allow_any_value=True, description="Run module"),
    ], allow_arguments=True, description="Python interpreter"),
    "python3": CommandSpec("python3", is_safe=True, safe_flags=[
        CommandFlagSpec("--version", flag_type="flag", description="Show version"),
        CommandFlagSpec("-c", flag_type="flag", requires_value=True, allow_any_value=True, description="Run command"),
    ], allow_arguments=True, description="Python3 interpreter"),
    "pip": CommandSpec("pip", is_safe=True, safe_flags=[
        CommandFlagSpec("list", flag_type="subcommand", allow_any_value=True, description="List packages"),
        CommandFlagSpec("show", flag_type="subcommand", allow_any_value=True, description="Show package info"),
        CommandFlagSpec("search", flag_type="subcommand", allow_any_value=True, description="Search packages"),
    ], allow_arguments=True, description="Python package manager"),
    "npm": CommandSpec("npm", is_safe=True, safe_flags=[
        CommandFlagSpec("list", flag_type="subcommand", allow_any_value=True, description="List packages"),
        CommandFlagSpec("view", flag_type="subcommand", allow_any_value=True, description="View package info"),
        CommandFlagSpec("search", flag_type="subcommand", allow_any_value=True, description="Search packages"),
        CommandFlagSpec("run", flag_type="subcommand", allow_any_value=True, description="Run scripts"),
    ], allow_arguments=True, description="Node package manager"),
    "node": CommandSpec("node", is_safe=True, safe_flags=[
        CommandFlagSpec("--version", flag_type="flag", description="Show version"),
        CommandFlagSpec("-e", flag_type="flag", requires_value=True, allow_any_value=True, description="Evaluate"),
    ], allow_arguments=True, description="Node.js runtime"),
    "ps": CommandSpec("ps", is_safe=True, allow_arguments=True, description="Process status"),
    "tasklist": CommandSpec("tasklist", is_safe=True, allow_arguments=True, description="List processes (Windows)"),
    "df": CommandSpec("df", is_safe=True, allow_arguments=True, description="Disk free space"),
    "du": CommandSpec("du", is_safe=True, allow_arguments=True, description="Disk usage"),
    "free": CommandSpec("free", is_safe=True, allow_arguments=True, description="Memory usage"),
    "top": CommandSpec("top", is_safe=True, description="Process monitor"),
    "htop": CommandSpec("htop", is_safe=True, description="Process monitor"),
    "netstat": CommandSpec("netstat", is_safe=True, allow_arguments=True, description="Network stats"),
    "ss": CommandSpec("ss", is_safe=True, allow_arguments=True, description="Socket stats"),
    "curl": CommandSpec("curl", is_safe=True, safe_flags=[
        CommandFlagSpec("-s", flag_type="flag", description="Silent mode"),
        CommandFlagSpec("-o", flag_type="flag", requires_value=True, allow_any_value=True, description="Output file"),
        CommandFlagSpec("-w", flag_type="flag", requires_value=True, allow_any_value=True, description="Write out"),
    ], allow_arguments=True, description="URL transfer"),
    "wget": CommandSpec("wget", is_safe=True, allow_arguments=True, description="Download files"),
    "tree": CommandSpec("tree", is_safe=True, allow_arguments=True, description="Directory tree"),
    "file": CommandSpec("file", is_safe=True, allow_arguments=True, description="File type"),
    "stat": CommandSpec("stat", is_safe=True, allow_arguments=True, description="File status"),
    "md5sum": CommandSpec("md5sum", is_safe=True, allow_arguments=True, description="MD5 hash"),
    "sha256sum": CommandSpec("sha256sum", is_safe=True, allow_arguments=True, description="SHA256 hash"),
    "javac": CommandSpec("javac", is_safe=True, allow_arguments=True, description="Java compiler"),
    "java": CommandSpec("java", is_safe=True, allow_arguments=True, description="Java runtime"),
    "go": CommandSpec("go", is_safe=True, safe_flags=[
        CommandFlagSpec("version", flag_type="subcommand", description="Show version"),
        CommandFlagSpec("env", flag_type="subcommand", allow_any_value=True, description="Go env"),
        CommandFlagSpec("list", flag_type="subcommand", allow_any_value=True, description="List packages"),
        CommandFlagSpec("vet", flag_type="subcommand", allow_any_value=True, description="Vet code"),
        CommandFlagSpec("build", flag_type="subcommand", allow_any_value=True, description="Build code"),
        CommandFlagSpec("test", flag_type="subcommand", allow_any_value=True, description="Test code"),
        CommandFlagSpec("run", flag_type="subcommand", allow_any_value=True, description="Run code"),
    ], description="Go toolchain"),
    "rustc": CommandSpec("rustc", is_safe=True, safe_flags=[
        CommandFlagSpec("--version", flag_type="flag", description="Show version"),
    ], allow_arguments=True, description="Rust compiler"),
    "cargo": CommandSpec("cargo", is_safe=True, safe_flags=[
        CommandFlagSpec("check", flag_type="subcommand", allow_any_value=True, description="Check code"),
        CommandFlagSpec("build", flag_type="subcommand", allow_any_value=True, description="Build code"),
        CommandFlagSpec("test", flag_type="subcommand", allow_any_value=True, description="Test code"),
        CommandFlagSpec("run", flag_type="subcommand", allow_any_value=True, description="Run code"),
        CommandFlagSpec("clippy", flag_type="subcommand", allow_any_value=True, description="Lint code"),
    ], description="Rust package manager"),
}


class CommandSafetyValidator:
    def __init__(self):
        self._allowlist = COMMAND_ALLOWLIST

    def validate_command(self, cmd: str) -> Tuple[bool, str, bool]:
        if not cmd or not cmd.strip():
            return True, "", False

        cmd = cmd.strip()
        if cmd.startswith("#!"):
            return False, "Shebang not allowed", False

        if "$(" in cmd or "`" in cmd:
            return False, "Command substitution not allowed in safety check", True

        if "&&" in cmd or "||" in cmd or "|" in cmd or ";" in cmd:
            parts = self._split_compound(cmd)
            for part in parts:
                safe, reason, classifiable = self.validate_command(part)
                if not safe:
                    return safe, reason, classifiable
            return True, "", False

        try:
            import shlex
            tokens = shlex.split(cmd, posix=True)
        except ValueError:
            tokens = cmd.split()

        if not tokens:
            return True, "", False

        base_cmd = os.path.basename(tokens[0]).lower()
        if base_cmd.endswith(".exe"):
            base_cmd = base_cmd[:-4]

        spec = self._allowlist.get(base_cmd)
        if spec and spec.is_safe:
            if spec.safe_flags and len(tokens) > 1:
                first_flag = tokens[1].lstrip("-")
                if first_flag in spec.safe_flags:
                    return True, "", False
                if spec.allow_arguments:
                    return True, "", False
                return True, "", False
            return True, "", False

        for dp in DENIED_COMMAND_PATTERNS:
            if dp.lower() in cmd.lower():
                return False, f"Dangerous command pattern: {dp}", True

        dangerous = ["sudo ", "runas ", "chmod 777", "icacls /grant Everyone",
                      "mkfs.", "dd if=", ":(){:|:&};:"]
        for pat in dangerous:
            if pat.lower() in cmd.lower():
                return False, f"Privilege escalation: {pat}", True

        return True, "", True

    def _split_compound(self, cmd: str) -> List[str]:
        import re
        parts = re.split(r'[;&|]{1,2}', cmd)
        return [p.strip() for p in parts if p.strip()]

    def is_read_only_command(self, cmd: str) -> bool:
        safe, _, _ = self.validate_command(cmd)
        return safe


class SafetyChecker:
    def __init__(self):
        self._cmd_validator = CommandSafetyValidator()

    def check(self, tool_name: str, tool_input: Dict) -> Tuple[bool, str, bool]:
        path = tool_input.get("file_path", tool_input.get("path", ""))
        cmd = tool_input.get("command", "")

        if path:
            for pp in PROTECTED_PATHS:
                if pp in path.replace("\\", "/"):
                    return False, f"Protected path: {pp}", False
            for dp in DENIED_PATHS_PATTERNS:
                if dp in path:
                    return False, f"Denied path pattern: {dp}", True

        if cmd and tool_name in EXECUTE_TOOLS:
            return self._cmd_validator.validate_command(cmd)

        return True, "", False


class AutoClassifier:
    def __init__(self, llm_adapter=None):
        self._llm_adapter = llm_adapter

    def classify(self, tool_name: str, tool_input: Dict,
                 mode: PermissionMode) -> Tuple[PermissionDecision, str]:
        if tool_name in SAFE_TOOLS:
            return PermissionDecision.ALLOW, f"Safe tool: {tool_name}"
        if tool_name in READ_ONLY_TOOLS:
            return PermissionDecision.ALLOW, f"Read-only tool: {tool_name}"

        if mode == PermissionMode.ACCEPT_EDITS:
            if tool_name in EDIT_TOOLS:
                path = tool_input.get("file_path", tool_input.get("path", ""))
                checker = SafetyChecker()
                safe, reason, _ = checker.check(tool_name, tool_input)
                if safe:
                    return PermissionDecision.ALLOW, f"acceptEdits: auto-accept edit"
                return PermissionDecision.DENY, f"acceptEdits: {reason}"
            if tool_name in EXECUTE_TOOLS:
                cmd = tool_input.get("command", "")
                if self._is_safe_command(cmd):
                    return PermissionDecision.ALLOW, "acceptEdits: safe command"
                return PermissionDecision.ASK, "acceptEdits: command needs approval"

        if mode == PermissionMode.PLAN:
            if tool_name in READ_ONLY_TOOLS or tool_name in ("WebFetch", "WebSearch"):
                return PermissionDecision.ALLOW, "plan: read-only allowed"
            return PermissionDecision.DENY, "plan: only read operations"

        if mode == PermissionMode.AUTO:
            if tool_name in EDIT_TOOLS:
                path = tool_input.get("file_path", tool_input.get("path", ""))
                checker = SafetyChecker()
                safe, reason, _ = checker.check(tool_name, tool_input)
                if safe:
                    return PermissionDecision.ALLOW, "auto: edit to safe path"
                return PermissionDecision.ASK, "auto: edit needs approval"
            if tool_name in EXECUTE_TOOLS:
                cmd = tool_input.get("command", "")
                if self._is_safe_command(cmd):
                    return PermissionDecision.ALLOW, "auto: safe command"
                return PermissionDecision.ASK, "auto: command needs approval"

        if self._llm_adapter:
            return self._classify_with_llm(tool_name, tool_input)

        return PermissionDecision.ASK, "Requires user approval"

    def _classify_with_llm(self, tool_name: str, tool_input: Dict) -> Tuple[PermissionDecision, str]:
        try:
            prompt = self._build_classifier_prompt(tool_name, tool_input)
            response = self._llm_adapter.chat(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You are a security classifier. Respond ONLY with 'ALLOW' or 'DENY' followed by a brief reason.",
                max_tokens=64,
                temperature=0.0,
            )
            content = response.get("content", "")
            if "ALLOW" in content.upper():
                return PermissionDecision.ALLOW, f"LLM classifier: approved"
            return PermissionDecision.DENY, f"LLM classifier: denied"
        except Exception:
            return PermissionDecision.DENY, "LLM classifier: error (fail-closed)"

    def _build_classifier_prompt(self, tool_name: str, tool_input: Dict) -> str:
        return (
            f"Tool: {tool_name}\n"
            f"Input: {json.dumps(tool_input, ensure_ascii=False)[:500]}\n"
            f"Is this operation safe to auto-approve? ALLOW or DENY."
        )

    def _is_safe_command(self, cmd: str) -> bool:
        if not cmd:
            return False
        cmd_lower = cmd.lower().strip()
        for dp in DENIED_COMMAND_PATTERNS:
            if dp.lower() in cmd_lower:
                return False
        dangerous = ["sudo ", "runas ", "chmod 777", "icacls /grant Everyone"]
        for pat in dangerous:
            if pat.lower() in cmd_lower:
                return False
        return True

    def get_risk_level(self, tool_name: str, tool_input: Dict) -> ToolRiskLevel:
        base_risk = TOOL_RISK_MAP.get(tool_name, ToolRiskLevel.MEDIUM)
        if tool_name in EXECUTE_TOOLS:
            cmd = tool_input.get("command", "")
            if not self._is_safe_command(cmd):
                return ToolRiskLevel.CRITICAL
        if tool_name in EDIT_TOOLS:
            path = tool_input.get("file_path", tool_input.get("path", ""))
            checker = SafetyChecker()
            safe, _, _ = checker.check(tool_name, tool_input)
            if not safe:
                return ToolRiskLevel.HIGH
        return base_risk


class PermissionPipeline:
    def __init__(self, rule_store: PermissionRuleStore, classifier: AutoClassifier,
                 safety_checker: SafetyChecker, denial_tracker: DenialTracker):
        self._rules = rule_store
        self._classifier = classifier
        self._safety = safety_checker
        self._denial_tracker = denial_tracker

    def evaluate(self, tool_name: str, tool_input: Dict,
                 mode: PermissionMode, session_id: str) -> PipelineResult:
        deny_rules = self._rules.get_deny_rules(tool_name)
        for rule in deny_rules:
            if self._rules.match_rule(rule, tool_name, tool_input):
                rule.hit_count += 1
                rule.last_used = datetime.utcnow().isoformat()
                return PipelineResult(
                    decision=PermissionDecision.DENY,
                    step=PipelineStep.STEP_1A_DENY_RULES,
                    reason=f"Denied by rule: {rule.rule_id}",
                    rule_id=rule.rule_id,
                    classifier_approvable=rule.classifier_approvable,
                    denial_record=self._make_denial(
                        session_id, tool_name, tool_input, mode,
                        DenialReasonCode.RULE_DENY,
                        f"Matched deny rule: {rule.rule_id}",
                        PipelineStep.STEP_1A_DENY_RULES.value,
                        rule.rule_id,
                    ),
                )

        ask_rules = self._rules.get_ask_rules(tool_name)
        for rule in ask_rules:
            if self._rules.match_rule(rule, tool_name, tool_input):
                rule.hit_count += 1
                rule.last_used = datetime.utcnow().isoformat()
                if rule.classifier_approvable and mode in (PermissionMode.AUTO, PermissionMode.ACCEPT_EDITS):
                    decision, reason = self._classifier.classify(tool_name, tool_input, mode)
                    if decision == PermissionDecision.ALLOW:
                        return PipelineResult(
                            decision=PermissionDecision.ALLOW,
                            step=PipelineStep.STEP_4_AUTO_CLASSIFIER,
                            reason=f"Classifier approved (ask rule {rule.rule_id} overridden)",
                            rule_id=rule.rule_id,
                        )
                return PipelineResult(
                    decision=PermissionDecision.ASK,
                    step=PipelineStep.STEP_1B_ASK_RULES,
                    reason=f"Ask rule: {rule.rule_id}",
                    rule_id=rule.rule_id,
                    classifier_approvable=rule.classifier_approvable,
                )

        if tool_name in SAFE_TOOLS:
            return PipelineResult(
                decision=PermissionDecision.ALLOW,
                step=PipelineStep.STEP_2B_ALWAYS_ALLOW,
                reason=f"Safe tool auto-allowed: {tool_name}",
            )

        if tool_name in EXECUTE_TOOLS:
            cmd = tool_input.get("command", "")
            if cmd:
                cmd_validator = CommandSafetyValidator()
                cmd_safe, cmd_reason, cmd_classifiable = cmd_validator.validate_command(cmd)
                if cmd_safe and not cmd_classifiable:
                    return PipelineResult(
                        decision=PermissionDecision.ALLOW,
                        step=PipelineStep.STEP_2B_ALWAYS_ALLOW,
                        reason=f"Command allowlist auto-allowed: {cmd.split()[0] if cmd.split() else cmd}",
                    )

        safe, reason, classifier_approvable = self._safety.check(tool_name, tool_input)
        if not safe and not classifier_approvable:
            return PipelineResult(
                decision=PermissionDecision.DENY,
                step=PipelineStep.STEP_1G_SAFETY_CHECK,
                reason=f"Safety check: {reason}",
                classifier_approvable=False,
                denial_record=self._make_denial(
                    session_id, tool_name, tool_input, mode,
                    DenialReasonCode.SAFETY_CHECK,
                    reason,
                    PipelineStep.STEP_1G_SAFETY_CHECK.value,
                ),
            )

        if mode == PermissionMode.BYPASS_PERMISSIONS:
            return PipelineResult(
                decision=PermissionDecision.ALLOW,
                step=PipelineStep.STEP_2A_BYPASS_MODE,
                reason="bypassPermissions mode",
            )

        if not safe and classifier_approvable:
            return PipelineResult(
                decision=PermissionDecision.DENY,
                step=PipelineStep.STEP_1G_SAFETY_CHECK,
                reason=f"Safety check: {reason}",
                classifier_approvable=True,
                denial_record=self._make_denial(
                    session_id, tool_name, tool_input, mode,
                    DenialReasonCode.SAFETY_CHECK,
                    reason,
                    PipelineStep.STEP_1G_SAFETY_CHECK.value,
                ),
            )

        allow_rules = self._rules.get_allow_rules(tool_name)
        for rule in allow_rules:
            if self._rules.match_rule(rule, tool_name, tool_input):
                rule.hit_count += 1
                rule.last_used = datetime.utcnow().isoformat()
                return PipelineResult(
                    decision=PermissionDecision.ALLOW,
                    step=PipelineStep.STEP_2B_ALWAYS_ALLOW,
                    reason=f"Allowed by rule: {rule.rule_id}",
                    rule_id=rule.rule_id,
                )

        if mode == PermissionMode.DONT_ASK:
            return PipelineResult(
                decision=PermissionDecision.DENY,
                step=PipelineStep.STEP_5_DONT_ASK,
                reason="dontAsk mode: auto-reject",
                denial_record=self._make_denial(
                    session_id, tool_name, tool_input, mode,
                    DenialReasonCode.MODE_DONT_ASK,
                    "dontAsk mode auto-reject",
                    PipelineStep.STEP_5_DONT_ASK.value,
                ),
            )

        if self._denial_tracker.should_escalate(session_id):
            state = self._denial_tracker.get_state(session_id)
            return PipelineResult(
                decision=PermissionDecision.ASK,
                step=PipelineStep.STEP_1F_CONTENT_RULES,
                reason=f"Escalated: {state.consecutive_denials} consecutive denials",
            )

        if mode in (PermissionMode.AUTO, PermissionMode.ACCEPT_EDITS):
            decision, reason = self._classifier.classify(tool_name, tool_input, mode)
            if decision == PermissionDecision.ALLOW:
                return PipelineResult(
                    decision=PermissionDecision.ALLOW,
                    step=PipelineStep.STEP_4_AUTO_CLASSIFIER,
                    reason=reason,
                )
            if decision == PermissionDecision.DENY:
                return PipelineResult(
                    decision=PermissionDecision.DENY,
                    step=PipelineStep.STEP_4_AUTO_CLASSIFIER,
                    reason=reason,
                    denial_record=self._make_denial(
                        session_id, tool_name, tool_input, mode,
                        DenialReasonCode.CLASSIFIER_DENY,
                        reason,
                        PipelineStep.STEP_4_AUTO_CLASSIFIER.value,
                    ),
                )

        return PipelineResult(
            decision=PermissionDecision.ASK,
            step=PipelineStep.STEP_7_INTERACTIVE,
            reason="Requires user approval",
        )

    def _make_denial(self, session_id: str, tool_name: str, tool_input: Dict,
                     mode: PermissionMode, reason_code: DenialReasonCode,
                     description: str, pipeline_step: str,
                     policy_rule_id: str = "") -> DenialRecord:
        path = tool_input.get("file_path", tool_input.get("path", ""))
        cmd = tool_input.get("command", "")
        return DenialRecord(
            record_id=f"denial_{uuid.uuid4().hex[:12]}",
            session_id=session_id,
            tool_name=tool_name,
            reason_code=reason_code,
            reason_description=description,
            resource_path=path or cmd or "",
            resource_attributes={"risk_level": self._classifier.get_risk_level(tool_name, tool_input).value},
            policy_rule_id=policy_rule_id,
            pipeline_step=pipeline_step,
            tool_input_summary=json.dumps(tool_input, ensure_ascii=False)[:200],
            risk_level=self._classifier.get_risk_level(tool_name, tool_input).value,
            mode_at_time=mode.value,
        )


class PermissionManager:
    def __init__(self, llm_adapter=None):
        self._rule_store = PermissionRuleStore()
        self._classifier = AutoClassifier(llm_adapter)
        self._safety = SafetyChecker()
        self._denial_tracker = DenialTracker()
        self._pipeline = PermissionPipeline(
            self._rule_store, self._classifier, self._safety, self._denial_tracker
        )
        self._pending: OrderedDict[str, PermissionRequest] = OrderedDict()
        self._session_modes: Dict[str, PermissionMode] = {}
        self._audit_log: List[PermissionAuditEntry] = []
        self._lock = threading.Lock()
        self._sse_listeners: Dict[str, List[Callable]] = {}
        self._global_mode = PermissionMode.DEFAULT
        self._max_audit_entries = 10000

    def set_llm_adapter(self, adapter):
        self._classifier = AutoClassifier(adapter)
        self._pipeline = PermissionPipeline(
            self._rule_store, self._classifier, self._safety, self._denial_tracker
        )

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
            for callbacks in self._sse_listeners.values():
                if callbacks:
                    return True
            return False

    def request_permission(self, session_id: str, tool_name: str,
                           tool_input: Dict[str, Any],
                           timeout: float = 120.0) -> str:
        mode = self.get_session_mode(session_id)
        risk_level = self._classifier.get_risk_level(tool_name, tool_input)

        pipeline_result = self._pipeline.evaluate(tool_name, tool_input, mode, session_id)

        if pipeline_result.decision == PermissionDecision.ALLOW:
            self._denial_tracker.record_success(session_id)
            request = PermissionRequest(
                request_id=f"perm_{uuid.uuid4().hex[:12]}",
                session_id=session_id,
                tool_name=tool_name,
                tool_input=tool_input,
                risk_level=risk_level,
                reason=pipeline_result.reason,
                pipeline_step=pipeline_result.step.value,
                auto_approved=True,
            )
            request.resolve(PermissionDecision.ALLOW)
            self._add_audit_entry(request, "pipeline_allowed", pipeline_result)
            return PermissionDecision.ALLOW.value

        if pipeline_result.decision == PermissionDecision.DENY:
            if pipeline_result.denial_record:
                self._denial_tracker.record_denial(pipeline_result.denial_record)
            request = PermissionRequest(
                request_id=f"perm_{uuid.uuid4().hex[:12]}",
                session_id=session_id,
                tool_name=tool_name,
                tool_input=tool_input,
                risk_level=risk_level,
                reason=pipeline_result.reason,
                pipeline_step=pipeline_result.step.value,
                auto_approved=False,
                denial_record=pipeline_result.denial_record,
            )
            request.resolve(PermissionDecision.DENY)
            self._add_audit_entry(request, "pipeline_denied", pipeline_result)
            self._notify_sse_listeners("permission_denied", {
                "request_id": request.request_id,
                "tool_name": tool_name,
                "reason": pipeline_result.reason,
                "reason_code": pipeline_result.denial_record.reason_code.value if pipeline_result.denial_record else "",
                "pipeline_step": pipeline_result.step.value,
            })
            return PermissionDecision.DENY.value

        has_ui = self.has_active_listeners()

        if not has_ui:
            return self._handle_no_ui(session_id, tool_name, tool_input,
                                      risk_level, mode, pipeline_result, timeout)

        request = PermissionRequest(
            request_id=f"perm_{uuid.uuid4().hex[:12]}",
            session_id=session_id,
            tool_name=tool_name,
            tool_input=tool_input,
            risk_level=risk_level,
            reason=pipeline_result.reason,
            pipeline_step=pipeline_result.step.value,
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
            "reason": pipeline_result.reason,
            "pipeline_step": pipeline_result.step.value,
            "options": request.options,
            "created_at": request.created_at,
        })

        if request.wait(timeout=timeout):
            with self._lock:
                self._pending.pop(request.request_id, None)

            if request.decision in (PermissionDecision.ALLOW, PermissionDecision.ALLOW_ALWAYS):
                self._denial_tracker.record_success(session_id)
            else:
                denial = DenialRecord(
                    record_id=f"denial_{uuid.uuid4().hex[:12]}",
                    session_id=session_id,
                    tool_name=tool_name,
                    reason_code=DenialReasonCode.TIMEOUT if request.decision is None else DenialReasonCode.RULE_DENY,
                    reason_description="User rejected" if request.decision else "Timeout",
                    resource_path=tool_input.get("file_path", tool_input.get("path", "")),
                    pipeline_step=pipeline_result.step.value,
                    tool_input_summary=json.dumps(tool_input, ensure_ascii=False)[:200],
                    risk_level=risk_level.value,
                    mode_at_time=mode.value,
                )
                self._denial_tracker.record_denial(denial)

            self._add_audit_entry(request, "user_resolved", pipeline_result)

            if request.decision == PermissionDecision.ALLOW_ALWAYS:
                self._add_trust_rule(tool_name, tool_input, PermissionDecision.ALLOW_ALWAYS)

            return request.decision.value if request.decision else PermissionDecision.DENY.value
        else:
            with self._lock:
                self._pending.pop(request.request_id, None)

            request.resolve(PermissionDecision.DENY)
            denial = DenialRecord(
                record_id=f"denial_{uuid.uuid4().hex[:12]}",
                session_id=session_id,
                tool_name=tool_name,
                reason_code=DenialReasonCode.TIMEOUT,
                reason_description=f"Permission request timed out after {timeout}s",
                resource_path=tool_input.get("file_path", tool_input.get("path", "")),
                pipeline_step=pipeline_result.step.value,
                tool_input_summary=json.dumps(tool_input, ensure_ascii=False)[:200],
                risk_level=risk_level.value,
                mode_at_time=mode.value,
            )
            self._denial_tracker.record_denial(denial)
            self._add_audit_entry(request, "timeout", pipeline_result)
            self._notify_sse_listeners("permission_timeout", {
                "request_id": request.request_id,
                "tool_name": tool_name,
            })
            return PermissionDecision.DENY.value

    def check_permission(self, session_id: str, tool_name: str,
                         tool_input: Dict[str, Any]) -> Dict[str, Any]:
        mode = self.get_session_mode(session_id)
        risk_level = self._classifier.get_risk_level(tool_name, tool_input)
        pipeline_result = self._pipeline.evaluate(tool_name, tool_input, mode, session_id)
        decision = pipeline_result.decision
        return {
            "success": True,
            "session_id": session_id,
            "tool_name": tool_name,
            "risk_level": risk_level.value,
            "mode": mode.value,
            "decision": decision.value,
            "auto_approved": decision == PermissionDecision.ALLOW,
            "reason": pipeline_result.reason,
            "pipeline_step": pipeline_result.step.value,
        }

    def _handle_no_ui(self, session_id: str, tool_name: str,
                      tool_input: Dict, risk_level: ToolRiskLevel,
                      mode: PermissionMode, pipeline_result: PipelineResult,
                      timeout: float) -> str:
        if mode in (PermissionMode.AUTO, PermissionMode.ACCEPT_EDITS):
            if risk_level in (ToolRiskLevel.SAFE, ToolRiskLevel.LOW, ToolRiskLevel.MEDIUM):
                self._denial_tracker.record_success(session_id)
                request = PermissionRequest(
                    request_id=f"perm_{uuid.uuid4().hex[:12]}",
                    session_id=session_id,
                    tool_name=tool_name,
                    tool_input=tool_input,
                    risk_level=risk_level,
                    reason="no_ui: auto-approved safe/low/medium risk",
                    pipeline_step=PipelineStep.STEP_6_NO_UI_FALLBACK.value,
                    auto_approved=True,
                )
                request.resolve(PermissionDecision.ALLOW)
                self._add_audit_entry(request, "no_ui_auto_approved", pipeline_result)
                return PermissionDecision.ALLOW.value

        denial = DenialRecord(
            record_id=f"denial_{uuid.uuid4().hex[:12]}",
            session_id=session_id,
            tool_name=tool_name,
            reason_code=DenialReasonCode.NO_UI_FALLBACK,
            reason_description="No UI available and risk too high for auto-approval",
            resource_path=tool_input.get("file_path", tool_input.get("path", "")),
            pipeline_step=PipelineStep.STEP_6_NO_UI_FALLBACK.value,
            tool_input_summary=json.dumps(tool_input, ensure_ascii=False)[:200],
            risk_level=risk_level.value,
            mode_at_time=mode.value,
        )
        self._denial_tracker.record_denial(denial)
        request = PermissionRequest(
            request_id=f"perm_{uuid.uuid4().hex[:12]}",
            session_id=session_id,
            tool_name=tool_name,
            tool_input=tool_input,
            risk_level=risk_level,
            reason="no_ui: rejected - high risk without UI",
            pipeline_step=PipelineStep.STEP_6_NO_UI_FALLBACK.value,
            auto_approved=False,
            denial_record=denial,
        )
        request.resolve(PermissionDecision.DENY)
        self._add_audit_entry(request, "no_ui_denied", pipeline_result)
        return PermissionDecision.DENY.value

    def respond_permission(self, request_id: str, decision: str) -> bool:
        with self._lock:
            request = self._pending.get(request_id)

        if not request or request.resolved:
            return False

        try:
            perm_decision = PermissionDecision(decision)
        except ValueError:
            if decision == "reject" or decision == "reject_always":
                perm_decision = PermissionDecision.DENY
            elif decision == "allow":
                perm_decision = PermissionDecision.ALLOW
            elif decision == "allow_always":
                perm_decision = PermissionDecision.ALLOW_ALWAYS
            else:
                return False

        request.resolve(perm_decision)

        self._notify_sse_listeners("permission_resolved", {
            "request_id": request_id,
            "decision": perm_decision.value,
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
        rule = PermissionRule(
            rule_id=f"rule_{uuid.uuid4().hex[:8]}",
            tool_name=tool_name,
            pattern=pattern,
            decision=decision,
            source=RuleSource.TRUST,
        )
        self._rule_store.add_rule(rule)

    def add_rule(self, rule: PermissionRule):
        self._rule_store.add_rule(rule)

    def remove_rule(self, rule_id: str) -> bool:
        return self._rule_store.remove_rule(rule_id)

    def get_rules(self, tool_name: str = None, source: str = None) -> List[Dict]:
        src = RuleSource(source) if source else None
        rules = self._rule_store.get_rules(tool_name, src)
        return [asdict(r) for r in rules]

    def _add_audit_entry(self, request: PermissionRequest, outcome: str,
                         pipeline_result: PipelineResult = None):
        denial_code = ""
        policy_rule_id = ""
        resource_path = ""
        pipeline_step = ""
        if pipeline_result:
            pipeline_step = pipeline_result.step.value
            if pipeline_result.denial_record:
                denial_code = pipeline_result.denial_record.reason_code.value
                policy_rule_id = pipeline_result.denial_record.policy_rule_id
                resource_path = pipeline_result.denial_record.resource_path
            policy_rule_id = policy_rule_id or pipeline_result.rule_id

        entry = PermissionAuditEntry(
            entry_id=f"audit_{uuid.uuid4().hex[:8]}",
            request_id=request.request_id,
            session_id=request.session_id,
            tool_name=request.tool_name,
            risk_level=request.risk_level.value,
            decision=request.decision.value if request.decision else "none",
            auto_approved=request.auto_approved,
            reason=f"{request.reason} [{outcome}]",
            pipeline_step=pipeline_step or request.pipeline_step,
            denial_reason_code=denial_code,
            policy_rule_id=policy_rule_id,
            resource_path=resource_path or request.tool_input.get("file_path", request.tool_input.get("path", "")),
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

    def get_denial_records(self, session_id: str = None, limit: int = 100,
                           reason_code: str = None) -> List[Dict]:
        rc = DenialReasonCode(reason_code) if reason_code else None
        return self._denial_tracker.get_records(session_id, limit, rc)

    def get_denial_stats(self, session_id: str = None) -> Dict[str, Any]:
        return self._denial_tracker.get_stats(session_id)

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total = len(self._audit_log)
            auto_approved = sum(1 for e in self._audit_log if e.auto_approved)
            user_approved = sum(1 for e in self._audit_log
                                if not e.auto_approved and e.decision in
                                (PermissionDecision.ALLOW.value, PermissionDecision.ALLOW_ALWAYS.value))
            rejected = sum(1 for e in self._audit_log
                           if e.decision == PermissionDecision.DENY.value)
            pending = len([r for r in self._pending.values() if not r.resolved])

        return {
            "total_requests": total,
            "auto_approved": auto_approved,
            "user_approved": user_approved,
            "rejected": rejected,
            "pending": pending,
            "global_mode": self._global_mode.value,
            "pipeline_version": "2.0",
            "denial_tracking": self._denial_tracker.get_stats(),
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
                        req.resolve(PermissionDecision.DENY)
            if session_id:
                self._pending = OrderedDict(
                    (k, v) for k, v in self._pending.items()
                    if v.session_id != session_id
                )
            else:
                self._pending.clear()

    def get_available_modes(self) -> List[Dict]:
        return [
            {"id": "auto", "name": "Auto", "description": "AI classifier auto-approves safe operations"},
            {"id": "default", "name": "Default", "description": "Ask for permission on risky operations"},
            {"id": "acceptEdits", "name": "Accept Edits", "description": "Auto-accept file edits, ask for commands"},
            {"id": "plan", "name": "Plan", "description": "Plan mode - read only, no modifications"},
            {"id": "dontAsk", "name": "Don't Ask", "description": "Never ask for permission (auto-reject all)"},
            {"id": "bypassPermissions", "name": "Bypass Permissions", "description": "Allow all operations without asking"},
        ]


permission_manager = PermissionManager()


def create_permission_manager(llm_adapter=None) -> PermissionManager:
    return PermissionManager(llm_adapter)
