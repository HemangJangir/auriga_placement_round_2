from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class SeatTier:
    name: str
    unit_price: Decimal
    available_seats: int


@dataclass(frozen=True)
class PricingConfig:
    tiers: dict[str, SeatTier]
    festival_discount: Decimal
    member_discount_percentage: Decimal
    member_discount_cap: Decimal
    convenience_fee: Decimal
    gst_rate: Decimal
