#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辉夜IDE 启动引导层 (Kaguya Bootstrap)
负责初始化所有kaguya_*模块、注册Flask API路由、注入前端JS模块

使用方式:
  方式1: 在qwen3_web.py顶部添加: from kaguya_bootstrap import *
  方式2: 作为独立入口运行: python kaguya_bootstrap.py --port 5000
  方式3: 通过Flask蓝图注册到现有app
"""

import os
import sys
import json
import uuid
import time
import secrets
import queue
import threading
from datetime import datetime
from functools import wraps

try:
    from flask import Flask, request, g, jsonify, Response
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False

KAGUYA_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, KAGUYA_DIR)


class KaguyaBootstrap:
    _instance = None
    _singleton_created = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._singleton_created:
            return
        self._app = None
        self._feature_flags = None
        self._hook_manager = None
        self._agent_registry = None
        self._agent_executor = None
        self._agent_runner = None
        self._skill_loader = None
        self._skill_tool = None
        self._account_manager = None
        self._acp_bridge = None
        self._acp_sessions = {}
        self._permission_manager = None
        self._tool_executor = None
        self._init_errors = []
        self._systems_initialized = False
        self._singleton_created = True

    def initialize(self, app=None):
        if app:
            self._app = app
        self._load_feature_flags()
        self._load_hooks()
        self._load_permission_system()
        self._load_agent_system()
        self._load_skill_system()
        self._load_account_system()
        self._load_tool_executor()
        self._load_acp_system()
        self._systems_initialized = True
        return self

    def get_status(self):
        return {
            "initialized": self._systems_initialized,
            "errors": self._init_errors,
            "systems": {
                "feature_flags": self._feature_flags is not None,
                "hooks": self._hook_manager is not None,
                "agents": self._agent_registry is not None,
                "skills": self._skill_loader is not None,
                "accounts": self._account_manager is not None,
                "acp": self._acp_bridge is not None,
                "permissions": self._permission_manager is not None,
            },
        }

    def _safe_import(self, module_name):
        try:
            mod = __import__(module_name)
            for part in module_name.split('.')[1:]:
                mod = getattr(mod, part)
            return mod
        except ImportError as e:
            self._init_errors.append(f"Import {module_name}: {e}")
            return None
        except Exception as e:
            self._init_errors.append(f"Load {module_name}: {e}")
            return None

    def _load_feature_flags(self):
        ffm = self._safe_import("kaguya_feature_flags")
        if ffm:
            try:
                self._feature_flags = ffm.FeatureFlagManager()
                self._feature_flags.enable("skills_system")
                self._feature_flags.enable("acp_protocol")
                self._feature_flags.enable("enhanced_accounts")
                self._feature_flags.enable("frontend_modules")
            except Exception as e:
                self._init_errors.append(f"FeatureFlags init: {e}")

    def _load_hooks(self):
        hm = self._safe_import("kaguya_hooks")
        if hm:
            try:
                self._hook_manager = hm.HookManager()
            except Exception as e:
                self._init_errors.append(f"Hooks init: {e}")

    def _load_agent_system(self):
        agents_mod = self._safe_import("kaguya_agents")
        if agents_mod and self._hook_manager:
            try:
                self._agent_registry, self._agent_executor, self._agent_runner = \
                    agents_mod.create_agent_system(
                        hook_manager=self._hook_manager,
                        permission_manager=self._permission_manager,
                    )
            except Exception as e:
                self._init_errors.append(f"Agent system init: {e}")
        elif agents_mod:
            try:
                self._agent_registry, self._agent_executor, self._agent_runner = \
                    agents_mod.create_agent_system(
                        permission_manager=self._permission_manager,
                    )
            except Exception as e:
                self._init_errors.append(f"Agent system init: {e}")

    def _load_skill_system(self):
        skills_mod = self._safe_import("kaguya_skills")
        if skills_mod:
            try:
                skill_dir = os.path.join(KAGUYA_DIR, ".kaguya", "skills")
                self._skill_loader, self._skill_tool = skills_mod.create_skill_system(
                    config_dir=skill_dir
                )
                self._skill_loader.load_all_skills(cwd=KAGUYA_DIR)
            except Exception as e:
                self._init_errors.append(f"Skill system init: {e}")

    def _load_account_system(self):
        acc_mod = self._safe_import("kaguya_accounts")
        if acc_mod:
            try:
                acc_dir = os.path.join(KAGUYA_DIR, ".kaguya", "accounts")
                secret = os.environ.get("KAGUYA_SECRET_KEY", None)
                self._account_manager = acc_mod.create_account_manager(
                    data_dir=acc_dir, secret_key=secret
                )
            except Exception as e:
                self._init_errors.append(f"Account system init: {e}")

    def _load_acp_system(self):
        acp_mod = self._safe_import("kaguya_acp")
        if acp_mod:
            try:
                self._acp_bridge = acp_mod.create_acp_http_bridge(
                    permission_manager=self._permission_manager,
                )
            except Exception as e:
                self._init_errors.append(f"ACP system init: {e}")

    def _load_permission_system(self):
        perm_mod = self._safe_import("kaguya_permissions")
        if perm_mod:
            try:
                self._permission_manager = perm_mod.create_permission_manager()
            except Exception as e:
                self._init_errors.append(f"Permission system init: {e}")

    def _load_tool_executor(self):
        te_mod = self._safe_import("kaguya_tool_executor")
        if te_mod:
            try:
                self._tool_executor = te_mod.create_tool_executor(
                    permission_manager=self._permission_manager,
                    hook_manager=self._hook_manager,
                )
            except Exception as e:
                self._init_errors.append(f"Tool executor init: {e}")


bootstrap = KaguyaBootstrap()


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not HAS_FLASK:
            return f(*args, **kwargs)
        if bootstrap._account_manager:
            token = None
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
            elif request.args.get("token"):
                token = request.args.get("token")

            if token:
                payload = bootstrap._account_manager._jwt.validate_token(token)
                if payload:
                    g.user_id = payload.get("sub")
                    g.user_role = payload.get("role")
                    return f(*args, **kwargs)

            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)


def register_routes(app):
    bootstrap._app = app
    if not bootstrap._systems_initialized:
        bootstrap.initialize(app)

    _register_acp_routes(app)
    _register_agent_routes(app)
    _register_skill_routes(app)
    _register_account_routes(app)
    _register_system_routes(app)
    _register_permission_routes(app)

    print("[KAGUYA] All API routes registered successfully")


def _register_acp_routes(app):
    @app.route('/acp/status', methods=['GET'])
    def acp_status():
        if not bootstrap._acp_bridge:
            return jsonify({"status": "not_initialized"}), 503
        sessions = bootstrap._acp_bridge.handle_list_sessions()
        return jsonify({
            "status": "running",
            "active_sessions": len(sessions.get("sessions", [])),
        })

    @app.route('/acp/initialize', methods=['POST'])
    def acp_initialize():
        if not bootstrap._acp_bridge:
            return jsonify({"error": "ACP not initialized"}), 503
        result = bootstrap._acp_bridge.handle_initialize()
        return jsonify(result)

    @app.route('/acp/session/new', methods=['POST'])
    def acp_new_session():
        if not bootstrap._acp_bridge:
            return jsonify({"error": "ACP not initialized"}), 503
        data = request.get_json() or {}
        result = bootstrap._acp_bridge.handle_new_session(data)
        session_id = result.get("sessionId")
        if session_id:
            bootstrap._acp_sessions[session_id] = {
                "created_at": datetime.utcnow().isoformat(),
                "cwd": data.get("cwd", ""),
            }
        return jsonify(result)

    @app.route('/acp/prompt', methods=['POST'])
    def acp_prompt():
        if not bootstrap._acp_bridge:
            return jsonify({"error": "ACP not initialized"}), 503
        data = request.get_json() or {}
        session_id = data.get("session_id")
        prompt = data.get("prompt", [])

        def on_update(sid, event):
            pass

        result = bootstrap._acp_bridge.handle_prompt(session_id, prompt, on_update)
        return jsonify(result)

    @app.route('/acp/cancel', methods=['POST'])
    def acp_cancel():
        if not bootstrap._acp_bridge:
            return jsonify({"error": "ACP not initialized"}), 503
        data = request.get_json() or {}
        result = bootstrap._acp_bridge.handle_cancel(data.get("session_id"))
        return jsonify(result)

    @app.route('/acp/sessions', methods=['GET'])
    def acp_list_sessions():
        if not bootstrap._acp_bridge:
            return jsonify({"error": "ACP not initialized"}), 503
        result = bootstrap._acp_bridge.handle_list_sessions()
        return jsonify(result)

    @app.route('/acp/session/close', methods=['POST'])
    def acp_close_session():
        if not bootstrap._acp_bridge:
            return jsonify({"error": "ACP not initialized"}), 503
        data = request.get_json() or {}
        sid = data.get("session_id")
        result = bootstrap._acp_bridge.handle_close_session(sid)
        bootstrap._acp_sessions.pop(sid, None)
        return jsonify(result)

    @app.route('/acp/mode', methods=['POST'])
    def acp_set_mode():
        if not bootstrap._acp_bridge:
            return jsonify({"error": "ACP not initialized"}), 503
        data = request.get_json() or {}
        result = bootstrap._acp_bridge.handle_set_mode(
            data.get("session_id"), data.get("mode_id")
        )
        return jsonify(result)

    @app.route('/acp/model', methods=['POST'])
    def acp_set_model():
        if not bootstrap._acp_bridge:
            return jsonify({"error": "ACP not initialized"}), 503
        data = request.get_json() or {}
        result = bootstrap._acp_bridge.handle_set_model(
            data.get("session_id"), data.get("model_id")
        )
        return jsonify(result)


def _register_agent_routes(app):
    @app.route('/agents/list', methods=['GET'])
    def agents_list():
        if not bootstrap._agent_registry:
            return jsonify({"error": "Agent system not initialized"}), 503
        agents = bootstrap._agent_registry.list_agents()
        result = []
        for a in agents:
            result.append({
                "agent_type": a.agent_type,
                "when_to_use": a.when_to_use,
                "model": a.model,
                "tools": a.tools,
                "disallowed_tools": a.disallowed_tools,
                "background": a.background,
                "source": a.source,
            })
        return jsonify({"agents": result})

    @app.route('/agents/execute', methods=['POST'])
    def agents_execute():
        if not bootstrap._agent_executor:
            return jsonify({"error": "Agent system not initialized"}), 503
        data = request.get_json() or {}
        directive = data.get("directive", "")
        agent_type = data.get("agent_type", "general-purpose")
        run_in_background = data.get("run_in_background", False)

        ctx = None
        if bootstrap._agent_executor:
            from kaguya_agents import AgentContext
            ctx = AgentContext(
                session_id=f"api_{uuid.uuid4().hex[:12]}",
                working_directory=data.get("cwd", KAGUYA_DIR),
            )

        if run_in_background and bootstrap._agent_runner:
            task_id = bootstrap._agent_runner.run_async(
                directive, agent_type, context=ctx
            )
            return jsonify({"task_id": task_id, "status": "running"})

        result = bootstrap._agent_executor.execute(directive, agent_type, context=ctx)
        return jsonify({
            "success": result.success,
            "output": result.output[:10000],
            "agent_type": result.agent_type,
            "duration_ms": result.duration_ms,
            "files_changed": result.files_changed,
            "error": result.error,
        })

    @app.route('/agents/active', methods=['GET'])
    def agents_active():
        if not bootstrap._agent_executor:
            return jsonify({"active": []})
        active = bootstrap._agent_executor.get_active_agents()
        return jsonify({"active": active})

    @app.route('/agents/cancel', methods=['POST'])
    def agents_cancel():
        if not bootstrap._agent_executor:
            return jsonify({"error": "Agent system not initialized"}), 503
        data = request.get_json() or {}
        ok = bootstrap._agent_executor.cancel_agent(data.get("session_id"))
        return jsonify({"cancelled": ok})


def _register_skill_routes(app):
    @app.route('/skills/list', methods=['GET'])
    def skills_list():
        if not bootstrap._skill_tool:
            return jsonify({"error": "Skill system not initialized"}), 503
        available = bootstrap._skill_tool.list_available()
        all_skills = bootstrap._skill_loader.list_skills()
        result = []
        for s in all_skills:
            result.append({
                "name": s.name,
                "description": s.description,
                "source": s.source.value,
                "context": s.frontmatter.context.value if s.frontmatter else "inline",
                "model": s.frontmatter.model if s.frontmatter else "",
                "user_invocable": s.frontmatter.user_invocable if s.frontmatter else True,
            })
        return jsonify({"skills": result, "available": available})

    @app.route('/skills/execute', methods=['POST'])
    def skills_execute():
        if not bootstrap._skill_tool:
            return jsonify({"error": "Skill system not initialized"}), 503
        data = request.get_json() or {}
        name = data.get("name", "")
        args = data.get("args", "")
        result = bootstrap._skill_tool.execute(name, args)
        return jsonify(result)

    @app.route('/skills/create', methods=['POST'])
    def skills_create():
        if not bootstrap._skill_loader:
            return jsonify({"error": "Skill system not initialized"}), 503
        data = request.get_json() or {}
        name = data.get("name", "")
        description = data.get("description", "")
        content = data.get("content", "")

        if not name or not description:
            return jsonify({"error": "name and description required"}), 400

        try:
            skill = bootstrap._skill_loader.create_skill(name, description, content)
            return jsonify({
                "success": True,
                "skill_name": skill.name,
                "skill_dir": skill.skill_dir,
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/skills/<skill_name>', methods=['DELETE'])
    def skills_delete(skill_name):
        if not bootstrap._skill_loader:
            return jsonify({"error": "Skill system not initialized"}), 503
        ok = bootstrap._skill_loader.delete_skill(skill_name)
        return jsonify({"deleted": ok})


def _register_account_routes(app):
    @app.route('/kaguya/auth/register', methods=['POST'])
    def kaguya_register():
        if not bootstrap._account_manager:
            return jsonify({"error": "Account system not initialized"}), 503
        data = request.get_json() or {}
        username = data.get("username", "")
        password = data.get("password", "")
        email = data.get("email", "")

        account, err = bootstrap._account_manager.create_account(username, password, email)
        if account:
            return jsonify({"success": True, "user_id": account.user_id})
        return jsonify({"error": err}), 400

    @app.route('/kaguya/auth/login', methods=['POST'])
    def kaguya_login():
        if not bootstrap._account_manager:
            return jsonify({"error": "Account system not initialized"}), 503
        data = request.get_json() or {}
        username = data.get("username", "")
        password = data.get("password", "")
        ip = request.remote_addr or ""
        ua = request.user_agent.string[:200] if request.user_agent else ""

        result, err = bootstrap._account_manager.authenticate(username, password, ip, ua)
        if result:
            return jsonify(result)
        return jsonify({"error": err}), 401

    @app.route('/kaguya/auth/logout', methods=['POST'])
    def kaguya_logout():
        if not bootstrap._account_manager:
            return jsonify({})
        from flask import request
        auth_header = request.headers.get("Authorization", "")
        token = auth_header[7:] if auth_header.startswith("Bearer ") else None
        if token:
            bootstrap._account_manager.logout(token)
        return jsonify({"success": True})

    @app.route('/kaguya/auth/password/change', methods=['POST'])
    def kaguya_change_password():
        if not bootstrap._account_manager:
            return jsonify({"error": "Account system not initialized"}), 503
        data = request.get_json() or {}
        user_id = data.get("user_id", "")
        old_password = data.get("old_password", "")
        new_password = data.get("new_password", "")

        ok, err = bootstrap._account_manager.change_password(user_id, old_password, new_password)
        if ok:
            return jsonify({"success": True})
        return jsonify({"error": err}), 400

    @app.route('/kaguya/auth/password/reset-request', methods=['POST'])
    def kaguya_reset_request():
        if not bootstrap._account_manager:
            return jsonify({"error": "Account system not initialized"}), 503
        data = request.get_json() or {}
        username = data.get("username", "")
        ip = request.remote_addr or ""
        ok, token = bootstrap._account_manager.request_password_reset(username, ip)
        return jsonify({"success": ok, "reset_token": token if ok else ""})

    @app.route('/kaguya/auth/password/reset', methods=['POST'])
    def kaguya_reset_password():
        if not bootstrap._account_manager:
            return jsonify({"error": "Account system not initialized"}), 503
        data = request.get_json() or {}
        reset_token = data.get("reset_token", "")
        new_password = data.get("new_password", "")
        ok, err = bootstrap._account_manager.reset_password(reset_token, new_password)
        if ok:
            return jsonify({"success": True})
        return jsonify({"error": err}), 400

    @app.route('/kaguya/auth/account', methods=['GET'])
    def kaguya_get_account():
        if not bootstrap._account_manager:
            return jsonify({"error": "Account system not initialized"}), 503
        user_id = request.args.get("user_id", "")
        account = bootstrap._account_manager.get_account(user_id)
        if account:
            return jsonify(account)
        return jsonify({"error": "Not found"}), 404

    @app.route('/kaguya/auth/accounts', methods=['GET'])
    def kaguya_list_accounts():
        if not bootstrap._account_manager:
            return jsonify({"error": "Account system not initialized"}), 503
        admin_id = request.args.get("admin_user_id", "")
        accounts = bootstrap._account_manager.list_accounts(admin_id)
        if accounts is not None:
            return jsonify({"accounts": accounts})
        return jsonify({"error": "Permission denied"}), 403

    @app.route('/kaguya/auth/audit', methods=['GET'])
    def kaguya_audit_log():
        if not bootstrap._account_manager:
            return jsonify({"error": "Account system not initialized"}), 503
        limit = int(request.args.get("limit", 100))
        audit = bootstrap._account_manager.get_audit_log(limit=limit)
        return jsonify({"audit_log": audit})


def _register_system_routes(app):
    @app.route('/kaguya/system/status', methods=['GET'])
    def kaguya_system_status():
        status = bootstrap.get_status()
        status["version"] = "3.1.0"
        status["python_version"] = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        status["uptime"] = str(datetime.utcnow())
        return jsonify(status)

    @app.route('/kaguya/frontend/js', methods=['GET'])
    def kaguya_frontend_js():
        try:
            frontend_mod = __import__("kaguya_frontend")
            js = frontend_mod.get_frontend_js()
            from flask import Response
            return Response(js, mimetype='application/javascript')
        except ImportError:
            return jsonify({"error": "Frontend module not available"}), 503
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/kaguya/features/flags', methods=['GET'])
    def kaguya_features():
        if not bootstrap._feature_flags:
            return jsonify({"error": "Feature flags not initialized"}), 503
        flags = bootstrap._feature_flags.list_flags()
        return jsonify({"flags": flags})


def _register_permission_routes(app):
    @app.route('/permissions/status', methods=['GET'])
    def permissions_status():
        if not bootstrap._permission_manager:
            return jsonify({"status": "not_initialized"}), 503
        stats = bootstrap._permission_manager.get_stats()
        stats["available_modes"] = bootstrap._permission_manager.get_available_modes()
        return jsonify(stats)

    @app.route('/permissions/mode', methods=['GET', 'POST'])
    def permissions_mode():
        if not bootstrap._permission_manager:
            return jsonify({"error": "Permission system not initialized"}), 503
        if request.method == 'GET':
            session_id = request.args.get("session_id", "")
            if session_id:
                mode = bootstrap._permission_manager.get_session_mode(session_id)
                return jsonify({"session_id": session_id, "mode": mode.value})
            return jsonify({"global_mode": bootstrap._permission_manager.get_global_mode().value})
        data = request.get_json() or {}
        from kaguya_permissions import PermissionMode
        mode_str = data.get("mode", "default")
        session_id = data.get("session_id", "")
        try:
            mode = PermissionMode(mode_str)
        except ValueError:
            return jsonify({"error": f"Invalid mode: {mode_str}"}), 400
        if session_id:
            bootstrap._permission_manager.set_session_mode(session_id, mode)
        else:
            bootstrap._permission_manager.set_global_mode(mode)
        return jsonify({"status": "ok", "mode": mode.value, "session_id": session_id})

    @app.route('/permissions/request', methods=['GET'])
    def permissions_pending():
        if not bootstrap._permission_manager:
            return jsonify({"error": "Permission system not initialized"}), 503
        session_id = request.args.get("session_id")
        requests = bootstrap._permission_manager.get_pending_requests(session_id)
        return jsonify({"pending": requests})

    @app.route('/permissions/respond', methods=['POST'])
    def permissions_respond():
        if not bootstrap._permission_manager:
            return jsonify({"error": "Permission system not initialized"}), 503
        data = request.get_json() or {}
        request_id = data.get("request_id", "")
        decision = data.get("decision", "reject")
        ok = bootstrap._permission_manager.respond_permission(request_id, decision)
        if ok:
            return jsonify({"status": "ok", "request_id": request_id, "decision": decision})
        return jsonify({"error": "Request not found or already resolved"}), 404

    @app.route('/permissions/trust-rules', methods=['GET', 'POST', 'DELETE'])
    def permissions_trust_rules():
        if not bootstrap._permission_manager:
            return jsonify({"error": "Permission system not initialized"}), 503
        if request.method == 'GET':
            rules = bootstrap._permission_manager.get_trust_rules()
            return jsonify({"rules": rules})
        elif request.method == 'DELETE':
            data = request.get_json() or {}
            rule_id = data.get("rule_id", "")
            ok = bootstrap._permission_manager.remove_trust_rule(rule_id)
            return jsonify({"removed": ok})
        return jsonify({"error": "Method not supported"}), 405

    @app.route('/permissions/audit', methods=['GET'])
    def permissions_audit():
        if not bootstrap._permission_manager:
            return jsonify({"error": "Permission system not initialized"}), 503
        limit = request.args.get("limit", 100, type=int)
        session_id = request.args.get("session_id")
        entries = bootstrap._permission_manager.get_audit_log(limit=limit, session_id=session_id)
        return jsonify({"audit": entries})

    @app.route('/permissions/cancel', methods=['POST'])
    def permissions_cancel():
        if not bootstrap._permission_manager:
            return jsonify({"error": "Permission system not initialized"}), 503
        data = request.get_json() or {}
        session_id = data.get("session_id")
        bootstrap._permission_manager.cancel_pending(session_id)
        return jsonify({"status": "ok"})

    @app.route('/permissions/sse', methods=['GET'])
    def permissions_sse():
        if not bootstrap._permission_manager:
            return jsonify({"error": "Permission system not initialized"}), 503

        def generate():
            listener_id = f"sse_{uuid.uuid4().hex[:8]}"
            event_queue = queue.Queue()

            def on_event(event_type, data):
                event_queue.put((event_type, data))

            bootstrap._permission_manager.register_sse_listener(listener_id, on_event)

            try:
                yield f"event: connected\ndata: {{\"listener_id\": \"{listener_id}\"}}\n\n"
                while True:
                    try:
                        event_type, data = event_queue.get(timeout=30)
                        yield f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
                    except queue.Empty:
                        yield f"event: heartbeat\ndata: {{\"ts\": {int(time.time())}}}\n\n"
            except GeneratorExit:
                pass
            finally:
                bootstrap._permission_manager.unregister_sse_listener(listener_id)

        return Response(generate(), mimetype='text/event-stream',
                        headers={
                            'Cache-Control': 'no-cache',
                            'X-Accel-Buffering': 'no',
                            'Connection': 'keep-alive',
                        })

    @app.route('/permissions/check', methods=['POST'])
    def permissions_check():
        if not bootstrap._permission_manager:
            return jsonify({"error": "Permission system not initialized"}), 503
        data = request.get_json() or {}
        tool_name = data.get("tool_name", "")
        tool_input = data.get("tool_input", {})
        session_id = data.get("session_id", "")
        from kaguya_permissions import AutoApprovalClassifier, PermissionMode
        classifier = AutoApprovalClassifier()
        mode = bootstrap._permission_manager.get_session_mode(session_id)
        trust_rules = [type('Rule', (), asdict(r))() for r in bootstrap._permission_manager.get_trust_rules()]
        auto_approved, reason = classifier.classify(tool_name, tool_input, mode, trust_rules)
        risk_level = classifier.get_risk_level(tool_name, tool_input)
        return jsonify({
            "tool_name": tool_name,
            "risk_level": risk_level.value,
            "mode": mode.value,
            "auto_approved": auto_approved,
            "reason": reason,
        })


def inject_frontend_modules(html_template_str):
    try:
        frontend_mod = __import__("kaguya_frontend")
        return frontend_mod.inject_frontend_into_template(html_template_str)
    except ImportError:
        return html_template_str
    except Exception:
        return html_template_str


def run_kaguya_server(port=5000, host="127.0.0.1", debug=False):
    from flask import Flask
    app = Flask(__name__)
    app.secret_key = os.environ.get('KAGUYA_SECRET_KEY', secrets.token_hex(32))

    register_routes(app)

    ssl_context = None
    cert_path = os.path.join(KAGUYA_DIR, 'cert.pem')
    key_path = os.path.join(KAGUYA_DIR, 'key.pem')
    https_enabled = os.environ.get('KAGUYA_HTTPS', '').lower() == 'true'
    if https_enabled and os.path.exists(cert_path) and os.path.exists(key_path):
        ssl_context = (cert_path, key_path)

    local_ip = "127.0.0.1"
    try:
        import socket as _sock
        s = _sock.socket(_sock.AF_INET, _sock.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        pass

    print("=" * 60)
    print("  辉夜 IDE - Kaguya IDE v3.1 (Enhanced)")
    print("=" * 60)
    protocol = "https" if ssl_context else "http"
    print(f"  Local:   {protocol}://127.0.0.1:{port}")
    print(f"  Network: {protocol}://{local_ip}:{port}")
    print(f"  Systems: ACP + Agents + Skills + Accounts + Frontend")
    status = bootstrap.get_status()
    systems = [k for k, v in status["systems"].items() if v]
    print(f"  Loaded:  {', '.join(systems) if systems else '(none)'}")
    if status["errors"]:
        print(f"  Errors:  {len(status['errors'])} issue(s)")
        for err in status["errors"][:5]:
            print(f"           - {err}")
    print("=" * 60)

    app.run(host=host, port=port, debug=debug, ssl_context=ssl_context)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="辉夜IDE 启动引导")
    parser.add_argument("--port", type=int, default=5000, help="服务端口")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="绑定地址")
    parser.add_argument("--debug", action="store_true", help="调试模式")
    args = parser.parse_args()

    run_kaguya_server(port=args.port, host=args.host, debug=args.debug)
