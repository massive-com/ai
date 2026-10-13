---
name: massive-data-accuracy
description: "Use when computing anything numeric from Massive.com market data over time - returns, total return, a backtest, a screen, adjusted prices - or when a number must be right: an adjusted return that looks too low, a split that looks like a crash, a backtest that's too good to be true, total-return vs price-return confusion, or delayed/stale data mistaken for live."
---

# Massive data accuracy

Getting the numbers right when Massive data feeds a calculation. On financial data a confidently wrong number is worse than no number, so compute the unforgiving parts deterministically (generated code or a source function), verify against a known anchor, and signal an explicit gap rather than guess. Never eyeball a numeric transform.

This is the correctness spine the analysis recipes (`massive-backtest`, `massive-screen`, `massive-earnings-prep`, `massive-market-brief`) build on. For reading a single response (FMV fallback, ticker formats, bar timestamps, the freshness signal) see `massive-data-shapes`; for what a key is entitled to see `massive-catalog`.

## The traps, and the rule for each

### 1. Adjustment: `adjusted=true` is split-only, not total return
- Massive's `adjusted=true` adjusts for **splits, not dividends**. An adjusted price series is **price return, not total return** - understated by the dividend yield. Do not call it total return.
- For total return you reinvest each cash dividend yourself (on the ex-date). See [references/adjustment.md](references/adjustment.md).
- Feed **raw** bars (`adjusted=false`) into any adjustment you compute - adjusting already-adjusted data double-counts.
- A backtest on unadjusted data across a split is silently wrong (a 4:1 split reads as a 75% crash).
- **Self-check:** your split-only output must equal Massive's own `adjusted=true` series for the same window. If it doesn't, the split data or the code is wrong - fix that before trusting the total-return layer on top.

### 2. Look-ahead: only use what was known at time T
- A signal for time T must use only data available at T. No peeking at later bars, later fundamentals, or restated numbers.
- Adjustment factors are inherently forward-looking (they encode future splits/dividends). Fine for charting and historical return analysis; a trap for a live-strategy backtest, where the strategy at T could not have known them. Keep the two uses separate.

### 3. Survivorship: today's members are not history's
- Massive returns index **levels, not constituents** - no "list S&P 500 members" endpoint, and no point-in-time membership. Backtesting or screening today's membership over history excludes every name dropped or delisted, which flatters results.
- For all listed US stocks on a past date (including later-delisted names), Massive's reference data has it: see `massive-universe`. For index membership, get a **point-in-time** list from another source, then query those tickers per period.

### 4. Freshness: stale data returns with no error
- Entitlement (real-time / delayed / EOD) is not API-queryable. Read freshness from the response: `last_trade.timeframe` on a v3 snapshot, or timestamp lag on a v2 snapshot (see `massive-data-shapes`), not the envelope `status`.
- Delayed or EOD data comes back looking normal. Building a "live" number on 15-minute-old or prior-session data is a silent error. If the user expects live and the class is delayed, that's a plan limit (`massive-catalog`) - say so.

## Where the math runs

Instructions, not a bundled script. For the unforgiving parts:
- **Prefer a deterministic source** where one exists: `mcp_massive`'s function registry computes Greeks, returns, Sharpe/Sortino, SMA/EMA over a fetched table; the REST indicator endpoints and the `massive` SDK also compute server-side. Point there instead of re-deriving.
- **Total-return adjustment:** generate it in the user's own stack from [references/adjustment.md](references/adjustment.md). Cross-check the dividend factor against `historical_adjustment_factor` on `/stocks/v1/dividends`, and run the split-only self-check above so it can't be silently wrong.
- Never have the model do the series arithmetic by hand.

## Before returning a number
- **Every number you report must come from an API response, or a deterministic computation on one - never estimate, extrapolate, or invent a value the data does not contain.**
- State the basis: raw, split-adjusted, or total return. They are different numbers.
- State the freshness: real-time, delayed, or EOD.
- If you can't compute it confidently (missing dividends, unknown membership, delayed feed), return the gap explicitly, not a plausible guess.
