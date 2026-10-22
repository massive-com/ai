---
name: massive-earnings-prep
description: Use when preparing for a company's earnings - pulling the financials history, recent price action and expected move, news, and key dates for an earnings-research workflow on Massive.com data.
metadata:
  category: recipe
  requires:
    skills: [massive-api, massive-data-accuracy]
---

# Earnings prep

Assemble the data for an earnings-research workflow on one name. Read-only: this pulls and organizes the data; the view is the user's.

> **PREREQUISITE:** load `massive-api` and `massive-data-accuracy`. See `massive-api/references/massive-fundamentals.md` (statement endpoints, point-in-time) and `massive-api/references/massive-catalog.md` (entitlements, add-ons). Confirm each path against the endpoint's `.md` docs page (listed in `llms.txt`) / `search_endpoints`.

## Steps

1. **Earnings history and next date.** If the key has Benzinga, start here: `GET /benzinga/v1/earnings?ticker={t}&sort=date.desc`. It gives actual vs estimated EPS, the surprise, the report `time`, and the next date with its `date_status`. Field gotchas (surprise percents are fractions, future rows omit `actual_eps`) are in `massive-api/references/massive-catalog.md`. On a 403 there is no Benzinga: use step 2 for actual EPS, say estimates are not included, and infer the next date from the filing cadence, flagged as inferred.
2. **Financials trend** - recent quarters of `/stocks/financials/v1/income-statements?tickers={t}&timeframe=quarterly&sort=period_end.desc`: `revenue`, `diluted_earnings_per_share`, margins from `gross_profit` / `operating_income`. Order by `period_end` (`massive-api/references/massive-fundamentals.md`).
3. **Reaction to past reports.** Pick the reaction session from the report `time`: after the close -> the next session; before the open -> the same session. Measure that session's close vs the prior close on split-adjusted daily bars `GET /v2/aggs/ticker/{t}/range/1/day/{from}/{to}`. Add a current snapshot for the latest print + freshness.
4. **Expected move** (only if options-entitled; Options Starter+, `massive-api/references/massive-catalog.md`). Quote per `massive-options` step 3. State which method you use:
   - **Straddle:** ATM `call_mid + put_mid` on the first expiry after the report. This includes normal volatility up to that expiry, so it overstates the earnings move alone.
   - **Earnings move alone:** take ATM IV on the last expiry before the report and the first expiry after it. Assuming normal volatility equals `IV_before`, event variance = `(IV_after^2 - IV_before^2) x T_after` (T in years, to the after-report expiry). The one-day move is its square root.
   If not entitled, say so and skip - do **not** fabricate an expected move.
5. **News** - Benzinga headlines `/benzinga/v2/news?tickers={t}` if entitled, else `GET /v2/reference/news?ticker={t}&limit=10`.
6. **Present:** EPS history with surprises and reaction moves, financials trend, expected move and its method (or "not entitled"), headlines, and the next date with its status. State basis + freshness; name any add-on-gated piece that was missing.

## Notes
- Earnings estimates, consensus, and the calendar come from the Benzinga partner feed, independent of a stocks plan. Do not imply them from core data.
- A projected date is not a confirmed date. Never present `date_status: projected` as confirmed.
- Options IV / expected move needs an Options plan (Starter+), which is also the gate on the options snapshot, so Basic Options 403s rather than returning a chain without IV. Skip the expected move and say why (`massive-api/references/massive-data-shapes.md`).

---
**Every number in the output must come from an API response or a deterministic computation on one - never estimate, extrapolate, or invent a value the data does not contain.** State the basis and the freshness. If an add-on-gated piece (estimates, options IV) is unavailable, say so - don't fill the gap. If an endpoint's shape does not match this recipe, re-verify against the endpoint's `.md` docs page (listed in `llms.txt`) / `search_endpoints`.
