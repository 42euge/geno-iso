---
name: geno-iso-dev-guide
description: >-
  Development guide for the geno-iso codebase. Container settings seeding,
  Claude Code onboarding bypass, credential injection, and testing patterns.
  Use when working on geno-iso itself or debugging container startup issues.
allowed-tools: "Bash(geno-iso *) Bash(docker *) Read Edit"
license: MIT
metadata:
  author: 42euge
  version: "0.1.0"
---

# geno-iso Development Guide

Reference for developing the geno-iso codebase. Covers the settings seeding
pipeline, credential injection, and how Claude Code detects first-run state.

## Container Settings Seeding Pipeline

When `geno-iso run` creates a new container, `_seed_settings()` in `docker.py`
runs these steps in order:

1. **Copy `CLAUDE.md`** — raw `docker cp` from `~/.claude/CLAUDE.md`
2. **Sanitize `settings.json`** — reads host settings, strips `hooks`,
   `enabledPlugins`, and `extraKnownMarketplaces` (host-only paths), writes
   via `docker exec`
3. **Seed `__store.db`** — creates an empty SQLite database with the Drizzle
   schema (5 tables). Without this, Claude Code treats the session as brand new.
4. **Seed `~/.claude.json`** — writes `hasCompletedOnboarding: true` plus
   workspace trust entry. This is the file that controls onboarding/theme
   picker and the "trust this folder" dialog.

### Key files inside the container

| Path | Purpose |
|------|---------|
| `/home/agent/.claude/settings.json` | User settings (sanitized, no hooks) |
| `/home/agent/.claude/CLAUDE.md` | Global agent instructions |
| `/home/agent/.claude/__store.db` | Conversation history DB (empty or copied) |
| `/home/agent/.claude_env` | Fresh OAuth env vars (written by `inject_env` at exec time) |
| `/home/agent/.claude.json` | Onboarding flags + per-project trust state |

## Claude Code First-Run Detection

Claude Code checks three things at startup:

1. **Onboarding completed** — `hasCompletedOnboarding` in `~/.claude.json`.
   If false/missing, shows the theme picker.
2. **Workspace trusted** — `projects["/home/agent/workspace"].hasTrustDialogAccepted`
   in `~/.claude.json`. If false/missing, shows "Is this a project you trust?"
3. **Store DB exists** — `~/.claude/__store.db`. If missing, may trigger
   additional first-run behavior.

## Credential Injection

OAuth tokens are short-lived. The container gets initial tokens via
`--env-file` at creation, but these expire. The `it` command refreshes:

1. `credentials.ensure_fresh()` — re-extracts from macOS Keychain if `.env`
   is older than 4 hours
2. `docker.inject_env()` — writes `/home/agent/.claude_env` with quoted
   `export` statements
3. `docker.exec_into()` — sources `.claude_env` before launching claude:
   `sh -c '[ -f .claude_env ] && . .claude_env; exec claude'`

Values must be single-quoted because `CLAUDE_CODE_OAUTH_SCOPES` contains spaces.

## Testing the Container

```bash
# Non-interactive smoke test (bypasses onboarding by design)
docker exec geno-iso-dev sh -c \
  '. /home/agent/.claude_env && claude -p "say hi" --dangerously-skip-permissions'

# Interactive test (catches onboarding/trust prompts)
# Uses `script` to fake a PTY since docker exec -i alone isn't enough
(sleep 8; echo "/exit") | docker exec -i geno-iso-dev sh -c \
  '[ -f /home/agent/.claude_env ] && . /home/agent/.claude_env; script -qc "claude" /dev/null'
```

The `-p` flag skips onboarding entirely — always test interactively when
changing the seeding pipeline.

## pipx Install Gotcha

`geno-iso` (and `geno-tools`) are installed via `pipx install -e <path>`.
If the editable path points to a stale copy (e.g., an Obsidian vault sync),
changes in the workspace won't take effect. Verify with:

```bash
pipx list --json | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['venvs']['geno-iso']['metadata']['main_package']['package_or_url'])"
```

Re-point with `pipx install -e /path/to/workspace/geno-iso --force`.

## run --seed-history

`geno-iso run --seed-history dev .` copies the host's full `__store.db`
instead of creating an empty one. This lets `claude --continue` work inside
the container with host conversation history.
