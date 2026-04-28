# Electron IPC Contract

Renderer access is intentionally narrow. Generic filesystem, shell, and native terminal IPC are disabled; renderer workflows must call the Flask backend, where workspace and permission checks run.

| API | Direction | Purpose | Risk | Permission |
| --- | --- | --- | --- | --- |
| `app-getInfo` | renderer -> main | Read app version/platform/resource path | Low | None |
| `app-getTheme` | renderer -> main | Read native theme | Low | None |
| `app-checkForUpdates` | renderer -> main | Ask updater for update metadata | Medium | Main process only |
| `device-getInfo` | renderer -> main | Read non-sensitive device identity and masked vault state | Low | None |
| `device-bind` | renderer -> main | Save external API config to encrypted device vault | High | Must not return full API key |
| `device-unbind` | renderer -> main | Delete encrypted device vault | High | User action |
| `dialog-openFile` | renderer -> main | Native file picker only | Medium | User-selected paths only |
| `dialog-openFolder` | renderer -> main | Native folder picker only | Medium | User-selected paths only |
| `dialog-saveFile` | renderer -> main | Native save picker only | Medium | User-selected path only |

## Disabled IPC

These handlers return structured denial if called and are not exposed by preload:

- `terminal-create`, `terminal-write`, `terminal-resize`, `terminal-kill`
- `fs-readFile`, `fs-writeFile`, `fs-readDir`, `fs-stat`, `fs-mkdir`, `fs-remove`, `fs-rename`, `fs-copy`, `fs-exists`
- `shell-execute`, `shell-showItemInFolder`, `shell-openPath`

`shell-openExternal` is not exposed by preload and only allows `https:`, `http:`, and `mailto:` when called internally.

## BrowserWindow

- `nodeIntegration: false`
- `contextIsolation: true`
- `sandbox: true`
- `webSecurity: true`
- Navigation is limited to the local Flask origin (`127.0.0.1`/`localhost`).
- New windows only open local app URLs directly; external URLs are passed to the OS only when the protocol is allowed.
