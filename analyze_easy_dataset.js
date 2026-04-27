const http = require('http');
const fs = require('fs');

const CONFIG = {
    HOST: 'localhost',
    PORT: 1717,
    PROJECT_ID: '4J1opHXSFqck'
};

function getDatasets(skip = 0, take = 100) {
    return new Promise((resolve, reject) => {
        const options = {
            hostname: CONFIG.HOST,
            port: CONFIG.PORT,
            path: `/api/projects/${CONFIG.PROJECT_ID}/datasets?skip=${skip}&take=${take}`,
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

function analyzeDataQuality(datasets) {
    const stats = {
        total: datasets.length,
        hasQuestion: 0,
        hasAnswer: 0,
        hasBoth: 0,
        emptyQuestion: 0,
        emptyAnswer: 0,
        shortQuestion: 0,
        shortAnswer: 0,
        avgQuestionLen: 0,
        avgAnswerLen: 0,
        confirmed: 0,
        unconfirmed: 0,
        samples: []
    };

    let totalQLen = 0;
    let totalALen = 0;

    datasets.forEach(d => {
        const q = d.question || '';
        const a = d.answer || '';

        if (q) stats.hasQuestion++;
        if (a) stats.hasAnswer++;
        if (q && a) stats.hasBoth++;
        if (!q || q.trim().length < 5) stats.emptyQuestion++;
        if (!a || a.trim().length < 5) stats.emptyAnswer++;
        if (q.length < 10) stats.shortQuestion++;
        if (a.length < 10) stats.shortAnswer++;

        totalQLen += q.length;
        totalALen += a.length;

        if (d.confirmed) stats.confirmed++;
        else stats.unconfirmed++;
    });

    stats.avgQuestionLen = Math.round(totalQLen / stats.total);
    stats.avgAnswerLen = Math.round(totalALen / stats.total);

    // 获取样本
    stats.samples = datasets.slice(0, 10).map(d => ({
        question: (d.question || '').substring(0, 100),
        answer: (d.answer || '').substring(0, 100),
        confirmed: d.confirmed
    }));

    return stats;
}

async function main() {
    console.log('========================================');
    console.log('  Easy Dataset 数据质量分析');
    console.log('========================================\n');

    console.log('[1] 获取数据样本...\n');

    // 获取多批次数据进行分析
    let allData = [];
    for (let i = 0; i < 10; i++) {
        try {
            const result = await getDatasets(i * 100, 100);
            if (result.data && result.data.length > 0) {
                allData = allData.concat(result.data);
            } else if (Array.isArray(result) && result.length > 0) {
                allData = allData.concat(result);
            } else {
                break;
            }
        } catch (e) {
            console.log(`获取第${i+1}批数据失败: ${e.message}`);
            break;
        }
    }

    console.log(`获取到 ${allData.length} 条数据\n`);

    console.log('[2] 分析数据质量...\n');

    const stats = analyzeDataQuality(allData);

    console.log('=== 数据统计 ===');
    console.log(`总数据量: ${stats.total}`);
    console.log(`已确认: ${stats.confirmed} (${Math.round(stats.confirmed/stats.total*100)}%)`);
    console.log(`未确认: ${stats.unconfirmed} (${Math.round(stats.unconfirmed/stats.total*100)}%)`);
    console.log('');
    console.log(`有问题: ${stats.hasQuestion} (${Math.round(stats.hasQuestion/stats.total*100)}%)`);
    console.log(`有回答: ${stats.hasAnswer} (${Math.round(stats.hasAnswer/stats.total*100)}%)`);
    console.log(`问答完整: ${stats.hasBoth} (${Math.round(stats.hasBoth/stats.total*100)}%)`);
    console.log('');
    console.log(`问题为空/过短: ${stats.emptyQuestion} (${Math.round(stats.emptyQuestion/stats.total*100)}%)`);
    console.log(`回答为空/过短: ${stats.emptyAnswer} (${Math.round(stats.emptyAnswer/stats.total*100)}%)`);
    console.log('');
    console.log(`平均问题长度: ${stats.avgQuestionLen} 字符`);
    console.log(`平均回答长度: ${stats.avgAnswerLen} 字符`);

    console.log('\n=== 数据样本 ===\n');
    stats.samples.forEach((s, i) => {
        console.log(`[样本 ${i+1}] ${s.confirmed ? '✅' : '⏳'}`);
        console.log(`  问: ${s.question}${s.question.length >= 100 ? '...' : ''}`);
        console.log(`  答: ${s.answer}${s.answer.length >= 100 ? '...' : ''}`);
        console.log('');
    });

    // 质量评估
    console.log('=== 质量评估 ===\n');

    const qualityScore = calculateQualityScore(stats);
    console.log(`质量评分: ${qualityScore.score}/100`);
    console.log(`评级: ${qualityScore.grade}`);
    console.log('');
    console.log('评估详情:');
    qualityScore.details.forEach(d => {
        console.log(`  ${d.icon} ${d.item}: ${d.value} - ${d.status}`);
    });

    console.log('\n=== 建议 ===\n');
    qualityScore.suggestions.forEach(s => {
        console.log(`  • ${s}`);
    });

    // 保存分析结果
    const report = {
        timestamp: new Date().toISOString(),
        stats: stats,
        quality: qualityScore
    };
    fs.writeFileSync('D:\\mira_easy_dataset\\quality_report.json', JSON.stringify(report, null, 2));
    console.log('\n报告已保存到: D:\\mira_easy_dataset\\quality_report.json');
}

function calculateQualityScore(stats) {
    let score = 0;
    const details = [];

    // 完整性 (30分)
    const completeness = Math.round(stats.hasBoth / stats.total * 30);
    score += completeness;
    details.push({
        icon: stats.hasBoth / stats.total > 0.9 ? '✅' : '⚠️',
        item: '数据完整性',
        value: `${Math.round(stats.hasBoth / stats.total * 100)}%`,
        status: stats.hasBoth / stats.total > 0.9 ? '优秀' : '需改进'
    });

    // 内容质量 (30分)
    const contentQuality = Math.round((1 - stats.emptyAnswer / stats.total) * 30);
    score += contentQuality;
    details.push({
        icon: stats.emptyAnswer / stats.total < 0.1 ? '✅' : '⚠️',
        item: '内容质量',
        value: `${Math.round((1 - stats.emptyAnswer / stats.total) * 100)}%`,
        status: stats.emptyAnswer / stats.total < 0.1 ? '优秀' : '需改进'
    });

    // 长度适中 (20分)
    const avgLen = (stats.avgQuestionLen + stats.avgAnswerLen) / 2;
    const lenScore = avgLen > 50 && avgLen < 500 ? 20 : (avgLen > 20 ? 15 : 10);
    score += lenScore;
    details.push({
        icon: lenScore >= 15 ? '✅' : '⚠️',
        item: '内容长度',
        value: `平均${avgLen}字符`,
        status: lenScore >= 15 ? '适中' : '偏短'
    });

    // 确认状态 (20分)
    const confirmScore = Math.round(stats.confirmed / stats.total * 20);
    score += confirmScore;
    details.push({
        icon: stats.confirmed / stats.total > 0.5 ? '✅' : '⏳',
        item: '确认状态',
        value: `${Math.round(stats.confirmed / stats.total * 100)}%`,
        status: stats.confirmed / stats.total > 0.5 ? '已审核' : '待审核'
    });

    let grade = 'D';
    if (score >= 90) grade = 'A';
    else if (score >= 80) grade = 'B';
    else if (score >= 70) grade = 'C';

    const suggestions = [];
    if (stats.emptyAnswer / stats.total > 0.1) {
        suggestions.push('部分数据缺少回答，建议进行蒸馏补充');
    }
    if (stats.confirmed / stats.total < 0.5) {
        suggestions.push('大部分数据未确认，建议审核或蒸馏');
    }
    if (avgLen < 50) {
        suggestions.push('内容较短，建议蒸馏扩展内容');
    }
    if (score >= 80) {
        suggestions.push('数据质量良好，可直接用于微调');
    }
    if (stats.unconfirmed > 1000) {
        suggestions.push('大量数据待处理，建议批量蒸馏');
    }

    return { score, grade, details, suggestions };
}

main().catch(console.error);
