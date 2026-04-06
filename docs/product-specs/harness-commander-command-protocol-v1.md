# Harness-Commander 命令协议导航 V1

## 说明

- 命令级协议不再集中维护在单个总表中。
- 当前入口按命令拆分，便于只修改一个命令时不影响其他命令上下文。
- 全局协议仍然固定：统一入口为 `harness <command> [options]`，统一 JSON 字段为 `command`、`status`、`summary`、`artifacts`、`warnings`、`errors`、`meta`。

## 命令协议入口

- `init`：`docs/product-specs/v1/commands/init/protocol.md`
- `propose-plan`：`docs/product-specs/v1/commands/propose-plan/protocol.md`
- `plan-check`：`docs/product-specs/v1/commands/plan-check/protocol.md`
- `sync`：`docs/product-specs/v1/commands/sync/protocol.md`
- `distill`：`docs/product-specs/v1/commands/distill/protocol.md`
- `check`：`docs/product-specs/v1/commands/check/protocol.md`
- `collect-evidence`：`docs/product-specs/v1/commands/collect-evidence/protocol.md`

## 全局约束

- 未传 `-p/--root` 时默认使用当前工作目录
- `success` / `warning` 的退出码为 `0`，`failure` 的退出码为 `1`
- 宿主模型只能参与被产品文档允许的认知型任务
