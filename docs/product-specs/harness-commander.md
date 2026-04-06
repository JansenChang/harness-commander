# Harness-Commander

## 1. 业务目标 (The "Why")
- 解决 Claude、Codex、Trae 等开发者工具在引入 Harness 能力时，缺少统一治理入口的问题。
- 解决 AI 开发流程中“先写后补”的问题，要求需求规划、规范审计、文档同步和验证取证进入同一套生命周期。
- 解决文档与代码事实脱节导致的错误上下文问题，在表结构、公共工具、规范文档发生重大变更后，及时刷新 AI 可读取的参考材料。
- 解决不同工具各自维护一套脚本和规则的问题，用统一命令约定降低接入成本和维护成本。
- 解决长周期任务中上下文过长、AI 注意力下降的问题，通过调用大模型自身的归纳和总结能力，把长文档和老代码压缩为轻量参考资产。
- 解决任务完成后缺少证据留痕的问题，让验证命令、结果摘要和关键日志形成可回溯记录。

## 2. 核心逻辑 (Business Logic)
- [关键规则 1]: Harness-Commander 是供多种开发者工具接入的通用 Skill，开发者工具负责调用命令，不负责复制规则。
- [关键规则 2]: Harness-Commander 通过统一命令入口管理 Harness 的完整生命周期，覆盖初始化、规划、校验、同步、审计、脱水和取证七类能力。
- [关键规则 3]: 所有能力都以仓库根目录为执行基准，并优先读取 `ARCHITECTURE.md`、`docs/PLANS.md`、`docs/PRODUCT_SENSE.md`、`docs/QUALITY_SCORE.md`、`docs/SECURITY.md`、`docs/RELIABILITY.md` 和 `docs/design-docs/core-beliefs.md`。
- [关键规则 4]: `harness init` 必须支持 `-p` 参数，用于指定目标项目根目录；未传入时默认使用当前工作目录。
- [关键规则 5]: `harness init` 负责补齐目录结构与基础模板；目录不存在时必须创建，文件不存在时必须创建，已存在文件不得被静默覆盖。
- [关键规则 6]: `harness propose-plan` 负责把模糊需求生成到 `docs/exec-plans/active/`，并按 ULW 拆分为可执行任务块。
- [关键规则 7]: `harness plan-check` 负责校验计划是否引用了正确约束文档，且必须具备业务目标、核心逻辑、验收标准和异常处理。
- [关键规则 8]: `harness sync` 只在识别到重大变更时更新 `docs/generated/` 或 `docs/references/`，避免产生无意义改动。
- [关键规则 9]: `harness distill` 负责调用大模型自身的能力，将长文档或老代码压缩为 `*-llms.txt` 参考材料。压缩过程必须利用大模型的归纳、总结和提炼能力，而不是简单的文本处理。输出必须保留原始材料的目标、关键规则、边界限制和禁止项。
- [关键规则 10]: `harness check` 负责对照质量、安全和团队信仰执行审计，必须区分阻断项与提醒项。
- [关键规则 11]: `harness collect-evidence` 负责在每轮任务结束后留存验证证据，失败结果也必须保留。
- [关键规则 12]: 统一命令入口固定为 `harness <command> [options]`，不同开发者工具不得重命名核心命令。
- [关键规则 13]: 所有命令必须支持人类可读摘要和机器可解析结果，供开发者工具展示与自动处理。
- [关键规则 14]: `harness init` 的默认补齐清单必须严格限定在以下目录与文件：`AGENTS.md`、`ARCHITECTURE.md`、`docs/DESIGN.md`、`docs/FRONTEND.md`、`docs/PLANS.md`、`docs/PRODUCT_SENSE.md`、`docs/QUALITY_SCORE.md`、`docs/RELIABILITY.md`、`docs/SECURITY.md`、`docs/design-docs/index.md`、`docs/design-docs/core-beliefs.md`、`docs/exec-plans/active/`、`docs/exec-plans/completed/`、`docs/exec-plans/tech-debt-tracker.md`、`docs/generated/db-schema.md`、`docs/product-specs/index.md`、`docs/product-specs/new-user-onboarding.md`、`docs/references/design-system-reference-llms.txt`、`docs/references/nixpacks-llms.txt`、`docs/references/uv-llms.txt`。
- [关键规则 15]: `harness init` 创建文件时必须使用 `src/harness_commander/init_templates/` 下的包内模板资源，确保不同项目初始化后具有一致的文档格式和结构标准。
- [关键规则 16]: `harness init` 不得在目标项目中额外创建 `src/`、`tests/`、`.venv/`、`venv/`、`dist/`、`build/`、`docs/generated/evidence/` 或任何未在白名单中的目录与文件。

## 3. 验收标准 (Acceptance Criteria - AC)
- AC 1: Claude、Codex、Trae 等开发者工具在引入 Harness-Commander 后，必须能够通过同一组命令语义触发 Harness 全流程，不要求为每个工具维护一套独立规则逻辑。
- AC 2: `harness init` 必须支持 `-p <path>` 指定目标项目根目录；未传入 `-p` 时，默认在当前工作目录执行。
- AC 3: `harness init` 执行后，必须补齐 Harness-Commander 运行所需的核心目录与模板；目录不存在则创建目录，文件不存在则创建文件，缺失项补齐率达到 100%，且已有文件不被静默覆盖。
- AC 4: `harness propose-plan` 必须在 `docs/exec-plans/active/` 下生成计划文件，且每个 ULW 都包含“目标、涉及范围、验收标准”三项。
- AC 5: `harness plan-check` 必须校验计划是否引用 `ARCHITECTURE.md`、`docs/PLANS.md` 及至少 1 份相关规范文档；缺少引用、缺少验收标准或缺少异常处理任一项时必须失败。
- AC 6: 当数据库结构、迁移文件、公共工具或参考目录发生重大变更时，`harness sync` 必须只更新受影响的 `docs/generated/` 或 `docs/references/` 文件，并输出变更摘要。
- AC 7: `harness distill` 必须调用大模型自身的归纳和总结能力，将长文档或老代码压缩为 `*-llms.txt` 参考文件。压缩过程必须利用大模型的上下文理解和信息提炼能力，而不是进行简单的文本截断或关键词提取。输出内容必须包含业务目标、关键规则、边界限制和禁止项四类核心信息，且保持原始材料的语义完整性。
- AC 8: `harness check` 必须基于 `docs/QUALITY_SCORE.md`、`docs/SECURITY.md` 和 `docs/design-docs/core-beliefs.md` 输出审计结果，结果中必须包含规则来源、严重级别、文件位置和处理建议。
- AC 9: 对于被定义为阻断项的违规，`harness check` 必须返回非零退出码并明确显示阻断原因。
- AC 10: `harness collect-evidence` 在每轮任务结束后必须生成证据记录，包含执行命令、退出码、开始时间、结束时间、结果摘要和关键日志片段。
- AC 11: 所有命令必须支持 `--json` 输出；在该模式下，结果至少包含 `command`、`status`、`summary`、`artifacts`、`warnings`、`errors` 六个字段。
- AC 12: 所有会改写文件的命令必须支持 `--dry-run`，用于先展示将发生的变更，再决定是否落盘。
- AC 13: `harness init -p <path>` 执行完成后，目标目录必须至少具备以下结构：`AGENTS.md`、`ARCHITECTURE.md`、`docs/DESIGN.md`、`docs/FRONTEND.md`、`docs/PLANS.md`、`docs/PRODUCT_SENSE.md`、`docs/QUALITY_SCORE.md`、`docs/RELIABILITY.md`、`docs/SECURITY.md`、`docs/design-docs/`、`docs/exec-plans/active/`、`docs/exec-plans/completed/`、`docs/generated/db-schema.md`、`docs/product-specs/index.md`、`docs/product-specs/new-user-onboarding.md`、`docs/references/`。
- AC 14: `harness init -p <path>` 执行完成后，目标目录中不得出现 `src/`、`tests/`、`.venv/`、`venv/`、`dist/`、`build/`、`docs/generated/evidence/` 或任何未列入默认补齐清单的额外目录与文件。
- AC 15: `harness init` 创建文件时必须使用 `src/harness_commander/init_templates/` 下的包内模板资源，模板内容必须包含明确的用途说明、适合内容范围和推荐用法三个核心章节。
- AC 16: `harness init` 创建的模板文件编码必须为 UTF-8，换行符必须为 LF（Unix 风格），且不得包含项目特定的配置信息。

## 4. 异常处理 (Edge Cases)
- 当 `ARCHITECTURE.md`、`docs/PLANS.md` 或其他核心规范文档缺失时，计划生成和合规审计必须停止执行，并明确指出缺失文件路径与影响范围。
- 当计划文件内容不符合模板，或未覆盖验收标准、异常处理时，`harness plan-check` 必须直接失败，不允许宽松放行。
- 当外部命令执行失败、接口超时或日志采集异常时，需按照 `docs/RELIABILITY.md` 的要求执行有限次数重试，并保留失败痕迹。
- 当 `harness init` 指定的目标目录不存在时，必须先创建目录树，再补齐缺失文件。
- 当 `harness init` 发现文件已存在时，必须跳过已有文件并在结果中列出跳过项，不允许覆盖已有内容。
- 当 `harness init` 识别到待创建目录或文件超出默认补齐白名单时，必须直接失败，并明确指出超出的路径列表。
- 当文件无权限写入或已有文件内容冲突时，必须停止自动覆盖，并输出待人工处理说明。
- 当输入文档过长、代码目录过大或大模型无法可靠提炼重点时，`harness distill` 必须输出失败摘要，说明大模型压缩能力的限制，而不是生成不完整或有误导性的参考材料。
- 当规则文档仍是说明型模板、无法形成机器可判断条件时，`harness check` 必须将对应项标记为“未量化”，不得伪造通过结果。
- 当测试命令未配置、命令不存在或返回异常时，`harness collect-evidence` 仍需生成证据文件，并记录“验证未执行成功”的原因。
- 当包内模板资源 `src/harness_commander/init_templates/` 缺失或损坏时，`harness init` 必须使用内置的默认模板进行初始化，并在结果中记录模板回退警告。
- 当模板文件内容因编码问题无法正确写入时，`harness init` 必须记录失败原因并继续处理其他文件，不允许因单个文件失败而中断整个初始化过程。
- 当模板内容包含特殊字符或换行符问题时，`harness init` 必须在创建前进行规范化处理，确保生成的文件符合编码规范。
