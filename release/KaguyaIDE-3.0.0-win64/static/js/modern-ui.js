/**
 * 辉夜AI平台 - 现代化UI交互脚本
 * Modern UI Interactions
 */

class ModernUI {
    constructor() {
        this.init();
    }

    init() {
        this.initAnimations();
        this.initTooltips();
        this.initScrollEffects();
        this.initMessageAnimations();
        this.initTypingIndicator();
        this.initThemeToggle();
    }

    // ==================== 动画初始化 ====================
    initAnimations() {
        // 为元素添加进入动画
        const animatedElements = document.querySelectorAll('.animate-on-load');
        animatedElements.forEach((el, index) => {
            el.style.opacity = '0';
            setTimeout(() => {
                el.classList.add('fade-in');
                el.style.opacity = '1';
            }, index * 100);
        });

        // 卡片悬停效果
        document.querySelectorAll('.glass-card, .feature-card').forEach(card => {
            card.addEventListener('mouseenter', () => {
                card.style.transform = 'translateY(-4px)';
            });
            card.addEventListener('mouseleave', () => {
                card.style.transform = 'translateY(0)';
            });
        });
    }

    // ==================== 工具提示 ====================
    initTooltips() {
        document.querySelectorAll('[data-tooltip]').forEach(el => {
            el.classList.add('tooltip');
        });
    }

    // ==================== 滚动效果 ====================
    initScrollEffects() {
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('slide-up');
                    observer.unobserve(entry.target);
                }
            });
        }, observerOptions);

        document.querySelectorAll('.scroll-animate').forEach(el => {
            el.style.opacity = '0';
            observer.observe(el);
        });
    }

    // ==================== 消息动画 ====================
    initMessageAnimations() {
        // 监听新消息
        const chatContainer = document.getElementById('chat-container');
        if (chatContainer) {
            const observer = new MutationObserver((mutations) => {
                mutations.forEach(mutation => {
                    mutation.addedNodes.forEach(node => {
                        if (node.nodeType === 1 && node.classList.contains('message')) {
                            node.style.animation = 'none';
                            node.offsetHeight; // 触发重排
                            node.style.animation = 'messageSlide 0.3s ease-out';
                        }
                    });
                });
            });

            observer.observe(chatContainer, { childList: true });
        }
    }

    // ==================== 打字指示器 ====================
    initTypingIndicator() {
        const indicator = document.querySelector('.typing-indicator');
        if (indicator) {
            const dots = indicator.querySelectorAll('.dot');
            dots.forEach((dot, index) => {
                dot.style.animationDelay = `${index * 0.15}s`;
            });
        }
    }

    // ==================== 主题切换 ====================
    initThemeToggle() {
        const themeToggle = document.getElementById('theme-toggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', () => {
                document.body.classList.toggle('dark');
                const isDark = document.body.classList.contains('dark');
                localStorage.setItem('theme', isDark ? 'dark' : 'light');
            });

            // 恢复保存的主题
            const savedTheme = localStorage.getItem('theme');
            if (savedTheme === 'dark') {
                document.body.classList.add('dark');
            }
        }
    }

    // ==================== 按钮波纹效果 ====================
    addRippleEffect(button) {
        button.addEventListener('click', function(e) {
            const ripple = document.createElement('span');
            const rect = this.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;

            ripple.style.cssText = `
                position: absolute;
                width: ${size}px;
                height: ${size}px;
                left: ${x}px;
                top: ${y}px;
                background: rgba(255, 255, 255, 0.3);
                border-radius: 50%;
                transform: scale(0);
                animation: ripple 0.6s ease-out;
                pointer-events: none;
            `;

            this.style.position = 'relative';
            this.style.overflow = 'hidden';
            this.appendChild(ripple);

            setTimeout(() => ripple.remove(), 600);
        });
    }

    // ==================== 骨架屏 ====================
    showSkeleton(container, count = 3) {
        container.innerHTML = '';
        for (let i = 0; i < count; i++) {
            const skeleton = document.createElement('div');
            skeleton.className = 'skeleton';
            skeleton.style.cssText = `
                height: 60px;
                margin-bottom: 12px;
                border-radius: 12px;
            `;
            container.appendChild(skeleton);
        }
    }

    hideSkeleton(container) {
        const skeletons = container.querySelectorAll('.skeleton');
        skeletons.forEach(s => s.remove());
    }

    // ==================== 通知提示 ====================
    showNotification(message, type = 'info', duration = 3000) {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 16px 24px;
            background: var(--bg-glass);
            backdrop-filter: blur(20px);
            border: 1px solid var(--border-light);
            border-radius: var(--radius-lg);
            box-shadow: var(--shadow-lg);
            z-index: 9999;
            animation: slideInRight 0.3s ease-out;
            display: flex;
            align-items: center;
            gap: 12px;
        `;

        const icons = {
            success: '✅',
            error: '❌',
            warning: '⚠️',
            info: 'ℹ️'
        };

        notification.innerHTML = `
            <span style="font-size: 20px;">${icons[type]}</span>
            <span style="font-size: 14px; font-weight: 500;">${message}</span>
        `;

        document.body.appendChild(notification);

        setTimeout(() => {
            notification.style.animation = 'slideOutRight 0.3s ease-out';
            setTimeout(() => notification.remove(), 300);
        }, duration);
    }

    // ==================== 输入框增强 ====================
    enhanceInput(input) {
        // 自动调整高度
        input.addEventListener('input', () => {
            input.style.height = 'auto';
            input.style.height = input.scrollHeight + 'px';
        });

        // 聚焦效果
        input.addEventListener('focus', () => {
            input.parentElement?.classList.add('input-focused');
        });

        input.addEventListener('blur', () => {
            input.parentElement?.classList.remove('input-focused');
        });
    }

    // ==================== 标签页切换动画 ====================
    switchTab(tabGroup, activeTab) {
        const tabs = tabGroup.querySelectorAll('.tab');
        const contents = tabGroup.querySelectorAll('.tab-content');

        tabs.forEach(tab => {
            tab.classList.remove('active');
            if (tab.dataset.target === activeTab) {
                tab.classList.add('active');
            }
        });

        contents.forEach(content => {
            if (content.id === activeTab) {
                content.style.display = 'block';
                content.style.animation = 'fadeIn 0.3s ease-out';
            } else {
                content.style.display = 'none';
            }
        });
    }

    // ==================== 进度条动画 ====================
    animateProgress(element, targetValue, duration = 1000) {
        const startValue = parseFloat(element.style.width) || 0;
        const startTime = performance.now();

        const animate = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const easeProgress = 1 - Math.pow(1 - progress, 3); // ease-out cubic
            const currentValue = startValue + (targetValue - startValue) * easeProgress;

            element.style.width = currentValue + '%';

            if (progress < 1) {
                requestAnimationFrame(animate);
            }
        };

        requestAnimationFrame(animate);
    }

    // ==================== 数字计数动画 ====================
    animateNumber(element, targetValue, duration = 1000) {
        const startValue = parseInt(element.textContent) || 0;
        const startTime = performance.now();

        const animate = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const easeProgress = 1 - Math.pow(1 - progress, 3);
            const currentValue = Math.floor(startValue + (targetValue - startValue) * easeProgress);

            element.textContent = currentValue.toLocaleString();

            if (progress < 1) {
                requestAnimationFrame(animate);
            }
        };

        requestAnimationFrame(animate);
    }
}

// ==================== CSS动画关键帧 ====================
const style = document.createElement('style');
style.textContent = `
    @keyframes ripple {
        to {
            transform: scale(4);
            opacity: 0;
        }
    }

    @keyframes slideInRight {
        from {
            opacity: 0;
            transform: translateX(100px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }

    @keyframes slideOutRight {
        from {
            opacity: 1;
            transform: translateX(0);
        }
        to {
            opacity: 0;
            transform: translateX(100px);
        }
    }

    @keyframes messageSlide {
        from {
            opacity: 0;
            transform: translateY(20px) scale(0.95);
        }
        to {
            opacity: 1;
            transform: translateY(0) scale(1);
        }
    }

    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }

    @keyframes slideUp {
        from {
            opacity: 0;
            transform: translateY(30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    .input-focused {
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }
`;
document.head.appendChild(style);

// 初始化
const modernUI = new ModernUI();

// 导出供其他模块使用
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ModernUI;
}
