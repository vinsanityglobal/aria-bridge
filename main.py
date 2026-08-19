import logging
from fastapi import FastAPI
from mcp.server import MCPServer
from config import settings
from client import ARIAEngineClient

# --- Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aria_bridge")

# --- ARIAEngine Client ---
aria_client = ARIAEngineClient()

# --- MCP Server Setup ---
mcp = MCPServer(settings.app_name)

@mcp.tool()
async def aria_health() -> str:
    """Verify the health and connectivity of the ARIA Bridge and ARIAEngine."""
    try:
        health = await aria_client.get_health()
        return (
            f"ARIA Bridge: OK\n"
            f"ARIAEngine: Connected ({health.get('version', 'unknown')})\n"
            f"Authentication: Verified"
        )
    except Exception as e:
        return f"ARIA Bridge: OK\nARIAEngine: Connection Failed ({str(e)})"

@mcp.tool()
async def aria_recall(query: str, domain: str = None, limit: int = 5) -> str:
    """Retrieve relevant ARIA memory, knowledge, and doctrine for a subject."""
    import json
    result = await aria_client.recall(query, domain, limit)
    return json.dumps(result, indent=2)

@mcp.tool()
async def aria_ingest(source_title: str, content: str, source_type: str = "research", source_url: str = None) -> str:
    """Submit externally gathered research or source material into ARIA's ingestion pipeline."""
    import json
    result = await aria_client.ingest(source_title, content, source_type, source_url)
    return json.dumps(result, indent=2)

@mcp.tool()
async def aria_run_gravity(thesis: str, publication: str = "TheSciFiScene", context_payload: str = None) -> str:
    """Invoke the Gravity writing system to generate professional editorial content."""
    import json
    result = await aria_client.invoke_capability(
        capability="gravity",
        intent="create_article",
        parameters={
            "thesis": thesis,
            "publication": publication,
            "context_payload": context_payload
        }
    )
    return json.dumps(result, indent=2)

# --- FastAPI App ---
app = FastAPI(title=settings.app_name, version=settings.app_version)

# --- MCP Transport Setup ---
# Use the built-in sse_app helper
mcp_sse_app = mcp.sse_app()
app.mount("/mcp", mcp_sse_app)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "aria-bridge"}

@app.get("/")
async def root():
    return {"message": "ARIA Bridge is operational. Use /mcp/sse for MCP connection."}

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)
