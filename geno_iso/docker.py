"""Docker container lifecycle management for geno-iso."""

import json
import os
import re
import subprocess
import sys
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


def image_tag(agent: str, version: str | None = None) -> str:
    v = version or AGENTS[agent]["default_version"]
    return f"{IMAGE_PREFIX}-{agent}:{v}"


def image_latest(agent: str) -> str:
    return f"{IMAGE_PREFIX}-{agent}:latest"


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


def create_container(
    name: str,
    workspace: Path,
    env_file: Path,
    agent: str = DEFAULT_AGENT,
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

    return subprocess.run(
        [
            "docker", "run", "-d",
            "--name", full,
            "--env-file", str(env_file),
            "-v", f"{workspace}:/home/agent/workspace",
            "-w", "/home/agent/workspace",
            "--entrypoint", "tail",
            image_latest(agent),
            "-f", "/dev/null",
        ],
        capture_output=True,
    )


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


def exec_into(name: str, cmd: str = "claude") -> None:
    """Replace current process with docker exec into the container."""
    full = _full_name(name)
    if not container_running(name):
        raise SystemExit(f"Container '{full}' is not running. Start it with 'geno-iso run {name}'.")
    os.execvp("docker", ["docker", "exec", "-it", full, cmd])


def exec_cmd(name: str, cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    """Run a command inside a running container."""
    full = _full_name(name)
    return subprocess.run(["docker", "exec", full, *cmd], **kwargs)


PIPX_BIN = "/home/agent/.local/bin"
GENO_TOOLS = f"{PIPX_BIN}/geno-tools"


def _ensure_geno_tools(name: str) -> None:
    """Install pipx + geno-tools inside the container if not already present."""
    full = _full_name(name)
    check = subprocess.run(
        ["docker", "exec", full, GENO_TOOLS, "--version"],
        capture_output=True,
    )
    if check.returncode == 0:
        return

    subprocess.run([
        "docker", "exec", "-u", "root", full,
        "pip3", "install", "--break-system-packages", "pipx",
    ])

    subprocess.run([
        "docker", "exec", full,
        "pipx", "install",
        "git+https://github.com/42euge/geno-tools.git",
    ])


def install_skills(name: str, skills: list[str], callback=None) -> None:
    """Install geno-* skillsets via geno-tools inside the container."""
    _ensure_geno_tools(name)
    full = _full_name(name)

    for skill in skills:
        if callback:
            callback(skill)
        subprocess.run([
            "docker", "exec", full,
            GENO_TOOLS, "install", skill,
        ])


def install_npx_skills(name: str, packages: list[str], callback=None) -> None:
    """Install Vercel-style skills (npx skills add) inside the container."""
    full = _full_name(name)
    for pkg in packages:
        if callback:
            callback(pkg)
        subprocess.run([
            "docker", "exec", full,
            "npx", "skills", "add", pkg, "--agent", "claude-code", "--global", "--yes",
        ])


def install_plugins(name: str, repos: list[str], callback=None) -> None:
    """Install Claude Code plugins from git repos inside the container."""
    full = _full_name(name)
    for repo in repos:
        if callback:
            callback(repo)
        subprocess.run([
            "docker", "exec", full,
            "claude", "plugin", "add", repo,
        ])


def configure_mcp(name: str, config_path: str) -> subprocess.CompletedProcess:
    """Copy an MCP config file into the container's ~/.claude/.mcp.json."""
    full = _full_name(name)
    return subprocess.run([
        "docker", "cp", config_path, f"{full}:/home/agent/.claude/.mcp.json",
    ])


def stop_container(name: str) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", "stop", _full_name(name)])


def remove_container(name: str, force: bool = False) -> subprocess.CompletedProcess:
    cmd = ["docker", "rm"]
    if force:
        cmd.append("-f")
    cmd.append(_full_name(name))
    return subprocess.run(cmd)
