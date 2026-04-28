#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辉夜IDE 项目指令系统
参考 Claude Code 的 claudemd.ts 架构，实现层级式项目指令发现与加载
"""

import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from pathlib import Path


INSTRUCTION_FILE_NAMES = ["KAGUYA.md", "kaguya.md"]
LOCAL_INSTRUCTION_FILE_NAMES = ["KAGUYA.local.md", "kaguya.local.md"]
RULES_DIR_NAME = ".kaguya"
RULES_PATTERN = "*.md"

MAX_INSTRUCTION_CHARS = 40000
MAX_INCLUDE_DEPTH = 5

TEXT_EXTENSIONS = {
    ".md", ".txt", ".text", ".json", ".yaml", ".yml", ".toml", ".xml", ".csv",
    ".html", ".htm", ".css", ".scss", ".js", ".ts", ".tsx", ".jsx", ".mjs",
    ".py", ".pyi", ".rb", ".go", ".rs", ".java", ".kt", ".scala", ".c", ".cpp",
    ".h", ".hpp", ".cs", ".swift", ".sh", ".bash", ".zsh", ".ps1", ".bat",
    ".env", ".ini", ".cfg", ".conf", ".sql", ".proto", ".vue", ".svelte",
}


@dataclass
class InstructionFile:
    path: str
    content: str
    priority: int
    source: str
    is_local: bool = False


@dataclass
class InstructionLoadResult:
    files: List[InstructionFile]
    combined_content: str
    total_chars: int
    warnings: List[str] = field(default_factory=list)


class ProjectInstructionsLoader:
    def __init__(self, project_root: str = None, user_home: str = None):
        self.project_root = os.path.abspath(project_root or os.getcwd())
        self.user_home = user_home or os.path.expanduser("~")
        self._cache: Dict[str, InstructionLoadResult] = {}

    def _is_text_file(self, file_path: str) -> bool:
        ext = os.path.splitext(file_path)[1].lower()
        return ext in TEXT_EXTENSIONS

    def _resolve_includes(self, content: str, base_dir: str, depth: int = 0) -> str:
        if depth >= MAX_INCLUDE_DEPTH:
            return content

        include_pattern = re.compile(r'@([\w./\\\-]+\.\w+)')

        lines = content.split("\n")
        result_lines = []

        for line in lines:
            if line.strip().startswith("```"):
                result_lines.append(line)
                continue

            in_code_block = False
            for rl in result_lines:
                if rl.strip().startswith("```"):
                    in_code_block = not in_code_block

            if in_code_block:
                result_lines.append(line)
                continue

            matches = include_pattern.finditer(line)
            offset = 0
            for match in matches:
                include_path = match.group(1)
                if not os.path.isabs(include_path):
                    full_path = os.path.join(base_dir, include_path)
                else:
                    full_path = include_path

                full_path = os.path.normpath(full_path)

                if os.path.exists(full_path) and self._is_text_file(full_path):
                    try:
                        with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                            included = f.read()
                        included = self._resolve_includes(included, os.path.dirname(full_path), depth + 1)
                        line = line[:match.start() + offset] + included + line[match.end() + offset:]
                        offset += len(included) - (match.end() - match.start())
                    except Exception:
                        pass

            result_lines.append(line)

        return "\n".join(result_lines)

    def _discover_project_instructions(self) -> List[InstructionFile]:
        files = []
        current = self.project_root
        depth = 0

        while current and depth < 20:
            for name in INSTRUCTION_FILE_NAMES:
                path = os.path.join(current, name)
                if os.path.exists(path):
                    priority = depth
                    files.append(InstructionFile(
                        path=path,
                        content="",
                        priority=priority,
                        source="project",
                    ))

            kaguya_dir = os.path.join(current, RULES_DIR_NAME)
            if os.path.isdir(kaguya_dir):
                for name in INSTRUCTION_FILE_NAMES:
                    path = os.path.join(kaguya_dir, name)
                    if os.path.exists(path):
                        files.append(InstructionFile(
                            path=path,
                            content="",
                            priority=depth + 0.5,
                            source="project_rules",
                        ))

                rules_dir = os.path.join(kaguya_dir, "rules")
                if os.path.isdir(rules_dir):
                    for entry in sorted(os.listdir(rules_dir)):
                        if entry.endswith(".md"):
                            path = os.path.join(rules_dir, entry)
                            files.append(InstructionFile(
                                path=path,
                                content="",
                                priority=depth + 0.5,
                                source="project_rules",
                            ))

            for name in LOCAL_INSTRUCTION_FILE_NAMES:
                path = os.path.join(current, name)
                if os.path.exists(path):
                    files.append(InstructionFile(
                        path=path,
                        content="",
                        priority=depth + 1,
                        source="local",
                        is_local=True,
                    ))

            parent = os.path.dirname(current)
            if parent == current:
                break
            current = parent
            depth += 1

        return files

    def _discover_user_instructions(self) -> List[InstructionFile]:
        files = []
        user_instruction_dir = os.path.join(self.user_home, ".kaguya")

        user_md = os.path.join(self.user_home, "KAGUYA.md")
        if os.path.exists(user_md):
            files.append(InstructionFile(
                path=user_md,
                content="",
                priority=-1,
                source="user_global",
            ))

        if os.path.isdir(user_instruction_dir):
            for name in INSTRUCTION_FILE_NAMES:
                path = os.path.join(user_instruction_dir, name)
                if os.path.exists(path):
                    files.append(InstructionFile(
                        path=path,
                        content="",
                        priority=-0.5,
                        source="user_dir",
                    ))

        return files

    def _load_file_content(self, instruction_file: InstructionFile) -> InstructionFile:
        try:
            with open(instruction_file.path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            content = self._resolve_includes(
                content, os.path.dirname(instruction_file.path)
            )

            if len(content) > MAX_INSTRUCTION_CHARS:
                content = content[:MAX_INSTRUCTION_CHARS] + (
                    f"\n\n> WARNING: {os.path.basename(instruction_file.path)} "
                    f"exceeds {MAX_INSTRUCTION_CHARS} chars and was truncated."
                )

            instruction_file.content = content
        except Exception as e:
            instruction_file.content = f"[Error loading {instruction_file.path}: {e}]"

        return instruction_file

    def load_instructions(self, use_cache: bool = True) -> InstructionLoadResult:
        cache_key = self.project_root
        if use_cache and cache_key in self._cache:
            return self._cache[cache_key]

        all_files = []
        all_files.extend(self._discover_user_instructions())
        all_files.extend(self._discover_project_instructions())

        loaded = []
        for f in all_files:
            loaded.append(self._load_file_content(f))

        loaded.sort(key=lambda f: f.priority)

        seen_paths = set()
        unique = []
        for f in loaded:
            if f.path not in seen_paths:
                seen_paths.add(f.path)
                unique.append(f)

        sections = []
        total_chars = 0
        warnings = []

        for f in unique:
            if not f.content.strip():
                continue

            header = f"# Instructions from: {os.path.relpath(f.path, self.project_root)}"
            if f.is_local:
                header += " (local, not for sharing)"

            section = f"{header}\n\n{f.content}"
            sections.append(section)
            total_chars += len(f.content)

        combined = "\n\n---\n\n".join(sections) if sections else ""

        if total_chars > MAX_INSTRUCTION_CHARS * 2:
            warnings.append(
                f"Total instructions ({total_chars} chars) are very large. "
                "Consider reducing instruction file sizes."
            )

        result = InstructionLoadResult(
            files=unique,
            combined_content=combined,
            total_chars=total_chars,
            warnings=warnings,
        )

        self._cache[cache_key] = result
        return result

    def get_system_prompt_section(self) -> str:
        result = self.load_instructions()
        if not result.combined_content:
            return ""

        return (
            "## Project Instructions\n\n"
            "Codebase and user instructions are shown below. "
            "These instructions OVERRIDE default behavior and MUST be followed exactly as written.\n\n"
            f"{result.combined_content}"
        )

    def invalidate_cache(self):
        self._cache.clear()

    def create_sample_instruction(self, path: str = None):
        if path is None:
            path = os.path.join(self.project_root, "KAGUYA.md")

        if os.path.exists(path):
            return False

        sample = """# Project Instructions

## Code Style
- Follow PEP 8 for Python code
- Use type hints for function signatures
- Write docstrings for public functions

## Architecture
- This project uses Flask for the web server
- Ollama is the LLM backend
- Memory system uses SQLite for persistence

## Important Files
- qwen3_web.py: Main application
- ollama_adapter.py: LLM adapter
- kaguya_core/: Core framework

## Conventions
- Use UTF-8 encoding for all files
- Keep functions under 50 lines
- Add error handling for all I/O operations
"""
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(sample)
        return True
