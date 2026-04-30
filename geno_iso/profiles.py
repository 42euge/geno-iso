"""Skillset profiles — named bundles of geno-tools skillsets."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Profile:
    name: str
    skillsets: list[str] = field(default_factory=list)
    system_deps: list[str] = field(default_factory=list)
    dockerfile: str | None = None
    description: str = ""


BUILTIN: dict[str, Profile] = {
    "bare": Profile(
        name="bare",
        description="Agent CLI + geno-tools plugin only",
    ),
    "base": Profile(
        name="base",
        skillsets=["geno-dev", "geno-notes", "geno-agents"],
        description="Core dev workflow: dev, notes, agents",
    ),
    "standard": Profile(
        name="standard",
        skillsets=["geno-dev", "geno-notes", "geno-agents", "geno-research", "geno-kaggle"],
        description="Base + research and kaggle",
    ),
    "full": Profile(
        name="full",
        skillsets=["geno-dev", "geno-notes", "geno-agents", "geno-research", "geno-kaggle", "geno-media"],
        system_deps=["ffmpeg", "libcairo2-dev", "libpango1.0-dev"],
        dockerfile="full",
        description="Everything including media creation",
    ),
}

NAMES = list(BUILTIN.keys())


def resolve(name: str) -> Profile:
    if name in BUILTIN:
        return BUILTIN[name]
    raise SystemExit(
        f"Unknown profile: {name}\nAvailable: {', '.join(NAMES)}"
    )


def resolve_skillsets(profile_name: str, extra: list[str] | None = None) -> list[str]:
    profile = resolve(profile_name)
    seen: set[str] = set()
    merged: list[str] = []
    for s in [*profile.skillsets, *(extra or [])]:
        if s not in seen:
            seen.add(s)
            merged.append(s)
    return merged
