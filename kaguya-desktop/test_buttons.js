const http = require('http');
const fs = require('fs');
const path = require('path');

const BASE_URL = 'http://127.0.0.1:58000';
const results = [];
let passCount = 0;
let failCount = 0;

function log(testName, passed, detail) {
    const status = passed ? 'PASS' : 'FAIL';
    const icon = passed ? '✅' : '❌';
    console.log(`${icon} [${status}] ${testName}`);
    if (detail) console.log(`   Detail: ${detail}`);
    results.push({ test: testName, passed, detail, time: new Date().toISOString() });
    if (passed) passCount++;
    else failCount++;
}

function fetchPage(urlPath) {
    return new Promise((resolve, reject) => {
        const url = new URL(urlPath, BASE_URL);
        http.get(url, (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => resolve({ status: res.statusCode, body: data }));
        }).on('error', reject);
    });
}

function extractJS(html) {
    const matches = [];
    const regex = /<script[^>]*>([\s\S]*?)<\/script>/g;
    let m;
    while ((m = regex.exec(html)) !== null) {
        if (m[1].trim().length > 0) matches.push(m[1]);
    }
    return matches;
}

async function testPageLoad(pageName, urlPath) {
    try {
        const res = await fetchPage(urlPath);
        log(`${pageName}: Page loads`, res.status === 200, `HTTP ${res.status}`);
        return res;
    } catch (e) {
        log(`${pageName}: Page loads`, false, e.message);
        return null;
    }
}

function testJSSyntax(pageName, jsCode) {
    const tempFile = path.join(require('os').tmpdir(), `kaguya_test_${Date.now()}.js`);
    try {
        fs.writeFileSync(tempFile, jsCode, 'utf8');
        const { execSync } = require('child_process');
        execSync(`node -c "${tempFile}"`, { encoding: 'utf8', timeout: 10000 });
        log(`${pageName}: JavaScript syntax check`, true, `${jsCode.length} chars validated`);
        return true;
    } catch (e) {
        const match = e.stderr ? e.stderr.match(/SyntaxError:.*/)?.[0] : e.message;
        log(`${pageName}: JavaScript syntax check`, false, match || e.message);
        return false;
    } finally {
        try { fs.unlinkSync(tempFile); } catch (e) {}
    }
}

function testFunctionExists(pageName, html, fnName) {
    const found = html.includes(`function ${fnName}`) || html.includes(`async function ${fnName}`);
    log(`${pageName}: Function '${fnName}' exists`, found, found ? 'Defined' : 'NOT FOUND');
    return found;
}

function testDOMElementExists(pageName, html, elementId) {
    const found = html.includes(`id="${elementId}"`) || html.includes(`id='${elementId}'`);
    log(`${pageName}: DOM element '${elementId}' exists`, found, found ? 'Present' : 'MISSING');
    return found;
}

function testOnclickBindings(pageName, html) {
    const onclickMatches = html.match(/onclick="[^"]*"/g) || [];
    const brokenBindings = [];
    const jsKeywords = new Set(['if','else','return','var','let','const','function','async','await','new','true','false','null','undefined','this','typeof','void','delete','throw','try','catch','finally','for','while','do','switch','case','break','continue','class','extends','super','import','export','default','yield','of','in']);
    for (const binding of onclickMatches) {
        const fnMatch = binding.match(/onclick="(\w+)\(/);
        if (fnMatch) {
            const fnName = fnMatch[1];
            if (!jsKeywords.has(fnName) && !html.includes(`function ${fnName}`) && !html.includes(`async function ${fnName}`)) {
                brokenBindings.push(fnName);
            }
        }
    }
    log(`${pageName}: All onclick bindings resolve`, brokenBindings.length === 0,
        brokenBindings.length === 0 ? `${onclickMatches.length} bindings OK` : `Undefined: ${brokenBindings.join(', ')}`);
    return brokenBindings.length === 0;
}

function testNoEscapeIssues(pageName, html) {
    const issues = [];
    if (html.includes("split('\\n')") || html.includes("split('\\n')")) {
    }
    const brokenSplit = html.match(/\.split\('[^']*\n/g);
    if (brokenSplit) issues.push('split with literal newline');
    const brokenReplace = html.match(/\.replace\('[^']*\n/g);
    if (brokenReplace) issues.push('replace with literal newline');
    log(`${pageName}: No Python escape issues`, issues.length === 0,
        issues.length === 0 ? 'Clean' : issues.join(', '));
    return issues.length === 0;
}

function testNoOverlayBlocking(pageName, html) {
    const hasDismissBtn = html.includes('Continue (File Browser Mode)');
    log(`${pageName}: API overlay has dismiss button`, hasDismissBtn,
        hasDismissBtn ? 'Dismiss button present' : 'MISSING dismiss button - overlay blocks all interaction');
    return hasDismissBtn;
}

async function runTests() {
    console.log('\n' + '='.repeat(70));
    console.log('  Kaguya IDE - Automated Frontend Button Test Suite');
    console.log('  ' + new Date().toISOString());
    console.log('='.repeat(70) + '\n');

    // === Chat Page Tests ===
    console.log('--- Chat Page (/) Tests ---\n');
    const chatRes = await testPageLoad('Chat', '/');
    if (chatRes) {
        const chatJS = extractJS(chatRes.body);
        const mainJS = chatJS.length > 0 ? chatJS[chatJS.length - 1] : '';
        testJSSyntax('Chat', mainJS);
        testFunctionExists('Chat', chatRes.body, 'sendMessage');
        testFunctionExists('Chat', chatRes.body, 'showToast');
        testFunctionExists('Chat', chatRes.body, 'respondPerm');
        testDOMElementExists('Chat', chatRes.body, 'mainInput');
        testDOMElementExists('Chat', chatRes.body, 'sendBtn');
        testDOMElementExists('Chat', chatRes.body, 'toast');
        testOnclickBindings('Chat', chatRes.body);
        testNoEscapeIssues('Chat', chatRes.body);
    }

    // === IDE Page Tests ===
    console.log('\n--- IDE Page (/agent-ide) Tests ---\n');
    const ideRes = await testPageLoad('IDE', '/agent-ide');
    if (ideRes) {
        const ideJS = extractJS(ideRes.body);
        const mainIDEJS = ideJS.length > 0 ? ideJS[0] : '';
        testJSSyntax('IDE', mainIDEJS);
        testFunctionExists('IDE', ideRes.body, 'sendAgentMsg');
        testFunctionExists('IDE', ideRes.body, 'showToast');
        testFunctionExists('IDE', ideRes.body, 'selectFiles');
        testFunctionExists('IDE', ideRes.body, 'selectFolder');
        testFunctionExists('IDE', ideRes.body, 'checkApiStatus');
        testFunctionExists('IDE', ideRes.body, 'loadFileTree');
        testFunctionExists('IDE', ideRes.body, 'browseHostDirs');
        testFunctionExists('IDE', ideRes.body, 'importFilesFromHost');
        testFunctionExists('IDE', ideRes.body, 'importEnvFromHost');
        testFunctionExists('IDE', ideRes.body, 'setMode');
        testFunctionExists('IDE', ideRes.body, 'showPermPanel');
        testFunctionExists('IDE', ideRes.body, 'showTaskPanel');
        testFunctionExists('IDE', ideRes.body, 'showBrowserPanel');
        testFunctionExists('IDE', ideRes.body, 'showProjectList');
        testFunctionExists('IDE', ideRes.body, 'compileCurrentFile');
        testFunctionExists('IDE', ideRes.body, 'openFile');
        testDOMElementExists('IDE', ideRes.body, 'agentInput');
        testDOMElementExists('IDE', ideRes.body, 'agentSendBtn');
        testDOMElementExists('IDE', ideRes.body, 'fileTree');
        testDOMElementExists('IDE', ideRes.body, 'terminalBody');
        testDOMElementExists('IDE', ideRes.body, 'toast');
        testOnclickBindings('IDE', ideRes.body);
        testNoEscapeIssues('IDE', ideRes.body);
        testNoOverlayBlocking('IDE', ideRes.body);
    }

    // === API Endpoint Tests ===
    console.log('\n--- API Endpoint Tests ---\n');
    try {
        const apiRes = await fetchPage('/agent/api-status');
        log('API: /agent/api-status responds', apiRes.status === 200 || apiRes.status === 400, `HTTP ${apiRes.status}`);
    } catch (e) {
        log('API: /agent/api-status responds', false, e.message);
    }

    try {
        const treeRes = await fetchPage('/agent/file-tree');
        log('API: /agent/file-tree responds', treeRes.status === 200 || treeRes.status === 405, `HTTP ${treeRes.status}`);
    } catch (e) {
        log('API: /agent/file-tree responds', false, e.message);
    }

    // === Summary ===
    console.log('\n' + '='.repeat(70));
    console.log(`  Results: ${passCount} PASSED, ${failCount} FAILED, ${passCount + failCount} TOTAL`);
    console.log('='.repeat(70) + '\n');

    if (failCount > 0) {
        console.log('Failed tests:');
        results.filter(r => !r.passed).forEach(r => {
            console.log(`  ❌ ${r.test}: ${r.detail}`);
        });
        console.log('');
    }

    const reportFile = path.join(__dirname, 'test_report.json');
    fs.writeFileSync(reportFile, JSON.stringify({ timestamp: new Date().toISOString(), total: passCount + failCount, passed: passCount, failed: failCount, results }, null, 2));
    console.log(`Report saved to: ${reportFile}`);

    process.exit(failCount > 0 ? 1 : 0);
}

runTests().catch(e => {
    console.error('Test runner error:', e);
    process.exit(2);
});
