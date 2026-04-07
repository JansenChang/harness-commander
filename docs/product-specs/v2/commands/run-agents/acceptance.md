# V2 `run-agents` 验收定义

## 当前状态

- active（Phase 1）

## 验收范围

- 仅验收 V2 第一轮实现切片：
  - 阶段合同字段落地
  - deterministic baseline
  - verify 阻断与 fallback 语义
- 不验收并发 runtime 与宿主模型主路径。

## 验收前提

- 仓库具备最小治理文档。
- 输入 spec 与 active plan 可被正常解析。
- 运行入口：`harness run-agents --json ...`

## 验收标准

### AC1 阶段合同字段完整

- `meta.stage_contracts` 存在且为数组。
- 每个阶段至少包含：
  - `stage`
  - `status`
  - `inputs`
  - `outputs`
  - `blocking_conditions`
  - `fallback`
  - `artifacts`
  - `host_model_allowed`

### AC2 兼容性保持

- `meta.agent_runs` 仍然存在并可读。
- 新旧字段描述同一执行事实，无冲突。

### AC3 verify 门禁有效

- verify 缺失或非 PASS 时：
  - 命令结果必须是 `warning`
  - 必须阻断 `pr-summary`
  - 必须给出稳定 warning code

### AC4 fallback 可追踪

- verify summary 缺失时：
  - 不得伪造完整验证摘要
  - 必须出现 fallback 文案或结构化 fallback 标记

### AC5 宿主模型边界符合阶段策略

- Phase 1 中 `host_model_allowed` 应为 `false`（全部阶段）。
- 不允许模型接管 verify / 阻断判断 / 最终状态 / 产物路径。

## 验收步骤（最小闭环）

1. 执行 success 场景，确认 `pr-summary` 生成与阶段合同完整。
2. 执行 verify 缺失场景，确认阻断与 warning。
3. 执行 verify 非 PASS 场景，确认阻断与 warning。
4. 执行 verify summary 缺失场景，确认 fallback 事实。
5. 比对 `meta.agent_runs` 与 `meta.stage_contracts` 阶段一致性。

## 判定规则

- 任一 AC 不满足，则本轮 `run-agents` Phase 1 验收不通过。
- 仅当所有 AC 通过，且结果语义与测试文档一致，才可进入下一轮扩展（`check` / `distill` 接入或宿主模型启用评估）。
