---
name: geno-iso-containers-enter
description: >-
  Interactively enter a running geno-iso container.
  Use when user says /geno-iso-containers-enter or wants to exec into a container.
allowed-tools: "Bash(geno-iso ls *) Bash(docker exec geno-iso-*)"
argument-hint: "[container-name] [--shell]"
license: MIT
metadata:
  author: 42euge
  version: "0.1.0"
observability:
  success_signal: "user informed of the correct geno-iso it command to run"
  failure_signals:
    - "no running containers found"
    - "docker exec command failed"
  knowledge_reads:
    - "running container list via geno-iso ls"
  knowledge_writes:
    - "none (interactive handoff to user)"
---

# Enter Container

## Important

`geno-iso it` uses `os.execvp` to replace the current process with an interactive Docker exec session. This cannot be run from within a skill -- the user must run it directly in their terminal.

## Workflow

1. Run `geno-iso ls --json` to show running containers
2. Tell the user to run the command directly:
   - `geno-iso it {name}` — launches the agent CLI inside the container
   - `geno-iso it {name} --shell` — launches bash instead
3. For non-interactive commands, use: `docker exec geno-iso-{name} claude -p "prompt" --max-turns 1`

## Completion

When this skill finishes, emit a trace:

```bash
geno-trace emit \
  --skill geno-iso-containers-enter \
  --status <success|failure|abandoned> \
  --tool-calls <approximate count> \
  --errors <count of tool/command errors>
```

- `success` = user was shown the correct `geno-iso it` command and container name
- `failure` = no running containers found or docker exec failed
- `abandoned` = user stopped early
