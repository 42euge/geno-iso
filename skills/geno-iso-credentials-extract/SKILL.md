---
name: geno-iso-credentials-extract
description: >-
  Extract or refresh OAuth credentials from macOS Keychain.
  Use when user says /geno-iso-credentials-extract or container auth fails.
allowed-tools: "Bash(geno-iso creds)"
license: MIT
metadata:
  author: 42euge
  version: "0.1.0"
observability:
  success_signal: "OAuth tokens written to .env successfully"
  failure_signals:
    - "macOS Keychain entry not found"
    - "geno-iso creds exited with non-zero status"
  knowledge_reads:
    - "macOS Keychain (Claude Code-credentials entry)"
  knowledge_writes:
    - ".env file with CLAUDE_CODE_OAUTH_TOKEN, CLAUDE_CODE_OAUTH_REFRESH_TOKEN, CLAUDE_CODE_OAUTH_SCOPES"
---

# Extract Credentials

## Workflow

1. Run `geno-iso creds`
2. This reads the macOS Keychain entry `Claude Code-credentials` and writes `CLAUDE_CODE_OAUTH_TOKEN`, `CLAUDE_CODE_OAUTH_REFRESH_TOKEN`, and `CLAUDE_CODE_OAUTH_SCOPES` to `.env`
3. Access tokens expire periodically — re-run this if container auth fails
4. Only works on macOS. On Linux, create `.env` manually with `ANTHROPIC_API_KEY` instead

## Completion

When this skill finishes, emit a trace:

```bash
geno-trace emit \
  --skill geno-iso-credentials-extract \
  --status <success|failure|abandoned> \
  --tool-calls <approximate count> \
  --errors <count of tool/command errors>
```

- `success` = OAuth tokens extracted from Keychain and written to .env
- `failure` = Keychain entry not found or geno-iso creds exited with error
- `abandoned` = user stopped early
