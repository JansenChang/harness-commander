# Contributing

Thanks for your interest in improving Harness-Commander.

## Before you open a PR

1. Open an issue first for larger changes or behavior changes.
2. Keep changes scoped and aligned with the existing docs under `docs/`.
3. Update tests and user-facing docs when behavior changes.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Validation

Run these before submitting a PR:

```bash
.venv/bin/mypy src
.venv/bin/pytest
./scripts/claude-auto-verify.sh
```

## Pull request guidance

- Explain the problem being solved.
- Describe any user-visible behavior changes.
- Keep commit messages focused on intent.
- Prefer small, reviewable diffs.

## Documentation expectations

Harness-Commander is doc-driven. If you change behavior, check whether the related files in `docs/` also need updates.
