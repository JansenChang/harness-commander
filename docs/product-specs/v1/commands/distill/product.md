# `harness distill` 产品定义

## 解决的问题

- 长文档、老代码和外部参考资料会占用过多上下文。
- 简单截断会丢失关键约束，误导 AI。

## 具体作用

- 将长材料压缩为 `*-llms.txt` 轻量参考材料。
- 保留业务目标、关键规则、边界限制和禁止项四类核心信息。
- 在节省上下文的同时优先保证约束完整性。

## 当前实现

- 默认模式为 `heuristic`。
- 支持可选 `host-model` 与 `auto` 模式。
- `distill` 在 `host-model` / `auto` 模式下默认读取项目已安装/已配置的 provider。
- `--provider` 仅作为当前命令的临时 override，不再是主路径。
- `distill` 是当前唯一已实现可选宿主模型增强的命令。

## 宿主模型边界

- 即使宿主模型参与，输出模板、目标路径、结果字段、warning/error 语义和 fallback 规则仍由 Harness 控制。

## 产物

- `docs/references/` 下的 `*-llms.txt` 文件。
