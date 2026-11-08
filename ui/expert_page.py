"""Expert-system Streamlit page."""

from __future__ import annotations

import logging

import streamlit as st

from core.errors import ValidationError
from core.expert.backward import backward_chaining
from core.expert.examples import EXAMPLE_KBS
from core.expert.explain import explain_forward
from core.expert.forward import forward_chaining
from core.expert.io import kb_from_json, kb_to_json
from core.expert.models import ProofNode
from core.expert.parsing import parse_facts_text, parse_rule_text
from core.search.visualization import draw_proof_tree
from ui.components import render_facts, show_unexpected_error, show_validation_error
from ui.theme import page_header
from ui.state import invalidate_expert_run, replace_kb

LOGGER = logging.getLogger(__name__)


def _goal() -> str:
    kb = st.session_state.es_kb
    options = [*kb.universe(), "✎ Autre…"]
    index = options.index(st.session_state.es_goal) if st.session_state.es_goal in options else 0
    selected = st.selectbox("Objectif", options, index=index, key="es_goal_select")
    custom = st.text_input("Objectif personnalisé", key="es_goal_custom")
    goal = custom.strip() if selected == "✎ Autre…" and custom.strip() else selected
    if goal != st.session_state.es_goal:
        st.session_state.es_goal = goal
        invalidate_expert_run()
    return goal


def _run() -> None:
    try:
        kb = st.session_state.es_kb.copy()
        if st.session_state.es_method == "forward":
            result = forward_chaining(
                kb, st.session_state.es_goal, st.session_state.es_stop_at_goal
            )
        else:
            result = backward_chaining(kb, st.session_state.es_goal)
        st.session_state.es_result = result
        st.session_state.es_signature = (
            st.session_state.es_kb.signature()
            + "|"
            + st.session_state.es_goal
            + "|"
            + st.session_state.es_method
            + "|"
            + str(st.session_state.es_stop_at_goal)
        )
        st.session_state.es_step = 1 if result.steps else 0
    except ValidationError as error:
        show_validation_error(error)
    except Exception as error:
        LOGGER.exception("Expert run failed")
        show_unexpected_error(error)


def _proof_graph_data(
    root: ProofNode,
) -> tuple[list[tuple[str, str, str, int]], list[tuple[str, str]]]:
    """Convert a proof tree into renderer-neutral graph data."""
    nodes: list[tuple[str, str, str, int]] = []
    edges: list[tuple[str, str]] = []
    counter = 0

    def visit(node: ProofNode, depth: int, parent_id: str | None = None) -> None:
        nonlocal counter
        node_id = f"proof_{counter}"
        counter += 1
        nodes.append((node_id, node.goal, node.status, depth))
        if parent_id is not None:
            edges.append((parent_id, node_id))
        if node.status != "proved":
            return
        successful = next(
            (attempt for attempt in node.attempts if attempt.success), None
        )
        if successful is not None:
            for subproof in successful.subproofs:
                visit(subproof, depth + 1, node_id)

    visit(root, 0)
    return nodes, edges


def _render_reasoning() -> None:
    kb = st.session_state.es_kb
    goal = _goal()
    st.info("✔ Déjà dans la base de faits" if kb.has_fact(goal) else "○ Pas dans la base de faits")
    st.radio(
        "Méthode",
        ["forward", "backward"],
        key="es_method",
        format_func=lambda value: "Chaînage avant" if value == "forward" else "Chaînage arrière",
        on_change=invalidate_expert_run,
    )
    if st.session_state.es_method == "forward":
        st.checkbox(
            "S'arrêter quand l'objectif est atteint",
            key="es_stop_at_goal",
            on_change=invalidate_expert_run,
        )
    controls = st.columns(4)
    if controls[0].button("Lancer", key="es_run"):
        _run()
    if controls[1].button("Précédent", key="es_prev"):
        st.session_state.es_step = max(0, st.session_state.es_step - 1)
    if controls[2].button("Suivant", key="es_next"):
        limit = len(st.session_state.es_result.steps) if st.session_state.es_result else 0
        st.session_state.es_step = min(limit, st.session_state.es_step + 1)
    if controls[3].button("Tout exécuter", key="es_all"):
        if st.session_state.es_result is None:
            _run()
        if st.session_state.es_result is not None:
            st.session_state.es_step = len(st.session_state.es_result.steps)
    if st.button("Réinitialiser", key="es_reset"):
        invalidate_expert_run()

    result = st.session_state.es_result
    if result is None:
        return
    shown = result.steps[: st.session_state.es_step]
    if st.session_state.es_method == "forward":
        st.dataframe(
            [
                {
                    "N° inférence": step.index,
                    "Détection": ", ".join(step.detected),
                    "Choix": step.chosen,
                    "Déduction": ", ".join(step.facts_after),
                }
                for step in shown
            ],
            use_container_width=True,
        )
    else:
        st.subheader("Exécution pas à pas")
        for step in shown:
            with st.container(border=True):
                st.caption(
                    f"Étape {step.index} · {step.kind} · "
                    f"Profondeur {step.depth}"
                )
                st.write(step.message)
                if step.goal_stack:
                    st.caption(
                        "Pile des buts : " + " → ".join(step.goal_stack)
                    )
    if st.session_state.es_step >= len(result.steps):
        if result.success:
            st.success("Objectif prouvé")
        else:
            st.error("Objectif non démontrable")
        st.write("Faits finaux :")
        render_facts(result.final_facts)
        if st.session_state.es_method == "forward":
            st.write("Explication :")
            for rule_id, premises, conclusion in explain_forward(result, goal):
                st.write(f"{rule_id} : {' ∧ '.join(premises)} ⇒ {conclusion}")
        else:
            st.subheader("Arbre de preuve")
            st.caption(
                "Le but est la racine ; les prémisses de chaque règle sont "
                "affichées comme ses sous-buts."
            )
            proof_nodes, proof_edges = _proof_graph_data(result.proof)
            figure = draw_proof_tree(proof_nodes, proof_edges)
            st.pyplot(figure)
            figure.clf()


def _render_editor() -> None:
    kb = st.session_state.es_kb
    st.write("Faits initiaux")
    render_facts(kb.facts)
    st.write("Règles")
    for rule in kb.rules:
        st.markdown(f"`{rule.to_text()}`")
    st.text_input("Nouveau fait", key="es_new_fact")
    if st.button("Ajouter le fait", key="es_add_fact"):
        try:
            for fact in parse_facts_text(st.session_state.es_new_fact):
                kb.add_fact(fact)
            invalidate_expert_run()
        except ValidationError as error:
            show_validation_error(error)
    facts = kb.facts or [""]
    st.selectbox("Supprimer un fait", facts, key="es_remove_fact_select")
    if st.button("Supprimer", key="es_remove_fact") and kb.facts:
        try:
            kb.remove_fact(st.session_state.es_remove_fact_select)
            invalidate_expert_run()
        except ValidationError as error:
            show_validation_error(error)
    st.text_input("Nouvelle règle", key="es_new_rule", placeholder="SI A ET B ALORS C")
    if st.button("Ajouter la règle", key="es_add_rule"):
        try:
            for premises, conclusion in parse_rule_text(st.session_state.es_new_rule):
                kb.add_rule(premises, conclusion)
            invalidate_expert_run()
        except ValidationError as error:
            show_validation_error(error)
    rule_ids = [rule.id for rule in kb.rules] or [""]
    st.selectbox("Modifier une règle", rule_ids, key="es_edit_rule_select")
    if kb.rules:
        selected = next(rule for rule in kb.rules if rule.id == st.session_state.es_edit_rule_select)
        st.text_input("Texte de la règle", value=selected.to_text(False), key="es_edit_rule_text")
        if st.button("Supprimer la règle", key="es_delete_rule"):
            kb.remove_rule(selected.id)
            invalidate_expert_run()
        if st.button("Mettre à jour la règle", key="es_update_rule"):
            try:
                parsed = parse_rule_text(st.session_state.es_edit_rule_text)
                premises, conclusion = parsed[0]
                kb.update_rule(selected.id, premises, conclusion)
                invalidate_expert_run()
            except ValidationError as error:
                show_validation_error(error)
    st.selectbox("Charger un exemple", list(EXAMPLE_KBS), key="es_example_select")
    if st.button("Charger l'exemple", key="es_load_example"):
        replace_kb(EXAMPLE_KBS[st.session_state.es_example_select].kb)
    st.download_button("Enregistrer", kb_to_json(kb), "knowledge_base.json", key="es_download")
    uploaded = st.file_uploader("Charger un fichier", type="json", key="es_upload")
    if st.button("Charger", key="es_load_file") and uploaded is not None:
        try:
            replace_kb(kb_from_json(uploaded.getvalue().decode("utf-8")))
        except ValidationError as error:
            show_validation_error(error)
        except Exception as error:
            LOGGER.exception("KB load failed")
            show_unexpected_error(error)


def render() -> None:
    """Render the expert module."""
    page_header("Systèmes experts", "Chaînage avant et chaînage arrière.", "back_menu_expert")
    reasoning, editor, about = st.tabs(
        ["Raisonnement", "Base de connaissances", "À propos du chaînage"]
    )
    with reasoning:
        _render_reasoning()
    with editor:
        _render_editor()
    with about:
        st.write("Le chaînage avant est piloté par les données ; le chaînage arrière est piloté par le but.")
