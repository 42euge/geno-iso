---
name: geno-iso-containers-list
description: >-
  List geno-iso containers (running and stopped).
  Use when user says /geno-iso-containers-list or asks what containers exist.
allowed-tools: "Bash(geno-iso ls *)"
license: MIT
metadata:
  author: 42euge
  version: "0.1.0"
observability:
  success_signal: "container list displayed with status and suggested actions"
  failure_signals:
    - "geno-iso ls command failed"
    - "Docker daemon not running"
  knowledge_reads:
    - "Docker container state via geno-iso ls"
  knowledge_writes:
    - "none (read-only listing)"
---

# List Containers

## Workflow

1. Run `geno-iso ls --all --json` to get all containers
2. Format and present the results: name, status, image version, workspace mount
3. Suggest next actions based on state (enter running ones, restart stopped ones)

## Completion

When this skill finishes, emit a trace:

```bash
geno-trace emit \
  --skill geno-iso-containers-list \
  --status <success|failure|abandoned> \
  --tool-calls <approximate count> \
  --errors <count of tool/command errors>
```

- `success` = container list displayed with status info and next-action suggestions
- `failure` = geno-iso ls command failed or Docker daemon unreachable
- `abandoned` = user stopped early
