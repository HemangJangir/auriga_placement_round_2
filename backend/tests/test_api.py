from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_default_catalogue_contains_all_five_tiers_and_recliner_is_sold_out():
    client.post("/api/reset-prices")
    tiers = client.get("/api/config").json()["tiers"]

    assert tiers == [
        {"name": "Silver", "price": "250.00", "available_seats": 30, "sold_out": False},
        {"name": "Gold", "price": "400.00", "available_seats": 12, "sold_out": False},
        {"name": "Premium", "price": "500.00", "available_seats": 20, "sold_out": False},
        {"name": "Platinum", "price": "650.00", "available_seats": 10, "sold_out": False},
        {"name": "Recliner", "price": "800.00", "available_seats": 0, "sold_out": True},
    ]


def test_sold_out_default_tier_cannot_be_booked():
    client.post("/api/reset-prices")
    response = client.post("/api/price", json={"tier": "Recliner", "quantity": 1})

    assert response.status_code == 400
    assert "sold out" in response.json()["detail"]


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
