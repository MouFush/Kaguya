"""
本地数据蒸馏脚本
直接处理数据，无需依赖Easy Dataset界面
"""

import json
import os
from pathlib import Path

INPUT_DIR = r"D:\mira_easy_dataset"
OUTPUT_FILE = r"D:\mira_easy_dataset\distilled_data.json"
PROCESSED_FILE = r"D:\datasets-4J1opHXSFqck-alpaca-2026-03-25.json"

def load_all_data():
    """加载所有待处理数据"""
    all_data = []
    
    for i in range(1, 6):
        batch_file = os.path.join(INPUT_DIR, f"batch_{i}.json")
        if os.path.exists(batch_file):
            with open(batch_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                all_data.extend(data)
                print(f"加载 batch_{i}.json: {len(data)} 条")
    
    return all_data

def distill_data(data):
    """蒸馏数据 - 清洗和优化"""
    distilled = []
    skipped_empty = 0
    skipped_short = 0
    skipped_duplicate = 0
    
    for item in data:
        instruction = item.get('instruction', '').strip()
        output = item.get('output', '').strip()
        
        if not instruction or not output:
            skipped_empty += 1
            continue
        
        if len(instruction) < 5 or len(output) < 5:
            skipped_short += 1
            continue
        
        if instruction == output:
            skipped_duplicate += 1
            continue
        
        instruction = ' '.join(instruction.split())
        output = ' '.join(output.split())
        
        if len(instruction) > 10 and len(output) > 10:
            distilled.append({
                "instruction": instruction,
                "input": "",
                "output": output
            })
    
    print(f"\n过滤统计:")
    print(f"  空数据: {skipped_empty} 条")
    print(f"  过短数据: {skipped_short} 条")
    print(f"  重复数据: {skipped_duplicate} 条")
    
    return distilled

def main():
    print("=" * 60)
    print("  本地数据蒸馏处理")
    print("=" * 60)
    
    print("\n[步骤1] 加载已处理的高质量数据...")
    processed_data = []
    if os.path.exists(PROCESSED_FILE):
        with open(PROCESSED_FILE, 'r', encoding='utf-8') as f:
            processed_data = json.load(f)
        print(f"已处理数据: {len(processed_data)} 条")
    
    print("\n[步骤2] 加载待处理数据...")
    raw_data = load_all_data()
    print(f"待处理数据: {len(raw_data)} 条")
    
    print("\n[步骤3] 蒸馏处理...")
    distilled_data = distill_data(raw_data)
    print(f"蒸馏后数据: {len(distilled_data)} 条")
    
    print("\n[步骤4] 合并数据...")
    final_data = processed_data + distilled_data
    print(f"最终数据: {len(final_data)} 条")
    
    print("\n[步骤5] 保存数据...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
    print(f"已保存到: {OUTPUT_FILE}")
    
    print("\n" + "=" * 60)
    print("  处理完成!")
    print("=" * 60)
    print(f"\n📊 最终统计:")
    print(f"  原有高质量数据: {len(processed_data)} 条")
    print(f"  新蒸馏数据: {len(distilled_data)} 条")
    print(f"  总计: {len(final_data)} 条")
    print(f"\n📁 输出文件: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
