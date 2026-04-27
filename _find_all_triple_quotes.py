with open(r'c:\Users\林智涵\.conda\qwen3_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

start = content.find('AGENT_IDE_HTML = r"""')
if start == -1:
    print('ERROR: AGENT_IDE_HTML not found!')
    exit(1)

# Find ALL """ occurrences after start (not just standalone ones)
search_from = start + 20
pos = search_from
count = 0
locations = []

while True:
    pos = content.find('"""', pos)
    if pos == -1 or pos > start + 2000000:  # Safety limit
        break
    count += 1
    
    # Get line number and context
    line_num = content[:pos].count('\n') + 1
    line_start = content.rfind('\n', 0, pos) + 1
    line_end = content.find('\n', pos)
    if line_end == -1:
        line_end = len(content)
    
    locations.append((pos, line_num, content[line_start:line_end].strip()[:80]))
    pos += 3  # Skip past this """

print('Found %d occurrences of triple-quote in AGENT_IDE_HTML area:' % count)
for i, (pos, line_num, ctx) in enumerate(locations):
    print('  #%d at line %d (pos %d): %s' % (i+1, line_num, pos, repr(ctx)))

# The FIRST occurrence is the problem!
if len(locations) > 0:
    print('\n*** The first occurrence at line %d truncates the string! ***' % locations[0][1])
