const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('kaguyaDesktop', {
    version: '3.1.0',
    platform: process.platform,

    isDesktop: () => true,

    getAppInfo: () => ipcRenderer.invoke('app-getInfo'),
    getTheme: () => ipcRenderer.invoke('app-getTheme'),
    checkForUpdates: () => ipcRenderer.invoke('app-checkForUpdates'),

    terminal: {
        create: (opts) => ipcRenderer.invoke('terminal-create', opts),
        write: (sessionId, data) => ipcRenderer.send('terminal-write', { sessionId, data }),
        resize: (sessionId, cols, rows) => ipcRenderer.send('terminal-resize', { sessionId, cols, rows }),
        kill: (sessionId) => ipcRenderer.send('terminal-kill', { sessionId }),
        onData: (callback) => ipcRenderer.on('terminal-data', (event, data) => callback(data)),
        onExit: (callback) => ipcRenderer.on('terminal-exit', (event, data) => callback(data)),
        onError: (callback) => ipcRenderer.on('terminal-error', (event, data) => callback(data)),
        onCreated: (callback) => ipcRenderer.on('terminal-created', (event, data) => callback(data)),
    },

    fs: {
        readFile: (path, options) => ipcRenderer.invoke('fs-readFile', path, options),
        writeFile: (path, content, options) => ipcRenderer.invoke('fs-writeFile', path, content, options),
        readDir: (path, options) => ipcRenderer.invoke('fs-readDir', path, options),
        stat: (path) => ipcRenderer.invoke('fs-stat', path),
        mkdir: (path, options) => ipcRenderer.invoke('fs-mkdir', path, options),
        remove: (path) => ipcRenderer.invoke('fs-remove', path),
        rename: (oldPath, newPath) => ipcRenderer.invoke('fs-rename', oldPath, newPath),
        copy: (src, dest) => ipcRenderer.invoke('fs-copy', src, dest),
        exists: (path) => ipcRenderer.invoke('fs-exists', path),
    },

    shell: {
        execute: (command, options) => ipcRenderer.invoke('shell-execute', command, options),
        openExternal: (url) => ipcRenderer.invoke('shell-openExternal', url),
        showItemInFolder: (path) => ipcRenderer.invoke('shell-showItemInFolder', path),
        openPath: (path) => ipcRenderer.invoke('shell-openPath', path),
    },

    dialog: {
        openFile: (options) => ipcRenderer.invoke('dialog-openFile', options),
        openFolder: (options) => ipcRenderer.invoke('dialog-openFolder', options),
        saveFile: (options) => ipcRenderer.invoke('dialog-saveFile', options),
    },

    on: (channel, callback) => {
        const validChannels = [
            'open-settings', 'new-terminal', 'toggle-terminal', 'clear-terminal',
            'terminal-data', 'terminal-exit', 'terminal-error', 'terminal-created',
        ];
        if (validChannels.includes(channel)) {
            ipcRenderer.on(channel, (event, ...args) => callback(...args));
        }
    },
});
