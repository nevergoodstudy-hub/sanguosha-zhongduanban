"""Tests that packaging metadata stays aligned across repository entry points."""

from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT_TOML = PROJECT_ROOT / "pyproject.toml"
REQUIREMENTS_TXT = PROJECT_ROOT / "requirements.txt"
CI_WORKFLOW = PROJECT_ROOT / ".github" / "workflows" / "ci.yml"
RELEASE_WORKFLOW = PROJECT_ROOT / ".github" / "workflows" / "release.yml"


def _load_requirement_entries(path: Path) -> list[str]:
    entries: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if line:
            entries.append(line)
    return entries


def _load_pyproject_string_literals(path: Path) -> set[str]:
    return set(re.findall(r'"([^"\\]+)"', path.read_text(encoding="utf-8")))


def _entries_for_package(entries: set[str] | list[str], package_name: str) -> set[str]:
    pattern = re.compile(rf"^{re.escape(package_name)}(?=[<>=!~])")
    return {entry for entry in entries if pattern.match(entry)}


def test_requirements_entries_are_declared_in_pyproject():
    requirement_entries = _load_requirement_entries(REQUIREMENTS_TXT)
    pyproject_literals = _load_pyproject_string_literals(PYPROJECT_TOML)

    missing = [entry for entry in requirement_entries if entry not in pyproject_literals]

    assert not missing, (
        f"requirements.txt and pyproject.toml drifted apart; missing from pyproject.toml: {missing}"
    )


def test_pydantic_runtime_pin_matches_in_both_metadata_files():
    requirement_entries = set(_load_requirement_entries(REQUIREMENTS_TXT))
    pyproject_literals = _load_pyproject_string_literals(PYPROJECT_TOML)

    for package_name in ("pydantic", "pydantic-core"):
        requirement_pin = _entries_for_package(requirement_entries, package_name)
        pyproject_pin = _entries_for_package(pyproject_literals, package_name)

        assert requirement_pin == pyproject_pin, (
            f"{package_name} pin drifted between requirements.txt and pyproject.toml: "
            f"{sorted(requirement_pin)} != {sorted(pyproject_pin)}"
        )


def test_build_extra_declares_pyinstaller():
    pyproject_text = PYPROJECT_TOML.read_text(encoding="utf-8")

    assert "build = [" in pyproject_text
    assert '"pyinstaller>=5.0.0"' in pyproject_text


def test_ci_workflow_uses_regular_dev_installs():
    workflow_text = CI_WORKFLOW.read_text(encoding="utf-8")

    assert 'python -m pip install ".[dev]"' in workflow_text
    assert 'python -m pip install -e ".[dev]"' not in workflow_text


def test_release_workflow_uses_build_extra_instead_of_adhoc_install():
    workflow_text = RELEASE_WORKFLOW.read_text(encoding="utf-8")

    assert 'python -m pip install ".[build]"' in workflow_text
    assert "python -m pip install . pyinstaller" not in workflow_text
