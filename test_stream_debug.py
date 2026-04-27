"""
调试 /stream 端点
"""
import json
import urllib.request

def test_stream():
    print("=" * 60)
    print("调试 /stream 端点")
    print("=" * 60)
    
    url = "http://127.0.0.1:5000/stream"
    data = {
        "message": "你好",
        "history": [],
        "role": "kaguya",
        "lora": None,
        "temperature": 0.7,
        "max_tokens": 512,
        "use_rag": False
    }
    
    body = json.dumps(data, ensure_ascii=False).encode('utf-8')
    headers = {"Content-Type": "application/json"}
    req = urllib.request.Request(url, data=body, headers=headers, method='POST')
    
    print(f"\n发送请求到 {url}")
    
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            print(f"响应状态: {response.status}")
            print(f"\n接收数据:")
            print("-" * 60)
            
            chunk_count = 0
            content_count = 0
            thinking_count = 0
            
            for line in response:
                line_str = line.decode('utf-8')
                if not line_str.startswith('data: '):
                    continue
                
                chunk_count += 1
                json_str = line_str[6:]
                
                try:
                    data = json.loads(json_str)
                    
                    if data.get('content'):
                        content_count += 1
                        print(f"[{chunk_count}] Content: '{data['content'][:50]}...'")
                    
                    if data.get('thinking'):
                        thinking_count += 1
                        if thinking_count <= 3:
                            print(f"[{chunk_count}] Thinking: '{data['thinking'][:50]}...'")
                    
                    if data.get('done'):
                        print(f"[{chunk_count}] Done! tokens_in={data.get('tokens_in')}, tokens_out={data.get('tokens_out')}")
                        
                except json.JSONDecodeError as e:
                    print(f"[{chunk_count}] JSON Error: {e}")
                    print(f"  Raw: {json_str[:100]}")
            
            print("-" * 60)
            print(f"\n总计:")
            print(f"  Chunks: {chunk_count}")
            print(f"  Content: {content_count}")
            print(f"  Thinking: {thinking_count}")
            
            if chunk_count > 1:
                print("\n✅ 测试通过！收到数据")
                return True
            else:
                print("\n❌ 测试失败！没有收到数据")
                return False
                
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_stream()
