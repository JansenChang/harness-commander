"""provider 配置读写与运行时解析。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from harness_commander.application.host_providers import get_provider_spec, normalize_provider
from harness_commander.domain.models import CommandArtifact, HarnessCommanderError
from harness_commander.infrastructure.filesystem import write_text

CONFIG_VERSION = 1
PROVIDER_CONFIG_PATH = Path(".harness/provider-config.json")


ProviderConfig = dict[str, Any]


def provider_config_path(root: Path) -> Path:
    """返回项目级 provider 配置文件路径。"""

    return root / PROVIDER_CONFIG_PATH


def default_provider_config() -> ProviderConfig:
    """返回默认 provider 配置结构。"""

    return {
        "version": CONFIG_VERSION,
        "default_provider": None,
        "installed_providers": [],
        "installation_results": {},
        "last_resolved_provider": None,
    }


def load_provider_config(root: Path) -> ProviderConfig:
    """读取 provider 配置；不存在时返回默认结构。"""

    path = provider_config_path(root)
    if not path.exists():
        return default_provider_config()

    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as error:
        raise HarnessCommanderError(
            code="provider_config_read_failed",
            message=f"无法读取 provider 配置文件：{error}",
            location=str(path),
        ) from error

    try:
        import json

        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        raise HarnessCommanderError(
            code="provider_config_invalid",
            message="provider 配置文件不是有效 JSON。",
            location=str(path),
        ) from error

    if not isinstance(payload, dict):
        raise HarnessCommanderError(
            code="provider_config_invalid",
            message="provider 配置文件内容必须是 JSON object。",
            location=str(path),
        )

    config = default_provider_config()
    config.update(payload)
    config["installed_providers"] = _normalize_provider_list(
        config.get("installed_providers", [])
    )
    config["installation_results"] = _normalize_installation_results(
        config.get("installation_results", {})
    )
    default_provider = config.get("default_provider")
    config["default_provider"] = (
        normalize_provider(default_provider) if isinstance(default_provider, str) and default_provider.strip() else None
    )
    last_resolved_provider = config.get("last_resolved_provider")
    config["last_resolved_provider"] = (
        normalize_provider(last_resolved_provider)
        if isinstance(last_resolved_provider, str) and last_resolved_provider.strip()
        else None
    )
    return config


def save_provider_config(
    root: Path, config: ProviderConfig, *, dry_run: bool, overwrite: bool = True
) -> CommandArtifact:
    """保存 provider 配置文件。"""

    import json

    normalized = default_provider_config()
    normalized.update(config)
    normalized["installed_providers"] = _normalize_provider_list(
        normalized.get("installed_providers", [])
    )
    normalized["installation_results"] = _normalize_installation_results(
        normalized.get("installation_results", {})
    )
    content = json.dumps(normalized, ensure_ascii=False, indent=2) + "\n"
    return write_text(
        provider_config_path(root),
        content,
        dry_run=dry_run,
        overwrite=overwrite,
    )


def resolve_effective_provider(
    root: Path,
    *,
    override: str | None,
    persist_last_resolved: bool = False,
    dry_run: bool = False,
) -> tuple[str, str, ProviderConfig]:
    """按优先级解析当前命令应使用的 provider。"""

    config = load_provider_config(root)

    if override and override.strip():
        provider = normalize_provider(override)
        source = "override"
    else:
        default_provider = config.get("default_provider")
        if isinstance(default_provider, str) and default_provider.strip():
            provider = normalize_provider(default_provider)
            source = "default_provider"
        else:
            installed = config.get("installed_providers", [])
            if installed:
                provider = normalize_provider(installed[0])
                source = "installed_providers"
            else:
                raise HarnessCommanderError(
                    code="provider_not_configured",
                    message="未找到可用 provider，请先执行 harness install-provider 或显式传入 --provider。",
                    location=str(provider_config_path(root)),
                )

    if persist_last_resolved:
        config["last_resolved_provider"] = provider
        save_provider_config(root, config, dry_run=dry_run, overwrite=True)
    return provider, source, config


def mark_provider_installed(
    config: ProviderConfig,
    *,
    provider: str,
    installation_result: dict[str, Any],
    set_as_default: bool,
) -> ProviderConfig:
    """把单个 provider 安装结果写回配置结构。"""

    normalized_provider = normalize_provider(provider)
    next_config = default_provider_config()
    next_config.update(config)
    installed = _normalize_provider_list(next_config.get("installed_providers", []))
    results = _normalize_installation_results(next_config.get("installation_results", {}))
    results[normalized_provider] = dict(installation_result)

    status = str(installation_result.get("status", "")).strip().lower()
    if status in {"installed", "already_installed"}:
        if normalized_provider not in installed:
            installed.append(normalized_provider)
        if set_as_default or not next_config.get("default_provider"):
            next_config["default_provider"] = normalized_provider
    elif normalized_provider in installed and status not in {"installed", "already_installed"}:
        installed.remove(normalized_provider)

    next_config["installed_providers"] = installed
    next_config["installation_results"] = results
    return next_config


def _normalize_provider_list(items: Any) -> list[str]:
    """规范化 provider 列表。"""

    if not isinstance(items, list):
        return []
    normalized: list[str] = []
    for item in items:
        if not isinstance(item, str) or not item.strip():
            continue
        provider = normalize_provider(item)
        if provider not in normalized:
            normalized.append(provider)
    return normalized


def _normalize_installation_results(results: Any) -> dict[str, dict[str, Any]]:
    """规范化安装结果字典。"""

    if not isinstance(results, dict):
        return {}

    normalized_results: dict[str, dict[str, Any]] = {}
    for provider, detail in results.items():
        if not isinstance(provider, str) or not provider.strip():
            continue
        normalized_provider = normalize_provider(provider)
        spec = get_provider_spec(normalized_provider)
        payload = dict(detail) if isinstance(detail, dict) else {}
        payload.setdefault("status", "unknown")
        payload.setdefault("support_level", spec.install_support_level)
        payload.setdefault("detected", False)
        payload.setdefault("cli_command", spec.cli_command)
        payload.setdefault("configured_at", None)
        payload.setdefault("message", "")
        payload.setdefault("host_detected", payload.get("detected", False))
        payload.setdefault("resolved_target_dir", None)
        payload.setdefault("resolved_target_file", None)
        payload.setdefault("target_scope", "user")
        payload.setdefault("artifact_paths", [])
        payload.setdefault("install_attempted", False)
        payload.setdefault("failure_reason_code", None)
        payload.setdefault("failure_reason_detail", None)
        normalized_results[normalized_provider] = payload
    return normalized_results
