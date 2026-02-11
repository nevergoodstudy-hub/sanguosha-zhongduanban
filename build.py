#!/usr/bin/env python3
"""三国杀终端版 - PyInstaller 6.18 构建脚本

使用方法:
    python build.py              # 单文件打包 (默认)
    python build.py --onedir     # 目录模式打包
    python build.py --debug      # 调试模式
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.resolve()
SEP = ";" if sys.platform == "win32" else ":"


def build(*, onedir: bool = False, debug: bool = False, name: str = "sanguosha") -> int:
    # 清理
    for d in ("dist", "build"):
        p = PROJECT_ROOT / d
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)

    args = [
        sys.executable, "-m", "PyInstaller",
        str(PROJECT_ROOT / "main.py"),
        f"--name={name}",
        f"--distpath={PROJECT_ROOT / 'dist'}",
        f"--workpath={PROJECT_ROOT / 'build'}",
        f"--specpath={PROJECT_ROOT}",
        # ===== 数据文件 =====
        f"--add-data={PROJECT_ROOT / 'data'}{SEP}data",
        f"--add-data={PROJECT_ROOT / 'i18n'}{SEP}i18n",
        f"--add-data={PROJECT_ROOT / 'ui' / 'textual_ui' / 'styles'}{SEP}ui/textual_ui/styles",
        # ===== 项目包（完整收集） =====
        "--collect-submodules=game",
        "--collect-submodules=ai",
        "--collect-submodules=ui",
        "--collect-submodules=net",
        "--collect-submodules=i18n",
        # ===== 第三方库动态加载模块 =====
        "--collect-submodules=rich",
        "--collect-submodules=textual",
        # ===== 根级模块 =====
        "--hidden-import=logging_config",
        # ===== 路径 =====
        f"--paths={PROJECT_ROOT}",
        # ===== 排除测试/开发依赖 =====
        "--exclude-module=pytest",
        "--exclude-module=_pytest",
        "--exclude-module=hypothesis",
        "--exclude-module=mypy",
        "--exclude-module=ruff",
        # ===== TUI 需要控制台 =====
        "--console",
        "--noconfirm",
        "--clean",
        "--noupx",
    ]

    # 模式
    args.append("--onedir" if onedir else "--onefile")

    if debug:
        args.append("--debug=all")

    print(f"构建模式: {'目录' if onedir else '单文件'}")
    print(f"Python: {sys.version.split()[0]}")
    print(f"执行 PyInstaller...")

    result = subprocess.run(args, cwd=PROJECT_ROOT)

    # 检查产物
    dist = PROJECT_ROOT / "dist"
    if dist.exists():
        for item in sorted(dist.iterdir()):
            if item.is_file():
                mb = item.stat().st_size / (1024 * 1024)
                print(f"  产物: {item.name} ({mb:.1f} MB)")
            elif item.is_dir():
                total = sum(f.stat().st_size for f in item.rglob("*") if f.is_file())
                print(f"  产物: {item.name}/ ({total / (1024 * 1024):.1f} MB)")

    return result.returncode


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--onedir", action="store_true")
    p.add_argument("--debug", action="store_true")
    p.add_argument("--name", default="sanguosha", help="输出文件名 (默认: sanguosha)")
    a = p.parse_args()
    sys.exit(build(onedir=a.onedir, debug=a.debug, name=a.name))
