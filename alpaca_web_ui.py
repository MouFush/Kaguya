"""
Alpaca数据转换工具 - Web前端
基于Gradio构建的可视化界面
"""

import os
import json
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import gradio as gr

from convert_to_alpaca import AlpacaDataConverter


class AlpacaWebConverter:
    """Web版本的Alpaca数据转换器"""
    
    def __init__(self):
        self.converter = None
        self.temp_dir = tempfile.mkdtemp()
        self.output_dir = os.path.join(self.temp_dir, "alpaca_output")
        self.current_data = []
        
    def process_uploaded_files(
        self,
        files: List,
        progress=gr.Progress()
    ) -> Tuple[str, str, str]:
        """处理上传的文件"""
        if not files:
            return "请上传文件！", "", ""
        
        progress(0, desc="初始化...")
        
        self.converter = AlpacaDataConverter(output_dir=self.output_dir)
        
        upload_dir = os.path.join(self.temp_dir, "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        
        stats = {
            "json": 0,
            "jsonl": 0,
            "images": 0,
            "chat": 0,
            "errors": []
        }
        
        total_files = len(files)
        
        for idx, file in enumerate(files):
            progress((idx + 1) / total_files, desc=f"处理文件 {idx + 1}/{total_files}...")
            
            try:
                file_path = file.name if hasattr(file, 'name') else file
                filename = os.path.basename(file_path)
                
                dest_path = os.path.join(upload_dir, filename)
                shutil.copy2(file_path, dest_path)
                
                ext = os.path.splitext(filename)[1].lower()
                
                if ext == '.json':
                    try:
                        count = self.converter.from_conversation_json(dest_path)
                        stats["json"] += count
                    except Exception as e:
                        stats["errors"].append(f"{filename}: {str(e)}")
                
                elif ext == '.jsonl':
                    try:
                        count = self.converter.from_conversation_jsonl(dest_path)
                        stats["jsonl"] += count
                    except Exception as e:
                        stats["errors"].append(f"{filename}: {str(e)}")
                
                elif ext in {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}:
                    pass
                
                elif ext in {'.txt', '.log', '.chat'}:
                    try:
                        count = self.converter.from_chat_history(dest_path)
                        stats["chat"] += count
                    except Exception as e:
                        stats["errors"].append(f"{filename}: {str(e)}")
            
            except Exception as e:
                stats["errors"].append(f"处理文件失败: {str(e)}")
        
        progress(0.9, desc="处理图片...")
        
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        image_files = []
        
        for root, dirs, files_in_dir in os.walk(upload_dir):
            for f in files_in_dir:
                if os.path.splitext(f)[1].lower() in image_extensions:
                    image_files.append(os.path.join(root, f))
        
        if image_files:
            img_dir = os.path.dirname(image_files[0])
            count = self.converter.from_image_folder(img_dir)
            stats["images"] += count
        
        progress(1.0, desc="完成！")
        
        self.current_data = self.converter.alpaca_data
        
        summary = self._generate_summary(stats)
        preview = self._generate_preview()
        
        return summary, preview, ""
    
    def process_zip_file(
        self,
        zip_file,
        progress=gr.Progress()
    ) -> Tuple[str, str, str]:
        """处理上传的ZIP压缩包"""
        if not zip_file:
            return "请上传ZIP文件！", "", ""
        
        progress(0, desc="解压文件...")
        
        self.converter = AlpacaDataConverter(output_dir=self.output_dir)
        
        extract_dir = os.path.join(self.temp_dir, "extracted")
        os.makedirs(extract_dir, exist_ok=True)
        
        try:
            zip_path = zip_file.name if hasattr(zip_file, 'name') else zip_file
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
        except Exception as e:
            return f"解压失败: {str(e)}", "", ""
        
        progress(0.2, desc="扫描文件...")
        
        stats = self.converter.merge_from_directory(extract_dir, recursive=True)
        
        progress(0.9, desc="生成数据...")
        
        self.current_data = self.converter.alpaca_data
        
        summary = self._generate_summary(stats)
        preview = self._generate_preview()
        
        progress(1.0, desc="完成！")
        
        return summary, preview, ""
    
    def _generate_summary(self, stats: Dict) -> str:
        """生成处理摘要"""
        converter_stats = self.converter.get_statistics() if self.converter else {}
        
        summary = f"""## 📊 处理结果摘要

### 数据统计
| 类型 | 数量 |
|------|------|
| JSON数据 | {stats.get('json', 0)} |
| JSONL数据 | {stats.get('jsonl', 0)} |
| 图片数据 | {stats.get('images', 0)} |
| 聊天记录 | {stats.get('chat', 0)} |

### 数据集信息
- **总条目数**: {converter_stats.get('total_entries', 0)}
- **包含图片**: {converter_stats.get('entries_with_images', 0)} 条
- **包含上下文**: {converter_stats.get('entries_with_input', 0)} 条
- **平均指令长度**: {converter_stats.get('average_instruction_length', 0)} 字符
- **平均输出长度**: {converter_stats.get('average_output_length', 0)} 字符
"""
        
        if stats.get('errors'):
            summary += "\n### ⚠️ 处理警告\n"
            for err in stats['errors'][:5]:
                summary += f"- {err}\n"
            if len(stats['errors']) > 5:
                summary += f"- ... 还有 {len(stats['errors']) - 5} 个错误\n"
        
        return summary
    
    def _generate_preview(self, num_items: int = 10) -> str:
        """生成数据预览"""
        if not self.current_data:
            return "暂无数据"
        
        preview = f"## 📝 数据预览 (前{min(num_items, len(self.current_data))}条)\n\n"
        
        for i, entry in enumerate(self.current_data[:num_items]):
            preview += f"### 条目 {i + 1}\n"
            preview += f"**指令**: {entry.get('instruction', '')[:200]}{'...' if len(entry.get('instruction', '')) > 200 else ''}\n\n"
            
            if entry.get('input'):
                preview += f"**输入**: {entry['input'][:100]}{'...' if len(entry['input']) > 100 else ''}\n\n"
            
            preview += f"**输出**: {entry.get('output', '')[:200]}{'...' if len(entry.get('output', '')) > 200 else ''}\n\n"
            
            if entry.get('image'):
                preview += f"**图片**: {entry['image']}\n\n"
            
            preview += "---\n\n"
        
        return preview
    
    def add_manual_entry(
        self,
        instruction: str,
        output: str,
        input_text: str,
        image
    ) -> Tuple[str, str]:
        """手动添加数据条目"""
        if not instruction or not output:
            return "指令和输出不能为空！", ""
        
        if not self.converter:
            self.converter = AlpacaDataConverter(output_dir=self.output_dir)
        
        image_path = None
        if image:
            image_path = image.name if hasattr(image, 'name') else image
        
        self.converter.add_entry(
            instruction=instruction,
            output=output,
            input_text=input_text,
            image_path=image_path
        )
        
        self.current_data = self.converter.alpaca_data
        
        stats = self.converter.get_statistics()
        preview = self._generate_preview()
        
        return f"✅ 已添加！当前共 {stats['total_entries']} 条数据", preview
    
    def export_alpaca_json(self) -> Optional[str]:
        """导出Alpaca JSON格式"""
        if not self.converter or not self.current_data:
            return None
        
        output_path = os.path.join(self.output_dir, "alpaca_data.json")
        self.converter.to_alpaca_json(output_path)
        return output_path
    
    def export_alpaca_jsonl(self) -> Optional[str]:
        """导出Alpaca JSONL格式"""
        if not self.converter or not self.current_data:
            return None
        
        output_path = os.path.join(self.output_dir, "alpaca_data.jsonl")
        self.converter.to_alpaca_jsonl(output_path)
        return output_path
    
    def export_llama_factory(self, dataset_name: str) -> Optional[str]:
        """导出LLaMA-Factory格式"""
        if not self.converter or not self.current_data:
            return None
        
        self.converter.to_llama_factory_format(
            dataset_name=dataset_name,
            output_dir=self.output_dir
        )
        
        return self.output_dir
    
    def export_and_package(self, export_format: str, dataset_name: str) -> Tuple[str, Optional[str]]:
        """导出并打包"""
        if not self.converter or not self.current_data:
            return "没有数据可导出！", None
        
        if export_format == "json":
            self.export_alpaca_json()
        elif export_format == "jsonl":
            self.export_alpaca_jsonl()
        elif export_format == "llama_factory":
            self.export_llama_factory(dataset_name)
        
        zip_path = os.path.join(self.temp_dir, f"alpaca_dataset_{dataset_name}.zip")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(self.output_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, self.output_dir)
                    zipf.write(file_path, arcname)
        
        return f"✅ 已导出 {len(self.current_data)} 条数据到压缩包", zip_path
    
    def clear_data(self) -> Tuple[str, str]:
        """清空当前数据"""
        if self.converter:
            self.converter.clear()
        self.current_data = []
        
        return "✅ 数据已清空", ""


def create_interface():
    """创建Gradio界面"""
    converter = AlpacaWebConverter()
    
    with gr.Blocks(
        title="Alpaca数据转换工具",
        theme=gr.themes.Soft(),
        css="""
        .main-title {text-align: center; margin-bottom: 20px;}
        .section-title {margin-top: 20px; margin-bottom: 10px;}
        """
    ) as demo:
        
        gr.Markdown(
            """
            # 🦙 Alpaca数据转换工具
            ### 将零散的图片和对话数据转换为可用于微调的Alpaca格式数据
            """,
            elem_classes=["main-title"]
        )
        
        with gr.Tabs():
            with gr.TabItem("📁 批量导入"):
                gr.Markdown("### 上传文件包")
                gr.Markdown("支持上传多个文件或ZIP压缩包，自动识别JSON、JSONL、图片和聊天记录")
                
                with gr.Row():
                    with gr.Column(scale=1):
                        file_input = gr.File(
                            label="上传文件（支持多选）",
                            file_count="multiple",
                            type="filepath"
                        )
                        process_btn = gr.Button("🔄 处理文件", variant="primary", size="lg")
                        
                        gr.Markdown("---")
                        gr.Markdown("### 或者上传ZIP压缩包")
                        
                        zip_input = gr.File(
                            label="上传ZIP压缩包",
                            file_types=[".zip"],
                            type="filepath"
                        )
                        process_zip_btn = gr.Button("📦 处理ZIP", variant="secondary", size="lg")
                
                with gr.Row():
                    summary_output = gr.Markdown(
                        label="处理结果",
                        elem_classes=["section-title"]
                    )
                
                with gr.Row():
                    preview_output = gr.Markdown(
                        label="数据预览",
                        elem_classes=["section-title"]
                    )
            
            with gr.TabItem("✏️ 手动添加"):
                gr.Markdown("### 手动添加数据条目")
                
                with gr.Row():
                    with gr.Column(scale=2):
                        manual_instruction = gr.Textbox(
                            label="指令/问题",
                            placeholder="输入问题或指令...",
                            lines=3
                        )
                        manual_input = gr.Textbox(
                            label="上下文输入（可选）",
                            placeholder="输入相关上下文...",
                            lines=2
                        )
                        manual_output = gr.Textbox(
                            label="输出/回答",
                            placeholder="输入回答或响应...",
                            lines=5
                        )
                    
                    with gr.Column(scale=1):
                        manual_image = gr.File(
                            label="上传图片（可选）",
                            file_types=["image"],
                            type="filepath"
                        )
                
                add_btn = gr.Button("➕ 添加数据", variant="primary")
                add_status = gr.Markdown()
                manual_preview = gr.Markdown()
            
            with gr.TabItem("📤 导出"):
                gr.Markdown("### 导出数据")
                
                with gr.Row():
                    with gr.Column():
                        export_format = gr.Radio(
                            choices=[
                                ("Alpaca JSON", "json"),
                                ("Alpaca JSONL", "jsonl"),
                                ("LLaMA-Factory", "llama_factory")
                            ],
                            value="json",
                            label="导出格式"
                        )
                        
                        dataset_name = gr.Textbox(
                            label="数据集名称",
                            value="my_dataset",
                            placeholder="输入数据集名称..."
                        )
                        
                        export_btn = gr.Button("📦 导出并打包下载", variant="primary", size="lg")
                        clear_btn = gr.Button("🗑️ 清空数据", variant="secondary")
                
                export_status = gr.Markdown()
                download_file = gr.File(label="下载文件")
        
        process_btn.click(
            fn=converter.process_uploaded_files,
            inputs=[file_input],
            outputs=[summary_output, preview_output, preview_output]
        )
        
        process_zip_btn.click(
            fn=converter.process_zip_file,
            inputs=[zip_input],
            outputs=[summary_output, preview_output, preview_output]
        )
        
        add_btn.click(
            fn=converter.add_manual_entry,
            inputs=[manual_instruction, manual_output, manual_input, manual_image],
            outputs=[add_status, manual_preview]
        )
        
        export_btn.click(
            fn=converter.export_and_package,
            inputs=[export_format, dataset_name],
            outputs=[export_status, download_file]
        )
        
        clear_btn.click(
            fn=converter.clear_data,
            outputs=[export_status, download_file]
        )
    
    return demo


def main():
    """启动Web服务"""
    demo = create_interface()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )


if __name__ == "__main__":
    main()
