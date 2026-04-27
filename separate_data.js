const fs = require('fs');
const path = require('path');

const INPUT_DIR = 'D:\\mira_export_clean\\easy_dataset_import.json';
const OUTPUT_TEXT = 'D:\\mira_export_text_only.json';

console.log('📊 分离文本和图片数据...\n');

const allData = JSON.parse(fs.readFileSync(INPUT_DIR, 'utf-8'));
console.log('总数据:', allData.length);

const textOnly = allData.filter(d => !d.images || d.images.length === 0);
const withImages = allData.filter(d => d.images && d.images.length > 0);

console.log('纯文本数据:', textOnly.length);
console.log('含图片数据:', withImages.length);

fs.writeFileSync(OUTPUT_TEXT, JSON.stringify(textOnly, null, 2), 'utf-8');
console.log('\n✅ 已保存纯文本数据到:', OUTPUT_TEXT);
