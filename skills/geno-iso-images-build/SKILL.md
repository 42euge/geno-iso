---
name: geno-iso-images-build
description: >-
  Build or rebuild the geno-iso Docker image.
  Use when user says /geno-iso-images-build or asks to build the Docker image.
allowed-tools: "Bash(geno-iso build *)"
argument-hint: "[--version X.Y.Z]"
license: MIT
metadata:
  author: 42euge
  version: "0.1.0"
observability:
  success_signal: "Docker image built and tagged successfully"
  failure_signals:
    - "geno-iso build exited with non-zero status"
    - "Dockerfile not found or Docker daemon not running"
  knowledge_reads:
    - "Dockerfile from geno-iso repo"
    - "optional --version argument"
  knowledge_writes:
    - "Docker image (geno-iso:<tag>)"
---

# Build Docker Image

## Workflow

1. Run `geno-iso build` (or `geno-iso build --version X.Y.Z` for a specific agent CLI version)
2. Report success and the image tag
3. Default version is 2.1.119 — override with `--version`

## Completion

When this skill finishes, emit a trace:

```bash
geno-trace emit \
  --skill geno-iso-images-build \
  --status <success|failure|abandoned> \
  --tool-calls <approximate count> \
  --errors <count of tool/command errors>
```

- `success` = Docker image built and tagged, image tag reported to user
- `failure` = build command failed (Dockerfile error, Docker daemon not running)
- `abandoned` = user stopped early
