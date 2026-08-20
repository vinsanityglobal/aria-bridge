import asyncio
import json
from mcp import ClientSession
from mcp.client.sse import sse_client

async def main():
    url = "https://aria-bridge-production.up.railway.app/sse"
    headers = {"Authorization": "Bearer aria-bridge-v1-9823472394"}
    
    print(f"Connecting to {url}...")
    try:
        async with sse_client(url, headers=headers) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                
                print("\nCalling aria_health...")
                result = await session.call_tool("aria_health")
                print(f"Result: {result.content[0].text}")
                
                print("\nCalling aria_recall...")
                result = await session.call_tool("aria_recall", arguments={"query": "ARIA", "limit": 1})
                print(f"Recall Success: {json.loads(result.content[0].text)['success']}")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
