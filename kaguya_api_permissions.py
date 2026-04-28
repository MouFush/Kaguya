import re
import uuid
from dataclasses import dataclass, asdict


RISK_LOW = "low"
RISK_MEDIUM = "medium"
RISK_HIGH = "high"
RISK_CRITICAL = "critical"


@dataclass
class PermissionResult:
    allowed: bool
    reason: str
    risk_level: str
    requires_confirmation: bool = False
    permission_id: str = None
    audit_id: str = None

    def to_dict(self):
        return asdict(self)


class PermissionService:
    def __init__(self):
        self._pending = {}

    def check(self, action, payload=None, session_id="", permission_token=None):
        payload = payload or {}
        risk, reason = self.classify_action(action, payload)
        audit_id = "aud_" + uuid.uuid4().hex[:12]
        if risk == RISK_CRITICAL:
            return PermissionResult(False, reason, risk, True, audit_id=audit_id)
        if risk in (RISK_MEDIUM, RISK_HIGH):
            permission_id = "perm_" + uuid.uuid4().hex[:12]
            self._pending[permission_id] = {"action": action, "payload": payload, "session_id": session_id, "risk_level": risk}
            return PermissionResult(False, reason, risk, True, permission_id=permission_id, audit_id=audit_id)
        return PermissionResult(True, reason, risk, False, audit_id=audit_id)

    def classify_action(self, action, payload):
        if action == "execute_command":
            return self.classify_command(payload.get("command", ""), bool(payload.get("shell")))
        if action in ("write_file", "delete_file", "create_directory", "import_files", "run_project", "compile"):
            return RISK_HIGH, f"{action} modifies files, runs code, or changes project state"
        if action in ("read_file", "file_tree"):
            return RISK_LOW, "read-only workspace access"
        if action in ("web_fetch", "open_external"):
            return RISK_MEDIUM, "network or external application access"
        return RISK_MEDIUM, "unknown action requires confirmation"

    def classify_command(self, command, shell=False):
        cmd = (command or "").strip()
        lower = cmd.lower()
        if not cmd:
            return RISK_LOW, "empty command"
        critical_patterns = [
            r"\brm\s+(-rf|-fr|-r|-f)\b",
            r"\bdel\s+(/s|/f|/q|\*)",
            r"\bformat\s+[a-z]:",
            r"\bshutdown\b|\breboot\b|\bhalt\b|\bpoweroff\b",
            r"\breg\s+(add|delete|import|save|restore|load|unload)\b",
            r"\bcurl\b.*\|\s*(sh|bash|powershell|pwsh)",
            r"\bpowershell\b.*(invoke-webrequest|iwr|downloadstring|frombase64string)",
        ]
        if shell:
            return RISK_HIGH, "shell mode can interpret compound commands"
        if any(re.search(pattern, lower) for pattern in critical_patterns):
            return RISK_CRITICAL, "critical destructive or download-execute command"
        if re.search(r"(\|\||&&|;|`|\$\(|>\s*[^&]|<)", cmd):
            return RISK_HIGH, "compound shell syntax is not allowed without explicit shell confirmation"
        parts = lower.split()
        exe = parts[0] if parts else ""
        read_only = {"ls", "dir", "pwd", "cd", "type", "cat", "python", "python.exe", "python3", "node", "node.exe", "npm", "git"}
        if exe in {"python", "python.exe", "python3"} and any(p.endswith((".py", ".pyw")) for p in parts[1:]):
            return RISK_HIGH, "executing scripts can modify files or run arbitrary code"
        if exe == "node" and any(p.endswith((".js", ".mjs", ".cjs")) for p in parts[1:]):
            return RISK_HIGH, "executing scripts can modify files or run arbitrary code"
        if exe in {"pip", "pip3", "uv", "poetry", "pnpm", "npm", "yarn"} and any(p in parts for p in ("install", "add", "update", "remove")):
            return RISK_HIGH, "dependency installation changes environment and may run scripts"
        if exe == "git" and len(parts) > 1 and parts[1] in {"commit", "push", "pull", "reset", "checkout", "clean", "merge", "rebase", "apply"}:
            return RISK_HIGH, "git mutation or network command requires confirmation"
        if exe in {"pytest", "unittest", "cargo", "mvn", "gradle"} or (exe == "npm" and len(parts) > 1 and parts[1] in {"test", "run"}):
            return RISK_MEDIUM, "build/test command requires confirmation"
        if exe in read_only:
            if "--version" in parts or "-v" in parts or exe in {"ls", "dir", "pwd", "cd", "type", "cat"}:
                return RISK_LOW, "read-only command"
        return RISK_HIGH, "command is not in the read-only allowlist"


permission_service = PermissionService()
