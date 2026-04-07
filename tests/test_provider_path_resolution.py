"""provider 用户级目录解析测试。"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from harness_commander.application.host_providers import (  # noqa: E402
    resolve_provider_install_target,
)


def test_resolve_provider_install_target_uses_dotdir_for_claude_on_macos(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("HARNESS_CLAUDE_SKILLS_DIR", raising=False)
    monkeypatch.setenv("HARNESS_PROVIDER_HOME", str(tmp_path / "home"))
    monkeypatch.setattr(sys, "platform", "darwin")

    resolved = resolve_provider_install_target("claude")

    assert resolved.target_dir == tmp_path / "home/.claude/skills/harness-commander"
    assert resolved.target_file == tmp_path / "home/.claude/skills/harness-commander/SKILL.md"
    assert resolved.failure_reason_code is None


def test_resolve_provider_install_target_uses_dotdir_for_codex_on_macos(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("HARNESS_CODEX_SKILLS_DIR", raising=False)
    monkeypatch.setenv("HARNESS_PROVIDER_HOME", str(tmp_path / "home"))
    monkeypatch.setattr(sys, "platform", "darwin")

    resolved = resolve_provider_install_target("codex")

    assert resolved.target_dir == tmp_path / "home/.codex/skills/harness-commander"
    assert resolved.target_file == tmp_path / "home/.codex/skills/harness-commander/SKILL.md"
    assert resolved.failure_reason_code is None


def test_resolve_provider_install_target_uses_dotdir_for_openclaw_on_macos(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("HARNESS_OPENCLAW_SKILLS_DIR", raising=False)
    monkeypatch.setenv("HARNESS_PROVIDER_HOME", str(tmp_path / "home"))
    monkeypatch.setattr(sys, "platform", "darwin")

    resolved = resolve_provider_install_target("openclaw")

    assert resolved.target_dir == tmp_path / "home/.openclaw/skills/harness-commander"
    assert resolved.target_file == tmp_path / "home/.openclaw/skills/harness-commander/SKILL.md"
    assert resolved.failure_reason_code is None


def test_resolve_provider_install_target_uses_dotdir_for_copilot_on_macos(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("HARNESS_COPILOT_SKILLS_DIR", raising=False)
    monkeypatch.setenv("HARNESS_PROVIDER_HOME", str(tmp_path / "home"))
    monkeypatch.setattr(sys, "platform", "darwin")

    resolved = resolve_provider_install_target("copilot")

    assert resolved.target_dir == tmp_path / "home/.copilot/skills/harness-commander"
    assert resolved.target_file == tmp_path / "home/.copilot/skills/harness-commander/SKILL.md"
    assert resolved.failure_reason_code is None


def test_resolve_provider_install_target_uses_dotdir_for_trae_on_macos(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("HARNESS_TRAE_SKILLS_DIR", raising=False)
    monkeypatch.setenv("HARNESS_PROVIDER_HOME", str(tmp_path / "home"))
    monkeypatch.setattr(sys, "platform", "darwin")

    resolved = resolve_provider_install_target("trae")

    assert resolved.target_dir == tmp_path / "home/.trae/skills/harness-commander"
    assert resolved.target_file == tmp_path / "home/.trae/skills/harness-commander/SKILL.md"
    assert resolved.failure_reason_code is None


def test_resolve_provider_install_target_uses_appdata_for_windows(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("HARNESS_TRAE_SKILLS_DIR", raising=False)
    monkeypatch.setenv("APPDATA", str(tmp_path / "AppData/Roaming"))
    monkeypatch.setattr(sys, "platform", "win32")

    resolved = resolve_provider_install_target("trae")

    assert resolved.target_dir == tmp_path / "AppData/Roaming/Trae/skills/harness-commander"
    assert resolved.target_file == tmp_path / "AppData/Roaming/Trae/skills/harness-commander/SKILL.md"
    assert resolved.failure_reason_code is None


def test_resolve_provider_install_target_project_scope_for_cursor(tmp_path: Path) -> None:
    resolved = resolve_provider_install_target("cursor", scope="project", root=tmp_path)

    assert resolved.target_dir == tmp_path / ".cursor/commands"
    assert resolved.target_file == tmp_path / ".cursor/commands/harness.md"
    assert resolved.target_scope == "project"


def test_resolve_provider_install_target_uses_explicit_override(tmp_path: Path, monkeypatch) -> None:
    override_dir = tmp_path / "custom/claude-skills"
    monkeypatch.setenv("HARNESS_CLAUDE_SKILLS_DIR", str(override_dir))

    resolved = resolve_provider_install_target("claude")

    assert resolved.target_dir == override_dir / "harness-commander"
    assert resolved.target_file == override_dir / "harness-commander/SKILL.md"
    assert resolved.target_scope == "user"
    assert resolved.failure_reason_code is None


def test_resolve_provider_install_target_uses_home_override_for_linux(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("HARNESS_CURSOR_SKILLS_DIR", raising=False)
    monkeypatch.setenv("HARNESS_PROVIDER_HOME", str(tmp_path / "home"))
    monkeypatch.setattr(sys, "platform", "linux")

    resolved = resolve_provider_install_target("cursor")

    assert resolved.target_dir == tmp_path / "home/.cursor/commands"
    assert resolved.target_file == tmp_path / "home/.cursor/commands/harness.md"
    assert resolved.failure_reason_code is None
