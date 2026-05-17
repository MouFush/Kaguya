// ==================== MCP 插件管理 ====================
        let mcpPlugins = [];
        let enabledMcpTools = [];
        
        // ==================== 工作流编排系统 ====================
        let workflows = [];
        let workflowNodeTypes = {};
        let currentWorkflow = null;
        let selectedNode = null;
        let workflowNodes = [];
        let workflowConnections = [];
        let workflowZoom = 1;
        let isDraggingNode = false;
        let dragOffset = { x: 0, y: 0 };
        let isConnecting = false;
        let connectionStart = null;
        
        function loadWorkflows() {
            fetch('/workflows').then(r => r.json()).then(data => {
                if (data.success) {
                    workflows = data.workflows;
                    renderWorkflowList();
                    renderFeatureCenterMeta();
                }
            });
        }
        
        function renderWorkflowList() {
            const container = document.getElementById('workflowList');
            if (!workflows.length) {
                container.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:20px;">暂无工作流，点击"新建"创建</div>';
                return;
            }
            
            container.innerHTML = workflows.map(wf => `
                <div class="workflow-item" data-id="${wf.id}">
                    <div class="workflow-icon" style="background:linear-gradient(135deg,${wf.color},${wf.color}dd);">${wf.icon}</div>
                    <div class="workflow-info">
                        <div class="workflow-name">${escapeHtml(wf.name)}</div>
                        <div class="workflow-desc">${wf.description || '无描述'}</div>
                        <div class="workflow-meta">
                            <span>📦 ${wf.node_count}个节点</span>
                            <span>🕐 ${new Date(wf.updated_at * 1000).toLocaleDateString()}</span>
                        </div>
                    </div>
                    <div class="workflow-actions">
                        <button class="workflow-btn run" onclick="runWorkflow('${wf.id}')">▶</button>
                        <button class="workflow-btn edit" onclick="editWorkflow('${wf.id}')">✏️</button>
                        <button class="workflow-btn delete" onclick="deleteWorkflow('${wf.id}')">🗑️</button>
                    </div>
                </div>
            `).join('');
        }
        
        function openWorkflowEditor() {
            currentWorkflow = null;
            workflowNodes = [];
            workflowConnections = [];
            selectedNode = null;
            document.getElementById('workflowName').value = '';
            document.getElementById('workflowNodesContainer').innerHTML = '';
            var svgEl = document.getElementById('workflowConnections');
            var defs = svgEl.querySelector('defs');
            svgEl.innerHTML = '';
            if (defs) svgEl.appendChild(defs);
            document.getElementById('workflowPropertiesContent').innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:40px 20px;"><div style="font-size:32px;margin-bottom:8px;">👈</div><div style="font-size:13px;">选择节点以编辑属性</div><div style="font-size:11px;margin-top:6px;opacity:0.7;">拖拽左侧节点到画布开始</div></div>';
            document.getElementById('workflowLogContent').innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:40px 20px;"><div style="font-size:32px;margin-bottom:8px;">📋</div><div style="font-size:13px;">运行工作流后查看执行日志</div></div>';
            switchPropertiesTab('props');
            
            loadWorkflowNodeTypes();
            document.getElementById('workflowEditorModal').classList.add('show');
            
            setupCanvasPan();
            setupWorkflowKeyboard();
        }
        
        let canvasPanOffset = { x: 0, y: 0 };
        let isPanning = false;
        let panStart = { x: 0, y: 0 };
        
        function setupCanvasPan() {
            var canvas = document.getElementById('workflowCanvas');
            if (!canvas) return;
            
            canvas.onmousedown = function(e) {
                if (e.target === canvas || e.target.classList.contains('workflow-canvas-grid')) {
                    if (e.button === 0) {
                        isPanning = true;
                        panStart.x = e.clientX - canvasPanOffset.x;
                        panStart.y = e.clientY - canvasPanOffset.y;
                        canvas.style.cursor = 'grabbing';
                    }
                }
            };
            
            canvas.onmousemove = function(e) {
                if (!isPanning) return;
                canvasPanOffset.x = e.clientX - panStart.x;
                canvasPanOffset.y = e.clientY - panStart.y;
                var container = document.getElementById('workflowNodesContainer');
                var svg = document.getElementById('workflowConnections');
                container.style.transform = 'translate(' + canvasPanOffset.x + 'px,' + canvasPanOffset.y + 'px) scale(' + workflowZoom + ')';
                svg.style.transform = 'translate(' + canvasPanOffset.x + 'px,' + canvasPanOffset.y + 'px) scale(' + workflowZoom + ')';
            };
            
            canvas.onmouseup = function(e) {
                if (isPanning) {
                    isPanning = false;
                    canvas.style.cursor = 'grab';
                }
            };
            
            canvas.onmouseleave = function() {
                if (isPanning) {
                    isPanning = false;
                    canvas.style.cursor = 'grab';
                }
            };
            
            canvas.onwheel = function(e) {
                e.preventDefault();
                var delta = e.deltaY > 0 ? -0.05 : 0.05;
                zoomWorkflow(delta);
            };
        }
        
        function setupWorkflowKeyboard() {
            var handler = function(e) {
                var modal = document.getElementById('workflowEditorModal');
                if (!modal || !modal.classList.contains('show')) return;
                
                if (e.key === 'Delete' || e.key === 'Backspace') {
                    if (selectedNode && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA') {
                        e.preventDefault();
                        deleteWorkflowNode(selectedNode);
                    }
                }
                if (e.ctrlKey && e.key === 'z') {
                    e.preventDefault();
                    undoWorkflowAction();
                }
                if (e.ctrlKey && e.key === 'y') {
                    e.preventDefault();
                    redoWorkflowAction();
                }
                if (e.ctrlKey && e.key === 'd') {
                    e.preventDefault();
                    if (selectedNode) duplicateWorkflowNode(selectedNode);
                }
                if (e.key === 'Escape') {
                    selectedNode = null;
                    renderWorkflowCanvas();
                }
            };
            
            document.removeEventListener('keydown', handler);
            document.addEventListener('keydown', handler);
        }

        function createQuickWorkflow(type) {
            openWorkflowEditor();
            const templates = {
                chat: { name: 'AI 对话流程', nodes: [
                    { type: 'start', x: 100, y: 200, config: {} },
                    { type: 'llm', x: 350, y: 200, config: { prompt: '你是一个有帮助的AI助手。', temperature: 0.7 } },
                    { type: 'end', x: 600, y: 200, config: {} }
                ]},
                rag: { name: 'RAG 检索增强', nodes: [
                    { type: 'start', x: 100, y: 200, config: {} },
                    { type: 'mcp', x: 300, y: 150, config: { tool_name: 'knowledge_base', action: 'search' } },
                    { type: 'llm', x: 500, y: 200, config: { prompt: '基于以下检索结果回答问题：\n{context}\n\n问题：{input}', temperature: 0.3 } },
                    { type: 'end', x: 700, y: 200, config: {} }
                ]},
                agent: { name: 'Agent 工具链', nodes: [
                    { type: 'start', x: 100, y: 250, config: {} },
                    { type: 'llm', x: 300, y: 250, config: { prompt: '你是一个智能助手，可以使用工具完成任务。', temperature: 0.5 } },
                    { type: 'condition', x: 520, y: 250, config: { condition_type: 'tool_call', true_label: '需要工具', false_label: '直接回答' } },
                    { type: 'mcp', x: 720, y: 150, config: { tool_name: 'auto', action: 'execute' } },
                    { type: 'end', x: 720, y: 350, config: {} }
                ]},
                pipeline: { name: '数据处理管线', nodes: [
                    { type: 'start', x: 80, y: 200, config: {} },
                    { type: 'http', x: 260, y: 200, config: { method: 'GET', url: '' } },
                    { type: 'transform', x: 440, y: 200, config: { transform_type: 'json_extract', expression: '' } },
                    { type: 'condition', x: 620, y: 200, config: { condition_type: 'value_check' } },
                    { type: 'llm', x: 800, y: 130, config: { prompt: '分析以下数据：\n{input}', temperature: 0.3 } },
                    { type: 'end', x: 800, y: 280, config: {} }
                ]},
                webhook_handler: { name: 'Webhook 处理器', nodes: [
                    { type: 'webhook', x: 80, y: 200, config: { method: 'POST', path: '/webhook/incoming' } },
                    { type: 'transform', x: 280, y: 200, config: { transform_type: 'json_parse', template: '' } },
                    { type: 'llm', x: 480, y: 200, config: { prompt: '处理以下Webhook数据并生成响应：\n{input}', temperature: 0.3 } },
                    { type: 'notification', x: 680, y: 200, config: { channel: 'webhook', webhook_url: '' } },
                    { type: 'end', x: 880, y: 200, config: {} }
                ]},
                scheduled_report: { name: '定时报告生成', nodes: [
                    { type: 'schedule', x: 80, y: 200, config: { cron: '0 9 * * *', timezone: 'Asia/Shanghai' } },
                    { type: 'http', x: 280, y: 200, config: { method: 'GET', url: '' } },
                    { type: 'llm', x: 480, y: 200, config: { prompt: '基于以下数据生成每日报告：\n{input}', temperature: 0.3 } },
                    { type: 'notification', x: 680, y: 200, config: { channel: 'email', email_to: '' } },
                    { type: 'end', x: 880, y: 200, config: {} }
                ]},
                batch_process: { name: '批量数据处理', nodes: [
                    { type: 'start', x: 80, y: 200, config: {} },
                    { type: 'split', x: 260, y: 200, config: { batch_size: 1 } },
                    { type: 'llm', x: 460, y: 200, config: { prompt: '处理以下数据项：\n{input}', temperature: 0.2 } },
                    { type: 'merge', x: 660, y: 200, config: { mode: 'append', wait_for_all: true } },
                    { type: 'end', x: 860, y: 200, config: {} }
                ]},
                content_pipeline: { name: '内容生产流水线', nodes: [
                    { type: 'start', x: 80, y: 200, config: {} },
                    { type: 'llm', x: 260, y: 200, config: { prompt: '根据以下主题生成内容草稿：\n{input}', temperature: 0.7 } },
                    { type: 'condition', x: 460, y: 200, config: { condition_type: 'quality_check', true_label: '通过', false_label: '需修改' } },
                    { type: 'llm', x: 660, y: 100, config: { prompt: '审核并优化以下内容：\n{input}', temperature: 0.3 } },
                    { type: 'notification', x: 660, y: 300, config: { channel: 'webhook', webhook_url: '' } },
                    { type: 'end', x: 860, y: 200, config: {} }
                ]}
            };
            const tpl = templates[type];
            if (!tpl) return;
            document.getElementById('workflowName').value = tpl.name;
            let nodeIdCounter = 1;
            workflowNodes = tpl.nodes.map((n, i) => ({
                id: 'node_' + nodeIdCounter++,
                type: n.type,
                x: n.x,
                y: n.y,
                config: n.config || {}
            }));
            workflowConnections = [];
            for (let i = 0; i < workflowNodes.length - 1; i++) {
                const curr = workflowNodes[i];
                const nextNodes = [];
                if (curr.type === 'condition') {
                    if (workflowNodes[i + 1]) nextNodes.push(workflowNodes[i + 1]);
                    if (workflowNodes[i + 2]) nextNodes.push(workflowNodes[i + 2]);
                } else {
                    if (workflowNodes[i + 1]) nextNodes.push(workflowNodes[i + 1]);
                }
                for (const next of nextNodes) {
                    workflowConnections.push({ source: curr.id, target: next.id });
                }
            }
            renderWorkflowCanvas();
            renderWorkflowConnections();
        }

        function showWorkflowHelp() {
            const modal = document.getElementById('workflowHelpModal');
            if (modal) modal.style.display = '';
        }
        
        function loadWorkflowNodeTypes() {
            fetch('/workflow/node-types').then(r => r.json()).then(data => {
                if (data.success) {
                    workflowNodeTypes = data.node_types;
                    renderWorkflowNodePalette();
                }
            });
        }
        
        function renderWorkflowNodePalette() {
            const controlContainer = document.getElementById('workflowNodesControl');
            const aiContainer = document.getElementById('workflowNodesAI');
            const toolContainer = document.getElementById('workflowNodesTool');
            
            controlContainer.innerHTML = '';
            aiContainer.innerHTML = '';
            toolContainer.innerHTML = '';
            
            Object.values(workflowNodeTypes).forEach(nodeType => {
                const nodeEl = document.createElement('div');
                nodeEl.className = 'workflow-node-item';
                nodeEl.draggable = true;
                nodeEl.innerHTML = `
                    <span class="workflow-node-icon" style="color:${nodeType.color};font-size:14px;">${nodeType.icon}</span>
                    <div style="flex:1;min-width:0;">
                        <div style="font-size:11px;font-weight:600;color:var(--text-primary);">${nodeType.name}</div>
                        ${nodeType.description ? `<div style="font-size:9px;color:var(--text-muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${nodeType.description}</div>` : ''}
                    </div>
                `;
                nodeEl.ondragstart = (e) => {
                    e.dataTransfer.setData('nodeType', nodeType.id);
                    e.dataTransfer.effectAllowed = 'copy';
                };
                
                if (nodeType.category === 'control') {
                    controlContainer.appendChild(nodeEl);
                } else if (nodeType.category === 'ai') {
                    aiContainer.appendChild(nodeEl);
                } else {
                    toolContainer.appendChild(nodeEl);
                }
            });
        }
        
        function editWorkflow(workflowId) {
            fetch(`/workflow/${workflowId}`).then(r => r.json()).then(data => {
                if (data.success) {
                    currentWorkflow = data.workflow;
                    workflowNodes = data.workflow.nodes || [];
                    workflowConnections = data.workflow.connections || [];
                    document.getElementById('workflowName').value = data.workflow.name;
                    renderWorkflowCanvas();
                    loadWorkflowNodeTypes();
                    document.getElementById('workflowEditorModal').classList.add('show');
                }
            });
        }
        
        function renderWorkflowCanvas() {
            const container = document.getElementById('workflowNodesContainer');
            container.innerHTML = '';
            
            workflowNodes.forEach(node => {
                const nodeType = workflowNodeTypes[node.type];
                if (!nodeType) return;
                
                const nodeEl = document.createElement('div');
                nodeEl.className = 'workflow-canvas-node' + (selectedNode === node.id ? ' selected' : '');
                nodeEl.style.left = node.x + 'px';
                nodeEl.style.top = node.y + 'px';
                nodeEl.style.borderColor = nodeType.color;
                nodeEl.dataset.nodeId = node.id;
                nodeEl.innerHTML = `
                    <div class="node-header" style="background:linear-gradient(135deg,${nodeType.color}18,${nodeType.color}08);">
                        <span class="node-icon">${nodeType.icon}</span>
                        <span class="node-title">${nodeType.name}</span>
                        <span class="node-status" data-node-id="${node.id}"></span>
                    </div>
                    <div class="node-body">${node.config?.label || nodeType.description || ''}</div>
                    <div class="node-ports">
                        ${nodeType.inputs.length ? '<div class="workflow-port input" data-port="input" title="Input"></div>' : '<div></div>'}
                        ${nodeType.outputs.length ? '<div class="workflow-port output" data-port="output" title="Output"></div>' : '<div></div>'}
                    </div>
                `;
                
                nodeEl.onclick = (e) => {
                    e.stopPropagation();
                    selectWorkflowNode(node.id);
                };
                
                nodeEl.onmousedown = (e) => {
                    if (e.target.classList.contains('workflow-port')) {
                        e.stopPropagation();
                        startConnectionDrag(e, node);
                        return;
                    }
                    e.stopPropagation();
                    isDraggingNode = true;
                    const canvasRect = document.getElementById('workflowNodesContainer').getBoundingClientRect();
                    dragOffset.x = e.clientX - (node.x * workflowZoom + canvasPanOffset.x);
                    dragOffset.y = e.clientY - (node.y * workflowZoom + canvasPanOffset.y);
                    
                    const onMouseMove = (e) => {
                        if (!isDraggingNode) return;
                        node.x = Math.round((e.clientX - dragOffset.x - canvasPanOffset.x) / workflowZoom / 10) * 10;
                        node.y = Math.round((e.clientY - dragOffset.y - canvasPanOffset.y) / workflowZoom / 10) * 10;
                        nodeEl.style.left = node.x + 'px';
                        nodeEl.style.top = node.y + 'px';
                        renderWorkflowConnections();
                        updateMinimap();
                    };
                    
                    const onMouseUp = () => {
                        isDraggingNode = false;
                        saveWorkflowState();
                        document.removeEventListener('mousemove', onMouseMove);
                        document.removeEventListener('mouseup', onMouseUp);
                    };
                    
                    document.addEventListener('mousemove', onMouseMove);
                    document.addEventListener('mouseup', onMouseUp);
                };
                
                container.appendChild(nodeEl);
            });
            
            renderWorkflowConnections();
            updateMinimap();
        }
        
        function startConnectionDrag(e, sourceNode) {
            const svg = document.getElementById('workflowConnections');
            const sourceEl = document.querySelector(`[data-node-id="${sourceNode.id}"]`);
            if (!sourceEl) return;
            
            const x1 = sourceNode.x + sourceEl.offsetWidth;
            const y1 = sourceNode.y + sourceEl.offsetHeight / 2;
            let tempPath = null;
            
            const onMouseMove = (e) => {
                if (tempPath) tempPath.remove();
                const canvas = document.getElementById('workflowCanvas');
                const rect = canvas.getBoundingClientRect();
                const x2 = e.clientX - rect.left;
                const y2 = e.clientY - rect.top;
                tempPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                tempPath.setAttribute('d', `M ${x1} ${y1} C ${x1 + 50} ${y1}, ${x2 - 50} ${y2}, ${x2} ${y2}`);
                tempPath.setAttribute('class', 'workflow-connection');
                tempPath.setAttribute('stroke-dasharray', '6 3');
                tempPath.style.opacity = '0.6';
                svg.appendChild(tempPath);
            };
            
            const onMouseUp = (e) => {
                if (tempPath) tempPath.remove();
                document.removeEventListener('mousemove', onMouseMove);
                document.removeEventListener('mouseup', onMouseUp);
                
                const targetEl = e.target.closest('.workflow-canvas-node');
                if (targetEl) {
                    const targetId = targetEl.dataset.nodeId;
                    if (targetId && targetId !== sourceNode.id) {
                        const exists = workflowConnections.some(c => c.source === sourceNode.id && c.target === targetId);
                        if (!exists) {
                            saveWorkflowState();
                            workflowConnections.push({ source: sourceNode.id, target: targetId });
                            renderWorkflowConnections();
                            updateMinimap();
                        }
                    }
                }
            };
            
            document.addEventListener('mousemove', onMouseMove);
            document.addEventListener('mouseup', onMouseUp);
        }
        
        function renderWorkflowConnections() {
            const svg = document.getElementById('workflowConnections');
            const defs = svg.querySelector('defs');
            svg.innerHTML = '';
            if (defs) svg.appendChild(defs);
            
            workflowConnections.forEach(conn => {
                const sourceNode = workflowNodes.find(n => n.id === conn.source);
                const targetNode = workflowNodes.find(n => n.id === conn.target);
                if (!sourceNode || !targetNode) return;
                
                const sourceEl = document.querySelector(`[data-node-id="${conn.source}"]`);
                const targetEl = document.querySelector(`[data-node-id="${conn.target}"]`);
                if (!sourceEl || !targetEl) return;
                
                const x1 = sourceNode.x + sourceEl.offsetWidth;
                const y1 = sourceNode.y + sourceEl.offsetHeight / 2;
                const x2 = targetNode.x;
                const y2 = targetNode.y + targetEl.offsetHeight / 2;
                
                const dx = Math.abs(x2 - x1) * 0.5;
                const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                path.setAttribute('d', `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`);
                path.setAttribute('class', 'workflow-connection' + (conn.status ? ' ' + conn.status : ''));
                path.setAttribute('marker-end', 'url(#arrowhead)');
                path.style.pointerEvents = 'stroke';
                path.onclick = (e) => {
                    e.stopPropagation();
                    if (confirm('Delete this connection?')) {
                        workflowConnections = workflowConnections.filter(c => c !== conn);
                        renderWorkflowConnections();
                    }
                };
                svg.appendChild(path);
            });
        }
        
        function updateMinimap() {
            const minimap = document.getElementById('workflowMinimap');
            const minimapNodes = minimap.querySelectorAll('.workflow-minimap-node');
            minimapNodes.forEach(n => n.remove());
            
            if (workflowNodes.length === 0) return;
            
            const canvas = document.getElementById('workflowCanvas');
            const cw = canvas.offsetWidth;
            const ch = canvas.offsetHeight;
            const mw = 160;
            const mh = 100;
            const scale = Math.min(mw / cw, mh / ch) * 0.8;
            
            workflowNodes.forEach(node => {
                const nodeType = workflowNodeTypes[node.type];
                if (!nodeType) return;
                const dot = document.createElement('div');
                dot.className = 'workflow-minimap-node';
                dot.style.left = (node.x * scale + mw * 0.1) + 'px';
                dot.style.top = (node.y * scale + mh * 0.1) + 'px';
                dot.style.width = '16px';
                dot.style.height = '8px';
                dot.style.background = nodeType.color;
                minimap.appendChild(dot);
            });
        }
        
        function fitWorkflowCanvas() {
            if (workflowNodes.length === 0) return;
            const minX = Math.min(...workflowNodes.map(n => n.x));
            const minY = Math.min(...workflowNodes.map(n => n.y));
            const offsetX = 80 - minX;
            const offsetY = 60 - minY;
            workflowNodes.forEach(n => { n.x += offsetX; n.y += offsetY; });
            renderWorkflowCanvas();
        }
        
        function showWorkflowContextMenu(e) {
            e.preventDefault();
            const existing = document.querySelector('.workflow-context-menu');
            if (existing) existing.remove();
            
            const menu = document.createElement('div');
            menu.className = 'workflow-context-menu';
            menu.style.left = e.clientX + 'px';
            menu.style.top = e.clientY + 'px';
            
            const canvas = document.getElementById('workflowCanvas');
            const rect = canvas.getBoundingClientRect();
            const dropX = Math.round((e.clientX - rect.left - canvasPanOffset.x) / workflowZoom / 10) * 10;
            const dropY = Math.round((e.clientY - rect.top - canvasPanOffset.y) / workflowZoom / 10) * 10;
            
            const nodeTypes = Object.values(workflowNodeTypes);
            const quickNodes = nodeTypes.slice(0, 6);
            
            menu.innerHTML = `
                <div class="workflow-context-menu-item" onclick="this.closest('.workflow-context-menu').remove();fitWorkflowCanvas()">⊞ 适应画布</div>
                <div class="workflow-context-menu-divider"></div>
                ${quickNodes.map(nt => `
                    <div class="workflow-context-menu-item" onclick="this.closest('.workflow-context-menu').remove();addNodeAtPosition('${nt.id}',${dropX},${dropY})">${nt.icon} ${nt.name}</div>
                `).join('')}
                <div class="workflow-context-menu-divider"></div>
                <div class="workflow-context-menu-item" onclick="this.closest('.workflow-context-menu').remove();clearWorkflowCanvas()">🗑️ 清空画布</div>
            `;
            
            document.body.appendChild(menu);
            
            const closeMenu = (e) => {
                if (!menu.contains(e.target)) {
                    menu.remove();
                    document.removeEventListener('click', closeMenu);
                }
            };
            setTimeout(() => document.addEventListener('click', closeMenu), 10);
        }
        
        function addNodeAtPosition(typeId, x, y) {
            const nodeType = workflowNodeTypes[typeId];
            if (!nodeType) return;
            saveWorkflowState();
            const newNode = {
                id: 'node_' + Date.now(),
                type: typeId,
                x: Math.round(x / 10) * 10,
                y: Math.round(y / 10) * 10,
                config: {...nodeType.config}
            };
            workflowNodes.push(newNode);
            renderWorkflowCanvas();
            selectWorkflowNode(newNode.id);
        }
        
        let workflowUndoStack = [];
        let workflowRedoStack = [];
        
        function saveWorkflowState() {
            workflowUndoStack.push({
                nodes: JSON.parse(JSON.stringify(workflowNodes)),
                connections: JSON.parse(JSON.stringify(workflowConnections))
            });
            workflowRedoStack = [];
            if (workflowUndoStack.length > 30) workflowUndoStack.shift();
        }
        
        function undoWorkflowAction() {
            if (workflowUndoStack.length === 0) return;
            workflowRedoStack.push({
                nodes: JSON.parse(JSON.stringify(workflowNodes)),
                connections: JSON.parse(JSON.stringify(workflowConnections))
            });
            const state = workflowUndoStack.pop();
            workflowNodes = state.nodes;
            workflowConnections = state.connections;
            renderWorkflowCanvas();
        }
        
        function redoWorkflowAction() {
            if (workflowRedoStack.length === 0) return;
            workflowUndoStack.push({
                nodes: JSON.parse(JSON.stringify(workflowNodes)),
                connections: JSON.parse(JSON.stringify(workflowConnections))
            });
            const state = workflowRedoStack.pop();
            workflowNodes = state.nodes;
            workflowConnections = state.connections;
            renderWorkflowCanvas();
        }
        
        function filterWorkflowNodes(query) {
            const q = query.toLowerCase();
            document.querySelectorAll('.workflow-node-item').forEach(item => {
                const text = item.textContent.toLowerCase();
                item.style.display = text.includes(q) ? '' : 'none';
            });
        }
        
        function selectWorkflowNode(nodeId) {
            selectedNode = nodeId;
            renderWorkflowCanvas();
            
            const node = workflowNodes.find(n => n.id === nodeId);
            const nodeType = workflowNodeTypes[node.type];
            if (!node || !nodeType) return;
            
            const panel = document.getElementById('workflowPropertiesContent');
            panel.innerHTML = `
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px;padding-bottom:12px;border-bottom:2px solid ${nodeType.color};">
                    <div style="width:36px;height:36px;border-radius:8px;background:linear-gradient(135deg,${nodeType.color}20,${nodeType.color}08);display:flex;align-items:center;justify-content:center;font-size:18px;">${nodeType.icon}</div>
                    <div style="flex:1;">
                        <div style="font-size:14px;font-weight:600;color:var(--text-primary);">${nodeType.name}</div>
                        <div style="font-size:11px;color:var(--text-muted);">${nodeType.description || ''}</div>
                    </div>
                </div>
                ${renderNodeProperties(node, nodeType)}
            `;
        }
        
        function renderNodeProperties(node, nodeType) {
            let basicProps = [];
            let advancedProps = [];
            
            Object.entries(nodeType.config).forEach(([key, defaultValue]) => {
                const isAdvanced = ['code', 'system_prompt', 'template', 'timeout', 'retries', 'condition_type', 'transform_type'].includes(key);
                (isAdvanced ? advancedProps : basicProps).push([key, defaultValue]);
            });
            
            let html = '';
            
            if (basicProps.length > 0) {
                html += `<div class="property-section">`;
                html += `<div class="property-section-header" onclick="this.parentElement.classList.toggle('collapsed')"><span>⚙️ 基础配置</span><span class="toggle-icon">▼</span></div>`;
                html += `<div class="property-section-body">`;
                basicProps.forEach(([key, defaultValue]) => {
                    const value = node.config[key] !== undefined ? node.config[key] : defaultValue;
                    html += `<div class="property-group">`;
                    html += `<div class="property-label">${key}</div>`;
                    html += renderPropertyField(node.id, key, value, defaultValue);
                    html += `</div>`;
                });
                html += `</div></div>`;
            }
            
            if (advancedProps.length > 0) {
                html += `<div class="property-section">`;
                html += `<div class="property-section-header" onclick="this.parentElement.classList.toggle('collapsed')"><span>🔧 高级配置</span><span class="toggle-icon">▼</span></div>`;
                html += `<div class="property-section-body">`;
                advancedProps.forEach(([key, defaultValue]) => {
                    const value = node.config[key] !== undefined ? node.config[key] : defaultValue;
                    html += `<div class="property-group">`;
                    html += `<div class="property-label">${key}</div>`;
                    html += renderPropertyField(node.id, key, value, defaultValue);
                    html += `</div>`;
                });
                html += `</div></div>`;
            }
            
            html += `<div style="margin-top:16px;">`;
            html += `<button onclick="duplicateWorkflowNode('${node.id}')" style="width:100%;padding:8px;border:1px solid var(--border);border-radius:6px;background:var(--bg-primary);color:var(--text-primary);cursor:pointer;font-size:12px;margin-bottom:8px;">📋 复制节点</button>`;
            html += `<button onclick="deleteWorkflowNode('${node.id}')" style="width:100%;padding:8px;border:none;border-radius:6px;background:#ef4444;color:white;cursor:pointer;font-size:12px;">🗑️ 删除节点</button>`;
            html += `</div>`;
            
            return html;
        }
        
        function renderPropertyField(nodeId, key, value, defaultValue) {
            if (typeof defaultValue === 'boolean') {
                return `<label style="display:flex;align-items:center;gap:8px;cursor:pointer;"><input type="checkbox" ${value ? 'checked' : ''} onchange="updateNodeConfig('${nodeId}', '${key}', this.checked)"><span style="font-size:12px;">${value ? 'Enabled' : 'Disabled'}</span></label>`;
            } else if (typeof defaultValue === 'number') {
                return `<input type="number" class="property-input" value="${value}" onchange="updateNodeConfig('${nodeId}', '${key}', parseFloat(this.value))">`;
            } else if (key === 'code' || key === 'prompt' || key === 'system_prompt' || key === 'template') {
                return `<textarea class="property-input property-textarea" onchange="updateNodeConfig('${nodeId}', '${key}', this.value)">${value}</textarea>`;
            } else {
                return `<input type="text" class="property-input" value="${value}" onchange="updateNodeConfig('${nodeId}', '${key}', this.value)">`;
            }
        }
        
        function duplicateWorkflowNode(nodeId) {
            const node = workflowNodes.find(n => n.id === nodeId);
            if (!node) return;
            const newNode = {
                id: 'node_' + Date.now(),
                type: node.type,
                x: node.x + 40,
                y: node.y + 40,
                config: JSON.parse(JSON.stringify(node.config))
            };
            workflowNodes.push(newNode);
            renderWorkflowCanvas();
            selectWorkflowNode(newNode.id);
        }
        
        function updateNodeConfig(nodeId, key, value) {
            const node = workflowNodes.find(n => n.id === nodeId);
            if (node) {
                node.config[key] = value;
            }
        }
        
        function deleteWorkflowNode(nodeId) {
            saveWorkflowState();
            workflowNodes = workflowNodes.filter(n => n.id !== nodeId);
            workflowConnections = workflowConnections.filter(c => c.source !== nodeId && c.target !== nodeId);
            selectedNode = null;
            renderWorkflowCanvas();
            renderWorkflowConnections();
            document.getElementById('workflowPropertiesContent').innerHTML = `
                <div style="text-align:center;color:var(--text-muted);padding:40px 20px;">
                    <div style="font-size:32px;margin-bottom:8px;">👈</div>
                    <div style="font-size:13px;">选择节点以编辑属性</div>
                    <div style="font-size:11px;margin-top:6px;opacity:0.7;">拖拽左侧节点到画布开始</div>
                </div>
            `;
        }
        
        function saveWorkflow() {
            const name = document.getElementById('workflowName').value || '未命名工作流';
            const workflowData = {
                id: currentWorkflow?.id,
                name: name,
                description: '',
                icon: '📋',
                color: '#667eea',
                nodes: workflowNodes,
                connections: workflowConnections
            };
            
            fetch('/workflow', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(workflowData)
            }).then(r => r.json()).then(data => {
                if (data.success) {
                    showToast('工作流已保存');
                    loadWorkflows();
                    closeModal('workflowEditorModal');
                } else {
                    showToast('保存失败: ' + (data.error || '未知错误'));
                }
            });
        }
        
        function executeWorkflow() {
            if (workflowNodes.length === 0) {
                showToast('请先添加节点到画布', 'warning');
                return;
            }
            const startNode = workflowNodes.find(n => n.type === 'start');
            if (!startNode) {
                showToast('工作流需要至少一个开始节点', 'warning');
                return;
            }
            
            const workflowData = {
                nodes: workflowNodes,
                connections: workflowConnections
            };
            
            setAllNodeStatus('running');
            setAllConnectionStatus('running');
            switchPropertiesTab('log');
            appendWorkflowLog('info', '开始执行工作流...');
            
            const startTime = Date.now();
            
            fetch('/workflow/execute', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({workflow: workflowData, inputs: {}})
            }).then(r => r.json()).then(data => {
                const elapsed = Date.now() - startTime;
                
                if (data.success) {
                    setAllNodeStatus('success');
                    setAllConnectionStatus('success');
                    appendWorkflowLog('success', '工作流执行完成 (' + elapsed + 'ms)');
                    
                    if (data.results) {
                        Object.entries(data.results).forEach(function(entry) {
                            var nodeId = entry[0];
                            var result = entry[1];
                            var node = workflowNodes.find(function(n) { return n.id === nodeId; });
                            var nodeType = node ? workflowNodeTypes[node.type] : null;
                            var name = nodeType ? nodeType.name : nodeId;
                            if (result.success) {
                                appendWorkflowLog('success', name + ': 完成');
                            } else {
                                appendWorkflowLog('error', name + ': ' + (result.error || '失败'));
                                setNodeStatus(nodeId, 'error');
                            }
                        });
                    }
                    
                    if (data.output) {
                        appendWorkflowLog('info', '输出: ' + String(data.output).substring(0, 200));
                    }
                    
                    showToast('工作流执行完成');
                } else {
                    setAllNodeStatus('error');
                    setAllConnectionStatus('error');
                    appendWorkflowLog('error', '执行失败: ' + (data.error || '未知错误'));
                    showToast('执行失败: ' + (data.error || '未知错误'));
                }
            }).catch(function(err) {
                setAllNodeStatus('error');
                setAllConnectionStatus('error');
                appendWorkflowLog('error', '网络错误: ' + err.message);
                showToast('执行失败: 网络错误');
            });
        }
        
        function setNodeStatus(nodeId, status) {
            var el = document.querySelector('[data-node-id="' + nodeId + '"] .node-status');
            if (el) {
                el.className = 'node-status ' + status;
            }
        }
        
        function setAllNodeStatus(status) {
            workflowNodes.forEach(function(node) {
                setNodeStatus(node.id, status);
            });
        }
        
        function setAllConnectionStatus(status) {
            workflowConnections.forEach(function(conn) {
                conn.status = status;
            });
            renderWorkflowConnections();
        }
        
        function switchPropertiesTab(tab) {
            var propsContent = document.getElementById('workflowPropertiesContent');
            var logContent = document.getElementById('workflowLogContent');
            var propsBtn = document.getElementById('propsTabBtn');
            var logBtn = document.getElementById('logTabBtn');
            if (!propsContent) return;
            
            if (tab === 'log') {
                propsContent.style.display = 'none';
                logContent.style.display = '';
                propsBtn.style.background = 'transparent';
                propsBtn.style.color = 'var(--text-muted)';
                propsBtn.style.borderColor = 'var(--border)';
                logBtn.style.background = 'var(--primary)';
                logBtn.style.color = 'white';
                logBtn.style.borderColor = 'var(--primary)';
            } else {
                propsContent.style.display = '';
                logContent.style.display = 'none';
                propsBtn.style.background = 'var(--primary)';
                propsBtn.style.color = 'white';
                propsBtn.style.borderColor = 'var(--primary)';
                logBtn.style.background = 'transparent';
                logBtn.style.color = 'var(--text-muted)';
                logBtn.style.borderColor = 'var(--border)';
            }
        }
        
        function appendWorkflowLog(type, message) {
            var logContent = document.getElementById('workflowLogContent');
            if (!logContent) return;
            
            var placeholder = logContent.querySelector('div[style*="text-align:center"]');
            if (placeholder) placeholder.remove();
            
            var colors = { info: '#3b82f6', success: '#10b981', error: '#ef4444', warning: '#f59e0b' };
            var icons = { info: 'ℹ️', success: '✅', error: '❌', warning: '⚠️' };
            var now = new Date();
            var time = String(now.getHours()).padStart(2, '0') + ':' + String(now.getMinutes()).padStart(2, '0') + ':' + String(now.getSeconds()).padStart(2, '0');
            
            var entry = document.createElement('div');
            entry.style.cssText = 'display:flex;gap:8px;align-items:flex-start;padding:6px 0;border-bottom:1px solid var(--border);font-size:11px;line-height:1.4;';
            entry.innerHTML = '<span style="color:var(--text-muted);font-size:9px;flex-shrink:0;margin-top:2px;">' + time + '</span>' +
                '<span style="flex-shrink:0;">' + (icons[type] || 'ℹ️') + '</span>' +
                '<span style="color:' + (colors[type] || 'var(--text-secondary)') + ';">' + message + '</span>';
            logContent.appendChild(entry);
            logContent.scrollTop = logContent.scrollHeight;
        }
        
        function exportWorkflowJSON() {
            var data = {
                name: document.getElementById('workflowName').value || 'untitled',
                version: '1.0',
                exported_at: new Date().toISOString(),
                nodes: workflowNodes,
                connections: workflowConnections
            };
            var blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            var url = URL.createObjectURL(blob);
            var a = document.createElement('a');
            a.href = url;
            a.download = (data.name || 'workflow') + '.json';
            a.click();
            URL.revokeObjectURL(url);
            showToast('工作流已导出');
        }
        
        function importWorkflowJSON(event) {
            var file = event.target.files[0];
            if (!file) return;
            var reader = new FileReader();
            reader.onload = function(e) {
                try {
                    var data = JSON.parse(e.target.result);
                    if (!data.nodes || !Array.isArray(data.nodes)) {
                        showToast('无效的工作流文件', 'warning');
                        return;
                    }
                    workflowNodes = data.nodes;
                    workflowConnections = data.connections || [];
                    if (data.name) {
                        var nameInput = document.getElementById('workflowName');
                        if (nameInput) nameInput.value = data.name;
                    }
                    renderWorkflowCanvas();
                    showToast('工作流已导入');
                } catch (err) {
                    showToast('导入失败: 文件格式错误', 'warning');
                }
            };
            reader.readAsText(file);
            event.target.value = '';
        }
        
        function runWorkflow(workflowId) {
            fetch(`/workflow/${workflowId}/execute`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({inputs: {}})
            }).then(r => r.json()).then(data => {
                if (data.success) {
                    showToast('工作流执行完成');
                } else {
                    showToast('执行失败: ' + (data.error || '未知错误'));
                }
            });
        }
        
        function deleteWorkflow(workflowId) {
            if (!confirm('确定要删除这个工作流吗？')) return;
            
            fetch(`/workflow/${workflowId}`, {method: 'DELETE'}).then(r => r.json()).then(data => {
                if (data.success) {
                    showToast('工作流已删除');
                    loadWorkflows();
                }
            });
        }
        
        function clearWorkflowCanvas() {
            if (!confirm('确定要清空所有节点吗？')) return;
            workflowNodes = [];
            workflowConnections = [];
            selectedNode = null;
            renderWorkflowCanvas();
        }
        
        function zoomWorkflow(delta) {
            workflowZoom = Math.max(0.3, Math.min(3, workflowZoom + delta));
            var container = document.getElementById('workflowNodesContainer');
            var svg = document.getElementById('workflowConnections');
            container.style.transform = 'translate(' + canvasPanOffset.x + 'px,' + canvasPanOffset.y + 'px) scale(' + workflowZoom + ')';
            svg.style.transform = 'translate(' + canvasPanOffset.x + 'px,' + canvasPanOffset.y + 'px) scale(' + workflowZoom + ')';
            updateMinimap();
        }
        
        // 画布拖放处理
        document.addEventListener('DOMContentLoaded', () => {
            const canvas = document.getElementById('workflowCanvas');
            if (canvas) {
                canvas.ondragover = (e) => e.preventDefault();
                canvas.ondrop = (e) => {
                    e.preventDefault();
                    const nodeTypeId = e.dataTransfer.getData('nodeType');
                    const nodeType = workflowNodeTypes[nodeTypeId];
                    if (!nodeType) return;
                    
                    const rect = canvas.getBoundingClientRect();
                    saveWorkflowState();
                    const newNode = {
                        id: 'node_' + Date.now(),
                        type: nodeTypeId,
                        x: Math.round((e.clientX - rect.left - canvasPanOffset.x) / workflowZoom / 10) * 10,
                        y: Math.round((e.clientY - rect.top - canvasPanOffset.y) / workflowZoom / 10) * 10,
                        config: {...nodeType.config}
                    };
                    
                    workflowNodes.push(newNode);
                    renderWorkflowCanvas();
                    selectWorkflowNode(newNode.id);
                };
                
                canvas.onclick = () => {
                    selectedNode = null;
                    renderWorkflowCanvas();
                    document.getElementById('workflowProperties').innerHTML = `
                        <div style="text-align:center;color:var(--text-muted);padding:40px 20px;">
                            <div style="font-size:32px;margin-bottom:8px;">👈</div>
                            <div style="font-size:13px;">选择节点以编辑属性</div>
                        </div>
                    `;
                };
            }
        });
        
        function loadMcpPlugins() {
            fetch('/mcp/plugins').then(r => r.json()).then(data => {
                if (data.success) {
                    mcpPlugins = data.plugins;
                    renderMcpList();
                    // 更新启用的工具列表
                    enabledMcpTools = mcpPlugins.filter(p => p.enabled).flatMap(p => {
                        return p.tools_count > 0 ? [`${p.id}: ${p.description}`] : [];
                    });
                    renderFeatureCenterMeta();
                }
            });
        }
        
        // 检测并执行 MCP 工具调用
        async function detectAndExecuteMcpTool(content) {
            // 检测 MCP 工具调用格式: [MCP:plugin_id:tool_name]{parameters}
            const mcpPattern = /\[MCP:(\w+):(\w+)\]\s*({[^}]*})/g;
            let match;
            let modifiedContent = content;
            
            while ((match = mcpPattern.exec(content)) !== null) {
                const [fullMatch, pluginId, toolName, paramsStr] = match;
                try {
                    const parameters = JSON.parse(paramsStr);
                    const result = await executeMcpTool(pluginId, toolName, parameters);
                    
                    // 替换工具调用为执行结果
                    const resultText = formatMcpResult(result);
                    modifiedContent = modifiedContent.replace(fullMatch, resultText);
                } catch (e) {
                    console.error('MCP工具执行失败:', e);
                    modifiedContent = modifiedContent.replace(fullMatch, `[工具执行失败: ${e.message}]`);
                }
            }
            
            return modifiedContent;
        }

        async function executeMcpTool(pluginId, toolName, parameters) {
            const res = await fetch('/mcp/execute', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({plugin_id: pluginId, tool_name: toolName, parameters})
            });
            const data = await res.json();
            return data.result || {error: '执行失败'};
        }
        
        function formatMcpResult(result) {
            if (result.error) {
                return `<div style="color:#e74c3c;padding:8px;background:rgba(231,76,60,0.1);border-radius:6px;margin:4px 0;">❌ ${result.error}</div>`;
            }
            
            // 格式化不同类型的结果
            if (result.content !== undefined) {
                return `<div style="padding:10px;background:rgba(102,126,234,0.1);border-radius:6px;margin:4px 0;"><pre style="margin:0;white-space:pre-wrap;">${result.content}</pre></div>`;
            }
            if (result.results !== undefined && Array.isArray(result.results)) {
                const items = result.results.map(r => `<li><a href="${r.link}" target="_blank" style="color:var(--primary);">${r.title}</a></li>`).join('');
                return `<div style="padding:10px;background:rgba(245,158,11,0.1);border-radius:6px;margin:4px 0;"><ol style="margin:0;padding-left:20px;">${items}</ol></div>`;
            }
            if (result.result !== undefined) {
                return `<div style="padding:8px;background:rgba(16,185,129,0.1);border-radius:6px;margin:4px 0;font-weight:600;">🧮 结果: ${result.result}</div>`;
            }
            if (result.items !== undefined && Array.isArray(result.items)) {
                const items = result.items.map(i => `<li>${i.type === 'directory' ? '📁' : '📄'} ${i.name}</li>`).join('');
                return `<div style="padding:10px;background:rgba(59,130,246,0.1);border-radius:6px;margin:4px 0;"><ul style="margin:0;padding-left:20px;">${items}</ul></div>`;
            }
            
            return `<div style="padding:8px;background:rgba(102,126,234,0.1);border-radius:6px;margin:4px 0;">${JSON.stringify(result)}</div>`;
        }
        
        // 获取 MCP 系统提示词
        function getMcpSystemPrompt() {
            if (enabledMcpTools.length === 0) return '';
            
            return `

【MCP工具使用说明】
你可以使用以下工具来帮助用户。当需要使用工具时，请按以下格式输出：
[MCP:插件ID:工具名]{"参数名": "参数值"}

可用工具：
${enabledMcpTools.map(t => `- ${t}`).join(String.fromCharCode(10))}

示例：
- 读取文件: [MCP:filesystem:read_file]{"path": "~/document.txt"}
- 搜索网络: [MCP:web_search:search]{"query": "最新科技新闻", "num_results": 5}
- 计算: [MCP:calculator:calculate]{"expression": "2+2*3"}
- 获取时间: [MCP:datetime:get_current_time]{"timezone": "Asia/Shanghai"}
`;
        }
        
        let currentMcpCategory = 'all';

        function filterMcpCategory(cat) {
            currentMcpCategory = cat;
            document.querySelectorAll('[data-mcp-cat]').forEach(b => b.classList.remove('active'));
            const activeBtn = document.querySelector(`[data-mcp-cat="${cat}"]`);
            if (activeBtn) activeBtn.classList.add('active');
            renderMcpList();
        }

        function renderMcpList() {
            const container = document.getElementById('mcpList');
            if (!mcpPlugins.length) {
                container.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:20px;">暂无可用插件</div>';
                return;
            }
            let filtered = mcpPlugins;
            if (currentMcpCategory !== 'all') {
                filtered = mcpPlugins.filter(p => (p.category || p.type || 'builtin') === currentMcpCategory);
            }
            const catLabels = {builtin: '内置', integration: '集成', ai: 'AI', tool: '工具'};
            const catColors = {builtin: '#667eea', integration: '#3b82f6', ai: '#10b981', tool: '#f59e0b'};
            container.innerHTML = filtered.map(p => {
                const enabled = p.enabled;
                const cat = p.category || p.type || 'builtin';
                const catLabel = catLabels[cat] || cat;
                const catColor = catColors[cat] || '#667eea';
                return `
                    <div class="mcp-item ${enabled ? 'enabled' : ''}" data-id="${p.id}">
                        <div class="mcp-icon" style="background:linear-gradient(135deg,${p.color},${p.color}dd);">${p.icon}</div>
                        <div class="mcp-info">
                            <div class="mcp-name">${escapeHtml(p.name)} <span style="font-size:9px;background:${catColor}22;color:${catColor};padding:1px 6px;border-radius:3px;margin-left:4px;">${catLabel}</span></div>
                            <div class="mcp-desc">${p.description}</div>
                        </div>
                        <span class="mcp-tools-count">${p.tools_count}个工具</span>
                        <button class="mcp-config-btn" onclick="showMcpConfig('${p.id}')" style="margin-right:8px;">⚙️</button>
                        <div class="mcp-toggle ${enabled ? 'enabled' : ''}" onclick="toggleMcpPlugin('${p.id}', ${!enabled})"></div>
                    </div>
                `;
            }).join('');
        }
        
        function toggleMcpPlugin(pluginId, enabled) {
            fetch(`/mcp/plugin/${pluginId}/enable`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({enabled})
            }).then(r => r.json()).then(data => {
                if (data.success) {
                    showToast(data.message);
                    loadMcpPlugins();
                } else {
                    showToast('操作失败: ' + (data.error || '未知错误'));
                }
            });
        }
        
        function refreshMcpPlugins() {
            loadMcpPlugins();
            showToast('已刷新插件列表');
        }
        
        function showMcpConfig(pluginId) {
            const plugin = mcpPlugins.find(p => p.id === pluginId);
            if (!plugin) return;
            
            // 简单的配置提示框
            if (plugin.id === 'filesystem') {
                const readOnly = confirm('是否设置为只读模式？' + String.fromCharCode(10) + String.fromCharCode(10) + '确定 = 只读' + String.fromCharCode(10) + '取消 = 可读写');
                fetch(`/mcp/plugin/${pluginId}/config`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({config: {read_only: readOnly, allowed_paths: [os.path.expanduser("~")]}})
                }).then(r => r.json()).then(data => {
                    if (data.success) showToast('配置已更新');
                });
            } else if (plugin.id === 'web_search') {
                const numResults = prompt('设置默认搜索结果数量 (1-10):', '5');
                if (numResults && !isNaN(numResults)) {
                    fetch(`/mcp/plugin/${pluginId}/config`, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({config: {max_results: parseInt(numResults)}})
                    }).then(r => r.json()).then(data => {
                        if (data.success) showToast('配置已更新');
                    });
                }
            } else {
                showToast('该插件暂无配置选项');
            }
        }
        
