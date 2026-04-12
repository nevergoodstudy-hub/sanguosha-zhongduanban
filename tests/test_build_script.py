"""Tests for the PyInstaller build helper script."""

import shutil
import tempfile
from pathlib import Path
from types import SimpleNamespace

import build


class TestBuildHelpers:
    def test_expected_output_path_uses_exe_suffix_for_windows_onefile(self):
        project_root = Path("D:/example-project")
        expected = project_root / "dist" / "sanguosha.exe"

        actual = build.expected_output_path(
            "sanguosha",
            project_root=project_root,
            platform="win32",
        )

        assert actual == expected

    def test_expected_output_path_uses_plain_name_for_posix_onefile(self):
        project_root = Path("D:/example-project")
        expected = project_root / "dist" / "sanguosha"

        actual = build.expected_output_path(
            "sanguosha",
            project_root=project_root,
            platform="linux",
        )

        assert actual == expected

    def test_expected_output_path_returns_directory_for_onedir(self):
        project_root = Path("D:/example-project")
        expected = project_root / "dist" / "sanguosha"

        actual = build.expected_output_path(
            "sanguosha",
            onedir=True,
            project_root=project_root,
            platform="darwin",
        )

        assert actual == expected

    def test_build_fails_when_pyinstaller_does_not_create_expected_output(self, monkeypatch):
        project_root = Path(tempfile.mkdtemp(prefix="build-script-test-", dir=Path.cwd()))
        monkeypatch.setattr(build, "PROJECT_ROOT", project_root)

        def fake_run(args, cwd):
            return SimpleNamespace(returncode=0)

        monkeypatch.setattr(build.subprocess, "run", fake_run)
        try:
            exit_code = build.build(name="missing-output")
        finally:
            shutil.rmtree(project_root, ignore_errors=True)

        assert exit_code == 1
