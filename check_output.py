#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
输出质量检查脚本
用于检测 AI 输出中的问题并生成报告
"""

import re
import json
import urllib.request
import time
from datetime import datetime
import sys

# 测试配置
TEST_MESSAGES = [
    "你好，请介绍一下你自己",
    "请用中文写一首关于春天的诗",
    "请解释什么是机器学习",
    "请写一个简短的故事",
]

# 问题检测规则
THINKING_MARKERS = [
    "Thinking Process:",
    "思考过程:",
    "Thought Process:",
    "Thinking:",
    "思考:",
    "**Analyze**",
    "**Determine**",
    "**Draft**",
]

def test_stream_output(message, url="http://127.0.0.1:5000/stream"):
    """测试流式输出"""
    print(f"\n{'='*60}")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"测试消息: {message}")
    print(f"{'='*60}\n")
    
    data = {
        "message": message,
        "history": [],
        "role": "kaguya",
        "temperature": 0.7,
        "max_tokens": 512
    }
    
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        
        full_content = ""
        chunk_count = 0
        thinking_detected = False
        
        with urllib.request.urlopen(req, timeout=120) as response:
            for line in response:
                line = line.decode('utf-8').strip()
                if line.startswith('data: '):
                    try:
                        chunk_data = json.loads(line[6:])
                        if chunk_data.get('content'):
                            content = chunk_data['content']
                            full_content += content
                            chunk_count += 1
                            # 检测思考过程标记
                            for marker in THINKING_MARKERS:
                                if marker in content:
                                    thinking_detected = True
                                    print(f"[警告] 检测到思考过程标记: {marker}")
                        if chunk_data.get('done'):
                            print(f"\n[完成] 总共 {chunk_count} 个 chunks")
                    except json.JSONDecodeError as e:
                        print(f"[JSON错误] {e}: {line}")
        
        return full_content, thinking_detected
        
    except Exception as e:
        print(f"[请求错误] {e}")
        return None, False

def analyze_output(text):
    """分析输出质量"""
    if not text:
        return {"error": "无输出内容"}
    
    result = {
        "total_chars": len(text),
        "chinese_ratio": 0,
        "english_ratio": 0,
        "paragraph_count": 0,
        "has_thinking": False,
        "thinking_markers": [],
        "issues": []
    }
    
    # 基本统计
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    english_chars = len(re.findall(r'[a-zA-Z]', text))
    
    if result["total_chars"] > 0:
        result["chinese_ratio"] = chinese_chars / result["total_chars"]
        result["english_ratio"] = english_chars / result["total_chars"]
    
    # 段落分析
    paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
    result["paragraph_count"] = len(paragraphs)
    
    # 检测思考过程标记
    for marker in THINKING_MARKERS:
        if marker in text:
            result["has_thinking"] = True
            result["thinking_markers"].append(marker)
    
    # 检测问题
    # 1. 过多的英文（可能是思考过程）
    if result["english_ratio"] > 0.5:
        result["issues"].append(f"英文比例过高 ({result['english_ratio']*100:.1f}%)，可能包含思考过程")
    
    # 2. 段落过多（可能是被错误分割）
    if result["paragraph_count"] > 20:
        result["issues"].append(f"段落数过多 ({result['paragraph_count']})，可能存在分割问题")
    
    # 3. 检测不完整的句子
    incomplete_sentences = 0
    for p in paragraphs:
        # 辉夜姬角色使用 ~、♪、★ 等符号作为句子结尾，这是正常的
        if p and not re.search(r'[。！？\.\!\?~♪★]$', p):
            incomplete_sentences += 1
    if incomplete_sentences > result["paragraph_count"] * 0.5:
        result["issues"].append(f"不完整句子过多 ({incomplete_sentences}/{result['paragraph_count']})")
    
    # 4. 检测重复内容
    if len(paragraphs) != len(set(paragraphs)):
        result["issues"].append("存在重复段落")
    
    return result

def print_report(text, analysis):
    """打印分析报告"""
    print(f"\n{'='*60}")
    print("输出质量分析报告")
    print(f"{'='*60}")
    
    print(f"\n[基本统计]")
    print(f"  总字符数: {analysis['total_chars']}")
    print(f"  中文比例: {analysis['chinese_ratio']*100:.1f}%")
    print(f"  英文比例: {analysis['english_ratio']*100:.1f}%")
    print(f"  段落数: {analysis['paragraph_count']}")
    
    print(f"\n[思考过程检测]")
    if analysis["has_thinking"]:
        print(f"  ⚠️ 检测到思考过程标记: {', '.join(analysis['thinking_markers'])}")
    else:
        print(f"  ✅ 未检测到思考过程标记")
    
    print(f"\n[问题检测]")
    if analysis["issues"]:
        for issue in analysis["issues"]:
            print(f"  ⚠️ {issue}")
    else:
        print(f"  ✅ 未检测到问题")
    
    print(f"\n[完整输出]")
    print("-" * 60)
    # 限制输出长度
    if len(text) > 500:
        print(text[:500] + "...")
    else:
        print(text)
    print("-" * 60)

def run_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("开始输出质量检查")
    print("="*60)
    
    all_results = []
    passed = 0
    failed = 0
    
    for i, message in enumerate(TEST_MESSAGES):
        print(f"\n[测试 {i+1}/{len(TEST_MESSAGES)}]")
        text, thinking_detected = test_stream_output(message)
        
        if text:
            analysis = analyze_output(text)
            analysis["thinking_detected_in_stream"] = thinking_detected
            print_report(text, analysis)
            all_results.append(analysis)
            
            # 判断是否通过
            if not analysis["has_thinking"] and not analysis["issues"]:
                passed += 1
                print("\n✅ 测试通过")
            else:
                failed += 1
                print("\n❌ 测试失败")
        else:
            failed += 1
            print("\n❌ 测试失败: 无输出")
        
        # 等待一段时间再进行下一个测试
        if i < len(TEST_MESSAGES) - 1:
            time.sleep(2)
    
    # 汇总报告
    print(f"\n{'='*60}")
    print("测试汇总报告")
    print(f"{'='*60}")
    print(f"  总测试数: {len(TEST_MESSAGES)}")
    print(f"  通过: {passed}")
    print(f"  失败: {failed}")
    
    if failed == 0:
        print("\n✅ 所有测试通过！输出质量良好。")
        return 0
    else:
        print(f"\n⚠️ {failed} 个测试失败，请检查输出质量。")
        return 1

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 自定义测试消息
        message = " ".join(sys.argv[1:])
        text, thinking_detected = test_stream_output(message)
        if text:
            analysis = analyze_output(text)
            print_report(text, analysis)
    else:
        # 运行所有测试
        sys.exit(run_tests())
