"""provider 安装探测与结果生成。"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from harness_commander.application.host_providers import (
    INSTALLABLE_PROVIDER_TARGETS,
    ResolvedInstallTarget,
    get_provider_spec,
    normalize_install_target,
    provider_wrapper_source_path,
    resolve_provider_install_target,
)
from harness_commander.domain.models import CommandArtifact
from harness_commander.infrastructure.filesystem import utc_timestamp, write_text


InstallerResult = dict[str, Any]


@dataclass(frozen=True, slots=True)
class ProviderInstallPlan:
    provider: str
    detected: bool
    resolved_target: ResolvedInstallTarget


def install_provider_target(
    root: Path,
    *,
    provider: str,
    scope: str,
    install_mode: str,
    dry_run: bool = False,
) -> tuple[dict[str, InstallerResult], list[CommandArtifact]]:
    """按 install-provider 目标执行探测、安装与配置。"""

    target = normalize_install_target(provider)
    providers = _resolve_providers_to_process(target)

    results: dict[str, InstallerResult] = {}
    artifacts: list[CommandArtifact] = []
    for candidate in providers:
        plan = _build_install_plan(candidate, root=root, scope=scope)
        result = _build_initial_result(root=root, plan=plan, dry_run=dry_run, install_mode=install_mode)
        install_artifacts = _execute_install_plan(
            root=root,
            plan=plan,
            install_mode=install_mode,
            dry_run=dry_run,
            result=result,
        )
        artifacts.extend(install_artifacts)
        results[candidate] = result
    return results, artifacts


def _resolve_providers_to_process(target: str) -> list[str]:
    if target in {"auto", "all"}:
        return list(INSTALLABLE_PROVIDER_TARGETS)
    return [target]


def _build_install_plan(provider: str, *, root: Path, scope: str) -> ProviderInstallPlan:
    spec = get_provider_spec(provider)
    detected = _detect_provider_cli(spec.detect_commands)
    resolved_target = resolve_provider_install_target(provider, scope=scope, root=root)
    return ProviderInstallPlan(provider=provider, detected=detected, resolved_target=resolved_target)


def _build_initial_result(
    *,
    root: Path,
    plan: ProviderInstallPlan,
    dry_run: bool,
    install_mode: str,
) -> InstallerResult:
    spec = get_provider_spec(plan.provider)
    resolved_dir = str(plan.resolved_target.target_dir) if plan.resolved_target.target_dir else None
    target_path = str(plan.resolved_target.target_file) if plan.resolved_target.target_file else None
    return {
        "status": "pending",
        "support_level": spec.install_support_level,
        "wrapper_kind": spec.wrapper_kind,
        "detected": plan.detected,
        "host_detected": plan.resolved_target.host_detected,
        "cli_command": spec.cli_command,
        "configured_at": utc_timestamp(),
        "message": spec.install_hint,
        "root": str(root),
        "installation_mode": _installation_mode_for_support_level(spec.install_support_level),
        "install_attempted": False,
        "artifact_paths": [],
        "dry_run": dry_run,
        "installer": spec.installer_name,
        "requested_install_mode": install_mode,
        "resolved_target_dir": resolved_dir,
        "resolved_target_file": target_path,
        "target_scope": plan.resolved_target.target_scope,
        "failure_reason_code": plan.resolved_target.failure_reason_code,
        "failure_reason_detail": plan.resolved_target.failure_reason_detail,
    }


def _detect_provider_cli(commands: tuple[str, ...]) -> bool:
    """探测候选 CLI 是否在 PATH 中可见。"""

    return any(shutil.which(command) for command in commands)


def _installation_mode_for_support_level(support_level: str) -> str:
    """根据 support level 返回安装模式标签。"""

    if support_level == "fully_supported":
        return "wrapper"
    if support_level == "config_only":
        return "config_only"
    return "manual"


def _execute_install_plan(
    *,
    root: Path,
    plan: ProviderInstallPlan,
    install_mode: str,
    dry_run: bool,
    result: InstallerResult,
) -> list[CommandArtifact]:
    """执行单个 provider 的安装计划。"""

    spec = get_provider_spec(plan.provider)
    source_path = provider_wrapper_source_path(root, plan.provider)
    target_file = plan.resolved_target.target_file
    target_dir = plan.resolved_target.target_dir

    if not plan.detected:
        result["status"] = "failed_detection"
        result["message"] = f"未探测到 {plan.provider} 本地 CLI，跳过自动安装。"
        result["failure_reason_code"] = "cli_not_detected"
        result["failure_reason_detail"] = f"未在 PATH 中发现 {spec.detect_commands}。"
        return []

    if target_file is None or target_dir is None:
        result["status"] = "failed_target_resolution"
        result["message"] = plan.resolved_target.failure_reason_detail or f"未能解析 {plan.provider} 的用户级目标目录。"
        result["failure_reason_code"] = plan.resolved_target.failure_reason_code or "target_dir_unresolved"
        result["failure_reason_detail"] = plan.resolved_target.failure_reason_detail
        return []

    result["install_attempted"] = True
    if source_path is None or not source_path.exists():
        result["status"] = "failed_source_missing"
        result["message"] = f"未找到 provider wrapper 源路径：{source_path}"
        result["failure_reason_code"] = "wrapper_source_missing"
        result["failure_reason_detail"] = str(source_path) if source_path else "wrapper source undefined"
        return []

    if spec.wrapper_kind == "skill":
        try:
            artifacts = _install_skill_directory(
                source_dir=source_path,
                target_dir=target_dir,
                install_mode=install_mode,
                dry_run=dry_run,
            )
        except OSError as error:
            _mark_install_os_error(result=result, error=error, provider=plan.provider)
            return []
        if not artifacts:
            result["status"] = "failed_source_missing"
            result["message"] = f"未找到 provider wrapper 源目录：{source_path}"
            result["failure_reason_code"] = "wrapper_source_missing"
            result["failure_reason_detail"] = str(source_path)
            return []
        result["artifact_paths"] = [artifact.path for artifact in artifacts]
        install_artifacts = artifacts
    elif install_mode == "link":
        try:
            artifact = _link_wrapper(
                source_path=source_path,
                target_file=target_file,
                dry_run=dry_run,
            )
        except OSError as error:
            _mark_install_os_error(result=result, error=error, provider=plan.provider)
            return []
        result["artifact_paths"] = [str(target_file)]
        install_artifacts = [artifact]
    else:
        try:
            artifact = write_text(
                target_file,
                source_path.read_text(encoding="utf-8"),
                dry_run=dry_run,
                overwrite=True,
            )
        except OSError as error:
            _mark_install_os_error(result=result, error=error, provider=plan.provider)
            return []
        result["artifact_paths"] = [str(target_file)]
        install_artifacts = [artifact]
    result["status"] = "installed"
    result["message"] = f"installed {spec.wrapper_kind} wrapper into resolved {plan.resolved_target.target_scope} target"
    result["installation_mode"] = f"{plan.resolved_target.target_scope}_{spec.wrapper_kind}_{install_mode}"
    result["failure_reason_code"] = None
    result["failure_reason_detail"] = None
    return install_artifacts


def _mark_install_os_error(
    *, result: InstallerResult, error: OSError, provider: str
) -> None:
    """把安装阶段的文件系统错误收敛为稳定结果。"""

    if isinstance(error, PermissionError):
        result["status"] = "failed_permission"
        result["message"] = f"provider {provider} 目标目录不可写，自动安装失败。"
        result["failure_reason_code"] = "target_not_writable"
    else:
        result["status"] = "failed_filesystem"
        result["message"] = f"provider {provider} 安装时发生文件系统错误。"
        result["failure_reason_code"] = "filesystem_error"
    result["failure_reason_detail"] = str(error)


def _install_skill_directory(
    *, source_dir: Path, target_dir: Path, install_mode: str, dry_run: bool
) -> list[CommandArtifact]:
    if not source_dir.exists() or not source_dir.is_dir():
        return []
    artifacts: list[CommandArtifact] = []
    for source_file in _iter_template_files(source_dir):
        relative_path = source_file.relative_to(source_dir)
        target_file = target_dir / relative_path
        if install_mode == "link":
            artifacts.append(_link_wrapper(source_path=source_file, target_file=target_file, dry_run=dry_run))
        else:
            artifacts.append(
                write_text(
                    target_file,
                    source_file.read_text(encoding="utf-8"),
                    dry_run=dry_run,
                    overwrite=True,
                )
            )
    return artifacts


def _iter_template_files(source_dir: Path) -> Iterable[Path]:
    return sorted(path for path in source_dir.rglob("*") if path.is_file())


def _link_wrapper(*, source_path: Path, target_file: Path, dry_run: bool) -> CommandArtifact:
    existed_before_write = target_file.exists() or target_file.is_symlink()
    if dry_run:
        return CommandArtifact(
            path=str(target_file),
            kind="file",
            action="would_overwrite" if existed_before_write else "would_create",
            note="dry-run 未实际创建符号链接",
        )
    target_file.parent.mkdir(parents=True, exist_ok=True)
    if existed_before_write:
        target_file.unlink()
    target_file.symlink_to(source_path)
    return CommandArtifact(
        path=str(target_file),
        kind="file",
        action="overwritten" if existed_before_write else "created",
        note=f"符号链接已创建 -> {source_path}",
    )
