# Security Policy

If you believe you have found a security issue in Harness-Commander, please do **not** open a public GitHub issue with exploit details.

## Reporting

Please report security concerns privately to the maintainer before public disclosure. Include:

- a clear description of the issue
- reproduction steps or proof of concept
- affected files or commands
- potential impact

The project will make a best effort to review and address legitimate reports.

## Scope

When contributing code, treat the following as minimum security expectations:

- do not leak secrets, tokens, or sensitive data in logs or fixtures
- validate behavior at external boundaries
- avoid unsafe command execution patterns
- preserve existing authentication and authorization assumptions

For the project's internal security baseline and implementation guidance, see [`docs/SECURITY.md`](docs/SECURITY.md).
