"""Docker container lifecycle management for geno-iso."""

import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

DOCKERFILES_DIR = Path.home() / ".geno" / "geno-iso" / "dockerfiles"
IMAGE_PREFIX = "geno-iso"
CONTAINER_PREFIX = "geno-iso-"

AGENTS = {
    "claude": {
        "package": "@anthropic-ai/claude-code",
        "default_version": "2.1.119",
        "version_arg": "CLAUDE_CODE_VERSION",
    },
    "codex": {
        "package": "@openai/codex",
        "default_version": "0.125.0",
        "version_arg": "CODEX_VERSION",
    },
    "gemini": {
        "package": "@google/gemini-cli",
        "default_version": "0.39.1",
        "version_arg": "GEMINI_CLI_VERSION",
    },
}

DEFAULT_AGENT = "claude"


def _image_name(agent: str, profile: str | None = None) -> str:
    suffix = f"-{profile}" if profile else ""
    return f"{IMAGE_PREFIX}-{agent}{suffix}"


def image_tag(agent: str, version: str | None = None, profile: str | None = None) -> str:
    v = version or AGENTS[agent]["default_version"]
    return f"{_image_name(agent, profile)}:{v}"


def image_latest(agent: str, profile: str | None = None) -> str:
    return f"{_image_name(agent, profile)}:latest"


def derive_name(workspace: Path) -> str:
    name = workspace.resolve().name.lower()
    name = re.sub(r"[^a-z0-9-]", "-", name)
    name = re.sub(r"-+", "-", name).strip("-")
    return name or "default"


def _full_name(name: str) -> str:
    return f"{CONTAINER_PREFIX}{name}"


def _dockerfile_dir(agent: str) -> Path:
    d = DOCKERFILES_DIR / agent
    if not (d / "Dockerfile").exists():
        raise SystemExit(f"Dockerfile not found at {d}/Dockerfile")
    return d


def build_base() -> subprocess.CompletedProcess:
    base_dir = DOCKERFILES_DIR / "base"
    if not (base_dir / "Dockerfile").exists():
        raise SystemExit(f"Base Dockerfile not found at {base_dir}/Dockerfile")
    return subprocess.run([
        "docker", "build",
        "-t", f"{IMAGE_PREFIX}-base:latest",
        str(base_dir),
    ])


def build_image(agent: str = DEFAULT_AGENT, version: str | None = None) -> subprocess.CompletedProcess:
    info = AGENTS.get(agent)
    if not info:
        raise SystemExit(f"Unknown agent: {agent}. Available: {', '.join(AGENTS)}")

    v = version or info["default_version"]
    build_dir = _dockerfile_dir(agent)

    base_exists = subprocess.run(
        ["docker", "images", "-q", f"{IMAGE_PREFIX}-base:latest"],
        capture_output=True, text=True,
    ).stdout.strip()
    if not base_exists:
        result = build_base()
        if result.returncode != 0:
            return result

    return subprocess.run([
        "docker", "build",
        "--build-arg", f"{info['version_arg']}={v}",
        "-t", image_tag(agent, v),
        "-t", image_latest(agent),
        str(build_dir),
    ])


def build_profile_image(agent: str, profile_dockerfile: str, version: str | None = None) -> subprocess.CompletedProcess:
    """Build a profile layer on top of an existing agent image."""
    build_dir = _dockerfile_dir(f"{agent}-{profile_dockerfile}")
    v = version or AGENTS[agent]["default_version"]
    return subprocess.run([
        "docker", "build",
        "-t", image_tag(agent, v, profile_dockerfile),
        "-t", image_latest(agent, profile_dockerfile),
        str(build_dir),
    ])


def container_exists(name: str) -> bool:
    r = subprocess.run(
        ["docker", "ps", "-a", "--filter", f"name=^{_full_name(name)}$", "--format", "{{.Names}}"],
        capture_output=True, text=True,
    )
    return _full_name(name) in r.stdout


def container_running(name: str) -> bool:
    r = subprocess.run(
        ["docker", "ps", "--filter", f"name=^{_full_name(name)}$", "--format", "{{.Names}}"],
        capture_output=True, text=True,
    )
    return _full_name(name) in r.stdout


HOST_CLAUDE_DIR = Path.home() / ".claude"
SEED_COPY_FILES = ("CLAUDE.md",)
SETTINGS_STRIP_KEYS = {"hooks", "enabledPlugins", "extraKnownMarketplaces"}


def create_container(
    name: str,
    workspace: Path,
    env_file: Path,
    agent: str = DEFAULT_AGENT,
    seed_history: bool = False,
    profile_dockerfile: str | None = None,
) -> subprocess.CompletedProcess:
    """Create a persistent container that stays alive for exec."""
    full = _full_name(name)
    workspace = workspace.resolve()

    if container_exists(name):
        if container_running(name):
            raise SystemExit(
                f"Container '{full}' is already running.\n"
                f"Use 'geno-iso it {name}' to enter it."
            )
        subprocess.run(["docker", "start", full], capture_output=True)
        return subprocess.CompletedProcess([], 0)

    result = subprocess.run(
        [
            "docker", "run", "-d",
            "--name", full,
            "--env-file", str(env_file),
            "-v", f"{workspace}:/home/agent/workspace",
            "-w", "/home/agent/workspace",
            "--entrypoint", "tail",
            image_latest(agent, profile_dockerfile),
            "-f", "/dev/null",
        ],
        capture_output=True,
    )
    if result.returncode == 0:
        _seed_settings(full, copy_history=seed_history)
    return result


_STORE_SCHEMA = """\
CREATE TABLE IF NOT EXISTS "__drizzle_migrations" (
    id SERIAL PRIMARY KEY, hash text NOT NULL, created_at numeric);
CREATE TABLE `base_messages` (
    `uuid` text PRIMARY KEY NOT NULL, `parent_uuid` text,
    `session_id` text NOT NULL, `timestamp` integer NOT NULL,
    `message_type` text NOT NULL, `cwd` text NOT NULL,
    `user_type` text NOT NULL, `version` text NOT NULL,
    `isSidechain` integer NOT NULL,
    FOREIGN KEY (`parent_uuid`) REFERENCES `base_messages`(`uuid`));
CREATE TABLE `user_messages` (
    `uuid` text PRIMARY KEY NOT NULL, `message` text NOT NULL,
    `tool_use_result` text, `timestamp` integer NOT NULL,
    FOREIGN KEY (`uuid`) REFERENCES `base_messages`(`uuid`));
CREATE TABLE `assistant_messages` (
    `uuid` text PRIMARY KEY NOT NULL, `cost_usd` real NOT NULL,
    `duration_ms` integer NOT NULL, `message` text NOT NULL,
    `is_api_error_message` integer DEFAULT false NOT NULL,
    `timestamp` integer NOT NULL, `model` text DEFAULT '' NOT NULL,
    FOREIGN KEY (`uuid`) REFERENCES `base_messages`(`uuid`));
CREATE TABLE `conversation_summaries` (
    `leaf_uuid` text PRIMARY KEY NOT NULL, `summary` text NOT NULL,
    `updated_at` integer NOT NULL,
    FOREIGN KEY (`leaf_uuid`) REFERENCES `base_messages`(`uuid`));
"""


def _seed_settings(full_name: str, *, copy_history: bool = False) -> None:
    """Copy host settings into the container (one-time, no bind mount).

    settings.json is sanitized — hooks and plugin entries that reference
    host-only paths are stripped so Claude Code starts cleanly.

    copy_history=False (default): creates an empty __store.db to skip onboarding.
    copy_history=True: copies the host's full __store.db (conversation history).
    """
    for fname in SEED_COPY_FILES:
        src = HOST_CLAUDE_DIR / fname
        if src.exists():
            subprocess.run(
                ["docker", "cp", str(src), f"{full_name}:/home/agent/.claude/{fname}"],
                capture_output=True,
            )

    settings_src = HOST_CLAUDE_DIR / "settings.json"
    if settings_src.exists():
        settings = json.loads(settings_src.read_text())
        for key in SETTINGS_STRIP_KEYS:
            settings.pop(key, None)
        payload = json.dumps(settings, indent=2)
        subprocess.run(
            ["docker", "exec", full_name,
             "sh", "-c", f"cat > /home/agent/.claude/settings.json << 'GENO_EOF'\n{payload}\nGENO_EOF"],
            capture_output=True,
        )

    if copy_history:
        host_db = HOST_CLAUDE_DIR / "__store.db"
        if host_db.exists():
            subprocess.run(
                ["docker", "cp", str(host_db), f"{full_name}:/home/agent/.claude/__store.db"],
                capture_output=True,
            )
    else:
        _seed_store_db(full_name)

    _seed_onboarding_flag(full_name)
    _install_geno_tools_plugin(full_name)


def _seed_onboarding_flag(full_name: str) -> None:
    """Write ~/.claude.json with hasCompletedOnboarding and workspace trust pre-accepted."""
    state: dict = {
        "hasCompletedOnboarding": True,
        "numStartups": 1,
        "projects": {
            "/home/agent/workspace": {
                "hasTrustDialogAccepted": True,
                "allowedTools": [],
            },
        },
    }
    host_state = Path.home() / ".claude.json"
    if host_state.exists():
        try:
            host_data = json.loads(host_state.read_text())
            if "theme" in host_data:
                state["theme"] = host_data["theme"]
            if "lastOnboardingVersion" in host_data:
                state["lastOnboardingVersion"] = host_data["lastOnboardingVersion"]
        except (json.JSONDecodeError, OSError):
            pass
    payload = json.dumps(state, indent=2)
    subprocess.run(
        ["docker", "exec", full_name,
         "sh", "-c", f"cat > /home/agent/.claude.json << 'GENO_EOF'\n{payload}\nGENO_EOF"],
        capture_output=True,
    )


def _install_geno_tools_plugin(full_name: str) -> None:
    """Install geno-tools plugin from scratch inside the container."""
    subprocess.run(
        ["docker", "exec", full_name,
         "claude", "plugin", "marketplace", "add", "42euge/geno-tools"],
        capture_output=True,
    )
    subprocess.run(
        ["docker", "exec", full_name,
         "claude", "plugin", "install", "geno-tools@geno-tools"],
        capture_output=True,
    )


def _seed_store_db(full_name: str) -> None:
    """Create an empty __store.db so Claude Code skips first-run onboarding."""
    fd, tmp = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        conn = sqlite3.connect(tmp)
        conn.executescript(_STORE_SCHEMA)
        conn.close()
        subprocess.run(
            ["docker", "cp", tmp, f"{full_name}:/home/agent/.claude/__store.db"],
            capture_output=True,
        )
    finally:
        os.unlink(tmp)


def run_ephemeral(
    workspace: Path,
    env_file: Path,
    agent: str = DEFAULT_AGENT,
    claude_args: list[str] | None = None,
) -> subprocess.CompletedProcess:
    """Run agent CLI in a one-shot container that is removed on exit."""
    workspace = workspace.resolve()
    tty = ["-it"] if sys.stdin.isatty() else ["-i"]
    cmd = [
        "docker", "run", *tty, "--rm",
        "--env-file", str(env_file),
        "-v", f"{workspace}:/home/agent/workspace",
        "-w", "/home/agent/workspace",
        image_latest(agent),
    ]
    if claude_args:
        cmd.extend(claude_args)
    return subprocess.run(cmd)


def list_containers() -> list[dict]:
    r = subprocess.run(
        [
            "docker", "ps", "-a",
            "--filter", f"name={CONTAINER_PREFIX}",
            "--format", "{{json .}}",
        ],
        capture_output=True, text=True,
    )
    if not r.stdout.strip():
        return []
    containers = []
    for line in r.stdout.strip().splitlines():
        c = json.loads(line)
        c["ShortName"] = c.get("Names", "").removeprefix(CONTAINER_PREFIX)
        containers.append(c)
    return containers


def inject_env(name: str, env_file: Path) -> None:
    """Push fresh env vars into a running container for the next exec."""
    full = _full_name(name)
    if not env_file.exists():
        return
    pairs = []
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            pairs.append(line)
    if not pairs:
        return
    script = "\n".join(
        f"export {p.split('=', 1)[0]}='{p.split('=', 1)[1]}'" for p in pairs
    )
    subprocess.run(
        ["docker", "exec", full, "sh", "-c",
         f"cat > /home/agent/.claude_env << 'GENO_EOF'\n{script}\nGENO_EOF"],
        capture_output=True,
    )


def exec_into(name: str, cmd: str = "claude") -> None:
    """Replace current process with docker exec into the container."""
    full = _full_name(name)
    if not container_running(name):
        raise SystemExit(f"Container '{full}' is not running. Start it with 'geno-iso run {name}'.")
    os.execvp("docker", [
        "docker", "exec", "-it", full,
        "sh", "-c", "[ -f /home/agent/.claude_env ] && . /home/agent/.claude_env; exec " + cmd,
    ])


def exec_cmd(name: str, cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    """Run a command inside a running container."""
    return subprocess.run(["docker", "exec", _full_name(name), *cmd], **kwargs)


PIPX_BIN = "/home/agent/.local/bin"
GENO_TOOLS = f"{PIPX_BIN}/geno-tools"


def _ensure_geno_tools(name: str) -> None:
    """Install pipx + geno-tools inside the container if not already present."""
    full = _full_name(name)
    if subprocess.run(["docker", "exec", full, GENO_TOOLS, "--version"], capture_output=True).returncode == 0:
        return
    subprocess.run(["docker", "exec", "-u", "root", full, "pip3", "install", "--break-system-packages", "pipx"])
    subprocess.run(["docker", "exec", full, "pipx", "install", "git+https://github.com/42euge/geno-tools.git"])


def install_skills(name: str, skills: list[str], callback=None) -> list[str]:
    """Install geno-* skillsets via geno-tools inside the container.

    Returns a list of skillsets that failed to install.
    """
    _ensure_geno_tools(name)
    full = _full_name(name)
    failed: list[str] = []
    for skill in skills:
        if callback:
            callback(skill)
        r = subprocess.run(
            ["docker", "exec", full, GENO_TOOLS, "install", skill],
            capture_output=True, text=True,
        )
        if r.returncode != 0:
            print(f"  warn: failed to install {skill}: {r.stderr.strip()}", file=sys.stderr)
            failed.append(skill)
    return failed


def install_npx_skills(name: str, packages: list[str], callback=None) -> None:
    """Install Vercel-style skills (npx skills add) inside the container."""
    full = _full_name(name)
    for pkg in packages:
        if callback:
            callback(pkg)
        subprocess.run(["docker", "exec", full, "npx", "skills", "add", pkg, "--agent", "claude-code", "--global", "--yes"])


def install_plugins(name: str, repos: list[str], callback=None) -> None:
    """Install Claude Code plugins from git repos inside the container."""
    full = _full_name(name)
    for repo in repos:
        if callback:
            callback(repo)
        subprocess.run(["docker", "exec", full, "claude", "plugin", "add", repo])


def configure_mcp(name: str, config_path: str) -> subprocess.CompletedProcess:
    """Copy an MCP config file into the container's ~/.claude/.mcp.json."""
    return subprocess.run(["docker", "cp", config_path, f"{_full_name(name)}:/home/agent/.claude/.mcp.json"])


def stop_container(name: str) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", "stop", _full_name(name)])


def remove_container(name: str, force: bool = False) -> subprocess.CompletedProcess:
    cmd = ["docker", "rm"]
    if force:
        cmd.append("-f")
    cmd.append(_full_name(name))
    return subprocess.run(cmd)
