# geno-iso — isolated Docker containers for Claude Code

`geno-iso` is a Python CLI and Claude Code skillset for running Claude Code inside Docker containers with OAuth credentials injected from the macOS Keychain.

## Skills

| Skill name | Sub-skillset | Skill | Slash command |
|---|---|---|---|
| `geno-iso` | — | — | — (umbrella) |
| `geno-iso-containers-run` | containers | run | `/gt-iso-containers-run` |
| `geno-iso-containers-list` | containers | list | `/gt-iso-containers-list` |
| `geno-iso-containers-enter` | containers | enter | `/gt-iso-containers-enter` |
| `geno-iso-images-build` | images | build | `/gt-iso-images-build` |
| `geno-iso-credentials-extract` | credentials | extract | `/gt-iso-credentials-extract` |

## CLI

Entry point: `geno-iso = "geno_iso.cli:main"`

| Command | Description |
|---|---|
| `geno-iso run [NAME] [WORKSPACE]` | Create/restart a persistent background container |
| `geno-iso run --rm [NAME] [WORKSPACE] -- [ARGS]` | One-shot: run claude and remove on exit |
| `geno-iso ls [--all] [--json]` | List geno-iso containers |
| `geno-iso it [NAME] [--shell]` | Exec into a running container (claude or bash) |
| `geno-iso stop [NAME]` | Stop a container |
| `geno-iso rm [NAME] [-f]` | Remove a container |
| `geno-iso build [--version]` | Build the Docker image |
| `geno-iso creds` | Extract OAuth credentials from Keychain |

## Architecture

Persistent containers run `tail -f /dev/null` to stay alive. Users interact via `geno-iso it` which calls `docker exec -it`. One-shot mode (`--rm`) runs claude directly and removes the container on exit.

## Compliance

### Nomenclature

Skill names follow: `{skillset}-{sub-skillset}-{skill-slug}`

- **Skillset** = `geno-iso`
- **Sub-skillset** = pluralized noun (`containers`, `images`, `credentials`)
- **Skill slug** = action verb (`run`, `list`, `enter`, `build`, `extract`)
- **Umbrella** = `geno-iso`

### Repo structure

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Project instructions for agents (this file) |
| `package.json` | Skills manifest with name, version, skills map |
| `.geno-agents` | Agent identity: role, description, capabilities |
| `skills/geno-iso/SKILL.md` | Umbrella skill |
| `README.md` | Human-facing docs: install, commands table, repo tree |

### SKILL.md frontmatter

```yaml
---
name: geno-iso-{sub-skillset}-{skill-slug}
description: >-
  What this skill does.
  Use when user says /gt-iso-{sub-skillset}-{skill-slug}.
allowed-tools: "Bash(geno-iso *)"
license: MIT
metadata:
  author: 42euge
  version: "0.1.0"
---
```

### Adding a new skill

1. Create `skills/geno-iso-{sub-skillset}-{skill}/SKILL.md` with compliant frontmatter
2. Update the umbrella `skills/geno-iso/SKILL.md` — add to description and commands table
3. Update `package.json` — add entry to skills map
4. Update `README.md` — commands table and repo tree
5. Update this file's Skills table
