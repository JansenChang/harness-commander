"""provider 安装命令的应用层编排。"""

from __future__ import annotations

from pathlib import Path

from harness_commander.application.host_providers import INSTALL_TARGETS
from harness_commander.application.provider_config import (
    load_provider_config,
    mark_provider_installed,
    save_provider_config,
)
from harness_commander.application.provider_installers import install_provider_target
from harness_commander.domain.models import (
    CommandMessage,
    CommandResult,
    ResultStatus,
)


def run_install_provider(
    root: Path,
    *,
    provider: str,
    scope: str,
    install_mode: str,
    dry_run: bool,
) -> CommandResult:
    """探测并配置项目默认 provider。"""

    config = load_provider_config(root)
    results, install_artifacts = install_provider_target(
        root,
        provider=provider,
        scope=scope,
        install_mode=install_mode,
        dry_run=dry_run,
    )
    updated_config = config
    artifacts = [*install_artifacts]
    warnings: list[CommandMessage] = []
    installed_count = 0
    resolved_count = 0
    detected_count = 0

    for candidate, result in results.items():
        updated_config = mark_provider_installed(
            updated_config,
            provider=candidate,
            installation_result=result,
            set_as_default=False,
        )
        if result.get("detected"):
            detected_count += 1
        if result.get("resolved_target_dir"):
            resolved_count += 1
        if result["status"] == "installed":
            installed_count += 1
        else:
            warnings.append(
                CommandMessage(
                    code="provider_install_incomplete",
                    message=f"provider {candidate} 未完成 {scope} 范围的自动安装。",
                    location=str(root / ".harness/provider-config.json"),
                    detail=result,
                )
            )

    updated_config["last_resolved_provider"] = updated_config.get("default_provider")
    artifacts.append(
        save_provider_config(root, updated_config, dry_run=dry_run, overwrite=True)
    )

    status = ResultStatus.SUCCESS if installed_count > 0 else ResultStatus.WARNING
    failed_count = len(results) - installed_count
    summary = (
        f"provider 安装配置完成，共处理 {len(results)} 个目标，"
        f"{detected_count} 个已探测到宿主，{resolved_count} 个已解析目标目录，"
        f"{installed_count} 个已完成真实安装，{failed_count} 个返回了明确失败或待处理结果。"
    )
    return CommandResult(
        command="install-provider",
        status=status,
        summary=summary,
        artifacts=artifacts,
        warnings=warnings,
        meta={
            "root": str(root),
            "provider": provider,
            "install_targets": list(INSTALL_TARGETS),
            "results": results,
            "default_provider": updated_config.get("default_provider"),
            "installed_providers": updated_config.get("installed_providers", []),
            "scope": scope,
            "install_mode": install_mode,
            "dry_run": dry_run,
        },
    )
