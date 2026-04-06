# `distill` 执行计划

## Goal

让 `harness distill` 从本地多源材料中默认调用宿主模型进行蒸馏，生成供下游 LLM / Agent 使用的 `.llms` 结构化上下文包。

## Scope

- 文件、文件片段和用户说明的输入解析
- 文档与源码混合输入的统一处理
- 宿主模型驱动的关联分析与关键知识单元提取
- 多轮对话收敛输出内容、参数选型和 `.llms` 结构
- `.llms` 文件或目录内容生成

## ULW

- `DISTILL-ULW-1`：解析文件、片段和说明，建立统一输入模型
- `DISTILL-ULW-2`：调用宿主模型分析跨文件关系、调用链和关键模式
- `DISTILL-ULW-3`：提取代码示例、文档精华和其他可复用知识单元
- `DISTILL-ULW-4`：在需要时通过多轮对话收敛输出格式与结构
- `DISTILL-ULW-5`：生成面向下游模型消费的 `.llms` 结构化上下文包

## 宿主模型参与

- `distill` 默认调用宿主模型，不要求用户显式传 `model` 参数。
- CLI 前期尽量少参数，主要由文件、片段和说明驱动蒸馏流程。
- 复杂输出要求通过后续对话收敛，而不是在初始命令中暴露大量 flags。

## References

- `docs/product-specs/v1/commands/distill/product.md`
- `docs/product-specs/v1/commands/distill/protocol.md`
- `docs/product-specs/v1/commands/distill/acceptance.md`
