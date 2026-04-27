import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

from modelscope import snapshot_download

print("开始下载 Qwen3.5-9B 模型...")
print("模型大小约 18GB，请耐心等待...")

model_dir = snapshot_download(
    'Qwen/Qwen3.5-9B',
    cache_dir=r'C:\Users\林智涵\.cache\modelscope\hub'
)

print(f"\n模型下载完成！")
print(f"模型路径: {model_dir}")
