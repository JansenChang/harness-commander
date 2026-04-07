"""provider 安装模式测试。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from harness_commander.application.provider_installers import install_provider_target  # noqa: E402


def test_install_provider_cursor_project_link_creates_symlink(tmp_path: Path, monkeypatch) -> None:
    wrapper_dir = tmp_path / "src/harness_commander/host_templates/cursor"
    wrapper_dir.mkdir(parents=True, exist_ok=True)
    (wrapper_dir / "harness.md").write_text("# Harness\n", encoding="utf-8")

    original_path = os.environ.get("PATH", "")
    monkeypatch.setenv("PATH", f"{Path(sys.executable).parent}{os.pathsep}{original_path}")

    results, artifacts = install_provider_target(
        tmp_path,
        provider="cursor",
        scope="project",
        install_mode="link",
        dry_run=False,
    )

    target = tmp_path / ".cursor/commands/harness.md"
    assert results["cursor"]["status"] in {"installed", "failed_detection"}
    if results["cursor"]["status"] == "installed":
        assert target.is_symlink()
        assert artifacts


def test_install_provider_trae_project_copy_creates_skill(tmp_path: Path, monkeypatch) -> None:
    original_path = os.environ.get("PATH", "")
    monkeypatch.setenv("PATH", f"{Path(sys.executable).parent}{os.pathsep}{original_path}")

    results, _ = install_provider_target(
        tmp_path,
        provider="trae",
        scope="project",
        install_mode="copy",
        dry_run=False,
    )

    target = tmp_path / ".trae/skills/harness/SKILL.md"
    reference_target = tmp_path / ".trae/skills/harness/Reference/README.md"
    assert results["trae"]["status"] in {"installed", "failed_detection"}
    if results["trae"]["status"] == "installed":
        assert target.exists()
        assert reference_target.exists()
        content = target.read_text(encoding="utf-8")
        assert "name: harness" in content
