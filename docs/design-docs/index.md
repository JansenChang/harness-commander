# 设计文档索引

## 这个文件是做什么的

用于汇总所有设计类文档，告诉团队和 AI 应该去哪里找到关键设计决策。

## 适合写什么

- 各设计文档的目录和链接
- 每篇文档的主题说明
- 哪些文档是当前有效版本
- 阅读顺序建议

## 推荐用法

- 把它当成设计知识库的首页
- 新增设计文档后，先更新这里再通知团队
- AI 在做较大改动前，先从这里找到相关设计依据

## 当前使用规则

- `design-docs/` 不是摆设；凡是涉及长期有效的设计决策，都不应只留在对话里。
- 应写入 `design-docs/` 的内容包括：
  - 技术原则和禁令
  - 模型参与边界
  - 文档组织与知识布局方式
  - 跨命令共享的设计决策
- 不应写入 `design-docs/` 的内容包括：
  - 单次任务执行记录
  - 纯临时 TODO
  - 只对单一 bug 生效的临时修补说明

## 当前建议阅读顺序

1. `core-beliefs.md`
2. 与当前改动相关的专题设计文档
3. 再进入 `docs/references/*-llms.txt` 阅读轻量 AI 参考材料

## 设计文档列表

- [Harness Engineering](harness-engineering.md)：定义本仓库的工程协作方法、文档分工、多 agent 原则和版本策略。
- [核心信念](core-beliefs.md)：团队坚持或禁止的技术原则
- [Init 模板规范](init-templates.md)：说明 `harness init` 所使用的包内模板资源结构与内容基线，约束初始化文档格式标准。
- [Distill 宿主模型契约](distill-host-model-contract.md)：定义 `distill` 在 `host-model` / `auto` 模式下的模型参与边界、结构化输出合同与 fallback 语义。
