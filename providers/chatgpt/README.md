# ChatGPT extensions

ChatGPT-targeted artifacts intended for customers: apps, custom GPT
configurations, action/tool schemas, and the prompts that go with them.

One per directory:

```
providers/chatgpt/
  <name>/
    README.md        # what it is, and how a customer loads it
    ...              # whatever that platform needs
```

## These are not marketplace plugins

Claude Code cannot install anything in here. The marketplace schema's plugin
sources are relative paths, `github`, `url`, `git-subdir` and `npm`, and all of
them expect a Claude Code plugin at the other end. There is no ChatGPT source
type, so nothing here appears in `/plugin` and neither catalog lists it.

They live in this repo because the review story is shared: same
[bar](https://github.com/massive-com/ai/blob/main/CONTRIBUTING.md#the-bar-for-anything-in-this-repo), same PR review.
Only the packaging differs.

`scripts/check_catalog.py` deliberately ignores this directory. It asserts that
every directory in `providers/claude/plugins/` is listed in the catalog;
applying that to ChatGPT artifacts would be wrong, since there is nowhere to
list them.

## The bar still applies

Everything in [the external bar](https://github.com/massive-com/ai/blob/main/CONTRIBUTING.md#the-bar-for-anything-in-this-repo)
holds here, and the first item matters more rather than less: an action schema
that points at an internal hostname is a leak whether or not Claude Code can load
it.

Two things to be specific about for this platform:

- **Action schemas name a base URL.** It must be our public API host, not a
  staging or internal one.
- **Auth is the customer's.** A schema's security scheme should describe how a
  customer's own key is passed. Never embed one, not even a revoked one.
