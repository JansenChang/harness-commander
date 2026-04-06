"""文件系统基础设施能力。

该模块负责目录创建、文件写入、文件名生成和 JSON 落盘等能力，
让应用层只表达业务意图，不直接处理底层文件细节。
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from harness_commander.domain.models import CommandArtifact, HarnessCommanderError


def slugify(value: str, *, fallback: str = "task") -> str:
    """将任意输入转换为适合作为文件名的短 slug。"""

    normalized = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", "-", value.strip().lower())
    normalized = normalized.strip("-")
    return normalized[:48] or fallback


def ensure_directory(path: Path, *, dry_run: bool) -> CommandArtifact:
    """确保目录存在，并返回描述本次动作的产物对象。"""

    if path.exists():
        return CommandArtifact(
            path=str(path),
            kind="directory",
            action="skipped",
            note="目录已存在",
        )
    if dry_run:
        return CommandArtifact(
            path=str(path),
            kind="directory",
            action="would_create",
            note="dry-run 未实际创建目录",
        )
    path.mkdir(parents=True, exist_ok=True)
    return CommandArtifact(
        path=str(path),
        kind="directory",
        action="created",
        note="目录创建成功",
    )


def normalize_text_content(content: str) -> str:
    """规范化文本内容，统一使用 LF 结尾。"""

    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    return normalized



def write_text(
    path: Path, content: str, *, dry_run: bool, overwrite: bool = False
) -> CommandArtifact:
    """按安全策略写入文本文件。

    默认禁止覆盖已有文件，避免静默改写现有资产。
    """

    existed_before_write = path.exists()
    if existed_before_write and not overwrite:
        raise HarnessCommanderError(
            "file_conflict",
            "目标文件已存在，已停止写入以避免静默覆盖",
            location=str(path),
        )
    if dry_run:
        action = "would_overwrite" if existed_before_write else "would_create"
        return CommandArtifact(
            path=str(path),
            kind="file",
            action=action,
            note="dry-run 未实际写入文件",
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(normalize_text_content(content), encoding="utf-8", newline="\n")
    return CommandArtifact(
        path=str(path),
        kind="file",
        action="overwritten" if existed_before_write and overwrite else "created",
        note="文件写入成功",
    )


def ensure_text_file(path: Path, content: str, *, dry_run: bool) -> CommandArtifact:
    """确保文本文件存在。

    当文件已存在时直接跳过并返回跳过产物；
    当文件不存在时按照非覆盖策略创建新文件。
    """

    if path.exists():
        return CommandArtifact(
            path=str(path),
            kind="file",
            action="skipped",
            note="文件已存在，保持原内容不变",
        )
    return write_text(path, content, dry_run=dry_run, overwrite=False)


def write_json(
    path: Path, payload: dict[str, Any], *, dry_run: bool
) -> CommandArtifact:
    """将字典以格式化 JSON 方式写入磁盘。"""

    content = json.dumps(payload, ensure_ascii=False, indent=2)
    return write_text(path, content + "\n", dry_run=dry_run, overwrite=False)


def next_available_path(path: Path) -> Path:
    """生成一个当前目录下不冲突的文件路径。"""

    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    for index in range(1, 1000):
        candidate = path.with_name(f"{stem}-{index}{suffix}")
        if not candidate.exists():
            return candidate
    raise HarnessCommanderError(
        "path_exhausted",
        "目标目录中文件冲突过多，无法自动生成新的可用文件名",
        location=str(path.parent),
    )


def utc_timestamp() -> str:
    """返回标准 UTC 时间戳，便于跨工具消费。"""

    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )



def utc_timestamp_precise() -> str:
    """返回带微秒精度的 UTC 时间戳。"""

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
