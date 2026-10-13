# Massive catalog: coverage and entitlement

What Massive offers and to whom, so an agent never builds on data that is missing, unentitled, or silently stale.

**Do not hardcode plan prices or limits.** They change. This file teaches the *structure*; fetch current specifics from the products API and read entitlement from responses. Numbers below are illustrative (verified 2026-07-30), not current quotes.

## Contents

- Coverage: asset classes and data types
- The entitlement model
- Delivery mode vs entitlement (WebSocket)
- Add-ons and partner data
- Benzinga endpoints
- Professional vs non-professional
- Agent behavior

## Coverage: asset classes and data types

**Asset classes** (pricing tabs): Stocks, Options, Indices, Currencies, Futures.

- **Crypto (`X:`) and forex (`C:`) both live under Currencies** - no separate "crypto" plan. Do not hunt for a crypto tier by name.
- Indices use the `I:` prefix (`I:SPX`); access gated by the Indices entitlement.
- **Massive provides index *values/levels*, not *constituents*.** No "list S&P 500 members" endpoint. Get a membership list elsewhere, then query those tickers. (All stocks listed on a past date, including delisted ones, *is* available: `/v3/reference/tickers?date=`; see `massive-universe`.)

**Data types:** aggregates (bars), snapshots, trades, quotes, fundamentals (financials & ratios), filings (10-K/8-K/13-F/Forms 3/4), news, corporate actions, economy (Fed/treasury/inflation), reference data.

- Risk-free rate (for Sharpe, Black-Scholes): `GET /fed/v1/treasury-yields?date=<YYYY-MM-DD>` or `?sort=date.desc&limit=1` for the latest.

Outside this set (bonds, mutual funds, arbitrary alt-data): say it is not covered rather than inventing an endpoint.

## The entitlement model

Entitlement is **per asset class AND per data level**, not account-wide.

**Free Basic ($0) is the default on every class: Stocks, Options, Indices, Currencies and Futures.** On all of them, **REST historical works with no paid plan**, even a class you never paid for: minute aggregates, reference data, corporate actions, technical indicators (~2yr history, ~5 calls/min). Free Futures is historical only and carries no corporate actions; free Stocks/Options/Indices/Currencies are end-of-day. No free tier holds snapshots, trades, quotes or WebSocket in any class.

**Everything above Basic is a per-class paid gate** returning `403 NOT_AUTHORIZED` ("You are not entitled to this data") unless you hold the matching paid plan *in that same class*:

- delayed data (15-min on stocks/options/indices, **10-min on futures**), **snapshots**, **delayed WebSocket**, **Flat Files** -> Starter tier or above
- REST **trades** -> Developer tier or above (bulk trades via Flat Files ride the Starter Flat Files gate, not this one)
- real-time data (including **real-time WebSocket**), quotes -> Advanced tier or above on stocks, options, indices and futures. **Currencies (crypto + forex) has no Advanced tier: paid Starter is already real-time.**
- FMV -> Business

A paid plan in one class does **not** extend to another. A **Stocks Advanced** key gets real-time stocks + the stocks WebSocket, but Options gives only **free EOD REST** until you buy an Options plan. Tiers differ by class (e.g. Indices has no Developer tier) - never recommend a tier that does not exist for a class.

**Two dangerous failures:**
- **"data came back" is not "real-time."** An EOD or delayed class returns data with no error. Always check freshness (see `massive-data-shapes`).
- **A 403 rarely means the whole class is blocked.** Free REST still works in every class: end-of-day on Stocks/Options/Indices/Currencies, historical minute aggregates on Futures. The 403 is the specific paid capability you lack (WebSocket, quotes, real-time, snapshots). Tell the user which capability needs which tier, not "you have no access."

## Delivery mode vs entitlement (WebSocket)

**Real-time** WS requires Advanced on stocks, options, indices and futures; on **currencies** the paid Starter plan already streams real-time and no Advanced tier exists. **Delayed** WS runs on the lower paid tiers (15-min, 10-min on futures), so do not tell a paid user "WS is unavailable" without checking their class; on a free plan, use REST. `massive-api` checks the catalog before routing to WS.

## Add-ons and partner data

Some data is a **separate add-on**, priced independently of any asset-class plan:

- **Financials & Ratios** - standalone, no stocks subscription required.
- **NYSE Order Imbalances**, **European Consumer Spending** - separate add-ons.
- **Partner data** via `api.massive.com/<partner>`: Benzinga (news/ratings), ETF Global (ETF analytics), TMX (corporate events). Each a per-dataset add-on.

So **do not assume news, fundamentals, or ETF analytics just because stocks work.** Independent entitlements.

## Benzinga endpoints

Use these paths directly. Do not fetch `llms-full.txt` to find them.

| Path | Use |
| --- | --- |
| `/benzinga/v2/news` | Benzinga articles: `title`, `teaser`, `body`, `tickers`, `channels`, `published` |
| `/benzinga/v1/earnings` | Earnings calendar with actuals and estimates |
| `/benzinga/v1/ratings`, `/benzinga/v1/consensus-ratings/{ticker}` | Analyst rating changes, consensus |
| `/benzinga/v1/guidance` | Company guidance |
| `/benzinga/v1/analyst-insights`, `/benzinga/v1/bulls-bears-say` | Analyst commentary |
| `/benzinga/v1/analysts`, `/benzinga/v1/firms` | Analyst and firm reference |

**News vs news.** `/v2/reference/news` is a separate, multi-publisher feed (Motley Fool and others, with `publisher`, `published_utc`, `insights`). `/benzinga/v2/news` is Benzinga only, with full `body` text. For "Benzinga headlines," use the Benzinga path.

Key params:
- News: `tickers` (or `tickers.any_of=AAPL,MSFT`), `published.gte` / `published.lt`, `channels.any_of`, `limit` (default 100, max 50,000), `sort` (default `published.desc`).
- Earnings: `ticker` (or `ticker.any_of`), `date.gte` / `date.lte`, `importance.gte` (0 to 5), `sort=date.desc`.

Field gotchas:
- **`eps_surprise_percent` and `revenue_surprise_percent` are fractions**, even though the spec says "percentage": `0.0622` = 6.22%. `eps_surprise` is the absolute difference in dollars.
- Earnings `date_status` is `projected` or `confirmed`. Future rows are usually `projected`; say so, and never present a projected date as confirmed.
- Earnings `time` is the report time, US Eastern (`16:20:00` = after the close). Use it to pick the reaction session: after the close -> the next session; before the open -> the same session.
- Future rows omit `actual_eps` (the field is missing, not null). Filter `date.lte=<today>` for history.
- **News `title` and `teaser` can contain HTML entities** (`&amp;`, `&#39;`). Decode them before display or text matching.

## Professional vs non-professional

Individual/self-serve plans are **non-pros only**. A subscriber is **professional** if ANY of:

1. Registered/qualified with the SEC, CFTC, a state securities agency, or a securities exchange/association.
2. An investment advisor under section 202(a)(11) of the Advisers Act of 1940.
3. Employed by a bank or exempt org doing work that would require such registration.
4. A non-US person performing equivalent functions.

Non-professional = a natural person using data solely for personal, non-business use. Misclassification carries penalties, fines, or access restrictions. Professionals route to Enterprise via contact. Full definition: `massive.com/blog/understanding-professional-status`.

**The agent flags, it does not adjudicate.** On professional triggers (building for a firm, redistributing/displaying data, a registered advisor, business use), say: "this looks professional; self-serve plans are non-pros only, you likely need Enterprise," and link the definition. Never tell a user they qualify as non-pro - that is their determination.

## Agent behavior

- Live entitlement (which plan a key holds) is **not API-queryable**. Do not claim to know it.
- On 401/403/`NOT_AUTHORIZED`: treat as auth or entitlement, not code. Name the likely cause (missing asset class, tier, or add-on) and point to check/upgrade.
- On stale-looking data: check freshness from the response, attribute to tier, note real-time for that class is an upgrade.
- Never hardcode prices/limits; fetch current plan/product data from the products API.
- To find what tier an endpoint needs, read that endpoint's docs page - each has an authoritative **Plan Access / Plan History / Plan Recency** section. Do not rely on a memorized matrix; the ladder shifts.
