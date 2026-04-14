from __future__ import annotations

import csv
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CASE_ROOT = REPO_ROOT / "analysis" / "sfoc_cases"
INDEX_CSV = CASE_ROOT / "case_index.csv"
INDEX_MD = CASE_ROOT / "case_index.md"


def load_manifests() -> list[dict[str, object]]:
    manifests: list[dict[str, object]] = []
    if not CASE_ROOT.is_dir():
        return manifests
    for manifest_path in sorted(CASE_ROOT.glob("*/case_manifest.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["case_dir"] = str(manifest_path.parent.relative_to(REPO_ROOT))
        manifests.append(manifest)
    return manifests


def write_csv(manifests: list[dict[str, object]]) -> None:
    CASE_ROOT.mkdir(parents=True, exist_ok=True)
    with INDEX_CSV.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            [
                "case_label",
                "case_dir",
                "rows",
                "steady_points",
                "start",
                "end",
                "regime_counts",
                "data_paths",
            ]
        )
        for item in manifests:
            writer.writerow(
                [
                    item["case_label"],
                    item["case_dir"],
                    item["rows"],
                    item["steady_points"],
                    item["time_range"]["start"],
                    item["time_range"]["end"],
                    json.dumps(item["regime_counts"], ensure_ascii=True, sort_keys=True),
                    json.dumps(item["data_paths"], ensure_ascii=True),
                ]
            )


def write_markdown(manifests: list[dict[str, object]]) -> None:
    lines = [
        "# SFOC Case Index",
        "",
        "Each case below has its own preserved output directory under `analysis/sfoc_cases/`.",
        "",
        "| Case | Folder | Rows | Steady points | Time range | Sources |",
        "| --- | --- | ---: | ---: | --- | --- |",
    ]
    for item in manifests:
        sources = "<br>".join(item["data_paths"])
        time_range = f"{item['time_range']['start']} to {item['time_range']['end']}"
        lines.append(
            f"| {item['case_label']} | `{item['case_dir']}` | {item['rows']} | {item['steady_points']} | {time_range} | {sources} |"
        )
    INDEX_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    manifests = load_manifests()
    write_csv(manifests)
    write_markdown(manifests)
    print(f"Saved {INDEX_CSV}")
    print(f"Saved {INDEX_MD}")


if __name__ == "__main__":
    main()
