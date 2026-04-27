#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
监控和告警系统
参考: Prometheus + Grafana, Datadog
"""

import os
import json
import time
import sqlite3
import threading
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
import statistics

# 监控数据目录
MONITORING_DIR = os.path.join(os.path.dirname(__file__), 'monitoring')
os.makedirs(MONITORING_DIR, exist_ok=True)

class MetricType(Enum):
    """指标类型"""
    COUNTER = "counter"  # 计数器（只增）
    GAUGE = "gauge"      # 仪表盘（可增可减）
    HISTOGRAM = "histogram"  # 直方图
    SUMMARY = "summary"  # 摘要

class AlertSeverity(Enum):
    """告警严重程度"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

@dataclass
class Metric:
    """指标"""
    name: str
    metric_type: MetricType
    value: float
    timestamp: float
    labels: Dict[str, str]
    
    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'type': self.metric_type.value,
            'value': self.value,
            'timestamp': self.timestamp,
            'labels': self.labels
        }

@dataclass
class AlertRule:
    """告警规则"""
    id: str
    name: str
    description: str
    metric_name: str
    condition: str  # '>', '<', '==', '>=', '<='
    threshold: float
    duration: int  # 持续时间（秒）
    severity: AlertSeverity
    enabled: bool = True
    
    def evaluate(self, value: float) -> bool:
        """评估是否触发告警"""
        if not self.enabled:
            return False
        
        if self.condition == '>':
            return value > self.threshold
        elif self.condition == '<':
            return value < self.threshold
        elif self.condition == '>=':
            return value >= self.threshold
        elif self.condition == '<=':
            return value <= self.threshold
        elif self.condition == '==':
            return value == self.threshold
        
        return False

@dataclass
class Alert:
    """告警"""
    id: str
    rule_id: str
    rule_name: str
    severity: AlertSeverity
    message: str
    timestamp: float
    value: float
    threshold: float
    acknowledged: bool = False
    resolved: bool = False
    resolved_at: Optional[float] = None

class MetricsCollector:
    """指标收集器"""
    
    def __init__(self):
        self.db_path = os.path.join(MONITORING_DIR, 'metrics.db')
        self._init_database()
        self._metrics_buffer = []
        self._buffer_lock = threading.Lock()
        self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._flush_thread.start()
    
    def _init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                metric_type TEXT NOT NULL,
                value REAL NOT NULL,
                timestamp REAL NOT NULL,
                labels TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_metrics_name ON metrics(name)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics(timestamp)
        ''')
        
        conn.commit()
        conn.close()
    
    def record(self, name: str, value: float, 
               metric_type: MetricType = MetricType.GAUGE,
               labels: Optional[Dict[str, str]] = None):
        """记录指标"""
        metric = Metric(
            name=name,
            metric_type=metric_type,
            value=value,
            timestamp=time.time(),
            labels=labels or {}
        )
        
        with self._buffer_lock:
            self._metrics_buffer.append(metric)
    
    def increment(self, name: str, value: float = 1.0, 
                  labels: Optional[Dict[str, str]] = None):
        """增加计数器"""
        self.record(name, value, MetricType.COUNTER, labels)
    
    def gauge(self, name: str, value: float,
              labels: Optional[Dict[str, str]] = None):
        """设置仪表盘值"""
        self.record(name, value, MetricType.GAUGE, labels)
    
    def histogram(self, name: str, value: float,
                  labels: Optional[Dict[str, str]] = None):
        """记录直方图值"""
        self.record(name, value, MetricType.HISTOGRAM, labels)
    
    def _flush_loop(self):
        """定期刷新缓冲区到数据库"""
        while True:
            time.sleep(10)  # 每10秒刷新一次
            self._flush_buffer()
    
    def _flush_buffer(self):
        """刷新缓冲区"""
        with self._buffer_lock:
            if not self._metrics_buffer:
                return
            
            metrics_to_flush = self._metrics_buffer[:]
            self._metrics_buffer = []
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for metric in metrics_to_flush:
                cursor.execute('''
                    INSERT INTO metrics (name, metric_type, value, timestamp, labels)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    metric.name,
                    metric.metric_type.value,
                    metric.value,
                    metric.timestamp,
                    json.dumps(metric.labels)
                ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"刷新指标失败: {e}")
    
    def query(self, name: str, start_time: Optional[float] = None,
              end_time: Optional[float] = None, 
              limit: int = 1000) -> List[Dict]:
        """查询指标"""
        if start_time is None:
            start_time = time.time() - 3600  # 默认最近1小时
        if end_time is None:
            end_time = time.time()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM metrics
            WHERE name = ? AND timestamp >= ? AND timestamp <= ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (name, start_time, end_time, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                'id': row[0],
                'name': row[1],
                'type': row[2],
                'value': row[3],
                'timestamp': row[4],
                'labels': json.loads(row[5]) if row[5] else {}
            }
            for row in rows
        ]
    
    def get_stats(self, name: str, 
                  start_time: Optional[float] = None,
                  end_time: Optional[float] = None) -> Dict:
        """获取指标统计"""
        data = self.query(name, start_time, end_time, limit=10000)
        
        if not data:
            return {'count': 0}
        
        values = [d['value'] for d in data]
        
        return {
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'mean': statistics.mean(values),
            'median': statistics.median(values),
            'stdev': statistics.stdev(values) if len(values) > 1 else 0
        }

class AlertManager:
    """告警管理器"""
    
    def __init__(self):
        self.db_path = os.path.join(MONITORING_DIR, 'alerts.db')
        self._init_database()
        self.rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self._alert_handlers: List[Callable] = []
        self._lock = threading.Lock()
        
        # 加载默认规则
        self._load_default_rules()
        
        # 启动评估线程
        self._eval_thread = threading.Thread(target=self._evaluation_loop, daemon=True)
        self._eval_thread.start()
    
    def _init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id TEXT PRIMARY KEY,
                rule_id TEXT NOT NULL,
                rule_name TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp REAL NOT NULL,
                value REAL NOT NULL,
                threshold REAL NOT NULL,
                acknowledged INTEGER DEFAULT 0,
                resolved INTEGER DEFAULT 0,
                resolved_at REAL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _load_default_rules(self):
        """加载默认告警规则"""
        default_rules = [
            AlertRule(
                id="high_error_rate",
                name="高错误率",
                description="API错误率超过5%",
                metric_name="api_error_rate",
                condition=">",
                threshold=0.05,
                duration=300,
                severity=AlertSeverity.WARNING
            ),
            AlertRule(
                id="high_latency",
                name="高延迟",
                description="API响应时间超过5秒",
                metric_name="api_response_time",
                condition=">",
                threshold=5000,
                duration=180,
                severity=AlertSeverity.WARNING
            ),
            AlertRule(
                id="disk_full",
                name="磁盘空间不足",
                description="磁盘使用率超过90%",
                metric_name="disk_usage_percent",
                condition=">",
                threshold=90,
                duration=60,
                severity=AlertSeverity.CRITICAL
            ),
            AlertRule(
                id="memory_high",
                name="内存使用率高",
                description="内存使用率超过85%",
                metric_name="memory_usage_percent",
                condition=">",
                threshold=85,
                duration=300,
                severity=AlertSeverity.WARNING
            ),
        ]
        
        for rule in default_rules:
            self.rules[rule.id] = rule
    
    def add_rule(self, rule: AlertRule):
        """添加告警规则"""
        self.rules[rule.id] = rule
    
    def remove_rule(self, rule_id: str):
        """移除告警规则"""
        self.rules.pop(rule_id, None)
    
    def add_alert_handler(self, handler: Callable):
        """添加告警处理器"""
        self._alert_handlers.append(handler)
    
    def _evaluation_loop(self):
        """告警评估循环"""
        # 这里简化实现，实际应该定期查询指标
        while True:
            time.sleep(60)  # 每分钟评估一次
            self._evaluate_rules()
    
    def _evaluate_rules(self):
        """评估所有规则"""
        # 简化实现，实际应该从MetricsCollector查询
        pass
    
    def evaluate_metric(self, metric_name: str, value: float):
        """评估特定指标"""
        for rule in self.rules.values():
            if rule.metric_name == metric_name and rule.evaluate(value):
                self._trigger_alert(rule, value)
    
    def _trigger_alert(self, rule: AlertRule, value: float):
        """触发告警"""
        alert_id = f"{rule.id}_{int(time.time())}"
        
        with self._lock:
            # 检查是否已有相同规则的活跃告警
            for alert in self.active_alerts.values():
                if alert.rule_id == rule.id and not alert.resolved:
                    return  # 已有活跃告警，不重复触发
            
            alert = Alert(
                id=alert_id,
                rule_id=rule.id,
                rule_name=rule.name,
                severity=rule.severity,
                message=f"{rule.description} (当前值: {value:.2f}, 阈值: {rule.threshold})",
                timestamp=time.time(),
                value=value,
                threshold=rule.threshold
            )
            
            self.active_alerts[alert_id] = alert
        
        # 保存到数据库
        self._save_alert(alert)
        
        # 通知处理器
        for handler in self._alert_handlers:
            try:
                handler(alert)
            except:
                pass
    
    def _save_alert(self, alert: Alert):
        """保存告警到数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO alerts 
                (id, rule_id, rule_name, severity, message, timestamp, value, threshold)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                alert.id, alert.rule_id, alert.rule_name, alert.severity.value,
                alert.message, alert.timestamp, alert.value, alert.threshold
            ))
            conn.commit()
            conn.close()
        except:
            pass
    
    def acknowledge_alert(self, alert_id: str):
        """确认告警"""
        with self._lock:
            if alert_id in self.active_alerts:
                self.active_alerts[alert_id].acknowledged = True
    
    def resolve_alert(self, alert_id: str):
        """解决告警"""
        with self._lock:
            if alert_id in self.active_alerts:
                alert = self.active_alerts[alert_id]
                alert.resolved = True
                alert.resolved_at = time.time()
                
                # 更新数据库
                try:
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE alerts SET resolved = 1, resolved_at = ?
                        WHERE id = ?
                    ''', (alert.resolved_at, alert_id))
                    conn.commit()
                    conn.close()
                except:
                    pass
    
    def get_active_alerts(self, severity: Optional[AlertSeverity] = None) -> List[Alert]:
        """获取活跃告警"""
        with self._lock:
            alerts = [
                alert for alert in self.active_alerts.values()
                if not alert.resolved and (severity is None or alert.severity == severity)
            ]
            return sorted(alerts, key=lambda x: x.timestamp, reverse=True)
    
    def get_alert_history(self, limit: int = 100) -> List[Dict]:
        """获取告警历史"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM alerts
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                'id': row[0],
                'rule_id': row[1],
                'rule_name': row[2],
                'severity': row[3],
                'message': row[4],
                'timestamp': row[5],
                'value': row[6],
                'threshold': row[7],
                'acknowledged': bool(row[8]),
                'resolved': bool(row[9]),
                'resolved_at': row[10]
            }
            for row in rows
        ]

class SystemMonitor:
    """系统监控器"""
    
    def __init__(self):
        self.metrics = MetricsCollector()
        self.alerts = AlertManager()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._running = False
    
    def start(self):
        """启动监控"""
        self._running = True
        self._monitor_thread.start()
        print("✓ 系统监控已启动")
    
    def stop(self):
        """停止监控"""
        self._running = False
    
    def _monitor_loop(self):
        """监控循环"""
        import psutil
        
        while self._running:
            try:
                # CPU使用率
                cpu_percent = psutil.cpu_percent(interval=1)
                self.metrics.gauge("cpu_usage_percent", cpu_percent)
                self.alerts.evaluate_metric("cpu_usage_percent", cpu_percent)
                
                # 内存使用
                memory = psutil.virtual_memory()
                self.metrics.gauge("memory_usage_percent", memory.percent)
                self.metrics.gauge("memory_used_mb", memory.used / 1024 / 1024)
                self.metrics.gauge("memory_available_mb", memory.available / 1024 / 1024)
                self.alerts.evaluate_metric("memory_usage_percent", memory.percent)
                
                # 磁盘使用
                disk = psutil.disk_usage('/')
                disk_percent = (disk.used / disk.total) * 100
                self.metrics.gauge("disk_usage_percent", disk_percent)
                self.metrics.gauge("disk_used_gb", disk.used / 1024 / 1024 / 1024)
                self.metrics.gauge("disk_free_gb", disk.free / 1024 / 1024 / 1024)
                self.alerts.evaluate_metric("disk_usage_percent", disk_percent)
                
                # 网络IO
                net_io = psutil.net_io_counters()
                self.metrics.gauge("network_sent_mb", net_io.bytes_sent / 1024 / 1024)
                self.metrics.gauge("network_recv_mb", net_io.bytes_recv / 1024 / 1024)
                
                # 进程数
                self.metrics.gauge("process_count", len(psutil.pids()))
                
            except Exception as e:
                print(f"监控采集错误: {e}")
            
            time.sleep(30)  # 每30秒采集一次

# 全局实例
metrics_collector = MetricsCollector()
alert_manager = AlertManager()
system_monitor = SystemMonitor()

if __name__ == '__main__':
    # 测试
    metrics = MetricsCollector()
    alerts = AlertManager()
    
    # 记录一些指标
    for i in range(10):
        metrics.gauge("test_metric", i * 10)
        time.sleep(0.1)
    
    # 查询指标
    data = metrics.query("test_metric")
    print(f"记录了 {len(data)} 个指标")
    
    # 获取统计
    stats = metrics.get_stats("test_metric")
    print(f"统计: {stats}")
    
    # 测试告警
    alerts.evaluate_metric("disk_usage_percent", 95)
    
    # 获取活跃告警
    active = alerts.get_active_alerts()
    print(f"活跃告警: {len(active)}")
    for alert in active:
        print(f"  - {alert.rule_name}: {alert.message}")
