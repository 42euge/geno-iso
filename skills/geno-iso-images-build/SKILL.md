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
---

# Build Docker Image

## Workflow

1. Run `geno-iso build` (or `geno-iso build --version X.Y.Z` for a specific agent CLI version)
2. Report success and the image tag
3. Default version is 2.1.119 — override with `--version`
