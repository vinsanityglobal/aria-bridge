from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from client import ARIAEngineClient
from contracts import CR028Record, CR028RecallRequest, CR028RecallResponse, CR028Telemetry

logger = logging.getLogger("aria_bridge.cr028")


class CR028RecallService:
    """Governed Bridge adapter for read-only ARIA recall.

    This service calls only ARIAEngine's existing recall interface. It does not
    call intake, signals, generic capability invocation, Airtable, or any other
    mutating path.
    """

    def __init__(self, aria_client: ARIAEngineClient | None = None):
        self.aria_client = aria_client or ARIAEngineClient()

    async def recall_prior_intelligence(
        self, request: CR028RecallRequest
    ) -> CR028RecallResponse:
        started = time.perf_counter()
        status = "bridge_failure"
        records: list[CR028Record] = []
        provenance: list[dict[str, Any]] = []
        warnings: list[str] = []
        errors: list[dict[str, Any]] = []
        execution_id: str | None = None

        query = self._build_query(request)
        context = {
            "intent": "recall_prior_intelligence",
            "caller": request.caller,
            "request_id": request.request_id,
            "as_of": request.as_of,
            "ticker": request.ticker,
            "entities": request.entities,
            "event_context": request.event_context,
        }

        try:
            raw = await self.aria_client.recall(
                query=query,
                domain=request.spatial_awareness.get("domain"),
                limit=request.limit,
            )
            execution_id = raw.get("execution_id")
            data = raw.get("data", raw)
            records = self._normalize_records(data.get("knowledge_records", []))
            provenance = self._normalize_provenance(records)
            if records:
                status = "recalled"
            else:
                status = "no_relevant_prior_intelligence"
                warnings.append("NO RELEVANT PRIOR INTELLIGENCE FOUND")

            # These values are intentionally empty: the governed ARIA recall
            # contract does not supply analog or relationship evidence here.
            warnings.append(
                "Historical analogs and relationships were not supplied by the ARIA recall interface."
            )
        except httpx.TimeoutException as exc:
            status = "timeout"
            errors.append({"classification": "timeout", "message": str(exc)})
        except httpx.HTTPStatusError as exc:
            status = "aria_failure"
            errors.append(
                {
                    "classification": "aria_failure",
                    "http_status": exc.response.status_code,
                    "message": "ARIA recall request failed",
                }
            )
        except Exception as exc:  # Bridge-side normalization/transport failure
            logger.exception("CR-028 recall failed")
            status = "bridge_failure"
            errors.append({"classification": "bridge_failure", "message": str(exc)})

        latency_ms = int((time.perf_counter() - started) * 1000)
        telemetry = CR028Telemetry(
            request_id=request.request_id,
            caller=request.caller,
            requested_operation=request.operation,
            status=status,
            latency_ms=latency_ms,
            result_count=len(records),
            kernel_writes=0,
        )
        logger.info(
            "cr028_recall request_id=%s caller=%s status=%s latency_ms=%s result_count=%s kernel_writes=0 execution_id=%s",
            request.request_id,
            request.caller,
            status,
            latency_ms,
            len(records),
            execution_id,
        )
        return CR028RecallResponse(
            request_id=request.request_id,
            status=status,
            relevant_prior_intelligence=records,
            historical_analogs=[],
            relationships=[],
            provenance=provenance,
            retrieval_timestamp=datetime.now(timezone.utc).isoformat(),
            warnings=warnings,
            errors=errors,
            telemetry=telemetry,
        )

    @staticmethod
    def _build_query(request: CR028RecallRequest) -> str:
        parts = [request.ticker, request.subject, request.event_context]
        parts.extend(request.entities)
        query = " ".join(part.strip() for part in parts if part and part.strip())
        return query or ""

    @staticmethod
    def _normalize_records(raw_records: Any) -> list[CR028Record]:
        if not isinstance(raw_records, list):
            return []
        normalized: list[CR028Record] = []
        for raw in raw_records:
            if not isinstance(raw, dict) or not raw.get("id"):
                continue
            normalized.append(
                CR028Record(
                    record_id=str(raw["id"]),
                    title=str(raw.get("title", "")),
                    summary=str(raw.get("summary", "")),
                    knowledge_type=str(raw.get("type", "")),
                    confidence=raw.get("confidence"),
                    source_ids=[str(value) for value in raw.get("source_ids", []) if value],
                    provenance=raw.get("provenance") if isinstance(raw.get("provenance"), dict) else None,
                )
            )
        return normalized

    @staticmethod
    def _normalize_provenance(records: list[CR028Record]) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for record in records:
            if record.provenance:
                result.append({"record_id": record.record_id, **record.provenance})
            elif record.source_ids:
                result.append({"record_id": record.record_id, "source_ids": record.source_ids})
        return result
