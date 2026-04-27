import json
import os

def update_dataset_info():
    print("=" * 60)
    print("更新 LLaMA-Factory dataset_info.json")
    print("=" * 60)
    
    dataset_info_path = r"C:\Users\林智涵\LLaMA-Factory\data\dataset_info.json"
    
    with open(dataset_info_path, 'r', encoding='utf-8') as f:
        dataset_info = json.load(f)
    
    dataset_info["mira_multimodal"] = {
        "file_name": "mira_multimodal.json",
        "formatting": "sharegpt",
        "columns": {
            "messages": "messages",
            "images": "images"
        }
    }
    
    with open(dataset_info_path, 'w', encoding='utf-8') as f:
        json.dump(dataset_info, f, ensure_ascii=False, indent=2)
    
    print("\n已添加 mira_multimodal 数据集配置")
    
    with open(dataset_info_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if "mira_multimodal" in content:
        print("\n验证成功: dataset_info.json 中已包含 mira_multimodal")
    
    print("\n" + "=" * 60)
    print("配置完成!")
    print("=" * 60)
    print("\n请在 LLaMA-Factory WebUI 中:")
    print("1. 选择支持视觉的模型 (如 Qwen2-VL)")
    print("2. 在数据集列表中找到 'mira_multimodal'")

if __name__ == '__main__':
    update_dataset_info()
