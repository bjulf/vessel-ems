"""Generate a single synthetic 24 h / 15 min validation load profile.

Outputs:
  - `data/load_profile.csv` as the active model input
  - `data/synthetic_profiles/validation_profile.csv`
  - `data/synthetic_profiles/plots/validation_profile.png`
  - `data/synthetic_profiles/plots/validation_profile_bars.png`
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


STEP_MINUTES = 15
STEPS_PER_DAY = 24 * 60 // STEP_MINUTES
START_TIME = "2026-03-01 00:00"
SEED = 7

DATA_DIR = Path(__file__).parent
SCENARIO_DIR = DATA_DIR / "synthetic_profiles"
PLOT_DIR = SCENARIO_DIR / "plots"
ACTIVE_PROFILE = DATA_DIR / "load_profile.csv"
VALIDATION_PROFILE = SCENARIO_DIR / "validation_profile.csv"

MODULES = {
    "harbor_hotel": {"label": "Harbor / hotel", "color": "#4C78A8", "range_kw": (20.0, 60.0)},
    "aux_work": {"label": "Auxiliary work", "color": "#72B7B2", "range_kw": (60.0, 150.0)},
    "maneuvering": {"label": "Maneuvering", "color": "#F58518", "range_kw": (120.0, 300.0)},
    "load_transients": {"label": "Load transients", "color": "#9C755F", "range_kw": (0.0, 350.0)},
    "transit": {"label": "Transit", "color": "#54A24B", "range_kw": (140.0, 260.0)},
    "high_transient": {"label": "High transient", "color": "#E45756", "range_kw": (250.0, 450.0)},
    "severe_load_transients": {"label": "Severe load transients", "color": "#B279A2", "range_kw": (0.0, 770.0)},
}


@dataclass(frozen=True)
class Block:
    module: str
    steps: int
    start_kw: float
    end_kw: float
    wave_kw: float = 0.0
    noise_kw: float = 0.0
    pattern: str = "trend"
    sequence_kw: Optional[tuple[float, ...]] = None


VALIDATION_BLOCKS = [
    Block("harbor_hotel", 12, 34, 40, wave_kw=3, noise_kw=1.5, pattern="plateau"),
    Block("aux_work", 16, 80, 120, wave_kw=0, noise_kw=16.0, pattern="random"),
    Block("transit", 24, 185, 205, wave_kw=8, noise_kw=4.0, pattern="plateau"),
    Block("maneuvering", 16, 150, 260, wave_kw=0, noise_kw=28.0, pattern="random"),
    Block(
        "load_transients",
        8,
        0,
        350,
        pattern="sequence",
        sequence_kw=(350.0, 0.0, 350.0, 120.0, 0.0, 300.0, 40.0, 330.0),
    ),
    Block("high_transient", 12, 280, 420, wave_kw=18, noise_kw=14.0, pattern="random"),
    Block(
        "severe_load_transients",
        8,
        0,
        770,
        pattern="sequence",
        sequence_kw=(0.0, 152.86, 0.0, 770.0, 0.0, 730.06, 770.0, 261.85),
    ),
]


def _build_block(block: Block, rng: np.random.Generator) -> np.ndarray:
    module = MODULES[block.module]
    lo, hi = module["range_kw"]

    if block.pattern == "sequence":
        if block.sequence_kw is None or len(block.sequence_kw) != block.steps:
            raise ValueError(f"{block.module} sequence must contain exactly {block.steps} values")
        values = np.array(block.sequence_kw, dtype=float)
    elif block.pattern == "plateau":
        center = 0.5 * (block.start_kw + block.end_kw)
        phase = np.linspace(0.0, 2.0 * np.pi, block.steps)
        values = center + block.wave_kw * np.sin(phase) + rng.normal(0.0, block.noise_kw, block.steps)
    elif block.pattern == "random":
        anchors = rng.uniform(block.start_kw, block.end_kw, block.steps)
        local_wave = block.wave_kw * np.sin(np.linspace(0.0, 3.0 * np.pi, block.steps))
        values = anchors + local_wave + rng.normal(0.0, block.noise_kw, block.steps)
    elif block.pattern == "chaos":
        values = rng.uniform(block.start_kw, block.end_kw, block.steps)
        extremes = np.arange(0, block.steps, 2)
        values[extremes] = rng.choice([block.start_kw, block.end_kw], size=len(extremes))
    else:
        base = np.linspace(block.start_kw, block.end_kw, block.steps)
        phase = np.linspace(0.0, np.pi, block.steps)
        values = base + block.wave_kw * np.sin(phase) + rng.normal(0.0, block.noise_kw, block.steps)

    return np.round(np.clip(values, lo, hi), 2)


def _module_spans(df: pd.DataFrame):
    start_idx = 0
    modules = df["module"].tolist()
    while start_idx < len(df):
        end_idx = start_idx + 1
        while end_idx < len(df) and modules[end_idx] == modules[start_idx]:
            end_idx += 1
        yield start_idx, end_idx - 1, modules[start_idx]
        start_idx = end_idx


def _draw_module_separators(ax: plt.Axes, times: pd.Series, df: pd.DataFrame) -> None:
    for start_idx, _, _ in list(_module_spans(df))[1:]:
        ax.axvline(times.iloc[start_idx], color="#64748b", lw=1.0, ls="--", alpha=0.7, zorder=1)


def _annotate_module_spans(ax: plt.Axes, times: pd.Series, df: pd.DataFrame, y: float) -> None:
    for start_idx, end_idx, module_name in _module_spans(df):
        start = times.iloc[start_idx]
        end = times.iloc[end_idx] + pd.Timedelta(minutes=STEP_MINUTES)
        midpoint = start + (end - start) / 2
        ax.text(
            midpoint,
            y,
            MODULES[module_name]["label"],
            ha="center",
            va="center",
            fontsize=14,
            color="#0f172a",
            bbox={
                "boxstyle": "round,pad=0.36",
                "facecolor": "white",
                "edgecolor": MODULES[module_name]["color"],
                "linewidth": 1.2,
                "alpha": 0.92,
            },
            zorder=5,
        )


def _label_y_scale(module_name: str) -> float:
    return {
        "harbor_hotel": 0.98,
        "aux_work": 0.98,
        "transit": 0.98,
        "maneuvering": 0.98,
        "load_transients": 0.98,
        "high_transient": 0.86,
        "severe_load_transients": 0.98,
    }.get(module_name, 0.98)


def _annotate_module_spans_elapsed(ax: plt.Axes, df: pd.DataFrame, y: float) -> None:
    step_hours = STEP_MINUTES / 60.0
    for start_idx, end_idx, module_name in _module_spans(df):
        start = start_idx * step_hours
        end = (end_idx + 1) * step_hours
        midpoint = 0.5 * (start + end)
        ax.text(
            midpoint,
            y * _label_y_scale(module_name),
            MODULES[module_name]["label"],
            ha="center",
            va="center",
            fontsize=16,
            color="#0f172a",
            bbox={
                "boxstyle": "round,pad=0.32",
                "facecolor": "white",
                "edgecolor": MODULES[module_name]["color"],
                "linewidth": 1.2,
                "alpha": 0.94,
            },
            zorder=5,
        )


def _draw_module_separators_elapsed(ax: plt.Axes, df: pd.DataFrame) -> None:
    step_hours = STEP_MINUTES / 60.0
    for start_idx, _, _ in list(_module_spans(df))[1:]:
        ax.axvline(start_idx * step_hours, color="#64748b", lw=1.0, ls="--", alpha=0.7, zorder=1)


def _draw_module_background_elapsed(ax: plt.Axes, df: pd.DataFrame) -> None:
    step_hours = STEP_MINUTES / 60.0
    for start_idx, end_idx, module_name in _module_spans(df):
        start = start_idx * step_hours
        end = (end_idx + 1) * step_hours
        ax.axvspan(start, end, color=MODULES[module_name]["color"], alpha=0.10, linewidth=0, zorder=0)


def generate_validation_profile() -> pd.DataFrame:
    total_steps = sum(block.steps for block in VALIDATION_BLOCKS)
    if total_steps != STEPS_PER_DAY:
        raise ValueError(f"Validation profile has {total_steps} steps, expected {STEPS_PER_DAY}")

    rng = np.random.default_rng(SEED)
    frames = []
    current_time = pd.Timestamp(START_TIME)
    timestep = 1

    for block in VALIDATION_BLOCKS:
        module = MODULES[block.module]
        values = _build_block(block, rng)
        times = pd.date_range(current_time, periods=block.steps, freq=f"{STEP_MINUTES}min")
        frame = pd.DataFrame(
            {
                "timestep": range(timestep, timestep + block.steps),
                "load_kw": values,
                "datetime": times.strftime("%Y-%m-%d %H:%M"),
                "module": block.module,
                "module_label": module["label"],
                "scenario": "validation",
            }
        )
        frames.append(frame)
        timestep += block.steps
        current_time = times[-1] + pd.Timedelta(minutes=STEP_MINUTES)

    return pd.concat(frames, ignore_index=True)


def save_profile(df: pd.DataFrame) -> None:
    SCENARIO_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(VALIDATION_PROFILE, index=False)
    df.to_csv(ACTIVE_PROFILE, index=False)


def plot_validation_profile(df: pd.DataFrame, path: Path) -> None:
    times = pd.to_datetime(df["datetime"])
    fig, ax = plt.subplots(figsize=(16, 6.2))
    y_top = max(560, df["load_kw"].max() * 1.18)

    for start_idx, end_idx, module_name in _module_spans(df):
        color = MODULES[module_name]["color"]
        start = times.iloc[start_idx]
        end = times.iloc[end_idx] + pd.Timedelta(minutes=STEP_MINUTES)
        ax.axvspan(start, end, color=color, alpha=0.14, linewidth=0)

    ax.plot(times, df["load_kw"], color="#1f2937", lw=2.2, marker="o", ms=3)
    ax.fill_between(times, 0, df["load_kw"], color="#94a3b8", alpha=0.18)
    _draw_module_separators(ax, times, df)
    _annotate_module_spans(ax, times, df, y_top * 0.93)
    ax.set_title("Synthetic Validation Load Profile", fontsize=22, pad=16)
    ax.set_ylabel("Load [kW]", fontsize=18)
    ax.set_xlabel("")
    ax.set_ylim(0, y_top)
    ax.xaxis.set_major_locator(mdates.HourLocator(interval=3))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax.tick_params(axis="both", labelsize=16)
    ax.grid(axis="y", alpha=0.25)

    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def plot_validation_bars(df: pd.DataFrame, path: Path) -> None:
    step_hours = STEP_MINUTES / 60.0
    elapsed_hours = np.arange(len(df)) * step_hours
    colors = [MODULES[module]["color"] for module in df["module"]]

    fig, ax = plt.subplots(figsize=(16, 6.2))
    _draw_module_background_elapsed(ax, df)
    ax.bar(
        elapsed_hours,
        df["load_kw"],
        width=step_hours,
        align="edge",
        color=colors,
        edgecolor="white",
        linewidth=0.45,
    )

    y_top = max(560, df["load_kw"].max() * 1.18)
    _draw_module_separators_elapsed(ax, df)
    _annotate_module_spans_elapsed(ax, df, y_top * 0.98)

    ax.set_ylabel("Load [kW]", fontsize=20)
    ax.set_xlabel("Hour", fontsize=20)
    ax.set_ylim(0, y_top)
    ax.set_xlim(0, len(df) * step_hours)
    ax.set_xticks(np.arange(0, 25, 2))
    ax.tick_params(axis="both", labelsize=18)
    ax.grid(axis="y", alpha=0.25)

    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    df = generate_validation_profile()
    save_profile(df)
    plot_validation_profile(df, PLOT_DIR / "validation_profile.png")
    plot_validation_bars(df, PLOT_DIR / "validation_profile_bars.png")

    print(f"Active profile -> {ACTIVE_PROFILE}")
    print(f"Validation profile -> {VALIDATION_PROFILE}")
    print(f"Steps: {len(df)}, range: {df['load_kw'].min():.1f}-{df['load_kw'].max():.1f} kW")


if __name__ == "__main__":
    main()
