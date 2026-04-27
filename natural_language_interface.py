# -*- coding: utf-8 -*-
"""
自然语言查询接口 - Natural Language Query Interface
支持自然语言与知识图谱、数据库和API进行交互
"""

import re
import json
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import threading
from collections import defaultdict


class QueryIntent(Enum):
    """查询意图类型"""
    SEARCH = "search"           # 搜索查询
    FIND_PATH = "find_path"     # 查找路径
    GET_INFO = "get_info"       # 获取信息
    COMPARE = "compare"         # 比较
    AGGREGATE = "aggregate"     # 聚合统计
    RECOMMEND = "recommend"     # 推荐
    UNKNOWN = "unknown"         # 未知


class QueryEntityType(Enum):
    """查询中的实体类型"""
    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    CONCEPT = "concept"
    EVENT = "event"
    PRODUCT = "product"
    TECHNOLOGY = "technology"
    TIME = "time"
    NUMBER = "number"
    UNKNOWN = "unknown"


@dataclass
class ParsedQuery:
    """解析后的查询"""
    original_query: str
    intent: QueryIntent
    entities: List[Dict[str, Any]] = field(default_factory=list)
    relations: List[str] = field(default_factory=list)
    conditions: List[Dict[str, Any]] = field(default_factory=list)
    attributes: List[str] = field(default_factory=list)
    time_range: Optional[Dict[str, datetime]] = None
    confidence: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "original_query": self.original_query,
            "intent": self.intent.value,
            "entities": self.entities,
            "relations": self.relations,
            "conditions": self.conditions,
            "attributes": self.attributes,
            "time_range": self.time_range,
            "confidence": self.confidence
        }


@dataclass
class QueryResult:
    """查询结果"""
    success: bool
    data: Any
    query_type: str
    execution_time_ms: float
    message: str = ""
    suggestions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "data": self.data,
            "query_type": self.query_type,
            "execution_time_ms": self.execution_time_ms,
            "message": self.message,
            "suggestions": self.suggestions
        }


class QueryParser:
    """自然语言查询解析器"""
    
    # 意图关键词映射
    INTENT_PATTERNS = {
        QueryIntent.SEARCH: [
            r'查找|搜索|查询|找一下?|有没有|在哪里|是什么',
            r'find|search|look for|where is|what is',
        ],
        QueryIntent.FIND_PATH: [
            r'.*和.*的关系|.*到.*的路径|.*怎么到.*|.*如何连接.*',
            r'relationship between|path from.*to|how to get from',
        ],
        QueryIntent.GET_INFO: [
            r'告诉我|介绍|说明|什么是|详细信息|属性',
            r'tell me about|introduce|explain|details of',
        ],
        QueryIntent.COMPARE: [
            r'比较|对比|区别|差异|vs|versus',
            r'compare|difference between|vs|versus',
        ],
        QueryIntent.AGGREGATE: [
            r'统计|总数|平均|最大|最小|多少|数量',
            r'count|total|average|max|min|how many',
        ],
        QueryIntent.RECOMMEND: [
            r'推荐|建议|类似的|相关的|像.*一样',
            r'recommend|suggest|similar to|like|related to',
        ],
    }
    
    # 实体类型识别模式
    ENTITY_PATTERNS = {
        QueryEntityType.PERSON: [
            r'[\u4e00-\u9fa5]{2,4}(?:先生|女士|博士|教授|经理|总监|工程师)',
            r'[A-Z][a-z]+\s+[A-Z][a-z]+',
        ],
        QueryEntityType.ORGANIZATION: [
            r'[\u4e00-\u9fa5]+(?:公司|集团|企业|机构|协会|大学|学院)',
            r'[A-Z][a-zA-Z]*\s*(?:Inc|Corp|Ltd|Company|University|Institute)',
        ],
        QueryEntityType.LOCATION: [
            r'[\u4e00-\u9fa5]+(?:省|市|区|县|镇|街道)',
            r'(?:北京|上海|广州|深圳|杭州|南京|成都|武汉|西安|重庆)',
        ],
        QueryEntityType.TIME: [
            r'\d{4}年(?:\d{1,2}月)?(?:\d{1,2}日)?',
            r'(?:19|20)\d{2}(?:-\d{2})?(?:-\d{2})?',
            r'最近|去年|今年|明年|上个月|下个月',
        ],
        QueryEntityType.NUMBER: [
            r'\d+(?:\.\d+)?(?:\s*(?:个|条|件|次|倍|%|percent))?',
        ],
    }
    
    # 关系关键词
    RELATION_KEYWORDS = {
        'belongs_to': ['属于', '隶属于', '归属', '是.*的成员', 'belongs to', 'member of'],
        'created_by': ['创建', '创立', '创办', '开发', 'created by', 'founded by', 'developed by'],
        'located_in': ['位于', '在', '坐落于', '总部在', 'located in', 'based in'],
        'contains': ['包含', '包括', '拥有', 'consists of', 'contains', 'includes'],
        'related_to': ['相关', '有关', '涉及', 'related to', 'associated with'],
        'depends_on': ['依赖', '依靠', '基于', 'depends on', 'relies on', 'based on'],
        'part_of': ['部分', '组成', '一部分', 'part of', 'component of'],
    }
    
    def __init__(self):
        self._compile_patterns()
    
    def _compile_patterns(self):
        """编译正则表达式"""
        self._intent_patterns = {}
        for intent, patterns in self.INTENT_PATTERNS.items():
            self._intent_patterns[intent] = [re.compile(p, re.IGNORECASE) for p in patterns]
        
        self._entity_patterns = {}
        for entity_type, patterns in self.ENTITY_PATTERNS.items():
            self._entity_patterns[entity_type] = [re.compile(p) for p in patterns]
    
    def parse(self, query: str) -> ParsedQuery:
        """解析自然语言查询"""
        parsed = ParsedQuery(
            original_query=query,
            intent=self._detect_intent(query),
            entities=self._extract_entities(query),
            relations=self._extract_relations(query),
            conditions=self._extract_conditions(query),
            attributes=self._extract_attributes(query),
            time_range=self._extract_time_range(query),
            confidence=0.0
        )
        
        # 计算置信度
        parsed.confidence = self._calculate_confidence(parsed)
        
        return parsed
    
    def _detect_intent(self, query: str) -> QueryIntent:
        """检测查询意图"""
        scores = defaultdict(int)
        
        for intent, patterns in self._intent_patterns.items():
            for pattern in patterns:
                if pattern.search(query):
                    scores[intent] += 1
        
        if scores:
            return max(scores, key=scores.get)
        return QueryIntent.UNKNOWN
    
    def _extract_entities(self, query: str) -> List[Dict[str, Any]]:
        """提取查询中的实体"""
        entities = []
        found_spans = set()
        
        for entity_type, patterns in self._entity_patterns.items():
            for pattern in patterns:
                for match in pattern.finditer(query):
                    span = match.span()
                    # 避免重叠
                    if not any(span[0] < end and span[1] > start for start, end in found_spans):
                        entities.append({
                            "text": match.group(),
                            "type": entity_type.value,
                            "start": span[0],
                            "end": span[1]
                        })
                        found_spans.add(span)
        
        # 按位置排序
        entities.sort(key=lambda x: x["start"])
        return entities
    
    def _extract_relations(self, query: str) -> List[str]:
        """提取关系关键词"""
        relations = []
        
        for rel_type, keywords in self.RELATION_KEYWORDS.items():
            for keyword in keywords:
                if keyword in query.lower():
                    relations.append(rel_type)
                    break
        
        return relations
    
    def _extract_conditions(self, query: str) -> List[Dict[str, Any]]:
        """提取查询条件"""
        conditions = []
        
        # 比较条件
        comparison_patterns = [
            (r'大于|超过|多于|>|greater than|more than', 'gt'),
            (r'小于|少于|低于|<|less than|fewer than', 'lt'),
            (r'等于|是|等于|=|equal to', 'eq'),
            (r'包含|含有|包括|contains|includes', 'contains'),
        ]
        
        for pattern, op in comparison_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                # 尝试提取数值
                number_match = re.search(r'\d+(?:\.\d+)?', query)
                if number_match:
                    conditions.append({
                        "operator": op,
                        "value": float(number_match.group()),
                        "type": "comparison"
                    })
        
        return conditions
    
    def _extract_attributes(self, query: str) -> List[str]:
        """提取属性关键词"""
        attributes = []
        
        attr_keywords = {
            'name': ['名称', '名字', 'name', 'title'],
            'description': ['描述', '介绍', '说明', 'description', 'about'],
            'date': ['日期', '时间', 'date', 'time', 'when'],
            'location': ['位置', '地点', '地址', 'location', 'where'],
            'status': ['状态', '情况', 'status', 'state'],
        }
        
        for attr, keywords in attr_keywords.items():
            if any(kw in query.lower() for kw in keywords):
                attributes.append(attr)
        
        return attributes
    
    def _extract_time_range(self, query: str) -> Optional[Dict[str, datetime]]:
        """提取时间范围"""
        time_range = {}
        
        # 年份范围
        year_pattern = r'(\d{4})(?:\s*[-至到]\s*(\d{4}))?'
        match = re.search(year_pattern, query)
        if match:
            start_year = int(match.group(1))
            end_year = int(match.group(2)) if match.group(2) else start_year
            time_range['start'] = datetime(start_year, 1, 1)
            time_range['end'] = datetime(end_year, 12, 31)
        
        # 相对时间
        if '最近' in query or 'recent' in query.lower():
            time_range['start'] = datetime.now() - __import__('datetime').timedelta(days=30)
            time_range['end'] = datetime.now()
        
        return time_range if time_range else None
    
    def _calculate_confidence(self, parsed: ParsedQuery) -> float:
        """计算解析置信度"""
        score = 0.0
        
        # 意图识别得分
        if parsed.intent != QueryIntent.UNKNOWN:
            score += 0.3
        
        # 实体提取得分
        if parsed.entities:
            score += min(0.3, len(parsed.entities) * 0.1)
        
        # 关系提取得分
        if parsed.relations:
            score += 0.2
        
        # 条件提取得分
        if parsed.conditions:
            score += 0.1
        
        # 属性提取得分
        if parsed.attributes:
            score += 0.1
        
        return min(1.0, score)


class NaturalLanguageQueryEngine:
    """自然语言查询引擎"""
    
    def __init__(self):
        self.parser = QueryParser()
        self._handlers: Dict[QueryIntent, Callable] = {}
        self._lock = threading.RLock()
        self._query_history: List[Dict] = []
        
        # 注册默认处理器
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """注册默认查询处理器"""
        self._handlers[QueryIntent.SEARCH] = self._handle_search
        self._handlers[QueryIntent.FIND_PATH] = self._handle_find_path
        self._handlers[QueryIntent.GET_INFO] = self._handle_get_info
        self._handlers[QueryIntent.COMPARE] = self._handle_compare
        self._handlers[QueryIntent.AGGREGATE] = self._handle_aggregate
        self._handlers[QueryIntent.RECOMMEND] = self._handle_recommend
    
    def register_handler(self, intent: QueryIntent, handler: Callable):
        """注册自定义查询处理器"""
        with self._lock:
            self._handlers[intent] = handler
    
    def execute(self, query: str, context: Optional[Dict] = None) -> QueryResult:
        """执行自然语言查询"""
        start_time = datetime.now()
        
        try:
            # 解析查询
            parsed = self.parser.parse(query)
            
            # 记录查询历史
            self._query_history.append({
                "query": query,
                "parsed": parsed.to_dict(),
                "timestamp": datetime.now().isoformat()
            })
            
            # 获取处理器
            handler = self._handlers.get(parsed.intent, self._handle_unknown)
            
            # 执行查询
            result_data = handler(parsed, context or {})
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return QueryResult(
                success=True,
                data=result_data,
                query_type=parsed.intent.value,
                execution_time_ms=execution_time,
                message=f"查询成功 (置信度: {parsed.confidence:.2f})"
            )
        
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return QueryResult(
                success=False,
                data=None,
                query_type="error",
                execution_time_ms=execution_time,
                message=f"查询失败: {str(e)}",
                suggestions=self._generate_suggestions(query)
            )
    
    def _handle_search(self, parsed: ParsedQuery, context: Dict) -> Dict:
        """处理搜索查询"""
        results = {
            "entities": [],
            "relations": [],
            "total_count": 0
        }
        
        # 从知识图谱搜索
        if 'knowledge_graph' in context:
            kg = context['knowledge_graph']
            search_results = kg.search(
                query=parsed.original_query,
                limit=context.get('limit', 20)
            )
            results['entities'] = search_results.get('entities', [])
            results['relations'] = search_results.get('relations', [])
            results['total_count'] = len(results['entities']) + len(results['relations'])
        
        return results
    
    def _handle_find_path(self, parsed: ParsedQuery, context: Dict) -> Dict:
        """处理路径查找查询"""
        results = {
            "paths": [],
            "entities": []
        }
        
        if len(parsed.entities) >= 2 and 'knowledge_graph' in context:
            kg = context['knowledge_graph']
            
            # 查找实体
            source_entities = kg.find_entities_by_name(parsed.entities[0]['text'])
            target_entities = kg.find_entities_by_name(parsed.entities[1]['text'])
            
            if source_entities and target_entities:
                # 查找路径
                paths = kg.find_all_paths(
                    source_entities[0].id,
                    target_entities[0].id,
                    max_depth=context.get('max_depth', 5),
                    max_paths=context.get('max_paths', 5)
                )
                
                results['paths'] = [p.to_dict() for p in paths]
                results['entities'] = [
                    source_entities[0].to_dict(),
                    target_entities[0].to_dict()
                ]
        
        return results
    
    def _handle_get_info(self, parsed: ParsedQuery, context: Dict) -> Dict:
        """处理信息获取查询"""
        results = {
            "entity": None,
            "relations": [],
            "neighbors": [],
            "attributes": {}
        }
        
        if parsed.entities and 'knowledge_graph' in context:
            kg = context['knowledge_graph']
            entity_name = parsed.entities[0]['text']
            
            # 查找实体
            entities = kg.find_entities_by_name(entity_name)
            if entities:
                entity = entities[0]
                results['entity'] = entity.to_dict()
                
                # 获取关系
                relations = kg.get_entity_relations(entity.id, "both")
                results['relations'] = [r.to_dict() for r in relations]
                
                # 获取邻居
                neighbors = kg.get_neighbors(entity.id, "both")
                results['neighbors'] = [n.to_dict() for n in neighbors]
                
                # 提取指定属性
                if parsed.attributes:
                    for attr in parsed.attributes:
                        if attr in entity.properties:
                            results['attributes'][attr] = entity.properties[attr]
        
        return results
    
    def _handle_compare(self, parsed: ParsedQuery, context: Dict) -> Dict:
        """处理比较查询"""
        results = {
            "entities": [],
            "comparison": {},
            "similarities": [],
            "differences": []
        }
        
        if len(parsed.entities) >= 2 and 'knowledge_graph' in context:
            kg = context['knowledge_graph']
            
            entities = []
            for entity_data in parsed.entities[:2]:
                found = kg.find_entities_by_name(entity_data['text'])
                if found:
                    entities.append(found[0])
            
            if len(entities) == 2:
                results['entities'] = [e.to_dict() for e in entities]
                
                # 比较属性
                props1 = set(entities[0].properties.keys())
                props2 = set(entities[1].properties.keys())
                
                results['comparison'] = {
                    "common_properties": list(props1 & props2),
                    "unique_to_first": list(props1 - props2),
                    "unique_to_second": list(props2 - props1)
                }
                
                # 查找相似度
                if hasattr(kg, 'find_similar_entities'):
                    similar = kg.find_similar_entities(entities[0].id, top_k=10)
                    for ent, score in similar:
                        if ent.id == entities[1].id:
                            results['similarities'].append({
                                "metric": "structural_similarity",
                                "score": score
                            })
        
        return results
    
    def _handle_aggregate(self, parsed: ParsedQuery, context: Dict) -> Dict:
        """处理聚合查询"""
        results = {
            "statistics": {},
            "aggregations": {}
        }
        
        if 'knowledge_graph' in context:
            kg = context['knowledge_graph']
            
            # 获取基本统计
            results['statistics'] = kg.get_statistics()
            
            # 计算中心性
            if 'centrality' in parsed.attributes:
                results['aggregations']['centrality'] = kg.calculate_centrality('degree')
            
            # 社区发现
            if 'communities' in parsed.attributes:
                communities = kg.find_communities('greedy')
                results['aggregations']['communities'] = [
                    {"id": i, "size": len(c), "members": list(c)}
                    for i, c in enumerate(communities)
                ]
        
        return results
    
    def _handle_recommend(self, parsed: ParsedQuery, context: Dict) -> Dict:
        """处理推荐查询"""
        results = {
            "recommendations": [],
            "based_on": None
        }
        
        if parsed.entities and 'knowledge_graph' in context:
            kg = context['knowledge_graph']
            entity_name = parsed.entities[0]['text']
            
            # 查找基准实体
            entities = kg.find_entities_by_name(entity_name)
            if entities:
                entity = entities[0]
                results['based_on'] = entity.to_dict()
                
                # 查找相似实体
                similar = kg.find_similar_entities(
                    entity.id,
                    top_k=context.get('top_k', 5)
                )
                
                results['recommendations'] = [
                    {
                        "entity": ent.to