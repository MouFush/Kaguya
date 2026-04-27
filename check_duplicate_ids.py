import re

with open(r'c:\Users\林智涵\.conda\qwen3_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 找出所有 id 属性
id_pattern = r'id="([^"]+)"'
ids = re.findall(id_pattern, content)

# 统计重复的 ID
from collections import Counter
id_counts = Counter(ids)

print('=' * 60)
print('重复的 ID 检查')
print('=' * 60)

duplicates = {id: count for id, count in id_counts.items() if count > 1}
if duplicates:
    print(f'\n发现 {len(duplicates)} 个重复的 ID:\n')
    for id_name, count in sorted(duplicates.items(), key=lambda x: -x[1]):
        print(f'  "{id_name}" 出现 {count} 次')
        
        # 找出重复 ID 的行号
        for i, line in enumerate(content.split('\n'), 1):
            if f'id="{id_name}"' in line:
                print(f'    行 {i}: {line.strip()[:80]}...')
else:
    print('\n✅ 没有发现重复的 ID')

print('\n' + '=' * 60)
