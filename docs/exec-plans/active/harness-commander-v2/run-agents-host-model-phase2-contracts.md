# Harness-Commander V2 `run-agents` Phase 2 宿主模型合同规划

## Goal

把 `run-agents` 从 Phase 1 的 deterministic baseline 推进到可实施的 Phase 2 产品规划，明确 `requirements` / `plan` 进入默认优先宿主模型主路径时的入口条件、阶段合同与 fallback 状态语义。

## Context

- V2 Phase 1 已完成并归档：
  - `run-agents` 已具备 `check -> requirements -> plan -> implement -> verify -> pr-summary` 的阶段合同基线
  - `check` preflight、verify 阻断与最终状态语义已收敛
- V2 已确认：
  - `run-agents` 是治理主入口
  - 只有 `requirements` 与 `plan` 允许进入宿主模型主路径
  - `check`、`verify`、`pr-summary`、最终状态、阻断逻辑与产物路径继续由 Harness 控制
- 当前尚未锁定的问题仍停留在产品/协议层，而不是实现层：
  - 默认何时进入宿主模型主路径
  - 宿主模型输出是摘要还是可重放任务包
  - 宿主模型失败、超时、结构不完整后的状态组合如何对外呈现

## Business Logic

- Phase 2 对 `run-agents` 的核心不是“接 provider”，而是先锁定 CLI 对外语义。
- 如果入口条件、阶段合同与 fallback 矩阵没有先落到文档，后续实现很容易出现：
  - 模型调用成功但阶段合同不可消费
  - fallback 已发生但结果看起来像主路径成功
  - `warning` / `failure` 在阶段级与命令级含义漂移
- 本计划先收敛产品和协议，不进入 runtime 或 provider 编排实现。

## Scope

- 明确 `requirements` / `plan` 进入宿主模型主路径的前置条件
- 明确 `requirements` / `plan` 的宿主模型输入输出最小合同
- 明确 provider 缺失、模型失败、超时、结构不完整时的 fallback 与最终状态矩阵
- 同步 `run-agents` 相关产品、协议和 V2 顶层导航

## Non-Goals

- 不实现新的宿主模型 runtime
- 不引入并发 agent 编排、恢复 / 重试 token 或 attempt 机制
- 不把 `docs` 阶段加入当前 runtime
- 不让 `check`、`verify`、`pr-summary` 进入宿主模型路径
- 不修改现有 `run-agents` CLI 参数与代码行为

## ULW 1: 锁定宿主模型主路径入口条件

### 目标

- 明确 `run-agents` 在什么前提下默认优先进入宿主模型主路径，以及缺失 prerequisite 时如何退回。

### 涉及范围

- `docs/product-specs/v2/commands/run-agents/product.md`
- `docs/product-specs/v2/commands/run-agents/protocol.md`

### 验收标准

- 明确默认入口是否只依赖 provider 已配置，还是仍需额外开关 / 模式门。
- 明确 provider 缺失、provider 不可用、provider 被禁用时，是命令级 `failure` 还是保守回退到 deterministic 路径。
- 明确除 `requirements` / `plan` 外，其余阶段继续保持 `host_model_allowed=false`。

## ULW 2: 锁定 `requirements` / `plan` 的宿主模型合同

### 目标

- 明确 Harness 如何向宿主模型提供输入，以及如何消费宿主模型返回结果。

### 涉及范围

- `docs/product-specs/v2/commands/run-agents/product.md`
- `docs/product-specs/v2/commands/run-agents/protocol.md`

### 验收标准

- 明确 `requirements` / `plan` 发送给宿主模型的最小输入包结构。
- 明确宿主模型返回的是“摘要级结果”还是“可重放任务包”，并把该决定写成协议事实。
- 明确哪些字段属于宿主模型可生成内容，哪些字段仍必须由 Harness 根据本地事实填充。

## ULW 3: 锁定 fallback 与最终状态矩阵

### 目标

- 让调用方能稳定理解“宿主模型失败，但命令仍继续”的真实语义。

### 涉及范围

- `docs/product-specs/v2/commands/run-agents/product.md`
- `docs/product-specs/v2/commands/run-agents/protocol.md`
- `docs/RELIABILITY.md`

### 验收标准

- 至少覆盖以下场景的阶段级与命令级语义：
  - provider 缺失
  - 宿主模型超时
  - 宿主模型返回空结果
  - 宿主模型返回结构不完整
  - 宿主模型失败后 deterministic fallback 成功
- 明确 fallback 事实必须如何进入 `meta.stage_contracts`、兼容字段与 summary。
- 明确何时是命令级 `success`、何时是 `warning`、何时必须升级为 `failure`。

## ULW 4: 同步导航并形成实现前移交物

### 目标

- 让仓库在进入实现前已经具备稳定的命令级事实源与计划入口。

### 涉及范围

- `docs/exec-plans/active/harness-commander-v2/index.md`
- `docs/exec-plans/active/harness-commander-v2/phase2-host-model-path-planning.md`
- `docs/product-specs/v2/index.md`

### 验收标准

- Phase 2 主计划能指向本命令级 active plan。
- `run-agents` 的产品和协议文档能明确引用本计划作为当前收敛入口。
- 后续实现无需再依赖对话补充 `run-agents` Phase 2 的基础产品边界。

## Acceptance Criteria

- `run-agents` Phase 2 的入口条件、宿主模型合同、fallback / 状态矩阵写成仓库事实源。
- `check`、`verify`、`pr-summary` 不进入宿主模型路径的边界明确且可导航。
- 后续实现计划可直接基于本计划展开，而不必重新发明 CLI 语义。

## Exception Handling

- 如果“默认优先宿主模型”与现有 CLI 兼容性冲突，优先锁兼容语义，再决定是否需要新增显式模式。
- 如果“可重放任务包”会扩大到新的 runtime 设计，必须明确标记为后续阶段，而不是混入本轮最小规划。
- 如果某种 fallback 场景暂时无法细化到实现级，至少先写清命令级状态与留痕要求。

## Verification

- 检查 `docs/product-specs/v2/index.md` 是否与 `run-agents` 命令文档对齐。
- 检查 `docs/product-specs/v2/commands/run-agents/product.md` 与 `protocol.md` 是否对同一组 Phase 2 问题给出一致口径。
- 检查主计划与本命令级计划之间不存在范围漂移。

## References

- `AGENTS.md`
- `docs/QUALITY_SCORE.md`
- `docs/RELIABILITY.md`
- `docs/design-docs/harness-engineering.md`
- `docs/exec-plans/active/harness-commander-v2/phase2-host-model-path-planning.md`
- `docs/product-specs/v2/index.md`
- `docs/product-specs/v2/commands/run-agents/product.md`
- `docs/product-specs/v2/commands/run-agents/protocol.md`
