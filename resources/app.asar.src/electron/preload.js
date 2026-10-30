const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('kaguyaDesktop', {
    version: '3.1.0',
    platform: process.platform,

    isDesktop: () => true,

    getAppInfo: () => ipcRenderer.invoke('app-getInfo'),
    getTheme: () => ipcRenderer.invoke('app-getTheme'),
    checkForUpdates: () => ipcRenderer.invoke('app-checkForUpdates'),
    device: {
        getInfo: () => ipcRenderer.invoke('device-getInfo'),
        bind: (config) => ipcRenderer.invoke('device-bind', config),
        unbind: () => ipcRenderer.invoke('device-unbind'),
    },

    dialog: {
        openFile: (options) => ipcRenderer.invoke('dialog-openFile', options),
        openFolder: (options) => ipcRenderer.invoke('dialog-openFolder', options),
        saveFile: (options) => ipcRenderer.invoke('dialog-saveFile', options),
    },

    terminal: {
        create: (options) => ipcRenderer.invoke('terminal-create', options),
        write: (sessionId, data) => ipcRenderer.send('terminal-write', { sessionId, data }),
        resize: (sessionId, cols, rows) => ipcRenderer.send('terminal-resize', { sessionId, cols, rows }),
        kill: (sessionId) => ipcRenderer.send('terminal-kill', { sessionId }),
        onData: (callback) => ipcRenderer.on('terminal-data', (event, data) => callback(data)),
        onExit: (callback) => ipcRenderer.on('terminal-exit', (event, data) => callback(data)),
        onError: (callback) => ipcRenderer.on('terminal-error', (event, data) => callback(data)),
    },

    on: (channel, callback) => {
        const validChannels = [
            'open-settings',
        ];
        if (validChannels.includes(channel)) {
            ipcRenderer.on(channel, (event, ...args) => callback(...args));
        }
    },
});
