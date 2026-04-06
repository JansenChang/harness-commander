# Harness-Commander

Harness-Commander 是一个面向开发者与 AI coding workflows 的 Python CLI，用于把 spec、plan、verification、sync 和 evidence capture 串成一条可治理的工作流。

> 项目当前处于 **early-stage / 0.x** 阶段。接口和行为可能继续演进，适合个人项目、原型和团队内试点，不承诺长期稳定兼容。

## 🎯 核心价值

- **统一入口**: 一个命令入口管理 Harness 全生命周期，覆盖初始化、规划、校验、同步、审计、脱水和取证七类能力
- **AI 友好**: 所有命令同时支持人类可读摘要和机器可解析的 JSON 输出，便于 AI 工具集成
- **文档驱动**: 严格执行 `docs/` 目录下的规范文档，确保代码与文档保持同步
- **证据留痕**: 自动记录每轮任务的执行证据，形成可回溯的验证记录

## 📦 快速开始

### 安装

```bash
# 从源码安装
git clone https://github.com/JansenChang/harness-commander.git
cd harness-commander
python -m venv .venv
source .venv/bin/activate
pip install -e .

# 验证安装
harness --help
```

### 30 秒最小示例

```bash
harness init -p /tmp/harness-demo
harness --json -p /tmp/harness-demo distill /tmp/harness-demo/README.md
```

如果你看到初始化后的治理文件，以及 `distill` 返回的 JSON 结果，就说明本地安装已可用。

### 基本使用

```bash
# 初始化项目结构
harness init -p /path/to/your/project

# 生成执行计划
harness propose-plan -p /path/to/project --input "添加用户认证功能"

# 校验计划合规性
harness plan-check -p /path/to/project docs/exec-plans/active/2026-04-06-user-auth.md

# 同步重大变更到文档
harness sync -p /path/to/project

# 压缩长文档为 AI 参考材料
harness distill -p /path/to/project docs/long-specification.md

# 执行项目审计
harness check -p /path/to/project

# 收集执行证据
harness collect-evidence -p /path/to/project \
  --command "make test" \
  --exit-code 0 \
  --summary "所有测试通过" \
  --status success \
  --log "测试运行 2.3 秒" \
  --log "通过率 100%"
```

## 🔧 Claude Code Skill 集成

Harness-Commander 可以通过项目内 skill 集成到 Claude Code，优先用于包装已安装的本地 `harness` CLI。

### Skill 安装

```bash
# 1. 确保 Harness-Commander 已安装
pip install -e .

# 2. 安装项目内 skill
./install-skill.sh
```

安装脚本会把项目级 skill 写入 `.claude/skills/harness/`，命令名保持为 `/harness`。

### Skill 使用

在 Claude Code 对话中直接使用 `/harness` 命令：

```
/harness init -p /path/to/project
/harness distill -p /path/to/project docs/long-specification.md --json
```

### Skill 参数映射

所有 CLI 参数都支持通过 skill 透传：
- `-p, --root` → 项目根目录
- `--json` → JSON 输出模式
- `--dry-run` → 预览模式
- `--verbose` → 详细日志

### 当前模型边界

- `distill` 当前默认使用规则/启发式提炼生成参考材料。
- `distill --mode host-model` 会通过本地 `claude` CLI 调用宿主模型做结构化提炼。
- `distill --mode auto` 会优先尝试宿主模型，失败后自动回退到启发式路径。
- `propose-plan`、`sync`、`plan-check`、`check`、`collect-evidence` 当前仍由 Harness 主导执行；其中只有 `propose-plan` 保留未来接宿主模型生成内容的扩展位，`sync` / `plan-check` / `check` / `collect-evidence` 仅允许未来增加摘要或建议文案增强，不能接管状态、产物路径和事实字段。

### 参数顺序提示

由于 `--json` 和 `--verbose` 是全局参数，放在子命令前最稳定，例如：

```bash
harness --json -p /tmp/harness-demo init
harness --json -p /tmp/harness-demo distill docs/requirements.md --mode auto
```

## 📁 项目结构

```
harness-commander/
├── src/harness_commander/
│   ├── cli.py              # CLI 入口
│   ├── application/        # 应用层（命令实现）
│   ├── domain/             # 领域层（模型定义）
│   └── infrastructure/     # 基础设施层（文件操作、模板等）
├── docs/                   # 治理文档
│   ├── design-docs/        # 设计文档
│   ├── exec-plans/         # 执行计划
│   ├── product-specs/      # 产品需求
│   ├── generated/          # 生成文档
│   └── references/         # AI 参考材料
├── tests/                  # 测试套件
├── pyproject.toml          # 项目配置
└── README.md               # 本文档
```

## 📚 核心文档

开始使用前，请阅读以下关键文档：

1. **`ARCHITECTURE.md`** - 系统架构与模块边界
2. **`AGENTS.md`** - AI 行为规范与决策边界
3. **`docs/PLANS.md`** - 当前 Roadmap 与执行重点
4. **`docs/design-docs/core-beliefs.md`** - 团队技术原则
5. **`docs/product-specs/index.md`** - 产品规格入口与命令导航
6. **`docs/product-specs/v1/index.md`** - Harness-Commander V1 按命令文档导航

## 🧪 开发与测试

### 开发环境设置

```bash
# 1. 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# 2. 安装开发依赖
pip install -e ".[dev]"

# 3. 运行代码质量检查
make lint    # 或: ruff check . && black --check . && isort --check .
make type    # 或: mypy src/
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_cli.py

# 运行验收测试
pytest tests/acceptance/
```

### 构建打包

```bash
# 构建分发包
make build

# 清理构建产物
make clean
```

## 🚀 高级功能

### JSON 输出模式

所有命令都支持 `--json` 参数，输出结构化的结果供程序处理：

```bash
harness init -p /tmp/test-project --json
```

输出示例：
```json
{
  "command": "init",
  "status": "success",
  "summary": "初始化完成，创建了 15 个文件，跳过了 2 个已有文件",
  "artifacts": ["AGENTS.md", "ARCHITECTURE.md", "docs/..."],
  "warnings": [],
  "errors": []
}
```

### Dry-run 预览模式

可能修改文件的命令都支持 `--dry-run`，预览将发生的变更而不实际写入：

```bash
harness init -p /tmp/test-project --dry-run
harness sync -p /path/to/project --dry-run
```

### 自定义模板

初始化文件模板由 `src/harness_commander/init_templates/` 中的包内资源提供，`docs/design-docs/init-templates.md` 负责说明模板规范与内容基线。

## 🔄 生命周期管理

Harness-Commander 支持完整的治理生命周期：

1. **初始化** (`init`) - 补齐目录结构与基础模板
2. **规划** (`propose-plan`) - 将需求转化为可执行计划
3. **校验** (`plan-check`) - 确保计划引用正确约束文档
4. **同步** (`sync`) - 将代码重大变更同步到文档
5. **脱水** (`distill`) - 默认通过规则提炼压缩长文档，也支持可选的宿主模型增强模式
6. **审计** (`check`) - 对照质量、安全和信仰执行审计
7. **取证** (`collect-evidence`) - 留存任务执行证据

## 📋 版本兼容性

- **Python**: >= 3.10
- **操作系统**: Linux, macOS, Windows (WSL 推荐)
- **Claude Code**: >= 1.0.0 (Skill 集成)

## 🐛 问题反馈

欢迎通过 GitHub Issues 和 Pull Requests 反馈问题、提出建议或提交改进。

提 issue 时建议附带：
1. 复现步骤
2. 错误输出或截图
3. Python 版本与操作系统
4. 你执行的 `harness` 命令

## 📄 许可证

本项目基于 **MIT License** 开源。详见根目录 [LICENSE](LICENSE)。

---

**提示**: 开始任何实现、重构、排查或文档补充前，请 AI 先阅读相关 `docs/` 文件。如果 `docs/` 中已有规范、计划、设计或业务约束，默认严格按这些文件执行。