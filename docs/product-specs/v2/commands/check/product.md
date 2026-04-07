# V2 `check` 产品定义

## 当前状态

- active（V2 第一轮实现中）

## V2 定位

- `check` 不是 V2 第一优先级命令。
- 它在 V2 中的正式定位是治理完整性入口，为 `run-agents` 提供前置门与下一步决策输入。
- 当前实现切片目标不是扩扫描器，而是把结果协议升级成可执行决策输入。
- 当前不把它列入默认优先宿主模型命令。

## 当前实现切片（Phase 1）

- 保留 V1 既有审计能力：
  - 规则源存在性与可量化性检查
  - 阻断项 / 提醒项分层
  - 默认检查对象识别
- 在结果层新增治理入口能力：
  - `health_score`
  - `governance_entry`
  - `next_actions`

## deterministic baseline（本轮约束）

- 默认不依赖宿主模型进行评分或判定。
- 健康度是启发式指标，不能覆盖 blocking / warning 的真实结果。
- 保持现有兼容字段不变：
  - `blocking_count`
  - `warning_count`
  - `checks`
  - `checked_targets`

## 本轮要解决的问题

- `check` 结果需要直接回答三件事：
  - 当前健康度如何
  - 是否可继续进入 `run-agents`
  - 下一步优先动作是什么
- 让 `check` 从“发现问题”升级为“可执行治理入口”。

## V2 继承的边界

- 继续由 Harness 控制最终状态。
- 规则来源、严重级别、位置、建议动作继续结构化输出。
- 不以健康度替代阻断事实。

## 与 active exec plan 对齐

- 当前执行计划：`docs/exec-plans/active/harness-commander-v2/check-governance-entry.md`
- 对齐 ULW：
  - ULW 1：锁定治理入口结果协议
  - ULW 2：把问题清单转成下一步动作输入
  - ULW 3：保持兼容并补齐覆盖
  - ULW 4：为后续接入 `run-agents` / `distill` 留扩展位

## 当前非目标

- 不并入 `run-agents` 自动执行
- 不扩展为大型知识库漂移扫描
- 不引入宿主模型判断
- 不重写现有扫描规则

## 当前开放问题

- `check` 在下一轮是否应成为 `run-agents` 的强前置门，而不是建议入口？
- `health_score` 后续是否需要按规则域分段（质量 / 安全 / 文档治理）？
- `next_actions` 是否需要标准化成可直接被其他命令消费的任务包？
