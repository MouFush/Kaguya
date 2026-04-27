import requests
import json
import sys

BASE_URL = "http://127.0.0.1:5000"

def test_service():
    results = []
    
    print("=" * 60)
    print("前端功能测试脚本")
    print("=" * 60)
    
    # 1. 测试主页
    print("\n[1] 测试主页访问...")
    try:
        r = requests.get(f"{BASE_URL}/", timeout=5)
        if r.status_code == 200:
            print("    ✅ 主页访问正常 (200)")
            results.append(("主页访问", True, "200"))
        else:
            print(f"    ❌ 主页访问失败 ({r.status_code})")
            results.append(("主页访问", False, str(r.status_code)))
    except Exception as e:
        print(f"    ❌ 主页访问错误: {e}")
        results.append(("主页访问", False, str(e)))
    
    # 2. 测试RAG统计
    print("\n[2] 测试RAG统计API...")
    try:
        r = requests.get(f"{BASE_URL}/rag/stats", timeout=5)
        if r.status_code == 200:
            data = r.json()
            if data.get('success'):
                print(f"    ✅ RAG统计正常 - 文档: {data['stats']['total_docs']}, 分块: {data['stats']['total_chunks']}")
                results.append(("RAG统计", True, f"docs:{data['stats']['total_docs']}"))
            else:
                print(f"    ❌ RAG统计失败: {data}")
                results.append(("RAG统计", False, str(data)))
        else:
            print(f"    ❌ RAG统计失败 ({r.status_code})")
            results.append(("RAG统计", False, str(r.status_code)))
    except Exception as e:
        print(f"    ❌ RAG统计错误: {e}")
        results.append(("RAG统计", False, str(e)))
    
    # 3. 测试RAG文档列表
    print("\n[3] 测试RAG文档列表API...")
    try:
        r = requests.get(f"{BASE_URL}/rag/documents", timeout=5)
        if r.status_code == 200:
            data = r.json()
            if data.get('success'):
                print(f"    ✅ RAG文档列表正常 - 数量: {len(data['documents'])}")
                results.append(("RAG文档列表", True, f"count:{len(data['documents'])}"))
            else:
                print(f"    ❌ RAG文档列表失败: {data}")
                results.append(("RAG文档列表", False, str(data)))
        else:
            print(f"    ❌ RAG文档列表失败 ({r.status_code})")
            results.append(("RAG文档列表", False, str(r.status_code)))
    except Exception as e:
        print(f"    ❌ RAG文档列表错误: {e}")
        results.append(("RAG文档列表", False, str(e)))
    
    # 4. 测试LoRA列表
    print("\n[4] 测试LoRA列表API...")
    try:
        r = requests.get(f"{BASE_URL}/lora/list", timeout=5)
        if r.status_code == 200:
            data = r.json()
            if data.get('loras'):
                print(f"    ✅ LoRA列表正常 - 数量: {len(data['loras'])}")
                results.append(("LoRA列表", True, f"count:{len(data['loras'])}"))
            else:
                print(f"    ❌ LoRA列表失败: {data}")
                results.append(("LoRA列表", False, str(data)))
        else:
            print(f"    ❌ LoRA列表失败 ({r.status_code})")
            results.append(("LoRA列表", False, str(r.status_code)))
    except Exception as e:
        print(f"    ❌ LoRA列表错误: {e}")
        results.append(("LoRA列表", False, str(e)))
    
    # 5. 测试头像图片
    print("\n[5] 测试头像图片...")
    try:
        r = requests.get(f"{BASE_URL}/header-img", timeout=5)
        if r.status_code == 200:
            print(f"    ✅ 头像图片正常 (200)")
            results.append(("头像图片", True, "200"))
        else:
            print(f"    ❌ 头像图片失败 ({r.status_code})")
            results.append(("头像图片", False, str(r.status_code)))
    except Exception as e:
        print(f"    ❌ 头像图片错误: {e}")
        results.append(("头像图片", False, str(e)))
    
    # 6. 测试背景图片
    print("\n[6] 测试背景图片...")
    try:
        r = requests.get(f"{BASE_URL}/background", timeout=5)
        if r.status_code == 200:
            print(f"    ✅ 背景图片正常 (200)")
            results.append(("背景图片", True, "200"))
        else:
            print(f"    ❌ 背景图片失败 ({r.status_code})")
            results.append(("背景图片", False, str(r.status_code)))
    except Exception as e:
        print(f"    ❌ 背景图片错误: {e}")
        results.append(("背景图片", False, str(e)))
    
    # 7. 测试RAG搜索
    print("\n[7] 测试RAG搜索API...")
    try:
        r = requests.post(f"{BASE_URL}/rag/search", 
                         json={"query": "测试", "top_k": 3},
                         timeout=5)
        if r.status_code == 200:
            data = r.json()
            if data.get('success'):
                print(f"    ✅ RAG搜索正常 - 结果数: {data['count']}, 类型: {data.get('query_type', 'N/A')}")
                results.append(("RAG搜索", True, f"count:{data['count']}"))
            else:
                print(f"    ❌ RAG搜索失败: {data}")
                results.append(("RAG搜索", False, str(data)))
        else:
            print(f"    ❌ RAG搜索失败 ({r.status_code})")
            results.append(("RAG搜索", False, str(r.status_code)))
    except Exception as e:
        print(f"    ❌ RAG搜索错误: {e}")
        results.append(("RAG搜索", False, str(e)))
    
    # 8. 测试DeepSeek测试端点
    print("\n[8] 测试DeepSeek API端点...")
    try:
        r = requests.post(f"{BASE_URL}/deepseek/test",
                         json={"apiKey": "test", "apiUrl": "https://api.deepseek.com"},
                         timeout=10)
        if r.status_code == 200:
            data = r.json()
            print(f"    ✅ DeepSeek端点正常 - 响应: {data.get('success', False)}")
            results.append(("DeepSeek端点", True, str(data.get('success', False))))
        else:
            print(f"    ❌ DeepSeek端点失败 ({r.status_code})")
            results.append(("DeepSeek端点", False, str(r.status_code)))
    except Exception as e:
        print(f"    ❌ DeepSeek端点错误: {e}")
        results.append(("DeepSeek端点", False, str(e)))
    
    # 9. 检查前端JavaScript关键函数
    print("\n[9] 检查前端JavaScript关键函数...")
    try:
        r = requests.get(f"{BASE_URL}/", timeout=5)
        content = r.text
        
        checks = [
            ("sendMessage", "function sendMessage" in content or "async function sendMessage" in content),
            ("openDeepSeek", "function openDeepSeek" in content),
            ("closeModal", "function closeModal" in content),
            ("deepseekConfig", "let deepseekConfig" in content),
            ("init()", "function init()" in content and "init();" in content),
        ]
        
        all_ok = True
        for name, exists in checks:
            if exists:
                print(f"    ✅ {name} 函数存在")
            else:
                print(f"    ❌ {name} 函数缺失")
                all_ok = False
        
        results.append(("JS函数检查", all_ok, str([n for n, e in checks if e])))
    except Exception as e:
        print(f"    ❌ JS检查错误: {e}")
        results.append(("JS函数检查", False, str(e)))
    
    # 10. 检查HTML结构
    print("\n[10] 检查HTML结构...")
    try:
        r = requests.get(f"{BASE_URL}/", timeout=5)
        content = r.text
        
        checks = [
            ("mainInput", 'id="mainInput"' in content),
            ("sendBtn", 'id="sendBtn"' in content),
            ("deepseekModal", 'id="deepseekModal"' in content),
            ("messagesContainer", 'id="messagesContainer"' in content),
        ]
        
        all_ok = True
        for name, exists in checks:
            if exists:
                print(f"    ✅ {name} 元素存在")
            else:
                print(f"    ❌ {name} 元素缺失")
                all_ok = False
        
        results.append(("HTML结构检查", all_ok, str([n for n, e in checks if e])))
    except Exception as e:
        print(f"    ❌ HTML检查错误: {e}")
        results.append(("HTML结构检查", False, str(e)))
    
    # 总结
    print("\n" + "=" * 60)
    print("测试结果总结")
    print("=" * 60)
    
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    
    for name, ok, detail in results:
        status = "✅ 通过" if ok else "❌ 失败"
        print(f"  {name}: {status} - {detail}")
    
    print(f"\n总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！前端功能正常！")
        return True
    else:
        print(f"\n⚠️ {total - passed} 个测试失败，需要修复")
        return False

if __name__ == "__main__":
    success = test_service()
    sys.exit(0 if success else 1)
