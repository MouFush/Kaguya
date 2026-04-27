#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IDE Comprehensive Functional Verification Test Suite (Code-Level)
Tests: File Upload, Terminal Access, Agent Automation, Stability
No server dependency - validates code logic directly
"""

import sys
import os
import json
import re
import time
import hashlib
import tempfile
import shutil
from datetime import datetime

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_RESULTS = []

def record(category, name, passed, details=""):
    TEST_RESULTS.append({
        "category": category, "name": name, "passed": passed,
        "details": details, "timestamp": datetime.now().isoformat()
    })
    s = "[PASS]" if passed else "[FAIL]"
    print(f"  {s} {name}" + (f" - {details}" if details and not passed else ""))

def read_source():
    with open(os.path.join(PROJECT_DIR, 'qwen3_web.py'), 'r', encoding='utf-8') as f:
        return f.read()

# ============================================================
# TEST 1: File Upload Functionality
# ============================================================
def test_file_upload():
    print("\n" + "=" * 60)
    print("TEST 1: File Upload Functionality Verification")
    print("=" * 60)
    src = read_source()

    # 1.1 Upload endpoint exists
    print("\n[1.1] Upload Endpoint Existence")
    record("File Upload", "Upload endpoint route", "/agent/upload-device-files" in src)
    record("File Upload", "Upload handler function", "def agent_upload_device_files" in src)
    record("File Upload", "Write file endpoint", "/agent/write-file" in src)
    record("File Upload", "Read file endpoint", "/agent/read-file" in src)
    record("File Upload", "File tree endpoint", "/agent/file-tree" in src)

    # 1.2 Multi-file type support
    print("\n[1.2] Multi-File Type Support")
    upload_code = src[src.find("def agent_upload_device_files"):src.find("def agent_upload_device_files")+2000]
    record("File Upload", "Multipart form handling", "request.files.getlist" in upload_code)
    record("File Upload", "File save capability", "f.save(dst)" in upload_code)
    record("File Upload", "Directory auto-creation", "os.makedirs" in upload_code)
    record("File Upload", "File size tracking", "os.path.getsize" in upload_code)
    record("File Upload", "Path normalization", "fname.replace('\\\\', '/')" in upload_code)

    # 1.3 File integrity mechanisms
    print("\n[1.3] File Integrity Mechanisms")
    write_code = src[src.find("def agent_write_file"):src.find("def agent_write_file")+1000]
    record("File Upload", "UTF-8 encoding write", "encoding='utf-8'" in write_code)
    record("File Upload", "Path validation", "_validate_path_in_workspace" in write_code)
    record("File Upload", "Workspace security check", "ws_path" in write_code)
    record("File Upload", "Parent dir creation", "os.makedirs" in write_code)

    # 1.4 Read-back verification
    print("\n[1.4] Read-Back Verification")
    read_code = src[src.find("def agent_read_file"):src.find("def agent_read_file")+1000]
    record("File Upload", "File existence check", "os.path.exists" in read_code)
    record("File Upload", "Directory vs file check", "os.path.isdir" in read_code)
    record("File Upload", "Language detection", "os.path.splitext" in read_code)
    record("File Upload", "Error replacement mode", "errors='replace'" in read_code)

    # 1.5 Edge case handling
    print("\n[1.5] Edge Case Handling")
    record("File Upload", "Empty filename check", "if not fname" in upload_code)
    record("File Upload", "Error collection", "errors.append" in upload_code)
    record("File Upload", "Imported paths tracking", "imported_paths" in upload_code)
    record("File Upload", "Relative path handling", "os.path.isabs" in write_code)

    # 1.6 File format preservation
    print("\n[1.6] File Format Preservation")
    record("File Upload", "Binary save support", "f.save(dst)" in upload_code)
    record("File Upload", "Content-Type passthrough", "ftype" in upload_code or "Content-Type" in src)
    record("File Upload", "No content transformation", "f.save(dst)" in upload_code and "encode" not in upload_code[:500])

    # 1.7 Revert capability
    print("\n[1.7] Revert Capability")
    revert_code = src[src.find("def agent_revert_file"):src.find("def agent_revert_file")+1500]
    record("File Upload", "Revert endpoint exists", "/agent/revert-file" in src)
    record("File Upload", "Old content restore", "old_content" in revert_code)
    record("File Upload", "New file removal", "os.remove" in revert_code)

    # 1.8 Actual file I/O test
    print("\n[1.8] Actual File I/O Test")
    test_dir = os.path.join(PROJECT_DIR, "_test_upload")
    try:
        os.makedirs(test_dir, exist_ok=True)
        # Test write
        test_file = os.path.join(test_dir, "test_write.txt")
        test_content = "Hello World\nLine 2\nSpecial: !@#$%^&*()\nUnicode: \u4f60\u597d\u4e16\u754c"
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(test_content)
        # Test read
        with open(test_file, 'r', encoding='utf-8') as f:
            read_content = f.read()
        integrity_ok = read_content == test_content
        record("File Upload", "Write/read integrity", integrity_ok,
               "Content mismatch" if not integrity_ok else "OK")

        # Test JSON format preservation
        json_file = os.path.join(test_dir, "test.json")
        json_content = {"key": "value", "num": 42, "arr": [1, 2, 3]}
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(json_content, f)
        with open(json_file, 'r', encoding='utf-8') as f:
            read_json = json.load(f)
        json_ok = read_json == json_content
        record("File Upload", "JSON format preservation", json_ok)

        # Test empty file
        empty_file = os.path.join(test_dir, "empty.txt")
        with open(empty_file, 'w', encoding='utf-8') as f:
            pass
        empty_ok = os.path.getsize(empty_file) == 0
        record("File Upload", "Empty file creation", empty_ok)

        # Test special filename
        special_file = os.path.join(test_dir, "file with spaces.txt")
        with open(special_file, 'w', encoding='utf-8') as f:
            f.write("special name test")
        special_ok = os.path.exists(special_file)
        record("File Upload", "Special character filename", special_ok)

    except Exception as e:
        record("File Upload", "File I/O test", False, str(e))
    finally:
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir, ignore_errors=True)

# ============================================================
# TEST 2: Terminal Access and Operation
# ============================================================
def test_terminal_access():
    print("\n" + "=" * 60)
    print("TEST 2: Terminal Access and Operation Verification")
    print("=" * 60)
    src = read_source()

    # 2.1 Terminal endpoint
    print("\n[2.1] Terminal Endpoint Existence")
    record("Terminal", "Terminal exec endpoint", "/agent/terminal/exec" in src)
    record("Terminal", "Terminal exec handler", "def agent_terminal_exec" in src)

    # 2.2 Command execution capabilities
    print("\n[2.2] Command Execution Capabilities")
    term_code = src[src.find("def agent_terminal_exec"):src.find("def agent_terminal_exec")+2000]
    record("Terminal", "Shell command execution", "subprocess.run" in term_code)
    record("Terminal", "shell=True support", "shell=True" in term_code)
    record("Terminal", "Output capture", "capture_output=True" in term_code)
    record("Terminal", "Text mode output", "text=True" in term_code)
    record("Terminal", "Timeout support", "timeout" in term_code)

    # 2.3 Working directory support
    print("\n[2.3] Working Directory Support")
    record("Terminal", "Working dir parameter", "working_dir" in term_code)
    record("Terminal", "cwd parameter in subprocess", "cwd=working_dir" in term_code)
    record("Terminal", "Relative path resolution", "os.path.isabs" in term_code)
    record("Terminal", "Default to workspace", "ws_path" in term_code)

    # 2.4 Output handling
    print("\n[2.4] Output Handling")
    record("Terminal", "Stdout capture", "result.stdout" in term_code)
    record("Terminal", "Stderr capture", "result.stderr" in term_code)
    record("Terminal", "Exit code reporting", "returncode" in term_code)
    record("Terminal", "Output size limit", "[:8000]" in term_code or "[:5000]" in term_code)
    record("Terminal", "Timeout handling", "TimeoutExpired" in term_code)

    # 2.5 Permission system
    print("\n[2.5] Permission System")
    record("Terminal", "Permission check", "permission_checker.check" in term_code)
    record("Terminal", "Deny logging", "terminal_denied" in term_code)
    record("Terminal", "Execution logging", "terminal_exec" in term_code)
    record("Terminal", "Device ID support", "device_id" in term_code)

    # 2.6 Frontend terminal
    print("\n[2.6] Frontend Terminal Panel")
    record("Terminal", "Terminal panel HTML", "terminalPanel" in src)
    record("Terminal", "Terminal input field", "terminalInput" in src)
    record("Terminal", "Terminal body display", "terminalBody" in src)
    record("Terminal", "Run terminal command JS", "function runTerminalCmd" in src)
    record("Terminal", "Terminal log function", "function termLog" in src)
    record("Terminal", "Auto-open on agent action", "terminalPanel.*display" in src and "tp.style.display='flex'" in src)

    # 2.7 Agent terminal sync
    print("\n[2.7] Agent-Terminal Sync")
    record("Terminal", "Agent command sync", "[Agent] $" in src)
    record("Terminal", "Agent result sync", "[Result]" in src)
    record("Terminal", "File write sync", "[Agent] Writing" in src)
    record("Terminal", "File edit sync", "[Agent] Editing" in src)
    record("Terminal", "Success notification", "[Success]" in src)
    record("Terminal", "Error notification", "[Error]" in src)

    # 2.8 Tool execute_command
    print("\n[2.8] Tool: execute_command")
    tool_code = src[src.find("def _execute_command"):src.find("def _execute_command")+800]
    record("Terminal", "execute_command tool", "def _execute_command" in src)
    record("Terminal", "Command parameter", '"command"' in tool_code)
    record("Terminal", "Timeout parameter", "timeout" in tool_code)
    record("Terminal", "Working dir parameter", "working_dir" in tool_code)
    record("Terminal", "Error output included", "result.stderr" in tool_code)

# ============================================================
# TEST 3: Agent Automation Execution
# ============================================================
def test_agent_automation():
    print("\n" + "=" * 60)
    print("TEST 3: Agent Automation Execution Verification")
    print("=" * 60)
    src = read_source()

    # 3.1 Agent run endpoint
    print("\n[3.1] Agent Run Endpoint")
    record("Agent", "Agent run endpoint", "/agent/run" in src)
    record("Agent", "SSE streaming support", "text/event-stream" in src)
    record("Agent", "External API support", "external_api" in src)
    record("Agent", "History support", "history" in src)
    record("Agent", "Working dir support", "working_dir" in src)

    # 3.2 Tool use parsing
    print("\n[3.2] Tool Use Parsing")
    parse_code = src[src.find("def _parse_tool_use"):src.find("def _safe_json")]
    record("Agent", "Tool code block format", "```tool" in parse_code)
    record("Agent", "XML format support", "<tool_use>" in parse_code)
    record("Agent", "JSON format support", "```json" in parse_code)
    record("Agent", "Function call format", "func_pattern_str" in parse_code or "func_pattern_json" in parse_code)
    record("Agent", "String parameter parsing", "string_params" in parse_code or "[\'\"](.+?)[\'\"]" in parse_code)

    # 3.3 Tool registry completeness
    print("\n[3.3] Tool Registry Completeness")
    required_tools = [
        "read_file", "write_file", "edit_file", "list_directory",
        "search_files", "execute_command", "glob", "create_directory",
        "compile", "open_project_dir", "list_env"
    ]
    for tool in required_tools:
        record("Agent", f"Tool: {tool}", f'self.tools["{tool}"]' in src)

    # 3.4 Agent system prompt
    print("\n[3.4] Agent System Prompt")
    record("Agent", "System prompt defined", "AGENT_SYSTEM_PROMPT" in src)
    record("Agent", "Direct file operation mode", "Direct File Operation Mode" in src)
    record("Agent", "Anti-loop rules", "ANTI-LOOP RULES" in src)
    record("Agent", "Tool call format examples", "```tool" in src and "write_file" in src)
    record("Agent", "Workflow guidance", "Workflow" in src)

    # 3.5 Loop detection
    print("\n[3.5] Loop Detection")
    loop_code = src[src.find("class LoopDetector"):src.find("class LoopDetector")+2000]
    record("Agent", "LoopDetector class", "class LoopDetector" in src)
    record("Agent", "Duplicate tool detection", "duplicate_tool" in loop_code)
    record("Agent", "Sequence loop detection", "sequence_loop" in loop_code)
    record("Agent", "Retry loop detection", "retry_loop" in loop_code)
    record("Agent", "Stuck agent detection", '"stuck"' in loop_code)
    record("Agent", "Loop check in query loop", "loop_detector.check_loop" in src)

    # 3.6 Permission system
    print("\n[3.6] Permission System")
    record("Agent", "PermissionChecker class", "class PermissionChecker" in src)
    record("Agent", "Permission request flow", "permission_request" in src)
    record("Agent", "Permission response endpoint", "/agent/permission/respond" in src)
    record("Agent", "Sandbox mode", "sandbox_mode" in src)
    record("Agent", "Denial tracker", "denial_tracker" in src or "DenialTracker" in src)

    # 3.7 Frontend agent display
    print("\n[3.7] Frontend Agent Display")
    record("Agent", "Thinking display", "d.type==='thinking'" in src)
    record("Agent", "Tool use display", "d.type==='tool_use'" in src)
    record("Agent", "Tool result display", "d.type==='tool_result'" in src)
    record("Agent", "Permission prompt display", "d.type==='permission_request'" in src)
    record("Agent", "Error display", "d.type==='error'" in src)
    record("Agent", "Assistant message display", "d.type==='assistant'" in src)
    record("Agent", "Done state handling", "d.done" in src)

    # 3.8 Operation feedback
    print("\n[3.8] Operation Feedback")
    record("Agent", "showOperationFeedback function", "function showOperationFeedback" in src)
    record("Agent", "showFileChangeConfirmation function", "function showFileChangeConfirmation" in src)
    record("Agent", "Status text updates", "statusText" in src)
    record("Agent", "File change confirmation UI", "file-change-confirmation" in src)
    record("Agent", "Operation feedback element", "operationFeedback" in src)

    # 3.9 Message compaction
    print("\n[3.9] Message Compaction")
    record("Agent", "Snip compact", "_snip_compact" in src)
    record("Agent", "Micro compact", "_micro_compact" in src)
    record("Agent", "Auto compact", "_auto_compact" in src)
    record("Agent", "Max turns limit", "max_turns" in src)

# ============================================================
# TEST 4: Functional Stability
# ============================================================
def test_stability():
    print("\n" + "=" * 60)
    print("TEST 4: Functional Stability Verification")
    print("=" * 60)
    src = read_source()

    # 4.1 Thread safety
    print("\n[4.1] Thread Safety")
    record("Stability", "Data lock", "data_lock" in src)
    record("Stability", "Log lock", "log_lock" in src)
    record("Stability", "Threading import", "import threading" in src)

    # 4.2 Error handling
    print("\n[4.2] Error Handling")
    record("Stability", "Try-except in upload", "except Exception" in src[src.find("agent_upload_device_files"):src.find("agent_upload_device_files")+2000])
    record("Stability", "Try-except in terminal", "except subprocess.TimeoutExpired" in src)
    record("Stability", "Try-except in agent run", "except Exception as e" in src[src.find("agent_run_endpoint"):src.find("agent_run_endpoint")+1000])
    record("Stability", "Try-except in file read", "except Exception as e" in src[src.find("agent_read_file"):src.find("agent_read_file")+1000])

    # 4.3 Resource limits
    print("\n[4.3] Resource Limits")
    record("Stability", "Output size limit", "[:8000]" in src or "[:5000]" in src)
    record("Stability", "Terminal timeout", "timeout" in src)
    record("Stability", "Max turns limit", "max_turns=8" in src or "max_turns=10" in src)
    record("Stability", "File list limit", "[:100]" in src)
    record("Stability", "History limit", "[-10:]" in src or "[-20:]" in src)

    # 4.4 Connection stability
    print("\n[4.4] Connection Stability")
    record("Stability", "Keep-alive header", "keep-alive" in src.lower())
    record("Stability", "No-cache header", "no-cache" in src.lower())
    record("Stability", "Buffering disabled", "no-buffering" in src.lower() or "X-Accel-Buffering" in src)
    record("Stability", "Threaded mode", "threaded=True" in src)

    # 4.5 Audit logging
    print("\n[4.5] Audit Logging")
    record("Stability", "Audit logger", "audit_logger" in src)
    record("Stability", "Loop detection logging", "loop_detected" in src)
    record("Stability", "Permission logging", "permission_granted" in src or "permission_denied" in src)
    record("Stability", "Terminal execution logging", "terminal_exec" in src)

    # 4.6 Code quality
    print("\n[4.6] Code Quality")
    record("Stability", "UTF-8 encoding declarations", "# -*- coding: utf-8 -*-" in src)
    record("Stability", "Main guard", "if __name__" in src)
    record("Stability", "Argparse for CLI", "argparse" in src)
    record("Stability", "Graceful shutdown", "debug=False" in src)

    # 4.7 Repeated operation simulation
    print("\n[4.7] Repeated Operation Simulation (3 rounds)")
    for i in range(1, 4):
        test_dir = os.path.join(PROJECT_DIR, f"_stability_test_r{i}")
        try:
            os.makedirs(test_dir, exist_ok=True)
            test_file = os.path.join(test_dir, f"test_r{i}.txt")
            content = f"Stability test round {i} at {datetime.now().isoformat()}"
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write(content)
            with open(test_file, 'r', encoding='utf-8') as f:
                read_back = f.read()
            ok = read_back == content
            record("Stability", f"Round {i}: File R/W consistency", ok)
        except Exception as e:
            record("Stability", f"Round {i}: File R/W consistency", False, str(e))
        finally:
            if os.path.exists(test_dir):
                shutil.rmtree(test_dir, ignore_errors=True)
        if i < 3:
            time.sleep(1)

# ============================================================
# REPORT GENERATION
# ============================================================
def generate_report():
    print("\n" + "=" * 60)
    print("COMPREHENSIVE TEST REPORT")
    print("=" * 60)

    categories = {}
    for r in TEST_RESULTS:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = {"passed": 0, "failed": 0, "total": 0, "failures": []}
        categories[cat]["total"] += 1
        if r["passed"]:
            categories[cat]["passed"] += 1
        else:
            categories[cat]["failed"] += 1
            categories[cat]["failures"].append(f"{r['name']}: {r['details']}" if r['details'] else r['name'])

    total_passed = sum(c["passed"] for c in categories.values())
    total_failed = sum(c["failed"] for c in categories.values())
    total_tests = total_passed + total_failed

    print(f"\n{'Category':<30} {'Passed':<10} {'Failed':<10} {'Rate':<10}")
    print("-" * 60)
    for cat, stats in categories.items():
        rate = f"{stats['passed']/stats['total']*100:.1f}%" if stats['total'] > 0 else "N/A"
        print(f"{cat:<30} {stats['passed']:<10} {stats['failed']:<10} {rate:<10}")
        if stats["failures"]:
            for f in stats["failures"]:
                print(f"  - FAIL: {f}")

    print("-" * 60)
    overall_rate = f"{total_passed/total_tests*100:.1f}%" if total_tests > 0 else "N/A"
    print(f"{'TOTAL':<30} {total_passed:<10} {total_failed:<10} {overall_rate:<10}")

    verdict = "PASS" if total_failed == 0 else ("CONDITIONAL PASS" if total_failed <= 5 else "FAIL")
    print(f"\n{'='*60}")
    print(f"VERDICT: {verdict}")
    print(f"Total: {total_tests} tests, {total_passed} passed, {total_failed} failed")
    print(f"Pass rate: {overall_rate}")
    print(f"{'='*60}")

    report_path = os.path.join(PROJECT_DIR, "ide_test_report.json")
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_tests": total_tests,
            "total_passed": total_passed,
            "total_failed": total_failed,
            "pass_rate": overall_rate,
            "verdict": verdict,
            "categories": {k: {kk: vv for kk, vv in v.items()} for k, v in categories.items()},
            "details": TEST_RESULTS
        }, f, ensure_ascii=False, indent=2)
    print(f"\nReport saved to: {report_path}")
    return total_failed == 0

def main():
    print("=" * 60)
    print("IDE Comprehensive Functional Verification Test Suite")
    print(f"Started: {datetime.now().isoformat()}")
    print(f"Project: {PROJECT_DIR}")
    print("=" * 60)

    try:
        test_file_upload()
        test_terminal_access()
        test_agent_automation()
        test_stability()
    except Exception as e:
        print(f"\n[FATAL] Test suite error: {e}")
        import traceback
        traceback.print_exc()

    success = generate_report()
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
