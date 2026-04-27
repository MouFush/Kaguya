const fs = require('fs');
const path = require('path');
const https = require('https');
const http = require('http');

const CONFIG = {
    INPUT_DIR: 'D:\\mira_export',
    OUTPUT_DIR: 'D:\\mira_export_converted',
    EASY_DATASET_URL: 'http://localhost:1717',
    MIN_CONVERSATION_LENGTH: 3,
    MAX_CONVERSATION_LENGTH: 50,
    MIN_TEXT_LENGTH: 5,
    MAX_TEXT_LENGTH: 4000,
    TIME_GAP_THRESHOLD: 600,
    QUALITY_THRESHOLD: 0.3,
    COPY_IMAGES: true,
    DIRECT_IMPORT: false,
    PROJECT_ID: null,
    USE_API: false,
    API_CONFIG: {
        provider: 'openai',
        apiKey: '',
        baseUrl: '',
        model: 'gpt-4o-mini',
        visionModel: 'gpt-4o-mini'
    },
    PROCESS_IMAGES: false
};

const STATS = {
    totalFiles: 0,
    processedFiles: 0,
    totalMessages: 0,
    validConversations: 0,
    skippedShort: 0,
    skippedLowQuality: 0,
    imagesCopied: 0,
    imagesProcessed: 0,
    apiCalls: 0,
    errors: []
};

const API_PROVIDERS = {
    openai: { baseUrl: 'https://api.openai.com/v1', visionSupport: true },
    deepseek: { baseUrl: 'https://api.deepseek.com/v1', visionSupport: false },
    zhipu: { baseUrl: 'https://open.bigmodel.cn/api/paas/v4', visionSupport: true },
    qwen: { baseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1', visionSupport: true },
    ollama: { baseUrl: 'http://localhost:11434/v1', visionSupport: true },
    custom: { baseUrl: '', visionSupport: true }
};

function ensureDir(dir) {
    if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
    }
}

async function callLLMAPI(messages, options = {}) {
    if (!CONFIG.USE_API || !CONFIG.API_CONFIG.apiKey) {
        return null;
    }
    
    const provider = API_PROVIDERS[CONFIG.API_CONFIG.provider] || API_PROVIDERS.openai;
    const baseUrl = CONFIG.API_CONFIG.baseUrl || provider.baseUrl;
    const model = options.model || CONFIG.API_CONFIG.model;
    
    return new Promise((resolve, reject) => {
        const postData = JSON.stringify({
            model: model,
            messages: messages,
            max_tokens: options.maxTokens || 1000,
            temperature: options.temperature || 0.7
        });
        
        const url = new URL(baseUrl);
        const requestOptions = {
            hostname: url.hostname,
            port: url.port || (url.protocol === 'https:' ? 443 : 80),
            path: '/chat/completions',
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${CONFIG.API_CONFIG.apiKey}`,
                'Content-Length': Buffer.byteLength(postData)
            }
        };
        
        const client = url.protocol === 'https:' ? https : http;
        
        const req = client.request(requestOptions, (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => {
                try {
                    const result = JSON.parse(data);
                    if (result.choices && result.choices[0]) {
                        STATS.apiCalls++;
                        resolve(result.choices[0].message.content);
                    } else {
                        reject(new Error('Invalid API response'));
                    }
                } catch (e) {
                    reject(e);
                }
            });
        });
        
        req.on('error', reject);
        req.setTimeout(30000, () => {
            req.destroy();
            reject(new Error('API timeout'));
        });
        req.write(postData);
        req.end();
    });
}

async function describeImage(imagePath) {
    if (!CONFIG.USE_API || !CONFIG.PROCESS_IMAGES) {
        return null;
    }
    
    try {
        const imageBuffer = fs.readFileSync(imagePath);
        const base64Image = imageBuffer.toString('base64');
        const ext = path.extname(imagePath).toLowerCase().replace('.', '');
        const mimeType = ext === 'jpg' ? 'jpeg' : ext;
        
        const messages = [
            {
                role: 'user',
                content: [
                    {
                        type: 'text',
                        text: '请详细描述这张图片的内容。如果是聊天截图，请提取其中的文字内容；如果是表情包，描述表情的含义；如果是其他图片，描述主要元素、场景、人物等。用简洁的中文回答。'
                    },
                    {
                        type: 'image_url',
                        image_url: {
                            url: `data:image/${mimeType};base64,${base64Image}`
                        }
                    }
                ]
            }
        ];
        
        const description = await callLLMAPI(messages, {
            model: CONFIG.API_CONFIG.visionModel,
            maxTokens: 500
        });
        
        STATS.imagesProcessed++;
        return description;
    } catch (error) {
        STATS.errors.push(`图片描述失败 ${imagePath}: ${error.message}`);
        return null;
    }
}

async function enhanceConversation(conversationText) {
    if (!CONFIG.USE_API) {
        return null;
    }
    
    try {
        const messages = [
            {
                role: 'system',
                content: '你是一个数据清洗专家。请分析以下聊天记录，提取有价值的信息，生成一个简洁的摘要和关键话题。'
            },
            {
                role: 'user',
                content: `请分析以下聊天记录，提供：\n1. 话题摘要（一句话）\n2. 关键信息点\n3. 情感倾向\n\n聊天记录：\n${conversationText.substring(0, 2000)}`
            }
        ];
        
        return await callLLMAPI(messages, { maxTokens: 500 });
    } catch (error) {
        return null;
    }
}

async function generateQAFromConversation(conversationText) {
    if (!CONFIG.USE_API) {
        return null;
    }
    
    try {
        const messages = [
            {
                role: 'system',
                content: '你是一个数据标注专家。请从聊天记录中提取或生成高质量的问答对，用于训练AI助手。'
            },
            {
                role: 'user',
                content: `请从以下聊天记录中提取或生成1-3个高质量的问答对。格式为JSON数组：[{"question": "...", "answer": "..."}]\n\n聊天记录：\n${conversationText.substring(0, 2000)}`
            }
        ];
        
        const response = await callLLMAPI(messages, { maxTokens: 1000 });
        
        try {
            const qaPairs = JSON.parse(response);
            return Array.isArray(qaPairs) ? qaPairs : null;
        } catch {
            return null;
        }
    } catch (error) {
        return null;
    }
}

function extractTextFromContext(context) {
    if (!Array.isArray(context)) return { text: '', images: [] };
    
    const textParts = [];
    const images = [];
    
    for (const item of context) {
        if (item.type === 'text' && item.value) {
            textParts.push(item.value);
        } else if (item.type === 'image' && item.value) {
            images.push({
                path: item.value,
                url: item.url,
                fileSize: item.file_size
            });
        }
    }
    
    return { text: textParts.join(' '), images };
}

function cleanText(text) {
    if (!text) return '';
    
    let cleaned = text
        .replace(/\s+/g, ' ')
        .replace(/[\u200B-\u200D\uFEFF]/g, '')
        .replace(/[\u0000-\u001F\u007F-\u009F]/g, '')
        .trim();
    
    return cleaned;
}

function isHighQualityMessage(text) {
    if (!text || text.length < CONFIG.MIN_TEXT_LENGTH) return false;
    if (text.length > CONFIG.MAX_TEXT_LENGTH) return false;
    
    const chineseRatio = (text.match(/[\u4e00-\u9fa5]/g) || []).length / text.length;
    const letterRatio = (text.match(/[a-zA-Z]/g) || []).length / text.length;
    
    if (chineseRatio < 0.1 && letterRatio < 0.1) return false;
    
    const junkPatterns = [
        /^[.\s,，。！!?？]+$/,
        /^[\d\s]+$/,
        /^https?:\/\//,
        /^\[.*\]$/,
        /^图片$|^表情$|^语音$|^视频$/,
    ];
    
    for (const pattern of junkPatterns) {
        if (pattern.test(text)) return false;
    }
    
    return true;
}

function calculateQualityScore(conversation) {
    let score = 1.0;
    
    const textLength = conversation.text.length;
    if (textLength < 50) score *= 0.5;
    else if (textLength < 100) score *= 0.7;
    else if (textLength > 2000) score *= 0.8;
    
    const messageCount = conversation.messages.length;
    if (messageCount < 4) score *= 0.6;
    else if (messageCount >= 6 && messageCount <= 15) score *= 1.1;
    
    const uniqueUsers = new Set(conversation.messages.map(m => m.user)).size;
    if (uniqueUsers < 2) score *= 0.3;
    else if (uniqueUsers >= 2 && uniqueUsers <= 4) score *= 1.1;
    
    const avgLength = textLength / messageCount;
    if (avgLength < 10) score *= 0.5;
    else if (avgLength > 200) score *= 0.8;
    
    if (conversation.hasImages) score *= 1.2;
    
    return Math.min(1.0, Math.max(0.0, score));
}

function smartSplitConversation(messages) {
    if (messages.length === 0) return [];
    
    const conversations = [];
    let currentConversation = [];
    let lastTime = 0;
    let currentUser = null;
    let consecutiveCount = 0;
    
    for (const msg of messages) {
        const timeDiff = msg.time - lastTime;
        const userChanged = currentUser !== null && currentUser !== msg.user;
        
        if (currentConversation.length > 0) {
            if (timeDiff > CONFIG.TIME_GAP_THRESHOLD) {
                if (currentConversation.length >= CONFIG.MIN_CONVERSATION_LENGTH) {
                    conversations.push([...currentConversation]);
                }
                currentConversation = [];
                consecutiveCount = 0;
            } else if (userChanged) {
                consecutiveCount = 0;
            } else {
                consecutiveCount++;
                if (consecutiveCount > 5 && currentConversation.length >= CONFIG.MIN_CONVERSATION_LENGTH) {
                    conversations.push([...currentConversation]);
                    currentConversation = [];
                    consecutiveCount = 0;
                }
            }
        }
        
        currentConversation.push(msg);
        lastTime = msg.time;
        currentUser = msg.user;
        
        if (currentConversation.length >= CONFIG.MAX_CONVERSATION_LENGTH) {
            conversations.push([...currentConversation]);
            currentConversation = [];
            consecutiveCount = 0;
        }
    }
    
    if (currentConversation.length >= CONFIG.MIN_CONVERSATION_LENGTH) {
        conversations.push(currentConversation);
    }
    
    return conversations;
}

function copyImage(imageInfo, imagesDir, sourceFile) {
    if (!imageInfo.path && !imageInfo.url) return null;
    
    try {
        const sourceDir = path.dirname(sourceFile);
        let imagePath = imageInfo.path;
        
        if (imagePath.startsWith('./')) {
            imagePath = path.resolve(sourceDir, '..', imagePath);
        }
        
        if (fs.existsSync(imagePath)) {
            const imageName = path.basename(imagePath);
            const destPath = path.join(imagesDir, imageName);
            
            if (!fs.existsSync(destPath)) {
                fs.copyFileSync(imagePath, destPath);
            }
            
            return `images/${imageName}`;
        }
    } catch (error) {
    }
    
    return null;
}

async function processForwardMessage(filePath, imagesDir) {
    try {
        const content = fs.readFileSync(filePath, 'utf-8');
        const data = JSON.parse(content);
        
        const results = [];
        if (data.messages && Array.isArray(data.messages)) {
            const processedMessages = [];
            let allImages = [];
            
            for (const msg of data.messages) {
                const { text, images } = extractTextFromContext(msg.context);
                const cleanedText = cleanText(text);
                
                if (cleanedText && isHighQualityMessage(cleanedText)) {
                    processedMessages.push({
                        user: msg.user,
                        nickname: msg.nickname || '未知用户',
                        text: cleanedText,
                        time: msg.time || 0,
                        images: images
                    });
                    allImages = allImages.concat(images);
                }
            }
            
            const conversations = smartSplitConversation(processedMessages);
            
            for (let i = 0; i < conversations.length; i++) {
                const conv = conversations[i];
                const conversationTexts = conv.map(m => m.text);
                
                const halfIndex = Math.floor(conv.length / 2);
                const questionPart = conversationTexts.slice(0, halfIndex).join('\n');
                const answerPart = conversationTexts.slice(halfIndex).join('\n');
                
                if (questionPart.trim() && answerPart.trim()) {
                    const conversationData = {
                        messages: conv,
                        text: conversationTexts.join('\n'),
                        hasImages: conv.some(m => m.images.length > 0)
                    };
                    
                    const qualityScore = calculateQualityScore(conversationData);
                    
                    if (qualityScore >= CONFIG.QUALITY_THRESHOLD) {
                        const copiedImages = [];
                        const imageDescriptions = [];
                        
                        if (CONFIG.COPY_IMAGES && imagesDir) {
                            for (const msg of conv) {
                                for (const img of msg.images) {
                                    const copiedPath = copyImage(img, imagesDir, filePath);
                                    if (copiedPath) {
                                        copiedImages.push(copiedPath);
                                        STATS.imagesCopied++;
                                        
                                        if (CONFIG.PROCESS_IMAGES && CONFIG.USE_API) {
                                            const fullImagePath = path.join(CONFIG.OUTPUT_DIR, copiedPath);
                                            const desc = await describeImage(fullImagePath);
                                            if (desc) {
                                                imageDescriptions.push({
                                                    path: copiedPath,
                                                    description: desc
                                                });
                                            }
                                        }
                                    }
                                }
                            }
                        }
                        
                        let enhancedSummary = null;
                        let generatedQA = null;
                        
                        if (CONFIG.USE_API && qualityScore >= 0.7) {
                            enhancedSummary = await enhanceConversation(conversationTexts.join('\n'));
                            generatedQA = await generateQAFromConversation(conversationTexts.join('\n'));
                        }
                        
                        results.push({
                            question: questionPart,
                            answer: answerPart,
                            chunkName: `forward_${path.basename(filePath, '.json')}_${i + 1}`,
                            chunkContent: conversationTexts.join('\n\n'),
                            model: 'chat_export',
                            questionLabel: 'conversation',
                            tags: ['聊天记录', '多轮对话', '转发消息'],
                            note: `来源: ${path.basename(filePath)}`,
                            qualityScore: qualityScore,
                            images: copiedImages,
                            imageDescriptions: imageDescriptions,
                            enhancedSummary: enhancedSummary,
                            generatedQA: generatedQA,
                            metadata: {
                                messageCount: conv.length,
                                userCount: new Set(conv.map(m => m.user)).size,
                                hasImages: copiedImages.length > 0,
                                apiEnhanced: !!enhancedSummary
                            }
                        });
                    } else {
                        STATS.skippedLowQuality++;
                    }
                }
            }
        }
        
        STATS.totalMessages += (data.messages || []).length;
        return results;
    } catch (error) {
        STATS.errors.push(`处理文件失败 ${filePath}: ${error.message}`);
        return [];
    }
}

async function processJsonlFile(filePath, imagesDir) {
    try {
        const content = fs.readFileSync(filePath, 'utf-8');
        const lines = content.split('\n').filter(line => line.trim());
        
        const allMessages = [];
        
        for (const line of lines) {
            try {
                const data = JSON.parse(line);
                const { text, images } = extractTextFromContext(data.context);
                const cleanedText = cleanText(text);
                
                if (cleanedText && isHighQualityMessage(cleanedText)) {
                    allMessages.push({
                        user: data.user,
                        nickname: data.nickname || '未知用户',
                        text: cleanedText,
                        time: data.time || 0,
                        images: images,
                        groupId: data.group_id,
                        groupName: data.group_name
                    });
                }
            } catch (e) {
            }
        }
        
        allMessages.sort((a, b) => a.time - b.time);
        
        const conversations = smartSplitConversation(allMessages);
        const results = [];
        
        for (let i = 0; i < conversations.length; i++) {
            const conv = conversations[i];
            const conversationTexts = conv.map(m => m.text);
            
            const halfIndex = Math.floor(conv.length / 2);
            const questionPart = conversationTexts.slice(0, halfIndex).join('\n');
            const answerPart = conversationTexts.slice(halfIndex).join('\n');
            
            if (questionPart.trim() && answerPart.trim()) {
                const conversationData = {
                    messages: conv,
                    text: conversationTexts.join('\n'),
                    hasImages: conv.some(m => m.images.length > 0)
                };
                
                const qualityScore = calculateQualityScore(conversationData);
                
                if (qualityScore >= CONFIG.QUALITY_THRESHOLD) {
                    const copiedImages = [];
                    const imageDescriptions = [];
                    
                    if (CONFIG.COPY_IMAGES && imagesDir) {
                        for (const msg of conv) {
                            for (const img of msg.images) {
                                const copiedPath = copyImage(img, imagesDir, filePath);
                                if (copiedPath) {
                                    copiedImages.push(copiedPath);
                                    STATS.imagesCopied++;
                                    
                                    if (CONFIG.PROCESS_IMAGES && CONFIG.USE_API) {
                                        const fullImagePath = path.join(CONFIG.OUTPUT_DIR, copiedPath);
                                        const desc = await describeImage(fullImagePath);
                                        if (desc) {
                                            imageDescriptions.push({
                                                path: copiedPath,
                                                description: desc
                                            });
                                        }
                                    }
                                }
                            }
                        }
                    }
                    
                    const groupName = conv[0]?.groupName || '未知群组';
                    
                    let enhancedSummary = null;
                    let generatedQA = null;
                    
                    if (CONFIG.USE_API && qualityScore >= 0.7) {
                        enhancedSummary = await enhanceConversation(conversationTexts.join('\n'));
                        generatedQA = await generateQAFromConversation(conversationTexts.join('\n'));
                    }
                    
                    results.push({
                        question: questionPart,
                        answer: answerPart,
                        chunkName: `chat_${groupName}_${i + 1}`,
                        chunkContent: conversationTexts.join('\n\n'),
                        model: 'chat_export',
                        questionLabel: 'conversation',
                        tags: ['聊天记录', '群聊', groupName],
                        note: `来源: ${path.basename(filePath)} | 群组: ${groupName}`,
                        qualityScore: qualityScore,
                        images: copiedImages,
                        imageDescriptions: imageDescriptions,
                        enhancedSummary: enhancedSummary,
                        generatedQA: generatedQA,
                        metadata: {
                            messageCount: conv.length,
                            userCount: new Set(conv.map(m => m.user)).size,
                            hasImages: copiedImages.length > 0,
                            groupName: groupName,
                            apiEnhanced: !!enhancedSummary
                        }
                    });
                } else {
                    STATS.skippedLowQuality++;
                }
            }
        }
        
        STATS.totalMessages += allMessages.length;
        return results;
    } catch (error) {
        STATS.errors.push(`处理JSONL文件失败 ${filePath}: ${error.message}`);
        return [];
    }
}

function convertToEasyDatasetFormat(results) {
    return results.map(item => ({
        question: item.question,
        answer: item.answer,
        chunkName: item.chunkName,
        chunkContent: item.chunkContent,
        model: item.model,
        questionLabel: item.questionLabel,
        tags: JSON.stringify(item.tags),
        note: item.note,
        confirmed: false,
        score: Math.round(item.qualityScore * 100) / 100,
        images: item.images || [],
        imageDescriptions: item.imageDescriptions || [],
        enhancedSummary: item.enhancedSummary,
        generatedQA: item.generatedQA,
        metadata: item.metadata
    }));
}

function convertToAlpacaFormat(results) {
    return results.map(item => ({
        instruction: item.question,
        input: '',
        output: item.answer
    }));
}

function convertToShareGPTFormat(results) {
    return results.map(item => ({
        conversations: [
            { role: 'user', content: item.question },
            { role: 'assistant', content: item.answer }
        ]
    }));
}

function convertToMultimodalFormat(results) {
    return results.filter(item => item.images && item.images.length > 0).map(item => ({
        id: item.chunkName,
        conversations: [
            {
                role: 'user',
                content: [
                    { type: 'text', text: item.question },
                    ...item.images.map(img => ({
                        type: 'image_url',
                        image_url: { url: img }
                    }))
                ]
            },
            { role: 'assistant', content: item.answer }
        ],
        imageDescriptions: item.imageDescriptions
    }));
}

async function importToEasyDataset(results, projectId) {
    if (!projectId) {
        console.log('⚠️ 未指定项目ID，跳过直接导入');
        return false;
    }
    
    const datasets = convertToEasyDatasetFormat(results);
    
    return new Promise((resolve) => {
        const postData = JSON.stringify({ datasets, sourceInfo: 'mira_export_converter' });
        
        const options = {
            hostname: 'localhost',
            port: 1717,
            path: `/api/projects/${projectId}/datasets/import`,
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(postData)
            }
        };
        
        const req = http.request(options, (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => {
                try {
                    const result = JSON.parse(data);
                    console.log(`✅ 已导入到 Easy Dataset: ${result.success} 条成功, ${result.failed} 条失败`);
                    resolve(true);
                } catch (e) {
                    console.log('❌ 导入响应解析失败:', e.message);
                    resolve(false);
                }
            });
        });
        
        req.on('error', (e) => {
            console.log('❌ 导入请求失败:', e.message);
            resolve(false);
        });
        
        req.write(postData);
        req.end();
    });
}

function printStats() {
    console.log('\n========== 处理统计 ==========');
    console.log(`📁 处理文件数: ${STATS.processedFiles}/${STATS.totalFiles}`);
    console.log(`💬 总消息数: ${STATS.totalMessages}`);
    console.log(`✅ 有效对话数: ${STATS.validConversations}`);
    console.log(`⏭️ 跳过(过短): ${STATS.skippedShort}`);
    console.log(`⏭️ 跳过(低质量): ${STATS.skippedLowQuality}`);
    console.log(`🖼️ 复制图片数: ${STATS.imagesCopied}`);
    console.log(`🤖 图片描述数: ${STATS.imagesProcessed}`);
    console.log(`🔌 API调用数: ${STATS.apiCalls}`);
    
    if (STATS.errors.length > 0) {
        console.log(`\n⚠️ 错误 (${STATS.errors.length} 个):`);
        STATS.errors.slice(0, 5).forEach(e => console.log(`  - ${e}`));
        if (STATS.errors.length > 5) {
            console.log(`  ... 还有 ${STATS.errors.length - 5} 个错误`);
        }
    }
}

async function main() {
    console.log('🚀 Mira Export 数据转换工具 v3.0 (增强版)');
    console.log('========================================\n');
    
    if (CONFIG.USE_API) {
        console.log('🔌 API增强已启用');
        console.log(`   提供商: ${CONFIG.API_CONFIG.provider}`);
        console.log(`   模型: ${CONFIG.API_CONFIG.model}`);
        console.log(`   Vision模型: ${CONFIG.API_CONFIG.visionModel}`);
        console.log('');
    }
    
    ensureDir(CONFIG.OUTPUT_DIR);
    const imagesDir = path.join(CONFIG.OUTPUT_DIR, 'images');
    if (CONFIG.COPY_IMAGES) {
        ensureDir(imagesDir);
    }
    
    let totalResults = [];
    
    const forwardDir = path.join(CONFIG.INPUT_DIR, 'forward');
    if (fs.existsSync(forwardDir)) {
        const forwardFiles = fs.readdirSync(forwardDir).filter(f => f.endsWith('.json'));
        STATS.totalFiles += forwardFiles.length;
        console.log(`📂 发现 ${forwardFiles.length} 个转发消息文件`);
        
        for (const file of forwardFiles) {
            const filePath = path.join(forwardDir, file);
            const results = await processForwardMessage(filePath, imagesDir);
            totalResults = totalResults.concat(results);
            STATS.processedFiles++;
            
            if (STATS.processedFiles % 50 === 0) {
                console.log(`  已处理 ${STATS.processedFiles}/${forwardFiles.length} 个转发文件...`);
            }
        }
        console.log(`  ✅ 转发消息处理完成\n`);
    }
    
    const jsonlFiles = fs.readdirSync(CONFIG.INPUT_DIR).filter(f => f.endsWith('.jsonl'));
    STATS.totalFiles += jsonlFiles.length;
    
    for (const file of jsonlFiles) {
        const filePath = path.join(CONFIG.INPUT_DIR, file);
        console.log(`📄 处理 JSONL 文件: ${file}`);
        const results = await processJsonlFile(filePath, imagesDir);
        totalResults = totalResults.concat(results);
        STATS.processedFiles++;
        console.log(`  生成 ${results.length} 条数据\n`);
    }
    
    STATS.validConversations = totalResults.length;
    
    totalResults.sort((a, b) => b.qualityScore - a.qualityScore);
    
    console.log('💾 保存数据文件...\n');
    
    const easyDatasetFormat = convertToEasyDatasetFormat(totalResults);
    const jsonPath = path.join(CONFIG.OUTPUT_DIR, 'easy_dataset_import.json');
    fs.writeFileSync(jsonPath, JSON.stringify(easyDatasetFormat, null, 2), 'utf-8');
    console.log(`✅ Easy Dataset 格式: ${jsonPath}`);
    
    const jsonlPath = path.join(CONFIG.OUTPUT_DIR, 'easy_dataset_import.jsonl');
    fs.writeFileSync(jsonlPath, easyDatasetFormat.map(item => JSON.stringify(item)).join('\n'), 'utf-8');
    console.log(`✅ JSONL 格式: ${jsonlPath}`);
    
    const alpacaFormat = convertToAlpacaFormat(totalResults);
    const alpacaPath = path.join(CONFIG.OUTPUT_DIR, 'alpaca_format.json');
    fs.writeFileSync(alpacaPath, JSON.stringify(alpacaFormat, null, 2), 'utf-8');
    console.log(`✅ Alpaca 格式: ${alpacaPath}`);
    
    const shareGPTFormat = convertToShareGPTFormat(totalResults);
    const shareGPTPath = path.join(CONFIG.OUTPUT_DIR, 'sharegpt_format.json');
    fs.writeFileSync(shareGPTPath, JSON.stringify(shareGPTFormat, null, 2), 'utf-8');
    console.log(`✅ ShareGPT 格式: ${shareGPTPath}`);
    
    const multimodalData = convertToMultimodalFormat(totalResults);
    if (multimodalData.length > 0) {
        const multimodalPath = path.join(CONFIG.OUTPUT_DIR, 'multimodal_format.json');
        fs.writeFileSync(multimodalPath, JSON.stringify(multimodalData, null, 2), 'utf-8');
        console.log(`✅ 多模态格式: ${multimodalPath} (${multimodalData.length} 条图文数据)`);
    }
    
    const highQuality = totalResults.filter(r => r.qualityScore >= 0.7);
    if (highQuality.length > 0) {
        const highQualityPath = path.join(CONFIG.OUTPUT_DIR, 'high_quality_dataset.json');
        fs.writeFileSync(highQualityPath, JSON.stringify(convertToEasyDatasetFormat(highQuality), null, 2), 'utf-8');
        console.log(`✅ 高质量数据集: ${highQualityPath} (${highQuality.length} 条)`);
    }
    
    const apiEnhanced = totalResults.filter(r => r.enhancedSummary || r.generatedQA);
    if (apiEnhanced.length > 0) {
        const apiEnhancedPath = path.join(CONFIG.OUTPUT_DIR, 'api_enhanced_dataset.json');
        fs.writeFileSync(apiEnhancedPath, JSON.stringify(convertToEasyDatasetFormat(apiEnhanced), null, 2), 'utf-8');
        console.log(`✅ API增强数据集: ${apiEnhancedPath} (${apiEnhanced.length} 条)`);
    }
    
    const statsPath = path.join(CONFIG.OUTPUT_DIR, 'conversion_stats.json');
    fs.writeFileSync(statsPath, JSON.stringify({
        config: CONFIG,
        stats: STATS,
        qualityDistribution: {
            high: totalResults.filter(r => r.qualityScore >= 0.7).length,
            medium: totalResults.filter(r => r.qualityScore >= 0.5 && r.qualityScore < 0.7).length,
            low: totalResults.filter(r => r.qualityScore < 0.5).length
        },
        generatedAt: new Date().toISOString()
    }, null, 2), 'utf-8');
    console.log(`✅ 统计信息: ${statsPath}`);
    
    if (CONFIG.DIRECT_IMPORT && CONFIG.PROJECT_ID) {
        console.log('\n📤 导入到 Easy Dataset...');
        await importToEasyDataset(totalResults, CONFIG.PROJECT_ID);
    }
    
    printStats();
    
    console.log('\n========== 使用说明 ==========');
    console.log('1. 打开 Easy Dataset: http://localhost:1717');
    console.log('2. 创建或选择项目');
    console.log('3. 进入"数据集"页面，点击"导入"');
    console.log('4. 选择 easy_dataset_import.json 文件');
    console.log('\n或使用高质量数据集: high_quality_dataset.json');
    if (multimodalData.length > 0) {
        console.log('图文数据集: multimodal_format.json');
    }
}

const args = process.argv.slice(2);
for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg === '--project-id' && args[i + 1]) {
        CONFIG.PROJECT_ID = args[i + 1];
        CONFIG.DIRECT_IMPORT = true;
        i++;
    } else if (arg === '--input' && args[i + 1]) {
        CONFIG.INPUT_DIR = args[i + 1];
        i++;
    } else if (arg === '--output' && args[i + 1]) {
        CONFIG.OUTPUT_DIR = args[i + 1];
        i++;
    } else if (arg === '--no-images') {
        CONFIG.COPY_IMAGES = false;
    } else if (arg === '--min-quality' && args[i + 1]) {
        CONFIG.QUALITY_THRESHOLD = parseFloat(args[i + 1]);
        i++;
    } else if (arg === '--api-key' && args[i + 1]) {
        CONFIG.USE_API = true;
        CONFIG.API_CONFIG.apiKey = args[i + 1];
        i++;
    } else if (arg === '--api-provider' && args[i + 1]) {
        CONFIG.API_CONFIG.provider = args[i + 1];
        i++;
    } else if (arg === '--api-model' && args[i + 1]) {
        CONFIG.API_CONFIG.model = args[i + 1];
        i++;
    } else if (arg === '--vision-model' && args[i + 1]) {
        CONFIG.API_CONFIG.visionModel = args[i + 1];
        CONFIG.PROCESS_IMAGES = true;
        i++;
    } else if (arg === '--process-images') {
        CONFIG.PROCESS_IMAGES = true;
    } else if (arg === '--help') {
        console.log(`
Mira Export 数据转换工具 v3.0 (增强版)

用法: node convert_mira_to_easy_dataset.js [选项]

基本选项:
  --input <目录>        输入目录 (默认: D:\\mira_export)
  --output <目录>       输出目录 (默认: D:\\mira_export_converted)
  --project-id <ID>     Easy Dataset 项目ID (启用直接导入)
  --no-images           不复制图片
  --min-quality <分数>  最低质量分数 (默认: 0.3)

API增强选项:
  --api-key <key>       API密钥 (启用API增强)
  --api-provider <名称> API提供商: openai/deepseek/zhipu/qwen/ollama/custom
  --api-model <模型>    文本模型 (默认: gpt-4o-mini)
  --vision-model <模型> 图片描述模型 (默认: gpt-4o-mini)
  --process-images      处理图片描述

示例:
  # 基本转换
  node convert_mira_to_easy_dataset.js

  # 使用API增强
  node convert_mira_to_easy_dataset.js --api-key sk-xxx --api-provider openai

  # 处理图片描述
  node convert_mira_to_easy_dataset.js --api-key sk-xxx --process-images --vision-model gpt-4o
        `);
        process.exit(0);
    }
}

main().catch(console.error);
