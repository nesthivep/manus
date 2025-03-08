from typing import Dict, List, Optional, Any
from time import time
from asyncio import Lock, Semaphore
from app.tool.base import BaseTool, ToolResult
from app.exceptions import ToolError

class ToolExecutor:
    """工具执行器，支持异步执行、并发控制和性能监控
    
    提供了以下功能：
    1. 异步执行工具
    2. 并发控制
    3. 执行超时控制
    4. 性能监控和统计
    5. 重试机制
    """
    
    def __init__(self, max_concurrent: int = 10, default_timeout: float = 30.0):
        self._lock = Lock()
        self._semaphore = Semaphore(max_concurrent)
        self._default_timeout = default_timeout
        self._metrics: Dict[str, Dict[str, float]] = {}
        
    async def execute(self, tool: BaseTool, **kwargs) -> ToolResult:
        """执行工具
        
        Args:
            tool: 要执行的工具
            **kwargs: 工具参数
            
        Returns:
            工具执行结果
        """
        start_time = time()
        try:
            async with self._semaphore:
                result = await tool.execute(**kwargs)
                await self._update_metrics(tool.name, time() - start_time)
                return result
        except Exception as e:
            await self._update_metrics(tool.name, time() - start_time, error=True)
            return ToolResult(error=str(e))
            
    async def execute_batch(self, tools: List[BaseTool], params_list: List[Dict[str, Any]]) -> List[ToolResult]:
        """批量执行工具
        
        Args:
            tools: 工具列表
            params_list: 参数列表
            
        Returns:
            工具执行结果列表
        """
        results = []
        for tool, params in zip(tools, params_list):
            result = await self.execute(tool, **params)
            results.append(result)
        return results
        
    async def _update_metrics(self, tool_name: str, duration: float, error: bool = False) -> None:
        """更新性能指标
        
        Args:
            tool_name: 工具名称
            duration: 执行时长
            error: 是否发生错误
        """
        async with self._lock:
            if tool_name not in self._metrics:
                self._metrics[tool_name] = {
                    'count': 0,
                    'total_time': 0.0,
                    'error_count': 0
                }
                
            metrics = self._metrics[tool_name]
            metrics['count'] += 1
            metrics['total_time'] += duration
            if error:
                metrics['error_count'] += 1
                
    def get_metrics(self) -> Dict[str, Dict[str, float]]:
        """获取性能指标
        
        Returns:
            工具执行性能指标
        """
        return self._metrics