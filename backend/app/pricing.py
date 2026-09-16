from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from app.exceptions import PricingValidationError
from app.models import PricingConfig

MONEY_QUANT = Decimal("0.01")


def quantize_money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def validate_tier_config(config: PricingConfig) -> None:
    if not config.tiers:
        raise PricingValidationError("pricing config must contain at least one seat tier")

    for name, tier in config.tiers.items():
        if not name or not name.strip():
            raise PricingValidationError("tier names cannot be blank")
        if tier.unit_price < Decimal("0.00"):
            raise PricingValidationError(f"tier {name} has a negative unit price")
        if tier.available_seats < 0:
            raise PricingValidationError(f"tier {name} has a negative available seat count")

    if config.festival_discount < Decimal("0.00"):
        raise PricingValidationError("festival discount cannot be negative")
    if config.member_discount_percentage < Decimal("0.00") or config.member_discount_percentage > Decimal("100.00"):
        raise PricingValidationError("member discount percentage must be between 0 and 100")
    if config.member_discount_cap < Decimal("0.00"):
        raise PricingValidationError("member discount cap cannot be negative")
    if config.convenience_fee < Decimal("0.00"):
        raise PricingValidationError("convenience fee cannot be negative")
    if config.gst_rate < Decimal("0.00") or config.gst_rate > Decimal("100.00"):
        raise PricingValidationError("GST rate must be between 0 and 100")


def validate_booking(config: PricingConfig, payload: dict) -> dict:
    validate_tier_config(config)

    tier_name = payload.get("tier")
    quantity = payload.get("quantity")

    if tier_name is None or str(tier_name).strip() == "":
        raise PricingValidationError("tier is required")

    tier_name = str(tier_name).strip()
    normalized = {key.casefold(): value for key, value in config.tiers.items()}
    tier = normalized.get(tier_name.casefold())
    if tier is None:
        raise PricingValidationError(f"unknown tier: {tier_name}")

    if quantity is None:
        raise PricingValidationError("quantity is required")
    if not isinstance(quantity, int) or isinstance(quantity, bool):
        raise PricingValidationError("quantity must be an integer")
    if quantity <= 0:
        raise PricingValidationError("quantity must be greater than zero")
    if tier.available_seats == 0:
        raise PricingValidationError(f"tier {tier_name} is sold out")
    if quantity > tier.available_seats:
        raise PricingValidationError(f"requested quantity exceeds available inventory for {tier_name}")

    return {
        "tier": tier.name,
        "quantity": quantity,
        "festival_offer": bool(payload.get("festival_offer", False)),
        "member": bool(payload.get("member", False)),
    }


def calculate_booking(config: PricingConfig, payload: dict) -> dict:
    validated = validate_booking(config, payload)
    tier_name = validated["tier"]
    quantity = validated["quantity"]
    festival_offer = validated["festival_offer"]
    member = validated["member"]

    tier = config.tiers[tier_name]
    unit_price = tier.unit_price
    base_subtotal = quantize_money(unit_price * quantity)

    festival_discount = Decimal("0.00")
    if festival_offer:
        festival_discount = min(base_subtotal, quantize_money(config.festival_discount))

    discounted_ticket_subtotal = max(base_subtotal - festival_discount, Decimal("0.00"))

    member_discount = Decimal("0.00")
    if member:
        percent_rate = config.member_discount_percentage / Decimal("100")
        raw_discount = discounted_ticket_subtotal * percent_rate
        member_discount = min(quantize_money(raw_discount), config.member_discount_cap, discounted_ticket_subtotal)

    convenience_fee = quantize_money(config.convenience_fee * quantity)
    taxable_subtotal = max(discounted_ticket_subtotal - member_discount + convenience_fee, Decimal("0.00"))
    gst = quantize_money(taxable_subtotal * (config.gst_rate / Decimal("100")))
    total = quantize_money(taxable_subtotal + gst)

    return {
        "tier": tier_name,
        "quantity": quantity,
        "unit_price": quantize_money(unit_price),
        "base_subtotal": base_subtotal,
        "festival_discount": quantize_money(festival_discount),
        "member_discount": quantize_money(member_discount),
        "convenience_fee": convenience_fee,
        "taxable_subtotal": taxable_subtotal,
        "gst_rate": quantize_money(config.gst_rate),
        "gst": gst,
        "total": total,
    }
