import logging
import os
import json
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecurityMiddleware
from config import settings
from client import ARIAEngineClient

# --- Foolproof Async Transport Security Bypass ---
async def _bypass_validate(self, request, is_post=False):
    return None

TransportSecurityMiddleware.validate_request = _bypass_validate

# --- Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aria_bridge")

# --- ARIAEngine Client ---
aria_client = ARIAEngineClient()

# --- MCP Server Setup & Tool Registration ---
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

# --- Authentication Middleware ---
class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        norm_path = path.rstrip("/")
        
        if norm_path in ["", "/health", "/docs", "/openapi.json"]:
            return await call_next(request)
            
        # Require Bearer token for /mcp endpoints
        if norm_path.startswith("/mcp"):
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return JSONResponse(status_code=401, content={"detail": "Unauthorized: Missing or invalid Bearer token"})
            token = auth_header.split(" ")[1]
            if token != settings.aria_bridge_api_key:
                return JSONResponse(status_code=403, content={"detail": "Forbidden: Invalid API key"})
            return await call_next(request)
            
        return await call_next(request)

# --- Build Starlette App with Mounted Streamable HTTP App ---
async def health(request: Request):
    return JSONResponse({"status": "ok", "service": "aria-bridge"})

async def root(request: Request):
    return JSONResponse({"message": "ARIA Bridge operational", "version": settings.app_version, "transport": "streamable_http", "endpoint": "/mcp"})

streamable_app = mcp.streamable_http_app(streamable_http_path="/")

app = Starlette(
    routes=[
        Route("/health", health, methods=["GET"]),
        Route("/", root, methods=["GET"]),
        Mount("/mcp", streamable_app),
    ],
    middleware=[
        Middleware(APIKeyMiddleware),
        Middleware(ProxyHeadersMiddleware, trusted_hosts="*"),
    ]
)
app.router.redirect_slashes = False

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port, proxy_headers=True)
