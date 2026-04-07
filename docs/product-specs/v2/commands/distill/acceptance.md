# V2 `distill` 验收定义

## 当前状态

- active（Phase 1）

## 验收范围

- 仅验收本轮最小切片：
  - extraction report 落地
  - 四类 section 来源映射落地
  - unmatched 语义稳定
  - 兼容字段保持
- 不验收：
  - 增量 distill
  - 跨文件聚合提炼
  - 宿主模型默认优先主路径

## 验收标准

### AC1 新增报告字段完整

- 结果 `meta` 包含：
  - `extraction_report`
  - `section_sources`
  - `source_mapping_coverage`

### AC2 来源映射语义稳定

- 有可定位来源时：
  - 映射应包含位置或行号信息
- 无法可靠定位时：
  - 必须标记 `unmatched`
  - 不允许伪造来源位置

### AC3 fallback 与兼容语义不回归

- 继续保留：
  - `distill_mode`
  - `extraction_source`
  - `fallback_from`
  - `fallback_reason`
- auto fallback 场景下新字段仍完整返回。

### AC4 产物可读且包含来源映射块

- `docs/references/*-llms.txt` 继续可读。
- 产物中包含最小来源映射区块。

## 验收步骤（最小闭环）

1. 跑 heuristic 场景，验证映射命中和 coverage 统计。
2. 跑 host-model 成功场景，验证结构完整和 unmatched 语义。
3. 跑 auto fallback 场景，验证 fallback 与映射报告并存。
4. 检查 `*-llms.txt` 是否包含来源映射区块。

## 判定规则

- 任一 AC 不满足，则本轮 `distill` Phase 1 验收不通过。
- 所有 AC 满足后，才可进入下一轮：
  - 增量 distill
  - 更复杂来源 schema（如 chunk 级映射）
