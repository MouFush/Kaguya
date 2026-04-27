"""
调试 ollama_adapter - 详细版本
"""
import sys
import json
import urllib.request
sys.path.insert(0, r'c:\Users\林智涵\.conda')

def test_raw_stream():
    print("=" * 60)
    print("直接测试 Ollama API 流式响应")
    print("=" * 60)
    
    url = "http://localhost:11434/api/chat"
    data = {
        "model": "qwen3.5:4b",
        "messages": [
            {"role": "system", "content": "你是一个有帮助的助手。"},
            {"role": "user", "content": "你好"}
        ],
        "stream": True,
        "options": {
            "temperature": 0.7,
            "num_predict": 100,
            "top_p": 0.9
        }
    }
    
    body = json.dumps(data, ensure_ascii=False).encode('utf-8')
    headers = {"Content-Type": "application/json"}
    req = urllib.request.Request(url, data=body, headers=headers, method='POST')
    
    print(f"\n请求 URL: {url}")
    print(f"请求数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            print(f"\n响应状态: {response.status}")
            print(f"\n逐行读取:")
            print("-" * 60)
            
            line_count = 0
            content_count = 0
            thinking_count = 0
            
            for line in response:
                line_count += 1
                line_str = line.decode('utf-8').strip()
                
                if not line_str:
                    continue
                
                try:
                    chunk = json.loads(line_str)
                    message = chunk.get('message', {})
                    content = message.get('content', '')
                    thinking = message.get('thinking', '')
                    done = chunk.get('done', False)
                    
                    if content:
                        content_count += 1
                        print(f"[{line_count}] Content ({len(content)} chars): '{content[:50]}...'")
                    
                    if thinking:
                        thinking_count += 1
                        if thinking_count <= 3:  # 只显示前3个 thinking
                            print(f"[{line_count}] Thinking: '{thinking[:50]}...'")
                    
                    if done:
                        print(f"[{line_count}] Done!")
                        break
                        
                except json.JSONDecodeError as e:
                    print(f"[{line_count}] JSON Error: {e}")
                    print(f"  Raw: {line_str[:100]}")
            
            print("-" * 60)
            print(f"\n总计:")
            print(f"  行数: {line_count}")
            print(f"  Content 数量: {content_count}")
            print(f"  Thinking 数量: {thinking_count}")
            
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()

def test_adapter_with_debug():
    print("\n" + "=" * 60)
    print("测试 ollama_adapter 带调试")
    print("=" * 60)
    
    from ollama_adapter import get_ollama_adapter, OllamaConfig
    
    adapter = get_ollama_adapter(OllamaConfig(model="qwen3.5:4b"))
    
    messages = [
        {"role": "system", "content": "你是一个有帮助的助手。"},
        {"role": "user", "content": "你好"}
    ]
    
    data = {
        "model": adapter.config.model,
        "messages": messages,
        "stream": True,
        "options": {
            "temperature": 0.7,
            "num_predict": 100,
            "top_p": 0.9,
        }
    }
    
    print(f"\n请求数据: {json.dumps(data, ensure_ascii=False)}")
    print("\n调用 _request 方法...")
    
    try:
        response = adapter._request("/api/chat", data, stream=True)
        print(f"响应类型: {type(response)}")
        print(f"响应对象: {response}")
        
        print("\n开始迭代响应...")
        print("-" * 60)
        
        line_count = 0
        for line in response:
            line_count += 1
            print(f"[{line_count}] Raw line type: {type(line)}, len: {len(line) if line else 0}")
            
            if line_count > 5:  # 只显示前5行
                print("... (截断)")
                break
        
        print("-" * 60)
        print(f"共 {line_count} 行")
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_raw_stream()
    test_adapter_with_debug()
