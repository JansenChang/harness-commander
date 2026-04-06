# `harness plan-check` 验收标准

- 成功路径：对结构完整、引用齐全、ULW 合格的计划文件返回成功
- 失败路径：缺少 Goal、Business Logic、Acceptance Criteria、Exception Handling、Verification 或必需引用时失败
- 默认行为：相对路径按 `root` 解析，不写入文件
- 宿主模型边界：最终通过/失败不能交给宿主模型决定
