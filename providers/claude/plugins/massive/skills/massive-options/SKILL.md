---
name: massive-options
description: "Use when working with options on Massive.com - an option chain, a contract's quote or Greeks, implied volatility, an expected move, gamma exposure, or a historical options backtest on past bid/ask - or when an options call returns without Greeks/IV or 403s."
metadata:
  category: recipe
  requires:
    skills: [massive-api, massive-data-accuracy]
---

# Work with options

Pull an option contract or chain and read it correctly, live or historical. Traps: the `O:` ticker, the x100 notional, an options 403 read as the whole class being blocked, and live-only fields used in a backtest.

> **PREREQUISITE:** load `massive-api` (host, auth, calling; `massive-api/references/massive-catalog.md` = entitlement, `massive-api/references/massive-data-shapes.md` = quote fallback + freshness) and `massive-data-accuracy` (freshness, do-not-invent). Verify paths against the endpoint's `.md` docs page (listed in `llms.txt`) / `search_endpoints`.

## Steps (live chain)

1. **Resolve the contract(s).** `O:` OCC id = underlying + expiry(YYMMDD) + `C`/`P` + strike x1000 padded to 8 digits, e.g. `O:AAPL240119C00150000`. Build it from a described position, or pull the chain and filter. Never pass a bare "AAPL call".
2. **Snapshot.** One contract: `GET /v3/snapshot/options/{underlying}/{O:contract}`. Chain: `GET /v3/snapshot/options/{underlying}`. Confirm against the spec.
3. **Quote.** Use the `last_quote` bid/ask mid when the snapshot has it. The options snapshot often has no `last_quote` or `last_trade` (off-hours, or by plan): then, **on Options Advanced+ only** (quotes gate there; `massive-api/references/massive-catalog.md`), take the latest NBBO from `/v3/quotes/{O:contract}?order=desc&limit=1` and state its time. Below Advanced, use `day.close`, label it as the session's last trade (not a live price), and name the missing quotes entitlement. Read `delta`/`gamma`/`theta`/`vega` and `implied_volatility` **if present**.
4. **Greeks/IV absent = plan, not data.** They need **Options Starter+**. Options Basic (free) holds no snapshot entitlement at all - it is EOD minute aggregates plus reference data - so the chain call fails rather than returning Greeks-less rows. Snapshots and Greeks gate together, so no tier returns a Greeks-less chain: an entitled key that omits `greeks`/`implied_volatility` on a contract is a per-contract data gap, not a tier limit. Say which it is; never report an empty filter as "no matches" and never invent the values. **In-the-money contracts often come back with no `greeks` and no `implied_volatility`** (on one SPY expiry, every contract without Greeks was an ITM put). Exclude them from Greek-weighted totals and say how many you dropped, or compute them yourself and label them as computed. On a **403**, hand off to `massive-debug-endpoints`: the 403 is the specific capability, not the whole class.
5. **Expected move (optional).** ATM straddle (`call_mid + put_mid`) or `spot x IV x sqrt(DTE/365)` - state which. Skip and say so if Greeks/IV are not entitled; do not invent it.
6. **Present:** contract(s), quote + basis, Greeks/IV **or** the named entitlement gap, dollar notional (**price x 100 x contracts**), freshness.

## Historical options (backtests)

The snapshot endpoints are live-only. An expired contract returns `Options contract not found.` Use these instead:

1. **Find the contracts that existed on a past date:** `GET /v3/reference/options/contracts?underlying_ticker=SPY&as_of=2024-03-15&expiration_date=2024-04-19`. Without `as_of` (or `expired=true`) expired contracts are not returned.
2. **Historical bid/ask:** `GET /v3/quotes/{O:contract}?timestamp.gte=...&timestamp.lt=...` gives the NBBO at any past time. For the quote in force at time T, use `timestamp.lte=<T>&order=desc&limit=1`. `sip_timestamp` is nanoseconds. Needs an Options tier with quotes (`massive-api/references/massive-catalog.md`).
3. **Historical bars:** `/v2/aggs/ticker/{O:contract}/range/...` works for expired contracts.
4. **Historical Greeks and IV do not exist on any plan.** Compute IV and delta yourself from the quote mid, the underlying price at the same time, and the time to expiry. Label them as modeled.
5. **Do not use snapshot prices in a backtest.** Price each fill from the quote at the fill time, and state mid vs natural (bid for sells, ask for buys).

For many contracts or long windows, Options Flat Files avoid thousands of REST calls (`massive-api/references/massive-flat-files.md`; they need separate S3 credentials).

## Notes
- **Chain-wide totals (gamma exposure, OI by strike):** page the whole chain (`next_url`) before summing, and state your sign convention. For 0DTE, API gamma and a plain Black-Scholes gamma on clock time can differ a lot; do not mix the two in one total.
- **Notional = price x 100 x contracts.** A $2.50 option is $250/contract. Dropping the x100 is the common options error.
- **Options is its own entitlement class.** A Stocks Advanced key gets options only as **free EOD REST** until you hold an Options plan; options follow the Options plan you hold (`massive-api/references/massive-catalog.md`). Never say the class is blocked.

---
**Every number comes from an API response or a deterministic computation on one - never estimate or invent.** State the quote basis, the x100 notional, and freshness. If the plan returns no Greeks/IV/expected-move, say so. If an endpoint's shape does not match, re-verify against the endpoint's `.md` docs page (listed in `llms.txt`) / `search_endpoints`.
