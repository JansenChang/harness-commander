"""轻量命令的应用层编排实现。"""

from __future__ import annotations

import logging
from pathlib import Path

from harness_commander.domain.models import (
    CommandMessage,
    CommandResult,
    ResultStatus,
    failure_result,
)
from harness_commander.infrastructure.docs import (
    build_plan_path,
    ensure_governance_documents,
    load_init_templates,
    render_plan_markdown,
    validate_plan_document,
)
from harness_commander.infrastructure.filesystem import (
    ensure_directory,
    ensure_text_file,
    next_available_path,
    slugify,
    utc_timestamp_precise,
    write_text,
    write_json,
)
from harness_commander.infrastructure.templates import (
    INIT_DIRECTORIES,
    validate_init_targets,
)

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


def run_propose_plan(root: Path, *, request: str, dry_run: bool) -> CommandResult:
    """根据自然语言需求生成计划文件。"""

    LOGGER.info(
        "开始执行 propose-plan 命令 root=%s dry_run=%s request=%s",
        root,
        dry_run,
        request[:120],
    )
    ensure_governance_documents(root)
    plan_path = build_plan_path(root, request)
    content = render_plan_markdown(request)
    artifact = write_text(plan_path, content, dry_run=dry_run, overwrite=False)
    summary = "计划生成完成，已补齐治理文档引用并产出细粒度 ULW 计划。"
    LOGGER.info(
        "propose-plan 命令执行完成 root=%s dry_run=%s plan_path=%s",
        root,
        dry_run,
        plan_path,
    )
    return CommandResult(
        command="propose-plan",
        status=ResultStatus.SUCCESS,
        summary=summary,
        artifacts=[artifact],
        meta={
            "root": str(root),
            "request": request,
            "dry_run": dry_run,
            "plan_path": str(plan_path),
            "ulw_count": content.count("## ULW "),
            "references": [
                "ARCHITECTURE.md",
                "docs/PLANS.md",
                "docs/PRODUCT_SENSE.md",
                "docs/QUALITY_SCORE.md",
                "docs/RELIABILITY.md",
                "docs/SECURITY.md",
                "docs/design-docs/core-beliefs.md",
                "docs/product-specs/v1/index.md",
            ],
        },
    )


def run_plan_check(root: Path, *, plan_path: Path) -> CommandResult:
    """校验计划文件是否满足最小治理要求。"""

    LOGGER.info("开始执行 plan-check 命令 root=%s plan_path=%s", root, plan_path)
    ensure_governance_documents(root)
    validation = validate_plan_document(root, plan_path)
    if validation.issues:
        LOGGER.warning(
            "plan-check 发现问题 root=%s plan_path=%s issue_count=%s",
            root,
            plan_path,
            len(validation.issues),
        )
        return CommandResult(
            command="plan-check",
            status=ResultStatus.FAILURE,
            summary="计划校验失败，存在结构缺失、引用缺失或 ULW 不完整问题。",
            errors=validation.issues,
            meta={
                "root": str(root),
                "plan_path": str(plan_path),
                "issue_count": len(validation.issues),
                "issues": [issue.to_dict() for issue in validation.issues],
            },
        )
    LOGGER.info("plan-check 校验通过 root=%s plan_path=%s", root, plan_path)
    return CommandResult(
        command="plan-check",
        status=ResultStatus.SUCCESS,
        summary="计划校验通过，结构章节、治理引用和 ULW 字段均满足要求。",
        meta={"root": str(root), "plan_path": str(plan_path), "issue_count": 0},
    )


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

    LOGGER.info(
        "开始执行 collect-evidence 命令 root=%s command=%s exit_code=%s status=%s dry_run=%s",
        root,
        command,
        exit_code,
        status,
        dry_run,
    )
    evidence_directory = root / "docs/generated/evidence"
    directory_artifact = ensure_directory(evidence_directory, dry_run=dry_run)
    recorded_started_at = started_at or utc_timestamp_precise()
    recorded_finished_at = finished_at or utc_timestamp_precise()
    safe_timestamp = recorded_started_at.replace(":", "-")
    evidence_name = f"{safe_timestamp}-{slugify(command, fallback='command')}.json"
    evidence_path = next_available_path(evidence_directory / evidence_name)
    payload = {
        "command": command,
        "status": status,
        "summary": summary,
        "exit_code": exit_code,
        "started_at": recorded_started_at,
        "finished_at": recorded_finished_at,
        "logs": log_lines,
        "artifacts": artifact_paths,
    }
    file_artifact = write_json(evidence_path, payload, dry_run=dry_run)
    result_status = ResultStatus.SUCCESS if exit_code == 0 else ResultStatus.WARNING
    result_summary = (
        "证据记录完成，已保留执行事实、时间范围、关键日志和产物路径。"
        if exit_code == 0
        else "证据记录完成，但被记录命令本身为失败状态。"
    )
    warnings = []
    if exit_code != 0:
        warnings.append(
            CommandMessage(
                code="captured_failed_execution",
                message="证据已保留，但被记录的命令返回了非零退出码。",
                detail={"exit_code": exit_code},
            )
        )
    LOGGER.info(
        "collect-evidence 命令执行完成 root=%s evidence_path=%s result_status=%s",
        root,
        evidence_path,
        result_status.value,
    )
    return CommandResult(
        command="collect-evidence",
        status=result_status,
        summary=result_summary,
        artifacts=[directory_artifact, file_artifact],
        warnings=warnings,
        meta={
            "root": str(root),
            "evidence_path": str(evidence_path),
            "dry_run": dry_run,
            "record": payload,
        },
    )
