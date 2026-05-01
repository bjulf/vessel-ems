# Minimum Up-Time Extension

Same H=12, moving-average forecast, mean soft-SOC penalty 10000 g/kWh, startup cost 500 g/start.

| Min up steps | Min up h | Fuel delta % | Fuel kg | Starts | Min SOC % | Final SOC % | Run lengths | Runs at minimum |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| 3 | 0.75 | 5.02 | 705.096 | 8 | 20.03 | 36.54 | `18 3 12 10 5 3 3 17` | 3 |
| 4 | 1.00 | 4.02 | 698.352 | 8 | 20.09 | 32.25 | `18 4 11 10 5 4 4 17` | 3 |
| 6 | 1.50 | 4.40 | 700.968 | 6 | 20.29 | 33.53 | `17 13 10 6 6 19` | 2 |
| 8 | 2.00 | 8.04 | 725.362 | 6 | 20.67 | 45.27 | `18 16 9 8 8 17` | 2 |

## Readout

- `min_up=3` removes 1-2 step runs, but three realized runs sit exactly at 3 steps, which still looks like chatter.
- `min_up=4` has the same issue at a 1-hour block length, though fuel is slightly better in this run.
- `min_up=6` reduces starts to 6 and only has two minimum-length blocks, with moderate fuel and SOC behavior.
- `min_up=8` further smooths blocks but costs much more fuel and ends with higher SOC.

Best current compromise from this quick test: `min_up_time_steps = 6`.