import sys
import os

print("Python 解释器路径:", sys.executable)
print("Python 版本:", sys.version)
print("当前工作目录:", os.getcwd())

# 检查是否在DL环境中
print("\n检查环境:")
env_path = sys.executable
if "DL" in env_path:
    print("✅ 当前在DL环境中")
else:
    print("❌ 不在DL环境中")

# 检查关键库
print("\n检查关键库:")
try:
    import numpy
    print(f"✅ NumPy: {numpy.__version__}")
except ImportError:
    print("❌ NumPy 未安装")

try:
    import torch
    print(f"✅ PyTorch: {torch.__version__}")
except ImportError:
    print("❌ PyTorch 未安装")

try:
    import pandas
    print(f"✅ pandas: {pandas.__version__}")
except ImportError:
    print("❌ pandas 未安装")
