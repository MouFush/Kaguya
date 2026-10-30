#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辉夜IDE 增强文件操作系统 v2
参考 Claude Code 的 FileReadTool/FileEditTool/FileWriteTool + fileStateCache + fileHistory
实现：安全读写、LRU文件状态缓存(mtime失效)、差异追踪、并发安全、编码检测、
     路径智能显示、相似文件查找、目录树渲染、文件历史快照、范围读取
"""

import fnmatch
import hashlib
import os
import shutil
import sys
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Set, Tuple


def _default_runtime_root():
    configured = os.environ.get("KAGUYA_RUNTIME_DIR") or os.environ.get("KAGUYA_USER_DATA_DIR")
    if configured:
        return os.path.realpath(os.path.abspath(configured))
    if os.name == "nt":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, "KaguyaIDE", "python-app")
    if sys.platform == "darwin":
        return os.path.join(os.path.expanduser("~"), "Library", "Application Support", "KaguyaIDE", "python-app")
    base = os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
    return os.path.join(base, "kaguyaide", "python-app")


KAGUYA_RUNTIME_DIR = _default_runtime_root()


@dataclass
class FileState:
    content: str
    timestamp: float
    offset: Optional[int] = None
    limit: Optional[int] = None
    encoding: str = "utf-8"
    line_count: int = 0
    size_bytes: int = 0
    content_hash: str = ""
    is_partial_view: bool = False
    mtime: float = 0.0
    line_endings: str = "lf"


@dataclass
class FileHistorySnapshot:
    file_path: str
    version: int
    timestamp: float
    content_hash: str
    line_count: int
    backup_path: Optional[str] = None


class FileStateCache:
    DEFAULT_MAX_ENTRIES = 1000
    DEFAULT_MAX_SIZE_BYTES = 50 * 1024 * 1024

    def __init__(self, max_entries: int = None, max_size_bytes: int = None):
        self._cache: OrderedDict[str, FileState] = OrderedDict()
        self._max_entries = max_entries or self.DEFAULT_MAX_ENTRIES
        self._max_size_bytes = max_size_bytes or self.DEFAULT_MAX_SIZE_BYTES
        self._current_size = 0
        self._lock = threading.Lock()

    def _normalize_path(self, path: str) -> str:
        return os.path.normpath(os.path.abspath(path))

    def _entry_size(self, state: FileState) -> int:
        return len(state.content.encode("utf-8")) if state.content else 1

    def get(self, path: str) -> Optional[FileState]:
        key = self._normalize_path(path)
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
        return None

    def get_if_fresh(self, path: str) -> Optional[FileState]:
        key = self._normalize_path(path)
        with self._lock:
            if key in self._cache:
                state = self._cache[key]
                try:
                    current_mtime = os.path.getmtime(key)
                    if state.mtime > 0 and abs(current_mtime - state.mtime) < 0.001:
                        self._cache.move_to_end(key)
                        return state
                    else:
                        self._current_size -= self._entry_size(state)
                        del self._cache[key]
                        return None
                except OSError:
                    self._current_size -= self._entry_size(state)
                    del self._cache[key]
                    return None
        return None

    def put(self, path: str, state: FileState):
        key = self._normalize_path(path)
        entry_size = self._entry_size(state)

        with self._lock:
            if key in self._cache:
                old_size = self._entry_size(self._cache[key])
                self._current_size -= old_size
                del self._cache[key]

            while len(self._cache) >= self._max_entries:
                self._evict_one()

            while self._current_size + entry_size > self._max_size_bytes and self._cache:
                self._evict_one()

            self._cache[key] = state
            self._current_size += entry_size

    def invalidate(self, path: str):
        key = self._normalize_path(path)
        with self._lock:
            if key in self._cache:
                self._current_size -= self._entry_size(self._cache[key])
                del self._cache[key]

    def _evict_one(self):
        if self._cache:
            key, state = self._cache.popitem(last=False)
            self._current_size -= self._entry_size(state)

    def clear(self):
        with self._lock:
            self._cache.clear()
            self._current_size = 0

    def keys(self) -> List[str]:
        with self._lock:
            return list(self._cache.keys())

    def clone(self) -> "FileStateCache":
        new_cache = FileStateCache(self._max_entries, self._max_size_bytes)
        with self._lock:
            for k, v in self._cache.items():
                new_cache._cache[k] = FileState(
                    content=v.content,
                    timestamp=v.timestamp,
                    offset=v.offset,
                    limit=v.limit,
                    encoding=v.encoding,
                    line_count=v.line_count,
                    size_bytes=v.size_bytes,
                    content_hash=v.content_hash,
                    is_partial_view=v.is_partial_view,
                    mtime=v.mtime,
                    line_endings=v.line_endings,
                )
        return new_cache


class FileHistory:
    MAX_SNAPSHOTS = 100
    MAX_BACKUP_DIR_SIZE = 200 * 1024 * 1024

    def __init__(self, backup_dir: str = None):
        self._snapshots: Dict[str, List[FileHistorySnapshot]] = {}
        self._sequence = 0
        self._lock = threading.Lock()
        self._backup_dir = backup_dir or os.path.join(
            KAGUYA_RUNTIME_DIR, ".kaguya_file_history"
        )
        os.makedirs(self._backup_dir, exist_ok=True)

    def _backup_file_path(self, file_path: str, version: int) -> str:
        path_hash = hashlib.sha256(file_path.encode("utf-8")).hexdigest()[:16]
        return os.path.join(self._backup_dir, f"{path_hash}@v{version}")

    def track_edit(
        self, file_path: str, content_before: str, content_after: str
    ) -> Optional[int]:
        file_path = os.path.normpath(os.path.abspath(file_path))
        with self._lock:
            self._sequence += 1
            version = self._sequence

            before_hash = _compute_content_hash(content_before)
            after_hash = _compute_content_hash(content_after)

            backup_path = self._backup_file_path(file_path, version)
            try:
                with open(backup_path, "w", encoding="utf-8") as f:
                    f.write(content_before)
            except Exception:
                backup_path = None

            snapshot = FileHistorySnapshot(
                file_path=file_path,
                version=version,
                timestamp=time.time(),
                content_hash=before_hash,
                line_count=content_before.count("\n") + 1,
                backup_path=backup_path,
            )

            if file_path not in self._snapshots:
                self._snapshots[file_path] = []
            self._snapshots[file_path].append(snapshot)

            if len(self._snapshots[file_path]) > self.MAX_SNAPSHOTS:
                removed = self._snapshots[file_path].pop(0)
                if removed.backup_path and os.path.exists(removed.backup_path):
                    try:
                        os.remove(removed.backup_path)
                    except Exception:
                        pass

            return version

    def rewind(self, file_path: str, version: int) -> Tuple[bool, Optional[str]]:
        file_path = os.path.normpath(os.path.abspath(file_path))
        with self._lock:
            snapshots = self._snapshots.get(file_path, [])
            target = None
            for snap in snapshots:
                if snap.version == version and snap.backup_path:
                    target = snap
                    break

            if not target or not os.path.exists(target.backup_path):
                return False, f"Snapshot v{version} not found or backup missing"

        try:
            with open(target.backup_path, "r", encoding="utf-8") as f:
                content = f.read()
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True, None
        except Exception as e:
            return False, f"Rewind failed: {e}"

    def get_history(self, file_path: str) -> List[Dict[str, Any]]:
        file_path = os.path.normpath(os.path.abspath(file_path))
        with self._lock:
            snapshots = self._snapshots.get(file_path, [])
            return [
                {
                    "version": s.version,
                    "timestamp": s.timestamp,
                    "content_hash": s.content_hash,
                    "line_count": s.line_count,
                    "has_backup": s.backup_path and os.path.exists(s.backup_path),
                }
                for s in snapshots
            ]


BLOCKED_DEVICE_PATHS = {
    "/dev/zero", "/dev/random", "/dev/urandom", "/dev/full",
    "/dev/stdin", "/dev/tty", "/dev/console",
}

SENSITIVE_PATH_PATTERNS = [
    "**/.ssh/**", "**/.gnupg/**", "**/.env", "**/.aws/**",
    "**/credentials*", "**/secret*", "**/*_key*", "**/id_rsa*",
    "**/id_ed25519*", "**/.gitconfig", "**/.npmrc",
]

WINDOWS_BLOCKED_PREFIXES = [
    "\\\\?", "\\\\?", "CON.", "PRN.", "AUX.", "NUL.",
]

COMMON_EXTENSIONS = {
    "python": [".py", ".pyw", ".pyi", ".pyx"],
    "javascript": [".js", ".jsx", ".mjs", ".cjs"],
    "typescript": [".ts", ".tsx", ".d.ts"],
    "java": [".java", ".kt", ".kts"],
    "c": [".c", ".h"],
    "cpp": [".cpp", ".cc", ".cxx", ".hpp", ".hxx"],
    "rust": [".rs"],
    "go": [".go"],
    "ruby": [".rb"],
    "php": [".php"],
    "swift": [".swift"],
    "html": [".html", ".htm"],
    "css": [".css", ".scss", ".sass", ".less"],
    "json": [".json"],
    "yaml": [".yaml", ".yml"],
    "xml": [".xml", ".xsl", ".xsd"],
    "markdown": [".md", ".mdx"],
    "sql": [".sql"],
    "shell": [".sh", ".bash", ".zsh"],
    "powershell": [".ps1", ".psm1"],
    "dockerfile": ["Dockerfile"],
    "config": [".ini", ".cfg", ".conf", ".toml"],
}


def _is_blocked_path(path: str) -> bool:
    norm = os.path.normpath(path)
    for blocked in BLOCKED_DEVICE_PATHS:
        if norm.startswith(blocked):
            return True
    if os.name == "nt":
        upper = norm.upper()
        for prefix in WINDOWS_BLOCKED_PREFIXES:
            if upper.startswith(prefix.upper()):
                return True
    return False


def _is_sensitive_path(path: str) -> bool:
    norm = os.path.normpath(path)
    for pattern in SENSITIVE_PATH_PATTERNS:
        if fnmatch.fnmatch(norm, pattern):
            return True
    return False


def _detect_encoding(file_path: str) -> str:
    try:
        with open(file_path, "rb") as f:
            raw = f.read(4096)
        if not raw:
            return "utf-8"
        if raw.startswith(b"\xef\xbb\xbf"):
            return "utf-8-sig"
        if raw.startswith(b"\xff\xfe"):
            return "utf-16-le"
        if raw.startswith(b"\xfe\xff"):
            return "utf-16-be"
        try:
            raw.decode("utf-8")
            return "utf-8"
        except UnicodeDecodeError:
            return "gbk" if any(b > 0x80 for b in raw[:512]) else "latin-1"
    except Exception:
        return "utf-8"


def _detect_line_endings(content: str) -> str:
    crlf = content.count("\r\n")
    lf = content.count("\n") - crlf
    return "crlf" if crlf > lf else "lf"


def _compute_content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def get_display_path(file_path: str, cwd: str = None) -> str:
    file_path = os.path.normpath(os.path.abspath(file_path))
    cwd = os.path.normpath(os.path.abspath(cwd or os.getcwd()))

    try:
        rel = os.path.relpath(file_path, cwd)
        if not rel.startswith(".."):
            return rel
    except ValueError:
        pass

    home = os.path.expanduser("~")
    if file_path.startswith(home):
        return "~" + file_path[len(home):]

    return file_path


def find_similar_file(file_path: str, cwd: str = None) -> Optional[str]:
    if os.path.exists(file_path):
        return file_path

    base, ext = os.path.splitext(file_path)
    dir_name = os.path.dirname(file_path)
    file_name_no_ext = os.path.basename(base)

    for lang, extensions in COMMON_EXTENSIONS.items():
        if ext.lower() in [e.lower() for e in extensions]:
            for alt_ext in extensions:
                if alt_ext.lower() == ext.lower():
                    continue
                candidate = base + alt_ext
                if os.path.exists(candidate):
                    return candidate

    if cwd and not os.path.isabs(file_path):
        abs_path = os.path.join(cwd, file_path)
        if os.path.exists(abs_path):
            return abs_path

    return None


def suggest_path_under_cwd(file_path: str, cwd: str = None) -> Optional[str]:
    if os.path.exists(file_path):
        return file_path

    cwd = cwd or os.getcwd()
    basename = os.path.basename(file_path)

    for root, dirs, files in os.walk(cwd):
        if basename in files:
            return os.path.join(root, basename)
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "node_modules" and d != "__pycache__"]

    return None


def render_directory_tree(
    root_path: str,
    max_depth: int = 3,
    ignore_patterns: List[str] = None,
    max_entries: int = 200,
) -> str:
    if not os.path.isdir(root_path):
        return f"Not a directory: {root_path}"

    default_ignores = [
        ".git", "__pycache__", "node_modules", ".venv", "venv",
        ".idea", ".vscode", "dist", "build", ".next", ".nuxt",
        "target", ".gradle", ".cache", "*.pyc", ".DS_Store",
    ]
    ignore = set(default_ignores + (ignore_patterns or []))

    lines = [os.path.basename(root_path) + "/"]
    entry_count = 0

    def _should_ignore(name: str) -> bool:
        for pattern in ignore:
            if fnmatch.fnmatch(name, pattern):
                return True
        return False

    def _render_recursive(path: str, prefix: str, depth: int):
        nonlocal entry_count
        if depth > max_depth or entry_count >= max_entries:
            lines.append(f"{prefix}... (truncated)")
            return

        try:
            entries = sorted(os.listdir(path))
        except PermissionError:
            lines.append(f"{prefix}[permission denied]")
            return

        dirs = []
        files = []
        for e in entries:
            if _should_ignore(e):
                continue
            full = os.path.join(path, e)
            if os.path.isdir(full):
                dirs.append(e)
            else:
                files.append(e)

        all_items = dirs + files
        for i, item in enumerate(all_items):
            if entry_count >= max_entries:
                lines.append(f"{prefix}... ({len(all_items) - i} more)")
                return

            is_last = (i == len(all_items) - 1)
            connector = "└── " if is_last else "├── "
            child_prefix = "    " if is_last else "│   "

            full = os.path.join(path, item)
            if os.path.isdir(full):
                lines.append(f"{prefix}{connector}{item}/")
                entry_count += 1
                _render_recursive(full, prefix + child_prefix, depth + 1)
            else:
                size = 0
                try:
                    size = os.path.getsize(full)
                except Exception:
                    pass
                size_str = _format_size(size)
                lines.append(f"{prefix}{connector}{item}  ({size_str})")
                entry_count += 1

    _render_recursive(root_path, "", 0)
    return "\n".join(lines)


def _format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f}KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f}MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f}GB"


class SafeFileOperations:
    MAX_READ_SIZE = 50 * 1024 * 1024
    MAX_EDIT_SIZE = 1024 * 1024 * 1024
    DEFAULT_READ_LIMIT = 2000
    WRITE_VERIFY_RETRY = 3

    def __init__(
        self,
        state_cache: FileStateCache = None,
        file_history: FileHistory = None,
    ):
        self._cache = state_cache or FileStateCache()
        self._history = file_history or FileHistory()
        self._write_locks: Dict[str, threading.Lock] = {}
        self._locks_mutex = threading.Lock()

    def _get_lock(self, path: str) -> threading.Lock:
        key = os.path.normpath(os.path.abspath(path))
        with self._locks_mutex:
            if key not in self._write_locks:
                self._write_locks[key] = threading.Lock()
            return self._write_locks[key]

    def _resolve_path(self, file_path: str, working_dir: str = None) -> str:
        if not os.path.isabs(file_path):
            file_path = os.path.join(working_dir or os.getcwd(), file_path)
        return os.path.normpath(os.path.abspath(file_path))

    def read_file(
        self,
        file_path: str,
        offset: int = 1,
        limit: int = None,
        working_dir: str = None,
    ) -> Tuple[Optional[str], Optional[str]]:
        file_path = self._resolve_path(file_path, working_dir)

        if _is_blocked_path(file_path):
            return None, f"Blocked device path: {file_path}"

        if not os.path.exists(file_path):
            cached = self._cache.get(file_path)
            if cached:
                return cached.content, None
            suggestion = suggest_path_under_cwd(file_path, working_dir)
            msg = f"File not found: {file_path}"
            if suggestion:
                msg += f"\nDid you mean: {get_display_path(suggestion, working_dir)}?"
            similar = find_similar_file(file_path, working_dir)
            if similar and similar != suggestion:
                msg += f"\nSimilar file: {get_display_path(similar, working_dir)}"
            return None, msg

        if os.path.isdir(file_path):
            return render_directory_tree(file_path), None

        try:
            file_size = os.path.getsize(file_path)
            if file_size > self.MAX_READ_SIZE:
                return None, f"File too large ({file_size} bytes). Use offset/limit."

            cached = self._cache.get_if_fresh(file_path)
            if cached and not cached.is_partial_view and offset == 1 and limit is None:
                lines = cached.content.split("\n")
                total_lines = len(lines)
                numbered = []
                for i, line in enumerate(lines, start=1):
                    numbered.append(f"{i:>6}\u2192{line}")
                return "\n".join(numbered), None

            encoding = _detect_encoding(file_path)
            mtime = os.path.getmtime(file_path)

            with open(file_path, "r", encoding=encoding, errors="replace") as f:
                all_lines = f.readlines()

            total_lines = len(all_lines)
            effective_limit = limit or self.DEFAULT_READ_LIMIT
            start = max(0, offset - 1)
            end = min(total_lines, start + effective_limit)
            selected = all_lines[start:end]

            numbered = []
            for i, line in enumerate(selected, start=start + 1):
                numbered.append(f"{i:>6}\u2192{line.rstrip()}")

            result = "\n".join(numbered)
            if end < total_lines:
                result += f"\n... ({total_lines - end} more lines)"

            content_raw = "".join(all_lines)
            line_endings = _detect_line_endings(content_raw)
            state = FileState(
                content=content_raw,
                timestamp=time.time(),
                offset=offset,
                limit=effective_limit,
                encoding=encoding,
                line_count=total_lines,
                size_bytes=file_size,
                content_hash=_compute_content_hash(content_raw),
                is_partial_view=(end - start) < total_lines,
                mtime=mtime,
                line_endings=line_endings,
            )
            self._cache.put(file_path, state)

            return result, None

        except PermissionError:
            return None, f"Permission denied: {file_path}"
        except Exception as e:
            return None, f"Error reading file: {e}"

    def read_file_range(
        self,
        file_path: str,
        start_line: int,
        end_line: int,
        working_dir: str = None,
    ) -> Tuple[Optional[str], Optional[str]]:
        return self.read_file(
            file_path,
            offset=start_line,
            limit=end_line - start_line + 1,
            working_dir=working_dir,
        )

    def write_file(
        self,
        file_path: str,
        content: str,
        working_dir: str = None,
        create_dirs: bool = True,
    ) -> Tuple[bool, Optional[str]]:
        file_path = self._resolve_path(file_path, working_dir)

        if _is_blocked_path(file_path):
            return False, f"Cannot write to blocked path: {file_path}"

        lock = self._get_lock(file_path)
        with lock:
            try:
                content_before = ""
                if os.path.exists(file_path):
                    try:
                        enc = _detect_encoding(file_path)
                        with open(file_path, "r", encoding=enc, errors="replace") as f:
                            content_before = f.read()
                    except Exception:
                        pass

                if create_dirs:
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)

                line_endings = "lf"
                if content_before:
                    line_endings = _detect_line_endings(content_before)
                if line_endings == "crlf":
                    content = content.replace("\r\n", "\n").replace("\n", "\r\n")

                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)

                for attempt in range(self.WRITE_VERIFY_RETRY):
                    with open(file_path, "r", encoding="utf-8") as f:
                        written = f.read()
                    verify_content = written.replace("\r\n", "\n") if line_endings == "crlf" else written
                    if verify_content == content.replace("\r\n", "\n"):
                        break
                    if attempt == self.WRITE_VERIFY_RETRY - 1:
                        return False, f"Write verification failed after {self.WRITE_VERIFY_RETRY} attempts"
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(content)

                if content_before and content_before != content:
                    self._history.track_edit(file_path, content_before, content)

                mtime = 0.0
                try:
                    mtime = os.path.getmtime(file_path)
                except Exception:
                    pass

                state = FileState(
                    content=content,
                    timestamp=time.time(),
                    encoding="utf-8",
                    line_count=content.count("\n") + 1,
                    size_bytes=len(content.encode("utf-8")),
                    content_hash=_compute_content_hash(content),
                    mtime=mtime,
                    line_endings=line_endings,
                )
                self._cache.put(file_path, state)

                return True, None

            except PermissionError:
                return False, f"Permission denied: {file_path}"
            except Exception as e:
                return False, f"Error writing file: {e}"

    def edit_file(
        self,
        file_path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,
        working_dir: str = None,
    ) -> Tuple[Optional[str], Optional[str]]:
        if old_string == new_string:
            return None, "old_string and new_string are identical - no changes"

        file_path = self._resolve_path(file_path, working_dir)

        if not os.path.exists(file_path):
            suggestion = suggest_path_under_cwd(file_path, working_dir)
            msg = f"File not found: {file_path}"
            if suggestion:
                msg += f"\nDid you mean: {get_display_path(suggestion, working_dir)}?"
            return None, msg

        file_size = os.path.getsize(file_path)
        if file_size > self.MAX_EDIT_SIZE:
            return None, f"File too large to edit ({file_size} bytes)"

        lock = self._get_lock(file_path)
        with lock:
            try:
                encoding = _detect_encoding(file_path)
                with open(file_path, "r", encoding=encoding, errors="replace") as f:
                    content = f.read()

                if old_string not in content:
                    cached = self._cache.get(file_path)
                    if cached and cached.is_partial_view:
                        return None, (
                            f"old_string not found. The file was only partially read before. "
                            f"Read the full file first to ensure accurate editing."
                        )

                    similar = find_similar_file(file_path, working_dir)
                    msg = f"old_string not found in {file_path}"
                    if similar:
                        msg += f"\nSimilar file exists: {get_display_path(similar, working_dir)}"
                    return None, msg

                count = content.count(old_string)
                if count > 1 and not replace_all:
                    return None, (
                        f"Found {count} occurrences of old_string. "
                        f"Set replace_all=true or provide more context for a unique match."
                    )

                new_content = content.replace(old_string, new_string) if replace_all else content.replace(old_string, new_string, 1)

                self._history.track_edit(file_path, content, new_content)

                line_endings = _detect_line_endings(content)
                with open(file_path, "w", encoding=encoding) as f:
                    f.write(new_content)

                mtime = 0.0
                try:
                    mtime = os.path.getmtime(file_path)
                except Exception:
                    pass

                state = FileState(
                    content=new_content,
                    timestamp=time.time(),
                    encoding=encoding,
                    line_count=new_content.count("\n") + 1,
                    size_bytes=len(new_content.encode("utf-8")),
                    content_hash=_compute_content_hash(new_content),
                    mtime=mtime,
                    line_endings=line_endings,
                )
                self._cache.put(file_path, state)

                diff_lines_old = old_string.count("\n") + 1
                diff_lines_new = new_string.count("\n") + 1
                display = get_display_path(file_path)
                return (
                    f"Edited {display}: "
                    f"replaced {count} occurrence(s), "
                    f"{diff_lines_old} line(s) -> {diff_lines_new} line(s)"
                ), None

            except Exception as e:
                return None, f"Error editing file: {e}"

    def list_directory(
        self,
        dir_path: str,
        working_dir: str = None,
        recursive: bool = False,
        max_depth: int = 3,
        ignore_patterns: List[str] = None,
    ) -> Tuple[Optional[str], Optional[str]]:
        dir_path = self._resolve_path(dir_path, working_dir)

        if not os.path.exists(dir_path):
            return None, f"Directory not found: {dir_path}"

        if not os.path.isdir(dir_path):
            return None, f"Not a directory: {dir_path}"

        if recursive:
            return render_directory_tree(dir_path, max_depth, ignore_patterns), None

        try:
            entries = sorted(os.listdir(dir_path))
            result_lines = []
            for entry in entries:
                full = os.path.join(dir_path, entry)
                if os.path.isdir(full):
                    result_lines.append(f"  {entry}/")
                else:
                    size = 0
                    try:
                        size = os.path.getsize(full)
                    except Exception:
                        pass
                    result_lines.append(f"  {entry}  ({_format_size(size)})")
            return "\n".join(result_lines), None
        except PermissionError:
            return None, f"Permission denied: {dir_path}"
        except Exception as e:
            return None, f"Error listing directory: {e}"

    def search_files(
        self,
        pattern: str,
        directory: str = None,
        working_dir: str = None,
        max_results: int = 50,
    ) -> Tuple[Optional[List[str]], Optional[str]]:
        directory = self._resolve_path(directory or ".", working_dir)

        if not os.path.isdir(directory):
            return None, f"Directory not found: {directory}"

        results = []
        try:
            for root, dirs, files in os.walk(directory):
                dirs[:] = [d for d in dirs if not d.startswith(".") and d != "node_modules" and d != "__pycache__"]
                for name in files:
                    if fnmatch.fnmatch(name, pattern):
                        results.append(os.path.join(root, name))
                        if len(results) >= max_results:
                            return results, None
        except Exception as e:
            return None, f"Search error: {e}"

        return results, None

    def get_file_info(
        self, file_path: str, working_dir: str = None
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        file_path = self._resolve_path(file_path, working_dir)

        if not os.path.exists(file_path):
            return None, f"File not found: {file_path}"

        try:
            stat = os.stat(file_path)
            is_dir = os.path.isdir(file_path)
            info = {
                "path": file_path,
                "display_path": get_display_path(file_path),
                "name": os.path.basename(file_path),
                "extension": os.path.splitext(file_path)[1],
                "is_dir": is_dir,
                "size": stat.st_size,
                "size_formatted": _format_size(stat.st_size),
                "modified": stat.st_mtime,
                "created": stat.st_ctime,
                "encoding": _detect_encoding(file_path) if not is_dir else None,
                "is_sensitive": _is_sensitive_path(file_path),
            }

            if not is_dir:
                cached = self._cache.get(file_path)
                if cached:
                    info["line_count"] = cached.line_count
                    info["content_hash"] = cached.content_hash
                    info["line_endings"] = cached.line_endings

            return info, None
        except Exception as e:
            return None, f"Error getting file info: {e}"

    def rewind_file(self, file_path: str, version: int) -> Tuple[bool, Optional[str]]:
        file_path = self._resolve_path(file_path)
        success, error = self._history.rewind(file_path, version)
        if success:
            self._cache.invalidate(file_path)
        return success, error

    def get_file_history(self, file_path: str) -> List[Dict[str, Any]]:
        file_path = self._resolve_path(file_path)
        return self._history.get_history(file_path)

    def get_cache(self) -> FileStateCache:
        return self._cache

    def get_changed_files(self) -> List[Dict[str, Any]]:
        changed = []
        for path in self._cache.keys():
            state = self._cache.get(path)
            if not state:
                continue
            if not os.path.exists(path):
                changed.append({
                    "path": path,
                    "display_path": get_display_path(path),
                    "status": "deleted",
                    "hash": state.content_hash,
                })
                continue
            try:
                current_mtime = os.path.getmtime(path)
                if state.mtime > 0 and abs(current_mtime - state.mtime) < 0.001:
                    continue

                with open(path, "r", encoding=state.encoding, errors="replace") as f:
                    current = f.read()
                current_hash = _compute_content_hash(current)
                if current_hash != state.content_hash:
                    changed.append({
                        "path": path,
                        "display_path": get_display_path(path),
                        "status": "modified",
                        "old_hash": state.content_hash,
                        "new_hash": current_hash,
                    })
            except Exception:
                changed.append({
                    "path": path,
                    "display_path": get_display_path(path),
                    "status": "unreadable",
                })
        return changed
