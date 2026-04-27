#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
角色卡功能自检脚本
测试关闭角色卡情况下是否能正常对话
"""

import requests
import json
import sys
import time

BASE_URL = "http://127.0.0.1:5000"

def test_health():
    """测试服务是否正常运行"""
    print("=" * 60)
    print("测试1: 服务健康检查")
    print("=" * 60)
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        if response.status_code == 200:
            print("✅ 服务正常运行")
            return True
        else:
            print(f"❌ 服务返回异常状态码: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 服务无法访问: {e}")
        return False

def test_chat_without_role():
    """测试关闭角色卡时的对话功能"""
    print("\n" + "=" * 60)
    print("测试2: 关闭角色卡对话测试")
    print("=" * 60)
    
    # 测试数据 - 模拟关闭角色卡的情况 (role为null)
    test_data = {
        "message": "你好，请介绍一下自己",
        "history": [],
        "role": None,  # 关闭角色卡
        "lora": None,
        "temperature": 0.7,
        "max_tokens": 1024
    }
    
    try:
        print("发送请求 (role=None)...")
        response = requests.post(
            f"{BASE_URL}/stream",
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=30,
            stream=True
        )
        
        print(f"响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            # 读取流式响应
            content_received = False
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        try:
                            data = json.loads(line_str[6:])
                            if 'content' in data and data['content']:
                                content_received = True
                                print(f"收到内容: {data['content'][:50]}...")
                                break
                        except:
                            pass
            
            if content_received:
                print("✅ 关闭角色卡时可以正常对话")
                return True
            else:
                print("⚠️ 收到响应但没有内容")
                return False
        else:
            print(f"❌ 请求失败: {response.status_code}")
            try:
                error_data = response.json()
                print(f"错误信息: {error_data}")
            except:
                print(f"响应内容: {response.text[:200]}")
            return False
            
    except requests.Timeout:
        print("❌ 请求超时")
        return False
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_chat_with_role():
    """测试开启角色卡时的对话功能"""
    print("\n" + "=" * 60)
    print("测试3: 开启角色卡对话测试")
    print("=" * 60)
    
    test_data = {
        "message": "你好",
        "history": [],
        "role": "kaguya",  # 开启角色卡
        "lora": None,
        "temperature": 0.7,
        "max_tokens": 1024
    }
    
    try:
        print("发送请求 (role='kaguya')...")
        response = requests.post(
            f"{BASE_URL}/stream",
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=30,
            stream=True
        )
        
        print(f"响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            content_received = False
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        try:
                            data = json.loads(line_str[6:])
                            if 'content' in data and data['content']:
                                content_received = True
                                print(f"收到内容: {data['content'][:50]}...")
                                break
                        except:
                            pass
            
            if content_received:
                print("✅ 开启角色卡时可以正常对话")
                return True
            else:
                print("⚠️ 收到响应但没有内容")
                return False
        else:
            print(f"❌ 请求失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return False

def test_deepseek_without_role():
    """测试DeepSeek API关闭角色卡时的情况"""
    print("\n" + "=" * 60)
    print("测试4: DeepSeek API关闭角色卡测试")
    print("=" * 60)
    
    # 首先检查DeepSeek配置
    try:
        response = requests.get(f"{BASE_URL}/api/deepseek/status", timeout=5)
        if response.status_code == 200:
            status = response.json()
            print(f"DeepSeek状态: {status}")
            if not status.get('enabled'):
                print("⚠️ DeepSeek未启用，跳过此测试")
                return None
        else:
            print("⚠️ 无法获取DeepSeek状态，跳过此测试")
            return None
    except:
        print("⚠️ DeepSeek API不可用，跳过此测试")
        return None
    
    test_data = {
        "apiKey": "test",
        "apiUrl": "https://api.deepseek.com",
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": "你好"}],
        "role": None,  # 关闭角色卡
        "kaguyaMode": False
    }
    
    try:
        print("发送DeepSeek请求 (role=None, kaguyaMode=False)...")
        response = requests.post(
            f"{BASE_URL}/api/deepseek/chat",
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ DeepSeek API可以正常接收关闭角色卡的请求")
            return True
        else:
            print(f"⚠️ DeepSeek请求返回: {response.status_code}")
            print(f"响应: {response.text[:200]}")
            return None
            
    except Exception as e:
        print(f"⚠️ DeepSeek请求异常: {e}")
        return None

def analyze_frontend_code():
    """分析前端代码中的角色卡逻辑"""
    print("\n" + "=" * 60)
    print("测试5: 前端代码逻辑分析")
    print("=" * 60)
    
    try:
        with open('qwen3_web_final.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查关键逻辑
        checks = {
            "currentRole初始化": "let currentRole = kaguyaMode ? 'kaguya' : null" in content,
            "toggleKaguyaMode更新currentRole": "if (!kaguyaMode) {\n                currentRole = null" in content,
            "发送消息检查角色": "if (currentRole && !enabledRoles.includes(currentRole))" in content,
            "stream请求传递role": "role: kaguyaMode ? currentRole : null" in content,
        }
        
        print("前端代码检查:")
        for check_name, result in checks.items():
            status = "✅" if result else "❌"
            print(f"  {status} {check_name}")
        
        all_passed = all(checks.values())
        if all_passed:
            print("\n✅ 前端代码逻辑正确")
        else:
            print("\n⚠️ 部分前端逻辑可能有问题")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ 代码分析失败: {e}")
        return False

def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("角色卡功能自检")
    print("=" * 60)
    print(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"测试地址: {BASE_URL}")
    print()
    
    results = {}
    
    # 运行各项测试
    results['服务健康'] = test_health()
    
    if results['服务健康']:
        results['关闭角色卡对话'] = test_chat_without_role()
        results['开启角色卡对话'] = test_chat_with_role()
        results['DeepSeek关闭角色卡'] = test_deepseek_without_role()
        results['前端代码逻辑'] = analyze_frontend_code()
    else:
        print("\n❌ 服务未运行，跳过后续测试")
        results['关闭角色卡对话'] = False
        results['开启角色卡对话'] = False
        results['DeepSeek关闭角色卡'] = None
        results['前端代码逻辑'] = False
    
    # 打印测试报告
    print("\n" + "=" * 60)
    print("测试报告")
    print("=" * 60)
    
    for test_name, result in results.items():
        if result is None:
            status = "⏭️ 跳过"
        elif result:
            status = "✅ 通过"
        else:
            status = "❌ 失败"
        print(f"{test_name}: {status}")
    
    # 关键测试
    critical_tests = ['关闭角色卡对话', '开启角色卡对话']
    critical_passed = all(results.get(t, False) for t in critical_tests)
    
    print("\n" + "=" * 60)
    if critical_passed:
        print("🎉 所有关键测试通过！角色卡功能正常")
        print("关闭角色卡时可以正常对话")
    else:
        print("⚠️ 部分关键测试失败")
        print("需要检查:")
        if not results.get('关闭角色卡对话'):
            print("  - 关闭角色卡时无法对话，请检查后端API逻辑")
        if not results.get('开启角色卡对话'):
            print("  - 开启角色卡时无法对话，请检查角色系统")
    print("=" * 60)
    
    return critical_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
