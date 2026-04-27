# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['c:\\Users\\林智涵\\.conda\\kaguya-desktop\\src\\kaguya_launcher.py'],
    pathex=[],
    binaries=[],
    datas=[('c:\\Users\\林智涵\\.conda\\qwen3_web.py', '.'), ('c:\\Users\\林智涵\\.conda\\ollama_adapter.py', '.'), ('c:\\Users\\林智涵\\.conda\\kaguya_file_operations.py', '.'), ('c:\\Users\\林智涵\\.conda\\kaguya_permissions.py', '.'), ('c:\\Users\\林智涵\\.conda\\kaguya_tool_executor.py', '.'), ('c:\\Users\\林智涵\\.conda\\kaguya_bootstrap.py', '.'), ('c:\\Users\\林智涵\\.conda\\kaguya_acp.py', '.'), ('c:\\Users\\林智涵\\.conda\\kaguya_agents.py', '.'), ('c:\\Users\\林智涵\\.conda\\kaguya_frontend.py', '.'), ('c:\\Users\\林智涵\\.conda\\kaguya_file_analyzer.py', '.'), ('c:\\Users\\林智涵\\.conda\\kaguya_file_history.py', '.')],
    hiddenimports=['flask', 'jinja2', 'werkzeug', 'markupsafe', 'sklearn', 'sklearn.feature_extraction', 'sklearn.feature_extraction.text', 'sklearn.metrics', 'sklearn.metrics.pairwise', 'sklearn.utils', 'sklearn.utils._typedefs', 'sklearn.utils._heap', 'sklearn.utils._sorting', 'sklearn.utils._vector_sentinel', 'sklearn.neighbors', 'sklearn.neighbors._partition_nodes', 'numpy', 'numpy.core', 'numpy.core._methods', 'numpy.lib', 'numpy.lib.format', 'PIL', 'PIL.Image', 'scipy', 'scipy.sparse', 'scipy.sparse.csgraph'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['torch', 'torchvision', 'torchaudio', 'transformers', 'tensorflow', 'keras', 'pandas', 'matplotlib', 'sympy', 'notebook', 'ipykernel', 'IPython', 'jupyterlab', 'gradio', 'streamlit', 'fastapi', 'uvicorn', 'pyarrow', 'h5py', 'numba', 'llvmlite', 'pygame', 'librosa', 'soundfile', 'onnxruntime', 'bitsandbytes', 'nltk', 'datasets', 'accelerate', 'diffusers', 'safetensors', 'tokenizers', 'cv2', 'skimage', 'sqlalchemy', 'opentelemetry', 'av', 'tqdm', 'rich', 'hydra', 'pydantic', 'tiktoken', 'openai', 'anthropic', 'google', 'boto3', 'botocore', 'websockets', 'anyio', 'httpcore', 'httpx', 'orjson', 'dns', 'win32com', 'pythoncom', 'pywintypes', 'tkinter', '_tkinter', 'cryptography', 'nacl', 'inflect'],
    noarchive=False,
    optimize=2,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [('O', None, 'OPTION'), ('O', None, 'OPTION')],
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
    icon=['c:\\Users\\林智涵\\.conda\\kaguya-desktop\\assets\\kaguya.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='KaguyaIDE',
)
