FILE = r'c:\Users\林智涵\.conda\qwen3_web.py'

with open(FILE, 'r', encoding='utf-8') as f:
    content = f.read()

# Find all </style> positions
tag = '</style>'
idx = 0
count = 0
positions = []
while True:
    idx = content.find(tag, idx + 1)
    if idx < 0:
        break
    count += 1
    ln = content[:idx].count('\n') + 1
    before = content[max(0, idx - 80):idx].replace('\n', '|')
    positions.append((count, ln, idx, before))
    print(f'#{count} at line {ln}: ...{before[-60:]}')

# The correct </style> is the one inside the HTML template
# It should be after CSS rules and before <script> tags
# Look for the one that has CSS-like content before it
for pos_count, pos_ln, pos_idx, pos_before in positions:
    if 'scrollbar' in pos_before or 'transition' in pos_before or 'animation' in pos_before:
        print(f"\nLikely correct </style> at line {pos_ln} (#{pos_count})")
        
        # Insert CSS code before this </style>
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
        
        content = content[:pos_idx] + css_code + content[pos_idx:]
        print(f"Inserted CSS utility classes + GPU acceleration at line {pos_ln}")
        break

with open(FILE, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done!")
