# Contributing

Thanks for helping improve Massive's AI plugins. Bug reports, fixes to skills
that give wrong answers, and new recipes are all welcome.

## Reporting a problem

Open an issue with:

- The assistant and version (for example, Claude Code 2.x or Cursor).
- The plugin and skill involved.
- What you asked, what it did, and what you expected.
- The endpoint and parameters it called, if it called the API. Leave out your
  API key.

## Making a change

This repo is published from Massive's internal source, so pull requests aren't
merged here directly. A maintainer reviews yours here, applies it upstream, and
closes it with a link once the change is published. Credit stays in that
comment.

1. Fork the repo and create a branch.
2. Make your change. Keep each skill focused on one task.
3. If you changed a plugin, bump its version (see [Versions](#versions)).
4. Run the checks:

   ```bash
   claude plugin validate .
   python3 scripts/check_catalog.py
   ```

5. Install your branch locally and try it the way a user would:

   ```
   /plugin marketplace add ./path/to/your/checkout
   /plugin install <plugin>@massive-plugins
   ```

6. Open a pull request describing what changed and how you tested it.

## The bar for anything in this repo

Every plugin here is run by people outside Massive, on their own machines, with
their own API keys. Before a change is merged it has to meet all of these:

- **No internal hostnames, cluster names, bucket names, IPs, or ARNs.** Not in
  skills, not in scripts, not in example output.
- **No assumed private access.** No VPN-only endpoints, no private MCP servers,
  no side effects in anyone's chat or ticketing tools.
- **Public API surface only.** If a skill needs an endpoint, it must be one a
  customer can call, authenticated the way a customer authenticates.
- **No secrets, tokens, or credential paths**, including in examples. A
  placeholder must look like a placeholder.
- **Works from a clean machine.** No dependency on dotfiles, shell aliases, or
  anything in `~/.claude` the plugin does not ship.
- **A README a user can follow** without outside context.
- **Documented failure modes.** What it does when the API returns nothing, when
  a ticker does not exist, and when the key lacks entitlement.

ChatGPT artifacts under `providers/chatgpt/` meet the same bar. Their action
schemas must point at the public API host and describe how the user's own key
is passed. Never embed a key.

## Adding a plugin

Claude Code plugins live in `providers/claude/plugins/<name>/`, and the
directory name must equal the plugin's `name`:

```
providers/claude/plugins/<name>/
├── .claude-plugin/
│   └── plugin.json          # required: plugin manifest
├── README.md
└── skills/
    └── <skill>/
        └── SKILL.md
```

Add an entry to `.claude-plugin/marketplace.json`:

```json
{
  "name": "<name>",
  "source": "./providers/claude/plugins/<name>",
  "description": "What the plugin does",
  "version": "0.1.0"
}
```

If the plugin also ships to Cursor, add `.cursor-plugin/plugin.json` next to
`.claude-plugin/plugin.json` and an entry in `.cursor-plugin/marketplace.json`.

See the [Claude Code plugin docs](https://code.claude.com/docs/en/plugins) for
hooks, agents and MCP servers.

## Versions

Claude Code only picks up a plugin change when its version changes. When you
change a plugin, bump `version` in all of these, to the same value:

- The plugin's `.claude-plugin/plugin.json`
- Its entry in `.claude-plugin/marketplace.json`
- If it ships to Cursor: its `.cursor-plugin/plugin.json` and its entry in
  `.cursor-plugin/marketplace.json`

`scripts/check_catalog.py` fails when they disagree. CI runs it and
`claude plugin validate .` on every pull request.

## License

By contributing, you agree that your contributions are licensed under the
[MIT License](LICENSE).
