"""Docker container lifecycle management for geno-iso."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

IMAGE = "geno-iso"
PREFIX = "geno-iso-"
DEFAULT_VERSION = "2.1.119"


def derive_name(workspace: Path) -> str:
    name = workspace.resolve().name.lower()
    name = re.sub(r"[^a-z0-9-]", "-", name)
    name = re.sub(r"-+", "-", name).strip("-")
    return name or "default"


def _full_name(name: str) -> str:
    return f"{PREFIX}{name}"


def find_dockerfile() -> Path:
    pkg_dir = Path(__file__).parent.parent
    candidate = pkg_dir / "Dockerfile"
    if candidate.exists():
        return pkg_dir
    if (Path.cwd() / "Dockerfile").exists():
        return Path.cwd()
    raise SystemExit(
        f"Dockerfile not found at {candidate} or {Path.cwd() / 'Dockerfile'}.\n"
        "Run this command from the geno-iso repo directory."
    )


def build_image(version: str = DEFAULT_VERSION, dockerfile_dir: Path | None = None) -> subprocess.CompletedProcess:
    build_dir = dockerfile_dir or find_dockerfile()
    return subprocess.run(
        [
            "docker", "build",
            "--build-arg", f"CLAUDE_CODE_VERSION={version}",
            "-t", f"{IMAGE}:{version}",
            "-t", f"{IMAGE}:latest",
            str(build_dir),
        ],
    )


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
            "-v", f"{workspace}:/home/claude/workspace",
            "-w", "/home/claude/workspace",
            "--entrypoint", "tail",
            f"{IMAGE}:latest",
            "-f", "/dev/null",
        ],
        capture_output=True,
    )


def run_ephemeral(
    workspace: Path,
    env_file: Path,
    claude_args: list[str] | None = None,
) -> subprocess.CompletedProcess:
    """Run Claude Code in a one-shot container that is removed on exit."""
    workspace = workspace.resolve()
    tty = ["-it"] if sys.stdin.isatty() else ["-i"]
    cmd = [
        "docker", "run", *tty, "--rm",
        "--env-file", str(env_file),
        "-v", f"{workspace}:/home/claude/workspace",
        "-w", "/home/claude/workspace",
        f"{IMAGE}:latest",
    ]
    if claude_args:
        cmd.extend(claude_args)
    return subprocess.run(cmd)


def list_containers() -> list[dict]:
    r = subprocess.run(
        [
            "docker", "ps", "-a",
            "--filter", f"name={PREFIX}",
            "--format", "{{json .}}",
        ],
        capture_output=True, text=True,
    )
    if not r.stdout.strip():
        return []
    containers = []
    for line in r.stdout.strip().splitlines():
        c = json.loads(line)
        c["ShortName"] = c.get("Names", "").removeprefix(PREFIX)
        containers.append(c)
    return containers


def exec_into(name: str, cmd: str = "claude") -> None:
    """Replace current process with docker exec into the container."""
    full = _full_name(name)
    if not container_running(name):
        raise SystemExit(f"Container '{full}' is not running. Start it with 'geno-iso run {name}'.")
    os.execvp("docker", ["docker", "exec", "-it", full, cmd])


def stop_container(name: str) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", "stop", _full_name(name)])


def remove_container(name: str, force: bool = False) -> subprocess.CompletedProcess:
    cmd = ["docker", "rm"]
    if force:
        cmd.append("-f")
    cmd.append(_full_name(name))
    return subprocess.run(cmd)
