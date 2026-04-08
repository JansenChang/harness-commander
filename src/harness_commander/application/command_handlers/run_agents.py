"""run-agents 命令的应用层编排。"""

from __future__ import annotations

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


@dataclass(frozen=True, slots=True)
class RunAgentsDependencies:
    """封装 run-agents 对外部能力的依赖，保持 facade patch 点稳定。"""

    resolve_effective_provider: Callable[..., tuple[str | None, str, bool]]
    supported_providers: tuple[str, ...]
    run_check: Callable[..., CommandResult]
    validate_plan_document: Callable[..., Any]
    parse_product_spec: Callable[[Path], Any]
    parse_active_plan: Callable[[Path], Any]
    write_text: Callable[..., CommandArtifact]
    next_available_path: Callable[[Path], Path]
    slugify: Callable[[str], str]
    utc_timestamp_precise: Callable[[], str]


def run_run_agents(
    root: Path,
    *,
    spec_path: str,
    plan_path: str,
    provider: str | None,
    dry_run: bool,
    deps: RunAgentsDependencies,
) -> CommandResult:
    """按 product spec 与 active exec plan 顺序编排多 agent 阶段。"""

    normalized_provider, provider_source, _ = deps.resolve_effective_provider(
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

    check_result = deps.run_check(root, dry_run=True)
    check_meta = dict(check_result.meta) if isinstance(check_result.meta, dict) else {}
    raw_governance_entry = check_meta.get("governance_entry")
    check_governance_entry = (
        dict(raw_governance_entry) if isinstance(raw_governance_entry, dict) else {}
    )
    raw_next_actions = check_meta.get("next_actions")
    raw_checks = check_meta.get("checks")
    missing_check_fields: list[str] = []
    if "health_score" not in check_meta:
        missing_check_fields.append("health_score")
    if not isinstance(raw_governance_entry, dict):
        missing_check_fields.append("governance_entry")
    if not isinstance(raw_next_actions, list):
        missing_check_fields.append("next_actions")
    if not isinstance(raw_checks, dict):
        missing_check_fields.append("checks")
    check_warning_codes = {warning.code for warning in check_result.warnings}
    explicit_plan_override_applied = (
        plan_file.exists() and "missing_plan_targets" in check_warning_codes
    )
    preflight_ready_for_run_agents = check_result.status != ResultStatus.FAILURE
    if check_governance_entry:
        preflight_ready_for_run_agents = bool(
            check_governance_entry.get(
                "ready_for_run_agents",
                preflight_ready_for_run_agents,
            )
        )
    if explicit_plan_override_applied:
        preflight_ready_for_run_agents = True
        check_governance_entry["ready_for_run_agents"] = True
        check_governance_entry["recommended_entrypoint"] = "harness run-agents"
        check_governance_entry["rationale"] = (
            "已显式指定 --plan 且路径存在，run-agents preflight 判定可继续。"
        )

    blocking_count = (
        check_meta.get("blocking_count")
        if isinstance(check_meta.get("blocking_count"), int)
        else len(check_result.errors)
    )
    warning_count = (
        check_meta.get("warning_count")
        if isinstance(check_meta.get("warning_count"), int)
        else len(check_result.warnings)
    )
    check_stage_summary = check_result.summary
    if explicit_plan_override_applied:
        check_stage_summary = (
            f"{check_stage_summary} 已基于显式 --plan 修正 run-agents 前置可继续判定。"
        )
    check_agent_run = {
        "stage": "check",
        "provider": "harness",
        "status": (
            ResultStatus.FAILURE.value
            if missing_check_fields
            else check_result.status.value
        ),
        "summary": check_stage_summary,
    }
    check_stage_contract = {
        "stage": "check",
        "status": (
            ResultStatus.FAILURE.value
            if missing_check_fields
            else check_result.status.value
        ),
        "inputs": {
            "root": str(root),
            "spec_path": str(spec_file),
            "plan_path": str(plan_file),
            "dry_run": True,
        },
        "outputs": {
            "blocking_count": blocking_count,
            "warning_count": warning_count,
            "health_score": check_meta.get("health_score"),
            "governance_entry_status": check_governance_entry.get("status"),
            "governance_entry": check_governance_entry,
            "ready_for_run_agents": preflight_ready_for_run_agents,
            "explicit_plan_override_applied": explicit_plan_override_applied,
            "next_actions_count": len(check_meta.get("next_actions", [])),
            "missing_required_fields": missing_check_fields,
        },
        "blocking_conditions": (
            [
                {
                    "code": "check_preflight_meta_incomplete",
                    "message": "check 前置门结果缺少必要治理字段，已按保守策略阻断。",
                    "blocked": True,
                }
            ]
            if missing_check_fields
            else [
                {
                    "code": "check_preflight_failed",
                    "message": "check 前置门失败，run-agents 已停止后续阶段。",
                    "blocked": True,
                }
            ]
            if check_result.status == ResultStatus.FAILURE
            else [
                {
                    "code": "check_preflight_warning",
                    "message": "check 前置门存在提醒项，但当前策略允许继续执行。",
                    "blocked": False,
                }
            ]
            if check_result.status == ResultStatus.WARNING
            else []
        ),
        "fallback": {
            "applied": False,
            "reason": None,
            "from": None,
            "to": None,
        },
        "artifacts": [],
        "host_model_allowed": False,
    }
    preflight_meta = {
        "status": check_result.status.value,
        "ready_for_run_agents": preflight_ready_for_run_agents,
        "explicit_plan_override_applied": explicit_plan_override_applied,
        "governance_entry": check_governance_entry,
    }

    if missing_check_fields:
        return CommandResult(
            command="run-agents",
            status=ResultStatus.FAILURE,
            summary="check 前置门结果不完整，已按保守策略停止多 agent 编排。",
            warnings=list(check_result.warnings),
            errors=[
                *list(check_result.errors),
                CommandMessage(
                    code="check_preflight_meta_incomplete",
                    message="check 前置门结果缺少必要治理字段，无法安全进入 run-agents。",
                    location=str(root),
                    detail={"missing_fields": missing_check_fields},
                ),
            ],
            meta={
                "root": str(root),
                "spec_path": str(spec_file),
                "plan_path": str(plan_file),
                "provider": normalized_provider,
                "provider_source": provider_source,
                "supported_providers": list(deps.supported_providers),
                "agent_runs": [check_agent_run],
                "stage_contracts": [check_stage_contract],
                "check_preflight": preflight_meta,
                "dry_run": dry_run,
            },
        )

    if check_result.status == ResultStatus.FAILURE:
        return CommandResult(
            command="run-agents",
            status=ResultStatus.FAILURE,
            summary=f"check 前置门未通过，已停止多 agent 编排。{check_stage_summary}",
            warnings=list(check_result.warnings),
            errors=list(check_result.errors),
            meta={
                "root": str(root),
                "spec_path": str(spec_file),
                "plan_path": str(plan_file),
                "provider": normalized_provider,
                "provider_source": provider_source,
                "supported_providers": list(deps.supported_providers),
                "agent_runs": [check_agent_run],
                "stage_contracts": [check_stage_contract],
                "check_preflight": preflight_meta,
                "dry_run": dry_run,
            },
        )

    validation = deps.validate_plan_document(root, plan_file)
    if validation.issues:
        return CommandResult(
            command="run-agents",
            status=ResultStatus.FAILURE,
            summary="执行计划不满足最小治理要求，已停止多 agent 编排。",
            warnings=list(check_result.warnings),
            errors=validation.issues,
            meta={
                "root": str(root),
                "spec_path": str(spec_file),
                "plan_path": str(plan_file),
                "provider": normalized_provider,
                "provider_source": provider_source,
                "supported_providers": list(deps.supported_providers),
                "agent_runs": [check_agent_run],
                "stage_contracts": [check_stage_contract],
                "check_preflight": preflight_meta,
                "issue_count": len(validation.issues),
            },
        )

    parsed_spec = deps.parse_product_spec(spec_file)
    parsed_plan = deps.parse_active_plan(plan_file)
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
    verify_summary_missing = (
        verify_stage["status"] == "success" and not verify_summary_text
    )

    agent_runs = [
        check_agent_run,
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
        check_stage_contract,
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
    warnings: list[CommandMessage] = list(check_result.warnings)
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
        pr_summary_path = _build_pr_summary_path(
            root=root,
            plan_title=parsed_plan.title,
            next_available_path=deps.next_available_path,
            slugify=deps.slugify,
            utc_timestamp_precise=deps.utc_timestamp_precise,
        )
        pr_summary_content = _render_pr_summary(
            spec_title=parsed_spec.title,
            plan_title=parsed_plan.title,
            provider=normalized_provider,
            agent_runs=agent_runs,
            verification_summary=verify_summary_text,
        )
        artifact = deps.write_text(
            pr_summary_path,
            pr_summary_content,
            dry_run=dry_run,
            overwrite=False,
        )
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

    if check_result.status == ResultStatus.WARNING:
        if status == ResultStatus.SUCCESS:
            status = ResultStatus.WARNING
            summary = "多 agent 阶段编排完成并生成 PR 摘要，但 check 前置审计存在提醒项。"
        elif "check 前置审计存在提醒项" not in summary:
            summary = f"{summary} check 前置审计存在提醒项。"

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
            "supported_providers": list(deps.supported_providers),
            "agent_runs": agent_runs,
            "stage_contracts": stage_contracts,
            "check_preflight": preflight_meta,
            "dry_run": dry_run,
        },
    )


def _build_requirements_stage_summary(parsed_spec: Any) -> str:
    goals = parsed_spec.sections.get("业务目标")
    rules = parsed_spec.sections.get("核心逻辑") or parsed_spec.sections.get("关键规则")
    acceptance = parsed_spec.sections.get("验收标准")
    goal_text = "；".join(goals.items[:3]) if goals else "未显式提取到业务目标"
    rule_text = "；".join(rules.items[:3]) if rules else "未显式提取到关键规则"
    acceptance_text = (
        "；".join(acceptance.items[:2])
        if acceptance and acceptance.items
        else "未显式提取到验收标准"
    )
    return f"需求提炼完成：目标={goal_text}；规则={rule_text}；验收={acceptance_text}。"


def _build_plan_stage_summary(parsed_plan: Any) -> str:
    scope = parsed_plan.sections.get("Scope")
    verification = parsed_plan.sections.get("Verification")
    ulw_count = len(parsed_plan.ulws)
    scope_text = (
        "；".join(scope.items[:3]) if scope and scope.items else "未显式提取到范围项"
    )
    verification_text = (
        "；".join(verification.items[:2])
        if verification and verification.items
        else "未显式提取到验证步骤"
    )
    return f"计划提炼完成：ULW={ulw_count} 个；范围={scope_text}；验证={verification_text}。"


def _build_implement_stage_summary(
    *, requirements_summary: str, plan_summary: str, provider: str | None
) -> str:
    return (
        f"实施阶段已按 {provider} 工作流生成执行摘要，先承接需求约束，再承接计划拆分。"
        f" requirements={requirements_summary} plan={plan_summary}"
    )


def _build_verify_stage(root: Path) -> dict[str, Any]:
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


def _build_pr_summary_path(
    *,
    root: Path,
    plan_title: str,
    next_available_path: Callable[[Path], Path],
    slugify: Callable[[str], str],
    utc_timestamp_precise: Callable[[], str],
) -> Path:
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
    provider: str | None,
    agent_runs: list[dict[str, Any]],
    verification_summary: str,
) -> str:
    run_lines = "\n".join(f"- {run['stage']}: {run['summary']}" for run in agent_runs)
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
