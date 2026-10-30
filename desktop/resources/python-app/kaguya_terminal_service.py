import os
import shlex
import signal
import subprocess
import sys
import time

from kaguya_api_permissions import permission_service
from kaguya_workspace_security import WorkspaceAuthorizationError, authorize_path


def classify_command(command, shell=False):
    return permission_service.classify_command(command, shell=shell)


def _split_command(command):
    return shlex.split(command, posix=True)


def _normalize_args(args):
    if not args:
        return args
    exe = args[0].lower()
    if exe in ("python", "python.exe", "python3", "python3.exe"):
        args[0] = sys.executable
    if os.name == "nt":
        if exe == "dir":
            return [os.environ.get("COMSPEC", "cmd.exe"), "/c", "dir"] + args[1:]
        if exe == "pwd":
            return [os.environ.get("COMSPEC", "cmd.exe"), "/c", "cd"] + args[1:]
        if exe == "type":
            return [os.environ.get("COMSPEC", "cmd.exe"), "/c", "type"] + args[1:]
    return args


def kill_process_tree(proc):
    if proc.poll() is not None:
        return
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/pid", str(proc.pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
        else:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def execute_command(command, working_dir, workspace_path, user_info=None, timeout=30, shell=False, session_id="", device_id=""):
    try:
        safe_cwd = authorize_path(working_dir or workspace_path, workspace_path, user_info=user_info, must_exist=True)
    except WorkspaceAuthorizationError as exc:
        permission = permission_service.check("execute_command", {"command": command, "shell": shell}, session_id=session_id)
        return {
            "success": False,
            "error": "working_dir_outside_workspace",
            "detail": str(exc),
            "permission": permission.to_dict(),
            "exit_code": None,
        }
    permission = permission_service.check("execute_command", {"command": command, "shell": shell, "working_dir": safe_cwd}, session_id=session_id)
    if not permission.allowed:
        return {
            "success": False,
            "error": "permission_denied",
            "permission": permission.to_dict(),
            "exit_code": None,
            "command": command,
            "working_dir": safe_cwd,
        }
    try:
        timeout = max(1, min(int(timeout), 120))
    except Exception:
        timeout = 30
    if shell:
        return {
            "success": False,
            "error": "shell_mode_requires_confirmation",
            "permission": permission.to_dict(),
            "exit_code": None,
            "command": command,
            "working_dir": safe_cwd,
        }
    try:
        args = _normalize_args(_split_command(command))
    except ValueError as exc:
        return {"success": False, "error": "invalid_command", "detail": str(exc), "permission": permission.to_dict(), "exit_code": None}
    if not args:
        return {"success": False, "error": "empty_command", "permission": permission.to_dict(), "exit_code": None}
    creationflags = 0
    preexec_fn = None
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        preexec_fn = os.setsid
    started = time.time()
    proc = subprocess.Popen(
        args,
        shell=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=safe_cwd,
        creationflags=creationflags,
        preexec_fn=preexec_fn,
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
        timed_out = False
    except subprocess.TimeoutExpired:
        timed_out = True
        kill_process_tree(proc)
        stdout, stderr = proc.communicate()
    output = (stdout or "")[:8000]
    if stderr:
        output += ("\nSTDERR:\n" + stderr[:3000])
    if timed_out:
        output = f"Command timed out after {timeout} seconds\n" + output
    return {
        "success": proc.returncode == 0 and not timed_out,
        "output": output.strip() or "(no output)",
        "exit_code": -1 if timed_out else proc.returncode,
        "timed_out": timed_out,
        "duration_ms": int((time.time() - started) * 1000),
        "command": command,
        "args": args,
        "working_dir": safe_cwd,
        "permission": permission.to_dict(),
    }
