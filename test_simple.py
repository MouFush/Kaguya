"""
最简单的测试
"""
import urllib.request
import json

def test_simple():
    # 测试根路径
    try:
        req = urllib.request.Request("http://127.0.0.1:5000/", method='GET')
        with urllib.request.urlopen(req, timeout=5) as resp:
            print(f"根路径状态: {resp.status}")
    except Exception as e:
        print(f"根路径错误: {e}")
    
    # 测试 /stream
    try:
        data = json.dumps({
            "message": "test",
            "history": [],
            "role": "kaguya",
            "temperature": 0.7,
            "max_tokens": 100
        }).encode('utf-8')
        
        req = urllib.request.Request(
            "http://127.0.0.1:5000/stream",
            data=data,
            headers={"Content-Type": "application/json"},
            method='POST'
        )
        
        print("\n发送 /stream 请求...")
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(f"状态: {resp.status}")
            print(f"内容类型: {resp.headers.get('Content-Type')}")
            print("\n响应内容 (前500字节):")
            content = resp.read(500)
            print(content.decode('utf-8', errors='replace'))
            
    except Exception as e:
        print(f"/stream 错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_simple()
