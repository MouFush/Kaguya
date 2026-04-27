import json
import shutil
import os

def setup_text_dataset():
    print("=" * 60)
    print("LLaMA-Factory 纯文本数据集配置工具")
    print("=" * 60)

    src_file = r"D:\mira_easy_dataset\final_training_data.json"
    dest_file = r"C:\Users\林智涵\LLaMA-Factory\data\mira_text.json"

    print("\n步骤1: 复制数据文件...")
    shutil.copy2(src_file, dest_file)
    print(f"  已复制: {dest_file}")

    print("\n步骤2: 更新 dataset_info.json...")
    dataset_info_path = r"C:\Users\林智涵\LLaMA-Factory\data\dataset_info.json"

    with open(dataset_info_path, 'r', encoding='utf-8') as f:
        dataset_info = json.load(f)

    dataset_info["mira_text"] = {
        "file_name": "mira_text.json",
        "columns": {
            "prompt": "instruction",
            "response": "output"
        }
    }

    with open(dataset_info_path, 'w', encoding='utf-8') as f:
        json.dump(dataset_info, f, ensure_ascii=False, indent=2)

    print(f"  已添加 mira_text 数据集配置")

    with open(dest_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print("\n" + "=" * 60)
    print("配置完成!")
    print("=" * 60)
    print(f"\n数据集信息:")
    print(f"  数据条数: {len(data)}")
    print(f"  数据格式: Alpaca (纯文本)")
    print(f"\n使用方法:")
    print("  1. 打开 LLaMA-Factory WebUI")
    print("  2. 选择纯文本模型 (如 Qwen2.5, Llama3 等)")
    print("  3. 在数据集列表中选择 'mira_text'")
    print("  4. 开始微调")

if __name__ == '__main__':
    setup_text_dataset()
