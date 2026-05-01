# Deep Assessment: Forecast Mean Soft-SOC Tuning

Scope: operational 15-minute average profile, moving-average forecast with window 4, H=12/16, mean-normalized soft SOC penalty.

The screen confirms that normalized SOC penalty reduces excessive terminal charge compared with the old summed penalty, but tuning still exposes a three-way tradeoff: fuel, SOC reserve, and short generator pulses.

## Main Read

- Best fuel while keeping realized minimum SOC at or above 20%: `h12_startup500_softsoc1000` with 2.48% fuel delta, 10 starts, 5 short runs, and final SOC 28.49%.
- Best low-pulse case with realized minimum SOC at or above 20% and at most two short runs: `h12_startup2500_softsoc10000` with 5.02% fuel delta, 7 starts, 2 short runs, and final SOC 37.31%.
- Best valid H=12 case: `h12_startup500_softsoc1000` at 2.48% fuel delta, 5 short runs, final SOC 28.49%.
- Best valid H=16 case: `h16_startup500_softsoc1000` at 3.08% fuel delta, 4 short runs, final SOC 30.43%.

## Candidate Region

Using a pragmatic filter of fuel delta <= 6.5%, short runs <= 3, minimum SOC >= 20%, and final SOC <= 43%, the strongest candidates are:

| Case | H | Startup | SOC penalty | Fuel delta % | Starts | Short runs | Min SOC % | Final SOC % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| h12_startup500_softsoc10000 | 12 | 500 | 10000 | 3.89 | 8 | 3 | 20.31 | 32.82 |
| h16_startup2500_softsoc1000 | 16 | 2500 | 1000 | 4.42 | 8 | 3 | 22.02 | 35.14 |
| h12_startup2500_softsoc10000 | 12 | 2500 | 10000 | 5.02 | 7 | 2 | 20.44 | 37.31 |
| h16_startup1000_softsoc1000 | 16 | 1000 | 1000 | 5.82 | 8 | 3 | 25.49 | 40.21 |
| h12_startup2500_softsoc5000 | 12 | 2500 | 5000 | 6.32 | 8 | 3 | 22.23 | 42.01 |

## Non-Dominated Cases

A case is treated as dominated if another case is no worse on fuel delta, starts, short runs, SOC floor violation, and final SOC above 40%, and strictly better on at least one of those metrics.

| Case | H | Startup | SOC penalty | Fuel delta % | Starts | Short runs | SOC floor violation pp | Final SOC % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| h16_startup500_softsoc250 | 16 | 500 | 250 | 0.46 | 10 | 5 | 1.99 | 20.81 |
| h12_startup500_softsoc1000 | 12 | 500 | 1000 | 2.48 | 10 | 5 | 0.00 | 28.49 |
| h16_startup2500_softsoc250 | 16 | 2500 | 250 | 2.77 | 7 | 2 | 6.98 | 28.88 |
| h16_startup500_softsoc1000 | 16 | 500 | 1000 | 3.08 | 9 | 4 | 0.00 | 30.43 |
| h12_startup500_softsoc10000 | 12 | 500 | 10000 | 3.89 | 8 | 3 | 0.00 | 32.82 |
| h12_startup2500_softsoc250 | 12 | 2500 | 250 | 4.16 | 6 | 1 | 10.24 | 34.41 |
| h12_startup2500_softsoc10000 | 12 | 2500 | 10000 | 5.02 | 7 | 2 | 0.00 | 37.31 |
| h16_startup2500_softsoc10000 | 16 | 2500 | 10000 | 7.28 | 6 | 1 | 0.00 | 45.15 |

## Interpretation

- Very low mean SOC penalty, especially 250 g/kWh, can make fuel look excellent because the controller is allowed to borrow too aggressively from the battery. Several of those cases fall below the 20% preferred SOC floor, so they should not be treated as clean operating candidates unless the thesis explicitly allows preferred-band violations.
- Higher startup cost generally reduces starts and short pulses, but it is not monotonic across all SOC penalties because the rolling forecast and SOC penalty can change when charging becomes attractive.
- Raising the mean SOC penalty protects minimum SOC but tends to increase final SOC and fuel. This is most visible around 5000-10000 g/kWh, where pulse counts can improve but the battery reserve becomes more conservative.
- H=12 gives the clearest low-fuel balanced candidate in this grid. H=16 can produce fewer pulses at high startup cost, but the better low-pulse H=16 cases carry more final SOC and fuel.

## Where To Look Next

1. Refine around the candidate region instead of widening the full grid: H=12 with startup 500-2500 and SOC penalty 7500-12500; H=16 with startup 1500-3000 and SOC penalty 750-2000.
2. Add a small minimum-up-time or switching penalty experiment. Startup cost alone reduces pulses only indirectly; the remaining 1-2 timestep runs are a commitment-regularity issue.
3. Consider asymmetric soft SOC penalties. A higher low-SOC penalty and lower high-SOC penalty could protect reserve without rewarding excessive final charge as strongly.
4. Add a terminal-value term or final-SOC accounting in the KPI comparison. Some low-fuel cases partly win by ending with a lower battery reserve than other cases.
5. Check whether forecast bias is driving unnecessary charging. The moving-average forecast may understate/overstate load around transitions, so forecast diagnostics around pulse windows are worth inspecting before adding more MILP constraints.

## Generated Diagnostic Plots

- `pareto_fuel_vs_short_runs.png`
- `parameter_effects_by_horizon.png`
- `soc_reserve_vs_fuel.png`
- `candidate_region_map.png`
- Existing heatmaps: `heatmap_fuel_delta_pct.png`, `heatmap_starts.png`, `heatmap_short_runs.png`, `heatmap_final_soc.png`

Every case also has `plots/rolling_horizon_dispatch_panel.png` and `plots/rolling_vs_full_horizon_comparison.png` in its run directory.
