"""CLI 骨架测试。

该测试文件覆盖第一轮骨架的关键行为：
目录初始化、计划生成、计划校验、证据留存以及 JSON 输出协议。
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

import json  # noqa: E402

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
        "docs/product-specs/harness-commander.md": "# spec\n",
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
    # 根据关键规则16，init不应创建docs/generated/evidence目录
    # 该目录应由collect-evidence命令在需要时创建
    assert (tmp_path / "AGENTS.md").exists()
    assert (tmp_path / "docs/product-specs/index.md").exists()
    assert (tmp_path / "docs/references/uv-llms.txt").exists()
    # 验证白名单目录被创建
    assert (tmp_path / "docs/design-docs").exists()
    assert (tmp_path / "docs/exec-plans/active").exists()
    assert (tmp_path / "docs/exec-plans/completed").exists()
    assert (tmp_path / "docs/product-specs").exists()
    assert (tmp_path / "docs/references").exists()
    # 验证禁止目录未被创建
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
            "collect-evidence",
            "--command",
            "pytest",
            "--exit-code",
            "1",
            "--status",
            "failure",
            "--summary",
            "测试失败",
            "--log",
            "line one",
            "--log",
            "line two",
        ]
    )
    captured = capsys.readouterr()
    evidence_files = list((tmp_path / "docs/generated/evidence").glob("*.json"))
    assert exit_code == 0
    assert "[warning] collect-evidence" in captured.out
    assert len(evidence_files) == 1
    payload = json.loads(evidence_files[0].read_text(encoding="utf-8"))
    assert payload["command"] == "pytest"
    assert payload["exit_code"] == 1
    assert payload["logs"] == ["line one", "line two"]


def test_load_init_templates_falls_back_when_package_resource_is_missing() -> None:
    """包内模板资源缺失时应回退到内置模板并返回 warning。"""

    missing_template = "AGENTS.md"
    original_get_path = docs_infra.get_template_resource_path

    def fake_get_template_resource_path(template_path: str) -> Path:
        if template_path == missing_template:
            return Path("/definitely-missing-init-template.md")
        return original_get_path(template_path)

    docs_infra.get_template_resource_path = fake_get_template_resource_path
    try:
        result = docs_infra.load_init_templates(Path("/tmp/unused-root"))
    finally:
        docs_infra.get_template_resource_path = original_get_path

    assert result.source == "builtin_fallback"
    assert result.templates == docs_infra.INIT_FILE_TEMPLATES
    assert len(result.warnings) == 1
    warning = result.warnings[0]
    assert warning.code == "init_template_fallback"
    assert warning.location == "/definitely-missing-init-template.md"
    assert missing_template in warning.detail["reason"]


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
    issue = payload["errors"][0]
    assert issue["detail"]["severity"] == "blocking"
    assert issue["detail"]["source"] == "docs/SECURITY.md"
    assert issue["location"] == "src/demo.py"
    assert issue["detail"]["suggestion"]


def test_sync_returns_no_artifacts_when_no_major_change(tmp_path: Path, capsys) -> None:
    """sync 在未识别到重大变更时不应生成同步产物。"""

    create_minimal_repo(tmp_path)
    exit_code = main(["-p", str(tmp_path), "--json", "sync", "--dry-run"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["command"] == "sync"
    assert payload["status"] == "success"
    assert payload["meta"]["change_count"] == 0
    assert payload["artifacts"] == []



def test_sync_only_updates_impacted_artifacts(tmp_path: Path, capsys) -> None:
    """sync 只更新被重大变更命中的目标产物。"""

    create_minimal_repo(tmp_path)
    migration_file = tmp_path / "migrations/0001_init.sql"
    migration_file.parent.mkdir(parents=True, exist_ok=True)
    migration_file.write_text("create table demo(id integer primary key);\n", encoding="utf-8")

    exit_code = main(["-p", str(tmp_path), "--json", "sync", "--dry-run"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["meta"]["change_count"] == 1
    assert payload["meta"]["change_types"] == ["database_schema"]
    assert len(payload["artifacts"]) == 1
    artifact = payload["artifacts"][0]
    assert artifact["path"].endswith("docs/generated/db-schema.md")
    assert artifact["action"] == "would_update"
    assert "migrations/0001_init.sql" in artifact["note"]


