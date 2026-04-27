"""
Qwen3.5-9B 公网访问设置指南
===========================

方法1: 使用ngrok (推荐)
----------------------
1. 访问 https://ngrok.com 免费注册账号
2. 登录后获取 authtoken
3. 打开PowerShell运行:
   c:\Users\林智涵\.conda\ngrok.exe config add-authtoken YOUR_TOKEN
   
4. 启动Web服务:
   $env:HF_ENDPOINT='https://hf-mirror.com'
   D:\Anoconda\envs\DL\python.exe c:\Users\林智涵\.conda\qwen3_web.py

5. 新开一个终端运行:
   c:\Users\林智涵\.conda\ngrok.exe http 5000
   
6. ngrok会显示类似这样的公网地址:
   https://xxxx-xxxx.ngrok-free.app
   
   任何设备都可以通过这个地址访问！


方法2: 使用Cloudflare Tunnel (免费无需注册)
------------------------------------------
1. 下载 cloudflared:
   https://github.com/cloudflare/cloudflared/releases
   
2. 启动Web服务后，运行:
   cloudflared tunnel --url http://localhost:5000
   
3. 会显示类似这样的公网地址:
   https://xxxx.trycloudflare.com


方法3: 使用localtunnel (免费无需注册)
------------------------------------
1. 安装Node.js: https://nodejs.org

2. 安装localtunnel:
   npm install -g localtunnel
   
3. 启动Web服务后，运行:
   lt --port 5000
   
4. 会显示类似这样的公网地址:
   https://xxxx.loca.lt


安全提示
--------
- 公网地址意味着任何人都可以访问
- 不要在公网环境下处理敏感信息
- 使用完毕后及时关闭服务
"""

if __name__ == '__main__':
    print(__doc__)
