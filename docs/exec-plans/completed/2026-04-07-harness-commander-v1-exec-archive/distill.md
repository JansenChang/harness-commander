# `distill` 执行计划

## Goal

让 `harness distill` 把长材料稳定压缩成不误导 AI 的轻量参考资产。

## Scope

- 输入材料类型识别
- 四类核心信息提炼
- 标准化 `*-llms.txt` 生成
- 摘要、警告和结构化结果输出

## ULW

- `DISTILL-ULW-1`：识别输入材料类型与压缩目标
- `DISTILL-ULW-2`：提炼业务目标、关键规则、边界限制和禁止项
- `DISTILL-ULW-3`：生成标准化 `*-llms.txt` 参考材料
- `DISTILL-ULW-4`：输出摘要、警告和结构化结果

## 宿主模型参与

- 当前已实现可选 `host-model` / `auto` 增强路径。
- 输出模板、落盘目录、结果字段和 fallback 语义由 Harness 统一控制。

## References

- `docs/product-specs/v1/commands/distill/product.md`
- `docs/product-specs/v1/commands/distill/protocol.md`
- `docs/product-specs/v1/commands/distill/acceptance.md`
