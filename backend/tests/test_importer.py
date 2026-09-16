from decimal import Decimal
from io import BytesIO

from fastapi.testclient import TestClient

from app.config import PricingConfigStore, create_demo_config
from app.importer import import_price_csv
from app.main import app
from app.pricing import calculate_booking


def test_imports_clean_csv_and_exact_decimal_prices():
    report = import_price_csv("seat_class,price\nSilver,250\nGold,400.00\n")

    assert report["cleaned_prices"] == [
        {"seat_class": "Silver", "price": "250.00"},
        {"seat_class": "Gold", "price": "400.00"},
    ]
    assert report["summary"] == {"imported": 2, "deduplicated": 0, "rejected": 0}
    assert Decimal(report["cleaned_prices"][0]["price"]) == Decimal("250.00")


def test_deduplicates_case_and_whitespace_with_first_display_name():
    report = import_price_csv("seat_class,price\nGold,400\n gold ,₹400.00\n GOLD,INR 400\n")

    assert report["cleaned_prices"] == [{"seat_class": "Gold", "price": "400.00"}]
    assert len(report["deduplicated"]) == 2
    assert report["summary"]["deduplicated"] == 2


def test_rejects_conflicting_duplicate_and_preserves_first_value():
    report = import_price_csv("seat_class,price\nGold,400\ngold,450\n")

    assert report["cleaned_prices"] == [{"seat_class": "Gold", "price": "400.00"}]
    assert report["rejected"] == [{
        "row": 3,
        "seat_class": "gold",
        "price": "450.00",
        "reason": "conflicting duplicate price",
    }]


def test_accepts_currency_prefixes_and_grouped_prices():
    report = import_price_csv(
        "seat_class,price\nRupee,₹ 400.00\nIndian,INR 650.00\nLegacy,Rs 400\nLarge,\"1,200.50\"\n"
    )

    assert [item["price"] for item in report["cleaned_prices"]] == ["400.00", "650.00", "400.00", "1200.50"]


def test_reports_blank_negative_and_malformed_values():
    report = import_price_csv(
        "seat_class,price\nRecliner,\n,-10\nPremium,-500\nBroken,not-a-price\n"
    )

    assert report["summary"] == {"imported": 0, "deduplicated": 0, "rejected": 4}
    assert [item["reason"] for item in report["rejected"]] == [
        "blank price",
        "blank seat class",
        "negative price",
        "unparseable price",
    ]


def test_cleaned_prices_feed_existing_pricing_engine():
    store = PricingConfigStore(create_demo_config())
    report = import_price_csv("seat_class,price\nPlatinum,650\n")
    config = store.replace_tiers(report["cleaned_prices"])

    result = calculate_booking(config, {"tier": "platinum", "quantity": 1})

    assert result["tier"] == "Platinum"
    assert result["unit_price"] == Decimal("650.00")


def test_import_endpoint_updates_config_and_prices_imported_tier():
    client = TestClient(app)
    response = client.post(
        "/api/import-prices",
        files={"file": ("prices.csv", BytesIO(b"seat_class,price\nPlatinum,INR 650\n"), "text/csv")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"] == {"imported": 1, "deduplicated": 0, "rejected": 0}
    assert any(tier["seat_class"] == "Platinum" for tier in payload["cleaned_prices"])

    config = client.get("/api/config").json()
    assert config["tiers"] == [{"name": "Platinum", "price": "650.00", "available_seats": 30, "sold_out": False}]

    priced = client.post("/api/price", json={"tier": "platinum", "quantity": 1})
    assert priced.status_code == 200
    assert priced.json()["unit_price"] == "650.00"


def test_import_endpoint_reports_all_rejected_rows_without_replacing_tiers():
    client = TestClient(app)
    response = client.post(
        "/api/import-prices",
        files={"file": ("invalid.csv", BytesIO(b"seat_class,price\nPremium,-500\nBroken,\n"), "text/csv")},
    )

    assert response.status_code == 200
    assert response.json()["summary"] == {"imported": 0, "deduplicated": 0, "rejected": 2}
    assert client.get("/api/config").json()["tiers"] == [
        {"name": "Platinum", "price": "650.00", "available_seats": 30, "sold_out": False}
    ]


def test_reset_endpoint_restores_default_tiers():
    client = TestClient(app)
    response = client.post("/api/reset-prices")

    assert response.status_code == 200
    assert [tier["name"] for tier in response.json()["tiers"]] == ["Silver", "Gold", "Recliner"]