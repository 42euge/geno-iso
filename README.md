# geno-iso

Isolated Docker containers for running [Claude Code](https://docs.anthropic.com/en/docs/claude-code). Extracts OAuth credentials from the macOS Keychain and manages container lifecycle.

## Install

```bash
npx skills add 42euge/geno-iso    # Claude Code skills
pipx install -e .                   # CLI (or via geno-tools install iso)
```

## Usage

```bash
# Build the Docker image (once)
geno-iso build

# Create a persistent container
geno-iso run my-project /path/to/workspace

# Enter it interactively
geno-iso it my-project          # launches Claude Code
geno-iso it my-project --shell  # launches bash

# Lifecycle
geno-iso ls                     # list running containers
geno-iso ls --all               # include stopped
geno-iso stop my-project
geno-iso rm my-project

# One-shot mode (ephemeral)
geno-iso run --rm oneshot . -- -p "hello" --max-turns 1

# Refresh credentials
geno-iso creds
```

## Commands

| Command | Description |
|---|---|
| `geno-iso run [NAME] [WORKSPACE]` | Create a persistent background container |
| `geno-iso run --rm [NAME] [WORKSPACE] -- [ARGS]` | One-shot: run and remove |
| `geno-iso ls [--all] [--json]` | List containers |
| `geno-iso it [NAME] [--shell]` | Enter a running container |
| `geno-iso stop [NAME]` | Stop a container |
| `geno-iso rm [NAME] [-f]` | Remove a container |
| `geno-iso build [--version X.Y.Z]` | Build the Docker image |
| `geno-iso creds` | Extract credentials from Keychain |

## Repository structure

```
geno-iso/
├── CLAUDE.md                              # project instructions
├── Dockerfile                             # Claude Code container image
├── pyproject.toml                         # Python CLI entry point
├── package.json                           # Vercel Skills manifest
├── .geno-agents                           # agent identity
├── geno_iso/                              # Python CLI package
│   ├── cli.py                             # Click CLI (7 subcommands)
│   ├── docker.py                          # Docker lifecycle management
│   └── credentials.py                     # macOS Keychain extraction
└── skills/
    ├── geno-iso/                          # umbrella skill
    ├── geno-iso-containers-run/           # spin up container
    ├── geno-iso-containers-list/          # list containers
    ├── geno-iso-containers-enter/         # interactive enter
    ├── geno-iso-images-build/             # build Docker image
    └── geno-iso-credentials-extract/      # refresh credentials
```

## How auth works

OAuth credentials are extracted from the macOS Keychain (`Claude Code-credentials`) and injected as environment variables (`CLAUDE_CODE_OAUTH_TOKEN`, `CLAUDE_CODE_OAUTH_REFRESH_TOKEN`, `CLAUDE_CODE_OAUTH_SCOPES`). Access tokens expire periodically — run `geno-iso creds` to refresh, or the CLI auto-refreshes if the `.env` is older than 4 hours.

## License

MIT
