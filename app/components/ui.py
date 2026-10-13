"""Common UI components, color palettes, and API utilities for AMR-Sense Streamlit app."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

import requests
import streamlit as st

API_URL = os.environ.get("AMR_SENSE_API", "http://127.0.0.1:8000")

DISCLAIMER_TEXT = (
    "Surveillance and research tool. Not for treatment decisions. "
    "Predicted resistance is not the probability of clinical cure. "
    "'High risk' and 'rising' thresholds are project-defined."
)

COMBINED_NOTICE = (
    "Sources use different resistance definitions (GLASS: R; ECDC: I+R). "
    "Do not compare levels directly."
)

# Color-blind safe curated palettes
SOURCE_COLORS = {
    "GLASS": "#0284c7",  # Sky / Blue
    "ECDC": "#d97706",   # Amber / Orange
    "Pooled": "#7c3aed", # Violet
    "GLASS-AMR": "#0284c7",
    "ECDC-derived": "#d97706",
    "Combined": "#475569"
}

PATHOGEN_COLORS = {
    "Escherichia coli": "#2563eb",       # Blue
    "Klebsiella pneumoniae": "#059669",  # Emerald
    "Acinetobacter spp.": "#dc2626"     # Red
}

METRIC_TOOLTIPS = {
    "PR-AUC": "Area under Precision-Recall curve. Primary metric for imbalanced surveillance flagging.",
    "ROC-AUC": "Area under Receiver Operating Characteristic curve. Measures ranking capability across all thresholds.",
    "Recall": "Fraction of true high-risk or rising cases detected by the alarm (Sensitivity).",
    "Precision": "Fraction of alerts that are true high-risk or rising cases (Positive Predictive Value).",
    "F1": "Harmonic mean of precision and recall at the selected decision threshold.",
    "False-alert rate": "FP / (FP + TN). Fraction of safe series incorrectly flagged.",
    "Brier score": "Mean squared error of probabilistic predictions. Lower is better (0 = perfect calibration).",
    "MAE": "Mean Absolute Error in percentage points (pp) between forecast and observed resistance."
}


@st.cache_data(ttl=120, show_spinner=False)
def api_get(path: str, params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
    """Cached GET request to AMR-Sense API."""
    try:
        url = f"{API_URL}{path}"
        r = requests.get(url, params=params, timeout=12)
        r.raise_for_status()
        return r.json()
    except requests.RequestException:
        return None


def api_post(path: str, json_data: Dict[str, Any]) -> Optional[Any]:
    """POST request to AMR-Sense API."""
    try:
        url = f"{API_URL}{path}"
        r = requests.post(url, json=json_data, timeout=15)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as exc:
        st.error(f"API request failed: {exc}")
        return None


def render_banner_and_header(page_title: str) -> Dict[str, Any]:
    """Renders the persistent warning banner, status strip, and page title."""
    st.warning(f"⚠️ **Disclaimer:** {DISCLAIMER_TEXT}")

    health = api_get("/health")
    if health:
        c1, c2, c3, c4 = st.columns([2, 3, 2, 2])
        c1.caption(f"**API Status:** {health.get('status', 'ok')}")
        c2.caption(f"**Data Version:** `{health.get('data_version', 'unknown')}`")
        frozen_str = "Frozen (Final-Test Unlocked)" if health.get("frozen") else "Training Mode"
        c3.caption(f"**Models:** {frozen_str}")
        c4.caption(f"**Seed:** {health.get('seed', 42)}")
    else:
        st.info("💡 Note: AMR-Sense API is not reachable at default port 8000. Start API with `uvicorn api.main:app`.")

    st.title(page_title)
    return health or {}


def render_sidebar(allow_pathogen_filter: bool = True, allow_antibiotic_filter: bool = True) -> Dict[str, Any]:
    """Renders persistent sidebar scope controls and filters."""
    st.sidebar.header("Scope & Filters")
    scope = st.sidebar.selectbox(
        "Data Scope",
        options=["Combined", "GLASS-AMR", "ECDC-derived"],
        index=0,
        help="Filter data by surveillance initiative or pooled combined dataset."
    )

    source_param = "combined"
    if scope == "GLASS-AMR":
        source_param = "glass"
    elif scope == "ECDC-derived":
        source_param = "ecdc"

    if scope == "Combined":
        st.sidebar.warning(f"ℹ️ **Combined Notice:** {COMBINED_NOTICE}")

    filters = {"scope": scope, "source": source_param}

    if allow_pathogen_filter:
        pathogen = st.sidebar.selectbox(
            "Pathogen",
            options=["All", "Escherichia coli", "Klebsiella pneumoniae", "Acinetobacter spp."],
            index=0
        )
        filters["pathogen"] = None if pathogen == "All" else pathogen

    if allow_antibiotic_filter:
        antibiotic_options = [
            "All", "Amikacin", "Gentamicin", "Ceftazidime", "Ceftriaxone",
            "Ciprofloxacin", "Ertapenem", "Imipenem", "Meropenem", "Colistin"
        ]
        abx = st.sidebar.selectbox("Antibiotic", options=antibiotic_options, index=0)
        filters["antibiotic"] = None if abx == "All" else abx

    min_tested = st.sidebar.slider("Minimum Tested Isolates (N)", min_value=0, max_value=200, value=30, step=10)
    filters["min_tested"] = min_tested

    return filters


def render_key_takeaway(text: str):
    """Renders an evidence-grounded key takeaway box."""
    st.markdown("---")
    st.subheader("💡 Key Takeaway")
    st.success(text)


def render_chart_expander(title: str, explanation: str):
    """Renders a collapsible 'How to read this' box."""
    with st.expander(f"ℹ️ How to read: {title}"):
        st.markdown(explanation)
