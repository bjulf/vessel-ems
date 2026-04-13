"""
Dispatch results plotter.
Reads dispatch_results.csv and params.toml from a run directory.

Usage:
    python plot.py
    python plot.py runs/2026-04-13_120000_
"""

import sys
from pathlib import Path

import matplotlib.colors as mcolors
import matplotlib.dates as mdates
import matplotlib.gridspec as gridspec
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


DPI = 150
SAVE = True

COLORS = {
    "discharge": "#2ecc71",
    "charge": "#9b59b6",
    "load": "#e74c3c",
    "soc": "#3498db",
}


def _midnight_boundaries(times: pd.DatetimeIndex):
    dates = times.normalize()
    changes = np.where(np.diff(dates.view("int64")) > 0)[0] + 1
    return times[changes]


def _add_day_markers(ax: plt.Axes, times: pd.DatetimeIndex) -> None:
    boundaries = _midnight_boundaries(times)
    for boundary in boundaries:
        ax.axvline(boundary, color="lightgrey", lw=0.8, ls="--", zorder=0)

    ax.xaxis.set_major_locator(mdates.DayLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax.xaxis.set_minor_locator(mdates.HourLocator(byhour=[6, 12, 18]))
    ax.tick_params(axis="x", which="minor", length=3)
    ax.set_xlabel("")


def _format_heatmap_xaxis(ax: plt.Axes, df: pd.DataFrame) -> None:
    times = df.groupby("timestep")["datetime"].first()
    dates = times.dt.normalize()
    changes = np.where(np.diff(dates.values.astype("int64")) > 0)[0] + 1

    for x in changes:
        ax.axvline(x, color="white", lw=1.5)

    boundaries = np.concatenate([[0], changes, [len(times)]])
    tick_pos = [(boundaries[i] + boundaries[i + 1]) / 2 for i in range(len(boundaries) - 1)]
    tick_labels = [f"Day {i + 1}" for i in range(len(tick_pos))]
    ax.set_xticks(tick_pos)
    ax.set_xticklabels(tick_labels)
    ax.set_xlabel("")


def load_data(run_dir: Path) -> pd.DataFrame:
    df = pd.read_csv(run_dir / "dispatch_results.csv")
    df["generator"] = df["generator"].astype(str)
    if "datetime" in df.columns:
        df["datetime"] = pd.to_datetime(df["datetime"])
    else:
        dt_h = 1.0
        t0 = pd.Timestamp("2000-01-01")
        df["datetime"] = t0 + pd.to_timedelta((df["timestep"] - 1) * dt_h, unit="h")
    return df


def plot_stacked_power(df: pd.DataFrame, ax: plt.Axes) -> None:
    wide = df.groupby("timestep").agg(
        datetime=("datetime", "first"),
        load_kw=("load_kw", "first"),
        P_dis_kw=("P_dis_kw", "first"),
    ).reset_index()

    gen_pivot = df.pivot(index="timestep", columns="generator", values="Pg_kw")
    times = wide["datetime"].values

    colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    gen_arrays = [gen_pivot[col].values for col in gen_pivot.columns]
    labels = [f"Gen {col}" for col in gen_pivot.columns]
    stack_arrays = gen_arrays + [wide["P_dis_kw"].values]
    stack_labels = labels + ["Batt discharge"]
    stack_colors = colors[: len(gen_arrays)] + [COLORS["discharge"]]
    ax.stackplot(times, *stack_arrays, labels=stack_labels, colors=stack_colors, alpha=0.85)

    ax.step(times, wide["load_kw"].values, where="post", color="black", lw=1.5, label="Load")

    ax.set_ylim(bottom=0)
    _add_day_markers(ax, pd.DatetimeIndex(times))
    ax.set_ylabel("Power [kW]")
    ax.set_title("Power Dispatch (Generators + Battery discharge)")
    ax.legend(loc="upper left", fontsize=8)


def plot_commitment(df: pd.DataFrame, ax: plt.Axes) -> None:
    pivot = df.pivot(index="generator", columns="timestep", values="u")
    cmap = mcolors.ListedColormap(["#d3d3d3", "#2ecc71"])
    norm = mcolors.BoundaryNorm([-0.5, 0.5, 1.5], cmap.N)

    sns.heatmap(pivot, annot=False, cmap=cmap, norm=norm, cbar=False, linewidths=0, ax=ax)
    _format_heatmap_xaxis(ax, df)
    ax.set_title("Commitment Schedule")
    ax.set_ylabel("Generator")
    ax.legend(
        handles=[
            mpatches.Patch(facecolor="#2ecc71", label="ON"),
            mpatches.Patch(facecolor="#d3d3d3", label="OFF"),
        ],
        loc="upper right",
        fontsize=8,
    )


def plot_load_heatmap(df: pd.DataFrame, ax: plt.Axes) -> None:
    pivot = df.pivot(index="generator", columns="timestep", values="load_pct")
    sns.heatmap(
        pivot,
        annot=False,
        cmap="YlOrRd",
        cbar_kws={"label": "Load [%]"},
        linewidths=0,
        vmin=0,
        vmax=100,
        ax=ax,
    )
    _format_heatmap_xaxis(ax, df)
    ax.set_title("Generator Utilisation [% of P_max]")
    ax.set_ylabel("Generator")


def plot_sfoc(df: pd.DataFrame, ax: plt.Axes) -> None:
    for gen, grp in df.groupby("generator"):
        online = grp[grp["u"] == 1]
        ax.plot(online["datetime"], online["sfoc_gkwh"], lw=1.5, label=f"Gen {gen}")

    times = pd.DatetimeIndex(df["datetime"].unique())
    _add_day_markers(ax, times)
    ax.set_ylabel("SFOC [g/kWh]")
    ax.set_title("Specific Fuel Oil Consumption")
    ax.legend(title="Generator")


def plot_total_fuel(df: pd.DataFrame, ax: plt.Axes) -> None:
    wide = df.groupby("timestep").agg(
        datetime=("datetime", "first"),
        total_fuel=("fuel_gph", "sum"),
    ).reset_index()

    times = wide["datetime"].values
    ax.fill_between(times, 0, wide["total_fuel"].values, step="post", alpha=0.8)
    ax.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda v, _: f"{v/1000:.0f}k" if v >= 1000 else f"{v:.0f}")
    )
    _add_day_markers(ax, pd.DatetimeIndex(times))
    ax.set_ylabel("Fuel rate [g/h]")
    ax.set_title("Total Fleet Fuel Consumption")


def plot_battery(df: pd.DataFrame, ax: plt.Axes) -> None:
    batt = df.groupby("timestep").agg(
        datetime=("datetime", "first"),
        P_ch_kw=("P_ch_kw", "first"),
        P_dis_kw=("P_dis_kw", "first"),
        soc_pct=("soc_pct", "first"),
        E_kwh=("E_kwh", "first"),
    ).reset_index()

    times = batt["datetime"].values

    ax.fill_between(
        times,
        0,
        batt["P_dis_kw"].values,
        step="post",
        color=COLORS["discharge"],
        alpha=0.75,
        label="Discharge",
    )
    ax.fill_between(
        times,
        0,
        -batt["P_ch_kw"].values,
        step="post",
        color=COLORS["charge"],
        alpha=0.75,
        label="Charge",
    )
    ax.axhline(0, color="grey", lw=0.5)
    ax.set_ylabel("Power [kW]")
    ax.legend(loc="upper left", fontsize=8)
    _add_day_markers(ax, pd.DatetimeIndex(times))

    ax2 = ax.twinx()
    soc = batt["soc_pct"]
    ekwh = batt["E_kwh"]
    ax2.plot(times, soc.values, lw=2, color=COLORS["soc"], label="SOC")

    for idx in {soc.idxmin(), soc.idxmax(), soc.index[-1]}:
        ax2.annotate(
            f"{ekwh[idx]:.0f} kWh",
            (times[batt.index.get_loc(idx)], soc[idx]),
            textcoords="offset points",
            xytext=(0, 8),
            ha="center",
            fontsize=7,
            color="#2471a3",
        )

    ax2.set_ylabel("SOC [%]")
    ax2.set_ylim(0, 100)
    ax2.legend(loc="upper right", fontsize=8)
    ax.set_title("Battery Operation")


def make_figures(run_dir: Path, show: bool = True):
    df = load_data(run_dir)

    sns.set_theme(style="whitegrid", context="notebook", palette="deep")

    fig1 = plt.figure(figsize=(16, 10))
    gs1 = gridspec.GridSpec(2, 1, figure=fig1, height_ratios=[2, 1.5], hspace=0.08)
    ax_power = fig1.add_subplot(gs1[0])
    ax_batt = fig1.add_subplot(gs1[1], sharex=ax_power)
    fig1.suptitle("Dispatch Optimisation - Timeseries", fontsize=14)

    plot_stacked_power(df, ax_power)
    plot_battery(df, ax_batt)

    plt.setp(ax_power.get_xticklabels(), visible=False)
    fig1.tight_layout(rect=[0, 0, 1, 0.97])

    fig2 = plt.figure(figsize=(14, 10))
    gs2 = gridspec.GridSpec(2, 2, figure=fig2, hspace=0.45, wspace=0.35)
    ax_commit = fig2.add_subplot(gs2[0, 0])
    ax_util = fig2.add_subplot(gs2[0, 1])
    ax_sfoc = fig2.add_subplot(gs2[1, 0])
    ax_fuel = fig2.add_subplot(gs2[1, 1])
    fig2.suptitle("Dispatch Optimisation - Generator Detail", fontsize=14)

    plot_commitment(df, ax_commit)
    plot_load_heatmap(df, ax_util)
    plot_sfoc(df, ax_sfoc)
    plot_total_fuel(df, ax_fuel)

    fig2.tight_layout(rect=[0, 0, 1, 0.97])

    if SAVE:
        save_dir = run_dir / "plots"
        save_dir.mkdir(exist_ok=True)
        fig1.savefig(save_dir / "dispatch_timeseries.png", dpi=DPI, bbox_inches="tight")
        fig2.savefig(save_dir / "dispatch_detail.png", dpi=DPI, bbox_inches="tight")
        print(f"Saved -> {save_dir / 'dispatch_timeseries.png'}")
        print(f"Saved -> {save_dir / 'dispatch_detail.png'}")

    if show:
        plt.show()

    return fig1, fig2


def main():
    run_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent
    make_figures(run_dir, show=True)


if __name__ == "__main__":
    main()
