"""应用层命令共享能力。"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from harness_commander.domain.models import (
    CommandMessage,
    CommandResult,
    HarnessCommanderError,
    failure_result,
)

LOGGER = logging.getLogger(__name__)


def execute_command(
    command_name: str, handler: Callable[..., CommandResult], **kwargs: Any
) -> CommandResult:
    """统一执行命令并将异常转换为稳定结果。"""

    try:
        return handler(**kwargs)
    except HarnessCommanderError as error:
        LOGGER.error(
            "命令执行失败 command=%s code=%s location=%s detail=%s reason=%s",
            command_name,
            error.code,
            error.location,
            error.detail,
            error.message,
        )
        return failure_result(
            command_name,
            "命令执行失败，请根据错误信息修正输入或补齐缺失资源。",
            error.to_message(),
        )
    except Exception as error:
        LOGGER.exception("命令出现未预期异常 command=%s reason=%s", command_name, error)
        return failure_result(
            command_name,
            "命令执行失败，出现未预期异常。",
            CommandMessage(
                code="unexpected_error",
                message=str(error),
            ),
        )


def relative_location(path: Path, root: Path) -> str:
    """将绝对路径转换为相对仓库根目录的可读位置。"""

    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)
