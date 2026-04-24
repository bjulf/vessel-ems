from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "config" / "baseline_model_no_terminal_soc_startup1000g.toml"
SWEEP_SCRIPTS = [
    "startup_cost_sensitivity.py",
    "soc_min_sensitivity.py",
    "initial_soc_sensitivity.py",
    "battery_efficiency_sensitivity.py",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the no-terminal sensitivity package for the 1000 g/start baseline. "
            "Outputs are written to analysis/output/sensitivity_new_baseline_startupcost1000g/."
        )
    )
    parser.add_argument(
        "config",
        nargs="?",
        default=str(DEFAULT_CONFIG),
        help="Config path relative to repo root or absolute path. Defaults to the 1000 g/start no-terminal baseline config.",
    )
    return parser.parse_args()


def resolve_repo_path(path_str: str) -> Path:
    path = Path(path_str)
    return path if path.is_absolute() else (REPO_ROOT / path).resolve()


def main() -> None:
    args = parse_args()
    config_path = resolve_repo_path(args.config)
    if not config_path.exists():
        raise FileNotFoundError(f"Missing config file: {config_path}")
    if not config_path.is_relative_to(REPO_ROOT):
        raise ValueError("Config path must be inside the repository.")

    rel_config = config_path.relative_to(REPO_ROOT)

    for script_name in SWEEP_SCRIPTS:
        script_path = Path("analysis") / script_name
        print(f"Running {script_path} with {rel_config}")
        subprocess.run(
            [sys.executable, str(script_path), str(rel_config)],
            cwd=REPO_ROOT,
            check=True,
        )

    print("Completed startup-1000g no-terminal sensitivity package.")
    print(f"Outputs: {REPO_ROOT / 'analysis' / 'output' / 'sensitivity_new_baseline_startupcost1000g'}")


if __name__ == "__main__":
    main()
