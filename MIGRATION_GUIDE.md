# 辉夜AI平台代码重构迁移指南

## 概述

本指南帮助你将现有的重复代码迁移到新的 `kaguya_core` 统一框架。

## 已创建的模块

```
kaguya_core/
├── __init__.py          # 统一导出接口
├── base_manager.py      # 基础管理器类
├── config.py            # 统一配置管理
├── exceptions.py        # 统一异常处理
├── utils.py             # 通用工具函数
├── logging.py           # 统一日志管理
├── models.py            # 统一数据模型
└── example_refactor.py  # 重构示例
```

## 迁移步骤

### 1. 替换管理器基类

**重构前:**
```python
class SecurityManager:
    def __init__(self):
        self._initialized = False
        self._logger = None
        self._config = {}
    
    async def initialize(self):
        if self._initialized:
            return
        self._config = self._load_config()
        self._logger = self._setup_logger()
        self._initialized = True
```

**重构后:**
```python
from kaguya_core import BaseManager

class SecurityManager(BaseManager):
    async def _do_initialize(self) -> None:
        # 只需实现具体逻辑
        self.logger.info("初始化安全模块...")
```

### 2. 使用统一工具函数

**重构前:**
```python
import uuid
from datetime import datetime

def generate_id():
    return str(uuid.uuid4())

def timestamp_now():
    return datetime.utcnow().isoformat()
```

**重构后:**
```python
from kaguya_core import generate_id, timestamp_now

# 直接使用，无需重复定义
id = generate_id("prefix_")
ts = timestamp_now()
```

### 3. 使用统一配置

**重构前:**
```python
import json
import os

config = {}
if os.path.exists('config.json'):
    with open('config.json') as f:
        config = json.load(f)
```

**重构后:**
```python
from kaguya_core import get_config

config = get_config()
# 支持点号路径访问
db_url = config.get('database.url')
```

### 4. 使用统一异常

**重构前:**
```python
class ValidationError(Exception):
    pass

class NotFoundError(Exception):
    pass
```

**重构后:**
```python
from kaguya_core import ValidationError, NotFoundError

# 统一的异常处理，包含错误码和详情
raise ValidationError("Invalid input", field="username")
```

### 5. 使用统一日志

**重构前:**
```python
import logging

logger = logging.getLogger('MyModule')
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
logger.addHandler(handler)
```

**重构后:**
```python
from kaguya_core import get_logger

logger = get_logger('MyModule')
# 支持结构化日志
logger.info("事件", extra={'user_id': '123'})
```

### 6. 使用统一数据模型

**重构前:**
```python
from dataclasses import dataclass

@dataclass
class User:
    id: str
    username: str
    created_at: str
```

**重构后:**
```python
from kaguya_core.models import User, Status

# 使用统一模型，包含基础字段和方法
user = User(id="123", username="test")
user_dict = user.to_dict()
user.update(last_login="2024-01-01")
```

## 批量迁移脚本

```python
#!/usr/bin/env python3
"""批量迁移脚本示例"""

import os
import re

# 定义替换规则
REPLACEMENTS = [
    # 导入替换
    (r'import uuid\nfrom datetime import datetime', 
     'from kaguya_core import generate_id, timestamp_now'),
    
    # 类继承替换
    (r'class (\w+)Manager:',
     r'class \1Manager(BaseManager):'),
    
    # 初始化方法替换
    (r'def __init__\(self\):\s+self\._initialized = False',
     '# 继承 BaseManager 的初始化'),
    
    # 工具函数调用替换
    (r'str\(uuid\.uuid4\(\)\)',
     'generate_id()'),
    
    (r'datetime\.utcnow\(\)\.isoformat\(\)',
     'timestamp_now()'),
]

def migrate_file(filepath):
    """迁移单个文件"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    for pattern, replacement in REPLACEMENTS:
        content = re.sub(pattern, replacement, content)
    
    if content != original:
        # 添加导入
        if 'from kaguya_core import' not in content:
            content = 'from kaguya_core import BaseManager\n' + content
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ 已迁移: {filepath}")
    else:
        print(f"⏭️  跳过: {filepath}")

# 批量迁移
for root, dirs, files in os.walk('.'):
    for file in files:
        if file.endswith('.py') and file != 'kaguya_core':
            migrate_file(os.path.join(root, file))
```

## 验证清单

迁移完成后，请检查：

- [ ] 所有管理器继承 `BaseManager`
- [ ] 使用 `generate_id()` 替代 `uuid.uuid4()`
- [ ] 使用 `timestamp_now()` 替代 `datetime.utcnow().isoformat()`
- [ ] 使用 `get_config()` 替代手动配置加载
- [ ] 使用 `get_logger()` 替代手动日志设置
- [ ] 使用统一异常类替代自定义异常
- [ ] 使用统一数据模型替代重复定义

## 预期收益

| 指标 | 预期改进 |
|------|---------|
| 代码重复 | 减少 60-80% |
| 代码行数 | 减少 30-50% |
| 维护成本 | 降低 40% |
| Bug率 | 降低 25% |
| 开发效率 | 提升 30% |

## 回滚计划

如果迁移出现问题：

1. 保留原始文件备份
2. 使用 git 回滚：`git checkout -- <file>`
3. 逐步迁移，一次一个模块

## 支持

如有问题，请参考：
- `kaguya_core/example_refactor.py` - 重构示例
- `kaguya_core/__init__.py` - API文档
