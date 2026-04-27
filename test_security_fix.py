#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试安全修复是否生效
"""

import sys
import os

# 测试 safe_eval 是否能正确阻止危险代码
def test_safe_eval():
    print("测试 safe_eval 安全功能...")
    try:
        from safe_code_executor import safe_eval
        
        # 正常数学表达式应该可以执行
        result = safe_eval("2 + 3 * 4")
        print(f"  ✓ 正常表达式 2 + 3 * 4 = {result}")
        
        result = safe_eval("sqrt(16) + pow(2, 3)")
        print(f"  ✓ 函数调用 sqrt(16) + pow(2, 3) = {result}")
        
        # 危险代码应该被阻止
        try:
            safe_eval("__import__('os').system('ls')")
            print("  ✗ 危险代码未被阻止！")
            return False
        except ValueError as e:
            print(f"  ✓ 危险代码被阻止: {e}")
        
        return True
    except Exception as e:
        print(f"  ✗ 测试失败: {e}")
        return False

# 测试线程锁是否存在
def test_thread_lock():
    print("\n测试线程锁...")
    try:
        # 读取文件检查锁是否存在
        with open('qwen3_web_final.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'rag_lock = threading.RLock()' in content:
            print("  ✓ rag_lock 已定义")
        else:
            print("  ✗ rag_lock 未定义")
            return False
        
        if 'with rag_lock:' in content:
            count = content.count('with rag_lock:')
            print(f"  ✓ 找到 {count} 处 rag_lock 使用")
        else:
            print("  ✗ 未找到 rag_lock 使用")
            return False
        
        return True
    except Exception as e:
        print(f"  ✗ 测试失败: {e}")
        return False

# 测试 eval 是否被替换
def test_eval_replacement():
    print("\n测试 eval() 替换...")
    try:
        with open('qwen3_web_final.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否还有危险的 eval
        if 'lambda x: str(eval(x.replace("^", "**")))' in content:
            print("  ✗ 仍存在危险的 eval()")
            return False
        else:
            print("  ✓ 危险的 eval() 已被替换")
        
        # 检查是否使用了 safe_eval
        if 'lambda x: str(safe_eval(x.replace("^", "**")))' in content:
            print("  ✓ 已使用 safe_eval 替代")
        else:
            print("  ⚠ 未找到 safe_eval 替代（可能使用其他方式）")
        
        return True
    except Exception as e:
        print(f"  ✗ 测试失败: {e}")
        return False

# 测试 PDF 资源泄漏修复
def test_pdf_fix():
    print("\n测试 PDF 资源泄漏修复...")
    try:
        with open('qwen3_web_final.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否使用了 with 语句
        if 'with fitz.open(file_path) as doc:' in content:
            print("  ✓ PDF 使用 with 语句，资源会自动关闭")
        elif 'doc.close()' in content:
            print("  ⚠ PDF 仍使用手动 close()")
        else:
            print("  ✗ 未找到 PDF 处理代码")
            return False
        
        return True
    except Exception as e:
        print(f"  ✗ 测试失败: {e}")
        return False

if __name__ == '__main__':
    print("=" * 50)
    print("安全修复测试")
    print("=" * 50)
    
    results = []
    results.append(("safe_eval 功能", test_safe_eval()))
    results.append(("线程锁", test_thread_lock()))
    results.append(("eval 替换", test_eval_replacement()))
    results.append(("PDF 资源泄漏", test_pdf_fix()))
    
    print("\n" + "=" * 50)
    print("测试结果汇总")
    print("=" * 50)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {name}")
    
    all_passed = all(r for _, r in results)
    if all_passed:
        print("\n🎉 所有安全修复测试通过！")
        sys.exit(0)
    else:
        print("\n⚠️ 部分测试未通过，请检查修复")
        sys.exit(1)
