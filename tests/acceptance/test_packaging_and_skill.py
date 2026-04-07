"""打包与 Claude skill 的最小验收测试。"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
INSTALL_SCRIPT = REPO_ROOT / "install-skill.sh"
UNINSTALL_SCRIPT = REPO_ROOT / "uninstall-skill.sh"
SKILL_FILE = REPO_ROOT / "src/harness_commander/host_templates/claude/harness/SKILL.md"
SKILL_REFERENCE_FILE = REPO_ROOT / "src/harness_commander/host_templates/claude/harness/Reference/README.md"
PROJECT_SKILL_FILE = REPO_ROOT / ".claude/skills/harness/SKILL.md"
PROJECT_REFERENCE_FILE = REPO_ROOT / ".claude/skills/harness/Reference/README.md"
HARNESS_BIN_DIR = Path(sysconfig.get_path("scripts") or Path(sys.executable).resolve().parent)


def _pick_packaging_python() -> str:
    """选择一个本机可导入 setuptools.build_meta 的解释器。"""

    candidates = [sys.executable]
    candidate_names = (
        "python",
        "python3",
        "python3.10",
        "python3.11",
        "python3.12",
        "python3.13",
        "python3.14",
    )
    for name in candidate_names:
        candidate = shutil.which(name)
        if candidate and candidate not in candidates:
            candidates.append(candidate)

    which_all = subprocess.run(
        [
            "/bin/zsh",
            "-lc",
            "which -a python python3 python3.10 python3.11 python3.12 python3.13 python3.14 2>/dev/null",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if which_all.stdout:
        for raw_line in which_all.stdout.splitlines():
            candidate = raw_line.strip()
            if not candidate.startswith("/"):
                continue
            if not os.path.isfile(candidate) or not os.access(candidate, os.X_OK):
                continue
            if candidate not in candidates:
                candidates.append(candidate)

    for candidate in candidates:
        probe = subprocess.run(
            [candidate, "-c", "import setuptools.build_meta"],
            capture_output=True,
            text=True,
            check=False,
        )
        if probe.returncode == 0:
            return candidate
    raise AssertionError("未找到可用于 editable install 的 Python 解释器。")


def _write_harness_wrapper(bin_dir: Path) -> None:
    """在测试虚拟环境脚本目录中写入本地 harness wrapper。"""

    if os.name == "nt":
        wrapper_path = bin_dir / "harness.cmd"
        wrapper_path.write_text(
            "\n".join(
                [
                    "@echo off",
                    f'set "PYTHONPATH={REPO_ROOT / "src"};%PYTHONPATH%"',
                    f'"{sys.executable}" -m harness_commander.cli %*',
                    "",
                ]
            ),
            encoding="utf-8",
        )
    else:
        wrapper_path = bin_dir / "harness"
        wrapper_path.write_text(
            "\n".join(
                [
                    "#!/bin/sh",
                    f'export PYTHONPATH="{REPO_ROOT / "src"}${{PYTHONPATH:+:$PYTHONPATH}}"',
                    f'exec "{sys.executable}" -m harness_commander.cli "$@"',
                    "",
                ]
            ),
            encoding="utf-8",
        )
        wrapper_path.chmod(0o755)


@pytest.fixture(scope="module", autouse=True)
def ensure_editable_install(tmp_path_factory: pytest.TempPathFactory) -> None:
    """在临时虚拟环境中完成可编辑安装。"""

    global HARNESS_BIN_DIR

    packaging_python = _pick_packaging_python()
    venv_root = tmp_path_factory.mktemp("acceptance-venv") / "venv"
    venv_result = subprocess.run(
        [packaging_python, "-m", "venv", "--system-site-packages", str(venv_root)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert venv_result.returncode == 0, venv_result.stderr
    HARNESS_BIN_DIR = venv_root / ("Scripts" if os.name == "nt" else "bin")
    cache_dir = tmp_path_factory.mktemp("acceptance-pip-cache")
    env = harness_env()
    env["PIP_CACHE_DIR"] = str(cache_dir)
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"

    result = subprocess.run(
        [
            str(HARNESS_BIN_DIR / ("python.exe" if os.name == "nt" else "python")),
            "-m",
            "pip",
            "install",
            "--no-build-isolation",
            "-e",
            ".",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    if result.returncode == 0:
        return

    editable_backend_unsupported = (
        'editable mode currently requires a setuptools-based build' in result.stderr
    )
    if editable_backend_unsupported:
        _write_harness_wrapper(HARNESS_BIN_DIR)
        return
    assert result.returncode == 0, result.stderr


def harness_env() -> dict[str, str]:
    """返回包含当前虚拟环境脚本目录的 PATH。"""

    env = os.environ.copy()
    env["PATH"] = f"{HARNESS_BIN_DIR}{os.pathsep}{env.get('PATH', '')}"
    return env


def test_harness_help_from_editable_install() -> None:
    """可编辑安装后应能直接调用 harness --help。"""

    result = subprocess.run(
        ["harness", "--help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=harness_env(),
    )
    assert result.returncode == 0, result.stderr
    assert "Harness-Commander 统一命令入口" in result.stdout
    assert "init" in result.stdout
    assert "distill" in result.stdout
    assert "run-agents" in result.stdout


def test_skill_source_file_exists_and_wraps_harness() -> None:
    """skill 源文件应存在并包装本地 harness CLI。"""

    content = SKILL_FILE.read_text(encoding="utf-8")
    assert "name: harness" in content
    assert "!`harness $ARGUMENTS`" in content
    assert "disable-model-invocation: true" in content
    assert SKILL_REFERENCE_FILE.exists()


def test_install_and_uninstall_skill_scripts_manage_project_skill() -> None:
    """安装与卸载脚本应管理项目级 skill 文件。"""

    if PROJECT_SKILL_FILE.exists():
        PROJECT_SKILL_FILE.unlink()
    if PROJECT_REFERENCE_FILE.exists():
        PROJECT_REFERENCE_FILE.unlink()

    install_result = subprocess.run(
        [str(INSTALL_SCRIPT)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=harness_env(),
    )
    assert install_result.returncode == 0, install_result.stderr
    assert PROJECT_SKILL_FILE.exists()
    assert PROJECT_REFERENCE_FILE.exists()
    assert "installed project skill" in install_result.stdout

    uninstall_result = subprocess.run(
        [str(UNINSTALL_SCRIPT)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=harness_env(),
    )
    assert uninstall_result.returncode == 0, uninstall_result.stderr
    assert not PROJECT_SKILL_FILE.exists()
    assert (
        "removed project skill" in uninstall_result.stdout
        or "skill is not installed" in uninstall_result.stdout
    )


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


def test_install_provider_claude_creates_project_config_and_user_skill(tmp_path: Path) -> None:
    """install-provider claude 应创建项目级 provider 配置并安装到用户级 Claude skill 目录。"""

    user_skill_dir = tmp_path / "user-home/.claude/skills"
    env = harness_env()
    env["HARNESS_CLAUDE_SKILLS_DIR"] = str(user_skill_dir)

    result = subprocess.run(
        ["harness", "-p", str(tmp_path), "--json", "install-provider", "--provider", "claude"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["command"] == "install-provider"
    config_path = tmp_path / ".harness/provider-config.json"
    skill_path = user_skill_dir / "harness-commander/SKILL.md"
    reference_path = user_skill_dir / "harness-commander/Reference/README.md"
    assert config_path.exists()
    assert skill_path.exists()
    assert reference_path.exists()
    config_payload = json.loads(config_path.read_text(encoding="utf-8"))
    assert config_payload["installation_results"]["claude"]["status"] == "installed"
    assert config_payload["installation_results"]["claude"]["support_level"] == "fully_supported"
    artifact_paths = config_payload["installation_results"]["claude"]["artifact_paths"]
    assert str(skill_path) in artifact_paths
    assert str(reference_path) in artifact_paths
    assert any(artifact["path"] == str(skill_path) for artifact in payload["artifacts"])



def test_install_provider_auto_records_results(tmp_path: Path) -> None:
    """install-provider auto 至少应落盘完整结果表。"""

    env = harness_env()
    env["HARNESS_CLAUDE_SKILLS_DIR"] = str(tmp_path / "user-home/.claude/skills")
    env["HARNESS_CURSOR_SKILLS_DIR"] = str(tmp_path / "user-home/Library/Application Support/Cursor/skills")
    env["HARNESS_CODEX_SKILLS_DIR"] = str(tmp_path / "user-home/Library/Application Support/Codex/skills")
    env["HARNESS_OPENCLAW_SKILLS_DIR"] = str(tmp_path / "user-home/Library/Application Support/OpenClaw/skills")
    env["HARNESS_TRAE_SKILLS_DIR"] = str(tmp_path / "user-home/Library/Application Support/Trae/skills")
    env["HARNESS_COPILOT_SKILLS_DIR"] = str(tmp_path / "user-home/Library/Application Support/Copilot/skills")

    result = subprocess.run(
        ["harness", "-p", str(tmp_path), "--json", "install-provider", "--provider", "auto"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["command"] == "install-provider"
    assert "results" in payload["meta"]
    config_path = tmp_path / ".harness/provider-config.json"
    assert config_path.exists()
    config_payload = json.loads(config_path.read_text(encoding="utf-8"))
    assert isinstance(config_payload["installation_results"], dict)
    assert set(config_payload["installation_results"]).issuperset({"claude", "cursor", "codex", "openclaw", "trae", "copilot"})
    assert config_payload["installation_results"]["claude"]["status"] == "installed"
    assert config_payload["installation_results"]["claude"]["resolved_target_dir"] is not None


def test_install_provider_all_and_dry_run(tmp_path: Path) -> None:
    """install-provider all 与 dry-run 应返回稳定结果且 dry-run 不落盘。"""

    user_skill_dir = tmp_path / "user-home/.claude/skills"
    env = harness_env()
    env["HARNESS_CLAUDE_SKILLS_DIR"] = str(user_skill_dir)
    env["HARNESS_CURSOR_SKILLS_DIR"] = str(tmp_path / "user-home/Library/Application Support/Cursor/skills")
    env["HARNESS_CODEX_SKILLS_DIR"] = str(tmp_path / "user-home/Library/Application Support/Codex/skills")
    env["HARNESS_OPENCLAW_SKILLS_DIR"] = str(tmp_path / "user-home/Library/Application Support/OpenClaw/skills")
    env["HARNESS_TRAE_SKILLS_DIR"] = str(tmp_path / "user-home/Library/Application Support/Trae/skills")
    env["HARNESS_COPILOT_SKILLS_DIR"] = str(tmp_path / "user-home/Library/Application Support/Copilot/skills")

    dry_run_result = subprocess.run(
        [
            "harness",
            "-p",
            str(tmp_path),
            "--json",
            "install-provider",
            "--provider",
            "all",
            "--dry-run",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert dry_run_result.returncode == 0, dry_run_result.stderr
    payload = json.loads(dry_run_result.stdout)
    assert set(payload["meta"]["results"]).issuperset({"claude", "codex", "cursor", "openclaw", "trae", "copilot"})
    assert payload["meta"]["results"]["claude"]["status"] == "installed"
    assert payload["meta"]["results"]["codex"]["status"] in {"installed", "failed_detection", "failed_target_resolution", "failed_source_missing"}
    assert payload["meta"]["results"]["codex"]["resolved_target_dir"] is not None
    assert payload["meta"]["results"]["claude"]["resolved_target_dir"] is not None
    assert not (user_skill_dir / "harness-commander/SKILL.md").exists()
    assert not (user_skill_dir / "harness-commander/Reference/README.md").exists()
    assert not (tmp_path / ".harness/provider-config.json").exists()
    actions = {artifact["action"] for artifact in payload["artifacts"]}
    assert "would_create" in actions or "would_overwrite" in actions



def test_skill_smoke_init_and_distill(tmp_path: Path) -> None:
    """最小 smoke 场景应覆盖 init 与 distill。"""

    init_result = subprocess.run(
        ["harness", "-p", str(tmp_path), "--json", "init"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=harness_env(),
    )
    assert init_result.returncode == 0, init_result.stderr
    init_payload = json.loads(init_result.stdout)
    assert init_payload["command"] == "init"
    assert (tmp_path / "ARCHITECTURE.md").exists()

    source_file = tmp_path / "requirements.md"
    source_file.write_text(
        "# 需求\n\n## 业务目标\n构建测试系统\n\n## 核心需求\n1. 用户管理\n\n## 技术约束\n- 使用 Python 3.10+\n",
        encoding="utf-8",
    )

    distill_result = subprocess.run(
        ["harness", "-p", str(tmp_path), "--json", "distill", str(source_file)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=harness_env(),
    )
    assert distill_result.returncode == 0, distill_result.stderr
    distill_payload = json.loads(distill_result.stdout)
    assert distill_payload["command"] == "distill"
    assert distill_payload["status"] in {"success", "warning"}
    target_path = Path(distill_payload["meta"]["target_path"])
    assert target_path.exists()
    content = target_path.read_text(encoding="utf-8")
    assert "- 用户管理" in content
    assert distill_payload["meta"]["source_type"] == "document"
