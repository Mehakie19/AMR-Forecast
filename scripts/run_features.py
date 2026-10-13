#!/usr/bin/env python
"""Stage 2: build panel features and feature dictionary."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from amr_sense.config import load_config
from amr_sense.data import load_combined
from amr_sense.features import build_features_for_panel, write_feature_dictionary
from amr_sense.panel import build_eligible_panel, classification_eligible, report_classification_filter


def main() -> None:
    cfg = load_config()
    raw = load_combined()
    out_dir = ROOT / cfg["paths"]["processed_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)

    for name in ["glass", "ecdc", "pooled"]:
        panel = build_features_for_panel(raw, name)
        path = out_dir / f"panel_{name}.parquet"
        panel.to_parquet(path, index=False)
        print(f"Wrote {path} ({len(panel)} rows)")

    ep = build_eligible_panel(raw)
    removed = report_classification_filter(ep)
    print("Classification filter rows removed per source:", removed)

    write_feature_dictionary(ROOT / cfg["paths"]["reports_results"] / "feature_dictionary.md")
    print("Features complete.")


if __name__ == "__main__":
    main()
