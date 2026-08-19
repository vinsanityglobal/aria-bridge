import logging
import uuid
from typing import Optional
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from mcp.server import MCPServer
from mcp.server.sse import SseServerTransport
from starlette.middleware.base import BaseHTTPMiddleware

from config import settings
from client import ARIAEngineClient

# --- Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aria_bridge")

# --- ARIAEngine Client ---
aria_client = ARIAEngineClient()

# --- MCP Server ---
mcp = MCPServer("aria_bridge")

@mcp.tool()
async def aria_health() -> str:
    """
    Verify the health and connectivity of the ARIA Bridge and ARIAEngine.
    Returns status of the Bridge, reachability of ARIAEngine, and protocol availability.
    """
    try:
        engine_health = await aria_client.get_health()
        return f"ARIA Bridge: OK\nARIAEngine: Connected ({engine_health.get('version', 'unknown')})\nAuthentication: Verified"
    except Exception as e:
        return f"ARIA Bridge: OK\nARIAEngine: DISCONNECTED ({str(e)})"

@mcp.tool()
async def aria_recall(query: str, domain: Optional[str] = None, limit: int = 5) -> dict:
    """
    Retrieve relevant ARIA memory, knowledge, and doctrine for a subject.
    
    Args:
        query: The search query or subject to recall.
        domain: Optional subject domain (e.g., 'finance', 'technology').
        limit: Maximum number of records to return (default 5).
    """
    try:
        result = await aria_client.recall(query=query, domain=domain, limit=limit)
        return result
    except Exception as e:
        return {"error": str(e), "success": False}

@mcp.tool()
async def aria_ingest(source_title: str, content: str, source_type: str = "research", source_url: Optional[str] = None) -> dict:
    """
    Submit externally gathered research or source material into ARIA's ingestion pipeline.
    
    Args:
        source_title: Title of the source material.
        content: The actual text content to ingest.
        source_type: Type of source (e.g., 'research', 'news', 'filing').
        source_url: Optional URL of the original source.
    """
    try:
        result = await aria_client.intake(
            source_title=source_title,
            content=content,
            source_type=source_type,
            source_url=source_url
        )
        return result
    except Exception as e:
        return {"error": str(e), "success": False}

@mcp.tool()
async def aria_run_gravity(thesis: str, publication: str, context_payload: Optional[str] = None) -> dict:
    """
    Invoke the Gravity writing system to generate professional editorial content.
    
    Args:
        thesis: The core thesis or topic for the article.
        publication: The target publication (e.g., 'TheSciFiScene').
        context_payload: Optional additional context or research to guide the generation.
    """
    try:
        result = await aria_client.run_gravity(
            thesis=thesis,
            publication=publication,
            context_payload=context_payload
        )
        return result
    except Exception as e:
        return {"error": str(e), "success": False}

# --- FastAPI App ---
app = FastAPI(title=settings.app_name, version=settings.app_version)

# --- Authentication Middleware ---
class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Skip auth for root health check
        if request.url.path in ["/", "/health", "/mcp/sse", "/mcp/messages"]:
            return await call_next(request)
            
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail": "Unauthorized: Missing or invalid Bearer token"})
        
        token = auth_header.split(" ")[1]
        if token != settings.aria_bridge_api_key:
            return JSONResponse(status_code=403, content={"detail": "Forbidden: Invalid API Key"})
            
        return await call_next(request)

app.add_middleware(APIKeyMiddleware)

# --- MCP Transport Setup ---
from mcp.server.sse import SseServerTransport
sse = SseServerTransport("/mcp/messages")

@app.get("/mcp/sse")
async def handle_sse(request: Request):
    async with sse.connect_sse(request.scope, request.receive, request._send) as (read_stream, write_stream):
        await mcp.run(
            read_stream,
            write_stream,
            mcp.create_initialization_options()
        )

@app.post("/mcp/messages")
async def handle_messages(request: Request):
    await sse.handle_post_message(request.scope, request.receive, request._send)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "aria-bridge"}

@app.get("/")
async def root():
    return {"message": "ARIA Bridge (Remote MCP Server) is operational. Use /sse for MCP connection."}

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)
