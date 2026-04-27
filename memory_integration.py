#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记忆系统集成模块
将高级记忆系统集成到主应用中
"""

import json
import time
from typing import List, Dict, Optional, Any
from advanced_memory_system import (
    AdvancedMemoryManager, MemoryTier, MemoryType, Memory
)

class ConversationMemory:
    """对话记忆包装器"""
    
    def __init__(self, llm_func=None):
        self.manager = AdvancedMemoryManager(llm_func)
        self.current_conversation_id = None
        self.conversation_history = []
    
    def start_conversation(self, conversation_id: str = None):
        """开始新对话"""
        self.current_conversation_id = conversation_id or f"conv_{int(time.time())}"
        self.conversation_history = []
    
    def add_message(self, role: str, content: str, 
                   metadata: Dict = None):
        """添加消息到记忆"""
        # 添加到工作记忆
        self.manager.add_to_working_memory(content, role)
        
        # 记录到对话历史
        message = {
            'role': role,
            'content': content,
            'timestamp': time.time(),
            'metadata': metadata or {}
        }
        self.conversation_history.append(message)
    
    def get_context_for_llm(self, query: str = None, 
                           max_tokens: int = 2000) -> str:
        """
        获取LLM的上下文
        结合工作记忆和相关历史记忆
        """
        context_parts = []
        
        # 1. 系统提示
        context_parts.append("以下是与用户相关的背景信息：")
        
        # 2. 检索相关记忆
        if query:
            relevant_memories = self.manager.retrieve_relevant(
                query, top_k=5, 
                tiers=[MemoryTier.WORKING, MemoryTier.LONG_TERM]
            )
            
            if relevant_memories:
                context_parts.append("\n[相关记忆]")
                for mem in relevant_memories:
                    context_parts.append(f"- {mem.content}")
        
        # 3. 最近对话历史（工作记忆）
        recent_messages = self.conversation_history[-10:]  # 最近10条
        if recent_messages:
            context_parts.append("\n[最近对话]")
            for msg in recent_messages:
                role_name = "用户" if msg['role'] == 'user' else "助手"
                context_parts.append(f"{role_name}: {msg['content'][:200]}")
        
        # 4. 用户偏好（高重要性）
        preferences = self._get_user_preferences()
        if preferences:
            context_parts.append("\n[用户偏好]")
            for pref in preferences:
                context_parts.append(f"- {pref}")
        
        context_parts.append("\n请基于以上信息回答用户的问题。")
        
        return "\n".join(context_parts)
    
    def _get_user_preferences(self) -> List[str]:
        """获取用户偏好"""
        # 从长期记忆中检索偏好类型的记忆
        all_memories = self.manager._load_memories_from_db([MemoryTier.LONG_TERM])
        preferences = [
            m.content for m in all_memories 
            if m.memory_type == MemoryType.PREFERENCE and m.importance > 0.7
        ]
        return preferences[:5]  # 最多5个
    
    def end_conversation(self):
        """结束对话，进行记忆蒸馏"""
        if len(self.conversation_history) > 5:
            # 蒸馏整个对话
            distilled = self.manager.distiller.distill_conversation(
                self.conversation_history
            )
            
            # 存储蒸馏后的记忆
            for mem in distilled:
                mem.source = self.current_conversation_id
                self.manager.store_memory(mem)
            
            print(f"✓ 对话已蒸馏，提取了 {len(distilled)} 个记忆")
        
        # 清空工作记忆
        self.manager.working_memory = []
        self.conversation_history = []
    
    def remember_fact(self, fact: str, importance: float = 0.7):
        """记住一个事实"""
        mem = Memory(
            id=f"fact_{int(time.time() * 1000)}",
            content=fact,
            memory_type=MemoryType.FACT,
            tier=MemoryTier.LONG_TERM,
            importance=importance,
            created_at=time.time(),
            last_accessed=time.time(),
            access_count=0
        )
        self.manager.store_memory(mem)
    
    def remember_preference(self, preference: str, importance: float = 0.9):
        """记住用户偏好"""
        mem = Memory(
            id=f"pref_{int(time.time() * 1000)}",
            content=preference,
            memory_type=MemoryType.PREFERENCE,
            tier=MemoryTier.LONG_TERM,
            importance=importance,
            created_at=time.time(),
            last_accessed=time.time(),
            access_count=0
        )
        self.manager.store_memory(mem)
    
    def get_memory_summary(self) -> str:
        """获取记忆摘要"""
        stats = self.manager.get_memory_stats()
        
        summary = f"""
记忆系统状态:
- 工作记忆: {stats.get('working_memory_count', 0)} 条
- 长期记忆: {stats.get('long_term_count', 0)} 条
- 短期记忆: {stats.get('short_term_count', 0)} 条
- 情景记忆: {stats.get('episodic_count', 0)} 条
- 语义记忆: {stats.get('semantic_count', 0)} 条
- 总记忆数: {stats.get('total_count', 0)} 条
- 平均重要性: {stats.get('avg_importance', 0):.2f}
"""
        return summary
    
    def search_memories(self, query: str, top_k: int = 10) -> List[Dict]:
        """搜索记忆"""
        results = self.manager.retrieve_relevant(query, top_k=top_k)
        
        return [
            {
                'content': mem.content,
                'type': mem.memory_type.value,
                'tier': mem.tier.value,
                'importance': mem.importance,
                'relevance_score': mem.relevance_score,
                'created_at': mem.created_at
            }
            for mem in results
        ]
    
    def consolidate(self):
        """手动触发记忆整合"""
        self.manager.consolidate_memories()

class MemoryEnhancedChat:
    """增强记忆的对话类"""
    
    def __init__(self, llm_func=None):
        self.memory = ConversationMemory(llm_func)
        self.llm = llm_func
    
    def chat(self, user_message: str, 
            system_prompt: str = None) -> str:
        """
        进行对话，自动使用记忆增强
        
        Args:
            user_message: 用户消息
            system_prompt: 可选的系统提示
        
        Returns:
            AI回复
        """
        # 1. 添加用户消息到记忆
        self.memory.add_message('user', user_message)
        
        # 2. 构建增强的提示
        memory_context = self.memory.get_context_for_llm(user_message)
        
        full_prompt = f"""{system_prompt or '你是一个有用的AI助手。'}

{memory_context}

用户当前问题: {user_message}

请回答:"""
        
        # 3. 调用LLM
        if self.llm:
            response = self.llm(full_prompt)
        else:
            response = "[LLM未配置，无法生成回复]"
        
        # 4. 添加AI回复到记忆
        self.memory.add_message('assistant', response)
        
        return response
    
    def save_important_info(self, info: str, info_type: str = "fact"):
        """保存重要信息"""
        if info_type == "preference":
            self.memory.remember_preference(info)
        else:
            self.memory.remember_fact(info)
    
    def get_stats(self) -> str:
        """获取统计信息"""
        return self.memory.get_memory_summary()

# 与现有系统的集成函数
def integrate_with_qwen3_web():
    """
    集成到现有的 qwen3_web.py 系统
    这个函数展示了如何修改现有代码以使用新记忆系统
    """
    integration_code = '''
# 在 qwen3_web.py 中添加以下代码：

from memory_integration import ConversationMemory, MemoryEnhancedChat

# 全局记忆管理器（替代原有的记忆系统）
memory_manager = ConversationMemory(generate_response)

# 修改 chat 路由
@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    message = data.get('message', '')
    conversation_id = data.get('conversation_id', 'default')
    
    # 添加用户消息到记忆
    memory_manager.add_message('user', message)
    
    # 获取记忆增强的上下文
    context = memory_manager.get_context_for_llm(message)
    
    # 构建完整提示
    full_prompt = f"{context}\\n\\n用户: {message}\\n助手:"
    
    # 生成回复
    response = generate_response(full_prompt)
    
    # 添加AI回复到记忆
    memory_manager.add_message('assistant', response)
    
    return jsonify({
        'response': response,
        'conversation_id': conversation_id
    })

# 修改记忆相关路由
@app.route('/memory/enhanced/stats')
def enhanced_memory_stats():
    return jsonify(memory_manager.get_memory_summary())

@app.route('/memory/enhanced/search', methods=['POST'])
def enhanced_memory_search():
    data = request.get_json()
    query = data.get('query', '')
    results = memory_manager.search_memories(query)
    return jsonify({'results': results})

@app.route('/memory/enhanced/consolidate', methods=['POST'])
def consolidate_memories():
    memory_manager.consolidate()
    return jsonify({'status': 'success', 'message': '记忆整合完成'})
'''
    return integration_code

# 便捷函数
def create_memory_chat(llm_func=None) -> MemoryEnhancedChat:
    """创建增强记忆的对话实例"""
    return MemoryEnhancedChat(llm_func)

if __name__ == '__main__':
    # 模拟LLM函数
    def mock_llm(prompt):
        return f"[模拟回复] 收到提示长度: {len(prompt)}"
    
    # 创建增强对话
    chat = MemoryEnhancedChat(mock_llm)
    
    # 开始对话
    chat.memory.start_conversation("test_001")
    
    # 进行多轮对话
    print("="*60)
    print("增强记忆对话测试")
    print("="*60)
    
    responses = [
        chat.chat("你好，我叫张三"),
        chat.chat("我喜欢Python编程"),
        chat.chat("请帮我写一个排序算法"),
        chat.chat("你还记得我叫什么吗？"),  # 应该记得"张三"
    ]
    
    for i, response in enumerate(responses, 1):
        print(f"\n对话 {i}:")
        print(f"  AI: {response[:100]}...")
    
    # 显示记忆统计
    print("\n" + "="*60)
    print(chat.get_stats())
    
    # 搜索记忆
    print("\n搜索记忆 'Python':")
    results = chat.memory.search_memories("Python")
    for r in results:
        print(f"  - {r['content'][:50]}... (相关度: {r['relevance_score']:.3f})")
    
    # 结束对话
    chat.memory.end_conversation()
