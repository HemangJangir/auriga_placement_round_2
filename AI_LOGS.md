Yes. For this round, the cleanest “vibe coding” setup is:

GitHub Codespaces + GitHub Copilot Chat in Agent mode.

In Agent mode, Copilot can inspect the repository, create files, edit code, run terminal commands, run tests, and iterate on failures. That is specifically what GitHub documents Agent mode for.

You can basically do the entire round from inside Codespaces without manually creating the project structure.

What you should do

Open the assessment repository in GitHub, create the Codespace, then open Copilot Chat. In Codespaces, Copilot works through the VS Code web interface; if it isn’t already available, the Copilot extension can be installed there.

Then switch the chat mode to Agent.

Do not start writing files yourself.

Paste one strong master prompt like this:

You are acting as the primary engineer for this coding assessment.

First inspect the entire repository, including README files, existing source code, package/config files, tests, hidden-test clues, and submission instructions. Do not assume this is an empty repository.

The problem is:

“Friday night at the multiplex”

Build a reusable cinema ticket pricing engine. Seats have tiers such as Silver, Gold, and Recliner with configurable prices and availability. Sold-out tiers must not be bookable.

Pricing rules include:

base ticket price determined by tier and number of tickets
flat festival discount
percentage member discount with a configurable maximum cap
configurable per-ticket convenience fee
GST added after the applicable pricing adjustments
all calculations must be exact to the paisa
return a clear line-by-line bill breakdown
solution must be reusable for different cinemas/shows and must not hardcode one example

Your job:

Inspect the repository and determine the required language, framework, interfaces, input/output format, and existing tests.
If the repository already defines an API or function signature, preserve it exactly.
If requirements are ambiguous, infer the safest behavior from the README/tests and document assumptions instead of inventing arbitrary business logic.
Implement the smallest robust production-quality solution.
Use integer paise or an exact decimal type for all money calculations. Never use binary floating-point for currency.
Make all business rules configurable rather than hardcoded:
seat tiers and their prices
availability
flat discount
member percentage
member discount cap
per-ticket convenience fee
GST rate
Reject invalid bookings such as:
sold-out tier
unknown tier
zero or negative ticket count
unavailable quantity if inventory exists
Produce a deterministic bill breakdown containing at minimum:
tier
ticket count
base price per ticket
base subtotal
festival discount
member discount
convenience fee
taxable subtotal
GST
final payable amount
Ensure the final amount is exact to one paisa.
Add thorough tests for normal cases and edge cases.
Run the existing test suite after every meaningful change.
Do not modify or weaken existing tests just to make them pass.
Keep dependencies minimal.
Add or update README documentation with:
assumptions
pricing order
how to run
how to test
example input/output
Before finishing:
run all tests
run formatting/linting if configured
inspect git diff
remove unnecessary/generated files
confirm the repository is ready for submission

Important pricing guidance:

Start with the plain ticket subtotal first. Then apply offers. Then add the per-ticket convenience fee. Then calculate GST on the appropriate post-discount amount plus taxable fees, unless the repository specification says otherwise.

Because discount stacking order can materially change the answer, inspect the repository/tests before deciding whether the percentage member discount is applied before or after the festival flat discount. If the specification does not say, choose one clearly documented rule and structure the pricing engine so the policy is easy to change.

Do not just explain what to do. Work autonomously: inspect files, create or modify the appropriate files, run commands, fix failures, and continue until the implementation is complete and all available tests pass.

At the end, give me:

files changed
pricing formula used
assumptions made
tests run and their result
anything I still need to do before submission

That is the prompt I would use.

The most important part is this line:

First inspect the entire repository.

Because there is a big difference between:

Build anything you want

and:

Implement PricingEngine.calculate(...)

If Auriga has hidden tests, blindly creating your own API can give you a perfect program that scores zero.

For this particular problem, there is one major trap

Money.

Do not let Copilot write things like:

const total = 199.99 * 3;

or:

total = 199.99 * 3

Binary floating-point can produce values such as:

599.969999999

For exact paisa accounting, the implementation should preferably represent money internally like:

₹299.50 = 29950 paise

Then calculations happen using integers.

For example:

Gold = 40000 paise
3 tickets

baseSubtotal = 120000 paise

Percentage calculations then require an explicit rounding policy before converting back to paise.

Alternatively, Python's Decimal, Java's BigDecimal, etc. are also appropriate.

The engine should conceptually work like this

Suppose:

Gold = ₹400
tickets = 3

Festival offer = ₹100
Member discount = 10%
Member cap = ₹150

Convenience = ₹20/ticket
GST = 18%

A possible rule set is:

Base:
3 × ₹400
= ₹1,200

Festival discount:
- ₹100

Remaining:
₹1,100

Member discount:
10% of ₹1,100
= ₹110

Discounted ticket amount:
₹990

Convenience:
3 × ₹20
= ₹60

Taxable amount:
₹1,050

GST @ 18%:
₹189

FINAL:
₹1,239

And the result should return something structured, not just:

1239

Something like:

{
  "tier": "GOLD",
  "quantity": 3,
  "baseSubtotal": "1200.00",
  "festivalDiscount": "100.00",
  "memberDiscount": "110.00",
  "convenienceFee": "60.00",
  "taxableAmount": "1050.00",
  "gst": "189.00",
  "total": "1239.00"
}

The exact formula may differ based on the repository instructions. Let the agent inspect those first.

Then let Agent mode do the work

Copilot Agent can propose and execute terminal commands, edit multiple files, and iterate after test failures.

So when it asks:

Allow command npm test?

Approve it.

When it asks:

Allow mkdir, pip install, etc.?

Read the command quickly, and approve sensible ones.

You don't need to manually create:

src/
tests/
README.md

The agent can do that itself.

After it says it is done, give it a second prompt

Do not submit immediately.

Paste:

Now behave as a strict senior reviewer who is trying to make this solution fail hidden tests.

Do not add features unnecessarily.

Review the complete implementation for:

floating point currency bugs
rounding to paisa
wrong discount ordering
member discount cap errors
discount exceeding subtotal
sold-out tiers
invalid tier
zero quantity
negative quantity
large quantities
zero discounts
zero GST
fractional GST results
festival discount larger than booking value
member discount larger than cap
combinations of both offers
immutability/state bugs
hardcoded cinema/show data
assumptions that hidden tests may reject

Inspect all tests and source files.

Add meaningful edge-case tests where appropriate, run the full test suite, and fix any genuine problems you discover.

Do not change the public contract unless necessary.

That second pass is extremely valuable.

Then use a third and final prompt:

Prepare this repository for submission.

Run all tests and lint/format commands configured by the project.

Run git status and inspect git diff.

Remove accidental files, temporary debugging output, generated files that should not be committed, unused dependencies, and unnecessary comments.

Verify the README explains the pricing order and assumptions.

Do not commit or push anything yet.

Tell me whether the repository is submission-ready and explicitly list any remaining issue.

Then you only need to do the Git part.

You can even ask Agent mode:

Commit all required source/test/documentation changes with the commit message Implement multiplex pricing engine, then push the current branch to origin. Do not force push.

But watch this step. Before allowing the push, make sure the assessment instructions actually want you to push to that branch.

What I would optimize for

Do not try to impress them with React, databases, UI, Docker, microservices, etc.

The prompt says:

pricing engine

So unless their repo asks for an API/UI, your best solution is probably a small domain module + strong unit tests + clear README.

The impressive bit here is not visual polish.

It is getting this perfectly right:

₹ → discounts → caps → fees → GST → exact paisa → readable breakdown.

And designing it so tomorrow another theatre could use:

Platinum ₹650
Luxury ₹900
GST 18%
Fee ₹35
different offers

without rewriting the engine.

One more thing: if you open the repo and send me the README / file structure / starter code, I can tell you exactly what hidden-test traps I see and give you a much more surgical Agent prompt for that actual repository.

Yes, that stack is solid for this assessment.

I’d lock it as:

Frontend: React + Vite + JavaScript
Backend: Python + FastAPI
Money calculations: Python Decimal
Backend testing: pytest
Frontend testing: Vitest, only if time permits
Styling: Tailwind if you want faster polish, plain CSS if you want fewer dependencies

The architecture should stay:

React UI
   ↓
FastAPI
   ↓
Pricing Engine
   ↓
Decimal calculations

The main rule: all authoritative pricing must happen in Python, not in React.

For example, React can send:

{
  "tier": "Gold",
  "quantity": 3,
  "festival_offer": true,
  "member": true
}

FastAPI should return:

{
  "base_subtotal": "1200.00",
  "festival_discount": "100.00",
  "member_discount": "110.00",
  "convenience_fee": "60.00",
  "gst": "189.00",
  "total": "1239.00"
}

And React just displays it.

For styling, I’d choose Tailwind if Copilot is building the UI because it can produce a polished page very quickly. If you want the most minimal setup, use CSS.

So my final recommendation is:

React + Vite + JavaScript + Tailwind
FastAPI + Python Decimal + pytest

That gives you a good-looking customer-facing product without compromising the correctness of the pricing engine.

seat_class,price
Gold,₹400
gold,400.00
 GOLD ,₹ 400
Silver,250
Recliner,
Premium,-500
Platinum,"INR 650.00"
in this there is gold, silver, recliner, premium, platinum 
but in site i can only see any three one so fix this by giving a prompt to copilot

Yes, understood. You want the normal booking page to already have a complete cinema seat catalogue, independent of CSV import. CSV should be an optional feature to update/import prices, not the thing that creates the seat choices.

Give Copilot this prompt:

The current booking UI shows only a few seat tiers by default. I want the normal application to feel like a complete multiplex booking system even before any CSV is uploaded.

Make this change without redesigning the application or changing the pricing logic.

GOAL

The booking page must ALWAYS show a proper default set of seat classes when the app first loads.

Use these default demo tiers:

Silver
- ₹250.00
- 30 seats available

Gold
- ₹400.00
- 12 seats available

Premium
- ₹500.00
- 20 seats available

Platinum
- ₹650.00
- 10 seats available

Recliner
- ₹800.00
- 0 seats available
- show as SOLD OUT and disabled

These are demo configuration values only.

IMPORTANT:
Do not hardcode these names inside the pricing calculation logic.
Keep them in the centralized cinema/configuration layer so the pricing engine remains generic and reusable for any cinema.

==================================================
DEFAULT BOOKING EXPERIENCE
==================================================

When the website first opens, before uploading any CSV:

Show ALL five seat-class cards:

Silver
Gold
Premium
Platinum
Recliner

The cards should display:

- seat-class name
- ticket price
- number of seats left
- sold-out state where applicable

Recliner should remain visible but disabled with a clear SOLD OUT badge.

Do not hide sold-out tiers.

The user should immediately understand all seat categories offered by the cinema.

Make the seat-tier area responsive:
- desktop: clean row/grid of cards
- smaller screens: wrap naturally
- mobile: 1 or 2 cards per row as appropriate

Do not allow cards to overflow the container.

==================================================
CSV IMPORT BEHAVIOR
==================================================

CSV import is an OPTIONAL administrative/configuration feature.

The booking page must not depend on a CSV being uploaded before seat classes are visible.

Keep the default tiers available from application startup.

When a valid CSV is imported:

1. Clean and validate it using the existing importer.
2. Show the existing Import Report:
   - Imported
   - De-duplicated
   - Rejected
3. For valid imported seat classes that already exist in the default catalogue:
   - update that tier's price using the cleaned imported price
   - preserve its existing availability unless the import format explicitly contains availability

Example:
Gold ₹400 default
CSV contains Gold ₹450
→ Gold should remain a seat tier but now display ₹450

4. For a new valid imported seat class that does not already exist:
   - add it as a new selectable tier
   - assign a sensible demo/default availability such as 30 seats unless the existing architecture has a better explicit policy

5. Rejected CSV records must NOT alter the existing seat catalogue.

Example:
Recliner has a blank price in CSV
→ report that CSV row as rejected
→ do NOT delete the existing Recliner tier from the normal booking catalogue

Premium has -500
→ report it as rejected
→ do NOT remove the existing Premium tier

6. Duplicate imported rows should follow the existing importer rules and should not create duplicate seat cards.

7. Add/keep a “Reset to default prices” action.
When clicked:
- restore the original five default tiers
- restore their original prices
- restore their original availability
- clear the imported configuration/report where appropriate

==================================================
BACKEND
==================================================

The backend must remain the source of truth.

GET /api/config should initially return all five default tiers.

Do not define the default tier catalogue separately in React.

React should render whatever valid configuration FastAPI returns.

The pricing engine must continue working generically for arbitrary tier names.

Do not duplicate pricing calculations in React.

==================================================
TESTS
==================================================

Add or update tests to verify:

- all five default tiers exist before CSV import
- Recliner exists but is sold out
- sold-out tier cannot be booked
- valid CSV matching an existing tier updates its price
- new valid CSV tier is added
- rejected CSV row does not delete an existing default tier
- duplicate CSV records do not create duplicate cards/config entries
- Reset restores the complete default catalogue
- pricing still works using updated/imported prices

Run the complete pytest suite afterward.

Also run:

npm run build

and ensure the frontend still builds successfully.

Do not change unrelated UI or pricing behavior.

At the end tell me:
- files changed
- final default seat catalogue
- how CSV affects existing tiers
- tests passing
- frontend build result

This will give you the behavior you actually want:

Before CSV:

Silver | Gold | Premium | Platinum | Recliner (Sold Out)

After a messy CSV: valid data can update/add tiers, but invalid CSV data doesn't make normal cinema categories disappear.

That is also a more natural demo because the booking system works immediately, while the messy-price-list importer remains a separate assessment feature.