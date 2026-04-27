const http = require('http');

function makeRequest(path) {
    return new Promise((resolve, reject) => {
        const options = {
            hostname: 'localhost',
            port: 1717,
            path: path,
            method: 'GET',
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

async function main() {
    console.log('📊 数据集质量检查报告\n');
    console.log('='.repeat(60));
    
    const confirmed = await makeRequest('/api/projects/4J1opHXSFqck/datasets?page=1&size=50&status=confirmed');
    const unconfirmed = await makeRequest('/api/projects/4J1opHXSFqck/datasets?page=1&size=10&status=unconfirmed');
    
    console.log('\n📈 数据统计:');
    console.log('  已确认数据:', confirmed.confirmedCount || confirmed.total || '?');
    console.log('  未确认数据:', unconfirmed.total || 0);
    
    let textCount = 0;
    let imageCount = 0;
    let textSamples = [];
    let imageSamples = [];
    let qualityScores = [];
    
    if (confirmed.data) {
        confirmed.data.forEach(d => {
            if (d.images && d.images.length > 0) {
                imageCount++;
                if (imageSamples.length < 3) imageSamples.push(d);
            } else {
                textCount++;
                if (textSamples.length < 5) textSamples.push(d);
                if (d.score) qualityScores.push(d.score);
            }
        });
    }
    
    console.log('\n📊 数据类型分布 (前50条已确认):');
    console.log('  文本对话数据:', textCount);
    console.log('  图片数据:', imageCount);
    
    if (qualityScores.length > 0) {
        const avg = qualityScores.reduce((a, b) => a + b, 0) / qualityScores.length;
        console.log('\n📊 文本数据质量分数:');
        console.log('  平均分数:', avg.toFixed(2));
        console.log('  最高分数:', Math.max(...qualityScores).toFixed(2));
        console.log('  最低分数:', Math.min(...qualityScores).toFixed(2));
    }
    
    if (textSamples.length > 0) {
        console.log('\n📝 文本数据样本:');
        textSamples.forEach((s, i) => {
            console.log('\n--- 样本 ' + (i+1) + ': ' + s.chunkName + ' ---');
            const q = s.question || '';
            const a = s.answer || '';
            console.log('问题 (' + q.length + '字):', q.substring(0, 100) + (q.length > 100 ? '...' : ''));
            console.log('回答 (' + a.length + '字):', a.substring(0, 100) + (a.length > 100 ? '...' : ''));
        });
    }
    
    if (imageSamples.length > 0) {
        console.log('\n🖼️ 图片数据样本:');
        imageSamples.forEach((s, i) => {
            console.log('  ' + (i+1) + '. ' + s.chunkName + ' - 图片数: ' + (s.images?.length || 0));
        });
    }
    
    console.log('\n' + '='.repeat(60));
    console.log('✅ 检查完成');
}

main().catch(console.error);
