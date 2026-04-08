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

### [open] 应用层命令已拆层，但 `run_agents` / `distill` handler 仍偏大

- 日期：2026-04-08
- 类型：`tech-debt`
- 范围：`src/harness_commander/application/command_handlers/run_agents.py`、`src/harness_commander/application/command_handlers/distill.py`
- 现象：`commands.py` 已从 2400+ 行拆为 façade，但为保持产品逻辑和测试 patch 点稳定，`run_agents` 与 `distill` 当前仍保留了较多协议构造与摘要辅助函数，模块体量仍偏大。
- 根因：本轮重构优先目标是消除单体入口和跨命令堆叠，而不是在同一轮同时重写 `run-agents` / `distill` 的内部协议构造结构。
- 当前处理：已把公共导出面收敛到 façade，并把命令实现迁入 `application/command_handlers/`；对更细粒度的二次拆分暂不继续推进，避免和 Phase 2 产品合同收敛互相干扰。
- 防复发：后续若继续改 `run-agents` / `distill`，优先把协议构造、摘要渲染、fallback / artifact 决策继续拆到各自私有 helper 模块，而不是再回堆到 façade 或继续扩单文件。
- 关联测试：`tests/test_cli.py`、`tests/test_integration.py`
- 关联文档：`docs/design-docs/application-command-development.md`、`docs/exec-plans/active/harness-commander-v2/application-commands-refactor.md`
- 关闭条件：`run_agents` / `distill` 进一步拆分为更小的私有模块，且不引入协议或测试 patch 漂移。

### [open] check ready 语义曾缺少 integration 防回归测试

- 日期：2026-04-07
- 类型：`ai-mistake`
- 范围：`check` V2 Phase 1、integration 覆盖
- 现象：产品文档已要求验证 `governance_entry.status=ready`，但仓库里最初只锁住了 blocking / warning 场景，未在 integration 层稳定验证真实 ready 入口。
- 根因：此前实现与测试优先关注“发现问题”，遗漏了治理入口的成功路径也必须在真实仓库上下文中被验证。
- 当前处理：新增 `check` ready 集成执行计划，并补 integration 用例锁定 `status=success`、`ready_for_run_agents=true`、`ready_for_clean_pass=true` 与 `next_actions=proceed`。
- 防复发：治理入口类命令默认要在 CLI 与 integration 两层同时覆盖 failure / warning / success 三态，不允许只测坏路径。
- 关联测试：`tests/test_integration.py`
- 关联文档：`docs/product-specs/v2/commands/check/testing.md`、`docs/QUALITY_SCORE.md`、`docs/RELIABILITY.md`
- 关闭条件：`check` ready 集成用例落地并持续通过。

### [closed] distill 的 `section_sources` 曾偏离协议键名

- 日期：2026-04-07
- 类型：`ai-mistake`
- 范围：`distill` V2 Phase 1、来源映射结果协议、integration 覆盖
- 现象：协议文档规定 `section_sources` 使用 `goals/rules/limits/prohibitions`，但真实 heuristic 路径返回了中文键名（`业务目标/关键规则/边界限制/禁止项`）。
- 根因：实现直接复用了人类可读 section 标签构造机器字段，CLI 层未对键集合做强断言，导致协议漂移未被及时发现。
- 当前处理：已把 `section_sources` 统一改回英文协议键；保留产物中的中文显示标签；补充 integration failure 场景测试并升级 CLI / integration 的 `assert_distill_mapping_meta` 为强断言。
- 防复发：凡是协议文档已锁定结构化键名的字段，测试 helper 必须直接断言键集合，不接受“只断言 value 结构”。
- 关联测试：`tests/test_cli.py`、`tests/test_integration.py`
- 关联文档：`docs/product-specs/v2/commands/distill/protocol.md`、`docs/QUALITY_SCORE.md`、`docs/RELIABILITY.md`
- 关闭条件：已修复并由 CLI / integration 回归测试覆盖。

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

### [open] check Phase 1 的 health_score 仍是启发式治理指标

- 日期：2026-04-07
- 类型：`temporary-fix`
- 范围：`check` V2 Phase 1、治理入口结果协议
- 现象：`check` 已输出 `health_score`、`governance_entry`、`next_actions`，但 `health_score` 当前只是 deterministic 启发式分数，不代表完整真实风险。
- 根因：本轮优先目标是把 `check` 从问题清单升级为治理入口，而不是一次性完成按规则域分段、跨命令消费和强门禁设计。
- 当前处理：已明确 blocking / warning 事实仍优先于 `health_score`，并把治理入口推荐逻辑写入结果协议。
- 防复发：后续任何命令若消费 `health_score`，必须同时读取 `blocking_count`、`warning_count` 与 `governance_entry.status`，不能单独用分数做通过判断。
- 关联测试：`tests/test_cli.py`、`tests/test_integration.py`
- 关联文档：`docs/product-specs/v2/commands/check/protocol.md`、`docs/exec-plans/active/harness-commander-v2/check-governance-entry.md`
- 关闭条件：`check` 的健康度模型按规则域分层，并与前置门 / 自动消费协议正式定版。

### [open] distill Phase 1 的 host-model 来源映射允许 unmatched 偏高

- 日期：2026-04-07
- 类型：`temporary-fix`
- 范围：`distill` V2 Phase 1、来源映射结果协议
- 现象：`distill` 已输出 `extraction_report`、`section_sources`、`source_mapping_coverage`，但 host-model 路径下因输出可能被重述，`unmatched` 比例可能较高。
- 根因：本轮优先目标是先提供稳定的来源可追踪协议与 `unmatched` 语义，而不是一次性完成 chunk 级对齐、重述回链或增量映射。
- 当前处理：已明确无法可靠定位时必须标记 `unmatched`，禁止伪造行号；同时保持 fallback 与主结果语义不回归。
- 防复发：后续若消费 `section_sources` 做自动判断，必须结合 `mapping_status` 和 `source_mapping_coverage`，不能把 host-model unmatched 直接当作提炼失败。
- 关联测试：`tests/test_cli.py`、`tests/test_integration.py`
- 关联文档：`docs/product-specs/v2/commands/distill/protocol.md`、`docs/exec-plans/active/harness-commander-v2/distill-source-mapping.md`
- 关闭条件：来源映射扩展到更稳定的 chunk / 引用回链机制，并为 host-model 路径定义可接受覆盖阈值。

### [open] distill 曾在 failure 路径写出正式参考材料

- 日期：2026-04-07
- 类型：`ai-mistake`
- 范围：`distill` failure 语义、`docs/references/*-llms.txt` 产物
- 现象：`distillation_insufficient` 返回 `failure` 时，命令仍会写出正式 `*-llms.txt` 文件，并在 `artifacts` 中报告已创建产物。
- 根因：实现先无条件执行写文件，再基于 `errors` 计算最终状态，导致结果对象与文件系统事实漂移。
- 当前处理：改为先计算命令状态；当状态为 `failure` 时保留 `meta.extraction_report`、`section_sources`、`source_mapping_coverage`，但不生成正式 artifact，也不真实落盘。
- 防复发：CLI 与 integration 都补充 `distillation_insufficient` 时 `artifacts=[]`、目标文件不存在的断言；协议文档同步明确 failure 不生成正式参考材料。
- 关联测试：`tests/test_cli.py`、`tests/test_integration.py`
- 关联文档：`docs/product-specs/v2/commands/distill/protocol.md`、`docs/product-specs/v2/commands/distill/testing.md`、`docs/RELIABILITY.md`
- 关闭条件：后续 `distill` 失败路径持续保持“结果 / JSON / 落盘事实一致”，且不再出现 failure 仍写正式产物的回归。

### [open] check 的 ready 成功入口曾缺少 integration 覆盖

- 日期：2026-04-07
- 类型：`ai-mistake`
- 范围：`check` 治理入口、integration 测试覆盖
- 现象：`check` 的产品/验收文档要求验证 ready 场景，但 integration 层此前只锁住 blocking / warning，没有真实仓库上下文下的 `status=success` + `governance_entry.status=ready` 用例。
- 根因：前一轮实现优先覆盖问题发现路径，遗漏了“当前可以继续”的成功入口断言，导致文档要求和集成覆盖不完全对齐。
- 当前处理：新增 real ready integration 用例，显式构造可量化治理文档、active plan、参考材料和测试目录，锁定 `ready_for_run_agents=true` 与 `next_actions[0].code=proceed`。
- 防复发：后续任何治理入口命令都必须同时覆盖 blocking / warning / ready 三态；不能只测坏状态。
- 关联测试：`tests/test_integration.py`
- 关联文档：`docs/product-specs/v2/commands/check/testing.md`、`docs/product-specs/v2/commands/check/acceptance.md`
- 关闭条件：`check` 的 ready 场景在后续全量回归中持续稳定，且不再出现只有 blocking / warning 被集成测试保护的情况。
