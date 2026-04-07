# PLANS

## 这个文件是做什么的

用于记录项目 Roadmap、当前阶段目标和近期执行重点。

## 适合写什么

- 本周、本月、本季度的目标
- 当前正在推进的里程碑
- 功能优先级和依赖关系
- 阶段性风险和阻塞项

## 推荐用法

- 开启集中开发前，先用这里和 AI 对齐当前要做什么
- 做任务拆分时，把这里作为上层目标输入
- 回顾执行偏差时，检查是否偏离这里的阶段目标

## 当前统一进度（2026-04-07）

### 当前阶段

- Harness-Commander V1 的 CLI 主命令集已经落地，本轮执行层硬化已归档完成。
- 项目当前处于“V2 最小闭环命令级规划 + 第二轮实现”阶段。
- 当前 active 计划已重新开启，入口位于 `docs/exec-plans/active/harness-commander-v2/`。

### 命令状态快照

| 命令 | 当前状态 | 说明 |
| --- | --- | --- |
| `init` | 已实现 | 已支持白名单补齐、`--dry-run`、统一 JSON 输出 |
| `propose-plan` | 已实现 | 已能生成标准执行计划并补齐治理文档引用 |
| `plan-check` | 已实现 | 已能校验计划结构和治理文档引用 |
| `sync` | 已实现 | 已能识别重大变更并刷新受影响参考产物 |
| `distill` | 已实现 | 已支持 heuristic / `host-model` / `auto` 模式 |
| `check` | 已实现 | 已支持默认扫描 active 计划和生成文档 |
| `collect-evidence` | 已实现 | 已支持统一证据落盘与失败事实保留 |
| `run-agents` | 已实现，继续硬化 | 已有阶段编排与 PR summary 产物，继续维护验证阻断与 provider 默认解析 |
| `install-provider` | 已实现，继续硬化 | 已有多 provider 安装与配置落盘，继续处理用户目录权限与打包验收链路 |

### 当前重点

- 已完成 `run-agents` Phase 1 阶段合同基线，当前继续推进 `check` 的治理入口结果协议。
- 保持默认不依赖宿主模型，先收敛 deterministic baseline，再为后续宿主模型主路径留出结构化边界。
- 在不扩大扫描面和 runtime 范围的前提下，优先补齐：
  - `check` 的 `health_score`、`governance_entry`、`next_actions`
  - `check` 对应 CLI / integration 覆盖
  - V2 `check` 产品、协议、测试、验收文档

### 当前阻塞与风险

- 2026-04-07 本地执行 `pytest` 的结果已恢复为：`67 passed`。
- `install-provider` 相关阻塞已收敛：acceptance 改为临时虚拟环境自举 editable install，CLI 测试不再写真实用户目录，并对权限失败返回稳定结果合同。
- `run-agents` 已补齐 verify 缺失 / 非 PASS 阻断、dry-run PR summary、不覆盖已有 PR summary、verification summary 缺失 fallback 等测试覆盖；剩余风险主要转向 `check` / `distill` 的集成级失败路径补齐。
- 当前主要风险已从“产品问题未定义”收敛到“V2 阶段合同尚未进入代码”；如果继续只靠摘要阶段推进，后续恢复、重试和宿主模型边界会继续漂浮。

### 当前 active 入口

- V2 active 索引：`docs/exec-plans/active/harness-commander-v2/index.md`
- 当前主计划：`docs/exec-plans/active/harness-commander-v2/product-planning.md`
- 当前命令级执行计划：
  - `docs/exec-plans/active/harness-commander-v2/run-agents-stage-contracts.md`
  - `docs/exec-plans/active/harness-commander-v2/check-governance-entry.md`
- 已归档入口：`docs/exec-plans/completed/2026-04-07-harness-commander-v1-exec-archive.md`
