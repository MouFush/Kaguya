const http = require('http');

const CONFIG = {
    HOST: 'localhost',
    PORT: 1717,
    PROJECT_ID: '4J1opHXSFqck'
};

console.log('========================================');
console.log('  启动 Easy Dataset 数据蒸馏');
console.log('========================================\n');

function triggerDistill(datasetIds) {
    return new Promise((resolve, reject) => {
        const postData = JSON.stringify({
            datasetIds: datasetIds,
            config: {
                model: 'qwen',
                temperature: 0.7,
                maxTokens: 2048
            }
        });

        const options = {
            hostname: CONFIG.HOST,
            port: CONFIG.PORT,
            path: `/api/projects/${CONFIG.PROJECT_ID}/distill/start`,
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
                console.log(`蒸馏响应状态: ${res.statusCode}`);
                console.log(`响应内容: ${body}`);
                try {
                    resolve(JSON.parse(body));
                } catch (e) {
                    resolve({ raw: body });
                }
            });
        });

        req.on('error', (e) => {
            console.error(`请求失败: ${e.message}`);
            reject(e);
        });

        req.write(postData);
        req.end();
    });
}

function getUndistilledDataIds() {
    return new Promise((resolve, reject) => {
        const options = {
            hostname: CONFIG.HOST,
            port: CONFIG.PORT,
            path: `/api/projects/${CONFIG.PROJECT_ID}/datasets?confirmed=false&take=100`,
            method: 'GET',
            headers: { 'Content-Type': 'application/json' }
        };

        const req = http.request(options, (res) => {
            let body = '';
            res.on('data', chunk => body += chunk);
            res.on('end', () => {
                try {
                    const result = JSON.parse(body);
                    const ids = result.data.map(d => d.id);
                    resolve(ids);
                } catch (e) {
                    reject(e);
                }
            });
        });

        req.on('error', reject);
        req.end();
    });
}

async function main() {
    console.log('[步骤1] 获取待蒸馏数据...\n');

    try {
        const ids = await getUndistilledDataIds();
        console.log(`待蒸馏数据数量: ${ids.length}`);
        console.log(`数据ID示例: ${ids.slice(0, 3).join(', ')}...`);

        console.log('\n[步骤2] 触发蒸馏处理...\n');

        const result = await triggerDistill(ids);
        console.log('\n蒸馏任务已提交！');
        console.log('请在 Easy Dataset 界面查看进度...');

    } catch (e) {
        console.error(`错误: ${e.message}`);
    }

    console.log('\n========================================');
    console.log('  蒸馏任务已启动');
    console.log('  地址: http://localhost:1717');
    console.log('========================================');
}

main().catch(console.error);
