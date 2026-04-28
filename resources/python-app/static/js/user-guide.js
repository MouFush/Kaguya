/**
 * 用户引导系统 - 前端实现
 * 功能: 首次登录引导、使用说明展示、引导流程控制
 */

class UserGuideManager {
    constructor() {
        this.deviceId = this._getDeviceId();
        this.currentSection = 0;
        this.sections = [];
        this.isShowing = false;
        this.guideData = null;
        
        this._init();
    }
    
    /**
     * 初始化
     */
    async _init() {
        // 禁用自动弹出帮助界面
        // const isFirstVisit = await this._checkFirstVisit();
        // if (isFirstVisit) {
        //     setTimeout(() => {
        //         this.showGuide();
        //     }, 1000);
        // }
        
        // 添加帮助按钮
        this._addHelpButton();
    }
    
    /**
     * 获取设备ID
     */
    _getDeviceId() {
        let deviceId = localStorage.getItem('device_id');
        if (!deviceId) {
            deviceId = 'device_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('device_id', deviceId);
        }
        return deviceId;
    }
    
    /**
     * 检查是否是首次访问
     */
    async _checkFirstVisit() {
        try {
            const response = await fetch(`/api/guide/check?device_id=${this.deviceId}`);
            const data = await response.json();
            return data.is_first_visit;
        } catch (error) {
            console.error('检查首次访问失败:', error);
            return false;
        }
    }
    
    /**
     * 获取引导内容
     */
    async _loadGuideContent() {
        try {
            const response = await fetch('/api/guide/content');
            const data = await response.json();
            
            if (data.success) {
                this.guideData = data.data;
                this.sections = this.guideData.sections || [];
            }
        } catch (error) {
            console.error('加载引导内容失败:', error);
        }
    }
    
    /**
     * 显示引导界面
     */
    async showGuide() {
        if (this.isShowing) return;
        
        this.isShowing = true;
        
        // 加载引导内容
        if (!this.guideData) {
            await this._loadGuideContent();
        }
        
        // 创建引导界面
        this._createGuideModal();
        
        // 显示第一个章节
        this.currentSection = 0;
        this._showCurrentSection();
    }
    
    /**
     * 创建引导模态框
     */
    _createGuideModal() {
        // 移除已存在的模态框
        const existingModal = document.getElementById('user-guide-modal');
        if (existingModal) {
            existingModal.remove();
        }
        
        // 创建模态框
        const modal = document.createElement('div');
        modal.id = 'user-guide-modal';
        modal.className = 'user-guide-modal';
        modal.innerHTML = `
            <div class="user-guide-overlay"></div>
            <div class="user-guide-container">
                <div class="user-guide-header">
                    <h2 class="user-guide-title">📖 使用说明</h2>
                    <button class="user-guide-close" onclick="userGuide.closeGuide()">✕</button>
                </div>
                
                <div class="user-guide-progress">
                    <div class="user-guide-progress-bar">
                        <div class="user-guide-progress-fill" id="guide-progress-fill"></div>
                    </div>
                    <span class="user-guide-progress-text" id="guide-progress-text">1 / ${this.sections.length}</span>
                </div>
                
                <div class="user-guide-navigation">
                    ${this.sections.map((section, index) => `
                        <button class="user-guide-nav-item ${index === 0 ? 'active' : ''}" 
                                data-index="${index}"
                                onclick="userGuide.goToSection(${index})">
                            ${section.title}
                        </button>
                    `).join('')}
                </div>
                
                <div class="user-guide-content" id="guide-content">
                    <!-- 内容将在这里动态插入 -->
                </div>
                
                <div class="user-guide-footer">
                    <button class="user-guide-btn user-guide-btn-secondary" id="guide-btn-prev" onclick="userGuide.prevSection()">
                        ← 上一步
                    </button>
                    <button class="user-guide-btn user-guide-btn-primary" id="guide-btn-next" onclick="userGuide.nextSection()">
                        下一步 →
                    </button>
                    <button class="user-guide-btn user-guide-btn-success" id="guide-btn-finish" onclick="userGuide.finishGuide()" style="display: none;">
                        ✓ 完成引导
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // 添加动画
        requestAnimationFrame(() => {
            modal.classList.add('user-guide-visible');
        });
    }
    
    /**
     * 显示当前章节
     */
    _showCurrentSection() {
        if (!this.sections[this.currentSection]) return;
        
        const sectionId = this.sections[this.currentSection].section_id;
        const sectionData = this.guideData.content[sectionId];
        
        // 更新内容
        const contentEl = document.getElementById('guide-content');
        contentEl.innerHTML = `
            <div class="user-guide-section">
                <h3 class="user-guide-section-title">${sectionData.title}</h3>
                <div class="user-guide-section-content">
                    ${this._formatContent(sectionData.content)}
                </div>
            </div>
        `;
        
        // 更新进度
        const progress = ((this.currentSection + 1) / this.sections.length) * 100;
        document.getElementById('guide-progress-fill').style.width = `${progress}%`;
        document.getElementById('guide-progress-text').textContent = 
            `${this.currentSection + 1} / ${this.sections.length}`;
        
        // 更新导航状态
        document.querySelectorAll('.user-guide-nav-item').forEach((item, index) => {
            item.classList.toggle('active', index === this.currentSection);
            item.classList.toggle('completed', index < this.currentSection);
        });
        
        // 更新按钮状态
        document.getElementById('guide-btn-prev').style.display = 
            this.currentSection === 0 ? 'none' : 'inline-block';
        
        if (this.currentSection === this.sections.length - 1) {
            document.getElementById('guide-btn-next').style.display = 'none';
            document.getElementById('guide-btn-finish').style.display = 'inline-block';
        } else {
            document.getElementById('guide-btn-next').style.display = 'inline-block';
            document.getElementById('guide-btn-finish').style.display = 'none';
        }
        
        // 标记章节完成
        this._markSectionCompleted(sectionId);
    }
    
    /**
     * 格式化内容
     */
    _formatContent(content) {
        // 将换行符转换为HTML
        return content
            .trim()
            .split('\n')
            .map(line => {
                // 处理标题
                if (line.startsWith('🎯') || line.startsWith('📦') || line.startsWith('⚙️') || 
                    line.startsWith('🌐') || line.startsWith('🔒') || line.startsWith('📊') ||
                    line.startsWith('📝') || line.startsWith('🔍') || line.startsWith('🏷️') ||
                    line.startsWith('📋') || line.startsWith('🤖') || line.startsWith('🔌') ||
                    line.startsWith('👥') || line.startsWith('📋') || line.startsWith('⚙️') ||
                    line.startsWith('💡') || line.startsWith('⌨️') || line.startsWith('❓') ||
                    line.startsWith('Q:') || line.startsWith('A:')) {
                    return `<h4 class="user-guide-subtitle">${line}</h4>`;
                }
                // 处理列表项
                else if (line.startsWith('•')) {
                    return `<li>${line.substring(1).trim()}</li>`;
                }
                // 处理数字列表
                else if (/^\d+\./.test(line)) {
                    return `<li>${line.substring(line.indexOf('.') + 1).trim()}</li>`;
                }
                // 处理普通段落
                else if (line.trim()) {
                    return `<p>${line}</p>`;
                }
                return '';
            })
            .join('');
    }
    
    /**
     * 跳转到指定章节
     */
    goToSection(index) {
        if (index >= 0 && index < this.sections.length) {
            this.currentSection = index;
            this._showCurrentSection();
        }
    }
    
    /**
     * 上一章
     */
    prevSection() {
        if (this.currentSection > 0) {
            this.currentSection--;
            this._showCurrentSection();
        }
    }
    
    /**
     * 下一章
     */
    nextSection() {
        if (this.currentSection < this.sections.length - 1) {
            this.currentSection++;
            this._showCurrentSection();
        }
    }
    
    /**
     * 完成引导
     */
    async finishGuide() {
        try {
            // 通知服务器引导完成
            await fetch('/api/guide/complete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ device_id: this.deviceId })
            });
        } catch (error) {
            console.error('标记引导完成失败:', error);
        }
        
        this.closeGuide();
        
        // 显示完成提示
        if (typeof showToast === 'function') {
            showToast('🎉 恭喜！您已完成使用说明，开始使用辉夜AI平台吧！', 'success');
        }
    }
    
    /**
     * 关闭引导
     */
    closeGuide() {
        const modal = document.getElementById('user-guide-modal');
        if (modal) {
            modal.classList.remove('user-guide-visible');
            setTimeout(() => {
                modal.remove();
            }, 300);
        }
        this.isShowing = false;
    }
    
    /**
     * 标记章节完成
     */
    async _markSectionCompleted(sectionId) {
        try {
            await fetch('/api/guide/complete-section', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    device_id: this.deviceId,
                    section_id: sectionId 
                })
            });
        } catch (error) {
            console.error('标记章节完成失败:', error);
        }
    }
    
    /**
     * 添加帮助按钮
     */
    _addHelpButton() {
        // 检查是否已存在
        if (document.getElementById('user-guide-help-btn')) return;
        
        const helpBtn = document.createElement('button');
        helpBtn.id = 'user-guide-help-btn';
        helpBtn.className = 'user-guide-help-btn';
        helpBtn.innerHTML = '❓ 帮助';
        helpBtn.title = '查看使用说明';
        helpBtn.onclick = () => this.showGuide();
        
        // 添加到页面（可以根据实际页面结构调整）
        const header = document.querySelector('.header') || document.querySelector('header');
        if (header) {
            header.appendChild(helpBtn);
        } else {
            document.body.appendChild(helpBtn);
        }
    }
}


// 添加CSS样式
const guideStyles = document.createElement('style');
guideStyles.textContent = `
    /* 引导模态框 */
    .user-guide-modal {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        z-index: 10000;
        display: flex;
        align-items: center;
        justify-content: center;
        opacity: 0;
        visibility: hidden;
        transition: opacity 0.3s ease, visibility 0.3s ease;
    }
    
    .user-guide-modal.user-guide-visible {
        opacity: 1;
        visibility: visible;
    }
    
    .user-guide-overlay {
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.6);
        backdrop-filter: blur(4px);
    }
    
    .user-guide-container {
        position: relative;
        width: 90%;
        max-width: 800px;
        max-height: 85vh;
        background: linear-gradient(135deg, #ffffff 0%, #f8f9ff 100%);
        border-radius: 20px;
        box-shadow: 0 25px 80px rgba(0, 0, 0, 0.3);
        display: flex;
        flex-direction: column;
        overflow: hidden;
        transform: scale(0.95);
        transition: transform 0.3s ease;
    }
    
    .user-guide-modal.user-guide-visible .user-guide-container {
        transform: scale(1);
    }
    
    .dark .user-guide-container {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    }
    
    /* 头部 */
    .user-guide-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 20px 24px;
        border-bottom: 1px solid rgba(102, 126, 234, 0.1);
    }
    
    .user-guide-title {
        margin: 0;
        font-size: 20px;
        font-weight: 600;
        color: #1a1a2e;
    }
    
    .dark .user-guide-title {
        color: #ffffff;
    }
    
    .user-guide-close {
        background: none;
        border: none;
        font-size: 20px;
        color: #666;
        cursor: pointer;
        padding: 4px 8px;
        border-radius: 8px;
        transition: all 0.2s ease;
    }
    
    .user-guide-close:hover {
        background: rgba(102, 126, 234, 0.1);
        color: #667eea;
    }
    
    /* 进度条 */
    .user-guide-progress {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px 24px;
        background: rgba(102, 126, 234, 0.05);
    }
    
    .user-guide-progress-bar {
        flex: 1;
        height: 6px;
        background: rgba(102, 126, 234, 0.2);
        border-radius: 3px;
        overflow: hidden;
    }
    
    .user-guide-progress-fill {
        height: 100%;
        background: linear-gradient(90deg, #667eea, #764ba2);
        border-radius: 3px;
        transition: width 0.3s ease;
    }
    
    .user-guide-progress-text {
        font-size: 13px;
        color: #666;
        font-weight: 500;
    }
    
    .dark .user-guide-progress-text {
        color: #aaa;
    }
    
    /* 导航 */
    .user-guide-navigation {
        display: flex;
        gap: 8px;
        padding: 12px 24px;
        overflow-x: auto;
        border-bottom: 1px solid rgba(102, 126, 234, 0.1);
        background: rgba(102, 126, 234, 0.02);
    }
    
    .user-guide-nav-item {
        padding: 8px 16px;
        border: none;
        background: transparent;
        color: #666;
        font-size: 13px;
        border-radius: 20px;
        cursor: pointer;
        white-space: nowrap;
        transition: all 0.2s ease;
    }
    
    .user-guide-nav-item:hover {
        background: rgba(102, 126, 234, 0.1);
    }
    
    .user-guide-nav-item.active {
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white;
    }
    
    .user-guide-nav-item.completed {
        color: #667eea;
    }
    
    .user-guide-nav-item.completed::after {
        content: ' ✓';
    }
    
    .dark .user-guide-nav-item {
        color: #aaa;
    }
    
    /* 内容区 */
    .user-guide-content {
        flex: 1;
        overflow-y: auto;
        padding: 24px;
    }
    
    .user-guide-section {
        animation: guideFadeIn 0.3s ease;
    }
    
    @keyframes guideFadeIn {
        from {
            opacity: 0;
            transform: translateY(10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .user-guide-section-title {
        margin: 0 0 16px 0;
        font-size: 22px;
        font-weight: 600;
        color: #1a1a2e;
    }
    
    .dark .user-guide-section-title {
        color: #ffffff;
    }
    
    .user-guide-section-content {
        color: #4a4a6a;
        line-height: 1.8;
    }
    
    .dark .user-guide-section-content {
        color: #b8b8d0;
    }
    
    .user-guide-section-content h4 {
        margin: 20px 0 12px 0;
        font-size: 16px;
        font-weight: 600;
        color: #667eea;
    }
    
    .user-guide-section-content p {
        margin: 0 0 12px 0;
    }
    
    .user-guide-section-content ul {
        margin: 0 0 16px 0;
        padding-left: 20px;
    }
    
    .user-guide-section-content li {
        margin: 8px 0;
    }
    
    /* 底部 */
    .user-guide-footer {
        display: flex;
        justify-content: space-between;
        padding: 16px 24px;
        border-top: 1px solid rgba(102, 126, 234, 0.1);
        background: rgba(102, 126, 234, 0.02);
    }
    
    .user-guide-btn {
        padding: 10px 20px;
        border: none;
        border-radius: 10px;
        font-size: 14px;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s ease;
    }
    
    .user-guide-btn-primary {
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white;
    }
    
    .user-guide-btn-primary:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
    }
    
    .user-guide-btn-secondary {
        background: rgba(102, 126, 234, 0.1);
        color: #667eea;
    }
    
    .user-guide-btn-secondary:hover {
        background: rgba(102, 126, 234, 0.2);
    }
    
    .user-guide-btn-success {
        background: linear-gradient(135deg, #48bb78, #38a169);
        color: white;
    }
    
    .user-guide-btn-success:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(72, 187, 120, 0.4);
    }
    
    /* 帮助按钮 */
    .user-guide-help-btn {
        position: fixed;
        bottom: 20px;
        right: 20px;
        padding: 12px 20px;
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white;
        border: none;
        border-radius: 25px;
        font-size: 14px;
        font-weight: 500;
        cursor: pointer;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        transition: all 0.3s ease;
        z-index: 9999;
    }
    
    .user-guide-help-btn:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5);
    }
    
    /* 响应式 */
    @media (max-width: 768px) {
        .user-guide-container {
            width: 95%;
            max-height: 90vh;
        }
        
        .user-guide-navigation {
            padding: 8px 16px;
        }
        
        .user-guide-nav-item {
            padding: 6px 12px;
            font-size: 12px;
        }
        
        .user-guide-content {
            padding: 16px;
        }
        
        .user-guide-help-btn {
            bottom: 10px;
            right: 10px;
            padding: 10px 16px;
            font-size: 13px;
        }
    }
`;

document.head.appendChild(guideStyles);


// 初始化用户引导系统
let userGuide;

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        userGuide = new UserGuideManager();
    });
} else {
    userGuide = new UserGuideManager();
}


// 导出全局函数供HTML调用
window.userGuide = {
    show: () => userGuide.showGuide(),
    close: () => userGuide.closeGuide(),
    next: () => userGuide.nextSection(),
    prev: () => userGuide.prevSection(),
    goTo: (index) => userGuide.goToSection(index),
    finish: () => userGuide.finishGuide()
};


console.log('✅ 用户引导系统已加载');
