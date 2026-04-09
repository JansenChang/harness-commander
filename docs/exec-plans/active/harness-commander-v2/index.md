# Harness-Commander V2 Active 执行计划索引

## 说明

- 本目录用于承载 V2 的进行中执行计划。
- 当前 V2 已完成 Phase 2 的首批命令级实现切片归档。
- 在下一轮范围未重新立项前，不直接扩大运行时范围。

## 当前状态

- 状态：phase2-implementation-slice-archived-awaiting-next-scope
- 当前主计划：待下一轮范围选择（参考 `phase2-host-model-path-planning.md`）
- 当前命令级 active plans：
  - 无
- 当前阶段：V2 Phase 1 已归档；Phase 2 首批 implementation slice 已归档，等待下一轮范围选择
- 当前子状态：
  - `run-agents`：implementation-slice-archived
  - `distill`：implementation-slice-archived

## 产品开发进度

- 已完成：
  - V2 Phase 1 最小闭环归档
  - Phase 2 顶层主计划
  - Phase 2 命令级计划拆解
  - `application-commands-refactor.md` 的结构治理与测试验证
  - `run-agents` Phase 2 默认入口、结构化摘要合同与 fallback 状态矩阵收敛
  - `run-agents` Phase 2 实现切片文档收敛为“四槽位协作 + Harness 独占 check/pr-summary”
  - `run-agents` Phase 2 四槽位实现、CLI / integration 补洞与回归验证
  - `distill` Phase 2 默认 `auto`、fallback 留痕、CLI / integration 补洞与回归验证
  - `run-agents` / `distill` Phase 2 implementation slice 归档
- 正在推进：
  - 产品缺陷重审与下一轮范围选择
- 尚未开始：
  - 下一条命令级 active plan

## 当前归档摘要

- `run-agents` 继续使用固定阶段顺序：`check -> requirements -> plan -> implement -> verify -> pr-summary`
- Phase 2 当前实现切片把 `requirements`、`plan`、`implement`、`verify` 定义为四个协作槽位
- `check` 与 `pr-summary` 继续由 Harness 独占，不进入宿主模型路径
- Phase 2 最小闭环里仅 `requirements` 与 `plan` 评估 host-first；`implement` 与 `verify` 仍消费本地可验证事实
- verify 缺失或非 PASS 时必须阻断 `pr-summary`
- verification summary 缺失时允许 `pr-summary` 走 placeholder fallback，但必须留下结构化 fallback 事实
- `distill` 默认入口已切到 `auto`
- `distill auto` 在 provider 可用时优先宿主模型，provider 缺失或 host 失败时回退 heuristic
- `distill` 继续保留 `heuristic` / `host-model` 兼容入口，并由 Harness 控制最终状态、产物路径和来源映射合同

## 下一步

- 重新审视产品缺陷，并只选择一条下一轮范围
- 若进入新一轮，再新开 active plan
- 更大的宿主模型编排、恢复机制与更细粒度引用系统，均不在当前已归档切片内

## 计划入口

- 已完成归档记录：`docs/exec-plans/completed/2026-04-08-harness-commander-v2-phase1-archive.md`
- 已归档快照目录：`docs/exec-plans/completed/2026-04-08-harness-commander-v2-phase1-archive/`
- 当前 Phase 2 归档记录：`docs/exec-plans/completed/2026-04-08-harness-commander-v2-phase2-implementation-slice-archive.md`
- 当前 Phase 2 归档快照：`docs/exec-plans/completed/2026-04-08-harness-commander-v2-phase2-implementation-slice-archive/`
- Phase 2 主计划参考：`phase2-host-model-path-planning.md`
- `run-agents` 命令级计划参考：`run-agents-host-model-phase2-contracts.md`
- `run-agents` 测试定义：`docs/product-specs/v2/commands/run-agents/testing.md`
- `run-agents` 验收定义：`docs/product-specs/v2/commands/run-agents/acceptance.md`
- `distill` 命令级计划参考：`distill-host-first-phase2-contracts.md`

## 历史说明

- 当前目录仍保留部分已完成计划副本，便于对照，但它们不再代表当前 active backlog。
- Phase 1 与当前 Phase 2 implementation slice 的正式归档事实源均以 `docs/exec-plans/completed/` 下对应归档记录与快照目录为准。
