"""Streamlit session-state initialization and mutation helpers."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import streamlit as st

from core.expert.examples import EXAMPLE_KBS
from core.expert.models import KnowledgeBase
from core.search.examples import EXAMPLE_GRAPHS
from core.search.models import SearchGraph, SearchParams


def init_state() -> None:
    """Initialize all application-owned session keys once."""
    defaults: dict[str, Any] = {
        "page": "home",
        "es_kb": EXAMPLE_KBS["tarte"].kb.copy(),
        "es_goal": "tarte aux abricots",
        "es_method": "forward",
        "es_stop_at_goal": True,
        "es_result": None,
        "es_signature": None,
        "es_step": 0,
        "sa_graph": EXAMPLE_GRAPHS["g1"].graph.copy(),
        "sa_category": "uninformed",
        "sa_algo": "bfs",
        "sa_params": replace(EXAMPLE_GRAPHS["g1"].suggested_params),
        "sa_result": None,
        "sa_signature": None,
        "sa_step": 0,
        "sa_compare": None,
        "sa_layout": None,
        "sa_layout_signature": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def expert_signature() -> str:
    """Return the signature of the current expert run inputs."""
    return (
        f"{st.session_state.es_kb.signature()}|{st.session_state.es_goal}|"
        f"{st.session_state.es_method}|{st.session_state.es_stop_at_goal}"
    )


def search_signature() -> str:
    """Return the signature of the current search run inputs."""
    return (
        f"{st.session_state.sa_graph.signature()}|{st.session_state.sa_algo}|"
        f"{st.session_state.sa_params!r}"
    )


def invalidate_expert_run() -> None:
    """Clear the stored expert result and navigation."""
    st.session_state.es_result = None
    st.session_state.es_signature = None
    st.session_state.es_step = 0


def invalidate_search_run() -> None:
    """Clear the stored search result, comparison and navigation."""
    st.session_state.sa_result = None
    st.session_state.sa_signature = None
    st.session_state.sa_step = 0
    st.session_state.sa_compare = None


def set_page(page: str) -> None:
    """Navigate to a known application page."""
    if page in {"home", "expert", "search", "quit"}:
        st.session_state.page = page


def replace_kb(kb: KnowledgeBase) -> None:
    """Replace the knowledge base with an independent copy."""
    st.session_state.es_kb = kb.copy()
    invalidate_expert_run()


def replace_graph(graph: SearchGraph) -> None:
    """Replace the graph with an independent copy."""
    st.session_state.sa_graph = graph.copy()
    invalidate_search_run()
    st.session_state.sa_layout = None

