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

    on: (channel, callback) => {
        const validChannels = [
            'open-settings',
        ];
        if (validChannels.includes(channel)) {
            ipcRenderer.on(channel, (event, ...args) => callback(...args));
        }
    },
});
