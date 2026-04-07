#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
REPO_ROOT=$SCRIPT_DIR
SOURCE_SKILL_DIR="$REPO_ROOT/src/harness_commander/host_templates/claude/harness"
TARGET_SKILL_DIR="$REPO_ROOT/.claude/skills/harness"

if ! command -v harness >/dev/null 2>&1; then
  printf 'error: harness command not found in PATH\n' >&2
  printf 'hint: run `pip install -e .` first\n' >&2
  exit 1
fi

if [ ! -d "$SOURCE_SKILL_DIR" ]; then
  printf 'error: source skill directory is missing: %s\n' "$SOURCE_SKILL_DIR" >&2
  exit 1
fi

if [ ! -f "$SOURCE_SKILL_DIR/SKILL.md" ]; then
  printf 'error: source skill file is missing: %s\n' "$SOURCE_SKILL_DIR/SKILL.md" >&2
  exit 1
fi

rm -rf "$TARGET_SKILL_DIR"
mkdir -p "$TARGET_SKILL_DIR"
cp -R "$SOURCE_SKILL_DIR/." "$TARGET_SKILL_DIR/"

printf 'installed project skill to %s\n' "$TARGET_SKILL_DIR"
printf 'verify in Claude Code with:\n'
printf '  /harness init -p /tmp/harness-skill-smoke\n'
printf '  /harness distill -p /tmp/harness-skill-smoke /tmp/harness-skill-smoke/requirements.md --json\n'
