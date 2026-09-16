# Reasoning and design notes

## 1. Interpretation of the problem

The assignment is a reusable pricing engine for a cinema booking counter. The system must validate seat availability, support multiple seat tiers, enforce discounts and fees in a clear order, and return a line-by-line bill that totals exactly. The assessment’s most important requirement is that UI code is not allowed to be a pricing authority; the backend is the only authoritative source.

## 2. Architecture chosen

The project is split into a minimal but clear two-layer design:

- React frontend for the customer-facing booking experience
- FastAPI backend with an independent Python pricing engine

The pricing engine is in backend/app/pricing.py and is used by the API; it is not imported into the frontend.

## 3. Why React + FastAPI

React is a clean fit for building a responsive customer UI with interactive seat selection and live pricing feedback. FastAPI is well suited for a small API that validates bookings, exposes a config endpoint, and returns structured Decimal-safe pricing results with strong data validation through Pydantic.

## 4. Why the pricing engine is independent from API/UI

The requirement explicitly states that there must be one source of truth. Keeping the engine separate isolates business rules from presentation and makes it easy to test outside FastAPI. This also prevents duplication and makes the logic reusable for different cinemas or booking counters.

## 5. Why Decimal is used

Money calculations must never rely on binary floating point. Python Decimal is the correct tool because it preserves exact decimal values and allows explicit rounding policies. This avoids issues such as 0.1 + 0.2 being imprecise or GST totals drifting by fractions of a paisa.

## 6. Decimal construction safety

Production code uses Decimal values created from decimal strings such as Decimal("400.00") rather than float literals. This ensures exact inputs and prevents the common floating point trap that breaks financial math.

## 7. Rounding policy

The project uses ROUND_HALF_UP and quantizes to two decimal places for currency. This is a deterministic, customer-friendly policy that matches how most billing systems round amounts to paisa precision.

## 8. Pricing pipeline

The backend follows the assessment’s intended flow:

1. validate booking data and inventory
2. calculate the base ticket subtotal
3. apply festival discount if enabled
4. apply member discount if enabled
5. cap member discount by configured maximum and remaining subtotal
6. add convenience fee per ticket
7. calculate taxable subtotal
8. compute GST on the taxable subtotal
9. return final payable total

This is implemented in a single engine function and easy to reason about from the API contract.

## 9. Festival/member discount order

The code applies the festival discount before member discount. That matches the problem statement and keeps the order explicit and testable. The member discount is calculated on the post-festival subtotal and is limited by the configured cap and remaining subtotal.

## 10. Member cap behavior

The member discount is calculated as:

- percentage of remaining ticket subtotal after festival discount
- then capped by min(raw_discount, cap, remaining_subtotal)

This ensures the discount can never exceed the configured cap, the remaining amount, or the theoretical percentage amount.

## 11. GST base assumption

The original prompt does not fully specify whether GST should be applied before or after convenience fees. The implemented assumption is that GST is applied to the discounted ticket subtotal plus convenience fee. This is documented as an assumption and encoded consistently in the engine and tests.

## 12. Inventory/sold-out validation

The backend rejects unknown tiers, sold-out tiers, zero/negative quantities, quantities above available inventory, and invalid configuration values. This prevents invalid bookings from being priced at all.

## 13. API design

The API exposes three important endpoints:

- GET /health for liveness
- GET /api/config for customer-visible configuration
- POST /api/price for the authoritative pricing calculation

The response model returns deterministic two-decimal string values so the UI can render them without additional formatting.

## 14. Frontend/backend source-of-truth decision

The frontend sends selections to the API and renders exactly what the API returns. It never performs its own money math. This keeps all pricing logic in one place and avoids inconsistent totals between UI and backend.

## 15. Edge cases considered

The engine and tests cover:

- sold-out inventory
- unknown tier names
- zero and negative quantities
- festival discount larger than subtotal
- member discount cap bounds
- GST and discount rounding
- custom cinema configuration
- case-insensitive tier matches
- zero-fee / zero-discount scenarios
- large valid bookings

## 16. Testing strategy

The backend suite is the primary proof of correctness. It tests the actual pricing logic independently from FastAPI and includes API tests for HTTP behavior. The tests intentionally cover edge cases and exact Decimal math so the implementation is not built around a weak approximation.

## 17. Configurability for different cinemas

The cinema configuration is centralized in backend/app/config.py and modeled as dataclasses with seat tiers and pricing values. This allows the same pricing engine to work with different unit prices, discount values, or seat inventories without rewriting business logic.

## 18. Important ambiguities in the original prompt

The assignment is clear in the general flow but leaves some tax semantics slightly ambiguous. In particular, it does not specify exactly whether GST is applied before or after convenience fee. The implementation makes a defensible explicit assumption: GST is applied to the discounted ticket subtotal plus convenience fee.

## 19. Alternatives/tradeoffs considered

A simpler alternative would be to keep all calculations inside the frontend or inline inside the API handler. That would have made the code harder to test and less reusable. Another possibility would be a heavier framework or database layer, but the assignment explicitly says not to add unnecessary architecture. This solution stays minimal and focused on the pricing engine.

## 20. What I deliberately did not build

I did not add a database, payment flow, or seat reservation system because those are out of scope for a pricing-engine assessment. I also did not create cloud services, authentication, or a complex dependency stack. The goal is a working assessment implementation that stays small, maintainable, and aligned with the prompt.

## 21. Why price-list import is separate from pricing

CSV import lives in `backend/app/importer.py`. It only parses, normalizes, validates, de-duplicates, and reports rows. After the report is produced, the API updates the in-memory tier configuration and sends bookings through the existing `calculate_booking` function, keeping the pricing engine as the single source of truth.

## 22. Import normalization and Decimal parsing

Seat-class names are trimmed and compared with `casefold()`. The first valid spelling remains the human-readable display name. Prices are parsed with `Decimal`, after accepting the supported `₹`, `INR`, `Rs`, and grouped-number forms, then quantized to two places using the pricing engine's existing `ROUND_HALF_UP` policy. Invalid values are rejected rather than coerced.

## 23. Duplicate and rejection policy

The first valid row for a case-insensitive seat class wins. Later rows with the same normalized price are reported as de-duplicated. Later rows with a different valid price are rejected with `conflicting duplicate price`, so an earlier price is never silently changed. Blank names, blank prices, negative prices, malformed prices, missing columns, and malformed rows receive row-level reasons.

## 24. Imported configuration lifetime

The API uses an encapsulated in-memory `PricingConfigStore`; no database is introduced. A successful import overlays matching default tiers, preserves their demo inventory, retains untouched defaults, and adds new imported names with 30 demo seats. The imported configuration lasts only until the backend process restarts.

## 25. Import ambiguity assumptions

The supported CSV contract is intentionally small: one `seat_class` column and one `price` column, with a few obvious header aliases. Comma-grouped prices must be quoted according to normal CSV rules. Because the input contains no inventory column, inventory remains demo configuration rather than being invented by the importer itself.
