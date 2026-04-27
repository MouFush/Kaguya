const http = require('http');
const fs = require('fs');
const path = require('path');

const CONFIG = {
    HOST: 'localhost',
    PORT: 1717,
    PROJECT_ID: '4J1opHXSFqck',
    BATCH_FILES: [
        'D:\\mira_easy_dataset\\batch_1.json',
        'D:\\mira_easy_dataset\\batch_2.json',
        'D:\\mira_easy_dataset\\batch_3.json',
        'D:\\mira_easy_dataset\\batch_4.json',
        'D:\\mira_easy_dataset\\batch_5.json'
    ]
};

console.log('========================================');
console.log('  Easy Dataset 自动化数据处理');
console.log('========================================\n');

function convertToEasyDatasetFormat(alpacaData, batchIndex) {
    return alpacaData.map((item, index) => ({
        question: item.instruction,
        answer: item.output,
        chunkName: `batch_${batchIndex}_${index}`,
        chunkContent: `${item.instruction}\n\n${item.output}`,
        model: 'alpaca_import',
        questionLabel: 'conversation',
        tags: JSON.stringify(['导入数据', `批次${batchIndex}`]),
        note: `来源: batch_${batchIndex}.json`,
        confirmed: false,
        score: 1,
        images: [],
        imageDescriptions: [],
        enhancedSummary: null,
        generatedQA: null,
        metadata: {
            hasImages: false,
            apiEnhanced: false,
            batchIndex: batchIndex
        }
    }));
}

function importBatch(batchFile, batchIndex) {
    return new Promise((resolve, reject) => {
        if (!fs.existsSync(batchFile)) {
            console.log(`⚠️ 文件不存在: ${batchFile}`);
            resolve(null);
            return;
        }

        const alpacaData = JSON.parse(fs.readFileSync(batchFile, 'utf-8'));
        console.log(`\n[批次 ${batchIndex}] 导入数据: ${alpacaData.length} 条`);

        const easyDatasetFormat = convertToEasyDatasetFormat(alpacaData, batchIndex);

        const postData = JSON.stringify({
            datasets: easyDatasetFormat,
            sourceInfo: `batch_${batchIndex}`
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
                    console.log(`   响应状态: ${res.statusCode}`);
                    if (result.success !== undefined) {
                        console.log(`   ✅ 成功: ${result.success} 条`);
                        if (result.failed) console.log(`   ❌ 失败: ${result.failed} 条`);
                    }
                    resolve({ success: true, data: result });
                } catch (e) {
                    console.log(`   响应: ${body.substring(0, 500)}`);
                    resolve({ success: false, error: body });
                }
            });
        });

        req.on('error', (e) => {
            console.error(`   ❌ 请求失败: ${e.message}`);
            resolve({ success: false, error: e.message });
        });

        req.write(postData);
        req.end();
    });
}

function getDatasets() {
    return new Promise((resolve, reject) => {
        const options = {
            hostname: CONFIG.HOST,
            port: CONFIG.PORT,
            path: `/api/projects/${CONFIG.PROJECT_ID}/datasets`,
            method: 'GET',
            headers: { 'Content-Type': 'application/json' }
        };

        const req = http.request(options, (res) => {
            let body = '';
            res.on('data', chunk => body += chunk);
            res.on('end', () => {
                try {
                    resolve(JSON.parse(body));
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
    console.log('[步骤1] 检查当前数据集...\n');
    
    try {
        const currentDatasets = await getDatasets();
        console.log(`当前数据集数量: ${currentDatasets.length || 0}`);
    } catch (e) {
        console.log(`获取数据集失败: ${e.message}`);
    }

    console.log('\n[步骤2] 导入批次数据...\n');

    let totalImported = 0;
    let totalSuccess = 0;
    
    for (let i = 0; i < CONFIG.BATCH_FILES.length; i++) {
        const batchFile = CONFIG.BATCH_FILES[i];
        const result = await importBatch(batchFile, i + 1);
        if (result && result.success) {
            totalImported++;
            if (result.data && result.data.success) {
                totalSuccess += result.data.success;
            }
        }
        await new Promise(r => setTimeout(r, 500));
    }

    console.log(`\n========================================`);
    console.log(`  导入完成: ${totalImported}/${CONFIG.BATCH_FILES.length} 个批次`);
    console.log(`  成功导入: ${totalSuccess} 条数据`);
    console.log(`========================================\n`);

    console.log('[步骤3] 检查导入后的数据集...\n');
    
    try {
        const datasets = await getDatasets();
        console.log(`当前数据集数量: ${datasets.length || 0}`);
    } catch (e) {
        console.log(`获取数据集失败: ${e.message}`);
    }

    console.log('\n========================================');
    console.log('  导入完成！');
    console.log('  请在 Easy Dataset 中进行蒸馏操作');
    console.log('  地址: http://localhost:1717');
    console.log('========================================');
}

main().catch(console.error);
