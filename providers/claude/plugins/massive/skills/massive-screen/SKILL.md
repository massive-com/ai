---
name: massive-screen
description: Use when filtering the Massive.com stock universe into a ranked list - gainers/losers, fundamental thresholds (P/E, margins, growth), or technical criteria - a natural-language screen, survivorship-aware.
metadata:
  category: recipe
  requires:
    skills: [massive-api, massive-data-accuracy]
---

# Screen the market

Filter the universe into a ranked list from Massive data. The traps are survivorship (screening today's members over history) and look-ahead on fundamentals (using a quarter before it was filed). Both route through `massive-data-accuracy`.

> **PREREQUISITE:** load `massive-api` and `massive-data-accuracy`. See `massive-api/references/massive-fundamentals.md` for financial-statement shapes and `massive-api/references/massive-catalog.md` for entitlement. Confirm each path against the endpoint's `.md` docs page (listed in `llms.txt`) / `search_endpoints`.

## Steps

1. **Define the screen:** universe, filter criteria (price/volume, fundamentals, technicals), ranking metric, and as-of date. State them.
2. **Resolve the universe.** A full-market screen "now" uses the all-tickers snapshot as the universe. A historical "as of" screen needs the names listed on that date, including later-delisted ones: build it with `massive-universe` (survivorship; `massive-data-accuracy`). An index screen needs index membership, which Massive does not have; source it elsewhere.
3. **Pull the filter data:**
   - Price / volume / day change -> full-market snapshot `GET /v2/snapshot/locale/us/markets/stocks/tickers` (snapshots need Starter+; `massive-api/references/massive-catalog.md`).
   - Multi-day history for the whole market (average volume, prior closes) -> grouped daily bars `GET /v2/aggs/grouped/locale/us/market/stocks/{date}?adjusted=true`, one call per session. Do not loop per-ticker bars over thousands of names.
   - Fundamentals -> `/stocks/financials/v1/*` statements and `/stocks/financials/v1/ratios` (`massive-api/references/massive-fundamentals.md`). For an as-of screen, gate on the original filing date from the filings index, not the statement's `filing_date`.
   - Technicals -> the indicator endpoints (SMA/EMA/RSI) or compute from bars.
4. **Apply filters.** Respect freshness (timestamp lag on the v2 all-tickers snapshot, which has no `timeframe`; see `massive-api/references/massive-data-shapes.md`) and point-in-time fundamentals (original filing date <= as-of; `massive-api/references/massive-fundamentals.md`). Drop tickers with missing data - do not guess a value to keep them in.
5. **Rank** on the chosen metric; present the ranked list with each ticker's metric values, the basis, and the freshness.

## Notes
- Snapshots require Starter+, and the Financials add-on is separate from any stocks tier (`massive-api/references/massive-catalog.md`). A 403 on either is entitlement, not code.
- "Screen the S&P 500 in 2019" is survivorship-biased unless you use 2019's membership, not today's. Say so if you can't get point-in-time membership.

---
**Every number in the output must come from an API response or a deterministic computation on one - never estimate, extrapolate, or invent a value the data does not contain.** State the basis and the freshness. Drop tickers with missing data rather than filling the gap. If an endpoint's shape does not match this recipe, re-verify against the endpoint's `.md` docs page (listed in `llms.txt`) / `search_endpoints`.
