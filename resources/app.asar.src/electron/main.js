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
let goProcess = null;
let tray = null;
let serverPort = DEFAULT_PORT;
let terminalSessions = new Map();
let startupDiagnostics = {};

function updateStartupDiagnostics(extra) {
    startupDiagnostics = Object.assign(startupDiagnostics, extra || {});
}

function getDeviceVaultDir() {
    return path.join(app.getPath('userData'), 'kaguya');
}

function getDeviceIdentityPath() {
    return path.join(getDeviceVaultDir(), 'device_identity.json');
}

function getDeviceVaultPath() {
    return path.join(getDeviceVaultDir(), 'device_vault.enc');
}

function ensureDeviceIdentity() {
    const dir = getDeviceVaultDir();
    fs.mkdirSync(dir, { recursive: true });
    const identityPath = getDeviceIdentityPath();
    if (fs.existsSync(identityPath)) {
        try {
            const existing = JSON.parse(fs.readFileSync(identityPath, 'utf8'));
            if (existing && existing.device_id) {
                return existing;
            }
        } catch (err) {
            console.warn('[DeviceVault] Invalid device identity, regenerating:', err.message);
        }
    }
    const identity = {
        device_id: crypto.randomUUID ? crypto.randomUUID() : crypto.randomBytes(16).toString('hex'),
        device_name: os.hostname() || 'Kaguya Desktop',
        platform: process.platform,
        created_at: new Date().toISOString(),
        vault_version: 1,
    };
    fs.writeFileSync(identityPath, JSON.stringify(identity, null, 2), 'utf8');
    return identity;
}

function normalizeExternalApiPayload(data) {
    data = data && typeof data === 'object' ? data : {};
    const provider = String(data.provider || data.active_provider || 'deepseek').trim().toLowerCase();
    const apiKey = String(data.api_key || data.apiKey || '').trim();
    const apiUrl = String(data.api_url || data.apiUrl || '').trim();
    const model = String(data.model || '').trim();
    return {
        provider,
        api_key: apiKey,
        api_url: apiUrl,
        model,
        enabled: Boolean((data.enabled === undefined ? true : data.enabled) && apiKey),
    };
}

function maskApiKey(apiKey) {
    if (!apiKey) return '';
    if (apiKey.length < 8) return '****';
    return apiKey.slice(0, 4) + '****' + apiKey.slice(-4);
}

function deriveFallbackVaultKey() {
    const identity = ensureDeviceIdentity();
    const username = (() => {
        try { return os.userInfo().username || ''; } catch (err) { return ''; }
    })();
    return crypto.pbkdf2Sync(
        `${identity.device_id}|${os.hostname()}|${username}|${app.getPath('userData')}`,
        'kaguya-device-vault-v1',
        100000,
        32,
        'sha256'
    );
}

function encryptFallbackVault(plainText) {
    const iv = crypto.randomBytes(12);
    const cipher = crypto.createCipheriv('aes-256-gcm', deriveFallbackVaultKey(), iv);
    const encrypted = Buffer.concat([cipher.update(plainText, 'utf8'), cipher.final()]);
    const tag = cipher.getAuthTag();
    return Buffer.concat([iv, tag, encrypted]).toString('base64');
}

function decryptFallbackVault(encoded) {
    const raw = Buffer.from(encoded, 'base64');
    const iv = raw.subarray(0, 12);
    const tag = raw.subarray(12, 28);
    const encrypted = raw.subarray(28);
    const decipher = crypto.createDecipheriv('aes-256-gcm', deriveFallbackVaultKey(), iv);
    decipher.setAuthTag(tag);
    return Buffer.concat([decipher.update(encrypted), decipher.final()]).toString('utf8');
}

function saveDeviceVault(config) {
    const normalized = normalizeExternalApiPayload(config);
    if (!normalized.api_key) {
        return { success: false, error: 'missing_api_key' };
    }
    ensureDeviceIdentity();
    const payload = {
        provider: normalized.provider,
        api_key: normalized.api_key,
        api_url: normalized.api_url,
        model: normalized.model,
        updated_at: new Date().toISOString(),
    };
    const plainText = JSON.stringify(payload);
    const encryptionAvailable = safeStorage && safeStorage.isEncryptionAvailable();
    const envelope = encryptionAvailable ? {
        version: 1,
        encryption: 'safeStorage',
        data: safeStorage.encryptString(plainText).toString('base64'),
    } : {
        version: 1,
        encryption: 'fallback',
        data: encryptFallbackVault(plainText),
    };
    fs.writeFileSync(getDeviceVaultPath(), JSON.stringify(envelope), 'utf8');
    return { success: true, encryption: envelope.encryption, config: payload };
}

function loadDeviceVault() {
    const vaultPath = getDeviceVaultPath();
    if (!fs.existsSync(vaultPath)) {
        return null;
    }
    try {
        const envelope = JSON.parse(fs.readFileSync(vaultPath, 'utf8'));
        let plainText = '';
        if (envelope.encryption === 'safeStorage') {
            if (!safeStorage || !safeStorage.isEncryptionAvailable()) {
                throw new Error('safeStorage encryption is not available');
            }
            plainText = safeStorage.decryptString(Buffer.from(envelope.data, 'base64'));
        } else if (envelope.encryption === 'fallback') {
            plainText = decryptFallbackVault(envelope.data);
        } else {
            throw new Error('unsupported vault encryption');
        }
        const parsed = JSON.parse(plainText);
        return normalizeExternalApiPayload(parsed).api_key ? Object.assign(parsed, { encryption: envelope.encryption }) : null;
    } catch (err) {
        console.error('[DeviceVault] Failed to load vault:', err.message);
        return null;
    }
}

function clearDeviceVault() {
    const vaultPath = getDeviceVaultPath();
    if (fs.existsSync(vaultPath)) {
        fs.unlinkSync(vaultPath);
    }
    return { success: true };
}

function getDeviceInfo() {
    const identity = ensureDeviceIdentity();
    const vault = loadDeviceVault();
    return {
        device_id: identity.device_id,
        device_name: identity.device_name,
        platform: identity.platform,
        encryption_available: Boolean(safeStorage && safeStorage.isEncryptionAvailable()),
        encryption: vault?.encryption || (safeStorage && safeStorage.isEncryptionAvailable() ? 'safeStorage' : 'fallback'),
        vault_exists: Boolean(vault && vault.api_key),
        active_provider: vault?.provider || '',
        masked_api_key: vault?.api_key ? maskApiKey(vault.api_key) : '',
    };
}

function htmlEscape(value) {
    return String(value == null ? '' : value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

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
    const hasPythonApp = (dir) => {
        try {
            return fs.existsSync(dir) && fs.statSync(dir).isDirectory();
        } catch (e) {
            return false;
        }
    };
    const record = (dir) => {
        updateStartupDiagnostics({
            appIsPackaged: app.isPackaged,
            resourcesPath: process.resourcesPath,
            resourcePath: dir,
            pythonAppExists: hasPythonApp(dir),
            pythonWorkerScriptExists: fs.existsSync(path.join(dir, 'start_server.py')),
        });
        return dir;
    };
    if (app.isPackaged) {
        const packagedPath = path.join(process.resourcesPath, 'python-app');
        console.log('[Startup] app.isPackaged:', app.isPackaged);
        console.log('[Startup] process.resourcesPath:', process.resourcesPath);
        console.log('[Startup] resourcePath:', packagedPath);
        console.log('[Startup] python-app exists:', hasPythonApp(packagedPath));
        return record(packagedPath);
    }
    
    const homeDir = process.env.USERPROFILE || process.env.HOME || os.homedir();
    const sourceDir = process.env.KAGUYA_SOURCE_DIR;
    
    if (sourceDir) {
        const sourcePath = path.resolve(sourceDir);
        if (hasPythonApp(sourcePath)) {
            console.log('[Main] Using KAGUYA_SOURCE_DIR:', sourcePath);
            return record(sourcePath);
        }
    }
    
    if (homeDir) {
        const desktopAppPath = path.join(homeDir, '.conda', 'kaguya-desktop', 'dist', 'KaguyaIDE-3.1.0-full', 'app');
        if (hasPythonApp(desktopAppPath)) {
            console.log('[Main] Using USERPROFILE path:', desktopAppPath);
            return record(desktopAppPath);
        }
        
        const condaPath = path.join(homeDir, '.conda');
        if (hasPythonApp(condaPath)) {
            console.log('[Main] Using conda path:', condaPath);
            return record(condaPath);
        }
    }
    
    try {
        const appPath = app.getAppPath();
        if (appPath) {
            const parentDir = path.dirname(path.dirname(appPath));
            const appDir = path.join(parentDir, 'app');
            if (hasPythonApp(appDir)) {
                console.log('[Main] Using app path:', appDir);
                return record(appDir);
            }
        }
    } catch(e) {}
    
    try {
        const electronDir = __dirname;
        const parentDir = path.dirname(electronDir);
        const appDir = path.join(parentDir, 'app');
        if (hasPythonApp(appDir)) {
            console.log('[Main] Using __dirname path:', appDir);
            return record(appDir);
        }
    } catch(e) {}
    
    console.log('[Main] WARNING: Could not find app directory, falling back to homeDir/.conda');
    const fallbackPath = path.join(homeDir || os.homedir(), '.conda');
    return record(fallbackPath);
}

function getPythonPath() {
    const homeDir = process.env.USERPROFILE || process.env.HOME || os.homedir();
    const resourcePath = getResourcePath();
    const explicitPython = process.env.KAGUYA_PYTHON;
    if (explicitPython && fs.existsSync(explicitPython)) {
        console.log('[Main] Found KAGUYA_PYTHON:', explicitPython);
        updateStartupDiagnostics({ pythonPath: explicitPython, pythonSource: 'KAGUYA_PYTHON' });
        return explicitPython;
    }

    const embeddedCandidates = [
        path.join(resourcePath, '..', 'python', 'python.exe'),
        process.resourcesPath ? path.join(process.resourcesPath, 'python', 'python.exe') : '',
    ].filter(Boolean);

    for (const p of embeddedCandidates) {
        try {
            if (fs.existsSync(p)) {
                console.log('[Main] Found embedded Python:', p);
                updateStartupDiagnostics({ pythonPath: p, pythonSource: 'embedded' });
                return p;
            }
        } catch(e) {}
    }

    console.log('[Main] Embedded Python not found; checking installed Python fallbacks');

    const standardPaths = [
        path.join(process.env.LOCALAPPDATA || '', 'Programs', 'Python', 'Python314', 'python.exe'),
        path.join(process.env.LOCALAPPDATA || '', 'Programs', 'Python', 'Python313', 'python.exe'),
        path.join(process.env.LOCALAPPDATA || '', 'Programs', 'Python', 'Python312', 'python.exe'),
        path.join(process.env.LOCALAPPDATA || '', 'Programs', 'Python', 'Python311', 'python.exe'),
        path.join(process.env.LOCALAPPDATA || '', 'Programs', 'Python', 'Python310', 'python.exe'),
        path.join(process.env.LOCALAPPDATA || '', 'Programs', 'Python', 'Python39', 'python.exe'),
    ];

    for (const p of standardPaths) {
        try {
            if (fs.existsSync(p)) {
                console.log('[Main] Found standard Python:', p);
                updateStartupDiagnostics({ pythonPath: p, pythonSource: 'standard' });
                return p;
            }
        } catch(e) {}
    }

    const fallbackCondaPaths = [
        path.join(homeDir, '.conda', 'kaguya_env', 'Scripts', 'python.exe'),
        path.join(homeDir, '.conda', 'envs', 'DL', 'python.exe'),
        path.join(homeDir, 'anaconda3', 'python.exe'),
        path.join(homeDir, 'miniconda3', 'python.exe'),
        path.join(homeDir, 'anaconda3', 'envs', 'DL', 'python.exe'),
        path.join(homeDir, 'miniconda3', 'envs', 'DL', 'python.exe'),
        'D:\\Anoconda\\envs\\DL\\python.exe',
        'D:\\Anaconda3\\envs\\DL\\python.exe',
        'D:\\Miniconda3\\envs\\DL\\python.exe',
        'C:\\Anaconda3\\envs\\DL\\python.exe',
        'C:\\Miniconda3\\envs\\DL\\python.exe',
    ];

    for (const p of fallbackCondaPaths) {
        try {
            if (fs.existsSync(p)) {
                console.log('[Main] Found fallback Python:', p);
                updateStartupDiagnostics({ pythonPath: p, pythonSource: 'fallback' });
                return p;
            }
        } catch(e) {}
    }
    
    console.log('[Main] Trying system Python from PATH...');
    updateStartupDiagnostics({ pythonPath: 'python', pythonSource: 'PATH' });
    return 'python';
}

function getShellPath() {
    if (process.platform === 'win32') {
        return process.env.COMSPEC || 'cmd.exe';
    }
    return process.env.SHELL || '/bin/bash';
}

function isAllowedExternalUrl(rawUrl) {
    try {
        const parsed = new URL(rawUrl);
        return ['https:', 'http:', 'mailto:'].includes(parsed.protocol);
    } catch (err) {
        return false;
    }
}

function isLocalAppUrl(rawUrl) {
    try {
        const parsed = new URL(rawUrl);
        return parsed.protocol === 'http:' && ['127.0.0.1', 'localhost'].includes(parsed.hostname);
    } catch (err) {
        return false;
    }
}

function getResourcesRoot() {
    if (app.isPackaged) {
        return process.resourcesPath;
    }
    return path.resolve(__dirname, '..', '..');
}

function getGoBackendDir() {
    return path.join(getResourcesRoot(), 'go-backend');
}

function findGoBackendExecutable() {
    if (process.env.KAGUYA_GO_BACKEND && fs.existsSync(process.env.KAGUYA_GO_BACKEND)) {
        return { command: process.env.KAGUYA_GO_BACKEND, args: [], cwd: path.dirname(process.env.KAGUYA_GO_BACKEND), source: 'KAGUYA_GO_BACKEND' };
    }
    const dir = getGoBackendDir();
    const exeName = process.platform === 'win32' ? 'kaguya-go-backend.exe' : 'kaguya-go-backend';
    const binary = path.join(dir, exeName);
    if (fs.existsSync(binary)) {
        return { command: binary, args: [], cwd: dir, source: 'bundled-binary' };
    }
    if (fs.existsSync(path.join(dir, 'go.mod')) && commandExists('go')) {
        return { command: 'go', args: ['run', '.'], cwd: dir, source: 'go-run' };
    }
    return null;
}

function commandExists(command) {
    try {
        const { execSync } = require('child_process');
        const lookup = process.platform === 'win32' ? `where ${command}` : `command -v ${command}`;
        execSync(lookup, { stdio: 'ignore', windowsHide: true });
        return true;
    } catch (err) {
        return false;
    }
}

function waitForBackend(port, route = '/') {
    return new Promise((resolve, reject) => {
        const req = require('http').get(`http://127.0.0.1:${port}${route}`, (res) => {
            res.resume();
            if (res.statusCode && res.statusCode < 500) resolve();
            else reject(new Error(`status ${res.statusCode}`));
        });
        req.on('error', reject);
        req.setTimeout(1000, () => { req.destroy(); reject(new Error('timeout')); });
    });
}

async function startGoServer(port) {
    const backend = findGoBackendExecutable();
    const resourcePath = getResourcePath();
    const workerScript = path.join(resourcePath, 'start_server.py');
    const runtimeDir = path.join(app.getPath('userData'), 'kaguya', 'go-backend');
    updateStartupDiagnostics({
        backendModeAttempted: 'go',
        goBackendDir: getGoBackendDir(),
        goBackendFound: !!backend,
        goRuntimeDir: runtimeDir,
        pythonWorkerScript: workerScript,
        pythonWorkerScriptExists: fs.existsSync(workerScript),
    });
    if (!backend) {
        throw new Error(`Go backend executable not found. Expected ${path.join(getGoBackendDir(), process.platform === 'win32' ? 'kaguya-go-backend.exe' : 'kaguya-go-backend')} or a Go toolchain for go run.`);
    }

    const args = backend.args.concat([
        '--host', '127.0.0.1',
        '--port', String(port),
        '--runtime-dir', runtimeDir,
        '--app-dir', resourcePath,
        '--static-dir', path.join(getGoBackendDir(), 'static'),
    ]);
    if (process.env.KAGUYA_ENABLE_PYTHON_WORKER === '1') {
        const pythonPath = getPythonPath();
        if (!fs.existsSync(workerScript)) {
            throw new Error(`Python worker requested but start_server.py was not found at ${workerScript}`);
        }
        args.push('--python-script', workerScript, '--python', pythonPath);
    }
    console.log('[Main] Starting Go backend:', backend.command, args.join(' '));
    updateStartupDiagnostics({
        goCommand: backend.command,
        goArgs: args,
        goSource: backend.source,
        backendPort: port,
    });

    goProcess = spawn(backend.command, args, {
        cwd: backend.cwd,
        env: Object.assign({}, process.env, {
            KAGUYA_DESKTOP_MODE: '1',
            KAGUYA_ELECTRON: '1',
            KAGUYA_DISABLE_NGROK: '1',
            KAGUYA_RUNTIME_DIR: runtimeDir,
        }),
        stdio: ['pipe', 'pipe', 'pipe'],
        windowsHide: true,
    });

    let goStdout = '';
    let goStderr = '';
    goProcess.stdout.on('data', (data) => {
        const output = data.toString();
        goStdout += output;
        updateStartupDiagnostics({ lastGoStdout: goStdout.slice(-2000) });
        console.log('[Go]', output.trim());
    });
    goProcess.stderr.on('data', (data) => {
        const output = data.toString();
        goStderr += output;
        updateStartupDiagnostics({ lastGoStderr: goStderr.slice(-2000) });
        console.error('[Go Err]', output.trim());
    });
    goProcess.on('close', (code) => {
        console.log(`[Go] Process exited with code ${code}`);
        updateStartupDiagnostics({ lastGoExitCode: code, lastGoStderr: goStderr.slice(-2000) });
        goProcess = null;
    });

    for (let i = 0; i < 150; i++) {
        await new Promise(r => setTimeout(r, 300));
        try {
            await waitForBackend(port, '/health');
            console.log(`[OK] Go backend ready at http://127.0.0.1:${port}/`);
            updateStartupDiagnostics({ backendMode: 'go' });
            return port;
        } catch (err) {
            if (i % 10 === 0) {
                console.log(`[Main] Waiting for Go backend... (${i}/150)`);
            }
        }
    }
    throw new Error(`Go backend did not become healthy. Last stderr: ${goStderr.slice(-2000)}`);
}

async function startBackendServer(port) {
    try {
        await startGoServer(port);
        return { port, mode: 'go' };
    } catch (goErr) {
        updateStartupDiagnostics({ goBackendError: goErr.message, backendFallback: 'mini' });
        throw new Error(`Go backend unavailable. ${goErr.message}`);
    }
}

async function startPythonServer(port) {
    const tmpDir = os.tmpdir();
    const launcherScript = path.join(tmpDir, 'kaguya_launcher.py');
    
    const resourcePath = getResourcePath();
    const startServerPath = path.join(resourcePath, 'start_server.py');
    const pythonPath = getPythonPath();
    updateStartupDiagnostics({
        appIsPackaged: app.isPackaged,
        resourcesPath: process.resourcesPath,
        resourcePath,
        pythonAppPath: resourcePath,
        pythonPath,
        launcherScript,
        flaskPort: port,
        attemptedScript: startServerPath,
        pythonWorkerScript: startServerPath,
        pythonWorkerScriptExists: fs.existsSync(startServerPath),
        startServerExists: fs.existsSync(startServerPath),
    });
    console.log('[Startup] app.isPackaged:', app.isPackaged);
    console.log('[Startup] process.resourcesPath:', process.resourcesPath);
    console.log('[Startup] final resourcePath:', resourcePath);
    console.log('[Startup] Python path:', pythonPath);
    console.log('[Startup] launcherScript:', launcherScript);
    console.log('[Startup] Flask port:', port);
    console.log('[Startup] start_server.py exists:', fs.existsSync(startServerPath));

    if (!fs.existsSync(startServerPath)) {
        throw new Error(`start_server.py not found at ${startServerPath}. The packaged resources/python-app directory is missing or corrupt.`);
    }
    
    const launcherContent = `
import os, sys

app_dir = r'${resourcePath.replace(/\\/g, '\\\\')}'
script = os.path.join(app_dir, 'start_server.py')
if not os.path.exists(script):
    print('[LAUNCHER ERROR] start_server.py not found in:', app_dir, file=sys.stderr)
    sys.exit(1)

os.chdir(app_dir)
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)
os.environ['KAGUYA_DESKTOP_MODE'] = '1'
os.environ['KAGUYA_PORT'] = '${port}'
os.environ['KAGUYA_ELECTRON'] = '1'
os.environ['KAGUYA_DISABLE_NGROK'] = '1'
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONUTF8'] = '1'

print('[LAUNCHER] App dir:', app_dir)
print('[LAUNCHER] Starting Python worker on port ${port}...')

sys.argv = ['start_server.py', '--port', '${port}', '--localhost-only', '--backend', 'bootstrap']
import runpy
runpy.run_path(script, run_name='__main__')
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
                updateStartupDiagnostics({ pythonPath: verifiedPythonPath, pythonSource: 'PATH' });
            }
        } catch (e) {
            console.error('[Main] Python not found in PATH');
            throw new Error('Python not found. Please install Python 3.9+ and ensure it is in PATH.');
        }
    }

    const env = Object.assign({}, process.env, {
        'KAGUYA_DESKTOP_MODE': '1',
        'KAGUYA_PORT': String(port),
        'KAGUYA_ELECTRON': '1',
        'KAGUYA_DISABLE_NGROK': '1',
        'KAGUYA_RUNTIME_DIR': path.join(app.getPath('userData'), 'kaguya', 'python-app'),
        'PYTHONIOENCODING': 'utf-8',
        'PYTHONUTF8': '1',
    });

    const args = [launcherScript];

    console.log('[Main] Starting Python server via launcher...');
    console.log('[Main] Command:', verifiedPythonPath, args.join(' '));

    pythonProcess = spawn(verifiedPythonPath, args, {
        cwd: tmpDir,
        env: env,
        stdio: ['pipe', 'pipe', 'pipe'],
        windowsHide: true,
    });

    let serverStdout = '';
    let serverStderr = '';

    pythonProcess.stdout.on('data', (data) => {
        const output = data.toString();
        serverStdout += output;
        updateStartupDiagnostics({ lastPythonStdout: serverStdout.slice(-2000) });
        console.log('[Python]', output.trim());
    });

    pythonProcess.stderr.on('data', (data) => {
        const output = data.toString();
        serverStderr += output;
        updateStartupDiagnostics({ lastPythonStderr: serverStderr.slice(-2000) });
        console.error('[Python Err]', output.trim());
    });

    pythonProcess.on('error', (err) => {
        console.error('[Main] Python process error:', err.message);
        updateStartupDiagnostics({ lastError: err.message });
        dialog.showErrorBox('Python Error',
            `Failed to start Python process:\n${err.message}\n\n` +
            `Python path: ${verifiedPythonPath}\n` +
            `Launcher: ${launcherScript}`);
    });

    pythonProcess.on('close', (code) => {
        console.log(`[Python] Process exited with code ${code}`);
        if (code !== 0 && code !== null) {
            console.error('[Main] Python exited unexpectedly. Last stderr:', serverStderr.slice(-2000));
            updateStartupDiagnostics({ lastError: `Python exited with code ${code}`, lastPythonStderr: serverStderr.slice(-2000) });
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
    const timeoutError = new Error(
        'Python backend did not become healthy. ' +
        `Port: ${port}. Resource path: ${resourcePath}. Python: ${verifiedPythonPath}. ` +
        `Last stderr: ${serverStderr.slice(-2000)}`
    );
    updateStartupDiagnostics({
        lastError: timeoutError.message,
        lastPythonStderr: serverStderr.slice(-2000),
        lastPythonStdout: serverStdout.slice(-2000),
    });
    throw timeoutError;
}

let miniServer = null;

function startMiniServer(port) {
    const http = require('http');
    const https = require('https');
    const url = require('url');

    const providerUrls = {
        deepseek: { url: 'https://api.deepseek.com', model: 'deepseek-chat', type: 'openai' },
        openai: { url: 'https://api.openai.com/v1', model: 'gpt-4o', type: 'openai' },
        claude: { url: 'https://api.anthropic.com', model: 'claude-3-7-sonnet-20250219', type: 'claude' },
        qwen: { url: 'https://dashscope.aliyuncs.com/compatible-mode/v1', model: 'qwen-plus', type: 'openai' },
        kimi: { url: 'https://api.moonshot.ai/v1', model: 'kimi-k2.6', type: 'openai' },
        moonshot: { url: 'https://api.moonshot.ai/v1', model: 'moonshot-v1-8k', type: 'openai' },
        minimax: { url: 'https://api.minimaxi.com/v1', model: 'MiniMax-M2.7', type: 'openai' },
        zhipu: { url: 'https://open.bigmodel.cn/api/paas/v4', model: 'glm-4-flash', type: 'openai' },
        groq: { url: 'https://api.groq.com/openai/v1', model: 'llama-3.3-70b-versatile', type: 'openai' },
        custom: { url: '', model: '', type: 'openai' },
    };

    let savedApiConfig = loadDeviceVault();

    function sendJson(res, status, payload) {
        res.writeHead(status, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(payload));
    }

    function readJsonBody(req, callback) {
        let body = '';
        req.on('data', c => body += c);
        req.on('end', () => {
            try {
                callback(null, body ? JSON.parse(body) : {});
            } catch (err) {
                callback(err);
            }
        });
    }

    function currentVaultConfig() {
        const vault = loadDeviceVault();
        savedApiConfig = vault || savedApiConfig;
        return savedApiConfig;
    }

    function miniDiagnostics() {
        return Object.assign({
            mode: 'mini',
            backend_available: false,
            appIsPackaged: app.isPackaged,
            resourcesPath: process.resourcesPath,
            resourcePath: startupDiagnostics.resourcePath || '',
            pythonAppPath: startupDiagnostics.pythonAppPath || '',
            pythonPath: startupDiagnostics.pythonPath || '',
            attemptedScript: startupDiagnostics.attemptedScript || startupDiagnostics.pythonWorkerScript || '',
            port,
            cwd: process.cwd(),
            pythonWorkerScriptExists: startupDiagnostics.pythonWorkerScriptExists || false,
            startServerExists: startupDiagnostics.startServerExists || false,
            stdoutTail: startupDiagnostics.lastPythonStdout || '',
            stderrTail: startupDiagnostics.lastPythonStderr || '',
        }, startupDiagnostics);
    }

    function chatEndpointFor(provider, apiUrl) {
        const pInfo = providerUrls[provider] || providerUrls.custom;
        const base = String(apiUrl || pInfo.url || '').replace(/\/+$/, '');
        if (!base) throw new Error('api_url required');
        if (pInfo.type === 'claude') {
            return base.endsWith('/v1/messages') ? base : base + '/v1/messages';
        }
        if (base.endsWith('/chat/completions')) return base;
        if (base.endsWith('/v1')) return base + '/chat/completions';
        if (base.includes('/v1/')) return base.split('/v1/')[0] + '/v1/chat/completions';
        return base + '/chat/completions';
    }

    function isKimiK2(provider, model) {
        return ['kimi', 'moonshot'].includes(String(provider || '').toLowerCase()) &&
            String(model || '').toLowerCase().startsWith('kimi-k2');
    }

    function buildOpenAiMiniPayload(provider, model, messages, chatData, stream) {
        const payload = { model, messages, stream };
        if (isKimiK2(provider, model)) {
            payload.thinking = { type: 'disabled' };
            payload.max_completion_tokens = chatData.max_tokens || 4096;
            return payload;
        }
        payload.temperature = chatData.temperature || 0.3;
        payload.max_tokens = chatData.max_tokens || 4096;
        return payload;
    }

    const server = http.createServer((req, res) => {
        const parsedUrl = url.parse(req.url, true);
        const pathname = parsedUrl.pathname;

        res.setHeader('Access-Control-Allow-Origin', '*');
        res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
        res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

        if (req.method === 'OPTIONS') { res.writeHead(200); res.end(); return; }

        if ((pathname === '/docs' || pathname === '/readme') && req.method === 'GET') {
            res.writeHead(200, { 'Content-Type': 'text/plain; charset=utf-8' });
            res.end('Kaguya IDE mini fallback\nmode: mini\nbackend_available: false\n\nThe Python Flask backend is unavailable. Use /api/device/bind to save an external provider or inspect /api/config for diagnostics.\n');
            return;
        }

        if (pathname === '/api/device/info' && req.method === 'GET') {
            sendJson(res, 200, { success: true, mode: 'mini', backend_available: false, device: getDeviceInfo() });
            return;
        }

        if (pathname === '/api/device/bind' && req.method === 'POST') {
            readJsonBody(req, (err, data) => {
                if (err) return sendJson(res, 400, { success: false, mode: 'mini', error: err.message });
                const cfg = normalizeExternalApiPayload(data);
                if (!cfg.api_key) return sendJson(res, 400, { success: false, mode: 'mini', error: 'missing_api_key' });
                const saved = saveDeviceVault(cfg);
                if (!saved.success) return sendJson(res, 400, Object.assign({ mode: 'mini' }, saved));
                savedApiConfig = saved.config;
                sendJson(res, 200, {
                    success: true,
                    mode: 'mini',
                    provider: saved.config.provider,
                    api_url: saved.config.api_url,
                    model: saved.config.model,
                    masked_api_key: maskApiKey(saved.config.api_key),
                    encryption: saved.encryption,
                });
            });
            return;
        }

        if (pathname === '/api/device/unbind' && req.method === 'POST') {
            clearDeviceVault();
            savedApiConfig = null;
            sendJson(res, 200, { success: true, mode: 'mini' });
            return;
        }

        if ((pathname === '/api/account/saved-config' || pathname === '/api/account/auto-fill') && req.method === 'GET') {
            const cfg = currentVaultConfig();
            sendJson(res, 200, {
                success: true,
                mode: 'mini',
                has_config: Boolean(cfg && cfg.api_key),
                provider: cfg?.provider || '',
                api_url: cfg?.api_url || '',
                model: cfg?.model || '',
                masked_api_key: cfg?.api_key ? maskApiKey(cfg.api_key) : '',
            });
            return;
        }

        if (pathname === '/api/config' && req.method === 'GET') {
            const cfg = currentVaultConfig();
            sendJson(res, 200, {
                success: true,
                mode: 'mini',
                backend_available: false,
                external_provider_configured: Boolean(cfg && cfg.api_key),
                provider: cfg?.provider || null,
                model: cfg?.model || null,
                masked_api_key: cfg?.api_key ? maskApiKey(cfg.api_key) : '',
                diagnostics: miniDiagnostics(),
            });
            return;
        }

        if (pathname === '/api/config' && req.method === 'POST') {
            readJsonBody(req, (err, data) => {
                if (err) return sendJson(res, 400, { success: false, mode: 'mini', error: err.message });
                const cfg = normalizeExternalApiPayload(data.external_api || data);
                if (!cfg.api_key) return sendJson(res, 400, { success: false, mode: 'mini', error: 'missing_api_key' });
                const saved = saveDeviceVault(cfg);
                if (!saved.success) return sendJson(res, 400, Object.assign({ mode: 'mini' }, saved));
                savedApiConfig = saved.config;
                sendJson(res, 200, { success: true, mode: 'mini', provider: saved.config.provider, api_url: saved.config.api_url, model: saved.config.model, masked_api_key: maskApiKey(saved.config.api_key) });
            });
            return;
        }

        if (pathname === '/api/model-status' && req.method === 'GET') {
            const cfg = currentVaultConfig();
            sendJson(res, 200, {
                success: true,
                mode: 'mini',
                backend_available: false,
                external_provider_configured: Boolean(cfg && cfg.api_key),
                model: cfg?.model || '',
                provider: cfg?.provider || '',
                available: false,
                reason: 'python_backend_unavailable',
            });
            return;
        }

        if (pathname === '/api/model-status' && req.method === 'POST') {
            readJsonBody(req, (err, data) => {
                if (err) return sendJson(res, 400, { success: false, mode: 'mini', available: false, error: err.message });
                const cfg = normalizeExternalApiPayload(data.external_api || data);
                if (!cfg.api_key) {
                    return sendJson(res, 200, { success: true, mode: 'mini', backend_available: false, external_provider_configured: false, available: false, reason: 'missing_api_key' });
                }
                const pInfo = providerUrls[cfg.provider] || providerUrls.custom;
                let testUrl = '';
                try {
                    testUrl = pInfo.type === 'claude'
                        ? chatEndpointFor(cfg.provider, cfg.api_url || pInfo.url)
                        : chatEndpointFor(cfg.provider, cfg.api_url || pInfo.url).replace(/\/chat\/completions$/, '/models');
                    const target = new URL(testUrl);
                    const headers = pInfo.type === 'claude'
                        ? { 'x-api-key': cfg.api_key, 'anthropic-version': '2023-06-01' }
                        : { 'Authorization': 'Bearer ' + cfg.api_key };
                    const testReq = https.request({ hostname: target.hostname, path: target.pathname + target.search, method: 'GET', headers, timeout: 10000 }, (testRes) => {
                        testRes.resume();
                        const ok = testRes.statusCode >= 200 && testRes.statusCode < 300;
                        if (ok) {
                            const saved = saveDeviceVault(cfg);
                            if (saved.success) savedApiConfig = saved.config;
                        }
                        sendJson(res, 200, {
                            success: true,
                            mode: 'mini',
                            backend_available: false,
                            external_provider_configured: true,
                            provider: cfg.provider,
                            model: cfg.model || pInfo.model || '',
                            available: ok,
                            reason: ok ? null : 'provider_verification_failed',
                            message: ok ? 'External provider verified.' : 'API returned status ' + testRes.statusCode,
                        });
                    });
                    testReq.on('error', (e) => sendJson(res, 200, { success: true, mode: 'mini', backend_available: false, external_provider_configured: true, provider: cfg.provider, model: cfg.model || pInfo.model || '', available: false, reason: 'provider_verification_failed', message: e.message }));
                    testReq.end();
                } catch (e) {
                    sendJson(res, 200, { success: true, mode: 'mini', backend_available: false, external_provider_configured: true, provider: cfg.provider, model: cfg.model || '', available: false, reason: 'provider_verification_failed', message: e.message });
                }
            });
            return;
        }

        if ((pathname === '/api/chat' || pathname === '/chat/completions') && req.method === 'POST') {
            readJsonBody(req, (err, chatData) => {
                if (err) return sendJson(res, 400, { success: false, mode: 'mini', error: err.message });
                const cfg = currentVaultConfig();
                if (!cfg || !cfg.api_key) {
                    return sendJson(res, 503, {
                        success: false,
                        mode: 'mini',
                        error: 'backend_unavailable',
                        message: 'Python backend is unavailable and no external provider is configured.',
                    });
                }
                try {
                    const pInfo = providerUrls[cfg.provider] || providerUrls.custom;
                    const targetUrl = chatEndpointFor(cfg.provider, cfg.api_url || pInfo.url);
                    const target = new URL(targetUrl);
                    const messages = Array.isArray(chatData.messages) ? chatData.messages : [{ role: 'user', content: String(chatData.message || '') }];
                    const model = chatData.model || cfg.model || pInfo.model;
                    const msgBody = pInfo.type === 'claude' ? JSON.stringify({
                        model: cfg.model || pInfo.model,
                        messages,
                        stream: chatData.stream !== false,
                        max_tokens: chatData.max_tokens || 4096,
                    }) : JSON.stringify(buildOpenAiMiniPayload(cfg.provider, model, messages, chatData, chatData.stream !== false && pathname === '/api/chat'));
                    const headers = pInfo.type === 'claude' ? {
                        'Content-Type': 'application/json',
                        'x-api-key': cfg.api_key,
                        'anthropic-version': '2023-06-01',
                    } : {
                        'Content-Type': 'application/json',
                        'Authorization': 'Bearer ' + cfg.api_key,
                    };
                    const proxyReq = https.request({ hostname: target.hostname, path: target.pathname + target.search, method: 'POST', headers }, (proxyRes) => {
                        res.writeHead(proxyRes.statusCode || 502, { 'Content-Type': proxyRes.headers['content-type'] || 'application/json' });
                        proxyRes.pipe(res);
                    });
                    proxyReq.on('error', (e) => {
                        sendJson(res, 502, { success: false, mode: 'mini', error: 'provider_proxy_failed', message: e.message });
                    });
                    proxyReq.write(msgBody);
                    proxyReq.end();
                } catch (e) {
                    sendJson(res, 502, { success: false, mode: 'mini', error: 'provider_proxy_failed', message: e.message });
                }
            });
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
                        savedApiConfig = extApi;
                        const pInfo = providerUrls[extApi.provider] || {};
                        const testUrl = (extApi.apiUrl || pInfo.url) + (pInfo.type === 'openai' ? '/models' : '/v1/models');
                        const testOpts = {
                            hostname: new URL(testUrl).hostname,
                            path: new URL(testUrl).pathname,
                            method: 'GET',
                            headers: pInfo.type === 'openai' ? { 'Authorization': 'Bearer ' + extApi.apiKey } : { 'x-api-key': extApi.apiKey, 'anthropic-version': '2023-06-01' },
                            timeout: 10000,
                        };
                        const testReq = https.request(testOpts, (testRes) => {
                            if (testRes.statusCode >= 200 && testRes.statusCode < 500) {
                                res.writeHead(200, { 'Content-Type': 'application/json' });
                                res.end(JSON.stringify({ available: true, provider: extApi.provider, model: extApi.model || pInfo.model }));
                            } else {
                                res.writeHead(200, { 'Content-Type': 'application/json' });
                                res.end(JSON.stringify({ available: false, message: 'API returned status ' + testRes.statusCode }));
                            }
                        });
                        testReq.on('error', (e) => {
                            res.writeHead(200, { 'Content-Type': 'application/json' });
                            res.end(JSON.stringify({ available: false, message: e.message }));
                        });
                        testReq.end();
                    } else {
                        res.writeHead(200, { 'Content-Type': 'application/json' });
                        res.end(JSON.stringify({ available: false, message: 'No API key provided' }));
                    }
                } catch (e) {
                    res.writeHead(400, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: e.message }));
                }
            });
            return;
        }

        if (pathname === '/api/chat' && req.method === 'POST') {
            let body = '';
            req.on('data', c => body += c);
            req.on('end', () => {
                if (!savedApiConfig) {
                    res.writeHead(503, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: 'No API configured' }));
                    return;
                }
                try {
                    const chatData = JSON.parse(body);
                    const pInfo = providerUrls[savedApiConfig.provider] || {};
                    const apiBase = savedApiConfig.apiUrl || pInfo.url;
                    const targetUrl = apiBase + (pInfo.type === 'openai' ? '/chat/completions' : '/v1/messages');
                    const targetParsed = new URL(targetUrl);

                    const legacyModel = savedApiConfig.model || pInfo.model;
                    const legacyMessages = chatData.messages || [];
                    const msgBody = pInfo.type === 'openai' ? JSON.stringify(buildOpenAiMiniPayload(savedApiConfig.provider, legacyModel, legacyMessages, chatData, chatData.stream !== false)) : JSON.stringify({
                        model: savedApiConfig.model || pInfo.model,
                        messages: legacyMessages,
                        stream: chatData.stream !== false,
                        max_tokens: chatData.max_tokens || 4096,
                    });

                    const headers = pInfo.type === 'openai' ? {
                        'Content-Type': 'application/json',
                        'Authorization': 'Bearer ' + savedApiConfig.apiKey,
                    } : {
                        'Content-Type': 'application/json',
                        'x-api-key': savedApiConfig.apiKey,
                        'anthropic-version': '2023-06-01',
                    };

                    if (chatData.stream !== false) {
                        res.writeHead(200, { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache', 'Connection': 'keep-alive' });
                    } else {
                        res.writeHead(200, { 'Content-Type': 'application/json' });
                    }

                    const proxyReq = https.request({
                        hostname: targetParsed.hostname,
                        path: targetParsed.pathname,
                        method: 'POST',
                        headers: headers,
                    }, (proxyRes) => {
                        proxyRes.pipe(res);
                    });
                    proxyReq.on('error', (e) => {
                        res.end(JSON.stringify({ error: e.message }));
                    });
                    proxyReq.write(msgBody);
                    proxyReq.end();
                } catch (e) {
                    res.writeHead(500, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: e.message }));
                }
            });
            return;
        }

        if (pathname === '/api/config' && req.method === 'GET') {
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ mode: 'mini', hasApi: !!savedApiConfig, provider: savedApiConfig?.provider || null }));
            return;
        }

        if (pathname === '/api/config' && req.method === 'POST') {
            let body = '';
            req.on('data', c => body += c);
            req.on('end', () => {
                try {
                    savedApiConfig = JSON.parse(body);
                    res.writeHead(200, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ ok: true }));
                } catch (e) {
                    res.writeHead(400, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: e.message }));
                }
            });
            return;
        }

        if (pathname === '/header-img' || pathname === '/hero-img' || pathname === '/welcome-img') {
            const imgName = pathname.replace('/', '') + '.png';
            const mapping = { '/header-img': 'kaguya-header.png', '/hero-img': 'kaguya-hero.png', '/welcome-img': 'kaguya-welcome.png' };
            const imgPath = path.join(getResourcePath(), 'assets', mapping[pathname]);
            if (fs.existsSync(imgPath)) {
                const imgData = fs.readFileSync(imgPath);
                res.writeHead(200, { 'Content-Type': 'image/png' });
                res.end(imgData);
            } else {
                res.writeHead(404);
                res.end();
            }
            return;
        }

        res.writeHead(404, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({
            success: false,
            mode: 'mini',
            backend_available: false,
            error: 'Not found',
            hint: 'Mini server mode: Python backend is not available. See setup diagnostics for resourcePath, pythonPath and stderr.',
            diagnostics: miniDiagnostics(),
        }));
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
    const diagnostics = Object.assign({
        appIsPackaged: app.isPackaged,
        resourcesPath: process.resourcesPath,
        resourcePath: startupDiagnostics.resourcePath || '',
        pythonPath: startupDiagnostics.pythonPath || '',
        launcherScript: startupDiagnostics.launcherScript || '',
        flaskPort: setupPort,
        pythonWorkerScriptExists: startupDiagnostics.pythonWorkerScriptExists || false,
        lastError: startupDiagnostics.lastError || '',
        lastPythonStderr: startupDiagnostics.lastPythonStderr || '',
    }, startupDiagnostics);
    const diagnosticsText = htmlEscape(JSON.stringify(diagnostics, null, 2));
    if (!miniServer) {
        startMiniServer(setupPort);
    }

    const iconPath = path.join(__dirname, '..', 'assets', process.platform === 'win32' ? 'kaguya.ico' : 'kaguya.png');
    const windowOpts = {
        width: 800,
        height: 600,
        minWidth: 640,
        minHeight: 480,
        title: APP_NAME + ' - Setup',
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, 'preload.js'),
            sandbox: true,
            webSecurity: true,
        },
        show: false,
        backgroundColor: '#0a0a0f',
    };
    if (fs.existsSync(iconPath)) {
        windowOpts.icon = iconPath;
    }
    mainWindow = new BrowserWindow(windowOpts);

    const setupHtml = `<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>${APP_NAME} Setup</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0a0a0f;color:#e0e0e0;font-family:'Segoe UI',system-ui,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;padding:40px}
.container{max-width:600px;text-align:center}
h1{font-size:28px;margin-bottom:8px;background:linear-gradient(135deg,#7c5cfc,#00d4ff);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.subtitle{color:#888;margin-bottom:32px;font-size:14px}
.card{background:#16161e;border:1px solid #2a2a3a;border-radius:12px;padding:24px;margin-bottom:20px;text-align:left}
.card h3{color:#7c5cfc;margin-bottom:12px;font-size:16px}
.card p{color:#aaa;font-size:13px;line-height:1.6;margin-bottom:12px}
.card ol{color:#aaa;font-size:13px;line-height:1.8;padding-left:20px}
.card code{background:#1a1a2e;padding:2px 6px;border-radius:4px;color:#00d4ff;font-size:12px}
.btn{display:inline-block;padding:12px 32px;border-radius:8px;font-size:14px;font-weight:600;cursor:pointer;border:none;margin:8px}
.btn-primary{background:linear-gradient(135deg,#7c5cfc,#5c3cfc);color:white}
.btn-secondary{background:#1a1a2e;border:1px solid #3a3a4a;color:#ccc}
.btn:hover{opacity:0.9;transform:translateY(-1px)}
.api-section{margin-top:16px}
.api-section label{display:block;color:#aaa;font-size:12px;margin-bottom:6px;margin-top:12px}
.api-section input,.api-section select{width:100%;padding:10px 12px;background:#0a0a0f;border:1px solid #2a2a3a;border-radius:6px;color:#e0e0e0;font-size:13px}
.api-section input:focus,.api-section select:focus{border-color:#7c5cfc;outline:none}
.diag{white-space:pre-wrap;background:#080812;border:1px solid #242438;border-radius:8px;padding:12px;color:#b8c0ff;font-size:11px;max-height:160px;overflow:auto;text-align:left}
.status{margin-top:16px;padding:12px;border-radius:8px;font-size:13px;display:none}
.status.ok{display:block;background:#0a2a0a;border:1px solid #1a4a1a;color:#4caf50}
.status.err{display:block;background:#2a0a0a;border:1px solid #4a1a1a;color:#ef5350}
</style></head><body>
<div class="container">
<h1>Kaguya IDE</h1>
<p class="subtitle">AI-Powered Development Environment v${APP_VERSION}</p>
<div class="card">
<h3>Quick Start with Cloud API</h3>
<p>No local model installation needed. Configure an API provider to start using Kaguya IDE immediately.</p>
<div class="api-section">
<label>API Provider</label>
<select id="provider">
<option value="deepseek">DeepSeek (Recommended)</option>
<option value="openai">OpenAI</option>
<option value="claude">Claude (Anthropic)</option>
<option value="qwen">Qwen (Alibaba)</option>
<option value="kimi">Kimi K2.6</option>
<option value="moonshot">Moonshot (Kimi)</option>
<option value="zhipu">Zhipu (GLM)</option>
<option value="groq">Groq</option>
</select>
<label>API Key</label>
<input type="password" id="apiKey" placeholder="sk-..." />
<label>API URL (optional)</label>
<input type="text" id="apiUrl" placeholder="Auto-detected based on provider" />
</div>
<div id="status" class="status"></div>
<button class="btn btn-primary" onclick="testAndStart()">Test & Start</button>
</div>
<div class="card">
<h3>Or: Use Local Model</h3>
<p>To use a local AI model instead:</p>
<ol>
<li>Install <a href="https://ollama.com" style="color:#7c5cfc">Ollama</a></li>
<li>Run: <code>ollama pull llama3.2:3b</code></li>
<li>Install <a href="https://www.python.org/downloads/" style="color:#7c5cfc">Python 3.9+</a> with Flask</li>
<li>Restart Kaguya IDE</li>
</ol>
</div>
<div class="card">
<h3>Backend Startup Diagnostics</h3>
<p>The Python backend did not become available. Install Python 3.9+ with Flask, or provide a packaged Python runtime under <code>resources/python/python.exe</code>.</p>
<pre class="diag">${diagnosticsText}</pre>
</div>
</div>
<script>
const providerUrls = {
deepseek:'https://api.deepseek.com',openai:'https://api.openai.com/v1',
claude:'https://api.anthropic.com',qwen:'https://dashscope.aliyuncs.com/compatible-mode/v1',
kimi:'https://api.moonshot.ai/v1',moonshot:'https://api.moonshot.ai/v1',zhipu:'https://open.bigmodel.cn/api/paas/v4',
groq:'https://api.groq.com/openai/v1'
};
const providerModels = {
deepseek:'deepseek-chat',openai:'gpt-4o',claude:'claude-3-7-sonnet-20250219',
qwen:'qwen-plus',kimi:'kimi-k2.6',moonshot:'moonshot-v1-8k',zhipu:'glm-4-flash',groq:'llama-3.3-70b-versatile'
};
document.getElementById('provider').onchange = function(){
document.getElementById('apiUrl').placeholder = providerUrls[this.value] || '';
};
async function testAndStart(){
const provider = document.getElementById('provider').value;
const apiKey = document.getElementById('apiKey').value.trim();
const apiUrl = document.getElementById('apiUrl').value.trim() || providerUrls[provider];
const model = providerModels[provider];
const statusEl = document.getElementById('status');
if(!apiKey){statusEl.className='status err';statusEl.style.display='block';statusEl.textContent='Please enter your API key.';return;}
statusEl.className='status';statusEl.style.display='block';statusEl.textContent='Testing API connection...';
try{
const resp = await fetch('/api/model-status',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({external_api:{enabled:true,provider:provider,apiKey:apiKey,apiUrl:apiUrl,model:model}})});
const data = await resp.json();
if(data.available){statusEl.className='status ok';statusEl.textContent='API connected! Starting Kaguya IDE...';
const bindResp=await fetch('/api/device/bind',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({provider:provider,apiKey:apiKey,apiUrl:apiUrl,model:model})});
const bindData=await bindResp.json();
if(!bindData.success){throw new Error(bindData.error||'Failed to save API config');}
localStorage.setItem('kaguya_external_api',JSON.stringify({enabled:true,provider:provider,apiUrl:apiUrl,model:model,masked_api_key:bindData.masked_api_key}));
setTimeout(()=>{window.location.reload();},1500);
}else{statusEl.className='status err';statusEl.textContent='API test failed: '+(data.message||'Unknown error');}
}catch(e){statusEl.className='status err';statusEl.textContent='Connection error: '+e.message;}
}
</script></body></html>`;

    mainWindow.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(setupHtml)}`);

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
            webviewTag: false,
            sandbox: true,
            webSecurity: true,
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
        if (isLocalAppUrl(openUrl)) {
            return { action: 'allow' };
        }
        if (isAllowedExternalUrl(openUrl)) {
            shell.openExternal(openUrl);
        }
        return { action: 'deny' };
    });

    mainWindow.webContents.on('will-navigate', (event, navUrl) => {
        if (!isLocalAppUrl(navUrl)) {
            event.preventDefault();
        }
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
                { label: 'New Terminal', accelerator: 'CmdOrCtrl+`', click: () => mainWindow?.webContents.send('new-terminal') },
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

ipcMain.handle('terminal-create', () => ({ success: false, error: 'native_terminal_ipc_disabled' }));

ipcMain.on('terminal-write', (event, { sessionId, data }) => {
    mainWindow?.webContents.send('terminal-error', { sessionId, error: 'native_terminal_ipc_disabled' });
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
    return { success: false, error: 'generic_fs_ipc_disabled' };
    try {
        const encoding = options?.encoding || 'utf-8';
        const content = await fs.promises.readFile(filePath, encoding);
        return { success: true, content };
    } catch (err) {
        return { success: false, error: err.message, code: err.code };
    }
});

ipcMain.handle('fs-writeFile', async (event, filePath, content, options) => {
    return { success: false, error: 'generic_fs_ipc_disabled' };
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
    return { success: false, error: 'generic_fs_ipc_disabled' };
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
    return { success: false, error: 'generic_fs_ipc_disabled' };
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
    return { success: false, error: 'generic_fs_ipc_disabled' };
    try {
        await fs.promises.mkdir(dirPath, { recursive: options?.recursive ?? true });
        return { success: true };
    } catch (err) {
        return { success: false, error: err.message };
    }
});

ipcMain.handle('fs-remove', async (event, filePath) => {
    return { success: false, error: 'generic_fs_ipc_disabled' };
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
    return { success: false, error: 'generic_fs_ipc_disabled' };
    try {
        await fs.promises.rename(oldPath, newPath);
        return { success: true };
    } catch (err) {
        return { success: false, error: err.message };
    }
});

ipcMain.handle('fs-copy', async (event, src, dest) => {
    return { success: false, error: 'generic_fs_ipc_disabled' };
    try {
        await fs.promises.copyFile(src, dest);
        return { success: true };
    } catch (err) {
        return { success: false, error: err.message };
    }
});

ipcMain.handle('fs-exists', async (event, filePath) => {
    return false;
    try {
        await fs.promises.access(filePath);
        return true;
    } catch {
        return false;
    }
});

// ========== IPC: Shell Execution ==========

ipcMain.handle('shell-execute', async (event, command, options) => {
    return { success: false, error: 'shell_execute_ipc_disabled' };
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
    if (!isAllowedExternalUrl(url)) {
        return { success: false, error: 'blocked_url_protocol' };
    }
    await shell.openExternal(url);
    return { success: true };
});

ipcMain.handle('shell-showItemInFolder', async (event, filePath) => {
    return { success: false, error: 'generic_shell_ipc_disabled' };
});

ipcMain.handle('shell-openPath', async (event, filePath) => {
    return { success: false, error: 'generic_shell_ipc_disabled' };
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

ipcMain.handle('device-getInfo', async () => ({ success: true, device: getDeviceInfo() }));

ipcMain.handle('device-bind', async (event, config) => {
    const saved = saveDeviceVault(config || {});
    if (!saved.success) return saved;
    return {
        success: true,
        provider: saved.config.provider,
        api_url: saved.config.api_url,
        model: saved.config.model,
        masked_api_key: maskApiKey(saved.config.api_key),
        encryption: saved.encryption,
    };
});

ipcMain.handle('device-unbind', async () => clearDeviceVault());

// ========== Lifecycle ==========

function stopPythonServer() {
    if (goProcess) {
        console.log('[Main] Stopping Go backend...');
        try {
            if (process.platform === 'win32') {
                exec(`taskkill /pid ${goProcess.pid} /T /F`, (err) => {
                    if (err && goProcess) goProcess.kill();
                });
            } else {
                goProcess.kill('SIGTERM');
                setTimeout(() => {
                    if (goProcess) goProcess.kill('SIGKILL');
                }, 5000);
            }
        } catch (e) {
            try { goProcess.kill(); } catch (_) {}
        }
        goProcess = null;
    }
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
                    const backend = await startBackendServer(serverPort);
                    console.log(`[Main] ${backend.mode} backend started successfully`);
                    createWindow(serverPort);
                    createTray();
                } catch (err) {
                    console.error('[Main] Backend server failed:', err);
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
                const backend = await startBackendServer(serverPort);
                console.log(`[Main] ${backend.mode} backend started successfully`);
                createWindow(serverPort);
                createTray();
            } catch (err) {
                console.error('[Main] Backend server failed:', err);
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
