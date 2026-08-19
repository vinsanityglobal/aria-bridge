import asyncio
import json
from mcp import ClientSession
from mcp.client.sse import sse_client

async def main():
    headers = {"Authorization": "Bearer bridge-secret-key"}
    async with sse_client("http://localhost:8001/mcp/sse", headers=headers) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            
            print("\nCalling aria_recall...")
            result = await session.call_tool("aria_recall", arguments={"query": "ARIA", "limit": 10})
            
            # The result is a list of content objects
            content = result.content[0].text
            print(f"Raw Result: {content}")
            
            data = json.loads(content)
            if data.get("success"):
                print("\nSUCCESS: Recall executed.")
                knowledge = data.get("data", {}).get("knowledge_records", [])
                print(f"Found {len(knowledge)} knowledge records.")
                for k in knowledge:
                    print(f"- [{k['id']}] {k['title']}")
            else:
                print(f"\nFAILURE: {data.get('error')}")

if __name__ == "__main__":
    asyncio.run(main())
