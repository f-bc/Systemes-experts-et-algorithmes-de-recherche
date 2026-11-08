"""Small visual helpers for the Streamlit interface."""

from __future__ import annotations

import streamlit as st


def apply_theme() -> None:
    """Apply minimal layout styling while preserving Streamlit defaults."""
    st.markdown(
        """
        <style>
        .block-container { max-width: 1400px; padding-top: 2rem; }
        .app-card { box-sizing: border-box; min-height: 180px;
                    padding: 1.2rem; border: 1px solid #D9E2EC;
                    border-radius: .7rem; background: #FFFFFF; }
        .app-card-expert { min-height: 205px; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str, back_key: str) -> None:
    """Render a page title and a stable return button."""
    st.title(title)
    st.caption(subtitle)
    if st.button("← Menu principal", key=back_key):
        st.session_state.page = "home"
        st.rerun()
