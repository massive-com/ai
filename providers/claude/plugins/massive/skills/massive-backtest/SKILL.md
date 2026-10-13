---
name: massive-backtest
description: "Use when backtesting a trading strategy on Massive.com historical data - a momentum, mean-reversion, or pairs signal over a universe and a period - or when a historical return/performance test must be correct: adjusted for total return, point-in-time, no look-ahead, survivorship-aware."
metadata:
  category: recipe
  requires:
    skills: [massive-api, massive-data-accuracy]
---

# Backtest a strategy

Assemble a historical strategy test on Massive data. The hard part is not the signal, it is not fooling yourself: total-return adjustment, look-ahead, and survivorship each silently inflate results. This recipe routes every one of them through `massive-data-accuracy`.

> **PREREQUISITE:** load `massive-api` (how to call) and `massive-data-accuracy` (adjustment, look-ahead, survivorship, freshness). Confirm each path against the spec / `llms-full.txt` / `search_endpoints` before relying on it.

## By asset class

The steps below are written for **stocks**. For other classes:
- **Forex:** skip steps 2 and 4. There are no splits, dividends, or delistings, and `adjusted` does nothing. Report price return, and say so.
- **Crypto:** skip the split and dividend adjustment (step 4) and report price return. Survivorship still applies, because pairs get delisted (LUNA, FTT). Build each date's pair list from that day's grouped daily bars, `GET /v2/aggs/grouped/locale/global/market/crypto/{date}`. Do not use `tickers?date=` for crypto; it returns today's list for every date.
- **Options:** follow "Historical options" in `massive-options` for contracts, fills, and modeled Greeks. The underlying still needs steps 3 and 4 if you use its price.

## Steps

1. **Define the test, explicitly:** universe, signal rules, rebalance cadence, period, starting capital, and cost assumptions (fees + slippage). State them in the output - a backtest without stated costs and assumptions is not reproducible.
2. **Resolve a point-in-time universe.** **Crypto:** use the pair list from "By asset class", not the stock method below. For all US stocks listed on each date (including names later delisted), build it from Massive with `massive-universe`, per rebalance date. For an index (e.g. the S&P 500), Massive returns index **levels, not constituents** - there is no membership endpoint, so source a point-in-time membership list elsewhere, then query those tickers per period. Backtesting today's membership over history is survivorship bias (see `massive-data-accuracy`); if you cannot get point-in-time membership, say the result is survivorship-biased rather than hiding it.
3. **Pull raw bars.** `adjusted=false` (you will adjust yourself; feeding adjusted data in double-counts). Many tickers or long range -> **Flat Files** (S3, `massive-flat-files`), one pull, not thousands of paginated REST calls. Small/point -> `GET /v2/aggs/ticker/{t}/range/1/day/{from}/{to}?adjusted=false`.
4. **Adjust to total return** per `massive-data-accuracy` -> `references/adjustment.md`, and **run the split-only self-check** (your `split` mode must match Massive `adjusted=true`). Do not proceed on a series that fails the check.
5. **Build signals with no look-ahead.** A signal for date T uses only data with timestamp <= T. Do not use adjustment factors, restated fundamentals, or membership that encode the future.
6. **Simulate honestly.** Enter/exit on the **next bar's open**, not the signal bar's close (same-bar fill is look-ahead). Apply the fee + slippage assumptions on every fill. Track equity.
7. **Compute metrics deterministically** - total return, annualized (CAGR), Sharpe (sample std, ddof=1), max drawdown, hit rate, turnover. Use generated code, never the model doing the arithmetic by hand. Only inside an MCP session with `mcp_massive` loaded, its `simple_return`/`cumulative_return`/`sharpe_ratio` functions also work; they do not belong in code you ship for a REST user.
8. **Report:** the equity curve / summary metrics, the stated basis (**total return** for stocks, price return for forex/crypto), the cost assumptions, and the controls applied (point-in-time universe, no look-ahead, self-checked adjustment). Name any control you could not apply.

## Notes
- A backtest is closed historical data, so **real-time entitlement is not needed** - the cheapest paid tier that unlocks the history depth is enough (`massive-catalog`). Free Basic is ~2yr only.
- The three biggest silent errors, in order: **survivorship** (today's members over history), **total-return vs price-return** (`adjusted=true` is split-only), and **same-bar look-ahead** (entering on the signal bar's close). This recipe controls all three; if you skip one, flag it in the output.

---
**Every number in the output must come from an API response or a deterministic computation on one - never estimate, extrapolate, or invent a value the data does not contain.** State the basis (total return), the cost assumptions, and the freshness. If a value can't be computed confidently, say so - don't fill the gap. If an endpoint's shape does not match this recipe, re-verify against the spec / `llms-full.txt` / `search_endpoints` before proceeding.
