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
        
        const PROMPT_TEMPLATES = [
            {id:'code',name:'代码助手',prompt:'请帮我写一段代码，实现以下功能：',icon:'📝',desc:'代码生成、重构与调试建议',category:'general',source:'通用',tags:['代码','生成']},
            {id:'translate',name:'翻译助手',prompt:'请将以下内容翻译成英文：',icon:'🌐',desc:'多语言翻译与语气适配',category:'general',source:'通用',tags:['翻译','多语言']},
            {id:'summary',name:'总结助手',prompt:'请帮我总结以下内容的要点：',icon:'📋',desc:'快速提炼重点与行动项',category:'general',source:'通用',tags:['总结','提炼']},
            {id:'email',name:'邮件助手',prompt:'请帮我写一封邮件，主题是：',icon:'📧',desc:'商务邮件写作与回复模板',category:'general',source:'通用',tags:['邮件','写作']},
            {id:'article',name:'文章助手',prompt:'请帮我写一篇关于',icon:'✍️',desc:'内容创作与表达优化',category:'general',source:'通用',tags:['写作','创作']},
            {id:'debug',name:'调试助手',prompt:'以下代码有问题，请帮我找出错误：',icon:'🐛',desc:'定位报错并给出修复路径',category:'general',source:'通用',tags:['调试','排错']},
            {id:'brainstorm',name:'头脑风暴',prompt:'请围绕以下主题进行头脑风暴，给出10个创意方向：',icon:'💡',desc:'发散思维与创意激发',category:'general',source:'通用',tags:['创意','发散']},
            {id:'explain',name:'概念解释',prompt:'请用通俗易懂的方式解释以下概念：',icon:'🎓',desc:'复杂概念的通俗化解读',category:'general',source:'通用',tags:['解释','学习']},
            {id:'comparison',name:'对比分析',prompt:'请对比分析以下两个方案/产品的优劣势：',icon:'⚖️',desc:'多维度对比与决策支持',category:'general',source:'通用',tags:['对比','决策']},
            {id:'checklist',name:'清单生成',prompt:'请为以下任务/场景生成一份完整的检查清单：',icon:'✅',desc:'任务清单与流程检查',category:'general',source:'通用',tags:['清单','流程']},
            {id:'ecommerce',name:'电商增长策略',prompt:'请为我的电商产品制定30天增长方案，包含人群画像、卖点、活动节奏、投放素材结构与转化指标。',icon:'🛍️',desc:'活动节奏、投放与转化闭环',category:'growth',source:'实战',tags:['电商','增长'],template:'ecommerce'},
            {id:'shortvideo',name:'短视频增长',prompt:'请为我设计7天短视频内容计划，输出选题、脚本结构、前3秒钩子、封面标题和发布时间建议。',icon:'🎬',desc:'账号内容排期与选题脚本',category:'growth',source:'实战',tags:['短视频','内容'],template:'shortvideo'},
            {id:'seo_strategy',name:'SEO内容策略',prompt:'请为我的网站制定SEO内容策略，包含关键词矩阵、内容日历、内链规划、外链策略和排名追踪方案。',icon:'🔎',desc:'搜索流量获取与内容规划',category:'growth',source:'实战',tags:['SEO','流量'],template:'seo_strategy'},
            {id:'user_retention',name:'用户留存体系',prompt:'请为我的产品设计用户留存体系，包含Aha Moment分析、留存漏斗、触达策略、召回机制和核心指标看板。',icon:'🔄',desc:'留存分析与召回策略设计',category:'growth',source:'实战',tags:['留存','运营'],template:'user_retention'},
            {id:'community_ops',name:'社区运营方案',prompt:'请为我的产品制定社区运营方案，包含社区定位、内容生态、KOL策略、活跃机制和冷启动计划。',icon:'👥',desc:'社区冷启动与活跃运营',category:'growth',source:'实战',tags:['社区','运营'],template:'community_ops'},
            {id:'content_marketing',name:'内容营销方案',prompt:'请为我的品牌制定内容营销方案，包含内容矩阵、分发渠道、KPI指标、内容日历和效果评估体系。',icon:'📢',desc:'内容矩阵与分发策略',category:'growth',source:'实战',tags:['营销','内容'],template:'content_marketing'},
            {id:'pricing_strategy',name:'定价策略分析',prompt:'请为我的产品制定定价策略，包含竞品定价分析、价值锚点、价格弹性测试、阶梯方案和促销节奏。',icon:'💵',desc:'定价模型与竞争策略',category:'growth',source:'商业分析',tags:['定价','策略'],template:'pricing_strategy'},
            {id:'growth_hacking',name:'增长黑客实验',prompt:'请为我的产品设计增长黑客实验方案，包含北极星指标、实验假设、MVP方案、数据埋点和迭代节奏。',icon:'🚀',desc:'低成本增长实验设计',category:'growth',source:'增长实践',tags:['增长','实验'],template:'growth_hacking'},
            {id:'brand_strategy',name:'品牌策略规划',prompt:'请为我的品牌制定策略规划，包含品牌定位、价值主张、视觉体系、传播策略和品牌资产建设路径。',icon:'🏷️',desc:'品牌定位与资产建设',category:'growth',source:'品牌实践',tags:['品牌','策略'],template:'brand_strategy'},
            {id:'prompt_eval',name:'提示词评测体系',prompt:'请为我的AI应用设计提示词评测方案，包括测试集、评分维度、A/B对比和持续回归机制。',icon:'🧪',desc:'借鉴 Promptfoo 的评测思想',category:'engineering',source:'Promptfoo',tags:['评测','AI'],template:'prompt_eval'},
            {id:'agent_observability',name:'智能体可观测性',prompt:'请为我的AI助手设计可观测性方案，覆盖链路追踪、错误分层、质量指标和排障流程。',icon:'📈',desc:'借鉴 Langfuse 的追踪与评估实践',category:'engineering',source:'Langfuse',tags:['可观测','AI'],template:'agent_observability'},
            {id:'ai_workflow',name:'自动化工作流设计',prompt:'请为我的业务场景设计一套AI自动化工作流，包含触发器、节点编排、审批机制和失败重试策略。',icon:'🔁',desc:'借鉴 n8n 的节点化编排思路',category:'engineering',source:'n8n',tags:['自动化','工作流'],template:'ai_workflow'},
            {id:'ai_redteam',name:'AI安全红队演练',prompt:'请为我的AI产品制定红队测试计划，覆盖越狱、提示注入、数据泄露和工具滥用风险。',icon:'🛡️',desc:'借鉴 Promptfoo 的红队测试场景',category:'engineering',source:'Promptfoo',tags:['安全','红队'],template:'ai_redteam'},
            {id:'api_design',name:'API接口设计',prompt:'请为以下业务场景设计RESTful API接口规范，包含资源定义、请求响应格式、错误码体系、版本策略和限流方案。',icon:'🔌',desc:'RESTful API规范与设计',category:'engineering',source:'工程实践',tags:['API','设计'],template:'api_design'},
            {id:'system_arch',name:'系统架构评审',prompt:'请对以下系统架构进行评审，从可用性、扩展性、安全性、成本四个维度输出评审报告和优化建议。',icon:'🏗️',desc:'架构评审与优化建议',category:'engineering',source:'工程实践',tags:['架构','评审'],template:'system_arch'},
            {id:'ci_cd',name:'CI/CD流水线',prompt:'请为我的项目设计CI/CD流水线方案，包含构建阶段、测试门禁、部署策略（蓝绿/金丝雀）、回滚机制和环境管理。',icon:'🚀',desc:'持续集成与部署方案',category:'engineering',source:'工程实践',tags:['CI/CD','DevOps'],template:'ci_cd'},
            {id:'code_review',name:'代码审查',prompt:'请对以下代码进行专业审查，分析代码质量、潜在Bug、性能问题和安全漏洞，并给出改进建议：',icon:'🔍',desc:'代码质量分析与优化建议',category:'engineering',source:'工程实践',tags:['审查','质量'],template:'code_review'},
            {id:'perf_optimize',name:'性能优化方案',prompt:'请对以下系统/代码进行性能分析，输出瓶颈定位、优化方案、预期收益和实施优先级。',icon:'⚡',desc:'性能瓶颈定位与优化',category:'engineering',source:'工程实践',tags:['性能','优化'],template:'perf_optimize'},
            {id:'db_design',name:'数据库设计',prompt:'请为以下业务场景设计数据库方案，包含ER模型、表结构、索引策略、分片方案和读写分离架构。',icon:'🗄️',desc:'数据库建模与优化',category:'engineering',source:'工程实践',tags:['数据库','设计'],template:'db_design'},
            {id:'rag_ops',name:'RAG知识运营',prompt:'请为我的知识库系统制定RAG运营方案，包含文档治理、检索质量评估和持续优化闭环。',icon:'📚',desc:'借鉴 Dify/Open WebUI 的RAG实践',category:'knowledge',source:'Dify/Open WebUI',tags:['RAG','知识库'],template:'rag_ops'},
            {id:'deep_research',name:'深度研究任务',prompt:'请围绕这个主题制定深度研究计划，包含信息源策略、交叉验证、证据分级和结论产出格式。',icon:'🔍',desc:'面向咨询与研究型工作',category:'knowledge',source:'研究实践',tags:['研究','分析'],template:'deep_research'},
            {id:'literature_review',name:'文献综述生成',prompt:'请围绕以下研究主题，生成结构化文献综述：研究背景、核心流派、方法论对比、研究空白和未来方向。',icon:'📖',desc:'学术文献综述框架',category:'knowledge',source:'学术实践',tags:['文献','学术'],template:'literature_review'},
            {id:'competitive_analysis',name:'竞品深度分析',prompt:'请对以下竞品进行深度分析，覆盖产品定位、核心功能、技术架构、商业模式、用户口碑和战略预判。',icon:'⚔️',desc:'竞品调研与战略分析',category:'knowledge',source:'商业分析',tags:['竞品','分析'],template:'competitive_analysis'},
            {id:'patent_analysis',name:'专利技术分析',prompt:'请对以下技术领域的专利布局进行分析，包含核心专利识别、技术路线图、侵权风险评估和专利策略建议。',icon:'📜',desc:'专利布局与技术路线',category:'knowledge',source:'知识产权',tags:['专利','技术'],template:'patent_analysis'},
            {id:'industry_report',name:'行业研究报告',prompt:'请为以下行业生成研究报告，包含市场规模、竞争格局、技术趋势、政策环境和投资建议。',icon:'📊',desc:'行业全景与趋势研判',category:'knowledge',source:'研究实践',tags:['行业','报告'],template:'industry_report'},
            {id:'tech_radar',name:'技术雷达',prompt:'请为以下技术领域生成技术雷达报告，包含技术成熟度评估、采用建议、风险提示和落地路径。',icon:'📡',desc:'技术趋势与采用决策',category:'knowledge',source:'技术实践',tags:['技术','趋势'],template:'tech_radar'},
            {id:'contract_review',name:'合同审阅顾问',prompt:'请基于合同摘要、交易背景、谈判目标和约束条件，输出风险审阅报告：高风险条款、责任边界、可谈判点、修改建议和谈判话术。',icon:'⚖️',desc:'法务合同风险审阅',category:'professional',source:'法务实践',tags:['合同','法务'],template:'contract_review'},
            {id:'financial_model',name:'财务模型搭建',prompt:'请为以下业务场景搭建财务模型框架，包含收入预测、成本结构、现金流、关键假设和敏感性分析。',icon:'💰',desc:'财务建模与估值分析',category:'professional',source:'金融实践',tags:['财务','建模'],template:'financial_model'},
            {id:'medical_literature',name:'医学文献解读',prompt:'请对以下医学文献进行专业解读，包含研究设计、统计方法、主要发现、临床意义和局限性评价。',icon:'🏥',desc:'医学文献循证解读',category:'professional',source:'医学实践',tags:['医学','文献'],template:'medical_literature'},
            {id:'legal_research',name:'法律检索报告',prompt:'请围绕以下法律问题进行检索分析，输出：适用法条、相关案例、裁判观点、争议焦点和法律风险提示。',icon:'⚖️',desc:'法律条文与案例检索',category:'professional',source:'法律实践',tags:['法律','检索'],template:'legal_research'},
            {id:'hr_interview',name:'面试评估框架',prompt:'请为以下岗位设计结构化面试方案，包含能力模型、行为面试题、评分标准和录用决策矩阵。',icon:'🤝',desc:'结构化面试设计',category:'professional',source:'HR实践',tags:['面试','HR'],template:'hr_interview'},
            {id:'investment_memo',name:'投资备忘录',prompt:'请为以下投资标的撰写投资备忘录，包含市场机会、团队评估、商业模式、财务预测、风险分析和投资建议。',icon:'💹',desc:'投资分析与决策备忘',category:'professional',source:'投资实践',tags:['投资','分析'],template:'investment_memo'},
            {id:'project_charter',name:'项目章程',prompt:'请为以下项目生成项目章程，包含项目目标、范围边界、里程碑计划、资源需求、风险登记和干系人分析。',icon:'📋',desc:'项目启动与章程制定',category:'professional',source:'项目管理',tags:['项目','管理'],template:'project_charter'},
            {id:'product_prd',name:'产品PRD生成',prompt:'请为以下产品需求生成PRD文档，包含背景与目标、用户故事、功能规格、交互流程、数据指标和里程碑计划。',icon:'📱',desc:'产品需求文档生成',category:'product',source:'产品实践',tags:['PRD','产品'],template:'product_prd'},
            {id:'ux_review',name:'UX体验评审',prompt:'请对以下产品界面进行UX评审，从信息架构、交互流程、视觉层次、可访问性和情感设计五个维度输出改进建议。',icon:'🎨',desc:'用户体验评审与优化',category:'product',source:'设计实践',tags:['UX','评审'],template:'ux_review'},
            {id:'data_analysis',name:'数据分析报告',prompt:'请对以下数据进行深度分析，输出：数据概览、关键发现、异常检测、归因分析和行动建议。',icon:'📊',desc:'数据洞察与决策支持',category:'product',source:'数据实践',tags:['数据','分析'],template:'data_analysis'},
            {id:'ab_test_design',name:'A/B实验设计',prompt:'请为以下产品功能设计A/B实验方案，包含假设定义、指标体系、样本量计算、分流策略和结果判定标准。',icon:'🧪',desc:'实验设计与统计检验',category:'product',source:'数据实践',tags:['A/B','实验'],template:'ab_test_design'},
            {id:'user_interview',name:'用户访谈提纲',prompt:'请为以下产品研究目标设计用户访谈提纲，包含访谈目的、目标用户筛选、问题设计（开场/核心/深挖/收尾）和数据分析框架。',icon:'🗣️',desc:'用户研究访谈设计',category:'product',source:'用研实践',tags:['访谈','用研'],template:'user_interview'},
            {id:'user_journey',name:'用户旅程地图',prompt:'请为以下产品场景绘制用户旅程地图，包含阶段划分、触点、情绪曲线、痛点和机会点。',icon:'🗺️',desc:'用户旅程与触点分析',category:'product',source:'设计实践',tags:['旅程','体验'],template:'user_journey'},
            {id:'feature_priority',name:'需求优先级矩阵',prompt:'请对以下产品需求列表进行优先级排序，使用RICE模型（Reach/Impact/Confidence/Effort）输出优先级矩阵和迭代建议。',icon:'📊',desc:'RICE模型需求排序',category:'product',source:'产品实践',tags:['需求','优先级'],template:'feature_priority'},
            {id:'design_system',name:'设计系统规范',prompt:'请为以下产品生成设计系统规范，包含设计原则、色彩体系、字体规范、组件库和交互模式。',icon:'🎨',desc:'设计系统与组件规范',category:'product',source:'设计实践',tags:['设计','规范'],template:'design_system'},
            {id:'sql_gen',name:'SQL生成',prompt:'请根据以下自然语言描述生成SQL查询语句，并解释查询逻辑：',icon:'🗃️',desc:'自然语言转SQL查询',category:'engineering',source:'工程实践',tags:['SQL','数据库'],template:'sql_gen'},
            {id:'test_gen',name:'测试用例生成',prompt:'请为以下代码生成全面的单元测试，覆盖主要功能、边界条件和异常情况：',icon:'🧪',desc:'单元测试用例自动生成',category:'engineering',source:'工程实践',tags:['测试','质量'],template:'test_gen'},
            {id:'security_audit',name:'安全审计',prompt:'请对以下代码/系统进行安全审计，识别潜在的安全漏洞（如SQL注入、XSS、CSRF等）并给出修复建议：',icon:'🔒',desc:'代码安全漏洞检测',category:'engineering',source:'安全实践',tags:['安全','审计'],template:'security_audit'},
            {id:'refactor',name:'代码重构',prompt:'请分析以下代码并提供重构建议，重点关注可读性、可维护性和性能：',icon:'♻️',desc:'智能代码优化建议',category:'engineering',source:'工程实践',tags:['重构','优化'],template:'refactor'}
        ];
        
        const PROMPT_FAVORITES = JSON.parse(localStorage.getItem('promptFavorites') || '[]');
        const PROMPT_USAGE = JSON.parse(localStorage.getItem('promptUsage') || '{}');
        const CUSTOM_TEMPLATES = JSON.parse(localStorage.getItem('customTemplates') || '[]');

        function savePromptFavorites() { localStorage.setItem('promptFavorites', JSON.stringify(PROMPT_FAVORITES)); }
        function savePromptUsage() { localStorage.setItem('promptUsage', JSON.stringify(PROMPT_USAGE)); }
        function saveCustomTemplates() { localStorage.setItem('customTemplates', JSON.stringify(CUSTOM_TEMPLATES)); }

        function getAllTemplates() { return [...PROMPT_TEMPLATES, ...CUSTOM_TEMPLATES]; }

        function renderPromptList() {
            const groups = {
                general: '🤖 通用助手',
                growth: '📈 增长运营',
                engineering: '⚙️ 工程治理',
                knowledge: '📚 知识研究',
                professional: '💼 专业服务',
                product: '📱 产品设计'
            };
            const allTpls = getAllTemplates();
            let filtered;
            if (promptCategory === 'favorites') {
                filtered = allTpls.filter(p => PROMPT_FAVORITES.includes(p.id));
            } else if (promptCategory === 'custom') {
                filtered = CUSTOM_TEMPLATES;
            } else {
                filtered = allTpls.filter(p => {
                    const hitCategory = promptCategory === 'all' || p.category === promptCategory;
                    const q = promptSearchKeyword.trim().toLowerCase();
                    const hitKeyword = !q || `${p.name} ${p.desc} ${p.source} ${(p.tags||[]).join(' ')} ${p.prompt}`.toLowerCase().includes(q);
                    return hitCategory && hitKeyword;
                });
            }
            const list = document.getElementById('promptList');
            const statsTotal = document.getElementById('promptStatsTotal');
            const statsFiltered = document.getElementById('promptStatsFiltered');
            if (statsTotal) statsTotal.textContent = allTpls.length + ' 个模板';
            if (statsFiltered && promptSearchKeyword) {
                statsFiltered.style.display = 'inline';
                statsFiltered.textContent = '/ 筛选: ' + filtered.length;
            } else if (statsFiltered) {
                statsFiltered.style.display = 'none';
            }
            if (!filtered.length) {
                list.innerHTML = '<div style="text-align:center;padding:40px;color:var(--text-muted);">' +
                    (promptCategory === 'favorites' ? '<div style="font-size:32px;margin-bottom:8px;">⭐</div><div>暂无收藏模板，点击卡片上的星标收藏</div>' :
                     promptCategory === 'custom' ? '<div style="font-size:32px;margin-bottom:8px;">🔧</div><div>暂无自定义模板，点击"新建"创建</div>' :
                     '<div style="font-size:32px;margin-bottom:8px;">🔍</div><div>未找到匹配模板，试试更短关键词</div>') + '</div>';
                return;
            }
            let html = '';
            if (promptCategory === 'all' || (promptCategory !== 'favorites' && promptCategory !== 'custom')) {
                Object.keys(groups).forEach(groupKey => {
                    const groupItems = filtered.filter(x => x.category === groupKey);
                    if (!groupItems.length) return;
                    html += `<div class="prompt-group-title">${groups[groupKey]} (${groupItems.length})</div>`;
                    html += `<div class="prompt-grid">${groupItems.map(p => renderPromptCard(p)).join('')}</div>`;
                });
                const uncategorized = filtered.filter(x => !groups[x.category]);
                if (uncategorized.length) {
                    html += `<div class="prompt-group-title">其他 (${uncategorized.length})</div>`;
                    html += `<div class="prompt-grid">${uncategorized.map(p => renderPromptCard(p)).join('')}</div>`;
                }
            } else {
                html += `<div class="prompt-grid">${filtered.map(p => renderPromptCard(p)).join('')}</div>`;
            }
            list.innerHTML = html;
        }

        function renderPromptCard(p) {
            const isFav = PROMPT_FAVORITES.includes(p.id);
            const isCustom = CUSTOM_TEMPLATES.some(c => c.id === p.id);
            return `<div class="prompt-card" onclick="usePromptTemplate('${p.id}')">
                <button class="prompt-fav-btn ${isFav ? 'is-fav' : ''}" onclick="event.stopPropagation();toggleFavorite('${p.id}')" title="${isFav ? '取消收藏' : '收藏'}">${isFav ? '★' : '☆'}</button>
                <div class="prompt-head">
                    <span style="font-size:18px;">${p.icon || '📝'}</span>
                    <span class="prompt-name">${escapeHtml(p.name)}</span>
                </div>
                <div class="prompt-desc">${escapeHtml(p.desc)}</div>
                <div class="prompt-meta">
                    ${(p.tags||[]).map(t => `<span class="prompt-meta-tag">${escapeHtml(t)}</span>`).join('')}
                    ${p.template ? '<span class="prompt-meta-tag cat-tag">结构化</span>' : ''}
                    ${isCustom ? '<span class="prompt-meta-tag" style="background:rgba(245,158,11,0.1);color:#f59e0b;">自定义</span>' : ''}
                    ${p.source ? `<span style="font-size:9px;color:var(--text-muted);margin-left:auto;">${escapeHtml(p.source)}</span>` : ''}
                </div>
            </div>`;
        }
        
        function setPromptSearch(value) {
            promptSearchKeyword = value || '';
            renderPromptList();
        }
        
        function setPromptCategory(category) {
            promptCategory = category;
            document.querySelectorAll('.prompt-chip').forEach(el => el.classList.remove('active'));
            const idMap = {all:'promptCatAll',general:'promptCatGeneral',growth:'promptCatGrowth',engineering:'promptCatEngineering',knowledge:'promptCatKnowledge',professional:'promptCatProfessional',product:'promptCatProduct',favorites:'promptCatFavorites',custom:'promptCatCustom'};
            const activeEl = document.getElementById(idMap[category] || 'promptCatAll');
            if (activeEl) activeEl.classList.add('active');
            renderPromptList();
        }
        
        function openPromptWorkbench() {
            const existing = document.getElementById('promptWorkbenchModal');
            if (existing) existing.remove();
            
            const modal = document.createElement('div');
            modal.className = 'modal-overlay show';
            modal.id = 'promptWorkbenchModal';
            modal.onclick = function(e) { if (e.target === modal) closeModal('promptWorkbenchModal'); };
            modal.innerHTML = `
                <div class="modal" style="max-width:860px;width:95%;max-height:85vh;display:flex;flex-direction:column;">
                    <div class="modal-header" style="background:linear-gradient(135deg,#667eea,#764ba2);color:white;border-radius:16px 16px 0 0;flex-shrink:0;">
                        <h3 style="margin:0;">🧭 专业工作台</h3>
                        <button class="modal-close" onclick="closeModal('promptWorkbenchModal')" style="color:white;font-size:18px;">×</button>
                    </div>
                    <div style="flex:1;overflow:hidden;display:flex;flex-direction:column;padding:0;">
                        <div style="padding:14px 16px 0;flex-shrink:0;">
                            <div class="workbench-tabs" style="margin-bottom:12px;">
                                <button class="workbench-tab active" onclick="switchWorkbenchTab('all', this)">📋 全部</button>
                                <button class="workbench-tab" onclick="switchWorkbenchTab('code', this)">💻 代码</button>
                                <button class="workbench-tab" onclick="switchWorkbenchTab('doc', this)">📄 文档</button>
                                <button class="workbench-tab" onclick="switchWorkbenchTab('data', this)">📊 数据</button>
                                <button class="workbench-tab" onclick="switchWorkbenchTab('favorites', this)">⭐ 收藏</button>
                                <button class="workbench-tab" onclick="switchWorkbenchTab('integrations', this)">🔗 接入</button>
                            </div>
                            <input class="project-input" id="workbenchSearch" placeholder="🔍 搜索模板、场景、工具..." style="width:100%;margin-bottom:12px;" oninput="filterWorkbenchTemplates()">
                        </div>
                        <div id="workbenchContent" style="flex:1;overflow-y:auto;padding:0 16px 16px;"></div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
            renderWorkbenchContent('all');
        }

        function switchWorkbenchTab(category, btn) {
            document.querySelectorAll('.workbench-tab').forEach(t => t.classList.remove('active'));
            btn.classList.add('active');
            renderWorkbenchContent(category);
        }

        function renderWorkbenchContent(category) {
            const container = document.getElementById('workbenchContent');
            if (!container) return;
            
            if (category === 'integrations') {
                renderIntegrationsPage(container);
                return;
            }
            
            const allTemplates = getAllTemplates();
            let templates;
            if (category === 'all') {
                templates = allTemplates;
            } else if (category === 'favorites') {
                templates = allTemplates.filter(t => PROMPT_FAVORITES.includes(t.id));
            } else if (category === 'code') {
                templates = allTemplates.filter(t => t.category === 'engineering' || (t.tags && t.tags.some(tag => ['代码','审查','重构','测试','API','SQL','安全'].includes(tag))));
            } else if (category === 'doc') {
                templates = allTemplates.filter(t => t.category === 'general' || (t.tags && t.tags.some(tag => ['写作','文档','翻译','邮件','报告','创作'].includes(tag))));
            } else if (category === 'data') {
                templates = allTemplates.filter(t => t.category === 'product' || (t.tags && t.tags.some(tag => ['数据','分析','A/B','实验','统计'].includes(tag))));
            } else {
                templates = allTemplates.filter(t => t.category === category);
            }
            
            const categoryColors = { general: '#667eea', growth: '#10b981', engineering: '#3b82f6', knowledge: '#f59e0b', professional: '#ec4899', product: '#8b5cf6', code: '#3b82f6', doc: '#10b981', data: '#f59e0b' };
            
            container.innerHTML = templates.map(t => {
                const catClass = t.category || 'general';
                const catColor = categoryColors[catClass] || '#667eea';
                const isFav = PROMPT_FAVORITES.includes(t.id);
                return `
                <div class="workbench-card" onclick="applyWorkbenchTemplate('${t.id}')">
                    <div class="card-icon ${catClass}">${t.icon || '📝'}</div>
                    <div style="flex:1;min-width:0;">
                        <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
                            <span style="font-size:14px;font-weight:600;color:var(--text-primary);">${escapeHtml(t.name)}</span>
                            ${(t.tags||[]).map(tag => `<span style="font-size:9px;padding:1px 6px;border-radius:4px;background:${catColor}15;color:${catColor};font-weight:500;">${tag}</span>`).join('')}
                        </div>
                        <div style="font-size:12px;color:var(--text-muted);line-height:1.4;">${escapeHtml(t.desc)}</div>
                    </div>
                    <button onclick="event.stopPropagation();toggleFavorite('${t.id}')" style="background:none;border:none;font-size:16px;cursor:pointer;padding:4px;opacity:${isFav ? '1' : '0.5'};transition:opacity 0.2s;color:${isFav ? '#f59e0b' : 'inherit'};" onmouseover="this.style.opacity='1'" onmouseout="this.style.opacity='${isFav ? '1' : '0.5'}'">${isFav ? '★' : '☆'}</button>
                </div>
            `}).join('') || '<div style="text-align:center;color:var(--text-muted);padding:40px;">暂无模板</div>';
        }

        function renderIntegrationsPage(container) {
            const integrations = [
                { id: 'mcp', name: 'MCP 协议', icon: '🤖', desc: 'Model Context Protocol 接入，支持工具调用和资源访问', status: 'active', color: '#8b5cf6', version: 'v1.2' },
                { id: 'rag', name: '知识库接入', icon: '📚', desc: 'RAG 检索增强生成，支持多种向量数据库', status: 'active', color: '#ec4899', version: 'v2.0' },
                { id: 'api', name: 'API 接入', icon: '🔌', desc: '配置外部 API 服务接入 (OpenAI/Claude/Gemini)', status: 'available', color: '#667eea', version: 'v1.0' },
                { id: 'database', name: '数据库连接', icon: '🗄️', desc: '连接 MySQL、PostgreSQL、MongoDB 等数据库', status: 'available', color: '#10b981', version: 'v1.1' },
                { id: 'webhook', name: 'Webhook', icon: '🔗', desc: '配置 Webhook 回调地址，实现事件通知', status: 'available', color: '#f59e0b', version: 'v1.0' },
                { id: 'tools', name: '工具调用', icon: '🔧', desc: '外部工具和函数调用，扩展 AI 能力', status: 'available', color: '#06b6d4', version: 'v1.3' },
                { id: 'plugins', name: '插件系统', icon: '🧩', desc: '管理和配置插件，扩展系统功能', status: 'available', color: '#84cc16', version: 'v0.9' },
                { id: 'oauth', name: 'OAuth 认证', icon: '🔐', desc: '第三方 OAuth 登录接入', status: 'available', color: '#f43f5e', version: 'v1.0' },
            ];
            
            container.innerHTML = `
                <div style="margin-bottom:20px;">
                    <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
                        <span style="font-size:14px;font-weight:600;color:var(--text-primary);">已启用</span>
                        <span style="font-size:11px;padding:2px 8px;border-radius:10px;background:#10b98115;color:#10b981;font-weight:500;">${integrations.filter(i => i.status === 'active').length}</span>
                    </div>
                    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px;">
                        ${integrations.filter(i => i.status === 'active').map(i => `
                            <div class="integration-card active" onclick="openIntegrationDetail('${i.id}')" style="padding:16px;background:linear-gradient(135deg,${i.color}12,${i.color}05);border:2px solid ${i.color}40;border-radius:12px;cursor:pointer;transition:all 0.2s;position:relative;overflow:hidden;">
                                <div style="position:absolute;top:8px;right:8px;font-size:9px;padding:2px 6px;border-radius:4px;background:${i.color}20;color:${i.color};">${i.version}</div>
                                <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
                                    <span style="font-size:24px;">${i.icon}</span>
                                    <span style="font-size:14px;font-weight:600;color:var(--text-primary);">${i.name}</span>
                                </div>
                                <div style="font-size:11px;color:var(--text-muted);margin-bottom:10px;line-height:1.4;">${i.desc}</div>
                                <div style="display:flex;align-items:center;gap:6px;">
                                    <span style="width:6px;height:6px;background:#10b981;border-radius:50%;animation:pulse 2s infinite;"></span>
                                    <span style="font-size:10px;color:#10b981;font-weight:500;">运行中</span>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
                <div>
                    <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
                        <span style="font-size:14px;font-weight:600;color:var(--text-primary);">可接入的服务</span>
                        <span style="font-size:11px;padding:2px 8px;border-radius:10px;background:var(--bg-secondary);color:var(--text-muted);font-weight:500;">${integrations.filter(i => i.status === 'available').length}</span>
                    </div>
                    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px;">
                        ${integrations.filter(i => i.status === 'available').map(i => `
                            <div class="integration-card" onclick="openIntegrationDetail('${i.id}')" style="padding:16px;background:var(--bg-secondary);border:1px solid var(--border);border-radius:12px;cursor:pointer;transition:all 0.2s;position:relative;">
                                <div style="position:absolute;top:8px;right:8px;font-size:9px;padding:2px 6px;border-radius:4px;background:var(--bg-primary);color:var(--text-muted);">${i.version}</div>
                                <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
                                    <span style="font-size:24px;">${i.icon}</span>
                                    <span style="font-size:14px;font-weight:600;color:var(--text-primary);">${i.name}</span>
                                </div>
                                <div style="font-size:11px;color:var(--text-muted);margin-bottom:10px;line-height:1.4;">${i.desc}</div>
                                <div style="display:flex;align-items:center;gap:6px;">
                                    <span style="width:6px;height:6px;background:var(--text-muted);border-radius:50%;opacity:0.5;"></span>
                                    <span style="font-size:10px;color:var(--text-muted);">点击配置</span>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }

        function openIntegrationDetail(integrationId) {
            const details = {
                'api': { name: 'API 接入', icon: '🔌', desc: '配置外部 API 服务接入，支持 OpenAI、Claude 等多种 API', config: ['API Key', 'Base URL', 'Model Name'] },
                'database': { name: '数据库连接', icon: '🗄️', desc: '连接 MySQL、PostgreSQL、MongoDB 等数据库', config: ['Host', 'Port', 'Database', 'Username', 'Password'] },
                'webhook': { name: 'Webhook', icon: '🔗', desc: '配置 Webhook 回调地址，实现事件通知', config: ['Callback URL', 'Secret Key', 'Events'] },
                'mcp': { name: 'MCP 协议', icon: '🤖', desc: 'Model Context Protocol 接入，支持工具调用和资源访问', config: ['Server URL', 'Transport Type'] },
                'rag': { name: '知识库接入', icon: '📚', desc: 'RAG 检索增强生成，支持多种向量数据库', config: ['Vector DB', 'Embedding Model', 'Collection Name'] },
                'tools': { name: '工具调用', icon: '🔧', desc: '外部工具和函数调用，扩展 AI 能力', config: ['Tool Name', 'Endpoint', 'Parameters'] },
                'plugins': { name: '插件系统', icon: '🧩', desc: '管理和配置插件，扩展系统功能', config: ['Plugin Directory', 'Auto Load'] },
                'oauth': { name: 'OAuth 认证', icon: '🔐', desc: '第三方 OAuth 登录接入', config: ['Provider', 'Client ID', 'Client Secret', 'Redirect URI'] },
            };
            
            const detail = details[integrationId];
            if (!detail) return;
            
            const modal = document.createElement('div');
            modal.className = 'modal-overlay show';
            modal.id = 'integrationDetailModal';
            modal.onclick = function(e) { if (e.target === modal) closeModal('integrationDetailModal'); };
            modal.innerHTML = `
                <div class="modal" style="max-width:500px;width:90%;max-height:80vh;display:flex;flex-direction:column;">
                    <div class="modal-header" style="flex-shrink:0;">
                        <h3 style="margin:0;display:flex;align-items:center;gap:8px;">
                            <span style="font-size:24px;">${detail.icon}</span>
                            ${detail.name}
                        </h3>
                        <button class="modal-close" onclick="closeModal('integrationDetailModal')" style="font-size:18px;">×</button>
                    </div>
                    <div style="flex:1;overflow-y:auto;padding:16px 0;">
                        <div style="font-size:13px;color:var(--text-secondary);margin-bottom:16px;line-height:1.6;">${detail.desc}</div>
                        <div style="margin-bottom:16px;">
                            <div style="font-size:12px;font-weight:600;color:var(--text-primary);margin-bottom:8px;">配置项</div>
                            ${detail.config.map(c => `
                                <div style="margin-bottom:12px;">
                                    <label style="display:block;font-size:11px;color:var(--text-muted);margin-bottom:4px;">${c}</label>
                                    <input class="project-input" placeholder="输入 ${c}..." style="width:100%;">
                                </div>
                            `).join('')}
                        </div>
                        <div style="background:var(--bg-secondary);border-radius:8px;padding:12px;">
                            <div style="font-size:11px;color:var(--text-muted);margin-bottom:4px;">状态</div>
                            <div style="display:flex;align-items:center;gap:8px;">
                                <span style="width:10px;height:10px;background:#10b981;border-radius:50%;"></span>
                                <span style="font-size:12px;color:var(--text-primary);">已配置</span>
                            </div>
                        </div>
                    </div>
                    <div style="display:flex;gap:10px;justify-content:flex-end;padding-top:12px;border-top:1px solid var(--border);">
                        <button class="project-mini-btn" onclick="closeModal('integrationDetailModal')">取消</button>
                        <button class="project-mini-btn" style="background:linear-gradient(135deg,var(--primary),#764ba2);color:white;" onclick="saveIntegration('${integrationId}')">保存配置</button>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }

        function saveIntegration(integrationId) {
            closeModal('integrationDetailModal');
            showToast('配置已保存');
        }

        function filterWorkbenchTemplates() {
            const search = document.getElementById('workbenchSearch')?.value.toLowerCase() || '';
            const cards = document.querySelectorAll('.workbench-card');
            cards.forEach(card => {
                const text = card.textContent.toLowerCase();
                card.style.display = text.includes(search) ? 'flex' : 'none';
            });
        }

        function applyWorkbenchTemplate(templateId) {
            const item = getAllTemplates().find(t => t.id === templateId);
            if (!item) return;
            const template = { name: item.name, icon: item.icon || '📝', prompt: item.prompt, steps: ['输入内容', 'AI分析', '生成结果', '优化建议'] };
            PROMPT_USAGE[templateId] = (PROMPT_USAGE[templateId] || 0) + 1;
            savePromptUsage();
            closeModal('promptWorkbenchModal');
            setTimeout(() => {
                openWorkPlanningModal(templateId, template);
            }, 100);
        }
        
        function openWorkPlanningModal(templateId, template) {
            // 先移除已存在的模态框
            const existing = document.getElementById('workPlanningModal');
            if (existing) existing.remove();
            
            const modal = document.createElement('div');
            modal.className = 'modal-overlay show';
            modal.id = 'workPlanningModal';
            modal.onclick = function(e) { if (e.target === modal) closeModal('workPlanningModal'); };
            
            // 根据不同模板创建不同的界面
            const specializedUI = getSpecializedUI(templateId, template);
            
            modal.innerHTML = `
                <div class="modal" style="max-width:1000px;width:95%;max-height:90vh;display:flex;flex-direction:column;background:linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);color:#fff;">
                    <div class="modal-header" style="flex-shrink:0;border-bottom:1px solid rgba(255,255,255,0.1);padding:16px 20px;">
                        <div style="display:flex;align-items:center;gap:12px;">
                            <span style="font-size:32px;">${template.icon}</span>
                            <div>
                                <h3 style="margin:0;font-size:20px;">${template.name}</h3>
                                <p style="margin:4px 0 0;font-size:12px;color:rgba(255,255,255,0.6);">${getTemplateDescription(templateId)}</p>
                            </div>
                        </div>
                        <button class="modal-close" onclick="closeModal('workPlanningModal')" style="font-size:24px;background:rgba(255,255,255,0.1);border:none;border-radius:8px;width:36px;height:36px;cursor:pointer;color:#fff;">×</button>
                    </div>
                    <div style="flex:1;overflow-y:auto;padding:20px;">
                        ${specializedUI}
                    </div>
                    <div class="modal-actions" style="flex-shrink:0;padding:16px 20px;border-top:1px solid rgba(255,255,255,0.1);display:flex;justify-content:space-between;gap:12px;">
                        <button onclick="closeModal('workPlanningModal')" style="padding:10px 20px;background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.2);border-radius:8px;color:#fff;cursor:pointer;">关闭</button>
                        <button onclick="executeSpecializedTask('${templateId}')" style="padding:10px 24px;background:linear-gradient(135deg, #667eea, #764ba2);border:none;border-radius:8px;color:#fff;cursor:pointer;font-weight:600;">🚀 开始执行</button>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }
        
        function getTemplateDescription(templateId) {
            const descriptions = {
                'code-review': '专业代码审查，识别潜在问题和优化建议',
                'doc-gen': '自动生成技术文档和API说明',
                'api-design': '设计RESTful API接口规范',
                'test-gen': '生成单元测试和集成测试用例',
                'refactor': '代码重构和质量优化建议',
                'security': '安全漏洞扫描和风险评估',
                'data-analysis': '数据统计分析和可视化建议',
                'report-gen': '结构化报告生成和导出',
                'creative-write': '创意内容创作和润色'
            };
            return descriptions[templateId] || '专业工具';
        }
        
        function getSpecializedUI(templateId, template) {
            const uis = {
                'code-review': `
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;">
                        <div>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">📝 待审查代码</label>
                            <textarea id="codeInput" placeholder="粘贴您的代码..." style="width:100%;height:200px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;padding:12px;color:#fff;font-family:monospace;font-size:13px;resize:none;"></textarea>
                        </div>
                        <div>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">⚙️ 审查选项</label>
                            <div style="background:rgba(0,0,0,0.2);border-radius:8px;padding:16px;">
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="checkbox" id="checkSecurity" checked style="width:18px;height:18px;">
                                    <span>🔒 安全漏洞检查</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="checkbox" id="checkPerformance" checked style="width:18px;height:18px;">
                                    <span>⚡ 性能优化建议</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="checkbox" id="checkStyle" checked style="width:18px;height:18px;">
                                    <span>📋 代码风格检查</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
                                    <input type="checkbox" id="checkBestPractice" checked style="width:18px;height:18px;">
                                    <span>✨ 最佳实践建议</span>
                                </label>
                            </div>
                            <label style="display:block;font-size:14px;font-weight:600;margin:16px 0 8px;">🎯 编程语言</label>
                            <select id="codeLanguage" style="width:100%;padding:10px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;color:#fff;">
                                <option value="auto">自动检测</option>
                                <option value="python">Python</option>
                                <option value="javascript">JavaScript</option>
                                <option value="java">Java</option>
                                <option value="cpp">C/C++</option>
                                <option value="go">Go</option>
                            </select>
                        </div>
                    </div>
                `,
                'doc-gen': `
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;">
                        <div>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">📝 代码/接口内容</label>
                            <textarea id="docSource" placeholder="粘贴代码或API接口定义..." style="width:100%;height:200px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;padding:12px;color:#fff;font-family:monospace;font-size:13px;resize:none;"></textarea>
                        </div>
                        <div>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">📄 文档类型</label>
                            <div style="background:rgba(0,0,0,0.2);border-radius:8px;padding:16px;">
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="radio" name="docType" value="api" checked style="width:18px;height:18px;">
                                    <span>🔌 API文档</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="radio" name="docType" value="readme" style="width:18px;height:18px;">
                                    <span>📖 README文档</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="radio" name="docType" value="technical" style="width:18px;height:18px;">
                                    <span>📚 技术文档</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
                                    <input type="radio" name="docType" value="comment" style="width:18px;height:18px;">
                                    <span>💬 代码注释</span>
                                </label>
                            </div>
                            <label style="display:block;font-size:14px;font-weight:600;margin:16px 0 8px;">🌍 文档语言</label>
                            <select id="docLanguage" style="width:100%;padding:10px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;color:#fff;">
                                <option value="zh">中文</option>
                                <option value="en">English</option>
                            </select>
                        </div>
                    </div>
                `,
                'api-design': `
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;">
                        <div>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">📋 需求描述</label>
                            <textarea id="apiRequirements" placeholder="描述您的API需求，例如：用户管理、订单处理..." style="width:100%;height:150px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;padding:12px;color:#fff;font-size:14px;resize:none;"></textarea>
                            <label style="display:block;font-size:14px;font-weight:600;margin:16px 0 8px;">🏷️ API名称</label>
                            <input type="text" id="apiName" placeholder="例如：UserAPI" style="width:100%;padding:10px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;color:#fff;">
                        </div>
                        <div>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">⚙️ API风格</label>
                            <div style="background:rgba(0,0,0,0.2);border-radius:8px;padding:16px;">
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="radio" name="apiStyle" value="rest" checked style="width:18px;height:18px;">
                                    <span>🔄 RESTful API</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="radio" name="apiStyle" value="graphql" style="width:18px;height:18px;">
                                    <span>📊 GraphQL</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
                                    <input type="radio" name="apiStyle" value="grpc" style="width:18px;height:18px;">
                                    <span>⚡ gRPC</span>
                                </label>
                            </div>
                            <label style="display:block;font-size:14px;font-weight:600;margin:16px 0 8px;">🔐 认证方式</label>
                            <select id="authType" style="width:100%;padding:10px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;color:#fff;">
                                <option value="none">无认证</option>
                                <option value="jwt">JWT Token</option>
                                <option value="oauth">OAuth 2.0</option>
                                <option value="apikey">API Key</option>
                            </select>
                        </div>
                    </div>
                `,
                'test-gen': `
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;">
                        <div>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">📝 待测试代码</label>
                            <textarea id="testSource" placeholder="粘贴需要生成测试的代码..." style="width:100%;height:180px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;padding:12px;color:#fff;font-family:monospace;font-size:13px;resize:none;"></textarea>
                        </div>
                        <div>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">🧪 测试框架</label>
                            <select id="testFramework" style="width:100%;padding:10px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;color:#fff;margin-bottom:16px;">
                                <option value="pytest">pytest (Python)</option>
                                <option value="jest">Jest (JavaScript)</option>
                                <option value="junit">JUnit (Java)</option>
                                <option value="gtest">Google Test (C++)</option>
                            </select>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">📊 测试覆盖率</label>
                            <div style="background:rgba(0,0,0,0.2);border-radius:8px;padding:16px;">
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="checkbox" id="testNormal" checked style="width:18px;height:18px;">
                                    <span>✅ 正常用例</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="checkbox" id="testEdge" checked style="width:18px;height:18px;">
                                    <span>🔍 边界用例</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
                                    <input type="checkbox" id="testError" checked style="width:18px;height:18px;">
                                    <span>❌ 异常用例</span>
                                </label>
                            </div>
                        </div>
                    </div>
                `,
                'refactor': `
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;">
                        <div>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">📝 待重构代码</label>
                            <textarea id="refactorSource" placeholder="粘贴需要重构的代码..." style="width:100%;height:200px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;padding:12px;color:#fff;font-family:monospace;font-size:13px;resize:none;"></textarea>
                        </div>
                        <div>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">🎯 重构目标</label>
                            <div style="background:rgba(0,0,0,0.2);border-radius:8px;padding:16px;">
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="checkbox" id="refactorReadability" checked style="width:18px;height:18px;">
                                    <span>📖 提高可读性</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="checkbox" id="refactorPerformance" style="width:18px;height:18px;">
                                    <span>⚡ 性能优化</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="checkbox" id="refactorModular" checked style="width:18px;height:18px;">
                                    <span>🧩 模块化拆分</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
                                    <input type="checkbox" id="refactorPattern" style="width:18px;height:18px;">
                                    <span>📐 设计模式应用</span>
                                </label>
                            </div>
                        </div>
                    </div>
                `,
                'security': `
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;">
                        <div>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">📝 待审计代码</label>
                            <textarea id="securitySource" placeholder="粘贴需要安全审计的代码..." style="width:100%;height:200px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;padding:12px;color:#fff;font-family:monospace;font-size:13px;resize:none;"></textarea>
                        </div>
                        <div>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">🔒 安全检查项</label>
                            <div style="background:rgba(0,0,0,0.2);border-radius:8px;padding:16px;">
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="checkbox" id="secSQL" checked style="width:18px;height:18px;">
                                    <span>💉 SQL注入</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="checkbox" id="secXSS" checked style="width:18px;height:18px;">
                                    <span>🎯 XSS攻击</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="checkbox" id="secCSRF" checked style="width:18px;height:18px;">
                                    <span>🔄 CSRF漏洞</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
                                    <input type="checkbox" id="secAuth" checked style="width:18px;height:18px;">
                                    <span>🔐 认证授权漏洞</span>
                                </label>
                            </div>
                        </div>
                    </div>
                `,
                'data-analysis': `
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;">
                        <div>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">📊 数据内容</label>
                            <textarea id="dataSource" placeholder="粘贴数据（CSV、JSON格式或文本）..." style="width:100%;height:180px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;padding:12px;color:#fff;font-family:monospace;font-size:13px;resize:none;"></textarea>
                        </div>
                        <div>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">📈 分析类型</label>
                            <div style="background:rgba(0,0,0,0.2);border-radius:8px;padding:16px;">
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="checkbox" id="analysisDesc" checked style="width:18px;height:18px;">
                                    <span>📊 描述性统计</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="checkbox" id="analysisTrend" style="width:18px;height:18px;">
                                    <span>📈 趋势分析</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="checkbox" id="analysisCorr" style="width:18px;height:18px;">
                                    <span>🔗 相关性分析</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
                                    <input type="checkbox" id="analysisVisual" checked style="width:18px;height:18px;">
                                    <span>📉 可视化建议</span>
                                </label>
                            </div>
                        </div>
                    </div>
                `,
                'report-gen': `
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;">
                        <div>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">📋 报告内容</label>
                            <textarea id="reportContent" placeholder="输入报告的核心内容、数据或要点..." style="width:100%;height:180px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;padding:12px;color:#fff;font-size:14px;resize:none;"></textarea>
                        </div>
                        <div>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">📄 报告类型</label>
                            <select id="reportType" style="width:100%;padding:10px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;color:#fff;margin-bottom:16px;">
                                <option value="business">商业报告</option>
                                <option value="technical">技术报告</option>
                                <option value="research">研究报告</option>
                                <option value="summary">总结报告</option>
                            </select>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">📑 输出格式</label>
                            <select id="reportFormat" style="width:100%;padding:10px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;color:#fff;">
                                <option value="markdown">Markdown</option>
                                <option value="html">HTML</option>
                                <option value="plain">纯文本</option>
                            </select>
                        </div>
                    </div>
                `,
                'creative-write': `
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;">
                        <div>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">💡 创作主题</label>
                            <input type="text" id="creativeTopic" placeholder="输入创作主题..." style="width:100%;padding:12px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;color:#fff;font-size:14px;margin-bottom:16px;">
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">📝 补充说明</label>
                            <textarea id="creativeNotes" placeholder="补充要求、风格偏好等..." style="width:100%;height:120px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;padding:12px;color:#fff;font-size:14px;resize:none;"></textarea>
                        </div>
                        <div>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">✍️ 创作类型</label>
                            <div style="background:rgba(0,0,0,0.2);border-radius:8px;padding:16px;">
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="radio" name="creativeType" value="article" checked style="width:18px;height:18px;">
                                    <span>📰 文章</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="radio" name="creativeType" value="story" style="width:18px;height:18px;">
                                    <span>📖 故事</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="radio" name="creativeType" value="copywriting" style="width:18px;height:18px;">
                                    <span>📢 文案</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
                                    <input type="radio" name="creativeType" value="script" style="width:18px;height:18px;">
                                    <span>🎬 脚本</span>
                                </label>
                            </div>
                            <label style="display:block;font-size:14px;font-weight:600;margin:16px 0 8px;">🎭 风格</label>
                            <select id="creativeStyle" style="width:100%;padding:10px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;color:#fff;">
                                <option value="professional">专业正式</option>
                                <option value="casual">轻松活泼</option>
                                <option value="humorous">幽默风趣</option>
                                <option value="emotional">情感共鸣</option>
                            </select>
                        </div>
                    </div>
                `
            };
            return uis[templateId] || `
                <div>
                    <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">📝 输入内容</label>
                    <textarea id="workInput" placeholder="请输入您的内容..." style="width:100%;height:200px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;padding:12px;color:#fff;font-size:14px;resize:none;"></textarea>
                </div>
            `;
        }
        
        function executeSpecializedTask(templateId) {
            let prompt = '';
            let input = '';
            
            switch(templateId) {
                case 'code-review':
                    input = document.getElementById('codeInput')?.value || '';
                    const lang = document.getElementById('codeLanguage')?.value || 'auto';
                    const checks = [];
                    if (document.getElementById('checkSecurity')?.checked) checks.push('安全漏洞');
                    if (document.getElementById('checkPerformance')?.checked) checks.push('性能优化');
                    if (document.getElementById('checkStyle')?.checked) checks.push('代码风格');
                    if (document.getElementById('checkBestPractice')?.checked) checks.push('最佳实践');
                    prompt = `请对以下${lang === 'auto' ? '' : lang}代码进行专业审查，重点关注：${checks.join('、')}\n\n代码：\n${input}`;
                    break;
                    
                case 'doc-gen':
                    input = document.getElementById('docSource')?.value || '';
                    const docType = document.querySelector('input[name="docType"]:checked')?.value || 'api';
                    const docLang = document.getElementById('docLanguage')?.value || 'zh';
                    prompt = `请为以下内容生成${docType === 'api' ? 'API文档' : docType === 'readme' ? 'README文档' : docType === 'technical' ? '技术文档' : '代码注释'}（${docLang === 'zh' ? '中文' : '英文'}）：\n\n${input}`;
                    break;
                    
                case 'api-design':
                    input = document.getElementById('apiRequirements')?.value || '';
                    const apiName = document.getElementById('apiName')?.value || '';
                    const apiStyle = document.querySelector('input[name="apiStyle"]:checked')?.value || 'rest';
                    const auth = document.getElementById('authType')?.value || 'none';
                    prompt = `请根据以下需求设计${apiStyle === 'rest' ? 'RESTful API' : apiStyle === 'graphql' ? 'GraphQL' : 'gRPC'}接口：\n需求：${input}\nAPI名称：${apiName}\n认证方式：${auth}`;
                    break;
                    
                case 'test-gen':
                    input = document.getElementById('testSource')?.value || '';
                    const framework = document.getElementById('testFramework')?.value || 'pytest';
                    prompt = `请使用${framework}框架为以下代码生成测试用例：\n\n${input}`;
                    break;
                    
                case 'refactor':
                    input = document.getElementById('refactorSource')?.value || '';
                    const goals = [];
                    if (document.getElementById('refactorReadability')?.checked) goals.push('提高可读性');
                    if (document.getElementById('refactorPerformance')?.checked) goals.push('性能优化');
                    if (document.getElementById('refactorModular')?.checked) goals.push('模块化拆分');
                    if (document.getElementById('refactorPattern')?.checked) goals.push('设计模式应用');
                    prompt = `请重构以下代码，目标：${goals.join('、')}\n\n代码：\n${input}`;
                    break;
                    
                case 'security':
                    input = document.getElementById('securitySource')?.value || '';
                    const secChecks = [];
                    if (document.getElementById('secSQL')?.checked) secChecks.push('SQL注入');
                    if (document.getElementById('secXSS')?.checked) secChecks.push('XSS攻击');
                    if (document.getElementById('secCSRF')?.checked) secChecks.push('CSRF漏洞');
                    if (document.getElementById('secAuth')?.checked) secChecks.push('认证授权漏洞');
                    prompt = `请对以下代码进行安全审计，检查：${secChecks.join('、')}\n\n代码：\n${input}`;
                    break;
                    
                case 'data-analysis':
                    input = document.getElementById('dataSource')?.value || '';
                    const analysis = [];
                    if (document.getElementById('analysisDesc')?.checked) analysis.push('描述性统计');
                    if (document.getElementById('analysisTrend')?.checked) analysis.push('趋势分析');
                    if (document.getElementById('analysisCorr')?.checked) analysis.push('相关性分析');
                    if (document.getElementById('analysisVisual')?.checked) analysis.push('可视化建议');
                    prompt = `请对以下数据进行${analysis.join('、')}：\n\n数据：\n${input}`;
                    break;
                    
                case 'report-gen':
                    input = document.getElementById('reportContent')?.value || '';
                    const reportType = document.getElementById('reportType')?.value || 'business';
                    const reportFormat = document.getElementById('reportFormat')?.value || 'markdown';
                    prompt = `请根据以下内容生成${reportType === 'business' ? '商业报告' : reportType === 'technical' ? '技术报告' : reportType === 'research' ? '研究报告' : '总结报告'}（${reportFormat}格式）：\n\n${input}`;
                    break;
                    
                case 'creative-write':
                    const topic = document.getElementById('creativeTopic')?.value || '';
                    const notes = document.getElementById('creativeNotes')?.value || '';
                    const creativeType = document.querySelector('input[name="creativeType"]:checked')?.value || 'article';
                    const style = document.getElementById('creativeStyle')?.value || 'professional';
                    prompt = `请以${style === 'professional' ? '专业正式' : style === 'casual' ? '轻松活泼' : style === 'humorous' ? '幽默风趣' : '情感共鸣'}的风格，创作一篇${creativeType === 'article' ? '文章' : creativeType === 'story' ? '故事' : creativeType === 'copywriting' ? '文案' : '脚本'}。\n主题：${topic}\n${notes ? '补充要求：' + notes : ''}`;
                    break;
                    
                default:
                    input = document.getElementById('workInput')?.value || '';
                    prompt = input;
            }
            
            if (!prompt || prompt.includes('undefined')) {
                showToast('请填写必要的内容');
                return;
            }
            
            closeModal('workPlanningModal');
            $('mainInput').value = prompt;
            showToast('正在执行任务...');
            $('sendBtn').click();
        }

        function toggleFavorite(templateId) {
            const idx = PROMPT_FAVORITES.indexOf(templateId);
            if (idx >= 0) {
                PROMPT_FAVORITES.splice(idx, 1);
                showToast('已取消收藏');
            } else {
                PROMPT_FAVORITES.push(templateId);
                showToast('已收藏');
            }
            savePromptFavorites();
            renderPromptList();
        }

        function favoriteTemplate(templateId) {
            if (!PROMPT_FAVORITES.includes(templateId)) {
                PROMPT_FAVORITES.push(templateId);
                savePromptFavorites();
            }
            showToast('已收藏模板');
        }

        function createCustomTemplate() {
            const existing = document.getElementById('customTemplateModal');
            if (existing) existing.remove();
            const modal = document.createElement('div');
            modal.className = 'modal-overlay show';
            modal.id = 'customTemplateModal';
            modal.onclick = function(e) { if (e.target === modal) closeModal('customTemplateModal'); };
            modal.innerHTML = `
                <div class="modal" style="max-width:520px;width:92%;max-height:85vh;display:flex;flex-direction:column;">
                    <div class="modal-header" style="flex-shrink:0;">
                        <h3 style="margin:0;">🔧 新建自定义模板</h3>
                        <button class="modal-close" onclick="closeModal('customTemplateModal')">×</button>
                    </div>
                    <div style="flex:1;overflow-y:auto;padding:16px 0;">
                        <div style="margin-bottom:14px;">
                            <label style="font-size:11px;display:block;margin-bottom:4px;color:var(--text-muted);">模板名称 *</label>
                            <input class="project-input" id="ctName" placeholder="例如：周报生成器" style="width:100%;">
                        </div>
                        <div style="margin-bottom:14px;">
                            <label style="font-size:11px;display:block;margin-bottom:4px;color:var(--text-muted);">描述</label>
                            <input class="project-input" id="ctDesc" placeholder="简短描述模板用途" style="width:100%;">
                        </div>
                        <div style="margin-bottom:14px;">
                            <label style="font-size:11px;display:block;margin-bottom:4px;color:var(--text-muted);">图标 (Emoji)</label>
                            <input class="project-input" id="ctIcon" placeholder="📝" value="📝" style="width:80px;">
                        </div>
                        <div style="margin-bottom:14px;">
                            <label style="font-size:11px;display:block;margin-bottom:4px;color:var(--text-muted);">分类</label>
                            <select class="project-input" id="ctCategory" style="width:100%;">
                                <option value="general">通用助手</option>
                                <option value="growth">增长运营</option>
                                <option value="engineering">工程治理</option>
                                <option value="knowledge">知识研究</option>
                                <option value="professional">专业服务</option>
                                <option value="product">产品设计</option>
                            </select>
                        </div>
                        <div style="margin-bottom:14px;">
                            <label style="font-size:11px;display:block;margin-bottom:4px;color:var(--text-muted);">标签 (逗号分隔)</label>
                            <input class="project-input" id="ctTags" placeholder="例如：周报,汇报" style="width:100%;">
                        </div>
                        <div style="margin-bottom:14px;">
                            <label style="font-size:11px;display:block;margin-bottom:4px;color:var(--text-muted);">提示词模板 *</label>
                            <textarea class="project-input" id="ctPrompt" placeholder="输入提示词模板内容，使用 {变量名} 表示可替换变量" style="width:100%;height:120px;resize:vertical;"></textarea>
                        </div>
                    </div>
                    <div style="display:flex;gap:10px;justify-content:flex-end;padding-top:12px;border-top:1px solid var(--border);flex-shrink:0;">
                        <button class="project-mini-btn" onclick="closeModal('customTemplateModal')">取消</button>
                        <button class="project-mini-btn" style="background:linear-gradient(135deg,var(--primary),#764ba2);color:white;" onclick="saveCustomTemplate()">保存模板</button>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }

        function saveCustomTemplate() {
            const name = document.getElementById('ctName').value.trim();
            const desc = document.getElementById('ctDesc').value.trim();
            const icon = document.getElementById('ctIcon').value.trim() || '📝';
            const category = document.getElementById('ctCategory').value;
            const tags = document.getElementById('ctTags').value.split(',').map(t => t.trim()).filter(Boolean);
            const prompt = document.getElementById('ctPrompt').value.trim();
            if (!name || !prompt) {
                showToast('请填写模板名称和提示词');
                return;
            }
            const id = 'custom_' + Date.now();
            CUSTOM_TEMPLATES.push({id, name, desc: desc || name, icon, category, tags, prompt, source: '自定义', custom: true});
            saveCustomTemplates();
            closeModal('customTemplateModal');
            renderPromptList();
            showToast('模板已保存');
        }

        function deleteCustomTemplate(templateId) {
            const idx = CUSTOM_TEMPLATES.findIndex(c => c.id === templateId);
            if (idx >= 0) {
                CUSTOM_TEMPLATES.splice(idx, 1);
                saveCustomTemplates();
                const favIdx = PROMPT_FAVORITES.indexOf(templateId);
                if (favIdx >= 0) { PROMPT_FAVORITES.splice(favIdx, 1); savePromptFavorites(); }
                renderPromptList();
                showToast('模板已删除');
            }
        }

        function openQuickSceneModal() {
            createCustomTemplate();
        }

        function saveQuickScene() {
            saveCustomTemplate();
        }

        function applyQuickScene(sceneId) {
            const item = getAllTemplates().find(t => t.id === sceneId);
            if (item && item.prompt) {
                $('mainInput').value = item.prompt;
                PROMPT_USAGE[sceneId] = (PROMPT_USAGE[sceneId] || 0) + 1;
                savePromptUsage();
                showToast('已应用场景模板');
            }
        }

        function loadTemplateAnalysis() {
            const range = document.getElementById('templateAnalysisRange')?.value || '7d';
            fetch('/templates/analysis?range=' + range)
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        const el = (id) => document.getElementById(id);
                        if (el('workbenchTemplateCount')) el('workbenchTemplateCount').textContent = data.stats.total_templates || getAllTemplates().length;
                        if (el('workbenchFavoriteCount')) el('workbenchFavoriteCount').textContent = data.stats.favorites || PROMPT_FAVORITES.length;
                        if (el('workbenchUsageCount')) el('workbenchUsageCount').textContent = data.stats.usage || Object.values(PROMPT_USAGE).reduce((a,b) => a+b, 0);
                        if (el('workbenchCustomCount')) el('workbenchCustomCount').textContent = data.stats.custom || CUSTOM_TEMPLATES.length;
                    }
                }).catch(() => {});
        }

        function exportTemplateReport() {
            const allTpls = getAllTemplates();
            const report = {
                exportTime: new Date().toISOString(),
                totalTemplates: allTpls.length,
                presetTemplates: PROMPT_TEMPLATES.length,
                customTemplates: CUSTOM_TEMPLATES.length,
                favorites: PROMPT_FAVORITES.length,
                totalUsage: Object.values(PROMPT_USAGE).reduce((a,b) => a+b, 0),
                usageByTemplate: PROMPT_USAGE,
                templates: allTpls.map(t => ({
                    id: t.id, name: t.name, category: t.category, source: t.source,
                    tags: t.tags || [], isFavorite: PROMPT_FAVORITES.includes(t.id),
                    usageCount: PROMPT_USAGE[t.id] || 0, isCustom: !!t.custom
                }))
            };
            const blob = new Blob([JSON.stringify(report, null, 2)], {type: 'application/json'});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url; a.download = 'template_report_' + new Date().toISOString().slice(0,10) + '.json';
            a.click(); URL.revokeObjectURL(url);
            showToast('报告已导出');
        }

        function refreshRagStats() {
            fetch('/rag/stats')
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        const docsEl = $('ragStatDocs');
                        const chunksEl = $('ragStatChunks');
                        const charsEl = $('ragStatChars');
                        const vectorsEl = document.getElementById('ragStatVectors');
                        if (docsEl) docsEl.textContent = data.stats.docs || 0;
                        if (chunksEl) chunksEl.textContent = data.stats.chunks || 0;
                        if (charsEl) charsEl.textContent = data.stats.chars || 0;
                        if (vectorsEl) vectorsEl.textContent = data.stats.vectors || 0;
                    }
                });
        }

        function openBatchImportModal() {
            const modal = createModal('batchImportModal', 'Batch Import', '', {maxWidth: '500px'});
            modal.querySelector('.modal-body').innerHTML =
            modal.innerHTML = `
                <div class="modal-content" style="max-width:500px;">
                    <div class="modal-header">
                        <h3>📤 批量导入文档</h3>
                        <button class="modal-close" onclick="closeModal('batchImportModal')">×</button>
                    </div>
                    <div class="modal-body">
                        <div style="margin-bottom:15px;">
                            <label style="font-size:12px;display:block;margin-bottom:5px;">选择文件（支持多选）</label>
                            <input type="file" id="batchFiles" multiple accept=".txt,.md,.pdf,.docx,.html,.json,.csv" style="width:100%;">
                        </div>
                        <div style="margin-bottom:15px;">
                            <label style="font-size:12px;display:block;margin-bottom:5px;">目标分类</label>
                            <select class="project-input" id="batchCategory" style="width:100%;">
                                <option value="doc">📄 文档</option>
                                <option value="code">💻 代码</option>
                                <option value="data">📊 数据</option>
                                <option value="web">🌐 网页</option>
                                <option value="text">📝 文本</option>
                            </select>
                        </div>
                        <div style="display:flex;gap:10px;justify-content:flex-end;">
                            <button class="project-mini-btn" onclick="closeModal('batchImportModal')">取消</button>
                            <button class="project-mini-btn" style="background:var(--primary);color:white;" onclick="executeBatchImport()">导入</button>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }

        function executeBatchImport() {
            showToast('正在批量导入...');
            closeModal('batchImportModal');
        }

        function openUrlImportModal() {
            const modal = createModal('urlImportModal', 'URL Import', '', {maxWidth: '500px'});
            modal.querySelector('.modal-body').innerHTML =
            modal.innerHTML = `
                <div class="modal-content" style="max-width:500px;">
                    <div class="modal-header">
                        <h3>🌐 网页抓取</h3>
                        <button class="modal-close" onclick="closeModal('urlImportModal')">×</button>
                    </div>
                    <div class="modal-body">
                        <div style="margin-bottom:15px;">
                            <label style="font-size:12px;display:block;margin-bottom:5px;">网页 URL</label>
                            <input class="project-input" id="importUrl" placeholder="https://example.com" style="width:100%;">
                        </div>
                        <div style="margin-bottom:15px;">
                            <label style="font-size:12px;display:block;margin-bottom:5px;">抓取深度</label>
                            <select class="project-input" id="crawlDepth" style="width:100%;">
                                <option value="1">仅当前页面</option>
                                <option value="2">2 层深度</option>
                                <option value="3">3 层深度</option>
                            </select>
                        </div>
                        <div style="display:flex;gap:10px;justify-content:flex-end;">
                            <button class="project-mini-btn" onclick="closeModal('urlImportModal')">取消</button>
                            <button class="project-mini-btn" style="background:var(--primary);color:white;" onclick="executeUrlImport()">抓取</button>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }

        function executeUrlImport() {
            const url = document.getElementById('importUrl').value;
            if (!url) {
                showToast('请输入 URL');
                return;
            }
            showToast('正在抓取网页...');
            closeModal('urlImportModal');
        }

        function openGitImportModal() {
            const modal = createModal('gitImportModal', 'Git Import', '', {maxWidth: '500px'});
            modal.querySelector('.modal-body').innerHTML =
            modal.innerHTML = `
                <div class="modal-content" style="max-width:500px;">
                    <div class="modal-header">
                        <h3>📦 Git 仓库导入</h3>
                        <button class="modal-close" onclick="closeModal('gitImportModal')">×</button>
                    </div>
                    <div class="modal-body">
                        <div style="margin-bottom:15px;">
                            <label style="font-size:12px;display:block;margin-bottom:5px;">仓库 URL</label>
                            <input class="project-input" id="gitRepoUrl" placeholder="https://github.com/user/repo" style="width:100%;">
                        </div>
                        <div style="margin-bottom:15px;">
                            <label style="font-size:12px;display:block;margin-bottom:5px;">分支</label>
                            <input class="project-input" id="gitBranch" placeholder="main" value="main" style="width:100%;">
                        </div>
                        <div style="margin-bottom:15px;">
                            <label style="font-size:12px;display:block;margin-bottom:5px;">文件类型</label>
                            <div style="display:flex;gap:10px;flex-wrap:wrap;">
                                <label style="font-size:11px;"><input type="checkbox" checked> .py</label>
                                <label style="font-size:11px;"><input type="checkbox" checked> .js</label>
                                <label style="font-size:11px;"><input type="checkbox" checked> .md</label>
                                <label style="font-size:11px;"><input type="checkbox"> .txt</label>
                            </div>
                        </div>
                        <div style="display:flex;gap:10px;justify-content:flex-end;">
                            <button class="project-mini-btn" onclick="closeModal('gitImportModal')">取消</button>
                            <button class="project-mini-btn" style="background:var(--primary);color:white;" onclick="executeGitImport()">导入</button>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }

        function executeGitImport() {
            const url = document.getElementById('gitRepoUrl').value;
            if (!url) {
                showToast('请输入仓库 URL');
                return;
            }
            showToast('正在导入仓库...');
            closeModal('gitImportModal');
        }

        function openRagSettingsModal() {
            showToast('打开 RAG 设置面板');
        }

        function openKnowledgeGraphModal() {
            const modal = createModal('knowledgeGraphModal', 'Knowledge Graph', '', {maxWidth: '600px'});
            modal.querySelector('.modal-body').innerHTML =
            modal.innerHTML = `
                <div class="modal-content" style="max-width:800px;">
                    <div class="modal-header">
                        <h3>🧠 知识图谱</h3>
                        <button class="modal-close" onclick="closeModal('knowledgeGraphModal')">×</button>
                    </div>
                    <div class="modal-body" style="height:500px;">
                        <div class="graph-container" id="graphContainer">
                            <div class="graph-placeholder">
                                <div class="graph-visualization">
                                    <div class="node-center">知识库</div>
                                    <div class="node-ring">
                                        <div class="node-item">概念</div>
                                        <div class="node-item">实体</div>
                                        <div class="node-item">关系</div>
                                        <div class="node-item">属性</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }

        function buildKnowledgeGraph() {
            showToast('正在构建知识图谱...');
            fetch('/rag/build-graph', { method: 'POST' })
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        document.getElementById('graphNodes').textContent = data.nodes || '--';
                        document.getElementById('graphEdges').textContent = data.edges || '--';
                        showToast('知识图谱构建完成');
                    }
                });
        }

        function loadRagAnalysis() {
            const range = document.getElementById('ragAnalysisRange')?.value || '7d';
            fetch('/rag/analysis?range=' + range)
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        document.getElementById('ragQueryCount').textContent = data.analysis.queries || '--';
                        document.getElementById('ragHitRate').textContent = data.analysis.hit_rate || '--';
                        document.getElementById('ragLatency').textContent = data.analysis.latency || '--';
                        document.getElementById('ragTopDoc').textContent = data.analysis.top_doc || '--';
                    }
                });
        }

        function exportRagReport() {
            showToast('正在导出 RAG 报告...');
        }

        function openVectorSettingsModal() {
            showToast('打开向量化设置面板');
        }
        
        function usePromptTemplate(templateId) {
            const item = getAllTemplates().find(x => x.id === templateId);
            if (!item) return;
            PROMPT_USAGE[templateId] = (PROMPT_USAGE[templateId] || 0) + 1;
            savePromptUsage();
            usePrompt(item.prompt, item.template || null);
        }
        
        function usePrompt(prompt, templateId = null) {
            try {
                const mainInput = $('mainInput');
                if (mainInput) { mainInput.value = prompt; }
                currentStructuredTemplate = templateId;
                if (typeof updateCharCount === 'function') updateCharCount();
            } catch(e) { console.error('usePrompt set value error:', e); }
            try {
                const chatsTab = document.querySelector('.sidebar-tab[onclick*="chats"]');
                if (chatsTab) switchTab('chats', chatsTab);
                setTimeout(function() {
                    var mi = document.getElementById('mainInput');
                    if (mi) { mi.focus(); }
                }, 100);
            } catch(e) { console.error('usePrompt switchTab error:', e); }
            showToast(templateId ? '已应用结构化模板' : '已填入模板');
        }
        
        function refreshSecurityStatus() {
            fetch('/security/status').then(r => r.json()).then(data => {
                if (!data.success) return;
                const s = data.status;
                const cards = document.getElementById('securityStatusCards');
                if (cards) {
                    const items = [
                        {label: '访问认证', value: s.auth_enabled ? '已启用' : '未启用', icon: '🔐', color: s.auth_enabled ? '#10b981' : '#ef4444'},
                        {label: '速率限制', value: s.rate_limit_active ? '已启用' : '未启用', icon: '⏱️', color: s.rate_limit_active ? '#10b981' : '#ef4444'},
                        {label: 'IP控制', value: s.ip_whitelist_mode === 'whitelist' ? '白名单' : '开放', icon: '🌐', color: s.ip_whitelist_mode === 'whitelist' ? '#10b981' : '#f59e0b'},
                        {label: '代码沙箱', value: s.code_sandbox ? '已启用' : '未启用', icon: '💻', color: s.code_sandbox ? '#10b981' : '#ef4444'},
                        {label: '审计日志', value: (s.audit_events_count || 0) + '条', icon: '📋', color: '#667eea'},
                        {label: '安全警告', value: (s.recent_warnings || 0) + '条', icon: '⚠️', color: s.recent_warnings > 0 ? '#f59e0b' : '#10b981'}
                    ];
                    cards.innerHTML = items.map(i => `<div class="ops-kpi-card" style="background:linear-gradient(135deg,${i.color}18,${i.color}08);border-color:${i.color}33;"><div style="font-size:20px;">${i.icon}</div><div style="font-size:11px;font-weight:600;color:${i.color};">${i.value}</div><div style="font-size:10px;color:var(--text-muted);">${i.label}</div></div>`).join('');
                }
                const grid = document.getElementById('securityShieldGrid');
                if (grid) {
                    const shields = [
                        {name: '访问认证', icon: '🔐', on: s.auth_enabled, desc: s.auth_enabled ? '密码保护，公网访问安全' : '未启用，任何人都可访问'},
                        {name: 'XSS防护', icon: '🔒', on: s.xss_protection, desc: '检测并阻止跨站脚本攻击'},
                        {name: 'SSRF防护', icon: '🌐', on: s.ssrf_protection, desc: '阻止对内网地址的请求'},
                        {name: '代码沙箱', icon: '💻', on: s.code_sandbox, desc: '限制代码执行权限和危险操作'},
                        {name: 'API Key脱敏', icon: '🔑', on: s.api_key_masking, desc: 'GET接口返回脱敏后的Key'},
                        {name: '速率限制', icon: '⏱️', on: s.rate_limit_active, desc: '防止暴力请求和DDoS攻击'},
                        {name: '输入验证', icon: '✅', on: s.input_validation, desc: '检测SQL注入和XSS攻击向量'},
                        {name: 'CSRF防护', icon: '🛡️', on: s.csrf_protection, desc: '防止跨站请求伪造攻击'},
                        {name: '审计日志', icon: '📋', on: s.audit_logging, desc: '记录所有安全相关事件'},
                        {name: '安全Session', icon: '🔐', on: s.session_secure, desc: 'HttpOnly + SameSite Cookie'},
                        {name: 'IP白名单', icon: '🌐', on: s.ip_whitelist_mode === 'whitelist', desc: s.ip_whitelist_mode === 'whitelist' ? `白名单模式，${s.ip_whitelist_count}个IP` : '开放模式，所有IP可访问'},
                        {name: '数据加密', icon: '🗝️', on: s.encryption_version >= 2, desc: s.encryption_version >= 2 ? 'AES级别CTR流加密+HMAC认证' : '基础HMAC完整性校验'}
                    ];
                    grid.innerHTML = shields.map(sh => `<div style="background:${sh.on ? 'rgba(16,185,129,0.06)' : 'rgba(239,68,68,0.06)'};border:1px solid ${sh.on ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)'};border-radius:8px;padding:8px 10px;display:flex;align-items:center;gap:8px;">
                        <span style="font-size:16px;">${sh.icon}</span>
                        <div style="flex:1;"><div style="font-size:11px;font-weight:600;color:var(--text-primary);">${sh.name} <span style="font-size:9px;color:${sh.on ? '#10b981' : '#ef4444'};">${sh.on ? '✅' : '❌'}</span></div><div style="font-size:9px;color:var(--text-muted);">${sh.desc}</div></div>
                    </div>`).join('');
                }
                loadSecurityAudit();
                loadAuthStatus();
                loadIpWhitelist();
            });
        }

        function loadSecurityAudit() {
            const filter = document.getElementById('securityAuditFilter')?.value || '';
            fetch('/security/audit' + (filter ? '?severity=' + filter : '')).then(r => r.json()).then(data => {
                if (!data.success) return;
                const list = document.getElementById('securityAuditList');
                if (!list) return;
                if (!data.events.length) {
                    list.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:20px;">暂无安全审计日志</div>';
                    return;
                }
                const severityColors = {critical: '#ef4444', warning: '#f59e0b', info: '#667eea'};
                const severityLabels = {critical: '严重', warning: '警告', info: '信息'};
                list.innerHTML = data.events.slice().reverse().map(e => `<div style="padding:8px 10px;border-left:3px solid ${severityColors[e.severity] || '#667eea'};background:var(--bg-secondary);border-radius:0 8px 8px 0;margin-bottom:6px;">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <span style="font-size:11px;font-weight:600;color:${severityColors[e.severity] || '#667eea'};">${severityLabels[e.severity] || e.severity} · ${e.type}</span>
                        <span style="font-size:10px;color:var(--text-muted);">${e.timestamp || ''}</span>
                    </div>
                    <div style="font-size:11px;color:var(--text-secondary);margin-top:4px;">${escapeHtml(e.detail || '')}</div>
                    <div style="font-size:9px;color:var(--text-muted);margin-top:2px;">IP: ${e.ip || 'unknown'}</div>
                </div>`).join('');
            });
        }

        function clearSecurityAudit() {
            fetch('/security/audit/clear', {method: 'POST'}).then(r => r.json()).then(data => {
                if (data.success) { loadSecurityAudit(); showToast('审计日志已清空'); }
            });
        }

        function runSecurityScan() {
            fetch('/dependencies/security-check').then(r => r.json()).then(data => {
                const list = document.getElementById('securityVulnList');
                if (!list) return;
                if (!data.vulnerabilities || !data.vulnerabilities.length) {
                    list.innerHTML = '<div style="text-align:center;color:#10b981;padding:20px;font-size:13px;">✅ 未发现安全漏洞</div>';
                    return;
                }
                const sevColors = {high: '#ef4444', medium: '#f59e0b', low: '#667eea'};
                list.innerHTML = data.vulnerabilities.map(v => `<div style="padding:8px 10px;border-left:3px solid ${sevColors[v.severity] || '#667eea'};background:var(--bg-secondary);border-radius:0 8px 8px 0;">
                    <div style="font-size:11px;font-weight:600;color:${sevColors[v.severity] || '#667eea'};">${v.severity?.toUpperCase() || 'UNKNOWN'} · ${v.type || ''}</div>
                    <div style="font-size:11px;color:var(--text-secondary);margin-top:4px;">${escapeHtml(v.message || '')}</div>
                </div>`).join('');
            });
        }

        function loadAuthStatus() {
            fetch('/auth/setup').then(r => r.json()).then(data => {
                const panel = document.getElementById('authManagementPanel');
                if (!panel) return;
                const enabled = data.enabled;
                const hasPwd = data.has_password;
                panel.innerHTML = `
                    <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;padding:10px;background:${enabled ? 'rgba(16,185,129,0.08)' : 'rgba(239,68,68,0.08)'};border:1px solid ${enabled ? 'rgba(16,185,129,0.2)' : 'rgba(239,68,68,0.2)'};border-radius:10px;">
                        <span style="font-size:24px;">${enabled ? '🛡️' : '⚠️'}</span>
                        <div style="flex:1;">
                            <div style="font-size:13px;font-weight:600;color:${enabled ? '#10b981' : '#ef4444'};">${enabled ? '访问认证已启用' : '访问认证未启用'}</div>
                            <div style="font-size:11px;color:var(--text-muted);">${enabled ? '所有访问需要密码验证，公网访问安全' : '任何人都可访问，公网环境有泄露风险'}</div>
                        </div>
                        <button class="project-mini-btn" style="background:${enabled ? '#ef4444' : '#10b981'};color:#fff;border:none;" onclick="${enabled ? 'disableAuth()' : 'showEnableAuthDialog()'}">${enabled ? '禁用' : '启用'}</button>
                    </div>
                    ${enabled ? `
                    <div style="margin-bottom:10px;">
                        <button class="project-mini-btn" onclick="showChangePasswordDialog()" style="width:100%;background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;border:none;padding:8px;">🔑 修改访问密码</button>
                    </div>
                    <div style="margin-bottom:10px;">
                        <button class="project-mini-btn" onclick="logoutAllDevices()" style="width:100%;background:#f59e0b;color:#fff;border:none;padding:8px;">🚪 踢出所有其他设备</button>
                    </div>
                    ` : ''}
                    <div style="font-size:10px;color:var(--text-muted);padding:6px 0;border-top:1px solid var(--border-color);">
                        💡 启用认证后，从公网访问需要输入密码。API调用需在Header中携带 <code style="background:var(--bg-secondary);padding:1px 4px;border-radius:3px;">Authorization: Bearer &lt;token&gt;</code>
                    </div>
                `;
            });
        }

        function showEnableAuthDialog() {
            const pwd = prompt('设置访问密码（至少4位）：');
            if (!pwd || pwd.length < 4) { if (pwd) showToast('密码至少4位'); return; }
            fetch('/auth/setup', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({action: 'enable', password: pwd})
            }).then(r => r.json()).then(data => {
                if (data.success) { showToast('认证已启用，请牢记密码'); loadAuthStatus(); refreshSecurityStatus(); }
                else showToast(data.error || '操作失败');
            });
        }

        function disableAuth() {
            if (!confirm('确定要禁用访问认证吗？公网环境下可能导致数据泄露！')) return;
            fetch('/auth/setup', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({action: 'disable'})
            }).then(r => r.json()).then(data => {
                if (data.success) { showToast('认证已禁用'); loadAuthStatus(); refreshSecurityStatus(); }
                else showToast(data.error || '操作失败');
            });
        }

        function showChangePasswordDialog() {
            const oldPwd = prompt('输入当前密码：');
            if (!oldPwd) return;
            const newPwd = prompt('输入新密码（至少4位）：');
            if (!newPwd || newPwd.length < 4) { if (newPwd) showToast('密码至少4位'); return; }
            fetch('/auth/setup', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({action: 'change_password', old_password: oldPwd, new_password: newPwd})
            }).then(r => r.json()).then(data => {
                if (data.success) { showToast('密码已修改，需重新登录'); loadAuthStatus(); }
                else showToast(data.error || '修改失败');
            });
        }

        function logoutAllDevices() {
            if (!confirm('将踢出所有其他设备（当前设备不受影响），确定？')) return;
            fetch('/auth/logout-all', {method: 'POST'}).then(r => r.json()).then(data => {
                if (data.success) showToast('已踢出所有其他设备');
                else showToast(data.error || '操作失败');
            });
        }

        function loadIpWhitelist() {
            fetch('/security/ip-whitelist').then(r => r.json()).then(data => {
                const panel = document.getElementById('ipWhitelistPanel');
                if (!panel) return;
                const wl = data.whitelist || [];
                const mode = data.mode || 'open';
                panel.innerHTML = `
                    <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;padding:8px;background:${mode === 'whitelist' ? 'rgba(16,185,129,0.08)' : 'rgba(239,68,68,0.08)'};border:1px solid ${mode === 'whitelist' ? 'rgba(16,185,129,0.2)' : 'rgba(239,68,68,0.2)'};border-radius:10px;">
                        <span style="font-size:20px;">${mode === 'whitelist' ? '✅' : '🌐'}</span>
                        <div style="flex:1;">
                            <div style="font-size:12px;font-weight:600;color:${mode === 'whitelist' ? '#10b981' : '#f59e0b'};">${mode === 'whitelist' ? '白名单模式' : '开放模式'}</div>
                            <div style="font-size:10px;color:var(--text-muted);">${mode === 'whitelist' ? '仅白名单IP可访问' : '所有IP均可访问'}</div>
                        </div>
                        <button class="project-mini-btn" style="background:${mode === 'whitelist' ? '#ef4444' : '#10b981'};color:#fff;border:none;" onclick="toggleIpMode()">${mode === 'whitelist' ? '切换开放' : '切换白名单'}</button>
                    </div>
                    <div style="display:flex;gap:6px;margin-bottom:8px;">
                        <input class="project-input" id="newIpInput" placeholder="输入IP地址 (如 192.168.1.100)" style="flex:1;">
                        <button class="project-mini-btn" onclick="addIpToWhitelist()" style="background:#667eea;color:#fff;border:none;">➕ 添加</button>
                    </div>
                    <div style="font-size:10px;color:var(--text-muted);margin-bottom:6px;">当前IP: <code style="background:var(--bg-secondary);padding:1px 4px;border-radius:3px;">${data.current_ip || 'unknown'}</code></div>
                    <div style="max-height:150px;overflow-y:auto;display:flex;flex-direction:column;gap:4px;">
                        ${wl.length ? wl.map(ip => `<div style="display:flex;align-items:center;justify-content:space-between;padding:6px 8px;background:var(--bg-secondary);border-radius:6px;">
                            <span style="font-size:11px;font-family:monospace;color:var(--text-primary);">${escapeHtml(ip)}</span>
                            <button style="background:none;border:none;color:#ef4444;cursor:pointer;font-size:12px;" onclick="removeIpFromWhitelist('${escapeHtml(ip)}')">✕</button>
                        </div>`).join('') : '<div style="text-align:center;color:var(--text-muted);font-size:11px;padding:10px;">白名单为空</div>'}
                    </div>
                `;
            });
        }

        function toggleIpMode() {
            fetch('/security/ip-whitelist/mode', {method: 'POST'}).then(r => r.json()).then(data => {
                if (data.success) { loadIpWhitelist(); showToast(data.mode === 'whitelist' ? '已切换为白名单模式' : '已切换为开放模式'); }
                else showToast(data.error || '操作失败');
            });
        }

        function addIpToWhitelist() {
            const ip = document.getElementById('newIpInput')?.value?.trim();
            if (!ip) { showToast('请输入IP地址'); return; }
            fetch('/security/ip-whitelist', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ip: ip})
            }).then(r => r.json()).then(data => {
                if (data.success) { loadIpWhitelist(); showToast('IP已添加'); }
                else showToast(data.error || '添加失败');
            });
        }

        function removeIpFromWhitelist(ip) {
            fetch('/security/ip-whitelist', {
                method: 'DELETE',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ip: ip})
            }).then(r => r.json()).then(data => {
                if (data.success) { loadIpWhitelist(); showToast('IP已移除'); }
                else showToast(data.error || '移除失败');
            });
        }

        function loadProjectConfig() {
            fetch('/project/config').then(r => r.json()).then(data => {
                if (!data.success) return;
                const c = data.config;
                document.getElementById('projectConfigName').value = c.name || '';
                document.getElementById('projectConfigDesc').value = c.description || '';
                document.getElementById('projectConfigTags').value = (c.tags || []).join(', ');
                document.getElementById('projectConfigVersion').value = c.version || '';
                document.getElementById('projectConfigOwner').value = c.owner || '';
                refreshProjectStats();
            });
        }

        function saveProjectConfig() {
            const config = {
                name: document.getElementById('projectConfigName')?.value || '',
                description: document.getElementById('projectConfigDesc')?.value || '',
                tags: (document.getElementById('projectConfigTags')?.value || '').split(',').map(t => t.trim()).filter(Boolean),
                version: document.getElementById('projectConfigVersion')?.value || '',
                owner: document.getElementById('projectConfigOwner')?.value || ''
            };
            fetch('/project/config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(config)
            }).then(r => r.json()).then(data => {
                if (data.success) showToast('项目配置已保存');
                else showToast(data.error || '保存失败');
            });
        }

        function refreshProjectStats() {
            fetch('/project/stats').then(r => r.json()).then(data => {
                if (!data.success) return;
                const s = data.stats;
                const panel = document.getElementById('projectStatsPanel');
                if (!panel) return;
                const bars = [
                    {label: '任务完成率', value: s.task_done_rate || 0, max: 100, color: '#10b981', suffix: '%'},
                    {label: '里程碑进度', value: s.milestone_progress || 0, max: 100, color: '#667eea', suffix: '%'},
                    {label: '风险缓解率', value: s.risk_mitigated_rate || 0, max: 100, color: '#f59e0b', suffix: '%'},
                    {label: '运营活动完成率', value: s.campaign_done_rate || 0, max: 100, color: '#ec4899', suffix: '%'},
                    {label: '发布成功率', value: s.release_success_rate || 0, max: 100, color: '#8b5cf6', suffix: '%'}
                ];
                panel.innerHTML = bars.map(b => `<div>
                    <div style="display:flex;justify-content:space-between;font-size:10px;margin-bottom:3px;">
                        <span style="color:var(--text-secondary);">${b.label}</span>
                        <span style="color:${b.color};font-weight:600;">${b.value}${b.suffix}</span>
                    </div>
                    <div style="height:6px;background:var(--bg-secondary);border-radius:3px;overflow:hidden;">
                        <div style="height:100%;width:${Math.min(b.value, 100)}%;background:${b.color};border-radius:3px;transition:width 0.5s;"></div>
                    </div>
                </div>`).join('') + `<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-top:8px;">
                    <div style="text-align:center;padding:6px;background:var(--bg-secondary);border-radius:6px;"><div style="font-size:14px;font-weight:700;color:var(--text-primary);">${s.total_artifacts || 0}</div><div style="font-size:9px;color:var(--text-muted);">产物</div></div>
                    <div style="text-align:center;padding:6px;background:var(--bg-secondary);border-radius:6px;"><div style="font-size:14px;font-weight:700;color:var(--text-primary);">${s.total_tasks || 0}</div><div style="font-size:9px;color:var(--text-muted);">任务</div></div>
                    <div style="text-align:center;padding:6px;background:var(--bg-secondary);border-radius:6px;"><div style="font-size:14px;font-weight:700;color:var(--text-primary);">${s.total_activities || 0}</div><div style="font-size:9px;color:var(--text-muted);">活动</div></div>
                </div>`;
            });
        }

        function exportProjectData() {
            fetch('/project/export').then(r => r.json()).then(data => {
                if (!data.success) { showToast(data.error || '导出失败'); return; }
                const blob = new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'});
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url; a.download = `kaguya_project_${new Date().toISOString().slice(0,10)}.json`;
                a.click(); URL.revokeObjectURL(url);
                showToast('项目数据已导出');
            });
        }

        function importProjectData(event) {
            const file = event.target.files[0];
            if (!file) return;
            const reader = new FileReader();
            reader.onload = function(e) {
                try {
                    const data = JSON.parse(e.target.result);
                    fetch('/project/import', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(data)
                    }).then(r => r.json()).then(res => {
                        if (res.success) { showToast(`导入成功: ${res.imported || 0}条数据`); loadProjectCenter(); }
                        else showToast(res.error || '导入失败');
                    });
                } catch(err) { showToast('文件格式无效'); }
            };
            reader.readAsText(file);
            event.target.value = '';
        }

        function exportChatHistory() {
            fetch('/chats/export').then(r => r.json()).then(data => {
                if (!data.success) { showToast(data.error || '导出失败'); return; }
                const blob = new Blob([JSON.stringify(data.chats || [], null, 2)], {type: 'application/json'});
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url; a.download = `kaguya_chats_${new Date().toISOString().slice(0,10)}.json`;
                a.click(); URL.revokeObjectURL(url);
                showToast('对话记录已导出');
            });
        }

        function clearAllProjectData() {
            if (!confirm('确定要清空所有项目数据吗？此操作不可恢复！')) return;
            fetch('/project/clear', {method: 'POST'}).then(r => r.json()).then(data => {
                if (data.success) { showToast('项目数据已清空'); loadProjectCenter(); }
                else showToast(data.error || '清空失败');
            });
        }

