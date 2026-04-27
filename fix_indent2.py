FILE = r'c:\Users\林智涵\.conda\qwen3_web.py'

with open(FILE, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix all "with data_lock:" indentation issues
# Pattern: "with data_lock:\n        project_artifacts" should be "with data_lock:\n            project_artifacts"

import re

# Fix 1: project_artifacts.append after with data_lock:
old1 = '''with data_lock:
        project_artifacts.append(artifact)
        save_project_artifacts()'''
new1 = '''with data_lock:
            project_artifacts.append(artifact)
        save_project_artifacts()'''
if old1 in content:
    content = content.replace(old1, new1, 1)
    print("Fix 1: project_artifacts.append indentation")

# Fix 2: project_artifacts delete after with data_lock:
old2 = '''with data_lock:
            project_artifacts = [a for a in project_artifacts if a.get('id') != artifact_id]'''
new2 = '''with data_lock:
                project_artifacts = [a for a in project_artifacts if a.get('id') != artifact_id]'''
if old2 in content:
    content = content.replace(old2, new2, 1)
    print("Fix 2: project_artifacts delete indentation")

# Also check for other with data_lock: patterns that might be broken
# Find all occurrences and check
lines = content.split('\n')
fixes = 0
for i, line in enumerate(lines):
    if line.strip() == 'with data_lock:' and i + 1 < len(lines):
        next_line = lines[i + 1]
        # The next line should be more indented than "with data_lock:"
        with_indent = len(line) - len(line.lstrip())
        next_indent = len(next_line) - len(next_line.lstrip())
        if next_indent <= with_indent and next_line.strip():
            # Fix: add 4 more spaces
            lines[i + 1] = ' ' * (with_indent + 4) + next_line.lstrip()
            fixes += 1
            print(f"Fix at line {i+2}: indented '{next_line.strip()[:40]}...'")

if fixes > 0:
    content = '\n'.join(lines)
    print(f"Fixed {fixes} indentation issues")

with open(FILE, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done")
