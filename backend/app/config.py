from dataclasses import replace
from decimal import Decimal

from app.models import PricingConfig, SeatTier


def create_demo_config() -> PricingConfig:
    return PricingConfig(
        tiers={
            "Silver": SeatTier(name="Silver", unit_price=Decimal("250.00"), available_seats=30),
            "Gold": SeatTier(name="Gold", unit_price=Decimal("400.00"), available_seats=12),
            "Premium": SeatTier(name="Premium", unit_price=Decimal("500.00"), available_seats=20),
            "Platinum": SeatTier(name="Platinum", unit_price=Decimal("650.00"), available_seats=10),
            "Recliner": SeatTier(name="Recliner", unit_price=Decimal("800.00"), available_seats=0),
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
        default_tiers = self._default_config.tiers
        default_names = {name.casefold() for name in default_tiers}
        imported_by_name = {item["seat_class"].casefold(): item for item in prices}
        tiers = {}

        for name, default_tier in default_tiers.items():
            imported = imported_by_name.get(name.casefold())
            tiers[name] = SeatTier(
                name=name,
                unit_price=Decimal(imported["price"]) if imported else default_tier.unit_price,
                available_seats=default_tier.available_seats,
            )

        for item in prices:
            if item["seat_class"].casefold() in default_names:
                continue
            tiers[item["seat_class"]] = SeatTier(
                name=item["seat_class"],
                unit_price=Decimal(item["price"]),
                available_seats=30,
            )
        self._config = replace(self._config, tiers=tiers)
        return self._config

    def reset(self) -> PricingConfig:
        self._config = self._default_config
        return self._config
