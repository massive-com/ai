# Massive fundamentals: financials, ratios, filings

How Massive exposes company financials and filings, and the one correctness trap that matters (point-in-time via the original filing date). Entitlement note: **Financials & Ratios is a standalone add-on**, independent of any stocks tier (`massive-catalog`) - a stocks plan does not include it.

## Contents
- Financial statements
- Point-in-time: period_end vs the original filing date (the look-ahead trap)
- Filings and forms
- Corporate actions and reference

## Financial statements
- One endpoint per statement, flat fields (not nested):
  - `/stocks/financials/v1/income-statements` - `revenue`, `gross_profit`, `operating_income`, `diluted_earnings_per_share`, `ebitda`, ...
  - `/stocks/financials/v1/balance-sheets` - `total_assets`, `total_liabilities`, `total_equity`, `cash_and_equivalents`, ...
  - `/stocks/financials/v1/cash-flow-statements` - `net_cash_from_operating_activities`, `purchase_of_property_plant_and_equipment`, `dividends`, ...
  - `/stocks/financials/v1/ratios` - one row per ticker per `date`: `price_to_earnings`, `ev_to_ebitda`, `debt_to_equity`, `market_cap`, ...
- Statement params: `tickers=AAPL` (the field is an array; a ticker filter is `tickers`, not `ticker`), `timeframe`, `period_end`, `fiscal_year`, `fiscal_quarter`, `sort=period_end.desc`. Ratios take `ticker`.
- `timeframe`: `quarterly` / `annual` / `trailing_twelve_months`. Pick deliberately - quarterly for trend, annual for stable comps, TTM for a rolling view.
- **Do not use `/vX/reference/financials`.** It is deprecated: responses carry `deprecation: true` and a `sunset` header, and it is being switched off (random `410 Gone` responses first, then removal).
- Values are **standardized** (Massive maps as-reported line items to a common schema). Standardized is not as-reported; for the exact filed figures, go to the filing.

## Point-in-time: `period_end` vs the original filing date (the look-ahead trap)
- Each record carries a **`period_end`** (the last day of the fiscal period it covers) and a **`filing_date`**.
- **`filing_date` is the most recent filing that included this period, not the original one.** A 10-Q restates prior-period comparatives, so an old quarter's `filing_date` moves forward. Example: AAPL's quarter ending 2025-06-28 shows `filing_date: 2026-07-31`.
- So do not gate an as-of screen or backtest on `filing_date`: old quarters would look unavailable. Get the original date from the filings index, `/stocks/filings/vX/index?ticker=<T>&form_type.any_of=10-Q,10-K`, and match each period to its first filing after `period_end`. Query both forms: fiscal Q4 and annual periods are filed in the 10-K, so a 10-Q-only lookup matches Q4 to the next Q1 filing, about 3 months late.
- **Values are the latest version.** Each row holds the most recently filed (possibly restated) numbers, not the numbers first reported. A strict point-in-time backtest cannot recover the originals from this endpoint. Say so.
- Using a quarter's numbers before its original filing date is look-ahead - the market did not have them yet. See look-ahead in `massive-data-accuracy`.

## Filings and forms
- SEC filings index: `/stocks/filings/vX/index?ticker=<T>&form_type.any_of=10-Q,10-K` returns `form_type`, `filing_date`, `accession_number` and `filing_url`. Ownership forms (3, 4, 13F) have their own endpoints; confirm exact paths against the spec.
- Filings are the as-reported source when the standardized financials are not enough.

## Corporate actions and reference
- Splits `/stocks/v1/splits`, dividends `/stocks/v1/dividends` (the `/v3/reference/*` versions are deprecated) - the inputs to total-return adjustment (`massive-data-accuracy` -> `references/adjustment.md`).
- Ticker reference `/v3/reference/tickers` for names and listing status (the active flag matters for survivorship).
- **Earnings estimates, analyst ratings, and an earnings calendar are NOT core** - they come from the Benzinga partner add-on (`api.massive.com/benzinga/...`, see `massive-catalog`). Do not assume them from a stocks plan.
