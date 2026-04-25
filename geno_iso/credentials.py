"""OAuth credential extraction from macOS Keychain."""

import json
import os
import platform
import subprocess
import tempfile
import time
from pathlib import Path


def extract_from_keychain() -> dict[str, str]:
    if platform.system() != "Darwin":
        raise SystemExit(
            "Credential extraction only works on macOS.\n"
            "On other platforms, create .env manually with CLAUDE_CODE_OAUTH_TOKEN or ANTHROPIC_API_KEY."
        )

    result = subprocess.run(
        ["security", "find-generic-password", "-s", "Claude Code-credentials", "-w"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise SystemExit(
            "Could not read credentials from macOS Keychain.\n"
            "Ensure Claude Code is installed and you're logged in (claude auth login)."
        )

    creds = json.loads(result.stdout.strip())
    oauth = creds["claudeAiOauth"]

    return {
        "CLAUDE_CODE_OAUTH_TOKEN": oauth["accessToken"],
        "CLAUDE_CODE_OAUTH_REFRESH_TOKEN": oauth["refreshToken"],
        "CLAUDE_CODE_OAUTH_SCOPES": " ".join(oauth["scopes"]),
    }


def write_env_file(env_path: Path, creds: dict[str, str]) -> None:
    content = "\n".join(f"{k}={v}" for k, v in creds.items()) + "\n"
    fd, tmp = tempfile.mkstemp(dir=env_path.parent, suffix=".env.tmp")
    try:
        os.write(fd, content.encode())
        os.close(fd)
        os.replace(tmp, env_path)
    except BaseException:
        os.close(fd) if not os.get_inheritable(fd) else None
        os.unlink(tmp)
        raise


def ensure_fresh(env_path: Path, max_age_hours: float = 4.0) -> Path:
    if env_path.exists():
        age_hours = (time.time() - env_path.stat().st_mtime) / 3600
        if age_hours < max_age_hours:
            return env_path

    creds = extract_from_keychain()
    write_env_file(env_path, creds)
    return env_path
