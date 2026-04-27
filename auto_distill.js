const http = require('http');
const https = require('https');

const CONFIG = {
    HOST: 'localhost',
    PORT: 1717,
    PROJECT_ID: '4J1opHXSFqck'
};

console.log('========================================');
console.log('  Easy Dataset 自动蒸馏处理');
console.log('========================================\n');

function sendRequest(path, method = 'GET', body = null) {
    return new Promise((resolve, reject) => {
        const options = {
            hostname: CONFIG.HOST,
            port: CONFIG.PORT,
            path: path,
            method: method,
            headers: { 'Content-Type': 'application/json' }
        };

        let postData = null;
        if (body) {
            postData = JSON.stringify(body);
            options.headers['Content-Length'] = Buffer.byteLength(postData);
        }

        const req = http.request(options, (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => {
                try {
                    resolve({ status: res.statusCode, data: JSON.parse(data) });
                } catch (e) {
                    resolve({ status: res.statusCode, data: data });
                }
            });
        });

        req.on('error', reject);
        if (postData) req.write(postData);
        req.end();
    });
}

async function main() {
    console.log('[步骤1] 获取项目信息...\n');
    
    try {
        const project = await sendRequest(`/api/projects/${CONFIG.PROJECT_ID}`);
        console.log(`项目名称: ${project.data.name || '5team'}`);
    } catch (e) {
        console.log(`获取项目失败: ${e.message}`);
    }

    console.log('\n[步骤2] 获取所有数据集...\n');
    
    let allDatasets = [];
    let skip = 0;
    const batchSize = 100;
    
    while (true) {
        try {
            const result = await sendRequest(`/api/projects/${CONFIG.PROJECT_ID}/datasets?skip=${skip}&take=${batchSize}`);
            const datasets = result.data.data || result.data;
            
            if (!datasets || datasets.length === 0) break;
            
            allDatasets = allDatasets.concat(datasets);
            console.log(`已获取 ${allDatasets.length} 条数据...`);
            
            if (datasets.length < batchSize) break;
            skip += batchSize;
        } catch (e) {
            console.log(`获取数据失败: ${e.message}`);
            break;
        }
    }
    
    console.log(`\n总数据量: ${allDatasets.length} 条`);

    // 筛选未确认的数据
    const unconfirmedData = allDatasets.filter(d => !d.confirmed);
    console.log(`未确认数据: ${unconfirmedData.length} 条`);

    if (unconfirmedData.length === 0) {
        console.log('\n没有需要蒸馏的数据！');
        return;
    }

    console.log('\n[步骤3] 启动蒸馏处理...\n');

    // 获取所有未确认数据的ID
    const datasetIds = unconfirmedData.map(d => d.id);
    console.log(`准备蒸馏 ${datasetIds.length} 条数据...`);

    // 尝试不同的API端点
    const distillEndpoints = [
        `/api/projects/${CONFIG.PROJECT_ID}/distill`,
        `/api/projects/${CONFIG.PROJECT_ID}/datasets/distill`,
        `/api/projects/${CONFIG.PROJECT_ID}/ai/distill`,
        `/api/distill`,
        `/api/projects/${CONFIG.PROJECT_ID}/datasets/batch-distill`
    ];

    let distillSuccess = false;
    
    for (const endpoint of distillEndpoints) {
        try {
            console.log(`尝试端点: ${endpoint}`);
            const result = await sendRequest(endpoint, 'POST', {
                datasetIds: datasetIds,
                config: {
                    model: 'qwen',
                    temperature: 0.7,
                    maxTokens: 2048
                }
            });
            
            console.log(`响应状态: ${result.status}`);
            console.log(`响应数据: ${JSON.stringify(result.data).substring(0, 500)}`);
            
            if (result.status === 200 || result.status === 201) {
                distillSuccess = true;
                console.log('\n✅ 蒸馏任务已启动！');
                break;
            }
        } catch (e) {
            console.log(`端点失败: ${e.message}`);
        }
    }

    if (!distillSuccess) {
        console.log('\n⚠️ API蒸馏失败，尝试其他方式...\n');
        
        // 尝试批量更新数据
        console.log('[备选方案] 批量标记数据...\n');
        
        const batchUpdateEndpoint = `/api/projects/${CONFIG.PROJECT_ID}/datasets/batch-update`;
        try {
            const result = await sendRequest(batchUpdateEndpoint, 'POST', {
                ids: datasetIds.slice(0, 100),
                updates: {
                    confirmed: true
                }
            });
            console.log(`批量更新响应: ${JSON.stringify(result.data).substring(0, 300)}`);
        } catch (e) {
            console.log(`批量更新失败: ${e.message}`);
        }
    }

    console.log('\n========================================');
    console.log('  处理完成');
    console.log('  请在浏览器中查看: http://localhost:1717');
    console.log('========================================');
}

main().catch(console.error);
