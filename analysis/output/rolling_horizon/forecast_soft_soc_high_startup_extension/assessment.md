# High Startup-Cost Extension Assessment

This extension tests whether much higher startup cost is enough to keep generators online longer and reduce short 1-2 timestep runs.

The table includes the earlier lower-startup anchor points for the same two controller settings, plus the new high-startup cases.

| Setting | Startup | Fuel delta % | Fuel kg | Starts | Short runs | Min SOC % | Final SOC % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| H=12, SOC penalty=10000 | 500 | 3.89 | 697.517 | 8 | 3 | 20.31 | 32.82 |
| H=12, SOC penalty=10000 | 1000 | 9.34 | 734.109 | 6 | 1 | 21.14 | 52.84 |
| H=12, SOC penalty=10000 | 2500 | 5.02 | 705.131 | 7 | 2 | 20.44 | 37.31 |
| H=12, SOC penalty=10000 | 5000 | 7.31 | 720.444 | 7 | 2 | 22.94 | 45.27 |
| H=12, SOC penalty=10000 | 10000 | 6.42 | 714.532 | 7 | 2 | 21.14 | 42.39 |
| H=12, SOC penalty=10000 | 20000 | 4.59 | 702.221 | 8 | 3 | 22.23 | 35.11 |
| H=12, SOC penalty=10000 | 50000 | 7.75 | 723.407 | 6 | 1 | 21.64 | 47.30 |
| H=16, SOC penalty=1000 | 500 | 3.08 | 692.073 | 9 | 4 | 24.35 | 30.43 |
| H=16, SOC penalty=1000 | 1000 | 5.82 | 710.484 | 8 | 3 | 25.49 | 40.21 |
| H=16, SOC penalty=1000 | 2500 | 4.42 | 701.101 | 8 | 3 | 22.02 | 35.14 |
| H=16, SOC penalty=1000 | 5000 | 5.85 | 710.679 | 8 | 3 | 24.52 | 40.40 |
| H=16, SOC penalty=1000 | 10000 | 6.15 | 712.741 | 7 | 2 | 22.40 | 41.36 |
| H=16, SOC penalty=1000 | 20000 | 4.85 | 703.973 | 8 | 3 | 20.08 | 36.06 |
| H=16, SOC penalty=1000 | 50000 | 3.22 | 692.991 | 6 | 1 | 16.99 | 30.17 |

## Readout

- Best valid fuel case in this comparison: `h16_startup500_softsoc1000` at 3.08% fuel delta, 4 short runs, final SOC 30.43%.
- Best valid low-pulse case: `h12_softsoc10000_startup50000` at 7.75% fuel delta, 1 short runs, final SOC 47.30%.
- Very high startup cost is not monotonic. In several cases it changes the SOC trajectory enough that fuel and pulse counts do not move smoothly.
- Startup cost can reduce pulses, but pushing it very high can either increase reserve/fuel or allow deeper SOC spending depending on the horizon and SOC penalty.
- This supports treating startup cost as a coarse regularization lever, not a clean anti-chatter mechanism.

## Practical Implication

The higher startup-cost extension does not remove the need for a direct commitment-regularity experiment. If short runs remain unacceptable, a minimum-up-time or explicit switching/stop penalty is a cleaner next test than continuing to raise startup cost.

## Generated Plots

- `high_startup_trends.png`
- `high_startup_tradeoff.png`
