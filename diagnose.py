"""诊断脚本"""
import torch
import json

# 加载分词器
with open(r'c:\Users\林智涵\.conda\checkpoints\tokenizer.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

vocab = data['vocab']
idx_to_token = {int(k): v for k, v in data['idx_to_token'].items()}

print('词汇表大小:', len(vocab))
print('\n前30个词汇:')
for i in range(min(30, len(idx_to_token))):
    print(f'  {i}: {idx_to_token.get(i, "N/A")}')

print('\n测试编码 "你好":')
words = '你好'.split()
print(f'  分词结果: {words}')
for w in words:
    print(f'  "{w}" -> {vocab.get(w, "<unk>")}')

print('\n测试编码 "hello":')
print(f'  "hello" -> {vocab.get("hello", "<unk>")}')

# 检查是否有中文词汇
chinese_words = [w for w in vocab.keys() if any('\u4e00' <= c <= '\u9fff' for c in w)]
print(f'\n中文词汇数量: {len(chinese_words)}')
if chinese_words:
    print(f'中文词汇示例: {chinese_words[:20]}')
