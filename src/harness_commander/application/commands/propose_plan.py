"""propose-plan 命令应用层编排。"""

from __future__ import annotations

import logging
from pathlib import Path

from harness_commander.domain.models import CommandResult, ResultStatus
from harness_commander.infrastructure.docs import (
    build_plan_path,
    ensure_governance_documents,
    render_plan_markdown,
)
from harness_commander.infrastructure.filesystem import write_text

LOGGER = logging.getLogger(__name__)


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
