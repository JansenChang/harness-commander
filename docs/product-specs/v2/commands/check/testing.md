# V2 `check` 测试定义

## 当前状态

- active（Phase 1）

## 测试目标

- 验证 `check` 在保留既有审计字段的前提下，新增治理入口决策字段。
- 验证 `health_score`、`governance_entry`、`next_actions` 在 blocking / warning / ready 三类场景的稳定语义。
- 确保 deterministic baseline：测试不依赖宿主模型。

## 分层策略

- CLI 测试：
  - 校验新增元数据结构与核心语义
  - 校验兼容字段未回归
  - 校验 blocking 场景下下一步动作优先级
- Integration 测试：
  - 校验实际项目结构下的入口判定
  - 校验 warning-only 场景和默认目标缺失场景
  - 校验结果摘要与元数据一致

## Phase 1 必测场景

### 阻断场景

- 存在阻断项（例如敏感信息暴露）时：
  - `status=failure`
  - `governance_entry.status=blocked`
  - `ready_for_run_agents=false`
  - `next_actions` 首项为阻断修复动作

### warning-only 场景

- 无阻断但有提醒项时：
  - `status=warning`
  - `governance_entry.status=needs_attention`
  - `next_actions` 先返回优先整改建议
  - 若 `ready_for_run_agents=true`，`next_actions` 末项追加显式推进动作

### ready 场景

- 无阻断且无提醒时：
  - `status=success`
  - `governance_entry.status=ready`
  - `ready_for_run_agents=true`

### 默认目标缺失场景

- 缺失 active 计划或生成材料时：
  - 保持 warning 语义
  - `next_actions` 包含补齐默认目标建议

## 兼容性断言

- 保留 `blocking_count`、`warning_count`、`checks`、`checked_targets`。
- 新增字段和旧字段指向同一事实，不允许冲突。
- `summary` 文本必须能解释 `governance_entry.status`。

## 非目标测试

- 本轮不测试宿主模型判定。
- 本轮不测试 `check` 自动触发 `run-agents`。
- 本轮不测试大规模新增扫描域。
