#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenAI兼容API接口
提供与OpenAI API兼容的接口
使用 Ollama 后端
"""

import json
import time
import uuid
from flask import Blueprint, request, jsonify, Response, stream_with_context
from functools import wraps

USE_OLLAMA = True
OLLAMA_MODEL = "qwen3.5:4b"

if USE_OLLAMA:
    from ollama_adapter import get_ollama_adapter, OllamaConfig

openai_bp = Blueprint('openai_api', __name__, url_prefix='/v1')

API_KEYS = {
    'sk-kaguya-local': {'user_id': 'local', 'rate_limit': 1000},
    'sk-ollama': {'user_id': 'ollama', 'rate_limit': 1000},
}

def verify_api_key():
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None
    api_key = auth_header[7:]
    return API_KEYS.get(api_key)

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        key_info = verify_api_key()
        if not key_info:
            return jsonify({
                'error': {
                    'message': 'Invalid API key',
                    'type': 'invalid_request_error',
                    'code': 'invalid_api_key'
                }
            }), 401
        return f(*args, **kwargs)
    return decorated

@openai_bp.route('/models', methods=['GET'])
@require_api_key
def list_models():
    models = [
        {
            'id': 'qwen3.5:4b',
            'object': 'model',
            'created': int(time.time()),
            'owned_by': 'ollama',
            'permission': [],
            'root': 'qwen3.5:4b',
            'parent': None,
        },
        {
            'id': 'kaguya-qwen3.5-4b',
            'object': 'model',
            'created': int(time.time()),
            'owned_by': 'kaguya-ai',
            'permission': [],
            'root': 'kaguya-qwen3.5-4b',
            'parent': None,
        }
    ]
    
    if USE_OLLAMA:
        try:
            adapter = get_ollama_adapter()
            for m in adapter.list_models():
                model_name = m.get('name', '')
                if model_name and not any(existing['id'] == model_name for existing in models):
                    models.append({
                        'id': model_name,
                        'object': 'model',
                        'created': int(time.time()),
                        'owned_by': 'ollama',
                        'permission': [],
                        'root': model_name,
                        'parent': None,
                    })
        except:
            pass
    
    return jsonify({
        'object': 'list',
        'data': models
    })

@openai_bp.route('/chat/completions', methods=['POST'])
@require_api_key
def chat_completions():
    data = request.get_json()
    
    messages = data.get('messages', [])
    model = data.get('model', OLLAMA_MODEL)
    stream = data.get('stream', False)
    temperature = data.get('temperature', 0.7)
    max_tokens = data.get('max_tokens', 1024)
    top_p = data.get('top_p', 0.9)
    
    response_id = f'chatcmpl-{uuid.uuid4().hex[:12]}'
    
    if stream:
        return Response(
            stream_with_context(generate_stream_response(
                response_id, model, messages, temperature, max_tokens, top_p
            )),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',
            }
        )
    else:
        response = generate_completion_response(
            response_id, model, messages, temperature, max_tokens, top_p
        )
        return jsonify(response)

@openai_bp.route('/embeddings', methods=['POST'])
@require_api_key
def create_embeddings():
    data = request.get_json()
    
    input_text = data.get('input', '')
    model = data.get('model', 'text-embedding-ada-002')
    
    if USE_OLLAMA:
        try:
            adapter = get_ollama_adapter()
            if isinstance(input_text, list):
                embeddings = []
                for text in input_text:
                    embedding = adapter.embeddings(text)
                    embeddings.append({
                        'object': 'embedding',
                        'embedding': embedding,
                        'index': len(embeddings)
                    })
            else:
                embedding = adapter.embeddings(input_text)
                embeddings = [{
                    'object': 'embedding',
                    'embedding': embedding,
                    'index': 0
                }]
            
            return jsonify({
                'object': 'list',
                'data': embeddings,
                'model': model,
                'usage': {
                    'prompt_tokens': len(str(input_text).split()),
                    'total_tokens': len(str(input_text).split())
                }
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    else:
        try:
            from qwen3_web import get_embedding
            
            if isinstance(input_text, list):
                embeddings = []
                for text in input_text:
                    embedding = get_embedding(text)
                    embeddings.append({
                        'object': 'embedding',
                        'embedding': embedding,
                        'index': len(embeddings)
                    })
            else:
                embedding = get_embedding(input_text)
                embeddings = [{
                    'object': 'embedding',
                    'embedding': embedding,
                    'index': 0
                }]
            
            return jsonify({
                'object': 'list',
                'data': embeddings,
                'model': model,
                'usage': {
                    'prompt_tokens': len(str(input_text).split()),
                    'total_tokens': len(str(input_text).split())
                }
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

def generate_stream_response(response_id, model, messages, temperature, max_tokens, top_p):
    created = int(time.time())
    
    yield f'data: {json.dumps({"id": response_id, "object": "chat.completion.chunk", "created": created, "model": model, "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}]})}\n\n'
    
    if USE_OLLAMA:
        try:
            adapter = get_ollama_adapter(OllamaConfig(model=model))
            for chunk in adapter.chat_stream(messages, temperature=temperature, max_tokens=max_tokens, top_p=top_p):
                data = {
                    'id': response_id,
                    'object': 'chat.completion.chunk',
                    'created': created,
                    'model': model,
                    'choices': [{
                        'index': 0,
                        'delta': {'content': chunk},
                        'finish_reason': None
                    }]
                }
                yield f'data: {json.dumps(data)}\n\n'
        except Exception as e:
            yield f'data: {json.dumps({"error": str(e)})}\n\n'
    else:
        try:
            from qwen3_web import generate_stream
            prompt = convert_messages_to_prompt(messages)
            for chunk in generate_stream(prompt, temperature=temperature, max_tokens=max_tokens):
                content = chunk.get('content', '')
                if content:
                    data = {
                        'id': response_id,
                        'object': 'chat.completion.chunk',
                        'created': created,
                        'model': model,
                        'choices': [{
                            'index': 0,
                            'delta': {'content': content},
                            'finish_reason': None
                        }]
                    }
                    yield f'data: {json.dumps(data)}\n\n'
        except Exception as e:
            yield f'data: {json.dumps({"error": str(e)})}\n\n'
    
    yield f'data: {json.dumps({"id": response_id, "object": "chat.completion.chunk", "created": created, "model": model, "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]})}\n\n'
    yield 'data: [DONE]\n\n'

def generate_completion_response(response_id, model, messages, temperature, max_tokens, top_p):
    if USE_OLLAMA:
        try:
            adapter = get_ollama_adapter(OllamaConfig(model=model))
            content = adapter.chat(messages, temperature=temperature, max_tokens=max_tokens, top_p=top_p)
        except Exception as e:
            content = f"错误: {str(e)}"
    else:
        try:
            from qwen3_web import generate_response
            prompt = convert_messages_to_prompt(messages)
            content = generate_response(prompt, temperature=temperature, max_tokens=max_tokens)
        except Exception as e:
            content = f"错误: {str(e)}"
    
    return {
        'id': response_id,
        'object': 'chat.completion',
        'created': int(time.time()),
        'model': model,
        'choices': [{
            'index': 0,
            'message': {
                'role': 'assistant',
                'content': content
            },
            'finish_reason': 'stop'
        }],
        'usage': {
            'prompt_tokens': sum(len(m.get('content', '').split()) for m in messages),
            'completion_tokens': len(content.split()),
            'total_tokens': sum(len(m.get('content', '').split()) for m in messages) + len(content.split())
        }
    }

def convert_messages_to_prompt(messages):
    prompt_parts = []
    
    for msg in messages:
        role = msg.get('role', 'user')
        content = msg.get('content', '')
        
        if role == 'system':
            prompt_parts.append(f"系统提示: {content}")
        elif role == 'user':
            prompt_parts.append(f"用户: {content}")
        elif role == 'assistant':
            prompt_parts.append(f"助手: {content}")
    
    prompt_parts.append("助手: ")
    return "\n".join(prompt_parts)

@openai_bp.route('/health', methods=['GET'])
def health_check():
    status = 'healthy'
    ollama_status = 'unknown'
    
    if USE_OLLAMA:
        try:
            adapter = get_ollama_adapter()
            ollama_status = 'running' if adapter.is_server_running() else 'stopped'
            if ollama_status != 'running':
                status = 'degraded'
        except:
            ollama_status = 'error'
            status = 'degraded'
    
    return jsonify({
        'status': status,
        'version': '2.0.0',
        'backend': 'ollama' if USE_OLLAMA else 'local',
        'ollama_status': ollama_status,
        'timestamp': int(time.time())
    })

if __name__ == '__main__':
    print("OpenAI API模块已加载 (Ollama 后端)")
