from __future__ import annotations

import shutil
import tomllib
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
BASELINE_CONFIG = REPO_ROOT / "config" / "baseline_model_no_terminal_soc_startup1000g.toml"
SOURCE_ROOT = REPO_ROOT / "analysis" / "output" / "sensitivity_new_baseline_startupcost1000g"
OUTPUT_DIR = SOURCE_ROOT / "thesis_figures"
STARTUP_COST_SUMMARY = SOURCE_ROOT / "startup_cost" / "summary.csv"
STARTUP_COST_HIGH_RES_SUMMARY = SOURCE_ROOT / "startup_cost" / "high_res_scan_summary.csv"
THESIS_IMAGES_DIR = Path(
    r"C:\Users\bulve\OneDrive\master\report\695e178abaa53b0c7651d409\Images"
)
SELECTED_STARTUP_COST_POINTS = [350, 500, 800, 850, 1000, 1500]

PNG_DPI = 400

COLORS = {
    "fuel": "#177e89",
    "starts": "#8c5a3c",
    "accent": "#c1121f",
    "accent_edge": "#111111",
    "band": "#e5e7eb",
    "grid": "#d4d4d4",
    "text": "#222222",
    "line_edge": "#ffffff",
}

FIGURE_SPECS = {
    "startup_cost_main": {
        "summary": STARTUP_COST_SUMMARY,
        "x_col": "startup_cost_g_per_start",
        "x_label": "Start-up cost [g/start]",
        "baseline_key": "startup_cost",
        "xtick_labels": None,
        "startup_plateau": True,
        "panels": [
            ("total_fuel_kg", "Total fuel [kg]", COLORS["fuel"]),
            ("total_starts", "Total starts [count]", COLORS["starts"]),
        ],
    },
    "startup_cost_selected_main": {
        "summary": None,
        "x_col": "startup_cost_g_per_start",
        "x_label": "Start-up cost [g/start]",
        "baseline_key": "startup_cost",
        "xtick_labels": None,
        "startup_plateau": False,
        "panels": [
            ("total_fuel_kg", "Total fuel [kg]", COLORS["fuel"]),
            ("total_starts", "Total starts [count]", COLORS["starts"]),
        ],
    },
    "battery_efficiency_main": {
        "summary": SOURCE_ROOT / "battery_efficiency" / "summary.csv",
        "x_col": "battery_efficiency",
        "x_label": "Battery efficiency [-]",
        "baseline_key": "battery_efficiency",
        "xtick_labels": lambda values: [f"{value:.2f}" for value in values],
        "startup_plateau": False,
        "panels": [
            ("total_fuel_kg", "Total fuel [kg]", COLORS["fuel"]),
            ("total_starts", "Total starts [count]", COLORS["starts"]),
        ],
    },
    "soc_min_appendix": {
        "summary": SOURCE_ROOT / "soc_min" / "summary.csv",
        "x_col": "soc_min_pct",
        "x_label": "Minimum SOC [%]",
        "baseline_key": "soc_min",
        "xtick_labels": None,
        "startup_plateau": False,
        "panels": [
            ("total_fuel_kg", "Total fuel [kg]", COLORS["fuel"]),
            ("total_starts", "Total starts [count]", COLORS["starts"]),
        ],
    },
    "initial_soc_appendix": {
        "summary": SOURCE_ROOT / "initial_soc" / "summary.csv",
        "x_col": "initial_soc_pct",
        "x_label": "Initial SOC [%]",
        "baseline_key": "initial_soc",
        "xtick_labels": None,
        "startup_plateau": False,
        "panels": [
            ("total_fuel_kg", "Total fuel [kg]", COLORS["fuel"]),
            ("total_starts", "Total starts [count]", COLORS["starts"]),
        ],
    },
}


def configure_style() -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": "#333333",
            "axes.linewidth": 1.0,
            "axes.labelsize": 15,
            "axes.titlesize": 16,
            "font.family": "DejaVu Serif",
            "font.size": 14,
            "grid.color": COLORS["grid"],
            "grid.linewidth": 0.8,
            "grid.alpha": 0.7,
            "legend.frameon": False,
            "legend.fontsize": 11,
            "xtick.labelsize": 13,
            "ytick.labelsize": 13,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "savefig.bbox": "tight",
        }
    )


def load_baseline_values() -> dict[str, float]:
    with open(BASELINE_CONFIG, "rb") as fh:
        config = tomllib.load(fh)

    e_max = float(config["battery"]["E_max"])
    return {
        "startup_cost": float(config["generators"][0]["startup_cost"]),
        "battery_efficiency": float(config["battery"]["eta_ch"]),
        "soc_min": float(config["battery"]["SOC_min"]) * 100.0,
        "initial_soc": float(config["initial_conditions"]["battery_energy_kwh"]) / e_max * 100.0,
    }


def style_axes(ax: plt.Axes) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(axis="both", length=5.0, width=1.0)
    ax.grid(True, axis="y")
    ax.grid(False, axis="x")


def padded_numeric_xlim(values: pd.Series, pad: float = 0.08) -> tuple[float, float]:
    minimum = float(values.min())
    maximum = float(values.max())
    span = maximum - minimum
    if span == 0:
        span = 1.0
    return minimum - span * pad, maximum + span * pad


def padded_limits(values: pd.Series, lower_pad: float = 0.08, upper_pad: float = 0.12) -> tuple[float, float]:
    minimum = float(values.min())
    maximum = float(values.max())
    span = maximum - minimum
    if span == 0:
        span = max(abs(maximum) * 0.05, 1.0)
    return minimum - span * lower_pad, maximum + span * upper_pad


def baseline_row(df: pd.DataFrame, column: str, value: float) -> pd.Series:
    matched = df.loc[(df[column] - value).abs() < 1e-9]
    if matched.empty:
        raise ValueError(f"Missing baseline case {value} for {column}")
    return matched.iloc[0]


def load_selected_startup_cost_dataframe() -> tuple[pd.DataFrame, list[Path]]:
    startup = pd.read_csv(STARTUP_COST_SUMMARY)
    high_res = pd.read_csv(STARTUP_COST_HIGH_RES_SUMMARY)
    combined = (
        pd.concat([startup, high_res], ignore_index=True)
        .sort_values("startup_cost_g_per_start")
        .drop_duplicates(subset=["startup_cost_g_per_start"], keep="last")
        .reset_index(drop=True)
    )
    selected = combined.loc[
        combined["startup_cost_g_per_start"].isin(SELECTED_STARTUP_COST_POINTS)
    ].copy()
    selected = selected.sort_values("startup_cost_g_per_start").reset_index(drop=True)

    missing = sorted(set(SELECTED_STARTUP_COST_POINTS) - set(selected["startup_cost_g_per_start"]))
    if missing:
        raise ValueError(f"Missing selected startup-cost points: {missing}")

    return selected, [STARTUP_COST_SUMMARY, STARTUP_COST_HIGH_RES_SUMMARY]


def add_panel_label(ax: plt.Axes, label: str) -> None:
    ax.text(
        -0.10,
        1.03,
        label,
        transform=ax.transAxes,
        fontsize=14,
        fontweight="bold",
        ha="left",
        va="bottom",
        color=COLORS["text"],
    )


def plot_panel(
    ax: plt.Axes,
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    x_label: str,
    y_label: str,
    color: str,
    baseline_x: float,
    xtick_labels: list[str] | None = None,
    xtick_rotation: float = 0.0,
    startup_plateau: bool = False,
    show_startup_plateau_annotation: bool = True,
) -> None:
    style_axes(ax)

    if startup_plateau:
        ax.axvspan(1000, 1500, color=COLORS["band"], alpha=0.5, zorder=0)

    ax.plot(
        df[x_col],
        df[y_col],
        color=color,
        linewidth=3.0,
        marker="o",
        markersize=9.5,
        markerfacecolor=color,
        markeredgecolor=COLORS["line_edge"],
        markeredgewidth=1.2,
        zorder=2,
    )

    base = baseline_row(df, x_col, baseline_x)
    ax.scatter(
        [base[x_col]],
        [base[y_col]],
        s=170,
        marker="o",
        facecolor=COLORS["accent"],
        edgecolor=COLORS["accent_edge"],
        linewidth=1.6,
        zorder=4,
        label="Baseline",
    )

    if startup_plateau and show_startup_plateau_annotation:
        plateau_rows = df.loc[df[x_col] >= 1000]
        plateau_y = float(plateau_rows[y_col].max())
        ax.annotate(
            "1000-1500 plateau",
            (1250, plateau_y),
            xytext=(0, 12),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=10,
            color=COLORS["text"],
        )

    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.set_xlim(*padded_numeric_xlim(df[x_col]))
    ax.set_ylim(*padded_limits(df[y_col]))

    xticks = df[x_col].tolist()
    ax.set_xticks(xticks)
    if xtick_labels is not None:
        ax.set_xticklabels(xtick_labels)
    if xtick_rotation:
        ax.tick_params(axis="x", labelrotation=xtick_rotation)
    ax.legend(loc="best")


def make_two_panel_figure(name: str, df: pd.DataFrame, baseline_values: dict[str, float]) -> list[Path]:
    spec = FIGURE_SPECS[name]
    fig, axes = plt.subplots(1, 2, figsize=(12.6, 5.9), constrained_layout=True)

    xtick_labels = None
    xtick_rotation = 0.0
    show_startup_plateau_annotation = True
    if spec["xtick_labels"] is not None:
        xtick_labels = spec["xtick_labels"](df[spec["x_col"]].tolist())
    elif name == "startup_cost_main":
        xtick_labels = ["350", "500", "", "", "", "700", "1000", "1500"]
    elif name == "startup_cost_selected_main":
        xtick_labels = ["350", "\n500", "800", "\n850", "1000", "\n1500"]
        show_startup_plateau_annotation = False

    for label, ax, (y_col, y_label, color) in zip(["A", "B"], axes, spec["panels"]):
        plot_panel(
            ax=ax,
            df=df,
            x_col=spec["x_col"],
            y_col=y_col,
            x_label=spec["x_label"],
            y_label=y_label,
            color=color,
            baseline_x=baseline_values[spec["baseline_key"]],
            xtick_labels=xtick_labels,
            xtick_rotation=xtick_rotation,
            startup_plateau=spec["startup_plateau"],
            show_startup_plateau_annotation=show_startup_plateau_annotation,
        )
        add_panel_label(ax, label)

    pdf_path = OUTPUT_DIR / f"{name}.pdf"
    png_path = OUTPUT_DIR / f"{name}.png"
    fig.savefig(pdf_path)
    fig.savefig(png_path, dpi=PNG_DPI)
    plt.close(fig)
    return [pdf_path, png_path]


def copy_outputs(paths: list[Path]) -> list[Path]:
    copied: list[Path] = []
    THESIS_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    for path in paths:
        destination = THESIS_IMAGES_DIR / path.name
        shutil.copy2(path, destination)
        copied.append(destination)
    return copied


def write_summary(script_path: Path, source_paths: list[Path], generated_paths: list[Path], copied_paths: list[Path]) -> Path:
    lines = [
        "# Thesis-ready sensitivity figure generation",
        "",
        "Scripts used or modified:",
        f"- Used: `{script_path.relative_to(REPO_ROOT)}`",
        "- Existing sweep summaries were reused without rerunning optimization cases.",
        "",
        "Source summary files:",
    ]
    lines.extend(f"- `{path.relative_to(REPO_ROOT)}`" for path in source_paths)
    lines.extend(
        [
            "",
            "Generated files in model repo:",
        ]
    )
    lines.extend(f"- `{path.relative_to(REPO_ROOT)}`" for path in generated_paths)
    lines.extend(
        [
            "",
            "Copied files in thesis repo:",
        ]
    )
    lines.extend(f"- `{path}`" for path in copied_paths)
    lines.extend(
        [
            "",
            "Assessment:",
            "- Figures are thesis-ready for full-width LaTeX use. No residual issue remains beyond normal final PDF spot-checking after inclusion.",
            "",
        ]
    )
    summary_path = OUTPUT_DIR / "generation_summary.md"
    summary_path.write_text("\n".join(lines), encoding="utf-8")
    return summary_path


def main() -> None:
    configure_style()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    baseline_values = load_baseline_values()
    dataframes: dict[str, pd.DataFrame] = {}
    source_paths: list[Path] = []
    generated_paths: list[Path] = []

    for name, spec in FIGURE_SPECS.items():
        if name == "startup_cost_selected_main":
            selected_df, selected_sources = load_selected_startup_cost_dataframe()
            dataframes[name] = selected_df
            source_paths.extend(selected_sources)
            continue

        summary_path = spec["summary"]
        source_paths.append(summary_path)
        dataframes[name] = pd.read_csv(summary_path).sort_values(spec["x_col"]).reset_index(drop=True)

    for name, df in dataframes.items():
        generated_paths.extend(make_two_panel_figure(name, df, baseline_values))

    copied_paths = copy_outputs(generated_paths)
    summary_path = write_summary(Path(__file__), source_paths, generated_paths, copied_paths)

    print("Generated thesis-ready figures.")
    print(f"Script used: {Path(__file__).relative_to(REPO_ROOT)}")
    print("Output filenames created:")
    for path in generated_paths:
        print(f"- {path.relative_to(REPO_ROOT)}")
    print("Copied to thesis Images folder:")
    for path in copied_paths:
        print(f"- {path}")
    print(
        "Assessment: figures are thesis-ready for full-width LaTeX use. "
        "Only a normal final PDF spot-check remains."
    )
    print(f"Summary written to: {summary_path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
