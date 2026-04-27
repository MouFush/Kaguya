import json
import os
import base64
import shutil
from pathlib import Path

def extract_image_text_pairs():
    """从mira_export提取图片-文本对"""
    mira_export = r'D:\mira_export'
    images_folder = os.path.join(mira_export, 'images')
    forward_folder = os.path.join(mira_export, 'forward')
    
    all_pairs = []
    
    def find_image(image_value):
        basename = os.path.basename(image_value)
        target_path = os.path.join(images_folder, basename)
        if os.path.exists(target_path):
            return target_path
        hash_name = basename.replace('.jpg', '').replace('.png', '').replace('.gif', '').replace('.webp', '')
        for ext in ['.jpg', '.png', '.gif', '.webp', '.jpeg', '.bmp']:
            potential = os.path.join(images_folder, hash_name + ext)
            if os.path.exists(potential):
                return potential
        return None
    
    def get_text_context(context):
        texts = []
        for item in context:
            if item.get('type') == 'text':
                text = item.get('value', '').strip()
                if text and len(text) > 1:
                    texts.append(text)
        return texts
    
    jsonl_files = [f for f in os.listdir(mira_export) if f.endswith('.jsonl')]
    for jsonl_file in jsonl_files:
        filepath = os.path.join(mira_export, jsonl_file)
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
                    image_path = find_image(image_value)
                    
                    if image_path:
                        before_texts = []
                        after_texts = []
                        
                        for j in range(max(0, i-2), i):
                            texts = get_text_context(messages[j].get('context', []))
                            before_texts.extend(texts)
                        
                        for j in range(i+1, min(len(messages), i+3)):
                            texts = get_text_context(messages[j].get('context', []))
                            after_texts.extend(texts)
                        
                        context_text = ' '.join(before_texts + after_texts)
                        
                        if context_text and len(context_text) >= 5:
                            all_pairs.append({
                                'image_path': image_path,
                                'image_name': os.path.basename(image_path),
                                'context': context_text[:300]
                            })
    
    if os.path.exists(forward_folder):
        forward_files = [f for f in os.listdir(forward_folder) if f.endswith('.json')]
        for forward_file in forward_files[:200]:
            filepath = os.path.join(forward_folder, forward_file)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                messages = data.get('messages', [])
                for i, msg in enumerate(messages):
                    context = msg.get('context', [])
                    for item in context:
                        if item.get('type') == 'image':
                            image_value = item.get('value', '')
                            image_path = find_image(image_value)
                            
                            if image_path:
                                before_texts = []
                                after_texts = []
                                
                                for j in range(max(0, i-2), i):
                                    texts = get_text_context(messages[j].get('context', []))
                                    before_texts.extend(texts)
                                
                                for j in range(i+1, min(len(messages), i+3)):
                                    texts = get_text_context(messages[j].get('context', []))
                                    after_texts.extend(texts)
                                
                                context_text = ' '.join(before_texts + after_texts)
                                
                                if context_text and len(context_text) >= 5:
                                    all_pairs.append({
                                        'image_path': image_path,
                                        'image_name': os.path.basename(image_path),
                                        'context': context_text[:300]
                                    })
            except:
                continue
    
    unique_pairs = {}
    for pair in all_pairs:
        img_name = pair['image_name']
        if img_name not in unique_pairs:
            unique_pairs[img_name] = pair
        else:
            if len(pair['context']) > len(unique_pairs[img_name]['context']):
                unique_pairs[img_name] = pair
    
    return list(unique_pairs.values())

def generate_multimodal_dataset(pairs, output_folder):
    """生成多模态训练数据集"""
    os.makedirs(output_folder, exist_ok=True)
    images_output = os.path.join(output_folder, 'images')
    os.makedirs(images_output, exist_ok=True)
    
    llava_format = []
    sharegpt_format = []
    alpaca_format = []
    
    print(f"处理 {len(pairs)} 个图片-文本对...")
    
    for i, pair in enumerate(pairs):
        image_path = pair['image_path']
        image_name = pair['image_name']
        context = pair['context']
        
        dest_image_path = os.path.join(images_output, image_name)
        if not os.path.exists(dest_image_path):
            try:
                shutil.copy2(image_path, dest_image_path)
            except:
                continue
        
        instruction = "请描述这张图片的内容"
        
        llava_item = {
            "id": f"img_{i:05d}",
            "image": f"images/{image_name}",
            "conversations": [
                {
                    "from": "human",
                    "value": "<image>\n请描述这张图片的内容"
                },
                {
                    "from": "gpt",
                    "value": context
                }
            ]
        }
        llava_format.append(llava_item)
        
        sharegpt_item = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"images/{image_name}"}},
                        {"type": "text", "text": "请描述这张图片的内容"}
                    ]
                },
                {
                    "role": "assistant",
                    "content": context
                }
            ]
        }
        sharegpt_format.append(sharegpt_item)
        
        alpaca_item = {
            "instruction": instruction,
            "input": f"<image>images/{image_name}",
            "output": context
        }
        alpaca_format.append(alpaca_item)
    
    llava_path = os.path.join(output_folder, 'llava_format.json')
    with open(llava_path, 'w', encoding='utf-8') as f:
        json.dump(llava_format, f, ensure_ascii=False, indent=2)
    
    sharegpt_path = os.path.join(output_folder, 'sharegpt_format.json')
    with open(sharegpt_path, 'w', encoding='utf-8') as f:
        json.dump(sharegpt_format, f, ensure_ascii=False, indent=2)
    
    alpaca_path = os.path.join(output_folder, 'alpaca_format.json')
    with open(alpaca_path, 'w', encoding='utf-8') as f:
        json.dump(alpaca_format, f, ensure_ascii=False, indent=2)
    
    return llava_path, sharegpt_path, alpaca_path, len(llava_format)

def main():
    print("=" * 60)
    print("多模态训练数据集生成器")
    print("=" * 60)
    
    output_folder = r'D:\mira_multimodal_dataset'
    
    print("\n步骤1: 提取图片-文本对...")
    pairs = extract_image_text_pairs()
    print(f"提取到 {len(pairs)} 个唯一图片-文本对")
    
    print("\n步骤2: 生成训练数据集...")
    llava_path, sharegpt_path, alpaca_path, count = generate_multimodal_dataset(pairs, output_folder)
    
    print(f"\n输出文件:")
    print(f"  LLaVA格式: {llava_path}")
    print(f"  ShareGPT格式: {sharegpt_path}")
    print(f"  Alpaca格式: {alpaca_path}")
    print(f"  图片文件夹: {output_folder}\\images")
    print(f"  数据条数: {count}")
    
    summary = {
        'total_pairs': count,
        'formats': ['llava', 'sharegpt', 'alpaca'],
        'output_folder': output_folder,
        'note': '此数据集可用于多模态模型微调，如LLaVA、Qwen-VL等'
    }
    summary_path = os.path.join(output_folder, 'dataset_info.json')
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"\n处理完成! 数据集已保存到: {output_folder}")

if __name__ == '__main__':
    main()
