const { app, BrowserWindow, Menu, Tray, shell, dialog, ipcMain, nativeTheme, safeStorage } = require('electron');
const path = require('path');
const { spawn, exec, execFile } = require('child_process');
const fs = require('fs');
const os = require('os');
const net = require('net');
const crypto = require('crypto');

let autoUpdater = null;
try {
    const updaterModule = require('electron-updater');
    autoUpdater = updaterModule.autoUpdater;
    console.log('[Updater] electron-updater loaded successfully');
} catch (e) {
    console.log('[Updater] electron-updater not available, auto-update disabled');
    autoUpdater = {
        on: () => {},
        checkForUpdates: () => Promise.resolve({ success: false, error: 'not available' }),
        checkForUpdatesAndNotify: () => Promise.resolve(),
        downloadProgress: null,
        quitAndInstall: () => {}
    };
}

const APP_NAME = 'Kaguya IDE';
const APP_VERSION = '3.1.0';
const DEFAULT_PORT = 58000;
const KAGUYA_DATA_DIR = path.join(os.homedir(), '.kaguya');
const DEVICE_VAULT_PATH = path.join(KAGUYA_DATA_DIR, 'device_vault.enc');
const DEVICE_IDENTITY_PATH = path.join(KAGUYA_DATA_DIR, 'device_identity.json');

// ========== Device Fingerprint & Secure Storage ==========

function generateDeviceFingerprint() {
    const components = [
        os.hostname(),
        os.userInfo().username,
        process.platform,
        process.arch,
        String(os.cpus().length),
        String(Math.floor(os.totalmem() / (1024 * 1024))),
        os.cpus()[0]?.model || 'unknown',
    ];
    const raw = components.join('|');
    const hash = crypto.createHash('sha256').update(raw).digest('hex');
    return 'dev_' + hash.substring(0, 16);
}

function getDeviceIdentity() {
    try {
        if (fs.existsSync(DEVICE_IDENTITY_PATH)) {
            const data = JSON.parse(fs.readFileSync(DEVICE_IDENTITY_PATH, 'utf-8'));
            const currentFp = generateDeviceFingerprint();
            if (data.fingerprint === currentFp) {
                return data;
            }
        }
    } catch (e) {}
    const fingerprint = generateDeviceFingerprint();
    const identity = {
        fingerprint: fingerprint,
        device_name: os.hostname() || 'Unknown Device',
        platform: process.platform,
        arch: process.arch,
        username: os.userInfo().username,
        created: new Date().toISOString(),
        last_seen: new Date().toISOString(),
    };
    try {
        if (!fs.existsSync(KAGUYA_DATA_DIR)) {
            fs.mkdirSync(KAGUYA_DATA_DIR, { recursive: true });
        }
        fs.writeFileSync(DEVICE_IDENTITY_PATH, JSON.stringify(identity, null, 2), 'utf-8');
        try {
            if (process.platform === 'win32') {
                const { execSync } = require('child_process');
                execSync(`icacls "${DEVICE_IDENTITY_PATH}" /inheritance:r /grant:r "%USERNAME%:R"`, { stdio: 'ignore' });
            } else {
                fs.chmodSync(DEVICE_IDENTITY_PATH, 0o600);
            }
        } catch (e2) {}
    } catch (e) {}
    return identity;
}

function isSafeStorageAvailable() {
    try {
        return safeStorage && safeStorage.isEncryptionAvailable();
    } catch (e) {
        return false;
    }
}

function encryptForStorage(plaintext) {
    if (!plaintext) return null;
    try {
        if (isSafeStorageAvailable()) {
            const encrypted = safeStorage.encryptString(plaintext);
            return { method: 'safeStorage', data: encrypted.toString('base64') };
        }
        const key = crypto.createHash('sha256').update(generateDeviceFingerprint() + '_kaguya_vault').digest();
        const iv = crypto.randomBytes(16);
        const cipher = crypto.createCipheriv('aes-256-cbc', key, iv);
        let encrypted = cipher.update(plaintext, 'utf8', 'base64');
        encrypted += cipher.final('base64');
        return { method: 'aes256cbc', iv: iv.toString('base64'), data: encrypted };
    } catch (e) {
        return null;
    }
}

function decryptFromStorage(encObj) {
    if (!encObj || !encObj.method || !encObj.data) return null;
    try {
        if (encObj.method === 'safeStorage' && isSafeStorageAvailable()) {
            const buffer = Buffer.from(encObj.data, 'base64');
            return safeStorage.decryptString(buffer);
        }
        if (encObj.method === 'aes256cbc' && encObj.iv) {
            const key = crypto.createHash('sha256').update(generateDeviceFingerprint() + '_kaguya_vault').digest();
            const iv = Buffer.from(encObj.iv, 'base64');
            const decipher = crypto.createDecipheriv('aes-256-cbc', key, iv);
            let decrypted = decipher.update(encObj.data, 'base64', 'utf8');
            decrypted += decipher.final('utf8');
            return decrypted;
        }
    } catch (e) {}
    return null;
}

function saveDeviceVault(vaultData) {
    try {
        if (!fs.existsSync(KAGUYA_DATA_DIR)) {
            fs.mkdirSync(KAGUYA_DATA_DIR, { recursive: true });
        }
        const identity = getDeviceIdentity();
        const toEncrypt = {
            active_provider: vaultData.active_provider || '',
            providers: {},
        };
        for (const [name, cfg] of Object.entries(vaultData.providers || {})) {
            const encKey = encryptForStorage(cfg.api_key || '');
            toEncrypt.providers[name] = {
                api_url: cfg.api_url || '',
                api_key_encrypted: encKey,
                model: cfg.model || '',
                bound_at: cfg.bound_at || new Date().toISOString(),
            };
        }
        const vault = {
            device_fingerprint: identity.fingerprint,
            device_name: identity.device_name,
            encrypted_at: new Date().toISOString(),
            vault_version: 1,
            data: toEncrypt,
        };
        fs.writeFileSync(DEVICE_VAULT_PATH, JSON.stringify(vault, null, 2), 'utf-8');
        try {
            if (process.platform === 'win32') {
                const { execSync } = require('child_process');
                execSync(`icacls "${DEVICE_VAULT_PATH}" /inheritance:r /grant:r "%USERNAME%:R"`, { stdio: 'ignore' });
            } else {
                fs.chmodSync(DEVICE_VAULT_PATH, 0o600);
            }
        } catch (e) {}
        return true;
    } catch (e) {
        return false;
    }
}

function loadDeviceVault() {
    try {
        if (!fs.existsSync(DEVICE_VAULT_PATH)) return null;
        const vault = JSON.parse(fs.readFileSync(DEVICE_VAULT_PATH, 'utf-8'));
        const identity = getDeviceIdentity();
        if (vault.device_fingerprint !== identity.fingerprint) {
            return null;
        }
        const result = {
            active_provider: vault.data?.active_provider || '',
            providers: {},
            device_name: vault.device_name || identity.device_name,
            bound_at: vault.encrypted_at,
        };
        for (const [name, cfg] of Object.entries(vault.data?.providers || {})) {
            const apiKey = cfg.api_key_encrypted ? decryptFromStorage(cfg.api_key_encrypted) : '';
            result.providers[name] = {
                api_url: cfg.api_url || '',
                api_key: apiKey || '',
                model: cfg.model || '',
                bound_at: cfg.bound_at || '',
            };
        }
        return result;
    } catch (e) {
        return null;
    }
}

function clearDeviceVault() {
    try {
        if (fs.existsSync(DEVICE_VAULT_PATH)) {
            fs.unlinkSync(DEVICE_VAULT_PATH);
        }
        return true;
    } catch (e) {
        return false;
    }
}

// ========== Auto Update Configuration ==========

function setupAutoUpdater() {
    // Check for updates every 30 minutes
    const UPDATE_CHECK_INTERVAL = 30 * 60 * 1000;
    
    autoUpdater.on('checking-for-update', () => {
        console.log('[Updater] Checking for updates...');
    });
    
    autoUpdater.on('update-available', (info) => {
        console.log('[Updater] Update available:', info.version);
        dialog.showMessageBox(mainWindow, {
            type: 'info',
            title: '发现新版本',
            message: `Kaguya IDE ${info.version} 已发布`,
            detail: '新版本正在下载中，下载完成后将提示安装。',
            buttons: ['确定'],
        });
    });
    
    autoUpdater.on('update-not-available', () => {
        console.log('[Updater] No updates available');
    });
    
    autoUpdater.on('error', (err) => {
        console.error('[Updater] Error:', err.message);
    });
    
    autoUpdater.on('download-progress', (progressObj) => {
        const percent = Math.round(progressObj.percent);
        console.log(`[Updater] Download progress: ${percent}%`);
        if (mainWindow && !mainWindow.isDestroyed()) {
            mainWindow.setProgressBar(progressObj.percent / 100);
        }
    });
    
    autoUpdater.on('update-downloaded', (info) => {
        console.log('[Updater] Update downloaded:', info.version);
        if (mainWindow && !mainWindow.isDestroyed()) {
            mainWindow.setProgressBar(-1); // Remove progress bar
        }
        
        dialog.showMessageBox(mainWindow, {
            type: 'question',
            title: '更新就绪',
            message: `Kaguya IDE ${info.version} 已下载完成`,
            detail: '是否立即重启应用以安装更新？',
            buttons: ['立即重启', '稍后手动更新'],
            defaultId: 0,
            cancelId: 1,
        }).then((result) => {
            if (result.response === 0) {
                autoUpdater.quitAndInstall(false, true);
            }
        });
    });
    
    // Check for updates on startup
    setTimeout(() => {
        autoUpdater.checkForUpdatesAndNotify();
    }, 5000);
    
    // Check for updates periodically
    setInterval(() => {
        autoUpdater.checkForUpdatesAndNotify();
    }, UPDATE_CHECK_INTERVAL);
    
    // Manual check via IPC
    ipcMain.handle('app-checkForUpdates', async () => {
        try {
            const result = await autoUpdater.checkForUpdates();
            return { 
                success: true, 
                updateAvailable: result && result.updateInfo && result.updateInfo.version !== APP_VERSION,
                currentVersion: APP_VERSION,
                latestVersion: result?.updateInfo?.version || APP_VERSION,
            };
        } catch (err) {
            return { success: false, error: err.message };
        }
    });
}

let mainWindow = null;
let pythonProcess = null;
let tray = null;
let serverPort = DEFAULT_PORT;
let terminalSessions = new Map();

function findFreePort() {
    return new Promise((resolve, reject) => {
        const server = net.createServer();
        server.listen(0, '127.0.0.1', () => {
            const port = server.address().port;
            server.close(() => resolve(port));
        });
        server.on('error', reject);
    });
}

function getResourcePath() {
    if (app.isPackaged) {
        return path.join(process.resourcesPath, 'python-app');
    }
    
    const homeDir = process.env.USERPROFILE || process.env.HOME || os.homedir();
    const sourceDir = process.env.KAGUYA_SOURCE_DIR;
    
    if (sourceDir) {
        const sourcePath = path.resolve(sourceDir);
        if (fs.existsSync(path.join(sourcePath, 'qwen3_web.py'))) {
            console.log('[Main] Using KAGUYA_SOURCE_DIR:', sourcePath);
            return sourcePath;
        }
    }
    
    if (homeDir) {
        const desktopAppPath = path.join(homeDir, '.conda', 'kaguya-desktop', 'dist', 'KaguyaIDE-3.1.0-full', 'app');
        if (fs.existsSync(path.join(desktopAppPath, 'qwen3_web.py'))) {
            console.log('[Main] Using USERPROFILE path:', desktopAppPath);
            return desktopAppPath;
        }
        
        const condaPath = path.join(homeDir, '.conda');
        if (fs.existsSync(path.join(condaPath, 'qwen3_web.py'))) {
            console.log('[Main] Using conda path:', condaPath);
            return condaPath;
        }
    }
    
    try {
        const appPath = app.getAppPath();
        if (appPath) {
            const parentDir = path.dirname(path.dirname(appPath));
            const appDir = path.join(parentDir, 'app');
            if (fs.existsSync(path.join(appDir, 'qwen3_web.py'))) {
                console.log('[Main] Using app path:', appDir);
                return appDir;
            }
        }
    } catch(e) {}
    
    try {
        const electronDir = __dirname;
        const parentDir = path.dirname(electronDir);
        const appDir = path.join(parentDir, 'app');
        if (fs.existsSync(path.join(appDir, 'qwen3_web.py'))) {
            console.log('[Main] Using __dirname path:', appDir);
            return appDir;
        }
    } catch(e) {}
    
    console.log('[Main] WARNING: Could not find app directory, falling back to homeDir/.conda');
    return path.join(homeDir || os.homedir(), '.conda');
}

function getPythonPath() {
    const homeDir = process.env.USERPROFILE || process.env.HOME || os.homedir();
    const dlPaths = [
        path.join(homeDir, '.conda', 'envs', 'DL', 'python.exe'),
        path.join(homeDir, 'anaconda3', 'envs', 'DL', 'python.exe'),
        path.join(homeDir, 'miniconda3', 'envs', 'DL', 'python.exe'),
        'D:\\Anoconda\\envs\\DL\\python.exe',
        'D:\\Anaconda3\\envs\\DL\\python.exe',
        'D:\\Miniconda3\\envs\\DL\\python.exe',
        'C:\\Anaconda3\\envs\\DL\\python.exe',
        'C:\\Miniconda3\\envs\\DL\\python.exe',
    ];
    
    for (const p of dlPaths) {
        try {
            if (fs.existsSync(p)) {
                console.log('[Main] Found DL Python:', p);
                return p;
            }
        } catch(e) {}
    }
    
    const resourcePath = getResourcePath();
    const embeddedPython = path.join(resourcePath, '..', 'python', 'python.exe');
    if (fs.existsSync(embeddedPython)) {
        console.log('[Main] Found embedded Python:', embeddedPython);
        return embeddedPython;
    }
    
    const otherCondaPaths = [
        path.join(homeDir, '.conda', 'kaguya_env', 'Scripts', 'python.exe'),
        path.join(homeDir, 'anaconda3', 'python.exe'),
        path.join(homeDir, 'miniconda3', 'python.exe'),
    ];
    
    for (const p of otherCondaPaths) {
        try {
            if (fs.existsSync(p)) {
                console.log('[Main] Found Conda Python:', p);
                return p;
            }
        } catch(e) {}
    }
    
    const standardPaths = [
        path.join(process.env.LOCALAPPDATA || '', 'Programs', 'Python', 'Python312', 'python.exe'),
        path.join(process.env.LOCALAPPDATA || '', 'Programs', 'Python', 'Python311', 'python.exe'),
        path.join(process.env.LOCALAPPDATA || '', 'Programs', 'Python', 'Python310', 'python.exe'),
        path.join(process.env.LOCALAPPDATA || '', 'Programs', 'Python', 'Python39', 'python.exe'),
    ];
    
    for (const p of standardPaths) {
        try {
            if (fs.existsSync(p)) {
                console.log('[Main] Found standard Python:', p);
                return p;
            }
        } catch(e) {}
    }
    
    console.log('[Main] Trying system Python from PATH...');
    return 'python';
}

function getShellPath() {
    if (process.platform === 'win32') {
        return process.env.COMSPEC || 'cmd.exe';
    }
    return process.env.SHELL || '/bin/bash';
}

async function startPythonServer(port) {
    const pythonPath = getPythonPath();
    
    const tmpDir = os.tmpdir();
    const launcherScript = path.join(tmpDir, 'kaguya_launcher.py');
    
    const resourcePath = getResourcePath();
    console.log('[Main] Resource path for Python:', resourcePath);
    
    const launcherContent = `
import os, sys

app_dir = r'${resourcePath.replace(/\\/g, '\\\\')}'
if not os.path.exists(os.path.join(app_dir, 'qwen3_web.py')):
    import pathlib
    home = str(pathlib.Path.home())
    for candidate in [
        os.path.join(home, '.conda', 'kaguya-desktop', 'dist', 'KaguyaIDE-3.1.0-full', 'app'),
        os.path.join(home, '.conda'),
    ]:
        if os.path.exists(os.path.join(candidate, 'qwen3_web.py')):
            app_dir = candidate
            break

if not os.path.exists(os.path.join(app_dir, 'qwen3_web.py')):
    print('[LAUNCHER ERROR] qwen3_web.py not found in:', app_dir, file=sys.stderr)
    sys.exit(1)

os.chdir(app_dir)
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)
os.environ['KAGUYA_DESKTOP_MODE'] = '1'
os.environ['KAGUYA_PORT'] = '${port}'
os.environ['KAGUYA_ELECTRON'] = '1'
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONUTF8'] = '1'

print('[LAUNCHER] App dir:', app_dir)
print('[LAUNCHER] Starting Flask on port ${port}...')

sys.argv = ['qwen3_web.py', '--port', '${port}', '--localhost-only']
import runpy
runpy.run_path(os.path.join(app_dir, 'qwen3_web.py'), run_name='__main__')
`;
    
    try {
        fs.writeFileSync(launcherScript, launcherContent, 'utf-8');
        console.log('[Main] Created launcher script:', launcherScript);
    } catch(e) {
        console.error('[Main] Failed to create launcher:', e.message);
        throw new Error('Failed to create launcher script');
    }

    console.log('[Main] Python path:', pythonPath);
    console.log('[Main] Launcher script:', launcherScript);

    // Verify Python is executable
    let verifiedPythonPath = pythonPath;
    if (pythonPath === 'python') {
        try {
            const { execSync } = require('child_process');
            const result = execSync('where python', { encoding: 'utf8', windowsHide: true });
            const paths = result.trim().split('\n').map(p => p.trim()).filter(p => p);
            if (paths.length > 0) {
                verifiedPythonPath = paths[0];
                console.log('[Main] Found Python in PATH:', verifiedPythonPath);
            }
        } catch (e) {
            console.error('[Main] Python not found in PATH');
            throw new Error('Python not found. Please install Python 3.9+ and ensure it is in PATH.');
        }
    }

    const env = Object.assign({}, process.env, {
        'KAGUYA_DESKTOP_MODE': '1',
        'KAGUYA_PORT': String(port),
        'KAGUYA_PERMISSION_MODE': 'bypassPermissions',
        'KAGUYA_ELECTRON': '1',
    });

    const args = [launcherScript];

    console.log('[Main] Starting Python server via launcher...');
    console.log('[Main] Command:', verifiedPythonPath, args.join(' '));

    pythonProcess = spawn(verifiedPythonPath, args, {
        cwd: tmpDir,
        env: env,
        stdio: ['pipe', 'pipe', 'pipe'],
        windowsHide: false,
    });

    let serverStdout = '';
    let serverStderr = '';

    pythonProcess.stdout.on('data', (data) => {
        const output = data.toString();
        serverStdout += output;
        console.log('[Python]', output.trim());
    });

    pythonProcess.stderr.on('data', (data) => {
        const output = data.toString();
        serverStderr += output;
        console.error('[Python Err]', output.trim());
    });

    pythonProcess.on('error', (err) => {
        console.error('[Main] Python process error:', err.message);
        dialog.showErrorBox('Python Error',
            `Failed to start Python process:\n${err.message}\n\n` +
            `Python path: ${verifiedPythonPath}\n` +
            `Launcher: ${launcherScript}`);
    });

    pythonProcess.on('close', (code) => {
        console.log(`[Python] Process exited with code ${code}`);
        if (code !== 0 && code !== null) {
            console.error('[Main] Python exited unexpectedly. Last stderr:', serverStderr.slice(-500));
        }
        pythonProcess = null;
        try { fs.unlinkSync(launcherScript); } catch(e) {}
    });

    // Wait for server
    console.log('[Main] Waiting for server to start...');
    for (let i = 0; i < 200; i++) {
        await new Promise(r => setTimeout(r, 300));
        try {
            await new Promise((resolve, reject) => {
                const req = require('http').get(`http://127.0.0.1:${port}/`, (res) => {
                    res.resume();
                    resolve();
                });
                req.on('error', reject);
                req.setTimeout(1000, () => { req.destroy(); reject(new Error('timeout')); });
            });
            console.log(`[OK] Server ready at http://127.0.0.1:${port}/`);
            return port;
        } catch (e) {
            if (i % 10 === 0) {
                console.log(`[Main] Waiting for server... (${i}/200)`);
            }
        }
    }
    console.log('[Main] Server wait timeout, proceeding anyway');
    return port;
}

let miniServer = null;

function startMiniServer(port) {
    const http = require('http');
    const https = require('https');
    const url = require('url');
    const crypto = require('crypto');

    const providerUrls = {
        deepseek: { url: 'https://api.deepseek.com', model: 'deepseek-chat', type: 'openai' },
        openai: { url: 'https://api.openai.com/v1', model: 'gpt-4o', type: 'openai' },
        claude: { url: 'https://api.anthropic.com', model: 'claude-3-7-sonnet-20250219', type: 'claude' },
        qwen: { url: 'https://dashscope.aliyuncs.com/compatible-mode/v1', model: 'qwen-plus', type: 'openai' },
        moonshot: { url: 'https://api.moonshot.cn/v1', model: 'moonshot-v1-8k', type: 'openai' },
        zhipu: { url: 'https://open.bigmodel.cn/api/paas/v4', model: 'glm-4-flash', type: 'openai' },
        groq: { url: 'https://api.groq.com/openai/v1', model: 'llama-3.3-70b-versatile', type: 'openai' },
    };

    let savedApiConfig = null;
    let fileWorkspaceDir = path.join(os.homedir(), 'KaguyaIDE_Files');
    if (!fs.existsSync(fileWorkspaceDir)) {
        try { fs.mkdirSync(fileWorkspaceDir, { recursive: true }); } catch(e) {}
    }

    try {
        const vault = loadDeviceVault();
        if (vault && vault.active_provider && vault.providers[vault.active_provider]) {
            const prov = vault.providers[vault.active_provider];
            if (prov.api_key) {
                savedApiConfig = {
                    enabled: true,
                    provider: vault.active_provider,
                    apiKey: prov.api_key,
                    apiUrl: prov.api_url,
                    model: prov.model || (providerUrls[vault.active_provider] || {}).model,
                };
                console.log(`[MiniServer] Auto-loaded API config for device: ${vault.device_name}, provider: ${vault.active_provider}`);
            }
        }
    } catch (e) {
        console.log('[MiniServer] No saved device vault found');
    }

    function serveJSON(res, code, obj) {
        res.writeHead(code, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(obj));
    }

    function serveImage(res, imgFile) {
        const mapping = { '/header-img': 'kaguya-header.png', '/hero-img': 'kaguya-hero.png', '/welcome-img': 'kaguya-welcome.png' };
        const fname = mapping[imgFile];
        if (fname) {
            const imgPath = path.join(getResourcePath(), 'assets', fname);
            if (fs.existsSync(imgPath)) {
                res.writeHead(200, { 'Content-Type': 'image/png' });
                res.end(fs.readFileSync(imgPath));
                return true;
            }
        }
        return false;
    }

    function getMainPageHtml() {
        const rp = getResourcePath();
        let apiConfigured = savedApiConfig ? 'true' : 'false';
        return `<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Kaguya IDE</title>
<style>${getMiniStyles()}</style></head><body>
<div id="app">
<aside class="sidebar" id="sidebar">
  <div class="sidebar-header">
    <img src="/header-img" class="sidebar-avatar">
    <div class="sidebar-title">Kaguya IDE</div>
    <div class="sidebar-sub">v${APP_VERSION}</div>
  </div>
  <div class="sidebar-nav">
     <button class="nav-btn active" onclick="switchView('chat')">💬 聊天</button>
     <button class="nav-btn" onclick="switchView('files')">📁 文件</button>
     <button class="nav-btn" onclick="switchView('config')">⚙️ 配置</button>
     <button class="nav-btn" onclick="switchView('account')">🔐 账户</button>
     <a href="/docs" class="nav-btn" style="text-decoration:none;display:block">📋 API文档</a>
     <a href="/readme" class="nav-btn" style="text-decoration:none;display:block">📖 README</a>
   </div>
  <div class="sidebar-footer">
    <div class="status-indicator" id="apiStatus">🔴 API未配置</div>
  </div>
</aside>
<main class="main">
  <header class="topbar">
    <div class="topbar-left">
      <img src="/header-img" class="topbar-avatar">
      <span class="topbar-title">辉夜 AI 助手</span>
    </div>
    <div class="topbar-actions">
      <button class="btn-sm" onclick="toggleSidebar()">☰</button>
      <button class="btn-sm btn-primary" onclick="newChat()">✨ 新对话</button>
    </div>
  </header>
  <div id="chatView" class="view active">
    <div id="messages" class="messages">
      <div class="welcome" id="welcomeScreen">
        <img src="/welcome-img" class="welcome-img">
        <h2>辉夜 AI 助手</h2>
        <p class="welcome-sub">输入消息开始对话，通过上方⚙️配置API Key</p>
        <div class="quick-actions">
          <button onclick="sendQuick('帮我写一段Python代码')">💻 写代码</button>
          <button onclick="sendQuick('翻译这段文本：Hello World')">🌐 翻译</button>
          <button onclick="sendQuick('解释一下什么是机器学习')">📚 学习</button>
          <button onclick="sendQuick('帮我分析这段数据')">📊 分析</button>
        </div>
      </div>
    </div>
    <div class="input-area">
      <div class="input-row">
        <textarea id="chatInput" rows="2" placeholder="输入消息... (Shift+Enter 换行, Enter 发送)" onkeydown="handleKey(event)"></textarea>
      </div>
      <div class="input-tools">
        <label class="file-btn" title="上传文件">📎<input type="file" id="fileInput" multiple style="display:none" onchange="uploadFiles(event)"></label>
        <button class="btn-sm" onclick="sendMessage()" id="sendBtn">🚀 发送</button>
      </div>
      <div id="uploadStatus" class="upload-status"></div>
    </div>
    <div id="loading" class="loading" style="display:none">🤔 思考中...</div>
  </div>
  <div id="filesView" class="view">
    <div class="panel-header">
      <h3>📁 文件管理</h3>
      <div class="panel-actions">
        <label class="btn-sm btn-primary">📤 上传文件<input type="file" id="fileInput2" multiple style="display:none" onchange="uploadFiles(event)"></label>
      </div>
    </div>
    <div id="fileList" class="file-list"></div>
  </div>
  <div id="configView" class="view">
    <div class="panel-header"><h3>⚙️ API 配置</h3></div>
    <div class="config-panel">
      <div class="form-group"><label>API 提供商</label>
        <select id="cfgProvider" class="input">
          <option value="deepseek">DeepSeek (推荐)</option>
          <option value="openai">OpenAI</option>
          <option value="claude">Claude (Anthropic)</option>
          <option value="qwen">Qwen (阿里)</option>
          <option value="moonshot">Moonshot (Kimi)</option>
          <option value="zhipu">智谱 (GLM)</option>
          <option value="groq">Groq</option>
        </select>
      </div>
      <div class="form-group"><label>API Key</label>
        <input type="password" id="cfgKey" class="input" placeholder="sk-...">
      </div>
      <div class="form-group"><label>API URL (可选)</label>
        <input type="text" id="cfgUrl" class="input" placeholder="自动检测">
      </div>
      <button class="btn-primary" onclick="saveConfig()" style="width:100%;padding:12px">💾 保存并测试连接</button>
      <div class="form-group" style="margin-top:12px">
        <label style="display:flex;align-items:center;gap:6px;cursor:pointer">
          <input type="checkbox" id="cfgRemember" checked style="accent-color:var(--primary)">
          <span style="font-size:12px;color:var(--muted)">记住在此设备上（安全加密存储）</span>
        </label>
      </div>
      <div id="cfgStatus" style="margin-top:12px;font-size:13px"></div>
    </div>
  </div>
  <div id="accountView" class="view">
    <div class="panel-header"><h3>🔐 账户与设备绑定</h3></div>
    <div class="config-panel">
      <div id="deviceInfoPanel" class="info-card">
        <div class="info-row"><span class="info-label">设备标识</span><span class="info-value" id="deviceId">加载中...</span></div>
        <div class="info-row"><span class="info-label">设备名称</span><span class="info-value" id="deviceName">-</span></div>
        <div class="info-row"><span class="info-label">平台</span><span class="info-value" id="devicePlatform">-</span></div>
        <div class="info-row"><span class="info-label">安全存储</span><span class="info-value" id="safeStorageStatus">-</span></div>
        <div class="info-row"><span class="info-label">绑定状态</span><span class="info-value" id="bindStatus">-</span></div>
      </div>
      <div id="boundProvidersPanel" style="margin-top:16px">
        <h4 style="font-size:13px;color:var(--muted);margin-bottom:8px">已绑定的API提供商</h4>
        <div id="boundProvidersList"></div>
      </div>
      <div style="margin-top:16px;display:flex;gap:8px">
        <button class="btn-primary" onclick="refreshAccountInfo()" style="flex:1;padding:10px">🔄 刷新状态</button>
        <button class="btn-danger" onclick="unbindAll()" style="flex:1;padding:10px">🗑 清除所有绑定</button>
      </div>
      <div id="accountStatus" style="margin-top:12px;font-size:13px"></div>
    </div>
  </div>
</main>
</div>
<script>${getMiniScript()}</script></body></html>`;
    }

    function getMiniStyles() {
        return `
:root{--bg:#0a0a0f;--surface:#16161e;--border:#2a2a3a;--text:#e0e0e0;--muted:#888;--primary:#7c5cfc;--primary2:#5c3cfc;--danger:#ef5350;--success:#4caf50}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif;height:100vh;overflow:hidden}
#app{display:flex;height:100vh}
.sidebar{width:220px;background:var(--surface);border-right:1px solid var(--border);display:flex;flex-direction:column;flex-shrink:0}
.sidebar-header{text-align:center;padding:20px 12px;border-bottom:1px solid var(--border)}
.sidebar-avatar{width:48px;height:48px;border-radius:50%;margin-bottom:8px;object-fit:cover}
.sidebar-title{font-size:15px;font-weight:700;background:linear-gradient(135deg,var(--primary),#00d4ff);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.sidebar-sub{font-size:11px;color:var(--muted);margin-top:2px}
.sidebar-nav{padding:12px;flex:1}
.nav-btn{display:block;width:100%;padding:10px 14px;margin-bottom:4px;border-radius:8px;border:none;background:transparent;color:var(--text);font-size:13px;text-align:left;cursor:pointer}
.nav-btn:hover,.nav-btn.active{background:rgba(124,92,252,0.15);color:var(--primary)}
.sidebar-footer{padding:12px;border-top:1px solid var(--border)}
.status-indicator{font-size:11px;padding:6px 10px;border-radius:6px;background:rgba(239,83,80,0.1);color:var(--danger);text-align:center}
.status-indicator.ok{background:rgba(76,175,80,0.1);color:var(--success)}
.main{flex:1;display:flex;flex-direction:column;min-width:0}
.topbar{display:flex;justify-content:space-between;align-items:center;padding:8px 16px;background:var(--surface);border-bottom:1px solid var(--border)}
.topbar-left{display:flex;align-items:center;gap:8px}
.topbar-avatar{width:28px;height:28px;border-radius:50%;object-fit:cover}
.topbar-title{font-weight:600;font-size:14px}
.topbar-actions{display:flex;gap:8px}
.btn-sm{padding:6px 14px;border-radius:6px;border:1px solid var(--border);background:var(--surface);color:var(--text);font-size:12px;cursor:pointer}
.btn-sm:hover{opacity:0.9}
.btn-primary{background:linear-gradient(135deg,var(--primary),var(--primary2));color:white;border:none}
.view{display:none;flex-direction:column;flex:1;overflow:hidden}
.view.active{display:flex}
.messages{flex:1;overflow-y:auto;padding:20px;padding-bottom:4px}
.welcome{text-align:center;padding:40px 20px}
.welcome-img{width:120px;height:120px;border-radius:50%;margin-bottom:16px;object-fit:cover}
.welcome h2{font-size:22px;margin-bottom:8px}
.welcome-sub{color:var(--muted);margin-bottom:24px;font-size:13px}
.quick-actions{display:flex;flex-wrap:wrap;gap:8px;justify-content:center}
.quick-actions button{padding:8px 16px;border-radius:8px;border:1px solid var(--border);background:var(--surface);color:var(--text);font-size:12px;cursor:pointer}
.quick-actions button:hover{border-color:var(--primary)}
.msg{margin-bottom:16px;max-width:85%}
.msg.user{margin-left:auto;text-align:right}
.msg-label{font-size:10px;color:var(--muted);margin-bottom:4px}
.msg-content{display:inline-block;padding:10px 16px;border-radius:12px;font-size:13px;line-height:1.6;word-break:break-word;text-align:left}
.msg.user .msg-content{background:linear-gradient(135deg,var(--primary),var(--primary2));color:white;border-bottom-right-radius:4px}
.msg.assistant .msg-content{background:var(--surface);border:1px solid var(--border);border-bottom-left-radius:4px}
.msg.assistant .msg-content pre{background:#0a0a0f;padding:10px;border-radius:6px;overflow-x:auto;font-size:12px;margin:8px 0}
.msg.assistant .msg-content code{font-size:12px}
.input-area{border-top:1px solid var(--border);padding:12px 16px;background:var(--surface)}
.input-row textarea{width:100%;background:var(--bg);border:1px solid var(--border);border-radius:8px;color:var(--text);font-size:13px;padding:10px 14px;resize:none;outline:none;font-family:inherit}
.input-row textarea:focus{border-color:var(--primary)}
.input-tools{display:flex;justify-content:space-between;align-items:center;margin-top:8px}
.file-btn{padding:6px 10px;border-radius:6px;border:1px solid var(--border);cursor:pointer;font-size:14px;background:var(--bg)}
.upload-status{font-size:11px;color:var(--muted);margin-top:4px}
.loading{text-align:center;padding:12px;color:var(--muted);font-size:13px}
.panel-header{display:flex;justify-content:space-between;align-items:center;padding:16px 20px;border-bottom:1px solid var(--border)}
.panel-header h3{font-size:15px}
.panel-actions{display:flex;gap:8px}
.file-list{padding:12px 20px;overflow-y:auto;flex:1}
.file-item{display:flex;justify-content:space-between;align-items:center;padding:8px 12px;margin-bottom:4px;background:var(--surface);border-radius:6px;font-size:13px}
.file-item-name{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.file-item-size{color:var(--muted);font-size:11px;margin-right:12px}
.file-item-del{color:var(--danger);cursor:pointer;font-size:14px}
.config-panel{max-width:500px;margin:20px auto;padding:20px;background:var(--surface);border-radius:12px;border:1px solid var(--border)}
.form-group{margin-bottom:14px}
.form-group label{display:block;font-size:12px;color:var(--muted);margin-bottom:4px}
.input{width:100%;padding:10px 12px;background:var(--bg);border:1px solid var(--border);border-radius:6px;color:var(--text);font-size:13px;outline:none}
.input:focus{border-color:var(--primary)}
.info-card{background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:12px}
.info-row{display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid rgba(42,42,58,0.5);font-size:13px}
.info-row:last-child{border-bottom:none}
.info-label{color:var(--muted);font-size:12px}
.info-value{color:var(--text);font-size:12px;font-family:monospace;word-break:break-all}
.bound-provider{display:flex;justify-content:space-between;align-items:center;padding:8px 12px;margin-bottom:4px;background:var(--bg);border:1px solid var(--border);border-radius:6px;font-size:12px}
.bound-provider-name{font-weight:600;color:var(--primary)}
.bound-provider-key{color:var(--muted);font-family:monospace;font-size:11px}
.bound-provider-del{color:var(--danger);cursor:pointer;font-size:14px;margin-left:8px}
.btn-danger{padding:10px 16px;border-radius:6px;border:1px solid var(--danger);background:rgba(239,83,80,0.1);color:var(--danger);font-size:12px;cursor:pointer}
.btn-danger:hover{background:rgba(239,83,80,0.2)}
@media(max-width:600px){.sidebar{display:none}.sidebar.show{display:flex;position:fixed;top:0;left:0;bottom:0;z-index:100}}`;
    }

    function getMiniScript() {
        return `
let conversations=[{id:'default',title:'新对话',messages:[]}];
let currentConvId='default';
let isStreaming=false;

function getConv(){let c=conversations.find(x=>x.id===currentConvId);if(!c){c={id:currentConvId,title:'新对话',messages:[]};conversations.push(c)}return c}
function switchView(v){
  document.querySelectorAll('.view').forEach(e=>e.classList.remove('active'));
  document.getElementById(v+'View').classList.add('active');
  document.querySelectorAll('.nav-btn').forEach(e=>e.classList.remove('active'));
  if(v==='files')refreshFileList();
  if(v==='config')loadConfig();
  if(v==='account')refreshAccountInfo();
  event.target.classList.add('active');
}
function toggleSidebar(){document.getElementById('sidebar').classList.toggle('show')}
function newChat(){currentConvId='conv_'+Date.now();conversations.push({id:currentConvId,title:'新对话',messages:[]});
  document.getElementById('messages').innerHTML='<div class="welcome"><img src="/welcome-img" class="welcome-img"><h2>辉夜 AI 助手</h2><p class="welcome-sub">新对话已开始</p></div>';
  document.getElementById('welcomeScreen')||(document.getElementById('messages').innerHTML+='<div class="welcome" id="welcomeScreen"><img src="/welcome-img" class="welcome-img"><h2>辉夜 AI 助手</h2><p class="welcome-sub">输入消息开始对话</p></div>')}
function handleKey(e){if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();sendMessage()}}
function sendQuick(text){document.getElementById('chatInput').value=text;sendMessage()}
async function sendMessage(){
  const input=document.getElementById('chatInput');
  const text=input.value.trim();
  if(!text||isStreaming)return;
  input.value='';
  const welcome=document.getElementById('welcomeScreen');
  if(welcome)welcome.style.display='none';
  const conv=getConv();
  conv.messages.push({role:'user',content:text});
  addMessage('user',text);
  document.getElementById('loading').style.display='block';
  const msgDiv=addMessage('assistant','');
  document.getElementById('loading').style.display='none';
  isStreaming=true;
  const sendBtn=document.getElementById('sendBtn');
  sendBtn.disabled=true;sendBtn.textContent='⏳';
  let fullText='';
  try{
    const messages=[{role:'system',content:'你是Kaguya IDE的AI助手，请简洁、专业地回答用户问题。代码用Markdown格式输出。'}];
    for(const m of conv.messages)messages.push(m);
    const resp=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({messages:conv.messages.slice(-20),stream:true})});
    if(!resp.ok){msgDiv.querySelector('.msg-content').textContent='API请求失败: '+resp.status;isStreaming=false;sendBtn.disabled=false;sendBtn.textContent='🚀 发送';return}
    const reader=resp.body.getReader();
    const decoder=new TextDecoder();
    let buffer='';
    while(true){
      const{done,value}=await reader.read();
      if(done)break;
      buffer+=decoder.decode(value,{stream:true});
      const lines=buffer.split('\\n');
      buffer=lines.pop()||'';
      for(const line of lines){
        if(!line.startsWith('data: '))continue;
        const data=line.slice(6).trim();
        if(data==='[DONE]')break;
        try{const chunk=JSON.parse(data);
          const content=chunk.choices?.[0]?.delta?.content||chunk.delta?.text||'';
          if(content){fullText+=content;msgDiv.querySelector('.msg-content').textContent=fullText}
        }catch(e){}
      }
    }
    conv.messages.push({role:'assistant',content:fullText||'(空响应)'});
    if(fullText&&conv.title==='新对话')conv.title=text.slice(0,20)+'...';
  }catch(e){msgDiv.querySelector('.msg-content').textContent='连接错误: '+e.message}
  isStreaming=false;sendBtn.disabled=false;sendBtn.textContent='🚀 发送';
}
function addMessage(role,content){
  const div=document.createElement('div');div.className='msg '+role;
  div.innerHTML='<div class="msg-label">'+(role==='user'?'👤 你':'🤖 辉夜')+'</div><div class="msg-content">'+escapeHtml(content||'')+'</div>';
  const messages=document.getElementById('messages');
  messages.appendChild(div);messages.scrollTop=messages.scrollHeight;
  return div;
}
function escapeHtml(t){if(!t)return'';return t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\\n/g,'<br>')
  .replace(/\\*\\*(.+?)\\*\\*/g,'<b>$1</b>').replace(/\\\`([^\\\`]+)\\\`/g,'<code>$1</code>')}
async function uploadFiles(e){
  const files=e.target.files;if(!files.length)return;
  const formData=new FormData();
  for(const f of files)formData.append('files',f);
  document.getElementById('uploadStatus').textContent='上传中...';
  try{
    const resp=await fetch('/agent/upload-device-files',{method:'POST',body:formData});
    const data=await resp.json();
    if(data.imported){document.getElementById('uploadStatus').textContent='✅ '+data.imported.map(x=>x.name).join(', ')+' 已上传'}
    else{document.getElementById('uploadStatus').textContent='❌ 上传失败'}
    setTimeout(()=>document.getElementById('uploadStatus').textContent='',3000);
  }catch(e){document.getElementById('uploadStatus').textContent='❌ '+e.message}
  e.target.value='';
}
async function refreshFileList(){
  try{
    const resp=await fetch('/agent/list-files');const data=await resp.json();
    const el=document.getElementById('fileList');
    if(!data.files||!data.files.length){el.innerHTML='<p style="color:var(--muted);padding:20px">暂无文件</p>';return}
    el.innerHTML=data.files.map(f=>'<div class="file-item"><span class="file-item-name">'+escapeHtml(f.name)+'</span><span class="file-item-size">'+formatSize(f.size)+'</span><span class="file-item-del" onclick="deleteFile(\\''+encodeURIComponent(f.name)+'\\')">🗑</span></div>').join('');
  }catch(e){document.getElementById('fileList').innerHTML='<p style="color:var(--danger);padding:20px">加载失败: '+e.message+'</p>'}
}
function formatSize(b){if(!b)return'';if(b<1024)return b+' B';if(b<1048576)return(b/1024).toFixed(1)+' KB';return(b/1048576).toFixed(1)+' MB'}
async function deleteFile(name){try{await fetch('/agent/delete-file',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:decodeURIComponent(name)})});refreshFileList()}catch(e){}}
async function saveConfig(){
  const provider=document.getElementById('cfgProvider').value;
  const apiKey=document.getElementById('cfgKey').value.trim();
  const apiUrl=document.getElementById('cfgUrl').value.trim();
  const remember=document.getElementById('cfgRemember').checked;
  const cfgStatus=document.getElementById('cfgStatus');
  cfgStatus.style.color='var(--muted)';cfgStatus.textContent='测试连接中...';
  try{
    const resp=await fetch('/api/model-status',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({external_api:{enabled:true,provider:provider,apiKey:apiKey,apiUrl:apiUrl}})});
    const data=await resp.json();
    if(data.available){cfgStatus.style.color='var(--success)';cfgStatus.textContent='✅ 连接成功! '+data.model;
      document.getElementById('apiStatus').className='status-indicator ok';document.getElementById('apiStatus').textContent='🟢 '+provider;
      if(remember&&apiKey){
        try{
          const bindResp=await fetch('/api/device/bind',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({provider:provider,api_key:apiKey,api_url:apiUrl,model:data.model||''})});
          const bindData=await bindResp.json();
          if(bindData.ok){cfgStatus.textContent+=' | 🔐 已绑定到此设备'}
          else{cfgStatus.textContent+=' | ⚠️ 设备绑定失败'}
        }catch(be){cfgStatus.textContent+=' | ⚠️ 绑定异常'}
      }
    }
    else{cfgStatus.style.color='var(--danger)';cfgStatus.textContent='❌ 连接失败: '+(data.message||'未知')}
  }catch(e){cfgStatus.style.color='var(--danger)';cfgStatus.textContent='❌ 请求失败: '+e.message}
}
async function loadConfig(){
  try{
    const resp=await fetch('/api/config');const data=await resp.json();
    if(data.provider){document.getElementById('cfgProvider').value=data.provider;
      document.getElementById('apiStatus').className='status-indicator ok';document.getElementById('apiStatus').textContent='🟢 '+data.provider}
    if(data.hasApi){
      try{
        const autoResp=await fetch('/api/account/auto-fill',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({provider:data.provider})});
        const autoData=await autoResp.json();
        if(autoData.found&&autoData.api_key){
          document.getElementById('cfgKey').value=autoData.api_key;
          if(autoData.api_url)document.getElementById('cfgUrl').value=autoData.api_url;
        }
      }catch(ae){}
    }
  }catch(e){}
}
async function refreshAccountInfo(){
  const statusEl=document.getElementById('accountStatus');
  statusEl.style.color='var(--muted)';statusEl.textContent='加载中...';
  try{
    const resp=await fetch('/api/device/info');const data=await resp.json();
    document.getElementById('deviceId').textContent=data.device_id||'-';
    document.getElementById('deviceName').textContent=data.device_name||'-';
    document.getElementById('devicePlatform').textContent=(data.platform||'-')+' / '+(data.arch||'-');
    document.getElementById('safeStorageStatus').textContent=data.safe_storage_available?'✅ 系统级加密可用':'⚠️ 使用AES-256降级加密';
    document.getElementById('safeStorageStatus').style.color=data.safe_storage_available?'var(--success)':'var(--muted)';
    document.getElementById('bindStatus').textContent=data.is_bound?'✅ 已绑定 '+String(data.bound_providers?.length||0)+' 个提供商':'❌ 未绑定';
    document.getElementById('bindStatus').style.color=data.is_bound?'var(--success)':'var(--danger)';
    const listEl=document.getElementById('boundProvidersList');
    if(data.bound_providers&&data.bound_providers.length>0){
      listEl.innerHTML=data.bound_providers.map(p=>'<div class="bound-provider"><div><span class="bound-provider-name">'+escapeHtml(p.name)+'</span><span style="color:var(--muted);margin-left:8px;font-size:11px">'+escapeHtml(p.model||'')+'</span></div><span class="bound-provider-del" onclick="unbindProvider(\\''+p.name+'\\')">🗑</span></div>').join('');
    }else{listEl.innerHTML='<p style="color:var(--muted);font-size:12px;padding:8px">暂无绑定的API提供商</p>'}
    statusEl.textContent='';
  }catch(e){statusEl.style.color='var(--danger)';statusEl.textContent='加载失败: '+e.message}
}
async function unbindProvider(name){
  if(!confirm('确定要解除 '+name+' 的设备绑定吗？'))return;
  try{
    const resp=await fetch('/api/device/unbind',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({provider:name})});
    const data=await resp.json();
    if(data.ok){refreshAccountInfo();loadConfig()}
  }catch(e){}
}
async function unbindAll(){
  if(!confirm('确定要清除所有设备绑定吗？此操作不可恢复！'))return;
  try{
    const resp=await fetch('/api/device/unbind',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({})});
    const data=await resp.json();
    if(data.ok){refreshAccountInfo();loadConfig();
      document.getElementById('apiStatus').className='status-indicator';document.getElementById('apiStatus').textContent='🔴 API未配置';
      document.getElementById('cfgKey').value='';document.getElementById('cfgUrl').value='';
    }
  }catch(e){}
}
fetch('/api/config').then(r=>r.json()).then(d=>{
  if(d.provider){document.getElementById('apiStatus').className='status-indicator ok';document.getElementById('apiStatus').textContent='🟢 '+d.provider}
  if(d.hasApi){
    fetch('/api/account/auto-fill',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({provider:d.provider})}).then(r=>r.json()).then(ad=>{
      if(ad.found&&ad.api_key){document.getElementById('cfgKey').value=ad.api_key;if(ad.api_url)document.getElementById('cfgUrl').value=ad.api_url}
    }).catch(()=>{});
  }
}).catch(()=>{});
`;
    }

    function getReadmeHtml() { return `<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Kaguya IDE - README</title>
<style>${getDocsStyles()}</style></head><body>
<div class="nav"><a href="/">🏠 首页</a><a href="/docs">📋 API文档</a><a href="/readme" class="active">📖 README</a></div>
<div class="container">
<h1>Kaguya IDE v${APP_VERSION}</h1>
<p class="sub">AI-Powered Development Environment — 面向开发、运营、增长与职场场景的高质量 AI 助手</p>

<div class="section"><h2>快速开始</h2>
<div class="card"><h3>桌面端直接运行（推荐）</h3>
<ol><li>解压安装包</li><li>双击 <code>Kaguya IDE.exe</code></li><li>在配置页面输入 API Key</li><li>开始对话</li></ol></div>
<div class="card"><h3>命令行启动（需要Python 3.9+）</h3>
<pre>conda activate DL
python start_server.py
python qwen3_web.py --port 58000</pre>
<p>访问 <code>http://127.0.0.1:58000</code></p></div>
<div class="card"><h3>使用Ollama本地模型</h3>
<pre>ollama pull qwen3.5:4b
python qwen3_web.py</pre></div>
</div>

<div class="section"><h2>核心功能</h2>
<table><tr><th>功能</th><th>说明</th></tr>
<tr><td>🤖 智能对话</td><td>流式响应、多轮对话、角色扮演</td></tr>
<tr><td>💻 代码助手</td><td>Python/JS/C/C++/Java/Go/Rust 在线执行</td></tr>
<tr><td>📁 文件管理</td><td>上传、分析、多文件操作</td></tr>
<tr><td>🛠 工具调用</td><td>网络搜索、代码执行、文件读写</td></tr>
<tr><td>📚 知识库/RAG</td><td>文档上传、向量检索、上下文增强</td></tr>
<tr><td>🎛 LoRA微调</td><td>模型低秩适配、在线训练与切换</td></tr>
<tr><td>🔄 工作流</td><td>可视化工作流编辑器、自动执行</td></tr>
<tr><td>📊 项目管理</td><td>Tasks、Milestones、Risks全生命周期</td></tr>
<tr><td>🧪 A/B实验</td><td>在线实验设计、指标分析</td></tr>
<tr><td>🚨 告警中心</td><td>自定义告警规则、实时监控</td></tr>
<tr><td>🧩 集成市场</td><td>第三方服务集成管理</td></tr>
<tr><td>🔐 安全框架</td><td>IP白名单、JWT认证、审计日志</td></tr></table>
</div>

<div class="section"><h2>命令行参数</h2>
<table><tr><th>参数</th><th>说明</th><th>默认值</th></tr>
<tr><td><code>--port</code></td><td>指定端口</td><td>5000</td></tr>
<tr><td><code>--host</code></td><td>绑定IP</td><td>127.0.0.1</td></tr>
<tr><td><code>--localhost-only</code></td><td>仅本地访问</td><td>false</td></tr>
<tr><td><code>--https</code></td><td>启用HTTPS</td><td>false</td></tr>
<tr><td><code>--cert</code></td><td>SSL证书路径</td><td>cert.pem</td></tr>
<tr><td><code>--key</code></td><td>SSL密钥路径</td><td>key.pem</td></tr>
<tr><td><code>--debug</code></td><td>调试模式</td><td>false</td></tr></table>
</div>

<div class="section"><h2>环境变量</h2>
<table><tr><th>变量</th><th>说明</th></tr>
<tr><td><code>KAGUYA_DESKTOP_MODE</code></td><td>桌面模式（禁用ngrok）</td></tr>
<tr><td><code>KAGUYA_PORT</code></td><td>指定端口</td></tr>
<tr><td><code>KAGUYA_SECRET_KEY</code></td><td>加密主密钥</td></tr>
<tr><td><code>KAGUYA_PERMISSION_MODE</code></td><td>权限模式: bypassPermissions</td></tr></table>
</div>

<div class="section"><h2>支持的API提供商</h2>
<table><tr><th>提供商</th><th>默认URL</th><th>模型</th></tr>
<tr><td>DeepSeek</td><td>https://api.deepseek.com</td><td>deepseek-chat</td></tr>
<tr><td>OpenAI</td><td>https://api.openai.com/v1</td><td>gpt-4o</td></tr>
<tr><td>Claude</td><td>https://api.anthropic.com</td><td>claude-3-7-sonnet</td></tr>
<tr><td>Qwen</td><td>https://dashscope.aliyuncs.com/compatible-mode/v1</td><td>qwen-plus</td></tr>
<tr><td>Moonshot</td><td>https://api.moonshot.cn/v1</td><td>moonshot-v1-8k</td></tr>
<tr><td>Zhipu</td><td>https://open.bigmodel.cn/api/paas/v4</td><td>glm-4-flash</td></tr>
<tr><td>Groq</td><td>https://api.groq.com/openai/v1</td><td>llama-3.3-70b</td></tr></table>
</div>

<div class="section"><h2>项目结构</h2>
<pre>
kaguya-desktop/
├── electron/             # Electron主进程
│   ├── main.js          # 主入口 + MiniServer
│   └── preload.js       # 预加载脚本
├── src/                  # Python源码
│   ├── qwen3_web.py     # Flask Web主应用
│   ├── kaguya_bootstrap.py # 核心引导层
│   ├── kaguya_agents.py # Agent系统
│   └── ...
├── kaguya_core/          # 核心框架
├── static/               # 前端资源
├── assets/               # 图片/图标
└── package.json          # 构建配置
</pre>
</div>
<div class="footer">Kaguya IDE v${APP_VERSION} · Built with Electron + Flask + Node.js · <a href="https://github.com/kaguya-ide/kaguya-ide">GitHub</a></div>
</div></body></html>`; }

    function getApiDocsHtml() { return `<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Kaguya IDE - API Reference</title>
<style>${getDocsStyles()}</style></head><body>
<div class="nav"><a href="/">🏠 首页</a><a href="/docs" class="active">📋 API文档</a><a href="/readme">📖 README</a></div>
<div class="container">
<h1>📋 API 接口文档</h1>
<p class="sub">Kaguya IDE v${APP_VERSION} · 完整API接口参考</p>
${generateApiDocSections()}
<div class="footer">注: <code>*</code> 标记的端点仅在Python后端(Flask)模式下可用，MiniServer模式仅支持核心API。</div>
</div></body></html>`; }

    function getDocsStyles() { return `
:root{--bg:#0a0a0f;--surface:#16161e;--border:#2a2a3a;--text:#e0e0e0;--muted:#888;--primary:#7c5cfc;--accent:#00d4ff}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif;line-height:1.6}
.nav{background:var(--surface);border-bottom:1px solid var(--border);padding:12px 24px;display:flex;gap:16px;position:sticky;top:0;z-index:10}
.nav a{color:var(--muted);text-decoration:none;font-size:13px;padding:6px 12px;border-radius:6px}
.nav a:hover,.nav a.active{color:var(--primary);background:rgba(124,92,252,0.1)}
.container{max-width:900px;margin:0 auto;padding:32px 24px 80px}
h1{font-size:28px;margin-bottom:4px;background:linear-gradient(135deg,var(--primary),var(--accent));-webkit-background-clip:text;-webkit-text-fill-color:transparent;display:inline-block}
.sub{color:var(--muted);margin-bottom:32px;font-size:14px}
.section{margin-bottom:40px}
.section h2{font-size:18px;color:var(--primary);margin-bottom:8px;padding-bottom:6px;border-bottom:1px solid var(--border)}
.section h3{font-size:15px;color:var(--accent);margin:16px 0 8px}
.card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:16px 20px;margin-bottom:12px}
.card p{color:var(--muted);font-size:13px;margin-bottom:6px}
.card ol,.card ul{padding-left:20px;color:var(--muted);font-size:13px}
.card li{margin-bottom:4px}
table{width:100%;border-collapse:collapse;font-size:13px}
th{background:var(--surface);color:var(--accent);text-align:left;padding:8px 12px;font-weight:600;border-bottom:2px solid var(--border)}
td{padding:8px 12px;border-bottom:1px solid var(--border)}
td code{background:rgba(124,92,252,0.1);padding:2px 6px;border-radius:4px;color:var(--accent);font-size:12px}
pre{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:14px;overflow-x:auto;font-size:12px;line-height:1.5;color:var(--text);margin:8px 0}
.method{display:inline-block;padding:2px 8px;border-radius:4px;font-size:10px;font-weight:700;margin-right:6px;min-width:48px;text-align:center}
.method.get{background:rgba(76,175,80,0.15);color:#4caf50}
.method.post{background:rgba(255,152,0,0.15);color:#ff9800}
.method.put{background:rgba(33,150,243,0.15);color:#2196f3}
.method.delete{background:rgba(239,83,80,0.15);color:#ef5350}
.api-group{margin:16px 0}
.api-item{display:flex;align-items:flex-start;padding:6px 0;border-bottom:1px solid rgba(42,42,58,0.5);font-size:13px}
.api-item .path{font-family:'Cascadia Code',Consolas,monospace;color:var(--text);flex:1;min-width:0}
.api-item .desc{color:var(--muted);flex:1;font-size:12px;margin-left:12px}
.api-badge{display:inline-block;font-size:9px;padding:1px 6px;border-radius:3px;margin-left:6px;font-weight:600}
.api-badge.mini{background:rgba(76,175,80,0.15);color:#4caf50}
.api-badge.full{background:rgba(255,152,0,0.15);color:#ff9800}
.footer{text-align:center;color:var(--muted);font-size:12px;margin-top:40px;padding:20px;border-top:1px solid var(--border)}
a{color:var(--primary);text-decoration:none}`; }

    function apiItem(method, path, desc, mode) { const badge = mode === 'mini' ? '<span class="api-badge mini">Mini</span>' : mode === 'full' ? '<span class="api-badge full">Full</span>' : ''; return '<div class="api-item"><span class="method ' + method + '">' + method.toUpperCase() + '</span><span class="path"><code>' + path + '</code>' + badge + '</span><span class="desc">' + desc + '</span></div>'; }

    function generateApiDocSections() {
        const sec = (title, items) => '<div class="section"><h2>' + title + '</h2><div class="api-group">' + items.join('') + '</div></div>';
        return [
            sec('💬 聊天 & 对话', [
                apiItem('post', '/chat', '发送聊天消息（流式SSE响应）', 'mini'),
                apiItem('post', '/stream', '发送流式聊天请求', 'full'),
                apiItem('post', '/api/chat', '发送聊天消息（与/chat等价）', 'mini'),
                apiItem('post', '/tts', '文本转语音', 'full'),
                apiItem('get', '/audio/&lt;filename&gt;', '获取生成的音频文件', 'full'),
                apiItem('get', '/chats/export', '导出所有聊天记录', 'full'),
                apiItem('get', '/api/roles', '获取所有角色卡列表', 'mini'),
                apiItem('get', '/api/prompts', '获取所有提示词模板', 'full'),
                apiItem('get', '/scenes/list', '获取场景模板列表', 'full'),
                apiItem('get', '/scenes/history', '获取场景对话历史', 'full'),
                apiItem('post', '/scenes/generate', '生成场景对话', 'full'),
            ]),
            sec('📁 文件管理', [
                apiItem('post', '/agent/upload-device-files', '上传设备文件（multipart）', 'mini'),
                apiItem('get', '/agent/list-files', '列出已上传文件', 'mini'),
                apiItem('post', '/agent/delete-file', '删除文件', 'mini'),
                apiItem('post', '/agent/file-write', '写入文件（Agent工具）', 'full'),
            ]),
            sec('🛠 工具 & 执行', [
                apiItem('post', '/tool/execute', '执行定义的工具', 'full'),
                apiItem('post', '/code/execute', '执行Python代码', 'full'),
                apiItem('post', '/web/search', '执行网页搜索', 'full'),
                apiItem('post', '/web/fetch', '获取网页内容', 'full'),
                apiItem('get', '/agent/tools', '获取Agent可用工具列表', 'full'),
            ]),
            sec('🤖 Agent系统', [
                apiItem('post', '/agent/run', '运行Agent任务', 'full'),
                apiItem('post', '/agent/permission/respond', '响应权限请求', 'full'),
                apiItem('get', '/agent/permission/config', '获取权限配置', 'full'),
                apiItem('post', '/agent/permission/config', '更新权限配置', 'full'),
                apiItem('post', '/agent/permission/rule', '添加/删除权限规则', 'full'),
                apiItem('get', '/agent/audit/logs', '获取Agent审计日志', 'full'),
                apiItem('get', '/agent/audit/stats', '获取Agent审计统计', 'full'),
                apiItem('get', '/agent/tasks', '获取后台任务列表', 'full'),
                apiItem('post', '/agent/tasks', '创建后台任务', 'full'),
            ]),
            sec('📚 知识库 / RAG', [
                apiItem('post', '/kb/add', '添加知识库条目', 'full'),
                apiItem('post', '/kb/search', '搜索知识库', 'full'),
                apiItem('post', '/rag/upload', '上传RAG文档', 'full'),
                apiItem('get', '/rag/documents', '获取RAG文档列表', 'full'),
                apiItem('post', '/rag/search', 'RAG语义搜索', 'full'),
                apiItem('get', '/rag/stats', 'RAG统计信息', 'full'),
                apiItem('post', '/rag/add_text', '添加文本到RAG', 'full'),
            ]),
            sec('🎛 LoRA & 微调', [
                apiItem('get', '/lora/list', '获取LoRA适配器列表', 'full'),
                apiItem('post', '/lora/load', '加载LoRA适配器', 'full'),
                apiItem('get', '/finetune/datasets', '获取微调数据集列表', 'full'),
                apiItem('post', '/finetune/dataset/upload', '上传微调数据集', 'full'),
                apiItem('get', '/finetune/jobs', '获取微调任务列表', 'full'),
                apiItem('post', '/finetune/job', '创建微调任务', 'full'),
            ]),
            sec('🔄 工作流', [
                apiItem('get', '/workflows', '获取工作流列表', 'full'),
                apiItem('post', '/workflow', '创建工作流', 'full'),
                apiItem('post', '/workflow/&lt;id&gt;/execute', '执行工作流', 'full'),
                apiItem('post', '/workflow/execute', '直接执行工作流', 'full'),
                apiItem('get', '/workflow/node-types', '获取节点类型列表', 'full'),
            ]),
            sec('🔐 认证 & 安全', [
                apiItem('post', '/auth/login', '用户登录', 'full'),
                apiItem('post', '/auth/register', '用户注册', 'full'),
                apiItem('post', '/auth/logout', '用户登出', 'full'),
                apiItem('get', '/auth/account', '获取账户信息', 'full'),
                apiItem('get', '/auth/setup', '获取认证配置状态', 'mini'),
                apiItem('get', '/security/status', '安全状态概览', 'full'),
                apiItem('get', '/security/audit', '安全审计日志', 'full'),
                apiItem('get', '/security/ip-whitelist', 'IP白名单管理', 'full'),
                apiItem('post', '/security/2fa/setup', '双因素认证设置', 'full'),
            ]),
            sec('👥 账户管理', [
                apiItem('get', '/account/profile', '获取/更新个人资料', 'full'),
                apiItem('get', '/account/tokens', 'API令牌管理', 'full'),
                apiItem('get', '/account/sessions', '会话管理', 'full'),
            ]),
            sec('📊 项目管理', [
                apiItem('get', '/project/overview', '项目概览', 'full'),
                apiItem('get', '/project/config', '项目配置', 'full'),
                apiItem('post', '/project/config', '更新项目配置', 'full'),
                apiItem('get', '/project/stats', '项目统计', 'full'),
                apiItem('get', '/project/tasks', '任务列表', 'full'),
                apiItem('post', '/project/tasks', '创建任务', 'full'),
                apiItem('get', '/project/milestones', '里程碑列表', 'full'),
                apiItem('post', '/project/milestones', '创建里程碑', 'full'),
                apiItem('get', '/project/risks', '风险列表', 'full'),
                apiItem('post', '/project/risks', '创建风险项', 'full'),
                apiItem('get', '/project/activity', '项目活动日志', 'full'),
                apiItem('get', '/project/export', '导出项目', 'full'),
                apiItem('post', '/project/import', '导入项目', 'full'),
            ]),
            sec('🧪 运营 & 实验', [
                apiItem('get', '/ops/overview', '运营概览', 'full'),
                apiItem('get', '/ops/campaigns', '营销活动列表', 'full'),
                apiItem('post', '/ops/campaigns', '创建营销活动', 'full'),
                apiItem('get', '/ab/experiments', 'A/B实验列表', 'full'),
                apiItem('post', '/ab/experiments', '创建A/B实验', 'full'),
                apiItem('get', '/release/plans', '发布计划列表', 'full'),
                apiItem('post', '/release/plans', '创建发布计划', 'full'),
                apiItem('get', '/alerts/rules', '告警规则列表', 'full'),
                apiItem('post', '/alerts/rules', '创建告警规则', 'full'),
            ]),
            sec('🧩 集成 & 部署', [
                apiItem('get', '/integrations', '集成列表', 'full'),
                apiItem('post', '/integrations', '添加集成', 'full'),
                apiItem('get', '/mcp/plugins', 'MCP插件列表', 'full'),
                apiItem('post', '/mcp/execute', '执行MCP工具', 'full'),
                apiItem('get', '/git/status', 'Git仓库状态', 'full'),
                apiItem('post', '/deploy/execute', '执行部署', 'full'),
            ]),
            sec('🗄 内存 & 记忆', [
                apiItem('get', '/memory/stats', '记忆系统统计', 'full'),
                apiItem('post', '/memory/search', '搜索记忆', 'full'),
                apiItem('post', '/memory', '添加记忆', 'full'),
                apiItem('put', '/memory/&lt;id&gt;/pin', '置顶记忆', 'full'),
                apiItem('get', '/memory/profile', '获取用户画像', 'full'),
                apiItem('post', '/memory/consolidate', '合并压缩记忆', 'full'),
            ]),
            sec('🎨 媒体资源', [
                apiItem('get', '/header-img', '顶部头像（辉夜姬）', 'mini'),
                apiItem('get', '/hero-img', '欢迎页主视觉图', 'mini'),
                apiItem('get', '/welcome-img', '欢迎页动态图', 'mini'),
                apiItem('get', '/background', '背景图片', 'full'),
                apiItem('get', '/wallpaper', '壁纸', 'full'),
                apiItem('get', '/favicon.ico', '网站图标', 'full'),
                apiItem('post', '/multimodal/upload', '上传多模态图片', 'full'),
                apiItem('post', '/multimodal/chat', '多模态对话', 'full'),
            ]),
            sec('⚙️ 配置 & 系统', [
                apiItem('get', '/api/config', '获取API配置状态', 'mini'),
                apiItem('post', '/api/config', '保存API配置', 'mini'),
                apiItem('post', '/api/model-status', '测试API连接', 'mini'),
                apiItem('get', '/kaguya/system/status', '系统状态', 'mini'),
                apiItem('get', '/kaguya/features/flags', '功能开关列表', 'full'),
                apiItem('get', '/external/config', '外部API配置', 'full'),
                apiItem('post', '/external/config', '更新外部API配置', 'full'),
                apiItem('post', '/external/test', '测试外部API', 'full'),
                apiItem('get', '/privacy/settings', '隐私设置', 'full'),
                apiItem('get', '/performance/stats', '性能统计', 'full'),
                apiItem('get', '/system/metrics', '系统指标', 'full'),
            ]),
            sec('🔐 账户 & 设备绑定', [
                apiItem('get', '/api/device/info', '获取设备信息与绑定状态', 'mini'),
                apiItem('post', '/api/device/bind', '绑定API提供商到设备（加密存储）', 'mini'),
                apiItem('post', '/api/device/unbind', '解除设备绑定（指定provider或全部）', 'mini'),
                apiItem('get', '/api/account/saved-config', '获取已保存配置（密钥脱敏）', 'mini'),
                apiItem('post', '/api/account/auto-fill', '自动填充指定提供商的API密钥', 'mini'),
            ]),
        ].join('');
    }

    const server = http.createServer((req, res) => {
        const parsedUrl = url.parse(req.url, true);
        const pathname = parsedUrl.pathname;

        res.setHeader('Access-Control-Allow-Origin', '*');
        res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, DELETE');
        res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

        if (req.method === 'OPTIONS') { res.writeHead(200); res.end(); return; }

        if (pathname === '/') {
            res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
            res.end(getMainPageHtml());
            return;
        }

        if (pathname === '/docs') {
            res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
            res.end(getApiDocsHtml());
            return;
        }

        if (pathname === '/readme') {
            res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
            res.end(getReadmeHtml());
            return;
        }

        if (pathname === '/api/model-status' && req.method === 'POST') {
            let body = '';
            req.on('data', c => body += c);
            req.on('end', () => {
                try {
                    const data = JSON.parse(body);
                    const extApi = data.external_api || {};
                    if (extApi.apiKey && extApi.provider) {
                        savedApiConfig = { enabled: true, provider: extApi.provider, apiKey: extApi.apiKey, apiUrl: extApi.apiUrl || '', model: extApi.model || (providerUrls[extApi.provider]||{}).model };
                        const pInfo = providerUrls[extApi.provider] || {};
                        const testUrl = (extApi.apiUrl || pInfo.url) + (pInfo.type === 'openai' ? '/models' : '/v1/models');
                        const opts = { hostname: new URL(testUrl).hostname, path: new URL(testUrl).pathname, method: 'GET', headers: pInfo.type === 'openai' ? { 'Authorization': 'Bearer ' + extApi.apiKey } : { 'x-api-key': extApi.apiKey, 'anthropic-version': '2023-06-01' }, timeout: 10000 };
                        const testReq = https.request(opts, (testRes) => {
                            serveJSON(res, 200, { available: testRes.statusCode < 500, provider: extApi.provider, model: extApi.model || pInfo.model });
                        });
                        testReq.on('error', (e) => serveJSON(res, 200, { available: false, message: e.message }));
                        testReq.setTimeout(10000, () => { testReq.destroy(); serveJSON(res, 200, { available: false, message: 'Connection timeout' }); });
                        testReq.end();
                    } else { serveJSON(res, 200, { available: false, message: 'No API key' }); }
                } catch (e) { serveJSON(res, 400, { error: e.message }); }
            });
            return;
        }

        if ((pathname === '/chat' || pathname === '/api/chat') && req.method === 'POST') {
            let body = '';
            req.on('data', c => body += c);
            req.on('end', () => {
                if (!savedApiConfig) { serveJSON(res, 503, { error: '请先在配置页面设置API Key' }); return; }
                try {
                    const chatData = JSON.parse(body);
                    const pInfo = providerUrls[savedApiConfig.provider] || {};
                    const apiBase = savedApiConfig.apiUrl || pInfo.url;
                    const targetUrl = apiBase + (pInfo.type === 'openai' ? '/chat/completions' : '/v1/messages');
                    const targetParsed = new URL(targetUrl);

                    const msgBody = pInfo.type === 'openai' ? JSON.stringify({
                        model: savedApiConfig.model || pInfo.model,
                        messages: chatData.messages || [],
                        stream: chatData.stream !== false,
                        temperature: 0.3, max_tokens: 4096,
                    }) : JSON.stringify({
                        model: savedApiConfig.model || pInfo.model,
                        messages: chatData.messages || [],
                        stream: chatData.stream !== false, max_tokens: 4096,
                    });

                    const headers = pInfo.type === 'openai' ? {
                        'Content-Type': 'application/json', 'Authorization': 'Bearer ' + savedApiConfig.apiKey,
                    } : { 'Content-Type': 'application/json', 'x-api-key': savedApiConfig.apiKey, 'anthropic-version': '2023-06-01' };

                    const proxyReq = https.request({
                        hostname: targetParsed.hostname, path: targetParsed.pathname, method: 'POST', headers,
                    }, (proxyRes) => {
                        if (chatData.stream !== false) {
                            res.writeHead(200, { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache', 'Connection': 'keep-alive' });
                        } else {
                            res.writeHead(200, { 'Content-Type': 'application/json' });
                        }
                        proxyRes.pipe(res);
                    });
                    proxyReq.on('error', (e) => { res.end(JSON.stringify({ error: e.message })); });
                    proxyReq.write(msgBody);
                    proxyReq.end();
                } catch (e) { serveJSON(res, 500, { error: e.message }); }
            });
            return;
        }

        if (pathname === '/api/config' && req.method === 'GET') {
            serveJSON(res, 200, { mode: 'mini', hasApi: !!savedApiConfig, provider: savedApiConfig?.provider || null });
            return;
        }

        if (pathname === '/api/config' && req.method === 'POST') {
            let body = '';
            req.on('data', c => body += c);
            req.on('end', () => {
                try { savedApiConfig = JSON.parse(body); serveJSON(res, 200, { ok: true }); }
                catch (e) { serveJSON(res, 400, { error: e.message }); }
            });
            return;
        }

        if (pathname === '/agent/upload-device-files' && req.method === 'POST') {
            const contentType = req.headers['content-type'] || '';
            if (!contentType.includes('multipart/form-data')) { serveJSON(res, 400, { error: '需要multipart/form-data' }); return; }

            const boundaryMatch = contentType.match(/boundary=(.+)/);
            if (!boundaryMatch) { serveJSON(res, 400, { error: '找不到boundary' }); return; }
            const boundary = '--' + boundaryMatch[1].trim();

            let rawBody = Buffer.alloc(0);
            req.on('data', c => rawBody = Buffer.concat([rawBody, c]));
            req.on('end', () => {
                try {
                    const parts = [];
                    const str = rawBody.toString('binary');
                    const sections = str.split(boundary).slice(1, -1);
                    for (const sec of sections) {
                        const headerEnd = sec.indexOf('\r\n\r\n');
                        if (headerEnd < 0) continue;
                        const headers = sec.slice(0, headerEnd);
                        const content = sec.slice(headerEnd + 4, sec.endsWith('\r\n') ? sec.length - 2 : sec.length);
                        const nameMatch = headers.match(/name="([^"]+)"/);
                        const filenameMatch = headers.match(/filename="([^"]+)"/);
                        if (nameMatch && filenameMatch) {
                            parts.push({ name: filenameMatch[1], data: Buffer.from(content, 'binary') });
                        }
                    }
                    if (!parts.length) { serveJSON(res, 400, { error: 'No files found' }); return; }
                    const imported = [];
                    for (const p of parts) {
                        const fname = path.basename(p.name);
                        const dst = path.join(fileWorkspaceDir, fname);
                        fs.writeFileSync(dst, p.data);
                        imported.push({ name: fname, size: p.data.length, path: dst });
                    }
                    serveJSON(res, 200, { imported: imported, errors: [] });
                } catch (e) { serveJSON(res, 500, { error: e.message }); }
            });
            return;
        }

        if (pathname === '/agent/list-files' && req.method === 'GET') {
            try {
                const entries = fs.readdirSync(fileWorkspaceDir, { withFileTypes: true });
                const files = entries.filter(e => e.isFile()).map(e => {
                    const stat = fs.statSync(path.join(fileWorkspaceDir, e.name));
                    return { name: e.name, size: stat.size, mtime: stat.mtime.toISOString() };
                });
                serveJSON(res, 200, { files });
            } catch (e) { serveJSON(res, 200, { files: [] }); }
            return;
        }

        if (pathname === '/agent/delete-file' && req.method === 'POST') {
            let body = '';
            req.on('data', c => body += c);
            req.on('end', () => {
                try {
                    const data = JSON.parse(body);
                    const target = path.join(fileWorkspaceDir, path.basename(data.name || ''));
                    if (fs.existsSync(target)) { fs.unlinkSync(target); serveJSON(res, 200, { ok: true }); }
                    else { serveJSON(res, 404, { error: 'File not found' }); }
                } catch (e) { serveJSON(res, 500, { error: e.message }); }
            });
            return;
        }

        if (pathname === '/api/device/info' && req.method === 'GET') {
            const identity = getDeviceIdentity();
            const vault = loadDeviceVault();
            const boundProviders = vault ? Object.entries(vault.providers || {})
                .filter(([_, v]) => v.api_key)
                .map(([name, v]) => ({ name, model: v.model, bound_at: v.bound_at })) : [];
            serveJSON(res, 200, {
                device_id: identity.fingerprint,
                device_name: identity.device_name,
                platform: identity.platform,
                arch: identity.arch,
                username: identity.username,
                is_bound: !!vault,
                active_provider: vault?.active_provider || null,
                bound_providers: boundProviders,
                safe_storage_available: isSafeStorageAvailable(),
                vault_created: vault?.bound_at || null,
            });
            return;
        }

        if (pathname === '/api/device/bind' && req.method === 'POST') {
            let body = '';
            req.on('data', c => body += c);
            req.on('end', () => {
                try {
                    const data = JSON.parse(body);
                    const provider = data.provider;
                    const apiKey = (data.api_key || '').trim();
                    const apiUrl = (data.api_url || '').trim();
                    const model = (data.model || '').trim();
                    if (!provider || !apiKey) {
                        serveJSON(res, 400, { error: 'provider and api_key are required' });
                        return;
                    }
                    const existingVault = loadDeviceVault() || { active_provider: provider, providers: {} };
                    existingVault.active_provider = provider;
                    existingVault.providers[provider] = {
                        api_url: apiUrl || (providerUrls[provider] || {}).url || '',
                        api_key: apiKey,
                        model: model || (providerUrls[provider] || {}).model || '',
                        bound_at: new Date().toISOString(),
                    };
                    const saved = saveDeviceVault(existingVault);
                    if (saved) {
                        savedApiConfig = {
                            enabled: true,
                            provider: provider,
                            apiKey: apiKey,
                            apiUrl: apiUrl || (providerUrls[provider] || {}).url || '',
                            model: model || (providerUrls[provider] || {}).model || '',
                        };
                        serveJSON(res, 200, { ok: true, message: 'Device bound successfully', provider: provider });
                    } else {
                        serveJSON(res, 500, { error: 'Failed to save device vault' });
                    }
                } catch (e) { serveJSON(res, 400, { error: e.message }); }
            });
            return;
        }

        if (pathname === '/api/device/unbind' && req.method === 'POST') {
            let body = '';
            req.on('data', c => body += c);
            req.on('end', () => {
                try {
                    const data = JSON.parse(body);
                    const provider = data.provider;
                    if (provider) {
                        const vault = loadDeviceVault();
                        if (vault && vault.providers[provider]) {
                            delete vault.providers[provider];
                            if (vault.active_provider === provider) {
                                const remaining = Object.keys(vault.providers);
                                vault.active_provider = remaining.length > 0 ? remaining[0] : '';
                            }
                            saveDeviceVault(vault);
                            if (savedApiConfig?.provider === provider) {
                                savedApiConfig = null;
                            }
                            serveJSON(res, 200, { ok: true, message: `Unbound ${provider}` });
                        } else {
                            serveJSON(res, 404, { error: 'Provider not found in vault' });
                        }
                    } else {
                        clearDeviceVault();
                        savedApiConfig = null;
                        serveJSON(res, 200, { ok: true, message: 'All device bindings cleared' });
                    }
                } catch (e) { serveJSON(res, 400, { error: e.message }); }
            });
            return;
        }

        if (pathname === '/api/account/saved-config' && req.method === 'GET') {
            const vault = loadDeviceVault();
            if (vault) {
                const maskedProviders = {};
                for (const [name, cfg] of Object.entries(vault.providers || {})) {
                    const key = cfg.api_key || '';
                    maskedProviders[name] = {
                        api_url: cfg.api_url,
                        api_key_masked: key ? key.substring(0, 4) + '****' + key.substring(key.length - 4) : '',
                        api_key_length: key.length,
                        model: cfg.model,
                        bound_at: cfg.bound_at,
                    };
                }
                serveJSON(res, 200, {
                    is_bound: true,
                    active_provider: vault.active_provider,
                    providers: maskedProviders,
                    device_name: vault.device_name,
                });
            } else {
                serveJSON(res, 200, { is_bound: false, active_provider: null, providers: {} });
            }
            return;
        }

        if (pathname === '/api/account/auto-fill' && req.method === 'POST') {
            let body = '';
            req.on('data', c => body += c);
            req.on('end', () => {
                try {
                    const data = JSON.parse(body);
                    const provider = data.provider;
                    const vault = loadDeviceVault();
                    if (vault && vault.providers[provider]) {
                        const cfg = vault.providers[provider];
                        serveJSON(res, 200, {
                            found: true,
                            provider: provider,
                            api_key: cfg.api_key,
                            api_url: cfg.api_url,
                            model: cfg.model,
                        });
                    } else {
                        serveJSON(res, 200, { found: false });
                    }
                } catch (e) { serveJSON(res, 400, { error: e.message }); }
            });
            return;
        }

        if (pathname === '/kaguya/system/status') {
            serveJSON(res, 200, { initialized: true, mode: 'mini', version: APP_VERSION, provider: savedApiConfig?.provider || null, errors: [] });
            return;
        }

        if (pathname === '/api/roles' || pathname === '/lora/list' || pathname === '/kaguya/features/flags') {
            serveJSON(res, 200, []);
            return;
        }

        if (pathname === '/api/prompts') {
            serveJSON(res, 200, { prompts: [] });
            return;
        }

        if (pathname === '/auth/setup') {
            serveJSON(res, 200, { setup: false });
            return;
        }

        if (['/header-img', '/hero-img', '/welcome-img', '/deepseek-icon', '/sidebar-icon', '/favicon.ico'].includes(pathname)) {
            const mapped = { '/header-img': 'kaguya-header.png', '/hero-img': 'kaguya-hero.png', '/welcome-img': 'kaguya-welcome.png' };
            const fname = mapped[pathname];
            if (fname) {
                const imgPath = path.join(getResourcePath(), 'assets', fname);
                if (fs.existsSync(imgPath)) { res.writeHead(200, { 'Content-Type': 'image/png' }); res.end(fs.readFileSync(imgPath)); return; }
            }
            serveJSON(res, 404, { error: 'Not found' });
            return;
        }

        serveJSON(res, 404, { error: 'Not found', hint: 'Mini server mode' });
    });

    server.listen(port, '127.0.0.1', () => {
        console.log(`[MiniServer] Running on http://127.0.0.1:${port}`);
    });
    miniServer = server;
    return server;
}

function createSetupWindow() {
    if (mainWindow) {
        mainWindow.focus();
        return;
    }

    const setupPort = serverPort || DEFAULT_PORT;
    if (!miniServer) {
        startMiniServer(setupPort);
    }

    const iconPath = path.join(__dirname, '..', 'assets', process.platform === 'win32' ? 'kaguya.ico' : 'kaguya.png');
    const windowOpts = {
        width: 1200,
        height: 800,
        minWidth: 800,
        minHeight: 600,
        title: APP_NAME,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, 'preload.js'),
            sandbox: false,
        },
        show: false,
        backgroundColor: '#0a0a0f',
    };
    if (fs.existsSync(iconPath)) {
        windowOpts.icon = iconPath;
    }
    mainWindow = new BrowserWindow(windowOpts);

    mainWindow.loadURL(`http://127.0.0.1:${setupPort}/`);

    mainWindow.once('ready-to-show', () => {
        mainWindow.show();
        mainWindow.focus();
    });

    mainWindow.on('closed', () => {
        mainWindow = null;
    });

    setupMenu();
}

function createWindow(port) {
    if (mainWindow) {
        mainWindow.focus();
        return;
    }

    const iconPath = path.join(__dirname, '..', 'assets', process.platform === 'win32' ? 'kaguya.ico' : 'kaguya.png');
    const windowOpts = {
        width: 1400,
        height: 900,
        minWidth: 1024,
        minHeight: 680,
        title: APP_NAME,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, 'preload.js'),
            webviewTag: true,
            sandbox: false,
        },
        show: false,
        backgroundColor: '#0a0a0f',
        titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
    };
    if (fs.existsSync(iconPath)) {
        windowOpts.icon = iconPath;
    }
    mainWindow = new BrowserWindow(windowOpts);

    const url = `http://127.0.0.1:${port}/`;
    mainWindow.loadURL(url);

    mainWindow.webContents.setWindowOpenHandler(({ url: openUrl }) => {
        if (openUrl.startsWith('http://127.0.0.1:') || openUrl.startsWith('http://localhost:')) {
            return { action: 'allow' };
        }
        require('electron').shell.openExternal(openUrl);
        return { action: 'deny' };
    });

    mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDesc) => {
        console.error(`[Main] Failed to load: ${errorCode} ${errorDesc}`);
        if (errorCode === -2 || errorDesc.includes('ERR_CONNECTION_REFUSED')) {
            console.log('[Main] Retrying in 3 seconds...');
            setTimeout(() => {
                if (mainWindow && !mainWindow.isDestroyed()) {
                    mainWindow.loadURL(url);
                }
            }, 3000);
        }
    });

    mainWindow.once('ready-to-show', () => {
        mainWindow.show();
        mainWindow.focus();
    });

    mainWindow.on('closed', () => {
        mainWindow = null;
    });

    setupMenu();
}

function setupMenu() {
    const template = [
        {
            label: APP_NAME,
            submenu: [
                { label: `About ${APP_NAME}`, click: () => showAboutDialog() },
                { type: 'separator' },
                { label: 'Preferences', accelerator: 'CmdOrCtrl+,', click: () => mainWindow?.webContents.send('open-settings') },
                { type: 'separator' },
                { role: 'quit' },
            ],
        },
        {
            label: 'Edit',
            submenu: [
                { role: 'undo' },
                { role: 'redo' },
                { type: 'separator' },
                { role: 'cut' },
                { role: 'copy' },
                { role: 'paste' },
                { role: 'selectAll' },
            ],
        },
        {
            label: 'View',
            submenu: [
                { role: 'reload' },
                { role: 'forceReload' },
                { role: 'toggleDevTools' },
                { type: 'separator' },
                { role: 'resetZoom' },
                { role: 'zoomIn' },
                { role: 'zoomOut' },
                { type: 'separator' },
                { role: 'togglefullscreen' },
                { type: 'separator' },
                { label: 'Toggle Terminal', accelerator: 'CmdOrCtrl+J', click: () => mainWindow?.webContents.send('toggle-terminal') },
            ],
        },
        {
            label: 'Terminal',
            submenu: [
                { label: 'New Terminal', accelerator: 'CmdOrCtrl+Shift+`', click: () => createTerminalSession() },
                { label: 'Clear Terminal', click: () => mainWindow?.webContents.send('clear-terminal') },
            ],
        },
        {
            label: 'Help',
            submenu: [
                { label: 'Documentation', click: () => shell.openExternal('https://github.com/kaguya-ide/docs') },
                { label: 'Report Issue', click: () => shell.openExternal('https://github.com/kaguya-ide/issues') },
            ],
        },
    ];
    Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

function showAboutDialog() {
    dialog.showMessageBoxSync(mainWindow, {
        type: 'info',
        title: `About ${APP_NAME}`,
        message: APP_NAME,
        detail: `Version: ${APP_VERSION}\nPlatform: ${process.platform}\nElectron: ${process.versions.electron}\n\nAI-Powered Development Environment\n\n© 2026 Kaguya. All rights reserved.`,
    });
}

function createTray() {
    const iconPath = path.join(__dirname, '..', 'assets', process.platform === 'win32' ? 'kaguya.ico' : 'kaguya.png');
    if (!fs.existsSync(iconPath)) return;

    tray = new Tray(iconPath);
    const contextMenu = Menu.buildFromTemplate([
        { label: 'Open Kaguya IDE', click: () => mainWindow?.show() || createWindow(serverPort) },
        { label: 'New Terminal', click: () => createTerminalSession() },
        { type: 'separator' },
        { label: 'Quit', click: () => app.quit() },
    ]);
    tray.setToolTip(APP_NAME);
    tray.setContextMenu(contextMenu);
    tray.on('double-click', () => mainWindow?.show() || createWindow(serverPort));
}

// ========== IPC: Terminal / Shell ==========

const TERMINAL_DANGEROUS_PATTERNS = [
    /\brm\s+(-rf|-r|-f)\s+([\/~]|C:\\)/i,
    /\bdel\s+\/[sfq]\s+[A-Z]:\\/i,
    /\bformat\s+[a-z]:/i,
    /\bshutdown\b/i,
    /\breboot\b/i,
    /\bhalt\b/i,
    /\bpoweroff\b/i,
    /:\(\)\{\s*\|\s*&\s*\}\s*;/,
    /\bdd\s+if=.*of=\/dev\//i,
    /\bnet\s+(user|localgroup|share|stop|start)\s/i,
    /\breg\s+(add|delete|import|export)\b/i,
    /\bicacls\b/i,
    /\brunas\s+\/user:/i,
];

function isTerminalCommandDangerous(cmd) {
    const trimmed = cmd.trim();
    if (!trimmed) return false;
    for (const pattern of TERMINAL_DANGEROUS_PATTERNS) {
        if (pattern.test(trimmed)) return true;
    }
    return false;
}

function createTerminalSession(cwd) {
    const sessionId = `term_${Date.now()}_${Math.random().toString(36).substr(2, 6)}`;
    const shellPath = getShellPath();
    const workDir = cwd || getResourcePath();

    const shellArgs = process.platform === 'win32' ? [] : ['-l'];

    const proc = spawn(shellPath, shellArgs, {
        cwd: workDir,
        env: Object.assign({}, process.env, {
            'TERM': 'xterm-256color',
            'COLORTERM': 'truecolor',
            'KAGUYA_TERMINAL': sessionId,
        }),
        stdio: ['pipe', 'pipe', 'pipe'],
        windowsHide: false,
    });

    const session = { id: sessionId, process: proc, cwd: workDir };

    proc.stdout.on('data', (data) => {
        mainWindow?.webContents.send('terminal-data', { sessionId, data: data.toString('utf8'), stream: 'stdout' });
    });

    proc.stderr.on('data', (data) => {
        mainWindow?.webContents.send('terminal-data', { sessionId, data: data.toString('utf8'), stream: 'stderr' });
    });

    proc.on('close', (code) => {
        mainWindow?.webContents.send('terminal-exit', { sessionId, code });
        terminalSessions.delete(sessionId);
    });

    proc.on('error', (err) => {
        mainWindow?.webContents.send('terminal-error', { sessionId, error: err.message });
        terminalSessions.delete(sessionId);
    });

    terminalSessions.set(sessionId, session);
    mainWindow?.webContents.send('terminal-created', { sessionId, shell: shellPath, cwd: workDir });
    return sessionId;
}

ipcMain.handle('terminal-create', (event, opts) => {
    return createTerminalSession(opts?.cwd);
});

ipcMain.on('terminal-write', (event, { sessionId, data }) => {
    const session = terminalSessions.get(sessionId);
    if (session && session.process.stdin.writable) {
        const lines = data.split('\n');
        for (const line of lines) {
            if (line.trim() && isTerminalCommandDangerous(line)) {
                mainWindow?.webContents.send('terminal-data', {
                    sessionId,
                    data: `\r\n\x1b[31m[BLOCKED] Dangerous command blocked: ${line.trim()}\x1b[0m\r\n`,
                    stream: 'stderr'
                });
                continue;
            }
            session.process.stdin.write(line + '\n');
        }
    }
});

ipcMain.on('terminal-resize', (event, { sessionId, cols, rows }) => {
    // Basic shell doesn't support resize; PTY would be needed for full support
});

ipcMain.on('terminal-kill', (event, { sessionId }) => {
    const session = terminalSessions.get(sessionId);
    if (session) {
        session.process.kill();
        terminalSessions.delete(sessionId);
    }
});

// ========== IPC: File System ==========

ipcMain.handle('fs-readFile', async (event, filePath, options) => {
    try {
        const encoding = options?.encoding || 'utf-8';
        const content = await fs.promises.readFile(filePath, encoding);
        return { success: true, content };
    } catch (err) {
        return { success: false, error: err.message, code: err.code };
    }
});

ipcMain.handle('fs-writeFile', async (event, filePath, content, options) => {
    try {
        const dir = path.dirname(filePath);
        await fs.promises.mkdir(dir, { recursive: true });
        await fs.promises.writeFile(filePath, content, options?.encoding || 'utf-8');
        return { success: true };
    } catch (err) {
        return { success: false, error: err.message, code: err.code };
    }
});

ipcMain.handle('fs-readDir', async (event, dirPath, options) => {
    try {
        const entries = await fs.promises.readdir(dirPath, { withFileTypes: true });
        const result = entries.map(entry => ({
            name: entry.name,
            isFile: entry.isFile(),
            isDirectory: entry.isDirectory(),
            isSymbolicLink: entry.isSymbolicLink(),
            path: path.join(dirPath, entry.name),
        }));
        return { success: true, entries: result };
    } catch (err) {
        return { success: false, error: err.message, code: err.code };
    }
});

ipcMain.handle('fs-stat', async (event, filePath) => {
    try {
        const stat = await fs.promises.stat(filePath);
        return {
            success: true,
            isFile: stat.isFile(),
            isDirectory: stat.isDirectory(),
            size: stat.size,
            mtime: stat.mtimeMs,
            ctime: stat.ctimeMs,
            mode: stat.mode,
        };
    } catch (err) {
        return { success: false, error: err.message, code: err.code };
    }
});

ipcMain.handle('fs-mkdir', async (event, dirPath, options) => {
    try {
        await fs.promises.mkdir(dirPath, { recursive: options?.recursive ?? true });
        return { success: true };
    } catch (err) {
        return { success: false, error: err.message };
    }
});

ipcMain.handle('fs-remove', async (event, filePath) => {
    try {
        const stat = await fs.promises.stat(filePath);
        if (stat.isDirectory()) {
            await fs.promises.rm(filePath, { recursive: true, force: true });
        } else {
            await fs.promises.unlink(filePath);
        }
        return { success: true };
    } catch (err) {
        return { success: false, error: err.message };
    }
});

ipcMain.handle('fs-rename', async (event, oldPath, newPath) => {
    try {
        await fs.promises.rename(oldPath, newPath);
        return { success: true };
    } catch (err) {
        return { success: false, error: err.message };
    }
});

ipcMain.handle('fs-copy', async (event, src, dest) => {
    try {
        await fs.promises.copyFile(src, dest);
        return { success: true };
    } catch (err) {
        return { success: false, error: err.message };
    }
});

ipcMain.handle('fs-exists', async (event, filePath) => {
    try {
        await fs.promises.access(filePath);
        return true;
    } catch {
        return false;
    }
});

// ========== IPC: Shell Execution ==========

ipcMain.handle('shell-execute', async (event, command, options) => {
    return new Promise((resolve) => {
        const cwd = options?.cwd || getResourcePath();
        const timeout = options?.timeout || 30000;
        const env = Object.assign({}, process.env, options?.env || {});

        const proc = exec(command, { cwd, env, timeout, maxBuffer: 10 * 1024 * 1024 }, (error, stdout, stderr) => {
            resolve({
                success: !error,
                stdout: stdout || '',
                stderr: stderr || '',
                code: error ? error.code || 1 : 0,
                signal: error?.signal || null,
            });
        });
    });
});

ipcMain.handle('shell-openExternal', async (event, url) => {
    shell.openExternal(url);
    return { success: true };
});

ipcMain.handle('shell-showItemInFolder', async (event, filePath) => {
    shell.showItemInFolder(filePath);
    return { success: true };
});

ipcMain.handle('shell-openPath', async (event, filePath) => {
    const result = await shell.openPath(filePath);
    return { success: !result, error: result || null };
});

// ========== IPC: Dialog ==========

ipcMain.handle('dialog-openFile', async (event, options) => {
    const result = await dialog.showOpenDialog(mainWindow, {
        title: options?.title || 'Open File',
        defaultPath: options?.defaultPath,
        filters: options?.filters,
        properties: ['openFile', ...(options?.multi ? ['multiSelections'] : [])],
    });
    return { canceled: result.canceled, filePaths: result.filePaths };
});

ipcMain.handle('dialog-openFolder', async (event, options) => {
    const result = await dialog.showOpenDialog(mainWindow, {
        title: options?.title || 'Open Folder',
        defaultPath: options?.defaultPath,
        properties: ['openDirectory'],
    });
    return { canceled: result.canceled, filePaths: result.filePaths };
});

ipcMain.handle('dialog-saveFile', async (event, options) => {
    const result = await dialog.showSaveDialog(mainWindow, {
        title: options?.title || 'Save File',
        defaultPath: options?.defaultPath,
        filters: options?.filters,
    });
    return { canceled: result.canceled, filePath: result.filePath };
});

// ========== IPC: App Info ==========

ipcMain.handle('app-getInfo', () => ({
    name: APP_NAME,
    version: APP_VERSION,
    platform: process.platform,
    arch: process.arch,
    electronVersion: process.versions.electron,
    chromeVersion: process.versions.chrome,
    nodeVersion: process.versions.node,
    homeDir: os.homedir(),
    tempDir: os.tmpdir(),
    resourcePath: getResourcePath(),
}));

ipcMain.handle('app-getTheme', () => nativeTheme.shouldUseDarkColors ? 'dark' : 'light');

// ========== Lifecycle ==========

function stopPythonServer() {
    if (pythonProcess) {
        console.log('[Main] Stopping Python server...');
        try {
            if (process.platform === 'win32') {
                exec(`taskkill /pid ${pythonProcess.pid} /T /F`, (err) => {
                    if (err) pythonProcess.kill();
                });
            } else {
                pythonProcess.kill('SIGTERM');
                setTimeout(() => {
                    if (pythonProcess) pythonProcess.kill('SIGKILL');
                }, 5000);
            }
        } catch (e) {
            pythonProcess.kill();
        }
        pythonProcess = null;
    }

    for (const [id, session] of terminalSessions) {
        try { session.process.kill(); } catch (e) {}
    }
    terminalSessions.clear();
}

app.on('ready', async () => {
    try {
        setupAutoUpdater();
        
        const externalPort = process.env.KAGUYA_PORT ? parseInt(process.env.KAGUYA_PORT) : null;
        
        if (externalPort) {
            let serverRunning = false;
            try {
                await new Promise((resolve, reject) => {
                    const req = require('http').get(`http://127.0.0.1:${externalPort}/`, (res) => {
                        res.resume();
                        resolve();
                    });
                    req.on('error', reject);
                    req.setTimeout(2000, () => { req.destroy(); reject(new Error('timeout')); });
                });
                serverRunning = true;
            } catch (e) {
                serverRunning = false;
            }
            
            if (serverRunning) {
                serverPort = externalPort;
                console.log(`[Main] Using existing server on port ${serverPort}`);
                createWindow(serverPort);
                createTray();
            } else {
                serverPort = externalPort;
                try {
                    await startPythonServer(serverPort);
                    console.log('[Main] Python server started successfully');
                    createWindow(serverPort);
                    createTray();
                } catch (err) {
                    console.error('[Main] Python server failed:', err);
                    console.log('[Main] Showing setup page instead of quitting');
                    serverPort = 0;
                    createSetupWindow();
                    createTray();
                }
            }
        } else {
            serverPort = await findFreePort();
            console.log(`[Main] Using port ${serverPort}`);
            try {
                await startPythonServer(serverPort);
                console.log('[Main] Python server started successfully');
                createWindow(serverPort);
                createTray();
            } catch (err) {
                console.error('[Main] Python server failed:', err);
                console.log('[Main] Showing setup page instead of quitting');
                serverPort = 0;
                createSetupWindow();
                createTray();
            }
        }
    } catch (err) {
        console.error('[Main] Failed to start:', err);
        serverPort = 0;
        createSetupWindow();
        createTray();
    }
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
        createWindow(serverPort);
    }
});

app.on('before-quit', () => stopPythonServer());
app.on('will-quit', () => stopPythonServer());

process.on('SIGINT', () => { stopPythonServer(); app.quit(); });
process.on('SIGTERM', () => { stopPythonServer(); app.quit(); });
