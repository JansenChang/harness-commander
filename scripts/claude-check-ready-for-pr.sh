#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/jansen/project/python/harness-commander"
STATUS_FILE="$ROOT/.claude/tmp/last-verify.status"
SUMMARY_FILE="$ROOT/.claude/tmp/verification-summary.md"

if [ ! -f "$STATUS_FILE" ]; then
  printf '{"continue":false,"stopReason":"最近还没有验证记录。请先让 Claude 完成修改并触发自动验证，或手动运行 scripts/claude-auto-verify.sh。","systemMessage":"PR gate blocked: missing verification status."}\n'
  exit 0
fi

status="$(tr -d '\n' < "$STATUS_FILE")"
if [ "$status" != "PASS" ]; then
  message="最近一次自动验证未通过。请先查看 .claude/tmp/last-verify.txt"
  if [ -f "$SUMMARY_FILE" ]; then
    message="$message 与 .claude/tmp/verification-summary.md"
  fi
  printf '{"continue":false,"stopReason":"%s","systemMessage":"PR gate blocked: verification failed."}\n' "$message"
  exit 0
fi

printf '{"continue":true,"systemMessage":"PR gate passed: latest verification is PASS."}\n'
