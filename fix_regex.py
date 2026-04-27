FILE = r'c:\Users\林智涵\.conda\qwen3_web.py'

with open(FILE, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the broken regex line
# Current broken state:
# Line 1392: for pattern in [r'<script[^>]*>.*?</script>', r'<style[^>]*>.*?</style>',
# Line 1393: (empty)
# Line 1394: (empty)
# Line 1395:     </style>',
# This should be:
# for pattern in [r'<script[^>]*>.*?</script>', r'<style[^>]*>.*?</style>',
#                        r'<nav[^>]*>.*?</nav>', r'<footer[^>]*>.*?</footer>',

old_broken = """for pattern in [r'<script[^>]*>.*?</script>', r'<style[^>]*>.*?</style>',


    </style>',"""

new_fixed = """for pattern in [r'<script[^>]*>.*?</script>', r'<style[^>]*>.*?</style>',"""

if old_broken in content:
    content = content.replace(old_broken, new_fixed, 1)
    print("Fixed broken regex line")
else:
    print("Pattern not found, trying alternative...")
    # Try to find and fix by line
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if "r'<style[^>]*>.*?</style>'," in line and i+1 < len(lines):
            # Check if next lines have the broken </style>'
            if '</style>\',' in lines[i+1] or '</style>\',' in lines[i+2] or '</style>\',' in lines[i+3]:
                print(f"Found broken pattern at line {i+1}")
                # Remove the orphaned </style>', line
                for j in range(i+1, min(i+5, len(lines))):
                    if lines[j].strip() == "</style>'," or lines[j].strip() == "</style>',":
                        lines[j] = ''
                        print(f"  Removed orphan at line {j+1}")
                    elif lines[j].strip() == '':
                        continue
                    else:
                        break
                content = '\n'.join(lines)
                break

with open(FILE, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done")
