const http = require('http');

const CONFIG = {
    HOST: 'localhost',
    PORT: 1717,
    PROJECT_ID: '4J1opHXSFqck'
};

function makeRequest(path) {
    return new Promise((resolve, reject) => {
        const options = {
            hostname: CONFIG.HOST,
            port: CONFIG.PORT,
            path: path,
            method: 'GET',
            headers: { 'Content-Type': 'application/json' }
        };

        const req = http.request(options, (res) => {
            let body = '';
            res.on('data', chunk => body += chunk);
            res.on('end', () => {
                try { resolve(JSON.parse(body)); }
                catch { resolve({}); }
            });
        });
        req.on('error', reject);
        req.end();
    });
}

async function getAllData() {
    let allData = [];
    let page = 1;
    const pageSize = 100;
    
    while (true) {
        const result = await makeRequest(`/api/projects/${CONFIG.PROJECT_ID}/datasets?page=${page}&pageSize=${pageSize}`);
        if (!result.data) {
            if (result.total) {
                console.log(`API返回total=${result.total}，但data为空`);
            }
            break;
        }
        if (result.data.length === 0) break;
        allData = allData.concat(result.data);
        console.log(`获取第${page}页: ${result.data.length}条，累计: ${allData.length}条`);
        if (allData.length >= result.total) break;
        page++;
        await new Promise(r => setTimeout(r, 100));
    }
    
    return allData;
}

async function main() {
    console.log('╔════════════════════════════════════════════════════════════╗');
    console.log('║          Easy Dataset 数据集质量检查报告                    ║');
    console.log('╚════════════════════════════════════════════════════════════╝\n');
    
    console.log('📊 正在获取所有数据...\n');
    const allData = await getAllData();
    
    const confirmed = allData.filter(d => d.confirmed === true);
    const unconfirmed = allData.filter(d => d.confirmed !== true);
    
    console.log('═════════════════ 数据概览 ═════════════════\n');
    console.log(`📦 总数据量:     ${allData.length} 条`);
    console.log(`✅ 已确认有效:   ${confirmed.length} 条 (${(confirmed.length/allData.length*100).toFixed(1)}%)`);
    console.log(`⏳ 待确认数据:   ${unconfirmed.length} 条 (${(unconfirmed.length/allData.length*100).toFixed(1)}%)`);
    
    if (confirmed.length === 0) {
        console.log('\n⚠️ 没有已确认的有效数据');
        return;
    }
    
    console.log('\n═════════════════ 内容质量分析 ═════════════════\n');
    
    const questionLengths = confirmed.map(d => (d.question || '').length);
    const answerLengths = confirmed.map(d => (d.answer || '').length);
    
    const avgQ = questionLengths.reduce((a, b) => a + b, 0) / questionLengths.length;
    const avgA = answerLengths.reduce((a, b) => a + b, 0) / answerLengths.length;
    const maxQ = Math.max(...questionLengths);
    const maxA = Math.max(...answerLengths);
    const minQ = Math.min(...questionLengths);
    const minA = Math.min(...answerLengths);
    
    console.log(`📝 问题长度统计:`);
    console.log(`   平均长度: ${avgQ.toFixed(1)} 字`);
    console.log(`   最短: ${minQ} 字 | 最长: ${maxQ} 字`);
    console.log(`   中位数: ${questionLengths.sort((a,b)=>a-b)[Math.floor(questionLengths.length/2)]} 字`);
    
    console.log(`\n💬 回答长度统计:`);
    console.log(`   平均长度: ${avgA.toFixed(1)} 字`);
    console.log(`   最短: ${minA} 字 | 最长: ${maxA} 字`);
    console.log(`   中位数: ${answerLengths.sort((a,b)=>a-b)[Math.floor(answerLengths.length/2)]} 字`);
    
    console.log('\n═════════════════ 数据分布 ═════════════════\n');
    
    const shortQ = confirmed.filter(d => (d.question || '').length < 10).length;
    const shortA = confirmed.filter(d => (d.answer || '').length < 20).length;
    const mediumQ = confirmed.filter(d => {const l=(d.question||'').length; return l>=10 && l<50;}).length;
    const mediumA = confirmed.filter(d => {const l=(d.answer||'').length; return l>=20 && l<100;}).length;
    const longQ = confirmed.filter(d => (d.question || '').length >= 50).length;
    const longA = confirmed.filter(d => (d.answer || '').length >= 100).length;
    
    console.log(`问题长度分布:`);
    console.log(`   短 (<10字):    ${shortQ} 条 (${(shortQ/confirmed.length*100).toFixed(1)}%)`);
    console.log(`   中 (10-50字):  ${mediumQ} 条 (${(mediumQ/confirmed.length*100).toFixed(1)}%)`);
    console.log(`   长 (≥50字):    ${longQ} 条 (${(longQ/confirmed.length*100).toFixed(1)}%)`);
    
    console.log(`\n回答长度分布:`);
    console.log(`   短 (<20字):    ${shortA} 条 (${(shortA/confirmed.length*100).toFixed(1)}%)`);
    console.log(`   中 (20-100字): ${mediumA} 条 (${(mediumA/confirmed.length*100).toFixed(1)}%)`);
    console.log(`   长 (≥100字):   ${longA} 条 (${(longA/confirmed.length*100).toFixed(1)}%)`);
    
    console.log('\n═════════════════ 数据来源分析 ═════════════════\n');
    
    const sources = {};
    confirmed.forEach(d => {
        const source = d.chunkName?.includes('forward') ? '转发消息' : 
                       d.chunkName?.includes('chat') ? '群聊记录' : '其他';
        sources[source] = (sources[source] || 0) + 1;
    });
    
    Object.entries(sources).forEach(([source, count]) => {
        console.log(`   ${source}: ${count} 条 (${(count/confirmed.length*100).toFixed(1)}%)`);
    });
    
    console.log('\n═════════════════ 样本展示 ═════════════════\n');
    
    const samples = confirmed.slice(0, 3);
    samples.forEach((item, i) => {
        console.log(`【样本 ${i + 1}】来源: ${item.chunkName || '未知'}`);
        console.log(`问题: ${item.question?.substring(0, 60)}${item.question?.length > 60 ? '...' : ''}`);
        console.log(`回答: ${item.answer?.substring(0, 80)}${item.answer?.length > 80 ? '...' : ''}`);
        console.log('');
    });
    
    console.log('═════════════════ 质量评分 ═════════════════\n');
    
    let score = 0;
    const details = [];
    
    if (confirmed.length >= 200) { score += 20; details.push('数据量充足 (+20)'); }
    else if (confirmed.length >= 100) { score += 15; details.push('数据量良好 (+15)'); }
    else if (confirmed.length >= 50) { score += 10; details.push('数据量一般 (+10)'); }
    else { score += 5; details.push('数据量较少 (+5)'); }
    
    if (avgQ >= 30 && avgA >= 80) { score += 25; details.push('内容丰富度优秀 (+25)'); }
    else if (avgQ >= 15 && avgA >= 40) { score += 18; details.push('内容丰富度良好 (+18)'); }
    else if (avgQ >= 8 && avgA >= 20) { score += 10; details.push('内容丰富度一般 (+10)'); }
    else { score += 5; details.push('内容丰富度较低 (+5)'); }
    
    const shortRatio = shortA / confirmed.length;
    if (shortRatio < 0.05) { score += 20; details.push('数据一致性优秀 (+20)'); }
    else if (shortRatio < 0.1) { score += 15; details.push('数据一致性良好 (+15)'); }
    else if (shortRatio < 0.2) { score += 10; details.push('数据一致性一般 (+10)'); }
    else { score += 5; details.push('数据一致性较低 (+5)'); }
    
    const confirmRate = confirmed.length / allData.length;
    if (confirmRate >= 0.8) { score += 20; details.push('有效率优秀 (+20)'); }
    else if (confirmRate >= 0.6) { score += 15; details.push('有效率良好 (+15)'); }
    else if (confirmRate >= 0.4) { score += 10; details.push('有效率一般 (+10)'); }
    else { score += 5; details.push('有效率较低 (+5)'); }
    
    details.forEach(d => console.log(`   ${d}`));
    
    console.log(`\n   📊 总分: ${score}/85 分`);
    
    let rating, emoji;
    if (score >= 70) { rating = '优秀'; emoji = '⭐⭐⭐⭐⭐'; }
    else if (score >= 55) { rating = '良好'; emoji = '⭐⭐⭐⭐'; }
    else if (score >= 40) { rating = '一般'; emoji = '⭐⭐⭐'; }
    else { rating = '较差'; emoji = '⭐⭐'; }
    
    console.log(`   ${emoji} 评级: ${rating}`);
    
    console.log('\n═════════════════ 建议 ═════════════════\n');
    
    if (shortRatio > 0.1) {
        console.log('   ⚠️ 存在较多短回答，建议进一步筛选');
    }
    if (avgQ < 15) {
        console.log('   ⚠️ 问题平均长度较短，可能影响微调效果');
    }
    if (unconfirmed.length > 50) {
        console.log(`   💡 还有 ${unconfirmed.length} 条数据待确认，可在Easy Dataset UI中手动处理`);
    }
    if (score >= 55) {
        console.log('   ✅ 数据质量良好，适合用于模型微调');
    }
    
    console.log('\n🌐 访问 http://localhost:1717 查看详细数据');
    console.log('\n' + '═'.repeat(50));
}

main().catch(console.error);
