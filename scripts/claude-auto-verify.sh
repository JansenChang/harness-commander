#!/usr/bin/env bash
set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP_DIR="$ROOT/.claude/tmp"
STATUS_FILE="$TMP_DIR/last-verify.status"
LOG_FILE="$TMP_DIR/last-verify.txt"
SUMMARY_FILE="$TMP_DIR/verification-summary.md"

mkdir -p "$TMP_DIR"
: > "$LOG_FILE"

echo "# Verification Summary" > "$SUMMARY_FILE"
echo >> "$SUMMARY_FILE"
echo "- Time: $(date '+%Y-%m-%d %H:%M:%S')" >> "$SUMMARY_FILE"
echo >> "$SUMMARY_FILE"

run_step() {
  local name="$1"
  shift
  echo "==> $name" | tee -a "$LOG_FILE"
  if "$@" >> "$LOG_FILE" 2>&1; then
    echo "- [x] $name" >> "$SUMMARY_FILE"
    return 0
  fi
  echo "- [ ] $name" >> "$SUMMARY_FILE"
  return 1
}

cd "$ROOT" || exit 1

failed=0
run_step "pytest" "$ROOT/.venv/bin/pytest" || failed=1
run_step "mypy src" "$ROOT/.venv/bin/mypy" "$ROOT/src" || failed=1
run_step "acceptance smoke" "$ROOT/.venv/bin/pytest" "$ROOT/tests/acceptance/test_packaging_and_skill.py" || failed=1

if [ "$failed" -eq 0 ]; then
  printf 'PASS\n' > "$STATUS_FILE"
  echo >> "$SUMMARY_FILE"
  echo "Result: PASS" >> "$SUMMARY_FILE"
  exit 0
fi

printf 'FAIL\n' > "$STATUS_FILE"
echo >> "$SUMMARY_FILE"
echo "Result: FAIL" >> "$SUMMARY_FILE"
exit 1
