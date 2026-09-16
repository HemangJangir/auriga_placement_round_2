from pydantic import BaseModel, ConfigDict, Field, field_validator


class BookingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tier: str = Field(..., min_length=1)
    quantity: int = Field(..., gt=0)
    festival_offer: bool = False
    member: bool = False

    @field_validator("tier")
    @classmethod
    def validate_tier_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("tier is required")
        return value.strip()


class BookingResponse(BaseModel):
    tier: str
    quantity: int
    unit_price: str
    base_subtotal: str
    festival_discount: str
    member_discount: str
    convenience_fee: str
    taxable_subtotal: str
    gst_rate: str
    gst: str
    total: str


class PublicTier(BaseModel):
    name: str
    price: str
    available_seats: int
    sold_out: bool


class PublicConfig(BaseModel):
    tiers: list[PublicTier]
    festival_discount: str
    member_discount_percentage: str
    member_discount_cap: str
    convenience_fee: str
    gst_rate: str


class CleanedPrice(BaseModel):
    seat_class: str
    price: str


class ImportedPriceRecord(BaseModel):
    row: int
    seat_class: str
    price: str


class DeduplicatedPriceRecord(ImportedPriceRecord):
    reason: str


class RejectedPriceRecord(BaseModel):
    row: int
    seat_class: str
    reason: str
    price: str | None = None


class ImportSummary(BaseModel):
    imported: int
    deduplicated: int
    rejected: int


class PriceImportReport(BaseModel):
    cleaned_prices: list[CleanedPrice]
    imported_records: list[ImportedPriceRecord]
    deduplicated: list[DeduplicatedPriceRecord]
    rejected: list[RejectedPriceRecord]
    summary: ImportSummary
