"""Streamlit AppTest smoke tests."""

from __future__ import annotations

import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PAGE_FILES = [
    "app/streamlit_app.py",
    "app/pages/1_Dataset_Overview.py",
    "app/pages/2_EDA_Explorer.py",
    "app/pages/3_Features.py",
    "app/pages/4_Model_Lab.py",
    "app/pages/5_Forecast_Explorer.py",
    "app/pages/6_Surveillance_Watchlist.py",
    "app/pages/7_Methods_and_Limitations.py",
]


@pytest.mark.parametrize("page_path", PAGE_FILES)
def test_page_loads_and_has_disclaimer(page_path: str):
    from streamlit.testing.v1 import AppTest

    file_path = str(ROOT / page_path)
    at = AppTest.from_file(file_path)
    at.run(timeout=30)
    assert not at.exception, f"Exception on {page_path}: {at.exception}"

    # Check for disclaimer banner in warnings or text
    all_warnings = " ".join(str(w.value) for w in at.warning)
    assert "Surveillance and research tool" in all_warnings or "disclaimer" in all_warnings.lower()


def test_sidebar_scope_switch():
    from streamlit.testing.v1 import AppTest

    file_path = str(ROOT / "app" / "pages" / "1_Dataset_Overview.py")
    at = AppTest.from_file(file_path)
    at.run(timeout=30)
    assert not at.exception

    # Check sidebar selectbox for scope exists
    if len(at.sidebar.selectbox) > 0:
        scope_box = at.sidebar.selectbox[0]
        # select GLASS-AMR (index 1)
        scope_box.select("GLASS-AMR")
        at.run(timeout=30)
        assert not at.exception

