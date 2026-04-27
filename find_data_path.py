import os
import json

def find_data_path():
    print("=" * 60)
    print("查找 LLaMA-Factory 数据目录")
    print("=" * 60)
    
    # 可能的 WSL 数据目录
    possible_paths = [
        "/mnt/c/Users/林智涵/LLaMA-Factory/data",
        "/home/fusheng/LLaMA-Factory/data",
        "/home/fusheng/llama-factory/data",
        "/opt/llama-factory/data",
        "/usr/local/llama-factory/data",
        "./data",
    ]
    
    print("\n检查可能的数据目录:")
    for path in possible_paths:
        if os.path.exists(path):
            print(f"  ✓ {path}")
            # 检查是否有 dataset_info.json
            info_path = os.path.join(path, "dataset_info.json")
            if os.path.exists(info_path):
                print(f"    - 包含 dataset_info.json")
                try:
                    with open(info_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    print(f"    - 数据集数量: {len(data)}")
                    if 'mira_text' in data:
                        print(f"    - ✓ 包含 mira_text")
                    if 'mira_multimodal' in data:
                        print(f"    - ✓ 包含 mira_multimodal")
                except:
                    pass
        else:
            print(f"  ✗ {path}")
    
    print("\n" + "=" * 60)
    print("建议:")
    print("=" * 60)
    print("\n在 WebUI 的 '数据路径' 字段中输入完整路径:")
    print("  /mnt/c/Users/林智涵/LLaMA-Factory/data")
    print("\n或者从该目录启动 LLaMA-Factory:")
    print("  cd /mnt/c/Users/林智涵/LLaMA-Factory")
    print("  llamafactory-cli webui")

if __name__ == '__main__':
    find_data_path()
