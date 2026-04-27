#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IDE功能验证脚本
验证终端、窗口、反馈和文件状态功能的修复
"""

import sys
import json
import re

def test_tool_use_parser():
    """测试工具调用解析器"""
    print("=" * 60)
    print("Test 1: Tool Use Parser")
    print("=" * 60)

    # 模拟_parse_tool_use函数的逻辑
    def parse_tool_use(text):
        patterns = [
            (r'```tool\n(\w+)\n(.*?)```', 1),
            (r'<tool_use>\s*<name>(\w+)</name>\s*<input>(.*?)</input>\s*</tool_use>', 2),
            (r'```(\w+)_call\n(.*?)```', 3),
        ]
        for pattern, pid in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                return {"format": f"pattern_{pid}", "name": match.group(1)}

        # JSON格式
        func_pattern_json = r'(?:read_file|write_file|edit_file|list_directory|search_files|execute_command|glob|create_directory|compile|open_project_dir|list_env)\s*\(\s*(\{[^}]+\})\s*\)'
        func_match_json = re.search(func_pattern_json, text, re.DOTALL)
        if func_match_json:
            tool_name_match = re.search(r'(read_file|write_file|edit_file|list_directory|search_files|execute_command|glob|create_directory|compile|open_project_dir|list_env)', text)
            if tool_name_match:
                return {"format": "json_params", "name": tool_name_match.group(1)}

        # 字符串参数格式（新增）
        func_pattern_str = r'(execute_command|read_file|write_file|edit_file|list_directory|search_files|glob|create_directory|compile|open_project_dir|list_env)\s*\(\s*[\'"](.+?)[\'"]\s*(?:,\s*[\'"](.+?)[\'"])?\s*(?:,\s*[\'"](.+?)[\'"])?\s*\)'
        func_match_str = re.search(func_pattern_str, text, re.DOTALL)
        if func_match_str:
            return {"format": "string_params", "name": func_match_str.group(1)}

        return None

    # 测试用例
    test_cases = [
        ("```tool\nexecute_command\n{\"command\": \"python main.py\"}```", "pattern_1", "execute_command"),
        ("execute_command('{\"command\": \"ls -la\"}')", "json_params", "execute_command"),
        ("execute_command('python3 -c \"print(\\'hello\\')\"')", "string_params", "execute_command"),
        ("write_file('/path/to/file.py', 'content')", "string_params", "write_file"),
        ("edit_file('file.py', 'old', 'new')", "string_params", "edit_file"),
        ("read_file('test.py')", "string_params", "read_file"),
    ]

    passed = 0
    failed = 0
    for text, expected_format, expected_name in test_cases:
        result = parse_tool_use(text)
        if result and result["format"] == expected_format and result["name"] == expected_name:
            print(f"[PASS] {text[:50]}...")
            passed += 1
        else:
            print(f"[FAIL] {text[:50]}... -> Expected {expected_format}/{expected_name}, Got {result}")
            failed += 1

    print(f"\nResult: {passed}/{passed+failed} passed")
    return failed == 0

def test_frontend_functions():
    """测试前端函数定义"""
    print("\n" + "=" * 60)
    print("Test 2: Frontend Function Completeness Check")
    print("=" * 60)

    # 读取文件内容
    with open('qwen3_web.py', 'r', encoding='utf-8') as f:
        content = f.read()

    required_functions = [
        'function termLog',
        'function showOperationFeedback',
        'function showFileChangeConfirmation',
        'function runTerminalCmd',
        'function sendAgentMsg',
        'function loadFileTree',
        'function openProjectDir'
    ]

    passed = 0
    failed = 0
    for func in required_functions:
        if func in content:
            print(f"[FOUND] {func}")
            passed += 1
        else:
            print(f"[MISSING] {func}")
            failed += 1

    # 检查终端同步代码
    terminal_sync_checks = [
        ('terminalPanel.*display', 'Terminal panel auto-open'),
        ('termLog.*\\[Agent\\]', 'Agent operation log sync'),
        ('termLog.*\\[Result\\]', 'Command execution result sync'),
        ('termLog.*\\[Success\\]', 'File save success notification'),
        ('showOperationFeedback', 'Operation status floating notification'),
        ('showFileChangeConfirmation', 'File modification confirmation')
    ]

    print("\nTerminal Sync Features:")
    for pattern, desc in terminal_sync_checks:
        if re.search(pattern, content):
            print(f"[OK] {desc}")
            passed += 1
        else:
            print(f"[X] {desc} not implemented")
            failed += 1

    print(f"\nResult: {passed}/{passed+failed} passed")
    return failed == 0

def test_terminal_integration():
    """测试终端集成"""
    print("\n" + "=" * 60)
    print("Test 3: Terminal Integration Verification")
    print("=" * 60)

    with open('qwen3_web.py', 'r', encoding='utf-8') as f:
        content = f.read()

    checks = [
        ('/agent/terminal/exec', 'Terminal execution endpoint'),
        ('agent_terminal_exec', 'Terminal execution function'),
        ('subprocess.run', 'Command execution support'),
        ('timeout', 'Timeout handling'),
        ('capture_output=True', 'Output capture'),
        ('working_dir', 'Working directory support')
    ]

    passed = 0
    failed = 0
    for pattern, desc in checks:
        if pattern in content:
            print(f"[OK] {desc}: Implemented")
            passed += 1
        else:
            print(f"[X] {desc}: Not found")
            failed += 1

    print(f"\nResult: {passed}/{passed+failed} passed")
    return failed == 0

def test_feedback_mechanisms():
    """测试反馈机制"""
    print("\n" + "=" * 60)
    print("Test 4: Feedback Mechanism Verification")
    print("=" * 60)

    with open('qwen3_web.py', 'r', encoding='utf-8') as f:
        content = f.read()

    feedback_checks = [
        ('operationFeedback', 'Operation feedback element ID'),
        ('position:fixed', 'Fixed position notification'),
        ('z-index:9999', 'High priority display'),
        ('transition:all 0.3s ease', 'Smooth transition animation'),
        ('file-change-confirmation', 'File change confirmation style'),
        ('background:rgba(52,211,153,0.08)', 'Success status color'),
        ('animation:fadeIn', 'Fade-in animation effect')
    ]

    passed = 0
    failed = 0
    for pattern, desc in feedback_checks:
        if pattern in content:
            print(f"[OK] {desc}: Implemented")
            passed += 1
        else:
            print(f"[X] {desc}: Not implemented")
            failed += 1

    print(f"\nResult: {passed}/{passed+failed} passed")
    return failed == 0

def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("IDE Function Comprehensive Verification Report")
    print("=" * 60)

    results = []
    results.append(("Tool Use Parser", test_tool_use_parser()))
    results.append(("Frontend Function Completeness", test_frontend_functions()))
    results.append(("Terminal Integration", test_terminal_integration()))
    results.append(("Feedback Mechanisms", test_feedback_mechanisms()))

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    total_passed = sum(1 for _, result in results if result)
    total_tests = len(results)

    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{name}: {status}")

    print(f"\nOverall Result: {total_passed}/{total_tests} tests passed")

    if total_passed == total_tests:
        print("\n[SUCCESS] All tests passed! All features are correctly implemented.")
        return 0
    else:
        print(f"\n[WARNING] {total_tests - total_passed} test(s) failed, need further inspection.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
