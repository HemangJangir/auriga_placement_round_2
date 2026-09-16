from __future__ import annotations

from decimal import Decimal

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from app.config import PricingConfigStore, create_demo_config
from app.importer import import_price_csv
from app.pricing import calculate_booking
from app.schemas import BookingRequest, BookingResponse, PriceImportReport, PublicConfig, PublicTier

app = FastAPI(title="CinePrice API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CONFIG_STORE = PricingConfigStore(create_demo_config())


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/config", response_model=PublicConfig)
def get_config() -> PublicConfig:
    config = CONFIG_STORE.get()
    return PublicConfig(
        tiers=[
            PublicTier(
                name=tier.name,
                price=str(tier.unit_price.quantize(Decimal("0.01"))),
                available_seats=tier.available_seats,
                sold_out=tier.available_seats == 0,
            )
            for tier in config.tiers.values()
        ],
        festival_discount=str(config.festival_discount.quantize(Decimal("0.01"))),
        member_discount_percentage=str(config.member_discount_percentage.quantize(Decimal("0.01"))),
        member_discount_cap=str(config.member_discount_cap.quantize(Decimal("0.01"))),
        convenience_fee=str(config.convenience_fee.quantize(Decimal("0.01"))),
        gst_rate=str(config.gst_rate.quantize(Decimal("0.01"))),
    )


@app.post("/api/price", response_model=BookingResponse)
def price_booking(payload: BookingRequest) -> BookingResponse:
    try:
        result = calculate_booking(CONFIG_STORE.get(), payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return BookingResponse(
        tier=result["tier"],
        quantity=result["quantity"],
        unit_price=str(result["unit_price"]),
        base_subtotal=str(result["base_subtotal"]),
        festival_discount=str(result["festival_discount"]),
        member_discount=str(result["member_discount"]),
        convenience_fee=str(result["convenience_fee"]),
        taxable_subtotal=str(result["taxable_subtotal"]),
        gst_rate=str(result["gst_rate"]),
        gst=str(result["gst"]),
        total=str(result["total"]),
    )


@app.post("/api/import-prices", response_model=PriceImportReport)
async def import_prices(file: UploadFile = File(...)) -> PriceImportReport:
    if not file.filename or not file.filename.casefold().endswith(".csv"):
        raise HTTPException(status_code=400, detail="please upload a .csv file")

    report = import_price_csv(await file.read())
    if report["summary"]["imported"] > 0:
        CONFIG_STORE.replace_tiers(report["cleaned_prices"])
    return PriceImportReport.model_validate(report)


@app.post("/api/reset-prices", response_model=PublicConfig)
def reset_prices() -> PublicConfig:
    CONFIG_STORE.reset()
    return get_config()
