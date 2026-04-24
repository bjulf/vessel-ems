from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Patch


CASE_DIR = Path(__file__).resolve().parent
RAW_DIR = CASE_DIR / "raw"
PREPARED_DIR = CASE_DIR / "prepared"
FIGURES_DIR = CASE_DIR / "figures"

RAW_PATHS = [
    RAW_DIR / "all-data-types_2026-01-26_to_2026-01-28.csv",
    RAW_DIR / "all-data-types_2026-01-28_to_2026-01-31.csv",
]

COMBINED_PATH = PREPARED_DIR / "combined_1min.csv"
CLEANED_PATH = PREPARED_DIR / "cleaned_1min.csv"
PROFILE_15MIN_PATH = PREPARED_DIR / "load_profile_15min_avg.csv"
FIG_PATH = FIGURES_DIR / "operational_load_validation_6day.png"

P_MAX_KW = 385.0

COLOR_TOTAL = "#0f766e"
COLOR_KNOWN = "#b45309"
COLOR_OTHER = "#cbd5e1"
COLOR_GEN1 = "#60a5fa"
COLOR_GEN2 = "#2563eb"
COLOR_DISCHARGE = "#dc2626"
COLOR_CHARGE = "#16a34a"

BATT_COL = "Electric Power System > Energy Storage Main > 1 > Battery Space > Power"
SOC_COL = "Electric Power System > Energy Storage Main > 1 > Battery Space > State of Charge"
GEN1_LOAD_COL = "Electric Power System > Generator Set > 1 > Engine > Load percentage"
GEN2_LOAD_COL = "Electric Power System > Generator Set > 2 > Engine > Load percentage"
LOAD_COLS = [
    "Propulsion and Steering > Propulsion Main Electric > Port > Inverter > Power",
    "Propulsion and Steering > Propulsion Main Electric > Starboard > Inverter > Power",
    "Propulsion and Steering > Thruster Electric > Port Aft > Inverter > Power",
    "Propulsion and Steering > Thruster Electric > Port Forward > Inverter > Power",
    "Propulsion and Steering > Thruster Electric > Starboard Aft > Inverter > Power",
]


def combine_raw_inputs() -> pd.DataFrame:
    frames = [pd.read_csv(path, parse_dates=["DateTime"]) for path in RAW_PATHS]
    df = pd.concat(frames, ignore_index=True)
    df = df.sort_values("DateTime").drop_duplicates(subset=["DateTime"], keep="first")
    return df.reset_index(drop=True)


def prepare_cleaned_data(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = df.copy()

    for col in [BATT_COL, SOC_COL, GEN1_LOAD_COL, GEN2_LOAD_COL, *LOAD_COLS]:
        cleaned[col] = pd.to_numeric(cleaned[col], errors="coerce")

    cleaned[GEN1_LOAD_COL] = cleaned[GEN1_LOAD_COL].ffill().fillna(0.0).clip(lower=0.0, upper=100.0)
    cleaned[GEN2_LOAD_COL] = cleaned[GEN2_LOAD_COL].ffill().fillna(0.0).clip(lower=0.0, upper=100.0)
    cleaned[BATT_COL] = cleaned[BATT_COL].fillna(0.0)
    cleaned[SOC_COL] = cleaned[SOC_COL].ffill()

    for col in LOAD_COLS:
        cleaned[col] = cleaned[col].fillna(0.0).clip(lower=0.0)

    cleaned["gen1_kw_proxy"] = cleaned[GEN1_LOAD_COL] / 100.0 * P_MAX_KW
    cleaned["gen2_kw_proxy"] = cleaned[GEN2_LOAD_COL] / 100.0 * P_MAX_KW
    cleaned["genset_kw_proxy"] = cleaned["gen1_kw_proxy"] + cleaned["gen2_kw_proxy"]
    cleaned["battery_discharge_kw"] = cleaned[BATT_COL].clip(lower=0.0)
    cleaned["battery_charge_kw"] = (-cleaned[BATT_COL]).clip(lower=0.0)
    cleaned["reconstructed_total_load_kw_raw"] = cleaned["genset_kw_proxy"] + cleaned[BATT_COL]
    cleaned["reconstructed_total_load_kw"] = cleaned["reconstructed_total_load_kw_raw"].clip(lower=0.0)
    cleaned["known_measured_load_kw"] = cleaned[LOAD_COLS].sum(axis=1)
    cleaned["other_onboard_load_kw"] = (
        cleaned["reconstructed_total_load_kw"] - cleaned["known_measured_load_kw"]
    )
    cleaned["elapsed_hours"] = (
        cleaned["DateTime"] - cleaned["DateTime"].iloc[0]
    ).dt.total_seconds() / 3600.0

    return cleaned


def build_15min_profile(cleaned: pd.DataFrame) -> pd.DataFrame:
    profile = (
        cleaned.set_index("DateTime")["reconstructed_total_load_kw"]
        .resample("15min")
        .mean()
        .reset_index()
    )
    profile["timestep"] = range(1, len(profile) + 1)
    profile = profile.rename(columns={"DateTime": "datetime", "reconstructed_total_load_kw": "load_kw"})
    return profile[["timestep", "load_kw", "datetime"]]


def save_prepared_outputs(combined: pd.DataFrame, cleaned: pd.DataFrame, profile_15min: pd.DataFrame) -> None:
    PREPARED_DIR.mkdir(parents=True, exist_ok=True)
    combined.to_csv(COMBINED_PATH, index=False)
    cleaned.to_csv(CLEANED_PATH, index=False)
    profile_15min.to_csv(PROFILE_15MIN_PATH, index=False)


def make_figure(cleaned: pd.DataFrame) -> None:
    plt.rcParams.update(
        {
            "font.size": 16,
            "axes.labelsize": 22,
            "xtick.labelsize": 18,
            "ytick.labelsize": 18,
            "legend.fontsize": 16,
        }
    )

    fig, (ax_top, ax_bottom) = plt.subplots(
        2,
        1,
        figsize=(17, 10),
        sharex=True,
        gridspec_kw={"height_ratios": [1.05, 0.95]},
    )

    elapsed_hours = cleaned["elapsed_hours"]
    line_total, = ax_top.plot(
        elapsed_hours,
        cleaned["reconstructed_total_load_kw"],
        color=COLOR_TOTAL,
        lw=2.2,
        label="Reconstructed total load",
    )
    line_known, = ax_top.plot(
        elapsed_hours,
        cleaned["known_measured_load_kw"],
        color=COLOR_KNOWN,
        lw=2.0,
        label="Measured propulsion/thruster load",
    )
    residual = ax_top.fill_between(
        elapsed_hours,
        cleaned["known_measured_load_kw"],
        cleaned["reconstructed_total_load_kw"],
        where=cleaned["reconstructed_total_load_kw"] >= cleaned["known_measured_load_kw"],
        color=COLOR_OTHER,
        alpha=0.34,
        label="Residual onboard load",
    )
    ax_top.set_ylabel("Power [kW]")
    ax_top.grid(alpha=0.18)
    ax_top.legend(
        handles=[line_total, line_known, residual],
        frameon=False,
        loc="upper left",
        ncol=3,
    )

    battery_net = cleaned["battery_discharge_kw"] - cleaned["battery_charge_kw"]
    ax_bottom.axhline(0, color="#334155", lw=1.5)
    line_gen1, = ax_bottom.plot(
        elapsed_hours,
        cleaned["gen1_kw_proxy"],
        color=COLOR_GEN1,
        lw=2.0,
        label="Gen 1 proxy",
    )
    line_gen2, = ax_bottom.plot(
        elapsed_hours,
        cleaned["gen2_kw_proxy"],
        color=COLOR_GEN2,
        lw=2.0,
        label="Gen 2 proxy",
    )
    ax_bottom.fill_between(
        elapsed_hours,
        0,
        battery_net,
        where=battery_net >= 0,
        color=COLOR_DISCHARGE,
        alpha=0.20,
    )
    ax_bottom.fill_between(
        elapsed_hours,
        0,
        battery_net,
        where=battery_net <= 0,
        color=COLOR_CHARGE,
        alpha=0.20,
    )
    line_battery, = ax_bottom.plot(
        elapsed_hours,
        battery_net,
        color="#0f172a",
        lw=1.7,
        label="Battery power",
    )
    ax_bottom.set_ylabel("Power [kW]")
    ax_bottom.set_xlabel("Elapsed time [h]")
    ax_bottom.grid(alpha=0.18)
    ax_bottom.legend(
        handles=[
            line_gen1,
            line_gen2,
            Patch(facecolor=COLOR_DISCHARGE, edgecolor=COLOR_DISCHARGE, alpha=0.28, label="Battery discharge"),
            Patch(facecolor=COLOR_CHARGE, edgecolor=COLOR_CHARGE, alpha=0.28, label="Battery charging"),
            line_battery,
        ],
        frameon=False,
        loc="upper left",
        ncol=3,
    )

    fig.tight_layout()
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG_PATH, dpi=180, bbox_inches="tight")
    plt.close(fig)


def write_readme(cleaned: pd.DataFrame, profile_15min: pd.DataFrame) -> None:
    span_hours = (
        cleaned["DateTime"].iloc[-1] - cleaned["DateTime"].iloc[0]
    ).total_seconds() / 3600.0
    readme_path = CASE_DIR / "README.md"
    text = "\n".join(
        [
            "# Baseline Load Case",
            "",
            "This case keeps the raw exports, prepared datasets, and working figures together.",
            "",
            "## Source Files",
            "",
            "- `raw/all-data-types_2026-01-26_to_2026-01-28.csv`",
            "- `raw/all-data-types_2026-01-28_to_2026-01-31.csv`",
            "",
            "## Prepared Outputs",
            "",
            "- `prepared/combined_1min.csv`: timestamp-sorted combination of the raw exports",
            "- `prepared/cleaned_1min.csv`: cleaned minute-level dataset with derived load columns",
            "- `prepared/load_profile_15min_avg.csv`: 15-minute average reconstructed load profile",
            "",
            "## Figure",
            "",
            "- `figures/operational_load_validation_6day.png`: 2-panel operational load reconstruction figure",
            "",
            "## Notes",
            "",
            f"- Combined span: {cleaned['DateTime'].iloc[0]} to {cleaned['DateTime'].iloc[-1]}",
            f"- Total duration: {span_hours:.2f} h",
            f"- 15-minute profile steps: {len(profile_15min)}",
            f"- Reconstructed load range: {cleaned['reconstructed_total_load_kw'].min():.1f} to {cleaned['reconstructed_total_load_kw'].max():.1f} kW",
            f"- Battery power range: {cleaned[BATT_COL].min():.1f} to {cleaned[BATT_COL].max():.1f} kW",
            f"- Gen 2 proxy max in this case: {cleaned['gen2_kw_proxy'].max():.1f} kW",
            "",
            "The current export behaves like a `gen1`-dominated operational case: `gen2` remains at zero throughout the prepared dataset.",
            "The figure therefore preserves the same structure as the existing validation plot while making that operating pattern visible.",
        ]
    )
    readme_path.write_text(text, encoding="utf-8")


def main() -> None:
    combined = combine_raw_inputs()
    cleaned = prepare_cleaned_data(combined)
    profile_15min = build_15min_profile(cleaned)
    save_prepared_outputs(combined, cleaned, profile_15min)
    make_figure(cleaned)
    write_readme(cleaned, profile_15min)

    print(f"Saved {COMBINED_PATH}")
    print(f"Saved {CLEANED_PATH}")
    print(f"Saved {PROFILE_15MIN_PATH}")
    print(f"Saved {FIG_PATH}")
    print(f"Saved {CASE_DIR / 'README.md'}")


if __name__ == "__main__":
    main()
