#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辉夜IDE 一键构建脚本
支持 Windows / macOS / Linux 平台打包
"""

import os
import sys
import shutil
import subprocess
import platform
import argparse
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
SRC_DIR = os.path.join(SCRIPT_DIR, "src")
DIST_DIR = os.path.join(SCRIPT_DIR, "dist")
BUILD_DIR = os.path.join(SCRIPT_DIR, "build")
ASSETS_DIR = os.path.join(SCRIPT_DIR, "assets")
INSTALLER_DIR = os.path.join(SCRIPT_DIR, "installer")

APP_NAME = "KaguyaIDE"
APP_VERSION = "3.1.0"


def run_cmd(cmd, cwd=None, check=True):
    print(f"[CMD] {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    result = subprocess.run(
        cmd, cwd=cwd or PROJECT_DIR, shell=isinstance(cmd, str),
        capture_output=False, text=True
    )
    if check and result.returncode != 0:
        print(f"[ERROR] Command failed with exit code {result.returncode}")
        sys.exit(1)
    return result


def clean_build_dirs():
    for d in [DIST_DIR, BUILD_DIR]:
        if os.path.exists(d):
            print(f"[CLEAN] Removing {d}")
            shutil.rmtree(d, ignore_errors=True)


def check_dependencies():
    print("[CHECK] Verifying dependencies...")

    required = ["flask", "pywebview"]
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            print(f"[INSTALL] Installing {pkg}...")
            run_cmd([sys.executable, "-m", "pip", "install", pkg, "-q"])

    try:
        import PyInstaller
    except ImportError:
        print("[INSTALL] Installing PyInstaller...")
        run_cmd([sys.executable, "-m", "pip", "install", "pyinstaller", "-q"])


def copy_core_files():
    print("[COPY] Copying core application files...")

    core_files = [
        "qwen3_web.py",
        "ollama_adapter.py",
        "kaguya_file_operations.py",
        "kaguya_permissions.py",
        "kaguya_tool_executor.py",
        "kaguya_file_analyzer.py",
        "kaguya_file_history.py",
        "kaguya_frontend.py",
        "kaguya_bootstrap.py",
        "kaguya_acp.py",
        "kaguya_agents.py",
        "kaguya_feature_flags.py",
        "kaguya_enhanced_features_v2.py",
        "kaguya_accounts.py",
        "kaguya_terminal.py",
        "kaguya_tool_system.py",
        "rbac_system.py",
        "encryption_system.py",
        "rate_limiter.py",
        "secure_sandbox.py",
    ]

    for f in core_files:
        src = os.path.join(PROJECT_DIR, f)
        if os.path.exists(src):
            dst = os.path.join(SRC_DIR, f)
            shutil.copy2(src, dst)
            print(f"  + {f}")
        else:
            print(f"  - {f} (not found, skipping)")


def build_windows():
    print("\n" + "=" * 50)
    print("  Building for Windows")
    print("=" * 50)

    copy_core_files()

    spec_file = os.path.join(SCRIPT_DIR, "kaguya_ide.spec")
    if not os.path.exists(spec_file):
        print("[ERROR] Spec file not found, creating inline build...")
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--name", APP_NAME,
            "--noconfirm",
            "--clean",
            "--windowed",
            "--onedir",
            "--optimize", "2",
            "--add-data", f"{os.path.join(PROJECT_DIR, 'qwen3_web.py')}{os.pathsep}.",
            "--add-data", f"{os.path.join(PROJECT_DIR, 'ollama_adapter.py')}{os.pathsep}.",
            "--hidden-import", "flask",
            "--hidden-import", "jinja2",
            "--hidden-import", "werkzeug",
            "--hidden-import", "webview",
            "--hidden-import", "webview.platforms",
            "--hidden-import", "webview.platforms.winforms",
            "--hidden-import", "sklearn",
            "--hidden-import", "sklearn.feature_extraction.text",
            "--hidden-import", "sklearn.metrics.pairwise",
            "--hidden-import", "numpy",
            "--hidden-import", "PIL",
            "--distpath", DIST_DIR,
            "--workpath", BUILD_DIR,
            os.path.join(SRC_DIR, "kaguya_desktop.py"),
        ]
    else:
        cmd = [
            sys.executable, "-m", "PyInstaller",
            spec_file,
            "--noconfirm",
            "--clean",
            "--distpath", DIST_DIR,
            "--workpath", BUILD_DIR,
        ]

    run_cmd(cmd)

    print("\n[OK] Windows build complete!")
    print(f"  Output: {os.path.join(DIST_DIR, APP_NAME)}")

    return os.path.join(DIST_DIR, APP_NAME)


def build_macos():
    print("\n" + "=" * 50)
    print("  Building for macOS")
    print("=" * 50)

    copy_core_files()

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", APP_NAME,
        "--noconfirm",
        "--clean",
        "--windowed",
        "--onedir",
        "--optimize", "2",
        "--osx-bundle-identifier", "com.kaguya.ide",
        "--add-data", f"{os.path.join(PROJECT_DIR, 'qwen3_web.py')}:.",
        "--add-data", f"{os.path.join(PROJECT_DIR, 'ollama_adapter.py')}:.",
        "--hidden-import", "flask",
        "--hidden-import", "jinja2",
        "--hidden-import", "werkzeug",
        "--hidden-import", "webview",
        "--hidden-import", "webview.platforms",
        "--hidden-import", "webview.platforms.cocoa",
        "--hidden-import", "sklearn",
        "--hidden-import", "sklearn.feature_extraction.text",
        "--hidden-import", "numpy",
        "--hidden-import", "PIL",
        "--distpath", DIST_DIR,
        "--workpath", BUILD_DIR,
        os.path.join(SRC_DIR, "kaguya_desktop.py"),
    ]

    run_cmd(cmd)

    app_bundle = os.path.join(DIST_DIR, f"{APP_NAME}.app")
    if os.path.exists(app_bundle):
        print(f"\n[OK] macOS .app bundle created: {app_bundle}")

        dmg_name = f"{APP_NAME}-{APP_VERSION}.dmg"
        dmg_path = os.path.join(DIST_DIR, dmg_name)
        print(f"[INFO] Creating DMG: {dmg_name}")

        run_cmd([
            "hdiutil", "create", "-volname", APP_NAME,
            "-srcfolder", app_bundle,
            "-ov", "-format", "UDZO",
            dmg_path,
        ], check=False)

        if os.path.exists(dmg_path):
            print(f"[OK] DMG created: {dmg_path}")

    return DIST_DIR


def build_linux():
    print("\n" + "=" * 50)
    print("  Building for Linux")
    print("=" * 50)

    copy_core_files()

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", APP_NAME,
        "--noconfirm",
        "--clean",
        "--windowed",
        "--onedir",
        "--optimize", "2",
        "--add-data", f"{os.path.join(PROJECT_DIR, 'qwen3_web.py')}:.",
        "--add-data", f"{os.path.join(PROJECT_DIR, 'ollama_adapter.py')}:.",
        "--hidden-import", "flask",
        "--hidden-import", "jinja2",
        "--hidden-import", "werkzeug",
        "--hidden-import", "webview",
        "--hidden-import", "webview.platforms",
        "--hidden-import", "webview.platforms.gtk",
        "--hidden-import", "sklearn",
        "--hidden-import", "sklearn.feature_extraction.text",
        "--hidden-import", "numpy",
        "--hidden-import", "PIL",
        "--distpath", DIST_DIR,
        "--workpath", BUILD_DIR,
        os.path.join(SRC_DIR, "kaguya_desktop.py"),
    ]

    run_cmd(cmd)

    app_dir = os.path.join(DIST_DIR, APP_NAME)
    if os.path.exists(app_dir):
        desktop_file = os.path.join(ASSETS_DIR, "kaguya-ide.desktop")
        if os.path.exists(desktop_file):
            shutil.copy2(desktop_file, os.path.join(app_dir, f"{APP_NAME}.desktop"))

        appimage_name = f"{APP_NAME}-{APP_VERSION}-x86_64.AppImage"
        appimage_path = os.path.join(DIST_DIR, appimage_name)
        print(f"[INFO] To create AppImage, install appimagetool and run:")
        print(f"  appimagetool {app_dir} {appimage_path}")

    return DIST_DIR


def create_portable_zip():
    print("\n[PACK] Creating portable ZIP archive...")

    app_dir = os.path.join(DIST_DIR, APP_NAME)
    if not os.path.exists(app_dir):
        print("[ERROR] Build output not found. Run build first.")
        return None

    zip_name = f"{APP_NAME}-{APP_VERSION}-{platform.system().lower()}-portable"
    zip_path = os.path.join(DIST_DIR, zip_name)

    shutil.make_archive(zip_path, "zip", DIST_DIR, APP_NAME)
    print(f"[OK] Portable archive: {zip_path}.zip")

    return f"{zip_path}.zip"


def main():
    parser = argparse.ArgumentParser(description=f"Build {APP_NAME} Desktop")
    parser.add_argument(
        "--platform", "-p",
        choices=["windows", "macos", "linux", "auto"],
        default="auto",
        help="Target platform (default: auto-detect)",
    )
    parser.add_argument("--clean", "-c", action="store_true", help="Clean build dirs first")
    parser.add_argument("--zip", "-z", action="store_true", help="Create portable ZIP after build")
    parser.add_argument("--installer", "-i", action="store_true", help="Create installer after build")
    parser.add_argument("--no-build", action="store_true", help="Skip build, only package")

    args = parser.parse_args()

    target_platform = args.platform
    if target_platform == "auto":
        system = platform.system().lower()
        target_platform = {"windows": "windows", "darwin": "macos", "linux": "linux"}.get(system, "linux")

    print(f"\n{'=' * 60}")
    print(f"  {APP_NAME} v{APP_VERSION} - Desktop Builder")
    print(f"  Platform: {target_platform}")
    print(f"  Python: {sys.version}")
    print(f"{'=' * 60}\n")

    start_time = time.time()

    if args.clean:
        clean_build_dirs()

    if not args.no_build:
        check_dependencies()

        builders = {
            "windows": build_windows,
            "macos": build_macos,
            "linux": build_linux,
        }

        builder = builders.get(target_platform)
        if builder:
            output = builder()
        else:
            print(f"[ERROR] Unsupported platform: {target_platform}")
            sys.exit(1)

    if args.zip:
        create_portable_zip()

    if args.installer and target_platform == "windows":
        print("\n[INSTALLER] To create Windows installer:")
        print(f"  1. Install NSIS from https://nsis.sourceforge.io")
        print(f"  2. Run: makensis {os.path.join(INSTALLER_DIR, 'kaguya_setup.nsi')}")

    elapsed = time.time() - start_time
    print(f"\n{'=' * 60}")
    print(f"  Build completed in {elapsed:.1f}s")
    print(f"  Output: {DIST_DIR}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
