# `plan-check` 执行计划

## Goal

让 `harness plan-check` 成为计划进入实现前的稳定校验入口。

## Scope

- 计划结构完整性检查
- 治理文档引用完整性检查
- 问题列表和修复建议输出

## ULW

- `PC-ULW-1`：识别计划结构缺失项
- `PC-ULW-2`：校验治理文档引用完整性
- `PC-ULW-3`：输出问题列表与修复建议

## 宿主模型参与

- 当前默认不接宿主模型。
- 未来仅允许辅助摘要或修复建议。

## References

- `docs/product-specs/v1/commands/plan-check/product.md`
- `docs/product-specs/v1/commands/plan-check/protocol.md`
- `docs/product-specs/v1/commands/plan-check/acceptance.md`
