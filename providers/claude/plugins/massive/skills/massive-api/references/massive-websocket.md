# Massive WebSocket: streaming mechanics

Opening a live stream once `massive-api` has routed you to WebSocket (live quotes/trades/aggregates). **Entitlement-gated:** real-time needs the Advanced tier on stocks, options, indices and futures, while currencies (crypto + forex) is real-time from paid Starter and has no Advanced tier; delayed WS runs on the lower paid tiers; a free plan has no WS (use REST). See `massive-catalog`.

**Prefer an SDK** - it handles the host, auth handshake, and reconnect. Drop to a raw socket only with no SDK, and confirm the raw host + handshake against the WebSocket spec first (do not invent a `wss://` host).

## Contents

- Feeds and tiers
- Connecting (SDK, per language)
- Subscribe: channels and message shape
- Raw WebSocket (only if no SDK)
- Connections and silent failures
- Timestamps

## Feeds and tiers

The feed must match your entitlement or the connection is rejected.

- `RealTime` (default) - Advanced tier; on currencies, paid Starter
- `Delayed` - lower paid tiers (15-min delayed; 10-min on futures)
- `Business` - Business/enterprise

Per-market streams exist for stocks, options, crypto, forex, indices, futures.

## Connecting (SDK)

**Python**
```python
from massive import WebSocketClient
from massive.websocket.models import Market, Feed

ws = WebSocketClient(api_key=key, market=Market.Stocks, subscriptions=["T.AAPL"])  # RealTime by default
# delayed feed on a lower tier:
ws = WebSocketClient(api_key=key, feed=Feed.Delayed, market=Market.Stocks, subscriptions=["T.AAPL"])
ws.run(handle_msg=lambda msgs: [print(m.price, m.size) for m in msgs])
```

**JavaScript / TypeScript**
```javascript
import { websocketClient } from "@massive.com/client-js";
const ws = websocketClient(process.env.MASSIVE_API_KEY, "wss://delayed.massive.com");  // delayed host (verified)
const stocks = ws.stocks();
stocks.onopen = () => stocks.send(JSON.stringify({ action: "subscribe", params: "T.AAPL" }));
stocks.onmessage = ({ data }) => {
  for (const msg of JSON.parse(data)) if (msg.ev === "T") console.log(msg.p, msg.s);
};
```
Per-market connections: `ws.stocks()`, `ws.options()`, `ws.crypto()`, `ws.forex()`, `ws.indices()`, `ws.futures()`.

**Go**
```go
c, err := massivews.New(massivews.Config{APIKey: key, Feed: massivews.Delayed, Market: massivews.Stocks})
if err != nil {
	log.Fatal(err)
}
if err := c.Subscribe(massivews.StocksTrades, "AAPL"); err != nil {
	log.Fatal(err)
}
if err := c.Connect(); err != nil {
	log.Fatal(err)
}
// A bad key does not fail Connect(). The auth failure arrives on c.Error().
for {
	select {
	case err := <-c.Error():
		log.Fatal(err)
	case out, more := <-c.Output():
		if !more {
			return
		}
		_ = out // type-switch on models.EquityTrade, etc.
	}
}
```

## Subscribe: channels and message shape

Subscribe with `{action: "subscribe", params: "<CHANNEL>.<TICKER>"}` (comma-separate multiple; `.*` = all tickers of that type). **Channel prefixes differ by market** - a common raw-socket mistake:

- **Stocks, options, futures:** `T.` trades, `Q.` quotes, `A.` per-second aggs, `AM.` per-minute aggs.
- **Crypto:** `XT.` trades, `XQ.` quotes, `XA.` per-min aggs, `XAS.` per-sec aggs, `XL2.` L2 book. (A crypto trade sub is `XT.BTC-USD`, not `T.`)
- **Forex:** `C.` quotes, `CA.` per-min aggs, `CAS.` per-sec aggs. No forex trades channel. **Forex symbols use a slash: `C.EUR/USD`.** (Crypto uses a hyphen: `XT.BTC-USD`.)
- **Cross-market:** `FMV.` fair market value (Business only), `V.` index values (indices only), `NOI.` / `LULD.` (stocks only).

Messages arrive as a JSON **array**; each carries an `ev` field naming the event (`T`, `Q`, `A`, `AM`, ...). Trade fields: `p` (price), `s` (size); quotes carry bid/ask. Match on `ev` before reading fields.

## Raw WebSocket (only if no SDK)

Connect, send `{action: "auth", params: "<key>"}`, **wait for `{ev: "status", status: "auth_success"}`**, then send subscribe frames.

**The URL is host + market path: `wss://<host>/<market>`.** The bare host returns HTTP 404.

| Host | Feed | Market paths |
| --- | --- | --- |
| `socket.massive.com` | Real-time | `/stocks`, `/options`, `/crypto`, `/forex`, `/indices`, `/futures` |
| `delayed.massive.com` | Delayed | `/stocks`, `/options`, `/indices`, `/futures` (no `/crypto` or `/forex`: paid currencies plans are real-time) |
| `business.massive.com` | Business | real per the SDK; not listed in the spec's `servers` block |

Subscribe examples (real-time host). For options, indices and futures, confirm the ticker form against the spec before subscribing:

| Market | URL | Subscribe `params` |
| --- | --- | --- |
| Stocks | `wss://socket.massive.com/stocks` | `T.AAPL,Q.AAPL,AM.AAPL` |
| Crypto | `wss://socket.massive.com/crypto` | `XT.BTC-USD,XQ.BTC-USD` |
| Forex | `wss://socket.massive.com/forex` | `C.EUR/USD,CAS.EUR/USD` |

## Connections and silent failures

- **A wrong symbol fails silently.** The server replies `subscribed to: <params>` and then sends nothing. `C.EURUSD` and `C.C:EURUSD` both do this; only `C.EUR/USD` streams. If a subscription sends no events within a few seconds during market hours, suspect the symbol format first, not the feed.
- **Concurrent connections per market can be capped by plan.** If the server sends a `max_connections` status and closes the socket (close code 1008), you have too many open connections on that market. Put all tickers on one connection with comma-separated `params` instead of one connection per ticker.
- **Options quotes: at most 1,000 contracts per connection** (per the spec). Subscribe to the contracts you need, not `Q.*`.

## Timestamps

Streamed trade/quote `t` and aggregate `s`/`e` are Unix **milliseconds**. REST trades/quotes are nanoseconds, so normalize before comparing a stream to REST or to now. Full table in `massive-data-shapes`.
