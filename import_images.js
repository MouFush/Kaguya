const http = require('http');
const fs = require('fs');

const CONFIG = {
    HOST: 'localhost',
    PORT: 1717,
    PROJECT_ID: '4J1opHXSFqck',
    DATA_FILE: 'D:\\mira_export_images_dataset\\easy_dataset_import.json',
    BATCH_SIZE: 100
};

console.log('🔄 导入图片数据到 Easy Dataset...\n');

const allData = JSON.parse(fs.readFileSync(CONFIG.DATA_FILE, 'utf-8'));
console.log(`📊 总数据: ${allData.length} 条\n`);

async function importBatch(data, batchIndex) {
    return new Promise((resolve, reject) => {
        const postData = JSON.stringify({
            datasets: data,
            sourceInfo: 'mira_export_images'
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
                    resolve(result);
                } catch (e) {
                    resolve({ success: 0, failed: data.length });
                }
            });
        });

        req.on('error', reject);
        req.write(postData);
        req.end();
    });
}

async function main() {
    let totalSuccess = 0;
    let totalFailed = 0;

    for (let i = 0; i < allData.length; i += CONFIG.BATCH_SIZE) {
        const batch = allData.slice(i, i + CONFIG.BATCH_SIZE);
        const batchIndex = Math.floor(i / CONFIG.BATCH_SIZE) + 1;

        console.log(`导入批次 ${batchIndex} (${i + 1}-${i + batch.length}/${allData.length})...`);

        const result = await importBatch(batch, batchIndex);
        totalSuccess += result.success || 0;
        totalFailed += result.failed || 0;

        console.log(`  成功: ${result.success || 0}, 失败: ${result.failed || 0}`);

        if (i + CONFIG.BATCH_SIZE < allData.length) {
            await new Promise(r => setTimeout(r, 500));
        }
    }

    console.log('\n========== 导入完成 ==========');
    console.log(`✅ 总成功: ${totalSuccess} 条`);
    console.log(`❌ 总失败: ${totalFailed} 条`);
    console.log(`📦 总计: ${totalSuccess + totalFailed} 条`);
}

main().catch(console.error);
