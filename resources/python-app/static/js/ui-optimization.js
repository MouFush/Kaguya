/**
 * UI优化模块 - 提升用户体验
 * 功能: 响应优化、加载状态、平滑动画、错误处理
 */

// ==================== 性能优化 ====================

/**
 * 防抖函数
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * 节流函数
 */
function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

/**
 * 请求队列管理器 - 防止重复请求
 */
class RequestQueue {
    constructor() {
        this.queue = new Map();
        this.maxRetries = 3;
        this.retryDelay = 1000;
    }

    async execute(key, requestFn, options = {}) {
        const { retry = 0, priority = 0 } = options;
        
        // 如果相同请求正在进行中，返回现有promise
        if (this.queue.has(key)) {
            return this.queue.get(key);
        }

        const promise = this._executeWithRetry(key, requestFn, retry);
        this.queue.set(key, promise);

        try {
            const result = await promise;
            return result;
        } finally {
            this.queue.delete(key);
        }
    }

    async _executeWithRetry(key, requestFn, retryCount) {
        try {
            return await requestFn();
        } catch (error) {
            if (retryCount < this.maxRetries) {
                await this._delay(this.retryDelay * (retryCount + 1));
                return this._executeWithRetry(key, requestFn, retryCount + 1);
            }
            throw error;
        }
    }

    _delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    cancel(key) {
        this.queue.delete(key);
    }

    cancelAll() {
        this.queue.clear();
    }
}

// 全局请求队列实例
const requestQueue = new RequestQueue();

// ==================== 加载状态管理 ====================

/**
 * 加载状态管理器
 */
class LoadingManager {
    constructor() {
        this.loadingElements = new Map();
        this.skeletonPool = [];
        this.maxSkeletons = 5;
    }

    /**
     * 显示加载状态
     */
    show(containerId, options = {}) {
        const { type = 'spinner', text = '加载中...', overlay = false } = options;
        const container = document.getElementById(containerId);
        if (!container) return;

        // 移除现有加载状态
        this.hide(containerId);

        const loader = document.createElement('div');
        loader.className = `ui-loader ui-loader-${type}`;
        loader.id = `loader-${containerId}`;

        if (overlay) {
            loader.classList.add('ui-loader-overlay');
        }

        let content = '';
        switch (type) {
            case 'spinner':
                content = `
                    <div class="ui-spinner">
                        <div class="ui-spinner-ring"></div>
                    </div>
                    <span class="ui-loader-text">${text}</span>
                `;
                break;
            case 'dots':
                content = `
                    <div class="ui-loading-dots">
                        <span></span><span></span><span></span>
                    </div>
                    <span class="ui-loader-text">${text}</span>
                `;
                break;
            case 'skeleton':
                content = this._createSkeleton();
                break;
            case 'progress':
                content = `
                    <div class="ui-progress-bar">
                        <div class="ui-progress-fill" id="progress-${containerId}"></div>
                    </div>
                    <span class="ui-loader-text">${text}</span>
                `;
                break;
        }

        loader.innerHTML = content;
        container.appendChild(loader);
        this.loadingElements.set(containerId, loader);

        // 添加进入动画
        requestAnimationFrame(() => {
            loader.classList.add('ui-loader-visible');
        });

        return loader;
    }

    /**
     * 隐藏加载状态
     */
    hide(containerId) {
        const loader = document.getElementById(`loader-${containerId}`);
        if (loader) {
            loader.classList.remove('ui-loader-visible');
            loader.classList.add('ui-loader-hiding');
            setTimeout(() => {
                loader.remove();
            }, 300);
            this.loadingElements.delete(containerId);
        }
    }

    /**
     * 更新进度
     */
    updateProgress(containerId, percent) {
        const progressBar = document.getElementById(`progress-${containerId}`);
        if (progressBar) {
            progressBar.style.width = `${percent}%`;
        }
    }

    /**
     * 创建骨架屏
     */
    _createSkeleton() {
        return `
            <div class="ui-skeleton">
                <div class="ui-skeleton-line" style="width: 100%"></div>
                <div class="ui-skeleton-line" style="width: 85%"></div>
                <div class="ui-skeleton-line" style="width: 90%"></div>
                <div class="ui-skeleton-line" style="width: 60%"></div>
            </div>
        `;
    }

    /**
     * 显示全局加载
     */
    showGlobal(text = '处理中...') {
        let globalLoader = document.getElementById('ui-global-loader');
        if (!globalLoader) {
            globalLoader = document.createElement('div');
            globalLoader.id = 'ui-global-loader';
            globalLoader.className = 'ui-global-loader';
            globalLoader.innerHTML = `
                <div class="ui-global-loader-content">
                    <div class="ui-spinner ui-spinner-large">
                        <div class="ui-spinner-ring"></div>
                    </div>
                    <span class="ui-global-loader-text">${text}</span>
                </div>
            `;
            document.body.appendChild(globalLoader);
        }
        globalLoader.classList.add('ui-global-loader-visible');
    }

    /**
     * 隐藏全局加载
     */
    hideGlobal() {
        const globalLoader = document.getElementById('ui-global-loader');
        if (globalLoader) {
            globalLoader.classList.remove('ui-global-loader-visible');
        }
    }
}

// 全局加载管理器实例
const loadingManager = new LoadingManager();

// ==================== 消息流优化 ====================

/**
 * 优化的消息渲染器
 */
class MessageRenderer {
    constructor() {
        this.chunkSize = 100; // 每批处理的字符数
        this.renderDelay = 16; // 渲染间隔(ms)
        this.buffer = '';
        this.isRendering = false;
    }

    /**
     * 流式渲染消息
     */
    async streamRender(element, content, options = {}) {
        const { onUpdate, onComplete, useMarkdown = true } = options;
        
        this.buffer = content;
        this.isRendering = true;
        
        let rendered = '';
        let index = 0;

        const renderChunk = () => {
            if (!this.isRendering) return;

            const chunk = this.buffer.slice(index, index + this.chunkSize);
            index += chunk.length;
            rendered += chunk;

            if (useMarkdown && typeof marked !== 'undefined') {
                element.innerHTML = marked.parse(rendered);
            } else {
                element.textContent = rendered;
            }

            if (onUpdate) onUpdate(rendered);

            if (index < this.buffer.length) {
                requestAnimationFrame(() => setTimeout(renderChunk, this.renderDelay));
            } else {
                this.isRendering = false;
                if (onComplete) onComplete(rendered);
            }
        };

        renderChunk();
    }

    /**
     * 停止渲染
     */
    stop() {
        this.isRendering = false;
    }

    /**
     * 批量渲染消息（用于历史记录）
     */
    renderBatch(container, messages, options = {}) {
        const { batchSize = 10, delay = 50 } = options;
        let index = 0;

        const renderNextBatch = () => {
            const batch = messages.slice(index, index + batchSize);
            index += batch.length;

            batch.forEach(msg => {
                this._renderMessageElement(container, msg);
            });

            if (index < messages.length) {
                setTimeout(renderNextBatch, delay);
            }
        };

        renderNextBatch();
    }

    _renderMessageElement(container, message) {
        // 复用现有的addMessageToUI逻辑
        if (typeof addMessageToUI === 'function') {
            addMessageToUI(message.role, message.content, message.time, 
                message.toolResults, null, message.reasoning);
        }
    }
}

// 全局消息渲染器实例
const messageRenderer = new MessageRenderer();

// ==================== 错误处理和恢复 ====================

/**
 * 错误处理器
 */
class ErrorHandler {
    constructor() {
        this.errorCallbacks = new Map();
        this.retryAttempts = new Map();
        this.maxRetries = 3;
    }

    /**
     * 处理错误
     */
    handle(error, context = {}) {
        const { operation, onRetry, onCancel } = context;
        
        console.error(`[ErrorHandler] ${operation}:`, error);

        // 分类错误
        const errorType = this._classifyError(error);
        
        // 显示用户友好的错误提示
        this._showErrorToast(errorType, error.message);

        // 尝试自动恢复
        if (this._shouldRetry(operation, errorType)) {
            this._scheduleRetry(operation, onRetry);
        }
    }

    /**
     * 分类错误
     */
    _classifyError(error) {
        if (error.name === 'AbortError') return 'cancelled';
        if (error.message?.includes('network')) return 'network';
        if (error.message?.includes('timeout')) return 'timeout';
        if (error.status >= 500) return 'server';
        if (error.status >= 400) return 'client';
        return 'unknown';
    }

    /**
     * 显示错误提示
     */
    _showErrorToast(type, message) {
        const errorMessages = {
            cancelled: '操作已取消',
            network: '网络连接失败，请检查网络',
            timeout: '请求超时，请重试',
            server: '服务器错误，请稍后重试',
            client: '请求错误，请检查输入',
            unknown: '发生错误，请重试'
        };

        if (typeof showToast === 'function') {
            showToast(errorMessages[type] || message, 'error');
        }
    }

    /**
     * 是否应该重试
     */
    _shouldRetry(operation, errorType) {
        const attempts = this.retryAttempts.get(operation) || 0;
        if (attempts >= this.maxRetries) return false;
        
        // 某些错误类型不应该重试
        const nonRetryable = ['cancelled', 'client'];
        return !nonRetryable.includes(errorType);
    }

    /**
     * 安排重试
     */
    _scheduleRetry(operation, onRetry) {
        const attempts = (this.retryAttempts.get(operation) || 0) + 1;
        this.retryAttempts.set(operation, attempts);

        const delay = Math.min(1000 * Math.pow(2, attempts - 1), 10000);
        
        setTimeout(() => {
            if (typeof onRetry === 'function') {
                onRetry();
            }
        }, delay);
    }

    /**
     * 重置重试计数
     */
    reset(operation) {
        this.retryAttempts.delete(operation);
    }
}

// 全局错误处理器实例
const errorHandler = new ErrorHandler();

// ==================== 输入优化 ====================

/**
 * 输入优化器
 */
class InputOptimizer {
    constructor(inputId) {
        this.input = document.getElementById(inputId);
        if (!this.input) return;

        this.history = [];
        this.historyIndex = -1;
        this.maxHistory = 50;

        this._setupEventListeners();
    }

    _setupEventListeners() {
        // 历史记录导航
        this.input.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowUp' && this.input.selectionStart === 0) {
                e.preventDefault();
                this._navigateHistory(-1);
            } else if (e.key === 'ArrowDown' && this.input.selectionStart === this.input.value.length) {
                e.preventDefault();
                this._navigateHistory(1);
            }
        });

        // 自动保存输入
        this.input.addEventListener('input', debounce(() => {
            this._saveToHistory(this.input.value);
        }, 1000));
    }

    _navigateHistory(direction) {
        if (this.history.length === 0) return;

        this.historyIndex += direction;
        this.historyIndex = Math.max(0, Math.min(this.historyIndex, this.history.length - 1));

        this.input.value = this.history[this.historyIndex];
    }

    _saveToHistory(value) {
        if (!value.trim()) return;
        
        this.history.unshift(value);
        if (this.history.length > this.maxHistory) {
            this.history.pop();
        }
        this.historyIndex = -1;
    }
}

// ==================== 平滑滚动优化 ====================

/**
 * 平滑滚动管理器
 */
class SmoothScrollManager {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) return;

        this.isScrolling = false;
        this.scrollTimeout = null;
    }

    /**
     * 平滑滚动到底部
     */
    scrollToBottom(options = {}) {
        const { smooth = true, force = false } = options;
        
        if (!force && this._isNearBottom()) return;

        this.container.scrollTo({
            top: this.container.scrollHeight,
            behavior: smooth ? 'smooth' : 'auto'
        });
    }

    /**
     * 检查是否在底部附近
     */
    _isNearBottom() {
        const threshold = 100;
        return this.container.scrollHeight - this.container.scrollTop - this.container.clientHeight < threshold;
    }

    /**
     * 智能滚动（只在用户在底部时自动滚动）
     */
    smartScroll() {
        if (this._isNearBottom()) {
            this.scrollToBottom({ smooth: true });
        }
    }
}

// ==================== 初始化 ====================

/**
 * 初始化UI优化
 */
function initUIOptimization() {
    // 添加CSS样式
    const style = document.createElement('style');
    style.textContent = `
        /* 加载动画样式 */
        .ui-loader {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 12px;
            padding: 20px;
            opacity: 0;
            transition: opacity 0.3s ease;
        }
        
        .ui-loader-visible {
            opacity: 1;
        }
        
        .ui-loader-hiding {
            opacity: 0;
        }
        
        .ui-loader-overlay {
            position: absolute;
            inset: 0;
            background: rgba(255, 255, 255, 0.9);
            backdrop-filter: blur(4px);
            z-index: 10;
        }
        
        .dark .ui-loader-overlay {
            background: rgba(30, 30, 50, 0.9);
        }
        
        /* 旋转动画 */
        .ui-spinner {
            position: relative;
            width: 40px;
            height: 40px;
        }
        
        .ui-spinner-large {
            width: 60px;
            height: 60px;
        }
        
        .ui-spinner-ring {
            position: absolute;
            inset: 0;
            border: 3px solid transparent;
            border-top-color: var(--primary, #667eea);
            border-radius: 50%;
            animation: ui-spin 1s linear infinite;
        }
        
        @keyframes ui-spin {
            to { transform: rotate(360deg); }
        }
        
        /* 加载点动画 */
        .ui-loading-dots {
            display: flex;
            gap: 6px;
        }
        
        .ui-loading-dots span {
            width: 10px;
            height: 10px;
            background: var(--primary, #667eea);
            border-radius: 50%;
            animation: ui-bounce 1.4s infinite ease-in-out;
        }
        
        .ui-loading-dots span:nth-child(1) { animation-delay: 0s; }
        .ui-loading-dots span:nth-child(2) { animation-delay: 0.2s; }
        .ui-loading-dots span:nth-child(3) { animation-delay: 0.4s; }
        
        @keyframes ui-bounce {
            0%, 60%, 100% { transform: translateY(0) scale(1); opacity: 0.6; }
            30% { transform: translateY(-8px) scale(1.2); opacity: 1; }
        }
        
        /* 骨架屏 */
        .ui-skeleton {
            width: 100%;
            padding: 16px;
        }
        
        .ui-skeleton-line {
            height: 12px;
            background: linear-gradient(90deg, 
                rgba(102, 126, 234, 0.1) 0%, 
                rgba(102, 126, 234, 0.2) 50%, 
                rgba(102, 126, 234, 0.1) 100%);
            background-size: 200% 100%;
            border-radius: 6px;
            margin-bottom: 10px;
            animation: ui-shimmer 1.5s infinite;
        }
        
        @keyframes ui-shimmer {
            0% { background-position: -200% 0; }
            100% { background-position: 200% 0; }
        }
        
        /* 进度条 */
        .ui-progress-bar {
            width: 200px;
            height: 6px;
            background: rgba(102, 126, 234, 0.2);
            border-radius: 3px;
            overflow: hidden;
        }
        
        .ui-progress-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--primary, #667eea), var(--secondary, #764ba2));
            border-radius: 3px;
            transition: width 0.3s ease;
        }
        
        /* 全局加载 */
        .ui-global-loader {
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.5);
            backdrop-filter: blur(8px);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 9999;
            opacity: 0;
            visibility: hidden;
            transition: opacity 0.3s ease, visibility 0.3s ease;
        }
        
        .ui-global-loader-visible {
            opacity: 1;
            visibility: visible;
        }
        
        .ui-global-loader-content {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.95), rgba(250, 250, 255, 0.9));
            padding: 40px 60px;
            border-radius: 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 20px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
        }
        
        .dark .ui-global-loader-content {
            background: linear-gradient(135deg, rgba(30, 30, 50, 0.95), rgba(25, 25, 45, 0.9));
        }
        
        .ui-global-loader-text {
            font-size: 16px;
            color: var(--text-primary, #1a1a2e);
            font-weight: 500;
        }
        
        .ui-loader-text {
            font-size: 13px;
            color: var(--text-secondary, #4a4a6a);
        }
        
        /* 消息进入动画优化 */
        .message {
            animation: messageSlideIn 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        }
        
        @keyframes messageSlideIn {
            from {
                opacity: 0;
                transform: translateY(20px) scale(0.96);
            }
            to {
                opacity: 1;
                transform: translateY(0) scale(1);
            }
        }
        
        /* 打字指示器优化 */
        .typing-indicator-enhanced {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 16px 20px;
            background: linear-gradient(135deg, rgba(102, 126, 234, 0.1), rgba(118, 75, 162, 0.05));
            border-radius: 16px;
            border: 1px solid rgba(102, 126, 234, 0.15);
        }
        
        .typing-indicator-enhanced .dots {
            display: flex;
            gap: 4px;
        }
        
        .typing-indicator-enhanced .dots span {
            width: 8px;
            height: 8px;
            background: var(--primary, #667eea);
            border-radius: 50%;
            animation: typingBounce 1.4s infinite ease-in-out;
        }
        
        .typing-indicator-enhanced .dots span:nth-child(1) { animation-delay: 0s; }
        .typing-indicator-enhanced .dots span:nth-child(2) { animation-delay: 0.16s; }
        .typing-indicator-enhanced .dots span:nth-child(3) { animation-delay: 0.32s; }
        
        @keyframes typingBounce {
            0%, 60%, 100% { transform: translateY(0); }
            30% { transform: translateY(-6px); }
        }
        
        .typing-indicator-enhanced .text {
            font-size: 13px;
            color: var(--text-secondary, #4a4a6a);
            margin-left: 8px;
        }
    `;
    document.head.appendChild(style);

    console.log('✅ UI优化模块已加载');
}

// 页面加载完成后初始化
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initUIOptimization);
} else {
    initUIOptimization();
}

// 导出模块
window.UIOptimization = {
    debounce,
    throttle,
    RequestQueue,
    requestQueue,
    LoadingManager,
    loadingManager,
    MessageRenderer,
    messageRenderer,
    ErrorHandler,
    errorHandler,
    InputOptimizer,
    SmoothScrollManager,
    initUIOptimization
};
