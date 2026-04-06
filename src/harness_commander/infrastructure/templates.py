"""初始化模板定义。

该模块集中维护 `harness init` 需要补齐的默认目录与文件模板，
避免模板内容散落在命令编排层，影响可维护性与后续扩展。

## 模板版本控制
- 版本: 1.0.0
- 最后更新: 2026-04-04
- 兼容性: 向后兼容，新增模板不会影响现有项目
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

INIT_DIRECTORIES = [
    "docs/design-docs",
    "docs/exec-plans/active",
    "docs/exec-plans/completed",
    "docs/generated",
    "docs/product-specs",
    "docs/references",
]

INIT_FILE_TEMPLATES = {
    "AGENTS.md": """# AGENTS

## 这个文件是做什么的

用于定义 AI 在本项目中的身份、语气、决策边界和默认工作方式。

## 适合写什么

- AI 扮演的角色，例如首席架构师、资深后端工程师、代码审计员
- 输出风格，例如偏严格、偏教学、偏业务导向
- 决策权限，例如可以直接重构、必须先给方案、禁止跨模块改动
- 优先级规则，例如安全优先、稳定性优先、速度优先

## 推荐用法

- 每次让 AI 参与开发前，先让它读取这个文件
- 当团队希望统一 AI 的行为时，在这里集中定义规则
- 当 AI 输出风格跑偏时，优先修改这里而不是反复口头纠正

## 示例约束

- 默认身份：首席架构师 + 资深实现工程师
- 默认原则：先理解上下文，再改代码，禁止跳过现有规范，后续所有任务都必须先按 `docs/` 下的相关文件执行
- 默认权限：允许修改实现细节，不允许擅自推翻系统边界

## 执行规范

- 开始任何实现、重构、排查或文档补充前，先阅读相关 `docs/` 文件
- 如果 `docs/` 中已有规范、计划、设计或业务约束，默认严格按这些文件执行
- 如果发现当前任务缺少规范，先补充到对应 `docs/`，再继续落地
- `docs/exec-plans/active/` 用于记录进行中的执行计划
- `docs/exec-plans/completed/` 用于归档已经完成的执行计划
""",
    "ARCHITECTURE.md": """# ARCHITECTURE

## 这个文件是做什么的

用于描述系统的整体架构蓝图，帮助开发者和 AI 理解模块边界、依赖方向、数据流和关键设计约束。

## 适合写什么

- 系统分层，例如接口层、应用层、领域层、基础设施层
- 模块职责，例如用户、订单、支付、通知分别归谁负责
- 数据流向，例如请求如何进入系统、如何落库、如何回传
- 外部依赖，例如数据库、缓存、消息队列、第三方服务

## 推荐用法

- AI 在做跨文件或跨模块改动前，必须先阅读这里
- 当项目出现“功能能跑但结构变乱”时，用这里纠正实现方向
- 新增模块时，先在这里声明它属于哪一层、依赖谁、不依赖谁

## 目标

防止在开发过程中出现职责混乱、重复实现、跨层调用和隐式耦合。
""",
    "docs/DESIGN.md": """# DESIGN

## 这个文件是做什么的

用于定义产品的视觉规范，包括颜色、间距、字体、组件外观和页面一致性要求。

## 适合写什么

- 品牌色、辅助色、语义色
- 间距体系、字号体系、圆角和阴影规则
- 组件样式优先级
- 页面视觉禁用项

## 推荐用法

- AI 生成页面或组件前先参考这里
- 设计和前端对齐时，以这里作为视觉落地标准
- 评审 UI 是否一致时，以这里作为判断依据
""",
    "docs/FRONTEND.md": """# FRONTEND

## 这个文件是做什么的

用于定义前端开发的专项约束，防止页面实现方式失控或风格不统一。

## 适合写什么

- Hooks 使用规范
- 状态管理约定
- 组件拆分原则
- 请求层、路由层、样式层的边界

## 推荐用法

- AI 在写前端代码前先阅读这里
- 当前端代码开始出现风格分裂时，用这里统一约束
- 新人接手前端模块时，用这里快速建立开发边界感
""",
    "docs/PLANS.md": """# PLANS

## 这个文件是做什么的

用于记录项目 Roadmap、当前阶段目标和近期执行重点。

## 适合写什么

- 本周、本月、本季度的目标
- 当前正在推进的里程碑
- 功能优先级和依赖关系
- 阶段性风险和阻塞项

## 推荐用法

- 开启集中开发前，先用这里和 AI 对齐当前要做什么
- 做任务拆分时，把这里作为上层目标输入
- 回顾执行偏差时，检查是否偏离这里的阶段目标
""",
    "docs/PRODUCT_SENSE.md": """# PRODUCT_SENSE

## 这个文件是做什么的

用于解释业务规则背后的原因，帮助团队和 AI 理解需求为什么存在，而不只是知道要做什么。

## 适合写什么

- 用户价值和商业目标
- 为什么某个流程不能简化
- 为什么某些体验细节必须保留
- 指标导向，例如转化率、留存率、完成率

## 推荐用法

- 当 AI 提出“看起来更简单”的方案时，用这里判断是否真的符合产品目标
- 需求争议较大时，用这里记录产品层面的决策依据
- 避免只做表面功能，而忽略真正的业务意图
""",
    "docs/QUALITY_SCORE.md": """# QUALITY_SCORE

## 这个文件是做什么的

用于定义什么样的代码才算高质量，并提供统一的验收标准和自检依据。

## 适合写什么

- 单元测试覆盖要求
- 复杂度限制
- 命名、可读性、可维护性要求
- Review 打分标准

## 推荐用法

- AI 改完代码后，根据这里进行自我评分
- Code Review 时，用这里减少“凭感觉评审”
- 当团队对质量标准不统一时，用这里建立共同语言
""",
    "docs/RELIABILITY.md": """# RELIABILITY

## 这个文件是做什么的

用于规定系统在错误处理、日志记录、重试、超时和降级方面的硬性要求。

## 适合写什么

- 接口异常处理规范
- 重试策略和超时策略
- 日志字段要求和禁止项
- 告警、监控、降级和兜底方案

## 推荐用法

- AI 在写接口、任务调度、集成第三方时先参考这里
- 防止出现只实现 happy path、不处理失败路径的代码
- 把稳定性要求前置到开发阶段，而不是线上出问题后补救
""",
    "docs/SECURITY.md": """# SECURITY

## 这个文件是做什么的

用于定义项目中的安全红线，明确哪些做法绝对禁止，哪些校验必须存在。

## 适合写什么

- 数据脱敏规则
- 接口鉴权要求
- 防注入、防越权、防泄露规范
- 密钥、令牌、身份证号等敏感信息处理方式

## 推荐用法

- AI 在写日志、接口、查询和配置时必须参考这里
- 防止把敏感信息写进明文日志或测试样例
- 安全评审时，把这里作为最低合规基线
""",
    "docs/design-docs/index.md": """# 设计文档索引

## 这个文件是做什么的

用于汇总所有设计类文档，告诉团队和 AI 应该去哪里找到关键设计决策。

## 适合写什么

- 各设计文档的目录和链接
- 每篇文档的主题说明
- 哪些文档是当前有效版本
- 阅读顺序建议

## 推荐用法

- 把它当成设计知识库的首页
- 新增设计文档后，先更新这里再通知团队
- AI 在做较大改动前，先从这里找到相关设计依据
""",
    "docs/design-docs/core-beliefs.md": """# 核心技术信仰

## 这个文件是做什么的

用于记录团队在技术实现上绝对坚持和绝对避免的原则。

## 适合写什么

- 哪些基础能力必须复用现有封装
- 哪些库可以用，哪些库明确禁止引入
- 哪些领域逻辑不能被“聪明重写”
- 哪些代码风格或架构模式是团队统一要求

## 推荐用法

- 当 AI 倾向于过度封装、随意抽象或乱换库时，用这里纠偏
- 涉及高风险业务逻辑时，把不可违背的规则写死在这里
- 修改老系统公共逻辑前，优先检查这里有没有明确禁令

## 示例场景

- 汇率计算必须使用现有 Utils，不允许重新实现
- 金额计算必须保证精度，不允许直接使用不安全的浮点写法
- 基础设施能力优先复用团队统一组件，不允许平行造轮子
""",
    "docs/exec-plans/tech-debt-tracker.md": """# 技术债追踪

## 这个文件是做什么的

用于记录系统中的已知问题、历史包袱、危险区域和待重构事项。

## 适合写什么

- 老代码中的坑点和已知限制
- 暂时保留但不理想的实现方案
- 重构优先级和影响范围
- 修改前必须注意的兼容性风险

## 推荐用法

- AI 修改旧模块前，先阅读这里，避免踩到历史雷区
- 每次发现临时方案、脏修复或绕路实现，都补一条记录
- 做重构计划时，把这里作为优先级输入
""",
    "docs/generated/db-schema.md": """# 数据库结构快照

## 这个文件是做什么的

用于记录当前数据库的表结构、字段类型、索引和约束，帮助团队在修改数据库前了解现有结构。

## 适合写什么

- 表名、字段名、数据类型、默认值、是否允许 NULL
- 主键、外键、唯一约束、检查约束
- 索引名称、索引字段、索引类型（B-tree、Hash、GIN 等）
- 视图、存储过程、触发器的定义
- 数据量估算、增长趋势、性能瓶颈

## 推荐用法

- 在写 ORM 模型或迁移脚本前，先从这里确认字段定义
- AI 在生成 SQL 或数据库相关代码时，优先参考这里而不是猜测
- 当数据库结构变更时，同步更新这个文件
- 把它作为数据库设计的唯一可信来源

## 注意

这是生成区文档，优先保证信息准确和可引用，不要求写成长篇说明。
""",
    "docs/product-specs/index.md": """# 业务需求索引

## 这个文件是做什么的

用于汇总所有产品需求文档，帮助团队快速定位具体业务规则和页面流程。

## 适合写什么

- PRD 文档目录
- 功能名称与对应文档链接
- 当前生效版本
- 需求负责人或背景说明

## 推荐用法

- 把它作为产品知识库入口
- 新需求落地时，先登记到这里再细化文档
- AI 在写业务逻辑前，先从这里找到对应 PRD

## 当前需求文档

- `新用户引导`：`docs/product-specs/new-user-onboarding.md`
""",
    "docs/product-specs/new-user-onboarding.md": """# 新用户引导

## 这个文件是做什么的

用于描述新用户从首次进入产品到完成关键激活动作的完整业务流程。

## 适合写什么

- 触发入口和目标用户
- 页面步骤、状态流转和分支条件
- 成功标准，例如注册完成、资料补齐、首个关键动作完成
- 异常路径，例如跳过、失败、重试、中断恢复

## 推荐用法

- 前后端在实现新手引导前先对齐这里的流程定义
- AI 在写 onboarding 相关逻辑时，优先参考这里而不是自行猜测
- 当转化率目标变化时，同步更新这里的业务目标和漏斗定义
""",
    "docs/references/design-system-reference-llms.txt": """设计系统参考文件

这个文件给 AI 提供简化版的 UI 与组件规范，避免在写页面时凭空假设设计规则。

适合放入：
- 颜色、字号、间距、圆角等基础规范
- 按钮、表单、弹窗、表格等组件的使用规则
- 禁止使用的视觉样式
- 常见页面布局模式

推荐用法：
- 让 AI 在写前端页面前先读取它
- 把设计系统长文档提炼成模型易读取的小抄
""",
    "docs/references/nixpacks-llms.txt": """Nixpacks 参考文件

这个文件给 AI 提供构建与部署相关的简化参考，避免生成与当前部署体系不兼容的配置。

适合放入：
- 常见构建入口和启动方式
- 环境变量约定
- 构建产物位置
- 部署时常见限制和注意事项

推荐用法：
- AI 在生成部署脚本、Docker 配置或构建命令前先读取它
- 把官方文档中真正常用的部分浓缩到这里
""",
    "docs/references/uv-llms.txt": """uv 参考文件

这个文件给 AI 提供依赖管理和 Python 开发工作流的简化说明，避免错误生成安装、锁定或运行命令。

适合放入：
- 依赖安装方式
- 虚拟环境管理方式
- 锁文件约定
- 常用开发命令

推荐用法：
- AI 在补充依赖、更新环境或生成命令时先读取它
- 如果项目不是 Python，也可以替换成对应生态的参考文件，例如 Maven、Gradle 或 pnpm

当前项目补充约定：
- 首轮 Python 骨架验证依赖 `pytest`
- 如果执行 `python3 -m pytest` 报错 `No module named pytest`，先安装开发依赖，再继续验证
- 优先使用 `python3 -m pip install pytest` 或等价的项目级依赖安装方式补齐测试依赖
- 如果出现 `externally-managed-environment`，禁止直接污染系统 Python，改为在项目内创建 `.venv` 后再安装测试依赖
""",
}


# 模板元数据
TEMPLATE_METADATA = {
    "version": "1.0.0",
    "last_updated": "2026-04-04",
    "template_count": len(INIT_FILE_TEMPLATES),
    "directory_count": len(INIT_DIRECTORIES),
}


def validate_template_structure() -> list[str]:
    """验证模板结构是否符合规范。

    返回:
        验证问题列表，空列表表示所有模板都符合规范
    """
    issues = []

    # 检查必需模板是否存在
    required_templates = [
        "ARCHITECTURE.md",
        "docs/RELIABILITY.md",
        "docs/SECURITY.md",
        "docs/QUALITY_SCORE.md",
        "docs/PLANS.md",
    ]

    for template in required_templates:
        if template not in INIT_FILE_TEMPLATES:
            issues.append(f"必需模板缺失: {template}")

    # 检查模板内容是否包含必需部分
    for template_path, content in INIT_FILE_TEMPLATES.items():
        # 检查是否包含标题
        if not content.strip().startswith("# "):
            issues.append(f"模板缺少标题: {template_path}")

        # 检查是否包含用途说明
        if "这个文件是做什么的" not in content:
            issues.append(f"模板缺少用途说明: {template_path}")

        # 检查是否包含推荐用法
        if "推荐用法" not in content:
            issues.append(f"模板缺少推荐用法: {template_path}")

    return issues


def get_template_summary() -> dict[str, Any]:
    """获取模板摘要信息。

    返回:
        包含模板统计信息的字典
    """
    # 按目录分组统计
    template_by_dir: dict[str, int] = {}
    for template_path in INIT_FILE_TEMPLATES.keys():
        dir_path = str(Path(template_path).parent)
        template_by_dir[dir_path] = template_by_dir.get(dir_path, 0) + 1

    return {
        "metadata": TEMPLATE_METADATA,
        "template_count": len(INIT_FILE_TEMPLATES),
        "directory_count": len(INIT_DIRECTORIES),
        "templates_by_directory": template_by_dir,
        "required_templates": [
            "ARCHITECTURE.md",
            "docs/RELIABILITY.md",
            "docs/SECURITY.md",
            "docs/QUALITY_SCORE.md",
            "docs/PLANS.md",
        ],
    }


def get_template_content(template_path: str) -> str:
    """获取指定路径的模板内容。

    参数:
        template_path: 模板路径

    返回:
        模板内容字符串

    异常:
        KeyError: 当模板不存在时抛出
    """
    if template_path not in INIT_FILE_TEMPLATES:
        raise KeyError(f"模板不存在: {template_path}")

    return INIT_FILE_TEMPLATES[template_path]


def list_templates() -> list[str]:
    """列出所有可用的模板路径。

    返回:
        按字母顺序排序的模板路径列表
    """
    return sorted(INIT_FILE_TEMPLATES.keys())


# 白名单校验相关
PROHIBITED_DIRS = {
    "src",
    "tests",
    ".venv",
    "venv",
    "dist",
    "build",
    "docs/generated/evidence",
    # 根据关键规则16，init命令不得创建以上目录
}


def validate_path_against_whitelist(path: str | Path) -> list[str]:
    """校验路径是否符合白名单约束。

    参数:
        path: 待校验的路径（相对路径）

    返回:
        问题描述列表，空列表表示通过校验
    """
    if isinstance(path, Path):
        path = str(path)

    # 转换为 POSIX 风格的路径，便于处理
    path = path.replace("\\", "/")

    issues = []

    # 检查是否以禁止的目录开头
    for prohibited in PROHIBITED_DIRS:
        if path == prohibited or path.startswith(prohibited + "/"):
            issues.append(f"路径 {path} 属于禁止创建的目录: {prohibited}")

    # 检查是否在白名单中（允许的目录或文件）
    # 白名单包括 INIT_DIRECTORIES 和 INIT_FILE_TEMPLATES 的键
    # 注意：这里只检查完全匹配或父目录在白名单中
    # 例如，如果白名单有 "docs/generated/evidence"，那么 "docs/generated/evidence/foo.json" 也允许
    # 但需要确保父目录在白名单中
    allowed = set(INIT_DIRECTORIES) | set(INIT_FILE_TEMPLATES.keys())

    # 将路径与白名单比较
    matched = False
    for allowed_path in allowed:
        if path == allowed_path:
            matched = True
            break
        # 如果路径是白名单中某个目录的子路径，也允许
        if path.startswith(allowed_path + "/"):
            matched = True
            break

    if not matched:
        # 检查是否是白名单中某个目录的父目录（例如，创建 "docs" 而白名单有 "docs/generated"）
        # 这种情况不允许，因为可能创建超出范围的目录
        for allowed_path in allowed:
            if allowed_path.startswith(path + "/"):
                issues.append(f"路径 {path} 是白名单目录 {allowed_path} 的父目录，不允许创建")
                break
        else:
            issues.append(f"路径 {path} 不在白名单中")

    return issues


def validate_init_targets(directories: list[str], files: list[str]) -> list[str]:
    """批量校验初始化目标路径。

    参数:
        directories: 目录路径列表
        files: 文件路径列表

    返回:
        所有校验问题的列表
    """
    issues = []
    for dir_path in directories:
        issues.extend(validate_path_against_whitelist(dir_path))
    for file_path in files:
        issues.extend(validate_path_against_whitelist(file_path))
    return issues
