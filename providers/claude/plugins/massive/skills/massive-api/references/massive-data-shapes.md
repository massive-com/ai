# Massive data shapes: how to read what you get

The non-obvious shapes of Massive data. Descriptive only. Analysis-correctness (point-in-time, look-ahead, survivorship) lives in the analysis skills.

## Contents

- Ticker formats
- Which price is "the price" (FMV and the fallback)
- Adjusted vs raw, and corporate actions
- Aggregate bars: timestamp and timezone
- SIP vs single-exchange
- Detecting data freshness (delayed vs real-time)
- Worked calls

## Ticker formats

Prefixes signal the asset class; getting them wrong is a common first-call failure.

| Class | Format | Example |
| --- | --- | --- |
| Stocks | bare symbol | `AAPL` |
| Options | `O:` + OCC id | `O:AAPL240119C00150000` |
| Crypto | `X:` | `X:BTCUSD` |
| Forex | `C:` | `C:EURUSD` |
| Indices | `I:` | `I:SPX` |
| Futures | contract ticker | `ESU5` |

- `ES`/`NQ` are the *product code* (a filter), not the ticker you query; the contract ticker is e.g. `ESU5`, and futures live under `/futures/v1/...`, not the `/v2/aggs/ticker/...` path.
- `I:` indices return index **levels** with no volume (do not compute notional/volume); an index snapshot carries the level in a `value` field, not `lastTrade` (confirm against the spec).
- `adjusted` is meaningless for crypto/forex (no splits).
- Options are quoted **per share**: dollar notional = price x 100 x contracts. Options **Greeks (delta/gamma/theta/vega) and IV require Options Starter or above**, the same tier that gates the options snapshot itself, so Basic Options 403s on the chain rather than returning it without Greeks.

**REST and WebSocket use different crypto/forex ticker formats - do not blend them.** REST/snapshots use the colon form (`X:BTCUSD`, `C:EURUSD`); WebSocket subscribe params use a different form under the market channel prefix: crypto is hyphenated (`XT.BTC-USD`), forex uses a slash (`C.EUR/USD`). A wrong form subscribes without error and then sends nothing. See `massive-websocket`.

## Which price is "the price" (FMV and the fallback)

No single "current price" field. Take the first one present:

1. **FMV** (Fair Market Value) - Massive's real-time modeled price. **The real-time price on Business plans**, which carry no exchange fees or approvals; exchange feeds are Enterprise. `fmv` is **null/absent on every other plan**, so this step only applies to Business keys. Snapshots and the `FMV.` WebSocket channel. It is a model output, not a printed trade (it behaves like a mid when there is a spread), so label it "FMV" in the output. `fmv_last_updated` is a nanosecond timestamp.
2. **`lastTrade`** - most recent trade on the tape. The price on Developer and above when there is no FMV. **Only returned when the plan includes trades**, so a Starter snapshot has none.
3. **`min.c`** - close of the latest minute bar. The price on Starter. Label its time from `min.t`.
4. **`prevDay` close** - prior session's close. The fallback when there is no bar today (before the open, or a halted name). Never a live price.

By plan on stocks: Business -> FMV. Developer / Advanced -> `lastTrade`. Starter -> `min.c`. Basic has no snapshot (403); use aggregates and label them end-of-day. State which source the price came from.

## Adjusted vs raw, and corporate actions

- Aggregate endpoints take **`adjusted`**. **`adjusted=true` (default) returns split-adjusted prices**; `adjusted=false` returns raw as-traded.
- **`adjusted` is split-adjusted ONLY, not dividend-adjusted.** Unlike Yahoo "Adj Close" or CRSP, this series is **price return, not total return** (understated by the dividend yield). Do not treat the adjusted close as total-return.
- A backtest on **unadjusted** data across a split is silently wrong (a 4:1 split looks like a 75% crash). Know which you have.
- **Corporate-action data** (splits, dividends) comes from reference endpoints as raw data; *applying* it across a series is an analysis concern.

## Aggregate bars: timestamp and timezone

- Bar timestamp `t` is the **start of the aggregate window** in **Unix milliseconds**, not the end. Off-by-one-bar bugs come from assuming end-of-window.
- **Timestamp units differ by source, and mixing ms and ns is off by 10^6.** Normalize before comparing to `Date.now()`. Use this table:

| Source | Field | Unit |
| --- | --- | --- |
| Aggregate bars (`/v2/aggs/...`) | `t` (window start) | ms |
| REST trades / quotes (`/v3/trades`, `/v3/quotes`), all classes | `sip_timestamp`, `participant_timestamp` | ns |
| v2 stocks snapshot | `lastTrade.t`, `lastQuote.t`, `updated` | ns |
| v2 crypto / forex snapshot | `lastTrade.t`, `lastQuote.t` | **ms** |
| v2 snapshot minute bar (all classes) | `min.t` | **ms** |
| v2 crypto / forex snapshot | `updated` | ns |
| v3 snapshots (`/v3/snapshot`, options chain) | `last_updated`, `*_timestamp` | ns |
| WebSocket trades / quotes | `t` | **ms** |
| WebSocket aggregates | `s`, `e` (window start / end) | ms |

  When unsure, count digits: 13 digits = ms, 19 digits = ns.
- Bar fields beyond OHLCV: `vw` (VWAP for the window, not the close), `n` (trade count), `otc` (OTC print flag).
- US equity market hours are Eastern; a day bar aligns to the trading session, not UTC midnight. Convert deliberately.

## SIP vs single-exchange

Trades/quotes come from the **SIP** (consolidated tape across all exchanges) or a single exchange feed. Consolidated is usually what you want for "the" price/volume; single-exchange is a partial view. Know which an endpoint returns before aggregating. **US equities and options only** - crypto and forex have no consolidated tape; their aggregates are a cross-exchange construction.

## Detecting data freshness (delayed vs real-time)

Entitlement (real-time vs delayed vs EOD) is **not API-queryable**, so read freshness from the response:

- **`timeframe` field, v3 snapshots only.** The value is `"DELAYED"` or `"REAL-TIME"`. It is nested, never at `results[].timeframe`:
  - Unified `/v3/snapshot?ticker.any_of=...` (stocks, options, crypto, forex, indices): `results[].last_trade.timeframe` and `results[].last_quote.timeframe`. Forex has no `last_trade`; read `last_quote.timeframe`.
  - Options chain `/v3/snapshot/options/{underlying}`: `results[].underlying_asset.timeframe`.
  - **v2 snapshots (`/v2/snapshot/...`) have no `timeframe`.** Aggregates have none either.
  - The envelope `status` is `DELAYED` on `/v3/trades` and `/v3/quotes` for a delayed entitlement, but `OK` elsewhere even when the data is delayed. Never read `OK` as real-time.
  - **For a pure "is this real-time?" question, call `/v3/snapshot?ticker.any_of=<ticker>` and read `last_trade.timeframe`.** This needs a plan with trades: v3 also omits `last_trade` on Starter, so use timestamp lag on `min.t` there.
- **Timestamp lag** - the check for v2 snapshots and all other data: `now - <timestamp of the price source>`: `fmv_last_updated`, `lastTrade.t`, or `min.t` on a plan without trades. ~15-min lag suggests a delayed feed. False-positives when the market is closed (nights/weekends/holidays) or the symbol is thin (a last trade legitimately lags then even on real-time). Mind units: `fmv_last_updated` and stocks `lastTrade.t` are ns; crypto/forex `lastTrade.t` and `min.t` are ms (see the table above).
- A snapshot whose latest data is the prior session's close means an **EOD** entitlement for that class.
- Delayed data when the user expects live is a plan limit (see `massive-catalog`), not a code error. Say so; note real-time for that class is an upgrade.

## Worked calls

Paths are realistic but **confirm against the endpoint's `.md` docs page (listed in `llms.txt`) / `search_endpoints`** before relying on them.

**Latest price (snapshot):**
```bash
curl -sS --max-time 15 -H "Authorization: Bearer $MASSIVE_API_KEY" \
  "https://api.massive.com/v2/snapshot/locale/us/markets/stocks/tickers/AAPL"
```
Pick the price per the fallback above. This v2 response has no `timeframe`: check freshness from the timestamp of the price source you used (`fmv_last_updated`, `lastTrade.t`, or `min.t`; see "Timestamp lag"). On a plan with trades, you can also call `/v3/snapshot?ticker.any_of=AAPL` and read `last_trade.timeframe`.

**Historical bars (aggregates):**
```bash
curl -sS --max-time 15 -H "Authorization: Bearer $MASSIVE_API_KEY" \
  "https://api.massive.com/v2/aggs/ticker/AAPL/range/1/day/2026-06-01/2026-06-30?adjusted=true&sort=desc"
```
Dates illustrative - compute `from`/`to` from today; expect ~21 bars per 30 calendar days (trading days only).

**Other asset classes (ticker formats):**
```bash
# Crypto snapshot
curl -sS --max-time 15 -H "Authorization: Bearer $MASSIVE_API_KEY" \
  "https://api.massive.com/v2/snapshot/locale/global/markets/crypto/tickers/X:BTCUSD"
# Index snapshot (returns a level, not a tradable price)
curl -sS --max-time 15 -H "Authorization: Bearer $MASSIVE_API_KEY" \
  "https://api.massive.com/v3/snapshot/indices?ticker=I:SPX"
```
Snapshot paths differ by class: stocks `/v2/snapshot/locale/us/markets/stocks/...`, crypto/forex `/v2/snapshot/locale/global/markets/{crypto,forex}/...`, indices `/v3/snapshot/indices`, options `/v3/snapshot/options/...`.

**Paginate (follow `next_url`):**
```bash
url="https://api.massive.com/v3/reference/tickers?market=stocks&limit=1000"
while [ -n "$url" ]; do
  resp=$(curl -sS --max-time 15 -H "Authorization: Bearer $MASSIVE_API_KEY" "$url")
  echo "$resp" | jq '.results[].ticker'
  url=$(echo "$resp" | jq -r '.next_url // empty')
done
```
Keep sending the `Authorization` header on every follow (the cursor URL is not pre-authenticated). Stop when `next_url` is absent.

**Resolve a name (reference):**
```bash
curl -sS --max-time 15 -H "Authorization: Bearer $MASSIVE_API_KEY" \
  "https://api.massive.com/v3/reference/tickers?search=apple&active=true&limit=10"
```
Reference endpoints work on the free tier - a good zero-risk first call to confirm auth.
