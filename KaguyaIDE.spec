# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['c:\\Users\\林智涵\\.conda\\start_server.py'],
    pathex=[],
    binaries=[],
    datas=[('c:\\Users\\林智涵\\.conda\\qwen3_web.py', '.'), ('c:\\Users\\林智涵\\.conda\\ollama_adapter.py', '.'), ('c:\\Users\\林智涵\\.conda\\start_server.py', '.'), ('c:\\Users\\林智涵\\.conda\\kaguya_bootstrap.py', '.'), ('c:\\Users\\林智涵\\.conda\\kaguya_acp.py', '.'), ('c:\\Users\\林智涵\\.conda\\kaguya_agents.py', '.'), ('c:\\Users\\林智涵\\.conda\\kaguya_skills.py', '.'), ('c:\\Users\\林智涵\\.conda\\kaguya_accounts.py', '.'), ('c:\\Users\\林智涵\\.conda\\kaguya_frontend.py', '.'), ('c:\\Users\\林智涵\\.conda\\kaguya_permissions.py', '.'), ('c:\\Users\\林智涵\\.conda\\kaguya_hooks.py', '.'), ('c:\\Users\\林智涵\\.conda\\kaguya_feature_flags.py', '.'), ('c:\\Users\\林智涵\\.conda\\kaguya_memory.py', '.'), ('c:\\Users\\林智涵\\.conda\\kaguya_thinking.py', '.'), ('c:\\Users\\林智涵\\.conda\\kaguya_tool_system.py', '.'), ('c:\\Users\\林智涵\\.conda\\kaguya_file_history.py', '.'), ('c:\\Users\\林智涵\\.conda\\kaguya_file_operations.py', '.'), ('c:\\Users\\林智涵\\.conda\\kaguya_file_analyzer.py', '.'), ('c:\\Users\\林智涵\\.conda\\kaguya_security_framework.py', '.'), ('c:\\Users\\林智涵\\.conda\\kaguya_enhanced_features.py', '.'), ('c:\\Users\\林智涵\\.conda\\kaguya_compaction.py', '.'), ('c:\\Users\\林智涵\\.conda\\kaguya_terminal.py', '.'), ('c:\\Users\\林智涵\\.conda\\kaguya_project_instructions.py', '.'), ('c:\\Users\\林智涵\\.conda\\static', 'static'), ('c:\\Users\\林智涵\\.conda\\kaguya_core', 'kaguya_core'), ('c:\\Users\\林智涵\\.conda\\data', 'data')],
    hiddenimports=['flask', 'numpy', 'sklearn', 'sklearn.feature_extraction', 'sklearn.feature_extraction.text', 'ollama_adapter', 'kaguya_bootstrap', 'kaguya_acp', 'kaguya_agents', 'kaguya_skills', 'kaguya_accounts', 'kaguya_frontend', 'kaguya_permissions', 'kaguya_hooks', 'kaguya_feature_flags', 'kaguya_memory', 'kaguya_thinking', 'kaguya_tool_system', 'kaguya_file_history', 'kaguya_file_operations', 'kaguya_file_analyzer', 'kaguya_security_framework', 'kaguya_enhanced_features', 'kaguya_compaction', 'kaguya_terminal', 'kaguya_project_instructions', 'kaguya_core', 'kaguya_core.config', 'kaguya_core.exceptions', 'kaguya_core.logging', 'kaguya_core.models', 'kaguya_core.utils', 'sqlite3', '_sqlite3', '_ctypes', '_hashlib', '_ssl', '_socket', 'queue', 'threading', 'json', 'uuid', 'secrets', 'dataclasses', 'enum', 'typing', 'abc', 're', 'subprocess', 'tempfile', 'shutil', 'collections', 'functools', 'datetime', 'hashlib', 'hmac', 'base64', 'struct', 'http', 'urllib', 'xml', 'html', 'ast', 'textwrap', 'fnmatch', 'math', 'socket', 'select', 'signal', 'mmap', 'multiprocessing', 'multiprocessing.util', 'certifi', 'urllib3', 'charset_normalizer', 'jinja2', 'markupsafe', 'werkzeug', 'itsdangerous', 'click', 'sklearn.utils', 'sklearn.metrics', 'sklearn.metrics.cluster', 'sklearn.metrics.pairwise', 'sklearn.feature_extraction.text'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tensorflow', 'torch', 'torchvision', 'torchaudio', 'keras', 'transformers', 'diffusers', 'accelerate', 'deepspeed', 'PIL', 'matplotlib', 'scipy', 'pandas', 'cv2', 'tkinter', 'notebook', 'IPython', 'jupyter', 'librosa', 'soundfile', 'pyarrow', 'datasets', 'h5py', 'onnxruntime', 'numba', 'llvmlite', 'sqlalchemy', 'nltk', 'pygame', 'av', 'bitsandbytes', 'opentelemetry', 'grpc', 'win32com', 'winreg', 'unittest', 'rich', 'pygments', 'anyio', 'sniffio', 'pydantic', 'orjson', 'uvicorn', 'dns', 'websockets', 'fsspec', 'zoneinfo', 'pytz', 'safetensors', 'zstandard', 'aiohttp', 'sklearn.ensemble', 'sklearn.svm', 'sklearn.tree', 'sklearn.neighbors', 'sklearn._loss', 'sklearn.cluster', 'sklearn.linear_model', 'sklearn.decomposition', 'sklearn.manifold', 'sklearn.preprocessing', 'sklearn.model_selection', 'sklearn.pipeline', 'sklearn.compose', 'sklearn.impute', 'sklearn.gaussian_process', 'sklearn.cross_decomposition', 'sklearn.discriminant_analysis', 'sklearn.isotonic', 'sklearn.kernel_ridge', 'sklearn.mixture', 'sklearn.multiclass', 'sklearn.multioutput', 'sklearn.naive_bayes', 'sklearn.semi_supervised', 'sklearn.feature_selection', 'sklearn.covariance', 'numpy.fft', 'numpy.linalg', 'numpy.random', 'numpy.ma', 'numpy.polynomial', 'numpy.testing'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

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
