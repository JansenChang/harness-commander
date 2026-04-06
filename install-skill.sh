#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
REPO_ROOT=$SCRIPT_DIR
SOURCE_SKILL_DIR="$REPO_ROOT/claude-skills/harness"
TARGET_SKILL_DIR="$REPO_ROOT/.claude/skills/harness"

if ! command -v harness >/dev/null 2>&1; then
  printf 'error: harness command not found in PATH\n' >&2
  printf 'hint: run `pip install -e .` first\n' >&2
  exit 1
fi

if [ ! -f "$SOURCE_SKILL_DIR/SKILL.md" ]; then
  printf 'error: source skill file is missing: %s\n' "$SOURCE_SKILL_DIR/SKILL.md" >&2
  exit 1
fi

mkdir -p "$TARGET_SKILL_DIR"
cp "$SOURCE_SKILL_DIR/SKILL.md" "$TARGET_SKILL_DIR/SKILL.md"

printf 'installed project skill to %s\n' "$TARGET_SKILL_DIR"
printf 'verify in Claude Code with:\n'
printf '  /harness init -p /tmp/harness-skill-smoke\n'
printf '  /harness distill -p /tmp/harness-skill-smoke --json /tmp/harness-skill-smoke/requirements.md "整理为 llms 上下文包"\n'
