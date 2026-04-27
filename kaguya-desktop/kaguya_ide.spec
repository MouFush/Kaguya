# -*- mode: python ; coding: utf-8 -*-
"""
辉夜IDE PyInstaller 打包配置
使用方法: pyinstaller kaguya_ide.spec
"""

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

block_cipher = None

SRC_DIR = os.path.join(os.path.dirname(os.path.abspath(SPECPATH)), '..')
SRC_DIR = os.path.abspath(SRC_DIR)

APP_NAME = 'KaguyaIDE'
APP_VERSION = '3.1.1'
APP_AUTHOR = 'Kaguya'

hiddenimports = [
    'flask',
    'jinja2',
    'werkzeug',
    'markupsafe',
    'itsdangerous',
    'click',
    'ollama_adapter',
    'kaguya_file_operations',
    'kaguya_permissions',
    'kaguya_tool_executor',
    'kaguya_file_analyzer',
    'kaguya_file_history',
    'kaguya_frontend',
    'kaguya_bootstrap',
    'kaguya_acp',
    'kaguya_agents',
    'kaguya_accounts',
    'kaguya_terminal',
    'kaguya_tool_system',
    'kaguya_security_framework',
    'kaguya_hooks',
    'kaguya_thinking',
    'kaguya_memory',
    'kaguya_skills',
    'kaguya_feature_flags',
    'kaguya_enhanced_features',
    'kaguya_compaction',
    'kaguya_project_instructions',
    'rbac_system',
    'encryption_system',
    'rate_limiter',
    'secure_sandbox',
    'webview',
    'webview.platforms',
    'webview.platforms.winforms',
    'webview.platforms.cocoa',
    'webview.platforms.gtk',
    'urllib3',
    'certifi',
    'charset_normalizer',
    'idna',
    'sklearn',
    'sklearn.feature_extraction',
    'sklearn.feature_extraction.text',
    'sklearn.metrics',
    'sklearn.metrics.pairwise',
    'sklearn.utils',
    'sklearn.utils._typedefs',
    'sklearn.utils._heap',
    'sklearn.utils._sorting',
    'sklearn.utils._vector_sentinel',
    'sklearn.neighbors',
    'sklearn.neighbors._partition_nodes',
    'PIL',
    'PIL.Image',
    'numpy',
    'numpy.core',
    'numpy.core._methods',
    'numpy.lib',
    'numpy.lib.format',
    'sqlite3',
    'hashlib',
    'hmac',
    'fnmatch',
    'threading',
    'socket',
    'tempfile',
    'subprocess',
    'collections',
    'dataclasses',
    'pathlib',
    'abc',
    'cryptography',
    'cryptography.fernet',
    'cryptography.hazmat.primitives.kdf.pbkdf2',
]

if sys.platform == 'win32':
    hiddenimports.extend([
        'webview.platforms.winforms',
        'webview.platforms.edgechromium',
        'clr',
        'System',
        'System.Windows.Forms',
    ])
elif sys.platform == 'darwin':
    hiddenimports.extend([
        'webview.platforms.cocoa',
        'objc',
        'Foundation',
        'AppKit',
        'WebKit',
    ])
else:
    hiddenimports.extend([
        'webview.platforms.gtk',
        'gi',
        'gi.repository',
        'gi.repository.Gtk',
        'gi.repository.WebKit2',
    ])

datas = []

for pkg_name in ['flask', 'jinja2', 'werkzeug', 'markupsafe', 'sklearn', 'numpy']:
    try:
        pkg_datas = collect_data_files(pkg_name)
        datas.extend(pkg_datas)
    except Exception:
        pass

for pkg_name in ['flask', 'jinja2', 'werkzeug', 'markupsafe', 'sklearn', 'numpy', 'webview', 'PIL']:
    try:
        pkg_datas = copy_metadata(pkg_name)
        datas.extend(pkg_datas)
    except Exception:
        pass

core_files = [
    'qwen3_web.py',
    'ollama_adapter.py',
    'kaguya_file_operations.py',
    'kaguya_permissions.py',
    'kaguya_tool_executor.py',
    'kaguya_file_analyzer.py',
    'kaguya_file_history.py',
    'kaguya_frontend.py',
    'kaguya_bootstrap.py',
    'kaguya_acp.py',
    'kaguya_agents.py',
    'kaguya_feature_flags.py',
    'kaguya_enhanced_features.py',
    'kaguya_accounts.py',
    'kaguya_terminal.py',
    'kaguya_tool_system.py',
    'kaguya_security_framework.py',
    'kaguya_hooks.py',
    'kaguya_thinking.py',
    'kaguya_memory.py',
    'kaguya_skills.py',
    'kaguya_compaction.py',
    'kaguya_project_instructions.py',
    'rbac_system.py',
    'encryption_system.py',
    'rate_limiter.py',
    'secure_sandbox.py',
]

for f in core_files:
    full_path = os.path.join(SRC_DIR, f)
    if os.path.exists(full_path):
        datas.append((full_path, '.'))

icon_path = None
for icon_name in ['kaguya.ico', 'icon.ico']:
    candidate = os.path.join(SRC_DIR, 'kaguya-desktop', 'assets', icon_name)
    if os.path.exists(candidate):
        icon_path = candidate
        break
    candidate = os.path.join(SRC_DIR, icon_name)
    if os.path.exists(candidate):
        icon_path = candidate
        break

a = Analysis(
    [os.path.join(SRC_DIR, 'kaguya-desktop', 'src', 'kaguya_desktop.py')],
    pathex=[SRC_DIR, os.path.join(SRC_DIR, 'kaguya-desktop', 'src')],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'scipy', 'pandas', 'tensorflow', 'torch',
        'torchaudio', 'torchvision', 'keras', 'cv2', 'PyQt5',
        'PyQt6', 'PySide2', 'PySide6', 'tkinter', 'unittest',
        'xmlrunner', 'pytest', 'sphinx', 'docutils',
    ],
    noarchive=False,
    optimize=2,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    icon=icon_path,
    version_file=os.path.join(SRC_DIR, 'kaguya-desktop', 'assets', 'version_info.txt') if os.path.exists(os.path.join(SRC_DIR, 'kaguya-desktop', 'assets', 'version_info.txt')) else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    name=APP_NAME,
)

if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name=APP_NAME + '.app',
        icon=icon_path if icon_path and icon_path.endswith('.icns') else None,
        bundle_identifier=f'com.kaguya.ide',
        info_plist={
            'CFBundleName': APP_NAME,
            'CFBundleDisplayName': APP_NAME,
            'CFBundleVersion': APP_VERSION,
            'CFBundleShortVersionString': APP_VERSION,
            'NSHighResolutionCapable': True,
            'LSMinimumSystemVersion': '10.13.0',
            'NSRequiresAquaSystemAppearance': False,
            'CFBundleDocumentTypes': [],
        },
    )
