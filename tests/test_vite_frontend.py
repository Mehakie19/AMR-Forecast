"""Tests verifying Vite frontend structure, disclaimer banner, and build integrity."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"


def test_vite_package_json():
    pkg_file = FRONTEND / "package.json"
    assert pkg_file.exists(), "frontend/package.json must exist"
    data = json.loads(pkg_file.read_text(encoding="utf-8"))
    assert "vite" in data.get("devDependencies", {}) or "vite" in data.get("dependencies", {})
    assert "react" in data.get("dependencies", {})


def test_vite_pages_exist():
    pages_dir = FRONTEND / "src" / "pages"
    assert pages_dir.exists()
    required_pages = [
        "DatasetOverview.jsx",
        "EdaExplorer.jsx",
        "FeatureEngineering.jsx",
        "ModelLab.jsx",
        "ForecastExplorer.jsx",
        "IntelligenceOverview.jsx",
    ]
    for page in required_pages:
        assert (pages_dir / page).exists(), f"Page {page} missing in frontend/src/pages"


def test_vite_global_disclaimer_removed():
    app_jsx = (FRONTEND / "src" / "App.jsx").read_text(encoding="utf-8")
    assert "disclaimer-banner" not in app_jsx
    assert "Research and surveillance only" not in app_jsx


def test_country_map_asset_exists():
    map_data = FRONTEND / "public" / "data" / "ne_110m_admin_0_countries.geojson"
    assert map_data.exists(), "Interactive overview requires the local Natural Earth country map"


def test_vite_build_artifact_exists():
    dist_html = FRONTEND / "dist" / "index.html"
    assert dist_html.exists(), "frontend/dist/index.html must exist from build"
