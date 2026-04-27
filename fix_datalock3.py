FILE = r'c:\Users\林智涵\.conda\qwen3_web.py'

with open(FILE, 'r', encoding='utf-8') as f:
    content = f.read()

changes = []

# Fix all remaining "with data_lock:" issues that broke the code
# The problem: the optimization script inserted "with data_lock:" before .append() calls
# inside try blocks in route handlers, but this breaks the try/except structure

# Strategy: Find all incorrectly placed "with data_lock:" and remove them
# The correct approach is to NOT use "with data_lock:" inside try blocks
# Instead, we should just add the lock around the critical section

# Let's find all remaining broken patterns
import re

# Pattern: empty line followed by "listname.append(item)" at wrong indentation
# This happens when "with data_lock:\n" was removed but the .append line kept extra indentation

# Fix 1: project_milestones.append at wrong indentation (line 15920)
# The "with data_lock:" was removed but the append kept the extra indentation
# We need to find these and fix the indentation

lines = content.split('\n')
fixes = 0

for i, line in enumerate(lines):
    stripped = line.strip()
    
    # Check for .append(item) at wrong indentation (should be inside try block)
    if stripped.endswith('.append(item)') and line.startswith('project_') or \
       stripped.endswith('.append(item)') and line.startswith('ops_') or \
       stripped.endswith('.append(item)') and line.startswith('release_') or \
       stripped.endswith('.append(item)') and line.startswith('alert_') or \
       stripped.endswith('.append(item)') and line.startswith('ab_') or \
       stripped.endswith('.append(item)') and line.startswith('integrations'):
        # Check if this line has no leading spaces (wrong indentation)
        if not line.startswith(' '):
            # Find the correct indentation from context
            # Look at the previous non-empty line
            for j in range(i-1, max(0, i-10), -1):
                prev = lines[j]
                if prev.strip() and prev.startswith(' '):
                    indent = len(prev) - len(prev.lstrip())
                    lines[i] = ' ' * indent + stripped
                    fixes += 1
                    print(f"Fixed indent at line {i+1}: {stripped[:50]}")
                    break

# Also find and fix any remaining "with data_lock:" that are incorrectly placed
# inside try blocks (they should be removed since they break the try/except structure)
for i, line in enumerate(lines):
    stripped = line.strip()
    if stripped == 'with data_lock:':
        # Check if we're inside a try block by looking at surrounding code
        context = '\n'.join(lines[max(0,i-10):i])
        if 'try:' in context:
            # This is inside a try block - the "with data_lock:" breaks the structure
            # Remove it and fix the indentation of the next line
            lines[i] = ''
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                # Remove extra indentation (4 spaces from "with data_lock:")
                if next_line.startswith(' ' * 12):
                    lines[i + 1] = next_line[4:]
            fixes += 1
            print(f"Removed 'with data_lock:' inside try block at line {i+1}")

if fixes > 0:
    content = '\n'.join(lines)
    changes.append(f"Fixed {fixes} indentation/structure issues from data_lock insertion")

with open(FILE, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"\nDone! {len(changes)} fixes:")
for i, c in enumerate(changes, 1):
    print(f"  {i}. {c}")
