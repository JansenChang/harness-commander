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

    resolve_effective_provider: Callable[..., tuple[str | None, str, Any]]
    supported_providers: tuple[str, ...]
    run_check: Callable[..., CommandResult]
    validate_plan_document: Callable[..., Any]
    parse_product_spec: Callable[[Path], Any]
    parse_active_plan: Callable[[Path], Any]
    write_text: Callable[..., CommandArtifact]
    next_available_path: Callable[[Path], Path]
    slugify: Callable[[str], str]
    utc_timestamp_precise: Callable[[], str]


@dataclass(frozen=True, slots=True)
class ProviderContext:
    """描述当前 run-agents 的 provider 上下文。"""

    provider: str | None
    provider_source: str
    configured: bool
    resolution_reason: str | None = None


@dataclass(frozen=True, slots=True)
class StageFrame:
    """统一描述单个阶段的兼容摘要与结构化合同。"""

    stage: str
    provider: str | None
    status: str
    summary: str
    inputs: dict[str, Any]
    outputs: dict[str, Any]
    blocking_conditions: list[dict[str, Any]]
    fallback: dict[str, Any]
    artifacts: list[dict[str, Any]]
    host_model_allowed: bool
    artifact_path: str | None = None
    include_in_agent_runs: bool = True

    def to_agent_run(self) -> dict[str, Any]:
        payload = {
            "stage": self.stage,
            "provider": self.provider,
            "status": self.status,
            "summary": self.summary,
        }
        if self.artifact_path:
            payload["artifact_path"] = self.artifact_path
        return payload

    def to_stage_contract(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "status": self.status,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "blocking_conditions": self.blocking_conditions,
            "fallback": self.fallback,
            "artifacts": self.artifacts,
            "host_model_allowed": self.host_model_allowed,
        }


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

    provider_context = _resolve_provider_context(
        root=root,
        provider=provider,
        dry_run=dry_run,
        deps=deps,
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
    check_frame, preflight_meta, missing_check_fields = _build_check_stage(
        root=root,
        spec_file=spec_file,
        plan_file=plan_file,
        check_result=check_result,
    )

    base_meta = {
        "root": str(root),
        "spec_path": str(spec_file),
        "plan_path": str(plan_file),
        "provider": provider_context.provider,
        "provider_source": provider_context.provider_source,
        "supported_providers": list(deps.supported_providers),
        "check_preflight": preflight_meta,
        "dry_run": dry_run,
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
                **base_meta,
                "agent_runs": [check_frame.to_agent_run()],
                "stage_contracts": [check_frame.to_stage_contract()],
            },
        )

    if check_result.status == ResultStatus.FAILURE:
        return CommandResult(
            command="run-agents",
            status=ResultStatus.FAILURE,
            summary=f"check 前置门未通过，已停止多 agent 编排。{check_frame.summary}",
            warnings=list(check_result.warnings),
            errors=list(check_result.errors),
            meta={
                **base_meta,
                "agent_runs": [check_frame.to_agent_run()],
                "stage_contracts": [check_frame.to_stage_contract()],
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
                **base_meta,
                "agent_runs": [check_frame.to_agent_run()],
                "stage_contracts": [check_frame.to_stage_contract()],
                "issue_count": len(validation.issues),
            },
        )

    parsed_spec = deps.parse_product_spec(spec_file)
    parsed_plan = deps.parse_active_plan(plan_file)
    requirements_frame = _build_requirements_stage(
        spec_file=spec_file,
        parsed_spec=parsed_spec,
        provider_context=provider_context,
    )
    plan_frame = _build_plan_stage(
        plan_file=plan_file,
        parsed_plan=parsed_plan,
        requirements_frame=requirements_frame,
        provider_context=provider_context,
    )
    implement_frame = _build_implement_stage(
        requirements_frame=requirements_frame,
        plan_frame=plan_frame,
        provider_context=provider_context,
    )
    verify_frame = _build_verify_stage(root=root)

    stage_frames = [
        check_frame,
        requirements_frame,
        plan_frame,
        implement_frame,
        verify_frame,
    ]
    artifacts: list[CommandArtifact] = []
    warnings: list[CommandMessage] = list(check_result.warnings)
    errors: list[CommandMessage] = []

    if verify_frame.status != ResultStatus.SUCCESS.value:
        warnings.append(
            CommandMessage(
                code="verify_not_ready_for_pr",
                message="验证尚未通过，已阻断 PR 摘要整理阶段。",
                location=str(root / ".claude/tmp/last-verify.status"),
                detail={"verify_status": verify_frame.status},
            )
        )
        pr_summary_frame = _build_pr_summary_blocked_stage(
            spec_title=parsed_spec.title,
            plan_title=parsed_plan.title,
            verify_frame=verify_frame,
        )
        stage_frames.append(pr_summary_frame)
        status = ResultStatus.WARNING
        summary = "多 agent 阶段编排完成，但验证未通过，PR 摘要未生成。"
    else:
        pr_summary_frame, artifact = _build_pr_summary_stage(
            root=root,
            parsed_spec=parsed_spec,
            parsed_plan=parsed_plan,
            provider_context=provider_context,
            stage_frames=stage_frames,
            verify_frame=verify_frame,
            dry_run=dry_run,
            deps=deps,
        )
        stage_frames.append(pr_summary_frame)
        artifacts.append(artifact)
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
            **base_meta,
            "agent_runs": [
                frame.to_agent_run() for frame in stage_frames if frame.include_in_agent_runs
            ],
            "stage_contracts": [frame.to_stage_contract() for frame in stage_frames],
        },
    )


def _resolve_provider_context(
    *,
    root: Path,
    provider: str | None,
    dry_run: bool,
    deps: RunAgentsDependencies,
) -> ProviderContext:
    """把 provider 解析为可选上下文，避免 deterministic baseline 被硬阻断。"""

    try:
        normalized_provider, provider_source, _ = deps.resolve_effective_provider(
            root,
            override=provider,
            persist_last_resolved=False,
            dry_run=dry_run,
        )
    except HarnessCommanderError as error:
        if error.code != "provider_not_configured":
            raise
        return ProviderContext(
            provider=None,
            provider_source="deterministic_baseline",
            configured=False,
            resolution_reason=error.code,
        )

    return ProviderContext(
        provider=normalized_provider,
        provider_source=provider_source,
        configured=normalized_provider is not None,
        resolution_reason="resolved" if normalized_provider is not None else None,
    )


def _build_check_stage(
    *,
    root: Path,
    spec_file: Path,
    plan_file: Path,
    check_result: CommandResult,
) -> tuple[StageFrame, dict[str, Any], list[str]]:
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

    preflight_meta = {
        "status": check_result.status.value,
        "ready_for_run_agents": preflight_ready_for_run_agents,
        "explicit_plan_override_applied": explicit_plan_override_applied,
        "governance_entry": check_governance_entry,
    }
    blocking_conditions = (
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
    )
    check_frame = StageFrame(
        stage="check",
        provider="harness",
        status=(
            ResultStatus.FAILURE.value
            if missing_check_fields
            else check_result.status.value
        ),
        summary=check_stage_summary,
        inputs={
            "root": str(root),
            "spec_path": str(spec_file),
            "plan_path": str(plan_file),
            "dry_run": True,
        },
        outputs={
            "summary": check_stage_summary,
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
        blocking_conditions=blocking_conditions,
        fallback=_default_fallback(),
        artifacts=[],
        host_model_allowed=False,
    )
    return check_frame, preflight_meta, missing_check_fields


def _build_requirements_stage(
    *,
    spec_file: Path,
    parsed_spec: Any,
    provider_context: ProviderContext,
) -> StageFrame:
    goal_items = _items_from_sections(parsed_spec, "业务目标", "目标", "Goal")
    rule_items = _items_from_sections(parsed_spec, "核心逻辑", "关键规则", "Business Logic")
    acceptance_items = _items_from_sections(parsed_spec, "验收标准", "Acceptance Criteria")
    open_questions = _items_from_sections(parsed_spec, "当前开放问题", "Open Questions")
    summary = _build_requirements_stage_summary(parsed_spec)
    source_inputs = [
        _source_input("product_spec", str(spec_file), True),
    ]
    outputs = _build_slot_outputs(
        summary=summary,
        source_inputs=source_inputs,
        key_decisions=(goal_items + rule_items + acceptance_items)[:5],
        open_questions=open_questions[:3],
        handoff_notes=[
            "将需求摘要合同提供给 plan 槽位。",
            "将需求约束提供给 implement 槽位。",
        ],
        execution_path="deterministic",
        host_attempted=False,
        requirements_summary=summary,
        host_first=_build_host_first_facts(
            stage="requirements",
            provider_context=provider_context,
            execution_path="deterministic",
        ),
    )
    return StageFrame(
        stage="requirements",
        provider=provider_context.provider,
        status=ResultStatus.SUCCESS.value,
        summary=summary,
        inputs={
            "spec_path": str(spec_file),
            "spec_title": parsed_spec.title,
            "provider": provider_context.provider,
            "provider_source": provider_context.provider_source,
        },
        outputs=outputs,
        blocking_conditions=[],
        fallback=_default_fallback(),
        artifacts=[],
        host_model_allowed=True,
    )


def _build_plan_stage(
    *,
    plan_file: Path,
    parsed_plan: Any,
    requirements_frame: StageFrame,
    provider_context: ProviderContext,
) -> StageFrame:
    scope_items = _items_from_sections(parsed_plan, "Scope")
    acceptance_items = _items_from_sections(parsed_plan, "Acceptance Criteria")
    verification_items = _items_from_sections(parsed_plan, "Verification")
    open_questions = _items_from_sections(parsed_plan, "当前开放问题", "Open Questions")
    summary = _build_plan_stage_summary(parsed_plan)
    outputs = _build_slot_outputs(
        summary=summary,
        source_inputs=[
            _source_input("active_plan", str(plan_file), True),
            _source_input("stage_output", "requirements", True),
        ],
        key_decisions=(scope_items + acceptance_items + verification_items)[:5],
        open_questions=open_questions[:3],
        handoff_notes=[
            "将计划摘要合同提供给 implement 槽位。",
            "保留 ULW 数量，便于后续执行对齐。",
        ],
        execution_path="deterministic",
        host_attempted=False,
        plan_summary=summary,
        ulw_count=len(parsed_plan.ulws),
        requirements_summary=requirements_frame.outputs.get("summary"),
        host_first=_build_host_first_facts(
            stage="plan",
            provider_context=provider_context,
            execution_path="deterministic",
        ),
    )
    return StageFrame(
        stage="plan",
        provider=provider_context.provider,
        status=ResultStatus.SUCCESS.value,
        summary=summary,
        inputs={
            "plan_path": str(plan_file),
            "plan_title": parsed_plan.title,
            "requirements_stage": requirements_frame.stage,
            "provider": provider_context.provider,
            "provider_source": provider_context.provider_source,
        },
        outputs=outputs,
        blocking_conditions=[],
        fallback=_default_fallback(),
        artifacts=[],
        host_model_allowed=True,
    )


def _build_implement_stage(
    *,
    requirements_frame: StageFrame,
    plan_frame: StageFrame,
    provider_context: ProviderContext,
) -> StageFrame:
    summary = _build_implement_stage_summary(
        requirements_summary=str(requirements_frame.outputs.get("summary", "")),
        plan_summary=str(plan_frame.outputs.get("summary", "")),
        provider=provider_context.provider,
    )
    outputs = _build_slot_outputs(
        summary=summary,
        source_inputs=[
            _source_input("stage_output", requirements_frame.stage, True),
            _source_input("stage_output", plan_frame.stage, True),
        ],
        key_decisions=[
            "先承接 requirements 的业务约束。",
            "再承接 plan 的执行拆分与验证约束。",
        ],
        open_questions=[],
        handoff_notes=[
            "当前 implement 仍是 Harness 控制的交接槽位，不宣称真实代码子 agent runtime。",
            "verify 继续以本地产物作为唯一裁决输入。",
        ],
        execution_path="deterministic",
        host_attempted=False,
        implement_summary=summary,
        requirements_summary=requirements_frame.outputs.get("summary"),
        plan_summary=plan_frame.outputs.get("summary"),
    )
    return StageFrame(
        stage="implement",
        provider=provider_context.provider,
        status=ResultStatus.SUCCESS.value,
        summary=summary,
        inputs={
            "requirements_stage": requirements_frame.stage,
            "plan_stage": plan_frame.stage,
            "requirements_summary": requirements_frame.outputs.get("requirements_summary"),
            "plan_summary": plan_frame.outputs.get("plan_summary"),
            "provider": provider_context.provider,
            "provider_source": provider_context.provider_source,
        },
        outputs=outputs,
        blocking_conditions=[],
        fallback=_default_fallback(),
        artifacts=[],
        host_model_allowed=False,
    )


def _build_verify_stage(*, root: Path) -> StageFrame:
    status_path = root / ".claude/tmp/last-verify.status"
    summary_path = root / ".claude/tmp/verification-summary.md"
    verify_status = "missing"
    verification_summary = ""
    stage_status = ResultStatus.WARNING.value
    summary = "未找到验证状态文件。"
    if status_path.exists():
        verify_status = status_path.read_text(encoding="utf-8").strip().lower() or "unknown"
        verification_summary = (
            summary_path.read_text(encoding="utf-8").strip()
            if summary_path.exists()
            else ""
        )
        summary = f"验证状态：{verify_status}"
        stage_status = (
            ResultStatus.SUCCESS.value
            if verify_status == "pass"
            else ResultStatus.WARNING.value
        )

    verification_summary_missing = (
        stage_status == ResultStatus.SUCCESS.value and not verification_summary
    )
    outputs = _build_slot_outputs(
        summary=summary,
        source_inputs=[
            _source_input("verify_status_file", str(status_path), True),
            _source_input("verification_summary_file", str(summary_path), False),
        ],
        key_decisions=[f"verify_status={verify_status}"],
        open_questions=(
            ["verification summary 缺失，需要人工补充。"]
            if verification_summary_missing
            else []
        ),
        handoff_notes=(
            ["只有 verify 成功时才允许进入 pr-summary。"]
            if stage_status == ResultStatus.SUCCESS.value
            else ["verify 未通过或未就绪，必须阻断 pr-summary。"]
        ),
        execution_path="deterministic",
        host_attempted=False,
        verify_status=verify_status,
        verification_summary=verification_summary,
        verify_stage_summary=summary,
        status_path=str(status_path),
        summary_path=str(summary_path),
        host_first=_build_host_first_facts(
            stage="verify",
            provider_context=ProviderContext(
                provider=None,
                provider_source="harness",
                configured=False,
                resolution_reason="host_model_not_allowed",
            ),
            execution_path="deterministic",
        ),
    )
    return StageFrame(
        stage="verify",
        provider="harness",
        status=stage_status,
        summary=summary,
        inputs={
            "status_path": str(status_path),
            "summary_path": str(summary_path),
        },
        outputs=outputs,
        blocking_conditions=(
            [
                {
                    "code": "verify_not_ready_for_pr",
                    "message": "验证尚未通过，PR 摘要阶段被阻断。",
                    "blocked": True,
                }
            ]
            if stage_status != ResultStatus.SUCCESS.value
            else []
        ),
        fallback={
            "applied": verification_summary_missing,
            "reason": (
                "verification_summary_missing"
                if verification_summary_missing
                else None
            ),
            "from": "verification-summary-file",
            "to": (
                "inline_placeholder_text"
                if verification_summary_missing
                else "verification-summary-file"
            ),
        },
        artifacts=[],
        host_model_allowed=False,
    )


def _build_pr_summary_blocked_stage(
    *,
    spec_title: str,
    plan_title: str,
    verify_frame: StageFrame,
) -> StageFrame:
    return StageFrame(
        stage="pr-summary",
        provider="harness",
        status=ResultStatus.WARNING.value,
        summary="验证尚未通过，PR 摘要阶段被阻断。",
        inputs={
            "spec_title": spec_title,
            "plan_title": plan_title,
            "verify_stage": verify_frame.stage,
            "verify_status": verify_frame.status,
        },
        outputs={
            "summary": "验证尚未通过，PR 摘要未生成。",
            "generated": False,
            "artifact_path": None,
        },
        blocking_conditions=[
            {
                "code": "verify_not_ready_for_pr",
                "message": "验证尚未通过，已阻断 PR 摘要整理阶段。",
                "blocked": True,
            }
        ],
        fallback=_default_fallback(),
        artifacts=[],
        host_model_allowed=False,
        include_in_agent_runs=False,
    )


def _build_pr_summary_stage(
    *,
    root: Path,
    parsed_spec: Any,
    parsed_plan: Any,
    provider_context: ProviderContext,
    stage_frames: list[StageFrame],
    verify_frame: StageFrame,
    dry_run: bool,
    deps: RunAgentsDependencies,
) -> tuple[StageFrame, CommandArtifact]:
    verification_summary = str(verify_frame.outputs.get("verification_summary", "")).strip()
    verification_summary_missing = not verification_summary
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
        provider=provider_context.provider,
        agent_runs=[frame.to_agent_run() for frame in stage_frames],
        verification_summary=verification_summary,
    )
    artifact = deps.write_text(
        pr_summary_path,
        pr_summary_content,
        dry_run=dry_run,
        overwrite=False,
    )
    frame = StageFrame(
        stage="pr-summary",
        provider="harness",
        status=ResultStatus.SUCCESS.value,
        summary=f"已整理 PR 摘要：{pr_summary_path}",
        inputs={
            "spec_title": parsed_spec.title,
            "plan_title": parsed_plan.title,
            "verify_stage": verify_frame.stage,
            "verify_status": verify_frame.status,
            "provider": provider_context.provider,
        },
        outputs={
            "summary": f"已整理 PR 摘要：{pr_summary_path}",
            "generated": True,
            "artifact_path": str(pr_summary_path),
            "verification_summary_used": bool(verification_summary),
        },
        blocking_conditions=[],
        fallback={
            "applied": verification_summary_missing,
            "reason": (
                "verification_summary_missing"
                if verification_summary_missing
                else None
            ),
            "from": "verification-summary-file",
            "to": (
                "inline_placeholder_text"
                if verification_summary_missing
                else "verification-summary-file"
            ),
        },
        artifacts=[
            {
                "path": str(pr_summary_path),
                "kind": "file",
                "action": "would_create" if dry_run else "created",
            }
        ],
        host_model_allowed=False,
        artifact_path=str(pr_summary_path),
    )
    return frame, artifact


def _build_slot_outputs(
    *,
    summary: str,
    source_inputs: list[dict[str, Any]],
    key_decisions: list[str],
    open_questions: list[str],
    handoff_notes: list[str],
    execution_path: str,
    host_attempted: bool,
    **extra: Any,
) -> dict[str, Any]:
    outputs = {
        "summary": summary,
        "source_inputs": source_inputs,
        "key_decisions": key_decisions,
        "open_questions": open_questions,
        "handoff_notes": handoff_notes,
        "execution_path": execution_path,
        "host_attempted": host_attempted,
    }
    outputs.update(extra)
    return outputs


def _source_input(input_type: str, ref: str, required: bool) -> dict[str, Any]:
    return {
        "type": input_type,
        "ref": ref,
        "required": required,
    }


def _default_fallback() -> dict[str, Any]:
    return {
        "applied": False,
        "reason": None,
        "from": None,
        "to": None,
    }


def _build_host_first_facts(
    *,
    stage: str,
    provider_context: ProviderContext,
    execution_path: str,
) -> dict[str, Any]:
    host_first_candidate = stage in {"requirements", "plan"}
    return {
        "future_host_first_candidate": host_first_candidate,
        "preferred_path": "host-first" if host_first_candidate else "harness",
        "selected_path": execution_path,
        "selection_reason": (
            "deterministic_baseline"
            if host_first_candidate
            else "host_model_not_allowed"
        ),
        "provider": provider_context.provider,
        "provider_source": provider_context.provider_source,
        "provider_configured": provider_context.configured,
        "provider_resolution_reason": provider_context.resolution_reason,
        "host_attempted": False,
    }


def _items_from_sections(parsed: Any, *titles: str) -> list[str]:
    items: list[str] = []
    for title in titles:
        section = parsed.sections.get(title)
        if not section:
            continue
        for item in section.items:
            if item and item not in items:
                items.append(item)
    return items


def _build_requirements_stage_summary(parsed_spec: Any) -> str:
    goals = parsed_spec.sections.get("业务目标") or parsed_spec.sections.get("目标")
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
    workflow_provider = provider or "deterministic"
    return (
        f"实施交接阶段已按 {workflow_provider} 工作流生成执行摘要，先承接需求约束，再承接计划拆分。"
        f" requirements={requirements_summary} plan={plan_summary}"
    )


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
