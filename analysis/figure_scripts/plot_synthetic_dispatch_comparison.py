from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
ANALYSIS_DIR = SCRIPT_DIR.parent
if str(ANALYSIS_DIR) not in sys.path:
    sys.path.insert(0, str(ANALYSIS_DIR))

from plot_verification_case import (
    BATTERY_CHARGE,
    BATTERY_DISCHARGE,
    GEN_COLORS,
    MODULE_COLORS,
    REPO_ROOT,
    add_module_background,
    format_hour_axis,
    load_dispatch,
    load_params,
    load_profile,
    merge_dispatch_labels,
    merge_profile_labels,
    module_spans,
)


OUTPUT_DIR = REPO_ROOT / "analysis" / "output" / "verification"
DEFAULT_MILP_SUFFIX = "baseline_model_no_terminal_soc"
DEFAULT_RULE_SUFFIX = "baseline_model_rule_based"

FONT_SIZE = 15
LABEL_SIZE = 17
LEGEND_SIZE = 14
DISPATCH_LINE_WIDTH = 2.2
LOAD_LINE_WIDTH = 2.6
SOC_LINE_WIDTH = 1.9
GRID_ALPHA = 0.18
PHASE_ALPHA = 0.07
LOAD_COLOR = "#111111"
SOC_COLOR = "#7A728F"
SOC_AXIS_COLOR = "#A8A1B9"
SOC_BOUND_COLOR = "#B8B1C7"
NEUTRAL_EDGE = "#CBD5E1"
TITLE_COLOR = "#0F172A"
NEW_OUTPUT_STEM = "synthetic_dispatch_comparison_small_multiples_final"

METHOD_STYLES = {
    "milp": {
        "label": "MILP",
        "accent": "#1D4ED8",
    },
    "rule": {
        "label": "Rule-based",
        "accent": "#C2410C",
    },
    "rolling": {
        "label": "Rolling-horizon MILP",
        "accent": "#1B5E20",
    },
}


@dataclass
class RunBundle:
    key: str
    source_dir: Path
    profile_path: Path
    params: dict
    dispatch: pd.DataFrame
    wide: pd.DataFrame
    total_fuel_kg: float
    total_starts: int
    terminal_soc_pct: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create thesis-ready synthetic dispatch comparison figures using a "
            "shared phase strip and repeated per-algorithm dispatch blocks."
        )
    )
    parser.add_argument(
        "--milp-run",
        help=(
            "Run directory to use for the no-terminal MILP case. Defaults to the "
            f"latest run whose directory name ends with '{DEFAULT_MILP_SUFFIX}'."
        ),
    )
    parser.add_argument(
        "--milp-data-dir",
        help=(
            "Directory containing copied MILP inputs (`params.toml`, "
            "`dispatch_results.csv`, and optionally `load_profile.csv`). "
            "If set, this is used instead of `--milp-run`."
        ),
    )
    parser.add_argument(
        "--rule-run",
        help=(
            "Run directory to use for the rule-based case. Defaults to the latest "
            f"run whose directory name ends with '{DEFAULT_RULE_SUFFIX}'."
        ),
    )
    parser.add_argument(
        "--rule-data-dir",
        help=(
            "Directory containing copied rule-based inputs (`params.toml`, "
            "`dispatch_results.csv`, and optionally `load_profile.csv`). "
            "If set, this is used instead of `--rule-run`."
        ),
    )
    parser.add_argument(
        "--rolling-run",
        help=(
            "Optional run directory for a future rolling-horizon MILP comparison. "
            "If omitted, the figure is built for two algorithms."
        ),
    )
    parser.add_argument(
        "--rolling-data-dir",
        help=(
            "Optional directory containing copied rolling-horizon inputs. "
            "If set, this is used instead of `--rolling-run`."
        ),
    )
    parser.add_argument(
        "--output-dir",
        help="Directory for figure outputs. Defaults to analysis/output/verification.",
    )
    parser.add_argument(
        "--output-stem",
        default=NEW_OUTPUT_STEM,
        help=f"Filename stem for saved outputs. Defaults to '{NEW_OUTPUT_STEM}'.",
    )
    parser.add_argument(
        "--power-y-min",
        type=float,
        help=(
            "Optional fixed lower power-axis bound in kW. "
            "Use together with --power-y-max to match another comparison figure."
        ),
    )
    parser.add_argument(
        "--power-y-max",
        type=float,
        help=(
            "Optional fixed upper power-axis bound in kW. "
            "Use together with --power-y-min to match another comparison figure."
        ),
    )
    parser.add_argument(
        "--soc-power-ref-kw",
        type=float,
        default=500.0,
        help=(
            "Power magnitude used to align the SOC guide lines. "
            "Defaults to 500, meaning -500/0/500 kW align with 20/50/80 percent SOC."
        ),
    )
    return parser.parse_args()


def resolve_run_dir(explicit: str | None, suffix: str) -> Path:
    if explicit:
        path = Path(explicit)
        return path if path.is_absolute() else (REPO_ROOT / path).resolve()

    matches = sorted(
        [
            path
            for path in (REPO_ROOT / "runs").iterdir()
            if path.is_dir() and path.name.endswith(suffix)
        ],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not matches:
        raise FileNotFoundError(f"No run directory found ending with '{suffix}'")
    return matches[0]


def resolve_source_dir(data_dir: str | None, run_dir: str | None, suffix: str) -> Path:
    if data_dir:
        path = Path(data_dir)
        return path if path.is_absolute() else (REPO_ROOT / path).resolve()
    return resolve_run_dir(run_dir, suffix)


def resolve_output_dir(explicit: str | None) -> Path:
    if explicit:
        path = Path(explicit)
        return path if path.is_absolute() else (REPO_ROOT / path).resolve()
    return OUTPUT_DIR


def resolve_profile_path(source_dir: Path, params: dict) -> Path:
    copied_profile = source_dir / "load_profile.csv"
    if copied_profile.is_file():
        return copied_profile

    profile_path = Path(params["load_profile"]["source_file"])
    return profile_path if profile_path.is_absolute() else (REPO_ROOT / profile_path).resolve()


def validated_load_bundle(source_dir: Path) -> tuple[dict, Path, pd.DataFrame, pd.DataFrame]:
    params = load_params(source_dir)
    dispatch, wide = load_dispatch(source_dir)
    profile_path = resolve_profile_path(source_dir, params)
    profile = load_profile(profile_path)
    dispatch = merge_dispatch_labels(dispatch, profile)
    wide = merge_profile_labels(wide, profile)
    return params, profile_path, dispatch, wide


def compute_total_fuel_kg(dispatch: pd.DataFrame, dt_hours: float) -> float:
    fuel_by_step = dispatch.groupby("timestep")["fuel_gph"].sum()
    return float(fuel_by_step.sum() * dt_hours / 1000.0)


def load_run_bundle(key: str, source_dir: Path) -> RunBundle:
    params, profile_path, dispatch, wide = validated_load_bundle(source_dir)
    dt_hours = float(params["battery"]["dt"])
    return RunBundle(
        key=key,
        source_dir=source_dir,
        profile_path=profile_path,
        params=params,
        dispatch=dispatch,
        wide=wide,
        total_fuel_kg=compute_total_fuel_kg(dispatch, dt_hours),
        total_starts=int(dispatch["startup"].sum()),
        terminal_soc_pct=float(wide["soc_pct"].iloc[-1]),
    )


def style_for(bundle: RunBundle) -> dict[str, str]:
    return METHOD_STYLES[bundle.key]


def panel_tag_for(bundle: RunBundle) -> str:
    return {
        "milp": "(A)",
        "rule": "(B)",
        "rolling": "(C)",
    }.get(bundle.key, "?")


def assert_compatible_runs(bundles: list[RunBundle]) -> None:
    reference = bundles[0]
    ref_times = reference.wide["datetime"]
    ref_load = reference.wide["load_kw"]

    for bundle in bundles[1:]:
        if len(ref_load) != len(bundle.wide["load_kw"]) or not ref_load.equals(bundle.wide["load_kw"]):
            raise ValueError(
                "Runs use different load profiles and should not be plotted together:\n"
                f"- {reference.source_dir}: {reference.profile_path}\n"
                f"- {bundle.source_dir}: {bundle.profile_path}"
            )
        times = bundle.wide["datetime"]
        if len(ref_times) != len(times) or not ref_times.equals(times):
            raise ValueError("Runs do not share the same timestep grid.")


def nice_upper_limit(value: float, step: float) -> float:
    if value <= 0:
        return step
    return step * int((value + step - 1e-12) // step + 1)


def dispatch_limits(bundles: list[RunBundle]) -> tuple[float, float]:
    upper = max(
        max(float(bundle.wide["load_kw"].max()), float(bundle.wide["total_gen_kw"].max()), float(bundle.wide["P_dis_kw"].max()))
        for bundle in bundles
    )
    lower = max(float(bundle.wide["P_ch_kw"].max()) for bundle in bundles)
    return -nice_upper_limit(lower, 100.0), nice_upper_limit(upper, 100.0)


def resolve_dispatch_limits(
    bundles: list[RunBundle],
    explicit_min: float | None,
    explicit_max: float | None,
) -> tuple[float, float]:
    if explicit_min is None and explicit_max is None:
        return dispatch_limits(bundles)
    if explicit_min is None or explicit_max is None:
        raise ValueError("Pass both --power-y-min and --power-y-max together.")
    if explicit_min >= explicit_max:
        raise ValueError("--power-y-min must be less than --power-y-max.")
    return explicit_min, explicit_max


def add_common_axis_style(ax: plt.Axes) -> None:
    ax.grid(axis="y", alpha=GRID_ALPHA, linewidth=0.8)
    ax.tick_params(axis="both", labelsize=FONT_SIZE)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_linewidth(0.9)
    ax.spines["bottom"].set_linewidth(0.9)


def add_phase_strip(ax: plt.Axes, wide: pd.DataFrame) -> None:
    times = wide["datetime"].reset_index(drop=True)
    if times.empty:
        return

    dt = times.iloc[1] - times.iloc[0] if len(times) > 1 else pd.Timedelta(minutes=15)
    ax.set_ylim(0, 1)
    ax.set_yticks([])
    ax.tick_params(axis="x", which="both", bottom=False, labelbottom=False)
    ax.spines["left"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["top"].set_visible(False)
    ax.spines["bottom"].set_color(NEUTRAL_EDGE)

    for start, end, module, _label in module_spans(wide):
        color = MODULE_COLORS.get(module, NEUTRAL_EDGE)
        x0 = times.iloc[start]
        x1 = times.iloc[end] + dt
        ax.axvspan(x0, x1, color=color, alpha=0.18, linewidth=0)


def dispatch_legend_handles() -> list[object]:
    return [
        Line2D([0], [0], color=LOAD_COLOR, lw=LOAD_LINE_WIDTH, label="Load"),
        Line2D([0], [0], color=GEN_COLORS["1"], lw=DISPATCH_LINE_WIDTH, label="Gen 1"),
        Line2D([0], [0], color=GEN_COLORS["2"], lw=DISPATCH_LINE_WIDTH, label="Gen 2"),
        Patch(facecolor=BATTERY_DISCHARGE, alpha=0.35, edgecolor="none", label="Battery discharge"),
        Patch(facecolor=BATTERY_CHARGE, alpha=0.35, edgecolor="none", label="Battery charge"),
        Line2D(
            [0],
            [0],
            marker="^",
            markersize=7,
            color="none",
            markerfacecolor="#64748B",
            markeredgecolor="white",
            label="Startup",
        ),
        Line2D([0], [0], color=SOC_COLOR, lw=SOC_LINE_WIDTH, label="SOC"),
        Line2D([0], [0], color=SOC_BOUND_COLOR, lw=1.4, linestyle="--", label="SOC bounds"),
    ]


def add_algorithm_title(ax: plt.Axes, bundle: RunBundle) -> None:
    ax.text(
        0.0,
        1.02,
        panel_tag_for(bundle),
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=LABEL_SIZE - 1,
        fontweight="semibold",
        color="#111111",
    )


def power_to_soc(power_kw: float, soc_power_ref_kw: float) -> float:
    return 50.0 + 30.0 * power_kw / soc_power_ref_kw


def add_soc_overlay(
    ax: plt.Axes,
    bundle: RunBundle,
    y_limits: tuple[float, float],
    show_right_label: bool,
    soc_power_ref_kw: float,
) -> plt.Axes:
    wide = bundle.wide
    times = wide["datetime"]
    soc = wide["soc_pct"]

    soc_ax = ax.twinx()
    soc_ax.plot(times, soc, color=SOC_COLOR, linewidth=SOC_LINE_WIDTH, alpha=0.92, zorder=6)
    soc_ax.axhline(20.0, color=SOC_BOUND_COLOR, linestyle="--", linewidth=1.0, alpha=0.7, zorder=5)
    soc_ax.axhline(80.0, color=SOC_BOUND_COLOR, linestyle="--", linewidth=1.0, alpha=0.7, zorder=5)

    soc_ax.set_ylim(power_to_soc(y_limits[0], soc_power_ref_kw), power_to_soc(y_limits[1], soc_power_ref_kw))
    soc_ax.set_yticks([20, 50, 80])
    soc_ax.tick_params(axis="y", labelsize=FONT_SIZE - 2, colors=SOC_AXIS_COLOR)
    soc_ax.spines["top"].set_visible(False)
    soc_ax.spines["left"].set_visible(False)
    soc_ax.spines["right"].set_color(SOC_AXIS_COLOR)
    soc_ax.spines["right"].set_linewidth(0.9)
    if show_right_label:
        soc_ax.set_ylabel("SOC [%]", fontsize=LABEL_SIZE - 2, color=SOC_AXIS_COLOR, rotation=270, labelpad=16)

    return soc_ax


def plot_dispatch_panel(
    ax: plt.Axes,
    bundle: RunBundle,
    y_limits: tuple[float, float],
    show_right_label: bool,
    soc_power_ref_kw: float,
) -> plt.Axes:
    wide = bundle.wide
    dispatch = bundle.dispatch
    times = wide["datetime"]

    add_module_background(ax, wide, alpha=PHASE_ALPHA)
    add_common_axis_style(ax)

    ax.step(times, wide["load_kw"], where="post", color=LOAD_COLOR, linewidth=LOAD_LINE_WIDTH, zorder=5)

    gen_pivot = dispatch.pivot(index="timestep", columns="generator", values="Pg_kw")
    for generator in sorted(gen_pivot.columns, key=int):
        series = gen_pivot[generator].reindex(wide["timestep"], fill_value=0.0)
        is_flat_zero = float(series.abs().max()) <= 1e-9
        ax.step(
            times,
            series.to_numpy(),
            where="post",
            color=GEN_COLORS.get(generator, "#334155"),
            linewidth=1.6 if is_flat_zero else DISPATCH_LINE_WIDTH,
            alpha=0.45 if is_flat_zero else 0.95,
            zorder=3 if is_flat_zero else 4,
        )

    ax.fill_between(
        times,
        0.0,
        wide["P_dis_kw"],
        step="post",
        color=BATTERY_DISCHARGE,
        alpha=0.35,
        zorder=2,
    )
    ax.fill_between(
        times,
        0.0,
        -wide["P_ch_kw"],
        step="post",
        color=BATTERY_CHARGE,
        alpha=0.35,
        zorder=2,
    )

    for generator, grp in dispatch.groupby("generator"):
        starts = grp.loc[grp["startup"] > 0.5, ["datetime", "Pg_kw"]]
        if starts.empty:
            continue
        ax.scatter(
            starts["datetime"],
            starts["Pg_kw"],
            marker="^",
            s=55,
            color=GEN_COLORS.get(str(generator), "#64748B"),
            edgecolor="white",
            linewidth=0.6,
            zorder=7,
        )

    ax.axhline(0.0, color="#94A3B8", linewidth=0.9)
    ax.set_ylim(*y_limits)
    ax.set_yticks([-soc_power_ref_kw, 0.0, soc_power_ref_kw])
    ax.set_ylabel("Power [kW]", fontsize=LABEL_SIZE)
    add_algorithm_title(ax, bundle)
    return add_soc_overlay(ax, bundle, y_limits, show_right_label, soc_power_ref_kw)


def save_figure_set(fig: plt.Figure, output_dir: Path, stem: str) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    saved_paths: list[Path] = []
    for suffix in ("png", "pdf"):
        path = output_dir / f"{stem}.{suffix}"
        fig.savefig(path, dpi=180 if suffix == "png" else None, bbox_inches="tight")
        saved_paths.append(path)
    plt.close(fig)
    return saved_paths


def apply_time_axis_format(ax: plt.Axes, times: pd.Series, *, major_hours: int, minor_hours: int | None = None) -> None:
    format_hour_axis(ax, times, major_hours=major_hours)
    if minor_hours is not None and minor_hours > 0:
        ax.xaxis.set_minor_locator(mdates.HourLocator(interval=minor_hours))
        ax.tick_params(axis="x", which="minor", length=3.0, width=0.7, color="#94A3B8")
    ax.tick_params(axis="x", which="major", length=5.0, width=0.9)


def build_comparison_figure(
    bundles: list[RunBundle],
    output_dir: Path,
    output_stem: str,
    y_limits: tuple[float, float],
    soc_power_ref_kw: float,
) -> list[Path]:
    reference = bundles[0]
    times = reference.wide["datetime"]
    rows = 1 + len(bundles)
    height_ratios = [0.36] + [3.25] * len(bundles)
    figure_height = 1.35 + 3.65 * len(bundles)

    fig = plt.figure(figsize=(16.5, figure_height), constrained_layout=True)
    fig.set_constrained_layout_pads(w_pad=0.02, h_pad=0.02, hspace=0.02, wspace=0.02)
    grid = fig.add_gridspec(rows, 1, height_ratios=height_ratios, hspace=0.05)

    legend_ax = fig.add_subplot(grid[0, 0])
    legend_ax.axis("off")

    legend = legend_ax.legend(
        handles=dispatch_legend_handles(),
        loc="center",
        ncol=8,
        frameon=False,
        fontsize=LEGEND_SIZE - 1,
        handlelength=1.9,
        columnspacing=0.9,
        labelspacing=0.5,
        borderaxespad=0.0,
    )
    legend.set_in_layout(True)

    dispatch_axes: list[plt.Axes] = []
    for idx, bundle in enumerate(bundles):
        dispatch_ax = fig.add_subplot(grid[1 + idx, 0], sharex=dispatch_axes[0] if dispatch_axes else None)
        plot_dispatch_panel(
            dispatch_ax,
            bundle,
            y_limits,
            show_right_label=(idx == 0 or idx == len(bundles) - 1),
            soc_power_ref_kw=soc_power_ref_kw,
        )
        dispatch_axes.append(dispatch_ax)

    for idx, dispatch_ax in enumerate(dispatch_axes):
        if idx < len(dispatch_axes) - 1:
            dispatch_ax.tick_params(axis="x", labelbottom=False)
        else:
            apply_time_axis_format(dispatch_ax, times, major_hours=6, minor_hours=3)

    return save_figure_set(fig, output_dir, output_stem)


def main() -> None:
    args = parse_args()
    output_dir = resolve_output_dir(args.output_dir)

    bundles: list[RunBundle] = [
        load_run_bundle("milp", resolve_source_dir(args.milp_data_dir, args.milp_run, DEFAULT_MILP_SUFFIX)),
        load_run_bundle("rule", resolve_source_dir(args.rule_data_dir, args.rule_run, DEFAULT_RULE_SUFFIX)),
    ]
    if args.rolling_run or args.rolling_data_dir:
        bundles.append(
            load_run_bundle(
                "rolling",
                resolve_source_dir(args.rolling_data_dir, args.rolling_run, ""),
            )
        )

    assert_compatible_runs(bundles)
    y_limits = resolve_dispatch_limits(bundles, args.power_y_min, args.power_y_max)

    if args.soc_power_ref_kw <= 0:
        raise ValueError("--soc-power-ref-kw must be positive.")

    comparison_paths = build_comparison_figure(
        bundles,
        output_dir,
        args.output_stem,
        y_limits,
        args.soc_power_ref_kw,
    )

    print("Saved comparison figure:")
    for path in comparison_paths:
        print(f"  {path}")
    print(f"Power-axis limits: {y_limits[0]:.1f} to {y_limits[1]:.1f} kW")
    print(f"SOC/power alignment reference: +/-{args.soc_power_ref_kw:.1f} kW")
    print("Algorithms:")
    for bundle in bundles:
        style = style_for(bundle)
        print(
            f"  {style['label']}: fuel {bundle.total_fuel_kg:.2f} kg, "
            f"starts {bundle.total_starts}, terminal SOC {bundle.terminal_soc_pct:.2f}% "
            f"| source {bundle.source_dir} | load {bundle.profile_path}"
        )


if __name__ == "__main__":
    main()
