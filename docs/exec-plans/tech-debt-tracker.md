# 技术债与 AI 失误台账

## 这个文件是做什么的

用于记录系统中的技术债、临时方案、危险区域，以及 AI / Codex 已确认失误与防复发措施。

## 使用原则

- 这是事件台账，不是泛泛而谈的说明文档。
- 每一条记录都必须可追溯、可行动、可关闭。
- 任何已确认的 AI / Codex 失误，都必须记录到这里或某个完成归档文档中；默认优先记录到这里。

## 什么时候必须记录

- AI / Codex 误改了行为、协议、结果语义或产物路径
- 通过补丁修掉了 bug，但本质问题仍未彻底消失
- 需要暂时接受不理想实现
- 有已知危险区域，后续 agent 改动前必须先知道
- 新增了一条防复发规则，但它来源于真实事故或真实误修

## 记录模板

### [状态] 标题

- 日期：
- 类型：`tech-debt` / `ai-mistake` / `temporary-fix` / `danger-zone`
- 范围：
- 现象：
- 根因：
- 当前处理：
- 防复发：
- 关联测试：
- 关联文档：
- 关闭条件：

## 当前记录

### [open] install-provider 测试曾依赖真实用户目录

- 日期：2026-04-07
- 类型：`ai-mistake`
- 范围：`install-provider` CLI 测试、acceptance 环境隔离
- 现象：测试直接写入真实 `~/.claude/skills/...`，在当前环境下因权限问题失败。
- 根因：测试把宿主目录当作稳定环境，未通过 override 隔离到临时路径。
- 当前处理：已改为使用 `HARNESS_CLAUDE_SKILLS_DIR` 指向临时目录，并补充权限失败的稳定结果断言。
- 防复发：所有用户目录安装测试默认必须先注入临时 provider 目录，不允许触达真实宿主目录。
- 关联测试：`tests/test_cli.py`
- 关联文档：`docs/QUALITY_SCORE.md`、`docs/RELIABILITY.md`
- 关闭条件：后续 CI 与本地持续验证证明无再次触达真实用户目录的测试。

### [open] acceptance 曾受宿主 Python 环境影响

- 日期：2026-04-07
- 类型：`temporary-fix`
- 范围：editable install、packaging acceptance
- 现象：`pip install -e .` 在 externally-managed environment 下失败，导致 acceptance 全部报错。
- 根因：验收测试过度依赖宿主 Python / pip 环境，而不是在受控环境自举。
- 当前处理：已改为在临时虚拟环境中完成 editable install，并探测可导入 `setuptools.build_meta` 的 Python。
- 防复发：所有 packaging / 安装类 acceptance 默认在临时环境执行，不直接依赖宿主系统 Python。
- 关联测试：`tests/acceptance/test_packaging_and_skill.py`
- 关联文档：`docs/RELIABILITY.md`
- 关闭条件：后续若引入 CI，应把 acceptance 自举链路稳定跑通并固化为标准。

### [open] run-agents 已稳定但产品边界仍未复盘

- 日期：2026-04-07
- 类型：`tech-debt`
- 范围：`run-agents`、V2 产品规划
- 现象：执行层硬化已完成，但产品缺陷尚未系统梳理，继续编码容易在错误边界上优化局部行为。
- 根因：V1 主要聚焦命令落地与稳定性，尚未单独完成产品缺陷审视。
- 当前处理：已归档 V1 执行计划，暂停继续滚动实现。
- 防复发：下一轮必须先在 V2 文档中定义问题，再重开 active exec plan。
- 关联测试：`tests/test_cli.py`、`tests/test_integration.py`
- 关联文档：`docs/design-docs/harness-engineering.md`、`docs/PLANS.md`
- 关闭条件：V2 的问题陈述、边界和优先级文档完成并通过评审。

### [open] run-agents Phase 1 已有阶段合同，但 implement 仍是摘要承接

- 日期：2026-04-07
- 类型：`temporary-fix`
- 范围：`run-agents` V2 Phase 1、阶段合同协议
- 现象：`run-agents` 已输出结构化阶段合同，但 `implement` 阶段当前仍只承接 requirements / plan 摘要，不代表真正的可恢复执行 runtime。
- 根因：本轮优先目标是先锁 deterministic baseline 和阶段结果协议，而不是一次性引入并发、恢复、重试和真实 agent 执行器。
- 当前处理：已把阶段合同落入 `meta.stage_contracts`，并保持 `meta.agent_runs` 兼容；同时明确本轮不扩 runtime 范围。
- 防复发：后续若继续扩 `run-agents`，必须以当前阶段合同为基础演进，不允许再回到只靠自由文本摘要传递状态。
- 关联测试：`tests/test_cli.py`、`tests/test_integration.py`
- 关联文档：`docs/product-specs/v2/commands/run-agents/protocol.md`、`docs/exec-plans/active/harness-commander-v2/run-agents-stage-contracts.md`
- 关闭条件：`implement` / `docs` / 后续治理阶段进入真实可恢复 runtime，并沿用当前阶段合同协议。
