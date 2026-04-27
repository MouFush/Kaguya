import requests
import re

BASE_URL = "http://127.0.0.1:5000"

def detailed_check():
    print("=" * 60)
    print("详细前端检查")
    print("=" * 60)
    
    r = requests.get(f"{BASE_URL}/", timeout=5)
    content = r.text
    
    # 检查sendMessage函数是否完整
    print("\n[1] 检查sendMessage函数...")
    if "async function sendMessage()" in content:
        # 检查函数是否完整
        if "const input = document.getElementById('mainInput')" in content:
            print("  ✅ sendMessage函数完整")
        else:
            print("  ❌ sendMessage函数不完整")
    else:
        print("  ❌ sendMessage函数未找到")
    
    # 检查openDeepSeek函数
    print("\n[2] 检查openDeepSeek函数...")
    if "function openDeepSeek()" in content:
        if "document.getElementById('deepseekApiKey')" in content:
            print("  ✅ openDeepSeek函数完整")
        else:
            print("  ❌ openDeepSeek函数不完整")
    else:
        print("  ❌ openDeepSeek函数未找到")
    
    # 检查closeModal函数
    print("\n[3] 检查closeModal函数...")
    if "function closeModal(id)" in content or "function closeModal(" in content:
        print("  ✅ closeModal函数存在")
    else:
        print("  ❌ closeModal函数未找到")
    
    # 检查deepseekConfig变量
    print("\n[4] 检查deepseekConfig变量...")
    if "let deepseekConfig" in content:
        print("  ✅ deepseekConfig变量存在")
    else:
        print("  ❌ deepseekConfig变量未找到")
    
    # 检查init函数调用
    print("\n[5] 检查init函数...")
    if "function init()" in content and "init();" in content:
        print("  ✅ init函数存在并被调用")
    else:
        print("  ❌ init函数问题")
    
    # 检查onclick绑定
    print("\n[6] 检查onclick绑定...")
    checks = [
        ('onclick="sendMessage()"', 'sendBtn'),
        ('onclick="openDeepSeek()"', 'DeepSeek按钮'),
        ('onclick="stopGeneration()"', 'stopBtn'),
        ('onclick="toggleVoiceInput()"', 'voiceInputBtn'),
    ]
    for pattern, name in checks:
        if pattern in content:
            print(f"  ✅ {name}绑定正确")
        else:
            print(f"  ❌ {name}绑定缺失")
    
    # 检查是否有JavaScript错误模式
    print("\n[7] 检查潜在JavaScript错误...")
    
    # 检查未定义变量使用
    errors = []
    
    # 检查是否有语法错误
    if "function function" in content:
        errors.append("重复function关键字")
    
    # 检查是否有未闭合的字符串
    if content.count('"') % 2 != 0:
        errors.append("双引号不匹配")
    
    if content.count("'") % 2 != 0:
        errors.append("单引号不匹配")
    
    if errors:
        for e in errors:
            print(f"  ❌ {e}")
    else:
        print("  ✅ 未发现明显语法错误")
    
    # 检查关键元素
    print("\n[8] 检查关键HTML元素...")
    elements = [
        'id="mainInput"',
        'id="sendBtn"',
        'id="stopBtn"',
        'id="messagesContainer"',
        'id="deepseekModal"',
        'id="statusText"',
    ]
    for elem in elements:
        if elem in content:
            print(f"  ✅ {elem}")
        else:
            print(f"  ❌ {elem} 缺失")
    
    # 检查CSS样式
    print("\n[9] 检查关键CSS...")
    css_checks = [
        '.send-btn',
        '.main-input',
        '.input-area',
        '.modal-overlay',
    ]
    for css in css_checks:
        if css in content:
            print(f"  ✅ {css} 样式存在")
        else:
            print(f"  ❌ {css} 样式缺失")
    
    print("\n" + "=" * 60)
    print("检查完成")
    print("=" * 60)

if __name__ == "__main__":
    detailed_check()
