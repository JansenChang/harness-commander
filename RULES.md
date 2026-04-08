# RULES

## 目的

这是 Harness-Commander 的项目级通用规则入口，对本仓库中的人类开发者与 AI agent 都生效。

它不是第二套独立规范源。它的职责是：

- 给所有协作者提供统一阅读顺序
- 固定跨工具一致的硬约束
- 把长期有效的项目规则收敛到一个稳定入口

更细的产品、架构、质量、可靠性和设计规则，仍以 `docs/` 和根目录正式文档为准。

## 适用范围

- 整个仓库
- 所有命令实现、文档变更、测试补洞、重构和排查任务
- 所有 AI 工具入口，包括但不限于 `AGENTS.md`、`CLAUDE.md` 对应的执行环境

## 默认阅读顺序

开始任何任务前，按以下顺序阅读：

1. `RULES.md`
2. 对应工具入口文件
   - `AGENTS.md`
   - `CLAUDE.md`
3. 与任务直接相关的正式规则源
   - `ARCHITECTURE.md`
   - `docs/product-specs/`
   - `docs/design-docs/`
   - `docs/QUALITY_SCORE.md`
   - `docs/RELIABILITY.md`
   - `docs/SECURITY.md`
4. 当前执行计划
   - `docs/exec-plans/active/`
5. 历史归档与技术债
   - `docs/exec-plans/completed/`
   - `docs/exec-plans/tech-debt-tracker.md`

## 总原则

- 先理解上下文，再改代码。
- 不允许绕过现有文档约束。
- 不允许在对话里发明规则却不回写仓库。
- 不允许借重构顺手改变产品逻辑。
- 不允许只修 happy path，不补失败路径和回退路径。

## 规则优先级

当多个文档同时约束一个任务时，按这个顺序处理：

1. 产品与协议事实
   - `docs/product-specs/`
2. 安全与可靠性红线
   - `docs/SECURITY.md`
   - `docs/RELIABILITY.md`
3. 架构与长期设计边界
   - `ARCHITECTURE.md`
   - `docs/design-docs/`
4. 质量与验收要求
   - `docs/QUALITY_SCORE.md`
5. 执行计划与阶段性约束
   - `docs/exec-plans/active/`

如果仍有冲突，先补文档澄清，再继续实现。

## 文档驱动规则

- 缺规范时，先补文档，再写实现。
- 改了行为，就必须同步更新对应文档。
- 单次任务记录进入 `docs/exec-plans/`，长期设计决策进入 `docs/design-docs/`。
- AI / Codex 的已确认错误，不允许只修代码，必须记录到：
  - `docs/exec-plans/tech-debt-tracker.md`
  - 或完成归档文档

## 应用层实现规则

- `src/harness_commander/application/commands.py` 是 facade，不再承载大段命令实现。
- 新的应用层命令逻辑默认进入 `src/harness_commander/application/command_handlers/`。
- 共享逻辑只有在跨命令复用时才允许上提。
- 不允许因为拆模块改变：
  - CLI 参数
  - `CommandResult` 结构
  - `success` / `warning` / `failure` 语义
  - 产物路径
  - dry-run 合同

详细规则见：

- `ARCHITECTURE.md`
- `docs/design-docs/application-command-development.md`

## 测试与验证规则

- 每次改动至少覆盖：
  - 1 条成功路径
  - 1 条主要失败路径
  - 1 条边界 / fallback 路径
- 重构不是“纯样式改动”；只要改了结构，就必须跑回归测试。
- 命令层改动默认至少跑：
  - `tests/test_cli.py`
  - `tests/test_integration.py`
- 如果涉及 provider 安装或路径解析，还要补跑：
  - `tests/test_provider_install_modes.py`
  - `tests/test_provider_path_resolution.py`
- 本项目默认优先使用 `.venv/bin/...` 路径执行测试和 CLI smoke，减少宿主环境差异。

## 重构规则

- 重构的目标是降复杂度、提可维护性，不是趁机改需求。
- 在 active plan 明确完成前，不允许跳过结构治理直接进入下一轮功能扩展。
- 如果重构后仍保留已知限制，必须记录到 `docs/exec-plans/tech-debt-tracker.md`。

## AI 协作规则

- 主 agent 负责：
  - 读取事实源
  - 做最终决策
  - 整合结果
  - 落代码或落文档
- 子 agent 负责：
  - 有边界的信息收集
  - 专项审查
  - 非重叠代码改动
- 在产品边界未锁定前，优先开分析型 agent，不优先开纯编码 agent。

## 当前项目约束

- 当前仓库仍以文档驱动为主，`docs/` 是正式事实源。
- 后续 V2 开发必须建立在：
  - 已确认的产品文档
  - 已落地的架构分层
  - 已通过的回归测试
 之上。

## 相关入口

- `AGENTS.md`
- `CLAUDE.md`
- `ARCHITECTURE.md`
- `docs/design-docs/index.md`
- `docs/product-specs/index.md`
- `docs/QUALITY_SCORE.md`
- `docs/RELIABILITY.md`
- `docs/SECURITY.md`
