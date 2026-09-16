from decimal import Decimal

import pytest

from app.config import create_demo_config
from app.models import PricingConfig, SeatTier
from app.pricing import calculate_booking, validate_booking


def test_one_ticket_no_offers():
    config = create_demo_config()
    result = calculate_booking(config, {"tier": "Gold", "quantity": 1, "festival_offer": False, "member": False})

    assert result["tier"] == "Gold"
    assert result["base_subtotal"] == Decimal("400.00")
    assert result["festival_discount"] == Decimal("0.00")
    assert result["member_discount"] == Decimal("0.00")
    assert result["convenience_fee"] == Decimal("20.00")
    assert result["taxable_subtotal"] == Decimal("420.00")
    assert result["gst"] == Decimal("75.60")
    assert result["total"] == Decimal("495.60")


def test_multiple_tickets_no_offers():
    config = create_demo_config()
    result = calculate_booking(config, {"tier": "Silver", "quantity": 4, "festival_offer": False, "member": False})

    assert result["base_subtotal"] == Decimal("1000.00")
    assert result["convenience_fee"] == Decimal("80.00")
    assert result["taxable_subtotal"] == Decimal("1080.00")
    assert result["gst"] == Decimal("194.40")
    assert result["total"] == Decimal("1274.40")


def test_member_discount_caps():
    config = create_demo_config()
    result = calculate_booking(config, {"tier": "Silver", "quantity": 8, "festival_offer": False, "member": True})

    assert result["member_discount"] == Decimal("200.00")
    assert result["taxable_subtotal"] == Decimal("1960.00")
    assert result["gst"] == Decimal("352.80")
    assert result["total"] == Decimal("2312.80")


def test_festival_discount_only():
    config = create_demo_config()
    result = calculate_booking(config, {"tier": "Silver", "quantity": 2, "festival_offer": True, "member": False})

    assert result["festival_discount"] == Decimal("100.00")
    assert result["member_discount"] == Decimal("0.00")
    assert result["taxable_subtotal"] == Decimal("440.00")
    assert result["gst"] == Decimal("79.20")
    assert result["total"] == Decimal("519.20")


def test_member_discount_below_cap_and_above_cap():
    config = create_demo_config()
    below_cap = calculate_booking(config, {"tier": "Gold", "quantity": 2, "festival_offer": False, "member": True})
    above_cap = calculate_booking(config, {"tier": "Gold", "quantity": 6, "festival_offer": False, "member": True})

    assert below_cap["member_discount"] == Decimal("80.00")
    assert above_cap["member_discount"] == Decimal("200.00")


def test_both_discounts_together():
    config = create_demo_config()
    result = calculate_booking(config, {"tier": "Gold", "quantity": 3, "festival_offer": True, "member": True})

    assert result["festival_discount"] == Decimal("100.00")
    assert result["member_discount"] == Decimal("110.00")
    assert result["taxable_subtotal"] == Decimal("1050.00")
    assert result["gst"] == Decimal("189.00")
    assert result["total"] == Decimal("1239.00")


def test_festival_discount_cannot_reduce_subtotal_below_zero():
    config = create_demo_config()
    result = calculate_booking(config, {"tier": "Silver", "quantity": 1, "festival_offer": True, "member": False})

    assert result["festival_discount"] == Decimal("100.00")
    assert result["taxable_subtotal"] == Decimal("170.00")
    assert result["total"] == Decimal("200.60")


def test_sold_out_and_unknown_tier():
    config = create_demo_config()

    with pytest.raises(ValueError, match="unknown tier"):
        validate_booking(config, {"tier": "Platinum", "quantity": 1, "festival_offer": False, "member": False})

    with pytest.raises(ValueError, match="sold out"):
        validate_booking(config, {"tier": "Recliner", "quantity": 1, "festival_offer": False, "member": False})


def test_validates_quantity_and_config():
    config = create_demo_config()

    with pytest.raises(ValueError, match="quantity"):
        validate_booking(config, {"tier": "Gold", "quantity": 0, "festival_offer": False, "member": False})

    with pytest.raises(ValueError, match="quantity"):
        validate_booking(config, {"tier": "Gold", "quantity": -1, "festival_offer": False, "member": False})

    with pytest.raises(ValueError, match="available"):
        validate_booking(config, {"tier": "Gold", "quantity": 50, "festival_offer": False, "member": False})

    bad_config = PricingConfig(
        tiers={"Gold": SeatTier(name="Gold", unit_price=Decimal("-100.00"), available_seats=5)},
        festival_discount=Decimal("0.00"),
        member_discount_percentage=Decimal("10.00"),
        member_discount_cap=Decimal("20.00"),
        convenience_fee=Decimal("20.00"),
        gst_rate=Decimal("18.00"),
    )
    with pytest.raises(ValueError, match="negative"):
        validate_booking(bad_config, {"tier": "Gold", "quantity": 1, "festival_offer": False, "member": False})


def test_decimal_rounding_and_float_precision_guard():
    config = PricingConfig(
        tiers={"Atlas": SeatTier(name="Atlas", unit_price=Decimal("99.99"), available_seats=10)},
        festival_discount=Decimal("19.99"),
        member_discount_percentage=Decimal("12.50"),
        member_discount_cap=Decimal("25.00"),
        convenience_fee=Decimal("1.25"),
        gst_rate=Decimal("18.00"),
    )

    result = calculate_booking(config, {"tier": "Atlas", "quantity": 3, "festival_offer": True, "member": True})
    assert result["base_subtotal"] == Decimal("299.97")
    assert result["festival_discount"] == Decimal("19.99")
    assert result["member_discount"] == Decimal("25.00")
    assert result["taxable_subtotal"] == Decimal("258.73")
    assert result["gst"] == Decimal("46.57")
    assert result["total"] == Decimal("305.30")


def test_custom_cinema_configuration_and_case_insensitive_tiers():
    config = PricingConfig(
        tiers={
            "Dune": SeatTier(name="Dune", unit_price=Decimal("777.00"), available_seats=3),
            "Ultra": SeatTier(name="Ultra", unit_price=Decimal("1250.00"), available_seats=0),
        },
        festival_discount=Decimal("150.00"),
        member_discount_percentage=Decimal("15.00"),
        member_discount_cap=Decimal("100.00"),
        convenience_fee=Decimal("10.00"),
        gst_rate=Decimal("5.00"),
    )

    result = calculate_booking(config, {"tier": "dune", "quantity": 3, "festival_offer": True, "member": True})
    assert result["tier"] == "Dune"
    assert result["member_discount"] == Decimal("100.00")
    assert result["total"] == Decimal("2216.55")

    with pytest.raises(ValueError, match="sold out"):
        validate_booking(config, {"tier": "Ultra", "quantity": 1, "festival_offer": False, "member": False})


def test_invalid_configuration_values():
    invalid = [
        PricingConfig({"A": SeatTier("A", Decimal("10.00"), 2)}, Decimal("-1.00"), Decimal("10.00"), Decimal("10.00"), Decimal("2.00"), Decimal("18.00")),
        PricingConfig({"A": SeatTier("A", Decimal("10.00"), 2)}, Decimal("0.00"), Decimal("101.00"), Decimal("10.00"), Decimal("2.00"), Decimal("18.00")),
        PricingConfig({"A": SeatTier("A", Decimal("10.00"), 2)}, Decimal("0.00"), Decimal("10.00"), Decimal("-1.00"), Decimal("2.00"), Decimal("18.00")),
        PricingConfig({"A": SeatTier("A", Decimal("10.00"), 2)}, Decimal("0.00"), Decimal("10.00"), Decimal("10.00"), Decimal("-1.00"), Decimal("18.00")),
        PricingConfig({"A": SeatTier("A", Decimal("10.00"), 2)}, Decimal("0.00"), Decimal("10.00"), Decimal("10.00"), Decimal("2.00"), Decimal("-1.00")),
    ]
    for bad_config in invalid:
        with pytest.raises(ValueError):
            validate_booking(bad_config, {"tier": "A", "quantity": 1, "festival_offer": False, "member": False})


def test_reconciles_bill_components():
    config = create_demo_config()
    result = calculate_booking(config, {"tier": "Gold", "quantity": 2, "festival_offer": True, "member": True})

    assert result["base_subtotal"] - result["festival_discount"] - result["member_discount"] + result["convenience_fee"] == result["taxable_subtotal"]
    assert result["taxable_subtotal"] + result["gst"] == result["total"]


def test_large_booking_quantity_is_allowed():
    config = create_demo_config()
    result = calculate_booking(config, {"tier": "Silver", "quantity": 30, "festival_offer": False, "member": True})
    assert result["quantity"] == 30
    assert result["member_discount"] == Decimal("200.00")
    assert result["total"] == Decimal("9322.00")


def test_zero_values_are_handled_cleanly():
    config = PricingConfig(
        tiers={"Test": SeatTier(name="Test", unit_price=Decimal("0.00"), available_seats=3)},
        festival_discount=Decimal("0.00"),
        member_discount_percentage=Decimal("0.00"),
        member_discount_cap=Decimal("0.00"),
        convenience_fee=Decimal("0.00"),
        gst_rate=Decimal("0.00"),
    )

    result = calculate_booking(config, {"tier": "Test", "quantity": 2, "festival_offer": False, "member": False})
    assert result["base_subtotal"] == Decimal("0.00")
    assert result["taxable_subtotal"] == Decimal("0.00")
    assert result["gst"] == Decimal("0.00")
    assert result["total"] == Decimal("0.00")
