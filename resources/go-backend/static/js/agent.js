        function showApiWarningModal(msg){
            const existing=document.getElementById('apiBlockModal');
            if(existing)existing.remove();
            const modal=document.createElement('div');
            modal.id='apiBlockModal';
            modal.style.cssText='position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.7);z-index:100000;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(6px);';
            const safeMsg=escapeHtml(msg||'请配置AI模型');

            modal.innerHTML=`<div style="background:var(--card-bg,#1e1e2e);border:1px solid rgba(252,129,129,0.25);border-radius:20px;padding:36px 40px;max-width:440px;text-align:center;box-shadow:0 20px 60px rgba(0,0,0,0.5);"><div style="width:60px;height:60px;margin:0 auto 20px;background:linear-gradient(135deg,#fc8181,#f687b3);border-radius:16px;display:flex;align-items:center;justify-content:center;font-size:26px;color:#fff;">⚠</div><h3 style="color:var(--text-primary,#e0e0e0);font-size:18px;margin-bottom:10px;font-weight:700;">API 未连接</h3><p style="color:var(--text-secondary,#999);font-size:13px;line-height:1.7;margin-bottom:8px;">高级功能需要 AI 模型支持，当前没有可用的模型。</p><p style="color:#fc8181;font-size:12px;margin-bottom:22px;padding:10px 14px;background:rgba(252,129,129,0.08);border-radius:8px;border:1px solid rgba(252,129,129,0.12);">${safeMsg}</p><button onclick="document.getElementById('apiBlockModal').remove()" style="padding:10px 28px;background:var(--accent,#7c6aff);color:#fff;border:none;border-radius:10px;font-size:13px;font-weight:600;cursor:pointer;">确定</button></div>`;
            document.body.appendChild(modal);
        }

        async function openAgentIDE(){
            const ok=await checkAdvancedApi();
            if(ok)window.open('/agent-ide','_blank');
        }

        let _sidebarIdeLoaded=false;
        let _sidebarIdeCurrentPath=null;

        function sidebarIdeInit(){
            if(_sidebarIdeLoaded)return;
            _sidebarIdeLoaded=true;
            sidebarIdeLoadTree();
            sidebarIdeSyncUser();
        }

        function sidebarIdeSyncUser(){
            const deviceId=localStorage.getItem('kaguya_device_id')||'';
            const userName=localStorage.getItem('kaguya_user_name')||'';
            if(userName){
                const avatar=document.getElementById('sidebarIdeAvatar');
                const nameEl=document.getElementById('sidebarIdeUserName');
                const idEl=document.getElementById('sidebarIdeUserId');
                if(avatar)avatar.textContent=userName.charAt(0).toUpperCase();
                if(nameEl)nameEl.textContent=userName;
                if(idEl)idEl.textContent='ID: '+(deviceId||'-').substring(0,10)+'...';
            }
        }

        async function sidebarIdeLoadTree(path){
            const deviceId=localStorage.getItem('kaguya_device_id')||'';
            try{
                const r=await fetch('/agent/file-tree',{
                    method:'POST',
                    headers:{'Content-Type':'application/json'},
                    body:JSON.stringify({path:path||undefined,device_id:deviceId})
                });
                const d=await r.json();
                if(d.error){console.error('IDE tree error:',d.error);return;}
                _sidebarIdeCurrentPath=d.path;
                if(d.user_name){
                    const avatar=document.getElementById('sidebarIdeAvatar');
                    const nameEl=document.getElementById('sidebarIdeUserName');
                    if(avatar)avatar.textContent=d.user_name.charAt(0).toUpperCase();
                    if(nameEl)nameEl.textContent=d.user_name;
                }
                const tree=document.getElementById('sidebarIdeFileTree');
                if(!tree)return;
                tree.innerHTML='';
                if(d.path){
                    const up=document.createElement('div');
                    up.style.cssText='padding:4px 10px;cursor:pointer;font-size:11px;color:var(--text-muted);display:flex;align-items:center;gap:6px;transition:var(--transition);border-radius:4px;margin:1px 4px;';
                    up.innerHTML='<span style="font-size:11px;">&#x1F4C1;</span> ..';
                    up.onmouseover=()=>up.style.background='var(--bg-hover)';
                    up.onmouseout=()=>up.style.background='';
                    const parentPath=d.path.split(/[\/]/).slice(0,-1).join('/');
                    up.onclick=()=>{
                        const ws=d.workspace||'';
                        if(parentPath&&parentPath.length>=ws.length)sidebarIdeLoadTree(parentPath);
                    };
                    tree.appendChild(up);
                }
                d.entries.forEach(e=>{
                    const item=document.createElement('div');
                    item.style.cssText='padding:4px 10px;cursor:pointer;font-size:11px;color:var(--text-secondary);display:flex;align-items:center;gap:6px;transition:var(--transition);border-radius:4px;margin:1px 4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;';
                    item.innerHTML='<span style="font-size:11px;">'+(e.is_dir?'&#x1F4C1;':'&#x1F4C4;')+'</span> '+escapeHtml(e.name);
                    item.onmouseover=()=>item.style.background='var(--bg-hover)';
                    item.onmouseout=()=>item.style.background='';
                    item.onclick=()=>{
                        if(e.is_dir)sidebarIdeLoadTree(e.path);
                        else sidebarIdeOpenFile(e.path,e.name);
                    };
                    tree.appendChild(item);
                });
            }catch(e){console.error('IDE tree load error:',e);}
        }

        async function sidebarIdeOpenFile(path,name){
            const ok=await checkAdvancedApi();
            if(!ok)return;
            window.open('/agent-ide','_blank');
        }

        function sidebarIdeRefresh(){
            _sidebarIdeCurrentPath=null;
            sidebarIdeLoadTree();
        }

        async function sidebarIdeNewFile(){
            const name=prompt('新文件名称:','');
            if(!name||!name.trim())return;
            const deviceId=localStorage.getItem('kaguya_device_id')||'';
            try{
                const idR=await fetch('/agent/identify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({device_id:deviceId})});
                const idD=await idR.json();
                const filePath=idD.workspace+'/'+name.trim();
                const r=await fetch('/agent/file-write',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:filePath,content:'',device_id:deviceId})});
                const d=await r.json();
                if(d.error)showToast('创建失败: '+d.error,'error');
                else{showToast('文件已创建: '+name.trim(),'success');sidebarIdeLoadTree(_sidebarIdeCurrentPath);}
            }catch(e){showToast('创建失败: '+e.message,'error');}
        }

        async function sidebarIdeNewFolder(){
            const name=prompt('新文件夹名称:','');
            if(!name||!name.trim())return;
            const deviceId=localStorage.getItem('kaguya_device_id')||'';
            try{
                const idR=await fetch('/agent/identify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({device_id:deviceId})});
                const idD=await idR.json();
                const dirPath=idD.workspace+'/'+name.trim();
                const r=await fetch('/agent/file-write',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:dirPath,content:'',is_dir:true,device_id:deviceId})});
                const d=await r.json();
                if(d.error)showToast('创建失败: '+d.error,'error');
                else{showToast('文件夹已创建: '+name.trim(),'success');sidebarIdeLoadTree(_sidebarIdeCurrentPath);}
            }catch(e){showToast('创建失败: '+e.message,'error');}
        }

        async function sidebarIdeCompile(){
            const ok=await checkAdvancedApi();
            if(!ok)return;
            window.open('/agent-ide','_blank');
        }

        async function toggleAgentMode() {
            if(!agentModeEnabled){
                const ok=await checkAdvancedApi();
                if(!ok)return;
            }
            agentModeEnabled = !agentModeEnabled;
            const btn = document.getElementById('agentModeBtn');
            const banner = document.getElementById('agentBanner');
            if (agentModeEnabled) {
                btn.classList.add('active');
                banner.classList.add('show');
                showToast('Agent mode enabled - AI will autonomously use tools', 'success');
            } else {
                btn.classList.remove('active');
                banner.classList.remove('show');
                showToast('Agent mode disabled', 'info');
            }
        }

        const AGENT_TOOL_ICONS = {
            'read_file': '[R]', 'write_file': '[W]', 'edit_file': '[E]',
            'list_directory': '[D]', 'search_files': '[S]', 'execute_command': '[!]', 'glob': '[G]',
            'compile': '[C]', 'todo_write': '[T]', 'enter_plan_mode': '[P]', 'exit_plan_mode': '[P]',
            'web_fetch': '[F]', 'web_search': '[Q]', 'agent_spawn': '[A]',
            'task_create': '[+]', 'task_update': '[^]', 'task_list': '[L]', 'brief': '[B]'
        };
        const AGENT_DANGEROUS_TOOLS = ['write_file', 'edit_file', 'execute_command', 'compile', 'agent_spawn'];

        function createAgentMessageEl(time) {
            const container = document.getElementById('messagesContainer');
            const msgEl = document.createElement('div');
            msgEl.className = 'message assistant';
            const contentId = 'agentStream_' + Date.now();
            msgEl.innerHTML = '<div class="message-avatar" style="font-size:14px;font-weight:700;background:var(--grad-warm);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">Agent</div><div class="message-content-wrapper"><div class="agent-progress-bar" id="' + contentId + '_progress"></div><div class="message-content" id="' + contentId + '"></div><div class="message-time">' + time + '</div></div>';
            container.appendChild(msgEl);
            container.scrollTop = container.scrollHeight;
            return contentId;
        }

        function updateAgentProgress(progressId, iteration, maxIter, status) {
            const bar = document.getElementById(progressId);
            if (!bar) return;
            const pct = Math.min(100, Math.round((iteration / maxIter) * 100));
            bar.innerHTML = '<div class="agent-progress-fill" style="width:' + pct + '%"></div><span class="agent-progress-text">Iter ' + iteration + '/' + maxIter + ' - ' + escapeHtml(status) + '</span>';
            bar.style.display = 'flex';
        }

        async function sendAgentMessage(message) {
            try {
                const extApi=getActiveApiConfig();
                const sr = await fetch('/agent/api-status',{
                    method:'POST',
                    headers:{'Content-Type':'application/json'},
                    body:JSON.stringify({external_api:extApi})
                });
                const sd = await sr.json();
                if (!sd.available) {
                    showToast('API not connected: ' + (sd.message || 'Please configure a model first'), 'error');
                    isGenerating = false;
                    document.getElementById('sendBtn').disabled = false;
                    document.getElementById('sendBtn').style.display = 'flex';
                    document.getElementById('stopBtn').style.display = 'none';
                    document.getElementById('statusText').textContent = '就绪';
                    return;
                }
            } catch(e) {}
            if (!currentChatId) newChat();
            const chat = chats.find(c => c.id === currentChatId);
            const time = new Date().toLocaleTimeString('zh-CN', {hour:'2-digit',minute:'2-digit'});
            addMessageToUI('user', message, time);
            chat.messages.push({role: 'user', content: message, time: time});
            const contentId = createAgentMessageEl(time);
            const contentEl = document.getElementById(contentId);
            const progressId = contentId + '_progress';
            const container = document.getElementById('messagesContainer');
            let fullContent = '';
            let iterationCount = 0;
            let thinkingEl = null;
            let thinkingText = '';
            try {
                const extApiRun=getActiveApiConfig();
                const response = await fetch('/agent/run', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({message: message, history: agentHistory.slice(-10), working_dir: document.querySelector('.main-input')?.getAttribute('data-cwd') || undefined, external_api: extApiRun, device_id: generateDeviceId()})
                });
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';
                while (true) {
                    const {done, value} = await reader.read();
                    if (done) break;
                    buffer += decoder.decode(value, {stream: true});
                    const lines = buffer.split('\n');
                    buffer = lines.pop() || '';
                    for (const line of lines) {
                        if (!line.startsWith('data: ')) continue;
                        try {
                            const data = JSON.parse(line.slice(6));
                            if (data.type === 'thinking') {
                                iterationCount = data.iteration;
                                if (!thinkingEl) {
                                    thinkingEl = document.createElement('div');
                                    thinkingEl.className = 'agent-thinking-block';
                                    thinkingEl.innerHTML = '<div class="agent-thinking-header" onclick="this.parentElement.classList.toggle(&quot;collapsed&quot;)"><span class="thinking-toggle">&#9660;</span> Thinking...</div><div class="agent-thinking-content"></div>';
                                    contentEl.appendChild(thinkingEl);
                                }
                                thinkingText += data.content;
                                const thinkContent = thinkingEl.querySelector('.agent-thinking-content');
                                if (thinkContent) thinkContent.textContent = thinkingText;
                                updateAgentProgress(progressId, data.iteration, 25, 'Thinking...');
                                container.scrollTop = container.scrollHeight;
                            } else if (data.type === 'tool_use') {
                                iterationCount = data.iteration;
                                if (thinkingEl) { thinkingEl = null; thinkingText = ''; }
                                const icon = AGENT_TOOL_ICONS[data.tool] || '[?]';
                                const isDangerous = data.dangerous || AGENT_DANGEROUS_TOOLS.includes(data.tool);
                                const inputStr = typeof data.input === 'object' ? JSON.stringify(data.input, null, 2) : String(data.input);
                                const dangerClass = isDangerous ? ' agent-tool-danger' : '';
                                const permBadge = data.permission === 'deny' ? '<span class="danger-badge" style="background:#ef4444;">X</span>' : (data.permission === 'prompt' ? '<span class="danger-badge">!</span>' : '');
                                contentEl.innerHTML += '<div class="agent-iteration">Iter #' + data.iteration + '</div><div class="agent-tool-call' + dangerClass + '"><div class="tool-header"><span class="tool-icon">' + icon + '</span> ' + escapeHtml(data.tool) + permBadge + '</div><div class="tool-input"><pre>' + escapeHtml(inputStr.substring(0, 800)) + '</pre></div></div>';
                                updateAgentProgress(progressId, data.iteration, 25, 'Running ' + data.tool);
                                container.scrollTop = container.scrollHeight;
                            } else if (data.type === 'tool_result') {
                                const outputStr = String(data.output || '');
                                const isErr = outputStr.startsWith('Error') || outputStr.includes('not found') || outputStr.includes('Permission denied');
                                const resultClass = isErr ? ' agent-result-error' : '';
                                contentEl.innerHTML += '<div class="agent-tool-result' + resultClass + '"><div class="result-header"><span>' + (isErr ? '[FAIL]' : '[OK]') + '</span> ' + escapeHtml(data.tool) + '</div><div class="result-output"><pre>' + escapeHtml(outputStr.substring(0, 1500)) + '</pre></div></div>';
                                updateAgentProgress(progressId, data.iteration, 25, 'Result from ' + data.tool);
                                container.scrollTop = container.scrollHeight;
                            } else if (data.type === 'assistant') {
                                fullContent = data.content || '';
                                if (thinkingEl) { thinkingEl = null; thinkingText = ''; }
                                const rendered = typeof marked !== 'undefined' ? marked.parse(fullContent) : escapeHtml(fullContent);
                                contentEl.innerHTML += '<div class="agent-final-answer">' + rendered + '</div>';
                                updateAgentProgress(progressId, data.iteration, 25, 'Done');
                                container.scrollTop = container.scrollHeight;
                            } else if (data.type === 'error') {
                                contentEl.innerHTML += '<div class="agent-error-block">Error: ' + escapeHtml(data.content) + '</div>';
                            }
                            if (data.done) {
                                agentHistory.push({user: message, assistant: fullContent});
                                const bar = document.getElementById(progressId);
                                if (bar) bar.style.display = 'none';
                            }
                        } catch(e) {}
                    }
                }
            } catch(e) {
                contentEl.innerHTML += '<div class="agent-error-block">Connection error: ' + escapeHtml(e.message) + '</div>';
            }
            chat.messages.push({role: 'assistant', content: fullContent || '(agent completed)', time: time});
            saveChats();
            isGenerating = false;
            document.getElementById('sendBtn').disabled = false;
            document.getElementById('sendBtn').style.display = 'flex';
            document.getElementById('stopBtn').style.display = 'none';
            document.getElementById('statusText').textContent = '就绪';
        }

        // ========== MULTIMODAL ENHANCEMENT ==========
        let multimodalChatMessages = [];
        let multimodalAnalysisHistory = [];
        let currentMultimodalImageUrl = '';

        function sendMultimodalChat() {
            const input = document.getElementById('multimodalChatInput');
            const msg = input.value.trim();
            if (!msg) return;
            input.value = '';
            multimodalChatMessages.push({ role: 'user', content: msg });
            renderMultimodalChat();
            fetch('/multimodal/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: msg, image_url: currentMultimodalImageUrl || '' })
            }).then(r => r.json()).then(data => {
                multimodalChatMessages.push({ role: 'assistant', content: data.response || data.content || '无法分析' });
                renderMultimodalChat();
            }).catch(() => {
                multimodalChatMessages.push({ role: 'assistant', content: '连接失败，请稍后重试' });
                renderMultimodalChat();
            });
        }

        function renderMultimodalChat() {
            const el = document.getElementById('multimodalChatHistory');
            if (!el) return;
            el.innerHTML = multimodalChatMessages.map(m => {
                const isUser = m.role === 'user';
                return '<div style="padding:4px 8px;border-radius:8px;font-size:11px;' +
                    (isUser ? 'background:linear-gradient(135deg,var(--primary),var(--secondary));color:white;margin-left:20px;' : 'background:var(--bg-secondary);color:var(--text-secondary);margin-right:20px;') +
                    '">' + escapeHtml(m.content) + '</div>';
            }).join('');
            el.scrollTop = el.scrollHeight;
        }

        function loadMultimodalHistory() {
            const el = document.getElementById('multimodalHistoryList');
            if (!el) return;
            fetch('/multimodal/history').then(r => r.json()).then(data => {
                multimodalAnalysisHistory = data.history || [];
                renderMultimodalHistoryList();
            }).catch(() => {
                el.innerHTML = '<div style="text-align:center;color:var(--text-muted);font-size:12px;padding:12px;">加载失败</div>';
            });
        }

        function renderMultimodalHistoryList() {
            const el = document.getElementById('multimodalHistoryList');
            if (!el) return;
            if (multimodalAnalysisHistory.length === 0) {
                el.innerHTML = '<div style="text-align:center;color:var(--text-muted);font-size:12px;padding:12px;">暂无分析历史</div>';
                return;
            }
            el.innerHTML = multimodalAnalysisHistory.slice(-15).reverse().map(h => {
                return '<div style="display:flex;align-items:center;gap:6px;padding:6px;border-radius:8px;border:1px solid var(--border);font-size:11px;">' +
                    '<span style="color:var(--text-muted);">' + (h.type === 'describe' ? '📝' : h.type === 'ocr' ? '🔤' : '🔬') + '</span>' +
                    '<span style="flex:1;color:var(--text-secondary);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' + escapeHtml(h.result || h.summary || '').substring(0, 60) + '</span>' +
                    '<span style="color:var(--text-muted);font-size:9px;">' + escapeHtml(h.timestamp || '') + '</span>' +
                '</div>';
            }).join('');
        }

        // ========== INIT ENHANCED MODULES ==========
        function initBackendModules() {
            try { renderOpsChannelComparison(); } catch(e) {}
            try { renderOpsCalendar(); } catch(e) {}
            try { renderReleaseTimeline(); } catch(e) {}
            try { renderRollbackVersions(); } catch(e) {}
            try { renderAlertHistory(); } catch(e) {}
            try { renderNotificationChannels(); } catch(e) {}
            try { renderTrafficAllocator(); } catch(e) {}
            try { renderIntegrationMarket(); } catch(e) {}
            try { renderWebhooks(); } catch(e) {}
            try { updateConnectionTestTargets(); } catch(e) {}
        }

        setTimeout(initBackendModules, 1000);

        let starfieldEnabled = false;
        let starfieldAnimId = null;
        let stars = [];
        let shootingStars = [];

        function initStarfield() {
            const canvas = document.getElementById('starfieldCanvas');
            if (!canvas) return;
            const ctx = canvas.getContext('2d');
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;

            stars = [];
            const starCount = Math.floor((canvas.width * canvas.height) / 1500);
            for (let i = 0; i < starCount; i++) {
                stars.push({
                    x: Math.random() * canvas.width,
                    y: Math.random() * canvas.height,
                    radius: Math.random() * 2.2 + 0.3,
                    alpha: Math.random() * 0.9 + 0.3,
                    twinkleSpeed: Math.random() * 0.025 + 0.008,
                    twinkleOffset: Math.random() * Math.PI * 2,
                    color: getStarColor()
                });
            }

            function getStarColor() {
                const colors = [
                    'rgba(255,255,255,',
                    'rgba(200,220,255,',
                    'rgba(180,200,255,',
                    'rgba(255,230,200,',
                    'rgba(200,180,255,',
                    'rgba(125,211,252,',
                    'rgba(192,132,252,',
                    'rgba(240,171,252,',
                    'rgba(94,234,212,'
                ];
                return colors[Math.floor(Math.random() * colors.length)];
            }

            function spawnShootingStar() {
                if (!starfieldEnabled) return;
                if (shootingStars.length < 5 && Math.random() < 0.015) {
                    const startX = Math.random() * canvas.width * 0.8;
                    const startY = Math.random() * canvas.height * 0.4;
                    const angle = Math.PI / 4 + (Math.random() - 0.5) * 0.3;
                    shootingStars.push({
                        x: startX, y: startY,
                        vx: Math.cos(angle) * (6 + Math.random() * 4),
                        vy: Math.sin(angle) * (6 + Math.random() * 4),
                        life: 1.0,
                        decay: 0.012 + Math.random() * 0.008,
                        length: 60 + Math.random() * 80,
                        width: 1 + Math.random() * 1.5
                    });
                }
            }

            function drawStarfield() {
                if (!starfieldEnabled) return;
                ctx.clearRect(0, 0, canvas.width, canvas.height);

                const time = Date.now() * 0.001;

                for (const star of stars) {
                    const twinkle = Math.sin(time * star.twinkleSpeed * 60 + star.twinkleOffset);
                    const alpha = star.alpha * (0.6 + 0.4 * twinkle);
                    const radius = star.radius * (0.8 + 0.2 * twinkle);

                    ctx.beginPath();
                    ctx.arc(star.x, star.y, radius, 0, Math.PI * 2);
                    ctx.fillStyle = star.color + alpha.toFixed(3) + ')';
                    ctx.fill();

                    if (star.radius > 1.2) {
                        ctx.beginPath();
                        ctx.arc(star.x, star.y, radius * 3, 0, Math.PI * 2);
                        const grad = ctx.createRadialGradient(star.x, star.y, 0, star.x, star.y, radius * 3);
                        grad.addColorStop(0, star.color + (alpha * 0.3).toFixed(3) + ')');
                        grad.addColorStop(1, star.color + '0)');
                        ctx.fillStyle = grad;
                        ctx.fill();
                    }
                }

                spawnShootingStar();

                for (let i = shootingStars.length - 1; i >= 0; i--) {
                    const ss = shootingStars[i];
                    ss.x += ss.vx;
                    ss.y += ss.vy;
                    ss.life -= ss.decay;

                    if (ss.life <= 0) {
                        shootingStars.splice(i, 1);
                        continue;
                    }

                    const tailX = ss.x - (ss.vx / Math.sqrt(ss.vx * ss.vx + ss.vy * ss.vy)) * ss.length * ss.life;
                    const tailY = ss.y - (ss.vy / Math.sqrt(ss.vx * ss.vx + ss.vy * ss.vy)) * ss.length * ss.life;

                    const grad = ctx.createLinearGradient(tailX, tailY, ss.x, ss.y);
                    grad.addColorStop(0, 'rgba(255,255,255,0)');
                    grad.addColorStop(0.6, 'rgba(125,211,252,' + (ss.life * 0.5).toFixed(3) + ')');
                    grad.addColorStop(1, 'rgba(255,255,255,' + ss.life.toFixed(3) + ')');

                    ctx.beginPath();
                    ctx.moveTo(tailX, tailY);
                    ctx.lineTo(ss.x, ss.y);
                    ctx.strokeStyle = grad;
                    ctx.lineWidth = ss.width * ss.life;
                    ctx.lineCap = 'round';
                    ctx.stroke();

                    ctx.beginPath();
                    ctx.arc(ss.x, ss.y, 2 * ss.life, 0, Math.PI * 2);
                    ctx.fillStyle = 'rgba(255,255,255,' + (ss.life * 0.8).toFixed(3) + ')';
                    ctx.fill();
                }

                starfieldAnimId = requestAnimationFrame(drawStarfield);
            }

            drawStarfield();

            window.addEventListener('resize', () => {
                canvas.width = window.innerWidth;
                canvas.height = window.innerHeight;
                stars = [];
                const newCount = Math.floor((canvas.width * canvas.height) / 1500);
                for (let i = 0; i < newCount; i++) {
                    stars.push({
                        x: Math.random() * canvas.width,
                        y: Math.random() * canvas.height,
                        radius: Math.random() * 2.2 + 0.3,
                        alpha: Math.random() * 0.9 + 0.3,
                        twinkleSpeed: Math.random() * 0.025 + 0.008,
                        twinkleOffset: Math.random() * Math.PI * 2,
                        color: getStarColor()
                    });
                }
            });
        }

        function enableStarfieldMode() {
            starfieldEnabled = true;
            if (wallpaperEnabled) disableWallpaperMode();
            document.body.classList.add('starfield-mode');
            if (!document.body.classList.contains('dark')) {
                document.body.classList.add('dark');
                settings.dark = true;
                const dm = $('darkModeToggle');
                if (dm) dm.checked = true;
            }
            const canvas = document.getElementById('starfieldCanvas');
            if (canvas) canvas.style.display = 'block';
            const n1 = document.getElementById('nebula1');
            const n2 = document.getElementById('nebula2');
            const n3 = document.getElementById('nebula3');
            if (n1) n1.style.display = 'block';
            if (n2) n2.style.display = 'block';
            if (n3) n3.style.display = 'block';
            if (!starfieldAnimId) initStarfield();
            const btn = document.getElementById('starfieldBtn');
            if (btn) btn.classList.add('active');
            localStorage.setItem('kaguya_starfield', 'true');
            showToast('🌌 星空模式已开启');
        }

        function disableStarfieldMode() {
            starfieldEnabled = false;
            document.body.classList.remove('starfield-mode');
            if (starfieldAnimId) {
                cancelAnimationFrame(starfieldAnimId);
                starfieldAnimId = null;
            }
            const canvas = document.getElementById('starfieldCanvas');
            if (canvas) {
                const ctx = canvas.getContext('2d');
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                canvas.style.display = 'none';
            }
            const n1 = document.getElementById('nebula1');
            const n2 = document.getElementById('nebula2');
            const n3 = document.getElementById('nebula3');
            if (n1) n1.style.display = 'none';
            if (n2) n2.style.display = 'none';
            if (n3) n3.style.display = 'none';
            const btn = document.getElementById('starfieldBtn');
            if (btn) btn.classList.remove('active');
            localStorage.setItem('kaguya_starfield', 'false');
        }

        function toggleStarfieldMode() {
            if (starfieldEnabled) {
                disableStarfieldMode();
                showToast('星空模式已关闭');
            } else {
                enableStarfieldMode();
            }
        }

        let wallpaperEnabled = false;

        function enableWallpaperMode() {
            wallpaperEnabled = true;
            if (starfieldEnabled) disableStarfieldMode();
            document.body.classList.add('wallpaper-mode');
            if (!document.body.classList.contains('dark')) {
                document.body.classList.add('dark');
                settings.dark = true;
                const dm = $('darkModeToggle');
                if (dm) dm.checked = true;
            }
            const btn = document.getElementById('wallpaperBtn');
            if (btn) btn.classList.add('active');
            localStorage.setItem('kaguya_wallpaper', 'true');
            showToast('🖼️ 壁纸模式已开启');
        }

        function disableWallpaperMode() {
            wallpaperEnabled = false;
            document.body.classList.remove('wallpaper-mode');
            const btn = document.getElementById('wallpaperBtn');
            if (btn) btn.classList.remove('active');
            localStorage.setItem('kaguya_wallpaper', 'false');
        }

        function toggleWallpaperMode() {
            if (wallpaperEnabled) {
                disableWallpaperMode();
                showToast('壁纸模式已关闭');
            } else {
                enableWallpaperMode();
            }
        }

        if (localStorage.getItem('kaguya_wallpaper') === 'true') {
            setTimeout(enableWallpaperMode, 300);
        }
        if (localStorage.getItem('kaguya_starfield') === 'true') {
            setTimeout(enableStarfieldMode, 300);
        }
