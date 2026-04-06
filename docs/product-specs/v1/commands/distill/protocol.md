# `harness distill` 协议

| 项目 | 定义 |
| --- | --- |
| 命令 | `harness distill <file-or-range>... <instruction>` |
| 参数 | `-p, --root`；`<file-or-range>...`；`<instruction>`；`-o, --output`；`-i, --interactive`；`--dry-run` |
| 默认行为 | 调用宿主模型，对输入材料做蒸馏与结构化整理 |
| 输入单元 | 文件、文件片段（如 `path/to/file.py:10-80`）、用户说明 |
| 产物落点 | 用户指定输出，或默认写入 `.llms` 文件 / 目录 |
| JSON `meta` | `root`、`inputs`、`instruction`、`output_path`、`dry_run`、`interactive`、`source_types`、`distilled_unit_count`、`unresolved_inputs`、`unresolved_sections` |
| 宿主模型 | 默认参与，不要求用户传 `model` 参数 |
| Harness 职责 | 负责输入解析、调用宿主模型、产物落盘和结构化结果输出 |

## 输入语义

- `<file-or-range>` 支持一个或多个本地文件。
- `<file-or-range>` 也支持文件片段引用，例如 `api.py:20-80`。
- `<instruction>` 是用户给宿主模型的一段自然语言说明，用于表达蒸馏目标。
- 输入可以混合文档与源码，既可以引用整文件，也可以引用片段。

## 交互语义

- 默认情况下，用户只需要提供文件、片段和说明。
- `distill` 会优先由宿主模型推断摘要深度、关联关系、示例选择和 `.llms` 结构。
- 当信息不足或目标不够明确时，可通过 `--interactive` 进入多轮对话，逐步确定输出内容与格式。

## 产物语义

- 输出不是单一摘要，而是面向下游 LLM / Agent 的结构化上下文包。
- 产物中可以同时包含摘要、关键关系、代码示例、文档精华和 Agent 使用指引。
- `.llms` 默认定位为机器可读上下文资产，而不是静态展示文档。
