"""Uninformed search algorithms (AS B.1–B.6, Ch3 p.32–48)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.search.models import (
    GeneratedEntry,
    SearchGraph,
    SearchParams,
    SearchResult,
)
from core.search.trace import (
    SearchCounters,
    SearchNode,
    TraceRecorder,
    build_result,
    path_from_node,
)
from core.text import fmt_num

_RECURSION_LIMIT = 800


@dataclass
class _CallCounter:
    """Cumulative recursive-call counter shared across IDS iterations."""

    calls: int = 0


class _CapReached(Exception):
    """Raised when a recursive runner exceeds its call/depth budget."""


def _init_message(
    graph: SearchGraph, frontier_after: tuple
) -> str:
    """Build the AS §0.5 init message."""
    return (
        f"État initial : {graph.start}. But : {graph.goal}. "
        f"Frontière initiale : "
        f"[{', '.join(entry.state for entry in frontier_after)}]."
    )


def _select_message(
    iteration: int, node: SearchNode, generated: list[GeneratedEntry]
) -> str:
    """Build the AS §0.5 select message."""
    added = [entry.state for entry in generated if entry.status == "added"]
    skipped = [
        entry.state
        for entry in generated
        if entry.status == "skipped_visited"
    ]
    added_text = ", ".join(added) if added else "aucun"
    message = (
        f"Itération {iteration} : on retire {node.state} de la frontière. "
        f"{node.state} n'est pas le but ; successeurs ajoutés : {added_text}."
    )
    if skipped:
        message += f" Déjà visités : {', '.join(skipped)}."
    return message


def _goal_message(iteration: int, node: SearchNode) -> str:
    """Build the AS §0.5 goal_found message."""
    path = " → ".join(path_from_node(node))
    return (
        f"Itération {iteration} : on retire {node.state} de la frontière : "
        f"c'est l'état but. Chemin : {path}, coût {fmt_num(node.g)}."
    )


def _recursive_goal_message(
    node: SearchNode, iteration: Optional[int] = None
) -> str:
    """Build a goal message for the recursive algorithms."""
    path = " → ".join(path_from_node(node))
    if iteration is None:
        prefix = (
            f"But {node.state} atteint à la profondeur {node.depth}"
        )
    else:
        prefix = (
            f"Itération {iteration} : but {node.state} atteint à la "
            f"profondeur {node.depth}"
        )
    return f"{prefix}. Chemin : {path}, coût {fmt_num(node.g)}."


def _fail_message(graph: SearchGraph) -> str:
    """Build the AS §0.5 frontier-empty failure message."""
    return (
        f"Frontière vide : aucun chemin de {graph.start} vers {graph.goal}."
    )


def _cap_message(params: SearchParams) -> str:
    """Build the AS §0.5 iteration-cap message."""
    return (
        f"Arrêt : limite de {params.max_iterations} itérations atteinte "
        f"(boucle probable)."
    )


def _cutoff_message(node: SearchNode, limit: int, limit_max: int) -> str:
    """Build the AS §0.5 cutoff message."""
    return (
        f"Profondeur {limit} > limite {limit_max} : coupure sur "
        f"{node.state} (non testé)."
    )


def _backtrack_message(node: SearchNode) -> str:
    """Build the AS B.4 backtrack message."""
    return f"Plus de successeur non visité pour {node.state} : retour."


def bfs(graph: SearchGraph, params: SearchParams) -> SearchResult:
    """Breadth-first search, improved version (Ch3 p.32)."""
    rec = TraceRecorder(graph, "bfs", use=("depth",))
    counters = SearchCounters(nodes_generated=1)
    root = SearchNode(graph.start)
    frontier = [root]
    rec.mark_visited(graph.start)
    counters.max_frontier_size = 1
    after = rec.snapshot(frontier)
    rec.step("init", None, _init_message(graph, after), after=after)
    iteration = 0
    while frontier:
        iteration += 1
        if iteration > params.max_iterations:
            message = _cap_message(params)
            rec.step("cap", None, message)
            return build_result(
                rec,
                graph,
                params,
                "bfs",
                "aborted_iteration_cap",
                None,
                message,
                counters,
            )
        before = rec.snapshot(frontier)
        node = frontier.pop(0)
        counters.max_depth_reached = max(
            counters.max_depth_reached, node.depth
        )
        if node.state == graph.goal:
            message = _goal_message(iteration, node)
            rec.step(
                "goal_found",
                node,
                message,
                before=before,
                after=rec.snapshot(frontier),
            )
            return build_result(
                rec, graph, params, "bfs", "found", node, message, counters
            )
        rec.mark_visited(node.state)
        generated: list[GeneratedEntry] = []
        for state, cost in graph.successors(node.state):
            if state in rec.visited:
                generated.append(
                    GeneratedEntry(
                        state,
                        node.state,
                        None,
                        None,
                        None,
                        "skipped_visited",
                        "déjà visité",
                    )
                )
            else:
                child = SearchNode(
                    state, node, node.g + cost, depth=node.depth + 1
                )
                frontier.append(child)
                counters.nodes_generated += 1
                rec.set_parent(state, node.state)
                generated.append(
                    GeneratedEntry(
                        state, node.state, None, None, None, "added"
                    )
                )
        after = rec.snapshot(frontier)
        counters.max_frontier_size = max(
            counters.max_frontier_size, len(frontier)
        )
        rec.step(
            "select",
            node,
            _select_message(iteration, node, generated),
            before=before,
            after=after,
            generated=tuple(generated),
            extra={"iteration": iteration},
        )
    message = _fail_message(graph)
    rec.step("fail", None, message)
    return build_result(
        rec, graph, params, "bfs", "not_found", None, message, counters
    )


def ucs(graph: SearchGraph, params: SearchParams) -> SearchResult:
    """Uniform-cost search, stable cost ordering (Ch3 p.35)."""
    rec = TraceRecorder(graph, "ucs", use=("g", "depth"))
    counters = SearchCounters(nodes_generated=1)
    root = SearchNode(graph.start)
    frontier = [root]
    rec.mark_visited(graph.start)
    counters.max_frontier_size = 1
    after = rec.snapshot(frontier)
    rec.step("init", None, _init_message(graph, after), after=after)
    iteration = 0
    while frontier:
        iteration += 1
        if iteration > params.max_iterations:
            message = _cap_message(params)
            rec.step("cap", None, message)
            return build_result(
                rec,
                graph,
                params,
                "ucs",
                "aborted_iteration_cap",
                None,
                message,
                counters,
            )
        before = rec.snapshot(frontier)
        node = frontier.pop(0)
        counters.max_depth_reached = max(
            counters.max_depth_reached, node.depth
        )
        if node.state == graph.goal:
            message = _goal_message(iteration, node)
            rec.step(
                "goal_found",
                node,
                message,
                before=before,
                after=rec.snapshot(frontier),
            )
            return build_result(
                rec, graph, params, "ucs", "found", node, message, counters
            )
        rec.mark_visited(node.state)
        generated: list[GeneratedEntry] = []
        for state, cost in graph.successors(node.state):
            if state in rec.visited:
                generated.append(
                    GeneratedEntry(
                        state,
                        node.state,
                        None,
                        None,
                        None,
                        "skipped_visited",
                        "déjà visité",
                    )
                )
            else:
                child = SearchNode(
                    state, node, node.g + cost, depth=node.depth + 1
                )
                frontier.append(child)
                counters.nodes_generated += 1
                rec.set_parent(state, node.state)
                generated.append(
                    GeneratedEntry(
                        state,
                        node.state,
                        child.g,
                        None,
                        None,
                        "added",
                    )
                )
        frontier.sort(key=lambda entry: entry.g)
        after = rec.snapshot(frontier)
        counters.max_frontier_size = max(
            counters.max_frontier_size, len(frontier)
        )
        rec.step(
            "select",
            node,
            _select_message(iteration, node, generated),
            before=before,
            after=after,
            generated=tuple(generated),
            extra={"iteration": iteration},
        )
    message = _fail_message(graph)
    rec.step("fail", None, message)
    return build_result(
        rec, graph, params, "ucs", "not_found", None, message, counters
    )


def dfs(graph: SearchGraph, params: SearchParams) -> SearchResult:
    """Depth-first search with a stack whose top is index 0 (Ch3 p.40)."""
    rec = TraceRecorder(graph, "dfs", use=("depth",))
    counters = SearchCounters(nodes_generated=1)
    root = SearchNode(graph.start)
    frontier = [root]
    counters.max_frontier_size = 1
    after = rec.snapshot(frontier)
    rec.step("init", None, _init_message(graph, after), after=after)
    iteration = 0
    while frontier:
        iteration += 1
        if iteration > params.max_iterations:
            message = _cap_message(params)
            rec.step("cap", None, message)
            return build_result(
                rec,
                graph,
                params,
                "dfs",
                "aborted_iteration_cap",
                None,
                message,
                counters,
            )
        before = rec.snapshot(frontier)
        node = frontier.pop(0)
        counters.max_depth_reached = max(
            counters.max_depth_reached, node.depth
        )
        if node.state == graph.goal:
            message = _goal_message(iteration, node)
            rec.step(
                "goal_found",
                node,
                message,
                before=before,
                after=rec.snapshot(frontier),
            )
            return build_result(
                rec, graph, params, "dfs", "found", node, message, counters
            )
        rec.mark_visited(node.state)
        generated: list[GeneratedEntry] = []
        block: list[SearchNode] = []
        for state, cost in graph.successors(node.state):
            if state in rec.visited:
                generated.append(
                    GeneratedEntry(
                        state,
                        node.state,
                        None,
                        None,
                        None,
                        "skipped_visited",
                        "déjà visité",
                    )
                )
            else:
                child = SearchNode(
                    state, node, node.g + cost, depth=node.depth + 1
                )
                block.append(child)
                counters.nodes_generated += 1
                rec.set_parent(state, node.state)
                generated.append(
                    GeneratedEntry(
                        state, node.state, None, None, None, "added"
                    )
                )
        frontier = block + frontier
        after = rec.snapshot(frontier)
        counters.max_frontier_size = max(
            counters.max_frontier_size, len(frontier)
        )
        rec.step(
            "select",
            node,
            _select_message(iteration, node, generated),
            before=before,
            after=after,
            generated=tuple(generated),
            extra={"iteration": iteration, "top_of_stack": "first"},
        )
    message = _fail_message(graph)
    rec.step("fail", None, message)
    return build_result(
        rec, graph, params, "dfs", "not_found", None, message, counters
    )


def _entry_statuses(
    graph: SearchGraph,
    node: SearchNode,
    rec: TraceRecorder,
    limit: int,
    limit_max: int,
    mode: str,
    stack: list[str],
) -> tuple[GeneratedEntry, ...]:
    """Successor statuses shown at the entry of a recursive call."""
    entries: list[GeneratedEntry] = []
    for state, _cost in graph.successors(node.state):
        if mode == "course":
            blocked = state in rec.visited
        else:
            blocked = state in stack
        if blocked:
            status, note = "skipped_visited", "déjà visité"
        elif limit + 1 > limit_max:
            status, note = "cutoff", "au-delà de la limite"
        else:
            status, note = "added", ""
        entries.append(
            GeneratedEntry(
                state, node.state, None, None, None, status, note
            )
        )
    return tuple(entries)


def dfs_recursive(
    graph: SearchGraph, params: SearchParams
) -> SearchResult:
    """Depth-first search, recursive version (Ch3 p.42)."""
    rec = TraceRecorder(graph, "dfs_recursive", use=())
    counters = SearchCounters(nodes_generated=1)
    stack: list[str] = []
    counter = _CallCounter()
    root = SearchNode(graph.start)
    rec.step("init", None, _init_message(graph, ()), after=())

    def visit(node: SearchNode) -> Optional[SearchNode]:
        counter.calls += 1
        if (
            counter.calls > params.max_iterations
            or len(stack) + 1 > _RECURSION_LIMIT
        ):
            raise _CapReached
        stack.append(node.state)
        counters.max_frontier_size = max(
            counters.max_frontier_size, len(stack)
        )
        counters.max_depth_reached = max(
            counters.max_depth_reached, node.depth
        )
        if node.state == graph.goal:
            message = _recursive_goal_message(node)
            rec.step(
                "goal_found",
                node,
                message,
                extra={"stack": list(stack), "depth": node.depth},
            )
            return node
        rec.mark_visited(node.state)
        generated = tuple(
            GeneratedEntry(
                state,
                node.state,
                None,
                None,
                None,
                "skipped_visited" if state in rec.visited else "added",
                "déjà visité" if state in rec.visited else "",
            )
            for state, _cost in graph.successors(node.state)
        )
        rec.step(
            "call",
            node,
            f"Appel récursif sur {node.state} "
            f"(profondeur {node.depth}).",
            generated=generated,
            extra={"stack": list(stack), "depth": node.depth},
        )
        for state, cost in graph.successors(node.state):
            if state not in rec.visited:
                child = SearchNode(
                    state, node, node.g + cost, depth=node.depth + 1
                )
                counters.nodes_generated += 1
                result = visit(child)
                if result is not None:
                    return result
        rec.step(
            "backtrack",
            node,
            _backtrack_message(node),
            extra={"stack": list(stack), "depth": node.depth},
        )
        stack.pop()
        return None

    try:
        goal_node = visit(root)
    except _CapReached:
        message = _cap_message(params)
        rec.step("cap", None, message)
        return build_result(
            rec,
            graph,
            params,
            "dfs_recursive",
            "aborted_iteration_cap",
            None,
            message,
            counters,
        )
    if goal_node is not None:
        message = rec.steps[-1].message
        return build_result(
            rec,
            graph,
            params,
            "dfs_recursive",
            "found",
            goal_node,
            message,
            counters,
        )
    message = _fail_message(graph)
    rec.step("fail", None, message)
    return build_result(
        rec,
        graph,
        params,
        "dfs_recursive",
        "not_found",
        None,
        message,
        counters,
    )


def _dls_core(
    graph: SearchGraph,
    params: SearchParams,
    rec: TraceRecorder,
    root: SearchNode,
    limit_max: int,
    mode: str,
    counters: SearchCounters,
    counter: _CallCounter,
    iteration: Optional[int],
) -> Optional[SearchNode]:
    """Recursive limited-depth search shared by DLS and IDS (Ch3 p.45)."""
    stack: list[str] = []

    def call(node: SearchNode, limit: int) -> Optional[SearchNode]:
        counter.calls += 1
        if (
            counter.calls > params.max_iterations
            or len(stack) + 1 > _RECURSION_LIMIT
        ):
            raise _CapReached
        if limit > limit_max:
            counters.max_depth_reached = max(
                counters.max_depth_reached, node.depth
            )
            rec.step(
                "cutoff",
                node,
                _cutoff_message(node, limit, limit_max),
                extra={
                    "stack": stack + [node.state],
                    "depth": limit,
                    "limit": limit,
                    "limit_max": limit_max,
                    "mode": mode,
                },
            )
            return None
        stack.append(node.state)
        counters.max_frontier_size = max(
            counters.max_frontier_size, len(stack)
        )
        counters.max_depth_reached = max(
            counters.max_depth_reached, node.depth
        )
        if node.state == graph.goal:
            message = _recursive_goal_message(node, iteration)
            rec.step(
                "goal_found",
                node,
                message,
                extra={
                    "stack": list(stack),
                    "depth": limit,
                    "limit": limit,
                    "limit_max": limit_max,
                    "mode": mode,
                },
            )
            return node
        rec.mark_visited(node.state)
        generated = _entry_statuses(
            graph, node, rec, limit, limit_max, mode, stack
        )
        rec.step(
            "call",
            node,
            f"Appel récursif sur {node.state} à la profondeur "
            f"{limit} (limite {limit_max}, mode {mode}).",
            generated=generated,
            extra={
                "stack": list(stack),
                "depth": limit,
                "limit": limit,
                "limit_max": limit_max,
                "mode": mode,
            },
        )
        for state, cost in graph.successors(node.state):
            if mode == "course":
                blocked = state in rec.visited
            else:
                blocked = state in stack
            if not blocked:
                child = SearchNode(
                    state, node, node.g + cost, depth=limit + 1
                )
                counters.nodes_generated += 1
                result = call(child, limit + 1)
                if result is not None:
                    return result
        rec.step(
            "backtrack",
            node,
            _backtrack_message(node),
            extra={
                "stack": list(stack),
                "depth": limit,
                "limit": limit,
                "limit_max": limit_max,
                "mode": mode,
            },
        )
        stack.pop()
        return None

    return call(root, 0)


def dls(graph: SearchGraph, params: SearchParams) -> SearchResult:
    """Depth-limited search (Ch3 p.45)."""
    rec = TraceRecorder(graph, "dls", use=())
    counters = SearchCounters(nodes_generated=1)
    root = SearchNode(graph.start)
    rec.step("init", None, _init_message(graph, ()), after=())
    counter = _CallCounter()
    try:
        goal_node = _dls_core(
            graph,
            params,
            rec,
            root,
            params.depth_limit,
            params.dls_visited_mode,
            counters,
            counter,
            None,
        )
    except _CapReached:
        message = _cap_message(params)
        rec.step("cap", None, message)
        return build_result(
            rec,
            graph,
            params,
            "dls",
            "aborted_iteration_cap",
            None,
            message,
            counters,
        )
    if goal_node is not None:
        message = rec.steps[-1].message
        return build_result(
            rec, graph, params, "dls", "found", goal_node, message, counters
        )
    message = (
        f"Aucune solution dans la limite de profondeur "
        f"{params.depth_limit} (le but peut exister au-delà)."
    )
    rec.step("fail", None, message)
    return build_result(
        rec, graph, params, "dls", "not_found", None, message, counters
    )


def ids(graph: SearchGraph, params: SearchParams) -> SearchResult:
    """Iterative deepening search (Ch3 p.48)."""
    rec = TraceRecorder(graph, "ids", use=())
    counters = SearchCounters(nodes_generated=1)
    root = SearchNode(graph.start)
    limit_max = params.max_depth or len(graph.vertices)
    rec.step("init", None, _init_message(graph, ()), after=())
    counter = _CallCounter()
    for limit in range(1, limit_max + 1):
        rec.reset_visited()
        rec.step(
            "iteration_start",
            None,
            f"Itération {limit} : recherche en profondeur limitée "
            f"à {limit}.",
            extra={
                "iteration": limit,
                "limit": limit,
                "limit_max": limit_max,
            },
        )
        try:
            goal_node = _dls_core(
                graph,
                params,
                rec,
                root,
                limit,
                params.dls_visited_mode,
                counters,
                counter,
                limit,
            )
        except _CapReached:
            message = _cap_message(params)
            rec.step("cap", None, message)
            return build_result(
                rec,
                graph,
                params,
                "ids",
                "aborted_iteration_cap",
                None,
                message,
                counters,
            )
        if goal_node is not None:
            message = rec.steps[-1].message
            return build_result(
                rec,
                graph,
                params,
                "ids",
                "found",
                goal_node,
                message,
                counters,
            )
    message = (
        f"Échec : aucune solution jusqu'à la profondeur maximale "
        f"{limit_max}."
    )
    rec.step("fail", None, message)
    return build_result(
        rec, graph, params, "ids", "not_found", None, message, counters
    )
