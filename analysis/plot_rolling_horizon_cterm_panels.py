from __future__ import annotations

import argparse
import tomllib
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SWEEP_DIR = REPO_ROOT / "analysis" / "output" / "rolling_horizon" / "operational_reserve_tuning"

GEN_COLORS = {
    "1": "#4C78A8",
    "2": "#F58518",
}
BATTERY_DISCHARGE = "#D62728"
BATTERY_CHARGE = "#2CA02C"
SOC_COLOR = "#2F6DB3"
SLACK_COLOR = "#7C2D12"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create full dispatch panel plots for the fixed-terminal-target C_term rolling-horizon sweep."
    )
    parser.add_argument(
        "sweep_dir",
        nargs="?",
        default=str(DEFAULT_SWEEP_DIR),
        help="Rolling-horizon sensitivity output directory.",
    )
    return parser.parse_args()


def load_dispatch(run_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    dispatch = pd.read_csv(run_dir / "dispatch_results.csv")
    dispatch["datetime"] = pd.to_datetime(dispatch["datetime"])
    dispatch["generator"] = dispatch["generator"].astype(str)
    wide = (
        dispatch.groupby("timestep")
        .agg(
            datetime=("datetime", "first"),
            load_kw=("load_kw", "first"),
            P_ch_kw=("P_ch_kw", "first"),
            P_dis_kw=("P_dis_kw", "first"),
            E_kwh=("E_kwh", "first"),
            soc_pct=("soc_pct", "first"),
            total_gen_kw=("Pg_kw", "sum"),
        )
        .reset_index()
    )
    wide["battery_net_kw"] = wide["P_dis_kw"] - wide["P_ch_kw"]
    return dispatch, wide


def soc_trajectory(wide: pd.DataFrame, params: dict) -> pd.DataFrame:
    battery = params["battery"]
    dt = float(battery["dt"])
    eta_ch = float(battery["eta_ch"])
    eta_dis = float(battery["eta_dis"])
    e_cap = float(battery["E_cap"])
    step = wide["datetime"].iloc[1] - wide["datetime"].iloc[0]

    terminal_e = wide["E_kwh"].iloc[-1] + dt * (
        eta_ch * wide["P_ch_kw"].iloc[-1] -
        (1.0 / eta_dis) * wide["P_dis_kw"].iloc[-1]
    )
    times = list(wide["datetime"]) + [wide["datetime"].iloc[-1] + step]
    energies = list(wide["E_kwh"]) + [terminal_e]
    return pd.DataFrame(
        {
            "datetime": times,
            "E_kwh": energies,
            "soc_pct": [energy / e_cap * 100.0 for energy in energies],
        }
    )


def plot_power_panel(ax: plt.Axes, dispatch: pd.DataFrame, wide: pd.DataFrame) -> None:
    times = wide["datetime"]
    ax.step(times, wide["load_kw"], where="post", color="black", linewidth=2.0, label="Load")

    gen_pivot = dispatch.pivot(index="timestep", columns="generator", values="Pg_kw")
    for generator in sorted(gen_pivot.columns, key=int):
        ax.step(
            times,
            gen_pivot[generator].to_numpy(),
            where="post",
            linewidth=1.7,
            color=GEN_COLORS.get(generator, "#334155"),
            label=f"Gen {generator}",
        )

    ax.fill_between(
        times,
        0,
        wide["battery_net_kw"].clip(lower=0.0),
        step="post",
        color=BATTERY_DISCHARGE,
        alpha=0.32,
        label="Battery discharge",
    )
    ax.fill_between(
        times,
        0,
        wide["battery_net_kw"].clip(upper=0.0),
        step="post",
        color=BATTERY_CHARGE,
        alpha=0.32,
        label="Battery charge",
    )
    ax.axhline(0.0, color="#94A3B8", linewidth=0.8)
    ax.set_ylabel("Power [kW]", fontsize=13)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(loc="upper left", ncol=3, fontsize=10)


def plot_commitment_panel(ax: plt.Axes, dispatch: pd.DataFrame, wide: pd.DataFrame) -> None:
    times = wide["datetime"]
    for idx, (generator, grp) in enumerate(dispatch.groupby("generator"), start=1):
        grp = grp.sort_values("timestep")
        on = grp["u"].to_numpy() > 0.5
        color = GEN_COLORS.get(generator, "#334155")
        ax.fill_between(
            times,
            idx - 0.32,
            idx + 0.32,
            where=on,
            step="post",
            color=color,
            alpha=0.60,
        )
        starts = grp[grp["startup"] > 0.5]["datetime"]
        if not starts.empty:
            ax.scatter(
                starts,
                [idx + 0.42] * len(starts),
                marker="^",
                s=42,
                color=color,
                edgecolor="white",
                linewidth=0.5,
                zorder=5,
            )
    ax.set_yticks([1, 2], labels=["Gen 1", "Gen 2"])
    ax.set_ylim(0.4, 2.75)
    ax.set_ylabel("Unit", fontsize=13)
    ax.grid(axis="y", alpha=0.20)


def plot_soc_panel(ax: plt.Axes, soc: pd.DataFrame, params: dict) -> None:
    battery = params["battery"]
    rolling = params["rolling_horizon"]
    soc_min = float(battery["SOC_min"]) * 100.0
    soc_max = float(battery["SOC_max"]) * 100.0
    terminal_target = float(rolling["terminal_soc_target"]) * 100.0

    ax.step(soc["datetime"], soc["soc_pct"], where="post", color=SOC_COLOR, linewidth=2.0)
    ax.axhline(soc_min, color="#64748B", linestyle="--", linewidth=1.1, label="SOC min")
    ax.axhline(soc_max, color="#64748B", linestyle=":", linewidth=1.1, label="SOC max")
    ax.axhline(
        terminal_target,
        color="#7C3AED",
        linestyle="-.",
        linewidth=1.2,
        label="Local terminal target",
    )
    ax.set_ylabel("SOC [%]", fontsize=13)
    ax.set_ylim(0, 100)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(loc="upper left", ncol=3, fontsize=10)


def plot_slack_panel(ax: plt.Axes, local_solves: pd.DataFrame) -> None:
    local_solves["datetime"] = pd.to_datetime(local_solves["datetime"])
    total_slack = local_solves["terminal_slack_kwh"].sum()
    max_slack = local_solves["terminal_slack_kwh"].max()
    ax.fill_between(
        local_solves["datetime"],
        0,
        local_solves["terminal_slack_kwh"],
        step="post",
        color=SLACK_COLOR,
        alpha=0.35,
    )
    ax.step(
        local_solves["datetime"],
        local_solves["terminal_slack_kwh"],
        where="post",
        color=SLACK_COLOR,
        linewidth=1.6,
    )
    ax.set_ylabel("Slack [kWh]", fontsize=13)
    ax.set_xlabel("Time", fontsize=13)
    ax.grid(axis="y", alpha=0.25)
    ax.text(
        0.99,
        0.86,
        f"sum = {total_slack:.1f} kWh\nmax = {max_slack:.1f} kWh",
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=11,
        bbox={"boxstyle": "round,pad=0.25", "facecolor": "white", "edgecolor": "#CBD5E1"},
    )


def plot_case(row: pd.Series, output_dir: Path) -> Path:
    run_dir = Path(row["run_dir"])
    with open(run_dir / "params.toml", "rb") as fh:
        params = tomllib.load(fh)
    dispatch, wide = load_dispatch(run_dir)
    soc = soc_trajectory(wide, params)
    local_solves = pd.read_csv(run_dir / "rolling_local_solves.csv")

    c_term = float(row["c_term_g_per_kwh"])
    target_pct = float(row["terminal_soc_target_pct"])
    fig, axes = plt.subplots(
        4,
        1,
        figsize=(16, 12.5),
        sharex=True,
        constrained_layout=True,
        gridspec_kw={"height_ratios": [3.0, 0.8, 1.2, 1.0]},
    )

    plot_power_panel(axes[0], dispatch, wide)
    plot_commitment_panel(axes[1], dispatch, wide)
    plot_soc_panel(axes[2], soc, params)
    plot_slack_panel(axes[3], local_solves)

    kpis = params["kpis"]["rolling_horizon"]
    fig.suptitle(
        f"Operational rolling-horizon MILP, terminal target {target_pct:.0f}%, "
        f"C_term {c_term:.0f} g/kWh\n"
        f"Fuel {kpis['total_fuel_kg']:.1f} kg, starts {int(kpis['generator_starts'])}, "
        f"min SOC {kpis['minimum_soc_pct']:.1f}%, final SOC {kpis['final_soc_pct']:.1f}%",
        fontsize=16,
        fontweight="bold",
    )

    path = output_dir / f"dispatch_panel_terminal{target_pct:.0f}_cterm_{c_term:.0f}.png"
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return path


def main() -> None:
    args = parse_args()
    sweep_dir = Path(args.sweep_dir).resolve()
    summary_path = sweep_dir / "cterm_sweep_terminal50.csv"
    if not summary_path.exists():
        raise FileNotFoundError(f"Missing fixed-target C_term sweep summary: {summary_path}")

    output_dir = sweep_dir / "cterm_dispatch_panels"
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = pd.read_csv(summary_path)
    paths = [plot_case(row, output_dir) for _, row in rows.iterrows()]
    for path in paths:
        print(f"Saved {path}")


if __name__ == "__main__":
    main()
