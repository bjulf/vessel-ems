from __future__ import annotations

import argparse
import tomllib
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]

GEN_COLORS = {
    "1": "#4C78A8",
    "2": "#F58518",
}
BATTERY_DISCHARGE = "#D62728"
BATTERY_CHARGE = "#2CA02C"
SOC_COLOR = "#2F6DB3"
SLACK_COLOR = "#7C2D12"
FORECAST_COLOR = "#0F766E"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a run-local rolling-horizon dispatch panel plot."
    )
    parser.add_argument("run_dirs", nargs="+", help="Run directories to plot.")
    return parser.parse_args()


def resolve_run_dir(path: str) -> Path:
    run_dir = Path(path)
    if not run_dir.is_absolute():
        run_dir = REPO_ROOT / run_dir
    return run_dir.resolve()


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
        eta_ch * wide["P_ch_kw"].iloc[-1] - (1.0 / eta_dis) * wide["P_dis_kw"].iloc[-1]
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
    rolling = params.get("rolling_horizon", {})
    soft_soc = params.get("soft_soc")
    soc_min = float(battery["SOC_min"]) * 100.0
    soc_max = float(battery["SOC_max"]) * 100.0

    ax.step(soc["datetime"], soc["soc_pct"], where="post", color=SOC_COLOR, linewidth=2.0)
    ax.axhline(soc_min, color="#64748B", linestyle="--", linewidth=1.1, label="Physical SOC min")
    ax.axhline(soc_max, color="#64748B", linestyle=":", linewidth=1.1, label="Physical SOC max")

    if soft_soc:
        ax.axhline(
            float(soft_soc["preferred_soc_min"]) * 100.0,
            color="#7C3AED",
            linestyle="-.",
            linewidth=1.2,
            label="Preferred SOC min",
        )
        ax.axhline(
            float(soft_soc["preferred_soc_max"]) * 100.0,
            color="#7C3AED",
            linestyle=(0, (3, 2, 1, 2)),
            linewidth=1.2,
            label="Preferred SOC max",
        )
    elif "terminal_soc_target" in rolling:
        ax.axhline(
            float(rolling["terminal_soc_target"]) * 100.0,
            color="#7C3AED",
            linestyle="-.",
            linewidth=1.2,
            label="Local terminal target",
        )

    ax.set_ylabel("SOC [%]", fontsize=13)
    ax.set_ylim(0, 100)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(loc="upper left", ncol=3, fontsize=10)


def plot_local_diagnostics(ax: plt.Axes, local_solves: pd.DataFrame) -> None:
    local_solves["datetime"] = pd.to_datetime(local_solves["datetime"])

    if "terminal_slack_kwh" in local_solves.columns:
        series = local_solves["terminal_slack_kwh"]
        label = "Terminal slack"
        ylabel = "Slack [kWh]"
    elif "local_soc_min_slack_sum_kwh" in local_solves.columns:
        series = (
            local_solves["local_soc_min_slack_sum_kwh"]
            + local_solves["local_soc_max_slack_sum_kwh"]
        )
        label = "SOC-band slack"
        ylabel = "Slack [kWh]"
    else:
        series = pd.Series([0.0] * len(local_solves))
        label = "Local slack"
        ylabel = "Slack [kWh]"

    ax.fill_between(
        local_solves["datetime"],
        0,
        series,
        step="post",
        color=SLACK_COLOR,
        alpha=0.35,
    )
    ax.step(local_solves["datetime"], series, where="post", color=SLACK_COLOR, linewidth=1.6)
    ax.set_ylabel(ylabel, fontsize=13)
    ax.grid(axis="y", alpha=0.25)
    ax.text(
        0.99,
        0.86,
        f"{label}\nsum = {series.sum():.1f} kWh\nmax = {series.max():.1f} kWh",
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=11,
        bbox={"boxstyle": "round,pad=0.25", "facecolor": "white", "edgecolor": "#CBD5E1"},
    )


def plot_forecast_panel(ax: plt.Axes, local_solves: pd.DataFrame) -> None:
    local_solves["datetime"] = pd.to_datetime(local_solves["datetime"])
    ax.step(
        local_solves["datetime"],
        local_solves["realized_load_kw"],
        where="post",
        color="black",
        linewidth=1.8,
        label="Realized load",
    )
    if "forecast_first_load_kw" in local_solves.columns:
        ax.step(
            local_solves["datetime"],
            local_solves["forecast_first_load_kw"],
            where="post",
            color=FORECAST_COLOR,
            linewidth=1.5,
            label="Forecast first step",
        )
    if "forecast_mean_load_kw" in local_solves.columns:
        ax.step(
            local_solves["datetime"],
            local_solves["forecast_mean_load_kw"],
            where="post",
            color="#9333EA",
            linewidth=1.2,
            alpha=0.85,
            label="Forecast horizon mean",
        )
    ax.set_ylabel("Load [kW]", fontsize=13)
    ax.set_xlabel("Time", fontsize=13)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(loc="upper left", ncol=3, fontsize=10)


def rolling_kpis(params: dict) -> dict:
    kpis = params["kpis"]
    if "rolling_horizon_soft_soc" in kpis:
        return kpis["rolling_horizon_soft_soc"]
    return kpis["rolling_horizon"]


def plot_run(run_dir: Path) -> Path:
    required = ["params.toml", "dispatch_results.csv", "rolling_local_solves.csv"]
    missing = [name for name in required if not (run_dir / name).exists()]
    if missing:
        raise FileNotFoundError(f"{run_dir} is missing required files: {', '.join(missing)}")

    with open(run_dir / "params.toml", "rb") as fh:
        params = tomllib.load(fh)
    dispatch, wide = load_dispatch(run_dir)
    soc = soc_trajectory(wide, params)
    local_solves = pd.read_csv(run_dir / "rolling_local_solves.csv")
    if "realized_load_kw" not in local_solves.columns:
        local_solves["realized_load_kw"] = wide["load_kw"].to_numpy()

    fig, axes = plt.subplots(
        5,
        1,
        figsize=(16, 14.5),
        sharex=True,
        constrained_layout=True,
        gridspec_kw={"height_ratios": [3.0, 0.8, 1.2, 1.0, 1.0]},
    )
    plot_power_panel(axes[0], dispatch, wide)
    plot_commitment_panel(axes[1], dispatch, wide)
    plot_soc_panel(axes[2], soc, params)
    plot_local_diagnostics(axes[3], local_solves)
    plot_forecast_panel(axes[4], local_solves)

    kpis = rolling_kpis(params)
    run = params["run"]
    rolling = params.get("rolling_horizon", {})
    forecast_method = rolling.get("forecast_method", "not recorded")
    min_up_steps = rolling.get("min_up_time_steps", 1)
    terminal_reserve = rolling.get("soft_band_terminal_reserve_enabled", False)
    controller_notes = [f"forecast {forecast_method}", f"min-up {min_up_steps} steps"]
    if terminal_reserve:
        controller_notes.append(f"terminal reserve {float(rolling.get('terminal_soc_target', 0.0)) * 100:.0f}%")
    fig.suptitle(
        f"{run['label']}\n"
        f"Fuel {kpis['total_fuel_kg']:.1f} kg, starts {int(kpis['generator_starts'])}, "
        f"min SOC {kpis['minimum_soc_pct']:.1f}%, final SOC {kpis['final_soc_pct']:.1f}%, "
        f"{', '.join(controller_notes)}",
        fontsize=16,
        fontweight="bold",
    )

    output_dir = run_dir / "plots"
    output_dir.mkdir(exist_ok=True)
    out_path = output_dir / "rolling_horizon_dispatch_panel.png"
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return out_path


def main() -> None:
    args = parse_args()
    for run_arg in args.run_dirs:
        path = plot_run(resolve_run_dir(run_arg))
        print(f"Saved {path}")


if __name__ == "__main__":
    main()
