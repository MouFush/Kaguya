"""
完整流程测试 - 模拟前端请求
"""
import json
import urllib.request
import sys

def test_stream_endpoint():
    """测试 /stream 端点"""
    print("=" * 60)
    print("测试 /stream 端点")
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
    print(f"请求数据: {json.dumps(data, ensure_ascii=False)}")
    
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            print(f"\n响应状态: {response.status}")
            print(f"内容类型: {response.headers.get('Content-Type')}")
            print(f"\n接收数据:")
            print("-" * 60)
            
            chunk_count = 0
            full_content = []
            
            for line in response:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    try:
                        json_data = json.loads(line_str[6:])
                        chunk_count += 1
                        
                        if json_data.get('content'):
                            content = json_data['content']
                            full_content.append(content)
                            print(f"[{chunk_count}] Content: '{content}'")
                        
                        if json_data.get('done'):
                            print(f"[{chunk_count}] Done! tokens_in={json_data.get('tokens_in')}, tokens_out={json_data.get('tokens_out')}")
                            break
                    except json.JSONDecodeError as e:
                        print(f"JSON解析错误: {e}, line: {line_str[:100]}")
            
            print("-" * 60)
            print(f"\n总计接收 {chunk_count} 个 chunk")
            print(f"完整内容: {''.join(full_content)}")
            
            if full_content:
                print("\n✅ 测试通过！收到回复")
                return True
            else:
                print("\n❌ 测试失败！没有收到内容")
                return False
                
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_generate_stream_directly():
    """直接测试 generate_stream 函数"""
    print("\n" + "=" * 60)
    print("直接测试 generate_stream 函数")
    print("=" * 60)
    
    sys.path.insert(0, r'c:\Users\林智涵\.conda')
    
    try:
        from qwen3_web import generate_stream
        
        print("\n调用 generate_stream...")
        chunks = []
        
        for chunk in generate_stream(
            message="你好",
            history=[],
            role_id="kaguya",
            temperature=0.7,
            max_tokens=100
        ):
            chunks.append(chunk)
            data = json.loads(chunk)
            if data.get('content'):
                print(f"Chunk: '{data['content']}'")
            if data.get('done'):
                print(f"Done! tokens: {data.get('tokens_out')}")
        
        print(f"\n共生成 {len(chunks)} 个 chunk")
        
        if len(chunks) > 1:
            print("✅ generate_stream 工作正常")
            return True
        else:
            print("❌ generate_stream 没有生成内容")
            return False
            
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("\n" + "=" * 60)
    print("Qwen3.5-4B 完整流程测试")
    print("=" * 60)
    
    results = []
    
    # 测试1: 直接测试 generate_stream
    results.append(("generate_stream 函数", test_generate_stream_directly()))
    
    # 测试2: 测试 /stream 端点
    results.append(("/stream 端点", test_stream_endpoint()))
    
    # 汇总
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {name}: {status}")
    
    all_passed = all(r[1] for r in results)
    
    if all_passed:
        print("\n🎉 所有测试通过！")
    else:
        print("\n⚠️ 部分测试失败")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
