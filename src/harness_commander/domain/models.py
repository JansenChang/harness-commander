"""领域层核心模型。

该模块只负责定义 Harness-Commander 在命令执行过程中的稳定数据结构，
避免 CLI、应用服务和基础设施层各自拼装字典，导致协议不一致。
所有命令最终都需要落到统一结果对象，既能输出给人阅读，也能序列化为 JSON。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ResultStatus(str, Enum):
    """统一命令状态枚举。"""

    SUCCESS = "success"
    WARNING = "warning"
    FAILURE = "failure"


@dataclass(slots=True)
class CommandMessage:
    """通用消息对象。

    该对象用于承载 warning 和 error。
    code 用于机器判断，message 用于面向人类展示，detail 用于补充上下文。
    """

    code: str
    message: str
    location: str | None = None
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """将消息对象转换为可序列化字典。"""

        return {
            "code": self.code,
            "message": self.message,
            "location": self.location,
            "detail": self.detail,
        }


@dataclass(slots=True)
class CommandArtifact:
    """命令产物描述。

    产物既可能是实际落盘文件，也可能是 dry-run 下的预期变更。
    """

    path: str
    kind: str
    action: str
    note: str = ""

    def to_dict(self) -> dict[str, str]:
        """将产物对象转换为可序列化字典。"""

        return {
            "path": self.path,
            "kind": self.kind,
            "action": self.action,
            "note": self.note,
        }


@dataclass(slots=True)
class CommandResult:
    """统一命令结果。

    这是 CLI 对外暴露的唯一结果协议，确保文本输出与 JSON 输出共享同一份事实。
    """

    command: str
    status: ResultStatus
    summary: str
    artifacts: list[CommandArtifact] = field(default_factory=list)
    warnings: list[CommandMessage] = field(default_factory=list)
    errors: list[CommandMessage] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def exit_code(self) -> int:
        """根据状态计算退出码。"""

        return 0 if self.status in {ResultStatus.SUCCESS, ResultStatus.WARNING} else 1

    def to_dict(self) -> dict[str, Any]:
        """序列化统一结果对象。"""

        return {
            "command": self.command,
            "status": self.status.value,
            "summary": self.summary,
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
            "warnings": [warning.to_dict() for warning in self.warnings],
            "errors": [error.to_dict() for error in self.errors],
            "meta": self.meta,
        }

    def to_text(self) -> str:
        """将结果渲染为简洁的人类可读摘要。"""

        lines = [f"[{self.status.value}] {self.command}", self.summary]
        if self.artifacts:
            lines.append("artifacts:")
            lines.extend(
                f"- {artifact.action} {artifact.kind}: {artifact.path}"
                + (f" ({artifact.note})" if artifact.note else "")
                for artifact in self.artifacts
            )
        if self.warnings:
            lines.append("warnings:")
            lines.extend(
                f"- {warning.code}: {warning.message}"
                + (f" @ {warning.location}" if warning.location else "")
                for warning in self.warnings
            )
        if self.errors:
            lines.append("errors:")
            lines.extend(
                f"- {error.code}: {error.message}"
                + (f" @ {error.location}" if error.location else "")
                for error in self.errors
            )
        return "\n".join(lines)


class HarnessCommanderError(Exception):
    """领域层基础异常。

    应用层可以捕获该异常并安全地转换为统一结果，
    避免把原始堆栈直接暴露给最终用户。
    """

    def __init__(
        self,
        code: str,
        message: str,
        *,
        location: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.location = location
        self.detail = detail or {}

    def to_message(self) -> CommandMessage:
        """将异常转换为错误消息对象。"""

        return CommandMessage(
            code=self.code,
            message=self.message,
            location=self.location,
            detail=self.detail,
        )


def failure_result(command: str, summary: str, error: CommandMessage) -> CommandResult:
    """快速构造失败结果，减少重复样板代码。"""

    return CommandResult(
        command=command,
        status=ResultStatus.FAILURE,
        summary=summary,
        errors=[error],
    )
