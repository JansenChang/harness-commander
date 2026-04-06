#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
TARGET_SKILL_DIR="$SCRIPT_DIR/.claude/skills/harness"

if [ ! -e "$TARGET_SKILL_DIR" ]; then
  printf 'skill is not installed: %s\n' "$TARGET_SKILL_DIR"
  exit 0
fi

rm -rf "$TARGET_SKILL_DIR"
printf 'removed project skill from %s\n' "$TARGET_SKILL_DIR"
