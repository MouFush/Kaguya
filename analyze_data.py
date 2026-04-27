import json

with open(r'D:\datasets-4J1opHXSFqck-alpaca-2026-03-25.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f'数据条数: {len(data)}')

total_chars = sum(len(d.get('instruction', '')) + len(d.get('output', '')) for d in data)
print(f'总字符数: {total_chars}')
print(f'平均每条字符数: {total_chars // len(data) if data else 0}')

avg_instruction = sum(len(d.get('instruction', '')) for d in data) / len(data) if data else 0
avg_output = sum(len(d.get('output', '')) for d in data) / len(data) if data else 0
print(f'平均指令长度: {avg_instruction:.1f}')
print(f'平均输出长度: {avg_output:.1f}')

total_tokens_estimate = total_chars // 2
print(f'预估Token数(中文约2字符/token): {total_tokens_estimate}')
