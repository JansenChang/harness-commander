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

from harness_commander.cli import main  # noqa: E402


def test_full_workflow_with_dry_run(tmp_path: Path, capsys) -> None:
    """测试完整工作流程（使用 dry-run 模式）。"""

    # 1. 初始化项目
    exit_code = main(["-p", str(tmp_path), "init"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "[success] init" in captured.out

    # 验证初始化创建的文件
    assert (tmp_path / "ARCHITECTURE.md").exists()
    assert (tmp_path / "docs/PLANS.md").exists()
    assert (tmp_path / "docs/RELIABILITY.md").exists()
    assert (tmp_path / "docs/SECURITY.md").exists()
    assert (tmp_path / "docs/QUALITY_SCORE.md").exists()
    assert (tmp_path / "docs/product-specs/index.md").exists()
    assert (tmp_path / "docs/references/uv-llms.txt").exists()

    # 2. 创建测试文档用于 distill 命令
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

    # 3. 运行 distill 命令（dry-run）
    exit_code = main(["-p", str(tmp_path), "distill", str(test_doc), "--dry-run"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "[success] distill" in captured.out
    assert "dry-run" in captured.out.lower()

    # 4. 运行 check 命令（dry-run）
    exit_code = main(["-p", str(tmp_path), "check", "--dry-run"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "[warning] check" in captured.out

    # 5. 运行 sync 命令（dry-run）
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
    """测试所有命令的 JSON 输出格式一致性。"""

    # 初始化项目
    exit_code = main(["-p", str(tmp_path), "init"])
    captured = capsys.readouterr()
    assert exit_code == 0

    migration_file = tmp_path / "migrations/0001_init.sql"
    migration_file.parent.mkdir(parents=True, exist_ok=True)
    migration_file.write_text("create table audit(id integer primary key);\n", encoding="utf-8")

    # 测试每个命令的 JSON 输出
    commands_to_test = [
        ["--json", "check"],
        ["--json", "sync", "--dry-run"],
    ]

    for command_args in commands_to_test:
        exit_code = main(["-p", str(tmp_path), *command_args])
        captured = capsys.readouterr()
        assert exit_code == 0

        # 验证 JSON 输出格式
        try:
            result = json.loads(captured.out.strip())
            assert "command" in result
            assert "status" in result
            assert "summary" in result
            assert isinstance(result.get("artifacts", []), list)
            assert isinstance(result.get("warnings", []), list)
            assert isinstance(result.get("meta", {}), dict)
        except json.JSONDecodeError as err:
            raise AssertionError(
                f"命令 {command_args[0]} 的输出不是有效的 JSON"
            ) from err


def test_command_chaining(tmp_path: Path, capsys) -> None:
    """测试命令链式执行（一个命令的输出作为另一个命令的输入）。"""

    # 初始化项目
    exit_code = main(["-p", str(tmp_path), "init"])
    captured = capsys.readouterr()
    assert exit_code == 0

    # 创建测试文档
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

    # 运行 distill 命令并获取 JSON 输出
    exit_code = main(["-p", str(tmp_path), "--json", "distill", str(test_doc)])
    captured = capsys.readouterr()
    assert exit_code == 0

    # 解析 distill 输出
    distill_result = json.loads(captured.out.strip())
    assert distill_result["command"] == "distill"
    assert distill_result["status"] == "success"

    # 验证 distill 生成了 artifacts
    artifacts = distill_result.get("artifacts", [])
    assert len(artifacts) > 0

    sync_exit_code = main(["-p", str(tmp_path), "--json", "sync"])
    sync_captured = capsys.readouterr()
    assert sync_exit_code == 0
    sync_result = json.loads(sync_captured.out.strip())
    assert sync_result["command"] == "sync"
    assert sync_result["status"] == "success"
    assert sync_result["meta"]["change_count"] == 1
    assert sync_result["artifacts"][0]["path"].endswith("docs/generated/db-schema.md")

    # 运行 check 命令验证项目状态
    exit_code = main(["-p", str(tmp_path), "--json", "check"])
    captured = capsys.readouterr()
    assert exit_code == 0

    check_result = json.loads(captured.out.strip())
    assert check_result["command"] == "check"
    assert check_result["status"] == "warning"

    meta = check_result.get("meta", {})
    assert meta.get("blocking_count", 0) == 0
    assert meta.get("warning_count", 0) >= 1
    assert any(
        warning["detail"]["severity"] == "warning"
        for warning in check_result.get("warnings", [])
    )


def test_check_reports_unquantified_rule_sources_in_summary(
    tmp_path: Path, capsys
) -> None:
    """check 应在摘要和元信息中体现未量化规则源。"""

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

    # 在不存在的路径上运行命令
    non_existent_path = tmp_path / "non-existent"
    exit_code = main(["-p", str(non_existent_path), "check"])
    captured = capsys.readouterr()
    assert exit_code != 0
    assert "error" in captured.out.lower()

    # 使用无效参数运行命令
    exit_code = main(["-p", str(tmp_path), "distill", "non-existent-file.md"])
    captured = capsys.readouterr()
    assert exit_code != 0
    assert "error" in captured.out.lower()

    # 初始化项目后再次运行 check 命令应该成功
    exit_code = main(["-p", str(tmp_path), "init"])
    captured = capsys.readouterr()
    assert exit_code == 0

    exit_code = main(["-p", str(tmp_path), "check"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "[warning] check" in captured.out


def test_template_validation_integration(tmp_path: Path, capsys) -> None:
    """测试模板验证功能的集成。"""

    # 初始化项目
    exit_code = main(["-p", str(tmp_path), "init"])
    captured = capsys.readouterr()
    assert exit_code == 0

    # 验证所有必需模板都已创建
    required_templates = [
        "ARCHITECTURE.md",
        "docs/RELIABILITY.md",
        "docs/SECURITY.md",
        "docs/QUALITY_SCORE.md",
        "docs/PLANS.md",
    ]

    for template in required_templates:
        assert (tmp_path / template).exists(), f"必需模板缺失: {template}"

        # 验证模板内容包含必需部分
        content = (tmp_path / template).read_text(encoding="utf-8")
        assert content.strip().startswith("# "), f"模板缺少标题: {template}"
        assert "这个文件是做什么的" in content, f"模板缺少用途说明: {template}"
        assert "推荐用法" in content, f"模板缺少推荐用法: {template}"

    # 运行 check 命令验证模板结构
    exit_code = main(["-p", str(tmp_path), "--json", "check"])
    captured = capsys.readouterr()
    assert exit_code == 0

    result = json.loads(captured.out.strip())
    meta = result.get("meta", {})
    assert meta.get("error_count", 0) == 0, f"模板验证失败: {result}"


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
