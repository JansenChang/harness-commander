# Distill 宿主模型契约

## 这个文件是做什么的

用于定义 `harness distill` 在 `host-model` / `auto` 模式下允许宿主模型参与的边界，防止模型调用逻辑散落在代码中却没有稳定的设计事实源。

## 适合写什么

- 宿主模型在 `distill` 中负责什么、不负责什么
- 结构化输出的字段合同
- prompt 设计目标
- fallback 与失败语义

## 当前设计结论

- 宿主模型只负责把输入材料提炼成四类结构化信息：
  - `goals`
  - `rules`
  - `limits`
  - `prohibitions`
- 宿主模型不负责：
  - 目标文件命名
  - 结果状态判断
  - 产物落盘路径
  - fallback 决策语义
  - 最终 `CommandResult` 字段

## 结构化合同

- 模型返回必须符合固定 schema。
- 缺失信息时返回空数组，不允许补写虚构内容。
- 如果返回不可解析、结构不合法或内容全空，Harness 必须把它视为模型失败，而不是“提炼成功”。

## fallback 规则

- `host-model`：
  - 需要可用 provider
  - provider 不存在时直接失败
- `auto`：
  - 优先尝试宿主模型
  - 模型失败时回退到 heuristic
  - 回退事实必须写入 warning / meta

## References

- `docs/product-specs/v1/commands/distill/protocol.md`
- `docs/references/distill-host-model-reference-llms.txt`
- `src/harness_commander/application/model_tasks.py`
