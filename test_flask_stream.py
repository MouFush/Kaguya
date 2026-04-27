"""
测试 Flask 流式响应
"""
import urllib.request
import json

def test_flask_stream():
    print("=" * 60)
    print("测试 Flask 流式响应")
    print("=" * 60)
    
    # 测试一个简单的流式端点
    url = "http://127.0.0.1:5000/stream"
    data = {
        "message": "hello",
        "history": [],
        "role": "kaguya",
        "temperature": 0.7,
        "max_tokens": 50
    }
    
    body = json.dumps(data, ensure_ascii=False).encode('utf-8')
    headers = {"Content-Type": "application/json"}
    req = urllib.request.Request(url, data=body, headers=headers, method='POST')
    
    print(f"\n发送请求到 {url}")
    
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            print(f"状态: {response.status}")
            print(f"内容类型: {response.headers.get('Content-Type')}")
            print(f"\n接收数据:")
            print("-" * 60)
            
            chunk_count = 0
            content_chunks = 0
            thinking_chunks = 0
            
            for line in response:
                line_str = line.decode('utf-8')
                if not line_str.startswith('data: '):
                    continue
                
                chunk_count += 1
                json_str = line_str[6:].strip()
                
                try:
                    data = json.loads(json_str)
                    
                    if data.get('content'):
                        content_chunks += 1
                        if content_chunks <= 5:
                            print(f"[{chunk_count}] Content: '{data['content'][:30]}...'")
                    
                    if data.get('thinking'):
                        thinking_chunks += 1
                        if thinking_chunks <= 3:
                            print(f"[{chunk_count}] Thinking: '{data['thinking'][:30]}...'")
                    
                    if data.get('done'):
                        print(f"[{chunk_count}] Done! tokens_in={data.get('tokens_in')}, tokens_out={data.get('tokens_out')}")
                        
                except json.JSONDecodeError as e:
                    print(f"[{chunk_count}] JSON Error: {e}")
            
            print("-" * 60)
            print(f"\n总计:")
            print(f"  Chunks: {chunk_count}")
            print(f"  Content: {content_chunks}")
            print(f"  Thinking: {thinking_chunks}")
            
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
    test_flask_stream()
