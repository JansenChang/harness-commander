"""plan-check 命令应用层编排。"""

from __future__ import annotations

import logging
from pathlib import Path

from harness_commander.domain.models import CommandResult, ResultStatus
from harness_commander.infrastructure.docs import ensure_governance_documents, validate_plan_document

LOGGER = logging.getLogger(__name__)


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
