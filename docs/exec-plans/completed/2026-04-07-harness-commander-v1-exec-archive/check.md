# `check` 执行计划

## Goal

让 `harness check` 在 V1 中输出稳定、可复用的审计结果，而不是强门禁。

## Scope

- 规则加载
- 默认对象检查
- 审计结果和处理建议输出
- 未量化规则标记

## ULW

- `CHECK-ULW-1`：加载质量、安全、设计信仰与产品相关规则
- `CHECK-ULW-2`：默认检查计划文件与生成文档
- `CHECK-ULW-3`：输出分层审计结果与处理建议
- `CHECK-ULW-4`：对未量化规则标记为“未量化”

## 宿主模型参与

- 当前默认不接宿主模型。
- 未来仅允许辅助摘要与建议文案。

## References

- `docs/product-specs/v1/commands/check/product.md`
- `docs/product-specs/v1/commands/check/protocol.md`
- `docs/product-specs/v1/commands/check/acceptance.md`
