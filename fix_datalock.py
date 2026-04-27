FILE = r'c:\Users\林智涵\.conda\qwen3_web.py'

with open(FILE, 'r', encoding='utf-8') as f:
    content = f.read()

changes = []

# Fix 1: normalized_with data_lock -> normalized_ with data_lock
# The script incorrectly inserted "with data_lock:" into variable names
bad_patterns = [
    'normalized_with data_lock:\n            release_plans.append(item)',
    'normalized_with data_lock:\n            ops_campaigns.append(item)',
    'normalized_with data_lock:\n            alert_rules.append(item)',
    'normalized_with data_lock:\n            ab_experiments.append(item)',
    'normalized_with data_lock:\n            integrations.append(item)',
    'normalized_with data_lock:\n            project_milestones.append(item)',
    'normalized_with data_lock:\n            project_risks.append(item)',
]

# Find all broken patterns
import re
# Pattern: <word>_with data_lock:
broken = re.findall(r'(\w+)_with data_lock:', content)
print(f"Found {len(broken)} broken patterns: {broken}")

# Fix each broken pattern
for match in broken:
    old = f'{match}_with data_lock:'
    new = f'{match}_'
    content = content.replace(old, new)
    changes.append(f"Fix broken variable name: {match}_with data_lock: -> {match}_")

# Now find all the incorrectly inserted "with data_lock:" lines in initialization code
# These are in the normalize functions which run at startup (single-threaded), not in request handlers
# They don't actually need locks. Let's remove the incorrectly placed ones.

# Check for any remaining "with data_lock:" in initialization code
lines = content.split('\n')
fixes = 0
for i, line in enumerate(lines):
    stripped = line.strip()
    if stripped == 'with data_lock:':
        # Check if this is in a function that handles requests or in initialization code
        # Look at the surrounding context
        prev_lines = '\n'.join(lines[max(0, i-5):i])
        next_line = lines[i+1].strip() if i+1 < len(lines) else ''
        
        # If next line contains .append in initialization code (like normalized_ lists), remove the lock
        if 'normalized_' in next_line or ('append(item)' in next_line and 'def ' not in prev_lines):
            # This is initialization code, remove the with data_lock
            lines[i] = ''  # Remove the "with data_lock:" line
            # Also fix indentation of next line (remove 12 spaces -> original indentation)
            if i+1 < len(lines) and lines[i+1].startswith(' ' * 12):
                lines[i+1] = lines[i+1][12:]  # Remove extra indentation
            fixes += 1

if fixes > 0:
    content = '\n'.join(lines)
    changes.append(f"Removed {fixes} incorrectly placed with data_lock: from initialization code")

# Also check for any other "with data_lock:" that might be broken
# The correct pattern should be in request handler functions only
# Let's verify all remaining "with data_lock:" are correct
remaining = content.count('with data_lock:')
print(f"Remaining 'with data_lock:' occurrences: {remaining}")

with open(FILE, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"\nDone! {len(changes)} fixes:")
for i, c in enumerate(changes, 1):
    print(f"  {i}. {c}")
