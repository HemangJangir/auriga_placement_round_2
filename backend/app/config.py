from dataclasses import replace
from decimal import Decimal

from app.models import PricingConfig, SeatTier


def create_demo_config() -> PricingConfig:
    return PricingConfig(
        tiers={
            "Silver": SeatTier(name="Silver", unit_price=Decimal("250.00"), available_seats=30),
            "Gold": SeatTier(name="Gold", unit_price=Decimal("400.00"), available_seats=12),
            "Recliner": SeatTier(name="Recliner", unit_price=Decimal("650.00"), available_seats=0),
        },
        festival_discount=Decimal("100.00"),
        member_discount_percentage=Decimal("10.00"),
        member_discount_cap=Decimal("200.00"),
        convenience_fee=Decimal("20.00"),
        gst_rate=Decimal("18.00"),
    )


class PricingConfigStore:
    def __init__(self, config: PricingConfig):
        self._default_config = config
        self._config = config

    def get(self) -> PricingConfig:
        return self._config

    def replace_tiers(self, prices: list[dict[str, str]]) -> PricingConfig:
        existing = {name.casefold(): tier for name, tier in self._config.tiers.items()}
        tiers = {}
        for item in prices:
            previous_tier = existing.get(item["seat_class"].casefold())
            tiers[item["seat_class"]] = SeatTier(
                name=item["seat_class"],
                unit_price=Decimal(item["price"]),
                available_seats=previous_tier.available_seats if previous_tier else 30,
            )
        self._config = replace(self._config, tiers=tiers)
        return self._config

    def reset(self) -> PricingConfig:
        self._config = self._default_config
        return self._config
