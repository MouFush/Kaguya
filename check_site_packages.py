#!/usr/bin/env python3
"""检查site-packages路径"""
import site
import sys

print("="*60)
print("Python库安装位置")
print("="*60)

print("\n📁 site-packages 路径:")
for path in site.getsitepackages():
    print(f"   {path}")

print("\n📁 用户site-packages:")
print(f"   {site.getusersitepackages()}")

print("\n📁 sys.path:")
for i, path in enumerate(sys.path):
    print(f"   [{i}] {path}")

print("\n" + "="*60)
