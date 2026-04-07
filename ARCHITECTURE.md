# ARCHITECTURE

## 这个文件是做什么的

用于描述 Harness-Commander 的正式系统架构，帮助研发与 AI 工具在实现命令时保持一致的模块边界、依赖方向、输入输出协议和产物落点。

## 适合写什么

- CLI 层、应用层、领域层、基础设施层的职责划分
- 命令请求如何从 CLI 进入、如何被编排、如何落盘、如何返回统一结果
- 命令间共享的规则、结果模型、文件系统能力和文档能力
- 宿主模型可以参与哪些认知任务，哪些职责必须由 Harness 自己掌控

## 推荐用法

- 在修改任一命令实现前，先阅读这里和 [docs/product-specs/v1/index.md](docs/product-specs/v1/index.md)
- 在新增命令参数、结果字段或产物路径前，先确认是否符合本架构中的统一协议
- 当实现开始出现跨层调用、重复封装或结果结构分叉时，用这里纠正方向

## 目标

防止 Harness-Commander 在后续扩展 `propose-plan`、`sync`、`distill`、`check`、`collect-evidence` 时出现职责混乱、结果协议漂移、文件落点不一致和宿主模型边界失控。

## 架构结论

Harness-Commander 当前应固定为“分层命令编排架构（Layered Command Architecture）”，具体是：

- 表现层（CLI）负责参数解析、输出渲染和退出码控制
- 应用层（Application）负责命令编排、异常收敛和调用顺序控制
- 领域层（Domain）负责统一结果协议、消息模型和领域异常
- 基础设施层（Infrastructure）负责文件系统操作、文档读取/校验、模板资源和时间/路径工具
- 宿主模型不属于核心业务层；它是可插拔的认知能力提供者，只能在产品允许的命令节点参与
- 首批宿主工具 provider 为 `cursor`、`claude`、`codex`、`openclaw`、`trae`、`copilot`；provider 差异、安装规格、配置解析与默认 provider 决策应收敛在应用层抽象中
- `install-provider` 是 provider 安装主路径；应用层需要根据 provider 决定 wrapper 类型（如 `skill` / `command`）、安装范围（`user` / `project`）与安装方式（`copy` / `link`），而不是把所有宿主统一处理成 Claude 风格项目级 skill；其中 Claude user scope 默认目录必须与 Linux 保持一致：Linux/macOS 走 `~/.claude/skills/harness-commander`，Windows 走 `%APPDATA%/Claude/skills/harness-commander`

这是一个适合当前项目阶段的架构，因为：

- 当前项目本质上是 CLI 驱动的命令执行系统，而不是长生命周期服务
- 命令的核心复杂度在“统一协议 + 文件产物 + 治理规则 + 可插拔认知任务”
- 现有代码已经按该方向组织，继续沿用能减少重构成本

## 分层设计

### 1. CLI / Presentation Layer

职责：

- 解析 `harness <command> [options]`
- 处理全局参数，如 `-p/--root`、`--json`、`--verbose`
- 把参数转换成应用层调用
- 根据 `CommandResult` 渲染文本或 JSON 输出
- 返回统一退出码

当前入口：

- [src/harness_commander/cli.py:43](src/harness_commander/cli.py#L43) `build_parser`
- [src/harness_commander/cli.py:131](src/harness_commander/cli.py#L131) `render_result`
- [src/harness_commander/cli.py:140](src/harness_commander/cli.py#L140) `main`

约束：

- CLI 不直接读写业务文件
- CLI 不直接实现规则判断
- CLI 不直接组装原始 dict 结果，必须依赖领域层结果对象

### 2. Application Layer

职责：

- 接收 CLI 参数并编排命令执行流程
- 串联领域模型和基础设施能力
- 把异常统一转换为稳定结果
- 决定命令级步骤顺序
- 维持每个命令的“入口函数”边界

当前模块：

- [src/harness_commander/application/commands.py:86](src/harness_commander/application/commands.py#L86) `run_init`
- [src/harness_commander/application/commands.py:149](src/harness_commander/application/commands.py#L149) `run_propose_plan`
- [src/harness_commander/application/commands.py:177](src/harness_commander/application/commands.py#L177) `run_plan_check`
- [src/harness_commander/application/commands.py:206](src/harness_commander/application/commands.py#L206) `run_collect_evidence`
- [src/harness_commander/application/commands.py:310](src/harness_commander/application/commands.py#L310) `run_sync`
- [src/harness_commander/application/commands.py:394](src/harness_commander/application/commands.py#L394) `run_distill`
- [src/harness_commander/application/commands.py:772](src/harness_commander/application/commands.py#L772) `run_check`
- [src/harness_commander/application/commands.py:277](src/harness_commander/application/commands.py#L277) `execute_command`

约束：

- 应用层不直接操作 CLI 参数对象
- 应用层不应该渲染终端文本
- 应用层可以决定是否调用宿主模型能力，但不能把结果协议控制权交出去

### 3. Domain Layer

职责：

- 定义统一状态枚举、消息对象、产物对象、命令结果对象
- 提供退出码语义
- 提供可被所有命令复用的失败结果构造
- 提供领域异常，供应用层安全收敛

当前模块：

- [src/harness_commander/domain/models.py:15](src/harness_commander/domain/models.py#L15) `ResultStatus`
- [src/harness_commander/domain/models.py:23](src/harness_commander/domain/models.py#L23) `CommandMessage`
- [src/harness_commander/domain/models.py:47](src/harness_commander/domain/models.py#L47) `CommandArtifact`
- [src/harness_commander/domain/models.py:70](src/harness_commander/domain/models.py#L70) `CommandResult`
- [src/harness_commander/domain/models.py:132](src/harness_commander/domain/models.py#L132) `HarnessCommanderError`

约束：

- 领域层不依赖 CLI
- 领域层不依赖具体命令实现细节
- 领域层不做文件系统读写

### 4. Infrastructure Layer

职责：

- 提供文件系统与路径能力
- 提供模板资源访问能力
- 提供治理文档检查、计划模板渲染、计划校验能力
- 提供时间戳、slug、唯一文件名等技术细节能力

当前模块：

- [src/harness_commander/infrastructure/filesystem.py](src/harness_commander/infrastructure/filesystem.py)
- [src/harness_commander/infrastructure/docs.py](src/harness_commander/infrastructure/docs.py)
- [src/harness_commander/infrastructure/templates.py](src/harness_commander/infrastructure/templates.py)

约束：

- 基础设施层不决定命令最终状态
- 基础设施层不做 CLI 输出渲染
- 基础设施层只提供能力，不承担完整业务流程编排

## 命令执行流

标准执行流固定为：

1. CLI 解析参数
2. CLI 调用应用层命令入口
3. 应用层按需要读取治理文档、模板和文件系统能力
4. 应用层汇总 `CommandResult`
5. CLI 根据 `CommandResult` 输出文本或 JSON，并返回退出码

对应当前代码：

- 参数解析：[src/harness_commander/cli.py:43](src/harness_commander/cli.py#L43)
- 命令分发：[src/harness_commander/cli.py:152](src/harness_commander/cli.py#L152)
- 异常收敛：[src/harness_commander/application/commands.py:277](src/harness_commander/application/commands.py#L277)
- 统一结果：[src/harness_commander/domain/models.py:70](src/harness_commander/domain/models.py#L70)

## 统一协议

### 结果协议

所有命令必须返回 `CommandResult`，不得自行拼装结构化输出。

固定字段：

- `command`
- `status`
- `summary`
- `artifacts`
- `warnings`
- `errors`
- `meta`

退出码规则：

- `success` -> 0
- `warning` -> 0
- `failure` -> 1

### 路径协议

- 所有命令以仓库根目录为基准
- 未传 `-p/--root` 时默认使用当前工作目录
- 所有文件产物必须写入产品规格定义的固定目录
- 不允许命令各自发明新的默认产物目录

### 写入协议

- 所有写入型命令必须支持 `--dry-run`
- `dry-run` 只描述将发生的产物变化，不实际落盘
- 默认不静默覆盖已有文件，除非命令产品定义明确允许覆盖

## 宿主模型边界

宿主模型的角色是“可插拔认知能力”，而不是流程控制中心。

### 当前已实现

- `distill` 已在 application 层提供显式模式切换：`heuristic` / `host-model` / `auto`
- 宿主模型接入点固定放在 [src/harness_commander/application/model_tasks.py](src/harness_commander/application/model_tasks.py)，provider 差异与安装规格收敛在 `application/host_providers.py`
- 项目级 provider 配置事实源固定为 `.harness/provider-config.json`，由 application 层解析默认 provider 与运行时 override 优先级
- `run_distill()` 负责模式选择、provider 解析、fallback、结果归一化和统一 `CommandResult`
- `run-agents` 负责按 product spec 与 active exec plan 顺序编排 requirements、plan、implement、verify、pr-summary 五阶段，但不把最终状态语义交给宿主工具
- `install-provider` 是主安装入口；`install-skill.sh` 仅作为 Claude project skill 兼容入口，不再承载 provider 主实现
- provider 安装抽象应以“canonical CLI + 多宿主 wrapper 模板树”为中心：Claude/Codex/OpenClaw/Trae/Copilot 当前走 `skill` wrapper，Cursor 当前走 `command` wrapper
- 运行时引用的 provider 模板事实源统一位于 `src/harness_commander/host_templates/`，并作为 package data 分发；不得再依赖 repo root 下的临时模板目录

### 当前不接模型，但保留扩展位

- `propose-plan`：未来可接宿主模型做需求整理和 ULW 草案生成，但引用补齐、落盘路径和结构约束仍由 Harness 控制
- `sync`、`plan-check`、`check`：未来只允许宿主模型补摘要或建议文案，不允许它决定命中规则、严重级别、目标产物或最终状态
- `collect-evidence`：默认不接模型；未来若补易读摘要，也不得改写命令、退出码、时间、日志和产物事实

### 明确禁止

- 命令名和参数协议定义
- 结果字段结构定义
- 产物路径和落盘位置定义
- 最终通过/失败状态语义
- 白名单、治理文档依赖和写入保护规则
- 任何会改写真实执行事实的摘要“润色”

## 当前命令与层职责映射

| 命令 | CLI | Application | Domain | Infrastructure | 宿主模型 |
| --- | --- | --- | --- | --- | --- |
| init | 参数解析、输出 | 编排初始化流程 | 统一结果 | 模板与文件写入 | 否 |
| propose-plan | 参数解析、输出 | 编排计划生成 | 统一结果 | 文档检查、计划落盘 | 未来可选 |
| plan-check | 参数解析、输出 | 编排计划校验 | 统一结果 | 计划加载与校验 | 仅未来摘要增强 |
| sync | 参数解析、输出 | 编排变更识别与产物更新 | 统一结果 | 文件扫描与落盘 | 仅未来内容摘要增强 |
| distill | 参数解析、输出 | 编排压缩流程与 fallback | 统一结果 | 读取源文件与写入参考材料 | 当前已实现可选 host-model |
| check | 参数解析、输出 | 编排审计流程 | 统一结果 | 规则源加载与文件扫描 | 仅未来摘要增强 |
| collect-evidence | 参数解析、输出 | 编排证据记录 | 统一结果 | 证据落盘 | 默认否，未来仅摘要增强 |

## 目录结构约定

当前项目应继续保持以下结构方向：

- `src/harness_commander/cli.py`：CLI 入口
- `src/harness_commander/application/`：命令编排
- `src/harness_commander/domain/`：领域协议与异常
- `src/harness_commander/infrastructure/`：文件、文档、模板等外部能力
- `src/harness_commander/init_templates/`：`init` 命令使用的包内模板资源
- `tests/`：CLI 与集成验证
- `docs/product-specs/`：产品文档与协议文档
- `docs/exec-plans/active/`：活动计划、任务清单和映射材料

## 当前架构判断

当前代码已经具备“可继续扩展”的基础分层，不建议现在改成更重的 DDD、插件总线或事件驱动架构。

V1 阶段应继续坚持：

- 保持 `cli -> application -> domain/infrastructure` 的依赖方向
- 新命令优先通过在应用层增加清晰入口函数实现
- 通用协议放到领域层，不放到 CLI 或单个命令里
- 文件和文档操作沉到基础设施层，不要散落在各命令实现中
- 宿主模型接入时，通过应用层抽象挂接，不要让 CLI 或基础设施层直接耦合模型 SDK

## 后续扩展建议

- `distill` 已按该原则落地到独立的 [src/harness_commander/application/model_tasks.py](src/harness_commander/application/model_tasks.py)；后续若扩展 `propose-plan`，应复用同样的 application 边界，而不是直接塞进 CLI。
- 如果 `sync` 和 `check` 规则继续增多，可把规则定义从 `application/commands.py` 拆到独立规则模块。
- 如果命令参数继续复杂化，可为每个命令增加独立输入 DTO，避免 `commands.py` 继续膨胀。
