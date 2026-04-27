import os
import sys
import subprocess
import pathlib

script_dir = pathlib.Path(__file__).parent.resolve()
source_dir = script_dir.parent

env = os.environ.copy()
env['KAGUYA_SOURCE_DIR'] = str(source_dir)
env['KAGUYA_DESKTOP_MODE'] = '1'
env['KAGUYA_ELECTRON'] = '1'
env['KAGUYA_PERMISSION_MODE'] = 'bypassPermissions'

os.chdir(script_dir)

if sys.platform == 'win32':
    subprocess.run('npm start', shell=True, env=env)
else:
    subprocess.run(['npm', 'start'], env=env)
