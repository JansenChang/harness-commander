"""宿主模型任务边界。"""

from __future__ import annotations

from typing import Any

from harness_commander.application.host_providers import run_structured_command

DISTILL_SCHEMA = {
    "type": "object",
    "properties": {
        "goals": {"type": "array", "items": {"type": "string"}},
        "rules": {"type": "array", "items": {"type": "string"}},
        "limits": {"type": "array", "items": {"type": "string"}},
        "prohibitions": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["goals", "rules", "limits", "prohibitions"],
    "additionalProperties": False,
}


class HostModelError(RuntimeError):
    """宿主模型调用失败。"""


def distill_with_host_model(
    *, provider: str, source_name: str, content: str
) -> dict[str, list[str]]:
    """调用宿主工具 CLI 生成四类结构化提炼结果。"""

    prompt = _build_distill_prompt(source_name=source_name, content=content)
    try:
        payload = run_structured_command(
            provider=provider,
            prompt=prompt,
            schema=DISTILL_SCHEMA,
            timeout_seconds=120,
        )
        structured_output = payload["structured_output"]
    except (KeyError, TypeError) as error:
        raise HostModelError("宿主工具 CLI 返回内容无法解析为结构化结果。") from error
    except RuntimeError as error:
        raise HostModelError(str(error)) from error

    normalized = {
        key: _normalize_items(structured_output.get(key, []))
        for key in ("goals", "rules", "limits", "prohibitions")
    }
    if not any(normalized.values()):
        raise HostModelError("宿主模型未返回可用的结构化提炼内容。")
    return normalized


def _build_distill_prompt(*, source_name: str, content: str) -> str:
    """构建 distill 的宿主模型提示词。"""

    return f"""你在为 Harness-Commander 的 distill 命令提炼参考材料。

请只根据输入内容提取四类信息，并严格返回符合给定 JSON schema 的结果：
- goals: 业务目标
- rules: 关键规则
- limits: 边界限制
- prohibitions: 禁止项

要求：
- 不要编造事实
- 提取不到时返回空数组
- 每个条目保持简短、可复用
- 不要输出 schema 之外的字段

源文档名：{source_name}

原文：
{content}
"""


def _normalize_items(items: Any) -> list[str]:
    """清洗宿主模型返回的字符串列表。"""

    if not isinstance(items, list):
        return []

    normalized: list[str] = []
    for item in items:
        if not isinstance(item, str):
            continue
        cleaned = " ".join(item.split()).strip()
        if cleaned and cleaned not in normalized:
            normalized.append(cleaned)
    return normalized
