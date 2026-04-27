# Getting Started

## Prerequisites

- **Docker** installed and running
- **macOS** for automatic credential extraction (Linux users create `.env` manually)
- A supported coding CLI (Claude Code, Gemini CLI, Codex, or OpenCode)

## Install

```bash
geno-tools install geno-iso
```

Or from within an agent session:

```
/geno-tools install geno-iso
```

## Build the Docker image

```bash
geno-iso build
```

This builds the base image and the default agent image (Claude Code). To build for a specific agent:

```bash
geno-iso build --agent codex
geno-iso build --agent gemini
```

## Run a container

```bash
# Persistent container
geno-iso run my-project /path/to/workspace

# Enter it
geno-iso it my-project          # launches the agent CLI
geno-iso it my-project --shell  # launches bash

# One-shot (ephemeral)
geno-iso run --rm oneshot . -- -p "hello" --max-turns 1
```

## Lifecycle management

```bash
geno-iso ls          # list running containers
geno-iso ls --all    # include stopped
geno-iso stop my-project
geno-iso rm my-project
```

## Credential refresh

OAuth tokens expire periodically. Refresh them with:

```bash
geno-iso creds
```

The CLI auto-refreshes if the `.env` is older than 4 hours.
