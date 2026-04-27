# CLI Reference

## `geno-iso run`

Create a persistent background container, or run a one-shot with `--rm`.

```
geno-iso run [NAME] [WORKSPACE] [--agent AGENT] [--rm] [--version VERSION] [-- AGENT_ARGS...]
```

| Option | Description |
|---|---|
| `--agent`, `-a` | Agent to run: `claude`, `codex`, or `gemini` (default: `claude`) |
| `--rm` | One-shot mode: run the agent and remove container on exit |
| `--version`, `-v` | Override the agent CLI version |

## `geno-iso ls`

List geno-iso containers.

```
geno-iso ls [--all] [--json]
```

| Option | Description |
|---|---|
| `--all` | Include stopped containers |
| `--json` | Output as JSON |

## `geno-iso it`

Interactively enter a running container.

```
geno-iso it [NAME] [--shell] [--cmd COMMAND]
```

| Option | Description |
|---|---|
| `--shell` | Open bash instead of the agent CLI |
| `--cmd` | Run an arbitrary command |

## `geno-iso stop`

Stop a running container.

```
geno-iso stop [NAME]
```

## `geno-iso rm`

Remove a container.

```
geno-iso rm [NAME] [-f]
```

| Option | Description |
|---|---|
| `-f`, `--force` | Force remove even if running |

## `geno-iso build`

Build agent Docker images.

```
geno-iso build [--agent AGENT] [--version VERSION]
```

| Option | Description |
|---|---|
| `--agent`, `-a` | Agent to build (omit for all) |
| `--version`, `-v` | Agent CLI version override |

## `geno-iso creds`

Extract OAuth credentials from macOS Keychain and write to `.env`.

```
geno-iso creds
```

## `geno-iso setup`

Sync Dockerfiles from the repo to `~/.geno/geno-iso/dockerfiles/`.

```
geno-iso setup
```
