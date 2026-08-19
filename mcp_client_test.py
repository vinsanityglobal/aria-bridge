import asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client

async def main():
    headers = {"Authorization": "Bearer bridge-secret-key"}
    async with sse_client("http://localhost:8001/mcp/sse", headers=headers) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            
            # List tools
            tools = await session.list_tools()
            print("Available tools:")
            for tool in tools.tools:
                print(f"- {tool.name}: {tool.description}")
            
            # Call aria_health
            print("\nCalling aria_health...")
            result = await session.call_tool("aria_health")
            print(f"Result: {result.content[0].text}")

if __name__ == "__main__":
    asyncio.run(main())
