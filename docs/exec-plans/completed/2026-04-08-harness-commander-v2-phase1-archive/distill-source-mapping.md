# Harness-Commander V2 `distill` 来源映射执行计划

## Goal

把 V2 `distill` 从“一次性压缩工具”推进到“可追踪的知识蒸馏入口”的第一轮可执行版本，为每次提炼结果补齐来源映射与 extraction report，同时保持现有 heuristic / host-model / auto 兼容。

## Context

- V2 已确认 `distill` 是第一批必须完成的宿主模型能力之一。
- 当前 `distill` 已支持 heuristic / host-model / auto，也已有 fallback 事实，但仍缺来源可追踪能力。
- 现有结果只能看到提炼结果，不容易回答“这条规则从哪来、哪些 section 是缺失还是匹配失败”。
- 本轮仍保持 deterministic baseline，不做增量更新和更大 schema 扩展。

## Business Logic

- 当前最重要的不是扩更多提炼模式，而是让现有结果可追溯、可复核。
- 本轮优先回答三件事：
  - 每个 section 提炼到了什么
  - 这些条目大致来自源文档哪里
  - 哪些 section 缺失、fallback、无法映射
- 结果协议和输出参考材料都应暴露这层事实。

## Scope

- 为 `distill` 增加 extraction report
- 为四类 section 增加来源映射
- 在生成的 `*-llms.txt` 中补最小来源映射块
- 更新 V2 `distill` 的产品、协议、测试、验收文档

## Non-Goals

- 不实现增量 distill
- 不改变四类 section 模型（`goals` / `rules` / `limits` / `prohibitions`）
- 不引入跨文件聚合提炼
- 不让宿主模型决定最终状态、目标路径或 fallback 语义

## ULW 1: 锁定 extraction report 协议

### 目标

- 明确 `distill` 每次执行至少返回哪些提炼报告字段。

### 涉及范围

- `docs/product-specs/v2/commands/distill/product.md`
- `docs/product-specs/v2/commands/distill/protocol.md`
- `src/harness_commander/application/commands.py`

### 验收标准

- `meta` 至少新增：
  - `extraction_report`
  - `section_sources`
  - `source_mapping_coverage`
- `extraction_report` 至少能说明：
  - section 计数
  - unresolved section
  - 使用的提炼来源
  - fallback 是否发生

## ULW 2: 给四类 section 补来源映射

### 目标

- 让提炼结果不再只是摘要文本，而是可追溯到输入材料。

### 涉及范围

- `src/harness_commander/application/commands.py`
- `tests/test_cli.py`
- `tests/test_integration.py`

### 验收标准

- heuristic 模式下，若能在源文档定位到条目，返回稳定的行号或位置映射。
- host-model / auto 模式下，若无法直接定位，必须明确标记未映射，而不是伪造行号。
- 生成的参考材料包含最小来源映射块。

## ULW 3: 保持 fallback 与兼容语义

### 目标

- 在增强来源可追踪性的同时，不破坏现有 distill 结果和 fallback 语义。

### 涉及范围

- `tests/test_cli.py`
- `tests/test_integration.py`
- `docs/product-specs/v2/commands/distill/testing.md`
- `docs/product-specs/v2/commands/distill/acceptance.md`

### 验收标准

- 继续保留：
  - `distill_mode`
  - `extraction_source`
  - `fallback_from`
  - `fallback_reason`
- success / warning / failure 语义不回归。
- 现有 host-model / auto fallback 测试继续通过。

## ULW 4: 为后续增量与 schema 扩展留扩展位

### 目标

- 让当前来源映射协议可以被下一轮增量 distill 或更复杂输入继续复用。

### 涉及范围

- `docs/exec-plans/active/harness-commander-v2/product-planning.md`
- `docs/exec-plans/tech-debt-tracker.md`
- `docs/design-docs/distill-host-model-contract.md`

### 验收标准

- 当前协议不假设只有 heuristic 模式才有来源映射。
- 若 host-model 输出无法映射，协议允许显式保留 unmatched 状态。
- 下一轮若扩展 chunk / 引用来源，不需要推翻本轮字段。

## Acceptance Criteria

- `distill` 结果中存在稳定 extraction report。
- 生成的参考材料包含最小来源映射信息。
- 现有 fallback 和兼容字段保持不变。
- 文档、代码、测试同步更新。

## Exception Handling

- 如果条目无法稳定映射到源文档，必须返回 `unmatched`，不能伪造位置。
- 如果映射信息不完整，不应改变主结果状态；除非提炼本身已不足以成立。
- 如果来源映射会破坏已有 `*-llms.txt` 可读性，优先追加区块而不是重排主体内容。

## Verification

- 运行 `pytest tests/test_cli.py tests/test_integration.py -k distill`
- 检查 heuristic / host-model / auto 三类路径的 `extraction_report`
- 检查生成的 `*-llms.txt` 是否包含来源映射块

## References

- `AGENTS.md`
- `ARCHITECTURE.md`
- `docs/PLANS.md`
- `docs/QUALITY_SCORE.md`
- `docs/RELIABILITY.md`
- `docs/design-docs/distill-host-model-contract.md`
- `docs/product-specs/v2/index.md`
- `docs/product-specs/v2/commands/distill/product.md`
