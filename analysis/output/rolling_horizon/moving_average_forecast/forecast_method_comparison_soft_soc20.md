# Soft-SOC20 Forecast Method Comparison

Same rolling soft-SOC20 MILP controller: soft 20-80% SOC band, physical 0-100% battery bounds, no terminal reserve constraint.

| Case | Forecast | Fuel [kg] | Delta vs full [%] | Starts | Min SOC [%] | Final SOC [%] | Local low slack [kWh] | P95 solve [s] | Power balance |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Synthetic | Persistence | 843.023 | +4.36 | 8 | 38.90 | 38.90 | 0.000 | 4.296 | yes |
| Synthetic | Moving average MA4 | 858.309 | +6.25 | 7 | 43.48 | 46.56 | 0.000 | 1.503 | yes |
| Operational | Persistence | 707.396 | +5.36 | 13 | 21.49 | 36.20 | 78.958 | 2.250 | yes |
| Operational | Moving average MA4 | 735.110 | +9.49 | 8 | 29.37 | 53.51 | 59.595 | 1.343 | yes |
