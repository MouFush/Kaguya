const http = require('http');

const PROJECT_ID = '4J1opHXSFqck';
const BASE_URL = 'localhost';
const PORT = 1717;

function fetch(path) {
    return new Promise((resolve, reject) => {
        const options = {
            hostname: BASE_URL,
            port: PORT,
            path: path,
            method: 'GET',
            headers: { 'Content-Type': 'application/json' }
        };

        const req = http.request(options, (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => {
                try {
                    resolve(JSON.parse(data));
                } catch (e) {
                    reject(e);
                }
            });
        });
        req.on('error', reject);
        req.end();
    });
}

async function checkQuality() {
    console.log('=== 数据集质量检查报告 ===\n');
    
    const confirmed = await fetch(`/api/projects/${PROJECT_ID}/datasets?confirmed=true&page=1&pageSize=1000`);
    const unconfirmed = await fetch(`/api/projects/${PROJECT_ID}/datasets?confirmed=false&page=1&pageSize=1000`);
    
    const confirmedData = confirmed.data || [];
    const unconfirmedData = unconfirmed.data || [];
    
    console.log(`✅ 已确认有效数据: ${confirmedData.length} 条`);
    console.log(`❌ 待确认/无效数据: ${unconfirmedData.length} 条`);
    console.log(`📊 总数据量: ${confirmedData.length + unconfirmedData.length} 条`);
    console.log(`📈 有效率: ${((confirmedData.length / (confirmedData.length + unconfirmedData.length)) * 100).toFixed(1)}%\n`);
    
    if (confirmedData.length > 0) {
        console.log('=== 有效数据样本展示 ===\n');
        
        const samples = confirmedData.slice(0, 5);
        samples.forEach((item, i) => {
            console.log(`【样本 ${i + 1}】`);
            console.log(`问题 (${item.question?.length || 0}字): ${item.question?.substring(0, 80)}${item.question?.length > 80 ? '...' : ''}`);
            console.log(`回答 (${item.answer?.length || 0}字): ${item.answer?.substring(0, 120)}${item.answer?.length > 120 ? '...' : ''}`);
            console.log('');
        });
        
        console.log('=== 数据质量分析 ===\n');
        
        const questionLengths = confirmedData.map(d => d.question?.length || 0);
        const answerLengths = confirmedData.map(d => d.answer?.length || 0);
        
        const avgQ = (questionLengths.reduce((a, b) => a + b, 0) / questionLengths.length).toFixed(1);
        const avgA = (answerLengths.reduce((a, b) => a + b, 0) / answerLengths.length).toFixed(1);
        const maxQ = Math.max(...questionLengths);
        const maxA = Math.max(...answerLengths);
        const minQ = Math.min(...questionLengths);
        const minA = Math.min(...answerLengths);
        
        console.log(`问题长度统计:`);
        console.log(`  - 平均: ${avgQ} 字`);
        console.log(`  - 最短: ${minQ} 字`);
        console.log(`  - 最长: ${maxQ} 字`);
        console.log(`\n回答长度统计:`);
        console.log(`  - 平均: ${avgA} 字`);
        console.log(`  - 最短: ${minA} 字`);
        console.log(`  - 最长: ${maxA} 字`);
        
        const shortAnswers = confirmedData.filter(d => (d.answer?.length || 0) < 20).length;
        const shortQuestions = confirmedData.filter(d => (d.question?.length || 0) < 10).length;
        
        console.log(`\n⚠️ 潜在问题:`);
        console.log(`  - 回答过短(<20字): ${shortAnswers} 条 (${(shortAnswers/confirmedData.length*100).toFixed(1)}%)`);
        console.log(`  - 问题过短(<10字): ${shortQuestions} 条 (${(shortQuestions/confirmedData.length*100).toFixed(1)}%)`);
        
        console.log('\n=== 质量评估 ===');
        let score = 0;
        if (confirmedData.length >= 200) score += 25;
        else if (confirmedData.length >= 100) score += 15;
        else score += 5;
        
        if (parseFloat(avgQ) >= 20 && parseFloat(avgA) >= 50) score += 25;
        else if (parseFloat(avgQ) >= 10 && parseFloat(avgA) >= 30) score += 15;
        else score += 5;
        
        if (shortAnswers / confirmedData.length < 0.1) score += 25;
        else if (shortAnswers / confirmedData.length < 0.2) score += 15;
        else score += 5;
        
        if (confirmedData.length / (confirmedData.length + unconfirmedData.length) > 0.7) score += 25;
        else if (confirmedData.length / (confirmedData.length + unconfirmedData.length) > 0.5) score += 15;
        else score += 5;
        
        console.log(`\n总体质量评分: ${score}/100 分`);
        
        if (score >= 80) console.log('评级: ⭐⭐⭐⭐⭐ 优秀 - 数据质量很高，适合微调');
        else if (score >= 60) console.log('评级: ⭐⭐⭐⭐ 良好 - 数据质量较好，可以用于微调');
        else if (score >= 40) console.log('评级: ⭐⭐⭐ 一般 - 数据质量一般，建议进一步筛选');
        else console.log('评级: ⭐⭐ 较差 - 数据质量较低，需要重新处理');
    }
}

checkQuality().catch(console.error);
