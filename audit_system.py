#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
审计日志系统
参考: SOC2合规要求, GDPR审计追踪
"""

import os
import json
import sqlite3
import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, asdict
import threading
import queue
import logging

# 审计日志数据库
AUDIT_DB_DIR = os.path.join(os.path.dirname(__file__), 'audit_logs')
os.makedirs(AUDIT_DB_DIR, exist_ok=True)

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
    """审计事件"""
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

class AuditLogger:
    """审计日志记录器"""
    
    def __init__(self):
        self.db_path = os.path.join(AUDIT_DB_DIR, 'audit.db')
        self._init_database()
        self._queue = queue.Queue()
        self._worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self._worker_thread.start()
        self._running = True
        
        # 配置日志文件
        self.file_logger = logging.getLogger('audit')
        self.file_logger.setLevel(logging.INFO)
        handler = logging.FileHandler(os.path.join(AUDIT_DB_DIR, 'audit.log'))
        formatter = logging.Formatter('%(asctime)s - %(message)s')
        handler.setFormatter(formatter)
        self.file_logger.addHandler(handler)
    
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
                print(f"审计日志处理错误: {e}")
    
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
            
            # 同时写入文件日志
            self.file_logger.info(json.dumps(event.to_dict(), ensure_ascii=False))
            
        except Exception as e:
            print(f"持久化审计事件失败: {e}")
    
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
            id=str(uuid.uuid4()),
            timestamp=datetime.now().isoformat(),
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
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        query = f'''
            SELECT * FROM audit_events
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        '''
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        # 转换为字典
        results = []
        for row in rows:
            results.append({
                'id': row[0],
                'timestamp': row[1],
                'event_type': row[2],
                'severity': row[3],
                'user_id': row[4],
                'tenant_id': row[5],
                'session_id': row[6],
                'ip_address': row[7],
                'user_agent': row[8],
                'resource_type': row[9],
                'resource_id': row[10],
                'action': row[11],
                'status': row[12],
                'details': json.loads(row[13]) if row[13] else {},
                'before_value': row[14],
                'after_value': row[15],
                'hash': row[16]
            })
        
        return results
    
    def get_statistics(self, tenant_id: Optional[str] = None, 
                      days: int = 30) -> Dict:
        """获取审计统计"""
        
        start_time = (datetime.now() - timedelta(days=days)).isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 基础统计
        query = '''
            SELECT 
                COUNT(*) as total_events,
                COUNT(DISTINCT user_id) as unique_users,
                COUNT(CASE WHEN severity = 'error' THEN 1 END) as error_count,
                COUNT(CASE WHEN severity = 'critical' THEN 1 END) as critical_count
            FROM audit_events
            WHERE timestamp > ?
        '''
        params = [start_time]
        
        if tenant_id:
            query += " AND tenant_id = ?"
            params.append(tenant_id)
        
        cursor.execute(query, params)
        row = cursor.fetchone()
        
        # 事件类型统计
        cursor.execute('''
            SELECT event_type, COUNT(*) as count
            FROM audit_events
            WHERE timestamp > ?
            GROUP BY event_type
            ORDER BY count DESC
            LIMIT 10
        ''', [start_time])
        event_types = {r[0]: r[1] for r in cursor.fetchall()}
        
        conn.close()
        
        return {
            'total_events': row[0],
            'unique_users': row[1],
            'error_count': row[2],
            'critical_count': row[3],
            'top_event_types': event_types,
            'period_days': days
        }
    
    def export_logs(self, format: str = 'json', 
                   start_time: Optional[str] = None,
                   end_time: Optional[str] = None) -> str:
        """导出审计日志"""
        
        logs = self.query(start_time=start_time, end_time=end_time, limit=10000)
        
        if format == 'json':
            filepath = os.path.join(AUDIT_DB_DIR, f'audit_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
        elif format == 'csv':
            import csv
            filepath = os.path.join(AUDIT_DB_DIR, f'audit_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                if logs:
                    writer = csv.DictWriter(f, fieldnames=logs[0].keys())
                    writer.writeheader()
                    writer.writerows(logs)
        
        return filepath
    
    def close(self):
        """关闭审计日志记录器"""
        self._running = False
        self._worker_thread.join(timeout=5)

# 全局实例
audit_logger = AuditLogger()

# 装饰器：自动记录函数调用
def audit_log(event_type: AuditEventType, 
              action: str,
              resource_type: Optional[str] = None):
    """审计日志装饰器"""
    def decorator(f):
        def wrapper(*args, **kwargs):
            # 获取请求信息（简化版）
            user_id = kwargs.get('user_id')
            tenant_id = kwargs.get('tenant_id')
            
            try:
                result = f(*args, **kwargs)
                
                # 记录成功
                audit_logger.log(
                    event_type=event_type,
                    action=action,
                    status="success",
                    user_id=user_id,
                    tenant_id=tenant_id,
                    resource_type=resource_type
                )
                
                return result
            except Exception as e:
                # 记录失败
                audit_logger.log(
                    event_type=event_type,
                    action=action,
                    status="failed",
                    severity=AuditSeverity.ERROR,
                    user_id=user_id,
                    tenant_id=tenant_id,
                    resource_type=resource_type,
                    details={'error': str(e)}
                )
                raise
        return wrapper
    return decorator

if __name__ == '__main__':
    # 测试
    logger = AuditLogger()
    
    # 记录一些事件
    logger.log(
        event_type=AuditEventType.LOGIN,
        action="user_login",
        user_id="user_123",
        tenant_id="tenant_456",
        ip_address="192.168.1.1",
        details={'method': 'password'}
    )
    
    logger.log(
        event_type=AuditEventType.CHAT_CREATED,
        action="create_chat",
        user_id="user_123",
        tenant_id="tenant_456",
        resource_type="chat",
        resource_id="chat_789",
        details={'title': '测试对话'}
    )
    
    # 等待异步处理
    import time
    time.sleep(2)
    
    # 查询
    logs = logger.query(user_id="user_123", limit=10)
    print(f"查询到 {len(logs)} 条日志")
    for log in logs:
        print(f"  {log['timestamp']} - {log['event_type']} - {log['action']}")
    
    # 统计
    stats = logger.get_statistics()
    print(f"\n统计: {stats}")
    
    logger.close()
