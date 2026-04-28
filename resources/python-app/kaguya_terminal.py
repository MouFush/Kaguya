#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辉夜IDE 增强终端操作系统
参考 Claude Code 的 BashTool + commandSemantics + bashPermissions + shouldUseSandbox
实现：命令语义分析、安全沙箱决策、输出智能处理、权限规则匹配
"""

import os
import re
import subprocess
import fnmatch
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Set
from enum import Enum


class CommandCategory(Enum):
    SEARCH = "search"
    READ = "read"
    LIST = "list"
    SILENT = "silent"
    DESTRUCTIVE = "destructive"
    NETWORK = "network"
    PACKAGE = "package"
    UNKNOWN = "unknown"


@dataclass
class CommandSemantics:
    command: str
    exit_code_1_is_error: bool = True
    category: CommandCategory = CommandCategory.UNKNOWN


COMMAND_SEMANTICS_MAP: Dict[str, CommandSemantics] = {
    "grep": CommandSemantics("grep", exit_code_1_is_error=False, category=CommandCategory.SEARCH),
    "rg": CommandSemantics("rg", exit_code_1_is_error=False, category=CommandCategory.SEARCH),
    "ag": CommandSemantics("ag", exit_code_1_is_error=False, category=CommandCategory.SEARCH),
    "ack": CommandSemantics("ack", exit_code_1_is_error=False, category=CommandCategory.SEARCH),
    "find": CommandSemantics("find", exit_code_1_is_error=False, category=CommandCategory.SEARCH),
    "locate": CommandSemantics("locate", exit_code_1_is_error=False, category=CommandCategory.SEARCH),
    "diff": CommandSemantics("diff", exit_code_1_is_error=False, category=CommandCategory.READ),
    "test": CommandSemantics("test", exit_code_1_is_error=False, category=CommandCategory.SILENT),
    "cat": CommandSemantics("cat", category=CommandCategory.READ),
    "head": CommandSemantics("head", category=CommandCategory.READ),
    "tail": CommandSemantics("tail", category=CommandCategory.READ),
    "less": CommandSemantics("less", category=CommandCategory.READ),
    "more": CommandSemantics("more", category=CommandCategory.READ),
    "wc": CommandSemantics("wc", category=CommandCategory.READ),
    "stat": CommandSemantics("stat", category=CommandCategory.READ),
    "file": CommandSemantics("file", category=CommandCategory.READ),
    "ls": CommandSemantics("ls", category=CommandCategory.LIST),
    "tree": CommandSemantics("tree", category=CommandCategory.LIST),
    "du": CommandSemantics("du", category=CommandCategory.LIST),
    "mv": CommandSemantics("mv", category=CommandCategory.DESTRUCTIVE),
    "cp": CommandSemantics("cp", category=CommandCategory.SILENT),
    "rm": CommandSemantics("rm", category=CommandCategory.DESTRUCTIVE),
    "rmdir": CommandSemantics("rmdir", category=CommandCategory.DESTRUCTIVE),
    "mkdir": CommandSemantics("mkdir", category=CommandCategory.SILENT),
    "chmod": CommandSemantics("chmod", category=CommandCategory.SILENT),
    "chown": CommandSemantics("chown", category=CommandCategory.SILENT),
    "touch": CommandSemantics("touch", category=CommandCategory.SILENT),
    "ln": CommandSemantics("ln", category=CommandCategory.SILENT),
    "curl": CommandSemantics("curl", category=CommandCategory.NETWORK),
    "wget": CommandSemantics("wget", category=CommandCategory.NETWORK),
    "ssh": CommandSemantics("ssh", category=CommandCategory.NETWORK),
    "scp": CommandSemantics("scp", category=CommandCategory.NETWORK),
    "pip": CommandSemantics("pip", category=CommandCategory.PACKAGE),
    "npm": CommandSemantics("npm", category=CommandCategory.PACKAGE),
    "yarn": CommandSemantics("yarn", category=CommandCategory.PACKAGE),
    "cargo": CommandSemantics("cargo", category=CommandCategory.PACKAGE),
    "go": CommandSemantics("go", category=CommandCategory.PACKAGE),
    "git": CommandSemantics("git", category=CommandCategory.UNKNOWN),
}

DANGEROUS_COMMAND_PATTERNS = [
    r"rm\s+(-[a-zA-Z]*f[a-zA-Z]*\s+)?/(\s|$)",
    r"rm\s+(-[a-zA-Z]*f[a-zA-Z]*\s+)?~(\s|$)",
    r"mkfs\.",
    r"dd\s+if=/dev/zero",
    r"dd\s+if=/dev/urandom",
    r":\(\)\{\s*:\|:&\s*\}",
    r"format\s+[a-zA-Z]:",
    r"del\s+/[sS]\s+/[qQ]\s+[a-zA-Z]:",
    r">\s*/dev/sd",
    r"chmod\s+(-[a-zA-Z]*\s+)?000\s+/",
    r"chown\s+.*\s+/",
]

DANGEROUS_ENV_VARS = {
    "LD_PRELOAD", "DYLD_INSERT_LIBRARIES", "PYTHONPATH",
    "NODE_OPTIONS", "JAVA_TOOL_OPTIONS",
}

SAFE_ENV_VARS = {
    "PATH", "HOME", "USER", "LANG", "LC_ALL", "TERM",
    "NODE_ENV", "PYTHONIOENCODING", "PIP_NO_CACHE_DIR",
    "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY",
    "LANGCHAIN_API_KEY", "OPENAI_API_KEY",
}


@dataclass
class BashPermissionContext:
    allowed_commands: List[str] = field(default_factory=list)
    denied_commands: List[str] = field(default_factory=list)
    allowed_path_patterns: List[str] = field(default_factory=list)
    denied_path_patterns: List[str] = field(default_factory=list)
    read_only_mode: bool = False
    sandbox_enabled: bool = False
    sandbox_excluded: List[str] = field(default_factory=list)
    max_timeout: int = 120
    bypass_permissions: bool = False


@dataclass
class CommandAnalysis:
    base_command: str
    category: CommandCategory
    is_dangerous: bool
    is_read_only: bool
    involves_network: bool
    involves_packages: bool
    working_directory: Optional[str] = None
    target_paths: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class ExecutionResult:
    stdout: str
    stderr: str
    exit_code: int
    is_error: bool
    message: str = ""
    truncated: bool = False
    command: str = ""
    duration_ms: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class CommandAnalyzer:
    def extract_base_command(self, command: str) -> str:
        stripped = command.strip()
        while stripped.startswith("sudo "):
            stripped = stripped[5:].strip()

        env_var_pattern = re.compile(r'^[A-Za-z_]\w*=\S+\s+')
        while env_var_pattern.match(stripped):
            stripped = env_var_pattern.sub("", stripped, count=1)

        if "&&" in stripped or "||" in stripped or "|" in stripped or ";" in stripped:
            parts = re.split(r'[|;]|(?:&&)|(?:\|\|)', stripped)
            last = parts[-1].strip()
            return last.split()[0] if last.split() else ""

        return stripped.split()[0] if stripped.split() else ""

    def analyze_command(self, command: str) -> CommandAnalysis:
        base = self.extract_base_command(command)
        semantics = COMMAND_SEMANTICS_MAP.get(base)
        category = semantics.category if semantics else CommandCategory.UNKNOWN

        is_dangerous = False
        warnings = []

        for pattern in DANGEROUS_COMMAND_PATTERNS:
            if re.search(pattern, command):
                is_dangerous = True
                warnings.append(f"Dangerous command pattern detected")

        target_paths = []
        path_patterns = [
            re.compile(r'(?:^|\s)(?:[~./][\w./\-]*)'),
            re.compile(r'(?:^|\s)(?:/[a-zA-Z][\w./\-]*)'),
        ]
        for p in path_patterns:
            for m in p.finditer(command):
                path = m.group().strip()
                if path and not path.startswith("-"):
                    target_paths.append(path)

        involves_network = category == CommandCategory.NETWORK
        if not involves_network:
            network_indicators = ["curl", "wget", "ssh", "scp", "rsync", "nc ", "netcat"]
            for indicator in network_indicators:
                if indicator in command:
                    involves_network = True
                    break

        involves_packages = category == CommandCategory.PACKAGE

        is_read_only = category in {
            CommandCategory.SEARCH, CommandCategory.READ, CommandCategory.LIST
        }

        return CommandAnalysis(
            base_command=base,
            category=category,
            is_dangerous=is_dangerous,
            is_read_only=is_read_only,
            involves_network=involves_network,
            involves_packages=involves_packages,
            target_paths=target_paths,
            warnings=warnings,
        )

    def interpret_result(
        self,
        command: str,
        exit_code: int,
        stdout: str,
        stderr: str,
    ) -> Tuple[bool, str]:
        base = self.extract_base_command(command)
        semantics = COMMAND_SEMANTICS_MAP.get(base)

        if exit_code == 0:
            return False, ""

        if exit_code == 1 and semantics and not semantics.exit_code_1_is_error:
            return False, ""

        if exit_code >= 2:
            error_msg = stderr.strip() if stderr.strip() else stdout.strip()
            return True, f"Command failed (exit {exit_code}): {error_msg[:500]}"

        if exit_code == 1:
            return True, f"Command failed (exit 1): {stderr.strip()[:500] if stderr.strip() else 'Unknown error'}"

        return False, ""


class SafeTerminalExecutor:
    DEFAULT_STDOUT_LIMIT = 50_000
    DEFAULT_STDERR_LIMIT = 20_000
    DEFAULT_TIMEOUT = 120

    def __init__(self, permission_context: BashPermissionContext = None):
        self._perm_ctx = permission_context or BashPermissionContext()
        self._analyzer = CommandAnalyzer()
        self._execution_log: List[Dict] = []
        self._log_lock = threading.Lock()

    def _should_use_sandbox(self, command: str) -> bool:
        if not self._perm_ctx.sandbox_enabled:
            return False

        for excluded in self._perm_ctx.sandbox_excluded:
            if command.strip().startswith(excluded):
                return False

        analysis = self._analyzer.analyze_command(command)
        if analysis.is_read_only:
            return False

        return True

    def check_permissions(self, command: str) -> Tuple[bool, str]:
        if self._perm_ctx.bypass_permissions:
            return True, ""

        analysis = self._analyzer.analyze_command(command)

        if analysis.is_dangerous:
            return False, f"Dangerous command blocked: {analysis.warnings[0] if analysis.warnings else 'unsafe pattern detected'}"

        if self._perm_ctx.denied_commands:
            base = analysis.base_command
            for denied in self._perm_ctx.denied_commands:
                if fnmatch.fnmatch(base, denied):
                    return False, f"Command '{base}' is denied by permission settings"

        if self._perm_ctx.allowed_commands:
            base = analysis.base_command
            if not any(fnmatch.fnmatch(base, allowed) for allowed in self._perm_ctx.allowed_commands):
                return False, f"Command '{base}' is not in allowed list"

        if self._perm_ctx.read_only_mode and not analysis.is_read_only:
            return False, f"Command '{analysis.base_command}' is not read-only and read-only mode is enabled"

        for path in analysis.target_paths:
            for denied_pattern in self._perm_ctx.denied_path_patterns:
                if fnmatch.fnmatch(path, denied_pattern):
                    return False, f"Access denied to path: {path}"

        return True, ""

    def execute(
        self,
        command: str,
        timeout: int = None,
        working_dir: str = None,
        env: Dict[str, str] = None,
        capture_output: bool = True,
    ) -> ExecutionResult:
        allowed, msg = self.check_permissions(command)
        if not allowed:
            return ExecutionResult(
                stdout="", stderr=msg, exit_code=-1,
                is_error=True, message=msg, command=command,
            )

        effective_timeout = min(
            timeout or self.DEFAULT_TIMEOUT,
            self._perm_ctx.max_timeout,
        )
        effective_timeout = max(effective_timeout, 1)

        safe_env = dict(os.environ)
        if env:
            for k, v in env.items():
                if k not in DANGEROUS_ENV_VARS:
                    safe_env[k] = v

        cwd = working_dir or os.getcwd()

        start_time = time.time() if __import__("time") else 0

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=capture_output,
                text=True,
                timeout=effective_timeout,
                cwd=cwd,
                env=safe_env,
            )

            duration_ms = int((__import__("time").time() - start_time) * 1000)

            stdout = result.stdout or ""
            stderr = result.stderr or ""
            truncated = False

            if len(stdout) > self.DEFAULT_STDOUT_LIMIT:
                stdout = stdout[:self.DEFAULT_STDOUT_LIMIT] + f"\n... (truncated, {len(result.stdout)} total chars)"
                truncated = True

            if len(stderr) > self.DEFAULT_STDERR_LIMIT:
                stderr = stderr[:self.DEFAULT_STDERR_LIMIT] + f"\n... (truncated, {len(result.stderr)} total chars)"
                truncated = True

            is_error, error_msg = self._analyzer.interpret_result(
                command, result.returncode, stdout, stderr
            )

            exec_result = ExecutionResult(
                stdout=stdout,
                stderr=stderr,
                exit_code=result.returncode,
                is_error=is_error,
                message=error_msg,
                truncated=truncated,
                command=command,
                duration_ms=duration_ms,
                metadata={"sandbox": self._should_use_sandbox(command)},
            )

            self._log_execution(exec_result)
            return exec_result

        except subprocess.TimeoutExpired:
            duration_ms = int((__import__("time").time() - start_time) * 1000)
            return ExecutionResult(
                stdout="", stderr=f"Command timed out after {effective_timeout}s",
                exit_code=-1, is_error=True,
                message=f"Timeout after {effective_timeout}s",
                command=command, duration_ms=duration_ms,
            )
        except Exception as e:
            return ExecutionResult(
                stdout="", stderr=str(e),
                exit_code=-1, is_error=True,
                message=f"Execution error: {e}",
                command=command,
            )

    def _log_execution(self, result: ExecutionResult):
        entry = {
            "command": result.command[:200],
            "exit_code": result.exit_code,
            "is_error": result.is_error,
            "duration_ms": result.duration_ms,
            "truncated": result.truncated,
            "timestamp": __import__("time").time(),
        }
        with self._log_lock:
            self._execution_log.append(entry)
            if len(self._execution_log) > 1000:
                self._execution_log = self._execution_log[-500:]

    def get_execution_log(self, limit: int = 100) -> List[Dict]:
        with self._log_lock:
            return self._execution_log[-limit:]

    def get_command_suggestion(self, command: str) -> Optional[str]:
        analysis = self._analyzer.analyze_command(command)
        if analysis.is_dangerous:
            if "rm " in command:
                return "Consider using 'rm -i' for interactive deletion, or move to a temp directory first"
            if "dd " in command:
                return "Verify the 'of=' target carefully before running dd commands"
        if analysis.involves_packages:
            return "Package operations may affect the environment. Consider using virtual environments"
        return None
