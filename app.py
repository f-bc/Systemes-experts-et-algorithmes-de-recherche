"""Streamlit entry point and page router."""

from __future__ import annotations

import streamlit as st

from ui import state
from ui.home import render as render_home
from ui.quit_page import render as render_quit
from ui.expert_page import render as render_expert
from ui.search_page import render as render_search
from ui.theme import apply_theme


def _navigate_from_radio() -> None:
    """Navigate only after the user changes the sidebar radio."""
    selected = st.session_state.nav_radio
    st.session_state.page = {
        "1. Systèmes experts": "expert",
        "2. Algorithmes de recherche": "search",
        "3. Quitter": "quit",
    }[selected]


st.set_page_config(
    layout="wide",
    page_title="Expert Systems & Research Algorithms",
    page_icon="🧠",
)
state.init_state()
apply_theme()

with st.sidebar:
    st.title("Systèmes Experts & Algorithmes de Recherche")
    page_options = [
        "1. Systèmes experts",
        "2. Algorithmes de recherche",
        "3. Quitter",
    ]
    current = {"expert": 0, "search": 1, "quit": 2}.get(st.session_state.page, 0)
    st.radio(
        "Menu principal",
        page_options,
        index=current,
        key="nav_radio",
        on_change=_navigate_from_radio,
    )
    if st.button("Accueil", key="nav_home"):
        st.session_state.page = "home"
        st.rerun()

if st.session_state.page == "home":
    render_home()
elif st.session_state.page == "expert":
    render_expert()
elif st.session_state.page == "search":
    render_search()
else:
    render_quit()
