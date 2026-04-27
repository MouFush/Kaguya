"""测试 Ollama 适配器"""
import sys
sys.path.insert(0, r'c:\Users\林智涵\.conda')

print("=" * 60)
print("Ollama 适配器测试")
print("=" * 60)

try:
    from ollama_adapter import get_ollama_adapter, OllamaConfig, chat_with_ollama
    
    adapter = get_ollama_adapter()
    
    print(f"\nOllama 服务状态: {'运行中' if adapter.is_server_running() else '未运行'}")
    
    if adapter.is_server_running():
        print("\n可用模型:")
        for model in adapter.list_models():
            print(f"  - {model.get('name')} ({model.get('size', 'unknown')})")
        
        print(f"\n模型 qwen3.5:4b 可用: {adapter.is_model_available('qwen3.5:4b')}")
        
        print("\n测试对话...")
        response = chat_with_ollama(
            "你好，请用一句话介绍自己",
            system_prompt="你是一个有帮助的AI助手。"
        )
        print(f"回复: {response}")
        
        print("\n✅ 测试成功!")
    else:
        print("\n❌ Ollama 服务未运行，请先启动 Ollama")
        
except Exception as e:
    print(f"\n❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()
