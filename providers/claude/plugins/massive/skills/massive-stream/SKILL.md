---
name: massive-stream
description: "Use when streaming live Massive.com market data over WebSocket - live trades, quotes, or per-second/minute aggregates, a live dashboard or price monitor - or when a WS connection is rejected, a subscription returns nothing, or a delayed feed is mistaken for real-time."
metadata:
  category: recipe
  requires:
    skills: [massive-api, massive-data-accuracy]
---

# Stream live data

Open a correct live WebSocket stream. Three failure modes: feed above entitlement (connection rejected), wrong channel prefix for the market (subscription silent), delayed feed shown as real-time.

> **PREREQUISITE:** load `massive-api` (owns REST/WS/Flat-Files routing; `references/massive-websocket` = connect/subscribe, `references/massive-catalog` = entitlement) and `massive-data-accuracy` (freshness, do-not-invent). Verify hosts/channels/message shapes against the WebSocket spec - never invent a `wss://` host.

## Steps

1. **WS is for live only.** History or backfill -> REST or Flat Files (`massive-flat-files`), not a socket.
2. **Check entitlement first** (`massive-catalog`, per asset class). **Free tiers have no WS** in any class; use REST. On **stocks, options, indices and futures**, real-time WS = **Advanced**; the lower paid tiers stream **15-min delayed**, or **10-min** on futures. **Crypto and forex (currencies) have no Advanced tier**: the paid Starter plan is already real-time. Not entitled to real-time -> stream **Delayed** and label it, or fall back to REST. Never tell a paid user "unavailable" without checking what their class actually offers.
3. **Prefer an SDK** (handles host, auth handshake, reconnect). Raw socket only with no SDK: the URL is `wss://<host>/<market>` (e.g. `wss://socket.massive.com/crypto`); the bare host 404s. Hosts, paths and the connection cap are in `massive-websocket`.
4. **Feed must match entitlement:** `RealTime`, `Delayed`, `Business`. Which one a paid plan gets depends on the class (step 2). Too-high feed = **rejected at connect**.
5. **Correct channel prefix per market** (the common raw-socket bug). `{action:"subscribe", params:"<CHANNEL>.<TICKER>"}`:
   - **Stocks/options/futures:** `T.` trades, `Q.` quotes, `A.` sec aggs, `AM.` min aggs.
   - **Crypto:** `XT.` trades, `XQ.` quotes, `XA.` min aggs, `XAS.` sec aggs, `XL2.` book. Crypto trade = `XT.BTC-USD`, not `T.`.
   - **Forex:** `C.` quotes, `CA.`/`CAS.` aggs. **No forex trades channel.** Forex symbol = `C.EUR/USD` (slash).
   - **Cross-market:** `FMV.` (Business only), `V.` index values (indices only).
   Messages are a JSON **array**; match each item's `ev` before reading fields.
   **A wrong symbol fails silently:** the server says `subscribed` and sends nothing. No events within a few seconds in market hours = check the symbol format first.
6. **Timestamps:** streamed trade/quote `t` and agg `s`/`e` = Unix **milliseconds**. REST trades/quotes are nanoseconds. Normalize before comparing (`massive-data-shapes`).
7. **Label freshness.** `Delayed` = 15 min behind on stocks/options/indices, 10 min on futures; say so. Arriving != real-time.

## Notes
- **Let the SDK reconnect;** do not hand-roll backoff. Raw socket: send `{action:"auth",...}`, **wait for `auth_success`**, then subscribe.
- **Rejected connection = entitlement, not code.** Re-check feed vs tier before debugging the socket.
- **`.*` = every ticker of a type** (firehose). Subscribe to only what the task needs.

---
**Every value comes from a stream message or a deterministic computation on one - never estimate or invent a tick.** State the feed (real-time vs delayed) and freshness on every live figure. If the feed is not entitled, route to Delayed or REST and say so. If a host/channel/shape does not match, re-verify against the WebSocket spec.
