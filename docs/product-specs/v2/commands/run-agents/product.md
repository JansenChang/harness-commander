# V2 `run-agents` 产品草案

## 当前状态

- draft

## V2 决策

- 这是 V2 的第一优先级命令。
- `run-agents` 将成为工程治理主入口，而不是附属工具。
- 当前阶段先保持默认不依赖宿主模型。
- 后续阶段会切到“默认优先宿主模型，失败 fallback”的模式，但 Harness 继续控制流程。

## V1 现状

- 已有顺序阶段编排：`requirements -> plan -> implement -> verify -> pr-summary`
- 已支持 provider 默认读取、`--provider` override、verify 阻断、PR summary 产物
- 已补齐缺失 verify / 非 PASS / dry-run / 路径冲突等关键测试覆盖

## V1 缺陷

- 还没有真正运行多 agent，只是在生成阶段摘要与 PR summary。
- 文档模型中的 `docs` 阶段没有进入 runtime。
- 没有阶段级输入输出契约，无法做恢复、重试、断点续跑和人工接管。
- 没有把 evidence、review、doc update、release note 整合进工作流主链。
- 缺少“为什么应该跑 run-agents 而不是手动串命令”的强产品理由。

## V2 要解决的问题

- 把 `run-agents` 从“摘要编排器”升级成真实工作流编排入口。
- 定义每个阶段的输入、输出、阻断条件、产物和可恢复策略。
- 明确 `docs` 阶段是否进入 runtime，以及进入后由谁负责。
- 定义 agent 间交接格式，而不是只靠自由文本摘要。
- 明确哪些阶段可由宿主模型默认完成，哪些阶段必须始终由 Harness 显式控制。

## V2 继承的边界

- Harness 必须继续控制阶段顺序、最终状态、产物落点和 verify 阻断。
- provider 继续是可插拔能力，不接管流程控制权。
- 即使后续默认优先宿主模型，失败时仍必须回退到可解释的本地规则 / 阻断路径。

## V2 可能推翻的边界

- V1 的固定五阶段模型可能需要扩展成更完整的 runtime。
- `implement` 阶段只生成摘要的策略可能不再足够。

## 当前开放问题

- `docs` 是否应该成为正式 runtime 阶段？
- V2 是否要支持并发 agent，还是先做可恢复串行编排？
- `run-agents` 是否要直接调用 `collect-evidence` / `check` / `distill`，形成闭环？
- 第一批默认优先宿主模型的阶段是只限 `requirements` / `plan`，还是扩展到 `docs` / `implement`？
