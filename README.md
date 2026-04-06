# Harness-Commander

统一 Harness 生命周期治理命令入口，为 Claude、Codex、Trae 等开发者工具提供标准化的治理能力。

## 🎯 核心价值

- **统一入口**: 一个命令入口管理 Harness 全生命周期，覆盖初始化、规划、校验、同步、审计、脱水和取证七类能力
- **AI 友好**: 所有命令同时支持人类可读摘要和机器可解析的 JSON 输出，便于 AI 工具集成
- **文档驱动**: 严格执行 `docs/` 目录下的规范文档，确保代码与文档保持同步
- **证据留痕**: 自动记录每轮任务的执行证据，形成可回溯的验证记录

## 📦 快速开始

### 安装

```bash
# 从源码安装
git clone <repository-url>
cd harness-commander
pip install -e .

# 验证安装
harness --help
```

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

# 从文件、片段和说明生成 .llms 上下文包
harness distill -p /path/to/project docs/long-specification.md "提炼成给下游 Agent 使用的 llms 上下文包"

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
/harness distill -p /path/to/project docs/long-specification.md "整理成 llms 上下文包" --json
```

### Skill 参数映射

所有 CLI 参数都支持通过 skill 透传：
- `-p, --root` → 项目根目录
- `--json` → JSON 输出模式
- `--dry-run` → 预览模式
- `--verbose` → 详细日志

### 当前模型边界

- `distill` 默认调用宿主模型，从文件、片段和说明生成 `.llms` 结构化上下文包。
- `distill` 使用位置参数协议：`harness distill <file-or-range>... <instruction>`，最后一个位置参数就是蒸馏说明。
- `distill` 不要求用户显式传 `model` 参数，也不再以 `--mode` 方式暴露内部蒸馏路径。
- `distill` 的复杂输出偏好应通过后续对话继续收敛，而不是在首轮 CLI 中堆叠过多参数。
- `propose-plan`、`sync`、`plan-check`、`check`、`collect-evidence` 当前仍由 Harness 主导执行；其中只有 `propose-plan` 保留未来接宿主模型生成内容的扩展位，`sync` / `plan-check` / `check` / `collect-evidence` 仅允许未来增加摘要或建议文案增强，不能接管状态、产物路径和事实字段。

### 参数顺序提示

由于 `--json` 和 `--verbose` 是全局参数，放在子命令前最稳定，例如：

```bash
harness --json -p /tmp/harness-demo init
harness --json -p /tmp/harness-demo distill docs/requirements.md "整理成 llms 上下文包"
```

### distill 协议补充

#### 位置参数协议

- 命令格式：`harness distill <file-or-range>... <instruction>`
- 最后一个位置参数始终是蒸馏说明 `instruction`
- 至少需要 1 个输入和 1 段说明
- `<file-or-range>` 支持整文件或 `path:start-end` 片段引用
- 当前只支持文件输入，不支持目录输入

示例：

```bash
harness distill requirements.md "整理成 llms 包"
harness distill api.py:20-80 service.py README.md "提取调用链与关键约束"
```

#### 输出路径语义

- 未指定 `--output` 时：
  - 单输入默认写到 `<root>/.llms/<source-stem>.llms`
  - 多输入默认写到 `<root>/.llms/index.llms`
- 指定 `--output` 为文件路径时，直接写到该文件
- 指定 `--output` 为目录路径时，实际写到该目录下的 `index.llms`
- 相对路径按 `--root` 解析，绝对路径则直接使用

#### distill 的 JSON meta

`harness distill --json` 的 `meta` 当前包含：

- `root`: 执行根目录
- `inputs`: 实际参与蒸馏的输入引用列表
- `instruction`: 最终解析出的蒸馏说明
- `output_path`: 目标 `.llms` 路径
- `dry_run`: 是否仅预览
- `interactive`: 是否允许后续对话继续收敛
- `source_types`: 输入类型集合，可能为 `document` / `code` / `mixed`
- `distilled_unit_count`: 当前提炼出的结构化单元数
- `unresolved_inputs`: 预留字段，当前通常为空列表
- `unresolved_sections`: 尚未充分提炼的 section 列表

示例：

```json
{
  "command": "distill",
  "status": "warning",
  "summary": "已基于 1 个输入生成 `.llms` 结构化上下文包 requirements.llms。",
  "artifacts": [
    {
      "path": "/tmp/demo/.llms/requirements.llms",
      "kind": "file",
      "action": "would_create",
      "note": "dry-run 未实际写入文件"
    }
  ],
  "warnings": [
    {
      "code": "partial_distillation",
      "message": "部分结构化上下文字段未被充分提炼，请人工复核。",
      "location": "distill",
      "detail": {
        "unresolved_sections": ["Key Relationships"]
      }
    }
  ],
  "errors": [],
  "meta": {
    "root": "/tmp/demo",
    "inputs": ["requirements.md"],
    "instruction": "整理成 llms 包",
    "output_path": "/tmp/demo/.llms/requirements.llms",
    "dry_run": true,
    "interactive": false,
    "source_types": ["document"],
    "distilled_unit_count": 3,
    "unresolved_inputs": [],
    "unresolved_sections": ["Key Relationships"]
  }
}
```

#### dry-run / interactive / 状态语义

- `--dry-run` 仍会解析输入、执行蒸馏流程并返回目标路径，但不会实际写出 `.llms` 文件
- `--interactive` 表示允许后续通过对话继续收敛首版结果，不是进入终端交互模式
- `partial_distillation`、`interactive_followup_available` 会把结果置为 `warning`
- `source_not_found`、`invalid_input_range`、`host_model_unavailable`、`output_write_failed` 会使命令失败

当前 `.llms` 产物至少围绕以下 section 组织：
- `Distilled Summary`
- `Key Relationships`
- `Reference Units`
- `Agent Guidance`

## 📁 项目结构

```
harness-commander/
├── src/harness_commander/
│   ├── cli.py              # CLI 入口
│   ├── application/
│   │   ├── commands/       # 按命令拆分的应用层编排
│   │   └── model_tasks.py  # 宿主模型调用边界
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
make lint    # 或: .venv/bin/ruff check . && .venv/bin/black --check . && .venv/bin/isort --check .
make type    # 或: .venv/bin/mypy src/
```

默认约定：本项目的测试、验收和 CLI smoke 命令都优先通过 `.venv/bin/...` 执行，不依赖系统 PATH 中是否已安装 `python`、`pytest` 或 `harness`。

### 运行测试

```bash
# 运行所有测试
.venv/bin/pytest

# 运行特定测试
.venv/bin/pytest tests/test_cli.py

# 运行验收测试
.venv/bin/pytest tests/acceptance/
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
5. **脱水** (`distill`) - 默认调用宿主模型，从文件、片段和说明生成供下游 LLM / Agent 使用的 `.llms` 上下文包
6. **审计** (`check`) - 对照质量、安全和信仰执行审计
7. **取证** (`collect-evidence`) - 留存任务执行证据

## 📋 版本兼容性

- **Python**: >= 3.10
- **操作系统**: Linux, macOS, Windows (WSL 推荐)
- **Claude Code**: >= 1.0.0 (Skill 集成)

## 🐛 问题反馈

遇到问题或需要新功能？

1. 检查 `docs/exec-plans/tech-debt-tracker.md` 是否已记录类似问题
2. 查看现有 Issue 或创建新 Issue
3. 提供复现步骤、错误信息和环境详情

## 📄 许可证

[请根据项目实际情况填写许可证信息]

---

**提示**: 开始任何实现、重构、排查或文档补充前，请 AI 先阅读相关 `docs/` 文件。如果 `docs/` 中已有规范、计划、设计或业务约束，默认严格按这些文件执行。