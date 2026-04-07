# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Changed
- Hardened `install-provider` result contracts to keep `wrapper_kind`, installer metadata, and stable failure reasons for permission and filesystem errors.
- Isolated packaging acceptance coverage from host Python environment by bootstrapping editable install inside a temporary virtual environment.
- Isolated CLI install-provider tests from real user directories by using temporary provider target overrides.
- Hardened `distill` summaries so dry-run, fallback, and partial extraction states stay consistent with warnings, meta, and artifact facts.

### Added
- Added `run-agents` CLI and integration coverage for missing spec/plan, invalid plan documents, non-PASS verify states, dry-run PR summary behavior, empty verification summary fallback, and PR summary path collision avoidance.
- Added CLI and integration coverage for `distill` summary consistency across dry-run and host-model fallback paths.
- Added `run-agents` CLI and integration coverage for explicit `--plan` preflight overrides when the default active plan target is missing.

## [0.1.0] - 2026-04-06

### Added
- Initial public release of Harness-Commander.
- Unified CLI entrypoint for `init`, `propose-plan`, `plan-check`, `sync`, `distill`, `check`, and `collect-evidence`.
- JSON output support across commands for AI-friendly integration.
- Claude Code skill packaging scripts and acceptance coverage.
- Local verification flow covering editable install, tests, type checks, and packaging smoke checks.

### Notes
- This is an early-stage `0.x` release. Interfaces and behavior may change as the workflow model evolves.
