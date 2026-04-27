"""
输出质量监控脚本
用于检测和诊断 AI 输出中的段落混乱和中英文混合问题
"""

import re
import json
import urllib.request
import time
from datetime import datetime

def test_stream_output(message="你好，请介绍一下你自己"):
    """测试流式输出"""
    print(f"\n{'='*60}")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"测试消息: {message}")
    print(f"{'='*60}\n")
    
    url = "http://127.0.0.1:5000/stream"
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
                            print(f"[Chunk {chunk_count}] {repr(content)}")
                        if chunk_data.get('done'):
                            print(f"\n[完成] 总共 {chunk_count} 个 chunks")
                    except json.JSONDecodeError as e:
                        print(f"[JSON错误] {e}: {line}")
        
        return full_content
        
    except Exception as e:
        print(f"[请求错误] {e}")
        return None

def analyze_output(text):
    """分析输出质量"""
    if not text:
        print("\n[分析] 无输出内容")
        return
    
    print(f"\n{'='*60}")
    print("输出质量分析")
    print(f"{'='*60}")
    
    # 1. 基本统计
    total_chars = len(text)
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    english_chars = len(re.findall(r'[a-zA-Z]', text))
    numbers = len(re.findall(r'[0-9]', text))
    punctuation = len(re.findall(r'[，。！？、；：""''（）【】《》\.,!?;:\'\"\(\)\[\]<>]', text))
    
    print(f"\n[基本统计]")
    print(f"  总字符数: {total_chars}")
    print(f"  中文字符: {chinese_chars} ({chinese_chars/total_chars*100:.1f}%)")
    print(f"  英文字符: {english_chars} ({english_chars/total_chars*100:.1f}%)")
    print(f"  数字: {numbers}")
    print(f"  标点符号: {punctuation}")
    
    # 2. 段落分析
    paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
    print(f"\n[段落分析]")
    print(f"  段落数: {len(paragraphs)}")
    for i, p in enumerate(paragraphs[:5]):  # 只显示前5个段落
        print(f"  段落 {i+1}: {p[:50]}{'...' if len(p) > 50 else ''}")
    
    # 3. 检测中英文混合问题
    print(f"\n[中英文混合检测]")
    mixed_sentences = []
    sentences = re.split(r'[。！？\n]', text)
    for s in sentences:
        s = s.strip()
        if s:
            has_chinese = bool(re.search(r'[\u4e00-\u9fff]', s))
            has_english = bool(re.search(r'[a-zA-Z]{2,}', s))  # 至少2个连续英文字母
            if has_chinese and has_english:
                mixed_sentences.append(s)
    
    if mixed_sentences:
        print(f"  发现 {len(mixed_sentences)} 个中英文混合句子:")
        for i, s in enumerate(mixed_sentences[:3]):
            print(f"    {i+1}. {s[:80]}{'...' if len(s) > 80 else ''}")
    else:
        print(f"  未发现中英文混合问题")
    
    # 4. 检测段落混乱
    print(f"\n[段落混乱检测]")
    issues = []
    
    # 检测不完整的句子（没有以标点结尾）
    for i, p in enumerate(paragraphs):
        if p and not re.search(r'[。！？\.\!\?]$', p):
            issues.append(f"段落 {i+1} 未以标点结尾: {p[:50]}...")
    
    # 检测过短的段落（可能是被错误分割）
    short_paragraphs = [p for p in paragraphs if len(p) < 5]
    if short_paragraphs:
        issues.append(f"发现 {len(short_paragraphs)} 个过短段落")
    
    # 检测重复内容
    if len(paragraphs) != len(set(paragraphs)):
        issues.append("发现重复段落")
    
    if issues:
        print(f"  发现 {len(issues)} 个问题:")
        for issue in issues[:5]:
            print(f"    - {issue}")
    else:
        print(f"  未发现段落混乱问题")
    
    # 5. 完整输出
    print(f"\n[完整输出]")
    print("-" * 60)
    print(text)
    print("-" * 60)
    
    return {
        'total_chars': total_chars,
        'chinese_ratio': chinese_chars/total_chars if total_chars > 0 else 0,
        'english_ratio': english_chars/total_chars if total_chars > 0 else 0,
        'paragraph_count': len(paragraphs),
        'mixed_sentences': len(mixed_sentences),
        'issues': issues
    }

def monitor_continuous(interval=30, max_tests=10):
    """持续监控"""
    test_messages = [
        "你好，请介绍一下你自己",
        "请用中文写一首关于春天的诗",
        "请用英文写一段关于人工智能的介绍",
        "请解释什么是机器学习",
        "请写一个简短的故事"
    ]
    
    results = []
    for i in range(max_tests):
        message = test_messages[i % len(test_messages)]
        output = test_stream_output(message)
        if output:
            analysis = analyze_output(output)
            results.append(analysis)
        
        if i < max_tests - 1:
            print(f"\n等待 {interval} 秒后进行下一次测试...")
            time.sleep(interval)
    
    # 汇总报告
    print(f"\n{'='*60}")
    print("监控汇总报告")
    print(f"{'='*60}")
    
    if results:
        avg_chinese = sum(r['chinese_ratio'] for r in results) / len(results)
        avg_english = sum(r['english_ratio'] for r in results) / len(results)
        total_issues = sum(len(r['issues']) for r in results)
        
        print(f"  测试次数: {len(results)}")
        print(f"  平均中文比例: {avg_chinese*100:.1f}%")
        print(f"  平均英文比例: {avg_english*100:.1f}%")
        print(f"  总问题数: {total_issues}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "continuous":
            interval = int(sys.argv[2]) if len(sys.argv) > 2 else 30
            max_tests = int(sys.argv[3]) if len(sys.argv) > 3 else 10
            monitor_continuous(interval, max_tests)
        else:
            # 自定义测试消息
            output = test_stream_output(" ".join(sys.argv[1:]))
            if output:
                analyze_output(output)
    else:
        # 单次测试
        output = test_stream_output()
        if output:
            analyze_output(output)
