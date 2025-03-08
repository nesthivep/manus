"""
LLM回调包装器，为现有LLM添加回调功能
"""
import asyncio
import inspect
import functools
from typing import Dict, List, Any, Callable, Optional

class LLMCallbackWrapper:
    """为LLM添加回调功能的包装类"""
    
    def __init__(self, llm_instance):
        self._llm = llm_instance
        self._callbacks = {
            "before_request": [],  # 发送请求前
            "after_request": [],   # 收到回复后
            "on_error": []         # 发生错误时
        }
        self._wrap_methods()
    
    def _wrap_methods(self):
        """包装LLM实例的方法以添加回调支持"""
        # 常见的方法名称
        method_names = ["completion", "chat", "generate", "run", "call", "__call__"]
        
        for name in method_names:
            if hasattr(self._llm, name) and callable(getattr(self._llm, name)):
                original_method = getattr(self._llm, name)
                
                # 检查是否是异步方法
                is_async = inspect.iscoroutinefunction(original_method)
                
                if is_async:
                    @functools.wraps(original_method)
                    async def async_wrapped(*args, **kwargs):
                        # 执行前回调
                        request_data = {"args": args, "kwargs": kwargs}
                        self._execute_callbacks("before_request", request_data)
                        
                        try:
                            # 调用原始方法
                            result = await original_method(*args, **kwargs)
                            
                            # 执行后回调
                            response_data = {"request": request_data, "response": result}
                            self._execute_callbacks("after_request", response_data)
                            
                            return result
                        except Exception as e:
                            # 错误回调
                            error_data = {"request": request_data, "error": str(e), "exception": e}
                            self._execute_callbacks("on_error", error_data)
                            raise
                    
                    # 替换为包装后的方法
                    setattr(self, name, async_wrapped)
                else:
                    @functools.wraps(original_method)
                    def wrapped(*args, **kwargs):
                        # 执行前回调
                        request_data = {"args": args, "kwargs": kwargs}
                        self._execute_callbacks("before_request", request_data)
                        
                        try:
                            # 调用原始方法
                            result = original_method(*args, **kwargs)
                            
                            # 执行后回调
                            response_data = {"request": request_data, "response": result}
                            self._execute_callbacks("after_request", response_data)
                            
                            return result
                        except Exception as e:
                            # 错误回调
                            error_data = {"request": request_data, "error": str(e), "exception": e}
                            self._execute_callbacks("on_error", error_data)
                            raise
                    
                    # 替换为包装后的方法
                    setattr(self, name, wrapped)
    
    def register_callback(self, event_type: str, callback: Callable):
        """注册回调函数
        
        Args:
            event_type: 事件类型，可以是"before_request"、"after_request"或"on_error"
            callback: 回调函数，接收相应的数据
        """
        if event_type in self._callbacks:
            self._callbacks[event_type].append(callback)
            return True
        return False
    
    def unregister_callback(self, event_type: str, callback: Callable):
        """注销特定的回调函数"""
        if event_type in self._callbacks and callback in self._callbacks[event_type]:
            self._callbacks[event_type].remove(callback)
            return True
        return False
    
    def clear_callbacks(self, event_type: str = None):
        """清除所有回调函数"""
        if event_type is None:
            # 清除所有类型的回调
            for event in self._callbacks:
                self._callbacks[event] = []
        elif event_type in self._callbacks:
            # 清除特定类型的回调
            self._callbacks[event_type] = []
    
    def _execute_callbacks(self, event_type: str, data: Dict[str, Any]):
        """执行指定类型的回调函数"""
        if event_type in self._callbacks:
            for callback in self._callbacks[event_type]:
                try:
                    callback(data)
                except Exception as e:
                    print(f"回调执行出错: {str(e)}")
    
    def __getattr__(self, name):
        """转发其他属性访问到原始LLM实例"""
        return getattr(self._llm, name)
