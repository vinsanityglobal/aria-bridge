import asyncio
import json
import httpx2
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

async def main():
    url = "https://aria-bridge-production.up.railway.app/mcp"
    headers = {"Authorization": "Bearer aria-bridge-v1-9823472394"}
    
    print(f"Connecting to Streamable HTTP endpoint {url}...")
    try:
        http_client = httpx2.AsyncClient(
            headers=headers,
            timeout=httpx2.Timeout(30.0, read=300.0)
        )
        async with streamable_http_client(url, http_client=http_client) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                
                print("\nCalling aria_health...")
                result = await session.call_tool("aria_health")
                print(f"Result: {result.content[0].text}")
                
                print("\nCalling aria_recall...")
                result = await session.call_tool("aria_recall", arguments={"query": "ARIA", "limit": 1})
                print(f"Recall Output:\n{result.content[0].text}")
                
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
