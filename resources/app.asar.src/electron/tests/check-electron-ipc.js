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
assert(/isAllowedExternalUrl/.test(main), 'external URL protocol allowlist must exist');

console.log('electron ipc contract ok');
