from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert "disclaimer" in body
    assert "data_version" in body
    assert body["status"] == "ok"
    assert "configurations" in body


def test_methods():
    r = client.get("/methods")
    assert r.status_code == 200
    body = r.json()
    assert "disclaimer" in body
    assert "thresholds" in body
    assert "limitations" in body


def test_datasets_summary():
    r = client.get("/datasets/summary?source=glass")
    assert r.status_code == 200
    body = r.json()
    assert "rows" in body
    assert body["rows"] == 2394
    assert "disclaimer" in body


def test_datasets_quality():
    r = client.get("/datasets/quality")
    assert r.status_code == 200
    body = r.json()
    assert "missingness" in body
    assert "duplicates" in body
    assert body["duplicates"] == 0


def test_features_dictionary():
    r = client.get("/features/dictionary")
    assert r.status_code == 200
    body = r.json()
    assert "features" in body
    assert len(body["features"]) >= 20


def test_series_history():
    r = client.get("/series", params={
        "source": "glass",
        "iso3": "ARE",
        "pathogen": "Acinetobacter spp.",
        "antibiotic": "Amikacin",
    })
    assert r.status_code == 200
    body = r.json()
    assert "history" in body
    assert len(body["history"]) >= 2


def test_predict_invalid_series_422():
    r = client.post("/predict", json={
        "source": "glass",
        "iso3": "INVALID",
        "pathogen": "Escherichia coli",
        "antibiotic": "Amikacin",
        "model_config": "glass",
    })
    assert r.status_code == 422
