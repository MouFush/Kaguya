#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辉夜AI - 增强记忆系统API路由
需要添加到主应用 qwen3_web_integrated.py 中
"""

# ==================== 增强记忆系统API路由 ====================

@app.route('/memory/device/register', methods=['POST'])
def memory_device_register():
    """注册设备并获取设备ID"""
    if not ENHANCED_MEMORY_AVAILABLE:
        return jsonify({"success": False, "error": "增强记忆系统未加载"})
    try:
        device_id = get_or_create_device_id(request)
        data = request.json or {}
        enable_memory = data.get('enable_memory', False)
        
        config = device_memory_manager.register_device(device_id, enable_memory)
        return jsonify({
            "success": True,
            "device_id": device_id,
            "memory_mode_enabled": config.memory_mode_enabled
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/memory/device/toggle', methods=['POST'])
def memory_device_toggle():
    """切换设备记忆模式"""
    if not ENHANCED_MEMORY_AVAILABLE:
        return jsonify({"success": False, "error": "增强记忆系统未加载"})
    try:
        device_id = get_or_create_device_id(request)
        data = request.json or {}
        enabled = data.get('enabled', False)
        
        success = device_memory_manager.toggle_memory_mode(device_id, enabled)
        return jsonify({
            "success": success,
            "device_id": device_id,
            "memory_mode_enabled": enabled
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/memory/device/status')
def memory_device_status():
    """获取设备记忆状态"""
    if not ENHANCED_MEMORY_AVAILABLE:
        return jsonify({"success": False, "error": "增强记忆系统未加载"})
    try:
        device_id = get_or_create_device_id(request)
        stats = device_memory_manager.get_memory_stats(device_id)
        return jsonify({"success": True, "stats": stats})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/memory/device/memories')
def memory_device_memories():
    """获取设备记忆列表"""
    if not ENHANCED_MEMORY_AVAILABLE:
        return jsonify({"success": False, "error": "增强记忆系统未加载"})
    try:
        device_id = get_or_create_device_id(request)
        memory_type = request.args.get('type')
        limit = int(request.args.get('limit', 100))
        
        memories = device_memory_manager.get_memories(device_id, memory_type, limit)
        return jsonify({
            "success": True,
            "memories": [
                {
                    "id": m.id,
                    "content": m.content,
                    "type": m.memory_type,
                    "created_at": m.created_at.isoformat(),
                    "access_count": m.access_count
                }
                for m in memories
            ]
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/memory/device/distilled')
def memory_device_distilled():
    """获取设备蒸馏记忆"""
    if not ENHANCED_MEMORY_AVAILABLE:
        return jsonify({"success": False, "error": "增强记忆系统未加载"})
    try:
        device_id = get_or_create_device_id(request)
        limit = int(request.args.get('limit', 50))
        
        memories = device_memory_manager.get_distilled_memories(device_id, limit)
        return jsonify({
            "success": True,
            "distilled_memories": [
                {
                    "id": m.id,
                    "distilled_content": m.distilled_content,
                    "key_facts": m.key_facts,
                    "user_preferences": m.user_preferences,
                    "conclusions": m.conclusions,
                    "importance_score": m.importance_score
                }
                for m in memories
            ]
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/memory/device/delete/<memory_id>', methods=['DELETE'])
def memory_device_delete(memory_id):
    """删除单条记忆"""
    if not ENHANCED_MEMORY_AVAILABLE:
        return jsonify({"success": False, "error": "增强记忆系统未加载"})
    try:
        device_id = get_or_create_device_id(request)
        success = device_memory_manager.delete_memory(device_id, memory_id)
        return jsonify({"success": success})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/memory/device/clear', methods=['POST'])
def memory_device_clear():
    """清空设备所有记忆"""
    if not ENHANCED_MEMORY_AVAILABLE:
        return jsonify({"success": False, "error": "增强记忆系统未加载"})
    try:
        device_id = get_or_create_device_id(request)
        data = request.json or {}
        include_distilled = data.get('include_distilled', True)
        
        count = device_memory_manager.clear_all_memories(device_id, include_distilled)
        return jsonify({"success": True, "deleted_count": count})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/memory/device/delete_cache', methods=['POST'])
def memory_device_delete_cache():
    """完全删除设备缓存"""
    if not ENHANCED_MEMORY_AVAILABLE:
        return jsonify({"success": False, "error": "增强记忆系统未加载"})
    try:
        device_id = get_or_create_device_id(request)
        success = device_memory_manager.delete_device_cache(device_id)
        return jsonify({"success": success})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/memory/devices')
def memory_devices_list():
    """列出所有设备"""
    if not ENHANCED_MEMORY_AVAILABLE:
        return jsonify({"success": False, "error": "增强记忆系统未加载"})
    try:
        devices = device_memory_manager.list_all_devices()
        return jsonify({"success": True, "devices": devices})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
