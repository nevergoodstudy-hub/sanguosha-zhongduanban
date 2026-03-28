"""Project version resolution helpers."""

from __future__ import annotations

from importlib import metadata
from pathlib import Path


def read_declared_version(pyproject_path: Path | None = None) -> str:
    """Read the declared project version from pyproject.toml."""
    path = pyproject_path or Path(__file__).resolve().parent / "pyproject.toml"
    if not path.exists():
        return "0.0.0"

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("version = "):
            return stripped.split("=", 1)[1].strip().strip('"').strip("'")

    return "0.0.0"


def get_project_version(package_name: str = "sanguosha") -> str:
    """Resolve the runtime project version with a pyproject fallback."""
    try:
        return metadata.version(package_name)
    except metadata.PackageNotFoundError:
        return read_declared_version()
