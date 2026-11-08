"""Search nodes, trace recorder and result assembly (AS §0.1, §0.3–0.4)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from core.search.models import (
    FrontierEntry,
    GeneratedEntry,
    SearchGraph,
    SearchParams,
    SearchResult,
    SearchStats,
    StepKind,
    TraceStep,
)

ALGO_META: dict[str, tuple[str, Literal["uninformed", "informed"]]] = {
    "bfs": ("Largeur d'abord (BFS)", "uninformed"),
    "ucs": ("Coût uniforme (UCS)", "uninformed"),
    "dfs": ("Profondeur d'abord (DFS, itératif)", "uninformed"),
    "dfs_recursive": ("Profondeur d'abord (DFS, récursif)", "uninformed"),
    "dls": ("Profondeur limitée (DLS)", "uninformed"),
    "ids": ("Approfondissement itératif (IDS)", "uninformed"),
    "greedy": ("Meilleur d'abord / Gloutonne (Greedy)", "informed"),
    "astar": ("A*", "informed"),
    "sba_star": ("SBA* (SMA* simplifié du cours)", "informed"),
    "rbfs": ("RBFS (Recursive Best-First Search)", "informed"),
}


@dataclass
class SearchNode:
    """Internal search node: a frontier entry is a node, not a state."""

    state: str
    parent: Optional["SearchNode"] = None
    g: float = 0.0
    h: Optional[float] = None
    f: Optional[float] = None
    depth: int = 0


@dataclass
class SearchCounters:
    """Runner-maintained statistics (AS §0.3)."""

    nodes_generated: int = 0
    max_frontier_size: int = 0
    max_depth_reached: int = 0


def path_from_node(node: Optional[SearchNode]) -> list[str]:
    """Reconstruct the path from the root to ``node``."""
    states: list[str] = []
    current = node
    while current is not None:
        states.append(current.state)
        current = current.parent
    states.reverse()
    return states


class TraceRecorder:
    """Owns the trace steps, the visited log and the parent table."""

    def __init__(
        self,
        graph: SearchGraph,
        algo_key: str,
        use: tuple[str, ...] = (),
    ) -> None:
        allowed = {"depth", "g", "h", "f"}
        unknown = set(use) - allowed
        if unknown:
            raise ValueError(f"Unknown frontier fields: {sorted(unknown)}")
        self.graph = graph
        self.algo_key = algo_key
        self.use = tuple(use)
        self._visited: list[str] = []
        self._parents: dict[str, Optional[str]] = {}
        if graph.start is not None:
            self._parents[graph.start] = None
        self._steps: list[TraceStep] = []

    @property
    def visited(self) -> list[str]:
        """Copy of the current visited log (read-only for callers)."""
        return list(self._visited)

    @property
    def steps(self) -> list[TraceStep]:
        """Copy of the recorded steps."""
        return list(self._steps)

    def mark_visited(self, state: str) -> None:
        """Add a state once (ordinary visited/closed list)."""
        if state not in self._visited:
            self._visited.append(state)

    def append_visit(self, state: str) -> None:
        """Append every entry, repeats included (RBFS only)."""
        self._visited.append(state)

    def reset_visited(self) -> None:
        """Empty the visited log (IDS starts a fresh iteration)."""
        self._visited.clear()

    def set_parent(self, state: str, parent_state: Optional[str]) -> None:
        """Record the newest parent of ``state``."""
        self._parents[state] = parent_state

    def snapshot(
        self, nodes: list[SearchNode] | tuple[SearchNode, ...]
    ) -> tuple[FrontierEntry, ...]:
        """Build frontier entries, filling only the fields in ``use``."""
        entries: list[FrontierEntry] = []
        for node in nodes:
            entries.append(
                FrontierEntry(
                    state=node.state,
                    g=node.g if "g" in self.use else None,
                    h=node.h if "h" in self.use else None,
                    f=node.f if "f" in self.use else None,
                    parent=node.parent.state if node.parent is not None else None,
                    depth=node.depth if "depth" in self.use else None,
                )
            )
        return tuple(entries)

    def step(
        self,
        kind: StepKind,
        current: Optional[SearchNode],
        message: str,
        *,
        before: tuple[FrontierEntry, ...] | None = None,
        after: tuple[FrontierEntry, ...] | None = None,
        generated: tuple[GeneratedEntry, ...] = (),
        extra: Optional[dict] = None,
    ) -> None:
        """Record one event, copying the current visited log and parents."""
        data = dict(extra) if extra is not None else {}
        if "stack" in data:
            path = tuple(data["stack"])
        else:
            path = tuple(path_from_node(current))
        self._steps.append(
            TraceStep(
                index=len(self._steps),
                kind=kind,
                current=current.state if current is not None else None,
                message=message,
                frontier_before=tuple(before) if before is not None else (),
                frontier_after=tuple(after) if after is not None else (),
                visited=tuple(self._visited),
                generated=tuple(generated),
                parents=dict(self._parents),
                path_to_current=path,
                g=(
                    current.g
                    if current is not None and "g" in self.use
                    else None
                ),
                h=(
                    current.h
                    if current is not None and "h" in self.use
                    else None
                ),
                f=(
                    current.f
                    if current is not None and "f" in self.use
                    else None
                ),
                extra=data,
            )
        )


def visit_order(result: SearchResult) -> list[str]:
    """Visited states of the final step, repeats preserved (OP-9)."""
    if not result.steps:
        return []
    return list(result.steps[-1].visited)


def build_result(
    rec: TraceRecorder,
    graph: SearchGraph,
    params: SearchParams,
    key: str,
    status: Literal["found", "not_found", "aborted_iteration_cap"],
    goal_node: Optional[SearchNode],
    message: str,
    counters: SearchCounters,
) -> SearchResult:
    """Assemble a ``SearchResult`` from the recorder and runner counters."""
    label, category = ALGO_META[key]
    steps = tuple(rec.steps)
    iterations = sum(
        1
        for step in steps
        if step.kind in ("select", "goal_found", "call")
    )
    nodes_expanded = sum(
        1 for step in steps if step.kind in ("select", "call")
    )
    found = status == "found"
    path = tuple(path_from_node(goal_node)) if found else ()
    cost = goal_node.g if found and goal_node is not None else None
    stats = SearchStats(
        iterations=iterations,
        nodes_expanded=nodes_expanded,
        nodes_generated=counters.nodes_generated,
        max_frontier_size=counters.max_frontier_size,
        max_depth_reached=counters.max_depth_reached,
        solution_length=len(path) - 1 if found else None,
        runtime_ms=0.0,
    )
    return SearchResult(
        algorithm_key=key,
        algorithm_label=label,
        category=category,
        start=graph.start,  # type: ignore[arg-type]
        goal=graph.goal,  # type: ignore[arg-type]
        status=status,
        found=found,
        path=path,
        cost=cost,
        steps=steps,
        stats=stats,
        params=params,
        message=message,
    )
