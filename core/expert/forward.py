"""Forward chaining (data-driven inference)"""

from __future__ import annotations

from core.expert.models import ForwardResult, ForwardStep, KnowledgeBase
from core.text import normalize


def forward_chaining(
    kb: KnowledgeBase,
    goal: str | None = None,
    stop_at_goal: bool = True,
) -> ForwardResult:
    """Run forward chaining without mutating ``kb``.

    One rule is fired per inference: among the unfired triggerable rules in
    list order, the first one is chosen. The goal is checked
    before the loop and after each firing .
    """
    if goal is not None:
        goal = normalize(goal)
    facts = list(kb.facts)
    factset = set(facts)
    initial = tuple(facts)
    fired: set[str] = set()
    steps: list[ForwardStep] = []
    derivation: dict[str, tuple[str, tuple[str, ...]]] = {}
    already = goal is not None and goal in factset

    if goal is not None and stop_at_goal and already:  
        return ForwardResult(
            goal=goal,
            initial_facts=initial,
            already_in_facts=True,
            success=True,
            stop_reason="goal_already_known",
            steps=[],
            final_facts=initial,
            derived_facts=(),
            fired_rules=(),
            unfired_rules=tuple(rule.id for rule in kb.rules),
            derivation={},
        )

    stop_reason = "saturated"
    while True:  # "tant qu'il y a des règles non vérifiées"
        detected = [
            rule
            for rule in kb.rules
            if rule.id not in fired
            and all(premise in factset for premise in rule.premises)
        ]
        if not detected:  # saturation 
            break
        chosen = detected[0]
        fired.add(chosen.id)
        is_new = chosen.conclusion not in factset
        if is_new:
            facts.append(chosen.conclusion)
            factset.add(chosen.conclusion)
            derivation[chosen.conclusion] = (chosen.id, chosen.premises)
        reached = goal is not None and chosen.conclusion == goal

        detected_ids = ", ".join(rule.id for rule in detected)
        message = (
            f"Inférence {len(steps) + 1} : règles déclenchables "
            f"{{{detected_ids}}}. Choix : {chosen.id} (première de la liste). "
        )
        if is_new:
            message += (
                f"Déduction : {chosen.conclusion} ajouté à la base de faits."
            )
        else:
            message += (
                f"Déduction : {chosen.conclusion} — conclusion déjà connue : "
                "aucun fait nouveau."
            )
        if reached:
            message += f" But atteint : {goal}."

        steps.append(
            ForwardStep(
                index=len(steps) + 1,
                detected=tuple(rule.id for rule in detected),
                chosen=chosen.id,
                chosen_text=chosen.to_text(),
                premises_satisfied=chosen.premises,
                derived=chosen.conclusion,
                is_new=is_new,
                facts_after=tuple(facts),
                goal_reached=reached,
                message=message,
            )
        )
        if reached and stop_at_goal:  # "si conclusion = But retourner Vrai"
            stop_reason = "goal_reached"
            break

    success = None if goal is None else (goal in factset)
    return ForwardResult(
        goal=goal,
        initial_facts=initial,
        already_in_facts=already,
        success=success,
        stop_reason=stop_reason,
        steps=steps,
        final_facts=tuple(facts),
        derived_facts=tuple(facts[len(initial) :]),
        fired_rules=tuple(step.chosen for step in steps),
        unfired_rules=tuple(rule.id for rule in kb.rules if rule.id not in fired),
        derivation=derivation,
    )
