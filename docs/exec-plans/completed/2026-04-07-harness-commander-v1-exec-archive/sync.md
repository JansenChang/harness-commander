# `sync` 执行计划

## Goal

让 `harness sync` 在重大变更发生后，稳定刷新受影响的 AI 参考产物。

## Scope

- 重大变更识别
- 受影响产物和目标路径判断
- 受影响参考材料更新
- 变更摘要与结构化结果输出

## ULW

- `SYNC-ULW-1`：识别重大变更来源
- `SYNC-ULW-2`：判断受影响产物与目标路径
- `SYNC-ULW-3`：更新受影响参考材料
- `SYNC-ULW-4`：输出变更摘要与结构化结果

## 宿主模型参与

- 当前默认不接宿主模型。
- 未来仅允许辅助摘要或内容文案增强。

## References

- `docs/product-specs/v1/commands/sync/product.md`
- `docs/product-specs/v1/commands/sync/protocol.md`
- `docs/product-specs/v1/commands/sync/acceptance.md`
