"""命令模块之间共享的轻量辅助能力。"""

from __future__ import annotations

from pathlib import Path


def relative_location(path: Path, root: Path) -> str:
    """将路径转换为相对仓库根目录的稳定显示形式。"""

    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)

