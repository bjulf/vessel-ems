from __future__ import annotations

import argparse
import tomllib
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUN_DIR = REPO_ROOT / "runs" / "2026-04-26_171631_baseline_model"
BASE_FONT = 13

MODULE_COLORS = {
    "harbor_hotel": "#4C78A8",
    "aux_work": "#72B7B2",
    "transit": "#54A24B",
    "maneuvering": "#F2A541",
    "load_transients": "#9C755F",
    "high_transient": "#E45756",
    "severe_load_transients": "#B279A2",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plot retained synthetic MILP dispatch points against the straight-line "
            "OEM SFOC reference curve."
        )
    )
    parser.add_argument(
        "run_dir",
        nargs="?",
        type=Path,
        default=DEFAULT_RUN_DIR,
        help="Run directory containing params.toml and dispatch_results.csv.",
    )
    return parser.parse_args()


def load_params(run_dir: Path) -> dict:
    with open(run_dir / "params.toml", "rb") as fh:
        return tomllib.load(fh)


def load_dispatch_with_modules(run_dir: Path, params: dict) -> pd.DataFrame:
    dispatch = pd.read_csv(run_dir / "dispatch_results.csv")
    dispatch["generator"] = dispatch["generator"].astype(str)

    profile_path = Path(params["load_profile"]["source_file"])
    profile = pd.read_csv(profile_path)
    module_cols = ["timestep", "module", "module_label"]
    available = [col for col in module_cols if col in profile.columns]
    if available == module_cols:
        dispatch = dispatch.merge(profile[module_cols], on="timestep", how="left")

    return dispatch


def oem_sfoc_reference(params: dict) -> pd.DataFrame:
    generator = params["generators"][0]
    return pd.DataFrame(
        {
            "P_kw": generator["P"],
            "SFOC_gkwh": generator["SFOC"],
        }
    )


def plot_oem_sfoc_reference(run_dir: Path) -> tuple[Path, Path, float]:
    params = load_params(run_dir)
    dispatch = load_dispatch_with_modules(run_dir, params)
    active = dispatch[dispatch["u"] > 0.5].copy()
    oem = oem_sfoc_reference(params)

    fig, ax = plt.subplots(figsize=(12.4, 3.7), constrained_layout=True)

    ax.plot(
        oem["P_kw"],
        oem["SFOC_gkwh"],
        color="#111827",
        linewidth=2.2,
        marker="o",
        markersize=4.8,
        label="OEM SFOC reference",
        zorder=2,
    )

    seen_labels: set[str] = set()
    for _, row in active.sort_values(["timestep", "generator"]).iterrows():
        module = row.get("module", "")
        label = str(row.get("module_label", module or "Unlabeled"))
        scatter_label = label if label not in seen_labels else None
        ax.scatter(
            row["Pg_kw"],
            row["sfoc_gkwh"],
            s=38,
            alpha=0.82,
            color=MODULE_COLORS.get(module, "#64748B"),
            edgecolor="white",
            linewidth=0.45,
            label=scatter_label,
            zorder=3,
        )
        if scatter_label is not None:
            seen_labels.add(label)

    ax.set_xlabel("Generator power [kW]", fontsize=BASE_FONT + 2)
    ax.set_ylabel("SFOC [g/kWh]", fontsize=BASE_FONT + 2)
    ax.set_xlim(oem["P_kw"].min() - 10, oem["P_kw"].max() + 12)
    ax.set_ylim(190.5, 198.5)
    ax.grid(alpha=0.25)
    ax.tick_params(axis="both", labelsize=BASE_FONT + 1)
    ax.legend(
        loc="lower right",
        fontsize=BASE_FONT - 3,
        frameon=True,
        borderpad=0.45,
        labelspacing=0.35,
    )

    out_dir = run_dir / "plots"
    out_dir.mkdir(parents=True, exist_ok=True)
    png_path = out_dir / "verification_oem_sfoc_reference_points_by_module.png"
    pdf_path = out_dir / "verification_oem_sfoc_reference_points_by_module.pdf"
    fig.savefig(png_path, dpi=180, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight")
    plt.close(fig)

    # Confirm the plotted dispatch SFOC values are model-implied output values,
    # equivalent to fuel_gph / Pg_kw within CSV rounding.
    active_nonzero = active[active["Pg_kw"] > 1e-9].copy()
    active_nonzero["sfoc_from_fuel"] = active_nonzero["fuel_gph"] / active_nonzero["Pg_kw"]
    max_delta = (active_nonzero["sfoc_gkwh"] - active_nonzero["sfoc_from_fuel"]).abs().max()

    return png_path, pdf_path, float(max_delta)


def main() -> None:
    args = parse_args()
    run_dir = args.run_dir.resolve()
    png_path, pdf_path, max_delta = plot_oem_sfoc_reference(run_dir)
    print(f"Saved {png_path}")
    print(f"Saved {pdf_path}")
    print(f"Dispatch point SFOC source: dispatch_results.csv sfoc_gkwh")
    print(f"Max |sfoc_gkwh - fuel_gph/Pg_kw| = {max_delta:.9g} g/kWh")


if __name__ == "__main__":
    main()
