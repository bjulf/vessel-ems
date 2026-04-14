from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D


RATED_POWER_KW = 385.0
FUEL_DENSITY_G_PER_L = 840.0
REGIME_SPLIT_RPM = 1600.0
ROLLING_WINDOW = 5
MAX_LOAD_STD = 2.0
MAX_SPEED_STD = 20.0
MIN_BIN_COUNT = 20
MIN_REGIME_SPAN_PCT = 15.0
LOAD_BINS = np.arange(0, 101, 10)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_PATHS = [REPO_ROOT / "data" / "v01_clean.csv"]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "analysis" / "output"
CASE_ROOT = REPO_ROOT / "analysis" / "sfoc_cases"

OEM_POWER_KW = np.array([0.5 * RATED_POWER_KW, 0.75 * RATED_POWER_KW, 310.0, 385.0])
OEM_SFOC_GKWH = np.array([193.0, 191.0, 191.0, 198.0])

GEN_COLS = {
    1: {
        "fuel_lph": "Electric Power System > Generator Set > 1 > Engine > Fuel Rate",
        "load_pct": "Electric Power System > Generator Set > 1 > Engine > Load percentage",
        "speed_rpm": "Electric Power System > Generator Set > 1 > Engine > Speed",
    },
    2: {
        "fuel_lph": "Electric Power System > Generator Set > 2 > Engine > Fuel Rate",
        "load_pct": "Electric Power System > Generator Set > 2 > Engine > Load percentage",
        "speed_rpm": "Electric Power System > Generator Set > 2 > Engine > Speed",
    },
}

REGIME_LABELS = {
    "lt1600": "~1400 rpm",
    "ge1600": "~1800 rpm",
}

REGIME_COLORS = {
    "lt1600": "#1b9e77",
    "ge1600": "#d95f02",
}


def case_paths(output_dir: Path) -> dict[str, Path]:
    return {
        "breakpoints": output_dir / "sfoc_regime_breakpoints.csv",
        "summary": output_dir / "sfoc_fit_summary.txt",
        "overlay_fig": output_dir / "sfoc_regime_overlay.png",
        "clean_fig": output_dir / "sfoc_regime_clean_compare.png",
        "thesis_scatter_fig": output_dir / "sfoc_regime_thesis_scatter.png",
        "oem_diag_csv": output_dir / "sfoc_oem_diagnostic.csv",
        "oem_diag_txt": output_dir / "sfoc_oem_diagnostic.txt",
        "manifest": output_dir / "case_manifest.json",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fit telemetry-derived SFOC breakpoints.")
    parser.add_argument(
        "--data",
        nargs="+",
        default=[str(path) for path in DEFAULT_DATA_PATHS],
        help="One or more CSV input files to combine for the case.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory where case outputs should be written.",
    )
    parser.add_argument(
        "--case-label",
        default="default",
        help="Human-readable case label stored in the case manifest.",
    )
    return parser.parse_args()


def load_source_data(data_paths: list[Path]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for path in data_paths:
        if not path.is_file():
            raise FileNotFoundError(f"Missing {path}")
        frame = pd.read_csv(path, parse_dates=["DateTime"])
        frame["source_file"] = str(path)
        frames.append(frame)
    source_df = pd.concat(frames, ignore_index=True)
    return source_df.sort_values(["source_file", "DateTime"]).reset_index(drop=True)


def prepare_generator(df: pd.DataFrame, gen: int) -> pd.DataFrame:
    cols = GEN_COLS[gen]
    source_cols = ["DateTime", "source_file", *cols.values()]
    sub = df[source_cols].rename(columns={v: k for k, v in cols.items()}).copy()
    sub[["fuel_lph", "load_pct", "speed_rpm"]] = (
        sub[["fuel_lph", "load_pct", "speed_rpm"]]
        .apply(pd.to_numeric, errors="coerce")
        .fillna(0.0)
    )

    steady_frames: list[pd.DataFrame] = []
    for _, source_sub in sub.groupby("source_file", sort=False):
        source_sub = source_sub.sort_values("DateTime").copy()
        source_sub["load_std"] = source_sub["load_pct"].rolling(
            ROLLING_WINDOW, center=True, min_periods=ROLLING_WINDOW
        ).std()
        source_sub["speed_std"] = source_sub["speed_rpm"].rolling(
            ROLLING_WINDOW, center=True, min_periods=ROLLING_WINDOW
        ).std()
        source_sub["steady"] = (
            (source_sub["fuel_lph"] > 0.0)
            & (source_sub["load_pct"] > 0.0)
            & (source_sub["speed_rpm"] > 0.0)
            & (source_sub["load_std"] <= MAX_LOAD_STD)
            & (source_sub["speed_std"] <= MAX_SPEED_STD)
        )
        source_sub = source_sub.loc[source_sub["steady"]].copy()
        if source_sub.empty:
            continue
        source_sub["gen"] = gen
        source_sub["regime"] = np.where(source_sub["speed_rpm"] < REGIME_SPLIT_RPM, "lt1600", "ge1600")
        source_sub["power_kw"] = source_sub["load_pct"] / 100.0 * RATED_POWER_KW
        source_sub["fuel_gph"] = source_sub["fuel_lph"] * FUEL_DENSITY_G_PER_L
        source_sub["sfoc_gkwh"] = source_sub["fuel_gph"] / source_sub["power_kw"]
        source_sub["load_bin"] = pd.cut(source_sub["load_pct"], bins=LOAD_BINS, right=False)
        steady_frames.append(source_sub)

    if not steady_frames:
        return pd.DataFrame(
            columns=[
                "DateTime",
                "source_file",
                "fuel_lph",
                "load_pct",
                "speed_rpm",
                "load_std",
                "speed_std",
                "steady",
                "gen",
                "regime",
                "power_kw",
                "fuel_gph",
                "sfoc_gkwh",
                "load_bin",
            ]
        )
    return pd.concat(steady_frames, ignore_index=True)


def fit_linear_fuel_curve(regime_df: pd.DataFrame, supported_bins: pd.DataFrame) -> dict[str, object]:
    load_span_pct = supported_bins["load_pct_median"].max() - supported_bins["load_pct_median"].min()
    enough_span = load_span_pct >= MIN_REGIME_SPAN_PCT and len(supported_bins) >= 2
    result: dict[str, object] = {
        "load_span_pct": float(load_span_pct),
        "enough_span": bool(enough_span),
        "fit": None,
    }
    if not enough_span:
        return result

    x = regime_df["power_kw"].to_numpy(dtype=float)
    y = regime_df["fuel_gph"].to_numpy(dtype=float)
    slope, intercept = np.polyfit(x, y, deg=1)
    x_fit = np.linspace(supported_bins["power_kw_median"].min(), supported_bins["power_kw_median"].max(), 100)
    y_fit = intercept + slope * x_fit
    sfoc_fit = y_fit / x_fit
    result["fit"] = {
        "slope": float(slope),
        "intercept": float(intercept),
        "power_kw": x_fit,
        "fuel_gph": y_fit,
        "sfoc_gkwh": sfoc_fit,
    }
    return result


def summarize_bins(regime_df: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        regime_df.groupby("load_bin", observed=False)
        .agg(
            n=("load_pct", "size"),
            gens=("gen", "nunique"),
            load_pct_median=("load_pct", "median"),
            power_kw_median=("power_kw", "median"),
            fuel_gph_median=("fuel_gph", "median"),
            sfoc_gkwh_median=("sfoc_gkwh", "median"),
        )
        .reset_index()
    )
    grouped["supported"] = grouped["n"] >= MIN_BIN_COUNT
    return grouped.loc[grouped["n"] > 0].copy()


def build_breakpoints_table(all_points: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, dict[str, object]]]:
    rows: list[pd.DataFrame] = []
    fit_meta: dict[str, dict[str, object]] = {}
    for regime, regime_df in all_points.groupby("regime"):
        bins = summarize_bins(regime_df)
        supported = bins.loc[bins["supported"]].copy()
        fit_meta[regime] = fit_linear_fuel_curve(regime_df, supported)
        bins["regime"] = regime
        bins["regime_label"] = REGIME_LABELS[regime]
        rows.append(bins)
    return pd.concat(rows, ignore_index=True), fit_meta


def build_oem_diagnostic_table(breakpoints: pd.DataFrame) -> pd.DataFrame:
    supported = breakpoints.loc[breakpoints["supported"]].copy()
    oem_fuel = OEM_POWER_KW * OEM_SFOC_GKWH

    supported["oem_sfoc_gkwh"] = np.interp(supported["power_kw_median"], OEM_POWER_KW, OEM_SFOC_GKWH)
    supported["oem_fuel_gph"] = np.interp(supported["power_kw_median"], OEM_POWER_KW, oem_fuel)
    supported["fuel_delta_gph"] = supported["fuel_gph_median"] - supported["oem_fuel_gph"]
    supported["fuel_delta_pct"] = 100.0 * supported["fuel_delta_gph"] / supported["oem_fuel_gph"]
    supported["sfoc_delta_gkwh"] = supported["sfoc_gkwh_median"] - supported["oem_sfoc_gkwh"]
    supported["sfoc_delta_pct"] = 100.0 * supported["sfoc_delta_gkwh"] / supported["oem_sfoc_gkwh"]
    supported["power_scale_to_match_oem"] = (
        supported["fuel_gph_median"] / supported["oem_sfoc_gkwh"] / supported["power_kw_median"]
    )
    return supported[
        [
            "regime",
            "regime_label",
            "load_bin",
            "n",
            "power_kw_median",
            "fuel_gph_median",
            "oem_fuel_gph",
            "fuel_delta_gph",
            "fuel_delta_pct",
            "sfoc_gkwh_median",
            "oem_sfoc_gkwh",
            "sfoc_delta_gkwh",
            "sfoc_delta_pct",
            "power_scale_to_match_oem",
        ]
    ].sort_values(["regime", "power_kw_median"])


def write_oem_diagnostic_summary(diag: pd.DataFrame, breakpoints_path: Path) -> str:
    lines = [
        "Telemetry vs OEM diagnostic at supported breakpoint medians",
        f"Source telemetry breakpoints: {breakpoints_path}",
        "Interpretation note: if fuel_delta_pct and sfoc_delta_pct are similar, the mismatch is already present in fuel-vs-power, not mainly created by dividing by proxy power.",
        "",
    ]

    for regime, regime_df in diag.groupby("regime"):
        label = regime_df["regime_label"].iloc[0]
        lines.append(f"{label}")
        for row in regime_df.itertuples():
            lines.append(
                "  "
                f"{row.load_bin}: "
                f"P={row.power_kw_median:.1f} kW, "
                f"fuel={row.fuel_gph_median:.0f} g/h vs OEM {row.oem_fuel_gph:.0f} g/h "
                f"({row.fuel_delta_pct:+.1f}%), "
                f"SFOC={row.sfoc_gkwh_median:.1f} vs OEM {row.oem_sfoc_gkwh:.1f} "
                f"({row.sfoc_delta_pct:+.1f}%), "
                f"power-scale-to-match-OEM={row.power_scale_to_match_oem:.3f}"
            )
        lines.append(
            "  "
            f"mean fuel delta: {regime_df['fuel_delta_pct'].mean():+.1f}%, "
            f"mean SFOC delta: {regime_df['sfoc_delta_pct'].mean():+.1f}%, "
            f"mean power-scale-to-match-OEM: {regime_df['power_scale_to_match_oem'].mean():.3f}"
        )
        lines.append("")

    lines.append("Bottom line")
    for regime, label in REGIME_LABELS.items():
        regime_df = diag.loc[diag["regime"] == regime].copy()
        if regime_df.empty:
            continue
        fuel_min = regime_df["fuel_delta_pct"].min()
        fuel_max = regime_df["fuel_delta_pct"].max()
        sfoc_min = regime_df["sfoc_delta_pct"].min()
        sfoc_max = regime_df["sfoc_delta_pct"].max()
        direction = "above" if fuel_max > 0 else "below"
        lines.append(
            "  "
            f"{label} telemetry sits {direction} OEM by about "
            f"{fuel_min:+.1f}% to {fuel_max:+.1f}% in fuel and "
            f"{sfoc_min:+.1f}% to {sfoc_max:+.1f}% in SFOC across the supported bins."
        )
    lines.extend(
        [
            "  Because the fuel and SFOC deltas are nearly the same magnitude, the disagreement is not mainly an artifact of the SFOC conversion step.",
            "  A single power-proxy calibration fix would not reconcile both regimes to OEM at the same time.",
        ]
    )
    return "\n".join(lines)


def write_summary(
    source_df: pd.DataFrame,
    steady_df: pd.DataFrame,
    breakpoints: pd.DataFrame,
    fit_meta: dict[str, dict[str, object]],
    data_paths: list[Path],
) -> str:
    dt_minutes = source_df["DateTime"].sort_values().diff().dropna().dt.total_seconds() / 60.0
    g1_load = pd.to_numeric(source_df[GEN_COLS[1]["load_pct"]], errors="coerce").fillna(0.0)
    g1_speed = pd.to_numeric(source_df[GEN_COLS[1]["speed_rpm"]], errors="coerce").fillna(0.0)
    g2_load = pd.to_numeric(source_df[GEN_COLS[2]["load_pct"]], errors="coerce").fillna(0.0)
    g2_speed = pd.to_numeric(source_df[GEN_COLS[2]["speed_rpm"]], errors="coerce").fillna(0.0)
    both_online = (g1_load > 0.0) & (g1_speed > 0.0) & (g2_load > 0.0) & (g2_speed > 0.0)

    lines = [
        "Telemetry SFOC first-pass fit",
        "Sources:",
        *[f"  - {path}" for path in data_paths],
        f"Rows: {len(source_df)}",
        f"Time range: {source_df['DateTime'].min()} to {source_df['DateTime'].max()}",
        f"Cadence counts (minutes): {dt_minutes.value_counts().sort_index().to_dict()}",
        f"Steady filtered points: {len(steady_df)}",
        f"Both-gensets-online points in source data: {int(both_online.sum())}",
        "",
    ]

    for regime, regime_df in steady_df.groupby("regime"):
        label = REGIME_LABELS[regime]
        bins = breakpoints.loc[breakpoints["regime"] == regime].copy()
        supported = bins.loc[bins["supported"]].copy()
        lines.extend(
            [
                f"{label} regime",
                f"  filtered points: {len(regime_df)}",
                f"  power range: {regime_df['power_kw'].min():.1f} to {regime_df['power_kw'].max():.1f} kW",
                f"  load range: {regime_df['load_pct'].min():.1f} to {regime_df['load_pct'].max():.1f} %",
                f"  sfoc median/p10/p90: {regime_df['sfoc_gkwh'].median():.1f} / {regime_df['sfoc_gkwh'].quantile(0.1):.1f} / {regime_df['sfoc_gkwh'].quantile(0.9):.1f}",
                f"  supported bins: {supported[['load_bin', 'n']].to_dict('records')}",
                f"  supported load-span: {fit_meta[regime]['load_span_pct']:.1f} percentage points",
            ]
        )
        if fit_meta[regime]["fit"] is None:
            lines.append("  judgment: insufficient supported load-span for a defensible regime-wide curve")
        else:
            fit = fit_meta[regime]["fit"]
            lines.append(
                f"  linear fuel fit: fuel_gph = {fit['intercept']:.1f} + {fit['slope']:.3f} * power_kw"
            )
            lines.append("  judgment: adequate for a provisional sensitivity-case curve")
        lines.append("")

    lines.append("Overall judgment")
    lines.append("  The operational data support two distinct speed regimes and a telemetry-derived comparison case.")
    for regime in ("ge1600", "lt1600"):
        label = REGIME_LABELS[regime]
        bins = breakpoints.loc[breakpoints["regime"] == regime].copy()
        supported = bins.loc[bins["supported"]].copy()
        if supported.empty:
            lines.append(f"  {label} has no supported breakpoint bins in this case.")
            continue
        supported_bins = ", ".join(str(bin_label) for bin_label in supported["load_bin"])
        if fit_meta[regime]["fit"] is None:
            lines.append(
                "  "
                f"{label} has supported bins at {supported_bins}, but the supported span remains too narrow for a defensible regime-wide curve."
            )
        else:
            lines.append(
                "  "
                f"{label} has supported bins at {supported_bins} and enough span for a provisional telemetry curve."
            )
    lines.append("  OEM should remain the active baseline until telemetry breakpoints are tested in the optimizer and, ideally, true per-genset kW is available.")
    return "\n".join(lines)


def make_figure(
    steady_df: pd.DataFrame,
    breakpoints: pd.DataFrame,
    fit_meta: dict[str, dict[str, object]],
    output_path: Path,
) -> None:
    fig, (ax_fuel, ax_sfoc) = plt.subplots(2, 1, figsize=(13, 11), sharex=True)

    for regime, regime_df in steady_df.groupby("regime"):
        color = REGIME_COLORS[regime]
        label = REGIME_LABELS[regime]
        bins = breakpoints.loc[breakpoints["regime"] == regime]
        supported = bins.loc[bins["supported"]]

        ax_fuel.scatter(
            regime_df["power_kw"],
            regime_df["fuel_gph"],
            s=16,
            alpha=0.25,
            color=color,
            label=f"{label} points",
        )
        ax_fuel.plot(
            supported["power_kw_median"],
            supported["fuel_gph_median"],
            color=color,
            marker="o",
            lw=2.4,
            label=f"{label} bin medians",
        )

        ax_sfoc.scatter(
            regime_df["power_kw"],
            regime_df["sfoc_gkwh"],
            s=16,
            alpha=0.22,
            color=color,
            label=f"{label} points",
        )
        ax_sfoc.plot(
            supported["power_kw_median"],
            supported["sfoc_gkwh_median"],
            color=color,
            marker="o",
            lw=2.4,
            label=f"{label} bin medians",
        )

        fit = fit_meta[regime]["fit"]
        if fit is not None:
            ax_fuel.plot(
                fit["power_kw"],
                fit["fuel_gph"],
                color=color,
                lw=2.0,
                ls="--",
                label=f"{label} linear fit",
            )
            ax_sfoc.plot(
                fit["power_kw"],
                fit["sfoc_gkwh"],
                color=color,
                lw=2.0,
                ls="--",
                label=f"{label} derived SFOC fit",
            )

    oem_fuel = OEM_POWER_KW * OEM_SFOC_GKWH
    ax_fuel.plot(OEM_POWER_KW, oem_fuel, color="#2c3e50", lw=2.6, marker="s", label="OEM baseline")
    ax_sfoc.plot(OEM_POWER_KW, OEM_SFOC_GKWH, color="#2c3e50", lw=2.6, marker="s", label="OEM baseline")

    ax_fuel.set_title("Telemetry Fuel-Rate Fit by Speed Regime", fontsize=19, pad=14)
    ax_fuel.set_ylabel("Fuel Rate [g/h]", fontsize=15)
    ax_fuel.grid(alpha=0.25)
    ax_fuel.tick_params(labelsize=12)
    ax_fuel.legend(fontsize=11, ncol=2, frameon=False)

    ax_sfoc.set_title("Telemetry-Derived SFOC vs OEM Baseline", fontsize=19, pad=14)
    ax_sfoc.set_xlabel("Generator Power [kW]", fontsize=15)
    ax_sfoc.set_ylabel("SFOC [g/kWh]", fontsize=15)
    ax_sfoc.grid(alpha=0.25)
    ax_sfoc.tick_params(labelsize=12)
    ax_sfoc.legend(fontsize=11, ncol=2, frameon=False)
    ax_sfoc.set_ylim(150, 235)

    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=170, bbox_inches="tight")
    plt.close(fig)


def _label_last_point(
    ax: plt.Axes,
    x: np.ndarray,
    y: np.ndarray,
    label: str,
    color: str,
    dx: float = 6.0,
    dy: float = 0.0,
) -> None:
    ax.annotate(
        label,
        xy=(x[-1], y[-1]),
        xytext=(x[-1] + dx, y[-1] + dy),
        textcoords="data",
        color=color,
        fontsize=11,
        va="center",
        ha="left",
    )


def make_clean_comparison_figure(breakpoints: pd.DataFrame, output_path: Path) -> None:
    fig, (ax_fuel, ax_sfoc) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)

    oem_fuel = OEM_POWER_KW * OEM_SFOC_GKWH
    ax_fuel.plot(OEM_POWER_KW, oem_fuel, color="#2c3e50", lw=2.8, marker="s")
    ax_sfoc.plot(OEM_POWER_KW, OEM_SFOC_GKWH, color="#2c3e50", lw=2.8, marker="s")

    _label_last_point(ax_fuel, OEM_POWER_KW, oem_fuel, "OEM baseline", "#2c3e50", dx=5.0, dy=2500.0)
    _label_last_point(ax_sfoc, OEM_POWER_KW, OEM_SFOC_GKWH, "OEM baseline", "#2c3e50", dx=5.0, dy=1.8)

    for regime in ("lt1600", "ge1600"):
        supported = breakpoints.loc[
            (breakpoints["regime"] == regime) & (breakpoints["supported"])
        ].sort_values("power_kw_median")
        if supported.empty:
            continue

        x = supported["power_kw_median"].to_numpy()
        fuel = supported["fuel_gph_median"].to_numpy()
        sfoc = supported["sfoc_gkwh_median"].to_numpy()
        color = REGIME_COLORS[regime]

        ax_fuel.plot(x, fuel, color=color, lw=2.8, marker="o")
        ax_sfoc.plot(x, sfoc, color=color, lw=2.8, marker="o")

        suffix = " telemetry"
        if regime == "lt1600":
            suffix = " telemetry (narrow support)"

        fuel_dy = -1400.0 if regime == "lt1600" else 900.0
        sfoc_dy = -0.8 if regime == "lt1600" else 1.0
        _label_last_point(ax_fuel, x, fuel, f"{REGIME_LABELS[regime]}{suffix}", color, dx=5.0, dy=fuel_dy)
        _label_last_point(ax_sfoc, x, sfoc, f"{REGIME_LABELS[regime]}{suffix}", color, dx=5.0, dy=sfoc_dy)

    note = "Telemetry power uses proxy: load % × 385 kW"
    ax_fuel.text(
        0.02,
        0.06,
        note,
        transform=ax_fuel.transAxes,
        fontsize=11,
        color="#444444",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="#dddddd", alpha=0.9),
    )

    ax_fuel.set_title("Fuel Rate vs Generated Power: OEM and Telemetry Regimes", fontsize=18, pad=14)
    ax_fuel.set_ylabel("Fuel Rate [g/h]", fontsize=14)
    ax_fuel.grid(alpha=0.25)
    ax_fuel.tick_params(labelsize=11)

    ax_sfoc.set_title("SFOC vs Generated Power: OEM and Telemetry Regimes", fontsize=18, pad=14)
    ax_sfoc.set_xlabel("Generated Power [kW]", fontsize=14)
    ax_sfoc.set_ylabel("SFOC [g/kWh]", fontsize=14)
    ax_sfoc.grid(alpha=0.25)
    ax_sfoc.tick_params(labelsize=11)
    ax_sfoc.set_xlim(170, 395)
    ax_sfoc.set_ylim(170, 225)

    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=170, bbox_inches="tight")
    plt.close(fig)


def make_thesis_sfoc_figure(
    steady_df: pd.DataFrame,
    breakpoints: pd.DataFrame,
    output_path: Path,
) -> None:
    fig, ax = plt.subplots(figsize=(10, 7.5))
    legend_handles: dict[str, object] = {}

    for regime in ("lt1600", "ge1600"):
        regime_df = steady_df.loc[steady_df["regime"] == regime]
        supported = breakpoints.loc[
            (breakpoints["regime"] == regime) & (breakpoints["supported"])
        ].sort_values("power_kw_median")
        color = REGIME_COLORS[regime]
        label = "1400 rpm" if regime == "lt1600" else "1800 rpm"

        ax.scatter(
            regime_df["power_kw"],
            regime_df["sfoc_gkwh"],
            s=14,
            alpha=0.16,
            color=color,
            edgecolors="none",
            label=f"{label} points",
        )
        legend_handles[f"{label} points"] = Line2D(
            [0],
            [0],
            marker="o",
            linestyle="None",
            markersize=7.0,
            markerfacecolor=color,
            markeredgecolor=color,
            alpha=0.9,
            label=f"{label} points",
        )

        if not supported.empty:
            line, = ax.plot(
                supported["power_kw_median"],
                supported["sfoc_gkwh_median"],
                color=color,
                lw=2.2,
                marker="o",
                ms=6,
                label=f"{label} medians",
            )
            legend_handles[f"{label} medians"] = line

    oem_line, = ax.plot(
        OEM_POWER_KW,
        OEM_SFOC_GKWH,
        color="#2c3e50",
        lw=2.4,
        marker="s",
        ms=6,
        label="OEM curve",
    )
    legend_handles["OEM curve"] = oem_line

    ax.set_xlabel("Generator power proxy [kW]", fontsize=13)
    ax.set_ylabel("SFOC [g/kWh]", fontsize=13)
    ax.set_xlim(30, 395)
    ax.set_ylim(155, 225)
    ax.grid(alpha=0.25)
    ax.tick_params(labelsize=11)
    ordered_labels = [
        "1400 rpm points",
        "1800 rpm points",
        "OEM curve",
        "1400 rpm medians",
        "1800 rpm medians",
    ]
    ax.legend(
        [legend_handles[label] for label in ordered_labels if label in legend_handles],
        [label for label in ordered_labels if label in legend_handles],
        fontsize=10.5,
        frameon=False,
        ncol=2,
        loc="upper left",
    )

    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=170, bbox_inches="tight")
    plt.close(fig)


def write_case_manifest(
    manifest_path: Path,
    case_label: str,
    data_paths: list[Path],
    source_df: pd.DataFrame,
    steady_df: pd.DataFrame,
    breakpoints: pd.DataFrame,
) -> None:
    supported_bins = breakpoints.loc[breakpoints["supported"], ["regime", "load_bin", "n"]].copy()
    supported_bins["load_bin"] = supported_bins["load_bin"].astype(str)
    manifest = {
        "case_label": case_label,
        "data_paths": [str(path) for path in data_paths],
        "rows": int(len(source_df)),
        "steady_points": int(len(steady_df)),
        "time_range": {
            "start": str(source_df["DateTime"].min()),
            "end": str(source_df["DateTime"].max()),
        },
        "regime_counts": {
            str(key): int(val) for key, val in steady_df["regime"].value_counts().to_dict().items()
        },
        "supported_bins": supported_bins.to_dict("records"),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def main() -> None:
    args = parse_args()
    data_paths = [Path(path).resolve() for path in args.data]
    output_dir = Path(args.output_dir).resolve()
    paths = case_paths(output_dir)

    source_df = load_source_data(data_paths)
    steady_frames = [prepare_generator(source_df, gen) for gen in GEN_COLS]
    steady_df = pd.concat(steady_frames, ignore_index=True)

    breakpoints, fit_meta = build_breakpoints_table(steady_df)
    output_dir.mkdir(parents=True, exist_ok=True)
    breakpoints.to_csv(paths["breakpoints"], index=False)
    oem_diag = build_oem_diagnostic_table(breakpoints)
    oem_diag.to_csv(paths["oem_diag_csv"], index=False)

    summary = write_summary(source_df, steady_df, breakpoints, fit_meta, data_paths)
    paths["summary"].write_text(summary, encoding="utf-8")
    paths["oem_diag_txt"].write_text(
        write_oem_diagnostic_summary(oem_diag, paths["breakpoints"]), encoding="utf-8"
    )
    make_figure(steady_df, breakpoints, fit_meta, paths["overlay_fig"])
    make_clean_comparison_figure(breakpoints, paths["clean_fig"])
    make_thesis_sfoc_figure(steady_df, breakpoints, paths["thesis_scatter_fig"])
    write_case_manifest(paths["manifest"], args.case_label, data_paths, source_df, steady_df, breakpoints)

    print(summary)
    print("")
    print(f"Saved {paths['breakpoints']}")
    print(f"Saved {paths['summary']}")
    print(f"Saved {paths['overlay_fig']}")
    print(f"Saved {paths['clean_fig']}")
    print(f"Saved {paths['thesis_scatter_fig']}")
    print(f"Saved {paths['oem_diag_csv']}")
    print(f"Saved {paths['oem_diag_txt']}")
    print(f"Saved {paths['manifest']}")


if __name__ == "__main__":
    main()
