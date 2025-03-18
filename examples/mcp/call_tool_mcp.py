from app.tool.mcp import MCP


async def main():
    mcp = MCP(name="test_sse_mcp", description="Test sse mcp")

    await mcp.connect("http://localhost:8080/sse")

    tools = await mcp.to_param()
    print(tools)

    result = await mcp.execute("get_alerts", {"state": "CA"})
    print(result.output)

    await mcp.disconnect()

if __name__ == "__main__":
    import asyncio

    asyncio.run(main())