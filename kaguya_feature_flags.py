#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辉夜IDE 特性标志系统
参考 Claude Code 的 feature flag 架构，实现运行时功能开关管理
"""

import json
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set
from enum import Enum


class FeatureState(Enum):
    DISABLED = "disabled"
    ENABLED = "enabled"
    ROLLOUT = "rollout"


@dataclass
class FeatureFlag:
    name: str
    state: FeatureState
    description: str = ""
    rollout_percentage: float = 0.0
    allowed_users: List[str] = field(default_factory=list)
    allowed_tiers: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class FeatureFlagManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config_path: str = None):
        if self._initialized:
            return
        self._initialized = True
        self._flags: Dict[str, FeatureFlag] = {}
        self._overrides: Dict[str, bool] = {}
        self._config_path = config_path
        self._user_id: Optional[str] = None
        self._user_tier: str = "free"
        self._listeners: Dict[str, List[Callable]] = {}

        self._register_defaults()

        if config_path and os.path.exists(config_path):
            self.load_config(config_path)

    def _register_defaults(self):
        defaults = [
            FeatureFlag("tool_system", FeatureState.ENABLED, "Structured tool system with permissions"),
            FeatureFlag("file_history", FeatureState.ENABLED, "File checkpointing and undo"),
            FeatureFlag("conversation_compaction", FeatureState.ENABLED, "Auto context window management"),
            FeatureFlag("project_instructions", FeatureState.ENABLED, "KAGUYA.md project instructions"),
            FeatureFlag("hooks_system", FeatureState.ENABLED, "Lifecycle hooks for tool execution"),
            FeatureFlag("auto_compact", FeatureState.ENABLED, "Automatic conversation compaction"),
            FeatureFlag("reactive_compact", FeatureState.DISABLED, "Reactive compaction mode"),
            FeatureFlag("sub_agents", FeatureState.ENABLED, "Built-in sub-agent system"),
            FeatureFlag("explore_agent", FeatureState.ENABLED, "Codebase exploration agent"),
            FeatureFlag("plan_agent", FeatureState.ENABLED, "Planning agent"),
            FeatureFlag("verification_agent", FeatureState.ENABLED, "Verification agent"),
            FeatureFlag("fork_subagent", FeatureState.DISABLED, "Fork subagent with prompt cache sharing"),
            FeatureFlag("daemon_mode", FeatureState.DISABLED, "Background daemon mode"),
            FeatureFlag("pipe_ipc", FeatureState.DISABLED, "Multi-instance pipe communication"),
            FeatureFlag("bridge_mode", FeatureState.DISABLED, "Remote control bridge"),
            FeatureFlag("computer_use", FeatureState.DISABLED, "Screen and browser control"),
            FeatureFlag("voice_mode", FeatureState.DISABLED, "Push-to-talk voice input"),
            FeatureFlag("cron_scheduling", FeatureState.DISABLED, "Scheduled task execution"),
            FeatureFlag("team_communication", FeatureState.DISABLED, "Peer messaging"),
            FeatureFlag("token_budget", FeatureState.ENABLED, "Token budget display and management"),
            FeatureFlag("prompt_cache", FeatureState.ENABLED, "Prompt cache stability"),
            FeatureFlag("ultrathink", FeatureState.DISABLED, "Extended thinking mode"),
            FeatureFlag("skills_system", FeatureState.ENABLED, "Markdown-based skills framework"),
            FeatureFlag("acp_protocol", FeatureState.ENABLED, "Agent Client Protocol for IDE integration"),
            FeatureFlag("enhanced_accounts", FeatureState.ENABLED, "Enhanced account management with RBAC"),
            FeatureFlag("frontend_modules", FeatureState.ENABLED, "Modular frontend with state management"),
            FeatureFlag("plugin_marketplace", FeatureState.DISABLED, "Plugin marketplace integration"),
            FeatureFlag("memory_extraction", FeatureState.DISABLED, "Automatic memory extraction"),
            FeatureFlag("session_transcript", FeatureState.DISABLED, "Session transcript classification"),
        ]

        for flag in defaults:
            self._flags[flag.name] = flag

    def is_enabled(self, feature_name: str) -> bool:
        if feature_name in self._overrides:
            return self._overrides[feature_name]

        flag = self._flags.get(feature_name)
        if not flag:
            return False

        if flag.state == FeatureState.DISABLED:
            return False

        if flag.state == FeatureState.ENABLED:
            return self._check_dependencies(flag)

        if flag.state == FeatureState.ROLLOUT:
            if not self._check_dependencies(flag):
                return False
            if flag.allowed_users and self._user_id:
                if self._user_id in flag.allowed_users:
                    return True
            if flag.allowed_tiers and self._user_tier:
                if self._user_tier in flag.allowed_tiers:
                    return True
            if flag.rollout_percentage > 0 and self._user_id:
                hash_val = hash(f"{feature_name}:{self._user_id}") % 100
                return hash_val < flag.rollout_percentage
            return False

        return False

    def _check_dependencies(self, flag: FeatureFlag) -> bool:
        for dep in flag.dependencies:
            if not self.is_enabled(dep):
                return False
        return True

    def enable(self, feature_name: str):
        if feature_name in self._flags:
            self._flags[feature_name].state = FeatureState.ENABLED
        else:
            self._flags[feature_name] = FeatureFlag(
                name=feature_name,
                state=FeatureState.ENABLED,
            )
        self._notify_listeners(feature_name, True)

    def disable(self, feature_name: str):
        if feature_name in self._flags:
            self._flags[feature_name].state = FeatureState.DISABLED
        self._notify_listeners(feature_name, False)

    def override(self, feature_name: str, enabled: bool):
        self._overrides[feature_name] = enabled
        self._notify_listeners(feature_name, enabled)

    def clear_override(self, feature_name: str):
        self._overrides.pop(feature_name, None)

    def clear_all_overrides(self):
        self._overrides.clear()

    def set_rollout(self, feature_name: str, percentage: float):
        if feature_name in self._flags:
            self._flags[feature_name].state = FeatureState.ROLLOUT
            self._flags[feature_name].rollout_percentage = percentage

    def set_user_context(self, user_id: str = None, user_tier: str = None):
        if user_id is not None:
            self._user_id = user_id
        if user_tier is not None:
            self._user_tier = user_tier

    def register_flag(self, flag: FeatureFlag):
        self._flags[flag.name] = flag

    def on_change(self, feature_name: str, callback: Callable):
        if feature_name not in self._listeners:
            self._listeners[feature_name] = []
        self._listeners[feature_name].append(callback)

    def _notify_listeners(self, feature_name: str, enabled: bool):
        for cb in self._listeners.get(feature_name, []):
            try:
                cb(feature_name, enabled)
            except Exception:
                pass

    def list_flags(self) -> List[Dict[str, Any]]:
        result = []
        for name, flag in sorted(self._flags.items()):
            effective = self.is_enabled(name)
            overridden = name in self._overrides
            result.append({
                "name": name,
                "state": flag.state.value,
                "effective": effective,
                "overridden": overridden,
                "description": flag.description,
                "rollout_percentage": flag.rollout_percentage,
                "dependencies": flag.dependencies,
            })
        return result

    def get_enabled_features(self) -> Set[str]:
        return {name for name in self._flags if self.is_enabled(name)}

    def get_disabled_features(self) -> Set[str]:
        return {name for name in self._flags if not self.is_enabled(name)}

    def load_config(self, config_path: str):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception:
            return

        for fc in config.get("flags", []):
            name = fc.get("name", "")
            state_str = fc.get("state", "disabled")
            try:
                state = FeatureState(state_str)
            except ValueError:
                state = FeatureState.DISABLED

            self._flags[name] = FeatureFlag(
                name=name,
                state=state,
                description=fc.get("description", ""),
                rollout_percentage=fc.get("rollout_percentage", 0.0),
                allowed_users=fc.get("allowed_users", []),
                allowed_tiers=fc.get("allowed_tiers", []),
                dependencies=fc.get("dependencies", []),
            )

        for name, enabled in config.get("overrides", {}).items():
            self._overrides[name] = bool(enabled)

        user_ctx = config.get("user_context", {})
        if "user_id" in user_ctx:
            self._user_id = user_ctx["user_id"]
        if "user_tier" in user_ctx:
            self._user_tier = user_ctx["user_tier"]

    def save_config(self, config_path: str = None):
        path = config_path or self._config_path
        if not path:
            return

        flags_list = []
        for name, flag in sorted(self._flags.items()):
            flags_list.append({
                "name": name,
                "state": flag.state.value,
                "description": flag.description,
                "rollout_percentage": flag.rollout_percentage,
                "allowed_users": flag.allowed_users,
                "allowed_tiers": flag.allowed_tiers,
                "dependencies": flag.dependencies,
            })

        config = {
            "flags": flags_list,
            "overrides": dict(self._overrides),
            "user_context": {
                "user_id": self._user_id,
                "user_tier": self._user_tier,
            },
        }

        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

    @classmethod
    def reset_instance(cls):
        cls._instance = None


def feature(feature_name: str) -> bool:
    return FeatureFlagManager().is_enabled(feature_name)
