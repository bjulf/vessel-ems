# Cautious Operator Scan

Scan date: 2026-04-29.

Scope: recent rolling-horizon summary files under `analysis/output/rolling_horizon/` with traceable `run_dir` values. The scan checked 106 unique run directories.

Criterion used for the specific behavior discussed here:

- one generator online continuously through the March 2 variable peak window, `2026-03-02 15:15` to `2026-03-02 19:45`;
- clean local solves where status information was available;
- no more than 6 total generator starts.

Only two tested runs matched that strict pattern:

| Case | Controller family | H | Startup | SOC penalty | Fuel kg | Delta % | Starts | Min SOC % | Final SOC % | Run lengths | Notes |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `h24_startup500_softsoc20000_minup6` | moving-average soft-band with min-up | 24 | 500 | 20000 | 717.71 | 6.90 | 5 | 23.23 | 43.60 | `19 13 18 6 17` | Best tested non-oracle cautious-operator candidate. Continuous through both March 2 and March 3 high-load windows. |
| `soft_h72_soc20_p1000_c1000` | oracle-realized-load soft-band screen | 72 | 1000 | 1000 | 762.90 | 13.63 | 4 | 20.00 | 69.31 | `17 11 20 19` | Even more conservative, but uses oracle future load and has much higher fuel/final-SOC carryover. Not a fair moving-average baseline candidate. |

Near misses with no more than 6 starts:

| Case | Fuel kg | Delta % | Starts | Min SOC % | Final SOC % | March 2 online fraction | March 3 online fraction | Notes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `h16_startup500_softsoc10000_minup6` | 688.44 | 2.54 | 5 | 20.09 | 27.44 | 0.67 | 1.00 | Efficient baseline candidate, but splits the March 2 variable peak into two blocks. |
| `h16_startup1000_softsoc10000_minup6` | 713.14 | 6.22 | 5 | 20.17 | 40.15 | 0.72 | 1.00 | Low starts and high final SOC, but still does not stay continuously online through March 2. |
| `h16_startup500_softsoc5000_minup6` | 701.24 | 4.45 | 6 | 21.41 | 34.22 | 0.83 | 0.94 | Closer to the cautious pattern, but still not continuous through the March 2 window. |
| `h20_startup500_softsoc10000_minup6` | 708.75 | 5.56 | 6 | 20.43 | 38.13 | 0.83 | 1.00 | More conservative than H16 P10k, but still not continuous through the March 2 window. |

Interpretation:

`h24_startup500_softsoc20000_minup6` appears to be the only tested non-oracle controller that combines the cautious-operator commitment shape, low starts, and clean solve behavior. Other tested terminal-reserve and longer-horizon cases often maintain the March 3 window, but they either add many short runs/starts, miss the March 2 continuous block, or carry substantially higher fuel/SOC penalties.

