"""Heuristic diagnostics (AS B.11, Ch3 p.70)."""

from __future__ import annotations

import heapq
from dataclasses import dataclass
from typing import Optional

from core.search.models import SearchGraph
from core.text import fmt_num

INF = float("inf")


@dataclass(frozen=True)
class HeuristicDiagnostics:
    """Result of the heuristic sanity checks (PS §6.1)."""

    admissible: Optional[bool]
    consistent: bool
    violations: list[str]


def true_costs_to_goal(graph: SearchGraph) -> dict[str, float]:
    """Exact cost to the goal for every vertex, by reverse Dijkstra."""
    distances = {vertex: INF for vertex in graph.vertices}
    if graph.goal is None:
        return distances
    reverse: dict[str, list[tuple[str, float]]] = {
        vertex: [] for vertex in graph.vertices
    }
    for edge in graph.edges:
        reverse[edge.target].append((edge.source, edge.cost))
    distances[graph.goal] = 0.0
    heap: list[tuple[float, str]] = [(0.0, graph.goal)]
    while heap:
        distance, vertex = heapq.heappop(heap)
        if distance > distances[vertex]:
            continue
        for predecessor, cost in reverse[vertex]:
            candidate = distance + cost
            if candidate < distances[predecessor]:
                distances[predecessor] = candidate
                heapq.heappush(heap, (candidate, predecessor))
    return distances


def check_heuristic(graph: SearchGraph) -> HeuristicDiagnostics:
    """Check admissibility and consistency without running a search."""
    exact = true_costs_to_goal(graph)
    violations: list[str] = []
    admissible: Optional[bool]
    if graph.goal is None:
        admissible = None
    else:
        admissible = True
        for vertex in graph.vertices:
            heuristic = graph.heuristics.get(vertex, 0.0)
            if exact[vertex] == INF:
                continue
            if heuristic > exact[vertex]:
                admissible = False
                violations.append(
                    f"Admissibilité : h({vertex})={fmt_num(heuristic)} "
                    f"> h*({vertex})={fmt_num(exact[vertex])}"
                )
    consistent = True
    for edge in graph.edges:
        source_h = graph.heuristics.get(edge.source, 0.0)
        target_h = graph.heuristics.get(edge.target, 0.0)
        bound = edge.cost + target_h
        if source_h > bound:
            consistent = False
            violations.append(
                f"Consistance : h({edge.source})={fmt_num(source_h)} "
                f"> c({edge.source},{edge.target})+"
                f"h({edge.target})={fmt_num(bound)}"
            )
    return HeuristicDiagnostics(
        admissible=admissible,
        consistent=consistent,
        violations=violations,
    )
