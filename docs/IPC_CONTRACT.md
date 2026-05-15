# Electron IPC Contract

This contract describes the IPC surface exposed by `desktop/resources/app.asar.src/electron/preload.js` and handled in `desktop/resources/app.asar.src/electron/main.js`.

## Exposed Renderer API

The renderer receives one object: `window.kaguyaDesktop`.

| API | Purpose | Risk | Permission/Boundary |
| --- | --- | --- | --- |
| `isDesktop()` | Desktop feature detection | low | No native capability |
| `getAppInfo()` | Read app/runtime metadata | low | No secrets |
| `getTheme()` | Read native theme | low | No secrets |
| `checkForUpdates()` | Trigger updater check | medium | No shell execution |
| `device.getInfo()` | Read device identity and masked vault metadata | medium | Must not return full API key |
| `device.bind(config)` | Save provider config in encrypted device vault | high | Normalize `apiKey/api_key`, never echo full key |
| `device.unbind()` | Delete encrypted device vault | medium | No full key returned |
| `dialog.openFile(options)` | User-selected file picker | medium | User gesture only; returns chosen paths |
| `dialog.openFolder(options)` | User-selected folder picker | medium | User gesture only; returns chosen paths |
| `dialog.saveFile(options)` | User-selected save picker | medium | User gesture only; returns chosen path |
| `on('open-settings', cb)` | App event callback | low | Whitelisted channel only |

## Disabled Native Capabilities

The following handlers exist only for compatibility and must return disabled errors:

- `terminal-create`
- `fs-readFile`
- `fs-writeFile`
- `fs-readDir`
- `fs-stat`
- `fs-mkdir`
- `fs-remove`
- `fs-rename`
- `fs-copy`
- `fs-exists`
- `shell-execute`
- `shell-showItemInFolder`
- `shell-openPath`

Workspace file actions and terminal commands must go through Go backend routes so workspace authorization, permission checks, and audit logging apply.

## Navigation Boundary

- Main BrowserWindow loads only `http://127.0.0.1:<port>/`.
- `will-navigate` blocks non-local app URLs.
- `setWindowOpenHandler` allows local app URLs and opens only `http:`, `https:`, or `mailto:` externally.
- `file:`, `javascript:`, and `data:` external opens are blocked.

## BrowserWindow Security Settings

Both setup and main windows use:

- `contextIsolation: true`
- `nodeIntegration: false`
- `sandbox: true`
- `webSecurity: true`

