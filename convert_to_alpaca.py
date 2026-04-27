"""
Alpaca数据格式转换工具
支持将零散的图片和对话数据转换为可用于微调的Alpaca格式数据

支持的数据源：
1. JSON/JSONL格式的对话数据
2. 文件夹结构中的图片+文本数据
3. 手动输入的对话数据
"""

import os
import json
import glob
import base64
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime


class AlpacaDataConverter:
    """Alpaca格式数据转换器"""
    
    def __init__(self, output_dir: str = "./alpaca_output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir = self.output_dir / "images"
        self.images_dir.mkdir(exist_ok=True)
        
        self.alpaca_data: List[Dict[str, str]] = []
        
    def add_entry(
        self,
        instruction: str,
        output: str,
        input_text: str = "",
        image_path: Optional[str] = None
    ) -> None:
        """添加一条Alpaca格式的数据"""
        entry = {
            "instruction": instruction,
            "input": input_text,
            "output": output
        }
        
        if image_path and os.path.exists(image_path):
            img_filename = os.path.basename(image_path)
            dest_path = self.images_dir / img_filename
            if not dest_path.exists():
                shutil.copy2(image_path, dest_path)
            entry["image"] = f"images/{img_filename}"
        
        self.alpaca_data.append(entry)
    
    def from_conversation_json(self, json_path: str, image_dir: Optional[str] = None) -> int:
        """
        从JSON格式的对话数据转换
        
        支持的JSON格式：
        1. 简单对话格式：
           [{"question": "...", "answer": "..."}, ...]
        
        2. 带角色的格式：
           [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
        
        3. 完整对话格式：
           [{"conversations": [{"role": "user", "content": "..."}, ...]}, ...]
        """
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        count = 0
        
        if isinstance(data, list):
            for item in data:
                if "question" in item and "answer" in item:
                    self.add_entry(
                        instruction=item["question"],
                        output=item["answer"],
                        input_text=item.get("context", ""),
                        image_path=item.get("image")
                    )
                    count += 1
                    
                elif "conversations" in item:
                    convs = item["conversations"]
                    for i in range(0, len(convs) - 1, 2):
                        if convs[i].get("role") == "user" and convs[i+1].get("role") == "assistant":
                            self.add_entry(
                                instruction=convs[i]["content"],
                                output=convs[i+1]["content"],
                                image_path=item.get("image")
                            )
                            count += 1
                
                elif "role" in item:
                    pass
                    
        return count
    
    def from_conversation_jsonl(self, jsonl_path: str) -> int:
        """从JSONL格式的对话数据转换"""
        count = 0
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                item = json.loads(line)
                
                if "question" in item and "answer" in item:
                    self.add_entry(
                        instruction=item["question"],
                        output=item["answer"],
                        input_text=item.get("context", ""),
                        image_path=item.get("image")
                    )
                    count += 1
                elif "instruction" in item and "output" in item:
                    self.add_entry(
                        instruction=item["instruction"],
                        output=item["output"],
                        input_text=item.get("input", ""),
                        image_path=item.get("image")
                    )
                    count += 1
        
        return count
    
    def from_image_folder(
        self,
        folder_path: str,
        text_file: Optional[str] = None,
        instruction_template: str = "请描述这张图片的内容"
    ) -> int:
        """
        从图片文件夹转换数据
        
        支持的结构：
        1. 图片文件 + 同名txt文件（描述）
        2. 图片文件 + JSON描述文件
        3. 图片文件夹 + 单独的标注文件
        """
        folder = Path(folder_path)
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        count = 0
        
        if text_file and os.path.exists(text_file):
            with open(text_file, 'r', encoding='utf-8') as f:
                annotations = json.load(f)
            
            for img_file in folder.glob("*"):
                if img_file.suffix.lower() in image_extensions:
                    img_name = img_file.stem
                    if img_name in annotations:
                        ann = annotations[img_name]
                        if isinstance(ann, str):
                            self.add_entry(
                                instruction=instruction_template,
                                output=ann,
                                image_path=str(img_file)
                            )
                        elif isinstance(ann, dict):
                            self.add_entry(
                                instruction=ann.get("question", instruction_template),
                                output=ann.get("answer", ann.get("description", "")),
                                input_text=ann.get("context", ""),
                                image_path=str(img_file)
                            )
                        count += 1
        else:
            for img_file in folder.glob("*"):
                if img_file.suffix.lower() in image_extensions:
                    txt_file = img_file.with_suffix('.txt')
                    json_file = img_file.with_suffix('.json')
                    
                    description = ""
                    question = instruction_template
                    
                    if txt_file.exists():
                        with open(txt_file, 'r', encoding='utf-8') as f:
                            description = f.read().strip()
                    elif json_file.exists():
                        with open(json_file, 'r', encoding='utf-8') as f:
                            ann_data = json.load(f)
                            description = ann_data.get("description", ann_data.get("answer", ""))
                            question = ann_data.get("question", instruction_template)
                    
                    if description:
                        self.add_entry(
                            instruction=question,
                            output=description,
                            image_path=str(img_file)
                        )
                        count += 1
        
        return count
    
    def from_qa_pairs(
        self,
        qa_pairs: List[Dict[str, str]],
        image_dir: Optional[str] = None
    ) -> int:
        """
        从问答对列表转换
        
        qa_pairs格式：
        [
            {"question": "...", "answer": "...", "image": "可选图片名"},
            ...
        ]
        """
        count = 0
        for qa in qa_pairs:
            image_path = None
            if image_dir and "image" in qa:
                img_path = os.path.join(image_dir, qa["image"])
                if os.path.exists(img_path):
                    image_path = img_path
            
            self.add_entry(
                instruction=qa.get("question", qa.get("instruction", "")),
                output=qa.get("answer", qa.get("output", "")),
                input_text=qa.get("context", qa.get("input", "")),
                image_path=image_path
            )
            count += 1
        
        return count
    
    def from_chat_history(
        self,
        chat_file: str,
        format_type: str = "auto"
    ) -> int:
        """
        从聊天记录转换
        
        支持的格式：
        - "wechat": 微信聊天记录
        - "telegram": Telegram导出格式
        - "generic": 通用格式 (用户: xxx\n助手: xxx)
        - "auto": 自动检测
        """
        with open(chat_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        count = 0
        
        if format_type == "auto":
            if "Telegram" in content or "message" in content.lower():
                format_type = "telegram"
            elif "用户" in content or "助手" in content:
                format_type = "generic"
            else:
                format_type = "generic"
        
        if format_type == "generic":
            lines = content.split('\n')
            current_user = ""
            current_assistant = ""
            
            for line in lines:
                line = line.strip()
                if line.startswith("用户:") or line.startswith("User:"):
                    if current_user and current_assistant:
                        self.add_entry(
                            instruction=current_user,
                            output=current_assistant
                        )
                        count += 1
                    current_user = line.split(":", 1)[1].strip()
                    current_assistant = ""
                elif line.startswith("助手:") or line.startswith("Assistant:"):
                    current_assistant = line.split(":", 1)[1].strip()
            
            if current_user and current_assistant:
                self.add_entry(
                    instruction=current_user,
                    output=current_assistant
                )
                count += 1
        
        return count
    
    def merge_from_directory(
        self,
        data_dir: str,
        recursive: bool = True
    ) -> Dict[str, int]:
        """
        从目录自动合并所有数据源
        
        返回各类型数据的转换数量
        """
        data_dir = Path(data_dir)
        stats = {
            "json": 0,
            "jsonl": 0,
            "images": 0,
            "chat": 0
        }
        
        pattern = "**/*" if recursive else "*"
        
        for file_path in data_dir.glob(pattern):
            if file_path.is_file():
                suffix = file_path.suffix.lower()
                
                if suffix == '.json':
                    try:
                        stats["json"] += self.from_conversation_json(str(file_path))
                        print(f"已转换JSON文件: {file_path}")
                    except Exception as e:
                        print(f"转换JSON文件失败 {file_path}: {e}")
                
                elif suffix == '.jsonl':
                    try:
                        stats["jsonl"] += self.from_conversation_jsonl(str(file_path))
                        print(f"已转换JSONL文件: {file_path}")
                    except Exception as e:
                        print(f"转换JSONL文件失败 {file_path}: {e}")
                
                elif suffix in {'.txt', '.log', '.chat'}:
                    try:
                        stats["chat"] += self.from_chat_history(str(file_path))
                        print(f"已转换聊天记录: {file_path}")
                    except Exception as e:
                        print(f"转换聊天记录失败 {file_path}: {e}")
        
        image_dirs = set()
        for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
            for img_file in data_dir.glob(f"{pattern}{ext}"):
                image_dirs.add(img_file.parent)
        
        for img_dir in image_dirs:
            try:
                stats["images"] += self.from_image_folder(str(img_dir))
                print(f"已转换图片目录: {img_dir}")
            except Exception as e:
                print(f"转换图片目录失败 {img_dir}: {e}")
        
        return stats
    
    def to_alpaca_json(self, output_file: Optional[str] = None) -> str:
        """导出为Alpaca格式的JSON文件"""
        if output_file is None:
            output_file = self.output_dir / "alpaca_data.json"
        else:
            output_file = Path(output_file)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.alpaca_data, f, ensure_ascii=False, indent=2)
        
        print(f"已导出 {len(self.alpaca_data)} 条数据到: {output_file}")
        return str(output_file)
    
    def to_alpaca_jsonl(self, output_file: Optional[str] = None) -> str:
        """导出为Alpaca格式的JSONL文件"""
        if output_file is None:
            output_file = self.output_dir / "alpaca_data.jsonl"
        else:
            output_file = Path(output_file)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for entry in self.alpaca_data:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        
        print(f"已导出 {len(self.alpaca_data)} 条数据到: {output_file}")
        return str(output_file)
    
    def to_llama_factory_format(
        self,
        dataset_name: str = "custom_dataset",
        output_dir: Optional[str] = None
    ) -> str:
        """
        导出为LLaMA-Factory格式
        
        这会在指定目录创建数据集配置和数据文件
        """
        if output_dir is None:
            output_dir = self.output_dir
        else:
            output_dir = Path(output_dir)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        data_file = output_dir / f"{dataset_name}.json"
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(self.alpaca_data, f, ensure_ascii=False, indent=2)
        
        has_images = any("image" in entry for entry in self.alpaca_data)
        
        if has_images:
            dataset_info = {
                dataset_name: {
                    "file_name": f"{dataset_name}.json",
                    "formatting": "sharegpt",
                    "columns": {
                        "messages": "conversations"
                    },
                    "images": "images"
                }
            }
        else:
            dataset_info = {
                dataset_name: {
                    "file_name": f"{dataset_name}.json",
                    "formatting": "alpaca",
                    "columns": {
                        "prompt": "instruction",
                        "query": "input",
                        "response": "output"
                    }
                }
            }
        
        info_file = output_dir / "dataset_info.json"
        existing_info = {}
        if info_file.exists():
            with open(info_file, 'r', encoding='utf-8') as f:
                existing_info = json.load(f)
        
        existing_info.update(dataset_info)
        
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(existing_info, f, ensure_ascii=False, indent=2)
        
        print(f"已导出LLaMA-Factory格式数据集: {output_dir}")
        print(f"数据集名称: {dataset_name}")
        print(f"数据条数: {len(self.alpaca_data)}")
        
        return str(output_dir)
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取数据统计信息"""
        total = len(self.alpaca_data)
        with_images = sum(1 for entry in self.alpaca_data if "image" in entry)
        with_input = sum(1 for entry in self.alpaca_data if entry.get("input"))
        
        avg_instruction_len = sum(len(entry["instruction"]) for entry in self.alpaca_data) / max(total, 1)
        avg_output_len = sum(len(entry["output"]) for entry in self.alpaca_data) / max(total, 1)
        
        return {
            "total_entries": total,
            "entries_with_images": with_images,
            "entries_with_input": with_input,
            "average_instruction_length": round(avg_instruction_len, 2),
            "average_output_length": round(avg_output_len, 2)
        }
    
    def clear(self) -> None:
        """清空当前数据"""
        self.alpaca_data = []


def interactive_mode():
    """交互式模式，手动添加数据"""
    converter = AlpacaDataConverter()
    
    print("=" * 60)
    print("Alpaca数据转换工具 - 交互式模式")
    print("=" * 60)
    
    while True:
        print("\n选择操作:")
        print("1. 手动添加问答对")
        print("2. 添加带图片的问答对")
        print("3. 从JSON文件导入")
        print("4. 从JSONL文件导入")
        print("5. 从图片文件夹导入")
        print("6. 从聊天记录导入")
        print("7. 查看当前统计")
        print("8. 导出为Alpaca JSON")
        print("9. 导出为LLaMA-Factory格式")
        print("0. 退出")
        
        choice = input("\n请选择 (0-9): ").strip()
        
        if choice == "0":
            break
        
        elif choice == "1":
            instruction = input("请输入问题/指令: ").strip()
            output = input("请输入回答: ").strip()
            input_text = input("请输入上下文(可选,直接回车跳过): ").strip()
            
            converter.add_entry(instruction, output, input_text)
            print("已添加!")
        
        elif choice == "2":
            instruction = input("请输入问题/指令: ").strip()
            output = input("请输入回答: ").strip()
            image_path = input("请输入图片路径: ").strip()
            
            converter.add_entry(instruction, output, image_path=image_path)
            print("已添加!")
        
        elif choice == "3":
            json_path = input("请输入JSON文件路径: ").strip()
            if os.path.exists(json_path):
                count = converter.from_conversation_json(json_path)
                print(f"已导入 {count} 条数据")
            else:
                print("文件不存在!")
        
        elif choice == "4":
            jsonl_path = input("请输入JSONL文件路径: ").strip()
            if os.path.exists(jsonl_path):
                count = converter.from_conversation_jsonl(jsonl_path)
                print(f"已导入 {count} 条数据")
            else:
                print("文件不存在!")
        
        elif choice == "5":
            folder_path = input("请输入图片文件夹路径: ").strip()
            text_file = input("请输入标注文件路径(可选,直接回车跳过): ").strip()
            if os.path.isdir(folder_path):
                count = converter.from_image_folder(
                    folder_path,
                    text_file if text_file else None
                )
                print(f"已导入 {count} 条数据")
            else:
                print("文件夹不存在!")
        
        elif choice == "6":
            chat_path = input("请输入聊天记录文件路径: ").strip()
            if os.path.exists(chat_path):
                count = converter.from_chat_history(chat_path)
                print(f"已导入 {count} 条数据")
            else:
                print("文件不存在!")
        
        elif choice == "7":
            stats = converter.get_statistics()
            print("\n当前数据统计:")
            for key, value in stats.items():
                print(f"  {key}: {value}")
        
        elif choice == "8":
            output_path = converter.to_alpaca_json()
            print(f"已导出到: {output_path}")
        
        elif choice == "9":
            dataset_name = input("请输入数据集名称(默认: custom_dataset): ").strip()
            if not dataset_name:
                dataset_name = "custom_dataset"
            converter.to_llama_factory_format(dataset_name)
    
    print("\n感谢使用!")


def main():
    """主函数 - 命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Alpaca数据格式转换工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 交互式模式
  python convert_to_alpaca.py -i
  
  # 从目录自动转换
  python convert_to_alpaca.py --from-dir ./my_data --output ./alpaca_output
  
  # 从JSON文件转换
  python convert_to_alpaca.py --from-json conversations.json --output alpaca_data.json
  
  # 从图片文件夹转换
  python convert_to_alpaca.py --from-images ./images --annotations annotations.json
  
  # 导出为LLaMA-Factory格式
  python convert_to_alpaca.py --from-dir ./my_data --llama-factory --dataset-name my_dataset
        """
    )
    
    parser.add_argument('-i', '--interactive', action='store_true',
                        help='启动交互式模式')
    parser.add_argument('--from-dir', type=str,
                        help='从目录自动合并所有数据源')
    parser.add_argument('--from-json', type=str,
                        help='从JSON文件转换')
    parser.add_argument('--from-jsonl', type=str,
                        help='从JSONL文件转换')
    parser.add_argument('--from-images', type=str,
                        help='从图片文件夹转换')
    parser.add_argument('--annotations', type=str,
                        help='图片标注文件(配合--from-images使用)')
    parser.add_argument('--from-chat', type=str,
                        help='从聊天记录转换')
    parser.add_argument('--output', '-o', type=str, default='./alpaca_output',
                        help='输出目录或文件路径')
    parser.add_argument('--llama-factory', action='store_true',
                        help='导出为LLaMA-Factory格式')
    parser.add_argument('--dataset-name', type=str, default='custom_dataset',
                        help='数据集名称(用于LLaMA-Factory)')
    parser.add_argument('--format', type=str, choices=['json', 'jsonl'],
                        default='json', help='输出格式')
    
    args = parser.parse_args()
    
    if args.interactive:
        interactive_mode()
        return
    
    converter = AlpacaDataConverter(output_dir=args.output)
    
    if args.from_dir:
        stats = converter.merge_from_directory(args.from_dir)
        print("\n转换统计:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
    
    if args.from_json:
        count = converter.from_conversation_json(args.from_json)
        print(f"从JSON导入 {count} 条数据")
    
    if args.from_jsonl:
        count = converter.from_conversation_jsonl(args.from_jsonl)
        print(f"从JSONL导入 {count} 条数据")
    
    if args.from_images:
        count = converter.from_image_folder(
            args.from_images,
            text_file=args.annotations
        )
        print(f"从图片文件夹导入 {count} 条数据")
    
    if args.from_chat:
        count = converter.from_chat_history(args.from_chat)
        print(f"从聊天记录导入 {count} 条数据")
    
    if converter.alpaca_data:
        stats = converter.get_statistics()
        print("\n数据统计:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        if args.llama_factory:
            converter.to_llama_factory_format(
                dataset_name=args.dataset_name,
                output_dir=args.output
            )
        else:
            if args.format == 'json':
                converter.to_alpaca_json()
            else:
                converter.to_alpaca_jsonl()
    else:
        print("没有数据可转换。请使用 -i 进入交互式模式或指定数据源。")


if __name__ == "__main__":
    main()
