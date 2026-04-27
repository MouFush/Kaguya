import requests, os, json

base = 'http://127.0.0.1:5000'

# Test 1: Import files
print('=== Test 1: Import Files ===')
test_path = os.path.expanduser('~')
r = requests.post(f'{base}/agent/import-files', json={
    'device_id': 'test_device_import',
    'paths': [test_path]
}, timeout=10)
print(f'Status: {r.status_code}')
d = r.json()
print(f'Imported: {len(d.get("imported", []))}')
print(f'Errors: {d.get("errors", [])}')
print(f'Workspace: {d.get("workspace", "")}')

# Test 2: Browse dirs
print('\n=== Test 2: Browse Dirs ===')
r = requests.post(f'{base}/agent/browsable-dirs', json={
    'path': test_path
}, timeout=10)
print(f'Status: {r.status_code}')
d = r.json()
print(f'Path: {d.get("path", "")}')
print(f'Entries: {len(d.get("entries", []))}')
if d.get('entries'):
    for e in d['entries'][:5]:
        print(f'  {"[DIR]" if e["is_dir"] else "[FILE]"} {e["name"]}')

# Test 3: Import env
print('\n=== Test 3: Import Env ===')
r = requests.post(f'{base}/agent/import-env', json={
    'device_id': 'test_device_import'
}, timeout=30)
print(f'Status: {r.status_code}')
d = r.json()
print(f'Success: {d.get("success")}')
print(f'Python: {d.get("python_version", "")}')
print(f'Packages: {d.get("package_count", 0)}')

# Test 4: Compile
print('\n=== Test 4: Compile ===')
test_code = 'print("Hello from Kaguya IDE!")'
r = requests.post(f'{base}/agent/compile', json={
    'language': 'python',
    'code': test_code,
    'timeout': 10
}, timeout=15)
print(f'Status: {r.status_code}')
d = r.json()
print(f'Result: {d.get("result", "")[:200] if d.get("result") else "N/A"}')
print(f'Error: {d.get("error", "None")}')

print('\n=== All Tests Complete ===')
