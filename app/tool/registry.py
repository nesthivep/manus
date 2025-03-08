from typing import Dict, List, Type, Optional
from importlib import import_module
from pathlib import Path
from app.tool.base import BaseTool
from app.exceptions import ToolError

class ToolRegistry:
    """工具注册器，支持动态注册和管理工具
    
    提供了以下功能：
    1. 动态注册工具类
    2. 从目录自动加载工具
    3. 工具依赖管理
    4. 工具版本控制
    """
    
    def __init__(self):
        self._tools: Dict[str, Type[BaseTool]] = {}
        self._instances: Dict[str, BaseTool] = {}
        self._dependencies: Dict[str, List[str]] = {}
        
    def register(self, tool_cls: Type[BaseTool], dependencies: List[str] = None) -> None:
        """注册工具类
        
        Args:
            tool_cls: 工具类，必须继承BaseTool
            dependencies: 工具依赖列表
        """
        if not issubclass(tool_cls, BaseTool):
            raise ToolError(f"{tool_cls.__name__} 必须继承BaseTool类")
            
        name = tool_cls.name
        self._tools[name] = tool_cls
        if dependencies:
            self._dependencies[name] = dependencies
            
    def register_instance(self, tool: BaseTool) -> None:
        """注册工具实例
        
        Args:
            tool: 工具实例
        """
        self._instances[tool.name] = tool
        
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """获取工具实例
        
        Args:
            name: 工具名称
            
        Returns:
            工具实例，如果不存在则返回None
        """
        if name in self._instances:
            return self._instances[name]
            
        if name in self._tools:
            tool = self._tools[name]()
            self._instances[name] = tool
            return tool
            
        return None
        
    def load_from_directory(self, directory: str) -> None:
        """从目录加载工具
        
        Args:
            directory: 工具目录路径
        """
        path = Path(directory)
        if not path.is_dir():
            raise ToolError(f"{directory} 不是有效的目录")
            
        for file in path.glob("*.py"):
            if file.name.startswith("_"):
                continue
                
            module_name = f"app.tool.{file.stem}"
            try:
                module = import_module(module_name)
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, type) and issubclass(attr, BaseTool) and attr != BaseTool:
                        self.register(attr)
            except Exception as e:
                raise ToolError(f"加载工具 {file.name} 失败: {str(e)}")
                
    def validate_dependencies(self) -> None:
        """验证工具依赖"""
        for name, deps in self._dependencies.items():
            for dep in deps:
                if dep not in self._tools:
                    raise ToolError(f"工具 {name} 依赖的 {dep} 不存在")
                    
    def get_all_tools(self) -> List[BaseTool]:
        """获取所有已注册的工具实例"""
        return list(self._instances.values())