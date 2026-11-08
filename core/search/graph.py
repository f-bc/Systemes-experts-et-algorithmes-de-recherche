"""Graph validation, signatures and parameter validation (PS §7.2)."""

from __future__ import annotations

import hashlib
import json
import math

from core.errors import ValidationReport
from core.search.models import SearchGraph, SearchParams
from core.text import normalize

PARAMS_BY_ALGO: dict[str, tuple[str, ...]] = {
    "bfs": ("max_iterations",),
    "ucs": ("max_iterations",),
    "dfs": ("max_iterations",),
    "dfs_recursive": ("max_iterations",),
    "dls": ("depth_limit", "dls_visited_mode", "max_iterations"),
    "ids": ("max_depth", "dls_visited_mode", "max_iterations"),
    "greedy": ("greedy_use_visited", "max_iterations"),
    "astar": ("max_iterations",),
    "sba_star": ("memory_limit", "max_iterations"),
    "rbfs": ("f_limit", "max_iterations"),
}


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def validate_graph(
    graph: SearchGraph, for_informed: bool = False
) -> ValidationReport:
    """Apply the validation table of PS §7.2."""
    report = ValidationReport()
    vertices = list(graph.vertices)
    known: set[str] = set()

    for name in vertices:
        if not isinstance(name, str) or not name:
            report.errors.append("Le nom d'un sommet ne peut pas être vide.")
            continue
        if normalize(name) != name:
            report.errors.append(
                f"Le nom du sommet « {name} » contient des espaces superflus."
            )
        if len(name) > 20:
            report.errors.append(
                f"Le nom du sommet « {name} » dépasse 20 caractères."
            )
        if name in known:
            report.errors.append(f"Le nom du sommet « {name} » est en double.")
        known.add(name)

    pairs: set[tuple[str, str]] = set()
    incident: set[str] = set()
    for edge in graph.edges:
        if edge.source not in known:
            report.errors.append(
                f"Le sommet source « {edge.source} » n'existe pas."
            )
        if edge.target not in known:
            report.errors.append(
                f"Le sommet cible « {edge.target} » n'existe pas."
            )
        if edge.source == edge.target:
            report.errors.append(
                f"Une boucle est interdite sur le sommet « {edge.source} »."
            )
        pair = (edge.source, edge.target)
        if pair in pairs:
            report.errors.append(
                f"L'arête {edge.source} → {edge.target} est en double."
            )
        pairs.add(pair)
        incident.add(edge.source)
        incident.add(edge.target)

        if isinstance(edge.cost, bool) or not isinstance(
            edge.cost, (int, float)
        ):
            report.errors.append(
                f"Le coût de l'arête {edge.source} → {edge.target} "
                "n'est pas un nombre."
            )
            continue
        cost = float(edge.cost)
        if not math.isfinite(cost):
            report.errors.append(
                f"Le coût de l'arête {edge.source} → {edge.target} "
                "doit être fini."
            )
        elif cost < 0:
            report.errors.append(
                f"Le coût de l'arête {edge.source} → {edge.target} "
                "doit être positif ou nul."
            )
        elif cost == 0:
            report.warnings.append(
                f"Le coût de l'arête {edge.source} → {edge.target} est nul."
            )

    if graph.start is None:
        report.errors.append("Le sommet de départ n'est pas défini.")
    elif graph.start not in known:
        report.errors.append(
            f"Le sommet de départ « {graph.start} » n'existe pas."
        )
    if graph.goal is None:
        report.errors.append("Le sommet de but n'est pas défini.")
    elif graph.goal not in known:
        report.errors.append(f"Le sommet de but « {graph.goal} » n'existe pas.")

    for name in vertices:
        if isinstance(name, str) and name not in incident:
            report.warnings.append(
                f"Le sommet « {name} » n'a aucune arête."
            )

    if for_informed:
        for name in vertices:
            if not isinstance(name, str):
                continue
            if name not in graph.heuristics:
                report.errors.append(
                    f"Heuristique manquante pour le sommet « {name} »."
                )
                continue
            value = graph.heuristics[name]
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                report.errors.append(
                    f"Heuristique invalide pour « {name} » : "
                    "un nombre est attendu."
                )
                continue
            number = float(value)
            if not math.isfinite(number):
                report.errors.append(
                    f"Heuristique invalide pour « {name} » : "
                    "la valeur doit être finie."
                )
            elif number < 0:
                report.errors.append(
                    f"Heuristique invalide pour « {name} » : "
                    "la valeur doit être positive ou nulle."
                )

        if graph.goal is not None and graph.goal in graph.heuristics:
            value = graph.heuristics[graph.goal]
            if (
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and math.isfinite(float(value))
                and float(value) != 0
            ):
                report.warnings.append(
                    f"L'heuristique du but « {graph.goal} » "
                    "devrait être nulle."
                )

    return report


def graph_signature(graph: SearchGraph) -> str:
    """SHA-256 of the canonical content; positions are excluded."""
    payload = {
        "name": graph.name,
        "vertices": list(graph.vertices),
        "edges": [
            [edge.source, edge.target, float(edge.cost)] for edge in graph.edges
        ],
        "heuristics": {
            name: float(value) for name, value in graph.heuristics.items()
        },
        "start": graph.start,
        "goal": graph.goal,
    }
    text = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def validate_params(
    params: SearchParams, graph: SearchGraph, key: str
) -> ValidationReport:
    """Check ``max_iterations`` and only the fields used by ``key``."""
    report = ValidationReport()
    used = PARAMS_BY_ALGO[key]

    if not _is_int(params.max_iterations) or params.max_iterations < 1:
        report.errors.append(
            "Le nombre maximal d'itérations doit être un entier ≥ 1."
        )

    if "depth_limit" in used:
        if not _is_int(params.depth_limit) or params.depth_limit < 0:
            report.errors.append(
                "La limite de profondeur doit être un entier ≥ 0."
            )

    if "max_depth" in used:
        if params.max_depth is not None and (
            not _is_int(params.max_depth) or params.max_depth < 1
        ):
            report.errors.append(
                "La profondeur maximale doit être un entier ≥ 1 "
                "ou rester indéfinie."
            )

    if "memory_limit" in used:
        if not _is_int(params.memory_limit) or params.memory_limit < 1:
            report.errors.append(
                "La limite mémoire doit être un entier ≥ 1."
            )

    if "f_limit" in used:
        if isinstance(params.f_limit, bool) or not isinstance(
            params.f_limit, (int, float)
        ):
            report.errors.append("La limite f doit être un nombre.")
        else:
            value = float(params.f_limit)
            if math.isnan(value) or value < 0:
                report.errors.append(
                    "La limite f doit être positive ou infinie "
                    "(NaN et −∞ sont interdits)."
                )

    if "dls_visited_mode" in used:
        if params.dls_visited_mode not in ("course", "path"):
            report.errors.append(
                "Le mode des visités doit être « course » ou « path »."
            )

    if "greedy_use_visited" in used:
        if not isinstance(params.greedy_use_visited, bool):
            report.errors.append(
                "L'option « liste des visités » doit être un booléen."
            )

    return report
