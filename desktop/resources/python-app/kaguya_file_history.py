#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辉夜IDE 文件历史/撤销系统
参考 Claude Code 的 fileHistory.ts 架构，实现快照式文件检查点与回滚
"""

import hashlib
import json
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path


@dataclass
class FileBackup:
    file_path: str
    backup_path: str
    version: int
    timestamp: str
    content_hash: str
    file_size: int


@dataclass
class FileHistorySnapshot:
    snapshot_id: str
    message_id: str
    tracked_files: Dict[str, FileBackup]
    timestamp: str


@dataclass
class DiffStats:
    files_changed: List[str]
    insertions: int
    deletions: int


class FileHistoryManager:
    MAX_SNAPSHOTS = 100
    BACKUP_DIR_NAME = ".kaguya_file_history"

    def __init__(self, project_root: str = None):
        self.project_root = project_root or os.getcwd()
        self.backup_root = os.path.join(self.project_root, self.BACKUP_DIR_NAME)
        self._snapshots: List[FileHistorySnapshot] = []
        self._tracked_files: set = set()
        self._snapshot_counter = 0

    def _ensure_backup_dir(self):
        os.makedirs(self.backup_root, exist_ok=True)

    def _compute_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    def _get_backup_path(self, file_path: str, version: int) -> str:
        rel_path = os.path.relpath(file_path, self.project_root)
        safe_name = rel_path.replace(os.sep, "_").replace(":", "_")
        return os.path.join(self.backup_root, f"{safe_name}@v{version}")

    def _read_file_content(self, file_path: str) -> Optional[str]:
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        except Exception:
            return None

    def track_edit(self, file_path: str, message_id: str = "") -> bool:
        if not os.path.isabs(file_path):
            file_path = os.path.join(self.project_root, file_path)

        if not os.path.exists(file_path):
            return False

        self._ensure_backup_dir()
        self._tracked_files.add(file_path)

        if self._snapshots:
            latest = self._snapshots[-1]
            if file_path in latest.tracked_files:
                return True

        content = self._read_file_content(file_path)
        if content is None:
            return False

        version = self._snapshot_counter + 1
        backup_path = self._get_backup_path(file_path, version)

        try:
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            shutil.copy2(file_path, backup_path)
        except Exception:
            return False

        backup = FileBackup(
            file_path=file_path,
            backup_path=backup_path,
            version=version,
            timestamp=datetime.now().isoformat(),
            content_hash=self._compute_hash(content),
            file_size=os.path.getsize(file_path),
        )

        snapshot_id = hashlib.sha256(
            f"{file_path}:{version}:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]

        snapshot = FileHistorySnapshot(
            snapshot_id=snapshot_id,
            message_id=message_id,
            tracked_files={file_path: backup},
            timestamp=datetime.now().isoformat(),
        )

        if self._snapshots:
            latest = self._snapshots[-1]
            merged = dict(latest.tracked_files)
            if file_path not in merged:
                merged[file_path] = backup
                snapshot.tracked_files = merged

        self._snapshots.append(snapshot)
        self._snapshot_counter += 1

        if len(self._snapshots) > self.MAX_SNAPSHOTS:
            evicted = self._snapshots.pop(0)
            for fb in evicted.tracked_files.values():
                if os.path.exists(fb.backup_path):
                    os.remove(fb.backup_path)

        return True

    def make_snapshot(self, message_id: str = "") -> str:
        self._ensure_backup_dir()
        updated_backups: Dict[str, FileBackup] = {}

        if self._snapshots:
            updated_backups = dict(self._snapshots[-1].tracked_files)

        for file_path in list(self._tracked_files):
            if not os.path.exists(file_path):
                continue

            content = self._read_file_content(file_path)
            if content is None:
                continue

            current_hash = self._compute_hash(content)
            existing = updated_backups.get(file_path)

            if existing and existing.content_hash == current_hash:
                continue

            version = self._snapshot_counter + 1
            backup_path = self._get_backup_path(file_path, version)

            try:
                os.makedirs(os.path.dirname(backup_path), exist_ok=True)
                shutil.copy2(file_path, backup_path)
            except Exception:
                continue

            updated_backups[file_path] = FileBackup(
                file_path=file_path,
                backup_path=backup_path,
                version=version,
                timestamp=datetime.now().isoformat(),
                content_hash=current_hash,
                file_size=os.path.getsize(file_path),
            )
            self._snapshot_counter += 1

        snapshot_id = hashlib.sha256(
            f"snapshot:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]

        snapshot = FileHistorySnapshot(
            snapshot_id=snapshot_id,
            message_id=message_id,
            tracked_files=updated_backups,
            timestamp=datetime.now().isoformat(),
        )

        self._snapshots.append(snapshot)

        if len(self._snapshots) > self.MAX_SNAPSHOTS:
            evicted = self._snapshots.pop(0)
            for fb in evicted.tracked_files.values():
                if os.path.exists(fb.backup_path):
                    try:
                        os.remove(fb.backup_path)
                    except Exception:
                        pass

        return snapshot_id

    def restore_file(self, file_path: str, version: int = -1) -> bool:
        if not os.path.isabs(file_path):
            file_path = os.path.join(self.project_root, file_path)

        if version == -1:
            target_backup = None
            for snapshot in reversed(self._snapshots):
                if file_path in snapshot.tracked_files:
                    target_backup = snapshot.tracked_files[file_path]
                    break
        else:
            target_backup = None
            for snapshot in self._snapshots:
                if file_path in snapshot.tracked_files:
                    fb = snapshot.tracked_files[file_path]
                    if fb.version == version:
                        target_backup = fb
                        break

        if not target_backup:
            return False

        if not os.path.exists(target_backup.backup_path):
            return False

        try:
            shutil.copy2(target_backup.backup_path, file_path)
            return True
        except Exception:
            return False

    def get_diff_stats(self) -> DiffStats:
        if not self._snapshots:
            return DiffStats(files_changed=[], insertions=0, deletions=0)

        latest = self._snapshots[-1]
        changed = []
        total_ins = 0
        total_del = 0

        for file_path, backup in latest.tracked_files.items():
            if not os.path.exists(file_path):
                changed.append(file_path)
                continue

            current = self._read_file_content(file_path)
            if current is None:
                continue

            if not os.path.exists(backup.backup_path):
                continue

            original = self._read_file_content(backup.backup_path)
            if original is None:
                continue

            if current != original:
                changed.append(file_path)
                orig_lines = original.splitlines()
                curr_lines = current.splitlines()
                total_ins += max(0, len(curr_lines) - len(orig_lines))
                total_del += max(0, len(orig_lines) - len(curr_lines))

        return DiffStats(files_changed=changed, insertions=total_ins, deletions=total_del)

    def list_versions(self, file_path: str) -> List[Dict]:
        if not os.path.isabs(file_path):
            file_path = os.path.join(self.project_root, file_path)

        versions = []
        for snapshot in self._snapshots:
            if file_path in snapshot.tracked_files:
                fb = snapshot.tracked_files[file_path]
                versions.append({
                    "version": fb.version,
                    "timestamp": fb.timestamp,
                    "content_hash": fb.content_hash,
                    "file_size": fb.file_size,
                    "snapshot_id": snapshot.snapshot_id,
                })
        return versions

    def get_snapshot_count(self) -> int:
        return len(self._snapshots)

    def is_tracked(self, file_path: str) -> bool:
        if not os.path.isabs(file_path):
            file_path = os.path.join(self.project_root, file_path)
        return file_path in self._tracked_files

    def save_state(self, state_path: str = None):
        if state_path is None:
            state_path = os.path.join(self.backup_root, "state.json")

        self._ensure_backup_dir()
        state = {
            "project_root": self.project_root,
            "snapshot_counter": self._snapshot_counter,
            "tracked_files": list(self._tracked_files),
            "snapshots": [],
        }

        for snapshot in self._snapshots:
            s = {
                "snapshot_id": snapshot.snapshot_id,
                "message_id": snapshot.message_id,
                "timestamp": snapshot.timestamp,
                "tracked_files": {},
            }
            for fp, fb in snapshot.tracked_files.items():
                s["tracked_files"][fp] = {
                    "file_path": fb.file_path,
                    "backup_path": fb.backup_path,
                    "version": fb.version,
                    "timestamp": fb.timestamp,
                    "content_hash": fb.content_hash,
                    "file_size": fb.file_size,
                }
            state["snapshots"].append(s)

        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    def load_state(self, state_path: str = None):
        if state_path is None:
            state_path = os.path.join(self.backup_root, "state.json")

        if not os.path.exists(state_path):
            return

        with open(state_path, "r", encoding="utf-8") as f:
            state = json.load(f)

        self._snapshot_counter = state.get("snapshot_counter", 0)
        self._tracked_files = set(state.get("tracked_files", []))
        self._snapshots = []

        for s in state.get("snapshots", []):
            tracked = {}
            for fp, fb_data in s.get("tracked_files", {}).items():
                tracked[fp] = FileBackup(
                    file_path=fb_data["file_path"],
                    backup_path=fb_data["backup_path"],
                    version=fb_data["version"],
                    timestamp=fb_data["timestamp"],
                    content_hash=fb_data["content_hash"],
                    file_size=fb_data["file_size"],
                )
            self._snapshots.append(FileHistorySnapshot(
                snapshot_id=s["snapshot_id"],
                message_id=s.get("message_id", ""),
                tracked_files=tracked,
                timestamp=s["timestamp"],
            ))
