#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辉夜IDE 前端模块化重构
将后端功能迁移到前端，实现客户端状态管理、API封装和组件化

迁移的功能：
1. 聊天历史管理 - 从后端session迁移到前端localStorage + IndexedDB
2. 消息渲染 - Markdown渲染、代码高亮从前端直接处理
3. 流式响应处理 - SSE解析从前端EventSource处理
4. 设置管理 - 用户偏好从前端管理
5. 主题系统 - 前端CSS变量驱动
6. 工具调用展示 - 前端组件化渲染
7. 对话搜索 - 前端全文搜索
8. 文件操作预览 - 前端diff渲染
"""

import json
import os
from typing import Dict, Any

FRONTEND_CORE_JS = r"""
// ============================================================
// 辉夜IDE 前端核心框架 - KaguyaFrontend
// ============================================================

const KaguyaFrontend = (function() {
    'use strict';

    // ---- 状态管理 ----
    class StateManager {
        constructor(initialState = {}) {
            this._state = { ...initialState };
            this._listeners = new Map();
            this._batchMode = false;
            this._pendingNotifications = new Set();
        }

        get(key, defaultValue = undefined) {
            const keys = key.split('.');
            let value = this._state;
            for (const k of keys) {
                if (value === null || value === undefined || typeof value !== 'object') {
                    return defaultValue;
                }
                value = value[k];
            }
            return value !== undefined ? value : defaultValue;
        }

        set(key, value) {
            const keys = key.split('.');
            let obj = this._state;
            for (let i = 0; i < keys.length - 1; i++) {
                if (!(keys[i] in obj) || typeof obj[keys[i]] !== 'object') {
                    obj[keys[i]] = {};
                }
                obj = obj[keys[i]];
            }
            const oldValue = obj[keys[keys.length - 1]];
            obj[keys[keys.length - 1]] = value;

            if (!this._batchMode) {
                this._notify(key, value, oldValue);
            } else {
                this._pendingNotifications.add(key);
            }
        }

        update(updates) {
            this._batchMode = true;
            for (const [key, value] of Object.entries(updates)) {
                this.set(key, value);
            }
            this._batchMode = false;
            for (const key of this._pendingNotifications) {
                this._notify(key, this.get(key), undefined);
            }
            this._pendingNotifications.clear();
        }

        subscribe(key, callback) {
            if (!this._listeners.has(key)) {
                this._listeners.set(key, new Set());
            }
            this._listeners.get(key).add(callback);
            return () => {
                const listeners = this._listeners.get(key);
                if (listeners) {
                    listeners.delete(callback);
                }
            };
        }

        _notify(key, newValue, oldValue) {
            const listeners = this._listeners.get(key);
            if (listeners) {
                for (const cb of listeners) {
                    try { cb(newValue, oldValue, key); } catch(e) { console.error('State listener error:', e); }
                }
            }
            for (const [pattern, cbs] of this._listeners) {
                if (pattern !== key && (key.startsWith(pattern + '.') || pattern === '*')) {
                    for (const cb of cbs) {
                        try { cb(newValue, oldValue, key); } catch(e) {}
                    }
                }
            }
        }

        getState() {
            return JSON.parse(JSON.stringify(this._state));
        }
    }

    // ---- API客户端 ----
    class APIClient {
        constructor(baseURL = '') {
            this._baseURL = baseURL;
            this._defaultHeaders = {
                'Content-Type': 'application/json',
            };
            this._interceptors = [];
            this._retryConfig = { maxRetries: 2, retryDelay: 1000 };
        }

        setDefaultHeader(key, value) {
            this._defaultHeaders[key] = value;
        }

        addInterceptor(fn) {
            this._interceptors.push(fn);
        }

        async request(method, path, data = null, options = {}) {
            const url = this._baseURL + path;
            const headers = { ...this._defaultHeaders, ...options.headers };

            const csrfToken = this._getCSRFToken();
            if (csrfToken) {
                headers['X-CSRF-Token'] = csrfToken;
            }

            let config = { method, headers, credentials: 'same-origin' };
            if (data && method !== 'GET') {
                config.body = JSON.stringify(data);
            }

            for (const interceptor of this._interceptors) {
                config = await interceptor(config);
            }

            const maxRetries = options.maxRetries ?? this._retryConfig.maxRetries;
            let lastError;

            for (let attempt = 0; attempt <= maxRetries; attempt++) {
                try {
                    const response = await fetch(url, config);
                    if (response.ok) {
                        const contentType = response.headers.get('content-type');
                        if (contentType && contentType.includes('application/json')) {
                            return await response.json();
                        }
                        return response;
                    }
                    if (response.status === 401) {
                        this._handleUnauthorized();
                        throw new Error('Unauthorized');
                    }
                    if (response.status >= 500 && attempt < maxRetries) {
                        await this._delay(this._retryConfig.retryDelay * (attempt + 1));
                        continue;
                    }
                    const errorData = await response.json().catch(() => ({}));
                    throw new Error(errorData.error || `HTTP ${response.status}`);
                } catch (e) {
                    lastError = e;
                    if (e.message === 'Unauthorized') throw e;
                    if (attempt < maxRetries) {
                        await this._delay(this._retryConfig.retryDelay * (attempt + 1));
                    }
                }
            }
            throw lastError;
        }

        async stream(path, data, onChunk, onDone, onError) {
            const url = this._baseURL + path;
            const headers = { ...this._defaultHeaders, 'Content-Type': 'application/json' };
            const csrfToken = this._getCSRFToken();
            if (csrfToken) headers['X-CSRF-Token'] = csrfToken;

            try {
                const response = await fetch(url, {
                    method: 'POST', headers, credentials: 'same-origin',
                    body: JSON.stringify(data),
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n');
                    buffer = lines.pop() || '';

                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            const dataStr = line.slice(6).trim();
                            if (dataStr === '[DONE]') {
                                if (onDone) onDone();
                                return;
                            }
                            try {
                                const parsed = JSON.parse(dataStr);
                                if (onChunk) onChunk(parsed);
                            } catch(e) {}
                        }
                    }
                }
                if (onDone) onDone();
            } catch(e) {
                if (onError) onError(e);
            }
        }

        get(path, options = {}) { return this.request('GET', path, null, options); }
        post(path, data, options = {}) { return this.request('POST', path, data, options); }
        put(path, data, options = {}) { return this.request('PUT', path, data, options); }
        delete(path, options = {}) { return this.request('DELETE', path, null, options); }

        _getCSRFToken() {
            const meta = document.querySelector('meta[name="csrf-token"]');
            if (meta) return meta.getAttribute('content');
            const cookies = document.cookie.split(';');
            for (const c of cookies) {
                const [name, value] = c.trim().split('=');
                if (name === 'csrf_token') return value;
            }
            return null;
        }

        _handleUnauthorized() {
            window.dispatchEvent(new CustomEvent('kaguya:unauthorized'));
        }

        _delay(ms) { return new Promise(r => setTimeout(r, ms)); }
    }

    // ---- 本地存储管理 ----
    class StorageManager {
        constructor(prefix = 'kaguya_') {
            this._prefix = prefix;
            this._db = null;
            this._dbReady = this._initDB();
        }

        async _initDB() {
            if (!window.indexedDB) return null;
            return new Promise((resolve) => {
                const request = indexedDB.open('KaguyaIDE', 2);
                request.onupgradeneeded = (e) => {
                    const db = e.target.result;
                    if (!db.objectStoreNames.contains('chats')) {
                        db.createObjectStore('chats', { keyPath: 'id' });
                    }
                    if (!db.objectStoreNames.contains('messages')) {
                        const store = db.createObjectStore('messages', { keyPath: 'id' });
                        store.createIndex('chatId', 'chatId', { unique: false });
                    }
                    if (!db.objectStoreNames.contains('files')) {
                        db.createObjectStore('files', { keyPath: 'path' });
                    }
                };
                request.onsuccess = (e) => { this._db = e.target.result; resolve(this._db); };
                request.onerror = () => resolve(null);
            });
        }

        setLocal(key, value) {
            try {
                localStorage.setItem(this._prefix + key, JSON.stringify(value));
            } catch(e) {}
        }

        getLocal(key, defaultValue = null) {
            try {
                const raw = localStorage.getItem(this._prefix + key);
                return raw ? JSON.parse(raw) : defaultValue;
            } catch(e) { return defaultValue; }
        }

        removeLocal(key) {
            localStorage.removeItem(this._prefix + key);
        }

        async setIndexed(storeName, data) {
            await this._dbReady;
            if (!this._db) return;
            return new Promise((resolve, reject) => {
                const tx = this._db.transaction(storeName, 'readwrite');
                tx.objectStore(storeName).put(data);
                tx.oncomplete = () => resolve();
                tx.onerror = () => reject(tx.error);
            });
        }

        async getIndexed(storeName, key) {
            await this._dbReady;
            if (!this._db) return null;
            return new Promise((resolve) => {
                const tx = this._db.transaction(storeName, 'readonly');
                const req = tx.objectStore(storeName).get(key);
                req.onsuccess = () => resolve(req.result);
                req.onerror = () => resolve(null);
            });
        }

        async getAllIndexed(storeName) {
            await this._dbReady;
            if (!this._db) return [];
            return new Promise((resolve) => {
                const tx = this._db.transaction(storeName, 'readonly');
                const req = tx.objectStore(storeName).getAll();
                req.onsuccess = () => resolve(req.result);
                req.onerror = () => resolve([]);
            });
        }

        async deleteIndexed(storeName, key) {
            await this._dbReady;
            if (!this._db) return;
            return new Promise((resolve) => {
                const tx = this._db.transaction(storeName, 'readwrite');
                tx.objectStore(storeName).delete(key);
                tx.oncomplete = () => resolve();
                tx.onerror = () => resolve();
            });
        }

        async getByIndex(storeName, indexName, key) {
            await this._dbReady;
            if (!this._db) return [];
            return new Promise((resolve) => {
                const tx = this._db.transaction(storeName, 'readonly');
                const idx = tx.objectStore(storeName).index(indexName);
                const req = idx.getAll(key);
                req.onsuccess = () => resolve(req.result);
                req.onerror = () => resolve([]);
            });
        }
    }

    // ---- 聊天管理器（前端） ----
    class ChatManager {
        constructor(storage, api) {
            this._storage = storage;
            this._api = api;
            this._chats = [];
            this._currentChatId = null;
            this._listeners = new Set();
            this._searchIndex = new Map();
            this._loadChats();
        }

        async _loadChats() {
            this._chats = await this._storage.getAllIndexed('chats') || [];
            if (this._chats.length === 0) {
                const local = this._storage.getLocal('chats', []);
                if (local.length > 0) {
                    this._chats = local;
                    for (const chat of this._chats) {
                        await this._storage.setIndexed('chats', chat);
                    }
                    this._storage.removeLocal('chats');
                }
            }
            this._buildSearchIndex();
            this._notify('chats_loaded');
        }

        async createChat(title = '新对话') {
            const chat = {
                id: 'chat_' + Date.now() + '_' + Math.random().toString(36).substr(2, 6),
                title,
                createdAt: new Date().toISOString(),
                updatedAt: new Date().toISOString(),
                messageCount: 0,
                model: '',
                tags: [],
            };
            this._chats.unshift(chat);
            await this._storage.setIndexed('chats', chat);
            this._currentChatId = chat.id;
            this._notify('chat_created', chat);
            return chat;
        }

        async deleteChat(chatId) {
            this._chats = this._chats.filter(c => c.id !== chatId);
            await this._storage.deleteIndexed('chats', chatId);
            const messages = await this._storage.getByIndex('messages', 'chatId', chatId);
            for (const msg of messages) {
                await this._storage.deleteIndexed('messages', msg.id);
            }
            if (this._currentChatId === chatId) {
                this._currentChatId = this._chats.length > 0 ? this._chats[0].id : null;
            }
            this._notify('chat_deleted', chatId);
        }

        async addMessage(chatId, role, content, metadata = {}) {
            const msg = {
                id: 'msg_' + Date.now() + '_' + Math.random().toString(36).substr(2, 6),
                chatId,
                role,
                content,
                timestamp: new Date().toISOString(),
                ...metadata,
            };
            await this._storage.setIndexed('messages', msg);

            const chat = this._chats.find(c => c.id === chatId);
            if (chat) {
                chat.messageCount++;
                chat.updatedAt = new Date().toISOString();
                await this._storage.setIndexed('chats', chat);
            }

            this._addToSearchIndex(msg);
            this._notify('message_added', msg);
            return msg;
        }

        async getMessages(chatId) {
            return await this._storage.getByIndex('messages', 'chatId', chatId);
        }

        async updateMessage(messageId, updates) {
            const msg = await this._storage.getIndexed('messages', messageId);
            if (msg) {
                Object.assign(msg, updates);
                await this._storage.setIndexed('messages', msg);
                this._notify('message_updated', msg);
            }
        }

        getChats() { return [...this._chats]; }
        getCurrentChatId() { return this._currentChatId; }
        setCurrentChatId(id) { this._currentChatId = id; this._notify('chat_switched', id); }

        search(query) {
            const results = [];
            const q = query.toLowerCase();
            for (const [msgId, text] of this._searchIndex) {
                if (text.toLowerCase().includes(q)) {
                    results.push(msgId);
                }
            }
            return results;
        }

        _buildSearchIndex() {
            this._searchIndex.clear();
        }

        _addToSearchIndex(msg) {
            if (typeof msg.content === 'string') {
                this._searchIndex.set(msg.id, msg.content);
            }
        }

        subscribe(callback) {
            this._listeners.add(callback);
            return () => this._listeners.delete(callback);
        }

        _notify(event, data) {
            for (const cb of this._listeners) {
                try { cb(event, data); } catch(e) {}
            }
        }
    }

    // ---- 消息渲染器 ----
    class MessageRenderer {
        constructor() {
            this._renderers = {
                text: (content) => this._renderMarkdown(content),
                tool_call: (data) => this._renderToolCall(data),
                tool_result: (data) => this._renderToolResult(data),
                thinking: (content) => this._renderThinking(content),
                image: (data) => this._renderImage(data),
                diff: (data) => this._renderDiff(data),
            };
        }

        render(message) {
            const container = document.createElement('div');
            container.className = `message message-${message.role}`;
            container.dataset.messageId = message.id || '';

            const avatar = document.createElement('div');
            avatar.className = 'message-avatar';
            avatar.textContent = message.role === 'user' ? '👤' : '🌙';

            const content = document.createElement('div');
            content.className = 'message-content';

            if (typeof message.content === 'string') {
                content.innerHTML = this._renderers.text(message.content);
            } else if (Array.isArray(message.content)) {
                for (const block of message.content) {
                    const renderer = this._renderers[block.type];
                    if (renderer) {
                        const el = document.createElement('div');
                        el.className = `content-block content-${block.type}`;
                        el.innerHTML = renderer(block);
                        content.appendChild(el);
                    }
                }
            }

            const meta = document.createElement('div');
            meta.className = 'message-meta';
            meta.textContent = new Date(message.timestamp).toLocaleTimeString();

            container.appendChild(avatar);
            container.appendChild(content);
            container.appendChild(meta);
            return container;
        }

        _renderMarkdown(text) {
            if (window.marked) {
                try { return window.marked.parse(text); } catch(e) {}
            }
            return text.replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>');
        }

        _renderToolCall(data) {
            const name = data.name || 'Unknown Tool';
            const input = typeof data.input === 'string' ? data.input : JSON.stringify(data.input, null, 2);
            return `<div class="tool-call">
                <div class="tool-call-header"><span class="tool-icon">🔧</span> ${this._escapeHtml(name)}</div>
                <pre class="tool-call-input"><code>${this._escapeHtml(input)}</code></pre>
            </div>`;
        }

        _renderToolResult(data) {
            const output = typeof data.content === 'string' ? data.content : JSON.stringify(data.content, null, 2);
            const status = data.error ? 'error' : 'success';
            return `<div class="tool-result tool-result-${status}">
                <div class="tool-result-header"><span class="tool-icon">${data.error ? '❌' : '✅'}</span> Result</div>
                <pre class="tool-result-output"><code>${this._escapeHtml(output)}</code></pre>
            </div>`;
        }

        _renderThinking(content) {
            return `<details class="thinking-block"><summary>💭 思考过程</summary><div class="thinking-content">${this._renderMarkdown(content)}</div></details>`;
        }

        _renderImage(data) {
            return `<img src="data:${data.mime_type || 'image/png'};base64,${data.data}" alt="${data.name || ''}" class="message-image">`;
        }

        _renderDiff(data) {
            const oldLines = (data.oldText || '').split('\n');
            const newLines = (data.newText || '').split('\n');
            let html = '<div class="diff-viewer">';
            for (const line of newLines) {
                const cls = line.startsWith('+') ? 'diff-add' : line.startsWith('-') ? 'diff-remove' : 'diff-context';
                html += `<div class="${cls}">${this._escapeHtml(line)}</div>`;
            }
            html += '</div>';
            return html;
        }

        _escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
    }

    // ---- 设置管理器 ----
    class SettingsManager {
        constructor(storage) {
            this._storage = storage;
            this._settings = this._storage.getLocal('settings', {
                theme: 'light',
                fontSize: 14,
                language: 'zh-CN',
                temperature: 0.7,
                maxTokens: 4096,
                markdown: true,
                streamMode: true,
                autoSave: true,
                showThinking: true,
                compactThreshold: 0.8,
            });
            this._listeners = new Set();
        }

        get(key, defaultValue) {
            return this._settings[key] !== undefined ? this._settings[key] : defaultValue;
        }

        set(key, value) {
            const oldValue = this._settings[key];
            this._settings[key] = value;
            this._storage.setLocal('settings', this._settings);
            this._notify(key, value, oldValue);
        }

        getAll() { return { ...this._settings }; }

        update(updates) {
            Object.assign(this._settings, updates);
            this._storage.setLocal('settings', this._settings);
            this._notify('*', this._settings);
        }

        subscribe(callback) {
            this._listeners.add(callback);
            return () => this._listeners.delete(callback);
        }

        _notify(key, value, oldValue) {
            for (const cb of this._listeners) {
                try { cb(key, value, oldValue); } catch(e) {}
            }
        }
    }

    // ---- 主题管理器 ----
    class ThemeManager {
        constructor(settings) {
            this._settings = settings;
            this._themes = {
                light: {
                    '--bg-primary': '#ffffff', '--bg-secondary': '#f5f5f5',
                    '--bg-tertiary': '#e8e8e8', '--text-primary': '#1a1a1a',
                    '--text-secondary': '#666666', '--accent': '#6366f1',
                    '--accent-hover': '#4f46e5', '--border': '#e2e2e2',
                    '--shadow': 'rgba(0,0,0,0.1)', '--success': '#10b981',
                    '--warning': '#f59e0b', '--error': '#ef4444',
                },
                dark: {
                    '--bg-primary': '#1a1b1e', '--bg-secondary': '#25262b',
                    '--bg-tertiary': '#2c2d32', '--text-primary': '#e4e4e4',
                    '--text-secondary': '#9a9a9a', '--accent': '#818cf8',
                    '--accent-hover': '#6366f1', '--border': '#3a3b40',
                    '--shadow': 'rgba(0,0,0,0.3)', '--success': '#34d399',
                    '--warning': '#fbbf24', '--error': '#f87171',
                },
                starfield: {
                    '--bg-primary': '#0a0a1a', '--bg-secondary': '#111128',
                    '--bg-tertiary': '#1a1a35', '--text-primary': '#e0e0ff',
                    '--text-secondary': '#8888bb', '--accent': '#7c3aed',
                    '--accent-hover': '#6d28d9', '--border': '#2a2a4a',
                    '--shadow': 'rgba(100,50,255,0.15)', '--success': '#4ade80',
                    '--warning': '#fbbf24', '--error': '#fb7185',
                },
            };
            this._applyTheme(this._settings.get('theme', 'light'));
            this._settings.subscribe((key, value) => {
                if (key === 'theme') this._applyTheme(value);
            });
        }

        _applyTheme(themeName) {
            const theme = this._themes[themeName] || this._themes.light;
            const root = document.documentElement;
            for (const [prop, value] of Object.entries(theme)) {
                root.style.setProperty(prop, value);
            }
            root.dataset.theme = themeName;
        }

        getTheme() { return this._settings.get('theme', 'light'); }
        setTheme(name) { this._settings.set('theme', name); }
        getAvailableThemes() { return Object.keys(this._themes); }
    }

    // ---- 事件总线 ----
    class EventBus {
        constructor() {
            this._handlers = new Map();
        }

        on(event, handler) {
            if (!this._handlers.has(event)) {
                this._handlers.set(event, new Set());
            }
            this._handlers.get(event).add(handler);
            return () => this._handlers.get(event)?.delete(handler);
        }

        emit(event, data) {
            const handlers = this._handlers.get(event);
            if (handlers) {
                for (const h of handlers) {
                    try { h(data); } catch(e) { console.error('Event error:', e); }
                }
            }
        }

        once(event, handler) {
            const wrapper = (data) => {
                handler(data);
                this.off(event, wrapper);
            };
            this.on(event, wrapper);
        }

        off(event, handler) {
            this._handlers.get(event)?.delete(handler);
        }
    }

    // ---- 初始化 ----
    const storage = new StorageManager();
    const api = new APIClient();
    const state = new StateManager({
        chats: [], currentChatId: null, settings: {},
        agentMode: false, ragEnabled: false,
    });
    const chatManager = new ChatManager(storage, api);
    const messageRenderer = new MessageRenderer();
    const settingsManager = new SettingsManager(storage);
    const themeManager = new ThemeManager(settingsManager);
    const eventBus = new EventBus();

    return {
        StateManager, APIClient, StorageManager, ChatManager,
        MessageRenderer, SettingsManager, ThemeManager, EventBus,
        storage, api, state, chatManager, messageRenderer,
        settingsManager, themeManager, eventBus,
    };
})();
"""

FRONTEND_API_ROUTES = r"""
// ============================================================
// 辉夜IDE 前端API路由封装
// ============================================================

const KaguyaAPI = (function() {
    'use strict';
    const { api } = KaguyaFrontend;

    return {
        chat: {
            send(message, options = {}) {
                return api.post('/stream', {
                    message,
                    history: options.history || [],
                    role: options.role || 'kaguya',
                    lora: options.lora || 'none',
                    temperature: options.temperature ?? 0.7,
                    max_tokens: options.maxTokens ?? 4096,
                });
            },

            stream(message, onChunk, onDone, onError, options = {}) {
                return api.stream('/stream', {
                    message,
                    history: options.history || [],
                    role: options.role || 'kaguya',
                    lora: options.lora || 'none',
                    temperature: options.temperature ?? 0.7,
                    max_tokens: options.maxTokens ?? 4096,
                }, onChunk, onDone, onError);
            },

            deepseek(message, onChunk, onDone, onError, options = {}) {
                return api.stream('/deepseek/chat', {
                    message,
                    history: options.history || [],
                    model: options.model || 'deepseek-chat',
                    temperature: options.temperature ?? 0.7,
                }, onChunk, onDone, onError);
            },
        },

        agent: {
            run(message, onChunk, onDone, onError, options = {}) {
                return api.stream('/agent/run', {
                    message,
                    cwd: options.cwd || '',
                    mode: options.mode || 'agent',
                    permission_mode: options.permissionMode || 'default',
                }, onChunk, onDone, onError);
            },

            readFile(filePath) {
                return api.post('/agent/read-file', { file_path: filePath });
            },

            writeFile(filePath, content) {
                return api.post('/agent/write-file', { file_path: filePath, content });
            },

            execCommand(command, cwd = '') {
                return api.post('/agent/terminal/exec', { command, cwd });
            },

            getFileTree(path = '.') {
                return api.post('/agent/file-tree', { path });
            },
        },

        tools: {
            execute(toolName, args) {
                return api.post('/tool/execute', { tool: toolName, args });
            },
        },

        rag: {
            upload(file) {
                const formData = new FormData();
                formData.append('file', file);
                return fetch('/rag/upload', {
                    method: 'POST', body: formData, credentials: 'same-origin',
                }).then(r => r.json());
            },

            search(query, topK = 5) {
                return api.post('/rag/search', { query, top_k: topK });
            },

            getDocuments() {
                return api.get('/rag/documents');
            },

            getStats() {
                return api.get('/rag/stats');
            },
        },

        knowledge: {
            add(content, metadata = {}) {
                return api.post('/kb/add', { content, metadata });
            },

            search(query, topK = 5) {
                return api.post('/kb/search', { query, top_k: topK });
            },
        },

        memory: {
            search(query) {
                return api.post('/memory/search', { query });
            },

            getProfile() {
                return api.get('/memory/profile');
            },
        },

        mcp: {
            getPlugins() {
                return api.get('/mcp/plugins');
            },

            execute(pluginId, toolName, args) {
                return api.post('/mcp/execute', { plugin_id: pluginId, tool: toolName, args });
            },
        },

        workflow: {
            list() {
                return api.get('/workflows');
            },

            execute(workflowId, params = {}) {
                return api.post(`/workflow/${workflowId}/execute`, params);
            },
        },

        project: {
            getArtifacts() { return api.get('/artifacts'); },
            createArtifact(data) { return api.post('/artifacts', data); },
            getTasks() { return api.get('/project/tasks'); },
            createTask(data) { return api.post('/project/tasks', data); },
            getMilestones() { return api.get('/project/milestones'); },
            getRisks() { return api.get('/project/risks'); },
        },

        system: {
            getMetrics() { return api.get('/system/metrics'); },
            getPerformance() { return api.get('/performance/stats'); },
        },

        web: {
            search(query) { return api.post('/web/search', { query }); },
            fetch(url) { return api.post('/web/fetch', { url }); },
        },

        code: {
            execute(code, language = 'python') {
                return api.post('/code/execute', { code, language });
            },
        },

        auth: {
            login(password) {
                return api.post('/auth/login', { password });
            },
            logout() {
                return api.post('/auth/logout', {});
            },
            setup(password) {
                return api.post('/auth/setup', { password });
            },
        },

        acp: {
            initialize() { return api.post('/acp/initialize', {}); },
            newSession(cwd) { return api.post('/acp/session/new', { cwd }); },
            prompt(sessionId, prompt) { return api.post('/acp/prompt', { session_id: sessionId, prompt }); },
            cancel(sessionId) { return api.post('/acp/cancel', { session_id: sessionId }); },
            closeSession(sessionId) { return api.post('/acp/session/close', { session_id: sessionId }); },
            setMode(sessionId, modeId) { return api.post('/acp/mode', { session_id: sessionId, mode_id: modeId }); },
            setModel(sessionId, modelId) { return api.post('/acp/model', { session_id: sessionId, model_id: modelId }); },
        },

        skills: {
            list() { return api.get('/skills/list'); },
            execute(name, args = '') { return api.post('/skills/execute', { name, args }); },
            create(name, description, content) { return api.post('/skills/create', { name, description, content }); },
            delete(name) { return api.delete(`/skills/${name}`); },
        },

        agents: {
            list() { return api.get('/agents/list'); },
            execute(directive, agentType, options = {}) {
                return api.post('/agents/execute', {
                    directive, agent_type: agentType, ...options,
                });
            },
            getActive() { return api.get('/agents/active'); },
            cancel(sessionId) { return api.post('/agents/cancel', { session_id: sessionId }); },
        },

        permissions: {
            getStatus() { return api.get('/permissions/status'); },
            getMode(sessionId) { return api.get('/permissions/mode', { session_id: sessionId }); },
            setMode(mode, sessionId) { return api.post('/permissions/mode', { mode, session_id: sessionId || '' }); },
            getPending(sessionId) { return api.get('/permissions/request', { session_id: sessionId }); },
            respond(requestId, decision) { return api.post('/permissions/respond', { request_id: requestId, decision }); },
            getTrustRules() { return api.get('/permissions/trust-rules'); },
            removeTrustRule(ruleId) { return api.delete('/permissions/trust-rules', { rule_id: ruleId }); },
            getAudit(limit, sessionId) { return api.get('/permissions/audit', { limit: limit || 100, session_id: sessionId }); },
            cancelPending(sessionId) { return api.post('/permissions/cancel', { session_id: sessionId }); },
            check(toolName, toolInput, sessionId) { return api.post('/permissions/check', { tool_name: toolName, tool_input: toolInput, session_id: sessionId }); },
            connectSSE() {
                const url = (api._baseURL || '') + '/permissions/sse';
                return new EventSource(url);
            },
        },
    };
})();
"""


FRONTEND_PERMISSION_JS = r"""
// ============================================================
// 辉夜IDE 权限请求前端组件 - KaguyaPermissionUI
// 参考 Trae 网页版权限交互设计
// ============================================================

const KaguyaPermissionUI = (function() {
    'use strict';
    const { api } = KaguyaFrontend;
    let sseConnection = null;
    let permissionPanelEl = null;
    let currentMode = 'default';
    let pendingRequests = [];
    let trustRules = [];

    function init() {
        connectSSE();
        loadCurrentMode();
        window.addEventListener('beforeunload', () => {
            if (sseConnection) sseConnection.close();
        });
    }

    function connectSSE() {
        if (sseConnection) {
            sseConnection.close();
        }
        try {
            sseConnection = KaguyaAPI.permissions.connectSSE();
            sseConnection.addEventListener('permission_request', (e) => {
                const data = JSON.parse(e.data);
                onPermissionRequest(data);
            });
            sseConnection.addEventListener('permission_auto_approved', (e) => {
                const data = JSON.parse(e.data);
                onAutoApproved(data);
            });
            sseConnection.addEventListener('permission_resolved', (e) => {
                const data = JSON.parse(e.data);
                onPermissionResolved(data);
            });
            sseConnection.addEventListener('permission_timeout', (e) => {
                const data = JSON.parse(e.data);
                onPermissionTimeout(data);
            });
            sseConnection.addEventListener('heartbeat', () => {});
            sseConnection.onerror = () => {
                setTimeout(() => connectSSE(), 5000);
            };
        } catch(e) {
            console.error('[KaguyaPerm] SSE connection error:', e);
        }
    }

    async function loadCurrentMode() {
        try {
            const result = await KaguyaAPI.permissions.getStatus();
            currentMode = result.global_mode || 'default';
        } catch(e) {}
    }

    function onPermissionRequest(data) {
        pendingRequests.push(data);
        showPermissionNotification(data);
        updatePermissionBadge();
    }

    function onAutoApproved(data) {
        const notif = document.createElement('div');
        notif.className = 'kaguya-perm-notif kaguya-perm-auto';
        notif.innerHTML = '<span class="kaguya-perm-icon">✓</span> <span>Auto-approved: ' + escapeHtml(data.tool_name) + '</span>';
        appendNotification(notif);
    }

    function onPermissionResolved(data) {
        pendingRequests = pendingRequests.filter(r => r.request_id !== data.request_id);
        updatePermissionBadge();
    }

    function onPermissionTimeout(data) {
        pendingRequests = pendingRequests.filter(r => r.request_id !== data.request_id);
        const notif = document.createElement('div');
        notif.className = 'kaguya-perm-notif kaguya-perm-timeout';
        notif.innerHTML = '<span class="kaguya-perm-icon">⏱</span> <span>Permission request timed out: ' + escapeHtml(data.tool_name) + '</span>';
        appendNotification(notif);
        updatePermissionBadge();
    }

    function showPermissionNotification(data) {
        const riskColors = {
            safe: '#10b981', low: '#3b82f6', medium: '#f59e0b',
            high: '#f97316', critical: '#ef4444'
        };
        const riskLabels = {
            safe: 'Safe', low: 'Low', medium: 'Medium',
            high: 'High', critical: 'Critical'
        };
        const riskColor = riskColors[data.risk_level] || '#f59e0b';
        const riskLabel = riskLabels[data.risk_level] || 'Medium';

        const notif = document.createElement('div');
        notif.className = 'kaguya-perm-request';
        notif.id = 'perm-req-' + data.request_id;
        notif.innerHTML = `
            <div class="kaguya-perm-header">
                <span class="kaguya-perm-icon">🛡️</span>
                <span class="kaguya-perm-title">Permission Request</span>
                <span class="kaguya-perm-risk" style="background:${riskColor};color:#fff;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:700;">${riskLabel}</span>
            </div>
            <div class="kaguya-perm-body">
                <div class="kaguya-perm-tool">Tool: <strong>${escapeHtml(data.tool_name)}</strong></div>
                ${formatToolInput(data.tool_input, data.tool_name)}
                <div class="kaguya-perm-reason" style="color:var(--text-muted);font-size:10px;margin-top:4px;">${escapeHtml(data.reason || '')}</div>
            </div>
            <div class="kaguya-perm-actions">
                <button class="kaguya-perm-btn kaguya-perm-allow-always" onclick="KaguyaPermissionUI.respond('${data.request_id}','allow_always')">Always Allow</button>
                <button class="kaguya-perm-btn kaguya-perm-allow" onclick="KaguyaPermissionUI.respond('${data.request_id}','allow')">Allow</button>
                <button class="kaguya-perm-btn kaguya-perm-reject" onclick="KaguyaPermissionUI.respond('${data.request_id}','reject')">Reject</button>
            </div>
        `;
        appendNotification(notif);
    }

    function formatToolInput(toolInput, toolName) {
        if (!toolInput || typeof toolInput !== 'object') return '';
        const items = [];
        if (toolInput.file_path || toolInput.path) {
            items.push('<div class="kaguya-perm-detail"><span class="kaguya-perm-label">Path:</span> ' + escapeHtml(toolInput.file_path || toolInput.path) + '</div>');
        }
        if (toolInput.command) {
            const cmd = toolInput.command.length > 100 ? toolInput.command.substring(0, 100) + '...' : toolInput.command;
            items.push('<div class="kaguya-perm-detail"><span class="kaguya-perm-label">Command:</span> <code>' + escapeHtml(cmd) + '</code></div>');
        }
        if (toolInput.pattern || toolInput.glob) {
            items.push('<div class="kaguya-perm-detail"><span class="kaguya-perm-label">Pattern:</span> ' + escapeHtml(toolInput.pattern || toolInput.glob) + '</div>');
        }
        return items.join('');
    }

    function appendNotification(el) {
        let container = document.getElementById('kaguya-perm-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'kaguya-perm-container';
            container.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:10001;display:flex;flex-direction:column-reverse;gap:8px;max-height:60vh;overflow-y:auto;pointer-events:none;';
            document.body.appendChild(container);
        }
        container.appendChild(el);
        el.style.pointerEvents = 'auto';
        setTimeout(() => {
            if (el.parentNode) {
                el.style.opacity = '0';
                el.style.transform = 'translateX(100%)';
                el.style.transition = 'all 0.3s ease';
                setTimeout(() => el.remove(), 300);
            }
        }, 30000);
    }

    async function respond(requestId, decision) {
        try {
            await KaguyaAPI.permissions.respond(requestId, decision);
            const el = document.getElementById('perm-req-' + requestId);
            if (el) {
                el.style.opacity = '0.5';
                el.style.pointerEvents = 'none';
                setTimeout(() => el.remove(), 1000);
            }
            pendingRequests = pendingRequests.filter(r => r.request_id !== requestId);
            updatePermissionBadge();
        } catch(e) {
            console.error('[KaguyaPerm] Respond error:', e);
        }
    }

    function updatePermissionBadge() {
        let badge = document.getElementById('kaguya-perm-badge');
        if (pendingRequests.length > 0) {
            if (!badge) {
                badge = document.createElement('div');
                badge.id = 'kaguya-perm-badge';
                badge.style.cssText = 'position:fixed;top:10px;right:10px;z-index:10002;background:#ef4444;color:#fff;border-radius:50%;width:24px;height:24px;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;cursor:pointer;box-shadow:0 2px 8px rgba(0,0,0,0.3);';
                badge.onclick = () => showPermissionPanel();
                document.body.appendChild(badge);
            }
            badge.textContent = pendingRequests.length;
            badge.style.display = 'flex';
        } else if (badge) {
            badge.style.display = 'none';
        }
    }

    async function showPermissionPanel() {
        if (permissionPanelEl) {
            permissionPanelEl.remove();
            permissionPanelEl = null;
            return;
        }
        permissionPanelEl = document.createElement('div');
        permissionPanelEl.id = 'kaguya-perm-panel';
        permissionPanelEl.style.cssText = 'position:fixed;top:0;right:0;width:420px;height:100%;background:var(--bg-primary,#1a1b1e);border-left:1px solid var(--border,#3a3b40);z-index:10000;display:flex;flex-direction:column;box-shadow:-8px 0 32px rgba(0,0,0,0.3);font-family:system-ui,-apple-system,sans-serif;color:var(--text-primary,#e4e4e4);';
        permissionPanelEl.innerHTML = `
            <div style="display:flex;align-items:center;padding:12px 16px;border-bottom:1px solid var(--border,#3a3b40);gap:8px;">
                <span style="font-size:16px;">🛡️</span>
                <span style="font-weight:700;font-size:14px;">Permission Manager</span>
                <span style="flex:1;"></span>
                <button onclick="KaguyaPermissionUI.closePanel()" style="background:none;border:none;color:var(--text-secondary,#9a9a9a);cursor:pointer;font-size:14px;">✕</button>
            </div>
            <div id="kaguya-perm-panel-content" style="flex:1;overflow-y:auto;padding:12px 16px;">
                <div style="text-align:center;color:var(--text-secondary,#9a9a9a);padding:20px;">Loading...</div>
            </div>
        `;
        document.body.appendChild(permissionPanelEl);
        await loadPermissionPanel();
    }

    async function loadPermissionPanel() {
        const content = document.getElementById('kaguya-perm-panel-content');
        if (!content) return;
        try {
            const [status, rules] = await Promise.all([
                KaguyaAPI.permissions.getStatus(),
                KaguyaAPI.permissions.getTrustRules(),
            ]);
            currentMode = status.global_mode || 'default';
            trustRules = rules.rules || [];

            let html = '';

            html += '<div style="margin-bottom:16px;">';
            html += '<div style="font-size:11px;font-weight:700;color:var(--accent,#818cf8);text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">Permission Mode</div>';
            html += '<div style="display:flex;gap:4px;flex-wrap:wrap;">';
            const modes = status.available_modes || [];
            for (const m of modes) {
                const active = m.id === currentMode;
                const bg = active ? 'var(--accent,#818cf8)' : 'var(--bg-tertiary,#2c2d32)';
                const color = active ? '#fff' : 'var(--text-primary,#e4e4e4)';
                html += `<button onclick="KaguyaPermissionUI.setMode('${m.id}')" style="padding:6px 12px;background:${bg};color:${color};border:1px solid ${active?'transparent':'var(--border,#3a3b40)'};border-radius:6px;font-size:11px;cursor:pointer;font-weight:${active?'700':'400'};transition:all 0.15s;" title="${escapeHtml(m.description)}">${escapeHtml(m.name)}</button>`;
            }
            html += '</div></div>';

            if (pendingRequests.length > 0) {
                html += '<div style="margin-bottom:16px;">';
                html += '<div style="font-size:11px;font-weight:700;color:#ef4444;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">Pending Requests (' + pendingRequests.length + ')</div>';
                for (const req of pendingRequests) {
                    const riskColors = {safe:'#10b981',low:'#3b82f6',medium:'#f59e0b',high:'#f97316',critical:'#ef4444'};
                    const rc = riskColors[req.risk_level] || '#f59e0b';
                    html += `<div style="padding:10px;background:var(--bg-secondary,#25262b);border-radius:8px;margin-bottom:8px;border-left:3px solid ${rc};">`;
                    html += `<div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;"><strong style="font-size:12px;">${escapeHtml(req.tool_name)}</strong><span style="background:${rc};color:#fff;padding:1px 6px;border-radius:8px;font-size:9px;">${req.risk_level}</span></div>`;
                    html += `<div style="font-size:10px;color:var(--text-secondary,#9a9a9a);margin-bottom:8px;">${escapeHtml(req.reason||'')}</div>`;
                    html += `<div style="display:flex;gap:4px;">`;
                    html += `<button onclick="KaguyaPermissionUI.respond('${req.request_id}','allow_always')" style="padding:4px 10px;background:#10b981;color:#fff;border:none;border-radius:4px;font-size:10px;cursor:pointer;">Always</button>`;
                    html += `<button onclick="KaguyaPermissionUI.respond('${req.request_id}','allow')" style="padding:4px 10px;background:#3b82f6;color:#fff;border:none;border-radius:4px;font-size:10px;cursor:pointer;">Allow</button>`;
                    html += `<button onclick="KaguyaPermissionUI.respond('${req.request_id}','reject')" style="padding:4px 10px;background:#ef4444;color:#fff;border:none;border-radius:4px;font-size:10px;cursor:pointer;">Reject</button>`;
                    html += '</div></div>';
                }
                html += '</div>';
            }

            html += '<div style="margin-bottom:16px;">';
            html += '<div style="font-size:11px;font-weight:700;color:var(--accent,#818cf8);text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">Statistics</div>';
            html += '<div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:6px;">';
            const stats = [
                {label:'Total',value:status.total_requests||0,color:'var(--text-primary,#e4e4e4)'},
                {label:'Auto',value:status.auto_approved||0,color:'#10b981'},
                {label:'Approved',value:status.user_approved||0,color:'#3b82f6'},
                {label:'Rejected',value:status.rejected||0,color:'#ef4444'},
            ];
            for (const s of stats) {
                html += `<div style="padding:8px;background:var(--bg-secondary,#25262b);border-radius:6px;text-align:center;"><div style="font-size:16px;font-weight:700;color:${s.color};">${s.value}</div><div style="font-size:9px;color:var(--text-secondary,#9a9a9a);">${s.label}</div></div>`;
            }
            html += '</div></div>';

            if (trustRules.length > 0) {
                html += '<div style="margin-bottom:16px;">';
                html += '<div style="font-size:11px;font-weight:700;color:var(--accent,#818cf8);text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">Trust Rules</div>';
                for (const rule of trustRules) {
                    const isAllow = rule.decision === 'allow_always' || rule.decision === 'allow';
                    const color = isAllow ? '#10b981' : '#ef4444';
                    const icon = isAllow ? '✓' : '✗';
                    html += `<div style="display:flex;align-items:center;gap:6px;padding:6px 10px;background:var(--bg-secondary,#25262b);border-radius:6px;margin-bottom:4px;">`;
                    html += `<span style="color:${color};font-weight:700;">${icon}</span>`;
                    html += `<span style="font-size:10px;flex:1;">${escapeHtml(rule.tool_name)}: ${escapeHtml(rule.pattern)}</span>`;
                    html += `<button onclick="KaguyaPermissionUI.removeTrustRule('${rule.rule_id}')" style="background:none;border:none;color:var(--text-secondary,#9a9a9a);cursor:pointer;font-size:10px;">✕</button>`;
                    html += '</div>';
                }
                html += '</div>';
            }

            html += '<div style="margin-bottom:16px;">';
            html += '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">';
            html += '<span style="font-size:11px;font-weight:700;color:var(--accent,#818cf8);text-transform:uppercase;letter-spacing:1px;">Audit Log</span>';
            html += `<button onclick="KaguyaPermissionUI.refreshAudit()" style="padding:3px 8px;background:var(--bg-tertiary,#2c2d32);border:1px solid var(--border,#3a3b40);border-radius:4px;color:var(--text-secondary,#9a9a9a);font-size:9px;cursor:pointer;">↻</button>`;
            html += '</div>';
            html += '<div id="kaguya-perm-audit-list" style="max-height:200px;overflow-y:auto;"></div>';
            html += '</div>';

            content.innerHTML = html;
            refreshAudit();
        } catch(e) {
            content.innerHTML = '<div style="color:#ef4444;padding:20px;">Error: ' + escapeHtml(e.message) + '</div>';
        }
    }

    async function refreshAudit() {
        const list = document.getElementById('kaguya-perm-audit-list');
        if (!list) return;
        try {
            const result = await KaguyaAPI.permissions.getAudit(30);
            const entries = result.audit || [];
            if (!entries.length) {
                list.innerHTML = '<div style="font-size:10px;color:var(--text-secondary,#9a9a9a);">No audit entries</div>';
                return;
            }
            list.innerHTML = entries.reverse().map(e => {
                const color = e.auto_approved ? '#10b981' : (e.decision === 'allow' || e.decision === 'allow_always') ? '#3b82f6' : '#ef4444';
                const icon = e.auto_approved ? '⚡' : ((e.decision === 'allow' || e.decision === 'allow_always') ? '✓' : '✗');
                const ts = e.timestamp ? e.timestamp.split('T')[1]?.split('.')[0] || '' : '';
                return `<div style="display:flex;align-items:center;gap:6px;padding:4px 6px;border-bottom:1px solid var(--border,#3a3b40);font-size:9px;">
                    <span style="color:${color};font-weight:700;">${icon}</span>
                    <span style="color:var(--text-secondary,#9a9a9a);min-width:50px;">${ts}</span>
                    <span style="flex:1;">${escapeHtml(e.tool_name||'')}</span>
                    <span style="color:var(--text-secondary,#9a9a9a);max-width:100px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${escapeHtml((e.reason||'').substring(0,40))}</span>
                </div>`;
            }).join('');
        } catch(e) {
            list.innerHTML = '<div style="color:#ef4444;font-size:10px;">Error loading audit</div>';
        }
    }

    async function setMode(mode) {
        try {
            await KaguyaAPI.permissions.setMode(mode);
            currentMode = mode;
            await loadPermissionPanel();
        } catch(e) {
            console.error('[KaguyaPerm] Set mode error:', e);
        }
    }

    async function removeTrustRule(ruleId) {
        try {
            await KaguyaAPI.permissions.removeTrustRule(ruleId);
            trustRules = trustRules.filter(r => r.rule_id !== ruleId);
            await loadPermissionPanel();
        } catch(e) {
            console.error('[KaguyaPerm] Remove rule error:', e);
        }
    }

    function closePanel() {
        if (permissionPanelEl) {
            permissionPanelEl.remove();
            permissionPanelEl = null;
        }
    }

    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    return {
        init,
        respond,
        setMode,
        showPermissionPanel,
        closePanel,
        removeTrustRule,
        refreshAudit,
        loadPermissionPanel,
    };
})();

document.addEventListener('DOMContentLoaded', () => {
    KaguyaPermissionUI.init();
});
"""

FRONTEND_PERMISSION_CSS = r"""
<style>
.kaguya-perm-request {
    background: var(--bg-secondary, #25262b);
    border: 1px solid var(--border, #3a3b40);
    border-radius: 8px;
    padding: 12px;
    min-width: 300px;
    max-width: 380px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.3);
    animation: kaguyaSlideIn 0.3s ease-out;
    transition: all 0.3s ease;
}
.kaguya-perm-header {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 8px;
}
.kaguya-perm-title {
    font-weight: 700;
    font-size: 12px;
    flex: 1;
}
.kaguya-perm-body {
    margin-bottom: 10px;
}
.kaguya-perm-tool {
    font-size: 11px;
    margin-bottom: 4px;
}
.kaguya-perm-detail {
    font-size: 10px;
    color: var(--text-secondary, #9a9a9a);
    margin-top: 2px;
}
.kaguya-perm-detail code {
    background: var(--bg-tertiary, #2c2d32);
    padding: 1px 4px;
    border-radius: 3px;
    font-size: 10px;
}
.kaguya-perm-label {
    font-weight: 600;
    color: var(--text-primary, #e4e4e4);
}
.kaguya-perm-actions {
    display: flex;
    gap: 6px;
}
.kaguya-perm-btn {
    padding: 5px 12px;
    border: none;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s;
}
.kaguya-perm-btn:hover {
    opacity: 0.85;
    transform: translateY(-1px);
}
.kaguya-perm-allow-always {
    background: #10b981;
    color: #fff;
}
.kaguya-perm-allow {
    background: #3b82f6;
    color: #fff;
}
.kaguya-perm-reject {
    background: #ef4444;
    color: #fff;
}
.kaguya-perm-notif {
    padding: 8px 12px;
    border-radius: 6px;
    font-size: 11px;
    min-width: 200px;
    display: flex;
    align-items: center;
    gap: 6px;
    animation: kaguyaSlideIn 0.3s ease-out;
    transition: all 0.3s ease;
}
.kaguya-perm-auto {
    background: rgba(16,185,129,0.15);
    border: 1px solid rgba(16,185,129,0.3);
    color: #10b981;
}
.kaguya-perm-timeout {
    background: rgba(245,158,11,0.15);
    border: 1px solid rgba(245,158,11,0.3);
    color: #f59e0b;
}
@keyframes kaguyaSlideIn {
    from { opacity: 0; transform: translateX(50px); }
    to { opacity: 1; transform: translateX(0); }
}
</style>
"""


def get_frontend_js() -> str:
    return FRONTEND_CORE_JS + "\n" + FRONTEND_API_ROUTES + "\n" + FRONTEND_PERMISSION_JS


def get_frontend_html_head() -> str:
    return """<meta name="csrf-token" content="{{csrf_token}}">
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/highlight.js/lib/highlight.js"></script>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/highlight.js/styles/github-dark.min.css">"""


def inject_frontend_into_template(existing_html: str) -> str:
    head_close = existing_html.find("</head>")
    if head_close == -1:
        return existing_html

    injection = f"""
<script>
{get_frontend_js()}
</script>
"""
    return existing_html[:head_close] + injection + existing_html[head_close:]
