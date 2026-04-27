#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户引导系统 - 设备首次登录使用说明
功能: 首次登录检测、使用说明展示、引导流程
"""

import json
import os
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


# 使用说明数据
USER_GUIDE_CONTENT = {
    "welcome": {
        "title": "欢迎使用辉夜AI平台",
        "content": """
👋 欢迎！辉夜AI平台是一个功能强大的AI助手平台，为您提供智能对话、代码执行、知识管理等多种功能。

🎯 核心功能:
• 💬 智能对话 - 与AI进行自然语言交流
• 🛠️ 工具调用 - 使用各种实用工具
• 💻 代码执行 - 运行和调试代码
• 📚 知识库 - 管理和检索知识
• 🔧 增强功能 - 工作流、Agent、MCP等高级功能

⚡ 快速开始:
1. 在下方输入框输入您的问题或需求
2. 按 Enter 或点击发送按钮
3. 等待AI回复
        """
    },
    
    "basic_chat": {
        "title": "基础对话功能",
        "content": """
💬 基础对话是最常用的功能，您可以直接与AI交流。

📝 使用方法:
• 在输入框输入问题或话题
• 支持多轮对话，AI会记住上下文
• 使用 Shift+Enter 换行

🎭 角色系统:
• 点击右上角角色卡选择不同角色
• 每个角色有独特的性格和风格
• 选择"关闭角色卡"使用默认模式

💡 提示技巧:
• 问题越具体，回答越准确
• 可以要求AI扮演特定角色
• 支持中文和英文对话
        """
    },
    
    "tools": {
        "title": "工具调用功能",
        "content": """
🛠️ 工具调用让AI能够使用各种实用工具来完成任务。

📦 可用工具:
• 🔢 计算器 - 复杂数学计算
• 📊 统计分析 - 数据分析统计
• 🔍 网络搜索 - 搜索网络信息
• 📝 代码格式化 - 格式化代码
• 🔗 URL分析 - 解析URL结构
• 🔤 正则测试 - 测试正则表达式

⚙️ 使用方法:
1. 在对话中描述您需要使用的工具
2. AI会自动识别并调用合适的工具
3. 查看工具执行结果

⚠️ 注意: 工具功能需要配置外部API才能使用
        """
    },
    
    "code_execution": {
        "title": "代码执行功能",
        "content": """
💻 代码执行功能支持多种编程语言的运行和调试。

🌐 支持语言:
• Python - 数据分析、算法实现
• JavaScript - Web开发、脚本编写
• Bash - 系统命令、自动化脚本
• SQL - 数据库查询

🔒 安全特性:
• 代码安全检查，防止危险操作
• 执行超时控制（30秒）
• 资源使用限制

📊 代码分析:
• 自动分析代码质量
• 计算复杂度评估
• 提供优化建议

⚠️ 注意: 代码执行需要配置外部API才能使用
        """
    },
    
    "knowledge_base": {
        "title": "知识库功能",
        "content": """
📚 知识库功能帮助您管理和检索个人知识。

📝 添加知识:
• 点击"知识库"标签
• 输入或粘贴文本内容
• 系统自动生成摘要和标签

🔍 检索知识:
• 在对话中引用知识库
• 支持语义搜索
• 自动关联相关内容

🏷️ 知识管理:
• 自动标签分类
• 智能摘要生成
• 支持导出导入

⚠️ 注意: 知识库功能需要配置外部API才能使用
        """
    },
    
    "advanced_features": {
        "title": "增强功能介绍",
        "content": """
🚀 增强功能提供更强大的AI能力。

📋 工作流:
• 可视化流程设计
• 自动化任务执行
• 支持条件分支和循环

🤖 Agent系统:
• 自主任务执行
• 多步骤问题解决
• 智能决策能力

🔌 MCP插件:
• 扩展AI能力
• 自定义工具集成
• 第三方服务接入

👥 多Agent协作:
• 多个AI协同工作
• 角色分工明确
• 复杂任务分解

⚠️ 注意: 所有增强功能都需要配置外部API才能使用
        """
    },
    
    "api_config": {
        "title": "配置外部API",
        "content": """
🔑 配置外部API以使用增强功能。

📋 支持的API提供商:
• OpenAI (GPT-4, GPT-3.5)
• Claude (Anthropic)
• DeepSeek
• 通义千问 (阿里)
• 文心一言 (百度)
• Moonshot (Kimi)
• 智谱AI (GLM)

⚙️ 配置步骤:
1. 点击右上角设置图标
2. 选择"API配置"
3. 选择要配置的提供商
4. 输入API密钥
5. 启用该提供商

💡 提示:
• 可以从各AI平台官网获取API密钥
• 建议配置多个提供商作为备用
• API调用会产生费用，请注意用量
        """
    },
    
    "shortcuts": {
        "title": "快捷键和技巧",
        "content": """
⌨️ 快捷键让操作更高效。

🎯 常用快捷键:
• Enter - 发送消息
• Shift+Enter - 换行
• Ctrl+/ - 聚焦输入框
• Esc - 取消输入

💡 使用技巧:
• 输入 / 快速访问命令
• 使用 @ 引用知识库
• 拖拽文件上传
• 右键消息可复制

🎨 界面定制:
• 点击主题切换明暗模式
• 调整字体大小
• 自定义快捷键
• 设置自动保存
        """
    },
    
    "faq": {
        "title": "常见问题",
        "content": """
❓ 常见问题解答。

Q: 为什么增强功能无法使用？
A: 增强功能需要配置外部API，请在设置中配置API密钥。

Q: 如何切换AI模型？
A: 在设置中选择不同的API提供商和模型。

Q: 对话历史会保存吗？
A: 是的，对话历史会自动保存，支持导出。

Q: 支持哪些文件格式？
A: 支持文本文件、代码文件、PDF、图片等多种格式。

Q: 如何保护隐私数据？
A: 敏感数据建议使用本地模型，不上传到外部API。

Q: 遇到错误怎么办？
A: 查看错误提示，检查网络连接，或联系管理员。
        """
    }
}


@dataclass
class DeviceGuideStatus:
    """设备引导状态"""
    device_id: str
    first_visit: bool
    guide_completed: bool
    guide_version: str
    last_guide_time: Optional[str] = None
    completed_sections: List[str] = None
    
    def __post_init__(self):
        if self.completed_sections is None:
            self.completed_sections = []


class UserGuideSystem:
    """用户引导系统"""
    
    GUIDE_VERSION = "1.0.0"
    GUIDE_STATUS_FILE = "device_guide_status.json"
    
    def __init__(self, storage_dir: str = "./guide_data"):
        self.storage_dir = storage_dir
        self.status_file = os.path.join(storage_dir, self.GUIDE_STATUS_FILE)
        self._ensure_storage()
        self._status_cache: Dict[str, DeviceGuideStatus] = {}
    
    def _ensure_storage(self):
        """确保存储目录存在"""
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)
    
    def _load_all_status(self) -> Dict[str, dict]:
        """加载所有设备状态"""
        if os.path.exists(self.status_file):
            try:
                with open(self.status_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_all_status(self, all_status: Dict[str, dict]):
        """保存所有设备状态"""
        with open(self.status_file, 'w', encoding='utf-8') as f:
            json.dump(all_status, f, ensure_ascii=False, indent=2)
    
    def get_device_status(self, device_id: str) -> DeviceGuideStatus:
        """获取设备引导状态"""
        # 检查缓存
        if device_id in self._status_cache:
            return self._status_cache[device_id]
        
        # 从文件加载
        all_status = self._load_all_status()
        
        if device_id in all_status:
            status_data = all_status[device_id]
            status = DeviceGuideStatus(**status_data)
        else:
            # 新设备
            status = DeviceGuideStatus(
                device_id=device_id,
                first_visit=True,
                guide_completed=False,
                guide_version=self.GUIDE_VERSION
            )
        
        self._status_cache[device_id] = status
        return status
    
    def save_device_status(self, status: DeviceGuideStatus):
        """保存设备引导状态"""
        all_status = self._load_all_status()
        all_status[status.device_id] = asdict(status)
        self._save_all_status(all_status)
        self._status_cache[status.device_id] = status
    
    def is_first_visit(self, device_id: str) -> bool:
        """检查是否是首次访问"""
        status = self.get_device_status(device_id)
        return status.first_visit
    
    def mark_guide_completed(self, device_id: str):
        """标记引导已完成"""
        status = self.get_device_status(device_id)
        status.first_visit = False
        status.guide_completed = True
        status.last_guide_time = datetime.now().isoformat()
        self.save_device_status(status)
    
    def mark_section_completed(self, device_id: str, section_id: str):
        """标记某个章节已完成"""
        status = self.get_device_status(device_id)
        if section_id not in status.completed_sections:
            status.completed_sections.append(section_id)
            self.save_device_status(status)
    
    def get_guide_content(self, section_id: Optional[str] = None) -> dict:
        """获取使用说明内容"""
        if section_id and section_id in USER_GUIDE_CONTENT:
            return {
                'section_id': section_id,
                **USER_GUIDE_CONTENT[section_id]
            }
        
        # 返回所有内容
        return {
            'sections': [
                {'section_id': k, 'title': v['title']}
                for k, v in USER_GUIDE_CONTENT.items()
            ],
            'content': USER_GUIDE_CONTENT
        }
    
    def get_next_guide_section(self, device_id: str) -> Optional[dict]:
        """获取下一个未完成的引导章节"""
        status = self.get_device_status(device_id)
        
        for section_id in USER_GUIDE_CONTENT.keys():
            if section_id not in status.completed_sections:
                return self.get_guide_content(section_id)
        
        return None
    
    def reset_guide(self, device_id: str):
        """重置引导状态"""
        status = DeviceGuideStatus(
            device_id=device_id,
            first_visit=True,
            guide_completed=False,
            guide_version=self.GUIDE_VERSION,
            completed_sections=[]
        )
        self.save_device_status(status)


# 全局实例
guide_system = UserGuideSystem()


# API路由处理函数（用于Flask集成）
def handle_guide_api(action: str, device_id: str, **kwargs) -> dict:
    """
    处理引导系统API请求
    
    Args:
        action: 操作类型
        device_id: 设备ID
        **kwargs: 其他参数
    
    Returns:
        API响应数据
    """
    try:
        if action == 'check_first_visit':
            is_first = guide_system.is_first_visit(device_id)
            return {
                'success': True,
                'is_first_visit': is_first,
                'device_id': device_id
            }
        
        elif action == 'get_guide_content':
            section_id = kwargs.get('section_id')
            content = guide_system.get_guide_content(section_id)
            return {
                'success': True,
                'data': content
            }
        
        elif action == 'get_next_section':
            next_section = guide_system.get_next_guide_section(device_id)
            return {
                'success': True,
                'data': next_section,
                'has_more': next_section is not None
            }
        
        elif action == 'mark_section_completed':
            section_id = kwargs.get('section_id')
            if section_id:
                guide_system.mark_section_completed(device_id, section_id)
            return {
                'success': True,
                'message': f'章节 {section_id} 已标记完成'
            }
        
        elif action == 'complete_guide':
            guide_system.mark_guide_completed(device_id)
            return {
                'success': True,
                'message': '引导已完成'
            }
        
        elif action == 'get_status':
            status = guide_system.get_device_status(device_id)
            return {
                'success': True,
                'data': asdict(status)
            }
        
        elif action == 'reset_guide':
            guide_system.reset_guide(device_id)
            return {
                'success': True,
                'message': '引导已重置'
            }
        
        else:
            return {
                'success': False,
                'error': f'未知操作: {action}'
            }
    
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


# 测试代码
if __name__ == '__main__':
    print("=" * 60)
    print("用户引导系统测试")
    print("=" * 60)
    
    # 创建测试实例
    test_system = UserGuideSystem(storage_dir="./test_guide_data")
    
    # 测试设备ID
    test_device_id = "device_test_001"
    
    # 测试首次访问检查
    print("\n1. 首次访问检查")
    is_first = test_system.is_first_visit(test_device_id)
    print(f"是否首次访问: {is_first}")
    
    # 测试获取引导内容
    print("\n2. 获取引导内容")
    content = test_system.get_guide_content()
    print(f"章节数量: {len(content['sections'])}")
    print(f"章节列表: {[s['title'] for s in content['sections']]}")
    
    # 测试获取单个章节
    print("\n3. 获取单个章节")
    welcome = test_system.get_guide_content('welcome')
    print(f"章节标题: {welcome['title']}")
    
    # 测试标记章节完成
    print("\n4. 标记章节完成")
    test_system.mark_section_completed(test_device_id, 'welcome')
    status = test_system.get_device_status(test_device_id)
    print(f"已完成章节: {status.completed_sections}")
    
    # 测试获取下一个章节
    print("\n5. 获取下一个章节")
    next_section = test_system.get_next_guide_section(test_device_id)
    print(f"下一个章节: {next_section['title'] if next_section else '无'}")
    
    # 测试完成引导
    print("\n6. 完成引导")
    test_system.mark_guide_completed(test_device_id)
    status = test_system.get_device_status(test_device_id)
    print(f"引导完成: {status.guide_completed}")
    print(f"首次访问: {status.first_visit}")
    
    # 测试API处理函数
    print("\n7. API处理函数测试")
    result = handle_guide_api('check_first_visit', test_device_id)
    print(f"API结果: {result}")
    
    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)
