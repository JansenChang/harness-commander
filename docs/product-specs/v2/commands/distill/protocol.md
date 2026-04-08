# V2 `distill` 协议定义

## 当前状态

- phase1-complete / phase2-planning

## 结果协议总览

- 保持现有兼容字段：
  - `distill_mode`
  - `extraction_source`
  - `fallback_from`
  - `fallback_reason`
  - `extracted_section_count`
  - `unresolved_sections`
- 新增来源可追踪字段：
  - `extraction_report`
  - `section_sources`
  - `source_mapping_coverage`

## 新增字段定义

### `extraction_report`

- 类型：`object`
- 最小字段：
  - `sections`: 四类 section 的条目数摘要
  - `unresolved_sections`
  - `extraction_source`
  - `fallback`: 是否发生、来源与原因
  - `mapping_summary`: 映射命中统计

### `section_sources`

- 类型：`object`
- 键：`goals` / `rules` / `limits` / `prohibitions`
- 每个键的值：来源条目数组
- 每个来源条目最小字段：
  - `text`: 提炼出的条目文本
  - `mapping_status`: `mapped` / `unmatched`
  - `line`: 命中行号；未命中时为 `null`
  - `snippet`: 命中行的简短摘要；未命中时为 `null`
  - `mapping_strategy`: `heuristic` / `host-model`

### `source_mapping_coverage`

- 类型：`object`
- 最小字段：
  - `mapped_items`
  - `unmatched_items`
  - `total_items`
  - `coverage_ratio`
  - `mapped_ratio`

## 判定语义（Phase 1）

- heuristic 模式：
  - 能定位则输出 `mapped + line`
  - 不能定位则输出 `unmatched`
- host-model / auto 模式：
  - 不强制要求全部可定位
  - 不能可靠定位时必须显式 `unmatched`
- `unmatched` 不单独触发 failure；除非提炼本身已不足（沿用 `distillation_insufficient`）。
- `distillation_insufficient`：
  - 命令结果为 `failure`
  - `meta.extraction_report`、`meta.section_sources`、`meta.source_mapping_coverage` 仍需完整返回
  - `artifacts` 必须为空
  - 真实文件不得落盘到 `docs/references/*-llms.txt`

## 参考材料输出约束

- 生成的 `*-llms.txt` 需追加“来源映射”区块。
- 区块应包含：
  - 四类 section 的映射摘要
  - unmatched 条目统计
- 不应破坏现有参考材料主体结构。

## 兼容性要求

- 现有消费者依赖字段必须继续可用。
- 新字段作为附加，不替代现有 fallback 语义。
- `summary`、`warnings/errors`、`meta` 必须指向同一份事实。
- failure 路径下，文件产物事实也必须与结果一致，不能出现“failure 但已创建正式参考材料”。
- dry-run 路径下，`summary` 不得伪造“已创建正式参考材料”。

## deterministic baseline

- 不依赖宿主模型决定最终状态或产物路径。
- 映射不到来源时返回 `unmatched`，禁止伪造行号。
- 结果优先“可解释”而不是“映射覆盖率看起来更高”。

## Phase 2 当前规划问题

- 若默认入口从 `heuristic` 切到 host-first / auto：
  - provider 缺失时是否直接 failure，还是回退到 heuristic
  - host-model 输出不足但未完全失败时，是否允许直接通过
  - 来源映射覆盖不足时，是否需要引入新的通过阈值或继续沿用 `unmatched`
- 无论 Phase 2 如何推进，以下事实继续由 Harness 控制：
  - 最终状态
  - 目标路径
  - fallback 记录
  - `section_sources` / `source_mapping_coverage` 的结构化合同
