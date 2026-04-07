# `install-provider` 执行计划

## Goal

让 `harness install-provider` 在 V1 中稳定完成多宿主安装、配置落盘和权限失败回传，而不是只在理想环境下工作。

## Scope

- 多 provider 目标解析
- 用户级 / 项目级目录解析
- 安装结果与配置事实源统一
- 权限失败、不可写目录和 dry-run 语义收敛

## ULW

- `IP-ULW-1`：统一 `cursor`、`claude`、`codex`、`openclaw`、`trae`、`copilot`、`auto`、`all` 的目标解析
- `IP-ULW-2`：保证 `.harness/provider-config.json` 与真实安装结果一致
- `IP-ULW-3`：对真实用户目录写入失败、宿主未安装和目录不可解析返回稳定结果
- `IP-ULW-4`：补齐 dry-run、JSON 结果和打包验收覆盖

## 宿主模型参与

- 当前不接宿主模型。
- provider 选择、目录解析、安装结果和失败语义必须由 Harness 决定。

## References

- `docs/product-specs/v1/commands/install-provider/product.md`
- `docs/product-specs/v1/commands/install-provider/protocol.md`
- `docs/product-specs/v1/commands/install-provider/acceptance.md`
