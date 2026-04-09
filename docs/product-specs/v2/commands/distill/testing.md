# V2 `distill` 测试定义

## 当前状态

- active（Phase 2 implementation slice）

## 测试目标

- 验证 `distill` 默认入口已切到 `auto`
- 验证 `auto` 在 provider 可用时优先宿主模型
- 验证 `auto` 在 provider 缺失或宿主模型结果不可用时稳定 fallback
- 验证显式 `heuristic` / `host-model` 兼容入口不回归
- 验证来源映射、summary、artifact、fallback 事实保持一致

## 分层策略

- CLI 测试：
  - 锁默认 `auto` 的成功路径与 fallback 路径
  - 锁显式 `heuristic` 的 deterministic baseline
  - 锁显式 `host-model` 的 provider 边界
  - 锁 `execution_path` / `host_attempted` / `host_first` 留痕
- Integration 测试：
  - 锁真实入口链路下默认 `auto` 的 provider 读取与 baseline 降级
  - 锁 `distillation_insufficient` 的真实 failure 协议
  - 锁 dry-run / artifact / summary 一致性
  - 锁 `*-llms.txt` 中来源映射区块仍可读

## 必测场景

### 默认 `auto`

- provider 可用时：
  - `meta.distill_mode = auto`
  - `meta.extraction_source = host-model`
  - `fallback_from = null`
  - `execution_path = host-model`
- provider 缺失时：
  - `meta.distill_mode = auto`
  - `meta.extraction_source = heuristic`
  - `fallback_from = host-model`
  - `fallback_reason = provider_not_configured`
  - `execution_path = heuristic_fallback`
  - 命令级至少为 `warning`
- 宿主模型失败或结构不完整时：
  - 继续回退到 heuristic
  - warning 与 meta fallback 事实一致

### 显式兼容入口

- `--mode heuristic`：
  - 继续返回 heuristic 提炼结果
  - 来源映射与 coverage 语义不回归
- `--mode host-model`：
  - provider 可用时成功
  - provider 缺失时稳定 `failure`

### 失败与产物

- `distillation_insufficient`：
  - 命令 `failure`
  - 结构化映射字段仍存在
  - 无正式 artifact 落盘
- dry-run：
  - `artifacts` 返回 `would_create` / `would_overwrite`
  - `summary` 不伪造正式写入

## 非目标测试

- 本轮不测试增量 distill
- 本轮不测试跨文件聚合提炼
- 本轮不测试 chunk 级来源引用系统
