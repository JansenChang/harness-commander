# Harness-Commander V1 文档导航

## 说明

- 本目录按命令拆分维护 Harness-Commander V1 的产品、协议、测试与验收文档。
- 以后修改某一个命令时，优先只改该命令目录下的文档，避免影响其他命令上下文。
- 全局共性规则仍以 [ARCHITECTURE.md](../../../ARCHITECTURE.md)、[README.md](../../../README.md) 和 [docs/product-specs/index.md](../index.md) 为入口。

## 命令导航

- `init`：`commands/init/product.md` / `commands/init/protocol.md` / `commands/init/testing.md` / `commands/init/acceptance.md`
- `propose-plan`：`commands/propose-plan/product.md` / `commands/propose-plan/protocol.md` / `commands/propose-plan/testing.md` / `commands/propose-plan/acceptance.md`
- `plan-check`：`commands/plan-check/product.md` / `commands/plan-check/protocol.md` / `commands/plan-check/testing.md` / `commands/plan-check/acceptance.md`
- `sync`：`commands/sync/product.md` / `commands/sync/protocol.md` / `commands/sync/testing.md` / `commands/sync/acceptance.md`
- `distill`：`commands/distill/product.md` / `commands/distill/protocol.md` / `commands/distill/testing.md` / `commands/distill/acceptance.md`
- `check`：`commands/check/product.md` / `commands/check/protocol.md` / `commands/check/testing.md` / `commands/check/acceptance.md`
- `collect-evidence`：`commands/collect-evidence/product.md` / `commands/collect-evidence/protocol.md` / `commands/collect-evidence/testing.md` / `commands/collect-evidence/acceptance.md`

## 全局约束

- 命令入口固定为 `harness <command> [options]`
- 所有命令必须同时支持文本输出和 `--json`
- 写入型命令必须支持 `--dry-run`
- 宿主模型只能参与产品文档允许的认知型任务，不能接管结果字段、产物路径和最终状态
