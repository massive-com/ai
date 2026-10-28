# skills

Two capabilities plus recipes, each a self-contained directory: a `SKILL.md`, plus an optional `references/` subdirectory of on-demand detail.

Capabilities:
- `massive-api/`: the hub. Auth, host, and the delivery-mode decision (REST / WebSocket / Flat Files). Its `references/` cover catalog (entitlement), data shapes, fundamentals, websocket, flat files, and the optional MCP.
- `massive-data-accuracy/`: the correctness spine every recipe uses. Total-return/corporate-action adjustment, point-in-time, look-ahead, survivorship, freshness.

Recipes (`massive-backtest`, `massive-screen`, `massive-earnings-prep`, `massive-market-brief`, `massive-options`, `massive-stream`, `massive-universe`, `massive-debug-endpoints`) are workflows that require one or both capabilities (named in each recipe's `requires` list).

Skill descriptions are triggering-conditions only ("Use when..."), never a workflow summary.
