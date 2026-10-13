---
name: massive-market-brief
description: Use when the user wants a morning or market brief, a daily summary, or a "what's the market doing" rundown from Massive.com data - current prices for a watchlist, index levels, top movers, market status, and headline news, presented as a readable brief.
metadata:
  category: recipe
  requires:
    skills: [massive-api, massive-data-accuracy]
---

# Market brief

A readable market rundown from Massive.com data: where the watchlist stands, index levels, what is moving, and whether the market is open. Read-only market data - no account or portfolio state (Massive has no user holdings), so this is a *market* brief, not a P&L brief.

> **PREREQUISITE:** load `massive-api` (how to call: host, auth, endpoints, API-first) and `massive-data-accuracy` (right numbers, freshness). Confirm each path against the spec / `llms-full.txt` / `search_endpoints` before relying on it.

## Steps

1. **Market status** - open, pre/post, or closed:
   `GET /v1/marketstatus/now`
2. **Watchlist snapshot** - price + % change for the user's tickers (if none given, ask or use a small core list):
   `GET /v2/snapshot/locale/us/markets/stocks/tickers?tickers=AAPL,MSFT,NVDA`
   Take the price via the `FMV -> lastTrade -> prevDay` fallback (`massive-data-shapes`); % change vs prev close. This v2 snapshot has no `timeframe`: check freshness with `now - lastTrade.t` (nanoseconds on stocks; `massive-data-shapes`) - if delayed or EOD, label it.
3. **Index levels** - context only (levels, not tradable prices, no volume):
   `GET /v3/snapshot/indices?ticker=I:SPX,I:NDX,I:DJI`
4. **Top movers** - the day's gainers and losers:
   `GET /v2/snapshot/locale/us/markets/stocks/gainers` and `.../losers`
5. **Headline news** (optional) - recent items per ticker:
   `GET /v2/reference/news?ticker=AAPL&limit=5`
6. **Present:** a market-status line; a watchlist table (ticker, price, % change) with basis + freshness noted; index levels; the top 3-5 movers each way; a few headlines. Keep it scannable.

## Notes
- The snapshot steps (2-4) need **Starter or above**: a free key 403s on them, so route those steps to EOD aggregates and say so. Market status (step 1) and news (step 5) are reference data and work on a free key, so keep them in the brief. On a paid but delayed plan the snapshot returns stale data with no error, and the brief must label it (see freshness in `massive-data-accuracy`). A genuinely *live* brief needs real-time entitlement for the class (`massive-catalog`).
- A continuously updating brief means real-time WebSocket = Advanced tier on stocks (currencies: paid Starter). The REST snapshots above are the portable path on any **paid** tier - default to them.

---
**Every number in the output must come from an API response - never estimate, extrapolate, or invent a value the data does not contain.** State the basis (raw / split-adjusted / total return, where relevant) and the freshness (real-time / delayed / EOD). If a value can't be fetched or computed confidently, say so - don't fill the gap. If an endpoint's shape does not match this recipe, re-verify against the spec / `llms-full.txt` / `search_endpoints` before proceeding.
