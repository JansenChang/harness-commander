"""check 命令的应用层编排。"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from harness_commander.domain.models import (
    CommandMessage,
    CommandResult,
    HarnessCommanderError,
    ResultStatus,
)

LOGGER = logging.getLogger(__name__)


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

    plan_files = (
        sorted((root / "docs/exec-plans/active").glob("*.md"))
        if (root / "docs/exec-plans/active").exists()
        else []
    )
    generated_files: list[Path] = []
    for generated_root in (root / "docs/generated", root / "docs/references"):
        if generated_root.exists():
            generated_files.extend(
                path for path in generated_root.rglob("*") if path.is_file()
            )

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
            duplicate_impls.setdefault(function_name, []).append(
                _relative_location(path, root)
            )
    for function_name, locations in sorted(duplicate_impls.items()):
        unique_locations = sorted(set(locations))
        if len(unique_locations) > 1 and function_name.startswith(
            ("validate_", "ensure_")
        ):
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
    unquantified_count = sum(
        1 for issue in all_issues if not issue.detail["quantifiable"]
    )
    blocking_count = len(blocking_issues)
    warning_count = len(warning_issues)
    blocking_reasons = [issue.message for issue in blocking_issues]
    has_active_plan = bool(plan_files)
    health_score = _compute_check_health_score(
        blocking_count=blocking_count,
        warning_count=warning_count,
        unquantified_count=unquantified_count,
    )
    governance_entry = _build_check_governance_entry(
        blocking_count=blocking_count,
        warning_count=warning_count,
        has_active_plan=has_active_plan,
    )
    next_actions = _build_check_next_actions(
        blocking_issues=blocking_issues,
        warning_issues=warning_issues,
        has_active_plan=has_active_plan,
        governance_entry=governance_entry,
    )

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
            "health_score": health_score,
            "governance_entry": governance_entry,
            "next_actions": next_actions,
            "checked_targets": {
                "plan_files": [_relative_location(path, root) for path in plan_files],
                "generated_files": [
                    _relative_location(path, root) for path in generated_files
                ],
            },
            "checks": {
                "blocking": [issue.to_dict() for issue in blocking_issues],
                "warnings": [issue.to_dict() for issue in warning_issues],
                "all": [issue.to_dict() for issue in all_issues],
            },
        },
    )


def _relative_location(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


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


def _compute_check_health_score(
    *,
    blocking_count: int,
    warning_count: int,
    unquantified_count: int,
) -> int:
    score = 100 - (blocking_count * 35) - (warning_count * 7) - (unquantified_count * 3)
    return max(0, min(100, score))


def _build_check_governance_entry(
    *,
    blocking_count: int,
    warning_count: int,
    has_active_plan: bool,
) -> dict[str, Any]:
    if blocking_count > 0:
        status = "blocked"
        recommended_entrypoint = "harness check"
        rationale = "存在阻断项，需先修复阻断问题再进入执行入口。"
    elif warning_count > 0:
        status = "needs_attention"
        if has_active_plan:
            recommended_entrypoint = "harness run-agents"
            rationale = "当前无阻断项且 active 计划已存在，可继续进入 run-agents，但仍应关注提醒项。"
        else:
            recommended_entrypoint = "harness propose-plan"
            rationale = "当前无阻断项但缺少 active 计划，需先补齐计划入口。"
    else:
        status = "ready"
        recommended_entrypoint = "harness run-agents"
        rationale = "治理检查通过，可进入 run-agents 执行入口。"

    ready_for_run_agents = blocking_count == 0 and has_active_plan
    ready_for_clean_pass = blocking_count == 0 and warning_count == 0
    return {
        "status": status,
        "ready_for_run_agents": ready_for_run_agents,
        "ready_for_clean_pass": ready_for_clean_pass,
        "recommended_entrypoint": recommended_entrypoint,
        "rationale": rationale,
    }


def _build_check_next_actions(
    *,
    blocking_issues: list[CommandMessage],
    warning_issues: list[CommandMessage],
    has_active_plan: bool,
    governance_entry: dict[str, Any],
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []

    for issue in blocking_issues:
        actions.append(
            {
                "priority": "P0",
                "code": "resolve_blocking_issue",
                "title": issue.message,
                "reason": issue.detail.get("impact_scope") or issue.message,
                "type": "resolve_blocking_issue",
                "issue_code": issue.code,
                "summary": issue.message,
                "suggestion": issue.detail.get("suggestion"),
                "source": issue.detail.get("source"),
                "location": issue.location,
                "recommended_command": "harness check",
            }
        )

    if not has_active_plan:
        actions.append(
            {
                "priority": "P1",
                "code": "create_active_plan",
                "title": "补齐 active 计划入口",
                "reason": "当前缺少 active 计划文件，尚不满足进入 run-agents 的前置条件。",
                "type": "create_active_plan",
                "issue_code": "missing_plan_targets",
                "summary": "缺少 active 计划文件，当前不满足进入 run-agents 的前置条件。",
                "suggestion": "先执行 harness propose-plan 生成 active 计划，再回到 check 校验入口状态。",
                "source": "docs/PLANS.md",
                "location": "docs/exec-plans/active/",
                "recommended_command": "harness propose-plan",
            }
        )

    for issue in warning_issues:
        if issue.code == "missing_plan_targets":
            continue
        actions.append(
            {
                "priority": "P1",
                "code": "resolve_warning_issue",
                "title": issue.message,
                "reason": issue.detail.get("impact_scope") or issue.message,
                "type": "resolve_warning_issue",
                "issue_code": issue.code,
                "summary": issue.message,
                "suggestion": issue.detail.get("suggestion"),
                "source": issue.detail.get("source"),
                "location": issue.location,
                "recommended_command": "harness check",
            }
        )

    if not actions:
        actions.append(
            {
                "priority": "P2",
                "code": "proceed",
                "title": "继续进入执行入口",
                "reason": "当前未发现阻断项或提醒项，治理入口已就绪。",
                "type": "proceed",
                "issue_code": None,
                "summary": "治理入口已就绪，可进入下一阶段执行。",
                "suggestion": "执行 run-agents 前后各运行一次 check，保持入口状态持续可见。",
                "source": "docs/product-specs/v2/commands/run-agents/product.md",
                "location": "docs/exec-plans/active/",
                "recommended_command": "harness run-agents",
            }
        )
    elif governance_entry["status"] == "needs_attention" and governance_entry.get(
        "ready_for_run_agents"
    ):
        actions.append(
            {
                "priority": "P2",
                "code": "proceed_with_attention",
                "title": "带着提醒项继续进入执行入口",
                "reason": "当前没有阻断项，active 计划已存在，可继续进入 run-agents，但提醒项仍需持续跟踪。",
                "type": "proceed_with_attention",
                "issue_code": None,
                "summary": "当前可继续进入 run-agents，同时保留对提醒项的整改与复查。",
                "suggestion": "进入 run-agents 后保持提醒项可见，并在阶段结束后复跑 check 确认治理状态没有恶化。",
                "source": "docs/product-specs/v2/commands/check/product.md",
                "location": "docs/exec-plans/active/",
                "recommended_command": "harness run-agents",
            }
        )
    elif governance_entry["status"] == "blocked":
        actions.append(
            {
                "priority": "P1",
                "code": "recheck_after_fix",
                "title": "修复后复跑 check",
                "reason": "阻断项修复后需要再次确认治理入口状态。",
                "type": "recheck_after_fix",
                "issue_code": None,
                "summary": "完成阻断修复后必须复跑 check 确认入口状态。",
                "suggestion": "阻断项清零后再进入 run-agents。",
                "source": "docs/RELIABILITY.md",
                "location": "docs/",
                "recommended_command": "harness check",
            }
        )
    return actions


def _find_python_files(root: Path) -> list[Path]:
    ignored_parts = {".venv", "venv", "build", "dist", ".git", "__pycache__"}
    python_files: list[Path] = []
    for path in root.rglob("*.py"):
        if any(part in ignored_parts for part in path.parts):
            continue
        python_files.append(path)
    return sorted(python_files)


def _file_contains_secret_literal(path: Path) -> bool:
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
