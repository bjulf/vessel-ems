from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Patch


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = REPO_ROOT / "data" / "v01.csv"
OUTPUT_DIR = REPO_ROOT / "analysis" / "output"
FIG_PATH = OUTPUT_DIR / "operational_load_validation.png"
SUMMARY_PATH = OUTPUT_DIR / "operational_load_validation.md"

P_MAX_KW = 385.0

COLOR_TOTAL = "#0f766e"
COLOR_KNOWN = "#b45309"
COLOR_OTHER = "#cbd5e1"
COLOR_GEN1 = "#60a5fa"
COLOR_GEN2 = "#2563eb"
COLOR_DISCHARGE = "#dc2626"
COLOR_CHARGE = "#16a34a"

AXIS_LABEL_FONTSIZE = 20
TICK_FONTSIZE = 17
LEGEND_FONTSIZE = 16


def prepare_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH, parse_dates=["DateTime"])

    batt = "Electric Power System > Energy Storage Main > 1 > Battery Space > Power"
    gen1_load = "Electric Power System > Generator Set > 1 > Engine > Load percentage"
    gen2_load = "Electric Power System > Generator Set > 2 > Engine > Load percentage"
    load_cols = [
        "Propulsion and Steering > Propulsion Main Electric > Port > Inverter > Power",
        "Propulsion and Steering > Propulsion Main Electric > Starboard > Inverter > Power",
        "Propulsion and Steering > Thruster Electric > Port Aft > Inverter > Power",
        "Propulsion and Steering > Thruster Electric > Port Forward > Inverter > Power",
        "Propulsion and Steering > Thruster Electric > Starboard Aft > Inverter > Power",
    ]

    for col in [batt, gen1_load, gen2_load, *load_cols]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df[gen1_load] = df[gen1_load].ffill().fillna(0.0)
    df[gen2_load] = df[gen2_load].ffill().fillna(0.0)
    df[batt] = df[batt].fillna(0.0)

    for col in load_cols:
        df[col] = df[col].fillna(0.0).clip(lower=0.0)

    df["gen1_kw_proxy"] = df[gen1_load] / 100.0 * P_MAX_KW
    df["gen2_kw_proxy"] = df[gen2_load] / 100.0 * P_MAX_KW
    df["genset_kw_proxy"] = df["gen1_kw_proxy"] + df["gen2_kw_proxy"]
    df["battery_discharge_kw"] = df[batt].clip(lower=0.0)
    df["battery_charge_kw"] = (-df[batt]).clip(lower=0.0)
    df["reconstructed_total_load_kw_raw"] = df["genset_kw_proxy"] + df[batt]
    df["reconstructed_total_load_kw"] = df["reconstructed_total_load_kw_raw"].clip(lower=0.0)
    df["known_measured_load_kw"] = df[load_cols].sum(axis=1)
    df["other_onboard_load_kw"] = df["reconstructed_total_load_kw"] - df["known_measured_load_kw"]
    return df


def make_figure(df: pd.DataFrame) -> None:
    elapsed_hours = (df["DateTime"] - df["DateTime"].iloc[0]).dt.total_seconds() / 3600.0

    plt.rcParams.update(
        {
            "font.size": 11,
            "axes.labelsize": 13,
            "xtick.labelsize": 11,
            "ytick.labelsize": 11,
            "legend.fontsize": 10,
        }
    )

    fig, (ax_top, ax_bottom) = plt.subplots(
        2,
        1,
        figsize=(13, 7.6),
        sharex=True,
        gridspec_kw={"height_ratios": [1.05, 0.95]},
    )

    line_total, = ax_top.plot(
        elapsed_hours,
        df["reconstructed_total_load_kw"],
        color=COLOR_TOTAL,
        lw=1.8,
        label="Reconstructed total load",
    )
    line_known, = ax_top.plot(
        elapsed_hours,
        df["known_measured_load_kw"],
        color=COLOR_KNOWN,
        lw=1.5,
        label="Measured propulsion/thruster load",
    )
    residual = ax_top.fill_between(
        elapsed_hours,
        df["known_measured_load_kw"],
        df["reconstructed_total_load_kw"],
        color=COLOR_OTHER,
        alpha=0.32,
        label="Residual other onboard load",
        where=df["reconstructed_total_load_kw"] >= df["known_measured_load_kw"],
    )
    ax_top.set_ylabel("Power [kW]", fontsize=AXIS_LABEL_FONTSIZE)
    ax_top.grid(alpha=0.18)
    ax_top.tick_params(labelsize=TICK_FONTSIZE)
    ax_top.legend(
        handles=[line_total, line_known, residual],
        fontsize=LEGEND_FONTSIZE,
        frameon=False,
        ncol=3,
        loc="upper left",
    )

    battery_net = df["battery_discharge_kw"] - df["battery_charge_kw"]
    ax_bottom.axhline(0, color="#334155", lw=1.4)
    line_gen1, = ax_bottom.plot(
        elapsed_hours,
        df["gen1_kw_proxy"],
        color=COLOR_GEN1,
        lw=1.5,
        label="Gen 1 proxy",
    )
    line_gen2, = ax_bottom.plot(
        elapsed_hours,
        df["gen2_kw_proxy"],
        color=COLOR_GEN2,
        lw=1.5,
        label="Gen 2 proxy",
    )
    ax_bottom.fill_between(
        elapsed_hours,
        0,
        battery_net,
        where=battery_net >= 0,
        color=COLOR_DISCHARGE,
        alpha=0.18,
    )
    ax_bottom.fill_between(
        elapsed_hours,
        0,
        battery_net,
        where=battery_net <= 0,
        color=COLOR_CHARGE,
        alpha=0.18,
    )
    line_battery, = ax_bottom.plot(
        elapsed_hours,
        battery_net,
        color="#0f172a",
        lw=1.2,
        label="Battery power",
    )
    ax_bottom.set_ylabel("Power [kW]", fontsize=AXIS_LABEL_FONTSIZE)
    ax_bottom.set_xlabel("Elapsed time [h]", fontsize=AXIS_LABEL_FONTSIZE)
    ax_bottom.grid(alpha=0.18)
    ax_bottom.tick_params(labelsize=TICK_FONTSIZE)
    ax_bottom.legend(
        handles=[
            line_gen1,
            line_gen2,
            Patch(facecolor=COLOR_DISCHARGE, edgecolor=COLOR_DISCHARGE, alpha=0.25, label="Battery discharge"),
            Patch(facecolor=COLOR_CHARGE, edgecolor=COLOR_CHARGE, alpha=0.25, label="Battery charging"),
            line_battery,
        ],
        fontsize=LEGEND_FONTSIZE,
        frameon=False,
        ncol=3,
        loc="upper left",
    )

    fig.tight_layout()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG_PATH, dpi=170, bbox_inches="tight")
    plt.close(fig)


def write_summary(df: pd.DataFrame) -> str:
    load = df["reconstructed_total_load_kw"]
    other = df["other_onboard_load_kw"]

    return "\n".join(
        [
            "# Operational Load Validation",
            "",
            f"Source: [{DATA_PATH.name}](../data/{DATA_PATH.name})",
            "",
            "## Definition",
            "",
            "`reconstructed_total_load_kw = gen1_load_pct/100*385 + gen2_load_pct/100*385 + battery_power`",
            "",
            "This is a reconstructed bus-load estimate, not a directly measured total-load signal.",
            "",
            "## Why This Makes Sense",
            "",
            "- The dataset does not contain a useful nonzero total-bus-load tag.",
            "- The generator `load %` proxy has already passed an internal consistency check against the explicit propulsion and thruster loads.",
            "- Adding battery power accounts for power being supplied by or absorbed into the battery at the bus.",
            "",
            "## What The Figure Shows",
            "",
            "- Top panel: reconstructed total load, known measured propulsion/thruster load, and residual other onboard load.",
            "- Bottom panel: generator 1 and generator 2 proxy output together with battery net power at the bus.",
            "",
            "## Key Numbers",
            "",
            f"- Reconstructed load mean / median: {load.mean():.1f} / {load.median():.1f} kW",
            f"- Reconstructed load min / max: {load.min():.1f} / {load.max():.1f} kW",
            f"- Raw reconstructed load min before clipping: {df['reconstructed_total_load_kw_raw'].min():.1f} kW",
            f"- Residual other onboard load mean / median: {other.mean():.1f} / {other.median():.1f} kW",
            f"- Battery charging max: {df['battery_charge_kw'].max():.1f} kW",
            f"- Battery discharging max: {df['battery_discharge_kw'].max():.1f} kW",
            "",
            "## Plotting Note",
            "",
            "- Calendar dates are removed from the x-axis and shown as elapsed hours for a more anonymous presentation.",
            "- The figure is reduced to two panels to keep the thesis Methods section focused on the reconstruction logic.",
            "- Battery discharge is shown in red and battery charging is shown in green.",
            "- Battery charge and discharge are shown as one signed bus-power signal around zero in the lower panel.",
            "- The residual shading in the top panel visualizes load that is plausibly onboard but not explicitly metered in the export.",
        ]
    )


def main() -> None:
    df = prepare_data()
    make_figure(df)
    summary = write_summary(df)
    SUMMARY_PATH.write_text(summary, encoding="utf-8")
    print(summary)
    print("")
    print(f"Saved {FIG_PATH}")
    print(f"Saved {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
