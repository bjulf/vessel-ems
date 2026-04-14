# Operational Signal Inventory

Date: 2026-04-13

## Purpose

This note inventories the signals available in the current operational export and groups them by how useful they are for electrical-load and SFOC analysis.

Source files:

- [data/v01.csv](../data/v01.csv)
- [data/v01_clean.csv](../data/v01_clean.csv)

## Short Answer on HPUs

No explicit HPU or hydraulic-power-unit tags were found in this export.

I checked the raw column names in [data/v01.csv](../data/v01.csv:1) and found no tags containing terms such as:

- `HPU`
- `Hydraulic`
- `Pump`
- `Hydraulic Power Unit`

I also ran a broader keyword search over the current export schema for terms such as:

- `hyd`
- `pump`
- `power unit`
- `winch`
- `crane`
- `deck`
- `aux`
- `hotel`

and still found no explicit HPU-like or hydraulic-load tag.

So if HPU loads exist on the vessel bus, they are not separately measured in this dataset. They would therefore be absorbed into the residual `other onboard load` bucket used in [analysis/power_proxy_validation.md](./power_proxy_validation.md).

## Explicitly Usable Load Signals

These are the load-side signals that are both present and useful in the current export.

| Signal | Practical use | Notes |
|---|---|---|
| `Propulsion Main Electric > Port > Inverter > Power` | Explicit measured load | Nonzero and useful |
| `Propulsion Main Electric > Starboard > Inverter > Power` | Explicit measured load | Nonzero and useful |
| `Thruster Electric > Port Aft > Inverter > Power` | Explicit measured load | Present, occasionally nonzero |
| `Thruster Electric > Port Forward > Inverter > Power` | Explicit measured load | Present, occasionally nonzero |

These are the signals used as `known_load_kw` in the proxy-validation work.

## Generation / Source / Proxy Signals

These are not direct load measurements, but they are useful for inferring supply, operating regime, and fuel behavior.

| Signal | Practical use | Notes |
|---|---|---|
| `Energy Storage Main > Battery Space > Power` | Battery charge/discharge power | Used directly in power balance |
| `Energy Storage Main > Battery Space > State of Charge` | Battery state | Sparse but useful for context |
| `Generator Set > 1 > Engine > Fuel Rate` | Fuel-flow signal | Used for telemetry SFOC work |
| `Generator Set > 1 > Engine > Load percentage` | Power proxy | Used as `load % * 385 kW` |
| `Generator Set > 1 > Engine > Speed` | Regime detection | Used to split `~1400` vs `~1800 rpm` |
| `Generator Set > 1 > Engine > Torque percentage` | Secondary context | May help later with interpretation |
| `Generator Set > 2 > Engine > Fuel Rate` | Fuel-flow signal | Used for telemetry SFOC work |
| `Generator Set > 2 > Engine > Load percentage` | Power proxy | Used as `load % * 385 kW` |
| `Generator Set > 2 > Engine > Speed` | Regime detection | Used to split `~1400` vs `~1800 rpm` |
| `Generator Set > 2 > Engine > Torque percentage` | Secondary context | May help later with interpretation |
| `Navigation Data > Location Current > Speed Over Ground` | Operational context | Could help classify transit vs non-transit |

## Present but Zero in This Export

These tags exist in the raw export schema but are zero throughout the inspected dataset, so they are not useful for this specific period.

| Signal | Comment |
|---|---|
| `Power Distribution Main AC > 1 > Microgrid > Power` | Present, but zero throughout |
| `Power Distribution Main AC > 1 > Shore Connection > Power` | Present, but zero throughout |
| `Power Distribution Main AC DC Shore Connection > 1 > Inverter > Power` | Present, but zero throughout |
| `Thruster Electric > Power` | Present, but zero throughout |
| `Thruster Electric > Starboard Aft > Inverter > Power` | Present, but zero throughout |

## Loads That Are Not Explicitly Measured Here

These likely exist physically on the vessel, but they are not broken out as explicit tags in this export.

| Load category | Status in this export | Likely treatment in analysis |
|---|---|---|
| Hotel load | Not explicit | Falls into residual other onboard load |
| Auxiliary services | Not explicit | Falls into residual other onboard load |
| HPU / hydraulic power unit loads | Not explicit | Falls into residual other onboard load |
| Other pumps, fans, HVAC, control loads | Not explicit | Falls into residual other onboard load |
| Full vessel bus demand | Not explicit as a useful nonzero tag | Inferred only indirectly |

## Most Important Missing Signals

These are the highest-value missing measurements for improving the current analysis.

| Missing signal | Why it matters |
|---|---|
| Per-genset active electrical power `kW` | Would replace the `load % * 385` proxy |
| Generator power setpoint | Would help interpret PLC speed-switch logic directly |
| Running status / breaker status | Would improve steady-state and startup filtering |
| Full bus or microgrid load | Would tighten the power-balance check |
| Explicit HPU or hydraulic load tags | Would reduce the unexplained residual load bucket |

## Practical Interpretation

The current export is good enough to support:

- exploratory SFOC analysis,
- speed-regime identification,
- first-pass validation of the generator `load %` signal as a power proxy,
- partial electrical-balance checks against propulsion and thruster loads.

The current export is not good enough to support:

- exact per-genset electrical efficiency claims,
- exact PLC threshold validation in `kW`,
- a full vessel-load decomposition,
- explicit HPU-load analysis.
