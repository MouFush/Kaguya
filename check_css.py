FILE = r'c:\Users\林智涵\.conda\qwen3_web.py'

with open(FILE, 'r', encoding='utf-8') as f:
    c = f.read()

print('gradient-primary:', c.count('.gradient-primary'))
print('will-change:', c.count('will-change'))
print('contain:', c.count('contain:'))

idx = c.find('.gradient-primary')
if idx > 0:
    ln = c[:idx].count('\n') + 1
    print(f'gradient-primary at line: {ln}')
    print('Context:', c[idx-20:idx+80].replace('\n', '|'))
else:
    print('gradient-primary NOT FOUND - need to insert CSS')
    
    # Find the correct </style> in the HTML template
    # The HTML template's </style> should be after the last CSS rule
    # Look for the pattern: a CSS rule followed by </style>
    # The second </style> at line ~5417 is the correct one
    
    tag = '</style>'
    positions = []
    idx = 0
    while True:
        idx = c.find(tag, idx + 1)
        if idx < 0:
            break
        ln = c[:idx].count('\n') + 1
        before = c[max(0, idx - 200):idx]
        positions.append((ln, idx, before))
    
    print(f'\nFound {len(positions)} </style> tags:')
    for ln, pos, before in positions:
        has_css = any(kw in before for kw in ['scrollbar', 'animation', 'transition', 'border-radius'])
        print(f'  Line {ln}: has_css_context={has_css}')
    
    # Insert before the second </style> (the one in the HTML template)
    if len(positions) >= 2:
        target_ln, target_idx, _ = positions[1]  # Second </style>
        
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
        
        c = c[:target_idx] + css_code + c[target_idx:]
        print(f"\nInserted CSS at line {target_ln}")
        
        with open(FILE, 'w', encoding='utf-8') as f:
            f.write(c)
        print("Saved!")
