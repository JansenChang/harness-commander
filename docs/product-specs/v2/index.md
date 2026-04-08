# Harness-Commander V2 文档导航

## 说明

- V2 在结构上与 V1 保持一致，便于对照与迁移。
- V2 Phase 1 已完成最小闭环落地，当前文档既是产品边界事实源，也是下一轮 Phase 2 / 3 的起点。
- 对于已完成的 Phase 1 最小闭环，可直接作为仓库事实源；对未来 Phase 2 / 3，仍需重新立项后再进入实现。

## 当前状态

- 状态：phase1-complete / phase2-planning
- 基线来源：V1 已实现命令集
- 当前完成：`run-agents + check + distill` 最小闭环与 deterministic baseline
- 当前规划中：`run-agents + distill` 默认优先宿主模型主路径
- 后续目标：推进宿主模型默认优先主路径与更强的治理联动

## 已确认的 V2 产品决策

- 产品定位：工程治理系统
- 宿主模型引入路线：
  - 当前阶段默认不依赖宿主模型
  - 后续阶段对部分命令切到“默认优先宿主模型，失败 fallback”
- 第一批必须完成的宿主模型能力：
  - `distill`
  - `run-agents`
- 第一优先级命令：
  - `run-agents`
- `run-agents` 的宿主模型接入范围：
  - 只限 `requirements` 与 `plan` 阶段
- `check` 的定位：
  - 治理完整性入口
- `collect-evidence` 的定位：
  - 保持独立命令
  - 在错误或失败时触发留痕
- 最小闭环：
  - `run-agents`
  - `check`
  - `distill`
- 最小闭环之外的能力：
  - 本轮不优先推进

## V2 总问题陈述

### V1 已完成但仍未真正解决的问题

- 命令已经能执行，但产品层“为什么存在、什么时候该用、和其他命令如何组合”仍不够清楚。
- 许多命令在 V1 更像“单点工具”，而不是一个完整的 Harness 工作流。
- CLI、文档、测试已趋于稳定，但用户价值仍主要停留在“可运行”，没有完全提升到“可持续治理项目与 agent 工作”。

### V1 尚未实现或只实现了占位的能力

- `run-agents`
  - 文档目标模型中的 `docs` 阶段仍未进入 runtime
  - 还没有真正的多 agent 编排 / 恢复 / 重试 / 阶段交接机制
  - 当前更像“阶段摘要生成器”，而不是可控的 agent 工作流编排器
- `distill`
  - 已能输出四类摘要，但还不是稳定的知识沉淀系统
  - 缺少来源映射、增量更新、不同材料类型的分层提炼策略
- `check`
  - 已能输出审计结果，但还不是团队治理总入口
  - 缺少文档漂移、版本漂移、知识库完整性等更高层检查
- `install-provider`
  - 已能安装和记录结果，但 provider 生命周期管理还不完整
  - 缺少 repair / doctor / uninstall / auth-check / compatibility 视角

### V2 要回答的问题

- Harness-Commander 到底是“一组命令”，还是“agent 工作流操作系统”？
- 哪些阶段必须由 Harness 控制，哪些阶段只提供宿主模型增强？
- 哪些命令应该保留，哪些命令应该合并、弱化或改名？
- 哪些 V1 的实现只是工程可行性证明，而不是最终产品形态？

## 当前回答

- V2 当前定位不是“多宿主集成平台”或“纯 agent 操作系统”，而是以工程治理为核心的平台。
- `run-agents` 是治理主入口，其他命令围绕它服务。
- 宿主模型将在 V2 中进入主路径，但采用分阶段推进：
  - 第一阶段：默认不用宿主模型，先保证 deterministic baseline
  - 第二阶段：`distill` 与 `run-agents` 默认优先宿主模型，失败回退到本地规则路径
- `run-agents` 即使进入宿主模型主路径，也只让宿主模型接管 `requirements` 与 `plan`，不接管 `verify`、最终状态和阻断逻辑。
- `distill` 是给下游大模型读取时使用的能力，但不替代 `design-docs/` 与 `product-specs/` 作为正式规则源。
- 无论是否进入宿主模型主路径，Harness 都继续控制最终状态、产物路径、阻断逻辑和 fallback 事实。

## 宿主模型永不接管的能力

- 最终通过 / 失败状态
- verify 阻断判断
- 产物路径与命名
- fallback 是否发生及其记录方式
- provider 配置事实源
- 结构化结果合同

## 命令导航

- `init`：`commands/init/`
- `propose-plan`：`commands/propose-plan/`
- `plan-check`：`commands/plan-check/`
- `sync`：`commands/sync/`
- `distill`：`commands/distill/`
- `install-provider`：`commands/install-provider/`
- `check`：`commands/check/`
- `collect-evidence`：`commands/collect-evidence/`
- `run-agents`：`commands/run-agents/`

## 当前要求

- 每个命令目录都沿用 `product.md` / `protocol.md` / `testing.md` / `acceptance.md` 四件套。
- 在正式进入实现前，至少先写清：
  - V1 的缺陷
  - V2 要继承的边界
  - V2 要推翻的边界
  - 当前仍未决定的问题

## 第一批优先复盘命令

- `run-agents`
- `distill`
- `check`
- `install-provider`

原因：

- 这四个命令最直接决定 Harness 是否只是 CLI 工具集合，还是可持续运行的工程治理系统。

## V2 实施顺序

### Phase 1

- 把 `run-agents` 定义成真正的治理主入口
- 明确阶段输入输出、阻断条件、恢复策略
- 保持默认不依赖宿主模型
- 形成 `run-agents + check + distill` 的最小闭环

当前状态：已完成

### Phase 2

- 让 `distill` 和 `run-agents` 进入“默认优先宿主模型，失败 fallback”模式
- 把宿主模型能力限制在 Harness 可控的边界内
- `run-agents` 仅开放 `requirements` 与 `plan` 给宿主模型主路径

当前状态：产品规划中

### Phase 3

- 再评估 `check` 是否需要有限度引入宿主模型增强
- `install-provider` 暂不作为本轮优先命令

当前状态：未开始
