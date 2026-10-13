# Massive AI

Official [Massive.com](https://massive.com) plugins and skills for AI coding
assistants. They teach your assistant how to use the Massive market-data API
correctly: the right host and auth, when to use REST, WebSocket or Flat Files,
what your plan is entitled to, and how to get historically accurate numbers.

## Install

You need a Massive API key. Get one at [massive.com](https://massive.com) and
export it before starting your assistant:

```bash
export MASSIVE_API_KEY=your_key_here
```

### Claude Code

```
/plugin marketplace add massive-com/ai
/plugin install massive@massive-plugins
```

Restart the session to load the skills.

### Cursor

The `massive` plugin also ships a Cursor manifest. Install instructions will
be added here when it is listed in the Cursor Marketplace.

## Plugins

| Plugin | Platforms | What it does |
| --- | --- | --- |
| [`massive`](providers/claude/plugins/massive/) | Claude Code, Cursor | Skills for the Massive API: auth and host, REST vs WebSocket vs Flat Files, entitlements, accurate historical data, and recipes for backtests, screens, options, streaming and more. Optionally registers the hosted Massive MCP server. |

## Layout

Content is grouped by the platform it targets:

```
.claude-plugin/marketplace.json   # Claude Code marketplace catalog
.cursor-plugin/marketplace.json   # Cursor marketplace catalog
providers/
  claude/plugins/<name>/          # Claude Code plugins (some also ship to Cursor)
  chatgpt/<name>/                 # ChatGPT apps, GPT configs and action schemas
```

## Contributing

Issues and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
