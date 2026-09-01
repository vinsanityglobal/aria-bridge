from starlette.testclient import TestClient

import main


def test_generic_capability_route_requires_auth():
    client = TestClient(main.app)
    response = client.post(
        "/v1/capabilities/invoke",
        json={"capability": "gravity", "intent": "test", "parameters": {}},
    )
    assert response.status_code == 401


def test_generic_capability_route_forwards_to_engine(monkeypatch):
    async def fake_invoke_capability(*, capability, intent, parameters):
        assert capability == "market_interpretation"
        assert intent == "interpret_evidence"
        assert parameters == {"tenant": "streetsmart"}
        return {"result": {"status": "ok"}}

    monkeypatch.setattr(main.aria_client, "invoke_capability", fake_invoke_capability)
    client = TestClient(main.app)
    response = client.post(
        "/v1/capabilities/invoke",
        headers={"Authorization": f"Bearer {main.settings.aria_bridge_api_key}"},
        json={
            "capability": "market_interpretation",
            "intent": "interpret_evidence",
            "parameters": {"tenant": "streetsmart"},
        },
    )
    assert response.status_code == 200
    assert response.json() == {"result": {"status": "ok"}}


def test_generic_capability_route_rejects_bad_contract():
    client = TestClient(main.app)
    response = client.post(
        "/v1/capabilities/invoke",
        headers={"Authorization": f"Bearer {main.settings.aria_bridge_api_key}"},
        json={"capability": "", "intent": "interpret_evidence", "parameters": {}},
    )
    assert response.status_code == 422
