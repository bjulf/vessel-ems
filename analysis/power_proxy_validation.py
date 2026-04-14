from __future__ import annotations

from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = REPO_ROOT / "data" / "v01.csv"
OUTPUT_DIR = REPO_ROOT / "analysis" / "output"
FIG_PATH = OUTPUT_DIR / "power_proxy_validation.png"
THESIS_FIG_PATH = OUTPUT_DIR / "power_proxy_validation_thesis.png"
SUMMARY_PATH = OUTPUT_DIR / "power_proxy_validation_summary.txt"

P_MAX_KW = 385.0


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

    numeric_cols = [batt, gen1_load, gen2_load, *load_cols]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Match the operational preprocessing logic: sparse generator load updates are held
    # until the next register value arrives.
    df[gen1_load] = df[gen1_load].ffill().fillna(0.0)
    df[gen2_load] = df[gen2_load].ffill().fillna(0.0)
    df[batt] = df[batt].fillna(0.0)

    for col in load_cols:
        df[col] = df[col].fillna(0.0).clip(lower=0.0)

    df["gen1_kw_proxy"] = df[gen1_load] / 100.0 * P_MAX_KW
    df["gen2_kw_proxy"] = df[gen2_load] / 100.0 * P_MAX_KW
    df["genset_kw_proxy"] = df["gen1_kw_proxy"] + df["gen2_kw_proxy"]
    df["known_load_kw"] = df[load_cols].sum(axis=1)
    df["supply_kw_proxy"] = df["genset_kw_proxy"] + df[batt]
    df["other_load_kw"] = df["supply_kw_proxy"] - df["known_load_kw"]
    df["active"] = (
        (df["genset_kw_proxy"] > 1.0)
        | (df["known_load_kw"] > 1.0)
        | (df[batt].abs() > 1.0)
    )
    return df


def write_summary(df: pd.DataFrame) -> str:
    active = df.loc[df["active"]].copy()
    corr = active[["supply_kw_proxy", "known_load_kw"]].corr().iloc[0, 1]
    resid = active["other_load_kw"]
    batt = active["Electric Power System > Energy Storage Main > 1 > Battery Space > Power"]

    lines = [
        "Load Percentage Proxy Validation",
        f"Source: {DATA_PATH}",
        f"Rows: {len(df)}",
        f"Active rows used in comparison: {len(active)}",
        "",
        "Proxy definition",
        "  genset_kw_proxy = (gen1_load_pct + gen2_load_pct) / 100 * 385",
        "  supply_kw_proxy = genset_kw_proxy + battery_power",
        "  known_load_kw = propulsion inverter powers + thruster inverter powers",
        "  other_load_kw = supply_kw_proxy - known_load_kw",
        "",
        "Key results",
        f"  corr(supply_kw_proxy, known_load_kw): {corr:.3f}",
        f"  battery power min / max: {batt.min():.1f} / {batt.max():.1f} kW",
        f"  battery charging rows / discharging rows: {int((batt < -1).sum())} / {int((batt > 1).sum())}",
        f"  other_load_kw mean / median: {resid.mean():.1f} / {resid.median():.1f} kW",
        f"  other_load_kw p10 / p90: {resid.quantile(0.1):.1f} / {resid.quantile(0.9):.1f} kW",
        f"  other_load_kw min / max: {resid.min():.1f} / {resid.max():.1f} kW",
        f"  share with other_load_kw < -5 kW: {(resid.lt(-5).mean() * 100):.2f} %",
        "",
        "Interpretation",
        "  The proxy supply tracks the known exported load-side powers closely.",
        "  The positive residual is consistent with unmetered hotel and auxiliary load on the vessel bus.",
        "  The low rate of negative residuals supports the sign convention and suggests the load % signal is a sensible generator-output proxy.",
        "  This validates the proxy for exploratory analysis, not as a replacement for measured per-genset active kW.",
    ]
    return "\n".join(lines)


def make_figure(df: pd.DataFrame) -> None:
    active = df.loc[df["active"]].copy()
    active["DateTime"] = pd.to_datetime(active["DateTime"])
    active["battery_discharge_kw"] = active[
        "Electric Power System > Energy Storage Main > 1 > Battery Space > Power"
    ].clip(lower=0.0)
    active["battery_charge_kw"] = active[
        "Electric Power System > Energy Storage Main > 1 > Battery Space > Power"
    ].clip(upper=0.0)

    fig, axes = plt.subplots(
        3,
        1,
        figsize=(15, 12),
        gridspec_kw={"height_ratios": [1.2, 1.2, 0.9]},
    )

    ax_time = axes[0]
    ax_scatter = axes[1]
    ax_resid = axes[2]

    ax_time.plot(
        active["DateTime"],
        active["genset_kw_proxy"],
        color="#2563eb",
        lw=1.8,
        label="Generator proxy from load %",
    )
    ax_time.plot(active["DateTime"], active["supply_kw_proxy"], color="#0f766e", lw=2.2, label="Proxy supply")
    ax_time.plot(active["DateTime"], active["known_load_kw"], color="#b45309", lw=2.0, label="Known measured load")
    ax_time.fill_between(
        active["DateTime"],
        active["genset_kw_proxy"],
        active["supply_kw_proxy"],
        where=active["battery_discharge_kw"] > 0,
        interpolate=True,
        color="#22c55e",
        alpha=0.35,
        label="Battery discharge",
    )
    ax_time.fill_between(
        active["DateTime"],
        active["genset_kw_proxy"],
        active["supply_kw_proxy"],
        where=active["battery_charge_kw"] < 0,
        interpolate=True,
        color="#ef4444",
        alpha=0.35,
        label="Battery charging",
    )
    ax_time.fill_between(
        active["DateTime"],
        active["known_load_kw"],
        active["supply_kw_proxy"],
        color="#cbd5e1",
        alpha=0.45,
        label="Residual other onboard load",
    )
    ax_time.set_title("Generator Load % Proxy vs Measured Load-Side Power", fontsize=20, pad=14)
    ax_time.set_ylabel("Power [kW]", fontsize=15)
    ax_time.grid(alpha=0.25)
    ax_time.tick_params(labelsize=12)
    ax_time.legend(fontsize=11, frameon=False, ncol=3, loc="upper left")
    ax_time.xaxis.set_major_locator(mdates.HourLocator(interval=8))
    ax_time.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d %H:%M"))

    ax_scatter.scatter(
        active["known_load_kw"],
        active["supply_kw_proxy"],
        s=18,
        alpha=0.35,
        color="#2563eb",
    )
    max_val = max(active["known_load_kw"].max(), active["supply_kw_proxy"].max()) * 1.03
    ax_scatter.plot([0, max_val], [0, max_val], color="#334155", lw=1.8, ls="--")
    ax_scatter.text(
        0.98 * max_val,
        0.90 * max_val,
        "Points sit close to the 1:1 line,\nwith a positive offset from unmetered onboard load",
        ha="right",
        va="top",
        fontsize=12,
        bbox={"facecolor": "white", "edgecolor": "#94a3b8", "alpha": 0.95},
    )
    ax_scatter.set_title("Pointwise Comparison", fontsize=18, pad=12)
    ax_scatter.set_xlabel("Known measured load-side power [kW]", fontsize=15)
    ax_scatter.set_ylabel("Proxy supply [kW]", fontsize=15)
    ax_scatter.grid(alpha=0.25)
    ax_scatter.tick_params(labelsize=12)

    ax_resid.hist(active["other_load_kw"], bins=40, color="#7c3aed", alpha=0.82, edgecolor="white")
    med = active["other_load_kw"].median()
    p10 = active["other_load_kw"].quantile(0.1)
    p90 = active["other_load_kw"].quantile(0.9)
    ax_resid.axvline(med, color="#111827", lw=2.0)
    ax_resid.axvline(p10, color="#475569", lw=1.5, ls="--")
    ax_resid.axvline(p90, color="#475569", lw=1.5, ls="--")
    ax_resid.text(
        med,
        ax_resid.get_ylim()[1] * 0.92,
        f"median {med:.1f} kW",
        ha="left",
        va="top",
        fontsize=12,
        color="#111827",
    )
    ax_resid.set_title("Residual 'Other Onboard Load' Distribution", fontsize=18, pad=12)
    ax_resid.set_xlabel("Proxy supply - known measured load [kW]", fontsize=15)
    ax_resid.set_ylabel("Count", fontsize=15)
    ax_resid.grid(alpha=0.2)
    ax_resid.tick_params(labelsize=12)

    fig.tight_layout()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG_PATH, dpi=170, bbox_inches="tight")
    plt.close(fig)


def make_thesis_figure(df: pd.DataFrame) -> None:
    active = df.loc[df["active"]].copy()

    fig, (ax_scatter, ax_hist) = plt.subplots(
        2,
        1,
        figsize=(10, 10),
        gridspec_kw={"height_ratios": [1.6, 1.0]},
    )

    scatter_color = "#5b7ea4"
    line_color = "#374151"
    hist_color = "#8aa29e"
    median_color = "#134e4a"

    ax_scatter.scatter(
        active["known_load_kw"],
        active["supply_kw_proxy"],
        s=18,
        alpha=0.35,
        color=scatter_color,
        edgecolors="none",
    )
    max_val = max(active["known_load_kw"].max(), active["supply_kw_proxy"].max()) * 1.03
    ax_scatter.plot([0, max_val], [0, max_val], color=line_color, lw=1.5, ls="--")
    ax_scatter.set_title("Validation of Generator Power Proxy", fontsize=18, pad=12)
    ax_scatter.set_xlabel("Measured propulsion and thruster power [kW]", fontsize=13)
    ax_scatter.set_ylabel("Proxy generator supply + battery power [kW]", fontsize=13)
    ax_scatter.grid(alpha=0.25)
    ax_scatter.tick_params(labelsize=11)

    ax_hist.hist(
        active["other_load_kw"],
        bins=36,
        color=hist_color,
        alpha=0.9,
        edgecolor="white",
    )
    ax_hist.axvline(0.0, color=line_color, lw=1.5, ls="--")
    ax_hist.axvline(active["other_load_kw"].median(), color=median_color, lw=2.0)
    ax_hist.set_title("Residual Distribution", fontsize=16, pad=10)
    ax_hist.set_xlabel("Residual [kW]", fontsize=13)
    ax_hist.set_ylabel("Count", fontsize=13)
    ax_hist.grid(alpha=0.2)
    ax_hist.tick_params(labelsize=11)

    fig.tight_layout()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(THESIS_FIG_PATH, dpi=170, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    df = prepare_data()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    summary = write_summary(df)
    SUMMARY_PATH.write_text(summary, encoding="utf-8")
    make_figure(df)
    make_thesis_figure(df)

    print(summary)
    print("")
    print(f"Saved {SUMMARY_PATH}")
    print(f"Saved {FIG_PATH}")
    print(f"Saved {THESIS_FIG_PATH}")


if __name__ == "__main__":
    main()
