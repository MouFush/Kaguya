import json
import os
import shutil

def setup_llama_factory():
    print("=" * 60)
    print("LLaMA-Factory 多模态数据集配置工具")
    print("=" * 60)
    
    src_data = r"D:\mira_llama_factory_dataset\llama_factory_multimodal.json"
    src_images = r"D:\mira_llama_factory_dataset\images"
    
    llama_factory_data = r"C:\Users\林智涵\LLaMA-Factory\data"
    dest_data = os.path.join(llama_factory_data, "mira_multimodal.json")
    dest_images = os.path.join(llama_factory_data, "mira_images")
    
    print("\n步骤1: 复制数据文件...")
    shutil.copy2(src_data, dest_data)
    print(f"  已复制: {dest_data}")
    
    print("\n步骤2: 复制图片文件夹...")
    if os.path.exists(dest_images):
        shutil.rmtree(dest_images)
    shutil.copytree(src_images, dest_images)
    print(f"  已复制: {dest_images}")
    
    print("\n步骤3: 更新数据集配置...")
    dataset_info_path = os.path.join(llama_factory_data, "dataset_info.json")
    
    with open(dataset_info_path, 'r', encoding='utf-8') as f:
        dataset_info = json.load(f)
    
    dataset_info["mira_multimodal"] = {
        "file_name": "mira_multimodal.json",
        "formatting": "sharegpt",
        "columns": {
            "messages": "messages",
            "images": "images"
        },
        "tags": {
            "role_tag": "role",
            "content_tag": "content",
            "user_tag": "user",
            "assistant_tag": "assistant"
        }
    }
    
    with open(dataset_info_path, 'w', encoding='utf-8') as f:
        json.dump(dataset_info, f, ensure_ascii=False, indent=2)
    
    print(f"  已更新: {dataset_info_path}")
    
    print("\n步骤4: 更新数据集中的图片路径...")
    with open(dest_data, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    for item in data:
        if "images" in item:
            item["images"] = [img.replace("images/", "mira_images/") for img in item["images"]]
    
    with open(dest_data, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"  已更新图片路径")
    
    image_count = len(os.listdir(dest_images))
    
    print("\n" + "=" * 60)
    print("配置完成!")
    print("=" * 60)
    print(f"\n数据集信息:")
    print(f"  数据条数: {len(data)}")
    print(f"  图片数量: {image_count}")
    print(f"  数据格式: ShareGPT (多模态)")
    print(f"\n使用方法:")
    print("  1. 打开 LLaMA-Factory WebUI")
    print("  2. 在数据集选择中选择 'mira_multimodal'")
    print("  3. 选择支持视觉的模型 (如 Qwen2-VL, LLaVA, InternVL 等)")
    print("  4. 开始微调")

if __name__ == '__main__':
    setup_llama_factory()
