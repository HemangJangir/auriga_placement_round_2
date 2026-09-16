# CinePrice Multiplex Booking

A small full-stack cinema booking pricing assessment built with React, Vite, FastAPI, and Python Decimal. The backend is the source of truth for all pricing decisions, and the frontend simply displays the exact bill returned by the API.

## Problem summary

The application models a reusable cinema counter where each seat tier has a unit price and inventory. The user can choose a tier, quantity, and applicable discounts. The backend calculates:

- base ticket subtotal
- festival discount
- member discount with cap
- convenience fee per ticket
- taxable subtotal
- GST
- final payable amount

All money uses Decimal with ROUND_HALF_UP quantization to ensure accurate paisa-level totals.

Operators can also import a messy CSV seat-class price list. The importer cleans and reports the input, then replaces the active in-memory tiers for the running process.

## Tech stack

- Frontend: React + Vite + JavaScript
- Backend: Python 3.12+, FastAPI, Pydantic
- Money: Python Decimal
- Testing: pytest + TestClient

## Architecture

- React customer interface sends a booking request to FastAPI
- FastAPI validates the request and delegates to an independent Python pricing engine
- The pricing engine uses Decimal for authoritative calculations
- React renders only the exact response from the API

## Project structure

```text
.
├── README.md
├── REASONING.md
├── .gitignore
├── backend/
│   ├── pyproject.toml
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── exceptions.py
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── pricing.py
│   │   └── schemas.py
│   └── tests/
│       ├── test_api.py
│       └── test_pricing.py
└── frontend/
    ├── index.html
    ├── package.json
    ├── vite.config.js
    └── src/
        ├── App.jsx
        ├── index.css
        ├── main.jsx
        ├── components/
        └── services/
            └── api.js
```

## Prerequisites

- Python 3.12 or newer
- Node.js 18+ and npm
- Git

## Backend setup

From repository root:

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -U pip
pip install -e '.[dev]'
```

## Frontend setup

From repository root:

```bash
cd frontend
npm install
```

## How to run backend

```bash
cd backend
. .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API is available at:

- http://localhost:8000/health
- http://localhost:8000/api/config
- http://localhost:8000/api/price
- POST http://localhost:8000/api/import-prices

## How to run frontend

```bash
cd frontend
npm run dev -- --host 0.0.0.0 --port 5173
```

Then open:

- http://localhost:5173

## How to run backend tests

```bash
cd backend
. .venv/bin/activate
pytest -q
```

## How to build frontend

```bash
cd frontend
npm run build
```

## Debugging instructions

- If the backend does not start, confirm the virtual environment is active and dependencies are installed.
- If the frontend cannot reach the backend, ensure the Vite dev server is using the default API URL or set VITE_API_BASE_URL before starting the app.
- For pricing issues, inspect the engine in backend/app/pricing.py and run the pytest suite.

## Importing a price list

The frontend includes an **Import Price List** control. Select a `.csv` file to import it and immediately refresh the tiers available to the booking flow. The API accepts the same operation as a multipart upload:

```bash
curl -F 'file=@prices.csv' http://localhost:8000/api/import-prices
```

The CSV must contain `seat_class` and `price` columns. Names are trimmed and compared with `casefold()`, with the first valid display name retained. Prices use `Decimal`, accept `₹`, `INR`, `Rs`, and quoted comma-grouped values such as `"1,200.50"`, and are normalized to two places with the existing `ROUND_HALF_UP` policy. Blank, malformed, and negative values are rejected with row-level reasons.

Example messy input:

```csv
seat_class,price
Gold,₹400
gold,400.00
 GOLD ,₹ 400
Silver,250
Recliner,
Premium,-500
Platinum,"INR 650.00"
```

The first valid occurrence wins. A later duplicate with the same normalized price is reported as de-duplicated. A later duplicate with a different valid price is rejected as `conflicting duplicate price`. Successful imports replace all tiers; existing tier names retain their demo inventory and new names receive 30 demo seats so they can be booked in this assessment UI. Imported configuration is in-memory only and is lost when the backend process restarts. The response includes cleaned prices, accepted records, de-duplicated records, rejected records, and counts.

An import containing no valid rows still returns its rejection report and does not replace the active tiers. Use `POST /api/reset-prices` or the **Reset defaults** button to restore the original demo prices.

## API endpoints

### GET /health

Returns service status.

Example response:

```json
{
  "status": "ok"
}
```

### POST /api/import-prices

Accepts a multipart form upload named `file` with a `.csv` filename and returns the complete import report, including cleaned prices and row-level results.

### POST /api/reset-prices

Restores the original in-memory demo tiers.

### GET /api/config

Returns the customer-visible inventory and pricing configuration.

Example response:

```json
{
  "tiers": [
    {"name": "Silver", "price": "250.00", "available_seats": 30, "sold_out": false},
    {"name": "Gold", "price": "400.00", "available_seats": 12, "sold_out": false},
    {"name": "Recliner", "price": "650.00", "available_seats": 0, "sold_out": true}
  ],
  "festival_discount": "100.00",
  "member_discount_percentage": "10.00",
  "member_discount_cap": "200.00",
  "convenience_fee": "20.00",
  "gst_rate": "18.00"
}
```

### POST /api/price

Example request:

```json
{
  "tier": "Gold",
  "quantity": 3,
  "festival_offer": true,
  "member": true
}
```

Example response:

```json
{
  "tier": "Gold",
  "quantity": 3,
  "unit_price": "400.00",
  "base_subtotal": "1200.00",
  "festival_discount": "100.00",
  "member_discount": "110.00",
  "convenience_fee": "60.00",
  "taxable_subtotal": "1050.00",
  "gst_rate": "18.00",
  "gst": "189.00",
  "total": "1239.00"
}
```

## Money calculation strategy

The application uses Python Decimal everywhere that matters. The policy is:

- calculate in Decimal
- round to 2 decimal places using ROUND_HALF_UP
- round only at business boundaries, not during intermediate reasoning beyond service-worthy values
- serialize money values as fixed 2-decimal strings for the API and UI

This avoids binary floating point errors and keeps billing exact to the paisa.

## Pricing order

The backend pricing engine follows this pipeline:

1. validate booking and inventory
2. calculate base ticket subtotal
3. apply festival discount if selected
4. apply member percentage discount if selected
5. cap member discount at configured limit and remaining subtotal
6. calculate convenience fee per ticket
7. calculate taxable subtotal
8. calculate GST on discounted subtotal plus convenience fee
9. return final payable total

## Known assumptions

- GST is applied to discounted ticket subtotal plus convenience fee, as the problem statement did not fully specify the tax base.
- Tier matching is case-insensitive for user inputs, but the canonical booking response uses the configured tier name.
- Sold-out tiers are not selectable in the frontend and return a validation error in the API.

## How to use the UI

1. Open the frontend in the browser.
2. Choose a seat tier.
3. Adjust the quantity with the +/- controls.
4. Toggle festival and member offers.
5. Review the live bill summary.
6. Click Confirm Booking to see the success state with the payable amount.

## Notes

- This repository intentionally does not include a database or authentication layer.
- The frontend is a presentation layer only; pricing is never calculated in React.
- The backend is the single source of truth for all money values.
