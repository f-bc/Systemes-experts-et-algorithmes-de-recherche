"""Reusable presentation and error helpers."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import streamlit as st

from core.errors import ValidationError
from core.search.models import SearchResult
from core.text import fmt_num


def show_validation_error(error: ValidationError) -> None:
    """Display every validation message as a bullet list."""
    st.error("\n".join(f"- {message}" for message in error.messages))


def show_unexpected_error(error: Exception) -> None:
    """Display an unexpected error without exposing a traceback."""
    st.error(f"Erreur inattendue : {error}")


def rule_line(text: str) -> None:
    """Display one rule in a compact monospace block."""
    st.markdown(f"`{text}`")


def search_result_panel(result: SearchResult) -> None:
    """Render a search result and its statistics."""
    if result.found:
        st.success("Chemin trouvé")
        st.write(f"Chemin : {' → '.join(result.path)}")
        st.write(f"Coût : {fmt_num(result.cost)} · Longueur : {result.stats.solution_length}")
    elif result.status == "aborted_iteration_cap":
        st.error("Arrêt : limite d'itérations atteinte")
        st.write(result.message)
    else:
        st.error("Aucun chemin trouvé")
        st.write(result.message)
    stats = result.stats
    st.table(
        {
            "Itérations": [stats.iterations],
            "Nœuds développés": [stats.nodes_expanded],
            "Nœuds générés": [stats.nodes_generated],
            "Taille max de la frontière": [stats.max_frontier_size],
            "Profondeur max atteinte": [stats.max_depth_reached],
            "Longueur de la solution": [stats.solution_length],
            "Temps (ms)": [round(stats.runtime_ms, 3)],
        }
    )


def render_facts(facts: Iterable[str]) -> None:
    """Render facts as inline chips."""
    st.write(" · ".join(facts) if facts else "Aucun fait.")

