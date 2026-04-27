"""
Qwen3.5-4B Ollama 对话脚本
使用 Ollama 运行本地模型
"""

import os
import sys

USE_OLLAMA = True
OLLAMA_MODEL = "qwen3.5:4b"

if USE_OLLAMA:
    from ollama_adapter import chat_with_ollama, stream_chat_with_ollama, get_ollama_adapter, OllamaConfig
else:
    os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig


def load_model():
    if USE_OLLAMA:
        print("=" * 60)
        print("Qwen3.5-4B (Ollama)")
        print("=" * 60)
        
        adapter = get_ollama_adapter(OllamaConfig(model=OLLAMA_MODEL))
        
        if not adapter.is_server_running():
            print("错误: Ollama 服务未运行")
            print("请先启动 Ollama 服务，或运行: ollama serve")
            sys.exit(1)
        
        if not adapter.is_model_available(OLLAMA_MODEL):
            print(f"错误: 模型 {OLLAMA_MODEL} 未安装")
            print(f"请运行: ollama pull {OLLAMA_MODEL}")
            sys.exit(1)
        
        print(f"模型: {OLLAMA_MODEL}")
        print("状态: 已就绪")
        return adapter, None
    else:
        print("=" * 60)
        print("Qwen3.5-9B 本地部署")
        print("=" * 60)
        
        model_name = r"C:\Users\林智涵\.cache\modelscope\hub\models\Qwen\Qwen3___5-9B"
        
        print(f"\n正在加载模型: {model_name}")
        print(f"镜像源: {os.environ.get('HF_ENDPOINT', 'huggingface.co')}")
        print(f"设备: {'CUDA' if torch.cuda.is_available() else 'CPU'}")
        if torch.cuda.is_available():
            print(f"GPU: {torch.cuda.get_device_name(0)}")
            print(f"显存: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
        
        print("\n配置4-bit量化...")
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True
        )
        
        print("加载tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            trust_remote_code=True
        )
        
        print("加载模型(首次运行需要下载约16GB)...")
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            quantization_config=quantization_config,
            device_map="auto",
            trust_remote_code=True
        )
        
        print("\n模型加载完成!")
        return model, tokenizer


def chat(model, tokenizer):
    print("\n" + "=" * 60)
    print("开始对话 (输入 'quit' 或 'exit' 退出)")
    print("=" * 60 + "\n")
    
    history = []
    
    while True:
        user_input = input("你: ").strip()
        
        if user_input.lower() in ['quit', 'exit', 'q']:
            print("再见!")
            break
        
        if not user_input:
            continue
        
        if USE_OLLAMA:
            try:
                print("Qwen3.5: ", end="", flush=True)
                for chunk in stream_chat_with_ollama(
                    user_input,
                    history=history,
                    system_prompt="你是一个有帮助的AI助手。",
                    temperature=0.7,
                    max_tokens=512
                ):
                    print(chunk, end="", flush=True)
                print("\n")
                
                response = ""
                for h_user, h_assistant in history:
                    pass
                history.append((user_input, response))
                
            except Exception as e:
                print(f"错误: {e}")
        else:
            messages = [
                {"role": "system", "content": "你是一个有帮助的AI助手。"},
                {"role": "user", "content": user_input}
            ]
            
            for h_user, h_assistant in history:
                messages.insert(-1, {"role": "user", "content": h_user})
                messages.insert(-1, {"role": "assistant", "content": h_assistant})
            
            text = tokenizer.apply_chat_template(
                messages, 
                tokenize=False, 
                add_generation_prompt=True
            )
            
            inputs = tokenizer([text], return_tensors="pt").to(model.device)
            
            print("Qwen3: ", end="", flush=True)
            
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=512,
                    do_sample=True,
                    temperature=0.7,
                    top_p=0.9,
                    pad_token_id=tokenizer.eos_token_id
                )
            
            generated_ids = outputs[0][inputs.input_ids.shape[1]:]
            response = tokenizer.decode(generated_ids, skip_special_tokens=True)
            print(response)
            print()
            
            history.append((user_input, response))


def main():
    model, tokenizer = load_model()
    chat(model, tokenizer)


if __name__ == "__main__":
    main()
