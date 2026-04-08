# Application Command Development

## 这个文件是做什么的

用于定义应用层命令实现的开发规范，避免 `src/harness_commander/application/commands.py` 再次膨胀成难以维护的单体模块。

## 目标

- 保持应用层只负责命令编排，不重新承担 CLI、领域协议或基础设施细节。
- 让命令实现可以按模块维护、按命令测试、按边界复用。
- 在不改变产品逻辑的前提下，降低单文件复杂度和跨命令耦合。

## 适用范围

- `src/harness_commander/application/commands.py`
- `src/harness_commander/application/command_handlers/`
- 未来所有新增或重构的应用层命令实现

## 核心规则

### 1. `commands.py` 只保留兼容入口

- `commands.py` 是应用层公共导出面，不再承载大段命令实现。
- 该文件默认只允许存在：
  - 公共导入
  - `execute_command`
  - 向下转发的兼容包装函数
  - 极少量为兼容 patch / monkeypatch 保留的依赖注入逻辑
- 新命令实现默认不得直接继续写进 `commands.py`。

### 2. 一个命令族一个模块

- 新增命令或重构命令时，优先按“命令族”拆到 `application/command_handlers/`。
- 推荐拆分粒度：
  - 简单命令可合并到同一模块
  - 带长辅助逻辑的命令必须独立模块
- 当前推荐结构：
  - `bootstrap.py`：`init` / `propose-plan` / `plan-check` / `collect-evidence`
  - `sync.py`
  - `distill.py`
  - `check.py`
  - `run_agents.py`
  - `provider_install.py`

### 3. 共享逻辑只在满足复用条件时抽取

- 辅助函数只有在满足以下条件之一时才抽到共享模块：
  - 被两个及以上命令模块复用
  - 属于稳定协议构造逻辑
  - 属于跨命令统一约束
- 只服务单个命令的辅助函数，应留在命令模块内，避免过早抽象。

### 4. 依赖方向必须稳定

- 命令模块可以依赖：
  - `domain`
  - `infrastructure`
  - `application` 下其他稳定能力模块
- 命令模块不得反向依赖 CLI。
- 命令模块之间不允许形成隐式循环依赖。
- 若一个命令必须调用另一个命令的结果，应优先通过显式依赖注入，而不是模块内直接互相 import。

### 5. 行为兼容优先于文件美观

- 重构阶段优先保持：
  - CLI 参数不变
  - `CommandResult` 合同不变
  - JSON 结构不变
  - 产物路径不变
  - 现有 patch 点和测试入口尽量不变
- 如果为拆模块而引入行为漂移，视为失败重构。

### 6. 辅助函数命名必须表达业务意图

- 允许的命名风格：
  - `_build_*`
  - `_render_*`
  - `_collect_*`
  - `_resolve_*`
  - `_validate_*`
- 禁止新增含糊命名，如：
  - `_process`
  - `_handle`
  - `_data`
  - `_misc`

### 7. 注释只解释边界和原因

- 模块注释应说明该模块负责哪类命令编排。
- 复杂辅助函数前可加一行注释说明“为什么需要这样拆”。
- 不写逐行复述型注释。

## 复杂度控制

- `commands.py` 应保持为轻量 façade，目标控制在 250 行以内。
- 单个命令模块若超过 400 行，应优先检查是否混入了第二类职责。
- 单个辅助函数若明显跨越“输入校验 + 文件读写 + 结果组装”多个阶段，应继续拆小。

## 重构时的硬约束

- 不在本轮重构中修改产品逻辑。
- 不借重构机会切换宿主模型策略或结果语义。
- 不借重构机会引入新的目录结构事实源，除非同步更新 `ARCHITECTURE.md`。
- 若必须保留兼容包装层，应在包装层写清楚其存在原因。

## 测试要求

- 重构必须至少跑：
  - `tests/test_cli.py`
  - `tests/test_integration.py`
- 如果改到 provider 安装路径，还要补跑：
  - `tests/test_provider_install_modes.py`
  - `tests/test_provider_path_resolution.py`
- 任何因重构导致的 import / patch 点变化，都必须有测试兜底。

## 与 V2 进度的关系

- 当前 V2 仍处于 Phase 2 产品规划阶段。
- 在 `commands.py` 分层重构完成前，不继续推进 Phase 2 的实现切片。
- 先完成命令层结构治理，再继续 `run-agents` / `distill` 的 V2 实现。
