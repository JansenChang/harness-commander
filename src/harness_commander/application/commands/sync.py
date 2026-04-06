"""sync 命令应用层编排。"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harness_commander.domain.models import (
    CommandArtifact,
    CommandResult,
    HarnessCommanderError,
    ResultStatus,
)
from harness_commander.infrastructure.filesystem import utc_timestamp

from .shared import relative_location

LOGGER = logging.getLogger(__name__)

MAX_SYNC_SUMMARY_FILES = 3
MAX_SYNC_SUMMARY_LINES = 2


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
        relative = relative_location(path, root)
        if any(part in ignored_parts for part in path.parts):
            continue
        if any(
            relative == ignored or relative.startswith(f"{ignored}/")
            for ignored in ignored_roots
        ):
            continue
        trigger_files.append(path)
    return sorted({relative_location(path, root) for path in trigger_files})


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
