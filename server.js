const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = 8101;
const DIRECTORY = __dirname;

const MIME_TYPES = {
    '.html': 'text/html',
    '.css': 'text/css',
    '.js': 'application/javascript',
    '.json': 'application/json',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.gif': 'image/gif',
    '.svg': 'image/svg+xml',
    '.ico': 'image/x-icon'
};

const server = http.createServer((req, res) => {
    let filePath = req.url.split('?')[0];
    if (filePath === '/') filePath = '/code_runner_v5.html';
    
    const fullPath = path.join(DIRECTORY, filePath);
    const ext = path.extname(filePath).toLowerCase();
    const contentType = MIME_TYPES[ext] || 'application/octet-stream';
    
    fs.readFile(fullPath, (err, data) => {
        if (err) {
            res.writeHead(404);
            res.end('Not Found: ' + filePath);
            return;
        }
        
        res.writeHead(200, {
            'Content-Type': contentType,
            'Access-Control-Allow-Origin': '*',
            'Cache-Control': 'no-cache'
        });
        res.end(data);
    });
});

server.listen(PORT, () => {
    console.log('');
    console.log('================================================');
    console.log('  MiniMind CS336 Learning Platform v5.0');
    console.log('================================================');
    console.log(`  Server: http://localhost:${PORT}/`);
    console.log('  代码与讲解分离 | 干净代码示例 | 逐行代码详解');
    console.log('================================================');
    console.log('');
});
