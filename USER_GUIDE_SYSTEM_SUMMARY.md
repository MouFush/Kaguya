# 用户引导系统总结

## 概述

为辉夜AI平台创建了完整的用户引导系统，在设备首次登录时自动展示使用说明，用户以后也可以随时在前端UI中查看相关说明。

## 系统组件

### 1. 后端系统 (`user_guide_system.py`)

#### 功能特性
- **设备首次登录检测**: 自动识别新设备
- **引导状态管理**: 记录用户引导进度
- **多章节内容管理**: 8个详细的使用说明章节
- **持久化存储**: JSON文件存储设备状态

#### 使用说明章节

| 章节ID | 标题 | 内容概要 |
|--------|------|----------|
| `welcome` | 欢迎使用辉夜AI平台 | 平台介绍、核心功能、快速开始 |
| `basic_chat` | 基础对话功能 | 对话方法、角色系统、提示技巧 |
| `tools` | 工具调用功能 | 可用工具列表、使用方法、注意事项 |
| `code_execution` | 代码执行功能 | 支持语言、安全特性、代码分析 |
| `knowledge_base` | 知识库功能 | 添加知识、检索知识、知识管理 |
| `advanced_features` | 增强功能介绍 | 工作流、Agent、MCP、多Agent协作 |
| `api_config` | 配置外部API | 支持的提供商、配置步骤、提示 |
| `shortcuts` | 快捷键和技巧 | 常用快捷键、使用技巧、界面定制 |
| `faq` | 常见问题 | 6个常见问题的解答 |

#### API接口

```python
# 检查是否是首次访问
GET /api/guide/check?device_id={device_id}

# 获取引导内容
GET /api/guide/content

# 标记章节完成
POST /api/guide/complete-section
Body: { device_id, section_id }

# 完成引导
POST /api/guide/complete
Body: { device_id }

# 重置引导
POST /api/guide/reset
Body: { device_id }
```

### 2. 前端系统 (`static/js/user-guide.js`)

#### 功能特性
- **自动检测首次访问**: 页面加载后自动检查
- **引导界面展示**: 美观的模态框展示使用说明
- **章节导航**: 顶部导航栏快速跳转
- **进度追踪**: 进度条显示阅读进度
- **帮助按钮**: 固定位置的帮助入口

#### 界面组件

1. **引导模态框**:
   - 标题栏（可关闭）
   - 进度条
   - 章节导航
   - 内容展示区
   - 底部操作按钮

2. **导航功能**:
   - 上一步/下一步按钮
   - 直接跳转到指定章节
   - 章节完成状态标记

3. **帮助按钮**:
   - 固定在页面右下角
   - 点击打开使用说明
   - 悬浮动画效果

#### 快捷键支持

| 操作 | 快捷键 |
|------|--------|
| 关闭引导 | Esc |
| 下一步 | → 或 Space |
| 上一步 | ← |

## 使用方法

### 集成到主应用

1. **添加后端API路由**:

```python
from user_guide_system import handle_guide_api

@app.route('/api/guide/check', methods=['GET'])
def guide_check():
    device_id = request.args.get('device_id')
    return jsonify(handle_guide_api('check_first_visit', device_id))

@app.route('/api/guide/content', methods=['GET'])
def guide_content():
    return jsonify(handle_guide_api('get_guide_content', ''))

@app.route('/api/guide/complete-section', methods=['POST'])
def guide_complete_section():
    data = request.json
    return jsonify(handle_guide_api(
        'mark_section_completed', 
        data.get('device_id'),
        section_id=data.get('section_id')
    ))

@app.route('/api/guide/complete', methods=['POST'])
def guide_complete():
    data = request.json
    return jsonify(handle_guide_api('complete_guide', data.get('device_id')))
```

2. **添加前端脚本**:

```html
<script src="/static/js/user-guide.js"></script>
```

### 用户操作流程

#### 首次访问流程
1. 用户首次访问平台
2. 系统自动检测设备ID
3. 判断为首次访问，延迟1秒后显示引导
4. 用户阅读使用说明
5. 可以逐章浏览或直接跳转到感兴趣章节
6. 完成后点击"完成引导"
7. 系统记录引导完成状态

#### 后续访问流程
1. 用户访问平台
2. 系统检测非首次访问，不自动显示引导
3. 页面右下角显示"❓ 帮助"按钮
4. 用户可以随时点击按钮查看使用说明

#### 查看使用说明
1. 点击右下角的"❓ 帮助"按钮
2. 或使用快捷键 `/` 打开（如已配置）
3. 浏览各章节内容
4. 点击关闭或完成按钮退出

## 自定义配置

### 修改使用说明内容

编辑 `user_guide_system.py` 中的 `USER_GUIDE_CONTENT` 字典：

```python
USER_GUIDE_CONTENT = {
    "custom_section": {
        "title": "自定义章节",
        "content": """
自定义内容...
        """
    }
}
```

### 调整引导行为

在 `user-guide.js` 中修改配置：

```javascript
// 修改延迟显示时间
setTimeout(() => {
    this.showGuide();
}, 2000); // 改为2秒

// 修改帮助按钮位置
const helpBtn = document.createElement('button');
helpBtn.style.bottom = '100px'; // 调整位置
```

## 数据存储

### 存储位置
- 文件: `./guide_data/device_guide_status.json`
- 格式: JSON

### 数据结构
```json
{
    "device_123456": {
        "device_id": "device_123456",
        "first_visit": false,
        "guide_completed": true,
        "guide_version": "1.0.0",
        "last_guide_time": "2026-03-03T12:00:00",
        "completed_sections": ["welcome", "basic_chat", "tools"]
    }
}
```

## 样式定制

### 修改主题颜色

在 `user-guide.js` 的CSS样式部分修改：

```css
.user-guide-btn-primary {
    background: linear-gradient(135deg, #667eea, #764ba2);
    /* 修改为您喜欢的颜色 */
}
```

### 响应式适配

系统已内置响应式支持：
- 桌面端: 800px宽度模态框
- 移动端: 95%宽度，自适应布局

## 注意事项

1. **设备ID生成**: 使用 localStorage 存储设备ID，清除浏览器数据会重置引导状态
2. **内容更新**: 修改使用说明内容后，已完成的用户不会重新看到引导
3. **版本控制**: 可以通过修改 `GUIDE_VERSION` 强制所有用户重新查看引导
4. **性能优化**: 引导内容按需加载，不会影响页面加载速度

## 后续扩展建议

1. **多语言支持**: 根据用户语言偏好显示不同语言的使用说明
2. **视频教程**: 在关键章节添加视频演示
3. **交互式引导**: 添加步骤式交互引导，手把手教用户使用
4. **搜索功能**: 在使用说明中添加搜索功能
5. **反馈收集**: 在引导完成后收集用户反馈

## 总结

用户引导系统为辉夜AI平台提供了：
- ✅ 首次登录自动引导
- ✅ 8个详细的使用说明章节
- ✅ 美观的引导界面
- ✅ 随时可访问的帮助入口
- ✅ 进度追踪和状态管理
- ✅ 响应式设计支持移动端

这大大提升了新用户的使用体验，降低了学习成本！
