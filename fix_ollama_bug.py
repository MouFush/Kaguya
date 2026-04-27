"""修复 qwen3_web.py 中的 USE_OLLAMA bug"""
import re

file_path = r'c:\Users\林智涵\.conda\qwen3_web.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 修复 generate_stream 函数 - 移除 USE_OLLAMA 条件判断和本地模型代码
old_generate_stream = '''    input_len = sum(len(m['content']) for m in messages) // 2
    
    if USE_OLLAMA:
        generated_tokens = 0
        try:
            for chunk in model.chat_stream(messages, temperature=temperature, max_tokens=max_tokens):
                generated_tokens += 1
                yield json.dumps({"content": chunk, "done": False}) + "\\n"
            yield json.dumps({"content": "", "done": True, "tokens_in": input_len, "tokens_out": generated_tokens}) + "\\n"
        except Exception as e:
            yield json.dumps({"content": f"错误: {str(e)}", "done": True}) + "\\n"
        return
    
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer([text], return_tensors="pt").to(model.device)
    input_len = inputs.input_ids.shape[1]
    
    generated_tokens = 0
    past_key_values = None
    current_input = inputs
    
    buffer = ""
    in_thinking = False
    thinking_content = ""
    response_content = ""
    think_start_detected = False
    
    with torch.no_grad():
        for _ in range(max_tokens):
            if past_key_values is None:
                outputs = model(**current_input, use_cache=True)
            else:
                outputs = model(input_ids=current_input["input_ids"][:, -1:], past_key_values=past_key_values, use_cache=True)
            
            past_key_values = outputs.past_key_values
            logits = outputs.logits[:, -1, :]
            
            if temperature > 0:
                probs = torch.softmax(logits / temperature, dim=-1)
                next_token = torch.multinomial(probs, 1)
            else:
                next_token = logits.argmax(dim=-1, keepdim=True)
            
            generated_tokens += 1
            current_input = {"input_ids": torch.cat([current_input["input_ids"], next_token], dim=-1)}
            
            token_text = tokenizer.decode(next_token[0], skip_special_tokens=True)
            
            if next_token[0].item() == tokenizer.eos_token_id:
                yield json.dumps({"content": "", "done": True, "tokens_in": input_len, "tokens_out": generated_tokens}) + "\\n"
                break
            
            buffer += token_text
            
            # 检测 <think > 标签开始
            if not in_thinking and not think_start_detected:
                if "<think >" in buffer:
                    in_thinking = True
                    think_start_detected = True
                    before_think = buffer.split("<think >")[0]
                    if before_think:
                        yield json.dumps({"content": before_think, "done": False}) + "\\n"
                        response_content += before_think
                    buffer = ""
                    continue
                if len(buffer) > 20:
                    yield json.dumps({"content": buffer, "done": False}) + "\\n"
                    response_content += buffer
                    buffer = ""
                    continue
            
            if in_thinking:
                if "</think >" in buffer:
                    in_thinking = False
                    think_parts = buffer.split("</think >")
                    thinking_content += think_parts[0]
                    yield json.dumps({"reasoning": think_parts[0], "done": False}) + "\\n"
                    if len(think_parts) > 1:
                        remaining = "</think >".join(think_parts[1:])
                        if remaining:
                            yield json.dumps({"content": remaining, "done": False}) + "\\n"
                            response_content += remaining
                    buffer = ""
                    continue
                else:
                    if len(buffer) > 20:
                        yield json.dumps({"reasoning": buffer, "done": False}) + "\\n"
                        thinking_content += buffer
                        buffer = ""
                    continue
            
            if buffer and not in_thinking and think_start_detected:
                yield json.dumps({"content": buffer, "done": False}) + "\\n"
                response_content += buffer
                buffer = ""
            elif buffer and not think_start_detected:
                yield json.dumps({"content": buffer, "done": False}) + "\\n"
                response_content += buffer
                buffer = ""

def chat(message, history, role_id='kaguya', lora_id=None, temperature=0.7, max_tokens=512, structured_template=None):
    model, tokenizer = load_model()
    
    system_prompt = get_role_system(role_id)
    lora_system = get_lora_system(lora_id)
    if lora_system:
        system_prompt = lora_system
    
    structured_prompt = get_structured_output_prompt(message, structured_template)
    if structured_prompt:
        system_prompt += structured_prompt
    
    messages = [{"role": "system", "content": system_prompt}]
    for h in history:
        messages.append({"role": "user", "content": h[0]})
        messages.append({"role": "assistant", "content": h[1]})
    messages.append({"role": "user", "content": message})
    
    input_len = sum(len(m['content']) for m in messages) // 2
    
    if USE_OLLAMA:
        try:
            response = model.chat(messages, temperature=temperature, max_tokens=max_tokens)
            return response, input_len, len(response) // 2
        except Exception as e:
            return f"错误: {str(e)}", input_len, 0
    
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer([text], return_tensors="pt").to(model.device)
    input_len = inputs.input_ids.shape[1]
    
    with torch.no_grad():
        outputs = model.generate('''

new_generate_stream = '''    input_len = sum(len(m['content']) for m in messages) // 2
    
    generated_tokens = 0
    try:
        for chunk in model.chat_stream(messages, temperature=temperature, max_tokens=max_tokens):
            generated_tokens += 1
            yield json.dumps({"content": chunk, "done": False}) + "\\n"
        yield json.dumps({"content": "", "done": True, "tokens_in": input_len, "tokens_out": generated_tokens}) + "\\n"
    except Exception as e:
        yield json.dumps({"content": f"错误: {str(e)}", "done": True}) + "\\n"


def chat(message, history, role_id='kaguya', lora_id=None, temperature=0.7, max_tokens=512, structured_template=None):
    model = load_model()
    
    system_prompt = get_role_system(role_id)
    lora_system = get_lora_system(lora_id)
    if lora_system:
        system_prompt = lora_system
    
    structured_prompt = get_structured_output_prompt(message, structured_template)
    if structured_prompt:
        system_prompt += structured_prompt
    
    messages = [{"role": "system", "content": system_prompt}]
    for h in history:
        messages.append({"role": "user", "content": h[0]})
        messages.append({"role": "assistant", "content": h[1]})
    messages.append({"role": "user", "content": message})
    
    input_len = sum(len(m['content']) for m in messages) // 2
    
    try:
        response = model.chat(messages, temperature=temperature, max_tokens=max_tokens)
        return response, input_len, len(response) // 2
    except Exception as e:
        return f"错误: {str(e)}", input_len, 0


def get_provider_runtime('''

if old_generate_stream in content:
    content = content.replace(old_generate_stream, new_generate_stream)
    print("已修复 generate_stream 和 chat 函数")
else:
    print("未找到需要修复的代码块，尝试其他方式...")

# 保存文件
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("修复完成！")
