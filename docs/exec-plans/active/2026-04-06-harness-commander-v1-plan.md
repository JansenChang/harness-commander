# 2026-04-06 Harness-Commander V1 总计划

## Goal

- 基于按命令拆分的产品规格，推进 Harness-Commander V1 的后续实现与维护。
- 让产品文档、执行计划和上下文引用方式都与实际命令执行顺序一致。

## Context

- 当前活跃规格已改为 `docs/product-specs/v1/commands/` 按命令维护。
- 当前活跃计划已改为 `docs/exec-plans/active/harness-commander-v1/` 按命令维护。
- `init` 作为已实现基线保留，但不作为本轮主要扩写对象。

## 命令计划入口

- `propose-plan`：`docs/exec-plans/active/harness-commander-v1/propose-plan.md`
- `plan-check`：`docs/exec-plans/active/harness-commander-v1/plan-check.md`
- `sync`：`docs/exec-plans/active/harness-commander-v1/sync.md`
- `distill`：`docs/exec-plans/active/harness-commander-v1/distill.md`
- `check`：`docs/exec-plans/active/harness-commander-v1/check.md`
- `collect-evidence`：`docs/exec-plans/active/harness-commander-v1/collect-evidence.md`

## Cross-Cutting Rules

- 所有命令继续以仓库根目录为执行基准
- 所有命令必须同时支持文本输出和 `--json`
- 写入型命令必须支持 `--dry-run`
- 宿主模型只能参与产品规格允许的认知型任务

## Verification

- 计划与产品规格的命令边界必须一一对应
- 单独修改某个命令的计划时，不应影响其他命令计划正文
