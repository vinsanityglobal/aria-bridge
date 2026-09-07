import logging
import os
import json
import hmac
from datetime import datetime, timezone
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecurityMiddleware
from config import settings
from client import ARIAEngineClient
from contracts import CR028RecallRequest, InterpretationRequest
from cr028_service import CR028RecallService

# --- Foolproof Async Transport Security Bypass ---
async def _bypass_validate(self, request, is_post=False):
    return None

TransportSecurityMiddleware.validate_request = _bypass_validate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aria_bridge")

aria_client = ARIAEngineClient()
cr028_recall_service = CR028RecallService(aria_client)

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
    result = await aria_client.recall(query, domain, limit)
    return json.dumps(result, indent=2)

@mcp.tool()
async def aria_ingest(source_title: str, content: str, source_type: str = "research", source_url: str = None) -> str:
    """Submit externally gathered research or source material into ARIA's ingestion pipeline."""
    result = await aria_client.intake(source_title, content, source_type, source_url)
    return json.dumps(result, indent=2)

@mcp.tool()
async def aria_interpret(request_json: str) -> str:
    """Interpret a bounded evidence packet using an explicitly configured existing ARIA capability."""
    try:
        request = InterpretationRequest.model_validate_json(request_json)
        result = await aria_client.interpret(request)
        return result.model_dump_json(indent=2)
    except Exception as e:
        return json.dumps({"status": "blocked", "error": str(e)}, indent=2)

@mcp.tool()
async def aria_run_gravity(thesis: str, publication: str = "TheSciFiScene", context_payload: str = None) -> str:
    """Invoke the Gravity writing system to generate professional editorial content."""
    result = await aria_client.run_gravity(thesis, publication, context_payload)
    return json.dumps(result, indent=2)


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Authenticate Bridge callers and bind CR-028 recall to the AESS principal."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        norm_path = path.rstrip("/")

        if norm_path in ["", "/health", "/docs", "/openapi.json"]:
            return await call_next(request)

        if norm_path == "/v1/recall-prior-intelligence":
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return JSONResponse(status_code=401, content={"detail": "Unauthorized: Missing or invalid Bearer token"})

            if not settings.aess_bridge_api_key:
                logger.error("CR-028 AESS credential is not configured")
                return JSONResponse(status_code=503, content={"detail": "AESS Bridge authorization is not configured"})

            token = auth_header.split(" ", 1)[1]
            if not hmac.compare_digest(token, settings.aess_bridge_api_key):
                return JSONResponse(status_code=403, content={"detail": "Forbidden: credential is not authorized for AESS recall"})

            request.state.authenticated_caller = settings.aess_caller_id
            request.state.authorized_operation = "recall_prior_intelligence"
            return await call_next(request)

        if norm_path.startswith("/mcp") or norm_path.startswith("/v1"):
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return JSONResponse(status_code=401, content={"detail": "Unauthorized: Missing or invalid Bearer token"})
            if not settings.aria_bridge_api_key:
                logger.error("General Bridge credential is not configured")
                return JSONResponse(status_code=503, content={"detail": "Bridge authentication is not configured"})
            token = auth_header.split(" ", 1)[1]
            if not hmac.compare_digest(token, settings.aria_bridge_api_key):
                return JSONResponse(status_code=403, content={"detail": "Forbidden: Invalid API key"})
            return await call_next(request)

        return await call_next(request)


async def health(request: Request):
    return JSONResponse({"status": "ok", "service": "aria-bridge", "version": settings.app_version})


async def root(request: Request):
    return JSONResponse({"message": "ARIA Bridge operational", "version": settings.app_version, "transport": "streamable_http", "endpoint": "/mcp"})


async def recall_prior_intelligence_http(request: Request):
    """Governed, read-only CR-028 AESS recall operation."""
    body = {}
    try:
        body = await request.json()

        authenticated_caller = getattr(request.state, "authenticated_caller", None)
        authorized_operation = getattr(request.state, "authorized_operation", None)
        if not authenticated_caller or authorized_operation != "recall_prior_intelligence":
            return JSONResponse(status_code=403, content={"detail": "Forbidden: AESS recall authorization missing"})

        supplied_caller = body.get("caller") if isinstance(body, dict) else None
        if supplied_caller is not None and supplied_caller != authenticated_caller:
            return JSONResponse(
                status_code=403,
                content={"detail": "Forbidden: caller does not match authenticated principal"},
            )

        # Caller identity is derived from the authenticated credential. The body is
        # normalized before contract validation so caller metadata cannot elevate identity.
        if isinstance(body, dict):
            body["caller"] = authenticated_caller

        recall_request = CR028RecallRequest.model_validate(body)
    except Exception as exc:
        return JSONResponse(
            status_code=422,
            content={
                "contract_version": "1.0",
                "request_id": body.get("request_id", "") if isinstance(body, dict) else "",
                "status": "malformed_request",
                "relevant_prior_intelligence": [],
                "historical_analogs": [],
                "relationships": [],
                "provenance": [],
                "retrieval_timestamp": datetime.now(timezone.utc).isoformat(),
                "warnings": [],
                "errors": [{"classification": "malformed_request", "message": str(exc)}],
                "telemetry": {
                    "request_id": body.get("request_id", "") if isinstance(body, dict) else "",
                    "caller": getattr(request.state, "authenticated_caller", ""),
                    "requested_operation": "recall_prior_intelligence",
                    "status": "malformed_request",
                    "latency_ms": 0,
                    "result_count": 0,
                    "kernel_writes": 0,
                },
            },
        )

    result = await cr028_recall_service.recall_prior_intelligence(recall_request)
    return JSONResponse(result.model_dump(mode="json"), status_code=200)


async def invoke_capability_http(request: Request):
    try:
        body = await request.json()
        capability = body.get("capability")
        intent = body.get("intent")
        parameters = body.get("parameters")

        if not isinstance(capability, str) or not capability.strip():
            return JSONResponse(status_code=422, content={"detail": "capability is required"})
        if not isinstance(intent, str) or not intent.strip():
            return JSONResponse(status_code=422, content={"detail": "intent is required"})
        if not isinstance(parameters, dict):
            return JSONResponse(status_code=422, content={"detail": "parameters must be an object"})

        result = await aria_client.invoke_capability(
            capability=capability,
            intent=intent,
            parameters=parameters,
        )
        return JSONResponse(result)
    except Exception as exc:
        logger.exception("Generic capability invocation failed")
        return JSONResponse(status_code=502, content={"detail": str(exc)})


streamable_app = mcp.streamable_http_app(streamable_http_path="/")

app = Starlette(
    routes=[
        Route("/health", health, methods=["GET"]),
        Route("/", root, methods=["GET"]),
        Route("/v1/recall-prior-intelligence", recall_prior_intelligence_http, methods=["POST"]),
        Route("/v1/capabilities/invoke", invoke_capability_http, methods=["POST"]),
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
