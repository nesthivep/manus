from typing import Any, ClassVar, Dict

from pydantic import Field

from app.agent.toolcall import ToolCallAgent
from app.prompt.manus import NEXT_STEP_PROMPT, SYSTEM_PROMPT
from app.tool import Terminate, ToolCollection
from app.tool.browser_use_tool import BrowserUseTool
from app.tool.file_saver import FileSaver
from app.tool.web_search import WebSearch
from app.tool.python_execute import PythonExecute
from app.tool.stock_data_tool import StockSearch
from app.config import config


class Manus(ToolCallAgent):
    """
    A versatile general-purpose agent that uses planning to solve various tasks.

    This agent extends PlanningAgent with a comprehensive set of tools and capabilities,
    including Python execution, web browsing, file operations, and information retrieval
    to handle a wide range of user requests.
    """

    name: str = "Manus"
    description: str = (
        "A versatile agent that can solve various tasks using multiple tools"
    )

    system_prompt: str = SYSTEM_PROMPT
    next_step_prompt: str = NEXT_STEP_PROMPT

    max_observe: int = 2000  # 默认值为2000
    max_steps: int = 20

    # 特定工具的max_observe配置
    tool_specific_max_observe: ClassVar[Dict[str, int]] = {
        "StockSearch": 13000
    }

    # Add general-purpose tools to the tool collection
    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            PythonExecute(), WebSearch(), BrowserUseTool(), FileSaver(), Terminate(), StockSearch()
        )
    )

    async def _set_max_observe_for_tool(self, tool_name: str):
        """根据使用的工具类型设置不同的max_observe值"""
        if tool_name in self.tool_specific_max_observe:
            self.max_observe = self.tool_specific_max_observe[tool_name]
        else:
            self.max_observe = 2000  # 默认值

    async def use_tool(self, *args, **kwargs):
        """重写use_tool方法，在调用工具前设置合适的max_observe值"""
        tool_name = kwargs.get("name") or (args[0] if args else None)
        old_max_observe = self.max_observe
        if tool_name:
            await self._set_max_observe_for_tool(tool_name)
            print(f"工具调用: {tool_name}, max_observe值: {self.max_observe} (原值: {old_max_observe})")
        return await super().use_tool(*args, **kwargs)

    async def _handle_special_tool(self, name: str, result: Any, **kwargs):
        await self.available_tools.get_tool(BrowserUseTool().name).cleanup()
        await super()._handle_special_tool(name, result, **kwargs)
