from __future__ import annotations

import math
import tomllib
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO_ROOT / "analysis" / "output" / "sensitivity" / "thesis"

STARTUP_SUMMARY = REPO_ROOT / "analysis" / "output" / "sensitivity" / "startup_cost" / "summary.csv"
TERMINAL_SOC_SUMMARY = REPO_ROOT / "analysis" / "output" / "sensitivity" / "terminal_reserve" / "summary.csv"
SOC_MIN_SUMMARY = REPO_ROOT / "analysis" / "output" / "sensitivity" / "soc_min" / "summary.csv"
INITIAL_SOC_SUMMARY = REPO_ROOT / "analysis" / "output" / "sensitivity" / "initial_soc" / "summary.csv"
BATTERY_EFFICIENCY_SUMMARY = REPO_ROOT / "analysis" / "output" / "sensitivity" / "battery_efficiency" / "summary.csv"
BASELINE_CONFIG = REPO_ROOT / "config" / "baseline_model.toml"

COLORS = {
    "fuel": "#177e89",
    "starts": "#8c5a3c",
    "min_soc": "#2b59c3",
    "throughput": "#d97706",
    "both_online": "#6b7280",
    "baseline_face": "#c1121f",
    "baseline_edge": "#111111",
    "line_edge": "#ffffff",
    "grid": "#d4d4d4",
    "text": "#222222",
}

PNG_DPI = 400


def configure_style() -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": "#333333",
            "axes.linewidth": 1.0,
            "axes.labelsize": 18,
            "axes.titlesize": 16,
            "axes.titleweight": "semibold",
            "font.family": "DejaVu Serif",
            "font.size": 16,
            "grid.color": COLORS["grid"],
            "grid.linewidth": 0.8,
            "grid.alpha": 0.7,
            "legend.frameon": False,
            "xtick.labelsize": 15,
            "ytick.labelsize": 15,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "savefig.bbox": "tight",
        }
    )


def load_baseline_values() -> dict[str, float]:
    with open(BASELINE_CONFIG, "rb") as fh:
        config = tomllib.load(fh)

    e_max = float(config["battery"]["E_max"])
    startup_cost = int(round(float(config["generators"][0]["startup_cost"])))
    terminal_soc_requirement = int(round(float(config["terminal_conditions"]["battery_energy_min_kwh"]) / e_max * 100))
    soc_min = int(round(float(config["battery"]["SOC_min"]) * 100))
    initial_soc = int(round(float(config["initial_conditions"]["battery_energy_kwh"]) / e_max * 100))
    battery_efficiency = float(config["battery"]["eta_ch"])
    return {
        "startup_cost": startup_cost,
        "terminal_soc_requirement": terminal_soc_requirement,
        "soc_min": soc_min,
        "initial_soc": initial_soc,
        "battery_efficiency": battery_efficiency,
    }


def load_summaries() -> dict[str, pd.DataFrame]:
    startup = pd.read_csv(STARTUP_SUMMARY).sort_values("startup_cost_g_per_start").reset_index(drop=True)
    terminal = pd.read_csv(TERMINAL_SOC_SUMMARY).sort_values("terminal_reserve_pct").reset_index(drop=True)
    soc_min = pd.read_csv(SOC_MIN_SUMMARY).sort_values("soc_min_pct").reset_index(drop=True)
    initial_soc = pd.read_csv(INITIAL_SOC_SUMMARY).sort_values("initial_soc_pct").reset_index(drop=True)
    battery_efficiency = (
        pd.read_csv(BATTERY_EFFICIENCY_SUMMARY).sort_values("battery_efficiency").reset_index(drop=True)
    )
    return {
        "startup": startup,
        "terminal": terminal,
        "soc_min": soc_min,
        "initial_soc": initial_soc,
        "battery_efficiency": battery_efficiency,
    }


def style_axes(ax: plt.Axes) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(axis="both", length=5.0, width=1.0)
    ax.grid(True, axis="y")
    ax.grid(False, axis="x")


def add_panel_label(ax: plt.Axes, label: str) -> None:
    ax.text(
        -0.10,
        1.05,
        label,
        transform=ax.transAxes,
        fontsize=16,
        fontweight="bold",
        ha="left",
        va="bottom",
        color=COLORS["text"],
    )


def padded_limits(values: pd.Series, lower_pad: float = 0.08, upper_pad: float = 0.12) -> tuple[float, float]:
    minimum = float(values.min())
    maximum = float(values.max())
    span = maximum - minimum
    if span == 0:
        span = max(abs(maximum) * 0.05, 1.0)
    return minimum - span * lower_pad, maximum + span * upper_pad


def padded_numeric_xlim(values: pd.Series, pad: float = 0.08) -> tuple[float, float]:
    minimum = float(values.min())
    maximum = float(values.max())
    span = maximum - minimum
    if span == 0:
        span = 1.0
    return minimum - span * pad, maximum + span * pad


def baseline_row(df: pd.DataFrame, column: str, value: float) -> pd.Series:
    matched = df.loc[(df[column] - value).abs() < 1e-9]
    if matched.empty:
        raise ValueError(f"Missing baseline case {value} for {column}")
    return matched.iloc[0]


def format_number(value: float) -> str:
    rounded = round(float(value), 2)
    if abs(rounded - round(rounded)) < 1e-9:
        return str(int(round(rounded)))
    if abs(rounded * 10 - round(rounded * 10)) < 1e-9:
        return f"{rounded:.1f}"
    return f"{rounded:.2f}"


def plot_series(
    ax: plt.Axes,
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    x_label: str,
    y_label: str,
    title: str,
    color: str,
    baseline_x: float,
    connect: bool = True,
    annotate_baseline: bool = False,
    xticks: list[float] | None = None,
) -> None:
    style_axes(ax)
    if connect:
        ax.plot(
            df[x_col],
            df[y_col],
            color=color,
            linewidth=3.1,
            marker="o",
            markersize=9.5,
            markerfacecolor=color,
            markeredgecolor=COLORS["line_edge"],
            markeredgewidth=1.2,
            zorder=2,
        )
    else:
        ax.scatter(
            df[x_col],
            df[y_col],
            s=110,
            facecolor=color,
            edgecolor=COLORS["line_edge"],
            linewidth=1.2,
            zorder=2,
        )

    base = baseline_row(df, x_col, baseline_x)
    ax.scatter(
        [base[x_col]],
        [base[y_col]],
        s=155,
        facecolor=COLORS["baseline_face"],
        edgecolor=COLORS["baseline_edge"],
        linewidth=1.7,
        zorder=4,
    )

    if annotate_baseline:
        ax.annotate(
            "Baseline",
            (float(base[x_col]), float(base[y_col])),
            xytext=(10, 12),
            textcoords="offset points",
            ha="left",
            va="bottom",
            fontsize=13,
            color=COLORS["text"],
        )

    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.set_title(title, pad=12)
    ax.set_xlim(*padded_numeric_xlim(df[x_col]))
    ax.set_ylim(*padded_limits(df[y_col]))
    if xticks is not None:
        ax.set_xticks(xticks)


def startup_label_offsets(df: pd.DataFrame) -> dict[int, tuple[int, int]]:
    offsets_by_group_size = {
        1: [(10, 10)],
        2: [(-18, 16), (18, -16)],
        3: [(-10, 18), (24, 18), (0, -20)],
    }
    offsets: dict[int, tuple[int, int]] = {}
    grouped = df.groupby(
        [
            df["total_starts"].round(6),
            df["total_fuel_kg"].round(6),
        ],
        sort=False,
    )
    for _, group in grouped:
        group = group.sort_values("startup_cost_g_per_start")
        patterns = offsets_by_group_size.get(len(group))
        if patterns is None:
            patterns = []
            radius = 26
            for idx in range(len(group)):
                angle = 2.0 * math.pi * idx / len(group)
                patterns.append((int(round(radius * math.cos(angle))), int(round(radius * math.sin(angle)))))
        for (_, row), offset in zip(group.iterrows(), patterns):
            offsets[int(row.name)] = offset
    return offsets


def plot_startup_tradeoff(ax: plt.Axes, df: pd.DataFrame, baseline_cost: int) -> None:
    style_axes(ax)
    ax.plot(
        df["total_starts"],
        df["total_fuel_kg"],
        color=COLORS["fuel"],
        linewidth=3.0,
        marker="o",
        markersize=9.5,
        markerfacecolor=COLORS["fuel"],
        markeredgecolor=COLORS["line_edge"],
        markeredgewidth=1.2,
        zorder=2,
    )

    base = baseline_row(df, "startup_cost_g_per_start", baseline_cost)
    ax.scatter(
        [base["total_starts"]],
        [base["total_fuel_kg"]],
        s=190,
        facecolor=COLORS["baseline_face"],
        edgecolor=COLORS["baseline_edge"],
        linewidth=1.7,
        zorder=4,
    )

    labels_to_show = {int(round(float(df["startup_cost_g_per_start"].min())))}
    offsets = startup_label_offsets(df)

    for idx, row in df.iterrows():
        startup_cost = int(round(float(row["startup_cost_g_per_start"])))
        if startup_cost not in labels_to_show:
            continue
        x_offset, y_offset = offsets.get(int(idx), (10, 12))
        is_baseline = startup_cost == baseline_cost
        ax.annotate(
            f"{startup_cost}",
            (float(row["total_starts"]), float(row["total_fuel_kg"])),
            xytext=(x_offset, y_offset),
            textcoords="offset points",
            ha="center",
            va="bottom" if y_offset >= 0 else "top",
            fontsize=13,
            color=COLORS["text"],
            bbox={
                "boxstyle": "round,pad=0.18",
                "facecolor": "#fff5f5" if is_baseline else "white",
                "edgecolor": COLORS["baseline_face"] if is_baseline else "none",
                "linewidth": 0.9 if is_baseline else 0.0,
                "alpha": 0.95,
            },
            zorder=5,
        )

    ax.set_xlabel("Total starts [count]")
    ax.set_ylabel("Total fuel [kg]")
    ax.set_title("Startup cost trade-off", pad=12)
    ax.set_xlim(*padded_numeric_xlim(df["total_starts"], pad=0.12))
    ax.set_ylim(*padded_limits(df["total_fuel_kg"], lower_pad=0.08, upper_pad=0.14))


def save_figure(fig: plt.Figure, stem: str) -> None:
    pdf_path = OUTPUT_DIR / f"{stem}.pdf"
    png_path = OUTPUT_DIR / f"{stem}.png"
    fig.savefig(pdf_path)
    fig.savefig(png_path, dpi=PNG_DPI)
    plt.close(fig)


def make_startup_cost_main_figure(startup: pd.DataFrame, baseline: dict[str, float]) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(15.8, 6.3), constrained_layout=True)

    plot_startup_tradeoff(axes[0], startup, int(baseline["startup_cost"]))
    add_panel_label(axes[0], "A")

    plot_series(
        axes[1],
        startup,
        "startup_cost_g_per_start",
        "min_soc_pct",
        "Startup cost [g/start]",
        "Minimum SOC reached [%]",
        "Minimum SOC response",
        COLORS["min_soc"],
        baseline["startup_cost"],
        xticks=[350, 550, 700, 1000, 1500],
    )
    axes[1].tick_params(axis="x", labelsize=14)
    add_panel_label(axes[1], "B")

    save_figure(fig, "startup_cost_main")


def make_other_main_sensitivities_figure(
    terminal: pd.DataFrame,
    battery_efficiency: pd.DataFrame,
    baseline: dict[str, float],
) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(15.6, 11.3), constrained_layout=True)

    plot_series(
        axes[0, 0],
        terminal,
        "terminal_reserve_pct",
        "total_fuel_kg",
        "Terminal SOC requirement [%]",
        "Total fuel [kg]",
        "Fuel response to terminal SOC requirement",
        COLORS["fuel"],
        baseline["terminal_soc_requirement"],
        xticks=terminal["terminal_reserve_pct"].tolist(),
    )
    add_panel_label(axes[0, 0], "A")

    plot_series(
        axes[0, 1],
        terminal,
        "terminal_reserve_pct",
        "min_soc_pct",
        "Terminal SOC requirement [%]",
        "Minimum SOC reached [%]",
        "Minimum SOC versus terminal SOC requirement",
        COLORS["min_soc"],
        baseline["terminal_soc_requirement"],
        xticks=terminal["terminal_reserve_pct"].tolist(),
    )
    add_panel_label(axes[0, 1], "B")

    eff_ticks = battery_efficiency["battery_efficiency"].tolist()
    plot_series(
        axes[1, 0],
        battery_efficiency,
        "battery_efficiency",
        "total_fuel_kg",
        "Battery charge/discharge efficiency [-]",
        "Total fuel [kg]",
        "Fuel response to battery efficiency",
        COLORS["fuel"],
        baseline["battery_efficiency"],
        xticks=eff_ticks,
    )
    axes[1, 0].set_xticklabels([f"{tick:.2f}" for tick in eff_ticks])
    add_panel_label(axes[1, 0], "C")

    plot_series(
        axes[1, 1],
        battery_efficiency,
        "battery_efficiency",
        "total_starts",
        "Battery charge/discharge efficiency [-]",
        "Total starts [count]",
        "Generator starts versus battery efficiency",
        COLORS["starts"],
        baseline["battery_efficiency"],
        xticks=eff_ticks,
    )
    axes[1, 1].set_xticklabels([f"{tick:.2f}" for tick in eff_ticks])
    add_panel_label(axes[1, 1], "D")

    save_figure(fig, "other_main_sensitivities")


def make_startup_appendix_figure(startup: pd.DataFrame, baseline: dict[str, float]) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(14.2, 10.6), constrained_layout=True)

    panels = [
        ("total_fuel_kg", "Total fuel [kg]", "Fuel response", COLORS["fuel"]),
        ("total_starts", "Total starts [count]", "Generator starts", COLORS["starts"]),
        ("min_soc_pct", "Minimum SOC reached [%]", "Minimum SOC reached", COLORS["min_soc"]),
        ("battery_throughput_kwh", "Battery throughput [kWh]", "Battery throughput", COLORS["throughput"]),
    ]

    for label, ax, (y_col, y_label, title, color) in zip(["A", "B", "C", "D"], axes.flatten(), panels):
        plot_series(
            ax,
            startup,
            "startup_cost_g_per_start",
            y_col,
            "Startup cost [g/start]",
            y_label,
            title,
            color,
            baseline["startup_cost"],
            xticks=startup["startup_cost_g_per_start"].tolist(),
        )
        add_panel_label(ax, label)

    save_figure(fig, "startup_cost_appendix")


def make_terminal_soc_appendix_figure(terminal: pd.DataFrame, baseline: dict[str, float]) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(14.2, 10.6), constrained_layout=True)

    panels = [
        ("total_fuel_kg", "Total fuel [kg]", "Fuel response", COLORS["fuel"]),
        ("total_starts", "Total starts [count]", "Generator starts", COLORS["starts"]),
        ("min_soc_pct", "Minimum SOC reached [%]", "Minimum SOC reached", COLORS["min_soc"]),
        ("battery_throughput_kwh", "Battery throughput [kWh]", "Battery throughput", COLORS["throughput"]),
    ]

    for label, ax, (y_col, y_label, title, color) in zip(["A", "B", "C", "D"], axes.flatten(), panels):
        plot_series(
            ax,
            terminal,
            "terminal_reserve_pct",
            y_col,
            "Terminal SOC requirement [%]",
            y_label,
            title,
            color,
            baseline["terminal_soc_requirement"],
            xticks=terminal["terminal_reserve_pct"].tolist(),
        )
        add_panel_label(ax, label)

    save_figure(fig, "terminal_soc_requirement_appendix")


def make_soc_min_appendix_figure(soc_min: pd.DataFrame, baseline: dict[str, float]) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12.3, 5.8), constrained_layout=True)

    panels = [
        ("total_fuel_kg", "Total fuel [kg]", "Fuel response", COLORS["fuel"]),
        ("total_starts", "Total starts [count]", "Generator starts", COLORS["starts"]),
    ]

    for label, ax, (y_col, y_label, title, color) in zip(["A", "B"], axes, panels):
        plot_series(
            ax,
            soc_min,
            "soc_min_pct",
            y_col,
            "Minimum SOC constraint [%]",
            y_label,
            title,
            color,
            baseline["soc_min"],
            xticks=soc_min["soc_min_pct"].tolist(),
        )
        add_panel_label(ax, label)

    save_figure(fig, "soc_min_appendix")


def make_initial_soc_appendix_figure(initial_soc: pd.DataFrame, baseline: dict[str, float]) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12.3, 5.8), constrained_layout=True)

    panels = [
        ("total_fuel_kg", "Total fuel [kg]", "Fuel response", COLORS["fuel"]),
        ("total_starts", "Total starts [count]", "Generator starts", COLORS["starts"]),
    ]

    for label, ax, (y_col, y_label, title, color) in zip(["A", "B"], axes, panels):
        plot_series(
            ax,
            initial_soc,
            "initial_soc_pct",
            y_col,
            "Initial SOC [%]",
            y_label,
            title,
            color,
            baseline["initial_soc"],
            xticks=initial_soc["initial_soc_pct"].tolist(),
        )
        add_panel_label(ax, label)

    save_figure(fig, "initial_soc_appendix")


def make_battery_efficiency_appendix_figure(
    battery_efficiency: pd.DataFrame,
    baseline: dict[str, float],
) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(14.2, 10.6), constrained_layout=True)
    eff_ticks = battery_efficiency["battery_efficiency"].tolist()

    panels = [
        ("total_fuel_kg", "Total fuel [kg]", "Fuel response", COLORS["fuel"]),
        ("total_starts", "Total starts [count]", "Generator starts", COLORS["starts"]),
        ("min_soc_pct", "Minimum SOC reached [%]", "Minimum SOC reached", COLORS["min_soc"]),
        ("battery_throughput_kwh", "Battery throughput [kWh]", "Battery throughput", COLORS["throughput"]),
    ]

    for label, ax, (y_col, y_label, title, color) in zip(["A", "B", "C", "D"], axes.flatten(), panels):
        plot_series(
            ax,
            battery_efficiency,
            "battery_efficiency",
            y_col,
            "Battery charge/discharge efficiency [-]",
            y_label,
            title,
            color,
            baseline["battery_efficiency"],
            xticks=eff_ticks,
        )
        ax.set_xticklabels([f"{tick:.2f}" for tick in eff_ticks])
        add_panel_label(ax, label)

    save_figure(fig, "battery_efficiency_appendix")


def write_manifest() -> None:
    text = """# Sensitivity Figure Manifest

These figures are presentation figures derived from the existing sweep summary CSV files. They are not new model runs.

Related notes:

- `sweep_parameters.md`
  - Consolidated record of the baseline values and sweep case values used for these figures

## Generated figures

- `startup_cost_main.pdf` and `startup_cost_main.png`
  - Source: `analysis/output/sensitivity/startup_cost/summary.csv`
  - Intended use: main text
  - Panels: A startup-cost trade-off in fuel versus starts, B minimum-SOC response to startup cost

- `other_main_sensitivities.pdf` and `other_main_sensitivities.png`
  - Sources: `analysis/output/sensitivity/terminal_reserve/summary.csv`, `analysis/output/sensitivity/battery_efficiency/summary.csv`
  - Intended use: main text
  - Panels: A fuel versus terminal SOC requirement, B minimum SOC versus terminal SOC requirement, C fuel versus battery efficiency, D starts versus battery efficiency

- `startup_cost_appendix.pdf` and `startup_cost_appendix.png`
  - Source: `analysis/output/sensitivity/startup_cost/summary.csv`
  - Intended use: appendix only
  - Panels: total fuel, total starts, minimum SOC reached, battery throughput versus startup cost

- `terminal_soc_requirement_appendix.pdf` and `terminal_soc_requirement_appendix.png`
  - Source: `analysis/output/sensitivity/terminal_reserve/summary.csv`
  - Intended use: appendix only
  - Panels: total fuel, total starts, minimum SOC reached, battery throughput versus terminal SOC requirement

- `battery_efficiency_appendix.pdf` and `battery_efficiency_appendix.png`
  - Source: `analysis/output/sensitivity/battery_efficiency/summary.csv`
  - Intended use: appendix only
  - Panels: total fuel, total starts, minimum SOC reached, battery throughput versus battery efficiency

- `soc_min_appendix.pdf` and `soc_min_appendix.png`
  - Source: `analysis/output/sensitivity/soc_min/summary.csv`
  - Intended use: appendix only
  - Panels: total fuel and total starts versus minimum SOC

- `initial_soc_appendix.pdf` and `initial_soc_appendix.png`
  - Source: `analysis/output/sensitivity/initial_soc/summary.csv`
  - Intended use: appendix only
  - Panels: total fuel and total starts versus initial SOC
"""
    (OUTPUT_DIR / "figure_manifest.md").write_text(text, encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    configure_style()
    baseline = load_baseline_values()
    summaries = load_summaries()

    make_startup_cost_main_figure(summaries["startup"], baseline)
    make_other_main_sensitivities_figure(
        summaries["terminal"],
        summaries["battery_efficiency"],
        baseline,
    )
    make_startup_appendix_figure(summaries["startup"], baseline)
    make_terminal_soc_appendix_figure(summaries["terminal"], baseline)
    make_battery_efficiency_appendix_figure(summaries["battery_efficiency"], baseline)
    make_soc_min_appendix_figure(summaries["soc_min"], baseline)
    make_initial_soc_appendix_figure(summaries["initial_soc"], baseline)
    write_manifest()


if __name__ == "__main__":
    main()
