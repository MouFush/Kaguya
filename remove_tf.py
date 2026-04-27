import shutil
import os

tf_path = r"D:\Anoconda\envs\DL\lib\site-packages\tensorflow"
tf_info = r"D:\Anoconda\envs\DL\lib\site-packages\tensorflow-2.20.0.dist-info"

if os.path.exists(tf_path):
    print(f"正在删除 {tf_path}...")
    try:
        shutil.rmtree(tf_path)
        print("tensorflow文件夹已删除")
    except Exception as e:
        print(f"删除失败: {e}")
else:
    print("tensorflow文件夹不存在")

if os.path.exists(tf_info):
    print(f"正在删除 {tf_info}...")
    try:
        shutil.rmtree(tf_info)
        print("tensorflow dist-info已删除")
    except Exception as e:
        print(f"删除失败: {e}")
else:
    print("tensorflow dist-info不存在")

print("\n检查tensorflow是否还存在:")
try:
    import tensorflow
    print(f"tensorflow仍然存在: {tensorflow.__file__}")
except ImportError:
    print("tensorflow已成功删除!")
