# Harness Engineering

## 这个文件是做什么的

用于把 Harness-Commander 在本仓库中的工程协作方式固定下来，作为 `AGENTS.md` 之外的正式方法论文档。

## 核心原则

- `AGENTS.md` 只负责导航，不承载全部规则。
- `docs/` 才是系统事实源；规则、设计、产品、质量、可靠性都必须回写到仓库。
- 每次重要变更都应该同时更新：
  - 代码
  - 测试
  - 对应文档
- AI / Codex 的错误不是私有记忆，必须变成：
  - 测试
  - 规则
  - 台账

## 文档分工

- `AGENTS.md`
  - 入口、角色、阅读顺序、行为边界
- `docs/product-specs/`
  - 产品、协议、测试、验收
- `docs/design-docs/`
  - 长期有效的设计决策、模型边界、工程原则
- `docs/references/*-llms.txt`
  - 给 AI / 宿主模型读的轻量参考材料
- `docs/exec-plans/active/`
  - 当前进行中的执行计划
- `docs/exec-plans/completed/`
  - 已完成计划与阶段归档
- `docs/exec-plans/tech-debt-tracker.md`
  - 技术债、AI 失误、临时方案与防复发台账

## 工作流

### 1. 启动任务前

- 先读 `AGENTS.md`
- 再读相关 `docs/`
- 如果缺少规则源，先补文档，再写代码

### 2. 实现时

- 代码、测试、文档必须同步推进
- 不允许只在对话里定义新规则
- 不允许为了通过测试伪造成功语义

### 3. 收尾时

- 更新对应事实源文档
- 如果有 AI / Codex 失误或临时修补，写入技术债台账
- 如果阶段结束，迁移 active 计划到 completed

## 多 agent 原则

- 主 agent 负责：
  - 读取事实源
  - 做最终决策
  - 整合结果
  - 落代码或落文档
- 子 agent 负责：
  - 有边界的信息收集或专项分析
- 在产品审视阶段，优先开：
  - 产品缺陷分析 agent
  - 实现影响分析 agent
- 在问题尚未定型前，不优先开纯编码 agent。

## 版本策略

- `V1` 是已实现基线，不因 `V2` 启动而删除。
- `V2` 在结构上可与 `V1` 同构，但内容定位应是草案与问题驱动分析，而不是旧实现的复制品。
- 新一轮 active plan 必须建立在新版本产品问题陈述之上，而不是延续上一轮硬化任务。

## 质量与可靠性联动

- 质量要求看 `docs/QUALITY_SCORE.md`
- 可靠性要求看 `docs/RELIABILITY.md`
- 两者不是补充材料，而是 AI / Codex 的强制约束

## References

- `AGENTS.md`
- `docs/QUALITY_SCORE.md`
- `docs/RELIABILITY.md`
- `docs/exec-plans/tech-debt-tracker.md`
- [OpenAI Harness Engineering](https://openai.com/zh-Hans-CN/index/harness-engineering/)
