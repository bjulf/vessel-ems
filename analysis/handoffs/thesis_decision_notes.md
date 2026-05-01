# Thesis Decision Notes

Compact notes for major modeling and thesis-interpretation decisions. This is a working defense and continuation aid, not polished thesis prose.

## Major Modeling Decisions

### Use the OEM SFOC Curve in the MILP

Decision: Keep the OEM SFOC curve as the optimization input.

Reason: The telemetry-derived SFOC work is useful as an empirical operating-regime assessment, but it is not robust enough to replace the OEM curve in the MILP.

### Use the No-Terminal Full-Horizon Baseline

Decision: Treat the no-terminal full-horizon benchmark as the main comparison baseline.

Reason: Terminal SOC constraints can distort fuel and start comparisons by forcing artificial end-of-horizon SOC carryover.

### Use Mean-Normalized Soft SOC Penalty in Rolling Horizon

Decision: Use `soft_soc_penalty_scaling = "mean"` for the rolling-horizon soft SOC controller.

Reason: The summed soft SOC penalty scales with horizon length and can make longer local horizons excessively conservative. Mean normalization keeps the penalty interpretation more stable across horizon lengths.

### Treat Terminal SOC Reserve as SOC Robustness, Not Anti-Chatter

Decision: Do not use soft terminal SOC reserve as the main anti-chatter mechanism.

Reason: In the weak terminal-reserve sweep, terminal reserve increased fuel use and final SOC while failing to reduce short generator runs compared with the no-terminal mean-soft-SOC reference. The mechanism is still meaningful as an SOC robustness signal, but it acts indirectly through battery energy economics rather than directly on generator commitment duration.

### Use Minimum Up-Time as the Anti-Chatter Direction

Decision: Treat minimum up-time as the main direction for suppressing low-load generator chatter in the rolling-horizon controller.

Reason: Minimum up-time acts directly on commitment duration. The `min_up_time_steps = 6` case reduced starts and removed sub-1.5-hour generator runs with moderate fuel and SOC impact compared with weaker indirect mechanisms.

### Keep a Startup Penalty in the Receding-Horizon Baseline

Decision: Keep a modest generator startup penalty in the receding-horizon/rolling-horizon baseline rather than setting startup cost to zero.

Reason: Minimum up-time prevents very short on-periods, but it does not discourage frequent legal on-blocks. Zero-startup cases reduced fuel in the operational contender sweep, but increased start counts substantially. With a weak SOC penalty, the zero-startup case also produced poor SOC behavior and a time-limited local solve. The startup penalty is therefore retained as a commitment-regularization term, with its value treated as a sensitivity parameter rather than a fully validated physical startup-fuel estimate.

### Reject Shutdown Penalty for the Main Rolling-Horizon Baseline

Decision: Do not add a shutdown penalty to the main rolling-horizon thesis baseline.

Reason: A shutdown-penalty diagnostic tested `shutdown_cost = 0, 250, 500, 1000 g/shutdown` on the selected `H16 MA4 C500 P10k min_up6` setup. The zero-cost case reproduced the selected baseline. Nonzero shutdown penalties kept a generator online at the March 3 17:45 endpoint, confirming that the observed stop is related to commitment hysteresis / rolling-horizon myopia. However, the nonzero cases materially increased fuel penalty, increased starts from 5 to 7, and produced less attractive commitment blocks without keeping the same genset continuously online through the full March 3 high-load window. Treat shutdown penalty as a diagnostic result, not a baseline mechanism.

### Freeze Two Rolling-Horizon Thesis Contenders

Decision: Freeze two 3-day operational-profile rolling-horizon contenders for thesis reporting: `config/rolling_horizon_thesis_balanced.toml` as the main balanced baseline and `config/rolling_horizon_thesis_conservative.toml` as the conservative/operator-style comparison.

Reason: The balanced case keeps the selected `H16 MA4 C500 P10k min_up6` controller with no shutdown penalty and reproduces the clean baseline result: 688.44 kg fuel, +2.54% versus the no-terminal full-horizon benchmark, 5 starts, minimum SOC 20.09%, and final SOC 27.44%. The conservative comparison keeps `H24 MA4 C500 P20k min_up6` with no shutdown penalty and reproduces the cautious/operator-style behavior: 717.71 kg fuel, +6.90%, 5 starts, minimum SOC 23.23%, and final SOC 43.60%. Both accepted freeze reruns had zero nonoptimal/time-limit/infeasible local solves.
