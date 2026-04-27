#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能监控系统 - 实时性能指标收集与分析
功能: 响应时间监控、资源使用追踪、性能告警、趋势分析
"""

import time
import threading
import psutil
import json
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import deque, defaultdict
import statistics


@dataclass
class MetricPoint:
    """指标数据点"""
    timestamp: float
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class RequestMetrics:
    """请求指标"""
    endpoint: str
    method: str
    status_code: int
    response_time_ms: float
    timestamp: float
    user_agent: str = ""
    error_message: str = ""


class MetricsCollector:
    """指标收集器"""
    
    def __init__(self, max_history: int = 10000):
        self.max_history = max_history
        self.request_history: deque = deque(maxlen=max_history)
        self.response_times: defaultdict = defaultdict(lambda: deque(maxlen=1000))
        self.error_counts: defaultdict = defaultdict(int)
        self.endpoint_counts: defaultdict = defaultdict(int)
        self.lock = threading.RLock()
        
        # 系统资源指标
        self.system_metrics: deque = deque(maxlen=3600)  # 1小时，每秒一个点
        
        # 启动系统监控线程
        self._start_system_monitor()
    
    def record_request(self, endpoint: str, method: str, status_code: int, 
                      response_time_ms: float, user_agent: str = "", 
                      error_message: str = ""):
        """记录请求指标"""
        with self.lock:
            metric = RequestMetrics(
                endpoint=endpoint,
                method=method,
                status_code=status_code,
                response_time_ms=response_time_ms,
                timestamp=time.time(),
                user_agent=user_agent,
                error_message=error_message
            )
            
            self.request_history.append(metric)
            self.response_times[endpoint].append(response_time_ms)
            self.endpoint_counts[f"{method}:{endpoint}"] += 1
            
            if status_code >= 400:
                self.error_counts[endpoint] += 1
    
    def get_response_time_stats(self, endpoint: str, last_n: int = 100) -> Dict:
        """获取响应时间统计"""
        with self.lock:
            times = list(self.response_times[endpoint])[-last_n:]
            
            if not times:
                return {
                    'count': 0,
                    'avg_ms': 0,
                    'min_ms': 0,
                    'max_ms': 0,
                    'p50_ms': 0,
                    'p95_ms': 0,
                    'p99_ms': 0
                }
            
            times.sort()
            
            return {
                'count': len(times),
                'avg_ms': round(statistics.mean(times), 2),
                'min_ms': round(min(times), 2),
                'max_ms': round(max(times), 2),
                'p50_ms': round(times[int(len(times) * 0.5)], 2),
                'p95_ms': round(times[int(len(times) * 0.95)], 2),
                'p99_ms': round(times[int(len(times) * 0.99)], 2)
            }
    
    def get_endpoint_summary(self, time_window_seconds: float = 3600) -> Dict:
        """获取端点汇总统计"""
        with self.lock:
            cutoff_time = time.time() - time_window_seconds
            
            summary = defaultdict(lambda: {
                'count': 0,
                'error_count': 0,
                'total_response_time': 0,
                'avg_response_time': 0
            })
            
            for metric in self.request_history:
                if metric.timestamp < cutoff_time:
                    continue
                
                key = f"{metric.method}:{metric.endpoint}"
                summary[key]['count'] += 1
                summary[key]['total_response_time'] += metric.response_time_ms
                
                if metric.status_code >= 400:
                    summary[key]['error_count'] += 1
            
            # 计算平均值
            for key in summary:
                count = summary[key]['count']
                if count > 0:
                    summary[key]['avg_response_time'] = round(
                        summary[key]['total_response_time'] / count, 2
                    )
            
            return dict(summary)
    
    def get_error_rate(self, time_window_seconds: float = 3600) -> float:
        """获取错误率"""
        with self.lock:
            cutoff_time = time.time() - time_window_seconds
            
            total = 0
            errors = 0
            
            for metric in self.request_history:
                if metric.timestamp < cutoff_time:
                    continue
                
                total += 1
                if metric.status_code >= 400:
                    errors += 1
            
            return round(errors / total * 100, 2) if total > 0 else 0.0
    
    def get_rpm(self, time_window_seconds: float = 60) -> float:
        """获取每分钟请求数"""
        with self.lock:
            cutoff_time = time.time() - time_window_seconds
            
            count = sum(1 for m in self.request_history if m.timestamp >= cutoff_time)
            
            return round(count / (time_window_seconds / 60), 2)
    
    def _start_system_monitor(self):
        """启动系统监控线程"""
        def monitor_task():
            while True:
                try:
                    metric = {
                        'timestamp': time.time(),
                        'cpu_percent': psutil.cpu_percent(interval=1),
                        'memory_percent': psutil.virtual_memory().percent,
                        'memory_available_mb': psutil.virtual_memory().available / (1024 * 1024),
                        'disk_usage_percent': psutil.disk_usage('/').percent,
                        'network_io': {
                            'bytes_sent': psutil.net_io_counters().bytes_sent,
                            'bytes_recv': psutil.net_io_counters().bytes_recv
                        }
                    }
                    
                    with self.lock:
                        self.system_metrics.append(metric)
                    
                    time.sleep(1)
                except Exception:
                    time.sleep(5)
        
        thread = threading.Thread(target=monitor_task, daemon=True)
        thread.start()
    
    def get_system_metrics(self, last_n: int = 60) -> List[Dict]:
        """获取系统指标"""
        with self.lock:
            return list(self.system_metrics)[-last_n:]
    
    def get_current_system_status(self) -> Dict:
        """获取当前系统状态"""
        return {
            'cpu_percent': psutil.cpu_percent(interval=0.1),
            'memory_percent': psutil.virtual_memory().percent,
            'memory_available_mb': psutil.virtual_memory().available / (1024 * 1024),
            'disk_usage_percent': psutil.disk_usage('/').percent,
            'process_memory_mb': psutil.Process().memory_info().rss / (1024 * 1024),
            'thread_count': threading.active_count()
        }


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.collector = MetricsCollector()
        self.alert_thresholds = {
            'response_time_p95_ms': 5000,  # 5秒
            'error_rate_percent': 5.0,      # 5%
            'cpu_percent': 80.0,            # 80%
            'memory_percent': 85.0          # 85%
        }
        self.alerts: deque = deque(maxlen=100)
        self.alert_callbacks: List[Callable] = []
        self.lock = threading.RLock()
        
        # 启动告警检查线程
        self._start_alert_checker()
    
    def record_request(self, endpoint: str, method: str, status_code: int,
                      response_time_ms: float, user_agent: str = "",
                      error_message: str = ""):
        """记录请求"""
        self.collector.record_request(
            endpoint, method, status_code, response_time_ms,
            user_agent, error_message
        )
    
    def set_alert_threshold(self, metric: str, threshold: float):
        """设置告警阈值"""
        self.alert_thresholds[metric] = threshold
    
    def add_alert_callback(self, callback: Callable):
        """添加告警回调"""
        self.alert_callbacks.append(callback)
    
    def _start_alert_checker(self):
        """启动告警检查线程"""
        def check_alerts():
            while True:
                try:
                    self._check_performance_alerts()
                    time.sleep(60)  # 每分钟检查一次
                except Exception:
                    time.sleep(60)
        
        thread = threading.Thread(target=check_alerts, daemon=True)
        thread.start()
    
    def _check_performance_alerts(self):
        """检查性能告警"""
        # 检查响应时间
        for endpoint in self.collector.response_times.keys():
            stats = self.collector.get_response_time_stats(endpoint)
            
            if stats['p95_ms'] > self.alert_thresholds['response_time_p95_ms']:
                self._trigger_alert(
                    'high_response_time',
                    f'端点 {endpoint} P95响应时间过高: {stats["p95_ms"]}ms',
                    {'endpoint': endpoint, 'p95_ms': stats['p95_ms']}
                )
        
        # 检查错误率
        error_rate = self.collector.get_error_rate(time_window_seconds=300)
        if error_rate > self.alert_thresholds['error_rate_percent']:
            self._trigger_alert(
                'high_error_rate',
                f'错误率过高: {error_rate}%',
                {'error_rate': error_rate}
            )
        
        # 检查系统资源
        system_status = self.collector.get_current_system_status()
        
        if system_status['cpu_percent'] > self.alert_thresholds['cpu_percent']:
            self._trigger_alert(
                'high_cpu_usage',
                f'CPU使用率过高: {system_status["cpu_percent"]}%',
                {'cpu_percent': system_status['cpu_percent']}
            )
        
        if system_status['memory_percent'] > self.alert_thresholds['memory_percent']:
            self._trigger_alert(
                'high_memory_usage',
                f'内存使用率过高: {system_status["memory_percent"]}%',
                {'memory_percent': system_status['memory_percent']}
            )
    
    def _trigger_alert(self, alert_type: str, message: str, data: Dict):
        """触发告警"""
        with self.lock:
            alert = {
                'type': alert_type,
                'message': message,
                'data': data,
                'timestamp': time.time()
            }
            
            self.alerts.append(alert)
            
            # 调用回调
            for callback in self.alert_callbacks:
                try:
                    callback(alert)
                except:
                    pass
    
    def get_dashboard_data(self) -> Dict:
        """获取监控面板数据"""
        return {
            'system_status': self.collector.get_current_system_status(),
            'system_metrics': self.collector.get_system_metrics(last_n=60),
            'endpoint_summary': self.collector.get_endpoint_summary(time_window_seconds=3600),
            'error_rate': self.collector.get_error_rate(time_window_seconds=3600),
            'rpm': self.collector.get_rpm(time_window_seconds=60),
            'alerts': list(self.alerts)[-10:],
            'thresholds': self.alert_thresholds
        }
    
    def get_performance_report(self, time_window_hours: int = 24) -> Dict:
        """生成性能报告"""
        window_seconds = time_window_hours * 3600
        
        # 获取所有端点统计
        endpoint_stats = self.collector.get_endpoint_summary(window_seconds)
        
        # 计算总体指标
        total_requests = sum(s['count'] for s in endpoint_stats.values())
        total_errors = sum(s['error_count'] for s in endpoint_stats.values())
        
        # 响应时间统计
        all_response_times = []
        for endpoint in self.collector.response_times.keys():
            stats = self.collector.get_response_time_stats(endpoint, last_n=1000)
            if stats['count'] > 0:
                all_response_times.append(stats['avg_ms'])
        
        return {
            'period_hours': time_window_hours,
            'total_requests': total_requests,
            'total_errors': total_errors,
            'error_rate': round(total_errors / total_requests * 100, 2) if total_requests > 0 else 0,
            'avg_response_time_ms': round(statistics.mean(all_response_times), 2) if all_response_times else 0,
            'endpoint_breakdown': endpoint_stats,
            'top_slow_endpoints': sorted(
                endpoint_stats.items(),
                key=lambda x: x[1]['avg_response_time'],
                reverse=True
            )[:5],
            'top_error_endpoints': sorted(
                endpoint_stats.items(),
                key=lambda x: x[1]['error_count'],
                reverse=True
            )[:5]
        }


# 全局监控实例
performance_monitor = PerformanceMonitor()


# 装饰器用于自动监控
def monitor_performance(endpoint_name: str = None):
    """性能监控装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            endpoint = endpoint_name or func.__name__
            
            try:
                result = func(*args, **kwargs)
                status_code = 200
                error_message = ""
            except Exception as e:
                status_code = 500
                error_message = str(e)
                raise
            finally:
                response_time_ms = (time.time() - start_time) * 1000
                performance_monitor.record_request(
                    endpoint=endpoint,
                    method='INTERNAL',
                    status_code=status_code,
                    response_time_ms=response_time_ms,
                    error_message=error_message
                )
            
            return result
        
        return wrapper
    return decorator


# 便捷函数
def record_request(*args, **kwargs):
    """记录请求"""
    performance_monitor.record_request(*args, **kwargs)


def get_dashboard_data() -> Dict:
    """获取监控面板数据"""
    return performance_monitor.get_dashboard_data()


def get_performance_report(time_window_hours: int = 24) -> Dict:
    """获取性能报告"""
    return performance_monitor.get_performance_report(time_window_hours)


# 测试代码
if __name__ == '__main__':
    print("=" * 60)
    print("性能监控系统测试")
    print("=" * 60)
    
    monitor = PerformanceMonitor()
    
    # 模拟一些请求
    print("\n1. 模拟请求记录")
    for i in range(100):
        monitor.record_request(
            endpoint='/api/chat',
            method='POST',
            status_code=200 if i < 95 else 500,
            response_time_ms=100 + i * 10
        )
    
    # 获取响应时间统计
    print("\n2. 响应时间统计")
    stats = monitor.collector.get_response_time_stats('/api/chat')
    print(f"平均响应时间: {stats['avg_ms']}ms")
    print(f"P95响应时间: {stats['p95_ms']}ms")
    print(f"P99响应时间: {stats['p99_ms']}ms")
    
    # 获取端点汇总
    print("\n3. 端点汇总")
    summary = monitor.collector.get_endpoint_summary()
    for endpoint, data in summary.items():
        print(f"{endpoint}: {data['count']} 请求, {data['error_count']} 错误")
    
    # 获取系统状态
    print("\n4. 系统状态")
    status = monitor.collector.get_current_system_status()
    print(f"CPU使用率: {status['cpu_percent']}%")
    print(f"内存使用率: {status['memory_percent']}%")
    print(f"进程内存: {status['process_memory_mb']:.1f}MB")
    
    # 获取监控面板数据
    print("\n5. 监控面板数据")
    dashboard = monitor.get_dashboard_data()
    print(f"当前RPM: {dashboard['rpm']}")
    print(f"错误率: {dashboard['error_rate']}%")
    
    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)
