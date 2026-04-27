#!/usr/bin/env python3
"""检查DL环境配置"""
import sys
print(f"Python版本: {sys.version}")
print(f"Python路径: {sys.executable}")

try:
    import torch
    print(f"\n✅ PyTorch已安装")
    print(f"   版本: {torch.__version__}")
    print(f"   CUDA可用: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"   CUDA版本: {torch.version.cuda}")
        print(f"   GPU数量: {torch.cuda.device_count()}")
        print(f"   GPU名称: {torch.cuda.get_device_name(0)}")
except ImportError:
    print("\n❌ PyTorch未安装")

try:
    import tensorflow as tf
    print(f"\n✅ TensorFlow已安装")
    print(f"   版本: {tf.__version__}")
    print(f"   GPU可用: {len(tf.config.list_physical_devices('GPU')) > 0}")
except ImportError:
    print("\n❌ TensorFlow未安装")

try:
    import transformers
    print(f"\n✅ Transformers已安装")
    print(f"   版本: {transformers.__version__}")
except ImportError:
    print("\n❌ Transformers未安装")

try:
    import numpy as np
    print(f"\n✅ NumPy已安装")
    print(f"   版本: {np.__version__}")
except ImportError:
    print("\n❌ NumPy未安装")

print("\n" + "="*50)
print("DL环境检查完成!")
