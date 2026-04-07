# `harness check` 验收标准

- 成功路径：无阻断项时返回 `success` 或 `warning`，输出规则来源、严重级别、文件位置和处理建议
- 失败路径：根目录不存在、关键治理文档缺失、检测到阻断性安全或质量问题时失败
- 默认行为：V1 默认对象为 `docs/exec-plans/active/` 下的计划文件，以及 `docs/generated/`、`docs/references/` 下的生成文档
- 宿主模型边界：严重级别、规则来源和状态判断由 Harness 决定
