# -*- coding: utf-8 -*-
"""
智能知识图谱系统 - Intelligent Knowledge Graph System
构建实体关系网络，支持智能推理和知识发现
"""

import json
import re
import math
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set, Callable
from dataclasses import dataclass, field, asdict
from collections import defaultdict
from enum import Enum
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import heapq


class EntityType(Enum):
    """实体类型枚举"""
    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    CONCEPT = "concept"
    EVENT = "event"
    PRODUCT = "product"
    TECHNOLOGY = "technology"
    DOCUMENT = "document"
    CUSTOM = "custom"


class RelationType(Enum):
    """关系类型枚举"""
    BELONGS_TO = "belongs_to"
    CONTAINS = "contains"
    RELATED_TO = "related_to"
    CREATED_BY = "created_by"
    LOCATED_IN = "located_in"
    PART_OF = "part_of"
    DEPENDS_ON = "depends_on"
    SIMILAR_TO = "similar_to"
    PRECEDES = "precedes"
    FOLLOWS = "follows"
    CUSTOM = "custom"


@dataclass
class Entity:
    """知识图谱实体"""
    id: str
    name: str
    entity_type: EntityType
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    confidence: float = 1.0
    source: str = ""
    
    def __hash__(self):
        return hash(self.id)
    
    def __eq__(self, other):
        if isinstance(other, Entity):
            return self.id == other.id
        return False
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "entity_type": self.entity_type.value,
            "properties": self.properties,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "confidence": self.confidence,
            "source": self.source
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Entity':
        return cls(
            id=data["id"],
            name=data["name"],
            entity_type=EntityType(data["entity_type"]),
            properties=data.get("properties", {}),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            confidence=data.get("confidence", 1.0),
            source=data.get("source", "")
        )


@dataclass
class Relation:
    """知识图谱关系"""
    id: str
    source_id: str
    target_id: str
    relation_type: RelationType
    properties: Dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0
    created_at: datetime = field(default_factory=datetime.now)
    confidence: float = 1.0
    bidirectional: bool = False
    
    def __hash__(self):
        return hash(self.id)
    
    def __eq__(self, other):
        if isinstance(other, Relation):
            return self.id == other.id
        return False
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type.value,
            "properties": self.properties,
            "weight": self.weight,
            "created_at": self.created_at.isoformat(),
            "confidence": self.confidence,
            "bidirectional": self.bidirectional
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Relation':
        return cls(
            id=data["id"],
            source_id=data["source_id"],
            target_id=data["target_id"],
            relation_type=RelationType(data["relation_type"]),
            properties=data.get("properties", {}),
            weight=data.get("weight", 1.0),
            created_at=datetime.fromisoformat(data["created_at"]),
            confidence=data.get("confidence", 1.0),
            bidirectional=data.get("bidirectional", False)
        )


@dataclass
class KnowledgePath:
    """知识路径 - 实体间的多跳关系路径"""
    entities: List[Entity]
    relations: List[Relation]
    total_weight: float
    path_length: int
    confidence: float
    
    def to_dict(self) -> Dict:
        return {
            "entities": [e.to_dict() for e in self.entities],
            "relations": [r.to_dict() for r in self.relations],
            "total_weight": self.total_weight,
            "path_length": self.path_length,
            "confidence": self.confidence
        }


class GraphMetrics:
    """图网络指标计算"""
    
    @staticmethod
    def calculate_degree_centrality(adjacency_list: Dict[str, Set[str]]) -> Dict[str, int]:
        """计算度中心性"""
        return {node: len(neighbors) for node, neighbors in adjacency_list.items()}
    
    @staticmethod
    def calculate_betweenness_centrality(adjacency_list: Dict[str, Set[str]]) -> Dict[str, float]:
        """计算介数中心性 (简化版)"""
        nodes = list(adjacency_list.keys())
        betweenness = {node: 0.0 for node in nodes}
        
        for source in nodes:
            # BFS计算最短路径
            paths = {node: [] for node in nodes}
            distances = {node: float('inf') for node in nodes}
            distances[source] = 0
            queue = [source]
            
            while queue:
                current = queue.pop(0)
                for neighbor in adjacency_list.get(current, set()):
                    if distances[neighbor] == float('inf'):
                        distances[neighbor] = distances[current] + 1
                        queue.append(neighbor)
                        paths[neighbor].append(current)
                    elif distances[neighbor] == distances[current] + 1:
                        paths[neighbor].append(current)
            
            # 统计经过各节点的最短路径数
            for target in nodes:
                if target != source:
                    for path_node in paths.get(target, []):
                        if path_node != source and path_node != target:
                            betweenness[path_node] += 1
        
        return betweenness
    
    @staticmethod
    def calculate_pagerank(adjacency_list: Dict[str, Set[str]], 
                          damping: float = 0.85, 
                          iterations: int = 100) -> Dict[str, float]:
        """计算PageRank"""
        nodes = list(adjacency_list.keys())
        n = len(nodes)
        if n == 0:
            return {}
        
        pagerank = {node: 1.0 / n for node in nodes}
        
        for _ in range(iterations):
            new_pagerank = {}
            for node in nodes:
                rank = (1 - damping) / n
                for other in nodes:
                    if node in adjacency_list.get(other, set()):
                        out_degree = len(adjacency_list.get(other, set()))
                        if out_degree > 0:
                            rank += damping * pagerank[other] / out_degree
                new_pagerank[node] = rank
            pagerank = new_pagerank
        
        return pagerank
    
    @staticmethod
    def calculate_clustering_coefficient(adjacency_list: Dict[str, Set[str]]) -> Dict[str, float]:
        """计算聚类系数"""
        coefficients = {}
        
        for node, neighbors in adjacency_list.items():
            k = len(neighbors)
            if k < 2:
                coefficients[node] = 0.0
                continue
            
            # 计算邻居间的连接数
            edges_between_neighbors = 0
            neighbors_list = list(neighbors)
            for i in range(k):
                for j in range(i + 1, k):
                    if neighbors_list[j] in adjacency_list.get(neighbors_list[i], set()):
                        edges_between_neighbors += 1
            
            # 聚类系数 = 实际边数 / 可能的最大边数
            max_edges = k * (k - 1) / 2
            coefficients[node] = edges_between_neighbors / max_edges if max_edges > 0 else 0.0
        
        return coefficients


class KnowledgeGraph:
    """知识图谱核心类"""
    
    def __init__(self, name: str = "default"):
        self.name = name
        self._entities: Dict[str, Entity] = {}
        self._relations: Dict[str, Relation] = {}
        self._entity_index: Dict[EntityType, Set[str]] = defaultdict(set)
        self._relation_index: Dict[RelationType, Set[str]] = defaultdict(set)
        self._adjacency_list: Dict[str, Set[str]] = defaultdict(set)
        self._reverse_adjacency: Dict[str, Set[str]] = defaultdict(set)
        self._entity_relations: Dict[str, Set[str]] = defaultdict(set)
        self._lock = threading.RLock()
        self._metrics_cache: Dict[str, Any] = {}
        self._cache_timestamp: Optional[datetime] = None
        
    # ============ 实体管理 ============
    
    def add_entity(self, entity: Entity) -> bool:
        """添加实体"""
        with self._lock:
            if entity.id in self._entities:
                return False
            
            self._entities[entity.id] = entity
            self._entity_index[entity.entity_type].add(entity.id)
            self._adjacency_list[entity.id] = set()
            self._reverse_adjacency[entity.id] = set()
            self._entity_relations[entity.id] = set()
            self._invalidate_cache()
            return True
    
    def update_entity(self, entity_id: str, updates: Dict[str, Any]) -> bool:
        """更新实体"""
        with self._lock:
            if entity_id not in self._entities:
                return False
            
            entity = self._entities[entity_id]
            if "name" in updates:
                entity.name = updates["name"]
            if "properties" in updates:
                entity.properties.update(updates["properties"])
            if "confidence" in updates:
                entity.confidence = updates["confidence"]
            
            entity.updated_at = datetime.now()
            self._invalidate_cache()
            return True
    
    def remove_entity(self, entity_id: str) -> bool:
        """删除实体及其所有关系"""
        with self._lock:
            if entity_id not in self._entities:
                return False
            
            entity = self._entities[entity_id]
            
            # 删除相关关系
            relations_to_remove = list(self._entity_relations[entity_id])
            for rel_id in relations_to_remove:
                self.remove_relation(rel_id)
            
            # 删除实体
            del self._entities[entity_id]
            self._entity_index[entity.entity_type].discard(entity_id)
            del self._adjacency_list[entity_id]
            del self._reverse_adjacency[entity_id]
            del self._entity_relations[entity_id]
            self._invalidate_cache()
            return True
    
    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """获取实体"""
        return self._entities.get(entity_id)
    
    def find_entities_by_name(self, name: str, fuzzy: bool = False) -> List[Entity]:
        """按名称查找实体"""
        results = []
        name_lower = name.lower()
        
        for entity in self._entities.values():
            if fuzzy:
                if name_lower in entity.name.lower():
                    results.append(entity)
            else:
                if entity.name.lower() == name_lower:
                    results.append(entity)
        
        return results
    
    def find_entities_by_type(self, entity_type: EntityType) -> List[Entity]:
        """按类型查找实体"""
        entity_ids = self._entity_index.get(entity_type, set())
        return [self._entities[eid] for eid in entity_ids if eid in self._entities]
    
    # ============ 关系管理 ============
    
    def add_relation(self, relation: Relation) -> bool:
        """添加关系"""
        with self._lock:
            if relation.id in self._relations:
                return False
            
            if relation.source_id not in self._entities or \
               relation.target_id not in self._entities:
                return False
            
            self._relations[relation.id] = relation
            self._relation_index[relation.relation_type].add(relation.id)
            
            # 更新邻接表
            self._adjacency_list[relation.source_id].add(relation.target_id)
            self._reverse_adjacency[relation.target_id].add(relation.source_id)
            
            self._entity_relations[relation.source_id].add(relation.id)
            self._entity_relations[relation.target_id].add(relation.id)
            
            if relation.bidirectional:
                self._adjacency_list[relation.target_id].add(relation.source_id)
                self._reverse_adjacency[relation.source_id].add(relation.target_id)
            
            self._invalidate_cache()
            return True
    
    def remove_relation(self, relation_id: str) -> bool:
        """删除关系"""
        with self._lock:
            if relation_id not in self._relations:
                return False
            
            relation = self._relations[relation_id]
            
            # 更新索引
            self._relation_index[relation.relation_type].discard(relation_id)
            
            # 更新邻接表
            self._adjacency_list[relation.source_id].discard(relation.target_id)
            self._reverse_adjacency[relation.target_id].discard(relation.source_id)
            
            self._entity_relations[relation.source_id].discard(relation_id)
            self._entity_relations[relation.target_id].discard(relation_id)
            
            if relation.bidirectional:
                self._adjacency_list[relation.target_id].discard(relation.source_id)
                self._reverse_adjacency[relation.source_id].discard(relation.target_id)
            
            del self._relations[relation_id]
            self._invalidate_cache()
            return True
    
    def get_relation(self, relation_id: str) -> Optional[Relation]:
        """获取关系"""
        return self._relations.get(relation_id)
    
    def find_relations_by_type(self, relation_type: RelationType) -> List[Relation]:
        """按类型查找关系"""
        relation_ids = self._relation_index.get(relation_type, set())
        return [self._relations[rid] for rid in relation_ids if rid in self._relations]
    
    def get_entity_relations(self, entity_id: str, direction: str = "both") -> List[Relation]:
        """获取实体的关系
        direction: "out" | "in" | "both"
        """
        if entity_id not in self._entities:
            return []
        
        relation_ids = self._entity_relations.get(entity_id, set())
        relations = []
        
        for rel_id in relation_ids:
            relation = self._relations.get(rel_id)
            if relation:
                if direction == "out" and relation.source_id == entity_id:
                    relations.append(relation)
                elif direction == "in" and relation.target_id == entity_id:
                    relations.append(relation)
                elif direction == "both":
                    relations.append(relation)
        
        return relations
    
    def get_neighbors(self, entity_id: str, direction: str = "both") -> List[Entity]:
        """获取实体的邻居实体"""
        if entity_id not in self._entities:
            return []
        
        neighbor_ids = set()
        
        if direction in ("out", "both"):
            neighbor_ids.update(self._adjacency_list.get(entity_id, set()))
        
        if direction in ("in", "both"):
            neighbor_ids.update(self._reverse_adjacency.get(entity_id, set()))
        
        return [self._entities[eid] for eid in neighbor_ids if eid in self._entities]
    
    # ============ 路径发现 ============
    
    def find_shortest_path(self, source_id: str, target_id: str, 
                          max_depth: int = 10) -> Optional[KnowledgePath]:
        """使用BFS查找最短路径"""
        if source_id not in self._entities or target_id not in self._entities:
            return None
        
        if source_id == target_id:
            entity = self._entities[source_id]
            return KnowledgePath(
                entities=[entity],
                relations=[],
                total_weight=0,
                path_length=0,
                confidence=1.0
            )
        
        # BFS
        queue = [(source_id, [source_id])]
        visited = {source_id}
        
        while queue and len(queue[0][1]) <= max_depth:
            current_id, path = queue.pop(0)
            
            for neighbor_id in self._adjacency_list.get(current_id, set()):
                if neighbor_id not in visited:
                    new_path = path + [neighbor_id]
                    
                    if neighbor_id == target_id:
                        # 构建路径对象
                        entities = [self._entities[eid] for eid in new_path]
                        relations = []
                        total_weight = 0
                        min_confidence = 1.0
                        
                        for i in range(len(new_path) - 1):
                            # 找到连接这两个实体的关系
                            for rel_id in self._entity_relations.get(new_path[i], set()):
                                rel = self._relations.get(rel_id)
                                if rel and rel.target_id == new_path[i + 1]:
                                    relations.append(rel)
                                    total_weight += rel.weight
                                    min_confidence = min(min_confidence, rel.confidence)
                                    break
                        
                        return KnowledgePath(
                            entities=entities,
                            relations=relations,
                            total_weight=total_weight,
                            path_length=len(relations),
                            confidence=min_confidence
                        )
                    
                    visited.add(neighbor_id)
                    queue.append((neighbor_id, new_path))
        
        return None
    
    def find_all_paths(self, source_id: str, target_id: str, 
                       max_depth: int = 5, max_paths: int = 10) -> List[KnowledgePath]:
        """查找所有路径 (使用DFS)"""
        if source_id not in self._entities or target_id not in self._entities:
            return []
        
        paths = []
        
        def dfs(current_id: str, target: str, path: List[str], 
                relations: List[Relation], depth: int):
            if depth > max_depth or len(paths) >= max_paths:
                return
            
            if current_id == target:
                entities = [self._entities[eid] for eid in path]
                total_weight = sum(r.weight for r in relations)
                confidence = min((r.confidence for r in relations), default=1.0)
                
                paths.append(KnowledgePath(
                    entities=entities,
                    relations=relations.copy(),
                    total_weight=total_weight,
                    path_length=len(relations),
                    confidence=confidence
                ))
                return
            
            for rel_id in self._entity_relations.get(current_id, set()):
                rel = self._relations.get(rel_id)
                if rel and rel.source_id == current_id:
                    next_id = rel.target_id
                    if next_id not in path:  # 避免环路
                        relations.append(rel)
                        dfs(next_id, target, path + [next_id], relations, depth + 1)
                        relations.pop()
        
        dfs(source_id, target_id, [source_id], [], 0)
        
        # 按权重排序
        paths.sort(key=lambda p: p.total_weight, reverse=True)
        return paths
    
    # ============ 图算法 ============
    
    def calculate_centrality(self, metric_type: str = "degree") -> Dict[str, float]:
        """计算中心性指标"""
        with self._lock:
            if metric_type == "degree":
                return {k: float(v) for k, v in 
                       GraphMetrics.calculate_degree_centrality(self._adjacency_list).items()}
            elif metric_type == "betweenness":
                return GraphMetrics.calculate_betweenness_centrality(self._adjacency_list)
            elif metric_type == "pagerank":
                return GraphMetrics.calculate_pagerank(self._adjacency_list)
            elif metric_type == "clustering":
                return GraphMetrics.calculate_clustering_coefficient(self._adjacency_list)
            else:
                return {}
    
    def find_communities(self, algorithm: str = "greedy") -> List[Set[str]]:
        """社区发现"""
        if algorithm == "greedy":
            return self._greedy_community_detection()
        return []
    
    def _greedy_community_detection(self) -> List[Set[str]]:
        """贪心社区发现算法"""
        nodes = set(self._entities.keys())
        communities = []
        unvisited = nodes.copy()
        
        while unvisited:
            # 从未访问节点中选择一个开始新社区
            start = unvisited.pop()
            community = {start}
            queue = [start]
            
            while queue:
                current = queue.pop(0)
                neighbors = self._adjacency_list.get(current, set()) | \
                           self._reverse_adjacency.get(current, set())
                
                for neighbor in neighbors:
                    if neighbor in unvisited:
                        # 计算与社区的连接密度
                        community_neighbors = sum(
                            1 for n in self._adjacency_list.get(neighbor, set())
                            if n in community
                        )
                        if community_neighbors >= 1:  # 至少与一个社区成员连接
                            community.add(neighbor)
                            unvisited.discard(neighbor)
                            queue.append(neighbor)
            
            communities.append(community)
        
        return communities
    
    def find_similar_entities(self, entity_id: str, top_k: int = 5) -> List[Tuple[Entity, float]]:
        """查找相似实体 (基于共同邻居)"""
        if entity_id not in self._entities:
            return []
        
        source_neighbors = set(self._adjacency_list.get(entity_id, set())) | \
                          set(self._reverse_adjacency.get(entity_id, set()))
        
        similarities = []
        
        for other_id, other_entity in self._entities.items():
            if other_id == entity_id:
                continue
            
            other_neighbors = set(self._adjacency_list.get(other_id, set())) | \
                             set(self._reverse_adjacency.get(other_id, set()))
            
            # Jaccard相似度
            intersection = len(source_neighbors & other_neighbors)
            union = len(source_neighbors | other_neighbors)
            
            if union > 0:
                similarity = intersection / union
                if similarity > 0:
                    similarities.append((other_entity, similarity))
        
        # 按相似度排序
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]
    
    # ============ 知识推理 ============
    
    def infer_relations(self, entity_id: str, max_hops: int = 2) -> List[Dict]:
        """关系推理 - 发现潜在关系"""
        if entity_id not in self._entities:
            return []
        
        inferred = []
        source_entity = self._entities[entity_id]
        
        # 获取多跳邻居
        neighbors_at_distance = self._get_neighbors_at_distance(entity_id, max_hops)
        
        for distance, neighbor_ids in neighbors_at_distance.items():
            if distance < 2:
                continue
            
            for neighbor_id in neighbor_ids:
                neighbor = self._entities[neighbor_id]
                
                # 检查是否已有直接关系
                has_direct = any(
                    rel.target_id == neighbor_id 
                    for rel in self.get_entity_relations(entity_id, "out")
                )
                
                if not has_direct:
                    # 推断潜在关系
                    confidence = 1.0 / distance  # 距离越远，置信度越低
                    
                    # 根据实体类型推断关系类型
                    inferred_type = self._infer_relation_type(
                        source_entity.entity_type, 
                        neighbor.entity_type
                    )
                    
                    inferred.append({
                        "source": source_entity.to_dict(),
                        "target": neighbor.to_dict(),
                        "inferred_relation": inferred_type.value,
                        "path_length": distance,
                        "confidence": round(confidence, 3),
                        "reasoning": f"通过{distance}跳连接推断"
                    })
        
        # 按置信度排序
        inferred.sort(key=lambda x: x["confidence"], reverse=True)
        return inferred
    
    def _get_neighbors_at_distance(self, entity_id: str, max_distance: int) -> Dict[int, Set[str]]:
        """获取指定距离的所有邻居"""
        distances = {entity_id: 0}
        queue = [entity_id]
        
        while queue:
            current = queue.pop(0)
            current_dist = distances[current]
            
            if current_dist >= max_distance:
                continue
            
            for neighbor in self._adjacency_list.get(current, set()):
                if neighbor not in distances:
                    distances[neighbor] = current_dist + 1
                    queue.append(neighbor)
        
        # 按距离分组
        result = defaultdict(set)
        for node_id, dist in distances.items():
            if dist > 0:
                result[dist].add(node_id)
        
        return dict(result)
    
    def _infer_relation_type(self, source_type: EntityType, 
                            target_type: EntityType) -> RelationType:
        """根据实体类型推断关系类型"""
        type_pairs = {
            (EntityType.PERSON, EntityType.ORGANIZATION): RelationType.BELONGS_TO,
            (EntityType.PERSON, EntityType.PERSON): RelationType.RELATED_TO,
            (EntityType.ORGANIZATION, EntityType.LOCATION): RelationType.LOCATED_IN,
            (EntityType.PRODUCT, EntityType.ORGANIZATION): RelationType.CREATED_BY,
            (EntityType.TECHNOLOGY, EntityType.TECHNOLOGY): RelationType.DEPENDS_ON,
            (EntityType.CONCEPT, EntityType.CONCEPT): RelationType.RELATED_TO,
        }
        
        return type_pairs.get((source_type, target_type), RelationType.RELATED_TO)
    
    # ============ 查询与搜索 ============
    
    def search(self, query: str, entity_types: Optional[List[EntityType]] = None,
               limit: int = 20) -> Dict[str, List]:
        """综合搜索"""
        results = {
            "entities": [],
            "relations": [],
            "paths": []
        }
        
        query_lower = query.lower()
        
        # 搜索实体
        for entity in self._entities.values():
            if entity_types and entity.entity_type not in entity_types:
                continue
            
            score = 0
            if query_lower in entity.name.lower():
                score += 3
            if any(query_lower in str(v).lower() for v in entity.properties.values()):
                score += 1
            
            if score > 0:
                results["entities"].append({
                    "entity": entity.to_dict(),
                    "score": score
                })
        
        # 搜索关系
        for relation in self._relations.values():
            score = 0
            if query_lower in relation.relation_type.value.lower():
                score += 2
            if any(query_lower in str(v).lower() for v in relation.properties.values()):
                score += 1
            
            if score > 0:
                results["relations"].append({
                    "relation": relation.to_dict(),
                    "score": score
                })
        
        # 排序和限制
        results["entities"].sort(key=lambda x: x["score"], reverse=True)
        results["relations"].sort(key=lambda x: x["score"], reverse=True)
        
        results["entities"] = results["entities"][:limit]
        results["relations"] = results["relations"][:limit]
        
        return results
    
    def execute_cypher_like_query(self, query: str) -> List[Dict]:
        """执行类Cypher查询 (简化版)"""
        # 支持简单查询如: MATCH (p:person)-[:created_by]->(o:organization) RETURN p, o
        results = []
        
        # 解析查询 (简化实现)
        # 实际应用中可以使用正式的Cypher解析器
        match_pattern = r'MATCH\s+\((\w+):?(\w+)?\)\s*-?\[:?(\w+)?\]?\s*->?\s*\((\w+):?(\w+)?\)'
        match = re.search(match_pattern, query, re.IGNORECASE)
        
        if match:
            source_var, source_type, relation_type, target_var, target_type = match.groups()
            
            # 过滤实体类型
            source_entities = list(self._entities.values())
            if source_type:
                try:
                    etype = EntityType(source_type.lower())
                    source_entities = self.find_entities_by_type(etype)
                except:
                    pass
            
            # 查找匹配的关系
            for entity in source_entities:
                for rel in self.get_entity_relations(entity.id, "out"):
                    if relation_type and rel.relation_type.value != relation_type.lower():
                        continue
                    
                    target = self._entities.get(rel.target_id)
                    if target:
                        if target_type:
                            try:
                                etype = EntityType(target_type.lower())
                                if target.entity_type != etype:
                                    continue
                            except:
                                pass
                        
                        results.append({
                            source_var or "source": entity.to_dict(),
                            "relation": rel.to_dict(),
                            target_var or "target": target.to_dict()
                        })
        
        return results
    
    # ============ 统计与导出 ============
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取图谱统计信息"""
        with self._lock:
            entity_type_counts = {
                etype.value: len(eids) 
                for etype, eids in self._entity_index.items()
            }
            
            relation_type_counts = {
                rtype.value: len(rids) 
                for rtype, rids in self._relation_index.items()
            }
            
            # 计算密度
            n = len(self._entities)
            m = len(self._relations)
            density = (2 * m) / (n * (n - 1)) if n > 1 else 0
            
            return {
                "total_entities": n,
                "total_relations": m,
                "entity_types": entity_type_counts,
                "relation_types": relation_type_counts,
                "density": round(density, 6),
                "avg_degree": round(2 * m / n, 2) if n > 0 else 0
            }
    
    def export_to_json(self) -> str:
        """导出为JSON"""
        data = {
            "name": self.name,
            "entities": [e.to_dict() for e in self._entities.values()],
            "relations": [r.to_dict() for r in self._relations.values()],
            "statistics": self.get_statistics(),
            "exported_at": datetime.now().isoformat()
        }
        return json.dumps(data, ensure_ascii=False, indent=2)
    
    def import_from_json(self, json_str: str) -> bool:
        """从JSON导入"""
        try:
            data = json.loads(json_str)
            
            with self._lock:
                # 清空现有数据
                self._entities.clear()
                self._relations.clear()
                self._entity_index.clear()
                self._relation_index.clear()
                self._adjacency_list.clear()
                self._reverse_adjacency.clear()
                self._entity_relations.clear()
                
                # 导入实体
                for entity_data in data.get("entities", []):
                    entity = Entity.from_dict(entity_data)
                    self._entities[entity.id] = entity
                    self._entity_index[entity.entity_type].add(entity.id)
                    self._adjacency_list[entity.id] = set()
                    self._reverse_adjacency[entity.id] = set()
                    self._entity_relations[entity.id] = set()
                
                # 导入关系
                for relation_data in data.get("relations", []):
                    relation = Relation.from_dict(relation_data)
                    self._relations[relation.id] = relation
                    self._relation_index[relation.relation_type].add(relation.id)
                    
                    self._adjacency_list[relation.source_id].add(relation.target_id)
                    self._reverse_adjacency[relation.target_id].add(relation.source_id)
                    self._entity_relations[relation.source_id].add(relation.id)
                    self._entity_relations[relation.target_id].add(relation.id)
                    
                    if relation.bidirectional:
                        self._adjacency_list[relation.target_id].add(relation.source_id)
                        self._reverse_adjacency[relation.source_id].add(relation.target_id)
                
                self._invalidate_cache()
                return True
        
        except Exception as e:
            print(f"导入失败: {e}")
            return False
    
    def export_to_cypher(self) -> str:
        """导出为Cypher语句 (Neo4j)"""
        statements = []
        
        # 创建实体
        for entity in self._entities.values():
            props = json.dumps(entity.properties, ensure_ascii=False)
            stmt = f"CREATE ({entity.id}:{entity.entity_type.value} {{"
            stmt += f"name: '{entity.name}', "
            stmt += f"confidence: {entity.confidence}, "
            stmt += f"properties: {props}"
            stmt += "})"
            statements.append(stmt)
        
        # 创建关系
        for relation in self._relations.values():
            stmt = f"MATCH (a), (b) WHERE a.id = '{relation.source_id}' AND b.id = '{relation.target_id}' "
            stmt += f"CREATE (a)-[:{relation.relation_type.value} {{"
            stmt += f"weight: {relation.weight}, "
            stmt += f"confidence: {relation.confidence}"
            stmt += "}]->(b)"
            statements.append(stmt)
        
        return "\n".join(statements)
    
    def _invalidate_cache(self):
        """使缓存失效"""
        self._metrics_cache.clear()
        self._cache_timestamp = None


class KnowledgeGraphManager:
    """知识图谱管理器 - 管理多个知识图谱"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._graphs: Dict[str, KnowledgeGraph] = {}
                    cls._instance._default_graph = None
        return cls._instance
    
    def create_graph(self, name: str) -> KnowledgeGraph:
        """创建新的知识图谱"""
        if name not in self._graphs:
            self._graphs[name] = KnowledgeGraph(name)
            if self._default_graph is None:
                self._default_graph = name
        return self._graphs[name]
    
    def get_graph(self, name: str) -> Optional[KnowledgeGraph]:
        """获取知识图谱"""
        return self._graphs.get(name)
    
    def get_default_graph(self) -> Optional[KnowledgeGraph]:
        """获取默认知识图谱"""
        if self._default_graph:
            return self._graphs.get(self._default_graph)
        return None
    
    def set_default_graph(self, name: str) -> bool:
        """设置默认知识图谱"""
        if name in self._graphs:
            self._default_graph = name
            return True
        return False
    
    def list_graphs(self) -> List[str]:
        """列出所有知识图谱"""
        return list(self._graphs.keys())
    
    def delete_graph(self, name: str) -> bool:
        """删除知识图谱"""
        if name in self._graphs:
            del self._graphs[name]
            if self._default_graph == name:
                self._default_graph = next(iter(self._graphs), None)
            return True
        return False
    
    def get_all_statistics(self) -> Dict[str, Any]:
        """获取所有图谱统计"""
        return {
            name: graph.get_statistics()
            for name, graph in self._graphs.items()
        }


# ============ 便捷函数 ============

def create_entity(name: str, entity_type: str, 
                 properties: Optional[Dict] = None,
                 source: str = "") -> Entity:
    """创建实体"""
    entity_id = hashlib.md5(f"{name}:{entity_type}:{datetime.now()}".encode()).hexdigest()[:12]
    
    try:
        etype = EntityType(entity_type.lower())
    except:
        etype = EntityType.CUSTOM
    
    return Entity(
        id=entity_id,
        name=name,
        entity_type=etype,
        properties=properties or {},
        source=source
    )


def create_relation(source_id: str, target_id: str, relation_type: str,
                   weight: float = 1.0, properties: Optional[Dict] = None,
                   bidirectional: bool = False) -> Relation:
    """创建关系"""
    rel_id = hashlib.md5(f"{source_id}:{target_id}:{relation_type}:{datetime.now()}".encode()).hexdigest()[:12]
    
    try:
        rtype = RelationType(relation_type.lower())
    except:
        rtype = RelationType.CUSTOM
    
    return Relation(
        id=rel_id,
        source_id=source_id,
        target_id=target_id,
        relation_type=rtype,
        properties=properties or {},
        weight=weight,
        bidirectional=bidirectional
    )


def get_knowledge_graph_manager() -> KnowledgeGraphManager:
    """获取知识图谱管理器实例"""
    return KnowledgeGraphManager()


# 初始化默认知识图谱
_default_manager = get_knowledge_graph_manager()
_default_manager.create_graph("main")
