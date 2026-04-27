"""
将未处理的数据提取出来，准备继续蒸馏处理
"""

import json
from pathlib import Path

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(data, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_content_hash(item):
    """生成内容的哈希值用于比较"""
    if 'conversations' in item:
        content = ""
        for conv in item['conversations']:
            content += conv.get('content', '')
        return content
    else:
        return item.get('instruction', '') + item.get('output', '')

def main():
    # 加载数据
    all_data = load_json(r'D:\mira_easy_dataset\easy_dataset_import.json')
    processed_data = load_json(r'D:\datasets-4J1opHXSFqck-alpaca-2026-03-25.json')
    
    print(f"原始数据: {len(all_data)} 条")
    print(f"已处理数据: {len(processed_data)} 条")
    
    # 获取已处理数据的内容签名
    processed_signatures = set()
    for item in processed_data:
        sig = get_content_hash(item)
        processed_signatures.add(sig[:100])  # 只取前100字符作为签名
    
    # 找出未处理的数据
    unprocessed_data = []
    for item in all_data:
        sig = get_content_hash(item)[:100]
        if sig not in processed_signatures:
            unprocessed_data.append(item)
    
    print(f"未处理数据: {len(unprocessed_data)} 条")
    
    # 保存未处理的数据
    output_path = r'D:\mira_easy_dataset\unprocessed_data.json'
    save_json(unprocessed_data, output_path)
    print(f"\n已保存未处理数据到: {output_path}")
    
    # 转换为Alpaca格式（用于Easy Dataset导入）
    alpaca_data = []
    for item in unprocessed_data:
        if 'conversations' in item:
            convs = item['conversations']
            if len(convs) >= 2:
                instruction = ""
                output = ""
                for conv in convs:
                    if conv['role'] == 'user':
                        instruction = conv['content']
                    elif conv['role'] == 'assistant':
                        output = conv['content']
                
                if instruction and output:
                    alpaca_data.append({
                        "instruction": instruction,
                        "input": "",
                        "output": output
                    })
    
    alpaca_path = r'D:\mira_easy_dataset\unprocessed_alpaca.json'
    save_json(alpaca_data, alpaca_path)
    print(f"已保存Alpaca格式数据到: {alpaca_path}")
    
    # 分批保存（每1000条一个文件，方便分批处理）
    batch_size = 1000
    for i in range(0, len(alpaca_data), batch_size):
        batch = alpaca_data[i:i+batch_size]
        batch_path = f'D:\\mira_easy_dataset\\batch_{i//batch_size + 1}.json'
        save_json(batch, batch_path)
        print(f"已保存批次 {i//batch_size + 1}: {len(batch)} 条 -> {batch_path}")
    
    print(f"\n=== 总结 ===")
    print(f"原始数据: {len(all_data)} 条")
    print(f"已处理: {len(processed_data)} 条")
    print(f"待处理: {len(unprocessed_data)} 条")
    print(f"批次文件: {(len(alpaca_data) + batch_size - 1) // batch_size} 个")

if __name__ == "__main__":
    main()
