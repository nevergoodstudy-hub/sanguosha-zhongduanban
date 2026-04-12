# Release Process

This project uses a tag-driven release flow. GitHub Actions builds cross-platform artifacts and uploads them to a GitHub Release.

## Versioning

- Use semantic version tags in the form `vX.Y.Z`.
- Example: `v4.1.2`
- Keep the `CHANGELOG.md` section title without the `v` prefix, for example `[4.1.2]`.

## Triggers

- Automatic release: pushing a `v*.*.*` tag triggers `.github/workflows/release.yml`.
- The release workflow builds artifacts for all supported platforms and creates or updates the matching GitHub Release.
- Manual validation: `workflow_dispatch` runs build validation only.
- Non-tag runs do not create a GitHub Release.

## Standard Release Steps

1. Confirm local `main` is up to date and key tests are passing.
2. Update `CHANGELOG.md`.
3. Create and push the version tag:

```bash
git tag v4.1.2
git push origin v4.1.2
```

4. Wait for the GitHub Actions `Release` workflow to finish.
5. Verify the Release title, artifacts, and notes on GitHub.

## Pre-release Environment Check

Keep local release validation aligned with CI by installing dependencies from project metadata rather than assembling the environment by hand:

```bash
python -m pip install ".[dev]"
python -c "from pydantic.version import version_info; print(version_info())"
python -m pytest tests/test_build_script.py tests/test_build_msix.py tests/test_dependency_metadata.py tests/test_versioning.py -q
```

- `version_info()` is a quick sanity check for the active `pydantic` and `pydantic-core` combination.
- If the reported versions do not match the current dependency declarations, reinstall the environment before building or tagging.
- The GitHub Release workflow now installs build tooling with `python -m pip install ".[build]"`.
- CI intentionally uses a regular `python -m pip install ".[dev]"` install so it stays closer to release and deployment behavior.

## Release Artifacts

- Windows: `sanguosha-windows-amd64.zip`
- Linux: `sanguosha-linux-amd64.tar.gz`
- macOS: `sanguosha-macos-amd64.tar.gz`

## Artifact Notes

- The Windows artifact is a zip archive containing the PyInstaller-built `.exe`.
- Linux and macOS artifacts are packaged as `tar.gz` archives so executable permissions are preserved.
- The release job publishes artifacts with GitHub CLI via `gh release create` and `gh release upload`, not a third-party release action.

## FAQ

### Why does a manually triggered workflow not create a Release?

That is expected. Only runs triggered from `refs/tags/v*.*.*` enter the publishing stage.

### Why are Linux and macOS artifacts packaged as `tar.gz`?

GitHub Actions artifacts do not preserve POSIX executable bits when they move across jobs. Packaging the binaries as `tar.gz` keeps those permissions intact and avoids extra manual fixups after download.
