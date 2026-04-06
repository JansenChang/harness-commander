"""distill 命令应用层编排。"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from harness_commander.application.model_tasks import HostModelError, distill_with_host_model
from harness_commander.domain.models import (
    CommandArtifact,
    CommandMessage,
    CommandResult,
    HarnessCommanderError,
    ResultStatus,
)
from harness_commander.infrastructure.filesystem import utc_timestamp, write_text

from .shared import relative_location

LOGGER = logging.getLogger(__name__)


def run_distill(
    root: Path,
    *,
    raw_inputs: list[str],
    output_path: str | None,
    interactive: bool,
    dry_run: bool,
) -> CommandResult:
    """从文件、片段和说明生成 `.llms` 结构化上下文包。"""

    LOGGER.info(
        "开始执行 distill 命令 root=%s input_count=%s dry_run=%s interactive=%s",
        root,
        len(raw_inputs),
        dry_run,
        interactive,
    )

    inputs, instruction = _split_distill_cli_inputs(raw_inputs)
    resolved_inputs = [_resolve_distill_input(root, item) for item in inputs]
    bundled_content = _bundle_distill_inputs(resolved_inputs)
    structured = _run_distill_extraction(
        bundled_content=bundled_content,
        instruction=instruction,
        input_descriptions=[item["reference"] for item in resolved_inputs],
        interactive=interactive,
    )
    distilled_content, extraction_report = _render_distill_context_bundle(
        title=_build_distill_title(resolved_inputs),
        instruction=instruction,
        structured=structured,
        input_descriptions=[item["reference"] for item in resolved_inputs],
        interactive=interactive,
    )

    warnings: list[CommandMessage] = []
    errors: list[CommandMessage] = []
    unresolved_sections = extraction_report["unresolved_sections"]
    distilled_unit_count = extraction_report["distilled_unit_count"]

    if interactive:
        warnings.append(
            CommandMessage(
                code="interactive_followup_available",
                message="当前产物为首版上下文包，如需更细结构可继续通过对话收敛。",
                location="distill",
                detail={"interactive": True},
            )
        )

    if unresolved_sections:
        warnings.append(
            CommandMessage(
                code="partial_distillation",
                message="部分结构化上下文字段未被充分提炼，请人工复核。",
                location="distill",
                detail={
                    "unresolved_sections": unresolved_sections,
                    "inputs": [item["reference"] for item in resolved_inputs],
                },
            )
        )

    if distilled_unit_count == 0:
        errors.append(
            CommandMessage(
                code="distillation_insufficient",
                message="提炼结果不足以生成可用的 `.llms` 上下文包，请补充更完整的输入或说明。",
                location="distill",
                detail={
                    "inputs": [item["reference"] for item in resolved_inputs],
                    "distilled_unit_count": distilled_unit_count,
                    "unresolved_sections": unresolved_sections,
                },
            )
        )

    artifacts: list[CommandArtifact] = []
    unresolved_inputs: list[str] = []
    target_file = _resolve_distill_output_path(root, resolved_inputs, output_path)
    if not errors:
        artifacts.append(
            _write_distill_output(
                target_file=target_file,
                distilled_content=distilled_content,
                dry_run=dry_run,
            )
        )

    summary = (
        f"已基于 {len(resolved_inputs)} 个输入生成 `.llms` 结构化上下文包 {target_file.name}。"
    )
    LOGGER.info(
        "distill 命令执行完成 root=%s target=%s dry_run=%s",
        root,
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
        artifacts=artifacts,
        warnings=warnings,
        errors=errors,
        meta={
            "root": str(root),
            "inputs": [item["reference"] for item in resolved_inputs],
            "instruction": instruction,
            "output_path": str(target_file),
            "dry_run": dry_run,
            "interactive": interactive,
            "source_types": sorted({item["source_type"] for item in resolved_inputs}),
            "distilled_unit_count": distilled_unit_count,
            "unresolved_inputs": unresolved_inputs,
            "unresolved_sections": unresolved_sections,
        },
    )


def _split_distill_cli_inputs(raw_inputs: list[str]) -> tuple[list[str], str]:
    """将 CLI 位置参数拆分为输入材料与蒸馏说明。"""

    if len(raw_inputs) < 2:
        raise HarnessCommanderError(
            code="missing_instruction",
            message="distill 至少需要一个输入文件或片段，以及一段蒸馏说明。",
            location="distill",
            detail={"raw_inputs": raw_inputs},
        )
    instruction = raw_inputs[-1].strip()
    if not instruction:
        raise HarnessCommanderError(
            code="missing_instruction",
            message="distill 的蒸馏说明不能为空。",
            location="distill",
            detail={"raw_inputs": raw_inputs},
        )
    return raw_inputs[:-1], instruction


def _resolve_distill_input(root: Path, raw_input: str) -> dict[str, Any]:
    """解析 distill 的文件或片段输入。"""

    path_part, start_line, end_line = _parse_distill_input_reference(raw_input)
    source_file = Path(path_part)
    if not source_file.is_absolute():
        source_file = root / path_part

    if not source_file.exists():
        raise HarnessCommanderError(
            code="source_not_found",
            message=f"源文件不存在：{source_file}",
            location="distill",
            detail={"input": raw_input},
        )
    if not source_file.is_file():
        raise HarnessCommanderError(
            code="source_not_file",
            message=f"distill 当前仅支持文件输入：{source_file}",
            location="distill",
            detail={"input": raw_input},
        )

    try:
        content = source_file.read_text(encoding="utf-8")
    except Exception as error:
        raise HarnessCommanderError(
            code="read_failed",
            message=f"无法读取源文件：{error}",
            location="distill",
            detail={"input": raw_input, "source_path": str(source_file)},
        ) from error

    lines = content.splitlines()
    excerpt = content
    reference = relative_location(source_file, root)
    if start_line is not None:
        if end_line is None or start_line <= 0 or end_line < start_line or end_line > len(lines):
            raise HarnessCommanderError(
                code="invalid_input_range",
                message=f"片段范围非法：{raw_input}",
                location="distill",
                detail={"input": raw_input, "line_count": len(lines)},
            )
        excerpt = "\n".join(lines[start_line - 1 : end_line])
        reference = f"{reference}:{start_line}-{end_line}"

    return {
        "reference": reference,
        "source_path": str(source_file),
        "source_type": _classify_distill_source(source_file),
        "content": excerpt,
    }


def _parse_distill_input_reference(raw_input: str) -> tuple[str, int | None, int | None]:
    """拆分 `path` 或 `path:start-end` 输入。"""

    match = re.match(r"^(.*?):(\d+)-(\d+)$", raw_input)
    if not match:
        return raw_input, None, None
    return match.group(1), int(match.group(2)), int(match.group(3))


def _classify_distill_source(source_file: Path) -> str:
    """识别 distill 输入材料类型。"""

    suffix = source_file.suffix.lower()
    if suffix in {".md", ".txt", ".rst"}:
        return "document"
    if suffix in {".py", ".ts", ".tsx", ".js", ".jsx", ".java", ".go", ".rs", ".json", ".yaml", ".yml"}:
        return "code"
    return "mixed"


def _bundle_distill_inputs(resolved_inputs: list[dict[str, Any]]) -> str:
    """把多个输入合并为宿主模型可消费的单段文本。"""

    chunks: list[str] = []
    for item in resolved_inputs:
        chunks.extend(
            [
                f"## SOURCE: {item['reference']}",
                item["content"],
                "",
            ]
        )
    return "\n".join(chunks).strip()


def _run_distill_extraction(
    *,
    bundled_content: str,
    instruction: str,
    input_descriptions: list[str],
    interactive: bool,
) -> dict[str, Any]:
    """默认调用宿主模型执行 distill 提炼。"""

    try:
        result = distill_with_host_model(
            instruction=instruction,
            input_descriptions=input_descriptions,
            bundled_content=bundled_content,
            interactive=interactive,
        )
        return dict(result)
    except HostModelError as error:
        raise HarnessCommanderError(
            code="host_model_unavailable",
            message=f"宿主模型无法完成 distill 提炼：{error}",
            location="distill",
            detail={"inputs": input_descriptions},
        ) from error


def _render_distill_context_bundle(
    *,
    title: str,
    instruction: str,
    structured: dict[str, Any],
    input_descriptions: list[str],
    interactive: bool,
) -> tuple[str, dict[str, Any]]:
    """将结构化提炼结果渲染为 `.llms` 上下文包。"""

    summary = structured.get("summary", "")
    key_relationships = structured.get("key_relationships", [])
    reference_units = structured.get("reference_units", [])
    agent_guidance = structured.get("agent_guidance", [])
    sections = {
        "Distilled Summary": [summary] if summary else [],
        "Key Relationships": key_relationships,
        "Reference Units": reference_units,
        "Agent Guidance": agent_guidance,
    }
    unresolved_sections = [name for name, items in sections.items() if not items]
    distilled_unit_count = sum(len(items) for items in sections.values())

    lines = [
        f"# {title}",
        "",
        "## Package Role",
        "该产物是供下游 LLM / Agent 检索、理解与复用的结构化上下文包，而不是静态摘要。",
        "",
        "## Task",
        instruction,
        "",
        "## Inputs",
        *[f"- {item}" for item in input_descriptions],
        "",
        "## Distilled Summary",
        *([summary] if summary else ["待补充摘要"]),
        "",
        "## Key Relationships",
        *_render_distilled_section(key_relationships, "待补充关键关系"),
        "",
        "## Reference Units",
        *_render_distilled_section(reference_units, "待补充参考单元"),
        "",
        "## Agent Guidance",
        *_render_distilled_section(agent_guidance, "待补充 Agent 使用指引"),
        "",
        "## Build Info",
        f"- generated_at: {utc_timestamp()}",
        f"- interactive: {str(interactive).lower()}",
    ]

    return "\n".join(lines), {
        "unresolved_sections": unresolved_sections,
        "distilled_unit_count": distilled_unit_count,
    }


def _build_distill_title(resolved_inputs: list[dict[str, Any]]) -> str:
    """为 distill 产物生成标题。"""

    if len(resolved_inputs) == 1:
        return f"{Path(resolved_inputs[0]['source_path']).stem}.llms"
    return "distilled-context.llms"


def _resolve_distill_output_path(
    root: Path,
    resolved_inputs: list[dict[str, Any]],
    output_path: str | None,
) -> Path:
    """确定 distill 的输出路径。"""

    if output_path:
        target = Path(output_path)
        if not target.is_absolute():
            target = root / output_path
        if target.suffix:
            return target
        return target / "index.llms"

    if len(resolved_inputs) == 1:
        source_stem = Path(resolved_inputs[0]["source_path"]).stem
        return root / ".llms" / f"{source_stem}.llms"
    return root / ".llms" / "index.llms"


def _write_distill_output(
    *,
    target_file: Path,
    distilled_content: str,
    dry_run: bool,
) -> CommandArtifact:
    """写入 distill 产物，并把底层写入失败映射为稳定业务错误。"""

    try:
        return write_text(target_file, distilled_content, dry_run=dry_run, overwrite=True)
    except HarnessCommanderError as error:
        raise HarnessCommanderError(
            code="output_write_failed",
            message=f"无法写入 distill 输出：{error.message}",
            location=str(target_file),
            detail={"output_path": str(target_file)},
        ) from error
    except OSError as error:
        raise HarnessCommanderError(
            code="output_write_failed",
            message=f"无法写入 distill 输出：{error}",
            location=str(target_file),
            detail={"output_path": str(target_file)},
        ) from error


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
