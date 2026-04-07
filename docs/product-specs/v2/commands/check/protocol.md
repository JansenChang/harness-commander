# V2 `check` 协议定义

## 当前状态

- active（Phase 1）

## 结果协议总览

- 保持现有兼容字段：
  - `blocking_count`
  - `warning_count`
  - `checks`
  - `checked_targets`
- 新增治理入口字段：
  - `health_score`
  - `governance_entry`
  - `next_actions`

## 新增字段定义

### `health_score`

- 类型：`number`（0-100）
- 含义：基于当前审计事实的启发式健康度
- 约束：
  - 不能覆盖真实 blocking / warning 事实
  - 只作为治理决策辅助指标

### `governance_entry`

- 类型：`object`
- 最小字段：
  - `status`: `blocked` / `needs_attention` / `ready`
  - `ready_for_run_agents`: `boolean`
  - `ready_for_clean_pass`: `boolean`
  - `recommended_entrypoint`: 推荐从哪个命令或动作进入下一步
  - `rationale`: 当前判定理由（可机器读）

### `next_actions`

- 类型：`array`
- 每项最小字段：
  - `priority`: 优先级（如 `P0` / `P1` / `P2`）
  - `code`: 动作码
  - `title`: 动作标题
  - `reason`: 动作触发原因
  - `suggestion`: 具体建议
- Phase 1 约束：
  - blocking 场景优先返回阻断修复动作
  - warning-only 且可继续时，除整改动作外还应追加显式推进动作
  - ready 场景返回 `proceed`

## 判定语义（Phase 1）

- `blocking_count > 0`：
  - `governance_entry.status = blocked`
  - `ready_for_run_agents = false`
- `blocking_count == 0 && warning_count > 0`：
  - `governance_entry.status = needs_attention`
  - `ready_for_run_agents` 取决于 active 计划和关键输入是否就绪
- `blocking_count == 0 && warning_count == 0`：
  - `governance_entry.status = ready`
  - `ready_for_run_agents = true`

## 兼容性要求

- 旧调用方依赖字段必须继续保留。
- 新字段作为附加，不替换已有审计明细。
- `summary` 与 `meta` 语义必须一致，不允许“摘要说可进，字段说不可进”。

## deterministic baseline

- 默认不依赖宿主模型做结果判断。
- 所有判定基于本地可验证事实：
  - 阻断项数量
  - 提醒项数量
  - 默认检查对象存在性

## 异常与边界处理

- 如果动作建议无法精确映射，返回保守动作（优先要求人工确认）。
- 如果健康度无法精确刻画风险，不降低阻断等级，不伪造 ready 状态。
- 新字段缺失时应回退到稳定默认值，而不是中断原有审计结果输出。
