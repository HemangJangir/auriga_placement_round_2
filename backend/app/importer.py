from __future__ import annotations

import csv
import io
import re
from decimal import Decimal, InvalidOperation

from app.pricing import quantize_money


HEADER_ALIASES = {
    "seat_class": {"seat_class", "seat class", "class", "tier", "tier_name", "tier name"},
    "price": {"price", "unit_price", "unit price"},
}
MONEY_PREFIX = re.compile(r"^(?:₹|INR|Rs)\s*", re.IGNORECASE)


def _normalize_header(value: str) -> str:
    return value.strip().casefold().replace("-", "_")


def _parse_price(value: str) -> Decimal:
    text = value.strip()
    if not text:
        raise ValueError("blank price")

    without_prefix = MONEY_PREFIX.sub("", text).strip()
    if not without_prefix or without_prefix.startswith("-"):
        if without_prefix.startswith("-"):
            raise ValueError("negative price")
        raise ValueError("unparseable price")

    if not re.fullmatch(r"\+?(?:\d+(?:,\d{3})*|\d+)(?:\.\d+)?", without_prefix):
        raise ValueError("unparseable price")

    try:
        price = Decimal(without_prefix.replace(",", ""))
    except InvalidOperation as exc:
        raise ValueError("unparseable price") from exc

    if price < Decimal("0"):
        raise ValueError("negative price")
    return quantize_money(price)


def _record(row: int, seat_class: str, price: Decimal) -> dict[str, object]:
    return {"row": row, "seat_class": seat_class, "price": f"{price:.2f}"}


def import_price_csv(content: bytes | str) -> dict[str, object]:
    if isinstance(content, bytes):
        try:
            content = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            return {
                "cleaned_prices": [],
                "imported_records": [],
                "deduplicated": [],
                "rejected": [{"row": 1, "seat_class": "", "reason": "file is not valid UTF-8"}],
                "summary": {"imported": 0, "deduplicated": 0, "rejected": 1},
            }

    reader = csv.DictReader(io.StringIO(content))
    if reader.fieldnames is None:
        return {
            "cleaned_prices": [],
            "imported_records": [],
            "deduplicated": [],
            "rejected": [{"row": 1, "seat_class": "", "reason": "missing header"}],
            "summary": {"imported": 0, "deduplicated": 0, "rejected": 1},
        }

    headers = {_normalize_header(header): header for header in reader.fieldnames if header is not None}
    columns: dict[str, str] = {}
    for logical_name, aliases in HEADER_ALIASES.items():
        match = next((header for normalized, header in headers.items() if normalized in {_normalize_header(alias) for alias in aliases}), None)
        if match is None:
            rejected = [{"row": 1, "seat_class": "", "reason": f"missing required column: {logical_name}"}]
            return {
                "cleaned_prices": [],
                "imported_records": [],
                "deduplicated": [],
                "rejected": rejected,
                "summary": {"imported": 0, "deduplicated": 0, "rejected": 1},
            }
        columns[logical_name] = match

    cleaned_prices: list[dict[str, str]] = []
    imported_records: list[dict[str, object]] = []
    deduplicated: list[dict[str, object]] = []
    rejected: list[dict[str, object]] = []
    seen: dict[str, Decimal] = {}

    for row_number, row in enumerate(reader, start=2):
        if None in row:
            rejected.append({"row": row_number, "seat_class": "", "reason": "malformed row: extra columns"})
            continue

        raw_name = (row.get(columns["seat_class"]) or "").strip()
        raw_price = row.get(columns["price"]) or ""
        if not raw_name:
            rejected.append({"row": row_number, "seat_class": "", "reason": "blank seat class"})
            continue

        try:
            price = _parse_price(raw_price)
        except ValueError as exc:
            rejected.append({"row": row_number, "seat_class": raw_name, "reason": str(exc)})
            continue

        name_key = raw_name.casefold()
        if name_key in seen:
            if seen[name_key] == price:
                deduplicated.append(_record(row_number, raw_name, price) | {"reason": "duplicate valid price"})
            else:
                rejected.append({
                    "row": row_number,
                    "seat_class": raw_name,
                    "price": f"{price:.2f}",
                    "reason": "conflicting duplicate price",
                })
            continue

        seen[name_key] = price
        record = _record(row_number, raw_name, price)
        imported_records.append(record)
        cleaned_prices.append({"seat_class": raw_name, "price": f"{price:.2f}"})

    return {
        "cleaned_prices": cleaned_prices,
        "imported_records": imported_records,
        "deduplicated": deduplicated,
        "rejected": rejected,
        "summary": {
            "imported": len(imported_records),
            "deduplicated": len(deduplicated),
            "rejected": len(rejected),
        },
    }