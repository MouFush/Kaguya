"""
优化数据格式，确保可用于微调
"""

import json
import os

INPUT_FILE = r"D:\mira_easy_dataset\distilled_data.json"
OUTPUT_FILE = r"D:\mira_easy_dataset\final_training_data.json"

def clean_and_format(data):
    """清洗和格式化数据"""
    cleaned = []
    removed = 0
    
    for item in data:
        instruction = item.get('instruction', '').strip()
        output = item.get('output', '').strip()
        
        if not instruction or not output:
            removed += 1
            continue
        
        if instruction == output:
            removed += 1
            continue
        
        if len(instruction) < 10 or len(output) < 10:
            removed += 1
            continue
        
        cleaned.append({
            "instruction": instruction,
            "input": "",
            "output": output
        })
    
    return cleaned, removed

def main():
    print("=" * 50)
    print("  优化数据格式")
    print("=" * 50)
    
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"原始数据: {len(data)} 条")
    
    cleaned, removed = clean_and_format(data)
    print(f"清洗后: {len(cleaned)} 条")
    print(f"移除: {removed} 条")
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)
    
    print(f"\n已保存到: {OUTPUT_FILE}")
    print(f"可用于微调!")

if __name__ == "__main__":
    main()
