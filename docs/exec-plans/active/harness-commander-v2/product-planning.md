# Harness-Commander V2 产品规划执行计划

## Goal

在不直接进入实现的前提下，完成 Harness-Commander V2 的产品问题收敛，明确最小闭环、宿主模型引入路径、阶段合同与非目标范围，为后续命令级执行计划提供稳定输入。

## Context

- V1 已完成主要命令落地与稳定性硬化，并已归档。
- V2 已建立与 V1 同构的产品文档骨架，并写入第一轮问题陈述。
- 当前团队目标不是继续滚动实现，而是先重新审视产品缺陷。
- 团队已确认：
  - V2 定位为工程治理系统
  - 第一优先级命令是 `run-agents`
  - 第一批宿主模型能力是 `distill` 与 `run-agents`
  - 当前阶段默认不依赖宿主模型，后续阶段才切到默认优先宿主模型并 fallback

## Scope

- 收敛 V2 的总问题陈述
- 收敛 `run-agents`、`distill`、`check`、`collect-evidence`、`install-provider` 的产品定位
- 锁定最小闭环
- 锁定宿主模型永不接管的能力
- 锁定 `run-agents` 的阶段合同字段清单
- 锁定当前不做的范围

## Non-Goals

- 不实现新命令
- 不改 runtime 代码
- 不扩展 provider 生命周期管理
- 不在本计划阶段引入并发 agent runtime

## ULW 1: 锁定 V2 总体产品方向

### 目标

- 把 V2 从“文档草案”推进为“可执行产品方向”。

### 涉及范围

- `docs/product-specs/v2/index.md`
- `docs/product-specs/index.md`

### 验收标准

- V2 的产品定位、最小闭环、阶段推进顺序、非目标范围明确可读
- 后续 agent 只读仓库即可知道 V2 当前阶段目标

## ULW 2: 锁定 run-agents 主入口地位与阶段合同

### 目标

- 明确 `run-agents` 为什么是 V2 第一优先级，以及它与其他命令的关系。

### 涉及范围

- `docs/product-specs/v2/commands/run-agents/product.md`
- `docs/product-specs/v2/commands/run-agents/protocol.md`

### 验收标准

- 明确每个阶段必须定义：
  - 输入
  - 输出
  - 阻断条件
  - fallback
  - 产物
  - 是否允许宿主模型参加
- 明确宿主模型只限 `requirements` 与 `plan`
- 明确 verify、最终状态、产物路径不交给宿主模型

## ULW 3: 锁定 distill / check / collect-evidence 的配角定位

### 目标

- 明确这些命令在最小闭环中承担什么，而不是继续各自独立生长。

### 涉及范围

- `docs/product-specs/v2/commands/distill/product.md`
- `docs/product-specs/v2/commands/check/product.md`
- `docs/product-specs/v2/commands/collect-evidence/product.md`
- `docs/product-specs/v2/commands/install-provider/product.md`

### 验收标准

- `distill` 明确是给下游大模型读取的参考材料入口
- `check` 明确是治理完整性入口
- `collect-evidence` 明确保持独立命令
- `install-provider` 明确不是本轮优先项

## ULW 4: 为命令级执行计划准备输入

### 目标

- 在进入实现前，生成足够稳定的产品输入。

### 涉及范围

- `docs/exec-plans/active/harness-commander-v2/`
- `docs/design-docs/harness-engineering.md`

### 验收标准

- 能从当前文档直接拆出下一轮命令级 active exec plans
- 不需要再靠口头补充解释 V2 当前方向

## Verification

- 检查 `docs/product-specs/v2/` 与 `docs/exec-plans/active/harness-commander-v2/` 是否对齐
- 检查最小闭环、宿主模型边界、非目标范围是否已落到仓库事实源
- 检查是否仍存在“对话中已确认、仓库中未记录”的关键产品决策

## 当前落实状态

- 已完成：
  - V2 总问题陈述
  - 宿主模型边界
  - 最小闭环和配角命令定位
  - `run-agents` 阶段合同基线
  - `check` 治理入口结果协议
  - `distill` 来源映射结果协议
  - `run-agents` 接入 `check` 治理前置门
  - `distill` integration failure / edge path 补洞
  - `check` ready integration 补洞
  - `distill` summary / artifact / meta 一致性补洞
  - `run-agents` 显式 `--plan` preflight override 覆盖
- 已归档：
  - V2 Phase 1 最小闭环归档：`docs/exec-plans/completed/2026-04-08-harness-commander-v2-phase1-archive.md`
- 已启动：
  - V2 Phase 2 宿主模型主路径产品规划：`phase2-host-model-path-planning.md`
  - `run-agents` Phase 2 命令级合同规划：`run-agents-host-model-phase2-contracts.md`
  - `distill` Phase 2 命令级合同规划：`distill-host-first-phase2-contracts.md`
- 当前选择：
  - 当前不继续补 Phase 1，而是进入 Phase 2 产品规划
  - 优先收敛 `run-agents` 与 `distill` 的“默认优先宿主模型，失败 fallback”边界
  - `check` 暂不进入宿主模型主路径，只保留后续评估入口

## References

- `AGENTS.md`
- `docs/PLANS.md`
- `docs/design-docs/harness-engineering.md`
- `docs/product-specs/v2/index.md`
- `docs/exec-plans/tech-debt-tracker.md`
