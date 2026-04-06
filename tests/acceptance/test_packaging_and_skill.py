"""打包与 Claude skill 的最小验收测试。"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
INSTALL_SCRIPT = REPO_ROOT / "install-skill.sh"
UNINSTALL_SCRIPT = REPO_ROOT / "uninstall-skill.sh"
SKILL_FILE = REPO_ROOT / "claude-skills/harness/SKILL.md"
PROJECT_SKILL_FILE = REPO_ROOT / ".claude/skills/harness/SKILL.md"
VENV_BIN = REPO_ROOT / ".venv/bin"


def _test_env() -> dict[str, str]:
    """为验收测试补充当前虚拟环境的 PATH。"""

    env = os.environ.copy()
    env["PATH"] = str(VENV_BIN) + os.pathsep + env.get("PATH", "")
    return env



def _harness_command() -> list[str]:
    """优先使用已安装 harness，否则退回源码入口。"""

    harness_bin = VENV_BIN / "harness"
    if harness_bin.exists():
        return [str(harness_bin)]
    if shutil.which("harness"):
        return ["harness"]
    return [sys.executable, "-m", "harness_commander.cli"]


def test_harness_help_from_editable_install() -> None:
    """可编辑安装后应能直接调用 harness --help。"""

    result = subprocess.run(
        ["harness", "--help"],
        cwd=REPO_ROOT,
        env=_test_env(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "Harness-Commander 统一命令入口" in result.stdout
    assert "init" in result.stdout
    assert "distill" in result.stdout


def test_skill_source_file_exists_and_wraps_harness() -> None:
    """skill 源文件应存在并包装本地 harness CLI。"""

    content = SKILL_FILE.read_text(encoding="utf-8")
    assert "name: harness" in content
    assert "!`harness $ARGUMENTS`" in content
    assert "disable-model-invocation: true" in content


def test_install_and_uninstall_skill_scripts_manage_project_skill() -> None:
    """安装与卸载脚本应管理项目级 skill 文件。"""

    if PROJECT_SKILL_FILE.exists():
        PROJECT_SKILL_FILE.unlink()

    install_result = subprocess.run(
        [str(INSTALL_SCRIPT)],
        cwd=REPO_ROOT,
        env=_test_env(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert install_result.returncode == 0, install_result.stderr
    assert PROJECT_SKILL_FILE.exists()
    assert "installed project skill" in install_result.stdout
    assert "/harness init -p /tmp/harness-skill-smoke" in install_result.stdout
    assert "--json /tmp/harness-skill-smoke/requirements.md \"整理为 llms 上下文包\"" in install_result.stdout

    uninstall_result = subprocess.run(
        [str(UNINSTALL_SCRIPT)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert uninstall_result.returncode == 0, uninstall_result.stderr
    assert not PROJECT_SKILL_FILE.exists()
    assert "removed project skill" in uninstall_result.stdout


def test_install_skill_reports_missing_harness_command() -> None:
    """当 harness 不在 PATH 中时，安装脚本应给出清晰错误。"""

    result = subprocess.run(
        [str(INSTALL_SCRIPT)],
        cwd=REPO_ROOT,
        env={"PATH": os.defpath},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "harness command not found" in result.stderr


def _write_distill_source_file(base_dir: Path) -> Path:
    source_file = base_dir / "requirements.md"
    source_file.write_text(
        "# 需求\n\n## 业务目标\n构建测试系统\n\n## 核心需求\n1. 用户管理\n\n## 技术约束\n- 使用 Python 3.10+\n",
        encoding="utf-8",
    )
    return source_file



def test_skill_smoke_init_and_distill(tmp_path: Path) -> None:
    """最小 smoke 场景应覆盖 init 与 distill。"""

    init_result = subprocess.run(
        [*_harness_command(), "-p", str(tmp_path), "--json", "init"],
        cwd=REPO_ROOT,
        env=_test_env(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert init_result.returncode == 0, init_result.stderr
    init_payload = json.loads(init_result.stdout)
    assert init_payload["command"] == "init"
    assert (tmp_path / "ARCHITECTURE.md").exists()

    source_file = _write_distill_source_file(tmp_path)

    distill_result = subprocess.run(
        [
            *_harness_command(),
            "-p",
            str(tmp_path),
            "--json",
            "distill",
            str(source_file),
            "整理需求文档为 llms 上下文包",
        ],
        cwd=REPO_ROOT,
        env=_test_env(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert distill_result.returncode == 0, distill_result.stderr
    distill_payload = json.loads(distill_result.stdout)
    assert distill_payload["command"] == "distill"
    assert distill_payload["status"] in {"success", "warning"}
    target_path = Path(distill_payload["meta"]["output_path"])
    assert target_path.exists()
    content = target_path.read_text(encoding="utf-8")
    assert "## Distilled Summary" in content
    assert distill_payload["meta"]["source_types"] == ["document"]



def test_real_claude_distill_writes_llms_file(tmp_path: Path) -> None:
    """启用门控后应可通过真实 Claude 宿主调用生成 llms 文件。"""

    if os.environ.get("HARNESS_RUN_CLAUDE_E2E") != "1":
        pytest.skip("set HARNESS_RUN_CLAUDE_E2E=1 to run real Claude distill e2e")
    if shutil.which("claude") is None:
        pytest.skip("claude command is not available in PATH")

    source_file = _write_distill_source_file(tmp_path)
    expected_output = tmp_path / ".llms" / "requirements.llms"

    distill_result = subprocess.run(
        [
            *_harness_command(),
            "-p",
            str(tmp_path),
            "--json",
            "distill",
            str(source_file),
            "整理为 llms 上下文包",
        ],
        cwd=REPO_ROOT,
        env=_test_env(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert distill_result.returncode == 0, distill_result.stderr
    distill_payload = json.loads(distill_result.stdout)
    assert distill_payload["command"] == "distill"
    assert distill_payload["status"] in {"success", "warning"}
    assert Path(distill_payload["meta"]["output_path"]) == expected_output
    assert expected_output.exists()
    content = expected_output.read_text(encoding="utf-8")
    assert "## Distilled Summary" in content
    assert "## Key Relationships" in content
    assert "## Reference Units" in content
    assert "## Agent Guidance" in content
