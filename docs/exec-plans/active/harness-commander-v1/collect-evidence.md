# `collect-evidence` 执行计划

## Goal

让 `harness collect-evidence` 成为宿主工具在关键节点自动调用的统一证据留痕入口。

## Scope

- 执行事实记录
- 结构化证据字段统一
- 失败证据与关键日志保留
- 自动调用与统一结果输出

## ULW

- `EVID-ULW-1`：在关键节点记录执行事实
- `EVID-ULW-2`：统一结构化证据字段
- `EVID-ULW-3`：保留失败证据与关键日志片段
- `EVID-ULW-4`：供宿主工具自动调用并返回统一结果

## 宿主模型参与

- 当前默认不接宿主模型。
- 未来最多允许补充更易读摘要，但不得改变原始事实。

## References

- `docs/product-specs/v1/commands/collect-evidence/product.md`
- `docs/product-specs/v1/commands/collect-evidence/protocol.md`
- `docs/product-specs/v1/commands/collect-evidence/acceptance.md`
