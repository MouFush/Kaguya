"""
将mira_export数据转换为Easy Dataset格式
支持图片+文本混合数据
"""

import os
import json
import shutil
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime


class MiraToEasyDataset:
    """将Mira导出数据转换为Easy Dataset格式"""
    
    def __init__(self, mira_dir: str, output_dir: str):
        self.mira_dir = Path(mira_dir)
        self.output_dir = Path(output_dir)
        self.images_dir = self.mira_dir / "images"
        self.forward_dir = self.mira_dir / "forward"
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.output_images_dir = self.output_dir / "images"
        self.output_images_dir.mkdir(exist_ok=True)
        
        self.image_map = {}
        self._build_image_map()
    
    def _build_image_map(self):
        """构建图片文件名映射"""
        if self.images_dir.exists():
            for img_file in self.images_dir.glob("*"):
                self.image_map[img_file.name] = str(img_file)
    
    def process_all(self) -> Dict[str, int]:
        """处理所有数据"""
        stats = {
            "jsonl_messages": 0,
            "forward_messages": 0,
            "images_copied": 0,
            "qa_pairs": 0
        }
        
        jsonl_files = list(self.mira_dir.glob("*.jsonl"))
        for jsonl_file in jsonl_files:
            count = self._process_jsonl(jsonl_file)
            stats["jsonl_messages"] += count
        
        if self.forward_dir.exists():
            for json_file in self.forward_dir.glob("*.json"):
                count = self._process_forward_json(json_file)
                stats["forward_messages"] += count
        
        return stats
    
    def _process_jsonl(self, jsonl_file: Path) -> int:
        """处理JSONL聊天记录"""
        messages = []
        
        with open(jsonl_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                    messages.append(msg)
                except:
                    continue
        
        qa_pairs = self._extract_qa_pairs(messages)
        self._save_qa_pairs(qa_pairs, jsonl_file.stem)
        
        return len(messages)
    
    def _process_forward_json(self, json_file: Path) -> int:
        """处理转发消息JSON"""
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        messages = data.get("messages", [])
        qa_pairs = self._extract_qa_pairs(messages)
        self._save_qa_pairs(qa_pairs, f"forward_{json_file.stem}")
        
        return len(messages)
    
    def _extract_qa_pairs(self, messages: List[Dict]) -> List[Dict]:
        """从消息中提取问答对"""
        qa_pairs = []
        
        i = 0
        while i < len(messages):
            msg = messages[i]
            context = msg.get("context", [])
            nickname = msg.get("nickname", "用户")
            
            text_content = []
            image_content = []
            
            for item in context:
                item_type = item.get("type", "")
                
                if item_type == "text":
                    text_content.append(item.get("value", ""))
                elif item_type == "image":
                    img_path = item.get("value", "")
                    img_name = os.path.basename(img_path)
                    if img_name in self.image_map:
                        dest_path = self.output_images_dir / img_name
                        if not dest_path.exists():
                            shutil.copy2(self.image_map[img_name], dest_path)
                        image_content.append(f"images/{img_name}")
            
            if text_content or image_content:
                full_text = " ".join(text_content)
                
                if i + 1 < len(messages):
                    next_msg = messages[i + 1]
                    next_context = next_msg.get("context", [])
                    next_nickname = next_msg.get("nickname", "用户")
                    next_text = []
                    next_images = []
                    
                    for item in next_context:
                        item_type = item.get("type", "")
                        if item_type == "text":
                            next_text.append(item.get("value", ""))
                        elif item_type == "image":
                            img_path = item.get("value", "")
                            img_name = os.path.basename(img_path)
                            if img_name in self.image_map:
                                dest_path = self.output_images_dir / img_name
                                if not dest_path.exists():
                                    shutil.copy2(self.image_map[img_name], dest_path)
                                next_images.append(f"images/{img_name}")
                    
                    if next_text or next_images:
                        qa_pairs.append({
                            "instruction": full_text,
                            "input": "",
                            "output": " ".join(next_text),
                            "images": image_content + next_images,
                            "metadata": {
                                "source": "mira_export",
                                "user1": nickname,
                                "user2": next_nickname
                            }
                        })
                        i += 2
                        continue
            
            i += 1
        
        return qa_pairs
    
    def _save_qa_pairs(self, qa_pairs: List[Dict], prefix: str):
        """保存问答对到文件"""
        if not qa_pairs:
            return
        
        output_file = self.output_dir / f"{prefix}_qa.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(qa_pairs, f, ensure_ascii=False, indent=2)
        
        print(f"已保存 {len(qa_pairs)} 条问答对到: {output_file}")
    
    def export_for_easy_dataset(self, output_file: str = None):
        """导出为Easy Dataset格式"""
        all_qa_pairs = []
        
        for json_file in self.output_dir.glob("*_qa.json"):
            with open(json_file, 'r', encoding='utf-8') as f:
                qa_pairs = json.load(f)
                all_qa_pairs.extend(qa_pairs)
        
        if output_file is None:
            output_file = self.output_dir / "easy_dataset_import.json"
        else:
            output_file = Path(output_file)
        
        easy_dataset_format = []
        
        for qa in all_qa_pairs:
            entry = {
                "conversations": [
                    {"role": "user", "content": qa["instruction"]},
                    {"role": "assistant", "content": qa["output"]}
                ]
            }
            
            if qa.get("images"):
                entry["images"] = qa["images"]
            
            easy_dataset_format.append(entry)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(easy_dataset_format, f, ensure_ascii=False, indent=2)
        
        print(f"已导出 {len(easy_dataset_format)} 条数据到: {output_file}")
        return str(output_file)
    
    def generate_image_dataset(self):
        """生成纯图片数据集（用于Easy Dataset图片处理）"""
        image_data = []
        
        for img_name, img_path in self.image_map.items():
            dest_path = self.output_images_dir / img_name
            if not dest_path.exists():
                shutil.copy2(img_path, dest_path)
            
            image_data.append({
                "image": f"images/{img_name}",
                "instruction": "请描述这张图片的内容",
                "output": ""
            })
        
        output_file = self.output_dir / "image_dataset.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(image_data, f, ensure_ascii=False, indent=2)
        
        print(f"已生成 {len(image_data)} 条图片数据到: {output_file}")
        return str(output_file)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="将Mira导出数据转换为Easy Dataset格式")
    parser.add_argument("--input", "-i", default=r"D:\mira_export", help="Mira导出目录")
    parser.add_argument("--output", "-o", default=r"D:\mira_easy_dataset", help="输出目录")
    parser.add_argument("--images-only", action="store_true", help="只处理图片")
    
    args = parser.parse_args()
    
    converter = MiraToEasyDataset(args.input, args.output)
    
    if args.images_only:
        converter.generate_image_dataset()
    else:
        stats = converter.process_all()
        print(f"\n处理统计:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        converter.export_for_easy_dataset()
        converter.generate_image_dataset()


if __name__ == "__main__":
    main()
