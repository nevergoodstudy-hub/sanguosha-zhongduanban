"""Tests for the MSIX packaging helper script."""

import build_msix


class TestBuildMsixHelpers:
    def test_get_missing_assets_reports_all_required_files(self, tmp_path):
        missing = build_msix.get_missing_assets(tmp_path)
        assert missing == list(build_msix.REQUIRED_ASSET_FILES)

    def test_ensure_assets_requires_explicit_placeholder_opt_in(self, tmp_path):
        assert build_msix.ensure_assets(assets_dir=tmp_path, allow_placeholder_assets=False) is False
        assert build_msix.get_missing_assets(tmp_path) == list(build_msix.REQUIRED_ASSET_FILES)

    def test_ensure_assets_creates_placeholders_when_opted_in(self, tmp_path):
        assert build_msix.ensure_assets(assets_dir=tmp_path, allow_placeholder_assets=True) is True
        assert build_msix.get_missing_assets(tmp_path) == []

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
