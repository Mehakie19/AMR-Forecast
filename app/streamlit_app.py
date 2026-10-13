"""AMR-Sense Streamlit multipage entry."""

from __future__ import annotations

import os

import requests
import streamlit as st

API_URL = os.environ.get("AMR_SENSE_API", "http://127.0.0.1:8000")
DISCLAIMER = (
    "Surveillance and research tool. Not for treatment decisions. "
    "Predicted resistance is not the probability of clinical cure. "
    "'High risk' and 'rising' thresholds are project-defined."
)


def api_get(path: str):
    try:
        r = requests.get(f"{API_URL}{path}", timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as exc:
        st.error(f"API unavailable ({API_URL}): {exc}")
        return None


st.set_page_config(page_title="AMR-Sense", layout="wide")
st.warning(DISCLAIMER)

health = api_get("/health")
if health:
    st.caption(
        f"API: {health.get('status')} | data_version: {health.get('data_version')} | "
        f"FROZEN: {health.get('frozen')}"
    )

st.title("AMR-Sense — Home")
st.markdown(
    """
Research-oriented AMR early-warning and decision-support from GLASS-AMR and ECDC-derived surveillance data.

Use the sidebar pages for EDA, features, model results, forecasts, watchlist, and methods.
"""
)

summary = api_get("/datasets/summary?source=combined")
if summary:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rows", summary["rows"])
    c2.metric("Series", summary["series"])
    c3.metric("Countries", summary["countries"])
    c4.metric("Years", f"{summary['years'][0]}–{summary['years'][1]}")
    st.info(
        "Combined scope: sources use different resistance definitions (GLASS: R; ECDC: I+R). "
        "Do not compare levels directly."
    )
    st.subheader("Key takeaway")
    st.success(
        f"Dataset holds {summary['rows']} rows across {summary['countries']} countries "
        f"and {summary['series']} surveillance series."
    )
