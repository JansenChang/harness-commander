# Harness-Commander V2 `distill` Phase 2 宿主模型主路径合同规划

## Goal

为 `distill` 的 Phase 2 锁定默认入口、provider prerequisite、fallback 语义与来源映射边界，使其能够从 Phase 1 的 deterministic baseline 稳定过渡到“默认优先宿主模型，失败 fallback”。

## Context

- V2 Phase 1 已完成并归档：
  - `distill` 来源映射结果协议
  - integration failure coverage
  - `*-llms.txt` 追加来源映射区块
- 当前 Phase 2 主计划已确认：
  - `distill` 是第一批必须进入宿主模型主路径的命令之一
  - 最终状态、目标路径、fallback 事实与结构化来源映射继续由 Harness 控制
- 当前命令文档已列出核心问题，但还没有命令级 active plan 来收敛 host-first 合同。

## Scope

- 锁定 Phase 2 默认入口是 `auto`、host-first，还是新的显式模式
- 锁定 provider 缺失、模型失败、输出不足时的 fallback 语义
- 锁定来源映射覆盖不足时的 success / warning / failure 边界
- 同步 `product.md` / `protocol.md` / `testing.md` / `acceptance.md` 的 Phase 2 输入

## Non-Goals

- 不实现增量 distill
- 不实现跨文件聚合提炼
- 不升级到 chunk 级来源映射
- 不改变四类基础 section 模型
- 不直接进入代码实现

## ULW 1: 锁定默认入口与模式兼容语义

### 目标

- 明确 `distill` 在 Phase 2 里如何从 Phase 1 的多模式入口过渡到默认优先宿主模型入口。

### 涉及范围

- `docs/product-specs/v2/commands/distill/product.md`
- `docs/product-specs/v2/commands/distill/protocol.md`
- `docs/product-specs/v2/commands/distill/acceptance.md`

### 验收标准

- 明确默认入口是继续复用 `auto`、切成 host-first 语义，还是新增显式模式
- 明确 CLI 默认行为与现有 `heuristic` / `host-model` / `auto` 的兼容边界
- 明确 provider prerequisite 是否成为进入默认主路径的硬条件

## ULW 2: 锁定宿主模型失败与 fallback 矩阵

### 目标

- 明确 `distill` 在 provider 缺失、超时、空结果、结构化解析失败时，是直接失败还是回退到 heuristic。

### 涉及范围

- `docs/product-specs/v2/commands/distill/protocol.md`
- `docs/product-specs/v2/commands/distill/testing.md`
- `docs/product-specs/v2/commands/distill/acceptance.md`

### 验收标准

- 定义至少以下场景的最终状态与 fallback 事实：
  - provider 缺失
  - provider 调用超时
  - 宿主模型返回空提炼结果
  - 宿主模型返回结构不完整
  - 宿主模型失败后 heuristic fallback 成功
  - 宿主模型失败后 heuristic fallback 仍不足
- 明确 `summary` / `meta` / `artifacts` 在上述场景下必须保持同一份事实
- 明确 failure 路径不得落盘正式 `*-llms.txt`

## ULW 3: 锁定来源映射覆盖率与通过边界

### 目标

- 明确宿主模型主路径下，来源映射不足是继续沿用 `unmatched`，还是引入新的 warning / failure 阈值。

### 涉及范围

- `docs/product-specs/v2/commands/distill/product.md`
- `docs/product-specs/v2/commands/distill/protocol.md`
- `docs/product-specs/v2/commands/distill/testing.md`

### 验收标准

- 明确 partial host-model output 在什么条件下仍可视为 `success`
- 明确来源映射覆盖不足时是 `success`、`warning` 还是 `failure`
- 明确 `section_sources` / `source_mapping_coverage` 的结构化合同在 fallback 后仍保持兼容

## ULW 4: 同步命令级文档与导航入口

### 目标

- 让仓库能清楚反映 `distill` 已进入命令级 Phase 2 合同规划，而不是只停留在总计划问题列表。

### 涉及范围

- `docs/exec-plans/active/harness-commander-v2/index.md`
- `docs/exec-plans/active/harness-commander-v2/phase2-host-model-path-planning.md`
- `docs/product-specs/v2/index.md`

### 验收标准

- active index 能直接定位到本命令级 active plan
- 主计划明确本文件是 `distill` 的命令级拆解入口
- V2 顶层导航能说明 `distill` Phase 2 已从“总规划”进入“命令级合同规划”

## Acceptance Criteria

- `distill` Phase 2 的产品问题被收敛为可执行的命令级合同计划。
- 后续实现团队不需要再靠对话判断“provider 缺失该失败还是回退”“映射覆盖不足算不算通过”。
- 宿主模型参与后的稳定事实边界继续由 Harness 控制，并写成仓库事实源。

## Verification

- 检查 `distill` 的 `product.md` / `protocol.md` / `testing.md` / `acceptance.md` 是否都获得了明确的 Phase 2 输入
- 检查 active index 与 Phase 2 主计划是否都能导航到本计划
- 检查是否仍存在“CLI 层模式已定义，但宿主模型失败路径与映射不足语义未定义”的空洞

## References

- `AGENTS.md`
- `docs/design-docs/harness-engineering.md`
- `docs/product-specs/v2/commands/distill/product.md`
- `docs/product-specs/v2/commands/distill/protocol.md`
- `docs/exec-plans/active/harness-commander-v2/phase2-host-model-path-planning.md`
