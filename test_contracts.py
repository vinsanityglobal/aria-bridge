from datetime import datetime, timezone
from uuid import uuid4

import pytest

from client import ARIAEngineClient
from contracts import EvidenceRef, InterpretationRequest, InterpretationResponse


def sample_request() -> InterpretationRequest:
    return InterpretationRequest(
        tenant="streetsmart",
        evidence=[
            EvidenceRef(
                evidence_id=uuid4(),
                source_ref="fixture://nvda",
                observed_at=datetime(2026, 8, 31, tzinfo=timezone.utc).isoformat(),
                content={"symbol": "NVDA", "event": "Quarterly earnings reported"},
            )
        ],
    )


def test_interpretation_contract_round_trips_json():
    request = sample_request()
    restored = InterpretationRequest.model_validate_json(request.model_dump_json())
    assert restored.contract_version == "1.0"
    assert restored.tenant == "streetsmart"
    assert restored.evidence[0].evidence_id == request.evidence[0].evidence_id


def test_response_requires_bounded_confidence():
    with pytest.raises(Exception):
        InterpretationResponse(
            why_it_matters="test",
            confidence=1.5,
            evidence_ids=[sample_request().evidence[0].evidence_id],
        )


@pytest.mark.asyncio
async def test_interpretation_fails_closed_when_capability_unconfigured(monkeypatch):
    from config import settings

    monkeypatch.setattr(settings, "aria_interpret_capability", None)
    client = ARIAEngineClient()
    with pytest.raises(RuntimeError, match="not configured"):
        await client.interpret(sample_request())
