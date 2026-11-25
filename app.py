"""Entry point: `streamlit run app.py`."""

import logging

import streamlit as st

from stt.app_context import render_sidebar, show_flash

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

st.set_page_config(page_title="Speech to Text", page_icon="🎙️", layout="wide")

pages = st.navigation(
    [
        st.Page("views/live.py", title="Live Transcription", icon="🎙️", default=True),
        st.Page("views/dashboard.py", title="History Dashboard", icon="📚"),
    ]
)
render_sidebar()
show_flash()
pages.run()
