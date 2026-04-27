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
                catch { resolve(body); }
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

async function getDatasets(page = 1, size = 100) {
    return makeRequest(`/api/projects/${CONFIG.PROJECT_ID}/datasets?page=${page}&size=${size}&status=unconfirmed`, 'GET');
}

async function updateDataset(datasetId, updates) {
    return makeRequest(`/api/projects/${CONFIG.PROJECT_ID}/datasets?id=${datasetId}`, 'PATCH', updates);
}

function isValidConversation(question, answer) {
    const invalidPatterns = [
        /爹妈.*绝症|你妈逼|傻逼|智障|去死|滚|操你|废物|垃圾/,
        /^[\s.,，。!！?？]+$/,
        /^.{0,5}$/
    ];

    for (const pattern of invalidPatterns) {
        if (pattern.test(question) || pattern.test(answer)) {
            return false;
        }
    }

    const hasContent = question.trim().length > 5 && answer.trim().length > 5;
    return hasContent;
}

function isImageDataset(dataset) {
    return (dataset.images && dataset.images.length > 0) ||
           (Array.isArray(dataset.images) && dataset.images.length > 0) ||
           (typeof dataset.images === 'string' && dataset.images.length > 0);
}

async function main() {
    console.log('🔄 Easy Dataset 综合处理工具\n');
    console.log('项目ID:', CONFIG.PROJECT_ID);

    console.log('\n📊 获取未确认的数据集...');
    const datasetsResult = await getDatasets(1, 100);

    if (!datasetsResult.data || datasetsResult.data.length === 0) {
        console.log('✅ 没有未确认的数据集');
        return;
    }

    console.log(`找到 ${datasetsResult.total} 条未确认数据，开始分类处理...\n`);

    let textCount = 0;
    let imageCount = 0;
    let textValid = 0;
    let textInvalid = 0;
    let imageConfirmed = 0;

    console.log('📋 数据分类处理:');
    console.log('─'.repeat(60));

    for (const dataset of datasetsResult.data) {
        const isImage = isImageDataset(dataset);

        if (isImage) {
            imageCount++;
            const updateResult = await updateDataset(dataset.id, { confirmed: true });
            if (updateResult.success) {
                imageConfirmed++;
                console.log(`🖼️ 图片确认: ${dataset.chunkName}`);
            }
        } else {
            textCount++;
            const question = dataset.question || '';
            const answer = dataset.answer || '';

            const valid = isValidConversation(question, answer);

            if (valid) {
                textValid++;
                const updateResult = await updateDataset(dataset.id, { confirmed: true });
                if (updateResult.success) {
                    console.log(`✅ 文本确认: ${dataset.chunkName}`);
                }
            } else {
                textInvalid++;
                console.log(`❌ 文本无效: ${dataset.chunkName}`);
            }
        }

        if ((textCount + imageCount) % 20 === 0) {
            console.log(`\n已处理: ${textCount + imageCount}/${datasetsResult.data.length}`);
        }

        await new Promise(r => setTimeout(r, 100));
    }

    console.log('\n' + '='.repeat(60));
    console.log('📊 处理完成');
    console.log(`\n📝 文本数据:`);
    console.log(`   ✅ 有效确认: ${textValid} 条`);
    console.log(`   ❌ 无效数据: ${textInvalid} 条`);
    console.log(`   📦 文本总计: ${textCount} 条`);
    console.log(`\n🖼️ 图片数据:`);
    console.log(`   ✅ 已确认: ${imageConfirmed} 条`);
    console.log(`   📦 图片总计: ${imageCount} 条`);
    console.log(`\n📦 总计: ${textCount + imageCount} 条`);

    if (datasetsResult.total > datasetsResult.data.length) {
        console.log(`\n💡 还有 ${datasetsResult.total - datasetsResult.data.length} 条数据未处理`);
        console.log('   可再次运行此脚本或使用 Easy Dataset UI 手动处理');
    }

    console.log('\n🌐 打开 http://localhost:1717 查看处理结果');
}

main().catch(console.error);
