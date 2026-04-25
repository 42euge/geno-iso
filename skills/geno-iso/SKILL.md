---
name: geno-iso
description: >-
  Isolated Docker containers for running Claude Code.
  Build images, manage container lifecycle, and extract credentials.
  Use when user says /geno-iso or asks about isolated Claude Code containers.
allowed-tools: "Bash(geno-iso *) Bash(docker exec geno-iso-*)"
license: MIT
metadata:
  author: 42euge
  version: "0.1.0"
---

# geno-iso — Isolated Claude Code Containers

Manage Docker containers for running Claude Code in isolation.

```!
which geno-iso >/dev/null 2>&1 || echo "geno-iso CLI not on PATH. Run: geno-tools install iso"
```

## Commands

| Command | Description |
|---|---|
| `geno-iso run [NAME] [WORKSPACE]` | Create a persistent container (background, enter with `it`) |
| `geno-iso run --rm [NAME] [WORKSPACE] -- [CLAUDE_ARGS]` | One-shot: run claude and remove container |
| `geno-iso ls [--all]` | List running (or all) geno-iso containers |
| `geno-iso it [NAME] [--shell]` | Enter a running container (Claude Code or bash) |
| `geno-iso stop [NAME]` | Stop a running container |
| `geno-iso rm [NAME] [-f]` | Remove a container |
| `geno-iso build [--version X.Y.Z]` | Build the Docker image |
| `geno-iso creds` | Extract OAuth credentials from macOS Keychain |

## Typical Workflow

1. `geno-iso build` — build the image (once)
2. `geno-iso run my-project /path/to/workspace` — create a persistent container
3. `geno-iso it my-project` — enter it interactively (launches Claude Code)
4. `geno-iso it my-project --shell` — or get a bash shell
5. `geno-iso stop my-project` / `geno-iso rm my-project` — lifecycle management

## Runtime

Requires Docker and macOS Keychain access for credential extraction.
