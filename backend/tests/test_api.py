from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_get_config_and_price():
    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    assert "tiers" in data
    assert any(tier["name"] == "Silver" for tier in data["tiers"])

    price_response = client.post(
        "/api/price",
        json={"tier": "Gold", "quantity": 2, "festival_offer": True, "member": True},
    )
    assert price_response.status_code == 200
    payload = price_response.json()
    assert payload["tier"] == "Gold"
    assert payload["quantity"] == 2
    assert payload["total"]
