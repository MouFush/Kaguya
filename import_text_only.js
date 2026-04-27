const http = require('http');
const fs = require('fs');

const CONFIG = {
    HOST: 'localhost',
    PORT: 1717,
    PROJECT_ID: '4J1opHXSFqck',
    DATA_FILE: 'D:\\mira_export_clean\\easy_dataset_import.json'
};

console.log('🔄 导入纯文本数据到 Easy Dataset...\n');

const data = JSON.parse(fs.readFileSync(CONFIG.DATA_FILE, 'utf-8'));
console.log(`📊 待导入数据: ${data.length} 条\n`);

const postData = JSON.stringify({
    datasets: data,
    sourceInfo: 'mira_export_text_only'
});

const options = {
    hostname: CONFIG.HOST,
    port: CONFIG.PORT,
    path: `/api/projects/${CONFIG.PROJECT_ID}/datasets/import`,
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(postData)
    }
};

const req = http.request(options, (res) => {
    let body = '';
    res.on('data', chunk => body += chunk);
    res.on('end', () => {
        try {
            const result = JSON.parse(body);
            console.log(`✅ 导入完成！`);
            console.log(`   成功: ${result.success} 条`);
            console.log(`   失败: ${result.failed || 0} 条`);
        } catch (e) {
            console.log(body);
        }
    });
});

req.on('error', (e) => {
    console.error('❌ 请求失败:', e.message);
});

req.write(postData);
req.end();
