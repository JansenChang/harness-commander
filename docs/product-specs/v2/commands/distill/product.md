# V2 `distill` 产品定义

## 当前状态

- phase1-complete / phase2-implementation-slice

## V2 定位

- `distill` 是 V2 第一批必须进入宿主模型默认主路径的命令之一。
- 当前切片目标是把它从“可选宿主模型增强工具”推进到“默认优先宿主模型、失败回退本地提炼”的知识蒸馏入口。
- 本轮继续保持 Harness 对最终状态、产物路径、fallback 事实和来源映射结构的控制权。

## Phase 2 当前实现切片

- 不新增 CLI 模式，继续沿用：`heuristic` / `host-model` / `auto`。
- 默认入口切换为现有 `auto`：
  - provider 可用时，优先尝试宿主模型提炼。
  - provider 缺失时，不直接命令失败，回退到 heuristic baseline。
  - 宿主模型运行失败或返回结构不完整时，回退到 heuristic baseline。
- 显式兼容入口继续保留：
  - `heuristic`：强制本地规则提炼
  - `host-model`：强制尝试宿主模型入口；provider 缺失仍是显式 failure
- `unmatched` 与 `source_mapping_coverage` 继续保留现有 Phase 1 语义：
  - 不新增 coverage threshold
  - 不因为 unmatched 单独升级为 failure

## 默认入口语义

- 默认执行 `distill <source>` 等价于 `distill <source> --mode auto`。
- `auto` 在本轮是唯一的 host-first 入口。
- fallback 发生时必须显式留下：
  - `fallback_from`
  - `fallback_reason`
  - warning 事实
- fallback 不能伪装成完整成功；即使最终产物生成，结果也必须体现退化事实。

## Harness 控制边界

- 无论是否进入宿主模型路径，以下能力继续由 Harness 控制：
  - 最终 `success` / `warning` / `failure` 判定
  - 目标文件路径与写入行为
  - `fallback_from` / `fallback_reason`
  - `extraction_report`
  - `section_sources`
  - `source_mapping_coverage`
- 宿主模型只负责候选提炼内容，不负责：
  - 产物命名
  - 结果合同
  - 真实 fallback 留痕
  - unmatched 补造

## 当前非目标

- 不新增新的 `distill` CLI 参数或第四种模式
- 不实现增量 distill
- 不实现跨文件聚合提炼
- 不升级到 chunk 级引用系统
- 不把 coverage 变成新的命令级 gate

## 与 active exec plan 对齐

- Phase 1 已归档：
  - `docs/exec-plans/completed/2026-04-08-harness-commander-v2-phase1-archive/distill-source-mapping.md`
  - `docs/exec-plans/completed/2026-04-08-harness-commander-v2-phase1-archive/distill-integration-failure-coverage.md`
- Phase 2 主计划参考：
  - `docs/exec-plans/active/harness-commander-v2/phase2-host-model-path-planning.md`
- Phase 2 当前实现切片归档：
  - `docs/exec-plans/completed/2026-04-08-harness-commander-v2-phase2-implementation-slice-archive.md`
- Phase 2 命令级计划参考：
  - `docs/exec-plans/active/harness-commander-v2/distill-host-first-phase2-contracts.md`

## 当前开放问题

- 后续是否需要把 `section_sources` 升级为更细粒度引用，而不只是当前 line/unmatched 级别
- 增量 distill 时如何处理历史映射失效与合并冲突
