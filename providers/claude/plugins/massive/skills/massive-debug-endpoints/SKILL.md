---
name: massive-debug-endpoints
description: Use when a Massive.com API call fails or returns something wrong - 401/403/NOT_AUTHORIZED, 404 "endpoint not found", a wrong-host error (polygon.io vs api.massive.com), a wrong package/SDK name, 429 rate limiting, or data that looks stale - and you need to find the root cause instead of guessing.
metadata:
  category: recipe
  requires:
    skills: [massive-api]
---

# Debug a failing call

Diagnose a broken Massive call and separate the two things that look alike: a **code bug** (wrong host, invented path, wrong package) versus a **plan limit** (entitlement, rate cap). The most common root cause is a hallucinated endpoint - a path invented from training or a stale `polygon.io` prior. The fix is almost always "confirm the path exists against the source," not "reshape the request and retry."

> **PREREQUISITE:** load `massive-api` (host, auth, triage, and the routing to `massive-api/references/massive-catalog.md` for entitlement). Confirm any corrected path against the endpoint's `.md` docs page (listed in `llms.txt`) / `search_endpoints`.

## Triage by symptom

1. **Read the actual error first** - HTTP status + the response `error` string. Do not guess from the symptom alone.
2. Match it:
   - **Wrong host / connection** -> the code used `polygon.io` / `api.polygon.io`. Fix to `api.massive.com`.
   - **`CERTIFICATE_VERIFY_FAILED`** with the correct host -> local Python has no CA bundle (common with the python.org macOS installer). Not a Massive outage. Use `requests` or `certifi`, or run `Install Certificates.command`. Do not retry.
   - **Import / package error** -> a pre-rebrand package (`polygon-api-client`, `@polygon.io/client-js`). Fix to `massive` / `@massive.com/client-js` / `github.com/massive-com/client-go/v3`.
   - **404 / "endpoint not found"** -> the path is invented or the version is wrong (v2 vs v3 differ per endpoint). **Re-confirm the exact path against the endpoint's `.md` docs page (listed in `llms.txt`) / `search_endpoints` - do not invent or retry variants.** This is the hallucinated-endpoint case.
   - **401** -> missing or bad key. Check `Authorization: Bearer <key>` (header, not `?apiKey=`) and `MASSIVE_API_KEY`.
   - **403 / `NOT_AUTHORIZED`** -> **entitlement, not code.** The plan lacks that asset class, tier, or add-on. Name the likely one (`massive-api/references/massive-catalog.md`) and point to check/upgrade. Do not thrash on the request.
   - **429** -> rate limit (free Basic caps per minute). Exponential backoff. Gotcha: the SDK drops the HTTP status on a rate-limit, so match the error body text (`maximum requests` / `rate limit`), not the code.
   - **Data looks stale / delayed** -> not an error. The class is EOD or delayed on this plan; read freshness per `massive-api/references/massive-data-shapes.md` (v3 `last_trade.timeframe` or timestamp lag) and attribute to tier (`massive-data-accuracy`, `massive-api/references/massive-catalog.md`).
3. **Verify the corrected call** against the spec before retrying.
4. **Report the root cause and the fix**, and say clearly whether it was a code bug or a plan limit - they need different actions from the user.

## Notes
- A 403 rarely means the whole asset class is blocked - free REST still works in every class (end-of-day on Stocks/Options/Indices/Currencies, historical minute aggregates on Futures); the 403 is the specific paid capability (snapshots, quotes, real-time, WebSocket). Say which capability needs which tier.
- Retrying an entitlement 403 or a hallucinated 404 without changing the cause just burns rate limit. Fix the cause first.

---
**Do not invent an endpoint, a parameter, or a fix to make an error go away - confirm it against the endpoint's `.md` docs page (listed in `llms.txt`) / `search_endpoints` first.** State whether the root cause is a code bug or a plan limit. If you can't confirm the correct call, say so rather than guessing a path.
