---
name: geno-iso-containers-run
description: >-
  Spin up an isolated coding agent container with a mounted workspace.
  Use when user says /geno-iso-containers-run or wants to run a coding agent in Docker.
allowed-tools: "Bash(geno-iso run *) Bash(geno-iso build *) Bash(geno-iso creds)"
argument-hint: "[name] [workspace-path] [--rm] [-- agent-args...]"
license: MIT
metadata:
  author: 42euge
  version: "0.1.0"
observability:
  success_signal: "container created and running, name reported to user"
  failure_signals:
    - "Docker image not found and build failed"
    - "geno-iso run exited with non-zero status"
    - "credential extraction failed before container start"
  knowledge_reads:
    - "Docker image list via geno-iso ls / docker images"
    - "workspace path from $ARGUMENTS or cwd"
  knowledge_writes:
    - "running Docker container (geno-iso-<name>)"
---

# Run Isolated Container

## Input

`$ARGUMENTS` — optional container name and workspace path.

If empty, derive the name from the current working directory.

## Workflow

1. Check if the Docker image exists: `geno-iso ls` or `docker images geno-iso --quiet`
2. If no image, build it: `geno-iso build`
3. For a persistent container: `geno-iso run $ARGUMENTS`
4. For a one-shot prompt: `geno-iso run --rm $ARGUMENTS -- -p "prompt" --max-turns 1`
5. Report the container name and how to enter it

## Completion

When this skill finishes, emit a trace:

```bash
geno-trace emit \
  --skill geno-iso-containers-run \
  --status <success|failure|abandoned> \
  --tool-calls <approximate count> \
  --errors <count of tool/command errors>
```

- `success` = container is running and user was told the container name and entry command
- `failure` = image build failed, container creation failed, or credential extraction failed
- `abandoned` = user stopped early
