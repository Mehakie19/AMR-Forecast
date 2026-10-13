"""Load and expose project configuration from config.yaml."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config" / "config.yaml"


def load_config(path: Path | None = None) -> dict[str, Any]:
    """Load YAML configuration."""
    cfg_path = path or CONFIG_PATH
    with open(cfg_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def config_hash(cfg: dict[str, Any] | None = None) -> str:
    """Stable hash of configuration for data_version."""
    cfg = cfg or load_config()
    blob = json.dumps(cfg, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def data_version(combined_path: Path | None = None) -> str:
    """Hash of combined dataset file + config."""
    cfg = load_config()
    path = combined_path or (ROOT / cfg["paths"]["raw_combined"])
    h_data = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    return f"{h_data}-{config_hash(cfg)}"
