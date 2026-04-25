---
name: geno-iso-containers-enter
description: >-
  Interactively enter a running geno-iso container.
  Use when user says /gt-iso-containers-enter or wants to exec into a container.
allowed-tools: "Bash(geno-iso ls *) Bash(docker exec geno-iso-*)"
argument-hint: "[container-name] [--shell]"
license: MIT
metadata:
  author: 42euge
  version: "0.1.0"
---

# Enter Container

## Important

`geno-iso it` uses `os.execvp` to replace the current process with an interactive Docker exec session. This cannot be run from within a Claude Code skill — the user must run it directly in their terminal.

## Workflow

1. Run `geno-iso ls --json` to show running containers
2. Tell the user to run the command directly:
   - `geno-iso it {name}` — launches Claude Code inside the container
   - `geno-iso it {name} --shell` — launches bash instead
3. For non-interactive commands, use: `docker exec geno-iso-{name} claude -p "prompt" --max-turns 1`
