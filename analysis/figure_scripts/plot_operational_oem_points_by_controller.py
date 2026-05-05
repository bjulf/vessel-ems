from __future__ import annotations

import argparse
import tomllib
from dataclasses import dataclass
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
ANALYSIS_DIR = SCRIPT_DIR.parent
if str(ANALYSIS_DIR) not in sys.path:
    sys.path.insert(0, str(ANALYSIS_DIR))

from plot_verification_case import REPO_ROOT, active_generator_points, draw_oem_curve


DEFAULT_ROLLING_RUN = (
    REPO_ROOT
    / "runs"
    / "2026-04-30_133906_rolling_horizon_balanced_3day_h16_ma4_c500_p10k_minup8"
)
DEFAULT_RULE_RUN = (
    REPO_ROOT
    / "runs"
    / "2026-04-24_114936_operational_model_soc60_no_terminal_cstart_1000g_rule_based"
)
DEFAULT_OUTPUT_DIR = REPO_ROOT / "analysis" / "thesis_figures" / "results"
DEFAULT_OUTPUT_STEM = "operational_oem_points_by_controller_minup8"

BASE_FONT = 13
LABEL_FONT = 15

CONTROLLER_STYLES = {
    "full": {
        "label": "Full-horizon MILP",
        "color": "#2563EB",
    },
    "rule": {
        "label": "Rule-based",
        "color": "#C2410C",
    },
    "rolling": {
        "label": "Rolling-horizon MILP",
        "color": "#15803D",
    },
}


@dataclass
class ControllerDispatch:
    key: str
    label: str
    color: str
    dispatch: pd.DataFrame
    active: pd.DataFrame
    fuel_kg: float
    starts: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plot active generator operating points on the modeled OEM SFOC curve, "
            "colored by controller for the 3-day operational comparison."
        )
    )
    parser.add_argument(
        "--rolling-run",
        default=str(DEFAULT_ROLLING_RUN),
        help="Rolling-horizon run directory containing dispatch and full-horizon benchmark files.",
    )
    parser.add_argument(
        "--rule-run",
        default=str(DEFAULT_RULE_RUN),
        help="Rule-based run directory for the same operational profile.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory where PNG/PDF outputs are saved.",
    )
    parser.add_argument(
        "--output-stem",
        default=DEFAULT_OUTPUT_STEM,
        help="Filename stem for saved outputs.",
    )
    return parser.parse_args()


def resolve_path(path_arg: str) -> Path:
    path = Path(path_arg)
    return path if path.is_absolute() else (REPO_ROOT / path).resolve()


def load_params(run_dir: Path) -> dict:
    with open(run_dir / "params.toml", "rb") as fh:
        return tomllib.load(fh)


def load_dispatch(path: Path) -> pd.DataFrame:
    dispatch = pd.read_csv(path)
    dispatch["datetime"] = pd.to_datetime(dispatch["datetime"])
    dispatch["generator"] = dispatch["generator"].astype(str)
    return dispatch


def dt_hours_from_params(params: dict) -> float:
    if "battery" in params and "dt" in params["battery"]:
        return float(params["battery"]["dt"])
    return float(params["load_profile"]["dt_minutes"]) / 60.0


def fuel_kg(dispatch: pd.DataFrame, dt_hours: float) -> float:
    return float(dispatch.groupby("timestep")["fuel_gph"].sum().sum() * dt_hours / 1000.0)


def starts(dispatch: pd.DataFrame) -> int:
    return int(dispatch["startup"].sum())


def build_controller_dispatch(
    key: str,
    dispatch_path: Path,
    params: dict,
) -> ControllerDispatch:
    dispatch = load_dispatch(dispatch_path)
    active = active_generator_points(dispatch)
    style = CONTROLLER_STYLES[key]
    return ControllerDispatch(
        key=key,
        label=style["label"],
        color=style["color"],
        dispatch=dispatch,
        active=active,
        fuel_kg=fuel_kg(dispatch, dt_hours_from_params(params)),
        starts=starts(dispatch),
    )


def assert_same_time_grid(cases: list[ControllerDispatch]) -> None:
    reference = cases[0].dispatch.groupby("timestep")[["datetime", "load_kw"]].first()
    for case in cases[1:]:
        current = case.dispatch.groupby("timestep")[["datetime", "load_kw"]].first()
        if not reference.equals(current):
            raise ValueError(
                "Controller dispatch files do not share the same timestep/load grid: "
                f"{cases[0].label} differs from {case.label}"
            )


def plot_controller_points(ax: plt.Axes, case: ControllerDispatch) -> None:
    if case.active.empty:
        return

    ax.scatter(
        case.active["Pg_kw"],
        case.active["sfoc_gkwh"],
        s=44,
        alpha=0.58,
        color=case.color,
        edgecolor="white",
        linewidth=0.45,
        label=f"{case.label} ({case.fuel_kg:.1f} kg, {case.starts} starts)",
        zorder=3,
    )


def add_operational_note(ax: plt.Axes) -> None:
    ax.text(
        0.02,
        0.96,
        "3-day operational comparison; active generator states only",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=BASE_FONT,
        color="#334155",
        bbox={
            "boxstyle": "round,pad=0.25",
            "facecolor": "white",
            "edgecolor": "#94A3B8",
            "linewidth": 1.0,
            "alpha": 0.95,
        },
    )
    ax.text(
        0.02,
        0.04,
        "Point color identifies controller; no operational-profile/module coloring is used",
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=BASE_FONT - 1,
        color="#475569",
    )


def build_figure(cases: list[ControllerDispatch], params: dict, output_dir: Path, output_stem: str) -> list[Path]:
    fig, ax = plt.subplots(figsize=(12.4, 5.1), constrained_layout=True)
    draw_oem_curve(ax, params, annotate_breakpoints=False)

    for case in cases:
        plot_controller_points(ax, case)

    add_operational_note(ax)
    ax.set_ylim(190.0, 198.8)
    ax.set_xlabel("Generator power [kW]", fontsize=LABEL_FONT)
    ax.set_ylabel("SFOC [g/kWh]", fontsize=LABEL_FONT)
    ax.tick_params(axis="both", labelsize=BASE_FONT)
    ax.legend(
        loc="lower right",
        fontsize=BASE_FONT - 2,
        frameon=True,
        borderpad=0.5,
        labelspacing=0.45,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for suffix in ("png", "pdf"):
        path = output_dir / f"{output_stem}.{suffix}"
        fig.savefig(path, dpi=180 if suffix == "png" else None, bbox_inches="tight")
        paths.append(path)
    plt.close(fig)
    return paths


def main() -> None:
    args = parse_args()
    rolling_run = resolve_path(args.rolling_run)
    rule_run = resolve_path(args.rule_run)
    output_dir = resolve_path(args.output_dir)

    rolling_params = load_params(rolling_run)
    rule_params = load_params(rule_run)

    cases = [
        build_controller_dispatch(
            "full",
            rolling_run / "full_horizon_benchmark_dispatch_results.csv",
            rolling_params,
        ),
        build_controller_dispatch("rule", rule_run / "dispatch_results.csv", rule_params),
        build_controller_dispatch("rolling", rolling_run / "dispatch_results.csv", rolling_params),
    ]
    assert_same_time_grid(cases)

    saved_paths = build_figure(cases, rolling_params, output_dir, args.output_stem)

    print("Saved operational OEM points by controller:")
    for path in saved_paths:
        print(f"  {path}")
    for case in cases:
        print(f"{case.label}: fuel {case.fuel_kg:.2f} kg, starts {case.starts}")


if __name__ == "__main__":
    main()
