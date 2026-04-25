---
name: geno-iso-credentials-extract
description: >-
  Extract or refresh OAuth credentials from macOS Keychain.
  Use when user says /gt-iso-credentials-extract or container auth fails.
allowed-tools: "Bash(geno-iso creds)"
license: MIT
metadata:
  author: 42euge
  version: "0.1.0"
---

# Extract Credentials

## Workflow

1. Run `geno-iso creds`
2. This reads the macOS Keychain entry `Claude Code-credentials` and writes `CLAUDE_CODE_OAUTH_TOKEN`, `CLAUDE_CODE_OAUTH_REFRESH_TOKEN`, and `CLAUDE_CODE_OAUTH_SCOPES` to `.env`
3. Access tokens expire periodically — re-run this if container auth fails
4. Only works on macOS. On Linux, create `.env` manually with `ANTHROPIC_API_KEY` instead
