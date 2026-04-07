"""应用层命令编排。

该模块负责把 CLI 输入翻译为用例执行流程，并组合领域模型与基础设施能力。
所有副作用都通过基础设施层实现，应用层只负责流程编排、错误处理与结果聚合。
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harness_commander.application.host_providers import (
    INSTALL_TARGETS,
    SUPPORTED_PROVIDERS,
    normalize_provider,
    provider_meta,
)
from harness_commander.application.provider_config import (
    load_provider_config,
    mark_provider_installed,
    resolve_effective_provider,
    save_provider_config,
)
from harness_commander.application.provider_installers import install_provider_target

MAX_SYNC_SUMMARY_FILES = 3
MAX_SYNC_SUMMARY_LINES = 2

from harness_commander.application.model_tasks import (
    HostModelError,
    distill_with_host_model,
)
from harness_commander.domain.models import (
    CommandArtifact,
    CommandMessage,
    CommandResult,
    HarnessCommanderError,
    ResultStatus,
    failure_result,
)
from harness_commander.infrastructure.docs import (
    build_plan_path,
    ensure_governance_documents,
    load_init_templates,
    parse_active_plan,
    parse_product_spec,
    render_plan_markdown,
    validate_plan_document,
)
from harness_commander.infrastructure.filesystem import (
    ensure_directory,
    ensure_text_file,
    next_available_path,
    slugify,
    utc_timestamp,
    utc_timestamp_precise,
    write_json,
    write_text,
)
from harness_commander.infrastructure.templates import (
    INIT_DIRECTORIES,
    validate_init_targets,
)

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class SyncRule:
    """定义可触发 sync 的输入集合与目标产物。"""

    change_type: str
    trigger_roots: tuple[str, ...]
    trigger_suffixes: tuple[str, ...]
    target_path: str
    reason: str


SYNC_RULES: tuple[SyncRule, ...] = (
    SyncRule(
        change_type="database_schema",
        trigger_roots=("migrations", "alembic", "db", "database", "schema"),
        trigger_suffixes=(".sql", ".ddl", ".prisma"),
        target_path="docs/generated/db-schema.md",
        reason="检测到数据库结构或迁移相关重大变更，需要刷新数据库快照。",
    ),
    SyncRule(
        change_type="shared_module",
        trigger_roots=("src", "shared", "packages", "libs"),
        trigger_suffixes=(".py", ".ts", ".tsx", ".js", ".jsx"),
        target_path="docs/references/uv-llms.txt",
        reason="检测到共享模块或公共实现变更，需要刷新 AI 参考材料。",
    ),
    SyncRule(
        change_type="build_runtime",
        trigger_roots=("scripts", "tools", "bin", "nixpacks", ".github", "deploy"),
        trigger_suffixes=(".nix", ".toml", ".yaml", ".yml", ".json", ".sh"),
        target_path="docs/references/nixpacks-llms.txt",
        reason="检测到构建、部署或运行方式变更，需要刷新工具参考材料。",
    ),
    SyncRule(
        change_type="governance_docs",
        trigger_roots=("docs",),
        trigger_suffixes=(".md", ".txt", ".rst"),
        target_path="docs/references/uv-llms.txt",
        reason="检测到核心规则文档或参考资料变更，需要刷新治理参考材料。",
    ),
    SyncRule(
        change_type="init_templates",
        trigger_roots=("src/harness_commander/init_templates",),
        trigger_suffixes=(".md", ".txt"),
        target_path="docs/references/uv-llms.txt",
        reason="检测到初始化模板结构变更，需要刷新模板参考材料。",
    ),
)


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


def run_sync(root: Path, *, dry_run: bool) -> CommandResult:
    """同步重大变更到文档目录。"""

    LOGGER.info("开始执行 sync 命令 root=%s dry_run=%s", root, dry_run)

    if not root.exists() or not root.is_dir():
        raise HarnessCommanderError(
            code="invalid_root",
            message="目标根目录不存在或不是目录，无法执行同步。",
            location=str(root),
        )

    trigger_files = _find_sync_triggers(root)
    artifacts: list[CommandArtifact] = []
    matched_changes: list[dict[str, Any]] = []

    for rule in SYNC_RULES:
        matched_inputs = [
            relative_path
            for relative_path in trigger_files
            if _matches_sync_rule(relative_path, rule)
            and relative_path != rule.target_path
        ]
        if not matched_inputs:
            continue

        content_summary = _build_sync_content_summary(root, matched_inputs)
        target_path = root / rule.target_path
        artifact = CommandArtifact(
            path=str(target_path),
            kind="file",
            action="would_update" if dry_run else "updated",
            note=(
                f"{rule.reason} 触发来源: "
                + ", ".join(matched_inputs[:3])
                + (" 等" if len(matched_inputs) > 3 else "")
            ),
        )
        if not dry_run:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(
                _render_sync_snapshot(rule, matched_inputs, content_summary),
                encoding="utf-8",
                newline="\n",
            )
        artifacts.append(artifact)
        matched_changes.append(
            {
                "type": rule.change_type,
                "target": rule.target_path,
                "inputs": matched_inputs,
                "reason": rule.reason,
                "content_summary": content_summary,
            }
        )

    change_count = len(matched_changes)
    if change_count == 0:
        summary = "未检测到需要同步的重大变更。"
    else:
        summary = (
            f"同步完成，识别到 {change_count} 类重大变更，"
            f"仅更新 {change_count} 个受影响产物。"
        )

    LOGGER.info(
        "sync 命令执行完成 root=%s dry_run=%s change_count=%s",
        root,
        dry_run,
        change_count,
    )

    return CommandResult(
        command="sync",
        status=ResultStatus.SUCCESS,
        summary=summary,
        artifacts=artifacts,
        meta={
            "root": str(root),
            "dry_run": dry_run,
            "change_count": change_count,
            "change_types": [change["type"] for change in matched_changes],
            "changes": matched_changes,
            "updated_targets": [change["target"] for change in matched_changes],
        },
    )


def run_distill(
    root: Path,
    *,
    source_path: str,
    dry_run: bool,
    mode: str = "heuristic",
    provider: str | None = None,
) -> CommandResult:
    """将长文档压缩为参考材料。"""

    normalized_provider: str | None = None
    provider_source = "not_used"
    if mode in {"host-model", "auto"}:
        normalized_provider, provider_source, _ = resolve_effective_provider(
            root,
            override=provider,
            persist_last_resolved=False,
            dry_run=dry_run,
        )
    LOGGER.info(
        "开始执行 distill 命令 root=%s source_path=%s dry_run=%s mode=%s provider=%s provider_source=%s",
        root,
        source_path,
        dry_run,
        mode,
        normalized_provider,
        provider_source,
    )

    source_file = Path(source_path)
    if not source_file.is_absolute():
        source_file = root / source_path

    if not source_file.exists():
        raise HarnessCommanderError(
            code="source_not_found",
            message=f"源文档不存在：{source_file}",
            location="distill",
            detail={"source_path": str(source_file)},
        )

    source_name = source_file.stem
    target_name = f"{source_name}-llms.txt"
    target_file = root / "docs" / "references" / target_name
    selected_mode = mode
    extraction_source = "heuristic"
    fallback_from: str | None = None
    fallback_reason: str | None = None
    model_provider: str | None = None
    model_name: str | None = None

    try:
        content = source_file.read_text(encoding="utf-8")
    except Exception as error:
        raise HarnessCommanderError(
            code="read_failed",
            message=f"无法读取源文档：{error}",
            location="distill",
            detail={"source_path": str(source_file)},
        ) from error

    distilled_content, extraction_report = _run_distill_extraction(
        content=content,
        source_name=source_name,
        mode=selected_mode,
        provider=normalized_provider,
    )
    extraction_source = extraction_report["extraction_source"]
    fallback_from = extraction_report["fallback_from"]
    fallback_reason = extraction_report["fallback_reason"]
    model_provider = extraction_report["model_provider"]
    model_name = extraction_report["model_name"]
    warnings: list[CommandMessage] = []
    errors: list[CommandMessage] = []
    unresolved_sections = extraction_report["unresolved_sections"]
    extracted_section_count = extraction_report["extracted_section_count"]

    if fallback_from:
        warnings.append(
            CommandMessage(
                code="distill_fallback_to_heuristic",
                message="宿主模型结果不可用，已回退到规则提炼路径。",
                location=str(source_file),
                detail={
                    "source_path": str(source_file),
                    "fallback_from": fallback_from,
                    "fallback_reason": fallback_reason,
                },
            )
        )

    if unresolved_sections:
        warnings.append(
            CommandMessage(
                code="partial_distillation",
                message="部分核心信息未被明确识别，请人工复核摘要是否完整。",
                location=str(source_file),
                detail={
                    "source_path": str(source_file),
                    "unresolved_sections": unresolved_sections,
                },
            )
        )

    if extracted_section_count == 0:
        errors.append(
            CommandMessage(
                code="distillation_insufficient",
                message="提炼结果不足以支撑参考材料，请补充更完整的结构化输入。",
                location=str(source_file),
                detail={
                    "source_path": str(source_file),
                    "extracted_section_count": extracted_section_count,
                    "unresolved_sections": unresolved_sections,
                },
            )
        )

    artifact = write_text(target_file, distilled_content, dry_run=dry_run, overwrite=True)

    summary = f"已将输入材料 {source_name} 压缩为参考材料 {target_name}。"
    LOGGER.info(
        "distill 命令执行完成 root=%s source=%s target=%s dry_run=%s",
        root,
        source_file,
        target_file,
        dry_run,
    )

    return CommandResult(
        command="distill",
        status=(
            ResultStatus.FAILURE
            if errors
            else ResultStatus.WARNING if warnings else ResultStatus.SUCCESS
        ),
        summary=summary,
        artifacts=[artifact],
        warnings=warnings,
        errors=errors,
        meta={
            "root": str(root),
            "source_path": str(source_file),
            "target_path": str(target_file),
            "dry_run": dry_run,
            "source_name": source_name,
            "target_name": target_name,
            "source_type": _classify_distill_source(source_file),
            "extracted_section_count": extracted_section_count,
            "unresolved_sections": unresolved_sections,
            "distill_mode": selected_mode,
            "extraction_source": extraction_source,
            "fallback_from": fallback_from,
            "fallback_reason": fallback_reason,
            "model_provider": model_provider,
            "model_name": model_name,
            "provider": normalized_provider,
            "provider_source": provider_source,
            "supported_providers": list(SUPPORTED_PROVIDERS),
        },
    )


def _classify_distill_source(source_file: Path) -> str:
    """识别 distill 输入材料类型。"""

    suffix = source_file.suffix.lower()
    if source_file.is_dir():
        return "code_directory"
    if suffix in {".md", ".txt", ".rst"}:
        return "document"
    return "external_reference"


def _run_distill_extraction(
    *,
    content: str,
    source_name: str,
    mode: str,
    provider: str | None,
) -> tuple[str, dict[str, Any]]:
    """按指定模式执行 distill 提炼。"""

    if mode not in {"heuristic", "host-model", "auto"}:
        raise HarnessCommanderError(
            code="invalid_distill_mode",
            message=f"不支持的 distill 模式：{mode}",
            location="distill",
            detail={"mode": mode},
        )

    extraction_source = "heuristic"
    fallback_from: str | None = None
    fallback_reason: str | None = None
    model_provider: str | None = None
    model_name: str | None = None

    if mode in {"host-model", "auto"}:
        if provider is None:
            raise HarnessCommanderError(
                code="provider_not_configured",
                message="当前模式需要可用 provider，请先执行 harness install-provider 或显式传入 --provider。",
                location="provider",
            )
        model_provider, model_name = provider_meta(provider)
        try:
            structured = distill_with_host_model(
                provider=provider,
                source_name=source_name,
                content=content,
            )
        except HostModelError as error:
            fallback_from = "host-model"
            fallback_reason = str(error)
        else:
            distilled_content, extraction_report = _render_distill_from_sections(
                goals=structured["goals"],
                rules=structured["rules"],
                limits=structured["limits"],
                prohibitions=structured["prohibitions"],
                source_name=source_name,
                source_meta={"host_model_used": True},
            )
            extraction_report.update(
                {
                    "extraction_source": "host-model",
                    "fallback_from": None,
                    "fallback_reason": None,
                    "model_provider": model_provider,
                    "model_name": model_name,
                }
            )
            return distilled_content, extraction_report

    distilled_content, extraction_report = extract_key_information(content, source_name)
    extraction_report.update(
        {
            "extraction_source": extraction_source,
            "fallback_from": fallback_from,
            "fallback_reason": fallback_reason,
            "model_provider": model_provider,
            "model_name": model_name,
        }
    )
    return distilled_content, extraction_report


def extract_key_information(content: str, source_name: str) -> tuple[str, dict[str, Any]]:
    """从文档内容中提取关键信息，并返回提炼报告。"""

    lines = content.split("\n")
    goals = _collect_section_items(lines, ("业务目标", "目标", "Why"))
    rules = _collect_section_items(
        lines,
        ("关键规则", "规则", "核心逻辑", "核心需求", "需求", "Business Logic"),
    )
    limits = _collect_section_items(
        lines,
        ("边界限制", "限制", "技术约束", "约束", "Scope", "Non-Goals"),
    )
    prohibitions = _collect_section_items(lines, ("禁止项", "禁止", "Non-Goals"))

    if not rules:
        rules = _collect_keyword_lines(lines, ("必须", "应", "需要", "不得", "禁止"))
    if not limits:
        limits = _collect_keyword_lines(lines, ("限制", "约束", "仅", "支持", "范围"))
    if not prohibitions:
        prohibitions = _collect_keyword_lines(lines, ("不得", "禁止", "不应", "不要"))

    return _render_distill_from_sections(
        goals=goals,
        rules=rules,
        limits=limits,
        prohibitions=prohibitions,
        source_name=source_name,
        source_meta={"提取行数": len(lines)},
    )


def _render_distill_from_sections(
    *,
    goals: list[str],
    rules: list[str],
    limits: list[str],
    prohibitions: list[str],
    source_name: str,
    source_meta: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    """把四类结构化信息渲染为标准 distill 输出。"""

    sections = {
        "业务目标": goals,
        "关键规则": rules,
        "边界限制": limits,
        "禁止项": prohibitions,
    }
    unresolved_sections = [name for name, items in sections.items() if not items]
    extracted_section_count = sum(1 for items in sections.values() if items)

    distilled_lines = [
        f"# {source_name} 参考材料",
        "",
        "## 业务目标",
        "",
        *_render_distilled_section(goals, "未明确识别业务目标"),
        "",
        "## 关键规则",
        "",
        *_render_distilled_section(rules, "未明确识别关键规则"),
        "",
        "## 边界限制",
        "",
        *_render_distilled_section(limits, "未明确识别边界限制"),
        "",
        "## 禁止项",
        "",
        *_render_distilled_section(prohibitions, "未明确识别禁止项"),
        "",
        "## 原始文档信息",
        f"- 原始文档：{source_name}",
        f"- 提取时间：{utc_timestamp()}",
    ]
    if source_meta:
        for key, value in source_meta.items():
            distilled_lines.append(f"- {key}: {value}")

    return "\n".join(distilled_lines), {
        "unresolved_sections": unresolved_sections,
        "extracted_section_count": extracted_section_count,
    }


def _relative_location(path: Path, root: Path) -> str:
    """将绝对路径转换为相对仓库根目录的可读位置。"""

    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)



def _collect_section_items(lines: list[str], section_names: tuple[str, ...]) -> list[str]:
    """按章节标题提取 bullet / 段落内容。"""

    normalized_names = tuple(name.lower() for name in section_names)
    in_section = False
    items: list[str] = []
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("## "):
            heading = line[3:].strip().lower()
            in_section = any(name in heading for name in normalized_names)
            continue
        if in_section and line.startswith("#"):
            break
        if in_section:
            cleaned = _clean_distill_line(line)
            if cleaned:
                items.append(cleaned)
    return _deduplicate_items(items)



def _collect_keyword_lines(lines: list[str], keywords: tuple[str, ...]) -> list[str]:
    """按关键词回收可能属于目标/规则/限制的行。"""

    items = []
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        cleaned = _clean_distill_line(line)
        if cleaned and any(keyword in cleaned for keyword in keywords):
            items.append(cleaned)
    return _deduplicate_items(items)



def _clean_distill_line(line: str) -> str:
    """清洗提炼出的单行内容。"""

    cleaned = line.strip()
    if cleaned.startswith("- ") or cleaned.startswith("* "):
        cleaned = cleaned[2:]
    elif cleaned[:1].isdigit() and ". " in cleaned:
        cleaned = cleaned.split(". ", 1)[1]
    return cleaned.strip()



def _deduplicate_items(items: list[str]) -> list[str]:
    """保序去重。"""

    seen: set[str] = set()
    deduped: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped



def _render_distilled_section(items: list[str], fallback: str) -> list[str]:
    """渲染 distill 分节内容。"""

    if not items:
        return [f"- {fallback}"]
    return [f"- {item}" for item in items]


def _build_sync_content_summary(root: Path, matched_inputs: list[str]) -> list[dict[str, str]]:
    """基于命中文件内容生成简短摘要，避免 sync 只回显路径。"""

    summaries: list[dict[str, str]] = []
    for relative_path in matched_inputs[:MAX_SYNC_SUMMARY_FILES]:
        file_path = root / relative_path
        excerpt = _summarize_sync_file(file_path)
        if not excerpt:
            continue
        summaries.append({"path": relative_path, "excerpt": excerpt})
    return summaries


def _summarize_sync_file(file_path: Path) -> str:
    """提取适合放入 sync 快照的简短内容片段。"""

    if not file_path.exists() or not file_path.is_file():
        return ""

    try:
        content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""

    lines = []
    for raw_line in content.splitlines():
        cleaned = raw_line.strip()
        if not cleaned:
            continue
        if cleaned.startswith(("#", "-", "*")) or "create table" in cleaned.lower():
            lines.append(cleaned)
        elif len(cleaned) <= 80:
            lines.append(cleaned)
        if len(lines) >= MAX_SYNC_SUMMARY_LINES:
            break

    if not lines:
        condensed = " ".join(content.split())
        if not condensed:
            return ""
        return condensed[:120]

    return " | ".join(lines)


def _render_sync_snapshot(
    rule: SyncRule,
    matched_inputs: list[str],
    content_summary: list[dict[str, str]],
) -> str:
    """渲染同步产物内容，记录触发来源、摘要与更新时间。"""

    lines = [
        f"# {rule.change_type} sync snapshot",
        "",
        "## 变更摘要",
        f"- 目标产物：{rule.target_path}",
        f"- 触发原因：{rule.reason}",
        f"- 同步时间：{utc_timestamp()}",
        f"- 命中文件数：{len(matched_inputs)}",
        "",
        "## 命中来源",
    ]
    lines.extend(f"- {path}" for path in matched_inputs)
    lines.extend(["", "## 内容摘录"])
    if content_summary:
        lines.extend(
            f"- {item['path']}: {item['excerpt']}" for item in content_summary
        )
    else:
        lines.append("- 未提取到可展示的内容摘录，请人工查看命中文件。")
    lines.extend(
        [
            "",
            "## 更新建议",
            "- 复核目标产物是否覆盖当前重大变更的核心约束。",
            "- 如需更高质量摘要，可在此基础上补充结构化说明与边界限制。",
        ]
    )
    return "\n".join(lines) + "\n"

def _find_sync_triggers(root: Path) -> list[str]:
    """收集可能触发文档同步的输入文件。"""

    ignored_parts = {".git", ".venv", "venv", "build", "dist", "__pycache__"}
    ignored_roots = {"docs/generated/evidence"}
    trigger_files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = _relative_location(path, root)
        if any(part in ignored_parts for part in path.parts):
            continue
        if any(
            relative == ignored or relative.startswith(f"{ignored}/")
            for ignored in ignored_roots
        ):
            continue
        trigger_files.append(path)
    return sorted({_relative_location(path, root) for path in trigger_files})


def _matches_sync_rule(relative_path: str, rule: SyncRule) -> bool:
    """判断某个文件是否命中指定 sync 规则。"""

    normalized = relative_path.replace("\\", "/")
    if normalized.startswith("docs/generated/") or normalized.startswith("docs/references/"):
        return False
    if rule.change_type == "governance_docs":
        allowed_files = {
            "ARCHITECTURE.md",
            "docs/PLANS.md",
            "docs/PRODUCT_SENSE.md",
            "docs/QUALITY_SCORE.md",
            "docs/RELIABILITY.md",
            "docs/SECURITY.md",
            "docs/design-docs/core-beliefs.md",
        }
        root_match = normalized in allowed_files
    else:
        root_match = any(
            normalized == trigger_root or normalized.startswith(f"{trigger_root}/")
            for trigger_root in rule.trigger_roots
        )
    suffix_match = normalized.endswith(rule.trigger_suffixes)
    return root_match and suffix_match


def _build_check_issue(
    *,
    code: str,
    message: str,
    severity: str,
    source: str,
    location: str,
    suggestion: str,
    quantifiable: bool,
    impact_scope: str | None = None,
) -> CommandMessage:
    """构造统一的审计问题对象。"""

    detail = {
        "severity": severity,
        "source": source,
        "suggestion": suggestion,
        "quantifiable": quantifiable,
    }
    if impact_scope:
        detail["impact_scope"] = impact_scope

    return CommandMessage(
        code=code,
        message=message,
        location=location,
        detail=detail,
    )


def _find_python_files(root: Path) -> list[Path]:
    """收集仓库内的 Python 文件，忽略虚拟环境与构建产物。"""

    ignored_parts = {".venv", "venv", "build", "dist", ".git", "__pycache__"}
    python_files: list[Path] = []
    for path in root.rglob("*.py"):
        if any(part in ignored_parts for part in path.parts):
            continue
        python_files.append(path)
    return sorted(python_files)


def _file_contains_secret_literal(path: Path) -> bool:
    """检查文件是否包含疑似硬编码凭据赋值。"""

    if not path.exists() or not path.is_file():
        return False
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return False
    secret_assignment = re.compile(
        r"(?i)(api_key|secret_key|access_token|private_key|password)\s*=\s*['\"][^'\"]{8,}['\"]"
    )
    return bool(secret_assignment.search(content))


def run_run_agents(
    root: Path,
    *,
    spec_path: str,
    plan_path: str,
    provider: str | None,
    dry_run: bool,
) -> CommandResult:
    """按 product spec 与 active exec plan 顺序编排多 agent 阶段。"""

    normalized_provider, provider_source, _ = resolve_effective_provider(
        root,
        override=provider,
        persist_last_resolved=False,
        dry_run=dry_run,
    )
    spec_file = Path(spec_path)
    if not spec_file.is_absolute():
        spec_file = root / spec_path
    plan_file = Path(plan_path)
    if not plan_file.is_absolute():
        plan_file = root / plan_path

    if not spec_file.exists():
        raise HarnessCommanderError(
            code="spec_not_found",
            message=f"产品规格文档不存在：{spec_file}",
            location=str(spec_file),
        )
    if not plan_file.exists():
        raise HarnessCommanderError(
            code="plan_not_found",
            message=f"执行计划文档不存在：{plan_file}",
            location=str(plan_file),
        )

    ensure_governance_documents(root)
    validation = validate_plan_document(root, plan_file)
    if validation.issues:
        return CommandResult(
            command="run-agents",
            status=ResultStatus.FAILURE,
            summary="执行计划不满足最小治理要求，已停止多 agent 编排。",
            errors=validation.issues,
            meta={
                "root": str(root),
                "spec_path": str(spec_file),
                "plan_path": str(plan_file),
                "provider": normalized_provider,
                "provider_source": provider_source,
                "issue_count": len(validation.issues),
            },
        )

    parsed_spec = parse_product_spec(spec_file)
    parsed_plan = parse_active_plan(plan_file)
    requirements_summary = _build_requirements_stage_summary(parsed_spec)
    plan_summary = _build_plan_stage_summary(parsed_plan)
    implement_summary = _build_implement_stage_summary(
        requirements_summary=requirements_summary,
        plan_summary=plan_summary,
        provider=normalized_provider,
    )
    verify_stage = _build_verify_stage(root)
    verify_details = verify_stage.get("details", {})
    verify_summary_text = str(verify_details.get("summary", "")).strip()
    verify_summary_missing = verify_stage["status"] == "success" and not verify_summary_text

    agent_runs = [
        {
            "stage": "requirements",
            "provider": normalized_provider,
            "status": "success",
            "summary": requirements_summary,
        },
        {
            "stage": "plan",
            "provider": normalized_provider,
            "status": "success",
            "summary": plan_summary,
        },
        {
            "stage": "implement",
            "provider": normalized_provider,
            "status": "success",
            "summary": implement_summary,
        },
        verify_stage,
    ]
    stage_contracts = [
        {
            "stage": "requirements",
            "status": "success",
            "inputs": {
                "spec_path": str(spec_file),
                "spec_title": parsed_spec.title,
            },
            "outputs": {
                "requirements_summary": requirements_summary,
            },
            "blocking_conditions": [],
            "fallback": {
                "applied": False,
                "reason": None,
                "from": None,
                "to": None,
            },
            "artifacts": [],
            "host_model_allowed": False,
        },
        {
            "stage": "plan",
            "status": "success",
            "inputs": {
                "plan_path": str(plan_file),
                "plan_title": parsed_plan.title,
            },
            "outputs": {
                "plan_summary": plan_summary,
                "ulw_count": len(parsed_plan.ulws),
            },
            "blocking_conditions": [],
            "fallback": {
                "applied": False,
                "reason": None,
                "from": None,
                "to": None,
            },
            "artifacts": [],
            "host_model_allowed": False,
        },
        {
            "stage": "implement",
            "status": "success",
            "inputs": {
                "requirements_summary": requirements_summary,
                "plan_summary": plan_summary,
                "provider": normalized_provider,
            },
            "outputs": {
                "implement_summary": implement_summary,
            },
            "blocking_conditions": [],
            "fallback": {
                "applied": False,
                "reason": None,
                "from": None,
                "to": None,
            },
            "artifacts": [],
            "host_model_allowed": False,
        },
        {
            "stage": "verify",
            "status": verify_stage["status"],
            "inputs": {
                "status_path": str(verify_details.get("status_path", "")),
                "summary_path": str(verify_details.get("summary_path", "")),
            },
            "outputs": {
                "verify_status": str(verify_details.get("verify_status", "missing")),
                "summary": verify_summary_text,
            },
            "blocking_conditions": (
                [
                    {
                        "code": "verify_not_ready_for_pr",
                        "message": "验证尚未通过，PR 摘要阶段被阻断。",
                        "blocked": True,
                    }
                ]
                if verify_stage["status"] != "success"
                else []
            ),
            "fallback": dict(verify_stage.get("fallback", {})),
            "artifacts": [],
            "host_model_allowed": False,
        },
    ]

    artifacts: list[CommandArtifact] = []
    warnings: list[CommandMessage] = []
    errors: list[CommandMessage] = []

    if verify_stage["status"] != "success":
        warnings.append(
            CommandMessage(
                code="verify_not_ready_for_pr",
                message="验证尚未通过，已阻断 PR 摘要整理阶段。",
                location=str(root / ".claude/tmp/last-verify.status"),
                detail={"verify_status": verify_stage["status"]},
            )
        )
        stage_contracts.append(
            {
                "stage": "pr-summary",
                "status": "warning",
                "inputs": {
                    "spec_title": parsed_spec.title,
                    "plan_title": parsed_plan.title,
                    "provider": normalized_provider,
                    "verify_status": verify_stage["status"],
                },
                "outputs": {
                    "generated": False,
                    "artifact_path": None,
                },
                "blocking_conditions": [
                    {
                        "code": "verify_not_ready_for_pr",
                        "message": "验证尚未通过，已阻断 PR 摘要整理阶段。",
                        "blocked": True,
                    }
                ],
                "fallback": {
                    "applied": False,
                    "reason": None,
                    "from": None,
                    "to": None,
                },
                "artifacts": [],
                "host_model_allowed": False,
            }
        )
        status = ResultStatus.WARNING
        summary = "多 agent 阶段编排完成，但验证未通过，PR 摘要未生成。"
    else:
        pr_summary_path = _build_pr_summary_path(root, parsed_plan.title)
        pr_summary_content = _render_pr_summary(
            spec_title=parsed_spec.title,
            plan_title=parsed_plan.title,
            provider=normalized_provider,
            agent_runs=agent_runs,
            verification_summary=verify_summary_text,
        )
        artifact = write_text(pr_summary_path, pr_summary_content, dry_run=dry_run, overwrite=False)
        artifacts.append(artifact)
        agent_runs.append(
            {
                "stage": "pr-summary",
                "provider": normalized_provider,
                "status": "success",
                "summary": f"已整理 PR 摘要：{pr_summary_path}",
                "artifact_path": str(pr_summary_path),
            }
        )
        stage_contracts.append(
            {
                "stage": "pr-summary",
                "status": "success",
                "inputs": {
                    "spec_title": parsed_spec.title,
                    "plan_title": parsed_plan.title,
                    "provider": normalized_provider,
                    "verify_status": verify_stage["status"],
                },
                "outputs": {
                    "generated": True,
                    "artifact_path": str(pr_summary_path),
                    "verification_summary_used": bool(verify_summary_text),
                },
                "blocking_conditions": [],
                "fallback": {
                    "applied": verify_summary_missing,
                    "reason": (
                        "verification_summary_missing"
                        if verify_summary_missing
                        else None
                    ),
                    "from": "verification-summary-file",
                    "to": (
                        "inline_placeholder_text"
                        if verify_summary_missing
                        else "verification-summary-file"
                    ),
                },
                "artifacts": [
                    {
                        "path": str(pr_summary_path),
                        "kind": "file",
                        "action": "would_create" if dry_run else "created",
                    }
                ],
                "host_model_allowed": False,
            }
        )
        status = ResultStatus.SUCCESS
        summary = "多 agent 阶段编排完成，验证通过并已生成 PR 摘要。"

    return CommandResult(
        command="run-agents",
        status=status,
        summary=summary,
        artifacts=artifacts,
        warnings=warnings,
        errors=errors,
        meta={
            "root": str(root),
            "spec_path": str(spec_file),
            "plan_path": str(plan_file),
            "provider": normalized_provider,
            "provider_source": provider_source,
            "supported_providers": list(SUPPORTED_PROVIDERS),
            "agent_runs": agent_runs,
            "stage_contracts": stage_contracts,
            "dry_run": dry_run,
        },
    )


def _build_requirements_stage_summary(parsed_spec: Any) -> str:
    """生成 requirements 阶段摘要。"""

    goals = parsed_spec.sections.get("业务目标")
    rules = parsed_spec.sections.get("核心逻辑") or parsed_spec.sections.get("关键规则")
    acceptance = parsed_spec.sections.get("验收标准")
    goal_text = "；".join(goals.items[:3]) if goals else "未显式提取到业务目标"
    rule_text = "；".join(rules.items[:3]) if rules else "未显式提取到关键规则"
    acceptance_text = (
        "；".join(acceptance.items[:2]) if acceptance and acceptance.items else "未显式提取到验收标准"
    )
    return f"需求提炼完成：目标={goal_text}；规则={rule_text}；验收={acceptance_text}。"


def _build_plan_stage_summary(parsed_plan: Any) -> str:
    """生成 plan 阶段摘要。"""

    scope = parsed_plan.sections.get("Scope")
    verification = parsed_plan.sections.get("Verification")
    ulw_count = len(parsed_plan.ulws)
    scope_text = "；".join(scope.items[:3]) if scope and scope.items else "未显式提取到范围项"
    verification_text = (
        "；".join(verification.items[:2])
        if verification and verification.items
        else "未显式提取到验证步骤"
    )
    return f"计划提炼完成：ULW={ulw_count} 个；范围={scope_text}；验证={verification_text}。"


def _build_implement_stage_summary(
    *, requirements_summary: str, plan_summary: str, provider: str
) -> str:
    """生成 implement 阶段摘要。"""

    return (
        f"实施阶段已按 {provider} 工作流生成执行摘要，先承接需求约束，再承接计划拆分。"
        f" requirements={requirements_summary} plan={plan_summary}"
    )


def _build_verify_stage(root: Path) -> dict[str, Any]:
    """读取现有验证状态文件并生成 verify 阶段结果。"""

    status_path = root / ".claude/tmp/last-verify.status"
    summary_path = root / ".claude/tmp/verification-summary.md"
    if not status_path.exists():
        return {
            "stage": "verify",
            "status": "warning",
            "summary": "未找到验证状态文件。",
            "details": {
                "status_path": str(status_path),
                "summary_path": str(summary_path),
                "verify_status": "missing",
                "summary": "",
            },
            "fallback": {
                "applied": False,
                "reason": None,
                "from": None,
                "to": None,
            },
        }

    verify_status = status_path.read_text(encoding="utf-8").strip().lower() or "unknown"
    verification_summary = (
        summary_path.read_text(encoding="utf-8").strip() if summary_path.exists() else ""
    )
    return {
        "stage": "verify",
        "status": "success" if verify_status == "pass" else "warning",
        "summary": f"验证状态：{verify_status}",
        "details": {
            "status_path": str(status_path),
            "summary_path": str(summary_path),
            "verify_status": verify_status,
            "summary": verification_summary,
        },
        "fallback": {
            "applied": verify_status == "pass" and not verification_summary,
            "reason": (
                "verification_summary_missing"
                if verify_status == "pass" and not verification_summary
                else None
            ),
            "from": "verification-summary-file",
            "to": (
                "inline_placeholder_text"
                if verify_status == "pass" and not verification_summary
                else "verification-summary-file"
            ),
        },
    }


def _build_pr_summary_path(root: Path, plan_title: str) -> Path:
    """生成 PR 摘要路径。"""

    summary_dir = root / "docs/generated/pr-summary"
    timestamp = utc_timestamp_precise().replace(":", "-")
    summary_path = next_available_path(
        summary_dir / f"{timestamp}-{slugify(plan_title, fallback='pr-summary')}.md"
    )
    return Path(summary_path)


def _render_pr_summary(
    *,
    spec_title: str,
    plan_title: str,
    provider: str,
    agent_runs: list[dict[str, Any]],
    verification_summary: str,
) -> str:
    """渲染最小 PR 摘要。"""

    run_lines = "\n".join(
        f"- {run['stage']}: {run['summary']}" for run in agent_runs
    )
    verification_block = verification_summary or "- 验证摘要文件存在但为空，请人工补充。"
    return (
        f"# PR Summary\n\n"
        f"## Summary\n"
        f"- Product spec: {spec_title}\n"
        f"- Active plan: {plan_title}\n"
        f"- Provider: {provider}\n\n"
        f"## Scope\n"
        f"{run_lines}\n\n"
        f"## Verification\n"
        f"{verification_block}\n\n"
        f"## Evidence\n"
        f"- 建议在提交前追加 harness collect-evidence 记录整轮执行事实。\n\n"
        f"## Risks / Follow-ups\n"
        f"- 如 provider 本地 CLI 不可用，应优先修复本地集成再继续自动化流程。\n"
        f"- 如验证状态不是 PASS，不应直接整理 PR。\n"
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
    artifacts: list[CommandArtifact] = [*install_artifacts]
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


def run_check(root: Path, *, dry_run: bool) -> CommandResult:
    """检查项目结构与治理文档的一致性。"""

    LOGGER.info("开始执行 check 命令 root=%s dry_run=%s", root, dry_run)

    if not root.exists() or not root.is_dir():
        raise HarnessCommanderError(
            code="invalid_root",
            message="目标根目录不存在或不是目录，无法执行审计。",
            location=str(root),
        )

    governance_sources = {
        "quality": root / "docs/QUALITY_SCORE.md",
        "security": root / "docs/SECURITY.md",
        "core_beliefs": root / "docs/design-docs/core-beliefs.md",
        "product": root / "docs/product-specs/v1/index.md",
    }
    source_labels = {
        "quality": "docs/QUALITY_SCORE.md",
        "security": "docs/SECURITY.md",
        "core_beliefs": "docs/design-docs/core-beliefs.md",
        "product": "docs/product-specs/v1/index.md",
    }
    blocking_issues: list[CommandMessage] = []
    warning_issues: list[CommandMessage] = []

    for source_name, source_path in governance_sources.items():
        source_label = source_labels[source_name]
        impact_scope = (
            "无法完成基于质量规则的审计。"
            if source_name == "quality"
            else "无法完成安全规则审计。"
            if source_name == "security"
            else "无法完成团队信仰规则审计。"
            if source_name == "core_beliefs"
            else "无法完成产品约束审计。"
        )
        if not source_path.exists():
            issue = _build_check_issue(
                code="missing_governance_source",
                message="审计所需规则文档缺失。",
                severity="warning" if source_name == "product" else "blocking",
                source=source_label,
                location=_relative_location(source_path, root),
                suggestion="先补齐治理文档，再重新执行 harness check。",
                quantifiable=True,
                impact_scope=impact_scope,
            )
            if source_name == "product":
                warning_issues.append(issue)
            else:
                blocking_issues.append(issue)
            continue
        content = source_path.read_text(encoding="utf-8")
        if not content.strip():
            blocking_issues.append(
                _build_check_issue(
                    code="empty_governance_source",
                    message="审计所需规则文档为空，无法提供有效规则。",
                    severity="blocking",
                    source=source_label,
                    location=_relative_location(source_path, root),
                    suggestion="补充可执行规则，再重新执行 harness check。",
                    quantifiable=True,
                    impact_scope=impact_scope,
                )
            )
            continue
        if "- " not in content and "1. " not in content:
            warning_issues.append(
                _build_check_issue(
                    code="unquantified_rule_source",
                    message="规则文档仍以说明模板为主，缺少可量化判断条件。",
                    severity="warning",
                    source=source_label,
                    location=_relative_location(source_path, root),
                    suggestion="把抽象说明补成可检查的条目或禁止项。",
                    quantifiable=False,
                    impact_scope="当前规则源只能给出人工提醒，不能形成机器可判断结论。",
                )
            )

    plan_files = sorted((root / "docs/exec-plans/active").glob("*.md")) if (root / "docs/exec-plans/active").exists() else []
    generated_files: list[Path] = []
    for generated_root in (root / "docs/generated", root / "docs/references"):
        if generated_root.exists():
            generated_files.extend(path for path in generated_root.rglob("*") if path.is_file())

    if not plan_files:
        warning_issues.append(
            _build_check_issue(
                code="missing_plan_targets",
                message="未检测到计划文件，默认检查对象不完整。",
                severity="warning",
                source="docs/product-specs/v1/index.md",
                location="docs/exec-plans/active/",
                suggestion="先生成或补齐计划文件，再重新执行审计。",
                quantifiable=True,
                impact_scope="当前无法验证计划文件是否满足默认检查要求。",
            )
        )

    if not generated_files:
        warning_issues.append(
            _build_check_issue(
                code="missing_generated_targets",
                message="未检测到生成文档或参考材料，默认检查对象不完整。",
                severity="warning",
                source="docs/product-specs/v1/index.md",
                location="docs/generated/ 或 docs/references/",
                suggestion="在执行 sync 或 distill 后重新运行审计。",
                quantifiable=True,
                impact_scope="当前无法验证生成文档和参考材料是否与变更保持同步。",
            )
        )

    python_files = _find_python_files(root)
    for path in python_files:
        if _file_contains_secret_literal(path):
            blocking_issues.append(
                _build_check_issue(
                    code="potential_secret_exposure",
                    message="检测到疑似敏感信息字面量或凭据字段。",
                    severity="blocking",
                    source="docs/SECURITY.md",
                    location=_relative_location(path, root),
                    suggestion="移除硬编码敏感信息，改为环境变量或安全配置注入。",
                    quantifiable=True,
                    impact_scope="仓库包含疑似明文凭据，存在泄露和误用风险。",
                )
            )

    tests_path = root / "tests"
    if tests_path.exists():
        for test_file in tests_path.rglob("*.py"):
            if _file_contains_secret_literal(test_file):
                warning_issues.append(
                    _build_check_issue(
                        code="secret_like_fixture",
                        message="测试目录中出现疑似敏感字段，请确认不是明文样例。",
                        severity="warning",
                        source="docs/SECURITY.md",
                        location=_relative_location(test_file, root),
                        suggestion="确认测试样例已脱敏，避免把真实密钥写入仓库。",
                        quantifiable=True,
                        impact_scope="测试样例可能把真实凭据或可复用密钥暴露到仓库历史中。",
                    )
                )
    else:
        warning_issues.append(
            _build_check_issue(
                code="missing_tests_directory",
                message="未检测到 tests 目录，当前无法验证测试覆盖要求。",
                severity="warning",
                source="docs/QUALITY_SCORE.md",
                location="tests/",
                suggestion="补充测试目录与基础验证用例。",
                quantifiable=True,
                impact_scope="当前只能基于代码静态迹象给出审计结果，无法验证测试覆盖要求。",
            )
        )

    duplicate_impls: dict[str, list[str]] = {}
    function_pattern = re.compile(r"^def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(")
    for path in python_files:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            match = function_pattern.match(line.strip())
            if not match:
                continue
            function_name = match.group(1)
            duplicate_impls.setdefault(function_name, []).append(_relative_location(path, root))
    for function_name, locations in sorted(duplicate_impls.items()):
        unique_locations = sorted(set(locations))
        if len(unique_locations) > 1 and function_name.startswith(("validate_", "ensure_")):
            warning_issues.append(
                _build_check_issue(
                    code="potential_parallel_implementation",
                    message=f"函数 `{function_name}` 在多个文件中重复定义，需确认是否平行造轮子。",
                    severity="warning",
                    source="docs/design-docs/core-beliefs.md",
                    location=", ".join(unique_locations),
                    suggestion="确认是否应复用既有封装，避免基础能力出现多份实现。",
                    quantifiable=True,
                    impact_scope="相近基础能力存在多份实现，后续维护和规则收敛成本会上升。",
                )
            )

    total_issues = len(blocking_issues) + len(warning_issues)
    all_issues = [*blocking_issues, *warning_issues]
    unquantified_count = sum(1 for issue in all_issues if not issue.detail["quantifiable"])
    blocking_count = len(blocking_issues)
    warning_count = len(warning_issues)
    blocking_reasons = [issue.message for issue in blocking_issues]

    if blocking_issues:
        status = ResultStatus.FAILURE
        summary = f"审计完成，发现 {blocking_count} 个阻断项与 {warning_count} 个提醒项。"
    elif warning_issues:
        status = ResultStatus.WARNING
        summary = f"审计完成，无阻断项，存在 {warning_count} 个提醒项。"
    else:
        status = ResultStatus.SUCCESS
        summary = "审计完成，质量、安全、团队信仰和产品规则均未发现阻断问题。"

    if unquantified_count:
        summary = f"{summary} 其中 {unquantified_count} 项规则源仍未量化。"

    LOGGER.info(
        "check 命令执行完成 root=%s dry_run=%s blocking=%s warning=%s unquantified=%s",
        root,
        dry_run,
        blocking_count,
        warning_count,
        unquantified_count,
    )

    return CommandResult(
        command="check",
        status=status,
        summary=summary,
        warnings=warning_issues,
        errors=blocking_issues,
        meta={
            "root": str(root),
            "dry_run": dry_run,
            "blocking_count": blocking_count,
            "warning_count": warning_count,
            "error_count": blocking_count,
            "issue_count": total_issues,
            "unquantified_count": unquantified_count,
            "blocking_reasons": blocking_reasons,
            "checked_targets": {
                "plan_files": [_relative_location(path, root) for path in plan_files],
                "generated_files": [_relative_location(path, root) for path in generated_files],
            },
            "checks": {
                "blocking": [issue.to_dict() for issue in blocking_issues],
                "warnings": [issue.to_dict() for issue in warning_issues],
                "all": [issue.to_dict() for issue in all_issues],
            },
        },
    )
