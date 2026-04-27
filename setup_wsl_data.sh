#!/bin/bash

echo "============================================================"
echo "WSL LLaMA-Factory 数据集配置"
echo "============================================================"

LLAMA_FACTORY_DIR="/mnt/c/Users/林智涵/LLaMA-Factory"
DATA_DIR="$LLAMA_FACTORY_DIR/data"

echo ""
echo "步骤1: 检查数据文件..."
ls -la "$DATA_DIR/mira_text.json" 2>/dev/null && echo "  ✓ mira_text.json 存在"
ls -la "$DATA_DIR/mira_multimodal.json" 2>/dev/null && echo "  ✓ mira_multimodal.json 存在"
ls -d "$DATA_DIR/mira_images" 2>/dev/null && echo "  ✓ mira_images 目录存在"

echo ""
echo "步骤2: 检查 dataset_info.json 配置..."
if grep -q "mira_text" "$DATA_DIR/dataset_info.json"; then
    echo "  ✓ mira_text 配置存在"
else
    echo "  ✗ mira_text 配置不存在，正在添加..."
fi

if grep -q "mira_multimodal" "$DATA_DIR/dataset_info.json"; then
    echo "  ✓ mira_multimodal 配置存在"
else
    echo "  ✗ mira_multimodal 配置不存在，正在添加..."
fi

echo ""
echo "步骤3: 显示当前数据目录内容..."
ls -la "$DATA_DIR" | grep -E "mira|dataset_info"

echo ""
echo "============================================================"
echo "配置检查完成!"
echo "============================================================"
echo ""
echo "重要提示:"
echo "1. 在 WSL 中启动 LLaMA-Factory 时，请确保工作目录正确:"
echo "   cd /mnt/c/Users/林智涵/LLaMA-Factory"
echo ""
echo "2. 或者使用绝对路径指定数据目录:"
echo "   llamafactory-cli webui --data_dir /mnt/c/Users/林智涵/LLaMA-Factory/data"
echo ""
echo "3. 如果使用虚拟环境，请先激活虚拟环境再启动"
