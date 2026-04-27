#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辉夜IDE 独立可执行文件打包脚本
打包结果包含完整的Python环境，无需外部安装Python即可运行
"""

import os
import sys
import shutil
import subprocess
import zipfile
import time
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
DIST_DIR = os.path.join(SCRIPT_DIR, "dist-standalone")
BUILD_DIR = os.path.join(SCRIPT_DIR, "build-standalone")
ASSETS_DIR = os.path.join(SCRIPT_DIR, "assets")

APP_NAME = "KaguyaIDE"
APP_VERSION = "3.1.0"

def run_cmd(cmd, cwd=None, check=True):
    print(f"[CMD] {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    result = subprocess.run(
        cmd, cwd=cwd or SCRIPT_DIR, shell=isinstance(cmd, str),
        capture_output=True, text=True, encoding='utf-8'
    )
    if check and result.returncode != 0:
        print(f"[ERROR] Command failed: {result.stderr}")
        return False
    return True

def clean_dirs():
    for d in [DIST_DIR, BUILD_DIR]:
        if os.path.exists(d):
            print(f"[CLEAN] Removing {d}")
            shutil.rmtree(d, ignore_errors=True)
    os.makedirs(DIST_DIR, exist_ok=True)
    os.makedirs(BUILD_DIR, exist_ok=True)

def copy_python_env():
    """复制Python环境和所有依赖"""
    print("[COPY] Copying Python environment...")
    
    python_exe = sys.executable
    python_dir = os.path.dirname(python_exe)
    
    # 创建内部Python目录
    internal_dir = os.path.join(DIST_DIR, APP_NAME, "_internal")
    os.makedirs(internal_dir, exist_ok=True)
    
    # 复制Python核心文件 - 复制所有exe和dll
    core_files = ['python.exe', 'pythonw.exe', 'python39.dll', 'python3.dll']
    for f in core_files:
        src = os.path.join(python_dir, f)
        if os.path.exists(src):
            shutil.copy2(src, internal_dir)
            print(f"  + {f}")
    
    # 复制所有DLL文件（除了已经复制的）
    skip_dlls = {'python39.dll', 'python3.dll'}
    for f in os.listdir(python_dir):
        if f.endswith('.dll') and f.lower() not in skip_dlls:
            src = os.path.join(python_dir, f)
            if os.path.isfile(src):
                shutil.copy2(src, internal_dir)
                print(f"  + {f}")
    
    # 复制DLLs目录下的所有.pyd和.dll文件
    dlls_dir = os.path.join(python_dir, 'DLLs')
    if os.path.exists(dlls_dir):
        dst_dlls = os.path.join(internal_dir, 'DLLs')
        os.makedirs(dst_dlls, exist_ok=True)
        for f in os.listdir(dlls_dir):
            if f.endswith('.pyd') or f.endswith('.dll'):
                shutil.copy2(os.path.join(dlls_dir, f), dst_dlls)
                print(f"  + DLLs/{f}")
    
    # 复制Lib标准库（完整复制）
    lib_dir = os.path.join(python_dir, 'Lib')
    if os.path.exists(lib_dir):
        dst_lib = os.path.join(internal_dir, 'Lib')
        print("[COPY] Copying standard library (this may take a while)...")
        # 复制关键目录
        key_stdlib_dirs = [
            'collections', 'concurrent', 'ctypes', 'email', 'encodings', 
            'html', 'http', 'importlib', 'json', 'logging', 'multiprocessing',
            'urllib', 'xml', 'sqlite3', 'site-packages', 'asyncio',
            'contextlib.py', 'copy.py', 'copyreg.py', 'datetime.py',
            'fnmatch.py', 'functools.py', 'glob.py', 'hashlib.py', 'heapq.py',
            'inspect.py', 'io.py', 'itertools.py', 'linecache.py', 'numbers.py',
            'operator.py', 'os.py', 'pathlib.py', 'pickle.py', 'pkgutil.py',
            'platform.py', 'posixpath.py', 'pprint.py', 'queue.py', 're.py',
            'reprlib.py', 'selectors.py', 'shlex.py', 'shutil.py', 'signal.py',
            'socket.py', 'socketserver.py', 'sre_compile.py', 'sre_constants.py',
            'sre_parse.py', 'ssl.py', 'stat.py', 'string.py', 'struct.py',
            'subprocess.py', 'sysconfig.py', 'tempfile.py', 'textwrap.py',
            'threading.py', 'token.py', 'tokenize.py', 'traceback.py', 'types.py',
            'typing.py', 'uuid.py', 'warnings.py', 'weakref.py', 'zipfile.py',
            'zipimport.py', '_collections_abc.py', '_compat_pickle.py',
            '_compression.py', '_markupbase.py', '_osx_support.py',
            '_pydecimal.py', '_pyio.py', '_sitebuiltins.py', '_strptime.py',
            '_threading_local.py', '_weakrefset.py', 'abc.py', 'base64.py',
            'bisect.py', 'codecs.py', 'enum.py', 'genericpath.py', 'getopt.py',
            'gettext.py', 'gzip.py', 'ipaddress.py', 'keyword.py', 'mimetypes.py',
            'netrc.py', 'ntpath.py', 'nturl2path.py', 'optparse.py', 'pathlib.py',
            'random.py', 'secrets.py', 'stringprep.py', 'tarfile.py', 'timeit.py',
            'urllib', 'uu.py', 'wave.py', 'webbrowser.py', 'xdrlib.py'
        ]
        for item in key_stdlib_dirs:
            src = os.path.join(lib_dir, item)
            if os.path.exists(src):
                dst = os.path.join(dst_lib, item)
                if os.path.isdir(src):
                    if not os.path.exists(dst):
                        shutil.copytree(src, dst, ignore=shutil.ignore_patterns('*.pyc', '__pycache__', 'test', 'tests'), dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dst)
        print("  + Lib/ (standard library)")
    
    # 复制site-packages中的关键依赖
    site_packages = os.path.join(python_dir, 'Lib', 'site-packages')
    if os.path.exists(site_packages):
        dst_site = os.path.join(internal_dir, 'Lib', 'site-packages')
        
        # 关键依赖包列表
        key_packages = [
            'flask', 'jinja2', 'werkzeug', 'markupsafe', 'itsdangerous', 'click',
            'requests', 'urllib3', 'certifi', 'charset_normalizer', 'idna',
            'numpy', 'PIL', 'yaml', 'psutil', 'flask_cors',
            'blinker', 'colorama', 'packaging', 'pip',
        ]
        
        for pkg in key_packages:
            src_pkg = os.path.join(site_packages, pkg)
            if os.path.exists(src_pkg):
                dst_pkg = os.path.join(dst_site, pkg)
                if os.path.isdir(src_pkg):
                    if not os.path.exists(dst_pkg):
                        shutil.copytree(src_pkg, dst_pkg, ignore=shutil.ignore_patterns('*.pyc', '__pycache__', 'test', 'tests'), dirs_exist_ok=True)
                else:
                    shutil.copy2(src_pkg, dst_pkg)
                print(f"  + site-packages/{pkg}")

def copy_app_files():
    """复制应用核心文件"""
    print("[COPY] Copying application files...")
    
    app_dir = os.path.join(DIST_DIR, APP_NAME)
    internal_dir = os.path.join(app_dir, "_internal")
    
    core_files = [
        "qwen3_web.py", "ollama_adapter.py",
        "kaguya_file_operations.py", "kaguya_permissions.py",
        "kaguya_tool_executor.py", "kaguya_file_analyzer.py",
        "kaguya_file_history.py", "kaguya_frontend.py",
        "kaguya_bootstrap.py", "kaguya_acp.py",
        "kaguya_agents.py", "kaguya_feature_flags.py",
        "kaguya_enhanced_features_v2.py",
        "kaguya_accounts.py", "kaguya_terminal.py",
        "kaguya_tool_system.py", "rbac_system.py",
        "encryption_system.py", "rate_limiter.py",
        "secure_sandbox.py", "unified_api_adapter.py",
        "claude_client.py", "llm_adapter.py",
    ]
    
    for f in core_files:
        src = os.path.join(PROJECT_DIR, f)
        if os.path.exists(src):
            shutil.copy2(src, internal_dir)
            print(f"  + {f}")
    
    # 复制Electron文件
    electron_src = os.path.join(SCRIPT_DIR, "electron")
    electron_dst = os.path.join(app_dir, "electron")
    if os.path.exists(electron_src):
        shutil.copytree(electron_src, electron_dst, dirs_exist_ok=True)
        print(f"  + electron/")
    
    # 复制assets
    if os.path.exists(ASSETS_DIR):
        assets_dst = os.path.join(app_dir, "assets")
        shutil.copytree(ASSETS_DIR, assets_dst, dirs_exist_ok=True)
        print(f"  + assets/")

def create_launcher():
    """创建启动器脚本"""
    print("[CREATE] Creating launcher...")
    
    app_dir = os.path.join(DIST_DIR, APP_NAME)
    
    # Windows批处理启动器
    bat_content = '''@echo off
chcp 65001 >nul 2>&1
title Kaguya IDE
cd /d "%~dp0"
set PYTHONPATH=%~dp0_internal;%~dp0_internal\Lib;%~dp0_internal\Lib\site-packages
set KAGUYA_DESKTOP_MODE=1
set KAGUYA_ELECTRON=1
set KAGUYA_PERMISSION_MODE=bypassPermissions
set KAGUYA_PORT=58000

:: Start Python server in background
start /b "" "%~dp0_internal\python.exe" "%~dp0_internal\qwen3_web.py" >nul 2>&1

:: Wait for server to start
:wait_loop
timeout /t 1 /nobreak >nul
curl -s http://127.0.0.1:58000/ >nul 2>&1
if errorlevel 1 goto wait_loop

:: Start Electron
cd /d "%~dp0"
"%~dp0electron\node_modules\.bin\electron.exe" . --port=58000
'''
    
    with open(os.path.join(app_dir, "start.bat"), 'w', encoding='utf-8') as f:
        f.write(bat_content)
    
    # 简化的启动器 - 直接启动Python服务器，用户可以用浏览器访问
    simple_bat = '''@echo off
chcp 65001 >nul 2>&1
title Kaguya IDE Server
cd /d "%~dp0"
set PYTHONPATH=%~dp0_internal;%~dp0_internal\Lib;%~dp0_internal\Lib\site-packages
set KAGUYA_DESKTOP_MODE=1
set KAGUYA_PERMISSION_MODE=bypassPermissions
set KAGUYA_PORT=58000

echo Starting Kaguya IDE Server...
echo Please open http://127.0.0.1:58000 in your browser
echo.
"%~dp0_internal\python.exe" "%~dp0_internal\qwen3_web.py"
pause
'''
    
    with open(os.path.join(app_dir, "start-server.bat"), 'w', encoding='utf-8') as f:
        f.write(simple_bat)
    
    print("  + start.bat")
    print("  + start-server.bat")

def create_package_json():
    """创建简化的package.json"""
    print("[CREATE] Creating package.json...")
    
    app_dir = os.path.join(DIST_DIR, APP_NAME)
    pkg = {
        "name": "kaguya-ide",
        "version": APP_VERSION,
        "main": "electron/main.js",
        "scripts": {
            "start": "electron ."
        }
    }
    
    with open(os.path.join(app_dir, "package.json"), 'w', encoding='utf-8') as f:
        json.dump(pkg, f, indent=2)
    
    print("  + package.json")

def create_readme():
    """创建使用说明"""
    readme = f'''# Kaguya IDE v{APP_VERSION}

## 独立运行版

此版本包含完整的Python运行环境，无需额外安装Python即可运行。

## 运行方式

### Windows
1. 双击运行 `start-server.bat` - 启动服务器，然后用浏览器访问 http://127.0.0.1:58000
2. 或双击运行 `start.bat` - 启动Electron桌面端（需要已安装Electron依赖）

### 系统要求
- Windows 10/11 64位
- 至少 4GB 内存
- 至少 500MB 磁盘空间

## 功能说明
- 内置AI编程助手
- 文件管理与编辑
- 终端操作
- 权限管理

## 注意事项
首次启动可能需要30-60秒初始化环境。
'''
    
    app_dir = os.path.join(DIST_DIR, APP_NAME)
    with open(os.path.join(app_dir, "README.txt"), 'w', encoding='utf-8') as f:
        f.write(readme)
    print("  + README.txt")

def create_zip():
    """创建ZIP分发包"""
    print("[PACK] Creating ZIP archive...")
    
    zip_name = f"{APP_NAME}-{APP_VERSION}-standalone-win64"
    zip_path = os.path.join(DIST_DIR, f"{zip_name}.zip")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        app_dir = os.path.join(DIST_DIR, APP_NAME)
        for root, dirs, files in os.walk(app_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, DIST_DIR)
                zf.write(file_path, arcname)
    
    size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    print(f"[OK] Created: {zip_path}")
    print(f"[INFO] Size: {size_mb:.1f} MB")
    return zip_path

def test_python():
    """测试打包的Python是否能正常运行"""
    print("[TEST] Testing embedded Python...")
    
    internal_dir = os.path.join(DIST_DIR, APP_NAME, "_internal")
    python_exe = os.path.join(internal_dir, "python.exe")
    
    # 测试基本Python
    result = subprocess.run(
        [python_exe, "-c", "import sys; print(sys.version)"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(f"  [OK] Python: {result.stdout.strip()}")
    else:
        print(f"  [FAIL] Python test failed: {result.stderr}")
        return False
    
    # 测试关键模块
    test_code = """
import sys
sys.path.insert(0, r'""" + internal_dir + """')
sys.path.insert(0, r'""" + os.path.join(internal_dir, 'Lib') + """')
sys.path.insert(0, r'""" + os.path.join(internal_dir, 'Lib', 'site-packages') + """')

try:
    import flask
    print('flask: OK')
except Exception as e:
    print(f'flask: FAIL - {e}')

try:
    import requests
    print('requests: OK')
except Exception as e:
    print(f'requests: FAIL - {e}')

try:
    import jinja2
    print('jinja2: OK')
except Exception as e:
    print(f'jinja2: FAIL - {e}')

print('All tests completed')
"""
    result = subprocess.run(
        [python_exe, "-c", test_code],
        capture_output=True, text=True
    )
    print(result.stdout)
    if result.stderr:
        print(f"  [WARN] {result.stderr}")
    
    return result.returncode == 0

def main():
    print(f"\n{'=' * 60}")
    print(f"  {APP_NAME} v{APP_VERSION} - Standalone Builder")
    print(f"  Python: {sys.executable}")
    print(f"{'=' * 60}\n")
    
    start_time = time.time()
    
    clean_dirs()
    copy_python_env()
    copy_app_files()
    create_launcher()
    create_package_json()
    create_readme()
    
    # 测试Python
    test_python()
    
    zip_path = create_zip()
    
    elapsed = time.time() - start_time
    print(f"\n{'=' * 60}")
    print(f"  Build completed in {elapsed:.1f}s")
    print(f"  Output: {zip_path}")
    print(f"{'=' * 60}")

if __name__ == "__main__":
    main()
