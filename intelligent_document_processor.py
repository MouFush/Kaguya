#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能文档处理模块 - 高级文档分析与处理
功能: 文档解析、内容提取、智能摘要、格式转换
"""

import re
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import Counter
import hashlib


@dataclass
class DocumentProcessingResult:
    """文档处理结果"""
    success: bool
    content: str = ""
    metadata: Dict = field(default_factory=dict)
    extracted_data: Dict = field(default_factory=dict)
    summary: str = ""
    keywords: List[str] = field(default_factory=list)
    error: Optional[str] = None
    processing_time: float = 0.0


class DocumentParser:
    """文档解析器"""
    
    SUPPORTED_FORMATS = ['txt', 'md', 'json', 'csv', 'html', 'xml', 'yaml']
    
    def parse_document(self, content: str, format_type: str) -> Dict:
        """
        解析文档内容
        
        Args:
            content: 文档内容
            format_type: 文档格式
            
        Returns:
            解析结果
        """
        format_type = format_type.lower()
        
        if format_type == 'json':
            return self._parse_json(content)
        elif format_type == 'csv':
            return self._parse_csv(content)
        elif format_type == 'html':
            return self._parse_html(content)
        elif format_type == 'xml':
            return self._parse_xml(content)
        elif format_type == 'yaml' or format_type == 'yml':
            return self._parse_yaml(content)
        elif format_type == 'md' or format_type == 'markdown':
            return self._parse_markdown(content)
        else:
            return self._parse_plain_text(content)
    
    def _parse_json(self, content: str) -> Dict:
        """解析JSON"""
        try:
            data = json.loads(content)
            return {
                'type': 'json',
                'data': data,
                'structure': self._analyze_json_structure(data),
                'item_count': len(data) if isinstance(data, (list, dict)) else 1
            }
        except json.JSONDecodeError as e:
            return {'type': 'json', 'error': str(e), 'data': None}
    
    def _analyze_json_structure(self, data: Any, path: str = "") -> Dict:
        """分析JSON结构"""
        if isinstance(data, dict):
            return {
                'type': 'object',
                'properties': {k: self._analyze_json_structure(v, f"{path}.{k}") for k, v in data.items()},
                'property_count': len(data)
            }
        elif isinstance(data, list):
            if data:
                return {
                    'type': 'array',
                    'item_type': self._analyze_json_structure(data[0], path),
                    'item_count': len(data)
                }
            return {'type': 'array', 'item_type': None, 'item_count': 0}
        elif isinstance(data, str):
            return {'type': 'string'}
        elif isinstance(data, (int, float)):
            return {'type': 'number'}
        elif isinstance(data, bool):
            return {'type': 'boolean'}
        else:
            return {'type': 'null'}
    
    def _parse_csv(self, content: str) -> Dict:
        """解析CSV"""
        lines = content.strip().split('\n')
        if not lines:
            return {'type': 'csv', 'error': 'Empty content'}
        
        # 简单CSV解析
        delimiter = ','
        if '\t' in lines[0]:
            delimiter = '\t'
        
        headers = lines[0].split(delimiter)
        rows = []
        
        for line in lines[1:]:
            if line.strip():
                values = line.split(delimiter)
                row = {headers[i].strip(): values[i].strip() if i < len(values) else '' 
                       for i in range(len(headers))}
                rows.append(row)
        
        return {
            'type': 'csv',
            'headers': headers,
            'rows': rows,
            'row_count': len(rows),
            'column_count': len(headers)
        }
    
    def _parse_html(self, content: str) -> Dict:
        """解析HTML"""
        # 提取文本内容
        text_content = re.sub(r'<[^>]+>', ' ', content)
        text_content = re.sub(r'\s+', ' ', text_content).strip()
        
        # 提取标题
        titles = re.findall(r'<h[1-6][^>]*>(.*?)</h[1-6]>', content, re.DOTALL)
        titles = [re.sub(r'<[^>]+>', '', t).strip() for t in titles]
        
        # 提取链接
        links = re.findall(r'href=["\'](.*?)["\']', content)
        
        # 提取图片
        images = re.findall(r'<img[^>]+src=["\'](.*?)["\']', content)
        
        return {
            'type': 'html',
            'text_content': text_content,
            'titles': titles,
            'links': links,
            'images': images,
            'link_count': len(links),
            'image_count': len(images)
        }
    
    def _parse_xml(self, content: str) -> Dict:
        """解析XML"""
        # 提取标签
        tags = re.findall(r'<(\w+)[^>]*>', content)
        tag_count = Counter(tags)
        
        # 提取文本内容
        text_content = re.sub(r'<[^>]+>', ' ', content)
        text_content = re.sub(r'\s+', ' ', text_content).strip()
        
        return {
            'type': 'xml',
            'root_element': tags[0] if tags else None,
            'elements': dict(tag_count),
            'text_content': text_content
        }
    
    def _parse_yaml(self, content: str) -> Dict:
        """解析YAML"""
        # 简单YAML解析
        data = {}
        current_key = None
        current_list = []
        
        for line in content.split('\n'):
            line = line.rstrip()
            if not line or line.startswith('#'):
                continue
            
            # 键值对
            if ':' in line and not line.startswith(' '):
                if current_key and current_list:
                    data[current_key] = current_list
                key, value = line.split(':', 1)
                current_key = key.strip()
                value = value.strip()
                if value:
                    data[current_key] = value
                else:
                    current_list = []
            # 列表项
            elif line.strip().startswith('- '):
                item = line.strip()[2:]
                current_list.append(item)
        
        if current_key and current_list:
            data[current_key] = current_list
        
        return {
            'type': 'yaml',
            'data': data,
            'key_count': len(data)
        }
    
    def _parse_markdown(self, content: str) -> Dict:
        """解析Markdown"""
        # 提取标题
        headers = re.findall(r'^(#{1,6})\s+(.+)$', content, re.MULTILINE)
        headers = [(len(h[0]), h[1].strip()) for h in headers]
        
        # 提取代码块
        code_blocks = re.findall(r'```(\w+)?\n(.*?)```', content, re.DOTALL)
        
        # 提取链接
        links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
        
        # 提取图片
        images = re.findall(r'!\[([^\]]*)\]\(([^)]+)\)', content)
        
        # 提取列表
        lists = re.findall(r'^[\s]*[-*+]\s+(.+)$', content, re.MULTILINE)
        
        # 提取纯文本
        text_content = re.sub(r'```.*?```', '', content, flags=re.DOTALL)
        text_content = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', '', text_content)
        text_content = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'\1', text_content)
        text_content = re.sub(r'#{1,6}\s+', '', text_content)
        text_content = re.sub(r'\*+|_+', '', text_content)
        text_content = re.sub(r'\s+', ' ', text_content).strip()
        
        return {
            'type': 'markdown',
            'headers': headers,
            'code_blocks': [{'language': cb[0] or 'text', 'code': cb[1]} for cb in code_blocks],
            'links': [{'text': l[0], 'url': l[1]} for l in links],
            'images': [{'alt': i[0], 'url': i[1]} for i in images],
            'lists': lists,
            'text_content': text_content,
            'header_count': len(headers),
            'code_block_count': len(code_blocks),
            'link_count': len(links),
            'image_count': len(images)
        }
    
    def _parse_plain_text(self, content: str) -> Dict:
        """解析纯文本"""
        lines = content.split('\n')
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        # 检测是否是代码
        is_code = self._detect_code(content)
        
        return {
            'type': 'text',
            'content': content,
            'lines': lines,
            'paragraphs': paragraphs,
            'line_count': len(lines),
            'paragraph_count': len(paragraphs),
            'char_count': len(content),
            'is_code': is_code
        }
    
    def _detect_code(self, content: str) -> bool:
        """检测内容是否是代码"""
        code_indicators = [
            r'def\s+\w+\s*\(',
            r'class\s+\w+',
            r'function\s+\w+',
            r'const\s+\w+',
            r'var\s+\w+',
            r'let\s+\w+',
            r'import\s+',
            r'from\s+\w+\s+import',
            r'#include',
            r'public\s+static',
        ]
        
        for indicator in code_indicators:
            if re.search(indicator, content):
                return True
        
        return False


class ContentExtractor:
    """内容提取器"""
    
    def extract_entities(self, text: str) -> Dict:
        """
        提取文本中的实体
        
        Args:
            text: 文本内容
            
        Returns:
            提取的实体
        """
        entities = {
            'emails': self._extract_emails(text),
            'urls': self._extract_urls(text),
            'phones': self._extract_phones(text),
            'dates': self._extract_dates(text),
            'numbers': self._extract_numbers(text),
            'ips': self._extract_ips(text),
            'hashtags': self._extract_hashtags(text),
            'mentions': self._extract_mentions(text)
        }
        
        return entities
    
    def _extract_emails(self, text: str) -> List[str]:
        """提取邮箱地址"""
        pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        return list(set(re.findall(pattern, text)))
    
    def _extract_urls(self, text: str) -> List[str]:
        """提取URL"""
        pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s]*'
        return list(set(re.findall(pattern, text)))
    
    def _extract_phones(self, text: str) -> List[str]:
        """提取电话号码"""
        pattern = r'(?:\+?86)?1[3-9]\d{9}|\d{3,4}-\d{7,8}|\(\d{3,4}\)\s*\d{7,8}'
        return list(set(re.findall(pattern, text)))
    
    def _extract_dates(self, text: str) -> List[str]:
        """提取日期"""
        patterns = [
            r'\d{4}-\d{2}-\d{2}',
            r'\d{4}/\d{2}/\d{2}',
            r'\d{2}-\d{2}-\d{4}',
            r'\d{2}/\d{2}/\d{4}',
            r'\d{4}年\d{1,2}月\d{1,2}日'
        ]
        
        dates = []
        for pattern in patterns:
            dates.extend(re.findall(pattern, text))
        
        return list(set(dates))
    
    def _extract_numbers(self, text: str) -> List[float]:
        """提取数字"""
        pattern = r'-?\d+\.?\d*'
        numbers = re.findall(pattern, text)
        return [float(n) for n in numbers if n not in ['.', '-']]
    
    def _extract_ips(self, text: str) -> List[str]:
        """提取IP地址"""
        pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
        return list(set(re.findall(pattern, text)))
    
    def _extract_hashtags(self, text: str) -> List[str]:
        """提取话题标签"""
        pattern = r'#\w+'
        return list(set(re.findall(pattern, text)))
    
    def _extract_mentions(self, text: str) -> List[str]:
        """提取@提及"""
        pattern = r'@\w+'
        return list(set(re.findall(pattern, text)))


class SmartSummarizer:
    """智能摘要生成器"""
    
    def generate_summary(self, text: str, max_length: int = 200) -> str:
        """
        生成文本摘要
        
        Args:
            text: 原文本
            max_length: 最大长度
            
        Returns:
            摘要文本
        """
        sentences = self._split_sentences(text)
        
        if not sentences:
            return ""
        
        if len(sentences) <= 3:
            return ' '.join(sentences)
        
        # 计算句子重要性
        word_freq = self._calculate_word_frequency(text)
        sentence_scores = {}
        
        for i, sentence in enumerate(sentences):
            score = self._calculate_sentence_score(sentence, word_freq)
            sentence_scores[i] = score
        
        # 选择最重要的句子
        important_indices = sorted(sentence_scores.keys(), 
                                   key=lambda x: sentence_scores[x], 
                                   reverse=True)[:3]
        important_indices.sort()  # 保持原始顺序
        
        summary_sentences = [sentences[i] for i in important_indices]
        summary = ' '.join(summary_sentences)
        
        # 截断到最大长度
        if len(summary) > max_length:
            summary = summary[:max_length].rsplit(' ', 1)[0] + '...'
        
        return summary
    
    def extract_keywords(self, text: str, top_n: int = 10) -> List[str]:
        """
        提取关键词
        
        Args:
            text: 文本内容
            top_n: 关键词数量
            
        Returns:
            关键词列表
        """
        # 分词（简单实现）
        words = re.findall(r'\b[a-zA-Z\u4e00-\u9fa5]+\b', text.lower())
        
        # 过滤停用词
        stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                      'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                      'would', 'could', 'should', 'may', 'might', 'must', 'shall',
                      'can', 'need', 'dare', 'ought', 'used', '的', '了', '在', '是',
                      '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上',
                      '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有',
                      '看', '好', '自己', '这'}
        
        words = [w for w in words if w not in stop_words and len(w) > 1]
        
        # 统计词频
        word_freq = Counter(words)
        
        # 返回高频词
        return [word for word, count in word_freq.most_common(top_n)]
    
    def _split_sentences(self, text: str) -> List[str]:
        """分割句子"""
        # 支持中英文句子分割
        pattern = r'[^。！？.!?]+[。！？.!?]'
        sentences = re.findall(pattern, text)
        
        if not sentences:
            # 如果没有标点，按换行分割
            sentences = [s.strip() for s in text.split('\n') if s.strip()]
        
        return sentences
    
    def _calculate_word_frequency(self, text: str) -> Dict[str, float]:
        """计算词频"""
        words = re.findall(r'\b[a-zA-Z\u4e00-\u9fa5]+\b', text.lower())
        word_count = Counter(words)
        total = len(words)
        
        return {word: count / total for word, count in word_count.items()}
    
    def _calculate_sentence_score(self, sentence: str, word_freq: Dict[str, float]) -> float:
        """计算句子重要性分数"""
        words = re.findall(r'\b[a-zA-Z\u4e00-\u9fa5]+\b', sentence.lower())
        
        if not words:
            return 0
        
        score = sum(word_freq.get(word, 0) for word in words)
        
        # 位置加权（开头和结尾的句子更重要）
        # 这里简化处理
        
        return score / len(words)


class FormatConverter:
    """格式转换器"""
    
    def convert(self, content: str, from_format: str, to_format: str) -> str:
        """
        转换文档格式
        
        Args:
            content: 原始内容
            from_format: 源格式
            to_format: 目标格式
            
        Returns:
            转换后的内容
        """
        from_format = from_format.lower()
        to_format = to_format.lower()
        
        # 先解析源格式
        parser = DocumentParser()
        parsed = parser.parse_document(content, from_format)
        
        # 转换为目标格式
        if to_format == 'json':
            return json.dumps(parsed, ensure_ascii=False, indent=2)
        elif to_format == 'markdown':
            return self._to_markdown(parsed)
        elif to_format == 'html':
            return self._to_html(parsed)
        elif to_format == 'text':
            return self._to_text(parsed)
        else:
            return content
    
    def _to_markdown(self, parsed: Dict) -> str:
        """转换为Markdown"""
        if 'text_content' in parsed:
            return parsed['text_content']
        elif 'data' in parsed:
            return json.dumps(parsed['data'], ensure_ascii=False, indent=2)
        else:
            return str(parsed)
    
    def _to_html(self, parsed: Dict) -> str:
        """转换为HTML"""
        if parsed.get('type') == 'markdown':
            html = parsed.get('text_content', '')
            # 简单转换
            html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
            html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
            html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
            html = f"<html><body>{html}</body></html>"
            return html
        else:
            content = parsed.get('text_content', str(parsed))
            return f"<html><body><pre>{content}</pre></body></html>"
    
    def _to_text(self, parsed: Dict) -> str:
        """转换为纯文本"""
        if 'text_content' in parsed:
            return parsed['text_content']
        elif 'content' in parsed:
            return parsed['content']
        else:
            return str(parsed)


class IntelligentDocumentProcessor:
    """智能文档处理器主类"""
    
    def __init__(self):
        self.parser = DocumentParser()
        self.extractor = ContentExtractor()
        self.summarizer = SmartSummarizer()
        self.converter = FormatConverter()
    
    def process_document(self, content: str, format_type: str, 
                        extract_entities: bool = True,
                        generate_summary: bool = True,
                        extract_keywords: bool = True) -> DocumentProcessingResult:
        """
        处理文档
        
        Args:
            content: 文档内容
            format_type: 文档格式
            extract_entities: 是否提取实体
            generate_summary: 是否生成摘要
            extract_keywords: 是否提取关键词
            
        Returns:
            处理结果
        """
        import time
        start_time = time.time()
        
        try:
            # 1. 解析文档
            parsed = self.parser.parse_document(content, format_type)
            
            # 2. 提取文本内容
            text_content = parsed.get('text_content', '')
            if not text_content:
                text_content = parsed.get('content', str(parsed))
            
            result = DocumentProcessingResult(
                success=True,
                content=text_content,
                metadata={
                    'format': format_type,
                    'parsed_type': parsed.get('type'),
                    'processing_time': datetime.now().isoformat()
                }
            )
            
            # 3. 提取实体
            if extract_entities:
                result.extracted_data = self.extractor.extract_entities(text_content)
            
            # 4. 生成摘要
            if generate_summary and len(text_content) > 100:
                result.summary = self.summarizer.generate_summary(text_content)
            
            # 5. 提取关键词
            if extract_keywords:
                result.keywords = self.summarizer.extract_keywords(text_content)
            
            # 6. 添加解析信息
            if 'header_count' in parsed:
                result.metadata['header_count'] = parsed['header_count']
            if 'link_count' in parsed:
                result.metadata['link_count'] = parsed['link_count']
            
            result.processing_time = time.time() - start_time
            
            return result
            
        except Exception as e:
            return DocumentProcessingResult(
                success=False,
                error=str(e),
                processing_time=time.time() - start_time
            )
    
    def convert_format(self, content: str, from_format: str, to_format: str) -> str:
        """转换文档格式"""
        return self.converter.convert(content, from_format, to_format)


# 全局实例
document_processor = IntelligentDocumentProcessor()


# 便捷函数
def process_document(content: str, format_type: str, **options) -> DocumentProcessingResult:
    """处理文档便捷函数"""
    return document_processor.process_document(content, format_type, **options)


def convert_document(content: str, from_format: str, to_format: str) -> str:
    """转换文档格式便捷函数"""
    return document_processor.convert_format(content, from_format, to_format)


def extract_content(text: str) -> Dict:
    """提取内容便捷函数"""
    return document_processor.extractor.extract_entities(text)


def summarize_text(text: str, max_length: int = 200) -> str:
    """生成摘要便捷函数"""
    return document_processor.summarizer.generate_summary(text, max_length)


# 测试代码
if __name__ == '__main__':
    print("=" * 60)
    print("智能文档处理模块测试")
    print("=" * 60)
    
    # 测试Markdown文档
    test_md = """
# 项目报告

## 概述

这是一个重要的项目，联系邮箱：test@example.com。

### 主要功能

- 功能1：数据分析
- 功能2：文档处理
- 功能3：智能推荐

访问我们的网站：https://example.com

### 代码示例

```python
def hello():
    print("Hello World")
```

项目完成日期：2024-03-15

#项目 #AI #数据分析
    """
    
    print("\n1. Markdown文档处理测试")
    result = process_document(test_md, 'markdown')
    
    if result.success:
        print(f"处理成功，耗时: {result.processing_time:.3f}s")
        print(f"内容长度: {len(result.content)} 字符")
        print(f"摘要: {result.summary[:100]}...")
        print(f"关键词: {', '.join(result.keywords[:5])}")
        print(f"提取的邮箱: {result.extracted_data.get('emails', [])}")
        print(f"提取的URL: {result.extracted_data.get('urls', [])}")
    else:
        print(f"处理失败: {result.error}")
    
    # 测试格式转换
    print("\n2. 格式转换测试")
    json_content = '{"name": "test", "value": 123}'
    converted = convert_document(json_content, 'json', 'markdown')
    print(f"JSON转Markdown:\n{converted}")
    
    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)
