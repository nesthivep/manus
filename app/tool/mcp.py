from app.tool.base import BaseTool,ToolResult
from mcp import ClientSession, Tool,StdioServerParameters
from typing import Optional,Dict
from pydantic import Field
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client
from mcp.types import TextContent
from contextlib import AsyncExitStack,ExitStack


class MCP(BaseTool):
    class Config:
        arbitrary_types_allowed = True

    session: Optional[ClientSession] = None
    exit_stack: AsyncExitStack = Field(default_factory=ExitStack)

    tools: list[Tool] = []
    tool_map: Dict[str, Tool] = {}

    def __init__(self, name: str = None, description: str = None):
        super().__init__(name=name, description=description)
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

    async def connect(self, server_url: str = None):
        if not server_url:
            raise Exception("Server URL is required.")
        
        """Disconnect from the server if already connected"""
        if self.session:
            await self.disconnect()

        """Connect to an MCP server running with SSE transport"""
        # Store the context managers so they stay alive
        self._streams_context = sse_client(url=server_url)
        streams = await self._streams_context.__aenter__()

        self._session_context = ClientSession(*streams)
        self.session: ClientSession = await self._session_context.__aenter__()

        # Initialize
        print("Initialized SSE client...")
        await self.session.initialize()

        # List available tools to verify connection
        response = await self.session.list_tools()
        tools = response.tools
        self.tool_map = {tool.name: tool for tool in tools}
        print("\nConnected to server with tools:", [tool.name for tool in tools])

    async def connect_stdio(self, server_command: str,args: list):
        if not server_command:
            raise Exception("Server command is required.")
        
        """Disconnect from the server if already connected"""
        if self.session:
            await self.disconnect()

        server_params = StdioServerParameters(
            command=server_command,
            args=args,
        )
        try:
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            read, write = stdio_transport
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            await self.session.initialize()

            # List available tools to verify connection
            print("Listing tools...")
            response = await self.session.list_tools()
            tools = response.tools
            print("\nConnected to server with tools:", [tool.name for tool in tools])

        except Exception as e:
            await self.disconnect()
            raise e 

    async def disconnect(self):
        """Properly clean up the session and streams"""
        if self._session_context:
            await self._session_context.__aexit__(None, None, None)
        if self._streams_context:
            await self._streams_context.__aexit__(None, None, None)

        await self.exit_stack.aclose()

        self.session = None

    async def execute(self,name:str,arguments: dict, **kwargs) -> ToolResult:
        if self.session is None:
            raise Exception("Not connected to a mcp server.")

        result = await self.session.call_tool(name,arguments)

        content_str = ""
        for item in result.content:
            if isinstance(item, TextContent):
                content_str += ',' + item.text

        return ToolResult(
            output=content_str,
        )

    async def to_param(self) -> list[Dict]:
        if self.session is None:
            raise Exception("Not connected to server.")
    
        response = await self.session.list_tools()

        available_tools = [{ 
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema   
            }
        } for tool in response.tools]

        return available_tools
