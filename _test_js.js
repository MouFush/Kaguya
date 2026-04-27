
const isElectron = typeof window !== 'undefined' && typeof window.kaguyaDesktop !== 'undefined';
const isDesktopMode = isElectron || (typeof window !== 'undefined' && window.location && window.location.search && window.location.search.includes('desktop=1'));
if (isElectron) {
    console.log('[Kaguya] Running in Electron desktop mode');
    console.log('[Kaguya] Platform:', window.kaguyaDesktop.platform);
    console.log('[Kaguya] Version:', window.kaguyaDesktop.version);
}
window.onerror = function(msg, url, line, col, error) {
    console.error('[Kaguya IDE] Uncaught error:', msg, 'at', url, 'line', line, ':', col, error ? error.stack : '');
    return false;
};
window.addEventListener('unhandledrejection', function(e) {
    console.error('[Kaguya IDE] Unhandled promise rejection:', e.reason);
});
function showToast(msg, type) {
    const t = document.getElementById('toast');
    if (!t) { console.log('[Toast]', msg); return; }
    t.textContent = msg;
    t.className = 'toast show' + (type ? ' toast-' + type : '');
    clearTimeout(t._timer);
    t._timer = setTimeout(() => { t.className = 'toast'; }, 2500);
}
let currentLang=localStorage.getItem('kaguya_ide_lang')||'zh';
const I18N={
  zh:{
    explorer:'资源管理器',chat:'聊天',files:'文件',selectFile:'📁 选择文件',selectFolder:'📂 选择文件夹',pathImport:'📋 路径导入',importEnv:'🐍 导入环境',browseHost:'🖥 浏览主机',
    welcomeTitle:'辉夜 Agent IDE',welcomeSub:'智能体编程助手',sendMsg:'发送消息',newLine:'换行',toggleSidebar:'切换侧边栏',toggleTerminal:'切换终端',compileRun:'编译运行',slashCmd:'斜杠命令',
    terminal:'终端',command:'命令...',agent:'Agent',modeChat:'聊天',modeAgent:'Agent',modeRun:'运行',
    noFile:'无文件',ready:'就绪',thinking:'思考中',compiling:'编译中',executing:'执行中',
    msgPlaceholder:'发送消息... (/ 查看命令)',noFileCompile:'没有打开的文件无法编译',importingPaths:'正在导入路径...',importSuccess:'导入成功',importFailed:'导入失败',
    uploadSuccess:'上传成功',uploadFailed:'上传失败',noFilesSelected:'未选择文件',uploadingFiles:'正在上传文件...',
    langToggle:'中/EN',backToChat:'← 聊天',statusTokens:'令牌',statusCost:'费用',
    slashHelp:'查看可用命令',slashClear:'清除对话历史',slashCompact:'压缩对话上下文',slashCost:'查看令牌用量和费用',slashMemory:'查看/编辑记忆文件',slashModel:'查看当前模型信息',slashPermissions:'查看权限设置',slashStatus:'查看Agent状态',slashUndo:'撤销上次文件更改',slashDiff:'查看待处理的文件更改',
    allow:'允许',deny:'拒绝',allowTool:'是否允许',alwaysAllow:'始终允许',alwaysDeny:'始终拒绝',
    permPanel:'权限管理',sandboxDirs:'沙箱目录',addSandboxDir:'添加目录',removeSandboxDir:'移除',
    permRules:'权限规则',dangerousCmds:'危险命令',sandboxMode:'沙箱模式',permDenied:'权限被拒绝',permGranted:'权限已授予',
    auditLog:'审计日志',auditStats:'审计统计',totalOps:'总操作数',allowedOps:'允许',deniedOps:'拒绝',
    noSandboxDirs:'No sandbox dirs configured - agent can operate anywhere',permRequest:'Permission Request',permReason:'Reason',
    permDetail:'Detail',waitingApproval:'Waiting for approval...',permTimeout:'Approval timeout',closePanel:'Close',
    apiNotConnected:'API Not Connected',apiRequiresModel:'Agent IDE requires external AI model. Local Ollama models are not supported.',apiConfig:'Please configure an external model in API Center',
    browseDir:'Browse Directory',enterPath:'Directory path (leave empty for home):',enterPaths:'Enter file/folder paths (comma separated):\nExample: C:\\Users\\xxx\\project, C:\\Users\\xxx\\data.csv',
    editName:'输入你的名字：',envImported:'环境已导入',envImportFailed:'环境导入失败',
    tasks:'任务',newTaskPlaceholder:'新任务...',taskPending:'待处理',taskInProgress:'进行中',taskDone:'已完成',taskFailed:'失败',
    chats:'对话',newChat:'新对话',files:'文件',acceptChange:'接受',rejectChange:'拒绝',fileChanged:'文件已更改',additions:'行新增',deletions:'行删除',
    openProject:'打开项目',enterProjectPath:'输入项目目录路径：',collapseAll:'折叠全部',expandAll:'展开全部',thinking:'思考中',
  },
  en:{
    explorer:'Explorer',chat:'Chat',files:'Files',selectFile:'📁 Select Files',selectFolder:'📂 Select Folder',pathImport:'📋 Path Import',importEnv:'🐍 Import Env',browseHost:'🖥 Browse Host',
    welcomeTitle:'Kaguya Agent IDE',welcomeSub:'AI Agent Programming Assistant',sendMsg:'Send message',newLine:'New line',toggleSidebar:'Toggle sidebar',toggleTerminal:'Toggle terminal',compileRun:'Compile & Run',slashCmd:'Slash command',
    terminal:'Terminal',command:'Command...',agent:'Agent',modeChat:'Chat',modeAgent:'Agent',modeRun:'Run',
    noFile:'No file',ready:'Ready',thinking:'Thinking',compiling:'Compiling',executing:'Executing',
    msgPlaceholder:'Message agent... (/ for commands)',noFileCompile:'No file open to compile',importingPaths:'Importing paths...',importSuccess:'Imported',importFailed:'Import failed',
    uploadSuccess:'Uploaded',uploadFailed:'Upload failed',noFilesSelected:'No files selected',uploadingFiles:'Uploading files...',
    langToggle:'中/EN',backToChat:'← Chat',statusTokens:'tokens',statusCost:'cost',
    slashHelp:'Show available commands',slashClear:'Clear conversation history',slashCompact:'Compact conversation context',slashCost:'Show token usage and cost',slashMemory:'View/edit KAGUYA.md memory',slashModel:'Show current model info',slashPermissions:'Show permission settings',slashStatus:'Show agent status',slashUndo:'Undo last file change',slashDiff:'Show pending file changes',
    allow:'Allow',deny:'Deny',allowTool:'Allow',alwaysAllow:'Always Allow',alwaysDeny:'Always Deny',
    permPanel:'Permissions',sandboxDirs:'Sandbox Dirs',addSandboxDir:'Add Dir',removeSandboxDir:'Remove',
    permRules:'Permission Rules',dangerousCmds:'Dangerous Commands',sandboxMode:'Sandbox Mode',permDenied:'Permission Denied',permGranted:'Permission Granted',
    auditLog:'Audit Log',auditStats:'Audit Stats',totalOps:'Total Ops',allowedOps:'Allowed',deniedOps:'Denied',
    noSandboxDirs:'No sandbox dirs configured (agent can operate anywhere)',permRequest:'Permission Request',permReason:'Reason',
    permDetail:'Detail',waitingApproval:'Waiting for approval...',permTimeout:'Approval timeout',closePanel:'Close',
    apiNotConnected:'API Not Connected',apiRequiresModel:'Agent IDE requires an external AI model. Local Ollama models are not supported.',apiConfig:'Please configure an external model in the API hub',
    browseDir:'Browse Directory',enterPath:'Directory path (empty for home):',enterPaths:'Enter file/folder paths (comma-separated):\ne.g. C:\\Users\\xxx\\project, C:\\Users\\xxx\\data.csv',
    editName:'Enter your name:',envImported:'Env imported',envImportFailed:'Env import failed',
    tasks:'Tasks',newTaskPlaceholder:'New task...',taskPending:'Pending',taskInProgress:'In Progress',taskDone:'Done',taskFailed:'Failed',
    chats:'Chats',newChat:'New Chat',files:'Files',acceptChange:'Accept',rejectChange:'Reject',fileChanged:'File Changed',additions:'additions',deletions:'deletions',
    openProject:'Open Project',enterProjectPath:'Enter project directory path:',collapseAll:'Collapse All',expandAll:'Expand All',thinking:'Thinking',
  }
};
function t(key){return(I18N[currentLang]||I18N.zh)[key]||key;}
function toggleLang(){currentLang=currentLang==='zh'?'en':'zh';localStorage.setItem('kaguya_ide_lang',currentLang);applyLang();}
function applyLang(){
  document.querySelectorAll('[data-i18n]').forEach(el=>{const k=el.getAttribute('data-i18n');if(t(k)!==k)el.textContent=t(k);});
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el=>{const k=el.getAttribute('data-i18n-placeholder');if(t(k)!==k)el.placeholder=t(k);});
  const ai=document.getElementById('agentInput');if(ai)ai.placeholder=t('msgPlaceholder');
  const ti=document.getElementById('terminalInput');if(ti)ti.placeholder=t('command');
  const ws=document.getElementById('welcomeScreen');
  if(ws){ws.querySelector('h2').textContent=t('welcomeTitle');ws.querySelector('p').textContent=t('welcomeSub');}
  document.getElementById('langToggle').textContent=t('langToggle');
  renderTasks();
}
let currentMode='chat';let openTabs=[];let activeTab=null;let agentHistory=[];let isAgentRunning=false;
let electronTerminalSession=null;
let ideTasks=JSON.parse(localStorage.getItem('kaguya_ide_tasks')||'[]');
let activeTaskId=localStorage.getItem('kaguya_ide_active_task')||'main';
let _termHistory=[];let _termHistIdx=-1;
let _terminalTabs=[{id:0,name:'bash',history:[],histIdx:-1}];let _activeTermTab=0;let _nextTermTabId=1;
let _outputLines=[];let _outputFilter='all';let _outputMaxLines=5000;
let _debugBreakpoints=[];let _debugVariables=[];let _debugCallstack=[];let _debugLogEntries=[];
let _convFilterMode='session';let _msgFoldAllState=false;
if(!ideTasks.length){ideTasks=[{id:'main',name:'Main',status:'done',created:Date.now(),history:[],pendingChanges:[]}];}
function switchSidebarTab(tab){
  document.getElementById('sidebarTabFiles').classList.toggle('active',tab==='files');
  document.getElementById('sidebarTabChats').classList.toggle('active',tab==='chats');
  document.getElementById('sidebarPanelFiles').classList.toggle('active',tab==='files');
  document.getElementById('sidebarPanelChats').classList.toggle('active',tab==='chats');
}
function saveTasks(){
  ideTasks.forEach(function(t2){
    t2.history=t2.history||[];
    if(t2.id===activeTaskId&&agentHistory.length>0){
      t2.history=agentHistory.slice(-50);
    }
  });
  localStorage.setItem('kaguya_ide_tasks',JSON.stringify(ideTasks.map(function(t2){return{id:t2.id,name:t2.name,status:t2.status,created:t2.created,history:t2.history||[]};})));
  localStorage.setItem('kaguya_ide_active_task',activeTaskId||'main');
  renderConvList();
}
function getActiveTask(){return ideTasks.find(function(t2){return t2.id===activeTaskId;})||ideTasks[0];}
function promptAddTask(){const name=prompt(t('newTaskPlaceholder'));if(name&&name.trim()){addTask(name.trim());}}
function addTask(name){const task={id:'t'+Date.now(),name:name,status:'pending',created:Date.now(),history:[],pendingChanges:[]};ideTasks.push(task);activeTaskId=task.id;agentHistory=[];saveTasks();switchSidebarTab('chats');const msgs=document.getElementById('agentMessages');msgs.innerHTML='';msgs.scrollTop=msgs.scrollHeight;}
function removeTask(id){if(id==='main')return;ideTasks=ideTasks.filter(function(t2){return t2.id!==id;});if(activeTaskId===id){activeTaskId='main';agentHistory=[];const msgs=document.getElementById('agentMessages');msgs.innerHTML='';const task=getActiveTask();if(task&&task.history&&task.history.length){task.history.forEach(function(h){const uEl=document.createElement('div');uEl.className='msg user';uEl.textContent=h.user;msgs.appendChild(uEl);const aEl=document.createElement('div');aEl.className='msg assistant';aEl.innerHTML=renderMd(h.assistant);msgs.appendChild(aEl);});}}saveTasks();}
function switchTask(id){if(id===activeTaskId)return;activeTaskId=id;agentHistory=[];const msgs=document.getElementById('agentMessages');msgs.innerHTML='';const task=getActiveTask();if(task&&task.history&&task.history.length){task.history.forEach(function(h){const uEl=document.createElement('div');uEl.className='msg user';uEl.textContent=h.user;msgs.appendChild(uEl);const aEl=document.createElement('div');aEl.className='msg assistant';aEl.innerHTML=renderMd(h.assistant);msgs.appendChild(aEl);agentHistory.push(h);});}msgs.scrollTop=msgs.scrollHeight;saveTasks();switchSidebarTab('chats');}
function updateTaskStatus(id,status){const task=ideTasks.find(function(t2){return t2.id===id;});if(task){task.status=status;saveTasks();}}
function renderConvList(){
  const list=document.getElementById('convList');if(!list)return;list.innerHTML='';
  ideTasks.forEach(function(task){
    const item=document.createElement('div');
    item.className='conv-item'+(task.id===activeTaskId?' active':'');
    const timeStr=new Date(task.created).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'});
    item.innerHTML='<div class="conv-dot '+task.status+'"></div><div class="conv-info"><div class="conv-name">'+esc(task.name.substring(0,20))+'</div><div class="conv-time">'+timeStr+'</div></div>'+(task.id!=='main'?'<span class="conv-del" onclick="event.stopPropagation();removeTask(\''+task.id+'\')">&#x2715;</span>':'');
    item.onclick=function(){switchTask(task.id);};
    list.appendChild(item);
  });
}
function toggleTaskStatus(id){const task=ideTasks.find(function(t2){return t2.id===id;});if(!task)return;const order=['pending','in_progress','done'];const idx=order.indexOf(task.status);task.status=order[(idx+1)%order.length];saveTasks();}
function renderTasks(){renderConvList();}
async function openProjectDir(){
  let projectPath;
  if(isElectron){
    try{
      const result = await window.kaguyaDesktop.dialog.openFolder({title: t('openProject')});
      if(result.canceled || !result.filePaths || !result.filePaths.length) return;
      projectPath = result.filePaths[0];
    }catch(e){termLog('Failed to select folder: '+e.message,'error');return;}
  } else {
    projectPath = prompt(t('enterProjectPath'));
    if(!projectPath||!projectPath.trim())return;
    projectPath = projectPath.trim();
  }
  fetch('/agent/open-project',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:projectPath,device_id:generateDeviceId()})}).then(function(r){return r.json();}).then(function(d){
    if(d.error){termLog('Error: '+d.error,'error');return;}
    currentWorkspace=d.workspace;
    loadFileTree(d.project_path);
    termLog('Project opened: '+d.project_path,'success');
    switchSidebarTab('files');
  }).catch(function(e){termLog('Failed to open project: '+e.message,'error');});
}
function toggleMsgCollapse(el){
  if(el.classList.contains('collapsed')){
    el.classList.remove('collapsed');
    const fade=el.querySelector('.think-fade');if(fade)fade.style.display='none';
    const toggle=el.querySelector('.think-toggle')||el.querySelector('.tool-toggle');
    if(toggle){toggle.textContent='▼';toggle.title='折叠';}
  } else {
    el.classList.add('collapsed');
    const fade=el.querySelector('.think-fade');if(fade)fade.style.display='block';
    const toggle=el.querySelector('.think-toggle')||el.querySelector('.tool-toggle');
    if(toggle){toggle.textContent='▶';toggle.title='展开';}
  }
}
function collapseAllMsgs(){
  document.querySelectorAll('#agentMessages .msg.assistant.thinking, #agentMessages .msg.tool-use, #agentMessages .msg.tool-result').forEach(function(el){
    if(!el.classList.contains('collapsed'))toggleMsgCollapse(el);
  });
}
function expandAllMsgs(){
  document.querySelectorAll('#agentMessages .msg.assistant.thinking, #agentMessages .msg.tool-use, #agentMessages .msg.tool-result').forEach(function(el){
    if(el.classList.contains('collapsed'))toggleMsgCollapse(el);
  });
}
let currentUserId=null;let currentUserName=null;let currentWorkspace=null;
let totalTokensIn=0;let totalTokensOut=0;let totalCost=0;let currentIteration=0;
let pendingPermissions={};
const DANGEROUS=['write_file','edit_file','execute_command','compile','agent_spawn'];
const TOOL_ICONS={'read_file':'R','write_file':'W','edit_file':'E','list_directory':'D','search_files':'S','execute_command':'!','glob':'G','compile':'C','todo_write':'T','enter_plan_mode':'P','exit_plan_mode':'P','web_fetch':'F','web_search':'Q','agent_spawn':'A','task_create':'+','task_update':'^','task_list':'L','brief':'B'};
const SLASH_COMMANDS=[
  {cmd:'/help',desc:'Show available commands'},
  {cmd:'/clear',desc:'Clear conversation history'},
  {cmd:'/compact',desc:'Compact conversation context'},
  {cmd:'/cost',desc:'Show token usage and cost'},
  {cmd:'/memory',desc:'View/edit KAGUYA.md memory'},
  {cmd:'/model',desc:'Show current model info'},
  {cmd:'/permissions',desc:'Show permission settings'},
  {cmd:'/status',desc:'Show agent status'},
  {cmd:'/undo',desc:'Undo last file change'},
  {cmd:'/diff',desc:'Show pending file changes'},
];
function esc(s){const d=document.createElement('div');d.textContent=s;return d.innerHTML;}
function getExternalApiConfig(){try{const cfg=JSON.parse(localStorage.getItem('api_providers')||'{}');for(const pv of Object.keys(cfg)){const c=cfg[pv];if(c&&c.enabled&&c.apiKey)return{enabled:true,apiKey:c.apiKey,apiUrl:c.apiUrl||'',model:c.model||'',provider:pv};}}catch(e){}return null;}
function generateDeviceId(){let stored=localStorage.getItem('kaguya_device_id');if(stored)return stored;const nav=window.navigator;const screen=window.screen;const raw=[nav.userAgent,nav.language,screen.width+'x'+screen.height,screen.colorDepth,new Date().getTimezoneOffset(),nav.hardwareConcurrency||0,nav.platform||''].join('|');let hash=0;for(let i=0;i<raw.length;i++){const c=raw.charCodeAt(i);hash=((hash<<5)-hash)+c;hash|=0;}const id='dev_'+Math.abs(hash).toString(36)+'_'+Date.now().toString(36);localStorage.setItem('kaguya_device_id',id);return id;}
function updateTokenDisplay(){document.getElementById('statusTokens').textContent=totalTokensIn+'+'+totalTokensOut+' tk';document.getElementById('tokenInfo').textContent=totalTokensIn+'+'+totalTokensOut+' tk';const costStr='$'+totalCost.toFixed(4);document.getElementById('statusCost').textContent=costStr;document.getElementById('costInfo').textContent=costStr;}
function estimateTokens(text){return Math.ceil(text.length/4);}
function addCost(inputTokens,outputTokens){totalTokensIn+=inputTokens;totalTokensOut+=outputTokens;const inCost=inputTokens*0.000003;const outCost=outputTokens*0.000015;totalCost+=inCost+outCost;updateTokenDisplay();}
async function identifyDevice(){const deviceId=generateDeviceId();const storedName=localStorage.getItem('kaguya_user_name')||'';try{const r=await fetch('/agent/identify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({device_id:deviceId,device_name:storedName})});const d=await r.json();currentUserId=d.user_id;currentUserName=d.user_name;currentWorkspace=d.workspace;document.getElementById('userName').textContent=currentUserName;document.getElementById('userId').textContent=currentUserId.substring(0,10)+'...';document.getElementById('userAvatar').textContent=currentUserName.charAt(0).toUpperCase();document.getElementById('statusUser').textContent=currentUserName;return true;}catch(e){document.getElementById('userName').textContent='Unknown';return false;}}
function editUserName(){const name=prompt(t('editName'),currentUserName||'');if(name&&name.trim()){currentUserName=name.trim().substring(0,32);localStorage.setItem('kaguya_user_name',currentUserName);fetch('/agent/identify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({device_id:generateDeviceId(),device_name:currentUserName})}).then(r=>r.json()).then(d=>{document.getElementById('userName').textContent=d.user_name;document.getElementById('userAvatar').textContent=d.user_name.charAt(0).toUpperCase();document.getElementById('statusUser').textContent=d.user_name;});}}
function setMode(m){
  currentMode=m;
  document.querySelectorAll('.mode-btn').forEach(b=>b.classList.remove('active'));
  const btnId='mode'+m.charAt(0).toUpperCase()+m.slice(1);
  const btn=document.getElementById(btnId);
  if(btn)btn.classList.add('active');
  const statusEl=document.getElementById('statusMode');
  if(statusEl)statusEl.textContent=m;
  const agentPanel=document.querySelector('.agent-panel');
  const filePanel=document.querySelector('.file-panel');
  const termPanel=document.getElementById('bottomPanel');
  const soloInd=document.getElementById('soloIndicator');
  if(m==='solo'){
    if(agentPanel){agentPanel.style.width='520px';agentPanel.classList.add('solo-active');}
    if(filePanel)filePanel.style.display='flex';
    if(termPanel)termPanel.style.display='flex';
    if(soloInd)soloInd.classList.add('active');
    const modeBadge=document.getElementById('modeBadge');
    if(modeBadge){modeBadge.textContent='SOLO';modeBadge.style.background='linear-gradient(135deg,#f59e0b,#ef4444)';modeBadge.style.display='inline-block';}
    showToast('Solo Mode: Full autonomy - Agent will execute all operations directly','success');
  } else {
    if(agentPanel){agentPanel.style.width='420px';agentPanel.classList.remove('solo-active');}
    if(soloInd)soloInd.classList.remove('active');
    const modeBadge=document.getElementById('modeBadge');
    if(modeBadge){modeBadge.textContent=m.toUpperCase();modeBadge.style.background=m==='agent'?'var(--accent)':'var(--bg-2)';modeBadge.style.display=m==='agent'?'inline-block':'none';}
  }
}
function handleInputKey(e){if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();const v=document.getElementById('agentInput').value.trim();if(v.startsWith('/')){executeSlashCommand(v);document.getElementById('agentInput').value='';hideSlashMenu();}else{sendAgentMsg();}}else if(e.key==='Tab'){e.preventDefault();const menu=document.getElementById('slashMenu');if(menu.classList.contains('visible')){const active=menu.querySelector('.active')||menu.querySelector('.slash-item');if(active){document.getElementById('agentInput').value=active.querySelector('.cmd').textContent+' ';hideSlashMenu();}}}}
function handleInputChange(el){const v=el.value;if(v.startsWith('/')){showSlashMenu(v.substring(1));}else{hideSlashMenu();}el.style.height='auto';el.style.height=Math.min(el.scrollHeight,120)+'px';}
function showSlashMenu(filter){const menu=document.getElementById('slashMenu');const filtered=SLASH_COMMANDS.filter(c=>c.cmd.substring(1).startsWith(filter.toLowerCase()));if(!filtered.length){hideSlashMenu();return;}menu.innerHTML=filtered.map(function(c,i){return '<div class="slash-item'+(i===0?' active':'')+'" onclick="document.getElementById(\'agentInput\').value=\''+c.cmd+' \';hideSlashMenu();"><span class="cmd">'+c.cmd+'</span><span class="desc">'+c.desc+'</span></div>';}).join('');menu.classList.add('visible');}
function hideSlashMenu(){document.getElementById('slashMenu').classList.remove('visible');}
function executeSlashCommand(cmd){const msgs=document.getElementById('agentMessages');const el=document.createElement('div');el.className='msg user';el.textContent=cmd;msgs.appendChild(el);switch(cmd.trim()){case'/help':const helpEl=document.createElement('div');helpEl.className='msg assistant';helpEl.innerHTML=SLASH_COMMANDS.map(function(c){return '<code>'+c.cmd+'</code> '+c.desc;}).join('<br>');msgs.appendChild(helpEl);break;case'/clear':agentHistory=[];msgs.innerHTML='<div class="msg assistant">Conversation cleared.</div>';break;case'/compact':agentHistory=agentHistory.slice(-2);const compactEl=document.createElement('div');compactEl.className='msg assistant';compactEl.textContent='Context compacted. Kept last 2 exchanges.';msgs.appendChild(compactEl);break;case'/cost':const costEl=document.createElement('div');costEl.className='msg assistant';costEl.innerHTML='Token usage: <code>'+totalTokensIn+'+'+totalTokensOut+'</code><br>Estimated cost: <code>$'+totalCost.toFixed(4)+'</code>';msgs.appendChild(costEl);break;case'/model':const extCfg=getExternalApiConfig();const modelEl=document.createElement('div');modelEl.className='msg assistant';modelEl.innerHTML=extCfg?'Provider: <code>'+esc(extCfg.provider)+'</code><br>Model: <code>'+esc(extCfg.model)+'</code>':'No external API configured. Using local model.';msgs.appendChild(modelEl);break;case'/memory':const memEl=document.createElement('div');memEl.className='msg assistant';memEl.innerHTML='Memory file (KAGUYA.md):<br><pre>Click "Import" to load, or ask the agent to create one.</pre>';msgs.appendChild(memEl);break;case'/status':const statusEl=document.createElement('div');statusEl.className='msg assistant';statusEl.innerHTML='Mode: <code>'+currentMode+'</code><br>Iterations: <code>'+currentIteration+'</code><br>Tokens: <code>'+totalTokensIn+'+'+totalTokensOut+'</code><br>Cost: <code>$'+totalCost.toFixed(4)+'</code><br>History: <code>'+agentHistory.length+' exchanges</code>';msgs.appendChild(statusEl);break;case'/permissions':showPermPanel();const permInfoEl=document.createElement('div');permInfoEl.className='msg assistant';permInfoEl.innerHTML='&#x1F6E1; '+t('permPanel')+' <button onclick="showPermPanel()" style="padding:2px 8px;background:var(--accent);color:#fff;border:none;border-radius:4px;font-size:10px;cursor:pointer;">'+t('permPanel')+'</button>';msgs.appendChild(permInfoEl);break;default:const unknownEl=document.createElement('div');unknownEl.className='msg assistant';unknownEl.textContent='Unknown command. Type /help for available commands.';msgs.appendChild(unknownEl);}msgs.scrollTop=msgs.scrollHeight;}
const FILE_ICONS={py:'🐍',js:'📜',ts:'🔷',jsx:'⚛️',tsx:'⚛️',html:'🌐',css:'🎨',json:'📋',yaml:'⚙️',yml:'⚙️',md:'📝',txt:'📄',sql:'🗃️',sh:'🖥️',bash:'🖥️',rs:'🦀',go:'🐹',java:'☕',rb:'💎',php:'🐘',swift:'🐦',c:'🔧',cpp:'⚙️',h:'📐',toml:'⚙️',ini:'⚙️',cfg:'⚙️',dockerfile:'🐳',gitignore:'🚫'};
function getFileIcon(name,ext){if(FILE_ICONS[ext])return FILE_ICONS[ext];if(name==='Dockerfile')return'🐳';if(name.startsWith('.'))return'🔒';return'📄';}
function formatFileSize(bytes){if(!bytes||bytes===0)return'';if(bytes<1024)return bytes+'B';if(bytes<1024*1024)return(bytes/1024).toFixed(1)+'KB';if(bytes<1024*1024*1024)return(bytes/(1024*1024)).toFixed(1)+'MB';return(bytes/(1024*1024*1024)).toFixed(1)+'GB';}
async function loadFileTree(path){try{const r=await fetch('/agent/file-tree',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:path||undefined,device_id:generateDeviceId()})});const d=await r.json();if(d.error){termLog('Error: '+d.error,'error');return;}if(d.user_name){currentUserName=d.user_name;document.getElementById('userName').textContent=d.user_name;document.getElementById('userAvatar').textContent=d.user_name.charAt(0).toUpperCase();}const tree=document.getElementById('fileTree');tree.innerHTML='<div class="tree-section" data-i18n="files">'+t('files')+'</div>';if(d.path){const up=document.createElement('div');up.className='tree-item';up.innerHTML='<span class="tree-icon dir">📁</span> <span class="tree-name">..</span>';const parentPath=d.path.split(/[\\/]/).slice(0,-1).join('/');up.onclick=()=>{if(currentWorkspace&&parentPath&&parentPath.length>=currentWorkspace.length)loadFileTree(parentPath);};tree.appendChild(up);}d.entries.forEach(e=>{const item=document.createElement('div');item.className='tree-item';item.dataset.path=e.path;var icon=e.is_dir?'📁':getFileIcon(e.name,e.ext);var sizeStr=e.is_dir?'':formatFileSize(e.size);item.innerHTML='<span class="tree-icon '+(e.is_dir?'dir':'file')+'">'+icon+'</span> <span class="tree-name">'+esc(e.name)+'</span>'+(sizeStr?'<span class="tree-size">'+sizeStr+'</span>':'');item.onclick=()=>{if(e.is_dir)loadFileTree(e.path);else openFile(e.path,e.name);};tree.appendChild(item);});}catch(e){termLog('Failed to load file tree: '+e,'error');}}
async function openFile(path,name){try{const r=await fetch('/agent/read-file',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path,device_id:generateDeviceId()})});const d=await r.json();if(d.error){termLog('Error: '+d.error,'error');return;}if(!openTabs.find(tb=>tb.path===path)){openTabs.push({path,name,language:d.language});renderTabs();}activeTab=path;renderTabs();renderCode(d.content,d.language);document.getElementById('statusFile').textContent=name;document.getElementById('statusLang').textContent=d.language;document.querySelectorAll('.tree-item').forEach(i=>i.classList.toggle('active',i.dataset.path===path));}catch(e){termLog('Failed to open file: '+e,'error');}}
function renderTabs(){const bar=document.getElementById('tabsBar');bar.innerHTML='';openTabs.forEach(tb=>{const tab=document.createElement('div');tab.className='tab'+(tb.path===activeTab?' active':'');tab.innerHTML='<span>'+esc(tb.name)+'</span><span class="close" onclick="event.stopPropagation();closeTab(\''+esc(tb.path).replace(/'/g,"\\'")+'\')">&#x2715;</span>';tab.onclick=()=>openFile(tb.path,tb.name);bar.appendChild(tab);});}
function closeTab(path){openTabs=openTabs.filter(tb=>tb.path!==path);if(activeTab===path){activeTab=openTabs.length?openTabs[openTabs.length-1].path:null;if(activeTab)openFile(activeTab,openTabs.find(tb=>tb.path===activeTab).name);else{document.getElementById('codeContent').innerHTML='<div class="welcome-screen" id="welcomeScreen"><div class="welcome-logo">K</div><h2>'+t('welcomeTitle')+'</h2><p>'+t('welcomeSub')+'</p></div>';document.getElementById('statusFile').textContent=t('noFile');document.getElementById('statusLang').textContent='-';}}renderTabs();}
function renderCode(content,lang){const el=document.getElementById('codeContent');let highlighted;try{highlighted=hljs.highlight(content,{language:lang||'plaintext'}).value;}catch(e){highlighted=esc(content);}el.innerHTML='<pre><code class="hljs">'+highlighted+'</code></pre>';}
function termLog(text,cls=''){const body=document.getElementById('terminalBody');const line=document.createElement('div');line.className='line'+(cls?' '+cls:'');if(cls==='html'){line.innerHTML=text;}else{line.textContent=text;}body.appendChild(line);body.scrollTop=body.scrollHeight;var tab=_terminalTabs.find(function(t){return t.id===_activeTermTab;});if(tab){if(!tab._outputCache)tab._outputCache=[];tab._outputCache.push({text:text,cls:cls});if(tab._outputCache.length>500)tab._outputCache=tab._outputCache.slice(-300);}var outType=cls==='error'?'stderr':cls==='success'?'stdout':cls==='info'?'info':'stdout';outputLog(text,outType);}
async function selectFiles(){
  if(isElectron){
    try{
      const result=await window.kaguyaDesktop.dialog.openFile({title:t('selectFile'),multi:true});
      if(result.canceled||!result.filePaths||!result.filePaths.length){termLog(t('noFilesSelected'),'info');return;}
      termLog(t('importingPaths')+' '+result.filePaths.length+' ...','info');
      const r=await fetch('/agent/import-files',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({paths:result.filePaths,device_id:generateDeviceId()})});
      const d=await r.json();
      if(d.error){termLog(t('importFailed')+': '+d.error,'error');return;}
      if(d.imported&&d.imported.length){d.imported.forEach(i=>termLog(t('importSuccess')+': '+i.src+' -> '+i.dst,'success'));loadFileTree();}
      if(d.errors&&d.errors.length){d.errors.forEach(e=>termLog(t('importFailed')+': '+e.path+' - '+e.error,'error'));}
    }catch(e){termLog(t('importFailed')+': '+e.message,'error');}
    return;
  }
  document.getElementById('ideFileInput').click();
}
async function selectFolder(){
  if(isElectron){
    try{
      const result=await window.kaguyaDesktop.dialog.openFolder({title:t('selectFolder')});
      if(result.canceled||!result.filePaths||!result.filePaths.length){termLog(t('noFilesSelected'),'info');return;}
      const selectedPath=result.filePaths[0];
      termLog(t('importingPaths')+' '+selectedPath+' ...','info');
      const r=await fetch('/agent/import-files',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({paths:[selectedPath],device_id:generateDeviceId()})});
      const d=await r.json();
      if(d.error){termLog(t('importFailed')+': '+d.error,'error');return;}
      if(d.imported&&d.imported.length){d.imported.forEach(i=>termLog(t('importSuccess')+': '+i.src+' -> '+i.dst,'success'));loadFileTree();}
      if(d.errors&&d.errors.length){d.errors.forEach(e=>termLog(t('importFailed')+': '+e.path+' - '+e.error,'error'));}
    }catch(e){termLog(t('importFailed')+': '+e.message,'error');}
    return;
  }
  document.getElementById('ideFolderInput').click();
}
function showOperationFeedback(toolName,toolInput,status){
  const fb=document.getElementById('operationFeedback');
  if(!fb){
    const newFb=document.createElement('div');
    newFb.id='operationFeedback';
    newFb.style.cssText='position:fixed;top:60px;right:20px;z-index:9999;padding:12px 20px;border-radius:10px;font-size:12px;font-weight:600;box-shadow:0 4px 20px rgba(0,0,0,0.4);transition:all 0.3s ease;max-width:320px;';
    document.body.appendChild(newFb);
  }
  const el=document.getElementById('operationFeedback');
  const iconMap={executing:'&#9203;',success:'&#10003;',error:'&#10007;',info:'&#8505;'};
  const colorMap={executing:'#fbbf24',success:'#34d399',error:'#f87171',info:'#60a5fa'};
  el.style.background=colorMap[status]||colorMap.info;
  el.style.color='#fff';
  el.innerHTML=(iconMap[status]||'')+' '+(status==='executing'?'Executing '+toolName:(status==='success'?toolName+' completed':(status==='error'?toolName+' failed':'')));
  el.style.opacity='1';
  el.style.transform='translateY(0)';
  clearTimeout(el._timeout);
  el._timeout=setTimeout(()=>{el.style.opacity='0';el.style.transform='translateY(-10px)';},3000);
}
function showFileChangeConfirmation(toolName,toolInput,output){
  const fileName=toolInput&&toolInput.path?toolInput.path.split(/[\\/]/).pop():'unknown file';
  const filePath=toolInput&&toolInput.path?toolInput.path:'';
  const confirmDiv=document.createElement('div');
  confirmDiv.className='file-change-confirmation';
  confirmDiv.style.cssText='margin:8px 0;padding:10px 14px;background:rgba(52,211,153,0.08);border:1px solid rgba(52,211,153,0.2);border-radius:8px;display:flex;align-items:center;gap:10px;animation:fadeIn 0.3s ease;';
  confirmDiv.innerHTML='<span style="font-size:18px;color:var(--success);">&#10003;</span><div style="flex:1;"><div style="font-size:11px;font-weight:600;color:var(--success);">File saved successfully</div><div style="font-size:9px;color:var(--text-dim);margin-top:2px;">'+esc(fileName)+'</div></div><button onclick="this.parentElement.remove()" style="background:none;border:none;color:var(--text-muted);cursor:pointer;font-size:14px;padding:2px;">&#x2715;</button>';
  const msgs=document.getElementById('agentMessages');
  msgs.appendChild(confirmDiv);
  msgs.scrollTop=msgs.scrollHeight;
  setTimeout(()=>{if(confirmDiv.parentElement){confirmDiv.style.opacity='0';confirmDiv.style.transition='opacity 0.5s ease';setTimeout(()=>{if(confirmDiv.parentElement)confirmDiv.remove();},500);}},5000);
}
function handleTerminalKey(e){
  const input=document.getElementById('terminalInput');
  var tab=_terminalTabs.find(function(t){return t.id===_activeTermTab;});
  var hist=tab?tab.history:_termHistory;
  var hIdx=tab?tab.histIdx:_termHistIdx;
  if(e.key==='Enter'){
    const cmd=input.value.trim();
    if(cmd){hist.push(cmd);if(tab){tab.histIdx=hist.length;}else{_termHistIdx=hist.length;}}
    runTerminalCmd(cmd);input.value='';
  }else if(e.key==='ArrowUp'){
    e.preventDefault();
    if(hIdx>0){hIdx--;input.value=hist[hIdx]||'';if(tab){tab.histIdx=hIdx;}else{_termHistIdx=hIdx;}}
  }else if(e.key==='ArrowDown'){
    e.preventDefault();
    if(hIdx<hist.length-1){hIdx++;input.value=hist[hIdx]||'';if(tab){tab.histIdx=hIdx;}else{_termHistIdx=hIdx;}}
    else{hIdx=hist.length;input.value='';if(tab){tab.histIdx=hIdx;}else{_termHistIdx=hIdx;}}
  }else if(e.ctrlKey&&e.key==='c'){
    e.preventDefault();
    input.value='';
  }
}
function clearTerminal(){const body=document.getElementById('terminalBody');if(body)body.innerHTML='';}
function switchBottomTab(tab){
  document.querySelectorAll('.bottom-tab').forEach(function(t){t.classList.remove('active');});
  document.querySelectorAll('.bottom-pane').forEach(function(p){p.classList.remove('active');});
  var tabMap={terminal:0,output:1,debug:2};
  var tabs=document.querySelectorAll('.bottom-tab');
  if(tabs[tabMap[tab]])tabs[tabMap[tab]].classList.add('active');
  var paneMap={terminal:'paneTerminal',output:'paneOutput',debug:'paneDebug'};
  var pane=document.getElementById(paneMap[tab]);
  if(pane)pane.classList.add('active');
}
function toggleBottomPanel(){
  var bp=document.getElementById('bottomPanel');
  if(!bp)return;
  if(bp.style.display==='none'){bp.style.display='flex';}else{bp.style.display='none';}
}
function toggleAgentPanel(){
  var panel=document.getElementById('agentPanel');
  var floatBtn=document.getElementById('agentToggleFloat');
  if(!panel)return;
  var isCollapsed=panel.classList.contains('collapsed');
  if(isCollapsed){
    panel.classList.remove('collapsed');
    if(floatBtn)floatBtn.style.display='none';
    localStorage.setItem('kaguya_agent_panel_collapsed','0');
  }else{
    panel.classList.add('collapsed');
    if(floatBtn)floatBtn.style.display='flex';
    localStorage.setItem('kaguya_agent_panel_collapsed','1');
  }
}
function initAgentPanelState(){
  var panel=document.getElementById('agentPanel');
  var floatBtn=document.getElementById('agentToggleFloat');
  if(!panel)return;
  var saved=localStorage.getItem('kaguya_agent_panel_collapsed');
  if(saved==='1'){
    panel.classList.add('collapsed');
    if(floatBtn)floatBtn.style.display='flex';
  }else{
    if(floatBtn)floatBtn.style.display='none';
  }
}
function addTerminalTab(){
  var id=_nextTermTabId++;
  var names=['python','node','cmd','powershell','zsh','sh'];
  var name=names[id%names.length];
  _terminalTabs.push({id:id,name:name,history:[],histIdx:-1});
  renderTerminalTabs();
  switchTerminalTab(id);
}
function switchTerminalTab(id){
  _activeTermTab=id;
  renderTerminalTabs();
  var body=document.getElementById('terminalBody');
  if(body)body.innerHTML='';
  var tab=_terminalTabs.find(function(t){return t.id===id;});
  if(tab&&tab._outputCache){tab._outputCache.forEach(function(l){termLog(l.text,l.cls);});}
  document.getElementById('termPrompt').textContent=tab&&tab.name==='python'?'>>>':'$';
}
function closeTerminalTab(id){
  if(_terminalTabs.length<=1)return;
  _terminalTabs=_terminalTabs.filter(function(t){return t.id!==id;});
  if(_activeTermTab===id){_activeTermTab=_terminalTabs[0].id;switchTerminalTab(_activeTermTab);}
  renderTerminalTabs();
}
function renderTerminalTabs(){
  var container=document.getElementById('terminalTabs');
  if(!container)return;
  container.innerHTML='';
  _terminalTabs.forEach(function(tab){
    var el=document.createElement('div');
    el.className='terminal-tab'+(tab.id===_activeTermTab?' active':'');
    el.id='ttab_'+tab.id;
    el.innerHTML='<span>'+esc(tab.name)+'</span>'+(_terminalTabs.length>1?'<span class="tt-close" onclick="event.stopPropagation();closeTerminalTab('+tab.id+')">&#x2715;</span>':'');
    el.onclick=function(){switchTerminalTab(tab.id);};
    container.appendChild(el);
  });
}
function outputLog(text,type){
  type=type||'stdout';
  var now=new Date();
  var ts=now.toLocaleTimeString([],{hour:'2-digit',minute:'2-digit',second:'2-digit'})+'.'+String(now.getMilliseconds()).padStart(3,'0');
  var entry={text:text,type:type,timestamp:ts};
  _outputLines.push(entry);
  if(_outputLines.length>_outputMaxLines){_outputLines=_outputLines.slice(-_outputMaxLines);}
  if(_outputFilter!=='all'&&_outputFilter!==type){return;}
  appendOutputLine(entry);
}
function appendOutputLine(entry){
  var panel=document.getElementById('outputPanel');
  if(!panel)return;
  var line=document.createElement('div');
  line.className='out-line out-'+entry.type;
  line.dataset.type=entry.type;
  line.innerHTML='<span class="out-timestamp">'+esc(entry.timestamp)+'</span>'+esc(entry.text);
  panel.appendChild(line);
  var auto=document.getElementById('outputAutoscroll');
  if(!auto||auto.checked){panel.scrollTop=panel.scrollHeight;}
}
function clearOutputPanel(){
  _outputLines=[];
  var panel=document.getElementById('outputPanel');
  if(panel)panel.innerHTML='';
}
function scrollOutputBottom(){
  var panel=document.getElementById('outputPanel');
  if(panel)panel.scrollTop=panel.scrollHeight;
}
function toggleOutputFilter(btn,filter){
  _outputFilter=filter;
  document.querySelectorAll('.output-toolbar .filter-btn').forEach(function(b){b.classList.remove('active');});
  btn.classList.add('active');
  var panel=document.getElementById('outputPanel');
  if(!panel)return;
  panel.innerHTML='';
  _outputLines.forEach(function(entry){
    if(filter==='all'||filter===entry.type){appendOutputLine(entry);}
  });
}
function toggleDebugSection(header){
  header.classList.toggle('collapsed');
}
function addBreakpoint(filePath,line){
  var bp=_debugBreakpoints.find(function(b){return b.file===filePath&&b.line===line;});
  if(bp){bp.enabled=!bp.enabled;}else{_debugBreakpoints.push({id:'bp_'+Date.now(),file:filePath,line:line,enabled:true});}
  renderBreakpoints();
  addDebugLog('Breakpoint '+(bp?(bp.enabled?'enabled':'disabled'):'added')+': '+filePath+':'+line);
}
function removeBreakpoint(bpId){
  _debugBreakpoints=_debugBreakpoints.filter(function(b){return b.id!==bpId;});
  renderBreakpoints();
}
function renderBreakpoints(){
  var list=document.getElementById('breakpointList');
  var count=document.getElementById('bpCount');
  if(!list)return;
  if(count)count.textContent='('+_debugBreakpoints.length+')';
  if(!_debugBreakpoints.length){list.innerHTML='<div class="debug-empty">No breakpoints set. Click line numbers in the editor to add.</div>';return;}
  list.innerHTML=_debugBreakpoints.map(function(bp){
    var fname=bp.file.split(/[\\/]/).pop();
    return '<div class="debug-breakpoint" onclick="jumpToBreakpoint(\''+esc(bp.file).replace(/'/g,"\\'")+'\','+bp.line+')"><span class="bp-dot'+(bp.enabled?'':' disabled')+'"></span><span class="bp-file">'+esc(fname)+':'+bp.line+'</span><span class="bp-line">'+esc(bp.file)+'</span><span class="bp-actions"><button onclick="event.stopPropagation();toggleBreakpoint(\''+bp.id+'\')" title="Toggle">&#x21BB;</button><button onclick="event.stopPropagation();removeBreakpoint(\''+bp.id+'\')" title="Remove">&#x2715;</button></span></div>';
  }).join('');
}
function toggleBreakpoint(bpId){
  var bp=_debugBreakpoints.find(function(b){return b.id===bpId;});
  if(bp){bp.enabled=!bp.enabled;renderBreakpoints();}
}
function jumpToBreakpoint(filePath,line){openFile(filePath,filePath.split(/[\\/]/).pop());}
function updateVariables(vars){
  _debugVariables=vars||[];
  renderVariables();
}
function renderVariables(){
  var list=document.getElementById('variableList');
  var count=document.getElementById('varCount');
  if(!list)return;
  if(count)count.textContent='('+_debugVariables.length+')';
  if(!_debugVariables.length){list.innerHTML='<div class="debug-empty">Run code in debug mode to inspect variables.</div>';return;}
  list.innerHTML=_debugVariables.map(function(v){
    return '<div class="debug-var-row"><span class="debug-var-scope">'+esc(v.scope||'local')+'</span><span class="debug-var-name">'+esc(v.name)+'</span><span class="debug-var-value">'+esc(String(v.value).substring(0,100))+'</span><span class="debug-var-type">'+esc(v.type||'')+'</span></div>';
  }).join('');
}
function updateCallstack(frames){
  _debugCallstack=frames||[];
  renderCallstack();
}
function renderCallstack(){
  var list=document.getElementById('callstackList');
  if(!list)return;
  if(!_debugCallstack.length){list.innerHTML='<div class="debug-empty">No active debug session.</div>';return;}
  list.innerHTML='<div class="debug-callstack">'+_debugCallstack.map(function(f,i){
    return '<div class="debug-callstack-frame'+(i===0?' current':'')+'" onclick="jumpToBreakpoint(\''+esc(f.file||'').replace(/'/g,"\\'")+'\','+(f.line||0)+')"><span class="frame-func">'+esc(f.function||'?')+'</span><span class="frame-loc">'+esc((f.file||'').split(/[\\/]/).pop())+':'+(f.line||0)+'</span></div>';
  }).join('')+'</div>';
}
function addDebugLog(msg){
  var now=new Date();
  var ts=now.toLocaleTimeString([],{hour:'2-digit',minute:'2-digit',second:'2-digit'});
  _debugLogEntries.push({msg:msg,ts:ts});
  if(_debugLogEntries.length>200)_debugLogEntries=_debugLogEntries.slice(-100);
  var log=document.getElementById('debugLog');
  if(log){log.innerHTML+='<div style="padding:1px 0;"><span style="color:var(--text-muted);font-size:8px;">'+esc(ts)+'</span> '+esc(msg)+'</div>';log.scrollTop=log.scrollHeight;}
}
function setConvFilter(mode){
  _convFilterMode=mode;
  document.querySelectorAll('.conv-filter-btn').forEach(function(b){b.classList.remove('active');});
  event.target.classList.add('active');
  applyConvFolding();
}
function applyConvFolding(){
  var msgs=document.getElementById('agentMessages');
  if(!msgs)return;
  msgs.querySelectorAll('.msg-group-divider,.msg-fold-section').forEach(function(el){el.remove();});
  var children=Array.from(msgs.children);
  if(_convFilterMode==='session'){
    var sessionIdx=0;
    children.forEach(function(child){
      if(child.classList.contains('user')){
        sessionIdx++;
        var divider=document.createElement('div');
        divider.className='msg-group-divider';
        divider.innerHTML='<span class="group-label">Session #'+sessionIdx+'</span>';
        msgs.insertBefore(divider,child);
      }
    });
  }else if(_convFilterMode==='time'){
    var lastMinute=null;
    children.forEach(function(child){
      var ts=child.dataset.timestamp;
      if(!ts)return;
      var d=new Date(ts);
      var minute=d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0')+' '+String(d.getHours()).padStart(2,'0')+':'+String(d.getMinutes()).padStart(2,'0');
      if(minute!==lastMinute){
        lastMinute=minute;
        var divider=document.createElement('div');
        divider.className='msg-group-divider';
        divider.innerHTML='<span class="group-label">'+minute+'</span>';
        msgs.insertBefore(divider,child);
      }
    });
  }else if(_convFilterMode==='topic'){
    var topicLabels={'read_file':'File Reading','write_file':'File Writing','edit_file':'File Editing','execute_command':'Command Execution','search_files':'Code Search','compile':'Compilation','glob':'File Search','web_fetch':'Web Fetch','web_search':'Web Search','agent_spawn':'Agent Spawn'};
    var lastTopic=null;
    children.forEach(function(child){
      var topic=null;
      if(child.classList.contains('tool-use')||child.classList.contains('tool-result')){
        var nameEl=child.querySelector('.tool-name');
        if(nameEl){var m=nameEl.textContent.match(/\[\w+\]\s*(\w+)/);if(m)topic=m[1];}
      }
      if(topic&&topic!==lastTopic){
        lastTopic=topic;
        var section=document.createElement('div');
        section.className='msg-fold-section';
        var header=document.createElement('div');
        header.className='msg-fold-header';
        header.innerHTML='<span class="fold-arrow">&#x25BC;</span> '+(topicLabels[topic]||topic);
        header.onclick=function(){header.classList.toggle('collapsed');};
        var body=document.createElement('div');
        body.className='msg-fold-body';
        section.appendChild(header);
        section.appendChild(body);
        msgs.insertBefore(section,child);
        body.appendChild(child);
      }else if(lastTopic){
        var prevSection=child.previousElementSibling;
        if(prevSection&&prevSection.classList.contains('msg-fold-section')){
          prevSection.querySelector('.msg-fold-body').appendChild(child);
        }
      }
    });
  }
}
function toggleMsgFoldAll(){
  _msgFoldAllState=!_msgFoldAllState;
  var btn=document.getElementById('foldToggleBtn');
  if(btn)btn.textContent=_msgFoldAllState?'▶ All':'◀ All';
  if(_msgFoldAllState){collapseAllMsgs();}else{expandAllMsgs();}
  document.querySelectorAll('.msg-fold-header').forEach(function(h){
    if(_msgFoldAllState){h.classList.add('collapsed');}else{h.classList.remove('collapsed');}
  });
  document.querySelectorAll('.conv-group-header').forEach(function(h){
    if(_msgFoldAllState){h.classList.add('collapsed');}else{h.classList.remove('collapsed');}
  });
}
async function runTerminalCmd(cmd){
  if(!cmd.trim())return;
  termLog('$ '+cmd);
  addDebugLog('Terminal: $ '+cmd);
  if(isElectron && electronTerminalSession){
    try{
      window.kaguyaDesktop.terminal.write(electronTerminalSession, cmd + '\n');
      return;
    }catch(e){
      termLog('Error: '+e.message,'error');
      return;
    }
  }
  var startTime=performance.now();
  try{
    var ctrl=new AbortController();
    var tid=setTimeout(function(){ctrl.abort();},30000);
    const r=await fetch('/agent/terminal/exec',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({command:cmd,device_id:generateDeviceId(),timeout:30}),signal:ctrl.signal});
    clearTimeout(tid);
    const d=await r.json();
    var elapsed=Math.round(performance.now()-startTime);
    if(d.error){termLog('Error: '+d.error,'error');addDebugLog('Command failed ('+elapsed+'ms): '+d.error);}
    else{
      var out=d.output||'';
      var isErr=d.exit_code!==0&&d.exit_code!==undefined;
      termLog(out,isErr?'error':'success');
      if(d.exit_code!==undefined&&d.exit_code!==0){termLog('[Exit code: '+d.exit_code+']','error');}
      addDebugLog('Command completed ('+elapsed+'ms, exit: '+(d.exit_code||0)+')');
      if(d.variables){updateVariables(d.variables);}
    }
  }catch(e){
    if(e.name==='AbortError'){termLog('Error: Command timed out (30s)','error');addDebugLog('Command timed out');}
    else{termLog('Error: '+e.message,'error');addDebugLog('Command error: '+e.message);}
  }
}
function showPermissionPrompt(toolName,toolInput,requestId,reason,msgEl){return new Promise((resolve)=>{const bar=document.createElement('div');bar.className='permission-bar';bar.style.flexWrap='wrap';bar.style.gap='4px';const inputStr=typeof toolInput==='object'?JSON.stringify(toolInput,null,1):String(toolInput);const shortInput=inputStr.length>200?inputStr.substring(0,200)+'...':inputStr;const reasonHtml=reason?'<div style="width:100%;font-size:9px;color:var(--text-muted);margin-top:2px;">'+t('permReason')+': '+esc(reason)+'</div>':'';const detailHtml='<div style="width:100%;max-height:80px;overflow:auto;font-size:9px;color:var(--text-dim);background:var(--bg-0);padding:4px 6px;border-radius:3px;margin-top:2px;font-family:var(--font-mono);white-space:pre-wrap;word-break:break-all;">'+esc(shortInput)+'</div>';bar.innerHTML='<span style="color:var(--warning);">&#x26A0;</span> <span>'+t('permRequest')+': <strong>'+esc(toolName)+'</strong></span>'+'<button class="allow-btn" id="permAllow">'+t('allow')+'</button>'+'<button class="deny-btn" id="permDeny">'+t('deny')+'</button>'+'<label style="font-size:9px;color:var(--text-muted);display:flex;align-items:center;gap:3px;margin-left:4px;"><input type="checkbox" id="permAlways" style="width:10px;height:10px;"> '+t('alwaysAllow')+'</label>'+reasonHtml+detailHtml;msgEl.appendChild(bar);msgEl.scrollTop=msgEl.scrollHeight;bar.querySelector('#permAllow').onclick=()=>{const always=bar.querySelector('#permAlways').checked;bar.remove();if(requestId){fetch('/agent/permission/respond',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({request_id:requestId,allowed:true,always:always})});}resolve({allowed:true,always:always});};bar.querySelector('#permDeny').onclick=()=>{const always=bar.querySelector('#permAlways').checked;bar.remove();if(requestId){fetch('/agent/permission/respond',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({request_id:requestId,allowed:false,always:always})});}resolve({allowed:false,always:always});};});}
async function sendAgentMsg(){
  const input=document.getElementById('agentInput');
  const msg=input.value.trim();
  if(!msg||isAgentRunning)return;
  input.value='';input.style.height='auto';hideSlashMenu();
  const msgs=document.getElementById('agentMessages');
  const userMsg=document.createElement('div');
  userMsg.className='msg user';userMsg.textContent=msg;
  userMsg.dataset.timestamp=new Date().toISOString();
  msgs.appendChild(userMsg);msgs.scrollTop=msgs.scrollHeight;
  isAgentRunning=true;document.getElementById('agentSendBtn').disabled=true;
  document.getElementById('statusText').textContent=t('thinking')+'...';
  currentIteration=0;
  updateTaskStatus(activeTaskId,'in_progress');
  let thinkingEl=null;
  let thinkingText='';
  try{
    const soloMode=currentMode==='solo';
    const r=await fetch('/agent/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:msg,history:agentHistory.slice(-10),working_dir:undefined,external_api:getExternalApiConfig(),solo_mode:soloMode,device_id:generateDeviceId()})});
    if(!r.ok){const errText=await r.text();throw new Error('HTTP '+r.status+': '+errText.substring(0,200));}
    const reader=r.body.getReader();const dec=new TextDecoder();
    let buf='';let fullContent='';
    while(true){
      const{done,value}=await reader.read();
      if(done){
        if(isAgentRunning){
          if(thinkingEl){thinkingEl.classList.remove('thinking');thinkingEl.classList.add('thinking-done');thinkingEl.classList.add('collapsed');const fade=thinkingEl.querySelector('.think-fade');if(fade)fade.style.display='block';const tg=thinkingEl.querySelector('.think-toggle');if(tg)tg.textContent='▶';}
          agentHistory.push({user:msg,assistant:fullContent||thinkingText});
          const task=getActiveTask();if(task){task.history=agentHistory.slice(-20);task.status='done';}
          isAgentRunning=false;document.getElementById('agentSendBtn').disabled=false;
          document.getElementById('statusText').textContent=t('ready');
          saveTasks();
        }
        break;
      }
      buf+=dec.decode(value,{stream:true});
      const lines=buf.split('\n');buf=lines.pop()||'';
      for(const l of lines){
        if(!l.startsWith('data: '))continue;
        try{
          const d=JSON.parse(l.slice(6));
          if(d.type==='thinking'){
            currentIteration=d.iteration||0;
            document.getElementById('statusText').textContent=t('thinking')+' (turn '+currentIteration+')...';
            thinkingText+=d.content||'';
            if(!thinkingEl){
              thinkingEl=document.createElement('div');
              thinkingEl.className='msg assistant thinking collapsed';
              thinkingEl.innerHTML='<span class="think-toggle">▶</span><div class="think-fade" style="display:block;"></div>';
              thinkingEl.onclick=function(ev){if(ev.target.classList.contains('think-toggle')||ev.target===thinkingEl){toggleMsgCollapse(thinkingEl);}};
              msgs.appendChild(thinkingEl);
            }
            const toggleBtn=thinkingEl.querySelector('.think-toggle');
            const fadeEl=thinkingEl.querySelector('.think-fade');
            const summary=thinkingText.length>120?thinkingText.substring(0,120)+'...':thinkingText;
            thinkingEl.innerHTML=renderMd(thinkingText)+'<span class="think-toggle">'+(thinkingEl.classList.contains('collapsed')?'▶':'▼')+'</span><div class="think-fade" style="display:'+(thinkingEl.classList.contains('collapsed')?'block':'none')+';"></div>';
            thinkingEl.onclick=function(ev){if(ev.target.classList.contains('think-toggle')||ev.target===thinkingEl){toggleMsgCollapse(thinkingEl);}};
            msgs.scrollTop=msgs.scrollHeight;
          }
          else if(d.type==='permission_request'){
            if(thinkingEl){thinkingEl.classList.remove('thinking');thinkingEl.classList.add('thinking-done');thinkingEl.classList.add('collapsed');const fade=thinkingEl.querySelector('.think-fade');if(fade)fade.style.display='block';const tg=thinkingEl.querySelector('.think-toggle');if(tg)tg.textContent='▶';thinkingEl=null;thinkingText='';}
            const icon=TOOL_ICONS[d.tool]||'?';
            const isDanger=d.dangerous||DANGEROUS.includes(d.tool);
            const inputStr=typeof d.input==='object'?JSON.stringify(d.input,null,2):String(d.input);
            const el=document.createElement('div');el.className='msg tool-use collapsed'+(isDanger?' tool-danger':'');
            const fileHint=(d.tool==='write_file'||d.tool==='edit_file')&&d.input&&d.input.path?' &#128196; '+esc(d.input.path.split(/[\\/]/).pop()):'';
            el.innerHTML='<span class="tool-name">['+icon+'] '+esc(d.tool)+'</span>'+(isDanger?'<span class="danger-badge">!</span>':'')+fileHint+'<span class="tool-toggle">▶</span><pre>'+esc(inputStr.substring(0,800))+'</pre>';
            el.onclick=function(ev){if(ev.target.classList.contains('tool-toggle')||ev.target===el){toggleMsgCollapse(el);}};
            msgs.appendChild(el);
            if(d.tool==='execute_command'){
              const outStr=(d.output||'').substring(0,500);
              const isPermErr=d.output&&d.output.startsWith('Error');
              termLog('[Result] '+outStr+(d.output&&d.output.length>500?'...':''),isPermErr?'error':'success');
            }
            else if((d.tool==='write_file'||d.tool==='edit_file')&&!(d.output&&d.output.startsWith('Error'))){
              termLog('[Success] File saved: '+(d.input&&d.input.path),'success');
            }
            else if(d.output&&d.output.startsWith('Error')){
              termLog('[Error] '+d.tool+': '+(d.output||'Unknown error').substring(0,200),'error');
            }
            else{
              termLog('[Done] '+d.tool,'success');
            }
            document.getElementById('statusText').textContent=t('waitingApproval');
            const result=await showPermissionPrompt(d.tool,d.input,d.request_id,d.reason,msgs);
            if(!result.allowed){const denyEl=document.createElement('div');denyEl.className='msg tool-result error-result';denyEl.innerHTML='<span class="tool-name">['+t('deny')+'] '+esc(d.tool)+'</span>'+(result.always?' <span style="color:var(--warning);font-size:9px;">('+t('alwaysDeny')+')</span>':'');msgs.appendChild(denyEl);}
            else if(result.always){const alwaysEl=document.createElement('div');alwaysEl.className='msg tool-result';alwaysEl.innerHTML='<span class="tool-name">['+t('allow')+'] '+esc(d.tool)+'</span> <span style="color:var(--success);font-size:9px;">('+t('alwaysAllow')+')</span>';msgs.appendChild(alwaysEl);}
          }
          else if(d.type==='tool_use'){
            if(thinkingEl){thinkingEl.classList.remove('thinking');thinkingEl.classList.add('thinking-done');thinkingEl.classList.add('collapsed');const fade=thinkingEl.querySelector('.think-fade');if(fade)fade.style.display='block';const tg=thinkingEl.querySelector('.think-toggle');if(tg)tg.textContent='▶';thinkingEl=null;thinkingText='';}
            const icon=TOOL_ICONS[d.tool]||'?';
            const isDanger=DANGEROUS.includes(d.tool);
            const inputStr=typeof d.input==='object'?JSON.stringify(d.input,null,2):String(d.input);
            const permBadge=d.permission==='deny'?'<span class="danger-badge" style="background:#ef4444;">X</span>':(d.permission==='allow'?'<span class="danger-badge" style="background:var(--success);">&#10003;</span>':'');
            const el=document.createElement('div');el.className='msg tool-use collapsed';
            const fileHint=(d.tool==='write_file'||d.tool==='edit_file')&&d.input&&d.input.path?' &#128196; '+esc(d.input.path.split(/[\\/]/).pop()):'';
            el.innerHTML='<span class="tool-name">['+icon+'] '+esc(d.tool)+'</span>'+permBadge+fileHint+'<span class="tool-toggle">▶</span><pre>'+esc(inputStr.substring(0,800))+'</pre>';
            el.onclick=function(ev){if(ev.target.classList.contains('tool-toggle')||ev.target===el){toggleMsgCollapse(el);}};
            msgs.appendChild(el);
            document.getElementById('statusText').textContent=t('executing')+' '+d.tool+' (turn '+currentIteration+')...';
            const tp=document.getElementById('bottomPanel');
            if(tp&&tp.style.display==='none'){tp.style.display='flex';switchBottomTab('terminal');}
            if(d.tool==='execute_command'&&d.input&&d.input.command){
              termLog('[Agent] $ '+d.input.command,'info');
            }
            else if(d.tool==='write_file'&&d.input&&d.input.path){
              termLog('[Agent] Writing: '+d.input.path,'info');
            }
            else if(d.tool==='edit_file'&&d.input&&d.input.path){
              termLog('[Agent] Editing: '+d.input.path,'info');
            }
            else{
              termLog('[Agent] Executing: '+d.tool,'info');
            }
          }
          else if(d.type==='tool_result'){
            if(thinkingEl){thinkingEl.classList.remove('thinking');thinkingEl.classList.add('thinking-done');thinkingEl.classList.add('collapsed');const fade=thinkingEl.querySelector('.think-fade');if(fade)fade.style.display='block';const tg=thinkingEl.querySelector('.think-toggle');if(tg)tg.textContent='▶';thinkingEl=null;thinkingText='';}
            const isErr=d.output&&d.output.startsWith('Error');
            const el=document.createElement('div');el.className='msg tool-result collapsed'+(isErr?' error-result':'');
            const shortOut=(d.output||'').substring(0,120).replace(/\n/g,' ');
            const filePath=d.input&&(d.input.path||d.input.file_path);
            let diffHtml='';
            if((d.tool==='write_file'||d.tool==='edit_file')&&d.old_content&&!isErr){
              const newContent=d.input&&d.input.content;
              if(newContent){diffHtml=renderDiffView(d.old_content,newContent,d.tool,filePath);}
            }
            if(diffHtml){
              el.innerHTML='<span class="tool-name">['+(isErr?'FAIL':'OK')+'] '+esc(d.tool)+'</span> <span style="color:var(--text-muted);font-size:10px;">'+esc(filePath||shortOut)+'</span><span class="tool-toggle">▶</span>'+diffHtml+'<pre style="margin-top:4px;">'+esc((d.output||'').substring(0,800))+'</pre>';
            }else{
              el.innerHTML='<span class="tool-name">['+(isErr?'FAIL':'OK')+'] '+esc(d.tool)+'</span> <span style="color:var(--text-muted);font-size:10px;">'+esc(shortOut)+(d.output&&d.output.length>120?'...':'')+'</span><span class="tool-toggle">▶</span><pre>'+esc((d.output||'').substring(0,1500))+'</pre>';
            }
            el.onclick=function(ev){if(ev.target.classList.contains('tool-toggle')||ev.target===el){toggleMsgCollapse(el);}};
            msgs.appendChild(el);
            if(d.tool==='execute_command'){
              const outStr=(d.output||'').substring(0,500);
              termLog('[Result] '+outStr+(d.output&&d.output.length>500?'...':''),isErr?'error':'success');
            }
            else if((d.tool==='write_file'||d.tool==='edit_file')&&!isErr){
              termLog('[Success] File saved: '+(d.input&&d.input.path),'success');
              showFileChangeConfirmation(d.tool,d.input,d.output);
            }
            else if(isErr){
              termLog('[Error] '+d.tool+': '+(d.output||'Unknown error').substring(0,200),'error');
            }
            else{
              termLog('[Done] '+d.tool,'success');
            }
            if(d.tool==='read_file'&&d.output){const p=d.input&&d.input.path;const ln=d.input&&d.input.line_number?d.input.line_number:0;if(p)openFileFromAgent(p,d.output,ln);}
            if((d.tool==='write_file'||d.tool==='edit_file'||d.tool==='create_directory')&&!isErr){
              loadFileTree();
              if(d.input){
                const p=d.input.path||d.input.file_path;
                const ln=d.input.line_number?d.input.line_number:0;
                if(p&&(d.tool==='write_file'||d.tool==='edit_file')){
                  fetch('/agent/read-file',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:p,device_id:generateDeviceId()})}).then(function(r){return r.json();}).then(function(fileData){
                    if(fileData.content!==undefined){openFileFromAgent(p,fileData.content,ln);}
                  }).catch(function(){});
                }
              }
            }
          }
          else if(d.type==='assistant'){
            if(thinkingEl){thinkingEl.classList.remove('thinking');thinkingEl=null;thinkingText='';}
            fullContent=d.content||'';
            const inTk=estimateTokens(msg);const outTk=estimateTokens(fullContent);
            addCost(inTk,outTk);
            const el=document.createElement('div');el.className='msg assistant';el.innerHTML=renderMd(fullContent);el.dataset.timestamp=new Date().toISOString();msgs.appendChild(el);
          }
          else if(d.type==='error'){const el=document.createElement('div');el.className='msg error';el.textContent='Error: '+d.content;msgs.appendChild(el);}
          msgs.scrollTop=msgs.scrollHeight;
          if(d.done){
            if(thinkingEl){thinkingEl.classList.remove('thinking');thinkingEl.classList.add('thinking-done');thinkingEl.classList.add('collapsed');const fade=thinkingEl.querySelector('.think-fade');if(fade)fade.style.display='block';const tg=thinkingEl.querySelector('.think-toggle');if(tg)tg.textContent='▶';thinkingEl=null;thinkingText='';}
            agentHistory.push({user:msg,assistant:fullContent});
            const task=getActiveTask();if(task){task.history=agentHistory.slice(-20);task.status='done';}
            isAgentRunning=false;document.getElementById('agentSendBtn').disabled=false;
            document.getElementById('statusText').textContent=t('ready');
            saveTasks();
            applyConvFolding();
            addDebugLog('Agent run completed. Tokens: '+totalTokensIn+'+'+totalTokensOut+', Cost: $'+totalCost.toFixed(4));
          }
        }catch(e){console.warn('[Kaguya IDE] SSE parse error:',e);}
      }
    }
  }catch(e){
    const el=document.createElement('div');el.className='msg error';el.textContent='Connection error: '+e.message;msgs.appendChild(el);isAgentRunning=false;document.getElementById('agentSendBtn').disabled=false;document.getElementById('statusText').textContent='Error';
  }
}
function openFileFromAgent(path,content,lineNum){const name=path.split(/[\\/]/).pop();const ext=path.split('.').pop();if(!openTabs.find(tb=>tb.path===path)){openTabs.push({path,name,language:ext});renderTabs();}activeTab=path;renderTabs();const ws=document.getElementById('welcomeScreen');if(ws)ws.style.display='none';if(content&&typeof content==='string'&&!content.match(/^\s*\d+\s*→/m)){renderCode(content,ext);scrollToLine(lineNum);document.getElementById('statusFile').textContent=name;document.getElementById('statusLang').textContent=ext;return;}fetch('/agent/read-file',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:path,device_id:generateDeviceId()})}).then(function(r){return r.json();}).then(function(d){if(d.content!==undefined){renderCode(d.content,d.language||ext);scrollToLine(lineNum);}else if(content){var clean=content.replace(/^\s*\d+\s*→/gm,'');renderCode(clean,ext);scrollToLine(lineNum);}}).catch(function(){if(content){var clean=content.replace(/^\s*\d+\s*→/gm,'');renderCode(clean,ext);scrollToLine(lineNum);}});document.getElementById('statusFile').textContent=name;document.getElementById('statusLang').textContent=ext;}
function scrollToLine(lineNum){if(!lineNum||lineNum<=0)return;var el=document.getElementById('codeContent');if(!el)return;var lines=el.querySelectorAll('.code-diff-line, pre code');if(lines.length>0&&lines[0].tagName!=='PRE'){var target=lines[Math.min(lineNum-1,lines.length-1)];if(target)target.scrollIntoView({behavior:'smooth',block:'center'});return;}var codeEl=el.querySelector('pre code');if(!codeEl)return;var allLines=codeEl.innerHTML.split('\n');if(lineNum<=allLines.length){var lineEls=codeEl.querySelectorAll('.hljs-line');if(lineEls.length===0){codeEl.innerHTML=allLines.map(function(l,i){return '<span class="hljs-line" data-line="'+(i+1)+'">'+l+'</span>';}).join('\n');}var targetLine=codeEl.querySelector('[data-line="'+lineNum+'"]');if(targetLine)targetLine.scrollIntoView({behavior:'smooth',block:'center'});}}
function computeDiff(oldText,newText){const oldLines=oldText?oldText.split('\n'):[];const newLines=newText?newText.split('\n'):[];const m=oldLines.length,n=newLines.length;const dp=[];for(let i=0;i<=m;i++){dp[i]=[];for(let j=0;j<=n;j++)dp[i][j]=0;}for(let i=1;i<=m;i++)for(let j=1;j<=n;j++){if(oldLines[i-1]===newLines[j-1])dp[i][j]=dp[i-1][j-1]+1;else dp[i][j]=Math.max(dp[i-1][j],dp[i][j-1]);}const result=[];let i=m,j=n;while(i>0||j>0){if(i>0&&j>0&&oldLines[i-1]===newLines[j-1]){result.unshift({type:'ctx',oldLine:i,newLine:j,content:oldLines[i-1]});i--;j--;}else if(j>0&&(i===0||dp[i][j-1]>=dp[i-1][j])){result.unshift({type:'add',newLine:j,content:newLines[j-1]});j--;}else{result.unshift({type:'del',oldLine:i,content:oldLines[i-1]});i--;}}return result;}
function renderDiffView(oldContent,newContent,toolName,filePath){if(!oldContent)return null;const diff=computeDiff(oldContent,newContent);let addCount=0,delCount=0;diff.forEach(function(d){if(d.type==='add')addCount++;else if(d.type==='del')delCount++;});let html='<div class="code-diff-container">';html+='<div class="code-diff-header">';html+='<span><span style="color:var(--accent2);font-weight:600;">'+esc(toolName)+'</span>'+ (filePath?' <span style="opacity:0.5;">'+esc(filePath)+'</span>':'')+'</span>';html+='<span class="diff-stats"><span class="stat-add">+'+addCount+'</span><span class="stat-del">-'+delCount+'</span></span>';html+='<span class="diff-toggle" onclick="this.closest(\'.code-diff-container\').querySelector(\'.code-diff-body\').classList.toggle(\'collapsed\')">Collapse</span>';html+='</div>';html+='<div class="code-diff-body">';const maxLineNum=Math.max(...diff.filter(function(d){return d.oldLine||d.newLine;}).map(function(d){return Math.max(d.oldLine||0,d.newLine||0);}));const numDigits=String(maxLineNum).length;diff.forEach(function(d){const cls='code-diff-line '+d.type;let numHtml='';if(d.type==='ctx'){numHtml='<span class="line-num old-num">'+String(d.oldLine).padStart(numDigits,' ')+'</span><span class="line-num new-num">'+String(d.newLine).padStart(numDigits,' ')+'</span>';}else if(d.type==='del'){numHtml='<span class="line-num old-num">'+String(d.oldLine).padStart(numDigits,' ')+'</span><span class="line-num"></span>';}else if(d.type==='add'){numHtml='<span class="line-num old-num"></span><span class="line-num new-num">'+String(d.newLine).padStart(numDigits,' ')+'</span>';}html+='<div class="'+cls+'">'+numHtml+'<span class="line-content">'+(d.type==='add'?'+ ':(d.type==='del'?'- ':'  ')+esc(d.content)+'</span></div>';});html+='</div></div>';return html;}
function renderMd(text){let html=esc(text);html=html.replace(new RegExp(String.fromCharCode(96)+String.fromCharCode(96)+String.fromCharCode(96)+'(\\w*)\\n([\\s\\S]*?)'+String.fromCharCode(96)+String.fromCharCode(96)+String.fromCharCode(96),'g'),function(m,lang,code){return '<pre><code>'+code+'</code></pre>';});html=html.replace(new RegExp(String.fromCharCode(96)+'([^'+String.fromCharCode(96)+']+)'+String.fromCharCode(96),'g'),'<code>$1</code>');html=html.replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>');html=html.replace(/\n/g,'<br>');return html;}
document.addEventListener('keydown',function(e){if(e.ctrlKey&&e.key==='b'){e.preventDefault();const s=document.querySelector('.sidebar');if(s)s.classList.toggle('collapsed');}if(e.ctrlKey&&e.key==='h'){e.preventDefault();toggleAgentPanel();}if(e.ctrlKey&&e.key==='j'){e.preventDefault();const tp=document.getElementById('bottomPanel');if(tp){if(tp.style.display==='none'){tp.style.display='flex';switchBottomTab('terminal');}else{tp.style.display='none';}}}if(e.key==='F5'){e.preventDefault();compileCurrentFile();}if(e.key==='Escape'){const overlay=document.getElementById('apiWarningOverlay');if(overlay)overlay.remove();}});
async function compileCurrentFile(){if(!activeTab){termLog(t('noFileCompile'),'error');return;}const tab=openTabs.find(t2=>t2.path===activeTab);if(!tab)return;const langMap={'py':'python','js':'javascript','ts':'typescript','c':'c','cpp':'cpp','java':'java','go':'go','rs':'rust'};const lang=langMap[tab.language]||tab.language;try{const r=await fetch('/agent/read-file',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:tab.path,device_id:generateDeviceId()})});const d=await r.json();if(d.error){termLog('Error: '+d.error,'error');return;}termLog(t('compiling')+' '+tab.name+' ('+lang+')...','info');outputLog('[Compile] '+tab.name+' ('+lang+')','info');addDebugLog('Compiling: '+tab.name+' ('+lang+')');switchBottomTab('output');const cr=await fetch('/agent/compile',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({language:lang,code:d.content,timeout:15})});const cd=await cr.json();if(cd.result){termLog(cd.result,cd.result.includes('Error')?'error':'success');outputLog(cd.result,cd.result.includes('Error')?'stderr':'stdout');addDebugLog('Compile '+(cd.result.includes('Error')?'failed':'succeeded'));if(cd.variables){updateVariables(cd.variables);}if(cd.callstack){updateCallstack(cd.callstack);}}else if(cd.error){termLog('Compile error: '+cd.error,'error');outputLog('Compile error: '+cd.error,'stderr');addDebugLog('Compile error: '+cd.error);}}catch(e){termLog('Compile failed: '+e.message,'error');outputLog('Compile failed: '+e.message,'stderr');addDebugLog('Compile exception: '+e.message);}}
async function checkApiStatus(){
  try{
    const extApi=getExternalApiConfig();
    if(!extApi||!extApi.enabled||!extApi.apiKey){
      if(isElectron){
        showIdeApiOverlay('External AI API not configured. Please configure an external model (DeepSeek/Qwen/Claude) in the API Center.', true);
        return false;
      }
      showIdeApiOverlay('External AI API not configured. Local models do not support IDE features. Please configure an external model in the API Center.');
      return false;
    }
    const ctrl=new AbortController();
    const tid=setTimeout(()=>ctrl.abort(),8000);
    const r=await fetch('/agent/api-status',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({external_api:extApi}),
      signal:ctrl.signal
    });
    clearTimeout(tid);
    const d=await r.json();
    if(!d.available||d.provider==='ollama'){
      if(isElectron){
        showIdeApiOverlay(d.provider==='ollama'?'Local Ollama model does not support IDE features. Please configure an external API (DeepSeek/Qwen/Claude).':d.message||'Unknown error', true);
        return false;
      }
      showIdeApiOverlay(d.provider==='ollama'?'Local Ollama model does not support IDE features. Please configure an external API (DeepSeek/Qwen/Claude).':d.message||'Unknown error');
      return false;
    }
    if(d.model){document.getElementById('modelLabel').textContent=d.model.substring(0,20);}
    return true;
  }catch(e){
    if(isElectron){
      showIdeApiOverlay('Connection error: '+(e.message||'timeout'), true);
      return false;
    }
    showIdeApiOverlay('Connection error: '+(e.message||'timeout'));
    return false;
  }
}
function showIdeApiOverlay(msg, dismissible){
  // Don't show overlay on first load - allow welcome screen to display
  // Instead, show a non-blocking warning banner at the top
  const existing=document.getElementById('apiWarningOverlay');
  if(existing)existing.remove();
  
  // Check if this is during initial load (within first 5 seconds)
  const isInitialLoad = !window.kaguyaAppReady;
  
  if(isInitialLoad && !dismissible){
    // Show a non-blocking banner instead of full overlay during initial load
    const banner=document.createElement('div');
    banner.id='apiWarningBanner';
    banner.style.cssText='position:fixed;top:0;left:0;right:0;background:linear-gradient(135deg,rgba(248,113,113,0.95),rgba(239,68,68,0.95));color:#fff;padding:12px 20px;z-index:99998;display:flex;align-items:center;justify-content:space-between;box-shadow:0 4px 12px rgba(0,0,0,0.3);font-size:13px;';
    banner.innerHTML='<div style="display:flex;align-items:center;gap:10px;"><span style="font-size:18px;">⚠️</span><div><strong>API 未配置</strong> - 请在左侧"API中心"配置外部模型 (DeepSeek/Qwen/Claude)</div></div><button onclick="this.parentElement.remove();" style="background:rgba(255,255,255,0.2);border:none;color:#fff;padding:6px 12px;border-radius:6px;cursor:pointer;font-size:12px;">稍后配置</button>';
    document.body.appendChild(banner);
    // Auto-hide after 8 seconds
    setTimeout(()=>{if(banner.parentElement)banner.remove();}, 8000);
    return;
  }
  
  // Show full overlay only when explicitly requested (e.g., when user tries to send a message)
  const overlay=document.createElement('div');
  overlay.id='apiWarningOverlay';
  overlay.style.cssText='position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(10,10,15,0.97);z-index:99999;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(12px);';
  const dismissBtn='<button onclick="document.getElementById(\'apiWarningOverlay\').remove();loadFileTree();" style="display:inline-block;padding:10px 28px;background:var(--grad);color:#fff;border-radius:10px;border:none;font-size:13px;font-weight:600;cursor:pointer;margin-top:8px;">Continue (File Browser Mode)</button>';
  const backBtn='<a href="/" style="display:inline-block;padding:10px 28px;background:var(--grad);color:#fff;border-radius:10px;text-decoration:none;font-size:13px;font-weight:600;">&#x2190; '+t('backToChat')+'</a>';
  overlay.innerHTML='<div style="text-align:center;max-width:460px;padding:36px;background:var(--bg-2);border:1px solid rgba(248,113,113,0.2);border-radius:16px;box-shadow:0 16px 64px rgba(0,0,0,0.5);"><div style="width:64px;height:64px;margin:0 auto 20px;background:linear-gradient(135deg,#f87171,#f472b6);border-radius:18px;display:flex;align-items:center;justify-content:center;font-size:28px;color:#fff;">&#x26A0;</div><h2 style="font-size:20px;color:var(--text);margin-bottom:10px;font-weight:700;">'+t('apiNotConnected')+'</h2><p style="color:var(--text-dim);font-size:12px;line-height:1.6;margin-bottom:8px;">'+t('apiRequiresModel')+'</p><p style="color:var(--error);font-size:11px;margin-bottom:20px;padding:10px;background:rgba(248,113,113,0.06);border-radius:8px;border:1px solid rgba(248,113,113,0.1);">'+esc(msg)+'</p>'+backBtn+' '+dismissBtn+'</div>';
  document.body.appendChild(overlay);
}
// Initialize IDE on DOM ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('[Kaguya IDE] DOM loaded, initializing...');
    try {
        applyLang();
        setupDragDrop();
        setupBottomPanelResize();
        setupAgentPanelResize();
        initAgentPanelState();
        renderTasks();
        console.log('[Kaguya IDE] Basic initialization complete');
    } catch(e) {
        console.error('[Kaguya IDE] Initialization error:', e);
    }
    // Delay API status check to allow welcome screen to show first
    setTimeout(function() {
        console.log('[Kaguya IDE] Checking API status...');
        checkApiStatus().then(function(ok) {
            console.log('[Kaguya IDE] API status:', ok ? 'OK' : 'Not configured');
            if(ok) {
                identifyDevice().then(function() { loadFileTree(); });
            } else {
                identifyDevice();
            }
        }).catch(function(e) {
            console.error('[Kaguya IDE] API check error:', e);
            identifyDevice();
        });
    }, 1500);
});
// Mark app as ready after a delay
setTimeout(function() { window.kaguyaAppReady = true; }, 3000);
function setupBottomPanelResize(){
  var handle=document.getElementById('terminalResize');
  var panel=document.getElementById('bottomPanel');
  if(!handle||!panel)return;
  var startY,startH;
  handle.addEventListener('mousedown',function(e){
    e.preventDefault();
    startY=e.clientY;
    startH=panel.offsetHeight;
    document.addEventListener('mousemove',onDrag);
    document.addEventListener('mouseup',onRelease);
    document.body.style.cursor='row-resize';
    document.body.style.userSelect='none';
  });
  function onDrag(e){
    var diff=startY-e.clientY;
    var newH=Math.max(80,Math.min(600,startH+diff));
    panel.style.height=newH+'px';
  }
  function onRelease(){
    document.removeEventListener('mousemove',onDrag);
    document.removeEventListener('mouseup',onRelease);
    document.body.style.cursor='';
    document.body.style.userSelect='';
  }
}
function setupAgentPanelResize(){
  var handle=document.getElementById('agentResize');
  var panel=document.querySelector('.agent-panel');
  if(!handle||!panel)return;
  var startX,startW;
  handle.addEventListener('mousedown',function(e){
    e.preventDefault();
    startX=e.clientX;
    startW=panel.offsetWidth;
    document.addEventListener('mousemove',onDrag);
    document.addEventListener('mouseup',onRelease);
    document.body.style.cursor='col-resize';
    document.body.style.userSelect='none';
  });
  function onDrag(e){
    var diff=startX-e.clientX;
    var newW=Math.max(280,Math.min(800,startW+diff));
    panel.style.width=newW+'px';
  }
  function onRelease(){
    document.removeEventListener('mousemove',onDrag);
    document.removeEventListener('mouseup',onRelease);
    document.body.style.cursor='';
    document.body.style.userSelect='';
  }
}
function setupDragDrop(){
  const editorArea=document.querySelector('.editor-area');
  if(!editorArea)return;
  editorArea.addEventListener('dragover',function(e){e.preventDefault();e.stopPropagation();editorArea.classList.add('drag-over');});
  editorArea.addEventListener('dragleave',function(e){e.preventDefault();e.stopPropagation();editorArea.classList.remove('drag-over');});
  editorArea.addEventListener('drop',function(e){
    e.preventDefault();e.stopPropagation();editorArea.classList.remove('drag-over');
    const files=e.dataTransfer.files;
    if(!files||!files.length)return;
    termLog(t('uploadingFiles')+' '+files.length+' (drag & drop)...','info');
    const formData=new FormData();
    for(let i=0;i<files.length;i++){
      const f=files[i];
      const relPath=f.webkitRelativePath||f.name;
      formData.append('files',f,relPath);
    }
    formData.append('device_id',generateDeviceId());
    fetch('/agent/upload-device-files',{method:'POST',body:formData}).then(r=>r.json()).then(d=>{
      if(d.error){termLog(t('uploadFailed')+': '+d.error,'error');return;}
      if(d.imported&&d.imported.length){d.imported.forEach(i=>termLog(t('uploadSuccess')+': '+i.name+' ('+i.size+' bytes)','success'));loadFileTree();}
      if(d.errors&&d.errors.length){d.errors.forEach(e=>termLog(t('uploadFailed')+': '+e.name+' - '+e.error,'error'));}
    }).catch(e=>termLog(t('uploadFailed')+': '+e.message,'error'));
  });
}

async function uploadDeviceFiles(event){
  if(isElectron){
    const isFolder = event && event.target && event.target.id === 'ideFolderInput';
    try{
      let result;
      if(isFolder){
        result = await window.kaguyaDesktop.dialog.openFolder({title: t('selectFolder')});
      } else {
        result = await window.kaguyaDesktop.dialog.openFile({title: t('selectFile'), multi: true});
      }
      if(result.canceled || !result.filePaths || !result.filePaths.length){
        termLog(t('noFilesSelected'),'info');
        return;
      }
      termLog(t('importingPaths')+' '+result.filePaths.length+' ...','info');
      const r=await fetch('/agent/import-files',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({paths:result.filePaths,device_id:generateDeviceId()})});
      const d=await r.json();
      if(d.error){termLog(t('importFailed')+': '+d.error,'error');return;}
      if(d.imported&&d.imported.length){d.imported.forEach(i=>termLog(t('importSuccess')+': '+i.src+' -> '+i.dst,'success'));loadFileTree();}
      if(d.errors&&d.errors.length){d.errors.forEach(e=>termLog(t('importFailed')+': '+e.path+' - '+e.error,'error'));}
      if(!d.imported||!d.imported.length)termLog(t('importFailed'),'error');
    }catch(e){termLog(t('importFailed')+': '+e.message,'error');}
    return;
  }
  const files=event.target.files;
  if(!files||!files.length){termLog(t('noFilesSelected'),'error');return;}
  termLog(t('uploadingFiles')+' '+files.length+' ...','info');
  const formData=new FormData();
  for(let i=0;i<files.length;i++){
    const f=files[i];
    const relPath=f.webkitRelativePath||f.name;
    formData.append('files',f,relPath);
  }
  formData.append('device_id',generateDeviceId());
  try{
    const r=await fetch('/agent/upload-device-files',{method:'POST',body:formData});
    const d=await r.json();
    if(d.error){termLog(t('uploadFailed')+': '+d.error,'error');return;}
    if(d.imported&&d.imported.length){d.imported.forEach(i=>termLog(t('uploadSuccess')+': '+i.name+' ('+i.size+' bytes)','success'));loadFileTree();}
    if(d.errors&&d.errors.length){d.errors.forEach(e=>termLog(t('uploadFailed')+': '+e.name+' - '+e.error,'error'));}
    if(!d.imported||!d.imported.length)termLog(t('uploadFailed'),'error');
  }catch(e){termLog(t('uploadFailed')+': '+e.message,'error');}
  event.target.value='';
}

async function importFilesFromHost(){
  if(isElectron){
    try{
      const result = await window.kaguyaDesktop.dialog.openFile({title: t('selectFile'), multi: true});
      if(result.canceled || !result.filePaths || !result.filePaths.length){
        termLog(t('noFilesSelected'),'info');
        return;
      }
      termLog(t('importingPaths')+' '+result.filePaths.length+' ...','info');
      const r=await fetch('/agent/import-files',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({paths:result.filePaths,device_id:generateDeviceId()})});
      const d=await r.json();
      if(d.error){termLog(t('importFailed')+': '+d.error,'error');return;}
      if(d.imported&&d.imported.length){d.imported.forEach(i=>termLog(t('importSuccess')+': '+i.src+' -> '+i.dst,'success'));loadFileTree();}
      if(d.errors&&d.errors.length){d.errors.forEach(e=>termLog(t('importFailed')+': '+e.path+' - '+e.error,'error'));}
      if(!d.imported||!d.imported.length)termLog(t('importFailed'),'error');
    }catch(e){termLog(t('importFailed')+': '+e.message,'error');}
    return;
  }
  const pathsStr=prompt(t('enterPaths'));
  if(!pathsStr||!pathsStr.trim())return;
  const paths=pathsStr.split(',').map(p=>p.trim()).filter(p=>p);
  if(!paths.length)return;
  termLog(t('importingPaths')+' '+paths.length+' ...','info');
  try{
    const r=await fetch('/agent/import-files',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({paths:paths,device_id:generateDeviceId()})});
    const d=await r.json();
    if(d.error){termLog(t('importFailed')+': '+d.error,'error');return;}
    if(d.imported&&d.imported.length){d.imported.forEach(i=>termLog(t('importSuccess')+': '+i.src+' -> '+i.dst,'success'));loadFileTree();}
    if(d.errors&&d.errors.length){d.errors.forEach(e=>termLog(t('importFailed')+': '+e.path+' - '+e.error,'error'));}
    if(!d.imported||!d.imported.length)termLog(t('importFailed'),'error');
  }catch(e){termLog(t('importFailed')+': '+e.message,'error');}
}

let permPanelEl=null;
function showPermPanel(){
  if(permPanelEl){permPanelEl.remove();permPanelEl=null;return;}
  permPanelEl=document.createElement('div');
  permPanelEl.id='permPanel';
  permPanelEl.style.cssText='position:fixed;top:0;right:0;width:380px;height:100%;background:var(--bg-1);border-left:1px solid var(--border);z-index:10000;display:flex;flex-direction:column;box-shadow:-8px 0 32px rgba(0,0,0,0.3);font-family:inherit;';
  permPanelEl.innerHTML='<div style="display:flex;align-items:center;padding:12px 16px;border-bottom:1px solid var(--border);gap:8px;"><span style="font-size:16px;">🛡️</span><span style="font-weight:700;color:var(--text);font-size:14px;">'+t('permPanel')+'</span><span style="flex:1;"></span><button onclick="permPanelEl.remove();permPanelEl=null;" style="background:none;border:none;color:var(--text-muted);cursor:pointer;font-size:14px;">✕</button></div><div id="permPanelContent" style="flex:1;overflow-y:auto;padding:12px 16px;"></div>';
  document.body.appendChild(permPanelEl);
  loadPermPanel();
}

async function loadPermPanel(){
  const content=document.getElementById('permPanelContent');
  if(!content)return;
  content.innerHTML='<div style="color:var(--text-muted);text-align:center;padding:20px;">Loading...</div>';
  try{
    const [configRes,statsRes]=await Promise.all([fetch('/agent/permission/config'),fetch('/agent/audit/stats')]);
    const config=await configRes.json();
    const stats=await statsRes.json();
    let html='';
    html+='<div style="margin-bottom:16px;"><div style="font-size:11px;font-weight:700;color:var(--accent2);text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">'+t('sandboxMode')+'</div>';
    html+='<label style="display:flex;align-items:center;gap:8px;padding:8px 10px;background:var(--bg-2);border-radius:var(--radius-sm);cursor:pointer;font-size:11px;color:var(--text);">';
    html+='<input type="checkbox" id="permSandboxToggle" '+(config.sandbox_mode?'checked':'')+' onchange="toggleSandboxMode(this.checked)" style="width:14px;height:14px;">';
    html+=t('sandboxMode')+' <span style="color:var(--text-muted);font-size:9px;">('+(config.sandbox_mode?'ON':'OFF')+')</span></label></div>';
    html+='<div style="margin-bottom:16px;"><div style="font-size:11px;font-weight:700;color:var(--accent2);text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">'+t('sandboxDirs')+'</div>';
    if(config.sandbox_dirs&&config.sandbox_dirs.length){
      config.sandbox_dirs.forEach(function(d){
        html+='<div style="display:flex;align-items:center;gap:6px;padding:6px 10px;background:var(--bg-2);border-radius:var(--radius-sm);margin-bottom:4px;">';
        html+='<span style="font-size:10px;color:var(--text);flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="'+esc(d)+'">'+esc(d)+'</span>';
        html+='<button onclick="removeSandboxDir(\''+esc(d).replace(/'/g,"\\'")+'\')" style="background:none;border:none;color:var(--error);cursor:pointer;font-size:10px;">✕</button></div>';
      });
    }else{
      html+='<div style="font-size:10px;color:var(--text-muted);padding:6px 0;">'+t('noSandboxDirs')+'</div>';
    }
    html+='<div style="display:flex;gap:4px;margin-top:6px;"><input id="newSandboxDir" placeholder="C:\\path\\to\\dir" style="flex:1;padding:5px 8px;background:var(--bg-0);border:1px solid var(--border);border-radius:4px;color:var(--text);font-size:10px;font-family:inherit;outline:none;"><button onclick="addSandboxDir()" style="padding:5px 10px;background:var(--accent);color:#fff;border:none;border-radius:4px;font-size:10px;cursor:pointer;">'+t('addSandboxDir')+'</button></div></div>';
    html+='<div style="margin-bottom:16px;"><div style="font-size:11px;font-weight:700;color:var(--accent2);text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">'+t('permRules')+'</div>';
    if(config.always_allow&&config.always_allow.length){
      html+='<div style="font-size:9px;color:var(--success);margin-bottom:4px;">✓ Always Allow:</div>';
      config.always_allow.forEach(function(tool){
        html+='<div style="display:flex;align-items:center;gap:6px;padding:4px 10px;background:rgba(52,211,153,0.06);border-radius:var(--radius-sm);margin-bottom:3px;">';
        html+='<span style="font-size:10px;color:var(--success);flex:1;">'+esc(tool)+'</span>';
        html+='<button onclick="removePermRule(\''+esc(tool)+'\')" style="background:none;border:none;color:var(--text-muted);cursor:pointer;font-size:9px;">✕</button></div>';
      });
    }
    if(config.always_deny&&config.always_deny.length){
      html+='<div style="font-size:9px;color:var(--error);margin-bottom:4px;margin-top:6px;">✗ Always Deny:</div>';
      config.always_deny.forEach(function(tool){
        html+='<div style="display:flex;align-items:center;gap:6px;padding:4px 10px;background:rgba(248,113,113,0.06);border-radius:var(--radius-sm);margin-bottom:3px;">';
        html+='<span style="font-size:10px;color:var(--error);flex:1;">'+esc(tool)+'</span>';
        html+='<button onclick="removePermRule(\''+esc(tool)+'\')" style="background:none;border:none;color:var(--text-muted);cursor:pointer;font-size:9px;">✕</button></div>';
      });
    }
    html+='<div style="display:flex;gap:4px;margin-top:6px;"><select id="newRuleTool" style="flex:1;padding:5px 8px;background:var(--bg-0);border:1px solid var(--border);border-radius:4px;color:var(--text);font-size:10px;font-family:inherit;">';
    ['write_file','edit_file','execute_command','compile','create_directory','agent_spawn'].forEach(function(tn){html+='<option value="'+tn+'">'+tn+'</option>';});
    html+='</select><select id="newRuleBehavior" style="padding:5px 8px;background:var(--bg-0);border:1px solid var(--border);border-radius:4px;color:var(--text);font-size:10px;font-family:inherit;"><option value="allow">'+t('allow')+'</option><option value="deny">'+t('deny')+'</option></select>';
    html+='<button onclick="addPermRule()" style="padding:5px 10px;background:var(--accent);color:#fff;border:none;border-radius:4px;font-size:10px;cursor:pointer;">+</button></div></div>';
    html+='<div style="margin-bottom:16px;"><div style="font-size:11px;font-weight:700;color:var(--accent2);text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">'+t('dangerousCmds')+'</div>';
    html+='<label style="display:flex;align-items:center;gap:8px;padding:8px 10px;background:var(--bg-2);border-radius:var(--radius-sm);cursor:pointer;font-size:11px;color:var(--text);">';
    html+='<input type="checkbox" id="permDangerousToggle" '+(config.dangerous_commands_allowed?'checked':'')+' onchange="toggleDangerousCmds(this.checked)" style="width:14px;height:14px;">';
    html+=t('dangerousCmds')+' <span style="color:var(--text-muted);font-size:9px;">(sudo, runas, chmod 777)</span></label></div>';
    html+='<div style="margin-bottom:16px;"><div style="font-size:11px;font-weight:700;color:var(--accent2);text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">'+t('auditStats')+'</div>';
    html+='<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px;">';
    html+='<div style="padding:8px;background:var(--bg-2);border-radius:var(--radius-sm);text-align:center;"><div style="font-size:16px;font-weight:700;color:var(--text);">'+(stats.total||0)+'</div><div style="font-size:9px;color:var(--text-muted);">'+t('totalOps')+'</div></div>';
    html+='<div style="padding:8px;background:var(--bg-2);border-radius:var(--radius-sm);text-align:center;"><div style="font-size:16px;font-weight:700;color:var(--success);">'+(stats.allowed||0)+'</div><div style="font-size:9px;color:var(--text-muted);">'+t('allowedOps')+'</div></div>';
    html+='<div style="padding:8px;background:var(--bg-2);border-radius:var(--radius-sm);text-align:center;"><div style="font-size:16px;font-weight:700;color:var(--error);">'+(stats.denied||0)+'</div><div style="font-size:9px;color:var(--text-muted);">'+t('deniedOps')+'</div></div>';
    html+='</div></div>';
    html+='<div><div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;"><span style="font-size:11px;font-weight:700;color:var(--accent2);text-transform:uppercase;letter-spacing:1px;">'+t('auditLog')+'</span><button onclick="loadAuditLogDetail()" style="padding:3px 8px;background:var(--bg-3);border:1px solid var(--border);border-radius:4px;color:var(--text-dim);font-size:9px;cursor:pointer;">↻ Refresh</button></div>';
    html+='<div id="auditLogList" style="max-height:200px;overflow-y:auto;"></div></div>';
    content.innerHTML=html;
    loadAuditLogDetail();
  }catch(e){
    content.innerHTML='<div style="color:var(--error);padding:20px;">Error: '+e.message+'</div>';
  }
}

async function loadAuditLogDetail(){
  const list=document.getElementById('auditLogList');
  if(!list)return;
  try{
    const r=await fetch('/agent/audit/logs?limit=30');
    const d=await r.json();
    if(!d.logs||!d.logs.length){list.innerHTML='<div style="font-size:10px;color:var(--text-muted);">No audit logs</div>';return;}
    list.innerHTML=d.logs.map(function(e){
      const ts=e.timestamp?e.timestamp.split('T')[1].split('.')[0]:'';
      const color=e.allowed?'var(--success)':'var(--error)';
      const icon=e.allowed?'✓':'✗';
      return '<div style="display:flex;align-items:center;gap:6px;padding:4px 6px;border-bottom:1px solid var(--border);font-size:9px;">'
        +'<span style="color:'+color+';font-weight:700;">'+icon+'</span>'
        +'<span style="color:var(--text-muted);min-width:55px;">'+ts+'</span>'
        +'<span style="color:var(--text);flex:1;">'+esc(e.tool||'')+'</span>'
        +'<span style="color:var(--text-muted);max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">'+esc((e.details&&e.details.reason)||'')+'</span></div>';
    }).join('');
  }catch(e){list.innerHTML='<div style="color:var(--error);font-size:10px;">Error loading logs</div>';}
}

async function toggleSandboxMode(enabled){
  await fetch('/agent/permission/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sandbox_mode:enabled})});
  loadPermPanel();
}

async function toggleDangerousCmds(enabled){
  await fetch('/agent/permission/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({dangerous_commands_allowed:enabled})});
  loadPermPanel();
}

async function addSandboxDir(){
  const input=document.getElementById('newSandboxDir');
  const path=input.value.trim();
  if(!path)return;
  const r=await fetch('/agent/permission/sandbox-dir',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:path})});
  const d=await r.json();
  if(d.error){alert(d.error);return;}
  loadPermPanel();
}

async function removeSandboxDir(path){
  await fetch('/agent/permission/sandbox-dir',{method:'DELETE',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:path})});
  loadPermPanel();
}

async function addPermRule(){
  const tool=document.getElementById('newRuleTool').value;
  const behavior=document.getElementById('newRuleBehavior').value;
  await fetch('/agent/permission/rule',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tool_name:tool,behavior:behavior})});
  loadPermPanel();
}

async function removePermRule(tool){
  await fetch('/agent/permission/rule',{method:'DELETE',headers:{'Content-Type':'application/json'},body:JSON.stringify({tool_name:tool,behavior:'allow'})});
  loadPermPanel();
}

let taskPanelEl=null;
function showTaskPanel(){
  if(taskPanelEl){taskPanelEl.remove();taskPanelEl=null;return;}
  taskPanelEl=document.createElement('div');
  taskPanelEl.id='taskPanel';
  taskPanelEl.style.cssText='position:fixed;top:0;right:0;width:400px;height:100%;background:var(--bg-1);border-left:1px solid var(--border);z-index:10000;display:flex;flex-direction:column;box-shadow:-8px 0 32px rgba(0,0,0,0.3);font-family:inherit;animation:slideInRight .2s ease-out;';
  taskPanelEl.innerHTML=`
    <div style="display:flex;align-items:center;padding:14px 18px;border-bottom:1px solid var(--border);gap:10px;background:linear-gradient(135deg,rgba(124,106,255,0.08),rgba(6,182,212,0.05));">
      <span style="font-size:18px;">📋</span>
      <span style="font-weight:700;color:var(--text);font-size:15px;letter-spacing:0.02em;">多任务管理</span>
      <span style="flex:1;"></span>
      <button onclick="taskPanelEl.remove();taskPanelEl=null;" style="background:none;border:none;color:var(--text-muted);cursor:pointer;font-size:16px;padding:4px 6px;border-radius:6px;transition:var(--transition);" onmouseover="this.style.background='var(--bg-hover)';this.style.color='var(--error)'" onmouseout="this.style.background='none';this.style.color='var(--text-muted)'">✕</button>
    </div>
    <div id="taskPanelContent" style="flex:1;overflow-y:auto;padding:14px 18px;"></div>
    <div style="padding:10px 18px;border-top:1px solid var(--border);display:flex;gap:6px;flex-shrink:0;">
      <input id="newTaskTitle" placeholder="输入任务名称..." style="flex:1;padding:8px 12px;background:var(--bg-0);border:1px solid var(--border);border-radius:8px;color:var(--text);font-size:11px;font-family:inherit;outline:none;transition:var(--transition);" onfocus="this.style.borderColor='var(--accent)'" onblur="this.style.borderColor='var(--border)'">
      <select id="newTaskPriority" style="padding:8px 10px;background:var(--bg-0);border:1px solid var(--border);border-radius:8px;color:var(--text);font-size:10px;font-family:inherit;cursor:pointer;">
        <option value="critical">🔴 紧急</option>
        <option value="high">🟠 高</option>
        <option value="medium" selected>🟡 中</option>
        <option value="low">🟢 低</option>
      </select>
      <button onclick="createTaskFromPanel()" style="padding:8px 14px;background:var(--grad);color:#fff;border:none;border-radius:8px;font-size:12px;cursor:pointer;font-weight:600;transition:var(--transition);box-shadow:0 2px 8px rgba(124,106,255,0.3);" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">+ 创建</button>
    </div>`;
  document.body.appendChild(taskPanelEl);
  loadTaskPanel();
}

async function loadTaskPanel(){
  const content=document.getElementById('taskPanelContent');
  if(!content)return;
  content.innerHTML='<div style="color:var(--text-muted);text-align:center;padding:30px;"><div style="font-size:24px;animation:pulse 1.5s infinite;">⏳</div><div style="margin-top:8px;font-size:11px;">加载中...</div></div>';
  try{
    const r=await fetch('/agent/tasks');
    const d=await r.json();
    const stats=d.stats||{};
    const tasks=d.tasks||[];
    let html='';
    html+='<div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:6px;margin-bottom:16px;">';
    const statCards=[
      {label:'总计',value:stats.total||0,color:'var(--accent)',icon:'📊'},
      {label:'进行中',value:(stats.by_status||{}).in_progress||0,color:'var(--warning)',icon:'🔄'},
      {label:'已完成',value:(stats.by_status||{}).done||0,color:'var(--success)',icon:'✅'},
      {label:'已失败',value:(stats.by_status||{}).failed||0,color:'var(--error)',icon:'❌'}
    ];
    statCards.forEach(function(s){
      html+='<div style="padding:10px 8px;background:linear-gradient(135deg,'+s.color+'12,'+s.color+'05);border:1px solid '+s.color+'30;border-radius:10px;text-align:center;">';
      html+='<div style="font-size:10px;margin-bottom:2px;">'+s.icon+'</div>';
      html+='<div style="font-size:18px;font-weight:800;color:'+s.color+';">'+s.value+'</div>';
      html+='<div style="font-size:8px;color:var(--text-muted);margin-top:2px;">'+s.label+'</div>';
      html+='</div>';
    });
    html+='</div>';
    if(tasks.length===0){
      html+='<div style="text-align:center;padding:40px 20px;">';
      html+='<div style="font-size:36px;margin-bottom:12px;opacity:0.3;">📋</div>';
      html+='<div style="color:var(--text-muted);font-size:12px;margin-bottom:4px;">暂无任务</div>';
      html+='<div style="color:var(--text-dim);font-size:10px;">在下方输入框创建新任务，或在对话中使用 /task 命令</div>';
      html+='</div>';
    }else{
      const statusIcons={pending:'⏳',in_progress:'🔄',done:'✅',failed:'❌'};
      const statusLabels={pending:'等待中',in_progress:'进行中',done:'已完成',failed:'已失败'};
      const statusColors={pending:'var(--warning)',in_progress:'var(--cyan)',done:'var(--success)',failed:'var(--error)'};
      const statusBg={pending:'rgba(251,191,36,0.08)',in_progress:'rgba(6,182,212,0.08)',done:'rgba(52,211,153,0.08)',failed:'rgba(248,113,113,0.08)'};
      const prioLabels={0:'🔴',1:'🟠',2:'🟡',3:'🟢'};
      tasks.forEach(function(task){
        const isActive=stats.active===task.id;
        const age=Math.round((Date.now()/1000-task.created_at)/60);
        const ageStr=age<1?'刚刚':age<60?age+'分钟前':Math.round(age/60)+'小时前';
        html+='<div style="padding:12px;background:'+statusBg[task.status]+';border-radius:12px;margin-bottom:8px;border:1px solid '+(isActive?'var(--accent)':'var(--border)')+';'+(isActive?'box-shadow:0 0 0 1px var(--accent),0 2px 12px rgba(124,106,255,0.15);':'transition:var(--transition);')+'" onmouseover="if(!'+isActive+')this.style.borderColor=\'var(--accent)\'" onmouseout="if(!'+isActive+')this.style.borderColor=\'var(--border)\'">';
        html+='<div style="display:flex;align-items:center;gap:8px;">';
        html+='<span style="font-size:14px;">'+(statusIcons[task.status]||'❓')+'</span>';
        html+='<span style="font-size:10px;">'+(prioLabels[task.priority]||'🟡')+'</span>';
        html+='<span style="flex:1;font-size:12px;color:var(--text);font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">'+esc(task.title)+'</span>';
        html+='<span style="font-size:8px;color:var(--text-muted);background:var(--bg-2);padding:2px 6px;border-radius:4px;">'+ageStr+'</span>';
        html+='</div>';
        if(task.description){html+='<div style="font-size:10px;color:var(--text-muted);margin-top:6px;padding-left:28px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">'+esc(task.description)+'</div>';}
        if(task.progress>0&&task.progress<100){html+='<div style="margin-top:8px;height:4px;background:var(--bg-0);border-radius:4px;overflow:hidden;"><div style="width:'+task.progress+'%;height:100%;background:linear-gradient(90deg,var(--cyan),var(--accent));border-radius:4px;transition:width 0.3s ease;"></div></div><div style="font-size:8px;color:var(--text-muted);margin-top:2px;text-align:right;">'+task.progress+'%</div>';}
        html+='<div style="display:flex;gap:4px;margin-top:8px;flex-wrap:wrap;">';
        html+='<span style="font-size:8px;padding:2px 8px;background:'+statusBg[task.status]+';color:'+statusColors[task.status]+';border-radius:4px;border:1px solid '+statusColors[task.status]+'30;">'+(statusLabels[task.status]||task.status)+'</span>';
        if(task.status==='pending'){html+='<button onclick="updateTaskFromPanel(\''+task.id+'\',\'in_progress\')" style="padding:3px 10px;background:var(--cyan);color:#0a0a0f;border:none;border-radius:6px;font-size:9px;cursor:pointer;font-weight:600;transition:var(--transition);" onmouseover="this.style.transform=\'scale(1.05)\'" onmouseout="this.style.transform=\'scale(1)\'">▶ 开始</button>';}
        if(task.status==='in_progress'){html+='<button onclick="updateTaskFromPanel(\''+task.id+'\',\'done\')" style="padding:3px 10px;background:var(--success);color:#0a0a0f;border:none;border-radius:6px;font-size:9px;cursor:pointer;font-weight:600;transition:var(--transition);" onmouseover="this.style.transform=\'scale(1.05)\'" onmouseout="this.style.transform=\'scale(1)\'">✓ 完成</button>';}
        if(task.status!=='done'&&task.status!=='failed'){html+='<button onclick="updateTaskFromPanel(\''+task.id+'\',\'failed\')" style="padding:3px 10px;background:transparent;color:var(--error);border:1px solid var(--error);border-radius:6px;font-size:9px;cursor:pointer;font-weight:600;transition:var(--transition);" onmouseover="this.style.background=\'var(--error)\';this.style.color=\'#fff\'" onmouseout="this.style.background=\'transparent\';this.style.color=\'var(--error)\'">✕ 取消</button>';}
        if(!isActive&&task.status!=='done'&&task.status!=='failed'){html+='<button onclick="activateTaskFromPanel(\''+task.id+'\')" style="padding:3px 10px;background:var(--accent);color:#fff;border:none;border-radius:6px;font-size:9px;cursor:pointer;font-weight:600;transition:var(--transition);" onmouseover="this.style.transform=\'scale(1.05)\'" onmouseout="this.style.transform=\'scale(1)\'">🎯 聚焦</button>';}
        html+='</div></div>';
      });
    }
    content.innerHTML=html;
  }catch(e){
    content.innerHTML='<div style="color:var(--error);padding:20px;text-align:center;"><div style="font-size:24px;margin-bottom:8px;">⚠️</div><div>加载失败: '+esc(e.message)+'</div><button onclick="loadTaskPanel()" style="margin-top:12px;padding:6px 16px;background:var(--accent);color:#fff;border:none;border-radius:6px;cursor:pointer;">重试</button></div>';
  }
}

async function createTaskFromPanel(){
  const title=document.getElementById('newTaskTitle').value.trim();
  if(!title)return;
  const priority=document.getElementById('newTaskPriority').value;
  document.getElementById('newTaskTitle').value='';
  await fetch('/agent/tasks',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title:title,priority:priority})});
  loadTaskPanel();
}

async function updateTaskFromPanel(taskId,status){
  await fetch('/agent/tasks/'+taskId,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({status:status})});
  loadTaskPanel();
}

async function activateTaskFromPanel(taskId){
  await fetch('/agent/tasks/'+taskId+'/activate',{method:'POST',headers:{'Content-Type':'application/json'}});
  loadTaskPanel();
}

let browserPanelEl=null;
function showBrowserPanel(){
  if(browserPanelEl){browserPanelEl.remove();browserPanelEl=null;return;}
  browserPanelEl=document.createElement('div');
  browserPanelEl.id='browserPanel';
  browserPanelEl.style.cssText='position:fixed;top:0;right:0;width:420px;height:100%;background:var(--bg-1);border-left:1px solid var(--border);z-index:10000;display:flex;flex-direction:column;box-shadow:-8px 0 32px rgba(0,0,0,0.3);font-family:inherit;animation:slideInRight .2s ease-out;';
  browserPanelEl.innerHTML='<div style="display:flex;align-items:center;padding:12px 16px;border-bottom:1px solid var(--border);gap:8px;"><span style="font-size:16px;">🌐</span><span style="font-weight:700;color:var(--text);font-size:14px;">浏览器集成</span><span style="flex:1;"></span><button onclick="browserPanelEl.remove();browserPanelEl=null;" style="background:none;border:none;color:var(--text-muted);cursor:pointer;font-size:14px;">✕</button></div><div id="browserPanelContent" style="flex:1;overflow-y:auto;padding:12px 16px;"></div>';
  document.body.appendChild(browserPanelEl);
  loadBrowserPanel();
}

function loadBrowserPanel(){
  const content=document.getElementById('browserPanelContent');
  if(!content)return;
  content.innerHTML='<div style="margin-bottom:16px;"><div style="font-size:11px;font-weight:700;color:var(--accent2);text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">🔍 Web Search</div><div style="display:flex;gap:4px;"><input id="browserSearchInput" placeholder="Search the web..." style="flex:1;padding:6px 8px;background:var(--bg-0);border:1px solid var(--border);border-radius:4px;color:var(--text);font-size:10px;font-family:inherit;outline:none;" onkeydown="if(event.key===\'Enter\')doBrowserSearch()"><button onclick="doBrowserSearch()" style="padding:6px 12px;background:var(--cyan);color:#0a0a0f;border:none;border-radius:4px;font-size:10px;cursor:pointer;font-weight:600;">Search</button></div><div id="browserSearchResults" style="margin-top:8px;"></div></div><div style="margin-bottom:16px;"><div style="font-size:11px;font-weight:700;color:var(--accent2);text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">📄 Fetch URL</div><div style="display:flex;gap:4px;"><input id="browserFetchInput" placeholder="https://example.com" style="flex:1;padding:6px 8px;background:var(--bg-0);border:1px solid var(--border);border-radius:4px;color:var(--text);font-size:10px;font-family:inherit;outline:none;" onkeydown="if(event.key===\'Enter\')doBrowserFetch()"><button onclick="doBrowserFetch()" style="padding:6px 12px;background:var(--accent);color:#fff;border:none;border-radius:4px;font-size:10px;cursor:pointer;font-weight:600;">Fetch</button></div><div id="browserFetchResults" style="margin-top:8px;"></div></div><div style="margin-bottom:16px;"><div style="font-size:11px;font-weight:700;color:var(--accent2);text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">📂 Open Project / URL</div><div style="display:flex;gap:4px;"><input id="browserOpenInput" placeholder="Path or URL..." style="flex:1;padding:6px 8px;background:var(--bg-0);border:1px solid var(--border);border-radius:4px;color:var(--text);font-size:10px;font-family:inherit;outline:none;" onkeydown="if(event.key===\'Enter\')doBrowserOpen()"><button onclick="doBrowserOpen()" style="padding:6px 12px;background:var(--success);color:#0a0a0f;border:none;border-radius:4px;font-size:10px;cursor:pointer;font-weight:600;">Open</button></div></div>';
}

async function doBrowserSearch(){
  const query=document.getElementById('browserSearchInput').value.trim();
  if(!query)return;
  const resultsEl=document.getElementById('browserSearchResults');
  resultsEl.innerHTML='<div style="color:var(--text-muted);font-size:10px;">Searching...</div>';
  try{
    const r=await fetch('/agent/browser/search',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query:query,max_results:5})});
    const d=await r.json();
    const results=d.results||[];
    if(!results.length||results[0].error){resultsEl.innerHTML='<div style="color:var(--error);font-size:10px;">No results or error: '+(results[0]?results[0].error:'unknown')+'</div>';return;}
    resultsEl.innerHTML=results.map(function(r){
      return '<div style="padding:6px 8px;background:var(--bg-2);border-radius:var(--radius-sm);margin-bottom:4px;cursor:pointer;" onclick="document.getElementById(\'browserFetchInput\').value=\''+esc(r.url).replace(/'/g,"\\'")+'\';doBrowserFetch();"><div style="font-size:10px;color:var(--cyan);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">'+esc(r.title)+'</div><div style="font-size:8px;color:var(--text-muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">'+esc(r.url)+'</div>'+(r.snippet?'<div style="font-size:9px;color:var(--text-dim);margin-top:2px;">'+esc(r.snippet.substring(0,120))+'</div>':'')+'</div>';
    }).join('');
  }catch(e){resultsEl.innerHTML='<div style="color:var(--error);font-size:10px;">Error: '+e.message+'</div>';}
}

async function doBrowserFetch(){
  const url=document.getElementById('browserFetchInput').value.trim();
  if(!url)return;
  const resultsEl=document.getElementById('browserFetchResults');
  resultsEl.innerHTML='<div style="color:var(--text-muted);font-size:10px;">Fetching...</div>';
  try{
    const r=await fetch('/agent/browser/fetch',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:url,format:'markdown'})});
    const d=await r.json();
    if(d.error){resultsEl.innerHTML='<div style="color:var(--error);font-size:10px;">Error: '+esc(d.error)+'</div>';return;}
    const content=(d.content||'').substring(0,3000);
    resultsEl.innerHTML='<div style="background:var(--bg-2);border-radius:var(--radius-sm);padding:8px;max-height:300px;overflow-y:auto;">'+(d.title?'<div style="font-size:11px;font-weight:700;color:var(--text);margin-bottom:4px;">'+esc(d.title)+'</div>':'')+'<pre style="font-size:9px;color:var(--text-dim);white-space:pre-wrap;word-break:break-all;font-family:inherit;margin:0;">'+esc(content)+'</pre></div>';
  }catch(e){resultsEl.innerHTML='<div style="color:var(--error);font-size:10px;">Error: '+e.message+'</div>';}
}

async function doBrowserOpen(){
  const target=document.getElementById('browserOpenInput').value.trim();
  if(!target)return;
  try{
    const r=await fetch('/agent/browser/open',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:target})});
    const d=await r.json();
    if(d.error){alert(d.error);}else{termLog('Opened: '+target,'success');}
  }catch(e){termLog('Error: '+e.message,'error');}
}

async function importEnvFromHost(){
  termLog(t('importEnv')+'...','info');
  try{
    const r=await fetch('/agent/import-env',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({device_id:generateDeviceId()})});
    const d=await r.json();
    if(d.success){termLog(t('envImported')+'! Python: '+(d.python_version||'N/A')+', Packages: '+d.package_count,'success');termLog('Env file: '+d.env_file,'info');termLog('Requirements: '+d.requirements_file,'info');loadFileTree();}
    else{termLog(t('envImportFailed')+': '+(d.error||'Unknown'),'error');}
  }catch(e){termLog(t('envImportFailed')+': '+e.message,'error');}
}

async function showProjectList(){
  try{
    const r=await fetch('/workspace/projects?refresh=true');
    const d=await r.json();
    if(!d.success||!d.projects||!d.projects.length){
      termLog('No projects found in workspace','info');
      return;
    }
    const existing=document.getElementById('projectListModal');
    if(existing)existing.remove();
    const modal=document.createElement('div');
    modal.id='projectListModal';
    modal.style.cssText='position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(10,10,15,0.85);z-index:10000;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(8px);';
    const listHtml=d.projects.map(function(p){
      const statusIcon=p.running?'🟢':(p.exists?'⚪':'🔴');
      const kindIcon={'python':'🐍','node':'📦','java':'☕','rust':'🦀'}[p.kind]||'📁';
      return '<div style="padding:10px 14px;border:1px solid var(--border);border-radius:8px;margin-bottom:6px;cursor:pointer;transition:all 0.2s;background:var(--bg-2);display:flex;align-items:center;gap:10px;" onmouseover="this.style.borderColor=\'var(--accent)\'" onmouseout="this.style.borderColor=\'var(--border)\'" onclick="runProjectFromList(\''+esc(p.id).replace(/'/g,"\\'")+'\',\''+esc(p.path).replace(/'/g,"\\'")+'\',\''+esc(p.start_command).replace(/'/g,"\\'")+'\')">'+
        '<span style="font-size:14px;">'+statusIcon+'</span>'+
        '<div style="flex:1;min-width:0;">'+
          '<div style="font-size:11px;font-weight:600;color:var(--text);display:flex;align-items:center;gap:4px;">'+kindIcon+' '+esc(p.name)+'</div>'+
          '<div style="font-size:9px;color:var(--text-muted);margin-top:2px;">'+esc(p.start_command||'No start command')+' · '+esc(p.kind||'unknown')+'</div>'+
        '</div>'+
        '<span style="font-size:9px;padding:2px 8px;border-radius:4px;background:'+(p.running?'rgba(52,211,153,0.15);color:var(--success)':'var(--bg-1);color:var(--text-muted)')+';">'+(p.running?'Running':'Start')+'</span>'+
      '</div>';
    }).join('');
    modal.innerHTML='<div style="width:420px;max-height:70vh;overflow-y:auto;background:var(--bg-0);border:1px solid var(--border);border-radius:14px;padding:20px;box-shadow:0 16px 64px rgba(0,0,0,0.5);">'+
      '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;">'+
        '<h3 style="font-size:14px;color:var(--text);font-weight:700;">▶ Run Project</h3>'+
        '<span onclick="document.getElementById(\'projectListModal\').remove()" style="cursor:pointer;color:var(--text-muted);font-size:16px;padding:4px;">✕</span>'+
      '</div>'+
      listHtml+
    '</div>';
    document.body.appendChild(modal);
    modal.onclick=function(e){if(e.target===modal)modal.remove();};
  }catch(e){termLog('Failed to load projects: '+e.message,'error');}
}
async function runProjectFromList(projectId,projectPath,startCommand){
  const modal=document.getElementById('projectListModal');
  if(modal)modal.remove();
  termLog('Starting project...','info');
  const tp=document.getElementById('bottomPanel');
  if(tp){tp.style.display='flex';switchBottomTab('terminal');}
  try{
    const r=await fetch('/agent/run-project',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({project_id:projectId,path:projectPath,start_command:startCommand,device_id:generateDeviceId()})});
    const d=await r.json();
    if(d.error){termLog('Error: '+d.error,'error');return;}
    termLog('Project started (PID: '+d.pid+')','success');
    termLog('Command: '+d.start_command,'info');
    if(d.initial_output){termLog(d.initial_output,'success');}
    showOperationFeedback('run_project',{path:projectPath},'success');
  }catch(e){termLog('Failed to start project: '+e.message,'error');}
}
async function browseHostDirs(){
  if(isElectron){
    try{
      const result = await window.kaguyaDesktop.dialog.openFolder({title: t('browseDir')});
      if(result.canceled || !result.filePaths || !result.filePaths.length){
        return;
      }
      const selectedPath = result.filePaths[0];
      termLog(t('importingPaths')+' '+selectedPath+' ...','info');
      const r=await fetch('/agent/import-files',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({paths:[selectedPath],device_id:generateDeviceId()})});
      const d=await r.json();
      if(d.error){termLog(t('importFailed')+': '+d.error,'error');return;}
      if(d.imported&&d.imported.length){d.imported.forEach(i=>termLog(t('importSuccess')+': '+i.src+' -> '+i.dst,'success'));loadFileTree();}
      if(d.errors&&d.errors.length){d.errors.forEach(e=>termLog(t('importFailed')+': '+e.path+' - '+e.error,'error'));}
    }catch(e){termLog('Browse failed: '+e.message,'error');}
    return;
  }
  const startPath=prompt(t('enterPath'),'');
  try{
    const r=await fetch('/agent/browsable-dirs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:startPath||''})});
    const d=await r.json();
    if(d.error){termLog('Browse error: '+d.error,'error');return;}
    let html='<div style="padding:8px;background:var(--bg-2);border:1px solid var(--border);border-radius:6px;margin:4px 0;max-height:250px;overflow-y:auto;">';
    html+='<div style="font-size:10px;font-weight:700;color:var(--cyan);margin-bottom:4px;">'+esc(d.path)+'</div>';
    if(d.parent)html+='<div style="cursor:pointer;padding:2px 4px;font-size:10px;color:var(--text-muted);" onclick="browseHostDirsAt(\''+esc(d.parent).replace(/'/g,"\\'")+'\')">..</div>';
    d.entries.forEach(e=>{
      if(e.is_dir)html+='<div style="cursor:pointer;padding:2px 4px;font-size:10px;color:var(--text);" onclick="browseHostDirsAt(\''+esc(e.path).replace(/'/g,"\\'")+'\')">'+esc(e.name)+'/</div>';
      else html+='<div style="cursor:pointer;padding:2px 4px;font-size:10px;color:var(--text-muted);" onclick="importSinglePath(\''+esc(e.path).replace(/'/g,"\\'")+'\')">'+esc(e.name)+'</div>';
    });
    html+='</div>';termLog(html,'html');
  }catch(e){termLog('Browse failed: '+e.message,'error');}
}

async function browseHostDirsAt(path){
  try{
    const r=await fetch('/agent/browsable-dirs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:path})});
    const d=await r.json();
    if(d.error){termLog('Browse error: '+d.error,'error');return;}
    let html='<div style="padding:8px;background:var(--bg-2);border:1px solid var(--border);border-radius:6px;margin:4px 0;max-height:250px;overflow-y:auto;">';
    html+='<div style="font-size:10px;font-weight:700;color:var(--cyan);margin-bottom:4px;">'+esc(d.path)+'</div>';
    if(d.parent)html+='<div style="cursor:pointer;padding:2px 4px;font-size:10px;color:var(--text-muted);" onclick="browseHostDirsAt(\''+esc(d.parent).replace(/'/g,"\\'")+'\')">..</div>';
    d.entries.forEach(e=>{
      if(e.is_dir)html+='<div style="cursor:pointer;padding:2px 4px;font-size:10px;color:var(--text);" onclick="browseHostDirsAt(\''+esc(e.path).replace(/'/g,"\\'")+'\')">'+esc(e.name)+'/</div>';
      else html+='<div style="cursor:pointer;padding:2px 4px;font-size:10px;color:var(--text-muted);" onclick="importSinglePath(\''+esc(e.path).replace(/'/g,"\\'")+'\')">'+esc(e.name)+'</div>';
    });
    html+='</div>';termLog(html,'html');
  }catch(e){termLog('Browse failed: '+e.message,'error');}
}

async function importSinglePath(path){
  termLog(t('importingPaths')+' '+path,'info');
  try{
    const r=await fetch('/agent/import-files',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({paths:[path],device_id:generateDeviceId()})});
    const d=await r.json();
    if(d.imported&&d.imported.length){termLog(t('importSuccess')+': '+path,'success');loadFileTree();}
    else if(d.errors&&d.errors.length){termLog(t('importFailed')+': '+d.errors[0].error,'error');}
  }catch(e){termLog(t('importFailed')+': '+e.message,'error');}
}
