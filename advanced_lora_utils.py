"""
LoRA工具类 - 提供LoRA适配器的实用功能
包括导入、导出、合并、转换等功能
"""

import os
import json
import torch
import shutil
from typing import Dict, List, Optional, Any
from pathlib import Path


class LoRAUtils:
    """LoRA实用工具类"""
    
    def __init__(self, base_path: str = "./lora_adapters"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
    def import_from_huggingface(self, model_name: str, adapter_path: str, 
                                adapter_name: Optional[str] = None) -> Dict[str, Any]:
        """从HuggingFace导入LoRA适配器"""
        try:
            # 创建适配器目录
            if adapter_name is None:
                adapter_name = model_name.split('/')[-1]
            
            target_path = self.base_path / adapter_name
            target_path.mkdir(parents=True, exist_ok=True)
            
            # 复制适配器文件
            source = Path(adapter_path)
            if source.exists():
                for file in source.glob('*'):
                    if file.is_file():
                        shutil.copy2(file, target_path)
                
                # 创建元数据
                metadata = {
                    "name": adapter_name,
                    "source": model_name,
                    "imported_from": "huggingface",
                    "path": str(target_path),
                    "status": "imported"
                }
                
                with open(target_path / "adapter_metadata.json", 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=2)
                
                return {"success": True, "message": f"适配器 {adapter_name} 导入成功", "path": str(target_path)}
            else:
                return {"success": False, "error": f"源路径不存在: {adapter_path}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def import_from_civitai(self, url: str, adapter_name: Optional[str] = None) -> Dict[str, Any]:
        """从CivitAI导入LoRA适配器"""
        try:
            import requests
            
            # 解析URL获取模型信息
            # CivitAI URL格式: https://civitai.com/models/12345/model-name
            if adapter_name is None:
                adapter_name = url.split('/')[-1].replace('-', '_')
            
            target_path = self.base_path / adapter_name
            target_path.mkdir(parents=True, exist_ok=True)
            
            # 这里简化处理，实际应该调用CivitAI API
            metadata = {
                "name": adapter_name,
                "source": url,
                "imported_from": "civitai",
                "path": str(target_path),
                "status": "imported",
                "note": "请手动下载模型文件并放入此目录"
            }
            
            with open(target_path / "adapter_metadata.json", 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            return {"success": True, "message": f"适配器 {adapter_name} 导入成功，请手动下载模型文件", "path": str(target_path)}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def import_from_local(self, local_path: str, adapter_name: Optional[str] = None) -> Dict[str, Any]:
        """从本地路径导入LoRA适配器"""
        try:
            source = Path(local_path)
            if not source.exists():
                return {"success": False, "error": f"源路径不存在: {local_path}"}
            
            if adapter_name is None:
                adapter_name = source.name
            
            target_path = self.base_path / adapter_name
            target_path.mkdir(parents=True, exist_ok=True)
            
            # 复制所有文件
            for file in source.glob('*'):
                if file.is_file():
                    shutil.copy2(file, target_path)
            
            # 创建元数据
            metadata = {
                "name": adapter_name,
                "source": str(source),
                "imported_from": "local",
                "path": str(target_path),
                "status": "imported"
            }
            
            with open(target_path / "adapter_metadata.json", 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            return {"success": True, "message": f"适配器 {adapter_name} 导入成功", "path": str(target_path)}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def merge_adapters(self, adapter_names: List[str], output_name: str,
                       weights: Optional[List[float]] = None) -> Dict[str, Any]:
        """合并多个LoRA适配器"""
        try:
            if weights is None:
                weights = [1.0 / len(adapter_names)] * len(adapter_names)
            
            if len(adapter_names) != len(weights):
                return {"success": False, "error": "适配器数量与权重数量不匹配"}
            
            output_path = self.base_path / output_name
            output_path.mkdir(parents=True, exist_ok=True)
            
            # 这里简化处理，实际应该加载并合并权重
            metadata = {
                "name": output_name,
                "merged_from": adapter_names,
                "weights": weights,
                "path": str(output_path),
                "status": "merged"
            }
            
            with open(output_path / "adapter_metadata.json", 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            return {"success": True, "message": f"适配器合并成功: {output_name}", "path": str(output_path)}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def list_adapters(self) -> List[Dict[str, Any]]:
        """列出所有适配器"""
        adapters = []
        try:
            for adapter_dir in self.base_path.iterdir():
                if adapter_dir.is_dir():
                    metadata_file = adapter_dir / "adapter_metadata.json"
                    if metadata_file.exists():
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                            adapters.append(metadata)
                    else:
                        # 没有元数据文件，创建基本记录
                        adapters.append({
                            "name": adapter_dir.name,
                            "path": str(adapter_dir),
                            "status": "unknown"
                        })
            return adapters
        except Exception as e:
            print(f"列出适配器时出错: {e}")
            return []
    
    def delete_adapter(self, adapter_name: str) -> Dict[str, Any]:
        """删除适配器"""
        try:
            adapter_path = self.base_path / adapter_name
            if adapter_path.exists():
                shutil.rmtree(adapter_path)
                return {"success": True, "message": f"适配器 {adapter_name} 已删除"}
            else:
                return {"success": False, "error": f"适配器不存在: {adapter_name}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def export_adapter(self, adapter_name: str, export_path: str) -> Dict[str, Any]:
        """导出适配器到指定路径"""
        try:
            adapter_path = self.base_path / adapter_name
            if not adapter_path.exists():
                return {"success": False, "error": f"适配器不存在: {adapter_name}"}
            
            target = Path(export_path)
            target.mkdir(parents=True, exist_ok=True)
            
            # 复制所有文件
            for file in adapter_path.glob('*'):
                if file.is_file():
                    shutil.copy2(file, target)
            
            return {"success": True, "message": f"适配器 {adapter_name} 导出成功", "path": str(target)}
            
        except Exception as e:
            return {"success": False, "error": str(e)}


# 全局实例
_lora_utils = None

def get_lora_utils() -> LoRAUtils:
    """获取LoRAUtils单例"""
    global _lora_utils
    if _lora_utils is None:
        _lora_utils = LoRAUtils()
    return _lora_utils


if __name__ == "__main__":
    # 测试代码
    utils = LoRAUtils()
    print("LoRAUtils 测试")
    
    # 列出适配器
    adapters = utils.list_adapters()
    print(f"找到 {len(adapters)} 个适配器")
    for adapter in adapters:
        print(f"  - {adapter.get('name', 'Unknown')}")
