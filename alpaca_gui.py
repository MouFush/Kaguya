"""
Alpaca数据转换工具 - 桌面GUI版本
基于tkinter构建的可视化界面
"""

import os
import sys
import json
import shutil
import tempfile
import zipfile
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox, scrolledtext
    from tkinterdnd2 import TkinterDnD, DND_FILES
    HAS_DND = True
except ImportError:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox, scrolledtext
    HAS_DND = False

from convert_to_alpaca import AlpacaDataConverter


class AlpacaConverterGUI:
    """Alpaca数据转换器GUI"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("🦙 Alpaca数据转换工具")
        self.root.geometry("1200x800")
        self.root.minsize(900, 600)
        
        self.converter = None
        self.temp_dir = tempfile.mkdtemp()
        self.output_dir = os.path.join(self.temp_dir, "alpaca_output")
        self.current_data = []
        self.uploaded_files = []
        
        self.setup_styles()
        self.create_widgets()
        
    def setup_styles(self):
        """设置样式"""
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure('Title.TLabel', font=('Microsoft YaHei', 16, 'bold'))
        style.configure('Section.TLabel', font=('Microsoft YaHei', 11, 'bold'))
        style.configure('Info.TLabel', font=('Microsoft YaHei', 10))
        style.configure('Primary.TButton', font=('Microsoft YaHei', 10))
        style.configure('Success.TButton', font=('Microsoft YaHei', 10))
        
    def create_widgets(self):
        """创建界面组件"""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        title_label = ttk.Label(
            main_frame,
            text="🦙 Alpaca数据转换工具",
            style='Title.TLabel'
        )
        title_label.pack(pady=(0, 10))
        
        subtitle = ttk.Label(
            main_frame,
            text="将零散的图片和对话数据转换为可用于微调的Alpaca格式数据",
            style='Info.TLabel'
        )
        subtitle.pack(pady=(0, 15))
        
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        self.create_batch_tab(notebook)
        self.create_manual_tab(notebook)
        self.create_preview_tab(notebook)
        self.create_export_tab(notebook)
        
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.status_var = tk.StringVar(value="就绪")
        self.status_label = ttk.Label(
            status_frame,
            textvariable=self.status_var,
            style='Info.TLabel'
        )
        self.status_label.pack(side=tk.LEFT)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            status_frame,
            variable=self.progress_var,
            maximum=100,
            length=200
        )
        self.progress_bar.pack(side=tk.RIGHT)
        
    def create_batch_tab(self, notebook):
        """创建批量导入标签页"""
        frame = ttk.Frame(notebook, padding="15")
        notebook.add(frame, text="📁 批量导入")
        
        upload_section = ttk.LabelFrame(frame, text="上传文件", padding="10")
        upload_section.pack(fill=tk.X, pady=(0, 10))
        
        btn_frame = ttk.Frame(upload_section)
        btn_frame.pack(fill=tk.X)
        
        ttk.Button(
            btn_frame,
            text="📂 选择文件",
            command=self.select_files,
            style='Primary.TButton'
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(
            btn_frame,
            text="📦 选择ZIP压缩包",
            command=self.select_zip,
            style='Primary.TButton'
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(
            btn_frame,
            text="📁 选择文件夹",
            command=self.select_folder,
            style='Primary.TButton'
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(
            btn_frame,
            text="🗑️ 清空列表",
            command=self.clear_file_list
        ).pack(side=tk.LEFT)
        
        self.file_listbox = tk.Listbox(upload_section, height=6, selectmode=tk.EXTENDED)
        self.file_listbox.pack(fill=tk.X, pady=(10, 0))
        
        scrollbar = ttk.Scrollbar(upload_section, orient=tk.VERTICAL, command=self.file_listbox.yview)
        self.file_listbox.configure(yscrollcommand=scrollbar.set)
        
        process_section = ttk.LabelFrame(frame, text="处理设置", padding="10")
        process_section.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(process_section, text="图片默认问题模板:").pack(side=tk.LEFT)
        self.template_var = tk.StringVar(value="请描述这张图片的内容")
        ttk.Entry(process_section, textvariable=self.template_var, width=40).pack(side=tk.LEFT, padx=10)
        
        ttk.Button(
            process_section,
            text="🔄 开始处理",
            command=self.process_files,
            style='Success.TButton'
        ).pack(side=tk.RIGHT)
        
        result_section = ttk.LabelFrame(frame, text="处理结果", padding="10")
        result_section.pack(fill=tk.BOTH, expand=True)
        
        self.result_text = scrolledtext.ScrolledText(result_section, height=15, wrap=tk.WORD)
        self.result_text.pack(fill=tk.BOTH, expand=True)
        
    def create_manual_tab(self, notebook):
        """创建手动添加标签页"""
        frame = ttk.Frame(notebook, padding="15")
        notebook.add(frame, text="✏️ 手动添加")
        
        form_frame = ttk.Frame(frame)
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        left_frame = ttk.Frame(form_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        ttk.Label(left_frame, text="指令/问题 *", style='Section.TLabel').pack(anchor=tk.W)
        self.instruction_text = scrolledtext.ScrolledText(left_frame, height=4, wrap=tk.WORD)
        self.instruction_text.pack(fill=tk.X, pady=(5, 10))
        
        ttk.Label(left_frame, text="上下文输入（可选）", style='Section.TLabel').pack(anchor=tk.W)
        self.input_text = scrolledtext.ScrolledText(left_frame, height=3, wrap=tk.WORD)
        self.input_text.pack(fill=tk.X, pady=(5, 10))
        
        ttk.Label(left_frame, text="输出/回答 *", style='Section.TLabel').pack(anchor=tk.W)
        self.output_text = scrolledtext.ScrolledText(left_frame, height=6, wrap=tk.WORD)
        self.output_text.pack(fill=tk.X, pady=(5, 10))
        
        right_frame = ttk.Frame(form_frame, width=300)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y)
        right_frame.pack_propagate(False)
        
        ttk.Label(right_frame, text="图片（可选）", style='Section.TLabel').pack(anchor=tk.W)
        
        self.image_frame = ttk.LabelFrame(right_frame, text="图片预览", padding="5")
        self.image_frame.pack(fill=tk.X, pady=(5, 10))
        
        self.image_label = ttk.Label(self.image_frame, text="未选择图片")
        self.image_label.pack(pady=20)
        
        self.image_path_var = tk.StringVar()
        
        btn_frame = ttk.Frame(right_frame)
        btn_frame.pack(fill=tk.X)
        
        ttk.Button(
            btn_frame,
            text="📷 选择图片",
            command=self.select_image
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(
            btn_frame,
            text="🗑️ 清除",
            command=self.clear_image
        ).pack(side=tk.LEFT)
        
        ttk.Separator(right_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=15)
        
        ttk.Button(
            right_frame,
            text="➕ 添加数据",
            command=self.add_manual_entry,
            style='Success.TButton'
        ).pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(
            right_frame,
            text="🧹 清空表单",
            command=self.clear_form
        ).pack(fill=tk.X)
        
        self.manual_status = ttk.Label(right_frame, text="", wraplength=280)
        self.manual_status.pack(pady=10)
        
    def create_preview_tab(self, notebook):
        """创建数据预览标签页"""
        frame = ttk.Frame(notebook, padding="15")
        notebook.add(frame, text="👁️ 数据预览")
        
        toolbar = ttk.Frame(frame)
        toolbar.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(
            toolbar,
            text="🔄 刷新预览",
            command=self.refresh_preview
        ).pack(side=tk.LEFT)
        
        ttk.Button(
            toolbar,
            text="📊 统计信息",
            command=self.show_statistics
        ).pack(side=tk.LEFT, padx=(10, 0))
        
        self.preview_text = scrolledtext.ScrolledText(frame, height=30, wrap=tk.WORD)
        self.preview_text.pack(fill=tk.BOTH, expand=True)
        
    def create_export_tab(self, notebook):
        """创建导出标签页"""
        frame = ttk.Frame(notebook, padding="15")
        notebook.add(frame, text="📤 导出")
        
        format_section = ttk.LabelFrame(frame, text="导出格式", padding="15")
        format_section.pack(fill=tk.X, pady=(0, 15))
        
        self.format_var = tk.StringVar(value="json")
        
        formats = [
            ("Alpaca JSON", "json", "标准Alpaca格式，适用于大多数微调框架"),
            ("Alpaca JSONL", "jsonl", "每行一个JSON对象，适合大数据集"),
            ("LLaMA-Factory", "llama_factory", "包含dataset_info.json，可直接用于LLaMA-Factory")
        ]
        
        for text, value, desc in formats:
            radio_frame = ttk.Frame(format_section)
            radio_frame.pack(fill=tk.X, pady=3)
            
            ttk.Radiobutton(
                radio_frame,
                text=text,
                variable=self.format_var,
                value=value
            ).pack(side=tk.LEFT)
            
            ttk.Label(
                radio_frame,
                text=f"  - {desc}",
                style='Info.TLabel'
            ).pack(side=tk.LEFT)
        
        name_section = ttk.LabelFrame(frame, text="数据集设置", padding="15")
        name_section.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(name_section, text="数据集名称:").pack(side=tk.LEFT)
        self.dataset_name_var = tk.StringVar(value="my_dataset")
        ttk.Entry(name_section, textvariable=self.dataset_name_var, width=30).pack(side=tk.LEFT, padx=10)
        
        export_section = ttk.LabelFrame(frame, text="导出操作", padding="15")
        export_section.pack(fill=tk.X, pady=(0, 15))
        
        btn_frame = ttk.Frame(export_section)
        btn_frame.pack(fill=tk.X)
        
        ttk.Button(
            btn_frame,
            text="💾 导出文件",
            command=self.export_files,
            style='Success.TButton'
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(
            btn_frame,
            text="📦 导出并打包下载",
            command=self.export_and_package,
            style='Success.TButton'
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(
            btn_frame,
            text="🗑️ 清空所有数据",
            command=self.clear_all_data
        ).pack(side=tk.LEFT)
        
        self.export_log = scrolledtext.ScrolledText(frame, height=15, wrap=tk.WORD)
        self.export_log.pack(fill=tk.BOTH, expand=True)
        
    def select_files(self):
        """选择文件"""
        files = filedialog.askopenfilenames(
            title="选择文件",
            filetypes=[
                ("所有支持格式", "*.json *.jsonl *.txt *.log *.chat *.jpg *.jpeg *.png *.gif *.bmp *.webp *.zip"),
                ("JSON文件", "*.json"),
                ("JSONL文件", "*.jsonl"),
                ("文本文件", "*.txt *.log *.chat"),
                ("图片文件", "*.jpg *.jpeg *.png *.gif *.bmp *.webp"),
                ("ZIP压缩包", "*.zip"),
                ("所有文件", "*.*")
            ]
        )
        
        for file in files:
            if file not in self.uploaded_files:
                self.uploaded_files.append(file)
                self.file_listbox.insert(tk.END, os.path.basename(file))
        
        self.status_var.set(f"已选择 {len(self.uploaded_files)} 个文件")
        
    def select_zip(self):
        """选择ZIP文件"""
        file = filedialog.askopenfilename(
            title="选择ZIP压缩包",
            filetypes=[("ZIP文件", "*.zip"), ("所有文件", "*.*")]
        )
        
        if file and file not in self.uploaded_files:
            self.uploaded_files.append(file)
            self.file_listbox.insert(tk.END, f"[ZIP] {os.path.basename(file)}")
            self.status_var.set(f"已选择 {len(self.uploaded_files)} 个文件")
            
    def select_folder(self):
        """选择文件夹"""
        folder = filedialog.askdirectory(title="选择文件夹")
        
        if folder:
            count = 0
            for root, dirs, files in os.walk(folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    if file_path not in self.uploaded_files:
                        self.uploaded_files.append(file_path)
                        self.file_listbox.insert(tk.END, os.path.relpath(file_path, folder))
                        count += 1
            
            self.status_var.set(f"已添加 {count} 个文件")
            
    def clear_file_list(self):
        """清空文件列表"""
        self.uploaded_files.clear()
        self.file_listbox.delete(0, tk.END)
        self.status_var.set("文件列表已清空")
        
    def process_files(self):
        """处理文件"""
        if not self.uploaded_files:
            messagebox.showwarning("警告", "请先选择要处理的文件！")
            return
        
        self.status_var.set("正在处理...")
        self.progress_var.set(0)
        
        thread = threading.Thread(target=self._process_files_thread)
        thread.daemon = True
        thread.start()
        
    def _process_files_thread(self):
        """处理文件的线程"""
        try:
            self.converter = AlpacaDataConverter(output_dir=self.output_dir)
            
            stats = {
                "json": 0,
                "jsonl": 0,
                "images": 0,
                "chat": 0,
                "zip": 0,
                "errors": []
            }
            
            total = len(self.uploaded_files)
            
            for idx, file_path in enumerate(self.uploaded_files):
                progress = (idx + 1) / total * 100
                self.root.after(0, lambda p=progress: self.progress_var.set(p))
                self.root.after(0, lambda f=file_path: self.status_var.set(f"处理: {os.path.basename(f)}"))
                
                try:
                    ext = os.path.splitext(file_path)[1].lower()
                    
                    if ext == '.zip':
                        extract_dir = os.path.join(self.temp_dir, f"extract_{idx}")
                        os.makedirs(extract_dir, exist_ok=True)
                        
                        with zipfile.ZipFile(file_path, 'r') as zip_ref:
                            zip_ref.extractall(extract_dir)
                        
                        zip_stats = self.converter.merge_from_directory(extract_dir)
                        for key in stats:
                            if key in zip_stats:
                                stats[key] += zip_stats[key]
                        stats["zip"] += 1
                    
                    elif ext == '.json':
                        count = self.converter.from_conversation_json(file_path)
                        stats["json"] += count
                    
                    elif ext == '.jsonl':
                        count = self.converter.from_conversation_jsonl(file_path)
                        stats["jsonl"] += count
                    
                    elif ext in {'.txt', '.log', '.chat'}:
                        count = self.converter.from_chat_history(file_path)
                        stats["chat"] += count
                    
                    elif ext in {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}:
                        pass
                    
                except Exception as e:
                    stats["errors"].append(f"{os.path.basename(file_path)}: {str(e)}")
            
            image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
            image_dirs = set()
            
            for file_path in self.uploaded_files:
                ext = os.path.splitext(file_path)[1].lower()
                if ext in image_extensions:
                    image_dirs.add(os.path.dirname(file_path))
            
            for img_dir in image_dirs:
                try:
                    count = self.converter.from_image_folder(
                        img_dir,
                        instruction_template=self.template_var.get()
                    )
                    stats["images"] += count
                except Exception as e:
                    stats["errors"].append(f"图片目录: {str(e)}")
            
            self.current_data = self.converter.alpaca_data
            
            self.root.after(0, lambda: self._update_result_display(stats))
            self.root.after(0, lambda: self.progress_var.set(100))
            self.root.after(0, lambda: self.status_var.set("处理完成！"))
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("错误", f"处理失败: {str(e)}"))
            self.root.after(0, lambda: self.status_var.set("处理失败"))
            
    def _update_result_display(self, stats):
        """更新结果显示"""
        self.result_text.delete(1.0, tk.END)
        
        converter_stats = self.converter.get_statistics() if self.converter else {}
        
        result = f"""{'='*50}
处理结果摘要
{'='*50}

数据统计:
  - JSON数据: {stats.get('json', 0)} 条
  - JSONL数据: {stats.get('jsonl', 0)} 条
  - 图片数据: {stats.get('images', 0)} 条
  - 聊天记录: {stats.get('chat', 0)} 条
  - ZIP压缩包: {stats.get('zip', 0)} 个

数据集信息:
  - 总条目数: {converter_stats.get('total_entries', 0)}
  - 包含图片: {converter_stats.get('entries_with_images', 0)} 条
  - 包含上下文: {converter_stats.get('entries_with_input', 0)} 条
  - 平均指令长度: {converter_stats.get('average_instruction_length', 0)} 字符
  - 平均输出长度: {converter_stats.get('average_output_length', 0)} 字符
"""
        
        if stats.get('errors'):
            result += f"\n处理警告:\n"
            for err in stats['errors'][:10]:
                result += f"  - {err}\n"
            if len(stats['errors']) > 10:
                result += f"  ... 还有 {len(stats['errors']) - 10} 个错误\n"
        
        self.result_text.insert(tk.END, result)
        
    def select_image(self):
        """选择图片"""
        file = filedialog.askopenfilename(
            title="选择图片",
            filetypes=[
                ("图片文件", "*.jpg *.jpeg *.png *.gif *.bmp *.webp"),
                ("所有文件", "*.*")
            ]
        )
        
        if file:
            self.image_path_var.set(file)
            self.image_label.configure(text=os.path.basename(file))
            
    def clear_image(self):
        """清除图片"""
        self.image_path_var.set("")
        self.image_label.configure(text="未选择图片")
        
    def clear_form(self):
        """清空表单"""
        self.instruction_text.delete(1.0, tk.END)
        self.input_text.delete(1.0, tk.END)
        self.output_text.delete(1.0, tk.END)
        self.clear_image()
        
    def add_manual_entry(self):
        """手动添加数据"""
        instruction = self.instruction_text.get(1.0, tk.END).strip()
        output = self.output_text.get(1.0, tk.END).strip()
        input_text = self.input_text.get(1.0, tk.END).strip()
        image_path = self.image_path_var.get() or None
        
        if not instruction or not output:
            messagebox.showwarning("警告", "指令和输出不能为空！")
            return
        
        if not self.converter:
            self.converter = AlpacaDataConverter(output_dir=self.output_dir)
        
        self.converter.add_entry(
            instruction=instruction,
            output=output,
            input_text=input_text,
            image_path=image_path
        )
        
        self.current_data = self.converter.alpaca_data
        
        stats = self.converter.get_statistics()
        self.manual_status.configure(text=f"✅ 已添加！当前共 {stats['total_entries']} 条数据")
        
        self.clear_form()
        
    def refresh_preview(self):
        """刷新预览"""
        self.preview_text.delete(1.0, tk.END)
        
        if not self.current_data:
            self.preview_text.insert(tk.END, "暂无数据")
            return
        
        preview = f"数据预览 (共 {len(self.current_data)} 条)\n{'='*50}\n\n"
        
        for i, entry in enumerate(self.current_data[:20]):
            preview += f"【条目 {i + 1}】\n"
            preview += f"指令: {entry.get('instruction', '')[:200]}{'...' if len(entry.get('instruction', '')) > 200 else ''}\n"
            
            if entry.get('input'):
                preview += f"输入: {entry['input'][:100]}{'...' if len(entry['input']) > 100 else ''}\n"
            
            preview += f"输出: {entry.get('output', '')[:200]}{'...' if len(entry.get('output', '')) > 200 else ''}\n"
            
            if entry.get('image'):
                preview += f"图片: {entry['image']}\n"
            
            preview += "\n" + "-"*50 + "\n\n"
        
        if len(self.current_data) > 20:
            preview += f"\n... 还有 {len(self.current_data) - 20} 条数据"
        
        self.preview_text.insert(tk.END, preview)
        
    def show_statistics(self):
        """显示统计信息"""
        if not self.converter:
            messagebox.showinfo("统计", "暂无数据")
            return
        
        stats = self.converter.get_statistics()
        
        msg = f"""数据统计信息

总条目数: {stats['total_entries']}
包含图片: {stats['entries_with_images']}
包含上下文: {stats['entries_with_input']}
平均指令长度: {stats['average_instruction_length']} 字符
平均输出长度: {stats['average_output_length']} 字符"""
        
        messagebox.showinfo("统计信息", msg)
        
    def export_files(self):
        """导出文件"""
        if not self.converter or not self.current_data:
            messagebox.showwarning("警告", "没有数据可导出！")
            return
        
        export_format = self.format_var.get()
        dataset_name = self.dataset_name_var.get()
        
        save_dir = filedialog.askdirectory(title="选择保存目录")
        
        if not save_dir:
            return
        
        try:
            if export_format == "json":
                output_path = os.path.join(save_dir, f"{dataset_name}.json")
                self.converter.to_alpaca_json(output_path)
                
            elif export_format == "jsonl":
                output_path = os.path.join(save_dir, f"{dataset_name}.jsonl")
                self.converter.to_alpaca_jsonl(output_path)
                
            elif export_format == "llama_factory":
                self.converter.to_llama_factory_format(
                    dataset_name=dataset_name,
                    output_dir=save_dir
                )
            
            self.export_log.delete(1.0, tk.END)
            self.export_log.insert(tk.END, f"✅ 导出成功！\n\n保存位置: {save_dir}\n数据条数: {len(self.current_data)}\n格式: {export_format}")
            
            messagebox.showinfo("成功", f"导出成功！\n保存位置: {save_dir}")
            
        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {str(e)}")
            
    def export_and_package(self):
        """导出并打包"""
        if not self.converter or not self.current_data:
            messagebox.showwarning("警告", "没有数据可导出！")
            return
        
        export_format = self.format_var.get()
        dataset_name = self.dataset_name_var.get()
        
        save_path = filedialog.asksaveasfilename(
            title="保存压缩包",
            defaultextension=".zip",
            filetypes=[("ZIP压缩包", "*.zip")],
            initialfile=f"{dataset_name}.zip"
        )
        
        if not save_path:
            return
        
        try:
            if export_format == "json":
                self.converter.to_alpaca_json()
            elif export_format == "jsonl":
                self.converter.to_alpaca_jsonl()
            elif export_format == "llama_factory":
                self.converter.to_llama_factory_format(dataset_name=dataset_name)
            
            with zipfile.ZipFile(save_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(self.output_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, self.output_dir)
                        zipf.write(file_path, arcname)
            
            self.export_log.delete(1.0, tk.END)
            self.export_log.insert(tk.END, f"✅ 打包成功！\n\n保存位置: {save_path}\n数据条数: {len(self.current_data)}\n格式: {export_format}")
            
            messagebox.showinfo("成功", f"打包成功！\n保存位置: {save_path}")
            
        except Exception as e:
            messagebox.showerror("错误", f"打包失败: {str(e)}")
            
    def clear_all_data(self):
        """清空所有数据"""
        if messagebox.askyesno("确认", "确定要清空所有数据吗？"):
            if self.converter:
                self.converter.clear()
            self.current_data = []
            self.export_log.delete(1.0, tk.END)
            self.export_log.insert(tk.END, "数据已清空")
            self.status_var.set("数据已清空")


def main():
    """主函数"""
    root = tk.Tk()
    app = AlpacaConverterGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
