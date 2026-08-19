import httpx
import logging
from typing import Any, Optional
from .config import settings

logger = logging.getLogger(__name__)

class ARIAEngineClient:
    def __init__(self):
        self.base_url = f"{settings.ariaengine_url.rstrip('/')}/api/client/v1"
        self.headers = {
            "Authorization": f"Bearer {settings.aria_client_api_key}",
            "Content-Type": "application/json"
        }

    async def _post(self, endpoint: str, payload: dict[str, Any], context: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        # Build standard CR-21 envelope
        request_body = {
            "client": {
                "type": "operator",
                "client_id": "aria-bridge",
                "protocol_version": "1.0"
            },
            "request_context": context or {},
            "payload": payload
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(url, headers=self.headers, json=request_body)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"ARIAEngine HTTP error: {e.response.status_code} - {e.response.text}")
                raise
            except Exception as e:
                logger.error(f"ARIAEngine connection error: {str(e)}")
                raise

    async def get_health(self) -> dict[str, Any]:
        # ARIAEngine health is at /api/health
        health_url = f"{settings.ariaengine_url.rstrip('/')}/api/health"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(health_url)
            response.raise_for_status()
            return response.json()

    async def recall(self, query: str, domain: Optional[str] = None, limit: int = 10) -> dict[str, Any]:
        payload = {"query": query, "limit": limit}
        if domain:
            payload["domain"] = domain
        return await self._post("recall", payload, context={"intent": "recall_knowledge", "domain": domain})

    async def intake(self, source_title: str, content: str, source_type: str = "research", source_url: Optional[str] = None) -> dict[str, Any]:
        # Transform MCP ingest into IntakePayload
        payload = {
            "source": {
                "source_name": source_title,
                "source_type": source_type,
                "url": source_url
            },
            "content": {
                "sections": [
                    {
                        "title": "Ingested Content",
                        "content": content
                    }
                ]
            }
        }
        return await self._post("intake", payload, context={"intent": "ingest_document"})

    async def run_gravity(self, thesis: str, publication: str, context_payload: Optional[str] = None) -> dict[str, Any]:
        payload = {
            "capability": "gravity",
            "intent": "create_article",
            "parameters": {
                "topic": thesis,
                "publication_id": publication,
                "context_payload": context_payload
            }
        }
        return await self._post("capabilities/invoke", payload, context={"intent": "invoke_gravity"})
