"""
本地知识图谱构建系统
支持图数据库存储、实体关系抽取和推理
"""

import json
import os
import re
import sqlite3
import hashlib
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from collections import defaultdict
import threading


@dataclass
class Entity:
    """知识图谱实体"""
    id: str
    name: str
    entity_type: str  # person, organization, location, concept, etc.
    properties: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    source: str = ""  # 来源文档/知识
    confidence: float = 1.0  # 置信度
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'name': self.name,
            'entity_type': self.entity_type,
            'properties': self.properties,
            'description': self.description,
            'source': self.source,
            'confidence': self.confidence,
            'created_at': self.created_at
        }


@dataclass
class Relation:
    """知识图谱关系"""
    id: str
    source_id: str  # 源实体ID
    target_id: str  # 目标实体ID
    relation_type: str  # 关系类型
    properties: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    confidence: float = 1.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'source_id': self.source_id,
            'target_id': self.target_id,
            'relation_type': self.relation_type,
            'properties': self.properties,
            'description': self.description,
            'confidence': self.confidence,
            'created_at': self.created_at
        }


@dataclass
class KnowledgeTriple:
    """知识三元组 (头实体, 关系, 尾实体)"""
    head: str
    relation: str
    tail: str
    confidence: float = 1.0
    source: str = ""
    
    def to_dict(self) -> Dict:
        return {
            'head': self.head,
            'relation': self.relation,
            'tail': self.tail,
            'confidence': self.confidence,
            'source': self.source
        }


class KnowledgeGraphDatabase:
    """知识图谱数据库 (基于SQLite)"""
    
    def __init__(self, db_path: str = "knowledge_graph.db"):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_database()
    
    def _init_database(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 实体表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS entities (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    properties TEXT,
                    description TEXT,
                    source TEXT,
                    confidence REAL DEFAULT 1.0,
                    created_at TEXT
                )
            ''')
            
            # 关系表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS relations (
                    id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    relation_type TEXT NOT NULL,
                    properties TEXT,
                    description TEXT,
                    confidence REAL DEFAULT 1.0,
                    created_at TEXT,
                    FOREIGN KEY (source_id) REFERENCES entities (id),
                    FOREIGN KEY (target_id) REFERENCES entities (id)
                )
            ''')
            
            # 创建索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_entity_type ON entities (entity_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_entity_name ON entities (name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_relation_type ON relations (relation_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_relation_source ON relations (source_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_relation_target ON relations (target_id)')
            
            conn.commit()
    
    def add_entity(self, entity: Entity) -> bool:
        """添加实体"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO entities 
                    (id, name, entity_type, properties, description, source, confidence, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    entity.id, entity.name, entity.entity_type,
                    json.dumps(entity.properties), entity.description,
                    entity.source, entity.confidence, entity.created_at
                ))
                conn.commit()
                return True
        except Exception as e:
            print(f"添加实体失败: {e}")
            return False
    
    def add_relation(self, relation: Relation) -> bool:
        """添加关系"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO relations 
                    (id, source_id, target_id, relation_type, properties, description, confidence, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    relation.id, relation.source_id, relation.target_id,
                    relation.relation_type, json.dumps(relation.properties),
                    relation.description, relation.confidence, relation.created_at
                ))
                conn.commit()
                return True
        except Exception as e:
            print(f"添加关系失败: {e}")
            return False
    
    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """获取实体"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM entities WHERE id = ?', (entity_id,))
            row = cursor.fetchone()
            
            if row:
                return Entity(
                    id=row[0],
                    name=row[1],
                    entity_type=row[2],
                    properties=json.loads(row[3]) if row[3] else {},
                    description=row[4],
                    source=row[5],
                    confidence=row[6],
                    created_at=row[7]
                )
            return None
    
    def get_entity_by_name(self, name: str) -> Optional[Entity]:
        """通过名称获取实体"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM entities WHERE name = ?', (name,))
            row = cursor.fetchone()
            
            if row:
                return Entity(
                    id=row[0],
                    name=row[1],
                    entity_type=row[2],
                    properties=json.loads(row[3]) if row[3] else {},
                    description=row[4],
                    source=row[5],
                    confidence=row[6],
                    created_at=row[7]
                )
            return None
    
    def search_entities(self, query: str, entity_type: str = None, limit: int = 20) -> List[Entity]:
        """搜索实体"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if entity_type:
                cursor.execute('''
                    SELECT * FROM entities 
                    WHERE name LIKE ? AND entity_type = ?
                    LIMIT ?
                ''', (f'%{query}%', entity_type, limit))
            else:
                cursor.execute('''
                    SELECT * FROM entities 
                    WHERE name LIKE ? OR description LIKE ?
                    LIMIT ?
                ''', (f'%{query}%', f'%{query}%', limit))
            
            entities = []
            for row in cursor.fetchall():
                entities.append(Entity(
                    id=row[0],
                    name=row[1],
                    entity_type=row[2],
                    properties=json.loads(row[3]) if row[3] else {},
                    description=row[4],
                    source=row[5],
                    confidence=row[6],
                    created_at=row[7]
                ))
            return entities
    
    def get_relations(self, entity_id: str, direction: str = 'both') -> List[Relation]:
        """获取实体的关系"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            relations = []
            
            if direction in ['outgoing', 'both']:
                cursor.execute('SELECT * FROM relations WHERE source_id = ?', (entity_id,))
                for row in cursor.fetchall():
                    relations.append(Relation(
                        id=row[0],
                        source_id=row[1],
                        target_id=row[2],
                        relation_type=row[3],
                        properties=json.loads(row[4]) if row[4] else {},
                        description=row[5],
                        confidence=row[6],
                        created_at=row[7]
                    ))
            
            if direction in ['incoming', 'both']:
                cursor.execute('SELECT * FROM relations WHERE target_id = ?', (entity_id,))
                for row in cursor.fetchall():
                    relations.append(Relation(
                        id=row[0],
                        source_id=row[1],
                        target_id=row[2],
                        relation_type=row[3],
                        properties=json.loads(row[4]) if row[4] else {},
                        description=row[5],
                        confidence=row[6],
                        created_at=row[7]
                    ))
            
            return relations
    
    def get_all_entities(self, entity_type: str = None, limit: int = 100) -> List[Entity]:
        """获取所有实体"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if entity_type:
                cursor.execute('SELECT * FROM entities WHERE entity_type = ? LIMIT ?', 
                             (entity_type, limit))
            else:
                cursor.execute('SELECT * FROM entities LIMIT ?', (limit,))
            
            entities = []
            for row in cursor.fetchall():
                entities.append(Entity(
                    id=row[0],
                    name=row[1],
                    entity_type=row[2],
                    properties=json.loads(row[3]) if row[3] else {},
                    description=row[4],
                    source=row[5],
                    confidence=row[6],
                    created_at=row[7]
                ))
            return entities
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 实体统计
            cursor.execute('SELECT COUNT(*) FROM entities')
            entity_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT entity_type, COUNT(*) FROM entities GROUP BY entity_type')
            entity_types = {row[0]: row[1] for row in cursor.fetchall()}
            
            # 关系统计
            cursor.execute('SELECT COUNT(*) FROM relations')
            relation_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT relation_type, COUNT(*) FROM relations GROUP BY relation_type')
            relation_types = {row[0]: row[1] for row in cursor.fetchall()}
            
            return {
                'entity_count': entity_count,
                'entity_types': entity_types,
                'relation_count': relation_count,
                'relation_types': relation_types
            }


class KnowledgeGraphBuilder:
    """知识图谱构建器"""
    
    def __init__(self, db: KnowledgeGraphDatabase = None):
        self.db = db or KnowledgeGraphDatabase()
        self._entity_cache = {}  # 名称到ID的缓存
    
    def _generate_id(self, text: str) -> str:
        """生成唯一ID"""
        return hashlib.md5(text.encode()).hexdigest()[:16]
    
    def extract_entities_from_text(self, text: str, source: str = "") -> List[Entity]:
        """从文本中提取实体 (简化版，实际应使用NER模型)"""
        entities = []
        
        # 简单的规则提取示例
        # 人名识别 (中文)
        person_pattern = r'[\u4e00-\u9fa5]{2,4}(?:先生|女士|博士|教授|经理)'
        for match in re.finditer(person_pattern, text):
            name = match.group()
            entity_id = self._generate_id(f"person:{name}")
            if entity_id not in self._entity_cache:
                entity = Entity(
                    id=entity_id,
                    name=name,
                    entity_type="person",
                    source=source,
                    description=f"从文本中提取的人物: {name}"
                )
                entities.append(entity)
                self._entity_cache[entity_id] = entity_id
        
        # 组织识别
        org_pattern = r'[\u4e00-\u9fa5]{2,}(?:公司|集团|大学|研究院|部门)'
        for match in re.finditer(org_pattern, text):
            name = match.group()
            entity_id = self._generate_id(f"organization:{name}")
            if entity_id not in self._entity_cache:
                entity = Entity(
                    id=entity_id,
                    name=name,
                    entity_type="organization",
                    source=source,
                    description=f"从文本中提取的组织: {name}"
                )
                entities.append(entity)
                self._entity_cache[entity_id] = entity_id
        
        # 技术概念识别
        tech_pattern = r'\b(?:Python|Java|AI|机器学习|深度学习|神经网络|数据库|算法|API)\b'
        for match in re.finditer(tech_pattern, text, re.IGNORECASE):
            name = match.group()
            entity_id = self._generate_id(f"concept:{name}")
            if entity_id not in self._entity_cache:
                entity = Entity(
                    id=entity_id,
                    name=name,
                    entity_type="concept",
                    source=source,
                    description=f"技术概念: {name}"
                )
                entities.append(entity)
                self._entity_cache[entity_id] = entity_id
        
        return entities
    
    def extract_relations_from_text(self, text: str, entities: List[Entity], source: str = "") -> List[Relation]:
        """从文本中提取关系 (简化版)"""
        relations = []
        entity_names = {e.name: e.id for e in entities}
        
        # 简单的关系模式
        relation_patterns = [
            (r'(.+?)是(.+?)的', '是'),
            (r'(.+?)在(.+?)工作', '工作于'),
            (r'(.+?)使用(.+?)', '使用'),
            (r'(.+?)开发(.+?)', '开发'),
            (r'(.+?)属于(.+?)', '属于'),
        ]
        
        for pattern, rel_type in relation_patterns:
            for match in re.finditer(pattern, text):
                subj = match.group(1).strip()
                obj = match.group(2).strip()
                
                if subj in entity_names and obj in entity_names:
                    relation_id = self._generate_id(f"{entity_names[subj]}:{rel_type}:{entity_names[obj]}")
                    relation = Relation(
                        id=relation_id,
                        source_id=entity_names[subj],
                        target_id=entity_names[obj],
                        relation_type=rel_type,
                        source=source,
                        description=f"{subj} {rel_type} {obj}"
                    )
                    relations.append(relation)
        
        return relations
    
    def add_knowledge_from_text(self, text: str, source: str = "") -> Tuple[int, int]:
        """从文本中添加知识"""
        # 提取实体
        entities = self.extract_entities_from_text(text, source)
        entity_count = 0
        for entity in entities:
            if self.db.add_entity(entity):
                entity_count += 1
        
        # 提取关系
        relations = self.extract_relations_from_text(text, entities, source)
        relation_count = 0
        for relation in relations:
            if self.db.add_relation(relation):
                relation_count += 1
        
        return entity_count, relation_count
    
    def add_knowledge_triple(self, head: str, relation: str, tail: str, 
                            source: str = "", confidence: float = 1.0) -> bool:
        """添加知识三元组"""
        # 创建或获取头实体
        head_id = self._generate_id(f"entity:{head}")
        head_entity = self.db.get_entity(head_id)
        if not head_entity:
            head_entity = Entity(
                id=head_id,
                name=head,
                entity_type="unknown",
                source=source,
                confidence=confidence
            )
            self.db.add_entity(head_entity)
        
        # 创建或获取尾实体
        tail_id = self._generate_id(f"entity:{tail}")
        tail_entity = self.db.get_entity(tail_id)
        if not tail_entity:
            tail_entity = Entity(
                id=tail_id,
                name=tail,
                entity_type="unknown",
                source=source,
                confidence=confidence
            )
            self.db.add_entity(tail_entity)
        
        # 创建关系
        relation_id = self._generate_id(f"{head_id}:{relation}:{tail_id}")
        relation_obj = Relation(
            id=relation_id,
            source_id=head_id,
            target_id=tail_id,
            relation_type=relation,
            source=source,
            confidence=confidence
        )
        
        return self.db.add_relation(relation_obj)


class KnowledgeGraphQuery:
    """知识图谱查询与推理"""
    
    def __init__(self, db: KnowledgeGraphDatabase = None):
        self.db = db or KnowledgeGraphDatabase()
    
    def find_path(self, start_entity_id: str, end_entity_id: str, 
                  max_depth: int = 3) -> List[List[Relation]]:
        """查找两个实体之间的路径"""
        # BFS搜索
        from collections import deque
        
        queue = deque([(start_entity_id, [])])
        visited = {start_entity_id}
        all_paths = []
        
        while queue:
            current_id, path = queue.popleft()
            
            if current_id == end_entity_id and path:
                all_paths.append(path)
                continue
            
            if len(path) >= max_depth:
                continue
            
            # 获取 outgoing relations
            relations = self.db.get_relations(current_id, 'outgoing')
            for rel in relations:
                if rel.target_id not in visited:
                    visited.add(rel.target_id)
                    queue.append((rel.target_id, path + [rel]))
        
        return all_paths
    
    def find_neighbors(self, entity_id: str, relation_type: str = None) -> List[Entity]:
        """查找实体的邻居"""
        relations = self.db.get_relations(entity_id, 'outgoing')
        
        neighbors = []
        for rel in relations:
            if relation_type is None or rel.relation_type == relation_type:
                neighbor = self.db.get_entity(rel.target_id)
                if neighbor:
                    neighbors.append(neighbor)
        
        return neighbors
    
    def infer_relation(self, entity_a_id: str, entity_b_id: str) -> List[str]:
        """推理两个实体之间可能存在的关系"""
        # 查找共同邻居
        neighbors_a = set(n.id for n in self.find_neighbors(entity_a_id))
        neighbors_b = set(n.id for n in self.find_neighbors(entity_b_id))
        
        common_neighbors = neighbors_a & neighbors_b
        
        inferred_relations = []
        for neighbor_id in common_neighbors:
            # 获取关系类型
            rels_a = self.db.get_relations(entity_a_id, 'outgoing')
            rels_b = self.db.get_relations(entity_b_id, 'outgoing')
            
            for rel_a in rels_a:
                if rel_a.target_id == neighbor_id:
                    for rel_b in rels_b:
                        if rel_b.target_id == neighbor_id:
                            inferred_relations.append(
                                f"通过 {neighbor_id} 关联: {rel_a.relation_type} & {rel_b.relation_type}"
                            )
        
        return inferred_relations
    
    def query(self, query_text: str) -> Dict:
        """自然语言查询 (简化版)"""
        results = {
            'entities': [],
            'relations': [],
            'paths': [],
            'inferred': []
        }
        
        # 搜索实体
        entities = self.db.search_entities(query_text)
        results['entities'] = [e.to_dict() for e in entities]
        
        # 如果找到实体，查找相关信息
        if entities:
            main_entity = entities[0]
            relations = self.db.get_relations(main_entity.id, 'both')
            results['relations'] = [r.to_dict() for r in relations[:10]]
            
            # 查找邻居
            neighbors = self.find_neighbors(main_entity.id)
            results['neighbors'] = [n.to_dict() for n in neighbors[:5]]
        
        return results


class LocalKnowledgeGraph:
    """本地知识图谱主类"""
    
    def __init__(self, db_path: str = "knowledge_graph.db"):
        self.db = KnowledgeGraphDatabase(db_path)
        self.builder = KnowledgeGraphBuilder(self.db)
        self.query = KnowledgeGraphQuery(self.db)
    
    def add_entity(self, name: str, entity_type: str, description: str = "", 
                   properties: Dict = None, source: str = "") -> bool:
        """添加实体"""
        entity_id = hashlib.md5(f"{entity_type}:{name}".encode()).hexdigest()[:16]
        entity = Entity(
            id=entity_id,
            name=name,
            entity_type=entity_type,
            description=description,
            properties=properties or {},
            source=source
        )
        return self.db.add_entity(entity)
    
    def add_relation(self, head_name: str, relation_type: str, tail_name: str,
                     description: str = "", source: str = "") -> bool:
        """添加关系"""
        return self.builder.add_knowledge_triple(
            head_name, relation_type, tail_name, source
        )
    
    def import_from_text(self, text: str, source: str = "") -> Dict:
        """从文本导入知识"""
        entity_count, relation_count = self.builder.add_knowledge_from_text(text, source)
        return {
            'entities_added': entity_count,
            'relations_added': relation_count
        }
    
    def search(self, query: str) -> List[Entity]:
        """搜索实体"""
        return self.db.search_entities(query)
    
    def get_entity_details(self, entity_id: str) -> Optional[Dict]:
        """获取实体详情"""
        entity = self.db.get_entity(entity_id)
        if not entity:
            return None
        
        relations = self.db.get_relations(entity_id, 'both')
        neighbors = self.query.find_neighbors(entity_id)
        
        return {
            'entity': entity.to_dict(),
            'relations': [r.to_dict() for r in relations],
            'neighbors': [n.to_dict() for n in neighbors]
        }
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        return self.db.get_statistics()
    
    def export_to_json(self, filepath: str):
        """导出到JSON"""
        entities = self.db.get_all_entities(limit=10000)
        
        data = {
            'entities': [e.to_dict() for e in entities],
            'statistics': self.get_statistics(),
            'exported_at': datetime.now().isoformat()
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def import_from_json(self, filepath: str):
        """从JSON导入"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for entity_data in data.get('entities', []):
            entity = Entity(**entity_data)
            self.db.add_entity(entity)


# 全局知识图谱实例
_knowledge_graph = None

def get_knowledge_graph(db_path: str = "knowledge_graph.db") -> LocalKnowledgeGraph:
    """获取知识图谱单例"""
    global _knowledge_graph
    if _knowledge_graph is None:
        _knowledge_graph = LocalKnowledgeGraph(db_path)
    return _knowledge_graph


if __name__ == "__main__":
    # 测试代码
    print("本地知识图谱系统测试")
    
    kg = get_knowledge_graph("test_kg.db")
    
    # 添加实体
    kg.add_entity("Python", "编程语言", "一种高级编程语言", {"creator": "Guido van Rossum"})
    kg.add_entity("机器学习", "技术领域", "人工智能的一个分支")
    kg.add_entity("深度学习", "技术领域", "机器学习的一个子领域")
    
    # 添加关系
    kg.add_relation("Python", "用于", "机器学习")
    kg.add_relation("深度学习", "属于", "机器学习")
    
    # 从文本导入
    text = "张三在阿里巴巴工作，使用Python开发机器学习系统。"
    result = kg.import_from_text(text, "测试文档")
    print(f"从文本导入: {result}")
    
    # 搜索
    results = kg.search("Python")
    print(f"\n搜索结果: {len(results)} 个实体")
    for e in results:
        print(f"  - {e.name} ({e.entity_type})")
    
    # 统计
    stats = kg.get_statistics()
    print(f"\n统计信息: {stats}")
    
    print("\n测试完成")
