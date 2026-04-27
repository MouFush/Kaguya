const fs = require('fs');
const path = require('path');

const INPUT_IMAGES = 'D:\\mira_export\\images';
const OUTPUT_DIR = 'D:\\mira_export_images_dataset';
const OUTPUT_IMAGES = path.join(OUTPUT_DIR, 'images');

console.log('🔄 处理图片数据...\n');

if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
    fs.mkdirSync(OUTPUT_IMAGES, { recursive: true });
}

const imageFiles = fs.readdirSync(INPUT_IMAGES).filter(f =>
    f.endsWith('.jpg') || f.endsWith('.png') || f.endsWith('.gif') || f.endsWith('.webp')
);

console.log(`📷 发现 ${imageFiles.length} 张图片\n`);

const datasets = [];
let copied = 0;

for (let i = 0; i < imageFiles.length; i++) {
    const filename = imageFiles[i];
    const srcPath = path.join(INPUT_IMAGES, filename);
    const destFilename = `image_${String(i + 1).padStart(5, '0')}_${filename}`;
    const destPath = path.join(OUTPUT_IMAGES, destFilename);

    fs.copyFileSync(srcPath, destPath);

    const stats = fs.statSync(destPath);

    datasets.push({
        question: `[图片描述任务] 请描述这张图片的内容、场景、人物、动作等。`,
        answer: `[待生成图片描述]`,
        chunkName: `image_${i + 1}`,
        chunkContent: `图片文件: ${destFilename}`,
        model: 'chat_export',
        questionLabel: 'image_description',
        tags: JSON.stringify(['图片', '待描述']),
        note: `来源: ${filename}`,
        confirmed: false,
        score: 0,
        images: [`images/${destFilename}`],
        metadata: {
            originalFilename: filename,
            fileSize: stats.size,
            messageCount: 0,
            userCount: 0,
            hasImages: true
        }
    });

    copied++;
    if (copied % 500 === 0) {
        console.log(`已处理 ${copied}/${imageFiles.length} 张图片...`);
    }
}

const jsonPath = path.join(OUTPUT_DIR, 'easy_dataset_import.json');
fs.writeFileSync(jsonPath, JSON.stringify(datasets, null, 2), 'utf-8');

const statsJson = {
    totalImages: copied,
    outputDir: OUTPUT_DIR,
    imagesDir: OUTPUT_IMAGES,
    generatedAt: new Date().toISOString()
};

fs.writeFileSync(
    path.join(OUTPUT_DIR, 'image_stats.json'),
    JSON.stringify(statsJson, null, 2),
    'utf-8'
);

console.log('\n========== 处理完成 ==========');
console.log(`✅ 已复制 ${copied} 张图片到:`);
console.log(`   ${OUTPUT_IMAGES}`);
console.log(`\n✅ 已生成数据集文件:`);
console.log(`   ${jsonPath}`);
console.log(`\n💡 导入 Easy Dataset 后，可以使用图片描述功能生成每张图片的描述。`);
