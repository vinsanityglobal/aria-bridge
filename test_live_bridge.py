import asyncio
import json
import httpx2
from mcp import ClientSession
from mcp.client.sse import sse_client

def custom_client_factory(headers=None, timeout=None, auth=None):
    return httpx2.AsyncClient(
        http2=False,
        follow_redirects=True,
        headers=headers,
        timeout=timeout or httpx2.Timeout(30.0, read=300.0),
        auth=auth
    )

async def main():
    url = "https://aria-bridge-production.up.railway.app/mcp/sse"
    headers = {"Authorization": "Bearer aria-bridge-v1-9823472394"}
    
    print(f"Connecting to {url}...")
    try:
        async with sse_client(url, headers=headers, timeout=30.0, httpx_client_factory=custom_client_factory) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                
                print("\nCalling aria_health...")
                result = await session.call_tool("aria_health")
                print(f"Result: {result.content[0].text}")
                
                print("\nCalling aria_recall...")
                result = await session.call_tool("aria_recall", arguments={"query": "ARIA", "limit": 1})
                print(f"Recall Success: {json.loads(result.content[0].text)['success']}")
                
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
