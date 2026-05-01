# Rolling-Horizon Tail Forecast Note

Use this note when continuing rolling-horizon controller comparisons.

## Context

The current rolling-horizon oracle configs use:

- `horizon_steps = 24`
- `dt_minutes = 15`
- `forecast_method = "oracle_realized_local_load"`
- `tail_forecast_policy = "repeat_final_load"`

This means each local solve has a fixed 6 h optimization horizon. For update
`r`, the oracle forecast is:

```text
P_hat_L(r,j) = P_L[r+j-1], j = 1,...,24
```

when those realized future loads exist. Near the end of the evaluated profile,
missing future loads are padded by repeating the final available load value.

## Why This Matters

The controller does not read the full future profile at each update. It only
uses the current 24-step local window. However, the last 23 local solves in a
24 h / 15 min profile include artificial tail values so the local MILP remains
24 steps long.

For the synthetic oracle run:

```text
runs/2026-04-26_185124_rolling_horizon_oracle_synthetic
```

the run metadata recorded:

- `tail_forecast_padded_solves = 23`
- `tail_forecast_total_padded_steps = 276`
- `tail_forecast_policy = "repeat_final_load"`

This is technically valid as a fixed-horizon implementation choice, but it can
distort end-of-profile decisions if the final load value is not representative.

## Better End-of-Horizon Options

Preferred for thesis-facing benchmark comparisons:

1. Append a realistic continuation profile, keep the 6 h rolling horizon, and
   score KPIs only on the original evaluation window.

Useful for implementation clarity:

2. Use a shrinking horizon near the end of the profile, with clear metadata
   that no artificial tail load is used.

Only if the synthetic profile is explicitly periodic:

3. Use cyclic wraparound padding from the start of the profile.

More advanced:

4. Replace padding with a terminal value or terminal policy approximation for
   SOC and commitment state.

## Recommended Next Step

Before treating oracle rolling-horizon results as final thesis benchmark
figures, decide and document the intended tail policy. The cleanest benchmark
choice is likely to append a plausible continuation profile and keep reporting
KPIs on the original 24 h window only.
