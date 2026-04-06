# `harness propose-plan` 验收标准

- 成功路径：生成计划文件到 `docs/exec-plans/active/`，包含 Goal、Business Logic、Acceptance Criteria、Exception Handling、Verification 与 ULW
- 失败路径：核心治理文档缺失、需求为空或无法形成最小结构时失败
- `--dry-run`：展示将生成的计划产物但不写文件
- 宿主模型边界：未来可辅助需求整理和 ULW 拆分，但输出路径和结果字段必须由 Harness 保证
