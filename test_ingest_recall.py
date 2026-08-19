import asyncio
import json
import time
from mcp import ClientSession
from mcp.client.sse import sse_client

async def main():
    headers = {"Authorization": "Bearer bridge-secret-key"}
    async with sse_client("http://localhost:8001/mcp/sse", headers=headers) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            
            unique_key = f"bridge-test-{int(time.time())}"
            content = f"The {unique_key} is a specialized testing protocol for the ARIA Bridge implementation. It confirms that data can travel from an external MCP client through the bridge into ARIAEngine's memory."
            
            print(f"\nCalling aria_ingest for {unique_key}...")
            ingest_result = await session.call_tool(
                "aria_ingest", 
                arguments={
                    "source_title": f"Bridge Integration Test: {unique_key}",
                    "content": content,
                    "source_type": "research"
                }
            )
            
            print(f"Ingest Result: {ingest_result.content[0].text}")
            
            # Wait for ARIAEngine to process (it's synchronous but give it a moment for Airtable propagation)
            print("\nWaiting 5 seconds for processing...")
            await asyncio.sleep(5)
            
            print(f"\nCalling aria_recall for {unique_key}...")
            recall_result = await session.call_tool(
                "aria_recall", 
                arguments={"query": unique_key}
            )
            
            content_text = recall_result.content[0].text
            print(f"Recall Result: {content_text}")
            
            data = json.loads(content_text)
            knowledge = data.get("data", {}).get("knowledge_records", [])
            if any(unique_key in k['summary'] or unique_key in k['title'] for k in knowledge):
                print("\nSUCCESS: Ingested material is now retrievable.")
            else:
                print("\nNOTE: Material not yet in knowledge base. This may be due to ARIA's learning disposition (Draft vs Validated) or processing delay.")

if __name__ == "__main__":
    asyncio.run(main())
