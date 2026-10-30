const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const main = fs.readFileSync(path.join(root, 'main.js'), 'utf8');
const preload = fs.readFileSync(path.join(root, 'preload.js'), 'utf8');

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

assert(!/terminal\s*:/.test(preload), 'preload must not expose native terminal');
assert(!/new-terminal|toggle-terminal|clear-terminal/.test(preload), 'preload must not expose terminal menu channels');
assert(!/fs\s*:/.test(preload), 'preload must not expose generic fs');
assert(!/shell\s*:/.test(preload), 'preload must not expose generic shell');
assert(!/shell-execute/.test(preload), 'preload must not expose shell-execute');
assert(/sandbox:\s*true/.test(main), 'BrowserWindow must enable sandbox');
assert(!/sandbox:\s*false/.test(main), 'BrowserWindow must not disable sandbox');
assert(/webSecurity:\s*true/.test(main), 'BrowserWindow must enable webSecurity');
assert(/native_terminal_ipc_disabled/.test(main), 'native terminal IPC must be disabled');
assert(/generic_fs_ipc_disabled/.test(main), 'generic fs IPC must be disabled');
assert(/shell_execute_ipc_disabled/.test(main), 'shell-execute IPC must be disabled');
assert(!/const\s*\{\s*spawn,\s*exec,/.test(main), 'main process must not import generic exec');
assert(!/exec\(command/.test(main), 'shell-execute handler must not retain unreachable generic exec code');
assert(!/fs\.promises\.(readFile|writeFile|readdir|stat|mkdir|rm|unlink|rename|copyFile|access)\(filePath/.test(main), 'disabled generic fs IPC must not retain unreachable arbitrary path operations');
assert(!/spawn\(shellPath/.test(main), 'native terminal menu must not spawn a local shell');
assert(!/Access-Control-Allow-Origin['"],\s*['"]\*/.test(main), 'mini fallback must not allow wildcard CORS');
assert(/miniServerToken/.test(main), 'mini fallback protected API must use a startup token');
assert(/mini_origin_denied/.test(main), 'mini fallback must reject cross-origin protected API calls');
assert(!/error: 'No API configured'/.test(main), 'mini fallback must not retain legacy unstructured chat errors');
assert(/isAllowedExternalUrl/.test(main), 'external URL protocol allowlist must exist');
assert(/createSetupWindow[\s\S]*setWindowOpenHandler/.test(main), 'setup window must route external links through openExternal');
assert(/miniAssetAliases/.test(main), 'mini fallback must serve bounded asset aliases');
assert(/'\/sidebar-icon'/.test(main), 'mini fallback must serve sidebar icon alias');
assert(/'\/favicon.ico'/.test(main), 'mini fallback must serve favicon alias');

console.log('electron ipc contract ok');
