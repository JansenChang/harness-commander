# 2026-04-08 Harness-Commander V2 Phase 1 最小闭环归档记录

## 背景

- 本轮工作围绕 V2 当前 active backlog，持续收敛 `run-agents`、`check`、`distill` 的最小闭环。
- 代码、测试和产品/协议文档已经对齐到 deterministic baseline：
  - `run-agents` 具备阶段合同与 `check` 前置门
  - `check` 具备治理入口元数据与下一步动作建议
  - `distill` 具备来源映射、fallback 事实和 summary / artifact / meta 一致性
- 本地全量验证已达到 `84 passed`。

## 本次归档动作

- 复制 `docs/exec-plans/active/harness-commander-v2/` 下当前命令级执行计划快照到：
  - `docs/exec-plans/completed/2026-04-08-harness-commander-v2-phase1-archive/`
- 更新 V2 顶层产品导航、Roadmap 和 active 索引，把当前阶段明确切到：
  - “V2 Phase 1 最小闭环已完成”
  - “后续 Phase 2 / Phase 3 需单独重开 active 计划”
- 保留 active 索引作为下一轮入口说明，而不再把当前切片描述为待实现任务。

## 本次归档对象

- `run-agents-stage-contracts.md`
- `run-agents-check-preflight.md`
- `check-governance-entry.md`
- `check-ready-integration-coverage.md`
- `distill-source-mapping.md`
- `distill-integration-failure-coverage.md`
- `product-planning.md`

对应快照目录：

- `docs/exec-plans/completed/2026-04-08-harness-commander-v2-phase1-archive/`

## 当前状态结论

- V2 Phase 1 的最小闭环已经完成，并有代码、测试和文档事实源支撑。
- 当前完成范围是：
  - `run-agents + check + distill` 的 deterministic baseline
  - 治理前置门、阶段合同、来源映射和关键失败路径覆盖
- 当前未完成范围仍然存在，但已明确属于下一轮，而不是本轮遗留缺陷：
  - 宿主模型默认优先主路径
  - 更强的前置门 / 自动消费
  - 并发 runtime、恢复 / 重试 token、provider 生命周期扩展

## 当前验证快照

- 本地 `pytest`：`84 passed`
- `run-agents`：
  - 已补齐 `check` preflight 三态覆盖
  - 已补齐显式 `--plan` 覆盖默认 active 缺失的 override 语义
  - 已补齐 verify / pr-summary 阻断与 fallback 语义
- `check`：
  - 已补齐 blocking / warning / ready 三态
  - 已补齐治理入口结果协议与 `next_actions`
- `distill`：
  - 已补齐 `extraction_report`、`section_sources`、`source_mapping_coverage`
  - 已补齐 failure / fallback / dry-run / partial 场景下的结果一致性

## 下一步

- 若继续推进 V2，应新开 active 计划进入 Phase 2：
  - `distill` / `run-agents` 默认优先宿主模型，失败 fallback
- 若继续推进治理链路，应新开 active 计划进入更强的 `run-agents` / `check` 联动硬化
- 当前这批 Phase 1 计划不再视为进行中任务入口
