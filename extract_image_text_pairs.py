import json
import os
import hashlib
import re
from pathlib import Path

def get_file_hash(filepath):
    """计算文件的MD5哈希"""
    try:
        with open(filepath, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except:
        return None

def find_image_in_folder(image_name, images_folder):
    """在图片文件夹中查找图片"""
    if not image_name:
        return None
    
    basename = os.path.basename(image_name)
    target_path = os.path.join(images_folder, basename)
    if os.path.exists(target_path):
        return target_path
    
    hash_from_name = basename.replace('.jpg', '').replace('.png', '').replace('.gif', '').replace('.webp', '')
    
    for ext in ['.jpg', '.png', '.gif', '.webp', '.jpeg', '.bmp']:
        potential_path = os.path.join(images_folder, hash_from_name + ext)
        if os.path.exists(potential_path):
            return potential_path
    
    return None

def extract_text_from_context(context):
    """从context中提取文本"""
    texts = []
    for item in context:
        if item.get('type') == 'text':
            text = item.get('value', '').strip()
            if text:
                texts.append(text)
    return texts

def process_jsonl_file(filepath, images_folder):
    """处理JSONL文件，提取图片-文本对"""
    pairs = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    messages = []
    for line in lines:
        try:
            msg = json.loads(line.strip())
            messages.append(msg)
        except:
            continue
    
    for i, msg in enumerate(messages):
        context = msg.get('context', [])
        
        for item in context:
            if item.get('type') == 'image':
                image_value = item.get('value', '')
                image_path = find_image_in_folder(image_value, images_folder)
                
                if image_path:
                    context_texts = []
                    
                    for j in range(max(0, i-3), min(len(messages), i+4)):
                        texts = extract_text_from_context(messages[j].get('context', []))
                        context_texts.extend(texts)
                    
                    if context_texts:
                        pairs.append({
                            'image_path': image_path,
                            'image_name': os.path.basename(image_path),
                            'context_text': ' '.join(context_texts),
                            'source': os.path.basename(filepath)
                        })
    
    return pairs

def process_forward_file(filepath, images_folder):
    """处理转发消息JSON文件"""
    pairs = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except:
        return pairs
    
    messages = data.get('messages', [])
    
    for i, msg in enumerate(messages):
        context = msg.get('context', [])
        
        for item in context:
            if item.get('type') == 'image':
                image_value = item.get('value', '')
                image_path = find_image_in_folder(image_value, images_folder)
                
                if image_path:
                    context_texts = []
                    
                    for j in range(max(0, i-3), min(len(messages), i+4)):
                        texts = extract_text_from_context(messages[j].get('context', []))
                        context_texts.extend(texts)
                    
                    if context_texts:
                        pairs.append({
                            'image_path': image_path,
                            'image_name': os.path.basename(image_path),
                            'context_text': ' '.join(context_texts),
                            'source': os.path.basename(filepath)
                        })
    
    return pairs

def generate_training_data(pairs, output_folder):
    """生成训练数据"""
    os.makedirs(output_folder, exist_ok=True)
    
    alpaca_data = []
    llava_data = []
    
    for pair in pairs:
        image_path = pair['image_path']
        context_text = pair['context_text']
        
        alpaca_item = {
            "instruction": "请描述这张图片的内容",
            "input": "",
            "output": context_text[:500] if len(context_text) > 500 else context_text
        }
        alpaca_data.append(alpaca_item)
        
        llava_item = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": image_path},
                        {"type": "text", "text": "请描述这张图片"}
                    ]
                },
                {
                    "role": "assistant",
                    "content": context_text[:500] if len(context_text) > 500 else context_text
                }
            ]
        }
        llava_data.append(llava_item)
    
    alpaca_path = os.path.join(output_folder, 'image_text_alpaca.json')
    with open(alpaca_path, 'w', encoding='utf-8') as f:
        json.dump(alpaca_data, f, ensure_ascii=False, indent=2)
    
    llava_path = os.path.join(output_folder, 'image_text_llava.json')
    with open(llava_path, 'w', encoding='utf-8') as f:
        json.dump(llava_data, f, ensure_ascii=False, indent=2)
    
    return alpaca_path, llava_path, len(alpaca_data)

def main():
    mira_export = r'D:\mira_export'
    images_folder = os.path.join(mira_export, 'images')
    forward_folder = os.path.join(mira_export, 'forward')
    output_folder = r'D:\mira_image_dataset'
    
    print("=" * 60)
    print("图片-文本对提取工具")
    print("=" * 60)
    
    all_pairs = []
    
    jsonl_files = [f for f in os.listdir(mira_export) if f.endswith('.jsonl')]
    for jsonl_file in jsonl_files:
        filepath = os.path.join(mira_export, jsonl_file)
        print(f"处理文件: {jsonl_file}")
        pairs = process_jsonl_file(filepath, images_folder)
        all_pairs.extend(pairs)
        print(f"  提取到 {len(pairs)} 个图片-文本对")
    
    if os.path.exists(forward_folder):
        forward_files = [f for f in os.listdir(forward_folder) if f.endswith('.json')]
        for forward_file in forward_files[:100]:
            filepath = os.path.join(forward_folder, forward_file)
            pairs = process_forward_file(filepath, images_folder)
            all_pairs.extend(pairs)
    
    print(f"\n总共提取到 {len(all_pairs)} 个图片-文本对")
    
    unique_pairs = {}
    for pair in all_pairs:
        img_name = pair['image_name']
        if img_name not in unique_pairs:
            unique_pairs[img_name] = pair
        else:
            existing_text = unique_pairs[img_name]['context_text']
            new_text = pair['context_text']
            if len(new_text) > len(existing_text):
                unique_pairs[img_name] = pair
    
    final_pairs = list(unique_pairs.values())
    print(f"去重后: {len(final_pairs)} 个唯一图片-文本对")
    
    alpaca_path, llava_path, count = generate_training_data(final_pairs, output_folder)
    
    print(f"\n输出文件:")
    print(f"  Alpaca格式: {alpaca_path}")
    print(f"  LLaVA格式: {llava_path}")
    print(f"  数据条数: {count}")
    
    summary_path = os.path.join(output_folder, 'extraction_summary.json')
    summary = {
        'total_pairs': len(all_pairs),
        'unique_pairs': len(final_pairs),
        'output_files': {
            'alpaca': alpaca_path,
            'llava': llava_path
        }
    }
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"\n处理完成!")

if __name__ == '__main__':
    main()
