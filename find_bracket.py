# 读取诊断脚本
with open('diagnostic_script.js', 'r', encoding='utf-8') as f:
    content = f.read()

print("=" * 70)
print("查找花括号不平衡问题")
print("=" * 70)

lines = content.split('\n')
brace_count = 0
issues = []

for i, line in enumerate(lines, 1):
    # 计算这一行的花括号变化
    open_braces = line.count('{')
    close_braces = line.count('}')
    
    prev_count = brace_count
    brace_count += open_braces - close_braces
    
    # 如果括号计数变为负数，说明有问题
    if brace_count < 0 and prev_count >= 0:
        issues.append((i, line, brace_count))

print(f"\n最终花括号计数: {brace_count}")

if issues:
    print(f"\n发现 {len(issues)} 个问题位置:")
    for line_num, line, count in issues:
        print(f"\n第 {line_num} 行: 计数变为 {count}")
        print(f"  代码: {line[:100]}")
        
        # 显示上下文
        print(f"\n  上下文:")
        for j in range(max(0, line_num-3), min(len(lines), line_num+2)):
            marker = ">>> " if j == line_num - 1 else "    "
            print(f"  {marker}{j+1:4d}: {lines[j][:80]}")
else:
    print("\n未发现花括号变为负数的问题")

# 检查最后几行
print("\n" + "=" * 70)
print("最后 10 行代码:")
print("=" * 70)
for i, line in enumerate(lines[-10:], len(lines) - 9):
    print(f"{i+1:4d}: {line}")
