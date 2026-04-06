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

from harness_commander.application.model_tasks import HostModelError  # noqa: E402
from harness_commander.cli import main  # noqa: E402
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


def test_distill_host_model_mode_uses_structured_output(tmp_path: Path, capsys) -> None:
    """distill 在 host-model 模式下应消费宿主模型结构化结果。"""

    create_minimal_repo(tmp_path)
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
    ):
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
    assert payload["meta"]["model_provider"] == "claude-cli"
    target_path = Path(payload["meta"]["target_path"])
    content = target_path.read_text(encoding="utf-8")
    assert "- 提升新用户完成率" in content
    assert "- 必须引导用户完成邮箱验证" in content
    assert "- 不得跳过风控校验" in content


def test_distill_auto_mode_falls_back_to_heuristic_when_host_model_fails(
    tmp_path: Path, capsys
) -> None:
    """auto 模式在宿主模型失败时应回退到 heuristic。"""

    create_minimal_repo(tmp_path)
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
    checked_targets = payload["meta"]["checked_targets"]
    assert checked_targets["plan_files"] == ["docs/exec-plans/active/demo.md"]
    assert checked_targets["generated_files"] == ["docs/references/demo-llms.txt"]


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
