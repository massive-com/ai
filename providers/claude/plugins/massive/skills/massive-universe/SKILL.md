---
name: massive-universe
description: "Use when building a survivorship-free or point-in-time US stock universe from Massive.com data - every name listed on a past date, including ones later delisted, merged, or renamed - for a backtest, a historical screen, or a universe(date) function. Also use when a historical ticker filter returns 0 rows or a delisted name is missing."
metadata:
  category: recipe
  requires:
    skills: [massive-api, massive-data-accuracy]
---

# Build a historical stock universe

List every US stock that was listed on a past date, including names delisted later. Massive's reference data has this, so do not source it elsewhere. The traps: old records with empty fields, tickers reused by a different company later, and wrong CIKs.

> **PREREQUISITE:** load `massive-api` (host, auth, pagination) and `massive-data-accuracy` (survivorship, do-not-invent). Confirm paths against the spec / `llms-full.txt` / `search_endpoints`.

This recipe gives **all listed names**, not an index. Massive has no index membership (no "S&P 500 on date D"); for that, get the membership list elsewhere.

## Steps

1. **Define the universe:** the as-of date D, and which names count (common stock only? ETFs? ADRs? OTC?). State it.
2. **Pull everything listed on D:** `GET /v3/reference/tickers?date=D&market=stocks&active=true&limit=1000`, following `next_url`. This includes names that were delisted after D. `active=false` with `date=D` returns names already gone before D, so leave them out.
3. **Filter after you fetch, not in the query.** On older dates many records have `type: null` and `primary_exchange: null` (on 2008-09-12, 4,406 of 8,225 had no type, AAPL and MSFT included). `exchange=XNAS&type=CS` in the query then returns 0 rows. Fetch without those filters and classify yourself.
4. **Classify names with no `type`:**
   - **Do not copy the type from today's record for the same ticker.** Tickers are reused: `ABAT` on 2008-09-12 is Advanced Battery Technologies, not today's American Battery Technology.
   - Accept a later record only when two things agree: the same `composite_figi` **and** the same ticker or company name. No single ID is enough. Some historical FIGIs point at another listing (2008 GE carries the FIGI of `GE.WD`), and some CIKs are wrong (2008 FRE carries Safe Bulkers' CIK).
   - Names change (GE is now "GE Aerospace"), so a name mismatch alone does not prove a different company. Put those in an `unresolved` group instead of guessing.
   - Otherwise mark the type `unknown`. If you guess from the name or ticker (`ADR`, `PFD`, a lowercase `p` suffix for preferreds, `WT`, `U`), label it as a guess and count how many.
5. **Confirm trading on D (recommended):** `GET /v2/aggs/grouped/locale/us/market/stocks/D?adjusted=false` returns every name with a bar that day. Report listed-but-not-traded and traded-but-not-listed counts. Do not drop either group silently.
6. **What happened to each name after D:** `GET /v3/reference/tickers?ticker=T&active=false` gives `delisted_utc`. A ticker can have several records (reuse); pick the one whose `name` matches.
   - Some names that left have **no inactive record at all** (Wachovia, `WB`). Report them as no longer listed with the date unknown, or bracket the date by querying `tickers?ticker=T&date=...` at later dates.
   - `/vX/reference/tickers/{T}/events` lists recent ticker changes for current names only; it returns `NOT_FOUND` for delisted names and does not reach back far (it does not link 2008 Google to today's `GOOG`/`GOOGL`). Do not infer a rename from a shared CIK.
7. **Price history per name:** bars by ticker return whichever company held the symbol at the time. Limit each name's window to D through its `delisted_utc`, so a later company on the same ticker does not leak in.
8. **Present:** the date, the count by type (including `unknown` and guessed), how many are no longer listed (with and without a known date), the unresolved names, and how you classified the null-type records.

## Notes
- Reference and grouped-daily endpoints are on every plan; history depth depends on the plan (`massive-catalog`).
- For a backtest across many dates, build the universe per rebalance date, not once. Names enter and leave.
- The null `type` / `primary_exchange` fields on old records are a known data gap (tracked by Massive Support). Re-check before building workarounds on a newer date.

---
**Every name and count must come from an API response or a deterministic step on one - never guess a security's type or fate and present it as data.** Label guessed classifications, list unresolved names, and state the as-of date.
