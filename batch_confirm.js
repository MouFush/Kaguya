const http = require('http');

const CONFIG = {
    HOST: 'localhost',
    PORT: 1717,
    PROJECT_ID: '4J1opHXSFqck'
};

function makeRequest(path, method, data = null) {
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
                catch { resolve({ raw: body }); }
            });
        });

        req.on('error', reject);
        if (data) {
            const postData = JSON.stringify(data);
            options.headers['Content-Length'] = Buffer.byteLength(postData);
            req.write(postData);
        }
        req.end();
    });
}

async function getAllDatasets() {
    const result = await makeRequest(`/api/projects/${CONFIG.PROJECT_ID}/datasets?pageSize=1000`, 'GET');
    return result;
}

async function updateDataset(datasetId, updates) {
    return makeRequest(`/api/projects/${CONFIG.PROJECT_ID}/datasets/${datasetId}`, 'PUT', updates);
}

function isValidConversation(question, answer) {
    if (!question || !answer) return false;
    
    const invalidPatterns = [
        /爹妈.*绝症|你妈逼|傻逼|智障|去死|操你|废物/,
        /^\s*$/,
    ];
    
    for (const pattern of invalidPatterns) {
        if (pattern.test(question) || pattern.test(answer)) {
            return false;
        }
    }
    
    if (question.trim().length < 5 || answer.trim().length < 10) {
        return false;
    }
    
    return true;
}

async function main() {
    console.log('🔄 Easy Dataset 批量数据处理工具\n');
    console.log('项目ID:', CONFIG.PROJECT_ID);
    
    console.log('\n📊 获取所有数据集...');
    const result = await getAllDatasets();
    
    if (!result.data || result.data.length === 0) {
        console.log('❌ 没有找到数据');
        return;
    }
    
    const total = result.pagination?.total || result.data.length;
    console.log(`找到 ${total} 条数据\n`);
    
    let validCount = 0;
    let invalidCount = 0;
    let errorCount = 0;
    
    console.log('开始处理...\n');
    
    for (let i = 0; i < result.data.length; i++) {
        const dataset = result.data[i];
        const question = dataset.question || '';
        const answer = dataset.answer || '';
        
        const valid = isValidConversation(question, answer);
        
        if (valid) {
            try {
                const updateResult = await updateDataset(dataset.id, {
                    ...dataset,
                    confirmed: true
                });
                
                if (updateResult.id || updateResult.success !== false) {
                    validCount++;
                    if (validCount % 50 === 0) {
                        console.log(`✅ 已确认 ${validCount} 条有效数据`);
                    }
                } else {
                    errorCount++;
                }
            } catch (e) {
                errorCount++;
            }
        } else {
            invalidCount++;
        }
        
        if ((i + 1) % 100 === 0) {
            console.log(`📊 进度: ${i + 1}/${result.data.length}`);
        }
    }
    
    console.log('\n' + '='.repeat(60));
    console.log('📊 处理完成');
    console.log(`   ✅ 有效并确认: ${validCount} 条`);
    console.log(`   ❌ 无效数据: ${invalidCount} 条`);
    console.log(`   ⚠️ 处理错误: ${errorCount} 条`);
    console.log(`   📦 总计: ${result.data.length} 条`);
    console.log(`   📈 有效率: ${((validCount / result.data.length) * 100).toFixed(1)}%`);
    
    console.log('\n🌐 打开 http://localhost:1717 查看结果');
}

main().catch(console.error);
