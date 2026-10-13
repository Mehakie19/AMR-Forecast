#!/usr/bin/env python
"""Build combined dataset from GLASS and ECDC sources (already provided in data/raw/)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMBINED = ROOT / "data" / "raw" / "combined_amr_dataset.csv"


def main() -> None:
    if not COMBINED.exists():
        raise SystemExit(f"Missing {COMBINED}; place combined_amr_dataset.csv in data/raw/.")
    print(f"Combined dataset already present at {COMBINED} ({COMBINED.stat().st_size} bytes).")


if __name__ == "__main__":
    main()
