"""
Qwen3.5-9B Web前端启动脚本
解决TensorFlow/protobuf冲突问题
"""

import sys
import types

tf_module = types.ModuleType('tensorflow')
tf_module.__spec__ = types.SimpleNamespace(name='tensorflow', loader=None, origin=None)
tf_module.__version__ = '2.0.0'
tf_module.__file__ = 'fake_tensorflow'
sys.modules['tensorflow'] = tf_module

import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

import torch
from flask import Flask, render_template_string, request, jsonify
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

MODEL_NAME = r"C:\Users\林智涵\.cache\modelscope\hub\models\Qwen\Qwen3___5-9B"
model = None
tokenizer = None

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Qwen3.5-9B 聊天助手</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh; display: flex; justify-content: center; align-items: center; padding: 20px;
        }
        .container { width: 100%; max-width: 800px; background: white; border-radius: 20px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); overflow: hidden; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 25px; text-align: center; }
        .header h1 { font-size: 28px; margin-bottom: 8px; }
        .header p { opacity: 0.9; font-size: 14px; }
        .chat-container { height: 450px; overflow-y: auto; padding: 20px; background: #f8f9fa; }
        .message { margin-bottom: 15px; display: flex; animation: fadeIn 0.3s ease; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        .message.user { justify-content: flex-end; }
        .message-content { max-width: 70%; padding: 12px 18px; border-radius: 18px; line-height: 1.5; word-wrap: break-word; }
        .message.user .message-content { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-bottom-right-radius: 4px; }
        .message.assistant .message-content { background: white; color: #333; border-bottom-left-radius: 4px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .input-container { padding: 20px; background: white; border-top: 1px solid #eee; display: flex; gap: 10px; }
        .input-container textarea { flex: 1; padding: 15px; border: 2px solid #e0e0e0; border-radius: 25px; resize: none; font-size: 15px; outline: none; font-family: inherit; }
        .input-container textarea:focus { border-color: #667eea; }
        .input-container button { padding: 15px 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 25px; cursor: pointer; font-size: 15px; font-weight: 600; }
        .input-container button:hover { transform: translateY(-2px); box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4); }
        .input-container button:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }
        .settings { padding: 15px 20px; background: #f8f9fa; border-top: 1px solid #eee; display: flex; gap: 20px; flex-wrap: wrap; align-items: center; }
        .setting-item { display: flex; align-items: center; gap: 8px; }
        .setting-item label { font-size: 13px; color: #666; }
        .setting-item input[type="range"] { width: 100px; }
        .setting-item span { font-size: 13px; color: #333; min-width: 40px; }
        .clear-btn { padding: 8px 16px; background: #e0e0e0; color: #333; border: none; border-radius: 15px; cursor: pointer; font-size: 13px; }
        .loading { display: none; padding: 10px; text-align: center; color: #666; }
        .loading.active { display: block; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 Qwen3.5-9B 聊天助手</h1>
            <p>基于通义千问3.5-9B模型的本地对话系统</p>
        </div>
        <div class="chat-container" id="chatContainer">
            <div class="message assistant">
                <div class="message-content">你好！我是Qwen3.5-9B助手，有什么可以帮助你的吗？</div>
            </div>
        </div>
        <div class="loading" id="loading">正在思考中...</div>
        <div class="settings">
            <div class="setting-item">
                <label>温度:</label>
                <input type="range" id="temperature" min="0.1" max="2.0" step="0.1" value="0.7">
                <span id="tempValue">0.7</span>
            </div>
            <div class="setting-item">
                <label>Top-p:</label>
                <input type="range" id="topP" min="0.1" max="1.0" step="0.05" value="0.9">
                <span id="topPValue">0.9</span>
            </div>
            <div class="setting-item">
                <label>最大长度:</label>
                <input type="range" id="maxTokens" min="64" max="2048" step="64" value="512">
                <span id="maxTokensValue">512</span>
            </div>
            <button class="clear-btn" onclick="clearChat()">清空对话</button>
        </div>
        <div class="input-container">
            <textarea id="userInput" rows="2" placeholder="输入你的问题..." onkeydown="handleKeyDown(event)"></textarea>
            <button id="sendBtn" onclick="sendMessage()">发送</button>
        </div>
    </div>
    <script>
        let history = [];
        document.getElementById('temperature').oninput = function() { document.getElementById('tempValue').textContent = this.value; };
        document.getElementById('topP').oninput = function() { document.getElementById('topPValue').textContent = this.value; };
        document.getElementById('maxTokens').oninput = function() { document.getElementById('maxTokensValue').textContent = this.value; };
        function handleKeyDown(e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } }
        function addMessage(role, content) {
            const container = document.getElementById('chatContainer');
            const msgDiv = document.createElement('div');
            msgDiv.className = 'message ' + role;
            msgDiv.innerHTML = '<div class="message-content">' + content + '</div>';
            container.appendChild(msgDiv);
            container.scrollTop = container.scrollHeight;
        }
        function clearChat() {
            history = [];
            document.getElementById('chatContainer').innerHTML = '<div class="message assistant"><div class="message-content">对话已清空。有什么新问题吗？</div></div>';
        }
        async function sendMessage() {
            const input = document.getElementById('userInput');
            const message = input.value.trim();
            if (!message) return;
            const sendBtn = document.getElementById('sendBtn');
            const loading = document.getElementById('loading');
            sendBtn.disabled = true;
            input.value = '';
            addMessage('user', message);
            loading.classList.add('active');
            const temperature = parseFloat(document.getElementById('temperature').value);
            const topP = parseFloat(document.getElementById('topP').value);
            const maxTokens = parseInt(document.getElementById('maxTokens').value);
            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ message: message, history: history, temperature: temperature, top_p: topP, max_tokens: maxTokens })
                });
                const data = await response.json();
                if (data.response) { addMessage('assistant', data.response); history.push([message, data.response]); }
                else if (data.error) { addMessage('assistant', '错误: ' + data.error); }
            } catch (error) { addMessage('assistant', '网络错误，请重试'); }
            loading.classList.remove('active');
            sendBtn.disabled = false;
            input.focus();
        }
    </script>
</body>
</html>
"""

def load_model():
    global model, tokenizer
    if model is not None:
        return model, tokenizer
    print("正在加载模型...")
    quantization_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True
    )
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        quantization_config=quantization_config,
        device_map="auto",
        trust_remote_code=True
    )
    print("模型加载完成!")
    return model, tokenizer

def chat(message, history, temperature, top_p, max_tokens):
    model, tokenizer = load_model()
    messages = [{"role": "system", "content": "你是一个有帮助的AI助手。"}]
    for user_msg, assistant_msg in history:
        if user_msg: messages.append({"role": "user", "content": user_msg})
        if assistant_msg: messages.append({"role": "assistant", "content": assistant_msg})
    messages.append({"role": "user", "content": message})
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer([text], return_tensors="pt").to(model.device)
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            do_sample=True,
            temperature=temperature,
            top_p=top_p,
            pad_token_id=tokenizer.eos_token_id
        )
    generated_ids = outputs[0][inputs.input_ids.shape[1]:]
    response = tokenizer.decode(generated_ids, skip_special_tokens=True)
    return response

app = Flask(__name__)

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/chat', methods=['POST'])
def chat_endpoint():
    try:
        data = request.json
        message = data.get('message', '')
        history = data.get('history', [])
        temperature = data.get('temperature', 0.7)
        top_p = data.get('top_p', 0.9)
        max_tokens = data.get('max_tokens', 512)
        response = chat(message, history, temperature, top_p, max_tokens)
        return jsonify({'response': response})
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    print("=" * 60)
    print("Qwen3.5-9B Web前端 (公网可访问)")
    print("=" * 60)
    import socket
    import threading
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    print(f"本地访问: http://127.0.0.1:5000")
    print(f"局域网访问: http://{local_ip}:5000")
    
    def start_ngrok():
        import time
        time.sleep(2)
        try:
            from pyngrok import ngrok
            ngrok_path = r"c:\Users\林智涵\.conda\ngrok.exe"
            if os.path.exists(ngrok_path):
                from pyngrok import conf
                conf.get_default().ngrok_path = ngrok_path
            public_url = ngrok.connect(5000)
            print(f"公网访问: {public_url}")
            print("=" * 60)
        except Exception as e:
            print(f"ngrok启动失败: {e}")
            print("=" * 60)
    
    ngrok_thread = threading.Thread(target=start_ngrok)
    ngrok_thread.daemon = True
    ngrok_thread.start()
    
    app.run(host='0.0.0.0', port=5000, debug=False)
