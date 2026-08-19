import asyncio
import json
from mcp import ClientSession
from mcp.client.sse import sse_client

async def main():
    headers = {"Authorization": "Bearer bridge-secret-key"}
    async with sse_client("http://localhost:8001/mcp/sse", headers=headers) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            
            print("\nCalling aria_run_gravity...")
            result = await session.call_tool(
                "aria_run_gravity", 
                arguments={
                    "thesis": "The integration of MCP as a protocol adapter for ARIAEngine ensures modularity and scalability in AI agent ecosystems.",
                    "publication": "VisionaryAlpha Internal",
                    "context_payload": "This is a test of the ARIA Bridge implementation (CR-025)."
                }
            )
            
            content = result.content[0].text
            print(f"Raw Result: {content}")
            
            data = json.loads(content)
            if data.get("success"):
                print("\nSUCCESS: Gravity article generated.")
                article_data = data.get("data", {})
                print(f"Title: {article_data.get('title')}")
                print(f"Artifact ID: {article_data.get('artifact_id')}")
                print(f"Execution ID: {data.get('execution_id')}")
                print("\nArticle Excerpt:")
                print(article_data.get('excerpt'))
            else:
                print(f"\nFAILURE: {data.get('error')}")

if __name__ == "__main__":
    asyncio.run(main())
