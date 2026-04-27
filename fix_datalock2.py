FILE = r'c:\Users\林智涵\.conda\qwen3_web.py'

with open(FILE, 'r', encoding='utf-8') as f:
    content = f.read()

changes = []

# Fix all broken patterns from the data_lock insertion
# Pattern 1: "normalized_" on its own line (remnant of "normalized_release_plans" etc.)
# Pattern 2: Wrong indentation on .append(item) lines

# Find all "normalized_" standalone lines
import re

# Replace broken patterns
broken = [
    # release_plans
    ('        normalized_\n            release_plans.append(item)', '        normalized_release_plans.append(item)'),
    # ops_campaigns
    ('        normalized_\n            ops_campaigns.append(item)', '        normalized_ops_campaigns.append(item)'),
    # alert_rules
    ('        normalized_\n            alert_rules.append(item)', '        normalized_alert_rules.append(item)'),
    # ab_experiments
    ('        normalized_\n            ab_experiments.append(item)', '        normalized_ab_experiments.append(item)'),
    # integrations
    ('        normalized_\n            integrations.append(item)', '        normalized_integrations.append(item)'),
    # project_milestones
    ('        normalized_\n            project_milestones.append(item)', '        normalized_project_milestones.append(item)'),
    # project_risks
    ('        normalized_\n            project_risks.append(item)', '        normalized_project_risks.append(item)'),
]

for old, new in broken:
    if old in content:
        content = content.replace(old, new, 1)
        changes.append(f"Fix: {new.strip()[:50]}")

# Also check for any other broken lines
# Look for lines that are just "normalized_" without the variable name
lines = content.split('\n')
for i, line in enumerate(lines):
    stripped = line.strip()
    if stripped == 'normalized_':
        # This is broken, check next line
        if i + 1 < len(lines):
            next_stripped = lines[i + 1].strip()
            if '.append(' in next_stripped:
                # Merge the two lines
                var_name = next_stripped.split('.')[0]
                append_part = next_stripped[next_stripped.index('.'):]
                indent = len(line) - len(line.lstrip())
                lines[i] = ' ' * indent + var_name + append_part
                lines[i + 1] = ''
                changes.append(f"Fix merged line at {i+1}: {var_name}.append(...)")

if changes:
    content = '\n'.join(lines)

with open(FILE, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"Done! {len(changes)} fixes:")
for i, c in enumerate(changes, 1):
    print(f"  {i}. {c}")
