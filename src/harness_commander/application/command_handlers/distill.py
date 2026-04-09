"""distill 命令的应用层编排。"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harness_commander.domain.models import (
    CommandArtifact,
    CommandMessage,
    CommandResult,
    HarnessCommanderError,
    ResultStatus,
)
from harness_commander.infrastructure.filesystem import utc_timestamp

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DistillDependencies:
    """封装 distill 运行时依赖，保持 facade patch 点稳定。"""

    resolve_effective_provider: Callable[..., tuple[str | None, str, bool]]
    provider_meta: Callable[[str], tuple[str | None, str | None]]
    distill_with_host_model: Callable[..., dict[str, list[str]]]
    host_model_error_cls: type[Exception]
    write_text: Callable[..., CommandArtifact]
    supported_providers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DistillProviderContext:
    """描述 distill 当前可用的 provider 事实。"""

    provider: str | None
    provider_source: str
    provider_configured: bool
    resolution_reason: str | None


@dataclass(frozen=True, slots=True)
class DistillExecutionResult:
    """描述一次 distill 执行的提炼结果和路径事实。"""

    distilled_content: str
    extraction_report: dict[str, Any]
    execution_path: str
    host_attempted: bool


def run_distill(
    root: Path,
    *,
    source_path: str,
    dry_run: bool,
    mode: str = "auto",
    provider: str | None = None,
    deps: DistillDependencies,
) -> CommandResult:
    """将长文档压缩为参考材料。"""

    provider_context = _resolve_distill_provider_context(
        root=root,
        mode=mode,
        provider=provider,
        dry_run=dry_run,
        deps=deps,
    )
    LOGGER.info(
        "开始执行 distill 命令 root=%s source_path=%s dry_run=%s mode=%s provider=%s provider_source=%s",
        root,
        source_path,
        dry_run,
        mode,
        provider_context.provider,
        provider_context.provider_source,
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

    try:
        content = source_file.read_text(encoding="utf-8")
    except Exception as error:
        raise HarnessCommanderError(
            code="read_failed",
            message=f"无法读取源文档：{error}",
            location="distill",
            detail={"source_path": str(source_file)},
        ) from error

    execution = _run_distill_extraction(
        content=content,
        source_name=source_name,
        mode=selected_mode,
        provider_context=provider_context,
        deps=deps,
    )
    distilled_content = execution.distilled_content
    extraction_report = execution.extraction_report
    extraction_source = extraction_report["extraction_source"]
    fallback_from = extraction_report["fallback_from"]
    fallback_reason = extraction_report["fallback_reason"]
    model_provider = extraction_report["model_provider"]
    model_name = extraction_report["model_name"]
    warnings: list[CommandMessage] = []
    errors: list[CommandMessage] = []
    unresolved_sections = extraction_report["unresolved_sections"]
    extracted_section_count = extraction_report["extracted_section_count"]
    section_sources = extraction_report["section_sources"]
    source_mapping_coverage = extraction_report["source_mapping_coverage"]

    if fallback_from:
        warnings.append(
            CommandMessage(
                code="distill_fallback_to_heuristic",
                message=_build_distill_fallback_message(fallback_reason),
                location=str(source_file),
                detail={
                    "source_path": str(source_file),
                    "fallback_from": fallback_from,
                    "fallback_reason": fallback_reason,
                    "execution_path": execution.execution_path,
                    "host_attempted": execution.host_attempted,
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

    status = (
        ResultStatus.FAILURE
        if errors
        else ResultStatus.WARNING if warnings else ResultStatus.SUCCESS
    )
    artifacts: list[CommandArtifact] = []
    if status != ResultStatus.FAILURE:
        artifacts.append(
            deps.write_text(target_file, distilled_content, dry_run=dry_run, overwrite=True)
        )

    summary = _build_distill_summary(
        status=status,
        source_name=source_name,
        target_name=target_name,
        dry_run=dry_run,
        fallback_from=fallback_from,
        fallback_reason=fallback_reason,
        unresolved_sections=unresolved_sections,
    )
    LOGGER.info(
        "distill 命令执行完成 root=%s source=%s target=%s dry_run=%s",
        root,
        source_file,
        target_file,
        dry_run,
    )

    return CommandResult(
        command="distill",
        status=status,
        summary=summary,
        artifacts=artifacts,
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
            "section_sources": section_sources,
            "source_mapping_coverage": source_mapping_coverage,
            "extraction_report": extraction_report,
            "distill_mode": selected_mode,
            "extraction_source": extraction_source,
            "fallback_from": fallback_from,
            "fallback_reason": fallback_reason,
            "model_provider": model_provider,
            "model_name": model_name,
            "provider": provider_context.provider,
            "provider_source": provider_context.provider_source,
            "execution_path": execution.execution_path,
            "host_attempted": execution.host_attempted,
            "host_first": extraction_report["host_first"],
            "supported_providers": list(deps.supported_providers),
        },
    )


def _resolve_distill_provider_context(
    *,
    root: Path,
    mode: str,
    provider: str | None,
    dry_run: bool,
    deps: DistillDependencies,
) -> DistillProviderContext:
    """把 distill 的 provider 解析为可选上下文。"""

    if mode == "heuristic":
        return DistillProviderContext(
            provider=None,
            provider_source="not_used",
            provider_configured=False,
            resolution_reason="heuristic_mode",
        )

    try:
        normalized_provider, provider_source, _ = deps.resolve_effective_provider(
            root,
            override=provider,
            persist_last_resolved=False,
            dry_run=dry_run,
        )
    except HarnessCommanderError as error:
        if error.code != "provider_not_configured" or mode == "host-model":
            raise
        return DistillProviderContext(
            provider=None,
            provider_source="deterministic_baseline",
            provider_configured=False,
            resolution_reason=error.code,
        )

    return DistillProviderContext(
        provider=normalized_provider,
        provider_source=provider_source,
        provider_configured=normalized_provider is not None,
        resolution_reason="resolved" if normalized_provider is not None else None,
    )


def _build_distill_summary(
    *,
    status: ResultStatus,
    source_name: str,
    target_name: str,
    dry_run: bool,
    fallback_from: str | None,
    fallback_reason: str | None,
    unresolved_sections: list[str],
) -> str:
    if status == ResultStatus.FAILURE:
        return f"输入材料 {source_name} 提炼不足，未生成参考材料 {target_name}。"

    if dry_run:
        summary = f"已完成输入材料 {source_name} 的参考材料预演，目标为 {target_name}。"
    else:
        summary = f"已将输入材料 {source_name} 压缩为参考材料 {target_name}。"

    notes: list[str] = []
    if fallback_from:
        notes.append(_build_distill_fallback_message(fallback_reason))
    if unresolved_sections:
        notes.append(f"仍有 {len(unresolved_sections)} 类核心 section 待人工复核。")
    if notes:
        summary = f"{summary} {' '.join(notes)}"
    return summary


def _build_distill_fallback_message(fallback_reason: str | None) -> str:
    if fallback_reason == "provider_not_configured":
        return "未找到可用 provider，已回退到规则提炼路径。"
    return "宿主模型结果不可用，已回退到规则提炼路径。"


def _classify_distill_source(source_file: Path) -> str:
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
    provider_context: DistillProviderContext,
    deps: DistillDependencies,
) -> DistillExecutionResult:
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
    host_attempted = False
    execution_path = "heuristic"

    if mode in {"host-model", "auto"}:
        if provider_context.provider is None:
            if mode == "auto":
                fallback_from = "host-model"
                fallback_reason = "provider_not_configured"
            else:
                raise HarnessCommanderError(
                    code="provider_not_configured",
                    message="当前模式需要可用 provider，请先执行 harness install-provider 或显式传入 --provider。",
                    location="provider",
                )
        else:
            model_provider, model_name = deps.provider_meta(provider_context.provider)
            host_attempted = True
            try:
                structured = deps.distill_with_host_model(
                    provider=provider_context.provider,
                    source_name=source_name,
                    content=content,
                )
                goals, rules, limits, prohibitions = _coerce_host_model_sections(structured)
            except (deps.host_model_error_cls, ValueError, TypeError, KeyError) as error:
                fallback_from = "host-model"
                fallback_reason = str(error)
            else:
                distilled_content, extraction_report = _render_distill_from_sections(
                    goals=goals,
                    rules=rules,
                    limits=limits,
                    prohibitions=prohibitions,
                    source_name=source_name,
                    source_meta={"host_model_used": True},
                    source_content=content,
                    mapping_strategy="host-model",
                )
                execution_path = "host-model"
                extraction_report.update(
                    {
                        "extraction_source": "host-model",
                        "fallback_from": None,
                        "fallback_reason": None,
                        "fallback": {
                            "applied": False,
                            "from": None,
                            "reason": None,
                        },
                        "model_provider": model_provider,
                        "model_name": model_name,
                        "execution_path": execution_path,
                        "host_attempted": host_attempted,
                        "host_first": _build_distill_host_first_fact(
                            mode=mode,
                            provider_context=provider_context,
                            execution_path=execution_path,
                            host_attempted=host_attempted,
                            fallback_from=None,
                            fallback_reason=None,
                        ),
                    }
                )
                return DistillExecutionResult(
                    distilled_content=distilled_content,
                    extraction_report=extraction_report,
                    execution_path=execution_path,
                    host_attempted=host_attempted,
                )

    distilled_content, extraction_report = extract_key_information(content, source_name)
    if fallback_from:
        execution_path = "heuristic_fallback"
    extraction_report.update(
        {
            "extraction_source": extraction_source,
            "fallback_from": fallback_from,
            "fallback_reason": fallback_reason,
            "fallback": {
                "applied": fallback_from is not None,
                "from": fallback_from,
                "reason": fallback_reason,
            },
            "model_provider": model_provider,
            "model_name": model_name,
            "execution_path": execution_path,
            "host_attempted": host_attempted,
            "host_first": _build_distill_host_first_fact(
                mode=mode,
                provider_context=provider_context,
                execution_path=execution_path,
                host_attempted=host_attempted,
                fallback_from=fallback_from,
                fallback_reason=fallback_reason,
            ),
        }
    )
    return DistillExecutionResult(
        distilled_content=distilled_content,
        extraction_report=extraction_report,
        execution_path=execution_path,
        host_attempted=host_attempted,
    )

def _build_distill_host_first_fact(
    *,
    mode: str,
    provider_context: DistillProviderContext,
    execution_path: str,
    host_attempted: bool,
    fallback_from: str | None,
    fallback_reason: str | None,
) -> dict[str, Any]:
    return {
        "mode": mode,
        "host_model_allowed": mode in {"host-model", "auto"},
        "preferred_path": "host-model" if mode in {"host-model", "auto"} else "heuristic",
        "provider": provider_context.provider,
        "provider_configured": provider_context.provider_configured,
        "provider_source": provider_context.provider_source,
        "provider_resolution_reason": provider_context.resolution_reason,
        "host_attempted": host_attempted,
        "selected_path": execution_path,
        "fallback_applied": fallback_from is not None,
        "fallback_from": fallback_from,
        "fallback_reason": fallback_reason,
    }


def _coerce_host_model_sections(
    structured: dict[str, Any],
) -> tuple[list[str], list[str], list[str], list[str]]:
    """验证宿主模型返回结构，避免不完整结果伪装成成功。"""

    if not isinstance(structured, dict):
        raise TypeError("host model distill result must be an object")

    sections: list[list[str]] = []
    for key in ("goals", "rules", "limits", "prohibitions"):
        value = structured[key]
        if not isinstance(value, list):
            raise TypeError(f"host model distill field {key} must be a list")
        normalized_items: list[str] = []
        for item in value:
            if not isinstance(item, str):
                raise TypeError(f"host model distill field {key} must contain strings")
            cleaned = item.strip()
            if cleaned:
                normalized_items.append(cleaned)
        sections.append(normalized_items)
    return tuple(sections)  # type: ignore[return-value]


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
        source_content=content,
        mapping_strategy="heuristic",
    )


def _render_distill_from_sections(
    *,
    goals: list[str],
    rules: list[str],
    limits: list[str],
    prohibitions: list[str],
    source_name: str,
    source_meta: dict[str, Any] | None = None,
    source_content: str | None = None,
    mapping_strategy: str = "heuristic",
) -> tuple[str, dict[str, Any]]:
    section_display_labels = {
        "goals": "业务目标",
        "rules": "关键规则",
        "limits": "边界限制",
        "prohibitions": "禁止项",
    }
    sections = {
        "goals": goals,
        "rules": rules,
        "limits": limits,
        "prohibitions": prohibitions,
    }
    unresolved_sections = [
        section_display_labels[name] for name, items in sections.items() if not items
    ]
    extracted_section_count = sum(1 for items in sections.values() if items)
    section_sources, source_mapping_coverage = _build_distill_source_mapping(
        sections=sections,
        source_content=source_content,
        mapping_strategy=mapping_strategy,
    )

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

    distilled_lines.extend(
        [
            "",
            "## 来源映射",
            f"- 映射策略：{source_mapping_coverage['mapping_strategy']}",
            f"- 映射覆盖：{source_mapping_coverage['mapped_items']}/{source_mapping_coverage['total_items']}",
        ]
    )
    for section_name, entries in section_sources.items():
        distilled_lines.extend(["", f"### {section_display_labels[section_name]}"])
        if not entries:
            distilled_lines.append("- 无提炼条目")
            continue
        for entry in entries:
            item = str(entry["text"])
            if entry["mapping_status"] == "mapped":
                distilled_lines.append(f"- {item} @ line {entry['line']}")
            else:
                distilled_lines.append(f"- {item} @ unmatched")

    return "\n".join(distilled_lines), {
        "sections": {
            "goals": len(goals),
            "rules": len(rules),
            "limits": len(limits),
            "prohibitions": len(prohibitions),
        },
        "unresolved_sections": unresolved_sections,
        "extracted_section_count": extracted_section_count,
        "section_item_counts": {name: len(items) for name, items in sections.items()},
        "section_sources": section_sources,
        "source_mapping_coverage": source_mapping_coverage,
        "mapping_summary": source_mapping_coverage,
    }


def _collect_section_items(lines: list[str], section_names: tuple[str, ...]) -> list[str]:
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
    cleaned = line.strip()
    if cleaned.startswith("- ") or cleaned.startswith("* "):
        cleaned = cleaned[2:]
    elif cleaned[:1].isdigit() and ". " in cleaned:
        cleaned = cleaned.split(". ", 1)[1]
    return cleaned.strip()


def _deduplicate_items(items: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


def _build_distill_source_mapping(
    *,
    sections: dict[str, list[str]],
    source_content: str | None,
    mapping_strategy: str,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    source_lines = source_content.splitlines() if source_content else []
    mapped_items = 0
    total_items = 0
    section_sources: dict[str, list[dict[str, Any]]] = {}

    for section_name, items in sections.items():
        entries: list[dict[str, Any]] = []
        for item in items:
            total_items += 1
            source_match = _locate_distill_source_line(item=item, source_lines=source_lines)
            if source_match is None:
                entries.append(
                    {
                        "text": item,
                        "mapping_status": "unmatched",
                        "line": None,
                        "snippet": None,
                        "mapping_strategy": mapping_strategy,
                    }
                )
                continue
            mapped_items += 1
            entries.append(
                {
                    "text": item,
                    "mapping_status": "mapped",
                    "line": source_match["line"],
                    "snippet": source_match["snippet"],
                    "mapping_strategy": mapping_strategy,
                }
            )
        section_sources[section_name] = entries

    unmatched_items = total_items - mapped_items
    source_mapping_coverage = {
        "mapping_strategy": mapping_strategy,
        "mapped_items": mapped_items,
        "total_items": total_items,
        "unmatched_items": unmatched_items,
        "mapped_ratio": round(mapped_items / total_items, 4) if total_items else 0.0,
        "coverage_ratio": round(mapped_items / total_items, 4) if total_items else 0.0,
    }
    return section_sources, source_mapping_coverage


def _locate_distill_source_line(
    *, item: str, source_lines: list[str]
) -> dict[str, Any] | None:
    normalized_item = _normalize_distill_match_text(item)
    if not normalized_item:
        return None

    for index, raw_line in enumerate(source_lines, start=1):
        stripped = raw_line.strip()
        if not stripped:
            continue
        cleaned = _clean_distill_line(stripped)
        normalized_line = _normalize_distill_match_text(cleaned)
        if not normalized_line:
            continue
        if normalized_item in normalized_line or normalized_line in normalized_item:
            return {"line": index, "snippet": cleaned[:120]}
    return None


def _normalize_distill_match_text(text: str) -> str:
    lowered = text.lower()
    compact = re.sub(r"\s+", "", lowered)
    return re.sub(r"[^\w\u4e00-\u9fff]", "", compact)


def _render_distilled_section(items: list[str], fallback: str) -> list[str]:
    if not items:
        return [f"- {fallback}"]
    return [f"- {item}" for item in items]
