import json
import os
import shutil

def create_llama_factory_dataset():
    """创建LLaMA-Factory兼容的多模态数据集"""
    
    input_folder = r'D:\mira_multimodal_dataset'
    output_folder = r'D:\mira_llama_factory_dataset'
    os.makedirs(output_folder, exist_ok=True)
    
    images_output = os.path.join(output_folder, 'images')
    os.makedirs(images_output, exist_ok=True)
    
    llava_path = os.path.join(input_folder, 'llava_format.json')
    with open(llava_path, 'r', encoding='utf-8') as f:
        llava_data = json.load(f)
    
    llama_factory_data = []
    
    print(f"处理 {len(llava_data)} 条数据...")
    
    for item in llava_data:
        image_rel_path = item['image']
        conversations = item['conversations']
        
        src_image = os.path.join(input_folder, image_rel_path)
        if not os.path.exists(src_image):
            continue
        
        image_name = os.path.basename(image_rel_path)
        dest_image = os.path.join(images_output, image_name)
        
        if not os.path.exists(dest_image):
            shutil.copy2(src_image, dest_image)
        
        user_content = ""
        assistant_content = ""
        
        for conv in conversations:
            if conv['from'] == 'human':
                user_content = conv['value']
            elif conv['from'] == 'gpt':
                assistant_content = conv['value']
        
        if user_content and assistant_content:
            llama_factory_item = {
                "messages": [
                    {
                        "role": "user",
                        "content": user_content
                    },
                    {
                        "role": "assistant",
                        "content": assistant_content
                    }
                ],
                "images": [f"images/{image_name}"]
            }
            llama_factory_data.append(llama_factory_item)
    
    output_path = os.path.join(output_folder, 'llama_factory_multimodal.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(llama_factory_data, f, ensure_ascii=False, indent=2)
    
    dataset_info = {
        "file_name": "llama_factory_multimodal.json",
        "formatting": "sharegpt",
        "multimodal": True,
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
    
    info_path = os.path.join(output_folder, 'dataset_info.json')
    with open(info_path, 'w', encoding='utf-8') as f:
        json.dump(dataset_info, f, ensure_ascii=False, indent=2)
    
    print(f"\n输出文件:")
    print(f"  数据集: {output_path}")
    print(f"  配置文件: {info_path}")
    print(f"  图片文件夹: {images_output}")
    print(f"  数据条数: {len(llama_factory_data)}")
    
    return output_path, len(llama_factory_data)

def create_llama_factory_config():
    """创建LLaMA-Factory的dataset_info.json配置"""
    
    config = {
        "mira_multimodal": {
            "file_name": "llama_factory_multimodal.json",
            "formatting": "sharegpt",
            "multimodal": True,
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
    }
    
    output_folder = r'D:\mira_llama_factory_dataset'
    config_path = os.path.join(output_folder, 'dataset_info_entry.json')
    
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    print(f"\nLLaMA-Factory配置条目已保存到: {config_path}")
    print("\n使用方法:")
    print("1. 将 dataset_info_entry.json 中的内容添加到 LLaMA-Factory 的 data/dataset_info.json 文件中")
    print("2. 将 llama_factory_multimodal.json 和 images 文件夹复制到 LLaMA-Factory 的 data 目录下")
    print("3. 在 LLaMA-Factory WebUI 中选择 'mira_multimodal' 数据集即可使用")
    
    return config_path

if __name__ == '__main__':
    print("=" * 60)
    print("LLaMA-Factory 多模态数据集生成器")
    print("=" * 60)
    
    create_llama_factory_dataset()
    create_llama_factory_config()
    
    print("\n" + "=" * 60)
    print("处理完成!")
    print("=" * 60)
