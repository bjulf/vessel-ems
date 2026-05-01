from __future__ import annotations

import csv
import shutil
import subprocess
import time
import tomllib
from copy import deepcopy
from itertools import product
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from oracle_operational_tuning_screen import write_rolling_config
from sensitivity_common import REPO_ROOT


BASE_CONFIG = REPO_ROOT / "config" / "rolling_horizon_soft_soc_min_up6_operational.toml"
OUTPUT_DIR = (
    REPO_ROOT
    / "analysis"
    / "output"
    / "rolling_horizon"
    / "min_up_confirmatory_baseline_sweep"
)
GENERATED_CONFIG_DIR = OUTPUT_DIR / "generated_configs"
PLOTS_DIR = OUTPUT_DIR / "plots"
TOP_PLOTS_DIR = PLOTS_DIR / "top_contenders"

LOAD_PROFILE = "data/operational_profiles/operational_load_profile_15min_avg.csv"
HORIZON_STEPS = [8, 12, 16]
STARTUP_COSTS = [250.0, 500.0, 1000.0]
SOFT_SOC_PENALTIES = [5000.0, 10000.0]

MIN_UP_STEPS = 6
LOCAL_TIME_LIMIT_S = 30.0
INITIAL_BATTERY_KWH = 564.0
INITIAL_COMMITMENT = [0, 0]
TOP_PLOT_COUNT = 5


SUMMARY_FIELDS = [
    "case_id",
    "horizon_steps",
    "horizon_hours",
    "startup_cost_g_per_start",
    "soft_soc_penalty_g_per_kwh",
    "min_up_time_steps",
    "soft_band_terminal_reserve_enabled",
    "rolling_fuel_kg",
    "fuel_delta_vs_full_pct",
    "fuel_delta_vs_full_kg",
    "full_fuel_kg",
    "rolling_starts",
    "full_starts",
    "starts_delta_vs_full",
    "minimum_soc_pct",
    "maximum_soc_pct",
    "final_soc_pct",
    "full_final_soc_pct",
    "final_soc_delta_pct_points",
    "realized_low_soc_slack_kwh",
    "realized_high_soc_slack_kwh",
    "realized_low_soc_slack_max_kwh",
    "realized_high_soc_slack_max_kwh",
    "local_low_soc_slack_kwh",
    "local_high_soc_slack_kwh",
    "local_low_soc_slack_max_kwh",
    "local_high_soc_slack_max_kwh",
    "run_count",
    "run_lengths_steps",
    "shorter_than_min_up_runs",
    "minimum_length_runs",
    "median_solve_s",
    "p95_solve_s",
    "max_solve_s",
    "nonoptimal_timeout_infeasible_local_solve_count",
    "tail_padded_solves",
    "wall_clock_s",
    "config_path",
    "run_dir",
]


def cases() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for horizon, startup, soft_soc in product(HORIZON_STEPS, STARTUP_COSTS, SOFT_SOC_PENALTIES):
        rows.append(
            {
                "case_id": (
                    f"h{horizon}_startup{startup:.0f}_softsoc{soft_soc:.0f}_minup{MIN_UP_STEPS}"
                ),
                "horizon": horizon,
                "startup": startup,
                "soft_soc": soft_soc,
            }
        )
    return rows


def load_existing_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def build_config(base: dict, case: dict[str, object]) -> dict:
    config = deepcopy(base)
    case_id = str(case["case_id"])
    horizon = int(case["horizon"])
    startup = float(case["startup"])
    soft_soc = float(case["soft_soc"])

    config["run"]["label"] = f"rolling_horizon_{case_id}"
    config["run"]["description"] = (
        "Operational 15-minute average-load forecast rolling-horizon MILP "
        f"confirmatory baseline sweep: H={horizon}, startup={startup:g} g/start, "
        f"mean soft-SOC penalty={soft_soc:g} g/kWh, 6-step minimum up-time"
    )
    config["run"]["show_solver_log"] = False
    config["load_profile"]["path"] = LOAD_PROFILE
    config["scheduling"]["dt_minutes"] = 15
    config["initial_conditions"]["battery_energy_kwh"] = INITIAL_BATTERY_KWH
    config["initial_conditions"]["generator_commitment"] = list(INITIAL_COMMITMENT)

    rolling = config["rolling_horizon"]
    rolling["horizon_steps"] = horizon
    rolling["forecast_method"] = "moving_average"
    rolling["moving_average_window_steps"] = 4
    rolling["soc_strategy"] = "soft_band"
    rolling["tail_forecast_policy"] = "repeat_final_load"
    rolling["min_up_time_steps"] = MIN_UP_STEPS
    rolling["soft_band_terminal_reserve_enabled"] = False
    rolling.pop("terminal_soc_target", None)
    rolling.pop("terminal_slack_penalty_g_per_kwh", None)

    solver = config.setdefault("solver", {})
    solver["rolling_local_time_limit_sec"] = LOCAL_TIME_LIMIT_S
    solver["progress_log_enabled"] = False
    solver["progress_log_every_steps"] = 25
    solver["slow_solve_log_threshold_sec"] = 999.0

    soft = config.setdefault("soft_soc", {})
    soft["preferred_soc_min"] = 0.20
    soft["preferred_soc_max"] = 0.80
    soft["soc_min_penalty_g_per_kwh"] = soft_soc
    soft["soc_max_penalty_g_per_kwh"] = soft_soc
    soft["soft_soc_penalty_scaling"] = "mean"

    for generator in config["generators"]:
        generator["startup_cost"] = startup

    return config


def verify_generated_config(path: Path, case: dict[str, object]) -> None:
    with open(path, "rb") as fh:
        config = tomllib.load(fh)

    rolling = config["rolling_horizon"]
    solver = config["solver"]
    soft = config["soft_soc"]
    initial = config["initial_conditions"]

    checks = {
        "load profile": config["load_profile"]["path"] == LOAD_PROFILE,
        "horizon": rolling["horizon_steps"] == int(case["horizon"]),
        "moving-average forecast": rolling["forecast_method"] == "moving_average",
        "MA4": rolling["moving_average_window_steps"] == 4,
        "soft band": rolling["soc_strategy"] == "soft_band",
        "min up": rolling["min_up_time_steps"] == MIN_UP_STEPS,
        "soft terminal reserve disabled": rolling["soft_band_terminal_reserve_enabled"] is False,
        "local time limit": abs(float(solver["rolling_local_time_limit_sec"]) - LOCAL_TIME_LIMIT_S) < 1e-9,
        "initial energy": abs(float(initial["battery_energy_kwh"]) - INITIAL_BATTERY_KWH) < 1e-9,
        "initial commitment": list(initial["generator_commitment"]) == INITIAL_COMMITMENT,
        "preferred low": abs(float(soft["preferred_soc_min"]) - 0.20) < 1e-12,
        "preferred high": abs(float(soft["preferred_soc_max"]) - 0.80) < 1e-12,
        "mean scaling": soft["soft_soc_penalty_scaling"] == "mean",
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError(f"{path} failed generated-config verification: {', '.join(failed)}")


def run_case(config_path: Path) -> tuple[dict, Path, float]:
    started_at = time.perf_counter()
    completed = subprocess.run(
        ["julia", "--project=.", "main_rolling_horizon.jl", str(config_path.relative_to(REPO_ROOT))],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    wall_clock_s = time.perf_counter() - started_at
    if completed.returncode != 0:
        raise RuntimeError(
            f"Case failed: {config_path}\nSTDOUT:\n{completed.stdout[-5000:]}\nSTDERR:\n{completed.stderr[-5000:]}"
        )
    run_dir = Path((REPO_ROOT / ".current_run").read_text(encoding="utf-8").strip())
    with open(run_dir / "params.toml", "rb") as fh:
        metadata = tomllib.load(fh)
    return metadata, run_dir, wall_clock_s


def generator_run_lengths(run_dir: Path) -> list[int]:
    by_generator: dict[str, list[tuple[int, int]]] = {}
    with open(run_dir / "dispatch_results.csv", newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            by_generator.setdefault(row["generator"], []).append(
                (int(row["timestep"]), 1 if float(row["u"]) > 0.5 else 0)
            )

    lengths: list[int] = []
    for rows in by_generator.values():
        run_length = 0
        for _, is_on in sorted(rows):
            if is_on:
                run_length += 1
            elif run_length:
                lengths.append(run_length)
                run_length = 0
        if run_length:
            lengths.append(run_length)
    return lengths


def summary_row(
    case: dict[str, object],
    config_path: Path,
    metadata: dict,
    run_dir: Path,
    wall_clock_s: float,
) -> dict[str, object]:
    rolling = metadata["kpis"]["rolling_horizon"]
    full = metadata["kpis"]["full_horizon_benchmark"]
    comparison = metadata["kpis"]["comparison"]
    min_up = int(metadata["rolling_horizon"]["min_up_time_steps"])
    lengths = generator_run_lengths(run_dir)

    return {
        "case_id": case["case_id"],
        "horizon_steps": int(case["horizon"]),
        "horizon_hours": int(case["horizon"]) * float(metadata["rolling_horizon"]["dt_h"]),
        "startup_cost_g_per_start": float(case["startup"]),
        "soft_soc_penalty_g_per_kwh": float(case["soft_soc"]),
        "min_up_time_steps": min_up,
        "soft_band_terminal_reserve_enabled": metadata["rolling_horizon"][
            "soft_band_terminal_reserve_enabled"
        ],
        "rolling_fuel_kg": rolling["total_fuel_kg"],
        "fuel_delta_vs_full_pct": comparison["fuel_delta_pct"],
        "fuel_delta_vs_full_kg": comparison["fuel_delta_g"] / 1000.0,
        "full_fuel_kg": full["total_fuel_kg"],
        "rolling_starts": rolling["generator_starts"],
        "full_starts": full["generator_starts"],
        "starts_delta_vs_full": comparison["generator_starts_delta"],
        "minimum_soc_pct": rolling["minimum_soc_pct"],
        "maximum_soc_pct": rolling["maximum_soc_pct"],
        "final_soc_pct": rolling["final_soc_pct"],
        "full_final_soc_pct": full["final_soc_pct"],
        "final_soc_delta_pct_points": comparison["final_soc_delta_pct_points"],
        "realized_low_soc_slack_kwh": rolling["realized_total_soc_min_slack_kwh"],
        "realized_high_soc_slack_kwh": rolling["realized_total_soc_max_slack_kwh"],
        "realized_low_soc_slack_max_kwh": rolling["realized_maximum_soc_min_slack_kwh"],
        "realized_high_soc_slack_max_kwh": rolling["realized_maximum_soc_max_slack_kwh"],
        "local_low_soc_slack_kwh": rolling["local_total_soc_min_slack_kwh"],
        "local_high_soc_slack_kwh": rolling["local_total_soc_max_slack_kwh"],
        "local_low_soc_slack_max_kwh": rolling["local_maximum_soc_min_slack_kwh"],
        "local_high_soc_slack_max_kwh": rolling["local_maximum_soc_max_slack_kwh"],
        "run_count": len(lengths),
        "run_lengths_steps": " ".join(str(value) for value in lengths),
        "shorter_than_min_up_runs": sum(value < min_up for value in lengths),
        "minimum_length_runs": sum(value == min_up for value in lengths),
        "median_solve_s": rolling["median_solve_time_s"],
        "p95_solve_s": rolling["p95_solve_time_s"],
        "max_solve_s": rolling["maximum_solve_time_s"],
        "nonoptimal_timeout_infeasible_local_solve_count": rolling[
            "nonoptimal_timeout_or_infeasible_solves"
        ],
        "tail_padded_solves": metadata["rolling_horizon"]["tail_forecast_padded_solves"],
        "wall_clock_s": wall_clock_s,
        "config_path": str(config_path),
        "run_dir": str(run_dir),
    }


def as_float(row: dict[str, object], key: str) -> float:
    return float(row[key])


def as_int(row: dict[str, object], key: str) -> int:
    return int(float(row[key]))


def is_valid(row: dict[str, object]) -> bool:
    return (
        as_int(row, "nonoptimal_timeout_infeasible_local_solve_count") == 0
        and as_float(row, "realized_low_soc_slack_kwh") <= 1e-6
        and as_float(row, "realized_high_soc_slack_kwh") <= 1e-6
        and as_float(row, "minimum_soc_pct") >= 20.0 - 1e-6
        and as_int(row, "shorter_than_min_up_runs") == 0
    )


def ranking_key(row: dict[str, object]) -> tuple[float, int, int, float, float]:
    # Commitment cleanliness is prioritized ahead of very small fuel differences.
    return (
        as_int(row, "rolling_starts"),
        as_int(row, "minimum_length_runs"),
        abs(as_float(row, "final_soc_pct") - 30.0),
        as_float(row, "fuel_delta_vs_full_pct"),
        as_float(row, "p95_solve_s"),
    )


def fuel_key(row: dict[str, object]) -> tuple[float, int, float]:
    return (
        as_float(row, "fuel_delta_vs_full_pct"),
        as_int(row, "rolling_starts"),
        as_float(row, "final_soc_pct"),
    )


def contender_rows(rows: list[dict[str, object]], count: int = TOP_PLOT_COUNT) -> list[dict[str, object]]:
    valid = [row for row in rows if is_valid(row)]
    if not valid:
        return sorted(rows, key=fuel_key)[:count]
    selected: list[dict[str, object]] = []
    for row in sorted(valid, key=ranking_key):
        selected.append(row)
        if len(selected) >= count:
            break
    for row in sorted(valid, key=fuel_key):
        if row not in selected:
            selected.append(row)
        if len(selected) >= count:
            break
    return selected[:count]


def write_appendix_plot(summary_path: Path) -> tuple[Path, Path]:
    df = pd.read_csv(summary_path)
    df = df.sort_values(
        ["horizon_steps", "startup_cost_g_per_start", "soft_soc_penalty_g_per_kwh"]
    ).reset_index(drop=True)
    labels = [
        f"H{int(row.horizon_steps)} C{int(row.startup_cost_g_per_start)} P{int(row.soft_soc_penalty_g_per_kwh / 1000)}k"
        for row in df.itertuples()
    ]
    colors = df["horizon_steps"].map({8: "#2563EB", 12: "#059669", 16: "#B45309"})

    plt.rcParams.update(
        {
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.labelsize": 11,
            "xtick.labelsize": 8,
            "ytick.labelsize": 10,
        }
    )
    fig, axes = plt.subplots(2, 1, figsize=(12.5, 7.5), sharex=True, constrained_layout=True)
    x = range(len(df))

    axes[0].bar(x, df["fuel_delta_vs_full_pct"], color=colors, alpha=0.86)
    axes[0].set_ylabel("Fuel penalty [%]")
    axes[0].set_title("Fuel Penalty vs Offline Full-Horizon MILP")
    axes[0].grid(axis="y", alpha=0.25)

    axes[1].bar(x, df["rolling_starts"], color=colors, alpha=0.86)
    axes[1].set_ylabel("Generator starts")
    axes[1].set_title("Commitment Activity")
    axes[1].grid(axis="y", alpha=0.25)
    axes[1].set_xticks(list(x), labels, rotation=45, ha="right")

    for ax in axes:
        ax.spines[["top", "right"]].set_visible(False)

    handles = [
        plt.Rectangle((0, 0), 1, 1, color=color, alpha=0.86, label=f"H={horizon}")
        for horizon, color in [(8, "#2563EB"), (12, "#059669"), (16, "#B45309")]
    ]
    axes[0].legend(handles=handles, loc="upper left", ncol=3, frameon=True)

    png = PLOTS_DIR / "confirmatory_sweep_appendix_fuel_starts.png"
    pdf = PLOTS_DIR / "confirmatory_sweep_appendix_fuel_starts.pdf"
    fig.savefig(png, dpi=220)
    fig.savefig(pdf)
    plt.close(fig)
    return png, pdf


def run_plot_script(script_name: str, run_dir: Path) -> Path:
    completed = subprocess.run(
        ["python", f"analysis/{script_name}", str(run_dir)],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"Plot script {script_name} failed for {run_dir}\n"
            f"STDOUT:\n{completed.stdout[-3000:]}\nSTDERR:\n{completed.stderr[-3000:]}"
        )
    for line in reversed(completed.stdout.splitlines()):
        if line.startswith("Saved "):
            return Path(line.replace("Saved ", "", 1).strip())
    raise RuntimeError(f"Could not parse output path from {script_name}: {completed.stdout}")


def generate_top_contender_plots(rows: list[dict[str, object]]) -> list[str]:
    TOP_PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for rank, row in enumerate(contender_rows(rows), start=1):
        run_dir = Path(str(row["run_dir"]))
        case_id = str(row["case_id"])
        dispatch_panel = run_plot_script("plot_rolling_horizon_run_panel.py", run_dir)
        comparison_panel = run_plot_script("plot_rolling_full_horizon_comparison.py", run_dir)

        for source, suffix in [
            (dispatch_panel, "dispatch_panel"),
            (comparison_panel, "rolling_vs_full"),
        ]:
            target = TOP_PLOTS_DIR / f"rank{rank:02d}_{case_id}_{suffix}{source.suffix}"
            shutil.copy2(source, target)
            copied.append(str(target))
    return copied


def format_rank_row(rank: int, row: dict[str, object]) -> str:
    validity = "clean" if is_valid(row) else "excluded"
    return (
        f"| {rank} | `{row['case_id']}` | {validity} | {as_int(row, 'horizon_steps')} | "
        f"{as_float(row, 'startup_cost_g_per_start'):.0f} | "
        f"{as_float(row, 'soft_soc_penalty_g_per_kwh'):.0f} | "
        f"{as_float(row, 'rolling_fuel_kg'):.2f} | "
        f"{as_float(row, 'fuel_delta_vs_full_pct'):.2f} | "
        f"{as_int(row, 'rolling_starts')} | {as_float(row, 'minimum_soc_pct'):.2f} | "
        f"{as_float(row, 'final_soc_pct'):.2f} | {row['run_lengths_steps']} | "
        f"{as_float(row, 'p95_solve_s'):.3f} | "
        f"{as_int(row, 'nonoptimal_timeout_infeasible_local_solve_count')} |"
    )


def write_markdown(rows: list[dict[str, object]], copied_plots: list[str]) -> None:
    valid = [row for row in rows if is_valid(row)]
    excluded = [row for row in rows if not is_valid(row)]
    ranked = sorted(valid, key=ranking_key)
    fuel_ranked = sorted(valid, key=fuel_key)
    recommendation = ranked[0] if ranked else sorted(rows, key=fuel_key)[0]
    best_fuel = fuel_ranked[0] if fuel_ranked else recommendation

    lines = [
        "# Rolling-Horizon Confirmatory Baseline Sweep",
        "",
        "Fixed setup: operational 15-minute average load profile, MA4 moving-average forecast, soft SOC band 20-80%, mean-normalized SOC penalty, 6-step minimum up-time, no soft-band terminal reserve, 30 s local solve limit, initial SOC 60% / 564 kWh, initial commitment [0, 0].",
        "",
        "Offline full-horizon MILP benchmarks are solved per generated config and have no terminal SOC constraint. Final SOC differences therefore matter when interpreting the rolling fuel penalty.",
        "",
        "## Recommendation",
        "",
    ]
    if ranked:
        lines.extend(
            [
                f"Use `{recommendation['case_id']}` for the clean final baseline rerun.",
                "",
                (
                    f"This case uses H={as_int(recommendation, 'horizon_steps')} "
                    f"({as_float(recommendation, 'horizon_hours'):.1f} h), "
                    f"startup cost {as_float(recommendation, 'startup_cost_g_per_start'):.0f} g/start, "
                    f"soft SOC penalty {as_float(recommendation, 'soft_soc_penalty_g_per_kwh'):.0f} g/kWh, "
                    f"and min_up_time_steps={as_int(recommendation, 'min_up_time_steps')}."
                ),
                "",
                (
                    f"It gives {as_float(recommendation, 'rolling_fuel_kg'):.2f} kg fuel "
                    f"({as_float(recommendation, 'fuel_delta_vs_full_pct'):.2f}% vs full horizon), "
                    f"{as_int(recommendation, 'rolling_starts')} starts, minimum SOC "
                    f"{as_float(recommendation, 'minimum_soc_pct'):.2f}%, final SOC "
                    f"{as_float(recommendation, 'final_soc_pct'):.2f}% "
                    f"({as_float(recommendation, 'final_soc_delta_pct_points'):+.2f} pp vs full horizon), "
                    f"and no nonoptimal/time-limited/infeasible local solves."
                ),
                "",
            ]
        )
        if best_fuel["case_id"] != recommendation["case_id"]:
            lines.extend(
                [
                    (
                        f"The lowest-fuel clean case is `{best_fuel['case_id']}` at "
                        f"{as_float(best_fuel, 'fuel_delta_vs_full_pct'):.2f}% fuel penalty and "
                        f"{as_int(best_fuel, 'rolling_starts')} starts. It is not the top recommendation "
                        "under the commitment-cleanliness preference."
                    ),
                    "",
                ]
            )
    else:
        lines.extend(
            [
                "No case passed the clean baseline filters. Do not freeze this controller setting without another targeted rerun.",
                "",
            ]
        )

    lines.extend(
        [
            "## Ranked Clean Contenders",
            "",
            "| Rank | Case | Status | H | Startup | SOC penalty | Fuel kg | Delta % | Starts | Min SOC % | Final SOC % | Run lengths | P95 solve s | Nonopt/time/infeas |",
            "| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |",
        ]
    )
    for rank, row in enumerate(ranked, start=1):
        lines.append(format_rank_row(rank, row))

    lines.extend(
        [
            "",
            "## Fuel Ranking",
            "",
            "| Rank | Case | Status | H | Startup | SOC penalty | Fuel kg | Delta % | Starts | Min SOC % | Final SOC % | Run lengths | P95 solve s | Nonopt/time/infeas |",
            "| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |",
        ]
    )
    for rank, row in enumerate(sorted(rows, key=fuel_key), start=1):
        lines.append(format_rank_row(rank, row))

    if excluded:
        lines.extend(["", "## Exclusions", ""])
        for row in sorted(excluded, key=fuel_key):
            reasons: list[str] = []
            if as_int(row, "nonoptimal_timeout_infeasible_local_solve_count") > 0:
                reasons.append(
                    f"{as_int(row, 'nonoptimal_timeout_infeasible_local_solve_count')} nonoptimal/time-limited/infeasible local solve(s)"
                )
            if as_float(row, "realized_low_soc_slack_kwh") > 1e-6:
                reasons.append(f"realized low SOC slack {as_float(row, 'realized_low_soc_slack_kwh'):.2f} kWh")
            if as_float(row, "realized_high_soc_slack_kwh") > 1e-6:
                reasons.append(f"realized high SOC slack {as_float(row, 'realized_high_soc_slack_kwh'):.2f} kWh")
            if as_int(row, "shorter_than_min_up_runs") > 0:
                reasons.append(f"{as_int(row, 'shorter_than_min_up_runs')} run(s) shorter than min-up")
            lines.append(f"- `{row['case_id']}`: {', '.join(reasons)}.")

    lines.extend(["", "## Generated Plots", ""])
    lines.append("- `plots/confirmatory_sweep_appendix_fuel_starts.png`: simple appendix fuel/start plot.")
    lines.append("- `plots/top_contenders/`: copied dispatch-panel and rolling-vs-full plots for the top contenders.")
    for path in copied_plots:
        lines.append(f"- `{Path(path).relative_to(OUTPUT_DIR).as_posix()}`")
    lines.append("")

    (OUTPUT_DIR / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def normalize_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return sorted(
        rows,
        key=lambda row: (
            as_int(row, "horizon_steps"),
            as_float(row, "startup_cost_g_per_start"),
            as_float(row, "soft_soc_penalty_g_per_kwh"),
        ),
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    GENERATED_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    with open(BASE_CONFIG, "rb") as fh:
        base_config = tomllib.load(fh)

    summary_path = OUTPUT_DIR / "summary.csv"
    rows: list[dict[str, object]] = [dict(row) for row in load_existing_rows(summary_path)]
    completed_cases = {str(row["case_id"]) for row in rows}

    for case in cases():
        case_id = str(case["case_id"])
        if case_id in completed_cases:
            print(f"Skipping existing {case_id}", flush=True)
            continue

        config = build_config(base_config, case)
        config_path = GENERATED_CONFIG_DIR / f"{case_id}.toml"
        write_rolling_config(config, config_path)
        verify_generated_config(config_path, case)

        print(f"Running {case_id}", flush=True)
        metadata, run_dir, wall_clock_s = run_case(config_path)
        row = summary_row(case, config_path, metadata, run_dir, wall_clock_s)
        rows.append(row)
        rows = normalize_rows(rows)
        write_csv(summary_path, rows)
        print(
            f"  fuel={as_float(row, 'rolling_fuel_kg'):.2f} kg, "
            f"delta={as_float(row, 'fuel_delta_vs_full_pct'):.2f}%, "
            f"starts={as_int(row, 'rolling_starts')}, "
            f"min SOC={as_float(row, 'minimum_soc_pct'):.2f}%, "
            f"final SOC={as_float(row, 'final_soc_pct'):.2f}%, "
            f"nonopt={as_int(row, 'nonoptimal_timeout_infeasible_local_solve_count')}, "
            f"run={run_dir}",
            flush=True,
        )

    rows = normalize_rows(rows)
    write_csv(summary_path, rows)
    appendix_png, appendix_pdf = write_appendix_plot(summary_path)
    copied_plots = generate_top_contender_plots(rows)
    write_markdown(rows, copied_plots)

    print(f"Saved {summary_path}", flush=True)
    print(f"Saved {OUTPUT_DIR / 'summary.md'}", flush=True)
    print(f"Saved {appendix_png}", flush=True)
    print(f"Saved {appendix_pdf}", flush=True)
    print(f"Saved top-contender plots under {TOP_PLOTS_DIR}", flush=True)


if __name__ == "__main__":
    main()
