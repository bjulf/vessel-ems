# Report Writing Handoff

Date: 2026-04-14

## Purpose

This note packages the current guidance for writing the thesis sections related to the telemetry-based SFOC work.
It is intended as a handoff for continuing the report-writing work in a new AI thread without having to reconstruct the discussion.

The thesis report repository is:

- `C:\Users\bulve\OneDrive\master\report\695e178abaa53b0c7651d409`

No report files were edited during this discussion.
The goal here is to preserve the agreed direction for how the telemetry work should be presented in the report.

## Core Decision

The telemetry work should be used in the thesis, but in a limited and controlled way.

Recommended role of the telemetry work in the report:

- use it to strengthen the methodology,
- use it to show that two real generator speed regimes exist,
- use it to explain why practical operation may differ from the fuel-only optimal dispatch,
- do not make the thesis depend on telemetry-derived curves as the main MILP input,
- keep the OEM curve as the baseline generator model in the MILP.

This is the main thesis-safe interpretation:

- the telemetry is valuable as an empirical operating assessment,
- it supports interpretation and discussion,
- it does not need to replace the OEM curve in the optimizer.

## Recommended Placement In The Report

### Methods

Add a dedicated subsection near the end of the Methods chapter:

- `\subsection{Operational data assessment for generator efficiency}`

This should be a self-contained subsection, not just a few extra paragraphs inside `Data processing`.

Reason:

- the telemetry work is substantial enough to deserve its own subsection,
- it will read better with structure,
- it avoids overloading the existing data-processing subsection,
- it makes it easier to reference from Results and Discussion.

Suggested internal structure:

- opening paragraph directly under the subsection heading
- `\subsubsection{Available data}`
- `\subsubsection{Preprocessing and power proxy}`
- `\subsubsection{Operating-regime and SFOC screening}`
- `\subsubsection{Use in this thesis}`

Do not use a separate `Purpose and scope` subsubsection.
Put the introduction directly under the subsection heading.

### Results

Add one short subsection in Results:

- `\subsection{Operational data based assessment of generator operating regimes}`

Keep it short.
The telemetry work should not take over the Results chapter.

### Discussion

Add one short subsection in Discussion, likely under generator modeling / model realism:

- `\subsubsection*{Interpretation of the telemetry based SFOC assessment}`

This is where the telemetry work has the highest value.

## Writing Direction

The report prose should be:

- direct,
- simple,
- educational,
- pragmatic,
- not too polished,
- not too self-contained,
- not repo-like.

It should fit the tone of the existing report better than the earlier, more polished draft.

Important style choices:

- do not mention CSV filenames in the thesis body,
- do not tell the story month by month,
- do not write the section like a standalone paper,
- do explain the method step by step,
- do state clearly that the original goal was to see whether telemetry could support a telemetry-informed SFOC curve for possible use in or comparison with the MILP,
- do keep the final wording cautious.

## What The Methods Section Should Explain

The Methods subsection should describe the full process up to the point where the telemetry work stopped.

It should explain:

1. Why the telemetry work was done

- The OEM curve was the baseline for the MILP.
- Operational telemetry was examined to see whether it could support a telemetry-informed SFOC curve for possible use in or comparison with the optimization model.

2. What data limitations existed

- telemetry extraction was limited to about 4000 data points per export,
- measured per-generator electrical power in kW was not available,
- fuel rate, load percentage, speed, torque, battery power, and propulsion/thruster powers were available,
- this meant that a direct electrical-power-based SFOC reconstruction was not possible.

3. How the power proxy was constructed

- generator power was approximated from generator `Load percentage` and rated generator power,
- the proxy used was:
  - `P_gen,proxy = load_pct / 100 * 385`
- this proxy was treated as an approximation, not a direct measurement.

4. How the proxy was checked

- the combined generator proxy, together with battery power, was compared against the measured propulsion and thruster loads,
- this was used to assess whether the proxy followed the known electrical demand pattern closely enough for exploratory analysis.

5. How the SFOC screening was carried out

- retain only points with positive fuel rate, load percentage, and speed,
- apply a rolling-window stability filter to exclude transient points,
- split points into two regimes using a 1600 rpm threshold,
- convert fuel rate to mass flow using assumed fuel density,
- compute provisional SFOC from fuel mass flow divided by proxy power,
- group points into load bins,
- use bin medians as representative points,
- compare telemetry-derived regime points with the OEM curve.

6. Why more data had to be fetched

- the initial one-minute dataset was enough to identify two regimes,
- but low-speed coverage was too narrow,
- because the extraction limit was around 4000 points, longer horizons had to be screened at lower time resolution,
- those lower-resolution scans were used to identify time windows with stronger low-speed operation,
- new one-minute windows were then fetched only for those targeted periods,
- the analysis was repeated on the expanded dataset.

7. How the telemetry work is used in the thesis

- as a separate empirical operating assessment,
- not as the primary source for the generator curve in the MILP,
- mainly to support interpretation of the optimization results and discussion of model realism.

## What The Results Section Should Say

The Results subsection should stay compact.

The main findings to communicate are:

1. Two real speed regimes were observed

- one around `1400 rpm`,
- one around `1800 rpm`,
- this pattern appeared repeatedly across the available windows,
- it was therefore interpreted as real operating behavior, not just startup and shutdown.

2. The load-percentage power proxy was usable for exploratory analysis

- it followed the known electrical demand pattern closely enough when checked against battery and measured propulsion/thruster loads,
- but it remained a proxy and not a direct electrical power measurement.

3. The first dataset mainly supported the high-speed regime

- the initial one-minute export gave useful support for the `~1800 rpm` regime,
- but the low-speed regime was too narrow at that stage.

4. Targeted follow-up windows improved the low-speed regime coverage

- longer low-resolution scans were used to find candidate windows,
- targeted one-minute windows were then extracted,
- the expanded dataset gave broader support for the low-speed regime.

5. The telemetry-derived regime behavior differed from the OEM curve

- the high-speed telemetry regime was consistently above the OEM curve over its supported range,
- the low-speed telemetry regime was generally below the OEM curve in its supported bins,
- the high-speed mismatch is the clearest and most reliable difference.

6. The telemetry supports interpretation, not replacement of the OEM curve

- the results are informative,
- but still limited by the lack of measured per-generator electrical power,
- therefore they should be used for interpretation and discussion rather than as a direct replacement for the OEM baseline in the MILP.

## What The Discussion Section Should Do

The Discussion subsection should explain what these telemetry results mean without overclaiming.

Recommended interpretation:

- the telemetry indicates that the vessel uses two distinct generator speed regimes,
- this matters because the MILP uses the OEM curve as an idealized fuel-performance description,
- actual operation may be influenced by considerations not represented in the model,
- examples include reserve requirements, transients, unmeasured auxiliary loads, and control choices,
- the telemetry therefore helps explain why a fuel-minimizing MILP may recommend operating patterns that differ from practice.

Important claims to avoid:

- do not claim that the vessel is definitively being operated inefficiently,
- do not claim that telemetry should replace the OEM curve,
- do not claim that operator behavior is wrong,
- do not claim achievable onboard savings directly from the telemetry mismatch.

Safer claims to make:

- the vessel appears to operate in two real regimes,
- observed operation does not align perfectly with the idealized OEM fuel picture,
- practical operation appears to be shaped by considerations beyond fuel minimization,
- the MILP results should therefore be interpreted as fuel-optimal schedules within the chosen assumptions.

## Figures To Use

### Methods Figure

Use one figure in Methods that helps the reader understand the operational data and the logic of the screening.

Good options:

- a representative time-series window showing generator speed and load,
- or a figure that makes the two speed clusters visible,
- or a simple operating-data overview that motivates the regime split and the steady-state screening.

This figure should answer:

- what kind of telemetry was available,
- why a regime split made sense,
- why transient filtering was needed.

### Results Figure

Use one clean comparison figure in Results showing:

- OEM SFOC curve,
- telemetry points or a muted swarm,
- representative regime points such as supported bin medians.

The best candidate is the clean combined comparison figure from the latest full combined case:

- `analysis/sfoc_cases/full_combined_all_windows/sfoc_regime_clean_compare.png`

Avoid filling the thesis with the full internal case-tracking figure set.

## Latest Technical Findings Worth Carrying Into The Report

These are the main results from the latest combined telemetry case.

Latest case folder:

- `analysis/sfoc_cases/full_combined_all_windows/`

Main files:

- `sfoc_regime_clean_compare.png`
- `sfoc_regime_overlay.png`
- `sfoc_fit_summary.txt`
- `sfoc_oem_diagnostic.txt`
- `sfoc_regime_breakpoints.csv`

Main findings:

- steady filtered points: `2939`
- `~1800 rpm` supported bins:
  - `40-50%`
  - `50-60%`
  - `60-70%`
  - `70-80%`
- `~1400 rpm` supported bins:
  - `10-20%`
  - `20-30%`
  - `40-50%`
  - `50-60%`

Latest provisional fit lines:

- `~1800 rpm`: `fuel_gph = -4371.0 + 233.075 * power_kw`
- `~1400 rpm`: `fuel_gph = -718.0 + 184.788 * power_kw`

Latest OEM comparison:

- `~1800 rpm` telemetry is above OEM across the supported range,
- `~1400 rpm` telemetry is below OEM in the supported bins,
- the high-speed difference is the most robust and easiest to defend.

Important caution for report writing:

- the low-load low-speed comparison to OEM is not fully apples-to-apples,
- the OEM breakpoint set does not strongly represent the same low-load region,
- therefore the strongest discussion point is the existence of two regimes and the high-speed mismatch, not the exact low-load low-speed delta.

## Recommended Final Thesis Position

This is the most defensible way to use the telemetry work in the report:

- Keep the OEM curve as the generator model in the MILP.
- Present the telemetry work as an operational-data assessment.
- Use it to show that two real operating regimes exist.
- Use it to show that real operation does not fully match the idealized OEM fuel picture.
- Use it to explain why optimized dispatch may differ from observed dispatch.

This gives the telemetry work real value in the thesis without forcing the model to depend on telemetry-derived breakpoints in poorly supported operating regions.

## Continuation Prompt

Use this prompt in the next AI thread:

> Continue from `analysis/report_writing_handoff.md`. We are now working on the thesis report in `C:\Users\bulve\OneDrive\master\report\695e178abaa53b0c7651d409`. Do not edit files yet unless asked. Help me draft a concise Methods subsection called `Operational data assessment for generator efficiency`, with short subsubsections and simple direct prose matching the rest of the report. The section should explain the telemetry-based attempt to construct an SFOC curve for possible use in or comparison with the MILP, the 4000-point extraction limitation, the use of low-resolution scouting to find additional low-speed windows, the load-percentage power proxy, the rolling-window steady-state filtering, the 1600 rpm regime split, and why the work ended as an empirical operating assessment rather than a replacement of the OEM curve. Then help me draft a short Results subsection and a short Discussion subsection in the same style, and suggest which figure to place in Methods and which figure to place in Results.

