import os
import sys
import subprocess
import pathlib
import time
import threading
import requests

script_dir = pathlib.Path(__file__).parent.resolve()
source_dir = script_dir.parent

os.chdir(source_dir)

port = 58000

env = os.environ.copy()
env['KAGUYA_DESKTOP_MODE'] = '1'
env['KAGUYA_ELECTRON'] = '1'
env['KAGUYA_PERMISSION_MODE'] = 'bypassPermissions'
env['KAGUYA_PORT'] = str(port)

def start_flask():
    subprocess.run([sys.executable, 'qwen3_web.py'], env=env, cwd=str(source_dir))

flask_thread = threading.Thread(target=start_flask, daemon=True)
flask_thread.start()

print(f'[Launcher] Waiting for Flask server to start on port {port}...')
for i in range(60):
    try:
        r = requests.get(f'http://127.0.0.1:{port}/', timeout=1)
        if r.status_code == 200:
            print(f'[Launcher] Flask server is ready!')
            break
    except:
        pass
    time.sleep(1)
else:
    print('[Launcher] Flask server failed to start')
    sys.exit(1)

electron_env = os.environ.copy()
electron_env['KAGUYA_SOURCE_DIR'] = str(source_dir)
electron_env['KAGUYA_DESKTOP_MODE'] = '1'
electron_env['KAGUYA_ELECTRON'] = '1'
electron_env['KAGUYA_PERMISSION_MODE'] = 'bypassPermissions'
electron_env['KAGUYA_PORT'] = str(port)

os.chdir(script_dir)
subprocess.run('npm start', shell=True, env=electron_env)
