"""CLI 骨架测试。

该测试文件覆盖第一轮骨架的关键行为：
目录初始化、计划生成、计划校验、证据留存以及 JSON 输出协议。
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

import json  # noqa: E402

from harness_commander.application.host_providers import (  # noqa: E402
    INSTALL_TARGETS,
    SUPPORTED_PROVIDERS,
    get_provider_spec,
)
from harness_commander.application.model_tasks import HostModelError  # noqa: E402
from harness_commander.cli import main  # noqa: E402
from harness_commander.domain.models import (  # noqa: E402
    CommandMessage,
    CommandResult,
    ResultStatus,
)
from harness_commander.infrastructure import docs as docs_infra  # noqa: E402


def create_minimal_repo(root: Path) -> None:
    """构造满足命令执行前提的最小仓库结构。"""

    required_files = {
        "ARCHITECTURE.md": "# architecture\n",
        "docs/PLANS.md": "# plans\n",
        "docs/PRODUCT_SENSE.md": "# product sense\n",
        "docs/QUALITY_SCORE.md": "# quality\n",
        "docs/RELIABILITY.md": "# reliability\n",
        "docs/SECURITY.md": "# security\n",
        "docs/design-docs/core-beliefs.md": "# beliefs\n",
        "docs/product-specs/index.md": "# specs index\n",
        "docs/product-specs/v1/index.md": "# spec v1 index\n",
    }
    for relative_path, content in required_files.items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def write_provider_config(root: Path, *, default_provider: str, installed: list[str] | None = None) -> None:
    """写入最小 provider 配置。"""

    config_path = root / ".harness/provider-config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(
            {
                "version": 1,
                "default_provider": default_provider,
                "installed_providers": installed or [default_provider],
                "installation_results": {
                    default_provider: {
                        "status": "config_only",
                        "support_level": "config_only",
                        "detected": True,
                        "cli_command": default_provider,
                        "configured_at": "2026-04-07T00:00:00Z",
                        "message": "configured in test",
                    }
                },
                "last_resolved_provider": default_provider,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def create_run_agents_inputs(
    root: Path,
    *,
    spec_content: str | None = None,
    plan_content: str | None = None,
) -> tuple[Path, Path]:
    """构造 run-agents 测试使用的最小 spec/plan 文档。"""

    spec_file = root / "docs/product-specs/sample.md"
    spec_file.parent.mkdir(parents=True, exist_ok=True)
    spec_file.write_text(
        spec_content
        or (
            "# 样例规格\n\n"
            "## 业务目标\n- 支持多 agent 编排\n\n"
            "## 核心逻辑\n- 验证通过后整理 PR\n\n"
            "## 验收标准\n- 产出 PR summary\n"
        ),
        encoding="utf-8",
    )
    plan_file = root / "docs/exec-plans/active/sample.md"
    plan_file.parent.mkdir(parents=True, exist_ok=True)
    plan_file.write_text(
        plan_content
        or (
            "# 样例计划\n\n"
            "## Goal\n- 完成编排\n\n"
            "## Context\n- 样例上下文\n\n"
            "## Business Logic\n- 按阶段执行\n\n"
            "## Scope\n- requirements\n- verify\n\n"
            "## Acceptance Criteria\n- 生成 PR 摘要\n\n"
            "## Exception Handling\n- 失败要保留状态\n\n"
            "## Verification\n- 检查验证状态\n\n"
            "## References\n- `ARCHITECTURE.md`\n- `docs/PLANS.md`\n- `docs/product-specs/v1/index.md`\n\n"
            "## ULW 1: 编排\n\n"
            "### 目标\n- 完成执行\n\n"
            "### 涉及范围\n- 读取文档\n\n"
            "### 验收标准\n- 输出阶段摘要\n"
        ),
        encoding="utf-8",
    )
    return spec_file, plan_file


def assert_stage_contracts_shape(
    payload: dict[str, object], *, expected_stages: list[str]
) -> list[dict[str, object]]:
    """断言 run-agents 阶段合同结构稳定。"""

    meta = payload.get("meta")
    assert isinstance(meta, dict)
    stage_contracts = meta.get("stage_contracts")
    assert isinstance(stage_contracts, list)
    assert [contract.get("stage") for contract in stage_contracts] == expected_stages

    required_keys = {
        "stage",
        "status",
        "inputs",
        "outputs",
        "blocking_conditions",
        "fallback",
        "artifacts",
        "host_model_allowed",
    }
    for contract in stage_contracts:
        assert isinstance(contract, dict)
        assert required_keys.issubset(set(contract.keys()))
        assert isinstance(contract["inputs"], dict)
        assert isinstance(contract["outputs"], dict)
        assert isinstance(contract["blocking_conditions"], list)
        assert isinstance(contract["fallback"], dict)
        assert isinstance(contract["artifacts"], list)
        assert isinstance(contract["host_model_allowed"], bool)
    return stage_contracts


def find_stage_contract(
    stage_contracts: list[dict[str, object]], stage: str
) -> dict[str, object]:
    """从阶段合同中定位指定阶段。"""

    for contract in stage_contracts:
        if contract.get("stage") == stage:
            return contract
    raise AssertionError(f"missing stage contract: {stage}")


def stage_has_blocking(stage_contract: dict[str, object]) -> bool:
    """判断阶段合同是否存在阻断条件命中。"""

    conditions = stage_contract.get("blocking_conditions")
    assert isinstance(conditions, list)
    return any(
        isinstance(condition, dict)
        and isinstance(condition.get("code"), str)
        and bool(condition["code"])
        for condition in conditions
    )


def stage_uses_fallback(stage_contract: dict[str, object]) -> bool:
    """判断阶段合同是否发生 fallback。"""

    fallback = stage_contract.get("fallback")
    assert isinstance(fallback, dict)
    return fallback.get("applied") is True


def build_check_preflight_result(
    *,
    status: ResultStatus,
    blocking_count: int = 0,
    warning_count: int = 0,
    health_score: int = 100,
    ready_for_run_agents: bool = True,
) -> CommandResult:
    """构造 run-agents preflight 使用的 check 结果。"""

    warnings: list[CommandMessage] = []
    errors: list[CommandMessage] = []
    if status == ResultStatus.WARNING:
        warnings.append(
            CommandMessage(
                code="check_preflight_warning",
                message="治理预检存在提醒项，允许继续执行。",
                location="check",
            )
        )
    elif status == ResultStatus.FAILURE:
        errors.append(
            CommandMessage(
                code="check_preflight_blocked",
                message="治理预检失败，阻断后续阶段。",
                location="check",
            )
        )

    checks_blocking = [item.to_dict() for item in errors]
    checks_warnings = [item.to_dict() for item in warnings]
    return CommandResult(
        command="check",
        status=status,
        summary="mock check preflight result",
        warnings=warnings,
        errors=errors,
        meta={
            "health_score": health_score,
            "blocking_count": blocking_count,
            "warning_count": warning_count,
            "governance_entry": {
                "status": (
                    "blocked"
                    if status == ResultStatus.FAILURE
                    else "needs_attention"
                    if status == ResultStatus.WARNING
                    else "ready"
                ),
                "ready_for_run_agents": ready_for_run_agents,
                "no_warning": status == ResultStatus.SUCCESS and warning_count == 0,
                "recommended_entrypoint": (
                    "harness run-agents"
                    if ready_for_run_agents
                    else "harness check"
                ),
            },
            "next_actions": [
                {
                    "code": "mock_action",
                    "title": "mock action",
                    "summary": "mock summary",
                    "recommended_command": "harness check",
                }
            ],
            "checks": {
                "blocking": checks_blocking,
                "warnings": checks_warnings,
                "all": [*checks_blocking, *checks_warnings],
            },
            "checked_targets": {
                "plan_files": ["docs/exec-plans/active/sample.md"],
                "generated_files": [],
            },
        },
    )



def test_init_command_creates_missing_directories(tmp_path: Path, capsys) -> None:
    """init 命令应补齐目录结构与模板文件并返回成功退出码。"""

    exit_code = main(["-p", str(tmp_path), "init"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "[success] init" in captured.out
    assert (tmp_path / "AGENTS.md").exists()
    assert (tmp_path / "docs/product-specs/index.md").exists()
    assert (tmp_path / "docs/references/uv-llms.txt").exists()
    assert (tmp_path / "docs/design-docs").exists()
    assert (tmp_path / "docs/exec-plans/active").exists()
    assert (tmp_path / "docs/exec-plans/completed").exists()
    assert (tmp_path / "docs/product-specs").exists()
    assert (tmp_path / "docs/references").exists()
    assert not (tmp_path / "src").exists(), "init不应创建src目录"
    assert not (tmp_path / "tests").exists(), "init不应创建tests目录"


def test_propose_plan_supports_json_dry_run(tmp_path: Path, capsys) -> None:
    """propose-plan 在 dry-run 模式下也应输出稳定 JSON 结构。"""

    create_minimal_repo(tmp_path)
    exit_code = main(
        [
            "-p",
            str(tmp_path),
            "--json",
            "propose-plan",
            "--input",
            "实现 sync 命令",
            "--dry-run",
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["command"] == "propose-plan"
    assert payload["status"] == "success"
    assert payload["artifacts"][0]["action"] == "would_create"


def test_propose_plan_generates_v1_sections_and_ulw_metadata(tmp_path: Path, capsys) -> None:
    """propose-plan 应生成符合 V1 结构的计划文件。"""

    create_minimal_repo(tmp_path)
    exit_code = main(
        [
            "-p",
            str(tmp_path),
            "--json",
            "propose-plan",
            "--input",
            "实现 sync 命令",
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["meta"]["ulw_count"] == 2
    plan_path = Path(payload["meta"]["plan_path"])
    content = plan_path.read_text(encoding="utf-8")
    assert "## Context" in content
    assert "## Scope" in content
    assert "## ULW 1: 澄清需求并锁定边界" in content
    assert "### 验收标准" in content
    assert "docs/product-specs/v1/index.md" in content


def test_plan_check_detects_invalid_plan(tmp_path: Path, capsys) -> None:
    """plan-check 应识别缺少关键段落和引用的计划。"""

    create_minimal_repo(tmp_path)
    invalid_plan = tmp_path / "docs/exec-plans/active/invalid.md"
    invalid_plan.parent.mkdir(parents=True, exist_ok=True)
    invalid_plan.write_text("# bad plan\n\n## Goal\n\n- only goal\n", encoding="utf-8")
    exit_code = main(["-p", str(tmp_path), "plan-check", str(invalid_plan)])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "[failure] plan-check" in captured.out
    assert "missing_section" in captured.out
    assert "missing_reference" in captured.out


def test_init_command_supports_explicit_target_project_path(
    tmp_path: Path, capsys
) -> None:
    """init 命令应支持通过 -p 在目标项目目录完成初始化。"""

    target_project = tmp_path / "test-project"
    exit_code = main(["init", "-p", str(target_project)])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "[success] init" in captured.out
    assert (target_project / "docs/exec-plans/active").exists()
    assert (target_project / "ARCHITECTURE.md").exists()
    assert (target_project / "docs/design-docs/core-beliefs.md").exists()


def test_init_command_reports_package_template_source_in_json(
    tmp_path: Path, capsys
) -> None:
    """init 命令默认应从包内模板资源加载内容。"""

    exit_code = main(["-p", str(tmp_path), "--json", "init"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["command"] == "init"
    assert payload["status"] == "success"
    assert payload["meta"]["template_source"] == "package_resources"
    assert payload["warnings"] == []


def test_init_command_ignores_docs_template_spec_file(tmp_path: Path, capsys) -> None:
    """init 命令不应把 docs 里的模板规范文档当作运行时模板源。"""

    spec_file = tmp_path / "docs/design-docs/init-templates.md"
    spec_file.parent.mkdir(parents=True, exist_ok=True)
    spec_file.write_text(
        "# fake spec\n\n## AGENTS.md 模板\n```markdown\n# broken\n```\n",
        encoding="utf-8",
    )

    exit_code = main(["-p", str(tmp_path), "init"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "[success] init" in captured.out
    agents_content = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "# broken" not in agents_content
    assert "用于定义 AI 在本项目中的身份、语气、决策边界和默认工作方式。" in agents_content


def test_init_command_skips_existing_files_without_overwriting(
    tmp_path: Path, capsys
) -> None:
    """init 命令发现已有文件时应跳过并保留原内容。"""

    target_project = tmp_path / "existing-project"
    target_project.mkdir(parents=True, exist_ok=True)
    architecture_file = target_project / "ARCHITECTURE.md"
    architecture_file.write_text("# custom architecture\n", encoding="utf-8")
    exit_code = main(["init", "-p", str(target_project)])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "skipped file" in captured.out
    assert architecture_file.read_text(encoding="utf-8") == "# custom architecture\n"
    assert (target_project / "docs/PLANS.md").exists()


def test_collect_evidence_persists_failed_command_context(
    tmp_path: Path, capsys
) -> None:
    """collect-evidence 即使记录失败命令，也应保留证据文件。"""

    create_minimal_repo(tmp_path)
    exit_code = main(
        [
            "-p",
            str(tmp_path),
            "--json",
            "collect-evidence",
            "--command",
            "pytest",
            "--exit-code",
            "1",
            "--status",
            "failure",
            "--summary",
            "测试失败",
            "--started-at",
            "2026-04-06T10:00:00Z",
            "--finished-at",
            "2026-04-06T10:00:02Z",
            "--artifact",
            "docs/generated/db-schema.md",
            "--log",
            "line1",
            "--log",
            "line2",
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["command"] == "collect-evidence"
    assert payload["status"] == "warning"
    assert payload["warnings"][0]["code"] == "captured_failed_execution"
    record = payload["meta"]["record"]
    assert record["started_at"] == "2026-04-06T10:00:00Z"
    assert record["finished_at"] == "2026-04-06T10:00:02Z"
    assert record["artifacts"] == ["docs/generated/db-schema.md"]
    assert record["logs"] == ["line1", "line2"]


def test_init_command_falls_back_to_builtin_templates_when_package_resource_missing(
    tmp_path: Path,
) -> None:
    """包内模板资源缺失时，init 应退回内置模板并发出 warning。"""

    missing_template = "missing from package"

    with patch.object(
        docs_infra,
        "_load_templates_from_package_resources",
        side_effect=FileNotFoundError(missing_template),
    ):
        result = docs_infra.load_init_templates(tmp_path)

    assert result.source == "builtin_fallback"
    assert len(result.warnings) == 1
    warning = result.warnings[0]
    assert warning.code == "init_template_fallback"
    assert warning.location.endswith("init_templates/AGENTS.md")
    assert missing_template in warning.detail["reason"]


def assert_distill_mapping_meta(
    payload: dict[str, object],
) -> tuple[dict[str, object], dict[str, list[dict[str, object]]], dict[str, object]]:
    """断言 distill 来源映射元数据结构稳定。"""

    meta = payload.get("meta")
    assert isinstance(meta, dict)
    extraction_report = meta.get("extraction_report")
    section_sources = meta.get("section_sources")
    source_mapping_coverage = meta.get("source_mapping_coverage")
    assert isinstance(extraction_report, dict)
    assert isinstance(section_sources, dict)
    assert isinstance(source_mapping_coverage, dict)
    assert set(section_sources.keys()) == {"goals", "rules", "limits", "prohibitions"}
    assert "unresolved_sections" in extraction_report
    assert "extracted_section_count" in extraction_report
    assert "extraction_source" in extraction_report
    assert "mapped_items" in source_mapping_coverage
    assert "unmatched_items" in source_mapping_coverage
    assert "total_items" in source_mapping_coverage
    assert (
        "mapped_ratio" in source_mapping_coverage
        or "coverage_ratio" in source_mapping_coverage
    )
    for value in section_sources.values():
        assert isinstance(value, list)
        for item in value:
            assert isinstance(item, dict)
            assert isinstance(item.get("text"), str)
            assert item.get("mapping_status") in {"mapped", "unmatched"}
    return extraction_report, section_sources, source_mapping_coverage


def flatten_section_sources(
    section_sources: dict[str, list[dict[str, object]]],
) -> list[dict[str, object]]:
    """拍平 section_sources，便于统一断言。"""

    flattened: list[dict[str, object]] = []
    for items in section_sources.values():
        flattened.extend(items)
    return flattened


def test_distill_marks_partial_extraction_as_warning(tmp_path: Path, capsys) -> None:
    """distill 缺少部分章节但仍可提炼时应返回 warning。"""

    create_minimal_repo(tmp_path)
    source_file = tmp_path / "brief.md"
    source_file.write_text(
        "# 简短文档\n\n## 业务目标\n保留一个最小目标。\n",
        encoding="utf-8",
    )

    exit_code = main(["-p", str(tmp_path), "--json", "distill", str(source_file)])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["status"] == "warning"
    assert payload["warnings"][0]["code"] == "partial_distillation"
    assert payload["warnings"][0]["detail"]["unresolved_sections"] == [
        "关键规则",
        "边界限制",
        "禁止项",
    ]
    assert payload["meta"]["source_type"] == "document"
    assert payload["meta"]["extracted_section_count"] == 1
    assert payload["meta"]["distill_mode"] == "heuristic"
    assert payload["meta"]["extraction_source"] == "heuristic"
    extraction_report, section_sources, source_mapping_coverage = assert_distill_mapping_meta(
        payload
    )
    assert extraction_report["extracted_section_count"] == 1
    assert source_mapping_coverage["total_items"] >= 1
    assert source_mapping_coverage["mapped_items"] >= 1
    assert any(
        item.get("mapping_status") == "mapped"
        for item in flatten_section_sources(section_sources)
    )


def test_distill_fails_when_extraction_is_insufficient(tmp_path: Path, capsys) -> None:
    """distill 几乎提炼不到结构化信息时应返回 failure。"""

    create_minimal_repo(tmp_path)
    source_file = tmp_path / "brief.md"
    source_file.write_text("# 简短文档\n\n只有一句描述。\n", encoding="utf-8")

    exit_code = main(["-p", str(tmp_path), "--json", "distill", str(source_file)])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 1
    assert payload["status"] == "failure"
    assert payload["warnings"][0]["code"] == "partial_distillation"
    assert payload["errors"][0]["code"] == "distillation_insufficient"
    assert payload["meta"]["extracted_section_count"] == 0
    assert payload["artifacts"] == []
    assert not Path(payload["meta"]["target_path"]).exists()
    assert "未生成参考材料" in payload["summary"]
    extraction_report, _, source_mapping_coverage = assert_distill_mapping_meta(payload)
    assert extraction_report["extracted_section_count"] == 0
    assert source_mapping_coverage["total_items"] == 0


def test_distill_extracts_requirements_and_constraints(tmp_path: Path, capsys) -> None:
    """distill 应从核心需求和技术约束中提炼规则与限制。"""

    create_minimal_repo(tmp_path)
    source_file = tmp_path / "requirements.md"
    source_file.write_text(
        "# 需求\n\n## 业务目标\n构建测试系统\n\n## 核心需求\n1. 用户管理\n2. 权限控制\n\n## 技术约束\n- 使用 Python 3.10+\n- 不得写入明文密钥\n",
        encoding="utf-8",
    )

    exit_code = main(["-p", str(tmp_path), "--json", "distill", str(source_file)])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    target_path = Path(payload["meta"]["target_path"])
    content = target_path.read_text(encoding="utf-8")
    assert "- 用户管理" in content
    assert "- 使用 Python 3.10+" in content
    assert "- 不得写入明文密钥" in content
    assert "来源映射" in content
    extraction_report, section_sources, source_mapping_coverage = assert_distill_mapping_meta(
        payload
    )
    assert extraction_report["extracted_section_count"] >= 3
    assert source_mapping_coverage["mapped_items"] >= 3
    assert source_mapping_coverage["mapped_items"] <= source_mapping_coverage["total_items"]
    assert flatten_section_sources(section_sources)


def test_distill_host_model_mode_uses_configured_provider_by_default(
    tmp_path: Path, capsys
) -> None:
    """distill 在 host-model 模式下默认应读取已配置 provider。"""

    create_minimal_repo(tmp_path)
    write_provider_config(tmp_path, default_provider="codex")
    source_file = tmp_path / "requirements.md"
    source_file.write_text("# 任意文档\n\n原始内容。\n", encoding="utf-8")

    with patch(
        "harness_commander.application.commands.distill_with_host_model",
        return_value={
            "goals": ["提升新用户完成率"],
            "rules": ["必须引导用户完成邮箱验证"],
            "limits": ["仅支持邮箱注册"],
            "prohibitions": ["不得跳过风控校验"],
        },
    ) as mocked_distill:
        exit_code = main(
            [
                "-p",
                str(tmp_path),
                "--json",
                "distill",
                str(source_file),
                "--mode",
                "host-model",
            ]
        )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["status"] == "success"
    assert payload["meta"]["distill_mode"] == "host-model"
    assert payload["meta"]["extraction_source"] == "host-model"
    assert payload["meta"]["model_provider"] == "codex-cli"
    assert payload["meta"]["provider"] == "codex"
    assert payload["meta"]["provider_source"] == "default_provider"
    assert payload["meta"]["supported_providers"] == list(SUPPORTED_PROVIDERS)
    assert mocked_distill.call_args.kwargs["provider"] == "codex"
    extraction_report, section_sources, source_mapping_coverage = assert_distill_mapping_meta(
        payload
    )
    assert extraction_report["extraction_source"] == "host-model"
    assert source_mapping_coverage["total_items"] >= 1
    assert any(
        item.get("mapping_status") == "unmatched"
        for item in flatten_section_sources(section_sources)
    )
    target_path = Path(payload["meta"]["target_path"])
    content = target_path.read_text(encoding="utf-8")
    assert "- 提升新用户完成率" in content
    assert "- 必须引导用户完成邮箱验证" in content
    assert "- 不得跳过风控校验" in content
    assert "来源映射" in content


def test_distill_auto_mode_falls_back_to_heuristic_when_host_model_fails(
    tmp_path: Path, capsys
) -> None:
    """auto 模式在宿主模型失败时应回退到 heuristic。"""

    create_minimal_repo(tmp_path)
    write_provider_config(tmp_path, default_provider="claude")
    source_file = tmp_path / "requirements.md"
    source_file.write_text(
        "# 需求\n\n## 业务目标\n构建测试系统\n\n## 核心需求\n1. 用户管理\n",
        encoding="utf-8",
    )

    with patch(
        "harness_commander.application.commands.distill_with_host_model",
        side_effect=HostModelError("boom"),
    ):
        exit_code = main(
            [
                "-p",
                str(tmp_path),
                "--json",
                "distill",
                str(source_file),
                "--mode",
                "auto",
            ]
        )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["meta"]["distill_mode"] == "auto"
    assert payload["meta"]["extraction_source"] == "heuristic"
    assert payload["meta"]["fallback_from"] == "host-model"
    warning_codes = [warning["code"] for warning in payload["warnings"]]
    assert "distill_fallback_to_heuristic" in warning_codes
    extraction_report, section_sources, source_mapping_coverage = assert_distill_mapping_meta(
        payload
    )
    assert extraction_report["extraction_source"] == "heuristic"
    assert source_mapping_coverage["total_items"] >= 1
    flattened = flatten_section_sources(section_sources)
    assert flattened
    assert all(
        item.get("mapping_status") in {"mapped", "unmatched"} for item in flattened
    )
    assert (
        any(item.get("mapping_status") == "unmatched" for item in flattened)
        or extraction_report["unresolved_sections"]
    )


def test_distill_provider_override_takes_precedence_over_config(
    tmp_path: Path, capsys
) -> None:
    """distill 显式 --provider 应覆盖默认配置。"""

    create_minimal_repo(tmp_path)
    write_provider_config(tmp_path, default_provider="claude")
    source_file = tmp_path / "requirements.md"
    source_file.write_text("# 任意文档\n\n原始内容。\n", encoding="utf-8")

    with patch(
        "harness_commander.application.commands.distill_with_host_model",
        return_value={
            "goals": ["支持更多宿主工具"],
            "rules": ["必须保持统一结果协议"],
            "limits": ["首版采用顺序阶段编排"],
            "prohibitions": ["不得伪造验证通过"],
        },
    ) as mocked_distill:
        exit_code = main(
            [
                "-p",
                str(tmp_path),
                "--json",
                "distill",
                str(source_file),
                "--mode",
                "host-model",
                "--provider",
                "codex",
            ]
        )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["meta"]["provider"] == "codex"
    assert payload["meta"]["provider_source"] == "override"
    assert payload["meta"]["model_provider"] == "codex-cli"
    assert mocked_distill.call_args.kwargs["provider"] == "codex"


def test_distill_host_model_requires_configured_provider_when_not_overridden(
    tmp_path: Path, capsys
) -> None:
    """distill host-model 在无配置且无 override 时应失败。"""

    create_minimal_repo(tmp_path)
    source_file = tmp_path / "requirements.md"
    source_file.write_text("# 任意文档\n\n原始内容。\n", encoding="utf-8")

    exit_code = main(
        [
            "-p",
            str(tmp_path),
            "--json",
            "distill",
            str(source_file),
            "--mode",
            "host-model",
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 1
    assert payload["status"] == "failure"
    assert payload["errors"][0]["code"] == "provider_not_configured"


def test_run_agents_fails_and_stops_before_requirements_when_check_preflight_fails(
    tmp_path: Path, capsys
) -> None:
    """check preflight failure 时，run-agents 应阻断且不进入 requirements。"""

    create_minimal_repo(tmp_path)
    write_provider_config(tmp_path, default_provider="claude")
    spec_file, plan_file = create_run_agents_inputs(tmp_path)

    with patch(
        "harness_commander.application.commands.run_check",
        return_value=build_check_preflight_result(
            status=ResultStatus.FAILURE,
            blocking_count=1,
            warning_count=0,
            health_score=35,
            ready_for_run_agents=False,
        ),
    ) as mocked_check:
        exit_code = main(
            [
                "-p",
                str(tmp_path),
                "--json",
                "run-agents",
                "--spec",
                str(spec_file),
                "--plan",
                str(plan_file),
            ]
        )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 1
    assert payload["status"] == "failure"
    assert mocked_check.call_count == 1
    stages = [item["stage"] for item in payload["meta"]["agent_runs"]]
    assert stages == ["check"]
    assert "requirements" not in stages
    stage_contracts = assert_stage_contracts_shape(payload, expected_stages=["check"])
    check_contract = find_stage_contract(stage_contracts, "check")
    assert check_contract["status"] == "failure"
    assert stage_has_blocking(check_contract)
    outputs = check_contract["outputs"]
    assert outputs["health_score"] == 35
    assert outputs["governance_entry"]["ready_for_run_agents"] is False


def test_run_agents_continues_with_check_warning_and_records_preflight_stage(
    tmp_path: Path, capsys
) -> None:
    """check preflight warning 时，run-agents 应继续并在结果中留痕。"""

    create_minimal_repo(tmp_path)
    write_provider_config(tmp_path, default_provider="cursor")
    spec_file, plan_file = create_run_agents_inputs(tmp_path)
    verify_dir = tmp_path / ".claude/tmp"
    verify_dir.mkdir(parents=True, exist_ok=True)
    (verify_dir / "last-verify.status").write_text("PASS\n", encoding="utf-8")
    (verify_dir / "verification-summary.md").write_text(
        "- pytest 全部通过\n",
        encoding="utf-8",
    )

    with patch(
        "harness_commander.application.commands.run_check",
        return_value=build_check_preflight_result(
            status=ResultStatus.WARNING,
            blocking_count=0,
            warning_count=1,
            health_score=84,
            ready_for_run_agents=True,
        ),
    ):
        exit_code = main(
            [
                "-p",
                str(tmp_path),
                "--json",
                "run-agents",
                "--spec",
                str(spec_file),
                "--plan",
                str(plan_file),
            ]
        )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["status"] == "warning"
    assert [item["stage"] for item in payload["meta"]["agent_runs"]] == [
        "check",
        "requirements",
        "plan",
        "implement",
        "verify",
        "pr-summary",
    ]
    stage_contracts = assert_stage_contracts_shape(
        payload,
        expected_stages=["check", "requirements", "plan", "implement", "verify", "pr-summary"],
    )
    check_contract = find_stage_contract(stage_contracts, "check")
    outputs = check_contract["outputs"]
    assert check_contract["status"] == "warning"
    assert outputs["health_score"] == 84
    assert outputs["governance_entry"]["status"] == "needs_attention"
    assert outputs["governance_entry"]["ready_for_run_agents"] is True


def test_run_agents_continues_normally_when_check_preflight_succeeds(
    tmp_path: Path, capsys
) -> None:
    """check preflight success 时，run-agents 应按既有语义继续。"""

    create_minimal_repo(tmp_path)
    write_provider_config(tmp_path, default_provider="copilot")
    spec_file, plan_file = create_run_agents_inputs(tmp_path)
    verify_dir = tmp_path / ".claude/tmp"
    verify_dir.mkdir(parents=True, exist_ok=True)
    (verify_dir / "last-verify.status").write_text("PASS\n", encoding="utf-8")
    (verify_dir / "verification-summary.md").write_text(
        "- pytest 全部通过\n",
        encoding="utf-8",
    )

    with patch(
        "harness_commander.application.commands.run_check",
        return_value=build_check_preflight_result(
            status=ResultStatus.SUCCESS,
            blocking_count=0,
            warning_count=0,
            health_score=100,
            ready_for_run_agents=True,
        ),
    ):
        exit_code = main(
            [
                "-p",
                str(tmp_path),
                "--json",
                "run-agents",
                "--spec",
                str(spec_file),
                "--plan",
                str(plan_file),
            ]
        )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["status"] == "success"
    assert [item["stage"] for item in payload["meta"]["agent_runs"]] == [
        "check",
        "requirements",
        "plan",
        "implement",
        "verify",
        "pr-summary",
    ]
    stage_contracts = assert_stage_contracts_shape(
        payload,
        expected_stages=["check", "requirements", "plan", "implement", "verify", "pr-summary"],
    )
    check_contract = find_stage_contract(stage_contracts, "check")
    verify_contract = find_stage_contract(stage_contracts, "verify")
    pr_summary_contract = find_stage_contract(stage_contracts, "pr-summary")
    assert check_contract["status"] == "success"
    assert verify_contract["status"] == "success"
    assert not stage_has_blocking(verify_contract)
    assert pr_summary_contract["status"] == "success"



def test_run_agents_blocks_pr_summary_when_verify_is_missing(
    tmp_path: Path, capsys
) -> None:
    """run-agents 在缺少验证状态时应阻断 PR 摘要生成。"""

    create_minimal_repo(tmp_path)
    write_provider_config(tmp_path, default_provider="cursor")
    spec_file, plan_file = create_run_agents_inputs(
        tmp_path,
        spec_content=(
            "# 样例规格\n\n## 业务目标\n- 支持多宿主工具\n\n"
            "## 核心逻辑\n- 保持统一协议\n\n## 验收标准\n- 生成阶段摘要\n"
        ),
        plan_content=(
            "# 样例计划\n\n## Goal\n- 完成编排\n\n## Context\n- 样例上下文\n\n"
            "## Business Logic\n- 按阶段执行\n\n## Scope\n- requirements\n- plan\n\n"
            "## Acceptance Criteria\n- 可阻断 PR\n\n## Exception Handling\n- 失败要保留状态\n\n"
            "## Verification\n- 检查验证状态\n\n"
            "## References\n- `ARCHITECTURE.md`\n- `docs/PLANS.md`\n- `docs/product-specs/v1/index.md`\n\n"
            "## ULW 1: 编排\n\n### 目标\n- 完成执行\n\n### 涉及范围\n- 读取文档\n\n### 验收标准\n- 输出阶段摘要\n"
        ),
    )

    with patch(
        "harness_commander.application.commands.run_check",
        return_value=build_check_preflight_result(status=ResultStatus.SUCCESS),
    ):
        exit_code = main(
            [
                "-p",
                str(tmp_path),
                "--json",
                "run-agents",
                "--spec",
                str(spec_file),
                "--plan",
                str(plan_file),
            ]
        )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["status"] == "warning"
    assert payload["warnings"][0]["code"] == "verify_not_ready_for_pr"
    assert payload["meta"]["provider"] == "cursor"
    assert payload["meta"]["provider_source"] == "default_provider"
    stages = [item["stage"] for item in payload["meta"]["agent_runs"]]
    assert stages == ["check", "requirements", "plan", "implement", "verify"]
    assert payload["artifacts"] == []
    stage_contracts = assert_stage_contracts_shape(
        payload,
        expected_stages=["check", "requirements", "plan", "implement", "verify", "pr-summary"],
    )
    check_contract = find_stage_contract(stage_contracts, "check")
    verify_contract = find_stage_contract(stage_contracts, "verify")
    pr_summary_contract = find_stage_contract(stage_contracts, "pr-summary")
    assert check_contract["status"] == "success"
    assert verify_contract["status"] == "warning"
    assert stage_has_blocking(verify_contract)
    assert pr_summary_contract["status"] == "warning"
    assert stage_has_blocking(pr_summary_contract)


def test_run_agents_provider_override_takes_precedence_over_config(
    tmp_path: Path, capsys
) -> None:
    """run-agents 显式 --provider 应覆盖默认配置。"""

    create_minimal_repo(tmp_path)
    write_provider_config(tmp_path, default_provider="claude")
    spec_file, plan_file = create_run_agents_inputs(tmp_path)
    verify_dir = tmp_path / ".claude/tmp"
    verify_dir.mkdir(parents=True, exist_ok=True)
    (verify_dir / "last-verify.status").write_text("PASS\n", encoding="utf-8")
    (verify_dir / "verification-summary.md").write_text(
        "- pytest 全部通过\n- mypy 全部通过\n", encoding="utf-8"
    )

    with patch(
        "harness_commander.application.commands.run_check",
        return_value=build_check_preflight_result(status=ResultStatus.SUCCESS),
    ):
        exit_code = main(
            [
                "-p",
                str(tmp_path),
                "--json",
                "run-agents",
                "--spec",
                str(spec_file),
                "--plan",
                str(plan_file),
                "--provider",
                "copilot",
            ]
        )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["status"] == "success"
    stages = [item["stage"] for item in payload["meta"]["agent_runs"]]
    assert stages == ["check", "requirements", "plan", "implement", "verify", "pr-summary"]
    pr_summary_path = Path(payload["artifacts"][0]["path"])
    assert pr_summary_path.exists()
    assert "PR Summary" in pr_summary_path.read_text(encoding="utf-8")
    assert payload["meta"]["provider"] == "copilot"
    assert payload["meta"]["provider_source"] == "override"
    stage_contracts = assert_stage_contracts_shape(
        payload,
        expected_stages=["check", "requirements", "plan", "implement", "verify", "pr-summary"],
    )
    check_contract = find_stage_contract(stage_contracts, "check")
    verify_contract = find_stage_contract(stage_contracts, "verify")
    pr_summary_contract = find_stage_contract(stage_contracts, "pr-summary")
    assert check_contract["status"] == "success"
    assert verify_contract["status"] == "success"
    assert not stage_has_blocking(verify_contract)
    assert not stage_uses_fallback(verify_contract)
    assert pr_summary_contract["status"] == "success"
    assert pr_summary_contract["artifacts"]
    assert all(contract["host_model_allowed"] is False for contract in stage_contracts)


def test_run_agents_fails_when_spec_is_missing(tmp_path: Path, capsys) -> None:
    """run-agents 缺少 spec 时应返回稳定 failure。"""

    create_minimal_repo(tmp_path)
    write_provider_config(tmp_path, default_provider="claude")
    _, plan_file = create_run_agents_inputs(tmp_path)
    missing_spec = tmp_path / "docs/product-specs/missing.md"

    with patch(
        "harness_commander.application.commands.run_check",
        return_value=build_check_preflight_result(status=ResultStatus.SUCCESS),
    ):
        exit_code = main(
            [
                "-p",
                str(tmp_path),
                "--json",
                "run-agents",
                "--spec",
                str(missing_spec),
                "--plan",
                str(plan_file),
            ]
        )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 1
    assert payload["status"] == "failure"
    assert payload["errors"][0]["code"] == "spec_not_found"
    assert payload["errors"][0]["location"] == str(missing_spec)


def test_run_agents_fails_when_plan_is_missing(tmp_path: Path, capsys) -> None:
    """run-agents 缺少 plan 时应返回稳定 failure。"""

    create_minimal_repo(tmp_path)
    write_provider_config(tmp_path, default_provider="claude")
    spec_file, _ = create_run_agents_inputs(tmp_path)
    missing_plan = tmp_path / "docs/exec-plans/active/missing.md"

    with patch(
        "harness_commander.application.commands.run_check",
        return_value=build_check_preflight_result(status=ResultStatus.SUCCESS),
    ):
        exit_code = main(
            [
                "-p",
                str(tmp_path),
                "--json",
                "run-agents",
                "--spec",
                str(spec_file),
                "--plan",
                str(missing_plan),
            ]
        )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 1
    assert payload["status"] == "failure"
    assert payload["errors"][0]["code"] == "plan_not_found"
    assert payload["errors"][0]["location"] == str(missing_plan)


def test_run_agents_fails_when_plan_validation_has_blocking_issues(
    tmp_path: Path, capsys
) -> None:
    """run-agents 计划不满足最小治理要求时应返回 failure。"""

    create_minimal_repo(tmp_path)
    write_provider_config(tmp_path, default_provider="claude")
    spec_file, plan_file = create_run_agents_inputs(
        tmp_path,
        plan_content="# 样例计划\n\n## Goal\n- 只有目标，没有引用\n",
    )

    with patch(
        "harness_commander.application.commands.run_check",
        return_value=build_check_preflight_result(status=ResultStatus.SUCCESS),
    ):
        exit_code = main(
            [
                "-p",
                str(tmp_path),
                "--json",
                "run-agents",
                "--spec",
                str(spec_file),
                "--plan",
                str(plan_file),
            ]
        )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 1
    assert payload["status"] == "failure"
    assert payload["summary"] == "执行计划不满足最小治理要求，已停止多 agent 编排。"
    error_codes = {error["code"] for error in payload["errors"]}
    assert "missing_section" in error_codes
    assert "missing_reference" in error_codes


def test_run_agents_blocks_pr_summary_when_verify_status_is_not_pass(
    tmp_path: Path, capsys
) -> None:
    """run-agents 在 verify 非 PASS 时应阻断 PR 摘要生成。"""

    create_minimal_repo(tmp_path)
    write_provider_config(tmp_path, default_provider="claude")
    spec_file, plan_file = create_run_agents_inputs(tmp_path)
    verify_dir = tmp_path / ".claude/tmp"
    verify_dir.mkdir(parents=True, exist_ok=True)
    (verify_dir / "last-verify.status").write_text("FAIL\n", encoding="utf-8")

    with patch(
        "harness_commander.application.commands.run_check",
        return_value=build_check_preflight_result(status=ResultStatus.SUCCESS),
    ):
        exit_code = main(
            [
                "-p",
                str(tmp_path),
                "--json",
                "run-agents",
                "--spec",
                str(spec_file),
                "--plan",
                str(plan_file),
            ]
        )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["status"] == "warning"
    assert payload["warnings"][0]["code"] == "verify_not_ready_for_pr"
    assert payload["warnings"][0]["detail"]["verify_status"] == "warning"
    stages = [item["stage"] for item in payload["meta"]["agent_runs"]]
    assert stages == ["check", "requirements", "plan", "implement", "verify"]
    assert payload["artifacts"] == []
    stage_contracts = assert_stage_contracts_shape(
        payload,
        expected_stages=["check", "requirements", "plan", "implement", "verify", "pr-summary"],
    )
    check_contract = find_stage_contract(stage_contracts, "check")
    verify_contract = find_stage_contract(stage_contracts, "verify")
    pr_summary_contract = find_stage_contract(stage_contracts, "pr-summary")
    assert check_contract["status"] == "success"
    assert verify_contract["status"] == "warning"
    assert stage_has_blocking(verify_contract)
    assert pr_summary_contract["status"] == "warning"
    assert stage_has_blocking(pr_summary_contract)


def test_run_agents_dry_run_reports_pr_summary_without_writing_file(
    tmp_path: Path, capsys
) -> None:
    """run-agents dry-run 在 verify 通过时应只报告将创建的 PR 摘要。"""

    create_minimal_repo(tmp_path)
    write_provider_config(tmp_path, default_provider="claude")
    spec_file, plan_file = create_run_agents_inputs(tmp_path)
    verify_dir = tmp_path / ".claude/tmp"
    verify_dir.mkdir(parents=True, exist_ok=True)
    (verify_dir / "last-verify.status").write_text("PASS\n", encoding="utf-8")
    (verify_dir / "verification-summary.md").write_text("- pytest 全部通过\n", encoding="utf-8")

    with patch(
        "harness_commander.application.commands.run_check",
        return_value=build_check_preflight_result(status=ResultStatus.SUCCESS),
    ):
        exit_code = main(
            [
                "-p",
                str(tmp_path),
                "--json",
                "run-agents",
                "--spec",
                str(spec_file),
                "--plan",
                str(plan_file),
                "--dry-run",
            ]
        )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["status"] == "success"
    assert payload["artifacts"][0]["action"] == "would_create"
    pr_summary_path = Path(payload["artifacts"][0]["path"])
    assert not pr_summary_path.exists()
    stages = [item["stage"] for item in payload["meta"]["agent_runs"]]
    assert stages == ["check", "requirements", "plan", "implement", "verify", "pr-summary"]
    stage_contracts = assert_stage_contracts_shape(
        payload,
        expected_stages=["check", "requirements", "plan", "implement", "verify", "pr-summary"],
    )
    check_contract = find_stage_contract(stage_contracts, "check")
    verify_contract = find_stage_contract(stage_contracts, "verify")
    pr_summary_contract = find_stage_contract(stage_contracts, "pr-summary")
    assert check_contract["status"] == "success"
    assert verify_contract["status"] == "success"
    assert not stage_has_blocking(verify_contract)
    assert pr_summary_contract["status"] == "success"
    assert not stage_uses_fallback(pr_summary_contract)


def test_install_provider_cli_dispatches_supported_targets(tmp_path: Path, capsys) -> None:
    """install-provider 应接受 install target 并透传到命令层。"""

    with patch("harness_commander.cli.run_install_provider") as mocked_run:
        mocked_run.return_value = CommandResult(
            command="install-provider",
            status=ResultStatus.SUCCESS,
            summary="ok",
        )
        exit_code = main(
            [
                "-p",
                str(tmp_path),
                "install-provider",
                "--provider",
                "auto",
                "--dry-run",
            ]
        )

    assert exit_code == 0
    assert INSTALL_TARGETS == (
        "claude",
        "cursor",
        "codex",
        "openclaw",
        "trae",
        "copilot",
        "all",
        "auto",
    )
    assert mocked_run.call_args.kwargs["provider"] == "auto"
    assert mocked_run.call_args.kwargs["dry_run"] is True


def test_install_provider_provider_spec_and_summary(tmp_path: Path, capsys) -> None:
    """install-provider 的 provider 规格与摘要应反映 Claude 真实安装能力。"""

    create_minimal_repo(tmp_path)
    user_skill_dir = tmp_path / "user-home/.claude/skills"

    spec = get_provider_spec("claude")
    assert spec.install_support_level == "fully_supported"
    assert spec.wrapper_source == "host_templates/claude/harness"
    assert spec.legacy_project_skill_target == ".claude/skills/harness/SKILL.md"

    with patch(
        "harness_commander.application.provider_installers._detect_provider_cli",
        return_value=True,
    ), patch.dict(
        "os.environ",
        {"HARNESS_CLAUDE_SKILLS_DIR": str(user_skill_dir)},
        clear=False,
    ):
        exit_code = main(
            ["-p", str(tmp_path), "--json", "install-provider", "--provider", "claude"]
        )
        captured = capsys.readouterr()
        payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["status"] == "success"
    assert payload["meta"]["results"]["claude"]["status"] == "installed"
    assert payload["meta"]["results"]["claude"]["wrapper_kind"] == "skill"
    assert payload["meta"]["results"]["claude"]["installation_mode"] == "user_skill_copy"
    assert payload["meta"]["results"]["claude"]["install_attempted"] is True
    assert payload["meta"]["results"]["claude"]["resolved_target_dir"] is not None
    assert "1 个已完成真实安装" in payload["summary"]


def test_install_provider_returns_warning_when_user_target_is_not_writable(
    tmp_path: Path, capsys
) -> None:
    """install-provider 遇到用户目录权限失败时应返回稳定 warning 结果。"""

    create_minimal_repo(tmp_path)

    with patch(
        "harness_commander.application.provider_installers._detect_provider_cli",
        return_value=True,
    ), patch.dict(
        "os.environ",
        {"HARNESS_CLAUDE_SKILLS_DIR": str(tmp_path / "user-home/.claude/skills")},
        clear=False,
    ), patch(
        "harness_commander.application.provider_installers.write_text",
        side_effect=PermissionError("permission denied"),
    ):
        exit_code = main(
            ["-p", str(tmp_path), "--json", "install-provider", "--provider", "claude"]
        )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["status"] == "warning"
    result = payload["meta"]["results"]["claude"]
    assert result["status"] == "failed_permission"
    assert result["failure_reason_code"] == "target_not_writable"
    assert result["wrapper_kind"] == "skill"
    assert result["install_attempted"] is True
    assert payload["warnings"][0]["code"] == "provider_install_incomplete"
    assert payload["meta"]["installed_providers"] == []
    config_payload = json.loads(
        (tmp_path / ".harness/provider-config.json").read_text(encoding="utf-8")
    )
    assert config_payload["installation_results"]["claude"]["status"] == "failed_permission"
    assert config_payload["installed_providers"] == []



def test_check_reports_blocking_issue_with_required_metadata(
    tmp_path: Path, capsys
) -> None:
    """check 命令发现阻断项时，应返回非零退出码和完整审计元信息。"""

    create_minimal_repo(tmp_path)
    source_file = tmp_path / "src/demo.py"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_text('password = "supersecret"\n', encoding="utf-8")

    exit_code = main(["-p", str(tmp_path), "--json", "check"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 1
    assert payload["command"] == "check"
    assert payload["status"] == "failure"
    assert payload["errors"]
    issue = next(
        error for error in payload["errors"] if error["code"] == "potential_secret_exposure"
    )
    assert issue["detail"]["severity"] == "blocking"
    assert issue["detail"]["source"] == "docs/SECURITY.md"
    assert issue["location"] == "src/demo.py"
    assert issue["detail"]["suggestion"]
    assert issue["detail"]["impact_scope"] == "仓库包含疑似明文凭据，存在泄露和误用风险。"
    assert payload["summary"].startswith("审计完成，发现")
    meta = payload["meta"]
    assert isinstance(meta["health_score"], int)
    assert 0 <= meta["health_score"] <= 100
    governance_entry = meta["governance_entry"]
    assert governance_entry["status"] == "blocked"
    assert governance_entry["ready_for_run_agents"] is False
    assert governance_entry["ready_for_clean_pass"] is False
    assert isinstance(governance_entry["recommended_entrypoint"], str)
    assert governance_entry["recommended_entrypoint"]
    next_actions = meta["next_actions"]
    assert isinstance(next_actions, list)
    assert next_actions
    assert any(
        isinstance(action, dict)
        and isinstance(action.get("summary"), str)
        and action["summary"]
        for action in next_actions
    )


def test_check_marks_template_only_governance_docs_as_unquantified(
    tmp_path: Path, capsys
) -> None:
    """说明型规则文档应被标记为未量化，而不是伪造通过。"""

    create_minimal_repo(tmp_path)
    (tmp_path / "docs/QUALITY_SCORE.md").write_text(
        "质量规范说明\n\n这个文件暂时只有说明文字，没有可检查条目。\n",
        encoding="utf-8",
    )
    (tmp_path / "docs/SECURITY.md").write_text(
        "安全规范说明\n\n这里只描述背景，不提供列表规则。\n",
        encoding="utf-8",
    )
    (tmp_path / "docs/design-docs/core-beliefs.md").write_text(
        "团队信仰说明\n\n当前仍在整理判断条件。\n",
        encoding="utf-8",
    )

    exit_code = main(["-p", str(tmp_path), "--json", "check"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["status"] == "warning"
    assert payload["meta"]["blocking_count"] == 0
    assert payload["meta"]["unquantified_count"] == 4
    unquantified_warnings = [
        warning for warning in payload["warnings"] if warning["code"] == "unquantified_rule_source"
    ]
    assert len(unquantified_warnings) == 4
    assert all(not warning["detail"]["quantifiable"] for warning in unquantified_warnings)
    assert all("impact_scope" in warning["detail"] for warning in unquantified_warnings)
    assert "未量化" in payload["summary"]
    governance_entry = payload["meta"]["governance_entry"]
    assert governance_entry["status"] == "needs_attention"
    assert governance_entry["ready_for_run_agents"] is False
    assert isinstance(governance_entry["recommended_entrypoint"], str)
    assert governance_entry["recommended_entrypoint"]
    next_actions = payload["meta"]["next_actions"]
    assert isinstance(next_actions, list)
    assert next_actions
    assert next_actions[0]["code"] == "create_active_plan"
    assert next_actions[0]["recommended_command"] == "harness propose-plan"
    assert payload["meta"]["health_score"] < 100


def test_check_reports_default_targets_in_meta(tmp_path: Path, capsys) -> None:
    """check 应在元信息中暴露默认检查对象。"""

    create_minimal_repo(tmp_path)
    plan_dir = tmp_path / "docs/exec-plans/active"
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / "demo.md").write_text("# demo\n", encoding="utf-8")
    ref_file = tmp_path / "docs/references/demo-llms.txt"
    ref_file.parent.mkdir(parents=True, exist_ok=True)
    ref_file.write_text("reference\n", encoding="utf-8")

    exit_code = main(["-p", str(tmp_path), "--json", "check"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["meta"]["checks"]["all"]
    checked_targets = payload["meta"]["checked_targets"]
    assert checked_targets["plan_files"] == ["docs/exec-plans/active/demo.md"]
    assert checked_targets["generated_files"] == ["docs/references/demo-llms.txt"]
    governance_entry = payload["meta"]["governance_entry"]
    assert governance_entry["ready_for_run_agents"] is True
    assert governance_entry["status"] in {"needs_attention", "ready"}


def test_sync_returns_governance_snapshot_when_only_baseline_exists(
    tmp_path: Path, capsys
) -> None:
    """sync 在仅有治理基线文件时应识别治理文档快照更新。"""

    create_minimal_repo(tmp_path)
    exit_code = main(["-p", str(tmp_path), "--json", "sync", "--dry-run"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["command"] == "sync"
    assert payload["status"] == "success"
    assert payload["meta"]["change_count"] == 1
    assert payload["meta"]["change_types"] == ["governance_docs"]
    assert len(payload["artifacts"]) == 1


def test_sync_snapshot_contains_summary_sections(tmp_path: Path, capsys) -> None:
    """sync 生成的快照应包含摘要、来源、内容摘录和建议区块。"""

    create_minimal_repo(tmp_path)
    migration_file = tmp_path / "migrations/0001_init.sql"
    migration_file.parent.mkdir(parents=True, exist_ok=True)
    migration_file.write_text("create table demo(id integer primary key);\n", encoding="utf-8")

    exit_code = main(["-p", str(tmp_path), "--json", "sync"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    db_snapshot = next(
        path for path in payload["meta"]["updated_targets"] if path == "docs/generated/db-schema.md"
    )
    content = (tmp_path / db_snapshot).read_text(encoding="utf-8")
    assert "## 变更摘要" in content
    assert "## 命中来源" in content
    assert "## 内容摘录" in content
    assert "## 更新建议" in content
    assert "migrations/0001_init.sql" in content
    assert "create table demo" in content


def test_sync_updates_only_impacted_targets(tmp_path: Path, capsys) -> None:
    """sync 只更新被重大变更命中的目标产物。"""

    create_minimal_repo(tmp_path)
    migration_file = tmp_path / "migrations/0001_init.sql"
    migration_file.parent.mkdir(parents=True, exist_ok=True)
    migration_file.write_text("create table demo(id integer primary key);\n", encoding="utf-8")

    exit_code = main(["-p", str(tmp_path), "--json", "sync", "--dry-run"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["meta"]["change_count"] == 2
    assert payload["meta"]["change_types"] == ["database_schema", "governance_docs"]
    assert len(payload["artifacts"]) == 2
    artifact_paths = [artifact["path"] for artifact in payload["artifacts"]]
    assert any(path.endswith("docs/generated/db-schema.md") for path in artifact_paths)
    assert any(path.endswith("docs/references/uv-llms.txt") for path in artifact_paths)
    assert any(
        "migrations/0001_init.sql" in artifact["note"] for artifact in payload["artifacts"]
    )
    db_change = next(
        change for change in payload["meta"]["changes"] if change["type"] == "database_schema"
    )
    assert db_change["content_summary"][0]["path"] == "migrations/0001_init.sql"
    assert "create table demo" in db_change["content_summary"][0]["excerpt"]
