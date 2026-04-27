"""
直接测试 ollama_adapter
"""
import sys
sys.path.insert(0, r'c:\Users\林智涵\.conda')

from ollama_adapter import get_ollama_adapter, OllamaConfig

def test_chat_stream():
    print("=" * 60)
    print("测试 ollama_adapter.chat_stream")
    print("=" * 60)
    
    adapter = get_ollama_adapter(OllamaConfig(model="qwen3.5:4b"))
    
    messages = [
        {"role": "system", "content": "你是一个有帮助的助手。"},
        {"role": "user", "content": "你好"}
    ]
    
    print(f"\n消息: {messages}")
    print("\n开始流式生成...")
    print("-" * 60)
    
    chunks = []
    chunk_count = 0
    
    try:
        for chunk in adapter.chat_stream(messages, temperature=0.7, max_tokens=100):
            chunk_count += 1
            chunks.append(chunk)
            print(f"[{chunk_count}] '{chunk}'")
        
        print("-" * 60)
        print(f"\n共 {chunk_count} 个 chunk")
        print(f"完整内容: {''.join(chunks)}")
        
        if chunk_count > 0:
            print("\n✅ chat_stream 工作正常")
            return True
        else:
            print("\n❌ chat_stream 没有返回任何内容")
            return False
            
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_chat_stream()
    sys.exit(0 if success else 1)
