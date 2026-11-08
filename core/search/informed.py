"""Informed search algorithms (AS B.7–B.10, Ch3 p.55–66)."""

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

INF = float("inf")
_RECURSION_LIMIT = 800


class _CapReached(Exception):
    """Raised when a recursive runner exceeds its call/depth budget."""


@dataclass
class _CallCounter:
    """Cumulative recursive-call counter (RBFS)."""

    calls: int = 0


def _init_message(graph: SearchGraph, after: tuple) -> str:
    """Build the AS §0.5 init message."""
    return (
        f"État initial : {graph.start}. But : {graph.goal}. "
        f"Frontière initiale : "
        f"[{', '.join(entry.state for entry in after)}]."
    )


def _cap_message(params: SearchParams) -> str:
    """Build the AS §0.5 iteration-cap message."""
    return (
        f"Arrêt : limite de {params.max_iterations} itérations atteinte "
        f"(boucle probable)."
    )


def _fail_message(graph: SearchGraph) -> str:
    """Build the AS §0.5 frontier-empty failure message."""
    return (
        f"Frontière vide : aucun chemin de {graph.start} vers {graph.goal}."
    )


def _goal_message(iteration: int, node: SearchNode) -> str:
    """Build the AS §0.5 goal_found message."""
    path = " → ".join(path_from_node(node))
    return (
        f"Itération {iteration} : on retire {node.state} de la frontière : "
        f"c'est l'état but. Chemin : {path}, coût {fmt_num(node.g)}."
    )


def _select_message(
    iteration: int,
    node: SearchNode,
    generated: list[GeneratedEntry],
    skipped_label: str,
) -> str:
    """Build a select message for the informed algorithms."""
    added = [entry.state for entry in generated if entry.status == "added"]
    skipped = [
        entry.state
        for entry in generated
        if entry.status in ("skipped_closed", "skipped_visited")
    ]
    added_text = ", ".join(added) if added else "aucun"
    message = (
        f"Itération {iteration} : on retire {node.state} de la frontière. "
        f"{node.state} n'est pas le but ; successeurs ajoutés : {added_text}."
    )
    if skipped:
        message += f" {skipped_label} : {', '.join(skipped)}."
    return message


def greedy(graph: SearchGraph, params: SearchParams) -> SearchResult:
    """Greedy best-first search."""
    rec = TraceRecorder(graph, "greedy", use=("h",))
    counters = SearchCounters(nodes_generated=1)
    root = SearchNode(
        graph.start,
        h=graph.heuristics[graph.start],
        f=graph.heuristics[graph.start],
    )
    frontier = [root]
    counters.max_frontier_size = 1
    after = rec.snapshot(frontier)
    rec.step("init", None, _init_message(graph, after), after=after)
    use_visited = params.greedy_use_visited
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
                "greedy",
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
                rec,
                graph,
                params,
                "greedy",
                "found",
                node,
                message,
                counters,
            )
        if use_visited:
            rec.mark_visited(node.state)
        generated: list[GeneratedEntry] = []
        for state, cost in graph.successors(node.state):
            if use_visited and state in rec.visited:
                generated.append(
                    GeneratedEntry(
                        state,
                        node.state,
                        None,
                        None,
                        None,
                        "skipped_closed",
                        "déjà fermé",
                    )
                )
                continue
            heuristic = graph.heuristics[state]
            child = SearchNode(
                state,
                node,
                node.g + cost,
                h=heuristic,
                f=heuristic,
                depth=node.depth + 1,
            )
            frontier.append(child)
            counters.nodes_generated += 1
            rec.set_parent(state, node.state)
            generated.append(
                GeneratedEntry(
                    state,
                    node.state,
                    None,
                    heuristic,
                    None,
                    "added",
                )
            )
        frontier.sort(key=lambda entry: entry.h)
        after = rec.snapshot(frontier)
        counters.max_frontier_size = max(
            counters.max_frontier_size, len(frontier)
        )
        rec.step(
            "select",
            node,
            _select_message(iteration, node, generated, "Déjà fermés"),
            before=before,
            after=after,
            generated=tuple(generated),
            extra={"iteration": iteration, "use_visited": use_visited},
        )
    message = _fail_message(graph)
    rec.step("fail", None, message)
    return build_result(
        rec, graph, params, "greedy", "not_found", None, message, counters
    )


def _mark_pruned(
    generated: list[GeneratedEntry],
    pruned: SearchNode,
    parent_state: Optional[str],
) -> None:
    """Turn the matching ``added`` entry into ``pruned`` (or append one)."""
    for index in range(len(generated) - 1, -1, -1):
        entry = generated[index]
        if entry.state == pruned.state and entry.status == "added":
            generated[index] = GeneratedEntry(
                entry.state,
                entry.parent,
                entry.g,
                entry.h,
                entry.f,
                "pruned",
                "élagué (limite mémoire)",
            )
            return
    generated.append(
        GeneratedEntry(
            pruned.state,
            parent_state,
            pruned.g,
            pruned.h,
            pruned.f,
            "pruned",
            "élagué (limite mémoire)",
        )
    )


def _best_first_core(
    graph: SearchGraph,
    params: SearchParams,
    rec: TraceRecorder,
    counters: SearchCounters,
    memory_limit: Optional[int],
) -> tuple[str, Optional[SearchNode], str]:
    """Shared A*/SBA* loop; ``memory_limit`` enables pruning."""
    root = SearchNode(
        graph.start,
        h=graph.heuristics[graph.start],
        f=graph.heuristics[graph.start],
    )
    open_list = [root]
    counters.max_frontier_size = 1
    after = rec.snapshot(open_list)
    rec.step("init", None, _init_message(graph, after), after=after)
    iteration = 0
    total_pruned = 0
    while open_list:
        iteration += 1
        if iteration > params.max_iterations:
            message = _cap_message(params)
            rec.step("cap", None, message)
            return "aborted_iteration_cap", None, message
        before = rec.snapshot(open_list)
        node = open_list.pop(0)
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
                after=rec.snapshot(open_list),
            )
            return "found", node, message
        rec.mark_visited(node.state)
        generated: list[GeneratedEntry] = []
        pruned_states: list[str] = []
        for state, cost in graph.successors(node.state):
            heuristic = graph.heuristics[state]
            new_g = node.g + cost
            if state in rec.visited:
                generated.append(
                    GeneratedEntry(
                        state,
                        node.state,
                        new_g,
                        heuristic,
                        new_g + heuristic,
                        "skipped_closed",
                        "déjà fermé",
                    )
                )
                continue
            existing = next(
                (entry for entry in open_list if entry.state == state),
                None,
            )
            if existing is None:
                child = SearchNode(
                    state,
                    node,
                    new_g,
                    h=heuristic,
                    f=new_g + heuristic,
                    depth=node.depth + 1,
                )
                open_list.append(child)
                counters.nodes_generated += 1
                rec.set_parent(state, node.state)
                generated.append(
                    GeneratedEntry(
                        state,
                        node.state,
                        child.g,
                        child.h,
                        child.f,
                        "added",
                    )
                )
                if memory_limit is not None:
                    open_list.sort(key=lambda entry: entry.f)
                    if len(open_list) > memory_limit:
                        pruned = open_list.pop()
                        total_pruned += 1
                        pruned_states.append(pruned.state)
                        _mark_pruned(
                            generated, pruned, pruned.parent.state
                        )
            elif new_g < existing.g:
                existing.g = new_g
                existing.f = new_g + existing.h
                existing.parent = node
                existing.depth = node.depth + 1
                rec.set_parent(state, node.state)
                generated.append(
                    GeneratedEntry(
                        state,
                        node.state,
                        existing.g,
                        existing.h,
                        existing.f,
                        "improved",
                    )
                )
                if memory_limit is not None:
                    open_list.sort(key=lambda entry: entry.f)
            else:
                generated.append(
                    GeneratedEntry(
                        state,
                        node.state,
                        new_g,
                        heuristic,
                        new_g + heuristic,
                        "not_improved",
                    )
                )
        open_list.sort(key=lambda entry: entry.f)
        after = rec.snapshot(open_list)
        counters.max_frontier_size = max(
            counters.max_frontier_size, len(open_list)
        )
        extra: dict = {"iteration": iteration}
        if memory_limit is not None:
            extra["memory_limit"] = memory_limit
            extra["pruned"] = list(pruned_states)
        rec.step(
            "select",
            node,
            _select_message(iteration, node, generated, "Déjà fermés"),
            before=before,
            after=after,
            generated=tuple(generated),
            extra=extra,
        )
    if memory_limit is not None and total_pruned:
        message = (
            f"Échec : aucun chemin trouvé ({total_pruned} nœud(s) "
            f"élagué(s) à cause de la limite mémoire {memory_limit})."
        )
    else:
        message = _fail_message(graph)
    rec.step("fail", None, message)
    return "not_found", None, message


def astar(graph: SearchGraph, params: SearchParams) -> SearchResult:
    """A* search."""
    rec = TraceRecorder(graph, "astar", use=("g", "h", "f"))
    counters = SearchCounters(nodes_generated=1)
    status, goal_node, message = _best_first_core(
        graph, params, rec, counters, None
    )
    return build_result(
        rec, graph, params, "astar", status, goal_node, message, counters
    )


def sba_star(graph: SearchGraph, params: SearchParams) -> SearchResult:
    """SBA*"""
    rec = TraceRecorder(graph, "sba_star", use=("g", "h", "f"))
    counters = SearchCounters(nodes_generated=1)
    status, goal_node, message = _best_first_core(
        graph, params, rec, counters, params.memory_limit
    )
    return build_result(
        rec,
        graph,
        params,
        "sba_star",
        status,
        goal_node,
        message,
        counters,
    )


def rbfs(graph: SearchGraph, params: SearchParams) -> SearchResult:
    """Recursive best-first search """
    rec = TraceRecorder(graph, "rbfs", use=("g", "h", "f"))
    counters = SearchCounters(nodes_generated=1)
    stack: list[str] = []
    counter = _CallCounter()
    root = SearchNode(
        graph.start, h=graph.heuristics[graph.start]
    )
    root.f = root.h
    rec.step("init", None, _init_message(graph, ()), after=())

    def call(
        node: SearchNode,
        f_limit: float,
        entry: Optional[dict],
    ) -> tuple[str, Optional[SearchNode], float]:
        counter.calls += 1
        if (
            counter.calls > params.max_iterations
            or len(stack) + 1 > _RECURSION_LIMIT
        ):
            raise _CapReached
        stack.append(node.state)
        rec.append_visit(node.state)
        counters.max_frontier_size = max(
            counters.max_frontier_size, len(stack)
        )
        counters.max_depth_reached = max(
            counters.max_depth_reached, node.depth
        )
        base_extra: dict = {
            "stack": list(stack),
            "depth": node.depth,
            "f_limit": f_limit,
            "node_f": node.f,
        }
        if entry is not None:
            base_extra.update(entry)
        if node.state == graph.goal:
            message = (
                f"But {node.state} atteint. Chemin : "
                f"{' → '.join(path_from_node(node))}, "
                f"coût {fmt_num(node.g)}."
            )
            rec.step("goal_found", node, message, extra=base_extra)
            return "found", node, node.f
        successors: list[SearchNode] = []
        for state, cost in graph.successors(node.state):
            heuristic = graph.heuristics[state]
            child = SearchNode(
                state,
                node,
                node.g + cost,
                h=heuristic,
                depth=node.depth + 1,
            )
            child.f = max(child.g + child.h, node.f)
            successors.append(child)
            counters.nodes_generated += 1
        if not successors:
            extra = dict(base_extra)
            extra["returned_f"] = INF
            rec.step(
                "backtrack",
                node,
                f"{node.state} n'a pas de successeur : échec (f = ∞).",
                extra=extra,
            )
            stack.pop()
            return "fail", None, INF
        successors.sort(key=lambda child: child.f)
        successors_extra = [
            {
                "state": child.state,
                "g": child.g,
                "h": child.h,
                "f": child.f,
            }
            for child in successors
        ]
        call_extra = dict(base_extra)
        call_extra["successors"] = successors_extra
        rec.step(
            "call",
            node,
            f"Appel RBFS sur {node.state} (f = {fmt_num(node.f)}, "
            f"limite {fmt_num(f_limit)}).",
            after=rec.snapshot(successors),
            extra=call_extra,
        )
        while True:
            successors.sort(key=lambda child: child.f)
            best = successors[0]
            if best.f > f_limit or best.f == INF:
                message = (
                    f"f(meilleur)={fmt_num(best.f)} > "
                    f"f_limit={fmt_num(f_limit)} : on remonte avec "
                    f"échec ; f({node.state}) devient "
                    f"{fmt_num(best.f)}."
                )
                extra = dict(base_extra)
                extra["returned_f"] = best.f
                extra["best"] = best.state
                rec.step("backtrack", node, message, extra=extra)
                stack.pop()
                return "fail", None, best.f
            alternative = (
                successors[1].f if len(successors) > 1 else INF
            )
            new_limit = min(f_limit, alternative)
            child_entry = {
                "best": best.state,
                "alternative": alternative,
                "new_limit": new_limit,
            }
            result, goal_node, best_f = call(
                best, new_limit, child_entry
            )
            best.f = best_f
            if result == "found":
                return "found", goal_node, best_f

    try:
        status, goal_node, _ = call(root, params.f_limit, None)
    except _CapReached:
        message = _cap_message(params)
        rec.step("cap", None, message)
        return build_result(
            rec,
            graph,
            params,
            "rbfs",
            "aborted_iteration_cap",
            None,
            message,
            counters,
        )
    if status == "found":
        message = rec.steps[-1].message
        return build_result(
            rec, graph, params, "rbfs", "found", goal_node, message, counters
        )
    message = _fail_message(graph)
    rec.step("fail", None, message)
    return build_result(
        rec, graph, params, "rbfs", "not_found", None, message, counters
    )
