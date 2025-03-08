from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Optional, Any
from pydantic import BaseModel, Field

class PromptVersion(str, Enum):
    """提示词模板版本"""
    V1 = "v1"
    V2 = "v2"

class BasePrompt(BaseModel, ABC):
    """提示词模板基类
    
    提供了提示词模板的基本功能，包括：
    1. 版本管理
    2. 参数替换
    3. 多语言支持
    4. 模板验证
    """
    version: PromptVersion = Field(default=PromptVersion.V1)
    language: str = Field(default="en")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        pass
    
    @abstractmethod
    def get_next_step_prompt(self) -> str:
        """获取下一步提示词"""
        pass
    
    def format_prompt(self, template: str, params: Optional[Dict[str, Any]] = None) -> str:
        """格式化提示词模板
        
        Args:
            template: 提示词模板
            params: 替换参数
        
        Returns:
            格式化后的提示词
        """
        if params:
            self.parameters.update(params)
        return template.format(**self.parameters)
    
    def validate(self) -> bool:
        """验证提示词模板
        
        Returns:
            验证是否通过
        """
        try:
            # 验证系统提示词
            system_prompt = self.get_system_prompt()
            if not system_prompt or not isinstance(system_prompt, str):
                return False
            
            # 验证下一步提示词
            next_step_prompt = self.get_next_step_prompt()
            if not next_step_prompt or not isinstance(next_step_prompt, str):
                return False
            
            return True
        except Exception:
            return False