#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复路由位置问题 - 将企业级套件和记忆系统路由移到 if __name__ == '__main__': 之前
"""

# 读取原文件
with open('qwen3_web_final.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 找到 if __name__ == '__main__': 的位置
main_block_start = content.find("if __name__ == '__main__':")
if main_block_start == -1:
    print("❌ 未找到 if __name__ == '__main__': 块")
    exit(1)

# 找到主程序块的结束位置（即下一个非空行且不是缩进的行）
lines = content.split('\n')
main_start_line = None
for i, line in enumerate(lines):
    if "if __name__ == '__main__':" in line:
        main_start_line = i
        break

if main_start_line is None:
    print("❌ 未找到 if __name__ == '__main__': 行")
    exit(1)

# 找到主程序块的结束（app.run之后的空行）
main_end_line = None
for i in range(main_start_line + 1, len(lines)):
    line = lines[i]
    # 跳过空行和注释
    if line.strip() == '' or line.strip().startswith('#'):
        continue
    # 如果遇到非缩进的代码，说明主程序块结束
    if not line.startswith(' ') and not line.startswith('\t'):
        main_end_line = i
        break
    # 如果遇到 app.run，记录位置
    if 'app.run(' in line:
        # 继续找空行
        for j in range(i + 1, len(lines)):
            if lines[j].strip() == '':
                main_end_line = j + 1
                break
        break

if main_end_line is None:
    main_end_line = len(lines)

print(f"主程序块: 第 {main_start_line + 1} 行 到 第 {main_end_line} 行")

# 提取主程序块之前的内容
before_main = '\n'.join(lines[:main_start_line])

# 提取主程序块
main_block = '\n'.join(lines[main_start_line:main_end_line])

# 提取主程序块之后的内容（即需要移动的路由）
after_main = '\n'.join(lines[main_end_line:])

# 将路由移到主程序块之前
new_content = before_main + '\n' + after_main + '\n\n' + main_block

# 保存修复后的文件
with open('qwen3_web_final.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("✅ 路由位置修复完成")
print(f"原文件行数: {len(lines)}")
print(f"新文件行数: {len(new_content.split(chr(10)))}")
