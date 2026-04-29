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
---

# List Containers

## Workflow

1. Run `geno-iso ls --all --json` to get all containers
2. Format and present the results: name, status, image version, workspace mount
3. Suggest next actions based on state (enter running ones, restart stopped ones)
