from __future__ import annotations

import sys
import tomllib
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO_ROOT / "analysis" / "output" / "verification"
BASE_FONT = 13
LABEL_FONT = 15

GEN_COLORS = {
    "1": "#4C78A8",
    "2": "#F58518",
}

MODULE_COLORS = {
    "harbor_hotel": "#4C78A8",
    "aux_work": "#72B7B2",
    "transit": "#54A24B",
    "maneuvering": "#F2A541",
    "load_transients": "#9C755F",
    "high_transient": "#E45756",
    "severe_load_transients": "#B279A2",
}

BATTERY_DISCHARGE = "#D62728"
BATTERY_CHARGE = "#2CA02C"
SOC_COLOR = "#2F6DB3"
BOUND_COLOR = "#64748B"


def resolve_run_dir() -> Path:
    if len(sys.argv) > 1:
        return Path(sys.argv[1]).resolve()
    return Path((REPO_ROOT / ".current_run").read_text(encoding="utf-8").strip())


def load_params(run_dir: Path) -> dict:
    with open(run_dir / "params.toml", "rb") as fh:
        return tomllib.load(fh)


def load_profile(profile_path: Path) -> pd.DataFrame:
    df = pd.read_csv(profile_path)
    df["datetime"] = pd.to_datetime(df["datetime"])
    return df


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
    wide["power_balance_residual_kw"] = (
        wide["total_gen_kw"] + wide["P_dis_kw"] - wide["P_ch_kw"] - wide["load_kw"]
    )
    return dispatch, wide


def merge_profile_labels(wide: pd.DataFrame, profile: pd.DataFrame) -> pd.DataFrame:
    label_cols = ["timestep", "module", "module_label"]
    available = [col for col in label_cols if col in profile.columns]
    if available == ["timestep"]:
        return wide.copy()
    return wide.merge(profile[available].drop_duplicates(), on="timestep", how="left")


def module_spans(df: pd.DataFrame) -> list[tuple[int, int, str, str]]:
    if "module" not in df.columns or df["module"].isna().all():
        return []

    spans: list[tuple[int, int, str, str]] = []
    start = 0
    modules = df["module"].fillna("").tolist()
    labels = df.get("module_label", pd.Series([""] * len(df))).fillna("").tolist()

    while start < len(df):
        end = start + 1
        while end < len(df) and modules[end] == modules[start]:
            end += 1
        spans.append((start, end - 1, modules[start], labels[start] or modules[start]))
        start = end

    return spans


def add_module_background(ax: plt.Axes, df: pd.DataFrame, alpha: float = 0.11) -> None:
    times = df["datetime"].reset_index(drop=True)
    for start, end, module, _ in module_spans(df):
        color = MODULE_COLORS.get(module, "#CBD5E1")
        x0 = times.iloc[start]
        x1 = times.iloc[end] + (times.iloc[1] - times.iloc[0])
        ax.axvspan(x0, x1, color=color, alpha=alpha, linewidth=0)


def add_module_labels(ax: plt.Axes, df: pd.DataFrame, y: float) -> None:
    times = df["datetime"].reset_index(drop=True)
    spans = module_spans(df)
    label_y_scale = {
        "harbor_hotel": 0.98,
        "aux_work": 0.98,
        "transit": 0.98,
        "maneuvering": 0.98,
        "load_transients": 0.98,
        "high_transient": 0.86,
        "severe_load_transients": 0.98,
    }
    for idx, (start, end, module, label) in enumerate(spans):
        color = MODULE_COLORS.get(module, "#CBD5E1")
        x0 = times.iloc[start]
        x1 = times.iloc[end] + (times.iloc[1] - times.iloc[0])
        midpoint = x0 + (x1 - x0) / 2
        y_pos = y * label_y_scale.get(module, 0.98)
        ax.text(
            midpoint,
            y_pos,
            label,
            ha="center",
            va="center",
            fontsize=LABEL_FONT,
            color="#0F172A",
            bbox={
                "boxstyle": "round,pad=0.30",
                "facecolor": "white",
                "edgecolor": color,
                "linewidth": 1.2,
                "alpha": 0.92,
            },
            zorder=6,
        )


def format_hour_axis(ax: plt.Axes, times: pd.Series, major_hours: int = 2) -> None:
    start = times.iloc[0]
    end = times.iloc[-1] + (times.iloc[1] - times.iloc[0] if len(times) > 1 else pd.Timedelta(minutes=15))
    total_hours = int(round((end - start).total_seconds() / 3600.0))
    tick_hours = list(range(0, total_hours + 1, major_hours))
    tick_positions = [start + pd.Timedelta(hours=hour) for hour in tick_hours]
    ax.set_xticks(tick_positions)
    ax.set_xticklabels([str(hour) for hour in tick_hours], fontsize=BASE_FONT + 1)
    ax.tick_params(axis="x", labelrotation=0)
    ax.set_xlabel("Hour", fontsize=BASE_FONT + 2)


def plot_power_panel(ax: plt.Axes, wide: pd.DataFrame, dispatch: pd.DataFrame, show_labels: bool) -> None:
    add_module_background(ax, wide)
    times = wide["datetime"]

    ax.step(times, wide["load_kw"], where="post", color="black", linewidth=2.2, label="Load")

    gen_pivot = dispatch.pivot(index="timestep", columns="generator", values="Pg_kw")
    for generator in sorted(gen_pivot.columns, key=int):
        ax.step(
            times,
            gen_pivot[generator].to_numpy(),
            where="post",
            linewidth=1.8,
            color=GEN_COLORS.get(generator, "#334155"),
            label=f"Gen {generator}",
        )

    battery_net = wide["battery_net_kw"]
    discharge = battery_net.clip(lower=0.0)
    charge = battery_net.clip(upper=0.0)
    ax.fill_between(
        times,
        0,
        discharge,
        step="post",
        color=BATTERY_DISCHARGE,
        alpha=0.35,
        label="Battery discharge",
    )
    ax.fill_between(
        times,
        0,
        charge,
        step="post",
        color=BATTERY_CHARGE,
        alpha=0.35,
        label="Battery charge",
    )

    ax.axhline(0, color="#94A3B8", linewidth=0.8)
    ax.set_ylabel("Power [kW]", fontsize=BASE_FONT + 2)
    ax.grid(axis="y", alpha=0.25)
    anchor_y = 0.88 if show_labels else 0.98
    ax.legend(
        loc="upper left",
        bbox_to_anchor=(0.01, anchor_y),
        ncol=2,
        fontsize=BASE_FONT,
        frameon=True,
    )
    ax.tick_params(axis="both", labelsize=BASE_FONT + 1)

    if show_labels:
        y_top = max(wide["load_kw"].max(), gen_pivot.max().max()) * 1.08
        add_module_labels(ax, wide, y_top * 0.98)


def plot_commitment_panel(ax: plt.Axes, dispatch: pd.DataFrame, wide: pd.DataFrame) -> None:
    add_module_background(ax, wide)
    times = wide["datetime"]
    startup_handle = None

    for idx, (generator, grp) in enumerate(dispatch.groupby("generator"), start=1):
        grp = grp.sort_values("timestep")
        on = grp["u"].to_numpy() > 0.5
        lower = pd.Series(idx - 0.32, index=grp.index)
        upper = pd.Series(idx + 0.32, index=grp.index)
        color = GEN_COLORS.get(generator, "#334155")

        ax.fill_between(
            times,
            lower,
            upper,
            where=on,
            step="post",
            color=color,
            alpha=0.60,
        )
        ax.step(
            times,
            idx + 0.32 * grp["u"].to_numpy(),
            where="post",
            color=color,
            linewidth=1.2,
        )

        starts = grp[grp["startup"] > 0.5]["datetime"]
        if not starts.empty:
            scatter = ax.scatter(
                starts,
                [idx + 0.42] * len(starts),
                marker="^",
                s=46,
                color=color,
                edgecolor="white",
                linewidth=0.5,
                zorder=5,
            )
            if startup_handle is None:
                startup_handle = scatter

    ax.set_ylabel("Unit", fontsize=BASE_FONT + 2)
    ax.set_yticks([1, 2], labels=["Gen 1", "Gen 2"])
    ax.set_ylim(0.4, 2.75)
    ax.grid(axis="y", alpha=0.20)
    ax.tick_params(axis="both", labelsize=BASE_FONT + 1)
    if startup_handle is not None:
        ax.legend([startup_handle], ["Startup"], loc="upper left", fontsize=BASE_FONT)


def plot_soc_panel(ax: plt.Axes, wide: pd.DataFrame, soc_min: float, soc_max: float) -> None:
    add_module_background(ax, wide)
    times = wide["datetime"]
    soc = wide["soc_pct"]

    ax.plot(times, soc, color=SOC_COLOR, linewidth=2.2)
    ax.axhline(soc_min * 100.0, color=BOUND_COLOR, linestyle="--", linewidth=1.2, label="SOC min")
    ax.axhline(soc_max * 100.0, color=BOUND_COLOR, linestyle=":", linewidth=1.2, label="SOC max")

    min_idx = soc.idxmin()
    end_idx = soc.index[-1]
    ax.scatter(times.iloc[min_idx], soc.iloc[min_idx], color=SOC_COLOR, s=28, zorder=5)
    ax.scatter(times.iloc[end_idx], soc.iloc[end_idx], color=SOC_COLOR, s=28, zorder=5)
    ax.annotate(
        f"Min {soc.iloc[min_idx]:.1f}%",
        (times.iloc[min_idx], soc.iloc[min_idx]),
        xytext=(0, -18),
        textcoords="offset points",
        ha="center",
        fontsize=BASE_FONT,
        color=SOC_COLOR,
    )
    ax.annotate(
        f"End {soc.iloc[end_idx]:.1f}%",
        (times.iloc[end_idx], soc.iloc[end_idx]),
        xytext=(0, 8),
        textcoords="offset points",
        ha="center",
        fontsize=BASE_FONT,
        color=SOC_COLOR,
    )

    ax.set_ylabel("SOC [%]", fontsize=BASE_FONT + 2)
    ax.set_ylim(20, 95)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(loc="upper left", fontsize=BASE_FONT)
    ax.tick_params(axis="both", labelsize=BASE_FONT + 1)


def plot_residual_panel(ax: plt.Axes, subset: pd.DataFrame) -> None:
    times = subset["datetime"]
    residual = subset["power_balance_residual_kw"]
    max_abs = residual.abs().max()

    ax.axhspan(-0.05, 0.05, color="#CBD5E1", alpha=0.45, label="Rounded-export band")
    ax.step(times, residual, where="post", color="#111827", linewidth=1.8)
    ax.axhline(0, color="#64748B", linewidth=0.9)
    ax.set_ylabel("Residual [kW]", fontsize=BASE_FONT + 2)
    ax.grid(axis="y", alpha=0.25)
    ax.tick_params(axis="both", labelsize=BASE_FONT + 1)
    ax.text(
        0.99,
        0.90,
        f"max |residual| = {max_abs:.2f} kW",
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=BASE_FONT,
        bbox={"boxstyle": "round,pad=0.25", "facecolor": "white", "edgecolor": "#CBD5E1"},
    )
    ax.legend(loc="upper left", fontsize=BASE_FONT)


def build_overview_figure(
    run_dir: Path,
    dispatch: pd.DataFrame,
    wide: pd.DataFrame,
    params: dict,
) -> Path:
    fig, axes = plt.subplots(
        3,
        1,
        figsize=(16, 10.5),
        sharex=True,
        constrained_layout=True,
        gridspec_kw={"height_ratios": [2.5, 1.1, 1.5], "hspace": 0.07},
    )

    plot_power_panel(axes[0], wide, dispatch, show_labels=True)

    plot_commitment_panel(axes[1], dispatch, wide)
    plot_soc_panel(
        axes[2],
        wide,
        soc_min=params["battery"]["SOC_min"],
        soc_max=params["battery"]["SOC_max"],
    )
    format_hour_axis(axes[2], wide["datetime"], major_hours=2)

    out_path = OUTPUT_DIR / f"{run_dir.name}_verification_overview.png"
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return out_path


def build_stress_figure(run_dir: Path, dispatch: pd.DataFrame, wide: pd.DataFrame) -> Path:
    if "module" in wide.columns and (wide["module"] == "severe_load_transients").any():
        stress_steps = wide.loc[wide["module"] == "severe_load_transients", "timestep"]
        start_step = max(int(stress_steps.min()) - 4, int(wide["timestep"].min()))
        end_step = int(stress_steps.max())
        subset = wide[(wide["timestep"] >= start_step) & (wide["timestep"] <= end_step)].copy()
        dispatch_subset = dispatch[dispatch["timestep"].between(start_step, end_step)].copy()
    else:
        subset = wide.tail(20).copy()
        dispatch_subset = dispatch[dispatch["timestep"].isin(subset["timestep"])].copy()

    fig, axes = plt.subplots(
        3,
        1,
        figsize=(15.5, 9.5),
        sharex=True,
        constrained_layout=True,
        gridspec_kw={"height_ratios": [2.2, 1.0, 1.0], "hspace": 0.07},
    )

    plot_power_panel(axes[0], subset, dispatch_subset, show_labels=False)
    plot_commitment_panel(axes[1], dispatch_subset, subset)
    plot_residual_panel(axes[2], subset)
    format_hour_axis(axes[2], subset["datetime"], major_hours=1)

    out_path = OUTPUT_DIR / f"{run_dir.name}_verification_stress_window.png"
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return out_path


def main() -> None:
    run_dir = resolve_run_dir()
    params = load_params(run_dir)
    profile_path = Path(params["load_profile"]["source_file"])

    dispatch, wide = load_dispatch(run_dir)
    profile = load_profile(profile_path)
    wide = merge_profile_labels(wide, profile)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    overview_path = build_overview_figure(run_dir, dispatch, wide, params)
    stress_path = build_stress_figure(run_dir, dispatch, wide)

    print(f"Saved {overview_path}")
    print(f"Saved {stress_path}")
    print(
        "Checks: "
        f"max |power balance residual| = {wide['power_balance_residual_kw'].abs().max():.2f} kW, "
        f"min SOC = {wide['soc_pct'].min():.2f} %, "
        f"terminal SOC = {wide['soc_pct'].iloc[-1]:.2f} %"
    )


if __name__ == "__main__":
    main()
