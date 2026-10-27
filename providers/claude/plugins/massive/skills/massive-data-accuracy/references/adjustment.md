# Total-return and corporate-action adjustment

Turning raw Massive bars + corporate actions into a correct adjusted series. These are instructions for code you generate in the user's own stack, not a script to ship. Keep raw bars as input.

## Inputs
- Raw bars: `/v2/aggs/...` with `adjusted=false`.
- Splits: `/stocks/v1/splits?ticker=<T>`. Fields: `execution_date`, `split_from`, `split_to`, `adjustment_type`, `historical_adjustment_factor`.
- Dividends: `/stocks/v1/dividends?ticker=<T>`. Fields: `ex_dividend_date`, `cash_amount`, `split_adjusted_cash_amount`, `distribution_type`, `historical_adjustment_factor`.
- Do not use `/v3/reference/splits` or `/v3/reference/dividends`. They are deprecated and use different field names.

Match actions to bars on the **ex-date** (`ex_dividend_date`, `execution_date`). Normalize timestamp units first (bar `t` is milliseconds; see `massive-api/references/massive-data-shapes.md`).

## Modes
- `raw` - as traded.
- `split` - split-adjusted only. Must match Massive `adjusted=true` (the self-check).
- `total_return` - split + dividends reinvested. Massive `adjusted=true` does not include dividends.

## Splits (backward cumulative factor)
For each historical date, multiply price fields by the product of `split_from / split_to` for every split whose `execution_date` is **after** that date. Divide volume by the same product. A 4:1 split (`split_from=1`, `split_to=4`) scales pre-split prices by 1/4.
Cross-check: each split record's `historical_adjustment_factor` is this cumulative product from that split forward (NVDA: 0.1 on the 2024 10:1, 0.025 on the 2021 4:1).

## Dividends (total return)
Work backward from the latest bar. On each ex-date, the multiplier is `1 - cash_amount / close_before_exdate`, where `close_before_exdate` is the raw close of the last session before the ex-date. The dividend factor for a date is the product of the multipliers for every ex-date **after** that date. Every multiplier is below 1, so old prices go **down**, never up.

The total-return series is `raw_price * cumulative_split_factor * cumulative_dividend_factor`.

## Cross-check with `historical_adjustment_factor`
Each `/stocks/v1/dividends` record carries `historical_adjustment_factor`. It is the cumulative dividend factor from that ex-date forward, including that ex-date's own multiplier. Apply it to prices dated **before** that ex-date. Your computed factor must match it to about 6 decimals.

- The factor runs through **today**, not your window's end. To cross-check, compute your factor over bars through today.
- Records do not come back in date order. Sort by `ex_dividend_date` before computing.
- If they diverge, check the ex-date alignment and which close you used before trusting either number.
- The field can be wrong across a ticker rename (for example, ELV/ANTM). When a ticker changed symbol in the window, trust your own computation and flag the gap.

## Ex-date, not pay-date
Apply every action on its ex-dividend / ex-split date.

## Self-check (mandatory)
Compute `split` mode and compare to Massive `adjusted=true` for the same window. They must match within rounding. If they diverge, **stop** - the split data or the code is wrong; do not ship the total-return number built on top of it.

## Point-in-time caveat
The factors encode future actions. Fine for a historical or charting series. For a live-strategy backtest, a signal at time T must not use factors from actions after T (see look-ahead in the parent skill).
