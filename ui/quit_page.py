"""Quit page."""

from __future__ import annotations

import streamlit as st


def render() -> None:
    """Render the non-destructive goodbye page."""
    st.success("Merci d'avoir utilisé l'application")
    st.write("Vous pouvez fermer cet onglet.")
    if st.button("Retour au menu", key="quit_back"):
        st.session_state.page = "home"
        st.rerun()

