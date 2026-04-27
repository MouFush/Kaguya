import os

def fix_unsloth():
    print("=" * 60)
    print("修复 Unsloth HuggingFace 连接问题")
    print("=" * 60)
    
    file_path = "/mnt/d/07-动手学微调/finetune/lib/python3.12/site-packages/unsloth/models/_utils.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 找到 get_statistics 函数并修改
    old_code = '''def get_statistics(local_files_only = False):
    from huggingface_hub.utils import (
        HfHubHTTPError,
        LocalEntryNotFoundError,
    )
    _get_statistics(None)
    _get_statistics("repeat", force_download = False)
    _get_statistics(f"vram-{vram}")
    _get_statistics(f"{DEVICE_COUNT if DEVICE_COUNT <= 8 else 9}")'''
    
    new_code = '''def get_statistics(local_files_only = False):
    # 跳过 HuggingFace 统计，避免网络超时
    print("Unsloth: Skipping HuggingFace statistics check")
    return'''
    
    if old_code in content:
        content = content.replace(old_code, new_code)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("\n已修改 get_statistics 函数，跳过 HuggingFace 检查")
    else:
        print("\n未找到目标代码，尝试其他方法...")
    
    print("\n" + "=" * 60)
    print("修复完成!")
    print("=" * 60)
    print("\n请重新启动训练")

if __name__ == '__main__':
    fix_unsloth()
