"""宿主模型任务边界。"""

from __future__ import annotations

import json
import subprocess
from typing import Any

DISTILL_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "key_relationships": {"type": "array", "items": {"type": "string"}},
        "reference_units": {"type": "array", "items": {"type": "string"}},
        "agent_guidance": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["summary", "key_relationships", "reference_units", "agent_guidance"],
    "additionalProperties": False,
}


class HostModelError(RuntimeError):
    """宿主模型调用失败。"""


def distill_with_host_model(
    *,
    instruction: str,
    input_descriptions: list[str],
    bundled_content: str,
    interactive: bool,
) -> dict[str, Any]:
    """调用 Claude CLI 生成结构化上下文包。"""

    prompt = _build_distill_prompt(
        instruction=instruction,
        input_descriptions=input_descriptions,
        bundled_content=bundled_content,
        interactive=interactive,
    )
    command = [
        "claude",
        "-p",
        "--output-format",
        "json",
        "--json-schema",
        json.dumps(DISTILL_SCHEMA, ensure_ascii=False),
        prompt,
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
    except OSError as error:
        raise HostModelError(f"无法调用 Claude CLI：{error}") from error
    except subprocess.TimeoutExpired as error:
        raise HostModelError("Claude CLI 调用超时。") from error

    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip() or "unknown error"
        raise HostModelError(f"Claude CLI 返回非零退出码：{stderr}")

    try:
        payload = json.loads(result.stdout)
        structured_output = payload["structured_output"]
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        raise HostModelError("Claude CLI 返回内容无法解析为结构化结果。") from error

    normalized = {
        "summary": _normalize_text(structured_output.get("summary", "")),
        "key_relationships": _normalize_items(structured_output.get("key_relationships", [])),
        "reference_units": _normalize_items(structured_output.get("reference_units", [])),
        "agent_guidance": _normalize_items(structured_output.get("agent_guidance", [])),
    }
    if not normalized["summary"] and not any(
        normalized[key] for key in ("key_relationships", "reference_units", "agent_guidance")
    ):
        raise HostModelError("宿主模型未返回可用的结构化提炼内容。")
    return normalized


def _build_distill_prompt(
    *,
    instruction: str,
    input_descriptions: list[str],
    bundled_content: str,
    interactive: bool,
) -> str:
    """构建 distill 的宿主模型提示词。"""

    interaction_note = "用户允许后续多轮对话收敛格式。" if interactive else "当前先输出一版默认结构化结果。"
    source_list = "\n".join(f"- {item}" for item in input_descriptions)
    return f"""你在为 Harness-Commander 的 distill 命令生成 `.llms` 结构化上下文包。

目标：
- 根据用户说明和输入材料，提炼给下游 LLM / Agent 使用的机器可读上下文。
- 不局限于文档摘要，也可以抽取代码示例、关系说明和使用指引。
- 输出必须严格符合给定 JSON schema。

用户说明：
{instruction}

输入材料：
{source_list}

附加要求：
- summary: 1 段简洁摘要
- key_relationships: 提炼跨文件关系、调用链、依赖关系或关键模式
- reference_units: 提炼最值得保留的代码片段说明、文档精华或参考单元
- agent_guidance: 给下游模型/Agent 的使用建议或生成约束
- 不要编造事实
- 提取不到时返回空字符串或空数组
- 每项保持简短、可复用
- {interaction_note}

输入内容：
{bundled_content}
"""


def _normalize_text(value: Any) -> str:
    """清洗宿主模型返回的单段文本。"""

    if not isinstance(value, str):
        return ""
    return " ".join(value.split()).strip()


def _normalize_items(items: Any) -> list[str]:
    """清洗宿主模型返回的字符串列表。"""

    if not isinstance(items, list):
        return []

    normalized: list[str] = []
    for item in items:
        cleaned = _normalize_text(item)
        if cleaned and cleaned not in normalized:
            normalized.append(cleaned)
    return normalized
