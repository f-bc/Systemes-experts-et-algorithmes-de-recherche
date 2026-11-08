"""Algorithm registry and single search entry point (PS §7.2, IP §P9)."""

from __future__ import annotations

from dataclasses import dataclass, replace
from time import perf_counter
from typing import Callable, Literal, Optional

from core.errors import ValidationError
from core.search.graph import PARAMS_BY_ALGO, validate_params
from core.search.informed import astar, greedy, rbfs, sba_star
from core.search.models import SearchGraph, SearchParams, SearchResult
from core.search.trace import ALGO_META
from core.search.uninformed import (
    bfs,
    dls,
    dfs,
    dfs_recursive,
    ids,
    ucs,
)

Category = Literal["uninformed", "informed"]
Runner = Callable[[SearchGraph, SearchParams], SearchResult]


@dataclass(frozen=True)
class AlgorithmInfo:
    """Static description of one search algorithm."""

    key: str
    label: str
    category: Category
    runner: Runner
    needs_heuristic: bool
    params_used: tuple[str, ...]
    slide_ref: str
    properties: dict[str, str]
    notes: tuple[str, ...]


_GRID_FILTER = "Filtre des visités à la génération, test du but au retrait (D9)."
_DLS_NOTES = (
    "Liste globale des visités, mode « chemin » disponible (D10, Q1).",
)
_IDS_NOTES = (
    "Liste des visités réinitialisée à chaque itération (D11).",
)
_GREEDY_NOTES = ("Liste des visités ajoutée par défaut (D12).",)
_ASTAR_NOTES = ("Fermés jamais rouverts, parent mis à jour (D13).",)
_SBA_NOTES = (
    "Trois corrections de la diapositive, pas de remontée de f (D14).",
)
_RBFS_NOTES = (
    "Mise à jour de f du meilleur après l'appel récursif, "
    "échec avec f = ∞ pour les impasses (D15).",
)


ALGORITHMS: dict[str, AlgorithmInfo] = {
    "bfs": AlgorithmInfo(
        key="bfs",
        label="Largeur d'abord (BFS)",
        category="uninformed",
        runner=bfs,
        needs_heuristic=False,
        params_used=PARAMS_BY_ALGO["bfs"],
        slide_ref="Ch3 p.32",
        properties={
            "temps": "O(b^d)",
            "espace": "O(b^d)",
            "complétude": "Oui",
            "optimalité": "Oui",
        },
        notes=(_GRID_FILTER,),
    ),
    "ucs": AlgorithmInfo(
        key="ucs",
        label="Coût uniforme (UCS)",
        category="uninformed",
        runner=ucs,
        needs_heuristic=False,
        params_used=PARAMS_BY_ALGO["ucs"],
        slide_ref="Ch3 p.35",
        properties={
            "temps": "O(b^(C*/ε))",
            "espace": "O(b^(C*/ε))",
            "complétude": "Oui (si coût ≥ ε)",
            "optimalité": "Oui",
        },
        notes=(_GRID_FILTER,),
    ),
    "dfs": AlgorithmInfo(
        key="dfs",
        label="Profondeur d'abord (DFS, itératif)",
        category="uninformed",
        runner=dfs,
        needs_heuristic=False,
        params_used=PARAMS_BY_ALGO["dfs"],
        slide_ref="Ch3 p.40",
        properties={
            "temps": "O(b^m)",
            "espace": "O(b×m)",
            "complétude": "Oui",
            "optimalité": "Non",
        },
        notes=(_GRID_FILTER,),
    ),
    "dfs_recursive": AlgorithmInfo(
        key="dfs_recursive",
        label="Profondeur d'abord (DFS, récursif)",
        category="uninformed",
        runner=dfs_recursive,
        needs_heuristic=False,
        params_used=PARAMS_BY_ALGO["dfs_recursive"],
        slide_ref="Ch3 p.42",
        properties={
            "temps": "O(b^m)",
            "espace": "O(b×m)",
            "complétude": "Oui",
            "optimalité": "Non",
        },
        notes=(_GRID_FILTER,),
    ),
    "dls": AlgorithmInfo(
        key="dls",
        label="Profondeur limitée (DLS)",
        category="uninformed",
        runner=dls,
        needs_heuristic=False,
        params_used=PARAMS_BY_ALGO["dls"],
        slide_ref="Ch3 p.45",
        properties={
            "temps": "O(b^l)",
            "espace": "O(b×l)",
            "complétude": "si l ≥ d",
            "optimalité": "Non",
        },
        notes=_DLS_NOTES,
    ),
    "ids": AlgorithmInfo(
        key="ids",
        label="Approfondissement itératif (IDS)",
        category="uninformed",
        runner=ids,
        needs_heuristic=False,
        params_used=PARAMS_BY_ALGO["ids"],
        slide_ref="Ch3 p.48",
        properties={
            "temps": "O(b^d)",
            "espace": "O(b×d)",
            "complétude": "Oui",
            "optimalité": "Oui",
        },
        notes=_IDS_NOTES,
    ),
    "greedy": AlgorithmInfo(
        key="greedy",
        label="Meilleur d'abord / Gloutonne (Greedy)",
        category="informed",
        runner=greedy,
        needs_heuristic=True,
        params_used=PARAMS_BY_ALGO["greedy"],
        slide_ref="Ch3 p.55",
        properties={
            "temps": "O(b^m)",
            "espace": "O(b^m)",
            "complétude": "Oui",
            "optimalité": "Non",
        },
        notes=_GREEDY_NOTES,
    ),
    "astar": AlgorithmInfo(
        key="astar",
        label="A*",
        category="informed",
        runner=astar,
        needs_heuristic=True,
        params_used=PARAMS_BY_ALGO["astar"],
        slide_ref="Ch3 p.61",
        properties={
            "temps": "O(b^d)",
            "espace": "O(b^d)",
            "complétude": "Oui",
            "optimalité": "Oui*",
        },
        notes=_ASTAR_NOTES,
    ),
    "sba_star": AlgorithmInfo(
        key="sba_star",
        label="SBA*",
        category="informed",
        runner=sba_star,
        needs_heuristic=True,
        params_used=PARAMS_BY_ALGO["sba_star"],
        slide_ref="Ch3 p.64",
        properties={
            "temps": "O(b^l)",
            "espace": "O(b^l)",
            "complétude": "Non",
            "optimalité": "Non",
        },
        notes=_SBA_NOTES,
    ),
    "rbfs": AlgorithmInfo(
        key="rbfs",
        label="RBFS (Recursive Best-First Search)",
        category="informed",
        runner=rbfs,
        needs_heuristic=True,
        params_used=PARAMS_BY_ALGO["rbfs"],
        slide_ref="Ch3 p.66",
        properties={
            "temps": "O(b^m)",
            "espace": "O(b^m)",
            "complétude": "Non",
            "optimalité": "Non",
        },
        notes=_RBFS_NOTES,
    ),
}

for _key, _info in ALGORITHMS.items():
    assert (_info.label, _info.category) == ALGO_META[_key]


def algorithms_by_category(category: Category) -> list[AlgorithmInfo]:
    """Return the algorithms of ``category`` in registry order."""
    return [
        info for info in ALGORITHMS.values() if info.category == category
    ]


def run_algorithm(
    key: str, graph: SearchGraph, params: SearchParams
) -> SearchResult:
    """Validate the input, run one algorithm and stamp its runtime."""
    info = ALGORITHMS[key]
    report = graph.validate(for_informed=info.needs_heuristic)
    if report.errors:
        raise ValidationError(report.errors)
    params_report = validate_params(params, graph, key)
    if params_report.errors:
        raise ValidationError(params_report.errors)
    start = perf_counter()
    result = info.runner(graph, params)
    elapsed_ms = (perf_counter() - start) * 1000.0
    return replace(
        result, stats=replace(result.stats, runtime_ms=elapsed_ms)
    )


def compare_algorithms(
    graph: SearchGraph,
    params: SearchParams,
    keys: Optional[list[str]] = None,
) -> list[SearchResult]:
    """Run several algorithms in registry order, skipping invalid informed ones."""
    selected = set(keys) if keys is not None else None
    informed_ok = graph.validate(for_informed=True).ok
    results: list[SearchResult] = []
    for key, info in ALGORITHMS.items():
        if selected is not None and key not in selected:
            continue
        if info.needs_heuristic and not informed_ok:
            continue
        results.append(run_algorithm(key, graph, params))
    return results
