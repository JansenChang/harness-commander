"""文档基础设施能力。

该模块负责治理文档存在性检查、计划模板渲染和计划校验，
确保所有命令都围绕仓库中的正式文档约束展开，而不是凭空猜测。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from harness_commander.domain.models import CommandMessage, HarnessCommanderError
from harness_commander.infrastructure.templates import INIT_FILE_TEMPLATES
from harness_commander.infrastructure.filesystem import (
    next_available_path,
    slugify,
    utc_timestamp,
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
    "docs/product-specs/harness-commander.md",
]

REQUIRED_PLAN_SECTIONS = {
    "## Goal": "计划缺少 Goal 段落",
    "## Business Logic": "计划缺少 Business Logic 段落",
    "## Acceptance Criteria": "计划缺少 Acceptance Criteria 段落",
    "## Exception Handling": "计划缺少 Exception Handling 段落",
    "## Steps": "计划缺少 Steps 段落",
    "## Verification": "计划缺少 Verification 段落",
}


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
    """渲染符合产品规格的最小计划模板。"""

    return f"""# {request} 执行计划

## Goal

- 围绕“{request}”完成一轮可验证交付。
- 确保实现过程遵循仓库治理文档，不绕过架构边界与质量规则。

## Business Logic

- 该计划服务于 Harness-Commander 统一命令治理目标。
- 实现过程中必须优先引用 `ARCHITECTURE.md`、`docs/PLANS.md` 和至少一份相关规范文档。

## Acceptance Criteria

- AC 1: 产出可执行实现，且核心命令输出统一结果结构。
- AC 2: 相关变更具备可验证方式，至少包含命令验证或测试验证。
- AC 3: 产物写入遵循非静默覆盖原则，支持 dry-run 预演。

## Exception Handling

- 当核心治理文档缺失时，必须直接失败并提示缺失路径。
- 当目标文件已存在且会产生覆盖时，必须停止并提示人工处理。
- 当验证失败时，必须保留失败摘要，不能伪造通过结果。

## Scope

- 涉及目标：{request}
- 涉及目录：`src/`、`tests/`、`docs/exec-plans/active/`

## ULW 1

- 目标：建立与“{request}”相关的最小实现骨架。
- 涉及范围：核心代码结构、输入输出协议、必要基础设施。
- 验收标准：命令或模块能够被调用，且返回结构稳定。

## ULW 2

- 目标：补齐与“{request}”对应的验证闭环。
- 涉及范围：测试、失败处理、证据输出。
- 验收标准：至少存在一条成功验证路径与一条失败校验路径。

## Steps

1. 阅读并确认相关治理文档与产品规格。
2. 完成核心代码实现与必要的文件写入保护。
3. 补充测试或验证命令，确认结果可复现。

## Verification

- 运行与实现相关的测试命令。
- 运行目标命令并检查文本输出与 JSON 输出。

## References

- `ARCHITECTURE.md`
- `docs/PLANS.md`
- `docs/PRODUCT_SENSE.md`
- `docs/RELIABILITY.md`
- `docs/SECURITY.md`
- `docs/product-specs/harness-commander.md`
"""


def validate_plan_document(root: Path, plan_path: Path) -> PlanValidationResult:
    """校验计划文档是否满足最小合规要求。"""

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
    if "ULW" not in content or "验收标准：" not in content:
        issues.append(
            CommandMessage(
                code="missing_ulw",
                message="计划缺少 ULW 任务块或 ULW 验收标准",
                location=str(plan_path),
            )
        )
    if not (root / "ARCHITECTURE.md").exists():
        issues.append(
            CommandMessage(
                code="missing_architecture_file",
                message="仓库中缺少 ARCHITECTURE.md，无法完成计划合规校验",
                location=str(root),
            )
        )
    return PlanValidationResult(issues=issues)


def load_init_templates(root: Path) -> TemplateLoadResult:
    """从 docs/design-docs/init-templates.md 加载初始化模板。"""

    LOGGER = logging.getLogger(__name__)
    templates_path = root / "docs/design-docs/init-templates.md"
    if not templates_path.exists():
        LOGGER.warning(
            "初始化模板文件缺失，使用内置模板 templates_path=%s",
            templates_path,
        )
        return TemplateLoadResult(
            templates=INIT_FILE_TEMPLATES.copy(),
            warnings=[
                CommandMessage(
                    code="init_template_fallback",
                    message="初始化模板文件缺失，已回退到内置模板。",
                    location=str(templates_path),
                )
            ],
            source="builtin",
        )

    try:
        content = templates_path.read_text(encoding="utf-8")
    except Exception as error:
        LOGGER.warning(
            "无法读取初始化模板文件，使用内置模板 templates_path=%s error=%s",
            templates_path,
            error,
        )
        return TemplateLoadResult(
            templates=INIT_FILE_TEMPLATES.copy(),
            warnings=[
                CommandMessage(
                    code="init_template_fallback",
                    message="初始化模板文件无法读取，已回退到内置模板。",
                    location=str(templates_path),
                    detail={"reason": str(error)},
                )
            ],
            source="builtin",
        )

    templates = parse_template_content(content)
    if not templates:
        LOGGER.warning(
            "初始化模板文件解析为空，使用内置模板 templates_path=%s",
            templates_path,
        )
        return TemplateLoadResult(
            templates=INIT_FILE_TEMPLATES.copy(),
            warnings=[
                CommandMessage(
                    code="init_template_fallback",
                    message="初始化模板文件损坏或解析为空，已回退到内置模板。",
                    location=str(templates_path),
                )
            ],
            source="builtin",
        )
    return TemplateLoadResult(templates=templates, warnings=[], source="external")


def parse_template_content(content: str) -> dict[str, str]:
    """解析模板文件内容，提取文件路径和模板内容。

    模板文件格式：
    #### 文件路径 模板
    ```markdown
    模板内容
    ```

    返回:
        模板字典，键为文件路径，值为模板内容
    """
    templates = {}
    lines = content.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i].strip()
        # 查找文件标题行，格式为 "#### 文件路径 模板"
        if line.startswith("#### ") and "模板" in line:
            # 提取文件路径，例如 "AGENTS.md 模板"
            path_part = line[5:].replace(" 模板", "").strip()

            # 查找代码块开始
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```markdown"):
                i += 1

            if i >= len(lines):
                break

            # 跳过代码块开始标记
            i += 1
            template_lines = []

            # 收集模板内容直到代码块结束
            while i < len(lines) and not lines[i].strip().startswith("```"):
                template_lines.append(lines[i])
                i += 1

            # 跳过代码块结束标记
            i += 1

            template_content = "\n".join(template_lines).rstrip("\n")
            if template_content:
                templates[path_part] = template_content

        i += 1

    # 如果模板文件解析失败或为空，返回空字典（调用方应处理这种情况）
    return templates
