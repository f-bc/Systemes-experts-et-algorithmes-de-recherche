"""Search data models and graph mutators."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Literal, Optional

from core.errors import ValidationError
from core.text import normalize

INF = math.inf


@dataclass(frozen=True)
class Edge:
    """Directed weighted edge; cost is a finite float >= 0."""

    source: str
    target: str
    cost: float


def _validate_cost(cost: float) -> float:
    if isinstance(cost, bool) or not isinstance(cost, (int, float)):
        raise ValidationError("Le coût d'une arête doit être un nombre.")
    value = float(cost)
    if not math.isfinite(value):
        raise ValidationError("Le coût d'une arête doit être fini.")
    if value < 0:
        raise ValidationError("Le coût d'une arête doit être positif ou nul.")
    return value


@dataclass
class SearchGraph:
    """Directed weighted graph; insertion order defines successor order."""

    name: str = "Graphe sans titre"
    vertices: list[str] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    heuristics: dict[str, float] = field(default_factory=dict)
    start: Optional[str] = None
    goal: Optional[str] = None
    positions: dict[str, tuple[float, float]] = field(default_factory=dict)

    def add_vertex(self, name: str) -> str:
        """Normalize, validate and append a vertex; return its stored name."""
        if not isinstance(name, str):
            raise ValidationError("Le nom d'un sommet doit être une chaîne.")
        value = normalize(name)
        if not value:
            raise ValidationError("Le nom d'un sommet ne peut pas être vide.")
        if len(value) > 20:
            raise ValidationError(
                "Le nom d'un sommet ne doit pas dépasser 20 caractères."
            )
        if value in self.vertices:
            raise ValidationError(f"Le sommet « {value} » existe déjà.")
        self.vertices.append(value)
        return value

    def remove_vertex(self, name: str) -> None:
        """Remove a vertex and everything attached to it."""
        if name not in self.vertices:
            raise ValidationError(f"Sommet inconnu : « {name} ».")
        self.vertices.remove(name)
        self.edges = [
            edge
            for edge in self.edges
            if edge.source != name and edge.target != name
        ]
        self.heuristics.pop(name, None)
        self.positions.pop(name, None)
        if self.start == name:
            self.start = None
        if self.goal == name:
            self.goal = None

    def add_edge(self, source: str, target: str, cost: float) -> Edge:
        """Append a validated edge; no self loop, no duplicate pair."""
        for endpoint in (source, target):
            if endpoint not in self.vertices:
                raise ValidationError(f"Sommet inconnu : « {endpoint} ».")
        if source == target:
            raise ValidationError("Une arête ne peut pas boucler sur son sommet.")
        if any(
            edge.source == source and edge.target == target for edge in self.edges
        ):
            raise ValidationError(
                f"L'arête {source} → {target} existe déjà."
            )
        edge = Edge(source, target, _validate_cost(cost))
        self.edges.append(edge)
        return edge

    def update_edge_cost(self, source: str, target: str, cost: float) -> Edge:
        """Replace the cost of an existing edge, keeping its position."""
        index = self._edge_index(source, target)
        old = self.edges[index]
        edge = Edge(old.source, old.target, _validate_cost(cost))
        self.edges[index] = edge
        return edge

    def remove_edge(self, source: str, target: str) -> None:
        """Remove an existing edge."""
        index = self._edge_index(source, target)
        del self.edges[index]

    def set_heuristic(self, name: str, value: float) -> float:
        """Store a finite non-negative heuristic value."""
        if name not in self.vertices:
            raise ValidationError(f"Sommet inconnu : « {name} ».")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValidationError("L'heuristique doit être un nombre.")
        number = float(value)
        if not math.isfinite(number):
            raise ValidationError("L'heuristique doit être finie.")
        if number < 0:
            raise ValidationError("L'heuristique doit être positive ou nulle.")
        self.heuristics[name] = number
        return number

    def clear_heuristic(self, name: str) -> None:
        """Remove the heuristic of an existing vertex (no-op if absent)."""
        if name not in self.vertices:
            raise ValidationError(f"Sommet inconnu : « {name} ».")
        self.heuristics.pop(name, None)

    def set_start(self, name: Optional[str]) -> None:
        """Set the start vertex (must exist) or clear it."""
        if name is not None and name not in self.vertices:
            raise ValidationError(f"Sommet de départ inconnu : « {name} ».")
        self.start = name

    def set_goal(self, name: Optional[str]) -> None:
        """Set the goal vertex (must exist) or clear it."""
        if name is not None and name not in self.vertices:
            raise ValidationError(f"Sommet de but inconnu : « {name} ».")
        self.goal = name

    def successors(self, name: str) -> list[tuple[str, float]]:
        """Return (target, cost) in edge insertion order (D8)."""
        if name not in self.vertices:
            raise ValidationError(f"Sommet inconnu : « {name} ».")
        return [
            (edge.target, edge.cost)
            for edge in self.edges
            if edge.source == name
        ]

    def copy(self) -> "SearchGraph":
        """Return a deep copy (edges and positions are immutable values)."""
        return SearchGraph(
            name=self.name,
            vertices=list(self.vertices),
            edges=list(self.edges),
            heuristics=dict(self.heuristics),
            start=self.start,
            goal=self.goal,
            positions=dict(self.positions),
        )

    def validate(self, for_informed: bool = False):
        """Delegate to ``graph.validate_graph`` (lazy import)."""
        from core.search.graph import validate_graph

        return validate_graph(self, for_informed)

    def signature(self) -> str:
        """Stable hash of the graph content, positions excluded."""
        from core.search.graph import graph_signature

        return graph_signature(self)

    def _edge_index(self, source: str, target: str) -> int:
        for index, edge in enumerate(self.edges):
            if edge.source == source and edge.target == target:
                return index
        raise ValidationError(f"Arête inconnue : {source} → {target}.")


@dataclass(frozen=True)
class SearchParams:
    """User parameters of the search algorithms."""

    depth_limit: int = 3
    max_depth: Optional[int] = None
    memory_limit: int = 3
    f_limit: float = INF
    dls_visited_mode: Literal["course", "path"] = "course"
    greedy_use_visited: bool = True
    max_iterations: int = 10_000


@dataclass(frozen=True)
class FrontierEntry:
    """One displayed frontier/stack entry."""

    state: str
    g: Optional[float] = None
    h: Optional[float] = None
    f: Optional[float] = None
    parent: Optional[str] = None
    depth: Optional[int] = None


GenStatus = Literal[
    "added",
    "skipped_visited",
    "skipped_closed",
    "improved",
    "not_improved",
    "pruned",
    "cutoff",
]


@dataclass(frozen=True)
class GeneratedEntry:
    """One successor generated during expansion."""

    state: str
    parent: str
    g: Optional[float]
    h: Optional[float]
    f: Optional[float]
    status: GenStatus
    note: str = ""


StepKind = Literal[
    "init",
    "select",
    "goal_found",
    "fail",
    "cap",
    "call",
    "cutoff",
    "backtrack",
    "iteration_start",
]


@dataclass(frozen=True)
class TraceStep:
    """One recorded event of a search run."""

    index: int
    kind: StepKind
    current: Optional[str]
    message: str
    frontier_before: tuple[FrontierEntry, ...] = ()
    frontier_after: tuple[FrontierEntry, ...] = ()
    visited: tuple[str, ...] = ()
    generated: tuple[GeneratedEntry, ...] = ()
    parents: dict[str, Optional[str]] = field(default_factory=dict)
    path_to_current: tuple[str, ...] = ()
    g: Optional[float] = None
    h: Optional[float] = None
    f: Optional[float] = None
    extra: dict = field(default_factory=dict)


@dataclass(frozen=True)
class SearchStats:
    """Statistics of a search run."""

    iterations: int = 0
    nodes_expanded: int = 0
    nodes_generated: int = 0
    max_frontier_size: int = 0
    max_depth_reached: int = 0
    solution_length: Optional[int] = None
    runtime_ms: float = 0.0


Status = Literal["found", "not_found", "aborted_iteration_cap"]


@dataclass(frozen=True)
class SearchResult:
    """Complete result of a search run."""

    algorithm_key: str
    algorithm_label: str
    category: Literal["uninformed", "informed"]
    start: str
    goal: str
    status: Status
    found: bool
    path: tuple[str, ...]
    cost: Optional[float]
    steps: tuple[TraceStep, ...]
    stats: SearchStats
    params: SearchParams
    message: str
