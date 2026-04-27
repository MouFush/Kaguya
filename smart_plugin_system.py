#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能插件系统 - 动态扩展平台能力
功能: 插件管理、热加载、沙箱执行、权限控制
"""

import os
import sys
import json
import importlib
import importlib.util
import inspect
import hashlib
import threading
from typing import Dict, List, Any, Optional, Callable, Type
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod
import traceback


class PluginStatus(Enum):
    """插件状态"""
    INSTALLED = "installed"      # 已安装
    ACTIVE = "active"            # 运行中
    ERROR = "error"              # 错误
    DISABLED = "disabled"        # 已禁用
    UPDATING = "updating"        # 更新中


class PluginPriority(Enum):
    """插件优先级"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class PluginMetadata:
    """插件元数据"""
    id: str
    name: str
    version: str
    description: str = ""
    author: str = ""
    email: str = ""
    url: str = ""
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    priority: PluginPriority = PluginPriority.NORMAL
    min_platform_version: str = "1.0.0"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


class PluginInterface(ABC):
    """插件接口基类"""
    
    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """返回插件元数据"""
        pass
    
    @abstractmethod
    def initialize(self, context: Dict[str, Any]) -> bool:
        """初始化插件"""
        pass
    
    @abstractmethod
    def execute(self, command: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行插件命令"""
        pass
    
    @abstractmethod
    def shutdown(self) -> bool:
        """关闭插件"""
        pass
    
    def get_capabilities(self) -> List[str]:
        """获取插件能力列表"""
        return []
    
    def on_event(self, event_type: str, event_data: Dict[str, Any]):
        """事件处理器"""
        pass


class PluginSandbox:
    """插件沙箱 - 安全执行环境"""
    
    # 允许的标准库模块
    ALLOWED_MODULES = {
        'json', 're', 'math', 'random', 'datetime', 'collections',
        'itertools', 'functools', 'typing', 'string', 'hashlib',
        'base64', 'urllib.parse', 'time', 'uuid', 'copy'
    }
    
    # 禁止的函数/属性
    FORBIDDEN_ATTRS = [
        '__import__', 'eval', 'exec', 'compile', 'open',
        '__builtins__', '__globals__', '__closure__'
    ]
    
    def __init__(self, plugin_id: str):
        self.plugin_id = plugin_id
        self.allowed_modules = {}
        self._setup_safe_environment()
    
    def _setup_safe_environment(self):
        """设置安全执行环境"""
        for module_name in self.ALLOWED_MODULES:
            try:
                self.allowed_modules[module_name] = importlib.import_module(module_name)
            except ImportError:
                pass
    
    def create_safe_globals(self) -> Dict:
        """创建安全的全局命名空间"""
        safe_globals = {
            '__builtins__': {
                'True': True,
                'False': False,
                'None': None,
                'len': len,
                'range': range,
                'enumerate': enumerate,
                'zip': zip,
                'map': map,
                'filter': filter,
                'sum': sum,
                'min': min,
                'max': max,
                'abs': abs,
                'round': round,
                'str': str,
                'int': int,
                'float': float,
                'list': list,
                'dict': dict,
                'tuple': tuple,
                'set': set,
                'bool': bool,
                'type': type,
                'isinstance': isinstance,
                'hasattr': hasattr,
                'getattr': getattr,
                'setattr': setattr,
                'print': self._safe_print,
            }
        }
        
        # 添加允许的模块
        for name, module in self.allowed_modules.items():
            safe_globals[name] = module
        
        return safe_globals
    
    def _safe_print(self, *args, **kwargs):
        """安全的打印函数"""
        message = ' '.join(str(arg) for arg in args)
        print(f"[{self.plugin_id}] {message}")
    
    def execute_code(self, code: str, local_vars: Dict = None) -> Dict:
        """在沙箱中执行代码"""
        result = {
            'success': False,
            'output': None,
            'error': None
        }
        
        try:
            # 检查代码安全性
            if not self._is_code_safe(code):
                raise ValueError("代码包含不安全的内容")
            
            # 创建安全环境
            safe_globals = self.create_safe_globals()
            safe_locals = local_vars or {}
            
            # 执行代码
            exec(code, safe_globals, safe_locals)
            
            result['success'] = True
            result['output'] = safe_locals.get('__output__', None)
            
        except Exception as e:
            result['error'] = str(e)
            result['traceback'] = traceback.format_exc()
        
        return result
    
    def _is_code_safe(self, code: str) -> bool:
        """检查代码安全性"""
        # 检查禁止的属性
        for attr in self.FORBIDDEN_ATTRS:
            if attr in code:
                return False
        
        # 检查危险导入
        dangerous_imports = ['os', 'sys', 'subprocess', 'socket', 'requests']
        for imp in dangerous_imports:
            if f'import {imp}' in code or f'from {imp}' in code:
                return False
        
        return True


class PluginManager:
    """插件管理器"""
    
    def __init__(self, plugin_dir: str = './plugins'):
        self.plugin_dir = plugin_dir
        self.plugins: Dict[str, PluginInterface] = {}
        self.plugin_status: Dict[str, PluginStatus] = {}
        self.plugin_errors: Dict[str, str] = {}
        self.sandboxes: Dict[str, PluginSandbox] = {}
        self.hooks: Dict[str, List[Callable]] = {}
        self.lock = threading.RLock()
        
        # 创建插件目录
        os.makedirs(plugin_dir, exist_ok=True)
        
        # 加载已安装的插件
        self._load_all_plugins()
    
    def _load_all_plugins(self):
        """加载所有插件"""
        if not os.path.exists(self.plugin_dir):
            return
        
        for item in os.listdir(self.plugin_dir):
            plugin_path = os.path.join(self.plugin_dir, item)
            if os.path.isdir(plugin_path):
                # 检查是否是插件目录
                manifest_path = os.path.join(plugin_path, 'manifest.json')
                if os.path.exists(manifest_path):
                    self._load_plugin_from_directory(item)
    
    def _load_plugin_from_directory(self, plugin_id: str) -> bool:
        """从目录加载插件"""
        try:
            plugin_path = os.path.join(self.plugin_dir, plugin_id)
            manifest_path = os.path.join(plugin_path, 'manifest.json')
            
            # 读取manifest
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
            
            # 创建插件沙箱
            sandbox = PluginSandbox(plugin_id)
            self.sandboxes[plugin_id] = sandbox
            
            # 加载主模块
            main_file = manifest.get('main', 'main.py')
            main_path = os.path.join(plugin_path, main_file)
            
            if os.path.exists(main_path):
                # 动态加载模块
                spec = importlib.util.spec_from_file_location(
                    f"plugin_{plugin_id}", main_path
                )
                module = importlib.util.module_from_spec(spec)
                
                # 在沙箱中执行
                safe_globals = sandbox.create_safe_globals()
                module.__dict__.update(safe_globals)
                spec.loader.exec_module(module)
                
                # 查找插件类
                plugin_class = None
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, PluginInterface) and 
                        obj != PluginInterface):
                        plugin_class = obj
                        break
                
                if plugin_class:
                    plugin_instance = plugin_class()
                    
                    with self.lock:
                        self.plugins[plugin_id] = plugin_instance
                        self.plugin_status[plugin_id] = PluginStatus.INSTALLED
                    
                    return True
            
            return False
            
        except Exception as e:
            self.plugin_errors[plugin_id] = str(e)
            self.plugin_status[plugin_id] = PluginStatus.ERROR
            return False
    
    def install_plugin(self, plugin_package: bytes, plugin_id: str = None) -> Dict:
        """安装插件"""
        result = {
            'success': False,
            'plugin_id': None,
            'message': ''
        }
        
        try:
            import zipfile
            import io
            
            # 解压插件包
            zip_file = zipfile.ZipFile(io.BytesIO(plugin_package))
            
            # 获取插件ID
            if not plugin_id:
                # 从manifest读取
                manifest_content = zip_file.read('manifest.json').decode('utf-8')
                manifest = json.loads(manifest_content)
                plugin_id = manifest.get('id', f"plugin_{int(datetime.now().timestamp())}")
            
            # 创建插件目录
            plugin_path = os.path.join(self.plugin_dir, plugin_id)
            os.makedirs(plugin_path, exist_ok=True)
            
            # 解压文件
            zip_file.extractall(plugin_path)
            
            # 加载插件
            if self._load_plugin_from_directory(plugin_id):
                result['success'] = True
                result['plugin_id'] = plugin_id
                result['message'] = '插件安装成功'
            else:
                result['message'] = '插件安装失败: 无法加载插件'
                
        except Exception as e:
            result['message'] = f'插件安装失败: {str(e)}'
        
        return result
    
    def activate_plugin(self, plugin_id: str, context: Dict = None) -> bool:
        """激活插件"""
        with self.lock:
            if plugin_id not in self.plugins:
                return False
            
            plugin = self.plugins[plugin_id]
            
            try:
                # 初始化插件
                if plugin.initialize(context or {}):
                    self.plugin_status[plugin_id] = PluginStatus.ACTIVE
                    return True
                else:
                    self.plugin_status[plugin_id] = PluginStatus.ERROR
                    return False
                    
            except Exception as e:
                self.plugin_errors[plugin_id] = str(e)
                self.plugin_status[plugin_id] = PluginStatus.ERROR
                return False
    
    def deactivate_plugin(self, plugin_id: str) -> bool:
        """停用插件"""
        with self.lock:
            if plugin_id not in self.plugins:
                return False
            
            plugin = self.plugins[plugin_id]
            
            try:
                plugin.shutdown()
                self.plugin_status[plugin_id] = PluginStatus.DISABLED
                return True
            except Exception as e:
                return False
    
    def uninstall_plugin(self, plugin_id: str) -> bool:
        """卸载插件"""
        with self.lock:
            # 先停用
            if plugin_id in self.plugins:
                self.deactivate_plugin(plugin_id)
                del self.plugins[plugin_id]
            
            # 删除文件
            plugin_path = os.path.join(self.plugin_dir, plugin_id)
            if os.path.exists(plugin_path):
                import shutil
                shutil.rmtree(plugin_path)
            
            # 清理状态
            if plugin_id in self.plugin_status:
                del self.plugin_status[plugin_id]
            if plugin_id in self.plugin_errors:
                del self.plugin_errors[plugin_id]
            if plugin_id in self.sandboxes:
                del self.sandboxes[plugin_id]
            
            return True
    
    def execute_plugin_command(self, plugin_id: str, command: str, 
                              params: Dict = None) -> Dict:
        """执行插件命令"""
        with self.lock:
            if plugin_id not in self.plugins:
                return {'success': False, 'error': '插件不存在'}
            
            if self.plugin_status.get(plugin_id) != PluginStatus.ACTIVE:
                return {'success': False, 'error': '插件未激活'}
            
            plugin = self.plugins[plugin_id]
            
            try:
                result = plugin.execute(command, params or {})
                return {'success': True, 'result': result}
            except Exception as e:
                return {'success': False, 'error': str(e)}
    
    def get_plugin_info(self, plugin_id: str) -> Dict:
        """获取插件信息"""
        with self.lock:
            if plugin_id not in self.plugins:
                return {'error': '插件不存在'}
            
            plugin = self.plugins[plugin_id]
            
            return {
                'id': plugin_id,
                'metadata': asdict(plugin.metadata),
                'status': self.plugin_status.get(plugin_id, PluginStatus.ERROR).value,
                'capabilities': plugin.get_capabilities(),
                'error': self.plugin_errors.get(plugin_id, '')
            }
    
    def list_plugins(self) -> List[Dict]:
        """列出所有插件"""
        with self.lock:
            return [
                {
                    'id': plugin_id,
                    'name': plugin.metadata.name,
                    'version': plugin.metadata.version,
                    'status': self.plugin_status.get(plugin_id, PluginStatus.ERROR).value,
                    'priority': plugin.metadata.priority.value
                }
                for plugin_id, plugin in self.plugins.items()
            ]
    
    def register_hook(self, event: str, callback: Callable):
        """注册事件钩子"""
        if event not in self.hooks:
            self.hooks[event] = []
        self.hooks[event].append(callback)
    
    def trigger_event(self, event: str, data: Dict):
        """触发事件"""
        # 调用注册的钩子
        if event in self.hooks:
            for callback in self.hooks[event]:
                try:
                    callback(data)
                except:
                    pass
        
        # 通知所有激活的插件
        with self.lock:
            for plugin_id, plugin in self.plugins.items():
                if self.plugin_status.get(plugin_id) == PluginStatus.ACTIVE:
                    try:
                        plugin.on_event(event, data)
                    except:
                        pass
    
    def get_sandbox(self, plugin_id: str) -> Optional[PluginSandbox]:
        """获取插件沙箱"""
        return self.sandboxes.get(plugin_id)


# 示例插件实现
class ExamplePlugin(PluginInterface):
    """示例插件"""
    
    def __init__(self):
        self._metadata = PluginMetadata(
            id="example_plugin",
            name="示例插件",
            version="1.0.0",
            description="这是一个示例插件",
            author="辉夜AI团队",
            tags=["example", "demo"]
        )
        self.initialized = False
    
    @property
    def metadata(self) -> PluginMetadata:
        return self._metadata
    
    def initialize(self, context: Dict[str, Any]) -> bool:
        print(f"示例插件初始化，上下文: {context}")
        self.initialized = True
        return True
    
    def execute(self, command: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if command == "hello":
            name = params.get('name', 'World')
            return {'message': f'Hello, {name}!'}
        elif command == "add":
            a = params.get('a', 0)
            b = params.get('b', 0)
            return {'result': a + b}
        else:
            return {'error': f'未知命令: {command}'}
    
    def shutdown(self) -> bool:
        print("示例插件关闭")
        self.initialized = False
        return True
    
    def get_capabilities(self) -> List[str]:
        return ["hello", "add"]


# 全局插件管理器
plugin_manager = PluginManager()


# 便捷函数
def install_plugin(plugin_package: bytes, plugin_id: str = None) -> Dict:
    """安装插件"""
    return plugin_manager.install_plugin(plugin_package, plugin_id)


def activate_plugin(plugin_id: str, context: Dict = None) -> bool:
    """激活插件"""
    return plugin_manager.activate_plugin(plugin_id, context)


def execute_plugin_command(plugin_id: str, command: str, params: Dict = None) -> Dict:
    """执行插件命令"""
    return plugin_manager.execute_plugin_command(plugin_id, command, params)


def list_plugins() -> List[Dict]:
    """列出插件"""
    return plugin_manager.list_plugins()


# 测试代码
if __name__ == '__main__':
    print("=" * 60)
    print("智能插件系统测试")
    print("=" * 60)
    
    manager = PluginManager()
    
    # 注册示例插件
    print("\n1. 注册示例插件")
    example_plugin = ExamplePlugin()
    manager.plugins['example'] = example_plugin
    manager.plugin_status['example'] = PluginStatus.INSTALLED
    manager.sandboxes['example'] = PluginSandbox('example')
    print(f"插件已注册: {example_plugin.metadata.name}")
    
    # 激活插件
    print("\n2. 激活插件")
    if manager.activate_plugin('example', {'test': True}):
        print("插件激活成功")
    
    # 执行命令
    print("\n3. 执行插件命令")
    result1 = manager.execute_plugin_command('example', 'hello', {'name': '辉夜'})
    print(f"Hello命令结果: {result1}")
    
    result2 = manager.execute_plugin_command('example', 'add', {'a': 10, 'b': 20})
    print(f"Add命令结果: {result2}")
    
    # 获取插件信息
    print("\n4. 插件信息")
    info = manager.get_plugin_info('example')
    print(f"插件名称: {info['metadata']['name']}")
    print(f"插件状态: {info['status']}")
    print(f"插件能力: {info['capabilities']}")
    
    # 列出插件
    print("\n5. 插件列表")
    plugins = manager.list_plugins()
    for plugin in plugins:
        print(f"  - {plugin['name']} ({plugin['version']}): {plugin['status']}")
    
    # 停用插件
    print("\n6. 停用插件")
    manager.deactivate_plugin('example')
    print("插件已停用")
    
    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)
