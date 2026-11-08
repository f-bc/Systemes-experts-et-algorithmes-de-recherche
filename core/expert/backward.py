"""Backward chaining (goal-driven inference), AS §A.2, Ch2 p.28–32."""

from __future__ import annotations

from core.expert.models import (
    BackwardKind,
    BackwardResult,
    BackwardStep,
    KnowledgeBase,
    ProofNode,
    RuleAttempt,
)
from core.text import normalize


def rules_used(proof: ProofNode) -> tuple[str, ...]:
    """Return the rules of the successful proof, post-order, de-duplicated."""
    used: list[str] = []
    seen: set[str] = set()

    def walk(node: ProofNode) -> None:
        if node.status != "proved":
            return
        for attempt in node.attempts:
            if not attempt.success:
                continue
            for subproof in attempt.subproofs:
                walk(subproof)
            if node.rule_id is not None and node.rule_id not in seen:
                seen.add(node.rule_id)
                used.append(node.rule_id)

    walk(proof)
    return tuple(used)


def backward_chaining(kb: KnowledgeBase, goal: str) -> BackwardResult:
    """Prove ``goal`` recursively without mutating ``kb`` ."""
    goal = normalize(goal)
    facts = list(kb.facts)
    factset = set(facts)
    initial = tuple(facts)
    steps: list[BackwardStep] = []

    def emit(
        depth: int,
        kind: BackwardKind,
        current: str,
        rule_id: str | None,
        stack: list[str],
        message: str,
    ) -> None:
        steps.append(
            BackwardStep(
                index=len(steps) + 1,
                depth=depth,
                kind=kind,
                goal=current,
                rule_id=rule_id,
                goal_stack=tuple(stack),
                facts_snapshot=tuple(facts),
                message=message,
            )
        )

    def prove(current: str, stack: list[str], depth: int) -> ProofNode:
        if current in factset:
            emit(
                depth,
                "fact_found",
                current,
                None,
                stack,
                f"{current} est dans la base de faits.",
            )
            return ProofNode(current, "fact", None, [])
        if current in stack:
            emit(
                depth,
                "cycle",
                current,
                None,
                stack,
                f"Cycle détecté sur {current} : branche abandonnée.",
            )
            return ProofNode(current, "cycle", None, [])

        candidates = kb.rules_for(current)
        if not candidates:
            emit(
                depth,
                "no_rule",
                current,
                None,
                stack,
                f"Aucune règle ne conclut {current} et ce n'est pas un fait.",
            )
            return ProofNode(current, "no_rule", None, [])

        node = ProofNode(current, "failed", None, [])
        for rule in candidates:
            child_stack = stack + [current]
            emit(
                depth,
                "try_rule",
                current,
                rule.id,
                child_stack,
                f"Pour prouver {current}, essai de {rule.to_text()}.",
            )
            attempt = RuleAttempt(rule.id, [], False)
            node.attempts.append(attempt)
            ok = True
            for premise in rule.premises:
                emit(
                    depth + 1,
                    "subgoal",
                    premise,
                    rule.id,
                    child_stack,
                    f"Sous-but : {premise}.",
                )
                subproof = prove(premise, child_stack, depth + 1)
                attempt.subproofs.append(subproof)
                if subproof.status not in ("fact", "proved"):
                    ok = False
                    break
            if ok:
                attempt.success = True
                facts.append(current)
                factset.add(current)
                node.status = "proved"
                node.rule_id = rule.id
                emit(
                    depth,
                    "goal_proved",
                    current,
                    rule.id,
                    stack,
                    f"{current} est prouvé par {rule.id}.",
                )
                return node
            emit(
                depth,
                "rule_failure",
                current,
                rule.id,
                child_stack,
                f"{rule.id} échoue : une prémisse n'est pas prouvable.",
            )

        emit(
            depth,
            "goal_failed",
            current,
            None,
            stack,
            f"Plus aucune règle pour {current} : échec.",
        )
        return node

    if goal in factset:  # E-4, Ch2 p.29
        emit(
            0,
            "fact_found",
            goal,
            None,
            [],
            "L'objectif est déjà dans la base de faits.",
        )
        proof = ProofNode(goal, "fact", None, [])
        return BackwardResult(
            goal=goal,
            initial_facts=initial,
            already_in_facts=True,
            success=True,
            stop_reason="goal_already_known",
            steps=steps,
            proof=proof,
            final_facts=initial,
            rules_used=(),
        )

    emit(0, "goal", goal, None, [], f"But à prouver : {goal}.")
    proof = prove(goal, [], 0)
    success = proof.status == "proved"
    return BackwardResult(
        goal=goal,
        initial_facts=initial,
        already_in_facts=False,
        success=success,
        stop_reason="proved" if success else "failed",
        steps=steps,
        proof=proof,
        final_facts=tuple(facts),
        rules_used=rules_used(proof),
    )
