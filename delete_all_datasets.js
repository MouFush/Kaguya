const http = require('http');

const CONFIG = {
    HOST: 'localhost',
    PORT: 1717,
    PROJECT_ID: '4J1opHXSFqck'
};

function makeRequest(path, method) {
    return new Promise((resolve, reject) => {
        const options = {
            hostname: CONFIG.HOST,
            port: CONFIG.PORT,
            path: path,
            method: method,
            headers: { 'Content-Type': 'application/json' }
        };
        const req = http.request(options, (res) => {
            let body = '';
            res.on('data', chunk => body += chunk);
            res.on('end', () => {
                try { resolve(JSON.parse(body)); }
                catch { resolve(body); }
            });
        });
        req.on('error', reject);
        req.end();
    });
}

async function deleteDataset(datasetId) {
    return makeRequest('/api/projects/' + CONFIG.PROJECT_ID + '/datasets?id=' + datasetId, 'DELETE');
}

async function getAllDatasets() {
    return makeRequest('/api/projects/' + CONFIG.PROJECT_ID + '/datasets?page=1&size=1000&selectedAll=true', 'GET');
}

async function main() {
    console.log('正在获取所有数据集...\n');

    const result = await getAllDatasets();

    if (Array.isArray(result)) {
        console.log('找到 ' + result.length + ' 条数据集，开始删除...\n');

        let deleted = 0;
        for (const dataset of result) {
            try {
                await deleteDataset(dataset.id);
                deleted++;
                if (deleted % 50 === 0) {
                    console.log('已删除: ' + deleted + '/' + result.length);
                }
            } catch (e) {
                console.log('删除失败: ' + dataset.id);
            }
        }
        console.log('\n✅ 已删除所有 ' + deleted + ' 条数据集');
    } else {
        console.log('获取数据集失败: ' + JSON.stringify(result));
    }
}

main().then(() => console.log('\n完成'));
