#!/usr/bin/env python3
import os, zipfile
DIST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist")
def create_zip(source_dir, zip_name):
    zip_path = os.path.join(DIST_DIR, zip_name)
    print(f"[打包] {zip_name}...")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            dirs[:] = [d for d in dirs if d != '__pycache__']
            for file in files:
                if file.endswith('.pyc'): continue
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, os.path.dirname(source_dir))
                zipf.write(file_path, arcname)
    print(f"[完成] {zip_name}: {os.path.getsize(zip_path)/(1024*1024):.2f} MB")
for d, z in [("KaguyaIDE-3.1.0-full", "KaguyaIDE-3.1.0-full-win64.zip"), ("KaguyaIDE-3.1.0-update", "KaguyaIDE-3.1.0-update.zip")]:
    p = os.path.join(DIST_DIR, d)
    if os.path.exists(p): create_zip(p, z)
    else: print(f"[跳过] {p} 不存在")
print("打包完成！")
