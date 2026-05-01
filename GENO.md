# geno-iso -- isolated Docker containers for coding agents

`geno-iso` is a Python CLI and skillset for running coding agents (Claude Code, Codex, Gemini CLI) inside Docker containers with OAuth credentials injected from the macOS Keychain.

## Skills

| Skill | Sub-skillset | Slash command |
|-------|-------------|---------------|
| geno-iso | -- | -- (umbrella) |
| geno-iso-containers-run | containers | /geno-iso-containers-run |
| geno-iso-containers-list | containers | /geno-iso-containers-list |
| geno-iso-containers-enter | containers | /geno-iso-containers-enter |
| geno-iso-images-build | images | /geno-iso-images-build |
| geno-iso-credentials-extract | credentials | /geno-iso-credentials-extract |
| geno-iso-dev-guide | -- | /geno-iso-dev-guide |

## Repo structure

```
geno-iso/
├── GENO.md              # agent instructions (this file)
├── SKILL.md             # umbrella skill manifest (-> skills/geno-iso/SKILL.md)
├── genotools.yaml       # geno-tools manifest
├── pyproject.toml       # Python CLI entry point
├── package.json         # skills manifest with name, version, skills map
├── .geno-agents         # agent identity: role, description, capabilities
├── dockerfiles/         # per-agent Dockerfiles
│   ├── base/            #   shared base image
│   ├── claude/          #   Claude Code container
│   ├── codex/           #   Codex container
│   └── gemini/          #   Gemini CLI container
├── geno_iso/            # Python CLI package
│   ├── cli.py           #   Click CLI (run, ls, it, stop, rm, build, creds, setup)
│   ├── docker.py        #   Docker lifecycle management
│   └── credentials.py   #   macOS Keychain extraction
├── skills/              # skill definitions
│   ├── geno-iso/                      # umbrella
│   ├── geno-iso-containers-run/       # spin up container
│   ├── geno-iso-containers-list/      # list containers
│   ├── geno-iso-containers-enter/     # interactive enter
│   ├── geno-iso-images-build/         # build Docker image
│   ├── geno-iso-credentials-extract/  # refresh credentials
│   └── geno-iso-dev-guide/            # development guide
└── docs/                # MkDocs Material site
```

## Conventions

### Command prefix aliasing

Skills in this repo use the canonical `geno-` prefix in source (e.g., `geno-iso-containers-run`). When installed via `geno-tools`, the installer may configure shorter `/gt-` aliases (e.g., `/gt-iso-containers-run`) depending on the user's settings. Always author skill names and docs with the canonical `geno-` prefix; alias mapping is handled at install time and never committed to this repo.

### Adding a new skill

1. Create a directory under `skills/` named after the skill (e.g., `skills/geno-iso-<verb>-<noun>/`).
2. Add a `SKILL.md` with YAML front matter (`name`, `description`, `allowed-tools`, `argument-hint`, `license`, `metadata`).
3. Register the skill in `package.json` under the `skills` map.
4. Add a row to the Skills table in this file.
5. If the skill belongs to a sub-skillset, note it in the table's Sub-skillset column.

## CLI

Entry point: `geno-iso = "geno_iso.cli:main"`

| Command | Description |
|---|---|
| `geno-iso run [NAME] [WORKSPACE]` | Create/restart a persistent background container |
| `geno-iso run --rm [NAME] [WORKSPACE] -- [ARGS]` | One-shot: run agent and remove on exit |
| `geno-iso ls [--all] [--json]` | List geno-iso containers |
| `geno-iso it [NAME] [--shell]` | Exec into a running container (agent CLI or bash) |
| `geno-iso stop [NAME]` | Stop a container |
| `geno-iso rm [NAME] [-f]` | Remove a container |
| `geno-iso build [--agent] [--version]` | Build Docker image(s) |
| `geno-iso creds` | Extract OAuth credentials from Keychain |
| `geno-iso setup` | Sync Dockerfiles to ~/.geno/geno-iso/dockerfiles/ |

## Architecture

Persistent containers run `tail -f /dev/null` to stay alive. Users interact via `geno-iso it` which calls `docker exec -it`. One-shot mode (`--rm`) runs the agent directly and removes the container on exit.

The `--agent` flag selects which coding agent to run (`claude`, `codex`, or `gemini`). Each agent has its own Dockerfile under `dockerfiles/` built on a shared base image.

## How auth works

OAuth credentials are extracted from the macOS Keychain (`Claude Code-credentials`) and injected as environment variables (`CLAUDE_CODE_OAUTH_TOKEN`, `CLAUDE_CODE_OAUTH_REFRESH_TOKEN`, `CLAUDE_CODE_OAUTH_SCOPES`). Access tokens expire periodically -- run `geno-iso creds` to refresh, or the CLI auto-refreshes if the `.env` is older than 4 hours.

## Dependencies and runtime

- **Python >= 3.10** with `click >= 8.0`
- **Docker** must be installed and running
- **macOS Keychain** for credential extraction (Linux users create `.env` manually)
