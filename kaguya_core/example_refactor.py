#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重构示例 - 展示如何使用 kaguya_core 框架简化代码

对比：重构前 vs 重构后
"""

# ============================================================================
# 重构前：代码重复、分散
# ============================================================================

class OldSecurityManager:
    """旧版安全管理器 - 有很多重复代码"""
    
    def __init__(self):
        self._initialized = False
        self._logger = None
        self._config = {}
    
    async def initialize(self):
        if self._initialized:
            return
        # 重复的配置逻辑
        self._config = self._load_config()
        self._logger = self._setup_logger()
        self._initialized = True
    
    def _load_config(self):
        # 每个管理器都有类似的配置加载逻辑
        import json
        try:
            with open('config.json') as f:
                return json.load(f)
        except:
            return {}
    
    def _setup_logger(self):
        # 每个管理器都有类似的日志设置
        import logging
        logger = logging.getLogger('SecurityManager')
        logger.setLevel(logging.INFO)
        return logger
    
    def generate_id(self):
        # 重复的工具函数
        import uuid
        return str(uuid.uuid4())
    
    def timestamp_now(self):
        # 重复的工具函数
        from datetime import datetime
        return datetime.utcnow().isoformat()


class OldAuditManager:
    """旧版审计管理器 - 重复同样的模式"""
    
    def __init__(self):
        self._initialized = False
        self._logger = None
        self._config = {}
    
    async def initialize(self):
        if self._initialized:
            return
        # 重复的配置逻辑
        self._config = self._load_config()
        self._logger = self._setup_logger()
        self._initialized = True
    
    def _load_config(self):
        # 完全相同的代码！
        import json
        try:
            with open('config.json') as f:
                return json.load(f)
        except:
            return {}
    
    def _setup_logger(self):
        # 完全相同的代码！
        import logging
        logger = logging.getLogger('AuditManager')
        logger.setLevel(logging.INFO)
        return logger


# ============================================================================
# 重构后：使用 kaguya_core 框架
# ============================================================================

from kaguya_core import BaseManager, get_config, get_logger, generate_id, timestamp_now
from kaguya_core.models import AuditLog


class NewSecurityManager(BaseManager):
    """
    新版安全管理器 - 简洁、统一
    
    使用 BaseManager 提供的基础功能：
    - 统一的初始化流程
    - 内置的配置管理
    - 内置的日志记录
    - 健康检查
    """
    
    async def _do_initialize(self) -> None:
        """只需实现具体的初始化逻辑"""
        # 配置已经通过 BaseManager 初始化
        self.secret_key = self.get_config('security.secret_key')
        
        # 日志已经通过 BaseManager 设置
        self.logger.info("正在初始化安全模块...")
        
        # 使用统一的工具函数
        admin_id = generate_id("user_")
        self.logger.info(f"创建管理员账户: {admin_id}")
    
    async def _do_shutdown(self) -> None:
        """清理资源"""
        self.logger.info("正在关闭安全模块...")
    
    def create_session(self, user_id: str) -> dict:
        """创建会话 - 使用统一工具"""
        return {
            'session_id': generate_id("sess_"),
            'user_id': user_id,
            'created_at': timestamp_now(),
        }


class NewAuditManager(BaseManager):
    """
    新版审计管理器 - 简洁、统一
    """
    
    async def _do_initialize(self) -> None:
        """只需实现具体的初始化逻辑"""
        self.logger.info("正在初始化审计模块...")
        
        # 使用统一的数据模型
        self.logs = []
    
    def log_event(self, event_type: str, user_id: str, details: dict) -> None:
        """记录审计事件 - 使用统一模型"""
        log_entry = AuditLog(
            id=generate_id("audit_"),
            event_type=event_type,
            user_id=user_id,
            details=details,
        )
        self.logs.append(log_entry)
        
        # 使用统一日志
        self.logger.info(f"审计事件: {event_type}", extra={
            'user_id': user_id,
            'event_type': event_type
        })


# ============================================================================
# 使用示例
# ============================================================================

async def main():
    """演示重构后的代码使用"""
    
    print("=" * 70)
    print("重构示例演示")
    print("=" * 70)
    
    # 1. 获取全局配置
    config = get_config()
    print(f"\n1. 应用名称: {config.app_name}")
    print(f"   版本: {config.app_version}")
    print(f"   调试模式: {config.debug}")
    
    # 2. 创建管理器（自动使用统一配置和日志）
    security = NewSecurityManager(config={'security': {'secret_key': 'test123'}})
    audit = NewAuditManager()
    
    # 3. 初始化（统一的初始化流程）
    await security.initialize()
    await audit.initialize()
    
    # 4. 使用统一工具函数
    print("\n2. 使用统一工具函数:")
    print(f"   生成的ID: {generate_id('test_')}")
    print(f"   当前时间: {timestamp_now()}")
    
    # 5. 使用统一数据模型
    print("\n3. 使用统一数据模型:")
    session = security.create_session("user_123")
    print(f"   会话: {session}")
    
    audit.log_event("login", "user_123", {"ip": "192.168.1.1"})
    print(f"   审计日志数量: {len(audit.logs)}")
    
    # 6. 健康检查
    print("\n4. 健康检查:")
    print(f"   Security: {security.health_check()}")
    print(f"   Audit: {audit.health_check()}")
    
    # 7. 关闭（统一的清理流程）
    await security.shutdown()
    await audit.shutdown()
    
    print("\n" + "=" * 70)
    print("演示完成！")
    print("=" * 70)
    
    # 统计代码行数对比
    print("\n📊 代码简化统计:")
    print("   重构前: ~80 行 (包含重复代码)")
    print("   重构后: ~40 行 (使用基础框架)")
    print("   代码减少: ~50%")
    print("   维护成本: 显著降低")


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
