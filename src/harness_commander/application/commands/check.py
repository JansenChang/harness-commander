"""check 命令应用层编排。"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from harness_commander.domain.models import (
    CommandMessage,
    CommandResult,
    HarnessCommanderError,
    ResultStatus,
)

from .shared import relative_location

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
                location=relative_location(source_path, root),
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
                    location=relative_location(source_path, root),
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
                    location=relative_location(source_path, root),
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
                    location=relative_location(path, root),
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
                        location=relative_location(test_file, root),
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
                relative_location(path, root)
            )
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
                "plan_files": [relative_location(path, root) for path in plan_files],
                "generated_files": [relative_location(path, root) for path in generated_files],
            },
            "checks": {
                "blocking": [issue.to_dict() for issue in blocking_issues],
                "warnings": [issue.to_dict() for issue in warning_issues],
                "all": [issue.to_dict() for issue in all_issues],
            },
        },
    )


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
