from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


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
