# Harness-Commander V2 Phase 2 宿主模型主路径产品规划

## Goal

为 V2 Phase 2 建立清晰、可执行的产品规划，定义 `run-agents` 与 `distill` 如何进入“默认优先宿主模型，失败 fallback”模式，同时保持 Harness 对最终状态、阻断逻辑与产物事实的控制权。

## Context

- V2 Phase 1 已完成并归档：
  - `run-agents + check + distill` 最小闭环
  - deterministic baseline
  - 关键失败路径与结果协议收敛
- `docs/product-specs/v2/index.md` 已明确：
  - Phase 2 目标是让 `distill` 与 `run-agents` 进入默认优先宿主模型主路径
  - `run-agents` 只开放 `requirements` 与 `plan` 给宿主模型
- 当前仓库还没有把 Phase 2 的产品范围、输入输出、fallback 语义与非目标统一写成 active plan。

## Business Logic

- Phase 2 不是“把模型接进去”这么简单，而是要先回答三个产品问题：
  - 默认优先宿主模型的入口条件是什么
  - fallback 发生时哪些事实必须稳定保留
  - `run-agents` / `distill` 的宿主模型输出应以什么结构被 Harness 消费
- 本轮先做产品规划，不直接进入实现。
- 只有在产品边界写清之后，后续实现才不会把宿主模型接入做成协议漂移或状态漂移。

## 当前收敛的产品问题

### `run-agents`

- 问题 1：默认走宿主模型的入口条件是什么
  - 是只要 provider 已配置就默认进入，还是仍需额外 Phase 2 开关
- 问题 2：`requirements` / `plan` 输出需要保持摘要级，还是升级为可重放任务包
  - 这是产品/协议问题，不是单纯实现细节
- 问题 3：宿主模型失败、超时、结构不完整时，阶段级 fallback 与命令级状态如何组合
  - 这决定调用方如何理解“模型失败但命令继续成功”

### `distill`

- 已锁定 1：Phase 2 默认入口直接复用现有 `auto`
- 已锁定 2：provider 缺失时默认入口回退到 heuristic，而不是直接 failure
- 已锁定 3：当前切片不新增 coverage threshold，继续沿用 unmatched 兼容语义

## Scope

- 明确 `run-agents` Phase 2 的宿主模型主路径范围
- 明确 `distill` Phase 2 的默认模式与 fallback 语义
- 明确哪些能力继续永不交给宿主模型
- 明确 Phase 2 的最小闭环与非目标
- 为命令级 Phase 2 active plans 提供输入

## 已拆解的命令级 active plans

- `run-agents-host-model-phase2-contracts.md`
  - 收敛 `requirements` / `plan` 的 host-first 启动条件、阶段合同与状态矩阵
- `distill-host-first-phase2-contracts.md`
  - 收敛默认入口、provider prerequisite、fallback 语义与来源映射通过边界
- 当前拆解顺序：
  - 先收敛 `run-agents`
  - 再收敛 `distill`

## Non-Goals

- 不实现宿主模型新 runtime
- 不修改现有命令代码
- 不引入并发 agent runtime
- 不在本轮扩 `check` 的宿主模型增强
- 不扩 `install-provider` 生命周期能力

## ULW 1: 锁定 `run-agents` Phase 2 边界

### 目标

- 明确 `run-agents` 在 Phase 2 中让宿主模型接管什么、不接管什么。

### 涉及范围

- `docs/product-specs/v2/commands/run-agents/product.md`
- `docs/product-specs/v2/commands/run-agents/protocol.md`

### 验收标准

- 明确 `requirements` / `plan` 是唯一允许默认优先宿主模型的阶段
- 明确宿主模型输出被 Harness 消费的最小结构
- 明确 fallback、verify、最终状态、blocking 逻辑仍由 Harness 控制

## ULW 2: 锁定 `distill` Phase 2 边界

### 目标

- 明确 `distill` 从多模式工具转向默认优先宿主模型入口时的产品边界。

### 涉及范围

- `docs/product-specs/v2/commands/distill/product.md`
- `docs/product-specs/v2/commands/distill/protocol.md`

### 验收标准

- 明确默认模式已从 `heuristic` 切到现有 `auto`
- 明确失败 fallback 时 artifact / summary / meta 的稳定要求
- 明确来源映射与 unmatched 语义在宿主模型主路径下如何保持兼容

## ULW 3: 更新 V2 顶层导航

### 目标

- 让仓库能反映“Phase 1 已归档，Phase 2 implementation slice 已启动”。

### 涉及范围

- `docs/exec-plans/active/harness-commander-v2/index.md`
- `docs/exec-plans/active/harness-commander-v2/product-planning.md`
- `docs/product-specs/v2/index.md`

### 验收标准

- active index 当前阶段切到 Phase 2 产品规划
- V2 顶层导航把 Phase 2 从“未开始”更新为“产品规划中”
- product planning 能解释为什么现在进入 Phase 2

## Acceptance Criteria

- Phase 2 的产品目标、最小闭环、宿主模型边界与非目标写成仓库事实源。
- `run-agents` 与 `distill` 的 Phase 2 规划已拆成命令级 active plans，并可继续推进命令级合同收敛。
- 不需要再靠对话补充 Phase 2 基本边界。

## Exception Handling

- 如果发现当前顶层产品决策与命令级文档冲突，优先在本轮收敛文档，而不是直接开实现。
- 如果 `run-agents` 与 `distill` 对宿主模型主路径的目标节奏不一致，优先明确先后顺序和最小闭环，而不是同时扩大范围。

## Verification

- 检查 `docs/product-specs/v2/index.md` 与命令级产品文档是否对齐
- 检查 active index 是否已从 Phase 1 完成态切换为 Phase 2 规划态
- 检查是否仍存在“宿主模型默认优先”只在对话里、未写入仓库的问题

## References

- `AGENTS.md`
- `docs/product-specs/v2/index.md`
- `docs/product-specs/v2/commands/run-agents/product.md`
- `docs/product-specs/v2/commands/distill/product.md`
- `docs/design-docs/harness-engineering.md`
