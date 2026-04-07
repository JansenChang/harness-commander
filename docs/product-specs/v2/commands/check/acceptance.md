# V2 `check` 验收定义

## 当前状态

- active（Phase 1）

## 验收范围

- 仅验收本轮最小切片：
  - 治理入口元数据落地
  - 下一步动作建议可执行
  - 兼容字段保留
- 不验收：
  - 宿主模型判定
  - 大范围扫描扩展
  - `check` 自动并入 `run-agents`

## 验收标准

### AC1 新增治理入口字段

- 结果 `meta` 存在：
  - `health_score`
  - `governance_entry`
  - `next_actions`

### AC2 阻断语义稳定

- 存在阻断项时：
  - 命令状态为 `failure`
  - `governance_entry.status=blocked`
  - `ready_for_run_agents=false`

### AC3 warning 语义稳定

- 无阻断但存在提醒时：
  - 命令状态为 `warning`
  - `governance_entry.status=needs_attention`
  - `next_actions` 提供可执行整改方向

### AC4 ready 语义稳定

- 无阻断且无提醒时：
  - 命令状态为 `success`
  - `governance_entry.status=ready`
  - `ready_for_run_agents=true`

### AC5 兼容字段不回归

- 继续存在并可用：
  - `blocking_count`
  - `warning_count`
  - `checks`
  - `checked_targets`

## 验收步骤（最小闭环）

1. 制造阻断场景，验证 `blocked` 入口状态和阻断动作建议。
2. 制造 warning-only 场景，验证 `needs_attention` 和建议动作。
3. 在无问题场景下验证 `ready` 和 `ready_for_run_agents`。
4. 对比新增字段与旧字段，确认无语义冲突。

## 判定规则

- 任一 AC 不满足，则本轮 `check` Phase 1 验收不通过。
- 所有 AC 满足后，才可进入下一轮：
  - 评估 `check` 是否升级为 `run-agents` 强前置门
  - 或扩展扫描域与跨命令联动
