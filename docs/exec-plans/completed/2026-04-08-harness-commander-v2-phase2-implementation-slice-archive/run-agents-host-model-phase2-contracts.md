# Harness-Commander V2 `run-agents` Phase 2 宿主模型合同与实现切片

## Goal

把 `run-agents` 从“Phase 2 产品合同已收敛”推进到“可直接进入编码的实现切片”，固定四槽位协作边界、Harness 独占阶段、最小闭环、非目标和测试矩阵。

## Context

- V2 Phase 1 已完成并归档：
  - `run-agents` 已具备 `check -> requirements -> plan -> implement -> verify -> pr-summary` 的阶段合同基线
  - `check` preflight、verify 阻断与最终状态语义已收敛
- V2 Phase 2 已锁定的产品事实：
  - `requirements` 与 `plan` 是唯一允许评估 host-first 的阶段
  - `check`、最终状态、阻断逻辑、产物路径继续由 Harness 控制
  - `pr-summary` 不进入宿主模型路径
  - `requirements` / `plan` 输出继续保持结构化摘要，不升级为可重放任务包
- 当前缺口已经不是产品是否成立，而是实现切片还未压缩到可执行最小闭环。

## Slice Decision

- 固定阶段顺序仍为：`check -> requirements -> plan -> implement -> verify -> pr-summary`
- 当前实现切片采用“四槽位协作 + Harness 独占两端”的模型：
  - Harness 独占：`check`、`pr-summary`
  - 协作槽位：`requirements`、`plan`、`implement`、`verify`
- “协作槽位”不等于“都允许宿主模型”：
  - `requirements`：允许评估 host-first
  - `plan`：允许评估 host-first
  - `implement`：协作槽位，但本切片不引入 host-model 主路径
  - `verify`：协作槽位，但 verify 结论仍由 Harness 根据本地验证事实写入
- 最小闭环不新增 CLI 模式门，不扩并发 runtime，不扩 docs 阶段。

## Minimal Closed Loop

### 输入

- spec 文档
- active exec plan 文档
- provider eligibility 结果
- 本地 verify 文件：
  - `.claude/tmp/last-verify.status`
  - `.claude/tmp/verification-summary.md`

### 输出

- 兼容字段：`meta.agent_runs`
- 结构化字段：`meta.stage_contracts`
- 产物：
  - verify 通过时生成 `docs/generated/pr-summary/*.md`
  - verify 未通过时不生成 `pr-summary`

### 阻断条件

- `check.failure` 或 `check` 结果缺少必要治理字段：命令级 `failure`
- spec 缺失：命令级 `failure`
- plan 缺失或治理校验失败：命令级 `failure`
- verify 缺失或非 PASS：命令级 `warning`，并阻断 `pr-summary`

### fallback

- `requirements` / `plan`
  - provider 缺失、运行时不可用、超时、空结果、结构不完整：
    - 回退到 deterministic 路径
    - 阶段至少 `warning`
    - 命令最终至少 `warning`
  - provider 被策略禁用：
    - 不尝试 host path
    - 直接走 deterministic 路径
    - 阶段可保持 `success`，但必须留下按策略跳过 host path 的事实
- `verify`
  - verify 结论本身不走宿主模型 fallback
  - verify 缺失或非 PASS 不是“继续生成 PR 摘要”，而是显式阻断
- `pr-summary`
  - 只有 `verification summary` 缺失或为空时允许 placeholder fallback
  - fallback 只能补摘要文案，不能伪造 verify 已通过的事实

## Scope

- 把 `run-agents` 固定为六阶段编排，其中四个阶段作为协作槽位对外呈现
- 明确 `check` / `pr-summary` 的 Harness 独占边界
- 明确 `requirements` / `plan` 的 host-first 启动条件与 fallback 语义
- 明确 verify 阻断与 `pr-summary` fallback 的命令级状态矩阵
- 为 CLI、integration、acceptance 提供统一测试入口

## Non-Goals

- 不引入并发 agent runtime
- 不引入 resume token / attempt 序号 / 自动重试
- 不新增 `docs` 阶段
- 不把 `implement` / `verify` 切到宿主模型主路径
- 不让宿主模型接管 `check`、verify 判定、`pr-summary`、最终状态、阻断逻辑或产物路径
- 不接入 `distill` 联动编排
- 不修改 `run-agents` CLI 入口形态

## 槽位边界

### `check`（Harness 独占）

- 位置：固定第一阶段
- 责任：preflight、治理完整性入口、阻断前置门
- host-model：禁止
- 失败语义：
  - `failure`：命令立即失败
  - `warning`：命令继续，但必须在最终结果中保留 warning 事实

### `requirements`（协作槽位 1）

- 责任：从 spec 生成 requirements 摘要
- host-model：允许评估 host-first
- 产物：无正式文件产物
- fallback：
  - host-path 失败后回退 deterministic
  - 必须保留 provider、尝试事实、fallback 原因和最终执行路径

### `plan`（协作槽位 2）

- 责任：从 active plan 生成 plan 摘要并承接治理校验结果
- host-model：允许评估 host-first
- 产物：无正式文件产物
- fallback：与 `requirements` 同口径

### `implement`（协作槽位 3）

- 责任：形成实施摘要与交接上下文
- host-model：本切片禁止
- 产物：无正式文件产物
- 说明：这是协作槽位，但当前仍以本地结构化事实为准，不扩新的模型入口

### `verify`（协作槽位 4）

- 责任：消费本地 verify 文件并写出阶段合同
- host-model：本切片禁止
- 阻断：
  - verify 缺失
  - verify 非 PASS
- 说明：`verify` 作为协作槽位出现，但 verify 结论、阻断判断和命令级状态仍由 Harness 写入

### `pr-summary`（Harness 独占）

- 位置：固定末阶段
- 进入条件：`verify.status == success`
- host-model：禁止
- 产物：`docs/generated/pr-summary/*.md`
- fallback：
  - 仅允许 verification summary 缺失时使用 placeholder 文案
  - 不允许越过 verify 阻断直接生成

## 状态矩阵

- `check.failure` 或 `check` 治理字段缺失：
  - 命令 `failure`
  - 四个协作槽位均不进入
- `check.warning` 且其余阶段全部成功：
  - 命令至少 `warning`
  - `pr-summary` 可生成
- `requirements` / `plan` host-path 成功：
  - 对应阶段 `success`
- `requirements` / `plan` provider 被策略禁用且 deterministic 成功：
  - 对应阶段 `success`
  - 必须保留 skipped-host-path 事实
- `requirements` / `plan` provider 缺失、运行时不可用、超时、空结果或结构不完整，但 deterministic fallback 成功：
  - 对应阶段 `warning`
  - 命令最终至少 `warning`
- `requirements` / `plan` host-path 失败且 deterministic fallback 也无法满足最小合同：
  - 对应阶段 `failure`
  - 命令 `failure`
- verify 缺失或非 PASS：
  - `verify` 阶段 `warning`
  - `pr-summary` 阶段 `warning`
  - 命令 `warning`
- verify 为 PASS，但 verification summary 缺失或为空：
  - `verify` 阶段 `success`
  - `pr-summary` 阶段 `success`
  - `pr-summary.fallback.applied=true`

## ULW 1：固定阶段 ownership 与四槽位模型

### 目标

- 把“哪些阶段是协作槽位，哪些阶段由 Harness 独占”写成实现前事实源。

### 涉及范围

- `docs/exec-plans/active/harness-commander-v2/index.md`
- `docs/product-specs/v2/commands/run-agents/testing.md`
- `docs/product-specs/v2/commands/run-agents/acceptance.md`

### 验收标准

- 文档明确四个协作槽位是 `requirements` / `plan` / `implement` / `verify`
- 文档明确 `check` / `pr-summary` 由 Harness 独占
- 文档明确“协作槽位”与“允许宿主模型”不是同一概念

## ULW 2：锁定最小闭环与 host-first 边界

### 目标

- 让实现只围绕最小闭环落地，不把 Phase 2 扩写成新的 runtime。

### 涉及范围

- `docs/exec-plans/active/harness-commander-v2/run-agents-host-model-phase2-contracts.md`
- `docs/product-specs/v2/commands/run-agents/testing.md`
- `docs/product-specs/v2/commands/run-agents/acceptance.md`

### 验收标准

- 明确最小闭环输入、输出、阻断条件、fallback
- 明确 `requirements` / `plan` 是唯一评估 host-first 的槽位
- 明确 `implement` / `verify` 在本切片不引入宿主模型主路径

## ULW 3：锁定 verify 阻断与 `pr-summary` fallback 语义

### 目标

- 让 verify 相关 warning、阻断和 fallback 能被稳定测试和验收。

### 涉及范围

- `docs/product-specs/v2/commands/run-agents/testing.md`
- `docs/product-specs/v2/commands/run-agents/acceptance.md`
- `docs/RELIABILITY.md`

### 验收标准

- verify 缺失或非 PASS 时，`pr-summary` 必须被阻断
- verification summary 缺失时，只允许 placeholder fallback，不允许伪造 verify 成功来源
- 命令级 `success` / `warning` / `failure` 与阶段级状态矩阵对齐

## ULW 4：形成实现测试矩阵

### 目标

- 把 CLI、integration、acceptance 需要覆盖的关键场景压缩成可执行清单。

### 涉及范围

- `docs/product-specs/v2/commands/run-agents/testing.md`
- `docs/product-specs/v2/commands/run-agents/acceptance.md`

### 验收标准

- 至少覆盖 1 条成功路径、1 条主要失败路径、1 条边界 / fallback 路径
- 明确 ownership、host fallback、verify 阻断、`pr-summary` fallback 的测试断言
- 测试矩阵能直接指导 `tests/test_cli.py` 与 `tests/test_integration.py` 补洞

## Acceptance Criteria

- 当前 active plan 已明确实现切片，而不是只停留在产品合同讨论
- `run-agents` 的最小闭环、非目标、状态矩阵和测试入口在仓库内可导航
- 实现阶段无需再重新定义“四槽位协作 + Harness 独占 check/pr-summary”的边界

## 当前落实状态

- 已锁定：
  - `requirements` / `plan` 是唯一允许进入宿主模型主路径的阶段
  - 默认不新增新的 CLI 模式门，先按 provider eligibility 评估 host-first
  - provider 缺失或运行时不可用时走 deterministic fallback，并升级为显式退化语义
  - provider 被策略禁用时不尝试 host path，但必须结构化留痕
  - Phase 2 继续保持结构化摘要合同，不升级为可重放任务包
  - 当前实现切片收敛为四槽位协作，`check` / `pr-summary` 继续由 Harness 独占
- 已回写：
  - `docs/exec-plans/active/harness-commander-v2/index.md`
  - `docs/product-specs/v2/commands/run-agents/testing.md`
  - `docs/product-specs/v2/commands/run-agents/acceptance.md`
- 下一步：
  - 执行最小 acceptance 闭环，确认实现与文档一致
  - 验收通过后归档本实现切片，并切换到下一条 Phase 2 backlog

## Exception Handling

- 如果实现发现 `implement` 或 `verify` 需要新的宿主模型合同，必须新开 active plan，不得悄悄扩写本切片。
- 如果阶段 ownership 需要新的协议字段表达，也应先补产品 / 协议文档，再改实现。
- 如果 verify fallback 语义与现有结果合同冲突，优先保留真实阻断事实，而不是保留看起来更“成功”的结果。

## Verification

- 检查 `docs/exec-plans/active/harness-commander-v2/index.md` 是否能准确导航到当前切片
- 检查 `docs/product-specs/v2/commands/run-agents/testing.md` 与 `acceptance.md` 是否采用同一组阶段边界
- 检查本计划没有把 `check` / `pr-summary` 错写成协作槽位
- 检查本计划没有把 `implement` / `verify` 错写成宿主模型主路径

## References

- `RULES.md`
- `AGENTS.md`
- `docs/QUALITY_SCORE.md`
- `docs/RELIABILITY.md`
- `docs/design-docs/harness-engineering.md`
- `docs/exec-plans/active/harness-commander-v2/phase2-host-model-path-planning.md`
- `docs/product-specs/v2/commands/run-agents/product.md`
- `docs/product-specs/v2/commands/run-agents/protocol.md`
