#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辉夜IDE Skills框架
参考 Claude Code 的 src/skills/ 架构
实现基于Markdown的可复用提示模板系统

核心设计：
1. 多来源加载：Managed(策略) > User(全局) > Project(项目) > Bundled(内置) > MCP(远程)
2. SKILL.md格式：YAML frontmatter + Markdown正文，支持参数替换和变量注入
3. 条件激活：通过paths frontmatter实现基于文件路径的技能自动发现
4. 与工具系统集成：通过SkillTool让模型可调用技能
"""

import json
import os
import re
import uuid
import fnmatch
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from enum import Enum
from datetime import datetime
from pathlib import Path


class SkillSource(Enum):
    MANAGED = "managed"
    USER = "skills"
    PROJECT = "skills"
    BUNDLED = "bundled"
    MCP = "mcp"
    LEGACY = "commands_DEPRECATED"


class SkillContext(Enum):
    INLINE = "inline"
    FORK = "fork"


@dataclass
class SkillFrontmatter:
    name: str = ""
    description: str = ""
    allowed_tools: List[str] = None
    when_to_use: str = ""
    argument_hint: str = ""
    arguments: List[str] = None
    model: str = "inherit"
    user_invocable: bool = True
    disable_model_invocation: bool = False
    context: SkillContext = SkillContext.INLINE
    agent: str = "general-purpose"
    effort: str = "medium"
    paths: List[str] = None
    hooks: Dict[str, Any] = None
    shell: str = "bash"
    version: str = "1.0"

    def __post_init__(self):
        if self.allowed_tools is None:
            self.allowed_tools = []
        if self.arguments is None:
            self.arguments = []
        if self.paths is None:
            self.paths = []
        if self.hooks is None:
            self.hooks = {}


@dataclass
class SkillDefinition:
    name: str
    description: str
    source: SkillSource
    frontmatter: SkillFrontmatter = None
    markdown_content: str = ""
    skill_dir: str = ""
    loaded_from: str = ""
    get_prompt: Optional[Callable] = None
    is_enabled_fn: Optional[Callable] = None
    has_user_specified_description: bool = False

    def __post_init__(self):
        if self.frontmatter is None:
            self.frontmatter = SkillFrontmatter(
                name=self.name,
                description=self.description,
            )


class FrontmatterParser:
    @staticmethod
    def parse(content: str) -> Tuple[Dict[str, Any], str]:
        content = content.strip()
        if not content.startswith("---"):
            return {}, content
        end_idx = content.find("---", 3)
        if end_idx == -1:
            return {}, content
        frontmatter_str = content[3:end_idx].strip()
        body = content[end_idx + 3:].strip()
        try:
            import yaml
            fm = yaml.safe_load(frontmatter_str)
            if not isinstance(fm, dict):
                return {}, body
            return fm, body
        except ImportError:
            return FrontmatterParser._parse_simple_yaml(frontmatter_str), body
        except Exception:
            return {}, body

    @staticmethod
    def _parse_simple_yaml(text: str) -> Dict[str, Any]:
        result = {}
        lines = text.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line or line.startswith("#"):
                i += 1
                continue
            if ":" in line:
                key, _, value = line.partition(":")
                key = key.strip()
                value = value.strip()
                if value.startswith("[") and value.endswith("]"):
                    items = [v.strip().strip("'\"") for v in value[1:-1].split(",")]
                    result[key] = items
                elif value.lower() in ("true", "false"):
                    result[key] = value.lower() == "true"
                elif value.isdigit():
                    result[key] = int(value)
                elif value == "" or value is None:
                    list_items = []
                    j = i + 1
                    while j < len(lines):
                        next_line = lines[j]
                        stripped = next_line.strip()
                        if not stripped:
                            j += 1
                            continue
                        if stripped.startswith("- "):
                            item_val = stripped[2:].strip().strip("'\"")
                            list_items.append(item_val)
                            j += 1
                        elif next_line.startswith("  ") or next_line.startswith("\t"):
                            j += 1
                        else:
                            break
                    if list_items:
                        result[key] = list_items
                    else:
                        result[key] = value.strip("'\"") if value else ""
                    i = j
                    continue
                else:
                    result[key] = value.strip("'\"")
            i += 1
        return result

    @staticmethod
    def parse_skill_fields(raw: Dict[str, Any]) -> SkillFrontmatter:
        def _to_list(val) -> List[str]:
            if isinstance(val, list):
                return val
            if isinstance(val, str):
                return [v.strip() for v in val.split(",") if v.strip()]
            return []

        ctx_str = raw.get("context", "inline")
        try:
            ctx = SkillContext(ctx_str)
        except ValueError:
            ctx = SkillContext.INLINE

        return SkillFrontmatter(
            name=raw.get("name", ""),
            description=raw.get("description", ""),
            allowed_tools=_to_list(raw.get("allowed-tools", raw.get("allowed_tools", []))),
            when_to_use=raw.get("when_to_use", raw.get("when-to-use", "")),
            argument_hint=raw.get("argument-hint", raw.get("argument_hint", "")),
            arguments=_to_list(raw.get("arguments", [])),
            model=raw.get("model", "inherit"),
            user_invocable=str(raw.get("user-invocable", raw.get("user_invocable", "true"))).lower() == "true",
            disable_model_invocation=bool(raw.get("disable-model-invocation", raw.get("disable_model_invocation", False))),
            context=ctx,
            agent=raw.get("agent", "general-purpose"),
            effort=raw.get("effort", "medium"),
            paths=_to_list(raw.get("paths", [])),
            hooks=raw.get("hooks", {}),
            shell=raw.get("shell", "bash"),
            version=str(raw.get("version", "1.0")),
        )


class SkillLoader:
    SKILL_MD_NAME = "SKILL.md"

    def __init__(self, config_dir: str = None):
        self._config_dir = config_dir or os.path.join(
            os.path.expanduser("~"), ".kaguya"
        )
        self._loaded_skills: Dict[str, SkillDefinition] = {}
        self._realpath_cache: Dict[str, str] = {}
        self._lock = threading.Lock()

    def load_all_skills(self, cwd: str = None) -> List[SkillDefinition]:
        cwd = cwd or os.getcwd()
        all_skills = []
        all_skills.extend(self._load_skills_from_dir(self._get_managed_dir(), SkillSource.MANAGED))
        all_skills.extend(self._load_skills_from_dir(self._get_user_dir(), SkillSource.USER))
        all_skills.extend(self._load_project_skills(cwd))
        all_skills.extend(self._load_bundled_skills())
        deduped = self._deduplicate(all_skills)
        with self._lock:
            for s in deduped:
                self._loaded_skills[s.name] = s
        return deduped

    def _load_skills_from_dir(self, base_path: str, source: SkillSource) -> List[SkillDefinition]:
        if not base_path or not os.path.isdir(base_path):
            return []
        skills = []
        try:
            entries = os.listdir(base_path)
        except OSError:
            return []
        for entry in entries:
            entry_path = os.path.join(base_path, entry)
            if not os.path.isdir(entry_path) and not os.path.islink(entry_path):
                continue
            md_path = os.path.join(entry_path, self.SKILL_MD_NAME)
            if not os.path.isfile(md_path):
                continue
            skill = self._load_skill_file(md_path, entry_path, source)
            if skill:
                skills.append(skill)
        return skills

    def _load_skill_file(self, md_path: str, skill_dir: str, source: SkillSource) -> Optional[SkillDefinition]:
        try:
            with open(md_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            return None
        raw_fm, body = FrontmatterParser.parse(content)
        fm = FrontmatterParser.parse_skill_fields(raw_fm)
        name = fm.name or os.path.basename(skill_dir)
        desc = fm.description or ""
        if not desc:
            first = body.strip().split("\n")[0] if body.strip() else ""
            desc = first.lstrip("#").strip()[:100] if first.startswith("#") else first[:100]
        skill = SkillDefinition(
            name=name, description=desc, source=source,
            frontmatter=fm, markdown_content=body, skill_dir=skill_dir,
            loaded_from=source.value,
            has_user_specified_description=bool(raw_fm.get("description")),
        )
        skill.get_prompt = self._make_prompt_fn(skill)
        return skill

    def _make_prompt_fn(self, skill: SkillDefinition) -> Callable:
        def get_prompt(args: str = "", context: Any = None) -> List[Dict[str, Any]]:
            content = skill.markdown_content
            if skill.skill_dir:
                content = f"Base directory for this skill: {skill.skill_dir}\n\n{content}"
            content = self._substitute_args(content, args, skill.frontmatter.arguments)
            content = self._substitute_vars(content, skill.skill_dir)
            return [{"type": "text", "text": content}]
        return get_prompt

    def _substitute_args(self, content: str, args: str, arg_names: List[str]) -> str:
        if not args:
            return content
        content = content.replace("$ARGUMENTS", args).replace("$args", args)
        if arg_names:
            parts = args.split()
            for i, name in enumerate(arg_names):
                if i < len(parts):
                    content = content.replace(f"${name}", parts[i])
                    content = content.replace(f"${{{name}}}", parts[i])
            remaining = " ".join(parts[len(arg_names):])
            if remaining:
                content = content.replace("$REMAINING_ARGS", remaining)
        return content

    def _substitute_vars(self, content: str, skill_dir: str) -> str:
        content = content.replace("${KAGUYA_SKILL_DIR}", skill_dir)
        content = content.replace("${KAGUYA_SESSION_ID}", str(uuid.uuid4())[:8])
        return content

    def _load_project_skills(self, cwd: str) -> List[SkillDefinition]:
        skills = []
        current = os.path.abspath(cwd)
        home = os.path.expanduser("~")
        while current and current != home and len(current) > 3:
            sd = os.path.join(current, ".kaguya", "skills")
            if os.path.isdir(sd):
                skills.extend(self._load_skills_from_dir(sd, SkillSource.PROJECT))
            parent = os.path.dirname(current)
            if parent == current:
                break
            current = parent
        return skills

    def _load_bundled_skills(self) -> List[SkillDefinition]:
        bundled = []

        bundled.append(SkillDefinition(
            name="verify", description="Verify code changes by running tests and checking for issues",
            source=SkillSource.BUNDLED, loaded_from="bundled",
            frontmatter=SkillFrontmatter(name="verify", description="Verify code changes",
                allowed_tools=["Read", "Bash", "Glob", "Grep"],
                when_to_use="Use when you need to verify code changes", context=SkillContext.FORK, agent="verification"),
            get_prompt=lambda args="", ctx=None: [{"type": "text", "text":
                f"Verify the recent code changes. Check for syntax errors, import issues, type mismatches, run tests, check security.\nFocus on: {args}" if args else "Verify the recent code changes."}],
        ))

        bundled.append(SkillDefinition(
            name="debug", description="Debug session issues and diagnose problems",
            source=SkillSource.BUNDLED, loaded_from="bundled",
            frontmatter=SkillFrontmatter(name="debug", description="Debug issues",
                allowed_tools=["Read", "Bash", "Glob", "Grep"],
                when_to_use="Use when diagnosing errors or unexpected behavior"),
            get_prompt=lambda args="", ctx=None: [{"type": "text", "text":
                f"Debug the following issue:\n{args}\n\n1. Read relevant files\n2. Identify root cause\n3. Suggest fix\n4. Verify fix"}],
        ))

        bundled.append(SkillDefinition(
            name="remember", description="Review and organize memories for long-term retention",
            source=SkillSource.BUNDLED, loaded_from="bundled",
            frontmatter=SkillFrontmatter(name="remember", description="Organize memories",
                when_to_use="Use when saving important information for future sessions"),
            get_prompt=lambda args="", ctx=None: [{"type": "text", "text":
                "Review the conversation and extract important information:\n1. User preferences\n2. Important decisions\n3. Technical knowledge\n4. Project conventions\n" + (f"Focus on: {args}" if args else "")}],
        ))

        bundled.append(SkillDefinition(
            name="simplify", description="Review code and suggest simplifications",
            source=SkillSource.BUNDLED, loaded_from="bundled",
            frontmatter=SkillFrontmatter(name="simplify", description="Simplify code",
                allowed_tools=["Read", "Glob", "Grep"],
                when_to_use="Use when reviewing code for cleanup"),
            get_prompt=lambda args="", ctx=None: [{"type": "text", "text":
                "Review code for simplification:\n1. Redundant code\n2. Complex logic\n3. Repeated patterns\n4. Over-engineering\n" + (f"Target: {args}" if args else "")}],
        ))

        bundled.append(SkillDefinition(
            name="skillify", description="Capture a conversation process as a reusable skill",
            source=SkillSource.BUNDLED, loaded_from="bundled",
            frontmatter=SkillFrontmatter(name="skillify", description="Create skill from conversation",
                when_to_use="Use when saving current workflow as a reusable skill",
                arguments=["skill-name"]),
            get_prompt=lambda args="", ctx=None: [{"type": "text", "text":
                "Analyze the conversation and create a reusable skill:\n1. Identify key steps\n2. Extract parameters\n3. Write SKILL.md\n4. Save to .kaguya/skills/\n" + (f"Skill name: {args}" if args else "")}],
        ))

        bundled.append(SkillDefinition(
            name="batch", description="Orchestrate parallel work across multiple tasks",
            source=SkillSource.BUNDLED, loaded_from="bundled",
            frontmatter=SkillFrontmatter(name="batch", description="Parallel task orchestration",
                when_to_use="Use when multiple independent tasks need parallel execution",
                context=SkillContext.FORK),
            get_prompt=lambda args="", ctx=None: [{"type": "text", "text":
                f"Orchestrate parallel tasks:\n{args}\n\nFor each task: break down, execute, report results, note dependencies"}],
        ))

        return bundled

    def _deduplicate(self, skills: List[SkillDefinition]) -> List[SkillDefinition]:
        seen: Set[str] = set()
        by_name: Dict[str, SkillDefinition] = {}
        priority = {SkillSource.MANAGED: 6, SkillSource.USER: 5, SkillSource.PROJECT: 4,
                    SkillSource.BUNDLED: 3, SkillSource.MCP: 2, SkillSource.LEGACY: 1}
        for s in skills:
            rp = os.path.realpath(s.skill_dir) if s.skill_dir else s.name
            if rp in seen:
                continue
            seen.add(rp)
            existing = by_name.get(s.name)
            if existing:
                if priority.get(s.source, 0) > priority.get(existing.source, 0):
                    by_name[s.name] = s
            else:
                by_name[s.name] = s
        return list(by_name.values())

    def _get_managed_dir(self) -> str:
        return os.path.join(self._config_dir, "managed", ".kaguya", "skills")

    def _get_user_dir(self) -> str:
        return os.path.join(self._config_dir, "skills")

    def get_skill(self, name: str) -> Optional[SkillDefinition]:
        with self._lock:
            return self._loaded_skills.get(name)

    def list_skills(self) -> List[SkillDefinition]:
        with self._lock:
            return list(self._loaded_skills.values())

    def discover_skills_for_paths(self, file_paths: List[str], cwd: str = None) -> List[SkillDefinition]:
        cwd = cwd or os.getcwd()
        discovered = []
        with self._lock:
            for skill in self._loaded_skills.values():
                if not skill.frontmatter.paths:
                    continue
                for fp in file_paths:
                    abs_fp = os.path.abspath(fp) if not os.path.isabs(fp) else fp
                    for pattern in skill.frontmatter.paths:
                        if fnmatch.fnmatch(abs_fp, pattern):
                            discovered.append(skill)
                            break
        return discovered

    def get_model_invocable_skills(self) -> List[SkillDefinition]:
        with self._lock:
            return [s for s in self._loaded_skills.values()
                    if not s.frontmatter.disable_model_invocation
                    and (s.loaded_from in ("bundled", "skills", "commands_DEPRECATED")
                         or s.has_user_specified_description
                         or s.frontmatter.when_to_use)]

    def format_skill_listing(self, budget: int = 4000) -> str:
        skills = self.get_model_invocable_skills()
        if not skills:
            return ""
        lines = ["Available skills (invoke with /skill-name):"]
        total = 0
        for s in skills:
            entry = f"  /{s.name}"
            if s.frontmatter.argument_hint:
                entry += f" {s.frontmatter.argument_hint}"
            entry += f" - {s.description}"
            if s.frontmatter.when_to_use:
                entry += f" ({s.frontmatter.when_to_use})"
            if total + len(entry) > budget:
                lines.append(f"  ... and {len(skills) - skills.index(s)} more skills")
                break
            lines.append(entry)
            total += len(entry)
        return "\n".join(lines)

    def create_skill(self, name: str, description: str, content: str,
                     skill_dir: str = None, source: SkillSource = SkillSource.USER) -> SkillDefinition:
        if not skill_dir:
            skill_dir = os.path.join(self._get_user_dir(), name)
        os.makedirs(skill_dir, exist_ok=True)
        md_path = os.path.join(skill_dir, self.SKILL_MD_NAME)
        fm_text = f"---\nname: {name}\ndescription: {description}\n---\n\n"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(fm_text + content)
        skill = self._load_skill_file(md_path, skill_dir, source)
        if skill:
            with self._lock:
                self._loaded_skills[name] = skill
        return skill

    def delete_skill(self, name: str) -> bool:
        with self._lock:
            skill = self._loaded_skills.pop(name, None)
        if not skill:
            return False
        if skill.skill_dir and os.path.isdir(skill.skill_dir):
            import shutil
            try:
                shutil.rmtree(skill.skill_dir)
            except Exception:
                pass
        return True


class SkillTool:
    TOOL_NAME = "Skill"

    def __init__(self, loader: SkillLoader):
        self._loader = loader
        self._ensure_loaded = False

    def _ensure_skills_loaded(self):
        if not self._ensure_loaded:
            if not self._loader._loaded_skills:
                self._loader.load_all_skills()
            self._ensure_loaded = True

    def execute(self, skill_name: str, args: str = "", context: Any = None) -> Dict[str, Any]:
        self._ensure_skills_loaded()
        skill = self._loader.get_skill(skill_name)
        if not skill:
            return {"error": f"Skill not found: {skill_name}"}

        if skill.is_enabled_fn and not skill.is_enabled_fn():
            return {"error": f"Skill is currently disabled: {skill_name}"}

        try:
            prompt_blocks = skill.get_prompt(args, context) if skill.get_prompt else []
            return {
                "success": True,
                "skill_name": skill_name,
                "prompt_blocks": prompt_blocks,
                "context": skill.frontmatter.context.value,
                "agent": skill.frontmatter.agent,
                "model": skill.frontmatter.model,
                "allowed_tools": skill.frontmatter.allowed_tools,
            }
        except Exception as e:
            return {"error": f"Skill execution error: {e}"}

    def list_available(self) -> List[Dict[str, Any]]:
        self._ensure_skills_loaded()
        skills = self._loader.get_model_invocable_skills()
        return [{
            "name": s.name,
            "description": s.description,
            "argument_hint": s.frontmatter.argument_hint,
            "context": s.frontmatter.context.value,
            "model": s.frontmatter.model,
        } for s in skills]


def create_skill_system(config_dir: str = None) -> Tuple[SkillLoader, SkillTool]:
    loader = SkillLoader(config_dir)
    tool = SkillTool(loader)
    return loader, tool
