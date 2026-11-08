"""JSON persistence for search graphs (schema PS §7.3)."""

from __future__ import annotations

import json
import math
from typing import Any

from core.errors import ValidationError
from core.search.models import SearchGraph

GRAPH_FORMAT = "ensi-ai-graph"
GRAPH_VERSION = 1


def _number(value: float) -> float | int:
    """Write integral floats as ints (PS §7.3)."""
    number = float(value)
    return int(number) if number.is_integer() else number


def graph_to_dict(graph: SearchGraph) -> dict[str, Any]:
    """Serialize ``graph`` to the ordered schema of PS §7.3."""
    return {
        "format": GRAPH_FORMAT,
        "version": GRAPH_VERSION,
        "name": graph.name,
        "vertices": list(graph.vertices),
        "edges": [
            {
                "from": edge.source,
                "to": edge.target,
                "cost": _number(edge.cost),
            }
            for edge in graph.edges
        ],
        "heuristics": {
            name: _number(value)
            for name, value in graph.heuristics.items()
        },
        "start": graph.start,
        "goal": graph.goal,
        "positions": {
            name: [_number(x), _number(y)]
            for name, (x, y) in graph.positions.items()
        },
    }


def graph_to_json(graph: SearchGraph) -> str:
    """Return indented JSON with raw non-ASCII characters."""
    return json.dumps(
        graph_to_dict(graph), ensure_ascii=False, indent=2
    )


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def graph_from_dict(data: object) -> SearchGraph:
    """Build a fresh validated graph, aggregating every problem."""
    if not isinstance(data, dict):
        raise ValidationError("Le document JSON doit être un objet.")

    messages: list[str] = []
    if data.get("format") != GRAPH_FORMAT:
        messages.append(f"Format invalide : « {GRAPH_FORMAT} » attendu.")

    version = data.get("version")
    if isinstance(version, bool) or not isinstance(version, int):
        messages.append(f"Version invalide : {GRAPH_VERSION} attendu.")
    elif version != GRAPH_VERSION:
        messages.append(f"Version invalide : {GRAPH_VERSION} attendu.")

    name = data.get("name")
    if not isinstance(name, str):
        messages.append("Le nom du graphe doit être une chaîne de caractères.")
        name = "Graphe sans titre"

    graph = SearchGraph(name=name)

    vertices = data.get("vertices")
    if not isinstance(vertices, list):
        messages.append("La clé « vertices » doit être une liste.")
    else:
        for index, vertex in enumerate(vertices, start=1):
            if not isinstance(vertex, str):
                messages.append(
                    f"Le sommet n°{index} doit être une chaîne de caractères."
                )
                continue
            try:
                graph.add_vertex(vertex)
            except ValidationError as exc:
                messages.extend(exc.messages)

    edges = data.get("edges")
    if not isinstance(edges, list):
        messages.append("La clé « edges » doit être une liste.")
    else:
        for index, raw in enumerate(edges, start=1):
            if not isinstance(raw, dict):
                messages.append(
                    f"L'arête n°{index} doit être un objet JSON."
                )
                continue
            source = raw.get("from")
            target = raw.get("to")
            cost = raw.get("cost")
            valid = True
            if not isinstance(source, str):
                messages.append(
                    f"Arête n°{index} : la clé « from » doit être une chaîne."
                )
                valid = False
            if not isinstance(target, str):
                messages.append(
                    f"Arête n°{index} : la clé « to » doit être une chaîne."
                )
                valid = False
            if not _is_number(cost):
                messages.append(
                    f"Arête n°{index} : la clé « cost » doit être un nombre."
                )
                valid = False
            if not valid:
                continue
            try:
                graph.add_edge(source, target, float(cost))
            except ValidationError as exc:
                messages.extend(exc.messages)

    heuristics = data.get("heuristics", {})
    if not isinstance(heuristics, dict):
        messages.append("La clé « heuristics » doit être un objet.")
    else:
        for vertex, value in heuristics.items():
            if not isinstance(vertex, str) or vertex not in graph.vertices:
                messages.append(
                    f"Heuristique pour un sommet inconnu : « {vertex} »."
                )
                continue
            if not _is_number(value):
                messages.append(
                    f"Heuristique invalide pour « {vertex} » : "
                    "un nombre est attendu."
                )
                continue
            try:
                graph.set_heuristic(vertex, float(value))
            except ValidationError as exc:
                messages.extend(exc.messages)

    for key in ("start", "goal"):
        value = data.get(key)
        if value is None:
            continue
        if not isinstance(value, str):
            messages.append(
                f"La clé « {key} » doit être une chaîne ou null."
            )
            continue
        if value not in graph.vertices:
            messages.append(
                f"Le sommet de {'départ' if key == 'start' else 'but'} "
                f"« {value} » n'existe pas."
            )
            continue
        if key == "start":
            graph.start = value
        else:
            graph.goal = value

    positions = data.get("positions", {})
    if not isinstance(positions, dict):
        messages.append("La clé « positions » doit être un objet.")
    else:
        for vertex, value in positions.items():
            if vertex not in graph.vertices:
                continue
            if (
                not isinstance(value, (list, tuple))
                or len(value) != 2
                or not all(_is_number(item) for item in value)
            ):
                messages.append(
                    f"Position invalide pour « {vertex} » : "
                    "deux nombres sont attendus."
                )
                continue
            x, y = float(value[0]), float(value[1])
            if not (math.isfinite(x) and math.isfinite(y)):
                messages.append(
                    f"Position invalide pour « {vertex} » : "
                    "les nombres doivent être finis."
                )
                continue
            graph.positions[vertex] = (x, y)

    if messages:
        raise ValidationError(messages)
    return graph


def graph_from_json(text: str) -> SearchGraph:
    """Parse JSON text and validate it as a search graph."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Fichier JSON invalide : {exc.msg}.") from exc
    return graph_from_dict(data)
