# V2 `distill` 产品定义

## 当前状态

- phase1-complete / phase2-planning

## V2 定位

- `distill` 是 V2 第一批必须完成的宿主模型能力之一。
- 当前切片目标是把它从“一次性压缩工具”推进到“可追踪知识蒸馏入口”。
- 本轮继续保持 deterministic baseline，不切宿主模型默认主路径。

## 当前实现切片（Phase 1）

- 保持现有模式：`heuristic` / `host-model` / `auto`。
- 保持四类提炼模型：`goals` / `rules` / `limits` / `prohibitions`。
- 在结果协议中新增：
  - `extraction_report`
  - `section_sources`
  - `source_mapping_coverage`
- 在 `*-llms.txt` 中追加最小来源映射区块，不重排主体内容。
- `distillation_insufficient` 时：
  - 保留失败结果与来源映射元数据
  - 不生成正式 `*-llms.txt` 产物

## deterministic baseline（本轮约束）

- 宿主模型不决定最终状态、目标路径和 fallback 语义。
- 来源映射优先“可解释、可复核”，不追求一次性完整覆盖。
- 条目无法可靠定位时必须标记 `unmatched`，不能伪造来源位置。
- `health` 或评分类字段不是本轮目标，不替代原有 warning / failure 语义。
- 失败状态不能继续落盘正式参考材料，否则会与结果语义漂移。

## 本轮要解决的问题

- 让提炼结果能回答“条目从哪里来”。
- 让 unresolved section 与 fallback 事实具备统一报告结构。
- 让下游 agent 能消费提炼结果和来源映射，而不只读纯文本摘要。

## Phase 2 当前规划方向

- 后续会评估把默认入口从 `heuristic` 推进到“默认优先宿主模型，失败 fallback”。
- 即使进入 host-first 主路径，Harness 仍然控制：
  - 最终状态
  - 目标路径
  - fallback 事实
  - 来源映射结构
- 当前 Phase 2 仍处于产品规划中，未进入实现。

## 与 active exec plan 对齐

- Phase 1 已归档：
  - `docs/exec-plans/completed/2026-04-08-harness-commander-v2-phase1-archive/distill-source-mapping.md`
  - `docs/exec-plans/completed/2026-04-08-harness-commander-v2-phase1-archive/distill-integration-failure-coverage.md`
- 当前 Phase 2 主计划：
  - `docs/exec-plans/active/harness-commander-v2/phase2-host-model-path-planning.md`
- 对齐 ULW：
  - ULW 1：锁定 extraction report 协议
  - ULW 2：四类 section 来源映射
  - ULW 3：保持 fallback 与兼容语义
  - ULW 4：为增量与 schema 扩展留扩展位

## 当前非目标

- 不实现增量 distill。
- 不引入跨文件聚合提炼。
- 不改变四类 section 基础模型。
- 不切换到宿主模型默认优先主路径。

## 当前开放问题

- 来源映射后续是否需要升级到 chunk 级而不只是行号/位置级？
- `next` 阶段是否要把 `section_sources` 输出标准化为可重放任务包？
- 增量 distill 时如何处理历史映射失效和冲突合并？
