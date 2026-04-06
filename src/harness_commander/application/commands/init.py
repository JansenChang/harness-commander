"""init 命令应用层编排。"""

from __future__ import annotations

import logging
from pathlib import Path

from harness_commander.domain.models import CommandMessage, CommandResult, ResultStatus, failure_result
from harness_commander.infrastructure.docs import load_init_templates
from harness_commander.infrastructure.filesystem import ensure_directory, ensure_text_file
from harness_commander.infrastructure.templates import INIT_DIRECTORIES, validate_init_targets

LOGGER = logging.getLogger(__name__)


def run_init(root: Path, *, dry_run: bool) -> CommandResult:
    """初始化 Harness-Commander 所需目录与模板骨架。"""

    LOGGER.info("开始执行 init 命令 root=%s dry_run=%s", root, dry_run)

    template_result = load_init_templates(root)
    templates = template_result.templates

    issues = validate_init_targets(INIT_DIRECTORIES, list(templates.keys()))
    if issues:
        LOGGER.error("init 命令发现白名单违规 root=%s issues=%s", root, issues)
        return failure_result(
            "init",
            "初始化目标包含白名单之外的目录或文件，请修正模板配置。",
            CommandMessage(
                code="whitelist_violation",
                message="以下路径违反白名单约束：",
                detail={"issues": issues},
            ),
        )

    directory_artifacts = [
        ensure_directory(root / relative_path, dry_run=dry_run)
        for relative_path in INIT_DIRECTORIES
    ]
    file_artifacts = [
        ensure_text_file(root / relative_path, content, dry_run=dry_run)
        for relative_path, content in templates.items()
    ]
    artifacts = [*directory_artifacts, *file_artifacts]
    created_count = sum(
        artifact.action in {"created", "would_create"} for artifact in artifacts
    )
    skipped_count = sum(artifact.action == "skipped" for artifact in artifacts)
    summary = (
        "初始化完成，"
        f"共处理 {len(artifacts)} 个目录或文件，"
        f"其中 {created_count} 个为新增或将新增项，"
        f"{skipped_count} 个为已存在跳过项。"
    )
    LOGGER.info(
        "init 命令执行完成 root=%s created_count=%s skipped_count=%s template_source=%s",
        root,
        created_count,
        skipped_count,
        template_result.source,
    )
    return CommandResult(
        command="init",
        status=ResultStatus.SUCCESS,
        summary=summary,
        artifacts=artifacts,
        warnings=template_result.warnings,
        meta={
            "root": str(root),
            "dry_run": dry_run,
            "created_count": created_count,
            "skipped_count": skipped_count,
            "template_source": template_result.source,
        },
    )
