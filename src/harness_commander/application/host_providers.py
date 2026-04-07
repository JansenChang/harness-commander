"""宿主工具 provider 抽象。"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harness_commander.domain.models import HarnessCommanderError

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
HOST_TEMPLATE_RESOURCE_DIR = PACKAGE_ROOT / "host_templates"


@dataclass(frozen=True, slots=True)
class HostProviderSpec:
    """描述宿主工具 provider 的最小能力。"""

    provider: str
    model_name: str
    cli_command: str
    supports_json_schema: bool = True
    install_support_level: str = "fully_supported"
    detect_commands: tuple[str, ...] = ()
    install_hint: str = "请先完成本地 CLI 安装与认证，再重新执行 install-provider。"
    wrapper_source: str | None = None
    wrapper_file_name: str = "SKILL.md"
    wrapper_kind: str = "skill"
    legacy_project_skill_target: str | None = None
    installer_name: str | None = None
    user_target_kind: str = "skill"


@dataclass(frozen=True, slots=True)
class ResolvedInstallTarget:
    """描述 provider 解析后的安装目标。"""

    provider: str
    host_display_name: str
    target_dir: Path | None
    target_file: Path | None
    target_scope: str
    host_detected: bool
    failure_reason_code: str | None = None
    failure_reason_detail: str | None = None


SUPPORTED_PROVIDERS: tuple[str, ...] = (
    "claude",
    "cursor",
    "codex",
    "openclaw",
    "trae",
    "copilot",
)

INSTALL_TARGETS: tuple[str, ...] = (*SUPPORTED_PROVIDERS, "all", "auto")
INSTALLABLE_PROVIDER_TARGETS: tuple[str, ...] = SUPPORTED_PROVIDERS

_PROVIDER_SPECS: dict[str, HostProviderSpec] = {
    "claude": HostProviderSpec(
        "claude",
        "claude",
        "claude",
        detect_commands=("claude",),
        install_hint="install-provider 默认安装到用户 Claude skills 目录；install-skill.sh 继续保留为项目级兼容入口。",
        wrapper_source="host_templates/claude/harness",
        wrapper_file_name="SKILL.md",
        wrapper_kind="skill",
        legacy_project_skill_target=".claude/skills/harness/SKILL.md",
        installer_name="claude_user_skill",
    ),
    "cursor": HostProviderSpec(
        "cursor",
        "cursor",
        "cursor",
        detect_commands=("cursor",),
        install_hint="install-provider 会尝试安装到 Cursor commands 目录。",
        wrapper_source="host_templates/cursor/harness.md",
        wrapper_file_name="harness.md",
        wrapper_kind="command",
        installer_name="cursor_user_command",
    ),
    "codex": HostProviderSpec(
        "codex",
        "codex",
        "codex",
        detect_commands=("codex",),
        install_hint="install-provider 会尝试安装到 Codex skills 目录。",
        wrapper_source="host_templates/codex/harness",
        wrapper_file_name="SKILL.md",
        wrapper_kind="skill",
        installer_name="codex_user_skill",
    ),
    "openclaw": HostProviderSpec(
        "openclaw",
        "openclaw",
        "openclaw",
        detect_commands=("openclaw",),
        install_hint="install-provider 会尝试安装到 OpenClaw skills 目录。",
        wrapper_source="host_templates/openclaw/harness",
        wrapper_file_name="SKILL.md",
        wrapper_kind="skill",
        installer_name="openclaw_user_skill",
    ),
    "trae": HostProviderSpec(
        "trae",
        "trae",
        "trae",
        detect_commands=("trae",),
        install_hint="install-provider 会尝试安装到 Trae skills 目录。",
        wrapper_source="host_templates/trae/harness",
        wrapper_file_name="SKILL.md",
        wrapper_kind="skill",
        installer_name="trae_user_skill",
    ),
    "copilot": HostProviderSpec(
        "copilot",
        "copilot",
        "copilot",
        detect_commands=("copilot", "github-copilot"),
        install_hint="install-provider 会尝试安装到 Copilot skills 目录。",
        wrapper_source="host_templates/copilot/harness",
        wrapper_file_name="SKILL.md",
        wrapper_kind="skill",
        installer_name="copilot_user_skill",
    ),
}


def normalize_provider(provider: str) -> str:
    """规范化 provider 名称。"""

    normalized = provider.strip().lower()
    aliases = {
        "claude-cli": "claude",
        "github-copilot": "copilot",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized not in _PROVIDER_SPECS:
        raise HarnessCommanderError(
            code="unsupported_provider",
            message=f"不支持的宿主工具 provider：{provider}",
            location="provider",
            detail={"provider": provider, "supported": list(SUPPORTED_PROVIDERS)},
        )
    return normalized


def normalize_install_target(provider: str) -> str:
    """规范化 install-provider 的目标值。"""

    normalized = provider.strip().lower()
    aliases = {
        "claude-cli": "claude",
        "github-copilot": "copilot",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized not in INSTALL_TARGETS:
        raise HarnessCommanderError(
            code="unsupported_install_target",
            message=f"不支持的 provider 安装目标：{provider}",
            location="provider",
            detail={"provider": provider, "supported": list(INSTALL_TARGETS)},
        )
    return normalized


def get_provider_spec(provider: str) -> HostProviderSpec:
    """获取 provider 规格。"""

    return _PROVIDER_SPECS[normalize_provider(provider)]


def provider_meta(provider: str) -> tuple[str, str]:
    """返回统一的 provider 元信息。"""

    spec = get_provider_spec(provider)
    return f"{spec.provider}-cli", spec.model_name


def provider_wrapper_source_path(root: Path, provider: str) -> Path | None:
    """返回 provider 的 wrapper 源路径。"""

    spec = get_provider_spec(provider)
    if not spec.wrapper_source:
        return None
    del root
    return PACKAGE_ROOT / spec.wrapper_source


def provider_project_skill_paths(root: Path, provider: str) -> tuple[Path, Path] | None:
    """返回 provider 的 legacy 项目级 skill 源文件与目标文件路径。"""

    spec = get_provider_spec(provider)
    if not spec.wrapper_source or not spec.legacy_project_skill_target:
        return None
    return PACKAGE_ROOT / spec.wrapper_source, root / spec.legacy_project_skill_target


def resolve_provider_install_target(
    provider: str,
    *,
    scope: str = "user",
    root: Path | None = None,
    env: dict[str, str] | None = None,
) -> ResolvedInstallTarget:
    """解析 provider 的安装目标。"""

    normalized = normalize_provider(provider)
    env_map = env or os.environ
    host_detected = _detect_host_environment(normalized, env_map)
    target_dir = _resolve_provider_target_dir(normalized, env_map, scope=scope, root=root)
    if target_dir is None:
        return ResolvedInstallTarget(
            provider=normalized,
            host_display_name=normalized,
            target_dir=None,
            target_file=None,
            target_scope=scope,
            host_detected=host_detected,
            failure_reason_code="target_dir_unresolved",
            failure_reason_detail=f"未能解析 {normalized} 的{scope}级安装目录。",
        )
    spec = get_provider_spec(normalized)
    if spec.wrapper_kind == "skill" and scope == "user":
        target_dir = target_dir / "harness-commander"
    target_file = target_dir / spec.wrapper_file_name
    return ResolvedInstallTarget(
        provider=normalized,
        host_display_name=normalized,
        target_dir=target_dir,
        target_file=target_file,
        target_scope=scope,
        host_detected=host_detected,
    )


def _detect_host_environment(provider: str, env: dict[str, str]) -> bool:
    override_key = f"HARNESS_{provider.upper()}_HOST_DETECTED"
    value = env.get(override_key)
    if value is not None:
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return True


def _resolve_provider_target_dir(
    provider: str,
    env: dict[str, str],
    *,
    scope: str,
    root: Path | None,
) -> Path | None:
    if scope == "project":
        return _resolve_project_target_dir(provider, root)

    override = env.get(f"HARNESS_{provider.upper()}_SKILLS_DIR")
    if override and override.strip():
        return Path(override).expanduser()

    home = _resolve_home_directory(env)
    if home is None:
        return None

    if sys.platform == "darwin":
        dotdir_suffixes = {
            "claude": Path(".claude/skills"),
            "codex": Path(".codex/skills"),
            "openclaw": Path(".openclaw/skills"),
            "trae": Path(".trae/skills"),
            "copilot": Path(".copilot/skills"),
        }
        if provider in dotdir_suffixes:
            return home / dotdir_suffixes[provider]
        base = home / "Library/Application Support"
        suffixes = {
            "cursor": Path("Cursor/commands"),
        }
        return base / suffixes[provider]

    if sys.platform.startswith("win"):
        appdata = env.get("APPDATA") or env.get("LOCALAPPDATA")
        if not appdata:
            return None
        base = Path(appdata)
        suffixes = {
            "claude": Path("Claude/skills"),
            "cursor": Path("Cursor/commands"),
            "codex": Path("Codex/skills"),
            "openclaw": Path("OpenClaw/skills"),
            "trae": Path("Trae/skills"),
            "copilot": Path("Copilot/skills"),
        }
        return base / suffixes[provider]

    suffixes = {
        "claude": Path(".claude/skills"),
        "cursor": Path(".cursor/commands"),
        "codex": Path(".codex/skills"),
        "openclaw": Path(".openclaw/skills"),
        "trae": Path(".trae/skills"),
        "copilot": Path(".copilot/skills"),
    }
    return home / suffixes[provider]


def _resolve_project_target_dir(provider: str, root: Path | None) -> Path | None:
    if root is None:
        return None
    suffixes = {
        "claude": Path(".claude/skills/harness"),
        "cursor": Path(".cursor/commands"),
        "codex": Path(".codex/skills/harness"),
        "openclaw": Path(".openclaw/skills/harness"),
        "trae": Path(".trae/skills/harness"),
        "copilot": Path(".copilot/skills/harness"),
    }
    return root / suffixes[provider]


def _resolve_home_directory(env: dict[str, str]) -> Path | None:
    override = env.get("HARNESS_PROVIDER_HOME")
    if override and override.strip():
        return Path(override).expanduser()
    home = env.get("HOME")
    if home and home.strip():
        return Path(home).expanduser()
    return None


def build_structured_command(*, provider: str, prompt: str, schema: dict[str, Any]) -> list[str]:
    """构造结构化宿主模型命令。"""

    spec = get_provider_spec(provider)
    if not spec.supports_json_schema:
        raise HarnessCommanderError(
            code="provider_schema_unsupported",
            message=f"provider 暂不支持 JSON schema 输出：{provider}",
            location="provider",
            detail={"provider": provider},
        )
    return [
        spec.cli_command,
        "-p",
        "--output-format",
        "json",
        "--json-schema",
        json.dumps(schema, ensure_ascii=False),
        prompt,
    ]


def run_structured_command(
    *, provider: str, prompt: str, schema: dict[str, Any], timeout_seconds: int = 120
) -> dict[str, Any]:
    """执行结构化 provider 命令并返回 JSON。"""

    command = build_structured_command(provider=provider, prompt=prompt, schema=schema)
    spec = get_provider_spec(provider)
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )
    except OSError as error:
        raise RuntimeError(f"无法调用 {spec.cli_command} CLI：{error}") from error
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(f"{spec.cli_command} CLI 调用超时。") from error

    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip() or "unknown error"
        raise RuntimeError(f"{spec.cli_command} CLI 返回非零退出码：{stderr}")

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"{spec.cli_command} CLI 返回内容无法解析为 JSON。") from error
    if not isinstance(payload, dict):
        raise RuntimeError(f"{spec.cli_command} CLI 返回内容不是 JSON object。")
    return dict(payload)
