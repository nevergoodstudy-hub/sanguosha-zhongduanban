#!/usr/bin/env python3
"""Build an MSIX package from the current PyInstaller output."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import build as pyinstaller_build
from versioning import read_declared_version

PROJECT_ROOT = Path(__file__).parent.resolve()
DIST_DIR = PROJECT_ROOT / "dist"
ASSETS_DIR = PROJECT_ROOT / "Assets"
MSIX_DIR = PROJECT_ROOT / "msix_output"

DEFAULT_EXE_NAME = "sanguosha"
DEFAULT_PACKAGE_EXECUTABLE = "sanguosha.exe"
DEFAULT_CERT_PASSWORD_ENV = "SANGUOSHA_MSIX_CERT_PASSWORD"

REQUIRED_ASSET_FILES = (
    "StoreLogo.png",
    "Square44x44Logo.png",
    "Square150x150Logo.png",
    "Wide310x150Logo.png",
    "SplashScreen.png",
)

PLACEHOLDER_ASSET_SIZES = {
    "StoreLogo.png": 50,
    "Square44x44Logo.png": 44,
    "Square150x150Logo.png": 150,
    "Wide310x150Logo.png": 310,
    "SplashScreen.png": 620,
}

PLACEHOLDER_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00"
    b"\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f"
    b"\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00I"
    b"END\xaeB`\x82"
)


def find_makeappx() -> Path | None:
    """Find makeappx.exe from common Windows SDK locations or PATH."""
    sdk_paths = [
        r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.22621.0\x64\makeappx.exe",
        r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.22000.0\x64\makeappx.exe",
        r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.19041.0\x64\makeappx.exe",
        r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.18362.0\x64\makeappx.exe",
        (
            r"C:\Program Files (x86)\Microsoft Visual Studio\Shared\NuGetPackages"
            r"\microsoft.windows.sdk.buildtools\10.0.26100.1742\bin\x64\makeappx.exe"
        ),
    ]
    for raw_path in sdk_paths:
        candidate = Path(raw_path)
        if candidate.exists():
            return candidate

    try:
        result = subprocess.run(["where", "makeappx"], capture_output=True, text=True)
    except OSError:
        result = None

    if result and result.returncode == 0:
        first_match = result.stdout.strip().splitlines()[0]
        return Path(first_match)

    kits_base = Path(r"C:\Program Files (x86)\Windows Kits\10\bin")
    if kits_base.exists():
        for version_dir in sorted(kits_base.iterdir(), reverse=True):
            candidate = version_dir / "x64" / "makeappx.exe"
            if candidate.exists():
                return candidate

    return None


def find_signtool(makeappx_path: Path | None = None) -> Path | None:
    """Find signtool.exe near makeappx.exe or from PATH."""
    search_paths: list[Path] = []
    if makeappx_path is not None:
        search_paths.append(makeappx_path.parent / "signtool.exe")

    for candidate in search_paths:
        if candidate.exists():
            return candidate

    try:
        result = subprocess.run(["where", "signtool"], capture_output=True, text=True)
    except OSError:
        result = None

    if result and result.returncode == 0:
        first_match = result.stdout.strip().splitlines()[0]
        return Path(first_match)

    return None


def get_missing_assets(assets_dir: Path = ASSETS_DIR) -> list[str]:
    """Return required asset filenames that are missing from a directory."""
    return [name for name in REQUIRED_ASSET_FILES if not (assets_dir / name).exists()]


def is_placeholder_asset(asset_path: Path) -> bool:
    """Return True when the asset still matches the generated placeholder PNG."""
    if not asset_path.exists() or not asset_path.is_file():
        return False

    try:
        return asset_path.read_bytes() == PLACEHOLDER_PNG
    except OSError:
        return False


def get_placeholder_assets(assets_dir: Path = ASSETS_DIR) -> list[str]:
    """Return required assets that still use the development placeholder image."""
    return [name for name in REQUIRED_ASSET_FILES if is_placeholder_asset(assets_dir / name)]


def create_assets(assets_dir: Path = ASSETS_DIR) -> None:
    """Create placeholder assets for local validation only."""
    assets_dir.mkdir(parents=True, exist_ok=True)
    for name in REQUIRED_ASSET_FILES:
        target = assets_dir / name
        if target.exists():
            continue

        size = PLACEHOLDER_ASSET_SIZES[name]
        print(f"  Note: creating placeholder asset {name} ({size}px).")
        target.write_bytes(PLACEHOLDER_PNG)


def ensure_assets(
    *,
    assets_dir: Path = ASSETS_DIR,
    allow_placeholder_assets: bool = False,
) -> bool:
    """Ensure the source asset directory contains all required files."""
    missing_assets = get_missing_assets(assets_dir)
    if not missing_assets:
        return True

    if not allow_placeholder_assets:
        print("Error: missing required MSIX asset files:")
        for name in missing_assets:
            print(f"  - {name}")
        print("Provide real assets, or pass --allow-placeholder-assets for local validation.")
        return False

    print("Warning: generating placeholder MSIX assets for local validation only.")
    create_assets(assets_dir)
    return get_missing_assets(assets_dir) == []


def prepare_msix_assets(
    *,
    source_dir: Path = ASSETS_DIR,
    dest_dir: Path,
    allow_placeholder_assets: bool = False,
) -> bool:
    """Copy real assets or explicitly allowed placeholders into the staging directory."""
    dest_dir.mkdir(parents=True, exist_ok=True)

    missing_source_assets = get_missing_assets(source_dir)
    placeholder_source_assets = get_placeholder_assets(source_dir)
    if not missing_source_assets and not placeholder_source_assets:
        for name in REQUIRED_ASSET_FILES:
            shutil.copy2(source_dir / name, dest_dir / name)
        return True

    if not allow_placeholder_assets:
        if missing_source_assets:
            print("Error: missing required MSIX asset files:")
            for name in missing_source_assets:
                print(f"  - {name}")
        if placeholder_source_assets:
            print("Error: placeholder assets are not allowed for a normal MSIX build:")
            for name in placeholder_source_assets:
                print(f"  - {name}")
        print("Provide real assets, or pass --allow-placeholder-assets for local validation.")
        return False

    print("Warning: preparing placeholder assets in the MSIX staging directory.")
    for name in REQUIRED_ASSET_FILES:
        src = source_dir / name
        dst = dest_dir / name
        if src.exists():
            shutil.copy2(src, dst)
            if name in placeholder_source_assets:
                print(f"  Note: reusing placeholder asset {name}.")
            continue

        print(f"  Note: creating placeholder asset {name} in the staging directory.")
        dst.write_bytes(PLACEHOLDER_PNG)

    return get_missing_assets(dest_dir) == []


def resolve_cert_password(
    cert_password: str,
    password_env: str = DEFAULT_CERT_PASSWORD_ENV,
) -> str:
    """Resolve the certificate password from an explicit value or an env var."""
    if cert_password:
        return cert_password
    return os.environ.get(password_env, "")


def get_msix_identity_version(version: str | None = None) -> str:
    """Normalize the project version into the four-part MSIX identity format."""
    raw_version = version or read_declared_version()
    core_version = raw_version.split("+", 1)[0].split("-", 1)[0]
    parts: list[str] = []

    for segment in core_version.split("."):
        digits = "".join(ch for ch in segment if ch.isdigit())
        parts.append(digits or "0")
        if len(parts) == 4:
            break

    while len(parts) < 4:
        parts.append("0")

    return ".".join(parts[:4])


def normalize_package_executable_name(
    name: str = DEFAULT_PACKAGE_EXECUTABLE,
    *,
    platform: str | None = None,
) -> str:
    """Normalize the executable filename used inside the MSIX package."""
    raw_name = (name or DEFAULT_PACKAGE_EXECUTABLE).strip()
    packaged_name = Path(raw_name).name or DEFAULT_PACKAGE_EXECUTABLE

    suffix = pyinstaller_build.executable_suffix(platform=platform)
    if suffix and not packaged_name.lower().endswith(suffix):
        packaged_name = f"{packaged_name}{suffix}"

    return packaged_name


def resolve_source_executable(
    *,
    exe_path: str = "",
    exe_name: str = DEFAULT_EXE_NAME,
    dist_dir: Path = DIST_DIR,
    project_root: Path = PROJECT_ROOT,
    platform: str | None = None,
) -> Path | None:
    """Resolve the built executable produced by build.py."""
    if exe_path:
        explicit_path = Path(exe_path)
        if not explicit_path.is_absolute():
            explicit_path = project_root / explicit_path
        explicit_path = explicit_path.resolve()
        if explicit_path.exists() and explicit_path.is_file():
            return explicit_path
        return None

    requested_name = (exe_name or DEFAULT_EXE_NAME).strip()
    requested_stem = Path(requested_name).stem or DEFAULT_EXE_NAME
    windows_platform = platform or sys.platform
    onefile_path = pyinstaller_build.expected_output_path(
        requested_stem,
        project_root=project_root,
        platform=windows_platform,
    )
    onedir_dir = pyinstaller_build.expected_output_path(
        requested_stem,
        onedir=True,
        project_root=project_root,
        platform=windows_platform,
    )
    onedir_exe = onedir_dir / normalize_package_executable_name(
        requested_stem,
        platform=windows_platform,
    )

    direct_name = dist_dir / requested_name
    nested_name = dist_dir / requested_stem / requested_name

    candidates: list[Path] = []
    for candidate in (onefile_path, onedir_exe, direct_name, nested_name):
        if candidate not in candidates:
            candidates.append(candidate)

    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate.resolve()

    return None


def resolve_payload_root(source_executable: Path, *, dist_dir: Path = DIST_DIR) -> Path:
    """Return the selected PyInstaller payload source for the staged package."""
    try:
        relative_path = source_executable.relative_to(dist_dir)
    except ValueError:
        return source_executable

    if len(relative_path.parts) == 1:
        return source_executable
    return source_executable.parent


def copy_path(source: Path, target: Path) -> None:
    """Copy a file or directory, replacing the target when needed."""
    if target.exists():
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()

    if source.is_dir():
        shutil.copytree(source, target)
        return

    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def stage_dist_payload(
    *,
    source_executable: Path,
    dest_dir: Path,
    package_executable: str = DEFAULT_PACKAGE_EXECUTABLE,
    dist_dir: Path = DIST_DIR,
) -> Path:
    """Stage the chosen PyInstaller payload and rename the main executable if needed."""
    payload_root = resolve_payload_root(source_executable, dist_dir=dist_dir)
    packaged_executable_name = normalize_package_executable_name(package_executable)
    dest_dir.mkdir(parents=True, exist_ok=True)

    if payload_root.is_file():
        copy_path(payload_root, dest_dir / packaged_executable_name)
        return dest_dir / packaged_executable_name

    for item in payload_root.iterdir():
        target_name = packaged_executable_name if item.resolve() == source_executable else item.name
        copy_path(item, dest_dir / target_name)

    return dest_dir / packaged_executable_name


def build_manifest(*, package_executable: str) -> str:
    """Return the AppxManifest.xml content for the staged package."""
    return f"""<?xml version="1.0" encoding="utf-8"?>
<Package xmlns="http://schemas.microsoft.com/appx/manifest/foundation/windows10"
         xmlns:uap="http://schemas.microsoft.com/appx/manifest/uap/windows10"
         xmlns:rescap="http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities"
         IgnorableNamespaces="uap rescap">

  <Identity Name="Sanguosha.Terminal.Game"
            Publisher="CN=SanguoshaTeam"
            Version="{get_msix_identity_version()}"
            ProcessorArchitecture="x64" />

  <Properties>
    <DisplayName>三国杀 Terminal</DisplayName>
    <PublisherDisplayName>Sanguosha Team</PublisherDisplayName>
    <Description>三国杀命令行终端游戏</Description>
    <Logo>Assets\\StoreLogo.png</Logo>
  </Properties>

  <Resources>
    <Resource Language="zh-CN" />
    <Resource Language="en-US" />
  </Resources>

  <Dependencies>
    <TargetDeviceFamily Name="Windows.Desktop"
                        MinVersion="10.0.17763.0"
                        MaxVersionTested="10.0.22621.0" />
  </Dependencies>

  <Capabilities>
    <rescap:Capability Name="runFullTrust" />
  </Capabilities>

  <Applications>
    <Application Id="App"
                 Executable="{package_executable}"
                 EntryPoint="Windows.FullTrustApplication">
      <uap:VisualElements DisplayName="三国杀 Terminal"
                          Description="三国杀命令行终端游戏"
                          BackgroundColor="transparent"
                          Square150x150Logo="Assets\\Square150x150Logo.png"
                          Square44x44Logo="Assets\\Square44x44Logo.png">
        <uap:DefaultTile Wide310x150Logo="Assets\\Wide310x150Logo.png" />
        <uap:SplashScreen Image="Assets\\SplashScreen.png" />
      </uap:VisualElements>
    </Application>
  </Applications>
</Package>
"""


def build_msix(
    *,
    sign: bool = False,
    cert_path: str = "",
    cert_password: str = "",
    cert_password_env: str = DEFAULT_CERT_PASSWORD_ENV,
    allow_placeholder_assets: bool = False,
    exe_path: str = "",
    exe_name: str = DEFAULT_EXE_NAME,
    package_executable: str = DEFAULT_PACKAGE_EXECUTABLE,
) -> int:
    """Build an MSIX package from the current dist payload."""
    packaged_executable_name = normalize_package_executable_name(package_executable)
    source_executable = resolve_source_executable(exe_path=exe_path, exe_name=exe_name)
    if source_executable is None:
        print("Error: built executable not found.")
        print("Run a fresh PyInstaller build first, for example:")
        print(f"  python build.py --name {exe_name}")
        print("Or provide an explicit file via --exe-path.")
        return 1

    if MSIX_DIR.exists():
        shutil.rmtree(MSIX_DIR)
    MSIX_DIR.mkdir(parents=True)

    print("Preparing MSIX staging directory...")
    manifest_path = MSIX_DIR / "AppxManifest.xml"
    manifest_path.write_text(
        build_manifest(package_executable=packaged_executable_name),
        encoding="utf-8",
    )

    msix_assets_dir = MSIX_DIR / "Assets"
    if not prepare_msix_assets(
        source_dir=ASSETS_DIR,
        dest_dir=msix_assets_dir,
        allow_placeholder_assets=allow_placeholder_assets,
    ):
        return 1

    packaged_executable_path = stage_dist_payload(
        source_executable=source_executable,
        dest_dir=MSIX_DIR,
        package_executable=packaged_executable_name,
        dist_dir=DIST_DIR,
    )
    if not packaged_executable_path.exists():
        print(f"Error: staged package executable is missing: {packaged_executable_path}")
        return 1

    makeappx_path = find_makeappx()
    if makeappx_path is None:
        print("Warning: makeappx.exe was not found. The staging directory is ready, but no .msix")
        print("package was produced.")
        print(f"Staging directory: {MSIX_DIR}")
        return 0

    msix_path = PROJECT_ROOT / "sanguosha.msix"
    print(f"Packing MSIX package: {msix_path}")
    result = subprocess.run(
        [str(makeappx_path), "pack", "/d", str(MSIX_DIR), "/p", str(msix_path), "/o"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("Error: makeappx.exe failed.")
        if result.stdout.strip():
            print(result.stdout.strip())
        if result.stderr.strip():
            print(result.stderr.strip())
        return 1

    if sign:
        if not cert_path:
            print("Error: --sign requires --cert to be provided.")
            return 1

        signtool_path = find_signtool(makeappx_path)
        if signtool_path is None:
            print("Warning: signtool.exe was not found, so the package was not signed.")
        else:
            resolved_password = resolve_cert_password(cert_password, cert_password_env)
            sign_cmd = [
                str(signtool_path),
                "sign",
                "/fd",
                "SHA256",
                "/f",
                cert_path,
            ]
            if resolved_password:
                sign_cmd.extend(["/p", resolved_password])
            else:
                print(
                    "Note: no certificate password was provided. Trying to sign without /p; "
                    f"set {cert_password_env} if your certificate requires one."
                )
            sign_cmd.append(str(msix_path))

            sign_result = subprocess.run(sign_cmd, capture_output=True, text=True)
            if sign_result.returncode != 0:
                print("Warning: signing failed.")
                if sign_result.stdout.strip():
                    print(sign_result.stdout.strip())
                if sign_result.stderr.strip():
                    print(sign_result.stderr.strip())

    print(f"Done. Output package: {msix_path}")
    print(f"Main executable inside package: {packaged_executable_name}")
    print(f"Staged source executable: {source_executable}")
    print(f"Package size: {msix_path.stat().st_size / (1024 * 1024):.1f} MB")
    return 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Build an MSIX package from the current PyInstaller output."
    )
    parser.add_argument("--sign", action="store_true", help="Sign the produced MSIX package.")
    parser.add_argument("--cert", default="", help="Path to the signing certificate (.pfx).")
    parser.add_argument(
        "--password",
        default="",
        help="Certificate password. Prefer --password-env in normal use.",
    )
    parser.add_argument(
        "--password-env",
        default=DEFAULT_CERT_PASSWORD_ENV,
        help="Environment variable that stores the certificate password.",
    )
    parser.add_argument(
        "--allow-placeholder-assets",
        action="store_true",
        help="Allow generated placeholder assets for local validation builds.",
    )
    parser.add_argument(
        "--exe-name",
        default=DEFAULT_EXE_NAME,
        help="Executable name produced by build.py --name (default: sanguosha).",
    )
    parser.add_argument(
        "--exe-path",
        default="",
        help="Explicit path to a built executable. Overrides --exe-name.",
    )
    parser.add_argument(
        "--package-executable",
        default=DEFAULT_PACKAGE_EXECUTABLE,
        help="Executable filename referenced inside the MSIX manifest.",
    )
    args = parser.parse_args()

    sys.exit(
        build_msix(
            sign=args.sign,
            cert_path=args.cert,
            cert_password=args.password,
            cert_password_env=args.password_env,
            allow_placeholder_assets=args.allow_placeholder_assets,
            exe_name=args.exe_name,
            exe_path=args.exe_path,
            package_executable=args.package_executable,
        )
    )
