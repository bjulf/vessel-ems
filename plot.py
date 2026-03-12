"""
Dispatch results plotter.
Reads dispatch_results.csv produced by main.jl and generates plots.

Usage:  python plot.py
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import seaborn as sns
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────────
CSV_PATH = Path(__file__).parent / "dispatch_results.csv"
SAVE_DIR = Path(__file__).parent / "plots"
DPI = 150
SAVE = True  # Set False to only display, not save


def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["generator"] = df["generator"].astype(str)  # treat as categorical label
    return df


# ── Plot 1: Stacked bar – generator power dispatch ────────────────────────────
def plot_stacked_power(df: pd.DataFrame, ax: plt.Axes):
    """Stacked bar showing each generator's power contribution per timestep."""
    pivot = df.pivot(index="timestep", columns="generator", values="Pg_mw")
    pivot.plot.bar(stacked=True, ax=ax, edgecolor="white", linewidth=0.5)

    # Overlay total load as a line
    load = df.groupby("timestep")["load_mw"].first()
    ax.plot(
        np.arange(len(load)), load.values,
        color="black", marker="o", ms=5, lw=1.5, label="Load demand",
    )

    ax.set_xlabel("Timestep")
    ax.set_ylabel("Power [MW]")
    ax.set_title("Generator Dispatch vs. Load")
    ax.legend(title="Generator", loc="upper left")
    ax.set_xticklabels(pivot.index, rotation=0)


# ── Plot 2: SFOC line plot ────────────────────────────────────────────────────
def plot_sfoc(df: pd.DataFrame, ax: plt.Axes):
    """Line plot of SFOC (g/kWh) per generator over timesteps."""
    for gen, grp in df.groupby("generator"):
        mask = grp["u"] == 1
        ax.plot(
            grp.loc[mask, "timestep"], grp.loc[mask, "sfoc_gkwh"],
            marker="s", ms=5, lw=1.5, label=f"Gen {gen}",
        )
        # Mark offline timesteps
        if (~mask).any():
            ax.scatter(
                grp.loc[~mask, "timestep"],
                [ax.get_ylim()[0]] * (~mask).sum(),
                marker="x", s=40, color="grey", zorder=5,
            )

    ax.set_xlabel("Timestep")
    ax.set_ylabel("SFOC [g/kWh]")
    ax.set_title("Specific Fuel Oil Consumption")
    ax.legend(title="Generator")
    ax.set_xticks(df["timestep"].unique())


# ── Plot 3: Load-percentage heatmap ──────────────────────────────────────────
def plot_load_heatmap(df: pd.DataFrame, ax: plt.Axes):
    """Heatmap of generator utilisation (% of P_max) across timesteps."""
    pivot = df.pivot(index="generator", columns="timestep", values="load_pct")
    sns.heatmap(
        pivot, annot=True, fmt=".0f", cmap="YlOrRd",
        cbar_kws={"label": "Load [%]"}, linewidths=0.5,
        vmin=0, vmax=100, ax=ax,
    )
    ax.set_title("Generator Utilisation")
    ax.set_ylabel("Generator")
    ax.set_xlabel("Timestep")


# ── Plot 4: Total fuel consumption bar ────────────────────────────────────────
def plot_total_fuel(df: pd.DataFrame, ax: plt.Axes):
    """Bar chart of total fuel consumption (g/h) per timestep."""
    fuel = df.groupby("timestep")["fuel_gph"].sum()
    bars = ax.bar(fuel.index, fuel.values, edgecolor="white", linewidth=0.5)

    # Annotate bars
    for bar, val in zip(bars, fuel.values):
        ax.text(
            bar.get_x() + bar.get_width() / 2, bar.get_height(),
            f"{val / 1000:.1f}k", ha="center", va="bottom", fontsize=8,
        )

    ax.set_xlabel("Timestep")
    ax.set_ylabel("Fuel consumption [g/h]")
    ax.set_title("Total Fleet Fuel Consumption")
    ax.set_xticks(fuel.index)


# ── Plot 5: Commitment schedule (on/off heatmap) ─────────────────────────────
def plot_commitment(df: pd.DataFrame, ax: plt.Axes):
    """Binary heatmap of generator on/off status."""
    pivot = df.pivot(index="generator", columns="timestep", values="u")
    cmap = mcolors.ListedColormap(["#d3d3d3", "#2ecc71"])
    bounds = [-0.5, 0.5, 1.5]
    norm = mcolors.BoundaryNorm(bounds, cmap.N)

    sns.heatmap(
        pivot, annot=True, fmt=".0f", cmap=cmap, norm=norm,
        cbar=False, linewidths=1, linecolor="white", ax=ax,
    )
    ax.set_title("Commitment Schedule (1 = ON)")
    ax.set_ylabel("Generator")
    ax.set_xlabel("Timestep")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    sns.set_theme(style="whitegrid", context="notebook", palette="deep")

    df = load_data(CSV_PATH)

    fig, axes = plt.subplots(3, 2, figsize=(14, 14))
    fig.suptitle("Dispatch Optimisation Results", fontsize=16, y=0.98)

    plot_stacked_power(df, axes[0, 0])
    plot_sfoc(df, axes[0, 1])
    plot_load_heatmap(df, axes[1, 0])
    plot_total_fuel(df, axes[1, 1])
    plot_commitment(df, axes[2, 0])

    # Hide unused subplot
    axes[2, 1].set_visible(False)

    fig.tight_layout(rect=[0, 0, 1, 0.96])

    if SAVE:
        SAVE_DIR.mkdir(exist_ok=True)
        out = SAVE_DIR / "dispatch_results.png"
        fig.savefig(out, dpi=DPI, bbox_inches="tight")
        print(f"Saved to {out}")

    plt.show()


if __name__ == "__main__":
    main()
