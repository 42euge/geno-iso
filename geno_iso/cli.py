"""CLI for managing isolated coding agent containers."""

import click

from geno_iso import docker, credentials, profiles
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
    return _image_exists_tag(docker.image_tag(agent, version))


def _image_exists_tag(tag: str) -> bool:
    import subprocess
    r = subprocess.run(
        ["docker", "images", "-q", tag],
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
@click.option("--profile", "-p", default="bare", type=click.Choice(profiles.NAMES), help="Skillset profile")
@click.option("--rm", "ephemeral", is_flag=True, help="One-shot mode: run and remove on exit")
@click.option("--version", "-v", "version", default=None, help="Agent CLI version override")
@click.option("--seed-history", is_flag=True, help="Copy host conversation history into the container")
@click.option("--skills", "-s", multiple=True, help="Extra skillsets on top of the profile")
@click.option("--npx-skill", multiple=True, help="Vercel-style skills via npx (e.g. --npx-skill user/repo)")
@click.option("--plugin", multiple=True, help="Claude Code plugins from git repos")
@click.option("--mcp-config", type=click.Path(exists=True), help="MCP config file to copy into container")
@click.argument("agent_args", nargs=-1, type=click.UNPROCESSED)
def run(name, workspace, agent, profile, ephemeral, version, seed_history, skills, npx_skill, plugin, mcp_config, agent_args):
    """Create a persistent container, or run a one-shot with --rm.

    \b
    Profiles bundle skillsets (bare, base, standard, full):
        geno-iso run --profile base dev .
        geno-iso run --profile standard -s geno-media dev .
    """
    ws = Path(workspace) if workspace else Path.cwd()
    name = name or docker.derive_name(ws)

    prof = profiles.resolve(profile)
    profile_df = prof.dockerfile

    v = version or docker.AGENTS[agent]["default_version"]
    if not _image_exists(agent, v):
        click.echo(f"Image not found. Building {agent}...")
        docker.build_image(agent=agent, version=version)
    if profile_df and not _image_exists_tag(docker.image_tag(agent, v, profile_df)):
        click.echo(f"Profile image not found. Building {agent}-{profile_df}...")
        docker.build_profile_image(agent=agent, profile_dockerfile=profile_df, version=version)

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

    result = docker.create_container(
        name=name, workspace=ws, env_file=env_path,
        agent=agent, seed_history=seed_history,
        profile_dockerfile=profile_df,
    )
    if result.returncode != 0:
        raise SystemExit(result.returncode)

    merged_skills = profiles.resolve_skillsets(profile, list(skills))
    _install_extensions(name, merged_skills, npx_skill, plugin, mcp_config)

    click.echo(f"Container ready: {docker.CONTAINER_PREFIX}{name} ({agent}, profile={profile})")
    if merged_skills:
        click.echo(f"  Skillsets:   {', '.join(merged_skills)}")
    if mcp_config:
        click.echo(f"  MCP config:  {mcp_config}")
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

    env_path = _default_env_path()
    credentials.ensure_fresh(env_path)
    docker.inject_env(name, env_path)

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
@click.option("--profile", "-p", default=None, type=click.Choice(profiles.NAMES), help="Also build a profile image layer")
def build(agent, version, profile):
    """Build agent Docker images.

    Builds the base image first, then the specified agent (or all agents).
    Use --profile to also build the profile layer (e.g. --profile full).
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

    if profile:
        prof = profiles.resolve(profile)
        if prof.dockerfile:
            for a in agents_to_build:
                v = version if agent else None
                click.echo(f"Building {a}-{prof.dockerfile}...")
                result = docker.build_profile_image(agent=a, profile_dockerfile=prof.dockerfile, version=v)
                if result.returncode != 0:
                    click.echo(f"Failed to build {a}-{prof.dockerfile}", err=True)
                    raise SystemExit(result.returncode)
                click.echo(f"  Built: {docker.image_tag(a, v, prof.dockerfile)}")
        else:
            click.echo(f"Profile '{profile}' has no extra system deps — no separate image needed.")

    click.echo("Done.")


@main.command("profiles")
def profiles_cmd():
    """List available skillset profiles."""
    for name, prof in profiles.BUILTIN.items():
        skills = ", ".join(prof.skillsets) if prof.skillsets else "(none)"
        marker = " [Dockerfile]" if prof.dockerfile else ""
        click.echo(f"  {name:<12} {prof.description}")
        click.echo(f"  {'':<12} skillsets: {skills}{marker}")
        click.echo()


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
