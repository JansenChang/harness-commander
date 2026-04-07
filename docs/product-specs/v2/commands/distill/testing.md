# V2 `distill` 测试定义

## 当前状态

- active（Phase 1）

## 测试目标

- 验证 `distill` 在保留既有模式和 fallback 语义的前提下，新增来源映射与 extraction report。
- 验证 `unmatched` 语义稳定，不伪造来源定位。
- 验证 `*-llms.txt` 产物包含来源映射区块。

## 分层策略

- CLI 测试：
  - 校验新增 `meta` 字段结构
  - 校验 heuristic / host-model / auto 下来源映射语义
  - 校验 fallback 兼容字段未回归
- Integration 测试：
  - 校验真实文件提炼后的映射覆盖统计
  - 校验 host-model 失败回退路径下报告一致性
  - 校验真实 failure / edge path 下稳定错误协议不漂移
  - 校验输出参考材料中的来源映射区块

## Phase 1 必测场景

### heuristic 场景

- 输入含明确 section 文本时：
  - `section_sources` 存在且有可定位项
  - `source_mapping_coverage.total_items > 0`
  - `extraction_report.mapping_summary` 与 coverage 一致

### host-model / auto 场景

- host-model 成功时：
  - 结果包含 `extraction_report`
  - 允许出现 `unmatched`，但不得伪造来源位置
- auto fallback 时：
  - 保留 `fallback_from=host-model`
  - 来源映射字段仍存在且结构完整

### 不足提炼场景

- `distillation_insufficient` 时：
  - 仍返回来源映射结构（可为空或 unmatched）
  - 不改变既有 failure 判定语义
  - integration 层也必须锁住该 failure 结果，不只在 CLI 层断言
  - 不生成正式 `*-llms.txt` artifact，也不真实落盘

### provider / mode 边界场景

- `host-model` 缺少 provider 时：
  - 返回 `provider_not_configured`
  - integration 层必须验证真实入口链路下错误码和 message 稳定
- 若后续补 `invalid_distill_mode`：
  - CLI 与 integration 都要共享同一份 failure 事实，不允许只测一层

## 兼容性断言

- 保留并继续断言：
  - `distill_mode`
  - `extraction_source`
  - `fallback_from`
  - `fallback_reason`
- 新字段与既有字段语义一致，不冲突。

## 非目标测试

- 本轮不测试增量 distill。
- 本轮不测试跨文件聚合提炼。
- 本轮不测试宿主模型默认优先主路径。
