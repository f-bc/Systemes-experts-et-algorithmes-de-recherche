"""Search-algorithm Streamlit page."""

from __future__ import annotations

import logging
import math
from dataclasses import replace

import streamlit as st

from core.errors import ValidationError
from core.search.examples import EXAMPLE_GRAPHS
from core.search.heuristics import check_heuristic
from core.search.io import graph_from_json, graph_to_json
from core.search.models import SearchParams
from core.search.registry import (
    ALGORITHMS,
    algorithms_by_category,
    compare_algorithms,
    run_algorithm,
)
from core.search.visualization import compute_layout, draw_search_graph
from ui.components import search_result_panel, show_unexpected_error, show_validation_error
from ui.state import invalidate_search_run, replace_graph
from ui.theme import page_header

LOGGER = logging.getLogger(__name__)


def _update_params(**values: object) -> None:
    current = st.session_state.sa_params
    if any(getattr(current, key) != value for key, value in values.items()):
        st.session_state.sa_params = replace(current, **values)
        invalidate_search_run()


def _run() -> None:
    try:
        result = run_algorithm(
            st.session_state.sa_algo,
            st.session_state.sa_graph,
            st.session_state.sa_params,
        )
        st.session_state.sa_result = result
        st.session_state.sa_signature = (
            f"{st.session_state.sa_graph.signature()}|"
            f"{st.session_state.sa_algo}|{st.session_state.sa_params!r}"
        )
        st.session_state.sa_step = 0
    except ValidationError as error:
        show_validation_error(error)
    except Exception as error:
        LOGGER.exception("Search run failed")
        show_unexpected_error(error)


def _render_graph_editor() -> None:
    graph = st.session_state.sa_graph
    st.selectbox("Charger un exemple", list(EXAMPLE_GRAPHS), key="sa_example_select")
    if st.button("Charger l'exemple", key="sa_load_example"):
        replace_graph(EXAMPLE_GRAPHS[st.session_state.sa_example_select].graph)
        return
    st.text_input("Nouveau sommet", key="sa_new_vertex")
    if st.button("Ajouter le sommet", key="sa_add_vertex"):
        try:
            for name in st.session_state.sa_new_vertex.split(","):
                graph.add_vertex(name)
            invalidate_search_run()
        except ValidationError as error:
            show_validation_error(error)
    vertices = graph.vertices or [""]
    st.selectbox("Source", vertices, key="sa_edge_src")
    st.selectbox("Destination", vertices, key="sa_edge_dst")
    st.number_input("Coût de l'arc", min_value=0.0, step=1.0, key="sa_edge_cost")
    if st.button("Ajouter l'arc", key="sa_add_edge"):
        try:
            graph.add_edge(
                st.session_state.sa_edge_src,
                st.session_state.sa_edge_dst,
                st.session_state.sa_edge_cost,
            )
            invalidate_search_run()
        except ValidationError as error:
            show_validation_error(error)
    edge_labels = [f"{edge.source} → {edge.target}" for edge in graph.edges] or [""]
    st.selectbox("Arc à modifier", edge_labels, key="sa_edge_pick")
    st.number_input("Nouveau coût", min_value=0.0, step=1.0, key="sa_edge_newcost")
    if graph.edges and st.button("Modifier le coût", key="sa_update_edge"):
        edge = graph.edges[edge_labels.index(st.session_state.sa_edge_pick)]
        try:
            graph.update_edge_cost(edge.source, edge.target, st.session_state.sa_edge_newcost)
            invalidate_search_run()
        except ValidationError as error:
            show_validation_error(error)
    if graph.edges and st.button("Supprimer l'arc", key="sa_delete_edge"):
        edge = graph.edges[edge_labels.index(st.session_state.sa_edge_pick)]
        graph.remove_edge(edge.source, edge.target)
        invalidate_search_run()
    st.selectbox("Sommet à supprimer", vertices, key="sa_vertex_remove_select")
    if graph.vertices and st.button("Supprimer le sommet", key="sa_remove_vertex"):
        graph.remove_vertex(st.session_state.sa_vertex_remove_select)
        invalidate_search_run()
    start_options = [None, *graph.vertices]
    goal_options = [None, *graph.vertices]
    st.selectbox(
        "État initial", start_options,
        index=start_options.index(graph.start) if graph.start in start_options else 0,
        key="sa_start_select",
    )
    st.selectbox(
        "État but", goal_options,
        index=goal_options.index(graph.goal) if graph.goal in goal_options else 0,
        key="sa_goal_select",
    )
    if st.session_state.sa_start_select != graph.start:
        graph.start = st.session_state.sa_start_select
        invalidate_search_run()
    if st.session_state.sa_goal_select != graph.goal:
        graph.goal = st.session_state.sa_goal_select
        invalidate_search_run()
    for vertex in graph.vertices:
        st.number_input(
            f"Heuristique h({vertex})",
            min_value=0.0,
            key=f"sa_h_{vertex}",
            value=float(graph.heuristics.get(vertex, 0.0)),
        )
        if st.session_state[f"sa_h_{vertex}"] != graph.heuristics.get(vertex):
            graph.heuristics[vertex] = st.session_state[f"sa_h_{vertex}"]
            invalidate_search_run()
    st.download_button("Enregistrer", graph_to_json(graph), "graph.json", key="sa_download")
    uploaded = st.file_uploader("Charger un fichier", type="json", key="sa_upload")
    if st.button("Charger", key="sa_load_file") and uploaded is not None:
        try:
            replace_graph(graph_from_json(uploaded.getvalue().decode("utf-8")))
        except ValidationError as error:
            show_validation_error(error)
        except Exception as error:
            LOGGER.exception("Graph load failed")
            show_unexpected_error(error)


def _render_algorithm_controls() -> None:
    category = st.radio(
        "Catégorie",
        ["uninformed", "informed"],
        key="sa_category",
        format_func=lambda value: "Non informée" if value == "uninformed" else "Informée",
        on_change=invalidate_search_run,
    )
    infos = algorithms_by_category(category)
    keys = [info.key for info in infos]
    if st.session_state.sa_algo not in keys:
        st.session_state.sa_algo = keys[0]
        invalidate_search_run()
    st.selectbox(
        "Algorithme",
        keys,
        key="sa_algo",
        format_func=lambda key: ALGORITHMS[key].label,
        on_change=invalidate_search_run,
    )
    params = st.session_state.sa_params
    if "depth_limit" in ALGORITHMS[st.session_state.sa_algo].params_used:
        st.number_input("Limite de profondeur", min_value=0, step=1, key="sa_p_depth_limit",
                        value=params.depth_limit, on_change=lambda: _update_params(depth_limit=st.session_state.sa_p_depth_limit))
    if "max_depth" in ALGORITHMS[st.session_state.sa_algo].params_used:
        st.number_input("Profondeur maximale", min_value=1, step=1, key="sa_p_max_depth",
                        value=params.max_depth or 10, on_change=lambda: _update_params(max_depth=st.session_state.sa_p_max_depth))
    if "memory_limit" in ALGORITHMS[st.session_state.sa_algo].params_used:
        st.number_input("Limite mémoire", min_value=1, step=1, key="sa_p_memory_limit",
                        value=params.memory_limit, on_change=lambda: _update_params(memory_limit=st.session_state.sa_p_memory_limit))
    if "f_limit" in ALGORITHMS[st.session_state.sa_algo].params_used:
        infinite = st.checkbox("f_limit = ∞", value=math.isinf(params.f_limit), key="sa_p_f_inf")
        value = st.number_input("Limite f", min_value=0.0, step=1.0, value=0.0 if infinite else params.f_limit, key="sa_p_f_limit")
        desired_limit = math.inf if infinite else value
        if desired_limit != params.f_limit:
            _update_params(f_limit=desired_limit)
    if "dls_visited_mode" in ALGORITHMS[st.session_state.sa_algo].params_used:
        mode = st.selectbox("Mode DLS", ["course", "path"], key="sa_p_dls_mode",
                            format_func=lambda value: "Cours" if value == "course" else "Chemin")
        if mode != params.dls_visited_mode:
            _update_params(dls_visited_mode=mode)
    if "greedy_use_visited" in ALGORITHMS[st.session_state.sa_algo].params_used:
        visited = st.checkbox("Utiliser la liste des visités", value=params.greedy_use_visited, key="sa_p_greedy_visited")
        if visited != params.greedy_use_visited:
            _update_params(greedy_use_visited=visited)
    st.number_input("Itérations maximales", min_value=1, step=1, key="sa_p_max_iterations",
                    value=params.max_iterations, on_change=lambda: _update_params(max_iterations=st.session_state.sa_p_max_iterations))


def _render_execution() -> None:
    graph = st.session_state.sa_graph
    _render_algorithm_controls()
    controls = st.columns(4)
    if controls[0].button("Lancer", key="sa_run"):
        _run()
    if controls[1].button("Précédent", key="sa_prev") and st.session_state.sa_result:
        st.session_state.sa_step = max(0, st.session_state.sa_step - 1)
    if controls[2].button("Suivant", key="sa_next") and st.session_state.sa_result:
        st.session_state.sa_step = min(len(st.session_state.sa_result.steps) - 1, st.session_state.sa_step + 1)
    if controls[3].button("Tout exécuter", key="sa_all"):
        if st.session_state.sa_result is None:
            _run()
        if st.session_state.sa_result:
            st.session_state.sa_step = len(st.session_state.sa_result.steps) - 1
    if st.button("Réinitialiser", key="sa_reset"):
        invalidate_search_run()
    if graph.vertices:
        result = st.session_state.sa_result
        step = result.steps[st.session_state.sa_step] if result and result.steps else None
        try:
            signature = graph.signature()
            if st.session_state.sa_layout is None or st.session_state.sa_layout_signature != signature:
                st.session_state.sa_layout = compute_layout(graph)
                st.session_state.sa_layout_signature = signature
            figure = draw_search_graph(
                graph, step, result,
                show_final_path=bool(result and result.found and st.session_state.sa_step == len(result.steps) - 1),
                show_heuristics=st.session_state.sa_category == "informed",
                positions=st.session_state.sa_layout,
            )
            st.pyplot(figure)
            figure.clf()
        except Exception:
            st.warning("Impossible de dessiner le graphe.")
    else:
        st.info("Le graphe est vide : ajoutez des sommets.")
    result = st.session_state.sa_result
    if result:
        if st.session_state.sa_step == len(result.steps) - 1:
            search_result_panel(result)
        st.dataframe([{"Étape": step.index, "Type": step.kind, "Message": step.message} for step in result.steps[: st.session_state.sa_step + 1]])


def _render_compare() -> None:
    if st.button("Comparer", key="sa_compare_run"):
        try:
            st.session_state.sa_compare = compare_algorithms(
                st.session_state.sa_graph, st.session_state.sa_params
            )
        except ValidationError as error:
            show_validation_error(error)
    if st.session_state.sa_compare:
        st.dataframe(
            [
                {
                    "Algorithme": ALGORITHMS[result.algorithm_key].label,
                    "Catégorie": result.category,
                    "Trouvé": result.found,
                    "Coût": result.cost,
                    "Chemin": " → ".join(result.path),
                    "Itérations": result.stats.iterations,
                }
                for result in st.session_state.sa_compare
            ],
            use_container_width=True,
        )


def render() -> None:
    """Render the search module."""
    page_header("Algorithmes de recherche", "Dix algorithmes du cours sur un graphe orienté pondéré.", "back_menu_search")
    graph_tab, algorithm_tab = st.tabs(["Graphe", "Algorithme"])
    with graph_tab:
        _render_graph_editor()
        if st.session_state.sa_graph.vertices:
            diagnostics = check_heuristic(st.session_state.sa_graph)
            with st.expander("Propriétés de h"):
                st.write(f"admissible {'✔' if diagnostics.admissible else '✘'}")
                st.write(f"consistante {'✔' if diagnostics.consistent else '✘'}")
    with algorithm_tab:
        execution, comparison = st.tabs(["Exécution", "Comparaison"])
        with execution:
            _render_execution()
        with comparison:
            _render_compare()
