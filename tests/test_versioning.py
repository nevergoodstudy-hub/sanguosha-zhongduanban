"""Tests for project version resolution helpers."""

from importlib.metadata import PackageNotFoundError

import versioning


def test_read_declared_version_from_pyproject(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        "[project]\n"
        'name = "sanguosha"\n'
        'version = "9.9.9"\n',
        encoding="utf-8",
    )
    assert versioning.read_declared_version(pyproject) == "9.9.9"


def test_get_project_version_falls_back_to_declared_version(monkeypatch):
    def raise_package_not_found(_package_name):
        raise PackageNotFoundError
    monkeypatch.setattr(versioning.metadata, "version", raise_package_not_found)
    monkeypatch.setattr(versioning, "read_declared_version", lambda *_args, **_kwargs: "9.9.9")

    assert versioning.get_project_version() == "9.9.9"
