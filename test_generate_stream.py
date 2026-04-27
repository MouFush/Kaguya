"""
直接测试 generate_stream 函数
"""
import sys
sys.path.insert(0, r'c:\Users\林智涵\.conda')

from qwen3_web import generate_stream
import json

def test():
    print("=" * 60)
    print("测试 generate_stream 函数")
    print("=" * 60)
    
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
            print(f"Content: {data['content'][:50]}...")
        if data.get('thinking'):
            print(f"Thinking: {data['thinking'][:50]}...")
        if data.get('done'):
            print(f"Done! tokens_in={data.get('tokens_in')}, tokens_out={data.get('tokens_out')}")
    
    print(f"\n共 {len(chunks)} 个 chunks")

if __name__ == "__main__":
    test()
