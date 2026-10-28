# Massive MCP: hosted vs self-hosted

The Massive MCP server is an **optional accelerant** for interactive data lookups - it lets an agent discover and call endpoints via tools instead of hand-writing REST. It is never required (the skills default to raw REST) and **never belongs in code the user ships** (see the client-axis in `massive-api`). Two flavors:

## Hosted (recommended for interactive use)
- **URL:** `https://mcp.massive.com`. GA. Auth is **OAuth** (`auth.massive.com`) - one browser authorization, no key to paste.
- **Register by hand in Claude Code:** `claude mcp add --transport http massive https://mcp.massive.com/`, then `/mcp` to authorize.
- **Register by hand in Cursor:** add `"massive": { "url": "https://mcp.massive.com" }` under `mcpServers` in `~/.cursor/mcp.json`. Cursor starts the OAuth flow on first use.
- Also a connector for Claude Desktop and ChatGPT.
- **Best for:** a human-in-the-loop session (someone can complete the OAuth once).

## Self-hosted (for headless / API-key / bulk-local)
- **Repo:** `massive-com/mcp_massive` (public), stdio by default. Auth is `MASSIVE_API_KEY` (Bearer); `POLYGON_API_KEY` is a deprecated alias.
- **Install + register (canonical, from the mcp_massive README):**
  ```bash
  uv tool install "mcp_massive @ git+https://github.com/massive-com/mcp_massive@v0.10.0"
  claude mcp add massive-local -e MASSIVE_API_KEY=your_api_key_here -- mcp_massive
  ```
  In Cursor, add `"massive-local": { "command": "mcp_massive", "env": { "MASSIVE_API_KEY": "your_api_key_here" } }` under `mcpServers` in `~/.cursor/mcp.json`.
  Name it `massive-local` so it does not collide with a hosted `massive` server. Do **not** use `uvx --from ... mcp_massive` - it re-downloads deps every cold start and can exceed Claude's 30s connection timeout (the mcp_massive README says the same).
- **Best for:** headless/CI agents (no browser to complete OAuth) and pulling large datasets locally.

## Which to reach for
- **Human-in-the-loop interactive session** -> hosted (`mcp.massive.com`, OAuth).
- **Headless / autonomous / CI / API-key only** -> self-hosted (`mcp_massive`), or just direct REST with the key.
- **Building an app that ships** -> neither. Write REST/SDK; the MCP is a session tool, not a runtime dependency.

## Tools (both flavors expose the same shape)
- `search_endpoints` - find the right path/endpoint from a description (use with `scope="functions"` to discover the finance-function registry).
- `call_api` - call a resolved endpoint.
- `query_data` - SQL over stored result tables, plus a closed finance-function registry (Greeks, returns, Sharpe/Sortino, SMA/EMA) applied via an `apply` pipeline.

Fully-qualify tool names when you name one (`massive:search_endpoints` for the hosted server, or your local server's name). If no Massive MCP is registered, do not tell the user to install one - use REST.
