"""Explanation helpers: forward derivation lines and backward proof text."""

from __future__ import annotations

from core.expert.models import ForwardResult, ProofNode, RuleAttempt
from core.text import normalize

ExplanationLine = tuple[str, tuple[str, ...], str]

_REASON = {
    "fact": "fait",
    "proved": "prouvé",
    "failed": "échec",
    "cycle": "cycle",
    "no_rule": "aucune règle",
}


def explain_forward(result: ForwardResult, fact: str) -> list[ExplanationLine]:
    """Return the ordered rule applications that establish ``fact``.

    Every premise is established before the rule that uses it; each fact is
    emitted once (first occurrence). An initial fact yields an empty list and
    an unknown fact raises ``KeyError``.
    """
    target = normalize(fact)
    initial = set(result.initial_facts)
    if target in initial:
        return []
    if target not in result.derivation:
        raise KeyError(fact)

    lines: list[ExplanationLine] = []
    emitted: set[str] = set()

    def walk(value: str) -> None:
        if value in initial or value in emitted:
            return
        if value not in result.derivation:
            return
        rule_id, premises = result.derivation[value]
        for premise in premises:
            walk(premise)
        if value not in emitted:
            emitted.add(value)
            lines.append((rule_id, premises, value))

    walk(target)
    return lines


def proof_to_lines(proof: ProofNode) -> list[str]:
    """Render a backward-chaining proof tree as indented text."""
    lines: list[str] = []

    def attempt_reason(attempt: RuleAttempt) -> str:
        if not attempt.subproofs:
            return "échec"
        failing = attempt.subproofs[-1]
        return f"{failing.goal} : {_REASON[failing.status]}"

    def render(node: ProofNode, depth: int) -> None:
        indent = "    " * depth
        if node.status == "fact":
            lines.append(f"{indent}✔ {node.goal} : fait")
        elif node.status == "proved":
            lines.append(f"{indent}✔ {node.goal} : prouvé par {node.rule_id}")
            for attempt in node.attempts:
                if not attempt.success:
                    lines.append(
                        f"{indent}    ✘ {node.goal} via {attempt.rule_id} : "
                        f"échec ({attempt_reason(attempt)})"
                    )
            for attempt in node.attempts:
                if attempt.success:
                    for subproof in attempt.subproofs:
                        render(subproof, depth + 1)
        elif node.status == "cycle":
            lines.append(f"{indent}↺ {node.goal} : cycle")
        elif node.status == "no_rule":
            lines.append(f"{indent}✘ {node.goal} : échec (aucune règle)")
        else:
            lines.append(f"{indent}✘ {node.goal} : échec")
            for attempt in node.attempts:
                if not attempt.success:
                    lines.append(
                        f"{indent}    ✘ {node.goal} via {attempt.rule_id} : "
                        f"échec ({attempt_reason(attempt)})"
                    )

    render(proof, 0)
    return lines
