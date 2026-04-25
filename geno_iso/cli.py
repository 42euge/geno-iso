"""CLI for managing isolated Claude Code containers."""

import click

from geno_iso import docker, credentials
from pathlib import Path


def _default_env_path() -> Path:
    return docker.find_dockerfile() / ".env"


def _pick_one(running_only: bool = True) -> str:
    """Auto-select a container when name is omitted."""
    containers = docker.list_containers()
    if running_only:
        containers = [c for c in containers if "Up" in c.get("Status", "")]
    if not containers:
        raise SystemExit("No running containers." if running_only else "No geno-iso containers.")
    if len(containers) == 1:
        return containers[0]["ShortName"]
    names = ", ".join(c["ShortName"] for c in containers)
    raise SystemExit(f"Multiple containers found: {names}\nSpecify a name.")


def _image_exists(version: str) -> bool:
    import subprocess
    r = subprocess.run(
        ["docker", "images", "-q", f"{docker.IMAGE}:{version}"],
        capture_output=True, text=True,
    )
    return bool(r.stdout.strip())


@click.group()
def main():
    """geno-iso — Isolated Docker containers for Claude Code."""
    pass


@main.command()
@click.argument("name", required=False)
@click.argument("workspace", required=False, type=click.Path(exists=True))
@click.option("--rm", "ephemeral", is_flag=True, help="One-shot mode: run claude and remove container on exit")
@click.option("--version", "version", default=None, help="Claude Code version override")
@click.argument("claude_args", nargs=-1, type=click.UNPROCESSED)
def run(name, workspace, ephemeral, version, claude_args):
    """Create a persistent container, or run a one-shot with --rm.

    Persistent mode (default): creates a background container you enter with 'geno-iso it'.
    One-shot mode (--rm): runs claude with ARGS and removes the container on exit.
    """
    ws = Path(workspace) if workspace else Path.cwd()
    name = name or docker.derive_name(ws)

    if version and not _image_exists(version):
        click.echo(f"Image geno-iso:{version} not found. Building...")
        docker.build_image(version=version)

    env_path = _default_env_path()
    credentials.ensure_fresh(env_path)

    if ephemeral:
        result = docker.run_ephemeral(
            workspace=ws,
            env_file=env_path,
            claude_args=list(claude_args) if claude_args else None,
        )
        raise SystemExit(result.returncode)

    result = docker.create_container(name=name, workspace=ws, env_file=env_path)
    if result.returncode != 0:
        raise SystemExit(result.returncode)
    click.echo(f"Container ready: {docker.PREFIX}{name}")
    click.echo(f"  Enter with:  geno-iso it {name}")
    click.echo(f"  Shell with:  geno-iso it {name} --shell")
    click.echo(f"  Stop with:   geno-iso stop {name}")


@main.command("ls")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.option("--all", "show_all", is_flag=True, help="Include exited containers")
def ls_cmd(as_json, show_all):
    """List geno-iso containers."""
    import json as json_mod

    containers = docker.list_containers()
    if not show_all:
        containers = [c for c in containers if "Up" in c.get("Status", "")]

    if as_json:
        click.echo(json_mod.dumps(containers, indent=2))
        return

    if not containers:
        click.echo("No geno-iso containers." if show_all else "No running containers. Use --all to include stopped.")
        return

    for c in containers:
        status = c.get("Status", "unknown")
        image = c.get("Image", "")
        name = c["ShortName"]
        mounts = c.get("Mounts", "")
        click.echo(f"  {name:<20} {status:<30} {image:<25} {mounts}")


@main.command("it")
@click.argument("name", required=False)
@click.option("--shell", is_flag=True, help="Open a bash shell instead of Claude Code")
def it_cmd(name, shell):
    """Interactively enter a running container.

    Default: launches Claude Code. Use --shell for bash.
    """
    name = name or _pick_one(running_only=True)
    docker.exec_into(name, cmd="bash" if shell else "claude")


@main.command()
@click.argument("name", required=False)
def stop(name):
    """Stop a running container."""
    name = name or _pick_one(running_only=True)
    result = docker.stop_container(name)
    if result.returncode == 0:
        click.echo(f"Stopped: {docker.PREFIX}{name}")
    raise SystemExit(result.returncode)


@main.command()
@click.argument("name", required=False)
@click.option("--force", "-f", is_flag=True, help="Force remove even if running")
def rm(name, force):
    """Remove a container."""
    name = name or _pick_one(running_only=False)
    result = docker.remove_container(name, force=force)
    if result.returncode == 0:
        click.echo(f"Removed: {docker.PREFIX}{name}")
    raise SystemExit(result.returncode)


@main.command()
@click.option("--version", default=docker.DEFAULT_VERSION, help="Claude Code version")
def build(version):
    """Build the geno-iso Docker image."""
    click.echo(f"Building geno-iso:{version}...")
    result = docker.build_image(version=version)
    if result.returncode == 0:
        click.echo(f"Built: geno-iso:{version}")
    raise SystemExit(result.returncode)


@main.command()
def creds():
    """Extract OAuth credentials from macOS Keychain."""
    env_path = _default_env_path()
    cred_data = credentials.extract_from_keychain()
    credentials.write_env_file(env_path, cred_data)
    click.echo(f"Credentials written to {env_path}")
