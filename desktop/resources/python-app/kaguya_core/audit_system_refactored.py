#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
审计日志系统 - 重构版
使用 kaguya_core 框架，减少代码重复

参考: SOC2合规要求, GDPR审计追踪
"""

import os
import json
import sqlite3
import hashlib
import queue
import threading
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass

# 使用核心框架
from .base_manager import BaseManager
from .utils import generate_id, timestamp_now
from .logging import get_logger
from .models import AuditLog as AuditLogModel


class AuditEventType(Enum):
    """审计事件类型"""
    # 认证事件
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    PASSWORD_CHANGE = "password_change"
    API_KEY_CREATED = "api_key_created"
    API_KEY_REVOKED = "api_key_revoked"
    
    # 数据访问
    DATA_READ = "data_read"
    DATA_WRITE = "data_write"
    DATA_DELETE = "data_delete"
    DATA_EXPORT = "data_export"
    
    # 对话事件
    CHAT_CREATED = "chat_created"
    CHAT_DELETED = "chat_deleted"
    MESSAGE_SENT = "message_sent"
    MESSAGE_RECEIVED = "message_received"
    
    # 模型使用
    MODEL_INVOKED = "model_invoked"
    MODEL_SWITCHED = "model_switched"
    FINE_TUNE_STARTED = "fine_tune_started"
    
    # 知识库
    KB_DOCUMENT_ADDED = "kb_document_added"
    KB_DOCUMENT_DELETED = "kb_document_deleted"
    KB_SEARCH = "kb_search"
    
    # 系统管理
    USER_CREATED = "user_created"
    USER_DELETED = "user_deleted"
    ROLE_CHANGED = "role_changed"
    SETTINGS_CHANGED = "settings_changed"
    
    # 安全事件
    PERMISSION_DENIED = "permission_denied"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    
    # API事件
    API_CALLED = "api_called"
    WEBHOOK_TRIGGERED = "webhook_triggered"


class AuditSeverity(Enum):
    """审计事件严重程度"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """审计事件 - 兼容旧版"""
    id: str
    timestamp: str
    event_type: AuditEventType
    severity: AuditSeverity
    user_id: Optional[str]
    tenant_id: Optional[str]
    session_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    resource_type: Optional[str]
    resource_id: Optional[str]
    action: str
    status: str
    details: Dict[str, Any]
    before_value: Optional[str]
    after_value: Optional[str]
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'timestamp': self.timestamp,
            'event_type': self.event_type.value,
            'severity': self.severity.value,
            'user_id': self.user_id,
            'tenant_id': self.tenant_id,
            'session_id': self.session_id,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'action': self.action,
            'status': self.status,
            'details': self.details,
            'before_value': self.before_value,
            'after_value': self.after_value
        }


class AuditLogger(BaseManager):
    """
    审计日志记录器 - 重构版
    
    使用 BaseManager 提供的基础功能
    """
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.db_path = None
        self._queue = queue.Queue()
        self._worker_thread = None
        self._running = False
        
    async def _do_initialize(self) -> None:
        """初始化审计系统"""
        # 获取配置
        audit_dir = self.get_config('audit_dir', './audit_logs')
        os.makedirs(audit_dir, exist_ok=True)
        
        self.db_path = os.path.join(audit_dir, 'audit.db')
        
        # 初始化数据库
        self._init_database()
        
        # 启动工作线程
        self._running = True
        self._worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self._worker_thread.start()
        
        self.logger.info("审计日志系统初始化完成")
    
    async def _do_shutdown(self) -> None:
        """关闭审计系统"""
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=5)
        self.logger.info("审计日志系统已关闭")
    
    def _init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 审计事件表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_events (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                user_id TEXT,
                tenant_id TEXT,
                session_id TEXT,
                ip_address TEXT,
                user_agent TEXT,
                resource_type TEXT,
                resource_id TEXT,
                action TEXT NOT NULL,
                status TEXT NOT NULL,
                details TEXT,
                before_value TEXT,
                after_value TEXT,
                hash TEXT NOT NULL
            )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_events(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user ON audit_events(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tenant ON audit_events(tenant_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_event_type ON audit_events(event_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_severity ON audit_events(severity)')
        
        conn.commit()
        conn.close()
    
    def _calculate_hash(self, event: AuditEvent) -> str:
        """计算事件哈希（防篡改）"""
        data = f"{event.id}{event.timestamp}{event.event_type.value}{event.user_id}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def _process_queue(self):
        """处理队列中的审计事件"""
        while self._running:
            try:
                event = self._queue.get(timeout=1)
                self._persist_event(event)
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"审计日志处理错误: {e}")
    
    def _persist_event(self, event: AuditEvent):
        """持久化审计事件"""
        try:
            # 计算哈希
            event_hash = self._calculate_hash(event)
            
            # 写入数据库
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO audit_events 
                (id, timestamp, event_type, severity, user_id, tenant_id, session_id,
                 ip_address, user_agent, resource_type, resource_id, action, status,
                 details, before_value, after_value, hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                event.id, event.timestamp, event.event_type.value, event.severity.value,
                event.user_id, event.tenant_id, event.session_id, event.ip_address,
                event.user_agent, event.resource_type, event.resource_id, event.action,
                event.status, json.dumps(event.details), event.before_value,
                event.after_value, event_hash
            ))
            conn.commit()
            conn.close()
            
            # 同时记录到结构化日志
            self.logger.info(f"审计事件: {event.event_type.value}", extra={
                'event_type': event.event_type.value,
                'user_id': event.user_id,
                'action': event.action,
                'severity': event.severity.value
            })
            
        except Exception as e:
            self.logger.error(f"持久化审计事件失败: {e}")
    
    def log(self, 
            event_type: AuditEventType,
            action: str,
            status: str = "success",
            severity: AuditSeverity = AuditSeverity.INFO,
            user_id: Optional[str] = None,
            tenant_id: Optional[str] = None,
            session_id: Optional[str] = None,
            ip_address: Optional[str] = None,
            user_agent: Optional[str] = None,
            resource_type: Optional[str] = None,
            resource_id: Optional[str] = None,
            details: Optional[Dict] = None,
            before_value: Optional[str] = None,
            after_value: Optional[str] = None):
        """记录审计事件"""
        
        event = AuditEvent(
            id=generate_id(),
            timestamp=timestamp_now(),
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            tenant_id=tenant_id,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            status=status,
            details=details or {},
            before_value=before_value,
            after_value=after_value
        )
        
        # 放入队列异步处理
        self._queue.put(event)
        
        # 关键事件立即处理
        if severity in [AuditSeverity.ERROR, AuditSeverity.CRITICAL]:
            self._persist_event(event)
    
    def query(self,
              start_time: Optional[str] = None,
              end_time: Optional[str] = None,
              user_id: Optional[str] = None,
              tenant_id: Optional[str] = None,
              event_types: Optional[List[AuditEventType]] = None,
              severity: Optional[AuditSeverity] = None,
              limit: int = 100,
              offset: int = 0) -> List[Dict]:
        """查询审计日志"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 构建查询
        conditions = []
        params = []
        
        if start_time:
            conditions.append("timestamp >= ?")
            params.append(start_time)
        if end_time:
            conditions.append("timestamp <= ?")
            params.append(end_time)
        if user_id:
            conditions.append("user_id = ?")
            params.append(user_id)
        if tenant_id:
            conditions.append("tenant_id = ?")
            params.append(tenant_id)
        if event_types:
            placeholders = ','.join(['?' for _ in event_types])
            conditions.append(f"event_type IN ({placeholders})")
            params.extend([et.value for et in event_types])
        if severity:
            conditions.append("severity = ?")
            params.append(severity.value)
        
        # 构建SQL
        sql = "SELECT * FROM audit_events"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        # 执行查询
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        
        # 获取列名
        columns = [description[0] for description in cursor.description]
        
        # 转换为字典列表
        results = []
        for row in rows:
            result = dict(zip(columns, row))
            # 解析JSON详情
            if result.get('details'):
                try:
                    result['details'] = json.loads(result['details'])
                except:
                    pass
            results.append(result)
        
        conn.close()
        return results
    
    def get_statistics(self, days: int = 30) -> Dict:
        """获取审计统计"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 总事件数
        cursor.execute("SELECT COUNT(*) FROM audit_events")
        total_events = cursor.fetchone()[0]
        
        # 按类型统计
        cursor.execute('''
            SELECT event_type, COUNT(*) as count 
            FROM audit_events 
            GROUP BY event_type 
            ORDER BY count DESC
        ''')
        event_type_stats = {row[0]: row[1] for row in cursor.fetchall()}
        
        # 按严重程度统计
        cursor.execute('''
            SELECT severity, COUNT(*) as count 
            FROM audit_events 
            GROUP BY severity
        ''')
        severity_stats = {row[0]: row[1] for row in cursor.fetchall()}
        
        conn.close()
        
        return {
            'total_events': total_events,
            'event_type_stats': event_type_stats,
            'severity_stats': severity_stats
        }


# 全局实例（保持兼容性）
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger(config: Optional[Dict] = None) -> AuditLogger:
    """获取审计日志记录器实例"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger(config)
    return _audit_logger


# 保持旧版兼容性
audit_logger = get_audit_logger()
