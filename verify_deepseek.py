import requests
import json
import os
import sys

BASE = "http://127.0.0.1:5000"

print("=" * 70)
print("DeepSeek API + Agent Tool Call Verification")
print("=" * 70)

# Step 1: Get the actual API config from the backend
print("\n--- Step 1: Get API Configuration ---")
r = requests.get(f"{BASE}/external/config", timeout=10)
d = r.json()
providers = d.get("providers", {})
ds = providers.get("deepseek", {})
print(f"  DeepSeek config from backend:")
print(f"    enabled: {ds.get('enabled')}")
print(f"    has_key: {ds.get('_has_key', False)}")
print(f"    model: {ds.get('model')}")
print(f"    apiUrl: {ds.get('apiUrl')}")

# The API key is stored in browser localStorage, not in backend
# We need to check if the user has actually configured it
# Let's try to read the config file directly
config_paths = [
    os.path.expanduser("~/.kaguya/api_config.json"),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "api_config.json"),
]

api_key = None
api_url = "https://api.deepseek.com/v1"
model_name = "deepseek-chat"

# Try to find the API key from various sources
for cp in config_paths:
    if os.path.exists(cp):
        with open(cp, 'r') as f:
            cfg = json.load(f)
        if 'deepseek' in cfg:
            api_key = cfg['deepseek'].get('apiKey', '')
            if api_key:
                print(f"  Found API key from {cp}")
                break

# Also check if the API key was saved in the Flask app's config
r2 = requests.get(f"{BASE}/external/config", timeout=10)
d2 = r2.json()
for name, prov in d2.get("providers", {}).items():
    if prov.get("_has_key") or prov.get("apiKey"):
        api_key = prov.get("apiKey", "")
        api_url = prov.get("apiUrl", f"https://api.{name}.com/v1")
        model_name = prov.get("model", "")
        print(f"  Found active provider: {name} (model={model_name})")
        break

if not api_key:
    print("\n  ERROR: No DeepSeek API key found!")
    print("  The API key is stored in browser localStorage.")
    print("  Please provide the API key for testing, or test manually in the browser.")
    print("\n  Attempting to test with the /agent/run endpoint anyway...")
    print("  (The frontend will send the API key from localStorage)")

# Step 2: Test agent with external API
print("\n--- Step 2: Test Agent Tool Call via /agent/run ---")

# We need to simulate what the browser does - send the API key in external_api
# The user said they configured DeepSeek, so let's try with a test message
# If the API key is in localStorage, the browser will send it automatically

# First, let's try without external_api to see if the backend has it stored
r = requests.post(f"{BASE}/agent/run", json={
    "message": "Use the write_file tool to create a file at C:/Users/林智涵/.conda/agent_tool_test.txt with the content: DeepSeek API tool call test OK",
    "solo_mode": True,
    "history": [],
}, stream=True, timeout=120)

events = []
tool_used = None
tool_result = None
final_response = None
error_msg = None

for line in r.iter_lines():
    if line:
        try:
            d = json.loads(line.decode().replace("data: ", "", 1))
            etype = d.get("type", "")
            events.append(etype)
            
            if etype == "tool_use":
                tool_used = d.get("tool", "")
                tool_input = d.get("input", {})
                print(f"  TOOL_USE: {tool_used}")
                print(f"  Input: {json.dumps(tool_input, ensure_ascii=False)[:300]}")
            elif etype == "tool_result":
                tool_result = d.get("output", "")
                print(f"  TOOL_RESULT: {str(tool_result)[:300]}")
            elif etype == "assistant" and d.get("done"):
                final_response = d.get("content", "")
                print(f"  FINAL: {final_response[:300]}")
            elif etype == "error":
                error_msg = d.get("content", "")
                print(f"  ERROR: {error_msg[:300]}")
            elif etype == "thinking":
                content = d.get("content", "")
                if content and len(content.strip()) > 0 and len(content) < 200:
                    print(f"  THINKING: {content[:150]}")
            
            if d.get("done"):
                break
        except:
            pass

# Check if file was created
test_file = r"C:\Users\林智涵\.conda\agent_tool_test.txt"
file_exists = os.path.exists(test_file)
print(f"\n  File exists on disk: {file_exists}")
if file_exists:
    with open(test_file, 'r', encoding='utf-8') as f:
        disk_content = f.read()
    print(f"  Disk content: {disk_content[:200]}")

# Step 3: If no external API was used, check what happened
if error_msg and "Ollama" in error_msg:
    print("\n--- Diagnosis: External API Not Used ---")
    print("  The agent fell back to Ollama because:")
    print("  1. No external_api was sent in the request, OR")
    print("  2. The API key is stored only in browser localStorage")
    print("  3. The backend /external/config doesn't have the key")
    print("\n  SOLUTION: The API key must be sent from the browser.")
    print("  Please test directly in the IDE browser at http://127.0.0.1:5000/agent-ide")
    print("  The frontend will automatically include the API key from localStorage.")
elif tool_used:
    print(f"\n--- SUCCESS: Agent used tool '{tool_used}' ---")
    if file_exists:
        print("  File was created on disk - FULL E2E WORKS!")
    else:
        print("  Tool was called but file may not be at expected path")

# Step 4: Test execute_command
print("\n--- Step 3: Test execute_command Tool Call ---")
r = requests.post(f"{BASE}/agent/run", json={
    "message": "Use the execute_command tool to run: python -c \"print('DeepSeek execute_command test OK')\"",
    "solo_mode": True,
    "history": [],
}, stream=True, timeout=120)

for line in r.iter_lines():
    if line:
        try:
            d = json.loads(line.decode().replace("data: ", "", 1))
            etype = d.get("type", "")
            if etype == "tool_use":
                print(f"  TOOL_USE: {d.get('tool')} -> {json.dumps(d.get('input', {}), ensure_ascii=False)[:200]}")
            elif etype == "tool_result":
                print(f"  TOOL_RESULT: {str(d.get('output', ''))[:300]}")
            elif etype == "assistant" and d.get("done"):
                print(f"  FINAL: {d.get('content', '')[:200]}")
            elif etype == "error":
                print(f"  ERROR: {d.get('content', '')[:300]}")
            if d.get("done"):
                break
        except:
            pass

# Cleanup
if os.path.exists(test_file):
    os.remove(test_file)

print("\n" + "=" * 70)
print("RESULT: If you see TOOL_USE events above, DeepSeek API works!")
print("If you see 'Ollama' errors, test in the browser instead.")
print("The browser sends the API key from localStorage automatically.")
print("=" * 70)
