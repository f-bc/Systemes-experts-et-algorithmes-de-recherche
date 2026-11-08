"""Matplotlib rendering of a search graph and one trace step (PS §8.4)."""

from __future__ import annotations

import math
from typing import Optional

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.figure import Figure
from matplotlib.patches import Patch

from core.search.models import SearchGraph, SearchResult, TraceStep
from core.text import fmt_num

ROLE_COLORS: dict[str, str] = {
    "default": "#F4F6F8",
    "current": "#FFB300",
    "explored": "#B0BEC5",
    "frontier": "#81D4FA",
    "final_path": "#CE93D8",
}

RING_COLORS: dict[str, str] = {
    "default": "#90A4AE",
    "initial": "#2E7D32",
    "goal": "#C62828",
    "current": "#E65100",
    "explored": "#546E7A",
    "frontier": "#0277BD",
    "final_path": "#6A1B9A",
}

RING_WIDTHS: dict[str, float] = {
    "default": 1.2,
    "initial": 3.0,
    "goal": 3.0,
    "current": 3.0,
    "explored": 1.5,
    "frontier": 1.5,
    "final_path": 2.5,
}

LEGEND_ITEMS: list[tuple[str, str]] = [
    ("Initial", RING_COLORS["initial"]),
    ("But", RING_COLORS["goal"]),
    ("En cours", ROLE_COLORS["current"]),
    ("Exploré", ROLE_COLORS["explored"]),
    ("Frontière", ROLE_COLORS["frontier"]),
    ("Chemin solution", ROLE_COLORS["final_path"]),
]

MAX_TITLE = 90
PROOF_COLORS: dict[str, str] = {
    "fact": "#C8E6C9",
    "proved": "#BBDEFB",
    "failed": "#FFCDD2",
    "cycle": "#FFE0B2",
    "no_rule": "#FFCDD2",
}


def compute_layout(
    graph: SearchGraph, seed: int = 42
) -> dict[str, tuple[float, float]]:
    """Use stored positions when complete, else a deterministic spring layout."""
    if graph.vertices and all(
        vertex in graph.positions for vertex in graph.vertices
    ):
        return {
            vertex: graph.positions[vertex] for vertex in graph.vertices
        }
    if not graph.vertices:
        return {}
    digraph = nx.DiGraph()
    digraph.add_nodes_from(graph.vertices)
    digraph.add_edges_from(
        (edge.source, edge.target) for edge in graph.edges
    )
    count = len(graph.vertices)
    positions = nx.spring_layout(
        digraph, seed=seed, k=1.2 / math.sqrt(count)
    )
    return {
        vertex: (float(point[0]), float(point[1]))
        for vertex, point in positions.items()
    }


def node_roles(
    graph: SearchGraph,
    step: Optional[TraceStep],
    result: Optional[SearchResult],
    show_final_path: bool,
) -> dict[str, str]:
    """Return the fill role of every vertex by the PS §8.4 precedence."""
    roles = {vertex: "default" for vertex in graph.vertices}
    if step is None:
        return roles
    final_path: set[str] = set()
    if show_final_path and result is not None and result.found:
        final_path = set(result.path)
    explored = set(step.visited)
    frontier = {entry.state for entry in step.frontier_after}
    frontier.update(step.extra.get("stack", ()))
    for vertex in graph.vertices:
        if vertex in final_path:
            roles[vertex] = "final_path"
        elif vertex == step.current:
            roles[vertex] = "current"
        elif vertex in explored:
            roles[vertex] = "explored"
        elif vertex in frontier:
            roles[vertex] = "frontier"
    return roles


def _shorten(message: str) -> str:
    if len(message) <= MAX_TITLE:
        return message
    return message[: MAX_TITLE - 1] + "…"


def draw_search_graph(
    graph: SearchGraph,
    step: Optional[TraceStep] = None,
    result: Optional[SearchResult] = None,
    *,
    show_final_path: bool = False,
    show_heuristics: bool = False,
    positions: Optional[dict[str, tuple[float, float]]] = None,
    figsize: tuple[float, float] = (8.5, 5.5),
) -> Figure:
    """Draw one trace step of ``graph`` and return the matplotlib figure."""
    digraph = nx.DiGraph()
    digraph.add_nodes_from(graph.vertices)
    for edge in graph.edges:
        digraph.add_edge(edge.source, edge.target, cost=edge.cost)
    layout = (
        dict(positions)
        if positions is not None
        else compute_layout(graph)
    )
    roles = node_roles(graph, step, result, show_final_path)

    figure, axes = plt.subplots(figsize=figsize)
    if digraph.number_of_edges():
        nx.draw_networkx_edges(
            digraph,
            layout,
            ax=axes,
            edge_color="#B0BEC5",
            width=1.2,
            arrows=True,
            arrowsize=12,
            connectionstyle="arc3,rad=0.12",
        )
        tree_edges = []
        if step is not None:
            for child, parent in step.parents.items():
                if parent is not None and digraph.has_edge(parent, child):
                    tree_edges.append((parent, child))
        if tree_edges:
            nx.draw_networkx_edges(
                digraph,
                layout,
                edgelist=tree_edges,
                ax=axes,
                edge_color="#546E7A",
                width=2.0,
                arrows=True,
                arrowsize=12,
                connectionstyle="arc3,rad=0.12",
            )
        if show_final_path and result is not None and result.found:
            path_edges = list(zip(result.path, result.path[1:]))
            nx.draw_networkx_edges(
                digraph,
                layout,
                edgelist=path_edges,
                ax=axes,
                edge_color="#6A1B9A",
                width=4.0,
                arrows=True,
                arrowsize=14,
                connectionstyle="arc3,rad=0.12",
            )
        edge_labels = {
            (edge.source, edge.target): fmt_num(edge.cost)
            for edge in graph.edges
        }
        nx.draw_networkx_edge_labels(
            digraph,
            layout,
            edge_labels=edge_labels,
            ax=axes,
            font_size=9,
            connectionstyle="arc3,rad=0.12",
        )

    if graph.vertices:
        node_colors = [ROLE_COLORS[roles[v]] for v in graph.vertices]
        edge_colors = []
        edge_widths = []
        for vertex in graph.vertices:
            if vertex == graph.goal:
                edge_colors.append(RING_COLORS["goal"])
                edge_widths.append(RING_WIDTHS["goal"])
            elif vertex == graph.start:
                edge_colors.append(RING_COLORS["initial"])
                edge_widths.append(RING_WIDTHS["initial"])
            else:
                edge_colors.append(RING_COLORS[roles[vertex]])
                edge_widths.append(RING_WIDTHS[roles[vertex]])
        nx.draw_networkx_nodes(
            digraph,
            layout,
            nodelist=graph.vertices,
            ax=axes,
            node_color=node_colors,
            edgecolors=edge_colors,
            linewidths=edge_widths,
            node_size=900,
        )
        labels = {}
        for vertex in graph.vertices:
            parts = [vertex]
            if vertex == graph.start and vertex == graph.goal:
                parts.append("S/G")
            if show_heuristics and vertex in graph.heuristics:
                parts.append(f"h={fmt_num(graph.heuristics[vertex])}")
            labels[vertex] = "\n".join(parts)
        nx.draw_networkx_labels(
            digraph, layout, labels=labels, ax=axes, font_size=10
        )

    title = graph.name if step is None else step.message or graph.name
    axes.set_title(_shorten(title), fontsize=10)
    axes.axis("off")
    handles = [
        Patch(
            facecolor=color,
            edgecolor="#546E7A",
            linewidth=0.8,
            label=label,
        )
        for label, color in LEGEND_ITEMS
    ]
    axes.legend(
        handles=handles,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.02),
        ncol=4,
        frameon=False,
        fontsize=8,
    )
    figure.tight_layout()
    return figure


def draw_proof_tree(
    nodes: list[tuple[str, str, str, int]],
    edges: list[tuple[str, str]],
    *,
    figsize: tuple[float, float] = (10.0, 5.5),
) -> Figure:
    """Draw a proof tree from ``(id, label, status, depth)`` node records."""
    tree = nx.DiGraph()
    for node_id, label, status, depth in nodes:
        tree.add_node(
            node_id,
            label=label,
            status=status,
            depth=depth,
        )
    tree.add_edges_from(edges)
    figure, axes = plt.subplots(figsize=figsize)
    if tree.number_of_nodes():
        layout = nx.multipartite_layout(
            tree,
            subset_key="depth",
            align="vertical",
            scale=1.0,
        )
        colors = [
            PROOF_COLORS.get(tree.nodes[node]["status"], PROOF_COLORS["failed"])
            for node in tree.nodes
        ]
        nx.draw_networkx_edges(
            tree,
            layout,
            ax=axes,
            edge_color="#78909C",
            arrows=True,
            arrowsize=14,
            connectionstyle="arc3,rad=0.08",
        )
        nx.draw_networkx_nodes(
            tree,
            layout,
            ax=axes,
            node_color=colors,
            edgecolors="#455A64",
            linewidths=1.2,
            node_size=2400,
        )
        nx.draw_networkx_labels(
            tree,
            layout,
            labels={node: tree.nodes[node]["label"] for node in tree.nodes},
            ax=axes,
            font_size=9,
        )
    axes.axis("off")
    figure.tight_layout()
    return figure
