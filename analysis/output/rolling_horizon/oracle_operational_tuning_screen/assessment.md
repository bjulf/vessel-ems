# Oracle Operational Tuning Screen Assessment

Completed cases assessed: 11. Full-horizon benchmark reference is 671.394 kg fuel and 4 starts.

## Main readout

- Lowest rolling-horizon fuel is `soft_h24_soc20_p350_c1000` at 701.622 kg, 4.50% above the full-horizon benchmark, with 12 starts and final SOC 34.79%.
- The screen baseline `soft_h24_soc20_p1000_c1000` uses 707.323 kg, 5.35% above the full-horizon benchmark, with 13 starts and final SOC 34.79%.
- The best case saves 5.700 kg relative to the screen baseline, so this screen is tuning small-to-moderate controller behavior rather than changing the fundamental gap to the offline benchmark.

## Sweep lessons

- Longer oracle horizons did not improve realized fuel in this screen. H=24 gives 5.35% fuel delta, while H=72 rises to 13.63% and ends at 69.31% SOC. The longer controller is carrying more reserve instead of converting the extra foresight into lower fuel.
- Raising the preferred lower SOC band from 20% to 40% increases fuel from 707.323 to 738.401 kg. It buys higher final SOC, but the cost is visible and monotonic.
- A lower soft-SOC penalty performs best among the soft-band cases: 350 g/kWh gives 701.622 kg, while 1500 g/kWh gives 716.619 kg. The lower penalty allows local plans to borrow against the preferred band, but realized SOC still respects the physical 20% minimum in these runs.
- Higher startup penalties do not reduce starts in the realized trajectory here. Starts move from 13 at 1000 g/start to 14 at 5000 g/start, with higher fuel. The local rolling decisions appear constrained by near-term load and SOC recovery more than by this startup-cost range.
- Terminal-reserve variants sit close to the soft baseline in fuel, with the best terminal case at 709.305 kg and 9 starts. They reduce starts relative to the soft baseline but end with a higher reserve.
- `term_h24_t20_p1000_c1000` should be treated cautiously: it has 2 non-optimal local solves and a maximum local solve time of 5343.5 s. Its fuel is competitive, but the solve profile is not robust enough for a clean recommendation.

## Interpretation

The practical lesson is that oracle load foresight is not enough by itself. The rolling controller still pays a nontrivial price relative to the full-horizon benchmark because it implements only the first step and must repeatedly re-create an end-of-local-horizon SOC policy. Cases that are more conservative about reserve, either through longer horizons or higher preferred SOC, leave more energy in the battery and use more fuel. The best-performing screen setting is therefore the less conservative soft-band penalty, not the longest horizon or highest reserve target.

## Generated artifacts

- `composed_case_metrics.csv`: ranked case-level metrics with sweep-family labels.
- `composed_dispatch_timeseries.csv`: per-case, per-timestep composed dispatch/SOC time series.
- `plots/oracle_tuning_ranked_fuel.png`: ranked fuel penalty and starts.
- `plots/oracle_tuning_sweep_tradeoffs.png`: parameter sweep tradeoff panels.
- `plots/oracle_tuning_soc_profiles.png`: representative SOC trajectories.
- `plots/oracle_tuning_solve_profile.png`: local solve-time profile.
