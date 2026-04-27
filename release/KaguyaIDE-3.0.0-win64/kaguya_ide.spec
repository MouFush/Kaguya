#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辉夜IDE PyInstaller 打包配置
支持 Windows / macOS / Linux 三平台打包
"""

import os
import sys

KAGUYA_VERSION = "3.0.0"

block_cipher = None

kaguya_datas = [
    ('static', 'static'),
    ('data', 'data'),
    ('kaguya_core', 'kaguya_core'),
]

kaguya_hiddenimports = [
    'flask',
    'ollama_adapter',
    'kaguya_bootstrap',
    'kaguya_acp',
    'kaguya_agents',
    'kaguya_skills',
    'kaguya_accounts',
    'kaguya_frontend',
    'kaguya_permissions',
    'kaguya_hooks',
    'kaguya_feature_flags',
    'kaguya_memory',
    'kaguya_thinking',
    'kaguya_tool_system',
    'kaguya_file_history',
    'kaguya_compaction',
    'kaguya_terminal',
    'kaguya_core',
    'kaguya_core.config',
    'kaguya_core.exceptions',
    'kaguya_core.logging',
    'kaguya_core.models',
    'kaguya_core.utils',
    'sqlite3',
    'json',
    'urllib',
    'hashlib',
    'secrets',
    'threading',
    'queue',
    'uuid',
    'datetime',
    'collections',
    'functools',
    'dataclasses',
    'enum',
    'typing',
    'abc',
    're',
    'subprocess',
    'tempfile',
    'shutil',
    'base64',
    'socket',
    'struct',
    'sklearn',
    'sklearn.feature_extraction',
    'sklearn.feature_extraction.text',
    'numpy',
]

a = Analysis(
    ['start_server.py'],
    pathex=[],
    binaries=[],
    datas=kaguya_datas,
    hiddenimports=kaguya_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tensorflow', 'torch', 'keras', 'PIL', 'matplotlib',
        'scipy', 'pandas', 'cv2', 'sympy', 'notebook',
        'IPython', 'jupyter', 'tornado', 'django',
        'tkinter', 'unittest', 'xmlrpc', 'pydoc',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='KaguyaIDE',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='KaguyaIDE',
)
