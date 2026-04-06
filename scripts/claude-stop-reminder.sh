#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/jansen/project/python/harness-commander"
STATUS_FILE="$ROOT/.claude/tmp/last-verify.status"

cd "$ROOT"

if ! git diff --quiet || ! git diff --cached --quiet; then
  status="missing"
  if [ -f "$STATUS_FILE" ]; then
    status="$(tr -d '\n' < "$STATUS_FILE")"
  fi

  if [ "$status" != "PASS" ]; then
    printf '{"systemMessage":"当前工作区有未提交修改，且最近验证不是 PASS。建议先查看 .claude/tmp/last-verify.txt，然后再 /ship 或创建 PR。"}\n'
    exit 0
  fi

  printf '{"systemMessage":"当前工作区有未提交修改，但最近验证已通过。若变更已完成，可继续 /ship。"}\n'
  exit 0
fi

exit 0
