"""文档基础设施能力。

该模块负责治理文档存在性检查、计划模板渲染和计划校验，
确保所有命令都围绕仓库中的正式文档约束展开，而不是凭空猜测。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from harness_commander.domain.models import CommandMessage, HarnessCommanderError
from harness_commander.infrastructure.filesystem import (
    next_available_path,
    slugify,
    utc_timestamp,
)
from harness_commander.infrastructure.templates import (
    INIT_FILE_TEMPLATES,
    INIT_TEMPLATE_FILES,
    get_template_resource_path,
)

REQUIRED_GOVERNANCE_FILES = [
    "ARCHITECTURE.md",
    "docs/PLANS.md",
]

RELATED_REFERENCE_FILES = [
    "docs/PRODUCT_SENSE.md",
    "docs/QUALITY_SCORE.md",
    "docs/RELIABILITY.md",
    "docs/SECURITY.md",
    "docs/design-docs/core-beliefs.md",
    "docs/product-specs/index.md",
    "docs/product-specs/v1/index.md",
]

RECOMMENDED_PLAN_REFERENCES = [
    "docs/PRODUCT_SENSE.md",
    "docs/QUALITY_SCORE.md",
    "docs/RELIABILITY.md",
    "docs/SECURITY.md",
    "docs/design-docs/core-beliefs.md",
    "docs/product-specs/v1/index.md",
]

REQUIRED_PLAN_SECTIONS = {
    "## Goal": "计划缺少 Goal 段落",
    "## Context": "计划缺少 Context 段落",
    "## Business Logic": "计划缺少 Business Logic 段落",
    "## Scope": "计划缺少 Scope 段落",
    "## Acceptance Criteria": "计划缺少 Acceptance Criteria 段落",
    "## Exception Handling": "计划缺少 Exception Handling 段落",
    "## Verification": "计划缺少 Verification 段落",
}

ULW_REQUIRED_LABELS = (
    "### 目标",
    "### 涉及范围",
    "### 验收标准",
)


@dataclass(slots=True)
class PlanContext:
    """生成计划时的中间上下文。"""

    request: str
    normalized_request: str
    goals: list[str]
    scope_items: list[str]
    constraint_items: list[str]
    risk_items: list[str]
    references: list[str]
    ulws: list[dict[str, object]]


@dataclass(slots=True)
class PlanValidationResult:
    """计划校验结果。

    issues 为空代表通过校验，否则由应用层决定以 warning 还是 failure 输出。
    """

    issues: list[CommandMessage]


@dataclass(slots=True)
class TemplateLoadResult:
    """初始化模板加载结果。"""

    templates: dict[str, str]
    warnings: list[CommandMessage]
    source: str


def ensure_governance_documents(root: Path) -> None:
    """检查核心治理文档是否齐全。"""

    missing = [
        relative_path
        for relative_path in [*REQUIRED_GOVERNANCE_FILES, *RELATED_REFERENCE_FILES]
        if not (root / relative_path).exists()
    ]
    if missing:
        raise HarnessCommanderError(
            "missing_governance_documents",
            "核心治理文档缺失，无法继续执行当前命令",
            detail={"missing_paths": missing},
        )


def build_plan_path(root: Path, request: str) -> Path:
    """根据需求内容生成计划文件路径。"""

    date_prefix = utc_timestamp()[:10]
    filename = f"{date_prefix}-{slugify(request)}.md"
    result: Path = next_available_path(root / "docs/exec-plans/active" / filename)
    return result


def render_plan_markdown(request: str) -> str:
    """渲染符合 V1 产品规格的计划模板。"""

    context = build_plan_context(request)
    references = "\n".join(f"- `{reference}`" for reference in context.references)
    scope_items = "\n".join(f"- {item}" for item in context.scope_items)
    ulw_sections = "\n\n".join(_render_ulw_section(ulw) for ulw in context.ulws)
    verification_steps = "\n".join(
        [
            "- 运行目标命令，检查文本摘要和 `--json` 输出字段是否一致。",
            "- 校验计划文件已落盘到 `docs/exec-plans/active/`，且引用了必需治理文档。",
            "- 针对至少一个失败场景验证不会伪造通过结果。",
        ]
    )

    return f"""# {context.normalized_request} 执行计划

## Goal

- 把“{context.normalized_request}”整理为可执行、可验证、可继续协作的实现计划。
- 在进入编码前补齐治理文档引用、约束边界和最小验证闭环。

## Context

- 当前输入需求：{context.normalized_request}
- 本计划由 `harness propose-plan` 生成，用于承接模糊需求并避免直接开写。
- 计划生成和后续实现需优先遵循 `ARCHITECTURE.md`、`docs/PLANS.md` 与相关规范文档。

## Business Logic

- 该计划服务于 Harness-Commander 的统一命令治理目标，要求先计划、后实现、再验证。
- Harness 负责统一计划结构、引用规则、产物路径和结果协议。
- 宿主模型可辅助需求整理与 ULW 拆分，但不能改变结果结构、落盘目录和通过/失败语义。
- 当前需求的核心目标包括：
{_indent_bullets(context.goals)}
- 当前需求的关键约束包括：
{_indent_bullets(context.constraint_items)}
- 当前需求的主要风险包括：
{_indent_bullets(context.risk_items)}

## Scope

{scope_items}

## Non-Goals

- 不跳过治理文档引用校验后直接开写实现。
- 不一次性把需求扩展为超出当前输入意图的大范围重构。
- 不在没有验证路径的情况下宣称任务完成。

{ulw_sections}

## Acceptance Criteria

- AC 1: 计划文件必须包含 Goal、Context、Business Logic、Scope、Acceptance Criteria、Exception Handling、Verification 等关键章节。
- AC 2: 计划文件必须引用 `ARCHITECTURE.md`、`docs/PLANS.md` 和至少一份相关规范文档。
- AC 3: 每个 ULW 必须包含“目标 / 涉及范围 / 验收标准”，便于宿主工具按块推进。
- AC 4: 计划产物固定落在 `docs/exec-plans/active/`，并遵循统一结果协议。

## Exception Handling

- 当 `ARCHITECTURE.md`、`docs/PLANS.md` 或相关规范文档缺失时，必须停止继续执行并提示缺失路径。
- 当目标计划文件名发生冲突时，必须生成新的不冲突路径，而不是覆盖已有文件。
- 当需求信息不足以可靠拆分任务时，至少保留目标、约束和风险提示，避免伪造确定性计划。
- 当后续实现或验证失败时，必须保留失败摘要，不能伪造通过结果。

## Verification

{verification_steps}

## References

- `ARCHITECTURE.md`
- `docs/PLANS.md`
{references}
"""


def build_plan_context(request: str) -> PlanContext:
    """把自然语言需求整理为稳定的计划生成上下文。"""

    normalized_request = request.strip() or "未命名需求"
    goals = [
        f"明确“{normalized_request}”要解决的用户问题与交付目标。",
        "把模糊需求收敛为可以继续实现和验证的执行计划。",
    ]
    scope_items = [
        f"需求主题：{normalized_request}",
        "涉及治理文档引用补齐与执行边界确认。",
        "涉及后续实现拆分、验证闭环和结果协议对齐。",
    ]
    constraint_items = [
        "计划必须引用 `ARCHITECTURE.md` 与 `docs/PLANS.md`。",
        "计划必须至少引用一份相关规范文档。",
        "每个 ULW 都必须包含目标、涉及范围、验收标准。",
        "计划文件必须落盘到 `docs/exec-plans/active/`。",
    ]
    risk_items = [
        "如果需求边界不清晰，后续实现容易范围失控。",
        "如果缺少治理文档引用，计划可能偏离架构与质量约束。",
        "如果没有验证闭环，宿主工具无法稳定消费执行结果。",
    ]
    references = [*RECOMMENDED_PLAN_REFERENCES]
    ulws: list[dict[str, object]] = [
        {
            "title": "ULW 1: 澄清需求并锁定边界",
            "goal": f"把“{normalized_request}”整理为清晰目标、范围、约束和风险。",
            "scope": [
                "梳理当前需求的交付目标。",
                "识别涉及的治理文档和关键边界。",
                "明确本轮不做的内容，避免范围膨胀。",
            ],
            "acceptance": [
                "需求被整理为明确的目标、约束和风险说明。",
                "计划可作为后续实现的低上下文输入。",
            ],
        },
        {
            "title": "ULW 2: 补齐治理文档引用并生成执行块",
            "goal": "把治理文档引用、ULW 结构和产物路径固化到计划中。",
            "scope": [
                "补齐必需治理文档与相关规范文档引用。",
                "生成细粒度 ULW，覆盖实现与验证闭环。",
                "确保落盘位置和结果协议符合产品要求。",
            ],
            "acceptance": [
                "计划包含 `ARCHITECTURE.md`、`docs/PLANS.md` 和相关规范文档引用。",
                "计划内每个 ULW 都包含目标、涉及范围、验收标准。",
            ],
        },
    ]
    return PlanContext(
        request=request,
        normalized_request=normalized_request,
        goals=goals,
        scope_items=scope_items,
        constraint_items=constraint_items,
        risk_items=risk_items,
        references=references,
        ulws=ulws,
    )
def validate_plan_document(root: Path, plan_path: Path) -> PlanValidationResult:
    """校验计划文档是否满足 V1 合规要求。"""

    if not plan_path.exists():
        raise HarnessCommanderError(
            "missing_plan_file",
            "计划文件不存在，无法执行校验",
            location=str(plan_path),
        )

    content = plan_path.read_text(encoding="utf-8")
    issues: list[CommandMessage] = []

    for heading, message in REQUIRED_PLAN_SECTIONS.items():
        if heading not in content:
            issues.append(
                CommandMessage(
                    code="missing_section",
                    message=message,
                    location=str(plan_path),
                    detail={"section": heading},
                )
            )

    for required_reference in REQUIRED_GOVERNANCE_FILES:
        if required_reference not in content:
            issues.append(
                CommandMessage(
                    code="missing_reference",
                    message="计划缺少必需治理文档引用",
                    location=str(plan_path),
                    detail={"reference": required_reference},
                )
            )

    if not any(reference in content for reference in RELATED_REFERENCE_FILES):
        issues.append(
            CommandMessage(
                code="missing_related_reference",
                message="计划未引用任何相关规范文档",
                location=str(plan_path),
            )
        )

    ulw_count = content.count("## ULW ")
    if ulw_count == 0:
        issues.append(
            CommandMessage(
                code="missing_ulw",
                message="计划缺少 ULW 任务块。",
                location=str(plan_path),
            )
        )
    else:
        for label in ULW_REQUIRED_LABELS:
            if label not in content:
                issues.append(
                    CommandMessage(
                        code="incomplete_ulw",
                        message="计划中的 ULW 缺少必需字段。",
                        location=str(plan_path),
                        detail={"required_label": label},
                    )
                )

    for required_path in [*REQUIRED_GOVERNANCE_FILES, *RELATED_REFERENCE_FILES]:
        absolute_path = root / required_path
        if not absolute_path.exists():
            issues.append(
                CommandMessage(
                    code="missing_governance_file",
                    message="仓库中缺少计划所依赖的治理文档。",
                    location=str(absolute_path),
                    detail={"reference": required_path},
                )
            )

    return PlanValidationResult(issues=issues)



def _render_ulw_section(ulw: dict[str, object]) -> str:
    """渲染单个 ULW 区块。"""

    title = str(ulw["title"])
    goal = str(ulw["goal"])
    scope = _indent_bullets(ulw["scope"])
    acceptance = _indent_bullets(ulw["acceptance"])
    return f"""## {title}

### 目标

- {goal}

### 涉及范围

{scope}

### 验收标准

{acceptance}"""



def _indent_bullets(items: object) -> str:
    """把列表项格式化为 markdown bullet。"""

    if not isinstance(items, (list, tuple)):
        return f"  - {items}"
    return "\n".join(f"  - {item}" for item in items)


def load_init_templates(root: Path) -> TemplateLoadResult:
    """从包内模板资源加载初始化模板。"""

    LOGGER = logging.getLogger(__name__)

    try:
        templates = _load_templates_from_package_resources()
    except Exception as error:
        fallback_location = str(get_template_resource_path("AGENTS.md"))
        LOGGER.warning(
            "无法读取包内初始化模板资源，使用内置模板 fallback_location=%s error=%s",
            fallback_location,
            error,
        )
        return TemplateLoadResult(
            templates=INIT_FILE_TEMPLATES.copy(),
            warnings=[
                CommandMessage(
                    code="init_template_fallback",
                    message="包内初始化模板资源无法读取，已回退到内置模板。",
                    location=fallback_location,
                    detail={"reason": str(error)},
                )
            ],
            source="builtin_fallback",
        )

    return TemplateLoadResult(
        templates=templates,
        warnings=[],
        source="package_resources",
    )


def _load_templates_from_package_resources() -> dict[str, str]:
    """读取全部包内模板资源，并按 init 输出路径返回。"""

    templates: dict[str, str] = {}
    missing_templates: list[str] = []

    for template_path in sorted(INIT_TEMPLATE_FILES):
        resource_path = get_template_resource_path(template_path)
        if not resource_path.exists():
            missing_templates.append(template_path)
            continue
        templates[template_path] = resource_path.read_text(encoding="utf-8").rstrip("\n")

    if missing_templates:
        missing_list = ", ".join(missing_templates)
        raise FileNotFoundError(f"缺少包内模板资源: {missing_list}")

    return templates
