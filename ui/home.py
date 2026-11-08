"""Home page for the application."""

from __future__ import annotations

import streamlit as st


def render() -> None:
    """Render the main menu."""
    st.title("Systèmes experts et algorithmes de recherche")
    st.write("Explorez les systèmes experts et les algorithmes de recherche du cours.")
    left, right = st.columns(2)
    with left:
        st.markdown(
            '<div class="app-card app-card-expert"><h3>🧠 Systèmes experts</h3>'
            "<p>Bases de faits et de règles · chaînage avant · chaînage arrière · "
            "explication du raisonnement</p></div>",
            unsafe_allow_html=True,
        )
        if st.button("Ouvrir le module", key="home_open_expert"):
            st.session_state.page = "expert"
            st.rerun()
    with right:
        st.markdown(
            '<div class="app-card"><h3>🔎 Algorithmes de recherche</h3>'
            "<p>Graphes orientés pondérés · 10 algorithmes du cours · "
            "visualisation pas à pas · comparaison</p></div>",
            unsafe_allow_html=True,
        )
        if st.button("Ouvrir le module", key="home_open_search"):
            st.session_state.page = "search"
            st.rerun()
    if st.button("3. Quitter", key="home_quit"):
        st.session_state.page = "quit"
        st.rerun()
