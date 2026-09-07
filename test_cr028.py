import asyncio

import httpx
from starlette.testclient import TestClient

import main
from contracts import CR028RecallRequest
from cr028_service import CR028RecallService


TEST_AESS_KEY = "test-aess-bridge-key"
main.settings.aess_bridge_api_key = TEST_AESS_KEY
main.settings.aess_caller_id = "aess-spatial-awareness"

AUTH = {"Authorization": f"Bearer {TEST_AESS_KEY}"}
BASE_REQUEST = {
    "contract_version": "1.0",
    "operation": "recall_prior_intelligence",
    "request_id": "req-cr028-001",
    "caller": "aess-spatial-awareness",
    "as_of": "2026-09-06T12:00:00Z",
    "ticker": "MDB",
    "entities": ["MongoDB"],
    "subject": "earnings reaction",
    "event_context": "market configuration",
    "spatial_awareness": {"domain": "market"},
    "provenance": {"source": "foundry-test"},
}


def test_cr028_requires_authentication():
    client = TestClient(main.app)
    response = client.post("/v1/recall-prior-intelligence", json=BASE_REQUEST)
    assert response.status_code == 401


def test_cr028_rejects_non_aess_credential():
    client = TestClient(main.app)
    response = client.post(
        "/v1/recall-prior-intelligence",
        headers={"Authorization": "Bearer wrong-key"},
        json=BASE_REQUEST,
    )
    assert response.status_code == 403


def test_cr028_rejects_claimed_caller_mismatch():
    client = TestClient(main.app)
    payload = {**BASE_REQUEST, "caller": "not-aess"}
    response = client.post("/v1/recall-prior-intelligence", headers=AUTH, json=payload)
    assert response.status_code == 403
    assert "caller does not match authenticated principal" in response.json()["detail"]


def test_cr028_derives_caller_from_credential(monkeypatch):
    async def fake_recall(*, query, domain, limit):
        return {"data": {"knowledge_records": [], "doctrine_records": []}}

    monkeypatch.setattr(main.aria_client, "recall", fake_recall)
    payload = {**BASE_REQUEST}
    payload.pop("caller")
    response = TestClient(main.app).post(
        "/v1/recall-prior-intelligence", headers=AUTH, json=payload
    )
    assert response.status_code == 200
    assert response.json()["telemetry"]["caller"] == "aess-spatial-awareness"


def test_cr028_rejects_unknown_fields():
    client = TestClient(main.app)
    payload = {**BASE_REQUEST, "unexpected": "must fail"}
    response = client.post("/v1/recall-prior-intelligence", headers=AUTH, json=payload)
    assert response.status_code == 422
    assert response.json()["status"] == "malformed_request"


def test_cr028_success_normalizes_aria_records_and_never_writes(monkeypatch):
    calls = []

    async def fake_recall(*, query, domain, limit):
        calls.append((query, domain, limit))
        return {
            "execution_id": "exec-1",
            "data": {
                "knowledge_records": [
                    {
                        "id": "rec-knowledge-1",
                        "title": "MDB earnings pattern",
                        "summary": "Prior observed pattern.",
                        "type": "Pattern",
                        "confidence": 0.8,
                        "source_ids": ["rec-source-1"],
                    }
                ],
                "doctrine_records": [],
            },
        }

    monkeypatch.setattr(main.aria_client, "recall", fake_recall)
    client = TestClient(main.app)
    response = client.post("/v1/recall-prior-intelligence", headers=AUTH, json=BASE_REQUEST)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "recalled"
    assert body["relevant_prior_intelligence"][0]["record_id"] == "rec-knowledge-1"
    assert body["provenance"] == [{"record_id": "rec-knowledge-1", "source_ids": ["rec-source-1"]}]
    assert body["historical_analogs"] == []
    assert body["relationships"] == []
    assert body["telemetry"]["caller"] == "aess-spatial-awareness"
    assert body["telemetry"]["kernel_writes"] == 0
    assert calls == [("MDB earnings reaction market configuration MongoDB", "market", 10)]


def test_cr028_empty_recall_is_not_a_failure(monkeypatch):
    async def fake_recall(*, query, domain, limit):
        return {"data": {"knowledge_records": [], "doctrine_records": []}}

    monkeypatch.setattr(main.aria_client, "recall", fake_recall)
    response = TestClient(main.app).post(
        "/v1/recall-prior-intelligence", headers=AUTH, json=BASE_REQUEST
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "no_relevant_prior_intelligence"
    assert "NO RELEVANT PRIOR INTELLIGENCE FOUND" in body["warnings"]
    assert body["telemetry"]["kernel_writes"] == 0


def test_cr028_classifies_aria_http_failure(monkeypatch):
    request = httpx.Request("POST", "https://aria.test/recall")
    response = httpx.Response(503, request=request)

    async def fake_recall(*, query, domain, limit):
        raise httpx.HTTPStatusError("upstream", request=request, response=response)

    monkeypatch.setattr(main.aria_client, "recall", fake_recall)
    body = TestClient(main.app).post(
        "/v1/recall-prior-intelligence", headers=AUTH, json=BASE_REQUEST
    ).json()

    assert body["status"] == "aria_failure"
    assert body["errors"][0]["classification"] == "aria_failure"
    assert body["telemetry"]["kernel_writes"] == 0


def test_cr028_classifies_timeout(monkeypatch):
    async def fake_recall(*, query, domain, limit):
        raise httpx.ReadTimeout("timed out")

    monkeypatch.setattr(main.aria_client, "recall", fake_recall)
    response = TestClient(main.app).post(
        "/v1/recall-prior_intelligence", headers=AUTH, json=BASE_REQUEST
    )

    # Route typo must not be accepted as the governed operation.
    assert response.status_code == 404

    body = TestClient(main.app).post(
        "/v1/recall-prior-intelligence", headers=AUTH, json=BASE_REQUEST
    ).json()
    assert body["status"] == "timeout"
    assert body["errors"][0]["classification"] == "timeout"
    assert body["telemetry"]["kernel_writes"] == 0


def test_service_never_exposes_mutating_client_methods():
    class RecallOnlyClient:
        async def recall(self, *, query, domain, limit):
            return {"data": {"knowledge_records": []}}

        def __getattr__(self, name):
            if name in {"intake", "invoke_capability"}:
                raise AssertionError(f"mutation-capable method accessed: {name}")
            raise AttributeError(name)

    service = CR028RecallService(RecallOnlyClient())
    result = asyncio.run(
        service.recall_prior_intelligence(CR028RecallRequest(**BASE_REQUEST))
    )
    assert result.status == "no_relevant_prior_intelligence"
    assert result.telemetry.kernel_writes == 0
