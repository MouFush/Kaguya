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

async function getUnconfirmedData() {
    let allData = [];
    let page = 1;
    
    while (true) {
        const result = await makeRequest(`/api/projects/${CONFIG.PROJECT_ID}/datasets?confirmed=false&page=${page}&pageSize=100`);
        if (!result.data || result.data.length === 0) break;
        allData = allData.concat(result.data);
        if (allData.length >= result.total) break;
        page++;
    }
    
    return allData;
}

async function confirmDataset(dataset) {
    const updateData = {
        ...dataset,
        confirmed: true
    };
    return makeRequest(`/api/projects/${CONFIG.PROJECT_ID}/datasets/${dataset.id}`, 'PUT', updateData);
}

function isValidConversation(question, answer) {
    if (!question || !answer) return false;
    
    const q = question.trim();
    const a = answer.trim();
    
    if (q.length < 5 || a.length < 10) return false;
    
    const invalidPatterns = [
        /爹妈.*绝症|你妈逼|傻逼|智障|去死|操你|废物|滚蛋/,
        /^\s*$/,
        /^[.,，。!！?？\s]+$/
    ];
    
    for (const pattern of invalidPatterns) {
        if (pattern.test(q) || pattern.test(a)) return false;
    }
    
    return true;
}

async function main() {
    console.log('🔄 批量确认待处理数据\n');
    console.log('项目ID:', CONFIG.PROJECT_ID);
    
    console.log('\n📊 获取待确认数据...');
    const unconfirmed = await getUnconfirmedData();
    console.log(`找到 ${unconfirmed.length} 条待确认数据\n`);
    
    if (unconfirmed.length === 0) {
        console.log('✅ 没有待确认的数据');
        return;
    }
    
    let validCount = 0;
    let invalidCount = 0;
    let errorCount = 0;
    
    console.log('开始处理...\n');
    
    for (let i = 0; i < unconfirmed.length; i++) {
        const dataset = unconfirmed[i];
        const question = dataset.question || '';
        const answer = dataset.answer || '';
        
        const valid = isValidConversation(question, answer);
        
        if (valid) {
            try {
                const result = await confirmDataset(dataset);
                if (result.id || result.success !== false) {
                    validCount++;
                } else {
                    errorCount++;
                }
            } catch (e) {
                errorCount++;
            }
        } else {
            invalidCount++;
        }
        
        if ((i + 1) % 50 === 0) {
            console.log(`📊 进度: ${i + 1}/${unconfirmed.length} | ✅ 有效: ${validCount} | ❌ 无效: ${invalidCount}`);
        }
        
        if ((i + 1) % 20 === 0) {
            await new Promise(r => setTimeout(r, 50));
        }
    }
    
    console.log('\n' + '='.repeat(60));
    console.log('📊 处理完成');
    console.log(`   ✅ 有效并确认: ${validCount} 条`);
    console.log(`   ❌ 无效数据: ${invalidCount} 条`);
    console.log(`   ⚠️ 处理错误: ${errorCount} 条`);
    console.log(`   📦 总计: ${unconfirmed.length} 条`);
    console.log(`   📈 有效率: ${((validCount / unconfirmed.length) * 100).toFixed(1)}%`);
    
    console.log('\n🌐 打开 http://localhost:1717 查看结果');
}

main().catch(console.error);
