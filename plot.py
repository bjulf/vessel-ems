"""
Dispatch results plotter.
Reads dispatch_results.csv and params.toml from a run directory.

Usage:
    python plot.py                           # uses current directory
    python plot.py runs/2026-03-17_soc35     # uses a specific run directory
"""

import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
import seaborn as sns
from pathlib import Path

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        raise ImportError("Python >= 3.11 required, or install tomli: pip install tomli")

# ── Constants ──────────────────────────────────────────────────────────────────
DPI  = 150
SAVE = True

COLORS = {
    "discharge": "#2ecc71",
    "charge":    "#9b59b6",
    "load":      "#e74c3c",
    "soc":       "#3498db",
}

# ── Day-axis helpers ───────────────────────────────────────────────────────────
_DAY_BOUNDARIES  = [24.5, 48.5, 72.5, 96.5]
_DAY_TICK_POS    = [12.5, 36.5, 60.5, 84.5, 98.5]
_DAY_TICK_LABELS = ["Day 1", "Day 2", "Day 3", "Day 4", "Day 5"]


def _add_day_markers(ax: plt.Axes) -> None:
    """Replace per-timestep x-ticks with day boundary markers on a time series axis."""
    for b in _DAY_BOUNDARIES:
        ax.axvline(b, color="lightgrey", lw=0.8, ls="--", zorder=0)
    ax.set_xticks(_DAY_TICK_POS)
    ax.set_xticklabels(_DAY_TICK_LABELS)
    ax.set_xlabel("")


def _format_heatmap_xaxis(ax: plt.Axes) -> None:
    """Replace per-cell x-ticks with day labels on a seaborn heatmap axis (100 timesteps)."""
    for x in [24, 48, 72, 96]:
        ax.axvline(x, color="white", lw=1.5)
    ax.set_xticks([12, 36, 60, 84, 98])
    ax.set_xticklabels(["Day 1", "Day 2", "Day 3", "Day 4", "Day 5"])
    ax.set_xlabel("")


# ── Data loading ───────────────────────────────────────────────────────────────
def _load_params(run_dir: Path) -> dict:
    with open(run_dir / "params.toml", "rb") as f:
        return tomllib.load(f)


def load_data(run_dir: Path) -> pd.DataFrame:
    df = pd.read_csv(run_dir / "dispatch_results.csv")
    df["generator"] = df["generator"].astype(str)
    return df


# ── Plot 1: Stacked bar – generator + battery power dispatch ───────────────────
def plot_stacked_power(df: pd.DataFrame, ax: plt.Axes) -> None:
    pivot = df.pivot(index="timestep", columns="generator", values="Pg_kw")
    ts = pivot.index.tolist()

    bottom = np.zeros(len(ts))
    colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    for i, col in enumerate(pivot.columns):
        ax.bar(ts, pivot[col].values, bottom=bottom, color=colors[i],
               edgecolor="white", linewidth=0.3, label=f"Gen {col}")
        bottom += pivot[col].values

    batt = df.groupby("timestep")[["P_dis_kw", "P_ch_kw"]].first()
    ax.bar(ts, batt["P_dis_kw"].values, bottom=bottom,
           color=COLORS["discharge"], edgecolor="white", linewidth=0.3,
           label="Batt discharge")
    ax.bar(ts, -batt["P_ch_kw"].values, color=COLORS["charge"],
           edgecolor="white", linewidth=0.3, label="Batt charge")

    load_vals = df.groupby("timestep")["load_kw"].first()
    ax.plot(ts, load_vals.values, color="black", lw=1.5, label="Load")

    ax.axhline(0, color="grey", lw=0.5)
    _add_day_markers(ax)
    ax.set_ylabel("Power [kW]")
    ax.set_title("Power Dispatch (Generators + Battery)")
    ax.legend(loc="upper left", fontsize=8)


# ── Plot 2: Commitment schedule ────────────────────────────────────────────────
def plot_commitment(df: pd.DataFrame, ax: plt.Axes) -> None:
    pivot = df.pivot(index="generator", columns="timestep", values="u")
    cmap  = mcolors.ListedColormap(["#d3d3d3", "#2ecc71"])
    norm  = mcolors.BoundaryNorm([-0.5, 0.5, 1.5], cmap.N)

    sns.heatmap(pivot, annot=False, cmap=cmap, norm=norm,
                cbar=False, linewidths=0, ax=ax)
    _format_heatmap_xaxis(ax)
    ax.set_title("Commitment Schedule")
    ax.set_ylabel("Generator")
    ax.legend(
        handles=[mpatches.Patch(facecolor="#2ecc71", label="ON"),
                 mpatches.Patch(facecolor="#d3d3d3", label="OFF")],
        loc="upper right", fontsize=8,
    )


# ── Plot 3: Generator utilisation heatmap ─────────────────────────────────────
def plot_load_heatmap(df: pd.DataFrame, ax: plt.Axes) -> None:
    pivot = df.pivot(index="generator", columns="timestep", values="load_pct")
    sns.heatmap(pivot, annot=False, cmap="YlOrRd",
                cbar_kws={"label": "Load [%]"}, linewidths=0,
                vmin=0, vmax=100, ax=ax)
    _format_heatmap_xaxis(ax)
    ax.set_title("Generator Utilisation [% of P_max]")
    ax.set_ylabel("Generator")


# ── Plot 4: SFOC ──────────────────────────────────────────────────────────────
def plot_sfoc(df: pd.DataFrame, ax: plt.Axes) -> None:
    for gen, grp in df.groupby("generator"):
        online = grp[grp["u"] == 1]
        ax.plot(online["timestep"], online["sfoc_gkwh"],
                lw=1.5, label=f"Gen {gen}")

    _add_day_markers(ax)
    ax.set_ylabel("SFOC [g/kWh]")
    ax.set_title("Specific Fuel Oil Consumption")
    ax.legend(title="Generator")


# ── Plot 5: Total fuel consumption ────────────────────────────────────────────
def plot_total_fuel(df: pd.DataFrame, ax: plt.Axes) -> None:
    fuel = df.groupby("timestep")["fuel_gph"].sum()
    ax.bar(fuel.index, fuel.values, edgecolor="white", linewidth=0.3)
    ax.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda v, _: f"{v/1000:.0f}k" if v >= 1000 else f"{v:.0f}")
    )
    _add_day_markers(ax)
    ax.set_ylabel("Fuel [g/h]")
    ax.set_title("Total Fleet Fuel Consumption")


# ── Plot 6: Battery operation (power + SOC) ───────────────────────────────────
def plot_battery(df: pd.DataFrame, ax: plt.Axes, soc_ref_pct: float) -> None:
    batt = df.groupby("timestep")[["P_ch_kw", "P_dis_kw", "soc_pct", "E_kwh"]].first()
    ts   = batt.index

    ax.bar(ts, batt["P_dis_kw"], color=COLORS["discharge"],
           edgecolor="white", linewidth=0.3, label="Discharge")
    ax.bar(ts, -batt["P_ch_kw"], color=COLORS["charge"],
           edgecolor="white", linewidth=0.3, label="Charge")
    ax.axhline(0, color="grey", lw=0.5)
    ax.set_ylabel("Power [kW]")
    ax.legend(loc="upper left", fontsize=8)
    _add_day_markers(ax)

    ax2  = ax.twinx()
    soc  = batt["soc_pct"]
    ekwh = batt["E_kwh"]

    ax2.plot(ts, soc, lw=2, color=COLORS["soc"], label="SOC")
    ax2.axhline(soc_ref_pct, color="#e67e22", lw=1.5, ls="--",
                label=f"SOC ref ({soc_ref_pct:.0f}%)", zorder=5)
    ax2.fill_between(ts, soc, soc_ref_pct,
                     where=(soc >= soc_ref_pct), alpha=0.18, color="#e67e22")
    ax2.fill_between(ts, soc, soc_ref_pct,
                     where=(soc <  soc_ref_pct), alpha=0.18, color="#c0392b")

    for t in {soc.idxmin(), soc.idxmax(), ts[-1]}:
        ax2.annotate(f"{ekwh[t]:.0f} kWh", (t, soc[t]),
                     textcoords="offset points", xytext=(0, 8),
                     ha="center", fontsize=7, color="#2471a3")

    ax2.set_ylabel("SOC [%]")
    ax2.set_ylim(0, 100)
    ax2.legend(loc="upper right", fontsize=8)
    ax.set_title("Battery Operation")


# ── Plot 7: SOC deviation analysis ────────────────────────────────────────────
def plot_soc_deviation(df: pd.DataFrame, ax: plt.Axes, soc_ref_pct: float) -> None:
    batt = df.groupby("timestep")["soc_pct"].first()
    ts   = batt.index
    dev  = (batt - soc_ref_pct).abs()

    norm   = plt.Normalize(vmin=0, vmax=dev.max() if dev.max() > 0 else 1)
    colors = [plt.cm.RdYlGn_r(norm(v)) for v in dev.values]

    ax.bar(ts, dev.values, color=colors, edgecolor="white", linewidth=0.3)
    ax.axhline(dev.mean(), color="steelblue", lw=1.5, ls="--",
               label=f"Mean ({dev.mean():.1f} pp)")
    _add_day_markers(ax)
    ax.set_ylabel("|SOC – SOC_ref| [pp]")
    ax.set_title(f"SOC Deviation from Reference ({soc_ref_pct:.0f}%)")
    ax.legend(loc="upper left", fontsize=8)

    t_max = dev.idxmax()
    ax.annotate(f"max\n{dev[t_max]:.1f} pp",
                xy=(t_max, dev[t_max]),
                xytext=(0, 6), textcoords="offset points",
                ha="center", fontsize=7, color="darkred")

    ax2 = ax.twinx()
    ax2.plot(ts, dev.cumsum().values, color="steelblue", lw=2)
    ax2.set_ylabel("Cumulative [pp]")


# ── Entry point ───────────────────────────────────────────────────────────────
def make_figures(run_dir: Path, show: bool = True):
    """Generate all figures for a run directory. Returns (fig1, fig2)."""
    params      = _load_params(run_dir)
    soc_ref_pct = params["battery"]["SOC_ref"] * 100.0
    df          = load_data(run_dir)

    sns.set_theme(style="whitegrid", context="notebook", palette="deep")

    # Figure 1: Timeseries — three wide panels, shared x-axis
    fig1 = plt.figure(figsize=(16, 15))
    gs1  = gridspec.GridSpec(3, 1, figure=fig1,
                             height_ratios=[2, 1.5, 1], hspace=0.08)
    ax_power  = fig1.add_subplot(gs1[0])
    ax_batt   = fig1.add_subplot(gs1[1], sharex=ax_power)
    ax_socdev = fig1.add_subplot(gs1[2], sharex=ax_power)
    fig1.suptitle("Dispatch Optimisation – Timeseries", fontsize=14)

    plot_stacked_power(df, ax_power)
    plot_battery(df, ax_batt, soc_ref_pct)
    plot_soc_deviation(df, ax_socdev, soc_ref_pct)

    plt.setp(ax_power.get_xticklabels(), visible=False)
    plt.setp(ax_batt.get_xticklabels(),  visible=False)
    fig1.tight_layout(rect=[0, 0, 1, 0.97])

    # Figure 2: Generator detail — 2×2 grid
    fig2 = plt.figure(figsize=(14, 10))
    gs2  = gridspec.GridSpec(2, 2, figure=fig2, hspace=0.45, wspace=0.35)
    ax_commit = fig2.add_subplot(gs2[0, 0])
    ax_util   = fig2.add_subplot(gs2[0, 1])
    ax_sfoc   = fig2.add_subplot(gs2[1, 0])
    ax_fuel   = fig2.add_subplot(gs2[1, 1])
    fig2.suptitle("Dispatch Optimisation – Generator Detail", fontsize=14)

    plot_commitment(df, ax_commit)
    plot_load_heatmap(df, ax_util)
    plot_sfoc(df, ax_sfoc)
    plot_total_fuel(df, ax_fuel)

    fig2.tight_layout(rect=[0, 0, 1, 0.97])

    if SAVE:
        save_dir = run_dir / "plots"
        save_dir.mkdir(exist_ok=True)
        fig1.savefig(save_dir / "dispatch_timeseries.png", dpi=DPI, bbox_inches="tight")
        fig2.savefig(save_dir / "dispatch_detail.png",     dpi=DPI, bbox_inches="tight")
        print(f"Saved → {save_dir / 'dispatch_timeseries.png'}")
        print(f"Saved → {save_dir / 'dispatch_detail.png'}")

    if show:
        plt.show()

    return fig1, fig2


def main():
    run_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent
    make_figures(run_dir, show=True)


if __name__ == "__main__":
    main()
