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
        "SurveillanceWatchlist.jsx",
        "MethodsLimitations.jsx",
    ]
    for page in required_pages:
        assert (pages_dir / page).exists(), f"Page {page} missing in frontend/src/pages"


def test_vite_disclaimer_present():
    app_jsx = (FRONTEND / "src" / "App.jsx").read_text(encoding="utf-8")
    assert "Surveillance and research tool" in app_jsx
    assert "Predicted resistance is not the probability of clinical cure" in app_jsx


def test_vite_build_artifact_exists():
    dist_html = FRONTEND / "dist" / "index.html"
    assert dist_html.exists(), "frontend/dist/index.html must exist from build"
