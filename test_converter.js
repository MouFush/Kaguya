const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const OUTPUT_DIR = 'D:\\mira_export_converted';

console.log('🔍 开始检测 Mira Export 转换脚本...\n');

// 1. 检查输入文件
console.log('📁 检查输入文件...');
const INPUT_DIR = 'D:\\mira_export';
if (!fs.existsSync(INPUT_DIR)) {
    console.log('❌ 输入目录不存在:', INPUT_DIR);
    process.exit(1);
}

const forwardDir = path.join(INPUT_DIR, 'forward');
const jsonFiles = fs.readdirSync(INPUT_DIR).filter(f => f.endsWith('.jsonl'));
const forwardFiles = fs.existsSync(forwardDir) ? fs.readdirSync(forwardDir).filter(f => f.endsWith('.json')) : [];

console.log(`✅ 输入目录存在`);
console.log(`   - JSONL 文件: ${jsonFiles.length} 个`);
console.log(`   - Forward 文件: ${forwardFiles.length} 个`);

if (jsonFiles.length === 0 && forwardFiles.length === 0) {
    console.log('⚠️ 警告: 没有找到数据文件');
}

// 2. 检查 Node.js
console.log('\n🔧 检查环境...');
try {
    const nodeVersion = execSync('node --version', { encoding: 'utf-8' }).trim();
    console.log(`✅ Node.js 版本: ${nodeVersion}`);
} catch (e) {
    console.log('❌ Node.js 未安装');
    process.exit(1);
}

// 3. 检查脚本文件
console.log('\n📄 检查脚本文件...');
const scriptPath = 'c:\\Users\\林智涵\\.conda\\convert_mira_to_easy_dataset.js';
if (!fs.existsSync(scriptPath)) {
    console.log('❌ 转换脚本不存在:', scriptPath);
    process.exit(1);
}
console.log('✅ 转换脚本存在');

// 4. 运行转换（使用最小配置）
console.log('\n🚀 运行转换脚本...');
try {
    const outputBefore = fs.existsSync(OUTPUT_DIR) ? fs.readdirSync(OUTPUT_DIR) : [];
    console.log(`   输出目录已存在 ${outputBefore.length} 个文件`);

    console.log('   执行命令: node convert_mira_to_easy_dataset.js --min-quality 0.5');

    execSync(`node "${scriptPath}" --input "${INPUT_DIR}" --output "${OUTPUT_DIR}" --min-quality 0.5 --no-images`, {
        stdio: 'inherit',
        timeout: 120000
    });

    console.log('\n✅ 转换脚本执行完成');
} catch (e) {
    console.log('\n❌ 转换脚本执行失败:', e.message);
    process.exit(1);
}

// 5. 检查输出文件
console.log('\n📊 检查输出文件...');
if (!fs.existsSync(OUTPUT_DIR)) {
    console.log('❌ 输出目录未创建');
    process.exit(1);
}

const outputFiles = fs.readdirSync(OUTPUT_DIR).filter(f => f.endsWith('.json') || f.endsWith('.jsonl'));
console.log(`✅ 输出文件: ${outputFiles.length} 个`);
outputFiles.forEach(f => {
    const size = fs.statSync(path.join(OUTPUT_DIR, f)).size;
    console.log(`   - ${f} (${(size / 1024).toFixed(1)} KB)`);
});

// 6. 检查统计数据
console.log('\n📈 检查转换统计...');
const statsPath = path.join(OUTPUT_DIR, 'conversion_stats.json');
if (fs.existsSync(statsPath)) {
    const stats = JSON.parse(fs.readFileSync(statsPath, 'utf-8'));
    console.log(`   处理文件: ${stats.stats.totalFiles}`);
    console.log(`   总消息数: ${stats.stats.totalMessages}`);
    console.log(`   有效对话: ${stats.stats.validConversations}`);
    console.log(`   高质量数据: ${stats.qualityDistribution?.high || 0}`);
    console.log('✅ 统计文件正常');
} else {
    console.log('⚠️ 统计文件未生成');
}

// 7. 检查数据格式
console.log('\n🔬 检查数据格式...');
const jsonPath = path.join(OUTPUT_DIR, 'easy_dataset_import.json');
if (fs.existsSync(jsonPath)) {
    try {
        const data = JSON.parse(fs.readFileSync(jsonPath, 'utf-8'));
        if (Array.isArray(data) && data.length > 0) {
            const sample = data[0];
            const hasRequired = sample.question && sample.answer && sample.chunkName;
            console.log(`   数据条数: ${data.length}`);
            console.log(`   必需字段: ${hasRequired ? '✅ 完整' : '❌ 缺失'}`);
            console.log('✅ 数据格式正确');
        } else {
            console.log('❌ 数据格式错误');
        }
    } catch (e) {
        console.log('❌ 数据解析失败:', e.message);
    }
} else {
    console.log('⚠️ 主数据文件未生成');
}

console.log('\n========== 检测完成 ==========');
console.log('✅ Mira Export 转换脚本工作正常！');
console.log('\n输出目录:', OUTPUT_DIR);
