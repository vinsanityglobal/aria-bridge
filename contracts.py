from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class EvidenceRef(BaseModel):
    evidence_id: UUID
    source_ref: str
    observed_at: str
    content: dict[str, Any]


class MetricRef(BaseModel):
    metric_name: str
    value: float
    unit: str
    as_of: str
    source_ref: str
    prior_value: float | None = None
    delta: float | None = None
    delta_pct: float | None = None


class InterpretationRequest(BaseModel):
    contract_version: str = "1.0"
    tenant: str
    evidence: list[EvidenceRef]
    metrics: list[MetricRef] = Field(default_factory=list)
    prior_state: dict[str, Any] | None = None
    questions: list[str] = Field(
        default_factory=lambda: [
            "What changed?",
            "Why does it matter?",
            "Which entities or relationships are affected?",
            "What should be watched next?",
            "What evidence weakens or conflicts with the interpretation?",
        ]
    )


class InterpretationResponse(BaseModel):
    contract_version: str = "1.0"
    why_it_matters: str
    affected_relationships: list[str] = Field(default_factory=list)
    watch_next: list[str] = Field(default_factory=list)
    uncertainty: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_ids: list[UUID]
    execution_id: str | None = None


class CR028RecallRequest(BaseModel):
    """AESS-facing, read-only request contract for CR-028."""

    model_config = ConfigDict(extra="forbid")

    contract_version: Literal["1.0"] = "1.0"
    operation: Literal["recall_prior_intelligence"] = "recall_prior_intelligence"
    request_id: str = Field(min_length=1, max_length=200)
    caller: str = Field(min_length=1, max_length=200)
    as_of: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    ticker: str | None = Field(default=None, max_length=32)
    entities: list[str] = Field(default_factory=list, max_length=50)
    subject: str | None = Field(default=None, max_length=500)
    event_context: str | None = Field(default=None, max_length=4000)
    spatial_awareness: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)
    limit: int = Field(default=10, ge=1, le=50)


class CR028Record(BaseModel):
    """Only values supplied by ARIA are exposed; no analogs are inferred."""

    record_id: str
    title: str = ""
    summary: str = ""
    knowledge_type: str = ""
    confidence: float | None = None
    source_ids: list[str] = Field(default_factory=list)
    provenance: dict[str, Any] | None = None


class CR028Telemetry(BaseModel):
    request_id: str
    caller: str
    requested_operation: str
    target_aria_capability: str = "recall"
    status: str
    latency_ms: int = Field(ge=0)
    result_count: int = Field(ge=0)
    kernel_writes: int = Field(default=0, ge=0)


class CR028RecallResponse(BaseModel):
    contract_version: Literal["1.0"] = "1.0"
    request_id: str
    status: Literal[
        "recalled",
        "no_relevant_prior_intelligence",
        "bridge_failure",
        "aria_failure",
        "timeout",
        "malformed_request",
    ]
    relevant_prior_intelligence: list[CR028Record] = Field(default_factory=list)
    historical_analogs: list[dict[str, Any]] = Field(default_factory=list)
    relationships: list[dict[str, Any]] = Field(default_factory=list)
    provenance: list[dict[str, Any]] = Field(default_factory=list)
    retrieval_timestamp: str
    warnings: list[str] = Field(default_factory=list)
    errors: list[dict[str, Any]] = Field(default_factory=list)
    telemetry: CR028Telemetry
