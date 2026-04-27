# 增强功能API配置要求总结

## 概述

已将所有增强功能修改为**必须配置外部API**才能使用。如果用户未配置API，访问这些功能时会收到明确的错误提示。

## 修改内容

### 1. 添加API配置验证装饰器

在 `qwen3_web_final.py` 中添加了 `require_api_config` 装饰器：

```python
def require_api_config(func):
    """
    装饰器 - 要求必须配置外部API才能使用增强功能
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        provider, config = get_active_api_provider()
        if not provider:
            return jsonify({
                'success': False,
                'error': '请先配置外部API',
                'message': '此功能需要配置外部API才能使用。请在设置中配置API提供商（OpenAI、Claude、DeepSeek等）',
                'require_api': True,
                'api_providers': list(api_configs.keys())
            }), 403
        return func(*args, **kwargs)
    return wrapper
```

### 2. 需要API配置的增强功能列表

以下功能已添加 `@require_api_config` 装饰器：

| 功能 | 路由 | 说明 |
|------|------|------|
| 工具执行 | `/tool/execute` | 搜索、翻译等工具 |
| 代码执行 | `/code/execute` | Python代码执行 |
| 知识库添加 | `/kb/add` | 智能摘要和标签生成 |
| MCP工具执行 | `/mcp/execute` | 插件工具执行 |
| 工作流执行 | `/workflow/<id>/execute` | 执行已保存的工作流 |
| 工作流直接执行 | `/workflow/execute` | 直接执行工作流 |
| Agent执行 | `/agent/execute` | 自主Agent任务 |

### 3. 移除本地回退逻辑

修改后的增强功能特点：
- ❌ 不再支持本地回退执行
- ❌ 不再检查 `use_api` 参数
- ✅ 统一使用 `call_api_with_unified_adapter()` 调用API
- ✅ 所有调用都通过统一API适配器

## 错误响应格式

当用户未配置API时，会收到以下错误响应：

```json
{
    "success": false,
    "error": "请先配置外部API",
    "message": "此功能需要配置外部API才能使用。请在设置中配置API提供商（OpenAI、Claude、DeepSeek等）",
    "require_api": true,
    "api_providers": ["openai", "claude", "gemini", "deepseek", "qwen", "moonshot", "zhipu"]
}
```

## 前端处理建议

前端应该根据 `require_api` 字段显示友好的提示：

```javascript
// 处理API配置错误
function handleApiError(response) {
    if (response.require_api) {
        showModal({
            title: '需要配置API',
            content: response.message,
            actions: [
                {
                    text: '去配置',
                    primary: true,
                    onClick: () => openSettings('api')
                },
                {
                    text: '取消',
                    onClick: () => closeModal()
                }
            ]
        });
    }
}
```

## 配置API的方法

用户需要在设置中配置以下信息：

```python
api_configs = {
    'openai': {
        'api_key': 'sk-...',
        'base_url': 'https://api.openai.com/v1',
        'model': 'gpt-4',
        'enabled': True
    },
    'claude': {
        'api_key': 'sk-ant-...',
        'base_url': 'https://api.anthropic.com',
        'model': 'claude-3-sonnet',
        'enabled': True
    },
    # ... 其他提供商
}
```

## 向后兼容性

- 基础聊天功能（`/chat`）**不需要**API配置，仍可使用本地模型
- 只有增强功能需要API配置
- 已配置的API会自动被统一API适配器使用

## 总结

通过添加 `@require_api_config` 装饰器，确保所有增强功能都必须配置外部API才能使用。这保证了：
1. 功能质量 - 使用强大的外部API而非本地简化版本
2. 用户体验 - 明确的错误提示引导用户配置
3. 代码简化 - 移除复杂的本地回退逻辑
4. 统一调用 - 所有功能都通过统一API适配器调用
