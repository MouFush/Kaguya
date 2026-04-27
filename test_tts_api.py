import requests
r = requests.post('http://127.0.0.1:5000/tts', json={'text': '你好'})
print(r.json())
