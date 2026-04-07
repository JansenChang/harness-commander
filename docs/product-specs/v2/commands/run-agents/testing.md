# V2 `run-agents` 测试定义

## 当前状态

- active（Phase 1）

## 测试目标

- 验证 `run-agents` 阶段合同字段稳定可断言。
- 保证在新增 `meta.stage_contracts` 的同时保持 `meta.agent_runs` 兼容。
- 覆盖成功、失败、阻断、fallback 四类关键语义。

## 分层策略

- CLI 测试：
  - 校验参数与结果合同字段
  - 校验缺失输入时的稳定失败码
  - 校验 verify 阻断与 dry-run 语义
- Integration 测试：
  - 校验真实落盘行为与路径冲突避让
  - 校验 verify 文件存在性与状态驱动的阶段变化
  - 校验 fallback 文案与结构化字段一致

## Phase 1 必测场景

### 成功路径

- verify 为 PASS 时：
  - 命令结果 `status=success`
  - 存在 `pr-summary` 阶段
  - `meta.stage_contracts` 与 `meta.agent_runs` 阶段列表一致

### 失败路径

- spec 缺失：
  - `status=failure`
  - `errors[].code=spec_not_found`
- plan 缺失：
  - `status=failure`
  - `errors[].code=plan_not_found`
- plan 校验失败：
  - `status=failure`
  - 具备稳定校验错误码（如 `missing_section` / `missing_reference`）

### 阻断路径

- verify 文件缺失：
  - `status=warning`
  - `warnings[].code=verify_not_ready_for_pr`
  - 无 `pr-summary` 产物
- verify 非 PASS：
  - `status=warning`
  - 阶段合同显示 verify 阻断命中
  - 无 `pr-summary` 产物

### fallback 路径

- verify 为 PASS 但 summary 缺失或为空：
  - `status=success`
  - `pr-summary` 可生成
  - 摘要中包含 fallback 提示
  - 阶段合同记录 fallback 事实

## 兼容性断言

- 保留 `meta.agent_runs` 字段，不改变其基本结构。
- 新增结构化阶段合同字段必须与旧字段可交叉验证，不允许语义冲突。

## 非目标测试

- 本轮不测试并发 agent runtime。
- 本轮不测试宿主模型主路径。
- 本轮不测试 `check` / `distill` 的联动编排。
