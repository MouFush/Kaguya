"""Small compatibility helpers for the Go backend migration.

This module intentionally contains pure functions only. The Go backend can own
the process/security boundary while the legacy Python worker keeps heavier
model, RAG, and agent behavior behind stable data contracts.
"""

from __future__ import annotations

from typing import Any, Mapping


PROVIDER_DEFAULTS: dict[str, dict[str, str]] = {
    "deepseek": {"api_url": "https://api.deepseek.com", "model": "deepseek-chat"},
    "openai": {"api_url": "https://api.openai.com/v1", "model": "gpt-4o"},
    "claude": {"api_url": "https://api.anthropic.com", "model": "claude-3-7-sonnet-20250219"},
    "gemini": {"api_url": "https://generativelanguage.googleapis.com/v1beta", "model": "gemini-2.0-flash"},
    "kimi": {"api_url": "https://api.moonshot.ai/v1", "model": "kimi-k2.6"},
    "moonshot": {"api_url": "https://api.moonshot.ai/v1", "model": "moonshot-v1-8k"},
    "qwen": {"api_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "model": "qwen-plus"},
    "minimax": {"api_url": "https://api.minimaxi.com/v1", "model": "MiniMax-M2.7"},
    "zhipu": {"api_url": "https://open.bigmodel.cn/api/paas/v4", "model": "glm-4-flash"},
    "mistral": {"api_url": "https://api.mistral.ai/v1", "model": "mistral-large-latest"},
    "groq": {"api_url": "https://api.groq.com/openai/v1", "model": "llama-3.3-70b-versatile"},
    "xai": {"api_url": "https://api.x.ai/v1", "model": "grok-2"},
}


def normalize_external_api_payload(data: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(data, Mapping):
        data = {}
    provider = str(data.get("provider") or data.get("active_provider") or "deepseek").strip().lower()
    api_key = str(data.get("api_key") or data.get("apiKey") or "").strip()
    api_url = str(data.get("api_url") or data.get("apiUrl") or "").strip()
    model = str(data.get("model") or "").strip()
    enabled_value = data.get("enabled")
    enabled = bool(api_key) if enabled_value is None else bool(enabled_value and api_key)
    base = PROVIDER_DEFAULTS.get(provider, {})
    return {
        "provider": provider,
        "api_key": api_key,
        "api_url": api_url or base.get("api_url", ""),
        "model": model or base.get("model", ""),
        "enabled": enabled,
    }


def mask_api_key(api_key: str | None) -> str:
    key = (api_key or "").strip()
    if not key:
        return ""
    if len(key) <= 8:
        return "****"
    return f"{key[:4]}****{key[-4:]}"


def frontend_external_api(config: Mapping[str, Any] | None) -> dict[str, Any]:
    cfg = normalize_external_api_payload(config)
    return {
        "enabled": cfg["enabled"],
        "provider": cfg["provider"],
        "apiKey": cfg["api_key"],
        "apiUrl": cfg["api_url"],
        "model": cfg["model"],
    }


def saved_config_response(config: Mapping[str, Any] | None) -> dict[str, Any]:
    cfg = normalize_external_api_payload(config)
    return {
        "success": True,
        "has_config": bool(cfg["api_key"]),
        "provider": cfg["provider"],
        "api_url": cfg["api_url"],
        "model": cfg["model"],
        "masked_api_key": mask_api_key(cfg["api_key"]),
    }


def build_saved_config_response(config: Mapping[str, Any] | None) -> dict[str, Any]:
    return saved_config_response(config)


def model_status_response(config: Mapping[str, Any] | None, *, mode: str = "python-worker") -> dict[str, Any]:
    cfg = normalize_external_api_payload(config)
    has_saved_key = bool(isinstance(config, Mapping) and config.get("hasSavedKey"))
    available = bool(cfg["api_key"] or has_saved_key)
    return {
        "success": True,
        "mode": mode,
        "external_provider_configured": available,
        "available": available,
        "provider": cfg["provider"],
        "api_url": cfg["api_url"],
        "model": cfg["model"],
        "reason": None if available else "missing_api_key",
    }


def build_model_status(config: Mapping[str, Any] | None, *, mode: str = "python-worker") -> dict[str, Any]:
    return model_status_response(config, mode=mode)


def default_external_api_config() -> dict[str, Any]:
    return {"active_provider": "deepseek", "providers": {k: dict(v, api_key="") for k, v in PROVIDER_DEFAULTS.items()}}


def structured_unavailable(
    feature: str = "chat",
    reason: str = "ollama_unavailable",
    *,
    provider: str = "ollama",
    model: str = "qwen3.5:4b",
    detail: str | None = None,
) -> dict[str, Any]:
    return {
        "success": False,
        "available": False,
        "error": reason,
        "feature": feature,
        "provider": provider,
        "model": model,
        "reason": reason,
        "detail": detail,
        "message": f"{feature} is unavailable in the current worker.",
    }
