---
name: massive-api
description: Use when calling the Massive.com market-data API, or hitting problems doing so - 401/403 auth failures, wrong-host errors (polygon.io vs api.massive.com), "endpoint not found", wrong package or SDK names, or uncertainty about which endpoint or access method to use for stocks, options, indices, currencies (crypto/forex), or futures.
---

# Massive API access

A stale `polygon.io` host or package name is the most common first-call failure: agents reach for it out of training data.

## Always, before any call

- **Host:** `api.massive.com`. Never `polygon.io` / `api.polygon.io`.
- **Auth:** `Authorization: Bearer <key>` header, key from `MASSIVE_API_KEY`. Do not put the key in a URL query.
- **Packages** (do not substitute from training): Python `massive` (`from massive import RESTClient`), JS `@massive.com/client-js`, Go `github.com/massive-com/client-go/v3`. Not `polygon-api-client`, not `@polygon.io/client-js`.
- **Confirm the path exists** against the endpoint's docs page (`massive.com/docs/rest/llms.txt` lists every endpoint with a link to its `.md` page), or `search_endpoints` if an MCP is present. Do not invent paths or assume an SDK method exists.
- Read responses correctly: [references/massive-data-shapes.md](references/massive-data-shapes.md) (FMV, adjusted, freshness).
- Check coverage + entitlement: [references/massive-catalog.md](references/massive-catalog.md).
- Fundamentals / filings / financials: [references/massive-fundamentals.md](references/massive-fundamentals.md) (statement endpoints, point-in-time via the original filing date).

## Pick the access path (two axes)

### 1. Delivery mode - by the task

| Task | Mode |
| --- | --- |
| Point/recent query, snapshot, single-symbol lookup | **REST** |
| Live streaming (quotes/trades/aggregates as they happen) | **WebSocket** |
| Bulk history (a full backtest, whole-market history) | **Flat Files** (S3, by date) |

Bulk history is a **Flat Files** job (one S3 pull), not paginated REST (thousands of requests). Access, credentials, and path structure: [references/massive-flat-files.md](references/massive-flat-files.md).

**WebSocket is entitlement-gated.** Real-time WS needs the Advanced tier on stocks, options, indices and futures; on currencies (crypto + forex) the paid Starter plan is already real-time and there is no Advanced tier. Delayed WS runs on the lower paid tiers (check `references/massive-catalog.md`); free plan uses REST. Connection mechanics (host, auth handshake, subscribe frames, channels like `T.`/`Q.`/`A.`): [references/massive-websocket.md](references/massive-websocket.md). A public or data-redistributing dashboard likely triggers professional-use rules (see `references/massive-catalog.md`).

### 2. Client - route by what the user is doing

- **Building an app, integration, or any code that ships** (the common case): write against the **REST API / SDK**, verified against the spec. That is the source apps are built on. **Never put a Massive MCP in the code you hand the user** - the MCP is a session tool, not a runtime dependency of their product.
- **A one-off interactive lookup in this session:** if a Massive MCP is registered, use it as an accelerant - prefer hosted `mcp.massive.com` (OAuth), or a self-hosted `mcp_massive`. Its `search_endpoints` -> `call_api` find the path fast. Optional - fall back to REST, and never tell the user to install one.
- **Headless / autonomous / CI (no browser):** the hosted `mcp.massive.com` needs a one-time interactive OAuth, so don't reach for it there. Use direct REST with `MASSIVE_API_KEY` (the default, zero setup), or a self-hosted `mcp_massive` (API-key auth) if you want the discovery tools.

Details:
- **Default is raw REST**, `Authorization: Bearer <key>`. Works from any language or `curl`, zero install.
- **Language SDKs** (Python `massive`, JS, Go) wrap the same REST surface; reach for them on heavier integrations.
- An agent that happens to have the MCP registered **still writes REST/SDK for the user's app** - the MCP never belongs in shipped code.
- MCP detail (hosted vs self-hosted, registration, headless, which to use): [references/massive-mcp.md](references/massive-mcp.md).

## Request and response shape

Per-endpoint paths come from the endpoint's `.md` docs page (listed in `llms.txt`) / `search_endpoints`; the envelope is universal.

**Request**
- Base `https://api.massive.com`, versioned paths (`/v2/aggs/...`, `/v3/reference/...`, `/v2/snapshot/...`). Versions differ per endpoint - confirm.
- Auth header (a legacy `?apiKey=<key>` query also works; prefer the header).
- Common query params: `adjusted`, `limit`, `sort`, `order`. Aggregates carry `multiplier`/`timespan`/`from`/`to` in the **path**, not the query.

**Response envelope** (JSON):
```json
{ "status": "OK", "request_id": "...", "results": [ ... ], "next_url": "...", "resultsCount": 123 }
```
- `results` holds the data. Count field varies: `count` on v3 list endpoints, `resultsCount`/`queryCount` on aggregates.
- **`status` values: `OK`, `DELAYED`, `ERROR`, `NOT_AUTHORIZED`.** `DELAYED` appears on `/v3/trades` and `/v3/quotes` for a delayed entitlement. `OK` does NOT mean real-time. Freshness is `last_trade.timeframe` / `last_quote.timeframe` (`"DELAYED"`/`"REAL-TIME"`) on v3 snapshots (forex has only `last_quote`); v2 snapshots have no `timeframe`, so use timestamp lag. See `references/massive-data-shapes.md`.
- `next_url` present means more pages.

**Pagination:** follow `next_url` until absent. **Re-attach the `Authorization` header on each follow.**

**Errors:** HTTP 4xx with `status` `ERROR` (text in `error`) or `NOT_AUTHORIZED` (text in `message`, `error` is null). Read both fields. Triage below.

**Worked example** - daily AAPL bars, adjusted, newest first:
```bash
curl -sS --max-time 15 \
  -H "Authorization: Bearer $MASSIVE_API_KEY" \
  "https://api.massive.com/v2/aggs/ticker/AAPL/range/1/day/2026-06-01/2026-06-30?adjusted=true&sort=desc"
```
`results` is an array of bars `{ t, o, h, l, c, v, vw, n, ... }`; `t` is the start-of-window timestamp in **milliseconds**.

**For "is this real-time or delayed?" call `/v3/snapshot?ticker.any_of=<ticker>`, not bars.** Read `results[].last_trade.timeframe` (`last_quote.timeframe` for forex, which has no `last_trade`). Starter plans get no `last_trade` here, so use timestamp lag on `min.t` (see `references/massive-data-shapes.md`). v2 snapshots and aggregates carry no `timeframe`, and a closed prior session's bar is identical on both feeds.

More worked calls (snapshot, crypto/index, pagination loop, reference lookups): [references/massive-data-shapes.md](references/massive-data-shapes.md) under "Worked calls."

## When a call fails

- **401 / 403 / `NOT_AUTHORIZED`:** auth or entitlement, not code. Check the key, then `references/massive-catalog.md` - the plan may not include that asset class, tier, or add-on. Say so; do not thrash on the code.
- **Data looks stale / delayed:** not an error. The class may be EOD or delayed on this plan. See freshness in `references/massive-data-shapes.md`, tiers in `references/massive-catalog.md`.
- **429 / rate limited:** free (Basic) tier caps calls per minute; paid tiers lift it. Exponential backoff. SDK gotcha: the SDK drops the HTTP status on a rate-limit, so detect by matching the error body text (`maximum requests` / `rate limit` / `too many requests`), not the status code.
- **`endpoint not found` / 404:** path is wrong or invented. Re-confirm against the endpoint's `.md` docs page (listed in `llms.txt`) / `search_endpoints`.
- **Wrong-host or import errors:** a `polygon.io` host or pre-rebrand package name. Fix per "Always, before any call."
- **`CERTIFICATE_VERIFY_FAILED` (Python):** a local setup problem, not a Massive outage. Python from the python.org macOS installer has no CA bundle until you run its `Install Certificates.command`. Use `requests`, or pass `certifi.where()` to `ssl.create_default_context`. **Never retry a certificate error** and never hide it behind a generic "giving up" message.

## Before building something real

Close the two gaps this skill leaves open rather than hardcoding facts that rot:

1. **Resolve the exact endpoint paths.** Versions differ (v2 vs v3); confirm against the endpoint's `.md` docs page (listed in `llms.txt`) / `search_endpoints`.
2. **Establish the plan tier.** It governs real-time vs delayed, WebSocket access, and rate limits, and is **not API-queryable**. Ask the user, or infer from responses (v3 snapshot `last_trade.timeframe`, timestamp lag). See `references/massive-catalog.md`.
