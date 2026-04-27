import subprocess
import sys
import os
import shutil

print("尝试多种方法删除TensorFlow...")

tf_path = r"D:\Anoconda\envs\DL\lib\site-packages\tensorflow"
tf_info = r"D:\Anoconda\envs\DL\lib\site-packages\tensorflow-2.20.0.dist-info"

print("\n方法1: 使用pip卸载...")
result = subprocess.run([sys.executable, "-m", "pip", "uninstall", "tensorflow", "-y"], capture_output=True, text=True)
print(result.stdout)
print(result.stderr)

print("\n方法2: 检查文件夹是否存在...")
if os.path.exists(tf_path):
    print(f"tensorflow文件夹仍存在: {tf_path}")
    print("尝试删除...")
    try:
        for root, dirs, files in os.walk(tf_path, topdown=False):
            for name in files:
                filepath = os.path.join(root, name)
                try:
                    os.remove(filepath)
                except Exception as e:
                    pass
            for name in dirs:
                dirpath = os.path.join(root, name)
                try:
                    os.rmdir(dirpath)
                except Exception as e:
                    pass
        os.rmdir(tf_path)
        print("tensorflow文件夹已删除!")
    except Exception as e:
        print(f"删除失败: {e}")
else:
    print("tensorflow文件夹不存在")

if os.path.exists(tf_info):
    print(f"tensorflow dist-info仍存在: {tf_info}")
    try:
        shutil.rmtree(tf_info)
        print("tensorflow dist-info已删除!")
    except Exception as e:
        print(f"删除失败: {e}")

print("\n最终检查:")
try:
    import tensorflow
    print(f"tensorflow仍然存在: {tensorflow.__file__}")
except ImportError:
    print("✓ tensorflow已成功删除!")
