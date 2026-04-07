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

- Harness-Commander V1 的 CLI 主命令集已经落地，当前阶段从“补命令骨架”切到“发布前对齐、安装链路硬化和文档归档”。
- `docs/exec-plans/active/` 只保留仍需继续跟进的命令级计划；历史阶段总计划统一归档到 `docs/exec-plans/completed/`。

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

- 统一 active / completed 的计划入口，避免“代码已实现但计划仍停留在历史阶段”的漂移。
- 继续收敛 `install-provider` 的用户目录安装语义、权限失败结果和 acceptance 覆盖。
- 继续收敛打包与 editable install 验证链路，保证本地与 CI 环境都能稳定跑通。

### 当前阻塞与风险

- 2026-04-07 本地执行 `pytest` 的结果为：`49 passed, 1 failed, 8 errors`。
- acceptance 侧错误主要来自 editable install 受 PEP 668 限制，当前环境中的 `pip install -e .` 被 `externally-managed-environment` 阻断。
- `install-provider` 的一条 CLI 测试在当前环境下会尝试写入真实用户目录 `~/.claude/skills/...`，并因权限限制失败；这说明安装测试仍需进一步隔离真实宿主目录。

### 当前 active 入口

- 命令级计划索引：`docs/exec-plans/active/harness-commander-v1/index.md`
- 当前维护重点优先看：`install-provider`、`run-agents`
