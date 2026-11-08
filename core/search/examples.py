"""l'application charge les graphes d'exemple depuis ce fichier."""
from __future__ import annotations

from dataclasses import dataclass

from core.search.models import SearchGraph, SearchParams


@dataclass(frozen=True)
class ExampleGraph:
    """One example with its display label, source and expected behaviour."""

    label: str
    source: str
    graph: SearchGraph
    suggested_params: SearchParams
    expectation: str


def _build(
    name: str,
    edges: list[tuple[str, str, float]],
    heuristics: dict[str, float],
    start: str,
    goal: str,
    positions: dict[str, tuple[float, float]],
) -> SearchGraph:
    graph = SearchGraph(name=name)
    for source, target, _cost in edges:
        for vertex in (source, target):
            if vertex not in graph.vertices:
                graph.add_vertex(vertex)
    for source, target, cost in edges:
        graph.add_edge(source, target, cost)
    for vertex, value in heuristics.items():
        graph.set_heuristic(vertex, value)
    graph.set_start(start)
    graph.set_goal(goal)
    for vertex, point in positions.items():
        graph.positions[vertex] = point
    return graph


_SPECS = [
    (
        "g1",
        "Graphe du cours (Ch3 p.62) — reconstruit",
        "Ch3 p.62, Q4",
        [
            ("G", "A", 10),
            ("G", "C", 5),
            ("A", "B", 5),
            ("A", "H", 10),
            ("B", "F", 5),
            ("C", "D", 5),
            ("D", "E", 5),
            ("D", "G", 10),
            ("E", "A", 5),
            ("E", "C", 10),
            ("E", "K", 10),
            ("F", "G", 10),
            ("H", "B", 5),
            ("H", "K", 20),
            ("K", "B", 10),
        ],
        {
            "G": 10,
            "A": 10,
            "B": 20,
            "C": 10,
            "D": 5,
            "E": 10,
            "F": 10,
            "H": 20,
            "K": 0,
        },
        "G",
        "K",
        {
            "G": (0, 1),
            "A": (2, 1),
            "B": (4, 1),
            "F": (1.5, 2),
            "H": (3, 0.4),
            "D": (1, 0.3),
            "C": (0, -0.5),
            "E": (2, -0.5),
            "K": (4, -0.5),
        },
        SearchParams(depth_limit=3, max_depth=6, memory_limit=2),
        "BFS/DFS/DLS/IDS donnent G→A→H→K (40) ; "
        "UCS/Greedy/A*/SBA*/RBFS donnent G→C→D→E→K (25).",
    ),
    (
        "g2",
        "Piège pour la gloutonne",
        "Ch3 p.55",
        [
            ("S", "A", 10),
            ("S", "B", 2),
            ("S", "C", 3),
            ("A", "T", 10),
            ("B", "T", 3),
        ],
        {"S": 6, "A": 1, "B": 5, "C": 4, "T": 0},
        "S",
        "T",
        {
            "S": (0, 1),
            "A": (2, 2),
            "B": (2, 1),
            "C": (2, 0),
            "T": (4, 1),
        },
        SearchParams(),
        "Greedy et BFS donnent S→A→T (20) ; "
        "A* et UCS trouvent S→B→T (5).",
    ),
    (
        "g3",
        "Cycle avec h trompeuse",
        "Ch3 p.55",
        [
            ("S", "A", 1),
            ("A", "S", 1),
            ("S", "B", 5),
            ("B", "T", 1),
        ],
        {"S": 1, "A": 1, "B": 4, "T": 0},
        "S",
        "T",
        {
            "S": (0, 1),
            "A": (2, 2),
            "B": (2, 0),
            "T": (4, 0),
        },
        SearchParams(),
        "Greedy par défaut trouve S→B→T (6) ; "
        "sans liste des visités, il boucle jusqu'à la limite d'itérations.",
    ),
    (
        "g4",
        "Mémoire limitée SBA*",
        "Ch3 p.64",
        [
            ("S", "B", 2),
            ("S", "C", 3),
            ("C", "T", 3),
        ],
        {"S": 6, "B": 1, "C": 4, "T": 0},
        "S",
        "T",
        {
            "S": (0, 1),
            "B": (2, 2),
            "C": (2, 0),
            "T": (4, 0),
        },
        SearchParams(memory_limit=2),
        "SBA* avec Lim=1 échoue (C élagué), Lim=2 trouve S→C→T (6) ; "
        "A* trouve S→C→T.",
    ),
    (
        "g5",
        "DLS et liste des visités",
        "Ch3 p.45–46",
        [
            ("S", "A", 1),
            ("S", "B", 1),
            ("A", "D", 1),
            ("D", "C", 1),
            ("B", "C", 1),
            ("C", "T", 1),
        ],
        {"S": 3, "A": 3, "B": 2, "C": 1, "D": 2, "T": 0},
        "S",
        "T",
        {
            "S": (0, 1),
            "A": (1, 2),
            "D": (2, 2),
            "B": (1, 0),
            "C": (3, 1),
            "T": (4, 1),
        },
        SearchParams(depth_limit=3),
        "DLS mode course échoue avec depth_limit=3 ; "
        "mode chemin trouve S→B→C→T ; IDS trouve S→A→D→C→T (4).",
    ),
    (
        "t1",
        "Arbre RBFS (Ch3 p.67)",
        "Ch3 p.66–67",
        [
            ("A", "B", 5),
            ("A", "C", 10),
            ("B", "D", 5),
            ("B", "E", 10),
            ("C", "G", 20),
            ("E", "F", 45),
        ],
        {
            "A": 30,
            "B": 20,
            "C": 25,
            "D": 40,
            "E": 30,
            "F": 45,
            "G": 0,
        },
        "A",
        "G",
        {
            "A": (2, 2),
            "B": (1, 1),
            "C": (3, 1),
            "D": (0.3, 0),
            "E": (1.7, 0),
            "G": (3, 0),
            "F": (1.7, -1),
        },
        SearchParams(f_limit=40),
        "RBFS avec f_limit=40 visite A B C G ; "
        "A→C→G a un coût 30 et une valeur f de 35.",
    ),
    (
        "gn",
        "Aucun chemin",
        "Ch3 p.32",
        [
            ("S", "A", 1),
            ("A", "B", 1),
            ("C", "T", 1),
        ],
        {"S": 1, "A": 1, "B": 1, "C": 1, "T": 0},
        "S",
        "T",
        {
            "S": (0, 1),
            "A": (1.5, 1),
            "B": (3, 1),
            "C": (0, 0),
            "T": (1.5, 0),
        },
        SearchParams(),
        "Tous les algorithmes signalent l'absence de chemin.",
    ),
]

EXAMPLE_GRAPHS: dict[str, ExampleGraph] = {
    key: ExampleGraph(
        label=label,
        source=source,
        graph=_build(label, edges, heuristics, start, goal, positions),
        suggested_params=suggested_params,
        expectation=expectation,
    )
    for key, label, source, edges, heuristics, start, goal, positions, (
        suggested_params
    ), expectation in _SPECS
}
