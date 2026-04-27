"""
Qwen3.5-4B 公网访问启动脚本
同时启动Flask服务器和ngrok隧道
后端: Ollama (qwen3.5:4b)
"""

import subprocess
import threading
import time
import socket
import os
import webbrowser

def get_local_ip():
    hostname = socket.gethostname()
    return socket.gethostbyname(hostname)

def start_flask():
    from qwen3_web import app
    app.run(host='0.0.0.0', port=5000, debug=False)

def start_ngrok():
    time.sleep(2)
    ngrok_path = r"c:\Users\林智涵\.conda\ngrok.exe"
    
    print("\n正在启动ngrok隧道...")
    print("如果需要固定域名，请先注册 https://ngrok.com 并运行:")
    print(f'  {ngrok_path} config add-authtoken YOUR_TOKEN')
    print()
    
    try:
        process = subprocess.Popen(
            [ngrok_path, "http", "5000"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        time.sleep(3)
        
        import urllib.request
        import json
        
        try:
            with urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels") as response:
                data = json.loads(response.read().decode())
                if data['tunnels']:
                    public_url = data['tunnels'][0]['public_url']
                    print("=" * 60)
                    print(f"公网访问地址: {public_url}")
                    print("=" * 60)
                    print("\n任何设备都可以通过以上地址访问你的Qwen3.5-4B服务！")
                    print("按 Ctrl+C 停止服务\n")
        except Exception as e:
            print(f"获取公网地址失败: {e}")
            print("请手动访问 http://127.0.0.1:4040 查看ngrok状态")
            
    except FileNotFoundError:
        print("ngrok未找到，请从 https://ngrok.com/download 下载")
    except Exception as e:
        print(f"ngrok启动失败: {e}")

if __name__ == '__main__':
    print("=" * 60)
    print("Qwen3.5-4B Web前端 (公网可访问版 - Ollama)")
    print("=" * 60)
    
    local_ip = get_local_ip()
    print(f"本地访问: http://127.0.0.1:5000")
    print(f"局域网访问: http://{local_ip}:5000")
    
    ngrok_thread = threading.Thread(target=start_ngrok)
    ngrok_thread.daemon = True
    ngrok_thread.start()
    
    print("\n正在启动Flask服务器...")
    
    try:
        start_flask()
    except KeyboardInterrupt:
        print("\n服务已停止")
