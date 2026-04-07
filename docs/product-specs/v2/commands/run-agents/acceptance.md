# V2 `run-agents` 验收定义

## 当前状态

- active（Phase 1）

## 验收范围

- 仅验收 V2 第一轮实现切片：
  - `check` preflight 治理前置门
  - 阶段合同字段落地
  - deterministic baseline
  - verify 阻断与 fallback 语义
- 不验收并发 runtime 与宿主模型主路径。

## 验收前提

- 仓库具备最小治理文档。
- 输入 spec 与 active plan 可被正常解析。
- 运行入口：`harness run-agents --json ...`

## 验收标准

### AC1 preflight 门禁生效

- `check` 阶段必须在 `requirements` 之前执行并写入结果。
- `check.failure` 必须阻断后续阶段，命令结果为 `failure`。
- `check.warning` 必须允许继续进入后续阶段，并留下结构化 warning 留痕。
- `check.success` 必须正常继续。

### AC2 阶段合同字段完整

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

### AC3 兼容性保持

- `meta.agent_runs` 仍然存在并可读。
- 新旧字段描述同一执行事实，无冲突。

### AC4 verify 门禁有效

- verify 缺失或非 PASS 时：
  - 命令结果必须是 `warning`
  - 必须阻断 `pr-summary`
  - 必须给出稳定 warning code

### AC5 fallback 可追踪

- verify summary 缺失时：
  - 不得伪造完整验证摘要
  - 必须出现 fallback 文案或结构化 fallback 标记

### AC6 宿主模型边界符合阶段策略

- Phase 1 中 `host_model_allowed` 应为 `false`（全部阶段）。
- 不允许模型接管 verify / 阻断判断 / 最终状态 / 产物路径。

## 验收步骤（最小闭环）

1. 执行 success 场景，确认 `pr-summary` 生成与阶段合同完整。
2. 执行 `check=failure` 场景，确认 preflight 阻断后续阶段。
3. 执行 `check=warning` 场景，确认继续执行且 warning 留痕。
4. 执行 verify 缺失场景，确认阻断 `pr-summary` 与 warning。
5. 执行 verify 非 PASS 场景，确认阻断 `pr-summary` 与 warning。
6. 执行 verify summary 缺失场景，确认 fallback 事实。
7. 比对 `meta.agent_runs` 与 `meta.stage_contracts` 阶段一致性。

## 判定规则

- 任一 AC 不满足，则本轮 `run-agents` Phase 1 验收不通过。
- 仅当所有 AC 通过，且结果语义与测试文档一致，才可进入下一轮扩展（强前置门评估、`distill` 接入或宿主模型启用评估）。
