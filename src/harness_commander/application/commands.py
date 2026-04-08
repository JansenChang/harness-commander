"""应用层命令外观。

该模块保留稳定的应用层导出面和测试 patch 入口。
具体命令实现已拆到 `application/command_handlers/`，避免再次回到超长单体模块。
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from harness_commander.application.command_handlers.bootstrap import (
    run_collect_evidence as _run_collect_evidence,
)
from harness_commander.application.command_handlers.bootstrap import (
    run_init as _run_init,
)
from harness_commander.application.command_handlers.bootstrap import (
    run_plan_check as _run_plan_check,
)
from harness_commander.application.command_handlers.bootstrap import (
    run_propose_plan as _run_propose_plan,
)
from harness_commander.application.command_handlers.check import run_check as _run_check
from harness_commander.application.command_handlers.distill import (
    DistillDependencies,
    run_distill as _run_distill,
)
from harness_commander.application.command_handlers.provider_install import (
    run_install_provider as _run_install_provider,
)
from harness_commander.application.command_handlers.run_agents import (
    RunAgentsDependencies,
    run_run_agents as _run_run_agents,
)
from harness_commander.application.command_handlers.sync import run_sync as _run_sync
from harness_commander.application.host_providers import (
    SUPPORTED_PROVIDERS,
    provider_meta,
)
from harness_commander.application.model_tasks import (
    HostModelError,
    distill_with_host_model,
)
from harness_commander.application.provider_config import resolve_effective_provider
from harness_commander.domain.models import (
    CommandMessage,
    CommandResult,
    HarnessCommanderError,
    failure_result,
)
from harness_commander.infrastructure.docs import (
    parse_active_plan,
    parse_product_spec,
    validate_plan_document,
)
from harness_commander.infrastructure.filesystem import (
    next_available_path,
    slugify,
    utc_timestamp_precise,
    write_text,
)

LOGGER = logging.getLogger(__name__)


def execute_command(
    command_name: str, handler: Callable[..., CommandResult], **kwargs: Any
) -> CommandResult:
    """统一执行命令并将异常转换为稳定结果。"""

    try:
        return handler(**kwargs)
    except HarnessCommanderError as error:
        LOGGER.error(
            "命令执行失败 command=%s code=%s location=%s detail=%s reason=%s",
            command_name,
            error.code,
            error.location,
            error.detail,
            error.message,
        )
        return failure_result(
            command_name,
            "命令执行失败，请根据错误信息修正输入或补齐缺失资源。",
            error.to_message(),
        )
    except Exception as error:
        LOGGER.exception("命令出现未预期异常 command=%s reason=%s", command_name, error)
        return failure_result(
            command_name,
            "命令执行失败，出现未预期异常。",
            CommandMessage(
                code="unexpected_error",
                message=str(error),
            ),
        )


def run_init(root: Path, *, dry_run: bool) -> CommandResult:
    """初始化 Harness-Commander 所需目录与模板骨架。"""

    return _run_init(root=root, dry_run=dry_run)


def run_propose_plan(root: Path, *, request: str, dry_run: bool) -> CommandResult:
    """根据自然语言需求生成计划文件。"""

    return _run_propose_plan(root=root, request=request, dry_run=dry_run)


def run_plan_check(root: Path, *, plan_path: Path) -> CommandResult:
    """校验计划文件是否满足最小治理要求。"""

    return _run_plan_check(root=root, plan_path=plan_path)


def run_collect_evidence(
    root: Path,
    *,
    command: str,
    exit_code: int,
    summary: str,
    status: str,
    log_lines: list[str],
    started_at: str | None,
    finished_at: str | None,
    artifact_paths: list[str],
    dry_run: bool,
) -> CommandResult:
    """生成命令执行证据文件。"""

    return _run_collect_evidence(
        root=root,
        command=command,
        exit_code=exit_code,
        summary=summary,
        status=status,
        log_lines=log_lines,
        started_at=started_at,
        finished_at=finished_at,
        artifact_paths=artifact_paths,
        dry_run=dry_run,
    )


def run_sync(root: Path, *, dry_run: bool) -> CommandResult:
    """同步重大变更到文档目录。"""

    return _run_sync(root=root, dry_run=dry_run)


def run_distill(
    root: Path,
    *,
    source_path: str,
    dry_run: bool,
    mode: str = "heuristic",
    provider: str | None = None,
) -> CommandResult:
    """将长文档压缩为参考材料。"""

    deps = DistillDependencies(
        resolve_effective_provider=resolve_effective_provider,
        provider_meta=provider_meta,
        distill_with_host_model=distill_with_host_model,
        host_model_error_cls=HostModelError,
        write_text=write_text,
        supported_providers=SUPPORTED_PROVIDERS,
    )
    return _run_distill(
        root=root,
        source_path=source_path,
        dry_run=dry_run,
        mode=mode,
        provider=provider,
        deps=deps,
    )


def run_run_agents(
    root: Path,
    *,
    spec_path: str,
    plan_path: str,
    provider: str | None,
    dry_run: bool,
) -> CommandResult:
    """按 product spec 与 active exec plan 顺序编排多 agent 阶段。"""

    deps = RunAgentsDependencies(
        resolve_effective_provider=resolve_effective_provider,
        supported_providers=SUPPORTED_PROVIDERS,
        run_check=run_check,
        validate_plan_document=validate_plan_document,
        parse_product_spec=parse_product_spec,
        parse_active_plan=parse_active_plan,
        write_text=write_text,
        next_available_path=next_available_path,
        slugify=slugify,
        utc_timestamp_precise=utc_timestamp_precise,
    )
    return _run_run_agents(
        root=root,
        spec_path=spec_path,
        plan_path=plan_path,
        provider=provider,
        dry_run=dry_run,
        deps=deps,
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

    return _run_install_provider(
        root=root,
        provider=provider,
        scope=scope,
        install_mode=install_mode,
        dry_run=dry_run,
    )


def run_check(root: Path, *, dry_run: bool) -> CommandResult:
    """检查项目结构与治理文档的一致性。"""

    return _run_check(root=root, dry_run=dry_run)
