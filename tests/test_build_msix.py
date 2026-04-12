"""Tests for the MSIX packaging helper script."""

import shutil
import tempfile
from pathlib import Path

import pytest

import build_msix


@pytest.fixture
def workspace_tmp_path():
    path = Path(tempfile.mkdtemp(prefix="build-msix-test-", dir=Path.cwd()))
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


class TestBuildMsixHelpers:
    def test_get_missing_assets_reports_all_required_files(self, workspace_tmp_path):
        missing = build_msix.get_missing_assets(workspace_tmp_path)
        assert missing == list(build_msix.REQUIRED_ASSET_FILES)

    def test_get_placeholder_assets_detects_placeholder_files(self, workspace_tmp_path):
        for name in build_msix.REQUIRED_ASSET_FILES:
            (workspace_tmp_path / name).write_bytes(build_msix.PLACEHOLDER_PNG)

        placeholders = build_msix.get_placeholder_assets(workspace_tmp_path)
        assert placeholders == list(build_msix.REQUIRED_ASSET_FILES)

    def test_ensure_assets_requires_explicit_placeholder_opt_in(self, workspace_tmp_path):
        assert (
            build_msix.ensure_assets(
                assets_dir=workspace_tmp_path,
                allow_placeholder_assets=False,
            )
            is False
        )
        assert build_msix.get_missing_assets(workspace_tmp_path) == list(
            build_msix.REQUIRED_ASSET_FILES
        )

    def test_ensure_assets_creates_placeholders_when_opted_in(self, workspace_tmp_path):
        assert (
            build_msix.ensure_assets(
                assets_dir=workspace_tmp_path,
                allow_placeholder_assets=True,
            )
            is True
        )
        assert build_msix.get_missing_assets(workspace_tmp_path) == []

    def test_prepare_msix_assets_rejects_placeholder_source_without_opt_in(
        self, workspace_tmp_path
    ):
        source_dir = workspace_tmp_path / "source"
        dest_dir = workspace_tmp_path / "dest"
        source_dir.mkdir()
        for name in build_msix.REQUIRED_ASSET_FILES:
            (source_dir / name).write_bytes(build_msix.PLACEHOLDER_PNG)

        assert (
            build_msix.prepare_msix_assets(
                source_dir=source_dir,
                dest_dir=dest_dir,
                allow_placeholder_assets=False,
            )
            is False
        )

    def test_prepare_msix_assets_allows_placeholder_source_with_opt_in(self, workspace_tmp_path):
        source_dir = workspace_tmp_path / "source"
        dest_dir = workspace_tmp_path / "dest"
        source_dir.mkdir()
        for name in build_msix.REQUIRED_ASSET_FILES:
            (source_dir / name).write_bytes(build_msix.PLACEHOLDER_PNG)

        assert (
            build_msix.prepare_msix_assets(
                source_dir=source_dir,
                dest_dir=dest_dir,
                allow_placeholder_assets=True,
            )
            is True
        )
        assert build_msix.get_missing_assets(dest_dir) == []
        assert build_msix.get_placeholder_assets(dest_dir) == list(build_msix.REQUIRED_ASSET_FILES)

    def test_resolve_cert_password_prefers_explicit_value(self, monkeypatch):
        monkeypatch.setenv("TEST_MSIX_PASSWORD", "env-secret")
        assert build_msix.resolve_cert_password("cli-secret", "TEST_MSIX_PASSWORD") == "cli-secret"

    def test_resolve_cert_password_reads_environment(self, monkeypatch):
        monkeypatch.setenv("TEST_MSIX_PASSWORD", "env-secret")
        assert build_msix.resolve_cert_password("", "TEST_MSIX_PASSWORD") == "env-secret"

    def test_get_msix_identity_version_pads_semver(self):
        assert build_msix.get_msix_identity_version("4.1.0") == "4.1.0.0"
        assert build_msix.get_msix_identity_version("4.1") == "4.1.0.0"
        assert build_msix.get_msix_identity_version("4.1.0-beta.1") == "4.1.0.0"

    def test_resolve_source_executable_finds_onefile_output_by_name(self, workspace_tmp_path):
        dist_dir = workspace_tmp_path / "dist"
        dist_dir.mkdir()
        exe_path = dist_dir / "custom-build.exe"
        exe_path.write_text("stub", encoding="utf-8")

        resolved = build_msix.resolve_source_executable(
            exe_name="custom-build",
            dist_dir=dist_dir,
            project_root=workspace_tmp_path,
            platform="win32",
        )

        assert resolved == exe_path.resolve()

    def test_resolve_source_executable_finds_onedir_output_by_name(self, workspace_tmp_path):
        dist_dir = workspace_tmp_path / "dist"
        exe_dir = dist_dir / "custom-build"
        exe_dir.mkdir(parents=True)
        exe_path = exe_dir / "custom-build.exe"
        exe_path.write_text("stub", encoding="utf-8")

        resolved = build_msix.resolve_source_executable(
            exe_name="custom-build",
            dist_dir=dist_dir,
            project_root=workspace_tmp_path,
            platform="win32",
        )

        assert resolved == exe_path.resolve()

    def test_stage_dist_payload_renames_selected_executable(self, workspace_tmp_path):
        dist_dir = workspace_tmp_path / "dist"
        payload_dir = dist_dir / "custom-build"
        payload_dir.mkdir(parents=True)

        exe_path = payload_dir / "custom-build.exe"
        exe_path.write_text("exe", encoding="utf-8")
        support_file = payload_dir / "library.dll"
        support_file.write_text("dll", encoding="utf-8")

        staged_dir = workspace_tmp_path / "msix_output"
        packaged_exe = build_msix.stage_dist_payload(
            source_executable=exe_path.resolve(),
            dest_dir=staged_dir,
            package_executable="sanguosha.exe",
            dist_dir=dist_dir,
        )

        assert packaged_exe == staged_dir / "sanguosha.exe"
        assert packaged_exe.read_text(encoding="utf-8") == "exe"
        assert (staged_dir / "library.dll").read_text(encoding="utf-8") == "dll"
        assert not (staged_dir / "custom-build.exe").exists()

    def test_stage_dist_payload_only_copies_selected_onefile_build(self, workspace_tmp_path):
        dist_dir = workspace_tmp_path / "dist"
        dist_dir.mkdir()

        exe_path = dist_dir / "custom-build.exe"
        exe_path.write_text("exe", encoding="utf-8")
        unrelated_file = dist_dir / "other-build.exe"
        unrelated_file.write_text("other", encoding="utf-8")
        unrelated_dir = dist_dir / "other-build"
        unrelated_dir.mkdir()
        (unrelated_dir / "helper.dll").write_text("dll", encoding="utf-8")

        staged_dir = workspace_tmp_path / "msix_output"
        packaged_exe = build_msix.stage_dist_payload(
            source_executable=exe_path.resolve(),
            dest_dir=staged_dir,
            package_executable="sanguosha.exe",
            dist_dir=dist_dir,
        )

        assert packaged_exe == staged_dir / "sanguosha.exe"
        assert packaged_exe.read_text(encoding="utf-8") == "exe"
        assert sorted(path.name for path in staged_dir.iterdir()) == ["sanguosha.exe"]
