import re

FILE = r'c:\Users\林智涵\.conda\qwen3_web.py'

with open(FILE, 'r', encoding='utf-8') as f:
    content = f.read()

# Extract JavaScript from <script> tags
scripts = re.findall(r'<script>(.*?)</script>', content, re.DOTALL)
if scripts:
    js_code = scripts[-1]  # Main script block
    with open(r'c:\Users\林智涵\.conda\temp_check.js', 'w', encoding='utf-8') as f:
        f.write(js_code)
    print(f"Extracted JS: {len(js_code)} chars, {js_code.count(chr(10))} lines")
    print("Saved to temp_check.js for syntax checking")
else:
    print("No script tags found")

# Also count key optimization markers
markers = {
    'debounce': 'function debounce(',
    'throttle': 'function throttle(',
    'DOM cache $()': 'function $(id)',
    'escapeHtml': 'function escapeHtml(',
    'createModal': 'function createModal(',
    'crudUpdate': 'function crudUpdate(',
    'crudDelete': 'function crudDelete(',
    'renderKpiCards': 'function renderKpiCards(',
    'saveToLS': 'function saveToLS(',
    'debouncedSaveLS': 'function debouncedSaveLS(',
    'data_lock': 'data_lock',
    '_cached_index_html': '_cached_index_html',
    '/project/batch': '/project/batch',
    'X-Accel-Buffering': 'X-Accel-Buffering',
    'gradient-primary': '.gradient-primary',
    'will-change': 'will-change',
    'contain:': 'contain:',
    'prefers-reduced-motion': 'prefers-reduced-motion',
    'X-Content-Type-Options': 'X-Content-Type-Options',
}

print("\n=== Optimization Markers ===")
for name, marker in markers.items():
    count = content.count(marker)
    status = "OK" if count > 0 else "MISSING"
    print(f"  {status:7} {name}: {count} occurrences")

# Count total lines
total_lines = content.count('\n') + 1
print(f"\nTotal lines: {total_lines}")
print(f"Original was: 17169 lines")
print(f"Change: {total_lines - 17169:+d} lines")
