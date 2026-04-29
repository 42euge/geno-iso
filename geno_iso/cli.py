"""CLI for managing isolated coding agent containers."""

import click

from geno_iso import docker, credentials
from pathlib import Path


def _default_env_path() -> Path:
    return docker.DOCKERFILES_DIR / ".env"


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


def _image_exists(agent: str, version: str) -> bool:
    import subprocess
    r = subprocess.run(
        ["docker", "images", "-q", docker.image_tag(agent, version)],
        capture_output=True, text=True,
    )
    return bool(r.stdout.strip())


@click.group()
def main():
    """geno-iso — Isolated containers for coding agents."""
    pass


@main.command()
@click.argument("name", required=False)
@click.argument("workspace", required=False, type=click.Path(exists=True))
@click.option("--agent", "-a", default=docker.DEFAULT_AGENT, type=click.Choice(list(docker.AGENTS)), help="Agent to run")
@click.option("--rm", "ephemeral", is_flag=True, help="One-shot mode: run and remove on exit")
@click.option("--version", "-v", "version", default=None, help="Agent CLI version override")
@click.option("--skills", "-s", multiple=True, help="Geno skillsets via geno-tools (e.g. -s media -s research)")
@click.option("--npx-skill", multiple=True, help="Vercel-style skills via npx (e.g. --npx-skill user/repo)")
@click.option("--plugin", multiple=True, help="Claude Code plugins from git repos")
@click.option("--mcp-config", type=click.Path(exists=True), help="MCP config file to copy into container")
@click.argument("agent_args", nargs=-1, type=click.UNPROCESSED)
def run(name, workspace, agent, ephemeral, version, skills, npx_skill, plugin, mcp_config, agent_args):
    """Create a persistent container, or run a one-shot with --rm.

    Persistent mode (default): creates a background container you enter with 'it'.
    One-shot mode (--rm): runs the agent with ARGS and removes the container on exit.

    \b
    Pre-install extensions to keep your host agent clean:
        geno-iso run -s media -s research myproject .
        geno-iso run --npx-skill user/repo myproject .
        geno-iso run --plugin git@github.com:user/plugin.git myproject .
        geno-iso run --mcp-config ./mcp.json myproject .
    """
    ws = Path(workspace) if workspace else Path.cwd()
    name = name or docker.derive_name(ws)

    if not _image_exists(agent, version or docker.AGENTS[agent]["default_version"]):
        click.echo(f"Image not found. Building {agent}...")
        docker.build_image(agent=agent, version=version)

    env_path = _default_env_path()
    credentials.ensure_fresh(env_path)

    if ephemeral:
        result = docker.run_ephemeral(
            workspace=ws,
            env_file=env_path,
            agent=agent,
            claude_args=list(agent_args) if agent_args else None,
        )
        raise SystemExit(result.returncode)

    result = docker.create_container(name=name, workspace=ws, env_file=env_path, agent=agent)
    if result.returncode != 0:
        raise SystemExit(result.returncode)

    _install_extensions(name, skills, npx_skill, plugin, mcp_config)

    click.echo(f"Container ready: {docker.CONTAINER_PREFIX}{name} ({agent})")
    installed = list(skills) + list(npx_skill) + list(plugin)
    if installed:
        click.echo(f"  Extensions: {', '.join(installed)}")
    if mcp_config:
        click.echo(f"  MCP config: {mcp_config}")
    click.echo(f"  Enter with:  geno-iso it {name}")
    click.echo(f"  Shell with:  geno-iso it {name} --shell")
    click.echo(f"  Stop with:   geno-iso stop {name}")


def _install_extensions(name, skills, npx_skills, plugins, mcp_config):
    """Install all requested extensions into a container."""
    if skills:
        click.echo("Installing geno skillsets...")
        docker.install_skills(name, list(skills), callback=lambda s: click.echo(f"  geno-tools install {s}"))
    if npx_skills:
        click.echo("Installing npx skills...")
        docker.install_npx_skills(name, list(npx_skills), callback=lambda s: click.echo(f"  npx skills add {s}"))
    if plugins:
        click.echo("Installing plugins...")
        docker.install_plugins(name, list(plugins), callback=lambda s: click.echo(f"  claude plugin add {s}"))
    if mcp_config:
        click.echo(f"Configuring MCP from {mcp_config}...")
        docker.configure_mcp(name, mcp_config)


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
@click.option("--shell", is_flag=True, help="Open a bash shell instead of the agent CLI")
@click.option("--cmd", default=None, help="Custom command to exec")
def it_cmd(name, shell, cmd):
    """Interactively enter a running container.

    Default: launches the agent CLI. Use --shell for bash, or --cmd for arbitrary commands.
    """
    name = name or _pick_one(running_only=True)
    if cmd:
        exec_cmd = cmd
    elif shell:
        exec_cmd = "bash"
    else:
        exec_cmd = _detect_agent(name)
    docker.exec_into(name, cmd=exec_cmd)


def _detect_agent(container_name: str) -> str:
    """Detect which agent CLI is in the container by checking its image tag."""
    containers = docker.list_containers()
    for c in containers:
        if c["ShortName"] == container_name:
            image = c.get("Image", "")
            for agent in docker.AGENTS:
                if agent in image:
                    return agent
            break
    return "claude"


@main.command()
@click.argument("name", required=False)
def stop(name):
    """Stop a running container."""
    name = name or _pick_one(running_only=True)
    result = docker.stop_container(name)
    if result.returncode == 0:
        click.echo(f"Stopped: {docker.CONTAINER_PREFIX}{name}")
    raise SystemExit(result.returncode)


@main.command()
@click.argument("name", required=False)
@click.option("--force", "-f", is_flag=True, help="Force remove even if running")
def rm(name, force):
    """Remove a container."""
    name = name or _pick_one(running_only=False)
    result = docker.remove_container(name, force=force)
    if result.returncode == 0:
        click.echo(f"Removed: {docker.CONTAINER_PREFIX}{name}")
    raise SystemExit(result.returncode)


@main.command()
@click.option("--agent", "-a", default=None, type=click.Choice(list(docker.AGENTS)), help="Agent to build (omit for all)")
@click.option("--version", "-v", "version", default=None, help="Agent CLI version")
def build(agent, version):
    """Build agent Docker images.

    Builds the base image first, then the specified agent (or all agents).
    """
    click.echo("Building base image...")
    result = docker.build_base()
    if result.returncode != 0:
        raise SystemExit(result.returncode)

    agents_to_build = [agent] if agent else list(docker.AGENTS)

    for a in agents_to_build:
        v = version if agent else None
        info = docker.AGENTS[a]
        display_v = v or info["default_version"]
        click.echo(f"Building {a}:{display_v}...")
        result = docker.build_image(agent=a, version=v)
        if result.returncode != 0:
            click.echo(f"Failed to build {a}", err=True)
            raise SystemExit(result.returncode)
        click.echo(f"  Built: {docker.image_tag(a, v)}")

    click.echo("Done.")


@main.command("extend")
@click.argument("name", required=False)
@click.option("--skill", "-s", multiple=True, help="Geno skillset via geno-tools")
@click.option("--npx-skill", multiple=True, help="Vercel-style skill via npx")
@click.option("--plugin", multiple=True, help="Claude Code plugin from git repo")
@click.option("--mcp-config", type=click.Path(exists=True), help="MCP config file to copy in")
@click.option("--list", "list_ext", is_flag=True, help="List installed extensions")
def extend_cmd(name, skill, npx_skill, plugin, mcp_config, list_ext):
    """Install extensions on a running container.

    \b
    Examples:
        geno-iso extend myproject -s media -s research
        geno-iso extend myproject --npx-skill user/repo
        geno-iso extend myproject --plugin git@github.com:user/plugin.git
        geno-iso extend myproject --mcp-config ./mcp.json
        geno-iso extend myproject --list
    """
    name = name or _pick_one(running_only=True)

    if list_ext or not (skill or npx_skill or plugin or mcp_config):
        click.echo(f"Extensions on {docker.CONTAINER_PREFIX}{name}:")
        result = docker.exec_cmd(name, [docker.GENO_TOOLS, "ls"], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            click.echo(f"\n  Geno skillsets:\n{result.stdout}")
        else:
            click.echo("  Geno skillsets: (none)")
        return

    _install_extensions(name, skill, npx_skill, plugin, mcp_config)
    click.echo("Done.")


@main.command()
def creds():
    """Extract OAuth credentials from macOS Keychain."""
    env_path = _default_env_path()
    cred_data = credentials.extract_from_keychain()
    credentials.write_env_file(env_path, cred_data)
    click.echo(f"Credentials written to {env_path}")


@main.command()
def setup():
    """Sync Dockerfiles from repo to ~/.geno/geno-iso/dockerfiles/."""
    import shutil
    src = Path(__file__).parent.parent / "dockerfiles"
    if not src.exists():
        raise SystemExit(f"Source dockerfiles not found at {src}")
    dst = docker.DOCKERFILES_DIR
    dst.mkdir(parents=True, exist_ok=True)
    for agent_dir in src.iterdir():
        if agent_dir.is_dir() and (agent_dir / "Dockerfile").exists():
            target = dst / agent_dir.name
            target.mkdir(parents=True, exist_ok=True)
            shutil.copy2(agent_dir / "Dockerfile", target / "Dockerfile")
            click.echo(f"  {agent_dir.name}/Dockerfile -> {target}/Dockerfile")
    click.echo(f"Dockerfiles synced to {dst}")
