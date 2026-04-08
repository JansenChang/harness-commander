# Harness-Commander V2 `run-agents` Phase 2 宿主模型合同规划

## Goal

为 `run-agents` 的 Phase 2 锁定 `requirements` / `plan` 的宿主模型主路径合同，明确入口条件、阶段输入输出、fallback 语义与最终状态边界，让后续实现可以在不破坏 Harness 治理权的前提下推进。

## Context

- V2 Phase 1 已完成并归档：
  - `run-agents` 固定阶段顺序
  - `check` preflight 三态
  - `meta.stage_contracts` 最小合同
- 当前 Phase 2 主计划已确认：
  - `run-agents` 只开放 `requirements` 与 `plan` 给宿主模型默认优先主路径
  - `check`、`verify`、`pr-summary`、最终状态、阻断逻辑继续由 Harness 控制
- 当前命令文档仍停留在“问题列出”层，尚未形成可直接进入实现的命令级合同计划。

## Scope

- 锁定 `requirements` / `plan` 进入宿主模型主路径的启动条件
- 锁定两阶段的最小输入输出合同
- 锁定 provider 缺失、模型失败、结构不完整时的 fallback / 最终状态矩阵
- 同步 `product.md` / `protocol.md` / `testing.md` / `acceptance.md` 的 Phase 2 输入

## Non-Goals

- 不引入新的 runtime 阶段，例如 `docs`
- 不设计 resume token / retry runtime / attempt 编排
- 不让 `check`、`implement`、`verify`、`pr-summary` 进入宿主模型主路径
- 不修改并发模型或多 agent 调度机制
- 不直接进入代码实现

## ULW 1: 锁定宿主模型主路径启动条件

### 目标

- 明确 `run-agents` 在什么前提下进入 `requirements` / `plan` 的 host-first 路径，以及 provider 不满足条件时如何处理。

### 涉及范围

- `docs/product-specs/v2/commands/run-agents/product.md`
- `docs/product-specs/v2/commands/run-agents/protocol.md`
- `docs/product-specs/v2/commands/run-agents/acceptance.md`

### 验收标准

- 明确默认行为是“provider 就绪即进入主路径”还是仍需额外开关
- 明确 provider 缺失、provider 不兼容、认证失败时的语义是 `failure` 还是 deterministic fallback
- 明确 `requirements` / `plan` 之外所有阶段继续 `host_model_allowed=false`

## ULW 2: 锁定 `requirements` / `plan` 的最小阶段合同

### 目标

- 把宿主模型参与后的阶段合同固定为 Harness 可消费、可验证、可 fallback 的最小结构。

### 涉及范围

- `docs/product-specs/v2/commands/run-agents/product.md`
- `docs/product-specs/v2/commands/run-agents/protocol.md`
- `docs/product-specs/v2/commands/run-agents/testing.md`

### 验收标准

- `requirements` 与 `plan` 都明确：
  - 输入
  - 输出
  - 阻断条件
  - fallback
  - 产物
  - 是否允许宿主模型参加
- 明确宿主模型输出是“摘要级结果”还是“可重放任务包”
- 明确宿主模型返回结构不完整时，Harness 需要保留哪些稳定 fallback 事实

## ULW 3: 锁定 fallback 与最终状态组合矩阵

### 目标

- 明确“模型失败但命令继续”“模型失败且 fallback 也失败”“模型成功但 verify 后续阻断”等场景下的最终语义。

### 涉及范围

- `docs/product-specs/v2/commands/run-agents/protocol.md`
- `docs/product-specs/v2/commands/run-agents/acceptance.md`
- `docs/product-specs/v2/commands/run-agents/testing.md`

### 验收标准

- 定义至少以下场景的命令级 `success` / `warning` / `failure` 语义：
  - provider 缺失
  - 宿主模型超时
  - 宿主模型返回空结果
  - 宿主模型返回结构不完整
  - 宿主模型失败后 deterministic fallback 成功
  - 宿主模型失败后 deterministic fallback 失败
- 明确 `check` preflight 三态与 Phase 2 host-first 路径如何组合
- 明确 `verify` 与 `pr-summary` 的门禁语义不因宿主模型接入而放宽

## ULW 4: 同步命令级文档与导航入口

### 目标

- 让仓库能够直接反映 `run-agents` Phase 2 的合同收敛进度，而不是继续依赖总计划或对话补充。

### 涉及范围

- `docs/exec-plans/active/harness-commander-v2/index.md`
- `docs/exec-plans/active/harness-commander-v2/phase2-host-model-path-planning.md`
- `docs/product-specs/v2/index.md`

### 验收标准

- active index 能直接定位到本命令级 active plan
- 主计划明确本文件是 `run-agents` 的命令级拆解入口
- V2 顶层导航能说明 `run-agents` Phase 2 已从“总规划”进入“命令级合同规划”

## Acceptance Criteria

- `run-agents` Phase 2 的产品问题被收敛为可执行的命令级合同计划。
- 后续实现团队不需要再靠口头澄清“什么时候走宿主模型”“失败后如何判定结果”。
- `requirements` / `plan` 的宿主模型边界与 Harness 保留权责写成仓库事实源。

## Verification

- 检查 `run-agents` 的 `product.md` / `protocol.md` / `testing.md` / `acceptance.md` 是否都有明确的 Phase 2 输入
- 检查 active index 与 Phase 2 主计划是否都能导航到本计划
- 检查是否仍存在“CLI 层已定义，但集成失败路径未定义”的合同空洞

## References

- `AGENTS.md`
- `docs/design-docs/harness-engineering.md`
- `docs/product-specs/v2/commands/run-agents/product.md`
- `docs/product-specs/v2/commands/run-agents/protocol.md`
- `docs/exec-plans/active/harness-commander-v2/phase2-host-model-path-planning.md`
