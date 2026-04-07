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

- Harness-Commander V1 的 CLI 主命令集已经落地，本轮执行层实现任务已完成收敛，当前阶段切到“归档执行任务 + 重新审视产品缺陷”。
- `docs/exec-plans/active/` 当前不再保留命令级执行计划；本轮命令计划快照已统一归档到 `docs/exec-plans/completed/2026-04-07-harness-commander-v1-exec-archive/`。

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

- 归档本轮执行层任务，冻结当前实现状态，避免在产品审视前继续滚动实现范围。
- 重新审视命令设计、结果协议和工作流层面的产品缺陷，决定下一轮是否需要新的 active exec plan。
- 若重开执行任务，应以产品缺陷清单为输入重新生成 active 计划，而不是继续复用本轮硬化计划。

### 当前阻塞与风险

- 2026-04-07 本地执行 `pytest` 的结果已恢复为：`67 passed`。
- `install-provider` 相关阻塞已收敛：acceptance 改为临时虚拟环境自举 editable install，CLI 测试不再写真实用户目录，并对权限失败返回稳定结果合同。
- `run-agents` 已补齐 verify 缺失 / 非 PASS 阻断、dry-run PR summary、不覆盖已有 PR summary、verification summary 缺失 fallback 等测试覆盖；剩余风险主要转向 `check` / `distill` 的集成级失败路径补齐。
- 当前主要风险不再是执行稳定性，而是产品缺陷尚未系统复盘；如果继续直接补实现，容易在错误产品边界上做局部优化。

### 当前 active 入口

- 当前无 active 执行计划。
- 已归档入口：`docs/exec-plans/completed/2026-04-07-harness-commander-v1-exec-archive.md`
