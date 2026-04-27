import re

FILE = r'c:\Users\林智涵\.conda\qwen3_web.py'

with open(FILE, 'r', encoding='utf-8') as f:
    content = f.read()

print(f"原始行数: {len(content.split(chr(10)))}")

changes = []

# ============================================================
# 修复1: 找到并移除错误位置的GPU CSS代码
# ============================================================
print("[1] 修复: 移除错误位置的GPU CSS代码...")

# 错误插入的GPU CSS代码在Python代码中间
bad_gpu_css = '''
        .chat-area,.sidebar,.main-container { contain: layout style; }
        .messages-container { contain: layout style paint; }
        .message { will-change: transform; }
        .sidebar-tab,.chat-item,.quick-tool,.header-btn,.prompt-card,.project-item { will-change: transform; }
        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; }
        }'''

if bad_gpu_css in content:
    content = content.replace(bad_gpu_css, '', 1)
    changes.append("移除错误位置的GPU CSS代码")

# ============================================================
# 修复2: 找到并移除错误位置的CSS工具类代码
# ============================================================
print("[2] 修复: 移除错误位置的CSS工具类代码...")

bad_utility_css = '''
        .gradient-primary { background: linear-gradient(135deg, var(--primary), var(--secondary)); }
        .glass-card { background: linear-gradient(135deg, rgba(255,255,255,0.6), rgba(255,255,255,0.4)); }
        .dark .glass-card { background: linear-gradient(135deg, rgba(50,50,75,0.6), rgba(45,45,70,0.4)); }
        .flex-center { display: flex; align-items: center; justify-content: center; }
        .flex-between { display: flex; align-items: center; justify-content: space-between; }
        .text-ellipsis { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .gap-sm { gap: 8px; }
        .gap-md { gap: 12px; }
        .gap-lg { gap: 16px; }
        .p-sm { padding: 8px; }
        .p-md { padding: 12px; }
        .p-lg { padding: 16px; }
        .rounded { border-radius: 12px; }
        .rounded-lg { border-radius: 16px; }
        .border { border: 1px solid var(--border); }
        .shadow-sm { box-shadow: 0 2px 6px rgba(0,0,0,0.04); }
        .shadow-md { box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
        .font-sm { font-size: 12px; }
        .font-xs { font-size: 11px; }
        .font-xxs { font-size: 10px; }
        .text-muted { color: var(--text-muted); }
        .text-secondary { color: var(--text-secondary); }
        .text-primary { color: var(--text-primary); }
        .font-bold { font-weight: 600; }
        .font-bolder { font-weight: 700; }'''

if bad_utility_css in content:
    content = content.replace(bad_utility_css, '', 1)
    changes.append("移除错误位置的CSS工具类代码")

# ============================================================
# 修复3: 在HTML模板中正确的</style>位置插入CSS代码
# ============================================================
print("[3] 修复: 在正确位置插入CSS代码...")

# 找到HTML模板中的</style>标签
# HTML模板在Python的三引号字符串中，</style>应该在CSS区域末尾
# 我们需要找到正确的</style>位置 - 它应该在 .dark .quick-tool 之后

correct_style_end = ".dark .quick-tool { background: linear-gradient(135deg, rgba(50,50,75,0.9), rgba(45,45,70,0.7)); }"
if correct_style_end in content:
    # 找到这个位置后面的 </style>
    pos = content.find(correct_style_end)
    after_pos = content[pos + len(correct_style_end):]
    style_close_pos = after_pos.find("</style>")
    if style_close_pos > 0 and style_close_pos < 500:
        insert_pos = pos + len(correct_style_end) + style_close_pos
        
        css_code = '''
        .gradient-primary { background: linear-gradient(135deg, var(--primary), var(--secondary)); }
        .glass-card { background: linear-gradient(135deg, rgba(255,255,255,0.6), rgba(255,255,255,0.4)); }
        .dark .glass-card { background: linear-gradient(135deg, rgba(50,50,75,0.6), rgba(45,45,70,0.4)); }
        .flex-center { display: flex; align-items: center; justify-content: center; }
        .flex-between { display: flex; align-items: center; justify-content: space-between; }
        .text-ellipsis { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .gap-sm { gap: 8px; } .gap-md { gap: 12px; } .gap-lg { gap: 16px; }
        .p-sm { padding: 8px; } .p-md { padding: 12px; } .p-lg { padding: 16px; }
        .rounded { border-radius: 12px; } .rounded-lg { border-radius: 16px; }
        .border { border: 1px solid var(--border); }
        .shadow-sm { box-shadow: 0 2px 6px rgba(0,0,0,0.04); }
        .shadow-md { box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
        .font-sm { font-size: 12px; } .font-xs { font-size: 11px; } .font-xxs { font-size: 10px; }
        .text-muted { color: var(--text-muted); } .text-secondary { color: var(--text-secondary); }
        .text-primary { color: var(--text-primary); }
        .font-bold { font-weight: 600; } .font-bolder { font-weight: 700; }
        .chat-area,.sidebar,.main-container { contain: layout style; }
        .messages-container { contain: layout style paint; }
        .message { will-change: transform; }
        .sidebar-tab,.chat-item,.quick-tool,.header-btn,.prompt-card,.project-item { will-change: transform; }
        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; }
        }'''
        
        content = content[:insert_pos] + css_code + content[insert_pos:]
        changes.append("在正确位置(HTML模板</style>前)插入CSS工具类+GPU加速代码")

# ============================================================
# 修复4: 检查并修复Python代码中被破坏的正则表达式
# ============================================================
print("[4] 修复: 检查正则表达式完整性...")

# 检查 for pattern in 那一行是否完整
broken_line = "for pattern in [r'<script[^>]*>.*?</script>', r'<style[^>]*>.*?"
if broken_line in content:
    # 找到并修复
    old_broken = "for pattern in [r'<script[^>]*>.*?</script>', r'<style[^>]*>.*?"
    new_fixed = "for pattern in [r'<script[^>]*>.*?</script>', r'<style[^>]*>.*?</style>',"
    content = content.replace(old_broken, new_fixed, 1)
    changes.append("修复被截断的正则表达式")

# ============================================================
# 保存文件
# ============================================================
new_lines = len(content.split('\n'))
print(f"\n修复后行数: {new_lines}")
print(f"行数变化: {new_lines - len(content.split(chr(10)))}")

with open(FILE, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"\nDone! {FILE}")
print(f"\nTotal {len(changes)} fixes:")
for i, c in enumerate(changes, 1):
    print(f"  {i}. {c}")
