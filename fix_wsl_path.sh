#!/bin/bash

echo "============================================================"
echo "修复 WSL 中的数据路径"
echo "============================================================"

FILE_PATH="/mnt/c/Users/林智涵/LLaMA-Factory/src/llamafactory/webui/common.py"

echo ""
echo "当前路径配置:"
grep "DEFAULT_DATA_DIR" "$FILE_PATH"

echo ""
echo "正在修改为 WSL 兼容路径..."

sed -i 's|DEFAULT_DATA_DIR = r"C:\\Users\\林智涵\\LLaMA-Factory\\data"|DEFAULT_DATA_DIR = "/mnt/c/Users/林智涵/LLaMA-Factory/data"|g' "$FILE_PATH"

echo ""
echo "修改后的路径配置:"
grep "DEFAULT_DATA_DIR" "$FILE_PATH"

echo ""
echo "============================================================"
echo "修改完成!"
echo "============================================================"
echo ""
echo "请重启 LLaMA-Factory WebUI"
