"""端到端集成测试。

该测试文件覆盖 Harness-Commander 的完整工作流程：
从项目初始化到文档同步、信息提取、一致性检查的完整流程。
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

import json  # noqa: E402
from unittest.mock import patch  # noqa: E402

from harness_commander.application.model_tasks import HostModelError  # noqa: E402
from harness_commander.cli import main  # noqa: E402
from harness_commander.domain.models import (  # noqa: E402
    CommandMessage,
    CommandResult,
    ResultStatus,
)


def write_provider_config(
    root: Path,
    *,
    default_provider: str,
    status: str = "config_only",
    support_level: str = "config_only",
) -> None:
    """写入集成测试使用的最小 provider 配置。"""

    config_path = root / ".harness/provider-config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(
            {
                "version": 1,
                "default_provider": default_provider,
                "installed_providers": [default_provider],
                "installation_results": {
                    default_provider: {
                        "status": status,
                        "support_level": support_level,
                        "detected": True,
                        "cli_command": default_provider,
                        "configured_at": "2026-04-07T00:00:00Z",
                        "message": "configured in integration test",
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
    """构造 run-agents 集成测试使用的最小 spec/plan 文档。"""

    v1_index = root / "docs/product-specs/v1/index.md"
    v1_index.parent.mkdir(parents=True, exist_ok=True)
    v1_index.write_text("# spec v1 index\n", encoding="utf-8")

    spec_file = root / "docs/product-specs/sample.md"
    spec_file.write_text(
        spec_content
        or (
            "# 样例规格\n\n"
            "## 业务目标\n- 支持更多 provider\n\n"
            "## 核心逻辑\n- 顺序阶段编排\n\n"
            "## 验收标准\n- 返回 agent_runs\n"
        ),
        encoding="utf-8",
    )
    plan_file = root / "docs/exec-plans/active/sample.md"
    plan_file.write_text(
        plan_content
        or (
            "# 样例计划\n\n"
            "## Goal\n- 完成编排\n\n"
            "## Context\n- 样例上下文\n\n"
            "## Business Logic\n- 顺序执行\n\n"
            "## Scope\n- requirements\n\n"
            "## Acceptance Criteria\n- 输出阶段摘要\n\n"
            "## Exception Handling\n- 验证失败不整理 PR\n\n"
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
    for items in section_sources.values():
        assert isinstance(items, list)
        for item in items:
            assert isinstance(item, dict)
            assert isinstance(item.get("text"), str)
            assert item.get("mapping_status") in {"mapped", "unmatched"}
    return extraction_report, section_sources, source_mapping_coverage


def flatten_distill_sources(
    section_sources: dict[str, list[dict[str, object]]],
) -> list[dict[str, object]]:
    """拍平 section_sources，便于统一断言。"""

    flattened: list[dict[str, object]] = []
    for items in section_sources.values():
        flattened.extend(items)
    return flattened



def test_full_workflow_with_dry_run(tmp_path: Path, capsys) -> None:
    """测试完整工作流程（使用 dry-run 模式）。"""

    exit_code = main(["-p", str(tmp_path), "init"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "[success] init" in captured.out

    test_doc = tmp_path / "test-document.md"
    test_doc.write_text(
        """# 测试文档

## 业务目标
测试 distill 命令的功能

## 核心逻辑
- 规则1: 测试规则提取
- 规则2: 测试信息压缩

## 技术实现
使用 Python 实现
""",
        encoding="utf-8",
    )

    exit_code = main(["-p", str(tmp_path), "distill", str(test_doc), "--dry-run"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "[warning] distill" in captured.out
    assert "would_create" in captured.out

    exit_code = main(["-p", str(tmp_path), "check", "--dry-run"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "[warning] check" in captured.out

    migration_file = tmp_path / "migrations/0001_init.sql"
    migration_file.parent.mkdir(parents=True, exist_ok=True)
    migration_file.write_text("create table users(id integer primary key);\n", encoding="utf-8")
    exit_code = main(["-p", str(tmp_path), "sync", "--dry-run"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "[success] sync" in captured.out
    assert "would_update" in captured.out
    assert "db-schema.md" in captured.out


def test_json_output_consistency(tmp_path: Path, capsys) -> None:
    """测试命令的 JSON 输出格式一致性。"""

    exit_code = main(["-p", str(tmp_path), "init"])
    captured = capsys.readouterr()
    assert exit_code == 0

    migration_file = tmp_path / "migrations/0001_init.sql"
    migration_file.parent.mkdir(parents=True, exist_ok=True)
    migration_file.write_text("create table audit(id integer primary key);\n", encoding="utf-8")

    commands_to_test = [
        ["--json", "sync", "--dry-run"],
        ["--json", "distill", str(tmp_path / "docs/SECURITY.md")],
    ]

    for command_args in commands_to_test:
        exit_code = main(["-p", str(tmp_path), *command_args])
        captured = capsys.readouterr()
        assert exit_code == 0
        result = json.loads(captured.out.strip())
        assert "command" in result
        assert "status" in result
        assert "summary" in result
        assert isinstance(result.get("artifacts", []), list)
        assert isinstance(result.get("warnings", []), list)
        assert isinstance(result.get("meta", {}), dict)


def test_command_chaining(tmp_path: Path, capsys) -> None:
    """测试命令链式执行。"""

    exit_code = main(["-p", str(tmp_path), "init"])
    captured = capsys.readouterr()
    assert exit_code == 0

    test_doc = tmp_path / "requirements.md"
    test_doc.write_text(
        """# 需求文档

## 业务目标
构建一个测试系统

## 核心需求
1. 用户管理
2. 权限控制
3. 数据导出

## 技术约束
- 使用 Python 3.10+
- 支持 JSON 输出
- 包含完整的测试覆盖
""",
        encoding="utf-8",
    )

    migration_file = tmp_path / "migrations/0001_init.sql"
    migration_file.parent.mkdir(parents=True, exist_ok=True)
    migration_file.write_text("create table reports(id integer primary key);\n", encoding="utf-8")

    exit_code = main(["-p", str(tmp_path), "--json", "distill", str(test_doc)])
    captured = capsys.readouterr()
    assert exit_code == 0
    distill_result = json.loads(captured.out.strip())
    assert distill_result["command"] == "distill"
    assert distill_result["artifacts"]
    extraction_report, _, source_mapping_coverage = assert_distill_mapping_meta(
        distill_result
    )
    assert extraction_report["extracted_section_count"] >= 1
    assert source_mapping_coverage["total_items"] >= 1
    output_path = Path(distill_result["meta"]["target_path"])
    assert "来源映射" in output_path.read_text(encoding="utf-8")
    _, section_sources, source_mapping_coverage = assert_distill_mapping_meta(
        distill_result
    )
    assert source_mapping_coverage["mapped_items"] >= 1
    target_path = Path(distill_result["meta"]["target_path"])
    assert "来源映射" in target_path.read_text(encoding="utf-8")
    assert flatten_distill_sources(section_sources)

    sync_exit_code = main(["-p", str(tmp_path), "--json", "sync"])
    sync_captured = capsys.readouterr()
    assert sync_exit_code == 0
    sync_result = json.loads(sync_captured.out.strip())
    assert sync_result["command"] == "sync"
    assert sync_result["status"] == "success"
    assert sync_result["meta"]["change_count"] >= 1

    check_exit_code = main(["-p", str(tmp_path), "--json", "check"])
    check_captured = capsys.readouterr()
    assert check_exit_code == 0
    check_result = json.loads(check_captured.out.strip())
    assert check_result["command"] == "check"
    assert check_result["status"] == "warning"
    assert check_result["meta"]["blocking_count"] == 0
    assert check_result["meta"]["warning_count"] >= 1


def test_install_provider_then_host_model_commands_use_config(tmp_path: Path, capsys, monkeypatch) -> None:
    """install-provider 安装用户级 Claude skill 后，后续命令仍应读取 provider 配置。"""

    exit_code = main(["-p", str(tmp_path), "init"])
    captured = capsys.readouterr()
    assert exit_code == 0

    fake_user_skill_dir = tmp_path / "user-home/.claude/skills"
    monkeypatch.setenv("HARNESS_CLAUDE_SKILLS_DIR", str(fake_user_skill_dir))

    install_exit_code = main(
        ["-p", str(tmp_path), "--json", "install-provider", "--provider", "claude"]
    )
    install_captured = capsys.readouterr()
    install_payload = json.loads(install_captured.out.strip())
    assert install_exit_code == 0
    assert install_payload["meta"]["results"]["claude"]["status"] == "installed"
    assert (fake_user_skill_dir / "harness-commander/SKILL.md").exists()
    assert (fake_user_skill_dir / "harness-commander/Reference/README.md").exists()

    test_doc = tmp_path / "requirements.md"
    test_doc.write_text("# 需求文档\n\n## 业务目标\n构建一个测试系统\n", encoding="utf-8")

    with patch(
        "harness_commander.application.commands.distill_with_host_model",
        return_value={
            "goals": ["提升覆盖率"],
            "rules": ["必须补齐 provider 配置"],
            "limits": ["只做最小重构"],
            "prohibitions": ["不得把 override 当主路径"],
        },
    ):
        exit_code = main(
            [
                "-p",
                str(tmp_path),
                "--json",
                "distill",
                str(test_doc),
                "--mode",
                "host-model",
            ]
        )
    captured = capsys.readouterr()
    payload = json.loads(captured.out.strip())

    assert exit_code == 0
    assert payload["meta"]["provider"] == "claude"
    assert payload["meta"]["provider_source"] == "default_provider"
    assert payload["meta"]["model_provider"] == "claude-cli"
    extraction_report, section_sources, source_mapping_coverage = assert_distill_mapping_meta(
        payload
    )
    assert extraction_report["extraction_source"] == "host-model"
    assert source_mapping_coverage["total_items"] >= 1
    assert any(
        item.get("mapping_status") == "unmatched"
        for item in flatten_section_sources(section_sources)
    )
    extraction_report, section_sources, source_mapping_coverage = assert_distill_mapping_meta(
        payload
    )
    assert extraction_report["extraction_source"] == "host-model"
    assert source_mapping_coverage["total_items"] >= 1
    assert any(
        item.get("mapping_status") == "unmatched"
        for item in flatten_distill_sources(section_sources)
    )


def test_host_model_distill_uses_configured_provider_integration(
    tmp_path: Path, capsys
) -> None:
    """集成层应验证 host-model 默认读取配置 provider。"""

    exit_code = main(["-p", str(tmp_path), "init"])
    captured = capsys.readouterr()
    assert exit_code == 0
    write_provider_config(tmp_path, default_provider="codex")

    test_doc = tmp_path / "requirements.md"
    test_doc.write_text("# 需求文档\n\n## 业务目标\n构建一个测试系统\n", encoding="utf-8")

    with patch(
        "harness_commander.application.commands.distill_with_host_model",
        return_value={
            "goals": ["提升覆盖率"],
            "rules": ["必须补齐 provider 配置"],
            "limits": ["只做最小重构"],
            "prohibitions": ["不得把 override 当主路径"],
        },
    ):
        exit_code = main(
            [
                "-p",
                str(tmp_path),
                "--json",
                "distill",
                str(test_doc),
                "--mode",
                "host-model",
            ]
        )
    captured = capsys.readouterr()
    payload = json.loads(captured.out.strip())

    assert exit_code == 0
    assert payload["meta"]["provider"] == "codex"
    assert payload["meta"]["provider_source"] == "default_provider"
    assert payload["meta"]["model_provider"] == "codex-cli"
    extraction_report, _, source_mapping_coverage = assert_distill_mapping_meta(payload)
    assert extraction_report["extraction_source"] == "host-model"
    assert source_mapping_coverage["total_items"] >= 1
    extraction_report, section_sources, source_mapping_coverage = assert_distill_mapping_meta(
        payload
    )
    assert extraction_report["extraction_source"] == "host-model"
    assert source_mapping_coverage["total_items"] >= 1
    assert any(
        item.get("mapping_status") == "unmatched"
        for item in flatten_distill_sources(section_sources)
    )



def test_host_model_distill_json_contract(tmp_path: Path, capsys) -> None:
    """host-model 模式应保留统一 JSON 协议与 fallback 字段。"""

    exit_code = main(["-p", str(tmp_path), "init"])
    captured = capsys.readouterr()
    assert exit_code == 0
    write_provider_config(tmp_path, default_provider="claude")

    test_doc = tmp_path / "requirements.md"
    test_doc.write_text(
        "# 需求文档\n\n## 业务目标\n构建一个测试系统\n",
        encoding="utf-8",
    )

    with patch(
        "harness_commander.application.commands.distill_with_host_model",
        side_effect=HostModelError("mock unavailable"),
    ):
        exit_code = main(
            [
                "-p",
                str(tmp_path),
                "--json",
                "distill",
                str(test_doc),
                "--mode",
                "auto",
            ]
        )
    captured = capsys.readouterr()
    payload = json.loads(captured.out.strip())

    assert exit_code == 0
    assert payload["command"] == "distill"
    assert payload["meta"]["distill_mode"] == "auto"
    assert payload["meta"]["fallback_from"] == "host-model"
    assert payload["meta"]["extraction_source"] == "heuristic"
    assert any(
        warning["code"] == "distill_fallback_to_heuristic"
        for warning in payload["warnings"]
    )
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
    extraction_report, section_sources, source_mapping_coverage = assert_distill_mapping_meta(
        payload
    )
    assert extraction_report["extraction_source"] == "heuristic"
    flattened = flatten_distill_sources(section_sources)
    assert flattened
    assert source_mapping_coverage["total_items"] >= 1
    assert all(
        item.get("mapping_status") in {"mapped", "unmatched"} for item in flattened
    )
    assert (
        any(item.get("mapping_status") == "unmatched" for item in flattened)
        or extraction_report["unresolved_sections"]
    )


def test_distill_insufficient_extraction_returns_stable_failure_integration(
    tmp_path: Path, capsys
) -> None:
    """integration 层应锁住 distillation_insufficient 的真实 failure 协议。"""

    exit_code = main(["-p", str(tmp_path), "init"])
    captured = capsys.readouterr()
    assert exit_code == 0

    test_doc = tmp_path / "brief.md"
    test_doc.write_text("# 简短文档\n\n只有一句描述。\n", encoding="utf-8")

    exit_code = main(["-p", str(tmp_path), "--json", "distill", str(test_doc)])
    captured = capsys.readouterr()
    payload = json.loads(captured.out.strip())

    assert exit_code == 1
    assert payload["command"] == "distill"
    assert payload["status"] == "failure"
    assert payload["warnings"][0]["code"] == "partial_distillation"
    assert payload["errors"][0]["code"] == "distillation_insufficient"
    assert payload["meta"]["distill_mode"] == "heuristic"
    assert payload["meta"]["extraction_source"] == "heuristic"
    assert payload["artifacts"] == []
    assert not Path(payload["meta"]["target_path"]).exists()
    assert "未生成参考材料" in payload["summary"]
    extraction_report, section_sources, source_mapping_coverage = assert_distill_mapping_meta(
        payload
    )
    assert extraction_report["extracted_section_count"] == 0
    assert source_mapping_coverage["total_items"] == 0
    assert isinstance(section_sources, dict)
    assert set(section_sources.keys()) == {"goals", "rules", "limits", "prohibitions"}


def test_distill_host_model_requires_provider_integration(
    tmp_path: Path, capsys
) -> None:
    """integration 层应锁住 host-model 缺少 provider 时的稳定 failure。"""

    exit_code = main(["-p", str(tmp_path), "init"])
    captured = capsys.readouterr()
    assert exit_code == 0

    test_doc = tmp_path / "requirements.md"
    test_doc.write_text("# 任意文档\n\n原始内容。\n", encoding="utf-8")

    exit_code = main(
        [
            "-p",
            str(tmp_path),
            "--json",
            "distill",
            str(test_doc),
            "--mode",
            "host-model",
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out.strip())

    assert exit_code == 1
    assert payload["command"] == "distill"
    assert payload["status"] == "failure"
    assert payload["artifacts"] == []
    assert payload["errors"][0]["code"] == "provider_not_configured"
    assert payload["meta"] == {}


def test_run_agents_preflight_failure_blocks_following_stages_integration(
    tmp_path: Path, capsys
) -> None:
    """check preflight failure 时应在集成层阻断后续阶段。"""

    exit_code = main(["-p", str(tmp_path), "init"])
    captured = capsys.readouterr()
    assert exit_code == 0
    write_provider_config(tmp_path, default_provider="cursor")
    spec_file, plan_file = create_run_agents_inputs(tmp_path)

    with patch(
        "harness_commander.application.commands.run_check",
        return_value=build_check_preflight_result(
            status=ResultStatus.FAILURE,
            blocking_count=1,
            warning_count=0,
            health_score=40,
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
    payload = json.loads(captured.out.strip())

    assert exit_code == 1
    assert payload["status"] == "failure"
    assert mocked_check.call_count == 1
    assert [item["stage"] for item in payload["meta"]["agent_runs"]] == ["check"]
    stage_contracts = assert_stage_contracts_shape(payload, expected_stages=["check"])
    check_contract = find_stage_contract(stage_contracts, "check")
    assert check_contract["status"] == "failure"
    assert stage_has_blocking(check_contract)
    assert check_contract["outputs"]["health_score"] == 40


def test_run_agents_preflight_warning_continues_and_leaves_trace_integration(
    tmp_path: Path, capsys
) -> None:
    """check preflight warning 时应继续执行并留下阶段留痕。"""

    exit_code = main(["-p", str(tmp_path), "init"])
    captured = capsys.readouterr()
    assert exit_code == 0
    write_provider_config(tmp_path, default_provider="cursor")
    spec_file, plan_file = create_run_agents_inputs(tmp_path)
    verify_dir = tmp_path / ".claude/tmp"
    verify_dir.mkdir(parents=True, exist_ok=True)
    (verify_dir / "last-verify.status").write_text("PASS\n", encoding="utf-8")
    (verify_dir / "verification-summary.md").write_text(
        "- pytest all passed\n",
        encoding="utf-8",
    )

    with patch(
        "harness_commander.application.commands.run_check",
        return_value=build_check_preflight_result(
            status=ResultStatus.WARNING,
            blocking_count=0,
            warning_count=1,
            health_score=82,
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
    payload = json.loads(captured.out.strip())

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
    assert check_contract["status"] == "warning"
    assert check_contract["outputs"]["governance_entry"]["status"] == "needs_attention"
    assert check_contract["outputs"]["health_score"] == 82


def test_run_agents_preflight_success_keeps_verify_pr_summary_semantics_integration(
    tmp_path: Path, capsys
) -> None:
    """check preflight success 时应保持 verify/pr-summary 的既有成功语义。"""

    exit_code = main(["-p", str(tmp_path), "init"])
    captured = capsys.readouterr()
    assert exit_code == 0
    write_provider_config(tmp_path, default_provider="claude")
    spec_file, plan_file = create_run_agents_inputs(tmp_path)
    verify_dir = tmp_path / ".claude/tmp"
    verify_dir.mkdir(parents=True, exist_ok=True)
    (verify_dir / "last-verify.status").write_text("PASS\n", encoding="utf-8")
    (verify_dir / "verification-summary.md").write_text(
        "- pytest all passed\n",
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
    payload = json.loads(captured.out.strip())

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
    assert pr_summary_contract["artifacts"]


def test_run_agents_real_check_failure_blocks_integration(
    tmp_path: Path, capsys
) -> None:
    """不 mock check 时，真实阻断项也应直接拦住 run-agents。"""

    exit_code = main(["-p", str(tmp_path), "init"])
    captured = capsys.readouterr()
    assert exit_code == 0
    write_provider_config(tmp_path, default_provider="claude")
    spec_file, plan_file = create_run_agents_inputs(tmp_path)
    (tmp_path / "docs/QUALITY_SCORE.md").unlink()

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
    payload = json.loads(captured.out.strip())

    assert exit_code == 1
    assert payload["status"] == "failure"
    assert [item["stage"] for item in payload["meta"]["agent_runs"]] == ["check"]
    assert any(error["code"] == "missing_governance_source" for error in payload["errors"])
    stage_contracts = assert_stage_contracts_shape(payload, expected_stages=["check"])
    check_contract = find_stage_contract(stage_contracts, "check")
    assert check_contract["status"] == "failure"
    assert stage_has_blocking(check_contract)


def test_run_agents_real_check_warning_continues_integration(
    tmp_path: Path, capsys
) -> None:
    """不 mock check 时，真实 warning 应留痕并继续主链。"""

    exit_code = main(["-p", str(tmp_path), "init"])
    captured = capsys.readouterr()
    assert exit_code == 0
    write_provider_config(tmp_path, default_provider="cursor")
    spec_file, plan_file = create_run_agents_inputs(tmp_path)
    (tmp_path / "docs/product-specs/v1/index.md").write_text(
        "# spec v1 index\n",
        encoding="utf-8",
    )

    verify_dir = tmp_path / ".claude/tmp"
    verify_dir.mkdir(parents=True, exist_ok=True)
    (verify_dir / "last-verify.status").write_text("PASS\n", encoding="utf-8")
    (verify_dir / "verification-summary.md").write_text(
        "- pytest all passed\n",
        encoding="utf-8",
    )

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
    payload = json.loads(captured.out.strip())

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
    warning_codes = {warning["code"] for warning in payload["warnings"]}
    assert "unquantified_rule_source" in warning_codes
    stage_contracts = assert_stage_contracts_shape(
        payload,
        expected_stages=["check", "requirements", "plan", "implement", "verify", "pr-summary"],
    )
    check_contract = find_stage_contract(stage_contracts, "check")
    assert check_contract["status"] == "warning"
    assert stage_has_blocking(check_contract)


def test_run_agents_uses_configured_provider_and_override_integration(
    tmp_path: Path, capsys
) -> None:
    """集成层应验证 run-agents 默认配置与显式 override。"""

    exit_code = main(["-p", str(tmp_path), "init"])
    captured = capsys.readouterr()
    assert exit_code == 0
    write_provider_config(tmp_path, default_provider="cursor")
    spec_file, plan_file = create_run_agents_inputs(tmp_path)

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
    default_payload = json.loads(captured.out.strip())

    assert exit_code == 0
    assert default_payload["meta"]["provider"] == "cursor"
    assert default_payload["meta"]["provider_source"] == "default_provider"

    with patch(
        "harness_commander.application.commands.run_check",
        return_value=build_check_preflight_result(status=ResultStatus.SUCCESS),
    ):
        override_exit_code = main(
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
                "--dry-run",
            ]
        )
    override_captured = capsys.readouterr()
    override_payload = json.loads(override_captured.out.strip())

    assert override_exit_code == 0
    assert override_payload["meta"]["provider"] == "copilot"
    assert override_payload["meta"]["provider_source"] == "override"



def test_run_agents_json_contract(tmp_path: Path, capsys) -> None:
    """run-agents 应返回稳定 JSON 协议。"""

    exit_code = main(["-p", str(tmp_path), "init"])
    captured = capsys.readouterr()
    assert exit_code == 0
    spec_file, plan_file = create_run_agents_inputs(tmp_path)

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
                "cursor",
                "--dry-run",
            ]
        )
    captured = capsys.readouterr()
    result = json.loads(captured.out.strip())

    assert exit_code == 0
    assert result["command"] == "run-agents"
    assert result["meta"]["provider"] == "cursor"
    assert isinstance(result["meta"]["agent_runs"], list)
    assert [item["stage"] for item in result["meta"]["agent_runs"]] == [
        "check",
        "requirements",
        "plan",
        "implement",
        "verify",
    ]
    stage_contracts = assert_stage_contracts_shape(
        result,
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


def test_run_agents_blocks_pr_summary_for_non_pass_verify_status_integration(
    tmp_path: Path, capsys
) -> None:
    """集成层应验证 verify 非 PASS 时不会生成 PR 摘要。"""

    exit_code = main(["-p", str(tmp_path), "init"])
    captured = capsys.readouterr()
    assert exit_code == 0
    write_provider_config(tmp_path, default_provider="cursor")
    spec_file, plan_file = create_run_agents_inputs(tmp_path)

    verify_dir = tmp_path / ".claude/tmp"
    verify_dir.mkdir(parents=True, exist_ok=True)
    (verify_dir / "last-verify.status").write_text("FAILED\n", encoding="utf-8")
    (verify_dir / "verification-summary.md").write_text(
        "- pytest failed\n",
        encoding="utf-8",
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
    payload = json.loads(captured.out.strip())

    assert exit_code == 0
    assert payload["status"] == "warning"
    assert payload["warnings"][0]["code"] == "verify_not_ready_for_pr"
    assert not (tmp_path / "docs/generated/pr-summary").exists()
    assert [item["stage"] for item in payload["meta"]["agent_runs"]] == [
        "check",
        "requirements",
        "plan",
        "implement",
        "verify",
    ]
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


def test_run_agents_generates_fallback_verification_block_when_summary_is_missing(
    tmp_path: Path, capsys
) -> None:
    """PASS 但缺少 verification summary 时，PR 摘要应带 fallback 文案。"""

    exit_code = main(["-p", str(tmp_path), "init"])
    captured = capsys.readouterr()
    assert exit_code == 0
    write_provider_config(tmp_path, default_provider="claude")
    spec_file, plan_file = create_run_agents_inputs(tmp_path)

    verify_dir = tmp_path / ".claude/tmp"
    verify_dir.mkdir(parents=True, exist_ok=True)
    (verify_dir / "last-verify.status").write_text("PASS\n", encoding="utf-8")

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
    payload = json.loads(captured.out.strip())

    assert exit_code == 0
    assert payload["status"] == "success"
    pr_summary_path = Path(payload["artifacts"][0]["path"])
    content = pr_summary_path.read_text(encoding="utf-8")
    assert "验证摘要文件存在但为空，请人工补充。" in content
    stage_contracts = assert_stage_contracts_shape(
        payload,
        expected_stages=["check", "requirements", "plan", "implement", "verify", "pr-summary"],
    )
    check_contract = find_stage_contract(stage_contracts, "check")
    verify_contract = find_stage_contract(stage_contracts, "verify")
    pr_summary_contract = find_stage_contract(stage_contracts, "pr-summary")
    assert check_contract["status"] == "success"
    assert verify_contract["status"] == "success"
    assert stage_uses_fallback(verify_contract)
    assert stage_uses_fallback(pr_summary_contract)


def test_run_agents_avoids_overwriting_existing_pr_summary_file(
    tmp_path: Path, capsys
) -> None:
    """PR 摘要目标冲突时，应自动生成新的可用文件名。"""

    exit_code = main(["-p", str(tmp_path), "init"])
    captured = capsys.readouterr()
    assert exit_code == 0
    write_provider_config(tmp_path, default_provider="copilot")
    spec_file, plan_file = create_run_agents_inputs(tmp_path)

    verify_dir = tmp_path / ".claude/tmp"
    verify_dir.mkdir(parents=True, exist_ok=True)
    (verify_dir / "last-verify.status").write_text("PASS\n", encoding="utf-8")
    (verify_dir / "verification-summary.md").write_text(
        "- pytest all passed\n",
        encoding="utf-8",
    )

    existing_path = tmp_path / "docs/generated/pr-summary/2026-04-07T00-00-00.000000Z-pr-summary.md"
    existing_path.parent.mkdir(parents=True, exist_ok=True)
    existing_path.write_text("# existing summary\n", encoding="utf-8")

    with patch(
        "harness_commander.application.commands.utc_timestamp_precise",
        return_value="2026-04-07T00:00:00.000000Z",
    ):
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
    payload = json.loads(captured.out.strip())

    assert exit_code == 0
    assert payload["status"] == "success"
    new_path = Path(payload["artifacts"][0]["path"])
    assert new_path != existing_path
    assert new_path.exists()
    assert existing_path.read_text(encoding="utf-8") == "# existing summary\n"
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
    assert not stage_uses_fallback(pr_summary_contract)
    assert pr_summary_contract["artifacts"]


def test_check_reports_ready_governance_entry_integration(
    tmp_path: Path, capsys
) -> None:
    """integration 场景下无阻断且无提醒时，应返回 ready 治理入口。"""

    exit_code = main(["-p", str(tmp_path), "init"])
    captured = capsys.readouterr()
    assert exit_code == 0

    quantifiable_docs = {
        "docs/QUALITY_SCORE.md": "# QUALITY_SCORE\n\n- 每次改动都要补成功、失败与边界测试。\n",
        "docs/SECURITY.md": "# SECURITY\n\n- 禁止提交明文凭据。\n",
        "docs/design-docs/core-beliefs.md": "# beliefs\n\n- 优先复用既有封装。\n",
        "docs/product-specs/v1/index.md": "# spec v1 index\n\n- `run-agents` 是默认执行入口。\n",
    }
    for relative_path, content in quantifiable_docs.items():
        path = tmp_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    active_plan = tmp_path / "docs/exec-plans/active/demo.md"
    active_plan.parent.mkdir(parents=True, exist_ok=True)
    active_plan.write_text("# demo plan\n", encoding="utf-8")

    reference_file = tmp_path / "docs/references/demo-llms.txt"
    reference_file.parent.mkdir(parents=True, exist_ok=True)
    reference_file.write_text("reference\n", encoding="utf-8")

    tests_dir = tmp_path / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)
    (tests_dir / "test_smoke.py").write_text("def test_smoke():\n    assert True\n", encoding="utf-8")

    exit_code = main(["-p", str(tmp_path), "--json", "check"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out.strip())

    assert exit_code == 0
    assert payload["command"] == "check"
    assert payload["status"] == "success"
    assert payload["warnings"] == []
    assert payload["errors"] == []
    assert payload["meta"]["blocking_count"] == 0
    assert payload["meta"]["warning_count"] == 0
    governance_entry = payload["meta"]["governance_entry"]
    assert governance_entry["status"] == "ready"
    assert governance_entry["ready_for_run_agents"] is True
    assert governance_entry["ready_for_clean_pass"] is True
    assert governance_entry["recommended_entrypoint"] == "harness run-agents"
    next_actions = payload["meta"]["next_actions"]
    assert isinstance(next_actions, list)
    assert next_actions
    assert next_actions[0]["code"] == "proceed"
    assert next_actions[0]["recommended_command"] == "harness run-agents"
    checked_targets = payload["meta"]["checked_targets"]
    assert "docs/exec-plans/active/demo.md" in checked_targets["plan_files"]
    assert "docs/references/demo-llms.txt" in checked_targets["generated_files"]


def test_check_reports_unquantified_rule_sources_in_summary(
    tmp_path: Path, capsys
) -> None:
    """check 应报告未量化规则来源并在摘要中提示。"""

    exit_code = main(["-p", str(tmp_path), "init"])
    captured = capsys.readouterr()
    assert exit_code == 0

    (tmp_path / "docs/QUALITY_SCORE.md").write_text(
        "质量说明\n\n暂时只有说明文本。\n",
        encoding="utf-8",
    )
    active_plan = tmp_path / "docs/exec-plans/active/demo.md"
    active_plan.parent.mkdir(parents=True, exist_ok=True)
    active_plan.write_text("# demo plan\n", encoding="utf-8")

    exit_code = main(["-p", str(tmp_path), "--json", "check"])
    captured = capsys.readouterr()
    assert exit_code == 0

    result = json.loads(captured.out.strip())
    assert result["command"] == "check"
    assert result["status"] == "warning"
    assert result["meta"]["unquantified_count"] >= 1
    assert result["meta"]["checks"]["all"]
    assert any(
        item["code"] == "unquantified_rule_source"
        and item["detail"]["source"] == "docs/QUALITY_SCORE.md"
        for item in result["meta"]["checks"]["all"]
    )
    assert "未量化" in result["summary"]
    assert isinstance(result["meta"]["health_score"], int)
    assert 0 <= result["meta"]["health_score"] <= 100
    governance_entry = result["meta"]["governance_entry"]
    assert governance_entry["status"] == "needs_attention"
    assert governance_entry["ready_for_run_agents"] is True
    assert isinstance(governance_entry["recommended_entrypoint"], str)
    assert governance_entry["recommended_entrypoint"]
    next_actions = result["meta"]["next_actions"]
    assert isinstance(next_actions, list)
    assert next_actions
    assert all(isinstance(action, dict) for action in next_actions)
    assert next_actions[0]["code"] == "resolve_warning_issue"
    assert next_actions[-1]["code"] == "proceed_with_attention"
    assert next_actions[-1]["recommended_command"] == "harness run-agents"


def test_check_governance_entry_blocked_for_secret_exposure_integration(
    tmp_path: Path, capsys
) -> None:
    """integration 场景下出现阻断项时，应给出 blocked 入口状态和动作建议。"""

    exit_code = main(["-p", str(tmp_path), "init"])
    captured = capsys.readouterr()
    assert exit_code == 0

    source_file = tmp_path / "src/demo.py"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_text('password = "supersecret"\n', encoding="utf-8")

    exit_code = main(["-p", str(tmp_path), "--json", "check"])
    captured = capsys.readouterr()
    result = json.loads(captured.out.strip())

    assert exit_code == 1
    assert result["command"] == "check"
    assert result["status"] == "failure"
    assert result["meta"]["blocking_count"] >= 1
    assert result["meta"]["checks"]["all"]
    governance_entry = result["meta"]["governance_entry"]
    assert governance_entry["status"] == "blocked"
    assert governance_entry["ready_for_run_agents"] is False
    assert governance_entry["ready_for_clean_pass"] is False
    assert isinstance(governance_entry["recommended_entrypoint"], str)
    assert governance_entry["recommended_entrypoint"]
    next_actions = result["meta"]["next_actions"]
    assert isinstance(next_actions, list)
    assert next_actions
    assert any(
        isinstance(action, dict)
        and isinstance(action.get("summary"), str)
        and action["summary"]
        for action in next_actions
    )


def test_error_handling_and_recovery(tmp_path: Path, capsys) -> None:
    """测试错误处理和恢复机制。"""

    non_existent_path = tmp_path / "non-existent"
    exit_code = main(["-p", str(non_existent_path), "check"])
    captured = capsys.readouterr()
    assert exit_code != 0
    assert "error" in captured.out.lower()

    exit_code = main(["-p", str(tmp_path), "distill", "non-existent-file.md"])
    captured = capsys.readouterr()
    assert exit_code != 0
    assert "error" in captured.out.lower()

    exit_code = main(["-p", str(tmp_path), "init"])
    captured = capsys.readouterr()
    assert exit_code == 0

    exit_code = main(["-p", str(tmp_path), "check"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "[warning] check" in captured.out


def test_template_validation_integration(tmp_path: Path, capsys) -> None:
    """测试模板验证功能的集成。"""

    exit_code = main(["-p", str(tmp_path), "init"])
    captured = capsys.readouterr()
    assert exit_code == 0

    required_templates = [
        "ARCHITECTURE.md",
        "docs/RELIABILITY.md",
        "docs/SECURITY.md",
        "docs/QUALITY_SCORE.md",
        "docs/PLANS.md",
    ]

    for template in required_templates:
        assert (tmp_path / template).exists(), f"必需模板缺失: {template}"
        content = (tmp_path / template).read_text(encoding="utf-8")
        assert content.strip().startswith("# "), f"模板缺少标题: {template}"
        assert "这个文件是做什么的" in content, f"模板缺少用途说明: {template}"
        assert "推荐用法" in content, f"模板缺少推荐用法: {template}"

    exit_code = main(["-p", str(tmp_path), "--json", "check"])
    captured = capsys.readouterr()
    assert exit_code == 0

    result = json.loads(captured.out.strip())
    meta = result.get("meta", {})
    assert meta.get("blocking_count", 0) == 0, f"模板验证失败: {result}"


def test_init_uses_package_templates_even_if_docs_spec_exists(
    tmp_path: Path, capsys
) -> None:
    """即使仓库里存在模板规范文档，init 也应继续使用包内模板资源。"""

    spec_file = tmp_path / "docs/design-docs/init-templates.md"
    spec_file.parent.mkdir(parents=True, exist_ok=True)
    spec_file.write_text(
        "# fake spec\n\n## ARCHITECTURE.md 模板\n```markdown\n# wrong architecture\n```\n",
        encoding="utf-8",
    )

    exit_code = main(["-p", str(tmp_path), "--json", "init"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out.strip())

    assert exit_code == 0
    assert payload["meta"]["template_source"] == "package_resources"
    architecture_content = (tmp_path / "ARCHITECTURE.md").read_text(encoding="utf-8")
    assert "# wrong architecture" not in architecture_content
    assert "用于描述系统的整体架构蓝图" in architecture_content
