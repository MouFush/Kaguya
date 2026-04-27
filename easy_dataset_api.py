"""
Easy Dataset 自动化数据处理脚本
使用urllib发送请求
"""

import urllib.request
import urllib.error
import json
import time
import os
from pathlib import Path

BASE_URL = "http://localhost:1717"
PROJECT_ID = "4J1opHXSFqck"

def send_request(endpoint, method="GET", data=None):
    """发送HTTP请求"""
    url = f"{BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    
    if data:
        data = json.dumps(data).encode('utf-8')
    
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        print(f"HTTP错误: {e.code} - {e.reason}")
        try:
            error_body = e.read().decode('utf-8')
            print(f"错误详情: {error_body}")
            return json.loads(error_body)
        except:
            return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}

def get_datasets():
    """获取数据集列表"""
    return send_request(f"/api/projects/{PROJECT_ID}/datasets")

def import_dataset(data, name="imported_data"):
    """导入数据集"""
    return send_request(f"/api/projects/{PROJECT_ID}/datasets/import", "POST", {
        "name": name,
        "data": data
    })

def get_dataset(dataset_id):
    """获取数据集详情"""
    return send_request(f"/api/projects/{PROJECT_ID}/datasets/{dataset_id}")

def distill_dataset(dataset_id, model_config=None):
    """蒸馏数据集"""
    if model_config is None:
        model_config = {
            "model": "qwen",
            "temperature": 0.7
        }
    return send_request(f"/api/projects/{PROJECT_ID}/datasets/{dataset_id}/distill", "POST", model_config)

def export_dataset(dataset_id, format="alpaca"):
    """导出数据集"""
    return send_request(f"/api/projects/{PROJECT_ID}/datasets/{dataset_id}/export?format={format}")

def delete_dataset(dataset_id):
    """删除数据集"""
    return send_request(f"/api/projects/{PROJECT_ID}/datasets/{dataset_id}", "DELETE")

def main():
    print("=" * 60)
    print("Easy Dataset 自动化数据处理")
    print("=" * 60)
    
    # 1. 获取当前数据集
    print("\n[步骤1] 获取当前数据集...")
    result = get_datasets()
    print(f"结果: {json.dumps(result, ensure_ascii=False, indent=2)[:500]}")
    
    # 2. 导入批次数据
    batch_files = [
        r"D:\mira_easy_dataset\batch_1.json",
    ]
    
    for batch_file in batch_files:
        if not os.path.exists(batch_file):
            print(f"文件不存在: {batch_file}")
            continue
        
        print(f"\n[步骤2] 导入数据: {batch_file}")
        
        with open(batch_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"数据条数: {len(data)}")
        
        result = import_dataset(data, Path(batch_file).stem)
        print(f"导入结果: {json.dumps(result, ensure_ascii=False, indent=2)[:500]}")

if __name__ == "__main__":
    main()
