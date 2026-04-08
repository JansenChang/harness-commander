# Harness-Commander V2 `distill` Phase 2 宿主模型默认路径规划

## Goal

把 `distill` 从 Phase 1 的 deterministic baseline 推进到可实施的 Phase 2 产品规划，明确默认入口、provider prerequisite、fallback 语义与来源映射兼容边界，为后续 host-first 实现提供稳定事实源。

## Context

- V2 Phase 1 已完成并归档：
  - `distill` 已具备 `heuristic` / `host-model` / `auto` 三种模式
  - `extraction_report`、`section_sources`、`source_mapping_coverage` 已形成基础结果协议
  - failure / fallback / artifact / summary / meta 一致性已补齐
- V2 已确认：
  - `distill` 是第一批必须进入宿主模型主路径的命令之一
  - 即使进入 host-first 主路径，Harness 仍控制最终状态、产物路径、fallback 事实和结构化结果合同
- 当前尚未锁定的问题仍停留在产品/协议层：
  - 默认入口是否从 `heuristic` 切到 `auto`、host-first，还是新增显式模式
  - provider 缺失时是直接失败还是回退到 heuristic
  - 宿主模型提炼部分成功但来源映射不足时的通过语义

## Business Logic

- `distill` 的 Phase 2 不是单纯把默认模式改成 host-model，而是重新定义“默认提炼路径”的产品语义。
- 如果默认入口、fallback 规则和来源映射通过条件没有先锁定，后续实现会出现：
  - provider 缺失时行为不可预测
  - 宿主模型部分成功被误报为完整成功
  - 结构化来源映射与最终状态漂移
- 本计划先收敛产品与协议，不修改命令实现。

## Scope

- 明确 `distill` Phase 2 的默认入口模式与 prerequisite
- 明确宿主模型失败、部分成功、fallback 成功时的结果合同
- 明确来源映射覆盖不足时的 success / warning / failure 边界
- 同步 `distill` 相关产品、协议和 V2 顶层导航

## Non-Goals

- 不实现 host-first runtime
- 不修改现有 `distill` CLI 参数与代码行为
- 不扩展新的 section 类型或跨文件聚合提炼
- 不实现增量 distill 或 chunk 级引用系统
- 不把最终状态、目标路径或 fallback 记录交给宿主模型

## ULW 1: 锁定默认入口与 prerequisite 语义

### 目标

- 明确 `distill` 在 Phase 2 中默认如何进入宿主模型主路径，以及 prerequisite 缺失时如何处理。

### 涉及范围

- `docs/product-specs/v2/commands/distill/product.md`
- `docs/product-specs/v2/commands/distill/protocol.md`

### 验收标准

- 明确默认入口是 `auto`、host-first 还是新的显式模式。
- 明确 provider 缺失、provider 不可用、provider 被禁用时的对外语义。
- 明确与现有 `heuristic` / `host-model` / `auto` 模式的兼容边界，避免 Phase 2 规划与现有 CLI 描述冲突。

## ULW 2: 锁定 host-first fallback 与状态合同

### 目标

- 让调用方能稳定理解宿主模型参与后的 `success` / `warning` / `failure` 语义。

### 涉及范围

- `docs/product-specs/v2/commands/distill/product.md`
- `docs/product-specs/v2/commands/distill/protocol.md`
- `docs/RELIABILITY.md`

### 验收标准

- 明确宿主模型超时、空结果、结构不完整、调用失败时，是否回退到 heuristic，以及回退后最终状态如何表达。
- 明确 partial host-model 输出但 fallback 未发生时，什么条件下允许继续成功，什么条件下必须 warning / failure。
- 明确 `fallback_from`、`fallback_reason`、`extraction_report`、`artifacts` 在 host-first 路径下的稳定留痕要求。

## ULW 3: 锁定来源映射覆盖与通过边界

### 目标

- 明确来源映射不足时对结果可信度与最终状态的影响，而不是让下游自己猜测。

### 涉及范围

- `docs/product-specs/v2/commands/distill/product.md`
- `docs/product-specs/v2/commands/distill/protocol.md`

### 验收标准

- 明确 unmatched 条目是否继续沿用现有语义，还是需要新增 coverage threshold。
- 明确 `source_mapping_coverage` 在 host-first 路径下是否影响命令级状态。
- 明确 Harness 继续控制 `section_sources`、`source_mapping_coverage` 与目标文件落盘事实。

## ULW 4: 同步导航并形成实现前移交物

### 目标

- 让仓库在进入实现前已经具备稳定的 `distill` Phase 2 规划入口。

### 涉及范围

- `docs/exec-plans/active/harness-commander-v2/index.md`
- `docs/exec-plans/active/harness-commander-v2/phase2-host-model-path-planning.md`
- `docs/product-specs/v2/index.md`

### 验收标准

- Phase 2 主计划能指向本命令级 active plan。
- `distill` 的产品和协议文档能明确引用本计划作为当前收敛入口。
- 后续实现无需再依赖对话补充 `distill` Phase 2 的默认路径语义。

## Acceptance Criteria

- `distill` Phase 2 的默认入口、fallback / 状态语义、来源映射通过边界写成仓库事实源。
- 宿主模型参与后仍由 Harness 控制最终状态、产物路径和结构化结果合同。
- 后续实现可直接基于本计划展开，而不需要重新定义产品问题。

## Exception Handling

- 如果默认 host-first 与现有模式体系冲突，优先锁定用户可理解的模式语义，再决定是否保留旧模式作为兼容入口。
- 如果覆盖率阈值无法在本轮稳定定义，至少先写清 unmatched 对最终状态的影响范围。
- 如果某些 partial-success 场景会引入新的状态类型，必须先评估是否真的需要新增状态，而不是直接扩大结果模型。

## Verification

- 检查 `docs/product-specs/v2/index.md` 是否与 `distill` 命令文档对齐。
- 检查 `docs/product-specs/v2/commands/distill/product.md` 与 `protocol.md` 是否对同一组 Phase 2 问题给出一致口径。
- 检查主计划与本命令级计划之间不存在范围漂移。

## References

- `AGENTS.md`
- `docs/QUALITY_SCORE.md`
- `docs/RELIABILITY.md`
- `docs/design-docs/harness-engineering.md`
- `docs/exec-plans/active/harness-commander-v2/phase2-host-model-path-planning.md`
- `docs/product-specs/v2/index.md`
- `docs/product-specs/v2/commands/distill/product.md`
- `docs/product-specs/v2/commands/distill/protocol.md`
