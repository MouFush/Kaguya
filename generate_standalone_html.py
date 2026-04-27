# -*- coding: utf-8 -*-
"""
生成嵌入Markdown内容的HTML文件
解决CORS问题：将Markdown内容直接嵌入HTML中
"""

import os

# 读取Markdown文件
md_path = r"c:\Users\林智涵\.conda\MiniMind_Complete_Tutorial.md"
html_path = r"c:\Users\林智涵\.conda\MiniMind_Tutorial_Viewer_Standalone.html"

with open(md_path, 'r', encoding='utf-8') as f:
    markdown_content = f.read()

# 转义JavaScript字符串
def escape_js_string(s):
    return s.replace('\\', '\\\\').replace('`', '\\`').replace('$', '\\$')

escaped_md = escape_js_string(markdown_content)

# HTML模板
html_template = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MiniMind 完整代码教学指南</title>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/highlight.js@11.9.0/lib/highlight.min.js"></script>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/highlight.js@11.9.0/styles/github-dark.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        :root {
            --bg-primary: #0d1117;
            --bg-secondary: #161b22;
            --bg-tertiary: #21262d;
            --bg-hover: #30363d;
            --text-primary: #e6edf3;
            --text-secondary: #8b949e;
            --text-muted: #6e7681;
            --accent: #58a6ff;
            --accent-hover: #79c0ff;
            --accent-glow: rgba(88, 166, 255, 0.3);
            --border: #30363d;
            --code-bg: #0d1117;
            --success: #3fb950;
            --warning: #d29922;
            --purple: #a371f7;
            --sidebar-width: 320px;
            --header-height: 56px;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans SC', Helvetica, Arial, sans-serif;
            background-color: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.75;
            overflow-x: hidden;
        }
        ::-webkit-scrollbar { width: 10px; height: 10px; }
        ::-webkit-scrollbar-track { background: var(--bg-secondary); }
        ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 5px; }
        ::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }
        
        .header {
            position: fixed; top: 0; left: 0; right: 0;
            height: var(--header-height);
            background: rgba(22, 27, 34, 0.95);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--border);
            display: flex; align-items: center;
            padding: 0 24px;
            z-index: 1000;
        }
        .header-left { display: flex; align-items: center; gap: 16px; }
        .logo { display: flex; align-items: center; gap: 10px; }
        .logo-icon {
            width: 32px; height: 32px;
            background: linear-gradient(135deg, var(--accent), var(--purple));
            border-radius: 8px;
            display: flex; align-items: center; justify-content: center;
            font-weight: bold; font-size: 16px;
        }
        .header h1 { font-size: 1.1rem; color: var(--text-primary); font-weight: 600; }
        .header-controls { margin-left: auto; display: flex; gap: 8px; align-items: center; }
        .btn {
            padding: 8px 14px;
            border-radius: 6px;
            border: 1px solid var(--border);
            background: var(--bg-tertiary);
            color: var(--text-primary);
            cursor: pointer;
            font-size: 13px;
            font-weight: 500;
            transition: all 0.2s;
            display: flex; align-items: center; gap: 6px;
        }
        .btn:hover { background: var(--bg-hover); border-color: var(--text-muted); }
        .btn-primary { background: var(--accent); border-color: var(--accent); color: white; }
        .btn-primary:hover { background: var(--accent-hover); border-color: var(--accent-hover); }
        
        .font-controls {
            display: flex; align-items: center; gap: 4px;
            padding: 4px;
            background: var(--bg-tertiary);
            border-radius: 6px;
            border: 1px solid var(--border);
        }
        .font-btn {
            width: 28px; height: 28px;
            border: none;
            background: transparent;
            color: var(--text-secondary);
            cursor: pointer;
            border-radius: 4px;
            font-size: 16px;
            display: flex; align-items: center; justify-content: center;
        }
        .font-btn:hover { background: var(--bg-hover); color: var(--text-primary); }
        .font-size-display { min-width: 36px; text-align: center; font-size: 12px; color: var(--text-secondary); }
        
        .progress-bar {
            position: fixed;
            top: var(--header-height);
            left: var(--sidebar-width);
            right: 0;
            height: 3px;
            background: var(--bg-tertiary);
            z-index: 999;
            transition: left 0.3s;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--accent), var(--purple));
            width: 0%;
            transition: width 0.1s;
            box-shadow: 0 0 10px var(--accent-glow);
        }
        
        .container {
            display: flex;
            margin-top: var(--header-height);
            min-height: calc(100vh - var(--header-height));
        }
        
        .sidebar {
            width: var(--sidebar-width);
            background: var(--bg-secondary);
            border-right: 1px solid var(--border);
            position: fixed;
            top: var(--header-height);
            left: 0;
            bottom: 0;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            transition: transform 0.3s ease;
            z-index: 100;
        }
        .sidebar.collapsed { transform: translateX(-100%); }
        
        .sidebar-header {
            padding: 16px 20px;
            border-bottom: 1px solid var(--border);
            background: var(--bg-tertiary);
        }
        .search-box { position: relative; }
        .search-input {
            width: 100%;
            padding: 10px 12px 10px 36px;
            border-radius: 8px;
            border: 1px solid var(--border);
            background: var(--bg-primary);
            color: var(--text-primary);
            font-size: 14px;
            transition: all 0.2s;
        }
        .search-input:focus {
            outline: none;
            border-color: var(--accent);
            box-shadow: 0 0 0 3px var(--accent-glow);
        }
        .search-icon {
            position: absolute;
            left: 12px;
            top: 50%;
            transform: translateY(-50%);
            color: var(--text-muted);
            font-size: 14px;
        }
        
        .sidebar-content { flex: 1; overflow-y: auto; padding: 12px 0; }
        .toc-section { padding: 8px 16px; margin-bottom: 4px; }
        .toc-section-title {
            font-size: 11px;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            padding: 4px 4px 8px;
        }
        .toc-item {
            display: flex;
            align-items: center;
            padding: 8px 12px;
            color: var(--text-secondary);
            text-decoration: none;
            font-size: 13px;
            border-radius: 6px;
            margin: 2px 4px;
            transition: all 0.15s;
            cursor: pointer;
            border-left: 2px solid transparent;
        }
        .toc-item:hover { color: var(--text-primary); background: var(--bg-tertiary); }
        .toc-item.active { color: var(--accent); background: rgba(88, 166, 255, 0.1); border-left-color: var(--accent); }
        .toc-item.level-2 { padding-left: 12px; font-weight: 500; }
        .toc-item.level-3 { padding-left: 28px; font-size: 12px; }
        .toc-item.level-4 { padding-left: 44px; font-size: 11px; color: var(--text-muted); }
        .toc-number { min-width: 24px; color: var(--text-muted); font-size: 11px; }
        
        .main-content { flex: 1; margin-left: var(--sidebar-width); transition: margin-left 0.3s; }
        .main-content.expanded { margin-left: 0; }
        .content-wrapper { max-width: 900px; margin: 0 auto; padding: 40px 60px 100px; }
        
        .markdown-body { font-size: 16px; }
        .markdown-body h1 {
            font-size: 2.25rem;
            font-weight: 700;
            padding-bottom: 0.4em;
            border-bottom: 1px solid var(--border);
            margin: 0 0 24px;
            line-height: 1.3;
            background: linear-gradient(135deg, var(--text-primary), var(--accent));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .markdown-body h2 {
            font-size: 1.75rem;
            font-weight: 600;
            padding-bottom: 0.3em;
            border-bottom: 1px solid var(--border);
            margin: 48px 0 20px;
            line-height: 1.4;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .markdown-body h2::before {
            content: '';
            width: 4px;
            height: 28px;
            background: linear-gradient(180deg, var(--accent), var(--purple));
            border-radius: 2px;
        }
        .markdown-body h3 { font-size: 1.35rem; font-weight: 600; margin: 32px 0 16px; color: var(--text-primary); line-height: 1.4; }
        .markdown-body h4 { font-size: 1.1rem; font-weight: 600; margin: 24px 0 12px; color: var(--accent); }
        .markdown-body h5 { font-size: 1rem; font-weight: 600; margin: 20px 0 10px; }
        .markdown-body h6 { font-size: 0.9rem; font-weight: 600; margin: 16px 0 8px; color: var(--text-secondary); }
        .markdown-body p { margin-bottom: 16px; text-align: justify; }
        .markdown-body ul, .markdown-body ol { padding-left: 2em; margin-bottom: 16px; }
        .markdown-body li { margin-bottom: 6px; }
        .markdown-body li::marker { color: var(--accent); }
        .markdown-body code {
            background: var(--bg-tertiary);
            padding: 0.2em 0.5em;
            border-radius: 6px;
            font-size: 0.875em;
            font-family: 'Fira Code', 'JetBrains Mono', 'Consolas', monospace;
            border: 1px solid var(--border);
        }
        .markdown-body pre {
            background: var(--code-bg);
            border-radius: 12px;
            padding: 20px;
            overflow-x: auto;
            margin: 20px 0;
            border: 1px solid var(--border);
            position: relative;
        }
        .markdown-body pre code {
            background: transparent;
            padding: 0;
            border: none;
            font-size: 14px;
            line-height: 1.6;
        }
        .markdown-body table { width: 100%; border-collapse: collapse; margin: 20px 0; border-radius: 8px; overflow: hidden; }
        .markdown-body th, .markdown-body td { padding: 12px 16px; border: 1px solid var(--border); text-align: left; }
        .markdown-body th { background: var(--bg-tertiary); font-weight: 600; color: var(--text-primary); }
        .markdown-body tr:nth-child(even) { background: rgba(22, 27, 34, 0.5); }
        .markdown-body tr:hover { background: var(--bg-tertiary); }
        .markdown-body blockquote {
            border-left: 4px solid var(--accent);
            padding: 12px 20px;
            margin: 20px 0;
            background: rgba(88, 166, 255, 0.05);
            border-radius: 0 8px 8px 0;
            color: var(--text-secondary);
        }
        .markdown-body blockquote p { margin-bottom: 0; }
        .markdown-body hr { border: none; height: 2px; background: linear-gradient(90deg, transparent, var(--border), transparent); margin: 40px 0; }
        .markdown-body a { color: var(--accent); text-decoration: none; border-bottom: 1px solid transparent; transition: border-color 0.2s; }
        .markdown-body a:hover { border-bottom-color: var(--accent); }
        .markdown-body img { max-width: 100%; border-radius: 12px; margin: 20px 0; border: 1px solid var(--border); }
        
        .code-block-wrapper { position: relative; margin: 20px 0; }
        .code-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 16px;
            background: var(--bg-tertiary);
            border: 1px solid var(--border);
            border-bottom: none;
            border-radius: 12px 12px 0 0;
        }
        .code-lang { font-size: 12px; color: var(--text-secondary); font-weight: 500; text-transform: uppercase; }
        .code-actions { display: flex; gap: 8px; }
        .copy-btn {
            padding: 4px 10px;
            background: var(--bg-hover);
            border: 1px solid var(--border);
            border-radius: 4px;
            color: var(--text-secondary);
            cursor: pointer;
            font-size: 11px;
            transition: all 0.2s;
        }
        .copy-btn:hover { background: var(--accent); border-color: var(--accent); color: white; }
        .code-block-wrapper pre { margin: 0; border-radius: 0 0 12px 12px; }
        
        .back-to-top {
            position: fixed;
            bottom: 30px;
            right: 30px;
            width: 48px;
            height: 48px;
            border-radius: 50%;
            background: linear-gradient(135deg, var(--accent), var(--purple));
            color: white;
            border: none;
            cursor: pointer;
            font-size: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 4px 20px rgba(88, 166, 255, 0.3);
            transition: all 0.3s;
            opacity: 0;
            transform: translateY(20px);
            z-index: 100;
        }
        .back-to-top.show { opacity: 1; transform: translateY(0); }
        .back-to-top:hover { transform: translateY(-3px); box-shadow: 0 6px 24px rgba(88, 166, 255, 0.4); }
        
        .reading-time {
            font-size: 12px;
            color: var(--text-muted);
            padding: 8px 20px;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            gap: 6px;
        }
        
        .anchor-link {
            opacity: 0;
            margin-left: 8px;
            color: var(--text-muted);
            font-size: 0.8em;
            transition: opacity 0.2s;
        }
        .markdown-body h1:hover .anchor-link,
        .markdown-body h2:hover .anchor-link,
        .markdown-body h3:hover .anchor-link,
        .markdown-body h4:hover .anchor-link { opacity: 1; }
        
        .mobile-menu-btn {
            display: none;
            padding: 8px;
            background: transparent;
            border: 1px solid var(--border);
            border-radius: 6px;
            color: var(--text-primary);
            cursor: pointer;
            margin-right: 12px;
        }
        @media (max-width: 768px) {
            .mobile-menu-btn { display: flex; }
            .sidebar { transform: translateX(-100%); }
            .sidebar.mobile-open { transform: translateX(0); }
            .main-content { margin-left: 0; }
            .progress-bar { left: 0; }
            .content-wrapper { padding: 20px 16px 60px; }
            .markdown-body h1 { font-size: 1.75rem; }
            .markdown-body h2 { font-size: 1.4rem; }
            .markdown-body h3 { font-size: 1.2rem; }
            .header h1 { font-size: 0.95rem; }
            .header-controls .btn span { display: none; }
        }
        
        .overlay {
            display: none;
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0, 0, 0, 0.5);
            z-index: 99;
        }
        .overlay.show { display: block; }
        
        @media print {
            .header, .sidebar, .progress-bar, .back-to-top { display: none !important; }
            .main-content { margin-left: 0 !important; }
            .content-wrapper { max-width: 100%; padding: 0; }
            body { background: white; color: black; }
        }
    </style>
</head>
<body>
    <header class="header">
        <div class="header-left">
            <button class="mobile-menu-btn" onclick="toggleMobileSidebar()">☰</button>
            <div class="logo">
                <div class="logo-icon">M</div>
                <h1>MiniMind 完整代码教学指南</h1>
            </div>
        </div>
        <div class="header-controls">
            <div class="font-controls">
                <button class="font-btn" onclick="changeFontSize(-1)">−</button>
                <span class="font-size-display" id="fontSizeDisplay">16px</span>
                <button class="font-btn" onclick="changeFontSize(1)">+</button>
            </div>
            <button class="btn" onclick="toggleSidebar()">
                <span>📁</span>
                <span>目录</span>
            </button>
            <button class="btn" onclick="toggleTheme()">
                <span id="themeIcon">🌙</span>
                <span>主题</span>
            </button>
            <button class="btn btn-primary" onclick="window.print()">
                <span>🖨️</span>
                <span>打印</span>
            </button>
        </div>
    </header>

    <div class="progress-bar">
        <div class="progress-fill" id="progressFill"></div>
    </div>

    <div class="overlay" id="overlay" onclick="closeMobileSidebar()"></div>

    <div class="container">
        <nav class="sidebar" id="sidebar">
            <div class="sidebar-header">
                <div class="search-box">
                    <span class="search-icon">🔍</span>
                    <input type="text" class="search-input" placeholder="搜索目录..." id="searchInput" oninput="filterToc()">
                </div>
            </div>
            <div class="reading-time" id="readingTime">
                📖 预计阅读时间：计算中...
            </div>
            <div class="sidebar-content" id="tocContainer"></div>
        </nav>

        <main class="main-content" id="mainContent">
            <div class="content-wrapper">
                <div class="markdown-body" id="content"></div>
            </div>
        </main>
    </div>

    <button class="back-to-top" id="backToTop" onclick="scrollToTop()">↑</button>

    <script>
        // 嵌入的Markdown内容
        const markdownContent = `''' + escaped_md + '''`;

        let headings = [];
        let currentFontSize = 16;
        let currentHeadingIndex = 0;
        let isDarkTheme = true;

        // 渲染Markdown
        function renderMarkdown() {
            const contentDiv = document.getElementById('content');
            
            marked.setOptions({
                highlight: function(code, lang) {
                    if (lang && hljs.getLanguage(lang)) {
                        return hljs.highlight(code, { language: lang }).value;
                    }
                    return hljs.highlightAuto(code).value;
                },
                breaks: true,
                gfm: true
            });

            contentDiv.innerHTML = marked.parse(markdownContent);

            // 为代码块添加包装和按钮
            document.querySelectorAll('pre').forEach((pre, index) => {
                const wrapper = document.createElement('div');
                wrapper.className = 'code-block-wrapper';
                
                const code = pre.querySelector('code');
                const langClass = code ? code.className.match(/language-(\\w+)/) : null;
                const lang = langClass ? langClass[1] : 'code';
                
                const header = document.createElement('div');
                header.className = 'code-header';
                header.innerHTML = '<span class="code-lang">' + lang + '</span><div class="code-actions"><button class="copy-btn" onclick="copyCode(this, ' + index + ')">复制代码</button></div>';
                
                pre.parentNode.insertBefore(wrapper, pre);
                wrapper.appendChild(header);
                wrapper.appendChild(pre);
            });

            // 提取标题并添加锚点
            headings = [];
            document.querySelectorAll('h1, h2, h3, h4').forEach((heading, index) => {
                const id = 'heading-' + index;
                heading.id = id;
                
                const anchor = document.createElement('a');
                anchor.className = 'anchor-link';
                anchor.href = '#' + id;
                anchor.textContent = '¶';
                heading.appendChild(anchor);
                
                headings.push({
                    id: id,
                    text: heading.textContent.replace('¶', '').trim(),
                    level: parseInt(heading.tagName.substring(1)),
                    element: heading
                });
            });
            
            generateToc();
            calculateReadingTime();
            setupScrollListener();
        }

        // 生成目录
        function generateToc() {
            const tocContainer = document.getElementById('tocContainer');
            tocContainer.innerHTML = '';

            let currentSection = null;
            let sectionItems = [];

            headings.forEach((heading, index) => {
                if (heading.level === 2) {
                    if (currentSection && sectionItems.length > 0) {
                        tocContainer.appendChild(createTocSection(currentSection, sectionItems));
                    }
                    currentSection = heading;
                    sectionItems = [];
                } else if (heading.level <= 4) {
                    sectionItems.push({ ...heading, index });
                }
            });

            if (currentSection && sectionItems.length > 0) {
                tocContainer.appendChild(createTocSection(currentSection, sectionItems));
            }
        }

        // 创建目录section
        function createTocSection(section, items) {
            const sectionDiv = document.createElement('div');
            sectionDiv.className = 'toc-section';

            const titleDiv = document.createElement('div');
            titleDiv.className = 'toc-section-title';
            titleDiv.textContent = section.text;
            sectionDiv.appendChild(titleDiv);

            items.forEach(item => {
                const link = document.createElement('a');
                link.className = 'toc-item level-' + item.level;
                link.innerHTML = '<span class="toc-number">' + (item.index + 1) + '.</span><span>' + item.text + '</span>';
                link.onclick = (e) => {
                    e.preventDefault();
                    document.getElementById(item.id).scrollIntoView({ behavior: 'smooth' });
                    closeMobileSidebar();
                };
                sectionDiv.appendChild(link);
            });

            return sectionDiv;
        }

        // 计算阅读时间
        function calculateReadingTime() {
            const text = markdownContent.replace(/```[\\s\\S]*?```/g, '').replace(/`[^`]*`/g, '').replace(/[#*\\[\\]()>|-]/g, '');
            const wordCount = text.length;
            const readingTime = Math.ceil(wordCount / 500);
            
            document.getElementById('readingTime').innerHTML = '📖 预计阅读时间：约 ' + readingTime + ' 分钟 | 共 ' + Math.floor(wordCount / 1000) + 'k 字';
        }

        // 更新活动目录项
        function updateActiveToc() {
            let currentHeading = null;
            
            headings.forEach((heading, index) => {
                const element = heading.element;
                if (element) {
                    const rect = element.getBoundingClientRect();
                    if (rect.top <= 120) {
                        currentHeading = index;
                    }
                }
            });

            document.querySelectorAll('.toc-item').forEach((item, index) => {
                item.classList.remove('active');
            });

            if (currentHeading !== null) {
                const activeItems = document.querySelectorAll('.toc-item');
                activeItems.forEach(item => {
                    if (item.textContent.includes(headings[currentHeading].text)) {
                        item.classList.add('active');
                    }
                });
            }

            currentHeadingIndex = currentHeading || 0;
        }

        // 滚动监听
        function setupScrollListener() {
            let ticking = false;
            
            window.addEventListener('scroll', () => {
                if (!ticking) {
                    requestAnimationFrame(() => {
                        updateProgress();
                        updateActiveToc();
                        updateBackToTop();
                        ticking = false;
                    });
                    ticking = true;
                }
            });
        }

        // 更新进度条
        function updateProgress() {
            const scrollTop = window.scrollY;
            const docHeight = document.documentElement.scrollHeight - window.innerHeight;
            const progress = Math.min((scrollTop / docHeight) * 100, 100);
            document.getElementById('progressFill').style.width = progress + '%';
        }

        // 更新回到顶部按钮
        function updateBackToTop() {
            const backToTop = document.getElementById('backToTop');
            if (window.scrollY > 300) {
                backToTop.classList.add('show');
            } else {
                backToTop.classList.remove('show');
            }
        }

        // 目录搜索过滤
        function filterToc() {
            const searchText = document.getElementById('searchInput').value.toLowerCase();
            document.querySelectorAll('.toc-section').forEach(section => {
                const title = section.querySelector('.toc-section-title').textContent.toLowerCase();
                const items = section.querySelectorAll('.toc-item');
                let hasMatch = title.includes(searchText);
                
                items.forEach(item => {
                    const text = item.textContent.toLowerCase();
                    if (text.includes(searchText)) {
                        item.style.display = 'flex';
                        hasMatch = true;
                    } else {
                        item.style.display = searchText ? 'none' : 'flex';
                    }
                });
                
                section.style.display = hasMatch || !searchText ? 'block' : 'none';
            });
        }

        // 切换侧边栏
        function toggleSidebar() {
            const sidebar = document.getElementById('sidebar');
            const mainContent = document.getElementById('mainContent');
            const progressBar = document.querySelector('.progress-bar');
            
            sidebar.classList.toggle('collapsed');
            mainContent.classList.toggle('expanded');
            
            if (sidebar.classList.contains('collapsed')) {
                progressBar.style.left = '0';
            } else {
                progressBar.style.left = 'var(--sidebar-width)';
            }
        }

        // 移动端侧边栏
        function toggleMobileSidebar() {
            const sidebar = document.getElementById('sidebar');
            const overlay = document.getElementById('overlay');
            
            sidebar.classList.toggle('mobile-open');
            overlay.classList.toggle('show');
        }

        function closeMobileSidebar() {
            const sidebar = document.getElementById('sidebar');
            const overlay = document.getElementById('overlay');
            
            sidebar.classList.remove('mobile-open');
            overlay.classList.remove('show');
        }

        // 回到顶部
        function scrollToTop() {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }

        // 复制代码
        function copyCode(btn, index) {
            const codeBlocks = document.querySelectorAll('.code-block-wrapper pre code');
            const code = codeBlocks[index].textContent;
            
            navigator.clipboard.writeText(code).then(() => {
                const originalText = btn.textContent;
                btn.textContent = '已复制!';
                btn.style.background = 'var(--success)';
                
                setTimeout(() => {
                    btn.textContent = originalText;
                    btn.style.background = '';
                }, 2000);
            });
        }

        // 字体大小调整
        function changeFontSize(delta) {
            currentFontSize = Math.max(12, Math.min(24, currentFontSize + delta));
            document.querySelector('.markdown-body').style.fontSize = currentFontSize + 'px';
            document.getElementById('fontSizeDisplay').textContent = currentFontSize + 'px';
            localStorage.setItem('minimind-font-size', currentFontSize);
        }

        // 主题切换
        function toggleTheme() {
            isDarkTheme = !isDarkTheme;
            document.getElementById('themeIcon').textContent = isDarkTheme ? '🌙' : '☀️';
            
            if (isDarkTheme) {
                document.documentElement.style.setProperty('--bg-primary', '#0d1117');
                document.documentElement.style.setProperty('--bg-secondary', '#161b22');
                document.documentElement.style.setProperty('--bg-tertiary', '#21262d');
                document.documentElement.style.setProperty('--text-primary', '#e6edf3');
                document.documentElement.style.setProperty('--text-secondary', '#8b949e');
            } else {
                document.documentElement.style.setProperty('--bg-primary', '#ffffff');
                document.documentElement.style.setProperty('--bg-secondary', '#f6f8fa');
                document.documentElement.style.setProperty('--bg-tertiary', '#eaeef2');
                document.documentElement.style.setProperty('--text-primary', '#1f2328');
                document.documentElement.style.setProperty('--text-secondary', '#656d76');
            }
            
            localStorage.setItem('minimind-theme', isDarkTheme ? 'dark' : 'light');
        }

        // 加载保存的设置
        function loadSettings() {
            const savedFontSize = localStorage.getItem('minimind-font-size');
            if (savedFontSize) {
                currentFontSize = parseInt(savedFontSize);
                document.querySelector('.markdown-body').style.fontSize = currentFontSize + 'px';
                document.getElementById('fontSizeDisplay').textContent = currentFontSize + 'px';
            }
            
            const savedTheme = localStorage.getItem('minimind-theme');
            if (savedTheme === 'light') {
                isDarkTheme = false;
                toggleTheme();
                isDarkTheme = false;
                document.getElementById('themeIcon').textContent = '☀️';
            }
        }

        // 键盘快捷键
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                closeMobileSidebar();
            }
        });

        // 页面加载完成后执行
        document.addEventListener('DOMContentLoaded', () => {
            loadSettings();
            renderMarkdown();
        });
    </script>
</body>
</html>'''

# 写入HTML文件
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html_template)

print(f"已生成独立HTML文件: {html_path}")
print("文件大小:", os.path.getsize(html_path) / 1024, "KB")
