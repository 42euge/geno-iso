# geno-iso

Isolated Docker containers for running coding agents. Extracts OAuth credentials from the macOS Keychain and manages container lifecycle. Supports Claude Code, Codex, and Gemini CLI.

## Install

```bash
geno-tools install geno-iso
```

Or from within an agent session:

```
/geno-tools install geno-iso
```

## Usage

```bash
# Build the Docker image (once)
geno-iso build

# Create a persistent container
geno-iso run my-project /path/to/workspace

# Enter it interactively
geno-iso it my-project          # launches the agent CLI
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
| `geno-iso build [--agent] [--version]` | Build Docker image(s) |
| `geno-iso creds` | Extract credentials from Keychain |

## How auth works

OAuth credentials are extracted from the macOS Keychain (`Claude Code-credentials`) and injected as environment variables (`CLAUDE_CODE_OAUTH_TOKEN`, `CLAUDE_CODE_OAUTH_REFRESH_TOKEN`, `CLAUDE_CODE_OAUTH_SCOPES`). Access tokens expire periodically -- run `geno-iso creds` to refresh, or the CLI auto-refreshes if the `.env` is older than 4 hours.

## License

MIT
