#!/usr/bin/env python3
"""MSIX 包构建脚本.

将三国杀游戏打包为 Microsoft Store 可用的 MSIX 格式.

前置要求:
    - Windows 10/11 SDK
    - makeappx.exe 在 PATH 中
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from versioning import read_declared_version

PROJECT_ROOT = Path(__file__).parent.resolve()
DIST_DIR = PROJECT_ROOT / "dist"
ASSETS_DIR = PROJECT_ROOT / "Assets"
MSIX_DIR = PROJECT_ROOT / "msix_output"
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
    """查找 Windows SDK 中的 makeappx.exe."""
    # 常见SDK路径
    sdk_paths = [
        r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.22621.0\x64\makeappx.exe",
        r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.22000.0\x64\makeappx.exe",
        r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.19041.0\x64\makeappx.exe",
        r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.18362.0\x64\makeappx.exe",
        # VS集成的NuGet包
        r"C:\Program Files (x86)\Microsoft Visual Studio\Shared\NuGetPackages\microsoft.windows.sdk.buildtools\10.0.26100.1742\bin\x64\makeappx.exe",
    ]
    for path in sdk_paths:
        if Path(path).exists():
            return Path(path)

    # 尝试从 PATH 查找
    try:
        result = subprocess.run(
            ["where", "makeappx"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return Path(result.stdout.strip().split("\n")[0])
    except Exception:
        pass

    # 尝试搜索Windows Kits目录
    kits_base = r"C:\Program Files (x86)\Windows Kits\10\bin"
    if Path(kits_base).exists():
        for version_dir in sorted(Path(kits_base).iterdir(), reverse=True):
            if version_dir.is_dir():
                makeappx_path = version_dir / "x64" / "makeappx.exe"
                if makeappx_path.exists():
                    return makeappx_path

    return None


def get_missing_assets(assets_dir: Path = ASSETS_DIR) -> list[str]:
    """返回缺失的必需资源文件名列表."""
    return [name for name in REQUIRED_ASSET_FILES if not (assets_dir / name).exists()]


def create_assets(assets_dir: Path = ASSETS_DIR) -> None:
    """创建开发占位资源文件."""
    assets_dir.mkdir(parents=True, exist_ok=True)
    for name, size in PLACEHOLDER_ASSET_SIZES.items():
        path = assets_dir / name
        if not path.exists():
            print(f"  注意: 创建开发占位图标 {name} ({size}px)，请勿用于正式发布")
            path.write_bytes(PLACEHOLDER_PNG)


def ensure_assets(
    *, assets_dir: Path = ASSETS_DIR, allow_placeholder_assets: bool = False
) -> bool:
    """确保目标目录包含构建所需资源."""
    missing_assets = get_missing_assets(assets_dir)
    if not missing_assets:
        return True

    if not allow_placeholder_assets:
        print("错误: 缺少以下 MSIX 资源文件:")
        for name in missing_assets:
            print(f"  - {name}")
        print("请提供真实资源文件，或仅在开发验证时显式传入 --allow-placeholder-assets。")
        return False

    print("警告: 正在生成开发占位图标，请勿将其用于正式发布。")
    create_assets(assets_dir)
    return get_missing_assets(assets_dir) == []


def prepare_msix_assets(
    *, source_dir: Path = ASSETS_DIR, dest_dir: Path, allow_placeholder_assets: bool = False
) -> bool:
    """准备 MSIX 输出目录中的资源文件."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    missing_source_assets = get_missing_assets(source_dir)
    if not missing_source_assets:
        for name in REQUIRED_ASSET_FILES:
            shutil.copy2(source_dir / name, dest_dir / name)
        return True

    if not allow_placeholder_assets:
        print("错误: 缺少以下 MSIX 资源文件:")
        for name in missing_source_assets:
            print(f"  - {name}")
        print("请在 Assets 目录提供真实资源文件，或仅在开发验证时显式传入 --allow-placeholder-assets。")
        return False

    print("警告: Assets 目录不完整，正在输出目录中生成开发占位图标。")
    return ensure_assets(assets_dir=dest_dir, allow_placeholder_assets=True)


def resolve_cert_password(
    cert_password: str, password_env: str = DEFAULT_CERT_PASSWORD_ENV
) -> str:
    """解析证书密码，优先显式参数，其次环境变量."""
    if cert_password:
        return cert_password
    return os.environ.get(password_env, "")


def get_msix_identity_version(version: str | None = None) -> str:
    """将项目版本转换为 MSIX 需要的四段数字版本号."""
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


def build_msix(
    *,
    sign: bool = False,
    cert_path: str = "",
    cert_password: str = "",
    cert_password_env: str = DEFAULT_CERT_PASSWORD_ENV,
    allow_placeholder_assets: bool = False,
) -> int:
    """构建 MSIX 包.

    Args:
        sign: 是否签名
        cert_path: 证书路径
        cert_password: 证书密码
        cert_password_env: 读取证书密码的环境变量名
        allow_placeholder_assets: 是否允许生成开发占位图标

    Returns:
        0 表示成功
    """
    # 清理输出目录
    if MSIX_DIR.exists():
        shutil.rmtree(MSIX_DIR)
    MSIX_DIR.mkdir()

    # 检查可执行文件
    exe_path = DIST_DIR / "sanguosha.exe"
    if not exe_path.exists():
        print("错误: 未找到可执行文件, 请先运行: python build.py")
        return 1


    # 复制文件到 MSIX 目录
    print("准备 MSIX 内容...")

    # 创建 AppxManifest.xml
    manifest_content = f"""<?xml version="1.0" encoding="utf-8"?>
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
    <Description>三国杀命令行终端游戏 - A classic Chinese card game in your terminal</Description>
    <Logo>Assets\\StoreLogo.png</Logo>
  </Properties>

  <Resources>
    <Resource Language="zh-CN" />
    <Resource Language="en-US" />
  </Resources>

  <Dependencies>
    <TargetDeviceFamily Name="Windows.Desktop" MinVersion="10.0.17763.0" MaxVersionTested="10.0.22621.0" />
  </Dependencies>

  <Capabilities>
    <rescap:Capability Name="runFullTrust" />
  </Capabilities>

  <Applications>
    <Application Id="App"
                 Executable="sanguosha.exe"
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
</Package>"""

    (MSIX_DIR / "AppxManifest.xml").write_text(manifest_content, encoding="utf-8")

    msix_assets = MSIX_DIR / "Assets"
    print("检查资源文件...")
    if not prepare_msix_assets(
        source_dir=ASSETS_DIR,
        dest_dir=msix_assets,
        allow_placeholder_assets=allow_placeholder_assets,
    ):
        return 1

    # 复制可执行文件和数据
    for item in DIST_DIR.glob("*"):
        if item.is_file():
            shutil.copy2(item, MSIX_DIR / item.name)

    # 复制数据文件夹
    for data_dir in ["data", "i18n", "ui"]:
        src = PROJECT_ROOT / data_dir
        if src.exists():
            dst = MSIX_DIR / data_dir
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)

    # 查找 makeappx
    makeappx = find_makeappx()
    if not makeappx:
        print("警告: 找不到 makeappx.exe, 无法创建 MSIX 包")
        print("请安装 Windows SDK 并确保 makeappx.exe 在 PATH 中")
        print(f"MSIX 预备内容已准备在: {MSIX_DIR}")
        return 0

    # 创建 MSIX
    msix_path = PROJECT_ROOT / "sanguosha.msix"
    print(f"创建 MSIX 包: {msix_path}")

    result = subprocess.run(
        [str(makeappx), "pack", "/d", str(MSIX_DIR), "/p", str(msix_path), "/o"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print("错误: makeappx 失败")
        print(result.stderr)
        return 1

    # 签名
    if sign and not cert_path:
        print("错误: 启用签名时必须提供 --cert 证书路径")
        return 1

    if sign and cert_path:
        signtool = makeappx.parent / "signtool.exe"
        if signtool.exists():
            resolved_password = resolve_cert_password(cert_password, cert_password_env)
            print("签名 MSIX 包...")
            sign_cmd = [
                str(signtool),
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
                    f"提示: 未提供显式证书密码；可通过环境变量 {cert_password_env} 提供，"
                    "当前将尝试无密码签名。"
                )
            sign_cmd.append(str(msix_path))
            result = subprocess.run(
                sign_cmd,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                print("警告: 签名失败")
                print(result.stderr)
        else:
            print("警告: 找不到 signtool.exe, 跳过签名")

    print(f"\n完成! 输出: {msix_path}")
    print(f"大小: {msix_path.stat().st_size / (1024*1024):.1f} MB")

    return 0


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="构建 MSIX 包")
    p.add_argument("--sign", action="store_true", help="签名 MSIX 包")
    p.add_argument("--cert", default="", help="证书路径")
    p.add_argument("--password", default="", help="证书密码（不推荐，优先使用 --password-env）")
    p.add_argument(
        "--password-env",
        default=DEFAULT_CERT_PASSWORD_ENV,
        help="从环境变量读取证书密码",
    )
    p.add_argument(
        "--allow-placeholder-assets",
        action="store_true",
        help="允许自动生成开发占位图标",
    )
    a = p.parse_args()
    sys.exit(
        build_msix(
            sign=a.sign,
            cert_path=a.cert,
            cert_password=a.password,
            cert_password_env=a.password_env,
            allow_placeholder_assets=a.allow_placeholder_assets,
        )
    )
