"""l'application charge les bases d'exemple depuis ce fichier."""
from __future__ import annotations

from dataclasses import dataclass

from core.expert.models import KnowledgeBase

DIAGNOSTIC_KEY = "diagnostic"


@dataclass(frozen=True)
class ExampleKB:
    """One example with its display label, source and suggested goals."""

    label: str
    source: str
    kb: KnowledgeBase
    suggested_goals: list[tuple[str, str]]


def _build(
    name: str, facts: list[str], rules: list[tuple[list[str], str]]
) -> KnowledgeBase:
    kb = KnowledgeBase(name=name)
    for fact in facts:
        kb.add_fact(fact)
    for premises, conclusion in rules:
        kb.add_rule(list(premises), conclusion)
    return kb


_EXAMPLE_SPECS: list[tuple[str, str, str, list[str], list[tuple[list[str], str]]]] = [
    (
        "tarte",
        "Tarte aux fruits",
        "Ch2 p.19, 30",
        ["pommes", "œufs", "poires", "abricots", "farine", "beurre", "sucre", "sel"],
        [
            (["farine", "beurre", "œufs", "sel"], "pâte"),
            (["pommes", "sucre"], "pommes sucrées"),
            (["pommes sucrées", "pâte"], "tarte aux pommes"),
            (["abricots", "pâte"], "tarte aux abricots"),
            (["poires", "pâte"], "tarte aux poires"),
            (["cerises", "pâte"], "tarte aux cerises"),
        ],
    ),
    (
        "cours_r1_r9",
        "Chaînage avant avec but",
        "Ch2 p.23–24",
        ["B", "C"],
        [
            (["B", "D", "E"], "F"),
            (["B", "G"], "A"),
            (["C", "F"], "A"),
            (["B"], "X"),
            (["D"], "E"),
            (["A", "X"], "H"),
            (["C"], "D"),
            (["X", "C"], "A"),
            (["X", "B"], "D"),
        ],
    ),
    (
        "exo_avant",
        "Exercice chaînage avant",
        "Ch2 p.39",
        ["E", "F"],
        [
            (["A", "B"], "C"),
            (["F", "D"], "A"),
            (["D", "E"], "B"),
            (["B", "D"], "F"),
            (["E", "F"], "D"),
        ],
    ),
    (
        "exo_arriere",
        "Exercice chaînage arrière",
        "Ch2 p.40",
        ["E", "F"],
        [
            (["E", "B"], "C"),
            (["B", "D"], "A"),
            (["J", "H"], "B"),
            (["D", "E"], "B"),
            (["B", "D"], "F"),
            (["E", "F"], "D"),
        ],
    ),
    (
        "triangle",
        "Formes géométriques",
        "Ch2 p.12, 20, 31",
        ["ordre vaut 3", "angle droit", "deux côtés de même taille"],
        [
            (["ordre vaut 3"], "triangle"),
            (["triangle", "angle droit"], "triangle rectangle"),
            (["triangle", "deux côtés de même taille"], "triangle isocèle"),
        ],
    ),
    (
        "autruche",
        "Animaux",
        "Ch2 p.25–26",
        [
            "animal a des plumes",
            "animal a un long cou",
            "animal a de longues pattes",
        ],
        [
            (["animal vole", "animal pond des œufs"], "animal est un oiseau"),
            (["animal a des plumes"], "animal est un oiseau"),
            (
                ["animal est un oiseau", "animal a un long cou", "animal a de longues pattes"],
                "animal est une autruche",
            ),
        ],
    ),
    (
        "diagnostic",
        "Diagnostic",
        "jouet, inspiré de Ch2 p.41",
        ["fièvre", "toux", "fatigue"],
        [
            (["fièvre", "toux"], "syndrome grippal"),
            (["syndrome grippal", "fatigue"], "grippe probable"),
            (["éternuements", "nez qui coule"], "rhume probable"),
            (["grippe probable"], "repos conseillé"),
        ],
    ),
    (
        "cycle",
        "Dépendance circulaire",
        "test",
        [],
        [(["A"], "B"), (["B"], "A")],
    ),
]

_SUGGESTED: dict[str, list[tuple[str, str]]] = {
    "tarte": [
        ("tarte aux abricots", "démontrable"),
        ("tarte aux cerises", "non démontrable"),
        ("sel", "déjà dans la base"),
    ],
    "cours_r1_r9": [("H", "démontrable")],
    "exo_avant": [("C", "démontrable")],
    "exo_arriere": [("C", "démontrable"), ("A", "démontrable")],
    "triangle": [
        ("triangle rectangle", "démontrable"),
        ("triangle isocèle", "démontrable"),
    ],
    "autruche": [("animal est une autruche", "démontrable")],
    "diagnostic": [
        ("repos conseillé", "démontrable"),
        ("rhume probable", "non démontrable"),
    ],
    "cycle": [("A", "non démontrable")],
}

EXAMPLE_KBS: dict[str, ExampleKB] = {
    key: ExampleKB(
        label=label,
        source=source,
        kb=_build(label, facts, rules),
        suggested_goals=list(_SUGGESTED[key]),
    )
    for key, label, source, facts, rules in _EXAMPLE_SPECS
}
