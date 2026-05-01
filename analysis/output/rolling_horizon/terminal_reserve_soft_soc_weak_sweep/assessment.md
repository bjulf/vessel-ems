# Weak Terminal Reserve Assessment

This sweep isolates the soft-band terminal reserve mechanism with minimum up-time disabled in every case (`min_up_time_steps = 1`). The terminal reserve penalty is intentionally much lower than the 10000 g/kWh preferred SOC-band penalty, so it should be read as a weak reserve signal rather than a direct anti-chatter constraint.

## Results

- Lowest fuel case: `term_t30_p250` with 5.93% fuel delta, 11 starts, 6 short runs, and final SOC 40.07%.
- Lowest short-run case: `term_t30_p500` with 4 short runs, 7.32% fuel delta, 9 starts, and final SOC 45.31%.
- Least harmful balance in this small screen: `term_t30_p250` because it has the best combined ranking across fuel delta, short runs, and final SOC carryover.

## Assessment Questions

1. Does weak terminal reserve reduce low-load generator chatter when minimum up-time is disabled?
   No. The no-terminal mean-soft-SOC reference has 3 short runs and 8 starts; the weak reserve cases have 4-7 short runs and 9-12 starts.

2. Does it mainly increase SOC/fuel instead?
   Yes. The no-terminal reference has 3.89% fuel delta and final SOC 32.82%; the weak reserve cases end between 40.07% and 52.58% SOC, with fuel deltas between 5.93% and 9.34%.

3. Which target/penalty combination is least harmful?
   `term_t30_p250` is the least harmful within this four-case reserve screen, but it is still worse than the no-terminal reference on fuel, starts, short runs, and final SOC. It should be treated as a local result, not a general tuning rule.

4. Is weak terminal reserve competitive with the current min-up-time direction, especially `min_up_time_steps = 6`?
   No. The `min_up_time_steps = 6` reference has 4.40% fuel delta, 6 starts, no sub-1.5-hour runs, and final SOC 33.53%. That directly addresses short commitment blocks, while terminal reserve remains only an SOC reserve signal.

5. Does even weak terminal reserve start to reintroduce excessive SOC carryover?
   The 40% target cases end at the upper end of the observed final-SOC range (48.11-52.58%). This is weaker than the prior 10000 g/kWh terminal-reserve case, but it still shows the expected carryover tendency.

## Thesis-Grounded Interpretation

The terminal reserve constraint is useful as an optimization reserve signal: it asks each local MILP to preserve future battery headroom through a soft one-sided terminal target. It is not a direct anti-chatter constraint. On this single operational profile, weak terminal reserve does not look competitive with a minimum up-time mechanism for suppressing low-load generator chatter. Its cleaner role is SOC robustness, with the known risk of unnecessary charging and elevated final SOC.

## Generated Outputs

- `summary.csv`
- `summary.md`
- `terminal_reserve_heatmap_fuel.png`
- `terminal_reserve_heatmap_starts.png`
- `terminal_reserve_heatmap_short_runs.png`
- `terminal_reserve_heatmap_final_soc.png`
- `fuel_start_short_run_tradeoff.png`
