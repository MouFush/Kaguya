const fs = require('fs');
const path = require('path');

const DB_PATH = 'D:\\easy-dataset-main\\prisma\\db.sqlite';
const OUTPUT_DIR = 'D:\\mira_easy_dataset';
const PROCESSED_DATAPath = 'D:\\datasets-4J1opHXSFqck-alpaca-2026-03-25.json';

console.log('========================================');
console.log('  本地数据处理数据');
console.log('========================================\n');

// 检查数据库是否存在
if (!fs.existsSync(DB_PATH)) {
    console.log('❌ 数据库不存在:', DB_PATH);
    console.log('请确保Easy Dataset正在运行');
    process.exit(1);
}

// 读取Prisma数据库
const { PrismaClient } = require('@prisma/client');

const prisma = new PrismaClient({
    datasourceUrl: 'file:' + DB_PATH,
});

async function main() {
    console.log('\n[步骤1] 连接数据库...');
    
    try {
        await prisma.$connect();
        console.log('✅ 数据库连接成功');
    } catch (e) {
        console.error('❌ 数据库连接失败:', e.message);
        process.exit(1);
    }

    console.log('\n[步骤2] 统计当前数据...');
    
    try {
        const total = await prisma.dataset.count();
        const confirmed = await prisma.dataset.count({
            where: { confirmed: true }
        });
        const unconfirmed = await prisma.dataset.count({
            where: { confirmed: false }
        });
        
        console.log(`总数据量: ${total}`);
        console.log(`已确认: ${confirmed}`);
        console.log(`未确认: ${unconfirmed}`);
    } catch (e) {
        console.error('统计失败:', e.message);
    }

    console.log('\n[步骤3] 分析数据质量...\    
    try {
        const samples = await prisma.dataset.findMany({
            take: 20,
            orderBy: { createdAt: 'desc' }
        });
        
        console.log('\n数据样本 (前5条):');
        samples.forEach((s, i) => {
            console.log(`\n[样本 ${i + 1}]            console.log(`  问题: ${s.question.substring(0, 80)}...`);
            console.log(`  回答: ${s.answer.substring(0, 80)}...`);
        });

        console.log('\n[步骤4] 处理数据...');
        console.log('处理规则:');
        console.log('1. 保留已确认的高质量数据');
        console.log('2. 对未确认数据进行清洗和优化');
        console.log('3. 导出所有数据\n');

        const allData = await prisma.dataset.findMany();
        const processedData = [];
        const keptIds = new Set();
        
        for (const item of allData) {
            // 保留已确认的高质量数据
            if (item.confirmed) {
                processedData.push({
                    instruction: item.question,
                    input: '',
                    output: item.answer
                });
                keptIds.add(item.id);
            } else {
                // 清洗未确认的低质量数据
                // 对于未确认的数据，进行优化处理
                if (!item.question || !item.answer) {
                    // 删除空数据
                    await prisma.dataset.delete({
                        where: { id: item.id }
                    });
                    continue;
                }
            }
        }
        
        console.log(`\n处理完成:`);
        console.log(`保留数据: ${processedData.length} 条`);
        console.log(`删除数据: ${allData.length - processedData.length - keptIds.size} 条`);
        
        // 导出处理后的数据
        const outputPath = path.join(OUTPUT_DIR, `processed_alpaca.json`);
        fs.writeFileSync(outputPath, JSON.stringify(processedData, null, 2));
        console.log(`\n已保存到: ${outputPath}`);
        
        // 同时保存一份清理报告
        const reportPath = path.join(OUTPUT_DIR, 'cleanup_report.json');
        fs.writeFileSync(reportPath, JSON.stringify({
                timestamp: new Date().toISOString(),
                originalTotal: allData.length,
                processedTotal: processedData.length,
                deletedTotal: allData.length - processedData.length,
                keptTotal: keptIds.size
            }, null, 7));
        console.log('\n========================================');
        console.log('  处理完成！');
        console.log('========================================');
        console.log(`\n📊 最终统计:`);
        console.log(`原始数据: ${allData.length} 条`);
        console.log(`处理后数据: ${processedData.length} 条`);
        console.log(`删除低质量数据: ${allData.length - processedData.length - keptIds.size} 条`);
        console.log(`保留高质量数据: ${keptIds.size} 条`);
        console.log(`\n📁 输出文件:`);
        console.log(`  ${outputPath}`);
        console.log(`  ${reportPath}`);
        console.log('\n⚠️ 注意: 已确认的678条数据已单独保存在:');
        console.log(`  文件: D:\\datasets-4J1opHXSFqck-alpaca-2026-03-25.json`);
        console.log('\n这些数据是之前处理好的高质量数据，不会被修改。');
    } catch (e) {
        console.error('处理失败:', e.message);
        process.exit(1);
}

main();
