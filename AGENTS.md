# AGENTS

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

## 目录索引

- `ARCHITECTURE.md`：系统分层、模块边界、数据流与依赖方向
- `docs/DESIGN.md`：视觉规范、颜色、间距和组件样式要求
- `docs/FRONTEND.md`：前端实现约束，例如 Hooks、状态管理和组件拆分规则
- `docs/PLANS.md`：当前 Roadmap、阶段目标和近期执行重点
- `docs/PRODUCT_SENSE.md`：业务目标、用户价值和需求背后的原因
- `docs/QUALITY_SCORE.md`：代码验收标准、自检标准和质量评分依据
- `docs/RELIABILITY.md`：错误处理、日志、重试、超时和稳定性要求
- `docs/SECURITY.md`：安全红线、鉴权规则和敏感信息处理规范
- `docs/design-docs/index.md`：设计文档总入口
- `docs/design-docs/core-beliefs.md`：团队坚持或禁止的技术原则
- `docs/exec-plans/active/`：当前进行中的功能计划
- `docs/exec-plans/completed/`：已经完成的执行计划
- `docs/exec-plans/tech-debt-tracker.md`：技术债、历史坑点和重构风险
- `docs/generated/db-schema.md`：数据库结构快照，写 SQL 或 ORM 前必须引用
- `docs/product-specs/index.md`：业务需求目录
- `docs/product-specs/new-user-onboarding.md`：新用户引导业务规则示例
- `docs/references/design-system-reference-llms.txt`：给 AI 用的设计系统小抄
- `docs/references/nixpacks-llms.txt`：给 AI 用的构建部署参考
- `docs/references/uv-llms.txt`：给 AI 用的依赖管理参考
