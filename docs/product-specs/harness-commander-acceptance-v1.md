# Harness-Commander 验收导航 V1

## 说明

- 命令级验收标准已按命令拆分维护。
- 本文件只保留全局验收规则和导航入口。

## 全局验收规则

- 所有命令都必须支持文本输出与 `--json`
- 文本输出与 JSON 输出必须表达同一份事实
- 写入型命令都必须支持 `--dry-run`
- 宿主模型只能参与认知型任务，命令语义、结果字段、产物路径和最终状态语义仍由 Harness 控制

## 命令验收入口

- `init`：`docs/product-specs/v1/commands/init/acceptance.md`
- `propose-plan`：`docs/product-specs/v1/commands/propose-plan/acceptance.md`
- `plan-check`：`docs/product-specs/v1/commands/plan-check/acceptance.md`
- `sync`：`docs/product-specs/v1/commands/sync/acceptance.md`
- `distill`：`docs/product-specs/v1/commands/distill/acceptance.md`
- `install-provider`：`docs/product-specs/v1/commands/install-provider/acceptance.md`
- `check`：`docs/product-specs/v1/commands/check/acceptance.md`
- `collect-evidence`：`docs/product-specs/v1/commands/collect-evidence/acceptance.md`
- `run-agents`：`docs/product-specs/v1/commands/run-agents/acceptance.md`
