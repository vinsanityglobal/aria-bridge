import logging
import os
import json
from fastapi import FastAPI, Request, Response
from starlette.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from mcp.server import MCPServer
from mcp.server.sse import SseServerTransport
from mcp.server.transport_security import TransportSecuritySettings
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
security_settings = TransportSecuritySettings(enable_dns_rebinding_protection=False)
sse = SseServerTransport("/messages/", security_settings=security_settings)

@app.get("/sse")
async def handle_sse(request: Request):
    logger.info(f"SSE Handshake: Method={request.scope.get('method')}, Path={request.scope.get('path')}")
    try:
        async with sse.connect_sse(request.scope, request.receive, request._send) as (read_stream, write_stream):
            await mcp.run(
                read_stream,
                write_stream,
                mcp._lowlevel_server.create_initialization_options()
            )
    except Exception as e:
        logger.error(f"SSE Error: {str(e)}")
        raise e
    return Response()

@app.post("/messages")
async def handle_messages(request: Request):
    await sse.handle_post_message(request.scope, request.receive, request._send)

# --- Authentication Middleware ---
class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        norm_path = path.rstrip("/")
        
        if norm_path in ["", "/health", "/sse", "/messages"]:
            return await call_next(request)
            
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
        
        token = auth_header.split(" ")[1]
        if token != settings.aria_bridge_api_key:
            return JSONResponse(status_code=403, content={"detail": "Forbidden"})
            
        return await call_next(request)

app.add_middleware(APIKeyMiddleware)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "aria-bridge"}

@app.get("/")
async def root():
    return {"message": "ARIA Bridge operational. Use /sse for MCP connection."}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)
