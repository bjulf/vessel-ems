import sys
import tomllib
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from plot_verification_case import (
    BASE_FONT,
    BOUND_COLOR,
    GEN_COLORS,
    REPO_ROOT,
    add_module_background,
    format_hour_axis,
    load_profile,
    merge_profile_labels,
    plots_dir,
)


ROLLING_LABEL = "Rolling horizon"
BENCHMARK_LABEL = "Offline full-horizon MILP"


def resolve_run_dir() -> Path:
    if len(sys.argv) > 1:
        return Path(sys.argv[1]).resolve()
    return Path((REPO_ROOT / ".current_run").read_text(encoding="utf-8").strip())


def load_params(run_dir: Path) -> dict:
    with open(run_dir / "params.toml", "rb") as fh:
        return tomllib.load(fh)


def load_dispatch_file(path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    dispatch = pd.read_csv(path)
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


def plot_power_balance(ax: plt.Axes, rolling: pd.DataFrame, benchmark: pd.DataFrame) -> None:
    add_module_background(ax, rolling)
    times = rolling["datetime"]

    ax.step(times, rolling["load_kw"], where="post", color="black", linewidth=2.2, label="Load")
    ax.step(
        times,
        rolling["total_gen_kw"],
        where="post",
        color="#2563EB",
        linewidth=2.0,
        label="Rolling total generation",
    )
    ax.step(
        times,
        benchmark["total_gen_kw"],
        where="post",
        color="#2563EB",
        linestyle="--",
        linewidth=2.0,
        label="Full-horizon total generation",
    )
    ax.step(
        times,
        rolling["battery_net_kw"],
        where="post",
        color="#DC2626",
        linewidth=1.7,
        alpha=0.85,
        label="Rolling battery net",
    )
    ax.step(
        times,
        benchmark["battery_net_kw"],
        where="post",
        color="#DC2626",
        linestyle="--",
        linewidth=1.7,
        alpha=0.85,
        label="Full-horizon battery net",
    )
    ax.axhline(0, color="#94A3B8", linewidth=0.8)
    ax.set_ylabel("Power [kW]", fontsize=BASE_FONT + 2)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(loc="upper left", ncol=2, fontsize=BASE_FONT - 2, frameon=True)
    ax.tick_params(axis="both", labelsize=BASE_FONT + 1)


def plot_generator_power(ax: plt.Axes, rolling_dispatch: pd.DataFrame, benchmark_dispatch: pd.DataFrame) -> None:
    rolling_pivot = rolling_dispatch.pivot(index="timestep", columns="generator", values="Pg_kw")
    benchmark_pivot = benchmark_dispatch.pivot(index="timestep", columns="generator", values="Pg_kw")
    times = rolling_dispatch.groupby("timestep")["datetime"].first().reset_index(drop=True)

    for generator in sorted(rolling_pivot.columns, key=int):
        color = GEN_COLORS.get(generator, "#334155")
        ax.step(
            times,
            rolling_pivot[generator].to_numpy(),
            where="post",
            color=color,
            linewidth=1.9,
            label=f"Gen {generator} rolling",
        )
        ax.step(
            times,
            benchmark_pivot[generator].to_numpy(),
            where="post",
            color=color,
            linestyle="--",
            linewidth=1.9,
            label=f"Gen {generator} full horizon",
        )

    ax.set_ylabel("Generator [kW]", fontsize=BASE_FONT + 2)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(loc="upper left", ncol=2, fontsize=BASE_FONT - 1, frameon=True)
    ax.tick_params(axis="both", labelsize=BASE_FONT + 1)


def plot_commitment(ax: plt.Axes, rolling_dispatch: pd.DataFrame, benchmark_dispatch: pd.DataFrame) -> None:
    times = rolling_dispatch.groupby("timestep")["datetime"].first().reset_index(drop=True)
    y_tracks = {
        ("1", "rolling"): 4,
        ("1", "benchmark"): 3,
        ("2", "rolling"): 2,
        ("2", "benchmark"): 1,
    }
    y_labels = {
        4: "G1 rolling",
        3: "G1 full",
        2: "G2 rolling",
        1: "G2 full",
    }

    for dispatch, mode, linestyle in [
        (rolling_dispatch, "rolling", "-"),
        (benchmark_dispatch, "benchmark", "--"),
    ]:
        for generator, grp in dispatch.groupby("generator"):
            grp = grp.sort_values("timestep")
            y_base = y_tracks[(generator, mode)]
            color = GEN_COLORS.get(generator, "#334155")
            ax.step(
                times,
                y_base + 0.35 * grp["u"].to_numpy(),
                where="post",
                color=color,
                linestyle=linestyle,
                linewidth=1.8,
            )
            starts = grp.loc[grp["startup"] > 0.5, "datetime"]
            if not starts.empty:
                ax.scatter(
                    starts,
                    [y_base + 0.50] * len(starts),
                    marker="^",
                    s=42,
                    color=color,
                    edgecolor="white",
                    linewidth=0.5,
                    zorder=5,
                )

    ax.set_yticks(list(y_labels.keys()), labels=[y_labels[y] for y in y_labels])
    ax.set_ylim(0.5, 4.8)
    ax.set_ylabel("Commitment", fontsize=BASE_FONT + 2)
    ax.grid(axis="y", alpha=0.20)
    ax.tick_params(axis="both", labelsize=BASE_FONT + 1)


def plot_soc(ax: plt.Axes, rolling: pd.DataFrame, benchmark: pd.DataFrame, params: dict) -> None:
    times = rolling["datetime"]
    ax.plot(times, rolling["soc_pct"], color="#2563EB", linewidth=2.2, label=ROLLING_LABEL)
    ax.plot(times, benchmark["soc_pct"], color="#111827", linestyle="--", linewidth=2.2, label=BENCHMARK_LABEL)
    ax.axhline(params["battery"]["SOC_min"] * 100.0, color=BOUND_COLOR, linestyle="--", linewidth=1.2, label="SOC min")
    ax.axhline(params["battery"]["SOC_max"] * 100.0, color=BOUND_COLOR, linestyle=":", linewidth=1.2, label="SOC max")
    ax.set_ylabel("SOC [%]", fontsize=BASE_FONT + 2)
    ax.set_ylim(0, 100)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(loc="upper right", fontsize=BASE_FONT - 1, frameon=True)
    ax.tick_params(axis="both", labelsize=BASE_FONT + 1)


def add_kpi_title(fig: plt.Figure, params: dict) -> None:
    rolling = params["kpis"]["rolling_horizon"]
    benchmark = params["kpis"]["full_horizon_benchmark"]
    comparison = params["kpis"]["comparison"]
    title = (
        f"Fuel: rolling {rolling['total_fuel_kg']:.3f} kg, "
        f"full horizon {benchmark['total_fuel_kg']:.3f} kg, "
        f"delta {comparison['fuel_delta_g'] / 1000.0:+.3f} kg "
        f"({comparison['fuel_delta_pct']:+.3f}%). "
        f"Starts: rolling {rolling['generator_starts']}, full horizon {benchmark['generator_starts']}."
    )
    fig.suptitle(title, x=0.01, ha="left", fontsize=BASE_FONT + 1, color="#0F172A")


def build_comparison_figure(run_dir: Path) -> Path:
    params = load_params(run_dir)
    profile = load_profile(Path(params["load_profile"]["source_file"]))

    rolling_dispatch, rolling_wide = load_dispatch_file(run_dir / "dispatch_results.csv")
    benchmark_dispatch, benchmark_wide = load_dispatch_file(run_dir / "full_horizon_benchmark_dispatch_results.csv")
    rolling_wide = merge_profile_labels(rolling_wide, profile)
    benchmark_wide = merge_profile_labels(benchmark_wide, profile)

    fig, axes = plt.subplots(
        4,
        1,
        figsize=(16, 13.2),
        sharex=True,
        constrained_layout=True,
        gridspec_kw={"height_ratios": [2.4, 2.0, 1.2, 1.4], "hspace": 0.07},
    )
    add_kpi_title(fig, params)
    plot_power_balance(axes[0], rolling_wide, benchmark_wide)
    plot_generator_power(axes[1], rolling_dispatch, benchmark_dispatch)
    plot_commitment(axes[2], rolling_dispatch, benchmark_dispatch)
    plot_soc(axes[3], rolling_wide, benchmark_wide, params)
    format_hour_axis(axes[3], rolling_wide["datetime"], major_hours=2)

    out_path = plots_dir(run_dir) / "rolling_vs_full_horizon_comparison.png"
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return out_path


def main() -> None:
    run_dir = resolve_run_dir()
    out_path = build_comparison_figure(run_dir)
    print(f"Saved {out_path}")


if __name__ == "__main__":
    main()
