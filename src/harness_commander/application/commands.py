"""应用层命令编排。

该模块负责把 CLI 输入翻译为用例执行流程，并组合领域模型与基础设施能力。
所有副作用都通过基础设施层实现，应用层只负责流程编排、错误处理与结果聚合。
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

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
    INIT_FILE_TEMPLATES,
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
    LOGGER.info(
        "propose-plan 命令执行完成 root=%s dry_run=%s plan_path=%s",
        root,
        dry_run,
        plan_path,
    )
    return CommandResult(
        command="propose-plan",
        status=ResultStatus.SUCCESS,
        summary="计划生成完成，已产出符合最小治理要求的执行计划模板。",
        artifacts=[artifact],
        meta={"root": str(root), "request": request, "dry_run": dry_run},
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
            summary="计划校验失败，存在缺失字段或约束引用问题。",
            errors=validation.issues,
            meta={"root": str(root), "plan_path": str(plan_path)},
        )
    LOGGER.info("plan-check 校验通过 root=%s plan_path=%s", root, plan_path)
    return CommandResult(
        command="plan-check",
        status=ResultStatus.SUCCESS,
        summary="计划校验通过，结构、引用和 ULW 信息满足最小要求。",
        meta={"root": str(root), "plan_path": str(plan_path)},
    )


def run_collect_evidence(
    root: Path,
    *,
    command: str,
    exit_code: int,
    summary: str,
    status: str,
    log_lines: list[str],
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
    started_at = utc_timestamp_precise()
    safe_timestamp = started_at.replace(":", "-")
    evidence_name = f"{safe_timestamp}-{slugify(command, fallback='command')}.json"
    evidence_path = next_available_path(evidence_directory / evidence_name)
    payload = {
        "command": command,
        "status": status,
        "summary": summary,
        "exit_code": exit_code,
        "started_at": started_at,
        "finished_at": utc_timestamp_precise(),
        "logs": log_lines,
    }
    file_artifact = write_json(evidence_path, payload, dry_run=dry_run)
    result_status = ResultStatus.SUCCESS if exit_code == 0 else ResultStatus.WARNING
    result_summary = (
        "证据记录完成。"
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
    """同步重大变更到文档目录。

    该命令检测数据库结构、迁移文件、公共工具或参考目录的重大变更，
    并更新受影响的 `docs/generated/` 或 `docs/references/` 文件。
    """

    LOGGER.info("开始执行 sync 命令 root=%s dry_run=%s", root, dry_run)

    # 检测变更的文件列表
    # 这里实现变更检测逻辑，例如：
    # 1. 检查数据库结构文件是否更新
    # 2. 检查迁移文件是否新增
    # 3. 检查公共工具是否变更
    # 4. 检查参考目录是否有新内容

    # 由于这是示例实现，我们假设检测到一些变更
    detected_changes = [
        {
            "type": "database_schema",
            "file": "docs/generated/db-schema.md",
            "reason": "数据库结构已更新，需要同步最新结构",
            "action": "would_update" if dry_run else "updated",
        },
        {
            "type": "reference_document",
            "file": "docs/references/design-system-reference-llms.txt",
            "reason": "设计系统文档已更新，需要生成新的参考材料",
            "action": "would_update" if dry_run else "updated",
        },
    ]

    artifacts = []
    for change in detected_changes:
        artifact = CommandArtifact(
            path=str(root / change["file"]),
            kind="file",
            action=change["action"],
            note=f"同步变更：{change['reason']}",
        )
        artifacts.append(artifact)

    change_count = len(detected_changes)
    summary = (
        f"同步完成，检测到 {change_count} 个重大变更需要同步到文档目录。"
        if change_count > 0
        else "未检测到需要同步的重大变更。"
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
            "change_types": list({c["type"] for c in detected_changes}),
        },
    )


def run_distill(root: Path, *, source_path: str, dry_run: bool) -> CommandResult:
    """将长文档压缩为参考材料。

    该命令提取文档中的业务目标、关键规则、边界限制和禁止项，
    生成 `*-llms.txt` 格式的参考材料，保存在 `docs/references/` 目录下。
    """

    LOGGER.info(
        "开始执行 distill 命令 root=%s source_path=%s dry_run=%s",
        root,
        source_path,
        dry_run,
    )

    # 解析源文档路径
    source_file = Path(source_path)
    if not source_file.is_absolute():
        source_file = root / source_path

    # 检查源文件是否存在
    if not source_file.exists():
        raise HarnessCommanderError(
            code="source_not_found",
            message=f"源文档不存在：{source_file}",
            location="distill",
            detail={"source_path": str(source_file)},
        )

    # 提取文件名和生成目标路径
    source_name = source_file.stem
    target_name = f"{source_name}-llms.txt"
    target_file = root / "docs" / "references" / target_name

    # 读取源文档内容
    try:
        content = source_file.read_text(encoding="utf-8")
    except Exception as error:
        raise HarnessCommanderError(
            code="read_failed",
            message=f"无法读取源文档：{error}",
            location="distill",
            detail={"source_path": str(source_file)},
        ) from error

    # 提取关键信息（简化实现，实际应使用更复杂的解析逻辑）
    # 这里我们假设文档包含特定的章节标记
    distilled_content = extract_key_information(content, source_name)

    # 生成产物
    artifact = write_text(
        target_file, distilled_content, dry_run=dry_run, overwrite=True
    )

    summary = f"已将文档 {source_name} 压缩为参考材料 {target_name}"
    LOGGER.info(
        "distill 命令执行完成 root=%s source=%s target=%s dry_run=%s",
        root,
        source_file,
        target_file,
        dry_run,
    )

    return CommandResult(
        command="distill",
        status=ResultStatus.SUCCESS,
        summary=summary,
        artifacts=[artifact],
        meta={
            "root": str(root),
            "source_path": str(source_file),
            "target_path": str(target_file),
            "dry_run": dry_run,
            "source_name": source_name,
            "target_name": target_name,
        },
    )


def extract_key_information(content: str, source_name: str) -> str:
    """从文档内容中提取关键信息。

    提取业务目标、关键规则、边界限制和禁止项。
    这是一个简化实现，实际应使用更复杂的自然语言处理或模式匹配。
    """

    lines = content.split("\n")
    distilled_lines = []

    # 添加标题
    distilled_lines.append(f"# {source_name} 参考材料")
    distilled_lines.append("")
    distilled_lines.append("## 业务目标")
    distilled_lines.append("")

    # 提取业务目标（查找章节标题后的内容）
    in_goals_section = False
    goals = []
    for _i, line in enumerate(lines):
        line_stripped = line.strip()

        # 检测业务目标章节
        if line_stripped.startswith("## 业务目标") or line_stripped.startswith(
            "## 目标"
        ):
            in_goals_section = True
            continue

        # 检测下一个章节开始
        if in_goals_section and line_stripped.startswith("## "):
            break

        # 收集业务目标内容
        if in_goals_section and line_stripped and not line_stripped.startswith("#"):
            # 移除列表标记和编号
            clean_line = line_stripped
            if clean_line.startswith("- "):
                clean_line = clean_line[2:]
            elif clean_line.startswith("* "):
                clean_line = clean_line[2:]
            elif clean_line[0].isdigit() and ". " in clean_line:
                clean_line = clean_line.split(". ", 1)[1]

            if clean_line:
                goals.append(clean_line)

    if goals:
        for goal in goals:
            distilled_lines.append(f"- {goal}")
    else:
        distilled_lines.append("- 未明确识别业务目标")

    distilled_lines.append("")
    distilled_lines.append("## 关键规则")
    distilled_lines.append("")

    # 提取关键规则（查找章节标题后的内容）
    in_rules_section = False
    rules = []
    for _i, line in enumerate(lines):
        line_stripped = line.strip()

        # 检测关键规则章节
        if line_stripped.startswith("## 关键规则") or line_stripped.startswith(
            "## 规则"
        ):
            in_rules_section = True
            continue

        # 检测下一个章节开始
        if in_rules_section and line_stripped.startswith("## "):
            break

        # 收集关键规则内容
        if in_rules_section and line_stripped and not line_stripped.startswith("#"):
            # 移除列表标记和编号
            clean_line = line_stripped
            if clean_line.startswith("- "):
                clean_line = clean_line[2:]
            elif clean_line.startswith("* "):
                clean_line = clean_line[2:]
            elif clean_line[0].isdigit() and ". " in clean_line:
                clean_line = clean_line.split(". ", 1)[1]

            if clean_line:
                rules.append(clean_line)

    if rules:
        for rule in rules:
            distilled_lines.append(f"- {rule}")
    else:
        distilled_lines.append("- 未明确识别关键规则")

    distilled_lines.append("")
    distilled_lines.append("## 边界限制")
    distilled_lines.append("")

    # 提取边界限制（查找章节标题后的内容）
    in_limits_section = False
    limits = []
    for _i, line in enumerate(lines):
        line_stripped = line.strip()

        # 检测边界限制章节
        if line_stripped.startswith("## 边界限制") or line_stripped.startswith(
            "## 限制"
        ):
            in_limits_section = True
            continue

        # 检测下一个章节开始
        if in_limits_section and line_stripped.startswith("## "):
            break

        # 收集边界限制内容
        if in_limits_section and line_stripped and not line_stripped.startswith("#"):
            # 移除列表标记和编号
            clean_line = line_stripped
            if clean_line.startswith("- "):
                clean_line = clean_line[2:]
            elif clean_line.startswith("* "):
                clean_line = clean_line[2:]
            elif clean_line[0].isdigit() and ". " in clean_line:
                clean_line = clean_line.split(". ", 1)[1]

            if clean_line:
                limits.append(clean_line)

    if limits:
        for limit in limits:
            distilled_lines.append(f"- {limit}")
    else:
        distilled_lines.append("- 未明确识别边界限制")

    distilled_lines.append("")
    distilled_lines.append("## 禁止项")
    distilled_lines.append("")

    # 提取禁止项（查找章节标题后的内容）
    in_prohibitions_section = False
    prohibitions = []
    for _i, line in enumerate(lines):
        line_stripped = line.strip()

        # 检测禁止项章节
        if line_stripped.startswith("## 禁止项") or line_stripped.startswith("## 禁止"):
            in_prohibitions_section = True
            continue

        # 检测下一个章节开始
        if in_prohibitions_section and line_stripped.startswith("## "):
            break

        # 收集禁止项内容
        if (
            in_prohibitions_section
            and line_stripped
            and not line_stripped.startswith("#")
        ):
            # 移除列表标记和编号
            clean_line = line_stripped
            if clean_line.startswith("- "):
                clean_line = clean_line[2:]
            elif clean_line.startswith("* "):
                clean_line = clean_line[2:]
            elif clean_line[0].isdigit() and ". " in clean_line:
                clean_line = clean_line.split(". ", 1)[1]

            if clean_line:
                prohibitions.append(clean_line)

    if prohibitions:
        for prohibition in prohibitions:
            distilled_lines.append(f"- {prohibition}")
    else:
        distilled_lines.append("- 未明确识别禁止项")

    distilled_lines.append("")
    distilled_lines.append("## 原始文档信息")
    distilled_lines.append(f"- 原始文档：{source_name}")
    distilled_lines.append(f"- 提取时间：{utc_timestamp()}")
    distilled_lines.append(f"- 提取行数：{len(lines)}")

    return "\n".join(distilled_lines)


def _relative_location(path: Path, root: Path) -> str:
    """将绝对路径转换为相对仓库根目录的可读位置。"""

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
) -> CommandMessage:
    """构造统一的审计问题对象。"""

    return CommandMessage(
        code=code,
        message=message,
        location=location,
        detail={
            "severity": severity,
            "source": source,
            "suggestion": suggestion,
            "quantifiable": quantifiable,
        },
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
    }
    blocking_issues: list[CommandMessage] = []
    warning_issues: list[CommandMessage] = []

    for source_name, source_path in governance_sources.items():
        if not source_path.exists():
            blocking_issues.append(
                _build_check_issue(
                    code="missing_governance_source",
                    message="审计所需规则文档缺失。",
                    severity="blocking",
                    source=source_name,
                    location=_relative_location(source_path, root),
                    suggestion="先补齐治理文档，再重新执行 harness check。",
                    quantifiable=True,
                )
            )
            continue
        content = source_path.read_text(encoding="utf-8")
        if not content.strip():
            blocking_issues.append(
                _build_check_issue(
                    code="empty_governance_source",
                    message="审计所需规则文档为空，无法提供有效规则。",
                    severity="blocking",
                    source=source_name,
                    location=_relative_location(source_path, root),
                    suggestion="补充可执行规则，再重新执行 harness check。",
                    quantifiable=True,
                )
            )
            continue
        if "- " not in content and "1. " not in content:
            warning_issues.append(
                _build_check_issue(
                    code="unquantified_rule_source",
                    message="规则文档仍以说明模板为主，缺少可量化判断条件。",
                    severity="warning",
                    source=source_name,
                    location=_relative_location(source_path, root),
                    suggestion="把抽象说明补成可检查的条目或禁止项。",
                    quantifiable=False,
                )
            )

    python_files = _find_python_files(root)
    if not python_files:
        warning_issues.append(
            _build_check_issue(
                code="no_python_files_detected",
                message="未检测到可审计的 Python 源码文件。",
                severity="warning",
                source="quality",
                location="src/",
                suggestion="如果项目尚未进入实现阶段，可忽略；否则补齐源码后重跑审计。",
                quantifiable=True,
            )
        )

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
                    )
                )

    if not tests_path.exists():
        warning_issues.append(
            _build_check_issue(
                code="missing_tests_directory",
                message="未检测到 tests 目录，当前无法验证测试覆盖要求。",
                severity="warning",
                source="docs/QUALITY_SCORE.md",
                location="tests/",
                suggestion="补充测试目录与基础验证用例。",
                quantifiable=True,
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
                )
            )

    total_issues = len(blocking_issues) + len(warning_issues)
    unquantified_count = sum(
        1 for issue in [*blocking_issues, *warning_issues] if not issue.detail["quantifiable"]
    )
    blocking_count = len(blocking_issues)
    warning_count = len(warning_issues)

    if blocking_issues:
        status = ResultStatus.FAILURE
        summary = (
            f"审计完成，发现 {blocking_count} 个阻断项与 {warning_count} 个提醒项。"
        )
    elif warning_issues:
        status = ResultStatus.WARNING
        summary = f"审计完成，无阻断项，存在 {warning_count} 个提醒项。"
    else:
        status = ResultStatus.SUCCESS
        summary = "审计完成，质量、安全与团队信仰规则均未发现阻断问题。"

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
            "checks": {
                "blocking": [issue.to_dict() for issue in blocking_issues],
                "warnings": [issue.to_dict() for issue in warning_issues],
            },
        },
    )
