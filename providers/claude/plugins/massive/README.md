# Massive

Skills for using the Massive.com market-data API correctly from Claude Code and Cursor: right host and auth, the REST / WebSocket / Flat-Files decision, entitlements, and data accuracy.

## Skills

Capabilities (shared knowledge the recipes build on):
- `massive-api`: host, auth, and the REST / WebSocket / Flat-Files decision.
- `massive-data-accuracy`: total-return adjustment, point-in-time, look-ahead, survivorship, freshness.

Recipes (trigger on the matching request):
- `massive-backtest`: a correct backtest on adjusted, point-in-time data.
- `massive-screen`: a ranked screen, survivorship-aware.
- `massive-earnings-prep`: the data for an earnings workflow.
- `massive-market-brief`: prices, index levels, movers, status, news.
- `massive-debug-endpoints`: diagnose a wrong-host, wrong-endpoint, or entitlement failure.
- `massive-options`: an option contract or chain, Greeks/IV, expected move.
- `massive-stream`: a live WebSocket stream of trades, quotes, or aggregates.

## API key

Calls use `Authorization: Bearer $MASSIVE_API_KEY`. Get a key at massive.com.

## MCP (optional)

Registers the hosted Massive MCP (`mcp.massive.com`, OAuth) as an optional accelerant for interactive lookups. The skills work over direct REST without it.

## Cursor

The same directory is also a Cursor plugin. Cursor reads `.cursor-plugin/plugin.json` and `mcp.json`. Claude Code reads `.claude-plugin/plugin.json` and `.mcp.json`. Both manifests point at the one `skills/` directory, so a skill change ships to both clients. Keep the two MCP files in step. `scripts/check_catalog.py` at the repo root checks that the Cursor versions match `.claude-plugin/plugin.json`.
