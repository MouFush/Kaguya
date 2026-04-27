#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高级数据分析模块 - 深度数据洞察与处理
功能: 数据清洗、统计分析、趋势预测、异常检测
"""

import json
import re
import math
import statistics
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import csv
import io


@dataclass
class DataAnalysisResult:
    """数据分析结果"""
    success: bool
    data: Any
    insights: List[str] = field(default_factory=list)
    visualizations: List[Dict] = field(default_factory=list)
    error: Optional[str] = None
    execution_time: float = 0.0


class DataCleaner:
    """数据清洗器"""
    
    def clean_dataset(self, data: List[Dict], options: Dict = None) -> Dict:
        """
        清洗数据集
        
        Args:
            data: 原始数据列表
            options: 清洗选项
            
        Returns:
            清洗后的数据和统计信息
        """
        options = options or {}
        remove_duplicates = options.get('remove_duplicates', True)
        fill_missing = options.get('fill_missing', 'auto')
        remove_outliers = options.get('remove_outliers', False)
        
        result = {
            'original_count': len(data),
            'cleaned_count': 0,
            'removed_duplicates': 0,
            'filled_missing': 0,
            'removed_outliers': 0,
            'cleaned_data': [],
            'quality_score': 0.0
        }
        
        if not data:
            return result
        
        cleaned = data.copy()
        
        # 1. 移除重复项
        if remove_duplicates:
            original_len = len(cleaned)
            seen = set()
            unique_data = []
            for item in cleaned:
                item_hash = json.dumps(item, sort_keys=True)
                if item_hash not in seen:
                    seen.add(item_hash)
                    unique_data.append(item)
            cleaned = unique_data
            result['removed_duplicates'] = original_len - len(cleaned)
        
        # 2. 处理缺失值
        if fill_missing:
            filled_count = 0
            for item in cleaned:
                for key, value in item.items():
                    if value is None or value == '' or value == 'null':
                        if fill_missing == 'auto':
                            # 智能填充
                            item[key] = self._smart_fill(cleaned, key)
                        elif fill_missing == 'zero':
                            item[key] = 0 if isinstance(value, (int, float)) else ''
                        elif fill_missing == 'mean':
                            item[key] = self._calculate_mean(cleaned, key)
                        filled_count += 1
            result['filled_missing'] = filled_count
        
        # 3. 移除异常值
        if remove_outliers:
            original_len = len(cleaned)
            cleaned = self._remove_outliers(cleaned)
            result['removed_outliers'] = original_len - len(cleaned)
        
        result['cleaned_data'] = cleaned
        result['cleaned_count'] = len(cleaned)
        
        # 4. 计算数据质量分数
        result['quality_score'] = self._calculate_quality_score(data, cleaned)
        
        return result
    
    def _smart_fill(self, data: List[Dict], column: str) -> Any:
        """智能填充缺失值"""
        values = [item[column] for item in data if item.get(column) is not None]
        if not values:
            return ''
        
        # 判断数据类型
        if all(isinstance(v, (int, float)) for v in values):
            return statistics.mean(values)
        elif all(isinstance(v, str) for v in values):
            # 返回最常见的值
            return Counter(values).most_common(1)[0][0]
        else:
            return values[0]
    
    def _calculate_mean(self, data: List[Dict], column: str) -> float:
        """计算列平均值"""
        values = [item[column] for item in data if isinstance(item.get(column), (int, float))]
        return statistics.mean(values) if values else 0
    
    def _remove_outliers(self, data: List[Dict], threshold: float = 3.0) -> List[Dict]:
        """使用IQR方法移除异常值"""
        if not data:
            return data
        
        # 找出数值列
        numeric_columns = []
        for key in data[0].keys():
            if all(isinstance(item.get(key), (int, float)) for item in data if item.get(key) is not None):
                numeric_columns.append(key)
        
        cleaned = []
        for item in data:
            is_outlier = False
            for col in numeric_columns:
                value = item.get(col)
                if value is not None:
                    values = [i[col] for i in data if i.get(col) is not None]
                    q1 = statistics.quantiles(values, n=4)[0]
                    q3 = statistics.quantiles(values, n=4)[2]
                    iqr = q3 - q1
                    lower_bound = q1 - threshold * iqr
                    upper_bound = q3 + threshold * iqr
                    if value < lower_bound or value > upper_bound:
                        is_outlier = True
                        break
            if not is_outlier:
                cleaned.append(item)
        
        return cleaned
    
    def _calculate_quality_score(self, original: List[Dict], cleaned: List[Dict]) -> float:
        """计算数据质量分数"""
        if not original:
            return 0.0
        
        completeness = len(cleaned) / len(original)
        
        # 检查完整性
        total_fields = sum(len(item) for item in original)
        filled_fields = sum(sum(1 for v in item.values() if v is not None and v != '') for item in original)
        fill_rate = filled_fields / total_fields if total_fields > 0 else 0
        
        score = (completeness * 0.5 + fill_rate * 0.5) * 100
        return round(score, 2)


class StatisticalAnalyzer:
    """统计分析器"""
    
    def analyze_dataset(self, data: List[Dict], target_column: Optional[str] = None) -> Dict:
        """
        对数据集进行全面的统计分析
        
        Args:
            data: 数据集
            target_column: 目标分析列
            
        Returns:
            统计分析结果
        """
        if not data:
            return {'error': '数据集为空'}
        
        result = {
            'overview': self._generate_overview(data),
            'columns': {},
            'correlations': {},
            'insights': []
        }
        
        # 分析每一列
        for column in data[0].keys():
            result['columns'][column] = self._analyze_column(data, column)
        
        # 计算相关性
        result['correlations'] = self._calculate_correlations(data)
        
        # 生成洞察
        result['insights'] = self._generate_insights(data, result)
        
        return result
    
    def _generate_overview(self, data: List[Dict]) -> Dict:
        """生成数据概览"""
        return {
            'total_rows': len(data),
            'total_columns': len(data[0]) if data else 0,
            'memory_usage': len(json.dumps(data)),
            'analysis_time': datetime.now().isoformat()
        }
    
    def _analyze_column(self, data: List[Dict], column: str) -> Dict:
        """分析单列数据"""
        values = [item[column] for item in data if item.get(column) is not None]
        
        if not values:
            return {'type': 'empty', 'count': 0}
        
        # 判断数据类型
        if all(isinstance(v, (int, float)) for v in values):
            return self._analyze_numeric_column(values, column)
        elif all(isinstance(v, str) for v in values):
            return self._analyze_text_column(values, column)
        else:
            return {'type': 'mixed', 'count': len(values)}
    
    def _analyze_numeric_column(self, values: List[float], column: str) -> Dict:
        """分析数值列"""
        result = {
            'type': 'numeric',
            'count': len(values),
            'mean': statistics.mean(values),
            'median': statistics.median(values),
            'std': statistics.stdev(values) if len(values) > 1 else 0,
            'min': min(values),
            'max': max(values),
            'range': max(values) - min(values),
            'quartiles': {
                'q1': statistics.quantiles(values, n=4)[0] if len(values) >= 4 else values[0],
                'q2': statistics.median(values),
                'q3': statistics.quantiles(values, n=4)[2] if len(values) >= 4 else values[-1]
            }
        }
        
        # 计算变异系数
        if result['mean'] != 0:
            result['cv'] = result['std'] / abs(result['mean'])
        
        return result
    
    def _analyze_text_column(self, values: List[str], column: str) -> Dict:
        """分析文本列"""
        lengths = [len(str(v)) for v in values]
        
        result = {
            'type': 'text',
            'count': len(values),
            'unique_count': len(set(values)),
            'most_common': Counter(values).most_common(5),
            'avg_length': statistics.mean(lengths),
            'min_length': min(lengths),
            'max_length': max(lengths)
        }
        
        # 计算唯一值比例
        result['uniqueness_ratio'] = result['unique_count'] / result['count'] if result['count'] > 0 else 0
        
        return result
    
    def _calculate_correlations(self, data: List[Dict]) -> Dict:
        """计算列间相关性"""
        # 找出数值列
        numeric_columns = []
        for column in data[0].keys():
            if all(isinstance(item.get(column), (int, float)) for item in data if item.get(column) is not None):
                numeric_columns.append(column)
        
        correlations = {}
        
        for i, col1 in enumerate(numeric_columns):
            for col2 in numeric_columns[i+1:]:
                values1 = [item[col1] for item in data if item.get(col1) is not None and item.get(col2) is not None]
                values2 = [item[col2] for item in data if item.get(col1) is not None and item.get(col2) is not None]
                
                if len(values1) > 1:
                    correlation = self._pearson_correlation(values1, values2)
                    correlations[f"{col1}_vs_{col2}"] = correlation
        
        return correlations
    
    def _pearson_correlation(self, x: List[float], y: List[float]) -> float:
        """计算皮尔逊相关系数"""
        n = len(x)
        if n != len(y) or n == 0:
            return 0.0
        
        mean_x = statistics.mean(x)
        mean_y = statistics.mean(y)
        
        numerator = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
        denominator = math.sqrt(sum((xi - mean_x) ** 2 for xi in x) * sum((yi - mean_y) ** 2 for yi in y))
        
        if denominator == 0:
            return 0.0
        
        return numerator / denominator
    
    def _generate_insights(self, data: List[Dict], analysis: Dict) -> List[str]:
        """生成数据洞察"""
        insights = []
        
        # 基于数值列的洞察
        for col, stats in analysis['columns'].items():
            if stats.get('type') == 'numeric':
                # 检测偏态
                if stats['mean'] > stats['median'] * 1.2:
                    insights.append(f"📊 {col}: 数据呈右偏分布，存在较大值")
                elif stats['mean'] < stats['median'] * 0.8:
                    insights.append(f"📊 {col}: 数据呈左偏分布，存在较小值")
                
                # 检测高变异性
                if stats.get('cv', 0) > 1:
                    insights.append(f"⚠️ {col}: 数据变异系数高({stats['cv']:.2f})，波动性大")
                
                # 检测异常范围
                if stats['max'] - stats['min'] > stats['std'] * 6:
                    insights.append(f"🔍 {col}: 数据范围异常宽，建议检查异常值")
            
            elif stats.get('type') == 'text':
                # 检测低唯一性
                if stats.get('uniqueness_ratio', 1) < 0.1:
                    insights.append(f"📝 {col}: 唯一值比例低({stats['uniqueness_ratio']:.1%})，可能是分类字段")
        
        # 基于相关性的洞察
        for pair, corr in analysis['correlations'].items():
            if abs(corr) > 0.8:
                strength = "强" if abs(corr) > 0.9 else "中等"
                direction = "正" if corr > 0 else "负"
                insights.append(f"🔗 {pair}: 存在{strength}{direction}相关({corr:.2f})")
        
        return insights


class TrendAnalyzer:
    """趋势分析器"""
    
    def analyze_trends(self, data: List[Dict], time_column: str, value_column: str) -> Dict:
        """
        分析时间序列趋势
        
        Args:
            data: 时间序列数据
            time_column: 时间列名
            value_column: 数值列名
            
        Returns:
            趋势分析结果
        """
        if not data:
            return {'error': '数据为空'}
        
        # 按时间排序
        sorted_data = sorted(data, key=lambda x: x.get(time_column, ''))
        
        values = [item[value_column] for item in sorted_data if isinstance(item.get(value_column), (int, float))]
        
        if len(values) < 2:
            return {'error': '数据点不足'}
        
        result = {
            'overall_trend': self._calculate_overall_trend(values),
            'trend_strength': 0.0,
            'seasonality': self._detect_seasonality(values),
            'forecast': self._simple_forecast(values),
            'change_points': self._detect_change_points(values)
        }
        
        # 计算趋势强度
        result['trend_strength'] = abs(result['overall_trend']['slope'] / (statistics.stdev(values) if len(values) > 1 else 1))
        
        return result
    
    def _calculate_overall_trend(self, values: List[float]) -> Dict:
        """计算整体趋势"""
        n = len(values)
        x = list(range(n))
        
        # 简单线性回归
        mean_x = statistics.mean(x)
        mean_y = statistics.mean(values)
        
        numerator = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, values))
        denominator = sum((xi - mean_x) ** 2 for xi in x)
        
        slope = numerator / denominator if denominator != 0 else 0
        intercept = mean_y - slope * mean_x
        
        # 计算R²
        ss_res = sum((yi - (slope * xi + intercept)) ** 2 for xi, yi in zip(x, values))
        ss_tot = sum((yi - mean_y) ** 2 for yi in values)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
        
        trend_direction = "上升" if slope > 0 else "下降" if slope < 0 else "平稳"
        
        return {
            'slope': slope,
            'intercept': intercept,
            'r_squared': r_squared,
            'direction': trend_direction,
            'change_rate': slope / mean_y if mean_y != 0 else 0
        }
    
    def _detect_seasonality(self, values: List[float]) -> Dict:
        """检测季节性"""
        if len(values) < 4:
            return {'has_seasonality': False}
        
        # 简单季节性检测：检查周期性模式
        diffs = [values[i] - values[i-1] for i in range(1, len(values))]
        
        # 如果差分符号频繁变化，可能存在季节性
        sign_changes = sum(1 for i in range(1, len(diffs)) if diffs[i] * diffs[i-1] < 0)
        seasonality_score = sign_changes / len(diffs) if diffs else 0
        
        return {
            'has_seasonality': seasonality_score > 0.3,
            'seasonality_score': seasonality_score,
            'period': None  # 需要更复杂的算法检测周期
        }
    
    def _simple_forecast(self, values: List[float], periods: int = 3) -> List[float]:
        """简单预测"""
        if len(values) < 2:
            return values
        
        # 使用移动平均和趋势
        trend = self._calculate_overall_trend(values)
        n = len(values)
        
        forecast = []
        for i in range(periods):
            next_value = trend['slope'] * (n + i) + trend['intercept']
            forecast.append(round(next_value, 2))
        
        return forecast
    
    def _detect_change_points(self, values: List[float]) -> List[int]:
        """检测变化点"""
        if len(values) < 3:
            return []
        
        change_points = []
        window_size = max(3, len(values) // 10)
        
        for i in range(window_size, len(values) - window_size):
            before = values[i-window_size:i]
            after = values[i:i+window_size]
            
            before_mean = statistics.mean(before)
            after_mean = statistics.mean(after)
            
            # 如果变化超过2个标准差，认为是变化点
            std = statistics.stdev(values) if len(values) > 1 else 1
            if abs(after_mean - before_mean) > 2 * std:
                change_points.append(i)
        
        return change_points


class AdvancedDataAnalytics:
    """高级数据分析主类"""
    
    def __init__(self):
        self.cleaner = DataCleaner()
        self.statistical_analyzer = StatisticalAnalyzer()
        self.trend_analyzer = TrendAnalyzer()
    
    def comprehensive_analysis(self, data: List[Dict], options: Dict = None) -> DataAnalysisResult:
        """
        综合分析数据集
        
        Args:
            data: 数据集
            options: 分析选项
            
        Returns:
            综合分析结果
        """
        import time
        start_time = time.time()
        
        try:
            result = {
                'data_cleaning': None,
                'statistical_analysis': None,
                'trend_analysis': None,
                'recommendations': []
            }
            
            # 1. 数据清洗
            if options.get('clean_data', True):
                result['data_cleaning'] = self.cleaner.clean_dataset(data, options.get('cleaning_options'))
                data = result['data_cleaning']['cleaned_data']
            
            # 2. 统计分析
            if options.get('statistical_analysis', True):
                result['statistical_analysis'] = self.statistical_analyzer.analyze_dataset(
                    data, 
                    options.get('target_column')
                )
            
            # 3. 趋势分析（如果有时间列）
            time_column = options.get('time_column')
            value_column = options.get('value_column')
            if time_column and value_column:
                result['trend_analysis'] = self.trend_analyzer.analyze_trends(
                    data, time_column, value_column
                )
            
            # 4. 生成建议
            result['recommendations'] = self._generate_recommendations(result)
            
            execution_time = time.time() - start_time
            
            return DataAnalysisResult(
                success=True,
                data=result,
                insights=result['statistical_analysis'].get('insights', []) if result['statistical_analysis'] else [],
                execution_time=execution_time
            )
            
        except Exception as e:
            return DataAnalysisResult(
                success=False,
                data=None,
                error=str(e),
                execution_time=time.time() - start_time
            )
    
    def _generate_recommendations(self, analysis: Dict) -> List[str]:
        """生成分析建议"""
        recommendations = []
        
        # 基于数据清洗的建议
        cleaning = analysis.get('data_cleaning')
        if cleaning:
            if cleaning.get('removed_duplicates', 0) > 0:
                recommendations.append(f"🧹 移除了 {cleaning['removed_duplicates']} 条重复数据")
            if cleaning.get('quality_score', 100) < 80:
                recommendations.append(f"⚠️ 数据质量分数较低({cleaning['quality_score']}%)，建议进一步清洗")
        
        # 基于统计分析的建议
        stats = analysis.get('statistical_analysis')
        if stats:
            insights = stats.get('insights', [])
            for insight in insights[:3]:  # 只取前3个
                recommendations.append(insight)
        
        # 基于趋势分析的建议
        trends = analysis.get('trend_analysis')
        if trends:
            if trends.get('overall_trend', {}).get('direction') == '上升':
                recommendations.append("📈 数据呈上升趋势，建议关注增长因素")
            elif trends.get('overall_trend', {}).get('direction') == '下降':
                recommendations.append("📉 数据呈下降趋势，建议分析原因并采取措施")
            
            if trends.get('seasonality', {}).get('has_seasonality'):
                recommendations.append("🔄 检测到季节性模式，建议考虑季节性因素")
        
        return recommendations


# 全局实例
advanced_analytics = AdvancedDataAnalytics()


# 便捷函数
def analyze_data(data: List[Dict], **options) -> DataAnalysisResult:
    """数据分析便捷函数"""
    return advanced_analytics.comprehensive_analysis(data, options)


def clean_data(data: List[Dict], **options) -> Dict:
    """数据清洗便捷函数"""
    return advanced_analytics.cleaner.clean_dataset(data, options)


def analyze_trends(data: List[Dict], time_column: str, value_column: str) -> Dict:
    """趋势分析便捷函数"""
    return advanced_analytics.trend_analyzer.analyze_trends(data, time_column, value_column)


# 测试代码
if __name__ == '__main__':
    print("=" * 60)
    print("高级数据分析模块测试")
    print("=" * 60)
    
    # 测试数据
    test_data = [
        {'date': '2024-01-01', 'sales': 100, 'customers': 50, 'region': 'North'},
        {'date': '2024-01-02', 'sales': 120, 'customers': 55, 'region': 'North'},
        {'date': '2024-01-03', 'sales': 95, 'customers': 48, 'region': 'South'},
        {'date': '2024-01-04', 'sales': 130, 'customers': 60, 'region': 'North'},
        {'date': '2024-01-05', 'sales': 110, 'customers': 52, 'region': 'South'},
        {'date': '2024-01-06', 'sales': None, 'customers': 58, 'region': 'North'},
        {'date': '2024-01-07', 'sales': 140, 'customers': 65, 'region': 'South'},
    ]
    
    # 测试数据清洗
    print("\n1. 数据清洗测试")
    cleaned = clean_data(test_data, remove_duplicates=True, fill_missing='auto')
    print(f"原始数据: {cleaned['original_count']} 条")
    print(f"清洗后: {cleaned['cleaned_count']} 条")
    print(f"质量分数: {cleaned['quality_score']}")
    
    # 测试综合分析
    print("\n2. 综合分析测试")
    result = analyze_data(
        test_data,
        clean_data=True,
        statistical_analysis=True,
        time_column='date',
        value_column='sales'
    )
    
    if result.success:
        print(f"分析成功，耗时: {result.execution_time:.2f}s")
        print(f"洞察数量: {len(result.insights)}")
        print("\n洞察:")
        for insight in result.insights[:3]:
            print(f"  - {insight}")
        
        print("\n建议:")
        for rec in result.data.get('recommendations', [])[:3]:
            print(f"  - {rec}")
    else:
        print(f"分析失败: {result.error}")
    
    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)
