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



def test_run_agents_uses_configured_provider_and_override_integration(
    tmp_path: Path, capsys
) -> None:
    """集成层应验证 run-agents 默认配置与显式 override。"""

    exit_code = main(["-p", str(tmp_path), "init"])
    captured = capsys.readouterr()
    assert exit_code == 0
    write_provider_config(tmp_path, default_provider="cursor")

    v1_index = tmp_path / "docs/product-specs/v1/index.md"
    v1_index.parent.mkdir(parents=True, exist_ok=True)
    v1_index.write_text("# spec v1 index\n", encoding="utf-8")

    spec_file = tmp_path / "docs/product-specs/sample.md"
    spec_file.write_text(
        "# 样例规格\n\n## 业务目标\n- 支持更多 provider\n\n## 核心逻辑\n- 顺序阶段编排\n\n## 验收标准\n- 返回 agent_runs\n",
        encoding="utf-8",
    )
    plan_file = tmp_path / "docs/exec-plans/active/sample.md"
    plan_file.write_text(
        "# 样例计划\n\n## Goal\n- 完成编排\n\n## Context\n- 样例上下文\n\n## Business Logic\n- 顺序执行\n\n## Scope\n- requirements\n\n## Acceptance Criteria\n- 输出阶段摘要\n\n## Exception Handling\n- 验证失败不整理 PR\n\n## Verification\n- 检查验证状态\n\n## References\n- `ARCHITECTURE.md`\n- `docs/PLANS.md`\n- `docs/product-specs/v1/index.md`\n\n## ULW 1: 编排\n\n### 目标\n- 完成执行\n\n### 涉及范围\n- 读取文档\n\n### 验收标准\n- 输出阶段摘要\n",
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
    default_payload = json.loads(captured.out.strip())

    assert exit_code == 0
    assert default_payload["meta"]["provider"] == "cursor"
    assert default_payload["meta"]["provider_source"] == "default_provider"

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

    v1_index = tmp_path / "docs/product-specs/v1/index.md"
    v1_index.parent.mkdir(parents=True, exist_ok=True)
    v1_index.write_text("# spec v1 index\n", encoding="utf-8")

    spec_file = tmp_path / "docs/product-specs/sample.md"
    spec_file.write_text(
        "# 样例规格\n\n## 业务目标\n- 支持更多 provider\n\n## 核心逻辑\n- 顺序阶段编排\n\n## 验收标准\n- 返回 agent_runs\n",
        encoding="utf-8",
    )
    plan_file = tmp_path / "docs/exec-plans/active/sample.md"
    plan_file.write_text(
        "# 样例计划\n\n## Goal\n- 完成编排\n\n## Context\n- 样例上下文\n\n## Business Logic\n- 顺序执行\n\n## Scope\n- requirements\n\n## Acceptance Criteria\n- 输出阶段摘要\n\n## Exception Handling\n- 验证失败不整理 PR\n\n## Verification\n- 检查验证状态\n\n## References\n- `ARCHITECTURE.md`\n- `docs/PLANS.md`\n- `docs/product-specs/v1/index.md`\n\n## ULW 1: 编排\n\n### 目标\n- 完成执行\n\n### 涉及范围\n- 读取文档\n\n### 验收标准\n- 输出阶段摘要\n",
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
